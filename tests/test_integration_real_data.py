from __future__ import annotations

import os
from pathlib import Path

import pytest

from deficitlens.config import load_settings
from deficitlens.data.weee import build_weee_windows


@pytest.mark.integration
def test_registered_weee_archive_when_available() -> None:
    archive = os.environ.get("DEFICITLENS_WEEE_ARCHIVE")
    if not archive:
        pytest.skip("Set DEFICITLENS_WEEE_ARCHIVE for the 652 MB public-data integration test")
    root = Path(__file__).resolve().parents[1]
    settings = load_settings(root / "configs" / "default.yml")
    windows, evidence = build_weee_windows(archive, settings.data)
    assert len(windows) == 811
    assert evidence.participants == 17
    assert "P14:cycle_low:non_monotonic_start" in evidence.notes
