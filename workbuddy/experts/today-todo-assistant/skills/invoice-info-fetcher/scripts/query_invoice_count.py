#!/usr/bin/env python3
"""查询待开票任务计数 + 当前机构信息（invoice-expert 查询计数入口）。

一次调用完成：get_user_and_org_info（机构上下文）+ get_pending_invoice（待开票总数），
输出扁平 JSON 供 agent 组装「机构提示 + title/subtitle 卡片」。

get_pending_invoice 固定参数：order=4、page_index=1、page_size=1（只读 total，不拉明细，
total 语义为「机构维度全量、跨页一致」；严禁 page_size>1，避免拉走非本次任务数据）。

输出（扁平 JSON）：
  {
    "org": {"org_no": "...", "org_name": "..."},
    "total": 0,
    "title": "待开票任务" | "",
    "subtitle": "还有 N 张票据待处理, 我来协助你批量识别并提交" | ""
  }
- total = 0 时 title/subtitle 留空（无待办）。
- org 查询失败时 org_no/org_name 为空，但不阻断计数查询。

错误契约：接口不可用即上抛错误 JSON（need_refresh 标记鉴权失败），绝不降级。

用法：python query_invoice_count.py
依赖：skills/_common/mcp_client.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "_common")))
from mcp_client import call_mcp, get_user_and_org_info, CALLER_EXPERT_ID, _sanitize, MCPAuthError
from observe_bootstrap import observe_entrypoint


def _main():
    try:
        # 机构信息（提示用，失败不阻断计数）
        org = get_user_and_org_info()
        if org.get("is_error"):
            org_info = {"org_no": "", "org_name": ""}
        else:
            org_info = dict(org)  # 完整机构字段透传：org_no/org_name/type_of_organization/affili_pub_org*/account_id/name

        # 待开票计数（page_size=1 只读 total，恒 order=4）
        r = call_mcp("get_pending_invoice", {"order": 4, "page_index": 1, "page_size": 1}, 30)
        if r.get("is_error"):
            raise RuntimeError(r.get("text") or "get_pending_invoice 调用失败")
        data = r.get("data") or {}
        if not isinstance(data, dict):
            data = {}
        # 兼容服务端再包一层 data 的形态
        if "total" not in data and isinstance(data.get("data"), dict):
            data = data["data"]
        total = data.get("total", 0) or 0

        if total > 0:
            title = "待开票任务"
            subtitle = f"还有 {total} 张票据待处理, 我来协助你批量识别并提交"
        else:
            title = ""
            subtitle = ""

        print(json.dumps({
            "org": org_info,
            "total": total,
            "title": title,
            "subtitle": subtitle,
        }, ensure_ascii=False))
    except Exception as e:  # noqa: BLE001
        need_refresh = isinstance(e, MCPAuthError)
        print(json.dumps({"success": False,
                          "error_code": "auth_failed" if need_refresh else "mcp_error",
                          "message": f"查询待开票计数失败: {_sanitize(str(e))}",
                          "need_refresh": need_refresh}, ensure_ascii=False))
        sys.exit(1)


def main():
    observe_entrypoint(CALLER_EXPERT_ID, "invoice.query_invoice_count", "query_invoice_count", _main)


if __name__ == "__main__":
    main()
