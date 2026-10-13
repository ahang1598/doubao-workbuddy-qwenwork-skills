#!/usr/bin/env python3
import json, sys

OUTPUTS = ["通知/群公告", "活动策划案", "排班表/分工表", "会议纪要", "执行清单与催办话术"]
COMPLIANCE = ["不编造学校、学院或职务背书。", "名单、手机号、学号等个人信息默认脱敏。", "活动安全、经费、审批事项只做提醒，不替代校方规定。"]

print("# Final Checklist")
for item in OUTPUTS:
    print(f"- [ ] deliverable: {item}")
print("- [ ] missing facts are marked")
print("- [ ] no fabricated facts")
for item in COMPLIANCE:
    print(f"- [ ] compliance: {item}")
