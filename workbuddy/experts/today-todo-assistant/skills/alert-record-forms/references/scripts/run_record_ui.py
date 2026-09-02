#!/usr/bin/env python3
"""备案号更新单步入口：校验、实时守卫、缓存，并通过 stdout 返回 UI 两字段参数。

视觉快速路径只需要一份位于当前工作目录（cwd）的 record_input.json。Agent 在调用前完成
OCR 质量提示和 no/selected_old_no 比对；脚本再次验证确认标记，并用实时项目数据防止
选择项目后 old_no 或审批状态发生变化。任何确认缺失或上下文过期都不会写公共缓存。
"""
import argparse
import contextlib
import io
import json
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COMMON_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "..", "..", "_common"))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
if COMMON_DIR not in sys.path:
    sys.path.insert(0, COMMON_DIR)

from build_record_ui_params import (  # noqa: E402
    INT_FIELDS,
    NEXT_STEP,
    SAFE_WARNING_RE,
    STR_FIELDS,
    _build_body,
    _fetch_project_by_id,
    _is_missing,
    _payload_hash,
)
from mcp_client import CALLER_EXPERT_ID, MCPAuthError, set_common_data_cache  # noqa: E402
from observe_bootstrap import observe_entrypoint  # noqa: E402
from validate_record_ocr import validate_record_ocr  # noqa: E402


TERMINAL_STATES = {"PAYLOAD_BUILT", "REJECTED", "STALE_PROJECT_CONTEXT", "CANCELLED"}


def _result(state, *, success=False, reason="", message="", **extra):
    output = {"success": success, "state": state}
    if reason:
        output["reason"] = reason
    if message:
        output["message"] = message
    output.update(extra)
    return output


def _is_in_skill_dir(path):
    """判断输入文件路径是否落在脚本目录或 _common 目录下（这些目录禁止写/删）。"""
    if not path:
        return False
    try:
        real_path = os.path.realpath(os.path.abspath(path))
        for protected in (SCRIPT_DIR, COMMON_DIR):
            if os.path.commonpath((real_path, os.path.realpath(protected))) == os.path.realpath(protected):
                return True
    except ValueError:
        return False
    return False


def _safe_remove_input(path):
    """删除输入文件（相对路径基于进程 cwd 解析）；保护 Skill 源码目录不被误删。"""
    if not path or _is_in_skill_dir(path):
        return
    try:
        os.remove(os.path.abspath(path))
    except (FileNotFoundError, OSError):
        pass


def _normalize_org_name(value):
    return re.sub(r"[\W_]+", "", str(value or "").strip(), flags=re.UNICODE).casefold()


def _map_charity_fields(result):
    mapped = {}
    for field in STR_FIELDS + INT_FIELDS:
        value = result.get(field)
        if not _is_missing(value):
            mapped[field] = value
    if not _is_missing(result.get("scheme_name")):
        mapped["name"] = result["scheme_name"]
    if not _is_missing(result.get("scheme_no")):
        mapped["no"] = result["scheme_no"]
    if not _is_missing(result.get("org_name")):
        mapped["_charity_org_name"] = str(result["org_name"]).strip()
    return mapped


def _fetch_charity_fields(url):
    """延迟导入，视觉快速路径不初始化慈善中国 HTTP 逻辑。"""
    from fetch_charity_record import extract_page_id_from_url, fetch_and_parse

    page_id = extract_page_id_from_url(url)
    if not page_id:
        return None, _result(
            "USER_DECISION_REQUIRED",
            reason="invalid_charity_url",
            message="必须提供有效的慈善中国备案详情页链接",
        )
    try:
        return _map_charity_fields(fetch_and_parse(page_id)), None
    except Exception:  # noqa: BLE001
        return None, _result(
            "USER_DECISION_REQUIRED",
            reason="charity_query_failed",
            message="慈善中国详情查询失败，请检查链接、稍后重试或改用截图",
        )


def _parse_context(payload):
    context = payload.get("context")
    if not isinstance(context, dict):
        return None, _result("REJECTED", reason="context_missing", message="输入缺少 context")

    try:
        project_id = int(context.get("id"))
    except (TypeError, ValueError):
        return None, _result("REJECTED", reason="id_invalid", message="context.id 必须是项目 ID")

    org_no = str(context.get("org_no") or "").strip()
    selected_old_no = str(context.get("selected_old_no") or "").strip()
    if not org_no:
        return None, _result("REJECTED", reason="org_no_missing", message="context.org_no 不能为空")
    if not selected_old_no:
        return None, _result(
            "REJECTED",
            reason="selected_old_no_missing",
            message="context.selected_old_no 必须来自用户选择项目时展示的备案号",
        )

    parsed = {
        "id": project_id,
        "org_no": org_no,
        "org_name": str(context.get("org_name") or "").strip(),
        "selected_old_no": selected_old_no,
        "quality_warning_confirmed": context.get("quality_warning_confirmed") is True,
        "confirmed_charity_org_name": str(context.get("confirmed_charity_org_name") or "").strip(),
    }
    return parsed, None


def _quality_requires_confirmation(quality, fields):
    return bool(
        quality.get("confidence") == "low"
        or quality.get("uncertain_fields")
        or _is_missing(fields.get("no"))
        or _is_missing(fields.get("name"))
    )


def prepare_record_ui(
    payload,
    *,
    source="vision",
    charity_url=None,
    fetch_project=_fetch_project_by_id,
    cache_payload=set_common_data_cache,
    fetch_charity=_fetch_charity_fields,
):
    """执行单步流水线；只有返回 PAYLOAD_BUILT 时才写入公共缓存。"""
    if not isinstance(payload, dict):
        return _result("REJECTED", reason="json_shape", message="输入 JSON 必须是对象")
    if payload.get("schema_version") != "2.0":
        return _result(
            "REJECTED",
            reason="schema_version_invalid",
            message="单步流程只接受 schema_version=2.0 的精简输入",
        )

    context, error = _parse_context(payload)
    if error:
        return error

    quality = {"missing_fields": [], "uncertain_fields": [], "warnings": [], "confidence": "high"}
    fields = {}

    if source == "vision":
        validated = validate_record_ocr(payload)
        if not validated.get("success"):
            return _result(
                "REJECTED",
                reason=validated.get("error_code") or "ocr_rejected",
                message="备案表视觉结果未通过结构校验",
                errors=validated.get("errors") or [],
            )
        fields.update(validated["fields"])
        quality.update(validated.get("quality") or {})
    elif source != "charity":
        return _result("REJECTED", reason="source_invalid", message="source 只能是 vision 或 charity")

    if charity_url:
        charity_fields, charity_error = fetch_charity(charity_url)
        if charity_error:
            return charity_error
        if source == "charity":
            fields.update(charity_fields)
        else:
            for field, value in charity_fields.items():
                if field.startswith("_") or _is_missing(fields.get(field)):
                    fields[field] = value
    elif source == "charity":
        return _result(
            "REJECTED",
            reason="charity_url_required",
            message="charity 来源必须提供有效慈善中国详情页链接",
        )

    if _is_missing(fields.get("no")) and _is_missing(fields.get("name")):
        return _result(
            "REJECTED",
            reason="record_not_detected",
            message="no 与 name 同时为空，未识别到有效备案信息",
        )

    if _quality_requires_confirmation(quality, fields):
        if not context["quality_warning_confirmed"]:
            return _result(
                "USER_DECISION_REQUIRED",
                reason="ocr_quality_warning",
                message="OCR 存在低置信度、关键字段缺失或不确定字段，需先由用户选择继续方式",
                missing_fields=quality.get("missing_fields") or [],
                uncertain_fields=quality.get("uncertain_fields") or [],
            )

    charity_org_name = str(fields.get("_charity_org_name") or "").strip()
    if charity_org_name:
        current_org_name = context["org_name"]
        if not current_org_name:
            return _result(
                "REJECTED",
                reason="current_org_name_missing",
                message="慈善中国返回机构名，但当前机构名缺失，无法执行一致性校验",
            )
        if (
            _normalize_org_name(charity_org_name) != _normalize_org_name(current_org_name)
            and context["confirmed_charity_org_name"] != charity_org_name
        ):
            return _result(
                "USER_DECISION_REQUIRED",
                reason="charity_org_mismatch",
                message="慈善中国机构名与当前机构不一致，必须先由用户确认",
                charity_org_name=charity_org_name,
                current_org_name=current_org_name,
            )

    project = fetch_project(context["id"])
    if project is None:
        return _result(
            "REJECTED",
            reason="project_not_found",
            message="实时预警项目列表中不存在所选项目，请刷新后重选",
            need_refresh=True,
        )
    raw_audit_status = project.get("fund_raising_program_audit_status")
    try:
        audit_status = int(raw_audit_status)
    except (TypeError, ValueError):
        return _result(
            "REJECTED",
            reason="audit_status_invalid",
            message="实时查询未返回有效审批状态，请刷新后重试",
            need_refresh=True,
        )
    if audit_status not in (1, 3):
        return _result(
            "REJECTED",
            reason="audit_pending" if audit_status == 2 else "audit_status_not_updatable",
            message="该备案号当前不可更新，请刷新项目状态",
            need_refresh=True,
        )

    latest_old_no = str(project.get("fund_raising_program_no") or "").strip()
    if not latest_old_no:
        return _result(
            "REJECTED",
            reason="old_no_missing",
            message="实时查询未返回有效备案号",
            need_refresh=True,
        )
    if latest_old_no != context["selected_old_no"]:
        return _result(
            "STALE_PROJECT_CONTEXT",
            reason="old_no_changed",
            message="项目备案号已在后台发生变化，请刷新项目后重新确认",
            need_refresh=True,
        )

    request = {
        "id": context["id"],
        "org_no": context["org_no"],
    }
    for field in STR_FIELDS:
        value = fields.get(field)
        request[field] = value.strip() if isinstance(value, str) else value
    for field in INT_FIELDS:
        request[field] = fields.get(field)
    body = _build_body(request, latest_old_no)

    ui_payload = {
        "caller_expert_id": CALLER_EXPERT_ID,
        "fundraising_program": body,
        "submit": {"next_step": NEXT_STEP},
    }
    cache_id = cache_payload(ui_payload)

    warnings = [
        warning for warning in (quality.get("warnings") or [])
        if isinstance(warning, str) and SAFE_WARNING_RE.fullmatch(warning)
    ]
    if not body.get("no"):
        warnings.append("no_missing_ui_required")
    if not body.get("name"):
        warnings.append("name_missing_ui_required")
    if body.get("no") and body["no"] != latest_old_no:
        warnings.append("no_mismatch_ui_review")

    return _result(
        "PAYLOAD_BUILT",
        success=True,
        caller_expert_id=CALLER_EXPERT_ID,
        data_cache_id=cache_id,
        warnings=list(dict.fromkeys(warnings)),
        payload_hash=_payload_hash(ui_payload),
    )


def _load_json(path):
    with open(os.path.abspath(path), encoding="utf-8") as file:
        return json.load(file)


def _main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=("vision", "charity"), default="vision")
    parser.add_argument("--json-file", required=True, help="当前工作目录中的 record_input.json（用相对路径）")
    parser.add_argument("--charity-url", default=None, help="用户明确提供并选择查询的慈善中国详情页链接")
    parser.add_argument("--cancel", action="store_true", help="取消当前流程并删除输入临时文件")
    args = parser.parse_args()

    if _is_in_skill_dir(args.json_file):
        print(json.dumps(_result(
            "REJECTED",
            reason="input_in_skill_dir",
            message="record_input.json 不得写入 Skill 源码目录，请写到会话工作目录（cwd）",
        ), ensure_ascii=False))
        return

    if args.cancel:
        _safe_remove_input(args.json_file)
        print(json.dumps(_result("CANCELLED", success=True), ensure_ascii=False))
        return

    try:
        payload = _load_json(args.json_file)
    except FileNotFoundError:
        normalized = os.path.abspath(args.json_file).replace("\\", "/")
        print(json.dumps(_result(
            "REJECTED",
            reason="input_file_not_found",
            message=(
                "输入文件不存在。请确认 record_input.json 已写入会话工作目录（cwd）且未被脚本清理"
                "（终态会自动删除输入文件）。若用文件写入能力写了相对路径，运行脚本时 cwd 必须与写入时一致: " + normalized
            ),
        ), ensure_ascii=False))
        return
    except ValueError:
        print(json.dumps(_result(
            "REJECTED",
            reason="input_json_parse",
            message="record_input.json 解析失败，请基于已载入图片重新生成一次",
        ), ensure_ascii=False))
        return

    try:
        with contextlib.redirect_stdout(io.StringIO()):
            result = prepare_record_ui(
                payload,
                source=args.source,
                charity_url=args.charity_url,
            )
    except (MCPAuthError, SystemExit):
        result = _result(
            "RETRY_REQUIRED",
            reason="mcp_auth_error",
            message="连接凭证失效，请刷新后使用同一输入文件重试",
            need_refresh=True,
        )
    except Exception as exc:  # noqa: BLE001
        result = _result(
            "RETRY_REQUIRED",
            reason="pipeline_error",
            message=f"备案号参数构建暂时失败，可使用同一输入文件重试: {type(exc).__name__}",
        )

    print(json.dumps(result, ensure_ascii=False))
    if result.get("state") in TERMINAL_STATES:
        _safe_remove_input(args.json_file)
    # 业务状态统一通过 stdout JSON 表达，避免命令层把待确认/拒绝误判为脚本崩溃。


def main():
    observe_entrypoint(CALLER_EXPERT_ID, "alert.run_record_ui", "run_record_ui", _main)


if __name__ == "__main__":
    main()
