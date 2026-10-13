#!/usr/bin/env python3
"""ip_licensing_template.py — IP许可协议模板 (Skill #32)"""
import sys
from datetime import datetime

def generate(ip_type: str = "软件著作权", licensor: str = "许可方", licensee: str = "被许可方") -> str:
    return f"""# {ip_type}许可使用协议

**签订日期**: {datetime.now().strftime('%Y年%m月%d日')}

## 第一条 许可标的
{licensor}将其合法拥有的{ip_type}许可给{licensee}使用。

## 第二条 许可类型
☐ 独占许可（仅被许可方可使用）
☐ 排他许可（许可方和被许可方可使用）
☐ 普通许可（许可方可许可多方使用）

## 第三条 许可范围
1. 地域范围：中华人民共和国境内
2. 使用方式：（具体使用方式待填）
3. 是否可转许可：☐ 可以 / ☐ 不可以

## 第四条 许可期限
自____年__月__日起至____年__月__日止。

## 第五条 许可费用
1. 许可费总额：人民币____元
2. 支付方式：☐ 一次性支付 / ☐ 分期支付 / ☐ 按销售额提成__%
3. 支付时间：

## 第六条 双方权利义务
**许可方义务**：保证许可标的权属清晰、协助被许可方使用
**被许可方义务**：按约定使用、按时支付费用、不得超范围使用

## 第七条 违约责任
违约方应赔偿守约方因此遭受的全部损失。

## 第八条 争议解决
本协议适用中华人民共和国法律，争议提交____仲裁委员会仲裁/____人民法院诉讼解决。
"""

def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--ip-type", default="软件著作权")
    p.add_argument("--licensor", default="许可方")
    p.add_argument("--licensee", default="被许可方")
    p.add_argument("--output", "-o")
    a = p.parse_args()
    r = generate(a.ip_type, a.licensor, a.licensee)
    if a.output:
        with open(a.output, "w", encoding="utf-8") as f: f.write(r)
        print(f"✅ 已保存至: {a.output}")
    else: print(r)

if __name__ == "__main__": main()
