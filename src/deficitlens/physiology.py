"""Transparent physiology calculations used by the benchmark.

These functions expose assumptions instead of presenting proprietary wearable values as truth.
They are analytical utilities, not medical advice.
"""

from __future__ import annotations

import math

KJ_PER_KCAL = 4.184
SECONDS_PER_DAY = 86_400
MINUTES_PER_DAY = 1_440


def normalize_sex(value: str) -> str:
    """Map common labels to the two categories required by Mifflin-St Jeor.

    The source equation uses sex-specific constants. Unknown or unsupported values must be
    handled explicitly by the caller rather than silently guessed.
    """

    normalized = value.strip().lower()
    if normalized in {"m", "male", "man"}:
        return "male"
    if normalized in {"f", "female", "woman"}:
        return "female"
    raise ValueError(f"Unsupported sex value for Mifflin-St Jeor: {value!r}")


def mifflin_st_jeor_rmr_kcal_day(
    *, weight_kg: float, height_cm: float, age_years: float, sex: str
) -> float:
    """Estimate resting metabolic rate in kcal/day using Mifflin-St Jeor."""

    if weight_kg <= 0 or height_cm <= 0 or age_years <= 0:
        raise ValueError("weight_kg, height_cm, and age_years must be positive")
    constant = 5.0 if normalize_sex(sex) == "male" else -161.0
    return 10.0 * weight_kg + 6.25 * height_cm - 5.0 * age_years + constant


def vo2_to_total_kcal_min(
    vo2_ml_kg_min: float, weight_kg: float, *, caloric_equivalent: float = 5.0
) -> float:
    """Convert mass-normalized oxygen uptake to approximate total kcal/min.

    Without VCO2, a fixed 5 kcal/L oxygen equivalent is a documented approximation. Values
    outside the plausible WEEE range are rejected to prevent unit mistakes.
    """

    if not math.isfinite(vo2_ml_kg_min) or not math.isfinite(weight_kg):
        return math.nan
    if vo2_ml_kg_min < 0 or weight_kg <= 0:
        raise ValueError("VO2 must be non-negative and weight must be positive")
    if not 4.5 <= caloric_equivalent <= 5.1:
        raise ValueError("caloric_equivalent must be between 4.5 and 5.1 kcal/L")
    vo2_l_min = vo2_ml_kg_min * weight_kg / 1000.0
    return vo2_l_min * caloric_equivalent


def total_to_active_kcal_min(total_kcal_min: float, rmr_kcal_day: float) -> float:
    """Subtract estimated resting expenditure and floor active energy at zero."""

    if not math.isfinite(total_kcal_min):
        return math.nan
    if rmr_kcal_day <= 0:
        raise ValueError("rmr_kcal_day must be positive")
    return max(total_kcal_min - rmr_kcal_day / MINUTES_PER_DAY, 0.0)


def apple_energy_to_kcal(value: float, unit: str) -> float:
    """Convert Apple Health energy quantities to kcal."""

    normalized = unit.strip().lower()
    if normalized in {"kcal", "cal"}:
        return float(value)
    if normalized in {"kj", "kilojoule", "kilojoules"}:
        return float(value) / KJ_PER_KCAL
    if normalized in {"j", "joule", "joules"}:
        return float(value) / (KJ_PER_KCAL * 1000.0)
    raise ValueError(f"Unsupported Apple energy unit: {unit!r}")


def tanaka_hr_max(age_years: float) -> float:
    """Return the Tanaka age-predicted maximum heart rate."""

    if age_years <= 0:
        raise ValueError("age_years must be positive")
    return 208.0 - 0.7 * age_years
