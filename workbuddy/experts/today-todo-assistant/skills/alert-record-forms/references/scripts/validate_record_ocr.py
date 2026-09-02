#!/usr/bin/env python3
"""备案号视觉结果校验兼容模块。

业务流程唯一入口是 run_record_ui.py；Agent 禁止单独运行本文件。validate_record_ocr()
由单步入口内部复用，下方写文件 CLI 仅保留旧流程兼容和测试。
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "_common")))
from observe_bootstrap import observe_entrypoint

CALLER_EXPERT_ID = "alert-expert"
SCHEMA_VERSION = "1.0"
COMPACT_SCHEMA_VERSION = "2.0"
STRATEGY_ID = "llm_vision_record"

STR_FIELDS = (
    "no", "name", "start_date", "end_date", "purpose_of_donation", "purpose_use",
    "support_project", "recipient_scope", "recipient_num", "recipient_confirm_method",
    "fundras_target", "recipient_funding_desc", "implement_desc", "manage_cost_desc",
    "fundraising_cost", "remain_assets_desc", "partner_name",
)
INT_FIELDS = ("offsite_fundraising", "has_partner", "partner_type")
ALL_FIELDS = STR_FIELDS + INT_FIELDS
EVIDENCE_FIELDS = ("no", "name", "start_date", "end_date", "fundras_target")
CONFIDENCE_VALUES = {"high", "medium", "low"}
WARNING_CODE_RE = re.compile(r"^[a-z][a-z0-9_]*(?::[a-z][a-z0-9_]*)?$")


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


def _is_empty(value):
    return value is None or (isinstance(value, str) and not value.strip())


def _valid_date(value):
    if _is_empty(value):
        return True
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return False
    try:
        dt.date.fromisoformat(value)
        return True
    except ValueError:
        return False


def _string_list(value):
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def validate_record_ocr(payload):
    """返回标准校验结果；仅 envelope 结构错误或无法确认备案表时拒绝进入 UI。"""
    structural_errors = []
    computed_warnings = []

    if not isinstance(payload, dict):
        payload = {}
        structural_errors.append("root_not_object")

    schema_version = payload.get("schema_version")
    if schema_version not in (SCHEMA_VERSION, COMPACT_SCHEMA_VERSION):
        structural_errors.append("schema_version_invalid")
    if schema_version == SCHEMA_VERSION and payload.get("success") is not True:
        structural_errors.append("extraction_not_successful")
    if payload.get("strategy_id") != STRATEGY_ID:
        structural_errors.append("strategy_id_invalid")

    source = payload.get("source")
    if not isinstance(source, dict):
        source = {}
        structural_errors.append("source_missing")
    image_count = source.get("image_count")
    if isinstance(image_count, bool) or not isinstance(image_count, int) or image_count not in (1, 2):
        structural_errors.append("image_count_invalid")
        image_count = 0
    has_partner_image = source.get("has_partner_image")
    if not isinstance(has_partner_image, bool):
        structural_errors.append("has_partner_image_invalid")
        has_partner_image = False
    if image_count and image_count != (2 if has_partner_image else 1):
        structural_errors.append("image_count_partner_image_mismatch")

    fields_input = payload.get("fields")
    if not isinstance(fields_input, dict):
        fields_input = {}
        structural_errors.append("fields_missing")

    fields = {}
    for field in STR_FIELDS:
        value = fields_input.get(field)
        if value is not None and not isinstance(value, str):
            computed_warnings.append(f"{field}:type_coerced_to_string")
            value = str(value)
        fields[field] = value

    for field in INT_FIELDS:
        value = fields_input.get(field)
        if value is None or value == "":
            fields[field] = None
        elif isinstance(value, bool):
            fields[field] = None
            computed_warnings.append(f"{field}:invalid_enum")
        elif isinstance(value, int) and value in (0, 1, 2):
            fields[field] = value
        elif isinstance(value, str) and value.strip() in ("0", "1", "2"):
            fields[field] = int(value.strip())
            computed_warnings.append(f"{field}:enum_coerced_to_int")
        else:
            fields[field] = None
            computed_warnings.append(f"{field}:invalid_enum")

    for field in ("start_date", "end_date"):
        if not _valid_date(fields[field]):
            computed_warnings.append(f"{field}:invalid_date")

    if not has_partner_image:
        if any(not _is_empty(fields[field]) for field in ("has_partner", "partner_type", "partner_name")):
            computed_warnings.append("partner_fields_ignored_without_partner_image")
        fields["has_partner"] = None
        fields["partner_type"] = None
        fields["partner_name"] = None
    elif fields["has_partner"] != 1:
        if any(not _is_empty(fields[field]) for field in ("partner_type", "partner_name")):
            computed_warnings.append("partner_details_ignored_without_confirmed_partner")
        fields["partner_type"] = None
        fields["partner_name"] = None

    quality = payload.get("quality")
    if not isinstance(quality, dict):
        quality = {}
        structural_errors.append("quality_missing")
    confidence = quality.get("confidence")
    if confidence not in CONFIDENCE_VALUES:
        confidence = "low"
        computed_warnings.append("confidence_invalid_defaulted_to_low")

    uncertain_fields = [
        field for field in _string_list(quality.get("uncertain_fields")) if field in ALL_FIELDS
    ]
    model_warnings = _string_list(quality.get("warnings"))
    safe_model_warnings = [warning for warning in model_warnings if WARNING_CODE_RE.fullmatch(warning)]
    if len(safe_model_warnings) != len(model_warnings):
        safe_model_warnings.append("model_warning_redacted")
    warnings = list(dict.fromkeys(safe_model_warnings + computed_warnings))

    applicable_fields = list(ALL_FIELDS)
    if not has_partner_image:
        applicable_fields = [
            field for field in applicable_fields
            if field not in ("has_partner", "partner_type", "partner_name")
        ]
    missing_fields = [field for field in applicable_fields if _is_empty(fields[field])]
    if schema_version == SCHEMA_VERSION:
        evidence_input = payload.get("evidence")
        evidence_input = evidence_input if isinstance(evidence_input, dict) else {}
        for field in EVIDENCE_FIELDS:
            value = evidence_input.get(field)
            evidence = value if isinstance(value, str) else None
            if not _is_empty(fields[field]) and _is_empty(evidence):
                warnings.append(f"{field}:evidence_missing")

        if not isinstance(payload.get("raw_ocr_text"), str):
            warnings.append("raw_ocr_text_missing")

    record_detected = not (_is_empty(fields["no"]) and _is_empty(fields["name"]))
    if not record_detected:
        structural_errors.append("record_not_detected")

    success = not structural_errors
    return {
        "schema_version": schema_version if schema_version in (SCHEMA_VERSION, COMPACT_SCHEMA_VERSION) else COMPACT_SCHEMA_VERSION,
        "success": success,
        "state": "OCR_VALIDATED" if success else "OCR_REJECTED",
        "allow_ui": success,
        "strategy_id": STRATEGY_ID,
        "source": {
            "image_count": image_count,
            "has_partner_image": has_partner_image,
        },
        "fields": fields,
        "quality": {
            "confidence": confidence,
            "missing_fields": missing_fields,
            "uncertain_fields": uncertain_fields,
            "warnings": list(dict.fromkeys(warnings)),
        },
        "evidence_checked": True,
        "sensitive_text_removed": True,
        "error_code": structural_errors[0] if structural_errors else "",
        "errors": structural_errors,
    }


def _default_output_path(input_path):
    base, _ = os.path.splitext(os.path.abspath(input_path))
    return base + "_validated.json"


def _main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-file", required=True, help="LLM 视觉输出的临时 ocr_result.json")
    parser.add_argument("--output", default=None, help="校验结果临时文件路径")
    args = parser.parse_args()
    output_path = args.output or _default_output_path(args.json_file)
    if not _is_temp_path(args.json_file) or not _is_temp_path(output_path):
        print(json.dumps({
            "success": False,
            "state": "OCR_REJECTED",
            "error_code": "temp_path_required",
            "message": "兼容 CLI 仅允许系统临时目录中的输入和输出文件",
        }, ensure_ascii=False))
        return

    try:
        with open(args.json_file, encoding="utf-8") as file:
            payload = json.load(file)
    except Exception:  # noqa: BLE001
        _safe_remove(args.json_file)
        _safe_remove(output_path)
        print(json.dumps({
            "success": False,
            "state": "OCR_REJECTED",
            "error_code": "json_parse",
            "message": "OCR JSON 解析失败，原始临时文件已清理",
        }, ensure_ascii=False))
        sys.exit(1)

    result = validate_record_ocr(payload)
    try:
        with open(output_path, "w", encoding="utf-8") as file:
            json.dump(result, file, ensure_ascii=False, indent=2)
    except OSError:  # noqa: BLE001
        _safe_remove(args.json_file)
        _safe_remove(output_path)
        print(json.dumps({
            "success": False,
            "state": "OCR_REJECTED",
            "error_code": "write_output",
            "message": "写出 OCR 校验结果失败，原始临时文件已清理",
        }, ensure_ascii=False))
        sys.exit(1)

    # 原始 envelope 可能含 raw OCR；校验完成后立即删除，只保留已去除原文的校验产物。
    _safe_remove(args.json_file)

    summary = {
        "success": result["success"],
        "state": result["state"],
        "error_code": result["error_code"],
        "output_file": output_path,
        "missing_fields": result["quality"]["missing_fields"],
        "uncertain_fields": result["quality"]["uncertain_fields"],
        "warnings": result["quality"]["warnings"],
    }
    print(json.dumps(summary, ensure_ascii=False))
    if not result["success"]:
        _safe_remove(output_path)
        sys.exit(1)


def main():
    observe_entrypoint(
        CALLER_EXPERT_ID,
        "alert.validate_record_ocr",
        "validate_record_ocr",
        _main,
    )


if __name__ == "__main__":
    main()
