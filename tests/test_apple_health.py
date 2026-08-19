from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from deficitlens.data.apple_health import (
    is_apple_watch_source,
    iter_apple_health_workouts,
    parse_apple_health_records,
    parse_health_date,
    strip_healthkit_prefix,
    write_normalized_records_csv,
)
from deficitlens.personal import daily_apple_health_summary, energy_uncertainty_scenario


def sample_xml() -> Path:
    return Path(__file__).resolve().parents[1] / "examples" / "apple_health_sample.xml"


def test_apple_health_filter_units_redaction_and_local_day(tmp_path: Path) -> None:
    records = parse_apple_health_records(sample_xml(), salt="test")
    assert len(records) == 6
    assert set(records["source"].str.len()) == {16}
    assert records["is_apple_watch"].all()
    energy = records[records["record_type"] == "ActiveEnergyBurned"]
    assert energy["value"].sum() == pytest.approx(7.2)
    daily = daily_apple_health_summary(records)
    assert daily["date"].astype(str).tolist() == ["2026-08-18"]
    assert daily.loc[0, "active_energy_kcal"] == pytest.approx(7.2)
    scenarios = energy_uncertainty_scenario(daily)
    assert len(scenarios) == 4
    assert scenarios["observed_active_energy_kcal"].eq(7.2).all()

    csv_path = tmp_path / "normalized.csv"
    assert write_normalized_records_csv(sample_xml(), csv_path) == 6
    assert len(pd.read_csv(csv_path)) == 6


def test_workout_and_helpers() -> None:
    workouts = list(iter_apple_health_workouts(sample_xml(), salt="test"))
    assert len(workouts) == 1
    assert workouts[0]["activity_type"] == "Running"
    assert workouts[0]["total_energy_kcal"] == 240.0
    assert workouts[0]["statistics"]["HeartRate_average"] == 142.0
    assert strip_healthkit_prefix("HKQuantityTypeIdentifierHeartRate") == "HeartRate"
    assert is_apple_watch_source({"device": "Watch7,1"})
    assert not is_apple_watch_source({"sourceName": "Chest Strap"})
    with pytest.raises(ValueError):
        parse_health_date("20 August 2026")


def test_empty_daily_and_missing_columns() -> None:
    assert daily_apple_health_summary(
        pd.DataFrame(columns=["record_type", "start_time", "value"])
    ).empty
    with pytest.raises(ValueError):
        daily_apple_health_summary(pd.DataFrame({"value": [1]}))
    with pytest.raises(ValueError):
        energy_uncertainty_scenario(pd.DataFrame({"steps": [1]}))
