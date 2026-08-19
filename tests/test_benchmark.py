from __future__ import annotations

import pandas as pd

from deficitlens.config import Settings
from deficitlens.evaluation.benchmark import run_loso_benchmark
from deficitlens.schemas import CATEGORICAL_FEATURES


def test_nested_loso_outputs(synthetic_windows: pd.DataFrame, settings: Settings) -> None:
    assert CATEGORICAL_FEATURES == ["sex", "activity_family"]
    result = run_loso_benchmark(synthetic_windows, settings)
    assert len(result.predictions) == len(synthetic_windows)
    assert result.predictions["held_out_participant"].nunique() == 6
    assert set(result.metrics["model"]) == {
        "apple_raw",
        "cohort_affine",
        "protocol_met_baseline",
        "ensemble",
    }
    assert 0 <= result.interval["coverage"] <= 1
    assert 0 <= result.compact_interval["coverage"] <= 1
    for diagnostic in result.fold_diagnostics:
        assert diagnostic["held_out_participant"] not in diagnostic["calibration_participants"]
        assert diagnostic["development_participants"] == 3
