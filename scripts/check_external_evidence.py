#!/usr/bin/env python3
"""Validate the explicit external-evidence ledger and its zero-state semantics."""

from __future__ import annotations

import json
from pathlib import Path

COUNT_FIELDS = {
    "independent_method_reviews",
    "independent_reproductions",
    "structured_usability_participants",
    "structured_accessibility_reviews",
    "production_deployments",
    "organizational_adoptions",
    "documented_real_users",
    "real_world_impact_evaluations",
}


def validate_ledger(path: Path) -> list[str]:
    """Return failures without inferring unrecorded evidence."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    failures: list[str] = []
    if payload.get("schema_version") != 2:
        failures.append("schema_version must be 2")
    for field in sorted(COUNT_FIELDS):
        value = payload.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            failures.append(f"{field} must be a non-negative integer")
    status = payload.get("publication_status")
    if status == "local_release_candidate":
        if payload.get("public_repository_verified") is not False:
            failures.append("local release candidate cannot claim a verified public repository")
        if payload.get("observed_public_stars") is not None:
            failures.append("public stars must be null before a verified public repository exists")
        if payload.get("public_repository_url") is not None:
            failures.append("public repository URL must be null before publication")
    elif status == "published":
        if payload.get("public_repository_verified") is not True:
            failures.append("published ledger requires a verified public repository")
        repository_url = payload.get("public_repository_url")
        if not isinstance(repository_url, str) or not repository_url.startswith(
            "https://github.com/"
        ):
            failures.append("published ledger requires a canonical GitHub repository URL")
        stars = payload.get("observed_public_stars")
        if not isinstance(stars, int) or isinstance(stars, bool) or stars < 0:
            failures.append("published ledger requires an observed non-negative Star count")
    else:
        failures.append("publication_status must be local_release_candidate or published")
    boundary = str(payload.get("boundary", "")).lower()
    for term in ("tests", "synthetic", "adoption", "impact"):
        if term not in boundary:
            failures.append(f"boundary must explain {term}")
    return failures


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    path = root / "evidence/external-evidence.json"
    bundled = root / "src/deficitlens/resources/external_evidence.json"
    if not path.is_file():
        print(f"FAIL missing ledger: {path}")
        return 1
    if not bundled.is_file() or path.read_bytes() != bundled.read_bytes():
        print("FAIL checkout and wheel external-evidence ledgers differ")
        return 1
    failures = validate_ledger(path)
    if failures:
        for failure in failures:
            print(f"FAIL {failure}")
        return 1
    print(f"PASS external evidence ledger ({len(COUNT_FIELDS)} explicit count fields)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
