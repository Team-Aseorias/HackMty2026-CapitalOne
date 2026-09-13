import math

from app.core.config import settings
from app.schemas.decision import DecisionOut, SafetyCheck


class DecisionService:
    def decide(
        self,
        risk_score: float,
        uplift: float = 0.0,
        expected_costs: tuple[float, float] | None = None,
        completion_probabilities: tuple[float, float] | None = None,
        amount: float = 0.0,
        context_available: bool = True,
        personalization_applied: bool = False,
        additional_safety_checks: list[SafetyCheck] | None = None,
    ) -> DecisionOut:
        """Choose the action with lower estimated net cost.

        Missing estimates always recommend verify. This is a recommendation,
        not an authorization or an implementation of a verification challenge.
        """
        if not math.isfinite(risk_score) or not 0 <= risk_score <= 1:
            raise ValueError("Invalid risk score; recommendation unavailable")
        if not math.isfinite(amount) or amount < 0:
            raise ValueError("Amount must be finite and nonnegative")
        if completion_probabilities is not None and (
            len(completion_probabilities) != 2
            or any(not math.isfinite(p) or not 0 <= p <= 1 for p in completion_probabilities)
        ):
            raise ValueError("Invalid completion probabilities")
        if expected_costs is not None and len(expected_costs) != 2:
            raise ValueError("Two expected cost predictions are required")
        if expected_costs is not None and any(
            not math.isfinite(cost) or cost < 0 for cost in expected_costs
        ):
            raise ValueError("Invalid cost prediction; recommendation unavailable")
        expected_fraud_loss = risk_score * amount
        # A percentage alone must not turn a low-value purchase into a forced
        # challenge.  The high-risk guardrail applies only when the expected
        # unverified loss can at least pay for the fixed verification friction.
        # Larger exposures remain protected by the independent loss limit.
        risk_limit_triggered = (
            risk_score >= settings.max_soft_risk
            and expected_fraud_loss >= settings.verify_cost
        )
        checks = [
            SafetyCheck(code="risk_limit", observed=risk_score,
                        threshold=settings.max_soft_risk, triggered=risk_limit_triggered),
            SafetyCheck(code="loss_limit", observed=expected_fraud_loss,
                        threshold=settings.max_soft_expected_loss,
                        triggered=expected_fraud_loss >= settings.max_soft_expected_loss),
            SafetyCheck(code="amount_limit", observed=amount,
                        threshold=settings.max_soft_amount,
                        triggered=amount >= settings.max_soft_amount),
            SafetyCheck(code="missing_context", observed=float(not context_available),
                        threshold=1, triggered=not context_available),
        ] + (additional_safety_checks or [])
        safety_override = any(check.triggered for check in checks)
        if expected_costs is None:
            verify = True  # Missing causal estimates never authorize a softer path.
            allow_cost = verify_cost = None
        else:
            allow_cost, verify_cost = expected_costs
            verify = verify_cost < allow_cost
        verify = verify or safety_override
        if safety_override:
            reason = "verify: independent risk, loss, amount or context safety limit"
        elif expected_costs is None:
            reason = "verify: causal estimates unavailable"
        elif verify:
            reason = "verify: estimated incremental benefit exceeds friction cost"
        else:
            reason = "allow: verification's estimated benefit does not cover friction"
        return DecisionOut(
            decision="verify" if verify else "allow",
            risk_score=risk_score,
            safety_override=safety_override,
            personalization_applied=personalization_applied,
            safety_checks=checks,
            cost_preferred_action=("verify" if verify_cost < allow_cost else "allow") if expected_costs is not None else None,
            reason=reason,
            estimated_cost_allow=allow_cost,
            estimated_cost_verify=verify_cost,
            uplift=allow_cost - verify_cost if expected_costs is not None else None,
            allow_completion_probability=(completion_probabilities or (None, None))[0],
            verify_completion_probability=(completion_probabilities or (None, None))[1],
            incremental_abandonment_probability=(
                max(0.0, completion_probabilities[0] - completion_probabilities[1])
                if completion_probabilities else None
            ),
        )
