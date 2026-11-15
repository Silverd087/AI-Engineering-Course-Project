"""Agent tools. Each tool is a LangChain StructuredTool built from a function
with a StrictArgs schema, and carries metadata={"is_write": bool}.

Read:  list_files, read_file, search_code
Exec:  run_tests
Write: edit_file, open_pull_request   (go through the human checkpoint)
Done:  finish
"""
