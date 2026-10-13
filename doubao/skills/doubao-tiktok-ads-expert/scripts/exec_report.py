#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📊 双层执行反馈模块（Dual-layer Report）
生成两种粒度的执行报告：概述版（默认）和详细版（按需展开）。
"""

import argparse
import json
import sys
import os
import time


def mask_sensitive(data: dict) -> dict:
    """脱敏敏感字段"""
    sensitive_keys = ["access_token", "secret", "app_secret", "password"]
    result = data.copy()
    for key in sensitive_keys:
        if key in result and result[key]:
            val = str(result[key])
            if len(val) > 4:
                result[key] = f"****{val[-4:]}"
            else:
                result[key] = "****"
    return result


def generate_summary(result: dict) -> str:
    """生成概述版报告"""
    campaign = result.get("campaign", {})
    adgroup = result.get("adgroup", {})
    ad = result.get("ad", {})
    status = result.get("status", "已暂停（默认安全模式）")
    total_time = result.get("total_time_ms", 0)

    # 预算信息
    budget = campaign.get("budget", "N/A")
    budget_mode = campaign.get("budget_mode", "")
    budget_display = f"{budget}"
    if budget_mode and "DAY" in budget_mode.upper():
        budget_display = f"日预算: ${budget}"
    elif budget_mode and "TOTAL" in budget_mode.upper():
        budget_display = f"总预算: ${budget}"

    # 出价信息
    bid_type = adgroup.get("bid_type", "")
    bid_amount = adgroup.get("bid_amount", "")
    if "NO_BID" in str(bid_type):
        bid_display = "自动出价（最大投放量）"
    elif bid_amount:
        bid_display = f"手动出价: ${bid_amount}"
    else:
        bid_display = "需确认"

    # 定向信息
    targeting = adgroup.get("targeting", {})
    region = targeting.get("region", "N/A")
    age = targeting.get("age", "N/A")
    gender = targeting.get("gender", "不限")

    lines = []
    lines.append("✅ 广告搭建完成")
    lines.append("📊 执行概览")
    if campaign.get("campaign_id"):
        lines.append(f"  ├─ Campaign: {campaign.get('campaign_name', 'N/A')} (ID: {campaign['campaign_id']})")
    if adgroup.get("adgroup_id"):
        lines.append(f"  ├─ Ad Group: {adgroup.get('adgroup_name', 'N/A')} (ID: {adgroup['adgroup_id']})")
    if ad.get("ad_id"):
        lines.append(f"  └─ Ad: {ad.get('ad_name', 'N/A')} (ID: {ad['ad_id']})")
    lines.append("")
    lines.append("💰 预算与出价")
    lines.append(f"  ├─ {budget_display}")
    lines.append(f"  └─ 出价: {bid_display}")
    lines.append("")
    lines.append("🎯 定向设置")
    lines.append(f"  └─ 地区: {region} | 年龄: {age} | 性别: {gender}")
    lines.append("")
    lines.append(f"📌 当前状态: {status}")
    lines.append("   确认无误后回复\"启用\"即可开始投放")
    lines.append("")
    lines.append("💡 回复\"查看详情\"可展开完整执行日志")

    return "\n".join(lines)


def generate_detailed(result: dict) -> str:
    """生成详细版报告"""
    phases = result.get("phases", [])
    total_time = result.get("total_time_ms", 0)
    success_count = sum(1 for p in phases if p.get("success", False))
    total_count = len(phases)
    request_id = result.get("request_id", "N/A")

    lines = []
    lines.append("📋 详细执行日志")

    for i, phase in enumerate(phases):
        phase_name = phase.get("name", f"Phase {i+1}")
        lines.append(f"【Phase {i+1}】{phase_name}")

        if phase.get("request"):
            req = phase["request"]
            lines.append(f"  ├─ 请求: {req.get('method', 'POST')} {req.get('endpoint', '')}")

        if phase.get("params"):
            params = mask_sensitive(phase["params"])
            param_str = ", ".join(f"{k}={v}" for k, v in params.items() if k not in ["access_token", "secret"])
            lines.append(f"  ├─ 参数: {param_str}")

        if phase.get("response"):
            resp = phase["response"]
            code = resp.get("code", "N/A")
            status_icon = "✅" if code == 0 else "❌"
            lines.append(f"  ├─ 响应: code={code} {status_icon}")
            # 显示关键返回字段
            for key in ["campaign_id", "adgroup_id", "ad_id", "video_id", "image_id"]:
                if key in resp.get("data", {}):
                    lines.append(f"  │     {key}: {resp['data'][key]}")

        if phase.get("time_ms"):
            lines.append(f"  └─ 耗时: {phase['time_ms']}ms")

        lines.append("")

    lines.append("【汇总】")
    lines.append(f"  ├─ 总耗时: {total_time}ms ({total_time/1000:.2f}s)")
    lines.append(f"  ├─ 成功步骤: {success_count}/{total_count}")
    lines.append(f"  └─ request_id: {request_id}")

    return "\n".join(lines)


def load_result_from_file(filepath: str) -> dict:
    """从文件加载执行结果"""
    if not os.path.exists(filepath):
        print(f"❌ 文件不存在: {filepath}", file=sys.stderr)
        sys.exit(1)
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 读取文件失败: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="双层执行反馈生成")
    parser.add_argument("--result", type=str, help="执行结果 JSON 文件路径")
    parser.add_argument("--mode", choices=["summary", "detailed", "both"], default="summary", help="报告模式")
    parser.add_argument("--output", type=str, help="输出文件路径（默认 stdout）")
    args = parser.parse_args()

    if not args.result:
        parser.print_help()
        return

    result = load_result_from_file(args.result)

    output_parts = []

    if args.mode in ("summary", "both"):
        output_parts.append(generate_summary(result))

    if args.mode in ("detailed", "both"):
        if args.mode == "both":
            output_parts.append("\n" + "=" * 50 + "\n")
        output_parts.append(generate_detailed(result))

    output_text = "\n".join(output_parts)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output_text)
        print(f"✅ 报告已写入: {args.output}")
    else:
        print(output_text)


if __name__ == "__main__":
    main()
