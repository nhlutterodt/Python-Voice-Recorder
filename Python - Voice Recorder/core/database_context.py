#!/usr/bin/env python3
"""
Database context management for Voice Recorder Pro
Provides robust session handling, connection pooling, and health monitoring.
Enhanced with comprehensive error handling, disk space monitoring, and resilience features.
"""

import contextlib
import threading
import time
import shutil
from typing import Generator, Optional, Any, Dict, Protocol, runtime_checkable, ContextManager
from pathlib import Path
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy.exc import (
    SQLAlchemyError, 
    OperationalError, 
    IntegrityError,
    TimeoutError,
    DisconnectionError
)
from sqlalchemy import text
import psutil

from core.logging_config import get_logger

logger = get_logger(__name__)

# Module-level placeholder so tests or other modules can patch/import db_context
db_context = None


@dataclass
class DatabaseConfig:
    """Database configuration with environment-specific settings"""
    connection_timeout: int = 30
    query_timeout: int = 60
    max_retries: int = 3
    retry_delay: float = 1.0
    min_disk_space_mb: int = 100
    disk_space_threshold_mb: int = 100
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 60
    enable_disk_space_check: bool = True
    retry_attempts: int = 3
    
    @classmethod
    def from_environment(cls, env: str = "production") -> "DatabaseConfig":
        """Create configuration based on environment"""
        configs = {
            "development": cls(
                connection_timeout=10,
                max_retries=1,
                retry_attempts=2,
                min_disk_space_mb=50,
                disk_space_threshold_mb=50
            ),
            "testing": cls(
                connection_timeout=5,
                max_retries=1,
                retry_attempts=1,
                min_disk_space_mb=10,
                enable_disk_space_check=False
            ),
            "production": cls(
                min_disk_space_mb=500,
                retry_attempts=5
            )  # Default values
        }
        return configs.get(env, cls())


@runtime_checkable
class DBContextProtocol(Protocol):
    """Protocol for database context managers used by services.

    The protocol requires a get_session contextmanager with the same
    signature used by DatabaseContextManager. This allows tests and
    services to accept either the real DatabaseContextManager or a
    test double that implements the same interface.
    """

    def get_session(self, autocommit: bool = False, readonly: bool = False, check_disk_space: bool = True) -> ContextManager[Session]:
        ...


class DatabaseContextManager:
    """Enhanced database context manager with health monitoring, error resilience, and disk space protection"""
    
    def __init__(self, session_factory, config: Optional[DatabaseConfig] = None):
        self.session_factory = session_factory
        self.config = config or DatabaseConfig()
        self._connection_count = 0
        self._failed_connections = 0
        self._last_health_check = 0
        self._lock = threading.RLock()
        self._circuit_breaker_failures = 0
        self._circuit_breaker_last_failure = 0
        self._active_sessions = 0
        self._total_sessions_created = 0
        self.health_check_interval = 300  # 5 minutes
        
    @contextlib.contextmanager
    def get_session(
        self, 
        autocommit: bool = False, 
        readonly: bool = False,
        check_disk_space: bool = True
    ) -> Generator[Session, None, None]:
        """
        Enhanced context manager for database sessions with comprehensive error handling.
        
        Args:
            autocommit: Whether to automatically commit on successful completion
            readonly: Optimize session for read-only operations  
            check_disk_space: Whether to validate disk space before operations
            
        Yields:
            Session: SQLAlchemy session object
            
        Raises:
            DatabaseConnectionError: If unable to establish database connection
            DatabaseTransactionError: If transaction fails and cannot be rolled back
            DatabaseDiskSpaceError: If insufficient disk space for operations
        """
        # Check circuit breaker
        if self._is_circuit_breaker_open():
            # Tests expect the message to include the phrase 'Circuit breaker is open'
            raise DatabaseCircuitBreakerError("Circuit breaker is open - too many recent failures")
        
        # Check disk space if requested (skip for read-only operations)
        if check_disk_space and not readonly:
            # _check_disk_space will raise DatabaseDiskSpaceError when insufficient
            self._check_disk_space()
        
        session = None
        retry_count = 0
        # Use 'retry_attempts' as the number of attempts when provided (tests expect this),
        # otherwise fall back to max_retries for backward compatibility.
        max_attempts = getattr(self.config, 'retry_attempts', None) or getattr(self.config, 'max_retries', 1)
        # Ensure at least one attempt
        try:
            max_attempts = max(1, int(max_attempts))
        except Exception:
            max_attempts = 1

        while retry_count < max_attempts:
            try:
                session = self._create_session_with_config()
                
                with self._lock:
                    self._connection_count += 1
                    self._active_sessions += 1
                    self._total_sessions_created += 1
                    
                if readonly:
                    self._configure_readonly_session(session)
                    
                logger.debug(f"Database session created (attempt {retry_count + 1}, total: {self._connection_count})")
                
                yield session
                
                if autocommit and self._has_pending_changes(session):
                    session.commit()
                    logger.debug("Database session committed successfully")
                
                # Reset circuit breaker on success
                self._reset_circuit_breaker()
                break
                
            except (OperationalError, DisconnectionError) as e:
                # Handle a connection-related error for this attempt (do not mark circuit breaker yet)
                self._handle_connection_error(e, session, retry_count)
                if retry_count >= (max_attempts - 1):
                    # Final failure for this get_session call: increment circuit breaker once
                    with self._lock:
                        self._circuit_breaker_failures += 1
                        self._circuit_breaker_last_failure = time.time()
                    raise DatabaseConnectionError(
                        f"Database connection failed after {max_attempts} attempts: {e}",
                        original_error=e,
                        retry_count=max_attempts
                    ) from e
                    
            except IntegrityError as e:
                self._handle_integrity_error(e, session)
                raise DatabaseIntegrityError(f"Database integrity constraint violated: {e}") from e
                
            except TimeoutError as e:
                self._handle_timeout_error(e, session, retry_count)
                if retry_count >= self.config.max_retries:
                    raise DatabaseTimeoutError(f"Database operation timed out after {self.config.max_retries} retries: {e}") from e
                    
            except SQLAlchemyError as e:
                self._handle_sqlalchemy_error(e, session)
                raise DatabaseTransactionError(f"Database transaction failed: {e}") from e
                
            except Exception as e:
                # If session is None then the error happened during session creation
                # (e.g., session_factory raised). Treat this like a connection error so
                # retry logic applies; after exhausting attempts, raise DatabaseConnectionError.
                if session is None:
                    self._handle_connection_error(e, session, retry_count)
                    if retry_count >= (max_attempts - 1):
                        with self._lock:
                            self._circuit_breaker_failures += 1
                            self._circuit_breaker_last_failure = time.time()
                        raise DatabaseConnectionError(
                            f"Database connection failed after {max_attempts} attempts: {e}",
                            original_error=e,
                            retry_count=max_attempts
                        ) from e
                    # allow retry
                else:
                    # Unexpected error after session creation — keep existing behavior
                    self._handle_unexpected_error(e, session)
                    raise
                
            finally:
                if session:
                    self._cleanup_session(session)
                    
            retry_count += 1
            if retry_count <= self.config.max_retries:
                delay = self.config.retry_delay * (2 ** retry_count)  # Exponential backoff
                logger.debug(f"Retrying database operation in {delay}s...")
                time.sleep(delay)
    
    def _create_session_with_config(self) -> Session:
        """Create session with enhanced configuration"""
        try:
            session = self.session_factory()
            # Set timeout for SQLite operations
            if hasattr(session.bind, 'execute'):
                session.execute(text(f"PRAGMA busy_timeout={self.config.connection_timeout * 1000}"))
            return session
        except Exception:
            with self._lock:
                self._failed_connections += 1
            raise
    
    def _configure_readonly_session(self, session: Session):
        """Configure session for read-only operations"""
        try:
            # SQLite read-only optimization  
            session.execute(text("PRAGMA query_only=ON"))
        except Exception:
            # Ignore if not supported
            pass
    
    def _has_pending_changes(self, session: Session) -> bool:
        """Check if session has pending changes"""
        return bool(session.new or session.dirty or session.deleted)
    
    def _handle_connection_error(self, error: Exception, session: Optional[Session], retry_count: int):
        """Handle connection-related errors with circuit breaker logic"""
        with self._lock:
            # Count the failed connection attempt; the circuit-breaker failure
            # count itself should only increment when a get_session call fails
            # permanently (after all retries).
            self._failed_connections += 1

        logger.warning(f"Database connection error (attempt {retry_count + 1}): {error}")

        if session:
            self._safe_rollback(session)
    
    def _handle_integrity_error(self, error: IntegrityError, session: Optional[Session]):
        """Handle integrity constraint violations"""
        logger.error(f"Database integrity error: {error}")
        if session:
            self._safe_rollback(session)
    
    def _handle_timeout_error(self, error: TimeoutError, session: Optional[Session], retry_count: int):
        """Handle timeout errors with retry logic"""
        logger.warning(f"Database timeout error (attempt {retry_count + 1}): {error}")
        if session:
            self._safe_rollback(session)
    
    def _handle_sqlalchemy_error(self, error: SQLAlchemyError, session: Optional[Session]):
        """Handle general SQLAlchemy errors"""
        logger.error(f"Database SQLAlchemy error: {error}")
        if session:
            self._safe_rollback(session)
    
    def _handle_unexpected_error(self, error: Exception, session: Optional[Session]):
        """Handle unexpected errors"""
        logger.error(f"Unexpected database error: {error}")
        if session:
            self._safe_rollback(session)
    
    def _safe_rollback(self, session: Session):
        """Safely rollback session with error handling"""
        try:
            session.rollback()
            logger.debug("Database session rolled back successfully")
        except Exception as rollback_error:
            logger.error(f"Failed to rollback session: {rollback_error}")
    
    def _cleanup_session(self, session: Session):
        """Safely cleanup session resources with enhanced tracking"""
        try:
            if session:
                session.close()
                with self._lock:
                    self._active_sessions = max(0, self._active_sessions - 1)
                logger.debug("Database session closed and tracked")
        except Exception as close_error:
            logger.error(f"Error closing database session: {close_error}")
    
    def get_session_metrics(self) -> Dict[str, Any]:
        """Get comprehensive session metrics"""
        with self._lock:
            return {
                "active_sessions": self._active_sessions,
                "total_sessions_created": self._total_sessions_created,
                "connection_count": self._connection_count,
                "failed_connections": self._failed_connections,
                "circuit_breaker_failures": self._circuit_breaker_failures,
                "last_failure_time": self._circuit_breaker_last_failure
            }
    
    def _check_disk_space(self) -> bool:
        """Check available disk space before write operations.

        Raises DatabaseDiskSpaceError when available space is below the configured minimum.
        Returns True when sufficient.
        """
        if not getattr(self.config, 'enable_disk_space_check', True):
            return True

        try:
            # Get database directory
            db_path = Path("db").resolve()
            if not db_path.exists():
                db_path = Path.cwd()

            # Prefer psutil.disk_usage so tests can patch psutil.disk_usage
            try:
                usage = psutil.disk_usage(str(db_path))
            except Exception:
                usage = shutil.disk_usage(str(db_path))

            available_mb = usage.free / (1024 * 1024)

            # Use min_disk_space_mb as the threshold tests expect
            required_mb = getattr(self.config, 'min_disk_space_mb', self.config.disk_space_threshold_mb)

            if available_mb < required_mb:
                logger.warning(f"Low disk space: {available_mb:.1f}MB available, threshold: {required_mb}MB")
                raise DatabaseDiskSpaceError(
                    f"Insufficient disk space: {available_mb:.1f} MB available",
                    required_mb=required_mb,
                    available_mb=round(available_mb, 1)
                )

            return True
        except DatabaseDiskSpaceError:
            raise
        except Exception as e:
            logger.warning(f"Could not check disk space: {e}")
            # If we can't determine disk space, be permissive
            return True
    
    def _is_circuit_breaker_open(self) -> bool:
        """Check if circuit breaker should prevent operations"""
        if self._circuit_breaker_failures < self.config.circuit_breaker_threshold:
            return False
            
        time_since_last_failure = time.time() - self._circuit_breaker_last_failure
        is_open = time_since_last_failure < self.config.circuit_breaker_timeout
        
        if is_open:
            logger.warning(f"Circuit breaker open: {self._circuit_breaker_failures} failures in {time_since_last_failure:.1f}s")
        
        return is_open
    
    def _reset_circuit_breaker(self):
        """Reset circuit breaker on successful operation"""
        with self._lock:
            if self._circuit_breaker_failures > 0:
                logger.info("Circuit breaker reset - successful operation completed")
            self._circuit_breaker_failures = 0
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get enhanced database health status with comprehensive metrics.
        
        Returns:
            dict: Health status information including system resources and circuit breaker state
        """
        current_time = time.time()
        
        # Perform health check if interval has passed
        if current_time - self._last_health_check > self.health_check_interval:
            self._perform_health_check()
            self._last_health_check = current_time
        
        with self._lock:
            failure_rate = (self._failed_connections / max(self._connection_count, 1)) * 100
        
        # Get system resource information
        try:
            memory_info = psutil.virtual_memory()
            disk_usage = shutil.disk_usage(Path.cwd())
            
            system_resources = {
                "memory_usage_percent": memory_info.percent,
                "disk_free_mb": round(disk_usage.free / (1024 * 1024), 2),
                "disk_usage_percent": round((disk_usage.used / disk_usage.total) * 100, 2)
            }
        except Exception:
            system_resources = {"error": "Could not retrieve system resources"}
        
        # Determine overall status
        if failure_rate < 5:
            status = "healthy"
        elif failure_rate < 20:
            status = "degraded"  
        else:
            status = "unhealthy"
            
        # Check circuit breaker state
        if self._is_circuit_breaker_open():
            status = "circuit_breaker_open"
        
        return {
            "status": status,
            "total_connections": self._connection_count,
            "failed_connections": self._failed_connections,
            "failure_rate_percent": round(failure_rate, 2),
            "circuit_breaker": {
                "is_open": self._is_circuit_breaker_open(),
                "failures": self._circuit_breaker_failures,
                "last_failure": self._circuit_breaker_last_failure
            },
            "system_resources": system_resources,
            "configuration": {
                "max_retries": self.config.max_retries,
                "disk_threshold_mb": self.config.disk_space_threshold_mb,
                "circuit_breaker_threshold": self.config.circuit_breaker_threshold
            },
            "last_health_check": self._last_health_check
        }
    
    def _perform_health_check(self) -> bool:
        """
        Perform a health check by executing a simple query.
        
        Returns:
            bool: True if healthy, False otherwise
        """
        try:
            with self.get_session() as session:
                # Simple health check query
                session.execute(text("SELECT 1"))
                logger.debug("Database health check passed")
                return True
        except Exception as e:
            logger.warning(f"Database health check failed: {e}")
            return False


class DatabaseConnectionError(Exception):
    """Raised when database connection cannot be established"""
    def __init__(self, message: str = "Database connection error", original_exception: Optional[Exception] = None, **kwargs: Any):
        super().__init__(message)
        # Expose both names for backward-compatibility with tests and callers
        self.original_exception = original_exception
        self.original_error = original_exception
        # Expose any extra keyword args as attributes for tests
        for k, v in kwargs.items():
            setattr(self, k, v)


class DatabaseTransactionError(Exception):
    """Raised when database transaction fails"""
    def __init__(self, message: str = "Database transaction error", original_exception: Optional[Exception] = None, **kwargs: Any):
        super().__init__(message)
        self.original_exception = original_exception
        self.original_error = original_exception
        for k, v in kwargs.items():
            setattr(self, k, v)


class DatabaseIntegrityError(Exception):
    """Raised when database integrity constraints are violated"""
    def __init__(self, message: str = "Database integrity error", original_exception: Optional[Exception] = None, **kwargs: Any):
        super().__init__(message)
        self.original_exception = original_exception
        self.original_error = original_exception
        for k, v in kwargs.items():
            setattr(self, k, v)


class DatabaseTimeoutError(Exception):
    """Raised when database operations timeout"""
    def __init__(self, message: str = "Database timeout", original_exception: Optional[Exception] = None, **kwargs: Any):
        super().__init__(message)
        self.original_exception = original_exception
        self.original_error = original_exception
        for k, v in kwargs.items():
            setattr(self, k, v)


class DatabaseCircuitBreakerError(Exception):
    """Raised when circuit breaker prevents database operations"""
    def __init__(self, message: str = "Circuit breaker open", original_exception: Optional[Exception] = None, **kwargs: Any):
        super().__init__(message)
        self.original_exception = original_exception
        self.original_error = original_exception
        for k, v in kwargs.items():
            setattr(self, k, v)


class DatabaseDiskSpaceError(Exception):
    """Raised when insufficient disk space for database operations"""
    def __init__(self, message: str = "Insufficient disk space", original_exception: Optional[Exception] = None, **kwargs: Any):
        super().__init__(message)
        self.original_exception = original_exception
        self.original_error = original_exception
        for k, v in kwargs.items():
            setattr(self, k, v)


# Connection configuration for enhanced performance
def configure_database_engine(engine):
    """
    Configure database engine with optimized settings for Voice Recorder Pro.
    
    Args:
        engine: SQLAlchemy engine to configure
    """
    if 'sqlite' in str(engine.url):
        # SQLite-specific optimizations
        with engine.connect() as conn:
            # Enable WAL mode for better concurrency
            conn.execute(text("PRAGMA journal_mode=WAL"))
            # Optimize synchronization for better performance
            conn.execute(text("PRAGMA synchronous=NORMAL"))
            # Set reasonable timeout
            conn.execute(text("PRAGMA busy_timeout=5000"))
            # Optimize cache size (negative value = KB)
            conn.execute(text("PRAGMA cache_size=-64000"))  # 64MB cache
            logger.info("SQLite engine configured with performance optimizations")
    
    logger.info(f"Database engine configured: {engine.url}")


def get_database_file_info(db_url: str) -> dict[str, Any]:
    """
    Get information about the database file.
    
    Args:
        db_url: Database URL
        
    Returns:
        dict: Database file information
    """
    if not db_url.startswith('sqlite:///'):
        return {"type": "non-file", "url": db_url}
    
    db_path = Path(db_url.replace('sqlite:///', ''))
    
    if not db_path.exists():
        return {
            "type": "sqlite",
            "path": str(db_path),
            "exists": False
        }
    
    stat = db_path.stat()
    
    return {
        "type": "sqlite",
        "path": str(db_path),
        "exists": True,
        "size_bytes": stat.st_size,
        "size_mb": round(stat.st_size / (1024 * 1024), 2),
        "modified": stat.st_mtime
    }
