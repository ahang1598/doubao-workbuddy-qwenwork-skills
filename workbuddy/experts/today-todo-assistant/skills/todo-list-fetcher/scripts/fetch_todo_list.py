#!/usr/bin/env python3
"""查询机构今日待办聚合（today-todo-assistant Lead 专用）。

直接调用 get_org_todo_list(caller_expert_id="today-todo-assistant")，拿到聚合后的四类数据，
**按各子专家原处理逻辑逐字符组装** option_data，输出给 Lead 渲染可点击列表。
用户点击某一项后，Lead 才按 type 召唤对应子专家（message→comment-assistant / alert→alert-expert / invoice→invoice-expert）。

输出（扁平 JSON）：
{
  "org": {机构信息},
  "has_message": bool,   # 是否有留言待处理
  "has_invoice": bool,   # 是否有票据待处理
  "has_filing": bool,    # 是否有备案号待处理
  "has_cert": bool,      # 是否有证件待处理
  "items": [
    {"key": "message", "type": "message", "option_data": "[留言处理]..."},
    {"key": "alert",   "type": "alert",   "kind": "cert|record|both", "option_data": "[证件更新]/[备案号更新]..."},
    {"key": "invoice", "type": "invoice", "option_data": "[待开票任务]..."}
  ],
  "filing_options": [   # 仅显式传 --include-filing-list 时返回
    {"key": "<project_no>", "option_data": "[备案号更新]..."}
  ]
}
- option_data 为脚本拼好的完整展示文案（含类型前缀 + 数量/到期描述），Lead 只透传、不拼装。
- 无待办的类别不进入 items（即该类别 option_data 为空时跳过）。
- has_* 为四类待办的布尔标记：供「直达指定类型」路由与「指定类型为空时推荐其他待办」判断。
- items[].type 为点击路由键：Lead 据此决定召唤哪个子专家。
- items 中 alert 额外带 kind（cert/record/both），供 Lead 转发时携带，子专家内部按 kind 分流。
- filing_options 仅当命令行传 --include-filing-list 时返回（备案号明细列表，防 Lead 在未指定备案号时误用）。

错误契约：接口不可用即上抛错误 JSON（need_refresh 标记鉴权失败），绝不降级展示假数据。
单类失败由服务端降级为零值（proto 省略零值字段），客户端按零值视为该类别无待办即可。

用法：
  python fetch_todo_list.py                          # 主路径聚合查询（不含备案号明细）
  python fetch_todo_list.py --include-filing-list    # 备案号直达（含备案号明细列表）
依赖：skills/_common/mcp_client.py（经 __file__ 相对路径自动导入）

==================================================================
字段契约（维护者必读 —— 由 get_org_todo_list 返回 proto 映射而来）
==================================================================
GetOrgTodoListResponse:
  pending_invoices  PendingInvoicesInfo  { total: uint32 }                       → 待处理票据数
  todo_filing       TodoFilingInfo       { pending_stop_project_count: int32,
                                           projects: [TodoFilingProject] }      → 备案号待办
  org_profile       OrgProfileInfo       { institution_type: int32,
                                           has_pending_review: bool,
                                           cert_warning: [CertWarningItem] }        → 机构画像（cert_warning 非超管为空、不可靠，已弃用）
  unreplied_comments UnrepliedCommentsInfo { total: uint32, risk_total: uint32 } → 待回复留言统计

TodoFilingProject: project_no, project_name, pending_stop_days:int32,
                   fund_raising_program_id:int32, fund_raising_program_no, fund_raising_program_audit_status:int32
CertWarningItem:   cert_type:int32, end_date:int64(秒级时间戳), remaining_day:int32（-1=已过期）

⚠️ proto3 零值字段在 JSON 中可能省略，统一用 .get(x, 0) / .get(x, []) 兜底。
⚠️ 证件预警（cert_warning）改用 get_org_detail 获取（get_org_todo_list 对超管判断有问题、返回空，已弃用 org_profile.cert_warning）。
  get_org_detail 返回 cert_warning 为 object（含 items 列表，证件清单在 cert_warning.items 里）；非超管为 nil → 视为无证件预警。
  get_org_detail 调用失败时视为无证件预警（柔性降级），不阻塞留言/票据/备案号等其它待办。
==================================================================
"""
import json
import os
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "_common")))
from mcp_client import call_mcp, get_user_and_org_info, CALLER_EXPERT_ID, mask, _sanitize, MCPAuthError
from observe_bootstrap import observe_entrypoint


# --------------------------------------------------------------------------- #
# 复刻 alert-expert 的 cert_type → label 映射（不得自行硬编码）
# --------------------------------------------------------------------------- #
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
    """把 get_org_detail 返回的 cert_warning.items 转成统一结构，按 (过期优先, remaining_day) 升序。"""
    items = (cert_warning or {}).get("items") or []
    out = []
    for it in items:
        rd = it.get("remaining_day")
        expired = (rd == -1)
        out.append({
            "cert_type_code": it.get("cert_type"),
            "cert_type_label": _cert_type_label(it.get("cert_type"), institution_type),
            "remaining_day": rd,
            "expired": expired,
        })
    # 已过期永远排最前
    out.sort(key=lambda x: (-1 if x["expired"] else x["remaining_day"]))
    return out


# --------------------------------------------------------------------------- #
# 卡片组装：复刻原各子专家 query_todo_summary / 查数 SKILL 的逐字符模板，
# 直接产出 option_data 完整展示文案（Lead 只透传、不拼装）。
# --------------------------------------------------------------------------- #
def _build_comment_item(unreplied_comments):
    """复刻 comment-todo-statistics SKILL 的留言处理卡片文案。"""
    total = unreplied_comments.get("total", 0) or 0
    risk = unreplied_comments.get("risk_total", 0) or 0
    if total <= 0:
        return {"key": "message", "type": "message", "option_data": ""}
    if total > 30:
        desc = f"30天内留言共{total}条，建议先处理最新的30条，去处理～"
    else:
        desc = f"有{total}条留言待处理, 其中{risk}条高风险留言, 我来协助你处理"
    option_data = f"[留言处理]{desc}"
    return {"key": "message", "type": "message", "option_data": option_data}


def _build_invoice_item(pending_invoices):
    """复刻 invoice-info-fetcher SKILL 的待开票任务卡片文案。"""
    total = pending_invoices.get("total", 0) or 0
    if total <= 0:
        return {"key": "invoice", "type": "invoice", "option_data": ""}
    option_data = f"[待开票任务]还有 {total} 张票据待处理, 我来协助你批量识别并提交"
    return {"key": "invoice", "type": "invoice", "option_data": option_data}


def _build_alert_part(org_detail, todo_filing):
    """复刻 alert-expert query_todo_summary.py：证件 > 备案号优先级；只取最紧迫 1 条。

    证件字段（institution_type / has_pending_review / cert_warning）取自 get_org_detail，
    因 get_org_todo_list 的 org_profile.cert_warning 在非超管下返回空、不可靠。

    返回 dict：
      - has_cert / has_filing：两类待办的布尔标记
      - alert_option：主路径菜单用的合并项 {key,type,kind,option_data}，无待办时 option_data 为空
    """
    institution_type = org_detail.get("institution_type")
    has_pending_review = bool(org_detail.get("has_pending_review"))
    cert_list = _build_cert_list(org_detail.get("cert_warning"), institution_type)
    cert_count = len(cert_list)

    pending_stop_project_count = todo_filing.get("pending_stop_project_count", 0) or 0
    projects = todo_filing.get("projects") or []
    record_has = bool(pending_stop_project_count and projects)
    cert_has = cert_count > 0

    if cert_has:
        top = cert_list[0]
        if has_pending_review:
            desc = "当前机构信息有申请单待审批, 审批完成后才能提交证件更新。"
        elif top["expired"]:
            desc = f"{top['cert_type_label']}已过期, 请尽快更新证件, 我来协助你更新"
        else:
            desc = f"{top['cert_type_label']}在 {top['remaining_day']} 天后到期, 请尽快更新证件, 我来协助你更新"
        option_data = f"[证件更新]{desc}"
    elif record_has:
        p0 = projects[0]
        project_no = p0.get("project_no", "")
        project_name = p0.get("project_name", "")
        pending_stop_days = p0.get("pending_stop_days", 0) or 0
        option_data = f"[备案号更新]{project_no} {project_name} 的备案号在 {pending_stop_days} 天后到期"
    else:
        option_data = ""

    if cert_has and record_has:
        kind = "both"
    elif cert_has:
        kind = "cert"
    elif record_has:
        kind = "record"
    else:
        kind = "none"

    return {
        "has_cert": cert_has,
        "has_filing": record_has,
        "alert_option": {"key": "alert", "type": "alert", "kind": kind, "option_data": option_data},
    }


def _build_filing_options(todo_filing):
    """备案号明细列表（仅显式指定备案号时调用）。option_data 复用 record 分支文案，
    并按 fund_raising_program_audit_status 做审批中标注。key=project_no 供 Lead 兜底匹配，
    alert-expert 从 option_data 内解析 project_no 精确匹配。"""
    projects = todo_filing.get("projects") or []
    out = []
    for p in projects:
        project_no = p.get("project_no", "")
        project_name = p.get("project_name", "")
        pending_stop_days = p.get("pending_stop_days", 0) or 0
        audit_status = p.get("fund_raising_program_audit_status", 0) or 0
        option_data = f"[备案号更新]{project_no} {project_name} 的备案号在 {pending_stop_days} 天后到期"
        if audit_status == 2:
            option_data += ", 【审批中】备案号更新中, 请等待审批通过后再修改"
        out.append({"key": project_no, "option_data": option_data})
    return out


def _unwrap(data):
    """兼容响应再包一层 data 的情况：优先用含四类字段的那一层。"""
    if not isinstance(data, dict):
        return {}
    if any(k in data for k in ("pending_invoices", "todo_filing", "org_profile", "unreplied_comments")):
        return data
    inner = data.get("data")
    if isinstance(inner, dict):
        return inner
    return data


def _main(include_filing_list=False):
    try:
        org = get_user_and_org_info()
        if org.get("is_error"):
            org_info = {"org_no": "", "org_name": ""}
        else:
            org_info = dict(org)  # 完整机构字段透传：org_no/org_name/type_of_organization/affili_pub_org*/account_id/name
        r = call_mcp("get_org_todo_list", {}, 30)
        resp = _unwrap(r.get("data") or {})

        pending_invoices = resp.get("pending_invoices") or {}
        todo_filing = resp.get("todo_filing") or {}
        unreplied_comments = resp.get("unreplied_comments") or {}

        # 证件预警改用 get_org_detail（get_org_todo_list 对超管判断有问题）。
        # 柔性：调用失败/异常视为无证件预警（org_detail 置空），不阻塞其它待办逻辑。
        try:
            detail = call_mcp("get_org_detail", {}, 30)
            org_detail = detail.get("data") or {}
        except Exception:
            org_detail = {}

        comment_item = _build_comment_item(unreplied_comments)
        alert_part = _build_alert_part(org_detail, todo_filing)
        invoice_item = _build_invoice_item(pending_invoices)

        # 四类待办布尔标记（供直达路由与"指定类型为空时推荐其他待办"判断）
        has_message = bool(comment_item.get("option_data"))
        has_filing = alert_part["has_filing"]
        has_cert = alert_part["has_cert"]
        has_invoice = bool(invoice_item.get("option_data"))

        candidates = [
            comment_item,
            alert_part["alert_option"],
            invoice_item,
        ]
        # option_data 为空 → 该类别无待办，跳过不进列表
        items = [it for it in candidates if it.get("option_data")]

        result = {
            "org": org_info,
            "has_message": has_message,
            "has_invoice": has_invoice,
            "has_filing": has_filing,
            "has_cert": has_cert,
            "items": items,
        }
        # 备案号明细列表：仅显式指定备案号（--include-filing-list）时才返回，防 Lead 误用
        if include_filing_list:
            result["filing_options"] = _build_filing_options(todo_filing)

        print(json.dumps(result, ensure_ascii=False))
    except Exception as e:  # noqa: BLE001
        need_refresh = isinstance(e, MCPAuthError)
        print(json.dumps({"success": False,
                          "error_code": "auth_failed" if need_refresh else "mcp_error",
                          "message": f"查询今日待办失败: {_sanitize(str(e))}",
                          "need_refresh": need_refresh}, ensure_ascii=False))
        sys.exit(1)


def main():
    include_filing_list = "--include-filing-list" in sys.argv
    observe_entrypoint(
        CALLER_EXPERT_ID,
        "today_todo.fetch_todo_list",
        "fetch_todo_list",
        lambda: _main(include_filing_list),
    )


if __name__ == "__main__":
    main()
