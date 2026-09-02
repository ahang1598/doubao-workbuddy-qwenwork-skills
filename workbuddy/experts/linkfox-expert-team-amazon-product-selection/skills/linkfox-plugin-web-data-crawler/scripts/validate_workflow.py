#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
前端采集 workflow JSON 契约校验器。

用法:
    python validate_workflow.py <workflow.json>

校验规则从 tools/*.md 的 frontmatter 中自动读取，无需手动同步。
新增/修改 action 字段时只需更新 tools/<action>.md 的 frontmatter 区块。

退出码: 0 通过, 1 不通过。
"""

import json
import os
import re
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent.parent / "tools"

# ═══════════════════════════════════════════
#  Frontmatter 解析
# ═══════════════════════════════════════════


def _parse_frontmatter(text):
    """提取 markdown 文件中 ---JSON--- 格式的 frontmatter。"""
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return None
    return json.loads(m.group(1))


def _load_action_schemas():
    """遍历 tools/*.md，从 frontmatter 加载所有 action 的字段 schema。

    selector-fallback.md 和 INDEX.md 没有 actionCode，自动跳过。
    """
    schemas = {}
    for md_file in sorted(TOOLS_DIR.glob("*.md")):
        with open(md_file, "r", encoding="utf-8") as f:
            text = f.read()
        fm = _parse_frontmatter(text)
        if not fm or "actionCode" not in fm:
            continue
        schemas[fm["actionCode"]] = fm
    return schemas


# ═══════════════════════════════════════════
#  类型检查
# ═══════════════════════════════════════════


def _is_nonempty_str_array(v):
    return isinstance(v, list) and len(v) > 0 and all(isinstance(x, str) for x in v)


def _check_type(value, type_str):
    """根据 frontmatter 中声明的 type 校验值类型。"""
    if type_str == "string":
        return isinstance(value, str) and bool(value)
    if type_str == "number":
        return isinstance(value, (int, float))
    if type_str == "boolean":
        return isinstance(value, bool)
    if type_str == "array":
        return isinstance(value, list)
    if type_str == "object":
        return isinstance(value, dict)
    if type_str == "string|string[]":
        return isinstance(value, str) and bool(value) or _is_nonempty_str_array(value)
    if type_str == "string|number":
        return isinstance(value, (str, int, float))
    if type_str == "string|array":
        return isinstance(value, (str, list))
    # 未知类型宽容放过
    return True


# ═══════════════════════════════════════════
#  校验逻辑
# ═══════════════════════════════════════════


def _validate_field(ctx, field_name, field_def, step, prefix=""):
    """校验单个字段，返回错误信息列表。

    field_def 可以是:
      - 简单 {type, required, enum, const}
      - 带嵌套 schema 的 {type, required, schema: {...}}
    """
    errors = []
    exists = field_name in step
    path = f"{prefix}.{field_name}" if prefix else field_name

    # ── Required 解析 ──
    required = field_def.get("required", False)
    if isinstance(required, dict):
        # 条件必须: { "when": { "extractType": "attribute" } }
        cond = required.get("when", {})
        required = all(str(step.get(k)) == str(v) for k, v in cond.items())

    if required and not exists:
        errors.append(f"{ctx}: 缺少 {path}")
        return errors

    if not exists:
        return errors  # 可选字段，跳过

    value = step[field_name]

    # ── 类型检查 ──
    expected_type = field_def.get("type")
    if expected_type and not _check_type(value, expected_type):
        errors.append(f"{ctx}: {path} 类型错误（期望 {expected_type}，得到 {type(value).__name__}）")

    # ── enum 检查 ──
    if "enum" in field_def and value not in field_def["enum"]:
        errors.append(f"{ctx}: {path} 值非法（{value!r}），应为 {field_def['enum']}")

    # ── const 检查 ──
    if "const" in field_def and value != field_def["const"]:
        errors.append(f"{ctx}: {path} 必须为 {field_def['const']!r}，得到 {value!r}")

    # ── 嵌套 schema ──
    if "schema" in field_def and isinstance(value, dict):
        sub_schema = field_def["schema"]
        for sub_name, sub_def in sub_schema.items():
            errors.extend(_validate_field(ctx, sub_name, sub_def, value, prefix=path))

    return errors


def validate(obj):
    """校验 workflow JSON，返回错误信息列表。"""
    errors = []

    if not isinstance(obj, dict):
        return ["顶层必须是 JSON 对象"]

    wf = obj.get("workflowName")
    if not isinstance(wf, str) or not wf.strip():
        errors.append("顶层缺少 workflowName（非空字符串）")

    steps = obj.get("steps")
    if not isinstance(steps, list) or len(steps) == 0:
        errors.append("顶层缺少 steps（非空数组）")
        return errors

    schemas = _load_action_schemas()
    if not schemas:
        errors.append("未找到任何 action frontmatter，请检查 tools/*.md")
        return errors

    # LOG/IF/EXTRACT_SCRIPT 不需要 tabKey
    _no_tabkey_codes = {"LOOP", "IF", "EXTRACT_SCRIPT"}

    for i, step in enumerate(steps, 1):
        ctx = f"step[{i}]"
        if not isinstance(step, dict):
            errors.append(f"{ctx}: 必须是对象")
            continue

        code = step.get("actionCode")
        if not code:
            errors.append(f"{ctx}: 缺少 actionCode")
            continue

        schema = schemas.get(code)
        if schema is None:
            errors.append(f"{ctx}: actionCode 非法（{code!r}），合法值: {sorted(schemas.keys())}")
            continue

        # ── 全局通用校验 ──

        # tabKey（LOOP/IF/EXTRACT_SCRIPT 除外）
        if code not in _no_tabkey_codes:
            if not isinstance(step.get("tabKey"), str) or not step.get("tabKey"):
                errors.append(f"{ctx}({code}): 缺少 tabKey")

        # allowFailure 类型
        if "allowFailure" in step and not isinstance(step["allowFailure"], bool):
            errors.append(f"{ctx}({code}): allowFailure 必须是 boolean")

        # selector 格式
        sel = step.get("selector")
        if "selector" in step and sel is not None:
            if isinstance(sel, str):
                if not sel:
                    errors.append(f"{ctx}({code}): selector 不能为空字符串")
            elif not _is_nonempty_str_array(sel):
                errors.append(f"{ctx}({code}): selector 必须是非空字符串或非空字符串数组")

        # ── 从 frontmatter 读取的字段校验 ──
        fields = schema.get("fields", {})
        for field_name, field_def in fields.items():
            errors.extend(_validate_field(ctx, field_name, field_def, step))

        # ── 约束规则 ──

        # requires_one_of: 至少存在一项
        for group in schema.get("requires_one_of", []):
            if not any(f in step for f in group):
                errors.append(f"{ctx}({code}): {', '.join(group)} 至少需要存在一项")

        # mutually_exclusive: 互斥
        for group in schema.get("mutually_exclusive", []):
            present = [f for f in group if f in step]
            if len(present) > 1:
                errors.append(f"{ctx}({code}): {', '.join(group)} 互斥，不能同时存在")

    return errors


# ═══════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

    if len(sys.argv) != 2:
        print("用法: python validate_workflow.py <workflow.json>", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]
    try:
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
    except FileNotFoundError:
        print(f"错误: 文件不存在: {path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"错误: JSON 解析失败: {e}", file=sys.stderr)
        sys.exit(1)

    errors = validate(obj)
    if errors:
        print(f"[FAIL] 校验未通过（{len(errors)} 处）:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    steps = obj.get("steps", [])
    print(f"[OK] 校验通过: workflowName={obj.get('workflowName')!r}, steps={len(steps)}")
    sys.exit(0)


if __name__ == "__main__":
    main()
