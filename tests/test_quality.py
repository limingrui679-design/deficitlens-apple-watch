from __future__ import annotations

from pathlib import Path

from deficitlens.quality import evaluate_quality


def test_quality_rubric_totals_100(tmp_path: Path) -> None:
    result = evaluate_quality(tmp_path)
    assert result["maximum"] == 100
    assert result["score"] < 100
    assert result["status"] == "iteration-required"


def test_quality_can_audit_checkout() -> None:
    root = Path(__file__).resolve().parents[1]
    result = evaluate_quality(root)
    assert result["rubric_version"] == 3
    assert result["maximum"] == 100
    assert len(result["checks"]) == 42
