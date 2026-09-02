#!/usr/bin/env python3
"""
粗筛脚本：基于关键字在解析后的 Markdown 中定位候选章节与候选表格。

职责（纯规则/无 LLM）：
  1) 读取腾讯云解析产物的 Markdown（.md 文件）
  2) 按 metrics.yaml 的 standard_name + synonyms + 章节关键词构建词表
  3) 扫描 Markdown，产出两类候选：
     a. 候选章节（chapter_candidates）：命中章节关键词的标题行
     b. 候选表格（table_candidates）：Markdown 表格（以 `|...|` 为特征）且在其上下文中命中指标词
  4) 为每个候选打上命中的指标 standard_name 列表 + 相关性得分
  5) 输出 JSON 清单，供后续 LLM 精筛阶段按需取用（避免把整份 Markdown 全塞进 LLM）

约定：
  - 候选表格的 context_window 默认向上取 20 行、向下取全表 + 5 行
  - 一个表格可以命中多个指标，指标 ID 去重
  - 命中严格按子串匹配 + 简单分词，不做语义匹配
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

import yaml

# ---------------------------------------------------------------------------
# 共享路径约定：默认从 $RETAIL_ANALYSIS_HOME（默认 ~/RetailAnalysis）读取配置
# ---------------------------------------------------------------------------
# paths.py 已同步为本 Skill scripts/ 下的副本（由 release.py 保证与仓库根一致），
# zip 打包后也能自包含运行。import 策略：
#   1) 优先从本脚本同目录导入（zip 打包 / 正常运行）
#   2) 兜底：向上三级找仓库根 scripts/（开发期 Skill 缺副本的极端场景）
try:  # pragma: no cover - 只在找不到 paths 模块时降级
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


# ---------------------------------------------------------------------------
# 章节关键词（粗筛第一道：先定位到相关的大章节，缩小后续扫描范围）
# ---------------------------------------------------------------------------

CHAPTER_KEYWORDS: Dict[str, List[str]] = {
    "segment_report": [
        "分部报告", "业务分部", "经营分部",
        "分部经营",        # 某银行"2.5分部经营数据"
        "经营分部信息",    # 附注中"经营分部信息"
        "分部信息",        # 通用
        "分部财务",        # 通用
        "业务条线",        # 某银行"各业务条线经营业绩"
        "盈利与规模",      # 某银行"2.5.1盈利与规模"
        "零售金融", "零售银行", "个人银行业务",
        "零售金融业务",    # 表头列名也作为章节关键词
    ],
    "retail_deposit": [
        "客户存款", "吸收存款", "存款结构",
        "个人存款", "储蓄存款",
        # P3 扩充
        "客户存款利息支出",  # 某银行：该章节表内含零售活期/定期细分
        "零售存款", "存款利息支出",
    ],
    "retail_loan": [
        "发放贷款", "客户贷款", "贷款结构",
        "个人贷款", "零售贷款",
        "信用卡", "住房按揭", "消费贷", "经营贷",
        # P3 扩充
        "按产品类型划分",  # 某银行的核心章节名
        "个人类贷款", "零售信贷",
        "贷款行业分布",  # 某银行
    ],
    "asset_quality": [
        "资产质量", "不良贷款", "贷款质量",
        "五级分类", "贷款迁徙",
        # P3 扩充
        "按产品类型划分",  # 某银行资产质量细分表的章节名
        "个人贷款结构",    # 某银行
        "不良贷款结构",
    ],
    "provision": [
        "贷款损失准备", "减值准备", "拨备",
        "拨备覆盖率", "贷款拨备率",
        "利润表项目分析",   # 利润表章节（跨 bundle 交叉引用来源）
        "利润表分析",       # 某银行"3.2利润表分析"
        "财务业绩摘要",     # 通用
        "损益项目",         # 通用
    ],
    "fee_commission": [
        "手续费及佣金", "银行卡手续费", "手续费收入",
        "利润表项目分析",   # 手续费也从利润表取
        "利润表分析",
    ],
}

# 章节感知兜底：当表格落在某个章节内时，这些"核心短词"也视为命中。
# 用于弥补 metrics.yaml 中同义词过长（如"零售银行业务-营业净收入"）而真实表格只写短词的问题。
CHAPTER_FALLBACK_SHORT_TOKENS: Dict[str, List[str]] = {
    "segment_report": [
        "营业净收入", "营业收入", "利息净收入", "手续费及佣金净收入",
        "信用减值损失", "业务及管理费", "业务费用",
        "折旧", "摊销", "税前利润", "利润总额",
        "信用及其他资产减值损失",   # 某银行利润表行名
        "减值损失前营业利润",       # 某银行分部表行名
        "净利润",                   # 通用
        "营业支出",                 # 通用
        # P3 扩充：某银行等分部报告里零售营收会拆分"零售净利息收入"+"零售非利息净收入"
        "零售净利息收入", "零售非利息净收入",
        "零售金融业务", "零售银行业务",  # 表格内行标签高频短词
        "非利息净收入",              # 与"利息净收入"对称
    ],
    "retail_deposit": [
        "活期存款", "定期存款", "存款余额", "平均余额", "成本率",
        # P3 扩充：个人存款活期/定期细项
        "个人活期", "个人定期", "储蓄活期", "储蓄定期",
        "零售活期", "零售定期",
        "日均余额",           # 通用
    ],
    "retail_loan": [
        "贷款余额", "平均余额", "收益率",
        # P3 扩充：零售贷款产品细分
        "信用卡应收", "信用卡透支", "信用卡 余额",
        "个人住房贷款", "住房贷款", "个人住房及商用房",
        "个人经营", "经营贷",  "个人消费", "消费贷",
        "零售贷款余额",
    ],
    "asset_quality": [
        "不良率", "不良贷款率", "不良贷款余额", "不良贷款额",
        # P3 扩充：产品级不良指标高频短词
        "个人按揭", "个人经营贷款", "个人住房", "信用卡及透支",
        "消费贷款及其他",   # 某银行口径
        "个人贷款不良率",
    ],
    "provision": [
        "拨备覆盖率", "贷款拨备率", "本期计提", "本期转回", "本期核销",
        "信用减值损失", "信用及其他资产减值损失",  # 利润表兜底
        # P3 扩充
        "贷款损失准备",  "减值准备期初余额", "减值准备期末余额",
        "本期净计提", "收回已核销",
    ],
    "fee_commission": [
        "银行卡手续费", "银行卡业务",
        "手续费及佣金净收入",  # 利润表兜底
        # P3 扩充
        "银行卡服务手续费",     # 某银行口径
        "手续费及佣金收入",     # 某银行等
        "理财服务手续费", "托管及其他受托", "代理业务手续费",
    ],
}


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class ChapterCandidate:
    chapter_group: str           # CHAPTER_KEYWORDS 的 key
    heading: str                 # 标题原文
    line_no: int                 # 在 Markdown 中的行号（1-based）
    matched_keywords: List[str]  # 命中的章节关键词


@dataclass
class TableCandidate:
    start_line: int              # 表格起始行（1-based）
    end_line: int                # 表格结束行
    context_start_line: int      # 上下文起始行
    context_end_line: int        # 上下文结束行
    heading_chain: List[str]     # 最近的 1-3 级标题链（用于定位章节）
    hit_metrics: List[str]       # 命中的 standard_name 列表（去重）
    hit_categories: List[str]    # 命中的 metric category（去重）
    hit_keywords: List[str]      # 命中的具体关键词
    score: int                   # 相关性得分（命中数 + 权重加成）
    table_markdown: str          # 表格本身的 Markdown 文本
    context_markdown: str        # 上下文片段（包含表格及前后文，供 LLM 精筛直接使用）


# ---------------------------------------------------------------------------
# metrics.yaml 读取与词表构建
# ---------------------------------------------------------------------------

# 仅 Skill 1 关心的指标分组 key
SKILL1_METRIC_GROUPS = [
    "segment_report_metrics",
    "retail_deposit_metrics",
    "retail_loan_metrics",
    "retail_asset_quality_metrics",
    "bank_wide_metrics",
]


def _load_metrics(metrics_yaml: pathlib.Path) -> List[Dict[str, Any]]:
    """读取 metrics.yaml 中 Skill 1 负责的表格类指标。"""
    data = yaml.safe_load(metrics_yaml.read_text(encoding="utf-8"))
    metrics: List[Dict[str, Any]] = []
    for group in SKILL1_METRIC_GROUPS:
        for item in data.get(group, []) or []:
            if item.get("scope") and item["scope"] != "表格":
                continue
            metrics.append({
                "standard_name": item["standard_name"],
                "category": item.get("category", ""),
                "synonyms": item.get("synonyms", []) or [],
                "group": group,
            })
    return metrics


def _build_keyword_index(
    metrics: List[Dict[str, Any]],
) -> Tuple[Dict[str, List[str]], Dict[str, str]]:
    """
    构建 keyword -> [standard_name...] 索引。
    同时返回 keyword -> category 的反查表用于打分。
    """
    kw_to_metrics: Dict[str, List[str]] = {}
    kw_to_category: Dict[str, str] = {}
    for m in metrics:
        names: Set[str] = {m["standard_name"], *m["synonyms"]}
        for kw in names:
            kw = kw.strip()
            if not kw:
                continue
            kw_to_metrics.setdefault(kw, []).append(m["standard_name"])
            kw_to_category[kw] = m["category"]
    # 去重
    for kw, lst in kw_to_metrics.items():
        kw_to_metrics[kw] = sorted(set(lst))
    return kw_to_metrics, kw_to_category


# ---------------------------------------------------------------------------
# Markdown 扫描工具
# ---------------------------------------------------------------------------

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$")
TABLE_SEP_RE = re.compile(r"^\s*\|?\s*[-:]+[-|:\s]*$")


def _iter_headings(lines: List[str]) -> List[Tuple[int, int, str]]:
    """返回 [(line_no, level, heading_text), ...]，line_no 为 1-based。"""
    out = []
    for idx, line in enumerate(lines, start=1):
        m = HEADING_RE.match(line)
        if m:
            level = len(m.group(1))
            out.append((idx, level, m.group(2).strip()))
    return out


def _nearest_heading_chain(
    headings: List[Tuple[int, int, str]], line_no: int, max_levels: int = 3,
) -> List[str]:
    """给定行号，反向找到最近的 h1..hN 标题链，最多 max_levels 条。"""
    chain_by_level: Dict[int, str] = {}
    for h_line, level, text in headings:
        if h_line > line_no:
            break
        chain_by_level[level] = text
        # 清理高于当前 level 的缓存（新段落开始）
        higher = [lv for lv in chain_by_level if lv > level]
        for lv in higher:
            chain_by_level.pop(lv, None)
    ordered = [chain_by_level[lv] for lv in sorted(chain_by_level.keys()) if lv <= max_levels]
    return ordered


def _find_tables(lines: List[str]) -> List[Tuple[int, int]]:
    """识别 Markdown 表格，返回 [(start_line, end_line), ...]（均为 1-based）。"""
    tables: List[Tuple[int, int]] = []
    i = 0
    n = len(lines)
    while i < n:
        if TABLE_ROW_RE.match(lines[i]):
            # 至少 2 行（表头 + 分隔 + 1 行数据）
            if i + 1 < n and TABLE_SEP_RE.match(lines[i + 1]):
                start = i + 1  # 1-based
                j = i + 2
                while j < n and TABLE_ROW_RE.match(lines[j]):
                    j += 1
                end = j  # 1-based（j 为最后表格行的下一行 0-based 索引 -> end 含义为闭区间行号=j）
                tables.append((start, j))  # j 就是 1-based 的最后一行号
                i = j
                continue
        i += 1
    return tables


def _scan_chapter_candidates(
    headings: List[Tuple[int, int, str]],
) -> List[ChapterCandidate]:
    """对标题列表扫描，命中章节关键词则加入候选。"""
    out: List[ChapterCandidate] = []
    for line_no, _, text in headings:
        for group, kws in CHAPTER_KEYWORDS.items():
            hits = [kw for kw in kws if kw in text]
            if hits:
                out.append(ChapterCandidate(
                    chapter_group=group,
                    heading=text,
                    line_no=line_no,
                    matched_keywords=hits,
                ))
                break  # 一个标题只归到第一个匹配组
    return out


def _scan_table_candidates(
    lines: List[str],
    tables: List[Tuple[int, int]],
    headings: List[Tuple[int, int, str]],
    kw_to_metrics: Dict[str, List[str]],
    kw_to_category: Dict[str, str],
    context_above: int,
    context_below: int,
    metrics: Optional[List[Dict[str, Any]]] = None,
) -> List[TableCandidate]:
    """
    对每个 Markdown 表格：
      - 取 [start-context_above, end+context_below] 的片段做关键词扫描
      - 命中任意指标关键词才视为候选
      - 章节感知兜底：若表格落在某 CHAPTER_KEYWORDS group 下，且 ctx 里出现该
        group 的 CHAPTER_FALLBACK_SHORT_TOKENS，则按 group 对应的 category 反查
        指标并补登命中。
    """
    total = len(lines)
    candidates: List[TableCandidate] = []

    # 构造 group -> [standard_name] 的反查，用于兜底
    group_to_std_names: Dict[str, List[str]] = {}
    if metrics:
        # 每个 CHAPTER group 对应哪些 metric groups
        group_to_metric_groups = {
            "segment_report": ["segment_report_metrics"],
            "retail_deposit": ["retail_deposit_metrics"],
            "retail_loan": ["retail_loan_metrics"],
            "asset_quality": ["retail_asset_quality_metrics"],
            "provision": ["bank_wide_metrics"],      # 只取风控指标那部分
            "fee_commission": ["bank_wide_metrics"],  # 只取收费指标那部分
        }
        for ch_group, metric_groups in group_to_metric_groups.items():
            names: List[str] = []
            for m in metrics:
                if m["group"] in metric_groups:
                    cat = m.get("category", "")
                    # provision 只挑风控类，fee_commission 只挑收费类
                    if ch_group == "provision" and "风控" not in cat:
                        continue
                    if ch_group == "fee_commission" and "收费" not in cat:
                        continue
                    names.append(m["standard_name"])
            group_to_std_names[ch_group] = names

    for start, end in tables:
        ctx_start = max(1, start - context_above)
        ctx_end = min(total, end + context_below)

        # 切片：lines 是 0-based list
        ctx_slice = "\n".join(lines[ctx_start - 1: ctx_end])

        hit_metrics: Set[str] = set()
        hit_keywords: Set[str] = set()
        hit_categories: Set[str] = set()

        for kw, std_names in kw_to_metrics.items():
            # 简单子串匹配；短关键词（<=2 字）严格避免，减少噪音
            if len(kw) <= 2:
                continue
            if kw in ctx_slice:
                hit_keywords.add(kw)
                for name in std_names:
                    hit_metrics.add(name)
                hit_categories.add(kw_to_category.get(kw, ""))

        # -------- 章节感知兜底 --------
        chain = _nearest_heading_chain(headings, start)
        chain_text = " / ".join(chain)

        # 为了适配 OCR 分行（如"分部营 业收入"、"分部税 前利润"），在扫描前把 ctx
        # 的"中文字符间空白"去除一份用于兜底匹配（仅兜底路径使用，不影响正文）。
        import re as _re
        ctx_squeezed = _re.sub(r"([\u4e00-\u9fff])\s+([\u4e00-\u9fff])", r"\1\2", ctx_slice)

        # 强制命中的章节：heading 命中这些章节，该章节的所有目标指标都登记为候选，
        # 即使 ctx 里没能命中短词（解决 OCR 分行/列名极简 如"分部营业收入"/"分部税前利润"）。
        FORCE_HIT_GROUPS = {"segment_report"}

        for ch_group, chapter_kws in CHAPTER_KEYWORDS.items():
            if not any(ck in chain_text for ck in chapter_kws):
                continue

            # 在本章节下，若 ctx（去空格版）命中任一短词，则把该章节的指标集合补登
            short_hits = [
                tok for tok in CHAPTER_FALLBACK_SHORT_TOKENS.get(ch_group, [])
                if tok in ctx_slice or tok in ctx_squeezed
            ]

            # 分部报告章节特殊处理：即使短词未命中（OCR 列名极简），
            # 只要 heading 明确落在分部章节内，就把所有分部指标登记为候选。
            if not short_hits and ch_group not in FORCE_HIT_GROUPS:
                continue

            for tok in short_hits:
                hit_keywords.add(tok)
            if ch_group in FORCE_HIT_GROUPS and not short_hits:
                # 至少把 chapter_kws 中命中的那个词作为"伪命中关键词"记录下来
                for ck in chapter_kws:
                    if ck in chain_text:
                        hit_keywords.add(ck)
                        break
            for name in group_to_std_names.get(ch_group, []):
                hit_metrics.add(name)
            # category 聚合：取该章节的第一个 category 主标签
            if group_to_std_names.get(ch_group):
                # 从 metrics 里找一个代表性 category
                if metrics:
                    for m in metrics:
                        if m["standard_name"] in group_to_std_names[ch_group]:
                            hit_categories.add(m.get("category", ""))
                            break

        if not hit_metrics:
            continue

        # 打分：命中指标数 * 2 + 命中关键词数
        score = len(hit_metrics) * 2 + len(hit_keywords)

        table_md = "\n".join(lines[start - 1: end])
        context_md = ctx_slice

        candidates.append(TableCandidate(
            start_line=start,
            end_line=end,
            context_start_line=ctx_start,
            context_end_line=ctx_end,
            heading_chain=chain,
            hit_metrics=sorted(hit_metrics),
            hit_categories=sorted(c for c in hit_categories if c),
            hit_keywords=sorted(hit_keywords),
            score=score,
            table_markdown=table_md,
            context_markdown=context_md,
        ))

    # 按 score 降序输出（保持稳定）
    candidates.sort(key=lambda c: (-c.score, c.start_line))
    return candidates


# ---------------------------------------------------------------------------
# 对外函数
# ---------------------------------------------------------------------------

def coarse_filter(
    markdown_path: pathlib.Path,
    metrics_yaml: pathlib.Path,
    context_above: int = 20,
    context_below: int = 5,
) -> Dict[str, Any]:
    """对外入口：执行粗筛并返回 dict。"""
    if not markdown_path.exists():
        raise FileNotFoundError(f"Markdown 不存在: {markdown_path}")
    if not metrics_yaml.exists():
        raise FileNotFoundError(f"metrics.yaml 不存在: {metrics_yaml}")

    text = markdown_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    metrics = _load_metrics(metrics_yaml)
    kw_to_metrics, kw_to_category = _build_keyword_index(metrics)

    headings = _iter_headings(lines)
    chapter_candidates = _scan_chapter_candidates(headings)

    tables = _find_tables(lines)
    table_candidates = _scan_table_candidates(
        lines=lines,
        tables=tables,
        headings=headings,
        kw_to_metrics=kw_to_metrics,
        kw_to_category=kw_to_category,
        context_above=context_above,
        context_below=context_below,
        metrics=metrics,
    )

    # 按 group 聚合表格候选，方便精筛按分组逐批交给 LLM。
    # 一张表经常同时覆盖多个类别（例如贷款余额 + 产品不良率）；必须加入所有命中
    # bucket，不能只取排序后的第一个 category，否则会稳定漏掉资产质量等指标。
    grouped: Dict[str, List[TableCandidate]] = {}
    for cand in table_candidates:
        buckets = {cat.split("-")[0] for cat in cand.hit_categories if cat}
        if not buckets:
            buckets = {"general"}
        for bucket in sorted(buckets):
            grouped.setdefault(bucket, []).append(cand)

    return {
        "markdown_path": str(markdown_path),
        "total_lines": len(lines),
        "chapter_candidates": [asdict(c) for c in chapter_candidates],
        "table_candidates": [asdict(c) for c in table_candidates],
        "table_candidates_by_category": {
            k: [asdict(c) for c in v] for k, v in grouped.items()
        },
        "metric_count": len(metrics),
        "kw_count": len(kw_to_metrics),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="粗筛：从 Markdown 中定位候选章节与候选表格")
    parser.add_argument("--markdown", required=True, help="腾讯云解析得到的 Markdown 文件路径")
    parser.add_argument(
        "--metrics-yaml",
        default=None,
        help="显式指标字典；默认使用环境覆盖或 Skill 本地 config/metrics.yaml",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="粗筛结果 JSON 输出路径",
    )
    parser.add_argument("--context-above", type=int, default=20)
    parser.add_argument("--context-below", type=int, default=5)
    return parser.parse_args()


def main() -> None:
    args = build_args()
    result = coarse_filter(
        markdown_path=pathlib.Path(args.markdown),
        metrics_yaml=_resolve_cli_metrics_yaml(args.metrics_yaml),
        context_above=args.context_above,
        context_below=args.context_below,
    )
    output_path = pathlib.Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    summary = (
        f"[coarse] markdown_lines={result['total_lines']} "
        f"chapter_candidates={len(result['chapter_candidates'])} "
        f"table_candidates={len(result['table_candidates'])} "
        f"metric_kw={result['kw_count']}"
    )
    print(summary, flush=True)
    print(f"[coarse] output -> {output_path.resolve()}", flush=True)


if __name__ == "__main__":
    main()
