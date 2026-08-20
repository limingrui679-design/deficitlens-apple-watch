from __future__ import annotations

import json
import zipfile
from pathlib import Path

from scripts.check_distribution import audit_distribution
from scripts.check_docs import broken_links
from scripts.check_external_evidence import validate_ledger
from scripts.check_html import audit_html
from scripts.check_repository_safety import audit_repository
from scripts.check_version_consistency import version_failures


def test_html_audit_accepts_portable_semantics_and_rejects_missing_alt(tmp_path: Path) -> None:
    asset = tmp_path / "figure.png"
    asset.write_bytes(b"png")
    valid = tmp_path / "valid.html"
    valid.write_text(
        '<html lang="en"><head><title>Audit</title></head><body>'
        '<a href="#main">Skip</a><main id="main"><img src="figure.png" alt="Result">'
        '<label for="choice">Choice</label><select id="choice"></select></main></body></html>',
        encoding="utf-8",
    )
    assert audit_html(valid) == []
    invalid = tmp_path / "invalid.html"
    invalid.write_text(
        '<html><head><title></title></head><body><main><img src="missing.png"></main></body></html>',
        encoding="utf-8",
    )
    failures = audit_html(invalid)
    assert "missing html lang" in failures
    assert "missing skip link to #main" in failures
    assert any("alt text" in failure for failure in failures)
    assert any("missing local assets" in failure for failure in failures)


def test_docs_and_repository_safety_fail_closed(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("[missing](docs/nope.md)\n", encoding="utf-8")
    assert broken_links(tmp_path) == ["README.md -> missing: docs/nope.md"]
    fake_key = "AK" + "IA" + "1234567890ABCDEF"
    (tmp_path / "credential.txt").write_text(fake_key + "\n", encoding="utf-8")
    findings = audit_repository(tmp_path)
    assert any("aws_access_key" in finding for finding in findings)


def test_external_ledger_and_archive_checks(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.json"
    ledger.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "publication_status": "local_release_candidate",
                "public_repository_verified": False,
                "observed_public_stars": None,
                "boundary": "Tests and synthetic demos are not adoption or impact.",
                "independent_method_reviews": 0,
                "independent_reproductions": 0,
                "structured_usability_participants": 0,
                "structured_accessibility_reviews": 0,
                "production_deployments": 0,
                "organizational_adoptions": 0,
                "documented_real_users": 0,
                "real_world_impact_evaluations": 0,
            }
        ),
        encoding="utf-8",
    )
    assert validate_ledger(ledger) == []
    unsafe = tmp_path / "unsafe.whl"
    with zipfile.ZipFile(unsafe, mode="w") as archive:
        archive.writestr("../escape.txt", "unsafe")
    failures = audit_distribution(unsafe)
    assert any("unsafe archive member" in failure for failure in failures)
    assert any("missing packaged resource" in failure for failure in failures)


def test_release_version_surfaces_match() -> None:
    root = Path(__file__).resolve().parents[1]
    assert version_failures(root) == []
