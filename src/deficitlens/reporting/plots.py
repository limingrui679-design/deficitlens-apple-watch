"""Publication-style, color-accessible benchmark figures."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.figure import Figure

COLORS = {
    "apple_raw": "#E45756",
    "cohort_affine": "#72B7B2",
    "protocol_met_baseline": "#F2CF5B",
    "ensemble": "#4C78A8",
}


def _save(figure: Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(figure)


def model_error_figure(metrics: pd.DataFrame, path: Path) -> None:
    """Plot MAE and mean bias for every comparator."""

    ordered = metrics.sort_values("mae")
    figure, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    labels = ordered["model"].str.replace("_", " ")
    colors = [COLORS.get(name, "#999999") for name in ordered["model"]]
    deployable = ordered[ordered["model"] != "protocol_met_baseline"]
    mae_cap = float(deployable["mae"].max()) * 1.35
    displayed_mae = np.minimum(ordered["mae"].to_numpy(dtype=float), mae_cap)
    axes[0].barh(labels, displayed_mae, color=colors)
    for position, actual in enumerate(ordered["mae"].to_numpy(dtype=float)):
        text_x = min(actual + mae_cap * 0.025, mae_cap * 0.97)
        alignment = "right" if actual > mae_cap else "left"
        suffix = " (off-scale)" if actual > mae_cap else ""
        axes[0].text(
            text_x, position, f"{actual:.2f}{suffix}", va="center", ha=alignment, fontsize=8
        )
    axes[0].set_xlim(0, mae_cap)
    axes[0].set_xlabel("MAE (active kcal/min; lower is better)")
    axes[0].grid(axis="x", alpha=0.2)
    bias_cap = max(float(deployable["mean_bias"].abs().max()) * 2.8, 0.35)
    displayed_bias = np.clip(ordered["mean_bias"].to_numpy(dtype=float), -bias_cap, bias_cap)
    axes[1].barh(labels, displayed_bias, color=colors)
    for position, actual in enumerate(ordered["mean_bias"].to_numpy(dtype=float)):
        is_off_scale = abs(actual) > bias_cap
        text_x = np.sign(actual) * bias_cap * 0.97 if is_off_scale else actual
        alignment = "right" if actual >= 0 else "left"
        suffix = " (off-scale)" if is_off_scale else ""
        axes[1].text(
            text_x,
            position,
            f"{actual:+.2f}{suffix}",
            va="center",
            ha=alignment,
            fontsize=8,
        )
    axes[1].axvline(0.0, color="#333333", linewidth=1)
    axes[1].set_xlim(-bias_cap, bias_cap)
    axes[1].set_xlabel("Mean bias (prediction - criterion)")
    axes[1].grid(axis="x", alpha=0.2)
    figure.suptitle("Held-out-participant performance")
    figure.tight_layout()
    _save(figure, path)


def observed_predicted_figure(predictions: pd.DataFrame, path: Path) -> None:
    """Compare raw Apple and ensemble predictions against the criterion."""

    figure, axes = plt.subplots(1, 2, figsize=(10, 4.5), sharex=True, sharey=True)
    maximum = float(predictions[["y_true", "apple_raw", "ensemble"]].to_numpy(dtype=float).max())
    for axis, column, title in zip(
        axes,
        ("apple_raw", "ensemble"),
        ("Apple Watch raw", "DeficitLens ensemble"),
        strict=True,
    ):
        axis.scatter(
            predictions["y_true"],
            predictions[column],
            c=COLORS[column],
            alpha=0.38,
            s=18,
            edgecolors="none",
        )
        axis.plot([0, maximum], [0, maximum], "--", color="#333333", linewidth=1)
        axis.set_title(title)
        axis.set_xlabel("Criterion active energy (kcal/min)")
        axis.grid(alpha=0.16)
    axes[0].set_ylabel("Estimated active energy (kcal/min)")
    figure.suptitle("Every point comes from an outer held-out participant")
    figure.tight_layout()
    _save(figure, path)


def coverage_by_activity_figure(predictions: pd.DataFrame, path: Path) -> None:
    """Plot empirical conformal coverage and interval width by activity."""

    frame = predictions.assign(
        covered=lambda value: (
            (value["y_true"] >= value["interval_lower"])
            & (value["y_true"] <= value["interval_upper"])
        ),
        width=lambda value: value["interval_upper"] - value["interval_lower"],
    )
    summary = frame.groupby("activity", observed=True).agg(
        coverage=("covered", "mean"), width=("width", "mean")
    )
    figure, axis = plt.subplots(figsize=(8, 4.6))
    positions = np.arange(len(summary))
    axis.bar(positions, summary["coverage"], color="#4C78A8")
    axis.axhline(0.90, color="#E45756", linestyle="--", label="90% nominal")
    axis.set_xticks(positions, summary.index.str.replace("_", " "), rotation=25, ha="right")
    axis.set_ylim(0.0, 1.05)
    axis.set_ylabel("Empirical coverage")
    axis.legend(frameon=False)
    axis.grid(axis="y", alpha=0.2)
    figure.tight_layout()
    _save(figure, path)


def external_agreement_figure(frame: pd.DataFrame, path: Path) -> None:
    """Plot Apple Watch Series 8 versus COSMED K5 session totals."""

    primary = frame[~frame["analysis_code_global_exclusion"] & ~frame["implausible_device_value"]]
    difference = primary["apple_kcal"] - primary["criterion_kcal"]
    average = (primary["apple_kcal"] + primary["criterion_kcal"]) / 2.0
    bias = float(difference.mean())
    sd = float(difference.std(ddof=1))
    figure, axes = plt.subplots(1, 2, figsize=(10, 4.3))
    axes[0].scatter(primary["criterion_kcal"], primary["apple_kcal"], color="#4C78A8")
    maximum = float(primary[["criterion_kcal", "apple_kcal"]].to_numpy().max())
    axes[0].plot([0, maximum], [0, maximum], "--", color="#333333")
    axes[0].set_xlabel("COSMED K5 (kcal)")
    axes[0].set_ylabel("Apple Watch Series 8 (kcal)")
    axes[0].set_title("Independent paired totals")
    axes[1].scatter(average, difference, color="#72B7B2")
    axes[1].axhline(bias, color="#333333", label="Mean bias")
    axes[1].axhline(bias - 1.96 * sd, color="#E45756", linestyle="--")
    axes[1].axhline(bias + 1.96 * sd, color="#E45756", linestyle="--", label="95% LoA")
    axes[1].set_xlabel("Pair average (kcal)")
    axes[1].set_ylabel("Apple - COSMED (kcal)")
    axes[1].set_title("Bland-Altman agreement")
    axes[1].legend(frameon=False)
    for axis in axes:
        axis.grid(alpha=0.16)
    figure.tight_layout()
    _save(figure, path)
