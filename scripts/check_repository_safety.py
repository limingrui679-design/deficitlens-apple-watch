#!/usr/bin/env python3
"""Fail on high-confidence secret, private-data, or local-path disclosure risks."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

TEXT_LIMIT = 2_000_000
FORBIDDEN_SUFFIXES = {".db", ".heic", ".key", ".p12", ".pem", ".sqlite", ".xlsx", ".zip"}
FORBIDDEN_NAMES = {"export.xml", "export_cda.xml"}
ALLOWED_XML = {
    Path("examples/apple_health_sample.xml"),
    Path("src/deficitlens/resources/apple_health_sample.xml"),
}
SECRET_PATTERNS = {
    "aws_access_key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "github_token": re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"),
    "openai_style_key": re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
}
ABSOLUTE_HOME_PATTERNS = {
    "posix_home": re.compile(r"/(?:Users|home)/[^/\s\"']+/"),
    "windows_home": re.compile(r"[A-Za-z]:[\\/]+Users[\\/]+[^\\/\s\"']+[\\/]"),
}


def candidate_paths(root: Path) -> list[Path]:
    """Return tracked and non-ignored untracked files, with a no-Git fallback."""

    completed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=root,
        check=False,
        stdout=subprocess.PIPE,
    )
    if completed.returncode == 0:
        names = [item for item in completed.stdout.split(b"\0") if item]
        return sorted(root / item.decode("utf-8", errors="surrogateescape") for item in names)
    ignored_parts = {".git", ".mypy_cache", ".pytest_cache", ".ruff_cache", "build", "dist"}
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and not ignored_parts.intersection(path.relative_to(root).parts)
    )


def audit_repository(root: Path) -> list[str]:
    """Return deterministic safety findings for the project tree."""

    findings: list[str] = []
    for path in candidate_paths(root):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        lower_name = path.name.lower()
        if lower_name in FORBIDDEN_NAMES and relative not in ALLOWED_XML:
            findings.append(f"private export filename: {relative}")
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            findings.append(f"forbidden tracked data/key type: {relative}")
        if path.stat().st_size > TEXT_LIMIT:
            continue
        raw = path.read_bytes()
        if b"\x00" in raw:
            continue
        text = raw.decode("utf-8", errors="ignore")
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                findings.append(f"{label}: {relative}")
        for label, pattern in ABSOLUTE_HOME_PATTERNS.items():
            if pattern.search(text):
                findings.append(f"{label}: {relative}")
    return sorted(set(findings))


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    findings = audit_repository(root)
    if findings:
        for finding in findings:
            print(f"FAIL {finding}")
        return 1
    print(f"PASS repository safety ({len(candidate_paths(root))} candidate files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
