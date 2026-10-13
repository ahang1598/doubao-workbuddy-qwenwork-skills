#!/usr/bin/env python3
"""external_counsel_brief.py — 外部律师简报 (Skill #47)"""
import sys
from datetime import datetime

def generate_brief(case_type: str, facts: str, questions: str) -> str:
    return f"""# 外部律师案情简报

**简报日期**: {datetime.now().strftime('%Y-%m-%d')}
**案件类型**: {case_type}

## 一、基本事实
{facts}

## 二、需咨询的法律问题
{questions}

## 三、相关证据材料
- [ ] 合同文件
- [ ] 往来函件/邮件
- [ ] 付款凭证
- [ ] 其他相关文件

## 四、期望结果
- [ ] 出具法律意见书
- [ ] 代理诉讼/仲裁
- [ ] 参与谈判
- [ ] 其他: ________

## 五、时间要求
- [ ] 紧急（3个工作日内）
- [ ] 一般（7个工作日内）
- [ ] 常规（15个工作日内）

## 六、联系方式
**联系人**: ________
**电话**: ________
**邮箱**: ________
"""

def main():
    import argparse; p = argparse.ArgumentParser(); p.add_argument("--case-type", default="合同纠纷"); p.add_argument("--facts", default="待补充"); p.add_argument("--questions", default="待补充"); p.add_argument("--output","-o"); a = p.parse_args()
    r = generate_brief(a.case_type, a.facts, a.questions)
    if a.output:
        with open(a.output, "w", encoding="utf-8") as f: f.write(r); print(f"✅ 已保存至: {a.output}")
    else: print(r)

if __name__ == "__main__": main()
