"""Paired model comparisons under reweighting of observed participants."""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray


def _downward_shift(gains: NDArray[np.float64], budget: float) -> tuple[float, float | None]:
    """Minimize mean gain in a TV ball and find first attainable break-even along that path."""
    minimum = float(np.min(gains))
    balanced = float(np.mean(gains))
    adverse = balanced
    mass_moved = 0.0
    tie: float | None = 0.0 if balanced == 0 else None
    # Moving one unit of probability from the highest gain to the lowest is optimal.
    for donor in np.sort(gains)[::-1]:
        spread = float(donor - minimum)
        if spread == 0:
            break
        donor_mass = 1.0 / len(gains)
        if balanced > 0 and tie is None and balanced <= donor_mass * spread:
            tie = mass_moved + balanced / spread
        balanced -= donor_mass * spread
        adverse -= max(0.0, min(donor_mass, budget - mass_moved)) * spread
        mass_moved += donor_mass
    # A zero minimum reaches equality when all positive-gain mass has moved.
    if minimum == 0 and tie is None and np.any(gains > 0):
        tie = float(np.mean(gains > 0))
    return adverse, tie


def participant_mix_sensitivity(
    truth: ArrayLike,
    prediction: ArrayLike,
    reference: ArrayLike,
    participants: ArrayLike,
    *,
    budget: float = 0.25,
) -> dict[str, float | int | None]:
    """Sharp gain range among mixtures within total variation `budget` of equal-person weights."""
    y, p, ref = (np.asarray(x, dtype=float) for x in (truth, prediction, reference))
    ids = np.asarray(participants)
    if y.ndim != 1 or not len(y) or any(x.shape != y.shape for x in (p, ref, ids)):
        raise ValueError("Expected nonempty paired observation vectors")
    if not all(np.isfinite(x).all() for x in (y, p, ref)) or not 0 <= budget <= 1:
        raise ValueError("Require finite paired outcomes and a TV budget in [0, 1]")
    if any(not isinstance(x, (str, np.str_)) or not x.strip() for x in ids):
        raise ValueError("Require a participant identifier for every observation")
    _, index = np.unique(ids, return_inverse=True)
    paired = np.abs(ref - y) - np.abs(p - y)
    gains = np.bincount(index, weights=paired) / np.bincount(index)
    lower, down_tie = _downward_shift(gains, budget)
    neg_upper, up_tie = _downward_shift(-gains, budget)
    return {
        "paired_participants": len(gains),
        "equal_person_gain_vs_raw": float(np.mean(gains)),
        "mix_tv_budget": budget,
        "worst_mix_gain_vs_raw": lower,
        "best_mix_gain_vs_raw": -neg_upper,
        "minimum_tv_to_tie_raw": down_tie if np.mean(gains) >= 0 else up_tie,
    }
