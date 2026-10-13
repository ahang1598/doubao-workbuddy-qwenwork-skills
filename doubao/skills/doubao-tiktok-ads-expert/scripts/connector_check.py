#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔌 TikTok for Business 连接器状态校准模块（平台关联模式）

本模块提供豆包官方「TikTok for Business」连接器的状态检查与关联引导。

⚠️  重要说明：
- 连接器状态检查必须由 Agent 通过 tool_search 完成（Python 脚本无法直接调用 Agent 工具）
- 本脚本提供：检查方法论、状态格式化输出、未连接时的关联引导文案
- Agent 在执行任何 TikTok 操作前，必须先完成连接器校准

使用方式：
  # 查看连接器检查方法论（Agent 执行前阅读）
  python3 connector_check.py --method

  # 输出已连接状态展示
  python3 connector_check.py --status connected

  # 输出未连接状态 + 关联引导
  python3 connector_check.py --status disconnected

  # Agent 自检：输出 tool_search 检查关键词和判定标准
  python3 connector_check.py --agent-check
"""

import argparse
import sys


# ==================== 连接器配置 ====================

# 连接器校准：tool_search 检出任意 mcp__tiktok_business__* 工具即判定已连接。
# 注意：tool_search 可能只返回部分工具（如 page_get/app_list_get），
# report_integrated_get、auth_advertiser_get、smart_plus_* 等核心工具
# 在运行时通过 MCP 连接可用，具体工具可用性在调用时确认，不在校准阶段硬拦截。
CONNECTOR_TOOL_PREFIX = "mcp__tiktok_business__"

# Agent 用于检查连接器的 tool_search 关键词
CONNECTOR_CHECK_KEYWORDS = [
    "tiktok_business",
    "tiktok ads",
    "mcp__tiktok_business__report",
]

# 运行时预期可用的核心工具（用于文档说明，不作为 tool_search 硬校验条件）
EXPECTED_CORE_TOOLS = [
    "mcp__tiktok_business__report_integrated_get",
    "mcp__tiktok_business__auth_advertiser_get",
]

# 完整功能需要的工具（运行时通过 MCP 连接或 tool_list 动态发现）
OPTIONAL_TOOLS = [
    "mcp__tiktok_business__smart_plus_campaign_create",
    "mcp__tiktok_business__smart_plus_adgroup_create",
    "mcp__tiktok_business__smart_plus_ad_create",
    "mcp__tiktok_business__tiktok_ads_diagnosis_agent",
    "mcp__tiktok_business__tool_execute",
]


# ==================== 状态输出 ====================

def print_methodology():
    """输出连接器检查方法论（Agent 执行前阅读）"""
    print("""
🔌 【TikTok for Business 连接器校准方法论】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【第一步：Agent 执行 tool_search 检查】
  Agent 必须调用 tool_search 工具，使用以下任一关键词：
    - "tiktok_business"
    - "tiktok for business"
    - "mcp__tiktok_business__report"

【第二步：判定连接状态】
  ✅ 已连接：tool_search 返回任意包含 mcp__tiktok_business__ 前缀的工具
  ❌ 未连接：tool_search 未返回任何 mcp__tiktok_business__ 前缀的工具

  注意：tool_search 可能只索引部分工具（如 page_get、app_list_get），
  未在 tool_search 中出现的工具（report_integrated_get、smart_plus_* 等）
  在运行时通过 MCP 连接可用，不影响连接判定。

【第三步：工具可用性（运行时确认）】
  以下核心工具在连接器已连接时运行时可用：
    - mcp__tiktok_business__report_integrated_get（报表查询）
    - mcp__tiktok_business__auth_advertiser_get（账户查询）
  完整功能还需要：
    - smart_plus_campaign/adgroup/ad 系列（广告搭建）
    - tiktok_ads_diagnosis_agent（投放诊断）
    - tool_execute（动态调度，传统拍卖广告）
  如调用时工具不可用，按平台返回的错误信息引导用户检查授权。

【第四步：根据状态执行】
  - 已连接 → 继续执行业务操作
  - 未连接 → 输出关联引导文案，暂停执行，等待用户完成关联

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")


def print_agent_check():
    """输出 Agent 自检指令（tool_search 关键词和判定标准）"""
    print("""
🤖 【Agent 连接器自检指令】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

执行以下 tool_search 调用检查连接器：

  tool_search(query="tiktok_business")

判定标准：
  返回结果中包含任意 "mcp__tiktok_business__" 前缀工具 → 连接器已连接
  返回结果为空或无此前缀工具 → 连接器未连接

  注意：tool_search 可能只返回部分工具，未出现的核心工具
  （report_integrated_get、auth_advertiser_get、smart_plus_* 等）
  在运行时通过 MCP 连接可用，不影响连接判定。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")


def print_connected_status(detected_tools=None):
    """输出已连接状态展示"""
    tools = detected_tools or []
    tiktok_tools = [t for t in tools if CONNECTOR_TOOL_PREFIX in t] if tools else []
    optional_count = sum(1 for t in OPTIONAL_TOOLS if any(t in tool for tool in tools)) if tools else 0

    lines = [
        "",
        "🔌 【TikTok for Business 连接器状态】",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "连接器:    ✅ 豆包官方 TikTok for Business 已连接",
        f"工具前缀:  {CONNECTOR_TOOL_PREFIX}",
        f"已检出工具: {len(tiktok_tools)} 个" + (f"（tool_search 索引，运行时可用工具更多）" if tiktok_tools else ""),
        f"扩展工具:  {'✅ 可用' if optional_count > 0 else '⚠️ 未在 tool_search 中检出（运行时可能可用）'} ({optional_count}/{len(OPTIONAL_TOOLS)})",
        "授权方式:  平台统一 OAuth",
        "状态:      🟢 可正常执行操作",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
    ]

    if tiktok_tools:
        lines.append("📋 已检测到的工具:")
        for tool in tiktok_tools[:15]:
            lines.append(f"  - {tool}")
        if len(tiktok_tools) > 15:
            lines.append(f"  ... 等共 {len(tiktok_tools)} 个工具")
        lines.append("")

    print("\n".join(lines))


def print_disconnected_status():
    """输出未连接状态 + 关联引导"""
    print("""
🔌 【TikTok for Business 连接器状态】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
连接器:    ❌ 未连接
工具前缀:  未检测到 mcp__tiktok_business__ 工具
授权方式:  待关联
状态:      🔴 无法执行 TikTok Ads 操作
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️  当前豆包官方「TikTok for Business」连接器未关联，无法执行任何 TikTok 广告操作。

📖 【关联操作引导】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

请按以下步骤完成 TikTok for Business 连接器关联：

  第一步：打开连接器管理
    → 在豆包客户端中进入「设置」→「连接器」或「插件管理」
    → 找到「TikTok for Business」连接器（如截图所示）

  第二步：开启连接器
    → 点击「TikTok for Business」右侧的开关，将其切换为开启状态（蓝色）

  第三步：完成 OAuth 授权
    → 在弹出的 TikTok for Business 登录页面中登录你的广告账户
    → 授权豆包访问你的 TikTok Ads 数据（只读 + 写权限）
    → 选择要关联的广告主账户（Advertiser）

  第四步：确认连接成功
    → 连接器开关显示为蓝色开启状态
    → 回到对话，重新发送你的操作指令

  💡 提示：
    - 关联需要你拥有 TikTok for Business 广告账户的管理员权限
    - 授权过程在浏览器中完成，不会在对话中暴露任何 Token
    - 关联成功后，本 skill 的所有功能即可正常使用

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏸️  操作已暂停。完成关联后请重新发送指令，我将自动重新检测连接器状态。
""")


def check_and_guide(detected_tools=None):
    """
    综合检查函数：根据检测到的工具列表输出对应状态。

    Args:
        detected_tools: Agent 通过 tool_search 检测到的工具名列表
                        为 None 时输出未连接状态

    Returns:
        dict: {"connected": bool, "core_tools": list, "message": str}
    """
    if not detected_tools:
        print_disconnected_status()
        return {"connected": False, "core_tools": [], "message": "连接器未连接"}

    # 检出任意 mcp__tiktok_business__* 工具即判定已连接
    tiktok_tools = [t for t in detected_tools if CONNECTOR_TOOL_PREFIX in t]
    if not tiktok_tools:
        print_disconnected_status()
        return {"connected": False, "core_tools": [], "message": "连接器未连接"}

    print_connected_status(detected_tools)
    return {
        "connected": True,
        "core_tools": tiktok_tools,
        "message": "连接器已连接，可正常执行操作",
    }


def main():
    parser = argparse.ArgumentParser(
        description="TikTok for Business 连接器状态校准模块",
        epilog="⚠️  连接器检查必须由 Agent 通过 tool_search 完成，本脚本提供方法论和输出格式化"
    )
    parser.add_argument("--method", action="store_true",
                        help="输出连接器检查方法论")
    parser.add_argument("--agent-check", action="store_true",
                        help="输出 Agent 自检指令（tool_search 关键词）")
    parser.add_argument("--status", choices=["connected", "disconnected", "check"],
                        default="check",
                        help="输出指定状态: connected/disconnected/check")
    parser.add_argument("--tools", type=str, default="",
                        help='已检测到的工具列表 JSON，如 \'["mcp__tiktok_business__report_integrated_get"]\'')
    args = parser.parse_args()

    if args.method:
        print_methodology()
        return

    if args.agent_check:
        print_agent_check()
        return

    if args.status == "connected":
        print_connected_status()
    elif args.status == "disconnected":
        print_disconnected_status()
    else:
        # check 模式：如果提供了工具列表则综合判断，否则输出方法论
        if args.tools:
            import json
            try:
                tools = json.loads(args.tools)
                check_and_guide(tools)
            except json.JSONDecodeError:
                print("❌ tools 参数 JSON 解析失败", file=sys.stderr)
                sys.exit(1)
        else:
            print_methodology()
            print("\n💡 使用 --status connected 或 --status disconnected 查看对应状态输出")
            print("   使用 --agent-check 查看 Agent 自检指令")


if __name__ == "__main__":
    main()
