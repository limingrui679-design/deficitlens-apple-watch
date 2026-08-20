"""Evidence-backed release rubric; 100 means controllable release gates passed."""

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
        QualityCheck("registry", "data_evidence", 3, registry_valid, "versioned source registry"),
        QualityCheck(
            "data_cards",
            "data_evidence",
            2,
            _contains(
                project / "docs/data-cards.md", "WEEE", "Apple Watch PAEE 2026", "restricted"
            ),
            "licenses, access, roles, and limits",
        ),
        QualityCheck(
            "two_public_datasets",
            "data_evidence",
            4,
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
            "every committed derived artifact is rehashed",
        ),
        QualityCheck(
            "data_density",
            "data_evidence",
            2,
            manifest.get("primary_non_overlapping_windows", 0) >= 800
            and manifest.get("high_resolution_overlapping_windows", 0) >= 4000,
            "primary and explicitly sensitivity-only window counts",
        ),
        QualityCheck(
            "case_catalog",
            "data_evidence",
            3,
            manifest.get("case_catalog", {}).get("case_count") == 4
            and manifest.get("case_catalog", {}).get("capability_count", 0) >= 8
            and _verification_passed(verification, "case_catalog"),
            "four validated, complementary evidence paths",
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
            "three-way participant separation and deployable context",
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
            2,
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
            "validated fixed seed and configuration",
        ),
        QualityCheck(
            "external_audit",
            "validation",
            3,
            manifest.get("external_primary_participants") == 52
            and (project / "artifacts/verified/tables/external_subgroup_audit.csv").exists(),
            "independent Series 8 raw-device agreement audit",
        ),
        QualityCheck(
            "external_bootstrap",
            "validation",
            2,
            (project / "artifacts/verified/tables/external_bootstrap.csv").exists()
            and _contains(
                project / "src/deficitlens/evaluation/external.py", "clustered_bootstrap"
            ),
            "participant-bootstrap uncertainty for external MAE and bias",
        ),
        QualityCheck(
            "transferability_gate",
            "validation",
            2,
            manifest.get("external_transferability", {}).get("status") == "blocked_model_transfer"
            and manifest.get("external_transferability", {}).get("passed") is False
            and (project / "artifacts/verified/tables/transferability_gate.json").exists(),
            "machine-readable refusal of unsupported model transfer",
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
            3,
            (project / "artifacts/verified/tables/subgroup_audit.csv").exists()
            and (project / "artifacts/verified/tables/subgroup_disparities.csv").exists(),
            "support-aware subgroup errors and disparities",
        ),
        QualityCheck(
            "decision_impact",
            "validation",
            4,
            (project / "artifacts/verified/tables/decision_impact_scenarios.csv").exists()
            and _contains(project / "docs/methodology.md", "weight forecast", "3, 5, or 7")
            and _contains(
                project / "src/deficitlens/evaluation/decision.py",
                "active_days_per_week",
                "kcal_per_kg_values",
            ),
            "multi-assumption fat-loss sensitivity analysis",
        ),
        QualityCheck(
            "interval_coverage",
            "validation",
            2,
            float(manifest.get("interval", {}).get("coverage", 0.0)) >= 0.90,
            "primary cluster interval empirical coverage meets target",
        ),
        QualityCheck(
            "model_card",
            "validation",
            2,
            _contains(project / "docs/model-card.md", "Out-of-scope use", "Failure modes"),
            "intended use, exclusions, and failure modes",
        ),
        QualityCheck(
            "apple_health_privacy",
            "privacy_security",
            3,
            _contains(
                project / "src/deficitlens/data/apple_health.py",
                "defusedxml",
                "iterparse",
                "redact_source_names",
                "apple_watch_only",
            ),
            "hardened streaming filtered parser",
        ),
        QualityCheck(
            "privacy_documentation",
            "privacy_security",
            2,
            (project / "docs/privacy.md").exists()
            and _contains(project / ".gitignore", "export.xml", "data/raw"),
            "threat model and ignore rules",
        ),
        QualityCheck(
            "no_private_raw",
            "privacy_security",
            2,
            _no_private_raw_files(project),
            "no raw archives, databases, or Health exports",
        ),
        QualityCheck(
            "explicit_sensitive_export",
            "privacy_security",
            1,
            _contains(
                project / "src/deficitlens/data/apple_health.py",
                "acknowledge_sensitive_output",
                "PermissionError",
                "token_hex",
            ),
            "row-level output acknowledgement and per-run hashing salt",
        ),
        QualityCheck(
            "repository_safety",
            "privacy_security",
            2,
            _verification_passed(verification, "repo_safety"),
            "tracked/unignored private-file, secret, and local-path scan",
        ),
        QualityCheck(
            "dependency_audit",
            "privacy_security",
            2,
            _verification_passed(verification, "dependency_audit"),
            "known-vulnerability audit of the verified dependency snapshot",
        ),
        QualityCheck(
            "lint", "software_release", 2, _verification_passed(verification, "lint"), "Ruff lint"
        ),
        QualityCheck(
            "format",
            "software_release",
            1,
            _verification_passed(verification, "format"),
            "Ruff format",
        ),
        QualityCheck(
            "typecheck",
            "software_release",
            2,
            _verification_passed(verification, "typecheck"),
            "strict Mypy",
        ),
        QualityCheck(
            "tests",
            "software_release",
            3,
            _verification_passed(verification, "tests"),
            "Pytest suite",
        ),
        QualityCheck(
            "coverage",
            "software_release",
            3,
            float(coverage.get("totals", {}).get("percent_covered", 0.0)) >= 85.0,
            "branch coverage >= 85%",
        ),
        QualityCheck(
            "distribution",
            "software_release",
            2,
            _verification_passed(verification, "build")
            and _verification_passed(verification, "distribution"),
            "wheel/sdist build, resource, and archive safety checks",
        ),
        QualityCheck(
            "wheel_smoke",
            "software_release",
            2,
            _verification_passed(verification, "wheel_smoke"),
            "isolated installed-wheel CLI and resource smoke test",
        ),
        QualityCheck(
            "cli_demo",
            "software_release",
            1,
            _verification_passed(verification, "cli_demo"),
            "offline synthetic CLI report",
        ),
        QualityCheck(
            "resource_sync",
            "software_release",
            1,
            _verification_passed(verification, "resource_sync")
            and _verification_passed(verification, "version_consistency"),
            "checkout/wheel resources and release-version surfaces match",
        ),
        QualityCheck(
            "readme",
            "project_docs",
            1,
            _contains(project / "README.md", "Quick start", "Case paths", "External evidence"),
            "decision-centered README",
        ),
        QualityCheck(
            "license_citation",
            "project_docs",
            1,
            (project / "LICENSE").exists() and (project / "CITATION.cff").exists(),
            "license and citation metadata",
        ),
        QualityCheck(
            "ci_security",
            "project_docs",
            1,
            (project / ".github/workflows/ci.yml").exists()
            and (project / ".github/workflows/security.yml").exists(),
            "compatibility CI and scheduled security workflow",
        ),
        QualityCheck(
            "governance",
            "project_docs",
            1,
            all(
                (project / name).exists()
                for name in ("CONTRIBUTING.md", "SECURITY.md", "SUPPORT.md", "CODE_OF_CONDUCT.md")
            ),
            "contribution, conduct, security, and support contracts",
        ),
        QualityCheck(
            "verified_report",
            "project_docs",
            1,
            (project / "artifacts/verified/report.html").exists()
            and (project / "docs/reproducibility.md").exists()
            and _verification_passed(verification, "html_audit"),
            "portable accessible report and reproduction protocol",
        ),
        QualityCheck(
            "docs_links",
            "project_docs",
            1,
            _verification_passed(verification, "docs_links"),
            "local documentation links resolve",
        ),
        QualityCheck(
            "external_evidence_ledger",
            "project_docs",
            1,
            _verification_passed(verification, "evidence_ledger")
            and (project / "evidence/external-evidence.json").exists(),
            "external review, reproduction, adoption, and impact remain explicit",
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
        "rubric_version": 3,
        "score": score,
        "maximum": maximum,
        "status": "release-ready" if score == maximum else "iteration-required",
        "categories": categories,
        "checks": [asdict(check) for check in checks],
    }
