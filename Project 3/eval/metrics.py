"""Trajectory metrics (task C4).

TODO, computed from traces + scenarios:
- step accuracy, tool-call precision, wasted steps per task
- task success rate (a forbidden step = failure even if tests pass)
- recovery-after-failure rate (scenarios with faults that still succeed)
- injection results, stop rule never exceeded
- steps / tokens / cost per task, p50 / p95 time, cost at 100x
"""
