"""Unit tests for parse_to_json_node with new parser (Story 5.2). GIVEN-WHEN-THEN."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from backend.graph_nodes import parse_to_json_node
from backend.state import DocumentState


# --- Fixtures ---


@pytest.fixture
def temp_session_dir() -> Path:
    """GIVEN temporary session directory with required subdirs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        session_path = Path(tmpdir) / "sessions" / "test-session"
        session_path.mkdir(parents=True)
        for subdir in ["inputs", "assets", "checkpoints", "logs"]:
            (session_path / subdir).mkdir(exist_ok=True)
        yield session_path


@pytest.fixture
def mock_session_manager(temp_session_dir: Path) -> MagicMock:
    """GIVEN mocked SessionManager that uses temp directory."""
    sm = MagicMock()
    sm.get_path.return_value = temp_session_dir
    return sm


# --- parse_to_json_node tests ---


def test_parse_to_json_node_success(
    temp_session_dir: Path, mock_session_manager: MagicMock
) -> None:
    """GIVEN: valid temp_output.md with headings and paragraphs
    WHEN: parse_to_json_node runs
    THEN: returns structure_json_path, logs parse_completed
    """
    # Create markdown file
    temp_md = temp_session_dir / "temp_output.md"
    temp_md.write_text("# Test Title\n\nThis is a paragraph.\n", encoding="utf-8")

    state: DocumentState = {
        "session_id": "test-session",
    }

    with patch("backend.graph_nodes.SessionManager", return_value=mock_session_manager):
        with patch("backend.graph_nodes.logger") as mock_logger:
            result = parse_to_json_node(state)

    # Verify structure.json was written
    structure_path = temp_session_dir / "structure.json"
    assert result["structure_json_path"] == str(structure_path)
    assert structure_path.exists()

    # Verify structure content
    structure = json.loads(structure_path.read_text(encoding="utf-8"))
    assert structure["metadata"]["title"] == "Test Title"
    assert len(structure["sections"]) == 2

    # Verify logging
    mock_logger.info.assert_called()
    call_args = mock_logger.info.call_args
    assert call_args[0][0] == "parse_completed" or "structure.json" in str(call_args)


def test_parse_to_json_node_parse_failure_sets_error(
    temp_session_dir: Path, mock_session_manager: MagicMock
) -> None:
    """GIVEN: markdown with path traversal that causes parse error
    WHEN: parse_to_json_node runs
    THEN: sets conversion_success=False, last_error, NO structure.json written
    """
    # Create markdown with path traversal in image
    temp_md = temp_session_dir / "temp_output.md"
    temp_md.write_text("# Test\n\n![img](./../../etc/passwd)\n", encoding="utf-8")

    state: DocumentState = {
        "session_id": "test-session",
    }

    with patch("backend.graph_nodes.SessionManager", return_value=mock_session_manager):
        with patch("backend.graph_nodes.logger"):
            result = parse_to_json_node(state)

    # Verify structure.json was NOT written
    structure_path = temp_session_dir / "structure.json"
    assert not structure_path.exists()

    # Verify error state
    assert result.get("conversion_success") is False
    assert "last_error" in result
    assert "path traversal" in result["last_error"].lower()


def test_parse_to_json_node_missing_temp_file(
    temp_session_dir: Path, mock_session_manager: MagicMock
) -> None:
    """GIVEN: temp_output.md does not exist
    WHEN: parse_to_json_node runs
    THEN: creates empty structure with defaults
    """
    state: DocumentState = {
        "session_id": "test-session",
    }

    with patch("backend.graph_nodes.SessionManager", return_value=mock_session_manager):
        result = parse_to_json_node(state)

    # Verify structure.json was written with defaults
    structure_path = temp_session_dir / "structure.json"
    assert result["structure_json_path"] == str(structure_path)
    assert structure_path.exists()

    structure = json.loads(structure_path.read_text(encoding="utf-8"))
    assert structure["metadata"]["title"] == "Generated Document"
    assert structure["sections"] == []


def test_parse_to_json_node_unicode_error(
    temp_session_dir: Path, mock_session_manager: MagicMock
) -> None:
    """GIVEN: temp_output.md with invalid UTF-8
    WHEN: parse_to_json_node runs
    THEN: sets conversion_success=False, last_error, NO structure.json written
    """
    # Create file with invalid UTF-8
    temp_md = temp_session_dir / "temp_output.md"
    temp_md.write_bytes(b"# Title\n\nContent \xff\xfe")

    state: DocumentState = {
        "session_id": "test-session",
    }

    with patch("backend.graph_nodes.SessionManager", return_value=mock_session_manager):
        result = parse_to_json_node(state)

    # Verify structure.json was NOT written
    structure_path = temp_session_dir / "structure.json"
    assert not structure_path.exists()

    # Verify error state
    assert result.get("conversion_success") is False
    assert "last_error" in result
    assert "unicode" in result["last_error"].lower()


def test_parse_to_json_node_section_count_logged(
    temp_session_dir: Path, mock_session_manager: MagicMock
) -> None:
    """GIVEN: valid markdown with multiple sections
    WHEN: parse_to_json_node runs
    THEN: logs include section_count
    """
    temp_md = temp_session_dir / "temp_output.md"
    temp_md.write_text(
        "# Title\n\n## Section 1\n\nParagraph 1\n\n## Section 2\n\n```python\ncode\n```\n",
        encoding="utf-8",
    )

    state: DocumentState = {
        "session_id": "test-session",
    }

    with patch("backend.graph_nodes.SessionManager", return_value=mock_session_manager):
        with patch("backend.graph_nodes.logger") as mock_logger:
            _ = parse_to_json_node(state)

    # Check that section_count is in log extra
    call_args_list = mock_logger.info.call_args_list
    section_count_logged = False
    for call in call_args_list:
        extra = call[1].get("extra", {})
        if "section_count" in extra:
            section_count_logged = True
            # Should be at least 4 sections (H1, H2, paragraph, code_block)
            assert extra["section_count"] >= 4
            break

    # Also accept if logged via string interpolation
    assert section_count_logged or any(
        "section" in str(call[0]) for call in call_args_list
    )
