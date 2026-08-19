"""Local-only Apple Health summaries and bounded planning scenarios."""

from __future__ import annotations

import pandas as pd


def daily_apple_health_summary(records: pd.DataFrame) -> pd.DataFrame:
    """Aggregate normalized records to privacy-safer daily features.

    Raw timestamps, record IDs, device strings, and source hashes are intentionally omitted.
    Energy and steps are summed, while heart-rate quantities are summarized as distributions.
    """

    required = {"record_type", "start_time", "value"}
    missing = required - set(records.columns)
    if missing:
        raise ValueError(f"Apple Health records missing columns: {sorted(missing)}")
    if records.empty:
        return pd.DataFrame()
    frame = records.copy()
    # Preserve the local calendar day encoded in each HealthKit timestamp. Converting to UTC
    # first can incorrectly move early-morning workouts to the previous day.
    frame["date"] = frame["start_time"].map(lambda value: pd.Timestamp(value).date())
    additive = {
        "ActiveEnergyBurned": "active_energy_kcal",
        "BasalEnergyBurned": "basal_energy_kcal",
        "StepCount": "steps",
        "DistanceWalkingRunning": "walking_running_distance",
    }
    output = pd.DataFrame(index=pd.Index(sorted(frame["date"].unique()), name="date"))
    for record_type, column in additive.items():
        subset = frame[frame["record_type"] == record_type]
        output[column] = subset.groupby("date")["value"].sum()

    heart = frame[frame["record_type"] == "HeartRate"]
    output["heart_rate_mean_bpm"] = heart.groupby("date")["value"].mean()
    output["heart_rate_p05_bpm"] = heart.groupby("date")["value"].quantile(0.05)
    output["heart_rate_p95_bpm"] = heart.groupby("date")["value"].quantile(0.95)
    output["heart_rate_samples"] = heart.groupby("date")["value"].size()
    output["record_count"] = frame.groupby("date")["value"].size()
    numeric = output.columns
    output[numeric] = output[numeric].fillna(0.0)
    return output.reset_index()


def energy_uncertainty_scenario(
    daily: pd.DataFrame,
    *,
    relative_error_rates: tuple[float, ...] = (-0.20, -0.10, 0.10, 0.20),
) -> pd.DataFrame:
    """Show how assumed Apple active-energy error changes cumulative totals.

    The result is a sensitivity table, not an inferred correction. Positive error means Apple
    overestimates true active energy, so the corrected total is smaller.
    """

    if "active_energy_kcal" not in daily:
        raise ValueError("daily summary lacks active_energy_kcal")
    observed = float(daily["active_energy_kcal"].sum())
    rows: list[dict[str, float]] = []
    for relative_error in relative_error_rates:
        corrected = observed / (1.0 + relative_error)
        rows.append(
            {
                "assumed_apple_relative_error": relative_error,
                "observed_active_energy_kcal": observed,
                "scenario_corrected_active_energy_kcal": corrected,
                "difference_kcal": observed - corrected,
            }
        )
    return pd.DataFrame(rows)
