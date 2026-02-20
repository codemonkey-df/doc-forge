"""Application state dataclasses."""

import threading
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ChapterEntry:
    """Represents a chapter in the document."""

    file_path: str
    custom_title: str | None = None


@dataclass
class AppState:
    """Application state for DocForge."""

    title: str = "Untitled"
    intro_file: str | None = None
    imported_file: str | None = None
    chapters: list[ChapterEntry] = field(default_factory=list)
    detected_files: list[str] = field(default_factory=list)
    log_lines: list[str] = field(default_factory=list)
    pipeline_complete: threading.Event = field(default_factory=threading.Event)

    # ── Preview / approval flow ─────────────────────────────────────────
    # Set to True after MD is written; TUI switches to preview mode.
    preview_mode: bool = False
    # Path to the generated .md file awaiting user approval.
    pending_md_path: Path | None = None
    # Scroll offset for the preview panel (lines from the top).
    preview_scroll: int = 0
    # Signal fired by pipeline background thread once MD is on disk.
    md_ready: threading.Event = field(default_factory=threading.Event)
    # Signal used to tell the background thread to proceed (accept) or abort.
    preview_accepted: threading.Event = field(default_factory=threading.Event)
    preview_cancelled: threading.Event = field(default_factory=threading.Event)