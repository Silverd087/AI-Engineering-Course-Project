from datetime import timedelta

import pytest

from billing.invoice import PAYMENT_TERM_DAYS, create_invoice


def test_invoice_records_customer_and_amount():
    invoice = create_invoice("cust-1", 1500)
    assert invoice.customer_id == "cust-1"
    assert invoice.amount_cents == 1500


def test_created_time_is_timezone_aware():
    invoice = create_invoice("cust-1", 1500)
    assert invoice.created.tzinfo is not None
    assert invoice.created.utcoffset() == timedelta(0)


def test_due_date_is_payment_term_after_creation():
    invoice = create_invoice("cust-1", 1500)
    assert invoice.due - invoice.created == timedelta(days=PAYMENT_TERM_DAYS)


def test_non_positive_amount_is_rejected():
    with pytest.raises(ValueError):
        create_invoice("cust-1", 0)