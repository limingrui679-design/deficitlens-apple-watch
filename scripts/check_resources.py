#!/usr/bin/env python3
"""Fail when wheel-bundled defaults drift from checkout-facing copies."""

from __future__ import annotations

from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    pairs = (
        (root / "configs/default.yml", root / "src/deficitlens/resources/default.yml"),
        (root / "data/registry.yml", root / "src/deficitlens/resources/registry.yml"),
        (root / "cases/catalog.yml", root / "src/deficitlens/resources/case_catalog.yml"),
        (
            root / "evidence/external-evidence.json",
            root / "src/deficitlens/resources/external_evidence.json",
        ),
    )
    for public, bundled in pairs:
        if public.read_bytes() != bundled.read_bytes():
            print(f"Resource drift: {public.relative_to(root)} != {bundled.relative_to(root)}")
            return 1
    print("Bundled config, registry, case catalog, and evidence ledger are synchronized.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
