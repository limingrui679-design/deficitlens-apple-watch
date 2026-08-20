"""Machine-readable, school-neutral case and capability catalog."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class CaseStudy(BaseModel):
    """One evidence-bounded public case path."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    title: str
    evidence_state: Literal[
        "observed_benchmark",
        "observed_external_audit",
        "private_local_workflow",
        "modeled_scenario",
    ]
    decision_status: str
    decision_question: str
    user_task: str
    datasets: list[str]
    methods: list[str]
    capabilities: list[str]
    outputs: list[str]
    claim_boundary: str


class CaseCatalog(BaseModel):
    """Validated catalog shared by the CLI, documentation, and tests."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1]
    capabilities: dict[str, str]
    cases: list[CaseStudy]

    @model_validator(mode="after")
    def validate_references(self) -> CaseCatalog:
        ids = [case.id for case in self.cases]
        if len(ids) != len(set(ids)):
            raise ValueError("case ids must be unique")
        known = set(self.capabilities)
        missing = sorted({item for case in self.cases for item in case.capabilities} - known)
        if missing:
            raise ValueError(f"cases reference unknown capabilities: {missing}")
        if len(self.cases) < 4:
            raise ValueError("catalog requires at least four complementary case paths")
        return self


def bundled_case_catalog_path() -> Path:
    """Return the catalog path included in an installed wheel."""

    return Path(str(files("deficitlens.resources").joinpath("case_catalog.yml")))


def load_case_catalog(path: str | Path | None = None) -> CaseCatalog:
    """Load and validate the public case catalog."""

    source = Path(path) if path is not None else bundled_case_catalog_path()
    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    return CaseCatalog.model_validate(payload)
