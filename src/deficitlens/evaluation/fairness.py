"""Subgroup performance slices with small-cell warnings."""

from __future__ import annotations

import math

import pandas as pd

from deficitlens.evaluation.metrics import regression_metrics


def subgroup_audit(
    frame: pd.DataFrame,
    *,
    target_column: str,
    prediction_column: str,
    group_column: str,
    subgroup_columns: list[str],
    minimum_participants: int = 3,
) -> pd.DataFrame:
    """Return disaggregated metrics and explicit reliability warnings."""

    rows: list[dict[str, object]] = []
    for subgroup_column in subgroup_columns:
        if subgroup_column not in frame:
            continue
        for subgroup, subset in frame.groupby(subgroup_column, dropna=False, observed=True):
            metrics = regression_metrics(
                subset[target_column].to_numpy(dtype=float),
                subset[prediction_column].to_numpy(dtype=float),
            )
            participants = subset[group_column].astype(str).nunique()
            rows.append(
                {
                    "subgroup_variable": subgroup_column,
                    "subgroup": str(subgroup),
                    "participants": participants,
                    "windows": len(subset),
                    "target_mean": float(subset[target_column].mean()),
                    "mae": metrics["mae"],
                    "rmse": metrics["rmse"],
                    "mean_bias": metrics["mean_bias"],
                    "mape": metrics["mape"],
                    "low_support": participants < minimum_participants,
                }
            )
    return pd.DataFrame(rows)


def disparity_summary(audit: pd.DataFrame) -> pd.DataFrame:
    """Summarize max-minus-min and max/min MAE for supported subgroup cells."""

    rows: list[dict[str, object]] = []
    if audit.empty:
        return pd.DataFrame(rows)
    for variable, subset in audit[~audit["low_support"]].groupby("subgroup_variable"):
        if len(subset) < 2:
            continue
        minimum = float(subset["mae"].min())
        maximum = float(subset["mae"].max())
        rows.append(
            {
                "subgroup_variable": variable,
                "mae_gap": maximum - minimum,
                "mae_ratio": maximum / minimum if minimum > 0 else math.inf,
                "best_group": str(subset.loc[subset["mae"].idxmin(), "subgroup"]),
                "worst_group": str(subset.loc[subset["mae"].idxmax(), "subgroup"]),
            }
        )
    return pd.DataFrame(rows)
