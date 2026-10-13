#!/usr/bin/env python3
import json, sys

OUTPUTS = ["PPT 结构", "逐页标题与正文", "演讲稿", "答辩问题", "素材缺口清单"]
COMPLIANCE = ["引用论文和数据必须保留来源提示。", "不得伪造实验结果、问卷样本或老师评价。", "不得代替学生完成需独立提交的学术诚信承诺内容。"]

print("# Final Checklist")
for item in OUTPUTS:
    print(f"- [ ] deliverable: {item}")
print("- [ ] missing facts are marked")
print("- [ ] no fabricated facts")
for item in COMPLIANCE:
    print(f"- [ ] compliance: {item}")
