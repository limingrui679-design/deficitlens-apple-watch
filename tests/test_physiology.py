from __future__ import annotations

import math

import pytest

from deficitlens.physiology import (
    apple_energy_to_kcal,
    mifflin_st_jeor_rmr_kcal_day,
    normalize_sex,
    tanaka_hr_max,
    total_to_active_kcal_min,
    vo2_to_total_kcal_min,
)


def test_physiology_happy_paths() -> None:
    assert normalize_sex(" F ") == "female"
    assert normalize_sex("man") == "male"
    assert mifflin_st_jeor_rmr_kcal_day(
        weight_kg=70, height_cm=175, age_years=30, sex="male"
    ) == pytest.approx(1648.75)
    assert vo2_to_total_kcal_min(20, 70) == pytest.approx(7.0)
    assert total_to_active_kcal_min(1.0, 1440) == 0.0
    assert apple_energy_to_kcal(4.184, "kJ") == pytest.approx(1.0)
    assert apple_energy_to_kcal(4184, "J") == pytest.approx(1.0)
    assert tanaka_hr_max(40) == 180.0
    assert math.isnan(vo2_to_total_kcal_min(math.nan, 70))


@pytest.mark.parametrize(
    ("function", "arguments"),
    [
        (normalize_sex, ("unknown",)),
        (apple_energy_to_kcal, (1.0, "BTU")),
        (tanaka_hr_max, (0.0,)),
    ],
)
def test_physiology_rejects_ambiguous_or_invalid_values(function: object, arguments: tuple) -> None:
    with pytest.raises(ValueError):
        function(*arguments)  # type: ignore[operator]


def test_vo2_rejects_invalid_values() -> None:
    with pytest.raises(ValueError):
        vo2_to_total_kcal_min(-1, 70)
    with pytest.raises(ValueError):
        vo2_to_total_kcal_min(20, 0)
    with pytest.raises(ValueError):
        vo2_to_total_kcal_min(20, 70, caloric_equivalent=6)
