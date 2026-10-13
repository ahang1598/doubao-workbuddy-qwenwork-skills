#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧭 智能导航模块（MCP版）
每台设备首次使用本 skill 时自动触发，展示能力导航栏。
"""

import argparse
import os
import sys

# 首次使用标记文件路径
FIRST_USE_FLAG = os.path.expanduser("~/.tiktok_ads_mcp_first_use")

NAV_TEMPLATE = """
📱 Tiktok广告投放专家（MCP版）— 能力导航
├── 🔧 可执行事项
│   ├── 搭建完整广告（Campaign → Ad Group → Ad）
│   ├── 上传创意素材（图片/视频）
│   ├── 启用/暂停/删除广告
│   ├── 查询枚举值与参数搭配
│   ├── 排查 API 报错
│   └── 查询素材规格
├── 🚀 使用流程
│   ├── Step 1：告诉我你的需求（如"搭建一个 App 安装广告"）
│   ├── Step 2：我会拆解所需信息 + 风控提示
│   ├── Step 3：你提供信息后我执行搭建
│   └── Step 4：返回概述结果，可随时查看详情
├── 🔌 MCP连接
│   ├── 官方端点：business-api.tiktok.com/open_mcp/tt-ads-mcp-flat
│   ├── OAuth授权，无需开发者Token
│   └── 连接状态可随时查询
└── 🔒 安全须知
    ├── OAuth Token加密存储在本地
    ├── 绝不明文传输Token或授权码
    ├── 建成默认暂停，确认后才启用
    └── 所有输出敏感字段自动脱敏
"""


def show_navigation():
    """展示能力导航栏"""
    print(NAV_TEMPLATE.strip())


def is_first_use():
    """检测是否首次使用"""
    return not os.path.exists(FIRST_USE_FLAG)


def mark_first_use_done():
    """标记首次使用已完成"""
    try:
        with open(FIRST_USE_FLAG, "w") as f:
            f.write("initialized")
    except Exception as e:
        print(f"⚠️  标记首次使用状态失败: {e}", file=sys.stderr)


def check_and_show():
    """检测是否首次使用，是则展示导航"""
    if is_first_use():
        show_navigation()
        mark_first_use_done()
        return True
    return False


def main():
    parser = argparse.ArgumentParser(description="Tiktok广告投放专家（MCP版）- 智能导航模块")
    parser.add_argument("--show", action="store_true", help="直接展示导航栏")
    parser.add_argument("--check-first", action="store_true", help="检测是否首次使用，是则展示")
    parser.add_argument("--reset", action="store_true", help="重置首次使用标记")
    args = parser.parse_args()

    if args.reset:
        if os.path.exists(FIRST_USE_FLAG):
            os.remove(FIRST_USE_FLAG)
            print("✅ 首次使用标记已重置")
        else:
            print("ℹ️  没有找到首次使用标记")
        return

    if args.show:
        show_navigation()
    elif args.check_first:
        shown = check_and_show()
        if not shown:
            print("ℹ️  非首次使用，跳过导航展示")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
