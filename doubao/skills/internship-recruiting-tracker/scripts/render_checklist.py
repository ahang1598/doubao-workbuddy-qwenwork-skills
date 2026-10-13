#!/usr/bin/env python3
import json, sys

OUTPUTS = ["岗位周报", "投递计划", "简历修改建议", "面试题库", "跟进提醒清单"]
COMPLIANCE = ["不承诺录用、内推成功或薪资结果。", "岗位信息需来源可追溯，不绕过登录或反爬。", "简历不得虚构经历、学历、项目或数据。"]

print("# Final Checklist")
for item in OUTPUTS:
    print(f"- [ ] deliverable: {item}")
print("- [ ] missing facts are marked")
print("- [ ] no fabricated facts")
for item in COMPLIANCE:
    print(f"- [ ] compliance: {item}")
