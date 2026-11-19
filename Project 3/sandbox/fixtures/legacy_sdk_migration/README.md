# legacy_sdk_migration

A small sample repo for the migration agent. The in-house messaging SDK is at version 2,
which renamed `send_message` to `deliver` and `fetch_status` to `get_status`. The notifier
still calls the version 1 names, so its tests fail until the calls are updated.

Expected migration: `src/notifier/service.py` only. The SDK in `src/legacy_sdk/` must not change.