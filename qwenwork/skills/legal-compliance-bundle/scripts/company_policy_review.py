#!/usr/bin/env python3
"""company_policy_review.py — 制度审查 (Skill #46)"""
import sys
from datetime import datetime

def review_checklist() -> str:
    return f"""# 公司内部制度合规审查清单

**审查日期**: {datetime.now().strftime('%Y-%m-%d')}

## 一、劳动用工制度
- [ ] 劳动合同模板符合《劳动合同法》
- [ ] 员工手册经民主程序制定
- [ ] 考勤制度合理（加班需审批）
- [ ] 薪酬制度符合最低工资标准
- [ ] 竞业限制条款符合法律规定

## 二、数据合规制度
- [ ] 隐私政策符合《个人信息保护法》
- [ ] 数据分类分级制度
- [ ] 数据安全应急预案
- [ ] 个人信息权利响应机制

## 三、商业行为制度
- [ ] 反商业贿赂制度
- [ ] 利益冲突申报制度
- [ ] 礼品招待管理制度
- [ ] 供应商尽职调查制度

## 四、公司治理制度
- [ ] 公司章程符合最新《公司法》
- [ ] 股东会/董事会议事规则
- [ ] 关联交易管理制度
- [ ] 信息披露制度

## 五、知识产权制度
- [ ] 商业秘密保护制度
- [ ] 知识产权归属约定
- [ ] 软件正版化管理制度

## 审查结论
- [ ] 制度合规，可继续执行
- [ ] 存在风险，需修订后执行
- [ ] 严重不合规，立即停用

**审查人**: ________ **审核人**: ________
"""

def main():
    import argparse; p = argparse.ArgumentParser(); p.add_argument("--output","-o"); a = p.parse_args()
    r = review_checklist()
    if a.output:
        with open(a.output, "w", encoding="utf-8") as f: f.write(r); print(f"✅ 已保存至: {a.output}")
    else: print(r)

if __name__ == "__main__": main()
