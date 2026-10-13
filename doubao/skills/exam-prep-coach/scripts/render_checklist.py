#!/usr/bin/env python3
import json, sys

OUTPUTS = ["备考日历", "每日任务", "错题复盘", "阶段检测", "动态调整建议"]
COMPLIANCE = ["禁止作弊、泄题、代考、规避监考。", "不承诺分数或通过结果。", "学习建议不替代学校或考试机构规定。"]

print("# Final Checklist")
for item in OUTPUTS:
    print(f"- [ ] deliverable: {item}")
print("- [ ] missing facts are marked")
print("- [ ] no fabricated facts")
for item in COMPLIANCE:
    print(f"- [ ] compliance: {item}")
