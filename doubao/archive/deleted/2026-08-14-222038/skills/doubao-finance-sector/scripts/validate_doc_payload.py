#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""飞书文档 payload 写入前校验。

用法：
    python3 scripts/validate_doc_payload.py work/<板块>_payload.json

本脚本只校验飞书文档所需 payload，不生成网页或其它产物。
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import market_checks as _mc  # noqa: E402
from hydrate_payload_from_facts import _stock_transfer_hash  # noqa: E402

GROUP_ORDER = ["放量上攻", "缩量上行", "缩量回调", "放量杀跌"]
DIMENSION_ORDER = ["价格涨跌", "成交量能", "代表股表现", "估值位置"]
FIXED_KEY_METRICS = {"close_point", "daily_change", "change_7d", "turnover_amount", "turnover_7d", "pe_ttm"}
KEY_CHIPS_REQUIRED = {"close_point", "pe_ttm"}
KEY_CHIPS_DAILY_PAIR = {"daily_change", "turnover_amount"}
KEY_CHIPS_D7_PAIR = {"change_7d", "turnover_7d"}
QUAD_ZH = {"BB": "双热 · 强趋势共振", "CC": "双冷 · 低关注", "IH_MC": "信息热 · 行情冷", "MH_IC": "行情热 · 信息冷"}
VAL_METRIC_RE = re.compile(r"P\s*[EBS]\b|市盈|市净|市销", re.I)
VAL_CALIBER_RE = re.compile(r"TTM|LYR|MRQ|静态|动态|滚动|静|动", re.I)
INTERNAL_HEAT_SCORE_RE = re.compile(r"(?:综合|信息|行情)?热度\s*[+\-＋－]\s*\d|热度\s*(?:上调|下调)\s*\d", re.I)


class PayloadError(Exception):
    pass


def as_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def score_quadrant(info_hot, market_hot):
    if info_hot and market_hot:
        return "BB"
    if (not info_hot) and (not market_hot):
        return "CC"
    if info_hot and not market_hot:
        return "IH_MC"
    return "MH_IC"


def classify_quadrant(type_str):
    t = str(type_str or "").replace(" ", "")
    if "双热" in t or "强趋势共振" in t:
        return "BB"
    if "双冷" in t or "低关注" in t:
        return "CC"
    info_hot, info_cold = "信息热" in t, "信息冷" in t
    market_hot, market_cold = "行情热" in t, "行情冷" in t
    if info_hot and market_cold:
        return "IH_MC"
    if market_hot and info_cold:
        return "MH_IC"
    if "利好兑现回落" in t or "题材未启动" in t or ("题材" in t and "启动" in t):
        return "IH_MC"
    if "纯资金" in t or "资金驱动" in t:
        return "MH_IC"
    return None


def require_text(obj, key, label, errors):
    if not str(obj.get(key) or "").strip():
        errors.append(f"缺少 {label}（{key}）。")


def validate_payload(p):
    errors, warnings = [], []

    for key, label in (
        ("sector", "板块名"),
        ("market", "市场"),
        ("timestamp", "数据截止时点"),
        ("index_caliber", "目标概念板块口径"),
        ("headline", "核心标题"),
        ("summary", "核心摘要"),
        ("gauge_pill", "综合热度标签"),
    ):
        require_text(p, key, label, errors)

    selected = p.get("selected_stocks") or []
    if not isinstance(selected, list) or len(selected) != 10:
        count = len(selected) if isinstance(selected, list) else "非数组"
        errors.append(f"selected_stocks 必须恰好 10 个股票名，当前 {count}。")

    comp, info, market = as_float(p.get("composite_score")), as_float(p.get("info_score")), as_float(p.get("market_score"))
    for lab, value in (("composite_score", comp), ("info_score", info), ("market_score", market)):
        if value is None:
            errors.append(f"{lab} 缺失或非数值（三个热度分都必须给出、且落在 1-5）。")
        elif not (1 <= value <= 5):
            errors.append(f"{lab}={value:g} 不在 1-5 范围内。")
    if comp is not None and info is not None and market is not None:
        expect = max(1, min(5, round(0.55 * market + 0.45 * info)))
        if round(comp) != expect:
            errors.append(f"composite_score={comp:g} 与公式不符：round(0.55×行情{market:g} + 0.45×信息{info:g}) 应为 {expect}。")
        dtype = str((p.get("divergence") or {}).get("type") or "").strip()
        claimed = classify_quadrant(dtype)
        if claimed:
            want = score_quadrant(info >= 3, market >= 3)
            if claimed != want:
                errors.append(f"divergence.type=“{dtype}” 与分数不符：信息{info:g} / 行情{market:g}（阈值3）应落在“{QUAD_ZH[want]}”象限。")

    divergence = p.get("divergence") if isinstance(p.get("divergence"), dict) else {}
    require_text(divergence, "verdict", "双轨判词", errors)
    require_text(divergence, "meaning", "双轨含义", errors)

    answer = p.get("answer") if isinstance(p.get("answer"), dict) else {}
    for key, label in (("restate", "问题"), ("conclusion", "结论"), ("next", "下一步")):
        require_text(answer, key, f"直接回答的{label}", errors)
    if str(answer.get("status") or "").strip():
        errors.append("answer.status 已废弃；请把需要展示的当前状态并入 answer.next。")

    summaries = p.get("section_summaries") if isinstance(p.get("section_summaries"), dict) else {}
    for key in ("heat", "catalysts", "divergence", "watch", "risks"):
        require_text(summaries, key, f"section_summaries.{key}", errors)

    chips = p.get("key_chips") or []
    if not isinstance(chips, list) or len(chips) != 4:
        count = len(chips) if isinstance(chips, list) else "非数组"
        errors.append(f"key_chips 必须恰好 4 张，当前 {count}。")
    seen_metrics = set()
    if isinstance(chips, list):
        for i, chip in enumerate(chips):
            if not isinstance(chip, dict):
                errors.append(f"key_chips[{i}] 不是对象。")
                continue
            for key in ("label", "value", "metric_key"):
                require_text(chip, key, f"key_chips[{i}].{key}", errors)
            metric_key = str(chip.get("metric_key") or "").strip()
            if metric_key and metric_key not in FIXED_KEY_METRICS:
                errors.append(f"key_chips[{i}] 的 metric_key=“{metric_key}” 非法。")
            if metric_key in seen_metrics:
                errors.append(f"key_chips 指标 metric_key=“{metric_key}” 重复。")
            if metric_key:
                seen_metrics.add(metric_key)
            src = chip.get("source") if isinstance(chip.get("source"), dict) else {}
            if src.get("lane") != "seed_finance_search":
                errors.append(f"key_chips[{i}] 必须标注 source.lane=seed_finance_search。")
            if metric_key == "pe_ttm":
                pe_text = " ".join(str(chip.get(k) or "") for k in ("label", "value", "read", "source_name"))
                if re.search(r"(?:板块|指数).*(?:PE|P/E|市盈)|(?:PE|P/E|市盈).*(?:板块|指数)", pe_text, re.I):
                    errors.append("key_chips 的 pe_ttm 禁止使用板块 PE / 板块市盈率；必须取代表股 PE(TTM)。")
    missing = KEY_CHIPS_REQUIRED - seen_metrics
    if missing:
        errors.append(f"key_chips 缺少必须展示的定卡：{', '.join(sorted(missing))}。")
    has_daily = bool(KEY_CHIPS_DAILY_PAIR & seen_metrics)
    has_d7 = bool(KEY_CHIPS_D7_PAIR & seen_metrics)
    if has_daily and has_d7:
        errors.append("key_chips 不得交叉混搭当日组与近7日组。")
    elif has_daily and KEY_CHIPS_DAILY_PAIR - seen_metrics:
        errors.append("key_chips 选了当日组却不成对：daily_change 与 turnover_amount 必须同时出现。")
    elif has_d7 and KEY_CHIPS_D7_PAIR - seen_metrics:
        errors.append("key_chips 选了近7日组却不成对：change_7d 与 turnover_7d 必须同时出现。")
    elif not has_daily and not has_d7:
        errors.append("key_chips 除两张定卡外，还须从当日组或近7日组中二选一补满两张。")

    dims = p.get("dimensions") or []
    if not isinstance(dims, list) or len(dims) != 4:
        count = len(dims) if isinstance(dims, list) else "非数组"
        errors.append(f"dimensions 必须为固定 4 个维度，当前 {count}。")
    else:
        got = [str(d.get("name") or "").strip() for d in dims if isinstance(d, dict)]
        if got != DIMENSION_ORDER:
            errors.append(f"dimensions 必须按固定顺序填写：{' / '.join(DIMENSION_ORDER)}。当前顺序为：{' / '.join(got)}。")
        for d in dims:
            if not isinstance(d, dict):
                continue
            if str(d.get("track") or "行情").strip() != "行情":
                errors.append(f"维度“{d.get('name','')}” track 必须为“行情”。")
            for key in ("name", "value", "state", "read"):
                require_text(d, key, f"dimensions[].{key}", errors)
            src = d.get("source") if isinstance(d.get("source"), dict) else {}
            if src.get("lane") != "seed_finance_search":
                errors.append(f"维度“{d.get('name','')}” 必须标注 source.lane=seed_finance_search。")
            if "估值" in str(d.get("name") or ""):
                val = str(d.get("value") or "")
                if VAL_METRIC_RE.search(val) and not VAL_CALIBER_RE.search(val):
                    errors.append(f"估值维度数值“{val[:40]}...”含 PE/PB/PS 但未标口径。")

    catalysts = p.get("catalysts") or []
    if not isinstance(catalysts, list) or not (3 <= len(catalysts) <= 6):
        count = len(catalysts) if isinstance(catalysts, list) else "非数组"
        errors.append(f"catalysts 必须精选 3-5 条、最多 6 条，当前 {count}。")
    else:
        for i, c in enumerate(catalysts):
            if not isinstance(c, dict):
                errors.append(f"catalysts[{i}] 不是对象。")
                continue
            for key in ("date", "tone", "category", "source_name", "title", "fact", "url", "why", "verify"):
                require_text(c, key, f"catalysts[{i}].{key}", errors)
            src = c.get("source") if isinstance(c.get("source"), dict) else {}
            if src.get("lane") != "general_search":
                errors.append(f"catalysts[{i}] 必须标注 source.lane=general_search。")
            try:
                tier = int(src.get("tier"))
            except (TypeError, ValueError):
                tier = None
            if tier not in (1, 2):
                errors.append(f"catalysts[{i}] 的 source.tier 必须为 1 或 2。")

    stocks = p.get("stocks") or []
    if not isinstance(stocks, list) or len(stocks) != 10:
        count = len(stocks) if isinstance(stocks, list) else "非数组"
        errors.append(f"stocks 必须恰好 10 只，当前 {count}。")
    groups = p.get("divergence_groups") if isinstance(p.get("divergence_groups"), dict) else {}
    for group in GROUP_ORDER:
        item = groups.get(group)
        if not isinstance(item, dict):
            errors.append(f"divergence_groups 缺少分组对象：{group}。")
            continue
        if not isinstance(item.get("stocks"), list):
            errors.append(f"divergence_groups.{group}.stocks 必须为数组。")
        require_text(item, "feature", f"divergence_groups.{group}.feature", errors)

    hydration = p.get("_facts_hydration") if isinstance(p.get("_facts_hydration"), dict) else {}
    expected_hash = str(hydration.get("stocks_sha256") or "").strip()
    if not expected_hash:
        errors.append("payload 缺少 _facts_hydration.stocks_sha256 —— 必须先运行 hydrate_payload_from_facts.py。")
    else:
        actual_hash = _stock_transfer_hash(p)
        if actual_hash != expected_hash:
            errors.append("payload 的 stocks / divergence_groups 与 facts 自动映射结果不一致——请重新运行 hydrate_payload_from_facts.py。")

    watch = p.get("watch_signals") or []
    if not isinstance(watch, list) or not (3 <= len(watch) <= 4):
        count = len(watch) if isinstance(watch, list) else "非数组"
        errors.append(f"watch_signals 必须 3-4 条，当前 {count}。")
    else:
        seen = set()
        for i, w in enumerate(watch):
            if not isinstance(w, dict):
                errors.append(f"watch_signals[{i}] 不是对象。")
                continue
            sig = re.sub(r"\s+", "", str(w.get("signal") or "")).lower()
            if sig and sig in seen:
                errors.append(f"watch_signals[{i}] signal 重复。")
            seen.add(sig)
            for key in ("signal", "watch", "improve", "worsen"):
                require_text(w, key, f"watch_signals[{i}].{key}", errors)
                if INTERNAL_HEAT_SCORE_RE.search(str(w.get(key) or "")):
                    errors.append(f"watch_signals[{i}].{key} 含内部热度加减分语言。")

    risks = p.get("risks") or []
    if not isinstance(risks, list) or len(risks) < 3:
        count = len(risks) if isinstance(risks, list) else "非数组"
        errors.append(f"risks 至少 3 条，当前 {count}。")
    else:
        for i, r in enumerate(risks):
            if not isinstance(r, dict):
                errors.append(f"risks[{i}] 不是对象。")
                continue
            for key in ("title", "trigger", "why", "invalidate"):
                require_text(r, key, f"risks[{i}].{key}", errors)

    sources = p.get("sources") or []
    if not isinstance(sources, list) or len(sources) < 1:
        errors.append("sources 至少 1 条。")
    else:
        for i, source in enumerate(sources):
            if not isinstance(source, dict):
                errors.append(f"sources[{i}] 不是对象。")
                continue
            require_text(source, "name", f"sources[{i}].name", errors)
            if not str(source.get("title") or source.get("purpose") or source.get("usage") or "").strip():
                warnings.append(f"sources[{i}] 缺少 title / purpose / usage，建议从模块6原句搬运。")

    mode = str(p.get("data_mode") or "full").strip().lower()
    if mode != "full":
        errors.append(f"data_mode=“{mode}” 非法；当前只允许 full。")
    if str(p.get("data_note") or "").strip():
        errors.append("data_note 已废弃；不要用 10 股样本替代板块指标，也不要写替代口径说明。")

    try:
        for msg in _mc.hard_checks(p):
            errors.append(msg)
        reg_err, reg_warn = _mc.registry_checks(p)
        errors.extend(reg_err)
        warnings.extend(reg_warn)
    except Exception as exc:
        warnings.append(f"复算门执行异常（请检查 typed 分量字段类型）：{exc}")

    if errors:
        msg = "payload 未通过飞书文档写入前校验，发现 %d 处硬错误：\n" % len(errors)
        msg += "\n".join(f"  [{i + 1}] {m}" for i, m in enumerate(errors))
        raise PayloadError(msg)
    return warnings


def main():
    ap = argparse.ArgumentParser(description="飞书文档 payload 写入前校验")
    ap.add_argument("payload", help="payload.json 路径")
    args = ap.parse_args()
    with open(args.payload, encoding="utf-8") as f:
        payload = json.load(f)
    try:
        warnings = validate_payload(payload)
    except PayloadError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)
    for msg in warnings:
        print("[警告] " + msg, file=sys.stderr)
    print("payload 校验通过（飞书文档写入前检查）")


if __name__ == "__main__":
    main()
