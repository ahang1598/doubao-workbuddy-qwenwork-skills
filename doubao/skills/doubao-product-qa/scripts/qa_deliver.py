#!/usr/bin/env python3
"""交付适配层：把“产物写完了”变成可由当前环境交付的结构化清单。

为什么单独一层（取证结论）：
- 旧流程的终点是 `publish` 返回 DELIVERY_LOCK=CLOSED，然后让执行者"把 locator 发给用户"。
  但仅在文本里写一个路径不保证用户能访问产物，重复尝试交付还可能生成重复卡片。
- 宿主交付能力不能被子进程直接调用，所以本脚本不“代发”，而是打印唯一一份
  结构化交付清单；执行者使用当前环境支持且用户可访问的方式完成实际交付。

三条硬性质：
1. 幂等：一次调用覆盖全部产物，只发一张卡片列表 → 结构上不可能出现重复卡。
2. 永不死锁：除"盘上没有东西可发"外，一律放行并把未解决项写进披露段。
   卡住执行者的门会被绕过（trace 19 已实证：lock=OPEN 后它照样连发 5 次）。
3. 已知坑内置：lark-cli 的相对路径限制、markdown 导入格式在脚本内处理，不暴露给执行者。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from qa_run_common import canonical_fingerprint  # noqa: E402

LARK_CARRIERS = {"lark_doc", "lark_sheets", "lark_base", "lark_ppt"}
DOC_SUFFIXES = {".md", ".markdown", ".txt"}
SHEET_SUFFIXES = {".csv", ".tsv"}


def lark_cli() -> str | None:
    return shutil.which("lark-cli")


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_cli(args: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    process = subprocess.run(args, cwd=str(cwd) if cwd else None, text=True, capture_output=True, check=False)
    return process.returncode, process.stdout, process.stderr


def parse_cli_json(stdout: str) -> dict[str, Any]:
    """lark-cli 会在 JSON 前后混入终端控制序列与进度行，取第一个完整对象。"""
    start = stdout.find("{")
    while start != -1:
        decoder = json.JSONDecoder()
        try:
            payload, _ = decoder.raw_decode(stdout[start:])
            if isinstance(payload, dict) and "ok" in payload:
                return payload
        except json.JSONDecodeError:
            pass
        start = stdout.find("{", start + 1)
    return {}


# ---------------------------------------------------------------------------
# 本地产物检查
# ---------------------------------------------------------------------------

def check_local(path: Path, required_sections: list[str]) -> tuple[bool, str, str]:
    """返回 (可交付, 回读摘要, 需披露的问题)。

    只有"盘上没有东西可以发"才判不可交付。章节缺失属于"产物不够好"，
    由披露承担而不是阻断承担——否则执行者手握真实产物却被判为未完成，
    会去发明自己的交付方式（实测事故）。
    """
    if not path.exists():
        return False, "文件不存在", ""
    if path.stat().st_size == 0:
        return False, "文件为空", ""
    if path.suffix.lower() in DOC_SUFFIXES:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return False, "不是合法 UTF-8 文本", ""
        if not text.strip():
            return False, "内容为空", ""
        missing = [section for section in required_sections if section and section not in text]
        summary = f"{len(text)} 字符 / {text.count(chr(10)) + 1} 行"
        if missing:
            return True, summary, f"{path.name} 缺少用户约定的章节：{'、'.join(missing)}"
        return True, f"{summary}；约定章节齐全", ""
    return True, f"{path.stat().st_size} bytes", ""


# ---------------------------------------------------------------------------
# 在线载体：脚本自己建、自己回读
# ---------------------------------------------------------------------------

def create_lark_doc(binary: str, title: str, source: Path) -> dict[str, Any]:
    code, stdout, stderr = run_cli([
        binary, "docs", "+create",
        "--doc-format", "markdown",
        "--title", title,
        "--content", f"@{source.name}",
        "--format", "json",
    ], cwd=source.parent)
    payload = parse_cli_json(stdout)
    if code != 0 or not payload.get("ok"):
        message = (payload.get("error") or {}).get("message") or stderr.strip() or stdout.strip()
        return {"ok": False, "error": message}
    document = (payload.get("data") or {}).get("document") or {}
    document_id = document.get("document_id") or ""
    return {
        "ok": True,
        "locator": f"https://bytedance.larkoffice.com/docx/{document_id}",
        "document_id": document_id,
    }


def readback_lark_doc(binary: str, document_id: str) -> tuple[bool, str]:
    code, stdout, stderr = run_cli([binary, "docs", "+fetch", "--document-id", document_id, "--format", "json"])
    payload = parse_cli_json(stdout)
    if code != 0 or not payload.get("ok"):
        return False, (stderr.strip() or "回读失败")[:200]
    body = json.dumps(payload.get("data") or {}, ensure_ascii=False)
    headings = body.count("heading")
    return True, f"真实回读 {len(body)} 字符，含 {headings} 个标题块，sha256:{hashlib.sha256(body.encode()).hexdigest()[:16]}"


def create_lark_sheet(binary: str, title: str, source: Path) -> dict[str, Any]:
    # 已知坑：--file 只接受当前目录下的相对路径，必须先 cd（trace 实测 unsafe file path）
    code, stdout, stderr = run_cli([
        binary, "drive", "+import",
        "--type", "sheet",
        "--file", f"./{source.name}",
        "--name", title,
        "--format", "json",
    ], cwd=source.parent)
    payload = parse_cli_json(stdout)
    if code != 0 or not payload.get("ok"):
        message = (payload.get("error") or {}).get("message") or stderr.strip() or stdout.strip()
        return {"ok": False, "error": message}
    data = payload.get("data") or {}
    token = data.get("token") or (data.get("result") or {}).get("token") or ""
    url = data.get("url") or (f"https://bytedance.larkoffice.com/sheets/{token}" if token else "")
    rows = 0
    try:
        rows = max(0, sum(1 for _ in source.open(encoding="utf-8")) - 1)
    except OSError:
        pass
    return {"ok": True, "locator": url, "token": token, "rows": rows}


# ---------------------------------------------------------------------------
# 交付清单生成
# ---------------------------------------------------------------------------

def delivery_instruction(outputs: list[dict[str, Any]]) -> list[str]:
    """生成唯一一份工具无关的结构化交付清单。

    清单同时支持本地绝对路径和 http(s) 在线载体 URL。每项产物只列一次，
    由执行者根据当前环境选择实际交付方式，不得猜测或改写 locator。
    """
    items = [
        {"name": item["name"], "locator": item["locator"]}
        for item in outputs
        if item.get("locator")
    ]
    payload = json.dumps(items, ensure_ascii=False)
    return [
        "交付清单（请一次性提供全部产物，不要重复交付）：",
        f"DELIVERY_ITEMS={payload}",
    ]


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def deliver(qa_run: Path, disclose: list[str]) -> int:
    run = json.loads(qa_run.read_text(encoding="utf-8-sig"))
    contract = run.get("request_contract", {}) or {}
    delivery = contract.get("delivery", {}) or {}
    manifest = run.setdefault("delivery_manifest", {"source_revision": run.get("revision", 1), "outputs": []})
    root = qa_run.parent

    specs = delivery.get("artifacts") or []
    if not specs:
        filenames = delivery.get("filenames") or []
        specs = [
            {"filename": name, "format": delivery.get("format", "markdown"), "carrier": delivery.get("carrier", "local")}
            for name in filenames
        ]
    if not specs:
        print("DELIVER: 契约里没有登记任何交付物。先跑 qa_flow.py bootstrap 建立 request_contract。")
        print("QA_FLOW_STATE=DELIVER_EMPTY")
        print("DELIVERY_LOCK=OPEN")
        print("NEXT=qa_flow.py bootstrap <qa-run.json> --request ... --target ...")
        return 1

    required_sections = list(delivery.get("required_sections") or [])
    binary = lark_cli()
    outputs: list[dict[str, Any]] = []
    problems: list[str] = []
    lines: list[str] = []

    existing = {str(item.get("filename")): item for item in manifest.get("outputs", []) if isinstance(item, dict)}

    for index, spec in enumerate(specs, start=1):
        name = str(spec.get("filename") or f"artifact-{index}")
        carrier = str(spec.get("carrier") or "local")
        source = (root / name) if not Path(name).is_absolute() else Path(name)
        if not source.exists():
            for candidate in (root.parent / name, Path.cwd() / name):
                if candidate.exists():
                    source = candidate
                    break

        # 幂等：本 revision 已经交付过且定位仍有效，直接复用，不重复创建
        prior = existing.get(name)
        digest = sha256_of(source) if source.exists() else ""
        if (
            prior
            and prior.get("validated")
            and prior.get("source_revision") == run.get("revision")
            and prior.get("sha256") == digest
        ):
            outputs.append({"name": name, "locator": prior.get("locator", ""), "carrier": carrier})
            lines.append(f"REUSED  {index}/{len(specs)}  {name}  {prior.get('locator')}")
            continue

        ok, note, gap = check_local(
            source, required_sections if source.suffix.lower() in DOC_SUFFIXES else []
        )
        if not ok:
            problems.append(f"{name}：{note}")
            lines.append(f"MISSING {index}/{len(specs)}  {name}  {note}")
            continue
        if gap:
            problems.append(gap)

        record: dict[str, Any] = {
            "purpose": spec.get("purpose", "deliverable"),
            "carrier": carrier,
            "format": spec.get("format", "markdown"),
            "filename": name,
            "source_revision": run.get("revision", 1),
            "sha256": sha256_of(source),
        }

        if carrier in LARK_CARRIERS and binary:
            title = Path(name).stem
            if source.suffix.lower() in SHEET_SUFFIXES or carrier == "lark_sheets":
                created = create_lark_sheet(binary, title, source)
                if created.get("ok"):
                    record["locator"] = created["locator"]
                    record["readback_receipt"] = f"表格导入成功，{created.get('rows', 0)} 行数据行"
                    record["validated"] = True
                    record["status"] = "validated"
            else:
                created = create_lark_doc(binary, title, source)
                if created.get("ok"):
                    ok_read, receipt = readback_lark_doc(binary, created["document_id"])
                    record["locator"] = created["locator"]
                    record["readback_receipt"] = receipt
                    record["validated"] = bool(ok_read)
                    record["status"] = "validated" if ok_read else "created"
            if not created.get("ok"):
                # 在线载体失败 → 降级为本地文件并披露，绝不静默改格式，也绝不卡死
                problems.append(f"{name}：在线载体创建失败（{created.get('error', '未知')}），已降级交付本地文件")
                record["locator"] = str(source.resolve())
                record["readback_receipt"] = note
                record["validated"] = True
                record["status"] = "degraded_local"
        else:
            if carrier in LARK_CARRIERS and not binary:
                problems.append(f"{name}：运行时没有 lark-cli，已降级交付本地文件")
                record["status"] = "degraded_local"
            else:
                record["status"] = "validated"
            record["locator"] = str(source.resolve())
            record["readback_receipt"] = note
            record["validated"] = True

        outputs.append({"name": name, "locator": record["locator"], "carrier": carrier})
        lines.append(f"READY   {index}/{len(specs)}  {name}  {record['locator']}")
        lines.append(f"        回读：{record['readback_receipt']}")
        existing[name] = record

    manifest["outputs"] = list(existing.values())
    manifest["source_revision"] = run.get("revision", 1)
    manifest["fingerprint"] = canonical_fingerprint(run)
    qa_run.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("\n".join(lines))

    if not outputs:
        # 唯一的真阻断：盘上没有任何东西可以发
        print("DELIVER: 没有任何可交付产物。")
        for item in problems:
            print(f"  - {item}")
        print("QA_FLOW_STATE=DELIVER_BLOCKED")
        print("DELIVERY_LOCK=OPEN")
        print("NEXT=先生成产物文件，再重跑同一条 qa_deliver.py 命令")
        return 1

    print()
    for line in delivery_instruction(outputs):
        print(line)

    notes = problems + list(disclose)
    if notes:
        print()
        print("本轮披露（必须原样写进最终回复，不得省略）：")
        for item in notes:
            print(f"  - {item}")

    print()
    print("QA_FLOW_STATE=DELIVERED" if not notes else "QA_FLOW_STATE=DELIVERED_WITH_DISCLOSURE")
    print("DELIVERY_LOCK=CLOSED")
    print("NEXT=使用当前环境支持且用户可访问的方式，一次性提供上述全部产物，然后写最终回复")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="QA 交付适配层：校验产物、创建在线载体、生成唯一结构化交付清单")
    parser.add_argument("qa_run", type=Path)
    parser.add_argument("--disclose", action="append", default=[], help="需要在最终回复中披露的未解决项")
    args = parser.parse_args()
    qa_run = args.qa_run.expanduser().resolve()
    if not qa_run.exists():
        print(f"DELIVER: 找不到 {qa_run}")
        print("QA_FLOW_STATE=DELIVER_BLOCKED")
        print("DELIVERY_LOCK=OPEN")
        print("NEXT=确认 qa-run.json 路径后重跑")
        return 1
    try:
        return deliver(qa_run, args.disclose)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"DELIVER: {exc}")
        print("QA_FLOW_STATE=DELIVER_BLOCKED")
        print("DELIVERY_LOCK=OPEN")
        print("NEXT=修复 qa-run.json 后重跑同一条命令")
        return 1


if __name__ == "__main__":
    sys.exit(main())
