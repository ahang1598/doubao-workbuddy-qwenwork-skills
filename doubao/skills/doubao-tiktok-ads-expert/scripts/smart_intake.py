#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 智能需求拆解模块（MCP版）
将用户的自然语言需求拆解为结构化的所需信息清单 + 风控安全提示。
"""

import argparse
import json
import sys
import re

# 风控检查规则（平台关联模式）
RISK_RULES = {
    "access_token": {"level": "critical", "label": "🔴 极高", "action": "由平台统一管理，绝不在对话中出现"},
    "refresh_token": {"level": "critical", "label": "🔴 极高", "action": "由平台统一管理，绝不在对话中出现"},
    "auth_code": {"level": "critical", "label": "🔴 极高", "action": "由平台授权流程自动处理，绝不在对话中出现"},
    "client_secret": {"level": "critical", "label": "🔴 极高", "action": "由平台统一管理，绝不在对话中出现"},
    "advertiser_id": {"level": "medium", "label": "🟡 中等", "action": "可正常传输，输出时部分脱敏"},
    "pixel_id": {"level": "low", "label": "🟢 低", "action": "可正常传输"},
}

# 营销目标映射
OBJECTIVE_MAP = {
    "app安装": "APP_PROMOTION",
    "app推广": "APP_PROMOTION",
    "应用安装": "APP_PROMOTION",
    "应用推广": "APP_PROMOTION",
    "转化": "CONVERSIONS",
    "网站转化": "CONVERSIONS",
    "流量": "TRAFFIC",
    "网站流量": "TRAFFIC",
    "曝光": "REACH",
    "覆盖": "REACH",
    "视频观看": "VIDEO_VIEWS",
    "粉丝增长": "ENGAGEMENT",
    "互动": "ENGAGEMENT",
    "线索": "LEAD_GENERATION",
    "销售": "PRODUCT_SALES",
}

# 优化目标映射
OPTIMIZATION_MAP = {
    "安装": "INSTALL",
    "下载": "INSTALL",
    "应用事件": "IN_APP_EVENT",
    "转化": "CONVERSIONS",
    "点击": "CLICK",
    "曝光": "IMPRESSION",
    "视频观看": "VIDEO_VIEW",
}

# 批量调控意图关键词
BATCH_CONTROL_KEYWORDS = {
    "status_enable": ["启用", "开启", "投放", "enable"],
    "status_disable": ["暂停", "关掉", "停掉", "关闭", "disable", "pause"],
    "status_delete": ["删除", "删掉", "delete"],
    "budget": ["预算", "budget", "加预算", "减预算", "提预算", "降预算"],
    "bid": ["出价", "bid", "加价", "降价", "提价", "竞价"],
    "rename": ["重命名", "改名", "rename", "加前缀", "加后缀"],
}


def detect_control_action(demand: str) -> str:
    """检测用户需求是否为批量调控操作

    Returns:
        "create" / "status" / "budget" / "bid" / "rename" / "unknown"
    """
    demand_lower = demand.lower()

    # 批量调控关键词
    has_batch = any(kw in demand_lower for kws in BATCH_CONTROL_KEYWORDS.values() for kw in kws)
    has_batch_marker = any(w in demand_lower for w in ["批量", "这些", "那些", "几个", "一批", "所有", "全部"])

    if has_batch or has_batch_marker:
        for action, keywords in BATCH_CONTROL_KEYWORDS.items():
            if any(kw in demand_lower for kw in keywords):
                return action.split("_")[0] if "_" in action else action
        if has_batch_marker:
            return "status"

    # 默认为创建
    if any(w in demand_lower for w in ["创建", "搭建", "新建", "建一个", "建一条", "create", "build"]):
        return "create"

    return "unknown"


def detect_control_level(demand: str) -> str:
    """检测调控层级"""
    demand_lower = demand.lower()
    if any(w in demand_lower for w in ["广告系列", "campaign", "计划"]):
        return "campaign"
    if any(w in demand_lower for w in ["广告组", "adgroup", "ad group", "单元"]):
        return "adgroup"
    if any(w in demand_lower for w in ["广告", "ad ", "创意", "ad"]):
        return "ad"
    return "adgroup"  # 默认广告组


def detect_objective(demand: str) -> str:
    """从需求文本中检测营销目标"""
    demand_lower = demand.lower()
    for keyword, objective in OBJECTIVE_MAP.items():
        if keyword in demand_lower:
            return objective
    return "APP_PROMOTION"  # 默认


def detect_optimization(demand: str) -> str:
    """从需求文本中检测优化目标"""
    demand_lower = demand.lower()
    for keyword, opt in OPTIMIZATION_MAP.items():
        if keyword in demand_lower:
            return opt
    return "INSTALL"  # 默认


def detect_region(demand: str) -> str:
    """从需求文本中检测投放地区"""
    regions = ["US", "美国", "UK", "英国", "JP", "日本", "KR", "韩国", "东南亚", "欧洲", "全球"]
    for r in regions:
        if r in demand:
            return r
    return "US（需确认）"


def detect_budget(demand: str) -> str:
    """从需求文本中检测预算"""
    # 匹配数字 + 货币
    match = re.search(r'(\d+)\s*(美元|美金|usd|\$|元|rmb|cny)', demand.lower())
    if match:
        amount = match.group(1)
        currency = match.group(2)
        currency_map = {"美元": "$", "美金": "$", "usd": "$", "$": "$", "元": "¥", "rmb": "¥", "cny": "¥"}
        return f"{currency_map.get(currency, '$')}{amount}"
    return "需确认"


def generate_intake(demand: str, fmt: str = "markdown") -> str:
    """生成需求拆解结果"""
    objective = detect_objective(demand)
    optimization = detect_optimization(demand)
    region = detect_region(demand)
    budget = detect_budget(demand)

    if fmt == "json":
        result = {
            "demand": demand,
            "required_info": {
                "credentials": [
                    "MCP连接状态（平台关联模式，自动就绪）",
                    "advertiser_id（用户提供或通过 auth_advertiser_get 查询）",
                    "OAuth Token（平台统一管理，永不暴露）",
                ],
                "campaign": {
                    "objective_type": objective,
                    "budget_mode": "日预算/总预算",
                    "budget_amount": budget,
                },
                "ad_group": {
                    "optimization_goal": optimization,
                    "bid_type": "自动/手动",
                    "targeting": {"region": region, "age": "需确认", "gender": "需确认"},
                    "placement": "需确认",
                },
                "ad": {
                    "creative_type": "视频/图片",
                    "ad_text": "需确认",
                    "cta": "需确认",
                },
            },
            "risk_warnings": [
                "平台关联模式：授权由平台统一管理，Token 永不暴露",
                "所有写操作通过平台工具执行，Agent 执行前需用户确认",
                "advertiser_id 输出时自动脱敏",
            ],
        }
        return json.dumps(result, ensure_ascii=False, indent=2)

    # Markdown 格式
    result = f"""📋 需求拆解结果
【1/2】你需要准备的信息
  ├─ 账户信息（平台关联模式，无需配置）
  │   ├─ ✅ MCP连接状态：平台已绑定
  │   ├─ ⚠️ advertiser_id（需提供或通过平台工具查询）
  │   └─ ✅ OAuth Token（平台统一管理，永不暴露）
  ├─ 广告计划（Campaign）
  │   ├─ 营销目标：{objective}
  │   ├─ 预算模式：日预算 / 总预算
  │   └─ 预算金额：{budget}
  ├─ 广告组（Ad Group）
  │   ├─ 优化目标：{optimization}
  │   ├─ 出价方式：自动 / 手动
  │   ├─ 定向设置（地区：{region}、年龄、性别等）
  │   └─ 版位选择
  └─ 广告创意（Ad）
      ├─ 视频素材 / 图片素材
      ├─ 广告文案
      └─ CTA 按钮

【2/2】风控安全提示
  🔴  平台关联模式安全提示
  ├─ 授权由平台统一管理，无需在对话中发送任何 Token
  │   └─ 所有写操作通过平台工具执行，Agent 会在执行前确认
  ├─ 授权码（auth_code）由平台授权流程自动处理
  └─ advertiser_id 输出时自动脱敏（****1234）

💡 提供以上信息后，我将为你执行广告搭建。
"""
    return result


def generate_batch_intake(demand: str, fmt: str = "markdown") -> str:
    """生成批量调控需求拆解结果"""
    action = detect_control_action(demand)
    level = detect_control_level(demand)

    action_map = {
        "status": "批量状态调控（启用/暂停/删除）",
        "budget": "批量预算调整",
        "bid": "批量出价调整",
        "rename": "批量重命名",
    }
    action_desc = action_map.get(action, "批量调控")

    # 解析 ID 列表
    ids = re.findall(r'\b\d{6,}\b', demand)

    # 检测预算/出价调整模式
    adjust_mode = "需确认"
    adjust_value = "需确认"
    percent_match = re.search(r'(\d+)\s*%', demand)
    if percent_match:
        adjust_mode = "percent"
        adjust_value = percent_match.group(1)
    elif re.search(r'(设为|设置|改成|调到)\s*\$?(\d+\.?\d*)', demand):
        adjust_mode = "set"
        adjust_value = re.search(r'(\d+\.?\d*)', demand).group(1)

    if fmt == "json":
        result = {
            "demand": demand,
            "action": action,
            "level": level,
            "required_info": {
                "credentials": [
                    "MCP连接状态（平台关联模式，自动就绪）",
                    "advertiser_id（用户提供或通过 auth_advertiser_get 查询）",
                    "OAuth Token（平台统一管理，永不暴露）",
                ],
                "targets": {
                    "entity_ids": ids if ids else "需提供ID列表或筛选条件",
                    "filter": "可选：按状态/名称/所属Campaign筛选",
                },
                "params": {
                    "action": action_desc,
                    "level": level,
                    "adjust_mode": adjust_mode,
                    "adjust_value": adjust_value,
                },
            },
            "risk_warnings": [
                "批量调控默认预演(dry-run)，确认后才执行",
                "DELETE操作为高危操作，需二次确认",
                "大幅调整预算/出价可能导致模型波动，建议渐进式调整",
                "advertiser_id 输出时自动脱敏",
            ],
        }
        return json.dumps(result, ensure_ascii=False, indent=2)

    id_display = ", ".join(ids) if ids else "需提供ID列表或筛选条件"
    lines = []
    lines.append("📋 批量调控需求拆解结果")
    lines.append("【1/2】你需要准备的信息")
    lines.append("  ├─ 账户信息（平台关联模式，无需配置）")
    lines.append("  │   ├─ ✅ MCP连接状态：平台已绑定")
    lines.append("  │   ├─ ⚠️ advertiser_id（需提供或通过平台工具查询）")
    lines.append("  │   └─ ✅ OAuth Token（平台统一管理，永不暴露）")
    lines.append(f"  ├─ 调控操作：{action_desc}")
    lines.append(f"  ├─ 调控层级：{level}")
    lines.append(f"  ├─ 目标实体：{id_display}")
    if action in ("budget", "bid"):
        lines.append(f"  ├─ 调整模式：{adjust_mode}")
        lines.append(f"  └─ 调整数值：{adjust_value}")
    elif action == "rename":
        lines.append("  └─ 命名模式：prefix:X / suffix:X / replace:旧->新 / sequence:X")
    else:
        lines.append("  └─ 操作状态：ENABLE / DISABLE / DELETE")
    lines.append("")
    lines.append("【2/2】风控安全提示")
    lines.append("  🔴  操作安全")
    lines.append("  ├─ 批量调控默认预演(dry-run)，确认后才执行真实操作")
    lines.append("  ├─ DELETE 为高危操作，需二次确认")
    lines.append("  ├─ 大幅调整预算/出价可能导致模型波动，建议渐进式调整")
    lines.append("  └─ 暂停学习期广告组可能浪费学习成本")
    lines.append("")
    lines.append("💡 确认信息后我将先进行预演展示变更明细，你确认后再执行。")
    return "\n".join(lines)
    """检查文本中的敏感信息风险"""
    warnings = []

    # 检测 access_token 模式
    if re.search(r'(access_token|token)\s*[:=]\s*[A-Za-z0-9_\-]{20,}', text, re.IGNORECASE):
        warnings.append({
            "field": "access_token",
            "level": "critical",
            "message": "⚠️  检测到 access_token！绝对不能在聊天中发送，请立即删除。平台关联模式下由平台统一管理。"
        })

    # 检测 refresh_token 模式
    if re.search(r'(refresh_token)\s*[:=]\s*[A-Za-z0-9_\-]{20,}', text, re.IGNORECASE):
        warnings.append({
            "field": "refresh_token",
            "level": "critical",
            "message": "⚠️  检测到 refresh_token！绝对不能在聊天中发送，请立即删除。"
        })

    # 检测 auth_code 模式
    if re.search(r'(auth_code|authorization_code)\s*[:=]\s*[A-Za-z0-9_\-]{10,}', text, re.IGNORECASE):
        warnings.append({
            "field": "auth_code",
            "level": "critical",
            "message": "⚠️  检测到授权码（auth_code）！绝不能在聊天中发送，请立即删除。授权码应在授权流程中自动处理。"
        })

    # 检测 client_secret 模式
    if re.search(r'(client_secret|app_secret)\s*[:=]\s*[A-Za-z0-9_\-]{10,}', text, re.IGNORECASE):
        warnings.append({
            "field": "client_secret",
            "level": "critical",
            "message": "⚠️  检测到 client_secret！禁止在会话中传输，请立即删除。平台关联模式下由平台统一管理。"
        })

    return warnings


def main():
    parser = argparse.ArgumentParser(description="智能需求拆解 + 风控检查（MCP版）")
    parser.add_argument("--demand", type=str, help="用户需求描述")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown", help="输出格式")
    parser.add_argument("--check-risk", type=str, help="检查文本中的敏感信息风险")
    parser.add_argument("--batch", action="store_true", help="按批量调控模式拆解需求")
    args = parser.parse_args()

    if args.check_risk:
        warnings = check_risk(args.check_risk)
        if warnings:
            for w in warnings:
                print(f"{w['level'].upper()}: {w['message']}")
        else:
            print("✅ 未检测到敏感信息风险")
        return

    if args.demand:
        if args.batch or detect_control_action(args.demand) in ("status", "budget", "bid", "rename"):
            result = generate_batch_intake(args.demand, args.format)
        else:
            result = generate_intake(args.demand, args.format)
        print(result)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
