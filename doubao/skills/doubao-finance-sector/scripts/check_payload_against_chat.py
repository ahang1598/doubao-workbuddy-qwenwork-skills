#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查飞书文档 payload 是否从第一阶段 chat 正文原句搬运而来。

用法：
    python3 scripts/check_payload_against_chat.py work/<板块>_分析草稿.md work/<板块>_payload.json

本脚本只做内容搬运一致性检查，不复算行情、不判断来源分级。
原则：payload 文本必须是第一阶段正文对应模块里的连续原文片段；找不到就回第一阶段补正文。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


SECTION_KEYS = {
    "direct": "直接回答",
    "heat": "现在有多热",
    "catalysts": "为什么涨",
    "divergence": "谁在动、谁没动",
    "watch": "接下来盯什么",
    "risks": "风险提示",
    "sources": "信息来源",
}
FIXED_RISK_NOTICE = "回答基于AI 生成，仅用于信息参考与研究辅助，不构成任何投资建议。股市有风险，请结合自身风险承受能力决策。"


def _strip_md(text: str) -> str:
    s = re.sub(r"<[^>]+>", "", text or "")
    s = re.sub(r"\{fact:[^}]+\}", "", s)
    s = re.sub(r"```.*?```", "", s, flags=re.S)
    s = re.sub(r"[*_`#>\-|]+", "", s)
    return s


def _norm(text: str) -> str:
    s = _strip_md(str(text or "")).lower()
    return re.sub(r"[^0-9a-z\u4e00-\u9fff%]+", "", s)


def _supported(value: str, context: str) -> bool:
    nv = _norm(value)
    if len(nv) < 6:
        return True
    nc = _norm(context)
    return nv in nc


def _section(lines: list[str], key: str) -> str:
    start = None
    for i, raw in enumerate(lines):
        s = raw.strip()
        if s.startswith("## ") and key in s:
            start = i + 1
            break
    if start is None:
        return ""
    end = len(lines)
    for j in range(start, len(lines)):
        if lines[j].strip().startswith("## "):
            end = j
            break
    return "\n".join(lines[start:end])


def _opening(lines: list[str]) -> str:
    end = len(lines)
    for i, raw in enumerate(lines):
        if raw.strip().startswith("## "):
            end = i
            break
    opening_lines = [line for line in lines[:end] if line.strip() != FIXED_RISK_NOTICE]
    return "\n".join(opening_lines)


def _opening_title(lines: list[str]) -> str:
    for raw in _opening(lines).splitlines():
        s = raw.strip()
        if s.startswith("标题：") or s.startswith("标题:"):
            return re.sub(r"^标题[：:]\s*", "", s).strip()
    return ""


def _load_json(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    return json.loads(text)


def _check_text(label: str, value: str, context: str, errors: list[str]) -> None:
    if not str(value or "").strip():
        errors.append(f"{label} 为空，无法映射到 chat。")
        return
    if FIXED_RISK_NOTICE in str(value):
        errors.append(f"{label} 不得搬运第一阶段固定风险提醒；飞书文档模板使用内置免责声明。")
        return
    if not _supported(str(value), context):
        errors.append(f"{label} 不是第一阶段正文对应模块中的连续原文片段；请从 chat 原句搬运，不要压缩、改写或在飞书文档阶段新增判断。")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="检查 payload 文本是否从第一阶段 chat 正文映射。")
    ap.add_argument("chat_md", help="第一阶段分析草稿 .md")
    ap.add_argument("payload_json", help="飞书文档 payload.json")
    args = ap.parse_args(argv)

    chat_path = Path(args.chat_md)
    payload_path = Path(args.payload_json)
    if not chat_path.exists():
        print(f"[错误] 找不到第一阶段分析草稿: {chat_path}")
        return 2
    if not payload_path.exists():
        print(f"[错误] 找不到 payload.json: {payload_path}")
        return 2

    lines = chat_path.read_text(encoding="utf-8").splitlines()
    payload = _load_json(payload_path)
    sections = {name: _section(lines, key) for name, key in SECTION_KEYS.items()}
    opening = _opening(lines)
    whole = "\n".join(line for line in lines if line.strip() != FIXED_RISK_NOTICE)
    errors: list[str] = []
    infos: list[str] = []

    if not opening.strip():
        errors.append("chat 开篇核心结论为空，无法映射飞书文档核心结论。")
    for name, text in sections.items():
        if name != "sources" and not text.strip():
            errors.append(f"chat 缺少对应模块内容：{SECTION_KEYS[name]}。")

    hero_context = opening + "\n" + sections.get("direct", "")
    title_text = _opening_title(lines)
    if not title_text:
        errors.append("chat 开篇缺少 `标题：...`，无法稳定映射 payload.headline 到飞书文档标题。")
    if payload.get("headline"):
        if title_text:
            _check_text("headline", str(payload.get("headline")), title_text, errors)
        else:
            _check_text("headline", str(payload.get("headline")), hero_context, errors)
        if re.search(r"综合热度|信息热度|行情热度|[1-5]\s*/\s*5", str(payload.get("headline"))):
            errors.append("headline 不应包含综合热度 / 信息热度 / 行情热度分数；打分已由飞书文档的综合热度和双轨表表达。")
    if payload.get("summary"):
        _check_text("summary", str(payload.get("summary")), hero_context, errors)

    answer = payload.get("answer") if isinstance(payload.get("answer"), dict) else {}
    for key in ("restate", "conclusion", "next"):
        if answer.get(key):
            _check_text(f"answer.{key}", str(answer.get(key)), sections.get("direct", ""), errors)
    if answer.get("status"):
        errors.append("answer.status 已废弃；直接回答统一为 answer.restate / answer.conclusion / answer.next（三项分别对应问题 / 结论 / 下一步）。")

    summary_map = {
        "heat": "heat",
        "catalysts": "catalysts",
        "divergence": "divergence",
        "watch": "watch",
        "risks": "risks",
    }
    summaries = payload.get("section_summaries") if isinstance(payload.get("section_summaries"), dict) else {}
    for key, sec in summary_map.items():
        _check_text(f"section_summaries.{key}", str(summaries.get(key) or ""), sections.get(sec, ""), errors)

    for i, d in enumerate(payload.get("dimensions") or []):
        if isinstance(d, dict):
            _check_text(f"dimensions[{i}].value", str(d.get("value") or ""), sections.get("heat", ""), errors)
            _check_text(f"dimensions[{i}].read", str(d.get("read") or ""), sections.get("heat", ""), errors)

    for i, c in enumerate(payload.get("catalysts") or []):
        if not isinstance(c, dict):
            continue
        ctx = sections.get("catalysts", "")
        for key in ("title", "fact", "why", "verify"):
            _check_text(f"catalysts[{i}].{key}", str(c.get(key) or ""), ctx, errors)

    for i, w in enumerate(payload.get("watch_signals") or []):
        if not isinstance(w, dict):
            continue
        ctx = sections.get("watch", "")
        for key in ("signal", "watch", "improve", "worsen"):
            _check_text(f"watch_signals[{i}].{key}", str(w.get(key) or ""), ctx, errors)

    for i, r in enumerate(payload.get("risks") or []):
        if not isinstance(r, dict):
            continue
        ctx = sections.get("risks", "")
        for key in ("title", "trigger", "why", "invalidate"):
            _check_text(f"risks[{i}].{key}", str(r.get(key) or ""), ctx, errors)

    groups = payload.get("divergence_groups") if isinstance(payload.get("divergence_groups"), dict) else {}
    for group_name in ("放量上攻", "缩量上行", "缩量回调", "放量杀跌"):
        g = groups.get(group_name) if isinstance(groups.get(group_name), dict) else {}
        feature = str(g.get("feature") or "")
        if feature and feature not in ("无。", "本期无此类个股。"):
            _check_text(f"divergence_groups.{group_name}.feature", feature, sections.get("divergence", ""), errors)
    if isinstance(groups, dict) and groups.get("meaning"):
        _check_text("divergence_groups.meaning", str(groups.get("meaning")), sections.get("divergence", ""), errors)

    for i, s in enumerate(payload.get("sources") or []):
        if isinstance(s, dict) and s.get("name"):
            _check_text(f"sources[{i}].name", str(s.get("name")), whole, errors)

    if not errors:
        infos.append("payload 文本映射检查通过：飞书文档内容均可在第一阶段 chat 中找到连续原文片段。")

    for msg in infos:
        print(f"[信息] {msg}")
    for msg in errors:
        print(f"[错误] {msg}")
    if errors:
        print(f"汇总: {len(errors)} 错误。请回到第一阶段 chat 补足内容，或把 payload 改为从 chat 原句搬运。")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
