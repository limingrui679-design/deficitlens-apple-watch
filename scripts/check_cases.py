#!/usr/bin/env python3
"""Validate case capabilities, bundled synchronization, and committed output references."""

from __future__ import annotations

from pathlib import Path

from deficitlens.cases import load_case_catalog


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    source = root / "cases/catalog.yml"
    bundled = root / "src/deficitlens/resources/case_catalog.yml"
    failures: list[str] = []
    if source.read_bytes() != bundled.read_bytes():
        failures.append("source and wheel case catalogs differ")
    catalog = load_case_catalog(source)
    for case in catalog.cases:
        for output in case.outputs:
            if output.startswith("artifacts/verified/") and not (root / output).is_file():
                failures.append(f"{case.id} references missing output: {output}")
    if failures:
        for failure in failures:
            print(f"FAIL {failure}")
        return 1
    print(
        f"PASS case catalog ({len(catalog.cases)} cases, {len(catalog.capabilities)} capabilities)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
