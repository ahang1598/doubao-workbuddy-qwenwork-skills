#!/usr/bin/env python3
"""查询待办汇总（1.1）：脚本内直接调用 get_org_detail + get_pending_project_list，
按 alert-info-fetcher 规范**逐字符组装** title/subtitle，返回给调用方（AI 无需猜字段）。

输出（扁平 JSON）：
  { "title": "...", "subtitle": "...",
    "kind": "cert" | "record" | "both" | "none",
    "has_pending_review": true | false }

kind 含义：cert=仅证件待办 / record=仅备案号待办 / both=两类都有待办（调用方须弹窗二选一）
        / none=无待办。优先级：证件 > 备案号，both 时 subtitle 取最紧迫证件文案。
has_pending_review：证件审批中守卫，true→证件入口暂不可用（不影响备案号更新）。
接口不可用即上抛错误 JSON，绝不降级。

用法：python query_todo_summary.py
依赖：skills/_common/mcp_client.py（经 __file__ 相对路径自动导入）

==================================================================
契约（维护者必读 —— 原 MCP 工具调用规范已并入此处作为唯一真相源）
==================================================================
【入参铁律】
- 两工具都必须传 caller_expert_id="alert-expert"（真实 inputSchema 要求必填，遗漏即被参数校验拒绝）。
  org_no 由 MCP token 注入，无需传。
- get_pending_project_list 必传 warning_types=[1]（备案号即将过期），空数组后端拒绝。
  ⚠️ inputSchema 常弱类型/失准（repeated 被标成无 items 的 array、int32 变 string、必填未暴露），
  改参时**禁止仅凭 inputSchema 猜测**，以本脚本硬编码为准。
- 查询计数固定 page=1, page_size=1：只要总数 pending_stop_project_count + 首条示例项，无需拉全。

【get_org_detail 字段契约】
- institution_type: 1=公募 / 2=非公募 / 3=专项基金，与 org.type_of_organization 同义（输出 org 字段优先用后者，失败回退本字段）。
- cert_warning: object|null，⭐核心字段。非超管调用时为 nil → 视为"无证件预警"，**不报错、不暗示权限限制**。
  items[] 顺序后端不保证，本脚本按 remaining_day 升序（已过期 -1 排最前）。
  items[].remaining_day: >0 未到期；-1 已过期。
  items[].cert_type 联合 institution_type 判定标签（见 _cert_type_label，不得自行硬编码）。
  ⛔ 不得用老字段 detailed.certificate_validity_day 等判断预警，必须以 cert_warning 为准。
- has_pending_review: bool，⭐证件更新入口守卫。true→审批中，禁调 update_org_cert；false→正常。
  **不影响**备案号更新。

【get_pending_project_list 字段契约】
- pending_stop_project_count: 项目数（跨页一致），**不是预警条目数**。
- fund_raising_program_id: ⭐ 用于 update_org_record_number 的 id 入参。
- fund_raising_program_no: ⭐ 用于 no 一致性校验基准。
- fund_raising_program_audit_status: 1=已通过 / 2=审批中 / 3=已驳回；===2 审批中禁提（项目级守卫）。
- warns[].warning_id: 预警条目主键，**不是业务主键，严禁作为 update_org_record_number.id**
  （v2 已从 warns[].id 迁移到项目级 fund_raising_program_id）。
  ⛔ 不得用 warns.length 加总代替 pending_stop_project_count（跨页会漏）。
  ⛔ 不得依赖保留字段 warning_type_desc / warning_prompt / warning_solution（当前恒空）。
- 本接口 days>=0 未到期，**无 -1 的已过期概念**（与 cert_warning.remaining_day 语义不同）。
==================================================================
"""
import json
import os
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "_common")))
from mcp_client import call_mcp, get_user_and_org_info, CALLER_EXPERT_ID, mask, _sanitize, MCPAuthError
from observe_bootstrap import observe_entrypoint


def _cert_type_label(cert_type, institution_type):
    if cert_type == 1:
        return "社会组织法人登记证书"
    if cert_type == 2:
        return "慈善组织公开募捐资格证书"
    if cert_type == 3:
        if institution_type == 3:
            return "专项基金负责人身份证"
        return "法人身份证"
    return f"未知证件({cert_type})"


def _build_cert_list(cert_warning, institution_type):
    items = (cert_warning or {}).get("items") or []
    out = []
    for it in items:
        rd = it.get("remaining_day")
        expired = (rd == -1)
        out.append({
            "cert_type_code": it.get("cert_type"),
            "cert_type_label": _cert_type_label(it.get("cert_type"), institution_type),
            "expire_date": it.get("end_date"),
            "remaining_day": rd,
            "expired": expired,
        })
    # 排序：(expired? -1 : remaining_day) 升序，已过期永远最前
    out.sort(key=lambda x: (-1 if x["expired"] else x["remaining_day"]))
    return out


def _main():
    import argparse
    ap = argparse.ArgumentParser()
    args = ap.parse_args()
    try:
        org = get_user_and_org_info()
        if org.get("is_error"):
            org_info = {"org_no": "", "org_name": "", "type_of_organization": None}
        else:
            org_info = dict(org)  # 完整机构字段透传：org_no/org_name/type_of_organization/affili_pub_org*/account_id/name
        detail = call_mcp("get_org_detail", {}, 30)
        ddata = detail["data"] or {}
        proj = call_mcp("get_pending_project_list",
                        {"page": 1, "page_size": 1, "warning_types": [1]}, 30)
        pdata = proj["data"] or {}

        institution_type = ddata.get("institution_type")
        # 机构类型回退：get_user_and_org_info 失败时用 get_org_detail.institution_type 补齐（两者等价）
        if org_info.get("type_of_organization") is None:
            org_info["type_of_organization"] = institution_type
        cert_warning = ddata.get("cert_warning")
        has_pending_review = bool(ddata.get("has_pending_review"))

        cert_list = _build_cert_list(cert_warning, institution_type)
        cert_count = len(cert_list)

        pending_stop_project_count = pdata.get("pending_stop_project_count", 0) or 0
        projects = pdata.get("projects") or []
        record_count = pending_stop_project_count

        # --- 判定 kind（cert 优先；两者都有 → both）---
        cert_has = cert_count > 0
        record_has = bool(record_count and projects)

        if cert_has:
            top = cert_list[0]
            if has_pending_review:
                subtitle = "当前机构信息有申请单待审批, 审批完成后才能提交证件更新。"
            elif top["expired"]:
                subtitle = f"{top['cert_type_label']}已过期, 请尽快更新证件, 我来协助你更新"
            else:
                subtitle = f"{top['cert_type_label']}在 {top['remaining_day']} 天后到期, 请尽快更新证件, 我来协助你更新"
            title = "证件更新"
        elif record_has:
            p0 = projects[0]
            project_no = p0.get("project_no", "")
            project_name = p0.get("project_name", "")
            pending_stop_days = p0.get("pending_stop_days", 0) or 0
            subtitle = f"{project_no} {project_name} 的备案号在 {pending_stop_days} 天后到期"
            title = "备案号更新"
        else:
            title = ""
            subtitle = ""

        if cert_has and record_has:
            kind = "both"
        elif cert_has:
            kind = "cert"
        elif record_has:
            kind = "record"
        else:
            kind = "none"

        print(json.dumps({"title": title, "subtitle": subtitle,
                          "kind": kind, "has_pending_review": has_pending_review,
                          "org": org_info},
                         ensure_ascii=False))
    except Exception as e:  # noqa: BLE001
        need_refresh = isinstance(e, MCPAuthError)
        print(json.dumps({"success": False,
                          "error_code": "auth_failed" if need_refresh else "mcp_error",
                          "message": f"查询待办汇总失败: {_sanitize(str(e))}",
                          "need_refresh": need_refresh}, ensure_ascii=False))
        sys.exit(1)


def main():
    observe_entrypoint(CALLER_EXPERT_ID, "alert.query_todo_summary", "query_todo_summary", _main)


if __name__ == "__main__":
    main()
