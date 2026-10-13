#!/usr/bin/env python3
"""Deterministic intake compilation, response normalization, and fast-list parsing."""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DECK_PATH = ROOT / "assets" / "cards" / "intake-card-deck.json"
SKIP_COVERAGE = {"sufficient", "not_applicable"}
AI_FILE_NOTICE = "该文件由AI生成，不能取代律师专业意见，请审慎核实"
AI_DELIVERY_NOTICE = "本内容由人工智能生成，可能存在偏差、遗漏或错误，建议由律师进行人工复核"
PLACEHOLDER_PATTERN = re.compile(
    r"\{\{.*?\}\}|待补|待核验|待确认|演示数据|正式生成前|某市|某区|未提供|签署时填写|TBD|TODO",
    re.IGNORECASE,
)
SENSITIVE_MASK_PATTERN = re.compile(r"[*＊]{2,}|[Xx]{4,}")


def load_deck(path: Path = DECK_PATH) -> dict[str, Any]:
    deck = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(deck, dict) or not isinstance(deck.get("cards"), list):
        raise ValueError("card deck must be an object containing cards")
    return deck


def cards_by_id(deck: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {card["base_card_id"]: card for card in deck["cards"]}


def resolve_base_card(card_id: str, deck: dict[str, Any]) -> str | None:
    ids = cards_by_id(deck)
    if card_id in ids:
        return card_id
    candidates = [base for base in ids if card_id.startswith(base + "-")]
    return max(candidates, key=len) if candidates else None


def _responses_by_id(responses: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for response in responses:
        card_id = response.get("card_id")
        if isinstance(card_id, str):
            result[card_id] = response
    return result


def _selected(responses: dict[str, dict[str, Any]], card_id: str) -> list[str]:
    values = responses.get(card_id, {}).get("selected_values")
    return [value for value in values if isinstance(value, str)] if isinstance(values, list) else []


def _coverage_requires(coverage: dict[str, Any], card: dict[str, Any]) -> bool:
    key = card.get("coverage_key")
    return not isinstance(key, str) or coverage.get(key, "missing") not in SKIP_COVERAGE


def _append(queue: list[str], card_id: str) -> None:
    if card_id not in queue:
        queue.append(card_id)


def _repeat_count(response: dict[str, Any] | None) -> tuple[int, bool]:
    if not response:
        return 0, False
    selected = response.get("selected_values") or []
    for value in selected:
        if isinstance(value, str) and value.isdigit():
            return int(value), False
        if value == "4+":
            explicit = (response.get("field_values") or {}).get("total_count")
            if isinstance(explicit, int) and explicit >= 4:
                return explicit, False
            if isinstance(explicit, str) and explicit.isdigit() and int(explicit) >= 4:
                return int(explicit), False
            return 4, True
    return 0, False


def compile_required_cards(
    coverage: dict[str, Any],
    mode: str,
    responses: Iterable[dict[str, Any]] = (),
    *,
    audience: str | None = None,
    deck: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compile the exact ordered card queue from coverage, mode, and prior answers."""
    deck = deck or load_deck()
    library = cards_by_id(deck)
    response_map = _responses_by_id(responses)
    if mode not in deck.get("collection_modes", {}):
        raise ValueError(f"unsupported collection mode: {mode}")
    if mode == "lawyer_sheet" and audience != "lawyer":
        raise ValueError("lawyer_sheet requires lawyer audience")

    queue: list[str] = []
    skipped: list[str] = []
    pending: list[dict[str, Any]] = []

    # 律师通道：隐私确认卡为首卡；其他模式：audience-type 为首卡，
    # 同意由用途告知 + 首次作答视为同意（运行时自动记录 consent）。
    # 用户类型由模式选择派生（律师专业通道→lawyer；简易/完整→general_public），不再单独发卡询问。
    mandatory = ("lawyer-privacy-consent",) if mode == "lawyer_sheet" else ()
    for card_id in mandatory:
        if card_id in library:
            _append(queue, card_id)

    if mode == "lawyer_sheet":
        _append(queue, "lawyer-sheet-intake")
    elif mode == "fast":
        fast_order = (
            "actor-authority",
            "testator-capacity",
            "fast-persons-enumeration",
            "fast-assets-enumeration",
            "fast-distribution-enumeration",
            "fast-assumptions-correction",
            "will-form-and-witnesses",
            "testator-basic-info",
            "deliverable-selection",
        )
        for card_id in fast_order:
            card = library.get(card_id)
            if card and _coverage_requires(coverage, card):
                _append(queue, card_id)
            elif card:
                skipped.append(card_id)
        corrections = set(_selected(response_map, "fast-assumptions-correction"))
        targeted = library.get("fast-assumptions-correction", {}).get("targeted_cards", {})
        for value in sorted(corrections):
            target = targeted.get(value)
            if isinstance(target, str):
                _append(queue, target)
    else:
        for card in deck["cards"]:
            card_id = card["base_card_id"]
            if card_id in {"intake-confirmation"}:
                continue
            if "complete" not in card.get("modes", []):
                continue
            if not _coverage_requires(coverage, card):
                skipped.append(card_id)
                continue
            activation = card.get("activation")
            if activation:
                source = activation["source_card_id"]
                selected = set(_selected(response_map, source))
                exact = activation.get("selected_value")
                excluded = set(activation.get("selected_values_any_except", []))
                active = exact in selected if exact else bool(selected - excluded)
                if not active:
                    continue
            _append(queue, card_id)

    family_count, family_pending = _repeat_count(response_map.get("family-map"))
    asset_count, asset_pending = _repeat_count(response_map.get("asset-declaration"))
    for base, count, template, needs_more in (
        ("family-map", family_count, "family-map-person-{n}", family_pending),
        ("asset-declaration", asset_count, "asset-declaration-{n}", asset_pending),
    ):
        if base in queue:
            insert_at = queue.index(base) + 1
            instances = [template.format(n=index) for index in range(1, count + 1)]
            queue[insert_at:insert_at] = [item for item in instances if item not in queue]
            if needs_more:
                pending.append({"type": "repeat_count_required", "base_card_id": base, "recorded_minimum": 4})

    if "estate-distribution" in queue:
        index = queue.index("estate-distribution")
        queue.pop(index)
        for offset in range(asset_count):
            queue.insert(index + offset, f"estate-distribution-{offset + 1}")

    _append(queue, "intake-confirmation")
    return {
        "ai_notice": AI_FILE_NOTICE,
        "deck_id": deck["deck_id"],
        "deck_version": deck["version"],
        "collection_mode": mode,
        "required_card_ids": queue,
        "skipped_base_card_ids": sorted(set(skipped)),
        "pending_actions": pending,
    }


def _walk_option_values(node: Any) -> set[str]:
    values: set[str] = set()
    if isinstance(node, dict):
        for option in node.get("options") or []:
            if isinstance(option, dict) and isinstance(option.get("value"), str):
                values.add(option["value"])
        values.update(item for item in node.get("other_value_parsing") or [] if isinstance(item, str))
        for child in node.values():
            values.update(_walk_option_values(child))
    elif isinstance(node, list):
        for child in node:
            values.update(_walk_option_values(child))
    return values


def _field_ids(card: dict[str, Any], card_id: str) -> list[str]:
    node: Any = card
    if card_id != card.get("base_card_id") and isinstance(card.get("page"), dict):
        node = card["page"].get("questions", [])
    fields: list[str] = []
    if isinstance(node, dict):
        fields.extend(item.get("field_id") for item in node.get("fields") or [] if isinstance(item, dict))
        fields.extend(item.get("field_id") for item in node.get("questions") or [] if isinstance(item, dict))
    elif isinstance(node, list):
        fields.extend(item.get("field_id") for item in node if isinstance(item, dict))
    return [field for field in fields if isinstance(field, str)]


def _field_options(card: dict[str, Any]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for field in card.get("fields") or []:
        if not isinstance(field, dict) or not isinstance(field.get("field_id"), str):
            continue
        options = (field.get("ask") or {}).get("options") or []
        values = {item.get("value") for item in options if isinstance(item, dict) and isinstance(item.get("value"), str)}
        if values:
            result[field["field_id"]] = values
    return result


def normalize_response(
    raw: dict[str, Any],
    *,
    deck: dict[str, Any] | None = None,
    answered_at: str,
) -> dict[str, Any]:
    """Normalize a platform response into the card-response contract."""
    deck = deck or load_deck()
    card_id = raw.get("card_id")
    if not isinstance(card_id, str):
        raise ValueError("card_id is required")
    base = resolve_base_card(card_id, deck)
    if base is None:
        raise ValueError(f"unknown card_id: {card_id}")
    card = cards_by_id(deck)[base]
    selected = raw.get("selected_values") or []
    if not isinstance(selected, list) or any(not isinstance(value, str) for value in selected):
        raise ValueError("selected_values must be a string array")
    allowed = _walk_option_values(card)
    unknown = set(selected) - allowed
    if unknown:
        raise ValueError(f"unknown option values: {', '.join(sorted(unknown))}")
    field_values = raw.get("field_values")
    expected = _field_ids(card, card_id)
    if expected:
        if not isinstance(field_values, dict):
            raise ValueError("field_values are required")
        missing = set(expected) - set(field_values)
        if missing:
            raise ValueError(f"missing field values: {', '.join(sorted(missing))}")
        for field_id, allowed_values in _field_options(card).items():
            value = field_values.get(field_id)
            if value is not None and value not in allowed_values:
                raise ValueError(f"unknown field value for {field_id}: {value}")
    free_text = raw.get("other_text") if raw.get("other_text") is not None else raw.get("free_text")
    if "enumerate_now" in selected and not str(free_text or "").strip():
        raise ValueError("enumerate_now requires text entered through the platform Other field")
    answer_status = raw.get("answer_status") or ("later" if "not_ready" in selected else "answered")
    return {
        "card_id": card_id,
        "base_card_id": base,
        "selected_values": selected,
        "field_values": deepcopy(field_values) if isinstance(field_values, dict) else None,
        "free_text": str(free_text).strip() if free_text is not None else None,
        "answer_status": answer_status,
        "answered_at": answered_at,
        "confirmed": bool(raw.get("confirmed", False)),
    }


def _split_top_level(value: str) -> list[str]:
    records: list[str] = []
    current: list[str] = []
    depth = 0
    for char in value.replace("\r\n", "\n"):
        if char in "（([【":
            depth += 1
        elif char in "）)]】" and depth:
            depth -= 1
        if depth == 0 and char in "\n;；":
            item = "".join(current).strip(" 、，,")
            if item:
                records.append(item)
            current = []
        else:
            current.append(char)
    item = "".join(current).strip(" 、，,")
    if item:
        records.append(item)
    return records


def _stable_id(prefix: str, text: str, index: int) -> str:
    digest = hashlib.sha256(text.strip().encode("utf-8")).hexdigest()[:10]
    return f"{prefix}-{index:02d}-{digest}"


def parse_people_list(value: str) -> dict[str, Any]:
    records, issues = [], []
    for index, raw in enumerate(_split_top_level(value), start=1):
        match = re.fullmatch(r"\s*(.*?)\s*[（(](.*)[）)]\s*", raw)
        if not match:
            records.append({"candidate_id": _stable_id("person", raw, index), "display_name": raw, "identity_number": None, "relationship": None, "is_possible_heir": "unknown", "birth_date": None, "gender": None, "raw": raw})
            issues.append({"code": "PERSON_FORMAT_UNMATCHED", "record": raw})
            continue
        name, detail = match.groups()
        parts = [item.strip() for item in re.split(r"[,，]", detail) if item.strip()]
        identity = parts[0] if len(parts) >= 2 else None
        relationship = parts[-1] if parts else None
        derived = derive_from_id_number(identity)
        records.append({"candidate_id": _stable_id("person", raw, index), "display_name": name, "identity_number": identity, "relationship": relationship, "is_possible_heir": derive_heir_status(relationship), "birth_date": derived["birth_date"], "gender": derived["gender"], "raw": raw})
    return {"records": records, "issues": issues}


def _asset_type(value: str) -> str:
    mapping = (
        (("房产", "房屋", "不动产"), "real_estate"),
        (("存款", "理财", "基金", "证券", "银行"), "financial_assets"),
        (("股权", "股份", "合伙", "份额"), "equity"),
        (("车辆", "汽车", "车牌"), "vehicles"),
        (("保险", "保单"), "insurance_rights"),
        (("债权", "借款"), "claims"),
        (("数字", "虚拟", "账号", "加密"), "digital_assets"),
    )
    return next((kind for words, kind in mapping if any(word in value for word in words)), "other")


def parse_assets_list(value: str) -> dict[str, Any]:
    records, issues = [], []
    for index, raw in enumerate(_split_top_level(value), start=1):
        match = re.fullmatch(r"\s*(.*?)\s*[（(](.*)[）)]\s*", raw)
        description = match.group(1).strip() if match else raw
        ownership = match.group(2).strip() if match else "uncertain"
        records.append({"candidate_id": _stable_id("asset", raw, index), "description": description, "asset_type": _asset_type(description), "ownership_text": ownership, "raw": raw})
        if not match:
            issues.append({"code": "ASSET_OWNERSHIP_UNCERTAIN", "record": raw})
    return {"records": records, "issues": issues}


def parse_distribution_list(value: str, people: Iterable[dict[str, Any]], assets: Iterable[dict[str, Any]]) -> dict[str, Any]:
    people_list, asset_list = list(people), list(assets)
    records, issues = [], []
    for index, raw in enumerate(_split_top_level(value), start=1):
        sides = re.split(r"\s*(?:→|->|=>)\s*", raw, maxsplit=1)
        if len(sides) != 2:
            issues.append({"code": "DISTRIBUTION_FORMAT_UNMATCHED", "record": raw})
            continue
        asset_text, beneficiary_text = sides
        matched_assets = [item for item in asset_list if asset_text in item.get("description", "") or item.get("description", "") in asset_text]
        matched_people = [item for item in people_list if item.get("display_name") and item["display_name"] in beneficiary_text]
        if len(matched_assets) != 1:
            issues.append({"code": "DISTRIBUTION_ASSET_AMBIGUOUS", "record": raw})
        if not matched_people:
            issues.append({"code": "DISTRIBUTION_BENEFICIARY_UNMATCHED", "record": raw})
        records.append({
            "candidate_id": _stable_id("intention", raw, index),
            "asset_candidate_ids": [item["candidate_id"] for item in matched_assets],
            "person_candidate_ids": [item["candidate_id"] for item in matched_people],
            "allocation_text": beneficiary_text.strip(),
            "raw": raw,
        })
    return {"records": records, "issues": issues}


def parse_fast_lists(person_text: str, asset_text: str, distribution_text: str) -> dict[str, Any]:
    people = parse_people_list(person_text)
    assets = parse_assets_list(asset_text)
    intentions = parse_distribution_list(distribution_text, people["records"], assets["records"])
    return {
        "people": people["records"],
        "assets": assets["records"],
        "intentions": intentions["records"],
        "issues": people["issues"] + assets["issues"] + intentions["issues"],
        "confirmation_status": "system_inference",
    }


def apply_response(state: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(state)
    intake = result.setdefault("intake_session", {})
    responses = intake.setdefault("card_responses", [])
    responses[:] = [item for item in responses if item.get("card_id") != response["card_id"]]
    responses.append(deepcopy(response))
    confirmed = {item.get("card_id") for item in responses if item.get("confirmed") is True}
    progress = intake.setdefault("progress", {})
    progress["completed_questions"] = len(confirmed & set(intake.get("required_card_ids", [])))
    if response.get("confirmed") and response["base_card_id"] == "lawyer-privacy-consent":
        privacy_selected = set(response.get("selected_values") or [])
        result["consent"] = {
            "accepted": "accepted" in privacy_selected,
            "accepted_at": response.get("answered_at"),
            "purposes": ["will_drafting", "legal_review", "document_generation"],
            "sensitive_data_acknowledged": "sensitive_data_acknowledged" in privacy_selected,
            "basis": "lawyer_privacy_card_explicit",
        }
    elif response.get("confirmed") and not result.get("consent"):
        result["consent"] = {
            "accepted": True,
            "accepted_at": response.get("answered_at"),
            "purposes": ["will_drafting", "legal_review", "document_generation"],
            "sensitive_data_acknowledged": True,
            "basis": "implied_by_first_card_answer_after_purpose_notice",
        }
    base = response["base_card_id"]
    fields = response.get("field_values") or {}
    selected = response.get("selected_values") or []
    answered_at = response.get("answered_at")
    if not result.get("audience_profile"):
        mode = (result.get("intake_session") or {}).get("collection_mode")
        audience = "lawyer" if mode == "lawyer_sheet" else "general_public"
        result["audience_profile"] = {
            "audience_type": audience,
            "language_profile": "professional" if audience == "lawyer" else "plain",
            "selected_via_card_id": "mode-selection",
            "selected_at": answered_at,
            "confirmed": True,
        }
    if base == "audience-type" and selected:
        audience = selected[0]
        result["audience_profile"] = {
            "audience_type": audience,
            "language_profile": "professional" if audience == "lawyer" else "plain",
            "selected_via_card_id": "audience-type",
            "selected_at": answered_at,
            "confirmed": bool(response.get("confirmed")),
        }
    elif base == "testator-basic-info" and isinstance(fields, dict):
        derived = derive_from_id_number(fields.get("identity_number"))
        result["testator_basic_info"] = {
            **deepcopy(fields),
            "gender": derived["gender"] if fields.get("gender") in (None, "") else fields.get("gender"),
            "birth_date": derived["birth_date"] if fields.get("birth_date") in (None, "") else fields.get("birth_date"),
            "derived_from_identity_number": bool(derived["birth_date"]),
            "source_card_id": base,
            "confirmation_status": "confirmed" if response.get("confirmed") else "pending_confirmation",
            "confirmed_at": answered_at if response.get("confirmed") else None,
        }
    elif base == "testator-capacity" and isinstance(fields, dict):
        capacity = result.setdefault("testator_capacity", {})
        capacity.update(deepcopy(fields))
        capacity.update({
            "source_card_id": base,
            "confirmation_status": "confirmed" if response.get("confirmed") else "pending_confirmation",
            "confirmed_at": answered_at if response.get("confirmed") else None,
        })
    elif base in {"family-map", "asset-declaration", "estate-distribution", "executor-custody", "liability-scope", "guardianship-special"}:
        pass  # inheritance_review 由 _derive_inheritance_review 统一推导
    elif base == "will-form-and-witnesses" and selected:
        result.setdefault("will_execution_plan", {})["form"] = selected[0]
    elif base == "deliverable-selection":
        optional = [
            value for value in selected
            if value in {"legal_research_report", "education_content", "asset_inventory", "relationship_diagram"}
        ]
        preferences = result.setdefault("output_preferences", {})
        preferences["requested_deliverables"] = [
            "will_docx", "execution_guide", *optional,
        ]
        preferences["selection_confirmed"] = bool(response.get("confirmed"))
        preferences["selected_at"] = answered_at
    elif base == "intake-confirmation" and "confirmed" in selected and response.get("confirmed"):
        intake["status"] = "confirmed"
        intake["confirmed_at"] = answered_at
        intake["current_card_id"] = None
        progress["current_question_index"] = None
    result["inheritance_review"] = _derive_inheritance_review(result)
    return result


def reconcile_coverage(state: dict[str, Any], *, deck: dict[str, Any] | None = None) -> dict[str, Any]:
    deck = deck or load_deck()
    intake = state.get("intake_session") or {}
    coverage = (intake.get("coverage_assessment") or {}).get("topics") or {}
    compiled = compile_required_cards(
        coverage,
        intake.get("collection_mode"),
        intake.get("card_responses") or [],
        audience=(state.get("audience_profile") or {}).get("audience_type"),
        deck=deck,
    )
    actual = intake.get("required_card_ids") or []
    return {
        "matches": actual == compiled["required_card_ids"],
        "expected_required_card_ids": compiled["required_card_ids"],
        "actual_required_card_ids": actual,
        "missing": [item for item in compiled["required_card_ids"] if item not in actual],
        "unexpected": [item for item in actual if item not in compiled["required_card_ids"]],
        "pending_actions": compiled["pending_actions"],
    }


def find_placeholders(value: Any, path: str = "$") -> list[str]:
    matches: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            matches.extend(find_placeholders(item, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            matches.extend(find_placeholders(item, f"{path}[{index}]"))
    elif isinstance(value, str) and (PLACEHOLDER_PATTERN.search(value) or SENSITIVE_MASK_PATTERN.search(value)):
        matches.append(path)
    return matches


def draft_readiness(case: dict[str, Any]) -> dict[str, Any]:
    """Return safe draft-generation readiness. This Skill never certifies signature readiness."""
    reasons: list[dict[str, str]] = []
    consent = case.get("consent") or {}
    if consent.get("accepted") is not True or consent.get("sensitive_data_acknowledged") is not True:
        reasons.append({"code": "CONSENT_REQUIRED", "message": "未完成数据使用和敏感信息处理确认。"})
    for item in (case.get("deliverables") or {}).get("ai_judgment_items", []):
        if item.get("blocking") is True:
            reasons.append({"code": "AI_JUDGMENT_BLOCKING", "message": str(item.get("title") or "存在阻断事项")})
    witnesses = (case.get("will_execution_plan") or {}).get("witnesses") or []
    witness_ids = [item.get("person_id") for item in witnesses if isinstance(item, dict)]
    if len(witness_ids) != len(set(witness_ids)):
        reasons.append({"code": "DUPLICATE_WITNESS", "message": "见证人不得重复。"})
    placeholders = find_placeholders({
        "testator_basic_info": case.get("testator_basic_info"),
        "will_document": case.get("will_document"),
    })
    return {
        "draft_generation_allowed": not reasons,
        "signature_ready": False,
        "signature_ready_reason": "本 Skill 只生成待律师人工复核的 AI 草案，不作可直接签署认定。",
        "reasons": reasons,
        "warnings": ([{"code": "PLACEHOLDER_OR_MASKED_VALUE", "message": "关键文书字段包含占位、演示或掩码值，必须由律师复核并决定如何补充。", "paths": placeholders}] if placeholders else []),
        "ai_notice": AI_FILE_NOTICE,
    }


def derive_from_id_number(value: Any) -> dict[str, str | None]:
    """从 18 位身份证号推导出生日期与性别；无法推导时返回 None。"""
    text = str(value or "").strip()
    if len(text) != 18:
        return {"birth_date": None, "gender": None}
    ymd = text[6:14]
    if not ymd.isdigit():
        return {"birth_date": None, "gender": None}
    birth = f"{ymd[0:4]}-{ymd[4:6]}-{ymd[6:8]}"
    gender = "男" if int(text[16]) % 2 == 1 else "女"
    return {"birth_date": birth, "gender": gender}


def derive_heir_status(relationship: Any) -> str:
    """按关系推导法定继承人身份：第一、二顺序继承人记 yes，其余 unknown。"""
    rel = str(relationship or "")
    statutory = {"配偶", "父亲", "母亲", "儿子", "女儿", "子女", "兄弟姐妹", "祖父", "祖母", "外祖父", "外祖母"}
    if rel in statutory or rel == "spouse" or rel in {"father", "mother", "son", "daughter", "child", "sibling"}:
        return "yes"
    return "unknown"


def _derive_inheritance_review(state: dict[str, Any]) -> dict[str, str]:
    """从已确认卡片回答确定性推导继承专项复核状态；通过回答可得出结论的不再单独提问。"""
    responses = [r for r in state.get("intake_session", {}).get("card_responses", []) if r.get("confirmed") is True]

    def merged_fields(card_base: str) -> dict[str, Any]:
        merged: dict[str, Any] = {}
        for r in responses:
            if r.get("base_card_id") == card_base and isinstance(r.get("field_values"), dict):
                merged.update(r["field_values"])
        return merged

    def selected_values(card_base: str) -> list[str]:
        values: list[str] = []
        for r in responses:
            if r.get("base_card_id") == card_base:
                values.extend(r.get("selected_values") or [])
        return values

    def instance_fields(card_base: str) -> list[dict[str, Any]]:
        return [
            r.get("field_values") or {}
            for r in responses
            if r.get("base_card_id") == card_base and r.get("card_id") != card_base
        ]

    family_instances = [r for r in responses if r.get("base_card_id") == "family-map" and r.get("card_id") != "family-map"]
    family_fields = merged_fields("family-map")
    asset_fields = instance_fields("asset-declaration")
    dist_fields = instance_fields("estate-distribution")
    executor_fields = merged_fields("executor-custody")
    liability_sel = selected_values("liability-scope")
    guardianship_sel = selected_values("guardianship-special")
    scope_types = selected_values("asset-declaration")

    fetal = family_fields.get("fetal_share_treatment")
    disq = family_fields.get("disqualification_status")
    obligations = [item.get("attached_obligation") for item in dist_fields]
    substitutes = [item.get("substitute_arrangement") for item in dist_fields]
    ownerships = [item.get("ownership") for item in asset_fields]
    possible_non_heir = any(
        (r.get("field_values") or {}).get("is_possible_heir") == "no" for r in family_instances
    )

    def all_answered(values: list[Any]) -> bool:
        return bool(values) and all(v is not None for v in values)

    review = {
        "heir_scope_status": (
            "complete" if family_fields.get("other_statutory_heirs") == "none"
            else "incomplete" if family_fields.get("other_statutory_heirs") == "reported"
            else "unknown" if family_fields.get("other_statutory_heirs") == "unknown"
            else "complete" if family_instances else "unknown"
        ),
        "fetal_share_treatment": fetal if fetal in {"not_applicable", "reserved", "professional_reviewed", "not_addressed"} else "unknown",
        "disqualification_status": disq if disq in {"none", "reported", "unknown"} else "unknown",
        "disqualification_review_status": (
            "not_applicable" if disq == "none" else "reviewed" if disq == "reported" else "unknown"
        ),
        "legatee_acceptance_status": "unknown" if (possible_non_heir and dist_fields) else "not_applicable",
        "attached_obligation_review_status": (
            "not_applicable" if obligations and all(v == "none" for v in obligations)
            else "reviewed" if any(v == "has_obligation" for v in obligations)
            else "not_reviewed" if obligations else "unknown"
        ),
        "lapse_and_residuary_status": (
            "reviewed" if all_answered(substitutes) else "not_reviewed" if dist_fields else "unknown"
        ),
        "coownership_review_status": (
            "reviewed" if all_answered(ownerships) else "not_reviewed" if asset_fields else "unknown"
        ),
        "administrator_consent_status": executor_fields.get("executor_willingness")
        if executor_fields.get("executor_willingness") in {"confirmed", "not_confirmed", "unknown"} else "unknown",
        "administrator_terms_status": "unknown",
        "debt_inventory_status": (
            "complete" if any(v in {"none_known", "mortgage_only", "other_debts"} for v in liability_sel) else "unknown"
        ),
        "tax_review_status": "not_applicable",
        "insurance_review_status": "not_reviewed" if "insurance_rights" in scope_types else "not_applicable",
        "guardianship_review_status": (
            "not_applicable" if "none" in guardianship_sel
            else "reviewed" if any(v in {"minor_children", "guardianship", "overseas", "family_dispute"} for v in guardianship_sel)
            else "unknown"
        ),
        "complex_asset_types": (
            "reported" if any(v in {"insurance_rights", "digital_assets", "other"} for v in scope_types)
            else "none" if scope_types else "unknown"
        ),
        "complex_asset_routing_status": "unknown",
    }
    review["complex_asset_routing_status"] = "not_applicable" if review["complex_asset_types"] == "none" else (
        "not_routed" if review["complex_asset_types"] == "reported" else "unknown"
    )
    return review
