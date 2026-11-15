"""Unit tests for the robust z-score baseline (pure logic, no cluster needed)."""

from incident_copilot.mcp_server.anomaly.baseline import robust_zscore


def test_spike_is_flagged() -> None:
    values = [1.0, 1.1, 0.9, 1.05, 0.95, 1.0, 1.1, 0.9, 10.0]
    assert robust_zscore(values) >= 3.0


def test_stable_series_not_flagged() -> None:
    values = [1.0, 1.1, 0.9, 1.05, 0.95, 1.0, 1.1, 0.9, 1.0]
    assert robust_zscore(values) < 3.0


def test_too_short_returns_zero() -> None:
    assert robust_zscore([1.0, 2.0]) == 0.0
