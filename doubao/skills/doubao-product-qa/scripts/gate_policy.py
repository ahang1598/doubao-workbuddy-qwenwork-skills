#!/usr/bin/env python3
"""门策略表：把校验发现分成 BLOCK / FIX / REPORT 三档，并自动修掉机械项。

设计前提（见 doubao-skill-builder/references/gate-design.md）：

- 阻断条件的**总量**本身就是一道门。执行者面对上百条 error 时，理性选择是绕过整条链，
  而不是逐条修。所以本表只保留"错了会让用户拿到错东西"的少数几条为 BLOCK。
- 未登记的发现默认 **REPORT（非致命）**。新增 BLOCK 必须同时移除一条。
- FIX 档必须答案唯一。有第二种合理答案的一律不自动改。
"""

from __future__ import annotations

import re
from typing import Any

BLOCK = "BLOCK"
FIX = "FIX"
REPORT = "REPORT"

DEFAULT_LEVEL = REPORT

# ---------------------------------------------------------------------------
# BLOCK 全集，按"类"组织而不是按条。
#
# 判据只有一条：错了会让用户拿到**错东西**（错数字、错结论、错优先级、没产物）。
# 只是"canonical 填得不够漂亮"一律不进这里——那是 FIX 或 REPORT。
#
# 新增一个类必须移除一个类，并同步 references/gate-policy.md 与 SKILL.md 的门清单。
# ---------------------------------------------------------------------------
BLOCK_CLASSES: dict[str, dict[str, Any]] = {
    "canonical-nonempty": {
        "why": "报告要引用的集合为空时，正文里的任何数字都没有来源",
        "paths": {"input.sources", "input.artifacts", "requirements", "risk_mechanisms", "cases", "executions"},
    },
    "count-identity": {
        "why": "统计不自洽（总数 ≠ 各状态之和）直接毁掉报告可信度",
        "paths": {"coverage"},
    },
    "verdict-discipline": {
        "why": "越过证据下终审是本 Skill 的核心红线：零证据只能 undetermined",
        "paths": {"release_decision.decision", "release_decision.rationale"},
    },
    "p0-blocking-identity": {
        "why": "金标准的真实规则是 P0 ⟺ 阻断本次发布；两个集合不等就是 P0 膨胀",
        "paths": {"release_decision.blocking_bug_ids"},
    },
    "unverified-consistency": {
        "why": "存在未执行却写「未验证范围：无」，是成品内部自相矛盾",
        "paths": {"unverified"},
    },
    "severity-priority-enum": {
        "why": "混入 S0/致命/High/Blocker 会让读者无法与既有 SOP 对齐",
        "paths": {"bugs[].severity", "bugs[].priority"},
    },
    "precheck-not-formal": {
        "why": "预跑、小样本、裁剪截图升成正式 Bug 会制造不存在的缺陷",
        "paths": {"bugs[].evidence_grade", "executions[].formal_conclusion"},
    },
    "open-oracle": {
        "why": "未决口径写成唯一预期，会驱动开发按错误规则验收",
        "paths": {"open_questions[].oracle_discipline"},
    },
    "delivery-contract": {
        "why": "用户指定的载体、文件名、章节顺序是硬契约，不是默认值",
        "paths": {
            "request_contract.delivery.format",
            "request_contract.delivery.carrier",
            "request_contract.delivery.filenames",
            "request_contract.delivery.artifacts",
        },
    },
    "delivery-artifact": {
        "why": "产物不存在或未回读就宣称交付",
        "paths": {"delivery_manifest.outputs"},
    },
}

BLOCK_RULES: dict[str, str] = {
    path: f"[{name}] {spec['why']}"
    for name, spec in BLOCK_CLASSES.items()
    for path in spec["paths"]
}

# ---------------------------------------------------------------------------
# FIX 档：答案唯一、可由脚本直接改完。
# ---------------------------------------------------------------------------
FIX_RULES: set[str] = {
    "requirements[].id",
    "risk_mechanisms[].id",
    "cases[].id",
    "acceptance_checks[].id",
    "executions[].id",
    "evidence[].id",
    "bugs[].id",
    "bug_candidates[].id",
    "open_questions[].id",
    "change_ledger[].id",
    "risk_mechanisms[].case_ids",
    "cases[].status",
    "acceptance_checks[].status",
    "change_ledger",
    "change_ledger[].delta_count",
    "change_ledger[].before_count",
    "change_ledger[].revision",
    "input.artifacts[].coverage_note",
}

ID_PREFIX = {
    "requirements": "REQ",
    "risk_mechanisms": "RM",
    "cases": "TC",
    "acceptance_checks": "AC",
    "executions": "EXE",
    "evidence": "EVD",
    "bugs": "BUG",
    "bug_candidates": "BUGC",
    "open_questions": "Q",
}

_INDEX = re.compile(r"\[[^\]]*\]")


def signature(path: str) -> str:
    """把 findings 的 path 归一成策略表的键：cases[3].id -> cases[].id"""
    return _INDEX.sub("[]", str(path or "")).strip()


def classify(finding: dict[str, Any]) -> str:
    """未登记的发现默认非致命。这是刻意的：门的总量本身就是风险。"""
    sig = signature(finding.get("path", ""))
    if sig in FIX_RULES:
        return FIX
    if sig in BLOCK_RULES:
        return BLOCK
    # 顶层集合为空属于 canonical-nonempty；子字段不合规不属于
    head = sig.split(".")[0].split("[")[0]
    if sig == head and head in BLOCK_RULES:
        return BLOCK
    if head in {"coverage", "unverified"}:
        return BLOCK
    if str(finding.get("level")) == "warning":
        return REPORT
    return DEFAULT_LEVEL


def block_class(finding: dict[str, Any]) -> str:
    sig = signature(finding.get("path", ""))
    for name, spec in BLOCK_CLASSES.items():
        if sig in spec["paths"] or sig.split(".")[0].split("[")[0] in spec["paths"]:
            return name
    return "other"


def partition(findings: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    buckets: dict[str, list[dict[str, Any]]] = {BLOCK: [], FIX: [], REPORT: []}
    for item in findings:
        buckets[classify(item)].append(item)
    return buckets


# ---------------------------------------------------------------------------
# 机械项自动修复
# ---------------------------------------------------------------------------

def _module_token(item: dict[str, Any], fallback: str) -> str:
    """从 module 字段取模块名；只用 ASCII 字母数字，其余回退。"""
    raw = str(item.get("module") or item.get("object_type") or "").strip()
    token = re.sub(r"[^0-9A-Za-z]", "", raw).upper()
    return token or fallback


def _frozen_ids(run: dict[str, Any]) -> set[str]:
    """已经出现在历史变更台账或 tombstone 里的 ID 不得重命名。

    multi-round-control.md 明确规定编号发布后不改名、删除后不复用。
    自动改名只允许作用于本 revision 首次出现、且从未被外部引用过的 ID。
    """
    frozen: set[str] = set()
    for entry in run.get("change_ledger", []) or []:
        if not isinstance(entry, dict):
            continue
        for key in ("removed_ids", "added_ids", "modified_ids", "restored_ids"):
            for value in entry.get(key, []) or []:
                frozen.add(str(value))
    for key in ("tombstones", "removed_objects"):
        for entry in run.get(key, []) or []:
            if isinstance(entry, dict) and entry.get("id"):
                frozen.add(str(entry["id"]))
    return frozen


def autofix_ids(run: dict[str, Any], slug: str) -> list[str]:
    """把 REQ-001 这类格式补成 REQ-<模块>-001，并同步全部引用。

    仅在 ID 不含模块段时触发；已合规、已冻结的 ID 一律不动。
    """
    changes: list[str] = []
    frozen = _frozen_ids(run)
    fallback = re.sub(r"[^0-9A-Za-z]", "", slug).upper()[:12] or "MAIN"

    rename: dict[str, str] = {}
    for collection, prefix in ID_PREFIX.items():
        items = run.get(collection)
        if not isinstance(items, list):
            continue
        pattern = re.compile(rf"^{prefix}-([0-9A-Za-z]+)-(\d+)$")
        loose = re.compile(rf"^{prefix}-(\d+)$")
        for item in items:
            if not isinstance(item, dict):
                continue
            current = str(item.get("id", ""))
            if not current or current in frozen or pattern.match(current):
                continue
            match = loose.match(current)
            if not match:
                continue
            module = _module_token(item, fallback)
            candidate = f"{prefix}-{module}-{match.group(1)}"
            if candidate == current or candidate in rename.values():
                continue
            rename[current] = candidate

    if not rename:
        return changes

    def remap(value: Any) -> Any:
        if isinstance(value, str):
            return rename.get(value, value)
        if isinstance(value, list):
            return [remap(entry) for entry in value]
        if isinstance(value, dict):
            return {key: remap(entry) for key, entry in value.items()}
        return value

    for key in list(run.keys()):
        run[key] = remap(run[key])
    changes.append(f"ids normalized ({len(rename)} 项补齐模块段)")
    return changes


def autofix(run: dict[str, Any], slug: str = "") -> list[str]:
    """运行全部机械修复，返回变更摘要。答案不唯一的项一律不碰。"""
    changes: list[str] = []
    changes.extend(autofix_ids(run, slug))

    # 风险机制与用例的双向引用：由用例侧单向推导，答案唯一
    case_ids_by_mechanism: dict[str, list[str]] = {}
    for case in run.get("cases", []) or []:
        if not isinstance(case, dict):
            continue
        for mechanism_id in case.get("risk_mechanism_ids", []) or []:
            case_ids_by_mechanism.setdefault(str(mechanism_id), []).append(str(case.get("id", "")))
    synced = 0
    for mechanism in run.get("risk_mechanisms", []) or []:
        if not isinstance(mechanism, dict):
            continue
        expected = case_ids_by_mechanism.get(str(mechanism.get("id", "")), [])
        if list(mechanism.get("case_ids") or []) != expected:
            mechanism["case_ids"] = expected
            synced += 1
    if synced:
        changes.append(f"risk_mechanisms.case_ids synced ({synced} 条)")

    # cases 不维护自己的 status，一律由 executions 派生
    stripped = 0
    for case in run.get("cases", []) or []:
        if isinstance(case, dict) and "status" in case:
            case.pop("status")
            stripped += 1
    if stripped:
        changes.append(f"cases.status removed ({stripped} 条，状态由执行派生)")

    return changes


def render_lines(buckets: dict[str, list[dict[str, Any]]], *, fixed: list[str]) -> list[str]:
    """人类可读的门禁输出。

    执行者不应该需要写代码来解析门的结果——trace 实测中，解析嵌套 JSON
    消耗了 6 次工具调用。这里输出定长行，顺序即修复顺序。
    """
    lines: list[str] = []
    lines.append(
        f"GATE: BLOCK {len(buckets[BLOCK])} / FIX {len(fixed)}(已自动修) / REPORT {len(buckets[REPORT])}"
    )
    for index, item in enumerate(buckets[BLOCK], start=1):
        lines.append(f"BLOCK-{index}  [{block_class(item)}]  {item.get('path')}  {item.get('message')}")
        fix = str(item.get("fix") or "").strip()
        if fix:
            lines.append(f"          修法：{fix}")
    for note in fixed:
        lines.append(f"FIXED     {note}")
    for item in buckets[REPORT][:12]:
        lines.append(f"REPORT    {item.get('path')}  {item.get('message')}")
    if len(buckets[REPORT]) > 12:
        lines.append(f"REPORT    …另有 {len(buckets[REPORT]) - 12} 条，全部进成品的「本轮披露」段")
    return lines


# 只有这些前缀的 REPORT 项对**用户**有意义，才进成品的「本轮披露」段。
# canonical 内部完整度（behavior 拆解、impact_scope 这类）只在门输出里出现，
# 不能倒进用户看到的产物——否则披露段会被几十条内部字段名淹没，
# 用户读到的仍然是"内部脚本旁白"，正是 qa-output-craft 明令禁止的东西。
USER_FACING_PREFIXES = (
    "evidence",
    "executions",
    "bugs",
    "unverified",
    "blockers",
    "delivery_manifest",
    "test_data",
    "manual_handoff",
    "open_questions",
)


def disclosure_notes(buckets: dict[str, list[dict[str, Any]]]) -> list[str]:
    """进成品披露段的 REPORT 项。内部完整度项不进这里，只在门输出里出现。"""
    notes: list[str] = []
    for item in buckets[REPORT]:
        sig = signature(item.get("path", ""))
        head = sig.split(".")[0].split("[")[0]
        if head in USER_FACING_PREFIXES:
            notes.append(f"{item.get('message')}（{sig}）")
    return notes


def blocking(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """全包唯一的"什么算阻断"判据。

    renderer / validator / publish 三处各自用 level=="error" 判阻断时，
    等于包内有四套并行的门；改了策略表也拦不住它们。一律走这里。
    """
    return [item for item in findings if classify(item) == BLOCK]
