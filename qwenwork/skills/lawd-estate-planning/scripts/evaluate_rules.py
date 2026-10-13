#!/usr/bin/env python3
"""Evaluate the development Chinese will rule pack against structured work data."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

from intake_runtime import AI_FILE_NOTICE


RULE_PACK_PATH = Path(__file__).resolve().parents[1] / "assets" / "rules" / "cn-will-core-v0.2.0.json"
LEVEL_ORDER = {"BLOCKED": 0, "REVIEW_REQUIRED": 1, "WARN": 2, "PASS": 3}
WITNESS_FORMS = {"dictated", "printed", "audio_video", "oral"}


def _result(rule: dict[str, Any], level: str, code: str, message: str, related_ids: list[str] | None = None) -> dict[str, Any]:
    return {
        "rule_id": rule["rule_id"],
        "title": rule["title"],
        "level": level,
        "code": code,
        "message": message,
        "authority_refs": rule["authority_refs"],
        "related_ids": related_ids or [],
    }


def _personal_property(rule: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    subject = data.get("subject", {}).get("person_id")
    uncertain: list[str] = []
    outside: list[str] = []
    for asset in data.get("assets", []):
        owners = asset.get("owners", [])
        subject_owners = [owner for owner in owners if owner.get("person_id") == subject]
        if not subject_owners:
            outside.append(asset.get("id", "unknown"))
        elif any(owner.get("share_percent") is None for owner in subject_owners) or asset.get("provenance", {}).get("confirmation_status") != "confirmed":
            uncertain.append(asset.get("id", "unknown"))
    if outside:
        return _result(rule, "BLOCKED", "ASSET_NOT_SHOWN_AS_TESTATOR_PROPERTY", "存在未显示为遗嘱人所有的财产，不能直接写入处分条款。", outside)
    if uncertain:
        return _result(rule, "REVIEW_REQUIRED", "OWNERSHIP_SCOPE_UNCERTAIN", "遗嘱人对部分财产的权属范围或份额尚未确认。", uncertain)
    return _result(rule, "PASS", "PERSONAL_PROPERTY_CHECK_PASSED", "已记录财产均显示遗嘱人为权属人且份额明确。")


def _capacity(rule: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    item = data.get("testator_capacity", {})
    professional = item.get("professional_assessment_status")
    reported = item.get("reported_status")
    voluntary = item.get("voluntariness_status")
    if professional == "confirmed_incapable" or reported == "concern_reported" or voluntary == "concern_reported":
        return _result(rule, "BLOCKED", "CAPACITY_OR_TRUE_INTENT_CONCERN", "存在行为能力或真实意思表示方面的明确疑点，应停止形成遗嘱条款并转专业评估。")
    if reported == "unknown" or voluntary == "unknown" or professional == "inconclusive":
        return _result(rule, "REVIEW_REQUIRED", "CAPACITY_OR_TRUE_INTENT_UNKNOWN", "行为能力或真实意思表示信息不完整，需要补充核实。")
    if professional == "confirmed_capable":
        return _result(rule, "PASS", "CAPACITY_REVIEW_PASSED", "已记录专业评估且未发现真实意思表示疑点。")
    return _result(rule, "REVIEW_REQUIRED", "CAPACITY_NOT_PROFESSIONALLY_VERIFIED", "目前仅有用户陈述或观察，AI 不据此作出法律能力结论；签署前应按风险配置留存独立表达和能力证据。")


def _formalities(rule: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    plan = data.get("will_execution_plan", {})
    form = plan.get("form")
    if form == "undecided" or not form:
        return _result(rule, "BLOCKED", "WILL_FORM_UNDECIDED", "未确定遗嘱形式，无法检查相应签名、日期、见证或记录要求。")
    if form == "notarized" and not plan.get("notary_appointment_planned"):
        return _result(rule, "REVIEW_REQUIRED", "NOTARIZATION_NOT_ARRANGED", "选择了公证遗嘱，但尚未记录由公证机构办理的安排。")
    if form == "oral" and plan.get("emergency_status") != "active":
        return _result(rule, "BLOCKED", "ORAL_WILL_EMERGENCY_NOT_ACTIVE", "口头遗嘱仅适用于危急情况；危急情况消除后能够采用书面或录音录像形式的，原口头遗嘱存在失效风险。")
    required = ["testator_signature_confirmed", "date_confirmed"]
    if form == "audio_video":
        required = ["date_confirmed", "identity_recording_confirmed"]
    if form == "oral":
        required = []
    if form == "printed":
        required += ["witnesses_sign_each_page_confirmed", "continuous_presence_confirmed"]
    if form == "dictated":
        required += ["continuous_presence_confirmed"]
    missing = [name for name in required if plan.get(name) is not True]
    if missing:
        return _result(rule, "BLOCKED", "WILL_FORMALITY_PLAN_INCOMPLETE", "所选遗嘱形式的签名、日期、全程在场或记录安排不完整：" + "、".join(missing) + "。")
    return _result(rule, "PASS", "WILL_FORMALITY_PLAN_PASSED", "所选遗嘱形式的结构化执行安排已通过当前规则检查。")


def _witnesses(rule: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    plan = data.get("will_execution_plan", {})
    if plan.get("form") not in WITNESS_FORMS:
        return _result(rule, "PASS", "WITNESSES_NOT_REQUIRED_BY_SELECTED_FORM", "当前所选形式不触发本规则包的见证人检查。")
    witnesses = plan.get("witnesses", [])
    ids = [item.get("person_id", "unknown") for item in witnesses]
    if len(witnesses) < 2:
        return _result(rule, "BLOCKED", "INSUFFICIENT_WITNESSES", "所选遗嘱形式至少需要两名见证人在场。", ids)
    if len(ids) != len(set(ids)):
        return _result(rule, "BLOCKED", "DUPLICATE_WITNESS", "同一人员被重复登记，不能按两名见证人计算。", ids)
    for witness in witnesses:
        if witness.get("capacity_status") == "ineligible" or witness.get("is_heir_or_legatee") == "yes" or witness.get("has_interest_with_heir_or_legatee") == "yes":
            return _result(rule, "BLOCKED", "INELIGIBLE_WITNESS", "存在法律规定不得作为遗嘱见证人的人员。", [witness.get("person_id", "unknown")])
        if "unknown" in {witness.get("capacity_status"), witness.get("is_heir_or_legatee"), witness.get("has_interest_with_heir_or_legatee")}:
            return _result(rule, "REVIEW_REQUIRED", "WITNESS_ELIGIBILITY_UNKNOWN", "见证人资格信息尚未完整核实。", [witness.get("person_id", "unknown")])
    return _result(rule, "PASS", "WITNESS_CHECK_PASSED", "见证人数及已记录资格信息通过当前规则检查。", ids)


def _reserved_share(rule: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    review = data.get("reserved_share_review", {})
    if review.get("status") == "unknown":
        return _result(rule, "REVIEW_REQUIRED", "RESERVED_SHARE_CANDIDATES_UNKNOWN", "尚未确认是否存在缺乏劳动能力且没有生活来源的继承人。")
    if review.get("status") == "candidate_reported" and review.get("treatment") not in {"reserved", "professional_reviewed"}:
        return _result(rule, "BLOCKED", "RESERVED_SHARE_NOT_ADDRESSED", "已报告可能需要保留必要份额的继承人，但遗嘱方案尚未处理。", review.get("candidate_person_ids", []))
    return _result(rule, "PASS", "RESERVED_SHARE_CHECK_PASSED", "必要份额问题已作出结构化记录。", review.get("candidate_person_ids", []))


def _prior_wills(rule: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    wills = [item.get("id", "unknown") for item in data.get("existing_documents", []) if item.get("document_type") in {"will", "prior_will"}]
    status = data.get("will_execution_plan", {}).get("prior_will_review_status")
    if wills and status != "reviewed":
        return _result(rule, "REVIEW_REQUIRED", "PRIOR_WILL_NOT_REVIEWED", "存在既有遗嘱，需比较日期、撤回行为和内容冲突后再定稿。", wills)
    return _result(rule, "PASS", "PRIOR_WILL_CHECK_PASSED", "未发现未处理的多份遗嘱问题。", wills)


def _support_agreement(rule: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    agreements = [item.get("id", "unknown") for item in data.get("existing_documents", []) if item.get("document_type") in {"legacy_support_agreement", "support_agreement"}]
    status = data.get("will_execution_plan", {}).get("prior_arrangement_review_status")
    if status == "conflict":
        return _result(rule, "BLOCKED", "SUPPORT_AGREEMENT_CONFLICT", "已识别遗赠扶养协议与拟订遗嘱存在冲突，应先处理冲突。", agreements)
    if agreements and status != "no_conflict":
        return _result(rule, "REVIEW_REQUIRED", "SUPPORT_AGREEMENT_NOT_REVIEWED", "存在遗赠扶养协议，需核对是否与遗嘱冲突。", agreements)
    return _result(rule, "PASS", "SUPPORT_AGREEMENT_CHECK_PASSED", "未发现未处理的遗赠扶养协议冲突。", agreements)


def _undisposed(rule: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    asset_ids = {item.get("id") for item in data.get("assets", []) if item.get("id")}
    arranged = {asset_id for item in data.get("intentions", []) for asset_id in item.get("related_asset_ids", [])}
    missing = sorted(asset_ids - arranged)
    if missing:
        return _result(rule, "REVIEW_REQUIRED", "ASSETS_NOT_COVERED_BY_INTENTIONS", "部分已知财产未建立处分意愿映射，应确认采用剩余财产条款还是保留法定处理。", missing)
    return _result(rule, "PASS", "ALL_KNOWN_ASSETS_MAPPED", "全部已知财产均已建立意愿映射。")


def _review(rule: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    return data.get("inheritance_review", {})


def _heir_scope(rule: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    status = _review(rule, data).get("heir_scope_status")
    if status != "complete":
        return _result(rule, "REVIEW_REQUIRED", "HEIR_SCOPE_INCOMPLETE", "法定继承人范围尚未完整核对，可能遗漏配偶、子女、父母或代位继承等关系。")
    return _result(rule, "PASS", "HEIR_SCOPE_REVIEWED", "法定继承人范围已记录为完整核对。")


def _fetal_share(rule: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    status = _review(rule, data).get("fetal_share_treatment")
    if status == "not_addressed":
        return _result(rule, "BLOCKED", "FETAL_SHARE_NOT_RESERVED", "可能涉及胎儿继承份额但尚未保留或完成专业复核。")
    if status not in {"not_applicable", "reserved", "professional_reviewed"}:
        return _result(rule, "REVIEW_REQUIRED", "FETAL_SHARE_UNKNOWN", "胎儿继承份额问题尚未明确。")
    return _result(rule, "PASS", "FETAL_SHARE_RECORDED", "胎儿继承份额问题已作结构化记录。")


def _disqualification(rule: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    review = _review(rule, data)
    if review.get("disqualification_status") == "reported" and review.get("disqualification_review_status") != "reviewed":
        return _result(rule, "REVIEW_REQUIRED", "DISQUALIFICATION_NOT_REVIEWED", "存在丧失继承权、宽恕或恢复继承资格相关事实，须结合证据和具体行为由律师复核。")
    if review.get("disqualification_status") == "unknown":
        return _result(rule, "REVIEW_REQUIRED", "DISQUALIFICATION_UNKNOWN", "是否存在丧失继承权或宽恕争议尚不明确。")
    return _result(rule, "PASS", "DISQUALIFICATION_RECORDED", "丧失继承权与宽恕风险已作结构化记录。")


def _coownership(rule: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    shared = [item.get("id", "unknown") for item in data.get("assets", []) if len(item.get("owners", [])) > 1]
    status = _review(rule, data).get("coownership_review_status")
    if shared and status != "reviewed":
        return _result(rule, "REVIEW_REQUIRED", "COOWNERSHIP_PARTITION_NOT_REVIEWED", "共有财产尚未先析出遗嘱人可处分的份额。", shared)
    return _result(rule, "PASS", "COOWNERSHIP_REVIEW_RECORDED", "共有财产析产问题已作结构化记录。", shared)


def _legatee_acceptance(rule: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    status = _review(rule, data).get("legatee_acceptance_status")
    if status in {"not_planned", "unknown", None}:
        return _result(rule, "REVIEW_REQUIRED", "LEGATEE_ACCEPTANCE_PLAN_MISSING", "遗赠接受期限及向遗赠受领人通知的安排尚未明确。")
    return _result(rule, "PASS", "LEGATEE_ACCEPTANCE_RECORDED", "遗赠接受期限风险已作结构化记录。")


def _attached_obligation(rule: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    status = _review(rule, data).get("attached_obligation_review_status")
    if status in {"not_reviewed", "unknown", None}:
        return _result(rule, "REVIEW_REQUIRED", "ATTACHED_OBLIGATION_NOT_REVIEWED", "附义务安排的内容、履行标准和不履行后果尚未完成专业复核。")
    return _result(rule, "PASS", "ATTACHED_OBLIGATION_RECORDED", "附义务安排已作结构化记录。")


def _lapse_residuary(rule: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    if _review(rule, data).get("lapse_and_residuary_status") != "reviewed":
        return _result(rule, "REVIEW_REQUIRED", "LAPSE_RESIDUARY_NOT_REVIEWED", "受益人先死亡、放弃、丧失权利或安排不能实现时的替补和剩余财产处理尚未核对。")
    return _result(rule, "PASS", "LAPSE_RESIDUARY_REVIEWED", "失效、替补与剩余财产安排已记录为完成核对。")


def _estate_administration(rule: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    review = _review(rule, data)
    missing = []
    if review.get("administrator_consent_status") != "confirmed":
        missing.append("管理人知情与履职意愿")
    if review.get("administrator_terms_status") != "covered":
        missing.append("职责、权限、费用与报酬")
    if missing:
        return _result(rule, "REVIEW_REQUIRED", "ESTATE_ADMINISTRATION_INCOMPLETE", "遗产管理安排尚不完整：" + "、".join(missing) + "。")
    return _result(rule, "PASS", "ESTATE_ADMINISTRATION_RECORDED", "遗产管理人的意愿和基本履职安排已记录。")


def _debt_tax(rule: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    review = _review(rule, data)
    missing = []
    if review.get("debt_inventory_status") != "complete":
        missing.append("税款、债务、担保盘点")
    if review.get("tax_review_status") in {"not_reviewed", "unknown", None}:
        missing.append("专项税费复核")
    if missing:
        return _result(rule, "REVIEW_REQUIRED", "DEBT_TAX_REVIEW_INCOMPLETE", "清偿税款和债务前置事项尚不完整：" + "、".join(missing) + "。")
    return _result(rule, "PASS", "DEBT_TAX_REVIEW_RECORDED", "税款、债务和税费风险已作结构化记录。")


def _insurance_guardianship(rule: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    review = _review(rule, data)
    missing = []
    if review.get("insurance_review_status") in {"not_reviewed", "unknown", None}:
        missing.append("保险金归属和受益人指定")
    if review.get("guardianship_review_status") in {"not_reviewed", "unknown", None}:
        missing.append("监护与未成年人财产管理")
    if missing:
        return _result(rule, "REVIEW_REQUIRED", "INSURANCE_GUARDIANSHIP_REVIEW_INCOMPLETE", "以下事项需要专项复核：" + "、".join(missing) + "。")
    return _result(rule, "PASS", "INSURANCE_GUARDIANSHIP_RECORDED", "保险与监护事项已作结构化记录。")


def _complex_assets(rule: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    review = _review(rule, data)
    if review.get("complex_asset_types") == "reported" and review.get("complex_asset_routing_status") != "routed":
        return _result(rule, "BLOCKED", "COMPLEX_ASSET_NOT_ROUTED", "企业权益、数字资产、境外资产或受限资产尚未分流至相应专业领域复核。")
    if review.get("complex_asset_types") == "unknown":
        return _result(rule, "REVIEW_REQUIRED", "COMPLEX_ASSET_SCOPE_UNKNOWN", "是否涉及需要专项处理的复杂资产尚不明确。")
    return _result(rule, "PASS", "COMPLEX_ASSET_ROUTING_RECORDED", "复杂资产范围与专项分流状态已作记录。")


HANDLERS: dict[str, Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]] = {
    "personal_lawful_property": _personal_property,
    "capacity_and_true_intent": _capacity,
    "will_formalities": _formalities,
    "witness_eligibility": _witnesses,
    "reserved_share": _reserved_share,
    "prior_wills": _prior_wills,
    "prior_support_agreement": _support_agreement,
    "undisposed_estate": _undisposed,
    "heir_scope": _heir_scope,
    "fetal_share": _fetal_share,
    "inheritance_disqualification": _disqualification,
    "coownership_partition": _coownership,
    "legatee_acceptance": _legatee_acceptance,
    "attached_obligation": _attached_obligation,
    "lapse_and_residuary": _lapse_residuary,
    "estate_administration": _estate_administration,
    "debt_and_tax": _debt_tax,
    "insurance_and_guardianship": _insurance_guardianship,
    "complex_asset_routing": _complex_assets,
}


def load_rule_pack(path: Path = RULE_PACK_PATH) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("rule pack root must be an object")
    return value


def evaluate_rules(data: dict[str, Any], rule_pack: dict[str, Any] | None = None) -> dict[str, Any]:
    pack = rule_pack or load_rule_pack()
    results = []
    for rule in pack.get("rules", []):
        handler = HANDLERS.get(rule.get("handler"))
        if handler is None:
            raise ValueError(f"unsupported rule handler: {rule.get('handler')}")
        results.append(handler(rule, data))
    results.sort(key=lambda item: (LEVEL_ORDER[item["level"]], item["rule_id"]))
    counts = {level: sum(item["level"] == level for item in results) for level in LEVEL_ORDER}
    return {
        "ai_notice": AI_FILE_NOTICE,
        "rule_pack_id": pack["rule_pack_id"],
        "rule_pack_version": pack["version"],
        "rule_pack_status": pack["status"],
        "authority_checked_at": pack["authority_checked_at"],
        "counts": counts,
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("work_data", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        data = json.loads(args.work_data.read_text(encoding="utf-8"))
        report = evaluate_rules(data)
        if args.output:
            args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1 if report["counts"]["BLOCKED"] else 0
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
