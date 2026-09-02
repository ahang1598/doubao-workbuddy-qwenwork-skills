#!/usr/bin/env python3
"""备案号字段构建兼容模块。

业务流程唯一入口是 run_record_ui.py；Agent 禁止单独运行本文件。下方 CLI 仅为旧流程兼容，
核心字段归一化、实时查询和业务体函数由单步入口内部复用。`old_no` 始终按 `id` 实时反查。
LLM 视觉主路径通过 `--validated-ocr-file` 输入 `OCR_VALIDATED` envelope；其中非空视觉字段
覆盖业务输入中的同名字段，空字段允许由慈善中国结果补齐。仅 `no` 与 `name` 同时为空时
判定未识别到备案表；单个字段缺失时按零值进入 UI，由用户补录。

输入：
  --source vision|charity：必传的数据来源类型。
  --json-file <path> 或 stdin：项目上下文，仅使用 `id` / `org_no` / `org_name` 和机构不一致确认标记。
  --validated-ocr-file <path>：vision 来源必传。
  --charity-result-file <path>：charity 来源必传；vision 路径补齐时可选。

关键规则：
  - 项目审批中、项目不存在、`id`/`org_no` 缺失属于入口硬阻断。
  - `no` 与 `name` 同时为空属于无有效备案表来源，硬阻断。
  - 仅 `no` 缺失、其他字段缺失或 `no` 不一致均不硬阻断，由 UI 补录/标红。
  - 未识别字段按类型填零值（string→"", int32→0）。
  - 若数据来自 fetch_charity_record.py，需先映射 scheme_name→name、scheme_no→no。
  - stdout 只输出状态、字段存在率、警告和 payload hash，不输出业务字段或 OCR 原文。

输出：
  ⚠️ **脚本先把「原先直接输出给 UI 的那份完整 JSON（caller_expert_id + fundraising_program + submit）」
     整体写入公共缓存（`set_common_data_cache`，即 `{"data": <那份完整 JSON>}`）拿到 `data_cache_id`，
     再把 UI 入参小 JSON 写出到文件**（不打印到 stdout，避免终端/工具链截断）。
     该文件内容**即是** `open_fund_raising_program_update_ui` MCP 工具的入参，仅含两字段：
     不含 `tool` / `success` 等任何 wrapper——UI 调用时【直接读取此文件内容】作为工具 parameters，
     ⛔ **禁止**二次转换/重组、⛔ **禁止**再塞进 `call_mcp(...)`、⛔ **禁止**读 inputSchema。
     文件路径：`--output <path>`；缺省为与 `--json-file` 同目录同名的 `<name>_ui_params.json`，
     若从 stdin 读入则缺省为当前目录 `./frp_ui_params.json`。
     文件内容形状：
  {
    "caller_expert_id": "alert-expert",
    "data_cache_id": "<set_common_data_cache 返回的 key>"
  }
  ⚠️ stdout 仅打印 `PAYLOAD_BUILT` 状态、字段完整性、警告、payload hash 和输出文件指针，不打印业务体 JSON。
  失败（守卫/校验不通过）时 stdout 输出错误形态（与工具入参形状不同，不会被误当入参）：
  { "success": false, "error_code": "...", "message": "...", "need_refresh": false }
"""
import argparse
import atexit
import hashlib
import json
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "_common")))
from mcp_client import call_mcp, set_common_data_cache, CALLER_EXPERT_ID, mask, _sanitize, MCPAuthError
from observe_bootstrap import observe_entrypoint

STR_FIELDS = ["no", "name", "purpose_of_donation", "start_date", "end_date",
             "purpose_use", "support_project", "recipient_scope", "recipient_num",
             "recipient_confirm_method", "fundras_target", "recipient_funding_desc",
             "implement_desc", "manage_cost_desc", "fundraising_cost", "remain_assets_desc",
             "partner_name"]
INT_FIELDS = ["offsite_fundraising", "has_partner", "partner_type"]
NEXT_STEP = "使用提交备案号到远程步骤, 重新拉取新的证件和备案号待办事项"
SAFE_WARNING_RE = re.compile(r"^[a-z][a-z0-9_]*(?::[a-z][a-z0-9_]*)?$")


def _is_temp_path(path):
    if not path:
        return False
    try:
        return os.path.commonpath((os.path.realpath(path), os.path.realpath(tempfile.gettempdir()))) == os.path.realpath(tempfile.gettempdir())
    except ValueError:
        return False


def _safe_remove(path):
    if not _is_temp_path(path):
        return
    try:
        os.remove(os.path.realpath(path))
    except (FileNotFoundError, OSError):
        pass


def _norm_fundras_target(v):
    """fundras_target 必须是纯浮点数字符串（如 "250000.00"），剔除单位/空格/千分位等非数字字符。

    OCR 可能返回 "250000.00 元" / "250,000.00 元"，一律归一为 "250000.00"。
    """
    if not isinstance(v, str):
        v = "" if v is None else str(v)
    return re.sub(r"[^\d.]", "", v)


def _norm_support_project(v):
    """support_project 去除 '-' 前的前缀，仅保留项目名。

    如 "531100006684027126P20001-三江源守护计划" → "三江源守护计划"；
    双横杠 "531100006684027126P20001-1-三江源守护计划" → "三江源守护计划"。
    """
    if not isinstance(v, str):
        return ""
    return v.split("-")[-1].strip()


def _err(error_code, msg, need_refresh=False):
    print(json.dumps({"success": False, "error_code": error_code, "message": msg,
                      "need_refresh": need_refresh}, ensure_ascii=False))
    sys.exit(1)


def _fetch_project_by_id(pid):
    page = 1
    while page <= 100:
        response = call_mcp(
            "get_pending_project_list",
            {"page": page, "page_size": 100, "warning_types": [1]},
            30,
        )
        if response.get("is_error"):
            raise RuntimeError(
                "get_pending_project_list 调用失败: "
                + str(response.get("text") or "未知错误")
            )
        data = response.get("data")
        if not isinstance(data, dict):
            raise RuntimeError("get_pending_project_list 返回数据格式错误")
        projects = data.get("projects") or []
        if not isinstance(projects, list):
            raise RuntimeError("get_pending_project_list.projects 不是数组")
        for project in projects:
            try:
                project_id = int(project.get("fund_raising_program_id"))
            except (TypeError, ValueError, AttributeError):
                continue
            if project_id == pid:
                return project
        if len(projects) < 100:
            return None
        page += 1
    raise RuntimeError("get_pending_project_list 分页超过 100 页，已停止查询")


def _build_body(req, old_no):
    body = {"id": int(req["id"]), "old_no": old_no, "org_no": str(req.get("org_no") or "").strip()}
    for f in STR_FIELDS:
        v = req.get(f)
        body[f] = v if isinstance(v, str) else ("" if v is None else str(v))
    for f in INT_FIELDS:
        v = req.get(f)
        if v in (None, ""):
            body[f] = 0
        else:
            try:
                body[f] = int(v)
            except (ValueError, TypeError):
                body[f] = 0
    # 字段归一化（脚本兜底，不依赖 AI 拼对）
    body["fundras_target"] = _norm_fundras_target(body.get("fundras_target"))
    body["support_project"] = _norm_support_project(body.get("support_project"))
    return body


def _is_missing(value):
    return value is None or (isinstance(value, str) and not value.strip())


def _load_charity_fields(charity_path):
    if not charity_path:
        return {}
    try:
        with open(charity_path, encoding="utf-8") as file:
            result = json.load(file)
    except Exception as exc:  # noqa: BLE001
        _err("charity_result_read", f"读取慈善中国结果失败: {_sanitize(str(exc))}")
    if not isinstance(result, dict):
        _err("charity_result_invalid", "慈善中国结果必须是 JSON 对象")
    if not (
        result.get("success") is True
        and result.get("_source") == "charity_china"
        and result.get("_schema_version") == "1.0"
        and result.get("_page_id")
    ):
        _err("charity_source_unverified", "慈善中国结果缺少合法来源标识")

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


def _load_validated_ocr(validation_path):
    try:
        with open(validation_path, encoding="utf-8") as file:
            validated = json.load(file)
    except Exception as exc:  # noqa: BLE001
        _err("ocr_validation_read", f"读取 OCR 校验结果失败: {_sanitize(str(exc))}")

    if not isinstance(validated, dict):
        _err("ocr_validation_invalid", "OCR 校验结果必须是 JSON 对象")
    if not (
        validated.get("schema_version") == "1.0"
        and validated.get("success") is True
        and validated.get("allow_ui") is True
        and validated.get("state") == "OCR_VALIDATED"
        and validated.get("strategy_id") == "llm_vision_record"
        and validated.get("sensitive_text_removed") is True
        and not validated.get("errors")
        and isinstance(validated.get("source"), dict)
    ):
        _err("ocr_not_validated", "OCR 结果未达到完整 OCR_VALIDATED 契约，禁止构建 UI 参数")
    fields = validated.get("fields")
    if not isinstance(fields, dict) or any(field not in fields for field in STR_FIELDS + INT_FIELDS):
        _err("ocr_fields_missing", "OCR 校验结果缺少完整 fields")
    quality = validated.get("quality")
    return fields, quality if isinstance(quality, dict) else {}


def _build_source_request(context, source, validation_path, charity_path):
    """只接受可验证来源工件；忽略上下文 JSON 中手写的业务字段。"""
    merged = {
        "id": context.get("id"),
        "org_no": context.get("org_no"),
        "org_name": context.get("org_name"),
        "charity_org_mismatch_confirmed": context.get("charity_org_mismatch_confirmed") is True,
    }
    charity_fields = _load_charity_fields(charity_path)
    if source == "charity":
        if validation_path:
            _err("source_conflict", "charity 来源不得传 --validated-ocr-file")
        if not charity_path:
            _err("charity_result_required", "charity 来源必须传 --charity-result-file")
        merged.update(charity_fields)
        return merged, {}

    if not validation_path:
        _err("ocr_validation_required", "vision 来源必须传 --validated-ocr-file")
    ocr_fields, quality = _load_validated_ocr(validation_path)
    merged.update(charity_fields)
    for field in STR_FIELDS + INT_FIELDS:
        value = ocr_fields.get(field)
        if not _is_missing(value):
            merged[field] = value
        elif field not in merged:
            merged[field] = value
    return merged, quality


def _payload_hash(payload):
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_charity_org(req):
    charity_org_name = str(req.get("_charity_org_name") or "").strip()
    if not charity_org_name:
        return
    current_org_name = str(req.get("org_name") or "").strip()
    if not current_org_name:
        _err("current_org_name_missing", "慈善中国返回了机构名，但当前机构名缺失，无法执行一致性校验")
    if charity_org_name != current_org_name and not req.get("charity_org_mismatch_confirmed"):
        _err("charity_org_mismatch_unconfirmed", "慈善中国机构名与当前机构不一致，必须先由用户明确确认")


def _audit_status(project):
    try:
        return int(project.get("fund_raising_program_audit_status") or 0)
    except (TypeError, ValueError, AttributeError):
        _err("audit_status_invalid", "实时查询返回的审批状态格式无效")


def _main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=("vision", "charity"), required=True,
                    help="字段来源：vision=已校验 LLM 视觉；charity=慈善中国结果")
    ap.add_argument("--json-file", default=None,
                    help="项目上下文 JSON，仅使用 id/org_no/org_name/机构不一致确认标记（缺省读 stdin）")
    ap.add_argument("--validated-ocr-file", default=None,
                    help="validate_record_ocr.py 生成的 OCR_VALIDATED 临时文件；vision 来源必传")
    ap.add_argument("--charity-result-file", default=None,
                    help="fetch_charity_record.py 生成的来源结果；charity 来源必传，vision 补齐时可选")
    ap.add_argument("--output", default=None,
                    help="成功时 UI 入参 JSON 的写出路径（缺省: 与 --json-file 同目录同名的 <name>_ui_params.json，或 ./frp_ui_params.json）")
    args = ap.parse_args()
    for temp_path in (args.json_file, args.validated_ocr_file, args.charity_result_file):
        if temp_path:
            atexit.register(_safe_remove, temp_path)
    try:
        raw = (args.json_file and open(args.json_file, encoding="utf-8").read()) or sys.stdin.read()
        req = json.loads(raw)
        if not isinstance(req, dict):
            _err("json_shape", "输入 JSON 必须是对象")
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        _err("json_parse", f"输入 JSON 解析失败: {_sanitize(str(e))}")

    req, ocr_quality = _build_source_request(
        req,
        args.source,
        args.validated_ocr_file,
        args.charity_result_file,
    )

    # 决定输出文件路径（成功时把 UI 入参小 JSON 写文件）
    out_path = args.output
    if not out_path:
        if args.json_file:
            base, _ = os.path.splitext(os.path.abspath(args.json_file))
            out_path = base + "_ui_params.json"
        else:
            out_path = os.path.join(os.getcwd(), "frp_ui_params.json")
    if not _is_temp_path(out_path):
        _err("temp_path_required", "兼容 CLI 的输出文件必须位于系统临时目录")

    try:
        org_no = str(req.get("org_no") or "").strip()
        if not org_no:
            _err("org_no_missing", "缺少 org_no（必须来自查询脚本输出 org.org_no，由 AI 传入）")

        pid = req.get("id")
        if pid in (None, ""):
            _err("id_missing", "缺少 id（必须来自查询阶段的 fund_raising_program_id）")
        try:
            pid = int(pid)
        except (ValueError, TypeError):
            _err("id_invalid", f"id 必须是整数: {pid}")

        proj = _fetch_project_by_id(pid)
        if proj is None:
            _err("project_not_found", f"未在预警项目列表中找到 id={pid}（请用查询阶段返回的项目 ID）")
        if _audit_status(proj) == 2:
            _err("audit_pending", "该备案号正在更新审批中, 请等待审批通过后再修改。")

        _validate_charity_org(req)

        old_no = str(proj.get("fund_raising_program_no") or "").strip()
        if not old_no:
            _err("old_no_missing", "实时查询未返回有效 fund_raising_program_no，数据不可信，请联系管理员")
        if _is_missing(req.get("no")) and _is_missing(req.get("name")):
            _err("record_not_detected", "no 与 name 同时为空，未识别到有效备案表，禁止调起 UI")

        # no 为空或与 old_no 不一致均照常输出，由 UI 提示补录或标红阻止提交。
        body = _build_body(req, old_no)
        # ⛔ 新范式：把原先输出的那份完整 UI 入参 JSON 整体写入公共缓存，UI 调用只带 caller_expert_id + data_cache_id
        ui_params = {
            "caller_expert_id": CALLER_EXPERT_ID,
            "fundraising_program": body,
            "submit": {"next_step": NEXT_STEP},
        }
        key = set_common_data_cache(ui_params)
        # UI 工具入参（仅两字段）写文件，避免 stdout 截断；内容 = caller_expert_id + data_cache_id
        result = {
            "caller_expert_id": CALLER_EXPERT_ID,
            "data_cache_id": key,
        }
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False)
        except Exception as e:  # noqa: BLE001
            _err("write_output", f"写出 UI 入参文件失败: {_sanitize(str(e))}")

        missing_fields = list(ocr_quality.get("missing_fields") or [])
        missing_fields.extend(field for field in STR_FIELDS if not body.get(field))
        missing_fields = list(dict.fromkeys(missing_fields))
        warnings = [
            warning for warning in (ocr_quality.get("warnings") or [])
            if isinstance(warning, str) and SAFE_WARNING_RE.fullmatch(warning)
        ]
        no_value = body.get("no", "").strip()
        if not no_value:
            warnings.append("no_missing_ui_required")
            no_matches_old_no = None
        else:
            no_matches_old_no = no_value == old_no
            if not no_matches_old_no:
                warnings.append("no_mismatch")
        if not body.get("name", "").strip():
            warnings.append("name_missing_ui_required")
        warnings = list(dict.fromkeys(warnings))

        print(json.dumps({
            "success": True,
            "state": "PAYLOAD_BUILT",
            "project_id": pid,
            "source": args.source,
            "ocr_validation_used": args.source == "vision",
            "no_matches_old_no": no_matches_old_no,
            "present_fields": len(STR_FIELDS) + len(INT_FIELDS) - len(missing_fields),
            "missing_fields": missing_fields,
            "warnings": warnings,
            "payload_hash": _payload_hash(ui_params),
            "output_file": out_path,
            "hint": "该文件内容即 open_fund_raising_program_update_ui 入参，UI 调用直接读取、不做转换",
        }, ensure_ascii=False))
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        _err("validate_fail", f"校验/取数失败: {_sanitize(str(e))}", need_refresh=isinstance(e, MCPAuthError))


def main():
    observe_entrypoint(CALLER_EXPERT_ID, "alert.build_record_ui_params", "build_record_ui_params", _main)


if __name__ == "__main__":
    main()
