import pytest
from logdrift.log_aggregator import AggregationBucket, AggregationConfig, LogAggregator
from logdrift.aggregator_integration import AggregatorIntegration


class FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self._t = start

    def __call__(self) -> float:
        return self._t

    def advance(self, seconds: float) -> None:
        self._t += seconds


def _make_aggregator(window: float = 10.0, max_buckets: int = 50, clock=None):
    config = AggregationConfig(window_seconds=window, max_buckets=max_buckets)
    key_fn = lambda line: line.split()[0] if line.split() else "_"
    clk = clock or FakeClock()
    return LogAggregator(config=config, key_fn=key_fn, clock=clk), clk


class TestAggregationConfig:
    def test_invalid_window_raises(self):
        with pytest.raises(ValueError):
            AggregationConfig(window_seconds=0)

    def test_invalid_max_buckets_raises(self):
        with pytest.raises(ValueError):
            AggregationConfig(max_buckets=0)

    def test_valid_config_does_not_raise(self):
        cfg = AggregationConfig(window_seconds=30.0, max_buckets=20)
        assert cfg.window_seconds == 30.0


class TestLogAggregator:
    def test_record_creates_bucket(self):
        agg, _ = _make_aggregator()
        bucket = agg.record("ERROR something happened")
        assert bucket.key == "ERROR"
        assert bucket.count == 1

    def test_same_key_increments_count(self):
        agg, _ = _make_aggregator()
        agg.record("ERROR first")
        bucket = agg.record("ERROR second")
        assert bucket.count == 2

    def test_different_keys_tracked_separately(self):
        agg, _ = _make_aggregator()
        agg.record("ERROR one")
        agg.record("WARN two")
        assert agg.total_keys == 2

    def test_expired_buckets_are_evicted(self):
        agg, clock = _make_aggregator(window=5.0)
        agg.record("ERROR old")
        clock.advance(10.0)
        agg.record("INFO new")
        assert agg.total_keys == 1

    def test_snapshot_sorted_by_count_desc(self):
        agg, _ = _make_aggregator()
        for _ in range(3):
            agg.record("WARN msg")
        agg.record("ERROR msg")
        snap = agg.snapshot()
        assert snap[0].key == "WARN"
        assert snap[0].count == 3

    def test_max_buckets_drops_oldest(self):
        agg, clock = _make_aggregator(max_buckets=2)
        agg.record("A line")
        clock.advance(1.0)
        agg.record("B line")
        clock.advance(1.0)
        agg.record("C line")  # should evict A
        assert agg.total_keys == 2

    def test_callback_is_called_on_record(self):
        agg, _ = _make_aggregator()
        received = []
        agg.add_callback(received.append)
        agg.record("ERROR test")
        assert len(received) == 1
        assert received[0].key == "ERROR"


class TestAggregatorIntegration:
    def test_total_processed_increments(self):
        clock = FakeClock()
        integration = AggregatorIntegration.from_config(key_fn=lambda l: l[:3])
        integration.process("ERR something")
        integration.process("WRN something")
        assert integration.total_processed == 2

    def test_top_returns_limited_results(self):
        clock = FakeClock()
        integration = AggregatorIntegration.from_config(key_fn=lambda l: l.split()[0])
        for _ in range(5):
            integration.process("A msg")
        integration.process("B msg")
        top = integration.top(n=1)
        assert len(top) == 1
        assert top[0].key == "A"

    def test_process_batch_returns_all_buckets(self):
        integration = AggregatorIntegration.from_config(key_fn=lambda l: l.split()[0])
        results = integration.process_batch(["X line", "Y line", "X again"])
        assert len(results) == 3
