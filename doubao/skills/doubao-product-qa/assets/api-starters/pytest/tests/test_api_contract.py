import os
import re

import pytest
from jsonschema import Draft202012Validator


SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def iter_cases(manifest):
    for operation in manifest.get("operations", []):
        for case in operation.get("cases", []):
            yield operation, case


def build_request(operation, case):
    path = operation["path"]
    query = {}
    headers = {}
    cookies = {}
    omit = case.get("omit", {})
    for parameter in operation.get("parameters", []):
        if omit.get("in") == parameter["in"] and omit.get("name") == parameter["name"]:
            value = "" if parameter["in"] == "path" else None
        else:
            value = parameter.get("value")
        if value is None:
            continue
        location = parameter["in"]
        name = parameter["name"]
        if location == "path":
            path = path.replace("{" + name + "}", str(value))
        elif location == "query":
            query[name] = value
        elif location == "header":
            headers[name] = str(value)
        elif location == "cookie":
            cookies[name] = str(value)
    if re.search(r"\{[^}]+\}", path):
        pytest.skip(f"缺少路径参数样例：{path}")
    if case["kind"] != "unauthorized":
        token = os.getenv("QA_API_TOKEN")
        if operation.get("requires_auth") and not token:
            pytest.skip("鉴权接口缺少 QA_API_TOKEN")
        if token:
            header = os.getenv("QA_AUTH_HEADER", "Authorization")
            scheme = os.getenv("QA_AUTH_SCHEME", "Bearer").strip()
            headers[header] = f"{scheme} {token}".strip()
    body = None if case["kind"] == "missing_body" else operation.get("body")
    return path, query, headers, cookies, body


def pytest_generate_tests(metafunc):
    if {"operation", "case"}.issubset(metafunc.fixturenames):
        import json
        from pathlib import Path

        manifest = json.loads(Path("api-operations.json").read_text(encoding="utf-8"))
        values = list(iter_cases(manifest))
        metafunc.parametrize("operation,case", values, ids=[case["case_id"] for _, case in values])


def test_api_contract(client, operation, case):
    method = operation["method"]
    if method not in SAFE_METHODS and os.getenv("QA_ALLOW_WRITES") != "1":
        pytest.skip("写接口默认禁用；确认测试环境和清理策略后设置 QA_ALLOW_WRITES=1")
    path, query, headers, cookies, body = build_request(operation, case)
    request_options = {"params": query, "headers": headers, "json": body}
    if cookies:
        request_options["cookies"] = cookies
    response = client.request(method, path, **request_options)
    assert response.status_code in case["expected_statuses"], response.text[:2000]
    schema = operation.get("response_schema")
    if case["kind"] == "happy" and schema and response.content:
        Draft202012Validator(schema).validate(response.json())
