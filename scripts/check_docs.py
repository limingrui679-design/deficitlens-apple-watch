#!/usr/bin/env python3
"""Check relative Markdown links without depending on network availability."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
EXTERNAL_SCHEMES = ("http://", "https://", "mailto:", "data:")


def markdown_files(root: Path) -> list[Path]:
    """Return public Markdown sources, excluding build/cache directories."""

    ignored = {".git", ".mypy_cache", ".pytest_cache", ".ruff_cache", "build", "dist"}
    return sorted(
        path
        for path in root.rglob("*.md")
        if not ignored.intersection(path.relative_to(root).parts)
    )


def broken_links(root: Path) -> list[str]:
    """Return unresolved local link targets."""

    failures: list[str] = []
    for document in markdown_files(root):
        content = document.read_text(encoding="utf-8")
        for raw_target in LINK.findall(content):
            target = raw_target.strip().strip("<>").split(" ", 1)[0]
            if not target or target.startswith("#") or target.startswith(EXTERNAL_SCHEMES):
                continue
            local_part = unquote(target.split("#", 1)[0].split("?", 1)[0])
            candidate = (document.parent / local_part).resolve()
            try:
                candidate.relative_to(root.resolve())
            except ValueError:
                failures.append(f"{document.relative_to(root)} -> outside repository: {target}")
                continue
            if not candidate.exists():
                failures.append(f"{document.relative_to(root)} -> missing: {target}")
    return failures


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    failures = broken_links(root)
    if failures:
        for failure in failures:
            print(f"FAIL {failure}")
        return 1
    print(f"PASS local Markdown links ({len(markdown_files(root))} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
