"""Transparent benchmark baselines."""

from __future__ import annotations

from typing import cast

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from deficitlens.physiology import MINUTES_PER_DAY


def apple_raw(frame: pd.DataFrame) -> NDArray[np.float64]:
    """Return Apple Watch active-energy rate without post-processing."""

    return frame["apple_active_kcal_min"].to_numpy(dtype=float)


def protocol_met(frame: pd.DataFrame) -> NDArray[np.float64]:
    """Convert protocol METs to an active-energy estimate.

    This is a protocol-informed comparator, not a deployable Apple Health model. The resting
    component is estimated with the same documented RMR equation used to align the criterion.
    """

    total = (
        frame["protocol_met"].to_numpy(dtype=float)
        * 3.5
        * frame["weight_kg"].to_numpy(dtype=float)
        / 200.0
    )
    resting = frame["mifflin_rmr_kcal_day"].to_numpy(dtype=float) / MINUTES_PER_DAY
    return cast(NDArray[np.float64], np.maximum(total - resting, 0.0))


def cohort_affine_fit(
    frame: pd.DataFrame, target: NDArray[np.float64], *, ridge: float = 1e-6
) -> tuple[float, float]:
    """Fit a stable affine correction to Apple energy on training participants only."""

    apple = frame["apple_active_kcal_min"].to_numpy(dtype=float)
    design = np.column_stack([np.ones(len(apple)), apple])
    penalty = np.diag([0.0, ridge])
    coefficients = np.linalg.solve(design.T @ design + penalty, design.T @ target)
    return float(coefficients[0]), float(coefficients[1])


def cohort_affine_predict(
    frame: pd.DataFrame, intercept: float, slope: float
) -> NDArray[np.float64]:
    """Apply an affine Apple-energy correction and enforce a physiological zero floor."""

    prediction = intercept + slope * frame["apple_active_kcal_min"].to_numpy(dtype=float)
    return cast(NDArray[np.float64], np.maximum(prediction, 0.0))
