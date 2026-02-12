"""Integration tests for agent node (Story 2.3). GIVEN-WHEN-THEN.

Run agent_node with mock LLM; verify state shape, messages appended,
generation_complete and pending_question set from response.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from backend.agent import agent_node
from backend.state import build_initial_state


@pytest.fixture
def base_state() -> dict:
    """GIVEN initial state with messages=[] and session/input_files."""
    return {
        **build_initial_state("session-abc", ["source.txt"]),
        "messages": [],
    }


def test_agent_node_returns_state_with_messages_appended(base_state: dict) -> None:
    """GIVEN state with empty messages / WHEN agent_node with mock LLM returning AIMessage / THEN messages length +2 (Human + AI)."""
    ai_content = "I will call read_file first."
    mock_ai = AIMessage(content=ai_content, tool_calls=[])

    with patch("backend.agent.get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value.invoke.return_value = mock_ai
        mock_get_llm.return_value = mock_llm

        result = agent_node(base_state)

    assert "messages" in result
    new_msgs = result["messages"]
    assert isinstance(new_msgs, list)
    assert len(new_msgs) == 2
    assert isinstance(new_msgs[0], HumanMessage)
    assert isinstance(new_msgs[1], AIMessage)
    assert new_msgs[1].content == ai_content


def test_agent_node_sets_generation_complete_when_ai_says_finished(
    base_state: dict,
) -> None:
    """GIVEN state / WHEN agent returns AIMessage with no tool_calls and 'I have finished' / THEN generation_complete is True."""
    mock_ai = AIMessage(
        content="I have finished processing the document.", tool_calls=[]
    )

    with patch("backend.agent.get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value.invoke.return_value = mock_ai
        mock_get_llm.return_value = mock_llm

        result = agent_node(base_state)

    assert result.get("generation_complete") is True


def test_agent_node_keeps_generation_complete_false_when_tool_calls_present(
    base_state: dict,
) -> None:
    """GIVEN state / WHEN agent returns AIMessage with tool_calls / THEN generation_complete is False."""
    mock_ai = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "read_file",
                "args": {"filename": "source.txt"},
                "id": "1",
                "type": "tool_call",
            }
        ],
    )

    with patch("backend.agent.get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value.invoke.return_value = mock_ai
        mock_get_llm.return_value = mock_llm

        result = agent_node(base_state)

    assert result.get("generation_complete") is False


def test_agent_node_sets_pending_question_when_content_mentions_missing_file(
    base_state: dict,
) -> None:
    """GIVEN state / WHEN agent returns content with 'missing file' / THEN pending_question is non-empty."""
    mock_ai = AIMessage(
        content="I found a reference to a missing file: diagram.png. Please ask the user to upload or skip.",
        tool_calls=[],
    )

    with patch("backend.agent.get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value.invoke.return_value = mock_ai
        mock_get_llm.return_value = mock_llm

        result = agent_node(base_state)

    assert result.get("pending_question", "").strip() != ""


def test_agent_node_preserves_other_state_keys(base_state: dict) -> None:
    """GIVEN state with session_id, input_files / WHEN agent_node / THEN other keys preserved."""
    mock_ai = AIMessage(content="Done.", tool_calls=[])

    with patch("backend.agent.get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value.invoke.return_value = mock_ai
        mock_get_llm.return_value = mock_llm

        result = agent_node(base_state)

    assert result["session_id"] == base_state["session_id"]
    assert result["input_files"] == base_state["input_files"]


def test_build_initial_state_messages_compatible_with_base_message() -> None:
    """GIVEN build_initial_state / WHEN messages is used as list / THEN it can hold BaseMessage instances."""
    from langchain_core.messages import HumanMessage

    state = build_initial_state("sid", ["f.txt"])
    messages = list(state["messages"])
    messages.append(HumanMessage(content="test"))
    assert len(messages) == 1
    assert messages[0].content == "test"
