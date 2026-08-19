"""WEEE adapter specialized for Apple Watch energy-expenditure validation."""

from __future__ import annotations

import io
import json
import math
from dataclasses import dataclass
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd

from deficitlens.config import DataConfig
from deficitlens.data.registry import checksum
from deficitlens.physiology import (
    KJ_PER_KCAL,
    mifflin_st_jeor_rmr_kcal_day,
    tanaka_hr_max,
    total_to_active_kcal_min,
    vo2_to_total_kcal_min,
)
from deficitlens.schemas import DatasetEvidence

PHASES = (
    ("sit", "Start_Sit", "MET_Sit", None),
    ("stand", "Start_Stand", "MET_Stand", None),
    ("cycle_low", "Start_Cycle1", "MET_Cycle1", "Cycle_Speed1"),
    ("cycle_high", "Start_Cycle2", "MET_Cycle2", "Cycle_Speed2"),
    ("run_low", "Start_Run1", "MET_Run1", "Run_Speed1"),
    ("run_high", "Start_Run2", "MET_Run2", "Run_Speed2"),
)

ACTIVITY_FAMILIES = {
    "sit": "rest",
    "stand": "rest",
    "cycle_low": "cycling",
    "cycle_high": "cycling",
    "run_low": "running",
    "run_high": "running",
}


@dataclass(frozen=True)
class ProtocolInterval:
    """One quality-checked activity interval."""

    activity: str
    start: pd.Timestamp
    end: pd.Timestamp
    met: float
    speed: float | None


def _read_csv(archive: ZipFile, name: str) -> pd.DataFrame:
    return pd.read_csv(io.BytesIO(archive.read(name)))


def load_demographics(archive: ZipFile) -> pd.DataFrame:
    """Load normalized participant demographics."""

    frame = _read_csv(archive, "dataset/Demographics.csv").rename(
        columns={
            "Participant": "participant_id",
            "BMI": "bmi",
            "Fat": "body_fat_pct",
            "Muscle": "muscle_pct",
            "Water": "water_pct",
            "Bone": "bone_pct",
            "Weight": "weight_kg",
            "Height": "height_cm",
            "Gender": "sex",
            "Age": "age_years",
        }
    )
    required = {
        "participant_id",
        "bmi",
        "body_fat_pct",
        "weight_kg",
        "height_cm",
        "sex",
        "age_years",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"WEEE demographics missing columns: {sorted(missing)}")
    frame["mifflin_rmr_kcal_day"] = frame.apply(
        lambda row: mifflin_st_jeor_rmr_kcal_day(
            weight_kg=float(row["weight_kg"]),
            height_cm=float(row["height_cm"]),
            age_years=float(row["age_years"]),
            sex=str(row["sex"]),
        ),
        axis=1,
    )
    return frame


def load_protocol(archive: ZipFile) -> pd.DataFrame:
    """Load the WEEE protocol table."""

    return _read_csv(archive, "dataset/Study_Information.csv")


def protocol_intervals(row: pd.Series) -> tuple[list[ProtocolInterval], list[str]]:
    """Build monotonic five-minute protocol intervals.

    WEEE documents known sensor loss and contains a corrupted set of post-rest timestamps for
    P14. Once a non-monotonic marker is encountered, that marker and all later phases are
    excluded rather than repaired by guessing.
    """

    parsed: list[tuple[str, pd.Timestamp, float, float | None]] = []
    notes: list[str] = []
    previous: pd.Timestamp | None = None
    for activity, start_col, met_col, speed_col in PHASES:
        raw_start = row.get(start_col)
        if raw_start is None or pd.isna(raw_start):
            notes.append(f"{activity}:missing_start")
            break
        start = pd.Timestamp(str(raw_start))
        if previous is not None and start <= previous:
            notes.append(f"{activity}:non_monotonic_start")
            break
        met = float(row[met_col])
        speed_value = row.get(speed_col) if speed_col else None
        speed = float(speed_value) if speed_value is not None and pd.notna(speed_value) else None
        parsed.append((activity, start, met, speed))
        previous = start

    intervals: list[ProtocolInterval] = []
    for index, (activity, start, met, speed) in enumerate(parsed):
        protocol_end = start + pd.Timedelta(5, unit="min")
        if index + 1 < len(parsed):
            protocol_end = min(protocol_end, parsed[index + 1][1])
        intervals.append(ProtocolInterval(activity, start, protocol_end, met, speed))
    return intervals, notes


def load_apple_watch_metrics(archive: ZipFile) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load Apple Watch Series 6 active-energy and heart-rate streams."""

    payload = json.loads(archive.read("dataset/Apple watch/HealthAutoExport.json"))["data"]
    metrics = {metric["name"]: metric for metric in payload["metrics"]}

    energy_rows = metrics["active_energy"]["data"]
    energy = pd.DataFrame(energy_rows).rename(columns={"date": "timestamp", "qty": "energy"})
    energy["timestamp"] = pd.to_datetime(energy["timestamp"], utc=True).dt.tz_localize(None)
    energy["apple_active_kcal_second"] = pd.to_numeric(energy["energy"], errors="coerce")
    if metrics["active_energy"]["units"].lower() == "kj":
        energy["apple_active_kcal_second"] /= KJ_PER_KCAL
    energy = energy.groupby("timestamp", as_index=False).agg(
        apple_active_kcal_second=("apple_active_kcal_second", "sum")
    )
    energy = energy.sort_values("timestamp")

    heart_rows = metrics["heart_rate"]["data"]
    heart = pd.DataFrame(heart_rows).rename(columns={"date": "timestamp"})
    heart["timestamp"] = pd.to_datetime(heart["timestamp"], utc=True).dt.tz_localize(None)
    if "Avg" in heart:
        heart["apple_hr_bpm"] = pd.to_numeric(heart["Avg"], errors="coerce")
    else:
        heart["apple_hr_bpm"] = pd.to_numeric(heart["qty"], errors="coerce")
    heart = heart.groupby("timestamp", as_index=False).agg(apple_hr_bpm=("apple_hr_bpm", "mean"))
    heart = heart.sort_values("timestamp")
    return energy, heart


def _assign_protocol(frame: pd.DataFrame, intervals: list[ProtocolInterval]) -> pd.DataFrame:
    result = frame.copy()
    result["activity"] = pd.NA
    result["protocol_met"] = np.nan
    result["protocol_speed"] = np.nan
    result["segment_start"] = pd.NaT
    for interval in intervals:
        mask = (result["timestamp"] >= interval.start) & (result["timestamp"] < interval.end)
        result.loc[mask, "activity"] = interval.activity
        result.loc[mask, "protocol_met"] = interval.met
        result.loc[mask, "protocol_speed"] = interval.speed
        result.loc[mask, "segment_start"] = interval.start
    return result[result["activity"].notna()].copy()


def load_weee_seconds(
    archive_path: str | Path, config: DataConfig
) -> tuple[pd.DataFrame, list[str]]:
    """Align WEEE VO2 ground truth to Apple Watch signals at one-second resolution."""

    all_frames: list[pd.DataFrame] = []
    notes: list[str] = []
    with ZipFile(archive_path) as archive:
        demographics = load_demographics(archive)
        protocol = load_protocol(archive)
        energy, heart = load_apple_watch_metrics(archive)
        demographics_by_id = demographics.set_index("participant_id")

        for _, protocol_row in protocol.iterrows():
            participant_id = str(protocol_row["Participant"])
            intervals, interval_notes = protocol_intervals(protocol_row)
            notes.extend(f"{participant_id}:{note}" for note in interval_notes)
            path = f"dataset/{participant_id}/VO2/DataAverage.csv"
            if path not in archive.namelist():
                notes.append(f"{participant_id}:missing_vo2_file")
                continue
            vo2 = _read_csv(archive, path).rename(
                columns={
                    "Time": "timestamp",
                    "VO2[mL/kg/min]": "vo2_ml_kg_min",
                    "HR[bpm]": "wahoo_hr_bpm",
                }
            )
            vo2["timestamp"] = pd.to_datetime(vo2["timestamp"], errors="coerce")
            vo2["vo2_ml_kg_min"] = pd.to_numeric(vo2["vo2_ml_kg_min"], errors="coerce")
            vo2["wahoo_hr_bpm"] = pd.to_numeric(vo2["wahoo_hr_bpm"], errors="coerce")
            vo2 = vo2.dropna(subset=["timestamp"]).sort_values("timestamp")
            vo2 = _assign_protocol(vo2, intervals)
            if vo2.empty:
                notes.append(f"{participant_id}:no_valid_protocol_rows")
                continue

            demo = demographics_by_id.loc[participant_id]
            weight = float(demo["weight_kg"])
            rmr = float(demo["mifflin_rmr_kcal_day"])
            vo2_values = vo2["vo2_ml_kg_min"].to_numpy(dtype=float)
            vo2["ground_truth_total_kcal_min"] = [
                vo2_to_total_kcal_min(
                    value,
                    weight,
                    caloric_equivalent=config.oxygen_caloric_equivalent_kcal_per_liter,
                )
                if np.isfinite(value) and value > 0
                else np.nan
                for value in vo2_values
            ]
            total_values = vo2["ground_truth_total_kcal_min"].to_numpy(dtype=float)
            vo2["ground_truth_active_kcal_min"] = [
                total_to_active_kcal_min(value, rmr) if np.isfinite(value) else np.nan
                for value in total_values
            ]

            second = vo2.merge(energy, how="left", on="timestamp")
            second["apple_energy_observed"] = second["apple_active_kcal_second"].notna()
            second["apple_active_kcal_second"] = second["apple_active_kcal_second"].fillna(0.0)
            second = pd.merge_asof(
                second.sort_values("timestamp"),
                heart,
                on="timestamp",
                direction="nearest",
                tolerance=pd.Timedelta(config.apple_hr_tolerance_seconds, unit="s"),
            )
            second["participant_id"] = participant_id
            for column in (
                "weight_kg",
                "height_cm",
                "age_years",
                "bmi",
                "body_fat_pct",
                "muscle_pct",
                "mifflin_rmr_kcal_day",
                "sex",
            ):
                second[column] = demo[column]
            all_frames.append(second)

    if not all_frames:
        raise ValueError("No valid WEEE participant data were prepared")
    combined = pd.concat(all_frames, ignore_index=True)
    return combined, notes


def _linear_slope(values: pd.Series) -> float:
    finite = values.dropna().astype(float)
    if len(finite) < 2:
        return math.nan
    x = np.arange(len(finite), dtype=float)
    return float(np.polyfit(x, finite.to_numpy(), 1)[0] * 60.0)


def _fixed_band(value: float, cutoffs: tuple[float, float], labels: tuple[str, str, str]) -> str:
    if value < cutoffs[0]:
        return labels[0]
    if value < cutoffs[1]:
        return labels[1]
    return labels[2]


def window_weee_seconds(seconds: pd.DataFrame, config: DataConfig) -> pd.DataFrame:
    """Create leakage-safe, non-overlapping or strided feature windows."""

    rows: list[dict[str, object]] = []
    grouping = ["participant_id", "activity", "segment_start"]
    for (participant_id, activity, segment_start), segment in seconds.groupby(
        grouping, observed=True, dropna=True
    ):
        segment = segment.sort_values("timestamp")
        start = pd.Timestamp(str(segment_start))
        last = segment["timestamp"].max()
        window_start = start
        while window_start <= last:
            window_end = window_start + pd.Timedelta(config.window_seconds, unit="s")
            window = segment[
                (segment["timestamp"] >= window_start) & (segment["timestamp"] < window_end)
            ]
            valid_target = window["ground_truth_active_kcal_min"].notna().sum()
            target_coverage = valid_target / config.window_seconds
            if target_coverage >= config.minimum_window_coverage:
                first = window.iloc[0]
                hr = window["apple_hr_bpm"]
                active_rate = (
                    float(window["apple_active_kcal_second"].sum()) * 60.0 / config.window_seconds
                )
                rows.append(
                    {
                        "participant_id": str(participant_id),
                        "activity": str(activity),
                        "window_start": window_start,
                        "window_end": window_end,
                        "window_elapsed_seconds": float((window_start - start).total_seconds()),
                        "target_coverage": target_coverage,
                        "ground_truth_total_kcal_min": float(
                            window["ground_truth_total_kcal_min"].mean()
                        ),
                        "ground_truth_active_kcal_min": float(
                            window["ground_truth_active_kcal_min"].mean()
                        ),
                        "apple_active_kcal_min": active_rate,
                        "apple_total_kcal_min": active_rate
                        + float(first["mifflin_rmr_kcal_day"]) / 1440.0,
                        "apple_energy_observed_fraction": float(
                            window["apple_energy_observed"].mean()
                        ),
                        "apple_hr_mean": float(hr.mean()) if hr.notna().any() else math.nan,
                        "apple_hr_sd": float(hr.std(ddof=0)) if hr.notna().sum() > 1 else math.nan,
                        "apple_hr_range": float(hr.max() - hr.min())
                        if hr.notna().sum() > 1
                        else math.nan,
                        "apple_hr_slope": _linear_slope(hr),
                        "apple_hr_mean_fraction_hrmax": float(hr.mean())
                        / tanaka_hr_max(float(first["age_years"]))
                        if hr.notna().any()
                        else math.nan,
                        "apple_hr_missing_fraction": float(hr.isna().mean()),
                        "wahoo_hr_mean": float(window["wahoo_hr_bpm"].mean()),
                        "protocol_met": float(first["protocol_met"]),
                        "protocol_speed": float(first["protocol_speed"])
                        if pd.notna(first["protocol_speed"])
                        else 0.0,
                        "weight_kg": float(first["weight_kg"]),
                        "height_cm": float(first["height_cm"]),
                        "age_years": float(first["age_years"]),
                        "bmi": float(first["bmi"]),
                        "body_fat_pct": float(first["body_fat_pct"]),
                        "muscle_pct": float(first["muscle_pct"]),
                        "mifflin_rmr_kcal_day": float(first["mifflin_rmr_kcal_day"]),
                        "sex": str(first["sex"]),
                    }
                )
            window_start += pd.Timedelta(config.stride_seconds, unit="s")

    result = pd.DataFrame(rows)
    if result.empty:
        raise ValueError("No WEEE windows met the coverage threshold")
    result["body_fat_band"] = result["body_fat_pct"].map(
        lambda value: _fixed_band(float(value), (20.0, 30.0), ("<20", "20-29.9", ">=30"))
    )
    result["bmi_band"] = result["bmi"].map(
        lambda value: _fixed_band(float(value), (25.0, 30.0), ("<25", "25-29.9", ">=30"))
    )
    result["activity_family"] = result["activity"].map(ACTIVITY_FAMILIES)
    if result["activity_family"].isna().any():
        unknown = sorted(result.loc[result["activity_family"].isna(), "activity"].unique())
        raise ValueError(f"No deployable activity-family mapping for: {unknown}")
    return result.sort_values(["participant_id", "window_start"]).reset_index(drop=True)


def build_weee_windows(
    archive_path: str | Path, config: DataConfig
) -> tuple[pd.DataFrame, DatasetEvidence]:
    """Run the full WEEE preparation pipeline and return traceable evidence."""

    seconds, notes = load_weee_seconds(archive_path, config)
    windows = window_weee_seconds(seconds, config)
    evidence = DatasetEvidence(
        dataset_id="weee",
        rows=len(windows),
        participants=windows["participant_id"].nunique(),
        activities=tuple(sorted(windows["activity"].unique())),
        checksum=f"md5:{checksum(archive_path, 'md5')}",
        source_path=str(Path(archive_path).resolve()),
        notes=tuple(sorted(set(notes))),
    )
    return windows, evidence
