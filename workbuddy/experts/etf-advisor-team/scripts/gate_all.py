#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
gate_all.py — Intent-1 交易决策报告「一键全量门禁」编排器（交付前自证闸）
============================================================================

定位
----
根治"agent 偷懒绕过门禁"的工程化抓手。历史事故：写完六面深稿 + 汇总报告后，
agent 以"上下文将尽/任务量大"为借口跳过单面检查点与汇总 GATE0-3，FAIL 也当作
"完成"交付。根因不是规则不够，而是：
  ① 逐个跑 7 条门禁命令摩擦大 → 给"太麻烦/省 token"留了借口；
  ② 没有一个"机器产出、agent 必须粘贴"的统一交付凭据 → 跳过无痕、不可审计；
  ③ 个别 FAIL 是 forecast 基准年 bug 导致的"假 FAIL"，把 agent 训练成"FAIL=噪音→绕过"。

本脚本用"一条命令跑完三阶段串行门禁 + 落盘机器台账 + 单一退出码"消除①②：
  - 按标准三阶段流水线，对同一时间戳的一组产物，**显式三阶段 fail-fast 串行**执行：
      阶段1) 6 份『分面深稿_{面}_{tail}.md』各跑本团队权威
             report_quality_checker.py --single-face <面>
             —— 六面全过才落盘 _faces_pass_{tail}.flag，并准许进入阶段2；任一面未过则阻断后续。
      阶段2) 汇总『交易决策报告_{tail}.md』跑本团队自身
             report_quality_checker.py --emit-gate（GATE0-3）
             —— 通过才准许进入阶段3；未过则阻断阶段3。
      阶段3) 用 md2html_report.py 整合输出单文件 7 标签页 HTML，再用 html_gate.py 做
             **HTML 产物级终检**（标签页齐全/占位符无残留/脚标无断链/内容无丢失/台账链路自证）。
  - 三阶段汇总为一张 PASS/FAIL 台账（含每个文件 + exit code + 实际调用的校验脚本 + 关键
    FAIL 摘要），落盘到 OutputReport/_delivery_gate_ledger.md（机器凭据，供 agent 原样粘贴自证）。
    注：阶段1+2 全过后会**先写一版中间台账**（供 md2html 交付闸读取 OVERALL: PASS），
    阶段3 跑完再重写最终台账（含 HTML 终检结果）。
  - 三阶段全部 PASS → 退出码 0；任一 FAIL/缺失/阻断 → 退出码 1
    （agent 严禁在退出码非 0 时宣布"完成"）。

交付铁律
--------------------------------
agent 在宣布"完成/已交付"汇总决策报告前，**必须**先运行本脚本并把其输出（含
"OVERALL: PASS (exit 0)"行）原样粘贴给用户作为自证；退出码非 0 时严禁交付，
也严禁以"上下文不够/任务量大/省 token"为由跳过——正确做法是诚实报告当前 PASS/FAIL
进度并继续补深，绝不伪造"完成"。

用法
----
  # 推荐：直接传汇总报告路径（最稳，tail 由文件名解析）——跑完整三阶段（含 HTML 生成+终检）
  python scripts/gate_all.py \
      --report OutputReport/交易决策报告_300308_中际旭创_202606262134.md

  # 或传 code + 时间戳（自动在 --outdir 内定位汇总报告）
  python scripts/gate_all.py --code 300308 --ts 202606262134

  # 只跑阶段1 六面单面检查点（阶段A 收口自检用）
  python scripts/gate_all.py --report <汇总报告> --faces-only

  # 跑阶段1+2、跳过阶段3 HTML（迭代提速；最终交付仍须跑满三阶段）
  python scripts/gate_all.py --report <汇总报告> --skip-html

退出码：0 = 三阶段全部 PASS；1 = 有 FAIL/缺失/阻断/异常。
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

FACES = ("基本面", "政策面", "资金面", "筹码面", "技术面", "消息面")
SCRIPT_DIR = Path(__file__).resolve().parent
CHECKER = SCRIPT_DIR / "report_quality_checker.py"  # 本团队权威校验脚本：
# 阶段1 各面单面门禁与阶段2 汇总决策 GATE0-3 门禁均由该脚本执行
MD2HTML = SCRIPT_DIR / "md2html_report.py"
HTML_GATE = SCRIPT_DIR / "html_gate.py"

# Windows 控制台默认 GBK，无法输出 ✅/⛔ 等字符 → 统一重配置为 UTF-8（失败则忽略）
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass


def _face_checker(face: str) -> Tuple[Path, bool]:
    """返回该面『权威』report_quality_checker.py 路径及是否为兜底。

    本团队六面的单面门禁统一由本文件同目录下的权威
    report_quality_checker.py 执行（含各面 face_contract 阈值）；
    兜底分支保留返回结构以兼容台账"校验脚本"列，恒不触发。
    """
    return CHECKER, False


def _checker_label(checker_path: Path, is_fallback: bool) -> str:
    """渲染校验脚本来源标签，供台账"校验脚本"列展示。"""
    rel = f"scripts/{checker_path.name}"
    return f"{rel}（兜底）" if is_fallback else rel


def _run_checker(args: List[str]) -> Tuple[int, str]:
    """跑一次本团队的 report_quality_checker.py（仅用于阶段2 汇总决策门禁）。"""
    return _run_py(CHECKER, args)


def _run_py(script: Path, args: List[str], timeout: int = 900) -> Tuple[int, str]:
    """跑一个 python 脚本，返回 (exit_code, 合并 stdout+stderr)。"""
    cmd = [sys.executable, str(script)] + args
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode, out
    except Exception as e:  # noqa: BLE001
        return 99, f"[gate_all] 调用脚本 {script} 异常: {e}"


def _fail_summary(output: str, max_lines: int = 6) -> str:
    """从门禁输出里抽取 FAIL/待补关键行，截断展示，便于台账快速定位。"""
    keys = ("FAIL", "缺", "待补", "未达", "[GATE", "背离", "runaway", "失控", "❌")
    picked: List[str] = []
    for ln in output.splitlines():
        s = ln.strip()
        if not s:
            continue
        if any(k in s for k in keys):
            picked.append(s)
        if len(picked) >= max_lines:
            picked.append("…（更多见 _gate_result.md / 控制台完整输出）")
            break
    return "\n".join(f"      {p}" for p in picked) if picked else "      （无显式 FAIL 行，详见完整输出）"


def resolve_report(args: argparse.Namespace) -> Optional[Path]:
    """定位汇总报告路径。优先 --report；否则用 --code/--ts 在 --outdir 内匹配。"""
    if args.report:
        return Path(args.report)
    if args.code and args.ts:
        outdir = Path(args.outdir)
        matches = sorted(outdir.glob(f"交易决策报告_{args.code}_*_{args.ts}.md"))
        if matches:
            return matches[0]
        # 兜底：只按时间戳匹配
        matches = sorted(outdir.glob(f"交易决策报告_*_{args.ts}.md"))
        if matches:
            return matches[0]
    return None


def _verdict(code: int) -> str:
    if code == 0:
        return "✅ PASS"
    if code == 2:
        return "⛔ 缺失"
    if code == -1:
        return "🚫 阻断(前序未过)"
    return "❌ FAIL"


def build_ledger(
    tail: str,
    report: Path,
    rows: List[Tuple[str, str, int, str, str]],
    all_pass: bool,
    faces_all_pass: bool,
    stage2_pass: bool,
    html_enabled: bool,
) -> str:
    """渲染三阶段交付台账文本（供落盘 + agent 原样粘贴自证）。

    rows 每项为 (阶段, 文件名, exit, fail摘要, 校验脚本来源标签)。
    "校验脚本来源"列记录各阶段实际调用的校验脚本，便于交付审计。
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    overall = "PASS (exit 0)" if all_pass else "FAIL (exit 1)"
    lines: List[str] = []
    lines.append(f"# 交付前全量门禁台账（三阶段串行） — {tail}")
    lines.append("")
    lines.append(f"- 生成时间：{now}")
    lines.append(f"- 汇总报告：`{report.name}`")
    lines.append("- 门禁流水线：**阶段1 六面单面门禁（单面校验脚本执法）** → "
                 "**阶段2 决策报告门禁(GATE0-3，汇总校验脚本)** → "
                 "**阶段3 HTML 整体终检**（fail-fast：前序未过则后续阻断）")
    lines.append("- 门禁脚本：各面 `scripts/report_quality_checker.py`"
                 "（--single-face，阶段1） + `scripts/report_quality_checker.py`"
                 "（--emit-gate，阶段2） + `md2html_report.py`（生成 HTML） + "
                 "`html_gate.py`（HTML 终检）")
    lines.append("")
    lines.append("| 阶段 | 文件 | exit | 结果 | 校验脚本 |")
    lines.append("|------|------|:----:|------|------|")
    for stage, fname, code, _summ, source in rows:
        lines.append(f"| {stage} | `{fname}` | {code} | {_verdict(code)} | `{source}` |")
    lines.append("")
    fails = [(s, f, c, m, src) for (s, f, c, m, src) in rows if c not in (0, -1)]
    blocked = [(s, f, c, m, src) for (s, f, c, m, src) in rows if c == -1]
    fallback_used = [(s, f, src) for (s, f, c, m, src) in rows if "（兜底）" in src]
    if fails:
        lines.append("## ❌ 未通过明细（必须补深/修复后复跑，禁止以上下文不足为由跳过）")
        lines.append("")
        for stage, fname, code, summ, src in fails:
            lines.append(f"- **[{stage}] {fname}**（exit {code}，校验脚本 `{src}`）")
            if summ:
                lines.append(summ)
        lines.append("")
    if blocked:
        lines.append("## 🚫 被阻断（前序阶段未过，未执行——非真失败，修复前序后自动放行）")
        lines.append("")
        for stage, fname, code, _summ, _src in blocked:
            lines.append(f"- [{stage}] `{fname}`")
        lines.append("")
    if fallback_used:
        lines.append("## ⚠️ 架构告警：以下面出现门禁兜底回退（单面校验脚本缺失）")
        lines.append("")
        for stage, fname, src in fallback_used:
            lines.append(f"- [{stage}] `{fname}` — 校验脚本 `{src}`，请检查 scripts/ 目录是否完整。")
        lines.append("")
    lines.append(f"## OVERALL: {overall}")
    lines.append("")
    if all_pass:
        lines.append("> 三阶段全部 PASS。agent 可交付，并须把本台账（含 OVERALL 行）原样粘贴给用户自证。")
        if not fallback_used:
            lines.append(">")
            lines.append("> 阶段1 六面门禁均已完成单面校验（无兜底回退）。")
        if html_enabled:
            html_name = report.with_suffix(".html").name
            lines.append(">")
            lines.append(f"> HTML 产物已生成并通过终检：`{html_name}`。")
    else:
        lines.append("> 存在 FAIL/阻断。**严禁交付、严禁宣布『完成』**；按下列回环纪律补到 `OVERALL: PASS` 再收尾。")
        lines.append(">")
        lines.append("> **回环纪律（不可跳过、不可以『上下文不足/省 token』为由收尾）**：")
        if not faces_all_pass:
            failed_faces = [(f, src) for (s, f, c, _m, src) in rows
                             if s == "阶段1·单面" and c not in (0, -1)]
            lines.append("> 1. **阶段1** 六面尚未全过 → 决策门禁/HTML 终检已被阻断。先逐一修复以下深稿，"
                         "对每份复跑该面自身校验脚本 `<校验脚本> \"<深稿>\" --single-face <面>` 直到 exit 0：")
            for ff, src in failed_faces:
                lines.append(f">    - `{ff}`（校验脚本 `{src}`）")
            lines.append("> 2. 六面全过后复跑 `gate_all.py --report ...`，确认生成 `_faces_pass_*.flag` 并自动进入阶段2。")
        elif not stage2_pass:
            lines.append("> 1. 阶段1 已全过；**阶段2** 决策稿 GATE0-3 未过 → HTML 终检已被阻断。"
                         "按上方明细补深决策稿，复跑 `report_quality_checker.py \"<决策稿>\" --emit-gate` 直到 PASS。")
            lines.append("> 2. 复跑 `gate_all.py --report ...` 自动进入阶段3。")
        else:
            lines.append("> 1. 阶段1+2 已全过；**阶段3 HTML 终检** FAIL → 多为 md→html 转换缺陷。"
                         "优先在 `md2html_report.py` 修复（占位符/合页/脚标渲染），再复跑 `gate_all.py` 重生成并复检。")
        lines.append("> 3. 复跑本命令直到 `OVERALL: PASS (exit 0)`（含 HTML 终检），再宣布完成。")
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Intent-1 交易决策报告三阶段串行门禁编排器（六面→决策→HTML，交付前自证闸）"
    )
    ap.add_argument("--report", help="汇总报告路径 OutputReport/交易决策报告_{code}_{简称}_{ts}.md")
    ap.add_argument("--code", help="股票代码（与 --ts 联用，自动定位汇总报告）")
    ap.add_argument("--ts", help="时间戳 YYYYMMDDHHMM（与 --code 联用）")
    ap.add_argument("--outdir", default="OutputReport", help="报告/深稿所在目录（默认 OutputReport）")
    ap.add_argument("--faces-only", action="store_true", help="只跑阶段1 六面单面门禁，跳过阶段2/3")
    ap.add_argument("--skip-html", action="store_true", help="跳过阶段3（HTML 生成+终检），只跑阶段1+2（迭代提速用）")
    ap.add_argument("--no-charts", action="store_true", help="阶段3 生成 HTML 时不出图表（结构性快检，传给 md2html_report.py）")
    ap.add_argument(
        "--ledger",
        default=None,
        help="机器台账落盘路径（默认 {outdir}/_delivery_gate_ledger.md）",
    )
    args = ap.parse_args()

    report = resolve_report(args)
    if report is None:
        print("[gate_all] ❌ 无法定位汇总报告：请用 --report <路径> 或 --code+--ts。", file=sys.stderr)
        sys.exit(1)

    stem = report.stem
    if not stem.startswith("交易决策报告_"):
        print(f"[gate_all] ❌ 报告名不是 Intent-1 汇总报告（缺『交易决策报告_』前缀）：{stem}", file=sys.stderr)
        sys.exit(1)
    tail = stem[len("交易决策报告_"):]  # {code}_{简称}_{ts}
    outdir = report.parent
    ledger_path = Path(args.ledger) if args.ledger else (outdir / "_delivery_gate_ledger.md")

    rows: List[Tuple[str, str, int, str, str]] = []  # (阶段, 文件名, exit, fail摘要, 校验脚本来源)
    faces_all_pass = True   # 阶段1 六面是否全过（决定能否进入阶段2）
    stage2_pass = True      # 阶段2 决策门禁是否过（决定能否进入阶段3）
    html_enabled = not (args.faces_only or args.skip_html)

    # ══ 阶段1：六面单面内容门禁 ══════════════════════════════════════
    # 各面统一由本团队 scripts/ 下的权威 report_quality_checker.py 校验。
    for face in FACES:
        draft = outdir / f"分面深稿_{face}_{tail}.md"
        if not draft.exists():
            rows.append(("阶段1·单面", draft.name, 2, "      文件不存在（阶段A 未产出该面深稿）", "-"))
            faces_all_pass = False
            continue
        checker_path, is_fallback = _face_checker(face)
        source_label = _checker_label(checker_path, is_fallback)
        code, out = _run_py(checker_path, [str(draft), "--single-face", face])
        if code != 0:
            faces_all_pass = False
        rows.append(("阶段1·单面", draft.name, code, ("" if code == 0 else _fail_summary(out)), source_label))

    # ── 阶段1 收口令牌（faces-pass flag）：六面全过才落盘，否则删除旧令牌 ──
    flag_path = outdir / f"_faces_pass_{tail}.flag"
    try:
        if faces_all_pass:
            flag_path.write_text(
                f"FACES_GATE: PASS\ntail: {tail}\n"
                f"time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                "meaning: 阶段1 六面单面门禁全部 PASS（各面均由单面门禁校验脚本校验），"
                "准许进入阶段2 撰写/校验决策稿。\n",
                encoding="utf-8",
            )
        elif flag_path.exists():
            flag_path.unlink()
    except Exception:  # noqa: BLE001
        pass

    # ══ 阶段2：决策报告汇总门禁 GATE0-3（fail-fast：阶段1 未全过则阻断）══
    if not args.faces_only:
        if not faces_all_pass:
            stage2_pass = False
            rows.append(("阶段2·决策", report.name, -1,
                         "      前序阶段1 六面未全过，按 fail-fast 阻断（不执行决策门禁）", "-"))
        elif not report.exists():
            stage2_pass = False
            rows.append(("阶段2·决策", report.name, 2, "      汇总报告文件不存在", "-"))
        else:
            # 正式交付严禁 --no-companion-check（铁律#6）；此处刻意不传该 flag
            code, out = _run_checker([str(report), "--emit-gate", "--format", "gate"])
            if code != 0:
                stage2_pass = False
            rows.append(("阶段2·决策", report.name, code, "" if code == 0 else _fail_summary(out),
                         "scripts/report_quality_checker.py"))

    # ══ 写"阶段1+2 中间台账"——md2html 的交付闸需读取本台账 OVERALL: PASS ══
    stages12_pass = faces_all_pass and (args.faces_only or stage2_pass)
    interim = build_ledger(tail, report, rows, stages12_pass, faces_all_pass, stage2_pass, html_enabled)
    try:
        ledger_path.write_text(interim, encoding="utf-8")
    except Exception as e:  # noqa: BLE001
        print(f"[gate_all] ⚠️ 中间台账落盘失败: {e}", file=sys.stderr)

    # ══ 阶段3：整合输出 HTML + HTML 整体终检（fail-fast：阶段1+2 全过才执行）══
    html_path = report.with_suffix(".html")
    if html_enabled:
        if not stages12_pass:
            rows.append(("阶段3·HTML生成", html_path.name, -1,
                         "      前序阶段1/2 未全过，按 fail-fast 阻断（不生成 HTML）", "-"))
            rows.append(("阶段3·HTML终检", html_path.name, -1,
                         "      前序未过，HTML 终检阻断", "-"))
        else:
            md2html_args = [str(report)]
            if args.no_charts:
                md2html_args.append("--no-charts")
            code_gen, out_gen = _run_py(MD2HTML, md2html_args)
            rows.append(("阶段3·HTML生成", html_path.name, code_gen,
                         "" if code_gen == 0 else _fail_summary(out_gen),
                         "scripts/md2html_report.py"))
            if code_gen != 0 or not html_path.exists():
                rows.append(("阶段3·HTML终检", html_path.name, -1,
                             "      HTML 未成功生成，终检阻断", "-"))
            else:
                code_h, out_h = _run_py(HTML_GATE, [str(html_path), "--ledger", str(ledger_path)])
                rows.append(("阶段3·HTML终检", html_path.name, code_h,
                             "" if code_h == 0 else _fail_summary(out_h),
                             "scripts/html_gate.py"))

    # ══ 汇总最终裁决 + 重写台账 ════════════════════════════════════════
    all_pass = all(c == 0 for (_s, _f, c, _m, _src) in rows)
    final = build_ledger(tail, report, rows, all_pass, faces_all_pass, stage2_pass, html_enabled)
    try:
        ledger_path.write_text(final, encoding="utf-8")
    except Exception as e:  # noqa: BLE001
        print(f"[gate_all] ⚠️ 台账落盘失败: {e}", file=sys.stderr)

    print(final)
    print(f"[gate_all] 台账已落盘: {ledger_path}", file=sys.stderr)
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
