#!/usr/bin/env python3
"""board_resolution_gen.py — 决议生成 (Skill #45)"""
import sys
from datetime import datetime

def generate_resolution(company: str, resolution_type: str, content: str) -> str:
    return f"""# {company}股东会/董事会决议

**决议编号**: {datetime.now().strftime('%Y')}-____号
**会议时间**: {datetime.now().strftime('%Y年%m月%d日')}
**会议地点**: 公司会议室
**会议性质**: 临时/定期

## 一、会议通知情况
本次{resolution_type}已于____年__月__日通知全体股东/董事，会议召集程序符合《公司法》及公司章程规定。

## 二、出席情况
应到股东/董事____人，实到____人，代表____%表决权，会议有效。

## 三、决议事项
{content}

## 四、表决结果
☐ 同意____票，反对____票，弃权____票
☐ 决议通过/未通过

## 五、签字

股东/董事签字：

1. ____________    2. ____________    3. ____________

4. ____________    5. ____________

**公司盖章**：

**日期**：{datetime.now().strftime('%Y年%m月%d日')}
"""

def main():
    import argparse; p = argparse.ArgumentParser(); p.add_argument("--company", default="XX公司"); p.add_argument("--type", default="股东会", choices=["股东会","董事会"]); p.add_argument("--content", default="审议通过公司年度财务预算方案。"); p.add_argument("--output","-o"); a = p.parse_args()
    r = generate_resolution(a.company, a.type, a.content)
    if a.output:
        with open(a.output, "w", encoding="utf-8") as f: f.write(r); print(f"✅ 已保存至: {a.output}")
    else: print(r)

if __name__ == "__main__": main()
