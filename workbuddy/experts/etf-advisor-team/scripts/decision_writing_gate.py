#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
decision_writing_gate.py — Intent-1「决策稿写作准入闸」（铁律#1 配套·写作顺序机器执法）
==========================================================================================

定位
----
根治历史事故"六面分面深稿尚未全部通过单面门禁，就提前撰写/校验/交付决策稿"。
铁律#1 规定的写作顺序（阶段A 六面全过 → 阶段C 写决策稿）此前**仅靠 agent 读文档自觉**，
无任何机器 checkpoint。本脚本把它升级为一个**可机器调用的 GO / NO-GO 准入闸**：

  agent 在动手撰写（或校验/交付）`交易决策报告_{tail}.md` 之前，**必须**先运行本闸；
  闸放行（exit 0）才允许写决策稿，否则（exit 1）必须先把六面修复到全过。

判据（全部满足才放行）
----------------------
  ① 同 tail 的收口令牌 `_faces_pass_{tail}.flag` 存在（由 gate_all.py 阶段1 六面全过时落盘）；
  ② 令牌内容裁决行为 `FACES_GATE: PASS`、且 tail 匹配；
  ③ **令牌新鲜**：令牌的修改时间 ≥ 6 份分面深稿中最新一份的修改时间——
     即"六面全过"这一结论反映的是**当前**深稿，而非旧版本。任一深稿在令牌之后被改过，
     说明该面可能已偏离上次通过态，令牌作废 → NO-GO，须复跑 gate_all.py --faces-only。

任一不满足 → exit 1，并打印"先把六面修到全过"的明确指引。

用法
----
  # 推荐：传 code + 时间戳（与最终报告同 tail）
  python scripts/decision_writing_gate.py --code 000708 --ts 202606301600

  # 或传 tail（{code}_{简称}_{时间戳}）
  python scripts/decision_writing_gate.py --tail 000708_中信特钢_202606301600

  # 或直接传将要撰写的决策稿路径（即便文件尚未创建，也按文件名解析 tail）
  python scripts/decision_writing_gate.py \
      --report OutputReport/交易决策报告_000708_中信特钢_202606301600.md

退出码：0 = 准许撰写决策稿；1 = 六面未全过/令牌缺失或过期/参数不足。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

FACES = ("基本面", "政策面", "资金面", "筹码面", "技术面", "消息面")
SCRIPT_DIR = Path(__file__).resolve().parent

# Windows 控制台默认 GBK，无法输出 ✅/⛔ → 统一重配置为 UTF-8（失败则忽略）
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass


def _resolve_tail_and_outdir(args: argparse.Namespace) -> tuple[str | None, Path]:
    """从 --report / --tail / (--code + --ts) 解析 tail 与产物目录。"""
    outdir = Path(args.outdir)
    if args.report:
        rp = Path(args.report)
        outdir = rp.parent if rp.parent != Path("") else outdir
        stem = rp.stem
        if stem.startswith("交易决策报告_"):
            return stem[len("交易决策报告_"):], outdir
        return None, outdir
    if args.tail:
        return args.tail, outdir
    if args.code and args.ts:
        # tail 含简称，无法仅由 code+ts 拼全；在 outdir 内反查 flag 文件匹配 {code}_*_{ts}
        pat = re.compile(rf"^_faces_pass_{re.escape(args.code)}_.+_{re.escape(args.ts)}\.flag$")
        for f in outdir.glob(f"_faces_pass_{args.code}_*_{args.ts}.flag"):
            if pat.match(f.name):
                return f.name[len("_faces_pass_"):-len(".flag")], outdir
        # 没找到 flag → 用 code+ts 反查任一分面深稿凑出 tail
        for f in outdir.glob(f"分面深稿_基本面_{args.code}_*_{args.ts}.md"):
            return f.name[len("分面深稿_基本面_"):-len(".md")], outdir
        return f"{args.code}_*_{args.ts}", outdir  # 占位，后续 flag 不存在会被拦下
    return None, outdir


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Intent-1 决策稿写作准入闸（写决策稿前必跑：校验六面已全过单面门禁）"
    )
    ap.add_argument("--report", help="将撰写的决策稿路径 OutputReport/交易决策报告_{tail}.md（可尚未创建）")
    ap.add_argument("--tail", help="{code}_{简称}_{时间戳}")
    ap.add_argument("--code", help="股票代码（与 --ts 联用）")
    ap.add_argument("--ts", help="时间戳 YYYYMMDDHHMM（与 --code 联用）")
    ap.add_argument("--outdir", default="OutputReport", help="深稿/令牌所在目录（默认 OutputReport）")
    args = ap.parse_args()

    tail, outdir = _resolve_tail_and_outdir(args)
    if not tail or "*" in tail:
        print(
            "[⛔ 写作准入闸·拒绝] 无法定位 tail：请用 --report <决策稿路径> 或 --tail 或 --code+--ts，"
            "且需先运行 gate_all.py --faces-only 产出 _faces_pass_*.flag。",
            file=sys.stderr,
        )
        sys.exit(1)

    flag_path = outdir / f"_faces_pass_{tail}.flag"
    hint = (
        "  ❗正确动作：逐面把 `分面深稿_{面}_" + tail + ".md` 修复到\n"
        "     `python scripts/report_quality_checker.py \"<深稿>\" --single-face <面>` exit 0\n"
        "     （权威校验脚本为本团队 scripts/ 目录下的 report_quality_checker.py），\n"
        "     六面全过后复跑 `python scripts/gate_all.py --report "
        "OutputReport/交易决策报告_" + tail + ".md --faces-only`\n"
        "     （gate_all.py 内部会自动逐面执行单面门禁校验）确认生成 _faces_pass 令牌后，再回来撰写决策稿。"
    )

    # 判据①：令牌存在
    if not flag_path.exists():
        print(
            f"[⛔ 写作准入闸·NO-GO] 未找到六面收口令牌 {flag_path.name}：六面尚未全部通过单面门禁，"
            "不得撰写/校验/交付决策稿。\n" + hint,
            file=sys.stderr,
        )
        sys.exit(1)

    # 判据②：内容裁决 PASS + tail 匹配
    try:
        ftext = flag_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:  # noqa: BLE001
        print(f"[⛔ 写作准入闸·NO-GO] 读取令牌失败: {e}\n" + hint, file=sys.stderr)
        sys.exit(1)
    if not re.search(r"FACES_GATE:\s*PASS", ftext):
        print(
            f"[⛔ 写作准入闸·NO-GO] 令牌 {flag_path.name} 裁决非 PASS（六面未全过）。\n" + hint,
            file=sys.stderr,
        )
        sys.exit(1)
    if tail not in ftext:
        print(
            f"[⛔ 写作准入闸·NO-GO] 令牌 {flag_path.name} 的 tail 不匹配（可能是旧报告令牌）。\n" + hint,
            file=sys.stderr,
        )
        sys.exit(1)

    # 判据③：令牌新鲜——令牌 mtime ≥ 6 份深稿中最新一份的 mtime
    flag_mtime = flag_path.stat().st_mtime
    stale_faces: list[str] = []
    missing_faces: list[str] = []
    for face in FACES:
        draft = outdir / f"分面深稿_{face}_{tail}.md"
        if not draft.exists():
            missing_faces.append(face)
            continue
        if draft.stat().st_mtime > flag_mtime + 1.0:  # 容差 1s，规避文件系统时间精度
            stale_faces.append(face)
    if missing_faces:
        print(
            f"[⛔ 写作准入闸·NO-GO] 缺失分面深稿：{'、'.join(missing_faces)}（令牌与当前产物不一致）。\n" + hint,
            file=sys.stderr,
        )
        sys.exit(1)
    if stale_faces:
        print(
            f"[⛔ 写作准入闸·NO-GO] 令牌已过期：以下面在令牌生成后又被修改过 → {'、'.join(stale_faces)}。\n"
            "  这些面可能已偏离上次通过态，令牌作废。\n" + hint,
            file=sys.stderr,
        )
        sys.exit(1)

    print(
        f"[✅ 写作准入闸·GO] {flag_path.name} 校验通过：六面单面门禁全过、tail 匹配、令牌新鲜。\n"
        "  准许撰写决策稿（顶部务必写 <!-- INTENT1_ARCH: faces-split -->、§四只放结论速览+[详见：面名]、严禁逐字搬入六面正文）。\n"
        "  ⚠️ 写完决策稿后仍须跑 gate_all.py 三阶段全量门禁直到 OVERALL: PASS 才可交付。"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
