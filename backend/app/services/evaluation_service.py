from math import sqrt
from statistics import mean, stdev

from app.ml.simulator import FEATURE_NAMES, generate_synthetic_data
from app.schemas.evaluation import PolicyEvaluation
from app.services.causal_service import _default_learner
from app.services.decision_service import DecisionService
from app.services.risk_service import RiskService
from app.core.config import settings


class EvaluationService:
    def run(self, rows: int = 1000, seed: int = 2027) -> list[PolicyEvaluation]:
        """Held-out synthetic evaluation of the static decision policy.

        Oracle losses/outcomes only score actions AFTER prediction. They never
        enter the feature matrix. Results measure this simulator, not a bank.
        Independent rows do not exercise temporal activity guardrails.
        """
        if seed == 2026:
            raise ValueError("Evaluation seed must differ from the training seed")
        if not 100 <= rows <= 10000:
            raise ValueError("Evaluation sample size must be between 100 and 10000")
        test_rows = generate_synthetic_data(rows=rows, seed=seed)
        features = [{name: row[name] for name in FEATURE_NAMES} for row in test_rows]
        scores = RiskService().scores(features)
        predictions = _default_learner().predict_many(features)
        neutral_features = [{**row, "prior_verifications": 0, "prior_verify_abandonment_rate": 1/6} for row in features]
        neutral_predictions = _default_learner().predict_many(neutral_features)
        policies = {name: [] for name in ("fixed_rule", "predictive", "causal_unconstrained", "causal_unpersonalized", "causal")}
        for row, risk, (allow, verify, ca, cv), neutral in zip(test_rows, scores, predictions, neutral_predictions):
            decision = DecisionService().decide(
                risk, allow - verify, (allow, verify), (ca, cv), amount=row["amount"],
            )
            policies["fixed_rule"].append(row["amount"] >= 500)
            policies["predictive"].append(
                (risk >= settings.max_soft_risk and risk * row["amount"] >= settings.verify_cost)
                or risk * row["amount"] >= settings.max_soft_expected_loss
                or row["amount"] >= settings.max_soft_amount
            )
            policies["causal_unconstrained"].append(verify < allow)
            policies["causal_unpersonalized"].append(DecisionService().decide(
                risk, expected_costs=neutral[:2], amount=row["amount"],
            ).decision == "verify")
            policies["causal"].append(decision.decision == "verify")
        results = []
        legitimate = sum(not row["fraud"] for row in test_rows)
        fraud_total = sum(row["fraud"] for row in test_rows)
        for name, actions in policies.items():
            costs, losses = [], []
            completions = captured = violations = 0
            for row, risk, verify in zip(test_rows, scores, actions):
                arm = "verify" if verify else "allow"
                costs.append(row[f"cost_{arm}"])
                loss = row[f"fraud_loss_{arm}"]
                losses.append(loss)
                completions += int(not row["fraud"] and row[f"completed_{arm}"])
                captured += int(row["fraud"] and loss == 0)
                violates = (
                    (risk >= settings.max_soft_risk and risk * row["amount"] >= settings.verify_cost)
                    or risk * row["amount"] >= settings.max_soft_expected_loss
                    or row["amount"] >= settings.max_soft_amount
                )
                violations += int(not verify and violates)
            results.append(PolicyEvaluation(
                policy=name, expected_cost=round(mean(costs), 4),
                verification_rate=round(sum(actions) / rows, 4),
                legitimate_completion_rate=round(completions / legitimate, 4) if legitimate else 0,
                legitimate_abandonment_rate=round(1 - completions / legitimate, 4) if legitimate else 0,
                fraud_loss_per_attempt=round(mean(losses), 4),
                fraud_capture_rate=round(captured / fraud_total, 4) if fraud_total else 0,
                safety_violations=violations,
                cost_standard_error=round(stdev(costs) / sqrt(rows), 4),
                seed=seed, sample_size=rows,
            ))
        return results
