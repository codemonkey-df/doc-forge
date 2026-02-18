"""DocForge - Main entry point."""

import argparse
import shutil
from pathlib import Path

from src.tui.state import AppState


def main():
    """Main entry point for DocForge."""
    parser = argparse.ArgumentParser(prog="docforge")
    parser.add_argument(
        "--input",
        default="./input",
        help="Input folder path (default: ./input)"
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Files to copy to input folder"
    )

    args = parser.parse_args()

    print("DocForge starting...")

    # Create input directory if it doesn't exist
    input_path = Path(args.input)
    input_path.mkdir(parents=True, exist_ok=True)

    # Copy positional files to input folder
    for file_path in args.files:
        src = Path(file_path)
        if src.exists():
            dest = input_path / src.name
            shutil.copy2(src, dest)

    # Create AppState instance
    state = AppState()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
