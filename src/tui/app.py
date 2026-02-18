"""Main DocForge TUI application."""

import threading
from queue import Queue, Empty

from rich.live import Live
from rich.console import Console, Group
from rich.text import Text
from rich.columns import Columns
from src.tui.state import AppState
from src.tui.panels import render_sources, render_outline, render_log
from src.tui.watcher import FileWatcher
from src.tui.commands import (
    parse_command,
    handle_title,
    handle_intro,
    handle_chapter,
    handle_remove,
    handle_reset,
    handle_help,
    handle_quit,
)


class DocForgeApp:
    """Main TUI application with live rendering."""

    def __init__(self, state: AppState, watcher: FileWatcher):
        self.state = state
        self.watcher = watcher
        self._input_buffer = ""
        self._live = None
        self._running = True
        self._input_queue: Queue[str] = Queue()
        self._input_thread: threading.Thread | None = None

    def _make_layout(self):
        """Create the layout structure (placeholder for future Rich Layout)."""
        return None

    def _render(self):
        """Render all panels and return the complete display."""
        sources = render_sources(self.state)
        outline = render_outline(self.state)
        log_panel = render_log(self.state)

        # Top row: Sources | Outline
        top_row = Columns([sources, outline], equal=False)

        return Group(
            top_row,
            log_panel,
            Text(f"> {self._input_buffer}", style="bold cyan"),
        )

    def _run_input_loop(self):
        """Run the input loop in a separate thread."""
        while self._running:
            try:
                line = input()
                if line.strip():
                    self._input_queue.put(line)
            except EOFError:
                break
            except Exception:
                # Handle any other input errors gracefully
                break

    def _execute_command(self, raw: str) -> None:
        """Parse and execute a command."""
        cmd = parse_command(raw)
        if cmd is None:
            self.state.log_lines.append(f"Unknown command: {raw}")
            return

        if cmd.name == "title":
            handle_title(self.state, cmd.args)
        elif cmd.name == "intro":
            handle_intro(self.state, cmd.args)
        elif cmd.name == "chapter":
            handle_chapter(self.state, cmd.args)
        elif cmd.name == "remove":
            handle_remove(self.state, cmd.args)
        elif cmd.name == "reset":
            handle_reset(self.state)
        elif cmd.name == "help":
            handle_help(self.state)
        elif cmd.name == "quit":
            handle_quit(self.state, [self._running])

    def run(self):
        """Start the Live loop with refresh_per_second=4."""
        # Start input thread
        self._input_thread = threading.Thread(target=self._run_input_loop, daemon=True)
        self._input_thread.start()

        console = Console()
        with Live(
            self._render(), console=console, refresh_per_second=4, screen=True
        ) as live:
            self._live = live
            try:
                while self._running:
                    live.update(self._render())

                    # Process input queue (non-blocking)
                    try:
                        while True:
                            line = self._input_queue.get_nowait()
                            self._execute_command(line)
                    except Empty:
                        pass

                    import time

                    time.sleep(0.25)
            except KeyboardInterrupt:
                pass
