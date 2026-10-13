#!/usr/bin/env python3
"""Report draft gates and the permanent no-signature-certification result."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from intake_runtime import draft_readiness


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("work_data", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    data = json.loads(args.work_data.read_text(encoding="utf-8"))
    payload = json.dumps(draft_readiness(data), ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
