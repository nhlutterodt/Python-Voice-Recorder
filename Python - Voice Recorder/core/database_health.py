#!/usr/bin/env python3
"""
Enhanced Database health monitoring service for Voice Recorder Pro
Provides comprehensive database status monitoring, performance metrics, and health checks.
"""

import time
import threading
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path
import json
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum
from sqlalchemy import text
import psutil

from models.database import db_context, engine, DATABASE_URL
from core.logging_config import get_logger
from core.database_context import get_database_file_info

logger = get_logger(__name__)


class HealthCheckSeverity(Enum):
    """Health check severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class HealthCheckResult:
    """Structured health check result"""
    name: str
    status: str  # "pass", "fail", "warning", "error"
    severity: HealthCheckSeverity
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    duration_ms: Optional[float] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


class DatabaseHealthMonitor:
    """Enhanced database health monitoring and metrics collection with comprehensive checks"""
    
    def __init__(self, alert_callback: Optional[Callable[[HealthCheckResult], None]] = None):
        self.health_history: List[Dict[str, Any]] = []
        self.max_history_size = 100
        self.alert_callback = alert_callback
        self._performance_baseline: Optional[Dict[str, float]] = None
        self._lock = threading.RLock()
        
        # Health check registry for extensibility
        self._health_checks = {
            "database_connectivity": self._check_database_connectivity,
            "query_performance": self._check_query_performance,
            "disk_space": self._check_disk_space,
            "memory_usage": self._check_memory_usage,
            "table_integrity": self._check_table_integrity,
        }
        
        # Add SQLite-specific checks
        if 'sqlite' in DATABASE_URL.lower():
            self._health_checks.update({
                "sqlite_integrity": self._check_sqlite_integrity,
                "sqlite_wal_health": self._check_sqlite_wal_health,
            })
    
    @property
    def health_checks(self) -> Dict[str, Any]:
        """Public property to access health checks for backward compatibility"""
        return self._health_checks
    
    def get_health_status(self, include_trends: bool = False) -> Dict[str, Any]:
        """Alias for get_comprehensive_health_status for backward compatibility"""
        return self.get_comprehensive_health_status(include_trends)
        
    def get_comprehensive_health_status(self, include_trends: bool = False) -> Dict[str, Any]:
        """
        Get comprehensive database health status with optional trend analysis.
        
        Args:
            include_trends: Whether to include historical trend analysis
            
        Returns:
            dict: Comprehensive health status with health checks and recommendations
        """
        start_time = time.time()
        
        # Run core health checks
        health_checks = self._run_health_checks()
        
        health_status = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database_url": DATABASE_URL,
            "file_info": get_database_file_info(DATABASE_URL),
            "connection_health": db_context.get_health_status(),
            "engine_info": self._get_enhanced_engine_info(),
            "performance_metrics": self._get_enhanced_performance_metrics(),
            "health_checks": [result.__dict__ for result in health_checks],
            "system_resources": self._get_system_resource_status(),
            "check_duration_ms": round((time.time() - start_time) * 1000, 2)
        }
        
        if include_trends and len(self.health_history) > 1:
            health_status["trends"] = self._analyze_health_trends()
        
        health_status["recommendations"] = self._generate_recommendations(health_status)
        health_status["overall_status"] = self._calculate_overall_status(health_status)
        
        # Store in history with thread safety
        with self._lock:
            self.health_history.append(health_status)
            if len(self.health_history) > self.max_history_size:
                self.health_history.pop(0)
        
        # Process alerts for critical issues
        self._process_alerts(health_checks)
        
        logger.debug(f"Database health check completed: {health_status['overall_status']}")
        return health_status
    
    def _run_health_checks(self) -> List[HealthCheckResult]:
        """Run all registered health checks"""
        results = []
        
        for check_name, check_func in self._health_checks.items():
            try:
                start_time = time.time()
                result = check_func()
                result.duration_ms = round((time.time() - start_time) * 1000, 2)
                results.append(result)
            except Exception as e:
                logger.error(f"Health check {check_name} failed: {e}")
                results.append(HealthCheckResult(
                    name=check_name,
                    status="error",
                    severity=HealthCheckSeverity.ERROR,
                    message=f"Health check failed: {e}",
                    details={"exception": str(e)}
                ))
        
        return results
    
    def _check_database_connectivity(self) -> HealthCheckResult:
        """Check basic database connectivity"""
        try:
            with db_context.get_session(check_disk_space=False) as session:
                session.execute(text("SELECT 1"))
                return HealthCheckResult(
                    name="database_connectivity",
                    status="pass",
                    severity=HealthCheckSeverity.INFO,
                    message="Database connection successful"
                )
        except Exception as e:
            return HealthCheckResult(
                name="database_connectivity",
                status="fail",
                severity=HealthCheckSeverity.CRITICAL,
                message=f"Database connection failed: {e}",
                details={"exception": str(e)}
            )
    
    def _check_query_performance(self) -> HealthCheckResult:
        """Check query performance and establish baselines"""
        try:
            start_time = time.time()
            with db_context.get_session(check_disk_space=False) as session:
                # Run a slightly more complex query to test performance
                session.execute(text("SELECT COUNT(*) FROM sqlite_master WHERE type='table'"))
                query_time = (time.time() - start_time) * 1000  # Convert to ms
            
            # Establish baseline if not set
            if self._performance_baseline is None:
                self._performance_baseline = {"query_time_ms": query_time}
            
            # Check against baseline
            baseline_time = self._performance_baseline.get("query_time_ms", query_time)
            performance_degradation = (query_time / baseline_time) if baseline_time > 0 else 1
            
            if query_time > 1000:  # > 1 second
                status, severity = "fail", HealthCheckSeverity.ERROR
                message = f"Query performance critical: {query_time:.2f}ms"
            elif query_time > 500:  # > 500ms
                status, severity = "warning", HealthCheckSeverity.WARNING
                message = f"Query performance degraded: {query_time:.2f}ms"
            elif performance_degradation > 2.0:  # 2x slower than baseline
                status, severity = "warning", HealthCheckSeverity.WARNING
                message = f"Performance degraded {performance_degradation:.1f}x from baseline"
            else:
                status, severity = "pass", HealthCheckSeverity.INFO
                message = f"Query performance good: {query_time:.2f}ms"
            
            return HealthCheckResult(
                name="query_performance",
                status=status,
                severity=severity,
                message=message,
                details={
                    "query_time_ms": round(query_time, 2),
                    "baseline_ms": round(baseline_time, 2),
                    "degradation_factor": round(performance_degradation, 2)
                }
            )
        except Exception as e:
            return HealthCheckResult(
                name="query_performance",
                status="error",
                severity=HealthCheckSeverity.ERROR,
                message=f"Performance check failed: {e}"
            )
    
    def _check_disk_space(self) -> HealthCheckResult:
        """Check available disk space"""
        try:
            db_path = Path("db").resolve()
            if not db_path.exists():
                db_path = Path.cwd()
            
            usage = psutil.disk_usage(str(db_path))
            free_gb = usage.free / (1024**3)
            usage_percent = (usage.used / usage.total) * 100
            
            if free_gb < 0.1:  # Less than 100MB
                status, severity = "fail", HealthCheckSeverity.CRITICAL
                message = f"Critical disk space: {free_gb:.2f}GB free"
            elif free_gb < 1.0:  # Less than 1GB
                status, severity = "warning", HealthCheckSeverity.WARNING
                message = f"Low disk space: {free_gb:.2f}GB free"
            elif usage_percent > 95:
                status, severity = "warning", HealthCheckSeverity.WARNING
                message = f"High disk usage: {usage_percent:.1f}%"
            else:
                status, severity = "pass", HealthCheckSeverity.INFO
                message = f"Disk space healthy: {free_gb:.2f}GB free"
            
            return HealthCheckResult(
                name="disk_space",
                status=status,
                severity=severity,
                message=message,
                details={
                    "free_gb": round(free_gb, 2),
                    "usage_percent": round(usage_percent, 1),
                    "total_gb": round(usage.total / (1024**3), 2)
                }
            )
        except Exception as e:
            return HealthCheckResult(
                name="disk_space",
                status="error",
                severity=HealthCheckSeverity.ERROR,
                message=f"Disk space check failed: {e}"
            )
    
    def _check_memory_usage(self) -> HealthCheckResult:
        """Check system memory usage"""
        try:
            memory = psutil.virtual_memory()
            
            if memory.percent > 95:
                status, severity = "fail", HealthCheckSeverity.ERROR
                message = f"Critical memory usage: {memory.percent:.1f}%"
            elif memory.percent > 85:
                status, severity = "warning", HealthCheckSeverity.WARNING
                message = f"High memory usage: {memory.percent:.1f}%"
            else:
                status, severity = "pass", HealthCheckSeverity.INFO
                message = f"Memory usage normal: {memory.percent:.1f}%"
            
            return HealthCheckResult(
                name="memory_usage",
                status=status,
                severity=severity,
                message=message,
                details={
                    "usage_percent": memory.percent,
                    "available_gb": round(memory.available / (1024**3), 2),
                    "total_gb": round(memory.total / (1024**3), 2)
                }
            )
        except Exception as e:
            return HealthCheckResult(
                name="memory_usage",
                status="error",
                severity=HealthCheckSeverity.ERROR,
                message=f"Memory check failed: {e}"
            )
    
    def _check_table_integrity(self) -> HealthCheckResult:
        """Check table accessibility and basic structure"""
        try:
            with db_context.get_session(check_disk_space=False) as session:
                # Check if we can perform basic operations on main tables
                try:
                    from models.recording import Recording
                    session.query(Recording).first()
                    return HealthCheckResult(
                        name="table_integrity",
                        status="pass",
                        severity=HealthCheckSeverity.INFO,
                        message="Main tables accessible"
                    )
                except Exception as e:
                    return HealthCheckResult(
                        name="table_integrity",
                        status="fail",
                        severity=HealthCheckSeverity.ERROR,
                        message=f"Table access error: {e}",
                        details={"table_error": str(e)}
                    )
        except Exception as e:
            return HealthCheckResult(
                name="table_integrity",
                status="error",
                severity=HealthCheckSeverity.ERROR,
                message=f"Table integrity check failed: {e}"
            )
    
    # SQLite-specific health checks
    def _check_sqlite_integrity(self) -> HealthCheckResult:
        """SQLite-specific integrity check"""
        try:
            with db_context.get_session(check_disk_space=False) as session:
                result = session.execute(text("PRAGMA integrity_check")).fetchone()
                
                if result and result[0] == 'ok':
                    return HealthCheckResult(
                        name="sqlite_integrity",
                        status="pass",
                        severity=HealthCheckSeverity.INFO,
                        message="SQLite integrity check passed"
                    )
                else:
                    return HealthCheckResult(
                        name="sqlite_integrity",
                        status="fail",
                        severity=HealthCheckSeverity.CRITICAL,
                        message=f"SQLite integrity check failed: {result[0] if result else 'unknown'}",
                        details={"integrity_result": result[0] if result else None}
                    )
        except Exception as e:
            return HealthCheckResult(
                name="sqlite_integrity",
                status="error",
                severity=HealthCheckSeverity.ERROR,
                message=f"SQLite integrity check error: {e}"
            )
    
    def _check_sqlite_wal_health(self) -> HealthCheckResult:
        """Check SQLite WAL mode health"""
        try:
            with db_context.get_session(check_disk_space=False) as session:
                journal_mode = session.execute(text("PRAGMA journal_mode")).fetchone()
                
                if journal_mode and journal_mode[0].upper() == 'WAL':
                    # Check WAL file size
                    db_path = Path(DATABASE_URL.replace('sqlite:///', ''))
                    wal_path = db_path.with_suffix('.db-wal')
                    
                    if wal_path.exists():
                        wal_size_mb = wal_path.stat().st_size / (1024 * 1024)
                        
                        if wal_size_mb > 100:  # WAL file > 100MB
                            status, severity = "warning", HealthCheckSeverity.WARNING
                            message = f"Large WAL file: {wal_size_mb:.2f}MB"
                        else:
                            status, severity = "pass", HealthCheckSeverity.INFO
                            message = f"WAL mode active, file size: {wal_size_mb:.2f}MB"
                        
                        details = {"wal_size_mb": round(wal_size_mb, 2)}
                    else:
                        status, severity = "pass", HealthCheckSeverity.INFO
                        message = "WAL mode active, no WAL file present"
                        details = {}
                else:
                    status, severity = "warning", HealthCheckSeverity.WARNING
                    message = f"Not using WAL mode: {journal_mode[0] if journal_mode else 'unknown'}"
                    details = {"journal_mode": journal_mode[0] if journal_mode else None}
                
                return HealthCheckResult(
                    name="sqlite_wal_health",
                    status=status,
                    severity=severity,
                    message=message,
                    details=details
                )
        except Exception as e:
            return HealthCheckResult(
                name="sqlite_wal_health",
                status="error",
                severity=HealthCheckSeverity.ERROR,
                message=f"WAL health check failed: {e}"
            )
    
    def _get_enhanced_engine_info(self) -> Dict[str, Any]:
        """Get enhanced SQLAlchemy engine information"""
        try:
            pool = engine.pool
            
            return {
                "pool_size": getattr(pool, 'size', lambda: 'N/A')(),
                "pool_checked_in": getattr(pool, 'checkedin', lambda: 'N/A')(),
                "pool_checked_out": getattr(pool, 'checkedout', lambda: 'N/A')(),
                "pool_invalid": getattr(pool, 'invalidated', lambda: 'N/A')(),
                "pool_overflow": getattr(pool, 'overflow', lambda: 'N/A')(),
                "driver": str(engine.dialect.driver),
                "dialect": str(engine.dialect.name),
                "pool_class": type(pool).__name__
            }
        except Exception as e:
            logger.warning(f"Could not get enhanced engine info: {e}")
            return {"error": str(e)}
    
    def _get_enhanced_performance_metrics(self) -> Dict[str, Any]:
        """Get enhanced database performance metrics"""
        metrics = {}
        
        # Query performance test
        try:
            start_time = time.time()
            with db_context.get_session(check_disk_space=False) as session:
                session.execute(text("SELECT 1"))
                simple_query_time = (time.time() - start_time) * 1000
            
            metrics["simple_query_ms"] = round(simple_query_time, 2)
            
            if simple_query_time < 100:
                status = "responsive"
            elif simple_query_time < 500:
                status = "slow"
            else:
                status = "very_slow"
            
            metrics["query_status"] = status
        except Exception as e:
            metrics["simple_query_ms"] = -1
            metrics["query_status"] = "error"
            metrics["query_error"] = str(e)
        
        return metrics
    
    def _get_system_resource_status(self) -> Dict[str, Any]:
        """Get system resource status"""
        try:
            memory = psutil.virtual_memory()
            
            # Get disk usage for database location
            db_path = Path("db").resolve()
            if not db_path.exists():
                db_path = Path.cwd()
            disk = psutil.disk_usage(str(db_path))
            
            return {
                "memory": {
                    "usage_percent": memory.percent,
                    "available_gb": round(memory.available / (1024**3), 2),
                    "total_gb": round(memory.total / (1024**3), 2)
                },
                "disk": {
                    "usage_percent": round((disk.used / disk.total) * 100, 1),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "total_gb": round(disk.total / (1024**3), 2)
                }
            }
        except Exception as e:
            return {"error": f"Could not get system resources: {e}"}
    
    def _analyze_health_trends(self) -> Dict[str, Any]:
        """Analyze health trends from historical data"""
        if len(self.health_history) < 5:
            return {"status": "insufficient_data"}
        
        trends = {"performance": "stable"}  # Simple implementation
        return trends
    
    def _generate_recommendations(self, health_status: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on health status"""
        recommendations = []
        
        # Check health check results
        if "health_checks" in health_status:
            failed_checks = [c for c in health_status["health_checks"] if c.get("status") in ["fail", "error"]]
            warning_checks = [c for c in health_status["health_checks"] if c.get("status") == "warning"]
            
            if failed_checks:
                recommendations.append(f"Address {len(failed_checks)} failed health checks immediately")
            
            if warning_checks:
                recommendations.append(f"Review {len(warning_checks)} health check warnings")
        
        if not recommendations:
            recommendations.append("System is healthy - no immediate actions required")
        
        return recommendations
    
    def _calculate_overall_status(self, health_status: Dict[str, Any]) -> str:
        """Calculate overall health status"""
        if "health_checks" in health_status:
            checks = health_status["health_checks"]
            
            # Count severity levels
            critical_count = sum(1 for c in checks if c.get("severity") == "critical" and c.get("status") in ["fail", "error"])
            error_count = sum(1 for c in checks if c.get("severity") == "error" and c.get("status") in ["fail", "error"])
            warning_count = sum(1 for c in checks if c.get("status") == "warning")
            
            if critical_count > 0:
                return "critical"
            elif error_count > 0:
                return "unhealthy"
            elif warning_count > 2:
                return "degraded"
            elif warning_count > 0:
                return "healthy_with_warnings"
            else:
                return "healthy"
        
        return "unknown"
    
    def _process_alerts(self, health_checks: List[HealthCheckResult]):
        """Process alerts for critical issues"""
        if not self.alert_callback:
            return
        
        for check in health_checks:
            if check.status in ["fail", "error"] and check.severity in [HealthCheckSeverity.CRITICAL, HealthCheckSeverity.ERROR]:
                try:
                    self.alert_callback(check)
                except Exception as e:
                    logger.error(f"Failed to process alert for {check.name}: {e}")
    
    # Backward compatibility methods (simplified versions of the old methods)
    def _get_engine_info(self) -> Dict[str, Any]:
        """Get SQLAlchemy engine information (backward compatibility)"""
        return self._get_enhanced_engine_info()
    
    def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get database performance metrics (backward compatibility)"""
        return self._get_enhanced_performance_metrics()
    
    def _get_engine_info(self) -> Dict[str, Any]:
        """Get SQLAlchemy engine information"""
        pool = engine.pool
        return {
            "pool_size": getattr(pool, 'size', lambda: 'N/A')(),
            "pool_checked_in": getattr(pool, 'checkedin', lambda: 'N/A')(),
            "pool_checked_out": getattr(pool, 'checkedout', lambda: 'N/A')(),
            "pool_invalid": getattr(pool, 'invalidated', lambda: 'N/A')(),
            "driver": str(engine.dialect.driver),
            "dialect": str(engine.dialect.name)
        }
    
    def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get database performance metrics"""
        start_time = time.time()
        
        try:
            with db_context.get_session() as session:
                # Simple performance test
                session.execute(text("SELECT 1"))
                query_time = time.time() - start_time
                
                return {
                    "query_response_time_ms": round(query_time * 1000, 2),
                    "status": "responsive" if query_time < 0.1 else "slow" if query_time < 1.0 else "very_slow"
                }
        except Exception as e:
            return {
                "query_response_time_ms": -1,
                "status": "error",
                "error": str(e)
            }
    
    def get_health_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent health check history.
        
        Args:
            limit: Maximum number of history entries to return
            
        Returns:
            list: Recent health check results
        """
        return self.health_history[-limit:]
    
    def check_database_integrity(self) -> Dict[str, Any]:
        """
        Perform database integrity checks.
        
        Returns:
            dict: Integrity check results
        """
        results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": []
        }
        
        try:
            with db_context.get_session() as session:
                # Check if we can perform basic operations
                results["checks"].append({
                    "name": "basic_connectivity",
                    "status": "pass",
                    "message": "Database connection successful"
                })
                
                # Check if main tables exist (assuming Recording table)
                try:
                    from models.recording import Recording
                    session.query(Recording).first()
                    results["checks"].append({
                        "name": "table_accessibility",
                        "status": "pass", 
                        "message": "Main tables accessible"
                    })
                except Exception as e:
                    results["checks"].append({
                        "name": "table_accessibility",
                        "status": "fail",
                        "message": f"Table access error: {e}"
                    })
                
                # SQLite-specific integrity check
                if 'sqlite' in DATABASE_URL:
                    try:
                        result = session.execute(text("PRAGMA integrity_check")).fetchone()
                        integrity_ok = result and result[0] == 'ok'
                        results["checks"].append({
                            "name": "sqlite_integrity",
                            "status": "pass" if integrity_ok else "fail",
                            "message": f"SQLite integrity check: {result[0] if result else 'unknown'}"
                        })
                    except Exception as e:
                        results["checks"].append({
                            "name": "sqlite_integrity",
                            "status": "error",
                            "message": f"Integrity check failed: {e}"
                        })
                
        except Exception as e:
            results["checks"].append({
                "name": "basic_connectivity",
                "status": "fail",
                "message": f"Database connection failed: {e}"
            })
        
        # Overall status
        failed_checks = [c for c in results["checks"] if c["status"] in ["fail", "error"]]
        results["overall_status"] = "healthy" if not failed_checks else "unhealthy"
        results["failed_checks_count"] = len(failed_checks)
        
        logger.info(f"Database integrity check completed: {results['overall_status']}")
        return results
    
    def export_health_report(self, output_path: str = None) -> str:
        """
        Export comprehensive health report to JSON file.
        
        Args:
            output_path: Path to save the report (optional)
            
        Returns:
            str: Path to the exported report
        """
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"logs/database_health_report_{timestamp}.json"
        
        report = {
            "report_timestamp": datetime.now(timezone.utc).isoformat(),
            "current_health": self.get_comprehensive_health_status(),
            "integrity_check": self.check_database_integrity(),
            "recent_history": self.get_health_history(20)
        }
        
        # Ensure output directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Database health report exported to: {output_path}")
        return output_path


# Global health monitor instance
health_monitor = DatabaseHealthMonitor()
