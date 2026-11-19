# billing_service

A small sample repo for the migration agent. Its code uses `datetime.utcnow()`, which is
deprecated since Python 3.12. The test suite is run with `-W error`, so the deprecated call
makes the tests fail until it is migrated to `datetime.now(timezone.utc)`.

Expected migration: `src/billing/invoice.py` only. Tests must not be edited.