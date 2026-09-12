import math

from app.core.config import settings
from app.schemas.decision import DecisionOut


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
        safety_override = (
            risk_score >= settings.max_soft_risk
            or risk_score * amount >= settings.max_soft_expected_loss
            or amount >= settings.max_soft_amount
            or not context_available
        )
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
