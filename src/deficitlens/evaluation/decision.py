"""Scenario-based translation from measurement error to fat-loss planning risk."""

from __future__ import annotations

import numpy as np
import pandas as pd


def projected_mass_error_scenarios(
    prediction_error_kcal_min: np.ndarray,
    groups: np.ndarray,
    *,
    horizons_weeks: list[int],
    kcal_per_kg: float | None = None,
    kcal_per_kg_values: tuple[float, ...] = (7700.0,),
    active_minutes_per_day: tuple[int, ...] = (30, 45, 60),
    active_days_per_week: tuple[int, ...] = (7,),
) -> pd.DataFrame:
    """Translate model bias into a bounded planning scenario.

    This is arithmetic sensitivity analysis, not a weight-loss forecast. It assumes the
    measured exercise-rate error repeats for a chosen number of minutes every day and uses a
    explicit kcal/kg conversions solely for comparability. The optional ``kcal_per_kg``
    argument preserves the original single-assumption API.
    """

    errors = np.asarray(prediction_error_kcal_min, dtype=float)
    group_values = np.asarray(groups).astype(str)
    participant_bias = (
        pd.DataFrame({"group": group_values, "error": errors}).groupby("group")["error"].mean()
    )
    energy_density_values = (float(kcal_per_kg),) if kcal_per_kg is not None else kcal_per_kg_values
    if not energy_density_values or any(value <= 0 for value in energy_density_values):
        raise ValueError("At least one positive kcal-per-kg assumption is required")
    if not active_days_per_week or any(day < 1 or day > 7 for day in active_days_per_week):
        raise ValueError("Active days per week must be between 1 and 7")
    rows: list[dict[str, float | int]] = []
    for minutes in active_minutes_per_day:
        daily = participant_bias.to_numpy(dtype=float) * minutes
        for days_per_week in active_days_per_week:
            for weeks in horizons_weeks:
                for energy_density in energy_density_values:
                    mass_error = daily * days_per_week * weeks / energy_density
                    rows.append(
                        {
                            "active_minutes_per_day": minutes,
                            "active_days_per_week": days_per_week,
                            "horizon_weeks": weeks,
                            "kcal_per_kg_assumption": energy_density,
                            "participant_count": len(participant_bias),
                            "median_projected_kg_error": float(np.median(mass_error)),
                            "median_absolute_projected_kg_error": float(
                                np.median(np.abs(mass_error))
                            ),
                            "p10_projected_kg_error": float(np.quantile(mass_error, 0.10)),
                            "p90_projected_kg_error": float(np.quantile(mass_error, 0.90)),
                        }
                    )
    return pd.DataFrame(rows)
