#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
date_calculator.py — 刑期日期精确计算器
==========================================
置信度: 95%
用途: Phase 4 羁押折抵计算后交叉验证 LLM 推导结果
依赖: 纯 Python 标准库，无第三方依赖

功能:
  1. 日期天数差精确计算（含跨年/闰年/月份天数处理）
  2. 分段羁押天数求和
  3. LLM 推导天数 vs 脚本计算天数 交叉验证
"""

import sys
from datetime import date, timedelta


def days_between(start: str, end: str, inclusive: bool = True) -> int:
    """
    计算两个日期之间的天数差。
    
    Args:
        start:    起始日期，格式 YYYY-MM-DD
        end:      终止日期，格式 YYYY-MM-DD
        inclusive: True=含首尾均计（事实描述用，如"羁押了448天"）
                   False=数学差（折抵计算用，如"折抵基数447天"）
    
    Returns:
        天数差（int）
        inclusive=True:  2024-03-15 → 2024-03-16 = 2天（含首尾均计）
        inclusive=False: 2024-03-15 → 2024-03-16 = 1天（数学差）
    
    ⚠️ 折抵计算必须使用 inclusive=False（数学差），否则释放日偏早1天。
       依据：刑诉法解释第202条，折抵的数学含义是"从判决日往回推N天"。
    
    Example:
        >>> days_between("2024-03-15", "2024-03-16", inclusive=True)
        2
        >>> days_between("2024-03-15", "2024-03-16", inclusive=False)
        1
    """
    try:
        d_start = date.fromisoformat(start)
        d_end = date.fromisoformat(end)
        delta = (d_end - d_start).days + (1 if inclusive else 0)
        return delta
    except ValueError as e:
        raise ValueError(f"日期格式错误（需 YYYY-MM-DD）: {e}")


def is_leap_year(year: int) -> bool:
    """
    判断是否为闰年。
    
    规则: 能被4整除但不能被100整除，或能被400整除。
    
    Example:
        >>> is_leap_year(2024)
        True
        >>> is_leap_year(2023)
        False
    """
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)


def total_custody_days(segments: list[dict], include_custody_type: bool = False) -> dict:
    """
    计算分段羁押总天数。
    
    Args:
        segments: 羁押段列表，每段格式:
            [
                {"start": "2024-03-15", "end": "2024-05-20", "label": "刑事拘留"},
                {"start": "2024-08-01", "end": "2025-06-05", "label": "逮捕"},
                {"start": "2024-06-01", "end": "2024-07-31", "label": "指定居所监视居住",
                 "custody_type": "指定居所监视居住"},  # 可选，默认为"羁押"
            ]
        include_custody_type: 是否区分羁押类型（用于指定居所监视居住2:1折抵）
    
    Returns:
        {
            "segments": [{"start":..., "end":..., "label":..., "days_inclusive": int,
                          "days_math": int, "custody_type": str, "leap_crossed": bool}],
            "total_days_inclusive": int,  # 含首尾总天数（事实描述用）
            "total_days_math": int,       # 数学差总天数（折抵计算用）
            "has_discontinuity": bool,
            "leap_years_crossed": [int, ...],
            "custody_type_breakdown": {...},  # 按类型分组的折抵基数
        }
    
    ⚠️ v2.2.0 重大修正：
      - 新增 days_math（数学差）字段，用于折抵计算
      - 含首尾天数（days_inclusive）仅用于O3明细表的事实描述
      - 折抵计算必须使用 total_days_math，否则释放日偏早1天
    
    Example:
        >>> result = total_custody_days([
        ...     {"start": "2024-03-15", "end": "2024-05-20", "label": "刑事拘留"},
        ...     {"start": "2024-08-01", "end": "2025-06-05", "label": "逮捕"},
        ... ])
        >>> result["total_days_math"]
        375
    """
    total_inclusive = 0
    total_math = 0
    detailed_segments = []
    leap_years = set()
    has_discontinuity = False
    type_breakdown = {}  # {custody_type: math_days_sum}

    # 排序：按起始日期升序
    sorted_segments = sorted(segments, key=lambda s: s["start"])

    for i, seg in enumerate(sorted_segments):
        days_incl = days_between(seg["start"], seg["end"], inclusive=True)   # 含首尾（事实描述）
        days_math = days_between(seg["start"], seg["end"], inclusive=False)   # 数学差（折抵用）
        total_inclusive += days_incl
        total_math += days_math

        # 羁押类型（默认"羁押"）
        custody_type = seg.get("custody_type", "羁押")
        type_breakdown[custody_type] = type_breakdown.get(custody_type, 0) + days_math

        # 检查是否跨越闰年
        start_year = date.fromisoformat(seg["start"]).year
        end_year = date.fromisoformat(seg["end"]).year
        leap_crossed = False
        for y in range(start_year, end_year + 1):
            if is_leap_year(y):
                leap_years.add(y)
                leap_crossed = True

        detailed_segments.append({
            "start": seg["start"],
            "end": seg["end"],
            "label": seg.get("label", ""),
            "days_inclusive": days_incl,
            "days_math": days_math,
            "custody_type": custody_type,
            "leap_crossed": leap_crossed,
        })

        # 检查羁押是否有中断（前一段结束日与后一段起始日不连续）
        if i > 0:
            prev_end = date.fromisoformat(sorted_segments[i - 1]["end"])
            curr_start = date.fromisoformat(seg["start"])
            if (curr_start - prev_end).days > 1:
                has_discontinuity = True

    return {
        "segments": detailed_segments,
        "total_days_inclusive": total_inclusive,
        "total_days_math": total_math,
        "has_discontinuity": has_discontinuity,
        "leap_years_crossed": sorted(list(leap_years)),
        "custody_type_breakdown": type_breakdown,
    }


def cross_validate(llm_days: int, script_days: int) -> dict:
    """
    交叉验证 LLM 推导的天数 vs 脚本计算的天数。
    
    Args:
        llm_days:    LLM 推导的羁押天数
        script_days: 脚本精确计算的羁押天数
    
    Returns:
        {
            "match": bool,          # 是否一致
            "deviation": int,       # 偏差天数（0 = 无偏差）
            "confidence": str,      # "high" | "warning" | "error"
            "recommendation": str,  # 建议
        }
    """
    deviation = abs(llm_days - script_days)
    
    if deviation == 0:
        return {
            "match": True,
            "deviation": 0,
            "confidence": "high",
            "recommendation": "LLM 推导与脚本计算一致，天数可信。",
        }
    elif deviation <= 2:
        return {
            "match": False,
            "deviation": deviation,
            "confidence": "warning",
            "recommendation": f"LLM 推导偏差 {deviation} 天，建议以脚本计算值 {script_days} 天为准。请核实羁押起止日期是否精确。",
        }
    else:
        return {
            "match": False,
            "deviation": deviation,
            "confidence": "error",
            "recommendation": f"LLM 推导偏差 {deviation} 天（≥3天），以脚本计算值 {script_days} 天为准。请逐一核实每段羁押起止日期。",
        }


def months_to_days(start_date: str, months: int) -> dict:
    """
    按刑诉法解释第202条逐月推算：以月计算的刑期，自本月某日至下月同日的前1日为1个月。
    
    废弃"30天/月"概算——29个月×30=870天（误差13天），逐月推算=883天。
    
    Args:
        start_date: 刑期起算日，格式 YYYY-MM-DD
        months:      月数（如29个月）
    
    Returns:
        {
            "start_date": str,           # 起算日
            "months": int,               # 月数
            "end_date": str,             # 刑期终止日（最后1个月的同日的前1日）
            "total_days_inclusive": int,  # 含首尾总天数
            "total_days_math": int,       # 数学差天数
            "monthly_breakdown": [        # 逐月明细
                {"month": 1, "start": "...", "end": "...", "days": 31},
                ...
            ]
        }
    
    规则（刑诉法解释第202条）：
      - 自本月某日至下月同日的前1日为1个月
      - 下月无同日 → 本月末日为1个月的最后一日
      - 2月28/29天、大小月31/30天均自动处理
    
    Example:
        >>> result = months_to_days("2024-03-15", 29)
        >>> result["total_days_math"]
        882
        >>> result["end_date"]
        '2026-08-14'
    """
    d_start = date.fromisoformat(start_date)
    current = d_start
    breakdown = []
    
    for m in range(1, months + 1):
        # 计算"下月同日"
        month_start = current
        
        # 推算下月同日
        next_month = current.month + 1
        next_year = current.year
        if next_month > 12:
            next_month = 1
            next_year += 1
        
        # 下月同日的前1日 = 本月的天数即为该月的天数
        try:
            same_day_next = date(next_year, next_month, current.day)
            month_end = same_day_next - timedelta(days=1)  # 前一日
        except ValueError:
            # 下月无同日（如1月31日→2月无31日）→ 取下月最后一天
            # 实际上：下月同日不存在时，本月末日即为该月末日
            # 先找到下月最后一天
            if next_month == 12:
                last_of_next = date(next_year + 1, 1, 1) - timedelta(days=1)
            else:
                last_of_next = date(next_year, next_month + 1, 1) - timedelta(days=1)
            month_end = last_of_next
            same_day_next = last_of_next + timedelta(days=1)  # 仅用于推进current
        
        month_days = (month_end - month_start).days + 1  # 含首尾
        
        breakdown.append({
            "month": m,
            "start": month_start.isoformat(),
            "end": month_end.isoformat(),
            "days": month_days,
        })
        
        # 推进到下月同日（即下一段的起始日）
        current = month_end + timedelta(days=1)
    
    end_date = breakdown[-1]["end"]
    total_inclusive = sum(b["days"] for b in breakdown)
    total_math = (date.fromisoformat(end_date) - d_start).days
    
    return {
        "start_date": start_date,
        "months": months,
        "end_date": end_date,
        "total_days_inclusive": total_inclusive,
        "total_days_math": total_math,
        "monthly_breakdown": breakdown,
    }


def calculate_offset_days(custody_result: dict, penalty_type: str) -> dict:
    """
    根据羁押类型和主刑类型，计算总折抵天数。
    
    羁押折抵比例：
      - 羁押 + 管制 = 1:2（羁押1日折抵2日）
      - 羁押 + 拘役/有期徒刑 = 1:1
      - 指定居所监视居住 + 管制 = 1:1（刑诉法第76条）
      - 指定居所监视居住 + 拘役/有期徒刑 = 2:1（监视居住2日折抵1日）
    
    Args:
        custody_result: total_custody_days() 的返回值
        penalty_type:   主刑类型 "管制" | "拘役" | "有期徒刑"
    
    Returns:
        {
            "offset_days": int,               # 总折抵天数
            "details": [                       # 各段折抵明细
                {"label":..., "custody_type":..., "math_days":..., "ratio":..., "offset_days":...}
            ],
            "penalty_type": str,
        }
    """
    # 折抵比例映射：{custody_type: {penalty_type: ratio}}
    # ratio 含义：羁押ratio日折抵刑期1日（即 ratio:1）
    OFFSET_RATIOS = {
        "羁押": {"管制": 0.5, "拘役": 1, "有期徒刑": 1},        # 管制1:2, 拘役/有期1:1
        "指定居所监视居住": {"管制": 1, "拘役": 2, "有期徒刑": 2},  # 管制1:1, 拘役/有期2:1
    }
    
    total_offset = 0
    details = []
    
    for seg in custody_result["segments"]:
        ctype = seg.get("custody_type", "羁押")
        math_days = seg.get("days_math", seg.get("days", 0))
        
        ratio_map = OFFSET_RATIOS.get(ctype, OFFSET_RATIOS["羁押"])
        ratio = ratio_map.get(penalty_type, 1)
        
        # 折抵天数 = 羁押天数 ÷ ratio（向下取整，有利于被告人取整后向上取）
        # 实务：折抵天数按完整日计算，余数不利被告人时四舍五入
        seg_offset = math_days // ratio if ratio >= 1 else math_days * 2
        # ratio=0.5 时（管制1:2），折抵天数 = 羁押天数 × 2
        # ratio=1 时（1:1），折抵天数 = 羁押天数
        # ratio=2 时（2:1），折抵天数 = 羁押天数 ÷ 2（向下取整）
        
        if ratio == 0.5:
            seg_offset = math_days * 2
        elif ratio == 1:
            seg_offset = math_days
        elif ratio == 2:
            seg_offset = math_days // 2  # 监视居住2:1，不足2日部分不折抵
        else:
            seg_offset = math_days
        
        total_offset += seg_offset
        details.append({
            "label": seg.get("label", ""),
            "custody_type": ctype,
            "math_days": math_days,
            "ratio": f"{ratio}:1" if ratio >= 1 else f"1:{int(1/ratio)}",
            "offset_days": seg_offset,
        })
    
    return {
        "offset_days": total_offset,
        "details": details,
        "penalty_type": penalty_type,
    }


def calculate_release_date(judgment_date: str, remaining_days: int) -> str:
    """
    根据判决日和剩余刑期天数计算预计释放日。
    
    Args:
        judgment_date: 判决日，格式 YYYY-MM-DD
        remaining_days: 折抵后剩余刑期天数
    
    Returns:
        预计释放日，格式 YYYY-MM-DD
    
    Example:
        >>> calculate_release_date("2025-06-05", 432)
        '2026-08-11'
    """
    d_judgment = date.fromisoformat(judgment_date)
    d_release = d_judgment + timedelta(days=remaining_days)
    return d_release.isoformat()


def main():
    """CLI 入口：支持命令行调用验证。"""
    import json
    
    if len(sys.argv) < 2:
        print("用法:")
        print("  python date_calculator.py --cross-validate <llm_days> <script_days>")
        print("  python date_calculator.py --segments '<json>'")
        print("  python date_calculator.py --release <judgment_date> <remaining_days>")
        print("  python date_calculator.py --months-to-days <start_date> <months>")
        print("  python date_calculator.py --offset '<custody_json>' <penalty_type>")
        print()
        print("示例:")
        print('  python date_calculator.py --segments \'[{"start":"2024-03-15","end":"2025-06-05","label":"羁押"}]\'')
        print("  python date_calculator.py --cross-validate 448 448")
        print("  python date_calculator.py --release 2025-06-05 432")
        print('  python date_calculator.py --months-to-days 2024-03-15 29')
        print('  python date_calculator.py --offset \'{"segments":[{"start":"2024-03-15","end":"2025-06-05","label":"羁押"}]}\' 有期徒刑')
        sys.exit(0)
    
    if sys.argv[1] == "--cross-validate" and len(sys.argv) >= 4:
        llm_days = int(sys.argv[2])
        script_days = int(sys.argv[3])
        result = cross_validate(llm_days, script_days)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif sys.argv[1] == "--segments" and len(sys.argv) >= 3:
        segments = json.loads(sys.argv[2])
        result = total_custody_days(segments)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif sys.argv[1] == "--release" and len(sys.argv) >= 4:
        jd = sys.argv[2]
        remaining = int(sys.argv[3])
        print(calculate_release_date(jd, remaining))
    
    elif sys.argv[1] == "--months-to-days" and len(sys.argv) >= 4:
        start = sys.argv[2]
        months = int(sys.argv[3])
        result = months_to_days(start, months)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif sys.argv[1] == "--offset" and len(sys.argv) >= 4:
        custody_data = json.loads(sys.argv[2])
        penalty_type = sys.argv[3]
        # 先计算羁押天数
        if "segments" in custody_data:
            custody_result = total_custody_days(custody_data["segments"])
        else:
            custody_result = total_custody_days(custody_data)
        offset_result = calculate_offset_days(custody_result, penalty_type)
        print(json.dumps(offset_result, ensure_ascii=False, indent=2))
    
    else:
        print("未知参数，请使用 --help 查看用法")
        sys.exit(1)


if __name__ == "__main__":
    main()
