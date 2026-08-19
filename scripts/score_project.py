#!/usr/bin/env python3
"""Write and display the evidence-backed 100-point quality score."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from deficitlens.quality import evaluate_quality


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--label", default="manual audit")
    parser.add_argument("--append-log", action="store_true")
    args = parser.parse_args()
    result = evaluate_quality(args.root)
    result["evaluated_at"] = datetime.now(UTC).isoformat()
    result["label"] = args.label
    output = args.output or args.root / "artifacts" / "quality-score.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.append_log:
        log = args.root / "artifacts" / "quality-history.jsonl"
        with log.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(result, sort_keys=True) + "\n")
    failed = [check["check_id"] for check in result["checks"] if not check["passed"]]
    print(f"Quality score: {result['score']}/{result['maximum']} ({result['status']})")
    if failed:
        print("Failed gates: " + ", ".join(failed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
