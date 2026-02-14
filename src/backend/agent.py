"""Agent node: single-step LLM invoke with tools (Story 2.3).

Agent node reads state["messages"] (List[BaseMessage]), appends user prompt and
AIMessage, returns state with messages, generation_complete, and pending_question.
No internal ReAct loop; graph provides agent → tools → agent.

Completion detection: generation_complete is True when the last AIMessage has
no tool_calls and content indicates done (e.g. "finished", "complete").
Interrupt detection: pending_question is set when content contains keywords
("missing file", "external reference", "need user", "ask the user") or when
the agent called request_human_input (Story 2.5 tools node sets it from result).

Messages return: we return only [human_msg, response] because LangGraph uses
a reducer (operator.add) on state["messages"]; the graph merges existing + delta.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, cast

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_litellm import ChatLiteLLM

from backend.prompts import SYSTEM_PROMPT, build_user_prompt
from backend.state import DocumentState
from backend.tools import get_tools

if TYPE_CHECKING:
    from backend.utils.settings import LLMSettings

logger = logging.getLogger(__name__)

# Max length for pending_question extracted from AI content (avoid huge state).
PENDING_QUESTION_MAX_LEN = 500

# Keywords in AI content that indicate completion (no more tool calls needed).
COMPLETION_PHRASES = (
    "finished",
    "complete",
    "generation complete",
    "i have finished",
    "done.",
)
# Keywords that indicate the agent is asking the user (missing file, external ref).
INTERRUPT_KEYWORDS = (
    "missing file",
    "external reference",
    "need user",
    "ask the user",
    "ask user",
)


def get_llm(settings: LLMSettings | None = None):  # noqa: ANN201
    """Build ChatLiteLLM with model and temperature from config. No API key in code."""
    from backend.utils.settings import LLMSettings

    s = settings if settings is not None else LLMSettings()
    return ChatLiteLLM(model=s.model, temperature=s.temperature)


def _content_str(content: str | list[Any] | None) -> str:
    """Normalize AIMessage content to a single string for detection logic."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and "text" in block:
                parts.append(block["text"])
        return " ".join(parts).strip()
    return str(content).strip()


def _is_completion(ai_message: AIMessage) -> bool:
    """True when AIMessage has no tool_calls and content indicates completion."""
    if getattr(ai_message, "tool_calls", None):
        return False
    content = _content_str(ai_message.content).lower()
    return any(phrase in content for phrase in COMPLETION_PHRASES)


def _extract_pending_question(ai_message: AIMessage) -> str:
    """If content suggests asking the user (missing file, etc.), return a short message."""
    content = _content_str(ai_message.content).lower()
    for kw in INTERRUPT_KEYWORDS:
        if kw in content:
            return _content_str(ai_message.content)[:PENDING_QUESTION_MAX_LEN]
    return ""


def agent_node(
    state: DocumentState | dict[str, Any],
    *,
    llm: Any = None,
) -> DocumentState:
    """Single-step agent: one LLM invoke per run. Appends HumanMessage + AIMessage; sets generation_complete and pending_question.

    Reads state["messages"], builds user prompt (with validation_issues if present),
    invokes LLM with tools from get_tools(state["session_id"]), returns state update
    with messages delta, generation_complete, and pending_question.
    """
    session_id = state.get("session_id", "")
    if not session_id or not str(session_id).strip():
        logger.warning("agent_node called with empty session_id")
    existing: list[BaseMessage] = list(state.get("messages") or [])

    user_content = build_user_prompt(dict(state))
    human_msg = HumanMessage(content=user_content)

    tools = get_tools(session_id)
    model = llm if llm is not None else get_llm()
    bound = model.bind_tools(tools)

    messages_for_invoke: list[BaseMessage] = [
        SystemMessage(content=SYSTEM_PROMPT),
        *existing,
        human_msg,
    ]
    try:
        response = bound.invoke(messages_for_invoke)
    except Exception as e:
        logger.exception("LLM invocation failed for session %s: %s", session_id, e)
        return cast(
            DocumentState,
            {
                **state,
                "status": "failed",
                "last_error": str(e),
                "error_type": "llm",
            },
        )
    if not isinstance(response, AIMessage):
        response = AIMessage(content=str(response))

    generation_complete = _is_completion(response)
    pending_question = (
        _extract_pending_question(response) or state.get("pending_question") or ""
    )

    status = state.get("status", "processing")
    if generation_complete:
        status = "complete"

    return cast(
        DocumentState,
        {
            **state,
            "messages": [human_msg, response],
            "generation_complete": generation_complete,
            "pending_question": pending_question,
            "status": status,
        },
    )
