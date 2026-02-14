"""Routing logic for agent ↔ tools loop (Story 2.5).

AC2.5.2: route_after_tools(state) determines next node after tools execute.
Priority (human_input > validate > complete > agent):
  1. if pending_question → "human_input" (user must decide on missing ref)
  2. if last_checkpoint_id → "validate" (validate chapter after checkpoint)
  3. if generation_complete → "complete" (move to parse_to_json for conversion)
  4. else → "agent" (continue processing)

Routing enables the agent ↔ tools loop: agent calls tools → tools node updates
state with last_checkpoint_id and pending_question → routing decides next step.
"""

from __future__ import annotations

from backend.state import DocumentState


def route_after_tools(state: DocumentState) -> str:
    """Route after tools execute: agent | validate | human_input | complete.

    Priority order (AC2.5.2):
    1. pending_question (human-in-the-loop) → "human_input"
    2. last_checkpoint_id (chapter complete, needs validation) → "validate"
    3. generation_complete (all files processed) → "complete"
    4. else → "agent" (continue processing)

    Args:
        state: DocumentState after tools have run.

    Returns:
        One of: "human_input", "validate", "complete", "agent"
    """
    # Check 1: User needs to decide on missing reference
    if state.get("pending_question") and str(state["pending_question"]).strip():
        return "human_input"

    # Check 2: Chapter complete, needs validation before next chapter
    if state.get("last_checkpoint_id") and str(state["last_checkpoint_id"]).strip():
        return "validate"

    # Check 3: All content generated, move to conversion pipeline
    if state.get("generation_complete"):
        return "complete"

    # Check 4: Continue processing
    return "agent"
