"""Adapter for the 2026 Apple Watch Series 8 PAEE fairness study."""

from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from deficitlens.data.registry import checksum
from deficitlens.schemas import DatasetEvidence

COLUMN_MAP = {
    "Participant": "participant_id",
    "Gender": "sex",
    "Age": "age_years",
    "Fitzpatrick ": "fitzpatrick_skin_type",
    "BMI (Calculated)": "bmi",
    "Weight": "weight_kg",
    "Height": "height_cm",
    "BF": "body_fat_pct",
    "Wrist_Circumf": "wrist_circumference_cm",
    "Apple (Cal) ": "apple_kcal",
    "K5 (Cal)": "criterion_kcal",
}


def load_paee2026(
    workbook_path: str | Path, *, primary_analysis: bool = True
) -> tuple[pd.DataFrame, DatasetEvidence]:
    """Load Apple Watch Series 8 and COSMED K5 paired session totals.

    The primary analysis mirrors the paper's participant-level exclusion of ID 58. Raw and
    filtered flags remain in the returned frame so sensitivity analyses are explicit.
    """

    path = Path(workbook_path)
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="Sparkline Group extension is not supported and will be removed",
            category=UserWarning,
        )
        raw = pd.read_excel(path, sheet_name=0).rename(columns=COLUMN_MAP)
    missing = set(COLUMN_MAP.values()) - set(raw.columns)
    if missing:
        raise ValueError(f"PAEE 2026 workbook missing columns: {sorted(missing)}")
    frame = raw[list(COLUMN_MAP.values())].copy()
    numeric = [
        "participant_id",
        "age_years",
        "fitzpatrick_skin_type",
        "bmi",
        "weight_kg",
        "height_cm",
        "body_fat_pct",
        "wrist_circumference_cm",
        "apple_kcal",
        "criterion_kcal",
    ]
    for column in numeric:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["sex"] = frame["sex"].astype("string").str.strip().str.title()
    frame = frame.dropna(subset=["participant_id", "apple_kcal", "criterion_kcal"])
    frame["participant_id"] = (
        frame["participant_id"].astype(int).map(lambda value: f"OSF{value:03d}")
    )
    frame["analysis_code_global_exclusion"] = frame["participant_id"].eq("OSF058")
    frame["implausible_device_value"] = (frame["apple_kcal"] <= 1) | (
        frame["apple_kcal"] > 4.5 * frame["criterion_kcal"]
    )
    frame["bias_kcal"] = frame["apple_kcal"] - frame["criterion_kcal"]
    frame["absolute_error_kcal"] = frame["bias_kcal"].abs()
    frame["absolute_percentage_error"] = (
        100.0 * frame["absolute_error_kcal"] / frame["criterion_kcal"]
    )
    frame["body_fat_band"] = pd.cut(
        frame["body_fat_pct"],
        bins=[-np.inf, 20.0, 30.0, np.inf],
        labels=["<20", "20-29.9", ">=30"],
        right=False,
    ).astype(str)
    frame["bmi_band"] = pd.cut(
        frame["bmi"],
        bins=[-np.inf, 25.0, 30.0, np.inf],
        labels=["<25", "25-29.9", ">=30"],
        right=False,
    ).astype(str)

    notes = ["Primary analysis excludes participant OSF058 across devices, per paper code."]
    if primary_analysis:
        frame = frame[~frame["analysis_code_global_exclusion"] & ~frame["implausible_device_value"]]
    frame = frame.sort_values("participant_id").reset_index(drop=True)

    evidence = DatasetEvidence(
        dataset_id="apple_watch_paee_2026",
        rows=len(frame),
        participants=frame["participant_id"].nunique(),
        activities=("recumbent_cycle_mixed_intensity",),
        checksum=f"sha256:{checksum(path)}",
        source_path=str(path.resolve()),
        notes=tuple(notes),
    )
    return frame, evidence
