#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日期/期限一致性验证脚本 — verify_dates.py

用于合同审查 Step 2 Layer 3 §3.4.2 的期限精确计算验证。
LLM 提取结构化数据 → 本脚本执行确定性计算 → LLM 解读结果。

期限一致性判定（修复）:
    合同/授权期限按惯例多采用"闭区间含尾日"写法，例如
    "授权期 3 年，自 2026/5/1 起"，终止日写作 2029/4/30（含当日）即为完整 3 年。
    旧版用裸日期相减会把这种写法误判为"35 个月零 29 天"而触发 P0 不一致告警。
    现已新增 is_inclusive_term_match() 含尾日判定：
    当 end == start + 约定月数 - 1 天时，视为完整期限，判 PASS，消除此类误报。

用法:
    python3 verify_dates.py --json dates.json
    python3 verify_dates.py --json dates.json --output results.json

输入 JSON 格式:
{
  "review_date": "2026-04-14",              // 审查日期（当天），ISO 格式
  "contract_term": {                         // 合同整体期限
    "start_date": "2026-02-01",             // 可以为 null
    "end_date": "2027-01-01",               // 可以为 null
    "stated_duration": "1年",               // 约定时长文本，可以为 null
    "clause": "第10条"
  },
  "date_pairs": [                            // 需要校验的日期/期限对
    {
      "label": "保密期限",
      "clause": "第8条",
      "start_date": "2026-02-01",           // 可以为 null
      "end_date": "2029-01-31",             // 可以为 null
      "stated_duration": "3年",             // 可以为 null
      "relation_to_contract": "after_end"   // before_start / within / after_end / independent
    }
  ],
  "key_dates": [                             // 关键日期节点
    {
      "label": "首期付款日",
      "clause": "第4.1条",
      "date": "2026-03-01",
      "dependency": "合同生效后30日内"       // 可以为 null
    }
  ],
  "renewal": {                               // 续约条款，可以为 null
    "auto_renew": true,
    "renewal_period": "1年",
    "notice_days": 30,
    "clause": "第10.2条"
  }
}

输出: JSON 格式的验证结果。
"""

import argparse
import json
import re
import sys
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 日期解析
# ---------------------------------------------------------------------------

def parse_date(s: Optional[str]) -> Optional[date]:
    """解析日期字符串，支持多种格式。"""
    if not s:
        return None
    s = s.strip()
    # 尝试多种格式
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y年%m月%d日"):
        try:
            from datetime import datetime
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def parse_duration_months(text: Optional[str]) -> Optional[int]:
    """
    解析中文/数字时长描述为月数。
    支持: "1年", "2年", "6个月", "18个月", "1年6个月", "3年零6个月",
          "一年", "两年", "三年", "半年" 等。
    """
    if not text:
        return None
    text = text.strip()

    _CN_NUM = {
        '零': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4,
        '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
        '十一': 11, '十二': 12, '半': 0.5,
    }

    total_months = 0
    found = False

    # 匹配年
    year_patterns = [
        r'(\d+(?:\.\d+)?)\s*年',
        r'([一二两三四五六七八九十]+)\s*年',
    ]
    for pat in year_patterns:
        m = re.search(pat, text)
        if m:
            val = m.group(1)
            if val in _CN_NUM:
                total_months += int(_CN_NUM[val] * 12)
            else:
                try:
                    total_months += int(float(val) * 12)
                except ValueError:
                    pass
            found = True
            break

    # 匹配"半年"
    if '半年' in text and not found:
        total_months += 6
        found = True

    # 匹配月
    month_patterns = [
        r'(\d+(?:\.\d+)?)\s*(?:个月|月)',
        r'([一二两三四五六七八九十]+)\s*(?:个月|月)',
    ]
    for pat in month_patterns:
        m = re.search(pat, text)
        if m:
            val = m.group(1)
            if val in _CN_NUM:
                total_months += int(_CN_NUM[val])
            else:
                try:
                    total_months += int(float(val))
                except ValueError:
                    pass
            found = True
            break

    # 匹配天（转换为近似月数，仅做参考）
    day_patterns = [
        r'(\d+)\s*(?:天|日)',
    ]
    for pat in day_patterns:
        m = re.search(pat, text)
        if m:
            days = int(m.group(1))
            # 天数不转换为月数，单独返回
            if not found:
                return None  # 纯天数的情况返回 None，由调用方处理
            break

    return total_months if found else None


def calc_month_diff(start: date, end: date) -> Tuple[int, int]:
    """
    计算两个日期之间的精确月数和剩余天数。
    返回 (months, extra_days)。
    """
    months = (end.year - start.year) * 12 + (end.month - start.month)
    # 如果 end.day < start.day，实际不足整月
    if end.day < start.day:
        months -= 1
        # 计算剩余天数
        prev_month = end.month - 1 if end.month > 1 else 12
        prev_year = end.year if end.month > 1 else end.year - 1
        import calendar
        days_in_prev = calendar.monthrange(prev_year, prev_month)[1]
        extra_days = days_in_prev - start.day + end.day
    elif end.day > start.day:
        extra_days = end.day - start.day
    else:
        extra_days = 0

    return months, extra_days


def add_months(d: date, months: int) -> date:
    """在日期 d 上增加 months 个月，自动处理月末溢出（如 1/31 + 1 月 → 2/28）。"""
    import calendar
    total = (d.year * 12 + (d.month - 1)) + months
    year, month = divmod(total, 12)
    month += 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def is_inclusive_term_match(start: date, end: date, stated_months: int) -> bool:
    """
    判断 [start, end] 是否构成"含尾日"的完整约定期限。

    合同/授权期限的惯例写法是**闭区间含尾日**：
    "授权期 3 年，自 2026/5/1 起"，截止日写作 2029/4/30（含当日）即为完整 3 年。
    用裸日期相减（calc_month_diff）会把这种写法判成"35 个月零 29 天"而误报不一致，
    因为它没有把终止日当天计入期限。

    含尾日整期的判定标准：终止日 == 起始日按约定月数推算后的"前一天"。
        end == start + stated_months 个月 - 1 天

    同时兼容"非含尾日"写法（end == start + stated_months 个月，即终止日不计入），
    这种情况由 calc_month_diff 的精确匹配处理，本函数只负责识别含尾日这一惯例。
    """
    if stated_months is None or stated_months <= 0:
        return False
    inclusive_end = add_months(start, stated_months) - timedelta(days=1)
    return end == inclusive_end


# ---------------------------------------------------------------------------
# 验证逻辑
# ---------------------------------------------------------------------------

def verify_contract_term(contract_term: Dict, review_date_str: str) -> List[Dict]:
    """验证合同整体期限。"""
    results = []
    review_dt = parse_date(review_date_str)
    if not review_dt:
        return [{"check": "contract_term_review_date", "status": "error",
                 "message": "无法解析审查日期"}]

    start = parse_date(contract_term.get("start_date"))
    end = parse_date(contract_term.get("end_date"))
    stated = contract_term.get("stated_duration")
    clause = contract_term.get("clause", "未知")

    # 检查1：合同是否已过期
    if end is not None:
        if end < review_dt:
            results.append({
                "check": "contract_expired",
                "status": "fail",
                "risk_level": "P0",
                "clause": clause,
                "end_date": str(end),
                "review_date": str(review_dt),
                "message": f"合同截止日期 {end} 早于审查日期 {review_dt}，合同已过期"
            })
        else:
            remaining = (end - review_dt).days
            result = {
                "check": "contract_expired",
                "status": "pass",
                "clause": clause,
                "end_date": str(end),
                "review_date": str(review_dt),
                "remaining_days": remaining,
                "message": f"合同截止日期 {end}，距今 {remaining} 天"
            }
            if remaining < 30:
                result["status"] = "warn"
                result["risk_level"] = "P2"
                result["message"] = f"合同将于 {remaining} 天后到期（{end}），请注意续约"
            results.append(result)

    # 检查2：合同倒签风险
    if start is not None:
        if start < review_dt:
            days_back = (review_dt - start).days
            result = {
                "check": "contract_backdate",
                "clause": clause,
                "start_date": str(start),
                "review_date": str(review_dt),
                "days_backdated": days_back,
            }
            if days_back > 180:
                result["status"] = "fail"
                result["risk_level"] = "P1"
                result["message"] = f"合同起始日期 {start} 早于审查日期 {review_dt} 达 {days_back} 天，存在严重倒签风险"
            elif days_back > 0:
                result["status"] = "warn"
                result["risk_level"] = "P2"
                result["message"] = f"合同起始日期 {start} 早于审查日期 {review_dt}（{days_back} 天），存在倒签风险"
            else:
                result["status"] = "pass"
                result["message"] = "合同起始日期不早于审查日期"
            results.append(result)

    # 检查3：约定时长 vs 起止日期精确校验（核心）
    if start is not None and end is not None and stated:
        stated_months = parse_duration_months(stated)
        if stated_months is not None:
            actual_months, extra_days = calc_month_diff(start, end)

            result = {
                "check": "term_duration_consistency",
                "clause": clause,
                "start_date": str(start),
                "end_date": str(end),
                "stated_duration": stated,
                "stated_months": stated_months,
                "actual_months": actual_months,
                "actual_extra_days": extra_days,
            }

            # 精确比较
            if actual_months == stated_months and extra_days == 0:
                result["status"] = "pass"
                result["message"] = (
                    f"约定时长 \"{stated}\"（{stated_months}个月）"
                    f"与起止日期 {start}→{end} 一致（{actual_months}个月）"
                )
            elif is_inclusive_term_match(start, end, stated_months):
                # 含尾日整期：终止日当天计入期限，是合同惯例写法，视为一致
                result["status"] = "pass"
                result["inclusive_end"] = True
                result["message"] = (
                    f"约定时长 \"{stated}\"（{stated_months}个月）"
                    f"与起止日期 {start}→{end} 一致"
                    f"（含尾日计算：终止日 {end} 计入期限，构成完整 {stated_months} 个月）"
                )
            else:
                actual_desc = f"{actual_months}个月"
                if extra_days > 0:
                    actual_desc += f"零{extra_days}天"
                result["status"] = "fail"
                result["risk_level"] = "P0"
                result["message"] = (
                    f"约定时长 \"{stated}\"（{stated_months}个月）"
                    f"与起止日期 {start}→{end} 实际间隔（{actual_desc}）不一致"
                )
            results.append(result)
        else:
            results.append({
                "check": "term_duration_consistency",
                "status": "info",
                "clause": clause,
                "stated_duration": stated,
                "message": f"无法解析约定时长 \"{stated}\"，跳过精确校验"
            })
    elif stated and (start is None or end is None):
        results.append({
            "check": "term_duration_consistency",
            "status": "info",
            "clause": clause,
            "message": "约定了时长但起止日期不完整，无法精确校验"
        })

    return results


def verify_date_pairs(date_pairs: List[Dict], contract_term: Dict) -> List[Dict]:
    """验证各日期/期限对的一致性。"""
    results = []

    contract_start = parse_date(contract_term.get("start_date"))
    contract_end = parse_date(contract_term.get("end_date"))

    for pair in date_pairs:
        label = pair.get("label", "未知")
        clause = pair.get("clause", "未知")
        start = parse_date(pair.get("start_date"))
        end = parse_date(pair.get("end_date"))
        stated = pair.get("stated_duration")
        relation = pair.get("relation_to_contract", "independent")

        # 校验1：起止日期 vs 约定时长
        if start is not None and end is not None and stated:
            stated_months = parse_duration_months(stated)
            if stated_months is not None:
                actual_months, extra_days = calc_month_diff(start, end)
                result = {
                    "check": "date_pair_duration",
                    "label": label,
                    "clause": clause,
                    "start_date": str(start),
                    "end_date": str(end),
                    "stated_duration": stated,
                    "stated_months": stated_months,
                    "actual_months": actual_months,
                    "actual_extra_days": extra_days,
                }
                if actual_months == stated_months and extra_days == 0:
                    result["status"] = "pass"
                    result["message"] = f"{label}：约定 \"{stated}\" 与实际间隔一致"
                elif is_inclusive_term_match(start, end, stated_months):
                    # 含尾日整期：终止日当天计入期限，是合同惯例写法，视为一致
                    result["status"] = "pass"
                    result["inclusive_end"] = True
                    result["message"] = (
                        f"{label}：约定 \"{stated}\" 与实际间隔一致"
                        f"（含尾日计算：终止日 {end} 计入期限，构成完整 {stated_months} 个月）"
                    )
                else:
                    actual_desc = f"{actual_months}个月"
                    if extra_days > 0:
                        actual_desc += f"零{extra_days}天"
                    result["status"] = "fail"
                    result["risk_level"] = "P0"
                    result["message"] = (
                        f"{label}：约定 \"{stated}\"（{stated_months}个月）"
                        f"与起止日期 {start}→{end}（{actual_desc}）不一致"
                    )
                results.append(result)

        # 校验2：起止日期逻辑（start < end）
        if start is not None and end is not None:
            if start >= end:
                results.append({
                    "check": "date_pair_order",
                    "label": label,
                    "clause": clause,
                    "status": "fail",
                    "risk_level": "P0",
                    "start_date": str(start),
                    "end_date": str(end),
                    "message": f"{label}：起始日期 {start} ≥ 终止日期 {end}，日期顺序错误"
                })

        # 校验3：与合同期限的关系
        if relation == "within" and contract_start and contract_end:
            if start and start < contract_start:
                results.append({
                    "check": "date_pair_contract_relation",
                    "label": label,
                    "clause": clause,
                    "status": "fail",
                    "risk_level": "P1",
                    "message": f"{label}起始日期 {start} 早于合同起始日期 {contract_start}"
                })
            if end and end > contract_end:
                results.append({
                    "check": "date_pair_contract_relation",
                    "label": label,
                    "clause": clause,
                    "status": "warn",
                    "risk_level": "P2",
                    "message": f"{label}终止日期 {end} 晚于合同终止日期 {contract_end}，确认是否有意延续"
                })

    return results


def verify_key_dates(key_dates: List[Dict], contract_term: Dict, review_date_str: str) -> List[Dict]:
    """验证关键日期节点。"""
    results = []
    review_dt = parse_date(review_date_str)
    contract_start = parse_date(contract_term.get("start_date"))

    for kd in key_dates:
        label = kd.get("label", "未知")
        clause = kd.get("clause", "未知")
        dt = parse_date(kd.get("date"))
        dependency = kd.get("dependency")

        if dt is None:
            continue

        # 校验：关键日期是否已过期
        if review_dt and dt < review_dt:
            results.append({
                "check": "key_date_expired",
                "label": label,
                "clause": clause,
                "status": "warn",
                "risk_level": "P2",
                "date": str(dt),
                "review_date": str(review_dt),
                "message": f"{label}（{dt}）已早于审查日期（{review_dt}），请确认是否仍需执行"
            })

        # 校验：依赖关系（如"合同生效后30日内"）
        if dependency and contract_start:
            days_match = re.search(r'(\d+)\s*(?:日|天|个工作日)', dependency)
            if days_match and '生效' in dependency:
                required_days = int(days_match.group(1))
                actual_days = (dt - contract_start).days
                if actual_days > required_days:
                    results.append({
                        "check": "key_date_dependency",
                        "label": label,
                        "clause": clause,
                        "status": "fail",
                        "risk_level": "P1",
                        "date": str(dt),
                        "contract_start": str(contract_start),
                        "dependency": dependency,
                        "actual_days": actual_days,
                        "required_days": required_days,
                        "message": (
                            f"{label}（{dt}）距合同起始日 {contract_start} 为 {actual_days} 天，"
                            f"超出约定的 \"{dependency}\"（{required_days} 天）"
                        )
                    })

    return results


def verify_renewal(renewal: Optional[Dict]) -> List[Dict]:
    """验证续约条款。"""
    if not renewal:
        return []

    results = []
    auto_renew = renewal.get("auto_renew", False)
    notice_days = renewal.get("notice_days")
    clause = renewal.get("clause", "未知")

    if auto_renew:
        result = {
            "check": "auto_renewal",
            "clause": clause,
            "auto_renew": True,
            "notice_days": notice_days,
        }
        if notice_days is None or notice_days <= 0:
            result["status"] = "fail"
            result["risk_level"] = "P1"
            result["message"] = "自动续约条款未约定提前通知期限，可能导致无法及时终止"
        elif notice_days < 15:
            result["status"] = "warn"
            result["risk_level"] = "P2"
            result["message"] = f"自动续约提前通知期仅 {notice_days} 天，可能不足以完成内部审批"
        else:
            result["status"] = "pass"
            result["message"] = f"自动续约提前通知期 {notice_days} 天"

        results.append(result)

    return results


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def run_all_checks(data: Dict) -> Dict:
    """执行所有日期验证检查。"""
    review_date = data.get("review_date", str(date.today()))
    contract_term = data.get("contract_term", {})
    date_pairs = data.get("date_pairs", [])
    key_dates = data.get("key_dates", [])
    renewal = data.get("renewal")

    all_checks = []

    # 合同整体期限
    all_checks.extend(verify_contract_term(contract_term, review_date))

    # 各日期/期限对
    all_checks.extend(verify_date_pairs(date_pairs, contract_term))

    # 关键日期节点
    all_checks.extend(verify_key_dates(key_dates, contract_term, review_date))

    # 续约条款
    all_checks.extend(verify_renewal(renewal))

    # 汇总
    fail_count = sum(1 for c in all_checks if c.get("status") == "fail")
    warn_count = sum(1 for c in all_checks if c.get("status") == "warn")
    pass_count = sum(1 for c in all_checks if c.get("status") == "pass")
    info_count = sum(1 for c in all_checks if c.get("status") == "info")

    results = {
        "summary": {
            "review_date": review_date,
            "total_checks": len(all_checks),
            "fail": fail_count,
            "warn": warn_count,
            "pass": pass_count,
            "info": info_count,
        },
        "checks": all_checks,
    }

    if fail_count > 0:
        results["summary"]["overall"] = "FAIL"
        results["summary"]["message"] = f"{fail_count} 项日期验证未通过"
    elif warn_count > 0:
        results["summary"]["overall"] = "WARN"
        results["summary"]["message"] = f"{warn_count} 项日期验证有警告"
    else:
        results["summary"]["overall"] = "PASS"
        results["summary"]["message"] = "所有日期验证通过"

    return results


def main():
    parser = argparse.ArgumentParser(description="合同日期/期限一致性验证脚本")
    parser.add_argument("--json", "-j", required=True, help="输入 JSON 文件路径")
    parser.add_argument("--output", "-o", help="输出结果 JSON 文件路径")
    args = parser.parse_args()

    with open(args.json, "r", encoding="utf-8") as f:
        data = json.load(f)

    results = run_all_checks(data)
    output_json = json.dumps(results, ensure_ascii=False, indent=2)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_json)
        print(f"[OK] 验证结果已写入 {args.output}")
    else:
        print(output_json)

    sys.exit(1 if results["summary"]["overall"] == "FAIL" else 0)


if __name__ == "__main__":
    main()
