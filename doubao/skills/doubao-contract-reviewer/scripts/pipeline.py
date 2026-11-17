#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
合同审查两阶段一条龙 — pipeline.py

把 LLM 不需要介入的脚本调度合并为两次 bash 调用,节省往返。

阶段 A (prepare):
    convert_to_docx → preprocess_contract → formal_checker
    输出 prepare_result.json,里面指向最终 .docx 路径、clean_text.json 和
    formal_report.json(形式审查候选证据,供 Step 2 LLM 使用)

阶段 B (finalize):
    build_json --multi → verify_all → apply_review --dry-run → apply_review
    输出 finalize_result.json

LLM 工作流:
    bash: python3 pipeline.py prepare --input contract.docx
    <读 clean_text.json + formal_report.json,生成 review_all.toml>
    bash: python3 pipeline.py finalize --toml review_all.toml --docx <path>

说明:
  - prepare 阶段的 formal_checker 步骤输出 formal_report.json;LLM 在
    Step 2 读取 candidates 做语义裁决,避免逐段人眼扫"占位符/序号/日期/金额/清单"
  - formal_checker 失败不阻塞 prepare,LLM 降级到纯人工形式审查
  - 所有中间产物/结果 JSON 的默认落点锚定到 **输入合同所在目录**(prepare)
    或 **TOML 所在目录**(finalize),避免 pipeline 被从只读安装目录调起时
    把结果写到只读目录导致 PermissionError。
  - 写文件统一走 _safe_write():遇到 PermissionError/OSError 时自动回退到
    系统临时目录,保证流程不因落盘失败而中断。
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PYTHON = sys.executable  # 使用当前解释器，避免硬编码 python3


def _resolve_out(path, base_dir):
    """把输出路径锚定到 base_dir。

    - 绝对路径:原样返回(尊重调用方显式指定)。
    - 相对路径/裸文件名:拼到 base_dir 下,而不是听任 cwd 决定。
      base_dir 取输入合同所在目录(prepare)或 TOML 所在目录(finalize),
      这两个目录一定可写,能避免落到只读的 skill 安装目录。
    """
    if not path:
        return None
    if os.path.isabs(path):
        return path
    return os.path.join(base_dir, path)


def _safe_write(path, text):
    """写文本文件;若目标目录不可写则回退到系统临时目录,返回实际写入路径。"""
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path
    except (PermissionError, OSError) as e:
        fallback = os.path.join(tempfile.gettempdir(), os.path.basename(path))
        with open(fallback, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"[pipeline] WARN: cannot write {path} ({e}); fell back to {fallback}",
              file=sys.stderr)
        return fallback


def run(cmd, cwd=None):
    """执行子命令,stdout/stderr 透传,返回 (rc, stdout, stderr)。"""
    print(f"[pipeline] $ {' '.join(str(x) for x in cmd)}")
    p = subprocess.run(
        [str(x) for x in cmd], cwd=cwd,
        capture_output=True, text=True,
    )
    if p.stdout:
        sys.stdout.write(p.stdout)
    if p.stderr:
        sys.stderr.write(p.stderr)
    return p.returncode, p.stdout, p.stderr


def cmd_prepare(args):
    """阶段 A: convert_to_docx + preprocess_contract"""
    input_path = os.path.abspath(args.input)
    if not os.path.exists(input_path):
        print(f"[pipeline] ERROR: input not found: {input_path}")
        return 1

    # 输出目录锚定到"输入合同所在目录"(一定可写),不再听任 cwd 决定,
    # 从根本上规避从只读 skill 目录调起时写盘失败。
    base_dir = os.path.dirname(input_path)
    # 中间文件默认加"合同名前缀",从根本上规避多份合同在同一目录并行审查时
    # prepare_result/clean_text/formal_report 因固定名互相覆盖。
    stem = os.path.splitext(os.path.basename(input_path))[0]
    output_path = _resolve_out(args.output or f"{stem}_prepare_result.json", base_dir)

    result = {"stage": "prepare", "input": input_path, "steps": []}

    # Step 1: convert_to_docx (固化 .doc/.docx)
    rc, out, _ = run([PYTHON, SCRIPT_DIR / "convert_to_docx.py", input_path])
    if rc != 0:
        result["steps"].append({"name": "convert_to_docx", "rc": rc, "error": "conversion failed"})
        print(f"[pipeline] convert_to_docx failed (rc={rc}), stopping")
        _dump(result, output_path)
        return rc

    # 约定:convert_to_docx.py 的 stdout 是一个 JSON(多行 indent=2),整体解析
    docx_path = input_path
    try:
        stripped = out.strip()
        # 找最后一个 { 到末尾 }, 作为整体 JSON
        if stripped.startswith("{") and stripped.endswith("}"):
            j = json.loads(stripped)
            if j.get("output_path"):
                docx_path = j["output_path"]
            result["convert_info"] = j
    except (json.JSONDecodeError, ValueError):
        pass
    result["steps"].append({"name": "convert_to_docx", "rc": 0, "docx_path": docx_path})

    # Step 1.5: normalize_docx_format (可选: 统一字体字号,默认关闭)
    # 传入 --normalize 时才执行;默认保留原始文档格式,审查工具不改排版
    if args.normalize:
        norm_out = _resolve_out(f"{stem}_normalized.docx", base_dir)
        rc_norm, out_norm, _ = run([
            PYTHON, SCRIPT_DIR / "normalize_docx_format.py",
            docx_path, "--output", norm_out,
        ])
        if rc_norm == 0 and os.path.exists(norm_out):
            # 解析 stdout JSON 拿统计信息
            try:
                norm_info = __import__("json").loads(out_norm.strip())
            except Exception:
                norm_info = {"stats": {}}
            docx_path = norm_out  # 后续步骤用标准化后的文件
            result["steps"].append({
                "name": "normalize_docx_format",
                "rc": 0,
                "docx_path": docx_path,
                "stats": norm_info.get("stats", {}),
            })
        else:
            # 非阻塞: 标准化失败不影响主流程,记录警告继续用原文件
            result["steps"].append({
                "name": "normalize_docx_format",
                "rc": rc_norm,
                "warning": "格式标准化失败,将使用原始 docx 继续审查",
            })
    else:
        result["steps"].append({
            "name": "normalize_docx_format",
            "rc": 0,
            "skipped": True,
            "reason": "默认关闭,保留原始格式;需统一格式请加 --normalize 参数",
        })

    # Step 2: preprocess_contract (接受修订 → clean_text.json)
    clean_path = _resolve_out(args.clean_text or f"{stem}_clean_text.json", base_dir)
    rc, _, _ = run([
        PYTHON, SCRIPT_DIR / "preprocess_contract.py",
        docx_path, "--out", clean_path,
    ])
    if rc != 0:
        result["steps"].append({"name": "preprocess_contract", "rc": rc, "error": "preprocess failed"})
        _dump(result, output_path)
        return rc
    result["steps"].append({"name": "preprocess_contract", "rc": 0, "clean_text": clean_path})

    # Step 3: formal_checker — 正则形式审查,产出 formal_report.json
    # 目的:把"占位符/序号/日期格式/金额粗筛/标的清单"这类纯正则判断前移到脚本,
    #      LLM 在 Step 2 形式审查阶段读 formal_report.json 的 candidates 做语义裁决,
    #      不再需要逐段眼睛扫。脚本失败不阻塞 prepare,LLM 降级到纯人工形式审查。
    formal_path = _resolve_out(args.formal_report or f"{stem}_formal_report.json", base_dir)
    rc_fc, _, _ = run([
        PYTHON, SCRIPT_DIR / "formal_checker.py",
        clean_path, "--output", formal_path,
    ])
    if rc_fc == 0 and os.path.exists(formal_path):
        result["steps"].append({"name": "formal_checker", "rc": 0, "formal_report": formal_path})
        result["formal_report"] = formal_path
    else:
        # 非阻塞:记录但不退出
        result["steps"].append({
            "name": "formal_checker", "rc": rc_fc,
            "error": "formal_checker failed or skipped; LLM 需降级到纯人工形式审查",
        })
        result["formal_report"] = None

    result["docx_path"] = docx_path
    result["clean_text"] = clean_path
    result["success"] = True
    _dump(result, output_path)
    print(f"[pipeline] prepare done. docx={docx_path} clean_text={clean_path} "
          f"formal_report={result.get('formal_report')}")
    return 0


def cmd_finalize(args):
    """阶段 B: build_json --multi → verify_all → apply_review --dry-run → apply_review"""
    toml_path = os.path.abspath(args.toml)
    docx_path = os.path.abspath(args.docx)
    if not os.path.exists(toml_path):
        print(f"[pipeline] ERROR: toml not found: {toml_path}")
        return 1
    if not os.path.exists(docx_path):
        print(f"[pipeline] ERROR: docx not found: {docx_path}")
        return 1

    workdir = os.path.dirname(toml_path) or "."
    # 结果 JSON 同样锚定到 workdir(TOML 所在目录,必然可写),不依赖 cwd。
    output_path = _resolve_out(args.output or "finalize_result.json", workdir)
    result = {"stage": "finalize", "toml": toml_path, "docx": docx_path, "steps": []}

    # Step 1: build_json --multi
    rc, _, _ = run([
        PYTHON, SCRIPT_DIR / "build_json.py",
        "--from-toml", toml_path, "--multi",
    ], cwd=workdir)
    if rc != 0:
        result["steps"].append({"name": "build_json", "rc": rc, "error": "build_json failed"})
        _dump(result, output_path)
        return rc
    result["steps"].append({"name": "build_json", "rc": 0})

    # Step 2: verify_all (如果 TOML 里只有 modifications 就跳过,由 verify_all 自己判断)
    verify_out = os.path.join(workdir, "verify_results.json")
    rc, _, _ = run([
        PYTHON, SCRIPT_DIR / "verify_all.py",
        "--from-toml", toml_path, "--output", verify_out,
    ], cwd=workdir)
    # verify_all 检测到问题会返回非 0,但 verify_results.json 仍然有效,这里只要产生了文件就继续
    if not os.path.exists(verify_out):
        result["steps"].append({"name": "verify_all", "rc": rc, "error": "verify_results.json not produced"})
        _dump(result, output_path)
        return rc
    result["steps"].append({"name": "verify_all", "rc": rc, "verify_results": verify_out})

    # Step 3: apply_review --dry-run (新增)
    mods_path = os.path.join(workdir, "modifications.json")
    if not os.path.exists(mods_path):
        result["steps"].append({"name": "dry_run", "rc": 1, "error": "modifications.json missing"})
        _dump(result, output_path)
        return 1

    dryrun_report = os.path.join(workdir, "dryrun_report.json")
    rc, _, _ = run([
        PYTHON, SCRIPT_DIR / "apply_review.py",
        "--input", docx_path, "--json", mods_path,
        "--dry-run", dryrun_report,
    ])
    dryrun_summary = {}
    if os.path.exists(dryrun_report):
        with open(dryrun_report, encoding="utf-8") as f:
            dryrun_summary = json.load(f)
    result["steps"].append({"name": "dry_run", "rc": rc, "report": dryrun_report,
                            "matched": dryrun_summary.get("matched"),
                            "unmatched": dryrun_summary.get("unmatched")})

    # 如果存在 --strict-dryrun 且有未命中,停止让 LLM 先修
    if args.strict_dryrun and dryrun_summary.get("unmatched", 0) > 0:
        result["halted_at"] = "dry_run"
        result["hint"] = "dry_run 发现未命中条目,请修正 TOML 后重新 finalize"
        _dump(result, output_path)
        return 2

    # Step 4: apply_review (真正写回)
    out_docx = args.out_docx or os.path.join(
        workdir, os.path.basename(docx_path).replace(".docx", "_AI审核版.docx"),
    )
    rc, _, _ = run([
        PYTHON, SCRIPT_DIR / "apply_review.py",
        "--input", docx_path, "--output", out_docx, "--json", mods_path,
    ])
    stats_path = out_docx + ".stats.json"
    stats = {}
    if os.path.exists(stats_path):
        with open(stats_path, encoding="utf-8") as f:
            stats = json.load(f)
    result["steps"].append({"name": "apply_review", "rc": rc, "out_docx": out_docx, "stats": stats})

    if rc != 0:
        _dump(result, output_path)
        return rc

    result["out_docx"] = out_docx
    result["verify_results"] = verify_out
    result["dryrun_report"] = dryrun_report

    result["success"] = True

    # 输出契约 — LLM 交付前必读这个字段,按输出模板拼最终消息
    # - local_docx_path: 本地带批注 .docx,永远填好
    # - download_url: 留空,由 LLM 在 finalize 完成后调宿主环境的文件上传工具填入
    result["delivery_contract"] = {
        "local_docx_path": os.path.abspath(out_docx),
        "download_url": "",
    }

    _dump(result, output_path)
    print(f"[pipeline] finalize done. reviewed={out_docx}")
    print(f"[pipeline] LLM next: upload {result['delivery_contract']['local_docx_path']} via the host file-upload tool to fill download_url, then deliver per output template.")
    return 0


def _dump(obj, path):
    if not path:
        path = "pipeline_result.json"
    text = json.dumps(obj, ensure_ascii=False, indent=2)
    actual = _safe_write(path, text)
    print(f"[pipeline] result -> {actual}")


def main():
    parser = argparse.ArgumentParser(
        description="合同审查两阶段一条龙 (— 三档关键词触发交付)")
    sub = parser.add_subparsers(dest="stage", required=True)

    p_prep = sub.add_parser("prepare", help="阶段 A: convert + preprocess + formal_checker")
    p_prep.add_argument("--input", required=True, help="原始合同文件(.doc/.docx)")
    p_prep.add_argument("--clean-text", default=None, help="预处理输出路径(默认 <合同名>_clean_text.json)")
    p_prep.add_argument("--formal-report", default=None,
                        help="形式审查候选证据输出路径(默认 <合同名>_formal_report.json)")
    p_prep.add_argument("--output", default=None, help="阶段结果 JSON(默认 <合同名>_prepare_result.json)")
    p_prep.add_argument("--normalize", action="store_true",
                        help="开启格式标准化(统一字体字号,默认关闭,保留原始格式)")
    p_prep.set_defaults(func=cmd_prepare)

    p_fin = sub.add_parser("finalize", help="阶段 B: build_json + verify + dry-run + apply")
    p_fin.add_argument("--toml", required=True, help="聚合 TOML(review_all.toml)")
    p_fin.add_argument("--docx", required=True, help="合同 .docx(prepare 返回的 output_path)")
    p_fin.add_argument("--out-docx", help="最终带批注 .docx 路径(默认 <docx>_AI审核版.docx)")
    p_fin.add_argument("--output", default="finalize_result.json", help="阶段结果 JSON")
    p_fin.add_argument("--strict-dryrun", action="store_true",
                       help="dry-run 有未命中时停止并要求 LLM 修正(默认关闭)")
    p_fin.set_defaults(func=cmd_finalize)

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
