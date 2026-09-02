#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""预注册预测（Pre-registration）软门禁验证器 — 对抗事后合理化

设计目的（accuracy-uplift v12 · 建议 3）
─────────────────────────────────────────────────────────────────────
强制在写正文之前先生成 `_prereg.json` 锁定核心论点、可证伪触发器与
"反命题（anti_thesis）"。正文必须正面回应 anti_thesis，避免 agent
事后合理化（先写结论再反向找数据）。

规范
─────────────────────────────────────────────────────────────────────
文件路径：OutputReport/{report_stem}_prereg.json
{
  "report": "...",
  "generated_at": "...",
  "core_thesis": "比亚迪海外业务是 2026 年核心驱动",
  "predictions": [
    {"id": "P1", "claim": "海外销量 2026 ≥ 80 万辆",
     "verify": "海关月度数据 / 公司月度产销快报"},
    ...
  ],
  "falsifiers": [
    {"id": "F1", "trigger": "海外月度销量连续 2 月环比下滑 > 15%",
     "action": "推翻核心论点，减仓 50%"},
    ...
  ],
  "anti_thesis": "如果让我反驳自己，我会说：海外渠道建设速度慢于销量增长，可能出现压库存"
}

软门禁规则
─────────────────────────────────────────────────────────────────────
1. 文件不存在 → WARN
2. core_thesis 缺失/为空 → WARN
3. predictions 数组 < 3 条，或任一缺 claim/verify → WARN
4. falsifiers 数组 < 3 条，或任一缺 trigger/action → WARN
5. anti_thesis 为空，或字数 < 30 → WARN
6. 正文找不到对 anti_thesis 关键名词的正面回应（启发式：anti_thesis
   抽 2-3 个 ≥3 字关键短语，正文未提及任一个）→ WARN
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import List

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

MIN_PREDICTIONS = 3
MIN_FALSIFIERS = 3
MIN_ANTI_THESIS_LEN = 30


def _detect_prereg_path(report_path: Path) -> Path:
    return report_path.parent / f"{report_path.stem}_prereg.json"


def _extract_keywords(text: str, n: int = 3) -> List[str]:
    """从 anti_thesis 抽取 n 个 ≥3 字的关键词（粗启发式：去掉常见连接词后取前 n 个长串）"""
    if not text:
        return []
    # 去标点
    cleaned = re.sub(r"[，。！？；：、,.!?;:\"'\(\)（）【】\[\]\s]+", " ", text)
    tokens = [t for t in cleaned.split() if len(t) >= 3]
    # 去停用词
    stop = {"如果", "我会", "可能", "因为", "所以", "但是", "然而", "他们", "我们", "自己",
            "这是", "那是", "对于", "关于", "需要", "应该", "可以", "或许", "也许"}
    tokens = [t for t in tokens if t not in stop]
    return tokens[:n] if tokens else []


def validate_prereg(report_path: Path) -> List[str]:
    warns: List[str] = []
    prereg_path = _detect_prereg_path(report_path)
    if not prereg_path.exists():
        warns.append(
            f"[预注册·WARN] 未产出预注册文件 `{prereg_path.name}`。"
            "建议 3（对抗事后合理化）要求在写正文前先生成 prereg.json 锁定 "
            "core_thesis/predictions/falsifiers/anti_thesis 四要素。"
            "示例见 `prereg_validator.py` docstring。"
        )
        return warns

    try:
        data = json.loads(prereg_path.read_text(encoding="utf-8"))
    except Exception as e:
        warns.append(f"[预注册·WARN] 文件 `{prereg_path.name}` 解析失败: {e}")
        return warns

    core_thesis = str(data.get("core_thesis", "")).strip()
    if not core_thesis:
        warns.append("[预注册·WARN] core_thesis 缺失或为空")
    predictions = data.get("predictions") or []
    if len(predictions) < MIN_PREDICTIONS:
        warns.append(
            f"[预注册·WARN] predictions 仅 {len(predictions)} 条 < {MIN_PREDICTIONS} 条"
        )
    for i, p in enumerate(predictions, 1):
        if not isinstance(p, dict):
            continue
        if not str(p.get("claim", "")).strip():
            warns.append(f"[预注册·WARN] predictions[{i}] 缺 claim")
        if not str(p.get("verify", "")).strip():
            warns.append(f"[预注册·WARN] predictions[{i}] 缺 verify（可验证路径）")

    falsifiers = data.get("falsifiers") or []
    if len(falsifiers) < MIN_FALSIFIERS:
        warns.append(
            f"[预注册·WARN] falsifiers 仅 {len(falsifiers)} 条 < {MIN_FALSIFIERS} 条"
        )
    for i, f in enumerate(falsifiers, 1):
        if not isinstance(f, dict):
            continue
        if not str(f.get("trigger", "")).strip():
            warns.append(f"[预注册·WARN] falsifiers[{i}] 缺 trigger（触发条件）")
        if not str(f.get("action", "")).strip():
            warns.append(f"[预注册·WARN] falsifiers[{i}] 缺 action（应对动作）")

    anti = str(data.get("anti_thesis", "")).strip()
    if len(anti) < MIN_ANTI_THESIS_LEN:
        warns.append(
            f"[预注册·WARN] anti_thesis 字数 {len(anti)} < {MIN_ANTI_THESIS_LEN}。"
            "应扮演对手方写出『如果让我反驳自己我会说』的完整反驳。"
        )
    else:
        # 正文是否回应 anti_thesis
        try:
            body = report_path.read_text(encoding="utf-8", errors="replace")
            kws = _extract_keywords(anti, n=3)
            if kws:
                hits = sum(1 for kw in kws if kw in body)
                if hits == 0:
                    warns.append(
                        f"[预注册·WARN] 正文未回应 anti_thesis 关键词 "
                        f"{kws}（建议在「对手方论证」章节正面回应）"
                    )
        except Exception:
            pass

    return warns


def main() -> None:
    parser = argparse.ArgumentParser(description="预注册预测软门禁验证器")
    parser.add_argument("report", help="报告 Markdown 路径")
    parser.add_argument("--format", choices=["json", "text"], default="text")
    args = parser.parse_args()

    report_path = Path(args.report)
    warns = validate_prereg(report_path)
    if args.format == "json":
        print(json.dumps({"pass": len(warns) == 0, "warns": warns}, ensure_ascii=False, indent=2))
    else:
        if not warns:
            print(f"✅ 预注册软门禁 PASS: {report_path.name}")
        else:
            print(f"⚠️ 预注册软门禁 {len(warns)} 条 WARN:")
            for w in warns:
                print(f"  - {w}")
    sys.exit(0)


if __name__ == "__main__":
    main()
