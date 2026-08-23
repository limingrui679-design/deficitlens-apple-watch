"""Participant-clustered uncertainty for repeated wearable measurements."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np
from numpy.typing import NDArray

Metric = Callable[[NDArray[np.float64], NDArray[np.float64]], float]


def clustered_bootstrap_interval(
    target: NDArray[np.float64],
    prediction: NDArray[np.float64],
    groups: NDArray[Any],
    metric: Metric,
    *,
    repetitions: int,
    seed: int,
    confidence: float = 0.95,
) -> dict[str, float | int]:
    """Bootstrap whole participants, preserving their within-person correlation."""

    y = np.asarray(target, dtype=float)
    p = np.asarray(prediction, dtype=float)
    group_values = np.asarray(groups).astype(str)
    unique = np.unique(group_values)
    if len(unique) < 2:
        raise ValueError("Cluster bootstrap requires at least two participant groups")
    if repetitions < 100:
        raise ValueError("At least 100 bootstrap repetitions are required")
    rng = np.random.default_rng(seed)
    values = np.empty(repetitions, dtype=float)
    indices = {group: np.flatnonzero(group_values == group) for group in unique}
    for repetition in range(repetitions):
        sampled = rng.choice(unique, size=len(unique), replace=True)
        sample_index = np.concatenate([indices[group] for group in sampled])
        values[repetition] = metric(y[sample_index], p[sample_index])
    tail = (1.0 - confidence) / 2.0
    return {
        "estimate": float(metric(y, p)),
        "lower": float(np.quantile(values, tail)),
        "upper": float(np.quantile(values, 1.0 - tail)),
        "confidence": confidence,
        "repetitions": repetitions,
        "clusters": len(unique),
    }


def mae(target: NDArray[np.float64], prediction: NDArray[np.float64]) -> float:
    """Mean absolute error helper for bootstrap calls."""

    return float(np.mean(np.abs(np.asarray(prediction) - np.asarray(target))))


def mean_bias(target: NDArray[np.float64], prediction: NDArray[np.float64]) -> float:
    """Mean prediction-minus-criterion bias helper for bootstrap calls."""

    return float(np.mean(np.asarray(prediction) - np.asarray(target)))
