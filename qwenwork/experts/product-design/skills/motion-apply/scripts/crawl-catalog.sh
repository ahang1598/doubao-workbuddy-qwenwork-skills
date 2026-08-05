#!/usr/bin/env bash
# crawl-catalog.sh — thin wrapper for backwards compatibility.
# Real implementation moved to crawl_catalog.py (more robust HTTP + JSON handling).
set -euo pipefail
exec python3 "$(dirname "$0")/crawl_catalog.py" "$@"
