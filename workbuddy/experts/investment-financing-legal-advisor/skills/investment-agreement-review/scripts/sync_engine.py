#!/usr/bin/env python3
# © 深圳市法大大网络科技有限公司 版权所有
"""sync_engine — 把共享内核引擎物化进 investment-agreement/contract-parse/scripts/。

投资协议家族复用 contract-review-core 的抽段/入库引擎，但遵守“自包含部署”契约：
不跨包 import，而是把所需引擎从 SSOT 物化进 contract-parse 包。`skill_paths.py` 是
本家族自有的适配层（见同名文件），不从 SSOT 覆盖。

  python3 tools/sync_engine.py            # 物化/更新
  python3 tools/sync_engine.py --check    # 校验已物化副本与 SSOT 一致（上架前必跑）
"""
from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # 自研Skills/
SSOT = ROOT / "_shared" / "contract-review-core" / "scripts"
DEST = ROOT / "investment-agreement" / "contract-parse" / "scripts"
ENGINE_FILES = ["ooxml_engine.py", "pdf_intake.py"]  # skill_paths 为本家族自有，不物化


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)

    drift = []
    for f in ENGINE_FILES:
        src, dst = SSOT / f, DEST / f
        if not src.exists():
            print(f"error: SSOT 缺少 {src}", file=sys.stderr)
            return 2
        if args.check:
            if not dst.exists() or not filecmp.cmp(src, dst, shallow=False):
                drift.append(f)
        else:
            shutil.copy2(src, dst)
            print(f"materialized {f} → {dst}")

    if args.check:
        if drift:
            print(f"[DRIFT] 与 SSOT 不一致：{drift}（请运行 sync_engine.py 重新物化）")
            return 1
        print("all engine copies in sync with SSOT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
