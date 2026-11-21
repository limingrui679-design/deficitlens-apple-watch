import numpy as np
import pytest
from scipy.optimize import linprog

from deficitlens.evaluation.mixture import participant_mix_sensitivity


def test_mix_bounds_match_independent_linear_program():
    gains = np.array([-1.5, 0.3, 1.0, 1.8, 2.1])
    n = len(gains)
    identity = np.eye(n)
    uniform = np.ones(n) / n
    # Variables q are alternative participant weights; slack variables bound |q - uniform|.
    constraints = np.vstack(
        [
            np.hstack([identity, -identity]),
            np.hstack([-identity, -identity]),
            np.r_[np.zeros(n), np.ones(n)],
        ]
    )
    for budget in (0, 0.1, 0.25, 0.6, 1):
        ids = np.array(list("abcde"))
        result = participant_mix_sensitivity(
            np.zeros(n), np.maximum(-gains, 0), np.maximum(gains, 0), ids, budget=budget
        )
        for sign, key in ((1, "worst_mix_gain_vs_raw"), (-1, "best_mix_gain_vs_raw")):
            solution = linprog(
                np.r_[sign * gains, np.zeros(n)],
                A_ub=constraints,
                b_ub=np.r_[uniform, -uniform, 2 * budget],
                A_eq=[np.r_[np.ones(n), np.zeros(n)]],
                b_eq=[1],
            )
            assert solution.success
            assert result[key] == pytest.approx(sign * solution.fun, abs=1e-10)
        t = result["minimum_tv_to_tie_raw"]
        at_tie = participant_mix_sensitivity(
            np.zeros(n), np.maximum(-gains, 0), np.maximum(gains, 0), ids, budget=t
        )
        assert at_tie["worst_mix_gain_vs_raw"] == pytest.approx(0, abs=1e-12)


def test_mixture_ties_dominance_and_duplicated_windows():
    for observed, expected in [([0, 0], 0), ([0, 2], 0.5), ([1, 2], None)]:
        out = participant_mix_sensitivity([0, 0], [0, 0], observed, ["a", "b"])
        assert out["minimum_tv_to_tie_raw"] == expected
    out = participant_mix_sensitivity([0] * 3, [1, 1, 0], [0, 0, 3], ["a", "a", "b"])
    assert out["equal_person_gain_vs_raw"] == 1
    inverse = participant_mix_sensitivity([0] * 3, [0, 0, 3], [1, 1, 0], ["a", "a", "b"])
    assert out["minimum_tv_to_tie_raw"] == inverse["minimum_tv_to_tie_raw"] == 0.25
    for bad in ([], ["a", "b", "c"], ["a", ""]):
        with pytest.raises(ValueError):
            participant_mix_sensitivity([0, 0], [0, 0], [1, 2], bad)
    with pytest.raises(ValueError):
        participant_mix_sensitivity([0], [np.nan], [0], ["a"])
