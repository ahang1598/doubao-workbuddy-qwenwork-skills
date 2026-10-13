#!/usr/bin/env python3
"""故障注入：检验门禁本身有没有测量能力。

正式验收回答的是"这份报告有没有问题"；这里回答的是另一个问题——
"尺子还准不准"。两者不能互相替代：一份好样本通过、一份坏样本失败，
只能说明门禁在这两个点上有区分度，说明不了它是否还抓得住某一类故障。
本 skill 已经两次出现"门禁全绿但产物有缺陷"，都是因为没有人检验尺子。

做法：先造一份干净基线并确认它通过，再逐条注入已知故障，
要求**指定的那一项**检查失败。只断言"整体失败"是不够的——
低对比度故障若被无关的指纹检查拦下，看着也像失败，
而可读性门禁其实完全没起作用。
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _playwright import node_modules  # noqa: E402

# 不再写死本机绝对路径——发布出去的 skill 在别人机器上也要能跑
NODE_MODULES = node_modules() or ""

# 每条故障必须点名它要杀死的检查项；只要求"整体失败"会放过张冠李戴的情况。
MUTATIONS = [
    {
        "id": "ancestor-opacity",
        "also_expects": ['no oversized empty band', 'charts are not dimmed', 'minimum coverage', 'average coverage'],
        "why": "文字自身不透明，祖先被调成近乎透明——读者看不见",
        "expect": "no text hidden by a transparent ancestor",
        "style": ".slide-content{opacity:0.12 !important}",
    },
    {
        "id": "low-contrast",
        "why": "字号合格但颜色与背景几乎同色",
        "expect": "text meets contrast floors",
        "style": ".slide .section-purpose,.slide .finding-list,.slide .metric-card span"
                 "{color:#f2f4f7 !important}",
    },
    {
        "id": "tiny-font",
        "why": "为了塞下内容而缩小正文",
        "expect": "text meets displayed font floors",
        "style": ".slide .section-purpose,.slide .metric-card span{font-size:9px !important}",
    },
    {
        "id": "occluding-overlay",
        "also_expects": ['drill:'],
        "why": "可点目标被高层级遮罩盖住",
        "expect": "interactive targets are not obstructed",
        "style": ".slide-content::after{content:'';position:absolute;inset:0;z-index:99;"
                 "background:rgba(0,0,0,.01);pointer-events:auto}.slide-content{position:relative}",
    },
    {
        "id": "pointer-events-none",
        "also_expects": ['drill:'],
        "why": "目标看得见却接不到点击",
        "expect": "interactive targets are not obstructed",
        "style": ".metric-card,.chart{pointer-events:none !important}",
    },
    {
        "id": "tiny-hit-area",
        "why": "热区小到点不中",
        "expect": "interactive targets are not obstructed",
        # padding/border 必须一并清零：box-sizing:border-box 下，元素宽度不会
        # 低于左右内边距之和，只写 width:2px 的话实际仍有 40px，注入等于没生效。
        "style": ".metric-card{width:2px !important;height:2px !important;"
                 "padding:0 !important;border:0 !important;min-width:0 !important;"
                 "overflow:hidden}",
    },
    {
        "id": "iframe-401-expected",
        "why": "规格声明了要内嵌原始记录（expect_iframe），子框架 401 是「需人工在登录态复核」",
        "expect": "embedded record sources need a signed-in check",
        "expect_status": "manual_required",
        # 关键：只有规格确实承诺内嵌记录时，401 才降级为人工项。
        "spec_mutate": lambda d: d["validation"]["browser"]["drills"][0].__setitem__(
            "expect_iframe", True),
        "needs_401_server": True,
        # 只替换最后一个 </body>：内联 JS 字符串里也含这个字面量，
        # 全量替换会把标签塞进脚本中间，页面直接语法错误——
        # 那样的失败来自用例本身，不是被测逻辑。
        "replace_last": True,
        # 必须挂进 .avd-root：归属现在按"下钻组件是否真的挂载了这个 frame"判定，
        # 随手塞在 body 里的 iframe 不算记录来源，那样测到的是另一条分支。
        "html_replace": ["</body>",
                         "<script>window.addEventListener('load',function(){setTimeout(function(){"
                         "var r=document.querySelector('.avd-root');if(!r)return;"
                         "var f=document.createElement('iframe');"
                         "f.src='http://127.0.0.1:{PORT}/record';"
                         "f.style.cssText='width:2px;height:2px;border:0';"
                         "r.appendChild(f);},700);});</script></body>"],
    },
    {
        "id": "iframe-401-unexpected",
        "also_expects": ['runtime errors'],
        "why": "对照组：规格没承诺内嵌记录时，同样的子框架 401 必须硬失败。"
               "若两者判定相同，说明 expect_iframe 绑定根本没生效",
        "expect": "no undeclared embedded frames",
        "expect_status": "failed",
        "needs_401_server": True,
        "replace_last": True,
        "html_replace": ["</body>",
                         "<iframe src='http://127.0.0.1:{PORT}/other' "
                         "style='width:2px;height:2px;border:0'></iframe></body>"],
    },
    {
        "id": "unrelated-401",
        "also_expects": ['runtime errors'],
        "why": "对照组：页面自己的图片 401 是报告坏了，不能也降级成人工检查。"
               "若两者判定相同，说明归属判断根本没生效",
        "expect": "own resources load",
        "expect_status": "failed",
        "needs_401_server": True,
        "replace_last": True,
        "html_replace": ["</body>",
                         "<img src='http://127.0.0.1:{PORT}/logo.png' alt='' "
                         "style='width:1px;height:1px'></body>"],
    },
    {
        "id": "heatmap-unaddressable",
        "also_expects": ['chart initialization', 'heat-map grid matches', 'drill:'],
        "why": "热力图格子的标记被剥掉——退化成一整块，逐格既点不到也测不了",
        "expect": "drillable heat-map cells are individually addressable",
        "html_replace": ["data-heatmap-cell", "data-was-cell"],
    },
    {
        "id": "heatmap-missing-cell",
        "also_expects": ['drill:'],
        "why": "网格少一格——看着仍是完整矩阵，但有一格的记录永远进不去",
        "expect": "heat-map grid matches its declared cells",
        "replace_last": True,
        "html_replace": ["</body>",
                         "<script>window.addEventListener('load',function(){setTimeout(function(){"
                         "var c=document.querySelector('[data-heatmap-cell]');"
                         "if(c)c.remove();},600);});</script></body>"],
    },
    {
        "id": "heatmap-same-field-ast",
        "also_expects": ['drill:', 'heat-map grid matches', 'cell labels match the filter'],
        # 同字段双 eq 会让渲染器推导出的坐标变成 (A, A)，
        # 标签与筛选不一致是同一个故障的正当连带症状。
        "why": "某格的 filter_ast 把两个条件写在同一字段上——坐标轴宣称的二维含义是假的",
        "expect": "heat-map cell filters constrain two distinct fields",
        "spec_mutate": lambda d: next(
            (dr["membership"]["filter_ast"]["children"].__setitem__(
                1, {"op": "eq", "field": "分类", "value": "A"})
             for dr in d["drilldowns"] if dr["id"] == "drill_cell_A_M1"), None),
    },
    {
        "id": "heatmap-swapped-drill",
        "why": "两格的 drill id 互换——坐标集合仍完整、格子仍可点，"
               "但点 (A,M1) 打开的是 (A,M2) 的记录",
        "expect": "heat-map cell labels match the filter they run",
        "also_expects": ["rendered cell values match the oracle"],
        "replace_last": True,
        "html_replace": ["</body>",
                         "<script>window.addEventListener('load',function(){setTimeout(function(){"
                         "var c=document.querySelectorAll('[data-heatmap-cell]');"
                         "if(c.length<2)return;var a=c[0].dataset.drilldownId;"
                         "c[0].dataset.drilldownId=c[1].dataset.drilldownId;"
                         "c[1].dataset.drilldownId=a;},700);});</script></body>"],
    },
    {
        "id": "count-cells-contradict-oracle",
        "why": "count 口径的热力图额外声明了 cells，且与 oracle 矛盾。"
               "若规格能覆盖真值，写错一个数就等于把错误立成了标准",
        "expect": "rendered cell values match the oracle",
        "expect_status": "failed",
        "spec_mutate": lambda d: next(
            (c.__setitem__("cells", [{"x": "A", "y": "M1", "value": 777}])
             for c in d["charts"] if c["id"] == "chart_h"), None),
    },
    {
        "id": "noncount-wrong-display",
        "why": "sum 口径的格子显示值被改错——它的真值来自 chart.cells，"
               "不是成员数，走的是另一条判定分支",
        "expect": "rendered cell values match the oracle",
        "expect_status": "failed",
        "replace_last": True,
        "html_replace": ["</body>",
                         "<script>window.addEventListener('load',function(){setTimeout(function(){"
                         'var g=document.querySelector("[data-chart-id=\'chart_s\']");if(!g)return;'
                         "g.querySelectorAll('.heat-value').forEach(function(n){n.textContent='4242';});"
                         "},700);});</script></body>"],
    },
    {
        "id": "heatmap-wrong-ast-fields",
        "also_expects": ['drill:', 'cell labels match the filter', 'rendered cell values match the oracle'],
        "why": "某格的 AST 换成两个不同但错误的字段。注意：规格故障会连 HTML 一起重建，"
               "渲染器从同一份坏 AST 推导坐标，DOM 与声明会「一致地错」——"
               "「是否一致」这条检查在两边同源时永远为真，验的是一致性不是正确性。"
               "真正兜住它的是下钻内容对不上",
        "expect": "drill:",
        "spec_mutate": lambda d: next(
            (dr.__setitem__("membership", {**dr["membership"], "filter_ast": {"op": "and", "children": [
                {"op": "eq", "field": "编号", "value": "R1-0"},
                {"op": "eq", "field": "数量", "value": 10}]}})
             for dr in d["drilldowns"] if dr["id"] == "drill_cell_A_M1"), None),
    },
    {
        "id": "falsified-cell-value",
        "why": "格子显示的数字被改错——runtime 与 oracle 都算对了，"
               "但屏幕上印的是另一个数。计算正确不等于显示正确",
        "expect": "rendered cell values match the oracle",
        "expect_status": "failed",
        "replace_last": True,
        "html_replace": ["</body>",
                         "<script>window.addEventListener('load',function(){setTimeout(function(){"
                         "document.querySelectorAll('.heat-value').forEach(function(n){"
                         "n.textContent='999';});},700);});</script></body>"],
    },
    {
        # 容器的多余高度会流向两处，症状相反、病因同源。两条支路各打一次：
        # 灌进行框（本条）缝不变、框撑大；灌进缝里（下一条）框不变、缝撑大。
        "id": "stretched-rows",
        # 列表变高会真的把同页图表挤矮、下钻弹窗随之打不开——这是真实连锁，
        # 不是误报，所以如实申报而不是想办法绕开。
        "also_expects": ['minimum coverage', 'average coverage', 'no oversized empty band',
                         'primary charts meet minimum height', 'drill:'],
        "why": "多余高度灌进行框自身（grid-auto-rows:1fr）——缝还是声明的 8px，"
               "每个行框却撑到三倍高，一行字孤零零悬在空框里。"
               "只盯「缝有多宽」的判据看不见这一种",
        "expect": "list rows are not stretched to fill their container",
        "style": ".finding-list{display:grid !important;grid-auto-rows:1fr !important;"
                 "height:330px !important;gap:8px !important;align-content:stretch !important}",
    },
    {
        "id": "stretched-gaps",
        "also_expects": ['minimum coverage', 'average coverage', 'no oversized empty band',
                         'primary charts meet minimum height', 'drill:'],
        "why": "多余高度灌进行与行之间（align-content:space-between）——"
               "行框还是内容高，缝从声明的 8px 撑到上百像素。"
               "这是 v4 第 10 页的真实症状",
        "expect": "list rows are not stretched to fill their container",
        "style": ".finding-list{display:grid !important;grid-auto-rows:min-content !important;"
                 "height:330px !important;gap:8px !important;"
                 "align-content:space-between !important}",
    },
    {
        "id": "leaked-placeholder",
        "also_expects": ['rendered cell values match the oracle'],
        "why": "取值失败后把 undefined 当内容渲染出来——字号对比度都合格，"
               "可读性检查天然看不见它",
        "expect": "no placeholder or error literals rendered",
        # 必须在绑定之后注入：启动代码会用真实数值覆盖 textContent，
        # 直接改 HTML 会被它抹掉，测到的就不是这条路径。
        "expect_status": "failed",
        "replace_last": True,
        "html_replace": ["</body>",
                         "<script>window.addEventListener('load',function(){setTimeout(function(){"
                         "var n=document.querySelector('.heat-value');"
                         "if(n)n.textContent='undefined';},600);});</script></body>"],
    },
    {
        "id": "chart-low-contrast",
        "why": "canvas 里的坐标轴文字与底色几乎同色——DOM 对比度检查看不到它",
        "expect": "chart text meets contrast floors",
        # 改的是 ECharts option 而非 CSS，故用脚本注入。
        # 必须显式带上 fontSize：整体替换 axisLabel 会连 runtime 设的字号一起抹掉，
        # 那样先撞上字号检查，测到的就不是对比度这条路径了。
        "html_replace": ["</body>",
                         "<script>window.addEventListener('load',function(){setTimeout(function(){"
                         "document.querySelectorAll('[data-chart-id]').forEach(function(el){"
                         "var i=window.echarts&&window.echarts.getInstanceByDom(el);"
                         "if(i)i.setOption({xAxis:{axisLabel:{color:'#fdfdfd',fontSize:21}},"
                         "yAxis:{axisLabel:{color:'#fdfdfd',fontSize:21}}});});},400);});</script></body>"],
        "replace_last": True,
    },
    {
        "id": "chart-hsl-low-contrast",
        "why": "坐标轴文字用 HSL 记号写成近白色。按数字硬扫会读成 [0,0,96] 的深蓝，"
               "算出高对比度而放行——记号必须真的被解析",
        "expect": "chart text meets contrast floors",
        "replace_last": True,
        "html_replace": ["</body>",
                         "<script>window.addEventListener('load',function(){setTimeout(function(){"
                         "document.querySelectorAll('[data-chart-id]').forEach(function(el){"
                         "var i=window.echarts&&window.echarts.getInstanceByDom(el);"
                         "if(i)i.setOption({xAxis:{axisLabel:{color:'hsl(0, 0%, 96%)',fontSize:21}},"
                         "yAxis:{axisLabel:{color:'hsl(0, 0%, 96%)',fontSize:21}}});});},400);});"
                         "</script></body>"],
    },
    {
        "id": "chart-dimmed",
        "also_expects": ['no oversized empty band', 'no text hidden by a transparent ancestor', 'minimum coverage', 'average coverage'],
        "why": "图表被半透明祖先压暗——正是用户投诉的折线和坐标轴发灰",
        "expect": "charts are not dimmed by a transparent ancestor",
        "style": ".chart-grid{opacity:0.35 !important}",
    },
    {
        "id": "decorative-abuse",
        "also_expects": ['minimum coverage', 'average coverage', 'no oversized empty band'],
        "why": "把承载正文的容器标成 decorative，一举跳过字号、对比度和覆盖率三项检查",
        "expect": "decorative role is not used to skip checks",
        # 这条改的是 DOM 属性而非样式，故用 html_replace 而不是注入 CSS。
        "html_replace": ['class="slide-content"',
                         'class="slide-content" data-visual-role="decorative"'],
    },
    {
        "id": "pseudo-gradient",
        "why": "渐变画在 ::before 上——元素自身 backgroundColor 仍是纯色，"
               "只看自身背景会拿错底色",
        "expect": "contrast undecidable over non-solid background",
        "expect_status": "manual_required",
        "style": ".slide-content{position:relative}"
                 ".slide-content::before{content:'';position:absolute;inset:0;"
                 "background-image:linear-gradient(90deg,#fff,#000);z-index:-1}",
    },
    {
        "id": "gradient-background",
        "why": "渐变底色下 backgroundColor 为透明，不能按纯色推断",
        "expect": "contrast undecidable over non-solid background",
        # 不止要有具名失败，整轮状态必须是 manual_required——若它被折算成
        # 普通 failed，就等于把"没能判定"混进了"已判定有缺陷"，三态形同虚设。
        "expect_status": "manual_required",
        "style": ".slide{background-image:linear-gradient(90deg,#fff,#000) !important}",
    },
]


class _Unauthorized(BaseHTTPRequestHandler):
    """恒定返回 401，用来真实触发"外部资源需要登录"这条路径。"""

    def do_GET(self):  # noqa: N802
        self.send_response(401)
        self.end_headers()

    def log_message(self, *args):  # 静音
        return


def start_401_server() -> tuple[HTTPServer, int]:
    server = HTTPServer(("127.0.0.1", 0), _Unauthorized)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, server.server_address[1]


def write(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def build_baseline(work: Path) -> Path:
    """造一份应当通过全部门禁的最小报告，含一个指标和一个柱图。"""
    blueprint_path = work / "content-blueprint.json"
    approval_path = work / "content-approval.json"
    design_path = work / "design-selection.json"
    spec_path = work / "report-spec.json"
    records_path = work / "records.json"
    manifest_path = work / "manifest.json"
    preview_path = work / "preview.html"
    report_path = work / "baseline.html"

    # 数据形态先算好：蓝图、规格、浏览器用例的期望值全部由它推导，
    # 不再各处硬编码——数据一变而期望没跟上，是这份夹具反复出过的错。
    MONTHS = ("M1", "M2", "M3", "M4", "M5", "M6")
    _cells = [(c, m) for c in ("A", "B") for m in MONTHS]
    _rows = []
    for idx, (c, m) in enumerate(_cells, start=1):
        for k in range(idx):                  # 第 idx 格放 idx 条，各格值不同
            _rows.append({"编号": f"R{idx}-{k}", "分类": c, "月份": m, "数量": 10})
    CELL_COUNT = {(c, m): i for i, (c, m) in enumerate(_cells, start=1)}
    TOTAL = sum(CELL_COUNT.values())
    A_TOTAL = sum(v for (c, _), v in CELL_COUNT.items() if c == "A")
    B_TOTAL = sum(v for (c, _), v in CELL_COUNT.items() if c == "B")

    write(blueprint_path, {
        "report": {"title": "门禁自检基线", "purpose": "检验门禁", "audience": "工程",
                   "delivery_type": "presentation", "density": "reading-first"},
        # 蓝图页数必须与规格一致：先前蓝图写 1 页、规格 3 页，
        # 内容契约与产物各说各话，正样本就不成其为闭环。
        "story": {"core_message": "基线", "narrative": "结论先行",
                  "estimated_slide_count": 4, "chapters": ["总体", "分布", "矩阵", "数量和"]},
        "slides": [
            {"id": "s1", "title": "总体", "management_question": "如何？",
             "key_message": "基线", "body_points": ["结论"], "source_refs": ["src"],
             "charts": [{"type": "bar", "title": "分类分布", "data_summary": f"A={A_TOTAL},B={B_TOTAL}",
                         "metric_ids": ["metric_a"]}]},
            {"id": "s2", "title": "分布", "management_question": "构成如何？",
             "key_message": "两类各半", "body_points": ["构成"], "source_refs": ["src"],
             "charts": [{"type": "line", "title": "分类趋势", "data_summary": f"A={A_TOTAL},B={B_TOTAL}"},
                        {"type": "donut", "title": "分类占比", "data_summary": f"A={A_TOTAL},B={B_TOTAL}"}]},
            {"id": "s3", "title": "矩阵", "management_question": "交叉如何？",
             "key_message": "12 格均有数据", "body_points": ["交叉"], "source_refs": ["src"],
             "charts": [{"type": "heatmap", "title": "分类 x 月份", "data_summary": "12 格"}]},
            {"id": "s4", "title": "数量和", "management_question": "总量怎么分布？",
             "key_message": "6 格数量之和", "body_points": ["总量"], "source_refs": ["src"],
             "charts": [{"type": "heatmap", "title": "分类 x 月份 · 数量和", "data_summary": "12 格"}]},
        ],
    })
    blueprint_hash = hashlib.sha256(blueprint_path.read_bytes()).hexdigest()
    write(approval_path, {
        "status": "approved", "approved_at": "2026-08-20T12:00:00+08:00",
        "approval_source": "user_explicit", "blueprint_path": str(blueprint_path),
        "blueprint_sha256": blueprint_hash,
        "approved_scope": ["story", "key_messages", "slide_allocation", "chart_plan"],
        "approved_degradations": ["no_original_record_links"], "requested_changes": [],
    })
    preview_path.write_text(
        "<!doctype html><html><head><meta charset='utf-8'><title>预览</title></head>"
        "<body><main class='preview-stage'><h1>预览</h1></main></body></html>\n",
        encoding="utf-8")
    write(design_path, {
        "status": "approved", "selected_preview": "style-a",
        "approved_at": "2026-08-20T12:01:00+08:00", "approval_source": "user_explicit",
        "selection_mode": "preview", "selected_preview_path": str(preview_path),
        "selected_preview_sha256": hashlib.sha256(preview_path.read_bytes()).hexdigest(),
    })
    # 加入月份维度，才能构成真正的二维网格（2 分类 x 3 月份）。
    # 不是 v4 的 5x12，但同样是二维——协议验证不依赖格数多少，夹具跑得更快。
    write(records_path, _rows)
    write(manifest_path, {"record_id_fidelity": "missing", "record_id_coverage": 0.0,
                          "record_link_coverage": 0.0})
    write(spec_path, {
        "schema_version": "1.0",
        "report": {"title": "门禁自检基线", "audience": "工程", "purpose": "检验门禁",
                   "confidentiality": "internal", "snapshot_at": "2026-08-20"},
        "sources": [{"id": "src", "name": "明细", "type": "aitable"}],
        "metrics": [{"id": "metric_a", "label": "记录数", "kind": "data_fact",
                     "evidence": ["src"], "verification": "exact", "display_value": str(TOTAL)}],
        # 有内容的结论列表：先前是空数组，导致拉伸类故障注在了一个没有行的
        # 容器上，检查直接跳过——故障看着"没被抓住"，其实是没施加。
        "findings": [
            {"id": "f1", "text": "A 类记录数为 B 类的一半，集中在前三个月。",
             "evidence": ["src"], "kind": "data_fact"},
            {"id": "f2", "text": "各月记录数递增，末月为首月的六倍。",
             "evidence": ["src"], "kind": "data_fact"},
            {"id": "f3", "text": "全部 12 个交叉格均有数据，无空缺。",
             "evidence": ["src"], "kind": "data_fact"},
        ],
        "charts": [{"id": "chart_a", "title": "分类分布", "type": "bar", "source_id": "src",
                    "question": "各分类各有多少条记录？", "evidence": ["src"],
                    "aggregation": {"group_by": "分类", "function": "count"}},
                   {"id": "chart_b", "title": "分类趋势", "type": "line", "source_id": "src",
                    "question": "分类的走势如何？", "evidence": ["src"],
                    "aggregation": {"group_by": "分类", "function": "count"}},
                   # 环图：验证扇区中点的角度与半径换算。算错就点在空洞或错误扇区上，
                   # 弹窗打不开或行数不对，基线立刻失败——不需要单独写断言。
                   {"id": "chart_c", "title": "分类占比", "type": "donut", "source_id": "src",
                    "question": "两个分类各占多少？", "evidence": ["src"],
                    "aggregation": {"group_by": "分类", "function": "count"}},
                   {"id": "chart_h", "title": "分类 x 月份", "type": "heatmap", "source_id": "src",
                    "question": "分类与月份的交叉分布如何？", "evidence": ["src"],
                    "aggregation": {"group_by": "分类", "function": "count"}},
                   # 非 count 口径：每格显示数量之和（10k），与成员数（k）明显不同。
                   # 用满 2x6：6 格撑不满页面，密度门禁会失败——
                   # 那是夹具不真实，不该靠 CSS 去迁就。
                   # 两个分支的差别只有在数值不同时才测得出来。
                   {"id": "chart_s", "title": "分类 x 月份 · 数量和", "type": "heatmap",
                    "source_id": "src", "question": "各交叉格的数量之和是多少？",
                    "evidence": ["src"],
                    "aggregation": {"group_by": "分类", "function": "sum", "value_field": "数量"},
                    "cells": [{"x": c, "y": m, "value": CELL_COUNT[(c, m)] * 10}
                              for c in ("A", "B") for m in MONTHS]}],
        "drilldowns": [
            {"id": "drill_metric", "source_id": "src", "columns": ["编号"], "mode": "local_only",
             "trigger": {"type": "metric", "ref_id": "metric_a"},
             "membership": {"filter_ast": {"op": "all"}, "expected_record_count": TOTAL,
                            "verification": {"method": "exact"}}},
            {"id": "drill_chart_a", "source_id": "src", "columns": ["编号"], "mode": "local_only",
             "trigger": {"type": "chart", "ref_id": "chart_a", "category": "A"},
             "membership": {"filter_ast": {"op": "eq", "field": "分类", "value": "A"},
                            "expected_record_count": A_TOTAL, "verification": {"method": "exact"}}},
            # 整图下钻（无 category）：验证器若强求 category，这条会以
            # category-not-in-chart 误判失败。放进基线，修复就不会悄悄退化。
            {"id": "drill_chart_c_b", "source_id": "src", "columns": ["编号"], "mode": "local_only",
             "trigger": {"type": "chart", "ref_id": "chart_c", "category": "B"},
             "membership": {"filter_ast": {"op": "eq", "field": "分类", "value": "B"},
                            "expected_record_count": B_TOTAL, "verification": {"method": "exact"}}},
            # 每格一个下钻，filter_ast 必须约束两个不同字段——渲染器正是从这里
            # 读出该格的两个坐标，不重算聚合。
            # 每格一个下钻，filter_ast 约束两个不同字段——渲染器正是从这里
            # 读出该格的两个坐标，不重算聚合。
            *[{"id": f"drill_cell_{c}_{m}", "source_id": "src", "columns": ["编号"],
               "mode": "local_only",
               "trigger": {"type": "chart", "ref_id": "chart_h", "category": f"{c}|{m}"},
               "membership": {"filter_ast": {"op": "and", "children": [
                   {"op": "eq", "field": "分类", "value": c},
                   {"op": "eq", "field": "月份", "value": m}]},
                   "expected_record_count": CELL_COUNT[(c, m)],
                   "verification": {"method": "exact"}}}
              for c in ("A", "B") for m in MONTHS],
            *[{"id": f"drill_sum_{c}_{m}", "source_id": "src", "columns": ["编号"],
               "mode": "local_only",
               "trigger": {"type": "chart", "ref_id": "chart_s", "category": f"{c}|{m}"},
               "membership": {"filter_ast": {"op": "and", "children": [
                   {"op": "eq", "field": "分类", "value": c},
                   {"op": "eq", "field": "月份", "value": m}]},
                   "expected_record_count": CELL_COUNT[(c, m)],
                   "verification": {"method": "exact"}}}
              for c in ("A", "B") for m in MONTHS],
            {"id": "drill_chart_all", "source_id": "src", "columns": ["编号"], "mode": "local_only",
             "trigger": {"type": "chart", "ref_id": "chart_b"},
             "membership": {"filter_ast": {"op": "all"}, "expected_record_count": TOTAL,
                            "verification": {"method": "exact"}}},
        ],
        # 三个图表挤一页会撑破画布（2 列 × 470px + 标题 > 1080px）。
        # 拆两页，让"布局装不下"不会被误读成"几何算错"。
        "sections": [
            {"id": "s1", "label": "总体", "title": "总体结果", "purpose": "看结果",
             "slide_role": "cover", "metric_ids": ["metric_a"], "chart_ids": ["chart_a"],
             "finding_ids": ["f1", "f2", "f3"]},
            {"id": "s2", "label": "分布", "title": "分类分布", "purpose": "看构成",
             "slide_role": "analysis", "chart_ids": ["chart_b", "chart_c"]},
            {"id": "s3", "label": "矩阵", "title": "分类 x 月份", "purpose": "看交叉",
             "slide_role": "analysis", "chart_ids": ["chart_h"]},
            {"id": "s4", "label": "数量和", "title": "交叉数量之和", "purpose": "看总量分布",
             "slide_role": "analysis", "chart_ids": ["chart_s"]},
        ],
        "privacy": {},
        "modes": {"presentation": {"enabled": True, "stage": "1920x1080", "density": "reading-first"},
                  "reading": {"enabled": False, "requested_by_user": False}},
        "validation": {"browser": {"drills": [
            {"drilldown_id": "drill_metric", "name": "指标下钻", "slide": 0,
             "trigger": "[data-metric-id='metric_a']", "modal": ".avd-root.avd-open",
             "rows": ".avd-table tbody tr", "expected_count": TOTAL, "close": ".avd-close"},
            {"drilldown_id": "drill_chart_a", "name": "柱图分类下钻", "slide": 0,
             "trigger": "[data-chart-id='chart_a']", "modal": ".avd-root.avd-open",
             "rows": ".avd-table tbody tr", "expected_count": A_TOTAL, "close": ".avd-close"},
            {"drilldown_id": "drill_chart_c_b", "name": "环图扇区下钻", "slide": 1,
             "trigger": "[data-chart-id='chart_c']", "modal": ".avd-root.avd-open",
             "rows": ".avd-table tbody tr", "expected_count": B_TOTAL, "close": ".avd-close"},
            # 每个格子下钻都要有用例——覆盖门禁不接受"抽查一格代表全部"。
            *[{"drilldown_id": f"drill_cell_{c}_{m}", "name": f"热力图 {c}-{m} 下钻",
               "slide": 2,
               "trigger": f"[data-heatmap-cell][data-cell-x='{c}'][data-cell-y='{m}']",
               "modal": ".avd-root.avd-open", "rows": ".avd-table tbody tr",
               "expected_count": CELL_COUNT[(c, m)], "close": ".avd-close"}
              for c in ("A", "B") for m in MONTHS],
            *[{"drilldown_id": f"drill_sum_{c}_{m}", "name": f"数量和 {c}-{m} 下钻",
               "slide": 3,
               "trigger": f"[data-chart-id='chart_s'] [data-cell-x='{c}'][data-cell-y='{m}']",
               "modal": ".avd-root.avd-open", "rows": ".avd-table tbody tr",
               "expected_count": CELL_COUNT[(c, m)], "close": ".avd-close"}
              for c in ("A", "B") for m in MONTHS],
            {"drilldown_id": "drill_chart_all", "name": "折线图整图下钻", "slide": 1,
             "trigger": "[data-chart-id='chart_b']", "modal": ".avd-root.avd-open",
             "rows": ".avd-table tbody tr", "expected_count": TOTAL, "close": ".avd-close"},
        ]}},
    })
    oracle_path = work / "verification-oracle.json"
    subprocess.run([sys.executable, str(ROOT / "scripts/build_visual_report.py"),
                    "--spec", str(spec_path), "--records", str(records_path),
                    "--output", str(report_path), "--blueprint", str(blueprint_path),
                    "--content-approval", str(approval_path),
                    "--design-selection", str(design_path), "--manifest", str(manifest_path)],
                   check=True, capture_output=True, text=True)
    # 让基线带 oracle 跑：没有独立真值，浏览器观察值只是自说自话。
    subprocess.run([sys.executable, str(ROOT / "scripts/build_verification_oracle.py"),
                    "--spec", str(spec_path), "--records", str(records_path),
                    "--output", str(oracle_path)],
                   check=True, capture_output=True, text=True)
    return report_path, spec_path, oracle_path


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    import os
    return subprocess.run(cmd, text=True, env={**os.environ, "CODEX_NODE_MODULES": NODE_MODULES}, **kw)


def build_report(work: Path, spec_path: Path, tag: str):
    """按给定规格重建报告与真值，使指纹链自洽。

    返回 (html, oracle)；规格已非法导致构建失败时返回 None。
    """
    html = work / f"rebuilt-{tag}.html"
    oracle = work / f"oracle-{tag}.json"
    built = run([sys.executable, str(ROOT / "scripts/build_visual_report.py"),
                 "--spec", str(spec_path), "--records", str(work / "records.json"),
                 "--output", str(html), "--blueprint", str(work / "content-blueprint.json"),
                 "--content-approval", str(work / "content-approval.json"),
                 "--design-selection", str(work / "design-selection.json"),
                 "--manifest", str(work / "manifest.json")], capture_output=True)
    if built.returncode:
        return None
    made = run([sys.executable, str(ROOT / "scripts/build_verification_oracle.py"),
                "--spec", str(spec_path), "--records", str(work / "records.json"),
                "--output", str(oracle)], capture_output=True)
    return (html, oracle) if made.returncode == 0 else None


def run_validator(html: Path, spec: Path, out: Path, oracle: Path | None = None) -> dict:
    """跑验收并区分三种结局：判定通过、判定失败、以及**根本没判定**。

    最初这里在读不到输出文件时返回空 runs，于是"验证器崩溃"和"没有任何失败"
    在数据上完全一样，harness 把崩溃读成了"故障存活"。崩溃必须是独立的一类，
    否则检验尺子的工具自己也在把沉默当成结论。
    """
    import os
    env = {**os.environ, "CODEX_NODE_MODULES": NODE_MODULES}
    command = ["node", str(ROOT / "scripts/validate_visual_report.js"),
               str(html), str(spec), "--output", str(out)]
    if oracle:
        command += ["--oracle", str(oracle)]
    proc = subprocess.run(command, capture_output=True, text=True, env=env)
    if not out.exists():
        return {"crashed": True, "stderr": (proc.stderr or "")[-400:], "runs": []}
    payload = json.loads(out.read_text(encoding="utf-8"))
    payload["crashed"] = False
    return payload


def failed_checks(result: dict) -> list[str]:
    return [c["name"] for run in result.get("runs", []) for c in run.get("checks", [])
            if not c.get("passed")]


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="aitable-mutations-") as directory:
        work = Path(directory)
        report, spec, oracle = build_baseline(work)
        html = report.read_text(encoding="utf-8")

        # 基线先要是一份合法规格。此前它缺 charts[].question / evidence，
        # 却仍被当作金标准——一份自己都不合规的样本，证明不了别的东西合规。
        spec_check = run([sys.executable, str(ROOT / "scripts/validate_report_spec.py"), str(spec)],
                         capture_output=True)
        if spec_check.returncode:
            print("❌ 基线规格未通过 validate_report_spec.py：")
            print(spec_check.stdout[:800])
            sys.exit(1)
        print("✅ 基线规格合法")

        base = run_validator(report, spec, work / "base.json", oracle)
        if base.get("crashed"):
            print("❌ 基线把验证器跑崩了：\n", base.get("stderr", ""))
            sys.exit(1)
        base_failures = failed_checks(base)
        if base_failures:
            print("❌ 基线本身就没通过，故障注入无从谈起：")
            for name in base_failures:
                print("   -", name)
            sys.exit(1)
        baseline_failures = set(base_failures)      # 空集：基线必须全绿
        print(f"✅ 基线通过（{base.get('passed')} 项检查）\n")

        survived, mismatched, crashed = [], [], []
        server_401, port_401 = start_401_server()
        for mutation in MUTATIONS:
            if mutation.get("html_replace"):
                find, repl = mutation["html_replace"]
                if find not in html:
                    print(f"⚠️  {mutation['id']:22s} 注入锚点不存在，用例无效（不是门禁的问题）")
                    mismatched.append(mutation["id"])
                    continue
                target = repl.replace("{PORT}", str(port_401))
                if mutation.get("replace_last"):
                    at = html.rfind(find)
                    injected = html[:at] + target + html[at + len(find):]
                else:
                    injected = html.replace(find, target)
            elif mutation.get("style"):
                injected = html.replace("</head>", f"<style>{mutation['style']}</style></head>", 1)
            else:
                # 纯 spec 故障：HTML 原样，缺陷只存在于规格里。
                injected = html
            # 先定好这轮用什么规格/真值/产物，再决定验哪个文件——
            # 先前的写法在赋值之前就引用了 rebuilt_html，第一轮直接崩。
            spec_for_run = spec
            rebuilt_html = None
            oracle_for_run = oracle          # 故障也要带 oracle：不带的话，
            # 依赖 oracle 的检查（如"显示值 vs 真值"）根本不会执行，
            # 故障看着"存活"，其实是那条检查压根没跑。
            if mutation.get("spec_mutate"):
                # 有些缺陷只存在于规格里（例如双字段 AST 写成同一字段），
                # 只改 HTML 测不到，故支持对 spec 做一次性变形。
                import copy
                data = json.loads(spec.read_text(encoding="utf-8"))
                mutation["spec_mutate"](data)
                spec_for_run = work / f"spec-{mutation['id']}.json"
                write(spec_for_run, data)
                # 规格变了就连 HTML 一并重建，让指纹链自洽。
                # 先前只是"不带真值"，结果依赖 oracle 的检查整个不执行——
                # 故障看着"存活"，其实是那条检查压根没跑到。
                rebuilt = build_report(work, spec_for_run, mutation["id"])
                if rebuilt:
                    rebuilt_html, oracle_for_run = rebuilt
                else:
                    rebuilt_html, oracle_for_run = None, None
            path = work / f"mut-{mutation['id']}.html"
            if rebuilt_html is not None:
                # 规格故障验的是按新规格重建的产物；但若这条故障同时还要改 HTML，
                # 注入必须重新打到重建后的文件上——否则直接用重建产物会把注入丢掉，
                # 故障看着"存活"，其实压根没被施加。
                rebuilt_text = rebuilt_html.read_text(encoding="utf-8")
                if mutation.get("html_replace"):
                    find, repl = mutation["html_replace"]
                    target = repl.replace("{PORT}", str(port_401))
                    if mutation.get("replace_last"):
                        at = rebuilt_text.rfind(find)
                        rebuilt_text = rebuilt_text[:at] + target + rebuilt_text[at + len(find):]
                    else:
                        rebuilt_text = rebuilt_text.replace(find, target)
                elif mutation.get("style"):
                    rebuilt_text = rebuilt_text.replace(
                        "</head>", f"<style>{mutation['style']}</style></head>", 1)
                path.write_text(rebuilt_text, encoding="utf-8")
            else:
                path.write_text(injected, encoding="utf-8")
            result = run_validator(path, spec_for_run,
                                   work / f"mut-{mutation['id']}.json", oracle_for_run)
            if result.get("crashed"):
                # 崩溃既不是"拦下"也不是"存活"：验证器没能给出判定。
                print(f"💥 {mutation['id']:22s} 让验证器崩溃，没有产出判定")
                crashed.append(mutation["id"])
                continue
            names = failed_checks(result)
            hit = [n for n in names if mutation["expect"] in n]
            # 差分断言：故障相对基线只允许新增「目标项」和明确申报的附带项。
            # 只要求目标项失败的话，一个把整页打烂的注入也能冒充精准探针——
            # 它确实让目标项挂了，但同时掩盖了自己波及范围过大的事实。
            allowed = {mutation["expect"], *mutation.get("also_expects", [])}
            stray = [n for n in names
                     if n not in baseline_failures
                     and not any(a in n for a in allowed)]
            if hit and stray:
                print(f"⚠️  {mutation['id']:22s} 命中目标，但波及了额外检查：{stray[:3]}")
                mismatched.append(mutation["id"])
                continue
            if hit:
                want = mutation.get("expect_status")
                got = result.get("status")
                if want and got != want:
                    print(f"⚠️  {mutation['id']:22s} 命中了具名检查，但整轮状态是 {got}，应为 {want}")
                    mismatched.append(mutation["id"])
                    continue
                suffix = f"，状态 {got}" if want else ""
                print(f"✅ {mutation['id']:22s} 被『{mutation['expect']}』拦下{suffix}")
            elif names:
                print(f"⚠️  {mutation['id']:22s} 失败了，但不是目标检查：{names[:3]}")
                mismatched.append(mutation["id"])
            else:
                print(f"❌ {mutation['id']:22s} 存活——门禁看不见这类故障（{mutation['why']}）")
                survived.append(mutation["id"])

        print()
        if survived or mismatched or crashed:
            if survived:
                print(f"存活 {len(survived)} 条：{', '.join(survived)}")
            if mismatched:
                print(f"张冠李戴 {len(mismatched)} 条：{', '.join(mismatched)}")
            if crashed:
                print(f"令验证器崩溃 {len(crashed)} 条：{', '.join(crashed)}"
                      "（应改为具名失败，而不是中断整轮验收）")
            sys.exit(1)
        print(f"全部 {len(MUTATIONS)} 条故障均被对应检查拦下。")


if __name__ == "__main__":
    main()
