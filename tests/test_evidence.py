from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from deficitlens.evidence import ExternalEvidenceLedger, load_external_evidence


def test_external_evidence_ledger_is_explicit_and_fail_closed() -> None:
    root = Path(__file__).resolve().parents[1]
    ledger = load_external_evidence(root / "evidence/external-evidence.json")
    assert ledger.publication_status == "local_release_candidate"
    assert ledger.documented_real_users == 0
    assert ledger.observed_public_stars is None

    invalid = ledger.model_dump(mode="json")
    invalid["public_repository_verified"] = True
    with pytest.raises(ValidationError, match="cannot verify a public repository"):
        ExternalEvidenceLedger.model_validate(invalid)

    invalid = ledger.model_dump(mode="json")
    invalid["observed_public_stars"] = 0
    with pytest.raises(ValidationError, match="unobserved"):
        ExternalEvidenceLedger.model_validate(invalid)
