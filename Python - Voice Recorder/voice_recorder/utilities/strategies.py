"""Multi-strategy retry pattern executor.

Provides tools for executing multiple strategies sequentially until one succeeds,
with comprehensive error accumulation and reporting.

NO DUPLICATION of existing utilities:
- error_boundaries.py handles error context and Sentry integration
- performance_monitor.py handles operation measurement
- logging_config.py handles logging

This module complements those by providing:
- StrategyExecutor: Orchestrates sequential strategy execution
- StrategyResult: Encapsulates single strategy result
- @retry_with_strategies: Decorator for function-level retries
"""

from dataclasses import dataclass
from typing import Any, Callable, List, Optional, Tuple

from voice_recorder.core.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class StrategyResult:
    """Result of a single strategy execution.
    
    Attributes:
        name: Strategy name
        success: Whether the strategy succeeded
        value: The result value (if successful)
        error: Error message (if failed)
    """
    
    name: str
    success: bool
    value: Any = None
    error: Optional[str] = None


class StrategyExecutor:
    """Execute multiple strategies sequentially until one succeeds.
    
    Strategies are attempted in order, with short-circuit on first success.
    All errors are accumulated for reporting.
    
    Example:
        executor = StrategyExecutor()
        strategies = [
            ("Try JSON", self._try_json),
            ("Try YAML", self._try_yaml),
            ("Try CSV", self._try_csv),
        ]
        
        result = executor.execute_strategies(
            strategies,
            on_progress=lambda msg: print(msg)
        )
        
        if result is None:
            print(executor.get_error_summary())
    """
    
    def __init__(self):
        """Initialize the strategy executor."""
        self.results: List[StrategyResult] = []
        self.successful_strategy: Optional[str] = None
    
    def execute_strategies(
        self,
        strategies: List[Tuple[str, Callable[[], Any]]],
        on_progress: Optional[Callable[[int, str], None]] = None,
    ) -> Optional[Any]:
        """Execute strategies sequentially until one succeeds.
        
        Args:
            strategies: List of (name, callable) tuples
                Each callable should take no arguments and return result on success
                or raise an exception on failure
            on_progress: Optional callback for progress updates (index, message)
        
        Returns:
            The value from the first successful strategy, or None if all failed
        """
        self.results.clear()
        self.successful_strategy = None
        
        for idx, (name, strategy_func) in enumerate(strategies):
            try:
                if on_progress:
                    on_progress(
                        int((idx / len(strategies)) * 100),
                        f"Attempting strategy: {name}"
                    )
                
                result = strategy_func()
                
                strategy_result = StrategyResult(
                    name=name,
                    success=True,
                    value=result,
                    error=None
                )
                self.results.append(strategy_result)
                self.successful_strategy = name
                
                logger.info(f"Strategy '{name}' succeeded")
                return result
            
            except Exception as e:
                error_msg = str(e)
                strategy_result = StrategyResult(
                    name=name,
                    success=False,
                    value=None,
                    error=error_msg
                )
                self.results.append(strategy_result)
                
                logger.debug(f"Strategy '{name}' failed: {error_msg}")
        
        # All strategies failed
        logger.warning(f"All {len(strategies)} strategies failed")
        return None
    
    def get_error_summary(self) -> str:
        """Get a human-readable summary of all errors.
        
        Returns:
            Formatted error summary
        """
        if not self.results:
            return "No strategies executed"
        
        summary_lines = [f"Strategy execution summary ({len(self.results)} attempted):"]
        
        for result in self.results:
            if result.success:
                summary_lines.append(f"  ✓ {result.name}: SUCCESS")
            else:
                summary_lines.append(f"  ✗ {result.name}: {result.error}")
        
        return "\n".join(summary_lines)
    
    def get_successful_strategy(self) -> Optional[str]:
        """Get the name of the successful strategy, if any.
        
        Returns:
            Strategy name or None if all failed
        """
        return self.successful_strategy


def retry_with_strategies(*strategies_info: Tuple[str, Callable]) -> Callable:
    """Decorator to retry a function with multiple strategies.
    
    Args:
        *strategies_info: Variable number of (name, strategy_func) tuples
    
    Returns:
        Decorated function
    
    Example:
        @retry_with_strategies(
            ("load_json", load_json_func),
            ("load_yaml", load_yaml_func),
            ("load_csv", load_csv_func),
        )
        def load_config(self, filepath):
            pass
    """
    
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            executor = StrategyExecutor()
            
            # Create strategies list
            strategies = list(strategies_info)
            
            # Execute strategies
            result = executor.execute_strategies(strategies)
            
            if result is None:
                raise RuntimeError(
                    f"All strategies failed for {func.__name__}:\n"
                    f"{executor.get_error_summary()}"
                )
            
            return result
        
        return wrapper
    
    return decorator
