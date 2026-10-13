#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
⚡ 批量调控模块（平台关联模式）

⚠️  平台关联模式：本脚本不再直接调用 API，而是：
  1. 做 dry-run 预演计算（预算/出价调整、命名模式应用）
  2. 生成平台工具调用指令列表，由 Agent 调用 mcp__tiktok_business__* 工具执行

核心特性：
- 支持 ID 列表直接指定 或 按条件筛选目标
- 支持绝对值设置 / 百分比增减 / 增减量
- 内置 dry-run 预演，先预览后执行
- 生成平台工具调用指令，授权由平台管理
- 敏感信息自动脱敏

使用方式：
  # 预演：暂停多个 Campaign（生成调用指令）
  python3 batch_control.py status --level campaign --ids "123,456" --op disable

  # 预算增加 20%（需要先查询当前预算，脚本生成查询+更新两步指令）
  python3 batch_control.py budget --level campaign --ids "123,456" --mode percent --value 20

  # 输出 JSON 供 Agent 消费
  BATCH_CONTROL_JSON_OUTPUT=1 python3 batch_control.py ...
"""

import argparse
import json
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tiktok_mcp_client import TikTokAdsMCPClient


# ==================== 常量 ====================
BATCH_STATUS_MAX_IDS = 100
BUDGET_MIN = 1.0
BUDGET_MAX = 1000000.0
BID_MIN = 0.01
BID_MAX = 10000.0
LEVELS = ("campaign", "adgroup", "ad")

STATUS_ACTIONS = {
    "enable": "ENABLE", "disable": "DISABLE", "pause": "DISABLE",
    "delete": "DELETE", "启用": "ENABLE", "暂停": "DISABLE", "删除": "DELETE",
}


# ==================== 工具函数 ====================

def mask_id(entity_id: str) -> str:
    if not entity_id:
        return "N/A"
    s = str(entity_id)
    return s if len(s) <= 4 else f"****{s[-4:]}"


def parse_ids(id_input: str) -> list:
    if not id_input:
        return []
    if isinstance(id_input, list):
        return [str(x).strip() for x in id_input if str(x).strip()]
    id_input = id_input.strip()
    if id_input.startswith("["):
        try:
            return [str(x).strip() for x in json.loads(id_input) if str(x).strip()]
        except json.JSONDecodeError:
            pass
    return [x.strip() for x in re.split(r"[,\s]+", id_input) if x.strip()]


def calc_adjustment(current: float, adjustment: dict) -> float:
    mode = adjustment.get("mode", "set")
    value = float(adjustment.get("value", 0))
    if mode == "set":
        return value
    elif mode == "percent":
        return round(current * (1 + value / 100.0), 2)
    elif mode == "delta":
        return round(current + value, 2)
    raise ValueError(f"不支持的调整模式: {mode}")


def chunk_list(lst: list, size: int) -> list:
    return [lst[i:i + size] for i in range(0, len(lst), size)]


def apply_name_pattern(pattern: str, current_name: str, index: int) -> str:
    if pattern.startswith("prefix:"):
        return f"{pattern[len('prefix:'):]}{current_name}"
    elif pattern.startswith("suffix:"):
        return f"{current_name}{pattern[len('suffix:'):]}"
    elif pattern.startswith("replace:"):
        rule = pattern[len("replace:"):]
        if "->" in rule:
            old, new = rule.split("->", 1)
            return current_name.replace(old, new)
        return current_name
    elif pattern.startswith("sequence:"):
        return f"{pattern[len('sequence:'):]}{index + 1}"
    else:
        return f"{pattern}_{index + 1}" if index > 0 else pattern


# ==================== 平台指令生成器 ====================

class BatchPlatformGenerator:
    """批量调控平台指令生成器（平台关联模式）"""

    def __init__(self, advertiser_id: str = ""):
        self.client = TikTokAdsMCPClient(advertiser_id=advertiser_id)
        self.calls = []       # 平台工具调用指令列表
        self.preview = []     # 预演明细

    def _add_call(self, call: dict, entity_id: str = "", action: str = "",
                  before=None, after=None, note: str = ""):
        self.calls.append({
            "platform_tool": call["platform_tool"],
            "arguments": call["arguments"],
            "description": call["description"],
            "entity_id": entity_id,
            "masked_id": mask_id(entity_id),
            "action": action,
            "before": before,
            "after": after,
            "note": note,
        })

    def _add_preview(self, entity_id: str, action: str, success: bool,
                     message: str = "", before=None, after=None):
        self.preview.append({
            "entity_id": entity_id,
            "masked_id": mask_id(entity_id),
            "action": action,
            "success": success,
            "message": message,
            "before": before,
            "after": after,
        })

    # ---------- 批量状态调控 ----------

    def batch_status(self, level: str, entity_ids: list,
                     operation_status: str) -> dict:
        if level not in LEVELS:
            return {"success": False, "error": f"不支持的层级: {level}"}

        action_desc = f"批量{operation_status.lower()}"
        id_chunks = chunk_list(entity_ids, BATCH_STATUS_MAX_IDS)

        for chunk in id_chunks:
            if level == "campaign":
                call = self.client.batch_update_campaign_status(chunk, operation_status)
            elif level == "adgroup":
                call = self.client.batch_update_adgroup_status(chunk, operation_status)
            else:
                call = self.client.batch_update_ad_status(chunk, operation_status)

            self._add_call(call, ",".join(chunk), action_desc,
                           after=operation_status,
                           note=f"批量操作 {len(chunk)} 个实体")
            for eid in chunk:
                self._add_preview(eid, action_desc, True,
                                  "[预演] 将执行状态变更", after=operation_status)

        return self._build_result(action_desc, level)

    # ---------- 批量预算调整 ----------

    def batch_budget(self, level: str, entity_ids: list,
                     adjustment: dict, current_budgets: dict = None,
                     budget_mode: str = None) -> dict:
        """
        批量预算调整

        Args:
            current_budgets: {id: current_budget} 当前预算映射（Agent 先查询后传入）
                           若为 None 且非 set 模式，会生成查询指令
        """
        if level not in ("campaign", "adgroup"):
            return {"success": False, "error": "预算调整仅支持 campaign 和 adgroup"}

        action_desc = f"批量预算调整({adjustment.get('mode')}={adjustment.get('value')})"
        current_budgets = current_budgets or {}
        need_query = []

        for eid in entity_ids:
            current = current_budgets.get(eid)

            # 需要先查询当前预算
            if current is None and adjustment.get("mode") != "set":
                need_query.append(eid)
                # 生成查询指令
                if level == "campaign":
                    qcall = self.client.get_campaign(eid)
                else:
                    qcall = self.client.list_adgroups(filtering={"adgroup_ids": [eid]})
                self._add_call(qcall, eid, "查询当前预算",
                               note="需要先查询当前预算才能计算百分比/增减量调整")
                self._add_preview(eid, action_desc, False,
                                  "需要先查询当前预算（非绝对值模式）")
                continue

            try:
                if current is not None:
                    new_budget = calc_adjustment(float(current), adjustment)
                else:
                    new_budget = float(adjustment["value"])
            except ValueError as e:
                self._add_preview(eid, action_desc, False, str(e))
                continue

            # 安全边界
            if new_budget < BUDGET_MIN:
                self._add_preview(eid, action_desc, False,
                    f"调整后预算 ${new_budget} 低于最小值 ${BUDGET_MIN}，已跳过",
                    before=current, after=new_budget)
                continue
            if new_budget > BUDGET_MAX:
                self._add_preview(eid, action_desc, False,
                    f"调整后预算 ${new_budget} 超过最大值 ${BUDGET_MAX}，已跳过",
                    before=current, after=new_budget)
                continue

            # 生成更新指令
            if level == "campaign":
                call = self.client.update_campaign(eid, budget=new_budget,
                                                   budget_mode=budget_mode)
            else:
                call = self.client.update_adgroup_budget(eid, new_budget, budget_mode)

            self._add_call(call, eid, action_desc, before=current, after=new_budget)
            self._add_preview(eid, action_desc, True,
                              "[预演] 将执行预算调整", before=current, after=new_budget)

        result = self._build_result(action_desc, level)
        if need_query:
            result["need_query_first"] = need_query
            result["query_note"] = (
                f"有 {len(need_query)} 个实体需要先查询当前预算。"
                "Agent 应先执行查询指令，获取当前预算后重新生成本计划。"
            )
        return result

    # ---------- 批量出价调整 ----------

    def batch_bid(self, adgroup_ids: list, adjustment: dict,
                  current_bids: dict = None, bid_type: str = None) -> dict:
        action_desc = f"批量出价调整({adjustment.get('mode')}={adjustment.get('value')})"
        current_bids = current_bids or {}
        need_query = []

        for eid in adgroup_ids:
            current = current_bids.get(eid)

            if current is None and adjustment.get("mode") != "set":
                need_query.append(eid)
                qcall = self.client.list_adgroups(filtering={"adgroup_ids": [eid]})
                self._add_call(qcall, eid, "查询当前出价",
                               note="需要先查询当前出价才能计算百分比/增减量调整")
                self._add_preview(eid, action_desc, False,
                                  "需要先查询当前出价（非绝对值模式）")
                continue

            try:
                if current is not None and float(current) > 0:
                    new_bid = calc_adjustment(float(current), adjustment)
                else:
                    new_bid = float(adjustment["value"])
            except ValueError as e:
                self._add_preview(eid, action_desc, False, str(e))
                continue

            if new_bid < BID_MIN or new_bid > BID_MAX:
                self._add_preview(eid, action_desc, False,
                    f"调整后出价 ${new_bid} 超出范围 [${BID_MIN}, ${BID_MAX}]，已跳过",
                    before=current, after=new_bid)
                continue

            call = self.client.update_adgroup(eid, bid_amount=new_bid, bid_type=bid_type)
            self._add_call(call, eid, action_desc, before=current, after=new_bid)
            self._add_preview(eid, action_desc, True,
                              "[预演] 将执行出价调整", before=current, after=new_bid)

        result = self._build_result(action_desc, "adgroup")
        if need_query:
            result["need_query_first"] = need_query
        return result

    # ---------- 批量重命名 ----------

    def batch_rename(self, level: str, entity_ids: list,
                     new_name_pattern: str, current_names: dict = None) -> dict:
        action_desc = f"批量重命名({new_name_pattern})"
        current_names = current_names or {}

        for idx, eid in enumerate(entity_ids):
            current_name = current_names.get(eid, "")
            new_name = apply_name_pattern(new_name_pattern, current_name, idx)

            if not new_name:
                self._add_preview(eid, action_desc, False, "生成的新名称为空，跳过")
                continue

            if level == "campaign":
                call = self.client.update_campaign(eid, campaign_name=new_name)
            elif level == "adgroup":
                call = self.client.update_adgroup(eid, adgroup_name=new_name)
            else:
                call = self.client.update_ad(eid, ad_name=new_name)

            self._add_call(call, eid, action_desc, before=current_name, after=new_name)
            self._add_preview(eid, action_desc, True,
                              "[预演] 将执行重命名", before=current_name, after=new_name)

        return self._build_result(action_desc, level)

    # ---------- 条件筛选（生成查询指令） ----------

    def resolve_targets_call(self, level: str, campaign_id: str = "",
                             adgroup_id: str = "", filtering: dict = None) -> dict:
        """生成条件筛选的查询指令（Agent 执行后得到 ID 列表，再传入批量操作）"""
        filtering = filtering or {}
        if level == "campaign":
            call = self.client.list_campaigns(filtering=filtering, page_size=100)
        elif level == "adgroup":
            call = self.client.list_adgroups(campaign_id=campaign_id,
                                             filtering=filtering, page_size=100)
        else:
            call = self.client.list_ads(adgroup_id=adgroup_id,
                                        filtering=filtering, page_size=100)
        return {
            "platform_tool": call["platform_tool"],
            "arguments": call["arguments"],
            "description": call["description"],
            "level": level,
            "note": "Agent 执行此查询后，从返回结果中提取实体 ID 列表，再进行批量操作",
        }

    # ---------- 结果构建 ----------

    def _build_result(self, action: str, level: str) -> dict:
        total = len(self.preview)
        success = sum(1 for p in self.preview if p["success"])
        failed = total - success
        return {
            "mode": "platform",
            "action": action,
            "level": level,
            "summary": {"total": total, "ready": success, "need_query": failed},
            "preview": self.preview,
            "platform_calls": self.calls,
            "execution_guide": (
                "Agent 执行说明：按 platform_calls 顺序调用对应平台工具；"
                "若存在 need_query_first，需先执行查询指令获取当前值，"
                "将结果传入 current_budgets/current_bids 后重新生成本计划。"
            ),
        }


# ==================== 报告格式化 ====================

def format_report(result: dict, verbose: bool = False) -> str:
    lines = []
    action = result.get("action", "未知操作")
    level = result.get("level", "")
    summary = result.get("summary", {})
    preview = result.get("preview", [])
    calls = result.get("platform_calls", [])

    lines.append(f"🔍 【预演模式 - 平台关联】{action}")
    lines.append(f"   层级: {level} | 总计: {summary.get('total', 0)} | "
                 f"可执行: {summary.get('ready', 0)} | 需先查询: {summary.get('need_query', 0)}")
    lines.append(f"   平台调用指令: {len(calls)} 条")
    lines.append("")

    if result.get("need_query_first"):
        lines.append(f"⚠️  有 {len(result['need_query_first'])} 个实体需要先查询当前值")
        lines.append(f"   涉及: {', '.join(mask_id(i) for i in result['need_query_first'])}")
        lines.append("")

    # 失败/跳过
    skipped = [p for p in preview if not p["success"]]
    if skipped:
        lines.append("❌ 跳过/需查询明细:")
        for p in skipped:
            lines.append(f"   - {p['masked_id']}: {p['message']}")
        lines.append("")

    # 可执行预览
    ready = [p for p in preview if p["success"]]
    if ready:
        lines.append("✅ 可执行预览:")
        for p in ready:
            change = ""
            if p.get("before") is not None or p.get("after") is not None:
                change = f" | {p.get('before', 'N/A')} → {p.get('after', 'N/A')}"
            lines.append(f"   - {p['masked_id']}: {p['message']}{change}")
        lines.append("")

    if verbose:
        lines.append("📋 平台工具调用指令:")
        for i, c in enumerate(calls, 1):
            lines.append(f"   {i}. {c['platform_tool']}")
            lines.append(f"      {c['description']}")
        lines.append("")

    lines.append("💡 以上为预演结果。Agent 将调用平台工具执行，无需手动管理 Token。")
    return "\n".join(lines)


# ==================== CLI 入口 ====================

def main():
    parser = argparse.ArgumentParser(
        description="⚡ TikTok Ads 批量调控（平台关联模式）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 预演：暂停多个 Campaign
  python3 batch_control.py status --level campaign --ids "123,456" --op disable

  # 预算增加 20%（非绝对值模式会提示先查询当前预算）
  python3 batch_control.py budget --level campaign --ids "123,456" --mode percent --value 20

  # 批量设置出价为 $5
  python3 batch_control.py bid --ids "123,456" --mode set --value 5

  # 批量重命名（加前缀）
  python3 batch_control.py rename --level ad --ids "123,456" --pattern "prefix:US_"
        """
    )
    subparsers = parser.add_subparsers(dest="command", help="调控操作类型")

    def add_common_args(sub):
        sub.add_argument("--ids", type=str, default="", help="实体 ID 列表，逗号分隔")
        sub.add_argument("--advertiser-id", type=str, default="", help="广告主 ID")
        sub.add_argument("--verbose", "-v", action="store_true", help="显示全部明细")
        sub.add_argument("--current-values", type=str, default="",
                         help='当前值 JSON，如 {"123": 50, "456": 30}（预算/出价调整用）')
        sub.add_argument("--current-names", type=str, default="",
                         help='当前名称 JSON，如 {"123": "旧名"}（重命名用）')

    p_status = subparsers.add_parser("status", help="批量状态调控")
    add_common_args(p_status)
    p_status.add_argument("--level", required=True, choices=LEVELS)
    p_status.add_argument("--op", required=True, help="enable/disable/delete 或中文")

    p_budget = subparsers.add_parser("budget", help="批量预算调整")
    add_common_args(p_budget)
    p_budget.add_argument("--level", required=True, choices=["campaign", "adgroup"])
    p_budget.add_argument("--mode", required=True, choices=["set", "percent", "delta"])
    p_budget.add_argument("--value", required=True, type=float)
    p_budget.add_argument("--budget-mode", default=None)

    p_bid = subparsers.add_parser("bid", help="批量出价调整")
    add_common_args(p_bid)
    p_bid.add_argument("--mode", required=True, choices=["set", "percent", "delta"])
    p_bid.add_argument("--value", required=True, type=float)
    p_bid.add_argument("--bid-type", default=None)

    p_rename = subparsers.add_parser("rename", help="批量重命名")
    add_common_args(p_rename)
    p_rename.add_argument("--level", required=True, choices=LEVELS)
    p_rename.add_argument("--pattern", required=True,
                          help="prefix:X / suffix:X / replace:旧->新 / sequence:X")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    advertiser_id = getattr(args, "advertiser_id", "")
    gen = BatchPlatformGenerator(advertiser_id=advertiser_id)
    entity_ids = parse_ids(args.ids)

    if not entity_ids:
        print("❌ 请通过 --ids 指定目标实体 ID 列表", file=sys.stderr)
        sys.exit(1)

    # 解析当前值
    current_values = {}
    if getattr(args, "current_values", ""):
        try:
            current_values = json.loads(args.current_values)
        except json.JSONDecodeError:
            print("⚠️  current-values JSON 解析失败，将忽略", file=sys.stderr)
    current_names = {}
    if getattr(args, "current_names", ""):
        try:
            current_names = json.loads(args.current_names)
        except json.JSONDecodeError:
            pass

    if args.command == "status":
        op_status = STATUS_ACTIONS.get(args.op.lower(), args.op.upper())
        result = gen.batch_status(args.level, entity_ids, op_status)
    elif args.command == "budget":
        adjustment = {"mode": args.mode, "value": args.value}
        result = gen.batch_budget(args.level, entity_ids, adjustment,
                                  current_budgets=current_values,
                                  budget_mode=args.budget_mode)
    elif args.command == "bid":
        adjustment = {"mode": args.mode, "value": args.value}
        result = gen.batch_bid(entity_ids, adjustment,
                               current_bids=current_values,
                               bid_type=args.bid_type)
    elif args.command == "rename":
        result = gen.batch_rename(args.level, entity_ids, args.pattern,
                                  current_names=current_names)
    else:
        parser.print_help()
        sys.exit(1)

    print(format_report(result, verbose=args.verbose))

    if os.environ.get("BATCH_CONTROL_JSON_OUTPUT"):
        print("\n--- JSON ---")
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
