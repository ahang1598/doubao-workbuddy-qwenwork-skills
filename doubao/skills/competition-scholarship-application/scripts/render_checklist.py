#!/usr/bin/env python3
import json, sys

OUTPUTS = ["申报时间线", "材料清单", "个人/项目陈述", "答辩稿", "材料缺口表"]
COMPLIANCE = ["禁止虚构成绩、证书、奖项、论文、项目角色。", "不做官方资格结论，只做规则解读和材料辅助。", "个人敏感信息默认脱敏。"]

print("# Final Checklist")
for item in OUTPUTS:
    print(f"- [ ] deliverable: {item}")
print("- [ ] missing facts are marked")
print("- [ ] no fabricated facts")
for item in COMPLIANCE:
    print(f"- [ ] compliance: {item}")
