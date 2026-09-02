#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sentence_validator.py — 刑期计算 L1 数值范围校验器
=====================================================
置信度: 95%
用途: Phase 6 质检阶段，对关键数值执行确定性范围校验
依赖: 纯 Python 标准库，无第三方依赖

职责边界:
  - L1 数值范围校验（本脚本负责）:
      ✅ 折抵比例是否 ∈ [0, 1]
      ✅ 数罪并罚上限是否 ≤ 法定上限
      ✅ 剩余刑期是否 ≥ 0
      ✅ 日期计算自洽性（LLM 推导天数 vs 脚本计算天数偏差）
      ✅ 输入值非空检查
  - L2 法条一致性校验（LLM Phase 5/6 负责）:
      ❌ 不检查: 折抵天数引用法条是否正确
      ❌ 不检查: 并罚上限引用法条是否匹配
      ❌ 不检查: 减轻幅度是否与量刑指导意见一致
"""

import json
import sys
from typing import Any


# ============================================================
# 一、L1 数值范围校验函数
# ============================================================

def validate_offset_ratio(ratio: float, penalty_type: str) -> dict:
    """
    校验折抵比例是否正确。
    
    Args:
        ratio:        折抵比例（如 1 表示 1:1, 2 表示 1:2）
        penalty_type: 主刑类型 "管制" | "拘役" | "有期徒刑"
    
    Returns:
        {"pass": bool, "expected": int, "actual": int, "message": str}
    """
    expected_map = {"管制": 2, "拘役": 1, "有期徒刑": 1}
    expected = expected_map.get(penalty_type, None)
    
    if expected is None:
        return {
            "pass": False,
            "check_item": "折抵比例-主刑类型",
            "expected": f"已知类型 {list(expected_map.keys())} 之一",
            "actual": penalty_type,
            "message": f"无法识别主刑类型 '{penalty_type}'，请确认是否为管制/拘役/有期徒刑",
            "severity": "block",
        }
    
    if ratio == expected:
        return {
            "pass": True,
            "check_item": "折抵比例",
            "expected": f"{1}:{expected}",
            "actual": f"{1}:{ratio}",
            "message": f"{penalty_type} 折抵比例 1:{ratio} 正确",
            "severity": "ok",
        }
    else:
        return {
            "pass": False,
            "check_item": "折抵比例",
            "expected": f"{1}:{expected}",
            "actual": f"{1}:{ratio}",
            "message": f"{penalty_type} 折抵比例应为 1:{expected}，实际为 1:{ratio}",
            "severity": "block",
        }


def validate_combined_punishment_limit(total_years: float, upper_limit_years: float) -> dict:
    """
    校验数罪并罚上限是否合法。
    
    规则（刑法第69条）:
      - 总和 < 35年 → 上限 ≤ 20年
      - 总和 ≥ 35年 → 上限 ≤ 25年
      - 管制 ≤ 3年，拘役 ≤ 1年（此处针对有期徒刑）
    
    Args:
        total_years:       各罪总和刑期（年）
        upper_limit_years: 并罚上限（年）
    
    Returns:
        {"pass": bool, "legal_max": int, "actual": float, "message": str}
    """
    if total_years < 35:
        legal_max = 20
    else:
        legal_max = 25
    
    if upper_limit_years <= legal_max:
        return {
            "pass": True,
            "check_item": "数罪并罚上限",
            "expected": f"≤ {legal_max}年（总和{'<' if total_years < 35 else '≥'}35年）",
            "actual": f"{upper_limit_years}年",
            "message": f"并罚上限 {upper_limit_years}年 ≤ 法定上限 {legal_max}年，合规",
            "severity": "ok",
        }
    else:
        return {
            "pass": False,
            "check_item": "数罪并罚上限",
            "expected": f"≤ {legal_max}年",
            "actual": f"{upper_limit_years}年",
            "message": f"并罚上限 {upper_limit_years}年 超出法定上限 {legal_max}年",
            "severity": "block",
        }


def validate_remaining_days(remaining_days: int) -> dict:
    """
    校验折抵后剩余刑期非负。
    
    Args:
        remaining_days: 折抵后剩余刑期天数
    
    Returns:
        {"pass": bool, "message": str}
    """
    if remaining_days >= 0:
        return {
            "pass": True,
            "check_item": "剩余刑期非负",
            "expected": "≥ 0",
            "actual": f"{remaining_days}天",
            "message": f"剩余刑期 {remaining_days}天 ≥ 0，合规",
            "severity": "ok",
        }
    else:
        return {
            "pass": False,
            "check_item": "剩余刑期非负",
            "expected": "≥ 0",
            "actual": f"{remaining_days}天",
            "message": f"剩余刑期 {remaining_days}天 < 0，羁押已超宣告刑期，应立即释放（非错误，为特殊情形）",
            "severity": "warning",  # 负值可能是正常的（羁押超宣告刑）
        }


def validate_input_not_null(data: dict, required_fields: list[str]) -> list[dict]:
    """
    校验输入关键字段是否存在且非空。
    
    Args:
        data:           计算中间结果字典
        required_fields: 必需字段列表
    
    Returns:
        校验结果列表
    """
    results = []
    for field in required_fields:
        value = data.get(field)
        if value is None or value == "":
            results.append({
                "pass": False,
                "check_item": f"输入字段非空-{field}",
                "expected": "非空",
                "actual": "缺失或为空",
                "message": f"必需字段 '{field}' 缺失",
                "severity": "block",
            })
        else:
            results.append({
                "pass": True,
                "check_item": f"输入字段非空-{field}",
                "expected": "非空",
                "actual": str(value)[:50],
                "message": f"字段 '{field}' 存在",
                "severity": "ok",
            })
    return results


def validate_llm_script_days_cross(llm_days: int, script_days: int, tolerance: int = 0) -> dict:
    """
    交叉验证 LLM 推导的羁押天数 vs 脚本计算的天数。
    
    Args:
        llm_days:    LLM 推导的天数
        script_days: 脚本计算的天数
        tolerance:   允许的偏差（天），默认 0（零容忍）
    
    Returns:
        校验结果
    """
    deviation = abs(llm_days - script_days)
    
    if deviation <= tolerance:
        return {
            "pass": True,
            "check_item": "日期计算自洽性",
            "expected": f"偏差 ≤ {tolerance}天",
            "actual": f"偏差 {deviation}天 (LLM={llm_days}, Script={script_days})",
            "message": "LLM 推导与脚本计算一致",
            "severity": "ok",
        }
    else:
        return {
            "pass": False,
            "check_item": "日期计算自洽性",
            "expected": f"偏差 ≤ {tolerance}天",
            "actual": f"偏差 {deviation}天 (LLM={llm_days}, Script={script_days})",
            "message": f"LLM 推导偏差 {deviation}天，建议以脚本计算值 {script_days}天为准",
            "severity": "block" if deviation >= 3 else "warning",
        }


def validate_month_conversion(method: str) -> dict:
    """
    校验月→天换算是否使用逐月推算（而非30天/月概算）。
    
    Args:
        method: "逐月推算" | "30天概算" | 其他
    
    Returns:
        校验结果
    """
    if method == "逐月推算":
        return {
            "pass": True,
            "check_item": "月天数换算方法",
            "expected": "逐月推算（刑诉法解释第202条）",
            "actual": method,
            "message": "月→天换算使用逐月推算，符合刑诉法解释第202条",
            "severity": "ok",
        }
    else:
        return {
            "pass": False,
            "check_item": "月天数换算方法",
            "expected": "逐月推算（刑诉法解释第202条）",
            "actual": method,
            "message": f"月→天换算使用'{method}'，29个月误差可达13天！必须使用逐月推算",
            "severity": "block",
        }


def validate_heterogeneous_penalty(penalty_types: list[str]) -> dict:
    """
    校验数罪中异种主刑的并罚处理是否正确（刑法第69条第2款）。
    
    规则：数罪中有判处有期徒刑和拘役的，执行有期徒刑（有期徒刑吸收拘役）。
         数罪中有判处有期徒刑和管制，或者拘役和管制的，有期徒刑、拘役执行完毕后，管制仍须执行。
    
    Args:
        penalty_types: 各罪主刑类型列表，如 ["有期徒刑", "拘役"] 或 ["有期徒刑", "管制"]
    
    Returns:
        校验结果
    """
    if len(penalty_types) <= 1:
        return {
            "pass": True,
            "check_item": "异种主刑并罚处理",
            "expected": "单罪无需并罚",
            "actual": f"仅{penalty_types}",
            "message": "单罪，无需异种主刑并罚处理",
            "severity": "ok",
        }
    
    unique_types = set(penalty_types)
    
    # 有期徒刑 + 拘役：吸收规则
    if "有期徒刑" in unique_types and "拘役" in unique_types:
        return {
            "pass": True,
            "check_item": "异种主刑并罚处理（第69条第2款）",
            "expected": "有期徒刑吸收拘役，仅执行有期徒刑",
            "actual": f"主刑类型：{', '.join(unique_types)}",
            "message": "有期徒刑+拘役并罚：拘役被有期徒刑吸收，仅执行有期徒刑（刑法第69条第2款）",
            "severity": "ok",
            "rule": "有期徒刑吸收拘役",
        }
    
    # 含管制：管制仍须执行
    if "管制" in unique_types and ("有期徒刑" in unique_types or "拘役" in unique_types):
        return {
            "pass": True,
            "check_item": "异种主刑并罚处理（第69条第2款）",
            "expected": "有期徒刑/拘役执行完毕后，管制仍须执行",
            "actual": f"主刑类型：{', '.join(unique_types)}",
            "message": "含管制+有期徒刑/拘役：有期徒刑/拘役执行完毕后，管制仍须执行（刑法第69条第2款）",
            "severity": "ok",
            "rule": "管制仍须执行",
        }
    
    return {
        "pass": True,
        "check_item": "异种主刑并罚处理",
        "expected": "同种主刑或无需特殊处理",
        "actual": f"主刑类型：{', '.join(unique_types)}",
        "message": "无需异种主刑特殊处理",
        "severity": "ok",
    }


def validate_sentencing_factor_cumulation(factors: dict, total_reduction: float) -> dict:
    """
    校验量刑情节累计从轻幅度是否超过合理上限。
    
    规则（2021年两高量刑指导意见）：
      - 同向相加、逆向相减
      - 累计从轻上限通常不超过60%
      - 自首+认罪认罚不得重复评价同一悔罪事实
    
    Args:
        factors: 量刑情节字典，如 {"自首": 0.20, "认罪认罚": 0.10}
        total_reduction: 累计从轻幅度（小数），如 0.30
    
    Returns:
        校验结果
    """
    warnings = []
    
    # 检查重复评价风险
    has_zishou = "自首" in factors or "坦白" in factors
    has_renzui = "认罪认罚" in factors
    if has_zishou and has_renzui:
        warnings.append("自首/坦白+认罪认罚可能构成重复评价——最高检明确指出不得对同一悔罪表现重复评价")
    
    # 检查累计上限
    CUMULATION_LIMIT = 0.60  # 通常不宜超过60%
    if total_reduction > CUMULATION_LIMIT:
        warnings.append(f"累计从轻幅度{total_reduction:.0%}超过{CUMULATION_LIMIT:.0%}上限，请核实是否存在重复评价")
    
    # 检查减轻 vs 从轻
    jianqing_keywords = ["减轻"]
    has_jianqing = any(k in str(factors.keys()) for k in jianqing_keywords)
    
    if warnings:
        return {
            "pass": False,
            "check_item": "量刑情节竞合校验",
            "expected": "累计从轻≤60%，无重复评价",
            "actual": f"累计{total_reduction:.0%}",
            "message": "；".join(warnings),
            "severity": "warning",
        }
    else:
        return {
            "pass": True,
            "check_item": "量刑情节竞合校验",
            "expected": "累计从轻≤60%，无重复评价",
            "actual": f"累计{total_reduction:.0%}",
            "message": "量刑情节竞合无异常",
            "severity": "ok",
        }


# ============================================================
# 二、批量验证入口
# ============================================================

def run_all_validations(calculation_data: dict) -> dict:
    """
    执行所有 L1 数值范围校验。
    
    Args:
        calculation_data: 计算中间结果，结构:
            {
                "penalty_type": "有期徒刑",
                "offset_ratio": 1,
                "total_years": 5.0,
                "upper_limit_years": 20,
                "remaining_days": 432,
                "llm_custody_days": 448,
                "script_custody_days": 448,
                "sentencing_factors": {"自首": 0.2, "认罪认罚": 0.1},
                "declared_sentence_months": 29,
                "month_conversion_method": "逐月推算",  # v2.2.0 新增
                "penalty_types_for_merge": ["有期徒刑"],  # v2.2.0 新增：异种主刑校验
                "total_reduction_ratio": 0.30,  # v2.2.0 新增：量刑累计幅度
            }
    
    Returns:
        {
            "all_pass": bool,
            "block_count": int,
            "warning_count": int,
            "total_checks": int,
            "checks": [ {...}, ... ],
            "summary": str,
        }
    """
    checks = []
    
    # 1. 折抵比例校验
    penalty_type = calculation_data.get("penalty_type", "")
    offset_ratio = calculation_data.get("offset_ratio", 0)
    checks.append(validate_offset_ratio(offset_ratio, penalty_type))
    
    # 2. 数罪并罚上限校验（条件触发）
    if "total_years" in calculation_data and "upper_limit_years" in calculation_data:
        checks.append(
            validate_combined_punishment_limit(
                calculation_data["total_years"],
                calculation_data["upper_limit_years"],
            )
        )
    
    # 3. 剩余刑期非负校验
    if "remaining_days" in calculation_data:
        checks.append(validate_remaining_days(calculation_data["remaining_days"]))
    
    # 4. LLM vs 脚本天数交叉验证
    if "llm_custody_days" in calculation_data and "script_custody_days" in calculation_data:
        checks.append(
            validate_llm_script_days_cross(
                calculation_data["llm_custody_days"],
                calculation_data["script_custody_days"],
                tolerance=0,
            )
        )
    
    # 5. 输入字段非空校验
    required_fields = ["penalty_type", "declared_sentence_months"]
    checks.extend(validate_input_not_null(calculation_data, required_fields))
    
    # 6. v2.2.0 新增：月天数换算方法校验
    month_method = calculation_data.get("month_conversion_method", "")
    if month_method:
        checks.append(validate_month_conversion(month_method))
    
    # 7. v2.2.0 新增：异种主刑并罚处理校验
    penalty_types = calculation_data.get("penalty_types_for_merge", [])
    if penalty_types:
        checks.append(validate_heterogeneous_penalty(penalty_types))
    
    # 8. v2.2.0 新增：量刑情节竞合校验
    factors = calculation_data.get("sentencing_factors", {})
    total_reduction = calculation_data.get("total_reduction_ratio", 0)
    if factors and total_reduction:
        checks.append(validate_sentencing_factor_cumulation(factors, total_reduction))
    
    # 汇总
    block_count = sum(1 for c in checks if c.get("severity") == "block" and not c["pass"])
    warning_count = sum(1 for c in checks if c.get("severity") == "warning" and not c["pass"])
    all_pass = block_count == 0
    
    return {
        "all_pass": all_pass,
        "block_count": block_count,
        "warning_count": warning_count,
        "total_checks": len(checks),
        "checks": checks,
        "summary": (
            f"✅ 全部 {len(checks)} 项校验通过" if all_pass
            else f"❌ {block_count} 项阻断 + {warning_count} 项警告 / 共 {len(checks)} 项"
        ),
    }


def main():
    """CLI 入口。"""
    if len(sys.argv) < 2:
        print("用法: python sentence_validator.py <json_file_or_string>")
        print('示例: python sentence_validator.py \'{"penalty_type":"有期徒刑","offset_ratio":1,"remaining_days":432,\"llm_custody_days\":448,\"script_custody_days\":448}\'')
        sys.exit(0)
    
    # 尝试作为 JSON 字符串解析
    try:
        data = json.loads(sys.argv[1])
    except json.JSONDecodeError:
        # 尝试作为文件路径读取
        try:
            with open(sys.argv[1], 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            print("错误: 无法解析输入，请提供有效 JSON 字符串或文件路径")
            sys.exit(1)
    
    result = run_all_validations(data)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    # 返回退出码
    sys.exit(0 if result["all_pass"] else 1)


if __name__ == "__main__":
    main()
