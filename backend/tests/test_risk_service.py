from app.services.risk_service import RiskService


def test_risk_score_is_bounded() -> None:
    assert 0 <= RiskService().score({"amount": 100}) <= 1
