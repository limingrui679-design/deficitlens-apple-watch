"""Validated external-review, publication, adoption, and impact evidence ledger."""

from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ExternalEvidenceLedger(BaseModel):
    """Claims that require actors or infrastructure outside the maintainer's local checks."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[2]
    as_of: str
    publication_status: Literal["local_release_candidate", "published"]
    public_repository_verified: bool
    public_repository_url: str | None = None
    independent_method_reviews: int = Field(ge=0)
    independent_reproductions: int = Field(ge=0)
    structured_usability_participants: int = Field(ge=0)
    structured_accessibility_reviews: int = Field(ge=0)
    production_deployments: int = Field(ge=0)
    organizational_adoptions: int = Field(ge=0)
    documented_real_users: int = Field(ge=0)
    real_world_impact_evaluations: int = Field(ge=0)
    observed_public_stars: int | None = Field(default=None, ge=0)
    boundary: str

    @model_validator(mode="after")
    def validate_publication_state(self) -> ExternalEvidenceLedger:
        if self.publication_status == "local_release_candidate":
            if self.public_repository_verified:
                raise ValueError("local release candidate cannot verify a public repository")
            if self.observed_public_stars is not None:
                raise ValueError("public stars are unobserved before repository publication")
            if self.public_repository_url is not None:
                raise ValueError("local release candidate cannot declare a public repository URL")
        else:
            if not self.public_repository_verified:
                raise ValueError("published ledger requires a verified public repository")
            if not self.public_repository_url or not self.public_repository_url.startswith(
                "https://github.com/"
            ):
                raise ValueError("published ledger requires a canonical GitHub repository URL")
            if self.observed_public_stars is None:
                raise ValueError("published ledger requires an observed public Star count")
        return self


def bundled_external_evidence_path() -> Path:
    """Return the external-evidence ledger included in an installed wheel."""

    return Path(str(files("deficitlens.resources").joinpath("external_evidence.json")))


def load_external_evidence(path: str | Path | None = None) -> ExternalEvidenceLedger:
    """Load the explicit ledger without inferring external evidence from internal checks."""

    source = Path(path) if path is not None else bundled_external_evidence_path()
    return ExternalEvidenceLedger.model_validate(json.loads(source.read_text(encoding="utf-8")))
