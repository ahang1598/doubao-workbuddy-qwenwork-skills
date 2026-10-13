#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TikTok Ads MCP 客户端（平台关联模式）

⚠️  本模块已改造为「平台关联模式」：
- 不再自行管理 OAuth Token / config.json
- 不再直接发 HTTP 请求到 TikTok MCP 端点
- 所有方法返回「平台工具调用指令」，由 Agent 调用 mcp__tiktok_business__* 工具执行
- 授权由平台统一管理，安全可靠

使用方式：
  client = TikTokAdsMCPClient(advertiser_id="xxx")
  call = client.create_campaign(...)
  # call = {"platform_tool": "mcp__tiktok_business__smart_plus_campaign_create",
  #         "arguments": {...}, "description": "..."}
  # Agent 读取后调用对应平台工具
"""

import json
import time


class TikTokMCPError(Exception):
    """MCP 错误异常"""

    def __init__(self, code, message, response=None):
        self.code = code
        self.message = message
        self.response = response
        super().__init__(f"MCP Error [{code}]: {message}")


# ==================== 平台工具名映射 ====================
# 内部方法名 → 平台已绑定的 MCP 工具名
# 直接注册的工具使用 mcp__tiktok_business__ 前缀
# 未直接注册的传统拍卖广告工具通过 tool_execute 动态调度
PLATFORM_TOOL_MAP = {
    # --- 账户 / BC ---
    "auth_advertiser_get": "mcp__tiktok_business__auth_advertiser_get",
    "advertiser_info_get": "mcp__tiktok_business__advertiser_info_get",
    "bc_get": "mcp__tiktok_business__bc_get",

    # --- 报表 / 诊断 ---
    "report_integrated_get": "mcp__tiktok_business__report_integrated_get",
    "tiktok_ads_diagnosis_agent": "mcp__tiktok_business__tiktok_ads_diagnosis_agent",

    # --- Smart+ Campaign（直接注册） ---
    "smart_plus_campaign_create": "mcp__tiktok_business__smart_plus_campaign_create",
    "smart_plus_campaign_get": "mcp__tiktok_business__smart_plus_campaign_get",
    "smart_plus_campaign_update": "mcp__tiktok_business__smart_plus_campaign_update",
    "smart_plus_campaign_status_update": "mcp__tiktok_business__smart_plus_campaign_status_update",

    # --- Smart+ Ad Group（直接注册） ---
    "smart_plus_adgroup_create": "mcp__tiktok_business__smart_plus_adgroup_create",
    "smart_plus_adgroup_get": "mcp__tiktok_business__smart_plus_adgroup_get",
    "smart_plus_adgroup_update": "mcp__tiktok_business__smart_plus_adgroup_update",
    "smart_plus_adgroup_status_update": "mcp__tiktok_business__smart_plus_adgroup_status_update",
    "smart_plus_adgroup_budget_update": "mcp__tiktok_business__smart_plus_adgroup_budget_update",

    # --- Smart+ Ad（直接注册） ---
    "smart_plus_ad_create": "mcp__tiktok_business__smart_plus_ad_create",
    "smart_plus_ad_get": "mcp__tiktok_business__smart_plus_ad_get",
    "smart_plus_ad_update": "mcp__tiktok_business__smart_plus_ad_update",
    "smart_plus_ad_status_update": "mcp__tiktok_business__smart_plus_ad_status_update",

    # --- 动态调度器（用于未直接注册的传统拍卖广告工具） ---
    "tool_list": "mcp__tiktok_business__tool_list",
    "tool_get": "mcp__tiktok_business__tool_get",
    "tool_execute": "mcp__tiktok_business__tool_execute",

    # --- 素材 / 受众 / 应用等（直接注册） ---
    "file_image_ad_search": "mcp__tiktok_business__file_image_ad_search",
    "file_music_get": "mcp__tiktok_business__file_music_get",
    "identity_get": "mcp__tiktok_business__identity_get",
    "identity_video_get": "mcp__tiktok_business__identity_video_get",
    "app_list_get": "mcp__tiktok_business__app_list_get",
    "app_info_get": "mcp__tiktok_business__app_info_get",
    "pixel_list_get": "mcp__tiktok_business__pixel_list_get",
    "dmp_custom_audience_list_get": "mcp__tiktok_business__dmp_custom_audience_list_get",
    "dmp_saved_audience_list_get": "mcp__tiktok_business__dmp_saved_audience_list_get",
    "catalog_get": "mcp__tiktok_business__catalog_get",
    "creative_portfolio_list_get": "mcp__tiktok_business__creative_portfolio_list_get",
}


class TikTokAdsMCPClient:
    """TikTok Ads MCP 客户端（平台关联模式）

    ⚠️  平台关联模式说明：
    - 不需要 config.json，不需要 OAuth Token
    - 所有方法返回平台工具调用指令，由 Agent 执行
    - 授权由平台统一管理
    """

    def __init__(self, advertiser_id: str = "", mcp_endpoint: str = ""):
        """
        初始化客户端（平台关联模式）

        Args:
            advertiser_id: 广告主 ID（可选，调用时可覆盖）
            mcp_endpoint: 保留参数，平台模式下不使用
        """
        self.advertiser_id = advertiser_id
        self.mcp_endpoint = mcp_endpoint or "platform-bound"
        self.last_request_id = ""
        self._request_id = 0
        self._tools_cache = None
        # 收集多步调用计划
        self._plan_steps = []

    @classmethod
    def from_config(cls, config_path: str = None):
        """
        从配置创建客户端（平台关联模式下的兼容方法）

        ⚠️  平台关联模式不再需要配置文件。
        此方法保留仅为向后兼容，返回无配置的客户端实例。
        """
        return cls(advertiser_id="")

    def _get_next_request_id(self):
        self._request_id += 1
        return self._request_id

    def _make_call(self, internal_tool: str, arguments: dict,
                   description: str = "") -> dict:
        """
        生成平台工具调用指令（核心方法，替代原 _mcp_request）

        Args:
            internal_tool: 内部工具名（用于查映射表）
            arguments: 调用参数
            description: 操作描述

        Returns:
            调用指令 dict，Agent 读取后调用对应平台工具
        """
        platform_tool = PLATFORM_TOOL_MAP.get(internal_tool, internal_tool)
        # 如果映射表中没有，且不是 tool_execute，标记为需要动态调度
        if internal_tool not in PLATFORM_TOOL_MAP and not internal_tool.startswith("mcp__"):
            platform_tool = PLATFORM_TOOL_MAP["tool_execute"]
            arguments = {"tool_name": internal_tool, "arguments": arguments}

        self.last_request_id = str(self._get_next_request_id())

        call = {
            "platform_tool": platform_tool,
            "arguments": arguments,
            "description": description or internal_tool,
            "request_id": self.last_request_id,
            "mode": "platform",
        }
        return call

    def list_tools(self) -> dict:
        """列出平台可用的 MCP 工具（通过动态调度器）"""
        return self._make_call("tool_list", {}, "列出平台可用工具")

    def call_tool(self, tool_name: str, arguments: dict = None) -> dict:
        """通用工具调用（通过动态调度器 tool_execute）"""
        return self._make_call(
            "tool_execute",
            {"tool_name": tool_name, "arguments": arguments or {}},
            f"动态调用: {tool_name}",
        )

    def get_connection_status(self) -> dict:
        """获取连接状态（平台关联模式）"""
        return {
            "endpoint": "platform-bound (mcp__tiktok_business__*)",
            "configured": True,
            "authorized": True,
            "auth_mode": "platform_oauth",
            "advertiser_id_configured": bool(self.advertiser_id),
            "tools_count": len(PLATFORM_TOOL_MAP),
            "note": "平台关联模式，授权由平台统一管理",
        }

    # ==================== Campaign 相关 ====================

    def create_campaign(self, campaign_name: str, objective_type: str,
                        budget_mode: str, budget: float,
                        operation_status: str = "DISABLE") -> dict:
        """创建广告系列（平台关联模式）

        优先使用 Smart+ campaign_create；如需传统拍卖广告，
        Agent 可根据返回指令改用 tool_execute 动态调用 campaign_create。
        """
        arguments = {
            "advertiser_id": self.advertiser_id,
            "campaign_name": campaign_name,
            "objective_type": objective_type,
            "budget_mode": budget_mode,
            "budget": budget,
            "operation_status": operation_status,
        }
        return self._make_call(
            "smart_plus_campaign_create", arguments,
            f"创建 Campaign: {campaign_name}",
        )

    def get_campaign(self, campaign_id: str) -> dict:
        """获取广告系列信息"""
        arguments = {
            "advertiser_id": self.advertiser_id,
            "filtering": {"campaign_ids": [campaign_id]},
        }
        return self._make_call(
            "smart_plus_campaign_get", arguments,
            f"查询 Campaign: {campaign_id}",
        )

    def update_campaign_status(self, campaign_id: str, operation_status: str) -> dict:
        """更新广告系列状态"""
        arguments = {
            "advertiser_id": self.advertiser_id,
            "campaign_ids": [campaign_id],
            "operation_status": operation_status,
        }
        return self._make_call(
            "smart_plus_campaign_status_update", arguments,
            f"更新 Campaign 状态: {campaign_id} → {operation_status}",
        )

    def batch_update_campaign_status(self, campaign_ids: list, operation_status: str) -> dict:
        """批量更新广告系列状态"""
        if not campaign_ids:
            return {"success": False, "error": "campaign_ids 不能为空"}
        arguments = {
            "advertiser_id": self.advertiser_id,
            "campaign_ids": campaign_ids,
            "operation_status": operation_status,
        }
        return self._make_call(
            "smart_plus_campaign_status_update", arguments,
            f"批量更新 Campaign 状态 ({len(campaign_ids)}个) → {operation_status}",
        )

    def update_campaign(self, campaign_id: str, budget: float = None,
                        campaign_name: str = None, budget_mode: str = None) -> dict:
        """更新广告系列属性"""
        arguments = {
            "advertiser_id": self.advertiser_id,
            "campaign_id": campaign_id,
        }
        if budget is not None:
            arguments["budget"] = budget
        if campaign_name is not None:
            arguments["campaign_name"] = campaign_name
        if budget_mode is not None:
            arguments["budget_mode"] = budget_mode
        return self._make_call(
            "smart_plus_campaign_update", arguments,
            f"更新 Campaign: {campaign_id}",
        )

    def list_campaigns(self, filtering: dict = None, page: int = 1,
                       page_size: int = 100) -> dict:
        """查询广告系列列表"""
        arguments = {
            "advertiser_id": self.advertiser_id,
            "page": page,
            "page_size": page_size,
        }
        if filtering:
            arguments["filtering"] = filtering
        return self._make_call(
            "smart_plus_campaign_get", arguments,
            "查询 Campaign 列表",
        )

    # ==================== Ad Group 相关 ====================

    def create_adgroup(self, adgroup_name: str, campaign_id: str,
                       optimization_goal: str, billing_event: str,
                       bid_type: str, bid_amount: float = 0,
                       targeting: dict = None, placement: dict = None,
                       schedule: dict = None) -> dict:
        """创建广告组"""
        arguments = {
            "advertiser_id": self.advertiser_id,
            "campaign_id": campaign_id,
            "adgroup_name": adgroup_name,
            "optimization_goal": optimization_goal,
            "billing_event": billing_event,
            "bid_type": bid_type,
            "operation_status": "DISABLE",
        }
        if bid_amount and bid_type != "BID_TYPE_NO_BID":
            arguments["bid_price"] = bid_amount
        if targeting:
            arguments["targeting_spec"] = targeting
        if placement:
            arguments.update(placement)
        if schedule:
            arguments.update(schedule)
        return self._make_call(
            "smart_plus_adgroup_create", arguments,
            f"创建 Ad Group: {adgroup_name}",
        )

    def update_adgroup_status(self, adgroup_id: str, operation_status: str) -> dict:
        """更新广告组状态"""
        arguments = {
            "advertiser_id": self.advertiser_id,
            "adgroup_ids": [adgroup_id],
            "operation_status": operation_status,
        }
        return self._make_call(
            "smart_plus_adgroup_status_update", arguments,
            f"更新 Ad Group 状态: {adgroup_id} → {operation_status}",
        )

    def batch_update_adgroup_status(self, adgroup_ids: list, operation_status: str) -> dict:
        """批量更新广告组状态"""
        if not adgroup_ids:
            return {"success": False, "error": "adgroup_ids 不能为空"}
        arguments = {
            "advertiser_id": self.advertiser_id,
            "adgroup_ids": adgroup_ids,
            "operation_status": operation_status,
        }
        return self._make_call(
            "smart_plus_adgroup_status_update", arguments,
            f"批量更新 Ad Group 状态 ({len(adgroup_ids)}个) → {operation_status}",
        )

    def update_adgroup(self, adgroup_id: str, budget: float = None,
                       bid_amount: float = None, bid_type: str = None,
                       adgroup_name: str = None, schedule_start_time: str = None,
                       schedule_end_time: str = None, targeting: dict = None,
                       placement: dict = None, operation_status: str = None) -> dict:
        """更新广告组属性"""
        arguments = {
            "advertiser_id": self.advertiser_id,
            "adgroup_id": adgroup_id,
        }
        if budget is not None:
            arguments["budget"] = budget
        if bid_amount is not None:
            arguments["bid_price"] = bid_amount
        if bid_type is not None:
            arguments["bid_type"] = bid_type
        if adgroup_name is not None:
            arguments["adgroup_name"] = adgroup_name
        if schedule_start_time is not None:
            arguments["schedule_start_time"] = schedule_start_time
        if schedule_end_time is not None:
            arguments["schedule_end_time"] = schedule_end_time
        if targeting is not None:
            arguments["targeting_spec"] = targeting
        if placement is not None:
            arguments.update(placement)
        if operation_status is not None:
            arguments["operation_status"] = operation_status
        return self._make_call(
            "smart_plus_adgroup_update", arguments,
            f"更新 Ad Group: {adgroup_id}",
        )

    def update_adgroup_budget(self, adgroup_id: str, budget: float,
                              budget_mode: str = None) -> dict:
        """更新广告组预算（专用预算更新工具）"""
        arguments = {
            "advertiser_id": self.advertiser_id,
            "adgroup_ids": [adgroup_id],
            "budget": budget,
        }
        if budget_mode:
            arguments["budget_mode"] = budget_mode
        return self._make_call(
            "smart_plus_adgroup_budget_update", arguments,
            f"更新 Ad Group 预算: {adgroup_id} → {budget}",
        )

    def list_adgroups(self, campaign_id: str = "", filtering: dict = None,
                      page: int = 1, page_size: int = 100) -> dict:
        """查询广告组列表"""
        arguments = {
            "advertiser_id": self.advertiser_id,
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
        return self._make_call(
            "smart_plus_adgroup_get", arguments,
            "查询 Ad Group 列表",
        )

    # ==================== Ad 相关 ====================

    def create_ad(self, ad_name: str, adgroup_id: str, ad_format: str,
                  video_id: str = "", image_id: str = "", ad_text: str = "",
                  call_to_action: str = "", landing_page_url: str = "") -> dict:
        """创建广告"""
        arguments = {
            "advertiser_id": self.advertiser_id,
            "adgroup_id": adgroup_id,
            "ad_name": ad_name,
            "operation_status": "DISABLE",
        }
        # 构建 creative_list
        creative_info = {"ad_format": ad_format}
        if video_id:
            creative_info["video_info"] = {"video_id": video_id}
        if image_id:
            creative_info["image_info"] = [{"web_uri": image_id}]
        arguments["creative_list"] = [{"creative_info": creative_info}]

        if ad_text:
            arguments["ad_text_list"] = [{"ad_text": ad_text}]
        if call_to_action:
            arguments["call_to_action_list"] = [{"call_to_action": call_to_action}]
        if landing_page_url:
            arguments["landing_page_url_list"] = [{"landing_page_url": landing_page_url}]

        return self._make_call(
            "smart_plus_ad_create", arguments,
            f"创建 Ad: {ad_name}",
        )

    def update_ad_status(self, ad_id: str, operation_status: str) -> dict:
        """更新广告状态"""
        arguments = {
            "advertiser_id": self.advertiser_id,
            "ad_ids": [ad_id],
            "operation_status": operation_status,
        }
        return self._make_call(
            "smart_plus_ad_status_update", arguments,
            f"更新 Ad 状态: {ad_id} → {operation_status}",
        )

    def batch_update_ad_status(self, ad_ids: list, operation_status: str) -> dict:
        """批量更新广告状态"""
        if not ad_ids:
            return {"success": False, "error": "ad_ids 不能为空"}
        arguments = {
            "advertiser_id": self.advertiser_id,
            "ad_ids": ad_ids,
            "operation_status": operation_status,
        }
        return self._make_call(
            "smart_plus_ad_status_update", arguments,
            f"批量更新 Ad 状态 ({len(ad_ids)}个) → {operation_status}",
        )

    def update_ad(self, ad_id: str, ad_name: str = None, ad_text: str = None,
                  call_to_action: str = None, operation_status: str = None,
                  landing_page_url: str = None, display_name: str = None) -> dict:
        """更新广告属性"""
        arguments = {
            "advertiser_id": self.advertiser_id,
            "smart_plus_ad_id": ad_id,
        }
        if ad_name is not None:
            arguments["ad_name"] = ad_name
        if ad_text is not None:
            arguments["ad_text_list"] = [{"ad_text": ad_text}]
        if call_to_action is not None:
            arguments["call_to_action_list"] = [{"call_to_action": call_to_action}]
        if operation_status is not None:
            arguments["operation_status"] = operation_status
        if landing_page_url is not None:
            arguments["landing_page_url_list"] = [{"landing_page_url": landing_page_url}]
        return self._make_call(
            "smart_plus_ad_update", arguments,
            f"更新 Ad: {ad_id}",
        )

    def list_ads(self, adgroup_id: str = "", filtering: dict = None,
                 page: int = 1, page_size: int = 100) -> dict:
        """查询广告列表"""
        arguments = {
            "advertiser_id": self.advertiser_id,
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
        return self._make_call(
            "smart_plus_ad_get", arguments,
            "查询 Ad 列表",
        )

    # ==================== 报表 / 诊断 ====================

    def get_report(self, advertiser_id: str = "", start_date: str = "",
                   end_date: str = "", data_level: str = "AUCTION_ADVERTISER",
                   dimensions: list = None, metrics: list = None,
                   report_type: str = "BASIC", filtering: list = None) -> dict:
        """获取报表数据（平台关联模式）"""
        adv_id = advertiser_id or self.advertiser_id
        if dimensions is None:
            dimensions = ["stat_time_day"]
        if metrics is None:
            metrics = ["spend", "impressions", "clicks", "ctr", "cpc", "cpm",
                       "conversions", "cost_per_conversion", "conversion_rate"]
        arguments = {
            "advertiser_id": adv_id,
            "start_date": start_date,
            "end_date": end_date,
            "data_level": data_level,
            "dimensions": dimensions,
            "metrics": metrics,
            "report_type": report_type,
        }
        if filtering:
            arguments["filtering"] = filtering
        return self._make_call(
            "report_integrated_get", arguments,
            f"查询报表: {data_level} [{start_date}~{end_date}]",
        )

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
        arguments = {
            "ctx": ctx,
            "messages": [{"content": query or "请诊断该广告的投放问题并给出优化建议"}],
        }
        return self._make_call(
            "tiktok_ads_diagnosis_agent", arguments,
            f"投放诊断: {issue_type}",
        )

    # ==================== 账户查询 ====================

    def list_accounts(self) -> dict:
        """获取已授权的广告账户列表"""
        return self._make_call(
            "auth_advertiser_get", {},
            "查询已授权广告账户",
        )

    # ==================== 辅助方法 ====================

    @staticmethod
    def normalize_result(result: dict) -> dict:
        """标准化平台工具返回结果"""
        if isinstance(result, dict):
            if "code" in result:
                return {
                    "code": result.get("code", -1),
                    "message": result.get("message", ""),
                    "data": result.get("data", {}),
                    "success": result.get("code", -1) == 0,
                }
            if "content" in result:
                content = result["content"]
                if isinstance(content, list) and len(content) > 0:
                    text = content[0].get("text", "{}")
                    try:
                        data = json.loads(text)
                        return {
                            "code": data.get("code", -1),
                            "message": data.get("message", ""),
                            "data": data.get("data", {}),
                            "success": data.get("code", -1) == 0,
                        }
                    except json.JSONDecodeError:
                        pass
            return {"code": 0, "message": "success", "data": result, "success": True}
        return {"code": -1, "message": "未知返回格式", "data": {"raw": result}, "success": False}


def test_connection_from_config() -> dict:
    """测试连接（平台关联模式）"""
    client = TikTokAdsMCPClient()
    status = client.get_connection_status()
    return {
        "code": 0,
        "message": "平台关联模式已就绪",
        "data": status,
        "success": True,
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description="TikTok Ads MCP 客户端（平台关联模式）",
        epilog="⚠️  平台关联模式：授权由平台统一管理，无需配置文件"
    )
    parser.add_argument("--status", action="store_true", help="查看连接状态")
    parser.add_argument("--tools", action="store_true", help="列出平台可用工具映射")
    parser.add_argument("--advertiser-id", type=str, default="", help="广告主 ID")
    args = parser.parse_args()

    if args.status:
        client = TikTokAdsMCPClient(advertiser_id=args.advertiser_id)
        status = client.get_connection_status()
        print("🔌 【MCP连接状态 - 平台关联模式】")
        print("━" * 50)
        print(f"端点:      {status['endpoint']}")
        print(f"授权方式:  平台统一 OAuth")
        print(f"已配置:    {'✅' if status['configured'] else '❌'}")
        print(f"已授权:    {'✅' if status['authorized'] else '❌'}")
        print(f"工具映射:  {status['tools_count']} 个")
        print(f"广告主ID:  {'已设置' if status['advertiser_id_configured'] else '未设置（调用时传入）'}")
        print("━" * 50)
    elif args.tools:
        print("🛠️  平台工具映射表（共 {} 个）".format(len(PLATFORM_TOOL_MAP)))
        print("━" * 50)
        for internal, platform in sorted(PLATFORM_TOOL_MAP.items()):
            print(f"  {internal:45s} → {platform}")
        print("━" * 50)
    else:
        parser.print_help()
