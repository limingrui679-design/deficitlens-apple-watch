"""Shared deterministic test data."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from deficitlens.config import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings.model_validate(
        {
            "seed": 42,
            "data": {
                "window_seconds": 10,
                "stride_seconds": 10,
                "minimum_window_coverage": 0.5,
            },
            "model": {
                "inner_group_folds": 2,
                "calibration_group_fraction": 0.25,
                "conformal_alpha": 0.1,
                "mondrian_column": "activity_family",
                "minimum_mondrian_samples": 5,
                "minimum_mondrian_clusters": 2,
                "ensemble_models": ["ridge", "extra_trees"],
            },
            "evaluation": {
                "bootstrap_repetitions": 100,
                "subgroup_columns": ["sex", "body_fat_band", "bmi_band", "activity"],
                "decision_horizons_weeks": [4, 8],
            },
            "privacy": {},
        }
    )


@pytest.fixture
def synthetic_windows() -> pd.DataFrame:
    rng = np.random.default_rng(7)
    activities = {
        "sit": 0.1,
        "stand": 0.3,
        "cycle_low": 2.0,
        "cycle_high": 4.0,
        "run_low": 5.0,
        "run_high": 6.5,
    }
    rows: list[dict[str, object]] = []
    for participant in range(1, 7):
        weight = 55.0 + participant * 4
        age = 22.0 + participant
        sex = "F" if participant % 2 else "M"
        bmi = 21.0 + participant
        body_fat = 16.0 + 2.5 * participant
        participant_bias = (participant - 3.5) * 0.08
        time_index = 0
        for activity, base in activities.items():
            for repetition in range(4):
                target = max(base + 0.008 * (weight - 65) + rng.normal(0, 0.12), 0.0)
                apple = max(target * (1.0 + participant_bias) + rng.normal(0, 0.2), 0.0)
                hr = 65.0 + base * 16 + rng.normal(0, 3)
                rows.append(
                    {
                        "participant_id": f"S{participant:02d}",
                        "activity": activity,
                        "activity_family": "rest"
                        if activity in {"sit", "stand"}
                        else "cycling"
                        if activity.startswith("cycle")
                        else "running",
                        "window_start": pd.Timestamp("2026-01-01")
                        + pd.Timedelta(time_index * 10, unit="s"),
                        "ground_truth_active_kcal_min": target,
                        "apple_active_kcal_min": apple,
                        "apple_energy_observed_fraction": 1.0,
                        "apple_hr_mean": hr if repetition != 0 else np.nan,
                        "apple_hr_sd": 3.0 if repetition != 0 else np.nan,
                        "apple_hr_range": 8.0 if repetition != 0 else np.nan,
                        "apple_hr_slope": 0.2 if repetition != 0 else np.nan,
                        "apple_hr_mean_fraction_hrmax": hr / (208 - 0.7 * age)
                        if repetition != 0
                        else np.nan,
                        "apple_hr_missing_fraction": 0.2 if repetition != 0 else 1.0,
                        "weight_kg": weight,
                        "height_cm": 165.0 + participant,
                        "age_years": age,
                        "bmi": bmi,
                        "body_fat_pct": body_fat,
                        "mifflin_rmr_kcal_day": 1400.0 + 30 * participant,
                        "sex": sex,
                        "protocol_met": 1.0 + base,
                        "protocol_speed": base,
                        "window_elapsed_seconds": repetition * 10.0,
                        "body_fat_band": "<20" if body_fat < 20 else "20-29.9",
                        "bmi_band": "<25" if bmi < 25 else "25-29.9",
                    }
                )
                time_index += 1
    return pd.DataFrame(rows)
