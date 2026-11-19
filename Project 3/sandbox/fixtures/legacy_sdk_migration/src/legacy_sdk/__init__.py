"""In-house messaging SDK, version 2. Version 1 functions were renamed or removed."""

SDK_VERSION = "2.0"


def deliver(recipient, text):
    return {"status": "queued", "recipient": recipient, "text": text}


def get_status(message_id):
    return "delivered" if message_id.startswith("ok-") else "pending"