#!/usr/bin/env python3
"""
patent_draft_assist.py — 专利辅助撰写 (Skill #28)
辅助撰写专利申请文件的摘要和权利要求书初稿。

用法: python patent_draft_assist.py --title "一种智能客服系统" --type invention --tech-field AI
"""

import sys
from datetime import datetime

PATENT_TEMPLATES = {
    "invention": {
        "name": "发明专利",
        "protection_years": 20,
        "requirements": "新颖性、创造性、实用性"
    },
    "utility": {
        "name": "实用新型",
        "protection_years": 10,
        "requirements": "新颖性、实用性（不要求创造性）"
    },
    "design": {
        "name": "外观设计",
        "protection_years": 15,
        "requirements": "新颖性、区别性"
    }
}

TECH_FIELDS = {
    "AI": "人工智能",
    "IoT": "物联网",
    "Blockchain": "区块链",
    "Software": "计算机软件",
    "Hardware": "电子硬件",
    "Biotech": "生物技术",
    "Medical": "医疗器械"
}


def draft_patent(title: str, patent_type: str = "invention", tech_field: str = "AI",
                 description: str = "") -> str:
    """辅助撰写专利申请文件"""
    pt = PATENT_TEMPLATES.get(patent_type, PATENT_TEMPLATES["invention"])
    field_name = TECH_FIELDS.get(tech_field, tech_field)

    doc = f"# 专利申请辅助文件\n\n"
    doc += f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    doc += f"**专利类型**: {pt['name']}（保护期{pt['protection_years']}年）\n"
    doc += f"**技术领域**: {field_name}\n\n"
    doc += "---\n\n"

    doc += f"## 一、发明名称\n\n{title}\n\n"

    doc += f"## 二、技术领域\n\n本发明涉及{field_name}领域，具体涉及{title}。\n\n"

    doc += f"## 三、背景技术\n\n"
    doc += f"【请在此处描述现有技术的不足和本发明要解决的技术问题】\n\n"
    doc += f"现有技术存在的问题：\n"
    doc += f"1. （问题一描述）\n"
    doc += f"2. （问题二描述）\n"
    doc += f"3. （问题三描述）\n\n"

    doc += f"## 四、发明内容\n\n"
    doc += f"为解决上述技术问题，本发明提供{title}，其技术方案如下：\n\n"
    doc += f"【请在此处详细描述技术方案】\n\n"
    doc += f"有益效果：\n"
    doc += f"1. （效果一）\n"
    doc += f"2. （效果二）\n"
    doc += f"3. （效果三）\n\n"

    doc += f"## 五、权利要求书（初稿模板）\n\n"
    doc += f"1. 一种{'智能' if '智能' in title or 'AI' in tech_field else ''}{'系统' if '系统' in title else '方法' if '方法' in title else '装置'}"
    doc += f"，其特征在于，包括：\n"
    doc += f"   （模块/步骤一）；\n"
    doc += f"   （模块/步骤二）；\n"
    doc += f"   （模块/步骤三）。\n\n"
    doc += f"2. 根据权利要求1所述的{'系统' if '系统' in title else '方法' if '方法' in title else '装置'}"
    doc += f"，其特征在于，（从属权利要求-进一步限定）。\n\n"
    doc += f"3. 根据权利要求1或2所述的{'系统' if '系统' in title else '方法' if '方法' in title else '装置'}"
    doc += f"，其特征在于，（从属权利要求-进一步限定）。\n\n"

    doc += f"## 六、摘要\n\n"
    doc += f"本发明公开了{title}，属于{field_name}领域。"
    doc += f"该{'系统' if '系统' in title else '方法'}通过（核心技术手段），解决了（技术问题），"
    doc += f"实现了（技术效果）。本发明具有（优势特点）等优点。\n\n"

    doc += "---\n\n"
    doc += f"## ⚠️ 使用说明\n\n"
    doc += f"1. 本文件为辅助撰写模板，需由专业专利代理人完善\n"
    doc += f"2. 权利要求书的撰写直接影响保护范围，建议咨询专业代理师\n"
    doc += f"3. 专利申请需通过国家知识产权局审查，建议委托代理机构办理\n"
    doc += f"4. {pt['name']}审查周期约{'2-3年' if patent_type == 'invention' else '6-12个月'}\n"

    return doc


def main():
    import argparse
    parser = argparse.ArgumentParser(description="专利辅助撰写")
    parser.add_argument("--title", required=True, help="发明名称")
    parser.add_argument("--type", dest="patent_type", default="invention", choices=["invention", "utility", "design"])
    parser.add_argument("--tech-field", default="AI")
    parser.add_argument("--output", "-o")
    args = parser.parse_args()

    result = draft_patent(args.title, args.patent_type, args.tech_field)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"✅ 专利辅助文件已保存至: {args.output}")
    else:
        print(result)


if __name__ == "__main__":
    main()
