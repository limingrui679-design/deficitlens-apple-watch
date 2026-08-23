"""Numerically explicit regression and agreement metrics."""

from __future__ import annotations

import math

import numpy as np
from numpy.typing import NDArray


def concordance_correlation_coefficient(
    target: NDArray[np.float64], prediction: NDArray[np.float64]
) -> float:
    """Return Lin's concordance correlation coefficient."""

    y = np.asarray(target, dtype=float)
    p = np.asarray(prediction, dtype=float)
    if len(y) < 2:
        return math.nan
    covariance = float(np.mean((y - y.mean()) * (p - p.mean())))
    denominator = float(y.var() + p.var() + (y.mean() - p.mean()) ** 2)
    return 2.0 * covariance / denominator if denominator > 0 else math.nan


def regression_metrics(
    target: NDArray[np.float64],
    prediction: NDArray[np.float64],
    *,
    mape_floor: float = 0.5,
) -> dict[str, float | int]:
    """Compute error, agreement, and threshold metrics.

    MAPE excludes criterion values below ``mape_floor`` because percentage error is unstable
    near rest. The retained count is reported, so the denominator is never hidden.
    """

    y = np.asarray(target, dtype=float)
    p = np.asarray(prediction, dtype=float)
    finite = np.isfinite(y) & np.isfinite(p)
    y = y[finite]
    p = p[finite]
    if len(y) == 0:
        raise ValueError("No finite target/prediction pairs")
    error = p - y
    absolute = np.abs(error)
    percentage_mask = np.abs(y) >= mape_floor
    percentage = absolute[percentage_mask] / np.abs(y[percentage_mask])
    target_ss = float(np.sum(np.square(y - y.mean())))
    residual_ss = float(np.sum(np.square(error)))
    return {
        "n": len(y),
        "mae": float(absolute.mean()),
        "rmse": float(np.sqrt(np.mean(np.square(error)))),
        "mean_bias": float(error.mean()),
        "median_absolute_error": float(np.median(absolute)),
        "mape": float(100.0 * percentage.mean()) if len(percentage) else math.nan,
        "mape_n": int(percentage_mask.sum()),
        "r2": 1.0 - residual_ss / target_ss if target_ss > 0 else math.nan,
        "ccc": concordance_correlation_coefficient(y, p),
        "within_0_5_kcal_min": float(np.mean(absolute <= 0.5)),
        "within_1_kcal_min": float(np.mean(absolute <= 1.0)),
    }


def agreement_metrics(
    target: NDArray[np.float64], prediction: NDArray[np.float64]
) -> dict[str, float]:
    """Return Bland-Altman bias and 95% limits of agreement."""

    difference = np.asarray(prediction, dtype=float) - np.asarray(target, dtype=float)
    difference = difference[np.isfinite(difference)]
    if len(difference) < 2:
        raise ValueError("At least two finite pairs are required")
    bias = float(difference.mean())
    sd = float(difference.std(ddof=1))
    return {
        "bland_altman_bias": bias,
        "bland_altman_lower_loa": bias - 1.96 * sd,
        "bland_altman_upper_loa": bias + 1.96 * sd,
    }


def interval_metrics(
    target: NDArray[np.float64],
    lower: NDArray[np.float64],
    upper: NDArray[np.float64],
) -> dict[str, float | int]:
    """Compute marginal coverage, width, and one-sided miss rates."""

    y = np.asarray(target, dtype=float)
    lo = np.asarray(lower, dtype=float)
    hi = np.asarray(upper, dtype=float)
    finite = np.isfinite(y) & np.isfinite(lo) & np.isfinite(hi)
    y, lo, hi = y[finite], lo[finite], hi[finite]
    if len(y) == 0:
        raise ValueError("No finite intervals")
    return {
        "n": len(y),
        "coverage": float(np.mean((y >= lo) & (y <= hi))),
        "mean_width": float(np.mean(hi - lo)),
        "below_interval": float(np.mean(y < lo)),
        "above_interval": float(np.mean(y > hi)),
    }
