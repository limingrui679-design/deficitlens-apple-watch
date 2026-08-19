"""Scenario-based translation from measurement error to fat-loss planning risk."""

from __future__ import annotations

import numpy as np
import pandas as pd


def projected_mass_error_scenarios(
    prediction_error_kcal_min: np.ndarray,
    groups: np.ndarray,
    *,
    horizons_weeks: list[int],
    kcal_per_kg: float,
    active_minutes_per_day: tuple[int, ...] = (30, 45, 60),
) -> pd.DataFrame:
    """Translate model bias into a bounded planning scenario.

    This is arithmetic sensitivity analysis, not a weight-loss forecast. It assumes the
    measured exercise-rate error repeats for a chosen number of minutes every day and uses a
    fixed kcal/kg conversion solely for comparability.
    """

    errors = np.asarray(prediction_error_kcal_min, dtype=float)
    group_values = np.asarray(groups).astype(str)
    participant_bias = (
        pd.DataFrame({"group": group_values, "error": errors}).groupby("group")["error"].mean()
    )
    rows: list[dict[str, float | int]] = []
    for minutes in active_minutes_per_day:
        daily = participant_bias.to_numpy(dtype=float) * minutes
        for weeks in horizons_weeks:
            mass_error = daily * 7.0 * weeks / kcal_per_kg
            rows.append(
                {
                    "active_minutes_per_day": minutes,
                    "horizon_weeks": weeks,
                    "median_projected_kg_error": float(np.median(mass_error)),
                    "median_absolute_projected_kg_error": float(np.median(np.abs(mass_error))),
                    "p10_projected_kg_error": float(np.quantile(mass_error, 0.10)),
                    "p90_projected_kg_error": float(np.quantile(mass_error, 0.90)),
                }
            )
    return pd.DataFrame(rows)
