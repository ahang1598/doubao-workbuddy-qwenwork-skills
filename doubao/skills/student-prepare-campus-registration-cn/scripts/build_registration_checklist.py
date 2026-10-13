#!/usr/bin/env python3
"""Build a privacy-minimized, evidence-aware freshman registration checklist."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


STAGES = {
    "before_arrival": (0, "到校前"),
    "arrival_day": (1, "报到当天"),
    "first_week": (2, "入校首周"),
    "after_registration": (3, "报到后续"),
    "unknown": (4, "阶段待确认"),
}
CATEGORIES = {
    "admission_identity",
    "online_onboarding",
    "fees_and_payment",
    "documents_and_copies",
    "student_records",
    "party_youth_relation",
    "residence_and_hukou",
    "financial_aid",
    "dormitory_checkin",
    "health_and_training",
    "campus_services",
    "other",
}
REQUIREMENTS = {"required", "conditional", "recommended"}
STATUSES = {"confirmed", "user_provided", "to_verify", "not_applicable"}
STATUS_LABELS = {
    "confirmed": "已确认",
    "user_provided": "用户提供",
    "to_verify": "待确认",
    "not_applicable": "不适用",
}
REQUIREMENT_LABELS = {
    "required": "必做",
    "conditional": "条件适用",
    "recommended": "建议准备",
}
RISK_LEVELS = {"low", "medium", "high"}
FORBIDDEN_KEYS = {
    "account",
    "account_name",
    "username",
    "login_name",
    "email",
    "email_address",
    "phone_number",
    "mobile_number",
    "cellphone",
    "password",
    "passwd",
    "token",
    "verification_code",
    "sms_code",
    "id_number",
    "identity_number",
    "bank_card",
    "student_id",
    "full_name",
    "phone",
    "home_address",
    "studentname",
    "respondentid",
    "身份证",
    "身份证号",
    "身份证号码",
    "银行卡",
    "银行卡号",
    "手机号",
    "手机",
    "电话",
    "姓名",
    "学号",
    "密码",
    "验证码",
    "电子邮箱",
    "邮箱",
    "账号",
    "用户名",
    "住址",
    "家庭地址",
}
LABEL_QUALIFIER = r"(?:\s*(?:[（(][^()（）\n]{0,20}[）)]|\[[^\[\]\n]{0,20}\]|【[^【】\n]{0,20}】))?"
LABEL_VALUE_SEPARATOR = r"(?:\s*[:：=]\s*|\s*-\s*|\s+(?:为|是)?\s*|\s*(?:为|是)\s*)"
PII_PATTERNS = {
    "可能的身份证号": re.compile(r"(?<!\d)\d(?:[-\s()]*\d){16}[-\s()]*[0-9Xx](?!\d)"),
    "可能的银行卡号": re.compile(r"(?<!\d)\d(?:[-\s()]*\d){15,18}(?!\d)"),
    "可能的手机号": re.compile(r"(?<!\d)1[3-9](?:[-\s()]*\d){9}(?!\d)"),
    "可能的学号": re.compile(rf"(?:学号|student\s*id){LABEL_QUALIFIER}{LABEL_VALUE_SEPARATOR}[A-Za-z0-9_-]{{6,32}}", re.IGNORECASE),
    "可能的密码": re.compile(rf"(?:密码|口令|password|passwd){LABEL_QUALIFIER}{LABEL_VALUE_SEPARATOR}\S{{4,128}}", re.IGNORECASE),
    "可能的验证码": re.compile(rf"(?:短信验证码|验证码|短信码|otp|sms\s*code){LABEL_QUALIFIER}{LABEL_VALUE_SEPARATOR}[A-Za-z0-9]{{4,12}}", re.IGNORECASE),
    "可能的姓名": re.compile(rf"(?:本人姓名|姓名|name){LABEL_QUALIFIER}{LABEL_VALUE_SEPARATOR}[\u3400-\u9fff·]{{2,20}}", re.IGNORECASE),
    "可能的家庭地址": re.compile(rf"(?:家庭地址|家庭住址|详细住址|居住地址|我的地址){LABEL_QUALIFIER}{LABEL_VALUE_SEPARATOR}[^,，;；\n]{{6,120}}"),
    "可能的登录账号": re.compile(rf"(?:登录账号|迎新账号|用户名|账户名|账号){LABEL_QUALIFIER}{LABEL_VALUE_SEPARATOR}[A-Za-z0-9_.@-]{{4,64}}"),
}
EMAIL_PATTERN = re.compile(r"(?<![\w.+-])[\w.+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?![\w.-])", re.IGNORECASE)
ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
SCOPE_WILDCARDS = {
    "campuses": "全部校区",
    "program_levels": "全部培养层次",
    "student_categories": "全部新生",
}
NETWORK_TOOL_STATUSES = {
    "available_authorized",
    "available_authorization_pending",
    "unavailable",
    "not_used",
}
NETWORK_TOOL_STATUS_LABELS = {
    "available_authorized": "可用且已授权",
    "available_authorization_pending": "可用但授权待确认",
    "unavailable": "不可用",
    "not_used": "未使用",
}
ACCESS_METHODS = {"user_provided", "public_web", "offline"}
ACCESS_METHOD_LABELS = {
    "user_provided": "用户提供",
    "public_web": "公开网页",
    "offline": "离线材料",
}
AUTHORIZATION_STATUSES = {"authorized", "pending", "restricted", "not_applicable"}
AUTHORIZATION_STATUS_LABELS = {
    "authorized": "已授权",
    "pending": "授权待确认",
    "restricted": "访问受限",
    "not_applicable": "不适用",
}


class InputError(ValueError):
    """Raised when the input contract is violated."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="UTF-8 JSON input")
    parser.add_argument("--output", required=True, type=Path, help="Markdown output")
    parser.add_argument("--summary", type=Path, help="Optional JSON summary")
    parser.add_argument("--force", action="store_true", help="Replace existing output files")
    return parser.parse_args()


def read_json(path: Path) -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise OSError(f"无法读取输入文件：{exc}") from exc
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InputError(f"输入必须是 UTF-8 JSON：{exc}") from exc
    if not isinstance(data, dict):
        raise InputError("JSON 根节点必须是对象")
    return data, raw


def ensure_distinct_paths(input_path: Path, output_path: Path, summary_path: Path | None) -> None:
    paths = [input_path, output_path]
    if summary_path is not None:
        paths.append(summary_path)
    resolved = [path.resolve() for path in paths]
    if len(set(resolved)) != len(resolved):
        raise InputError("输入、Markdown 输出和摘要必须使用不同路径")
    for left_index, left in enumerate(paths):
        if not left.exists():
            continue
        for right in paths[left_index + 1 :]:
            if right.exists() and left.samefile(right):
                raise InputError("输入、Markdown 输出和摘要不得指向同一文件或硬链接")


def detect_forbidden_keys(value: Any, prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = re.sub(r"[_\-\s]", "", str(key).lower())
            field = f"{prefix}.{key}" if prefix else str(key)
            normalized_forbidden = {re.sub(r"[_\-\s]", "", item.lower()) for item in FORBIDDEN_KEYS}
            if key_text in normalized_forbidden:
                found.append(field)
            found.extend(detect_forbidden_keys(child, field))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(detect_forbidden_keys(child, f"{prefix}[{index}]"))
    return found


def normalize_pii_text(value: Any) -> str:
    """Normalize a detection-only copy without altering rendered user content."""
    text = unicodedata.normalize("NFKC", json.dumps(value, ensure_ascii=False))
    text = re.sub(r"sha256:[0-9a-fA-F]{64}", "", text)
    text = re.sub(r"(?:\*\*|__)", "", text)
    for emphasis_pattern in (r"(?<!\*)\*([^*\n]{1,40})\*(?!\*)", r"(?<!_)_([^_\n]{1,40})_(?!_)", r"`([^`\n]{1,40})`"):
        text = re.sub(emphasis_pattern, r"\1", text)
    text = text.translate(
        str.maketrans(
            {
                "‐": "-",
                "‑": "-",
                "‒": "-",
                "–": "-",
                "—": "-",
                "―": "-",
                "−": "-",
                "﹣": "-",
                "－": "-",
                ".": "-",
                "/": "-",
                "／": "-",
                "·": "-",
                "•": "-",
            }
        )
    )
    return text


def detect_pii(value: Any) -> list[str]:
    text = normalize_pii_text(value)
    return [label for label, pattern in PII_PATTERNS.items() if pattern.search(text)]


def find_emails(value: Any) -> set[str]:
    text = unicodedata.normalize("NFKC", json.dumps(value, ensure_ascii=False))
    return {match.group(0).lower() for match in EMAIL_PATTERN.finditer(text)}


def allowed_public_emails(data: dict[str, Any]) -> set[str]:
    allowed: set[str] = set()
    sources = data.get("sources")
    if not isinstance(sources, list):
        return allowed
    for source in sources:
        if isinstance(source, dict) and source.get("official") is True:
            contact = source.get("public_contact")
            if isinstance(contact, str):
                allowed.update(find_emails(contact))
    return allowed


def find_email_locations(value: Any, prefix: str = "") -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            found.extend(find_email_locations(child, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(find_email_locations(child, f"{prefix}[{index}]"))
    elif isinstance(value, str):
        found.extend((prefix, email) for email in find_emails(value))
    return found


def detect_unapproved_input_emails(data: dict[str, Any]) -> list[str]:
    sources = data.get("sources")
    unapproved: list[str] = []
    for path, email in find_email_locations(data):
        match = re.fullmatch(r"sources\[(\d+)\]\.public_contact", path)
        if match and isinstance(sources, list):
            index = int(match.group(1))
            if index < len(sources) and isinstance(sources[index], dict) and sources[index].get("official") is True:
                continue
        unapproved.append(f"{path}={email}")
    return sorted(unapproved)


def detect_unapproved_output_emails(text: str, allowed: set[str]) -> list[str]:
    allowed_normalized = {email.lower() for email in allowed}
    unapproved: list[str] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for email in find_emails(line):
            if "；公开联系：" in line and email.lower() in allowed_normalized:
                continue
            unapproved.append(f"line {line_number}={email}")
    return sorted(unapproved)


def require_text(obj: dict[str, Any], key: str, where: str) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        raise InputError(f"{where}.{key} 必须是非空字符串")
    return value.strip()


def require_string_list(obj: dict[str, Any], key: str, where: str) -> list[str]:
    value = obj.get(key)
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise InputError(f"{where}.{key} 必须是字符串数组")
    return [item.strip() for item in value if item.strip()]


def parse_deadline(value: Any, where: str) -> str | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise InputError(f"{where}.deadline 必须是 ISO 8601 字符串或 null")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise InputError(f"{where}.deadline 不是有效 ISO 8601 日期/时间：{value}") from exc
    if not 2000 <= parsed.year <= 2100:
        raise InputError(f"{where}.deadline 年份必须在 2000-2100 范围内")
    return value


def validate_scope_context(source: dict[str, Any], where: str) -> dict[str, Any]:
    scope = source.get("scope_context")
    if not isinstance(scope, dict):
        raise InputError(f"{where}.scope_context 必须是对象")
    year = scope.get("admission_year")
    if year is not None and (not isinstance(year, int) or not 2000 <= year <= 2100):
        raise InputError(f"{where}.scope_context.admission_year 必须是 2000-2100 的整数或 null")
    normalized: dict[str, Any] = {"admission_year": year}
    for key in ("schools", "campuses", "program_levels", "student_categories"):
        normalized[key] = require_string_list(scope, key, f"{where}.scope_context")
    if source.get("official"):
        missing = [
            key
            for key, value in normalized.items()
            if value is None or value == []
        ]
        if missing:
            raise InputError(f"{where}.scope_context 官方来源缺少：{', '.join(missing)}")
        source_text = " ".join(str(source.get(key, "")) for key in ("title", "publisher", "scope"))
        missing_school_names = [school for school in normalized["schools"] if school not in source_text]
        if missing_school_names:
            raise InputError(
                f"{where}.scope_context.schools 未在来源标题、发布主体或范围中出现："
                + ", ".join(missing_school_names)
            )
    source["scope_context"] = normalized
    return normalized


def validate_runtime(data: dict[str, Any]) -> dict[str, Any]:
    runtime = data.get("runtime")
    if not isinstance(runtime, dict):
        raise InputError("runtime 必须是对象")
    network_tool_status = runtime.get("network_tool_status")
    if network_tool_status not in NETWORK_TOOL_STATUSES:
        raise InputError("runtime.network_tool_status 不在允许列表")
    limitations = require_string_list(runtime, "limitations", "runtime")
    return {
        "network_tool_status": network_tool_status,
        "limitations": limitations,
    }


def validate_source_access(source: dict[str, Any], where: str, runtime: dict[str, Any]) -> None:
    access_method = source.get("access_method")
    authorization_status = source.get("authorization_status")
    retrieved_at = source.get("retrieved_at")
    if access_method not in ACCESS_METHODS:
        raise InputError(f"{where}.access_method 不在允许列表")
    if authorization_status not in AUTHORIZATION_STATUSES:
        raise InputError(f"{where}.authorization_status 不在允许列表")
    if retrieved_at is not None:
        if not isinstance(retrieved_at, str) or not retrieved_at.strip():
            raise InputError(f"{where}.retrieved_at 必须是 ISO 8601 字符串或 null")
        try:
            retrieved_time = datetime.fromisoformat(retrieved_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise InputError(f"{where}.retrieved_at 不是有效 ISO 8601 日期/时间") from exc
        if retrieved_time.tzinfo is None or "T" not in retrieved_at:
            raise InputError(f"{where}.retrieved_at 必须包含时间和时区")

    if access_method == "public_web":
        if authorization_status not in {"authorized", "pending", "restricted"}:
            raise InputError(f"{where} 公开网页必须记录 authorized/pending/restricted")
        if authorization_status == "authorized":
            if retrieved_at is None:
                raise InputError(f"{where} 已授权的公开网页必须记录 retrieved_at")
            if runtime["network_tool_status"] != "available_authorized":
                raise InputError(f"{where} 声称已授权联网获取，但 runtime.network_tool_status 不匹配")
        elif retrieved_at is not None:
            raise InputError(f"{where} 授权待确认或受限时 retrieved_at 必须为 null")
    else:
        if authorization_status != "not_applicable":
            raise InputError(f"{where} 用户提供/离线来源的 authorization_status 必须为 not_applicable")
        if retrieved_at is not None:
            raise InputError(f"{where} 用户提供/离线来源的 retrieved_at 必须为 null")


def source_matches_context(source: dict[str, Any], context: dict[str, Any]) -> bool:
    if not source.get("official"):
        return False
    if source["access_method"] == "public_web" and source["authorization_status"] != "authorized":
        return False
    scope = source["scope_context"]
    if scope["admission_year"] != context["admission_year"]:
        return False
    if context["school"] in {"待确认", "未知"} or context["school"] not in scope["schools"]:
        return False
    comparisons = (
        ("campuses", "campus"),
        ("program_levels", "program_level"),
        ("student_categories", "student_category"),
    )
    for scope_key, context_key in comparisons:
        actual = context[context_key]
        if actual in {"待确认", "未知"}:
            return False
        allowed = scope[scope_key]
        if SCOPE_WILDCARDS[scope_key] not in allowed and actual not in allowed:
            return False
    return True


def validate_payload(data: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    forbidden = detect_forbidden_keys(data)
    if forbidden:
        raise InputError("输入含禁止的个人信息字段：" + ", ".join(forbidden))
    pii = detect_pii(data)
    if pii:
        raise InputError("输入含需要先脱敏的数据：" + ", ".join(pii))
    unapproved_emails = detect_unapproved_input_emails(data)
    if unapproved_emails:
        raise InputError("输入含未获准的邮箱地址；个人邮箱必须脱敏，官方邮箱仅可放在官方来源 public_contact：" + ", ".join(unapproved_emails))

    context = data.get("context")
    if not isinstance(context, dict):
        raise InputError("context 必须是对象")
    for key in ("school", "campus", "program_level", "student_category", "timezone"):
        context[key] = require_text(context, key, "context")
    try:
        ZoneInfo(context["timezone"])
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise InputError("context.timezone 必须是有效的 IANA 时区，例如 Asia/Shanghai") from exc
    year = context.get("admission_year")
    if not isinstance(year, int) or not 2000 <= year <= 2100:
        raise InputError("context.admission_year 必须是 2000-2100 的整数")

    runtime = validate_runtime(data)

    sources = data.get("sources")
    if not isinstance(sources, list):
        raise InputError("sources 必须是数组")
    source_map: dict[str, dict[str, Any]] = {}
    for index, source in enumerate(sources):
        where = f"sources[{index}]"
        if not isinstance(source, dict):
            raise InputError(f"{where} 必须是对象")
        source_id = require_text(source, "id", where)
        if not ID_PATTERN.fullmatch(source_id):
            raise InputError(f"{where}.id 格式无效")
        if source_id in source_map:
            raise InputError(f"来源 ID 重复：{source_id}")
        for key in ("title", "publisher", "issued_at", "locator", "scope"):
            source[key] = require_text(source, key, where)
        try:
            datetime.fromisoformat(str(source["issued_at"]).replace("Z", "+00:00"))
        except ValueError as exc:
            raise InputError(f"{where}.issued_at 不是有效 ISO 8601 日期") from exc
        if not isinstance(source.get("official"), bool):
            raise InputError(f"{where}.official 必须是布尔值")
        public_contact = source.get("public_contact")
        if public_contact is not None:
            if not isinstance(public_contact, str) or not public_contact.strip():
                raise InputError(f"{where}.public_contact 必须是非空字符串或 null")
            if not source["official"]:
                raise InputError(f"{where}.public_contact 只允许用于已核验的官方来源")
            source["public_contact"] = public_contact.strip()
        validate_source_access(source, where, runtime)
        validate_scope_context(source, where)
        source_map[source_id] = source

    items = data.get("items")
    if not isinstance(items, list) or not items:
        raise InputError("items 必须是至少含一项的数组")
    item_ids: set[str] = set()
    normalized_items: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        where = f"items[{index}]"
        if not isinstance(item, dict):
            raise InputError(f"{where} 必须是对象")
        item_id = require_text(item, "id", where)
        if not ID_PATTERN.fullmatch(item_id):
            raise InputError(f"{where}.id 格式无效")
        if item_id in item_ids:
            raise InputError(f"事项 ID 重复：{item_id}")
        item_ids.add(item_id)
        item["title"] = require_text(item, "title", where)
        if item.get("category") not in CATEGORIES:
            raise InputError(f"{where}.category 不在允许列表")
        if item.get("stage") not in STAGES:
            raise InputError(f"{where}.stage 不在允许列表")
        if item.get("requirement") not in REQUIREMENTS:
            raise InputError(f"{where}.requirement 不在允许列表")
        if item.get("evidence_status") not in STATUSES:
            raise InputError(f"{where}.evidence_status 不在允许列表")
        if item.get("risk_level") not in RISK_LEVELS:
            raise InputError(f"{where}.risk_level 不在允许列表")
        item["applies_to"] = require_text(item, "applies_to", where)
        item["deadline"] = parse_deadline(item.get("deadline"), where)
        location = item.get("location")
        if location is not None and not isinstance(location, str):
            raise InputError(f"{where}.location 必须是字符串或 null")
        if isinstance(location, str):
            item["location"] = location.strip()
        for key in ("materials", "actions", "prerequisites", "source_ids"):
            item[key] = require_string_list(item, key, where)
        for key in ("completion_evidence", "fallback", "notes"):
            if not isinstance(item.get(key), str):
                raise InputError(f"{where}.{key} 必须是字符串")
            item[key] = item[key].strip()
        unknown_sources = [source_id for source_id in item["source_ids"] if source_id not in source_map]
        if unknown_sources:
            raise InputError(f"{where}.source_ids 引用了未知来源：{', '.join(unknown_sources)}")
        if item["evidence_status"] == "confirmed":
            if not item["source_ids"]:
                raise InputError(f"{where} 标为 confirmed 但没有来源")
            if not any(source_matches_context(source_map[source_id], context) for source_id in item["source_ids"]):
                raise InputError(f"{where} 标为 confirmed 但没有适用范围匹配的官方来源")
        if item["requirement"] == "required" and item["evidence_status"] != "not_applicable":
            if not item["actions"] or not item["completion_evidence"] or not item["fallback"]:
                raise InputError(f"{where} 为必做事项，必须填写 actions、completion_evidence 和 fallback")
        if item["requirement"] == "conditional" and item["applies_to"] in {"待确认", "未知"}:
            if item["evidence_status"] != "to_verify":
                warnings.append(f"{item_id} 的适用条件未明确，状态应保持待确认")
        if item["deadline"] and item["evidence_status"] not in {"confirmed", "user_provided"}:
            warnings.append(f"{item_id} 的日期尚未得到足够证据确认")
        normalized_items.append(item)

    unknown_context = [
        key
        for key in ("campus", "program_level", "student_category")
        if context[key] in {"待确认", "未知"}
    ]
    if unknown_context and any(item["evidence_status"] == "confirmed" for item in normalized_items):
        warnings.append("存在已确认事项，但关键适用范围仍待确认：" + ", ".join(unknown_context))

    assumptions = data.get("assumptions", [])
    conflicts = data.get("conflicts", [])
    if not isinstance(assumptions, list) or any(not isinstance(item, str) for item in assumptions):
        raise InputError("assumptions 必须是字符串数组")
    if not isinstance(conflicts, list) or any(not isinstance(item, str) for item in conflicts):
        raise InputError("conflicts 必须是字符串数组")

    normalized = {
        "context": context,
        "runtime": runtime,
        "sources": sources,
        "source_map": source_map,
        "items": normalized_items,
        "assumptions": [item.strip() for item in assumptions if item.strip()],
        "conflicts": [item.strip() for item in conflicts if item.strip()],
    }
    return normalized, warnings


def item_sort_key(item: dict[str, Any], timezone_name: str) -> tuple[int, float, str]:
    stage_order = STAGES[item["stage"]][0]
    if item["deadline"] is None:
        deadline_utc = float("inf")
    else:
        deadline = datetime.fromisoformat(item["deadline"].replace("Z", "+00:00"))
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=ZoneInfo(timezone_name))
        deadline_utc = deadline.astimezone(timezone.utc).timestamp()
    return stage_order, deadline_utc, item["id"]


def bullet_lines(values: list[str], empty_text: str = "无") -> str:
    if not values:
        return empty_text
    return "；".join(clean_inline(value) for value in values)


def clean_inline(value: Any, *, table: bool = False) -> str:
    text = " ".join(str(value).splitlines()).strip()
    text = text.replace("<", "&lt;").replace(">", "&gt;")
    if table:
        text = text.replace("|", "\\|")
    return text


def render_markdown(payload: dict[str, Any], source_hash: str, warnings: list[str]) -> str:
    context = payload["context"]
    runtime = payload["runtime"]
    items = sorted(payload["items"], key=lambda item: item_sort_key(item, context["timezone"]))
    counts = Counter(item["evidence_status"] for item in items)
    confirmed_count = counts.get("confirmed", 0)
    pending_count = counts.get("to_verify", 0) + counts.get("user_provided", 0)
    first_action = clean_inline(next((item["actions"][0] for item in items if item["actions"]), "补充官方报到资料"))

    gaps: list[str] = []
    for key, label in (("campus", "校区"), ("program_level", "培养层次"), ("student_category", "学生类别")):
        if context[key] in {"待确认", "未知"}:
            gaps.append(f"{label}待确认")
    gaps.extend(f"{item['title']}：证据状态为{STATUS_LABELS[item['evidence_status']]}" for item in items if item["evidence_status"] in {"to_verify", "user_provided"})
    gaps.extend(payload["conflicts"])
    gaps.extend(warnings)

    lines = [
        "# 新生报到执行清单",
        "",
        "## 适用范围与结论",
        "",
        f"- 学校：{clean_inline(context['school'])}",
        f"- 校区：{clean_inline(context['campus'])}",
        f"- 入学年份：{context['admission_year']}",
        f"- 培养层次：{clean_inline(context['program_level'])}",
        f"- 学生类别：{clean_inline(context['student_category'])}",
        f"- 输入指纹：`sha256:{source_hash}`",
        "",
        f"基于当前来源，已整理 {len(items)} 项报到事项，其中已确认 {confirmed_count} 项、仍需核验 {pending_count} 项；最先需要完成的是“{first_action}”。",
        "",
        "## 关键缺口",
        "",
    ]
    if gaps:
        lines.extend(f"- {clean_inline(gap)}" for gap in gaps)
    else:
        lines.append("- 当前结构化输入未发现关键缺口；仍应在执行前复核官方通知是否更新。")

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        grouped[item["stage"]].append(item)
    lines.extend(["", "## 分阶段执行清单", ""])
    for stage in sorted(grouped, key=lambda value: STAGES[value][0]):
        lines.extend([f"### {STAGES[stage][1]}", ""])
        for item in grouped[stage]:
            status_label = STATUS_LABELS[item["evidence_status"]]
            req_label = REQUIREMENT_LABELS[item["requirement"]]
            checkbox = "x" if item["evidence_status"] == "not_applicable" else " "
            deadline = item["deadline"] or "待确认/未规定"
            location = item["location"] or "待确认/线上"
            lines.extend(
                [
                    f"<!-- item:{item['id']} -->",
                    f"- [{checkbox}] **[{status_label}] {clean_inline(item['title'])}**",
                    f"  - 要求类型：{req_label}",
                    f"  - 适用对象：{clean_inline(item['applies_to'])}",
                    f"  - 截止时间：{deadline}",
                    f"  - 地点/入口：{clean_inline(location)}",
                    f"  - 材料：{bullet_lines(item['materials'])}",
                    f"  - 前置条件：{bullet_lines(item['prerequisites'])}",
                    f"  - 下一动作：{bullet_lines(item['actions'])}",
                    f"  - 完成证据：{clean_inline(item['completion_evidence'] or '待确认')}",
                    f"  - 失败备选：{clean_inline(item['fallback'] or '联系通知指定的官方部门')}",
                    f"  - 风险等级：{item['risk_level']}",
                    f"  - 来源：{', '.join(item['source_ids']) if item['source_ids'] else '待确认'}",
                    f"  - 说明：{clean_inline(item['notes'] or '无')}",
                    "",
                ]
            )

    material_rows: dict[str, set[str]] = defaultdict(set)
    for item in items:
        if item["evidence_status"] == "not_applicable":
            continue
        for material in item["materials"]:
            material_rows[material].add(item["id"])
    lines.extend(["## 材料总表", "", "| 材料 | 用途事项 | 份数 | 状态 | 来源 |", "| --- | --- | --- | --- | --- |"])
    if material_rows:
        for material in sorted(material_rows):
            related = [item for item in items if item["id"] in material_rows[material]]
            statuses = "/".join(sorted({STATUS_LABELS[item["evidence_status"]] for item in related}))
            sources = sorted({source_id for item in related for source_id in item["source_ids"]})
            lines.append(f"| {clean_inline(material, table=True)} | {', '.join(sorted(material_rows[material]))} | 待确认/按原文 | {statuses} | {', '.join(sources) or '待确认'} |")
    else:
        lines.append("| 暂无已录入材料 | — | — | 待确认 | — |")

    lines.extend(["", "## 冲突与待确认项", ""])
    conflict_lines = payload["conflicts"] + [item["title"] for item in items if item["evidence_status"] in {"to_verify", "user_provided"}]
    if conflict_lines:
        lines.extend(f"- {clean_inline(value)}" for value in conflict_lines)
    else:
        lines.append("- 当前未记录来源冲突；执行前仍需检查是否发布补充通知。")

    lines.extend(["", "## 来源台账", ""])
    if payload["sources"]:
        for source in payload["sources"]:
            official = "官方" if source["official"] else "非官方/待核验"
            public_contact = source.get("public_contact")
            contact_text = f"；公开联系：{clean_inline(public_contact)}" if public_contact else ""
            access_method = ACCESS_METHOD_LABELS[source["access_method"]]
            authorization = AUTHORIZATION_STATUS_LABELS[source["authorization_status"]]
            retrieved_at = source["retrieved_at"] or "未联网获取"
            lines.append(f"- **{source['id']}｜{clean_inline(source['title'])}**：{clean_inline(source['publisher'])}，{source['issued_at']}，{official}；适用范围：{clean_inline(source['scope'])}；定位：{clean_inline(source['locator'])}；获取：{access_method}；授权：{authorization}；获取时间：{retrieved_at}{contact_text}")
    else:
        lines.append("- 暂无来源；当前清单只能作为通用准备框架。")

    lines.extend(["", "## Tool 与数据授权状态", ""])
    lines.append(f"- 联网 Tool：{NETWORK_TOOL_STATUS_LABELS[runtime['network_tool_status']]}")
    if runtime["limitations"]:
        lines.extend(f"- 限制：{clean_inline(value)}" for value in runtime["limitations"])
    else:
        lines.append("- 限制：未记录额外限制。")
    for source in payload["sources"]:
        lines.append(
            f"- 来源 {source['id']}：{ACCESS_METHOD_LABELS[source['access_method']]}，"
            f"{AUTHORIZATION_STATUS_LABELS[source['authorization_status']]}，"
            f"{source['retrieved_at'] or '未联网获取'}"
        )

    lines.extend(["", "## 隐私与使用限制", ""])
    lines.extend(
        [
            "- 本清单不保存账号、密码、验证码、证件号码、银行卡号或其他非必要个人信息。",
            "- 动态安排以适用年度、校区和学生类别的学校官方通知为准。",
            "- 本清单用于信息整理和行动提示，不代替学校审核，也不保证报到、资助、户口迁移或其他申请结果。",
            "",
        ]
    )
    return "\n".join(lines)


def write_text(path: Path, content: str, force: bool) -> None:
    if path.exists() and not force:
        raise OSError(f"输出已存在：{path}；如确认替换请使用 --force")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def preflight_outputs(paths: list[Path], force: bool) -> None:
    if force:
        return
    existing = [str(path) for path in paths if path.exists()]
    if existing:
        raise OSError("输出已存在：" + ", ".join(existing) + "；如确认替换请使用 --force")


def main() -> int:
    args = parse_args()
    try:
        ensure_distinct_paths(args.input, args.output, args.summary)
        data, raw = read_json(args.input)
        payload, warnings = validate_payload(data)
        source_hash = hashlib.sha256(raw).hexdigest()
        markdown = render_markdown(payload, source_hash, warnings)
        summary = {
            "ok": True,
            "input_sha256": source_hash,
            "item_count": len(payload["items"]),
            "status_counts": dict(Counter(item["evidence_status"] for item in payload["items"])),
            "warning_count": len(warnings),
            "warnings": warnings,
        }
        preflight_outputs([path for path in (args.output, args.summary) if path is not None], args.force)
        write_text(args.output, markdown, args.force)
        if args.summary is not None:
            write_text(args.summary, json.dumps(summary, ensure_ascii=False, indent=2) + "\n", args.force)
    except InputError as exc:
        print(f"INPUT_ERROR: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"IO_ERROR: {exc}", file=sys.stderr)
        return 3
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
