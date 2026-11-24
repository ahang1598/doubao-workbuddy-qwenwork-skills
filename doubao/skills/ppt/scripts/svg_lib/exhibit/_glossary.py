"""Reader-facing glossary for research decks: industry abbreviations / units get a one-line definition the first time
they appear in the deck (page footnote), and the whole list goes into an appendix page at the end.

frame(...) calls footnote_terms(...) for business-research pages; glossary_rows(cwd, deck) returns every term the
deck has explained, for text_table on the appendix page."""

from __future__ import annotations

import json
import re
from pathlib import Path

# term → definition (shown as "CAGR = 年均复合增长率"). Units carry their size in plain words.
TERMS = {
    "CAGR": "年均复合增长率",
    "YoY": "同比增长",
    "QoQ": "环比增长",
    "pt": "百分点，比率之间的差（如 30%→32% 为 +2pt）",
    "pp": "百分点，比率之间的差",
    "bp": "基点，0.01 个百分点",
    "GW": "吉瓦，功率单位，1 GW = 100 万千瓦",
    "GWh": "吉瓦时，电量 / 储能容量单位，1 GWh = 100 万千瓦时",
    "MW": "兆瓦，功率单位，1 MW = 1000 千瓦",
    "MWh": "兆瓦时，电量单位",
    "TWh": "太瓦时，1 TWh = 10 亿千瓦时",
    "kWh": "千瓦时，即 1 度电",
    "Wh": "瓦时，电量单位（元/Wh 即每瓦时的价格）",
    "Ah": "安时，电芯容量单位（314Ah 指单颗电芯容量）",
    "PE": "市盈率，股价 ÷ 每股收益",
    "PB": "市净率，股价 ÷ 每股净资产",
    "PS": "市销率，市值 ÷ 营业收入",
    "EV/EBITDA": "企业价值倍数，(市值 + 净负债) ÷ 息税折旧摊销前利润",
    "EBITDA": "息税折旧摊销前利润",
    "EPS": "每股收益",
    "ROE": "净资产收益率，净利润 ÷ 净资产",
    "ROA": "总资产收益率",
    "ROIC": "投入资本回报率",
    "TTM": "最近 12 个月滚动口径",
    "DCF": "现金流折现估值",
    "WACC": "加权平均资本成本，DCF 的折现率",
    "FCF": "自由现金流",
    "capex": "资本开支",
    "Capex": "资本开支",
    "CR3": "行业前 3 名的合计份额",
    "CR5": "行业前 5 名的合计份额",
    "CR10": "行业前 10 名的合计份额",
    "ASP": "平均售价",
    "GMV": "成交总额",
    "ARPU": "每用户平均收入",
    "SKU": "单品 / 货号",
    "LFP": "磷酸铁锂电池",
    "OEM": "代工生产",
    "ODM": "原始设计制造",
    "OBM": "自有品牌制造",
    "CXO": "医药研发 / 生产外包服务",
    "CDMO": "医药定制研发生产外包",
    "IPO": "首次公开发行",
    "SSS": "同店销售增长",
    "SSSG": "同店销售增长",
    "GAAP": "公认会计准则口径",
    "OPM": "营业利润率",
    "JV": "合资公司",
    "BOM": "物料清单（整机由哪些零部件构成及其成本）",
    "eVTOL": "电动垂直起降飞行器",
    "NIM": "净息差，生息资产收益率 − 付息负债成本率",
    "NPL": "不良贷款率",
    "AUM": "管理资产规模",
    "ROI": "投资回报率",
    "LTV": "用户生命周期价值",
    "CAC": "获客成本",
    "DTC": "直面消费者（自营渠道）",
    "MNC": "跨国药企",
    "FIC": "同类首创药物",
    "BIC": "同类最优药物",
    "ADC": "抗体偶联药物",
    "NBV": "新业务价值，当年新卖保单未来利润的现值，衡量寿险增长质量",
    "NBV margin": "新业务价值率，NBV ÷ 首年保费，越高说明卖的保单越赚钱",
    "VONB": "新业务价值（友邦等港股险企的叫法，同 NBV）",
    "PEV": "股价 ÷ 每股内含价值，寿险股常用估值倍数，<1 表示市值低于内含价值",
    "CSM": "合同服务边际，新准则下尚未释放的未来保单利润",
    "COR": "综合成本率，(赔付 + 费用) ÷ 保费，<100% 说明承保赚钱",
    "BVPS": "每股净资产",
    "RoEV": "内含价值回报率，当年 EV 增长 ÷ 期初 EV",
    "DPS": "每股分红",
    "PEG": "市盈率 ÷ 盈利增速，<1 常被视为估值相对增速便宜",
    "IRR": "内部收益率，使投资现金流现值为零的回报率",
    "NPV": "净现值，未来现金流折现后减去投资额",
    "BEP": "盈亏平衡点，收入刚好覆盖全部成本的销量或时点",
    "Payback": "回本期，累计现金流转正所需时间",
    "TAM": "总可服务市场规模",
    "SAM": "可触达市场规模",
    "SOM": "可获得的市场份额规模",
    "NPS": "净推荐值，推荐者占比 − 贬损者占比，衡量客户口碑",
    "ARR": "年化经常性收入",
    "NRR": "净收入留存率，老客户今年付费 ÷ 去年付费，>100% 说明老客户在扩容",
    "GRR": "毛收入留存率，不算增购的老客户收入留存",
    "Churn": "客户流失率",
    "UE": "单位经济模型（单店 / 单客的收入与成本）",
    "EBIT": "息税前利润",
    "GPM": "毛利率",
    "NPM": "净利率",
    "DSO": "应收账款周转天数",
    "DIO": "存货周转天数",
    "CCC": "现金转换周期，存货天数 + 应收天数 − 应付天数",
    "BOPIS": "线上下单、门店自提",
    "1H": "上半年", "2H": "下半年",
    "E": "年份后的 E 表示预测值（如 2026E）",
}

# English definitions for English decks (lang="en"); a term missing here gets no footnote on an English page.
TERMS_EN = {
    "CAGR": "compound annual growth rate", "YoY": "year-on-year change", "QoQ": "quarter-on-quarter change",
    "pt": "percentage point (30% → 32% is +2pt)", "pp": "percentage point", "bp": "basis point, 0.01 percentage point",
    "PE": "price-to-earnings ratio", "PB": "price-to-book ratio", "PS": "price-to-sales ratio",
    "EV/EBITDA": "enterprise value ÷ EBITDA", "EBITDA": "earnings before interest, taxes, depreciation and amortisation",
    "EPS": "earnings per share", "ROE": "return on equity", "ROA": "return on assets", "ROIC": "return on invested capital",
    "TTM": "trailing twelve months", "DCF": "discounted cash flow valuation", "WACC": "weighted average cost of capital",
    "FCF": "free cash flow", "capex": "capital expenditure", "Capex": "capital expenditure",
    "ASP": "average selling price", "GMV": "gross merchandise value", "ARPU": "average revenue per user",
    "SKU": "stock-keeping unit (one product item)", "OEM": "original equipment manufacturing",
    "ODM": "original design manufacturing", "IPO": "initial public offering", "SSS": "same-store sales growth",
    "SSSG": "same-store sales growth", "GAAP": "generally accepted accounting principles", "OPM": "operating profit margin",
    "JV": "joint venture", "BOM": "bill of materials", "AUM": "assets under management", "ROI": "return on investment",
    "LTV": "customer lifetime value", "CAC": "customer acquisition cost", "DTC": "direct-to-consumer",
    "NPS": "net promoter score: promoters minus detractors", "IRR": "internal rate of return", "NPV": "net present value",
    "TAM": "total addressable market", "SAM": "serviceable addressable market", "ARR": "annual recurring revenue",
    "NRR": "net revenue retention (>100% means existing customers spend more)", "GRR": "gross revenue retention",
    "EBIT": "earnings before interest and taxes", "PEG": "PE ÷ earnings growth rate", "DPS": "dividend per share",
    "BVPS": "book value per share", "CCC": "cash conversion cycle", "BEP": "break-even point",
    "COR": "combined ratio: (claims + expenses) ÷ premiums; below 100% means underwriting profit",
    "NBV": "new business value: present value of future profits on policies sold in the year",
    "PEV": "price ÷ embedded value per share", "CSM": "contractual service margin (unearned future policy profit)",
    "NIM": "net interest margin", "NPL": "non-performing loan ratio", "KA": "key accounts",
    "1H": "first half", "2H": "second half", "E": "E after a year marks a forecast (e.g. 2026E)",
}

# ambiguous abbreviations: term → [(context regex, definition), …]. The sense whose regex hits the page text most
# (then the whole deck's visible text) wins; a tie or no hit at all leaves the term unexplained (better none than wrong).
# A term listed here may still keep a TERMS entry: that one is used only through SENSE_DEFAULT.
_PHARMA = r"药|临床|靶点|授权|License|licen[cs]e|MNC|首付|里程碑|抗体|ADC|肿瘤|适应症|管线|生物|III\s*期|FDA|NMPA"
_BATTERY = r"电池|储能|GWh|MWh|电芯|锂|充放电|BESS|逆变|光伏|电网"
SENSES = {
    "BMS": [(_PHARMA, "百时美施贵宝（Bristol-Myers Squibb，美国跨国药企）"), (_BATTERY, "电池管理系统")],
    "BD": [(_PHARMA, "对外授权与合作交易（Business Development，药企授权 / 并购）"),
           (r"拓客|商务|渠道|销售|客户|签约|招商", "商务拓展")],
    "PCS": [(_BATTERY, "储能变流器（电池与电网之间的交直流转换设备）")],
    "EMS": [(_BATTERY + r"|能源|能耗|负荷", "能量管理系统"),
            (r"代工|组装|SMT|PCB|电子制造|ODM|OEM|消费电子|富士康", "电子制造服务（代工组装）")],
    "IP": [(r"潮玩|盲盒|手办|角色|形象|动漫|影视|联名|授权|毛绒|周边|游戏|内容|文创|衍生品", "知识产权 / 形象角色（可授权的角色、品牌或内容）"),
           (r"芯片|半导体|EDA|SoC|晶圆|流片|IP\s*核", "芯片设计中可授权复用的功能模块（IP 核）")],
    "KA": [(r"渠道|零售|商超|连锁|经销|门店|卖场|终端|铺货", "重点大客户 / 大型连锁渠道（Key Account）"),
           (r"大客户|政企|销售团队|客户经理|B\s*端", "重点大客户（Key Account）")],
    "EV": [(r"寿险|保险|保单|NBV|PEV|内含价值|险企|代理人", "内含价值，寿险公司净资产 + 存量保单未来利润现值"),
           (r"电动车|新能源车|整车|充电|电池|销量|车型|汽车", "纯电动汽车")],
    "PE": [(r"私募|LP|GP|募资|股权投资|VC|基金管理|投资机构", "私募股权投资"),
           (r"倍|估值|市盈|TTM|EPS|PB|股价|分位", "市盈率，股价 ÷ 每股收益")],
}
SENSE_DEFAULT = {"PE": "市盈率，股价 ÷ 每股收益"}   # ambiguous terms that still get a definition when nothing decides


def _pick_sense(term, *contexts):
    """Definition of an ambiguous term from the first context that decides (most regex hits, no tie); else the
    SENSE_DEFAULT entry or None."""
    for ctx in contexts:
        if not ctx:
            continue
        ctx = _term_re().sub(lambda m: " " if m.group(1) == term else m.group(0), ctx)   # the term itself is no evidence
        hits = sorted(((len(re.findall(rx, ctx, re.I)), d) for rx, d in SENSES[term]), key=lambda x: -x[0])
        if hits and hits[0][0] > 0 and (len(hits) == 1 or hits[0][0] > hits[1][0]):
            return hits[0][1]
    return SENSE_DEFAULT.get(term)


def define(term, text="", deck_text="", lang="zh"):
    """Reader-facing definition of a glossary term in this context (page text, then the whole deck); None when an
    ambiguous term cannot be decided. lang="en": the English definition (None when there is none)."""
    if lang == "en":
        return TERMS_EN.get(term)
    if term in SENSES:
        return _pick_sense(term, text, deck_text)
    return TERMS.get(term)


# jargon the model coins or borrows from sell-side shorthand: never a reader-facing label
INHOUSE = re.compile(r"守正(?!创新)|出奇制胜|卫星(?:仓位|配置|组合)|卫星\s*[|｜]|核心仓|进攻仓|防守仓|左侧布局|右侧布局|"
                     r"戴维斯双击|杀估值|杀业绩|胜率赔率|α\s*标的|β\s*标的|弹性标的|底仓|长坡厚雪|中枢重估|干净可比|卖铲人|博弹性|"
                     r"组合拳|抢占心智|用户心智|打法闭环|抓手|赋能|三驾马车")

_TERM_RE = None


def _term_re():
    global _TERM_RE
    if _TERM_RE is None:
        keys = sorted((k for k in set(TERMS) | set(SENSES) if len(k) >= 2 or k in ("E",)), key=len, reverse=True)
        keys = [k for k in keys if k not in ("E", "1H", "2H")]
        _TERM_RE = re.compile(r"(?<![A-Za-z])(" + "|".join(re.escape(k) for k in keys) + r")(?![A-Za-z])")
    return _TERM_RE


def terms_in(text):
    """Glossary terms appearing in visible text, in first-appearance order (2026E-style forecast years count as 'E')."""
    found = []
    for m in _term_re().finditer(text or ""):
        k = m.group(1)
        k = "Capex" if k == "capex" else k
        if k not in found:
            found.append(k)
    if re.search(r"(?<!\d)20\d{2}E(?![A-Za-z])", text or "") and "E" not in found:
        found.append("E")
    return found


def _ledger(cwd, deck):
    return Path(cwd or ".") / ".lark-slides" / f"glossary-{deck}.json"


def _load(cwd, deck):
    try:
        return json.loads(_ledger(cwd, deck).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def footnote_terms(text, cwd, deck, page, limit=3, lang=None):
    """Terms on this page that no earlier page of the deck has explained (a rewritten page keeps its own). Records them
    for this page. Returns [(term, definition)] — at most `limit` (the rest wait for the next page / the appendix)."""
    if not (deck and page is not None):
        return []
    if lang is None:
        lang = "en" if not re.search(r"[\u4e00-\u9fff]", text or "") else "zh"
    led = _load(cwd, deck)
    key = str(int(page))
    earlier = {t for p, ts in led.items() if p.isdigit() and int(p) < int(page) for t in ts}
    deck_text = None
    defs = dict(led.get("_defs") or {})
    mine = []
    for t in terms_in(text):
        if t in earlier or len(mine) >= limit:
            continue
        d = define(t, text, lang=lang)
        if d is None and t in SENSES and lang != "en":   # the page alone does not decide: the rest of the deck may
            if deck_text is None:
                deck_text = _deck_text(cwd, deck)
            d = define(t, "", deck_text)
        if d is None:
            continue   # ambiguous and undecidable: no footnote (a wrong one is worse)
        defs[t] = d
        mine.append(t)
    led[key] = mine
    led["_defs"] = defs
    try:
        f = _ledger(cwd, deck)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(led, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass
    return [(t, defs[t]) for t in mine]


def _deck_text(cwd, deck):
    """Visible text of every written page of the deck (pagetext ledger), for deciding ambiguous terms."""
    try:
        led = json.loads((Path(cwd or ".") / ".lark-slides" / f"pagetext-{deck}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    return " ".join(str(v) for k, v in led.items() if str(k).isdigit())


def footnote_line(pairs, lang="zh"):
    if not pairs:
        return ""
    if lang != "zh":
        return "Terms: " + "; ".join(f"{t} = {d}" for t, d in pairs)
    return "术语：" + "；".join(f"{t} = {d}" for t, d in pairs)


def glossary_rows(cwd, deck, extra_text="", lang="zh"):
    """[[term, definition]] of every term the deck explained (plus terms in extra_text), for the appendix table."""
    led = _load(cwd, deck)
    defs = dict(led.get("_defs") or {})
    seen = []
    for p, ts in sorted(((k, v) for k, v in led.items() if k.isdigit()), key=lambda kv: int(kv[0])):
        for t in ts:
            if t not in seen:
                seen.append(t)
    for t in terms_in(extra_text):
        if t not in seen:
            seen.append(t)
    rows = []
    for t in seen:
        d = (define(t, lang="en") if lang == "en" else
             defs.get(t) or define(t, extra_text, _deck_text(cwd, deck) if t in SENSES else ""))
        if d:
            rows.append([t, d])
    return rows


def inhouse_jargon(text):
    """Coined / insider shorthand on reader-facing text ("守正 / 卫星", "戴维斯双击"): [words]."""
    return list(dict.fromkeys(m.group(0) for m in INHOUSE.finditer(text or "")))


def record_sources(cwd, deck, page, names):
    """Remember the source names a page cites (frame calls this), for the appendix source list."""
    f = Path(cwd or ".") / ".lark-slides" / f"sources-{deck}.json"
    try:
        led = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        led = {}
    led[str(int(page))] = [n for n in names if n and not re.fullmatch(r"(?:来源|资料来源|Source)\s*[:：]?\s*", n)]
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(led, ensure_ascii=False), encoding="utf-8")


def source_rows(cwd, deck, page_of=None, lang="zh"):
    """[[source, pages]] of every source the deck's pages cited (team analysis last), in first-citation order."""
    f = Path(cwd or ".") / ".lark-slides" / f"sources-{deck}.json"
    try:
        led = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    seen = {}
    for p, ns in sorted(led.items(), key=lambda kv: int(kv[0]) if kv[0].isdigit() else 0):
        if page_of is not None and p == str(page_of):
            continue
        for n in ns:
            import html as _html
            n = _html.unescape(re.sub(r"^(?:来源|资料来源|Source)\s*[:：]\s*", "", n)).strip()
            if n and not re.fullmatch(r"团队(?:分析|整理|测算)|team analysis", n, re.I):
                if p not in seen.setdefault(n, []):
                    seen[n].append(p)
    sep = "、P" if lang == "zh" else ", P"
    return [[n, "P" + sep.join(ps[:6]) + ("…" if len(ps) > 6 else "")] for n, ps in seen.items()]


def glossary_page(f, cwd=None, deck=None, extra_text="", palette=None, sources=True):
    """Last appendix page "术语与来源": left the terms the deck explained in its footnotes (plus terms in extra_text),
    right every source the deck's pages cited with the pages that use it (sources=False: terms only, two columns).
    Write it after every other page. Returns xml for f.publish(xml, ...)."""
    from ._frame import text_table, _resolve_deck, project_root
    cwd = project_root(cwd)
    deck = _resolve_deck(deck, cwd)
    zh_ = bool(re.search(r"[\u4e00-\u9fff]", getattr(f, "title", "") or ""))
    rows = glossary_rows(cwd, deck, extra_text, lang="zh" if zh_ else "en")
    if not rows:
        raise ValueError("glossary_page：本 deck 还没有任何页解释过术语（页脚'术语：'行由 frame 自动生成）——"
                         "在其他页都写完后再做这一页，或传 extra_text=全稿标题文本")
    zh = (getattr(f, "title", "") or "") and any("一" <= ch <= "鿿" for ch in f.title)
    srcs = source_rows(cwd, deck, getattr(f, "page_no", None), lang="zh" if zh_ else "en") if sources else []
    if srcs:   # terms left, sources right (each half of the body)
        mid = f.left + (f.right - f.left) / 2
        n_t, n_s = min(len(rows), 9), min(len(srcs), 9)
        if len(rows) > n_t or len(srcs) > n_s:   # the rest goes to the speaker notes (one page, readable rows)
            more = [f"{t}：{d}" for t, d in rows[n_t:]] + [f"{n}（{p}）" for n, p in srcs[n_s:]]
            f.note = ((f.note + "\n") if getattr(f, "note", None) else "") + (
                "其余术语与来源：" + "；".join(more) if zh_ else "Other terms and sources: " + "; ".join(more))
        xml1, _ = text_table(f.left, f.top, mid - f.left - 14, ["术语", "含义"] if zh else ["Term", "Meaning"], rows[:n_t],
                             widths=[0.22, 0.78], palette=palette, size=12, h=f.bottom - f.top)
        head2 = ["数据来源", "用于"] if zh else ["Source", "Pages"]
        w2 = f.right - mid - 14
        # the pages column fits its longest page list on one line at the largest size text_table may grow to (16pt;
        # rows wrap at 90 % of the box, plus the column gap) — a narrow column wraps "P4、P12、P18" or overflows. It
        # takes at most a third of the table (source names need the room); a longer list keeps its first pages + "…"
        from ._text import tw

        def _need(t, bold=False):
            return tw(str(t), 16, bold=bold) / 0.9 + 14
        frac_max = 1 / 3
        sep_ = "、" if zh_ else ", "
        srcs = [list(r) for r in srcs]
        for r in srcs[:n_s]:
            ps, cut = str(r[1]).rstrip("…").split(sep_), str(r[1]).endswith("…")
            while len(ps) > 1 and _need(sep_.join(ps) + ("…" if cut else "")) > w2 * frac_max:
                ps, cut = ps[:-1], True
            r[1] = sep_.join(ps) + ("…" if cut else "")
        need = max([_need(p_) for _, p_ in srcs[:n_s]] + [_need(head2[1], True)])
        frac = min(max(need / w2, 0.18), frac_max)
        xml2, _ = text_table(mid + 14, f.top, w2, head2, srcs[:n_s], widths=[1 - frac, frac], palette=palette,
                             size=12, h=f.bottom - f.top)
        return xml1 + xml2
    half = (len(rows) + 1) // 2
    mid = f.left + (f.right - f.left) / 2
    head = ["术语", "含义"] if zh else ["Term", "Meaning"]
    xml1, _ = text_table(f.left, f.top, mid - f.left - 14, head, rows[:half], widths=[0.22, 0.78], palette=palette,
                         size=12, h=f.bottom - f.top)
    out = xml1
    if rows[half:]:
        xml2, _ = text_table(mid + 14, f.top, f.right - mid - 14, head, rows[half:], widths=[0.22, 0.78],
                             palette=palette, size=12, h=f.bottom - f.top)
        out += xml2
    return out
