"""Fault injection (task C2).

TODO: wrap a tool so that its Nth call returns a failure instead of running:
  down -> TOOL_UNAVAILABLE, timeout -> TIMEOUT, empty -> success with empty result,
  bad_output -> garbled result, server_error -> TOOL_UNAVAILABLE ("PR API returned 500").
Driven by Scenario.faults.
"""
