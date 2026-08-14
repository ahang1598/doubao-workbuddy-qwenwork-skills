#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第一阶段静态检查：facts.json 事实表 + 分析草稿的一致性与措辞口径。

用法：
    python3 scripts/lint_analysis.py <分析草稿.md> work/<板块>_facts.json
    python3 scripts/lint_analysis.py work/<板块>_facts.json            # 只校验 facts.json
（两个文件顺序无关，按扩展名 .json / .md 自动识别。）

它做三件事：
  1. 校验 facts.json 结构与三级分级是否自洽（行情数字须一级、入选催化须一级/二级+可打开链接、
     二级须带限定措辞、三级不得作展示值），并复算回撤 / 单日涨跌 / 反弹 / 比值等派生数字。
  2. 若给了分析草稿，比对草稿正文：关键数字是否登记在 facts.json、绑定的二级 / 三级数据与
     推断是否用了限定措辞、期间口径是否一致；并检查第一阶段成品合同（核心 4 值、模块1
     四维度、模块2条数/日期、模块4/5字段完整）。
  3. 打印 [复算/信息]、[警告]、[错误] 给你订正的机会。

退出码：
    0：默认提醒模式不阻塞；正式第一阶段准出请加 --strict。
    1：加 --strict 且存在 [错误] 时。
    2：用法错误 / 无法读取 facts.json。

设计意图：上下文很长时指令遵循会下降，这道检查在写作期暴露事实表与正文口径问题；正式准出用 --strict。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import market_checks as mc  # noqa: E402


# ---- 正文措辞线索 ----
FACT_REF_RE = re.compile(r"\{fact:([A-Za-z0-9_.\-,\s]+)\}")
ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.\-]*$")
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
# 正文里的数值（百分比 / 金额 / 倍数 / 家数等），用于「展示数字是否登记」提示
NUMERIC_FACT_RE = re.compile(
    r"(?<![A-Za-z0-9])[-+＋−]?\d+(?:,\d{3})*(?:\.\d+)?\s*"
    r"(?:%|个百分点|亿元|亿|万元|万|元|倍|x|X|家|只|手|bp|bps)"
)
# 二级数据应出现的限定 / 归因措辞
ATTRIB_CUE_RE = re.compile(r"据|报道|报道称|estimate|估算|测算|机构|预计|预测|研报|或|可能|约|转引|一致预期")
# 不该用在二级 / 三级 / 推断上的确定性措辞
CERTAIN_RE = re.compile(r"确定|坐实|必然|无疑|证实|事实是|已达|铁定")
# 推断应有的限制语
INFER_CUE_RE = re.compile(r"可能|或许|指向|意味着|倾向|推断|预计|后续|若|如果|取决于|仍需|有望")
# 日期 / 期间
PERIOD_YEAR_RE = re.compile(r"(20\d{2})\s*年")
PERIOD_MD_RE = re.compile(r"(\d{1,2})\s*月\s*(\d{1,2})\s*日")
# 写作提示 / 模板说明泄漏到正文的高频短语
META_LEAK_RE = re.compile(
    r"按时间倒序|最新在最上|每条标题前显示|量化信息看表格|无对应个股.*填[\"“]?无|"
    r"其余事件.*继续|每组只给代表股|实际内容随分析结果变化|批注[:：]|"
    r"不要.*写个股数字|不得.*输出|本文件|本规则|模板"
)
MODULE_HEADING_RE = re.compile(r"^##\s+")
FIXED_CORE_METRICS = {
    "close_point": re.compile(r"收盘点位|当日收盘点位"),
    "daily_change": re.compile(r"当日涨跌幅"),
    "change_7d": re.compile(r"近\s*7\s*(?:个交易)?日涨跌幅"),
    "turnover_amount": re.compile(r"当日成交额"),
    "turnover_7d": re.compile(r"近\s*7\s*(?:个交易)?日(?:日均)?成交额|近\s*7\s*(?:个交易)?日.*?日均.*?成交额"),
    "pe_ttm": re.compile(r"PE\s*[\(（]?\s*TTM\s*[\)）]?|市盈率\s*[\(（]\s*TTM\s*[\)）]"),
}
DAILY_PAIR = {"daily_change", "turnover_amount"}
D7_PAIR = {"change_7d", "turnover_7d"}
REQUIRED_CORE = {"close_point", "pe_ttm"}
DIMENSION_ORDER = ["价格涨跌", "成交量能", "代表股表现", "估值位置"]
INTERNAL_SCORE_RE = re.compile(r"信息热度\s*[+\-＋－]\s*\d|行情热度\s*[+\-＋－]\s*\d|热度\s*(?:上调|下调)\s*\d")
REQUIRED_HEADINGS = [
    "## 直接回答",
    "## 现在有多热",
    "## 为什么涨 / 跌",
    "## 谁在动、谁没动",
    "## 接下来盯什么",
    "## 风险提示",
    "## 信息来源",
]
SECTION_ALIASES = {
    "模块1": ("现在有多热",),
    "模块2": ("为什么涨", "为什么跌", "为什么涨 / 跌"),
    "模块3": ("谁在动、谁没动",),
    "模块4": ("接下来盯什么",),
    "模块5": ("风险提示",),
    "模块6": ("信息来源",),
}
FIXED_CLOSING = '下一步是否为您生成飞书文档版？如果需要，请回复"生成飞书文档"。'
FIXED_RISK_NOTICE = "回答基于AI 生成，仅用于信息参考与研究辅助，不构成任何投资建议。股市有风险，请结合自身风险承受能力决策。"


def _meta_year(facts_obj):
    meta = facts_obj.get("meta") or {}
    for key in ("timestamp", "today", "as_of"):
        raw = str(meta.get(key) or "")
        m = re.search(r"(20\d{2})", raw)
        if m:
            return int(m.group(1))
    return None


def _meta_cutoff_date(facts_obj):
    meta = facts_obj.get("meta") or {}
    year = _meta_year(facts_obj)
    raw = str(meta.get("timestamp") or meta.get("as_of") or "")
    iso = re.search(r"(20\d{2})-(\d{1,2})-(\d{1,2})", raw)
    if iso:
        try:
            return date(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))
        except ValueError:
            return None
    md = PERIOD_MD_RE.search(raw)
    if md and year:
        try:
            return date(year, int(md.group(1)), int(md.group(2)))
        except ValueError:
            return None
    return None


def _date_from_md_token(text, facts_obj):
    year = _meta_year(facts_obj)
    m = PERIOD_MD_RE.search(text or "")
    if not (year and m):
        return None
    try:
        return date(year, int(m.group(1)), int(m.group(2)))
    except ValueError:
        return None


def _section_lines(lines, heading_key):
    keys = SECTION_ALIASES.get(heading_key, (heading_key,))
    start = None
    for i, raw in enumerate(lines):
        s = raw.strip()
        if MODULE_HEADING_RE.match(s) and any(k in s for k in keys):
            start = i + 1
            break
    if start is None:
        return []
    end = len(lines)
    for j in range(start, len(lines)):
        if MODULE_HEADING_RE.match(lines[j].strip()):
            end = j
            break
    return lines[start:end]


def _opening_lines(lines):
    end = len(lines)
    for i, raw in enumerate(lines):
        if MODULE_HEADING_RE.match(raw.strip()):
            end = i
            break
    return lines[:end]


def _opening_title_line(lines):
    for raw in _opening_lines(lines):
        s = raw.strip()
        if s.startswith("标题：") or s.startswith("标题:"):
            return s
    return ""


def _plain_cell(text):
    s = re.sub(r"<[^>]+>", "", text or "")
    s = re.sub(r"[*_`｜|：:·\s]", "", s)
    return s.strip()


def _module2_event_dates(lines, facts_obj):
    """Extract dated catalyst title lines from Module 2 in the chat draft."""
    year = _meta_year(facts_obj)
    if not year:
        return []
    in_module2 = False
    events = []
    for i, raw in enumerate(lines, start=1):
        s = raw.strip()
        if s.startswith("## "):
            if ("为什么涨" in s or "为什么跌" in s or "为什么涨 / 跌" in s):
                in_module2 = True
                continue
            if in_module2:
                break
        if not in_module2 or "信息来源" not in s:
            continue
        m = PERIOD_MD_RE.search(s)
        if not m:
            continue
        month, day = int(m.group(1)), int(m.group(2))
        try:
            events.append((date(year, month, day), i, s))
        except ValueError:
            continue
    return events


def check_module2_chronology(lines, facts_obj, errors):
    events = _module2_event_dates(lines, facts_obj)
    for prev, cur in zip(events, events[1:]):
        prev_date, prev_line, _prev_text = prev
        cur_date, cur_line, cur_text = cur
        if cur_date > prev_date:
            errors.append(
                f"L{cur_line}: 模块2 催化未按事件日倒序排列——{cur_date.month}月{cur_date.day}日"
                f" 出现在 {prev_date.month}月{prev_date.day}日 之后；请把最新事件放最上面：{cur_text[:80]}"
            )


def check_core_metric_contract(lines, errors):
    opening = "\n".join(_opening_lines(lines))
    if not opening.strip():
        return
    found = {name for name, pat in FIXED_CORE_METRICS.items() if pat.search(opening)}
    if len(found) != 4:
        errors.append(
            "开篇核心结论的展示值必须恰好 4 个，且字段名只能来自固定 6 个候选"
            "（收盘点位 / 当日涨跌幅 / 近7日涨跌幅 / 当日成交额 / 近7个交易日日均成交额 / 代表股 PE(TTM)）。"
            f" 当前识别到 {len(found)} 个：{', '.join(sorted(found)) or '无'}。"
        )
        return
    missing = REQUIRED_CORE - found
    if missing:
        errors.append("开篇核心结论缺少固定展示值：收盘点位与代表股 PE(TTM) 必须都出现。")
    has_daily = bool(DAILY_PAIR & found)
    has_d7 = bool(D7_PAIR & found)
    if has_daily and has_d7:
        errors.append("开篇核心结论展示值不得交叉混搭当日组与近7日组；除收盘点位和 PE(TTM) 外，两张可变卡只能二选一成对出现。")
    elif has_daily and DAILY_PAIR - found:
        errors.append("开篇核心结论选了当日组但不成对：当日涨跌幅与当日成交额必须同时出现。")
    elif has_d7 and D7_PAIR - found:
        errors.append("开篇核心结论选了近7日组但不成对：近7日涨跌幅与近7个交易日日均成交额必须同时出现。")
    elif not has_daily and not has_d7:
        errors.append("开篇核心结论除收盘点位与 PE(TTM) 外，还必须从当日组或近7日组中二选一补足两张展示值。")


def check_module1_dimensions(lines, errors):
    mod = _section_lines(lines, "模块1")
    if not mod:
        return
    table_dims = []
    for raw in mod:
        s = raw.strip()
        if "|" not in s or "---" in s or "维度" in s and "数值" in s:
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if not cells:
            continue
        first = _plain_cell(cells[0])
        if first in DIMENSION_ORDER:
            table_dims.append(first)
    if table_dims:
        if table_dims != DIMENSION_ORDER:
            errors.append(
                "模块1 四维度必须且只能按固定顺序出现："
                f"{' / '.join(DIMENSION_ORDER)}。当前表格识别为：{' / '.join(table_dims)}。"
            )
        return
    joined = "\n".join(mod)
    positions = []
    missing = []
    for dim in DIMENSION_ORDER:
        pos = joined.find(dim)
        if pos < 0:
            missing.append(dim)
        else:
            positions.append(pos)
    if missing:
        errors.append(f"模块1 缺少固定维度：{'、'.join(missing)}。模块1只能写价格涨跌 / 成交量能 / 代表股表现 / 估值位置四项。")
    elif positions != sorted(positions):
        errors.append(f"模块1 四维度顺序不对，必须为：{' / '.join(DIMENSION_ORDER)}。")


def check_module2_events(lines, facts_obj, warnings, errors):
    events = _module2_event_dates(lines, facts_obj)
    if not events:
        if _section_lines(lines, "模块2"):
            errors.append("模块2 未识别到带日期与“信息来源”的催化标题行；模块2必须精选 3-5 条、最多 6 条核心催化。")
        return
    if len(events) > 6:
        errors.append(f"模块2 催化最多 6 条，当前识别到 {len(events)} 条；请合并同一逻辑，保留最高等级原文。")
    elif len(events) < 3:
        errors.append(f"模块2 催化必须精选 3-5 条、最多 6 条，当前识别到 {len(events)} 条；若确实缺少合格催化，应补搜或重写归因，不得用不足量新闻准出。")
    cutoff = _meta_cutoff_date(facts_obj)
    if cutoff:
        for ev_date, line_no, text in events:
            if ev_date > cutoff:
                errors.append(
                    f"L{line_no}: 模块2 催化日期 {ev_date.month}月{ev_date.day}日 晚于行情数据截止日"
                    f" {cutoff.month}月{cutoff.day}日；截止日后新闻不能解释已收盘行情，应转入模块4后续验证。{text[:80]}"
                )


def _split_blocks_by_start(lines, start_re):
    blocks = []
    cur = None
    for raw in lines:
        if start_re.search(raw.strip()):
            if cur:
                blocks.append(cur)
            cur = [raw]
        elif cur is not None:
            cur.append(raw)
    if cur:
        blocks.append(cur)
    return blocks


def _has_field(block, field):
    pat = re.compile(rf"\*\*\s*{re.escape(field)}\s*\*\*\s*[：:]")
    return any(pat.search(x) for x in block)


def _field_nonempty(block, field):
    pat = re.compile(rf"\*\*\s*{re.escape(field)}\s*\*\*\s*[：:]\s*(.+)")
    for raw in block:
        m = pat.search(raw.strip())
        if m and m.group(1).strip():
            return True
    return False


def _dates_in_text(text, facts_obj):
    year = _meta_year(facts_obj)
    if not year:
        return []
    out = []
    for m in PERIOD_MD_RE.finditer(text or ""):
        try:
            out.append(date(year, int(m.group(1)), int(m.group(2))))
        except ValueError:
            pass
    return out


def check_module4_watch(lines, facts_obj, warnings, errors):
    mod = _section_lines(lines, "模块4")
    if not mod:
        return
    blocks = _split_blocks_by_start(mod, re.compile(r"📈?\s*\*\*\s*信号"))
    if not blocks:
        errors.append("模块4 未识别到 `📈 **信号N · 标签**：...` 结构；每条信号必须写 signal / watch / improve / worsen。")
        return
    if len(blocks) > 4:
        errors.append(f"模块4 盯盘信号最多 4 条，当前 {len(blocks)} 条；请合并同类变量。")
    elif len(blocks) < 3:
        errors.append(f"模块4 盯盘信号必须 3-4 条，当前 {len(blocks)} 条；请补足真正改变结论的未来验证变量，或合并后保持不少于 3 条。")
    cutoff = _meta_cutoff_date(facts_obj)
    for idx, block in enumerate(blocks, start=1):
        title = block[0].strip()
        if not re.search(r"[：:].+", title):
            errors.append(f"模块4 信号{idx} 标题冒号后缺少被观察变量：{title[:80]}")
        for field in ("盯", "改善", "恶化"):
            if not _has_field(block, field):
                errors.append(f"模块4 信号{idx} 缺少 `{field}` 字段。每条都必须写全信号 / 盯 / 改善 / 恶化。")
            elif not _field_nonempty(block, field):
                errors.append(f"模块4 信号{idx} 的 `{field}` 字段为空。")
        text = "\n".join(block)
        if INTERNAL_SCORE_RE.search(text):
            errors.append(f"模块4 信号{idx} 暴露了内部热度加减分语言；只写结论如何升级 / 转弱 / 失效。")
        if cutoff:
            for d in _dates_in_text(text, facts_obj):
                if d <= cutoff:
                    errors.append(
                        f"模块4 信号{idx} 出现不晚于数据截止日的具体日期 {d.month}月{d.day}日；"
                        "模块4只能盯尚未兑现 / 尚未验证的未来变量，已发生旧事应放模块2或改成后续验证条件。"
                    )


def check_module5_risks(lines, warnings, errors):
    mod = _section_lines(lines, "模块5")
    if not mod:
        return
    blocks = _split_blocks_by_start(mod, re.compile(r"⚠️?\s*\*\*\s*风险"))
    if not blocks:
        errors.append("模块5 未识别到 `⚠️ **风险N · 风险标题**` 结构；每条风险必须写标题 / 触发 / 证伪，触发段可合并说明影响机制。")
        return
    if len(blocks) < 2:
        warnings.append("模块5 当前只识别到 1 条风险；请确认是否足以覆盖会推翻主结论的主要情景。")
    for idx, block in enumerate(blocks, start=1):
        title = block[0].strip()
        if not re.search(r"风险\s*\d+\s*·\s*[^*]+", title):
            errors.append(f"模块5 风险{idx} 标题不完整，应写成 `⚠️ **风险N · <风险标题>**`：{title[:80]}")
        for field in ("触发", "证伪"):
            if not _has_field(block, field):
                errors.append(f"模块5 风险{idx} 缺少 `{field}` 字段。每条风险必须写全触发 / 证伪。")
            elif not _field_nonempty(block, field):
                errors.append(f"模块5 风险{idx} 的 `{field}` 字段为空。")


def check_outline_contract(lines, errors):
    nonempty = [x.strip() for x in lines if x.strip()]
    if not nonempty:
        errors.append("分析草稿为空。")
        return
    if nonempty[0] != FIXED_RISK_NOTICE:
        errors.append(f"第一阶段正文第一行必须逐字输出固定风险提醒：{FIXED_RISK_NOTICE}")
    first_content = next((x for x in nonempty[1:] if x != FIXED_RISK_NOTICE), "")
    if not first_content.startswith("目标概念板块："):
        errors.append("固定风险提醒后，开篇核心结论必须以 `目标概念板块：` 开头，并写明板块名称、代码、数据截止日、10股样本口径与综合热度。")
    title_line = _opening_title_line(lines)
    if not title_line:
        errors.append("开篇必须单独写一行 `标题：<一句话核心判断>`，用于映射飞书文档核心标题；不要从打分句里抽标题。")
    elif re.search(r"综合热度|信息热度|行情热度|[1-5]\s*/\s*5", title_line):
        errors.append("开篇 `标题：` 不应包含综合热度 / 信息热度 / 行情热度分数；打分已映射到飞书文档的综合热度和双轨表。")
    if FIXED_CLOSING not in nonempty[-1]:
        errors.append('正文最后必须逐字输出：下一步是否为您生成飞书文档版？如果需要，请回复"生成飞书文档"。')

    headings = [x.strip() for x in lines if x.strip().startswith("## ")]
    positions = []
    missing = []
    for h in REQUIRED_HEADINGS:
        try:
            positions.append(headings.index(h))
        except ValueError:
            missing.append(h)
    if missing:
        errors.append(f"正文缺少固定标题：{'、'.join(missing)}。")
    elif positions != sorted(positions):
        errors.append("正文标题顺序必须固定：直接回答 / 现在有多热 / 为什么涨 / 跌 / 谁在动、谁没动 / 接下来盯什么 / 风险提示 / 信息来源。")

    direct = "\n".join(_section_lines(lines, "直接回答"))
    for label in ("**问题**", "**结论**", "**下一步**"):
        if label not in direct:
            errors.append(f"直接回答缺少固定行：{label}。")

    for heading_key in ("模块1", "模块2", "模块3", "模块4", "模块5"):
        mod_lines = _section_lines(lines, heading_key)
        mod = "\n".join(mod_lines)
        if mod and "**本段结论：**" not in mod:
            errors.append(f"{heading_key} 开头必须写 `**本段结论：**...`。")
            continue


def check_chat_contract(lines, facts_obj, warnings, errors):
    check_outline_contract(lines, errors)
    check_core_metric_contract(lines, errors)
    check_module1_dimensions(lines, errors)
    check_module2_chronology(lines, facts_obj, errors)
    check_module2_events(lines, facts_obj, warnings, errors)
    check_module4_watch(lines, facts_obj, warnings, errors)
    check_module5_risks(lines, warnings, errors)


def load_json(path: Path):
    text = path.read_text(encoding="utf-8")
    s = text.strip()
    if s.startswith("{"):
        return json.loads(s)
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if m:
        return json.loads(m.group(1))
    raise ValueError(f"{path} 不含 JSON 对象")


def strip_inline_code(line: str) -> str:
    return INLINE_CODE_RE.sub("", line)


def strip_fact_refs(line: str) -> str:
    return FACT_REF_RE.sub("", line)


def parse_fact_refs(line: str):
    refs = []
    for grp in FACT_REF_RE.findall(line):
        for raw in grp.split(","):
            r = raw.strip()
            if r:
                refs.append(r)
    return refs


def collect_facts(obj):
    """facts.json 的 facts[] -> {id: fact}。"""
    out = {}
    for f in (obj.get("facts") or []):
        if isinstance(f, dict) and isinstance(f.get("id"), str) and ID_RE.fullmatch(f["id"]):
            out[f["id"]] = f
    return out


def detect_summary_facts_shape(obj):
    """Detect a common but invalid summary-style facts.json shape.

    Agents sometimes write a compact research note JSON with top-level keys such as
    sector_name/top_10_stocks/catalysts. It is valid JSON, but not the schema this
    lint can verify because the 10-stock recomputation components are missing.
    """
    if not isinstance(obj, dict) or isinstance(obj.get("meta"), dict):
        return None
    summary_keys = {
        "sector_name",
        "sector_code",
        "data_date",
        "sector_index",
        "representative_stock",
        "top_10_stocks",
        "group_counts",
        "scoring",
        "catalysts",
        "signals",
        "risks",
    }
    hit = sorted(k for k in summary_keys if k in obj)
    if len(hit) < 3:
        return None
    return (
        "facts.json 已成功读取，但当前是摘要型结构，不是本 skill 的可校验 facts schema。"
        f" 识别到顶层字段：{', '.join(hit[:8])}{'…' if len(hit) > 8 else ''}。"
        " 请改为顶层 `meta` / `stock_checks` / `divergence_groups` / `facts`："
        " `meta.selected_stocks` 恰好 10 只；`stock_checks` 逐股包含 change、turnover、"
        " change_7d、turnover_7d、d7_close_base、d7_close_t、d7_turnovers、role、select_reason；"
        " `facts` 登记展示数字与最终入选模块2催化。这个错误不是参数顺序问题。"
    )


def _tier(f):
    t = f.get("tier")
    if isinstance(t, bool):
        return None
    try:
        return int(t)
    except (TypeError, ValueError):
        return None


def _wlist(f, key):
    raw = f.get(key)
    if isinstance(raw, str):
        return [raw.strip()] if raw.strip() else []
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    return []


def is_numeric_line(line: str) -> bool:
    prose = strip_inline_code(strip_fact_refs(line))
    if not NUMERIC_FACT_RE.search(prose):
        return False
    # 表格分隔行不算
    if re.fullmatch(r"\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*", prose):
        return False
    return True


def check_line_against_facts(idx, line, facts, warnings):
    refs = parse_fact_refs(line)
    prose = strip_fact_refs(strip_inline_code(line))

    # 显式期间（用于 vs claim.period 对照）
    line_years = set(PERIOD_YEAR_RE.findall(line))

    for ref in refs:
        f = facts.get(ref)
        if f is None:
            warnings.append(f"L{idx}: 未知 fact 引用 `{ref}`——请在 facts.json 补登记或改正文。")
            continue
        tier = _tier(f)
        usage = str(f.get("usage_type") or "").strip()
        metric = str(f.get("metric") or "").strip()
        # 期间对照
        claim_period = str(f.get("period") or f.get("as_of") or "")
        cy = set(PERIOD_YEAR_RE.findall(claim_period))
        if line_years and cy and line_years.isdisjoint(cy):
            warnings.append(
                f"L{idx}: `{ref}` 期间口径复核——facts 登记 period/as_of={claim_period}，"
                f"正文显式年份为 {sorted(line_years)}；若在讲当前判断，请补当前期间事实或写明“据{claim_period}”。"
            )
        # 二级数据：须带限定 / 归因，不得确定性措辞
        if tier == 2:
            allowed = _wlist(f, "allowed_wording")
            ok = any(w in prose for w in allowed) if allowed else bool(ATTRIB_CUE_RE.search(prose))
            if not ok:
                sug = (_wlist(f, "suggested_wording") or [""])[0]
                tip = f"；建议改写：{sug}" if sug else ""
                warnings.append(
                    f"L{idx}: `{ref}`（{metric}）为二级数据，正文未见“据…/估算/报道/或/可能”等限定措辞{tip}"
                )
            if CERTAIN_RE.search(prose):
                warnings.append(f"L{idx}: `{ref}`（{metric}）为二级数据，却用了确定性措辞，请降级为“据…估算/可能”。")
        # 三级：不应绑定到展示值
        if tier == 3:
            warnings.append(
                f"L{idx}: `{ref}`（{metric}）为三级信息，不应作为展示数据绑定——请核验到一级/二级原文后引用更高级来源。"
            )
        # 推断：须有限制语、不得确定性
        if usage == "author_inference":
            if CERTAIN_RE.search(prose):
                warnings.append(f"L{idx}: `{ref}`（{metric}）是推断，却用了确定性措辞，请改“可能/指向/后续需验证”。")
            elif not INFER_CUE_RE.search(prose):
                warnings.append(f"L{idx}: `{ref}`（{metric}）是推断，建议加“可能/指向/后续验证”等限制语。")


def main(argv=None):
    ap = argparse.ArgumentParser(description="第一阶段 facts.json + 分析草稿静态检查。")
    ap.add_argument("paths", nargs="+", help="<分析草稿.md> 与 <facts.json>，顺序无关（按扩展名识别）")
    ap.add_argument("--strict", action="store_true", help="存在 [错误] 时返回退出码 1（默认不阻塞）")
    args = ap.parse_args(argv)

    facts_path = None
    md_path = None
    for p in args.paths:
        if p.lower().endswith(".json"):
            facts_path = Path(p)
        elif p.lower().endswith((".md", ".markdown", ".txt")):
            md_path = Path(p)
    if facts_path is None:
        print("[错误] 必须提供 facts.json（.json 文件）。用法: python3 lint_analysis.py <分析草稿.md> <facts.json>")
        return 2
    if not facts_path.exists():
        print(f"[错误] 找不到 facts.json: {facts_path}")
        return 2

    try:
        facts_obj = load_json(facts_path)
    except Exception as exc:  # noqa: BLE001
        print(f"[错误] 无法读取 facts.json: {exc}")
        return 2

    infos, warnings, errors = mc.facts_json_checks(facts_obj)
    shape_error = detect_summary_facts_shape(facts_obj)
    if shape_error:
        errors.insert(0, shape_error)

    # 草稿正文比对（可选）
    if md_path is not None and md_path.exists():
        lines = md_path.read_text(encoding="utf-8").splitlines()
        # 结构 / 深度槽位检查：只要提供了草稿就无条件运行，不受 facts[] 是否已登记影响。
        check_chat_contract(lines, facts_obj, warnings, errors)
        facts = collect_facts(facts_obj)
        if not facts:
            warnings.append("facts.json 无可用 facts 条目，跳过 {fact:id} 绑定与措辞核验（结构 / 深度槽位检查已照常运行）。")
        else:
            in_code = False
            in_sources = False
            n_refs = 0
            for i, raw in enumerate(lines, start=1):
                s = raw.strip()
                if s.startswith("```") or s.startswith("~~~"):
                    in_code = not in_code
                    continue
                if in_code:
                    continue
                if s.startswith("## ") and ("信息来源" in s or "数据来源" in s):
                    in_sources = True
                elif s.startswith("## "):
                    in_sources = False
                refs = parse_fact_refs(raw)
                n_refs += len(refs)
                if refs:
                    check_line_against_facts(i, raw, facts, warnings)
                if META_LEAK_RE.search(s):
                    warnings.append(
                        f"L{i}: 疑似把写作提示 / 模板说明输出进正文，请改成真实分析内容或删除：{s[:80]}"
                    )
            infos.append(f"草稿绑定 {{fact:…}} 共 {n_refs} 处；facts.json 登记 {len(facts)} 条事实")
    elif md_path is not None:
        warnings.append(f"找不到分析草稿: {md_path}（已跳过草稿比对，仅校验 facts.json）")
    else:
        infos.append("未提供分析草稿，仅校验 facts.json 结构 / 分级 / 复算。可加 <分析草稿.md> 一并比对正文措辞。")

    for m in infos:
        print(f"[复算/信息] {m}")
    for m in warnings:
        print(f"[警告] {m}")
    for m in errors:
        print(f"[错误] {m}")
    print(f"汇总: {len(errors)} 错误, {len(warnings)} 警告, {len(infos)} 条复算/信息")
    if errors:
        if args.strict:
            print("（严格模式：标 [错误] 者需先修正，本次返回失败。）")
        else:
            print("（提醒模式未加 --strict；正式第一阶段准出请加 --strict，标 [错误] 者需先修正。）")
        print("修复纪律：请先完整读完所有错误，再读 references/facts_schema.md 的“lint 会查什么 / 第一阶段错误速查”；只有 lane / 字段名 / 嵌套 source / 摘要结构等机械问题才运行 `python3 scripts/repair_facts.py <facts.json>`。修复或回填原始字段后运行 `python3 scripts/derive_facts.py <facts.json>` 统一生成涨跌、近7日日均成交额和四组；缺真实行情字段、7日序列、role/select_reason 或 facts[] 时直接回填数据，不要重新生成整份 facts.json。")

    if args.strict and errors:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
