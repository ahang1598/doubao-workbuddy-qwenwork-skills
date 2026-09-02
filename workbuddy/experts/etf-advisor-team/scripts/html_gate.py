#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
html_gate.py — Intent-1 第三阶段「HTML 产物级终检门禁」（薄 · 确定性 · 终检）
============================================================================

定位（与前两阶段的边界）
------------------------
门禁三阶段串行流水线的**第三阶段**，且**只做这一阶段该做的事**：

    阶段1  六面单面内容门禁   report_quality_checker.py --single-face <面>
    阶段2  决策报告汇总门禁   report_quality_checker.py --emit-gate（GATE0-3）
    阶段3  HTML 整体终检      ← 本脚本

前两阶段已经在 **.md 源文件** 上把"内容质量"（字数/表格/推导/评分/信源/减仓硬条件）
查得很彻底。本脚本**绝不重复校验内容质量**，只断言一件前两阶段无法覆盖的事：

    「md → html 这一步转换有没有把东西搞坏」。

`md2html_report.py` 在转换时做了三件有风险的事，都是 .md 阶段保证不了的：
  ① 把 决策稿 + 6 份分面深稿 合成 **7 个 Tab 单文件**（可能漏 tab / 漏页）；
  ② 把 `[[chart:KEY]]` / `[[table:KEY]]` 占位符**注入成图表/数据组件**（注入失败会残留字面量）；
  ③ 脚标 `[^srcN]`、跨页 `[详见：{面}]`、章节 `[详见§X.X]` 的**渲染/跳转**（断链或泄漏字面量）。

因此本门禁是一道**薄、确定性、绝大多数情况下恒 PASS 的终检**——它的价值是"出转换事故时
拦住不可交付的 HTML"，而不是"日常制造返工"。真要修，多数缺陷应在 `md2html_report.py`
转换器里加断言根治（缺陷前移），而非靠本门禁反复打回。

校验项（全部针对**已生成的 HTML 产物**，非 .md）
------------------------------------------------
  [C1] 标签页完整性（FAIL）：按同 tail 实际存在的源 .md 推算应有的页集合
       = {page-决策} ∪ {page-<面> | 该面分面深稿存在}；要求 HTML 中
       `<button class="tab-btn" data-target="...">` 与 `<section class="report-page" id="...">`
       两个集合 **彼此相等且等于应有集合**（既不缺页、也不缺导航按钮）。
  [C2] 图表/数据占位符泄漏（FAIL）：正文（剔除 <code>/<pre>/<script>/<style>/<svg>）中
       不得残留 `[[chart:` / `[[图:` / `[[table:` / 任意 `[[` 字面量（占位符未被替换/删除）。
  [C3] 脚标泄漏（FAIL）：正文不得残留裸 `[^src...]` 引用（脚注定义缺失，未被 footnotes 扩展转换）。
  [C4] 跨引用泄漏（FAIL）：正文不得残留带方括号的 `[详见：{面}]` / `[详见§...]`
       （未转成切页/锚链接；正常转换后只会留无方括号的"详见 …"或 <a> 标签）。
  [C5] 图表注入（WARN，非 FAIL）：统计成功图卡 `<figure class="chart-figure">` 与失败图卡
       `chart-error`。失败图属"数据源/网络"问题（非转换缺陷），仅告警；0 张成功图也仅告警。
  [C6] 内容覆盖率（FAIL/WARN）：每个页面 `<main class="content">` 的可见正文字数，
       相对其源 .md 正文字数的比值。catastrophic 丢失（< 0.50）判 FAIL；偏低（< 0.75）WARN。
       —— 只抓"整页内容被吞"这类转换事故，不评判内容好坏（阈值刻意宽松）。
  [C7] 上游链路自证（FAIL）：交付台账 `_delivery_gate_ledger.md` 存在、tail 匹配、
       且 `## OVERALL: PASS`——确保第三阶段建立在阶段1+2 已 PASS 之上（三阶段链不断裂）。

用法
----
  python scripts/html_gate.py \
      OutputReport/交易决策报告_300308_中际旭创_202606262134.html

  # 显式指定台账（默认取 HTML 同目录 _delivery_gate_ledger.md）
  python ... html_gate.py <html> --ledger <ledger.md>
  # 跳过 C7 上游链路自证（仅独立调试 HTML 时用，正式交付严禁）
  python ... html_gate.py <html> --no-ledger-check

退出码：0 = 全部 PASS（可含 WARN）；1 = 有 FAIL/缺失/异常。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

FACES = ("基本面", "政策面", "技术面", "资金面", "筹码面", "消息面")

# 内容覆盖率阈值（页面正文相对源 md 正文字数）
_COVERAGE_FAIL = 0.50   # 低于此 = 整页内容被吞 → FAIL
_COVERAGE_WARN = 0.75   # 低于此 = 疑似部分丢失 → WARN

# Windows 控制台 UTF-8 兜底
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass


# ── 文本工具 ──────────────────────────────────────────────────────────

def _strip_noise_html(html: str) -> str:
    """剔除不参与"可见正文泄漏扫描"的区段：<script>/<style>/<svg>/<code>/<pre>。

    这些区段可能合法包含 `[[`、`[^`、`[详见` 等字符（如代码示例、SVG 内部文本），
    扫描泄漏时必须排除，避免误报。
    """
    out = html
    for tag in ("script", "style", "svg", "code", "pre"):
        out = re.sub(rf"<{tag}\b[^>]*>.*?</{tag}>", " ", out, flags=re.S | re.I)
    return out


def _visible_text_len(fragment_html: str) -> int:
    """把一段 HTML 折叠成可见正文，返回 CJK+字母数字字符数（用于覆盖率比对）。

    剔除 svg（图形，不算正文）/ style / script / pre / code（契约块、代码示例，
    与 md 侧剥离对称），再去标签、还原少量实体后计数。
    """
    t = fragment_html
    for tag in ("svg", "style", "script", "pre", "code"):
        t = re.sub(rf"<{tag}\b[^>]*>.*?</{tag}>", " ", t, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = (t.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
         .replace("&nbsp;", " ").replace("&quot;", '"').replace("&#39;", "'"))
    return len(re.findall(r"[\w\u4e00-\u9fff]", t))


def _md_plain_len(md_text: str) -> int:
    """源 .md 正文的 CJK+字母数字字符数（与 HTML 侧口径对称）。

    剔除：``` 围栏代码块（含 face_contract JSON）、HTML 注释、脚注定义行、
    frontmatter 顶部 `**X**: Y`、markdown 结构符号（| # > * _ ` ~ - :）。
    """
    t = md_text
    t = re.sub(r"```.*?```", " ", t, flags=re.S)
    t = re.sub(r"<!--.*?-->", " ", t, flags=re.S)
    t = re.sub(r"^\[\^[^\]]+\]:.*$", " ", t, flags=re.M)   # 脚注定义行
    t = re.sub(r"[|#>*_`~:]", " ", t)
    return len(re.findall(r"[\w\u4e00-\u9fff]", t))


# ── 源文件发现 ────────────────────────────────────────────────────────

def _derive_tail(html_path: Path) -> Optional[str]:
    """从 HTML 文件名解析 tail（{code}_{简称}_{ts}）。仅认 交易决策报告_ 前缀。"""
    stem = html_path.stem
    if not stem.startswith("交易决策报告_"):
        return None
    return stem[len("交易决策报告_"):]


def _discover_sources(html_path: Path, tail: str) -> Tuple[Optional[Path], Dict[str, Path]]:
    """定位决策稿 .md 与各面分面深稿 .md（仅返回实际存在的）。"""
    outdir = html_path.parent
    decision = outdir / f"交易决策报告_{tail}.md"
    decision = decision if decision.exists() else None
    faces: Dict[str, Path] = {}
    for face in FACES:
        p = outdir / f"分面深稿_{face}_{tail}.md"
        if p.exists():
            faces[face] = p
    return decision, faces


# ── HTML 解析 ─────────────────────────────────────────────────────────

def _parse_pages(html: str) -> Dict[str, str]:
    """切出每个 `<section class="report-page..." id="page-X">…</section>` 的内层 HTML。

    报告页之间不嵌套 <section>，故非贪婪匹配到下一个 </section> 即可。
    """
    pages: Dict[str, str] = {}
    pat = re.compile(
        r'<section class="report-page[^"]*"\s+id="(page-[^"]+)">(.*?)</section>',
        re.S,
    )
    for m in pat.finditer(html):
        pages[m.group(1)] = m.group(2)
    return pages


def _parse_tab_targets(html: str) -> List[str]:
    """导航按钮的 data-target 列表（多页面才有；单页面无导航返回 [])。"""
    return re.findall(r'<button class="tab-btn[^"]*"\s+data-target="(page-[^"]+)"', html)


def _main_content(section_inner: str) -> str:
    """取 <main class="content">…</main> 内层；缺失则退回整段。"""
    m = re.search(r'<main class="content">(.*?)</main>', section_inner, re.S)
    return m.group(1) if m else section_inner


# ── 各项校验 ──────────────────────────────────────────────────────────

class Issue:
    def __init__(self, level: str, code: str, msg: str):
        self.level = level   # "FAIL" | "WARN"
        self.code = code
        self.msg = msg

    def __str__(self) -> str:
        icon = "❌" if self.level == "FAIL" else "⚠️"
        return f"  {icon} [{self.code}] {self.msg}"


def run_html_gate(
    html_path: Path,
    ledger_path: Optional[Path],
    check_ledger: bool = True,
) -> Tuple[List[Issue], dict]:
    """执行 HTML 终检，返回 (问题列表, 统计信息)。"""
    issues: List[Issue] = []
    stats: dict = {}

    html = html_path.read_text(encoding="utf-8", errors="replace")
    tail = _derive_tail(html_path)
    if tail is None:
        issues.append(Issue("FAIL", "C0",
                            f"HTML 文件名非 Intent-1 汇总报告（缺『交易决策报告_』前缀）：{html_path.name}"))
        return issues, stats

    decision_md, face_mds = _discover_sources(html_path, tail)

    # ── C1 标签页完整性 ──────────────────────────────────────────────
    expected = {"page-决策"} | {f"page-{f}" for f in face_mds}
    if decision_md is None:
        # 决策稿源缺失：无法据 tail 推断，退化为"以 HTML 现有页为准只查 tab/page 一致性"
        issues.append(Issue("WARN", "C1",
                            f"未找到决策稿源 交易决策报告_{tail}.md，标签页应有集合按现存分面深稿推断。"))
    pages = _parse_pages(html)
    tabs = _parse_tab_targets(html)
    page_ids = set(pages.keys())
    tab_ids = set(tabs)
    stats["pages"] = sorted(page_ids)
    stats["tabs"] = sorted(tab_ids)
    stats["expected_pages"] = sorted(expected)

    # 多页面（Intent-1 faces-split）才校验导航；单页面（理论上不该出现在 Intent-1）放过
    is_multi = len(page_ids) > 1 or len(tab_ids) > 0
    if is_multi:
        if page_ids != tab_ids:
            miss_tab = page_ids - tab_ids
            miss_page = tab_ids - page_ids
            detail = []
            if miss_tab:
                detail.append(f"有页面但无导航按钮: {sorted(miss_tab)}")
            if miss_page:
                detail.append(f"有导航按钮但无页面: {sorted(miss_page)}")
            issues.append(Issue("FAIL", "C1", "导航按钮与报告页不一致（" + "；".join(detail) + "）"))
        # 与"应有集合"比对（只在能确定应有集合时）
        if expected and page_ids != expected:
            miss = expected - page_ids
            extra = page_ids - expected
            detail = []
            if miss:
                detail.append(f"缺页: {sorted(miss)}")
            if extra:
                detail.append(f"多出页(源 md 不存在): {sorted(extra)}")
            issues.append(Issue("FAIL", "C1",
                                f"标签页集合与源 .md 推断的应有集合不符（{'；'.join(detail)}）"))
    else:
        issues.append(Issue("WARN", "C1",
                            "HTML 为单页面结构（无 Tab 导航）——Intent-1 应为 7 标签页多页面，请确认决策稿是否带 faces-split 标记。"))

    # ── C2/C3/C4 字面量泄漏（剔除 code/pre/script/style/svg 后扫描）──────
    scan = _strip_noise_html(html)
    # C2 占位符
    leaks_c2 = []
    for pat, label in ((r"\[\[\s*chart\s*[:：]", "[[chart:]]"),
                       (r"\[\[\s*图\s*[:：]", "[[图:]]"),
                       (r"\[\[\s*table\s*[:：]", "[[table:]]")):
        cnt = len(re.findall(pat, scan, re.I))
        if cnt:
            leaks_c2.append(f"{label}×{cnt}")
    # 兜底：任意残留 [[ （其它未知数据组件占位符）
    other = len(re.findall(r"\[\[", scan)) - sum(
        len(re.findall(p, scan, re.I)) for p, _ in
        ((r"\[\[\s*chart\s*[:：]", 0), (r"\[\[\s*图\s*[:：]", 0), (r"\[\[\s*table\s*[:：]", 0))
    )
    if other > 0:
        leaks_c2.append(f"其它[[…]]×{other}")
    if leaks_c2:
        issues.append(Issue("FAIL", "C2",
                            "正文残留未注入的占位符字面量（转换器未替换/删除）: " + "、".join(leaks_c2)))
    # C3 脚标
    src_leak = len(re.findall(r"\[\^src[\w\-]*\]", scan))
    if src_leak > 0:
        issues.append(Issue("FAIL", "C3",
                            f"正文残留裸脚标引用 [^src…]×{src_leak}（脚注定义缺失，未被 footnotes 扩展转换）"))
    # C4 跨引用（带方括号的才算泄漏；正常转换后无方括号）
    face_ref_leak = len(re.findall(r"\[详见\s*[：:]\s*(?:基本面|政策面|技术面|资金面|筹码面|消息面)\s*\]", scan))
    cross_ref_leak = len(re.findall(r"\[详见\s*§", scan))
    if face_ref_leak or cross_ref_leak:
        parts = []
        if face_ref_leak:
            parts.append(f"[详见：{{面}}]×{face_ref_leak}")
        if cross_ref_leak:
            parts.append(f"[详见§…]×{cross_ref_leak}")
        issues.append(Issue("FAIL", "C4",
                            "正文残留未转链接的跨引用字面量: " + "、".join(parts)))

    # ── C5 图表注入（WARN）────────────────────────────────────────────
    ok_charts = len(re.findall(r'<figure class="chart-figure"(?![^>]*chart-error)', html))
    err_charts = len(re.findall(r'class="chart-figure chart-error"', html))
    stats["charts_ok"] = ok_charts
    stats["charts_err"] = err_charts
    if err_charts > 0:
        issues.append(Issue("WARN", "C5",
                            f"{err_charts} 张图表生成失败（chart-error，属数据源/网络问题，非转换缺陷）。"))
    if ok_charts == 0 and err_charts == 0:
        issues.append(Issue("WARN", "C5", "HTML 未注入任何图表（若非 --no-charts 生成请核查 chart_generator）。"))

    # ── C6 内容覆盖率（每页 main.content 可见正文 vs 源 md 正文）──────────
    cov_rows: List[Tuple[str, int, int, float]] = []
    src_map: Dict[str, Optional[Path]] = {"page-决策": decision_md}
    for f, p in face_mds.items():
        src_map[f"page-{f}"] = p
    for pid, src in src_map.items():
        if pid not in pages or src is None:
            continue
        html_len = _visible_text_len(_main_content(pages[pid]))
        try:
            md_len = _md_plain_len(src.read_text(encoding="utf-8", errors="replace"))
        except Exception:  # noqa: BLE001
            md_len = 0
        cov = (html_len / md_len) if md_len else 1.0
        cov_rows.append((pid, html_len, md_len, cov))
        if md_len >= 500:  # 源太短不做覆盖率判断（避免噪音）
            if cov < _COVERAGE_FAIL:
                issues.append(Issue("FAIL", "C6",
                                    f"{pid} 正文覆盖率 {cov:.0%}（HTML {html_len} 字 / 源 md {md_len} 字）"
                                    f"低于 {_COVERAGE_FAIL:.0%}——疑整页内容在转换中丢失。"))
            elif cov < _COVERAGE_WARN:
                issues.append(Issue("WARN", "C6",
                                    f"{pid} 正文覆盖率 {cov:.0%}（HTML {html_len} / 源 {md_len}）偏低，请核查是否部分丢失。"))
    stats["coverage"] = cov_rows

    # ── C7 上游链路自证（台账 OVERALL: PASS + tail 匹配）──────────────────
    if check_ledger:
        ledger = ledger_path or (html_path.parent / "_delivery_gate_ledger.md")
        if not ledger.exists():
            issues.append(Issue("FAIL", "C7",
                                f"未找到交付台账 {ledger.name}：HTML 终检须建立在阶段1+2 PASS 之上，请先跑 gate_all.py。"))
        else:
            ltext = ledger.read_text(encoding="utf-8", errors="replace")
            tail_ok = (tail in ltext)
            overall_m = re.search(r"^##\s*OVERALL:\s*(PASS|FAIL)", ltext, re.M)
            pass_ok = bool(overall_m and overall_m.group(1) == "PASS")
            if not tail_ok:
                issues.append(Issue("FAIL", "C7",
                                    f"台账 {ledger.name} 不属于本报告（未匹配 tail『{tail}』）。"))
            if not pass_ok:
                verdict = overall_m.group(1) if overall_m else "缺失/无法解析"
                issues.append(Issue("FAIL", "C7",
                                    f"台账阶段1+2 裁决 OVERALL={verdict}（非 PASS），HTML 不应被生成/交付。"))

    return issues, stats


def main() -> None:
    ap = argparse.ArgumentParser(description="Intent-1 第三阶段 HTML 产物级终检门禁（薄·确定性）")
    ap.add_argument("html_file", help="待检 HTML 路径 OutputReport/交易决策报告_{tail}.html")
    ap.add_argument("--ledger", default=None, help="交付台账路径（默认 HTML 同目录 _delivery_gate_ledger.md）")
    ap.add_argument("--no-ledger-check", action="store_true", help="跳过 C7 上游链路自证（仅独立调试用，正式交付严禁）")
    args = ap.parse_args()

    html_path = Path(args.html_file)
    if not html_path.exists():
        print(f"[html_gate] ❌ 文件不存在: {html_path}", file=sys.stderr)
        sys.exit(1)

    issues, stats = run_html_gate(
        html_path,
        Path(args.ledger) if args.ledger else None,
        check_ledger=not args.no_ledger_check,
    )

    fails = [i for i in issues if i.level == "FAIL"]
    warns = [i for i in issues if i.level == "WARN"]
    passed = not fails

    print(f"# HTML 终检门禁（阶段3） — {html_path.name}")
    if stats.get("expected_pages"):
        print(f"  应有页: {stats['expected_pages']}")
    if "pages" in stats:
        print(f"  实有页: {stats.get('pages')}　导航按钮: {stats.get('tabs')}")
    if "charts_ok" in stats:
        print(f"  图表: 成功 {stats['charts_ok']} / 失败 {stats['charts_err']}")
    for pid, hl, ml, cov in stats.get("coverage", []):
        print(f"  覆盖率 {pid}: {cov:.0%}（HTML {hl} / 源 {ml}）")
    print("")
    if issues:
        for i in issues:
            print(str(i))
    else:
        print("  （无任何 FAIL/WARN）")
    print("")
    verdict = "PASS (exit 0)" if passed else "FAIL (exit 1)"
    print(f"## HTML_GATE: {verdict}　| FAIL {len(fails)} · WARN {len(warns)}")
    if not passed:
        print(">  存在 FAIL：HTML 产物不可交付。多数为转换器缺陷——优先在 md2html_report.py 加断言根治后重生成 HTML 再复检。")

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
