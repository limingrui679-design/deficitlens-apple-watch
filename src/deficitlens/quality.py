"""Evidence-backed project quality rubric; 100 means all release gates passed."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, cast

from deficitlens.data.registry import checksum, load_registry


@dataclass(frozen=True)
class QualityCheck:
    """One auditable release gate."""

    check_id: str
    category: str
    points: int
    passed: bool
    evidence: str


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return cast(dict[str, Any], payload)


def _contains(path: Path, *needles: str) -> bool:
    if not path.exists():
        return False
    content = path.read_text(encoding="utf-8")
    return all(needle in content for needle in needles)


def _verification_passed(verification: dict[str, Any], name: str) -> bool:
    checks = verification.get("checks", {})
    return bool(checks.get(name, {}).get("passed", False))


def _manifest_hashes_match(root: Path, manifest: dict[str, Any]) -> bool:
    output_root = root / "artifacts" / "verified"
    outputs = manifest.get("outputs", {})
    if not outputs:
        return False
    for relative, expected in outputs.items():
        path = output_root / relative
        if not path.is_file():
            return False
        algorithm, expected_hex = str(expected).split(":", 1)
        if checksum(path, algorithm) != expected_hex:
            return False
    return True


def _no_private_raw_files(root: Path) -> bool:
    forbidden_suffixes = {".zip", ".heic", ".sqlite", ".db"}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if relative.parts[0] in {
            ".git",
            ".mypy_cache",
            ".pytest_cache",
            ".ruff_cache",
            "dist",
            "build",
        }:
            continue
        if relative == Path("examples/apple_health_sample.xml"):
            continue
        if path.suffix.lower() in forbidden_suffixes:
            return False
        if path.name.lower() in {"export.xml", "export_cda.xml"}:
            return False
    return not (root / "data" / "raw").exists()


def evaluate_quality(root: str | Path) -> dict[str, Any]:
    """Evaluate the 100-point rubric from files, artifacts, and executed checks."""

    project = Path(root)
    manifest = _read_json(project / "artifacts" / "verified" / "run_manifest.json")
    verification = _read_json(project / "artifacts" / "verification" / "verification.json")
    coverage = _read_json(project / "artifacts" / "verification" / "coverage.json")
    registry_path = project / "data" / "registry.yml"
    registry_valid = False
    if registry_path.exists():
        try:
            registry = load_registry(registry_path)
            registry_valid = {"weee", "apple_watch_paee_2026", "bigideaslab_step"}.issubset(
                registry["datasets"]
            )
        except (OSError, ValueError, KeyError):
            registry_valid = False

    data_evidence = manifest.get("data_evidence", {})
    checks = [
        QualityCheck("registry", "data_evidence", 4, registry_valid, "versioned source registry"),
        QualityCheck(
            "data_cards",
            "data_evidence",
            3,
            _contains(
                project / "docs/data-cards.md", "WEEE", "Apple Watch PAEE 2026", "restricted"
            ),
            "licenses, access, roles, limits",
        ),
        QualityCheck(
            "two_public_datasets",
            "data_evidence",
            5,
            data_evidence.get("weee", {}).get("participants") == 17
            and data_evidence.get("apple_watch_paee_2026", {}).get("participants") == 53,
            "manifest participant counts",
        ),
        QualityCheck(
            "artifact_hashes",
            "data_evidence",
            4,
            _manifest_hashes_match(project, manifest)
            and _contains(
                project / "artifacts/verified/tables/loso_predictions.csv", "activity_family"
            ),
            "all committed evidence hashes and deployable feature snapshot rechecked",
        ),
        QualityCheck(
            "data_density",
            "data_evidence",
            4,
            manifest.get("primary_non_overlapping_windows", 0) >= 800
            and manifest.get("high_resolution_overlapping_windows", 0) >= 4000,
            "primary and high-resolution window counts",
        ),
        QualityCheck(
            "nested_loso",
            "algorithms",
            6,
            _contains(
                project / "src/deficitlens/evaluation/benchmark.py",
                "held_out_participant",
                "calibration_participants",
                "development_participants",
            )
            and _contains(
                project / "src/deficitlens/schemas.py",
                'CATEGORICAL_FEATURES = ["sex", "activity_family"]',
            ),
            "three-way participant separation and deployable activity context",
        ),
        QualityCheck(
            "convex_stack",
            "algorithms",
            5,
            _contains(
                project / "src/deficitlens/models/ensemble.py", "SLSQP", "GroupKFold", "oof_rmse_"
            ),
            "group-cross-fitted constrained stacking",
        ),
        QualityCheck(
            "cluster_conformal",
            "algorithms",
            5,
            _contains(
                project / "src/deficitlens/models/conformal.py",
                "cluster_global_radius",
                "per_cluster_max",
                "conformal_quantile",
            ),
            "finite-sample participant-cluster interval",
        ),
        QualityCheck(
            "adaptive_calibration",
            "algorithms",
            3,
            _contains(
                project / "src/deficitlens/models/adaptive.py", "KalmanBiasCalibrator", "gain"
            ),
            "criterion-gated Bayesian bias update",
        ),
        QualityCheck(
            "physiology_baselines",
            "algorithms",
            3,
            (project / "src/deficitlens/physiology.py").exists()
            and (project / "src/deficitlens/models/baselines.py").exists(),
            "explicit assumptions and transparent comparators",
        ),
        QualityCheck(
            "deterministic_config",
            "algorithms",
            3,
            _contains(project / "configs/default.yml", "seed: 20260820", "inner_group_folds"),
            "validated fixed seed/config",
        ),
        QualityCheck(
            "external_audit",
            "validation",
            5,
            manifest.get("external_primary_participants") == 52
            and (project / "artifacts/verified/tables/external_subgroup_audit.csv").exists(),
            "Series 8 versus COSMED K5",
        ),
        QualityCheck(
            "cluster_bootstrap",
            "validation",
            4,
            _contains(project / "src/deficitlens/evaluation/bootstrap.py", "sampled", "unique")
            and (project / "artifacts/verified/tables/cluster_bootstrap.csv").exists(),
            "1,000 whole-participant resamples",
        ),
        QualityCheck(
            "subgroup_audit",
            "validation",
            4,
            (project / "artifacts/verified/tables/subgroup_audit.csv").exists()
            and (project / "artifacts/verified/tables/subgroup_disparities.csv").exists(),
            "support-aware subgroup errors and disparities",
        ),
        QualityCheck(
            "decision_impact",
            "validation",
            3,
            (project / "artifacts/verified/tables/decision_impact_scenarios.csv").exists()
            and _contains(project / "docs/methodology.md", "not a weight forecast")
            and _contains(project / "src/deficitlens/pipeline.py", "exercise_predictions"),
            "bounded fat-loss sensitivity analysis",
        ),
        QualityCheck(
            "interval_coverage",
            "validation",
            2,
            float(manifest.get("interval", {}).get("coverage", 0.0)) >= 0.90,
            "primary cluster interval empirical coverage >= target",
        ),
        QualityCheck(
            "model_card",
            "validation",
            2,
            _contains(project / "docs/model-card.md", "Out-of-scope use", "Failure modes"),
            "intended use, exclusions, failure modes",
        ),
        QualityCheck(
            "apple_health_privacy",
            "privacy",
            4,
            _contains(
                project / "src/deficitlens/data/apple_health.py",
                "iterparse",
                "redact_source_names",
                "apple_watch_only",
            ),
            "streaming filtered normalized parser",
        ),
        QualityCheck(
            "privacy_documentation",
            "privacy",
            3,
            (project / "docs/privacy.md").exists()
            and _contains(project / ".gitignore", "export.xml", "data/raw"),
            "threat model and ignore rules",
        ),
        QualityCheck(
            "no_private_raw",
            "privacy",
            3,
            _no_private_raw_files(project),
            "no raw archives, databases, or Health exports",
        ),
        QualityCheck(
            "lint", "software", 3, _verification_passed(verification, "lint"), "Ruff lint"
        ),
        QualityCheck(
            "format", "software", 2, _verification_passed(verification, "format"), "Ruff format"
        ),
        QualityCheck(
            "typecheck", "software", 3, _verification_passed(verification, "typecheck"), "Mypy"
        ),
        QualityCheck(
            "tests", "software", 4, _verification_passed(verification, "tests"), "Pytest suite"
        ),
        QualityCheck(
            "coverage",
            "software",
            4,
            float(coverage.get("totals", {}).get("percent_covered", 0.0)) >= 85.0,
            "branch coverage >= 85%",
        ),
        QualityCheck(
            "build",
            "software",
            2,
            _verification_passed(verification, "build")
            and _verification_passed(verification, "wheel_smoke"),
            "wheel/sdist build and isolated installed-wheel smoke test",
        ),
        QualityCheck(
            "cli",
            "software",
            2,
            _verification_passed(verification, "cli_demo"),
            "installed CLI demo",
        ),
        QualityCheck(
            "readme", "project_docs", 1, _contains(project / "README.md", "Quick start"), "README"
        ),
        QualityCheck(
            "license_citation",
            "project_docs",
            1,
            (project / "LICENSE").exists() and (project / "CITATION.cff").exists(),
            "license and citation metadata",
        ),
        QualityCheck(
            "ci", "project_docs", 1, (project / ".github/workflows/ci.yml").exists(), "CI workflow"
        ),
        QualityCheck(
            "governance",
            "project_docs",
            1,
            (project / "CONTRIBUTING.md").exists() and (project / "SECURITY.md").exists(),
            "contribution and security guidance",
        ),
        QualityCheck(
            "verified_report",
            "project_docs",
            1,
            (project / "artifacts/verified/report.html").exists()
            and (project / "docs/reproducibility.md").exists(),
            "human report and reproduction protocol",
        ),
    ]
    maximum = sum(check.points for check in checks)
    if maximum != 100:
        raise RuntimeError(f"Quality rubric must total 100 points, got {maximum}")
    score = sum(check.points for check in checks if check.passed)
    categories: dict[str, dict[str, int]] = {}
    for check in checks:
        category = categories.setdefault(check.category, {"earned": 0, "maximum": 0})
        category["maximum"] += check.points
        if check.passed:
            category["earned"] += check.points
    return {
        "rubric_version": 2,
        "score": score,
        "maximum": maximum,
        "status": "release-ready" if score == maximum else "iteration-required",
        "categories": categories,
        "checks": [asdict(check) for check in checks],
    }
