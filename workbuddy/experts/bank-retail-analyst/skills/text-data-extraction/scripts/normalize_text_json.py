#!/usr/bin/env python3
"""
normalize_text_json.py —— 将 $RA/data/text/<bank>.json 统一到 Skill 2 规范 schema

背景（2026-04-30 故障复盘）
---------------------------
历史各银行 JSON 由不同阶段/不同子代理产出，字段命名七家各异：
- standard_name 字段名：中信/平安用 name，招商/兴业/浦发用 metric，光大用 indicator，民生用 metric_type
- 单位字段：中信/兴业/浦发用 unit，平安/光大/民生用 value_unit，招商把单位嵌入 value 字符串
- 原文字段：中信/民生用 source_text，平安/兴业/浦发/光大用 original_text，招商用 note
- 所有银行都**缺失 category_bucket 字段**（765 条 metric 全部 <missing>）
- 所有银行都把 period_end_value 直接扁平挂在 metric 上，**丢失了 values[] 数组层**
- 光大/民生 2025年度 **被多套了一层 by_period["2025年度"] 嵌套**，真实 metrics 在里层

本脚本职责
-----------
1. 修正 by_period 嵌套异常（展开 pdata.by_period.<period>.metrics → pdata.metrics）
2. 将 metric 字段 rename 到 SKILL.md 契约：
   name | metric | indicator | metric_type → standard_name
   category | (按名称反查 metrics.yaml) → category_bucket（7 个枚举值）
3. 将扁平 value/unit/raw_quote 等字段包装进 values[] 数组
4. F/G bucket 的 standard_name 补全 `(文字)` 后缀
5. 招商的字符串形式 value（如 "170,825.19亿元"）拆分为 period_end_value + unit

用法
----
    python normalize_text_json.py --check                     # 只检查差异，不改文件
    python normalize_text_json.py --dry-run                   # 打印转换结果，不写盘
    python normalize_text_json.py --apply                     # 备份后原地写回
    python normalize_text_json.py --apply --bank 某某 招商    # 只处理指定银行

幂等：已经规范化的 JSON 再次运行不会重复修改（通过 `_schema_version` 元字段判断）。
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

import yaml

# ---------------------------------------------------------------------------
# 使 scripts 目录能直接找到 paths 模块
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from paths import TEXT_DIR, get_skill_config_file  # noqa: E402

SCHEMA_VERSION = "text-v1.0"  # 每次 schema 结构变动递增
BANKS = ["中信", "招商", "兴业", "平安", "浦发", "光大", "民生"]

# 与 SKILL.md / references/02_bucket_details.md 一致的 bucket 枚举
VALID_BUCKETS = {"AUM", "客户数", "财富收入", "信用卡", "分部效益", "量价", "渠道", "其他"}

# 按名称包含的关键词兜底推断 bucket（当 metrics.yaml 未命中时）
BUCKET_KEYWORDS = [
    ("分部效益", ["分部营收", "分部营业", "分部税前", "营业净收入", "税前利润",
                "非息净收入", "非息收入", "非利息净收入", "信用减值损失",
                "零售营收", "零售利润", "零售非息", "零售减值"]),
    ("AUM",      ["AUM", "零售AUM", "私行AUM", "管理客户资产", "管理零售",
                "个人客户金融资产", "零售客户资产"]),
    ("客户数",   ["客户数", "客户总数", "贵宾", "金葵花", "钻石", "代发客户",
                "私人银行客户", "私行客户"]),
    ("财富收入", ["财富管理收入", "理财收入", "保险收入", "基金收入",
                "代销", "代理", "财富业务收入"]),
    ("信用卡",   ["信用卡发卡", "信用卡累计发卡", "信用卡有效", "信用卡流通",
                "信用卡交易", "信用卡消费", "发卡量"]),
    ("量价",     ["个人存款余额", "零售存款余额", "存款成本率", "付息率",
                "贷款收益率", "贷款平均利率", "贷款不良率", "零售不良"]),
    ("渠道",     ["手机银行", "MAU", "APP", "网点"]),
]

# metric 层字段别名（来自旧 schema）
METRIC_NAME_ALIASES = (
    "standard_name", "name", "metric", "indicator", "metric_type", "metric_name",
)
METRIC_CATEGORY_ALIASES = ("category_bucket", "category", "category_code")

# 老版 category 单字母映射：A→AUM, B→客户数, C→财富收入, D→信用卡,
# E→其他（渠道/其他量化）, F→分部效益, G→量价, H→其他
LEGACY_CATEGORY_LETTER_MAP = {
    "A": "AUM",
    "B": "客户数",
    "C": "财富收入",
    "D": "信用卡",
    "E": "其他",
    "F": "分部效益",
    "G": "量价",
    "H": "其他",
}

# value 层字段别名
VALUE_NUMBER_ALIASES = ("period_end_value", "value", "current_value")
VALUE_UNIT_ALIASES = ("unit", "value_unit", "current_value_unit")
VALUE_CHANGE_ALIASES = ("change_value", "change_amount", "yoy_change", "change")
VALUE_CHANGE_PCT_ALIASES = ("change_pct", "yoy_pct")
VALUE_QUOTE_ALIASES = ("raw_quote", "source_text", "original_text", "note")
VALUE_PAGE_ALIASES = (
    "source_page", "page", "page_context", "page_number", "page_num",
    "source_line_range",
)
VALUE_SECTION_ALIASES = ("source_section", "source", "section")
# calibration_note 别名（招商用 "calib"）
VALUE_CALIB_ALIASES = ("calibration_note", "calib")

# ---------------------------------------------------------------------------
# 配置字典加载
# ---------------------------------------------------------------------------

def load_metrics_yaml() -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    加载 skill2 本地 config/metrics.yaml，构建：
    - name2bucket: 所有 standard_name（含 synonyms）→ category_bucket
    - name2standard: 所有别名 → 规范 standard_name（含 F/G 的 "(文字)" 后缀）
    """
    path = get_skill_config_file("skill2", "metrics.yaml")
    if not path.exists():
        print(f"⚠️  {path} 不存在，normalize 只能用关键词兜底推断", file=sys.stderr)
        return {}, {}
    doc = yaml.safe_load(path.read_text())
    # text_metrics 列表在顶层
    text_metrics = doc.get("text_metrics", []) if isinstance(doc, dict) else []
    name2bucket: Dict[str, str] = {}
    name2standard: Dict[str, str] = {}
    for m in text_metrics:
        std_name = m.get("standard_name", "")
        bucket = m.get("category", "其他")
        if not std_name:
            continue
        # standard_name 本身映射到自己
        name2standard[std_name] = std_name
        name2bucket[std_name] = bucket
        # 去掉 "(文字)" 后缀后也建一份（用于旧数据匹配）
        stripped = std_name.replace("(文字)", "").replace("（文字）", "")
        if stripped != std_name:
            name2standard[stripped] = std_name
            name2bucket[stripped] = bucket
        # synonyms
        for syn in (m.get("synonyms") or []):
            name2standard.setdefault(syn, std_name)
            name2bucket.setdefault(syn, bucket)
    return name2bucket, name2standard


# ---------------------------------------------------------------------------
# 核心 normalize 逻辑
# ---------------------------------------------------------------------------

def _pick(src: Dict[str, Any], aliases: Tuple[str, ...]) -> Any:
    """按顺序从 src 中取第一个非 None 的字段。"""
    for k in aliases:
        v = src.get(k)
        if v is not None and v != "":
            return v
    return None


def _infer_bucket_by_keyword(std_name: str) -> str:
    """按关键词兜底推断 bucket。"""
    if not std_name:
        return "其他"
    for bucket, kws in BUCKET_KEYWORDS:
        if any(kw in std_name for kw in kws):
            return bucket
    return "其他"


def _should_add_wenzi_suffix(bucket: str, name: str) -> bool:
    """F (分部效益) 和 G (量价) bucket 的 standard_name 需要带 (文字) 后缀。"""
    if bucket not in ("分部效益", "量价"):
        return False
    return "(文字)" not in name and "（文字）" not in name


_VALUE_UNIT_RE = re.compile(r"^\s*([\-\d,]+(?:\.\d+)?)\s*(.*?)\s*$")


def _parse_value_string(raw: Any) -> Tuple[Optional[float], Optional[str]]:
    """
    把招商风格的字符串 '170,825.19亿元' 拆成 (数值, 单位)。
    支持 '14.44%' / '1,234' / '123亿元' 等格式。
    """
    if raw is None:
        return None, None
    if isinstance(raw, (int, float)):
        return float(raw), None
    if not isinstance(raw, str):
        return None, None
    s = raw.strip()
    if not s:
        return None, None
    m = _VALUE_UNIT_RE.match(s)
    if not m:
        return None, None
    num_part = m.group(1).replace(",", "")
    unit = m.group(2).strip() or None
    try:
        return float(num_part), unit
    except ValueError:
        return None, unit


def _parse_change_string(raw: Any) -> Tuple[Optional[float], Optional[float]]:
    """把招商的 change 字段（如 '14.44%' 或 '123亿元'）拆成 (change_value, change_pct)。"""
    if raw is None:
        return None, None
    if isinstance(raw, (int, float)):
        return float(raw), None
    if not isinstance(raw, str):
        return None, None
    s = raw.strip()
    num, unit = _parse_value_string(s)
    if num is None:
        return None, None
    if unit == "%":
        return None, num
    return num, None


def normalize_metric(
    raw: Dict[str, Any],
    period_label: str,
    name2bucket: Dict[str, str],
    name2standard: Dict[str, str],
) -> Optional[Dict[str, Any]]:
    """把任意形态的旧 metric 转成规范 schema。返回 None 表示无法识别（将 warning）。"""

    # 1) standard_name
    raw_name = _pick(raw, METRIC_NAME_ALIASES)
    if not raw_name:
        return None
    raw_name = str(raw_name).strip()
    # 映射到规范名（含 (文字) 后缀）
    standard_name = name2standard.get(raw_name, raw_name)

    # 2) category_bucket
    raw_bucket = _pick(raw, METRIC_CATEGORY_ALIASES)
    bucket: Optional[str] = None
    if isinstance(raw_bucket, str):
        raw_bucket_s = raw_bucket.strip()
        if raw_bucket_s in VALID_BUCKETS:
            bucket = raw_bucket_s
        elif raw_bucket_s in LEGACY_CATEGORY_LETTER_MAP:
            bucket = LEGACY_CATEGORY_LETTER_MAP[raw_bucket_s]
    if bucket is None:
        # 优先用 metrics.yaml 字典，失败则关键词兜底
        bucket = (
            name2bucket.get(standard_name)
            or name2bucket.get(raw_name)
            or _infer_bucket_by_keyword(standard_name)
        )
    if bucket not in VALID_BUCKETS:
        bucket = "其他"

    # 3) 补齐 F/G bucket 的 (文字) 后缀
    if _should_add_wenzi_suffix(bucket, standard_name):
        standard_name = f"{standard_name}(文字)"

    # 4) 如果 raw 已经是规范 values[] 结构，直接透传（幂等）
    if isinstance(raw.get("values"), list) and raw.get("values"):
        normed_values = [_normalize_value_item(v, period_label) for v in raw["values"]]
        normed_values = [v for v in normed_values if v]
    else:
        # 5) 旧扁平结构：包装进 values[]
        value_item = _normalize_value_item(raw, period_label, flat_source=True)
        normed_values = [value_item] if value_item else []

    return {
        "standard_name": standard_name,
        "category_bucket": bucket,
        "values": normed_values,
    }


def _normalize_value_item(
    src: Dict[str, Any],
    period_label: str,
    *,
    flat_source: bool = False,
) -> Optional[Dict[str, Any]]:
    """把一条 value dict（或旧的扁平 metric）转成规范 values[i] 结构。"""
    if not isinstance(src, dict):
        return None

    # period_end_value + unit
    raw_val = _pick(src, VALUE_NUMBER_ALIASES)
    raw_unit = _pick(src, VALUE_UNIT_ALIASES)
    period_end_value: Optional[float] = None
    unit: Optional[str] = raw_unit if isinstance(raw_unit, str) else None

    if isinstance(raw_val, (int, float)):
        period_end_value = float(raw_val)
    elif isinstance(raw_val, str):
        period_end_value, inferred_unit = _parse_value_string(raw_val)
        if unit is None and inferred_unit:
            unit = inferred_unit

    # change_value + change_pct
    raw_change = _pick(src, VALUE_CHANGE_ALIASES)
    raw_change_pct = _pick(src, VALUE_CHANGE_PCT_ALIASES)
    change_value: Optional[float] = None
    change_pct: Optional[float] = None

    if isinstance(raw_change, (int, float)):
        change_value = float(raw_change)
    elif isinstance(raw_change, str):
        cv, cp = _parse_change_string(raw_change)
        change_value = cv
        if cp is not None and raw_change_pct is None:
            change_pct = cp

    if change_pct is None and isinstance(raw_change_pct, (int, float)):
        change_pct = float(raw_change_pct)
    elif change_pct is None and isinstance(raw_change_pct, str):
        _, cp = _parse_change_string(raw_change_pct)
        change_pct = cp

    # 如果值和变动都没有，且又是扁平源，那这条 metric 可能是彻底空的（跳过）
    if flat_source and period_end_value is None and change_value is None and change_pct is None:
        return None

    # raw_quote / source_section / source_page / candidate_id / calibration_note / confidence
    raw_quote = _pick(src, VALUE_QUOTE_ALIASES)
    source_section = _pick(src, VALUE_SECTION_ALIASES)
    source_page = _pick(src, VALUE_PAGE_ALIASES)
    candidate_id = src.get("candidate_id")
    calibration_note = _pick(src, VALUE_CALIB_ALIASES)
    confidence = src.get("confidence", "medium" if period_end_value is not None else "low")

    out: Dict[str, Any] = {
        "period_label": src.get("period_label") or period_label,
        "period_end_value": period_end_value,
        "change_value": change_value,
        "change_pct": change_pct,
        "unit": unit,
        "raw_quote": raw_quote,
        "source_section": source_section,
        "source_page": source_page,
        "candidate_id": candidate_id,
        "calibration_note": calibration_note,
        "confidence": confidence,
    }
    return out


def flatten_nested_by_period(pdata: Dict[str, Any], period: str) -> Dict[str, Any]:
    """
    光大/民生 2025 的结构异常修复：
    pdata 本身被当成了 Skill 2 输出的顶层文件，内部又嵌了一层 by_period[period]。
    展开成扁平的 period-level dict。
    """
    if not isinstance(pdata, dict) or "by_period" not in pdata:
        return pdata
    inner = pdata.get("by_period", {})
    if not isinstance(inner, dict):
        return pdata
    # 优先匹配同名 period，否则取第一个
    if period in inner and isinstance(inner[period], dict):
        return inner[period]
    for k, v in inner.items():
        if isinstance(v, dict):
            return v
    return pdata


def normalize_period_data(
    pdata: Dict[str, Any],
    period: str,
    name2bucket: Dict[str, str],
    name2standard: Dict[str, str],
) -> Tuple[Dict[str, Any], List[str]]:
    """把一个 period 的数据 normalize，返回 (新 pdata, warning 列表)。"""
    warnings: List[str] = []
    pdata = flatten_nested_by_period(pdata, period)

    raw_metrics = pdata.get("metrics", []) if isinstance(pdata, dict) else []
    normed: List[Dict[str, Any]] = []
    for idx, m in enumerate(raw_metrics):
        if not isinstance(m, dict):
            warnings.append(f"period={period} metric#{idx} 非 dict，已丢弃")
            continue
        nm = normalize_metric(m, period, name2bucket, name2standard)
        if nm is None:
            warnings.append(
                f"period={period} metric#{idx} 无法识别 standard_name，原始字段: {list(m.keys())}"
            )
            continue
        normed.append(nm)

    return {
        "period": period,
        "metrics": normed,
        "alerts": pdata.get("alerts", []) or [],
        "notes": pdata.get("notes", []) or [],
        "warnings": (pdata.get("warnings", []) or []) + warnings,
    }, warnings


def normalize_bank_json(
    src: Dict[str, Any],
    name2bucket: Dict[str, str],
    name2standard: Dict[str, str],
) -> Tuple[Dict[str, Any], List[str]]:
    """normalize 单家银行的 JSON。"""
    all_warnings: List[str] = []
    by_period_in = src.get("by_period", {}) or {}
    by_period_out: Dict[str, Any] = {}
    for period, pdata in by_period_in.items():
        new_pdata, w = normalize_period_data(pdata, period, name2bucket, name2standard)
        by_period_out[period] = new_pdata
        all_warnings.extend(w)

    out = {
        "bank": src.get("bank", ""),
        "bank_key": src.get("bank_key", ""),
        "kind": "text",
        "_schema_version": SCHEMA_VERSION,
        "periods": sorted(by_period_out.keys()),
        "by_period": by_period_out,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    return out, all_warnings


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def report_diff(src: Dict[str, Any], dst: Dict[str, Any]) -> Dict[str, Any]:
    """汇总一家银行的转换前后差异统计。"""
    def count_metrics(data: Dict[str, Any]) -> Tuple[int, Dict[str, int]]:
        total = 0
        by_bucket: Dict[str, int] = {}
        for _, pd in (data.get("by_period", {}) or {}).items():
            if not isinstance(pd, dict):
                continue
            # src 可能嵌套了一层 by_period，就再展开
            if "by_period" in pd and isinstance(pd["by_period"], dict):
                inner_all = []
                for _, ip in pd["by_period"].items():
                    if isinstance(ip, dict):
                        inner_all.extend(ip.get("metrics", []) or [])
                metrics = inner_all
            else:
                metrics = pd.get("metrics", []) or []
            for m in metrics:
                if not isinstance(m, dict):
                    continue
                total += 1
                bucket = m.get("category_bucket") or m.get("category") or "<missing>"
                by_bucket[bucket] = by_bucket.get(bucket, 0) + 1
        return total, by_bucket

    s_total, s_buckets = count_metrics(src)
    d_total, d_buckets = count_metrics(dst)
    return {
        "periods_src": len(src.get("by_period", {})),
        "periods_dst": len(dst.get("by_period", {})),
        "metrics_src": s_total,
        "metrics_dst": d_total,
        "buckets_src": s_buckets,
        "buckets_dst": d_buckets,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只打印差异报告，不改文件")
    ap.add_argument("--dry-run", action="store_true", help="运行 normalize 但不写回，打印汇总")
    ap.add_argument("--apply", action="store_true", help="备份后原地写回")
    ap.add_argument("--bank", nargs="*", default=None, help="只处理指定银行（中信/招商/...）")
    ap.add_argument("--text-dir", default=str(TEXT_DIR), help="覆盖 text 目录（默认 $RA/data/text）")
    args = ap.parse_args()

    if not (args.check or args.dry_run or args.apply):
        ap.error("必须指定 --check / --dry-run / --apply 之一")

    text_dir = Path(args.text_dir).expanduser().resolve()
    if not text_dir.is_dir():
        print(f"❌ 目录不存在：{text_dir}", file=sys.stderr)
        return 2

    targets = args.bank or BANKS

    name2bucket, name2standard = load_metrics_yaml()
    print(f"📚 字典加载：{len(name2standard)} 个 standard_name 别名，覆盖 {len(set(name2bucket.values()))} 个 bucket")

    overall_warnings: List[str] = []
    for bank in targets:
        f = text_dir / f"{bank}.json"
        if not f.exists():
            print(f"⚠️  跳过 {bank}：文件不存在 {f}")
            continue
        src = json.loads(f.read_text())

        if src.get("_schema_version") == SCHEMA_VERSION and not args.apply:
            print(f"ℹ️  {bank} 已是 {SCHEMA_VERSION}，跳过")
            continue

        dst, warnings = normalize_bank_json(src, name2bucket, name2standard)
        diff = report_diff(src, dst)

        print(f"\n=== {bank} ===")
        print(f"  periods: {diff['periods_src']} → {diff['periods_dst']}")
        print(f"  metrics: {diff['metrics_src']} → {diff['metrics_dst']}")
        print(f"  buckets src: {diff['buckets_src']}")
        print(f"  buckets dst: {diff['buckets_dst']}")
        if warnings:
            print(f"  ⚠️  {len(warnings)} warnings, top 3:")
            for w in warnings[:3]:
                print(f"     - {w}")
        overall_warnings.extend(warnings)

        if args.apply:
            backup = f.with_suffix(f.suffix + f".bak.{datetime.now():%Y%m%d-%H%M%S}")
            shutil.copy2(f, backup)
            f.write_text(json.dumps(dst, ensure_ascii=False, indent=2))
            print(f"  ✅ 已写回 {f}（备份 {backup.name}）")

    print(f"\n合计 warnings：{len(overall_warnings)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
