#!/usr/bin/env python3
"""
技能ID: overtime-compliance
技能名称: 加班合规检查
模块: 劳动合规
功能: 检查加班安排是否符合《劳动法》第41-43条及《劳动合同法》相关规定
"""

import json
from typing import Dict, List, Any

# 法律规则库
RULES = {
    "max_monthly_overtime": 36,
    "max_daily_overtime": 3,
    "max_daily_hours": 11,  # 8+3
    "pay_rates": {"weekday": 1.5, "rest_day": 2.0, "holiday": 3.0},
    "protected_categories": ["pregnant", "minor", "breastfeeding", "disabled"],
}

VIOLATION_MESSAGES = {
    "exceed_monthly": "月加班时长超过36小时上限（《劳动法》第41条）",
    "exceed_daily": "日加班时长超过3小时上限（《劳动法》第41条）",
    "exceed_total_hours": "日总工作时间超过11小时（8h标准+3h加班上限）",
    "protected_category_overtime": "不允许安排{category}员工加班（《劳动法》第61/63条）",
    "no_overtime_pay": "未按规定支付加班费（标准工作日150%、休息日200%、法定节假日300%）",
    "forced_overtime": "强制加班违法，加班需员工同意（《劳动法》第41条）",
    "no_rest_day_in_week": "连续工作超过6天未安排休息日（《劳动法》第38条）",
}


def skill_function(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """检查加班合规性"""
    try:
        records = input_data.get("records", [])
        employee_info = input_data.get("employee", {})

        if not records:
            return {"status": "error", "message": "请提供加班记录"}

        violations = []
        warnings = []
        total_overtime = 0
        monthly_stats = {}

        for rec in records:
            date = rec.get("date", "")
            hours = float(rec.get("overtime_hours", 0))
            day_type = rec.get("day_type", "weekday")  # weekday/rest_day/holiday
            forced = rec.get("forced", False)
            month = date[:7] if date else "unknown"

            total_overtime += hours
            monthly_stats[month] = monthly_stats.get(month, 0) + hours

            # 检查日加班上限
            if hours > RULES["max_daily_overtime"]:
                violations.append({
                    "日期": date,
                    "类型": "超时加班",
                    "详情": f"当日加班{hours}小时，超过3小时上限",
                    "法律依据": "《劳动法》第41条",
                })

            # 检查总工时
            daily_total = 8 + hours
            if daily_total > RULES["max_daily_hours"]:
                violations.append({
                    "日期": date,
                    "类型": "总工时超标",
                    "详情": f"当日总工时{daily_total}小时，超过11小时上限",
                    "法律依据": "《劳动法》第41条",
                })

            # 强制加班
            if forced:
                violations.append({
                    "日期": date,
                    "类型": "强制加班",
                    "详情": "加班需与工会和劳动者协商，不得强制",
                    "法律依据": "《劳动法》第41条",
                })

        # 检查月加班上限
        for month, hours in monthly_stats.items():
            if hours > RULES["max_monthly_overtime"]:
                violations.append({
                    "月份": month,
                    "类型": "月加班超标",
                    "详情": f"当月加班{hours}小时，超过36小时上限",
                    "法律依据": "《劳动法》第41条",
                })

        # 检查特殊保护群体
        category = employee_info.get("category", "")
        if category in RULES["protected_categories"]:
            category_names = {
                "pregnant": "孕期女职工",
                "minor": "未成年工",
                "breastfeeding": "哺乳期女职工",
                "disabled": "残疾人",
            }
            violations.append({
                "类型": "特殊保护违规",
                "详情": f"不允许安排{category_names.get(category, category)}加班",
                "法律依据": "《劳动法》第61/63条",
            })

        # 合规评级
        risk_level = "低风险" if len(violations) == 0 else ("中风险" if len(violations) <= 2 else "高风险")

        return {
            "status": "success",
            "result": {
                "合规状态": risk_level,
                "违规事项": violations,
                "警告事项": warnings,
                "统计": {
                    "总加班时长": total_overtime,
                    "月度明细": monthly_stats,
                    "检查记录数": len(records),
                },
                "合规建议": [
                    "建立加班审批制度，避免口头安排",
                    "保留加班记录至少2年备查",
                    "按法定标准支付加班费",
                    "确保每周至少休息1天",
                ],
            },
            "法律依据": "《劳动法》第38/41-43条、《劳动合同法》第31条",
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    test_input = {
        "records": [
            {"date": "2025-03-01", "overtime_hours": 2, "day_type": "weekday", "forced": False},
            {"date": "2025-03-05", "overtime_hours": 4, "day_type": "weekday", "forced": True},
            {"date": "2025-03-10", "overtime_hours": 3, "day_type": "rest_day", "forced": False},
        ],
        "employee": {"category": "normal"},
    }
    result = skill_function(test_input)
    print(json.dumps(result, ensure_ascii=False, indent=2))
