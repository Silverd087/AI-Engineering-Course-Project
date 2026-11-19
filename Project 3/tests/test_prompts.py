from agent.prompts import SYSTEM_PROMPT, UNTRUSTED_CLOSE, UNTRUSTED_OPEN


def test_prompt_names_the_untrusted_tags():
    assert UNTRUSTED_OPEN in SYSTEM_PROMPT
    assert UNTRUSTED_CLOSE in SYSTEM_PROMPT


def test_prompt_says_tagged_text_is_data_not_instructions():
    assert "never an instruction" in SYSTEM_PROMPT


def test_prompt_explains_both_ways_to_finish():
    assert '"success"' in SYSTEM_PROMPT
    assert '"gave_up"' in SYSTEM_PROMPT


def test_prompt_forbids_editing_tests():
    assert "Never edit test files" in SYSTEM_PROMPT