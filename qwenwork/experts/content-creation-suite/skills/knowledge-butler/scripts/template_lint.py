#!/usr/bin/env python3
"""知识管家 · 专题模板健康检查脚本

按 v3 模板规范扫描所有专题页，输出：
  - 段频率统计（按 entity_kind 分组）—— 反哺"软建议"清单
  - 空段比例 / 缺源比例 / 孤儿专题
  - 每个专题的 lint 警告

子命令：
  count-mentions   扫摘要 + 专题，统计每个 [[实体]] 出现次数（用于"专题 3 规则"批量判定）
  audit            扫所有专题，输出健康检查报告（JSON + Markdown）
  section-stats    按 entity_kind 分组统计段频率，给"软建议清单演化"提供依据
  staleness-check  扫最近 N 天新增/修改的摘要，对比被引用的专题文件 mtime——
                   摘要新但专题未同步更新 = staleness 警报（防止 wiki 退化成 RAG）

使用示例：
  # 统计实体出现次数（批量投喂 flomo 后用）
  python3 template_lint.py count-mentions --kb-root ~/Documents/0-project/知识管家/CC版-KB/

  # 健康检查
  python3 template_lint.py audit --kb-root ~/Documents/0-project/知识管家/CC版-KB/

  # 段频率统计
  python3 template_lint.py section-stats --kb-root ~/Documents/0-project/知识管家/CC版-KB/
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional

# ---------- 常量 ----------

SCRIPT_VERSION = "v1.0"

DIR_SUMMARIES = Path("2-AI知识库") / "素材摘要"
DIR_TOPICS = Path("2-AI知识库") / "专题"
DIR_INSIGHTS = Path("2-AI知识库") / "洞察"

# v3 硬骨架段（L1 必填）
HARD_SECTIONS_L1 = [
    "已确认事实",
    "当前判断",
    "AI 推断",
    "未解决问题",
    "Timeline",
    "被提到",
]

# 段名向后兼容映射（v2 名 → v3 名）—— 存量逐步迁移期使用
SECTION_ALIASES = {
    "现状综合": "当前判断",
    "Synthesis": "当前判断",
    "关键事实": "已确认事实",
    "关键标签": "已确认事实",
    "待解问题": "未解决问题",
    "Lint 提示": "未解决问题",
    "关联": "关联专题",
}

# v3 通用 L2 段
SOFT_SECTIONS_L2 = ["矛盾与分歧", "关联专题"]

# v3 entity_kind 推荐段（可演化）
RECOMMENDED_BY_KIND = {
    "person": ["核心观点", "行为模式", "对我的影响", "原话金句"],
    "org": ["业务场景", "关键人", "诉求", "机会风险"],
    "project": ["目标", "假设", "状态", "关键里程碑", "决策记录", "下一步"],
    "method": ["定义", "适用场景", "操作流程", "案例", "反例", "Checklist"],
}

# 正则
RE_FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
RE_LINK = re.compile(r"\[\[([^\[\]\n]+?)\]\]")
RE_H2 = re.compile(r"^## (.+?)$", re.MULTILINE)
RE_FRONTMATTER_FIELD = re.compile(r"^(\w+):\s*(.*?)$", re.MULTILINE)


def parse_frontmatter(text: str) -> dict:
    """简化版 frontmatter 解析，只取顶层 key-value 字符串。"""
    m = RE_FRONTMATTER.match(text)
    if not m:
        return {}
    fm_text = m.group(1)
    out = {}
    for fm in RE_FRONTMATTER_FIELD.finditer(fm_text):
        key, val = fm.group(1), fm.group(2).strip()
        # 简单去引号
        val = val.strip("'\"")
        out[key] = val
    return out


def normalize_section_name(raw: str) -> str:
    """段名归一化：去括号注释 + 应用 v2→v3 alias。

    "现状综合（Synthesis · 最后综合时间：2026-05-02）" → "当前判断"
    "待解问题（Lint 提示）" → "未解决问题"
    """
    # 去掉括号（中英文）及之后的内容
    name = re.split(r"[（(]", raw, maxsplit=1)[0].strip()
    return SECTION_ALIASES.get(name, name)


def get_h2_sections(text: str) -> list[str]:
    """提取所有 ## 标题（去掉 frontmatter 后），段名已归一化。"""
    body = text
    m = RE_FRONTMATTER.match(text)
    if m:
        body = text[m.end():]
    return [normalize_section_name(h) for h in RE_H2.findall(body)]


def get_section_body(text: str, section_name: str) -> str:
    """提取某个 ## 段的 body（不含标题，到下一个 ## 或 EOF）。

    支持归一化后的段名匹配——会同时尝试原始段名 + 所有可能的 v2 alias。
    """
    # 收集所有可能匹配该归一化段名的原始名字
    candidates = [section_name]
    for v2_name, v3_name in SECTION_ALIASES.items():
        if v3_name == section_name:
            candidates.append(v2_name)

    for cand in candidates:
        pattern = re.compile(
            rf"^## {re.escape(cand)}.*?$\n(.*?)(?=^## |\Z)",
            re.MULTILINE | re.DOTALL,
        )
        m = pattern.search(text)
        if m:
            return m.group(1).strip()
    return ""


def scan_files(kb_root: Path, subdir: Path) -> list[Path]:
    target = kb_root / subdir
    if not target.exists():
        return []
    return sorted(target.glob("*.md"))


# ---------- 子命令实现 ----------


def cmd_count_mentions(args) -> dict:
    """扫摘要 + 专题，统计每个 [[实体]] 引用次数。

    返回结构：
      {
        "实体名": {
          "total": N,
          "from_summaries": [...],
          "from_topics": [...]
        }
      }
    """
    kb = Path(args.kb_root).expanduser().resolve()
    counter: dict[str, dict] = defaultdict(
        lambda: {"total": 0, "from_summaries": [], "from_topics": []}
    )

    for f in scan_files(kb, DIR_SUMMARIES):
        text = f.read_text(encoding="utf-8")
        for link in set(RE_LINK.findall(text)):
            counter[link]["total"] += 1
            counter[link]["from_summaries"].append(f.stem)

    for f in scan_files(kb, DIR_TOPICS):
        text = f.read_text(encoding="utf-8")
        for link in set(RE_LINK.findall(text)):
            counter[link]["total"] += 1
            counter[link]["from_topics"].append(f.stem)

    # 按 total 降序
    sorted_out = dict(sorted(counter.items(), key=lambda x: -x[1]["total"]))
    return {
        "version": SCRIPT_VERSION,
        "kb_root": str(kb),
        "total_entities": len(sorted_out),
        "mentions": sorted_out,
    }


def cmd_audit(args) -> dict:
    """对所有专题做健康检查，按 v3 模板规范。"""
    kb = Path(args.kb_root).expanduser().resolve()
    topics = scan_files(kb, DIR_TOPICS)
    summaries = scan_files(kb, DIR_SUMMARIES)

    summary_stems = {f.stem for f in summaries}
    topic_stems = {f.stem for f in topics}
    all_stems = summary_stems | topic_stems

    audit_rows = []
    issues_total = 0

    for f in topics:
        text = f.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        sections = get_h2_sections(text)
        sections_set = set(sections)

        kind = fm.get("entity_kind", "unknown")
        stage = fm.get("lifecycle_stage", "unknown")
        roles = fm.get("roles", "")

        issues = []

        # 检查 1：L1 硬骨架段
        if stage in ("L1", "L2", "unknown"):
            for hard in HARD_SECTIONS_L1:
                if hard not in sections_set:
                    issues.append(f"missing_hard_section:{hard}")

        # 检查 2：frontmatter 字段
        if not fm.get("entity_kind"):
            issues.append("missing_frontmatter:entity_kind")
        if not fm.get("lifecycle_stage"):
            issues.append("missing_frontmatter:lifecycle_stage")
        if not fm.get("roles") and kind in ("person", "org", "project"):
            issues.append("missing_frontmatter:roles")

        # 检查 3：每段是否含 [[]] 双链（事实带源原则）
        for sec in ("已确认事实", "Timeline", "被提到", "AI 推断"):
            body = get_section_body(text, sec)
            if body and not RE_LINK.search(body):
                issues.append(f"section_no_link:{sec}")

        # 检查 4：当前判断段是否标注"最后综合时间"
        synthesis = get_section_body(text, "当前判断") or get_section_body(text, "现状综合")
        if synthesis and "最后综合" not in synthesis and "Synthesis" not in synthesis:
            issues.append("synthesis_no_timestamp")

        # 检查 5：孤儿专题（没被任何摘要 + 其他专题引用）
        backlink_body = get_section_body(text, "被提到")
        if not RE_LINK.search(backlink_body):
            issues.append("orphan_no_backlinks")

        issues_total += len(issues)
        audit_rows.append({
            "file": f.name,
            "stem": f.stem,
            "entity_kind": kind,
            "lifecycle_stage": stage,
            "roles": roles,
            "section_count": len(sections),
            "issue_count": len(issues),
            "issues": issues,
        })

    # 检查 6：摘要里 [[]] 引用了不存在的专题（Unresolved Link）
    unresolved = []
    for f in summaries + topics:
        text = f.read_text(encoding="utf-8")
        for link in set(RE_LINK.findall(text)):
            if link not in all_stems:
                unresolved.append({"link": link, "from": f.stem})

    return {
        "version": SCRIPT_VERSION,
        "kb_root": str(kb),
        "total_topics": len(topics),
        "total_summaries": len(summaries),
        "total_issues": issues_total,
        "topic_audit": audit_rows,
        "unresolved_links": unresolved[:50],  # 截断避免过长
        "unresolved_total": len(unresolved),
    }


def cmd_staleness_check(args) -> dict:
    """扫最近 N 天新增/修改的摘要，对比所引用的专题文件 mtime。

    判定逻辑：
      - 收集最近 N 天有 mtime 变化的摘要文件
      - 提取每个摘要里所有 [[实体]] 引用
      - 对每个引用：如果对应专题文件存在且 mtime 早于摘要 mtime → staleness 警报
      - 如果引用的专题文件不存在但实体被引用 ≥3 次 → 应该建专题但没建

    输出：staleness 警报清单 + 应建未建清单
    """
    import time

    kb = Path(args.kb_root).expanduser().resolve()
    days = args.days
    cutoff = time.time() - days * 86400

    summaries = scan_files(kb, DIR_SUMMARIES)
    topics = scan_files(kb, DIR_TOPICS)
    topic_by_stem = {t.stem: t for t in topics}

    # 收集"近期"摘要
    recent_summaries = []
    for f in summaries:
        if f.stat().st_mtime >= cutoff:
            recent_summaries.append(f)

    staleness_alerts = []
    for sf in recent_summaries:
        sf_mtime = sf.stat().st_mtime
        text = sf.read_text(encoding="utf-8")
        for link in set(RE_LINK.findall(text)):
            if link in topic_by_stem:
                tf = topic_by_stem[link]
                if tf.stat().st_mtime < sf_mtime:
                    staleness_alerts.append({
                        "summary": sf.stem,
                        "summary_mtime": time.strftime(
                            "%Y-%m-%d %H:%M", time.localtime(sf_mtime)),
                        "stale_topic": link,
                        "topic_mtime": time.strftime(
                            "%Y-%m-%d %H:%M", time.localtime(tf.stat().st_mtime)),
                        "lag_hours": round((sf_mtime - tf.stat().st_mtime) / 3600, 1),
                    })

    # 统计未建但被引用 ≥3 次的实体
    summary_stems = {f.stem for f in summaries}
    mention_counter: Counter = Counter()
    for f in summaries + topics:
        text = f.read_text(encoding="utf-8")
        for link in set(RE_LINK.findall(text)):
            mention_counter[link] += 1

    should_create = []
    for link, cnt in mention_counter.most_common():
        # 过滤：(1) 已有专题；(2) 链接指向的是已存在的摘要文件本身
        if cnt >= 3 and link not in topic_by_stem and link not in summary_stems:
            should_create.append({
                "entity": link,
                "mention_count": cnt,
                "rule": "≥3 引用应建 L1 专题（专题 3 规则）",
            })

    return {
        "version": SCRIPT_VERSION,
        "kb_root": str(kb),
        "days_window": days,
        "recent_summaries_count": len(recent_summaries),
        "staleness_alerts_count": len(staleness_alerts),
        "staleness_alerts": staleness_alerts,
        "should_create_count": len(should_create),
        "should_create": should_create[:30],  # 截断
    }


def cmd_section_stats(args) -> dict:
    """按 entity_kind 分组统计段名出现频率，反哺软建议清单演化。"""
    kb = Path(args.kb_root).expanduser().resolve()
    topics = scan_files(kb, DIR_TOPICS)

    # {entity_kind: {section_name: count}}
    stats: dict[str, Counter] = defaultdict(Counter)
    kind_totals: Counter = Counter()

    for f in topics:
        text = f.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        kind = fm.get("entity_kind", "unknown")
        kind_totals[kind] += 1
        for sec in get_h2_sections(text):
            stats[kind][sec] += 1

    # 计算占比 + 给出"加/减"建议
    suggestions = []
    out: dict[str, dict] = {}
    for kind, sec_counter in stats.items():
        total = kind_totals[kind]
        if total == 0:
            continue
        out[kind] = {"total_topics": total, "sections": {}}
        for sec, cnt in sec_counter.most_common():
            ratio = cnt / total
            out[kind]["sections"][sec] = {
                "count": cnt,
                "ratio": round(ratio, 2),
            }
            recommended = RECOMMENDED_BY_KIND.get(kind, [])
            # 高频未在推荐清单 → 建议加入
            if (
                ratio >= 0.8
                and sec not in recommended
                and sec not in HARD_SECTIONS_L1
                and sec not in SOFT_SECTIONS_L2
            ):
                suggestions.append({
                    "action": "add_to_recommended",
                    "kind": kind,
                    "section": sec,
                    "ratio": round(ratio, 2),
                    "reason": f">= 80% {kind} 实体自发加了此段",
                })
        # 低频在推荐清单 → 建议移除
        for sec in RECOMMENDED_BY_KIND.get(kind, []):
            ratio = sec_counter.get(sec, 0) / total if total > 0 else 0
            if ratio < 0.2:
                suggestions.append({
                    "action": "remove_from_recommended",
                    "kind": kind,
                    "section": sec,
                    "ratio": round(ratio, 2),
                    "reason": f"< 20% {kind} 实体填了此段",
                })

    return {
        "version": SCRIPT_VERSION,
        "kb_root": str(kb),
        "stats_by_kind": out,
        "evolution_suggestions": suggestions,
    }


# ---------- main ----------


def main():
    parser = argparse.ArgumentParser(
        prog="template_lint.py",
        description="知识管家 · 专题模板健康检查（v3 规范）",
    )
    parser.add_argument(
        "--kb-root",
        required=True,
        help="知识管家根目录（如 ~/Documents/0-project/知识管家/CC版-KB/）",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("count-mentions", help="统计 [[实体]] 引用次数")
    sub.add_parser("audit", help="按 v3 规范健康检查所有专题")
    sub.add_parser("section-stats", help="按 entity_kind 统计段频率，反哺推荐清单演化")
    p_stale = sub.add_parser(
        "staleness-check",
        help="检查最近 N 天摘要 vs 专题 mtime —— 防止 wiki 退化成 RAG",
    )
    p_stale.add_argument("--days", type=int, default=7,
                        help="看最近多少天的摘要（默认 7）")

    args = parser.parse_args()

    if args.cmd == "count-mentions":
        result = cmd_count_mentions(args)
    elif args.cmd == "audit":
        result = cmd_audit(args)
    elif args.cmd == "section-stats":
        result = cmd_section_stats(args)
    elif args.cmd == "staleness-check":
        result = cmd_staleness_check(args)
    else:
        parser.error(f"unknown cmd: {args.cmd}")
        return

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
