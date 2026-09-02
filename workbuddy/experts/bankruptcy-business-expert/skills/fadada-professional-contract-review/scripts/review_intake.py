#!/usr/bin/env python3
"""审查准备驱动：把「清单 + 上传 + 立场匹配 + 发起引擎 + 抽取原文」收成一次调用。

背景（来自真机诊断 717c60d9）：调用方过去要自己串 `load_org_checklist` →
`upload_contract` → `match_review_list` → `start_review` → `review_docx extract`
五条命令，还要自行保管 contractId / recordId / ruleListCode。本驱动收成一条：

    python scripts/review_intake.py <合同.docx> --business-type 租赁合同 \
        --position "出租方（甲方）" [--strictness 2] [--out /tmp/intake.json]

产出一份上下文包 JSON（合同段落 + 组织清单 + 引擎标识），供模型直接做本地深度审查。

设计纪律（对齐 runtime-playbook）：
  - **引擎是增强路径，本地是主路径**：上传/匹配/发起任一步失败或接口不可用，
    只记 warning 并继续，绝不阻断——合同段落抽取是本地能力，永远可用。
  - **发起后不等待**：只取 recordId，不在此轮轮询引擎结果（避免阻塞十几分钟）。
  - 未提供 --position 时，返回 positionList 供调用方让用户选择后再次调用；
    立场不得由模型自由臆造。
"""

from __future__ import annotations

# 同目录模块（skill_paths）在部分宿主环境下不会自动进入 sys.path，显式注入。
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import argparse
import hashlib
import json
import shutil
import subprocess
import zipfile
from pathlib import Path

import failure_policy as fp
from skill_paths import work_root

SCRIPTS = Path(__file__).resolve().parent

# 格式一律按内容判定，不信后缀：真机样本里 .DOC 原件（OLE2）内嵌了 OOXML 主题
# 片段，zipfile.is_zipfile() 会误判为 True，后缀与 zip 探测都不可靠。
OLE2_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"   # 旧版 Word/WPS 复合文档
ZIP_MAGIC = b"PK\x03\x04"
RTF_MAGIC = b"{\\rt"

# LibreOffice 能转成 docx 的格式
CONVERTIBLE_KINDS = {"ole2", "rtf"}

SOFFICE_CANDIDATES = (
    "soffice",
    "libreoffice",
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
)

RESAVE_HINT = (
    "请用 Word/WPS 打开该文件，另存为 .docx（Word 文档）格式后重新提交；"
    "或在本机安装 LibreOffice 以启用自动转换。"
)


def find_soffice() -> str | None:
    """探测 LibreOffice 可执行文件：先查 PATH，再查各平台常见安装位置。"""
    for candidate in SOFFICE_CANDIDATES:
        if os.sep in candidate or (os.altsep and os.altsep in candidate):
            if Path(candidate).exists():
                return candidate
        else:
            found = shutil.which(candidate)
            if found:
                return found
    return None


def convert_to_docx(source: Path, outdir: Path) -> tuple[Path | None, str]:
    """把 .doc/.wps 转成 .docx；未安装 LibreOffice 或转换失败时只回报原因。"""
    executable = find_soffice()
    if not executable:
        return None, "未检测到 LibreOffice（soffice），无法自动转换旧版 Word 格式"
    outdir.mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.run(
            [executable, "--headless", "--convert-to", "docx",
             "--outdir", str(outdir), str(source)],
            capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, f"LibreOffice 转换失败: {exc}"
    target = outdir / f"{source.stem}.docx"
    if proc.returncode != 0 or not target.exists():
        detail = (proc.stderr or proc.stdout or "").strip()[:300]
        return None, detail or "LibreOffice 未产出 docx 文件"
    return target, ""


def input_format_error(errors: list[str]) -> dict:
    """输入格式不可处理时的统一契约。

    这类错误**只有用户能修**（另存为 .docx / 装 LibreOffice），重试预算为 0：
    直接返回 escalate 与成品话术，不给调用方任何"再试一次"的余地——真机中
    正是把这类错误当成可自修错误反复重试，烧掉了十几分钟且毫无产出。
    """
    payload = fp.escalation(
        "input_format", fp.CLASS_USER, errors,
        fp.user_message_for("input_format", errors), attempts=1)
    payload["capabilities"] = {"report": False, "redline": False}
    payload["resaveHint"] = RESAVE_HINT
    return payload


def detect_format(path: Path) -> str:
    """按文件头判定真实格式：docx / ole2 / rtf / zip-other / unknown。"""
    with path.open("rb") as handle:
        head = handle.read(8)
    if head.startswith(OLE2_MAGIC):
        return "ole2"
    if head.startswith(RTF_MAGIC):
        return "rtf"
    if head.startswith(ZIP_MAGIC):
        try:
            with zipfile.ZipFile(path) as archive:
                if "word/document.xml" in archive.namelist():
                    return "docx"
        except zipfile.BadZipFile:
            return "unknown"
        return "zip-other"
    return "unknown"


KIND_LABELS = {
    "ole2": "旧版 Word/WPS 复合文档（.doc）",
    "rtf": "RTF 文档",
    "zip-other": "zip 包但不含 word/document.xml（可能是 xlsx/pptx 或损坏的 docx）",
    "unknown": "无法识别的二进制格式（可能是 PDF、加密文档或已损坏）",
}


def normalize_contract_input(contract: Path, work: Path) -> tuple[Path | None, str | None, dict | None]:
    """返回 (可用的 docx 路径, 原始格式说明, 错误负载)。错误负载非空即中止。"""
    kind = detect_format(contract)
    if kind == "docx":
        return contract, None, None
    if kind in CONVERTIBLE_KINDS:
        converted, err = convert_to_docx(contract, work / "converted")
        if converted is None:
            return None, None, input_format_error([
                f"{contract.name} 实际格式为{KIND_LABELS[kind]}，无法直接审查：{err}"])
        return converted, f"{contract.name}（{KIND_LABELS[kind]}）", None
    if kind == "unknown":
        # PDF/扫描件有平台正规链路（内置读取工具 / fadada-special-ocr），
        # 指向它们而不是笼统建议「另存为 .docx」——后者对 PDF 是无效建议
        payload = input_format_error([
            f"{contract.name} 实际格式为{KIND_LABELS[kind]}，本技能不直接读 PDF/图片"])
        payload["userMessage"] = (
            "这份文件不是 Word 文档，我不能直接审查。\n"
            "1. 数字版 PDF：请先用系统内置读取工具取出文本，再转成 .docx；\n"
            "2. 扫描件/图片：请走 fadada-special-ocr 取文本后再转 .docx；\n"
            "3. 或直接提供合同的原始 Word（.docx）文件——这条最快也最准。")
        return None, None, payload
    return None, None, input_format_error([
        f"{contract.name} 实际格式为{KIND_LABELS.get(kind, kind)}，本技能只处理 .docx"
        "（.doc/.wps/.rtf 可在装有 LibreOffice 时自动转换）"])


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_json(cmd: list[str]) -> tuple[dict | None, str]:
    """执行子脚本并尽力解析其 JSON 输出；失败只回报原因，不抛出。"""
    proc = subprocess.run(cmd, capture_output=True, text=True)
    raw = (proc.stdout or "").strip()
    if proc.returncode != 0:
        return None, (proc.stderr or raw or f"exit {proc.returncode}").strip()[:300]
    for candidate in (raw, raw[raw.find("{"):] if "{" in raw else ""):
        try:
            return json.loads(candidate), ""
        except Exception:
            continue
    return None, f"输出非 JSON: {raw[:200]}"


def dig(data: dict | None, *keys):
    """在嵌套结构里按候选键名找第一个非空值（各接口返回层级不完全一致）。"""
    if not isinstance(data, dict):
        return None
    for key in keys:
        if data.get(key) not in (None, "", [], {}):
            return data[key]
    for value in data.values():
        if isinstance(value, dict):
            found = dig(value, *keys)
            if found is not None:
                return found
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("contract", type=Path)
    parser.add_argument("--business-type", required=True)
    parser.add_argument("--position", default=None,
                        help="审查立场；缺省时返回 positionList 供用户选择")
    parser.add_argument("--strictness", default="2", choices=("1", "2", "3"))
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    if not args.contract.exists():
        detail = f"合同不存在: {args.contract}"
        print(json.dumps(
            fp.escalation("input", fp.CLASS_USER, [detail],
                          "找不到要审查的合同文件。请确认文件路径，或重新发送该文件。",
                          attempts=1),
            ensure_ascii=False, indent=2))
        return 2

    work = work_root()

    # 0) 输入格式门禁 —— 旧版 .doc/.wps 在此转换或明确拒绝，
    #    不允许带着非 OOXML 文件进入下游撞 zipfile.BadZipFile
    contract, converted_from, error = normalize_contract_input(args.contract, work)
    if error is not None:
        print(json.dumps(error, ensure_ascii=False, indent=2))
        return 2  # 2 = 已升级至用户，调用方不得重跑

    bundle: dict = {
        "status": "ok",
        "contractPath": str(contract),
        "contractName": args.contract.name,
        "businessType": args.business_type,
        "position": args.position,
        "warnings": [],
        # 审查对象指纹：交付闸门据此核对「报告声称审了什么」与「实际审了什么」
        "sourceSha256": file_digest(contract),
        "sourceBytes": contract.stat().st_size,
    }
    if converted_from:
        bundle["convertedFrom"] = converted_from
        bundle["warnings"].append(
            f"原文件为旧版 Word 格式，已用 LibreOffice 转换为 docx 后审查；"
            f"排版可能与原件存在细微差异，红线请以转换件为准。")

    # 1) 本地抽取合同段落 —— 主路径能力，必须成功
    extracted = work / f"extracted_{contract.stem}.json"
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "review_docx.py"), "extract",
         str(contract), "--out", str(extracted)],
        capture_output=True, text=True)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()[:400]
        print(json.dumps(
            fp.escalation("extract", fp.CLASS_USER, [detail],
                          fp.user_message_for("extract", [detail]), attempts=1),
            ensure_ascii=False, indent=2))
        return 2
    bundle["extractedPath"] = str(extracted)
    bundle["paragraphCount"] = len(
        json.loads(extracted.read_text(encoding="utf-8")).get("paragraphs", []))

    # 2) 组织审查清单（可选增强）
    checklist, err = run_json(
        [sys.executable, str(SCRIPTS / "load_org_checklist.py"),
         "--business-type", args.business_type,
         "--position", args.position or "", "--format", "auto"])
    if checklist is None:
        bundle["warnings"].append(f"组织清单未命中，退回通用审查要点：{err}")
    else:
        bundle["checklist"] = checklist

    # 3) 上传合同（增强路径，失败不阻断）
    uploaded, err = run_json(
        [sys.executable, str(SCRIPTS / "upload_contract.py"), str(contract)])
    if uploaded is None:
        bundle["warnings"].append(f"引擎上传失败，转纯本地审查：{err}")
        bundle["engine"] = {"available": False}
        return finish(bundle, args.out)

    contract_id = dig(uploaded, "contractId")
    position_list = dig(uploaded, "positionList")
    bundle["engine"] = {"available": True, "contractId": contract_id}
    if position_list:
        bundle["positionList"] = position_list

    # 立场未定：交还调用方让用户从 positionList 中选择，不臆造
    if not args.position:
        bundle["nextAction"] = "choose_position"
        bundle["note"] = "请让用户从 positionList 中选择审查立场，再以 --position 重新调用。"
        return finish(bundle, args.out)

    # 4) 立场匹配审查清单编码（增强路径）
    matched, err = run_json(
        [sys.executable, str(SCRIPTS / "match_review_list.py"),
         str(contract_id), args.position])
    rule_list_code = dig(matched, "ruleListCode") if matched else None
    if not rule_list_code:
        bundle["warnings"].append(f"清单编码匹配失败，引擎审查跳过：{err or '无 ruleListCode'}")
        return finish(bundle, args.out)
    bundle["engine"]["ruleListCode"] = rule_list_code

    # 5) 发起引擎审查——只取 recordId，**发起后不等待**
    started, err = run_json(
        [sys.executable, str(SCRIPTS / "start_review.py"), str(contract_id),
         contract.name, str(rule_list_code), args.position, args.strictness])
    record_id = dig(started, "recordId") if started else None
    if record_id:
        bundle["engine"]["recordId"] = record_id
        bundle["engine"]["note"] = (
            "引擎已在后台受理，本轮不等待。本地审查完成后可用 "
            f"get_review_result.py {record_id} 检查并融合；未完成则直接交付本地结果。")
    else:
        bundle["warnings"].append(f"引擎发起失败，转纯本地审查：{err or '无 recordId'}")

    return finish(bundle, args.out)


def finish(bundle: dict, out: Path | None) -> int:
    contract = bundle.get("contractPath")
    if contract:
        fp.clear(fp.scope_key(Path(contract)))
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
        bundle = {**bundle, "bundlePath": str(out)}
    print(json.dumps(bundle, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
