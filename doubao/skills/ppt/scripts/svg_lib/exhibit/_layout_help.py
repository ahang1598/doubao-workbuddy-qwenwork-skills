"""Runnable native page-layout recipes, kept separate from chart-only RECIPES."""

PAGE_LAYOUTS = {
    "icon_grid": (
        "图标网格（10×10）：任何'一个整体 ≤4 部分'的占比（市场份额、渠道结构、收入构成、用户结构都用它，不限于人），标题写成'每 100 个…中有 N 个…'。10×10 个 IconPark 图标（icon= 任意 iconType："
        "人 people、车 car、房 home、商店 shop…，iconpark_tool.py search 找；也可每部分一个列表），每个图标是一个可编辑元素，"
        "按部分依次填色、余下灰色；右侧占比大字与名称。整页正文区，不另加右栏；多于 4 部分或比较几年的构成用 stacked_columns。",
        """f = frame("每 100 位宠物主中，62 位已转向国产粮", page=6)
body = icon_grid(f, [("国产品牌", 62), ("外资品牌", 31)], icon="iconpark/Peoples/people.svg", rest="未固定品牌")
"""),
    "key_takeaways": (
        "右侧 2–4 条加粗结论 + 14pt 证据；左侧图、表或上下组合，用 body_w(f) 预留宽度。"
        "满高灰底不等于内容充实：条目过短换组合，不硬拉距；放不下删字不缩字。",
        """f = frame("规模增长，仍需关注转化", page=4)
ex = Exhibit(w=body_w(f), h=f.bottom - f.top)
r = columns(ex, ex.body, ["2021", "2022", "2023", "2024", "2025"], [("收入", [52, 61, 70, 84, 97], None)], focus="2025")
items = [("2025 年规模创新高", "收入 97 亿元，五年翻近一倍。"),            # 点名对象 + 引用图上的读数，不编号
         ("2023 年起提速", "2023 年 70 亿元，此后两年增速抬升。"), ("跟踪指标", "跟踪订单与收入转化。")]
body = key_takeaways(f, items)
""",
    ),
    "diagram_page": (
        "图 + 2–4 条要点的便捷模板，stats/parameters 中栏二选一、无需参数；自由组合与位置用 mixed_columns_page 的 image 模块。"
        "实体/品牌分析先搜官方技术参数、型号与结构参考，cutaway 工程剖面线稿用三分之四视角、白底、本页配色的深色轮廓/内部细线、"
        "浅灰排线及少量强调色，图内无文字；主要构造据已核资料，未知局部省略。"
        "示例 IMAGE_TOKEN/IMAGE_RATIO 为占位，发布前替换上传 token 与原图比例；部件名称用 callouts=(名称,x比例,y比例) "
        "放图外，以细引线连接，focus 标部件。"
        "caption 写“工程剖面示意图”，不编参数。示例部件/锚点仅演示，按资料及实际成图替换。",
        """f = frame("剖切结构帮助定位工艺改动，效果另由数据核对", page=4)
IMAGE_TOKEN, IMAGE_RATIO = "replace-with-uploaded-image-token", 1.3
items = [("结构定位", "主要层次由已核资料确认，未知局部省略。"),
         ("证据边界", "插画解释部件位置，不据此推算成本或性能。")]
body, slots = diagram_page(f, IMAGE_TOKEN, image_ratio=IMAGE_RATIO, items=items,
                          callouts=[("外壳", 0.12, 0.5), ("内部层", 0.8, 0.6)],
                          caption="工程剖面示意图")
""",
    ),
    "kpi_charts_page": (
        "上字下图：顶部 2–4 个大数字（指标·期间 / 数字 / 同比或口径），下方 1–2 张图并排铺满，不加底部结论条（结论写在标题）。"
        "适合业绩概览、量与利。图填 slots，不再用整页高覆盖 KPI。",
        """f = frame("量增不再抵消价跌：季度收入创新高，净利增速放缓", page=4)
kpis = [("26Q3 营收", "RMB165bn", "单季新高", 0), ("26Q3 归母净利", "RMB21bn", "环比 −9%", 1)]   # 第 4 项 = 取自哪张图
body, slots = kpi_charts_page(f, kpis, ["季度营收（RMB bn）", "季度归母净利（RMB bn）"])
frags = []
QUARTERS = ["25Q1", "25Q2", "25Q3", "25Q4", "26Q1", "26Q2", "26Q3"]
for box, vals in zip(slots, [[85, 94, 104, 141, 129, 148, 165], [14, 17, 19, 23, 21, 23, 21]]):
    ex = Exhibit(w=box[2], h=box[3]); columns(ex, ex.body, QUARTERS, [("值", vals, None)], cagr=(0, len(vals) - 1))
    frags.append(ex.to_slide(x=box[0], y=box[1], width=box[2]))
""",
    ),
    "columns_page": (
        "2–4 栏模型/参数：同构块按行对齐；icon（IconPark 名）、小标题、kv、note 可选。研究页至少一栏要 chart=（同口径小图），≤3 栏放图，"
        "只有文字和数字的对比改用 row_table。"
        "chart=(预留高度,标题)，有图栏的图区吸收区域余高，slots[i] 返回最终图区或 None；按 sx/sy/sw/sh 建 Exhibit(w=sw,h=sh)，"
        "用 ex.body 作图、to_slide(x=sx,y=sy)。一小图配稀疏指标时，用 mixed_columns_page 给图较宽一栏、证据块独立堆叠；"
        "短栏也可用 x/top/w/bottom 限定紧凑区域。保留全称/口径和正常间距，证据少可并页。",
        """f = frame("自供与锁定各有天花板：中立供应商的客户分散度最难复制", page=4)
cols = [dict(icon="car", kicker="垂直一体化 · 自供", title="比亚迪",
                kv=[("全球份额 1H26", "14.4%"), ("外供份额", "8%"), ("车型均价", "17.4 万")],
                chart=(120, "外供份额，%"), note="外供受自供优先级约束，集中在中低价车型。"),
           dict(icon="cooperative-handshake", kicker="单一绑定 · 锁定", title="松下",
                kv=[("经营利润率", "13.2%"), ("4680 成本", "$88.41/kWh"), ("对标成本", "$54.62/kWh")],
                chart=(120, "经营利润率，%"), note="客户与路线高度集中，利润率依赖补贴。"),
           dict(icon="world", kicker="中立供应 · 外部客户", title="宁德时代",
                kv=[("前十车企客户", "9 家"), ("最大客户占比", "13.7%"), ("切换敞口", "3–4%")],
                chart=(120, "前五客户占比，%"), note="最大客户 13.7%、前五 39%，分散度无可比。")]
body, slots = columns_page(f, cols, card=False)
frags = []
for box, (cats, vals) in zip(slots, [(["2024", "1H26"], [6, 8]), (["2024", "2025"], [11.8, 13.2]), (["2024", "2025"], [42, 39])]):
    ex = Exhibit(w=box[2], h=box[3]); columns(ex, ex.body, cats, [("值", vals, None)])
    frags.append(ex.to_slide(x=box[0], y=box[1]))
""",
    ),
    "mixed_columns_page": (
        "1–4 栏自由组合：image/chart/table/kv/steps/text/takeaways（独占一栏）；栏序决定左/中/右，blocks 顺序决定上/下，单栏整宽堆叠，x/top/w/bottom 限定区域。"
        "工程图是 image 基础模块，callouts/focus/caption 随图，配套内容按论点选，无需参数或要点。实体分析据已核结构画本页配色 cutaway；"
        "示例 token/ratio、部件锚点发布前按上传原图替换。slots[(栏号,key)] 是页面坐标，Exhibit 内用 ex.body，数据取 plan/research，不由图推效果。",
        """f = frame("冷却通道定位温控改动，成效另由实测数据验证", page=4)
IMAGE_TOKEN, IMAGE_RATIO = "replace-with-uploaded-image-token", 1.5
cols = [dict(blocks=[dict(kind="chart", key="performance", height=200, title="温控数据，采用已核记录口径"),
                       dict(kind="dots", items=["完整序列取 plan/research，插画不证明增长或因果。"])]),
           dict(blocks=[dict(kind="image", key="structure", src=IMAGE_TOKEN, ratio=IMAGE_RATIO, height=220,
                            callouts=[("外壳", 0.12, 0.5), ("冷却通道", 0.8, 0.6)], focus="冷却通道",
                            caption="工程剖面示意图")])]
body, slots = mixed_columns_page(f, cols, widths=[0.52, 0.48])
chart_box = slots[(0, "performance")]
""",
    ),
    "four_columns": (
        "four_columns 是版式别名，同构四栏调用 columns_page(..., card=True)，无同名函数。"
        "少量指标配一图时用 mixed_columns_page 独立堆叠（例），或用 top/bottom 限定紧凑栏区。不把方向性估计加总。",
        """page_frame = frame("投入增长不等于回报改善", page=4)
cols = [dict(blocks=[dict(kind="head", text="两期投入对比"),
                       dict(kind="chart", key="investment", height=220, title="投入金额（亿元，同口径）")]),
           dict(blocks=[dict(kind="head", text="运营证据"),
                       dict(kind="text", text="项目投产进度按已核资料列示，利用率另取运营数据。"),
                       dict(kind="head", text="回报口径"),
                       dict(kind="text", text="增量收益、投入成本及观察期间分别核对，回报率待口径齐备再算。")])]
body, slots = mixed_columns_page(page_frame, cols, widths=[0.6, 0.4])
chart_box = slots[(0, "investment")]
""",
    ),
}


def layout_help(name):
    description, code = PAGE_LAYOUTS[name]
    return (
        f"# {name} — 咨询整页版式\n{description}\n示例数据需替换为 plan/research 数据。\n```python\n{code}```\n"
        "组合：f.publish(body, frags=[图区片段...], deck=DECK, page=N, cwd=CWD, who=作者, layout=短描述, why=理由)。"
    )
