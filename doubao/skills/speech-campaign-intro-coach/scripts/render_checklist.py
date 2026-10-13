#!/usr/bin/env python3
import json, sys

OUTPUTS = ["自我介绍稿", "竞选演讲稿", "面试回答", "答辩 Q&A", "表达优化建议"]
COMPLIANCE = ["不虚构经历、奖项、身份或承诺。", "不生成攻击竞争者或操纵投票内容。", "涉及奖学金答辩时仅辅助表达，不替代事实材料。"]

print("# Final Checklist")
for item in OUTPUTS:
    print(f"- [ ] deliverable: {item}")
print("- [ ] missing facts are marked")
print("- [ ] no fabricated facts")
for item in COMPLIANCE:
    print(f"- [ ] compliance: {item}")
