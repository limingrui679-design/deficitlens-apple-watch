"""Command-line interface for reproducible and privacy-preserving workflows."""

from __future__ import annotations

import argparse
import json
from importlib.resources import files
from pathlib import Path
from typing import Any

from deficitlens.config import load_settings
from deficitlens.data.apple_health import parse_apple_health_records
from deficitlens.data.registry import fetch_registered_dataset, load_registry
from deficitlens.personal import daily_apple_health_summary, energy_uncertainty_scenario
from deficitlens.pipeline import run_verified_pipeline


def project_root() -> Path:
    """Resolve the source checkout root from this module."""

    return Path(__file__).resolve().parents[2]


def bundled_resource(name: str) -> Path:
    """Return a resource path that also works from an installed wheel."""

    return Path(str(files("deficitlens.resources").joinpath(name)))


def checkout_or_bundled(relative: str, bundled_name: str) -> Path:
    """Prefer editable-checkout files, then fall back to wheel resources."""

    candidate = project_root() / relative
    return candidate if candidate.exists() else bundled_resource(bundled_name)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _registry_command(args: argparse.Namespace) -> int:
    registry = load_registry(args.registry)
    for dataset_id, entry in registry["datasets"].items():
        access = entry.get("access", "public")
        print(f"{dataset_id:24} {access:52} {entry['role']}")
    return 0


def _fetch_command(args: argparse.Namespace) -> int:
    registry = load_registry(args.registry)
    entry: dict[str, Any] = registry["datasets"].get(args.dataset, {})
    if not entry:
        raise SystemExit(f"Unknown dataset: {args.dataset}")
    if not entry.get("download_url") and not entry.get("files"):
        raise SystemExit(
            f"{args.dataset} is not automatically downloadable: "
            f"{entry.get('access', 'no public URL')}"
        )
    for path in fetch_registered_dataset(args.dataset, args.registry, args.output):
        print(path)
    return 0


def _benchmark_command(args: argparse.Namespace) -> int:
    settings = load_settings(args.config)
    manifest = run_verified_pipeline(
        weee_archive=args.weee,
        paee2026_workbook=args.paee2026,
        output_dir=args.output,
        settings=settings,
    )
    print(f"Report: {Path(args.output) / 'report.html'}")
    print(
        "Verified participants: "
        f"{manifest['outer_test_participants']} WEEE + "
        f"{manifest['external_primary_participants']} external"
    )
    return 0


def _apple_health_command(args: argparse.Namespace) -> int:
    records = parse_apple_health_records(
        args.xml,
        apple_watch_only=not args.include_non_watch,
        redact_source_names=not args.keep_source_names,
    )
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    daily = daily_apple_health_summary(records)
    scenarios = energy_uncertainty_scenario(daily) if not daily.empty else daily
    daily.to_csv(output / "daily_summary.csv", index=False)
    scenarios.to_csv(output / "energy_uncertainty_scenarios.csv", index=False)
    summary = {
        "records_read": len(records),
        "days": len(daily),
        "apple_watch_only": not args.include_non_watch,
        "source_names_redacted": not args.keep_source_names,
        "raw_records_written": False,
        "warning": "Sensitivity scenarios are not inferred corrections or medical advice.",
    }
    _write_json(output / "summary.json", summary)
    print(output)
    return 0


def _demo_command(args: argparse.Namespace) -> int:
    sample = checkout_or_bundled("examples/apple_health_sample.xml", "apple_health_sample.xml")
    namespace = argparse.Namespace(
        xml=sample,
        output=args.output,
        include_non_watch=False,
        keep_source_names=False,
    )
    return _apple_health_command(namespace)


def build_parser() -> argparse.ArgumentParser:
    """Construct the public CLI parser."""

    checkout = project_root()
    root = checkout if (checkout / "pyproject.toml").exists() else Path.cwd()
    registry_default = checkout_or_bundled("data/registry.yml", "registry.yml")
    config_default = checkout_or_bundled("configs/default.yml", "default.yml")
    parser = argparse.ArgumentParser(
        prog="deficitlens",
        description="Audit Apple Watch energy estimates without hiding uncertainty or leakage.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    registry = subparsers.add_parser("registry", help="List data sources, roles, and access")
    registry.add_argument("--registry", type=Path, default=registry_default)
    registry.set_defaults(func=_registry_command)

    fetch = subparsers.add_parser("fetch", help="Download and checksum a public registered set")
    fetch.add_argument("dataset", choices=("weee", "apple_watch_paee_2026"))
    fetch.add_argument("--registry", type=Path, default=registry_default)
    fetch.add_argument("--output", type=Path, default=root / "data" / "raw")
    fetch.set_defaults(func=_fetch_command)

    benchmark = subparsers.add_parser(
        "benchmark", help="Run the nested benchmark and build the evidence report"
    )
    benchmark.add_argument("--weee", type=Path, required=True, help="WEEE dataset.zip")
    benchmark.add_argument(
        "--paee2026", type=Path, required=True, help="2026 OSF subject-level workbook"
    )
    benchmark.add_argument("--config", type=Path, default=config_default)
    benchmark.add_argument("--output", type=Path, default=root / "artifacts" / "verified")
    benchmark.set_defaults(func=_benchmark_command)

    health = subparsers.add_parser(
        "apple-health", help="Create local-only daily summaries from Apple Health export.xml"
    )
    health.add_argument("--xml", type=Path, required=True)
    health.add_argument("--output", type=Path, required=True)
    health.add_argument("--include-non-watch", action="store_true")
    health.add_argument(
        "--keep-source-names",
        action="store_true",
        help="Privacy-sensitive: preserve device/source names in memory (still not written)",
    )
    health.set_defaults(func=_apple_health_command)

    demo = subparsers.add_parser("demo", help="Run the bundled synthetic Apple Health example")
    demo.add_argument("--output", type=Path, default=root / "artifacts" / "demo")
    demo.set_defaults(func=_demo_command)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the requested CLI command."""

    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
