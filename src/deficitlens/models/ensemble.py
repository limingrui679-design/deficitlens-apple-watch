"""Participant-grouped, cross-fitted stacking for Apple Watch calibration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from scipy.optimize import minimize
from sklearn.base import RegressorMixin
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


def _preprocessor(
    numeric_features: list[str], categorical_features: list[str], *, scale: bool
) -> ColumnTransformer:
    numeric_steps: list[tuple[str, Any]] = [("impute", SimpleImputer(strategy="median"))]
    if scale:
        numeric_steps.append(("scale", StandardScaler()))
    numeric = Pipeline(numeric_steps)
    categorical = Pipeline(
        [
            ("impute", SimpleImputer(strategy="most_frequent")),
            ("one_hot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )
    return ColumnTransformer(
        [
            ("numeric", numeric, numeric_features),
            ("categorical", categorical, categorical_features),
        ],
        remainder="drop",
        sparse_threshold=0.0,
    )


def _estimator(
    name: str,
    numeric_features: list[str],
    categorical_features: list[str],
    seed: int,
) -> Pipeline:
    if name == "ridge":
        regressor: RegressorMixin = Ridge(alpha=4.0)
        scale = True
    elif name == "extra_trees":
        regressor = ExtraTreesRegressor(
            n_estimators=96,
            min_samples_leaf=4,
            max_features=0.8,
            n_jobs=1,
            random_state=seed,
        )
        scale = False
    elif name == "histogram_gradient_boosting":
        regressor = HistGradientBoostingRegressor(
            learning_rate=0.05,
            max_iter=100,
            max_leaf_nodes=15,
            l2_regularization=1.0,
            random_state=seed,
        )
        scale = False
    else:
        raise ValueError(f"Unsupported ensemble model: {name}")
    return Pipeline(
        [
            ("prepare", _preprocessor(numeric_features, categorical_features, scale=scale)),
            ("regressor", regressor),
        ]
    )


def _simplex_weights(
    predictions: NDArray[np.float64], target: NDArray[np.float64]
) -> NDArray[np.float64]:
    """Find non-negative stacking weights that sum to one."""

    n_models = predictions.shape[1]
    initial = np.full(n_models, 1.0 / n_models)

    def objective(weights: NDArray[np.float64]) -> float:
        residual = predictions @ weights - target
        return float(np.mean(np.square(residual)))

    result = minimize(
        objective,
        initial,
        method="SLSQP",
        bounds=[(0.0, 1.0)] * n_models,
        constraints={"type": "eq", "fun": lambda values: float(values.sum() - 1.0)},
        options={"maxiter": 500, "ftol": 1e-12},
    )
    if not result.success:
        return cast(NDArray[np.float64], initial)
    weights = np.maximum(np.asarray(result.x, dtype=float), 0.0)
    return cast(NDArray[np.float64], weights / weights.sum())


@dataclass
class GroupStackedRegressor:
    """Cross-fitted convex stack whose inner folds never split a participant.

    The stack uses out-of-fold predictions to learn its convex combination. Final base models
    are then refit on all development participants. This avoids the optimistic in-sample
    stacking common in small wearable datasets.
    """

    model_names: list[str]
    numeric_features: list[str]
    categorical_features: list[str]
    inner_group_folds: int = 5
    seed: int = 20260820

    def __post_init__(self) -> None:
        if len(self.model_names) < 2:
            raise ValueError("Stacking requires at least two base models")
        self.models_: dict[str, Pipeline] = {}
        self.weights_: NDArray[np.float64] | None = None
        self.oof_rmse_: float | None = None

    @property
    def features(self) -> list[str]:
        """Return the ordered feature contract."""

        return [*self.numeric_features, *self.categorical_features]

    def fit(
        self, frame: pd.DataFrame, target: NDArray[np.float64], groups: NDArray[Any]
    ) -> GroupStackedRegressor:
        """Fit group-cross-fitted weights and final base estimators."""

        unique_groups = np.unique(groups)
        n_splits = min(self.inner_group_folds, len(unique_groups))
        if n_splits < 2:
            raise ValueError("At least two participant groups are required")
        y = np.asarray(target, dtype=float)
        oof = np.full((len(frame), len(self.model_names)), np.nan, dtype=float)
        splitter = GroupKFold(n_splits=n_splits)
        features = frame[self.features]

        for fold_index, (train_index, validation_index) in enumerate(
            splitter.split(features, y, groups)
        ):
            for model_index, name in enumerate(self.model_names):
                model = _estimator(
                    name,
                    self.numeric_features,
                    self.categorical_features,
                    self.seed + fold_index * 101 + model_index,
                )
                model.fit(features.iloc[train_index], y[train_index])
                oof[validation_index, model_index] = model.predict(features.iloc[validation_index])

        if np.isnan(oof).any():
            raise RuntimeError("Cross-fitting did not produce every out-of-fold prediction")
        self.weights_ = _simplex_weights(oof, y)
        self.oof_rmse_ = float(np.sqrt(np.mean(np.square(oof @ self.weights_ - y))))
        self.models_ = {}
        for model_index, name in enumerate(self.model_names):
            model = _estimator(
                name,
                self.numeric_features,
                self.categorical_features,
                self.seed + 10_000 + model_index,
            )
            model.fit(features, y)
            self.models_[name] = model
        return self

    def predict_components(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Return one prediction column per fitted base estimator."""

        if not self.models_:
            raise RuntimeError("Model is not fitted")
        features = frame[self.features]
        return pd.DataFrame(
            {name: model.predict(features) for name, model in self.models_.items()},
            index=frame.index,
        )

    def predict(self, frame: pd.DataFrame) -> NDArray[np.float64]:
        """Return the non-negative convex-stack prediction."""

        if self.weights_ is None:
            raise RuntimeError("Model is not fitted")
        components = self.predict_components(frame)[self.model_names].to_numpy(dtype=float)
        return cast(NDArray[np.float64], np.maximum(components @ self.weights_, 0.0))

    def diagnostics(self) -> dict[str, object]:
        """Return serializable stacking diagnostics."""

        if self.weights_ is None:
            raise RuntimeError("Model is not fitted")
        return {
            "weights": {
                name: float(weight)
                for name, weight in zip(self.model_names, self.weights_, strict=True)
            },
            "oof_rmse": self.oof_rmse_,
            "inner_group_folds": self.inner_group_folds,
        }
