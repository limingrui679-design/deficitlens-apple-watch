"""Nested leave-one-subject-out benchmark orchestration."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from deficitlens.config import Settings
from deficitlens.evaluation.bootstrap import (
    clustered_bootstrap_interval,
    mae,
    mean_bias,
)
from deficitlens.evaluation.metrics import (
    agreement_metrics,
    interval_metrics,
    regression_metrics,
)
from deficitlens.evaluation.mixture import participant_mix_sensitivity
from deficitlens.models.baselines import (
    apple_raw,
    cohort_affine_fit,
    cohort_affine_predict,
    protocol_met,
)
from deficitlens.models.conformal import MondrianConformalRegressor
from deficitlens.models.ensemble import GroupStackedRegressor
from deficitlens.schemas import (
    APPLE_ONLY_NUMERIC_FEATURES,
    CATEGORICAL_FEATURES,
    GROUP_COLUMN,
    TARGET_COLUMN,
)


@dataclass(frozen=True)
class BenchmarkResult:
    """All row-level and aggregate outputs from the nested benchmark."""

    predictions: pd.DataFrame
    metrics: pd.DataFrame
    bootstrap: pd.DataFrame
    interval: dict[str, float | int]
    compact_interval: dict[str, float | int]
    fold_diagnostics: list[dict[str, object]]


def _calibration_groups(candidate_groups: NDArray[Any], fraction: float, *, seed: int) -> set[str]:
    unique = np.unique(candidate_groups.astype(str))
    count = max(1, math.ceil(len(unique) * fraction))
    count = min(count, len(unique) - 2)
    rng = np.random.default_rng(seed)
    return set(rng.choice(unique, size=count, replace=False).tolist())


def run_loso_benchmark(frame: pd.DataFrame, settings: Settings) -> BenchmarkResult:
    """Evaluate every participant once with nested participant-level separation."""

    required = {
        *APPLE_ONLY_NUMERIC_FEATURES,
        *CATEGORICAL_FEATURES,
        GROUP_COLUMN,
        TARGET_COLUMN,
        "protocol_met",
        "window_start",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Benchmark frame missing columns: {sorted(missing)}")
    groups = frame[GROUP_COLUMN].astype(str).to_numpy()
    unique_groups = np.unique(groups)
    if len(unique_groups) < 6:
        raise ValueError("At least six participants are required for nested LOSO evaluation")

    fold_outputs: list[pd.DataFrame] = []
    diagnostics: list[dict[str, object]] = []
    for outer_index, held_out in enumerate(unique_groups):
        test_mask = groups == held_out
        candidate_mask = ~test_mask
        calibration = _calibration_groups(
            groups[candidate_mask],
            settings.model.calibration_group_fraction,
            seed=settings.seed + outer_index * 997,
        )
        calibration_mask = np.isin(groups, list(calibration))
        development_mask = candidate_mask & ~calibration_mask
        development = frame.loc[development_mask]
        calibration_frame = frame.loc[calibration_mask]
        test = frame.loc[test_mask]

        target_development = development[TARGET_COLUMN].to_numpy(dtype=float)
        model = GroupStackedRegressor(
            model_names=list(settings.model.ensemble_models),
            numeric_features=list(APPLE_ONLY_NUMERIC_FEATURES),
            categorical_features=list(CATEGORICAL_FEATURES),
            inner_group_folds=settings.model.inner_group_folds,
            seed=settings.seed + outer_index * 10_007,
        ).fit(
            development,
            target_development,
            development[GROUP_COLUMN].astype(str).to_numpy(),
        )
        calibration_prediction = model.predict(calibration_frame)
        conformal = MondrianConformalRegressor.fit(
            calibration_frame,
            calibration_frame[TARGET_COLUMN].to_numpy(dtype=float),
            calibration_prediction,
            alpha=settings.model.conformal_alpha,
            group_column=settings.model.mondrian_column,
            minimum_group_samples=settings.model.minimum_mondrian_samples,
            cluster_column=GROUP_COLUMN,
            minimum_group_clusters=settings.model.minimum_mondrian_clusters,
        )
        ensemble_prediction = model.predict(test)
        compact_lower, compact_upper, compact_radii = conformal.predict_interval(
            test, ensemble_prediction
        )
        lower, upper, radii = conformal.predict_interval(
            test, ensemble_prediction, cluster_robust=True
        )
        intercept, slope = cohort_affine_fit(development, target_development)
        components = model.predict_components(test)

        output = test.copy()
        output["y_true"] = test[TARGET_COLUMN].to_numpy(dtype=float)
        output["apple_raw"] = apple_raw(test)
        output["cohort_affine"] = cohort_affine_predict(test, intercept, slope)
        output["protocol_met_baseline"] = protocol_met(test)
        output["ensemble"] = ensemble_prediction
        output["interval_lower"] = lower
        output["interval_upper"] = upper
        output["interval_radius"] = radii
        output["compact_interval_lower"] = compact_lower
        output["compact_interval_upper"] = compact_upper
        output["compact_interval_radius"] = compact_radii
        output["outer_fold"] = outer_index
        output["held_out_participant"] = held_out
        output["calibration_participants"] = ",".join(sorted(calibration))
        for column in components:
            output[f"component_{column}"] = components[column].to_numpy(dtype=float)
        fold_outputs.append(output)

        fold_diagnostic = {
            "outer_fold": outer_index,
            "held_out_participant": held_out,
            "development_participants": development[GROUP_COLUMN].nunique(),
            "calibration_participants": sorted(calibration),
            "development_windows": len(development),
            "calibration_windows": len(calibration_frame),
            "test_windows": len(test),
            "conformal_global_radius": conformal.global_radius,
            "conformal_group_radii": conformal.group_radii,
            "cluster_conformal_global_radius": conformal.cluster_global_radius,
            "cluster_conformal_group_radii": conformal.cluster_group_radii,
            "conformal_calibration_clusters": conformal.calibration_clusters,
            "affine_intercept": intercept,
            "affine_slope": slope,
            **model.diagnostics(),
        }
        radius = conformal.simultaneous_radius
        abs_error = np.abs(test[TARGET_COLUMN].to_numpy(dtype=float) - ensemble_prediction)
        fold_diagnostic["simultaneous_participant_band"] = {
            "alpha": conformal.alpha,
            "calibration_people": conformal.calibration_clusters,
            "required_order": conformal.simultaneous_order,
            "max_finite_nominal_coverage": conformal.calibration_clusters
            / (conformal.calibration_clusters + 1),
            "radius": radius,
            "status": "finite" if radius is not None else "insufficient_calibration_people",
            "held_out_all_windows_covered": bool(np.all(abs_error <= radius))
            if radius is not None
            else None,
        }
        diagnostics.append(fold_diagnostic)

    predictions = pd.concat(fold_outputs).sort_index()
    models = ["apple_raw", "cohort_affine", "protocol_met_baseline", "ensemble"]
    metric_rows: list[dict[str, object]] = []
    bootstrap_rows: list[dict[str, object]] = []
    target = predictions["y_true"].to_numpy(dtype=float)
    prediction_groups = predictions[GROUP_COLUMN].astype(str).to_numpy()
    for model_name in models:
        values = predictions[model_name].to_numpy(dtype=float)
        metric_rows.append(
            {
                "model": model_name,
                **regression_metrics(target, values),
                **agreement_metrics(target, values),
                **participant_mix_sensitivity(
                    target,
                    values,
                    predictions["apple_raw"].to_numpy(dtype=float),
                    prediction_groups,
                ),
            }
        )
        for metric_name, function in (("mae", mae), ("mean_bias", mean_bias)):
            interval = clustered_bootstrap_interval(
                target,
                values,
                prediction_groups,
                function,
                repetitions=settings.evaluation.bootstrap_repetitions,
                seed=settings.seed + len(bootstrap_rows) * 37,
            )
            bootstrap_rows.append({"model": model_name, "metric": metric_name, **interval})

    intervals = interval_metrics(
        target,
        predictions["interval_lower"].to_numpy(dtype=float),
        predictions["interval_upper"].to_numpy(dtype=float),
        participants=prediction_groups,
    )
    compact_intervals = interval_metrics(
        target,
        predictions["compact_interval_lower"].to_numpy(dtype=float),
        predictions["compact_interval_upper"].to_numpy(dtype=float),
        participants=prediction_groups,
    )
    return BenchmarkResult(
        predictions=predictions.reset_index(drop=True),
        metrics=pd.DataFrame(metric_rows),
        bootstrap=pd.DataFrame(bootstrap_rows),
        interval=intervals,
        compact_interval=compact_intervals,
        fold_diagnostics=diagnostics,
    )
