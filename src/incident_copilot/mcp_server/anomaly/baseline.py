"""Robust z-score baseline: how far the latest point sits from the window's norm.

Uses median + MAD (median absolute deviation) instead of mean + std, so a single
spike doesn't poison the baseline. The Isolation Forest detector (trained on a
recorded fault-free period) is a separate, evaluated component; this is the cheap
always-available method the live `detect_anomalies` tool uses.
"""

from __future__ import annotations

import statistics

_MAD_TO_STD = 1.4826  # scale factor so MAD approximates std for normal data


def robust_zscore(values: list[float]) -> float:
    """|z| of the latest value vs the median/MAD of the preceding points."""
    if len(values) < 4:
        return 0.0
    history = values[:-1]
    latest = values[-1]
    median = statistics.median(history)
    mad = statistics.median([abs(v - median) for v in history])
    if mad == 0:
        # No variation in history: flag only if the latest point moved at all.
        return 0.0 if latest == median else 3.0
    return abs(latest - median) / (_MAD_TO_STD * mad)
