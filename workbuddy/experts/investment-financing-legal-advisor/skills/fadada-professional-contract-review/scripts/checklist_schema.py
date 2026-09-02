#!/usr/bin/env python3
"""零依赖的 JSON Schema 子集校验器（组织清单专用）。

为什么自己写：官方 `jsonschema` 的依赖链含 `rpds-py` 编译型二进制 wheel，
平台 × Python 版本双绑定，要覆盖 mac(x86_64/arm64)/Windows/Linux × 多个 Python
小版本需内置十余个二进制 wheel——对跨平台技能包是把"少一个包"换成"少一个正确的
二进制"。而 `iterms-checklist-v2.json` 实际只用到 14 个基础关键字，无
`oneOf/anyOf/allOf/not/if-then-else/patternProperties`，`$ref` 也只指向本文件
`$defs`，故原生实现即可覆盖。

**能力边界必须可见**：遇到本模块不认识的关键字时，**不静默跳过**，而是记入
`unsupported` 并由调用方回报（`validation_mode` 带 `partial_unsupported:<kw>`）。
静默漏检正是本轮修复的那类缺陷，不能在这里重新引入。

`format` 按 JSON Schema 规范默认语义处理：仅注解、不断言，故不计入 unsupported。
"""

from __future__ import annotations

import re
from typing import Any

# 本模块实现断言语义的关键字
SUPPORTED = {
    "type", "properties", "required", "items", "additionalProperties",
    "enum", "const", "pattern", "minLength", "maxLength",
    "minItems", "maxItems", "minimum", "maximum", "$ref",
}
# 纯注解/结构性关键字：不参与断言，出现不算「不支持」
ANNOTATIONS = {
    "$schema", "$id", "$defs", "definitions", "$comment",
    "title", "description", "examples", "default",
    "deprecated", "readOnly", "writeOnly", "format",
}

TYPE_CHECKS = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    # JSON Schema 中布尔不是数字；Python 里 bool 是 int 的子类，必须显式排除
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


class _Ctx:
    def __init__(self, root: dict[str, Any]) -> None:
        self.root = root
        self.errors: list[str] = []
        self.unsupported: set[str] = set()


def _join(path: str, part: str | int) -> str:
    return f"{path}/{part}" if path else str(part)


def _resolve_ref(ref: str, ctx: _Ctx) -> dict[str, Any] | None:
    """只解析指向本文件的本地引用（`#/$defs/X` 形式）。"""
    if not ref.startswith("#"):
        ctx.unsupported.add("$ref(remote)")
        return None
    node: Any = ctx.root
    for token in ref.lstrip("#/").split("/"):
        if not token:
            continue
        token = token.replace("~1", "/").replace("~0", "~")
        if not isinstance(node, dict) or token not in node:
            ctx.unsupported.add(f"$ref({ref})")
            return None
        node = node[token]
    return node if isinstance(node, dict) else None


def _type_name(value: Any) -> str:
    for name, check in TYPE_CHECKS.items():
        if name != "number" and check(value):
            return name
    return "number" if TYPE_CHECKS["number"](value) else "unknown"


def _validate(value: Any, schema: Any, path: str, ctx: _Ctx) -> None:
    # 布尔 schema：true 恒通过、false 恒失败
    if isinstance(schema, bool):
        if not schema:
            ctx.errors.append(f"{path or '<root>'}: 该位置不允许出现任何值")
        return
    if not isinstance(schema, dict):
        return

    if "$ref" in schema:
        target = _resolve_ref(schema["$ref"], ctx)
        if target is not None:
            _validate(value, target, path, ctx)
        # $ref 与同级关键字并存时，兄弟关键字在 2020-12 中仍需生效，故继续往下

    for keyword in schema:
        if keyword not in SUPPORTED and keyword not in ANNOTATIONS:
            ctx.unsupported.add(keyword)

    loc = path or "<root>"

    # type
    expected = schema.get("type")
    if expected is not None:
        names = expected if isinstance(expected, list) else [expected]
        if not any(TYPE_CHECKS.get(n, lambda _: False)(value) for n in names):
            ctx.errors.append(
                f"{loc}: 类型应为 {'/'.join(names)}，实际为 {_type_name(value)}")
            return  # 类型不符时后续断言无意义，避免连锁噪声

    if "const" in schema and value != schema["const"]:
        ctx.errors.append(f"{loc}: 值应为 {schema['const']!r}，实际为 {value!r}")
    if "enum" in schema and value not in schema["enum"]:
        ctx.errors.append(f"{loc}: 值应为 {schema['enum']!r} 之一，实际为 {value!r}")

    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            ctx.errors.append(f"{loc}: 长度应 ≥ {schema['minLength']}，实际 {len(value)}")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            ctx.errors.append(f"{loc}: 长度应 ≤ {schema['maxLength']}，实际 {len(value)}")
        if "pattern" in schema:
            try:
                if re.search(schema["pattern"], value) is None:
                    ctx.errors.append(f"{loc}: 不匹配模式 {schema['pattern']}")
            except re.error:
                ctx.unsupported.add("pattern(invalid-regex)")

    if TYPE_CHECKS["number"](value):
        if "minimum" in schema and value < schema["minimum"]:
            ctx.errors.append(f"{loc}: 应 ≥ {schema['minimum']}，实际 {value}")
        if "maximum" in schema and value > schema["maximum"]:
            ctx.errors.append(f"{loc}: 应 ≤ {schema['maximum']}，实际 {value}")

    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            ctx.errors.append(f"{loc}: 元素数应 ≥ {schema['minItems']}，实际 {len(value)}")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            ctx.errors.append(f"{loc}: 元素数应 ≤ {schema['maxItems']}，实际 {len(value)}")
        items = schema.get("items")
        if isinstance(items, list):
            # draft-07 的元组形式；本 schema 未使用，出现即声明不支持
            ctx.unsupported.add("items(tuple-form)")
        elif items is not None:
            for index, element in enumerate(value):
                _validate(element, items, _join(path, index), ctx)

    if isinstance(value, dict):
        for field in schema.get("required", []):
            if field not in value:
                ctx.errors.append(f"{loc}: 缺少必填字段 {field}")
        properties = schema.get("properties", {})
        for key, sub in properties.items():
            if key in value:
                _validate(value[key], sub, _join(path, key), ctx)
        extra = schema.get("additionalProperties")
        if extra is not None:
            unknown = [k for k in value if k not in properties]
            if extra is False:
                for key in unknown:
                    ctx.errors.append(f"{loc}: 不允许的额外字段 {key}")
            elif isinstance(extra, dict):
                for key in unknown:
                    _validate(value[key], extra, _join(path, key), ctx)


def validate(payload: Any, schema: dict[str, Any]) -> tuple[list[str], list[str]]:
    """返回 (错误列表, 未支持关键字列表)。

    未支持关键字非空时，调用方**必须**如实回报为部分校验——本模块宁可声明
    自己没查，也不假装查过。
    """
    ctx = _Ctx(schema if isinstance(schema, dict) else {})
    _validate(payload, schema, "", ctx)
    return ctx.errors, sorted(ctx.unsupported)
