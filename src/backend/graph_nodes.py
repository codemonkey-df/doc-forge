"""Graph nodes for Story 2.5: validate_md, parse_to_json, tools_node.

AC2.5.3: validate_md node runs markdown validation (markdownlint) and sets
validation_passed and validation_issues. Routes back to agent for fixes.

AC2.5.4: parse_to_json stub reads temp_output.md, writes minimal structure.json,
sets structure_json_path for downstream conversion epic.

Custom tools_node updates state from tool results: sets last_checkpoint_id from
create_checkpoint tool and pending_question from request_human_input tool.
"""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path
from typing import Any, cast

from backend.state import DocumentState
from backend.utils.session_manager import SessionManager

logger = logging.getLogger(__name__)

# Markdownlint JSON output field names
MARKDOWNLINT_LINE_KEY = "lineNumber"
MARKDOWNLINT_RULE_KEY = "ruleDescription"


def validate_md_node(state: DocumentState) -> DocumentState:
    """Run markdown validation on temp_output.md (AC2.5.3).

    Runs markdownlint on session temp_output.md, parses JSON issues,
    sets state[validation_passed] and state[validation_issues].

    Returns state with updated validation fields. On error, logs warning
    and returns state with validation_passed=False.

    Args:
        state: DocumentState with session_id and optionally temp_md_path.

    Returns:
        Updated DocumentState with validation_passed and validation_issues.
    """
    session_id = state.get("session_id", "")
    sm = SessionManager()
    session_path = sm.get_path(session_id)

    # Use provided temp_md_path or default
    temp_md_path = state.get("temp_md_path") or str(session_path / "temp_output.md")
    temp_md_file = Path(temp_md_path)

    if not temp_md_file.exists():
        logger.warning("temp_output.md not found at %s", temp_md_path)
        return cast(
            DocumentState,
            {
                **state,
                "validation_passed": False,
                "validation_issues": [
                    {"error": f"temp_output.md not found at {temp_md_path}"}
                ],
            },
        )

    try:
        # Run markdownlint on the file
        result = subprocess.run(
            ["markdownlint", str(temp_md_file), "--json"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            # No errors
            logger.info("Markdown validation passed for session %s", session_id)
            return cast(
                DocumentState,
                {
                    **state,
                    "validation_passed": True,
                    "validation_issues": [],
                },
            )

        # Parse JSON output for issues
        try:
            issues = json.loads(result.stdout) if result.stdout else []
        except json.JSONDecodeError:
            logger.warning(
                "Failed to parse markdownlint JSON output: %s", result.stdout
            )
            issues = [{"error": "Failed to parse markdownlint output"}]

        # Normalize issue format
        normalized_issues = []
        for issue in issues:
            if isinstance(issue, dict):
                normalized_issues.append(
                    {
                        "lineNumber": issue.get(MARKDOWNLINT_LINE_KEY, 0),
                        "ruleDescription": issue.get(
                            MARKDOWNLINT_RULE_KEY, "Unknown error"
                        ),
                    }
                )

        logger.info(
            "Markdown validation failed for session %s: %d issues",
            session_id,
            len(normalized_issues),
        )
        return cast(
            DocumentState,
            {
                **state,
                "validation_passed": False,
                "validation_issues": normalized_issues,
            },
        )

    except subprocess.TimeoutExpired:
        logger.error("Markdown validation timeout for session %s", session_id)
        return cast(
            DocumentState,
            {
                **state,
                "validation_passed": False,
                "validation_issues": [{"error": "Validation timeout"}],
            },
        )
    except subprocess.SubprocessError as e:
        logger.error(
            "Markdown validation subprocess error for session %s: %s",
            session_id,
            e,
        )
        return cast(
            DocumentState,
            {
                **state,
                "validation_passed": False,
                "validation_issues": [{"error": f"Validation error: {str(e)}"}],
            },
        )
    except Exception as e:
        logger.exception(
            "Unexpected error validating markdown for session %s",
            session_id,
        )
        return cast(
            DocumentState,
            {
                **state,
                "validation_passed": False,
                "validation_issues": [{"error": f"Unexpected error: {str(e)}"}],
            },
        )


def parse_to_json_node(state: DocumentState) -> DocumentState:
    """Convert temp_output.md to structure.json stub (AC2.5.4).

    Reads markdown file, parses basic structure (headings, paragraphs, code blocks),
    writes minimal JSON structure for docx-js converter.

    Sets state[structure_json_path] pointing to created structure.json file
    in session root. This enables the conversion epic (Epic 4) to consume the
    structured format.

    Args:
        state: DocumentState with session_id and optionally temp_md_path.

    Returns:
        Updated DocumentState with structure_json_path set.
    """
    session_id = state.get("session_id", "")
    sm = SessionManager()
    session_path = sm.get_path(session_id)

    # Use provided temp_md_path or default
    temp_md_path = state.get("temp_md_path") or str(session_path / "temp_output.md")
    temp_md_file = Path(temp_md_path)

    structure_json_path = session_path / "structure.json"

    # Read markdown (handle missing file gracefully)
    if not temp_md_file.exists():
        logger.warning(
            "temp_output.md not found at %s, creating empty structure", temp_md_path
        )
        md_content = ""
    else:
        try:
            md_content = temp_md_file.read_text(encoding="utf-8")
        except Exception as e:
            logger.error("Failed to read %s: %s", temp_md_path, e)
            md_content = ""

    # Parse markdown into sections
    sections = _parse_markdown_to_sections(md_content)

    # Build structure JSON (minimal stub for conversion epic)
    structure = {
        "metadata": {
            "title": "Generated Document",
            "author": "AI Agent",
            "created": _get_iso_timestamp(),
        },
        "sections": sections,
    }

    # Write structure.json
    try:
        structure_json_path.write_text(
            json.dumps(structure, indent=2),
            encoding="utf-8",
        )
        logger.info(
            "Created structure.json for session %s with %d sections",
            session_id,
            len(sections),
        )
    except Exception as e:
        logger.error(
            "Failed to write structure.json for session %s: %s",
            session_id,
            e,
        )
        # Still return state with path, conversion epic can handle missing file

    return cast(
        DocumentState,
        {
            **state,
            "structure_json_path": str(structure_json_path),
        },
    )


def _parse_markdown_to_sections(content: str) -> list[dict[str, Any]]:
    """Parse markdown content into sections (headings, paragraphs, code blocks).

    Simple regex-based parsing to extract:
    - Headings (# → ###) → heading1/heading2/heading3
    - Code blocks (```language ... ```) → code_block
    - Paragraphs → paragraph

    Returns list of section dicts compatible with structure.json schema.
    """
    sections: list[dict[str, Any]] = []

    if not content.strip():
        return sections

    lines = content.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]

        # Parse heading
        if line.startswith("#"):
            level = len(line.split()[0])  # Count # chars
            if 1 <= level <= 3:
                text = line[level:].strip()
                sections.append(
                    {
                        "type": f"heading{level}",
                        "text": text,
                    }
                )
            i += 1
            continue

        # Parse code block
        if line.strip().startswith("```"):
            language = line[3:].strip() or "text"
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            if i < len(lines):
                i += 1  # Skip closing ```

            code_content = "\n".join(code_lines).rstrip()
            if code_content:  # Only add if non-empty
                sections.append(
                    {
                        "type": "code_block",
                        "language": language,
                        "code": code_content,
                    }
                )
            continue

        # Skip empty lines
        if not line.strip():
            i += 1
            continue

        # Parse paragraph
        para_lines = []
        while i < len(lines) and lines[i].strip():
            if lines[i].startswith("#") or lines[i].strip().startswith("```"):
                break
            para_lines.append(lines[i])
            i += 1

        para_text = " ".join([l.strip() for l in para_lines]).strip()
        if para_text:
            sections.append(
                {
                    "type": "paragraph",
                    "text": para_text,
                }
            )

    return sections


def _get_iso_timestamp() -> str:
    """Return current timestamp in ISO format."""
    from datetime import datetime

    return datetime.now().isoformat()


def tools_node(state: DocumentState) -> DocumentState:
    """Custom tools node: execute tools and update state from results (AC2.5.1, 2.5.2).

    After LangGraph's ToolNode executes tool calls, this node:
    1. Parses last message for tool results
    2. Sets last_checkpoint_id if create_checkpoint was called
    3. Sets pending_question if request_human_input was called

    This enables route_after_tools to access these fields for conditional routing.

    Note: This is a stub implementation. In practice, this integrates with
    LangGraph's ToolNode. For now, this documents the expected behavior.

    Args:
        state: DocumentState with messages from agent/tools loop.

    Returns:
        Updated DocumentState with last_checkpoint_id and pending_question
        set from tool results if applicable.
    """
    # TODO: Integrate with actual ToolNode to extract tool results
    # For now, this documents the expected pattern:
    #
    # if last_message is ToolMessage and message.name == "create_checkpoint":
    #     state["last_checkpoint_id"] = message.content
    # if last_message is ToolMessage and message.name == "request_human_input":
    #     state["pending_question"] = message.content

    return state
