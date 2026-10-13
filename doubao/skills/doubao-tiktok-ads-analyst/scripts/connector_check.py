#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔌 TikTok for Business 连接器状态校准模块（分析版 - 平台关联模式）

本模块提供豆包官方「TikTok for Business」连接器的状态检查与关联引导。

⚠️  重要说明：
- 连接器状态检查必须由 Agent 通过 tool_search 完成（Python 脚本无法直接调用 Agent 工具）
- 本脚本提供：检查方法论、状态格式化输出、未连接时的关联引导文案
- Agent 在执行任何 TikTok 分析操作前，必须先完成连接器校准

使用方式：
  python3 connector_check.py --method       # 查看检查方法论
  python3 connector_check.py --agent-check  # 查看 Agent 自检指令
  python3 connector_check.py --status connected     # 已连接状态展示
  python3 connector_check.py --status disconnected  # 未连接状态 + 关联引导
  python3 connector_check.py --status check --tools '["..."]'  # 综合判断
"""

import argparse
import json
import sys


CONNECTOR_TOOL_PREFIX = "mcp__tiktok_business__"

CONNECTOR_CHECK_KEYWORDS = [
    "tiktok_business",
    "tiktok ads",
    "mcp__tiktok_business__report",
]

# 连接器校准：tool_search 检出任意 mcp__tiktok_business__* 工具即判定已连接。
# 注意：tool_search 可能只返回部分工具，核心工具在运行时通过 MCP 连接可用。
EXPECTED_CORE_TOOLS = [
    "mcp__tiktok_business__report_integrated_get",
    "mcp__tiktok_business__auth_advertiser_get",
]

# 分析版扩展工具（运行时通过 MCP 连接或 tool_list 动态发现）
OPTIONAL_TOOLS = [
    "mcp__tiktok_business__tiktok_ads_diagnosis_agent",
    "mcp__tiktok_business__smart_plus_campaign_get",
    "mcp__tiktok_business__smart_plus_adgroup_get",
    "mcp__tiktok_business__smart_plus_ad_get",
    "mcp__tiktok_business__tool_execute",
]


def print_methodology():
    print("""
🔌 【TikTok for Business 连接器校准方法论（分析版）】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【第一步：Agent 执行 tool_search 检查】
  Agent 必须调用 tool_search，使用关键词：
    - "tiktok_business" 或 "tiktok for business"

【第二步：判定连接状态】
  ✅ 已连接：返回任意包含 mcp__tiktok_business__ 前缀的工具
  ❌ 未连接：未返回任何 mcp__tiktok_business__ 前缀的工具

  注意：tool_search 可能只索引部分工具，未出现的核心工具
  （report_integrated_get、auth_advertiser_get 等）
  在运行时通过 MCP 连接可用，不影响连接判定。

【第三步：工具可用性（运行时确认）】
  以下核心工具在连接器已连接时运行时可用：
    - mcp__tiktok_business__report_integrated_get（报表查询）
    - mcp__tiktok_business__auth_advertiser_get（账户查询）
  如调用时工具不可用，按平台返回的错误信息引导用户检查授权。

【第四步：根据状态执行】
  - 已连接 → 继续执行数据分析
  - 未连接 → 输出关联引导文案，暂停执行

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")


def print_agent_check():
    print("""
🤖 【Agent 连接器自检指令】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

执行：tool_search(query="tiktok_business")

判定：
  返回含任意 "mcp__tiktok_business__" 前缀工具 → 已连接
  返回为空或无此前缀 → 未连接

  注意：tool_search 可能只返回部分工具，未出现的核心工具
  在运行时通过 MCP 连接可用，不影响连接判定。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")


def print_connected_status(detected_tools=None):
    tools = detected_tools or []
    tiktok_tools = [t for t in tools if CONNECTOR_TOOL_PREFIX in t] if tools else []
    optional_count = sum(1 for t in OPTIONAL_TOOLS if any(t in tool for tool in tools)) if tools else 0

    lines = [
        "",
        "🔌 【TikTok for Business 连接器状态】",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "连接器:    ✅ 豆包官方 TikTok for Business 已连接",
        f"已检出工具: {len(tiktok_tools)} 个" + (f"（tool_search 索引，运行时可用工具更多）" if tiktok_tools else ""),
        f"诊断工具:  {'✅ 可用' if any('diagnosis' in t for t in tools) else '⚠️ 未在 tool_search 中检出（运行时可能可用）'}",
        "授权方式:  平台统一 OAuth（只读分析权限）",
        "状态:      🟢 可正常执行数据分析",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
    ]
    print("\n".join(lines))


def print_disconnected_status():
    print("""
🔌 【TikTok for Business 连接器状态】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
连接器:    ❌ 未连接
状态:      🔴 无法执行 TikTok Ads 数据分析
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️  当前豆包官方「TikTok for Business」连接器未关联，无法获取广告数据。

📖 【关联操作引导】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  第一步：打开连接器管理
    → 豆包客户端「设置」→「连接器」/「插件管理」
    → 找到「TikTok for Business」连接器

  第二步：开启连接器
    → 点击「TikTok for Business」右侧的开关，切换为蓝色开启状态

  第三步：完成 OAuth 授权
    → 在 TikTok for Business 登录页登录广告账户
    → 授权豆包访问广告数据（至少授予只读权限）
    → 选择要关联的广告主账户

  第四步：确认连接
    → 连接器开关显示为蓝色开启状态
    → 回到对话重新发送分析指令

  💡 提示：
    - 关联需要 TikTok for Business 广告账户的访问权限
    - 授权在浏览器中完成，不会在对话中暴露 Token
    - 关联成功后所有分析功能即可使用

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏸️  操作已暂停。完成关联后请重新发送指令，将自动重新检测连接器状态。
""")


def check_and_guide(detected_tools=None):
    if not detected_tools:
        print_disconnected_status()
        return {"connected": False, "message": "连接器未连接"}

    tiktok_tools = [t for t in detected_tools if CONNECTOR_TOOL_PREFIX in t]
    if not tiktok_tools:
        print_disconnected_status()
        return {"connected": False, "message": "连接器未连接"}

    print_connected_status(detected_tools)
    return {"connected": True, "message": "连接器已连接"}


def main():
    parser = argparse.ArgumentParser(
        description="TikTok for Business 连接器状态校准（分析版）",
        epilog="⚠️  连接器检查必须由 Agent 通过 tool_search 完成"
    )
    parser.add_argument("--method", action="store_true", help="输出检查方法论")
    parser.add_argument("--agent-check", action="store_true", help="输出 Agent 自检指令")
    parser.add_argument("--status", choices=["connected", "disconnected", "check"], default="check")
    parser.add_argument("--tools", type=str, default="", help="已检测工具列表 JSON")
    args = parser.parse_args()

    if args.method:
        print_methodology()
    elif args.agent_check:
        print_agent_check()
    elif args.status == "connected":
        print_connected_status()
    elif args.status == "disconnected":
        print_disconnected_status()
    else:
        if args.tools:
            try:
                check_and_guide(json.loads(args.tools))
            except json.JSONDecodeError:
                print("❌ tools 参数 JSON 解析失败", file=sys.stderr)
                sys.exit(1)
        else:
            print_methodology()


if __name__ == "__main__":
    main()
