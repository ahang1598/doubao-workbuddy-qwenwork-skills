#!/usr/bin/env python3
"""Validate a will and estate-planning case and its workflow gates."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

from evaluate_rules import evaluate_rules, load_rule_pack
from intake_runtime import AI_FILE_NOTICE, reconcile_coverage


SCHEMA_VERSION = "0.5.1"
TEMPLATE_SHA256 = "c8398bc4050b4bb640b7cc8e15f762ce223c6b5cbc76bda5a8f444e8f954558c"
ID_PATTERN = re.compile(r"^[a-z][a-z0-9-]{2,63}$")
ARRAY_SECTIONS = (
    "people", "relationships", "assets", "liabilities", "existing_documents",
    "intentions", "evidence", "issues", "confirmations",
)
PROVENANCE_SECTIONS = ("people", "relationships", "assets", "liabilities", "existing_documents", "intentions")
RESEARCH_GATE_STATUSES = {"research_verified", "ready_for_output", "output_generated"}
OUTPUT_GATE_STATUSES = {"ready_for_output", "output_generated"}
ALL_STATUSES = {
    "audience_selecting", "intake_cards", "information_incomplete", "user_confirming",
    "researching", "research_blocked", "research_verified", "review_required",
    "ready_for_output", "output_generated",
}
ISSUE_LEVELS = {"BLOCKED", "REVIEW_REQUIRED", "WARN", "INFO", "PASS"}
ISSUE_STATUSES = {"open", "resolved", "accepted", "not_applicable"}
CONFIRMATION_STATUSES = {"pending_confirmation", "confirmed", "disputed", "unknown", "not_applicable"}
WILL_SECTION_KEYS = (
    "declarations", "legal_heirs", "estate_distribution", "executor",
    "guardianship", "minor_guardianship", "other",
)
CARD_DECK_ID = "will-intake-v3"
CARD_DECK_VERSION = "4.0.0"
CARD_LIBRARY_IDS = {
    "actor-authority", "lawyer-privacy-consent",
    "testator-basic-info", "testator-capacity",
    "family-map", "guardianship-special",
    "asset-declaration", "liability-scope",
    "existing-arrangements", "distribution-goals", "estate-distribution",
    "will-form-and-witnesses", "executor-custody",
    "deliverable-selection", "intake-confirmation",
    "fast-persons-enumeration", "fast-assets-enumeration",
    "fast-distribution-enumeration", "fast-assumptions-correction",
    "lawyer-sheet-intake",
}
COLLECTION_MODES = {"fast", "complete", "lawyer_sheet"}
CORE_DELIVERABLES = {
    "will_docx", "execution_guide",
}
INHERITANCE_REVIEW_ENUMS = {
    "heir_scope_status": {"complete", "incomplete", "unknown"},
    "fetal_share_treatment": {"not_applicable", "reserved", "professional_reviewed", "not_addressed"},
    "disqualification_status": {"none", "reported", "unknown"},
    "disqualification_review_status": {"not_applicable", "reviewed", "not_reviewed", "unknown"},
    "legatee_acceptance_status": {"not_applicable", "planned", "not_planned", "unknown"},
    "attached_obligation_review_status": {"not_applicable", "reviewed", "not_reviewed", "unknown"},
    "lapse_and_residuary_status": {"reviewed", "not_reviewed", "unknown"},
    "coownership_review_status": {"not_applicable", "reviewed", "not_reviewed", "unknown"},
    "administrator_consent_status": {"confirmed", "not_confirmed", "unknown"},
    "administrator_terms_status": {"covered", "incomplete", "unknown"},
    "debt_inventory_status": {"complete", "incomplete", "unknown"},
    "tax_review_status": {"not_applicable", "reviewed", "not_reviewed", "unknown"},
    "insurance_review_status": {"not_applicable", "reviewed", "not_reviewed", "unknown"},
    "guardianship_review_status": {"not_applicable", "reviewed", "not_reviewed", "unknown"},
    "complex_asset_types": {"none", "reported", "unknown"},
    "complex_asset_routing_status": {"not_applicable", "routed", "not_routed", "unknown"},
}


def _load_deck_contracts() -> dict[str, Any]:
    deck_path = Path(__file__).resolve().parents[1] / "assets" / "cards" / "intake-card-deck.json"
    try:
        deck = json.loads(deck_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"vocab": {}, "field_cards": {}, "field_vocab": {}, "conditional": {}}
    vocab: dict[str, set[str]] = {}
    field_cards: dict[str, list[str]] = {}
    field_vocab: dict[str, dict[str, set[str]]] = {}
    conditional: dict[str, dict[str, list[str]]] = {}

    def collect_options(node: Any, values: set[str]) -> None:
        if isinstance(node, dict):
            options = node.get("options")
            if isinstance(options, list):
                for option in options:
                    if isinstance(option, dict) and isinstance(option.get("value"), str):
                        values.add(option["value"])
            for extra in node.get("other_value_parsing") or []:
                if isinstance(extra, str):
                    values.add(extra)
            for value in node.values():
                collect_options(value, values)
        elif isinstance(node, list):
            for item in node:
                collect_options(item, values)

    for card in deck.get("cards", []):
        base_id = card.get("base_card_id")
        if not isinstance(base_id, str):
            continue
        values: set[str] = set()
        collect_options(card, values)
        vocab[base_id] = values
        if card.get("response_mode") == "field_values" and isinstance(card.get("fields"), list):
            field_cards[base_id] = [
                field.get("field_id") for field in card["fields"]
                if isinstance(field, dict) and isinstance(field.get("field_id"), str)
            ]
            field_vocab[base_id] = {}
            for field in card["fields"]:
                if not isinstance(field, dict) or not isinstance(field.get("field_id"), str):
                    continue
                values = {
                    option.get("value") for option in (field.get("ask") or {}).get("options") or []
                    if isinstance(option, dict) and isinstance(option.get("value"), str)
                }
                if values:
                    field_vocab[base_id][field["field_id"]] = values
        if card.get("kind") == "conditional" and isinstance(card.get("conditional_fields"), dict):
            conditional[base_id] = {
                form: [
                    field.get("field_id") for field in fields
                    if isinstance(field, dict) and isinstance(field.get("field_id"), str)
                ]
                for form, fields in card["conditional_fields"].items()
                if isinstance(fields, list)
            }
    return {"vocab": vocab, "field_cards": field_cards, "field_vocab": field_vocab, "conditional": conditional}


DECK_CONTRACTS = _load_deck_contracts()


def _resolve_base_card(card_id: str) -> str | None:
    """Resolve a card id to its library base id; repeatable instances use '<base>-<suffix>'."""
    if card_id in CARD_LIBRARY_IDS:
        return card_id
    candidates = [base for base in CARD_LIBRARY_IDS if card_id.startswith(base + "-")]
    return max(candidates, key=len) if candidates else None
OPTIONAL_DELIVERABLES = {"asset_inventory", "relationship_diagram", "legal_research_report", "education_content"}
OFFICIAL_LAW_DOMAINS = (
    "flk.npc.gov.cn", "npc.gov.cn", "www.npc.gov.cn", "gov.cn", "www.gov.cn",
    "court.gov.cn", "www.court.gov.cn", "moj.gov.cn", "www.moj.gov.cn",
)
OFFICIAL_CASE_DOMAINS = (
    "rmfyalk.court.gov.cn", "court.gov.cn", "www.court.gov.cn",
    "wenshu.court.gov.cn", "gongbao.court.gov.cn",
)
LEVEL_ORDER = {"error": 0, "warning": 1, "info": 2}


@dataclass(frozen=True)
class Message:
    level: str
    code: str
    path: str
    message: str


def _msg(level: str, code: str, path: str, message: str) -> Message:
    return Message(level, code, path, message)


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _records(case: dict[str, Any], section: str) -> Iterable[tuple[int, dict[str, Any]]]:
    for index, item in enumerate(_as_list(case.get(section))):
        if isinstance(item, dict):
            yield index, item


def _valid_https(url: Any) -> bool:
    if not isinstance(url, str):
        return False
    parsed = urlparse(url)
    return parsed.scheme == "https" and bool(parsed.netloc)


def _host_allowed(url: str, allowed: tuple[str, ...]) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == domain or host.endswith("." + domain) for domain in allowed)


def _parse_date(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value[:10]).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def validate_case(case: Any) -> dict[str, Any]:
    messages: list[Message] = []
    if not isinstance(case, dict):
        return _report([_msg("error", "ROOT_NOT_OBJECT", "$", "案件根节点必须是 JSON 对象。")])

    required = {
        "schema_version", "work_id", "status", "baseline_at",
        "audience_profile", "intake_session", "subject", "testator_basic_info", "testator_capacity", "will_execution_plan", "reserved_share_review", "inheritance_review", *ARRAY_SECTIONS, "consent",
        "legal_research", "rule_context", "will_document", "deliverables",
        "output_preferences",
    }
    for key in sorted(required - set(case)):
        messages.append(_msg("error", "MISSING_TOP_LEVEL", f"$.{key}", "缺少必需顶层字段。"))
    for key in sorted(set(case) - required):
        messages.append(_msg("error", "UNKNOWN_TOP_LEVEL", f"$.{key}", "存在 Schema 未定义的顶层字段。"))

    if case.get("schema_version") != SCHEMA_VERSION:
        messages.append(_msg("error", "UNSUPPORTED_SCHEMA_VERSION", "$.schema_version", f"仅支持 Schema {SCHEMA_VERSION}。"))
    work_id = case.get("work_id")
    if not isinstance(work_id, str) or not ID_PATTERN.fullmatch(work_id):
        messages.append(_msg("error", "INVALID_WORK_ID", "$.work_id", "本次工作 ID 必须为 3-64 位小写字母、数字或连字符。"))
    elif re.search(r"\d{11}|\d{17}[\dXx]", work_id):
        messages.append(_msg("warning", "SENSITIVE_WORK_ID", "$.work_id", "工作 ID 疑似包含电话或证件号码。"))
    if case.get("status") not in ALL_STATUSES:
        messages.append(_msg("error", "INVALID_CASE_STATUS", "$.status", "案件状态不受支持。"))
    _validate_audience_and_intake(case, messages)

    section_ids: dict[str, set[str]] = {section: set() for section in ARRAY_SECTIONS}
    all_ids: dict[str, str] = {}
    for section in ARRAY_SECTIONS:
        value = case.get(section)
        if not isinstance(value, list):
            messages.append(_msg("error", "SECTION_NOT_ARRAY", f"$.{section}", "该字段必须为数组。"))
            continue
        for index, item in enumerate(value):
            path = f"$.{section}[{index}]"
            if not isinstance(item, dict):
                messages.append(_msg("error", "RECORD_NOT_OBJECT", path, "数组记录必须为对象。"))
                continue
            record_id = item.get("id")
            if not isinstance(record_id, str) or not ID_PATTERN.fullmatch(record_id):
                messages.append(_msg("error", "INVALID_ENTITY_ID", f"{path}.id", "实体 ID 格式无效。"))
                continue
            if record_id in all_ids:
                messages.append(_msg("error", "DUPLICATE_ENTITY_ID", f"{path}.id", f"ID 与 {all_ids[record_id]} 重复。"))
            else:
                all_ids[record_id] = path
                section_ids[section].add(record_id)

    person_ids = section_ids["people"]
    asset_ids = section_ids["assets"]
    subject = case.get("subject")
    if not isinstance(subject, dict) or subject.get("person_id") not in person_ids:
        messages.append(_msg("error", "UNKNOWN_SUBJECT", "$.subject.person_id", "办理主体未引用有效人物。"))

    basic = case.get("testator_basic_info")
    if not isinstance(basic, dict) or basic.get("source_card_id") != "testator-basic-info":
        messages.append(_msg("error", "INVALID_TESTATOR_BASIC_INFO", "$.testator_basic_info", "遗嘱人姓名、性别、出生日期、身份证号码和住址必须来自基本信息表单或经汇总确认的材料提取。"))
    elif basic.get("confirmation_status") != "confirmed" or not basic.get("confirmed_at"):
        messages.append(_msg("error", "TESTATOR_BASIC_INFO_NOT_CONFIRMED", "$.testator_basic_info", "遗嘱人基本信息尚未确认。"))

    capacity = case.get("testator_capacity")
    if not isinstance(capacity, dict):
        messages.append(_msg("error", "INVALID_TESTATOR_CAPACITY", "$.testator_capacity", "遗嘱人行为能力与表达情况必须独立记录。"))
    else:
        if capacity.get("reported_status") not in {"no_concern_reported", "communication_support_needed", "concern_reported", "unknown"}:
            messages.append(_msg("error", "INVALID_CAPACITY_STATUS", "$.testator_capacity.reported_status", "行为能力与表达情况记录值无效。"))
        if capacity.get("source_card_id") != "testator-capacity":
            messages.append(_msg("error", "CAPACITY_CARD_SOURCE_MISMATCH", "$.testator_capacity.source_card_id", "行为能力信息必须来自独立的 testator-capacity 卡片。"))
        for index, evidence_id in enumerate(_as_list(capacity.get("supporting_evidence_ids"))):
            if evidence_id not in section_ids["evidence"]:
                messages.append(_msg("error", "UNKNOWN_CAPACITY_EVIDENCE", f"$.testator_capacity.supporting_evidence_ids[{index}]", "行为能力记录引用的证据不存在。"))

    execution = case.get("will_execution_plan")
    if not isinstance(execution, dict):
        messages.append(_msg("error", "INVALID_WILL_EXECUTION_PLAN", "$.will_execution_plan", "必须记录遗嘱形式与签署/见证安排。"))
    else:
        witness_ids: list[str] = []
        for index, witness in enumerate(_as_list(execution.get("witnesses"))):
            if not isinstance(witness, dict) or witness.get("person_id") not in person_ids:
                messages.append(_msg("error", "UNKNOWN_WITNESS", f"$.will_execution_plan.witnesses[{index}].person_id", "见证人必须引用有效人物。"))
            elif isinstance(witness.get("person_id"), str):
                witness_ids.append(witness["person_id"])
        if len(witness_ids) != len(set(witness_ids)):
            messages.append(_msg("error", "DUPLICATE_WITNESS", "$.will_execution_plan.witnesses", "同一人员不得重复计为多名见证人。"))

    reserved = case.get("reserved_share_review")
    if not isinstance(reserved, dict):
        messages.append(_msg("error", "INVALID_RESERVED_SHARE_REVIEW", "$.reserved_share_review", "必须记录必要份额排查。"))
    else:
        for index, person_id in enumerate(_as_list(reserved.get("candidate_person_ids"))):
            if person_id not in person_ids:
                messages.append(_msg("error", "UNKNOWN_RESERVED_SHARE_PERSON", f"$.reserved_share_review.candidate_person_ids[{index}]", "必要份额候选人不存在。"))

    inheritance = case.get("inheritance_review")
    if not isinstance(inheritance, dict):
        messages.append(_msg("error", "INVALID_INHERITANCE_REVIEW", "$.inheritance_review", "继承人、析产、遗赠、管理、债务和复杂资产复核必须形成结构化记录。"))
    else:
        missing = set(INHERITANCE_REVIEW_ENUMS) - set(inheritance)
        unknown = set(inheritance) - set(INHERITANCE_REVIEW_ENUMS)
        if missing:
            messages.append(_msg("error", "INHERITANCE_REVIEW_INCOMPLETE", "$.inheritance_review", f"专项复核缺少字段：{', '.join(sorted(missing))}。"))
        if unknown:
            messages.append(_msg("error", "INHERITANCE_REVIEW_UNKNOWN_FIELD", "$.inheritance_review", f"专项复核包含未知字段：{', '.join(sorted(unknown))}。"))
        for key, allowed in INHERITANCE_REVIEW_ENUMS.items():
            if key in inheritance and inheritance[key] not in allowed:
                messages.append(_msg("error", "INHERITANCE_REVIEW_VALUE_UNKNOWN", f"$.inheritance_review.{key}", f"专项复核值不受支持：{inheritance[key]}。"))

    for section in PROVENANCE_SECTIONS:
        for index, record in _records(case, section):
            provenance = record.get("provenance")
            path = f"$.{section}[{index}].provenance"
            if not isinstance(provenance, dict):
                messages.append(_msg("error", "MISSING_PROVENANCE", path, "关键实体必须记录来源和确认状态。"))
                continue
            source = provenance.get("source")
            if not isinstance(source, dict) or not source.get("type") or not source.get("reference"):
                messages.append(_msg("error", "INVALID_SOURCE", f"{path}.source", "来源必须包含 type 和 reference。"))
            if provenance.get("confirmation_status") not in CONFIRMATION_STATUSES:
                messages.append(_msg("error", "INVALID_CONFIRMATION_STATUS", f"{path}.confirmation_status", "确认状态无效。"))

    for index, relation in _records(case, "relationships"):
        path = f"$.relationships[{index}]"
        if relation.get("from_person_id") not in person_ids:
            messages.append(_msg("error", "UNKNOWN_RELATIONSHIP_SOURCE", f"{path}.from_person_id", "关系起点不存在。"))
        if relation.get("to_person_id") not in person_ids:
            messages.append(_msg("error", "UNKNOWN_RELATIONSHIP_TARGET", f"{path}.to_person_id", "关系终点不存在。"))
        if relation.get("from_person_id") == relation.get("to_person_id"):
            messages.append(_msg("error", "SELF_RELATIONSHIP", path, "关系不能指向同一人物。"))

    for index, asset in _records(case, "assets"):
        path = f"$.assets[{index}]"
        owners = asset.get("owners")
        if not isinstance(owners, list):
            messages.append(_msg("error", "OWNERS_NOT_ARRAY", f"{path}.owners", "资产 owners 必须为数组。"))
            continue
        if not owners:
            messages.append(_msg("warning", "ASSET_WITHOUT_OWNER", f"{path}.owners", "资产尚未记录权属主体。"))
        seen: set[str] = set()
        total = 0.0
        for owner_index, owner in enumerate(owners):
            owner_path = f"{path}.owners[{owner_index}]"
            if not isinstance(owner, dict):
                messages.append(_msg("error", "OWNER_NOT_OBJECT", owner_path, "权属记录必须为对象。"))
                continue
            person_id = owner.get("person_id")
            if person_id not in person_ids:
                messages.append(_msg("error", "UNKNOWN_ASSET_OWNER", f"{owner_path}.person_id", "资产权属主体不存在。"))
            if person_id in seen:
                messages.append(_msg("error", "DUPLICATE_ASSET_OWNER", owner_path, "同一资产中权属主体重复。"))
            seen.add(person_id)
            share = owner.get("share_percent")
            if share is not None:
                if isinstance(share, bool) or not isinstance(share, (int, float)) or not 0 <= share <= 100:
                    messages.append(_msg("error", "INVALID_OWNERSHIP_SHARE", f"{owner_path}.share_percent", "权属比例必须为 0-100 或 null。"))
                else:
                    total += float(share)
        if total > 100.000001:
            messages.append(_msg("error", "OWNERSHIP_OVER_100", f"{path}.owners", "已知权属比例合计超过 100%。"))
        if asset.get("arrangement_status") in {"not_started", "partial", "unknown"}:
            messages.append(_msg("info", "ASSET_NOT_FULLY_ARRANGED", path, "资产安排尚未完全覆盖。"))

    for index, liability in _records(case, "liabilities"):
        for ref_index, asset_id in enumerate(_as_list(liability.get("related_asset_ids"))):
            if asset_id not in asset_ids:
                messages.append(_msg("error", "UNKNOWN_LIABILITY_ASSET", f"$.liabilities[{index}].related_asset_ids[{ref_index}]", "债务引用的资产不存在。"))
    for index, intention in _records(case, "intentions"):
        for ref_index, person_id in enumerate(_as_list(intention.get("related_person_ids"))):
            if person_id not in person_ids:
                messages.append(_msg("error", "UNKNOWN_INTENTION_PERSON", f"$.intentions[{index}].related_person_ids[{ref_index}]", "意愿引用的人物不存在。"))
        for ref_index, asset_id in enumerate(_as_list(intention.get("related_asset_ids"))):
            if asset_id not in asset_ids:
                messages.append(_msg("error", "UNKNOWN_INTENTION_ASSET", f"$.intentions[{index}].related_asset_ids[{ref_index}]", "意愿引用的资产不存在。"))
    for section in ("evidence", "issues", "confirmations"):
        for index, record in _records(case, section):
            for ref_index, related_id in enumerate(_as_list(record.get("related_ids"))):
                if related_id not in all_ids:
                    messages.append(_msg("error", "UNKNOWN_GENERIC_REFERENCE", f"$.{section}[{index}].related_ids[{ref_index}]", "引用实体不存在。"))
    for index, confirmation in _records(case, "confirmations"):
        if confirmation.get("confirmed_by") not in person_ids:
            messages.append(_msg("error", "UNKNOWN_CONFIRMER", f"$.confirmations[{index}].confirmed_by", "确认人不存在。"))
    for index, issue in _records(case, "issues"):
        if issue.get("level") not in ISSUE_LEVELS:
            messages.append(_msg("error", "INVALID_ISSUE_LEVEL", f"$.issues[{index}].level", "问题级别不受支持。"))
        if issue.get("status") not in ISSUE_STATUSES:
            messages.append(_msg("error", "INVALID_ISSUE_STATUS", f"$.issues[{index}].status", "问题状态不受支持。"))

    _validate_consent(case, messages)
    _validate_research(case, messages)
    _validate_rule_context(case, messages)
    _validate_output_gate(case, messages)

    if not person_ids:
        messages.append(_msg("error", "NO_PEOPLE", "$.people", "案件至少需要一名人物。"))
    if not asset_ids:
        messages.append(_msg("warning", "NO_ASSETS", "$.assets", "尚未记录任何资产。"))
    if not section_ids["intentions"]:
        messages.append(_msg("warning", "NO_INTENTIONS", "$.intentions", "尚未记录任何安排意愿。"))
    return _report(messages)


def _validate_audience_and_intake(case: dict[str, Any], messages: list[Message]) -> None:
    profile = case.get("audience_profile")
    if not isinstance(profile, dict):
        messages.append(_msg("error", "INVALID_AUDIENCE_PROFILE", "$.audience_profile", "用户类型必须为对象。"))
        return
    audience = profile.get("audience_type")
    language = profile.get("language_profile")
    if audience not in {"lawyer", "general_public"}:
        messages.append(_msg("error", "INVALID_AUDIENCE_TYPE", "$.audience_profile.audience_type", "用户类型仅支持 lawyer 或 general_public。"))
    expected = {"lawyer": "professional", "general_public": "plain"}.get(audience)
    if expected and language != expected:
        messages.append(_msg("error", "AUDIENCE_LANGUAGE_MISMATCH", "$.audience_profile.language_profile", f"{audience} 必须使用 {expected}。"))
    if profile.get("selected_via_card_id") not in {"audience-type", "mode-selection"} or profile.get("confirmed") is not True:
        messages.append(_msg("error", "AUDIENCE_CARD_NOT_CONFIRMED", "$.audience_profile", "用户类型必须由模式选择派生或身份卡确认。"))

    intake = case.get("intake_session")
    if not isinstance(intake, dict) or not isinstance(intake.get("card_responses"), list):
        messages.append(_msg("error", "INVALID_INTAKE_SESSION", "$.intake_session", "访谈会话或卡片响应无效。"))
        return
    if intake.get("deck_id") != CARD_DECK_ID or intake.get("deck_version") != CARD_DECK_VERSION:
        messages.append(_msg("error", "CARD_DECK_MISMATCH", "$.intake_session", "案件未绑定受支持的完整卡片集。"))
    if intake.get("navigation_mode") != "mode_routed_batched":
        messages.append(_msg("error", "INVALID_CARD_NAVIGATION", "$.intake_session.navigation_mode", "卡片必须按卡组确定性推进（fast/complete/lawyer_sheet 模式路由），不得由模型逐题临时生成。"))
    if intake.get("collection_mode") is not None and intake.get("collection_mode") not in COLLECTION_MODES:
        messages.append(_msg("error", "INVALID_COLLECTION_MODE", "$.intake_session.collection_mode", "采集模式仅支持 fast / complete / lawyer_sheet。"))
    if intake.get("collection_mode") == "lawyer_sheet" and case.get("audience_profile", {}).get("audience_type") != "lawyer":
        messages.append(_msg("error", "LAWYER_SHEET_REQUIRES_LAWYER", "$.intake_session.collection_mode", "律师信息表快速通道仅限律师用户使用。"))

    required_ids = set(_as_list(intake.get("required_card_ids")))
    skipped_ids = set(_as_list(intake.get("skipped_base_card_ids")))
    if not all(_resolve_base_card(card_id) for card_id in required_ids):
        messages.append(_msg("error", "UNKNOWN_REQUIRED_CARD", "$.intake_session.required_card_ids", "编译后的卡片队列包含未知卡片（可重复实例须以卡组基础 ID 为前缀）。"))
    if not all(_resolve_base_card(card_id) for card_id in skipped_ids):
        messages.append(_msg("error", "UNKNOWN_SKIPPED_CARD", "$.intake_session.skipped_base_card_ids", "材料覆盖评估包含未知跳过卡片。"))
    if required_ids & skipped_ids:
        messages.append(_msg("error", "CARD_REQUIRED_AND_SKIPPED", "$.intake_session", "同一卡片不能同时列为必答和因材料充分而跳过。"))
    coverage = intake.get("coverage_assessment")
    if not isinstance(coverage, dict) or coverage.get("status") not in {"sufficient_for_drafting", "cards_required"} or not coverage.get("assessed_at"):
        messages.append(_msg("error", "COVERAGE_ASSESSMENT_REQUIRED", "$.intake_session.coverage_assessment", "显示卡片前必须评估用户指令和上传材料是否足以起草。"))

    progress = intake.get("progress")
    if not isinstance(progress, dict):
        messages.append(_msg("error", "INVALID_INTAKE_PROGRESS", "$.intake_session.progress", "必须记录总问题数、已完成数和当前题号。"))
    else:
        if progress.get("total_questions") != len(required_ids):
            messages.append(_msg("error", "CARD_TOTAL_MISMATCH", "$.intake_session.progress.total_questions", "总问题数必须等于材料覆盖评估后编译的必答卡片数。"))
        completed = progress.get("completed_questions")
        if not isinstance(completed, int) or not 0 <= completed <= len(required_ids):
            messages.append(_msg("error", "INVALID_COMPLETED_QUESTIONS", "$.intake_session.progress.completed_questions", "已完成问题数无效。"))
        current = progress.get("current_question_index")
        if current is not None and (not isinstance(current, int) or not 1 <= current <= max(len(required_ids), 1)):
            messages.append(_msg("error", "INVALID_CURRENT_QUESTION", "$.intake_session.progress.current_question_index", "当前题号无效。"))

    seen: set[str] = set()
    confirmed_cards: set[str] = set()
    response_by_card: dict[str, dict[str, Any]] = {}
    for index, response in enumerate(intake["card_responses"]):
        path = f"$.intake_session.card_responses[{index}]"
        if not isinstance(response, dict):
            messages.append(_msg("error", "CARD_RESPONSE_NOT_OBJECT", path, "卡片响应必须为对象。"))
            continue
        card_id = response.get("card_id")
        if not isinstance(card_id, str) or not ID_PATTERN.fullmatch(card_id):
            messages.append(_msg("error", "INVALID_CARD_ID", f"{path}.card_id", "卡片 ID 格式无效。"))
        elif response.get("base_card_id") not in CARD_LIBRARY_IDS:
            messages.append(_msg("error", "UNKNOWN_CARD_ID", f"{path}.card_id", "卡片不属于当前预载问题集。"))
        elif card_id in seen:
            messages.append(_msg("warning", "DUPLICATE_CARD_RESPONSE", f"{path}.card_id", "同一卡片存在多次响应；须保留修订关系。"))
        seen.add(card_id)
        if response.get("confirmed") is not True:
            messages.append(_msg("warning", "UNCONFIRMED_CARD_RESPONSE", path, "卡片响应尚未确认。"))
        elif isinstance(card_id, str):
            confirmed_cards.add(card_id)
            response_by_card[card_id] = response

    if isinstance(progress, dict) and progress.get("completed_questions") != len(confirmed_cards):
        messages.append(_msg("error", "CARD_PROGRESS_MISMATCH", "$.intake_session.progress.completed_questions", "已完成问题数必须等于已确认卡片数。"))

    audience_response = response_by_card.get("audience-type")
    if audience_response and audience not in _as_list(audience_response.get("selected_values")):
        messages.append(_msg("error", "AUDIENCE_RESPONSE_MISMATCH", "$.intake_session.card_responses", "身份卡响应与 audience_profile 不一致。"))

    if intake.get("collection_mode") == "lawyer_sheet":
        privacy_response = response_by_card.get("lawyer-privacy-consent")
        privacy_values = set(_as_list(privacy_response.get("selected_values"))) if privacy_response else set()
        if not {"accepted", "sensitive_data_acknowledged"} <= privacy_values:
            messages.append(_msg("error", "LAWYER_PRIVACY_CONSENT_REQUIRED", "$.intake_session.card_responses", "律师通道必须先完成律师隐私确认卡（同意用途并知悉敏感信息处理）才能继续采集。"))

    basic_response = response_by_card.get("testator-basic-info")
    if basic_response:
        field_values = basic_response.get("field_values")
        required_fields = {"name", "identity_number", "address"}
        if not isinstance(field_values, dict) or not required_fields <= set(field_values):
            messages.append(_msg("error", "BASIC_INFO_FIELD_VALUES_REQUIRED", "$.intake_session.card_responses", "遗嘱人基本信息卡必须提交 field_values（姓名/证件号码/住址；性别与出生日期由身份证号推导），不接受聊天文本替代。"))

    for card_id, response in response_by_card.items():
        base = response.get("base_card_id")
        allowed_values = DECK_CONTRACTS["vocab"].get(base)
        if allowed_values:
            unknown_values = sorted(value for value in _as_list(response.get("selected_values")) if value not in allowed_values)
            if unknown_values:
                messages.append(_msg("error", "CARD_OPTION_VALUE_UNKNOWN", f"$.intake_session.card_responses({card_id})", f"卡片 {card_id} 的选项值不在卡组词表内：{', '.join(unknown_values)}。选项必须来自 intake-card-deck.json。"))
        if base != "testator-basic-info":
            expected_fields = DECK_CONTRACTS["field_cards"].get(base)
            if expected_fields:
                field_values = response.get("field_values")
                if not isinstance(field_values, dict) or not set(expected_fields) <= set(field_values):
                    messages.append(_msg("error", "CARD_FIELD_VALUES_REQUIRED", f"$.intake_session.card_responses({card_id})", f"卡片 {card_id} 必须提交完整 field_values（{'、'.join(expected_fields)}），不接受聊天文本替代。"))
                else:
                    for field_id, allowed in DECK_CONTRACTS["field_vocab"].get(base, {}).items():
                        if field_values.get(field_id) is not None and field_values[field_id] not in allowed:
                            messages.append(_msg("error", "CARD_FIELD_VALUE_UNKNOWN", f"$.intake_session.card_responses({card_id}).field_values.{field_id}", f"字段值不在卡组词表内：{field_values[field_id]}。"))
        form_fields = DECK_CONTRACTS["conditional"].get(base)
        if form_fields:
            selected = _as_list(response.get("selected_values"))
            if selected and selected[0] in form_fields and form_fields[selected[0]]:
                field_values = response.get("field_values")
                if not isinstance(field_values, dict) or not set(form_fields[selected[0]]) <= set(field_values):
                    messages.append(_msg("error", "CONDITIONAL_FIELD_VALUES_REQUIRED", f"$.intake_session.card_responses({card_id})", f"卡片 {card_id} 选择 {selected[0]} 后必须补充该形式对应的条件字段。"))

    if case.get("status") in RESEARCH_GATE_STATUSES | {"researching", "research_blocked"}:
        if intake.get("status") != "confirmed" or not intake.get("confirmed_at"):
            messages.append(_msg("error", "INTAKE_NOT_CONFIRMED", "$.intake_session", "进入研究阶段前必须确认情况与诉求。"))
        missing = required_ids - confirmed_cards
        if missing:
            messages.append(_msg("error", "INCOMPLETE_CARD_DECK", "$.intake_session.card_responses", f"进入研究阶段前须完成全部卡片：{', '.join(sorted(missing))}。"))
        if intake.get("collection_channel") != "ask_user_question":
            messages.append(_msg("error", "INVALID_COLLECTION_CHANNEL", "$.intake_session.collection_channel", "卡片回答必须经 AskUserQuestion 采集通道回传，不接受对话文本或文件回传。"))
        if intake.get("current_card_id") is not None or (isinstance(progress, dict) and progress.get("current_question_index") is not None):
            messages.append(_msg("error", "CONFIRMED_INTAKE_HAS_CURRENT_CARD", "$.intake_session", "访谈确认后不应仍指向当前问题。"))
        try:
            reconciliation = reconcile_coverage(case)
        except (KeyError, TypeError, ValueError) as exc:
            messages.append(_msg("error", "CARD_QUEUE_COMPILATION_FAILED", "$.intake_session", f"卡片队列无法按覆盖评估确定性编译：{exc}"))
        else:
            if not reconciliation["matches"]:
                messages.append(_msg("error", "CARD_QUEUE_MISMATCH", "$.intake_session.required_card_ids", "保存的必答卡片队列与覆盖评估、采集模式和已确认分支不一致。"))

    selection = response_by_card.get("deliverable-selection")
    selected_optional = set(_as_list(selection.get("selected_values"))) & OPTIONAL_DELIVERABLES if selection else set()
    preferences = case.get("output_preferences")
    if selection and isinstance(preferences, dict):
        requested = set(_as_list(preferences.get("requested_deliverables")))
        if selected_optional != requested & OPTIONAL_DELIVERABLES:
            messages.append(_msg("error", "DELIVERABLE_SELECTION_MISMATCH", "$.output_preferences.requested_deliverables", "成果选择卡与案件 JSON 的可选成果不一致。"))


def _validate_consent(case: dict[str, Any], messages: list[Message]) -> None:
    consent = case.get("consent")
    if not isinstance(consent, dict):
        messages.append(_msg("error", "INVALID_CONSENT", "$.consent", "consent 必须为对象。"))
        return
    if consent.get("accepted") is not True or not consent.get("accepted_at"):
        messages.append(_msg("error", "CONSENT_REQUIRED", "$.consent", "必须记录有效授权和时间。"))
    if consent.get("sensitive_data_acknowledged") is not True:
        messages.append(_msg("error", "SENSITIVE_ACK_REQUIRED", "$.consent.sensitive_data_acknowledged", "必须确认敏感信息处理。"))


def _validate_research(case: dict[str, Any], messages: list[Message]) -> None:
    research = case.get("legal_research")
    if not isinstance(research, dict):
        messages.append(_msg("error", "INVALID_LEGAL_RESEARCH", "$.legal_research", "法律研究必须为对象。"))
        return
    status = research.get("status")
    if status not in {"not_started", "in_progress", "verified", "blocked", "stale"}:
        messages.append(_msg("error", "INVALID_RESEARCH_STATUS", "$.legal_research.status", "研究状态无效。"))
    authorities = research.get("authorities")
    cases = research.get("cases")
    links = research.get("education_links")
    for key, value in (("authorities", authorities), ("cases", cases), ("education_links", links), ("limitations", research.get("limitations"))):
        if not isinstance(value, list):
            messages.append(_msg("error", "RESEARCH_SECTION_NOT_ARRAY", f"$.legal_research.{key}", "研究字段必须为数组。"))
    for index, item in enumerate(_as_list(authorities)):
        path = f"$.legal_research.authorities[{index}]"
        url = item.get("source_url") if isinstance(item, dict) else None
        if not _valid_https(url):
            messages.append(_msg("error", "INVALID_AUTHORITY_URL", f"{path}.source_url", "法律依据必须使用可追溯 HTTPS 原文。"))
        elif not _host_allowed(url, OFFICIAL_LAW_DOMAINS):
            messages.append(_msg("warning", "NON_PRIMARY_AUTHORITY_DOMAIN", f"{path}.source_url", "法律依据不是预设官方域名，须人工核验。"))
        if isinstance(item, dict) and (not item.get("retrieved_at") or item.get("effective_status") in {None, "unknown"}):
            messages.append(_msg("error", "AUTHORITY_NOT_VERIFIED", path, "法律依据缺少检索时间或明确效力状态。"))
    recent_dates: list[datetime] = []
    for index, item in enumerate(_as_list(cases)):
        path = f"$.legal_research.cases[{index}]"
        url = item.get("source_url") if isinstance(item, dict) else None
        if not _valid_https(url):
            messages.append(_msg("error", "INVALID_CASE_URL", f"{path}.source_url", "案例必须使用可追溯 HTTPS 原文。"))
        elif not _host_allowed(url, OFFICIAL_CASE_DOMAINS):
            messages.append(_msg("warning", "NON_PRIMARY_CASE_DOMAIN", f"{path}.source_url", "案例不是预设法院官方域名，须人工核验。"))
        if isinstance(item, dict):
            if not item.get("retrieved_at") or not item.get("source_kind"):
                messages.append(_msg("error", "CASE_NOT_VERIFIED", path, "案例缺少检索时间或案例类型。"))
            parsed = _parse_date(item.get("decision_or_publication_date"))
            if parsed:
                recent_dates.append(parsed)
    for index, item in enumerate(_as_list(links)):
        path = f"$.legal_research.education_links[{index}]"
        url = item.get("url") if isinstance(item, dict) else None
        if not _valid_https(url):
            messages.append(_msg("error", "INVALID_EDUCATION_URL", f"{path}.url", "普法链接必须为 HTTPS。"))
        if not isinstance(item, dict) or item.get("verified_access") is not True or not item.get("retrieved_at"):
            messages.append(_msg("error", "EDUCATION_LINK_NOT_VERIFIED", path, "普法链接必须实际打开并记录核验时间。"))

    if case.get("status") in RESEARCH_GATE_STATUSES and status != "verified":
        messages.append(_msg("error", "RESEARCH_GATE_NOT_PASSED", "$.legal_research.status", "当前状态要求研究门禁已通过。"))
    if status == "verified":
        if not research.get("retrieved_at") or not research.get("research_summary"):
            messages.append(_msg("error", "RESEARCH_METADATA_REQUIRED", "$.legal_research", "verified 研究必须有检索时间和摘要。"))
        if not _as_list(authorities):
            messages.append(_msg("error", "NO_VERIFIED_AUTHORITY", "$.legal_research.authorities", "至少需要一项现行法律依据。"))
        if not _as_list(cases):
            messages.append(_msg("error", "NO_VERIFIED_CASE", "$.legal_research.cases", "至少需要一项相关案例。"))
        years = research.get("recent_case_years")
        if not isinstance(years, int) or not 1 <= years <= 20:
            messages.append(_msg("error", "INVALID_RECENT_CASE_WINDOW", "$.legal_research.recent_case_years", "近年案例窗口必须为 1-20 年。"))
        elif recent_dates:
            cutoff_year = datetime.now(timezone.utc).year - years
            if max(recent_dates).year < cutoff_year:
                messages.append(_msg("error", "NO_RECENT_CASE_IN_WINDOW", "$.legal_research.cases", "案例日期未落入声明的近年窗口。"))


def _validate_rule_context(case: dict[str, Any], messages: list[Message]) -> None:
    context = case.get("rule_context")
    pack = load_rule_pack()
    if not isinstance(context, dict):
        messages.append(_msg("error", "INVALID_RULE_CONTEXT", "$.rule_context", "规则包上下文无效。"))
        return
    if context.get("rule_pack_id") != pack.get("rule_pack_id") or context.get("rule_pack_version") != pack.get("version"):
        messages.append(_msg("error", "RULE_PACK_MISMATCH", "$.rule_context", "工作数据引用的规则包 ID 或版本与内置规则包不一致。"))
    if context.get("authority_checked_at") != pack.get("authority_checked_at"):
        messages.append(_msg("error", "RULE_AUTHORITY_BASELINE_MISMATCH", "$.rule_context.authority_checked_at", "规则法源核验基准与规则包不一致。"))
    if context.get("status") == "development":
        messages.append(_msg("warning", "RULE_PACK_IN_DEVELOPMENT", "$.rule_context.status", "规则包已进入开发并执行确定性检查，但尚未完成双人专业审核，不得据此保证遗嘱有效。"))
    elif context.get("status") != "approved":
        messages.append(_msg("error", "INVALID_RULE_CONTEXT", "$.rule_context.status", "规则包状态无效。"))


def _validate_output_gate(case: dict[str, Any], messages: list[Message]) -> None:
    if case.get("status") not in OUTPUT_GATE_STATUSES:
        return
    rule_report = evaluate_rules(case)
    for result in rule_report["results"]:
        if result["level"] == "BLOCKED":
            messages.append(_msg("error", result["code"], "$.rule_context", result["message"]))
        elif result["level"] == "REVIEW_REQUIRED":
            messages.append(_msg("warning", result["code"], "$.rule_context", result["message"]))
    open_blocked = [issue for _, issue in _records(case, "issues") if issue.get("level") == "BLOCKED" and issue.get("status") == "open"]
    if open_blocked:
        messages.append(_msg("error", "OPEN_BLOCKED_ISSUE", "$.issues", "存在未解决的 BLOCKED 问题。"))
    blocking_ai = [item for item in _as_list((case.get("deliverables") or {}).get("ai_judgment_items")) if isinstance(item, dict) and item.get("blocking") is True]
    if blocking_ai:
        messages.append(_msg("error", "AI_JUDGMENT_BLOCKING", "$.deliverables.ai_judgment_items", "AI 待判断清单仍有阻断事项，只能交付缺口报告，不能形成遗嘱正文草案。"))
    scopes = {item.get("scope") for _, item in _records(case, "confirmations")}
    for scope in ("facts", "intentions"):
        if scope not in scopes:
            messages.append(_msg("error", "MISSING_REQUIRED_CONFIRMATION", "$.confirmations", f"缺少 {scope} 确认。"))
    for section in PROVENANCE_SECTIONS:
        for index, record in _records(case, section):
            if record.get("provenance", {}).get("confirmation_status") == "pending_confirmation":
                messages.append(_msg("error", "PENDING_CONFIRMATION_IN_OUTPUT", f"$.{section}[{index}]", "输出阶段仍有待确认关键实体。"))

    capacity = case.get("testator_capacity")
    if not isinstance(capacity, dict) or capacity.get("confirmation_status") != "confirmed" or not capacity.get("confirmed_at"):
        messages.append(_msg("error", "CAPACITY_INFORMATION_NOT_CONFIRMED", "$.testator_capacity", "输出前必须确认独立采集的行为能力与表达情况；该确认不等于 AI 作出法律结论。"))

    preferences = case.get("output_preferences")
    if not isinstance(preferences, dict):
        messages.append(_msg("error", "INVALID_OUTPUT_PREFERENCES", "$.output_preferences", "必须记录用户确认的成果选择。"))
    else:
        requested = preferences.get("requested_deliverables")
        if not isinstance(requested, list):
            messages.append(_msg("error", "INVALID_REQUESTED_DELIVERABLES", "$.output_preferences.requested_deliverables", "成果选择必须为数组。"))
        else:
            requested_set = set(requested)
            unknown = requested_set - CORE_DELIVERABLES - OPTIONAL_DELIVERABLES
            if unknown:
                messages.append(_msg("error", "UNKNOWN_REQUESTED_DELIVERABLE", "$.output_preferences.requested_deliverables", f"存在未知成果类型：{', '.join(sorted(unknown))}。"))
            missing_core = CORE_DELIVERABLES - requested_set
            if missing_core:
                messages.append(_msg("error", "MISSING_CORE_DELIVERABLE", "$.output_preferences.requested_deliverables", f"遗嘱草案和执行指引不可取消：{', '.join(sorted(missing_core))}。"))
        if preferences.get("selection_confirmed") is not True or not preferences.get("selected_at"):
            messages.append(_msg("error", "OUTPUT_SELECTION_NOT_CONFIRMED", "$.output_preferences", "成果选择卡必须经用户确认并记录时间。"))

    will = case.get("will_document")
    if not isinstance(will, dict):
        messages.append(_msg("error", "INVALID_WILL_DOCUMENT", "$.will_document", "遗嘱文档输入必须为对象。"))
    else:
        if will.get("template_id") != "will-template-v1" or will.get("template_sha256") != TEMPLATE_SHA256:
            messages.append(_msg("error", "WILL_TEMPLATE_MISMATCH", "$.will_document", "遗嘱范本 ID 或 SHA-256 不匹配。"))
        if will.get("review_status") != "draft_pending_review":
            messages.append(_msg("error", "INVALID_WILL_REVIEW_STATUS", "$.will_document.review_status", "本 Skill 仅允许生成 draft_pending_review 的 AI 草案，不接受已审定或可签署状态。"))
        sections = will.get("sections")
        if not isinstance(sections, dict):
            messages.append(_msg("error", "INVALID_WILL_SECTIONS", "$.will_document.sections", "遗嘱正文必须为七段对象。"))
        else:
            if set(sections) != set(WILL_SECTION_KEYS):
                messages.append(_msg("error", "WILL_SECTION_KEYS_MISMATCH", "$.will_document.sections", "遗嘱正文标题集合不匹配范本。"))
            for key in WILL_SECTION_KEYS:
                clauses = sections.get(key)
                if not isinstance(clauses, list) or not clauses or any(not isinstance(item, str) or not item.strip() for item in clauses):
                    messages.append(_msg("error", "EMPTY_WILL_SECTION", f"$.will_document.sections.{key}", "每个范本部分至少需要一条完整条款。"))
        for block in ("metadata", "testator", "signature"):
            if not isinstance(will.get(block), dict) or any(not isinstance(value, str) or not value.strip() for value in will.get(block, {}).values()):
                messages.append(_msg("error", "INCOMPLETE_WILL_BLOCK", f"$.will_document.{block}", "遗嘱字段不得为空。"))
        basic = case.get("testator_basic_info", {})
        testator = will.get("testator", {})
        for work_key, will_key in (("name", "name"), ("gender", "gender"), ("identity_number", "identity_number"), ("address", "address")):
            if basic.get(work_key) != testator.get(will_key):
                messages.append(_msg("error", "TESTATOR_WILL_INFO_MISMATCH", f"$.will_document.testator.{will_key}", "遗嘱字段与已确认的基本信息表单不一致。"))
    deliverables = case.get("deliverables")
    if not isinstance(deliverables, dict):
        messages.append(_msg("error", "INVALID_DELIVERABLES", "$.deliverables", "交付输入必须为对象。"))
    else:
        if not _as_list(deliverables.get("execution_guide")):
            messages.append(_msg("error", "NO_EXECUTION_GUIDE", "$.deliverables.execution_guide", "执行操作指引不得为空。"))


def _report(messages: list[Message]) -> dict[str, Any]:
    ordered = sorted(messages, key=lambda item: (LEVEL_ORDER[item.level], item.path, item.code))
    counts = {level: sum(item.level == level for item in ordered) for level in LEVEL_ORDER}
    return {
        "ai_notice": AI_FILE_NOTICE,
        "validator": "lawd-estate-planning.validate_case",
        "validator_version": "0.5.1",
        "schema_version": SCHEMA_VERSION,
        "valid": counts["error"] == 0,
        "counts": counts,
        "messages": [asdict(item) for item in ordered],
    }


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case_file", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)
    try:
        case = _load_json(args.case_file)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read case JSON: {exc}", file=sys.stderr)
        return 1
    report = validate_case(case)
    if args.report:
        _write_json(args.report, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["valid"]:
        return 1
    if args.strict and report["counts"]["warning"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
