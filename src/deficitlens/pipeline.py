"""End-to-end public-data benchmark and evidence-bundle pipeline."""

from __future__ import annotations

import json
import platform
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np
import pandas as pd

from deficitlens.cases import CaseCatalog, load_case_catalog
from deficitlens.config import Settings
from deficitlens.data.paee2026 import load_paee2026
from deficitlens.data.registry import checksum
from deficitlens.data.weee import build_weee_windows
from deficitlens.evaluation.benchmark import BenchmarkResult, run_loso_benchmark
from deficitlens.evaluation.decision import projected_mass_error_scenarios
from deficitlens.evaluation.external import audit_paee2026
from deficitlens.evaluation.fairness import disparity_summary, subgroup_audit
from deficitlens.evaluation.transportability import build_transferability_gate
from deficitlens.evidence import ExternalEvidenceLedger, load_external_evidence
from deficitlens.reporting.plots import (
    coverage_by_activity_figure,
    external_agreement_figure,
    model_error_figure,
    observed_predicted_figure,
)
from deficitlens.reporting.report import accessible_table, render_report
from deficitlens.schemas import GROUP_COLUMN, DatasetEvidence
from deficitlens.version import __version__


def _json_default(value: object) -> object:
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (datetime, pd.Timestamp)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Cannot serialize {type(value).__name__}")


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=_json_default) + "\n",
        encoding="utf-8",
    )


def _safe_evidence(evidence: DatasetEvidence) -> dict[str, Any]:
    values = evidence.to_dict()
    values["source_file"] = Path(str(values.pop("source_path"))).name
    values["activities"] = list(values["activities"])
    values["notes"] = list(values["notes"])
    return values


def _fairness_tables(
    predictions: pd.DataFrame, settings: Settings
) -> tuple[pd.DataFrame, pd.DataFrame]:
    audits: list[pd.DataFrame] = []
    for model_name in ("apple_raw", "ensemble"):
        frame = predictions.copy()
        frame["audited_prediction"] = frame[model_name]
        audit = subgroup_audit(
            frame,
            target_column="y_true",
            prediction_column="audited_prediction",
            group_column=GROUP_COLUMN,
            subgroup_columns=settings.evaluation.subgroup_columns,
        )
        audit.insert(0, "model", model_name)
        audits.append(audit)
    combined = pd.concat(audits, ignore_index=True)
    disparities: list[pd.DataFrame] = []
    for grouped_model, subset in combined.groupby("model"):
        summary = disparity_summary(subset)
        summary.insert(0, "model", str(grouped_model))
        disparities.append(summary)
    return combined, pd.concat(disparities, ignore_index=True)


def _decision_tables(predictions: pd.DataFrame, settings: Settings) -> pd.DataFrame:
    exercise_predictions = predictions[predictions["activity_family"].isin(["cycling", "running"])]
    if exercise_predictions.empty:
        raise ValueError("Decision scenarios require cycling or running exercise windows")
    outputs: list[pd.DataFrame] = []
    for model_name in ("apple_raw", "cohort_affine", "ensemble"):
        scenario = projected_mass_error_scenarios(
            exercise_predictions[model_name].to_numpy(dtype=float)
            - exercise_predictions["y_true"].to_numpy(dtype=float),
            exercise_predictions[GROUP_COLUMN].astype(str).to_numpy(),
            horizons_weeks=settings.evaluation.decision_horizons_weeks,
            kcal_per_kg_values=tuple(settings.evaluation.kcal_per_kg_scenarios),
            active_minutes_per_day=tuple(settings.evaluation.decision_active_minutes_per_day),
            active_days_per_week=tuple(settings.evaluation.decision_active_days_per_week),
        )
        scenario.insert(0, "model", model_name)
        outputs.append(scenario)
    return pd.concat(outputs, ignore_index=True)


def _report_context(
    *,
    benchmark: BenchmarkResult,
    evidence: dict[str, Any],
    high_resolution_rows: int,
    external_primary: dict[str, object],
    external_all: dict[str, object],
    external_bootstrap: pd.DataFrame,
    transferability_gate: dict[str, object],
    subgroup: pd.DataFrame,
    disparities: pd.DataFrame,
    external_subgroups: pd.DataFrame,
    decisions: pd.DataFrame,
    case_catalog: CaseCatalog,
    external_evidence: ExternalEvidenceLedger,
    elapsed_seconds: float,
) -> dict[str, Any]:
    metrics = benchmark.metrics.copy()
    best = metrics.loc[metrics["mae"].idxmin()].to_dict()
    raw = metrics.loc[metrics["model"] == "apple_raw"].iloc[0]
    ensemble = metrics.loc[metrics["model"] == "ensemble"].iloc[0]
    improvement = 100.0 * (float(raw["mae"]) - float(ensemble["mae"])) / float(raw["mae"])
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "version": __version__,
        "evidence": evidence,
        "high_resolution_rows": high_resolution_rows,
        "best": best,
        "ensemble_improvement_pct": improvement,
        "interval": benchmark.interval,
        "compact_interval": benchmark.compact_interval,
        "external_primary": external_primary,
        "external_all": external_all,
        "external_bootstrap_table": accessible_table(
            external_bootstrap.round(3).to_html(index=False, classes="data-table")
        ),
        "transferability_gate": transferability_gate,
        "elapsed_seconds": elapsed_seconds,
        "metrics_table": accessible_table(
            metrics.round(4).to_html(index=False, classes="data-table")
        ),
        "bootstrap_table": accessible_table(
            benchmark.bootstrap.round(4).to_html(index=False, classes="data-table")
        ),
        "subgroup_table": accessible_table(
            subgroup.round(4).to_html(index=False, classes="data-table")
        ),
        "disparity_table": accessible_table(
            disparities.round(4).to_html(index=False, classes="data-table")
        ),
        "external_subgroup_table": accessible_table(
            external_subgroups.round(3).to_html(index=False, classes="data-table")
        ),
        "decision_table": accessible_table(
            decisions.round(4).to_html(index=False, classes="data-table")
        ),
        "decision_minutes": sorted(decisions["active_minutes_per_day"].unique().tolist()),
        "decision_days": sorted(decisions["active_days_per_week"].unique().tolist()),
        "decision_horizons": sorted(decisions["horizon_weeks"].unique().tolist()),
        "decision_energy_density": sorted(decisions["kcal_per_kg_assumption"].unique().tolist()),
        "case_paths": [case.model_dump(mode="json") for case in case_catalog.cases],
        "external_evidence": external_evidence.model_dump(mode="json"),
    }


def run_verified_pipeline(
    *,
    weee_archive: str | Path,
    paee2026_workbook: str | Path,
    output_dir: str | Path,
    settings: Settings,
) -> dict[str, Any]:
    """Run all registered analyses and produce a checksum-addressed evidence bundle."""

    started = perf_counter()
    output = Path(output_dir)
    tables = output / "tables"
    figures = output / "figures"
    tables.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)
    case_catalog = load_case_catalog()
    external_evidence_ledger = load_external_evidence()

    windows, weee_evidence = build_weee_windows(weee_archive, settings.data)
    high_resolution_config = settings.data.model_copy(update={"stride_seconds": 5})
    high_resolution, _ = build_weee_windows(weee_archive, high_resolution_config)
    benchmark = run_loso_benchmark(windows, settings)

    external_all_frame, external_evidence = load_paee2026(paee2026_workbook, primary_analysis=False)
    external_primary_frame = external_all_frame[
        ~external_all_frame["analysis_code_global_exclusion"]
        & ~external_all_frame["implausible_device_value"]
    ].copy()
    external_primary_result = audit_paee2026(
        external_primary_frame,
        repetitions=settings.evaluation.bootstrap_repetitions,
        seed=settings.seed + 70_001,
    )
    external_all_result = audit_paee2026(
        external_all_frame,
        repetitions=settings.evaluation.bootstrap_repetitions,
        seed=settings.seed + 70_101,
    )
    transferability_gate = build_transferability_gate(external_primary_frame.columns)
    subgroup, disparities = _fairness_tables(benchmark.predictions, settings)
    decisions = _decision_tables(benchmark.predictions, settings)

    prediction_columns = [
        GROUP_COLUMN,
        "activity",
        "activity_family",
        "window_start",
        "y_true",
        "apple_raw",
        "cohort_affine",
        "protocol_met_baseline",
        "ensemble",
        "interval_lower",
        "interval_upper",
        "compact_interval_lower",
        "compact_interval_upper",
        "outer_fold",
    ]
    benchmark.predictions[prediction_columns].to_csv(tables / "loso_predictions.csv", index=False)
    benchmark.metrics.to_csv(tables / "model_metrics.csv", index=False)
    benchmark.bootstrap.to_csv(tables / "cluster_bootstrap.csv", index=False)
    subgroup.to_csv(tables / "subgroup_audit.csv", index=False)
    disparities.to_csv(tables / "subgroup_disparities.csv", index=False)
    external_primary_result.bootstrap.to_csv(tables / "external_bootstrap.csv", index=False)
    external_primary_result.subgroups.to_csv(tables / "external_subgroup_audit.csv", index=False)
    decisions.to_csv(tables / "decision_impact_scenarios.csv", index=False)
    _write_json(tables / "fold_diagnostics.json", benchmark.fold_diagnostics)
    _write_json(tables / "transferability_gate.json", transferability_gate)
    _write_json(tables / "case_catalog.json", case_catalog.model_dump(mode="json"))
    _write_json(tables / "external_evidence.json", external_evidence_ledger.model_dump(mode="json"))

    model_error_figure(benchmark.metrics, figures / "model_error.png")
    observed_predicted_figure(benchmark.predictions, figures / "observed_predicted.png")
    coverage_by_activity_figure(benchmark.predictions, figures / "coverage_by_activity.png")
    external_agreement_figure(external_all_frame, figures / "external_agreement.png")

    evidence = {
        "weee": _safe_evidence(weee_evidence),
        "apple_watch_paee_2026": _safe_evidence(external_evidence),
    }
    context = _report_context(
        benchmark=benchmark,
        evidence=evidence,
        high_resolution_rows=len(high_resolution),
        external_primary=external_primary_result.summary,
        external_all=external_all_result.summary,
        external_bootstrap=external_primary_result.bootstrap,
        transferability_gate=transferability_gate,
        subgroup=subgroup,
        disparities=disparities,
        external_subgroups=external_primary_result.subgroups,
        decisions=decisions,
        case_catalog=case_catalog,
        external_evidence=external_evidence_ledger,
        elapsed_seconds=perf_counter() - started,
    )
    render_report(context, output / "report.html")

    generated_files = sorted(
        path for path in output.rglob("*") if path.is_file() and path.name != "run_manifest.json"
    )
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "project_version": __version__,
        "generated_at": context["generated_at"],
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "numpy": version("numpy"),
            "pandas": version("pandas"),
            "scikit_learn": version("scikit-learn"),
        },
        "seed": settings.seed,
        "data_evidence": evidence,
        "primary_non_overlapping_windows": len(windows),
        "high_resolution_overlapping_windows": len(high_resolution),
        "outer_test_participants": windows[GROUP_COLUMN].nunique(),
        "external_primary_participants": len(external_primary_frame),
        "external_transferability": {
            "status": transferability_gate["status"],
            "passed": transferability_gate["passed"],
        },
        "case_catalog": {
            "case_count": len(case_catalog.cases),
            "capability_count": len(case_catalog.capabilities),
            "case_ids": [case.id for case in case_catalog.cases],
        },
        "external_evidence": external_evidence_ledger.model_dump(mode="json"),
        "interval": benchmark.interval,
        "compact_interval": benchmark.compact_interval,
        "elapsed_seconds": context["elapsed_seconds"],
        "outputs": {
            str(path.relative_to(output)): f"sha256:{checksum(path)}" for path in generated_files
        },
        "claims_boundary": [
            "WEEE predictions are outer-fold estimates for unseen participants.",
            "The 2026 cohort audits raw Apple Watch totals; it is not a transfer test of the WEEE model.",
            "Projected mass differences are fixed-assumption sensitivity scenarios, not forecasts.",
            "No medical diagnosis or treatment recommendation is produced.",
        ],
    }
    _write_json(output / "run_manifest.json", manifest)
    return manifest
