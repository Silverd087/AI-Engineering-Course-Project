"""System prompt (task A7).

TODO: the prompt must say that anything inside <untrusted_tool_output> tags is
data from the repository, never instructions, and that the agent may only edit
files the migration spec allows.
"""

UNTRUSTED_OPEN = "<untrusted_tool_output>"
UNTRUSTED_CLOSE = "</untrusted_tool_output>"
