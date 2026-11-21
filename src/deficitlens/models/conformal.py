"""Finite-sample participant-held-out conformal intervals."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_CEILING, Decimal

import numpy as np
import pandas as pd
from numpy.typing import NDArray


def conformal_quantile(scores: NDArray[np.float64], alpha: float) -> float:
    """Return the capped empirical radius used by the historical benchmark."""

    finite = np.sort(np.asarray(scores, dtype=float)[np.isfinite(scores)])
    if len(finite) == 0:
        raise ValueError("At least one finite calibration score is required")
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be between zero and one")
    rank = min(int(np.ceil((len(finite) + 1) * (1.0 - alpha))), len(finite))
    return float(finite[rank - 1])


@dataclass(frozen=True)
class MondrianConformalRegressor:
    """Global interval with group-conditional (Mondrian) refinements when supported."""

    alpha: float
    global_radius: float
    group_radii: dict[str, float]
    cluster_global_radius: float | None
    cluster_group_radii: dict[str, float]
    group_column: str
    calibration_size: int
    calibration_clusters: int

    @property
    def simultaneous_order(self) -> int:
        """Order statistic for one exchangeable new participant's maximum residual."""
        rank = Decimal(self.calibration_clusters + 1) * (1 - Decimal(str(self.alpha)))
        return int(rank.to_integral_value(rounding=ROUND_CEILING))

    @property
    def simultaneous_radius(self) -> float | None:
        """No finite distribution-free radius is supported when the order exceeds n."""
        if self.simultaneous_order > self.calibration_clusters:
            return None
        return self.cluster_global_radius

    def predict_simultaneous_interval(
        self, prediction: NDArray[np.float64]
    ) -> tuple[NDArray[np.float64], NDArray[np.float64]] | None:
        """Apply one participant-wide radius to every predicted window, if supported."""
        radius = self.simultaneous_radius
        if radius is None:
            return None
        point = np.asarray(prediction, dtype=float)
        return np.maximum(0.0, point - radius), point + radius

    @classmethod
    def fit(
        cls,
        frame: pd.DataFrame,
        target: NDArray[np.float64],
        prediction: NDArray[np.float64],
        *,
        alpha: float,
        group_column: str,
        minimum_group_samples: int,
        cluster_column: str | None = None,
        minimum_group_clusters: int = 3,
    ) -> MondrianConformalRegressor:
        """Calibrate absolute-residual intervals on participant-disjoint data."""

        if np.shape(target) != np.shape(prediction):
            raise ValueError("Targets and predictions must have the same shape")
        scores = np.abs(np.asarray(target, dtype=float) - np.asarray(prediction, dtype=float))
        if scores.ndim != 1 or len(scores) != len(frame) or not np.isfinite(scores).all():
            raise ValueError("Calibration requires one finite residual per row")
        if cluster_column is not None and frame[cluster_column].isna().any():
            raise ValueError("Participant IDs are required for every calibration window")
        global_radius = conformal_quantile(scores, alpha)
        group_radii: dict[str, float] = {}
        labels = frame[group_column].astype(str).to_numpy()
        for label in sorted(set(labels)):
            group_scores = scores[labels == label]
            if len(group_scores) >= minimum_group_samples:
                group_radii[label] = conformal_quantile(group_scores, alpha)

        cluster_global_radius: float | None = None
        cluster_group_radii: dict[str, float] = {}
        calibration_clusters = 0
        if cluster_column is not None:
            calibration = pd.DataFrame(
                {
                    "score": scores,
                    "cluster": frame[cluster_column].astype(str).to_numpy(),
                    "mondrian": labels,
                }
            )
            per_cluster_max = calibration.groupby("cluster")["score"].max()
            calibration_clusters = len(per_cluster_max)
            if calibration_clusters < 2:
                raise ValueError("Cluster conformal requires at least two calibration clusters")
            rank = Decimal(calibration_clusters + 1) * (1 - Decimal(str(alpha)))
            order = min(int(rank.to_integral_value(rounding=ROUND_CEILING)), calibration_clusters)
            cluster_global_radius = float(np.sort(per_cluster_max.to_numpy())[order - 1])
            for label, subset in calibration.groupby("mondrian"):
                cluster_scores = subset.groupby("cluster")["score"].max()
                if len(cluster_scores) >= minimum_group_clusters:
                    cluster_group_radii[str(label)] = conformal_quantile(
                        cluster_scores.to_numpy(), alpha
                    )
        return cls(
            alpha=alpha,
            global_radius=global_radius,
            group_radii=group_radii,
            cluster_global_radius=cluster_global_radius,
            cluster_group_radii=cluster_group_radii,
            group_column=group_column,
            calibration_size=len(scores),
            calibration_clusters=calibration_clusters,
        )

    def predict_interval(
        self,
        frame: pd.DataFrame,
        prediction: NDArray[np.float64],
        *,
        cluster_robust: bool = False,
    ) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
        """Return lower/upper bounds plus the radius used for each row."""

        point = np.asarray(prediction, dtype=float)
        labels = frame[self.group_column].astype(str).to_numpy()
        if cluster_robust:
            if self.cluster_global_radius is None:
                raise ValueError("No cluster calibration was fitted")
            radii = np.asarray(
                [
                    self.cluster_group_radii.get(label, self.cluster_global_radius)
                    for label in labels
                ],
                dtype=float,
            )
        else:
            radii = np.asarray(
                [self.group_radii.get(label, self.global_radius) for label in labels], dtype=float
            )
        return np.maximum(point - radii, 0.0), point + radii, radii
