#!/usr/bin/env python3
"""交付构建驱动：把「红线 + 报告 + 交付闸门 + 证据 + 落位」收成一次调用。

背景（来自真机诊断 717c60d9）：调用方过去要自己串 `review_docx apply` →
`build_review_report` → `cp` 到工作区 → `validate_review_outputs`，闸门每失败一次
就要重跑这一串 3-4 条命令。本驱动把它们收成**一条命令**：

    python scripts/review_build.py --contract <原合同.docx> --operations <ops.json> \\
        --report-json <report.json> --name "<合同简称>" \\
        [--intake <intake.json>] [--outdir "<交付目录>"]

    # 替代路径：传 --risk-json 替代 --report-json，内部自动调用 assemble_report_json.py 组装
    python scripts/review_build.py --contract <原合同.docx> --operations <ops.json> \\
        --risk-json <risk.json> --name "<合同简称>" \\
        [--intake <intake.json>] [--position "<审查立场>"]

行为：
  1. 中间产物统一生成到 work_root()（满足 skill_paths 的输出纪律）
  2. 依次执行 apply（红线/clean）→ build_review_report（报告）
  3. 跑 validate_review_outputs 交付闸门（若提供 --intake 则一并传入做审查对象一致性机检），
     并固定产出生产者证据 JSON
  4. **闸门不过**：stdout 输出结构化失败结果 + 逐条错误，退出码 1；
     调用方只需修正 report.json / operations.json 后**重跑同一条命令**
  5. **闸门通过**：按「<简称>_<文书类型>_<日期>」统一命名，复制到 --outdir 交付
     （--outdir 缺省时自动取 RICHEE_OUTPUT_DIR → /mnt/user-data/outputs → ~/richeeai/project）

这样调用方不必再执行 cp（落位由本脚本完成），文件名与证据台账也不会漏——
诊断中 BLK-02（缺生产者证据）、BLK-03（文件名不统一）正是手工编排导致的。
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
from skill_paths import output_root, work_root  # noqa: E402 (需要 SCRIPTS 在 sys.path 中)


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


def fail(stage: str, proc: subprocess.CompletedProcess) -> dict:
    """把子脚本输出整理成可直接照做的错误列表。

    子脚本失败有两种形态：闸门逐条列错（每行一条，直接可读），或 Python 抛异常
    （traceback 末行才是真因）。后者把末行提到最前，避免调用方在栈帧里翻找。
    """
    detail = (proc.stderr or proc.stdout or "").strip()
    lines = [line for line in detail.splitlines() if line.strip()]
    if any(line.startswith("Traceback") for line in lines):
        cause = lines[-1]
        return {"status": "failed", "stage": stage, "errors": [cause],
                "traceback": detail[-1500:]}
    return {"status": "failed", "stage": stage, "errors": lines}


def emit(result: dict) -> None:
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True, type=Path, help="原合同 docx")
    parser.add_argument("--operations", required=True, type=Path, help="operations.json")
    parser.add_argument("--report-json", type=Path, help="报告数据 JSON（与 --risk-json 二选一）")
    parser.add_argument("--risk-json", type=Path, default=None,
                        help="AI 产出的风险 JSON（替代 --report-json，内部自动组装）")
    parser.add_argument("--position", default="", help="审查立场（配合 --risk-json 使用，如 甲方/乙方）")
    parser.add_argument("--name", required=True, help="合同简称，用于文件命名")
    parser.add_argument("--intake", type=Path, default=None,
                        help="review_intake.py 上下文包，用于审查对象一致性机检")
    parser.add_argument("--outdir", type=Path, default=None,
                        help="交付目录（缺省自动取 RICHEE_OUTPUT_DIR → 云端 → 桌面端）")
    parser.add_argument("--date", default=date.today().strftime("%Y%m%d"))
    args = parser.parse_args()

    if not args.report_json and not args.risk_json:
        emit({"status": "failed", "stage": "input",
              "errors": ["必须提供 --report-json 或 --risk-json（二选一）"]})
        return 1

    if args.report_json and args.risk_json:
        emit({"status": "failed", "stage": "input",
              "errors": ["--report-json 与 --risk-json 不能同时提供"]})
        return 1

    # --risk-json 路径：自动调用 assemble_report_json.py 组装完整 report JSON
    report_json = args.report_json
    if args.risk_json:
        if not args.risk_json.exists():
            emit({"status": "failed", "stage": "input",
                  "errors": [f"risk JSON 不存在: {args.risk_json}"]})
            return 1
        assembled = work_root() / f"report_assembled_{args.date}.json"
        asm_cmd = [sys.executable, str(SCRIPTS / "assemble_report_json.py"),
                   "--risk-json", str(args.risk_json), "--out", str(assembled)]
        if args.intake is not None:
            asm_cmd.extend(["--intake", str(args.intake)])
        if args.position:
            asm_cmd.extend(["--position", args.position])
        asm_proc = run(asm_cmd)
        if asm_proc.returncode != 0:
            emit(fail("assemble_report", asm_proc))
            return 1
        report_json = assembled

    for path, label in ((args.contract, "原合同"), (args.operations, "operations"),
                        (report_json, "报告 JSON")):
        if not path.exists():
            emit({"status": "failed", "stage": "input", "errors": [f"{label}不存在: {path}"]})
            return 1

    if args.intake is not None and not args.intake.exists():
        emit({"status": "failed", "stage": "input",
              "errors": [f"intake 上下文包不存在: {args.intake}"]})
        return 1

    outdir = args.outdir or output_root()

    stem = f"{args.name}"
    work = work_root() / f"fadada_build_{args.date}"
    work.mkdir(parents=True, exist_ok=True)
    redline = work / f"{stem}_带批注修订版_{args.date}.docx"
    clean = work / f"{stem}_clean_internal_{args.date}.docx"
    report = work / f"{stem}_审查报告_{args.date}.docx"
    evidence = work / f"redline_producer_evidence_{args.date}.json"

    proc = run([sys.executable, str(SCRIPTS / "review_docx.py"), "apply",
                str(args.contract), str(args.operations),
                "--redline", str(redline), "--clean", str(clean)])
    if proc.returncode != 0:
        emit(fail("apply_redline", proc))
        return 1

    proc = run([sys.executable, str(SCRIPTS / "build_review_report.py"),
                str(report_json), str(report)])
    if proc.returncode != 0:
        emit(fail("build_report", proc))
        return 1

    validate_cmd = [sys.executable, str(SCRIPTS / "validate_review_outputs.py"),
                    "--redline", str(redline), "--report", str(report),
                    "--operations", str(args.operations), "--result-json", str(evidence)]
    if args.intake is not None:
        validate_cmd.extend(["--intake", str(args.intake)])
    proc = run(validate_cmd)
    if proc.returncode != 0:
        result = fail("delivery_gate", proc)
        result["hint"] = (
            "交付闸门未通过。按上列逐条修正 report-json / operations 后重跑本命令即可，"
            "不必重新执行其他步骤，也不要重新生成已通过的制品。"
        )
        emit(result)
        return 1

    outdir.mkdir(parents=True, exist_ok=True)
    artifacts = []
    for src, role in ((report, "review_report"), (redline, "redline"),
                      (evidence, "producer_evidence")):
        dst = outdir / src.name
        shutil.copy2(src, dst)
        artifacts.append({
            "path": str(dst),
            "role": role,
            # 过程件对律师用户不可读，主 Agent 不应列入用户可见交付清单
            "userVisible": role != "producer_evidence",
        })

    emit({
        "status": "passed",
        "stage": "delivered",
        "artifacts": artifacts,
        "validationStatus": "warning",
        "note": "生产者自检通过（SELF_VALIDATED_ONLY），等待平台可信校验器复核。",
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
