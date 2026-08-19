"""Independent Apple Watch Series 8 session-level bias audit."""

from __future__ import annotations

import pandas as pd

from deficitlens.evaluation.metrics import agreement_metrics, regression_metrics


def audit_paee2026(frame: pd.DataFrame) -> tuple[dict[str, object], pd.DataFrame]:
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
    rows: list[dict[str, object]] = []
    subgroup_columns = ["sex", "fitzpatrick_skin_type", "body_fat_band", "bmi_band"]
    for column in subgroup_columns:
        for label, subset in frame.groupby(column, dropna=False, observed=True):
            metrics = regression_metrics(
                subset["criterion_kcal"].to_numpy(dtype=float),
                subset["apple_kcal"].to_numpy(dtype=float),
                mape_floor=1.0,
            )
            rows.append(
                {
                    "subgroup_variable": column,
                    "subgroup": str(label),
                    "participants": subset["participant_id"].nunique(),
                    "mae_kcal": metrics["mae"],
                    "mean_bias_kcal": metrics["mean_bias"],
                    "mape": metrics["mape"],
                    "low_support": len(subset) < 5,
                }
            )
    return summary, pd.DataFrame(rows)
