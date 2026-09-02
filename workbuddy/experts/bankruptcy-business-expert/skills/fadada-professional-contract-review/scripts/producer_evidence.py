"""Build non-trusted producer evidence for contract-review deliverables."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


STANDARD_VERSION = "1.1.0"
CHECKER_VERSION = "1.0.0"
DOCX_MIME = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)
ROLE_PROFILES = {
    "review_report": "word-report",
    "redline": "word-revision",
    "clean_contract": "word-revision",
    "bilingual_contract": "word-revision",
}
PROFILE_RULES = {
    "word-report": ("OUT-COM-003", "OUT-WORD-001", "OUT-WORD-003", "OUT-WORD-006"),
    "word-revision": ("OUT-COM-003", "OUT-WORD-001", "OUT-WORD-002", "OUT-WORD-003"),
}


def infer_rule_id(message: str) -> str:
    value = message.lower()
    if "emoji" in value:
        return "OUT-WORD-001"
    if any(token in value for token in ("w:ins", "w:del", "revision", "comments.xml")):
        return "OUT-WORD-002"
    if "disclaimer" in value or "免责声明" in value:
        return "OUT-WORD-006"
    if any(token in value for token in ("table", "width", "heading", "a4", "page", "signature")):
        return "OUT-WORD-003"
    return "OUT-COM-003"


def _artifact_errors(path: Path, role: str, errors: list[str]) -> list[str]:
    labels = {
        "review_report": ("report:", path.name.lower()),
        "redline": ("redline:", path.name.lower()),
        "clean_contract": ("clean:", path.name.lower()),
        "bilingual_contract": ("bilingual:", path.name.lower()),
    }[role]
    selected = [
        error
        for error in errors
        if any(label and label in error.lower() for label in labels)
    ]
    return selected or (list(errors) if errors else [])


def _rule_results(profile: str, errors: list[str]) -> list[dict]:
    failures: dict[str, list[str]] = {}
    for error in errors:
        failures.setdefault(infer_rule_id(error), []).append(error)
    return [
        {
            "ruleId": rule_id,
            "status": "failed" if failures.get(rule_id) else "passed",
            "message": "; ".join(failures.get(rule_id, [])) or "producer check passed",
        }
        for rule_id in PROFILE_RULES[profile]
    ]


def build_review_evidence(
    *,
    producer_skill_id: str,
    artifacts: list[tuple[Path, str]],
    errors: list[str],
) -> dict:
    """Return bundle evidence without claiming trusted platform validation."""
    artifact_results = []
    for path, role in artifacts:
        profile = ROLE_PROFILES[role]
        own_errors = _artifact_errors(path, role, errors)
        failed = bool(own_errors)
        findings = [
            {
                "code": "PRODUCER_CHECK_FAILED",
                "severity": "error",
                "message": error,
                "ruleId": infer_rule_id(error),
            }
            for error in own_errors
        ]
        if not failed:
            findings.append(
                {
                    "code": "SELF_VALIDATED_ONLY",
                    "severity": "warning",
                    "message": (
                        "Producer self-check passed; trusted platform validation is still required."
                    ),
                }
            )
        artifact_results.append(
            {
                "path": str(path),
                "role": role,
                "mimeType": DOCX_MIME,
                "outputProfile": profile,
                "standardVersion": STANDARD_VERSION,
                "producerSkillId": producer_skill_id,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None,
                "validationStatus": "failed" if failed else "warning",
                "validationFindings": findings,
                "producerValidation": {
                    "evidenceType": "producer_self_check",
                    "checkerId": f"{producer_skill_id}:review-output-gate",
                    "checkerVersion": CHECKER_VERSION,
                    "trusted": False,
                    "status": "failed" if failed else "passed",
                    "ruleResults": _rule_results(profile, own_errors),
                },
            }
        )
    return {
        "standardVersion": STANDARD_VERSION,
        "producerSkillId": producer_skill_id,
        "producerValidation": {
            "evidenceType": "producer_self_check",
            "checkerId": f"{producer_skill_id}:review-output-gate",
            "checkerVersion": CHECKER_VERSION,
            "trusted": False,
            "status": "failed" if errors else "passed",
        },
        "artifacts": artifact_results,
    }


def write_review_evidence(path: Path, evidence: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
