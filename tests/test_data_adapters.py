from __future__ import annotations

import io
import json
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import pytest

from deficitlens.config import DataConfig
from deficitlens.data.paee2026 import load_paee2026
from deficitlens.data.registry import checksum, load_registry, verify_checksum
from deficitlens.data.weee import build_weee_windows, protocol_intervals


def _write_csv(archive: ZipFile, name: str, frame: pd.DataFrame) -> None:
    buffer = io.StringIO()
    frame.to_csv(buffer, index=False)
    archive.writestr(name, buffer.getvalue())


def test_weee_tiny_archive_and_protocol_guard(tmp_path: Path) -> None:
    archive_path = tmp_path / "tiny.zip"
    starts = pd.date_range("2026-01-01 08:00:00", periods=6, freq="5min")
    study = pd.DataFrame(
        [
            {
                "Participant": "P01",
                "Start_Sit": starts[0],
                "MET_Sit": 1,
                "Start_Stand": starts[1],
                "MET_Stand": 1.2,
                "Start_Cycle1": starts[2],
                "MET_Cycle1": 6,
                "Cycle_Speed1": 50,
                "Start_Cycle2": starts[3],
                "MET_Cycle2": 10,
                "Cycle_Speed2": 80,
                "Start_Run1": starts[4],
                "MET_Run1": 8,
                "Run_Speed1": 7,
                "Start_Run2": starts[5],
                "MET_Run2": 12,
                "Run_Speed2": 10,
            }
        ]
    )
    demographics = pd.DataFrame(
        [
            {
                "Participant": "P01",
                "BMI": 23,
                "Fat": 20,
                "Muscle": 40,
                "Water": 55,
                "Bone": 3,
                "Weight": 70,
                "Height": 175,
                "Gender": "M",
                "Age": 30,
            }
        ]
    )
    seconds = pd.date_range(starts[0], periods=10, freq="s")
    vo2 = pd.DataFrame({"Time": seconds, "VO2[mL/kg/min]": [8.0] * 10, "HR[bpm]": range(80, 90)})
    payload = {
        "data": {
            "metrics": [
                {
                    "name": "active_energy",
                    "units": "kJ",
                    "data": [{"date": str(timestamp), "qty": 0.4184} for timestamp in seconds],
                },
                {
                    "name": "heart_rate",
                    "units": "bpm",
                    "data": [{"date": str(timestamp), "Avg": 85} for timestamp in seconds],
                },
            ]
        }
    }
    with ZipFile(archive_path, "w") as archive:
        _write_csv(archive, "dataset/Demographics.csv", demographics)
        _write_csv(archive, "dataset/Study_Information.csv", study)
        _write_csv(archive, "dataset/P01/VO2/DataAverage.csv", vo2)
        archive.writestr("dataset/Apple watch/HealthAutoExport.json", json.dumps(payload))

    windows, evidence = build_weee_windows(
        archive_path,
        DataConfig(window_seconds=5, stride_seconds=5, minimum_window_coverage=0.8),
    )
    assert len(windows) == 2
    assert evidence.participants == 1
    assert windows["apple_active_kcal_min"].iloc[0] == pytest.approx(6.0)
    assert windows["ground_truth_active_kcal_min"].gt(0).all()

    bad = study.iloc[0].copy()
    bad["Start_Cycle1"] = starts[0]
    intervals, notes = protocol_intervals(bad)
    assert [interval.activity for interval in intervals] == ["sit", "stand"]
    assert notes == ["cycle_low:non_monotonic_start"]


def test_paee_primary_and_sensitivity(tmp_path: Path) -> None:
    workbook = tmp_path / "paee.xlsx"
    rows = []
    for participant in (1, 2, 58):
        rows.append(
            {
                "Participant": participant,
                "Gender": " Female " if participant % 2 else "Male ",
                "Age": 30,
                "Fitzpatrick ": 4,
                "BMI (Calculated)": 26,
                "Weight": 70,
                "Height": 170,
                "BF": 28,
                "Wrist_Circumf": 17,
                "Apple (Cal) ": 230 if participant == 58 else 100 + participant,
                "K5 (Cal)": 55 if participant == 58 else 90 + participant,
            }
        )
    pd.DataFrame(rows).to_excel(workbook, index=False)
    all_rows, _ = load_paee2026(workbook, primary_analysis=False)
    primary, evidence = load_paee2026(workbook)
    assert len(all_rows) == 3
    assert len(primary) == 2
    assert set(primary["sex"].astype(str)) == {"Female", "Male"}
    assert evidence.participants == 2


def test_registry_checksum_and_validation(tmp_path: Path) -> None:
    payload = tmp_path / "payload.bin"
    payload.write_bytes(b"deficitlens")
    digest = checksum(payload)
    assert verify_checksum(payload, f"sha256:{digest}")
    assert not verify_checksum(payload, "sha256:" + "0" * 64)
    with pytest.raises(ValueError):
        verify_checksum(payload, digest)
    registry = tmp_path / "registry.yml"
    registry.write_text("schema_version: 2\ndatasets: {}\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_registry(registry)
