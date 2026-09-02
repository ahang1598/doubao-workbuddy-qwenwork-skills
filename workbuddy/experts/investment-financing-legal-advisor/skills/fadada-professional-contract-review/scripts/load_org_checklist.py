#!/usr/bin/env python3
"""
load_org_checklist.py — 组织级标准清单加载器（B 侧消费 A 侧产物）。

优先扫描 iTerms v2 清单：
  ~/legal-checklists-iterms/{owner_org}/{business_type}/latest.json

旧 checklist-v1 清单仍作为 fallback：
  ~/legal-checklists/{owner_org}/{business_type}/latest.json

成功加载后输出原始 checklist，并将 iTerms review_items[] 或 legacy items[]
统一规范化为 normalized_rules[]，供 SKILL.md 注入审查规则上下文。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

DEFAULT_LEGACY_ROOT = Path.home() / "legal-checklists"
DEFAULT_ITERMS_ROOT = Path.home() / "legal-checklists-iterms"
CHECKLIST_GENERATOR_DIR = Path(__file__).resolve().parent.parent.parent / "合同审查清单生成器"
IMPORT_ITERMS_XLSX_SCRIPT = CHECKLIST_GENERATOR_DIR / "scripts" / "import_iterms_checklist_xlsx.py"

import checklist_schema

SCHEMA_CANDIDATES = {
    "iterms": [
        Path(__file__).resolve().parent.parent.parent
        / "合同审查清单生成器"
        / "schemas"
        / "iterms-checklist-v2.json",
        Path(__file__).resolve().parent.parent / "schemas" / "iterms-checklist-v2.json",
    ],
    "legacy": [
        Path(__file__).resolve().parent.parent.parent
        / "合同审查清单生成器"
        / "schemas"
        / "checklist-v1.json",
        Path(__file__).resolve().parent.parent / "schemas" / "checklist-v1.json",
    ],
}


def load_json(path: Path) -> dict[str, Any]:
    # utf-8-sig：兼容带 BOM 的文件。出处技能导出的 schema/清单带 UTF-8 BOM，
    # 用 utf-8 读会抛 "Unexpected UTF-8 BOM"，此前被 find_schema 的 except 吞掉，
    # 表现为「schema 找不到」而非「schema 读不了」。
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("清单 JSON 顶层必须为 object")
    return payload


def is_excel_path(path: Path) -> bool:
    return path.suffix.lower() in {".xlsx", ".xlsm"}


def business_code(business_type: str) -> str:
    code = re.sub(r"[^A-Za-z0-9]", "", business_type).upper()
    return code[:12] or "AUTO"


def import_excel_payload(path: Path, args: argparse.Namespace) -> tuple[dict[str, Any] | None, list[str]]:
    if not IMPORT_ITERMS_XLSX_SCRIPT.exists():
        return None, [f"未找到 Excel 导入脚本: {IMPORT_ITERMS_XLSX_SCRIPT}"]

    with tempfile.TemporaryDirectory(prefix="iterms-checklist-xlsx-") as tmp_dir:
        output = Path(tmp_dir) / "checklist.json"
        base_cmd = [
            sys.executable,
            str(IMPORT_ITERMS_XLSX_SCRIPT),
            "--input",
            str(path),
            "--output",
            str(output),
        ]
        result = subprocess.run(base_cmd, text=True, capture_output=True)
        if result.returncode != 0:
            year = datetime.now().year
            fallback_cmd = base_cmd + [
                "--business-type",
                args.business_type,
                "--position",
                args.position,
                "--scope",
                "library",
                "--version",
                "0.0.0",
                "--owner-org",
                args.owner_org or "_default",
                "--checklist-id",
                f"CL-ITM-{business_code(args.business_type)}-{year}-AUTO",
                "--checklist-name",
                f"{args.business_type}审查清单",
            ]
            result = subprocess.run(fallback_cmd, text=True, capture_output=True)
        if result.returncode != 0:
            details = [line for line in (result.stderr or result.stdout).splitlines() if line.strip()]
            return None, details or [f"Excel 导入失败，退出码 {result.returncode}"]
        try:
            return load_json(output), []
        except (json.JSONDecodeError, ValueError) as exc:
            return None, [str(exc)]


SCHEMA_FILENAMES = {
    "iterms": "iterms-checklist-v2.json",
    "legacy": "checklist-v1.json",
}


def discover_schema(fmt: str) -> Path | None:
    """在同级技能目录中按文件名发现 schema。

    历史问题：`SCHEMA_CANDIDATES` 把出处技能的目录名写死为「合同审查清单生成器」，
    而该技能此后被改名并迁移（仓库为 `研发中/合同规则/contract-review-rule-list-generator`，
    安装态为 `custom/审查规则地图生成`），硬编码路径全部落空——完整 schema 校验因此
    长期是死代码，且因降级静默而无人察觉。改为按文件名在若干层祖先目录下发现，
    对改名与目录调整都不敏感。
    """
    filename = SCHEMA_FILENAMES.get(fmt)
    if not filename:
        return None
    override = os.environ.get("RICHEE_CHECKLIST_SCHEMA_DIR")
    if override:
        candidate = Path(override).expanduser() / filename
        if candidate.exists():
            return candidate
    here = Path(__file__).resolve().parent
    # 逐层上溯：覆盖「安装态 custom/<skill>/schemas」与「仓库 <类目>/<skill>/schemas」两种布局
    for ancestor in list(here.parents)[:5]:
        # 1–4 层通配：覆盖安装态 `custom/<skill>/schemas`（1 层）与
        # 仓库 `skills/<阶段>/<类目>/<skill>/schemas`（3 层）等布局
        patterns = [f"{'*/' * depth}schemas/{filename}" for depth in range(1, 5)]
        for pattern in patterns:
            for match in sorted(ancestor.glob(pattern)):
                if match.is_file():
                    return match
    return None


def find_schema(fmt: str) -> dict[str, Any] | None:
    candidates = list(SCHEMA_CANDIDATES[fmt])
    discovered = discover_schema(fmt)
    if discovered is not None:
        candidates.append(discovered)
    for candidate in candidates:
        if not candidate.exists():
            continue
        try:
            return load_json(candidate)
        except (json.JSONDecodeError, ValueError):
            continue
    return None


def detect_format(payload: dict[str, Any]) -> str | None:
    schema_version = payload.get("schema_version")
    if schema_version == "iterms-2.0":
        return "iterms"
    if schema_version == "1.0":
        return "legacy"
    if isinstance(payload.get("data"), list):
        return "iterms"
    if isinstance(payload.get("items"), list):
        return "legacy"
    return None


def find_checklist(
    business_type: str, owner_org: str | None, root: Path
) -> tuple[Path | None, list[str]]:
    """搜索路径优先级：owner_org/latest -> owner_org/v* -> _default/latest -> any_org/latest。"""
    searched: list[str] = []
    if owner_org:
        target = root / owner_org / business_type / "latest.json"
        searched.append(str(target))
        if target.exists():
            return target, searched
        version_dir = root / owner_org / business_type
        if version_dir.exists():
            versions = sorted(version_dir.glob("v*.json"), reverse=True)
            if versions:
                searched.append(str(versions[0]))
                return versions[0], searched

    target = root / "_default" / business_type / "latest.json"
    searched.append(str(target))
    if target.exists():
        return target, searched

    if root.exists():
        for org_dir in root.iterdir():
            if not org_dir.is_dir() or org_dir.name.startswith("_"):
                continue
            candidate = org_dir / business_type / "latest.json"
            searched.append(str(candidate))
            if candidate.exists():
                return candidate, searched
    return None, searched


def split_by_impact(errors: list[str]) -> tuple[list[str], list[str]]:
    """把 schema 错误分为「阻断」与「提示」。

    判据是**是否影响注入的审查规则**：`data[...]` 下的错误会让畸形规则进入
    normalized_rules[]，属技能契约 D1-S5「禁止错误格式清单静默注入」要防的情形，
    必须阻断；`source_meta` 等出处元数据的错误只是生成器与 schema 漂移，
    不影响审查结论，阻断反而会让在用清单加载失败（实测 6 份真实清单中有 2 份
    仅因 source_meta 字段漂移而不合格）。
    """
    blocking = [e for e in errors if e.split(":", 1)[0].startswith("data")]
    advisory = [e for e in errors if e not in blocking]
    return blocking, advisory


def validate_payload(payload: dict[str, Any], schema: dict[str, Any] | None,
                     fmt: str) -> tuple[list[str], str]:
    """返回 (错误列表, 校验模式)。

    模式必须回报给调用方：`minimal` 只检查顶层必填字段与 data 非空，**不校验
    data[] 内每条规则的结构**——格式损坏的规则仍会被注入 normalized_rules[]。
    技能契约 D1-S5 明令「禁止错误格式清单静默注入」，故降级必须显式可见，
    不能与「完整校验且零错误」返回同样的结果。
    """
    if schema is None:
        return minimal_validate(payload, fmt), [], "minimal_no_schema"

    # 内置零依赖校验器：无论是否装了 jsonschema 都先跑一遍
    native_errors, unsupported = checklist_schema.validate(payload, schema)

    try:
        import jsonschema  # type: ignore
    except ImportError:
        # 未装官方库：以内置校验器为准。未支持关键字必须如实回报，
        # 否则又变回「静默漏检」——这正是本模块要避免的。
        mode = "native"
        if unsupported:
            mode = "partial_unsupported:" + ",".join(unsupported)
        blocking, advisory = split_by_impact(native_errors)
        return blocking, advisory, mode

    official: list[str] = []
    validator = jsonschema.Draft202012Validator(schema)
    for err in sorted(validator.iter_errors(payload), key=lambda e: list(e.absolute_path)):
        path = "/".join(str(p) for p in err.absolute_path) or "<root>"
        official.append(f"{path}: {err.message}")

    # 交叉验证：两个实现结论不一致时以官方为准，但把分歧暴露出来供修内置校验器
    blocking, advisory = split_by_impact(official)
    if bool(official) != bool(native_errors):
        advisory.append(
            f"[内置校验器分歧] 官方判 {len(official)} 项错误、内置判 "
            f"{len(native_errors)} 项；本次以官方结论为准，请核对 checklist_schema.py"
        )
    return blocking, advisory, "jsonschema"


def minimal_validate(payload: dict[str, Any], fmt: str) -> list[str]:
    if fmt == "iterms":
        required = (
            "checklist_id",
            "schema_version",
            "business_type",
            "position",
            "scope",
            "version",
            "data",
        )
        errors = [f"缺少必填字段: {field}" for field in required if field not in payload]
        if payload.get("schema_version") != "iterms-2.0":
            errors.append("schema_version 必须为 iterms-2.0")
        if not isinstance(payload.get("data"), list) or not payload.get("data"):
            errors.append("data 必须为非空数组")
        return errors

    required = ("checklist_id", "schema_version", "business_type", "position", "scope", "items")
    errors = [f"缺少必填字段: {field}" for field in required if field not in payload]
    if payload.get("schema_version") != "1.0":
        errors.append("schema_version 必须为 1.0")
    if not isinstance(payload.get("items"), list) or not payload.get("items"):
        errors.append("items 必须为非空数组")
    return errors


def position_match(checklist_position: str, requested_position: str) -> bool:
    return checklist_position == requested_position or checklist_position == "neutral"


ITERMS_RISK_TYPE_MAP = {
    "法律风险": "legal",
    "交易风险": "transaction",
    "结构风险": "structure",
    "其他风险": "other",
}
ITERMS_SEVERITY_MAP = {"高风险": "high", "中风险": "mid", "低风险": "low"}
ALLOWED_EVIDENCE_TAGS = ("[用规]", "[要点]", "[法规]", "[惯例]")


def split_comma(text: Any) -> list[str]:
    """元素字段按英文逗号拆分（iTerms 多要素只用英文逗号）。"""
    return [part.strip() for part in str(text or "").split(",") if part.strip()]


def split_lines(text: Any) -> list[str]:
    return [part.strip() for part in str(text or "").splitlines() if part.strip()]


def pick_source_tag(note: str, laws: list[str], default: str = "[用规]") -> str:
    """从 iTerms 备注字段解析依据来源标签。"""
    for tag in ALLOWED_EVIDENCE_TAGS:
        if tag in note:
            return tag
    if laws:
        return "[法规]"
    return default


def normalize_iterms_rules(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []
    group_ids: dict[str, str] = {}
    for index, record in enumerate(payload.get("data", []), start=1):
        if not isinstance(record, dict):
            continue
        group_name = record.get("审查项分组", "")
        if group_name not in group_ids:
            group_ids[group_name] = f"G-{len(group_ids) + 1:03d}"
        note = str(record.get("备注", ""))
        laws = split_lines(record.get("法律依据", ""))
        cases = split_lines(record.get("参考案例", ""))
        rule = {
            "rule_id": f"RI-{index:03d}",
            "group_id": group_ids[group_name],
            "group_name": group_name,
            "item_name": record.get("审查项名称", ""),
            "risk_type": ITERMS_RISK_TYPE_MAP.get(record.get("风险类型"), "other"),
            "severity": ITERMS_SEVERITY_MAP.get(record.get("风险等级"), "mid"),
            "target_clause_element": record.get("待审查条款要素", ""),
            "related_clause_elements": split_comma(record.get("关联条款要素", "")),
            "review_rule": record.get("审查规则", ""),
            "risk_description": record.get("风险说明", ""),
            "suggestion": record.get("修改建议", ""),
            "suggestion_direction": record.get("修改方向", ""),
            "reference_clause": record.get("参考条款", ""),
            "laws": laws,
            "cases": cases,
            "source_tag": pick_source_tag(note, laws),
            "source_detail": note,
            "format": "iterms",
        }
        rules.append(rule)
    return rules


def normalize_legacy_rules(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []
    for item in payload.get("items", []):
        if not isinstance(item, dict):
            continue
        clause_type = item.get("clause_type", "")
        check_payload = item.get("check_payload", {})
        review_rule = ""
        related_elements: list[str] = []
        if isinstance(check_payload, dict):
            review_rule = str(check_payload.get("prompt", "") or check_payload.get("missing_signal", ""))
            fields = check_payload.get("fields", [])
            if isinstance(fields, list):
                related_elements = [str(field) for field in fields if field]
        if not review_rule:
            review_rule = str(item.get("problem_pattern", ""))
        legacy_tag = item.get("source_tag")
        if not (isinstance(legacy_tag, str) and legacy_tag in ALLOWED_EVIDENCE_TAGS):
            legacy_tag = "[法规]" if item.get("laws") else "[用规]"
        rules.append(
            {
                "rule_id": item.get("item_id"),
                "group_id": None,
                "group_name": item.get("group_name", ""),
                "item_name": item.get("item_name", clause_type),
                "risk_type": item.get("risk_dimension", "civil"),
                "severity": item.get("severity", "mid"),
                "target_clause_element": clause_type,
                "related_clause_elements": related_elements,
                "review_rule": review_rule,
                "risk_description": item.get("problem_pattern", ""),
                "suggestion": item.get("suggested_wording", ""),
                "suggestion_direction": item.get("suggested_wording", ""),
                "reference_clause": "",
                "laws": [],
                "cases": [],
                "source_tag": legacy_tag,
                "source_detail": item.get("source_detail", ""),
                "format": "legacy",
            }
        )
    return rules


def normalize_rules(payload: dict[str, Any], fmt: str) -> list[dict[str, Any]]:
    if fmt == "iterms":
        return normalize_iterms_rules(payload)
    return normalize_legacy_rules(payload)


def count_groups(payload: dict[str, Any], fmt: str) -> int:
    if fmt != "iterms":
        return 0
    names = {
        str(record.get("审查项分组", ""))
        for record in payload.get("data", [])
        if isinstance(record, dict)
    }
    names.discard("")
    return len(names)


def load_target(
    path: Path, requested_format: str, args: argparse.Namespace
) -> tuple[dict[str, Any] | None, str | None, list[str], str | None]:
    if is_excel_path(path):
        if requested_format == "legacy":
            return None, "iterms", ["Excel 清单只支持导入为 iTerms v2 格式，不能按 legacy 加载"], "format_mismatch"
        payload, import_errors = import_excel_payload(path, args)
        if import_errors or payload is None:
            return payload, "iterms", import_errors, "excel_import_invalid"
    else:
        try:
            payload = load_json(path)
        except json.JSONDecodeError as exc:
            return None, None, [str(exc)], "json_invalid"
        except ValueError as exc:
            return None, None, [str(exc)], "json_invalid"

    detected = detect_format(payload)
    if detected is None:
        return payload, None, ["无法识别清单格式：schema_version 既非 iterms-2.0 也非 1.0"], "format_unknown"
    if requested_format != "auto" and detected != requested_format:
        return payload, detected, [f"请求格式为 {requested_format}，但文件格式为 {detected}"], "format_mismatch"

    errors, advisory, mode = validate_payload(payload, find_schema(detected), detected)
    args.validation_mode = mode          # 供成功输出组装时回报
    args.schema_advisory = advisory      # 非阻断的 schema 漂移，作为 warning 呈现
    if errors:
        return payload, detected, errors, "schema_invalid"
    return payload, detected, [], None


def output_not_found(searched: list[str]) -> int:
    print(json.dumps({"ok": False, "reason": "not_found", "searched": searched}, ensure_ascii=False))
    return 1


def output_invalid(reason: str, path: Path, errors: list[str], searched: list[str]) -> int:
    print(
        json.dumps(
            {
                "ok": False,
                "reason": reason,
                "path": str(path),
                "errors": errors,
                "searched": searched,
            },
            ensure_ascii=False,
        )
    )
    return 3 if reason in {"schema_invalid", "format_mismatch", "format_unknown", "excel_import_invalid"} else 2


def build_success(payload: dict[str, Any], fmt: str, path: Path, requested_position: str,
                  validation_mode: str = "unknown",
                  schema_advisory: list[str] | None = None) -> dict[str, Any]:
    normalized_rules = normalize_rules(payload, fmt)
    out: dict[str, Any] = {
        "ok": True,
        "format": fmt,
        "schema_version": payload.get("schema_version"),
        "checklist_id": payload["checklist_id"],
        "version": payload.get("version"),
        "scope": payload.get("scope"),
        "business_type": payload["business_type"],
        "position": payload["position"],
        "path": str(path),
        "source_artifact": "excel" if is_excel_path(path) else "json",
        "validation_mode": validation_mode,
        "items_count": len(normalized_rules),
        "groups_count": count_groups(payload, fmt),
        "normalized_rules": normalized_rules,
        "has_transaction_profile": bool(payload.get("transaction_profile")),
        "has_cross_doc_rules": bool(payload.get("cross_doc_rules")),
        "has_calc_rules": bool(payload.get("calc_rules")),
        "has_lint_rules": bool(payload.get("lint_rules")),
        "checklist": payload,
    }
    if payload.get("transaction_profile"):
        out["transaction_profile"] = payload["transaction_profile"]
    if not position_match(payload.get("position", ""), requested_position):
        out["warning"] = (
            f"清单立场为 {payload['position']}，与本次审查立场 {requested_position} 不一致；"
            f"将注入但建议人工复核规则适用性。"
        )
    if validation_mode.startswith("minimal"):
        reason = ("本机未安装 jsonschema" if validation_mode == "minimal_no_jsonschema"
                  else "未找到该格式的 schema 文件")
        out.setdefault("warnings", []).append(
            f"清单只做了最小校验（{reason}）：仅核对顶层必填字段与 data 非空，"
            f"**未逐条校验 data[] 内规则结构**。若清单来源不可靠，注入的 "
            f"normalized_rules 可能含格式错误项，建议人工抽查。"
        )
    for item in (schema_advisory or []):
        out.setdefault("warnings", []).append(
            f"清单 schema 漂移（不影响注入的审查规则，未阻断）：{item}")
    if validation_mode.startswith("partial_unsupported:"):
        kws = validation_mode.split(":", 1)[1]
        out.setdefault("warnings", []).append(
            f"清单为**部分校验**：schema 使用了内置校验器不支持的关键字（{kws}），"
            f"相关节点未被断言。其余部分已按 schema 校验通过。"
            f"如需完整校验，安装 jsonschema 后重跑；或在 checklist_schema.py 中补齐该关键字。"
        )
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--business-type", required=True)
    parser.add_argument("--position", required=True)
    parser.add_argument("--owner-org", default=None)
    parser.add_argument(
        "--format",
        default="auto",
        choices=["auto", "iterms", "legacy"],
        help="清单格式。auto 优先加载 iTerms v2，未命中再 fallback legacy。",
    )
    parser.add_argument(
        "--iterms-root",
        default=str(DEFAULT_ITERMS_ROOT),
        help="iTerms 清单库根目录，默认 ~/legal-checklists-iterms",
    )
    parser.add_argument(
        "--root",
        default=str(DEFAULT_LEGACY_ROOT),
        help="legacy 清单库根目录，默认 ~/legal-checklists",
    )
    parser.add_argument("--checklist-path", default=None, help="显式指定清单文件路径，绕过自动查找")
    args = parser.parse_args()

    searched: list[str] = []
    if args.checklist_path:
        target = Path(args.checklist_path).expanduser().resolve()
        searched.append(str(target))
        if not target.exists():
            return output_not_found(searched)
        payload, fmt, errors, reason = load_target(target, args.format, args)
        if errors or payload is None or fmt is None:
            return output_invalid(reason or "schema_invalid", target, errors, searched)
        print(json.dumps(build_success(payload, fmt, target, args.position, getattr(args, "validation_mode", "unknown"), getattr(args, "schema_advisory", [])), ensure_ascii=False, indent=2))
        return 0

    roots: list[tuple[str, Path]] = []
    if args.format in ("auto", "iterms"):
        roots.append(("iterms", Path(args.iterms_root).expanduser().resolve()))
    if args.format in ("auto", "legacy"):
        roots.append(("legacy", Path(args.root).expanduser().resolve()))

    for fmt, root in roots:
        target, root_searched = find_checklist(args.business_type, args.owner_org, root)
        searched.extend(root_searched)
        if target is None:
            continue
        payload, detected_fmt, errors, reason = load_target(target, fmt, args)
        if errors or payload is None or detected_fmt is None:
            return output_invalid(reason or "schema_invalid", target, errors, searched)
        print(json.dumps(build_success(payload, detected_fmt, target, args.position, getattr(args, "validation_mode", "unknown"), getattr(args, "schema_advisory", [])), ensure_ascii=False, indent=2))
        return 0

    return output_not_found(searched)


if __name__ == "__main__":
    sys.exit(main())
