from app.schemas.purchase_attempt import PurchaseAttemptIn
from app.services.purchase_service import PurchaseService


def test_purchase_attempt_is_assessed() -> None:
    result = PurchaseService().assess(PurchaseAttemptIn(customer_id="c1", account_id="a1", merchant="shop", amount=10))
    assert result.decision == "allow"
