"""Small regularized probability models for reproducible synthetic experiments.

The abandonment coefficient is constrained nonnegative. Historical abandonment
can increase estimated friction, but cannot make predicted fraud less likely.
"""
from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit

from app.ml.simulator import FEATURE_NAMES, RISK_FEATURE_NAMES


def feature_matrix(records: list[dict], personalization: bool = True) -> np.ndarray:
    names = FEATURE_NAMES if personalization else RISK_FEATURE_NAMES
    matrix = []
    for row in records:
        values = [float(row.get(name, 0)) for name in names]
        # A late-night indicator handles the discontinuity without treating
        # 23:00 and 00:00 as far apart on a numerical hour scale.
        values.append(float(float(row.get("hour", 12)) < 6))
        matrix.append(values)
    array = np.asarray(matrix, dtype=float)
    if array.size and not np.isfinite(array).all():
        raise ValueError("Model features must be finite")
    return array


@dataclass
class RegularizedProbabilityModel:
    monotone_index: int | None = None
    regularization: float = 0.001

    def fit(self, x, y):
        x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
        if not len(y) or not np.isfinite(x).all() or not np.isin(y, [0, 1]).all():
            raise ValueError("Binary observations and finite features are required")
        self.classes_ = np.array([False, True])
        self.mean_ = x.mean(axis=0)
        self.scale_ = np.maximum(x.std(axis=0), 1e-6)
        values = np.column_stack([np.ones(len(x)), (x - self.mean_) / self.scale_])
        # Handles a single observed class without pretending absolute certainty.
        prevalence = (y.sum() + 0.5) / (len(y) + 1)
        initial = np.zeros(values.shape[1])
        initial[0] = np.log(prevalence / (1 - prevalence))
        if np.all(y == y[0]):
            self.coefficients_ = initial
            return self

        def loss(beta):
            logits = values @ beta
            penalty = self.regularization * np.dot(beta[1:], beta[1:]) / 2
            objective = np.mean(np.logaddexp(0, logits) - y * logits) + penalty
            gradient = values.T @ (expit(logits) - y) / len(y)
            gradient[1:] += self.regularization * beta[1:]
            return objective, gradient

        bounds = [(None, None)] * values.shape[1]
        if self.monotone_index is not None:
            bounds[self.monotone_index + 1] = (0, None)
        fitted = minimize(loss, initial, jac=True, method="L-BFGS-B", bounds=bounds,
                          options={"maxiter": 500, "ftol": 1e-10})
        if not fitted.success:
            raise RuntimeError("Probability model did not converge")
        self.coefficients_ = fitted.x
        return self

    def predict_proba(self, x):
        x = np.asarray(x, dtype=float)
        if not np.isfinite(x).all():
            raise ValueError("Model features must be finite")
        logits = ((x - self.mean_) / self.scale_) @ self.coefficients_[1:] + self.coefficients_[0]
        p = expit(logits)
        return np.column_stack([1 - p, p])


def fit_fraud_model(records: list[dict]) -> RegularizedProbabilityModel:
    return RegularizedProbabilityModel().fit(
        feature_matrix(records, personalization=False), [row["fraud"] for row in records],
    )
