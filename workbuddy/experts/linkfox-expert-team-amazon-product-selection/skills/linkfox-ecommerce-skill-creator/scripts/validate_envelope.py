#!/usr/bin/env python3
"""已废弃：请改用 scripts/validate_product_payload.py。"""

from __future__ import annotations

import sys
from pathlib import Path

# 保证从仓库根目录执行 `python scripts/validate_envelope.py` 时能找到同目录模块
sys.path.insert(0, str(Path(__file__).resolve().parent))

from validate_product_payload import main  # noqa: E402

if __name__ == "__main__":
    print(
        "WARNING: validate_envelope.py 已废弃，请改用 validate_product_payload.py",
        file=sys.stderr,
    )
    main()
