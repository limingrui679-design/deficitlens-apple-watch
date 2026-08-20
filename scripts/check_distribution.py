#!/usr/bin/env python3
"""Check built wheel/sdist members for traversal and required runtime resources."""

from __future__ import annotations

import argparse
import tarfile
import zipfile
from pathlib import Path, PurePosixPath

REQUIRED_SUFFIXES = {
    "src/deficitlens/resources/case_catalog.yml",
    "src/deficitlens/resources/external_evidence.json",
    "src/deficitlens/reporting/templates/personal_audit.html.j2",
    "src/deficitlens/reporting/templates/report.html.j2",
    "deficitlens/resources/case_catalog.yml",
    "deficitlens/resources/external_evidence.json",
    "deficitlens/reporting/templates/personal_audit.html.j2",
    "deficitlens/reporting/templates/report.html.j2",
}


def members(path: Path) -> list[str]:
    """Read member names from a wheel/zip or gzipped source archive."""

    if path.suffix == ".whl" or path.suffix == ".zip":
        with zipfile.ZipFile(path) as archive:
            return archive.namelist()
    if path.name.endswith((".tar.gz", ".tgz")):
        with tarfile.open(path, mode="r:gz") as archive:
            return archive.getnames()
    raise ValueError(f"unsupported distribution archive: {path}")


def audit_distribution(path: Path) -> list[str]:
    """Return unsafe paths or missing resource failures."""

    names = members(path)
    failures: list[str] = []
    for name in names:
        pure = PurePosixPath(name)
        if pure.is_absolute() or ".." in pure.parts or "" in pure.parts:
            failures.append(f"unsafe archive member: {name}")
    expected = {item for item in REQUIRED_SUFFIXES if item.startswith("deficitlens/")}
    if path.name.endswith((".tar.gz", ".tgz")):
        expected = {item for item in REQUIRED_SUFFIXES if item.startswith("src/")}
    for suffix in sorted(expected):
        if not any(name.endswith(suffix) for name in names):
            failures.append(f"missing packaged resource: {suffix}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("archives", nargs="+", type=Path)
    args = parser.parse_args()
    failed = False
    for archive in args.archives:
        if not archive.is_file():
            print(f"FAIL missing distribution: {archive}")
            failed = True
            continue
        failures = audit_distribution(archive)
        if failures:
            failed = True
            for failure in failures:
                print(f"FAIL {archive}: {failure}")
        else:
            print(f"PASS {archive} ({len(members(archive))} members)")
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
