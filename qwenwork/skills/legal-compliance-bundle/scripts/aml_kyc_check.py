#!/usr/bin/env python3
"""aml_kyc_check.py — 反洗钱/KYC合规检查 (Skill #41)"""
import sys
from datetime import datetime

def aml_checklist() -> str:
    return f"""# 反洗钱/KYC合规检查清单

**检查日期**: {datetime.now().strftime('%Y-%m-%d')}

## 一、客户身份识别(KYC)
- [ ] 核实客户真实身份（身份证/营业执照）
- [ ] 确认受益所有人（持股25%以上）
- [ ] 了解客户资金来源和用途
- [ ] 评估客户风险等级（高/中/低）
- [ ] 建立客户身份资料和交易记录档案

## 二、大额和可疑交易报告
- [ ] 个人单笔5万元以上的现金交易
- [ ] 单位单笔200万元以上的转账交易
- [ ] 短期内资金分散转入集中转出或相反
- [ ] 与高风险国家/地区的交易
- [ ] 无明显经济目的的交易

## 三、制裁名单筛查
- [ ] 联合国安理会制裁名单
- [ ] 美国OFAC SDN名单
- [ ] 欧盟制裁名单
- [ ] 中国反洗钱监测名单

## 四、持续监控
- [ ] 定期更新客户信息（至少每年1次）
- [ ] 监控异常交易模式
- [ ] 关注政治敏感人物(PEP)
- [ ] 内部审计和培训

## 五、法律依据
- 《反洗钱法》
- 《金融机构大额交易和可疑交易报告管理办法》
- 《金融机构客户身份识别和客户身份资料及交易记录保存管理办法》
"""
def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--output", "-o")
    a = p.parse_args()
    r = aml_checklist()
    if a.output:
        with open(a.output, "w", encoding="utf-8") as f: f.write(r)
        print(f"✅ 已保存至: {a.output}")
    else: print(r)
if __name__ == "__main__": main()
