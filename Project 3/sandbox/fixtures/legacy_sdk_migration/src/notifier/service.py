"""Sends customer notifications through the messaging SDK."""

import legacy_sdk


def notify_customer(recipient, text):
    result = legacy_sdk.send_message(recipient, text)
    return result["status"]


def check_notification(message_id):
    return legacy_sdk.fetch_status(message_id)