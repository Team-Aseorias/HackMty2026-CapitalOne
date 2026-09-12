from app.schemas.decision import DecisionOut


class DecisionService:
    def decide(
        self,
        risk_score: float,
        uplift: float = 0.0,
        expected_costs: tuple[float, float] | None = None,
        completion_probabilities: tuple[float, float] | None = None,
    ) -> DecisionOut:
        """Choose the action with lower estimated net cost.

        ``expected_costs`` is intentionally required for the causal policy.
        The risk-only branch remains for compatibility and acts as the
        predictive baseline, not the production causal decision.
        """
        if expected_costs is None:
            verify = risk_score + uplift >= 0.5
            allow_cost = verify_cost = None
        else:
            allow_cost, verify_cost = expected_costs
            verify = verify_cost < allow_cost
        if verify:
            reason = "verify: estimated incremental benefit exceeds friction cost"
        else:
            reason = "allow: verification's estimated benefit does not cover friction"
        return DecisionOut(
            decision="verify" if verify else "allow",
            risk_score=risk_score,
            reason=reason,
            estimated_cost_allow=allow_cost,
            estimated_cost_verify=verify_cost,
            uplift=uplift if expected_costs is not None else None,
            allow_completion_probability=(completion_probabilities or (None, None))[0],
            verify_completion_probability=(completion_probabilities or (None, None))[1],
            incremental_abandonment_probability=(
                max(0.0, completion_probabilities[0] - completion_probabilities[1])
                if completion_probabilities else None
            ),
        )
