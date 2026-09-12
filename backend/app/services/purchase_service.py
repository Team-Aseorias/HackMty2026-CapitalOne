from app.schemas.decision import DecisionOut
from app.schemas.purchase_attempt import PurchaseAttemptIn
from app.services.causal_service import CausalService
from app.services.decision_service import DecisionService
from app.services.feature_service import FeatureService
from app.services.risk_service import RiskService
from app.core.config import settings


class PurchaseService:
    def assess(self, attempt: PurchaseAttemptIn) -> DecisionOut:
        return self.assess_with_context(attempt, history=[])

    def assess_with_context(
        self,
        attempt: PurchaseAttemptIn,
        history: list[dict],
        account: dict | None = None,
        decision_history: list[dict] | None = None,
        context_available: bool = True,
    ) -> DecisionOut:
        features = FeatureService().build(attempt.model_dump(), history, account, decision_history)
        causal = CausalService()
        allow, verify, allow_completion, verify_completion = causal.predict(features)
        expected_costs = (allow, verify)
        personalized = features["prior_verifications"] >= settings.min_personalization_history
        # The risk model receives no abandonment/treatment history: learning that
        # a user abandons must never make their fraud estimate decrease.
        return DecisionService().decide(
            RiskService().score(features),
            expected_costs[0] - expected_costs[1],
            expected_costs,
            (allow_completion, verify_completion),
            amount=attempt.amount,
            context_available=context_available and bool(account or features["recent_purchase_count"]),
            personalization_applied=personalized,
        )
