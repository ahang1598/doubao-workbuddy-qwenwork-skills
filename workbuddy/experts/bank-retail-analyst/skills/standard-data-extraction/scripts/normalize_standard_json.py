#!/usr/bin/env python3
"""
normalize_standard_json.py —— 将 $RA/data/standard/<bank>.json 统一到 Skill 1 规范 schema

转换规则
--------
1. 某银行 2020-2021 年度结构异常：pd 被当成顶层文件再嵌一层 `by_period[<period>]`，展开为扁平 period dict
2. 某银行 period 层冗余字段（year / metadata / extraction_date）→ 删除
3. metric 扁平结构 → 包装为 `{standard_name, values:[{...}]}` 标准结构
   - 兴业: `{standard_name, value, unit, source_table, confidence}`
   - 光大: `{category, standard_name, value:str|num, unit, source, notes, confidence}`
4. metric 层冗余字段（招商 `unit` / 光大 `category` 等）→ 删除（仅保留 `standard_name` / `values`）
5. value 层字符串数值（如 "58,663百万元" / "1,234.56"）→ 拆分为 float + unit
6. 顶层补 `_schema_version: "standard-v1.0"` + 规范化 `periods` 列表

用法
----
    python normalize_standard_json.py --dry-run
    python normalize_standard_json.py --apply           # 备份后原地写回
    python normalize_standard_json.py --apply --bank 某甲 某乙

幂等：`_schema_version == "standard-v1.0"` 则跳过（除非指定 --force）。
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# paths 模块（修正 skill-local paths.py 的路径 bug）
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import paths as _paths  # noqa: E402
_REAL_REPO_ROOT = SCRIPT_DIR.parent.parent.parent
_paths.REPO_ROOT = _REAL_REPO_ROOT
_paths.SKILL_DIRS = {
    "cninfo-bank-reports": _REAL_REPO_ROOT / "skills" / "cninfo-bank-reports",
    "skill1": _REAL_REPO_ROOT / "skills" / "standard-data-extraction",
    "skill2": _REAL_REPO_ROOT / "skills" / "text-data-extraction",
    "skill3": _REAL_REPO_ROOT / "skills" / "benchmark-analysis",
    "skill4": _REAL_REPO_ROOT / "skills" / "strategic-insight",
    "skill5": _REAL_REPO_ROOT / "skills" / "strategy-governance-analysis",
}
from paths import STANDARD_DIR  # noqa: E402

SCHEMA_VERSION = "standard-v1.0"
BANKS = ["中信", "招商", "兴业", "平安", "浦发", "光大", "民生"]

# 规范 period 层字段
PERIOD_KEYS_ALLOWED = {"period", "metrics", "notes", "warnings", "source_markdown"}

# 规范 metric 层字段
METRIC_KEYS_ALLOWED = {"standard_name", "values"}

# 规范 value 层字段
VALUE_KEYS_ALLOWED = {
    "period_label", "value", "unit",
    "raw_label_in_table", "source_line_range", "candidate_id",
    "confidence", "note",
}

# value 数值字符串解析：匹配开头的数字（含千分位、负号、小数），剩余视作单位
_VALUE_NUM_RE = re.compile(r"^\s*(-?[\d,]+(?:\.\d+)?)\s*(.*?)\s*$")


def _parse_value_number(raw: Any) -> Tuple[Optional[float], Optional[str]]:
    """把 '58,663百万元' / '1,234.56' / 12345 拆成 (float, unit_or_None)。"""
    if raw is None:
        return None, None
    if isinstance(raw, bool):
        return None, None  # 避免 True/False 被当数值
    if isinstance(raw, (int, float)):
        return float(raw), None
    if not isinstance(raw, str):
        return None, None
    s = raw.strip()
    if not s or s in ("-", "—", "–", "N/A", "n/a"):
        return None, None
    m = _VALUE_NUM_RE.match(s)
    if not m:
        return None, None
    try:
        return float(m.group(1).replace(",", "")), (m.group(2).strip() or None)
    except ValueError:
        return None, None


def normalize_value_item(src: Dict[str, Any], period_label: str) -> Optional[Dict[str, Any]]:
    """标准化一条 value dict；返回 None 表示空。"""
    if not isinstance(src, dict):
        return None

    raw_val = src.get("value")
    raw_unit = src.get("unit")
    value, inferred_unit = _parse_value_number(raw_val)
    if isinstance(raw_unit, str) and raw_unit.strip():
        unit = raw_unit.strip()
    else:
        unit = inferred_unit

    if value is None and not src.get("raw_label_in_table") and not src.get("note"):
        return None

    out: Dict[str, Any] = {
        "period_label": src.get("period_label") or period_label,
        "value": value,
        "unit": unit,
        "raw_label_in_table": src.get("raw_label_in_table"),
        "source_line_range": src.get("source_line_range"),
        "candidate_id": src.get("candidate_id"),
        "confidence": src.get("confidence", "medium" if value is not None else "low"),
    }
    # note 只在有值时写入
    note = src.get("note")
    if note:
        out["note"] = note
    return out


def flatten_metric(raw: Dict[str, Any], period_label: str) -> Dict[str, Any]:
    """
    把可能是扁平格式的 metric 统一到 {standard_name, values[]}。

    某银行A扁平：{standard_name, value, unit, source_table, confidence}
    某银行B扁平：{category, standard_name, value: "58,663百万元", unit, source, notes, confidence}
    某银行C冗余：{values: [], unit, standard_name}  ← metric 层 unit 冗余
    """
    std_name = raw.get("standard_name", "")

    # 分支 1：已有 values[]（规范结构，但可能 metric 层有 unit 冗余需清除）
    if isinstance(raw.get("values"), list):
        normed_values = []
        for v in raw["values"]:
            nv = normalize_value_item(v, period_label)
            if nv is not None:
                normed_values.append(nv)
        return {"standard_name": std_name, "values": normed_values}

    # 分支 2：扁平结构 → 构造一条 value
    # 源别名映射
    pseudo_value = {
        "period_label": raw.get("period_label") or period_label,
        "value": raw.get("value"),
        "unit": raw.get("unit"),
        "raw_label_in_table": raw.get("raw_label_in_table") or raw.get("source_table") or raw.get("source"),
        "source_line_range": raw.get("source_line_range"),
        "candidate_id": raw.get("candidate_id"),
        "confidence": raw.get("confidence", "medium"),
        "note": raw.get("note") or raw.get("notes"),
    }
    nv = normalize_value_item(pseudo_value, period_label)
    return {"standard_name": std_name, "values": [nv] if nv else []}


def flatten_nested_by_period(pdata: Dict[str, Any], period: str) -> Dict[str, Any]:
    """某银行 2020-2021：pd 被嵌了一层 by_period[<period>]，展开。"""
    if not isinstance(pdata, dict) or "by_period" not in pdata:
        return pdata
    inner = pdata.get("by_period", {})
    if not isinstance(inner, dict):
        return pdata
    # 优先匹配同名，其次取第一个 dict
    if period in inner and isinstance(inner[period], dict):
        return inner[period]
    for _, v in inner.items():
        if isinstance(v, dict):
            return v
    return pdata


def normalize_period(pdata: Dict[str, Any], period: str) -> Tuple[Dict[str, Any], List[str]]:
    """标准化一期数据。"""
    warnings: List[str] = []
    pdata = flatten_nested_by_period(pdata, period)

    if not isinstance(pdata, dict):
        return {
            "period": period, "metrics": [], "notes": [],
            "warnings": [f"period 数据非 dict，类型 {type(pdata).__name__}"],
            "source_markdown": None,
        }, []

    # 丢弃非规范 period 层字段（记到 warnings 便于审计）
    unknown = sorted(set(pdata.keys()) - PERIOD_KEYS_ALLOWED)
    if unknown:
        warnings.append(
            f"period 层非规范字段已丢弃: {unknown}"
        )

    raw_metrics = pdata.get("metrics", []) or []
    normed_metrics: List[Dict[str, Any]] = []
    for idx, m in enumerate(raw_metrics):
        if not isinstance(m, dict):
            warnings.append(f"metric#{idx} 非 dict，已丢弃")
            continue
        std_name = m.get("standard_name")
        if not std_name:
            warnings.append(f"metric#{idx} 缺 standard_name，已丢弃")
            continue
        normed_metrics.append(flatten_metric(m, period))

    return {
        "period": period,
        "metrics": normed_metrics,
        "notes": pdata.get("notes", []) or [],
        "warnings": (pdata.get("warnings", []) or []) + warnings,
        "source_markdown": pdata.get("source_markdown"),
    }, warnings


def normalize_bank_json(src: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """标准化单家银行 JSON。"""
    all_warnings: List[str] = []
    by_period_in = src.get("by_period", {}) or {}
    by_period_out: Dict[str, Any] = {}
    for period, pdata in by_period_in.items():
        np, w = normalize_period(pdata, period)
        by_period_out[period] = np
        all_warnings.extend([f"[{period}] {x}" for x in w])

    out = {
        "bank": src.get("bank", ""),
        "bank_key": src.get("bank_key", ""),
        "kind": "standard",
        "_schema_version": SCHEMA_VERSION,
    }
    # bank_aliases 可选保留
    if src.get("bank_aliases"):
        out["bank_aliases"] = src["bank_aliases"]
    out["periods"] = sorted(by_period_out.keys())
    out["by_period"] = by_period_out
    out["updated_at"] = datetime.now().isoformat(timespec="seconds")
    return out, all_warnings


# ---------------------------------------------------------------------------
# 差异报告
# ---------------------------------------------------------------------------

def summarize(data: Dict[str, Any]) -> Dict[str, Any]:
    n_periods = len(data.get("by_period", {}))
    n_metrics_total = 0
    n_metrics_with_values = 0
    n_flat_metrics = 0  # metric 层有 value 字段（非规范）
    n_nested_period = 0  # period 层有 by_period 嵌套
    for p, pd in (data.get("by_period", {}) or {}).items():
        if not isinstance(pd, dict):
            continue
        if "by_period" in pd:
            n_nested_period += 1
        # 展开一层再数 metrics（仅用于 src 端计数）
        inner_pd = flatten_nested_by_period(pd, p) if "by_period" in pd else pd
        for m in (inner_pd.get("metrics", []) or []):
            if not isinstance(m, dict):
                continue
            n_metrics_total += 1
            if isinstance(m.get("values"), list) and m["values"]:
                n_metrics_with_values += 1
            if "value" in m and "values" not in m:
                n_flat_metrics += 1
    return {
        "n_periods": n_periods,
        "n_metrics_total": n_metrics_total,
        "n_with_values": n_metrics_with_values,
        "n_flat_metrics": n_flat_metrics,
        "n_nested_period": n_nested_period,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="试跑，不写盘")
    ap.add_argument("--apply", action="store_true", help="备份后原地写回")
    ap.add_argument("--bank", nargs="*", default=None, help="只处理指定银行")
    ap.add_argument("--standard-dir", default=str(STANDARD_DIR))
    ap.add_argument("--force", action="store_true", help="即使已是 current schema 也重新处理")
    args = ap.parse_args()

    if not (args.dry_run or args.apply):
        ap.error("必须指定 --dry-run 或 --apply")

    root = Path(args.standard_dir).expanduser().resolve()
    if not root.is_dir():
        print(f"❌ 目录不存在：{root}", file=sys.stderr)
        return 2

    targets = args.bank or BANKS

    for bank in targets:
        f = root / f"{bank}.json"
        if not f.exists():
            print(f"⚠️  跳过 {bank}：{f} 不存在")
            continue

        src = json.loads(f.read_text())
        if src.get("_schema_version") == SCHEMA_VERSION and not args.force:
            print(f"ℹ️  {bank} 已是 {SCHEMA_VERSION}，跳过（用 --force 强制重跑）")
            continue

        src_stats = summarize(src)
        dst, warnings = normalize_bank_json(src)
        dst_stats = summarize(dst)

        print(f"\n=== {bank} ===")
        print(f"  src : periods={src_stats['n_periods']}, metrics={src_stats['n_metrics_total']}, "
              f"有 values={src_stats['n_with_values']}, 扁平={src_stats['n_flat_metrics']}, "
              f"嵌套 period={src_stats['n_nested_period']}")
        print(f"  dst : periods={dst_stats['n_periods']}, metrics={dst_stats['n_metrics_total']}, "
              f"有 values={dst_stats['n_with_values']}, 扁平={dst_stats['n_flat_metrics']}, "
              f"嵌套 period={dst_stats['n_nested_period']}")
        if warnings:
            print(f"  ⚠️  {len(warnings)} warnings, top 3:")
            for w in warnings[:3]:
                print(f"     - {w}")

        if args.apply:
            backup = f.with_suffix(f.suffix + f".bak.{datetime.now():%Y%m%d-%H%M%S}")
            shutil.copy2(f, backup)
            f.write_text(json.dumps(dst, ensure_ascii=False, indent=2))
            print(f"  ✅ 已写回（备份 {backup.name}）")

    return 0


if __name__ == "__main__":
    sys.exit(main())
