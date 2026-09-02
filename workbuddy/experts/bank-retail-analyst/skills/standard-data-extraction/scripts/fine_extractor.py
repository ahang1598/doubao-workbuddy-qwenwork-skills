#!/usr/bin/env python3
"""
精筛辅助工具：为 LLM 子代理构造 input_bundle，并对子代理回写结果做校验。

与 LLM 解耦的设计原则：
  - 本脚本**不直接调用任何 LLM API**
  - 只负责把粗筛输出 + metrics schema 拼装成子代理可用的 JSON 包
  - 真正的 LLM 调用由主 Agent 的 `task` 工具（Codebuddy 内置子代理）完成
  - 子代理返回的结构化 JSON，由本脚本提供 validate() 做事后校验

典型使用流程：
  1) 运行 coarse_filter.py 得到 coarse_<bank>_<period>.json
  2) fine_extractor.py build-bundles
       -> 产出 bundles/<category>.json 清单
  3) 主 Agent 对每个 bundle 启动子代理（task 工具），子代理读取 fine_extractor_prompt.md
       + bundle JSON 后输出 extraction_<category>.json
  4) fine_extractor.py validate 对所有 extraction_* 做单位/量程/加总校验
  5) 编排器合并为 partial_<bank>_<period>.json
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any, Dict, List, Optional, Tuple

import yaml

# ---------------------------------------------------------------------------
# 共享路径约定：默认从 $RETAIL_ANALYSIS_HOME（默认 ~/RetailAnalysis）读取配置
# ---------------------------------------------------------------------------
# paths.py 已同步为本 Skill scripts/ 下的副本（由 release.py 保证一致），
# import 策略：同目录优先 -> 仓库根兜底
try:  # pragma: no cover
    _SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
    if str(_SCRIPT_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPT_DIR))
    try:
        import paths as _PATHS  # type: ignore
    except ImportError:
        _repo_scripts = _SCRIPT_DIR.parent.parent.parent / "scripts"
        if _repo_scripts.is_dir() and str(_repo_scripts) not in sys.path:
            sys.path.insert(0, str(_repo_scripts))
        import paths as _PATHS  # type: ignore
except Exception:  # noqa: BLE001
    _PATHS = None  # type: ignore


def _resolve_cli_metrics_yaml(explicit_path: Optional[str]) -> pathlib.Path:
    if _PATHS is not None:
        return _PATHS.resolve_config_file(
            "skill1", "metrics.yaml", explicit_path=explicit_path,
        )[0]
    path = pathlib.Path(explicit_path or _SCRIPT_DIR.parent / "config" / "metrics.yaml").expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"配置文件不存在：{path}")
    return path


SKILL1_METRIC_GROUPS = [
    "segment_report_metrics",
    "retail_deposit_metrics",
    "retail_loan_metrics",
    "retail_asset_quality_metrics",
    "bank_wide_metrics",
]

# metric group -> category_bucket 映射（用于和粗筛的 table_candidates_by_category 对齐）
GROUP_TO_BUCKET: Dict[str, str] = {
    "segment_report_metrics": "分部报告",
    "retail_deposit_metrics": "零售存款",
    "retail_loan_metrics": "零售贷款",
    "retail_asset_quality_metrics": "资产质量",
    "bank_wide_metrics": "收费指标",   # bank_wide 在粗筛里会被拆分为多个 bucket
}

# 分部报告允许主标签
_BUCKETS = [
    "分部报告", "零售存款", "零售贷款", "资产质量",
    "收费指标", "风控指标", "五级分类", "全行规模",
]


# ---------------------------------------------------------------------------
# 读取
# ---------------------------------------------------------------------------

def _load_metrics(metrics_yaml: pathlib.Path) -> Dict[str, List[Dict[str, Any]]]:
    data = yaml.safe_load(metrics_yaml.read_text(encoding="utf-8"))
    out: Dict[str, List[Dict[str, Any]]] = {}
    for group in SKILL1_METRIC_GROUPS:
        out[group] = [it for it in (data.get(group) or []) if it.get("scope", "表格") == "表格"]
    return out


def _metrics_for_bucket(
    all_metrics: Dict[str, List[Dict[str, Any]]], bucket: str,
) -> List[Dict[str, Any]]:
    """根据 bucket 取出应该由该批子代理处理的目标指标子集。"""
    picked: List[Dict[str, Any]] = []
    for group, lst in all_metrics.items():
        for m in lst:
            cat = (m.get("category") or "").split("-")[0]
            if cat == bucket:
                picked.append({
                    "standard_name": m["standard_name"],
                    "unit": m.get("unit", ""),
                    "synonyms": m.get("synonyms", []) or [],
                    "valid_range": m.get("valid_range", {}),
                    "category": m.get("category", ""),
                    "calibration_note": m.get("calibration_note", ""),
                })
    return picked


# ---------------------------------------------------------------------------
# build-bundles
# ---------------------------------------------------------------------------

def build_bundles(
    coarse_json: pathlib.Path,
    metrics_yaml: pathlib.Path,
    bank: str,
    period: str,
    output_dir: pathlib.Path,
    max_candidates_per_bucket: int = 6,
) -> List[pathlib.Path]:
    """
    为每个 category_bucket 产出一个 bundle JSON：
      {
        "bank": ..., "period": ..., "category_bucket": ...,
        "target_metrics": [...],
        "candidates": [...]   // 已裁剪 top-N
      }
    """
    coarse = json.loads(coarse_json.read_text(encoding="utf-8"))
    grouped = coarse.get("table_candidates_by_category", {}) or {}

    # 若粗筛没有对应 bucket，也要为该 bucket 生成 bundle（candidates=[]），
    # 以便子代理显式返回"未找到"，而不是漏提取。
    all_metrics = _load_metrics(metrics_yaml)

    output_dir.mkdir(parents=True, exist_ok=True)
    produced: List[pathlib.Path] = []

    # bank_wide_metrics 的 category 会是 "收费指标" / "风控指标" / "五级分类"，
    # 我们直接遍历 _BUCKETS，保证覆盖所有精筛批次
    for bucket in _BUCKETS:
        targets = _metrics_for_bucket(all_metrics, bucket)
        if not targets:
            continue
        cands = grouped.get(bucket, []) or []

        # 不能简单截断全局 top-N：高分综合表会挤掉只覆盖一个稀有指标的表。
        # 先按新增 target metric 覆盖做贪心选择，再用原始得分顺序补足名额。
        target_names = {m["standard_name"] for m in targets}
        selected: List[Dict[str, Any]] = []
        selected_keys = set()
        covered = set()
        for c in cands:
            hits = set(c.get("hit_metrics", [])) & target_names
            if hits - covered:
                key = (c.get("start_line"), c.get("end_line"))
                if key not in selected_keys:
                    selected.append(c)
                    selected_keys.add(key)
                    covered.update(hits)
            if len(selected) >= max_candidates_per_bucket:
                break
        if len(selected) < max_candidates_per_bucket:
            for c in cands:
                key = (c.get("start_line"), c.get("end_line"))
                if key in selected_keys:
                    continue
                selected.append(c)
                selected_keys.add(key)
                if len(selected) >= max_candidates_per_bucket:
                    break
        cands = selected

        # 只保留子代理必需的 candidate 字段，减少 prompt 体积
        trimmed = []
        for i, c in enumerate(cands, start=1):
            trimmed.append({
                "candidate_id": f"t{i:02d}",
                "heading_chain": c.get("heading_chain", []),
                "table_start_line": c.get("start_line"),
                "table_end_line": c.get("end_line"),
                "context_start_line": c.get("context_start_line"),
                "context_end_line": c.get("context_end_line"),
                "hit_metrics": c.get("hit_metrics", []),
                "hit_keywords": c.get("hit_keywords", []),
                "score": c.get("score", 0),
                # context_markdown 优先给 LLM，若太长可让主 Agent 进一步切片
                "context_markdown": c.get("context_markdown", ""),
            })

        bundle = {
            "bank": bank,
            "period": period,
            "category_bucket": bucket,
            "target_metrics": targets,
            "candidates": trimmed,
        }
        safe_bucket = bucket.replace("/", "_")
        out_path = output_dir / f"bundle_{safe_bucket}.json"
        out_path.write_text(
            json.dumps(bundle, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        produced.append(out_path)

    # ------------------------------------------------------------------
    # 跨 bundle 交叉引用：利润表字段兜底（泛化，所有银行通用）
    # ------------------------------------------------------------------
    # 如果分部报告 bundle 的 candidates 为空或只命中了少量表格，
    # 尝试从风控指标/收费指标 bundle 中找利润表 candidate（包含全行
    # 利息净收入/手续费/信用减值损失/业务费用/税前利润），补充进分部报告 bundle。
    # 这解决了"某银行能跨 bundle 取值但其他银行不行"的问题。
    _cross_bundle_enrich(output_dir)

    return produced


# 全行利润表字段（需要跨 bundle 兜底的指标）
_INCOME_STMT_FIELDS = {
    "全行信用减值损失", "全行利息净收入", "全行手续费及佣金净收入",
    "全行业务费用", "全行税前利润", "全行营业净收入",
}

# 利润表章节关键词（用于识别 candidate 是否来自利润表）
_INCOME_STMT_KEYWORDS = {
    "利润表", "损益", "营业收入", "利息净收入",
    "信用减值损失", "信用及其他资产减值损失",
}

# P4 新增：按产品分类的零售贷款表特征关键词
# 这类表典型特征：同一张表同时含"信用卡/住房贷款/经营贷/消费贷"等产品行
# 兼具贷款余额 + 不良贷款额 + 不良率三列 → 同时对 retail_loan 和 asset_quality 两个 bucket 都有价值
_RETAIL_LOAN_BREAKDOWN_KEYWORDS = {
    "信用卡及透支", "信用卡透支", "信用卡应收",
    "个人按揭", "个人住房及商用房", "住房贷款",
    "个人经营贷款", "经营性贷款", "小微贷款",
    "消费贷款及其他", "个人消费贷款",
}

# P4 新增：零售存款细分表特征关键词（典型：客户存款利息支出表含零售活期/定期）
_RETAIL_DEPOSIT_BREAKDOWN_KEYWORDS = {
    "零售客户存款", "零售客户定期", "零售客户活期",
    "个人活期", "个人定期", "储蓄活期", "储蓄定期",
}


def _cross_bundle_enrich(bundle_dir: pathlib.Path) -> None:
    """
    跨 bundle 交叉引用（多策略）：
      策略 A：分部报告 bundle ← 风控/收费 bundle 的利润表 candidate
      策略 B：零售贷款 ↔ 资产质量 双向共享「按产品类型的零售贷款表」
      策略 C：零售存款 ← 风控/收费 bundle 的客户存款利息支出表
    """
    # ---------- 策略 A：分部报告 ← 利润表 ----------
    _enrich_from_income_statement(bundle_dir)
    # ---------- 策略 B：零售贷款 ↔ 资产质量（产品分类表）----------
    _enrich_retail_loan_breakdown(bundle_dir)
    # ---------- 策略 C：零售存款 ← 利息支出章 ----------
    _enrich_retail_deposit_from_interest_table(bundle_dir)


def _enrich_from_income_statement(bundle_dir: pathlib.Path) -> None:
    """原策略 A：从风控/收费 bundle 补分部报告 bundle 的利润表 candidate。"""
    seg_path = bundle_dir / "bundle_分部报告.json"
    if not seg_path.exists():
        return

    seg = json.loads(seg_path.read_text(encoding="utf-8"))
    seg_candidates = seg.get("candidates", [])

    # 检查分部报告 bundle 中是否已有足够的全行字段 candidate
    seg_ctx_text = " ".join(c.get("context_markdown", "") for c in seg_candidates)
    has_income_stmt = any(kw in seg_ctx_text for kw in _INCOME_STMT_KEYWORDS)

    if has_income_stmt and len(seg_candidates) >= 2:
        return  # 已有利润表内容，无需补充

    # 从风控指标和收费指标 bundle 中收集利润表 candidate
    donor_bundles = ["bundle_风控指标.json", "bundle_收费指标.json"]
    extra_candidates = []

    for donor_name in donor_bundles:
        donor_path = bundle_dir / donor_name
        if not donor_path.exists():
            continue
        donor = json.loads(donor_path.read_text(encoding="utf-8"))
        for c in donor.get("candidates", []):
            ctx = c.get("context_markdown", "")
            # 只取包含利润表关键词的 candidate
            if any(kw in ctx for kw in _INCOME_STMT_KEYWORDS):
                # 重新标记 candidate_id 避免冲突
                new_c = dict(c)
                new_c["candidate_id"] = f"xref-{donor_name.replace('.json', '')}-{c.get('candidate_id', 'x')}"
                new_c["cross_bundle_source"] = donor_name
                extra_candidates.append(new_c)

    if not extra_candidates:
        return

    # 把利润表 candidate 追加到分部报告 bundle
    seg["candidates"].extend(extra_candidates)
    # 在 notes 中记录交叉引用来源
    notes = seg.setdefault("notes", [])
    notes.append(
        f"跨 bundle 交叉引用：从 {', '.join(donor_bundles)} 中补充了 "
        f"{len(extra_candidates)} 个利润表 candidate，用于全行口径字段兜底"
    )

    seg_path.write_text(
        json.dumps(seg, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        f"[cross-bundle] 分部报告 bundle 追加了 {len(extra_candidates)} 个利润表 candidate "
        f"（来源：{', '.join(donor_bundles)}）",
        flush=True,
    )


def _enrich_retail_loan_breakdown(bundle_dir: pathlib.Path) -> None:
    """
    P4 策略 B：零售贷款 ↔ 资产质量 双向 cross-bundle。

    典型表：按产品类型划分的个人贷款结构表（如某银行A 3.10.2 / 某银行B 3.5.4.6 / 某银行C (二)）
    此表同时含：
      - 产品级贷款余额 （零售贷款 bucket 需要）
      - 产品级不良贷款额/率（资产质量 bucket 需要）

    如果某个 bundle 中没有这类表但另一个 bundle 有，则互相补充。
    """
    loan_path = bundle_dir / "bundle_零售贷款.json"
    quality_path = bundle_dir / "bundle_资产质量.json"
    if not loan_path.exists() or not quality_path.exists():
        return

    loan = json.loads(loan_path.read_text(encoding="utf-8"))
    quality = json.loads(quality_path.read_text(encoding="utf-8"))

    def _is_breakdown_table(c: Dict) -> bool:
        """判断 candidate 是否为按产品类型划分的零售贷款表。"""
        ctx = c.get("context_markdown", "")
        hits = sum(1 for kw in _RETAIL_LOAN_BREAKDOWN_KEYWORDS if kw in ctx)
        # 至少含 2 个产品关键词，且有"不良"字样（表明是产品级细分表）
        return hits >= 2 and "不良" in ctx

    def _find_breakdown_in(bundle: Dict) -> List[Dict]:
        return [c for c in bundle.get("candidates", []) if _is_breakdown_table(c)]

    loan_has = _find_breakdown_in(loan)
    quality_has = _find_breakdown_in(quality)

    synced = 0
    # 零售贷款 ← 资产质量
    if not loan_has and quality_has:
        existing_ids = {c.get("candidate_id") for c in loan.get("candidates", [])}
        for c in quality_has:
            new_c = dict(c)
            new_c["candidate_id"] = f"xref-bundle_资产质量-{c.get('candidate_id', 'x')}"
            new_c["cross_bundle_source"] = "bundle_资产质量.json"
            if new_c["candidate_id"] in existing_ids:
                continue
            loan.setdefault("candidates", []).append(new_c)
            synced += 1
        if synced > 0:
            loan.setdefault("notes", []).append(
                f"P4 cross-bundle：从 bundle_资产质量.json 补入 {synced} 个按产品分类的零售贷款表"
            )
            loan_path.write_text(json.dumps(loan, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[cross-bundle-P4] 零售贷款 ← 资产质量：{synced} 个 candidate", flush=True)

    # 资产质量 ← 零售贷款
    synced2 = 0
    if not quality_has and loan_has:
        existing_ids = {c.get("candidate_id") for c in quality.get("candidates", [])}
        for c in loan_has:
            new_c = dict(c)
            new_c["candidate_id"] = f"xref-bundle_零售贷款-{c.get('candidate_id', 'x')}"
            new_c["cross_bundle_source"] = "bundle_零售贷款.json"
            if new_c["candidate_id"] in existing_ids:
                continue
            quality.setdefault("candidates", []).append(new_c)
            synced2 += 1
        if synced2 > 0:
            quality.setdefault("notes", []).append(
                f"P4 cross-bundle：从 bundle_零售贷款.json 补入 {synced2} 个按产品分类的不良贷款表"
            )
            quality_path.write_text(json.dumps(quality, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[cross-bundle-P4] 资产质量 ← 零售贷款：{synced2} 个 candidate", flush=True)


def _enrich_retail_deposit_from_interest_table(bundle_dir: pathlib.Path) -> None:
    """
    P4 策略 C：零售存款 ← 风控/收费/分部报告 bundle 的"客户存款利息支出表"。

    典型：某银行等在"利息支出 → 客户存款利息支出"章节有详细的零售活期/定期拆分表，
    但粗筛可能把它归入了 provision 或 fee_commission group。
    """
    dep_path = bundle_dir / "bundle_零售存款.json"
    if not dep_path.exists():
        return

    dep = json.loads(dep_path.read_text(encoding="utf-8"))
    # 已有 candidate 且含零售细分，跳过
    existing_ctx = " ".join(c.get("context_markdown", "") for c in dep.get("candidates", []))
    if any(kw in existing_ctx for kw in _RETAIL_DEPOSIT_BREAKDOWN_KEYWORDS) and dep.get("candidates"):
        return

    donor_bundles = ["bundle_风控指标.json", "bundle_收费指标.json", "bundle_分部报告.json"]
    extra: List[Dict] = []
    for donor_name in donor_bundles:
        p = bundle_dir / donor_name
        if not p.exists(): continue
        donor = json.loads(p.read_text(encoding="utf-8"))
        for c in donor.get("candidates", []):
            ctx = c.get("context_markdown", "")
            hits = sum(1 for kw in _RETAIL_DEPOSIT_BREAKDOWN_KEYWORDS if kw in ctx)
            if hits >= 2:  # 至少含 2 个零售存款关键词
                new_c = dict(c)
                new_c["candidate_id"] = f"xref-{donor_name.replace('.json', '')}-{c.get('candidate_id', 'x')}"
                new_c["cross_bundle_source"] = donor_name
                extra.append(new_c)

    if not extra:
        return
    dep.setdefault("candidates", []).extend(extra)
    dep.setdefault("notes", []).append(
        f"P4 cross-bundle：从 {', '.join(donor_bundles)} 补入 {len(extra)} 个含零售存款细分的 candidate"
    )
    dep_path.write_text(json.dumps(dep, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[cross-bundle-P4] 零售存款 ← {len(extra)} 个细分表", flush=True)


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------

def validate_extraction(
    extraction_json: pathlib.Path,
    metrics_yaml: pathlib.Path,
) -> Dict[str, Any]:
    """
    对子代理回写的 extraction JSON 做事后校验：
      - 结构必需字段
      - value 为数值
      - 落在 valid_range 内（否则降级 low + warning）
      - 单位一致
    返回补齐 warnings 的 JSON（不修改原文件，由调用方决定是否覆写）。
    """
    data = json.loads(extraction_json.read_text(encoding="utf-8"))
    all_metrics = _load_metrics(metrics_yaml)

    # 快查表
    schema_by_name: Dict[str, Dict[str, Any]] = {}
    for lst in all_metrics.values():
        for m in lst:
            schema_by_name[m["standard_name"]] = m

    warnings: List[str] = list(data.get("warnings", []) or [])

    for metric in data.get("metrics", []) or []:
        name = metric.get("standard_name")
        schema = schema_by_name.get(name)
        if not schema:
            warnings.append(f"未知指标：{name}")
            continue
        expected_unit = schema.get("unit", "")
        vr = schema.get("valid_range") or {}

        for v in metric.get("values", []) or []:
            val = v.get("value")
            if val is None:
                continue
            if not isinstance(val, (int, float)):
                warnings.append(f"{name} 的 value 非数值：{val!r}")
                v["confidence"] = "low"
                continue
            unit = v.get("unit", expected_unit)
            if unit != expected_unit:
                warnings.append(
                    f"{name} 单位不一致：返回 {unit}，期望 {expected_unit}"
                )
            lo = vr.get("min")
            hi = vr.get("max")
            if lo is not None and val < lo:
                v["confidence"] = "low"
                warnings.append(f"{name} 值 {val} 低于 valid_range.min={lo}")
            if hi is not None and val > hi:
                v["confidence"] = "low"
                warnings.append(f"{name} 值 {val} 高于 valid_range.max={hi}")

    data["warnings"] = warnings
    return data


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="精筛辅助工具：bundle 构造 + 结果校验")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build-bundles", help="基于粗筛输出构造 LLM 子代理的 input_bundle 批次")
    b.add_argument("--coarse-json", required=True)
    b.add_argument(
        "--metrics-yaml",
        default=None,
        help="显式指标字典；默认使用环境覆盖或 Skill 本地 config/metrics.yaml",
    )
    b.add_argument("--bank", required=True, help="银行简称，如 中信银行")
    b.add_argument("--period", required=True, help="报告期，如 2025年度")
    b.add_argument("--output-dir", required=True, help="bundle 输出目录")
    b.add_argument("--max-candidates-per-bucket", type=int, default=6)

    v = sub.add_parser("validate", help="校验子代理回写的 extraction JSON")
    v.add_argument("--extraction-json", required=True)
    v.add_argument(
        "--metrics-yaml",
        default=None,
        help="显式指标字典；默认使用环境覆盖或 Skill 本地 config/metrics.yaml",
    )
    v.add_argument("--inplace", action="store_true", help="将补齐 warnings 的结果写回原文件")

    return p.parse_args()


def main() -> None:
    args = build_args()
    metrics_yaml = _resolve_cli_metrics_yaml(args.metrics_yaml)
    if args.cmd == "build-bundles":
        produced = build_bundles(
            coarse_json=pathlib.Path(args.coarse_json),
            metrics_yaml=metrics_yaml,
            bank=args.bank,
            period=args.period,
            output_dir=pathlib.Path(args.output_dir),
            max_candidates_per_bucket=args.max_candidates_per_bucket,
        )
        print(f"[fine] bundles produced: {len(produced)}", flush=True)
        for p in produced:
            print(f"  - {p}", flush=True)
    elif args.cmd == "validate":
        validated = validate_extraction(
            extraction_json=pathlib.Path(args.extraction_json),
            metrics_yaml=metrics_yaml,
        )
        if args.inplace:
            pathlib.Path(args.extraction_json).write_text(
                json.dumps(validated, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        else:
            print(json.dumps(validated, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
