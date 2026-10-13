#!/usr/bin/env python3
"""技能ID: contract-amendment-gen | 合同修订建议生成"""
import json
from typing import Dict, Any
from datetime import date

def skill_function(input_data):
    contract_name = input_data.get("contract_name", "原合同")
    changes = input_data.get("changes", [])
    if not changes:
        return {"status": "error", "message": "请提供变更事项"}
    lines = [f"# {contract_name} 补充协议", f"\n**签订日期**: {date.today().isoformat()}\n"]
    lines.append(f"鉴于双方此前签订的《{contract_name}》，经协商一致，达成以下补充协议：\n")
    for i, c in enumerate(changes, 1):
        lines.append(f"### 第{i}款 {c.get('clause','相关条款')}")
        lines.append(f"- **原条款**: {c.get('old_text','')}")
        lines.append(f"- **修改为**: {c.get('new_text','')}")
        if c.get("reason"):
            lines.append(f"- **修改原因**: {c['reason']}")
        lines.append("")
    lines.append("## 其他条款\n原合同其他条款不变，继续有效。")
    lines.append("\n**甲方签章**: ___________ **乙方签章**: ___________")
    return {"status": "success", "result": {"补充协议": "\n".join(lines), "修改项数": len(changes)}}

if __name__ == "__main__":
    test = {"contract_name": "服务器采购合同", "changes": [{"clause": "交货日期", "old_text": "2025-04-01", "new_text": "2025-05-01", "reason": "供应商产能不足"}]}
    print(json.dumps(skill_function(test), ensure_ascii=False, indent=2))
