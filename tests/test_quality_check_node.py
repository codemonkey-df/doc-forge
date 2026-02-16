"""Unit tests for quality_check_node (Story 5.5)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from backend.graph_nodes import quality_check_node
from backend.state import DocumentState


class TestQualityCheckNode:
    """Test cases for the quality_check_node function."""

    @pytest.fixture
    def base_state(self) -> DocumentState:
        """Base state for testing."""
        return {
            "session_id": "test-session-123",
            "output_docx_path": "",
            "quality_passed": False,
            "quality_issues": [],
            "last_error": "",
            "status": "quality_checking",
        }

    def test_quality_check_node_pass(self, base_state, tmp_path):
        """Test quality_check_node when quality passes - quality_passed=True, status='complete'."""
        # Create a mock DOCX file
        docx_path = tmp_path / "output.docx"
        docx_path.write_bytes(b"PK\x03\x04")  # Minimal DOCX

        base_state["output_docx_path"] = str(docx_path)

        # Mock QualityValidator to return pass=True
        with patch("backend.graph_nodes.QualityValidator") as mock_validator_class:
            mock_validator = MagicMock()
            mock_validator.validate.return_value = {
                "passed": True,
                "issues": [],
                "score": 100,
            }
            mock_validator_class.return_value = mock_validator

            result = quality_check_node(base_state)

        assert result["quality_passed"] is True
        assert result["quality_issues"] == []
        assert result["status"] == "complete"
        assert result["last_error"] == ""

    def test_quality_check_node_fail(self, base_state, tmp_path):
        """Test quality_check_node when quality fails - quality_passed=False, status='error_handling'."""
        # Create a mock DOCX file
        docx_path = tmp_path / "output.docx"
        docx_path.write_bytes(b"PK\x03\x04")  # Minimal DOCX

        base_state["output_docx_path"] = str(docx_path)

        # Mock QualityValidator to return pass=False with issues
        with patch("backend.graph_nodes.QualityValidator") as mock_validator_class:
            mock_validator = MagicMock()
            mock_validator.validate.return_value = {
                "pass": False,
                "issues": [
                    "Skipped heading level: jumped from H1 to H3",
                    "Code block uses non-monospace font: Arial",
                ],
                "score": 60,
            }
            mock_validator_class.return_value = mock_validator

            result = quality_check_node(base_state)

        assert result["quality_passed"] is False
        assert len(result["quality_issues"]) == 2
        assert result["status"] == "error_handling"
        assert "Quality check failed" in result["last_error"]

    def test_quality_check_node_missing_docx(self, base_state):
        """Test quality_check_node with missing DOCX path - quality_passed=False, issue='No DOCX output to validate'."""
        # No output_docx_path set
        result = quality_check_node(base_state)

        assert result["quality_passed"] is False
        assert "No DOCX output to validate" in result["quality_issues"]
        assert result["status"] == "error_handling"
        assert result["last_error"] == "No DOCX output to validate"

    def test_quality_check_node_empty_docx_path(self, base_state):
        """Test quality_check_node with empty DOCX path string."""
        base_state["output_docx_path"] = ""
        result = quality_check_node(base_state)

        assert result["quality_passed"] is False
        assert "No DOCX output to validate" in result["quality_issues"]

    def test_quality_check_node_with_score(self, base_state, tmp_path):
        """Test that score is included in logging."""
        docx_path = tmp_path / "output.docx"
        docx_path.write_bytes(b"PK\x03\x04")

        base_state["output_docx_path"] = str(docx_path)

        with patch("backend.graph_nodes.QualityValidator") as mock_validator_class:
            mock_validator = MagicMock()
            mock_validator.validate.return_value = {
                "passed": True,
                "issues": [],
                "score": 100,
            }
            mock_validator_class.return_value = mock_validator

            # Just verify it doesn't error - the logging is captured via the mock
            result = quality_check_node(base_state)
            assert result["status"] == "complete"

    def test_quality_check_node_multiple_issues_summary(self, base_state, tmp_path):
        """Test that issue summary truncates to 3 issues in last_error."""
        docx_path = tmp_path / "output.docx"
        docx_path.write_bytes(b"PK\x03\x04")

        base_state["output_docx_path"] = str(docx_path)

        issues = [
            "Issue 1",
            "Issue 2",
            "Issue 3",
            "Issue 4",
            "Issue 5",
        ]

        with patch("backend.graph_nodes.QualityValidator") as mock_validator_class:
            mock_validator = MagicMock()
            mock_validator.validate.return_value = {
                "pass": False,
                "issues": issues,
                "score": 0,
            }
            mock_validator_class.return_value = mock_validator

            result = quality_check_node(base_state)

        # Should include "+2 more" for issues beyond 3
        assert "+2 more" in result["last_error"]
