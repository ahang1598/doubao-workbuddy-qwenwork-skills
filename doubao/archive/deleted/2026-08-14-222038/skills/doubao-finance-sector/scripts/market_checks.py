# -*- coding: utf-8 -*-
"""市场数据复算与事实表校验（板块 skill 的数据真实性内核）。

本模块把**能从原始分量复算出来的财务 / 股票数字真的算一遍**，用「分量 → 复算值 vs
登记值」的对账，把凭印象编造、却又内部对不上的数字挡在出图之前；并按三级可信度对
每条事实的来源与措辞做一致性校验。被 lint_analysis.py、check_market_facts.py、
validate_doc_payload.py 共用。

主要输出（调用方决定是报错还是打印）：
  - recompute(p)            -> list[str]            复算明细（[复算/信息]），写作阶段唯一允许的衍生数字来源
  - hard_checks(p)          -> list[str]            硬错误：复算对不上、量纲越界、登记值与展示值打架
  - registry_checks(p)      -> (errors, warnings)   payload 的 numeric_facts 事实表结构、来源分级与「展示数值是否登记/溯源」
  - fact_tier_issues(f,...) -> (errors, warnings)   单条事实的三级分级 / 措辞 / 来源一致性（facts.json 与 payload 通用）
  - facts_json_checks(obj)  -> (infos,warn,errors)  整份 facts.json（meta + stock_checks + groups + facts）的结构、分级与复算

设计原则（避免误杀）：
  * 所有硬检查**只在 typed 分量齐全时触发**；分量缺失最多给一条 warning，绝不报错。
  * 复算对账带容差（默认 0.6 个百分点或 6% 相对，取大者），吸收四舍五入与盘中/收盘口径的微小差。
  * 不解析正文 prose 里的任意数字（易误杀）——要被复算的数字请以 typed 分量登记到
    numeric_facts / facts.json，或在 dimensions / key_chips / stocks 上挂结构化分量字段。
"""
from __future__ import annotations

import math
import re

# 两个搜索工具对应的来源 lane 取值（与 validate_doc_payload.py 一致）
_LANE_FINANCE = "seed_finance_search"
_LANE_GENERAL = "general_search"
_VALID_LANES = {_LANE_FINANCE, _LANE_GENERAL}

# 三级可信度与行情类 kind（行情数字必须一级、催化只许一级 / 二级）
_TIER_VALID = {1, 2, 3}
_MARKET_KINDS = {"market", "change", "retracement", "rebound", "ratio"}
_FIRSTHAND_LEVELS = {"一手", "权威"}
_AGGREGATOR_CATALYST_URL_KEYS = (
    "toutiao.com", "m.toutiao.com", "weibo.com", "m.weibo.cn",
    "baijiahao.baidu.com", "mbd.baidu.com", "xueqiu.com", "eastmoney.com", "guba.eastmoney.com",
)
_SUSPECT_CATALYST_URL_KEYS = (
    "sohu.com/a/", "qq.com/rain/a/", "c.m.163.com", "m.163.com/news",
    "sina.com.cn/wm/", "t.m.youth.cn/transfer/", "transfer/index/url",
    "mp.weixin.qq.com",
)
_PLATFORM_SOURCE_KEYS = (
    "东方财富", "eastmoney", "同花顺", "10jqka", "雪球", "xueqiu",
    "今日头条", "微博", "weibo",
)
_TIER3_CATALYST_SOURCE_KEYS = (
    "股吧", "贴吧", "论坛", "头条号", "百家号", "大鱼号",
    "自媒体", "博主", "个人专栏", "@",
)
_PERSONAL_SOURCE_KEYS = (
    "个人", "作者", "博主", "达人", "号主", "自媒体", "专栏作者", "个人专栏",
    "头条号", "百家号", "大鱼号", "公众号作者", "@",
)
_INSTITUTIONAL_SOURCE_KEYS = (
    "新华社", "中新社", "中国新闻社", "人民日报", "财联社", "证券时报", "上海证券报", "中国证券报",
    "第一财经", "界面新闻", "华尔街见闻", "财新", "21世纪经济报道", "证券日报", "光明网",
    "新京报", "中国经济网", "中国青年网", "中国旅游报", "海外网", "羊城晚报", "北京商报",
    "澎湃新闻", "路透", "彭博",
)
_INSTITUTION_AUTHOR_TYPES = {
    "机构", "机构号", "机构账号", "机构媒体", "新闻机构", "媒体机构", "媒体", "新闻媒体", "新闻网站", "机构报道",
    "上市公司", "公司号", "行业协会", "第三方机构", "券商", "券商号", "官方号", "官方账号",
    "media", "institution", "institution_account", "institutional_account", "official", "official_account",
    "mainstream_media", "official_news_agency", "industry_data", "industry_association", "news_website",
    "institutional_media", "listed_company", "company_account", "broker", "brokerage", "third_party_institution",
}

# 复算对账容差：绝对 0.6 个百分点 与 相对 6% 取大者
_TOL_ABS_PCT = 0.6
_TOL_REL = 0.06

# 量纲护栏（单位：成交额=亿元，PE/PB=倍）
_TURNOVER_ABSURD_YI = 5000.0      # 单只个股单日成交额（亿元）超此视为疑似单位错误
_PE_ABSURD = 1000.0               # |PE| 超此视为疑似单位错误
_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.\-]*$")
_GROUP_ORDER = ("放量上攻", "缩量上行", "缩量回调", "放量杀跌")
_GROUP_UP = {"放量上攻", "缩量上行"}
_GROUP_DOWN = {"缩量回调", "放量杀跌"}
_GROUP_VOLUME = {"放量上攻": "放量", "缩量上行": "缩量", "缩量回调": "缩量", "放量杀跌": "放量"}
_BOARD_PE_RE = re.compile(r"(?:板块|指数|sector[_\s-]*index).*(?:PE|P/E|市盈|pe[_\s-]*ttm)|(?:PE|P/E|市盈|pe[_\s-]*ttm).*(?:板块|指数|sector[_\s-]*index)", re.I)
_BOARD_PE_KEYS = {"pe", "pe_ttm", "sector_pe", "sector_pe_ttm", "board_pe", "board_pe_ttm", "市盈率", "板块市盈率", "板块pe", "板块pe_ttm"}


# ------------------------------------------------------------------ 基础工具

def _as_float(v):
    if isinstance(v, bool):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _date_key(s):
    """把日期串解析成可比较的 (年, 月, 日)；解析不出月份则 day/month=0。

    支持 ISO（2026-06-12）、中文（6月12日 / 数据截至…收盘里的 ISO）、斜杠点（6/12、06.06）。
    与 validate_doc_payload 的日期比较行为一致（用于 as_of ≤ timestamp 的时点比较）。
    """
    if not s:
        return (0, 0, 0)
    s = str(s)
    iso = re.search(r"(20\d{2})-(\d{1,2})-(\d{1,2})", s)
    if iso:
        return (int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))
    ym = re.search(r"(20\d{2})\D", s)
    year = int(ym.group(1)) if ym else 2026
    mm = re.search(r"(\d{1,2})\s*月", s)
    if mm:
        month = int(mm.group(1))
        dd = re.search(r"(\d{1,2})\s*日", s)
        if dd:
            day = int(dd.group(1))
        elif "初" in s:
            day = 3
        elif "中" in s:
            day = 15
        elif "底" in s or "末" in s:
            day = 28
        else:
            day = 0
        return (year, month, day)
    m = re.search(r"(?<!\d)(\d{1,2})[/.](\d{1,2})(?!\d)", s)
    if m:
        return (year, int(m.group(1)), int(m.group(2)))
    return (year, 0, 0)


def _pct_from(numer, denom):
    """(numer/denom - 1) * 100；denom 为 0 / None 时返回 None。"""
    if numer is None or denom is None or denom == 0:
        return None
    return (numer / denom - 1.0) * 100.0


def _within_tol(expected, claimed):
    """复算值 expected 与登记值 claimed 是否在容差内一致。"""
    if expected is None or claimed is None:
        return True  # 分量不全，不在此报错（由 warning 兜底）
    tol = max(_TOL_ABS_PCT, abs(expected) * _TOL_REL)
    return abs(expected - claimed) <= tol


def _fmt(v):
    if v is None:
        return "N/A"
    return f"{v:+.1f}" if abs(v - round(v)) > 1e-9 else f"{v:+.0f}"


def _group_members(groups, group_name):
    raw = (groups or {}).get(group_name)
    if isinstance(raw, dict):
        raw = raw.get("stocks")
    if not isinstance(raw, list):
        return []
    return [str(x).strip() for x in raw if str(x).strip() and str(x).strip() != "无"]


def _expected_group(ch, turn, t7):
    if ch is None or turn is None or t7 is None:
        return None
    if ch >= 0 and turn >= t7:
        return "放量上攻"
    if ch >= 0:
        return "缩量上行"
    if turn >= t7:
        return "放量杀跌"
    return "缩量回调"


def _validate_stock_checks(obj, meta):
    """第一阶段 10 股逐股行情与量价四象限硬校验。

    facts.json 用 stock_checks / divergence_groups 记录第一轮已验证的个股表，
    不要求第一阶段组装文档 payload。
    """
    infos, warnings, errors = [], [], []
    selected = [str(x).strip() for x in (meta.get("selected_stocks") or []) if str(x).strip()]
    checks = obj.get("stock_checks")
    groups = obj.get("divergence_groups")

    if len(selected) != 10:
        errors.append("meta.selected_stocks 必须恰好 10 只代表股名称。")

    if not isinstance(checks, list):
        errors.append("facts.json 缺少 stock_checks 数组——第一阶段必须登记 10 股逐股行情、近7日复算分量与量价分组依据。")
        return infos, warnings, errors
    if len(checks) != 10:
        errors.append(f"stock_checks 必须恰好 10 只，当前 {len(checks)} 只。")

    names = []
    by_name = {}
    for i, s in enumerate(checks):
        label = f"stock_checks[{i}]"
        if not isinstance(s, dict):
            errors.append(f"{label} 必须是对象。")
            continue
        nm = str(s.get("name") or "").strip()
        if not nm:
            errors.append(f"{label}.name 缺失。")
            continue
        names.append(nm)
        by_name[nm] = s
        if not str(s.get("role") or "").strip():
            errors.append(f"{label}（{nm}）缺 role；第一阶段必须写明该代表股的定性角色。")
        if not str(s.get("select_reason") or s.get("note") or "").strip():
            errors.append(f"{label}（{nm}）缺 select_reason；第一阶段必须说明为什么选入这 10 只代表股。")
        if not str(s.get("source_name") or "").strip():
            errors.append(f"{label}（{nm}）缺 source_name；10 股行情须标明同花顺数据库来源。")
        elif "同花顺" not in str(s.get("source_name")):
            warnings.append(f"{label}（{nm}）source_name=“{s.get('source_name')}”，请确认 10 股行情来自同花顺数据库。")
        if not str(s.get("evidence") or "").strip():
            errors.append(f"{label}（{nm}）缺 evidence；请粘贴 seed_finance_search / 同花顺返回的原始数据行摘要，不能只填自洽数字。")
        ao = s.get("as_of")
        ts = _date_key(meta.get("timestamp"))
        if ao and ts[1]:
            ak = _date_key(ao)
            if ak[1] and ak > ts:
                errors.append(f"{label}（{nm}）as_of({ao}) 晚于数据截止日，时点矛盾。")

        for fld in ("change", "turnover", "pe_ttm", "change_7d", "turnover_7d", "d7_close_base", "d7_close_t"):
            if _as_float(s.get(fld)) is None:
                errors.append(f"{label}（{nm}）缺少有效 {fld}。")
        ch = _as_float(s.get("change"))
        if ch is not None and abs(ch) > 20.0:
            errors.append(f"{label}（{nm}）change={ch:g}% 超出 A 股单日 ±20% 上限，疑似数据错误。")
        turn = _as_float(s.get("turnover"))
        if turn is not None and turn < 0:
            errors.append(f"{label}（{nm}）turnover={turn:g} 为负，成交额不应为负。")
        c7 = _as_float(s.get("change_7d"))
        if c7 is not None and abs(c7) > 200.0:
            warnings.append(f"{label}（{nm}）change_7d={c7:g}% 绝对值过大（>200%），请复核近7日序列。")
        t7 = _as_float(s.get("turnover_7d"))
        if t7 is not None and t7 < 0:
            errors.append(f"{label}（{nm}）turnover_7d={t7:g} 为负，成交额不应为负。")

        base = _as_float(s.get("d7_close_base"))
        close_t = _as_float(s.get("d7_close_t"))
        if base is not None and close_t is not None and c7 is not None:
            calc = _pct_from(close_t, base)
            ok = _within_tol(calc, c7)
            infos.append(f"{nm} 近7日涨跌复算：T日收盘 {close_t:g} / T-7交易日收盘 {base:g} − 1 = {_fmt(calc)}%（登记 {c7:+.1f}%，{'一致' if ok else '✗ 不一致'}）")
            if not ok:
                errors.append(f"{label}（{nm}）change_7d 复算不一致：T日收盘 / T-7交易日收盘 − 1 = {calc:+.1f}%，登记 {c7:+.1f}%。")
        turns = s.get("d7_turnovers")
        if not isinstance(turns, list) or len(turns) != 7:
            errors.append(f"{label}（{nm}）d7_turnovers 必须是最近 7 个交易日成交额数组，且长度为 7。")
        else:
            vals = [_as_float(x) for x in turns]
            if any(v is None for v in vals):
                errors.append(f"{label}（{nm}）d7_turnovers 含非数字值。")
            elif any(v < 0 for v in vals):
                errors.append(f"{label}（{nm}）d7_turnovers 含负成交额。")
            elif t7 is not None:
                avg = sum(vals) / 7.0
                ok = _within_tol(avg, t7)
                infos.append(f"{nm} 近7个交易日日均成交额复算：逐日成交额平均值 = {avg:.1f} 亿（登记 {t7:.1f} 亿，{'一致' if ok else '✗ 不一致'}）")
                if not ok:
                    errors.append(f"{label}（{nm}）turnover_7d 复算不一致：最近7个交易日逐日成交额平均值 = {avg:.1f} 亿，登记 {t7:.1f} 亿。")

    dup = sorted({n for n in names if names.count(n) > 1})
    if dup:
        errors.append(f"stock_checks 存在重复个股：{'、'.join(dup)}。")
    if selected and set(names) != set(selected):
        only_sel = sorted(set(selected) - set(names))
        only_chk = sorted(set(names) - set(selected))
        parts = []
        if only_sel:
            parts.append(f"selected_stocks 中未检查：{'、'.join(only_sel)}")
        if only_chk:
            parts.append(f"stock_checks 多出：{'、'.join(only_chk)}")
        errors.append("stock_checks 名单必须与 meta.selected_stocks 完全一致。" + "；".join(parts))

    if not isinstance(groups, dict):
        errors.append("facts.json 缺少 divergence_groups 对象——第一阶段必须登记放量上攻 / 缩量上行 / 缩量回调 / 放量杀跌四组。")
        return infos, warnings, errors

    grouped = []
    for g in _GROUP_ORDER:
        grouped.extend(_group_members(groups, g))
    if set(grouped) != set(names):
        miss = sorted(set(names) - set(grouped))
        extra = sorted(set(grouped) - set(names))
        parts = []
        if miss:
            parts.append(f"未分组：{'、'.join(miss)}")
        if extra:
            parts.append(f"分组中有口径外个股：{'、'.join(extra)}")
        errors.append("divergence_groups 四组并集必须等于 stock_checks 的 10 只代表股。" + "；".join(parts))
    gdup = sorted({n for n in grouped if grouped.count(n) > 1})
    if gdup:
        errors.append(f"divergence_groups 中同一个股被分到多个组：{'、'.join(gdup)}。")

    for g in _GROUP_ORDER:
        for nm in _group_members(groups, g):
            s = by_name.get(nm)
            if not s:
                continue
            ch = _as_float(s.get("change"))
            turn = _as_float(s.get("turnover"))
            t7 = _as_float(s.get("turnover_7d"))
            expected_group = _expected_group(ch, turn, t7)
            if expected_group and expected_group != g:
                errors.append(
                    f"个股“{nm}”按硬口径应归入“{expected_group}”，却被归入“{g}”："
                    f"change={ch:+.2f}%，当日成交额 {turn:g} 亿，近7个交易日日均成交额 {t7:g} 亿。"
                    f"分组规则为 change>=0 进上行侧、change<0 进下行侧；turnover>=turnover_7d 为放量，否则缩量。"
                )
                continue
            if ch is not None:
                if g in _GROUP_UP and ch < 0:
                    errors.append(f"个股“{nm}”change={ch:+.2f}% 为负，却被归入上行组“{g}”（收平才按上行侧处理）。")
                if g in _GROUP_DOWN and ch >= 0:
                    errors.append(f"个股“{nm}”change={ch:+.2f}% 非负，却被归入下行组“{g}”（change >= 0 应归入放量上攻或缩量上行）。")
            if turn is not None and t7 is not None:
                actual = "放量" if turn >= t7 else "缩量"
                expected = _GROUP_VOLUME[g]
                if actual != expected:
                    op = "≥" if expected == "放量" else "<"
                    errors.append(
                        f"个股“{nm}”被归入“{g}”，但当日成交额 {turn:g} 亿、近7个交易日日均成交额 {t7:g} 亿，"
                        f"按硬口径应为“{actual}”（{expected}组要求 turnover {op} turnover_7d）。"
                    )

    if names and not errors:
        infos.append(f"10 股逐股数据校验通过：{len(names)} 只，近7日涨跌 / 日均成交额可复算，四象限分组自洽。")
    return infos, warnings, errors


def _validate_sector_checks(obj, meta):
    """第一阶段目标板块 5 个核心小卡候选指标校验。"""
    infos, warnings, errors = [], [], []
    mode = str(meta.get("data_mode") or "").strip().lower()
    sc = obj.get("sector_checks")
    if not isinstance(sc, dict):
        errors.append(
            "facts.json 缺少 sector_checks 对象——第一阶段必须登记目标板块收盘、当日涨跌、"
            "当日成交、近7日涨跌、近7个交易日日均成交额及复算分量。"
        )
        return infos, warnings, errors

    if "missing_fields" in sc:
        errors.append("sector_checks.missing_fields 已废弃；目标板块指标必须取目标板块自身数据，不允许用 10 股样本替代。")

    required = ("close_point", "daily_change", "turnover_amount", "change_7d", "turnover_7d")
    components = ("prev_close", "d7_close_base", "d7_close_t")
    for fld in required:
        if _as_float(sc.get(fld)) is None:
            errors.append(f"sector_checks 缺少有效 {fld}；目标板块 5 个核心指标必须登记目标板块自身数据。")
    for fld in components:
        if _as_float(sc.get(fld)) is None:
            errors.append(f"sector_checks 缺少有效 {fld}；板块当日 / 近7日涨跌需要原始收盘分量复算（近7日基准为 T-7 交易日收盘）。")

    if not str(sc.get("source_name") or "").strip():
        errors.append("sector_checks 缺 source_name；板块行情须标明 seed_finance_search / 同花顺数据库来源。")
    elif "同花顺" not in str(sc.get("source_name")):
        warnings.append(f"sector_checks.source_name=“{sc.get('source_name')}”，请确认板块行情来自 seed_finance_search / 同花顺数据库。")
    if not str(sc.get("evidence") or "").strip():
        errors.append("sector_checks 缺 evidence；请粘贴 seed_finance_search / 同花顺返回的目标板块原始数据行摘要，不能只填自洽数字。")
    ao = sc.get("as_of")
    ts = _date_key(meta.get("timestamp"))
    if ao and ts[1]:
        ak = _date_key(ao)
        if ak[1] and ak > ts:
            errors.append(f"sector_checks.as_of({ao}) 晚于数据截止日，时点矛盾。")

    close_point = _as_float(sc.get("close_point"))
    prev_close = _as_float(sc.get("prev_close"))
    daily_change = _as_float(sc.get("daily_change"))
    if prev_close is not None and close_point is not None and daily_change is not None:
        calc = _pct_from(close_point, prev_close)
        ok = _within_tol(calc, daily_change)
        infos.append(f"板块当日涨跌复算：{close_point:g} / {prev_close:g} − 1 = {_fmt(calc)}%（登记 {daily_change:+.1f}%，{'一致' if ok else '✗ 不一致'}）")
        if not ok:
            errors.append(f"sector_checks.daily_change 复算不一致：close_point/prev_close−1 = {calc:+.1f}%，登记 {daily_change:+.1f}%。")

    d7_base = _as_float(sc.get("d7_close_base"))
    d7_close_t = _as_float(sc.get("d7_close_t"))
    change_7d = _as_float(sc.get("change_7d"))
    if close_point is not None and d7_close_t is not None and not _within_tol(close_point, d7_close_t):
        warnings.append(f"sector_checks.close_point({close_point:g}) 与 d7_close_t({d7_close_t:g}) 不一致；通常二者都应为截止日收盘点位。")
    if d7_base is not None and d7_close_t is not None and change_7d is not None:
        calc = _pct_from(d7_close_t, d7_base)
        ok = _within_tol(calc, change_7d)
        infos.append(f"板块近7日涨跌复算：T日收盘 {d7_close_t:g} / T-7交易日收盘 {d7_base:g} − 1 = {_fmt(calc)}%（登记 {change_7d:+.1f}%，{'一致' if ok else '✗ 不一致'}）")
        if not ok:
            errors.append(f"sector_checks.change_7d 复算不一致：T日收盘 / T-7交易日收盘 − 1 = {calc:+.1f}%，登记 {change_7d:+.1f}%。")

    turns = sc.get("d7_turnovers")
    turnover_7d = _as_float(sc.get("turnover_7d"))
    if not isinstance(turns, list) or len(turns) != 7:
        errors.append("sector_checks.d7_turnovers 必须是目标板块最近 7 个交易日成交额数组，且长度为 7。")
    else:
        vals = [_as_float(x) for x in turns]
        if any(v is None for v in vals):
            errors.append("sector_checks.d7_turnovers 含非数字值。")
        elif any(v < 0 for v in vals):
            errors.append("sector_checks.d7_turnovers 含负成交额。")
        elif turnover_7d is not None:
            avg = sum(vals) / 7.0
            ok = _within_tol(avg, turnover_7d)
            infos.append(f"板块近7个交易日日均成交额复算：逐日成交额平均值 = {avg:.1f} 亿（登记 {turnover_7d:.1f} 亿，{'一致' if ok else '✗ 不一致'}）")
            if not ok:
                errors.append(f"sector_checks.turnover_7d 复算不一致：最近7个交易日逐日成交额平均值 = {avg:.1f} 亿，登记 {turnover_7d:.1f} 亿。")

    turnover_amount = _as_float(sc.get("turnover_amount"))
    if turnover_amount is not None and turnover_amount < 0:
        errors.append(f"sector_checks.turnover_amount={turnover_amount:g} 为负，成交额不应为负。")
    if turnover_7d is not None and turnover_7d < 0:
        errors.append(f"sector_checks.turnover_7d={turnover_7d:g} 为负，成交额不应为负。")

    if sc and not errors:
        infos.append("目标板块 5 个核心指标校验通过：收盘、当日涨跌 / 成交、近7日涨跌 / 近7个交易日日均成交额已登记并可复算。")
    return infos, warnings, errors


# ------------------------------------------------------------------ 复算明细

def _iter_recompute_objs(p):
    """产出所有可能携带 typed 复算分量的对象：numeric_facts + dimensions + key_chips。"""
    for i, f in enumerate(p.get("numeric_facts") or []):
        if isinstance(f, dict):
            yield (f.get("id") or f"numeric_facts[{i}]"), f
    for i, d in enumerate(p.get("dimensions") or []):
        if isinstance(d, dict):
            yield (f"维度“{d.get('name', i)}”"), d
    for i, c in enumerate(p.get("key_chips") or []):
        if isinstance(c, dict):
            yield (f"key_chips[{i}]（{c.get('label', '')}）"), c


def _recompute_one(label, o):
    """对单个对象按其 typed 分量复算，产出 (info_lines, error_lines)。"""
    infos, errs = [], []

    high = _as_float(o.get("range_high"))
    low = _as_float(o.get("range_low"))
    pct = _as_float(o.get("range_pct"))
    if high is not None and low is not None:
        if low > high + 1e-9:
            errs.append(f"{label}：区间高低点疑似填反（range_high={high:g} < range_low={low:g}）。")
        exp = _pct_from(low, high)
        if pct is not None:
            ok = _within_tol(exp, pct)
            infos.append(
                f"{label} 回撤复算：低{low:g} / 高{high:g} − 1 = {_fmt(exp)}%"
                f"（登记 {pct:+.1f}%，{'一致' if ok else '✗ 不一致'}）"
            )
            if not ok:
                errs.append(
                    f"{label}：回撤幅度对不上——低{low:g}/高{high:g} 复算为 {exp:+.1f}%，"
                    f"但登记 range_pct={pct:+.1f}%（超出容差）。请核对高低点或回撤值。"
                )
        else:
            infos.append(f"{label} 回撤复算：低{low:g} / 高{high:g} − 1 = {_fmt(exp)}%（未登记 range_pct）")

    prev = _as_float(o.get("prev_close"))
    last = _as_float(o.get("last_close"))
    chg = _as_float(o.get("change_pct"))
    if prev is not None and last is not None:
        exp = _pct_from(last, prev)
        if chg is not None:
            ok = _within_tol(exp, chg)
            infos.append(
                f"{label} 单日涨跌复算：收{last:g} / 前收{prev:g} − 1 = {_fmt(exp)}%"
                f"（登记 {chg:+.1f}%，{'一致' if ok else '✗ 不一致'}）"
            )
            if not ok:
                errs.append(
                    f"{label}：单日涨跌幅对不上——收{last:g}/前收{prev:g} 复算为 {exp:+.1f}%，"
                    f"但登记 change_pct={chg:+.1f}%（超出容差）。"
                )
        else:
            infos.append(f"{label} 单日涨跌复算：收{last:g} / 前收{prev:g} − 1 = {_fmt(exp)}%（未登记 change_pct）")

    fl = _as_float(o.get("from_low"))
    to = _as_float(o.get("rebound_to"))
    rpct = _as_float(o.get("rebound_pct"))
    if fl is not None and to is not None:
        exp = _pct_from(to, fl)
        if rpct is not None:
            ok = _within_tol(exp, rpct)
            infos.append(
                f"{label} 反弹复算：{to:g} / 低{fl:g} − 1 = {_fmt(exp)}%"
                f"（登记 {rpct:+.1f}%，{'一致' if ok else '✗ 不一致'}）"
            )
            if not ok:
                errs.append(
                    f"{label}：反弹幅度对不上——{to:g}/低{fl:g} 复算为 {exp:+.1f}%，"
                    f"但登记 rebound_pct={rpct:+.1f}%（超出容差）。"
                )
        else:
            infos.append(f"{label} 反弹复算：{to:g} / 低{fl:g} − 1 = {_fmt(exp)}%（未登记 rebound_pct）")

    # 通用两操作数复算：numerator / denominator（as_pct=True 时按百分比）对账 value
    numer = _as_float(o.get("numerator"))
    denom = _as_float(o.get("denominator"))
    val = _as_float(o.get("value"))
    if numer is not None and denom is not None and denom != 0:
        ratio = numer / denom
        shown = ratio * 100.0 if o.get("as_pct") else ratio
        unit = "%" if o.get("as_pct") else ""
        if val is not None:
            tol = max(_TOL_ABS_PCT, abs(shown) * _TOL_REL) if o.get("as_pct") else max(abs(shown) * _TOL_REL, 1e-6)
            ok = abs(shown - val) <= tol
            infos.append(
                f"{label} 比值复算：{numer:g} / {denom:g} = {shown:.2f}{unit}"
                f"（登记 {val:g}{unit}，{'一致' if ok else '✗ 不一致'}）"
            )
            if not ok:
                errs.append(f"{label}：比值对不上——{numer:g}/{denom:g}={shown:.2f}{unit}，登记 value={val:g}{unit}。")
        else:
            infos.append(f"{label} 比值复算：{numer:g} / {denom:g} = {shown:.2f}{unit}（未登记 value）")

    return infos, errs


def recompute(p):
    """产出展示数字复算明细（[复算/信息]）。

    10 股逐股复算与量价分组属于第一阶段 facts_json_checks()，文档生成阶段不在
    payload 复算门里重新输出股票分组均值或两端排名。
    """
    lines = []
    for label, o in _iter_recompute_objs(p):
        infos, _ = _recompute_one(label, o)
        lines.extend(infos)
    return lines


# ------------------------------------------------------------------ 硬错误（复算对不上 / 量纲越界 / 登记 vs 展示打架）

def hard_checks(p):
    """返回硬错误列表（调用方据此 fail-loud）。

    文档生成阶段只做 numeric_facts / key_chips / dimensions 等展示数字的复算与登记一致性。
    10 股逐股复算、量价四象限和代表股理由已前移到 facts_json_checks()，并由
    hydrate_payload_from_facts.py 自动映射到 payload，不在这里重复做内容判断。
    """
    errors = []

    # 1) 逐对象复算对账
    for label, o in _iter_recompute_objs(p):
        _, errs = _recompute_one(label, o)
        errors.extend(errs)

    # 2) 事实表内同一指标多处取值打架；登记事实 vs 展示对象绑定值打架
    errors.extend(_cross_value_conflicts(p))

    return errors


def _facts_index(p):
    idx = {}
    for f in (p.get("numeric_facts") or []):
        if isinstance(f, dict) and isinstance(f.get("id"), str):
            idx[f["id"]] = f
    return idx


def _cross_value_conflicts(p):
    errors = []
    facts = p.get("numeric_facts") or []

    # (a) 同 metric@period 的多条登记事实，数值必须一致
    by_key = {}
    for i, f in enumerate(facts):
        if not isinstance(f, dict):
            continue
        v = _as_float(f.get("value"))
        if v is None:
            continue
        key = (str(f.get("metric") or "").strip(), str(f.get("period") or f.get("as_of") or "").strip())
        if not key[0]:
            continue
        by_key.setdefault(key, []).append((f.get("id") or f"#{i}", v))
    for (metric, period), items in by_key.items():
        vals = [v for _, v in items]
        if len(vals) >= 2 and (max(vals) - min(vals)) > max(_TOL_ABS_PCT, abs(max(vals)) * _TOL_REL):
            who = "、".join(f"{i}={v:g}" for i, v in items)
            errors.append(
                f"事实表内同一指标取值不一致：「{metric}{('（' + period + '）') if period else ''}」存在冲突取值（{who}）。"
            )

    # (b) 展示对象声明了 fact id 且自带 typed value_num，与登记事实数值打架
    idx = _facts_index(p)
    if idx:
        spots = []
        for c in (p.get("key_chips") or []):
            if isinstance(c, dict):
                spots.append((f"key_chips（{c.get('label', '')}）", c))
        for s in (p.get("stocks") or []):
            if isinstance(s, dict):
                spots.append((f"个股“{s.get('name', '?')}”", s))
        for d in (p.get("dimensions") or []):
            if isinstance(d, dict):
                spots.append((f"维度“{d.get('name', '')}”", d))
        for label, o in spots:
            fid = o.get("fact")
            shown = _as_float(o.get("value_num"))
            if isinstance(fid, str) and fid in idx and shown is not None:
                reg = _as_float(idx[fid].get("value"))
                if reg is not None and abs(reg - shown) > max(_TOL_ABS_PCT, abs(reg) * _TOL_REL):
                    errors.append(
                        f"{label}：展示值 value_num={shown:g} 与所绑定事实 `{fid}` 的登记值 {reg:g} 不一致。"
                    )
    return errors


# ------------------------------------------------------------------ 事实表结构与「展示数值是否登记/溯源」

def registry_checks(p, timestamp_key=None):
    """校验 numeric_facts 事实表与展示数值的登记/溯源。

    返回 (errors, warnings)。
    - errors：事实表条目结构错误、lane 分级错误、as_of 晚于数据截止日。
    - warnings：未提供事实表、关键展示数值未绑定 fact id、登记事实缺 source_name 等（不阻断）。
    """
    errors, warnings = [], []
    facts = p.get("numeric_facts")

    if not facts:
        warnings.append(
            "未提供 numeric_facts 事实表：无法对关键财务/股票数字做登记与复算对账，"
            "建议把每个展示数值登记进 numeric_facts（带 value / lane / source_name；可复算项带原始分量），以提升可核验性。"
        )
        return errors, warnings

    if not isinstance(facts, list):
        errors.append("numeric_facts 必须是数组。")
        return errors, warnings

    seen = set()
    for i, f in enumerate(facts):
        label = f"numeric_facts[{i}]"
        if not isinstance(f, dict):
            errors.append(f"{label} 必须是对象。")
            continue
        fid = f.get("id")
        if not isinstance(fid, str) or not _ID_RE.fullmatch(fid):
            errors.append(f"{label}.id 缺失或格式错误（需以字母开头，只含字母/数字/._-）。")
        elif fid in seen:
            errors.append(f"{label}.id 重复：{fid}。")
        else:
            seen.add(fid)
        if not str(f.get("metric") or "").strip():
            errors.append(f"{label}.metric 缺失（指标名）。")
        if "value" not in f:
            errors.append(f"{label}.value 缺失（登记值；定性可填字符串说明）。")

        kind = str(f.get("kind") or "market").strip().lower()
        lane = str(f.get("lane") or "").strip()
        if not lane:
            errors.append(f"{label}.lane 缺失（须标 {_LANE_FINANCE} 或 {_LANE_GENERAL}）。")
        elif lane not in _VALID_LANES:
            errors.append(f"{label}.lane=“{lane}” 非法。")
        elif kind == "catalyst":
            if lane != _LANE_GENERAL:
                errors.append(f"{label}：催化类事实必须 lane=general_search（当前 {lane}）。")
        else:
            if lane != _LANE_FINANCE:
                errors.append(
                    f"{label}：行情/财务类事实必须 lane=seed_finance_search（当前 {lane}）——"
                    f"除「为什么涨/跌」催化外，一切金融数据只走 seed_finance_search（分级约束）。"
                )

        if not str(f.get("source_name") or "").strip():
            warnings.append(f"{label}（{f.get('metric', '')}）缺 source_name（来源名/数据终端名），建议补全以便溯源。")

        ao = f.get("as_of")
        if ao and timestamp_key:
            ak = _date_key(ao)
            if ak[1] and ak > timestamp_key:
                errors.append(f"{label}.as_of({ao}) 晚于数据截止日，时点矛盾。")

        # 三级可信度一致性（当条目带 tier 时校验；不带 tier 仅作 source_name 级别的提示）
        if "tier" in f:
            te, tw = fact_tier_issues(f, label)
            errors.extend(te)
            warnings.extend(tw)

    # 关键展示数值是否绑定事实表（warning）：仅对 headline 级的 key_chips 提示；
    # 个股的涨跌/资金/成交已由复算与区间/分组硬校验守住，不再逐只 warning，避免噪音淹没真正的对账信息。
    for c in (p.get("key_chips") or []):
        if isinstance(c, dict) and not str(c.get("fact") or "").strip():
            warnings.append(
                f"key_chips（{c.get('label', '')}）含展示数值但未绑定 numeric_facts 的 fact id，"
                "复核是否关键证据数字、是否应登记。"
            )

    return errors, warnings


# ------------------------------------------------------------------ 三级可信度分级校验

def _tier_of(f):
    t = f.get("tier")
    if isinstance(t, bool):
        return None
    try:
        return int(t)
    except (TypeError, ValueError):
        return None


def fact_tier_issues(f, label):
    """单条事实的三级分级 / 措辞 / 来源一致性。返回 (errors, warnings)。

    适用于 facts.json 的 facts[] 与 payload 的 numeric_facts[]（两者同结构）。
    规则：行情数字必须一级；催化只许一级 / 二级 + source_name + url；二级须带限定措辞；三级不得作展示值或模块2催化来源。
    聚合 / 分发承载页若署名 / 作者 / 采编主体为机构媒体，可作为二级催化链接保留但给警告；标一级报错，个人 / 自媒体仍报错。
    """
    errors, warnings = [], []
    kind = str(f.get("kind") or "market").strip().lower()
    tier = _tier_of(f)
    metric = str(f.get("metric") or "").strip()
    text_for_board_pe = " ".join(str(f.get(k) or "") for k in ("id", "metric", "metric_key", "source_name"))
    if _BOARD_PE_RE.search(text_for_board_pe):
        errors.append(
            f"{label}（{metric}）：禁止登记板块 PE / 板块市盈率。固定模块只回填股票 PE(TTM)："
            f"核心小卡取 10 只代表股中市值最大那只，估值位置取 10 只代表股 PE(TTM) 中位数 / 区间。"
        )

    if tier is None:
        warnings.append(f"{label}（{metric}）缺 tier（可信度等级 1/2/3），建议补全以便分级核对。")
    elif tier not in _TIER_VALID:
        errors.append(f"{label}.tier={f.get('tier')} 非法，应为 1 / 2 / 3。")

    # 行情 / 财务数字必须一级（数据库或经其核验）
    if kind in _MARKET_KINDS and tier is not None and tier != 1:
        errors.append(
            f"{label}（{metric}）：行情 / 财务数字（kind={kind}）必须为一级（tier=1，"
            f"取自 seed_finance_search 或经其核验），当前 tier={tier}。二级 / 三级来源里的行情数字只能作核验线索。"
        )

    # 模块2 催化：必须可核验（url 必填）+ 显名标注来源（source_name 必填）；来源只能选取一级 / 二级，禁止三级（命中三级硬错）
    if kind == "catalyst":
        source_name = str(f.get("source_name") or "").strip()
        url = str(f.get("url") or "").strip()
        nl, ul = source_name.lower(), url.lower()
        author_type = str(f.get("author_type") or f.get("source_type") or "").strip().lower()
        institution_author = author_type in _INSTITUTION_AUTHOR_TYPES
        known_institution = any(h in source_name for h in _INSTITUTIONAL_SOURCE_KEYS)
        explicit_tier2 = tier == 2
        for k in _TIER3_CATALYST_SOURCE_KEYS:
            if k in source_name or k.lower() in nl:
                errors.append(
                    f"{label}（{metric}）：催化 source_name=“{source_name}” 命中三级来源（{k}）——"
                    f"模块2 须回溯一级 / 二级原文。"
                )
                break
        for k in _PERSONAL_SOURCE_KEYS:
            if k in source_name or k.lower() in nl:
                errors.append(
                    f"{label}（{metric}）：催化 source_name=“{source_name}” 疑似个人 / 自媒体作者（{k}）——"
                    f"模块2 只能使用机构媒体 / 官方 / 行业第三方等一级或二级来源。"
                )
                break
        for k in _PLATFORM_SOURCE_KEYS:
            if k in source_name or k.lower() in nl:
                if explicit_tier2 and institution_author:
                    warnings.append(
                        f"{label}（{metric}）：source_name=“{source_name}” 是平台 / 聚合名（{k}），但已标明机构主体，可按二级保留；更建议 source_name 填实际机构名。"
                    )
                else:
                    errors.append(
                        f"{label}（{metric}）：source_name=“{source_name}” 是平台 / 聚合名（{k}），"
                        f"需确认作者 / 账号主体为机构号并标 source.tier=2；个人 / 自媒体 / 无法确认机构主体不得入选模块2。"
                    )
                break
        for k in _AGGREGATOR_CATALYST_URL_KEYS:
            if k.lower() in ul:
                if tier == 1 and (known_institution or institution_author):
                    errors.append(
                        f"{label}（{metric}）：催化 url=“{url}” 是聚合 / 分发承载页（{k}），"
                        f"即使 source_name=“{source_name}” 可识别为机构媒体 / 新闻网站，也只能标 source.tier=2；"
                        f"只有回溯到官方 / 公告 / 官媒原文链接时才可标一级。"
                    )
                elif tier == 2 and (known_institution or institution_author):
                    warnings.append(
                        f"{label}（{metric}）：催化 url=“{url}” 是聚合 / 分发承载页（{k}），"
                        f"但 source_name=“{source_name}” 可识别为机构媒体 / 新闻网站，允许按二级保留；聚合 URL 不自动判三级，能回溯原文时仍优先改用原文直链。"
                    )
                else:
                    errors.append(
                        f"{label}（{metric}）：催化 url=“{url}” 落在聚合 / 分发承载页（{k}），"
                        f"但未能确认署名 / 作者 / 采编主体为机构媒体 / 新闻网站；个人 / 自媒体或无法确认机构作者不得作为模块2 最终来源。"
                    )
                break
        for k in _SUSPECT_CATALYST_URL_KEYS:
            if k.lower() in ul:
                warnings.append(
                    f"{label}（{metric}）：催化 url=“{url}” 命中可疑转载 / 移动分发 / 跳转特征（{k}），"
                    f"建议回溯一级 / 二级原文；若确认为来源方原文，请显式标注 tier。"
                )
                break
        title = str(f.get("title") or f.get("metric") or "").strip()
        if source_name and len(source_name) > 16:
            warnings.append(
                f"{label}（{metric}）：source_name=“{source_name}”较长，请确认只填来源名本身、没有把标题或描述粘进去。"
            )
        if source_name and title and len(title) >= 6 and title in source_name:
            errors.append(f"{label}（{metric}）：source_name 含标题内容；标题请放 title / metric，来源名只放来源。")
        if tier == 3:
            errors.append(
                f"{label}（{metric}）：催化为【三级】来源——「为什么涨/跌」只能选取数据来源为一级和二级的数据，"
                f"禁止三级（行情 / 研报摘要 / 自媒体 / UGC，尤其个人作者发表的文章，以及无法确认机构作者的聚合 / 分发页）；"
                        f"须回溯到一级（官方 / 监管 / 交易所 / 公司公告 / 官媒）或二级（机构媒体 / 新闻网站、行业第三方等非三级来源；名单非封闭）原文并改链。"
            )
        elif tier is None:
            warnings.append(
                f"{label}（{metric}）：催化未标 tier —— 模块2 只能用一级 / 二级来源，请显式标 source.tier 为 1 或 2；若 url 是聚合承载页且机构署名，只能标 2，并确认其非个人 / 自媒体 / 无法确认机构作者。"
            )
        if not str(f.get("source_name") or "").strip():
            errors.append(f"{label}（{metric}）：催化缺 source_name（信息来源名，标题前【信息来源】须显名、一条都不能漏）。")
        if not str(f.get("url") or "").strip():
            errors.append(f"{label}（{metric}）：催化缺 url（可「打开原文」核验的链接）。")

    # 二级须带限定措辞
    if tier == 2:
        has_words = bool(f.get("allowed_wording")) or bool(str(f.get("suggested_wording") or "").strip())
        if not has_words:
            warnings.append(
                f"{label}（{metric}）：二级数据建议填 allowed_wording / suggested_wording —— "
                f"正文引用时须带限定语（如“据…报道 / 据…估算”），不要写成一手披露的确定事实。"
            )

    # 三级不得作展示值（行情 / 财务类）
    if tier == 3 and kind in _MARKET_KINDS:
        errors.append(
            f"{label}（{metric}）：三级信息不得作为展示数值（kind={kind}）—— "
            f"应顺藤核验到一级 / 二级原文后再用，核验不到就不展示。"
        )

    return errors, warnings


def facts_json_checks(obj):
    """整份 facts.json（meta + facts 列表）的结构、三级分级与复算。

    返回 (infos, warnings, errors)。供 lint_analysis.py 调用。
    """
    infos, warnings, errors = [], [], []

    meta = obj.get("meta")
    if not isinstance(meta, dict):
        errors.append("facts.json 缺 meta 块（板块 / 目标概念板块 / 10 只代表股 / 数据时点 / data_mode）。")
        meta = {}
    for field in ["sector", "index_caliber", "timestamp", "today", "data_mode"]:
        if not str(meta.get(field) or "").strip():
            errors.append(f"meta.{field} 缺失。")
    mode = str(meta.get("data_mode") or "").strip().lower()
    if mode and mode != "full":
        errors.append(f"meta.data_mode=“{mode}” 非法；当前只允许 full，板块指标不得用 partial/proxy 或 10 股样本替代。")
    if str(meta.get("data_note") or "").strip():
        errors.append("meta.data_note 已废弃；板块指标必须是目标板块自身数据，不再写兜底口径说明。")
    sector_index = obj.get("sector_index")
    if isinstance(sector_index, dict):
        bad_keys = [str(k) for k in sector_index if str(k).strip().lower() in _BOARD_PE_KEYS or _BOARD_PE_RE.search(str(k))]
        if bad_keys:
            errors.append(
                "facts.json 顶层 sector_index 禁止回填板块 PE / 板块市盈率字段："
                f"{'、'.join(bad_keys)}。请删除这些字段；股票 PE(TTM) 填到 10 只代表股逐股表或 facts[] 的代表股估值条目。"
            )

    sector_infos, sector_warnings, sector_errors = _validate_sector_checks(obj, meta)
    infos.extend(sector_infos)
    warnings.extend(sector_warnings)
    errors.extend(sector_errors)

    stock_infos, stock_warnings, stock_errors = _validate_stock_checks(obj, meta)
    infos.extend(stock_infos)
    warnings.extend(stock_warnings)
    errors.extend(stock_errors)

    facts = obj.get("facts")
    if not isinstance(facts, list) or not facts:
        errors.append("facts.json 缺 facts 数组（或为空）：请把每个展示数字与每条催化登记进来。")
        return infos, warnings, errors

    # 时点键（用于 as_of ≤ timestamp 比较）
    ts_key = None
    raw_ts = str(meta.get("timestamp") or "").strip()
    if raw_ts:
        ts_key = _date_key(raw_ts)
        if not ts_key[1]:
            ts_key = None

    seen = set()
    for i, f in enumerate(facts):
        label = f"facts[{i}]"
        if not isinstance(f, dict):
            errors.append(f"{label} 必须是对象。")
            continue
        fid = f.get("id")
        if not isinstance(fid, str) or not _ID_RE.fullmatch(fid):
            errors.append(f"{label}.id 缺失或格式错误（需以字母开头，只含字母 / 数字 / ._-）。")
        elif fid in seen:
            errors.append(f"{label}.id 重复：{fid}。")
        else:
            seen.add(fid)
        if not str(f.get("metric") or "").strip():
            errors.append(f"{label}.metric 缺失（指标名 / 事件名）。")
        if "value" not in f:
            errors.append(f"{label}.value 缺失（登记值；定性可填字符串说明）。")
        if not str(f.get("source_name") or "").strip():
            warnings.append(f"{label}（{f.get('metric', '')}）缺 source_name（来源名 / 数据终端名）。")
        ao = f.get("as_of")
        if ao and ts_key:
            ak = _date_key(ao)
            if ak[1] and ak > ts_key:
                errors.append(f"{label}.as_of({ao}) 晚于数据截止日，时点矛盾。")
        te, tw = fact_tier_issues(f, label)
        errors.extend(te)
        warnings.extend(tw)

    # 复算：把行情类事实当作 numeric_facts 喂给复算内核
    market_facts = [f for f in facts if isinstance(f, dict) and str(f.get("kind") or "market").strip().lower() in _MARKET_KINDS]
    pseudo = {"numeric_facts": market_facts}
    infos.extend(recompute(pseudo))
    errors.extend(hard_checks(pseudo))

    return infos, warnings, errors


# ------------------------------------------------------------------ 便捷封装（独立预检脚本用）

def run_all(p):
    """供 check_market_facts.py 调用：返回 (infos, warnings, errors)。"""
    ts = None
    raw_ts = str(p.get("timestamp") or "").strip()
    if raw_ts:
        ts = _date_key(raw_ts)
        if not ts[1]:
            ts = None
    infos = recompute(p)
    errs = list(hard_checks(p))
    reg_err, reg_warn = registry_checks(p, timestamp_key=ts)
    errs.extend(reg_err)
    return infos, reg_warn, errs
