from app.schemas.decision import DecisionOut
from app.schemas.purchase_attempt import PurchaseAttemptIn
from app.services.causal_service import CausalService
from app.services.decision_service import DecisionService
from app.services.feature_service import FeatureService
from app.services.risk_service import RiskService


class PurchaseService:
    def assess(self, attempt: PurchaseAttemptIn) -> DecisionOut:
        return self.assess_with_context(attempt, history=[])

    def assess_with_context(
        self,
        attempt: PurchaseAttemptIn,
        history: list[dict],
        account: dict | None = None,
        decision_history: list[dict] | None = None,
    ) -> DecisionOut:
        features = FeatureService().build(attempt.model_dump(), history, account, decision_history)
        causal = CausalService()
        expected_costs = causal.expected_costs(features)
        return DecisionService().decide(
            RiskService().score(features),
            causal.uplift(features),
            expected_costs,
            causal.completion_probabilities(features),
        )
