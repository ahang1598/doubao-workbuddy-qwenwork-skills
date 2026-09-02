#!/usr/bin/env python3
"""
Skill 2 编排脚本：prepare / merge

职责（纯 Python / 无 LLM）：
  [prepare]
    1. 加载 Markdown/文本（腾讯云 DocParse zip 或 data/extracted_text/*.md）
    2. 按章节关键词定位零售业务相关章节 + 按指标同义词定位候选段落
    3. 按 `category_bucket` 分组，为每个 bucket 构造 input_bundle
    4. 生成 fine_tasks.json（子代理任务清单，宿主无关）

  [merge]
    1. 读取所有子代理产出的 text_extraction/<bucket>.json
    2. 合并、规则 T2 停披校验
    3. 写 $RA/data/partial/text_<bank>_<period>.json

规则 T1（反推校验）、规则 T3（口径变化检索）由主 Agent 跨期执行，不在本脚本内。

用法：
  # 粗筛 + bundle + fine_tasks
  python prepare_text_extraction.py prepare \
      --bank 某某银行 --period 2025年度 \
      --source "$RA/data/extracted_text/中信/某某_2025年度_docparse.zip" \
      --work-dir "$RA/work/text_某某_2025年度" \
      --partial-output "$RA/data/partial/text_某某_2025年度.json"

  # 合并子代理产出
  python prepare_text_extraction.py merge \
      --manifest "$RA/work/text_某某_2025年度/manifest.json"
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import zipfile
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

import yaml

# ---------------------------------------------------------------------------
# 共享路径（paths.py 同目录优先，仓库根兜底）
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# 章节关键词（粗筛第一道：缩小扫描范围）
# ---------------------------------------------------------------------------

RETAIL_CHAPTER_KEYWORDS: List[str] = [
    # 主来源
    "零售银行业务", "零售金融业务", "零售业务",
    "个人银行业务", "个人金融业务",
    # 辅助来源
    "董事长致辞", "董事长报告",
    "行长致辞", "行长报告",
    "经营概述", "经营综述", "业绩综述",
    "业绩亮点", "经营亮点",
    "管理层讨论与分析",
    # 子章节
    "财富管理", "私人银行",
    "信用卡业务", "信用卡经营",
    "消费金融",
    "零售客户", "个人客户",
]

# bucket 定义：标签 -> 该 bucket 关注的指标 category 前缀
# category 字段在 metrics.yaml 的 text_metrics 中声明：AUM/客户数/财富收入/信用卡/渠道 等
# 额外增加"分部效益"和"量价"两个 bucket（F 类 / G 类），它们的 category 是分部报告-零售/零售存款/零售贷款
TEXT_BUCKETS: List[str] = [
    "AUM",        # A 类
    "客户数",      # B 类 (含 E 类代发客户数、渠道 MAU 归入"渠道"单独一个 bucket)
    "财富收入",    # C 类
    "信用卡",      # D 类
    "分部效益",    # F 类（零售营收/利润/非息/减值，从文字段补充）
    "量价",        # G 类（存款成本率/贷款收益率/不良率等，从文字段补充）
    "渠道",        # E 类 MAU 等
    "其他",        # 兜底：text_metrics 中未归类的
]

# category（metrics.yaml 的 category 字段）-> bucket 映射
CATEGORY_TO_BUCKET: Dict[str, str] = {
    "AUM": "AUM",
    "客户数": "客户数",
    "财富收入": "财富收入",
    "信用卡": "信用卡",
    "渠道": "渠道",
    # F 类：分部效益（来自 segment_report_metrics 中的 scope=文字，或 text_metrics 中类似 category）
    "分部报告-零售": "分部效益",
    "分部报告-全行": "分部效益",
    "分部效益": "分部效益",
    # G 类：量价（来自 retail_deposit_metrics / retail_loan_metrics 中的 scope=文字，
    #     或 text_metrics 中的存款成本率/贷款收益率/不良率）
    "零售存款": "量价",
    "零售贷款-合计": "量价",
    "零售贷款-信用卡": "量价",
    "零售贷款-非信用卡": "量价",
    "资产质量-合计": "量价",
    "资产质量-信用卡": "量价",
    "资产质量-非信用卡": "量价",
    "量价": "量价",
}


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------


@dataclass
class SectionCandidate:
    heading: str
    line_no: int
    page: Optional[int]
    matched_keywords: List[str]

    def asdict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ParagraphCandidate:
    candidate_id: str = ""
    heading_chain: List[str] = field(default_factory=list)
    start_line: int = 0
    end_line: int = 0
    page: Optional[int] = None
    hit_metrics: List[str] = field(default_factory=list)
    hit_keywords: List[str] = field(default_factory=list)
    score: int = 0
    context_text: str = ""

    def asdict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# 文本加载
# ---------------------------------------------------------------------------


def _load_markdown_from_source(source: pathlib.Path, unzip_dir: pathlib.Path) -> pathlib.Path:
    """
    source 可以是：
      - *.zip（腾讯云 DocParse 结果）：解压后取最大 .md
      - *.md：直接使用
      - 目录：取目录下最大 .md
      - *.txt / *.json（extracted_text 兼容）：也一并支持
    """
    source = source.expanduser().resolve()
    if source.is_file():
        if source.suffix.lower() == ".zip":
            unzip_dir.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(source) as zf:
                zf.extractall(unzip_dir)
            candidates = sorted(
                list(unzip_dir.rglob("*.md")) + list(unzip_dir.rglob("*.txt")),
                key=lambda p: p.stat().st_size,
                reverse=True,
            )
            if not candidates:
                raise RuntimeError(f"zip 中未找到 .md/.txt：{source}")
            return candidates[0]
        if source.suffix.lower() in {".md", ".txt"}:
            return source
        if source.suffix.lower() == ".json":
            return source  # 不推荐但兼容
        raise RuntimeError(f"未识别的 source 类型：{source}")

    if source.is_dir():
        candidates = sorted(
            list(source.rglob("*.md")) + list(source.rglob("*.txt")),
            key=lambda p: p.stat().st_size,
            reverse=True,
        )
        if not candidates:
            raise RuntimeError(f"目录下未找到 .md/.txt：{source}")
        return candidates[0]

    raise RuntimeError(f"source 不存在：{source}")


def _load_text_content(path: pathlib.Path) -> str:
    if path.suffix.lower() == ".json":
        obj = json.loads(path.read_text(encoding="utf-8"))
        # 兼容常见 extracted_text JSON 结构
        if isinstance(obj, dict):
            for k in ("text", "content", "markdown"):
                v = obj.get(k)
                if isinstance(v, str) and v:
                    return v
        return json.dumps(obj, ensure_ascii=False, indent=2)
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# metrics.yaml 加载
# ---------------------------------------------------------------------------


def _load_text_metrics(metrics_yaml: pathlib.Path) -> List[Dict[str, Any]]:
    """
    加载 text_metrics 以及 segment_report_metrics / retail_deposit_metrics
    / retail_loan_metrics / retail_asset_quality_metrics 中 scope=文字 的指标。

    输出：统一展平为一个列表，每个元素 {standard_name, unit, synonyms,
    description, extract_fields, valid_range, calibration_note, category, source_group}
    """
    data = yaml.safe_load(metrics_yaml.read_text(encoding="utf-8")) or {}

    picked: List[Dict[str, Any]] = []

    # 1. text_metrics 主体
    for m in data.get("text_metrics") or []:
        picked.append({
            "standard_name": m["standard_name"],
            "unit": m.get("unit", ""),
            "synonyms": list(m.get("synonyms", []) or []),
            "description": m.get("description", ""),
            "extract_fields": m.get("extract_fields", ["value"]),
            "valid_range": m.get("valid_range", {}),
            "calibration_note": m.get("calibration_note", ""),
            "category": m.get("category", "其他"),
            "source_group": "text_metrics",
        })

    # 2. 其他 group 中 scope=文字 的条目（F 类 / G 类补充）
    for group in (
        "segment_report_metrics",
        "retail_deposit_metrics",
        "retail_loan_metrics",
        "retail_asset_quality_metrics",
        "bank_wide_metrics",
    ):
        for m in data.get(group) or []:
            if m.get("scope") == "文字":
                picked.append({
                    "standard_name": m["standard_name"],
                    "unit": m.get("unit", ""),
                    "synonyms": list(m.get("synonyms", []) or []),
                    "description": m.get("description", ""),
                    "extract_fields": m.get(
                        "extract_fields",
                        ["value", "yoy_change", "yoy_pct"],
                    ),
                    "valid_range": m.get("valid_range", {}),
                    "calibration_note": m.get("calibration_note", ""),
                    "category": m.get("category", group),
                    "source_group": group,
                })

    # 去重（同名）
    seen: Set[str] = set()
    unique: List[Dict[str, Any]] = []
    for m in picked:
        if m["standard_name"] in seen:
            continue
        seen.add(m["standard_name"])
        unique.append(m)
    return unique


def _bucket_of(metric: Dict[str, Any]) -> str:
    cat = metric.get("category", "其他")
    # 精确命中
    if cat in CATEGORY_TO_BUCKET:
        return CATEGORY_TO_BUCKET[cat]
    # 前缀命中（兼容"分部报告-零售-xxx"之类多级 category）
    for prefix, bucket in CATEGORY_TO_BUCKET.items():
        if cat.startswith(prefix + "-") or cat.startswith(prefix):
            return bucket
    return "其他"


# ---------------------------------------------------------------------------
# 粗筛：章节 + 段落
# ---------------------------------------------------------------------------

# Markdown 标题行识别（# / ## / ### ...）
_HEADING_RE = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*$")
# 行内页码标记（腾讯云 DocParse 常见：<PAGE:45> 或 "——第45页——"）
_PAGE_HINT_RE = re.compile(
    r"(?:<PAGE:(\d+)>|<page[_\s]*no[=:]?\s*(\d+)\s*/?>|第\s*(\d+)\s*页|——\s*(\d+)\s*——)",
    re.IGNORECASE,
)


def _find_page_for_line(lines: List[str], line_idx: int) -> Optional[int]:
    """向前找最近的页码提示。"""
    for i in range(line_idx, -1, -1):
        m = _PAGE_HINT_RE.search(lines[i])
        if m:
            for g in m.groups():
                if g:
                    try:
                        return int(g)
                    except ValueError:
                        continue
    return None


def _find_chapter_candidates(lines: List[str]) -> List[SectionCandidate]:
    out: List[SectionCandidate] = []
    for i, line in enumerate(lines):
        m = _HEADING_RE.match(line)
        title = m.group(2).strip() if m else line.strip()
        # 既支持 markdown 标题，也支持粗体/普通行中包含关键词
        hits = [kw for kw in RETAIL_CHAPTER_KEYWORDS if kw in title]
        if not hits:
            continue
        # 过滤掉过长的行（不是标题）
        if not m and len(title) > 40:
            continue
        out.append(SectionCandidate(
            heading=title[:120],
            line_no=i + 1,
            page=_find_page_for_line(lines, i),
            matched_keywords=hits,
        ))
    return out


def _get_heading_chain(lines: List[str], line_idx: int) -> List[str]:
    """向前收集层级更高的标题，构造 heading_chain（从最顶层到最近）。"""
    chain: List[Tuple[int, str]] = []  # [(level, title)]
    current_level = 99
    for i in range(line_idx, -1, -1):
        m = _HEADING_RE.match(lines[i])
        if not m:
            continue
        level = len(m.group(1))
        title = m.group(2).strip()
        if level < current_level:
            chain.append((level, title))
            current_level = level
        if level == 1:
            break
    chain.reverse()
    return [t for _, t in chain][-4:]  # 最多 4 级


def _build_paragraph_candidates(
    lines: List[str],
    metrics: List[Dict[str, Any]],
    section_windows: List[Tuple[int, int]],
    max_per_metric: int = 4,
    context_before: int = 3,
    context_after: int = 6,
) -> List[ParagraphCandidate]:
    """
    在给定的 section_windows（行号区间）内扫描段落：
      - 对每个 metric，构建 "synonyms + standard_name 不含章节限定的裸词" 的关键词表
      - 按关键词 + 数字 pattern（含"亿"/"万"/"%"/"BPs"）识别候选段落
      - 合并相邻段落（3 行以内的相邻命中合并为同一 candidate）
    """
    # 构建 "关键词 -> [metric names]"
    keyword_to_metrics: Dict[str, List[str]] = {}
    for m in metrics:
        keywords = set(m.get("synonyms", []) or [])
        keywords.add(m["standard_name"])
        for kw in keywords:
            if len(kw) < 2:
                continue
            keyword_to_metrics.setdefault(kw, []).append(m["standard_name"])

    number_re = re.compile(
        r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?\s*"
        r"(?:万亿|亿元|亿|万元|万户|万张|万人|百万元|百万|个百分点|BPs?|%)"
    )

    candidates: List[ParagraphCandidate] = []
    candidate_seq = 0

    for start, end in section_windows:
        # 区间内逐行扫描
        i = start
        while i <= end and i < len(lines):
            line = lines[i]
            hit_metrics: Set[str] = set()
            hit_keywords: Set[str] = set()
            for kw, metric_names in keyword_to_metrics.items():
                if kw in line:
                    hit_keywords.add(kw)
                    for n in metric_names:
                        hit_metrics.add(n)
            # 要求同时命中关键词 + 句子里含数字单位（避免纯标题的空命中）
            has_number = bool(number_re.search(line))
            if hit_metrics and has_number:
                # 上下文窗口
                s = max(0, i - context_before)
                e = min(len(lines) - 1, i + context_after)
                ctx = "\n".join(lines[s: e + 1])
                candidate_seq += 1
                cand = ParagraphCandidate(
                    candidate_id=f"p{candidate_seq:03d}",
                    heading_chain=_get_heading_chain(lines, i),
                    start_line=s + 1,
                    end_line=e + 1,
                    page=_find_page_for_line(lines, i),
                    hit_metrics=sorted(hit_metrics),
                    hit_keywords=sorted(hit_keywords),
                    score=len(hit_metrics) * 2 + len(hit_keywords),
                    context_text=ctx,
                )
                candidates.append(cand)
                # 继续逐行扫描。财报常把理财/基金/保险收入放在连续表格行中；
                # 跳到上下文末尾会漏掉后续行对应的 metric。后续按 metric 限额去重即可。
            i += 1

    # 按 score 降序 + 每个 metric 最多保留 max_per_metric 个
    candidates.sort(key=lambda c: c.score, reverse=True)
    kept: List[ParagraphCandidate] = []
    metric_counter: Dict[str, int] = {}
    for c in candidates:
        keep = False
        for m in c.hit_metrics:
            if metric_counter.get(m, 0) < max_per_metric:
                keep = True
                break
        if keep:
            for m in c.hit_metrics:
                metric_counter[m] = metric_counter.get(m, 0) + 1
            kept.append(c)
    return kept


def _section_windows(
    lines: List[str],
    chapters: List[SectionCandidate],
    window_after: int = 500,
) -> List[Tuple[int, int]]:
    """把章节候选扩展为行号窗口。一个章节默认向后延伸 window_after 行。"""
    if not chapters:
        # 没有明显章节时，扫全文但限制最多前 60% 行（零售业务一般在后半段）
        return [(0, len(lines) - 1)]
    windows: List[Tuple[int, int]] = []
    for c in chapters:
        start = max(0, c.line_no - 1)
        end = min(len(lines) - 1, start + window_after)
        windows.append((start, end))
    # 合并相邻重叠窗口
    windows.sort()
    merged: List[Tuple[int, int]] = []
    for s, e in windows:
        if merged and s <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))
    return merged


def coarse_filter_text(
    md_path: pathlib.Path,
    metrics: List[Dict[str, Any]],
    bank: str,
    period: str,
) -> Dict[str, Any]:
    content = _load_text_content(md_path)
    lines = content.splitlines()
    chapters = _find_chapter_candidates(lines)
    windows = _section_windows(lines, chapters)
    paragraph_candidates = _build_paragraph_candidates(lines, metrics, windows)

    # 按 bucket 聚合 candidates（一个候选可能命中多个 bucket 的指标）
    by_bucket: Dict[str, List[ParagraphCandidate]] = {}
    metric_to_bucket: Dict[str, str] = {m["standard_name"]: _bucket_of(m) for m in metrics}
    for c in paragraph_candidates:
        buckets: Set[str] = set()
        for mname in c.hit_metrics:
            buckets.add(metric_to_bucket.get(mname, "其他"))
        for b in buckets:
            by_bucket.setdefault(b, []).append(c)

    return {
        "bank": bank,
        "period": period,
        "markdown_path": str(md_path),
        "chapter_candidates": [c.asdict() for c in chapters],
        "paragraph_candidates": [c.asdict() for c in paragraph_candidates],
        "paragraph_candidates_by_bucket": {
            b: [c.asdict() for c in cs] for b, cs in by_bucket.items()
        },
    }


# ---------------------------------------------------------------------------
# bundle 构造
# ---------------------------------------------------------------------------


def build_bundles(
    coarse: Dict[str, Any],
    metrics: List[Dict[str, Any]],
    out_dir: pathlib.Path,
    max_candidates_per_bucket: int = 8,
) -> List[pathlib.Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    grouped = coarse.get("paragraph_candidates_by_bucket", {}) or {}
    produced: List[pathlib.Path] = []

    for bucket in TEXT_BUCKETS:
        targets = [
            {
                "standard_name": m["standard_name"],
                "unit": m["unit"],
                "synonyms": m["synonyms"],
                "description": m.get("description", ""),
                "extract_fields": m.get("extract_fields", []),
                "valid_range": m.get("valid_range", {}),
                "calibration_note": m.get("calibration_note", ""),
                "category": m.get("category", ""),
            }
            for m in metrics
            if _bucket_of(m) == bucket
        ]
        if not targets:
            continue
        cands = grouped.get(bucket, []) or []

        # 先保证每个 target metric 的候选覆盖，再按粗筛得分补齐；避免 AUM 等高频
        # 候选占满 top-N 后挤掉理财/基金/保险等低频披露。
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

        trimmed = []
        for i, c in enumerate(cands, start=1):
            cc = dict(c)
            cc["candidate_id"] = f"p{i:02d}"
            trimmed.append(cc)

        bundle = {
            "bank": coarse["bank"],
            "period": coarse["period"],
            "category_bucket": bucket,
            "target_metrics": targets,
            "candidates": trimmed,
        }
        safe = bucket.replace("/", "_")
        out_path = out_dir / f"bundle_{safe}.json"
        out_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
        produced.append(out_path)
    return produced


# ---------------------------------------------------------------------------
# fine_tasks.json
# ---------------------------------------------------------------------------


def _render_spawn_prompt(
    bank: str,
    period: str,
    bucket: str,
    bundle_path: pathlib.Path,
    output_path: pathlib.Path,
    prompt_template: pathlib.Path,
) -> str:
    return (
        f"你是 Skill2 文字指标子代理，负责银行「{bank}」报告期「{period}」的 "
        f"「{bucket}」bucket。\n\n"
        f"执行步骤：\n"
        f"1. 先阅读系统提示文件（这是你的契约）：\n"
        f"   {prompt_template}\n"
        f"2. 读取 input_bundle（唯一数据源）：\n"
        f"   {bundle_path}\n"
        f"3. 严格遵守 text_extractor_prompt.md 中的规则，只从 "
        f"candidates[*].context_text 取值，**禁止编造**；未找到的指标 values 必须返回空数组 []。\n"
        f"4. 输出**纯 JSON**（不要 markdown 代码块、不要解释文字），写入：\n"
        f"   {output_path}\n"
        f"5. 写入完成后回报「bucket / metrics 数 / alerts 数 / 输出路径」，不贴 JSON 原文。\n"
        f"\n"
        f"完成标志：{output_path} 文件已存在且为合法 JSON。"
    )


def build_fine_tasks(
    bundles: List[pathlib.Path],
    extraction_dir: pathlib.Path,
    prompt_template: pathlib.Path,
    bank: str,
    period: str,
    concurrency: int,
) -> Dict[str, Any]:
    extraction_dir.mkdir(parents=True, exist_ok=True)
    concurrency = max(1, int(concurrency))

    tasks: List[Dict[str, Any]] = []
    for idx, bundle in enumerate(bundles):
        stem = bundle.stem
        bucket = stem[len("bundle_"):] if stem.startswith("bundle_") else stem
        output_path = extraction_dir / f"{bucket}.json"
        batch_index = idx // concurrency
        task_id = f"s2-fine-{bank}-{period}-{bucket}"
        spawn_prompt = _render_spawn_prompt(
            bank=bank, period=period, bucket=bucket,
            bundle_path=bundle.resolve(),
            output_path=output_path.resolve(),
            prompt_template=prompt_template,
        )
        tasks.append({
            "task_id": task_id,
            "bucket": bucket,
            "bundle_path": str(bundle.resolve()),
            "output_path": str(output_path.resolve()),
            "batch_index": batch_index,
            "spawn_prompt": spawn_prompt,
        })

    batches: List[List[str]] = []
    if tasks:
        max_batch = max(t["batch_index"] for t in tasks)
        batches = [[] for _ in range(max_batch + 1)]
        for t in tasks:
            batches[t["batch_index"]].append(t["task_id"])

    return {
        "bank": bank,
        "period": period,
        "concurrency": concurrency,
        "prompt_template": str(prompt_template),
        "extraction_dir": str(extraction_dir.resolve()),
        "tasks": tasks,
        "batches": batches,
    }


# ---------------------------------------------------------------------------
# merge
# ---------------------------------------------------------------------------


def _t2_stop_disclosure(
    current_metrics: List[Dict[str, Any]],
    prior_metrics: Optional[List[Dict[str, Any]]],
    bank: str,
    current_period: str,
    prior_period: Optional[str],
) -> List[Dict[str, Any]]:
    """规则 T2：上期披露但本期未披露。"""
    if not prior_metrics:
        return []
    alerts: List[Dict[str, Any]] = []
    current_names = {
        m["standard_name"] for m in current_metrics if m.get("values")
    }
    for pm in prior_metrics:
        if not pm.get("values"):
            continue
        if pm["standard_name"] in current_names:
            continue
        # 找到上期的 representative value
        v = pm["values"][0] if pm["values"] else {}
        alerts.append({
            "alert_type": "disclosure_discontinued",
            "bank": bank,
            "metric": pm["standard_name"],
            "prior_period": prior_period,
            "prior_value": v.get("period_end_value") or v.get("value"),
            "prior_unit": v.get("unit"),
            "prior_source_page": v.get("source_page"),
            "current_period": current_period,
            "current_value": None,
            "note": f"上期({prior_period})披露该指标，本期({current_period})未找到对应披露",
        })
    return alerts


def _normalized_evidence(text: Any) -> str:
    """归一化证据文本，兼容 Markdown 表格分隔符和 OCR 空白。"""
    if not isinstance(text, str):
        return ""
    return re.sub(r"[\s|*`]+", "", text)


def _load_candidate_evidence(manifest: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    """返回 bucket -> candidate_id -> context_text 的证据索引。"""
    evidence: Dict[str, Dict[str, str]] = {}
    for raw_path in manifest.get("bundles", []) or []:
        path = pathlib.Path(raw_path).expanduser()
        try:
            bundle = json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        bucket = str(bundle.get("category_bucket") or path.stem.removeprefix("bundle_"))
        evidence[bucket] = {
            str(c.get("candidate_id")): str(c.get("context_text", ""))
            for c in (bundle.get("candidates", []) or [])
            if c.get("candidate_id")
        }
    return evidence


def _filter_unverifiable_values(
    metrics: List[Dict[str, Any]],
    candidate_contexts: Dict[str, str],
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """删除无法在 candidate 原文中回溯的值，阻断示例值/配置值污染。"""
    warnings: List[str] = []
    for metric in metrics:
        kept_values = []
        name = metric.get("standard_name", "<unknown>")
        for value in metric.get("values", []) or []:
            candidate_id = str(value.get("candidate_id") or "")
            quote = _normalized_evidence(value.get("raw_quote"))
            context = _normalized_evidence(candidate_contexts.get(candidate_id, ""))
            if not candidate_id or len(quote) < 6 or quote not in context:
                warnings.append(
                    f"证据校验未通过，已删除 {name} 的值：candidate_id={candidate_id or '<missing>'}"
                )
                continue
            kept_values.append(value)
        metric["values"] = kept_values
    return metrics, warnings


def merge_extractions(
    manifest: Dict[str, Any],
    prior_partial: Optional[pathlib.Path] = None,
) -> Dict[str, Any]:
    extraction_dir = pathlib.Path(manifest["extraction_dir"]).expanduser()
    merged_metrics: List[Dict[str, Any]] = []
    merged_alerts: List[Dict[str, Any]] = []
    merged_notes: List[str] = []
    merged_warnings: List[str] = []
    evidence_by_bucket = _load_candidate_evidence(manifest)

    for f in sorted(extraction_dir.glob("*.json")):
        try:
            obj = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            merged_warnings.append(f"读取 {f.name} 失败：{e}")
            continue
        bucket = str(obj.get("category_bucket") or f.stem)
        metrics, evidence_warnings = _filter_unverifiable_values(
            obj.get("metrics", []) or [], evidence_by_bucket.get(bucket, {}),
        )
        merged_metrics.extend(metrics)
        merged_alerts.extend(obj.get("alerts", []) or [])
        merged_notes.extend(obj.get("notes", []) or [])
        merged_warnings.extend(obj.get("warnings", []) or [])
        merged_warnings.extend(evidence_warnings)

    # 规则 T2（需要上期 partial）
    prior_metrics = None
    prior_period = None
    if prior_partial and prior_partial.exists():
        prior_doc = json.loads(prior_partial.read_text(encoding="utf-8"))
        prior_metrics = prior_doc.get("metrics", [])
        prior_period = prior_doc.get("period")
    t2_alerts = _t2_stop_disclosure(
        merged_metrics, prior_metrics, manifest["bank"],
        manifest["period"], prior_period,
    )
    merged_alerts.extend(t2_alerts)

    partial_doc = {
        "bank": manifest["bank"],
        "period": manifest["period"],
        "metrics": merged_metrics,
        "alerts": merged_alerts,
        "notes": merged_notes,
        "warnings": merged_warnings,
        "source": {
            "markdown_path": manifest.get("markdown_path"),
            "coarse_json": manifest.get("coarse_json"),
            "extraction_dir": manifest.get("extraction_dir"),
        },
        "config": manifest.get("config", {}),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    return partial_doc


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _get_metrics_config(args: argparse.Namespace) -> Tuple[pathlib.Path, Dict[str, Any]]:
    """按统一优先级解析 Skill 2 指标配置，并返回可审计元数据。"""
    path, source = _PATHS.resolve_config_file(
        "skill2", "metrics.yaml", explicit_path=args.metrics_yaml,
    )
    return path, _PATHS.config_file_metadata(path, source)


def cmd_prepare(args: argparse.Namespace) -> None:
    work_dir = pathlib.Path(args.work_dir).expanduser().resolve()
    work_dir.mkdir(parents=True, exist_ok=True)

    unzip_dir = work_dir / "unzip"
    bundles_dir = work_dir / "text_bundles"
    extraction_dir = work_dir / "text_extraction"

    md_path = _load_markdown_from_source(pathlib.Path(args.source), unzip_dir)
    print(f"[prepare] markdown -> {md_path}", flush=True)

    metrics_yaml, metrics_meta = _get_metrics_config(args)
    metrics = _load_text_metrics(metrics_yaml)
    print(
        f"[config] metrics={metrics_yaml} source={metrics_meta['source']} "
        f"sha256={metrics_meta['sha256'][:12]}",
        flush=True,
    )
    print(f"[prepare] loaded {len(metrics)} text metrics", flush=True)

    coarse = coarse_filter_text(md_path, metrics, args.bank, args.period)
    coarse_path = work_dir / "coarse.json"
    coarse_path.write_text(
        json.dumps(coarse, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        f"[coarse] chapters={len(coarse['chapter_candidates'])} "
        f"paragraphs={len(coarse['paragraph_candidates'])} -> {coarse_path}",
        flush=True,
    )

    bundles = build_bundles(coarse, metrics, bundles_dir)
    print(f"[bundle] {len(bundles)} bundle(s) -> {bundles_dir}", flush=True)
    for b in bundles:
        print(f"         - {b.name}", flush=True)

    prompt_template = pathlib.Path(
        args.prompt_template
        or (_SCRIPT_DIR / "text_extractor_prompt.md")
    ).resolve()
    if not prompt_template.exists():
        raise SystemExit(f"prompt 模板不存在：{prompt_template}")

    fine_tasks = build_fine_tasks(
        bundles=bundles,
        extraction_dir=extraction_dir,
        prompt_template=prompt_template,
        bank=args.bank,
        period=args.period,
        concurrency=args.concurrency,
    )
    fine_tasks_path = work_dir / "fine_tasks.json"
    fine_tasks_path.write_text(
        json.dumps(fine_tasks, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        f"[fine_tasks] {len(fine_tasks['tasks'])} task(s) in "
        f"{len(fine_tasks['batches'])} batch(es) (concurrency={args.concurrency}) "
        f"-> {fine_tasks_path}",
        flush=True,
    )

    partial_output = pathlib.Path(args.partial_output).expanduser().resolve()
    manifest = {
        "bank": args.bank,
        "period": args.period,
        "markdown_path": str(md_path),
        "coarse_json": str(coarse_path),
        "bundles": [str(p) for p in bundles],
        "extraction_dir": str(extraction_dir),
        "prompt_template": str(prompt_template),
        "fine_tasks_json": str(fine_tasks_path),
        "partial_output": str(partial_output),
        "concurrency": args.concurrency,
        "config": {"metrics": metrics_meta},
    }
    manifest_path = work_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[manifest] -> {manifest_path}", flush=True)
    print(
        f"[next] 主 Agent 请读取 {fine_tasks_path} 并按 batches 并发 spawn 子代理 "
        f"(默认并发 {args.concurrency})。\n"
        f"       每个子代理按 {prompt_template} 契约工作，不要主 Agent 自己调 LLM。",
        flush=True,
    )


def cmd_merge(args: argparse.Namespace) -> None:
    manifest_path = pathlib.Path(args.manifest).expanduser().resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    prior_partial = pathlib.Path(args.prior_partial).expanduser() if args.prior_partial else None

    partial_doc = merge_extractions(manifest, prior_partial=prior_partial)

    partial_output = pathlib.Path(manifest["partial_output"]).expanduser().resolve()
    partial_output.parent.mkdir(parents=True, exist_ok=True)
    partial_output.write_text(
        json.dumps(partial_doc, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        f"[merge] metrics={len(partial_doc['metrics'])} "
        f"alerts={len(partial_doc['alerts'])} "
        f"warnings={len(partial_doc['warnings'])} "
        f"-> {partial_output}",
        flush=True,
    )


def build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Skill 2 文字指标抽取 prepare / merge（禁止自己调 LLM，子代理分派）",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_prep = sub.add_parser("prepare", help="粗筛 + bundle + fine_tasks.json")
    p_prep.add_argument("--bank", required=True)
    p_prep.add_argument("--period", required=True)
    p_prep.add_argument(
        "--source",
        required=True,
        help="DocParse zip / markdown 文件 / 目录",
    )
    p_prep.add_argument("--work-dir", required=True)
    p_prep.add_argument("--partial-output", required=True)
    p_prep.add_argument("--metrics-yaml", default=None)
    p_prep.add_argument("--prompt-template", default=None)
    p_prep.add_argument("--concurrency", type=int, default=3)
    p_prep.set_defaults(func=cmd_prepare)

    p_merge = sub.add_parser("merge", help="合并子代理输出 -> partial JSON")
    p_merge.add_argument("--manifest", required=True)
    p_merge.add_argument(
        "--prior-partial",
        default=None,
        help="上期 partial JSON 路径（提供后将触发规则 T2 停披校验）",
    )
    p_merge.set_defaults(func=cmd_merge)

    return parser


def main() -> None:
    args = build_argparser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
