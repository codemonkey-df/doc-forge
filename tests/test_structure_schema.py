"""Tests for the structure.json schema validation."""

import json
from pathlib import Path

import jsonschema
import pytest


# Get the path to the schema file
SCHEMA_PATH = (
    Path(__file__).parent.parent / "docs" / "schemas" / "structure.schema.json"
)


@pytest.fixture
def schema():
    """Load the JSON schema."""
    with open(SCHEMA_PATH) as f:
        return json.load(f)


@pytest.fixture
def valid_structure():
    """A valid structure.json example."""
    return {
        "metadata": {
            "title": "Test Document",
            "author": "AI Assistant",
            "created": "2025-02-11T10:30:00Z",
        },
        "sections": [
            {"type": "heading1", "text": "Chapter 1: Introduction", "id": "h1_1"},
            {
                "type": "paragraph",
                "text": "This is a regular paragraph.",
                "formatting": ["normal"],
            },
            {
                "type": "code_block",
                "language": "python",
                "code": "def hello():\n    print('world')",
            },
            {
                "type": "table",
                "headers": ["Column 1", "Column 2"],
                "rows": [["Data 1", "Data 2"]],
            },
            {
                "type": "image",
                "path": "./assets/diagram.png",
                "alt": "System Diagram",
                "width": 400,
            },
        ],
    }


@pytest.fixture
def minimal_structure():
    """A minimal valid structure.json example."""
    return {
        "metadata": {
            "title": "Minimal Document",
            "author": "Test",
            "created": "2025-02-11T10:30:00Z",
        },
        "sections": [
            {"type": "heading2", "text": "Overview"},
            {"type": "code_block", "code": "print('hello')"},
            {"type": "image", "path": "./assets/test.png"},
        ],
    }


class TestStructureSchema:
    """Tests for structure.json schema validation."""

    def test_schema_file_exists(self):
        """Test that the schema file exists."""
        assert SCHEMA_PATH.exists(), f"Schema file not found at {SCHEMA_PATH}"

    def test_valid_structure(self, schema, valid_structure):
        """Test that a valid structure passes validation."""
        jsonschema.validate(valid_structure, schema)

    def test_minimal_structure(self, schema, minimal_structure):
        """Test that a minimal structure passes validation."""
        jsonschema.validate(minimal_structure, schema)

    def test_heading_types(self, schema):
        """Test all heading types are valid."""
        for heading_type in ["heading1", "heading2", "heading3"]:
            structure = {
                "metadata": {
                    "title": "Test",
                    "author": "Test",
                    "created": "2025-02-11T10:30:00Z",
                },
                "sections": [{"type": heading_type, "text": "Test Heading"}],
            }
            jsonschema.validate(structure, schema)

    def test_paragraph_without_formatting(self, schema):
        """Test paragraph without formatting field."""
        structure = {
            "metadata": {
                "title": "Test",
                "author": "Test",
                "created": "2025-02-11T10:30:00Z",
            },
            "sections": [{"type": "paragraph", "text": "Plain text"}],
        }
        jsonschema.validate(structure, schema)

    def test_code_block_without_language(self, schema):
        """Test code block without language field."""
        structure = {
            "metadata": {
                "title": "Test",
                "author": "Test",
                "created": "2025-02-11T10:30:00Z",
            },
            "sections": [{"type": "code_block", "code": "some code"}],
        }
        jsonschema.validate(structure, schema)

    def test_table_with_empty_rows(self, schema):
        """Test table with empty rows array."""
        structure = {
            "metadata": {
                "title": "Test",
                "author": "Test",
                "created": "2025-02-11T10:30:00Z",
            },
            "sections": [{"type": "table", "headers": ["Column 1"], "rows": []}],
        }
        jsonschema.validate(structure, schema)

    def test_image_minimal(self, schema):
        """Test image with only required fields."""
        structure = {
            "metadata": {
                "title": "Test",
                "author": "Test",
                "created": "2025-02-11T10:30:00Z",
            },
            "sections": [{"type": "image", "path": "./assets/test.png"}],
        }
        jsonschema.validate(structure, schema)

    def test_invalid_type(self, schema):
        """Test that invalid type fails validation."""
        structure = {
            "metadata": {
                "title": "Test",
                "author": "Test",
                "created": "2025-02-11T10:30:00Z",
            },
            "sections": [{"type": "invalid_type", "text": "Some text"}],
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(structure, schema)

    def test_missing_required_field_in_section(self, schema):
        """Test that missing required field in section fails validation."""
        structure = {
            "metadata": {
                "title": "Test",
                "author": "Test",
                "created": "2025-02-11T10:30:00Z",
            },
            "sections": [{"type": "paragraph"}],
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(structure, schema)

    def test_missing_metadata_field(self, schema):
        """Test that missing metadata field fails validation."""
        structure = {"metadata": {"title": "Test"}, "sections": []}
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(structure, schema)

    def test_root_requires_metadata_and_sections(self, schema):
        """Test that root object requires metadata and sections fields."""
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate({}, schema)
