import legacy_sdk
from notifier.service import check_notification, notify_customer


def test_sdk_is_version_two():
    assert legacy_sdk.SDK_VERSION == "2.0"


def test_notify_customer_returns_queued():
    assert notify_customer("alice", "hi") == "queued"


def test_check_notification_reports_delivered():
    assert check_notification("ok-123") == "delivered"


def test_check_notification_reports_pending():
    assert check_notification("new-1") == "pending"