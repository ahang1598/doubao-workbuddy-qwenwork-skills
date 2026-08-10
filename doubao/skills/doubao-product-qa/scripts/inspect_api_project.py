#!/usr/bin/env python3
"""识别 API 项目技术栈、已有测试框架和推荐 starter。"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(read_text(path))
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        return {}


def inspect(project: Path) -> dict[str, Any]:
    evidence: list[str] = []
    existing: list[str] = []
    candidates: list[dict[str, str]] = []

    package = read_json(project / "package.json")
    node_dependencies: dict[str, Any] = {}
    for field in ("dependencies", "devDependencies", "peerDependencies"):
        value = package.get(field)
        if isinstance(value, dict):
            node_dependencies.update(value)
    if package:
        evidence.append("package.json")
        if "supertest" in node_dependencies:
            existing.append("Supertest")
        if "@playwright/test" in node_dependencies:
            existing.append("Playwright APIRequestContext")
        if "vitest" in node_dependencies:
            existing.append("Vitest")
        if "jest" in node_dependencies:
            existing.append("Jest")
        candidates.append({"framework": "supertest", "reason": "检测到 Node.js 工程"})

    python_markers = [name for name in ("pyproject.toml", "requirements.txt", "Pipfile", "uv.lock") if (project / name).is_file()]
    python_text = "\n".join(read_text(project / name) for name in python_markers)
    if python_markers:
        evidence.extend(python_markers)
        if re.search(r"\bpytest\b", python_text, re.IGNORECASE) or "[tool.pytest" in python_text:
            existing.append("pytest")
        if re.search(r"\b(httpx|requests)\b", python_text, re.IGNORECASE):
            existing.append("httpx/requests")
        candidates.append({"framework": "pytest", "reason": "检测到 Python 工程"})

    java_files = [name for name in ("pom.xml", "build.gradle", "build.gradle.kts") if (project / name).is_file()]
    java_text = "\n".join(read_text(project / name) for name in java_files)
    if java_files:
        evidence.extend(java_files)
        if "rest-assured" in java_text or "restassured" in java_text:
            existing.append("REST Assured")
        if "junit" in java_text.lower():
            existing.append("JUnit")
        if "testng" in java_text.lower():
            existing.append("TestNG")
        candidates.append({"framework": "restassured", "reason": "检测到 Java/Gradle/Maven 工程"})

    openapi_files: list[str] = []
    for pattern in ("*openapi*.json", "*openapi*.yaml", "*openapi*.yml", "*swagger*.json", "*swagger*.yaml", "*swagger*.yml"):
        openapi_files.extend(str(path.relative_to(project)) for path in project.glob(pattern) if path.is_file())

    priority = {"pytest": 0, "supertest": 1, "restassured": 2}
    if any(name in existing for name in ("pytest", "Supertest", "REST Assured")):
        preferred_map = {"pytest": "pytest", "Supertest": "supertest", "REST Assured": "restassured"}
        preferred = next(preferred_map[name] for name in existing if name in preferred_map)
        reason = "沿用项目已有 API 测试框架"
    elif candidates:
        preferred = sorted(candidates, key=lambda item: priority[item["framework"]])[0]["framework"]
        reason = next(item["reason"] for item in candidates if item["framework"] == preferred)
    else:
        preferred = None
        reason = "未识别技术栈；需要从代码、CI 或团队约定确认"

    return {
        "schema_version": 1,
        "project": str(project),
        "evidence": sorted(set(evidence)),
        "existing_test_tools": sorted(set(existing)),
        "framework_candidates": candidates,
        "recommended_framework": preferred,
        "recommendation_reason": reason,
        "openapi_files": sorted(set(openapi_files)),
        "notes": [
            "项目已有框架优先，不并行维护三套同等业务测试。",
            "生成写接口测试后默认仍禁止执行，需显式设置 QA_ALLOW_WRITES=1。",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="识别 API 项目和已有测试框架")
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project = args.project.expanduser().resolve()
    if not project.is_dir():
        print(f"项目目录不存在：{project}", file=sys.stderr)
        return 2
    report = inspect(project)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"项目：{report['project']}")
        print(f"已有工具：{', '.join(report['existing_test_tools']) or '未识别'}")
        print(f"推荐 starter：{report['recommended_framework'] or '待确认'}")
        print(f"原因：{report['recommendation_reason']}")
        print(f"OpenAPI：{', '.join(report['openapi_files']) or '未发现'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
