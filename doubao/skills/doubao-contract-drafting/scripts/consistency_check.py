#!/usr/bin/env python3
"""Run concise structural consistency checks for a V5.7 JSON draft."""
from __future__ import annotations

import re
import sys

from contract_model import as_list, load_contract


def validate(data: dict) -> list[str]:
    """Return structural consistency errors for one draft."""
    sections = as_list(data.get("sections"))
    text = "\n".join(str(item.get("text", "")) for item in sections if isinstance(item, dict))
    errors = []
    articles = [
        match.group(1)
        for item in sections
        if isinstance(item, dict) and item.get("level") == 1
        for match in [re.match(r"^第([一二三四五六七八九十百]+)条", str(item.get("text", "")).strip())]
        if match
    ]
    if len(articles) != len(set(articles)):
        errors.append("存在重复一级条款编号")
    appendix_numbers = [item.get("number") for item in as_list(data.get("appendices")) if isinstance(item, dict)]
    if len(appendix_numbers) != len(set(appendix_numbers)):
        errors.append("附件编号重复")
    appendix_titles = [item.get("title") for item in as_list(data.get("appendices")) if isinstance(item, dict)]
    if len(appendix_titles) != len(set(appendix_titles)):
        errors.append("附件名称重复")
    primary_patterns = {
        "付款": r"^(?:费用与付款|费用、付款与结算|价款与付款|付款与结算|结算与付款)$",
        "验收": r"^(?:交付与验收|验收|质量与验收|交付、验收与质量)$",
        "争议解决": r"^(?:争议解决|法律适用与争议解决)$",
    }
    for topic, pattern in primary_patterns.items():
        headings = []
        for item in sections:
            if not isinstance(item, dict) or item.get("level") != 1:
                continue
            heading = re.sub(r"^第[一二三四五六七八九十百]+条\s*", "", str(item.get("text", "")).strip())
            if re.fullmatch(pattern, heading):
                headings.append(heading)
        if len(headings) > 1:
            errors.append(f"{topic}存在多套主机制")
    if data.get("contract_form") == "single" and data.get("signature_ready") and data.get("has_blanks"):
        errors.append("单项合同标记为可直接签署，但仍存在待填写的关键事实")
    return list(dict.fromkeys(errors))


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: consistency_check.py <contract.json>")
    try:
        data = load_contract(sys.argv[1])
    except (OSError, ValueError) as exc:
        print("CONSISTENCY CHECK FAILED")
        print(f"- {exc}")
        raise SystemExit(1) from exc
    errors = validate(data)
    if errors:
        print("CONSISTENCY CHECK FAILED")
        print("\n".join("- " + item for item in errors))
        raise SystemExit(1)
    print("Consistency check passed.")


if __name__ == "__main__":
    main()
