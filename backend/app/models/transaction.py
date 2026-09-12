from typing import TypedDict


class TransactionDocument(TypedDict, total=False):
    customer_id: str
    account_id: str
    merchant: str
    amount: float
