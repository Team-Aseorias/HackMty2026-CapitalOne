"""Model selection uses seed 2030, never the final audit seeds."""
import json
from time import perf_counter

from app.ml.audit_inference import probability_metrics
from app.ml.probability_models import feature_matrix, fit_fraud_model
from app.ml.simulator import RISK_FEATURE_NAMES, generate_synthetic_data
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier


def compare():
    validation = generate_synthetic_data(3000, seed=2030)
    y = [row["fraud"] for row in validation]
    train = generate_synthetic_data(2000, seed=2026)
    matrix = lambda records: [[float(row[name]) for name in RISK_FEATURE_NAMES] for row in records]
    legacy = CalibratedClassifierCV(RandomForestClassifier(
        n_estimators=100, min_samples_leaf=8, random_state=2026, n_jobs=1), method="sigmoid", cv=3)
    legacy.fit(matrix(train), [row["fraud"] for row in train])
    results = {"legacy_rf_2000": probability_metrics(y, legacy.predict_proba(matrix(validation))[:, 1])}
    for size in (2000, 12000):
        started = perf_counter()
        model = fit_fraud_model(generate_synthetic_data(size, seed=2026))
        scores = model.predict_proba(feature_matrix(validation, personalization=False))[:, 1]
        results[f"regularized_logistic_{size}"] = {
            **probability_metrics(y, scores), "train_seconds": perf_counter() - started,
        }
    return results


if __name__ == "__main__":
    print(json.dumps(compare(), indent=2))
