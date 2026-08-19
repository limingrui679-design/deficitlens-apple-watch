"""Optional Bayesian streaming personalization after criterion calibration sessions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class KalmanBiasCalibrator:
    """One-dimensional state-space correction for slowly drifting device bias.

    A criterion measurement is required for every update. In ordinary use, ``predict`` can be
    called indefinitely without pretending that scale weight or Apple Watch output is ground
    truth. The state variance widens between calibrations through process noise.
    """

    process_variance: float = 0.01
    observation_variance: float = 0.25
    bias: float = 0.0
    variance: float = 1.0

    def __post_init__(self) -> None:
        if self.process_variance < 0 or self.observation_variance <= 0 or self.variance <= 0:
            raise ValueError("Kalman variances must be positive (process may be zero)")

    def predict(self, apple_estimate: float) -> tuple[float, float]:
        """Correct Apple energy and return the current bias standard deviation."""

        self.variance += self.process_variance
        return max(float(apple_estimate) - self.bias, 0.0), self.variance**0.5

    def update(self, *, apple_estimate: float, criterion: float) -> float:
        """Update latent device bias from a genuine paired criterion observation."""

        observed_bias = float(apple_estimate) - float(criterion)
        prior_variance = self.variance + self.process_variance
        gain = prior_variance / (prior_variance + self.observation_variance)
        self.bias += gain * (observed_bias - self.bias)
        self.variance = (1.0 - gain) * prior_variance
        return gain
