"""Invoice creation for the billing service."""

from dataclasses import dataclass
from datetime import datetime, timedelta

PAYMENT_TERM_DAYS = 30


@dataclass(frozen=True)
class Invoice:
    customer_id: str
    amount_cents: int
    created: datetime
    due: datetime


def create_invoice(customer_id: str, amount_cents: int) -> Invoice:
    if amount_cents <= 0:
        raise ValueError("amount_cents must be positive")
    created = datetime.utcnow()
    due = created + timedelta(days=PAYMENT_TERM_DAYS)
    return Invoice(customer_id=customer_id, amount_cents=amount_cents, created=created, due=due)