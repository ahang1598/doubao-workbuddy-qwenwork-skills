#!/usr/bin/env python3
"""Deterministic case-local intake and page-coverage checks."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Iterable


CASE_SUBDIRECTORIES = (
    "00-原始材料",
    "01-处理中/material",
    "01-处理中/research",
    "01-处理中/drafting",
    "01-处理中/trial",
    "01-处理中/verification",
    "02-中间成果",
    "03-最终交付",
)
SAFE_MATTER_ID = re.compile(r"^[A-Za-z0-9._-]+$")


class MaterialGateError(ValueError):
    """Raised when an input cannot be safely processed."""


def _resolved(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def create_case_workspace(workspace_root: str | Path, matter_id: str) -> Path:
    """Create an isolated matter directory with the fixed criminal layout."""

    if not matter_id or not SAFE_MATTER_ID.fullmatch(matter_id):
        raise MaterialGateError("matter_id只允许字母、数字、点、下划线和短横线")
    root = _resolved(workspace_root)
    root.mkdir(parents=True, exist_ok=True)
    case_root = root / matter_id
    case_root.mkdir(exist_ok=True)
    for name in CASE_SUBDIRECTORIES:
        (case_root / name).mkdir(parents=True, exist_ok=True)
    return case_root


def is_case_local_path(case_root: str | Path, candidate: str | Path) -> bool:
    """Return True only when candidate resolves inside the current matter."""

    root = _resolved(case_root)
    path = _resolved(candidate)
    return path == root or root in path.parents


def validate_case_path(case_root: str | Path, candidate: str | Path) -> Path:
    """Resolve a path and reject cross-matter access."""

    root = _resolved(case_root)
    if not root.is_dir():
        raise MaterialGateError("案件目录不存在")
    path = _resolved(candidate)
    if not is_case_local_path(root, path):
        raise MaterialGateError(f"路径不属于当前案件: {path}")
    return path


def _unique_destination(directory: Path, source: Path) -> Path:
    destination = directory / source.name
    if not destination.exists():
        return destination
    source_hash = _sha256(source)
    if destination.is_file() and _sha256(destination) == source_hash:
        return destination
    counter = 2
    while True:
        candidate = directory / f"{source.stem}_{counter}{source.suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def register_sources(case_root: str | Path, source_paths: Iterable[str | Path]) -> list[dict]:
    """Copy every explicit source into 00-原始材料 and return an inventory."""

    root = _resolved(case_root)
    originals = root / "00-原始材料"
    if not originals.is_dir():
        raise MaterialGateError("案件目录结构不完整，请先创建案件目录")

    inventory: list[dict] = []
    seen_sources: set[Path] = set()
    seen_hashes: set[str] = set()
    for order, raw_path in enumerate(source_paths, start=1):
        source = _resolved(raw_path)
        if not source.is_file():
            raise MaterialGateError(f"原始材料不存在或不是文件: {source}")
        if source in seen_sources:
            raise MaterialGateError(f"原始材料清单存在重复路径: {source}")
        seen_sources.add(source)
        source_hash = _sha256(source)
        if source_hash in seen_hashes:
            raise MaterialGateError(f"原始材料清单存在重复哈希: {source.name}")
        seen_hashes.add(source_hash)
        destination = _unique_destination(originals, source)
        if source != destination.resolve() and not destination.exists():
            shutil.copy2(source, destination)
        digest = _sha256(destination)
        inventory.append(
            {
                "order": order,
                "source_name": source.name,
                "source_path": str(source),
                "case_path": str(destination.resolve()),
                "sha256": digest,
                "source_id": f"source-{digest[:16]}",
            }
        )
    return inventory


def summarize_inventory(inventory: list[dict]) -> dict:
    source_ids = [item["source_id"] for item in inventory]
    if len(source_ids) != len(set(source_ids)):
        raise MaterialGateError("原始材料清单存在重复哈希")
    return {
        "source_count": len(inventory),
        "source_paths": [item["source_path"] for item in inventory],
        "case_paths": [item["case_path"] for item in inventory],
    }


def _parse_pages(value: str | Iterable[int] | None, page_count: int) -> set[int]:
    if value is None or value == "":
        return set()
    if isinstance(value, str):
        pages: set[int] = set()
        for token in re.split(r"[,，、\s]+", value.strip()):
            if not token:
                continue
            match = re.fullmatch(r"(\d+)(?:\s*[-–—至]\s*(\d+))?", token)
            if not match:
                raise MaterialGateError(f"无法识别页码范围: {token}")
            start = int(match.group(1))
            end = int(match.group(2) or start)
            if start > end:
                raise MaterialGateError(f"页码范围起止颠倒: {token}")
            pages.update(range(start, end + 1))
    else:
        pages = {int(page) for page in value}
    invalid = sorted(page for page in pages if page < 1 or page > page_count)
    if invalid:
        raise MaterialGateError(f"页码超出1-{page_count}: {invalid}")
    return pages


def evaluate_page_coverage(
    *,
    page_count: int,
    read_pages: str | Iterable[int] | None,
    ocr_pages: str | Iterable[int] | None,
    failed_pages: str | Iterable[int] | None = None,
    retry_count: int = 0,
) -> dict:
    if page_count < 1:
        raise MaterialGateError("page_count必须为正整数")
    if retry_count < 0:
        raise MaterialGateError("retry_count不能为负数")

    expected = set(range(1, page_count + 1))
    read = _parse_pages(read_pages, page_count)
    ocr = _parse_pages(ocr_pages, page_count)
    explicitly_failed = _parse_pages(failed_pages, page_count)
    covered = read | ocr
    missing = expected - covered
    failed = sorted(missing | (explicitly_failed - covered))

    if not missing:
        return {
            "outcome": "PASS",
            "retryable": False,
            "covered_count": len(covered),
            "missing_pages": [],
            "failed_pages": [],
            "retry_pages": [],
        }
    if retry_count == 0:
        return {
            "outcome": "NEEDS_LOCAL_RETRY",
            "retryable": True,
            "covered_count": len(covered),
            "missing_pages": sorted(missing),
            "failed_pages": failed,
            "retry_pages": sorted(missing),
        }
    return {
        "outcome": "BLOCKED",
        "retryable": False,
        "covered_count": len(covered),
        "missing_pages": sorted(missing),
        "failed_pages": failed,
        "retry_pages": [],
        "reason": "page_coverage_incomplete_after_local_retry",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="刑事案件目录、路径与材料页覆盖检查")
    subparsers = parser.add_subparsers(dest="command", required=True)

    workspace = subparsers.add_parser("create-case-workspace")
    workspace.add_argument("--workspace-root", required=True)
    workspace.add_argument("--matter-id", required=True)

    register = subparsers.add_parser("register-sources")
    register.add_argument("--case-root", required=True)
    register.add_argument("paths", nargs="+")

    validate = subparsers.add_parser("validate-case-path")
    validate.add_argument("--case-root", required=True)
    validate.add_argument("--path", required=True)

    coverage = subparsers.add_parser("evaluate-page-coverage")
    coverage.add_argument("--page-count", required=True, type=int)
    coverage.add_argument("--read-pages", default="")
    coverage.add_argument("--ocr-pages", default="")
    coverage.add_argument("--failed-pages", default="")
    coverage.add_argument("--retry-count", type=int, default=0)

    args = parser.parse_args(argv)
    try:
        if args.command == "create-case-workspace":
            result = {"outcome": "PASS", "case_root": str(create_case_workspace(args.workspace_root, args.matter_id))}
        elif args.command == "register-sources":
            sources = register_sources(args.case_root, args.paths)
            result = {"outcome": "PASS", **summarize_inventory(sources), "sources": sources}
        elif args.command == "validate-case-path":
            result = {"outcome": "PASS", "path": str(validate_case_path(args.case_root, args.path))}
        else:
            result = evaluate_page_coverage(
                page_count=args.page_count,
                read_pages=args.read_pages,
                ocr_pages=args.ocr_pages,
                failed_pages=args.failed_pages,
                retry_count=args.retry_count,
            )
    except MaterialGateError as error:
        result = {"outcome": "BLOCKED", "retryable": False, "reason": str(error)}
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["outcome"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

