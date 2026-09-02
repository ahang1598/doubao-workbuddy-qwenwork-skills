#!/usr/bin/env python3
"""查询待办详情（1.2）：脚本内直接调用 get_org_detail / get_pending_project_list，
解析后直接给出哪些 cert 要更新、哪些项目备案号要更新。

--scope 决定查哪种：
  cert   只查证件（get_org_detail）
  record 只查备案号（get_pending_project_list 分页拉全）
  both   两者都查（默认）

输出 JSON：
  { "cert":   {"count":N, "list":[{cert_type_code, cert_type_label, expire_date, remaining_day, expired}], "has_pending_review": bool},
    "record": {"count":N, "updatable_count":N, "list":[{project_no, project_name, pending_stop_days, fund_raising_program_id,
                                    fund_raising_program_no, fund_raising_program_audit_status,
                                    audit_status_label, updatable, warns}], "data_version_ts": ...},
    "todo_cards": [{"title":..., "subtitle":..., "description":...}, ...] }
  record.list 排序：updatable=True（可更新）项目排在前，updatable=False（审批中等）排在后；
  组内按 pending_stop_days 升序（越紧迫越靠前）。updatable_count 为可更新项目数量。
  todo_cards（可点击待办卡片列表，title/subtitle/description 三字段）生成规则：
    - 证件：cert 列表非空 且 has_pending_review=false 时添加 1 张
        title="证件"；subtitle="更新<证件名(只取首项)>(XX天内到期)"（仅首项）；
        description="证件名1(XX天内到期),证件名2(XX天内到期)"（全部项）
    - 备案号：record 列表中每个 updatable=true 的项目各添加 1 张
        title="备案号"；subtitle 与 description 同为
        "更新[项目ID]<项目名>的备案号<备案号ID>(XX天内到期)"
    XX = remaining_day（证件，已过期取"已过期"）/ pending_stop_days（备案号）
    仅返回 --scope 所涵盖的范围内对应的卡片。

接口不可用即上抛错误 JSON，绝不降级。

用法：python query_todo_detail.py [--scope cert|record|both]
依赖：skills/_common/mcp_client.py

==================================================================
契约（维护者必读 —— 原 MCP 工具调用规范已并入此处作为唯一真相源）
==================================================================
【入参铁律】
- 两工具都必须传 caller_expert_id="alert-expert"（真实 inputSchema 要求必填，遗漏即被参数校验拒绝）。
  org_no 由 MCP token 注入，无需传。
- get_pending_project_list 必传 warning_types=[1]（备案号即将过期），空数组后端拒绝。
  ⚠️ inputSchema 常弱类型/失准（repeated 被标成无 items 的 array、int32 变 string、必填未暴露），
  改参时**禁止仅凭 inputSchema 猜测**，以本脚本硬编码为准。
- 备案号完整清单用 page_size=100 分页迭代拉全（直到 projects[] 为空），不能用一次 page_size=1 凑数。

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
  updatable = (status != 2)，即审批中项目不可更新。
- warns[].warning_id: 预警条目主键，**不是业务主键，严禁作为 update_org_record_number.id**
  （v2 已从 warns[].id 迁移到项目级 fund_raising_program_id）。本脚本透传 warns 但**不使用 warning_id 作为业务 ID**。
  ⛔ 不得用 warns.length 加总代替 pending_stop_project_count（跨页会漏）。
  ⛔ 不得依赖保留字段 warning_type_desc / warning_prompt / warning_solution（当前恒空）。
- 本接口 days>=0 未到期，**无 -1 的已过期概念**（与 cert_warning.remaining_day 语义不同）。
- fund_raising_program_id=0 或 fund_raising_program_no="" 表示后端备案号补齐失败，数据不可信，
  调用方必须中止该项目更新流程、提示用户联系管理员，不得强行提交。
==================================================================
"""
import argparse
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


def _audit_label(status):
    return {1: "已通过", 2: "审批中", 3: "已驳回"}.get(status, f"未知({status})")


def _cert_detail(detail_data, institution_type):
    cw = detail_data.get("cert_warning")
    items = (cw or {}).get("items") or []
    out = []
    for it in items:
        rd = it.get("remaining_day")
        out.append({
            "cert_type_code": it.get("cert_type"),
            "cert_type_label": _cert_type_label(it.get("cert_type"), institution_type),
            "expire_date": it.get("end_date"),
            "remaining_day": rd,
            "expired": rd == -1,
        })
    out.sort(key=lambda x: (-1 if x["expired"] else x["remaining_day"]))
    return {"count": len(out), "list": out,
            "has_pending_review": bool(detail_data.get("has_pending_review"))}


def _record_detail():
    all_projects = []
    page = 1
    data_version_ts = None
    while True:
        r = call_mcp("get_pending_project_list",
                     {"page": page, "page_size": 100,
                      "warning_types": [1]}, 30)["data"] or {}
        if data_version_ts is None:
            data_version_ts = r.get("data_version_ts")
        projs = r.get("projects") or []
        if not projs:
            break
        for p in projs:
            status = p.get("fund_raising_program_audit_status")
            all_projects.append({
                "project_no": p.get("project_no"),
                "project_name": p.get("project_name"),
                "project_type": p.get("project_type"),
                "pending_stop_days": p.get("pending_stop_days"),
                "fund_raising_program_id": p.get("fund_raising_program_id"),
                "fund_raising_program_no": p.get("fund_raising_program_no"),
                "fund_raising_program_audit_status": status,
                "audit_status_label": _audit_label(status),
                "updatable": status != 2,
                # warns[] 透传但本流程不使用 warning_id（v2 已迁移到项目级 fund_raising_program_id）；
                # warning_id 是预警条目主键，严禁作为 update_org_record_number.id 入参
                "warns": p.get("warns") or [],
            })
        if len(projs) < 100:
            break
        page += 1
    # 排序：updatable=True（可更新）排前，False（审批中等）排后；组内按 pending_stop_days 升序（越紧迫越靠前）
    all_projects.sort(key=lambda x: (not x["updatable"], x["pending_stop_days"] if x["pending_stop_days"] is not None else 0))
    updatable_count = sum(1 for p in all_projects if p["updatable"])
    return {"count": len(all_projects), "updatable_count": updatable_count,
            "list": all_projects, "data_version_ts": data_version_ts}


def _cert_day_label(rd):
    if rd == -1:
        return "已过期"
    return f"{rd}天内到期"


def _rec_day_label(days):
    d = days if isinstance(days, int) else 0
    return f"{d}天内到期"


def _build_todo_cards(cert_detail, record_detail):
    """组装可点击待办卡片列表（title/subtitle/description），供调用方渲染。

    规则：
    - 证件：cert 列表非空 且 has_pending_review=false → 1 张（subtitle 仅首项，description 全部项）
    - 备案号：record 列表内每个 updatable=true 的项目各 1 张（subtitle==description）
    """
    cards = []
    if cert_detail is not None:
        cert_list = cert_detail.get("list") or []
        has_pending_review = cert_detail.get("has_pending_review")
        if cert_list and not has_pending_review:
            first = cert_list[0]
            subtitle = f"更新{first['cert_type_label']}({_cert_day_label(first['remaining_day'])})"
            desc = ", ".join(
                f"{c['cert_type_label']}({_cert_day_label(c['remaining_day'])})" for c in cert_list
            )
            cards.append({"title": "证件", "subtitle": subtitle, "description": desc})
    if record_detail is not None:
        for p in record_detail.get("list") or []:
            if not p.get("updatable"):
                continue
            pid = p.get("project_no")  # 项目自身编号（非备案号主键 fund_raising_program_id）
            pname = p.get("project_name")
            pno = p.get("fund_raising_program_no")
            text = f"更新[{pid}]{pname}的备案号{pno}({_rec_day_label(p.get('pending_stop_days'))})"
            cards.append({"title": "备案号", "subtitle": text, "description": text})
    return cards


def _main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", choices=["cert", "record", "both"], default="both")
    args = ap.parse_args()
    try:
        out = {}
        org = get_user_and_org_info()
        if org.get("is_error"):
            org_info = {"org_no": "", "org_name": "", "type_of_organization": None}
        else:
            org_info = dict(org)  # 完整机构字段透传：org_no/org_name/type_of_organization/affili_pub_org*/account_id/name
        cert_detail = None
        record_detail = None
        if args.scope in ("cert", "both"):
            d = call_mcp("get_org_detail", {}, 30)["data"] or {}
            cert_detail = _cert_detail(d, d.get("institution_type"))
            out["cert"] = cert_detail
            # 机构类型回退：get_user_and_org_info 失败时用 get_org_detail.institution_type 补齐（两者等价）
            if org_info.get("type_of_organization") is None:
                org_info["type_of_organization"] = d.get("institution_type")
        out["org"] = org_info
        if args.scope in ("record", "both"):
            record_detail = _record_detail()
            out["record"] = record_detail
        out["todo_cards"] = _build_todo_cards(cert_detail, record_detail)
        print(json.dumps(out, ensure_ascii=False))
    except Exception as e:  # noqa: BLE001
        need_refresh = isinstance(e, MCPAuthError)
        print(json.dumps({"success": False,
                          "error_code": "auth_failed" if need_refresh else "mcp_error",
                          "message": f"查询待办详情失败: {_sanitize(str(e))}",
                          "need_refresh": need_refresh}, ensure_ascii=False))
        sys.exit(1)


def main():
    observe_entrypoint(CALLER_EXPERT_ID, "alert.query_todo_detail", "query_todo_detail", _main)


if __name__ == "__main__":
    main()
