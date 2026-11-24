"""exhibit_help(): figure router + independent chart recipes, annotations, conversion and XML composition.

Every recipe's code is executed by tests/test_exhibit.py, so the snippets stay valid.
"""

from __future__ import annotations

import re

_HEAD = """# exhibit — 咨询图表（可独立生成 SVG）

exhibit_help('standalone')：独立画布、柱图/折线/瀑布/排名 SVG 示例与导出。
exhibit_help('atomize')：SVG 转原生元素，与其它 page_xml 合页并一次提交。
exhibit_help('方案名')：数据条件、图表配方与标注；exhibit_help('函数名')：参数；exhibit_help('api')：接口总表。
只制作单图用 Exhibit + 绘图函数 + save；页面其它内容用 XML，按需转换与合页。
颜色用 ex.C 角色，focus 只突出主角；图内坐标使用 ex.body/ex.cols/ex.split，默认缩放 1.25。

## 按读者要比较什么选方案
"""

ROUTES = [
    ("实体构造/作用路径+证据（image组合）", "mixed_columns_page"),
    ("多对象 × 多指标（排名、份额、两期、缺失）", "rank_table / scorecard"),
    ("两期/两状态变化（逐项）", "dumbbell_table / slope"),
    ("现状→目标 / 前后两态对照，中间写变化", "before_after"),
    ("排名谁升谁降（两期 / 多期）", "slope / bump"),
    ("只有本期值+目标（无序列）", "target_columns"),
    ("实际+目标+差/中/好区间；同行区间/中位数", "bullet / dot_range"),
    ("多面板同组对象，突出当期", "focus_panels"),
    ("同单位独立趋势/预测/情景", "trend_lines / fan"),
    ("多对象的趋势形状（同轴）；对同一基准谁超谁差", "small_multiples / baseline_panels"),
    ("可加分项总量/构成（面积用area_stack）", "stacked_columns"),
    ("年度柱实际vs预测 + 增速/CAGR", "forecast_columns"),
    ("变化由哪些因素贡献（从 0 起 / 只看变化）", "bridge / variance_bridge"),
    ("经营指标达成（红黄绿 / 迷你走势 / 差异条）", "kpi_scorecard / kpi_spark_table / variance_table"),
    ("实际 vs 预算/去年：逐月/区域/归因桥（IBCS）", "ibcs_columns / ibcs_bars / ibcs_bridge"),
    ("全年进度（累计 vs 预算）；周/月走势", "pace / wbr_trend"),
    ("对象 × 月份达成热力", "heat_matrix"),
    ("两指标关系 + 规模（象限/阈值）", "bubble_map"),
    ("集中度：少数几项占多数（二八）", "pareto / share_bars"),
    ("份额面积/规模×结构", "treemap / marimekko"),
    ("构成的一块或几块再拆开", "pie_of_pie"),
    ("山脊形态与峰值时点", "ridgeline"),
    ("利润池（宽=收入、高=利润率）", "profit_pool"),
    ("同期间同队列步骤转化/留存", "funnel"),
    ("守恒流向（预算/用户去向）", "flows"),
    ("里程碑；措施补回缺口", "roadmap / action_plan"),
    ("两图/表合起来证明标题（右侧拆解栏）", "chart_takeaway / table_panel"),
    ("左图一行/一根柱/一段在右图展开", "expand_row / expand_bar / expand_segment"),
    ("多图一页", "panel_pair / panel_trends / shared_time / shared_rows"),
    ("时间序列分阶段讲", "period_notes"),
    ("分布与区间（估计值±CI、热力矩阵）", "distribution_table"),
    ("多对象两期倍数（量级差异大）", "multiples_grid"),
    ("选项/路径/竞品多维对比", "scorecard"),
    ("风险；章节导航", "risk_register/risk_matrix/chapter_nav"),
    ("哪些假设会推翻结论", "sensitivity"),
    ("附录", "appendix"),
]

LAYOUT_ROUTES = [
    ("左图/左表 + 右侧 2–4 条结论（单图页默认）", "key_takeaways"),
    ("整体≤4份占比：图标网格", "icon_grid"),
    ("上方 2–4 个大数字 + 下方 1–2 张图", "kpi_charts_page"),
    ("图 + 要点便捷模板，可选参数", "diagram_page"),
    ("三栏模型/参数表 + 图标，逐行对齐", "columns_page"),
    ("四驱动：数字+解释+图（columns_page别名）", "four_columns"),
    ("1–4 栏任意位置：图片+图表/表格/解释，或上下堆叠", "mixed_columns_page"),
]

RECIPES = {}

RECIPES["rank_table"] = ("""## rank_table — 排名 / 份额 / 两期对比表（exa12 型）
适用：≥6 个对象，1–3 个数值列；需要排序、前 N 合计、合计行、口径不同的"其他"行。
版面：行标签右对齐 + Bar 列（灰底槽）+ 占比 Text 列 + 可选第二期 Bar 列 + 增速列；brackets 标前 N 合计；total 深色合计行。
主标注：前 N 合计括号（程序算）；颜色按一个分类维度（如利率档）或只给主角 accent，其余 main。
要点：数值大小差异悬殊时用 cumulative=True 让条依次排开（阶梯），条短时数值自动放到条前；"其他/未细分"行设 _style='muted'；
有决策主体时加一行"我方"（无实数写"我方（假设）"），Bar(color=) 给它 accent。
对象 >8 个：top_n(rows, "v", 6, keep=…) 留前 6 + 我方，其余并成一行 muted"其他（k 家）"，返回前 N 占比供括号标注。""",
"""rows = [dict(label=n, v=v) for n, v in [("南非", 26.4), ("埃及", 18.0), ("尼日利亚", 8.7), ("摩洛哥", 6.9),
        ("肯尼亚", 5.9), ("阿尔及利亚", 4.0), ("加纳", 3.1), ("突尼斯", 2.9), ("安哥拉", 2.5), ("科特迪瓦", 2.0)]]
rows, top = top_n(rows, "v", 6)
tot = sum(r["v"] for r in rows)
ex = Exhibit(w=880, h=330)
row_table(ex, ex.body, rows, [Label("label", align="end"), Bar("v", cumulative=True, fmt=lambda v: f"{v:.1f}"),
          Text(lambda r: f"{r['v'] / tot:.0%}", header="占比")],
          total=dict(label="合计", v=tot), brackets=[(0, 5, f"{top:.0%}", 2)])
""")

RECIPES["dumbbell_table"] = ("""## dumbbell_table — 现状→目标 / 两组对照（exa7 / exa10 型）
适用：同一组对象在两个状态或两个群体上的同口径值；差距本身就是论点。
版面：行标签（可加 level=0 分组头）+ 1–2 个 Dumbbell 面板共享行；第二面板（如另一技术/年份）并排，同尺度。
主标注：brackets 框住差距最大的几行写平均差距（程序算）；connector='arrow' 表示方向，base=True 灰底=已达到，connector='bar' 表示两组差距。
要点：按差距或目标值排序；labels="values" 标出两端数值，再加一列差距（程序算），否则读者读不出数；差距很小（<5% 量程）就改用 Text/Bar 列；图例颜色用与 series 相同的 ex.C 角色。""",
"""rows = [dict(label=l, now=a, fut=b) for l, a, b in [("市场情报", 28, 43), ("成本跟踪", 19, 46), ("定价", 18, 45),
        ("促销", 18, 45), ("折扣审批", 13, 41), ("续约", 12, 45)]]
rows.sort(key=lambda r: r["now"] - r["fut"])          # 按差距排序
k = sum(r["fut"] - r["now"] >= 25 for r in rows)      # 差距 ≥25 的行数（程序算）
avg = sum(r["fut"] - r["now"] for r in rows[:k]) / k
ex = Exhibit(w=880, h=330)
legend(ex, ex.w - 200, 12, [("现状", ex.C["main"], "dot"), ("1–3 年后", ex.C["accent"], "dot")])
body = (0, 24, ex.w, ex.h)
row_table(ex, body, rows, [Label("label", align="end"),
          Dumbbell([("now", "现状", ex.C["main"], "dot"), ("fut", "未来", ex.C["accent"], "dot")], domain=(0, 50),
                   ticks=[0, 10, 20, 30, 40, 50], connector="arrow", base=True, labels="values"),
          Text(lambda r: f"+{r['fut'] - r['now']}", header="差距", weight=700)],
          brackets=[(0, k - 1, f"{k} 项平均 +{avg:.0f}", 2)])
""")

RECIPES["focus_panels"] = ("""## focus_panels — 多面板突出当期（exa11 型）
适用：同一组对象在 2–4 个时期/情景下的区间或数值，要看"谁在哪个时期拉开差距"。
版面：分组头（level=0, valign='middle'）+ 每期一个 Dumbbell/Range 面板（sep=True 分隔，header_bold=True）；
每行代表 (对象, 时期)，面板用列级 focus 只给本期上色，其余期淡灰作对照。
主标注：最分化的一行旁 badge 写区间宽度是首期的倍数（程序算）；本期颜色由浅到深递进（light→second→main）。
要点：所有面板同尺度（domain 相同）；刻度放底部（ticks_pos='bottom'）。""",
"""rows = []
for seg, qs in [("整车", [(0, 20), (-15, 8), (12, 53)]), ("一级供应商", [(18, 21), (4, 8), (20, 34)]), ("材料", [(-1, 9), (-8, 3), (33, 82)])]:
    for p, (q1, q3) in enumerate(qs):
        rows.append(dict(seg=seg, p=p, q1=q1, q3=q3))
ex = Exhibit(w=880, h=340)
cols = [Label("seg", level=0, align="end", valign="middle", width=80)]
for k, (name, col) in enumerate([("2012–19", ex.C["light"]), ("2019–22", ex.C["second"]), ("2022–25", ex.C["main"])]):
    d = Dumbbell([("q1", "Q1", col, "ring"), ("q3", "Q3", col, "dot")], header=name, domain=(-20, 100), connector="line",
                 ticks=[0, 50, 100], ticks_pos="bottom", r=4.6, focus=(lambda kk: lambda r: r["p"] == kk)(k))
    d.header_bold, d.sep = True, k > 0
    cols.append(d)
t = row_table(ex, ex.body, rows, cols, rules=False, gap=24)
i = max(range(len(rows)), key=lambda j: rows[j]["q3"] - rows[j]["q1"])   # 最分化的 (对象, 时期)
r0 = next(j for j, r in enumerate(rows) if r["seg"] == rows[i]["seg"] and r["p"] == 0)
w, w0 = rows[i]["q3"] - rows[i]["q1"], rows[r0]["q3"] - rows[r0]["q1"]
c, cy = cols[rows[i]["p"] + 1], t["top"] + (i + 0.5) * t["row_h"]
badge(ex, c._sx(rows[i]["q3"]) + 20, cy, f"{w / w0:.0f}×", fill=ex.C["accent"], size=10.5)   # 四分位差是首期的倍数
""")

RECIPES["trend_lines"] = ("""## trend_lines — 趋势线（含预测与区间）
适用：连续时间序列（≥5 个时点），1–4 条线；预测段需与实际区分。
版面：lines() 主图（右侧直接标线名+末值，不用图例）；图区右侧可留给 key_takeaways 栏或另一个图区（donut / share_bars）。
主标注：forecast_from 阴影区 + 虚线；lo/hi 给预测区间；band 标特殊时期、ax.ref_y 标目标/均值线；callout（leader 引线）指向拐点/新高并写出程序算的增速。
要点：年份轴自动按整数显示；focus 只突出主角线，其余灰；线多于 4 条就改用 row_table 或小多图。""",
"""X = list(range(2019, 2029))
ex = Exhibit(w=580, h=330)
ax = lines(ex, ex.body, X, [{"name": "移动", "y": [68, 86, 93, 92, 92, 102, 113, 118, 122, 126],
                             "lo": [None] * 7 + [114, 116, 118], "hi": [None] * 7 + [122, 128, 134]},
                            {"name": "PC", "y": [37, 40, 37, 38, 38, 39, 44, 47, 50, 53]}],
           xticks=[2019, 2021, 2023, 2025, 2027], forecast_from=2025)
band(ax, 2020, 2022, "疫情期")
callout(ex, (ax.sx(2025), ax.sy(44)), "PC 2025 年 +12%，创历史新高", width=120)
""")

RECIPES["stacked_columns"] = ("""## stacked_columns — 总量 + 构成（堆叠 / 100% 柱）
适用：少量时点（≤8）或类别，既看总量又看构成；只看构成用 stack='percent'。
版面：columns(stack='stack', totals=True) 主图；或主图总量 + 侧栏 percent 构成。
主标注：总量图 cagr=(i, j)；两图间 relate(kind="arrow", text=论点系列占比变化 pp)；构成里只给论点系列 accent。
要点：系列 ≤5；段太小自动不写数值；堆叠自动由重到轻（合计最大的系列在最下、颜色最深），order="given" 保留传入顺序。""",
"""ex = Exhibit(w=880, h=330)
main, side = ex.split(0.42, gap=64)
S = [("移动", [92, 102, 113], ex.C["main"]), ("PC", [38, 39, 44], ex.C["second"]), ("主机", [44, 44, 45], ex.C["light"])]
with ex.panel(main):
    r = columns(ex, main, ["2023", "2024", "2025"], S, stack="stack", totals=True, cagr=(0, 2))   # 总量 CAGR
with ex.panel(side):
    columns(ex, side, ["2023", "2024", "2025"], S, stack="percent", legend_items=False)
sh = [S[0][1][i] / r["values"][i] for i in (0, 2)]
relate(ex, main, side, kind="arrow", text=[f"{sh[1] - sh[0]:+.0%}".replace("%", "pp"), "移动占比"])
""")

RECIPES["forecast_columns"] = ("""## forecast_columns — 年度柱：实际 vs 预测 + 增速论证（游戏 P4 型）
适用：一个总量指标的年度序列，含预测年；论点是某年转折或预测期 CAGR。
版面：columns(forecast_from=…) 主图（预测柱自动浅色 + 虚线分界 + 实绩/预测）；右侧可再放一个 bridge 图区解释增量来源。
主标注（think-cell 式，columns 参数直接画、百分比自动算）：yoy=k 转折年同比；cagr=(i, j) 预测期 CAGR；diff=(i, j) 首尾总差；target=(值, "目标") 目标线；特殊时期 band(r["ax"], i, j, "原因")（虚线框 + 框顶标签）。
同一组年份的第二个指标（利润率 / 份额 / 均价）放轴下数据行 rows=[(名, 值列表, fmt)]，不另开小图、不混轴。
要点：预测数值由 CAGR 程序推算，脚注写明方法。""",
"""Y = ["2020", "2021", "2022", "2023", "2024", "2025", "2026E", "2027E"]
V = [178, 193, 184, 188, 185, 202, 212, 223]
ex = Exhibit(w=560, h=330)
r = columns(ex, ex.body, Y, [("收入", V, ex.C["main"])], forecast_from=6,
            yoy=4, cagr=(5, 7),           # 2024→2025 同比箭头 + 2025→2027E CAGR 椭圆（百分比自动算）
            note=("2022", "疫后补库，增速最快的一年"),   # 说话框：这个数说明什么
            rows=[("毛利率", [41.2, 42.0, 39.5, 40.1, 40.8, 42.3, 42.9, 43.4], lambda v: f"{v:.1f}%")])   # 轴下数据行
band(r["ax"], 1, 2, "疫情扰动", axis="x")    # 特殊时期：虚线框 + 框顶标签
""")

RECIPES["bridge"] = ("""## bridge — 增量桥 / 瀑布
适用：起点到终点的变化可加和地拆成若干因素（平台、地区、价量）。
版面：Axes.fit + waterfall；常作窄图区放在趋势或年度柱旁边。纵轴从 0 起（截断会夸大增量）；增量相对总量太小时把桥画成"只看变化"——起点柱写数值、各举措柱从 0 起表示增量。
主标注：各因素数值 + 占增量比重（waterfall(..., share=True) 自动算）；增项统一 accent、减项统一 neg（只给部分步骤第 4 项颜色会被忽略）；要突出最大贡献因素就给该步第 4 项颜色并传 focus='因素名'。
要点：终点必须等于起点+各项之和（程序校验）。""",
"""ex = Exhibit(w=300, h=330)
steps = [("total", "2024", 184.8), ("delta", "移动", 10.9), ("delta", "PC", 4.7), ("delta", "主机", 1.2), ("total", "2025", 201.6)]
ax = Axes.fit(ex, ex.body, 210, ticks=[0, 70, 140, 210])
ax.grid()
bands = ax.bands(len(steps), pad=0.45)
cents = [b[0] + b[1] / 2 for b in bands]
waterfall(ax, cents, bands[0][1], steps, share=True)
ax.xlabels(cents, [s[1] for s in steps])
""")

RECIPES["bubble_map"] = ("""## bubble_map — 两指标关系 + 规模（游戏 P9/P10、exa9 型）
适用：每个对象有两个连续指标（+可选规模），论点是"谁在哪个象限/谁偏离群体"。
版面：NAxes.fit 主图（band_rows 给缺失对象留灰带）+ bubbles；需要侧栏时图区收窄，右侧用 key_takeaways 写要点（或大数字），或在图区内再放一个 row_table 排名。
主标注：ref_x/ref_y 阈值线或 quadrants(ax, x, y, labels=…) 四象限；相关性论点用 trend(ax, xs, ys) 回归线；dim_arrow+badge 标两点差距倍数；callout（leader 引线）1–2 条解释异常点；size_legend(..., ax=ax) 把气泡面积图例放在图上方标题行（不放图内）。
气泡多（≥6 个）且扎堆：NAxes.fit(..., key_w=110) 给图右侧留颜色图例位，bubbles 自动给扎堆的气泡各一种颜色、名称列在右侧（不再逐个贴标签挤在一起）。
要点：缺 y 的对象进 missing_band，不画在 0；口径不同的点在标签加上标并写脚注；标签全部自动放置。""",
"""P = [("腾讯", 32, 33, 774), ("世纪华通", 61, 95, 222), ("三七", 34, 8, 54), ("吉比特", 15, 86, 9)]
ex = Exhibit(w=600, h=340)
with ex.panel(ex.body):
    ax = NAxes.fit(ex, ex.body, (0, 70), (0, 120), xticks=[0, 20, 40, 60, 70], yticks=[0, 40, 80, 120], band_rows=1)
    ax.frame(xtitle="海外收入占比，%", ytitle="海外同比，%")
    ax.ref_x(50, "海外收入过半")
    xy = bubbles(ax, [dict(x=a, y=b, size=s, label=n, color=ex.C["accent"] if n == "世纪华通" else ex.C["main"]) for n, a, b, s in P])
    callout(ex, xy[3][:2], "增速 86% 但基数仅 9 亿", width=110, target_r=xy[3][2])
    missing_band(ex, ax, [{"x": 10, "label": "网易（增速未披露）", "marker": "hollow"}], label="未披露")
    size_legend(ex, 0, 0, [700, 100], ex.bubble_to_r, label_lines=["气泡=收入，亿元"], ax=ax)   # 标题行，不占图内
""")

RECIPES["share_bars"] = ("""## share_bars — 构成 / 集中度（单一整体 ≤4 部分优先用整页版式 icon_grid）
适用：一个整体的构成，论点是"前几项合计占多少"。
版面：hstack100 横向 100% 条（可多条上下对照，图区可以很矮）；或 vstack100 竖条作窄图区；donut 只在 ≤5 项且需中心总数时用。
主标注：span_bracket 框住前 N 项并写合计（程序算）；前 N 用 main，其余 context/dim。
要点：窄段标签自动外置错层；不要用饼图比较多个整体。""",
"""ex = Exhibit(w=880, h=130)
x0, y0, x1, y1 = ex.body
segs = [("美国", 32, ex.C["main"], "#FFFFFF"), ("日本", 16, ex.C["main"], "#FFFFFF"), ("韩国", 7.5, ex.C["main"], "#FFFFFF"),
        ("德英法", 8.8, ex.C["context"], ex.C["ink"]), ("其他", 35.7, ex.C["track"], ex.C["ink"])]
sp = hstack100(ex, x0, y0 + 22, x1 - x0, 46, segs)
span_bracket(ex, sp[0][0], sp[2][1], y0 + 78, "美日韩合计 56%", up=False)
""")

RECIPES["marimekko"] = ("""## marimekko — 规模 × 内部结构
适用：多个市场/客群，既比规模（列宽）又比内部构成（块高）。
版面：marimekko 占满主图；图例在上；列顶写规模。
主标注：图下 span_bracket 框住论点列，写"日韩 RPG 占全球 64%"（程序算）；论点系列放在 accent 位（colors 顺序）。
要点：列 ≤8、段 ≤5；小块自动不写数值。value_fmt 收到的是该段占本列的百分比（0–100），不是原值；标注的列位置一律取返回值 r["列名"] = (左, 右)。""",
"""M = [("美国", 320, [50, 20, 15, 15]), ("日本", 160, [15, 10, 55, 20]), ("韩国", 75, [20, 12, 50, 18]), ("其他", 110, [35, 25, 20, 20])]
ex = Exhibit(w=880, h=330)
x0, y0, x1, y1 = ex.body
r = marimekko(ex, (x0, y0, x1, y1 - 30), M, ["SLG", "射击", "RPG", "其他"], width_fmt=lambda v: f"{v:.0f}亿")
rpg = {n: t * s[2] / sum(s) for n, t, s in M}                  # 各市场 RPG 规模（程序算）
jk = (rpg["日本"] + rpg["韩国"]) / sum(rpg.values())
span_bracket(ex, r["日本"][0], r["韩国"][1], y1 - 28, f"日韩 RPG 占全球 RPG 的 {jk:.0%}", up=False)   # 列位置用返回值，不自己算
""")

RECIPES["flows"] = ("""## flows — 守恒流向（桑基）
适用：2–4 个阶段的守恒流量（预算、用户、收入来源→去向）；每层合计相等或损耗显式列出。
版面：sankey 图区约占页宽 60%；右侧 key_takeaways 写 2–3 条要点或放一个小 row_table 图区。
主标注：focus 只给论点路径上色；论点带中点 badge 写它占目标节点的比重（sankey 返回节点 x/y/h，程序算）。
要点：节点 ≤12；链接按来源色；损耗作为单独节点而不是省略。""",
"""links = [("rd", "own", 18), ("rd", "live", 12), ("own", "os", 13), ("own", "cn", 5), ("live", "os", 4), ("live", "cn", 8)]
ex = Exhibit(w=600, h=330)
N = sankey(ex, ex.body, [{"id": "rd", "label": "研发", "stage": 0}, {"id": "own", "label": "自研精品", "stage": 1},
                         {"id": "live", "label": "长线运营", "stage": 1}, {"id": "os", "label": "海外", "stage": 2},
                         {"id": "cn", "label": "国内", "stage": 2}], links,
           focus=lambda l: l[1] in ("own", "os") and l[0] in ("rd", "own"))
b = N["os"]                                    # 论点：海外收入主要来自自研精品（占比程序算）
v = next(x for s, d, x in links if (s, d) == ("own", "os"))
a = N["own"]
bx, by = (a["x"] + 12 + b["x"]) / 2, (a["y"] + b["y"]) / 2 + a["h"] * v / a["val"] / 2   # 论点带的中点
badge(ex, bx, by, f"占海外 {v / b['val']:.0%}", fill=ex.C["accent"], size=10.5)
""")

RECIPES["roadmap"] = ("""## roadmap — 路线图（举措 × 时间 + 目标与触发条件）
适用：建议页的分阶段计划；替代"三栏小字"路线图页。
版面：row_table 一行一个举措：Label + Range 甘特条（起止年，同一 Range 列）+ Text 列"投入"（来自 plan.py）+ Text 列"里程碑 KPI / 触发条件"（加码或止损的量化阈值）；图区占满宽度。
主标注：主推举措 focus 高亮；Range 的 ref 画"今天"竖线；检查点 diamond + tag 写 KPI（Range._sx 定位）；total 合计投入。
要点：KPI 写成可检验的数（"2027 年售后占比 ≥35%"），不写"能力成型"；触发阈值不能是已达到的现状；投入合计与目标桥/执行摘要一致。Range 甘特条只给有明确起止（计划 / 公告日期）的举措；投资观点、跟踪方向这类没有起止的行不画条，改成 Text 列"时间窗 / 检查点"（或 timeline 只画时点），不让条长暗示持续时间。""",
"""rows = [dict(label="售后与二手车", s=2026.0, e=2028.9, capex=3.0, kpi="2027 售后占比 ≥35%；低于 28% 暂停扩店"),
        dict(label="新势力交付服务", s=2026.5, e=2028.5, capex=1.8, kpi="交付中心单店年交付 ≥3,000 台"),
        dict(label="收缩燃油品牌", s=2026.0, e=2027.5, capex=-0.6, kpi="关停 12 店；单店亏损 >200 万即退出"),
        dict(label="汽车金融", s=2027.0, e=2028.9, capex=0.5, kpi="渗透率 ≥45%，不良率 ≤1.5%")]
ex = Exhibit(w=880, h=330)   # h = f.bottom − f.top：行高按图区自动铺满，不传 max_row_h
gantt = Range("s", "e", domain=(2026, 2029), ticks=[2026, 2027, 2028, 2029], tick_fmt=lambda v: f"{v:.0f}", ref=2026.8,
              bar_h=0.36, focus=lambda r: r["label"] == "售后与二手车")
t = row_table(ex, ex.body, rows, [Label("label", weight=700), gantt,
              Text(lambda r: f"{r['capex']:+.1f} 亿".replace("-", "−"), header="投入", width=60),
              Text(lambda r: r["kpi"], header="里程碑 KPI / 触发条件", width=300, align="start")],
              total=dict(label="合计", s=None, e=None, capex=sum(r["capex"] for r in rows), kpi=""))
r0 = rows[0]                                                     # 主推举措的检查点：Range 刻度上画菱形 + 引线注
x, cy = gantt._sx(2027.5), t["y"][r0["label"]]
diamond(ex, x, cy, 6, fill=ex.C["accent"])
callout(ex, (x, cy), f"{r0['kpi'].split('；')[0]} 检查点", width=200, target_r=6, prefer=("N", "S"), style="tag")
""")

RECIPES["distribution_table"] = ("""## distribution_table — 分布 / 区间 / 热力矩阵
适用：各组的分布（Box：最小/四分位/中位/最大）、估计值±CI（Range point=）、多指标强弱矩阵（Heat 多列）。
版面：row_table 共享行：Label + Box 或 Range 或若干 Heat 列；可与 Text 列混排。
主标注：对照组中位数虚线 + 论点组旁 tag 写差几个月（Box._sx 定位，程序算）；Range 用 ref 参考线；论点组 accent。
要点：只用来源报告的分位数/区间，不从均值反推分布；Heat 列 mid= 用于正负发散配色。""",
"""rows = [dict(label="SLG", mn=14, q1=18, md=22, q3=27, mx=36, a=72, b=65), dict(label="RPG", mn=18, q1=24, md=30, q3=36, mx=48, a=55, b=61),
        dict(label="射击", mn=20, q1=28, md=34, q3=40, mx=55, a=40, b=38)]
ex = Exhibit(w=880, h=200)
box = Box(("mn", "q1", "md", "q3", "mx"), header="研发周期，月", domain=(0, 60), ticks=[0, 20, 40, 60],
          color=lambda r: ex.C["accent"] if r["label"] == "SLG" else ex.C["main"])
t = row_table(ex, ex.body, rows, [Label("label"), box, Heat("a", header="品质"), Heat("b", header="留存")])
lo, hi = min(rows, key=lambda r: r["md"]), max(rows, key=lambda r: r["md"])
y0, y1 = t["top"], t["top"] + len(rows) * t["row_h"]
ex.line(box._sx(hi["md"]), y0, box._sx(hi["md"]), y1, stroke=ex.C["accent"], width=1, dash="3,3", tag="ref")   # 最慢组中位数参考线
callout(ex, (box._sx(lo["mx"]) + 24, t["y"][lo["label"]]), f"中位数比{hi['label']}短 {hi['md'] - lo['md']} 个月", width=160,
        style="tag", prefer=("E",))
""")

RECIPES["multiples_grid"] = ("""## multiples_grid — 两期倍数小多图（exa1 型）
适用：多个对象各自两期值，量级差异大，论点是"谁翻倍"。
版面：一大（最大对象，单独尺度）+ 3×N 同轴小多图（每行一个尺度）；每格两根柱：基期 main、本期 second（预测部分 light）。
主标注：每格上方 badge 写倍数（程序算）；最大对象用 dim_arrow+badge，倍数含义写在 XML 文字栏。
要点：同一行小多图共用纵轴；对象名放柱下，过长自动换行。""",
"""D = [("航天", 16, 190), ("生命科学", 101, 128), ("网络安全", 78, 126), ("出行", 63, 75)]
ex = Exhibit(w=880, h=330)
x0, y0, x1, y1 = ex.body
cw = (x1 - x0) / len(D)
for i, (n, a, b) in enumerate(D):
    ax = Axes.fit(ex, (x0 + i * cw + 6, y0 + 52, x0 + (i + 1) * cw - 6, y1), 200, ticks=[0, 100, 200], left=30 if i == 0 else 4)
    ax.grid(labels=i == 0)
    mid = ax.x + ax.w / 2
    stacked_bar(ax, mid - 24, 20, [(a, ex.C["main"])]); stacked_bar(ax, mid + 4, 20, [(b, ex.C["second"])])
    badge(ex, mid, y0 + 26, f"{b / a:.1f}×", size=10.5)
    ax.xlabels([mid], [n])
""")

RECIPES["sensitivity"] = ("""## sensitivity — 敏感性龙卷风（选项测算页的配套）
适用：已在假设表里算出选项的结果（NPV、IRR、回本年数、三年利润）后，回答"哪几个假设会推翻结论"。
版面：左侧 XML 写假设表（基准值与上下限）或结论要点，右侧 tornado 图区；也可上方测算结果条 + 下方龙卷风。
主标注：门槛线（threshold=）+ 最危险驱动条下 span_bracket 写下行幅度与剩余安全边际（tornado 返回 sx）；XML 要点点名。
要点：每个结果都由同一个函数从假设表算出（改一个假设重算一次），不手填；上下限写在条旁括号里。""",
"""def npv(price=1.0, util=0.75, capex=40):
    return round(-capex + sum((120 * util * price - 55) * 0.62 / 1.08 ** t for t in range(1, 6)), 1)
base = npv()
rows = [("电芯价格", "−15%", npv(price=0.85), "+10%", npv(price=1.1)),
        ("产能利用率", "60%", npv(util=0.6), "85%", npv(util=0.85)),
        ("单 GWh 投资", "+25%", npv(capex=50), "−15%", npv(capex=34))]
ex = Exhibit(w=600, h=300)
sx = tornado(ex, ex.body, base, rows, base_label="基准 NPV", value_fmt=lambda v: f"{v:.0f}", threshold=0, threshold_label="NPV=0")
worst = min(rows, key=lambda r: min(r[2], r[4]))                     # 最接近门槛的驱动（程序找）
k = sorted(rows, key=lambda r: -abs(r[4] - r[2])).index(worst)       # tornado 按幅度降序排行
x0, y0, x1, y1 = ex.body
cy = y0 + 30 + (k + 0.5) * min((y1 - y0 - 50) / len(rows), 80)       # 与 tornado 同一行高
lo = min(worst[2], worst[4])
span_bracket(ex, sx(lo), sx(base), cy + 24, f"NPV −{base - lo:.0f}，仅余 {lo:.0f}", up=False,
             color=ex.C["accent"])                                   # 最危险驱动的下行幅度与剩余安全边际
""")


LAYOUT = {'scorecard': ('图区占满宽度，高度按行数（每行约 50）；上方 XML 写结论标题与评分口径，下方 XML 写推荐理由 1–2 句。', 40, 130), 'risk_matrix': ('图区 w≈600 左侧；右侧 XML 写各象限应对要点（≤4 条）。', 40, 118), 'risk_register': ('图区占满宽度（h≈300–340），表下一行图例；不另加右栏。', 40, 118), 'rank_table': ("图区 w≈880 h≈330，放在 x=40 y≈118；标题与'指标，单位'副标题在上方 XML，脚注/来源在底部 XML。", 40, 118), 'dumbbell_table': ('图区占满宽度（w≈880 h≈330, x=40 y≈118）；图例可画在图区顶部，也可写成 XML。', 40, 118), 'focus_panels': ('图区占满宽度并略高（h≈340）；面板标题由列 header 画在图区内。', 40, 112), 'trend_lines': ('图区 w≈580 放左侧（x=40 y≈118）；右侧 key_takeaways 写 2–3 条要点（或 KPI 大数字）。', 40, 118), 'stacked_columns': ('图区占满宽度；图区内左右两块分别是总量与构成。', 40, 118), 'forecast_columns': ('图区 w≈560 左侧；右侧可放 bridge 图区（另一个 Exhibit，x≈640）或 key_takeaways。', 40, 118), 'bridge': ('窄图区（w≈300）常放在主图右侧 x≈640；也可单独成页加宽。', 640, 118), 'bubble_map': ('图区 w≈600 左侧；右侧 x≈680 起用 XML 写衬线大数字（如 97%）与一句解释，或再放一个 row_table 图区。', 40, 118), 'share_bars': ('一条 100% 横条只占约 1/3 高度：左栏要么堆 2–3 条（不同年份 / 不同对象的构成，上下对比），要么上面横条、下面再放一张支撑图（如各段的增速柱 / 趋势线），用满 f.top–f.bottom，不留下半页空白。', 40, 118), 'marimekko': ('图区占满宽度（h≈330）。', 40, 118), 'flows': ('图区 w≈600 左侧；右侧 key_takeaways 写 2–3 条要点。', 40, 118), 'roadmap': ('图区占满宽度（h≈220–280），上方标题写分阶段目标；不另做三栏小字。', 40, 130), 'distribution_table': ('图区占满宽度，高度按行数（每行约 40）。', 40, 130), 'multiples_grid': ('图区占满宽度；每格徽章画在图区内。', 40, 118), 'appendix': ('左右两栏 text_table：左为关键口径与测算假设两个表，右为主要来源分组表；不画图区。', 40, 110), 'slope': ('图区 w≈560 左侧 + 右侧 key_takeaways，或占满宽度。', 40, 118), 'bullet': ('图区占满宽度或左侧 60% + 右侧 key_takeaways。', 40, 118), 'pareto': ('图区 w≈560 左侧 + 右侧 key_takeaways。', 40, 118), 'small_multiples': ('图区占满宽度。', 40, 118), 'baseline_panels': ('图区占满宽度（或左侧 + 右栏 key_takeaways）；frame 副标题写指标与基准口径。', 40, 118), 'fan': ('图区 w≈560 左侧 + 右侧 key_takeaways 写情景假设。', 40, 118), 'treemap': ('图区 w≈560 左侧 + 右侧 key_takeaways。', 40, 118), 'chart_takeaway': ('图区左 2/3，右侧竖大括号指向拆解栏；结论只写在页标题。', 40, 118), 'table_panel': ('表左、虚线结论栏右。', 40, 118), 'expand_row': ('图区占满宽度，frame 不传副标题（面板标题画在图区内）。', 40, 100), 'expand_bar': ('图区占满宽度，frame 不传副标题。', 40, 100), 'expand_segment': ('图区占满宽度，frame 不传副标题。', 40, 100), 'period_notes': ('图区占满宽度，上方 64px 放时段说明。', 40, 182), 'panel_pair': ('两栏，每栏顶部一句结论。', 40, 190), 'panel_trends': ('三栏，每栏顶部一句结论。', 40, 190), 'shared_time': ('图区占满宽度，左侧 120px 放两行面板标签。', 40, 118), 'shared_rows': ('图区占满宽度。', 40, 118), 'sensitivity': ('图区 w≈600 放右侧（x≈320 y≈118）；左侧 XML 写假设表或 2–3 条结论。', 320, 118)}


RECIPES["scorecard"] = ("""## scorecard — 评分矩阵 / 选项对比（替代文字页）
适用：战略路径、业务选项、竞品画像等"每个对象若干维度"的判断；原本会写成三栏文字卡或逐页介绍。
版面：row_table 一行一个对象；真实数值列（NPV、回本、投入）+ 每个维度的 Harvey 球（定性强弱一眼可读，不写裸数字）+ 加权分 + 一句理由；表头写权重。
主标注：按加权分排序，focus + badge"推荐"给第一名，判断列写领先分差（程序算）；预算/推荐顺序必须等于这里的排名。
要点：分数一律由 score_options 从 plan.py 的原始数值按规则算出（不手填 1–5）；返回的 rule 文本放进 frame 的 notes。""",
"""opts = [dict(label="零售财富", npv=18, payback=4.5, risk=2, why="轻资本、复利强"),
        dict(label="小微经营", npv=11, payback=3.2, risk=4, why="定价权高，信用成本波动"),
        dict(label="对公综合", npv=6, payback=6.0, risk=3, why="规模大、资本消耗重")]
rows, rule = score_options(opts, [("NPV", "npv", 0.4, "high"), ("回本", "payback", 0.3, ("low", [4, 5, 6, 7])),
                                  ("风险", "risk", 0.3, "low")])
rows[0]["why"] += f"；领先 {rows[0]['score'] - rows[1]['score']:.1f} 分"   # 领先幅度（程序算）
ex = Exhibit(w=880, h=210)
t = row_table(ex, ex.body, rows, [Label("label", weight=700, width=96), Bar("npv", header="NPV，亿元", track=False),
              Text(lambda r: f"{r['payback']:.1f}", header="回本，年"), Harvey("s_npv", header="NPV\\n权重 40%", scale=(1, 5)),
              Harvey("s_payback", header="回本\\n权重 30%", scale=(1, 5)), Harvey("s_risk", header="风险\\n权重 30%", scale=(1, 5)),
              Text(lambda r: f"{r['score']:.1f}", header="加权分", weight=700, width=48), Text(lambda r: r["why"], header="判断", width=150, align="start")],
              focus=lambda r: r["rank"] == 1)
badge(ex, tw(rows[0]["label"], 11, True) + 24, t["y"][rows[0]["label"]], "推荐", fill=ex.C["accent"], size=10)   # 第一名 = 推荐
""")

RECIPES["risk_matrix"] = ("""## risk_matrix — 两维定位矩阵（风险/机会/选项）
适用：多个对象按两个**可度量**的维度定位（概率 % × 影响金额、市场增速 × 份额）。可能性 / 影响只是团队打分（高中低、1–5 分）时不用本图，改 risk_register（档位表）。
版面：图区 w≈520 左侧 + 右侧 XML points() 列出"① 风险 — 触发信号 / 应对"；NAxes 两轴 + quadrants() 分四象限（阈值线 + 浅底 + 象限名）。
主标注：bubbles(numbered=True) 只画编号（标签不会互压），右上象限对象用 accent，其余 context；默认等大点——只有每项都有真实金额（影响额、敞口）时才传 size= 并画 size_legend，评分/关注度这类定性量不做气泡大小。
要点：评分方法写在脚注；对象 ≤ 8 个，气泡编号与右侧列表一一对应（数量相同）；同分对象自动错开；风险的概率/影响与正文结论一致（正在发生的事实不标"低概率"）。""",
"""R = [("监管收紧", 35, 42), ("买量成本上升", 60, 18), ("汇率波动", 45, 9), ("人才流失", 20, 12), ("技术迭代", 15, 30)]   # 概率 %、影响 亿元
ex = Exhibit(w=520, h=330)
ax = NAxes.fit(ex, ex.body, (0, 80), (0, 50), xticks=[0, 20, 40, 60, 80], yticks=[0, 10, 20, 30, 40, 50])
ax.frame(xtitle="发生概率，%", ytitle="利润影响，亿元")
quadrants(ax, 40, 20, labels=dict(TR="优先应对", TL="预案", BR="监测", BL="接受"), shade="TR")
bubbles(ax, [dict(x=a, y=b, color=ex.C["accent"] if a > 40 and b > 20 else ex.C["context"]) for n, a, b in R],
        r_max=11, r_min=11, numbered=True)   # 等大点；有第三个真实数值才加 size= + size_legend
legend(ex, ax.x + 8, ax.y + 12, [("需优先应对", ex.C["accent"], "dot"), ("其他", ex.C["context"], "dot")])
side, _ = points(580, 130, 340, [(f"{n}：", "触发信号 / 应对一句") for n, *_ in R], numbered=True)
""")



RECIPES["risk_register"] = ("""## risk_register — 风险登记表（定性的可能性 × 影响，档位不打分）
适用：风险 / 不确定性 / 跟踪变量的"可能性、影响"是团队判断（高 / 中 / 低），不是测出来的数——不画气泡坐标（会被读成精确数值）。
版面：图区占满宽度；一行一个风险，按优先级排（可能性 × 影响 高的在上）；列 = 风险 | 可能性 | 影响 | 触发信号（可验证的阈值） | 应对 / 对结论的影响。
主标注：Level 列把"低 / 中低 / 中 / 中高 / 高"画成 Harvey 球（不写 1–5 分）；focus= 高亮需优先应对的行（其余变浅）；表下一行图例写深浅含义和"球越满 = 档位越高"。
要点：触发信号写成可证伪的数字阈值（"中标价 < 0.35 元/Wh"），不是形容词；≤6 行，多了拆页或并项。只有每项都有真实金额 / 概率时才用 risk_matrix 气泡图。""",
"""R = [dict(label="锂价剧烈波动", p="高", i="高", sig="中枢跌破 8 万元/吨", act="重估盈利预测"),
     dict(label="海外政策 / 关税反复", p="高", i="中高", sig="欧洲户储补库不及预期", act="下调海外出货"),
     dict(label="利用率回升不及预期", p="中", i="中高", sig="季度利用率 < 60%", act="价格战延长"),
     dict(label="电芯涨价不及预期", p="中", i="中", sig="Q4 中标价 < 0.35 元/Wh", act="涨价逻辑证伪")]
ex = Exhibit(w=880, h=330)
row_table(ex, ex.body, R, [Label("label", header="风险", weight=700), Level("p", header="可能性"), Level("i", header="影响"),
                            Note("sig", header="触发信号", width=230), Note("act", header="应对", width=200)],
          focus=[0, 1], legend_items=[("需优先应对", ex.C["main"], "dot"), ("持续跟踪", ex.C["dim"], "dot"), ("球越满 = 档位越高（低 / 中 / 中高 / 高）", "#FFFFFF", "dot")])
""")


RECIPES["appendix"] = ("""## appendix — 附录（服务于被追问：测算明细 + 原始数据 + 口径来源，可 2–4 页）
测算明细（假设表、逐年测算、敏感性明细）与原始数据表（对标原始数值、口径换算）各一页表格；最后一页口径与来源，三块：
① 关键口径：指标 | 定义 | 适用页　② 测算假设：假设 | 取值 | 依据（用户给定 / 团队估算 + 来源）| 敏感性见　③ 主要来源：按类别分组（行业机构、公司披露、监管与统计、第三方研究），每条"机构《报告/数据》（年份）"/"Org, Report (year)"，≤15 条。
要点：不写网址、不写内部文件名（research/*.md、plan.py）；需要可追溯就把机构名做成 XML 超链接或放 <note>。各页 frame(source=[...]) 用同一批来源名（SRC 元组带链接即可点击）；不写"团队分析"一类来源，派生算法写进 notes。""",
"""f = frame("附录：口径、假设与来源", source=["公司年报（2025）"], page=14, section="附录")
H = f.bottom - f.top
t1, y1 = text_table(f.left, f.top, 420, ["指标", "定义", "适用页"], [["国产化率", "国产设备金额 ÷ 当年设备采购额", "P5、P7"],
                    ["毛利率", "(营收 − 营业成本) ÷ 营收", "P8"]], widths=[1, 2.4, 0.8], h=H / 2 - 10)
t2, _ = text_table(f.left, y1 + 18, 420, ["假设", "取值", "依据"], [["2026–28 资本开支增速", "8%", "SEMI 预测"]], widths=[1.6, 0.6, 1.2])
t3, _ = text_table(500, f.top, 420, ["类别", "来源"], [["行业机构", "SEMI《World Fab Forecast》（2025）"], ["公司披露", "各公司年报（2024）"]],
                   widths=[0.7, 2.3], h=H)
ex = Exhibit(w=10, h=10)   # 占位，不发布：附录是纯文字表，无论证标注；f.publish(t1, t2, t3, deck=..., page=14, cwd=...)
""")


RECIPES["chapter_nav"] = ("""## chapter_nav — 章节导航页（每章第一页之前一页，复用目录版式）
适用：章数 ≥4 的研究稿，plan 在每章开头排一行 dict(p=N, recipe="chapter_nav", title=<章名>, chart=False)，SECTIONS 的章起始页就是这页。
版面：contents(f, SECTIONS, PAGES, descs, current=<第几章>) 整页出图：左侧深色主色块写 PART 0N、大号章号、章名、本章一句结论；
右侧列出全部章节，当前章浅底 + 强调色竖条 + 强调色编号，其余章变灰。不写正文、不画图，几秒做完。
descs 与目录页同一份（{章名: 一句带数字的结论}），由 plan.py 提供，目录页与各导航页一致。""",
"""SECTIONS = {2: "目录", 3: "执行摘要", 4: "一、外部市场", 8: "二、竞争格局", 10: "三、进入模式", 14: "四、推荐方案"}   # plan.py
CHAPTER_DESCS = {"三、进入模式": "加盟 IRR 约 28%、回本 2–3 年"}                                             # plan.py
f = frame("进入模式", page=10, section=SECTIONS, note="第三章：进入模式。")
body = contents(f, SECTIONS, [], descs=CHAPTER_DESCS, current=3, deck_name="东南亚市场进入可行性研究")
# f.publish(body, deck=DECK, page=10, cwd=CWD)
ex = Exhibit(w=10, h=10)   # 占位，不发布：文字页无图区
""")
LAYOUT["chapter_nav"] = ("整页由 contents(current=) 画，frame 只取 note 与 logo。", 40, 110)



RECIPES["slope"] = ("""## slope — 斜率图（两期 / 两情景，谁升谁降）
适用：5–12 个对象在两个时点的数值或排名（rank=True），论点是"位次/份额此消彼长"。比哑铃更突出交叉与方向。
版面：图区 w≈520–600 左侧，右侧 key_takeaways 写 2–3 条要点；或占满宽度。
主标注：程序找最大升/降两条线 focus，线上 badge 写变化 pp（slope 返回 sy, xl, xr）；两端直接标"名称 值"。""",
"""D = [("海底捞", 20.5, 24.1), ("呷哺", 10.2, 6.8), ("巴奴", 12.0, 16.5), ("楠火锅", 8.0, 11.2), ("小龙坎", 9.5, 8.1)]
D.sort(key=lambda t: -t[2])                    # 按终值排序：第一条论点线（最大升）取 accent
up, dn = max(D, key=lambda t: t[2] - t[1]), min(D, key=lambda t: t[2] - t[1])     # 最大升 / 最大降（程序找）
ex = Exhibit(w=560, h=330)
sy, xl, xr = slope(ex, ex.body, D, "2023", "2025", value_fmt=lambda v: f"{v:.1f}%", focus=lambda n: n in (up[0], dn[0]))
for n, a, b in (up, dn):                       # 线上放徽章：变化 pp
    badge(ex, xl + (xr - xl) * 0.6, sy(a) + (sy(b) - sy(a)) * 0.6, f"{b - a:+.1f}pp".replace("-", "−"), size=10,
          fill=ex.C["accent"] if b > a else ex.C["neg"])
""")

RECIPES["target_columns"] = ("""## target_columns — 实绩与目标成组柱（使用 columns，无需新函数）
适用：只有实绩＋目标的 1–6 个同口径对象；实绩深色、目标浅色，直接标两者数值与较目标差距。
版面：左图右侧解释原因/补缺动作，或占满正文；单个对象可用大数字＋明确的目标与差距。
要点：系列名写清实际期和目标期；未来目标不是同期预算。不同单位分图，量级悬殊分面板并标刻度；目标区间保留上下界，不偷偷取上界。不默认用哑铃或差异表。""",
"""ex = Exhibit(w=560, h=320)
columns(ex, ex.body, ["华东", "华南", "华北"],
        [("FY2026 实绩", [24, 18, 12], ex.C["main"]),
         ("FY2026 预算目标", [28, 20, 15], ex.C["context"])],
        delta=(1, 0), delta_fmt=lambda gap: f"较目标 {gap:+g}", unit="亿元")
""")

RECIPES["bullet"] = ("""## bullet — 子弹图（实际＋目标＋可信基准区间）
适用：同时具有实绩、目标、可信差/中/好基准区间的多个 KPI；没有基准区间就选 target_columns，不拼造 bands。
读法：粗条=实绩，竖线=目标，灰阶底带=基准区间；不是误差线。bands 三个上界严格递增，来源与目标时点写清。
版面：左图＋右侧差距原因。单位或量级不同分面板；不加形似误差线的差距括号。""",
"""K = [dict(label="售后占比", actual=24, target=35, bands=(20, 30, 45)),
     dict(label="二手车毛利", actual=9.5, target=8, bands=(5, 8, 12)),
     dict(label="金融渗透率", actual=38, target=45, bands=(30, 40, 60))]
ex = Exhibit(w=560, h=260)
bullet(ex, ex.body, K, value_fmt=lambda v: f"{v:g}%", ranges_label="灰阶 = 行业 差 / 中 / 好", target_label="2027 目标")
""")

RECIPES["pareto"] = ("""## pareto — 帕累托（集中度、二八）
适用：一组对象按贡献降序 + 累计占比线，论点是"前 N 项贡献 X%"（客户、SKU、区域、病种、成本项）。
版面：图区 body_w(f) 左侧 + 右侧 key_takeaways，或占满宽度。
主标注：自动在累计跨过 cut（默认 80%）处画虚线并写"前 N 项 = X%"；尾部灰色。""",
"""f = frame("前三大区域贡献 75% 收入", "收入，按区域，亿元", page=6)
ex = Exhibit(w=body_w(f), h=f.bottom - f.top)                  # 图宽让出右栏
r = pareto(ex, ex.body, [("华东", 38), ("华南", 22), ("华北", 15), ("西南", 9), ("华中", 7), ("西北", 5), ("东北", 4)])
side = key_takeaways(f, [("东部三区占 75%", "华东、华南、华北合计 75%。"), ("尾部分散", "其余四区各不足 10%。")], label="区域集中度")
# f.publish(ex=ex, side=side, deck=..., page=6, cwd=CWD)
""")

RECIPES["small_multiples"] = ("""## small_multiples — 小多图（同轴看很多条趋势的形状）
适用：4–12 个对象（公司/品类/地区）各自 4–10 期的序列，一张折线图会缠成一团时。每格同一 y 轴（shared=True），标题右侧自动写末值与较上一有效期的变化（base='prev'，默认）；base='first' 改为首期→末期的跨期涨跌，非同比。
x：分类/季度字符串按等距排布，首末显示原标签；数值 x 保留真实数值距离。每行 y 与 x 等长，缺值用 None（至少 4 个有效值）。
版面：图区占满宽度；highlight 高亮论点对象（含我方，如有）。
主标注：每格同一参照线（起点/均值虚线，主角 accent）+ 空格写一句读图说明；离群对象由程序找。""",
"""P = [("中升", [100, 108, 112, 104, 96, 94]), ("永达", [60, 66, 70, 64, 58, 56]), ("美东", [20, 25, 28, 27, 26, 29]),
     ("广汇", [160, 150, 140, 128, 120, 116]), ("和谐", [30, 33, 34, 31, 29, 28])]
X = ["2024Q1", "2024Q2", "2024Q3", "2024Q4", "2025Q1", "2025Q2"]
best = max(P, key=lambda p: p[1][-1] / p[1][0])[0]                       # 唯一高于起点的对象（程序找）
ex = Exhibit(w=760, h=330)
boxes = small_multiples(ex, ex.body, P, X, highlight=lambda t: t == best, shared=False, base="first")  # 论点是 2024Q1 以来
for (n, ys), (bx0, by0, bx1, by1) in zip(P, boxes):                    # 每格同一参照：2024Q1 起点水平虚线
    ay0, ay1, lo = by0 + 24, by1 - 18, min(0, min(ys))                  # 与 small_multiples 同一纵轴（shared=False 各格独立尺度）
    y = ay1 - (ys[0] - lo) / (max(ys) - lo) * (ay1 - ay0)
    ex.line(bx0, y, bx1, y, stroke=ex.C["accent"] if n == best else ex.C["context"], width=0.8, dash="3,3", tag="ref")
a, b, c, d = boxes[-1]                                                  # 空出的第 6 格写读图说明
ex.lines(c + 26, b + 40, [f"虚线 = 2024Q1 起点", f"{len(P)} 家中仅{best}高于起点"], size=11, fill=ex.C["ink"])
""")

RECIPES["baseline_panels"] = ("""## baseline_panels — 同口径小多图 + 一条横穿各格的基准线 + 每格一个大数字（麦肯锡复刻页型）
适用：2–4 个对象（地区 / 分部 / 产品线）对同一基准（疫情前 = 100、目标、行业均值、去年同期）比较；论点是"谁超过、谁还差多少"。
版面：图区占满宽度（或右侧留 key_takeaways）；每格标题 = 对象名，下面一个大数字 = 该格对基准的读数（程序算），一根基准虚线贯穿所有格（同一尺度）。
主标注：ref=(基准值, "标签") 自动统一尺度并画线；kpi=[每格文字] 或 'last' / 'change'。标题里的几个数 = 这几个大数字。""",
"""X = ["22-11", "22-12", "23-03", "23-06"]
P = [("内地", [26, 40, 95, 107]), ("港澳台", [8, 13, 40, 59]), ("国际", [4, 5, 18, 42])]
gap = [f"{ys[-1] / 100 - 1:+.0%}".replace("-", "−") for _, ys in P]       # 对基准的读数（程序算）
ex = Exhibit(w=880, h=330)
small_multiples(ex, ex.body, P, X, kind="column", ref=(100, "2019 同月 = 100"), kpi=gap)
""")

RECIPES["fan"] = ("""## fan — 情景预测（扇形区间）
适用：实绩 + 基准预测（虚线）+ 乐观/悲观区间（浅色扇面），三个终值直接标在右端。替代"只画一条预测线"。
版面：图区 w≈560 左侧，右侧 key_takeaways 写三种情景的假设（各一句）与触发信号。
主标注：ax.ref_y 画最后实绩水平线；callout 指向基准线写 CAGR 与悲观增量（程序算）。
要点：三条情景都由 plan.py 的同一函数按不同假设算出。""",
"""X = [2021, 2022, 2023, 2024, 2025, 2026, 2027, 2028]
A = [40, 46, 51, 55, 58, None, None, None]
S = dict(low=[None] * 5 + [59, 60, 61], base=[None] * 5 + [62, 66, 70], high=[None] * 5 + [65, 72, 80])
ex = Exhibit(w=560, h=330)
ax = fan(ex, ex.body, X, A, S, 2025, ytitle="营收，亿元")
g = (S["base"][-1] / A[4]) ** (1 / (X[-1] - 2025)) - 1                       # 基准情景 CAGR（程序算）
callout(ex, (ax.sx(2027), ax.sy(S["base"][6])), f"基准 CAGR {g:+.0%}；悲观仅 {S['low'][-1] - A[4]:+d} 亿", width=170, prefer=("NW", "N", "W"))
ax.ref_y(A[4], f"2025 实绩 {A[4]}")
""")

RECIPES["treemap"] = ("""## treemap — 树图（份额面积 / 层级构成）
适用：6–15 个组成部分的份额，论点是"谁大、谁小、前几块合计多少"；比 100% 条更容易同时看清几十个小项。
版面：图区 w≈560 左侧 + 右侧 key_takeaways，或占满宽度；focus 只给论点块上主色，其余淡化。
主标注：右侧留 ~64 宽，vbracket 框住论点块写合计份额（treemap 返回各块框，程序算）。""",
"""T = [("包装水", 620), ("碳酸", 420), ("无糖茶", 310), ("功能饮料", 260), ("果汁", 180), ("即饮咖啡", 120), ("其他", 90)]
F = ("无糖茶", "功能饮料")
ex = Exhibit(w=560, h=330)
x0, y0, x1, y1 = ex.body
R = treemap(ex, (x0, y0, x1 - 64, y1), T, value_fmt=lambda v: f"{v:.0f}亿", focus=lambda n: n in F)
sh = sum(v for n, v in T if n in F) / sum(v for _, v in T)                  # 论点块合计份额（程序算）
ya, yb = min(R[n][1] for n in F), max(R[n][3] for n in F)
vbracket(ex, x1 - 60, ya + 2, yb - 2, f"{sh:.0%}", color=ex.C["accent"])
""")

RECIPES["profit_pool"] = ("""## profit_pool — 利润池（宽 = 收入占比，高 = 利润率，面积 = 利润）
适用：价值链环节 / 业务线 / 细分市场 4–10 个，论点是"收入大的环节不赚钱、赚钱的环节规模小"。
版面：图区 w≈560–620 左侧，右侧 key_takeaways 写各环节利润占比与机会；或占满宽度。
主标注：按利润率降序排列；虚线 = 收入加权平均利润率（程序算）；focus 只给论点环节上 accent，其余灰。
要点：窄柱名称自动放到轴下分行（带引线），仍放不下的列入"另有"；负利润率柱向下画。""",
"""ex = Exhibit(w=880, h=330)
profit_pool(ex, ex.body, [("整车销售", 520, 3), ("售后维保", 120, 42), ("金融保险", 60, 55), ("二手车", 90, 8),
            ("精品附件", 30, 35)], focus=lambda n: n in ("售后维保", "金融保险"))
""")

RECIPES["bump"] = ("""## bump — 排名变化（多期）
适用：5–10 个对象在 3–8 期的排名（1 = 第一），论点是"谁持续上升 / 谁掉出前列"；两期用 slope。
版面：图区占满宽度，或 w≈600 左侧 + 右侧 key_takeaways。
主标注：focus 只高亮 1–3 条论点线（含我方，如有），其余灰细线；右端写"#名次 名称"，左端写名称；
某期未上榜写 None，top=N 只画前 N 名。""",
"""ex = Exhibit(w=760, h=330)
bump(ex, ex.body, ["2021", "2022", "2023", "2024", "2025"],
     [("比亚迪", [3, 2, 1, 1, 1]), ("特斯拉", [1, 1, 2, 2, 3]), ("吉利", [4, 4, 3, 3, 2]), ("五菱", [2, 3, 4, 5, 5]),
      ("理想", [6, 5, 5, 4, 4]), ("蔚来", [5, 6, 6, 6, 6])], focus=lambda n: n in ("比亚迪", "五菱"))
""")

RECIPES["dot_range"] = ("""## dot_range — 对标点图（我方 vs 同行区间 / 中位数）
适用：3–10 个指标或对象，每行灰条 = 同行区间（lo–hi），圆点 = 实际值，空心菱形 = 中位数/目标（mark）。
版面：图区占满宽度或左侧 60%；右侧 key_takeaways 写差距最大的 1–2 项与原因。
box=(x0,y0,x1,y1) 为端点，非宽高；须 x1>x0、y1>y0，可用 ex.cols/ex.split。
主标注：focus 高亮论点行（accent 点 + 粗体 + 浅底）；ref= 画一条虚线基准（行业平均/门槛），ref_label 写在底部。
要点：每行同行区间/中位数须同指标定义、口径、时期，不仅同单位；跨行可不同指标。同单位共用尺度，异单位用 ex.cols/ex.split 拆图。""",
"""ex = Exhibit(w=760, h=300)
dot_range(ex, ex.body, [dict(label="毛利率", value=18, lo=15, hi=28, mark=22),
                        dict(label="销售费用率", value=12, lo=8, hi=16, mark=11),
                        dict(label="研发费用率", value=4, lo=3, hi=9, mark=6),
                        dict(label="净利率", value=3, lo=2, hi=12, mark=7)],
          value_fmt=lambda v: f"{v:.0f}%", focus=lambda l: l == "净利率", mark_label="同行中位数",
          ref=10, ref_label="行业平均 10%")
""")

RECIPES["funnel"] = ("""## funnel — 转化漏斗（层层流失，找最大流失环节）
适用：3–9 个依次发生的环节（曝光→点击→下单、线索→签约、患者筛查→治疗），论点是"哪一步流失最大"。
版面：图区 w≈560–620 左侧，右侧 key_takeaways 写最大流失环节的原因与改进举措；环节多时图区占满高度。
主标注：相邻环节间自动算转化率（"→ 38%"），最低一步标 accent"最大流失"；focus 高亮论点环节。
要点：条宽按数值 √ 压缩（尾部仍可见），尾部很小的环节靠数值标签读。""",
"""ex = Exhibit(w=600, h=300)
funnel(ex, ex.body, [("曝光", 100000), ("点击", 12000), ("加购", 4500), ("下单", 1700), ("复购", 900)],
       value_fmt=lambda v: f"{v:,.0f}")
""")

LAYOUT.update({"profit_pool": ("图区 w≈580 左侧 + 右侧 key_takeaways，或占满宽度。", 40, 118),
               "bump": ("图区占满宽度，或 w≈600 左侧 + 右侧 key_takeaways。", 40, 118),
               "dot_range": ("图区占满宽度或左侧 60% + 右侧 key_takeaways。", 40, 118),
               "funnel": ("图区 w≈600 左侧 + 右侧 key_takeaways。", 40, 118)})

RECIPES["chart_takeaway"] = ("""## chart_takeaway — 两张图合起来证明标题（图 → 右侧大括号 → 拆解栏）
适用：一个判断要两个指标一起看才成立（GMV 低 + 回本慢 → 加盟商不赚钱）。**结论就是页标题**（结论先行），页底不放结论框。
版面：图区占左侧约 2/3（两面板 relate 连起来），brace 竖在图区右侧、尖端朝右，指向右栏 points：每条是一个证据的拆解或含义（原因 / 口径 / 对我方），不重复标题。
主标注：每图主角柱 badge 写与同行均值之差（程序算）+ relate(kind="op", op="+") 连两图。
要点：右栏 ≤3 条、每条 ≤40 字；结论句只写在标题里。""",
"""f = frame("加盟商不赚钱：单店 GMV 比同行低 31%，回本期却长 53%", "按品牌，2025", source=["公司招股书（2025）"], page=5)
ex = Exhibit(w=600, h=f.bottom - f.top)
L, R = ex.cols(2, gap=56)                      # gap ≥48 才放得下 relate 连接符
B = ["A", "B", "C", "我方"]                    # 窄面板：类目用简称（全称写进脚注）
for box, (name, V) in zip((L, R), [("单店 GMV", [57, 46, 40, 39]), ("回本月数", [14, 18, 20, 26])]):
    with ex.panel(box):
        r = columns(ex, box, B, [(name, V, ex.C["main"])], focus=lambda c, s: c == "我方", cagr=False)
        d = V[-1] / (sum(V[:-1]) / (len(V) - 1)) - 1                  # 我方 vs 同行均值（程序算），徽章放在柱内顶部
        badge(ex, r["centers"][-1], r["tops"]["我方"] + 24, f"{d:+.0%}".replace("-", "−"), fill=ex.C["accent"], size=10)
relate(ex, L, R, kind="op", op="+")            # 两图合起来才证明标题：GMV 低 + 回本慢
br, _ = brace(650, f.top, 666, f.bottom, tip="right")
side = points(684, f.top, 236, [("客流不足", "门店集中在三四线县城，日均杯量仅同行六成"), ("成本偏高", "装修与设备投入高于同行 20%，拉长回本")],
              h=f.bottom - f.top)[0]
# frag = ex.to_slide(x=40, y=f.top); f.publish(br, side, frags=[frag], deck=..., page=5, cwd=CWD)
""")

RECIPES["expand_row"] = ("""## expand_row — 左边小多图的一行（或相邻几行）在右边展开
适用：左边同一指标按群体分行（全部 / 子群体），右边只看被选中群体的另一个指标或更细的拆分。
版面：expand_panels 建左右面板（粗体面板标题 + 细线 + 单位，中间竖分隔线）；small_rows(highlight=k 或 (a, b)) 给被展开的行铺灰底；expand(ex, rows) 从灰底引线到分隔线上的圆点。
右边：任意图——plain_bars、columns 分组柱，或再一组 small_rows（highlight 两行时右边一行对一行）。
要点：右图标题点名被展开的群体；不画 y 轴和网格，数值标在柱顶；左右合起来只讲一句话。""",
"""ex = Exhibit(w=704, h=307)
L, R = expand_panels(ex, "人均年到店次数", "次/年", "会员 12 个月复购率", "%")
yrs = ["2022", "23", "24", "2025"]
rows = small_rows(ex, L, yrs, [("全部顾客", [5.1, 5.4, 5.6, 6.2]), ("会员", [8.3, 9.1, 9.6, 11.0]),
                               ("非会员", [3.9, 4.0, 4.1, 4.3])], highlight=1)
columns(ex, (R[0], R[1] + 10, R[2], R[3]), ["普通会员", "付费会员"],
        [("2023", [52, 71], ex.C["light"]), ("2024", [58, 80], ex.C["second"]), ("2025", [66, 92], ex.C["main"])],
        show_grid=False, order="given", value_fmt=lambda v: f"{v}%", delta=(0, 2))      # 两期差直接标在柱组上
expand(ex, rows)
""")

RECIPES["expand_bar"] = ("""## expand_bar — 左图的一根柱在右图拆开（总量 → 构成 / 原因）
适用：左边是时间序列或对标，右边解释其中一根柱（最新年、我方、最大值）由什么构成。
版面：expand_panels；左图 columns(show_grid=False) 或 plain_bars；expand(ex, (r, k)) 给第 k 根柱描边并连到分隔线圆点。
要点：右图合计 = 被选中那根柱的值，右图标题写"2025 年 116 亿的构成"；最大的构成项 focus 成 accent。""",
"""ex = Exhibit(w=704, h=307)
L, R = expand_panels(ex, "营业收入", "亿元", "2025 年 116 亿的构成", "亿元")
r = columns(ex, L, ["2022", "2023", "2024", "2025"], [("收入", [72, 85, 98, 116], ex.C["main"])], show_grid=False,
            cagr=(0, 3))
plain_bars(ex, R, ["门店", "外卖", "团购", "零售"], [52, 34, 18, 12], focus=lambda c: c == "门店")
expand(ex, (r, 3))
""")

RECIPES["expand_segment"] = ("""## expand_segment — 左边堆叠柱的一段在右边展开（"愿意的人里，愿意多少"）
适用：左边是构成（100% 或绝对堆叠），右边只看其中一个色段人群/业务的分布。
版面：expand_panels；左图 columns(stack="percent", show_grid=False, order="given")；expand(ex, (r, k, "系列名")) 给那一段描边并连到圆点。
要点：右图口径 = 那一段（标题写明"2025，愿意多付者"）；右图论点项 accent，其余 light。""",
"""ex = Exhibit(w=704, h=307)
L, R = expand_panels(ex, "是否愿意为国际品牌多付钱", "受访者占比，%", "愿意多付的幅度（2025，愿意者）", "受访者占比，%")
r = columns(ex, L, ["2023", "2024", "2025"], [("不愿意", [47, 50, 50], ex.C["main"]), ("愿意多付", [53, 50, 50], ex.C["light"])],
            stack="percent", show_grid=False, order="given")
plain_bars(ex, R, ["<10%", "10–20%", "20–30%", ">30%"], [63, 34, 3, 0], focus=lambda c: c == "<10%")
expand(ex, (r, 2, "愿意多付"))
""")

RECIPES["period_notes"] = ("""## period_notes — 时间序列 + 按时段的短结论（文字在对应年份正上方）
适用：一条时间序列分成 2–4 个阶段讲（疫情前/扰动/恢复/预测、政策前后），每段一句话。
版面：图区上方留 64px；period_notes 把每段说明放在它覆盖的年份正上方，顶部色条标出时段；论点所在时段 focus 用 accent。
要点：每段 lead ≤6 字 + text ≤14 字；时段不超过 4 个；不画引线。""",
"""f = frame("门店客流三年没回到疫情前，增量全部来自即时零售", "我方年销售额，亿元", page=6)
ex = Exhibit(w=f.right - f.left, h=f.bottom - f.top - 64)
cats = ["2019", "2020", "2021", "2022", "2023", "2024", "2025", "2026E"]
r = columns(ex, ex.body, cats, [("门店", [38, 33, 34, 32, 33, 32, 31, 31], ex.C["main"]),
            ("即时零售", [1.5, 4, 5, 6, 7.5, 9, 10.5, 12.5], ex.C["accent"])], stack="stack", totals=True, forecast_from=7,
            cagr=(3, 7))   # 总量增速（不传时年度序列也会自动画）
xs, bw = period_x(ex, r, f.left)
notes, chart_top = period_notes(f, [(0, 0, "疫情前：", "门店贡献 96%"), (1, 3, "扰动期：", "门店 −13%"),
                                    (4, 6, "恢复期：", "增量全部来自线上"), (7, 7, "预测：", "线上 29%")], xs, bw, focus=2)
# f.publish(notes, frags=[ex.to_slide(x=f.left, y=chart_top)], deck=..., page=6, cwd=CWD)
""")

RECIPES["panel_pair"] = ("""## panel_pair — 两个面板，各带一句编号结论（"规模 + 质量"、"增长 + 代价"）
适用：一个判断需要两张图共同证明，例如收入涨了（左）但毛利率跌了（右）；两图看同一个对象、同一时期。
版面：frame 不传副标题；panel_heads 给每个面板一行加粗结论（关键数字 accent）+ 灰色图表标题；面板间细竖线。
主标注：每张图一处证明本栏结论的标注（左 cagr=、右 band 标"跌破同行"的年份段，程序找）。
要点：两句面板结论连起来 = 页标题；同一对象两图同色。""",
"""f = frame("收入五年翻倍，但增长是用利润换来的", None, page=5)
heads, boxes = panel_heads(f, [("收入 5 年从 24 亿增至 49 亿，年均 +15%", "营业收入，亿元", "+15%"),
                               ("同期毛利率从 24% 降到 18%，跌破同行", "毛利率，%", "18%")])
(x1, y1, w1, h1), (x2, y2, w2, h2) = boxes
ex1 = Exhibit(w=w1, h=h1)
columns(ex1, ex1.body, ["2020", "2021", "2022", "2023", "2024", "2025"], [("收入", [24, 28, 33, 38, 44, 49], ex1.C["main"])],
        cagr=(0, 5))
me, peer = [24, 23, 21.5, 20, 19, 18], [21, 21, 20.5, 20.5, 20, 20]
ex = Exhibit(w=w2, h=h2)
ax = lines(ex, ex.body, [2020, 2021, 2022, 2023, 2024, 2025], [{"name": "我方", "y": me, "color": ex.C["accent"]},
           {"name": "同行", "y": peer, "color": ex.C["context"]}], ylim=(14, 26), dots=True)
x = next(y for y, a, b in zip(range(2020, 2026), me, peer) if a < b)      # 首次跌破同行的年份（程序找）
band(ax, x - 0.5, 2025, f"{x} 起跌破同行")
# f.publish(heads, frags=[ex1.to_slide(x=x1, y=y1), ex.to_slide(x=x2, y=y2)], deck=..., page=5, cwd=CWD)
""")

RECIPES["panel_trends"] = ("""## panel_trends — 三个小图并排，各带一句结论（细分市场 / 区域 / 产品线走势分化）
适用：3 个对象的趋势形状不同，标题是"分化"；每个面板一句结论说明它的走势。
版面：panel_heads 三栏；主角面板 accent，下滑的用 neg，其余 main；每个小图在末点标最新值或累计变化。
主标注：每个小图 band 标出面板结论所说的时段并写变化（与结论文字同一个计算）。
要点：三句面板结论连起来 = 页标题；y 轴可各自独立，单位写进图表标题；超过 3 个对象用 small_multiples。""",
"""f = frame("三个细分市场走势分化：只有即时零售在加速", None, page=6)
X = list(range(2019, 2026))
data = [[2.1, 3.0, 3.9, 4.6, 5.6, 6.8, 8.7], [0.9, 1.1, 1.4, 1.8, 2.3, 2.7, 3.0], [3.1, 3.0, 3.05, 2.95, 2.88, 2.82, 2.78]]
k = [1, 1, 3]                                   # 每个面板论证的跨度：近 1 年 / 近 1 年 / 近 3 年
chg = [ys[-1] / ys[-1 - n] - 1 for ys, n in zip(data, k)]
pc = lambda v: f"{v:+.0%}".replace("-", "−")
heads, boxes = panel_heads(f, [(f"即时零售逐年加速，2025 年 {pc(chg[0])}", "规模，千亿元", pc(chg[0])),
                               (f"会员店增速降到 {chg[1]:.0%}", "规模，千亿元", f"{chg[1]:.0%}"),
                               (f"传统超市三年累计 {pc(chg[2])}", "规模，万亿元", pc(chg[2]))])
frags = []
for (x, y, w, h), ys, n, c, role in zip(boxes, data, k, chg, ["accent", "main", "neg"]):
    ex = Exhibit(w=w, h=h)
    lo, hi = min(ys), max(ys)
    ax = lines(ex, ex.body, X, [{"name": "", "y": ys, "color": ex.C[role]}],
               ylim=(lo - (hi - lo) * 0.3, hi + (hi - lo) * 0.3), xticks=[2019, 2022, 2025], dots=True, end_labels=False)
    band(ax, X[-1 - n], X[-1], pc(c))           # 面板结论里的那段时间 + 变化（程序算）
    frags.append(ex.to_slide(x=x, y=y))
# f.publish(heads, frags=frags, deck=..., page=6, cwd=CWD)
""")

RECIPES["shared_time"] = ("""## shared_time — 两个指标共用一条时间轴（上柱下线），同一时段色带贯穿两图
适用：一个指标的变化解释另一个（扩张提速 → 利润率下滑；价格战 → 份额变化），读者要看到"同一时期"。
版面：页标题左上即总论点；frame 副标题写两个指标"收入（亿元）与毛利率（%）"；图区左侧留 left≈120 放两行面板标签（XML）。
要点：band=(i, j, "时期名") 只标论证的那段；下方第一条线是主角（每点标值），第二条是对照（灰，末端标名）。""",
"""f = frame("收入五年翻倍，但扩张提速后毛利率连续下滑，已跌破同行", "营业收入（亿元）与毛利率（%）", page=7)
ex = Exhibit(w=f.right - f.left, h=f.bottom - f.top)
g = shared_time(ex, ["2020", "2021", "2022", "2023", "2024", "2025"], ("收入", [24, 28, 33, 38, 44, 49]),
                [("我方", [24, 23, 21.5, 20, 19, 18]), ("同行均值", [21, 21, 20.5, 20.5, 20, 20])],
                band=(2, 5, "扩张提速期"), left=96, bottom_fmt=lambda v: f"{v:g}%")
# 面板标签（XML，左栏与各面板等高）：g["top"] / g["bottom"] 是画布单位，×ex.scale + f.top 换成页面 y
""")

RECIPES["shared_rows"] = ("""## shared_rows — 同一组对象横向比较两三个指标（一行读到底）
适用："规模领先 ≠ 盈利领先"、"增速快的份额低"——同一组对象在两个指标上排序不同。
版面：row_table 一列对象名 + 2–3 个 Bar 列；列标题写"① 指标：一句结论"；"我方"整行 accent，负值用 neg 且从零线向左。
主标注：龙头值竖虚线 + 我方行 tag"比龙头低 Xpp"（Bar._sx 定位，程序算）；表头名次也由程序算。
要点：按页标题的主指标排序；Bar(domain=(负, 正)) 自动画零线；不要拆成两张独立条形图。""",
"""ex = Exhibit(w=880, h=340)
rows = [dict(label=n, rev=v, m=m) for n, v, m in [("山姆", 1100, 4.1), ("盒马", 750, 0.5), ("永辉", 680, -1.2),
        ("物美", 520, 1.8), ("我方", 400, -2.6), ("家家悦", 180, 1.1)]]
me = lambda r: ex.C["accent"] if r["label"] == "我方" else ex.C["main"]
rank = 1 + sorted(rows, key=lambda r: -r["rev"]).index(next(r for r in rows if r["label"] == "我方"))   # 我方收入名次（程序算）
margin = Bar("m", header="② 净利率：我方最低", domain=(-4, 5), fmt=lambda v: f"{v:+.1f}%",
             color=lambda r: ex.C["neg"] if r["m"] < 0 else me(r))
t = row_table(ex, ex.body, rows, [Label(header="", width=70), Bar("rev", header=f"① 收入，亿元：我方第 {rank}", color=me), margin],
              focus=lambda r: r["label"] in ("我方", "山姆"))
lead, mine = rows[0], next(r for r in rows if r["label"] == "我方")
callout(ex, (margin._sx(0) + 6, t["y"]["我方"]), f"比{lead['label']}低 {lead['m'] - mine['m']:.1f}pp", width=120, style="tag",
        prefer=("E",))
xl = margin._sx(lead["m"])                                          # 龙头净利率参考虚线
ex.line(xl, t["top"], xl, t["top"] + len(rows) * t["row_h"], stroke=ex.C["context"], width=0.8, dash="3,3", tag="ref")
""")

RECIPES["table_panel"] = ("""## table_panel — 表 → 虚线连接 → 结论栏（"由表可得"）
适用：一张测算/对标表推出 2–3 条对目标客户或行动的含义。
版面：表图区放左（w≈560–600）；linked_panel 放右（w≈260），source=表的绝对框，虚线从表右上/右下角连到结论栏，顶部实色标签写结论主题。
主标注：brackets 框住结论对应的行写合计占比；标题、括号、结论栏用同一组程序算的数。
要点：结论栏 2–3 条，每条以表中数字开头；标签 ≤6 字；表里与结论对应的行用 focus 高亮。""",
"""rows = [dict(label=n, a=a, s=s) for n, a, s in [("药企", 335, 40), ("Biotech", 157, 32), ("学术", 148, 30), ("医院", 86, 23)]]
S, top2 = sum(r["s"] for r in rows), rows[0]["s"] + rows[1]["s"]       # 标题、括号、结论栏用同一组数（程序算）
f = frame(f"可服务研发市场约 {S} 亿美元，药企与 Biotech 占 {top2 / S:.0%}", "按客户类型，亿美元", source=["CMC 数据（2025）"], page=6)
H = f.bottom - f.top
ex = Exhibit(w=560, h=H)
row_table(ex, ex.body, rows, [Label("label", weight=700), Bar("a", header="研发支出"),
          Text(lambda r: f"{r['s']}", header="可服务市场", weight=700)], focus=lambda r: r["label"] in ("药企", "Biotech"),
          brackets=[(0, 1, f"{top2 / S:.0%}", 2)])
panel = linked_panel(660, f.top, 260, H, "目标客户", [("药企与 Biotech：", f"合计 {top2} 亿，外包意愿最高"),
                     ("学术：", f"{rows[2]['s']} 亿，跟随基金周期")], source=(40, f.top, 600, f.bottom))
# frag = ex.to_slide(x=40, y=f.top); publish_slide(f.page(panel), frag, ...)
""")




RECIPES["before_after"] = ("""## before_after — 现状 → 目标（两个状态并排，中间写变化）
适用：同一组构成在两个时点/状态（现状 vs 目标、改革前 vs 后），论点是"总量变多少、靠哪一项"。
版面：ex.cols(2, gap≥56) 两面板同纵轴（ymax 相同），各自顶部写"状态：合计"；面板间 relate(kind="arrow", text=总量变化)。
主标注：relate 箭头上写总量变化（程序算）；增量最大的一项 badge 写增量，变化项 focus 高亮。
要点：两面板同口径同尺度；>6 项改用 dumbbell_table。""",
"""C = ["门店", "外卖", "团购", "零售"]
now, tgt = [52, 34, 18, 12], [50, 46, 26, 28]                         # 2025 实绩 → 2028 目标，亿元
ex = Exhibit(w=880, h=330)
L, R = ex.cols(2, gap=72)                                              # gap ≥48 放 relate 箭头
top = max(now + tgt) * 1.15
for box, V, t in ((L, now, "2025 现状"), (R, tgt, "2028 目标")):
    with ex.panel(box):
        ex.text(box[0], box[1] + 12, f"{t}：{sum(V)} 亿", size=11.5, weight=700, fill=ex.C["ink"])
        r = columns(ex, (box[0], box[1] + 22, box[2], box[3]), C, [(t, V, ex.C["main"] if V is now else ex.C["accent"])],
                    ymax=top, focus=lambda c, s: c in ("外卖", "零售"))
k = max(range(len(C)), key=lambda i: tgt[i] - now[i])                  # 增量最大的一项（程序找）
badge(ex, r["centers"][k], r["tops"][C[k]] - 30, f"+{tgt[k] - now[k]}", fill=ex.C["accent"], size=10)
relate(ex, L, R, kind="arrow", text=[f"{sum(tgt) / sum(now) - 1:+.0%}", "三年"])   # 总量变化写在箭头上
""")
LAYOUT["before_after"] = ("图区占满宽度；页标题写总量变化与主要来源。", 40, 118)

RECIPES["pie_of_pie"] = ("""## pie_of_pie — 复合饼图：主饼的一块或几块各自展开成子饼
适用：两层构成，第二层属于主饼的某几块（渠道 → 线上平台 + 门店类型、航线 → 各航线的承运联盟）；主饼 2–6 块、每个子饼 2–5 块。
版面：图区宽 ≥560。拆 1 块：主饼左、子饼右；拆 2–4 块：主饼居中，子饼分列左右，各自一条漏斗连到自己那块，
标题"<块名> <占比>"与图例在子饼外侧。没拆开的块保留原色但用斜线填充（原生图案，可编辑），拆开的块与子饼同色系。
主标注：标题写两层结论（"线上占 38%，其中天猫独占六成"）；可在子饼旁 speech_note 写含义。
要点：只有一层构成用 donut / hstack100；扇区 >6 个把小项并成"其他"；拆开 >4 块改 marimekko。""",
"""ex = Exhibit(w=880, h=330)
# 只拆一块
pie_of_pie(ex, ex.body, [("门店", 46), ("线上", 38), ("批发", 16)], "线上", [("天猫", 60), ("京东", 22), ("抖音", 18)],
           title_main="渠道结构 2025", title_sub="线上内部")
# 拆多块：parts 写成 {块名: 子项}，explode 省略即拆 parts 里的全部块
# pie_of_pie(ex, ex.body, [("门店", 46), ("线上", 38), ("批发", 10), ("其他", 6)], None,
#            {"门店": [("直营", 70), ("加盟", 30)], "线上": [("天猫", 60), ("京东", 22), ("抖音", 18)],
#             "批发": [("华东", 50), ("华南", 30), ("其他", 20)]})
""")
LAYOUT["pie_of_pie"] = ("图区占满宽度，或左 600 + 右侧 key_takeaways 写两层结论的原因。", 40, 118)

RECIPES["ridgeline"] = ("""## ridgeline — 山脊图：多条序列各占一行、上下交叠，比较形状与峰值时点
适用：3–6 条同单位序列（年份/区域/品类）要比的是"什么时候高、峰多尖、有几个峰"——季节性、促销节点、需求错峰。
数据必须是 research 里真实的分月/分季序列；没有就不用山脊图（不编"示意指数"/高斯曲线），改用 columns + note= 标出旺季节点。
版面：每条序列一行基线（名称在左），各行按同一最大值缩放、相邻行交叠 overlap（默认 0.55）；只保留 x 轴。
主标注：speech_note 指向最特殊的峰（"2025 出现双峰：618 + 双 11"），或 callout 写峰值月份。
要点：比绝对大小改用 lines / columns；序列 >6 条改小多图。""",
"""import math
M = list(range(1, 13))
bump_ = lambda c, w, h, b=4: [b + h * math.exp(-((m - c) / w) ** 2) for m in M]
ex = Exhibit(w=880, h=330)
bases = layered_area(ex, ex.body, M, [("2022", bump_(7, 1.6, 40)), ("2023", bump_(7.5, 1.4, 55)), ("2024", bump_(6, 1.8, 62)),
                     ("2025", [a + b for a, b in zip(bump_(5, 1.2, 50), bump_(10.5, 0.8, 35, 0))])],
                     ridge=True, xfmt=lambda v: f"{v:.0f}月")
s25 = [a + b for a, b in zip(bump_(5, 1.2, 50), bump_(10.5, 0.8, 35, 0))]
speech_note(ex, ridge_point(ex, 3, 10.5, max(s25[9:])), "双 11 形成第二峰", width=110)   # 指向 2025 行的第二个峰
""")
LAYOUT["ridgeline"] = ("图区左 600 + 右侧 key_takeaways 写峰值变化原因；或占满宽度。", 40, 118)

RECIPES["layered_area"] = ("""## layered_area — 同单位独立 overlapping（非堆积）
各层从0叠盖；趋势默认trend_lines，构成用area_stack/stacked_columns。下例为 area_stack：互斥分项累加，勿再传总量一层；拒绝缺值/负数，不填0。
unit=/line_unit= 字符串或METRICS，明确 ytitle 单位必须与元数据一致；冲突ValueError、未知兼容。价格/比率分panel或基期正规化，不自动双轴/缩放；CFO分解用 bridge。""",
"""from math import isfinite
periods = [2024, 2025]
series = [("I&A", [60, 80], "#153A56"), ("Systems", [30, 40], "#4A8BAD"), ("Service", [10, 20], "#9ABFD0")]
unit, units = "$M", ["$M", "$M", "$M"]
if len(units) != len(series) or set(units) != {unit}:
    raise ValueError("stacked：单位冲突")
if any(len(values) != len(periods) or any(value is None or not isfinite(value) or value < 0 for value in values) for _, values, _ in series):
    raise ValueError("stacked：缺值/负数")
totals = [sum(values) for values in zip(*(item[1] for item in series))]
if not all(map(isfinite, totals)): raise ValueError("stacked：总量非有限")
ex = Exhibit(w=880, h=330)
ax = NAxes.fit(ex, ex.body, (min(periods), max(periods)), (0, (max(totals) or 1) * 1.06), xticks=periods)
ax.frame(ytitle=unit)
tops = area_stack(ax, periods, series)
legend(ex, ax.x + 40, 10, [(name, color, "square") for name, _, color in series])
""")
LAYOUT["layered_area"] = ("同单位独立层从0叠盖；趋势默认trend_lines。", 40, 118)



RECIPES["kpi_scorecard"] = ("""## kpi_scorecard — 经营指标记分卡（本期 / 目标 / 较目标 / 同比 + 状态）
适用：经营回顾的达成情况：5–9 个指标逐行看本期、目标、差距和同比，未达标的一眼可见。
数据：指标只在 data_common.py 的 METRICS 里定义一次（actual / target / ly / unit / higher_better）；metric_rows(METRICS) 统一算达成、差距、同比与红黄绿状态，不手算百分比。
版面：row_table 一行一个指标；Status 列画红黄绿圆点（达标 main、接近 accent、未达标 neg）；未达标行 focus，"较目标"列同色；末列 Note 写一句原因。
要点：成本率、不良率这类越低越好的指标写 higher_better=False；% 指标的差距自动写 pt（低于 5% 的比率写 bp）。""",
"""METRICS = {"rev": dict(name="营业收入", unit="亿元", actual=126.8, target=130.0, ly=119.4),
           "nim": dict(name="净息差", unit="%", actual=1.63, target=1.60, ly=1.58),
           "npl": dict(name="不良率", unit="%", actual=1.46, target=1.35, ly=1.40, higher_better=False),
           "aum": dict(name="零售 AUM", unit="亿元", actual=3428, target=3300, ly=3110)}   # 实际写在 data_common.py
WHY = {"rev": "贷款定价下行", "nim": "存款重定价", "npl": "零售按揭风险暴露", "aum": "理财代销放量"}
rows = metric_rows(METRICS)
ex = Exhibit(w=880, h=330)
light = {"green": ex.C["main"], "amber": ex.C["accent"], "red": ex.C["neg"], None: ex.C["context"]}
pc = lambda r, k: r[k] + ("%" if r["unit"] == "%" else "")       # actual_s / target_s：按 data_common.py 的小数位
t = row_table(ex, ex.body, rows, [Label("label", weight=700), Status("status"),
          Text(lambda r: pc(r, "actual_s"), header="本期", width=70),
          Text(lambda r: pc(r, "target_s"), header="目标", width=70),
          Text(lambda r: r["vs_t"], header="较目标", width=76, color=lambda r: light[r["status"]]),
          Text(lambda r: r["delta"], header="同比", width=64),
          Note(lambda r: ("", WHY[r["key"]]), header="原因", width=200)],
          focus=lambda r: r["status"] == "red")
""")
LAYOUT["kpi_scorecard"] = ("图区占满宽度；标题写达成全貌（几项达标、最大缺口是哪项、差多少）。", 40, 118)

RECIPES["variance_bridge"] = ("""## variance_bridge — 差异桥（上期/预算 → 本期，只看变化）
适用：利润、毛利率、净息差、费用率等"为什么和目标/去年不一样"：各因素逐项加减，正负分色。
版面：Axes 的纵轴下限取在起点、终点下方一点（如 150），首尾柱从这条底线起——各项增减只有总量的几个百分点时，从 0 起画的桥看不见变化；纵轴旁写清单位，底线不是 0 时首尾柱标数值。
主标注：share=True 自动写各项占净变化比重；负向因素自动用 neg；最大贡献项在页标题里点名。
要点：终点必须等于起点+各项之和（程序校验）；增减为绝对值单位（BP、亿元），不混百分比。""",
"""steps = [("total", "2025年", 157), ("delta", "存款成本", 3), ("delta", "市场化负债", 2), ("delta", "贷款收益率", -3),
         ("delta", "债券收益率", -1), ("delta", "资产结构", 5), ("total", "2026Q3", 163)]
ex = Exhibit(w=880, h=330)
x0, y0, x1, y1 = ex.body
lo = 150                                               # 底线取在首尾值下方，变化才看得见
ax = Axes(ex, x0 + 40, y0 + 20, x1 - x0 - 50, y1 - y0 - 60, 166, lo, [150, 155, 160, 165])
ax.grid()
bands = ax.bands(len(steps), pad=0.45)
cents = [b[0] + b[1] / 2 for b in bands]
waterfall(ax, cents, bands[0][1], steps, share=True, truncated_ok=True)   # 截断底线必须显式声明并标出
scale_marker(ex, x1 - 110, y0 + 12, text=f"纵轴自 {lo} 起")
ax.xlabels(cents, [s[1] for s in steps])
""")
LAYOUT["variance_bridge"] = ("图区占满宽度，或左 600 + 右侧 key_takeaways 写前两大因素的原因。", 40, 118)


# ===== business review (IBCS)

RECIPES["ibcs_columns"] = ("""## ibcs_columns — 实际 vs 预算/去年 的月度柱 + 差异（IBCS 标准时间序列图）
适用：一个指标逐月/逐季的 AC 对 PL（或 PY），含未来期 FC；论点是"哪几个月没完成、全年预计差多少"。
版面：ibcs_columns 占满图区：下方主图（AC 实心、FC 斜线、PL 空心框/PY 灰条错位在后）+ 上方 ΔPL 差异柱 + ΔPL% 针图，三层共用 x 位置。
主标注：差异柱/针本身（红绿只给差异，程序算）；focus= 当前月浅底 + 加粗；全年合计差异写进 XML 标题或 badge。
要点：成本类指标传 favorable="down"（超支 = 红）；差异层各有自己的比例，不画网格和刻度；≥2 期；variance 要有对应参照数据。""",
"""P = ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"]
AC = [82, 78, 91, 95, 88, 102, 108, 99, 112, None, None, None]        # 净收入，百万元
FC = [None] * 9 + [115, 118, 130]                                    # 10–12 月最新预测
PL = [80, 82, 88, 92, 95, 98, 100, 104, 108, 112, 116, 124]
ex = Exhibit(w=880, h=340)
r = ibcs_columns(ex, ex.body, P, AC, PL=PL, FC=FC, variance="PL", focus="9月")
gap = sum(d for d in r["deltas"] if d is not None)                     # 全年预计 vs 预算（程序算）→ 写进标题
""")

RECIPES["ibcs_bars"] = ("""## ibcs_bars — 区域/产品/渠道 达成与差异（IBCS 结构图）
适用：4–12 个结构对象的 AC 对 PL（或 PY）；论点是"谁拖后腿、谁超额"。
版面：标题块 chart_head 左上 → 每行一个对象：AC 实心条 + PL 空心框（PY 灰条）错位在后，右侧同行对齐 ΔPL 差异条 + ΔPL% 针；total=True 合计行在细线下。
主标注：差异条/针（红绿只给差异）；focus= 只突出论点对象，其余淡化；按 AC 降序（sort=True）。
要点：结构纵向（行）、时间横向（列）；同一页两张同指标图共用比例；也可直接用 row_table 的 Scen / Variance 列自组表。""",
"""R = ["华东", "华南", "华北", "西南", "华中", "西北", "东北"]
AC = [412, 298, 265, 188, 152, 76, 58]                               # 净收入，百万元
PL = [395, 310, 250, 200, 140, 82, 66]
ex = Exhibit(w=880, h=340)
x0, y0, x1, y1 = ex.body
top = chart_head(ex, x0, y0, "全国销售", "净收入，百万元", "2026 年 1–9 月 · AC vs PL")
t = ibcs_bars(ex, (x0, top + 8, x1, y1), R, AC, PL=PL, total=True)
""")

RECIPES["variance_table"] = ("""## variance_table — 多指标 KPI 差异表（损益/经营 KPI 对预算与去年）
适用：5–8 个 KPI 对预算与去年；达成比较AC与PL须同期间同口径，PY取相同可比时段。上期实绩对下期指引用普通对比表展示预期变化，不作达标状态；口径不同只并列注明、不算Δ。
版面：row_table：Label + Text(实际) + Text(预算) + Variance(ΔPL) + Variance(ΔPL%) + Text(去年) + Variance(ΔPY) + Variance(ΔPY%)；w=880 放得下 6–8 行。
主标注：Variance 列的红绿条/针就是标注（自动计数）；费用行 favorable=lambda r: "down"（超支 = 红）。
要点：Variance 列宽默认均分剩余宽度（width= 可固定）；同一参照的两列共用一个零轴；数值列只写 AC/PL/PY，可比差异由程序算。""",
"""rows = [dict(label=n, ac=a, pl=p, py=y) for n, a, p, y in [("净收入", 1204, 1180, 1096), ("毛利", 386, 401, 352),
        ("销售费用", 158, 150, 149), ("管理费用", 64, 70, 61), ("营业利润", 164, 181, 142), ("经营现金流", 131, 150, 118)]]
fav = lambda r: "down" if "费用" in r["label"] else "up"              # 费用越低越好
ex = Exhibit(w=880, h=300)
row_table(ex, ex.body, rows, [Label("label", weight=700), Text(lambda r: fmt(r["ac"]), header="实际", weight=700),
          Text(lambda r: fmt(r["pl"]), header="预算"), Variance("ac", "pl", favorable=fav),
          Variance("ac", "pl", pct=True, favorable=fav), Text(lambda r: fmt(r["py"]), header="去年"),
          Variance("ac", "py", favorable=fav), Variance("ac", "py", pct=True, favorable=fav)])
""")

RECIPES["wbr_trend"] = ("""## wbr_trend — 周/月指标走势（Amazon WBR 6+12 图）
适用：周会/月会的核心指标：近 6 周看短期拐点，近 12 个月看季节与趋势，同时对去年和目标。
版面：左窄（近 6 周）右宽（近 12 个月）两栏共用一个纵轴；AC 粗线带点、PY 细灰线、目标虚线；末点写值 + 同比。
主标注：末值与同比（红绿按 favorable）、目标线标签（程序算）；ex.related 自动设好（共用比例即关系）。
要点：多个指标 = 多个 wbr_trend 图区上下排（每个 h≈200–260），或 small_multiples；周标签用 W35 / 9-01 这类短写法。""",
"""W = ["W35", "W36", "W37", "W38", "W39", "W40"]
M = ["11月", "12月", "1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月"]
ex = Exhibit(w=880, h=320)
wbr_trend(ex, ex.body, W, [18.2, 18.9, 19.4, 18.7, 20.1, 21.3], [16.8, 17.1, 17.5, 17.9, 18.0, 18.4],
          M, [15.2, 17.8, 14.9, 14.1, 15.6, 16.2, 16.9, 17.4, 17.8, 18.3, 19.0, 20.4],
          [13.9, 16.0, 13.8, 13.0, 14.2, 14.8, 15.3, 15.9, 16.2, 16.8, 17.3, 18.1],
          target=20, value_fmt=lambda v: f"{v:.1f}", name="GMV（亿元）")
""")

RECIPES["ibcs_bridge"] = ("""## ibcs_bridge — 预算（或去年）→ 实际 差异归因桥
适用：解释"实际比预算多/少多少、各因素各贡献多少"（销量、价格、结构、费用、汇率、一次性）。
版面：一行 ibcs_bridge：起点预算 = 空心框（start_scen="PY" 时浅灰），终点实际 = 实心，中间因素有利 good / 不利 bad；
图区占满宽度，或 w≈560 放左 + 右侧 key_takeaways 逐项写原因与动作。
主标注：各因素数值；因素同向时自动写占净差异比重；focus= 标题点名的主因描框；纵轴截断时自动写"纵轴自 x 起"。
要点：起点 + 各项 = 终点（程序校验，拆不出的列"其他"）；成本 / 费用桥 favorable="down"（增加 = 不利红）；
因素按影响大小或业务逻辑排序，≤7 项。""",
"""steps = [("销量", 38), ("价格", -14), ("结构", 6), ("汇率", -5), ("一次性", -3)]   # 百万元，来自 plan.py
ex = Exhibit(w=880, h=320)
r = ibcs_bridge(ex, ex.body, ("预算", 1180), steps, end=("实际", 1202), focus="销量")
""")

LAYOUT.update({
    "target_columns": ("成组柱直接标实绩、目标和差距；右栏解释原因。", 40, 118),
    "ibcs_columns": ("图区占满宽度（h≈320–360）；页标题写全年预计差异，副标题写 实体·指标·期间（AC vs PL）。", 40, 118),
    "ibcs_bars": ("图区占满宽度或左侧 60% + 右侧 key_takeaways；标题块 chart_head 画在图区左上。", 40, 118),
    "variance_table": ("图区占满宽度，高度按行数（每行约 40–50）；下方 XML 写 2–3 条差异原因。", 40, 130),
    "wbr_trend": ("图区占满宽度；一页 1–2 个指标（上下两个 Exhibit，各 h≈220）。", 40, 118),
    "ibcs_bridge": ("图区占满宽度，或 w≈560 放左 + 右侧 key_takeaways 逐项解释因素。", 40, 118),
})

RECIPES["pace"] = ("""## pace — 全年进度：累计实际 vs 累计预算 + 余下每期需完成多少
适用：年中/季度复盘回答"按现在的节奏全年能不能完成"；比月度柱更直接看出领先/落后与追赶压力。
版面：上 70% 累计线（预算灰、去年浅灰、实际主色），实际末点到全年目标画虚线"所需节奏"；下 30% 每期累计差（好坏色）。
主标注：callout 自动写"X月累计领先/落后 N，余下每期需 M（此前均 K）"——数值由程序算；页标题照抄这句结论。
要点：AC/PL/PY 均为单期流量，累计/YTD 先差分；全年总额不能作最后一期增量。AC 未来期省略/None；前期仅合计用 base=；target= 全年目标，可不同于 PL 合计。
只有全年指引、无真实分期预算：不编造 PL/预算差异，改用实际 vs 全年目标 + 所需余量组合；不用 lines 手画挤在一起的累计线。""",
"""M = ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"]
AC = [8.2, 7.8, 9.1, 9.5, 8.8, 10.2, 10.8, 9.9, 11.2]                  # 亿元，来自 data_common.py
PL = [8, 8.2, 8.8, 9.2, 9.5, 9.8, 10, 10.4, 10.8, 11.2, 11.6, 12.4]
ex = Exhibit(w=880, h=340)
r = pace(ex, ex.body, M, AC, PL, unit="亿")                             # r["gap"] / r["need"] → 标题
# 只有上半年合计 + 下半年逐月时：pace(ex, box, ["7月", …, "12月"], AC_H2, PL_H2, base=("1–6月", 15820, 15600))
""")

RECIPES["kpi_spark_table"] = ("""## kpi_spark_table — 指标走势表（每行：指标 + 迷你走势 + 本期 + 同比 + 一句原因）
适用：一页看 4–8 个指标的水平和走势（年报"五年摘要"、月报指标墙）；替代"6 张 KPI 卡 + 6 条迷你线"的仪表盘。
版面：row_table：Label + Spark(序列) + Text(本期) + Text(同比/较目标) + Note(原因)；Spark(kind="bar") 画迷你柱（末期 accent）。
主标注：Spark 末点 accent 并写值；最需要关注的行 focus=，其余淡化。
要点：Spark 每行自用尺度（看形状），同单位可 shared=True；序列从 METRICS 的 series 取，不手打。""",
"""rows = [dict(label="营业收入", s=[88, 96, 104, 118, 127], v="126.8 亿", d="+6.2%", why="门店扩张贡献 70%"),
        dict(label="毛利率", s=[31.9, 31.2, 30.5, 32.4, 31.1], v="31.1%", d="−1.3pt", why="原料涨价，未提价"),
        dict(label="门店数（万）", s=[3.2, 3.6, 4.5, 5.2, 5.98], v="5.98", d="+28.7%", why="下沉市场占新增 58%"),
        dict(label="净利润", s=[12, 14, 18, 22, 25], v="25.0 亿", d="+33.1%", why="规模摊薄费用率")]
ex = Exhibit(w=880, h=300)
row_table(ex, ex.body, rows, [Label("label", weight=700), Spark("s", width=150, header="2021–2025"),
          Text(lambda r: r["v"], header="2025", width=80, weight=700), Text(lambda r: r["d"], header="同比", width=70),
          Note(lambda r: ("", r["why"]), header="原因", width=210)], focus=lambda r: r["label"] != "毛利率")
""")

RECIPES["heat_matrix"] = ("""## heat_matrix — 达成热力矩阵（区域/门店/产品 × 月份，哪里持续偏低）
适用：几个对象 × 6–12 期的达成率/增速，读者要一眼找到"哪一行一直红"；比 6 条折线清楚。
版面：row_table：Label + 每期一个 Heat 列（mid=100 以达标为界：高于偏主色、低于 below="neg" 偏警示色）+ Text 累计列；gap=6 收紧。
主标注：focus= 只亮问题行（其余淡化）；vbracket 括住问题行写原因，或右侧 key_takeaways 解释。
要点：格内只写数字（≤4 字）；列多时 Heat(width=50) + gap=6；对象 >8 行用 top_n 合并。""",
"""R = ["华东", "华南", "华北", "华中", "西南"]
M = ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月"]
A = {"华东": [102, 98, 105, 107, 103, 110, 108, 104, 112], "华南": [96, 94, 99, 101, 97, 100, 103, 98, 104],
     "华北": [91, 88, 92, 95, 90, 93, 94, 89, 92], "华中": [99, 101, 100, 104, 102, 98, 105, 103, 106],
     "西南": [85, 83, 88, 86, 84, 87, 90, 86, 88]}                         # 达成率 %，来自 data_common.py
rows = [dict(label=r, ytd=round(sum(A[r]) / len(M)), **dict(zip(M, A[r]))) for r in R]
ex = Exhibit(w=880, h=300)
cols = [Label("label", weight=700)] + [Heat(m, width=54, header=m, mid=100, below="neg", fmt=lambda v: f"{v:.0f}")
                                       for m in M] + [Text(lambda r: f"{r['ytd']}%", header="累计", width=56, weight=700)]
t = row_table(ex, ex.body, rows, cols, gap=6, focus=lambda r: r["ytd"] < 95)
bad = [r["label"] for r in rows if r["ytd"] < 95]                        # 问题行（程序找）→ 括号写原因
vbracket(ex, t["cols"][-1][1] + 6, t["y"][bad[0]] - t["row_h"] / 2 + 4, t["y"][bad[-1]] + t["row_h"] / 2 - 4, "渠道调整")
""")
LAYOUT.update({"pace": ("图区占满宽度，或 w≈600 放左 + 右侧 key_takeaways 写追赶措施。", 40, 118),
               "kpi_spark_table": ("图区占满宽度；标题写最重要的一两项变化。", 40, 118),
               "heat_matrix": ("图区占满宽度，或 w≈620 + 右侧 key_takeaways 解释问题行。", 40, 118)})

RECIPES["action_plan"] = ("""## action_plan — 措施闭环表（每条措施补回多少，累加对上缺口）
适用：下一步 / 追赶计划页：3–6 条措施，各写负责人、时点、预计补回与检验标准，累计条显示能否补上缺口；比甘特图更适合一个季度内的行动。
版面：row_table：Label(措施) + Text(负责人) + Text(时点) + Bar(cumulative=True, domain=(0, 缺口)) + Note(检验标准)；total 行写合计对缺口；右侧或下方写需要拍板的事项（key_takeaways）。
主标注：累计条本身（自动计为标注）；合计不足缺口时标题写"仍差 N"，超过时写"可覆盖缺口"。
要点：补回金额来自测算（data_common.py），检验标准写可量化阈值；跨多个季度/年度的计划改用 roadmap。""",
"""GAP = 519                                                              # 万元，来自 data_common.py
rows = [dict(label="蛋糕爆品聚焦", who="产品部", due="11 月中", imp=180, kpi="蛋糕缺口 ≤120 万；末位 20% SKU 下架"),
        dict(label="杭州、宁波帮扶", who="营运部", due="12 月末", imp=150, kpi="宁波达成 ≥90%，否则闭店评估"),
        dict(label="黄油奶油锁价", who="采购部", due="10 月末", imp=90, kpi="毛利率回到 ≥62.5%"),
        dict(label="会员复购召回", who="CRM", due="11 月末", imp=60, kpi="复购率 ≥41%")]
ex = Exhibit(w=880, h=320)
t = row_table(ex, ex.body, rows, [Label("label", weight=700), Text(lambda r: r["who"], header="负责人", width=70, align="start"),
              Text(lambda r: r["due"], header="时点", width=64, align="start"),
              Bar("imp", header=f"预计补回，万元（累加，满格 = 缺口 {GAP}）", cumulative=True, domain=(0, GAP), fmt=lambda v: f"+{v:.0f}"),
              Note(lambda r: ("", r["kpi"]), header="检验标准", width=230)],
              total=dict(label="合计", who="", due="", imp=sum(r["imp"] for r in rows), kpi=""))
""")
LAYOUT["action_plan"] = ("图区占满宽度；或 w≈620 + 右侧 key_takeaways 列需要拍板的事项。", 40, 118)

_API = """# exhibit 图区接口

画布：Exhibit(w=目标框宽, h=目标框高, palette=配色, lang='zh')。
ex.body / ex.cols(n) / ex.split(frac) 分配图内区域；坐标使用画布单位，轴用 Axes / NAxes 映射真实数值。
输出：ex.save(path) 写 SVG；ex.tostring() 返回 SVG；ex.to_slide(x,y,width) 返回原生元素片段。
生成流程：exhibit_help('standalone')；SVG 转原生、合入调用方已有 XML：exhibit_help('atomize')。

常用图表：columns / lines / row_table / waterfall / bubbles / pareto / funnel / sankey / treemap。
标注：cagr_arrow / total_diff / level_diff / callout / speech_note / badge / num_dot / band / span_bracket。
columns 的 cagr/yoy/diff/target/delta/note，lines 的 delta/forecast_from/note 可随数据直接画标注。
表列：Label / Text / Note / Bar / Dumbbell / Range / Box / Heat / Harvey / Scen / Variance / Spark / Status。
图内配色：ex.C 的 main/accent/second/light/context/neg/good/bad/ink/text/axis/grid 等角色。
绘图函数返回轴或位置数据；SVG 导出、原生转换及页面 XML 组装是独立步骤。
"""


_WORKFLOW_HELP = {
    'standalone': '''# exhibit：独立 SVG 图表制作

Exhibit 只承载图区。无需 frame、演示文稿 ID 或发布调用。
先运行 exhibit_help() 选方案，再用 exhibit_help('方案名') 查数据条件、exhibit_help('函数名') 查参数。
图表配方返回独立图区代码；目标尺寸由调用方按展示位置确定，下面尺寸仅用于接口示例。

w/h 是目标框尺寸，内部画布默认除以 1.25；图内使用 ex.body、ex.cols/ex.split 或轴映射。
palette 可用 mckinsey_blue/bcg_green/bain_red/exec_navy，或 brand_palette('#品牌色') 返回的字典。
绘图函数返回的是轴或位置数据，不是 SVG；用 ex.save(path) 写文件，返回布局问题 list（即使有问题也会写）。
下面示例数据仅演示接口，正式使用替换为来源数据；CAGR 只用于可比年度总量，比例变化用百分点。

## 导入
```python
import sys
from pathlib import Path

sys.path.insert(0, "<skill 根目录>")  # SKILL.md 所在目录，放在所有 scripts 导入之前
from scripts.svg_lib.exhibit import (
    Exhibit, Axes, columns, lines, waterfall, row_table, Label, Bar, exhibit_help,
)
```

## 柱图与 CAGR
```python
# 柱图：各年收入与 CAGR（示例数据）
ex_columns = Exhibit(w=880, h=340, palette="mckinsey_blue", lang="zh", keynote=False)
columns(ex_columns, ex_columns.body, ["2023", "2024", "2025"],
        [("收入", [100, 135, 180])], cagr=(0, 2), unit="万元")
issues = ex_columns.save("columns.svg")
print(issues)  # save 返回布局问题 list，不是文件路径；空列表表示没有问题
```

## 时间折线
```python
# 折线图：按真实年份间隔绘制（示例数据）
ex_lines = Exhibit(w=880, h=340, palette="mckinsey_blue", lang="zh", keynote=False)
lines(ex_lines, ex_lines.body, [2020, 2021, 2022, 2023, 2024, 2025],
      [{"name": "收入", "y": [80, 90, 110, 130, 150, 180]}],
      xtitle="年份", ytitle="收入（万元）")
ex_lines.save("lines.svg")
```

## 贡献瀑布
```python
# 瀑布图：100 + 20 - 10 = 110（示例数据）
ex_bridge = Exhibit(w=880, h=340, palette="mckinsey_blue", lang="zh", keynote=False)
steps = [("total", "期初", 100), ("delta", "销量", 20),
         ("delta", "成本", -10), ("total", "期末", 110)]
ax = Axes.fit(ex_bridge, ex_bridge.body, 140)
ax.grid()
bands = ax.bands(len(steps), pad=0.45)
centers = [x + w / 2 for x, w in bands]
waterfall(ax, centers, bands[0][1], steps)
ax.xlabels(centers, [s[1] for s in steps])
ex_bridge.save("bridge.svg")
```

## 排名条形表
```python
# 排名条形表：记录字段与列定义（示例数据）
ex_rank = Exhibit(w=880, h=340, palette="mckinsey_blue", lang="zh", keynote=False)
rows = [{"label": n, "value": v} for n, v in
        [("华东", 60), ("华南", 50), ("华北", 40), ("西南", 30), ("华中", 20), ("东北", 10)]]
row_table(ex_rank, ex_rank.body, rows,
          [Label("label", header="区域"), Bar("value", header="收入（万元）")])
ex_rank.save("ranking.svg")
```

选中画布后导出，例如 ex_columns.tostring() 返回柱图 SVG 字符串；其它图可换成 ex_lines / ex_bridge / ex_rank。
独立展示需要背景时用 Path('chart.svg').write_text(ex_columns.tostring(background=True), encoding='utf-8')。
用于原生转换的 SVG 用 ex_columns.save，保留图案填充等转换标记。
用户需要 PNG 时用 ex_columns.preview('chart.png', width=1320)，返回路径或渲染器不可用时的空字符串。
SVG 转原生并合页：exhibit_help('atomize')。
''',
    'atomize': '''# exhibit：任意图框、多图与其它 XML 合页

每张图的 box=(x,y,width,height) 由调用方按内容自主确定；没有固定的页面位置或尺寸。
这里是页面映射的左上角与宽高；ex.body 等绘图框使用 (x0,y0,x1,y1)，不要混用。
一页可以组合任意数量的图区与文字、表格、图片等 XML。每个 SVG 单独映射，再合并全部片段。
生成 SVG 时按各图目标框设置 Exhibit(w=width,h=height)，保持源图比例与目标框一致。

## SVG 转原生片段
```python
from pathlib import Path
import xml.etree.ElementTree as ET
from scripts.svg_lib.atomize_svg_to_slide import (
    set_mapping, atomize_svg_to_slide, compose_slide, publish_slide,
)

def svg_fragment(svg_path, box):
    x, y, w, h = box
    _, _, sw, sh = map(float, ET.parse(svg_path).getroot().attrib['viewBox'].split())
    set_mapping(svg_w=sw, svg_h=sh, slide_x0=x, slide_y0=y, slide_w=w, slide_h=h)
    return atomize_svg_to_slide(svg_path)
```

atomize_svg_to_slide 输入 SVG 路径，返回原生元素片段；slide/data 外壳是容器，不代表新增一页。
柱块、文字、点、线、曲线路径可转原生，复杂效果可能保留局部 embed。
若已有 Exhibit 对象，可调用 ex.to_slide(x=x,y=y,width=w)，内部完成转换和连线避让；不发布。
改数据后重生成图形，单改数值文字不会移动图形。

## 与调用方已有 XML 组合
chart_jobs 由调用方提供，格式为 [(SVG路径, (x,y,width,height)), ...]。
page.xml 包含本页自行编排的标题、正文、图片、表格等内容，图框应与这些元素协调。
```python
page_xml = Path('page.xml').read_text(encoding='utf-8')
fragments = [svg_fragment(path, box) for path, box in chart_jobs]
combined_xml = compose_slide(page_xml, *fragments)  # 可只合页、保存 XML
r = publish_slide(page_xml, *fragments, presentation='<xml_presentation_id>', page=3)
print(r['ok'], r['slide_id'], r['summary'])
```

单图也使用相同接口，chart_jobs 只有一项即可；不必让一张图占满整页。
compose_slide 合并所有 data；不要手工嵌套 slide，也不要把 combined_xml 与相同片段再次传入。
修改已有页指定 slide_id；确认 ok 和 slide_id，失败保留 errors/summary。
''',
}

_RECIPE_BUDGET = 2280   # exhibit_help('<recipe>') stays compact (tests: < 2300)


def _default(v):
    if callable(v):
        return "<fn>"
    r = repr(v)
    return r if len(r) <= 28 else r[:25] + "…"


def signature(name):
    """'name(param, param=default, …)' + first docstring line of a public exhibit function / column class, generated
    from inspect.signature so it never drifts from the code. None for unknown names."""
    import inspect
    import importlib
    pkg = importlib.import_module(__package__)
    f = getattr(pkg, name, None)
    if f is None or not callable(f):
        return None
    try:
        sig = inspect.signature(f)
    except (TypeError, ValueError):
        return None
    ps = []
    for p in sig.parameters.values():
        if p.name == "self":
            continue
        if p.kind is p.VAR_POSITIONAL:
            ps.append("*" + p.name)
        elif p.kind is p.VAR_KEYWORD:
            ps.append("**" + p.name)
        elif p.default is p.empty:
            ps.append(p.name)
        else:
            ps.append(f"{p.name}={_default(p.default)}")
    para = " ".join((inspect.getdoc(f) or "").strip().split("\n\n")[0].split())
    m = re.search(r"^(.+?[.。])(\s|$)", para)
    doc = (m.group(1) if m else para)[:160]
    return f"{name}({', '.join(ps)})" + (f"\n    {doc[:160]}" if doc else "")


def signatures(names=None):
    """Signature block for names (default: every public function / column class in exhibit.__all__)."""
    import importlib
    pkg = importlib.import_module(__package__)
    names = names or [n for n in pkg.__all__ if n not in ("exhibit_help", "fmt", "tw", "wrap", "roles")]
    return "\n".join(s_ for s_ in (signature(n) for n in names) if s_)


_PAGE_RECIPE_NAMES = {"appendix", "chapter_nav", "period_notes", "panel_pair", "panel_trends", "table_panel"}


def _chart_function_names():
    """Only figure/data APIs; page builders retain their runtime APIs but have no chart help entry."""
    import importlib
    import inspect

    pkg = importlib.import_module(__package__)
    names = []
    for name in pkg.__all__:
        function = getattr(pkg, name, None)
        if not callable(function) or name == "exhibit_help":
            continue
        module = getattr(function, "__module__", "")
        if module.rsplit(".", 1)[-1] in {"_frame", "_layouts", "_glossary"}:
            continue
        try:
            first = next(iter(inspect.signature(function).parameters), None)
        except (ValueError, TypeError):
            continue
        if first not in {"f", "frame"}:
            names.append(name)
    return names


def _figure_code(name):
    """Extract the figure from a legacy recipe; never return its slide shell or side rail."""
    import ast

    code = RECIPES[name][1]
    if name == "risk_matrix":
        code = code.replace("dict(x=a, y=b,", "dict(label=n, x=a, y=b,").replace("numbered=True", "numbered=False")
    tree = ast.parse(code)
    page_calls = {"frame", "points", "key_takeaways", "brace", "linked_panel"}
    kept = []
    for node in tree.body:
        value = node.value if isinstance(node, (ast.Assign, ast.Expr)) else None
        if value is not None and any(isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
                                     and call.func.id in page_calls for call in ast.walk(value)):
            continue
        kept.append(node)
    tree.body = kept

    class FigureBox(ast.NodeTransformer):
        def visit_Call(self, node):
            if isinstance(node.func, ast.Name) and node.func.id == "Exhibit":
                for option in node.keywords:
                    if option.arg in {"w", "h"} and any(isinstance(n, ast.Name) and n.id == "f" for n in ast.walk(option.value)):
                        option.value = ast.Constant(880 if option.arg == "w" else 340)
            return self.generic_visit(node)

    tree = FigureBox().visit(tree)
    if any(isinstance(node, ast.Name) and node.id == "f" for node in ast.walk(tree)):
        return None
    ast.fix_missing_locations(tree)
    return ast.unparse(tree) + "\nex.save('chart.svg')\n"


def _chart_recipe_names():
    return [name for name in RECIPES if name not in _PAGE_RECIPE_NAMES and _figure_code(name) is not None]


def _figure_notes(notes):
    """Keep data conditions and annotations, excluding complete-slide placement advice."""
    out = []
    for line in notes.splitlines():
        if line.startswith("版面："):
            continue
        if any(token in line for token in ("key_takeaways", "frame(", "f.publish", "body_w(f)", "整页", "页宽", "右栏", "左栏")):
            continue
        out.append(line)
    return "\n".join(out)


def exhibit_help(name=None):
    """Figure capabilities, independent SVG recipes, annotations, conversion and XML composition."""
    charts = _chart_recipe_names()
    functions = _chart_function_names()
    if name is None:
        rows = []
        for question, choices in ROUTES:
            names = [choice for choice in re.split(r"\s*/\s*", choices) if choice in charts]
            if not names:
                continue
            question = question.replace("（右侧拆解栏）", "").replace("多图一页", "多图区共享时间或对象")
            rows.append(f"| {question} | {' / '.join(names)} |")
        return _HEAD + "\n| 读者要比较什么 | 图表方案 |\n|---|---|\n" + "\n".join(rows)
    name = name.strip()
    if name in _WORKFLOW_HELP:
        return _WORKFLOW_HELP[name]
    if name in ("api", "signatures", "sig"):
        return _API + "\n# 图区函数与列类型签名\n" + signatures(functions).replace("frame(...), ", "")
    if name not in charts:
        if name in functions:
            extra = [name] + (["Label", "Text", "Bar", "Note", "Dumbbell", "Range", "Heat"] if name == "row_table" else [])
            out = signatures(list(dict.fromkeys(extra))).replace("frame(...), ", "")
            hints = annotation_hints([name])
            return out + ("\n标注参数：" + hints[name] if hints else "")
        raise KeyError(f"exhibit_help only provides figure APIs and recipes; choose from {', '.join(charts)}; SVG/export: standalone/atomize")
    points = _figure_notes(RECIPES[name][0])
    code = _figure_code(name)
    called = [n for n in dict.fromkeys(re.findall(r"\b([A-Za-z_]\w*)\(", code)) if n in functions and n != "Exhibit"]
    hints = annotation_hints(called)
    if hints:
        points += "\n标注参数：\n" + "\n".join(f"- {n}：{text}" for n, text in hints.items())
    sigs = []
    for n in called:
        line = (signature(n) or "").split("\n")[0]
        if len(points) + len(code) + sum(len(s) + 1 for s in sigs) + len(line) + 140 < _RECIPE_BUDGET:
            sigs.append(line)
    if sigs:
        points += "\n本方案用到的函数签名（自动生成）：\n" + "\n".join(sigs)
    return points + "\n\n独立图区代码（示例数据；尺寸按调用方需求调整）：\n```python\nfrom scripts.svg_lib.exhibit import *\n" + code + "```"


# Argument annotations each function can draw by itself: "title says … → parameter". next() attaches the lines for the
# functions a page's recipe calls, so the builder sees the annotation options next to the signature, not buried in it.
ANNOTATIONS = {
    "columns": ["可比年度总量的 CAGR → cagr=(i,j)，按原数据自动算；比率/同比增速传 unit='%'，用 diff= / yoy= 画 Δpt，不再算 CAGR", "同比/转折 → yoy=k",
                "差距/倍数 → diff=(i, j)", "目标/缺口 → target=(值, '目标')", "两系列逐组差 → delta=(a, b)",
                "主角 → focus=lambda c, s: …", "预测年 → forecast_from=k",
                "某根柱说明什么 → note=(类目, '一句含义')（说话框，可与 cagr 同用）",
                "同一组类目的第二个指标（利润率、份额、笔数、均价）→ rows=[('利润率', [...], lambda v: f'{v:.1f}%')]（轴下数据行，≤2 行，不另画小图、不混轴）"],
    "lines": ["两线差距 → delta=(a, b, [x])", "预测 → forecast_from=x", "主角线 → focus=lambda name: …",
              "时期 → band(ax, a, b, '原因')", "目标/均值 → ax.ref_y(v, '标签')", "拐点 → callout((ax.sx(x), ax.sy(y)), '一句判断')",
              "某点说明什么 → note=(x, '一句含义')（说话框）",
              "同期第二个指标 → rows=[('渗透率', [...], fmt)]（轴下数据行，不用双轴）"],
    "row_table": ["前 N 合计/分组 → brackets=[(i0, i1, '62%', 列号)]", "合计行 → total=dict(...)", "重点行 → focus=lambda r: …",
                  "每行含义 → Note 列", "排名升降 → Rank 列", "两期差 → Dumbbell(delta=True)"],
    "bubbles": ["主角 → focus=", "分组着色 → groups=True", "象限 → quadrants(ax, x, y, labels=)（键按坐标：TR=x大y大、TL=x小y大、BR=x大y小、BL=x小y小；象限名要和该角的 x/y 含义一致）", "相关 → trend(ax, xs, ys)",
                "编号呼应 → numbered=True"],
    "slope": ["主角 → focus=", "排名而非数值 → rank=True"],
    "bullet": ["仅有实绩+目标 → exhibit_help('target_columns')", "可信区间带 → bands=(差, 中, 好)，严格递增", "目标时点/区间来源 → target_label= / ranges_label="],
    "pareto": ["二八分界 → cut=0.8", "只看前 N → top_n="],
    "small_multiples": ["主角面板 → highlight=", "统一尺度 → shared=True", "关键年 → focus_x=",
                        "共同基准（疫情前=100 / 目标 / 行业均值）→ ref=(值, '标签')：一条线横穿所有格、自动同尺度",
                        "每格一个大数字（对基准差、末值、变化）→ kpi=[每格文字] 或 'last' / 'change'",
                        "表头变化默认对上一期（同比/环比，与副标题口径一致）；要首期以来的累计变化 → base='first'"],
    "fan": ["预测起点 → forecast_from=", "基准线 → ax.ref_y(v, '标签')"],
    "treemap": ["主角块 → focus="],
    "funnel": ["最大流失环节 → focus=（自动标转化率）"],
    "dot_range": ["我方/主角点 → focus=", "基准线 → ref= + ref_label=", "点的含义 → mark_label="],
    "waterfall": ["占净变化比重 → share=True", "逐项着色 → steps 第 4 项写颜色"],
    "ibcs_bridge": ["主因 → focus='项名'", "费用桥 → favorable='down'"],
    "ibcs_columns": ["对预算/去年 → variance='PL'/'PY'", "预测期 → FC=", "费用类 → favorable='down'", "重点期 → focus="],
    "ibcs_bars": ["对预算/去年 → variance=", "重点行 → focus=", "合计 → total=True"],
    "wbr_trend": ["目标线 → target=(v, '目标')"],
    "bump": ["主角 → focus=", "只看前 N → top="],
    "tornado": ["决策阈值 → threshold= + threshold_label="],
    "timeline": ["关键事件 → focus=", "阶段 → phases="],
    "donut": ["主角扇区 → focus=", "中心大数 → center= + center_sub="],
    "pie_of_pie": ["被展开的一块 → explode='名称'（自动 accent）", "拆多块 → parts={块名: 子项}（未拆的块斜线填充）",
                   "两饼标题 → title_main= / title_sub="],
    "layered_area": ["默认同单位目标线：line=，unit=/line_unit=",
                     "互斥构成：area_stack；轴取逐期和，勿另叠总量",
                     "山脊：ridge=True；堆积标注取tops累加边界"],
    "speech_note": ["说话框：任何图都能用 speech_note(ex, (x, y), '这个数说明什么')；columns/lines 直接传 note=；每图 ≤2 个、≤30 字"],
    "Dumbbell": ["两期差写在连线上 → delta=True", "数值 → labels='values'"],
    "Range": ["参考线（0 / 1 / 中位数）→ ref="],
    "Bar": ["主角行 → focus=", "依次累加 → cumulative=True"],
    "shared_time": ["贯穿两图的时期 → band=(i, j, '时期名')"],
}


def annotation_hints(names):
    """{function: "title says … → parameter; …"} for the functions named (those with annotation options)."""
    return {n: "；".join(ANNOTATIONS[n]) for n in names if n in ANNOTATIONS}
