#!/usr/bin/env python3
"""
按银行聚合 partial JSON -> $RETAIL_ANALYSIS_HOME/data/<kind>/<bank>.json

路径约定
--------
所有 Skill 共享的数据根目录由 ``scripts/paths.py`` 解析，默认
``~/RetailAnalysis``，可通过环境变量 ``RETAIL_ANALYSIS_HOME`` 覆盖。

上游约定：
  每次 (bank × period) 的提取产物落盘到
    $RETAIL_ANALYSIS_HOME/data/partial/{kind}_{bank}_{period}.json
  （例：~/RetailAnalysis/data/partial/standard_某某_2025年度.json）

本脚本把同一银行的多个 period 合并为
  $RETAIL_ANALYSIS_HOME/data/{kind}/{bank}.json
  {
    "bank": "某某银行",
    "kind": "standard",                     // "standard" 或 "text"
    "periods": ["2024年度", "2025年度", ...],
    "by_period": {
      "2025年度": { ...原 partial 文件内容, 去掉 bank 字段... },
      "2024年度": { ... }
    },
    "updated_at": "2026-04-27T21:45:00"
  }

典型用法
--------
  # 聚合 Skill 2 的结果（使用默认 Home 路径）
  python scripts/merge_partials.py --kind text

  # 聚合 Skill 1 的结果（Skill 1 有自己的副本）
  python scripts/merge_partials.py --kind standard

  # 只聚合单家银行
  python scripts/merge_partials.py --kind text --bank 某某

  # 显式指定目录（覆盖默认）
  python scripts/merge_partials.py \
    --kind text \
    --partial-dir ~/RetailAnalysis/data/partial \
    --output-dir ~/RetailAnalysis/data/text

  # 干跑，仅列出将要写入的文件
  python scripts/merge_partials.py --kind text --dry-run
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# paths.py 已同步为本 Skill scripts/ 下的副本（由 release.py 保证与仓库根一致）
# import 策略：同目录优先（zip 打包场景）→ 仓库根兜底（开发期）
_SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))
try:
    import paths  # noqa: E402  # 共享路径约定
except ImportError:
    _repo_scripts = _SCRIPT_DIR.parent.parent.parent / "scripts"
    if _repo_scripts.is_dir() and str(_repo_scripts) not in sys.path:
        sys.path.insert(0, str(_repo_scripts))
    import paths  # noqa: E402


# partial 文件命名约定：{kind}_{bank}_{period}.json
# bank / period 中不允许出现下划线（中文银行名天然满足，period 如 "2025年度" / "2025H1" 也满足）
# 若后续 period 需要包含下划线，可改为 "__" 作为分隔符
FNAME_RE = re.compile(r"^(?P<kind>standard|text)_(?P<bank>[^_]+)_(?P<period>[^_]+)\.json$")


def _parse_filename(fname: str) -> Optional[Tuple[str, str, str]]:
    m = FNAME_RE.match(fname)
    if not m:
        return None
    return m.group("kind"), m.group("bank"), m.group("period")


def _period_sort_key(period: str) -> Tuple[int, str]:
    """
    按期末时间排序的 key。支持：
      - "2025年度" / "2024年度"  → (202512, original)
      - "2025H1" / "2024H2"     → (202506 / 202412, ...)
      - "2025Q1" / "2025Q3"     → (202503 / 202509, ...)
      - 其他                     → (0, original)  排在最前以便显式识别
    """
    m = re.match(r"^(\d{4})年度$", period)
    if m:
        return (int(m.group(1)) * 100 + 12, period)
    m = re.match(r"^(\d{4})H([12])$", period)
    if m:
        month = 6 if m.group(2) == "1" else 12
        return (int(m.group(1)) * 100 + month, period)
    m = re.match(r"^(\d{4})Q([1-4])$", period)
    if m:
        month = int(m.group(2)) * 3
        return (int(m.group(1)) * 100 + month, period)
    return (0, period)


def _collect_partials(
    partial_dir: pathlib.Path,
    kind: str,
    bank_filter: Optional[str],
) -> Dict[str, List[Tuple[str, pathlib.Path]]]:
    """返回 {bank -> [(period, path), ...]}。"""
    by_bank: Dict[str, List[Tuple[str, pathlib.Path]]] = {}
    for p in sorted(partial_dir.glob("*.json")):
        parsed = _parse_filename(p.name)
        if not parsed:
            continue
        k, bank, period = parsed
        if k != kind:
            continue
        if bank_filter and bank_filter not in (bank,):
            continue
        by_bank.setdefault(bank, []).append((period, p))
    # 按 period 排序
    for bank in by_bank:
        by_bank[bank].sort(key=lambda t: _period_sort_key(t[0]))
    return by_bank


def _canonicalize_period_block(raw: Dict[str, Any], period: str) -> Dict[str, Any]:
    """把历史/异常 partial 展开成规范 PeriodBlock，避免嵌套 by_period。"""
    block: Any = raw.get("data", raw)
    seen_ids = set()
    while isinstance(block, dict) and isinstance(block.get("by_period"), dict):
        if id(block) in seen_ids:
            break
        seen_ids.add(id(block))
        nested_by_period = block["by_period"]
        nested = nested_by_period.get(period)
        if nested is None and len(nested_by_period) == 1:
            nested = next(iter(nested_by_period.values()))
        if not isinstance(nested, dict):
            break
        block = nested

    if not isinstance(block, dict):
        block = {}
    cleaned = {
        k: v for k, v in block.items()
        if k not in {"bank", "bank_key", "kind", "periods", "by_period", "_schema_version"}
    }
    cleaned["period"] = cleaned.get("period") or period
    if not isinstance(cleaned.get("metrics"), list):
        cleaned["metrics"] = []
    return cleaned


def _build_bank_doc(
    kind: str,
    bank_key: str,
    period_files: List[Tuple[str, pathlib.Path]],
) -> Dict[str, Any]:
    """
    把一家银行的多 period partial 合并为单个 JSON。

    bank_key 来自文件名（通常是简称，如"中信"），
    JSON 内 bank 字段保留 partial 里原写的值（可能是"中信银行"等全称）。
    若多期 partial 的 bank 字段不一致，记录到 bank_aliases 并在合并后打 warning。
    """
    by_period: Dict[str, Any] = {}
    bank_values: List[str] = []
    for period, path in period_files:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw.get("bank"), str):
            bank_values.append(raw["bank"])
        by_period[period] = _canonicalize_period_block(raw, period)

    # 取频次最高者作为展示 bank；其余收入 aliases
    canonical = bank_key
    aliases: List[str] = []
    if bank_values:
        from collections import Counter
        counter = Counter(bank_values)
        canonical = counter.most_common(1)[0][0]
        aliases = sorted({v for v in bank_values if v != canonical})

    doc: Dict[str, Any] = {
        "bank": canonical,
        "bank_key": bank_key,        # 与文件名一致的简称，供下游 glob 后 key-by
        "kind": kind,
        "_schema_version": "text-v1.0" if kind == "text" else "standard-v1.0",
        "periods": [p for p, _ in period_files],
        "by_period": by_period,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    if aliases:
        doc["bank_aliases"] = aliases
    return doc


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="按银行聚合 partial JSON")
    p.add_argument(
        "--kind",
        required=True,
        choices=["standard", "text"],
        help="聚合 standard（Skill 1）或 text（Skill 2）",
    )
    p.add_argument(
        "--partial-dir",
        default=str(paths.PARTIAL_DIR),
        help=f"partial 目录（默认 {paths.PARTIAL_DIR}）",
    )
    p.add_argument(
        "--output-dir",
        default=None,
        help=(
            "输出目录（未指定时：kind=standard -> "
            f"{paths.STANDARD_DIR}，kind=text -> {paths.TEXT_DIR}）"
        ),
    )
    p.add_argument(
        "--bank",
        help="只聚合指定银行（可选），用于增量更新",
    )
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


def main() -> None:
    args = build_args()
    partial_dir = pathlib.Path(args.partial_dir).expanduser()
    if args.output_dir:
        out_dir = pathlib.Path(args.output_dir).expanduser()
    else:
        out_dir = paths.STANDARD_DIR if args.kind == "standard" else paths.TEXT_DIR

    if not partial_dir.exists():
        raise SystemExit(f"partial 目录不存在: {partial_dir}")

    by_bank = _collect_partials(partial_dir, args.kind, args.bank)
    if not by_bank:
        print(
            f"[merge] 未找到 kind={args.kind} bank={args.bank or '*'} 的 partial 文件",
            flush=True,
        )
        return

    out_dir.mkdir(parents=True, exist_ok=True)
    total_files = 0
    for bank, pairs in by_bank.items():
        doc = _build_bank_doc(args.kind, bank, pairs)
        target = out_dir / f"{bank}.json"
        periods_summary = ", ".join(doc["periods"])
        if args.dry_run:
            print(
                f"[dry-run] {target} ← {len(pairs)} periods ({periods_summary})",
                flush=True,
            )
            continue
        target.write_text(
            json.dumps(doc, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        total_files += 1
        print(
            f"[merge] {target}  periods={len(pairs)} ({periods_summary})",
            flush=True,
        )

    if not args.dry_run:
        print(f"[merge] done. {total_files} file(s) written to {out_dir}", flush=True)


if __name__ == "__main__":
    main()
