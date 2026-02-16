"""Unit tests for md_to_json_parser (Story 5.2). GIVEN-WHEN-THEN."""

from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from backend.utils.md_to_json_parser import parse_md_to_structure


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


# --- parse_md_to_structure tests ---


def test_parse_minimal_md_with_h1_and_paragraph(temp_session_dir: Path) -> None:
    """GIVEN: minimal markdown with one H1 and paragraph
    WHEN: parse_md_to_structure is called
    THEN: returns valid structure with metadata and sections
    """
    md_content = "# My Document\n\nThis is a paragraph."
    md_path = temp_session_dir / "temp_output.md"
    md_path.write_text(md_content, encoding="utf-8")

    result = parse_md_to_structure(md_path, temp_session_dir)

    assert "metadata" in result
    assert "sections" in result
    assert result["metadata"]["title"] == "My Document"
    assert len(result["sections"]) == 2
    assert result["sections"][0]["type"] == "heading1"
    assert result["sections"][0]["text"] == "My Document"
    assert result["sections"][1]["type"] == "paragraph"


def test_parse_headings_h1_h2_h3(temp_session_dir: Path) -> None:
    """GIVEN: markdown with H1, H2, H3 headings
    WHEN: parse_md_to_structure is called
    THEN: sections have correct heading types
    """
    md_content = "# Heading 1\n\n## Heading 2\n\n### Heading 3"
    md_path = temp_session_dir / "temp_output.md"
    md_path.write_text(md_content, encoding="utf-8")

    result = parse_md_to_structure(md_path, temp_session_dir)

    sections = result["sections"]
    assert sections[0]["type"] == "heading1"
    assert sections[0]["text"] == "Heading 1"
    assert sections[1]["type"] == "heading2"
    assert sections[1]["text"] == "Heading 2"
    assert sections[2]["type"] == "heading3"
    assert sections[2]["text"] == "Heading 3"


def test_parse_code_blocks_with_language(temp_session_dir: Path) -> None:
    """GIVEN: markdown with fenced code blocks with language
    WHEN: parse_md_to_structure is called
    THEN: sections contain code_block with language and code
    """
    md_content = """# Code Example

```python
def hello():
    print("Hello, world!")
```

Some text.
"""
    md_path = temp_session_dir / "temp_output.md"
    md_path.write_text(md_content, encoding="utf-8")

    result = parse_md_to_structure(md_path, temp_session_dir)

    code_block = result["sections"][1]
    assert code_block["type"] == "code_block"
    assert code_block["language"] == "python"
    assert "def hello" in code_block["code"]


def test_parse_code_blocks_empty_language(temp_session_dir: Path) -> None:
    """GIVEN: markdown with fenced code block without language
    WHEN: parse_md_to_structure is called
    THEN: code_block has default language "text"
    """
    md_content = """# Code

```
some code here
```
"""
    md_path = temp_session_dir / "temp_output.md"
    md_path.write_text(md_content, encoding="utf-8")

    result = parse_md_to_structure(md_path, temp_session_dir)

    code_block = result["sections"][1]
    assert code_block["type"] == "code_block"
    assert code_block["language"] == "text"


def test_parse_tables_with_headers_and_rows(temp_session_dir: Path) -> None:
    """GIVEN: markdown with table
    WHEN: parse_md_to_structure is called
    THEN: sections contain table with headers and rows
    """
    md_content = "# Table\n\n| Column A | Column B |\n|----------|----------|\n| Cell 1   | Cell 2   |\n| Cell 3   | Cell 4   |\n"
    md_path = temp_session_dir / "temp_output.md"
    md_path.write_text(md_content, encoding="utf-8")

    result = parse_md_to_structure(md_path, temp_session_dir)

    table = result["sections"][1]
    assert table["type"] == "table"
    assert table["headers"] == ["Column A", "Column B"]
    assert len(table["rows"]) == 2
    assert table["rows"][0] == ["Cell 1", "Cell 2"]


def test_parse_images_with_alt_and_path(temp_session_dir: Path) -> None:
    """GIVEN: markdown with image
    WHEN: parse_md_to_structure is called
    THEN: sections contain image with alt and session-relative path
    """
    md_content = """# Image

![Alt text](./assets/image.png)
"""
    md_path = temp_session_dir / "temp_output.md"
    md_path.write_text(md_content, encoding="utf-8")

    result = parse_md_to_structure(md_path, temp_session_dir)

    image = result["sections"][1]
    assert image["type"] == "image"
    assert image["alt"] == "Alt text"
    assert image["path"] == "./assets/image.png"


def test_extract_title_from_first_h1(temp_session_dir: Path) -> None:
    """GIVEN: markdown with first H1 containing title
    WHEN: parse_md_to_structure is called
    THEN: metadata title is extracted from first H1
    """
    md_content = "# My Custom Title\n\nSome content."
    md_path = temp_session_dir / "temp_output.md"
    md_path.write_text(md_content, encoding="utf-8")

    result = parse_md_to_structure(md_path, temp_session_dir)

    assert result["metadata"]["title"] == "My Custom Title"


def test_default_title_when_no_h1(temp_session_dir: Path) -> None:
    """GIVEN: markdown without H1 heading
    WHEN: parse_md_to_structure is called
    THEN: metadata title defaults to "Generated Document"
    """
    md_content = "## Section 1\n\nSome content."
    md_path = temp_session_dir / "temp_output.md"
    md_path.write_text(md_content, encoding="utf-8")

    result = parse_md_to_structure(md_path, temp_session_dir)

    assert result["metadata"]["title"] == "Generated Document"


def test_iso8601_created_timestamp(temp_session_dir: Path) -> None:
    """GIVEN: valid markdown file
    WHEN: parse_md_to_structure is called
    THEN: metadata created is ISO8601 timestamp
    """
    md_content = "# Title\n\nContent."
    md_path = temp_session_dir / "temp_output.md"
    md_path.write_text(md_content, encoding="utf-8")

    result = parse_md_to_structure(md_path, temp_session_dir)

    created = result["metadata"]["created"]
    # Should be parseable as ISO8601
    parsed = datetime.fromisoformat(created)
    assert parsed is not None


def test_image_path_security_reject_traversal(temp_session_dir: Path) -> None:
    """GIVEN: markdown with path traversal in image path
    WHEN: parse_md_to_structure is called
    THEN: raises ValueError for security concern
    """
    md_content = """# Image

![Alt](./../../etc/passwd)
"""
    md_path = temp_session_dir / "temp_output.md"
    md_path.write_text(md_content, encoding="utf-8")

    with pytest.raises(ValueError, match="path traversal"):
        parse_md_to_structure(md_path, temp_session_dir)


def test_unicode_decode_error_handling(temp_session_dir: Path) -> None:
    """GIVEN: markdown file with invalid UTF-8 bytes
    WHEN: parse_md_to_structure is called
    THEN: raises UnicodeDecodeError with proper handling
    """
    md_path = temp_session_dir / "temp_output.md"
    # Write invalid UTF-8 bytes
    md_path.write_bytes(b"# Title\n\nContent \xff\xfe")

    with pytest.raises(UnicodeDecodeError):
        parse_md_to_structure(md_path, temp_session_dir)


def test_lists_fallback_to_paragraph(temp_session_dir: Path) -> None:
    """GIVEN: markdown with list items
    WHEN: parse_md_to_structure is called
    THEN: list items are converted to paragraph
    """
    md_content = """# List

- Item 1
- Item 2
- Item 3
"""
    md_path = temp_session_dir / "temp_output.md"
    md_path.write_text(md_content, encoding="utf-8")

    result = parse_md_to_structure(md_path, temp_session_dir)

    # Should be paragraph with list content
    para = result["sections"][1]
    assert para["type"] == "paragraph"
    assert "Item 1" in para["text"]


def test_blockquotes_fallback_to_paragraph(temp_session_dir: Path) -> None:
    """GIVEN: markdown with blockquotes
    WHEN: parse_md_to_structure is called
    THEN: blockquotes are converted to paragraph
    """
    md_content = """# Quote

> This is a blockquote
> with multiple lines
"""
    md_path = temp_session_dir / "temp_output.md"
    md_path.write_text(md_content, encoding="utf-8")

    result = parse_md_to_structure(md_path, temp_session_dir)

    para = result["sections"][1]
    assert para["type"] == "paragraph"
    assert "blockquote" in para["text"].lower()


def test_metadata_author_default(temp_session_dir: Path) -> None:
    """GIVEN: valid markdown
    WHEN: parse_md_to_structure is called
    THEN: author defaults to "AI Agent"
    """
    md_content = "# Title\n\nContent."
    md_path = temp_session_dir / "temp_output.md"
    md_path.write_text(md_content, encoding="utf-8")

    result = parse_md_to_structure(md_path, temp_session_dir)

    assert result["metadata"]["author"] == "AI Agent"


def test_empty_markdown_returns_structure(temp_session_dir: Path) -> None:
    """GIVEN: empty markdown file
    WHEN: parse_md_to_structure is called
    THEN: returns structure with empty sections
    """
    md_content = ""
    md_path = temp_session_dir / "temp_output.md"
    md_path.write_text(md_content, encoding="utf-8")

    result = parse_md_to_structure(md_path, temp_session_dir)

    assert "metadata" in result
    assert "sections" in result
    assert result["sections"] == []
    assert result["metadata"]["title"] == "Generated Document"
