#!/usr/bin/env python3
"""Run release checks and persist machine-readable evidence."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter


def run_check(root: Path, name: str, arguments: list[str]) -> dict[str, object]:
    """Run one check without a shell and persist its complete combined log."""

    started = perf_counter()
    completed = subprocess.run(
        arguments,
        cwd=root,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    log_dir = root / "artifacts" / "verification" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{name}.log"
    sanitized_output = completed.stdout.replace(str(root), ".").replace(str(Path.home()), "~")
    log_path.write_text(sanitized_output, encoding="utf-8")
    display_command = [
        "python" if index == 0 else argument.replace(str(root), ".").replace(str(Path.home()), "~")
        for index, argument in enumerate(arguments)
    ]
    return {
        "passed": completed.returncode == 0,
        "exit_code": completed.returncode,
        "elapsed_seconds": perf_counter() - started,
        "command": display_command,
        "log": str(log_path.relative_to(root)),
    }


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    python = sys.executable
    verification_dir = root / "artifacts" / "verification"
    verification_dir.mkdir(parents=True, exist_ok=True)
    checks = {
        "lint": [python, "-m", "ruff", "check", "."],
        "format": [python, "-m", "ruff", "format", "--check", "."],
        "typecheck": [python, "-m", "mypy", "src", "scripts"],
        "tests": [
            python,
            "-m",
            "pytest",
            "--cov=deficitlens",
            "--cov-branch",
            "--cov-report=term-missing",
            f"--cov-report=json:{verification_dir / 'coverage.json'}",
        ],
        "cli_demo": [
            python,
            "-m",
            "deficitlens",
            "demo",
            "--output",
            str(verification_dir / "demo"),
        ],
        "resource_sync": [python, "scripts/check_resources.py"],
        "build": [
            python,
            "-m",
            "build",
            "--outdir",
            str(verification_dir / "dist"),
        ],
    }
    results: dict[str, dict[str, object]] = {}
    for name, command in checks.items():
        result = run_check(root, name, command)
        results[name] = result
        status = "PASS" if result["passed"] else "FAIL"
        print(f"{status:4} {name:10} {result['elapsed_seconds']:.2f}s")
    wheels = sorted((verification_dir / "dist").glob("*.whl"))
    wheel_command = (
        [python, "scripts/smoke_wheel.py", str(wheels[-1])]
        if wheels and bool(results["build"]["passed"])
        else [python, "-c", "raise SystemExit('wheel build unavailable')"]
    )
    wheel_result = run_check(root, "wheel_smoke", wheel_command)
    results["wheel_smoke"] = wheel_result
    wheel_status = "PASS" if wheel_result["passed"] else "FAIL"
    print(f"{wheel_status:4} {'wheel_smoke':10} {wheel_result['elapsed_seconds']:.2f}s")
    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "python": sys.version,
        "checks": results,
        "all_passed": all(bool(result["passed"]) for result in results.values()),
    }
    target = verification_dir / "verification.json"
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if payload["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
