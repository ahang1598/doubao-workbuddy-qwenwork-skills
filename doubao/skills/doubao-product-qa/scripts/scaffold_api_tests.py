#!/usr/bin/env python3
"""按项目技术栈复制 API 自动化 starter，并可从 OpenAPI 生成执行清单。"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import generate_api_manifest
import inspect_api_project


FRAMEWORKS = ("pytest", "supertest", "restassured")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成 API 自动化 starter")
    parser.add_argument("--project", type=Path, default=Path.cwd(), help="用于识别技术栈的项目目录")
    parser.add_argument("--framework", choices=("auto", *FRAMEWORKS), default="auto")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--openapi", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project = args.project.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if not project.is_dir():
        print(f"项目目录不存在：{project}", file=sys.stderr)
        return 2
    report = inspect_api_project.inspect(project)
    framework = report["recommended_framework"] if args.framework == "auto" else args.framework
    if framework not in FRAMEWORKS:
        print("无法自动识别框架；请显式传入 --framework pytest|supertest|restassured", file=sys.stderr)
        return 2
    if output.exists():
        print(f"输出目录已存在，为避免覆盖已停止：{output}", file=sys.stderr)
        return 2

    source = Path(__file__).resolve().parent.parent / "assets" / "api-starters" / framework
    shutil.copytree(source, output)
    manifest = {
        "schema_version": 1,
        "source": None,
        "suggested_base_url": None,
        "execution_policy": {
            "base_url_requires_explicit_env": True,
            "safe_methods_default": ["GET", "HEAD", "OPTIONS"],
            "write_methods_require_env": "QA_ALLOW_WRITES=1",
        },
        "operations": [],
    }
    if args.openapi:
        spec = args.openapi.expanduser().resolve()
        try:
            document = generate_api_manifest.load_document(spec)
            manifest = generate_api_manifest.build_manifest(document, str(spec))
            generate_api_manifest.write_coverage(output / "api-coverage.csv", manifest)
        except (OSError, ValueError) as exc:
            shutil.rmtree(output)
            print(f"OpenAPI 处理失败：{exc}", file=sys.stderr)
            return 2
    (output / "api-operations.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "starter-metadata.json").write_text(
        json.dumps({"framework": framework, "project_inspection": report}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"framework": framework, "output": str(output), "operations": len(manifest["operations"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
