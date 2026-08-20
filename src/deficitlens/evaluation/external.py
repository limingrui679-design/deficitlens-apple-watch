"""Independent Apple Watch Series 8 session-level bias audit."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from deficitlens.evaluation.bootstrap import (
    clustered_bootstrap_interval,
    mae,
    mean_bias,
)
from deficitlens.evaluation.metrics import agreement_metrics, regression_metrics


@dataclass(frozen=True)
class ExternalAuditResult:
    """Summary, uncertainty, and subgroup outputs for one external audit frame."""

    summary: dict[str, object]
    bootstrap: pd.DataFrame
    subgroups: pd.DataFrame


def audit_paee2026(
    frame: pd.DataFrame, *, repetitions: int = 1000, seed: int = 20260820
) -> ExternalAuditResult:
    """Audit Apple Watch totals against COSMED K5 without training on the external cohort."""

    target = frame["criterion_kcal"].to_numpy(dtype=float)
    prediction = frame["apple_kcal"].to_numpy(dtype=float)
    summary: dict[str, object] = {
        **regression_metrics(target, prediction, mape_floor=1.0),
        **agreement_metrics(target, prediction),
        "participants": frame["participant_id"].nunique(),
        "analysis_code_global_exclusions": int(frame["analysis_code_global_exclusion"].sum()),
        "implausible_device_values": int(frame["implausible_device_value"].sum()),
    }
    bootstrap_rows: list[dict[str, object]] = []
    groups = frame["participant_id"].astype(str).to_numpy()
    for index, (metric_name, metric) in enumerate((("mae", mae), ("mean_bias", mean_bias))):
        interval = clustered_bootstrap_interval(
            target,
            prediction,
            groups,
            metric,
            repetitions=repetitions,
            seed=seed + index * 97,
        )
        bootstrap_rows.append({"metric": metric_name, **interval})
    rows: list[dict[str, object]] = []
    subgroup_columns = ["sex", "fitzpatrick_skin_type", "body_fat_band", "bmi_band"]
    for column in subgroup_columns:
        for label, subset in frame.groupby(column, dropna=False, observed=True):
            normalized_label = (
                "Unknown" if pd.isna(label) or str(label).lower() == "nan" else str(label)
            )
            metrics = regression_metrics(
                subset["criterion_kcal"].to_numpy(dtype=float),
                subset["apple_kcal"].to_numpy(dtype=float),
                mape_floor=1.0,
            )
            rows.append(
                {
                    "subgroup_variable": column,
                    "subgroup": normalized_label,
                    "participants": subset["participant_id"].nunique(),
                    "mae_kcal": metrics["mae"],
                    "mean_bias_kcal": metrics["mean_bias"],
                    "mape": metrics["mape"],
                    "low_support": len(subset) < 5,
                }
            )
    return ExternalAuditResult(
        summary=summary,
        bootstrap=pd.DataFrame(bootstrap_rows),
        subgroups=pd.DataFrame(rows),
    )
