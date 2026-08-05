#!/usr/bin/env python3
"""Compatibility wrapper for the old Doubao-only sync entrypoint."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sync_platform import main  # noqa: E402


if __name__ == "__main__":
    if "--platform" not in sys.argv:
        sys.argv.extend(["--platform", "doubao"])
    raise SystemExit(main())
