from app.schemas.decision import DecisionOut
from app.schemas.purchase_attempt import PurchaseAttemptIn
from app.services.causal_service import CausalService
from app.services.decision_service import DecisionService
from app.services.feature_service import FeatureService
from app.services.risk_service import RiskService
from app.core.config import settings
from app.schemas.decision import ActivityEvidence, SafetyCheck
from app.services.activity_service import activity_checks
from app.services.model_diagnostics import diagnostics


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
        activity: ActivityEvidence | None = None,
    ) -> DecisionOut:
        features = FeatureService().build(attempt.model_dump(), history, account, decision_history)
        causal = CausalService()
        allow, verify, allow_completion, verify_completion = causal.predict(features)
        expected_costs = (allow, verify)
        personalized = features["prior_verifications"] >= settings.min_personalization_history
        evidence, warnings = diagnostics(features)
        checks = activity_checks(activity) if activity is not None else []
        # Only the purchase-amount support gate is enforced here; other
        # feature-range excursions are disclosed without inventing confidence.
        if "outside_training_range:amount" in warnings:
            checks.append(SafetyCheck(code="amount_outside_training", observed=1,
                                      threshold=1, triggered=True))
        # The risk model receives no abandonment/treatment history: learning that
        # a user abandons must never make their fraud estimate decrease.
        decision = DecisionService().decide(
            RiskService().score(features),
            expected_costs[0] - expected_costs[1],
            expected_costs,
            (allow_completion, verify_completion),
            amount=attempt.amount,
            context_available=context_available and bool(account or features["recent_purchase_count"]),
            personalization_applied=personalized,
            additional_safety_checks=checks,
        )
        if activity is None:
            warnings.append("velocity_not_evaluated")
        return decision.model_copy(update={
            "personalization_evidence": evidence,
            "recent_activity": activity,
            "model_warnings": warnings,
        })
