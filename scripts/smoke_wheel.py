#!/usr/bin/env python3
"""Install the built wheel in an isolated environment and exercise bundled resources."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("wheel", type=Path)
    args = parser.parse_args()
    wheel = args.wheel.resolve()
    if not wheel.is_file():
        raise SystemExit(f"Wheel not found: {args.wheel}")
    with tempfile.TemporaryDirectory(prefix="deficitlens-wheel-") as temporary:
        root = Path(temporary)
        installed = root / "installed"
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(installed)
        commands = [
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--quiet",
                "--no-deps",
                "--target",
                str(installed),
                str(wheel),
            ],
            [
                sys.executable,
                "-c",
                "import deficitlens; print(deficitlens.__file__); "
                "assert __import__('pathlib').Path(deficitlens.__file__).resolve().is_relative_to("
                "(__import__('pathlib').Path.cwd() / 'installed').resolve())",
            ],
            [sys.executable, "-m", "deficitlens", "registry"],
            [
                sys.executable,
                "-m",
                "deficitlens",
                "demo",
                "--output",
                str(root / "demo"),
            ],
        ]
        for command in commands:
            subprocess.run(command, cwd=root, check=True, env=environment)
        required = {
            root / "demo" / "summary.json",
            root / "demo" / "daily_summary.csv",
            root / "demo" / "energy_uncertainty_scenarios.csv",
        }
        if not all(path.is_file() for path in required):
            raise SystemExit("Installed-wheel demo did not produce every expected artifact")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
