from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from deficitlens.models.adaptive import KalmanBiasCalibrator
from deficitlens.models.baselines import (
    apple_raw,
    cohort_affine_fit,
    cohort_affine_predict,
    protocol_met,
)
from deficitlens.models.conformal import MondrianConformalRegressor, conformal_quantile
from deficitlens.models.ensemble import GroupStackedRegressor
from deficitlens.schemas import APPLE_ONLY_NUMERIC_FEATURES, CATEGORICAL_FEATURES, TARGET_COLUMN


def test_group_stacked_regressor(synthetic_windows: pd.DataFrame) -> None:
    target = synthetic_windows[TARGET_COLUMN].to_numpy(dtype=float)
    model = GroupStackedRegressor(
        model_names=["ridge", "extra_trees", "histogram_gradient_boosting"],
        numeric_features=list(APPLE_ONLY_NUMERIC_FEATURES),
        categorical_features=list(CATEGORICAL_FEATURES),
        inner_group_folds=2,
        seed=8,
    ).fit(
        synthetic_windows,
        target,
        synthetic_windows["participant_id"].to_numpy(),
    )
    prediction = model.predict(synthetic_windows.head())
    assert prediction.shape == (5,)
    assert (prediction >= 0).all()
    diagnostics = model.diagnostics()
    assert sum(diagnostics["weights"].values()) == pytest.approx(1.0)  # type: ignore[union-attr]
    assert set(model.predict_components(synthetic_windows.head())) == {
        "ridge",
        "extra_trees",
        "histogram_gradient_boosting",
    }


def test_model_guards(synthetic_windows: pd.DataFrame) -> None:
    with pytest.raises(ValueError):
        GroupStackedRegressor(
            ["ridge"], list(APPLE_ONLY_NUMERIC_FEATURES), list(CATEGORICAL_FEATURES)
        )
    model = GroupStackedRegressor(
        ["ridge", "extra_trees"],
        list(APPLE_ONLY_NUMERIC_FEATURES),
        list(CATEGORICAL_FEATURES),
    )
    with pytest.raises(RuntimeError):
        model.predict(synthetic_windows)
    tiny = synthetic_windows[synthetic_windows["participant_id"] == "S01"]
    with pytest.raises(ValueError):
        model.fit(tiny, tiny[TARGET_COLUMN].to_numpy(), tiny["participant_id"].to_numpy())


def test_conformal_window_and_cluster_intervals() -> None:
    frame = pd.DataFrame(
        {
            "activity": ["run"] * 6 + ["sit"] * 6,
            "participant_id": ["A"] * 3 + ["B"] * 3 + ["A"] * 3 + ["B"] * 3,
        }
    )
    target = np.arange(12, dtype=float)
    prediction = target + np.array([0.1, 0.2, 1, 0.1, 0.3, 2, 0.1, 0.2, 0.4, 0.1, 0.5, 1])
    conformal = MondrianConformalRegressor.fit(
        frame,
        target,
        prediction,
        alpha=0.1,
        group_column="activity",
        minimum_group_samples=3,
        cluster_column="participant_id",
        minimum_group_clusters=2,
    )
    compact = conformal.predict_interval(frame, prediction)
    robust = conformal.predict_interval(frame, prediction, cluster_robust=True)
    assert np.all(robust[2] >= compact[2])
    assert conformal.calibration_clusters == 2
    assert conformal_quantile(np.array([1, 2, 3, 4]), 0.25) == 4
    with pytest.raises(ValueError):
        conformal_quantile(np.array([]), 0.1)
    with pytest.raises(ValueError):
        conformal_quantile(np.array([1]), 1.0)


def test_baselines_and_adaptive_calibrator(synthetic_windows: pd.DataFrame) -> None:
    target = synthetic_windows[TARGET_COLUMN].to_numpy(dtype=float)
    intercept, slope = cohort_affine_fit(synthetic_windows, target)
    assert len(apple_raw(synthetic_windows)) == len(target)
    assert (cohort_affine_predict(synthetic_windows, intercept, slope) >= 0).all()
    assert (protocol_met(synthetic_windows) >= 0).all()

    kalman = KalmanBiasCalibrator(process_variance=0.01, observation_variance=0.2)
    before, uncertainty = kalman.predict(10)
    gain = kalman.update(apple_estimate=10, criterion=8)
    after, new_uncertainty = kalman.predict(10)
    assert before == 10
    assert 0 < gain < 1
    assert after < before
    assert new_uncertainty < uncertainty
    with pytest.raises(ValueError):
        KalmanBiasCalibrator(observation_variance=0)
