#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从第一阶段 facts.json + 分析草稿.md 生成第二阶段 doc.md 中间产物。

doc.md 不是自由写作 Markdown，而是带 YAML front matter 的结构化文档：
- front matter 存放飞书文档顶部元数据
- 各 section 存放与 payload 语义等价的结构化块

这样做的目的不是发明一套通用 Markdown 解析器，而是把第二阶段的中间层
从 `payload.json` 换成一个更可读、可人工检查的 `doc.md`。
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from hydrate_payload_from_facts import hydrate

FIXED_RISK_NOTICE = "回答基于AI 生成，仅用于信息参考与研究辅助，不构成任何投资建议。股市有风险，请结合自身风险承受能力决策。"
DOC_META_KEYS = [
    "sector",
    "market",
    "timestamp",
    "index_caliber",
    "selected_stocks",
    "data_mode",
    "composite_score",
    "gauge_pill",
    "info_score",
    "market_score",
]
DOC_SECTION_ORDER = [
    "headline",
    "summary",
    "key_chips",
    "divergence",
    "answer",
    "section_summaries",
    "dimensions",
    "catalysts",
    "stocks",
    "divergence_groups",
    "watch_signals",
    "risks",
    "sources",
    "_facts_hydration",
]
GROUP_ORDER = ["放量上攻", "缩量上行", "缩量回调", "放量杀跌"]
DIMENSION_ORDER = ["价格涨跌", "成交量能", "代表股表现", "估值位置"]
RANK_WORDS = {1: "冷清", 2: "温和", 3: "活跃", 4: "高热", 5: "过热"}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _section(text: str, heading: str, next_heading: str | None = None) -> str:
    m = re.search(rf"^##\s*{re.escape(heading)}\s*$", text, re.M)
    if not m:
        return ""
    start = m.end()
    if next_heading:
        n = re.search(rf"^##\s*{re.escape(next_heading)}\s*$", text[start:], re.M)
        end = start + n.start() if n else len(text)
        return text[start:end].strip()
    return text[start:].strip()


def _opening_lines(chat_text: str) -> list[str]:
    lines = chat_text.splitlines()
    out: list[str] = []
    for line in lines:
        if line.strip().startswith("## "):
            break
        if line.strip() == FIXED_RISK_NOTICE:
            continue
        out.append(line.rstrip())
    return out


def _first_match(pattern: str, text: str) -> str:
    m = re.search(pattern, text, re.M)
    return m.group(1).strip() if m else ""


def _parse_opening(chat_text: str, facts: dict[str, Any]) -> dict[str, Any]:
    opening_lines = _opening_lines(chat_text)
    opening = "\n".join(opening_lines)
    non_empty = [line.strip() for line in opening_lines if line.strip()]

    meta_line = next((line for line in non_empty if line.startswith("目标概念板块：")), "")
    title = _first_match(r"^标题[：:]\s*(.+)$", opening)

    summary = ""
    key_line = ""
    stocks_line = ""
    title_idx = next((i for i, line in enumerate(non_empty) if line.startswith("标题：") or line.startswith("标题:")), -1)
    for idx in range(title_idx + 1, len(non_empty)):
        line = non_empty[idx]
        if line.startswith("收盘点位："):
            key_line = line
            if idx + 1 < len(non_empty) and non_empty[idx + 1].startswith("本次选取的 10 只代表股："):
                stocks_line = non_empty[idx + 1]
            break
        summary = (summary + "\n" + line).strip() if summary else line

    score_match = re.search(r"综合热度\s*(\d)\s*/\s*5（([^）]+)）", meta_line)
    composite_score = int(score_match.group(1)) if score_match else 0
    gauge_pill = score_match.group(2).strip() if score_match else ""

    meta = facts.get("meta") or {}
    sector_checks = facts.get("sector_checks") or {}
    today = str(meta.get("today") or sector_checks.get("as_of") or str(meta.get("timestamp") or "")[:10]).strip()

    sector = str(meta.get("sector") or "").strip()
    index_caliber = str(meta.get("index_caliber") or "").strip()
    if not sector and meta_line:
        sm = re.search(r"目标概念板块：([^（(；;]+)", meta_line)
        sector = sm.group(1).strip() if sm else ""
    if not index_caliber:
        im = re.search(r"目标概念板块：(.+?)；", meta_line)
        index_caliber = im.group(1).strip() if im else sector

    return {
        "meta_line": meta_line,
        "headline": title,
        "summary": summary.strip(),
        "key_line": key_line.rstrip("。"),
        "stocks_line": stocks_line,
        "sector": sector,
        "index_caliber": index_caliber,
        "timestamp": today,
        "composite_score": composite_score,
        "gauge_pill": gauge_pill or RANK_WORDS.get(composite_score, ""),
    }


def _infer_market(facts: dict[str, Any]) -> str:
    for item in facts.get("stock_checks") or []:
        evidence = str(item.get("evidence") or "")
        if re.search(r"\((?:60|68|00|30)\d{4}\)", evidence):
            return "A股"
        if re.search(r"\((?:HK|0)\d{4,5}\)", evidence, re.I):
            return "港股"
        if re.search(r"\([A-Z]{1,5}\)", evidence):
            return "美股"
    return "A股"


def _parse_key_chips(line: str, facts: dict[str, Any]) -> list[dict[str, Any]]:
    if not line:
        return []
    parts = [seg.strip().rstrip("。") for seg in re.split(r"[；;]", line) if seg.strip()]
    as_of = str((facts.get("sector_checks") or {}).get("as_of") or (facts.get("meta") or {}).get("today") or "")
    chips: list[dict[str, Any]] = []
    for part in parts:
        if "：" not in part and ":" not in part:
            continue
        label, value = re.split(r"[：:]", part, maxsplit=1)
        label = label.strip()
        value = value.strip()
        metric_key = ""
        color = ""
        unit = ""
        if "收盘点位" in label:
            metric_key = "close_point"
            unit = "点"
        elif "PE(TTM)" in label:
            metric_key = "pe_ttm"
            unit = "倍"
        elif "近7日涨跌幅" in label:
            metric_key = "change_7d"
            unit = "%"
        elif "当日涨跌幅" in label:
            metric_key = "daily_change"
            unit = "%"
        elif "近7个交易日日均成交额" in label:
            metric_key = "turnover_7d"
            unit = "亿"
        elif "当日成交额" in label:
            metric_key = "turnover_amount"
            unit = "亿"
        if value.startswith("+"):
            color = "up"
        elif value.startswith("-"):
            color = "down"
        chips.append(
            {
                "label": label,
                "value": value,
                "unit": unit,
                "metric_key": metric_key,
                "color": color,
                "source": {"lane": "seed_finance_search", "as_of": as_of},
            }
        )
    return chips


def _extract_section_summary(section_text: str) -> str:
    m = re.search(r"\*\*本段结论：\*\*\s*(.+?)(?=\n\s*(?:\||###|-\s+\*\*|📈|⚠️)|\Z)", section_text, re.S)
    if not m:
        return ""
    return re.sub(r"\s+", " ", m.group(1)).strip()


def _parse_direct_answer(section_text: str) -> dict[str, str]:
    restate = ""
    for line in section_text.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("**问题**"):
            break
        restate = (restate + "\n" + s).strip() if restate else s
    def get(label: str) -> str:
        return _first_match(rf"\*\*{re.escape(label)}\*\*[：:]\s*(.+)", section_text)
    return {
        "restate": restate,
        "conclusion": get("结论"),
        "next": get("下一步"),
    }


def _parse_dimensions(section_text: str) -> list[dict[str, Any]]:
    rows = []
    for line in section_text.splitlines():
        s = line.strip()
        if not s.startswith("|") or s.startswith("|---"):
            continue
        cells = [cell.strip() for cell in s.strip("|").split("|")]
        if len(cells) != 4 or cells[0] == "维度":
            continue
        rows.append(cells)
    dims: list[dict[str, Any]] = []
    for name, value, state, read in rows:
        dims.append(
            {
                "name": name,
                "track": "行情",
                "value": value,
                "state": state,
                "read": read,
                "source": {"lane": "seed_finance_search"},
            }
        )
    if [d.get("name") for d in dims] != DIMENSION_ORDER:
        dims.sort(key=lambda item: DIMENSION_ORDER.index(item["name"]) if item["name"] in DIMENSION_ORDER else 99)
    return dims


def _normalize_date_text(text: str) -> str:
    raw = str(text or "").strip()
    m = re.search(r"(\d{4})[-/年.](\d{1,2})[-/月.](\d{1,2})", raw)
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = re.search(r"(\d{1,2})月(\d{1,2})日", raw)
    if m:
        return f"{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    return raw


def _parse_sources(section_text: str) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for line in section_text.splitlines():
        s = line.strip().lstrip("-* ").strip()
        if not s or s.startswith("下一步"):
            continue
        if "：" not in s and ":" not in s:
            continue
        name, rest = re.split(r"[：:]", s, maxsplit=1)
        parts = [p.strip() for p in re.split(r"[，,]", rest) if p.strip()]
        title = parts[0] if parts else ""
        date = ""
        url = ""
        for part in parts[1:]:
            if part.startswith("http://") or part.startswith("https://"):
                url = part
            elif re.search(r"20\d{2}[-/]\d{2}[-/]\d{2}", part):
                date = part
        out.append({"name": name.strip(), "title": title, "date": date, "url": url})
    return out


def _infer_catalyst_tone(text: str) -> str:
    bad = ("利空", "下跌", "收缩", "风险", "拖累", "回落", "出逃", "承压")
    if any(word in text for word in bad):
        return "利空"
    neutral = ("中性", "观察", "待定")
    if any(word in text for word in neutral):
        return "中性"
    return "利好"


def _infer_catalyst_category(title: str, fact: str) -> str:
    text = f"{title} {fact}"
    if any(word in text for word in ("规划", "政策", "发改委", "能源局", "工信部", "标准", "导则", "监管")):
        return "政策"
    if any(word in text for word in ("装机", "订单", "出货", "价格", "产能", "组件", "硅料", "硅片")):
        return "产业"
    if any(word in text for word in ("合作", "实验室", "大会", "论坛")):
        return "事件"
    return "中性"


def _source_by_name_and_date(sources: list[dict[str, str]], name: str, date_text: str) -> dict[str, str]:
    norm_date = _normalize_date_text(date_text)
    for src in sources:
        if src.get("name") == name and _normalize_date_text(src.get("date", "")) == norm_date:
            return src
    month_day = re.search(r"(\d{1,2})月(\d{1,2})日", date_text)
    if month_day:
        mm, dd = int(month_day.group(1)), int(month_day.group(2))
        for src in sources:
            dm = re.search(r"20\d{2}-(\d{2})-(\d{2})", str(src.get("date") or ""))
            if src.get("name") == name and dm and int(dm.group(1)) == mm and int(dm.group(2)) == dd:
                return src
    for src in sources:
        if src.get("name") == name:
            return src
    return {}


def _parse_catalysts(section_text: str, sources: list[dict[str, str]]) -> list[dict[str, Any]]:
    pat = re.compile(
        r"^###\s*(?P<date>\d{1,2}月\d{1,2}日)｜信息来源：(?P<source>[^｜]+)｜(?P<title>[^\n]+)\n"
        r"\*\*事实\*\*[：:]\s*(?P<fact>.+?)\n"
        r"🔗\s*\*\*为什么重要\*\*[：:]\s*(?P<why>.+?)\n"
        r"🔍\s*\*\*后续验证\*\*[：:]\s*(?P<verify>.+?)(?=\n### |\Z)",
        re.M | re.S,
    )
    out: list[dict[str, Any]] = []
    for m in pat.finditer(section_text):
        title = re.sub(r"\s+", " ", m.group("title")).strip()
        fact = re.sub(r"\s+", " ", m.group("fact")).strip()
        why = re.sub(r"\s+", " ", m.group("why")).strip()
        verify = re.sub(r"\s+", " ", m.group("verify")).strip()
        source_name = m.group("source").strip()
        source_ref = _source_by_name_and_date(sources, source_name, m.group("date"))
        out.append(
            {
                "date": m.group("date"),
                "tone": _infer_catalyst_tone(f"{title} {fact}"),
                "category": _infer_catalyst_category(title, fact),
                "source_name": source_name,
                "title": title,
                "fact": fact,
                "url": source_ref.get("url", ""),
                "why": why,
                "verify": verify,
                "source": {"lane": "general_search", "tier": 2, "level": "二级"},
            }
        )
    return out


def _parse_watch_signals(section_text: str, today: str) -> list[dict[str, Any]]:
    pat = re.compile(
        r"📈\s*\*\*信号(?P<idx>\d+)(?:\s*·\s*(?P<tag>[^*：:]+))?\*\*[：:]\s*(?P<signal>.+?)\n"
        r"\*\*盯\*\*[：:]\s*(?P<watch>.+?)\n"
        r"\*\*改善\*\*[：:]\s*(?P<improve>.+?)\n"
        r"\*\*恶化\*\*[：:]\s*(?P<worsen>.+?)(?=\n📈|\Z)",
        re.S,
    )
    out: list[dict[str, Any]] = []
    for m in pat.finditer(section_text):
        watch = re.sub(r"\s+", " ", m.group("watch")).strip()
        event_date = ""
        dm = re.search(r"(20\d{2}[-/年]\d{1,2}[-/月]\d{1,2})", watch)
        if dm:
            event_date = dm.group(1).replace("年", "-").replace("月", "-").replace("日", "")
            if event_date <= today:
                event_date = ""
        out.append(
            {
                "tag": (m.group("tag") or "").strip(),
                "signal": re.sub(r"\s+", " ", m.group("signal")).strip(),
                "watch": watch,
                "improve": re.sub(r"\s+", " ", m.group("improve")).strip(),
                "worsen": re.sub(r"\s+", " ", m.group("worsen")).strip(),
                "event_date": event_date,
            }
        )
    return out


def _split_risk_trigger_and_why(raw: str) -> tuple[str, str]:
    text = re.sub(r"\s+", " ", raw).strip()
    for sep in ("；", ";"):
        if sep in text:
            left, right = text.split(sep, 1)
            return left.strip(), right.strip()
    return text, text


def _parse_risks(section_text: str) -> list[dict[str, Any]]:
    pat = re.compile(
        r"⚠️\s*\*\*风险(?P<idx>\d+)\s*·\s*(?P<title>[^*]+)\*\*\n"
        r"\*\*触发\*\*[：:]\s*(?P<trigger>.+?)\n"
        r"\*\*证伪\*\*[：:]\s*(?P<invalidate>.+?)(?=\n⚠️|\Z)",
        re.S,
    )
    out: list[dict[str, Any]] = []
    for m in pat.finditer(section_text):
        trigger_text = re.sub(r"\s+", " ", m.group("trigger")).strip()
        trigger, why = _split_risk_trigger_and_why(trigger_text)
        out.append(
            {
                "title": m.group("title").strip(),
                "trigger": trigger,
                "why": why,
                "invalidate": re.sub(r"\s+", " ", m.group("invalidate")).strip(),
            }
        )
    return out


def _market_score_from_dimensions(dimensions: list[dict[str, Any]]) -> int:
    confirms = sum(1 for d in dimensions if d.get("state") == "确认")
    weaks = sum(1 for d in dimensions if d.get("state") == "弱确认")
    if confirms >= 4:
        return 5
    if confirms >= 3:
        return 4
    if confirms >= 2 or (confirms == 1 and weaks >= 2):
        return 3 if confirms >= 2 else 2
    if confirms == 1 or weaks >= 2:
        return 2
    return 1


def _info_score_from_catalysts(catalysts: list[dict[str, Any]]) -> int:
    weight = 0.0
    for item in catalysts:
        tier = int(((item.get("source") or {}).get("tier") or 2))
        weight += 1.0 if tier == 1 else 0.75
    if weight >= 4.5:
        return 4
    if weight >= 2.5:
        return 3
    if weight >= 1.0:
        return 2
    return 1


def _divergence_type(info_score: int, market_score: int) -> str:
    if info_score >= 3 and market_score >= 3:
        return "双热 · 强趋势共振"
    if info_score >= 3 and market_score < 3:
        return "信息热 · 行情冷"
    if info_score < 3 and market_score >= 3:
        return "行情热 · 信息冷"
    return "双冷 · 低关注"


def _divergence_pill_label(info_score: int, market_score: int) -> tuple[str, str]:
    if info_score >= 3 and market_score >= 3:
        return "双轨偏热", "信息与行情共振，市场关注度高且资金参与积极"
    if info_score >= 3 and market_score < 3:
        return "信息领先", "政策/消息面热度领先于价格表现，预期走在行情前面"
    if info_score < 3 and market_score >= 3:
        return "行情领先", "价格/成交热度领先于信息面，可能存在纯资金驱动"
    return "双轨偏冷", "信息面与行情面均低迷，板块处于低关注状态"


def _build_doc_payload(facts: dict[str, Any], chat_text: str) -> dict[str, Any]:
    opening = _parse_opening(chat_text, facts)
    direct = _section(chat_text, "直接回答", "现在有多热")
    heat = _section(chat_text, "现在有多热", "为什么涨 / 跌")
    catalysts_text = _section(chat_text, "为什么涨 / 跌", "谁在动、谁没动")
    divergence_text = _section(chat_text, "谁在动、谁没动", "接下来盯什么")
    watch_text = _section(chat_text, "接下来盯什么", "风险提示")
    risks_text = _section(chat_text, "风险提示", "信息来源")
    sources_text = _section(chat_text, "信息来源", None)

    sources = _parse_sources(sources_text)
    dimensions = _parse_dimensions(heat)
    catalysts = _parse_catalysts(catalysts_text, sources)
    market_score = _market_score_from_dimensions(dimensions)
    info_score = _info_score_from_catalysts(catalysts)
    divergence_type = _divergence_type(info_score, market_score)
    pill_label, pill_meaning = _divergence_pill_label(info_score, market_score)
    answer = _parse_direct_answer(direct)

    payload: dict[str, Any] = {
        "sector": opening["sector"],
        "market": _infer_market(facts),
        "timestamp": opening["timestamp"],
        "index_caliber": opening["index_caliber"],
        "selected_stocks": list((facts.get("meta") or {}).get("selected_stocks") or []),
        "data_mode": str((facts.get("meta") or {}).get("data_mode") or "full"),
        "composite_score": opening["composite_score"] or max(1, min(5, round(0.55 * market_score + 0.45 * info_score))),
        "gauge_pill": opening["gauge_pill"] or RANK_WORDS.get(opening["composite_score"] or 0, ""),
        "info_score": info_score,
        "market_score": market_score,
        "headline": opening["headline"],
        "summary": opening["summary"],
        "key_chips": _parse_key_chips(opening["key_line"], facts),
        "divergence": {
            "type": divergence_type,
            "pill": pill_label,
            "verdict": answer.get("conclusion", ""),
            "meaning": opening["summary"] or pill_meaning,
        },
        "answer": answer,
        "section_summaries": {
            "heat": _extract_section_summary(heat),
            "catalysts": _extract_section_summary(catalysts_text),
            "divergence": _extract_section_summary(divergence_text),
            "watch": _extract_section_summary(watch_text),
            "risks": _extract_section_summary(risks_text),
        },
        "dimensions": dimensions,
        "catalysts": catalysts,
        "stocks": [],
        "divergence_groups": {group: {"stocks": [], "feature": ""} for group in GROUP_ORDER},
        "watch_signals": _parse_watch_signals(watch_text, opening["timestamp"]),
        "risks": _parse_risks(risks_text),
        "sources": sources,
    }

    hydrated, _warnings = hydrate(facts, payload, chat_text)
    return hydrated


def _yaml_scalar(value: Any) -> str:
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps("" if value is None else str(value), ensure_ascii=False)


def dump_doc_markdown(doc: dict[str, Any], path: Path) -> None:
    lines = ["---"]
    for key in DOC_META_KEYS:
        value = doc.get(key)
        if key == "selected_stocks":
            lines.append(f"{key}:")
            for item in value or []:
                lines.append(f"  - {json.dumps(str(item), ensure_ascii=False)}")
        else:
            lines.append(f"{key}: {_yaml_scalar(value)}")
    lines.append("---")
    lines.append("")

    for key in DOC_SECTION_ORDER:
        lines.append(f"## {key}")
        value = doc.get(key)
        if key in {"headline", "summary"}:
            lines.append(str(value or "").strip())
        else:
            lines.append("```json")
            lines.append(json.dumps(value, ensure_ascii=False, indent=2))
            lines.append("```")
        lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    m = re.match(r"^---\n(.*?)\n---\n?", text, re.S)
    if not m:
        raise ValueError("doc.md 缺少 YAML front matter。")
    raw = m.group(1)
    body = text[m.end():]
    meta: dict[str, Any] = {}
    current_list_key = ""
    for line in raw.splitlines():
        if re.match(r"^\s*-\s+", line) and current_list_key:
            meta.setdefault(current_list_key, []).append(json.loads(line.split("-", 1)[1].strip()))
            continue
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        key = key.strip()
        val = val.strip()
        if not val:
            meta[key] = []
            current_list_key = key
            continue
        current_list_key = ""
        if val.startswith('"') or val.startswith("'"):
            meta[key] = json.loads(val)
        elif re.fullmatch(r"-?\d+", val):
            meta[key] = int(val)
        elif re.fullmatch(r"-?\d+\.\d+", val):
            meta[key] = float(val)
        else:
            meta[key] = val
    return meta, body


def load_doc_markdown(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    meta, body = _parse_frontmatter(text)
    out = dict(meta)
    for idx, key in enumerate(DOC_SECTION_ORDER):
        pat = re.compile(rf"^##\s*{re.escape(key)}\s*$", re.M)
        m = pat.search(body)
        if not m:
            continue
        start = m.end()
        n = re.compile(r"^##\s+", re.M).search(body, start)
        raw = body[start:n.start() if n else len(body)].strip()
        if key in {"headline", "summary"}:
            out[key] = raw.strip()
            continue
        code = re.search(r"```json\s*(.*?)\s*```", raw, re.S)
        if not code:
            raise ValueError(f"section `{key}` 缺少 JSON 代码块。")
        out[key] = json.loads(code.group(1))
    return out


def infer_output_path(facts_path: Path) -> Path:
    stem = facts_path.stem
    if stem.endswith("_facts"):
        stem = stem[: -len("_facts")]
    return facts_path.with_name(stem + "_doc.md")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="从 facts.json + 分析草稿.md 生成飞书文档中间 doc.md。")
    ap.add_argument("facts_json", help="第一阶段 facts.json")
    ap.add_argument("chat_md", help="第一阶段分析草稿 .md")
    ap.add_argument("-o", "--output", help="输出 doc.md 路径")
    args = ap.parse_args(argv)

    facts_path = Path(args.facts_json)
    chat_path = Path(args.chat_md)
    out_path = Path(args.output) if args.output else infer_output_path(facts_path)
    facts = load_json(facts_path)
    chat_text = read_text(chat_path)
    doc = _build_doc_payload(facts, chat_text)
    dump_doc_markdown(doc, out_path)
    print(f"[信息] 已生成 doc.md: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
