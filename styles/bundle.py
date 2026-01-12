#!/usr/bin/env python3
"""TCSS Bundler - Concatenates modular TCSS files into main.tcss."""

import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

STYLES_DIR = Path(__file__).parent
SRC_DIR = STYLES_DIR / "src"
OUTPUT_FILE = STYLES_DIR / "main.tcss"

FOLDER_ORDER = [
    "00-base",
    "10-layout",
    "20-components",
    "30-blocks",
    "40-screens",
    "50-features",
    "60-utilities",
]


def generate_header() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    return f"""/* ==========================================================================
   Null Terminal - Generated Stylesheet
   
   AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY
   Edit source files in styles/src/ and run: python styles/bundle.py
   
   Generated: {timestamp}
   ========================================================================== */

"""


def generate_section_header(folder: str, file_count: int) -> str:
    folder_name = folder.split("-", 1)[1].upper() if "-" in folder else folder.upper()
    return f"""
/* ==========================================================================
   {folder_name} ({file_count} file{"s" if file_count != 1 else ""})
   ========================================================================== */

"""


def generate_file_header(filepath: Path) -> str:
    return f"/* --- {filepath.name} --- */\n\n"


def collect_files() -> dict[str, list[Path]]:
    files_by_folder: dict[str, list[Path]] = {}

    for folder in FOLDER_ORDER:
        folder_path = SRC_DIR / folder
        if not folder_path.exists():
            continue

        tcss_files = sorted(folder_path.glob("*.tcss"))
        if tcss_files:
            files_by_folder[folder] = tcss_files

    return files_by_folder


def bundle() -> tuple[str, int, int]:
    files_by_folder = collect_files()

    if not files_by_folder:
        return "", 0, 0

    output_parts = [generate_header()]
    total_files = 0
    total_folders = 0

    for folder in FOLDER_ORDER:
        if folder not in files_by_folder:
            continue

        files = files_by_folder[folder]
        total_folders += 1

        output_parts.append(generate_section_header(folder, len(files)))

        for filepath in files:
            total_files += 1
            output_parts.append(generate_file_header(filepath))
            content = filepath.read_text(encoding="utf-8")
            output_parts.append(content)
            if not content.endswith("\n"):
                output_parts.append("\n")
            output_parts.append("\n")

    return "".join(output_parts), total_files, total_folders


def build() -> bool:
    content, file_count, folder_count = bundle()

    if file_count == 0:
        print(f"[WARN] No .tcss files found in {SRC_DIR}")
        print(f"       Expected subdirectories: {', '.join(FOLDER_ORDER)}")
        return False

    OUTPUT_FILE.write_text(content, encoding="utf-8")

    print(f"[OK] Bundled {file_count} file(s) from {folder_count} folder(s)")
    print(f"     Output: {OUTPUT_FILE}")

    return True


def watch() -> None:
    print(f"[WATCH] Monitoring {SRC_DIR} for changes...")
    print("        Press Ctrl+C to stop\n")

    def get_mtimes() -> dict[Path, float]:
        mtimes = {}
        for folder in FOLDER_ORDER:
            folder_path = SRC_DIR / folder
            if folder_path.exists():
                for f in folder_path.glob("*.tcss"):
                    mtimes[f] = f.stat().st_mtime
        return mtimes

    last_mtimes = get_mtimes()
    build()

    try:
        while True:
            time.sleep(0.5)
            current_mtimes = get_mtimes()

            if current_mtimes != last_mtimes:
                changed = set(current_mtimes.keys()) ^ set(last_mtimes.keys())
                for path in current_mtimes:
                    if (
                        path in last_mtimes
                        and current_mtimes[path] != last_mtimes[path]
                    ):
                        changed.add(path)

                if changed:
                    print(f"\n[CHANGE] Detected: {', '.join(p.name for p in changed)}")
                    build()

                last_mtimes = current_mtimes
    except KeyboardInterrupt:
        print("\n[STOP] Watch stopped")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bundle TCSS files from styles/src/ into main.tcss"
    )
    parser.add_argument(
        "--watch",
        "-w",
        action="store_true",
        help="Watch for changes and rebuild automatically",
    )
    args = parser.parse_args()

    if not SRC_DIR.exists():
        print(f"[INFO] Creating source directory: {SRC_DIR}")
        SRC_DIR.mkdir(parents=True, exist_ok=True)
        for folder in FOLDER_ORDER:
            (SRC_DIR / folder).mkdir(exist_ok=True)
        print(f"       Created subdirectories: {', '.join(FOLDER_ORDER)}")
        print("\n[NEXT] Add .tcss files to the src/ subdirectories and run again")
        return 0

    if args.watch:
        watch()
    else:
        if not build():
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
