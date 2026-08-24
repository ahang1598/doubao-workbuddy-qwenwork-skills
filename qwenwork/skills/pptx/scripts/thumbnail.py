#!/usr/bin/env python3
"""Compatibility entry point for the cloud-first PPTX contact sheet renderer.

The latest local PPTX baseline calls this command ``thumbnail.py``.  Keep the
existing ``contact_sheet.py`` implementation as the single rendering module so
both names share cloud routing, hidden-slide handling, and local fallback.
"""

from contact_sheet import main


if __name__ == "__main__":
    main()
