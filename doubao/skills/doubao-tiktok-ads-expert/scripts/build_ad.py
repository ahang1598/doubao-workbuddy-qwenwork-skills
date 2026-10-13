#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
端到端广告搭建脚本（平台关联模式）

⚠️  平台关联模式：本脚本不再直接调用 API，而是生成「操作计划」。
Agent 读取计划后，按步骤调用平台 mcp__tiktok_business__* 工具执行。

使用方式：
  python3 build_ad.py --config brief.json --output plan.json
  # 输出的 plan.json 包含带依赖关系的步骤列表，Agent 逐步执行

计划格式：
  {
    "advertiser_id": "...",
    "steps": [
      {
        "step": 1,
        "name": "创建 Campaign",
        "platform_tool": "mcp__tiktok_business__smart_plus_campaign_create",
        "arguments": {...},
        "output_field": "campaign_id",
        "depends_on": []
      },
      {
        "step": 2,
        "name": "创建 Ad Group",
        "platform_tool": "mcp__tiktok_business__smart_plus_adgroup_create",
        "arguments": {...},  // 含 {{campaign_id}} 占位符
        "output_field": "adgroup_id",
        "depends_on": [1]
      },
      ...
    ]
  }
"""

import argparse
import json
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tiktok_mcp_client import TikTokAdsMCPClient


def build_ad_plan(config: dict) -> dict:
    """
    生成端到端广告搭建计划（平台关联模式）

    config 结构:
    {
        "advertiser_id": "...",
        "campaign": {
            "campaign_name": "...",
            "objective_type": "APP_PROMOTION",
            "budget_mode": "BUDGET_MODE_DAY",
            "budget": 50
        },
        "adgroup": {
            "adgroup_name": "...",
            "optimization_goal": "INSTALL",
            "billing_event": "OCPM",
            "bid_type": "BID_TYPE_NO_BID",
            "bid_amount": 0,
            "targeting": {...},
            "placement": {...}
        },
        "ad": {
            "ad_name": "...",
            "ad_format": "SINGLE_VIDEO",
            "video_id": "...",
            "ad_text": "...",
            "call_to_action": "INSTALL_NOW"
        }
    }
    """
    advertiser_id = str(config.get("advertiser_id", ""))
    if not advertiser_id:
        return {"success": False, "error": "缺少 advertiser_id", "steps": []}

    client = TikTokAdsMCPClient(advertiser_id=advertiser_id)
    steps = []

    # ===== Step 1: 创建 Campaign =====
    campaign_config = config.get("campaign", {})
    campaign_name = campaign_config.get("campaign_name", f"Campaign_{int(time.time())}")

    call1 = client.create_campaign(
        campaign_name=campaign_name,
        objective_type=campaign_config.get("objective_type", "APP_PROMOTION"),
        budget_mode=campaign_config.get("budget_mode", "BUDGET_MODE_DAY"),
        budget=campaign_config.get("budget", 50),
        operation_status="DISABLE",
    )
    steps.append({
        "step": 1,
        "name": "创建 Campaign",
        "platform_tool": call1["platform_tool"],
        "arguments": call1["arguments"],
        "description": call1["description"],
        "output_field": "campaign_id",
        "output_path": "data.campaign_id",
        "depends_on": [],
    })

    # ===== Step 2: 创建 Ad Group =====
    adgroup_config = config.get("adgroup", {})
    adgroup_name = adgroup_config.get("adgroup_name", f"AdGroup_{int(time.time())}")

    call2 = client.create_adgroup(
        adgroup_name=adgroup_name,
        campaign_id="{{campaign_id}}",  # 占位符，Agent 执行时替换
        optimization_goal=adgroup_config.get("optimization_goal", "INSTALL"),
        billing_event=adgroup_config.get("billing_event", "OCPM"),
        bid_type=adgroup_config.get("bid_type", "BID_TYPE_NO_BID"),
        bid_amount=adgroup_config.get("bid_amount", 0),
        targeting=adgroup_config.get("targeting"),
        placement=adgroup_config.get("placement"),
        operation_status="DISABLE",  # 🚨 建成不投铁律：Ad Group 默认 DISABLE
    )
    steps.append({
        "step": 2,
        "name": "创建 Ad Group",
        "platform_tool": call2["platform_tool"],
        "arguments": call2["arguments"],
        "description": call2["description"],
        "output_field": "adgroup_id",
        "output_path": "data.adgroup_id",
        "depends_on": [1],
    })

    # ===== Step 3: 创建 Ad =====
    ad_config = config.get("ad", {})
    ad_name = ad_config.get("ad_name", f"Ad_{int(time.time())}")

    call3 = client.create_ad(
        ad_name=ad_name,
        adgroup_id="{{adgroup_id}}",  # 占位符
        ad_format=ad_config.get("ad_format", "SINGLE_VIDEO"),
        video_id=ad_config.get("video_id", ""),
        image_id=ad_config.get("image_id", ""),
        ad_text=ad_config.get("ad_text", ""),
        call_to_action=ad_config.get("call_to_action", ""),
        landing_page_url=ad_config.get("landing_page_url", ""),
        operation_status="DISABLE",  # 🚨 建成不投铁律：Ad 默认 DISABLE
    )
    steps.append({
        "step": 3,
        "name": "创建 Ad",
        "platform_tool": call3["platform_tool"],
        "arguments": call3["arguments"],
        "description": call3["description"],
        "output_field": "ad_id",
        "output_path": "data.ad_id",
        "depends_on": [2],
    })

    # ===== Step 4（可选）: 启用广告 =====
    # 默认不自动启用，由用户确认后手动执行
    if config.get("auto_enable", False):
        call4 = client.update_campaign_status("{{campaign_id}}", "ENABLE")
        steps.append({
            "step": 4,
            "name": "启用 Campaign",
            "platform_tool": call4["platform_tool"],
            "arguments": call4["arguments"],
            "description": call4["description"],
            "output_field": None,
            "depends_on": [1, 3],
        })

    plan = {
        "success": True,
        "mode": "platform",
        "advertiser_id": advertiser_id,
        "total_steps": len(steps),
        "steps": steps,
        "summary": {
            "campaign_name": campaign_name,
            "adgroup_name": adgroup_name,
            "ad_name": ad_name,
            "objective_type": campaign_config.get("objective_type", "APP_PROMOTION"),
            "budget": campaign_config.get("budget", 50),
            "initial_status": "DISABLE（默认安全模式，确认后启用）",
        },
        "execution_guide": (
            "Agent 执行说明：按 step 顺序执行，每步调用 platform_tool 对应的平台工具；"
            "上一步返回结果中 output_path 字段的值，替换下一步 arguments 中的 {{占位符}}；"
            "全部完成后返回各实体 ID。"
        ),
    }
    return plan


def load_config(config_path: str) -> dict:
    """从文件加载配置"""
    if not os.path.exists(config_path):
        print(f"❌ 配置文件不存在: {config_path}", file=sys.stderr)
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        if config_path.endswith((".yaml", ".yml")):
            import yaml
            return yaml.safe_load(f)
        return json.load(f)


def print_plan_preview(plan: dict):
    """打印计划预览"""
    print("📋 广告搭建计划（平台关联模式）")
    print("━" * 60)
    print(f"广告主 ID: {plan['advertiser_id']}")
    print(f"总步骤数: {plan['total_steps']}")
    print(f"初始状态: {plan['summary']['initial_status']}")
    print("━" * 60)
    for step in plan["steps"]:
        deps = f" (依赖步骤: {step['depends_on']})" if step["depends_on"] else ""
        print(f"\n  Step {step['step']}: {step['name']}{deps}")
        print(f"    平台工具: {step['platform_tool']}")
        print(f"    输出字段: {step.get('output_field', '无')}")
        # 打印参数摘要
        args = step["arguments"]
        summary_args = {k: v for k, v in args.items()
                        if k not in ("advertiser_id", "operation_status")}
        print(f"    参数摘要: {json.dumps(summary_args, ensure_ascii=False)[:120]}...")
    print("\n" + "━" * 60)
    print("💡 Agent 将按步骤调用平台工具执行，无需手动管理 Token")


def main():
    parser = argparse.ArgumentParser(
        description="端到端广告搭建计划生成器（平台关联模式）",
        epilog="⚠️  平台关联模式：生成操作计划，由 Agent 调用平台工具执行"
    )
    parser.add_argument("--config", type=str, required=True, help="需求配置文件路径 (JSON/YAML)")
    parser.add_argument("--output", type=str, help="计划输出文件路径 (JSON)")
    parser.add_argument("--dry-run", action="store_true", help="仅验证配置并预览计划，不输出文件")
    args = parser.parse_args()

    config = load_config(args.config)

    if not config.get("advertiser_id"):
        print("❌ 配置中缺少 advertiser_id", file=sys.stderr)
        sys.exit(1)

    plan = build_ad_plan(config)

    if not plan.get("success"):
        print(f"❌ 计划生成失败: {plan.get('error', '未知错误')}", file=sys.stderr)
        sys.exit(1)

    print_plan_preview(plan)

    if args.dry_run:
        print("\n🔍 Dry Run 模式：仅预览，未输出文件")
        return

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(plan, f, ensure_ascii=False, indent=2)
        print(f"\n📄 计划已保存到: {args.output}")
    else:
        # 输出到 stdout 供 Agent 读取
        print("\n--- PLAN JSON ---")
        print(json.dumps(plan, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
