#!/usr/bin/env python3
"""从 OpenAPI/Swagger 文档生成跨框架 API 执行清单和覆盖矩阵。"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any


HTTP_METHODS = ("get", "post", "put", "patch", "delete", "head", "options", "trace")
SAFE_METHODS = {"get", "head", "options"}


def load_document(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        try:
            import yaml  # type: ignore
        except ImportError as exc:
            raise ValueError("YAML 文档需要 PyYAML；也可先转换为 JSON") from exc
        value = yaml.safe_load(text)
    if not isinstance(value, dict):
        raise ValueError("接口文档根节点必须是对象")
    if not (str(value.get("openapi", "")).startswith("3.") or str(value.get("swagger", "")) == "2.0"):
        raise ValueError("只支持 OpenAPI 3.x 或 Swagger 2.0")
    return value


def resolve_ref(document: dict[str, Any], ref: str) -> Any:
    if not ref.startswith("#/"):
        return {}
    value: Any = document
    for raw in ref[2:].split("/"):
        key = raw.replace("~1", "/").replace("~0", "~")
        if not isinstance(value, dict) or key not in value:
            return {}
        value = value[key]
    return value


def inline_schema(document: dict[str, Any], schema: Any, depth: int = 0, seen: tuple[str, ...] = ()) -> Any:
    if depth > 8 or not isinstance(schema, dict):
        return schema
    ref = schema.get("$ref")
    if isinstance(ref, str):
        if ref in seen:
            return {}
        target = resolve_ref(document, ref)
        return inline_schema(document, target, depth + 1, seen + (ref,))
    result = {}
    for key, value in schema.items():
        if key in {"properties", "patternProperties"} and isinstance(value, dict):
            result[key] = {name: inline_schema(document, child, depth + 1, seen) for name, child in value.items()}
        elif key in {"items", "additionalProperties", "not"}:
            result[key] = inline_schema(document, value, depth + 1, seen)
        elif key in {"allOf", "anyOf", "oneOf"} and isinstance(value, list):
            result[key] = [inline_schema(document, child, depth + 1, seen) for child in value]
        else:
            result[key] = value
    return result


def sample_from_schema(document: dict[str, Any], schema: Any, depth: int = 0) -> Any:
    schema = inline_schema(document, schema, depth)
    if not isinstance(schema, dict) or depth > 8:
        return None
    for key in ("example", "default"):
        if key in schema:
            return schema[key]
    enum = schema.get("enum")
    if isinstance(enum, list) and enum:
        return enum[0]
    for key in ("oneOf", "anyOf"):
        options = schema.get(key)
        if isinstance(options, list) and options:
            return sample_from_schema(document, options[0], depth + 1)
    all_of = schema.get("allOf")
    if isinstance(all_of, list):
        merged: dict[str, Any] = {}
        for part in all_of:
            sample = sample_from_schema(document, part, depth + 1)
            if isinstance(sample, dict):
                merged.update(sample)
        return merged
    schema_type = schema.get("type")
    if schema_type == "object" or "properties" in schema:
        properties = schema.get("properties", {})
        required = set(schema.get("required", []))
        if not isinstance(properties, dict):
            return {}
        return {
            name: sample_from_schema(document, child, depth + 1)
            for name, child in properties.items()
            if name in required or (isinstance(child, dict) and any(k in child for k in ("example", "default")))
        }
    if schema_type == "array":
        return [sample_from_schema(document, schema.get("items", {}), depth + 1)]
    if schema_type == "integer":
        return schema.get("minimum", 1)
    if schema_type == "number":
        return schema.get("minimum", 1.0)
    if schema_type == "boolean":
        return True
    if schema.get("format") == "date":
        return "2026-01-01"
    if schema.get("format") == "date-time":
        return "2026-01-01T00:00:00Z"
    if schema.get("format") == "email":
        return "qa@example.test"
    if schema.get("format") == "uuid":
        return "00000000-0000-4000-8000-000000000001"
    return "qa-sample"


def parameter_sample(document: dict[str, Any], parameter: dict[str, Any]) -> Any:
    if "example" in parameter:
        return parameter["example"]
    examples = parameter.get("examples")
    if isinstance(examples, dict) and examples:
        first = next(iter(examples.values()))
        if isinstance(first, dict) and "value" in first:
            return first["value"]
    return sample_from_schema(document, parameter.get("schema", {}))


def request_body(document: dict[str, Any], operation: dict[str, Any]) -> tuple[Any, bool]:
    body = operation.get("requestBody")
    if isinstance(body, dict) and isinstance(body.get("$ref"), str):
        body = resolve_ref(document, body["$ref"])
    if isinstance(body, dict):
        content = body.get("content", {})
        if isinstance(content, dict):
            selected = content.get("application/json") or next(iter(content.values()), None)
            if isinstance(selected, dict):
                if "example" in selected:
                    return selected["example"], bool(body.get("required"))
                return sample_from_schema(document, selected.get("schema", {})), bool(body.get("required"))
    parameters = operation.get("parameters", [])
    if isinstance(parameters, list):
        for parameter in parameters:
            if isinstance(parameter, dict) and parameter.get("in") == "body":
                return sample_from_schema(document, parameter.get("schema", {})), bool(parameter.get("required"))
    return None, False


def expected_response(document: dict[str, Any], operation: dict[str, Any]) -> tuple[list[int], Any]:
    responses = operation.get("responses", {})
    if not isinstance(responses, dict):
        return [200], None
    success = []
    for key in responses:
        if str(key).isdigit() and 200 <= int(key) < 300:
            success.append(int(key))
    statuses = sorted(success) or [200, 201, 202, 204]
    response = responses.get(str(statuses[0])) or responses.get("default")
    if isinstance(response, dict) and isinstance(response.get("$ref"), str):
        response = resolve_ref(document, response["$ref"])
    schema = None
    if isinstance(response, dict):
        content = response.get("content", {})
        if isinstance(content, dict) and content:
            selected = content.get("application/json") or next(iter(content.values()), None)
            if isinstance(selected, dict):
                schema = inline_schema(document, selected.get("schema"))
        if schema is None and "schema" in response:
            schema = inline_schema(document, response.get("schema"))
    return statuses, schema


def base_url(document: dict[str, Any]) -> str | None:
    servers = document.get("servers")
    if isinstance(servers, list) and servers and isinstance(servers[0], dict):
        return servers[0].get("url")
    host = document.get("host")
    if host:
        schemes = document.get("schemes")
        scheme = schemes[0] if isinstance(schemes, list) and schemes else "https"
        return f"{scheme}://{host}{document.get('basePath', '')}"
    return None


def case_id(method: str, operation_id: str, suffix: str) -> str:
    token = re.sub(r"[^A-Za-z0-9]+", "-", operation_id).strip("-").upper() or "OPERATION"
    return f"TC-API-{method.upper()}-{token}-{suffix}"


def build_manifest(document: dict[str, Any], source: str) -> dict[str, Any]:
    operations = []
    paths = document.get("paths", {})
    global_security = document.get("security")
    if not isinstance(paths, dict):
        raise ValueError("paths 必须是对象")
    for route, path_item in sorted(paths.items()):
        if not isinstance(path_item, dict):
            continue
        shared_parameters = path_item.get("parameters", []) if isinstance(path_item.get("parameters"), list) else []
        for method in HTTP_METHODS:
            operation = path_item.get(method)
            if not isinstance(operation, dict):
                continue
            op_id = str(operation.get("operationId") or f"{method}-{route}")
            parameters = []
            for item in [*shared_parameters, *(operation.get("parameters", []) if isinstance(operation.get("parameters"), list) else [])]:
                if isinstance(item, dict) and isinstance(item.get("$ref"), str):
                    item = resolve_ref(document, item["$ref"])
                if not isinstance(item, dict) or not item.get("name") or not item.get("in"):
                    continue
                parameters.append({
                    "name": item["name"],
                    "in": item["in"],
                    "required": bool(item.get("required") or item.get("in") == "path"),
                    "value": parameter_sample(document, item),
                })
            body, body_required = request_body(document, operation)
            statuses, response_schema = expected_response(document, operation)
            security = operation.get("security", global_security)
            requires_auth = isinstance(security, list) and bool(security)
            base = {
                "operation_id": op_id,
                "method": method.upper(),
                "path": route,
                "summary": operation.get("summary") or operation.get("description") or op_id,
                "tags": operation.get("tags", []),
                "safe_by_default": method in SAFE_METHODS,
                "requires_auth": requires_auth,
                "parameters": parameters,
                "body": body,
                "body_required": body_required,
                "success_statuses": statuses,
                "response_schema": response_schema,
                "cases": [],
            }
            base["cases"].append({
                "case_id": case_id(method, op_id, "HAPPY"),
                "kind": "happy",
                "expected_statuses": statuses,
            })
            required = next((item for item in parameters if item["required"]), None)
            if required:
                base["cases"].append({
                    "case_id": case_id(method, op_id, "MISSING-REQUIRED"),
                    "kind": "missing_required",
                    "omit": {"in": required["in"], "name": required["name"]},
                    "expected_statuses": [400, 404, 422],
                })
            elif body_required:
                base["cases"].append({
                    "case_id": case_id(method, op_id, "MISSING-BODY"),
                    "kind": "missing_body",
                    "expected_statuses": [400, 415, 422],
                })
            if requires_auth:
                base["cases"].append({
                    "case_id": case_id(method, op_id, "UNAUTHORIZED"),
                    "kind": "unauthorized",
                    "expected_statuses": [401, 403],
                })
            operations.append(base)
    return {
        "schema_version": 1,
        "source": source,
        "document_version": document.get("openapi") or document.get("swagger"),
        "title": (document.get("info") or {}).get("title") if isinstance(document.get("info"), dict) else None,
        "suggested_base_url": base_url(document),
        "execution_policy": {
            "base_url_requires_explicit_env": True,
            "safe_methods_default": sorted(method.upper() for method in SAFE_METHODS),
            "write_methods_require_env": "QA_ALLOW_WRITES=1",
        },
        "operations": operations,
    }


def write_coverage(path: Path, manifest: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["operation_id", "method", "path", "case_id", "kind", "safe_by_default", "requires_auth"])
        writer.writeheader()
        for operation in manifest["operations"]:
            for case in operation["cases"]:
                writer.writerow({
                    "operation_id": operation["operation_id"],
                    "method": operation["method"],
                    "path": operation["path"],
                    "case_id": case["case_id"],
                    "kind": case["kind"],
                    "safe_by_default": str(operation["safe_by_default"]).lower(),
                    "requires_auth": str(operation["requires_auth"]).lower(),
                })


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="从 OpenAPI/Swagger 生成 API 自动化执行清单")
    parser.add_argument("spec", type=Path)
    parser.add_argument("--output", type=Path, default=Path("api-operations.json"))
    parser.add_argument("--coverage", type=Path, default=Path("api-coverage.csv"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    spec = args.spec.expanduser().resolve()
    try:
        document = load_document(spec)
        manifest = build_manifest(document, str(spec))
    except (OSError, ValueError) as exc:
        print(f"生成失败：{exc}", file=sys.stderr)
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.coverage.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_coverage(args.coverage, manifest)
    print(json.dumps({"operations": len(manifest["operations"]), "manifest": str(args.output), "coverage": str(args.coverage)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
