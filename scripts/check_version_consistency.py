#!/usr/bin/env python3
"""Require one release version across source, metadata, citation, changelog, and evidence."""

from __future__ import annotations

import json
from pathlib import Path

import tomllib
import yaml


def version_failures(root: Path) -> list[str]:
    """Return mismatched release-version surfaces."""

    pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    expected = str(pyproject["project"]["version"])
    citation = yaml.safe_load((root / "CITATION.cff").read_text(encoding="utf-8"))
    manifest = json.loads(
        (root / "artifacts/verified/run_manifest.json").read_text(encoding="utf-8")
    )
    version_source = (root / "src/deficitlens/version.py").read_text(encoding="utf-8")
    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    report = (root / "artifacts/verified/report.html").read_text(encoding="utf-8")
    observed = {
        "version module": f'__version__ = "{expected}"' in version_source,
        "CITATION.cff": str(citation.get("version")) == expected,
        "preferred citation": str(citation.get("preferred-citation", {}).get("version"))
        == expected,
        "verified manifest": str(manifest.get("project_version")) == expected,
        "changelog": f"## {expected} " in changelog,
        "verified report": f"version {expected}" in report.lower(),
    }
    return [
        f"{surface} does not match {expected}" for surface, passed in observed.items() if not passed
    ]


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    failures = version_failures(root)
    if failures:
        for failure in failures:
            print(f"FAIL {failure}")
        return 1
    version = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"][
        "version"
    ]
    print(f"PASS version consistency ({version})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
