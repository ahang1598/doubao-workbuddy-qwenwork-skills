#!/usr/bin/env python3
"""Markdown 产物生成与校验（从属于 qa_deliver.py）。

本脚本只负责"文件对不对"：生成合并 Markdown、回读、登记 delivery_manifest。
"用户看不看得到"由 qa_deliver.py 负责——它才是唯一交付口，
因为在豆包宿主里，回执里有一个路径不等于屏幕上有一张卡片。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from qa_gate import REQUIRED_PHASES, stage_findings
import gate_policy
from qa_run_common import canonical_fingerprint, requested_delivery, semantic_findings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="验证 request_contract 并发布最终 QA 交付物")
    parser.add_argument("qa_run", type=Path)
    parser.add_argument("--locator", action="append", default=[], help="已有 Office/Lark/本地交付物路径或 URL")
    parser.add_argument("--readback-receipt", action="append", default=[], help="对应 locator 的实际回读结果")
    return parser.parse_args()


def load_run(path: Path) -> tuple[Path, dict[str, Any]]:
    resolved = path.expanduser().resolve()
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"无法读取 qa-run.json：{exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("qa-run.json 根节点必须是对象")
    return resolved, payload


def atomic_write(path: Path, payload: dict[str, Any]) -> None:
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def validate_local_file(path: Path, output_format: str) -> str:
    if not path.is_file():
        raise ValueError(f"交付物不存在或不是文件：{path}")
    if path.stat().st_size == 0:
        raise ValueError(f"交付物为空：{path}")
    expected_suffix = {
        "markdown": ".md", "csv": ".csv", "json": ".json", "docx": ".docx",
        "xlsx": ".xlsx", "pptx": ".pptx", "pdf": ".pdf",
    }.get(output_format)
    if expected_suffix and path.suffix.lower() != expected_suffix:
        raise ValueError(f"交付物扩展名与 {output_format} 不匹配：{path.name}")
    if output_format in {"markdown", "csv"}:
        path.read_text(encoding="utf-8-sig")
    elif output_format == "json":
        json.loads(path.read_text(encoding="utf-8-sig"))
    elif output_format in {"docx", "xlsx", "pptx"}:
        expected_member = {"docx": "word/", "xlsx": "xl/", "pptx": "ppt/"}[output_format]
        if not zipfile.is_zipfile(path):
            raise ValueError(f"{output_format} 不是合法 OOXML 压缩包：{path}")
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
        if "[Content_Types].xml" not in names or not any(name.startswith(expected_member) for name in names):
            raise ValueError(f"{output_format} 缺少必要 OOXML 结构：{path}")
    elif output_format == "pdf":
        if not path.read_bytes().startswith(b"%PDF-"):
            raise ValueError(f"PDF 文件头无效：{path}")
    return file_digest(path)


def valid_phase_receipts(run: dict[str, Any]) -> set[str]:
    fingerprint = canonical_fingerprint(run)
    return {
        str(item.get("stage"))
        for item in run.get("phase_receipts", [])
        if item.get("revision") == run.get("revision")
        and item.get("source_fingerprint") == fingerprint
        and item.get("state") in {"CLOSED", "DISCLOSE"}
    }


def render_markdown(path: Path, run: dict[str, Any], filename: str) -> Path:
    renderer = Path(__file__).with_name("render_qa_artifacts.py")
    result = subprocess.run(
        [
            sys.executable,
            str(renderer),
            str(path),
            "--out",
            str(path.parent),
            "--bundle",
            filename,
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise ValueError(result.stderr.strip() or result.stdout.strip() or "Markdown renderer 失败")
    return path.parent / filename


def markdown_readback(path: Path, delivery: dict[str, Any]) -> str:
    content = path.read_text(encoding="utf-8-sig")
    if not content.strip():
        raise ValueError("Markdown 文件为空")
    for section in delivery.get("required_sections", []):
        if str(section) not in content:
            raise ValueError(f"Markdown 缺少必需章节：{section}")
    positions = [content.find(str(section)) for section in delivery.get("section_order", [])]
    if any(position < 0 for position in positions) or positions != sorted(positions):
        raise ValueError("Markdown 章节顺序与 request_contract 不一致")
    return (
        f"UTF-8 回读通过；非空；章节与顺序通过；bytes={path.stat().st_size}；"
        f"{file_digest(path)}"
    )


def next_change_id(changes: list[dict[str, Any]]) -> str:
    numbers = []
    for item in changes:
        value = str(item.get("id", ""))
        if value.startswith("CHG-") and value[4:].isdigit():
            numbers.append(int(value[4:]))
    return f"CHG-{max(numbers, default=0) + 1:03d}"


def update_delivery_ledger(run: dict[str, Any], before: int, after: int) -> None:
    if before == after:
        return
    changes = run.setdefault("change_ledger", [])
    changes.append({
        "id": next_change_id(changes),
        "revision": run["revision"],
        "action": "ADD" if after > before else "REMOVE",
        "object_type": "delivery",
        "added_ids": [str(item.get("filename")) for item in run["delivery_manifest"]["outputs"]],
        "removed_ids": [],
        "modified_ids": [],
        "before_count": before,
        "after_count": after,
        "delta_count": after - before,
        "source": "qa_publish.py",
        "summary": "登记经回读验证的最终交付物",
    })


def build_outputs(
    qa_run_path: Path,
    run: dict[str, Any],
    locators: list[str],
    readback_receipts: list[str],
) -> list[dict[str, Any]]:
    delivery = requested_delivery(run)
    if not delivery.get("artifact_required"):
        if locators:
            raise ValueError("inline 交付不应登记实体 locator")
        return []
    artifacts = delivery.get("artifacts", [])
    if not isinstance(artifacts, list) or not artifacts:
        raise ValueError("request_contract 没有逐项声明交付 artifacts")
    external_count = sum(item.get("format") != "markdown" for item in artifacts)
    if len(locators) != external_count:
        raise ValueError(f"需要 {external_count} 个 locator，实际收到 {len(locators)} 个")
    if len(readback_receipts) != external_count:
        raise ValueError(f"需要 {external_count} 个 readback-receipt，实际收到 {len(readback_receipts)} 个")

    outputs = []
    external_index = 0
    for index, artifact in enumerate(artifacts):
        filename = str(artifact.get("filename", ""))
        output_format = str(artifact.get("format", ""))
        carrier = str(artifact.get("carrier", ""))
        if output_format == "markdown":
            generated = render_markdown(qa_run_path, run, filename).resolve()
            validate_local_file(generated, output_format)
            locator = str(generated)
            receipt = markdown_readback(generated, delivery)
        else:
            locator = locators[external_index]
            receipt = readback_receipts[external_index].strip()
            external_index += 1
        if not receipt:
            raise ValueError(f"{filename} 缺少实际回读回执")
        digest = ""
        if carrier in {"local", "office_file"}:
            local_path = Path(locator).expanduser().resolve()
            if local_path.name != filename:
                raise ValueError(f"locator 文件名 {local_path.name} 与请求文件名 {filename} 不一致")
            digest = validate_local_file(local_path, output_format)
            locator = str(local_path)
        elif not locator.startswith(("http://", "https://")):
            raise ValueError(f"{carrier} 交付必须记录真实 http(s) URL")
        outputs.append({
            "purpose": "primary" if index == 0 else f"companion_{index}",
            "carrier": carrier,
            "format": output_format,
            "filename": filename,
            "locator": locator,
            "source_revision": run["revision"],
            "status": "validated",
            "validated": True,
            "readback_receipt": receipt,
            "content_sha256": digest,
            "request_hash": run["request_contract"]["request_hash"],
            "surface_instruction": "最终回复必须返回此 locator，且不得改写为未验证路径。",
        })
    return outputs


def main() -> int:
    args = parse_args()
    try:
        path, run = load_run(args.qa_run)
        contract = run.get("request_contract")
        if not isinstance(contract, dict):
            raise ValueError(
                "缺少 request_contract。FIX: 使用 qa_flow.py bootstrap <qa-run> "
                "--request <摘要> --target <名称> 初始化"
            )
        required = set(REQUIRED_PHASES.get(str(run.get("profile")), ("baseline", "design", "execution")))
        missing = sorted(required - valid_phase_receipts(run))
        if missing:
            raise ValueError(f"缺少当前 canonical 指纹对应的阶段回执：{', '.join(missing)}")

        preflight_findings = semantic_findings(run, path.parent)
        preflight_errors = gate_policy.blocking(preflight_findings)
        if preflight_errors:
            print(json.dumps({
                "publish_state": "OPEN",
                "delivery_allowed": False,
                "artifacts_created": False,
                "errors": len(preflight_errors),
                "warnings": sum(item["level"] == "warning" for item in preflight_findings),
                "findings": preflight_findings,
            }, ensure_ascii=False, indent=2))
            return 1

        original_outputs = run.get("delivery_manifest", {}).get("outputs", [])
        new_outputs = build_outputs(path, run, args.locator, args.readback_receipt)
        requested_names = {str(value) for value in requested_delivery(run).get("filenames", [])}
        preserved = [
            item for item in original_outputs
            if str(item.get("filename")) not in requested_names
        ]
        working = json.loads(json.dumps(run, ensure_ascii=False))
        working["delivery_manifest"] = {
            "source_revision": working["revision"],
            "outputs": preserved + new_outputs,
        }
        update_delivery_ledger(working, len(original_outputs), len(preserved + new_outputs))

        findings = semantic_findings(working, path.parent)
        findings.extend(stage_findings(working, "release", path.parent))
        errors = gate_policy.blocking(findings)
        warnings = [item for item in findings if item not in errors]
        if errors:
            print(json.dumps({
                "publish_state": "OPEN",
                "delivery_allowed": False,
                "errors": len(errors),
                "warnings": len(warnings),
                "findings": findings,
            }, ensure_ascii=False, indent=2))
            return 1

        release_state = "DISCLOSE" if warnings else "CLOSED"
        release_receipt = {
            "stage": "release",
            "revision": working["revision"],
            "state": release_state,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "source_fingerprint": canonical_fingerprint(working),
            "warnings": len(warnings),
        }
        working["phase_receipts"] = [
            item for item in working.get("phase_receipts", [])
            if not (item.get("stage") == "release" and item.get("revision") == working["revision"])
        ] + [release_receipt]
        atomic_write(path, working)
        print(json.dumps({
            "publish_state": release_state,
            "delivery_allowed": True,
            "qa_run": str(path),
            "revision": working["revision"],
            "request_hash": contract.get("request_hash"),
            "outputs": new_outputs,
            "release_receipt": release_receipt,
            "warnings": warnings,
            "final_response_contract": "最终回复必须逐项返回 outputs[].locator；这些路径/URL 是唯一已验证交付定位。",
        }, ensure_ascii=False, indent=2))
        return 3 if warnings else 0
    except (ValueError, OSError, UnicodeError, zipfile.BadZipFile) as exc:
        print(json.dumps({
            "publish_state": "OPEN",
            "delivery_allowed": False,
            "error": str(exc),
        }, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
