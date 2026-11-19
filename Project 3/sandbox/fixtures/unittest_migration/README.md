# unittest_migration

A small sample repo for the migration agent. Its tests are `unittest.TestCase` classes that
use `assertEquals`, an alias removed in Python 3.12, so they fail until they are migrated to
plain pytest functions with `assert`.

Expected migration: `tests/test_stats.py` only. The code in `src/` must not change.