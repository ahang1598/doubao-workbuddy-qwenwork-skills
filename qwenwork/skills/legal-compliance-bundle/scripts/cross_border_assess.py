#!/usr/bin/env python3
"""cross_border_assess.py — 数据出境安全评估 (Skill #36)"""
import sys
from datetime import datetime

def assess_cross_border(data_type: str, recipient_country: str, data_volume: str) -> str:
    r = f"# 数据出境安全评估报告\n\n**评估时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    r += f"**数据类型**: {data_type}\n**接收方国家/地区**: {recipient_country}\n**数据量级**: {data_volume}\n\n---\n\n"
    r += "## 一、法规要求\n\n根据《数据出境安全评估办法》(2022)，以下情形须申报安全评估：\n"
    r += "1. 向境外提供重要数据\n2. 关键信息基础设施运营者向境外提供个人信息\n"
    r += "3. 处理100万人以上个人信息的数据处理者向境外提供个人信息\n"
    r += "4. 自上年1月1日起累计向境外提供10万人个人信息或1万人敏感个人信息\n\n"
    r += "## 二、评估要素\n\n"
    r += f"- 数据出境目的: {data_type}\n- 接收方数据保护水平: {'需重点评估' if recipient_country not in ['中国香港','中国澳门','中国台湾'] else '跨境但仍在境内'}\n"
    r += f"- 数据量级: {data_volume}\n\n"
    r += "## 三、合规路径建议\n\n"
    r += "1. **安全评估**（如适用）: 向国家网信办申报\n2. **标准合同**: 与境外接收方签订数据出境标准合同\n3. **认证**: 通过专业机构认证\n4. **其他**: 根据具体情况采取适当保障措施\n\n"
    r += "## 四、建议行动\n\n1. 确认是否属于须申报安全评估的情形\n2. 开展个人信息保护影响评估\n3. 与接收方签订数据处理协议\n4. 保存数据出境记录至少3年\n"
    return r

def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--data-type", default="个人信息")
    p.add_argument("--country", default="美国")
    p.add_argument("--volume", default="少量")
    p.add_argument("--output", "-o")
    a = p.parse_args()
    r = assess_cross_border(a.data_type, a.country, a.volume)
    if a.output:
        with open(a.output, "w", encoding="utf-8") as f: f.write(r)
        print(f"✅ 已保存至: {a.output}")
    else: print(r)

if __name__ == "__main__": main()
