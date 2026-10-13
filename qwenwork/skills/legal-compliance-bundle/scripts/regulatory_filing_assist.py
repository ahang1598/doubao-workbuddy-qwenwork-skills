#!/usr/bin/env python3
"""regulatory_filing_assist.py — 监管报送辅助 (Skill #44)"""
import sys
from datetime import datetime

def filing_guide(report_type: str = "年报") -> str:
    guides = {
        "年报": {"deadline": "每年1月1日-6月30日", "platform": "国家企业信用信息公示系统", "items": "基本信息、股东出资、资产状况、社保信息"},
        "税务申报": {"deadline": "每月15日前", "platform": "电子税务局", "items": "增值税、企业所得税、附加税"},
        "社保申报": {"deadline": "每月15日前", "platform": "社保费管理客户端", "items": "养老、医疗、失业、工伤、生育"},
        "数据出境": {"deadline": "事前申报", "platform": "国家网信办", "items": "数据出境安全评估报告"}
    }
    g = guides.get(report_type, guides["年报"])
    r = f"# 监管报送指南：{report_type}\n\n"
    r += f"**报送类型**: {report_type}\n"
    r += f"**截止时间**: {g['deadline']}\n"
    r += f"**报送平台**: {g['platform']}\n"
    r += f"**报送内容**: {g['items']}\n\n"
    r += "## 报送流程\n\n"
    r += "1. 登录报送平台\n"
    r += "2. 填写/上传报送资料\n"
    r += "3. 核对信息准确性\n"
    r += "4. 提交并获取回执\n"
    r += "5. 保存报送记录\n\n"
    r += "## 注意事项\n\n- 逾期报送可能面临罚款\n- 虚假报送将承担法律责任\n- 建议提前准备，避免最后期限\n"
    return r

def main():
    import argparse; p = argparse.ArgumentParser(); p.add_argument("--type", default="年报", choices=["年报","税务申报","社保申报","数据出境"]); p.add_argument("--output","-o"); a = p.parse_args()
    r = filing_guide(a.type)
    if a.output:
        with open(a.output, "w", encoding="utf-8") as f: f.write(r); print(f"✅ 已保存至: {a.output}")
    else: print(r)

if __name__ == "__main__": main()
