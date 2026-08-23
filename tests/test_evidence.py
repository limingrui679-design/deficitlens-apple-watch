from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from deficitlens.evidence import ExternalEvidenceLedger, load_external_evidence


def test_external_evidence_ledger_is_explicit_and_fail_closed() -> None:
    root = Path(__file__).resolve().parents[1]
    ledger = load_external_evidence(root / "evidence/external-evidence.json")
    assert ledger.publication_status == "published"
    assert ledger.public_repository_verified is True
    assert ledger.public_repository_url == (
        "https://github.com/limingrui679-design/deficitlens-apple-watch"
    )
    assert ledger.documented_real_users == 0
    assert ledger.observed_public_stars == 0

    invalid = ledger.model_dump(mode="json")
    invalid["public_repository_verified"] = False
    with pytest.raises(ValidationError, match="requires a verified public repository"):
        ExternalEvidenceLedger.model_validate(invalid)

    invalid = ledger.model_dump(mode="json")
    invalid["public_repository_url"] = None
    with pytest.raises(ValidationError, match="canonical GitHub repository URL"):
        ExternalEvidenceLedger.model_validate(invalid)

    invalid = ledger.model_dump(mode="json")
    invalid["observed_public_stars"] = None
    with pytest.raises(ValidationError, match="observed public Star count"):
        ExternalEvidenceLedger.model_validate(invalid)

    local = ledger.model_dump(mode="json")
    local.update(
        publication_status="local_release_candidate",
        public_repository_verified=False,
        public_repository_url=None,
        observed_public_stars=None,
    )
    assert ExternalEvidenceLedger.model_validate(local).publication_status == (
        "local_release_candidate"
    )
    local["public_repository_url"] = ledger.public_repository_url
    with pytest.raises(ValidationError, match="cannot declare a public repository URL"):
        ExternalEvidenceLedger.model_validate(local)
