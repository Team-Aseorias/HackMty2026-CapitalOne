"""Train the regularized probability model used by RiskService."""

from app.services.risk_service import _risk_model


def train_risk_model():
    """Return a fitted artifact; callers may serialize it with joblib."""
    model = _risk_model()
    if model is None:
        raise RuntimeError("Install scikit-learn to train the calibrated risk model")
    return model
