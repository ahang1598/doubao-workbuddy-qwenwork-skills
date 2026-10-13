#!/usr/bin/env python3
"""
技能ID: social-insurance-calc
技能名称: 社保公积金计算器
模块: 劳动合规
功能: 根据工资和城市自动计算社保公积金缴纳金额（雇主+员工）
"""

import json
from typing import Dict, List, Any, Optional

# 2024-2025年社保费率（以北京为例，其他城市可扩展）
DEFAULT_RATES = {
    "pension": {"employer": 0.16, "employee": 0.08},
    "medical": {"employer": 0.095, "employee": 0.02},
    "unemployment": {"employer": 0.005, "employee": 0.005},
    "work_injury": {"employer": 0.004, "employee": 0.0},
    "maternity": {"employer": 0.008, "employee": 0.0},
}

CITY_RATES = {
    "北京": DEFAULT_RATES,
    "上海": {
        "pension": {"employer": 0.16, "employee": 0.08},
        "medical": {"employer": 0.095, "employee": 0.02},
        "unemployment": {"employer": 0.005, "employee": 0.005},
        "work_injury": {"employer": 0.002, "employee": 0.0},
        "maternity": {"employer": 0.0, "employee": 0.0},
    },
    "深圳": {
        "pension": {"employer": 0.14, "employee": 0.08},
        "medical": {"employer": 0.062, "employee": 0.02},
        "unemployment": {"employer": 0.007, "employee": 0.003},
        "work_injury": {"employer": 0.002, "employee": 0.0},
        "maternity": {"employer": 0.005, "employee": 0.0},
    },
    "广州": {
        "pension": {"employer": 0.14, "employee": 0.08},
        "medical": {"employer": 0.055, "employee": 0.02},
        "unemployment": {"employer": 0.0048, "employee": 0.002},
        "work_injury": {"employer": 0.002, "employee": 0.0},
        "maternity": {"employer": 0.0085, "employee": 0.0},
    },
}

# 缴费基数上下限（2024年北京标准示例）
BASE_LIMITS = {
    "北京": {"min": 6326, "max": 35283},
    "上海": {"min": 7310, "max": 36549},
    "深圳": {"min": 2360, "max": 26421},
    "广州": {"min": 5284, "max": 26421},
}


def skill_function(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """计算社保公积金缴纳金额"""
    try:
        salary = float(input_data.get("salary", 0))
        city = input_data.get("city", "北京")
        housing_fund_rate = float(input_data.get("housing_fund_rate", 0.12))  # 默认12%

        if salary <= 0:
            return {"status": "error", "message": "工资必须大于0"}

        rates = CITY_RATES.get(city, DEFAULT_RATES)
        limits = BASE_LIMITS.get(city, {"min": 6326, "max": 35283})

        # 应用基数上下限
        base = max(limits["min"], min(salary, limits["max"]))

        breakdown = {}
        employer_total = 0
        employee_total = 0

        for item, rate_pair in rates.items():
            emp_part = round(base * rate_pair["employer"], 2)
            ee_part = round(base * rate_pair["employee"], 2)
            breakdown[item] = {
                "缴费基数": base,
                "雇主比例": f"{rate_pair['employer'] * 100:.1f}%",
                "雇主金额": emp_part,
                "员工比例": f"{rate_pair['employee'] * 100:.1f}%",
                "员工金额": ee_part,
            }
            employer_total += emp_part
            employee_total += ee_part

        # 住房公积金
        hf_emp = round(base * housing_fund_rate, 2)
        hf_ee = round(base * housing_fund_rate, 2)
        breakdown["住房公积金"] = {
            "缴费基数": base,
            "雇主比例": f"{housing_fund_rate * 100:.1f}%",
            "雇主金额": hf_emp,
            "员工比例": f"{housing_fund_rate * 100:.1f}%",
            "员工金额": hf_ee,
        }
        employer_total += hf_emp
        employee_total += hf_ee

        return {
            "status": "success",
            "result": {
                "城市": city,
                "税前月薪": salary,
                "缴费基数": base,
                "基数范围": limits,
                "明细": breakdown,
                "雇主合计": round(employer_total, 2),
                "员工合计": round(employee_total, 2),
                "企业总成本": round(salary + employer_total, 2),
                "员工实发（扣五险一金前）": round(salary - employee_total, 2),
            },
            "法律依据": "《社会保险法》《住房公积金管理条例》",
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    test_input = {"salary": 15000, "city": "北京", "housing_fund_rate": 0.12}
    result = skill_function(test_input)
    print(json.dumps(result, ensure_ascii=False, indent=2))
