from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from deficitlens.evaluation.bootstrap import clustered_bootstrap_interval, mae, mean_bias
from deficitlens.evaluation.decision import projected_mass_error_scenarios
from deficitlens.evaluation.external import audit_paee2026
from deficitlens.evaluation.fairness import disparity_summary, subgroup_audit
from deficitlens.evaluation.metrics import agreement_metrics, interval_metrics, regression_metrics
from deficitlens.evaluation.transportability import build_transferability_gate


def test_metrics_bootstrap_and_decisions() -> None:
    target = np.array([0.0, 1.0, 2.0, 3.0, 2.0, 4.0])
    prediction = np.array([0.1, 1.2, 1.5, 3.5, 2.2, 3.8])
    groups = np.array(["A", "A", "B", "B", "C", "C"])
    metrics = regression_metrics(target, prediction)
    assert metrics["n"] == 6
    assert metrics["mape_n"] == 5
    assert agreement_metrics(target, prediction)["bland_altman_lower_loa"] < 0
    intervals = interval_metrics(target, prediction - 0.6, prediction + 0.6)
    assert intervals["coverage"] == 1.0
    bootstrap = clustered_bootstrap_interval(
        target, prediction, groups, mae, repetitions=100, seed=1
    )
    assert bootstrap["clusters"] == 3
    assert mean_bias(target, prediction) == pytest.approx(prediction.mean() - target.mean())
    scenarios = projected_mass_error_scenarios(
        prediction - target,
        groups,
        horizons_weeks=[4],
        kcal_per_kg=7700,
        active_minutes_per_day=(30,),
    )
    assert scenarios.shape == (1, 9)
    assert scenarios.loc[0, "active_days_per_week"] == 7
    assert scenarios.loc[0, "kcal_per_kg_assumption"] == 7700
    expanded = projected_mass_error_scenarios(
        prediction - target,
        groups,
        horizons_weeks=[4],
        kcal_per_kg_values=(7000, 9000),
        active_minutes_per_day=(30,),
        active_days_per_week=(3, 5),
    )
    assert len(expanded) == 4
    with pytest.raises(ValueError):
        projected_mass_error_scenarios(
            prediction - target,
            groups,
            horizons_weeks=[4],
            kcal_per_kg_values=(),
        )
    with pytest.raises(ValueError):
        clustered_bootstrap_interval(
            target, prediction, np.array(["A"] * 6), mae, repetitions=100, seed=1
        )


def test_subgroup_and_external_audits() -> None:
    frame = pd.DataFrame(
        {
            "participant_id": ["A", "B", "C", "D", "E", "F"],
            "sex": ["F", "F", "F", "M", "M", "M"],
            "target": [1, 2, 3, 1, 2, 3],
            "prediction": [1, 2.5, 3, 2, 2, 4],
        }
    )
    audit = subgroup_audit(
        frame,
        target_column="target",
        prediction_column="prediction",
        group_column="participant_id",
        subgroup_columns=["sex", "missing"],
    )
    assert len(audit) == 2
    assert not audit["low_support"].any()
    assert len(disparity_summary(audit)) == 1

    external = pd.DataFrame(
        {
            "participant_id": [f"P{x}" for x in range(6)],
            "apple_kcal": [110, 100, 90, 120, 105, 95],
            "criterion_kcal": [100] * 6,
            "analysis_code_global_exclusion": [False] * 6,
            "implausible_device_value": [False] * 6,
            "sex": ["F"] * 3 + ["M"] * 3,
            "fitzpatrick_skin_type": [3, 3, 4, 4, 5, 5],
            "body_fat_band": ["<20"] * 3 + [">=30"] * 3,
            "bmi_band": ["<25"] * 3 + [">=30"] * 3,
        }
    )
    result = audit_paee2026(external, repetitions=100, seed=4)
    assert result.summary["participants"] == 6
    assert set(result.bootstrap["metric"]) == {"mae", "mean_bias"}
    assert set(result.subgroups["subgroup_variable"]) == {
        "sex",
        "fitzpatrick_skin_type",
        "body_fat_band",
        "bmi_band",
    }

    transfer = build_transferability_gate(external.columns)
    assert transfer["status"] == "blocked_model_transfer"
    assert transfer["passed"] is False
    assert "apple_hr_mean" in transfer["missing_required_features"]


def test_coverage_estimands_retain_the_person_as_the_sampling_unit() -> None:
    from deficitlens.evaluation.metrics import interval_metrics

    result = interval_metrics(
        np.array([1.0, 1.0, 1.0, 2.0]),
        np.zeros(4),
        np.ones(4),
        participants=np.array(["a", "a", "a", "b"]),
    )
    assert result["coverage"] == 0.75
    assert result["participant_balanced_coverage"] == 0.5
    assert result["participants_all_windows_covered"] == 1
    assert result["simultaneous_participant_coverage"] == 0.5
