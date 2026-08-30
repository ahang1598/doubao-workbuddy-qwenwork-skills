#!/usr/bin/env python3
"""Extract the last MCP tool result from QoderWork/QwenWorkCN session log.

Usage: python3 extract_mcp_result.py <output_file> [--marker <keyword>]

Automatically finds the latest session JSONL file and extracts the most
recent tool_result that looks like MCP data (JSON array/object > 200 chars).
This avoids the agent having to regenerate large MCP results via Write/heredoc.

In parallel testing (two QoderWork instances), --marker is essential to
distinguish between sessions: it searches all recent JSONL files (newest
first) and skips results that don't contain the marker keyword.
"""
import json
import glob
import os
import sys


def find_recent_session_jsonls(limit=5):
    """Find the most recently modified session JSONL files (newest first)."""
    candidates = []
    for base in ["~/.qoderwork/projects", "~/.qwenworkcn/projects"]:
        pattern = os.path.expanduser(f"{base}/*/*.jsonl")
        candidates.extend(glob.glob(pattern))
    if not candidates:
        return []
    candidates.sort(key=os.path.getmtime, reverse=True)
    return candidates[:limit]


def extract_last_mcp_result(jsonl_path, marker=None):
    """Read JSONL backwards; return last tool_result that looks like MCP data."""
    with open(jsonl_path, "r") as f:
        lines = f.readlines()

    for line in reversed(lines):
        try:
            d = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue

        # QoderWork stores tool results in toolUseResult field
        tur = d.get("toolUseResult", "")
        if tur and isinstance(tur, str) and len(tur) > 200:
            stripped = tur.strip()
            if stripped and stripped[0] in "[{":
                if marker is None or marker in tur:
                    return tur

        # Also check message.content for tool_result
        msg = d.get("message", {})
        if isinstance(msg, dict):
            content = msg.get("content", [])
            if isinstance(content, list):
                for item in content:
                    if not isinstance(item, dict):
                        continue
                    if item.get("type") != "tool_result":
                        continue
                    inner = item.get("content", "")
                    if isinstance(inner, str) and len(inner) > 200:
                        stripped = inner.strip()
                        if stripped and stripped[0] in "[{":
                            if marker is None or marker in inner:
                                return inner
    return None


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 extract_mcp_result.py <output_file> [--marker <keyword>]", file=sys.stderr)
        sys.exit(1)

    output_file = sys.argv[1]
    marker = None
    if "--marker" in sys.argv:
        idx = sys.argv.index("--marker")
        if idx + 1 < len(sys.argv):
            marker = sys.argv[idx + 1]

    jsonl_paths = find_recent_session_jsonls()
    if not jsonl_paths:
        print("Error: No session JSONL file found in ~/.qoderwork or ~/.qwenworkcn", file=sys.stderr)
        sys.exit(1)

    # Search through recent JSONL files (newest first) for the MCP result.
    # With --marker, skip results that don't contain the keyword.
    # This handles parallel testing where multiple sessions write simultaneously.
    for jsonl_path in jsonl_paths:
        result = extract_last_mcp_result(jsonl_path, marker)
        if result:
            with open(output_file, "w") as f:
                f.write(result)
            print(f"OK: extracted {len(result)} chars to {output_file}")
            return

    marker_hint = f" with marker '{marker}'" if marker else ""
    print(f"Error: No MCP tool result{marker_hint} found in {len(jsonl_paths)} recent session logs", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
