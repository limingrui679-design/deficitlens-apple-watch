from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from deficitlens.config import Settings
from deficitlens.evaluation.benchmark import BenchmarkResult
from deficitlens.evaluation.metrics import agreement_metrics, interval_metrics, regression_metrics
from deficitlens.pipeline import run_verified_pipeline
from deficitlens.schemas import DatasetEvidence


def _fake_benchmark(frame: pd.DataFrame) -> BenchmarkResult:
    predictions = frame.copy()
    target = frame["ground_truth_active_kcal_min"].to_numpy(dtype=float)
    predictions["y_true"] = target
    predictions["apple_raw"] = frame["apple_active_kcal_min"].to_numpy(dtype=float)
    predictions["cohort_affine"] = np.maximum(predictions["apple_raw"] * 0.95, 0)
    predictions["protocol_met_baseline"] = np.maximum(target + 0.8, 0)
    predictions["ensemble"] = np.maximum(target + 0.08, 0)
    predictions["interval_lower"] = np.maximum(predictions["ensemble"] - 1.0, 0)
    predictions["interval_upper"] = predictions["ensemble"] + 1.0
    predictions["compact_interval_lower"] = np.maximum(predictions["ensemble"] - 0.5, 0)
    predictions["compact_interval_upper"] = predictions["ensemble"] + 0.5
    predictions["outer_fold"] = predictions["participant_id"].str[1:].astype(int)
    metric_rows = []
    for model_name in ("apple_raw", "cohort_affine", "protocol_met_baseline", "ensemble"):
        values = predictions[model_name].to_numpy(dtype=float)
        metric_rows.append(
            {
                "model": model_name,
                **regression_metrics(target, values),
                **agreement_metrics(target, values),
            }
        )
    metrics = pd.DataFrame(metric_rows)
    bootstrap = pd.DataFrame(
        [
            {
                "model": model,
                "metric": metric,
                "estimate": 0.2,
                "lower": 0.1,
                "upper": 0.3,
                "confidence": 0.95,
                "repetitions": 100,
                "clusters": 6,
            }
            for model in metrics["model"]
            for metric in ("mae", "mean_bias")
        ]
    )
    interval = interval_metrics(
        target,
        predictions["interval_lower"].to_numpy(),
        predictions["interval_upper"].to_numpy(),
    )
    compact = interval_metrics(
        target,
        predictions["compact_interval_lower"].to_numpy(),
        predictions["compact_interval_upper"].to_numpy(),
    )
    return BenchmarkResult(predictions, metrics, bootstrap, interval, compact, [{"fold": 1}])


def _external_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "participant_id": [f"OSF{x:03d}" for x in range(1, 7)],
            "apple_kcal": [105, 95, 110, 100, 115, 90],
            "criterion_kcal": [100] * 6,
            "analysis_code_global_exclusion": [False] * 5 + [True],
            "implausible_device_value": [False] * 6,
            "sex": ["Female"] * 3 + ["Male"] * 3,
            "fitzpatrick_skin_type": [3, 3, 4, 4, 5, 5],
            "body_fat_band": ["<20"] * 3 + [">=30"] * 3,
            "bmi_band": ["<25"] * 3 + [">=30"] * 3,
        }
    )


def test_pipeline_builds_hashed_report_bundle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    synthetic_windows: pd.DataFrame,
    settings: Settings,
) -> None:
    import deficitlens.pipeline as pipeline_module

    weee_evidence = DatasetEvidence(
        "weee",
        len(synthetic_windows),
        6,
        tuple(sorted(synthetic_windows["activity"].unique())),
        "md5:abc",
        str(tmp_path / "dataset.zip"),
    )
    external = _external_frame()
    external_evidence = DatasetEvidence(
        "apple_watch_paee_2026",
        len(external),
        len(external),
        ("cycle",),
        "sha256:def",
        str(tmp_path / "external.xlsx"),
    )
    benchmark = _fake_benchmark(synthetic_windows)

    monkeypatch.setattr(
        pipeline_module,
        "build_weee_windows",
        lambda archive, config: (synthetic_windows, weee_evidence),
    )
    monkeypatch.setattr(pipeline_module, "run_loso_benchmark", lambda frame, config: benchmark)
    monkeypatch.setattr(
        pipeline_module,
        "load_paee2026",
        lambda path, primary_analysis=False: (external, external_evidence),
    )
    output = tmp_path / "evidence"
    manifest = run_verified_pipeline(
        weee_archive=tmp_path / "dataset.zip",
        paee2026_workbook=tmp_path / "external.xlsx",
        output_dir=output,
        settings=settings,
    )
    assert manifest["outer_test_participants"] == 6
    assert (output / "report.html").exists()
    assert (output / "figures/model_error.png").stat().st_size > 1000
    assert (output / "tables/subgroup_audit.csv").exists()
    assert "report.html" in manifest["outputs"]
    report = (output / "report.html").read_text(encoding="utf-8")
    assert "DeficitLens" in report
    assert "cluster-robust" in report
