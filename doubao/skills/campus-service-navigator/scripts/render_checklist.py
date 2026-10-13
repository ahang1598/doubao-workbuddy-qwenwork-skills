#!/usr/bin/env python3
import json, sys

OUTPUTS = ["流程清单", "材料列表", "负责部门", "时间节点", "咨询话术"]
COMPLIANCE = ["不绕过学校流程、审批或门禁。", "不伪造证明、病假单或成绩材料。", "校内政策需标注待核验，以官方最新通知为准。"]

print("# Final Checklist")
for item in OUTPUTS:
    print(f"- [ ] deliverable: {item}")
print("- [ ] missing facts are marked")
print("- [ ] no fabricated facts")
for item in COMPLIANCE:
    print(f"- [ ] compliance: {item}")
