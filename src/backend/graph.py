"""Minimal LangGraph workflow for Story 1.4, 2.1, 2.4: START → scan_assets → human_input | agent → END.

Session is not created in the graph; entry provides state with session_id and
input_files. scan_assets reads from state only (session_id, input_files) and
uses SessionManager.get_path for session root; no SessionManager.create in graph.

Story 2.4 adds: checkpointer (MemorySaver) for interrupt/resume, interrupt_before=["human_input"]
to pause at human_input node, and conditional edge from agent → human_input when pending_question
(second interrupt point for external references during generation).

Resume flow (caller-managed):
  1. Entry: workflow.invoke(initial_state, config) with thread_id in config
  2. Graph: detects missing_references, routes to human_input (interrupt)
  3. Caller: receives state, collects user decisions, validates upload paths
  4. Caller: updates state["user_decisions"], clears state["pending_question"]
  5. Caller: workflow.invoke(None, config) with same thread_id to resume
  6. Graph: human_input node runs, continues to agent, completes workflow
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from backend.agent import agent_node as agent_node_impl
from backend.state import DocumentState
from backend.utils.session_manager import SessionManager

logger = logging.getLogger(__name__)

# Markdown image syntax: ![alt](path)
IMAGE_REF_PATTERN = re.compile(r"!\[.*?\]\((.*?)\)")


def _scan_assets_impl(
    state: DocumentState, session_manager: SessionManager
) -> DocumentState:
    """Read input files, detect image refs (regex), set missing_references and pending_question or status=processing.

    Uses only state["session_id"] and state["input_files"]; does not create session.
    """
    session_id = state["session_id"]
    input_files = state["input_files"]
    session_path = session_manager.get_path(session_id)
    inputs_dir = session_path / "inputs"

    missing_refs: list[str] = []

    for filename in input_files:
        file_path = inputs_dir / filename
        if not file_path.exists():
            continue
        try:
            content = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            logger.warning("Skipping file %s: %s", file_path, e)
            continue
        for match in IMAGE_REF_PATTERN.finditer(content):
            ref = match.group(1).strip()
            if ref.startswith("http"):
                continue
            # Resolve in order: inputs dir, session root, then absolute path
            candidate = (inputs_dir / ref).resolve()
            if not candidate.exists():
                candidate = (session_path / ref).resolve()
            if not candidate.exists():
                try:
                    candidate = Path(ref).resolve()
                except (OSError, ValueError):
                    pass
            if not candidate.exists():
                missing_refs.append(ref)

    if missing_refs:
        return {
            **state,
            "missing_references": missing_refs,
            "pending_question": f"Missing images: {', '.join(missing_refs)}. Upload or skip?",
            "status": "scanning_assets",
        }
    return {
        **state,
        "status": "processing",
    }


def _human_input_node(state: DocumentState) -> DocumentState:
    """Stub: return state unchanged. After resume, entry injects user_decisions."""
    return state


def _agent_node(state: DocumentState) -> DocumentState:
    """Single-step agent node (Story 2.3). One LLM invoke; returns state with messages, generation_complete, pending_question."""
    return agent_node_impl(state)


def create_document_workflow(
    session_manager: SessionManager | None = None,
) -> Any:
    """Build and compile the document workflow. Graph starts at scan_assets (Story 2.1, 2.4).

    Entry injects session_manager so scan_assets can resolve session path.

    Story 2.4 additions (interrupt/resume for human-in-the-loop):
    - Checkpointer: MemorySaver allows saving/restoring state at thread_id
    - interrupt_before=["human_input"]: graph pauses before human_input node
      (first interrupt point: when missing_references detected in scan_assets)
    - Conditional edge from agent to human_input when pending_question is set
      (second interrupt point: when agent detects external reference during generation)
    - Resume flow: caller invokes workflow.invoke(None, config) with same thread_id
      after updating state["user_decisions"] and clearing state["pending_question"]

    Args:
        session_manager: Optional SessionManager for dependency injection (test/mock friendly).

    Returns:
        Compiled graph with checkpointer and interrupt_before support.
    """
    sm = session_manager if session_manager is not None else SessionManager()

    def scan_assets_node(state: DocumentState) -> DocumentState:
        return _scan_assets_impl(state, sm)

    workflow = StateGraph(DocumentState)
    workflow.add_node("scan_assets", scan_assets_node)
    workflow.add_node("human_input", _human_input_node)
    workflow.add_node("agent", _agent_node)

    workflow.add_edge(START, "scan_assets")

    # Conditional edge 1: scan_assets → human_input | agent
    # Task 1: If missing_references non-empty, route to human_input (interrupt point 1)
    workflow.add_conditional_edges(
        "scan_assets",
        lambda s: "human_input" if s.get("missing_references") else "agent",
        {"human_input": "human_input", "agent": "agent"},
    )

    # Task 4: Edge from human_input to agent (after interrupt is resolved, resume to agent)
    workflow.add_edge("human_input", "agent")

    # Conditional edge 2: agent → human_input | END
    # Task 5: If pending_question set, route to human_input (interrupt point 2)
    # pending_question is set when agent detects external reference during generation
    workflow.add_conditional_edges(
        "agent",
        lambda s: "human_input" if s.get("pending_question") else "END",
        {"human_input": "human_input", "END": END},
    )

    # Task 6: Compile with checkpointer and interrupt_before (Story 2.4)
    checkpointer = MemorySaver()
    return workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_input"],
    )