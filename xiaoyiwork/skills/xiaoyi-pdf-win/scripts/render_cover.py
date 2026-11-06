# 基于 MiniMax-AI/skills/minimax-pdf 修改，原项目协议：MIT License
# 原版权：Copyright (c) 2025 MiniMax AI

#!/usr/bin/env python3
"""
render_cover.py — Render cover.html → cover.pdf via Playwright (Python).

Usage:
    python3 render_cover.py --input cover.html --out cover.pdf
    python3 render_cover.py --input cover.html --out cover.pdf --wait 1200

Exit codes: 0 success, 1 bad args, 2 dependency missing, 3 render error
"""

import argparse
import json
import os
import shutil
import sys
from pathlib import Path


def usage():
    print("Usage: python3 render_cover.py --input <file.html> --out <file.pdf> [--wait <ms>]", file=sys.stderr)
    sys.exit(1)


def parse_args():
    parser = argparse.ArgumentParser(description="Render cover HTML to PDF via Playwright")
    parser.add_argument("--input", required=True, help="Input HTML file path")
    parser.add_argument("--out", required=True, help="Output PDF file path")
    parser.add_argument("--wait", type=int, default=800, help="Wait time in ms for CSS/JS to settle")
    return parser.parse_args()


def _browser_candidates() -> list[Path]:
    """Return system Chromium browser candidates in priority order."""
    candidates: list[Path] = []
    env_path = os.environ.get("CHROME_PATH", "").strip()
    if env_path:
        candidates.append(Path(env_path).expanduser())

    if sys.platform == "win32":
        program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        program_files_x86 = os.environ.get(
            "ProgramFiles(x86)", r"C:\Program Files (x86)"
        )
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        candidates.extend([
            Path(program_files) / "Google/Chrome/Application/chrome.exe",
            Path(program_files_x86) / "Google/Chrome/Application/chrome.exe",
            Path(program_files) / "Microsoft/Edge/Application/msedge.exe",
            Path(program_files_x86) / "Microsoft/Edge/Application/msedge.exe",
        ])
        if local_app_data:
            candidates.extend([
                Path(local_app_data) / "Google/Chrome/Application/chrome.exe",
                Path(local_app_data) / "Microsoft/Edge/Application/msedge.exe",
            ])
    elif sys.platform == "darwin":
        candidates.extend([
            Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
        ])
    else:
        candidates.extend([
            Path("/opt/chrome-linux/chrome"),
            Path("/usr/bin/google-chrome"),
            Path("/usr/bin/google-chrome-stable"),
            Path("/usr/bin/chromium"),
            Path("/usr/bin/chromium-browser"),
        ])
        for command in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
            resolved = shutil.which(command)
            if resolved:
                candidates.append(Path(resolved))

    # Keep the first occurrence so CHROME_PATH always wins.
    return list(dict.fromkeys(candidates))


def resolve_chrome_path() -> str | None:
    """Resolve an installed system browser, or use Playwright Chromium later."""
    for candidate in _browser_candidates():
        if candidate.is_file():
            return str(candidate)
    return None


def _launch_browser(chromium):
    """Launch a discovered system browser, falling back to Playwright's."""
    chrome_path = resolve_chrome_path()
    if chrome_path:
        return chromium.launch(executable_path=chrome_path)
    return chromium.launch()


def render_cover(input_file: str, output_file: str, wait_ms: int) -> dict:
    """Render HTML cover to PDF using Playwright."""
    input_path = Path(input_file)
    output_path = Path(output_file)

    # Validate input file exists
    if not input_path.exists():
        return {
            "status": "error",
            "error": f"File not found: {input_file}"
        }

    # Import playwright (may fail if not installed)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {
            "status": "error",
            "error": "playwright not found",
            "hint": "Wait for 小艺 Work dependency installation or retry from the skill page"
        }

    # Render using Playwright
    try:
        with sync_playwright() as p:
            browser = _launch_browser(p.chromium)
            page = browser.new_page()
            file_url = input_path.resolve().as_uri()
            page.goto(file_url)
            page.wait_for_timeout(wait_ms)

            page.pdf(
                path=str(output_path),
                width="794px",
                height="1123px",
                print_background=True
            )
            browser.close()
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to render: {e}",
            "hint": (
                "Set CHROME_PATH to Chrome/Edge, install a supported system browser, "
                "or run 'playwright install chromium' for the active Python interpreter"
            )
        }

    # Validate output
    stat = output_path.stat()
    if stat.st_size < 5000:
        return {
            "status": "error",
            "error": "Output PDF is suspiciously small — cover may be blank",
            "hint": "Check cover.html for render errors"
        }

    return {
        "status": "ok",
        "out": str(output_file),
        "size_kb": round(stat.st_size / 1024)
    }


def main():
    args = parse_args()
    result = render_cover(args.input, args.out, args.wait)

    # Print result as JSON
    print(json.dumps(result))

    # Exit with appropriate code
    if result["status"] == "ok":
        sys.exit(0)
    else:
        sys.exit(2 if "not found" in result.get("error", "").lower() else 3)


if __name__ == "__main__":
    main()
