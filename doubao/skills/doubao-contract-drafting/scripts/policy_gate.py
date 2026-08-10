#!/usr/bin/env python3
"""Block non-negotiable drafting red lines in a JSON contract draft."""
from __future__ import annotations

import re
import sys

from contract_model import iter_contract_text, load_contract

IMPLIED_ACCEPTANCE = r"(?:未.{0,20}(?:回复|反馈|确认|提出异议)|逾期未回复|持续使用|使用|试运行届满|上线运行).{0,30}(?:(?:视为|即视为|应(?:被)?视为|视同|即代表).{0,20}(?:验收|验收合格|通过|完成)|(?:即|则|即表示|则表示)?(?:验收|验收合格|通过)|即告完成)"
IMPLIED_CONSENT = r"(?:未.{0,20}(?:回复|反馈|确认|提出异议)|逾期未回复).{0,30}(?:(?:视为|即视为|应(?:被)?视为|视同|推定).{0,20}(?:同意|确认|批准)|(?:即|则|即表示|则表示)(?:同意|确认|批准))"
RULES = (
    ("POLICY_IMPLIED_ACCEPTANCE", "默示验收", IMPLIED_ACCEPTANCE),
    ("POLICY_IMPLIED_CONSENT", "默示同意", IMPLIED_CONSENT),
    ("POLICY_AUTO_RENEWAL", "自动续期", r"自动续期|自动续展|自动延续|届满自动延长|自动顺延|自动展期"),
    ("POLICY_AUTO_EFFECT", "自动生效", r"自动生效|当然生效"),
)


def negated(sentence: str, match: re.Match[str]) -> bool:
    """Allow explicit prohibitions such as '不视为验收合格' and '不自动续期'."""
    window = sentence[max(0, match.start() - 12): match.end() + 12]
    return bool(re.search(r"(?:不|不得|并不|均不|不应|不构成|不当然)\s*(?:被)?(?:视为|即视为|应视为|视同|推定|自动续期|自动续展|自动延续|自动顺延|自动展期|自动生效|当然生效|生效)|(?:不|不得).{0,8}(?:构成|代表).{0,8}(?:验收|同意|确认|批准)", window))


def violations(text: str) -> list[str]:
    """Return unique policy labels present in plain text."""
    labels = []
    for sentence in re.split(r"[。；\n]", text):
        for _, label, pattern in RULES:
            if any(not negated(sentence, match) for match in re.finditer(pattern, sentence)):
                labels.append(label)
    return sorted(set(labels))


def validate(data: dict) -> list[str]:
    """Return path-aware policy violations for a contract draft."""
    errors = []
    for path, text in iter_contract_text(data):
        for sentence in re.split(r"[。；\n]", text):
            for rule_id, label, pattern in RULES:
                for match in re.finditer(pattern, sentence):
                    if not negated(sentence, match):
                        errors.append(f"{rule_id} {path}：{label}（{sentence.strip()}）")
    return list(dict.fromkeys(errors))


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: policy_gate.py <contract.json>")
    try:
        data = load_contract(sys.argv[1])
    except (OSError, ValueError) as exc:
        print("POLICY GATE FAILED")
        print(f"- {exc}")
        raise SystemExit(1) from exc
    errors = validate(data)
    if errors:
        print("POLICY GATE FAILED")
        print("\n".join("- " + item for item in errors))
        raise SystemExit(1)
    print("Policy gate passed.")


if __name__ == "__main__":
    main()
