#!/usr/bin/env python3
"""
privacy_policy_gen.py — 隐私政策生成器 (Skill #34)
根据App/网站信息自动生成符合PIPL的隐私政策。

用法: python privacy_policy_gen.py --config app_info.json [--output privacy_policy.md]
"""

import sys
import json
from datetime import datetime
from pathlib import Path

# 默认模板字段
DEFAULT_APP_INFO = {
    "company_name": "XX科技有限公司",
    "app_name": "XX应用",
    "contact_email": "privacy@example.com",
    "contact_phone": "400-XXX-XXXX",
    "contact_address": "XX省XX市XX区XX路XX号",
    "data_types": ["姓名", "手机号", "邮箱", "设备信息"],
    "purposes": ["提供服务", "改善体验", "安全保障"],
    "third_parties": [],
    "data_retention": "服务期间及服务结束后3年",
    "has_minors": False,
    "has_cross_border": False,
    "has_sensitive_data": False,
}


def generate_privacy_policy(app_info: dict) -> str:
    """Generate PIPL-compliant privacy policy."""
    now = datetime.now().strftime("%Y年%m月%d日")
    info = {**DEFAULT_APP_INFO, **app_info}
    
    lines = [
        f"# {info['app_name']}隐私政策",
        "",
        f"**生效日期**: {now}",
        f"**最近更新**: {now}",
        "",
        f"{info['company_name']}（以下简称\u201c我们\u201d）深知个人信息对您的重要性，"
        f"我们将严格遵守《中华人民共和国个人信息保护法》（以下简称\u201cPIPL\u201d）等相关法律法规，"
        f"采取相应的安全保护措施来保护您的个人信息。",
        "",
        "本隐私政策将帮助您了解：",
        "1. 我们如何收集和使用您的个人信息",
        "2. 我们如何使用Cookie和同类技术",
        "3. 我们如何共享、转让、公开披露您的个人信息",
        "4. 我们如何保护您的个人信息",
        "5. 您的权利",
        "6. 我们如何处理未成年人的个人信息",
        "7. 您的个人信息如何在全球范围转移",
        "8. 本隐私政策如何更新",
        "9. 如何联系我们",
        "",
        "---",
        "",
        "## 一、我们如何收集和使用您的个人信息",
        "",
        f"我们收集您的个人信息的目的是为了向您提供{info['app_name']}的服务，具体包括：",
        "",
    ]
    
    # Data types and purposes
    lines.append("| 信息类型 | 收集目的 | 是否必填 |")
    lines.append("|----------|----------|----------|")
    for dt in info["data_types"]:
        purpose = info["purposes"][0] if info["purposes"] else "提供服务"
        lines.append(f"| {dt} | {purpose} | 视具体功能而定 |")
    lines.append("")
    
    # Sensitive data section
    if info.get("has_sensitive_data"):
        lines.extend([
            "### 敏感个人信息",
            "",
            "在特定场景下，我们可能需要收集您的敏感个人信息（如生物识别信息、"
            "金融账户信息、行踪轨迹信息等），我们将在收集前另行取得您的单独同意。",
            "",
        ])
    
    # Third party sharing
    lines.extend([
        "## 二、我们如何共享您的个人信息",
        "",
        "我们不会向任何第三方共享您的个人信息，但以下情形除外：",
        "1. 获得您明确同意的",
        "2. 为履行法定义务所必需的",
        "3. 为订立、履行合同所必需的",
        "",
    ])
    
    if info.get("third_parties"):
        lines.append("我们可能与以下第三方共享部分信息：")
        lines.append("")
        lines.append("| 第三方 | 共享目的 | 共享信息 |")
        lines.append("|--------|----------|----------|")
        for tp in info["third_parties"]:
            name = tp.get("name", "第三方服务")
            purpose = tp.get("purpose", "服务提供")
            data = tp.get("data", "必要信息")
            lines.append(f"| {name} | {purpose} | {data} |")
        lines.append("")
    
    # Data retention
    lines.extend([
        "## 三、我们如何保存您的个人信息",
        "",
        f"- **保存期限**: {info.get('data_retention', '服务期间及合理期限')}",
        f"- **存储地点**: 中华人民共和国境内",
        "- **安全措施**: 采用加密存储、访问控制等技术手段",
        "",
    ])
    
    # Cross-border
    if info.get("has_cross_border"):
        lines.extend([
            "### 跨境传输",
            "",
            "如需向境外传输您的个人信息，我们将：",
            "1. 通过国家网信部门组织的安全评估",
            "2. 经专业机构进行个人信息保护认证",
            "3. 按照标准合同与境外接收方订立合同",
            "",
        ])
    
    # User rights
    lines.extend([
        "## 四、您的权利",
        "",
        "根据PIPL，您享有以下权利：",
        "",
        "1. **知情权** — 了解我们如何处理您的个人信息",
        "2. **决定权** — 决定是否同意我们处理您的个人信息",
        "3. **查阅权** — 查阅我们持有的您的个人信息",
        "4. **复制权** — 获取您的个人信息副本",
        "5. **更正权** — 更正不准确的个人信息",
        "6. **删除权** — 在特定情形下要求删除您的个人信息",
        "7. **撤回同意权** — 随时撤回之前给出的同意",
        "8. **获取处理规则权** — 获取我们的个人信息处理规则",
        "",
        f"行使以上权利，请联系：{info['contact_email']}",
        "",
    ])
    
    # Minors
    if info.get("has_minors"):
        lines.extend([
            "## 五、未成年人保护",
            "",
            "我们非常重视对未成年人个人信息的保护。",
            "若您是未满14周岁的未成年人，需取得您的父母或监护人的同意后方可使用我们的服务。",
            "如我们发现在未取得可证实的父母同意的情况下收集了未成年人的个人信息，将尽快删除。",
            "",
        ])
    else:
        lines.extend([
            "## 五、未成年人保护",
            "",
            f"{info['app_name']}主要面向成年人提供服务。",
            "若您是未满18周岁的未成年人，请在监护人指导下使用我们的服务。",
            "",
        ])
    
    # Updates and contact
    lines.extend([
        "## 六、本隐私政策的更新",
        "",
        "我们可能适时修订本隐私政策。当隐私政策发生重大变更时，"
        "我们将通过应用内通知或其他方式告知您。继续使用我们的服务即表示您同意受修订后的隐私政策约束。",
        "",
        "## 七、如何联系我们",
        "",
        f"- **公司名称**: {info['company_name']}",
        f"- **联系邮箱**: {info['contact_email']}",
        f"- **联系电话**: {info['contact_phone']}",
        f"- **联系地址**: {info['contact_address']}",
        "",
        "如您对本隐私政策有任何疑问、意见或建议，请通过上述方式与我们联系。"
        "我们将在15个工作日内回复您的请求。",
        "",
        "---",
        "",
        f"*{info['company_name']}*",
        f"*{now}*",
    ])
    
    return "\n".join(lines)


def main():
    if "--help" in sys.argv or len(sys.argv) < 2:
        print("用法:")
        print("  python privacy_policy_gen.py --config app_info.json [--output policy.md]")
        print("  python privacy_policy_gen.py --demo")
        print("")
        print("app_info.json 格式:")
        print(json.dumps(DEFAULT_APP_INFO, ensure_ascii=False, indent=2))
        sys.exit(0)
    
    app_info = DEFAULT_APP_INFO.copy()
    output_file = None
    
    if "--demo" in sys.argv:
        app_info = DEFAULT_APP_INFO
    elif "--config" in sys.argv:
        idx = sys.argv.index("--config")
        if idx + 1 < len(sys.argv):
            config_path = Path(sys.argv[idx + 1])
            if config_path.exists():
                app_info = json.loads(config_path.read_text(encoding="utf-8"))
    
    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        if idx + 1 < len(sys.argv):
            output_file = sys.argv[idx + 1]
    
    policy = generate_privacy_policy(app_info)
    
    if output_file:
        Path(output_file).write_text(policy, encoding="utf-8")
        print(f"隐私政策已生成: {output_file}")
    else:
        print(policy)


if __name__ == "__main__":
    main()
