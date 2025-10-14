# performance_monitor.py
# Performance monitoring and benchmarking system

import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import psutil

from voice_recorder.core.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class PerformanceMetric:
    """Data class for storing performance metrics"""

    operation_name: str
    duration: float
    memory_delta: int
    timestamp: datetime
    additional_data: Optional[Dict[str, Any]] = None


class PerformanceBenchmark:
    """Performance monitoring and benchmarking system"""

    def __init__(self):
        self.metrics: List[PerformanceMetric] = []
        self.current_operation: str = ""
        self.start_time: float = 0.0
        self.start_memory: int = 0

    @contextmanager
    def measure_operation(self, operation_name: str, **additional_data: Any):
        """Context manager to measure operation performance"""
        self.current_operation = operation_name
        self.start_time = time.time()
        self.start_memory = psutil.Process().memory_info().rss

        try:
            yield self
        finally:
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss

            metric = PerformanceMetric(
                operation_name=operation_name,
                duration=end_time - self.start_time,
                memory_delta=end_memory - self.start_memory,
                timestamp=datetime.now(),
                additional_data=additional_data or {},
            )

            self.metrics.append(metric)

            # Log performance metrics for slow operations (> 1 second)
            if metric.duration > 1.0:
                logger.warning(
                    f"Slow operation detected: {operation_name} took {metric.duration:.2f}s"
                )
            elif metric.duration > 0.5:
                logger.info(
                    f"Performance: {operation_name} completed in {metric.duration:.2f}s"
                )
            else:
                logger.debug(
                    f"Performance: {operation_name} completed in {metric.duration:.3f}s"
                )

    def add_manual_metric(
        self,
        operation_name: str,
        duration: float,
        memory_delta: int = 0,
        **additional_data,
    ):
        """Manually add a performance metric"""
        metric = PerformanceMetric(
            operation_name=operation_name,
            duration=duration,
            memory_delta=memory_delta,
            timestamp=datetime.now(),
            additional_data=additional_data or {},
        )
        self.metrics.append(metric)

    def get_metrics_by_operation(self, operation_name: str) -> List[PerformanceMetric]:
        """Get all metrics for a specific operation"""
        return [m for m in self.metrics if m.operation_name == operation_name]

    def get_average_duration(self, operation_name: str) -> float:
        """Get average duration for an operation"""
        metrics = self.get_metrics_by_operation(operation_name)
        if not metrics:
            return 0.0
        return sum(m.duration for m in metrics) / len(metrics)

    def get_memory_usage_stats(self) -> Dict[str, float]:
        """Get memory usage statistics"""
        if not self.metrics:
            return {"min": 0, "max": 0, "avg": 0}

        memory_deltas = [abs(m.memory_delta) for m in self.metrics]
        return {
            "min": min(memory_deltas) / (1024 * 1024),  # Convert to MB
            "max": max(memory_deltas) / (1024 * 1024),
            "avg": sum(memory_deltas) / len(memory_deltas) / (1024 * 1024),
        }

    def generate_report(self) -> str:
        """Generate comprehensive performance report"""
        if not self.metrics:
            return "No performance metrics collected yet."

        report = []
        report.append("🚀 PERFORMANCE BENCHMARK REPORT")
        report.append("=" * 50)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Total Operations: {len(self.metrics)}")
        report.append("")

        # Group metrics by operation
        operations: Dict[str, List[PerformanceMetric]] = {}
        for metric in self.metrics:
            if metric.operation_name not in operations:
                operations[metric.operation_name] = []
            operations[metric.operation_name].append(metric)

        # Report by operation
        for operation_name, metrics in operations.items():
            report.append(f"📊 {operation_name.upper()}")
            report.append("-" * 30)

            durations = [m.duration for m in metrics]
            memory_deltas = [
                m.memory_delta / (1024 * 1024) for m in metrics
            ]  # Convert to MB

            report.append(f"  Count: {len(metrics)}")
            report.append(
                f"  Duration - Avg: {sum(durations)/len(durations):.3f}s, Min: {min(durations):.3f}s, Max: {max(durations):.3f}s"
            )
            report.append(
                f"  Memory - Avg: {sum(memory_deltas)/len(memory_deltas):+.1f}MB, Min: {min(memory_deltas):+.1f}MB, Max: {max(memory_deltas):+.1f}MB"
            )

            # Show recent operations
            recent_metrics = sorted(metrics, key=lambda x: x.timestamp, reverse=True)[
                :3
            ]
            report.append("  Recent Operations:")
            for i, metric in enumerate(recent_metrics, 1):
                report.append(
                    f"    {i}. {metric.timestamp.strftime('%H:%M:%S')} - {metric.duration:.3f}s ({metric.memory_delta/(1024*1024):+.1f}MB)"
                )

            report.append("")

        # Overall statistics
        report.append("📈 OVERALL STATISTICS")
        report.append("-" * 30)

        all_durations = [m.duration for m in self.metrics]
        memory_stats = self.get_memory_usage_stats()

        report.append(f"  Total Runtime: {sum(all_durations):.3f}s")
        report.append(
            f"  Average Operation Duration: {sum(all_durations)/len(all_durations):.3f}s"
        )
        report.append(
            f"  Memory Usage - Avg: {memory_stats['avg']:.1f}MB, Peak: {memory_stats['max']:.1f}MB"
        )

        # Performance assessment
        report.append("")
        report.append("🎯 PERFORMANCE ASSESSMENT")
        report.append("-" * 30)

        # Check against targets from our enhancement plan
        avg_load_time = self.get_average_duration("Audio Loading")
        if avg_load_time > 0:
            if avg_load_time < 1.0:
                report.append("  ✅ Audio Loading: EXCELLENT (< 1.0s target)")
            elif avg_load_time < 3.0:
                report.append("  🟡 Audio Loading: GOOD (< 3.0s, target: < 1.0s)")
            else:
                report.append("  🔴 Audio Loading: NEEDS IMPROVEMENT (> 3.0s)")

        avg_trim_time = self.get_average_duration("Audio Trimming")
        if avg_trim_time > 0:
            if avg_trim_time < 2.0:
                report.append("  ✅ Audio Trimming: EXCELLENT (< 2.0s target)")
            elif avg_trim_time < 5.0:
                report.append("  🟡 Audio Trimming: GOOD (< 5.0s, target: < 2.0s)")
            else:
                report.append("  🔴 Audio Trimming: NEEDS IMPROVEMENT (> 5.0s)")

        if memory_stats["avg"] < 2.0:
            report.append("  ✅ Memory Usage: EXCELLENT (< 2MB average)")
        elif memory_stats["avg"] < 10.0:
            report.append("  🟡 Memory Usage: GOOD (< 10MB average)")
        else:
            report.append("  🔴 Memory Usage: HIGH (> 10MB average)")

        return "\n".join(report)

    def export_csv(self, filename: Optional[str] = None) -> str:
        """Export metrics to CSV file"""
        if filename is None:
            filename = (
                f"performance_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            )

        import csv

        with open(filename, "w", newline="", encoding="utf-8") as csvfile:
            fieldnames = [
                "timestamp",
                "operation",
                "duration_s",
                "memory_delta_mb",
                "additional_data",
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for metric in self.metrics:
                writer.writerow(
                    {
                        "timestamp": metric.timestamp.isoformat(),
                        "operation": metric.operation_name,
                        "duration_s": metric.duration,
                        "memory_delta_mb": metric.memory_delta / (1024 * 1024),
                        "additional_data": (
                            str(metric.additional_data)
                            if metric.additional_data
                            else ""
                        ),
                    }
                )

        return filename

    def clear_metrics(self):
        """Clear all collected metrics"""
        self.metrics.clear()

    def get_current_system_info(self) -> Dict[str, Any]:
        """Get current system performance information"""
        process = psutil.Process()

        return {
            "cpu_percent": process.cpu_percent(),
            "memory_mb": process.memory_info().rss / (1024 * 1024),
            "memory_percent": process.memory_percent(),
            "num_threads": process.num_threads(),
            "system_cpu": psutil.cpu_percent(interval=0.1),
            "system_memory": psutil.virtual_memory().percent,
            "timestamp": datetime.now().isoformat(),
        }


# Global performance monitor instance
performance_monitor = PerformanceBenchmark()


def benchmark_operation(operation_name: str, **additional_data):
    """Decorator for benchmarking function operations"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            with performance_monitor.measure_operation(
                operation_name, **additional_data
            ):
                return func(*args, **kwargs)

        return wrapper

    return decorator


# Convenience functions
def start_monitoring():
    """Start performance monitoring"""
    performance_monitor.clear_metrics()
    return performance_monitor


def get_performance_report() -> str:
    """Get current performance report"""
    return performance_monitor.generate_report()


def save_performance_report(filename: Optional[str] = None) -> str:
    """Save performance report to file"""
    if filename is None:
        filename = f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(performance_monitor.generate_report())

    return filename
