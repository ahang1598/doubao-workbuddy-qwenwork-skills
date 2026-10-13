#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TikTok Ads MCP Client - 分析版（平台关联模式）

⚠️  平台关联模式：
- 不再自行管理 OAuth Token / config.json
- 不再直接发 HTTP 请求
- 所有方法返回「平台工具调用指令」，由 Agent 调用 mcp__tiktok_business__* 工具执行
- 授权由平台统一管理

使用方式:
    python3 tiktok_mcp_client.py --action status
    python3 tiktok_mcp_client.py --action tools
    python3 tiktok_mcp_client.py --action report --advertiser-id xxx --start-date 2026-01-01 --end-date 2026-01-31
"""

import argparse
import json
import os
import sys


class TikTokMCPError(Exception):
    def __init__(self, code, message, response=None):
        self.code = code
        self.message = message
        self.response = response
        super().__init__(f"MCP Error [{code}]: {message}")


# 平台工具名映射
PLATFORM_TOOLS = {
    "report_integrated_get": "mcp__tiktok_business__report_integrated_get",
    "auth_advertiser_get": "mcp__tiktok_business__auth_advertiser_get",
    "advertiser_info_get": "mcp__tiktok_business__advertiser_info_get",
    "bc_get": "mcp__tiktok_business__bc_get",
    "tiktok_ads_diagnosis_agent": "mcp__tiktok_business__tiktok_ads_diagnosis_agent",
    "smart_plus_campaign_get": "mcp__tiktok_business__smart_plus_campaign_get",
    "smart_plus_adgroup_get": "mcp__tiktok_business__smart_plus_adgroup_get",
    "smart_plus_ad_get": "mcp__tiktok_business__smart_plus_ad_get",
    "tool_list": "mcp__tiktok_business__tool_list",
    "tool_get": "mcp__tiktok_business__tool_get",
    "tool_execute": "mcp__tiktok_business__tool_execute",
}


class TikTokAdsMCPClient:
    """TikTok Ads MCP 客户端（平台关联模式 - 分析版）"""

    def __init__(self, advertiser_id: str = ""):
        self.advertiser_id = advertiser_id
        self.mcp_endpoint = "platform-bound"
        self._request_id = 0

    def _get_next_request_id(self):
        self._request_id += 1
        return self._request_id

    def _make_call(self, tool_key: str, arguments: dict,
                   description: str = "") -> dict:
        """生成平台工具调用指令"""
        platform_tool = PLATFORM_TOOLS.get(tool_key, tool_key)
        if tool_key not in PLATFORM_TOOLS and not tool_key.startswith("mcp__"):
            platform_tool = PLATFORM_TOOLS["tool_execute"]
            arguments = {"tool_name": tool_key, "arguments": arguments}

        return {
            "platform_tool": platform_tool,
            "arguments": arguments,
            "description": description or tool_key,
            "request_id": str(self._get_next_request_id()),
            "mode": "platform",
        }

    def get_connection_status(self) -> dict:
        return {
            "endpoint": "platform-bound (mcp__tiktok_business__*)",
            "configured": True,
            "authorized": True,
            "auth_mode": "platform_oauth",
            "advertiser_id_configured": bool(self.advertiser_id),
            "tools_count": len(PLATFORM_TOOLS),
            "note": "平台关联模式，授权由平台统一管理，只读分析权限",
        }

    def list_tools(self) -> dict:
        return self._make_call("tool_list", {}, "列出平台可用工具")

    def list_accounts(self) -> dict:
        return self._make_call("auth_advertiser_get", {}, "查询已授权广告账户")

    def get_report(self, advertiser_id: str = "", start_date: str = "",
                   end_date: str = "", data_level: str = "AUCTION_ADVERTISER",
                   dimensions: list = None, metrics: list = None,
                   report_type: str = "BASIC", filtering: list = None,
                   page: int = 1, page_size: int = 100) -> dict:
        """生成报表查询指令"""
        adv_id = advertiser_id or self.advertiser_id
        if dimensions is None:
            dimensions = ["stat_time_day"]
        if metrics is None:
            metrics = [
                "spend", "impressions", "clicks", "ctr", "cpc", "cpm",
                "conversions", "cost_per_conversion", "conversion_rate",
                "frequency", "video_play_actions", "video_watched_2s",
                "video_watched_6s", "video_play_p25", "video_play_p50",
                "video_play_p75", "video_play_p100",
            ]
        arguments = {
            "advertiser_id": adv_id,
            "start_date": start_date,
            "end_date": end_date,
            "data_level": data_level,
            "dimensions": dimensions,
            "metrics": metrics,
            "report_type": report_type,
            "page": page,
            "page_size": page_size,
        }
        if filtering:
            arguments["filtering"] = filtering
        return self._make_call(
            "report_integrated_get", arguments,
            f"报表查询: {data_level} [{start_date}~{end_date}]",
        )

    def get_campaigns(self, advertiser_id: str = "", filtering: dict = None,
                      page: int = 1, page_size: int = 100) -> dict:
        adv_id = advertiser_id or self.advertiser_id
        arguments = {
            "advertiser_id": adv_id,
            "page": page,
            "page_size": page_size,
        }
        if filtering:
            arguments["filtering"] = filtering
        return self._make_call("smart_plus_campaign_get", arguments, "查询 Campaign 列表")

    def get_adgroups(self, advertiser_id: str = "", campaign_id: str = "",
                     filtering: dict = None, page: int = 1,
                     page_size: int = 100) -> dict:
        adv_id = advertiser_id or self.advertiser_id
        arguments = {
            "advertiser_id": adv_id,
            "page": page,
            "page_size": page_size,
        }
        if campaign_id:
            arguments["filtering"] = {"campaign_ids": [campaign_id]}
        if filtering:
            if "filtering" in arguments:
                arguments["filtering"].update(filtering)
            else:
                arguments["filtering"] = filtering
        return self._make_call("smart_plus_adgroup_get", arguments, "查询 Ad Group 列表")

    def get_ads(self, advertiser_id: str = "", adgroup_id: str = "",
                filtering: dict = None, page: int = 1,
                page_size: int = 100) -> dict:
        adv_id = advertiser_id or self.advertiser_id
        arguments = {
            "advertiser_id": adv_id,
            "page": page,
            "page_size": page_size,
        }
        if adgroup_id:
            arguments["filtering"] = {"adgroup_ids": [adgroup_id]}
        if filtering:
            if "filtering" in arguments:
                arguments["filtering"].update(filtering)
            else:
                arguments["filtering"] = filtering
        return self._make_call("smart_plus_ad_get", arguments, "查询 Ad 列表")

    def diagnose(self, advertiser_id: str = "", campaign_id: str = "",
                 adgroup_id: str = "", issue_type: str = "UNCLEAR_DIAGNOSIS",
                 issue_date: str = "", query: str = "") -> dict:
        """调用官方诊断 Agent"""
        adv_id = advertiser_id or self.advertiser_id
        ctx = {"advertiser_id": adv_id}
        if campaign_id:
            ctx["campaign_id"] = campaign_id
        if adgroup_id:
            ctx["adgroup_id"] = adgroup_id
        if issue_type:
            ctx["issue_type"] = issue_type
        if issue_date:
            ctx["issue_date"] = issue_date
        return self._make_call(
            "tiktok_ads_diagnosis_agent",
            {"ctx": ctx, "messages": [{"content": query or "请诊断投放问题并给出优化建议"}]},
            f"投放诊断: {issue_type}",
        )


# ==================== 格式化输出 ====================

def format_status_output(status: dict) -> str:
    lines = [
        "🔌 【MCP连接状态 - 平台关联模式】",
        "━" * 50,
        f"端点地址:  {status.get('endpoint', 'N/A')}",
        f"连接状态:  ✅ 平台关联已就绪",
        f"授权方式:  平台统一 OAuth",
        f"工具映射:  {status.get('tools_count', 0)} 个",
        f"广告主ID:  {'已设置' if status.get('advertiser_id_configured') else '未设置（调用时传入）'}",
        "━" * 50,
    ]
    return "\n".join(lines)


def format_tools_output() -> str:
    lines = [
        f"🛠️  【平台工具映射表】（共 {len(PLATFORM_TOOLS)} 个）",
        "━" * 50,
    ]
    for key, tool in sorted(PLATFORM_TOOLS.items()):
        lines.append(f"  {key:35s} → {tool}")
    lines.append("━" * 50)
    return "\n".join(lines)


def format_report_summary(data_list: list) -> str:
    if not data_list:
        return "无数据"
    total_spend = 0.0
    total_impressions = 0
    total_clicks = 0
    total_conversions = 0
    for item in data_list:
        metrics = item.get("metrics", item) if isinstance(item, dict) else {}
        total_spend += float(metrics.get("spend", 0) or 0)
        total_impressions += int(metrics.get("impressions", 0) or 0)
        total_clicks += int(metrics.get("clicks", 0) or 0)
        total_conversions += int(metrics.get("conversions", 0) or 0)
    ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
    cpc = (total_spend / total_clicks) if total_clicks > 0 else 0
    cpa = (total_spend / total_conversions) if total_conversions > 0 else 0
    cvr = (total_conversions / total_clicks * 100) if total_clicks > 0 else 0
    return f"""
📊 报表数据摘要
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
总花费:        ${total_spend:,.2f}
总曝光:        {total_impressions:,}
总点击:        {total_clicks:,}
总转化:        {total_conversions:,}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CTR:           {ctr:.2f}%
CPC:           ${cpc:.2f}
CPA:           ${cpa:.2f}
CVR:           {cvr:.2f}%
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
数据条数:      {len(data_list)}
"""


def main():
    parser = argparse.ArgumentParser(
        description="TikTok Ads MCP 分析客户端（平台关联模式）",
        epilog="⚠️  平台关联模式：授权由平台统一管理，无需配置文件"
    )
    parser.add_argument("--action", required=True,
                        choices=["status", "tools", "accounts", "report", "diagnose"],
                        help="操作类型")
    parser.add_argument("--advertiser-id", default="", help="广告主 ID")
    parser.add_argument("--start-date", help="开始日期 YYYY-MM-DD")
    parser.add_argument("--end-date", help="结束日期 YYYY-MM-DD")
    parser.add_argument("--data-level", default="AUCTION_ADVERTISER",
                        choices=["AUCTION_ADVERTISER", "AUCTION_CAMPAIGN",
                                 "AUCTION_ADGROUP", "AUCTION_AD"],
                        help="数据层级")
    parser.add_argument("--report-type", default="BASIC",
                        choices=["BASIC", "AUDIENCE", "PLAYABLE_MATERIAL",
                                 "CATALOG", "BC", "TT_SHOP"],
                        help="报表类型")
    parser.add_argument("--dimensions", default="",
                        help="维度列表，逗号分隔，如 stat_time_day,adgroup_id")
    parser.add_argument("--metrics", default="",
                        help="指标列表，逗号分隔，如 spend,impressions,clicks")
    parser.add_argument("--issue-type", default="UNCLEAR_DIAGNOSIS",
                        help="诊断类型: NO_SPENDING/LOW_SPENDING/HIGH_CPA/CREATIVE_FATIGUE")
    parser.add_argument("--query", default="", help="诊断查询文本")
    parser.add_argument("--output", help="输出文件路径（JSON格式）")
    parser.add_argument("--summary", action="store_true", help="只输出摘要说明")

    args = parser.parse_args()
    client = TikTokAdsMCPClient(advertiser_id=args.advertiser_id)

    if args.action == "status":
        print(format_status_output(client.get_connection_status()))

    elif args.action == "tools":
        print(format_tools_output())

    elif args.action == "accounts":
        call = client.list_accounts()
        print("📋 账户查询指令（平台关联模式）")
        print("━" * 50)
        print(f"平台工具: {call['platform_tool']}")
        print(f"描述: {call['description']}")
        print("━" * 50)
        print("\n💡 Agent 将调用此平台工具获取已授权账户列表")
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(call, f, ensure_ascii=False, indent=2)

    elif args.action == "report":
        if not args.start_date or not args.end_date:
            print("❌ report 操作需要 --start-date 和 --end-date", file=sys.stderr)
            sys.exit(1)
        if not args.advertiser_id:
            print("❌ report 操作需要 --advertiser-id", file=sys.stderr)
            sys.exit(1)

        dimensions = [d.strip() for d in args.dimensions.split(",") if d.strip()] if args.dimensions else None
        metrics = [m.strip() for m in args.metrics.split(",") if m.strip()] if args.metrics else None
        call = client.get_report(
            advertiser_id=args.advertiser_id,
            start_date=args.start_date,
            end_date=args.end_date,
            data_level=args.data_level,
            dimensions=dimensions,
            metrics=metrics,
            report_type=args.report_type,
        )
        print("📊 报表查询指令（平台关联模式）")
        print("━" * 50)
        print(f"平台工具: {call['platform_tool']}")
        print(f"描述: {call['description']}")
        print(f"参数摘要: data_level={args.data_level}, report_type={args.report_type}")
        print(f"  时间范围: {args.start_date} ~ {args.end_date}")
        print("━" * 50)
        print("\n💡 Agent 将调用此平台工具获取报表数据")
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(call, f, ensure_ascii=False, indent=2)
            print(f"\n📄 指令已保存到: {args.output}")
        else:
            print("\n--- CALL JSON ---")
            print(json.dumps(call, ensure_ascii=False, indent=2))

    elif args.action == "diagnose":
        if not args.advertiser_id:
            print("❌ diagnose 操作需要 --advertiser-id", file=sys.stderr)
            sys.exit(1)
        call = client.diagnose(
            advertiser_id=args.advertiser_id,
            issue_type=args.issue_type,
            query=args.query,
        )
        print("🩺 投放诊断指令（平台关联模式）")
        print("━" * 50)
        print(f"平台工具: {call['platform_tool']}")
        print(f"描述: {call['description']}")
        print("━" * 50)
        print("\n💡 Agent 将调用官方诊断 Agent 进行分析")
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(call, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
