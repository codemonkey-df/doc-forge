"""MD to JSON structure parser for Story 5.2.

Converts temp_output.md to structure.json conforming to structure.schema.json.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any


def parse_md_to_structure(md_path: Path, session_path: Path) -> dict[str, Any]:
    """Parse markdown file to structure.json format.

    Reads markdown from md_path, parses headings, paragraphs, code blocks,
    tables, and images, and returns a dict conforming to structure.schema.json.

    Args:
        md_path: Path to temp_output.md file
        session_path: Path to session directory (for asset resolution)

    Returns:
        Dict with metadata (title, author, created) and sections array

    Raises:
        UnicodeDecodeError: If file cannot be read as UTF-8
        ValueError: If image path contains path traversal
    """
    # Read markdown with UTF-8 encoding
    md_content = md_path.read_text(encoding="utf-8")

    # Parse into sections
    sections = _parse_markdown_sections(md_content)

    # Extract title from first H1 or use default
    title = "Generated Document"
    for section in sections:
        if section["type"] == "heading1":
            title = section["text"]
            break

    # Build structure
    structure = {
        "metadata": {
            "title": title,
            "author": "AI Agent",
            "created": datetime.now().isoformat(),
        },
        "sections": sections,
    }

    return structure


def _parse_markdown_sections(content: str) -> list[dict[str, Any]]:
    """Parse markdown content into sections.

    Handles:
    - Headings (#, ##, ###) -> heading1, heading2, heading3
    - Fenced code blocks (```) -> code_block
    - Tables (|) -> table
    - Images (![alt](path)) -> image
    - Lists and blockquotes -> paragraph
    - Paragraphs -> paragraph

    Args:
        content: Markdown content string

    Returns:
        List of section dicts
    """
    sections: list[dict[str, Any]] = []

    if not content.strip():
        return sections

    lines = content.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]

        # Skip empty lines
        if not line.strip():
            i += 1
            continue

        # Parse heading
        if line.startswith("#"):
            heading = _parse_heading(line)
            if heading:
                sections.append(heading)
            i += 1
            continue

        # Parse code block
        if line.strip().startswith("```"):
            code_block = _parse_code_block(lines, i)
            if code_block:
                sections.append(code_block["section"])
                i = code_block["next_index"]
            continue

        # Parse table
        if _is_table_row(line):
            table_result = _parse_table(lines, i)
            if table_result:
                sections.append(table_result["section"])
                i = table_result["next_index"]
            continue

        # Parse image
        if _is_image_line(line):
            image = _parse_image(line)
            if image:
                sections.append(image)
                i += 1
            continue

        # Parse list or blockquote as paragraph
        if line.strip().startswith(("- ", "* ", "+ ")) or line.strip().startswith(">"):
            para = _parse_list_or_blockquote(lines, i)
            if para:
                sections.append(para["section"])
                i = para["next_index"]
            continue

        # Parse paragraph
        para_result = _parse_paragraph(lines, i)
        if para_result:
            sections.append(para_result["section"])
            i = para_result["next_index"]
            continue

        i += 1

    return sections


def _parse_heading(line: str) -> dict[str, Any] | None:
    """Parse a heading line.

    Args:
        line: Markdown line starting with #

    Returns:
        Section dict or None if not a valid heading
    """
    match = re.match(r"^(#{1,3})\s+(.+)$", line)
    if not match:
        return None

    level = len(match.group(1))
    text = match.group(2).strip()

    if level == 1:
        section_type = "heading1"
    elif level == 2:
        section_type = "heading2"
    else:
        section_type = "heading3"

    return {
        "type": section_type,
        "text": text,
    }


def _parse_code_block(lines: list[str], start_index: int) -> dict[str, Any] | None:
    """Parse a fenced code block.

    Args:
        lines: All markdown lines
        start_index: Index of opening ``` line

    Returns:
        Dict with section and next_index, or None
    """
    opening_line = lines[start_index]
    language = opening_line[3:].strip() or "text"

    code_lines = []
    i = start_index + 1

    while i < len(lines):
        if lines[i].strip().startswith("```"):
            break
        code_lines.append(lines[i])
        i += 1

    code_content = "\n".join(code_lines).rstrip()

    if code_content:
        return {
            "section": {
                "type": "code_block",
                "language": language,
                "code": code_content,
            },
            "next_index": i + 1,
        }

    return {"section": None, "next_index": i + 1}


def _is_table_row(line: str) -> bool:
    """Check if a line looks like a markdown table row.

    Args:
        line: Line to check

    Returns:
        True if line is a table row
    """
    line = line.strip()
    if not line.startswith("|") or not line.endswith("|"):
        return False
    # Must have at least one pipe in middle
    if "|" not in line[1:-1]:
        return False
    return True


def _parse_table(lines: list[str], start_index: int) -> dict[str, Any] | None:
    """Parse a markdown table.

    Args:
        lines: All markdown lines
        start_index: Index of first row

    Returns:
        Dict with section and next_index, or None
    """
    rows: list[list[str]] = []
    headers: list[str] = []
    i = start_index
    separator_found = False

    while i < len(lines):
        line = lines[i]

        if not line.strip():
            break

        if not _is_table_row(line):
            break

        # Skip separator row (|---|---| or |:---:|:---|
        if re.match(r"^\|[\s\-:]+\|[\s\-:]+\|$", line):
            separator_found = True
            i += 1
            continue

        cells = _parse_table_row(line)

        if not separator_found:
            headers = cells
        else:
            rows.append(cells)

        i += 1

    if not headers:
        return None

    # If no separator was found, treat first row as headers
    if not separator_found and rows:
        headers = rows[0]
        rows = rows[1:]

    return {
        "section": {
            "type": "table",
            "headers": headers,
            "rows": rows,
        },
        "next_index": i,
    }


def _parse_table_row(line: str) -> list[str]:
    """Parse a table row into cells.

    Args:
        line: Table row line

    Returns:
        List of cell strings
    """
    line = line.strip()
    # Remove leading and trailing pipes
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]

    cells = line.split("|")
    # Strip whitespace from each cell
    return [cell.strip() for cell in cells]


def _is_image_line(line: str) -> bool:
    """Check if a line contains a markdown image.

    Args:
        line: Line to check

    Returns:
        True if line contains image
    """
    return bool(re.match(r"^!\[.*\]\(.+\)$", line.strip()))


def _parse_image(line: str) -> dict[str, Any] | None:
    """Parse a markdown image.

    Args:
        line: Image line

    Returns:
        Image section dict or None
    """
    match = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)$", line.strip())
    if not match:
        return None

    alt = match.group(1)
    raw_path = match.group(2)

    # Validate path for path traversal
    _validate_image_path(raw_path)

    return {
        "type": "image",
        "path": raw_path,
        "alt": alt,
    }


def _validate_image_path(path: str) -> None:
    """Validate image path for security.

    Args:
        path: Image path from markdown

    Raises:
        ValueError: If path contains traversal sequences
    """
    # Reject path traversal attempts
    if ".." in path or path.startswith("/") or path.startswith("\\"):
        raise ValueError(f"Image path contains path traversal: {path}")


def _is_list_item(line: str) -> bool:
    """Check if a line is a list item.

    Args:
        line: Line to check

    Returns:
        True if line is a list item
    """
    stripped = line.strip()
    return stripped.startswith(("- ", "* ", "+ ")) or bool(
        re.match(r"^\d+\.\s+", stripped)
    )


def _parse_list_or_blockquote(
    lines: list[str], start_index: int
) -> dict[str, Any] | None:
    """Parse list items or blockquotes as paragraph.

    Args:
        lines: All markdown lines
        start_index: Index of first list/blockquote line

    Returns:
        Dict with paragraph section and next_index
    """
    content_lines: list[str] = []
    i = start_index

    while i < len(lines):
        line = lines[i]

        # Blockquote
        if line.strip().startswith(">"):
            content_lines.append(line.strip()[1:].strip())
            i += 1
            continue

        # List item
        if _is_list_item(line):
            # Strip list marker
            content = re.sub(r"^(\d+\.|-|\*|\+)\s+", "", line.strip())
            content_lines.append(content)
            i += 1
            continue

        # End of list/blockquote if we hit empty line or different element
        if not line.strip():
            break

        # Check for other markdown elements
        if (
            line.startswith("#")
            or line.strip().startswith("```")
            or _is_table_row(line)
        ):
            break

        break

    if not content_lines:
        return None

    text = " ".join(content_lines)

    return {
        "section": {
            "type": "paragraph",
            "text": text,
        },
        "next_index": i,
    }


def _parse_paragraph(lines: list[str], start_index: int) -> dict[str, Any] | None:
    """Parse a paragraph.

    Args:
        lines: All markdown lines
        start_index: Index of first paragraph line

    Returns:
        Dict with paragraph section and next_index
    """
    para_lines: list[str] = []
    i = start_index

    while i < len(lines):
        line = lines[i]

        # Empty line ends paragraph
        if not line.strip():
            break

        # Check for other elements
        if line.startswith("#") or line.strip().startswith("```"):
            break

        if _is_table_row(line):
            break

        if _is_image_line(line):
            break

        para_lines.append(line.strip())
        i += 1

    if not para_lines:
        return None

    text = " ".join(para_lines)

    return {
        "section": {
            "type": "paragraph",
            "text": text,
        },
        "next_index": i,
    }
