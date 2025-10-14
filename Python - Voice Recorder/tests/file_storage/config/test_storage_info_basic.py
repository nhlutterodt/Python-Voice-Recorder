"""
Basic tests for Storage Info Module - Phase 4
"""

from pathlib import Path

from services.file_storage.config.storage_info import (
    StorageInfoCollector,
    StorageMetrics,
)


def test_storage_info_collector_initialization():
    """Test StorageInfoCollector initialization"""
    collector = StorageInfoCollector(Path("."))

    assert collector.base_path == Path(".")
    print("✅ StorageInfoCollector initialization test passed")


def test_get_raw_storage_info():
    """Test raw storage info collection"""
    collector = StorageInfoCollector(Path("."))

    info = collector.get_raw_storage_info()

    # Check that we get basic storage info
    assert "free_mb" in info
    assert "total_mb" in info
    assert "used_mb" in info
    assert "base_path" in info
    assert "method" in info

    # Check that values are reasonable
    assert info["free_mb"] >= 0
    assert info["total_mb"] > 0
    assert info["used_mb"] >= 0

    # Check consistency (approximately)
    total_calculated = info["free_mb"] + info["used_mb"]
    assert (
        abs(total_calculated - info["total_mb"]) < 1.0
    )  # Allow small rounding differences

    print("✅ Raw storage info test passed")


def test_get_storage_info():
    """Test enhanced storage info collection"""
    collector = StorageInfoCollector(Path("."))

    info = collector.get_storage_info()

    # Check that we get enhanced storage info
    assert "free_mb" in info
    assert "total_mb" in info
    assert "used_mb" in info
    assert "platform" in info
    assert "path_info" in info
    assert "health" in info
    assert "performance" in info
    assert "collection_timestamp" in info

    # Check that basic values are reasonable
    assert info["free_mb"] >= 0
    assert info["total_mb"] > 0
    assert info["used_mb"] >= 0

    print("✅ Enhanced storage info test passed")


def test_storage_metrics_initialization():
    """Test StorageMetrics initialization"""
    collector = StorageInfoCollector(Path("."))
    metrics = StorageMetrics(collector)

    assert metrics.info_collector == collector
    print("✅ StorageMetrics initialization test passed")


def test_storage_metrics_collection():
    """Test storage metrics collection"""
    collector = StorageInfoCollector(Path("."))
    metrics = StorageMetrics(collector)

    collected_metrics = metrics.collect_metrics()

    # Check that we get metrics
    assert "timestamp" in collected_metrics
    assert "free_mb" in collected_metrics
    assert "used_mb" in collected_metrics
    assert "total_mb" in collected_metrics
    assert "utilization_percent" in collected_metrics
    assert "statistics" in collected_metrics

    print("✅ Storage metrics collection test passed")


def test_cache_management():
    """Test cache management"""
    collector = StorageInfoCollector(Path("."))

    # Test setting cache TTL
    collector.set_cache_ttl(60)

    # Test clearing cache
    collector.clear_cache()

    print("✅ Cache management test passed")


if __name__ == "__main__":
    """Run basic tests"""
    try:
        test_storage_info_collector_initialization()
        test_get_raw_storage_info()
        test_get_storage_info()
        test_storage_metrics_initialization()
        test_storage_metrics_collection()
        test_cache_management()
        print("\n🎉 All basic storage info tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise
