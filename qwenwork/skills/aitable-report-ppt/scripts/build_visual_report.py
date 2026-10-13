#!/usr/bin/env python3
"""Baseline reference renderer for visual reports.

This is the first consumer of the shared report-runtime.js and its functional
baseline: it proves the runtime works end to end, without constraining the DOM
of formal themes. It follows the native Frontend Slides model — one fixed
1920×1080 deck, one active slide — and delegates ALL correctness-critical
logic (aggregation, filter_ast membership, chart mounting, drill wiring,
stage scaling, keyboard control) to the runtime. This file must not contain a
second implementation of any of those functions.

Continuous reading reports require a separate user-requested renderer; they
are never silently combined with this deck.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


def runtime_contract_version(root: Path) -> str:
    """从 runtime 源文件读取合同版本，不在此处硬编码。

    硬编码会与 runtime 各自漂移：版本没跟上就让指纹因无关原因永久失败，
    行为变了版本没变则让旧报告被误判为兼容。
    """
    source = (root / "assets/components/report-runtime.js").read_text(encoding="utf-8")
    match = re.search(r"CONTRACT_VERSION\s*=\s*'([^']+)'", source)
    if not match:
        raise SystemExit("无法从 report-runtime.js 解析 CONTRACT_VERSION")
    return match.group(1)


def load(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256_file(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def find_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict) and isinstance(payload.get("records"), list):
        rows = payload["records"]
    elif isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        return find_records(payload["data"])
    else:
        rows = []
    result: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        cells = row.get("cells") if isinstance(row.get("cells"), dict) else row
        flat = {**cells}
        record_id = row.get("recordId") or row.get("rowId")
        if record_id:
            flat["__record_id"] = record_id
        else:
            flat["__local_row_key"] = row.get("localRowKey") or f"local-{index + 1}"
        result.append(flat)
    return result


def esc(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def metric_value(metric: dict[str, Any]) -> str:
    value = metric.get("display_value", metric.get("expected_value", "—"))
    return f"{esc(value)}{esc(metric.get('unit', ''))}"


def cell_coords(drill: dict[str, Any]) -> tuple[str, str] | None:
    """从下钻的双字段 filter_ast 取出这一格的两个坐标。

    坐标来自规格声明，不在这里重算聚合——渲染器不得持有第二份计算逻辑。
    """
    ast = (drill.get("membership") or {}).get("filter_ast") or {}
    if ast.get("op") != "and":
        return None
    eqs = [c for c in ast.get("children", []) if isinstance(c, dict) and c.get("op") == "eq"]
    if len(eqs) != 2:
        return None
    return str(eqs[0].get("value")), str(eqs[1].get("value"))


def heatmap_html(chart: dict[str, Any], drilldowns: list[dict[str, Any]]) -> str:
    """把热力图渲染成逐格可寻址的 DOM 网格。

    canvas 每格既没有可点元素、也无法检查遮挡，单个字符串 category 也表达不了
    二维坐标。每格一个真实元素后，尺寸、遮挡、点击这些既有检查自动覆盖到它。
    数值由 runtime 在启动时按 drilldown 成员数填入。
    """
    chart_id = chart.get("id")
    # 只有 count 口径下，成员数才等于该格要显示的值。
    count_is_value = (chart.get("aggregation") or {}).get("function") == "count"
    cells = []
    for drill in drilldowns:
        trigger = drill.get("trigger") or {}
        if trigger.get("type") != "chart" or trigger.get("ref_id") != chart_id:
            continue
        coords = cell_coords(drill)
        if not coords:
            continue
        x, y = coords
        declared = ""
        for entry in chart.get("cells", []) or []:
            if str(entry.get("x")) == x and str(entry.get("y")) == y:
                declared = f' data-cell-value="{esc(entry.get("value"))}"'
                break
        cells.append(
            f'<button class="heat-cell" data-heatmap-cell data-cell-x="{esc(x)}" '
            f'data-cell-y="{esc(y)}" data-drilldown-id="{esc(drill["id"])}"'
            f'{declared} data-count-is-value="{"true" if count_is_value else "false"}" '
            f'title="{esc(x)} · {esc(y)}"><span class="heat-value">·</span></button>'
        )
    return (f'<article class="chart-card heat-card"><h3>{esc(chart.get("title"))}</h3>'
            f'<div class="heat-grid" data-chart-id="{esc(chart_id)}">{"".join(cells)}</div></article>')


def build_slide(section: dict[str, Any], metrics: dict[str, dict], findings: dict[str, dict], charts: dict[str, dict], drilldowns: list[dict[str, Any]], index: int, total: int) -> str:
    metric_html = "".join(
        f'<button class="metric-card" data-metric-id="{esc(metric_id)}"><b>{metric_value(metrics[metric_id])}</b><span>{esc(metrics[metric_id].get("label"))}</span></button>'
        for metric_id in section.get("metric_ids", []) if metric_id in metrics
    )
    chart_html = "".join(
        heatmap_html(charts[chart_id], drilldowns)
        if charts[chart_id].get("type") == "heatmap"
        else f'<article class="chart-card"><h3>{esc(charts[chart_id].get("title"))}</h3><div class="chart" id="chart-{esc(chart_id)}" data-chart-id="{esc(chart_id)}"></div></article>'
        for chart_id in section.get("chart_ids", []) if chart_id in charts
    )
    finding_html = "".join(
        f'<li>{esc(findings[finding_id].get("text"))}</li>'
        for finding_id in section.get("finding_ids", []) if finding_id in findings
    )
    return f'''<section class="slide{' active visible' if index == 0 else ''}" data-slide="{index}">
      <div class="slide-content">
        <p class="eyebrow reveal">{esc(section.get('label'))}</p>
        <h2 class="reveal">{esc(section.get('title'))}</h2>
        <p class="section-purpose reveal">{esc(section.get('purpose'))}</p>
        <div class="metric-grid reveal">{metric_html}</div>
        <div class="chart-grid reveal">{chart_html}</div>
        <ul class="finding-list reveal">{finding_html}</ul>
      </div><span class="slide-number">{index + 1} / {total}</span>
    </section>'''


def validate_gate(args: argparse.Namespace, root: Path) -> None:
    if args.draft:
        return
    required = {
        "--blueprint": args.blueprint,
        "--content-approval": args.content_approval,
        "--design-selection": args.design_selection,
    }
    missing = [flag for flag, value in required.items() if not value]
    if missing:
        raise SystemExit(f"正式生成缺少门禁参数：{', '.join(missing)}。草稿请显式使用 --draft。")
    command = [
        sys.executable, str(root / "scripts" / "validate_generation_gate.py"),
        "--spec", args.spec,
        "--blueprint", args.blueprint,
        "--content-approval", args.content_approval,
        "--design-selection", args.design_selection,
    ]
    if args.manifest:
        command += ["--manifest", args.manifest]
    completed = subprocess.run(command, text=True)
    if completed.returncode:
        raise SystemExit("正式生成门禁未通过。")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True)
    parser.add_argument("--records", required=True)
    parser.add_argument("--fields", help="fields.json（可选，用于 zero_policy 的选项补全）")
    parser.add_argument("--output", required=True)
    parser.add_argument("--blueprint")
    parser.add_argument("--content-approval")
    parser.add_argument("--design-selection")
    parser.add_argument("--manifest")
    parser.add_argument("--draft", action="store_true")
    parser.add_argument("--theme", choices=("blue-column", "consulting-blue", "research-grid"), default="blue-column")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    validate_gate(args, root)
    spec = load(args.spec)
    modes = spec.get("modes") if isinstance(spec.get("modes"), dict) else {}
    if not modes.get("presentation", {}).get("enabled"):
        raise SystemExit("基础参考渲染器只生成演示稿；连续阅读报告需使用用户明确要求的独立渲染流程。")
    if modes.get("reading", {}).get("enabled"):
        raise SystemExit("基础参考渲染器不把阅读和演示塞进同一 HTML；请分别生成两个交付文件。")
    confidentiality = spec.get("report", {}).get("confidentiality", "internal")
    if confidentiality != "internal":
        raise SystemExit(
            f"基础参考渲染器直接内嵌完整记录，只支持 internal 等级（当前 {confidentiality}）。"
            "external_masked 需走 member_key 脱敏构建流程，public 只允许内嵌聚合值。"
        )

    records = find_records(load(args.records))
    fields: list = []
    if args.fields:
        payload = load(args.fields)
        fields = payload if isinstance(payload, list) else payload.get("fields", [])
    metrics = {row["id"]: row for row in spec.get("metrics", [])}
    findings = {row["id"]: row for row in spec.get("findings", [])}
    charts = {row["id"]: row for row in spec.get("charts", [])}
    sections = spec.get("sections", [])
    report = spec.get("report", {})
    slides = "".join(build_slide(section, metrics, findings, charts, spec.get("drilldowns", []), index, len(sections)) for index, section in enumerate(sections))

    themes = (root / "assets/themes/management-report-themes.css").read_text(encoding="utf-8")
    viewport = (root / "references/presentation/viewport-base.css").read_text(encoding="utf-8")
    drill_css = (root / "assets/components/standard-drilldown.css").read_text(encoding="utf-8")

    def inline_js(relative: str) -> tuple[str, str]:
        source = (root / relative).read_text(encoding="utf-8")
        digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
        return source.replace("</script", "<\\/script"), digest

    drill_js, _ = inline_js("assets/components/standard-drilldown.js")
    echarts_js, _ = inline_js("assets/vendor/echarts.min.js")
    runtime_js, runtime_hash = inline_js("assets/components/report-runtime.js")

    fingerprints = {
        "snapshot_sha256": sha256_file(args.records),
        "report_spec_sha256": sha256_file(args.spec),
        "semantics_version": spec.get("semantics_version", "1.0"),
        "runtime_contract_version": runtime_contract_version(root),
        "runtime_asset_sha256": runtime_hash,
    }

    def embed(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False).replace("</", "<\\/")

    draft_label = "【草稿】" if args.draft else ""
    css = r'''
*{box-sizing:border-box}button{font:inherit}.slide{padding:68px 92px 92px}.slide-content{height:100%;display:flex;flex-direction:column}.eyebrow{margin:0;font-size:24px;font-weight:800;letter-spacing:.13em;color:var(--report-primary)}.slide h2{margin:10px 0 8px;font-size:64px;line-height:1.05;color:var(--report-heading)}.section-purpose{margin:0;max-width:1200px;color:var(--report-muted);font-size:24px;line-height:1.55}.metric-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px;margin:24px 0}.metric-card{text-align:left;border:1px solid var(--report-line);border-radius:var(--report-radius);padding:19px;background:var(--report-card);color:var(--report-ink)}.metric-card b{display:block;font-size:42px;color:var(--report-primary)}.metric-card span{font-size:24px;color:var(--report-muted)}.chart-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px;flex:1;min-height:0}.chart-card{min-height:0;margin:0;padding:17px;display:flex;flex-direction:column;border:1px solid var(--report-line);border-radius:var(--report-radius);background:var(--report-card)}.chart-card h3{margin:0;font-size:24px}.chart{height:470px}.heat-card{grid-column:1/-1}.heat-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));grid-auto-rows:1fr;gap:12px;align-content:stretch;padding:12px 0;flex:1;min-height:0}.heat-cell{min-width:220px;height:100%;min-height:280px;border:1px solid var(--report-line);border-radius:6px;background:var(--report-card);color:var(--report-ink);cursor:pointer;font-size:24px;display:flex;align-items:center;justify-content:center}.heat-value{font-size:24px}.finding-list{display:grid;grid-auto-rows:max-content;align-content:start;gap:8px;margin:14px 0 0;padding-left:23px;font-size:24px;line-height:1.5}.slide-number{position:absolute;right:92px;bottom:38px;font-size:18px;color:var(--report-muted)}.deck-controls{display:flex;align-items:center;gap:10px;padding:8px 13px;border:1px solid var(--report-line);border-radius:999px;background:var(--report-surface);color:var(--report-ink)}.deck-controls button{width:36px;height:36px;border:0;border-radius:50%;background:transparent;color:var(--report-primary);cursor:pointer}.draft-badge{position:fixed;left:20px;top:20px;z-index:1000;padding:8px 12px;border-radius:8px;background:#b42318;color:#fff;font-weight:800}.reveal{opacity:0;transform:translateY(20px);transition:.45s ease}.slide.visible .reveal{opacity:1;transform:none}
'''

    # The baseline theme owns its DOM and hands nodes to the runtime via the
    # explicit mount API — the same protocol formal themes must follow.
    page_script = '''
(function(){
  var runtime = VisualReportRuntime.create({
    spec: window.REPORT_SPEC,
    records: window.REPORT_RECORDS,
    fields: window.REPORT_FIELDS,
    fingerprints: window.REPORT_FINGERPRINTS,
    echarts: window.echarts,
  });
  (window.REPORT_SPEC.charts || []).forEach(function (def) {
    /* A heat-map is DOM, not an ECharts instance: its cells are bound one by
     * one below so each is a real, measurable, clickable target. */
    if (def.type === 'heatmap') return;
    var node = document.getElementById('chart-' + def.id);
    if (node) runtime.mountChart(node, def.id);
  });
  document.querySelectorAll('[data-heatmap-cell]').forEach(function (cell) {
    var id = cell.dataset.drilldownId;
    if (!id) return;
    runtime.bindDrilldown(cell, id);
    /* Values come from the runtime's own membership resolution — the renderer
     * must never carry a second copy of the aggregation logic. */
    try {
      /* resolveMembers() returns {count, memberKeys}, not an array — reading
       * .length off it rendered the string "undefined" into every cell, and
       * the gate passed it: "undefined" is perfectly legible text. Legibility
       * checks cannot see wrongness, only illegibility.
       *
       * Member count is the cell's value only when the heat-map counts records.
       * For an attainment-rate matrix it is a different number entirely, so the
       * renderer refuses to invent one: the spec must state it. Leaving the
       * placeholder is deliberate — the gate then reports a missing value
       * rather than a plausible wrong one. */
      var label = cell.querySelector('.heat-value');
      if (!label) return;
      var declared = cell.dataset.cellValue;
      if (declared !== undefined && declared !== '') { label.textContent = declared; return; }
      if (cell.dataset.countIsValue !== 'true') return;
      var members = runtime.resolveMembers(id);
      if (members && typeof members.count === 'number') label.textContent = String(members.count);
    } catch (error) { /* leave the placeholder; the oracle check will speak */ }
  });
  var drilldowns = window.REPORT_SPEC.drilldowns || [];
  document.querySelectorAll('[data-metric-id]').forEach(function (node) {
    var metricId = node.dataset.metricId;
    var def = drilldowns.find(function (item) {
      return item.trigger && item.trigger.type === 'metric' && item.trigger.ref_id === metricId;
    });
    if (def) runtime.bindDrilldown(node, def.id);
  });
  var countNode = document.getElementById('deckCount');
  var deck = runtime.createDeckController({
    stage: document.getElementById('deckStage'),
    slides: document.querySelectorAll('.slide'),
    keyboard: true,
    onChange: function (current, total) {
      if (countNode) countNode.textContent = (current + 1) + ' / ' + total;
    },
  });
  document.getElementById('deckPrev').onclick = function () { deck.prev(); };
  document.getElementById('deckNext').onclick = function () { deck.next(); };
})();
'''

    document = f'''<!doctype html><html lang="zh-CN" data-theme="{esc(args.theme)}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{draft_label}{esc(report.get('title'))}</title><style>{themes}\n{viewport}\n{drill_css}\n{css}</style></head><body>
<div class="deck-viewport"><main class="deck-stage" id="deckStage">{slides}</main></div>
<div class="deck-controls"><button id="deckPrev" aria-label="上一页">←</button><span id="deckCount">1 / {len(sections)}</span><button id="deckNext" aria-label="下一页">→</button></div>
{f'<div class="draft-badge">内容或主题尚未确认 · 草稿</div>' if args.draft else ''}
<script data-vendor="echarts-inline" data-inlined="echarts">{echarts_js}</script>
<script data-inlined="drilldown">{drill_js}</script>
<script data-inlined="runtime">{runtime_js}</script>
<script>window.REPORT_SPEC={embed(spec)};window.REPORT_RECORDS={embed(records)};window.REPORT_FIELDS={embed(fields)};window.REPORT_FINGERPRINTS={embed(fingerprints)};</script>
<script>{page_script}</script></body></html>'''
    Path(args.output).write_text(document, encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
