#!/usr/bin/env python3
"""Validate fact states and output-format instructions before drafting."""
from __future__ import annotations

import re
import sys

from contract_model import as_list, iter_contract_text, load_contract, validate_schema


BASE_PARAMETERS = {"争议解决", "书面验收规则", "验收期", "逾期履行违约金", "普通责任上限", "合同期限"}
FAMILY_PARAMETERS = {
    "货物买卖/采购": {"交付期", "付款节点", "付款期限", "质保/维护期"},
    "服务采购": {"履行/启动期", "付款节点", "付款期限", "质保/维护期"},
    "营销推广": {"履行/启动期", "付款节点", "付款期限", "质保/维护期"},
    "工程施工与空间改造": {"工期或相对竣工期", "付款节点", "付款期限", "质保/养护期", "工程质量与安全责任例外"},
    "软件许可/SaaS采购": {"开通/交付期", "付款节点", "付款期限", "服务期"},
    "委托开发/技术服务": {"交付期", "付款节点", "付款期限", "质保/维护期"},
    "知识产权许可": {"交付期", "付款节点", "付款期限", "权利保证期限"},
    "知识产权转让": {"交付期", "付款节点", "付款期限", "权利保证期限"},
    "租赁": {"交付期", "租期", "付款周期"},
    "数据处理/数据共享": {"配置/启动期", "服务期", "事件通知时限"},
    "合作开发/联合研发": {"项目计划期", "验收期"},
}


def validate(data: dict) -> list[str]:
    """Return preflight errors for one parsed contract draft."""
    errors = ["SCHEMA " + error for error in validate_schema(data)]
    if errors:
        return errors
    text = "\n".join(str(item.get("text", "")) for item in as_list(data.get("sections")) if isinstance(item, dict))
    placeholder_pattern = re.compile(r"【[^】]*(?:待填|待补|待确认|待核查)[^】]*】|\[[^\]]*(?:待填|待补|待确认|待核查|TBD)[^\]]*\]|\bTBD\b", re.IGNORECASE)
    for path, value in iter_contract_text(data):
        if placeholder_pattern.search(value):
            errors.append(f"{path} 存在已废止的文字型占位符")

    facts_by_key = {str(fact.get("key", "")): fact for fact in as_list(data.get("facts")) if isinstance(fact, dict)}
    if data.get("contract_form") == "single":
        profile = data.get("parameter_profile")
        if isinstance(profile, dict) and profile.get("family") and profile.get("role"):
            required = {str(key) for key in profile.get("required", [])}
            expected = BASE_PARAMETERS | FAMILY_PARAMETERS.get(str(profile.get("family")), set())
            not_applicable = profile.get("not_applicable", {})
            if not isinstance(not_applicable, dict):
                not_applicable = {}
            for key, reason in not_applicable.items():
                if key not in expected:
                    errors.append(f"不适用项 {key} 不属于该参数档案")
                elif not str(reason).strip():
                    errors.append(f"不适用项 {key} 缺少理由")
            expected -= {str(key) for key in not_applicable}
            missing_profile_keys = expected - required
            if missing_profile_keys:
                errors.append("parameter_profile 缺少覆盖项：" + "、".join(sorted(missing_profile_keys)))
            for key in required:
                fact = facts_by_key.get(key)
                if not fact or fact.get("status") not in {"confirmed", "standard_parameter"}:
                    errors.append(f"应预填参数 {key} 未记录为确认事实或标准参数")
                    continue
                terms = [str(term) for term in fact.get("coverage_terms", []) if str(term)]
                if not terms:
                    errors.append(f"应预填参数 {key} 缺少 coverage_terms")
                elif not all(term in text for term in terms):
                    errors.append(f"应预填参数 {key} 未完整写入合同")

    visible_text = list(iter_contract_text(data))
    for fact in as_list(data.get("facts")):
        if not isinstance(fact, dict) or fact.get("status") != "pending":
            continue
        aliases = [str(item) for item in fact.get("aliases", []) if str(item)]
        assertions = [str(item) for item in fact.get("forbidden_assertions", []) if str(item)]
        if not aliases or not assertions:
            continue
        for path, value in visible_text:
            for sentence in value.replace("\n", "。 ").split("。"):
                if not (any(alias in sentence for alias in aliases) and any(assertion in sentence for assertion in assertions)):
                    continue
                is_negated = any(re.search(r"(?:未|尚未|不得|不应|不能|是否|待|需).{0,8}" + re.escape(assertion), sentence) for assertion in assertions)
                if not is_negated:
                    errors.append(f"{path} 将待核查事实 {fact.get('key', '未命名')} 写为已确认")
                    break
            else:
                continue
            break

    if data.get("allow_tables") is False and data.get("tables"):
        errors.append("用户禁止表格，但草案仍声明根级表格")
    for index, appendix in enumerate(as_list(data.get("appendices"))):
        if not isinstance(appendix, dict):
            continue
        if appendix.get("source") and not appendix.get("list_only") and not appendix.get("content"):
            errors.append(f"受控附件 {appendix.get('number', '未编号')} 缺少原始附件内容")
        if data.get("allow_tables") is False and appendix.get("tables"):
            errors.append(f"用户禁止表格，但 $.appendices[{index}] 含表格")
    return list(dict.fromkeys(errors))


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: preflight.py <contract.json>")
    try:
        data = load_contract(sys.argv[1])
    except (OSError, ValueError) as exc:
        print("PREFLIGHT FAILED")
        print(f"- {exc}")
        raise SystemExit(1) from exc
    errors = validate(data)
    if errors:
        print("PREFLIGHT FAILED")
        print("\n".join("- " + item for item in errors))
        raise SystemExit(1)
    print("Preflight passed.")


if __name__ == "__main__":
    main()
