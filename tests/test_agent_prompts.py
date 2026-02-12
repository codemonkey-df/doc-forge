"""Unit tests for agent prompts (Story 2.3). GIVEN-WHEN-THEN.

Assert system prompt contains required instructions (fidelity, structure, context,
interrupt) and user prompt template includes current_file, current_chapter,
and validation_issues when present.
"""

from __future__ import annotations

import pytest

# Required keywords in system prompt per ARCHITECTURE §4.3 (AC2.3.1, AC2.3.2)
SYSTEM_PROMPT_REQUIRED_KEYWORDS = [
    "verbatim",
    "fidelity",
    "structure",
    "heading",
    "read",
    "interrupt",
    "missing",
    "ask",
]


@pytest.fixture
def minimal_state() -> dict:
    """GIVEN minimal DocumentState-like dict for build_user_prompt."""
    return {
        "session_id": "sid-123",
        "input_files": ["a.txt", "b.md"],
        "current_file_index": 0,
        "current_chapter": 1,
        "validation_issues": [],
    }


@pytest.fixture
def state_with_validation_issues(minimal_state: dict) -> dict:
    """GIVEN state with validation_issues set (returning from validate_md)."""
    return {
        **minimal_state,
        "validation_issues": [
            {
                "lineNumber": 5,
                "ruleDescription": "Fenced code blocks",
                "errorDetail": "Expected blank line",
            },
        ],
    }


def test_system_prompt_contains_fidelity_instructions() -> None:
    """GIVEN prompts module / WHEN SYSTEM_PROMPT / THEN it contains fidelity and verbatim."""
    from backend.prompts import SYSTEM_PROMPT

    prompt_lower = SYSTEM_PROMPT.lower()
    assert "verbatim" in prompt_lower or "fidelity" in prompt_lower
    assert "code" in prompt_lower or "log" in prompt_lower


def test_system_prompt_contains_structure_instructions() -> None:
    """GIVEN prompts module / WHEN SYSTEM_PROMPT / THEN it contains structure and heading hierarchy."""
    from backend.prompts import SYSTEM_PROMPT

    prompt_lower = SYSTEM_PROMPT.lower()
    assert "structure" in prompt_lower or "heading" in prompt_lower
    assert "#" in SYSTEM_PROMPT or "h1" in prompt_lower or "h2" in prompt_lower


def test_system_prompt_contains_context_instructions() -> None:
    """GIVEN prompts module / WHEN SYSTEM_PROMPT / THEN it says to read current document before adding."""
    from backend.prompts import SYSTEM_PROMPT

    prompt_lower = SYSTEM_PROMPT.lower()
    assert "read" in prompt_lower
    assert (
        "before" in prompt_lower
        or "temp" in prompt_lower
        or "generated" in prompt_lower
    )


def test_system_prompt_contains_interrupt_instructions() -> None:
    """GIVEN prompts module / WHEN SYSTEM_PROMPT / THEN it contains interrupt / ask user for missing file."""
    from backend.prompts import SYSTEM_PROMPT

    prompt_lower = SYSTEM_PROMPT.lower()
    assert "interrupt" in prompt_lower or "ask" in prompt_lower
    assert "missing" in prompt_lower or "external" in prompt_lower


def test_build_user_prompt_includes_current_file_and_chapter(
    minimal_state: dict,
) -> None:
    """GIVEN state with input_files and current_chapter / WHEN build_user_prompt / THEN output contains file and chapter."""
    from backend.prompts import build_user_prompt

    prompt = build_user_prompt(minimal_state)
    assert "a.txt" in prompt
    assert "1" in prompt or "chapter" in prompt.lower()


def test_build_user_prompt_includes_validation_issues_when_present(
    state_with_validation_issues: dict,
) -> None:
    """GIVEN state with validation_issues / WHEN build_user_prompt / THEN output contains validation or issues."""
    from backend.prompts import build_user_prompt

    prompt = build_user_prompt(state_with_validation_issues)
    assert "validation" in prompt.lower() or "issue" in prompt.lower()
    assert "5" in prompt or "Fenced" in prompt or "blank line" in prompt


def test_build_user_prompt_does_not_require_validation_issues(
    minimal_state: dict,
) -> None:
    """GIVEN state without validation_issues key / WHEN build_user_prompt / THEN no error and prompt returned."""
    from backend.prompts import build_user_prompt

    del minimal_state["validation_issues"]
    prompt = build_user_prompt(minimal_state)
    assert isinstance(prompt, str)
    assert len(prompt) > 0
