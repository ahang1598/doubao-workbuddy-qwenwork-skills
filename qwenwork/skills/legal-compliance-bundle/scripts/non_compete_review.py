#!/usr/bin/env python3
"""
技能ID: non-compete-review
技能名称: 竞业限制审查
模块: 劳动合规
功能: 审查竞业限制条款合理性及合规性
"""

import json
from typing import Dict, Any

def skill_function(input_data: Dict[str, Any]) -> Dict[str, Any]:
    try:
        clause_text = input_data.get("clause_text", "")
        monthly_salary = float(input_data.get("monthly_salary", 0))
        duration_months = int(input_data.get("duration_months", 0))
        scope = input_data.get("scope", "")
        compensation_pct = float(input_data.get("compensation_pct", 0))

        violations = []
        warnings = []

        # 检查期限（最长2年）
        if duration_months > 24:
            violations.append({"问题": f"竞业期限{duration_months}个月超过法定24个月上限", "法律依据": "《劳动合同法》第24条"})
        elif duration_months > 12:
            warnings.append(f"竞业期限{duration_months}个月较长，可能影响条款效力")

        # 检查补偿金（不低于离职前12个月平均工资的30%，且不低于当地最低工资）
        min_compensation = monthly_salary * 0.30
        if compensation_pct < 30:
            violations.append({"问题": f"补偿金比例{compensation_pct}%低于法定最低30%", "法律依据": "最高人民法院劳动争议司法解释(四)第6条"})

        if monthly_salary > 0 and compensation_pct > 0:
            actual_comp = monthly_salary * compensation_pct / 100
            if actual_comp < 2320:  # 2024年北京最低工资
                warnings.append(f"月补偿金{actual_comp}元可能低于当地最低工资标准")

        # 检查范围是否合理
        if "所有行业" in clause_text or "任何公司" in clause_text:
            warnings.append("竞业范围过于宽泛（'所有行业/任何公司'），可能被认定无效")

        # 给出综合评估
        if violations:
            rating = "不合规"
        elif warnings:
            rating = "有风险"
        else:
            rating = "合规"

        return {
            "status": "success",
            "result": {
                "合规评级": rating,
                "违规事项": violations,
                "风险提示": warnings,
                "条款分析": {
                    "期限": f"{duration_months}个月",
                    "补偿比例": f"{compensation_pct}%",
                    "月薪基数": monthly_salary,
                    "月补偿金额": round(monthly_salary * compensation_pct / 100, 2) if monthly_salary > 0 else "未提供",
                },
                "建议": [
                    "竞业期限建议控制在6-12个月",
                    "补偿金比例建议不低于30%",
                    "竞业范围应明确具体行业和地域",
                    "建议约定公司可单方放弃竞业限制（需额外支付3个月补偿）",
                ],
            },
            "法律依据": "《劳动合同法》第23-24条、最高法劳动争议司法解释(四)",
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    test = {"clause_text": "离职后2年内不得在同行业公司任职", "monthly_salary": 20000, "duration_months": 24, "compensation_pct": 30}
    print(json.dumps(skill_function(test), ensure_ascii=False, indent=2))
