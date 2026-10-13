#!/usr/bin/env python3
"""模式A 字段映射门禁：校验类案检索交付集的案号 / 法院 / 出处（数据来源）三项出处字段。

背景：连接器改造后案例字段来源由供应商 schema 决定，`process_case_results.py` 只强校验
`caseNo` 为 str/null（非字符串直接整体报错、无法定位），且统计里只有 `missingCaseNoCount`，
未统计法院名与数据来源缺失。本脚本作为交付前独立门禁补上这两个 P0 缺口：

  1. 案号字段类型容错 + 精确定位：`caseNo` 为 int/float/bool/list/dict 等非字符串类型时，
     不整体崩溃，而是逐条记录「第 N 条 案号类型异常（实际类型/取值）」并拦截。
  2. 出处三字段齐全度统计：分别统计案号（caseNo）、法院（trialCourt.name）、
     数据来源/出处（dataFrom）的非空条数与缺失条数，任一字段缺失比例超过阈值即拦截。

验收口径「返回判例带案号 / 法院 / 出处」→ 三者任一大面积缺失应拦截。

用法：
    python3 scripts/validate_case_fields.py <交付集或完整集 JSON> [--max-missing-ratio 0.3] [--json]

退出码：
    0  通过
    1  拦截（存在阻断项）
    2  输入无法读取或结构不符合契约
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

DEFAULT_MAX_MISSING_RATIO = 0.3
TRACKED_FIELDS = (
    ("caseNo", "案号"),
    ("trialCourt.name", "法院"),
    ("dataFrom", "出处（数据来源）"),
)


class ContractError(ValueError):
    """输入 JSON 不符合 case-retrieval-handoff 契约。"""


def load_cases(path: Path) -> tuple[dict[str, Any], list[Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"无法读取有效 JSON：{path}：{exc}") from exc
    if not isinstance(payload, dict):
        raise ContractError(f"顶层 JSON 必须是对象：{path}")
    cases = payload.get("cases")
    if not isinstance(cases, list):
        raise ContractError(f"缺少数组字段 cases：{path}")
    return payload, cases


def type_name(value: Any) -> str:
    return {
        type(None): "null",
        bool: "bool",
        int: "int",
        float: "float",
        str: "str",
        list: "list",
        dict: "dict",
    }.get(type(value), type(value).__name__)


def brief(value: Any, limit: int = 40) -> str:
    try:
        text = json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        text = repr(value)
    return text if len(text) <= limit else text[:limit] + "…"


def nonblank_text(value: Any) -> str | None:
    """仅当 value 是非空白字符串时返回去首尾空白的文本，否则 None。"""
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def read_field(domain: dict[str, Any], dotted: str) -> tuple[Any, bool]:
    """按点号路径取值。返回 (取到的值, 路径是否可达)。路径中间不是对象时视为不可达。"""
    current: Any = domain
    for part in dotted.split("."):
        if not isinstance(current, dict):
            return None, False
        if part not in current:
            return None, False
        current = current[part]
    return current, True


def validate(payload: dict[str, Any], cases: list[Any], max_missing_ratio: float) -> dict[str, Any]:
    blocking: list[str] = []
    warnings: list[str] = []
    total = len(cases)
    present: dict[str, int] = {dotted: 0 for dotted, _ in TRACKED_FIELDS}
    missing_index: dict[str, list[int]] = {dotted: [] for dotted, _ in TRACKED_FIELDS}
    type_errors: list[str] = []

    if total == 0:
        blocking.append("cases 为空：没有任何判例可交付，禁止输出案例清单")

    for index, case in enumerate(cases, start=1):
        if not isinstance(case, dict):
            blocking.append(f"第 {index} 条案例不是对象（实际 {type_name(case)}）")
            continue
        domain = case.get("caseDomain")
        if not isinstance(domain, dict):
            blocking.append(f"第 {index} 条案例缺少对象字段 caseDomain（实际 {type_name(domain)}）")
            continue

        for dotted, label in TRACKED_FIELDS:
            raw, reachable = read_field(domain, dotted)
            if not reachable:
                missing_index[dotted].append(index)
                continue
            if raw is None:
                missing_index[dotted].append(index)
                continue
            if not isinstance(raw, str):
                # P0 隐患①：类型异常不整体崩溃，逐条定位后拦截。
                type_errors.append(
                    f"第 {index} 条 {label} 字段类型异常："
                    f"{dotted} 应为字符串或 null，实际 {type_name(raw)}，取值 {brief(raw)}"
                )
                missing_index[dotted].append(index)
                continue
            if nonblank_text(raw) is None:
                missing_index[dotted].append(index)
                continue
            present[dotted] += 1

    blocking.extend(type_errors)

    field_stats: list[dict[str, Any]] = []
    for dotted, label in TRACKED_FIELDS:
        missing = missing_index[dotted]
        ratio = (len(missing) / total) if total else 1.0
        field_stats.append(
            {
                "field": dotted,
                "label": label,
                "presentCount": present[dotted],
                "missingCount": len(missing),
                "missingRatio": round(ratio, 4),
                "missingCaseIndexes": missing[:20],
            }
        )
        if total == 0:
            continue
        if ratio > max_missing_ratio:
            blocking.append(
                f"{label}（{dotted}）缺失 {len(missing)}/{total} 条，缺失率 {ratio:.0%} "
                f"超过阈值 {max_missing_ratio:.0%}：属大面积缺失，禁止交付"
            )
        elif missing:
            warnings.append(
                f"{label}（{dotted}）缺失 {len(missing)}/{total} 条"
                f"（第 {', '.join(str(i) for i in missing[:10])} 条）："
                f"未超阈值，交付时须逐条注明「未提供」，禁止推断补全"
            )

    schema_version = payload.get("schemaVersion")
    if schema_version != "case-retrieval-handoff/v1":
        warnings.append(
            f"schemaVersion 非 case-retrieval-handoff/v1（实际 {brief(schema_version)}）："
            "确认输入确实来自 process_case_results.py"
        )

    return {
        "totalCases": total,
        "setType": payload.get("setType"),
        "maxMissingRatio": max_missing_ratio,
        "fields": field_stats,
        "blocking": blocking,
        "warnings": warnings,
        "passed": not blocking,
    }


def print_human(result: dict[str, Any], path: Path) -> None:
    stream = sys.stdout if result["passed"] else sys.stderr
    print(f"输入：{path}", file=stream)
    print(
        f"集合类型：{result['setType'] or '未标注'}；案例数：{result['totalCases']}；"
        f"缺失率阈值：{result['maxMissingRatio']:.0%}",
        file=stream,
    )
    print("字段齐全度：", file=stream)
    for item in result["fields"]:
        print(
            f"  - {item['label']}（{item['field']}）："
            f"齐全 {item['presentCount']} 条 / 缺失 {item['missingCount']} 条"
            f"（{item['missingRatio']:.0%}）",
            file=stream,
        )
    if result["warnings"]:
        print(f"提示（不拦截）共 {len(result['warnings'])} 项：", file=stream)
        for item in result["warnings"]:
            print(f"  - {item}", file=stream)
    if result["blocking"]:
        print(f"拦截清单，共 {len(result['blocking'])} 项：", file=stream)
        for item in result["blocking"]:
            print(f"  - {item}", file=stream)
        print("字段映射校验未通过：禁止交付案例清单或生成报告。", file=stream)
    else:
        print("字段映射校验通过：案号 / 法院 / 出处 三项均满足交付门槛。", file=stream)


def ratio_value(value: str) -> float:
    try:
        number = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("必须是 0 到 1 之间的小数") from exc
    if not 0.0 <= number <= 1.0:
        raise argparse.ArgumentTypeError("必须是 0 到 1 之间的小数")
    return number


def main() -> int:
    parser = argparse.ArgumentParser(
        description="模式A 字段映射门禁：校验交付集案号 / 法院 / 出处三项字段的类型与齐全度",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例：\n"
            "  python3 scripts/validate_case_fields.py ./tmp/cases_delivery.json\n"
            "  python3 scripts/validate_case_fields.py ./tmp/cases_delivery.json"
            " --max-missing-ratio 0.2 --json\n"
        ),
    )
    parser.add_argument(
        "input_json",
        type=Path,
        help="process_case_results.py 产出的 cases_delivery.json 或 cases_full.json",
    )
    parser.add_argument(
        "--max-missing-ratio",
        type=ratio_value,
        default=DEFAULT_MAX_MISSING_RATIO,
        help=f"单个字段允许的最大缺失比例，超过即拦截（默认 {DEFAULT_MAX_MISSING_RATIO}）",
    )
    parser.add_argument("--json", action="store_true", help="以 JSON 输出校验结果，便于日志留痕")
    args = parser.parse_args()

    try:
        payload, cases = load_cases(args.input_json)
    except ContractError as exc:
        print(f"字段映射校验失败：{exc}", file=sys.stderr)
        return 2

    result = validate(payload, cases, args.max_missing_ratio)

    if args.json:
        stream = sys.stdout if result["passed"] else sys.stderr
        print(json.dumps(result, ensure_ascii=False, indent=2), file=stream)
    else:
        print_human(result, args.input_json)

    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
