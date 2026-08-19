"""Shared schemas and feature contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

APPLE_ONLY_NUMERIC_FEATURES = [
    "apple_active_kcal_min",
    "apple_energy_observed_fraction",
    "apple_hr_mean",
    "apple_hr_sd",
    "apple_hr_range",
    "apple_hr_slope",
    "apple_hr_mean_fraction_hrmax",
    "apple_hr_missing_fraction",
    "weight_kg",
    "height_cm",
    "age_years",
    "bmi",
    "body_fat_pct",
    "mifflin_rmr_kcal_day",
]

CONTEXT_NUMERIC_FEATURES = [
    *APPLE_ONLY_NUMERIC_FEATURES,
    "protocol_met",
    "protocol_speed",
    "window_elapsed_seconds",
]

CATEGORICAL_FEATURES = ["sex", "activity_family"]
TARGET_COLUMN = "ground_truth_active_kcal_min"
GROUP_COLUMN = "participant_id"


@dataclass(frozen=True)
class FoldMetrics:
    """Metrics from one held-out participant fold."""

    model: str
    held_out_group: str
    n: int
    mae: float
    rmse: float
    mean_bias: float
    mape: float
    interval_coverage: float | None = None
    interval_width: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""

        return asdict(self)


@dataclass(frozen=True)
class DatasetEvidence:
    """Traceable evidence about one prepared dataset."""

    dataset_id: str
    rows: int
    participants: int
    activities: tuple[str, ...]
    checksum: str | None
    source_path: str
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""

        result = asdict(self)
        result["activities"] = list(self.activities)
        result["notes"] = list(self.notes)
        return result
