# pathlib_migration

A small sample repo for the migration agent. Its helpers build file paths with `os.path`.
The spec asks for `pathlib.Path` instead. The tests check that the helpers return `Path`
objects, so they fail until the migration is done.

Expected migration: `src/reports/paths.py` only. Tests must not be edited.