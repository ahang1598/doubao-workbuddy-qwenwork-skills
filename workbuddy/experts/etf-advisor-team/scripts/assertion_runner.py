#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Assertion Runner — 针对本团队产出的报告执行自动化断言。

本脚本不执行分析流程本身（分析由 agent 驱动），而是对**已产出的报告**做量化校验。
典型用法：

  # 用最近的报告按 eval 1 的断言校验
  python assertion_runner.py --eval-id 1 \\
    --md OutputReport/基金投资组合推荐报告_20260417.md \\
    --html OutputReport/基金投资组合推荐报告_20260417.html

  # 自动在 OutputReport/ 查找最近的匹配报告
  python assertion_runner.py --eval-id 1 --auto

  # 跑全部 evals
  python assertion_runner.py --all

返回码：
  0 = 全部断言通过
  1 = 至少一条断言未通过
"""

from __future__ import annotations

# --- UTF-8 bootstrap (auto-injected, idempotent) ---
import os as _bootstrap_os, sys as _bootstrap_sys
_bootstrap_dir = _bootstrap_os.path.dirname(_bootstrap_os.path.abspath(__file__))
if _bootstrap_dir not in _bootstrap_sys.path:
    _bootstrap_sys.path.insert(0, _bootstrap_dir)
try:
    from _utf8_bootstrap import enable_utf8_io as _bootstrap_enable
    _bootstrap_enable()
except Exception:
    pass
# --- end UTF-8 bootstrap ---

import argparse
import glob as _glob
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
EVALS_PATH = SKILL_DIR / "evals" / "evals.json"


# ============================================================
# 辅助：读取文件/提取 chartData
# ============================================================

def _read_text_safe(path: Optional[Path]) -> str:
    if path is None or not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig", errors="replace")


def _effective_chars(text: str) -> int:
    return len(re.sub(r"\s+", "", text))


def _extract_chart_data_json(html: str) -> Dict[str, Any]:
    """从 HTML 中抠出 `const chartData = {...}` 的 JSON。"""
    m = re.search(r"const\s+chartData\s*=\s*(\{.*?\});\s*\n", html, re.DOTALL)
    if not m:
        return {}
    try:
        return json.loads(m.group(1))
    except Exception:
        return {}


# ============================================================
# 单条断言执行器
# ============================================================

def _glob_latest_in_workspace(workspace: Path, pattern: str) -> Optional[Path]:
    """按 glob 在 workspace 下查找最新匹配（按 mtime 倒序）。"""
    hits = list(workspace.glob(pattern))
    if not hits:
        return None
    return max(hits, key=lambda p: p.stat().st_mtime)


def _check_file_exists(workspace: Path, assertion: Dict) -> Tuple[bool, str]:
    pattern = assertion.get("glob", "")
    path = _glob_latest_in_workspace(workspace, pattern)
    if path:
        return True, f"找到文件: {path.name}"
    return False, f"未找到匹配 {pattern} 的文件"


def _check_min_chars(text: str, assertion: Dict) -> Tuple[bool, str]:
    min_v = int(assertion.get("value", 0))
    actual = _effective_chars(text)
    return actual >= min_v, f"实际 {actual} 字 vs 要求 ≥ {min_v}"


def _check_emoji_min_each(text: str, assertion: Dict) -> Tuple[bool, str]:
    emojis = assertion.get("emojis", [])
    min_v = int(assertion.get("value", 0))
    counts = {e: text.count(e) for e in emojis}
    all_ok = all(v >= min_v for v in counts.values())
    detail = " / ".join(f"{e}={v}" for e, v in counts.items())
    return all_ok, f"{detail} (要求每种 ≥ {min_v})"


def _check_section_count_md(text: str, assertion: Dict) -> Tuple[bool, str]:
    expected = int(assertion.get("value", 0))
    sections = re.findall(r"(?m)^##\s+[一二三四五六七八九十]+、", text)
    return len(sections) >= expected, f"找到 {len(sections)} 个章节（## 一、/二、...），要求 ≥ {expected}"


def _check_code_count_min(text: str, assertion: Dict) -> Tuple[bool, str]:
    pat = assertion.get("pattern", r"(?<!\d)\d{6}(?!\d)")
    min_v = int(assertion.get("value", 0))
    codes = set(re.findall(pat, text))
    return len(codes) >= min_v, f"唯一代码 {len(codes)} 个，要求 ≥ {min_v}"


def _check_contains(text: str, assertion: Dict) -> Tuple[bool, str]:
    s = assertion.get("substring", "")
    ok = s in text
    return ok, f"{'含有' if ok else '不含'} '{s}'"


def _check_not_contains(text: str, assertion: Dict) -> Tuple[bool, str]:
    s = assertion.get("substring", "")
    ok = s not in text
    return ok, f"{'正确不含' if ok else '错误地包含了'} '{s}'"


def _check_contains_any(text: str, assertion: Dict) -> Tuple[bool, str]:
    subs = assertion.get("substrings", [])
    hits = [s for s in subs if s in text]
    return len(hits) > 0, f"命中 {hits or '无'}"


def _check_contains_all(text: str, assertion: Dict) -> Tuple[bool, str]:
    subs = assertion.get("substrings", [])
    missing = [s for s in subs if s not in text]
    return not missing, f"{'全部命中' if not missing else f'缺失 {missing}'}"


def _check_chart_populated(html: str, assertion: Dict) -> Tuple[bool, str]:
    key = assertion.get("key", "")
    chart_data = _extract_chart_data_json(html)
    value = chart_data.get(key)
    if not value:
        return False, f"chartData.{key} 为空或缺失"
    # 至少要有内容（数据/sectors/funds 任一）
    if isinstance(value, dict):
        for k in ("data", "sectors", "funds"):
            v = value.get(k)
            if isinstance(v, list) and v:
                return True, f"chartData.{key}.{k} 有 {len(v)} 项"
    return False, f"chartData.{key} 结构不含有效数据数组"


def _check_weights_sum_near_100(text: str, assertion: Dict) -> Tuple[bool, str]:
    """在 MD 中找带"配置比例/权重/仓位"的表格，检查百分比总和是否接近 100%。"""
    lines = text.splitlines()
    found_ok = False
    best_total = -1.0
    for idx, line in enumerate(lines):
        if "|" in line and ("配置比例" in line or "权重" in line or "仓位" in line or "比例" in line):
            # 向下收集数据行
            pct_col_guess = -1
            header_cells = [c.strip() for c in line.strip().strip("|").split("|")]
            for ci, cell in enumerate(header_cells):
                if any(kw in cell for kw in ["配置比例", "权重", "仓位", "比例"]):
                    pct_col_guess = ci
                    break
            if pct_col_guess < 0:
                continue
            total = 0.0
            n_rows = 0
            for j in range(idx + 2, min(idx + 50, len(lines))):
                row = lines[j]
                if "|" not in row or row.strip().startswith("---"):
                    break
                cells = [c.strip() for c in row.strip().strip("|").split("|")]
                if pct_col_guess >= len(cells):
                    continue
                m = re.search(r"(\d+(?:\.\d+)?)\s*%", cells[pct_col_guess])
                if m:
                    total += float(m.group(1))
                    n_rows += 1
            if n_rows >= 2 and 90 <= total <= 110:
                return True, f"配置比例表合计 {total:.1f}%（行数 {n_rows}）"
            if total > best_total:
                best_total = total
    return False, f"未找到合计接近 100% 的配置表（最接近: {best_total:.1f}%）"


def _check_validator_pass(workspace: Path, text_path: Optional[Path], assertion: Dict) -> Tuple[bool, str]:
    intent = assertion.get("intent", "full")
    if text_path is None or not text_path.exists():
        return False, "报告文件不存在，无法运行 validator"
    validator = SCRIPT_DIR / "report_validator.py"
    try:
        proc = subprocess.run(
            [sys.executable, str(validator), str(text_path), "--intent", intent],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
        )
        ok = proc.returncode == 0
        tail = (proc.stderr or proc.stdout or "")[-200:].replace("\n", " | ")
        return ok, f"exit={proc.returncode}{(' | ' + tail) if tail and not ok else ''}"
    except subprocess.TimeoutExpired:
        return False, "validator 超时（>60s）"
    except Exception as e:
        return False, f"validator 执行异常: {e}"


# 断言类型分发
HANDLERS = {
    "file_exists": lambda ws, md, html, a: _check_file_exists(ws, a),
    "min_chars": lambda ws, md, html, a: _check_min_chars(md if a.get("target") == "md" else html, a),
    "emoji_min_each": lambda ws, md, html, a: _check_emoji_min_each(md if a.get("target") == "md" else html, a),
    "section_count_md": lambda ws, md, html, a: _check_section_count_md(md, a),
    "code_count_min": lambda ws, md, html, a: _check_code_count_min(md if a.get("target") == "md" else html, a),
    "contains": lambda ws, md, html, a: _check_contains(md if a.get("target") == "md" else html, a),
    "not_contains": lambda ws, md, html, a: _check_not_contains(md if a.get("target") == "md" else html, a),
    "contains_any": lambda ws, md, html, a: _check_contains_any(md if a.get("target") == "md" else html, a),
    "contains_all": lambda ws, md, html, a: _check_contains_all(md if a.get("target") == "md" else html, a),
    "chart_populated": lambda ws, md, html, a: _check_chart_populated(html, a),
    "weights_sum_near_100": lambda ws, md, html, a: _check_weights_sum_near_100(md, a),
}


def run_assertions(
    workspace: Path,
    md_path: Optional[Path],
    html_path: Optional[Path],
    assertions: List[Dict],
) -> List[Dict]:
    md_text = _read_text_safe(md_path)
    html_text = _read_text_safe(html_path)
    results = []
    for a in assertions:
        a_type = a.get("type", "")
        handler = HANDLERS.get(a_type)
        if handler:
            passed, evidence = handler(workspace, md_text, html_text, a)
        elif a_type == "validator_pass":
            target = html_path if a.get("target") == "html" else md_path
            passed, evidence = _check_validator_pass(workspace, target, a)
        else:
            passed, evidence = False, f"未知断言类型: {a_type}"
        results.append({
            "text": a.get("text", ""),
            "type": a_type,
            "passed": bool(passed),
            "evidence": evidence,
        })
    return results


# ============================================================
# CLI
# ============================================================

def _auto_find_reports(workspace: Path, patterns: List[str]) -> Tuple[Optional[Path], Optional[Path]]:
    """按模式自动查找最近的 md / html 报告。

    patterns 里的路径可以是：① "OutputReport/xxx_*.md"、② "xxx_*.md"、
    ③ 带多层通配 "OutputReport/**/xxx_*.md"。统一转为绝对查找。
    """
    md_path: Optional[Path] = None
    html_path: Optional[Path] = None
    for pat in patterns:
        # 归一化：如果 pat 不以 glob 符号开头但包含目录，直接按 workspace/pat 查找
        full_pat = str((workspace / pat).resolve()) if not pat.startswith("/") and ":" not in pat else pat
        # 用 glob 查找（支持通配）
        hits = [Path(p) for p in _glob.glob(full_pat, recursive=True)]
        # 若上面没匹配，也试试直接 workspace.glob
        if not hits:
            try:
                hits = list(workspace.glob(pat))
            except Exception:
                hits = []
        if not hits:
            continue
        latest = max(hits, key=lambda p: p.stat().st_mtime)
        if pat.endswith(".md"):
            md_path = latest
        elif pat.endswith(".html"):
            html_path = latest
    return md_path, html_path


def main() -> int:
    parser = argparse.ArgumentParser(description="报告断言执行器")
    parser.add_argument("--eval-id", type=int, help="指定 eval id 运行")
    parser.add_argument("--all", action="store_true", help="运行全部 evals")
    parser.add_argument("--md", help="MD 报告路径")
    parser.add_argument("--html", help="HTML 报告路径")
    parser.add_argument("--auto", action="store_true",
                        help="基于 eval 的 expected_report_patterns 自动查找报告")
    parser.add_argument("--workspace", default=".", help="工作区根目录（默认当前目录）")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    args = parser.parse_args()

    if not args.eval_id and not args.all:
        parser.error("必须指定 --eval-id 或 --all")

    evals_data = json.loads(EVALS_PATH.read_text(encoding="utf-8-sig"))
    evals = evals_data["evals"]
    target_evals = evals if args.all else [e for e in evals if e["id"] == args.eval_id]
    if not target_evals:
        print(f"❌ 找不到 id={args.eval_id} 的 eval", file=sys.stderr)
        return 2

    workspace = Path(args.workspace).resolve()
    all_results = []
    overall_pass = True

    for ev in target_evals:
        print(f"\n=== Eval #{ev['id']}: {ev.get('name', '')} ===")
        print(f"Prompt: {ev['prompt']}")

        if args.auto or (not args.md and not args.html):
            md_path, html_path = _auto_find_reports(workspace, ev.get("expected_report_patterns", []))
            print(f"自动查找 MD: {md_path}")
            print(f"自动查找 HTML: {html_path}")
        else:
            md_path = Path(args.md).resolve() if args.md else None
            html_path = Path(args.html).resolve() if args.html else None

        results = run_assertions(workspace, md_path, html_path, ev.get("assertions", []))
        n_pass = sum(1 for r in results if r["passed"])
        n_total = len(results)
        if n_pass < n_total:
            overall_pass = False

        print(f"断言结果: {n_pass}/{n_total} 通过")
        for r in results:
            icon = "✅" if r["passed"] else "❌"
            print(f"  {icon} [{r['type']:20}] {r['text']}")
            print(f"       证据: {r['evidence']}")

        all_results.append({
            "eval_id": ev["id"],
            "eval_name": ev.get("name"),
            "md": str(md_path) if md_path else None,
            "html": str(html_path) if html_path else None,
            "pass_count": n_pass,
            "total_count": n_total,
            "passed": n_pass == n_total,
            "assertions": results,
        })

    print("\n" + "=" * 60)
    total_assertions = sum(r["total_count"] for r in all_results)
    total_passed = sum(r["pass_count"] for r in all_results)
    print(f"📊 总计: {total_passed}/{total_assertions} 断言通过 | "
          f"{sum(1 for r in all_results if r['passed'])}/{len(all_results)} eval 全绿")

    if args.json:
        print(json.dumps(all_results, ensure_ascii=False, indent=2))

    return 0 if overall_pass else 1


if __name__ == "__main__":
    sys.exit(main())
