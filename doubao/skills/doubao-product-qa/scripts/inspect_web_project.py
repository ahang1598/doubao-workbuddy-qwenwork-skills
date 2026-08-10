#!/usr/bin/env python3
"""识别本地 Web/API 工程、启动候选和已有测试工具。"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


FRAMEWORKS = {
    "next": ("Next.js", 3000),
    "vite": ("Vite", 5173),
    "react-scripts": ("Create React App", 3000),
    "nuxt": ("Nuxt", 3000),
    "@angular/core": ("Angular", 4200),
    "@vue/cli-service": ("Vue CLI", 8080),
    "@sveltejs/kit": ("SvelteKit", 5173),
    "astro": ("Astro", 4321),
}

TEST_TOOLS = {
    "@playwright/test": "Playwright",
    "playwright": "Playwright",
    "cypress": "Cypress",
    "puppeteer": "Puppeteer",
    "vitest": "Vitest",
    "jest": "Jest",
    "@testing-library/react": "React Testing Library",
    "@axe-core/playwright": "axe + Playwright",
    "lighthouse": "Lighthouse",
}


def load_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def infer_port(command: str) -> int | None:
    patterns = [
        r"(?:^|\s)PORT=(\d+)(?:\s|$)",
        r"--port(?:=|\s+)(\d+)",
        r"(?:^|\s)-p\s+(\d+)(?:\s|$)",
        r":(\d{2,5})(?:\s|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, command)
        if match:
            value = int(match.group(1))
            if 1 <= value <= 65535:
                return value
    return None


def env_keys(path: Path) -> list[str]:
    keys = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return keys
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key = line.split("=", 1)[0].strip()
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            keys.append(key)
    return sorted(set(keys))


def package_manager(project: Path) -> tuple[str | None, str | None]:
    choices = [
        ("pnpm-lock.yaml", "pnpm"),
        ("yarn.lock", "yarn"),
        ("bun.lockb", "bun"),
        ("bun.lock", "bun"),
        ("package-lock.json", "npm"),
    ]
    for filename, manager in choices:
        if (project / filename).is_file():
            return manager, filename
    return ("npm", None) if (project / "package.json").is_file() else (None, None)


def add_candidate(
    candidates: list[dict[str, Any]],
    command: list[str],
    source: str,
    confidence: str,
    port: int | None = None,
    requires_confirmation: bool = False,
) -> None:
    key = tuple(command)
    if any(tuple(item["command"]) == key for item in candidates):
        return
    candidates.append(
        {
            "command": command,
            "source": source,
            "confidence": confidence,
            "port": port,
            "url": f"http://127.0.0.1:{port}" if port else None,
            "requires_confirmation": requires_confirmation,
        }
    )


def inspect(project: Path) -> dict[str, Any]:
    files = {path.name for path in project.iterdir()} if project.is_dir() else set()
    manager, lockfile = package_manager(project)
    candidates: list[dict[str, Any]] = []
    frameworks = []
    test_tools = []
    notes = []

    package = load_json(project / "package.json")
    if package:
        scripts = package.get("scripts", {}) if isinstance(package.get("scripts"), dict) else {}
        dependencies = {}
        for field in ("dependencies", "devDependencies", "peerDependencies"):
            value = package.get(field)
            if isinstance(value, dict):
                dependencies.update(value)
        framework_default = None
        for dep, (name, default_port) in FRAMEWORKS.items():
            if dep in dependencies:
                frameworks.append(name)
                framework_default = framework_default or default_port
        for dep, name in TEST_TOOLS.items():
            if dep in dependencies and name not in test_tools:
                test_tools.append(name)
        for script_name in ("dev", "start", "serve", "preview", "web"):
            script = scripts.get(script_name)
            if not isinstance(script, str):
                continue
            command = [manager or "npm", "run", script_name]
            port = infer_port(script) or framework_default
            add_candidate(candidates, command, f"package.json scripts.{script_name}", "high", port)
        if not scripts:
            notes.append("package.json 没有 scripts")

    if "manage.py" in files:
        add_candidate(candidates, ["python3", "manage.py", "runserver"], "manage.py", "high", 8000)
        frameworks.append("Django")
    if "go.mod" in files:
        add_candidate(candidates, ["go", "run", "."], "go.mod", "medium")
        frameworks.append("Go")
    if "mvnw" in files:
        add_candidate(candidates, ["./mvnw", "spring-boot:run"], "mvnw", "medium", 8080)
    elif "pom.xml" in files:
        add_candidate(candidates, ["mvn", "spring-boot:run"], "pom.xml", "medium", 8080)
    if "gradlew" in files:
        add_candidate(candidates, ["./gradlew", "bootRun"], "gradlew", "medium", 8080)
    if "docker-compose.yml" in files or "docker-compose.yaml" in files or "compose.yml" in files or "compose.yaml" in files:
        add_candidate(
            candidates,
            ["docker", "compose", "up"],
            "Compose 文件",
            "medium",
            requires_confirmation=True,
        )
    if "index.html" in files and not package:
        add_candidate(candidates, ["python3", "-m", "http.server", "8000"], "静态 index.html", "high", 8000)

    python_files = {"pyproject.toml", "requirements.txt", "Pipfile", "uv.lock"} & files
    if python_files and "manage.py" not in files:
        notes.append("检测到 Python 工程；需从 pyproject/README 确认 ASGI/WSGI 入口")
    if not candidates:
        notes.append("没有唯一启动候选；读取 README、Makefile、CI 或询问用户")

    env_templates = []
    for filename in (".env.example", ".env.sample", ".env.template", "env.example"):
        path = project / filename
        if path.is_file():
            env_templates.append({"file": filename, "keys": env_keys(path)})

    project_markers = sorted(
        name
        for name in files
        if name
        in {
            "package.json",
            "pyproject.toml",
            "requirements.txt",
            "manage.py",
            "go.mod",
            "pom.xml",
            "build.gradle",
            "build.gradle.kts",
            "Dockerfile",
            "docker-compose.yml",
            "docker-compose.yaml",
            "compose.yml",
            "compose.yaml",
            "index.html",
        }
    )
    return {
        "schema_version": 1,
        "project": str(project),
        "code_detected": bool(project_markers),
        "project_markers": project_markers,
        "package_manager": manager,
        "lockfile": lockfile,
        "dependencies_installed": (project / "node_modules").is_dir() if package else None,
        "frameworks": sorted(set(frameworks)),
        "test_tools": sorted(set(test_tools)),
        "start_candidates": candidates,
        "recommended_start": candidates[0] if candidates else None,
        "env_templates": env_templates,
        "env_file_present": (project / ".env").is_file(),
        "notes": notes,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="识别本地 Web/API 工程和启动候选")
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
        print(f"框架：{', '.join(report['frameworks']) or '未识别'}")
        print(f"测试工具：{', '.join(report['test_tools']) or '未识别'}")
        if report["recommended_start"]:
            print("推荐启动：" + " ".join(report["recommended_start"]["command"]))
            print(f"候选 URL：{report['recommended_start']['url'] or '需从配置确认'}")
        for note in report["notes"]:
            print(f"- {note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
