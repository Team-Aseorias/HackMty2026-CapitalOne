from app.ml.simulator import generate_synthetic_data
from app.schemas.evaluation import PolicyEvaluation
from app.services.causal_service import CausalService
from app.services.risk_service import RiskService


class EvaluationService:
    def run(self) -> list[PolicyEvaluation]:
        """Evaluate policies on held-out oracle outcomes, never training rows."""
        test_rows = generate_synthetic_data(rows=1_000, seed=2027)
        causal = CausalService()
        risk = RiskService()
        totals = {"fixed_rule": 0.0, "predictive": 0.0, "causal": 0.0}
        verifications = {key: 0 for key in totals}
        for row in test_rows:
            features = {key: row[key] for key in row if key not in {
                "fraud", "treatment", "observed_cost", "cost_allow", "cost_verify", "completed_allow", "completed_verify"
            }}
            actions = {
                "fixed_rule": row["amount"] >= 500 and row["merchant_novelty"] > 0,
                "predictive": risk.score(features) >= 0.25,
                "causal": causal.uplift(features) > 0,
            }
            for policy, verify in actions.items():
                totals[policy] += row["cost_verify"] if verify else row["cost_allow"]
                verifications[policy] += int(verify)
        return [
            PolicyEvaluation(
                policy=policy,
                expected_cost=round(totals[policy] / len(test_rows), 2),
                verification_rate=round(verifications[policy] / len(test_rows), 3),
            )
            for policy in ("fixed_rule", "predictive", "causal")
        ]
