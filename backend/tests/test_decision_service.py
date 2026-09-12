from app.services.decision_service import DecisionService


def test_high_risk_requires_verification() -> None:
    assert DecisionService().decide(0.8).decision == "verify"
