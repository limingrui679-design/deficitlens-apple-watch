"""Validated configuration loading."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field


class DataConfig(BaseModel):
    """Data preparation settings."""

    model_config = ConfigDict(extra="forbid")

    window_seconds: int = Field(default=30, ge=5, le=300)
    stride_seconds: int = Field(default=30, ge=1, le=300)
    apple_hr_tolerance_seconds: int = Field(default=15, ge=1, le=120)
    minimum_window_coverage: float = Field(default=0.70, gt=0, le=1)
    oxygen_caloric_equivalent_kcal_per_liter: float = Field(default=5.0, ge=4.5, le=5.1)
    apple_active_energy_unit: Literal["kJ", "kcal"] = "kJ"


class ModelConfig(BaseModel):
    """Model and uncertainty settings."""

    model_config = ConfigDict(extra="forbid")

    outer_split: Literal["leave_one_subject_out"] = "leave_one_subject_out"
    inner_group_folds: int = Field(default=5, ge=2, le=10)
    calibration_group_fraction: float = Field(default=0.20, gt=0, lt=1.0)
    conformal_alpha: float = Field(default=0.10, gt=0, lt=0.5)
    mondrian_column: str = "activity_family"
    minimum_mondrian_samples: int = Field(default=25, ge=5)
    minimum_mondrian_clusters: int = Field(default=3, ge=2)
    ensemble_models: list[Literal["ridge", "extra_trees", "histogram_gradient_boosting"]]


class EvaluationConfig(BaseModel):
    """Evaluation and decision-impact settings."""

    model_config = ConfigDict(extra="forbid")

    bootstrap_repetitions: int = Field(default=1000, ge=100, le=10000)
    subgroup_columns: list[str]
    decision_horizons_weeks: list[Annotated[int, Field(ge=1, le=104)]]
    decision_active_minutes_per_day: list[Annotated[int, Field(ge=1, le=240)]] = [30, 45, 60]
    decision_active_days_per_week: list[Annotated[int, Field(ge=1, le=7)]] = [3, 5, 7]
    kcal_per_kg_scenarios: list[Annotated[int, Field(ge=6000, le=10000)]] = [7000, 7700, 9000]


class PrivacyConfig(BaseModel):
    """Local health-data privacy defaults."""

    model_config = ConfigDict(extra="forbid")

    redact_source_names: bool = True
    hash_salt_environment_variable: str = "DEFICITLENS_HASH_SALT"
    retain_raw_rows: bool = False


class Settings(BaseModel):
    """Top-level project settings."""

    model_config = ConfigDict(extra="forbid")

    seed: int = 20260820
    data: DataConfig
    model: ModelConfig
    evaluation: EvaluationConfig
    privacy: PrivacyConfig


def load_settings(path: str | Path) -> Settings:
    """Load and validate a YAML settings file."""

    config_path = Path(path)
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return Settings.model_validate(raw)
