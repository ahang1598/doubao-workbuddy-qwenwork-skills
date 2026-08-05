#!/usr/bin/env python3
"""Post-process MCP shop operation data into a diagnostic report."""

from __future__ import annotations

from typing import Any


DATE_TYPE_LABELS = {
    "RECENT_1": "近1天",
    "RECENT_7": "近7天",
    "RECENT_30": "近30天",
}

VALID_DATE_TYPES = {"RECENT_1", "RECENT_7", "RECENT_30"}
RANKING_DATE_TYPES = {"RECENT_7", "RECENT_30"}

CORE_METRIC_NAMES = {
    "impression": "展现次数",
    "visitor": "访客数",
    "page_view": "浏览量",
    "click_cvr": "点击转化率",
    "pay_cvr": "支付转化率",
    "buyer_count": "支付买家数",
    "pay_amount": "支付金额",
}

CORE_METRIC_ORDER = [
    "impression",
    "visitor",
    "page_view",
    "click_cvr",
    "pay_cvr",
    "buyer_count",
    "pay_amount",
]


def build_report(payload: dict[str, Any]) -> dict[str, Any]:
    """Build a markdown report from MCP tool results.

    The input accepts direct MCP results or common wrappers such as
    {"success": true, "data": {"data": {...}}}.
    """

    if not isinstance(payload, dict):
        raise ValueError("输入必须是 JSON 对象")

    date_type = payload.get("date_type") or "RECENT_7"
    if date_type not in VALID_DATE_TYPES:
        raise ValueError(f"date_type 必须为 {', '.join(sorted(VALID_DATE_TYPES))} 之一，当前值: {date_type}")

    core = _unwrap_result(payload.get("get_core_metrics") or payload.get("core_metrics"))
    traffic = _unwrap_result(payload.get("get_traffic_structure") or payload.get("traffic_structure"))
    ranking = None
    if date_type in RANKING_DATE_TYPES:
        ranking = _unwrap_result(payload.get("get_transaction_ranking") or payload.get("transaction_ranking"), optional=True)
    customer = _unwrap_result(payload.get("get_customer_profile") or payload.get("customer_profile"))

    sections: list[str] = [_report_title(date_type, core, traffic, ranking, customer)]
    sections.append(_core_metrics_section(core))
    sections.append(_traffic_section(traffic))

    ranking_available = _is_ranking_available(ranking)
    next_section_no = 3
    if ranking_available:
        sections.append(_industry_section(ranking, next_section_no))
        next_section_no += 1

    sections.append(_customer_section(customer, next_section_no))
    next_section_no += 1
    sections.append(_diagnosis_section(core, traffic, ranking if ranking_available else None, customer, next_section_no))
    sections.append("---\n\n如需深入了解某个方面（流量优化 / 转化提升 / 客户运营），或希望基于诊断结论生成月度经营规划，请告知。")

    markdown = "\n\n".join(sections)
    return {
        "markdown": markdown,
        "data": {
            "date_type": date_type,
            "industry_section_included": ranking_available,
            "module_status": {
                "core_metrics": _module_status(core),
                "traffic_structure": _module_status(traffic),
                "transaction_ranking": "skipped" if date_type == "RECENT_1" else _module_status(ranking),
                "customer_profile": _module_status(customer),
            },
        },
    }


def _unwrap_result(value: Any, optional: bool = False) -> dict[str, Any] | None:
    if value is None:
        if optional:
            return None
        return {"__unavailable__": True, "__reason__": "数据暂不可用"}

    if not isinstance(value, dict):
        return {"__unavailable__": True, "__reason__": "格式异常，请稍后重试"}

    if value.get("success") is False or value.get("__success__") is False:
        return {
            "__unavailable__": True,
            "__reason__": value.get("markdown") or value.get("message") or value.get("__msgInfo__") or "数据暂不可用",
        }

    data = value.get("data", value)
    if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict):
        data = data["data"]

    if not isinstance(data, dict):
        return {"__unavailable__": True, "__reason__": "格式异常，请稍后重试"}
    return data


def _module_status(data: dict[str, Any] | None) -> str:
    if data is None:
        return "skipped"
    return "unavailable" if data.get("__unavailable__") else "ok"


def _is_unavailable(data: dict[str, Any] | None) -> bool:
    return data is None or bool(data.get("__unavailable__"))


def _report_title(date_type: str, *modules: dict[str, Any] | None) -> str:
    date_range = {}
    for module in modules:
        if isinstance(module, dict) and isinstance(module.get("date_range"), dict):
            date_range = module["date_range"]
            break

    start_date = date_range.get("start_date")
    end_date = date_range.get("end_date")
    if start_date and end_date:
        suffix = f"{start_date} 至 {end_date}"
    else:
        suffix = DATE_TYPE_LABELS.get(date_type, date_type)
    return f"# 店铺经营健康诊断报告（{suffix}）"


def _core_metrics_section(core: dict[str, Any] | None) -> str:
    if _is_unavailable(core):
        return "## 一、核心指标 vs 同行同层\n\n数据暂不可用"

    metrics = core.get("core_metrics") or core.get("metrics") or []
    metrics = _ensure_list(metrics)
    by_code = {_pick(item, "metric_code", "code", "key"): item for item in metrics if isinstance(item, dict)}

    lines = [
        "## 一、核心指标 vs 同行同层",
        "",
        "| 指标 | 本店 | 同行同层均值 | 达标率 | 评级 |",
        "|------|------|--------------|--------|------|",
    ]
    for code in CORE_METRIC_ORDER:
        item = by_code.get(code, {})
        name = _pick(item, "metric_name", "name") or CORE_METRIC_NAMES[code]
        my_value = _format_metric_value(code, _pick(item, "my_value", "value", "current_value", "shop_value"))
        peer_avg = _format_metric_value(code, _pick(item, "peer_avg", "peer_average", "avg_value", "peer_value"))
        ratio = _format_percent(_pick(item, "ratio_to_peer", "ratio", "achievement_rate"), default="数据暂不可用")
        rating = _rating_with_icon(_pick(item, "rating", "level") or _infer_rating(_pick(item, "ratio_to_peer", "ratio")))
        lines.append(f"| {name} | {my_value} | {peer_avg} | {ratio} | {rating} |")

    lines.append("")
    lines.append("> 达标率 = 本店 / 同行同层均值。评级标准：优秀(>=110%) / 持平(90%-110%) / 略低(50%-90%) / 极低(<50%)。")

    trend = core.get("trend")
    if trend:
        lines.append("")
        lines.append("**趋势数据说明**：`pay_cvr`、`pay_amount` 等趋势字段缺失时统一标注“数据暂不可用”，不得补造。")
    return "\n".join(lines)


def _traffic_section(traffic: dict[str, Any] | None) -> str:
    if _is_unavailable(traffic):
        return "## 二、流量结构分析\n\n数据暂不可用"

    data = traffic.get("traffic", traffic)
    sources = _ensure_list(data.get("sources") or data.get("source_rank") or data.get("traffic_sources") or data.get("source_list"))
    lines = [
        "## 二、流量结构分析",
        "",
        "**来源分布**：",
        "",
        "| 流量来源 | 访客数 | 占比 |",
        "|---------|--------|------|",
    ]
    if sources:
        for source in sources[:10]:
            name = _pick(source, "source", "source_name", "name", "channel") or "数据暂不可用"
            visitors = _format_number(_pick(source, "visitors", "visitor", "visitor_count", "uv"))
            ratio = _format_percent(_pick(source, "ratio", "percent", "percentage"))
            lines.append(f"| {name} | {visitors} | {ratio} |")
    else:
        lines.append("| 数据暂不可用 | 数据暂不可用 | 数据暂不可用 |")

    lines.extend([
        "",
        "**关键指标**：",
        "",
        "| 指标 | 数值 | 判断 |",
        "|------|------|------|",
    ])
    new_ratio = _pick(data, "new_visitor_ratio", "newVisitorRatio")
    bounce_rate = _pick(data, "bounce_rate", "bounceRate")
    avg_page = _pick(data, "avg_page_per_visit", "avgPagePerVisit", "pv_per_uv")
    lines.append(f"| 新访客占比 | {_format_percent(new_ratio)} | {_judge_new_visitor(new_ratio)} |")
    lines.append(f"| 跳失率 | {_format_percent(bounce_rate)} | {_judge_bounce_rate(bounce_rate)} |")
    lines.append(f"| 人均浏览量 | {_format_number(avg_page)} | {_judge_avg_page(avg_page)} |")

    keywords = _ensure_list(data.get("search_keywords") or data.get("keywords") or data.get("top_keywords"))
    keyword_names = [_pick(k, "keyword", "word", "name") if isinstance(k, dict) else k for k in keywords[:5]]
    lines.append("")
    lines.append(f"**入店热搜词 TOP5**：{_join_or_unavailable(keyword_names)}")
    return "\n".join(lines)


def _industry_section(ranking: dict[str, Any], section_no: int) -> str:
    benchmark = ranking.get("benchmark") or {}
    my_pay_amount = _pick(ranking, "my_pay_amount", "pay_amount")
    return "\n".join([
        f"## {_section_no(section_no)}、行业定位",
        "",
        f"**所属行业**：{ranking.get('industry_name', '数据暂不可用')}",
        "",
        "| 指标 | 数值 |",
        "|------|------|",
        f"| 支付金额 | {_format_money(my_pay_amount)} |",
        f"| 行业排名 | {_format_rank(ranking.get('industry_rank'))} |",
        f"| 行业店铺总数 | {_format_number(ranking.get('industry_total'))} |",
        f"| 排名百分位 | {_format_rank_percentile(ranking.get('rank_percentile'))} |",
        "",
        "**标杆对比**：",
        "",
        "| 标杆层级 | 平均支付金额 | 与本店差距 |",
        "|---------|------------|----------|",
        f"| TOP3 平均 | {_format_money(benchmark.get('top3_avg'))} | {_format_gap(my_pay_amount, benchmark.get('top3_avg'))} |",
        f"| TOP10 平均 | {_format_money(benchmark.get('top10_avg'))} | {_format_gap(my_pay_amount, benchmark.get('top10_avg'))} |",
        f"| TOP100 平均 | {_format_money(benchmark.get('top100_avg'))} | {_format_gap(my_pay_amount, benchmark.get('top100_avg'))} |",
    ])


def _customer_section(customer: dict[str, Any] | None, section_no: int) -> str:
    if _is_unavailable(customer):
        return f"## {_section_no(section_no)}、客户健康度\n\n数据暂不可用"

    data = customer.get("customer", customer)
    rows = [
        ("支付买家数", "buyer_count", "pay_buyer_count"),
        ("L会员买家数", "l_member_buyer_count", "member_buyer_count"),
        ("客户数", "customer_count", "customers"),
        ("买家回头率", "repurchase_rate", "return_rate"),
    ]
    lines = [
        f"## {_section_no(section_no)}、客户健康度",
        "",
        "| 指标 | 本店 | 同行优秀 | 差距 |",
        "|------|------|----------|------|",
    ]
    for label, *keys in rows:
        mine = _pick(data, *keys, f"my_{keys[0]}")
        peer = _pick(data, f"peer_excellent_{keys[0]}", f"excellent_{keys[0]}", f"peer_{keys[0]}")
        formatter = _format_percent if "rate" in keys[0] else _format_number
        lines.append(f"| {label} | {formatter(mine)} | {formatter(peer)} | {_format_delta(mine, peer, formatter)} |")

    new_gmv = _pick(data, "new_customer_gmv", "new_buyer_gmv")
    old_gmv = _pick(data, "old_customer_gmv", "old_buyer_gmv")
    avg_order = _pick(data, "avg_order_value", "customer_unit_price")
    lines.append("")
    lines.append(f"**新老客贡献**：新客 {_format_money(new_gmv)} / 老客 {_format_money(old_gmv)} | 客单价 {_format_money(avg_order)}")
    return "\n".join(lines)


def _diagnosis_section(core: dict[str, Any] | None, traffic: dict[str, Any] | None,
                       ranking: dict[str, Any] | None, customer: dict[str, Any] | None,
                       section_no: int) -> str:
    bottlenecks = []
    bottlenecks.extend(_core_bottlenecks(core))
    bottlenecks.extend(_traffic_bottlenecks(traffic))
    bottlenecks.extend(_industry_bottlenecks(ranking))
    bottlenecks.extend(_customer_bottlenecks(customer))
    bottlenecks = bottlenecks[:3] or [("数据完整性不足", "严重", "关键模块数据暂不可用", "请稍后重试或检查 MCP 工具返回。")]

    lines = [f"## {_section_no(section_no)}、瓶颈诊断与改善方向", "", "**核心瓶颈**：", ""]
    for idx, (name, severity, evidence, suggestion) in enumerate(bottlenecks, start=1):
        lines.append(f"{idx}. **{name}**（{severity}）")
        lines.append(f"   - 数据依据：{evidence}")
        lines.append(f"   - 改善方向：{suggestion}")
    return "\n".join(lines)


def _core_bottlenecks(core: dict[str, Any] | None) -> list[tuple[str, str, str, str]]:
    if _is_unavailable(core):
        return [("核心指标不可用", "严重", "核心指标模块数据暂不可用", "先恢复核心指标查询，再判断转化或流量瓶颈。")]
    results = []
    for item in _ensure_list(core.get("core_metrics")):
        code = _pick(item, "metric_code", "code", "key")
        rating = _pick(item, "rating", "level") or _infer_rating(_pick(item, "ratio_to_peer", "ratio"))
        if rating in {"略低", "极低"}:
            name = _pick(item, "metric_name", "name") or CORE_METRIC_NAMES.get(code, code or "核心指标")
            ratio = _format_percent(_pick(item, "ratio_to_peer", "ratio", "achievement_rate"))
            severity = "严重" if rating == "极低" else "中等"
            results.append((f"{name}低于同行", severity, f"{name}达标率 {ratio}，评级 {rating}", "优先定位该指标的上游漏斗环节，并围绕商品曝光、点击或转化做专项优化。"))
    return results


def _traffic_bottlenecks(traffic: dict[str, Any] | None) -> list[tuple[str, str, str, str]]:
    if _is_unavailable(traffic):
        return []
    data = traffic.get("traffic", traffic)
    bounce = _to_float(_pick(data, "bounce_rate", "bounceRate"))
    if bounce is not None and bounce >= 0.7:
        return [("入店承接偏弱", "中等", f"跳失率达到 {_format_percent(bounce)}", "优化主推商品首屏卖点、价格力与店铺承接页，降低单页跳出。")]
    return []


def _industry_bottlenecks(ranking: dict[str, Any] | None) -> list[tuple[str, str, str, str]]:
    if _is_unavailable(ranking):
        return []
    percentile = _to_float(ranking.get("rank_percentile"))
    if percentile is not None and percentile > 0.5:
        return [("行业排名偏后", "中等", f"行业排名百分位 {_format_rank_percentile(percentile)}", "对标行业 TOP100 的支付规模，优先提升高转化品类和核心商品供给。")]
    return []


def _customer_bottlenecks(customer: dict[str, Any] | None) -> list[tuple[str, str, str, str]]:
    if _is_unavailable(customer):
        return []
    data = customer.get("customer", customer)
    repurchase = _to_float(_pick(data, "repurchase_rate", "return_rate"))
    if repurchase is not None and repurchase < 0.15:
        return [("老客复购不足", "中等", f"买家回头率 {_format_percent(repurchase)}", "建立老客分层触达和复购优惠，提升老客 GMV 占比。")]
    return []


def _is_ranking_available(ranking: dict[str, Any] | None) -> bool:
    return bool(ranking and not ranking.get("__unavailable__") and ranking.get("industry_name"))


def _ensure_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return list(value.values())
    return []


def _pick(data: Any, *keys: str) -> Any:
    if not isinstance(data, dict):
        return None
    for key in keys:
        if key in data:
            return data[key]
    return None


def _to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(str(value).strip().rstrip("%"))
    except (TypeError, ValueError):
        return None


def _format_number(value: Any, default: str = "数据暂不可用") -> str:
    number = _to_float(value)
    if number is None:
        return default
    if number.is_integer():
        return f"{int(number):,}"
    return f"{number:,.2f}"


def _format_money(value: Any) -> str:
    number = _to_float(value)
    if number is None:
        return "数据暂不可用"
    return f"¥{number:,.2f}"


def _format_percent(value: Any, default: str = "数据暂不可用") -> str:
    number = _to_float(value)
    if number is None:
        return default
    if abs(number) <= 1:
        number *= 100
    return f"{number:.1f}%"


def _format_metric_value(code: str, value: Any) -> str:
    if code == "pay_amount":
        return _format_money(value)
    if code in {"click_cvr", "pay_cvr"}:
        return _format_percent(value)
    return _format_number(value)


def _format_rank(value: Any) -> str:
    number = _to_float(value)
    if number is None:
        return "数据暂不可用"
    return f"第 {int(number):,} 名"


def _format_rank_percentile(value: Any) -> str:
    number = _to_float(value)
    if number is None:
        return "数据暂不可用"
    display = number * 100 if number <= 1 else number
    return f"{display:.2f}%（前{int(display)}%）"


def _format_gap(my_value: Any, benchmark: Any) -> str:
    mine = _to_float(my_value)
    bench = _to_float(benchmark)
    if mine is None or bench in (None, 0):
        return "数据暂不可用"
    return f"本店为标杆的 {mine / bench * 100:.1f}%"


def _format_delta(mine: Any, peer: Any, formatter) -> str:
    mine_num = _to_float(mine)
    peer_num = _to_float(peer)
    if mine_num is None or peer_num is None:
        return "数据暂不可用"
    delta = mine_num - peer_num
    prefix = "高于" if delta >= 0 else "低于"
    return f"{prefix}同行优秀 {formatter(abs(delta))}"


def _rating_with_icon(rating: str | None) -> str:
    icons = {"优秀": "优秀", "持平": "持平", "略低": "略低", "极低": "极低"}
    return icons.get(rating or "", rating or "数据暂不可用")


def _infer_rating(ratio: Any) -> str | None:
    value = _to_float(ratio)
    if value is None:
        return None
    if value >= 1.1:
        return "优秀"
    if value >= 0.9:
        return "持平"
    if value >= 0.5:
        return "略低"
    return "极低"


def _judge_new_visitor(value: Any) -> str:
    ratio = _to_float(value)
    if ratio is None:
        return "数据暂不可用"
    return "新客占比较高，需关注老客留存" if ratio > 0.75 else "结构相对稳定"


def _judge_bounce_rate(value: Any) -> str:
    ratio = _to_float(value)
    if ratio is None:
        return "数据暂不可用"
    return "偏高，入店承接需优化" if ratio >= 0.7 else "相对可控"


def _judge_avg_page(value: Any) -> str:
    number = _to_float(value)
    if number is None:
        return "数据暂不可用"
    return "浏览深度偏低" if number < 2 else "浏览深度正常"


def _join_or_unavailable(values: list[Any]) -> str:
    clean = [str(v) for v in values if v not in (None, "")]
    return "、".join(clean) if clean else "数据暂不可用"


def _section_no(value: int) -> str:
    return {1: "一", 2: "二", 3: "三", 4: "四", 5: "五"}.get(value, str(value))
