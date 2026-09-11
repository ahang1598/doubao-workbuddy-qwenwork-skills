"""
Chart 配色体系集合。

每个 style 提供 3+ 套 palette，可通过 name（如 "editorial_cream"）传入任意 make_* 函数：
    from gen_svg_charts import make_waterfall
    make_waterfall(steps, palette="editorial_cream")   # 传名字
    make_waterfall(steps, palette=PALETTES["editorial_cream"])  # 传 dict

统一字段（所有 18 张图共用）：
    ink       - 主墨色（文字/坐标轴/主柱/描边）
    accent    - 强调色（高亮点、pos 柱、关键 slice、主 series 深色）
    secondary - 次要色（对比色、rival 象限、neg 柱另一系、次 series 深色）
    bg        - 图表背景（默认透明，仅当 palette 有 bg 时才渲染背景色块）
    muted     - 中性灰（辅助文字、次刻度、图例文字）

派生字段由 chart 内部自动计算：grid = ink@12%，connect = ink@40%，等等。
"""

# ============================================================
# 学术研究（academic-research）：反常规高端；忌医院蓝/环保绿；
# 钛灰/档案纸/象牙纸背景 + 深墨主色 + 一个克制强调色
# ============================================================

PALETTE_ARCHIVE_INK = {
    # "档案纸底 · 铅墨黑主色 · 赭石强调"（历史/人文/档案研究）
    "ink":       "rgba(28,25,20,1)",       # 铅墨黑（略暖）
    "accent":    "rgba(163,88,50,1)",      # 赭石红（本色系原有主 accent）
    "secondary": "rgba(94,80,62,1)",       # 深棕灰
    "bg":        "rgba(241,233,218,1)",    # 档案纸 #F1E9DA
    "muted":     "rgba(94,80,62,0.6)",
}

PALETTE_IVORY_INDIGO = {
    # "象牙 + 深靛蓝"（人文社科 / 期刊风）
    "ink":       "rgba(22,32,72,1)",       # 深靛蓝
    "accent":    "rgba(180,60,50,1)",      # 深赭红
    "secondary": "rgba(120,130,155,1)",    # 雾蓝灰
    "bg":        "rgba(247,243,232,1)",    # 象牙纸 #F7F3E8
    "muted":     "rgba(80,90,110,0.65)",
}

PALETTE_TITANIUM_OLIVE = {
    # "钛灰 + 橄榄墨"（理工科答辩 / 会议报告）
    "ink":       "rgba(45,50,42,1)",       # 橄榄墨
    "accent":    "rgba(148,110,54,1)",     # 古铜金
    "secondary": "rgba(85,90,80,1)",       # 灰橄榄
    "bg":        "rgba(231,232,229,1)",    # 钛灰 #E7E8E5
    "muted":     "rgba(90,92,85,0.6)",
}

PALETTE_NIGHTLAB = {
    # "夜实验室"（数据科学 / 计算机科学论文）—— 深底
    "ink":       "rgba(240,240,232,1)",    # 象牙白正文
    "accent":    "rgba(212,233,44,1)",     # 荧光绿黄（数据强调）
    "secondary": "rgba(122,139,44,1)",     # 橄榄绿
    "bg":        "rgba(16,20,28,1)",       # 深靛底 #10141C
    "muted":     "rgba(184,188,194,0.7)",
}


# ============================================================
# 分析决策（strategy-and-analysis）：品牌主色 + 灰阶，一色主导
# 勃艮第/深酒红/赭石/深靛/墨青
# ============================================================

PALETTE_BURGUNDY_ANALYST = {
    # 头部咨询报告经典：勃艮第红 + 深墨 + 石灰
    "ink":       "rgba(30,25,28,1)",       # 深墨（略偏酒红）
    "accent":    "rgba(122,32,44,1)",      # 勃艮第 #7A202C
    "secondary": "rgba(60,55,58,1)",       # 石墨
    "bg":        "rgba(255,255,255,1)",
    "muted":     "rgba(90,88,90,0.65)",
}

PALETTE_INK_JADE = {
    # "墨青"：深靛蓝主色 + 玉青强调（金融 / 战略）
    "ink":       "rgba(20,35,60,1)",       # 深靛
    "accent":    "rgba(58,120,110,1)",     # 玉青 #3A786E
    "secondary": "rgba(90,105,125,1)",     # 靛灰
    "bg":        "rgba(255,255,255,1)",
    "muted":     "rgba(100,110,125,0.65)",
}

PALETTE_OCHRE_STONE = {
    # "赭石 + 石灰"：低饱和赭石主色（品牌研究 / 消费品）
    "ink":       "rgba(45,38,32,1)",       # 深棕墨
    "accent":    "rgba(174,120,54,1)",     # 焦赭石 #AE7836
    "secondary": "rgba(115,105,92,1)",     # 石棕
    "bg":        "rgba(250,247,242,1)",    # 象牙白
    "muted":     "rgba(120,110,100,0.65)",
}


# ============================================================
# 管理汇报（business-review）：品牌主色 + 灰阶；深稳克制；
# 暖白/雾灰/深墨蓝/墨黑
# ============================================================

PALETTE_EXEC_NAVY = {
    # "行政深靛"（董事会 / 财务 / OKR）
    "ink":       "rgba(22,40,60,1)",       # 深墨蓝 #16283C
    "accent":    "rgba(180,120,45,1)",     # 铜金强调
    "secondary": "rgba(74,90,110,1)",      # 蓝灰
    "bg":        "rgba(247,243,232,1)",    # 暖白 #F7F3E8
    "muted":     "rgba(100,108,120,0.65)",
}

PALETTE_SAGE_REVIEW = {
    # "鼠尾草 + 雾灰"（人力 / 行政 / 政务汇报 · 稳重亲和）
    "ink":       "rgba(38,45,42,1)",       # 深绿灰
    "accent":    "rgba(184,76,58,1)",      # 暖赤（强调达成/风险）
    "secondary": "rgba(115,138,120,1)",    # 鼠尾草绿
    "bg":        "rgba(236,234,228,1)",    # 浅石灰 #ECEAE4
    "muted":     "rgba(95,102,98,0.65)",
}

PALETTE_MOCHA_KPI = {
    # "摩卡棕 + 深底"（增长月报 · 硬核数字页）
    "ink":       "rgba(240,236,228,1)",    # 米白正文
    "accent":    "rgba(212,140,72,1)",     # 摩卡橘
    "secondary": "rgba(158,122,96,1)",     # 深摩卡
    "bg":        "rgba(26,26,32,1)",       # 墨黑 #1A1A20
    "muted":     "rgba(180,178,170,0.7)",
}


# ============================================================
# 商业提案（business-pitch）：大胆别致；戏剧性主角色
# 酒红/深墨绿/锈橙/葡萄紫/古铜金
# ============================================================

PALETTE_MERLOT_PITCH = {
    # "酒红戏剧"（融资 / 招商 · 巨字 + 单色戏剧）
    "ink":       "rgba(240,235,222,1)",    # 象牙正文
    "accent":    "rgba(148,42,58,1)",      # 酒红 Merlot
    "secondary": "rgba(180,140,86,1)",     # 古铜金辅助
    "bg":        "rgba(22,18,22,1)",       # 深墨底
    "muted":     "rgba(180,175,165,0.7)",
}

PALETTE_FOREST_LUXE = {
    # "深墨绿 + 古铜金"（高端消费品 / 奢侈品 / 品牌提案）
    "ink":       "rgba(238,235,228,1)",    # 象牙
    "accent":    "rgba(198,158,84,1)",     # 古铜金
    "secondary": "rgba(90,120,100,1)",     # 橄榄绿次色
    "bg":        "rgba(30,50,42,1)",       # 深墨绿 #1E322A
    "muted":     "rgba(180,180,170,0.7)",
}

PALETTE_RUST_TERRACOTTA = {
    # "锈橙 + 陶土"（工业设计 / 建材 / 制造业提案）
    "ink":       "rgba(38,30,26,1)",       # 深赭墨
    "accent":    "rgba(184,84,44,1)",      # 锈橙 #B8542C
    "secondary": "rgba(148,110,92,1)",     # 陶土
    "bg":        "rgba(246,240,228,1)",    # 米白
    "muted":     "rgba(120,105,95,0.65)",
}

PALETTE_GRAPE_ECLECTIC = {
    # "葡萄紫 + 象牙"（时尚 / 内容 / 女性向消费）
    "ink":       "rgba(38,28,42,1)",       # 深紫墨
    "accent":    "rgba(96,52,110,1)",      # 葡萄紫 #60346E
    "secondary": "rgba(180,145,110,1)",    # 米棕
    "bg":        "rgba(245,240,235,1)",    # 象牙
    "muted":     "rgba(110,95,115,0.65)",
}


# ============================================================
# 技术工程（technical-presentation）：主色 + 灰阶两级，最多三色
# 宝石蓝/松绿/深靛/深底荧光绿
# ============================================================

PALETTE_SAPPHIRE_DEV = {
    # "宝石蓝"（架构评审 / 研发汇报 · 参考 style 表原色）
    "ink":       "rgba(0,28,84,1)",        # #001C54
    "accent":    "rgba(0,112,186,1)",      # #0070BA
    "secondary": "rgba(71,85,105,1)",      # 深灰蓝正文 #475569
    "bg":        "rgba(255,255,255,1)",
    "muted":     "rgba(90,100,115,0.65)",
}

PALETTE_DEEP_INDIGO = {
    # "深靛蓝"（AI / 数据 / ML 论文级）
    "ink":       "rgba(13,19,38,1)",       # #0D1326
    "accent":    "rgba(37,99,235,1)",      # #2563EB
    "secondary": "rgba(83,97,116,1)",      # #536174
    "bg":        "rgba(242,244,248,1)",    # #F2F4F8
    "muted":     "rgba(100,110,130,0.65)",
}

PALETTE_TERMINAL_NEON = {
    # "深底荧光绿"（Terminal / DevOps / Security）
    "ink":       "rgba(240,242,239,1)",    # 象牙正文
    "accent":    "rgba(212,233,44,1)",     # 荧光绿黄 #D4E92C
    "secondary": "rgba(122,139,44,1)",     # 橄榄绿
    "bg":        "rgba(16,20,24,1)",       # 深底 #101418
    "muted":     "rgba(184,188,194,0.7)",
}

PALETTE_PINE_ENGINEERING = {
    # "松绿"（可持续工程 / 能源 / 环保基建）
    "ink":       "rgba(30,50,45,1)",
    "accent":    "rgba(76,122,90,1)",      # #4C7A5A
    "secondary": "rgba(115,138,125,1)",
    "bg":        "rgba(244,246,245,1)",    # #F4F6F5
    "muted":     "rgba(80,95,88,0.65)",
}


# ============================================================
# 品牌 / 创意展示（brand-storytelling）：单主色（材料世界）+ 中性轴 + 至多 1 强调
# 茶汤/木/石/陶/织物/金属/植物/土壤/机身漆面
# ============================================================

PALETTE_TEA_CEREMONY = {
    # "茶汤 + 陶土"（茶文化 / 生活方式 / 东方美学）
    "ink":       "rgba(38,32,26,1)",
    "accent":    "rgba(168,108,58,1)",     # 茶汤色 #A86C3A
    "secondary": "rgba(148,124,98,1)",     # 陶土
    "bg":        "rgba(244,237,224,1)",    # 米纸
    "muted":     "rgba(115,105,90,0.65)",
}

PALETTE_STONE_INK = {
    # "石与墨"（现代艺术 / 摄影集 / 空间设计）
    "ink":       "rgba(28,28,28,1)",       # 墨黑
    "accent":    "rgba(184,72,52,1)",      # 朱红点
    "secondary": "rgba(110,110,108,1)",    # 石灰
    "bg":        "rgba(238,236,230,1)",    # 石纸
    "muted":     "rgba(105,105,105,0.65)",
}

PALETTE_CANDLELIGHT = {
    # "烛光 + 深胡桃"（品牌故事夜幕篇 / 电影感）
    "ink":       "rgba(240,232,214,1)",    # 烛光米
    "accent":    "rgba(216,164,84,1)",     # 蜂蜡金
    "secondary": "rgba(140,100,68,1)",     # 深胡桃
    "bg":        "rgba(28,22,20,1)",       # 深胡桃底
    "muted":     "rgba(190,180,168,0.7)",
}

PALETTE_LINEN_PLUM = {
    # "亚麻 + 梅子"（女性向品牌 / 服装 / 内容）
    "ink":       "rgba(40,26,38,1)",
    "accent":    "rgba(122,52,80,1)",      # 梅紫
    "secondary": "rgba(148,120,98,1)",     # 亚麻棕
    "bg":        "rgba(246,240,230,1)",    # 亚麻底
    "muted":     "rgba(115,95,105,0.65)",
}


# ============================================================
# 教育培训 / 知识科普（learning-and-training）：主色梯度 + 中性灰 + 单强调色
# 亲和但不幼稚
# ============================================================

PALETTE_CLASSROOM_INDIGO = {
    # "学院靛蓝"（K12 / 大学课件 · 亲和不严肃）
    "ink":       "rgba(28,42,72,1)",
    "accent":    "rgba(220,120,60,1)",     # 亲橙
    "secondary": "rgba(110,130,170,1)",
    "bg":        "rgba(252,249,244,1)",    # 象牙白
    "muted":     "rgba(90,100,120,0.65)",
}

PALETTE_MEADOW_SCIENCE = {
    # "青草 + 象牙"（科普 / 生物 / 自然科学）
    "ink":       "rgba(32,45,38,1)",
    "accent":    "rgba(204,132,58,1)",     # 秋橙
    "secondary": "rgba(122,155,102,1)",    # 青草绿
    "bg":        "rgba(250,247,238,1)",
    "muted":     "rgba(90,105,90,0.65)",
}

PALETTE_CORAL_PATIENT = {
    # "珊瑚 + 米白"（患者教育 / 医学科普 · 亲和不冷）
    "ink":       "rgba(46,32,38,1)",
    "accent":    "rgba(210,90,86,1)",      # 珊瑚红
    "secondary": "rgba(160,110,105,1)",    # 玫瑚
    "bg":        "rgba(250,245,240,1)",
    "muted":     "rgba(115,95,95,0.65)",
}


# ============================================================
# 兜底（fallback）：莫兰迪 4 色
# ============================================================

PALETTE_MORANDI_WARM = {
    # 暖调莫兰迪
    "ink":       "rgba(58,52,48,1)",       # 深灰棕
    "accent":    "rgba(178,120,102,1)",    # 陶土粉
    "secondary": "rgba(148,138,120,1)",    # 灰米
    "bg":        "rgba(245,241,235,1)",
    "muted":     "rgba(120,110,100,0.65)",
}

PALETTE_MORANDI_COOL = {
    # 冷调莫兰迪
    "ink":       "rgba(48,52,58,1)",
    "accent":    "rgba(108,132,148,1)",    # 雾蓝
    "secondary": "rgba(138,144,142,1)",    # 石灰
    "bg":        "rgba(240,240,238,1)",
    "muted":     "rgba(115,120,125,0.65)",
}

PALETTE_MORANDI_MOSS = {
    # 苔藓莫兰迪
    "ink":       "rgba(45,50,42,1)",
    "accent":    "rgba(130,142,108,1)",    # 苔绿
    "secondary": "rgba(158,148,124,1)",    # 灰卡其
    "bg":        "rgba(242,240,232,1)",
    "muted":     "rgba(100,105,90,0.65)",
}


# ============================================================
# 统一注册表
# ============================================================

PALETTES = {
    # academic
    "archive_ink":     PALETTE_ARCHIVE_INK,
    "ivory_indigo":    PALETTE_IVORY_INDIGO,
    "titanium_olive":  PALETTE_TITANIUM_OLIVE,
    "nightlab":        PALETTE_NIGHTLAB,
    # strategy
    "burgundy_analyst": PALETTE_BURGUNDY_ANALYST,
    "ink_jade":         PALETTE_INK_JADE,
    "ochre_stone":      PALETTE_OCHRE_STONE,
    # business-review
    "exec_navy":       PALETTE_EXEC_NAVY,
    "sage_review":     PALETTE_SAGE_REVIEW,
    "mocha_kpi":       PALETTE_MOCHA_KPI,
    # business-pitch
    "merlot_pitch":     PALETTE_MERLOT_PITCH,
    "forest_luxe":      PALETTE_FOREST_LUXE,
    "rust_terracotta":  PALETTE_RUST_TERRACOTTA,
    "grape_eclectic":   PALETTE_GRAPE_ECLECTIC,
    # technical
    "sapphire_dev":     PALETTE_SAPPHIRE_DEV,
    "deep_indigo":      PALETTE_DEEP_INDIGO,
    "terminal_neon":    PALETTE_TERMINAL_NEON,
    "pine_engineering": PALETTE_PINE_ENGINEERING,
    # brand
    "tea_ceremony":    PALETTE_TEA_CEREMONY,
    "stone_ink":       PALETTE_STONE_INK,
    "candlelight":     PALETTE_CANDLELIGHT,
    "linen_plum":      PALETTE_LINEN_PLUM,
    # learning
    "classroom_indigo": PALETTE_CLASSROOM_INDIGO,
    "meadow_science":   PALETTE_MEADOW_SCIENCE,
    "coral_patient":    PALETTE_CORAL_PATIENT,
    # fallback / morandi
    "morandi_warm":     PALETTE_MORANDI_WARM,
    "morandi_cool":     PALETTE_MORANDI_COOL,
    "morandi_moss":     PALETTE_MORANDI_MOSS,
}

# style → 推荐 palette 列表（供 style 文档引用）
STYLE_PALETTES = {
    "academic-research":       ["archive_ink", "ivory_indigo", "titanium_olive", "nightlab"],
    "strategy-and-analysis":   ["burgundy_analyst", "ink_jade", "ochre_stone"],
    "business-review":         ["exec_navy", "sage_review", "mocha_kpi"],
    "business-pitch":          ["merlot_pitch", "forest_luxe", "rust_terracotta", "grape_eclectic"],
    "technical-presentation":  ["sapphire_dev", "deep_indigo", "terminal_neon", "pine_engineering"],
    "brand-storytelling":      ["tea_ceremony", "stone_ink", "candlelight", "linen_plum"],
    "learning-and-training":   ["classroom_indigo", "meadow_science", "coral_patient"],
    "fallback":                ["morandi_warm", "morandi_cool", "morandi_moss"],
}


def resolve_palette(p):
    """把用户传入的 palette 参数（name str / dict / None）统一解析为 dict。

    - None → None（chart 用默认硬编码色）
    - str  → 从 PALETTES 查表；找不到 raise ValueError
    - dict → 原样返回
    """
    if p is None or isinstance(p, dict):
        return p
    if isinstance(p, str):
        if p not in PALETTES:
            raise ValueError(
                f"palette '{p}' not found. Available: {sorted(PALETTES.keys())}"
            )
        return dict(PALETTES[p])
    raise TypeError(f"palette must be None / str / dict, got {type(p)}")

# ==== BEGIN AGENT-TUNED PALETTES (auto-generated) ====
# 由 fan-out sub-agent 优化后写回，覆盖上方 PALETTE_XXX 的 name 映射。
PALETTES['archive_ink'] = {
    'ink': 'rgba(28,25,20,1)',
    'accent': 'rgba(163,88,50,1)',
    'secondary': 'rgba(94,80,62,1)',
    'bg': 'rgba(241,233,218,1)',
    'muted': 'rgba(94,80,62,0.6)',
    'series': [
        'rgba(163,88,50,1)',
        'rgba(60,74,66,1)',
        'rgba(120,90,60,1)',
        'rgba(74,68,90,1)',
        'rgba(148,120,72,1)',
        'rgba(102,58,48,1)',
        'rgba(90,96,80,1)',
        'rgba(178,148,102,1)'
    ],
}

PALETTES['burgundy_analyst'] = {
    'ink': 'rgba(30,25,28,1)',
    'accent': 'rgba(122,32,44,1)',
    'secondary': 'rgba(60,55,58,1)',
    'bg': 'rgba(255,255,255,1)',
    'muted': 'rgba(90,88,90,0.65)',
    'series': [
        'rgba(122,32,44,1)',
        'rgba(60,55,58,1)',
        'rgba(150,120,70,1)',
        'rgba(70,95,100,1)',
        'rgba(170,90,70,1)',
        'rgba(110,105,95,1)'
    ],
}

PALETTES['candlelight'] = {
    'ink': 'rgba(240,232,214,1)',
    'accent': 'rgba(232,172,80,1)',
    'secondary': 'rgba(150,110,72,1)',
    'bg': 'rgba(28,22,20,1)',
    'muted': 'rgba(190,180,168,0.7)',
    'series': [
        'rgba(232,172,80,1)',
        'rgba(110,140,150,1)',
        'rgba(200,90,70,1)',
        'rgba(180,130,72,1)',
        'rgba(150,140,90,1)',
        'rgba(120,95,140,1)',
        'rgba(210,190,150,1)'
    ],
}

PALETTES['classroom_indigo'] = {
    'ink': 'rgba(28,42,72,1)',
    'accent': 'rgba(220,120,60,1)',
    'secondary': 'rgba(110,130,170,1)',
    'bg': 'rgba(252,249,244,1)',
    'muted': 'rgba(90,100,120,0.65)',
    'series': [
        'rgba(28,42,72,1)',
        'rgba(220,120,60,1)',
        'rgba(110,130,170,1)',
        'rgba(78,148,150,1)',
        'rgba(198,168,92,1)',
        'rgba(160,110,150,1)',
        'rgba(60,90,130,1)',
        'rgba(180,196,210,1)'
    ],
}

PALETTES['coral_patient'] = {
    'ink': 'rgba(46,32,38,1)',
    'accent': 'rgba(210,90,86,1)',
    'secondary': 'rgba(160,110,105,1)',
    'bg': 'rgba(250,245,240,1)',
    'muted': 'rgba(115,95,95,0.65)',
    'series': [
        'rgba(210,90,86,1)',
        'rgba(160,110,105,1)',
        'rgba(232,168,140,1)',
        'rgba(180,140,120,1)',
        'rgba(196,88,72,1)',
        'rgba(220,180,150,1)',
        'rgba(140,96,92,1)',
        'rgba(238,206,180,1)'
    ],
}

PALETTES['deep_indigo'] = {
    'ink': 'rgba(15,23,42,1)',
    'accent': 'rgba(67,56,202,1)',
    'secondary': 'rgba(71,85,105,1)',
    'bg': 'rgba(243,244,248,1)',
    'muted': 'rgba(100,116,139,0.6)',
    'series': [
        'rgba(67,56,202,1)',
        'rgba(14,116,144,1)',
        'rgba(120,113,178,1)',
        'rgba(71,85,105,1)',
        'rgba(51,65,120,1)',
        'rgba(148,163,199,1)',
        'rgba(30,64,175,1)',
        'rgba(180,190,215,1)'
    ],
}

PALETTES['exec_navy'] = {
    'ink': 'rgba(22,40,60,1)',
    'accent': 'rgba(180,120,45,1)',
    'secondary': 'rgba(74,90,110,1)',
    'bg': 'rgba(247,243,232,1)',
    'muted': 'rgba(100,108,120,0.65)',
    'series': [
        'rgba(22,40,60,1)',
        'rgba(180,120,45,1)',
        'rgba(74,90,110,1)',
        'rgba(140,120,90,1)',
        'rgba(58,90,110,1)',
        'rgba(198,168,120,1)',
        'rgba(120,132,148,1)',
        'rgba(90,72,52,1)'
    ],
}

PALETTES['forest_luxe'] = {
    'ink': 'rgba(238,235,228,1)',
    'accent': 'rgba(198,158,84,1)',
    'secondary': 'rgba(90,120,100,1)',
    'bg': 'rgba(30,50,42,1)',
    'muted': 'rgba(180,180,170,0.7)',
    'series': [
        'rgba(198,158,84,0.92)',
        'rgba(160,120,60,0.92)',
        'rgba(120,150,120,0.88)',
        'rgba(210,195,160,0.90)',
        'rgba(90,120,100,0.90)',
        'rgba(230,215,180,0.88)'
    ],
}

PALETTES['grape_eclectic'] = {
    'ink': 'rgba(38,28,42,1)',
    'accent': 'rgba(96,52,110,1)',
    'secondary': 'rgba(180,145,110,1)',
    'bg': 'rgba(245,240,235,1)',
    'muted': 'rgba(110,95,115,0.65)',
    'series': [
        'rgba(96,52,110,1)',
        'rgba(180,145,110,1)',
        'rgba(168,120,150,1)',
        'rgba(128,102,72,1)',
        'rgba(60,32,72,1)',
        'rgba(196,168,140,1)',
        'rgba(140,90,120,1)',
        'rgba(82,72,90,1)'
    ],
}

PALETTES['ink_jade'] = {
    'ink': 'rgba(20,35,60,1)',
    'accent': 'rgba(58,120,110,1)',
    'secondary': 'rgba(90,105,125,1)',
    'bg': 'rgba(255,255,255,1)',
    'muted': 'rgba(100,110,125,0.65)',
    'series': [
        'rgba(20,35,60,1)',
        'rgba(58,120,110,1)',
        'rgba(90,105,125,1)',
        'rgba(120,165,155,1)',
        'rgba(45,80,95,1)',
        'rgba(160,180,175,1)',
        'rgba(75,95,120,1)'
    ],
}

PALETTES['ivory_indigo'] = {
    'ink': 'rgba(22,32,72,1)',
    'accent': 'rgba(158,52,44,1)',
    'secondary': 'rgba(120,130,155,1)',
    'bg': 'rgba(247,243,232,1)',
    'muted': 'rgba(80,90,110,0.65)',
    'series': [
        'rgba(22,32,72,1)',
        'rgba(158,52,44,1)',
        'rgba(120,130,155,1)',
        'rgba(58,110,102,1)',
        'rgba(168,138,72,1)',
        'rgba(92,72,110,1)',
        'rgba(72,92,120,1)',
        'rgba(140,102,86,1)'
    ],
}

PALETTES['linen_plum'] = {
    'ink': 'rgba(40,26,38,1)',
    'accent': 'rgba(122,52,80,1)',
    'secondary': 'rgba(168,132,110,1)',
    'bg': 'rgba(246,240,230,1)',
    'muted': 'rgba(115,95,105,0.65)',
    'series': [
        'rgba(122,52,80,1)',
        'rgba(168,132,110,1)',
        'rgba(178,130,146,1)',
        'rgba(210,180,158,1)',
        'rgba(90,60,74,1)',
        'rgba(148,100,120,1)',
        'rgba(228,208,190,1)',
        'rgba(74,50,62,1)'
    ],
}

PALETTES['meadow_science'] = {
    'ink': 'rgba(32,45,38,1)',
    'accent': 'rgba(204,132,58,1)',
    'secondary': 'rgba(122,155,102,1)',
    'bg': 'rgba(250,247,238,1)',
    'muted': 'rgba(90,105,90,0.65)',
    'series': [
        'rgba(122,155,102,1)',
        'rgba(204,132,58,1)',
        'rgba(78,120,86,1)',
        'rgba(219,178,96,1)',
        'rgba(160,180,120,1)',
        'rgba(155,95,50,1)',
        'rgba(200,210,170,1)',
        'rgba(120,140,90,1)'
    ],
}

PALETTES['merlot_pitch'] = {
    'ink': 'rgba(240,235,222,1)',
    'accent': 'rgba(148,42,58,1)',
    'secondary': 'rgba(180,140,86,1)',
    'bg': 'rgba(22,18,22,1)',
    'muted': 'rgba(180,175,165,0.7)',
    'series': [
        'rgba(148,42,58,1)',
        'rgba(180,140,86,1)',
        'rgba(196,110,96,1)',
        'rgba(112,52,64,1)',
        'rgba(214,182,140,1)',
        'rgba(90,32,44,1)'
    ],
}

PALETTES['mocha_kpi'] = {
    'ink': 'rgba(240,236,228,1)',
    'accent': 'rgba(212,140,72,1)',
    'secondary': 'rgba(158,122,96,1)',
    'bg': 'rgba(26,26,32,1)',
    'muted': 'rgba(180,178,170,0.7)',
    'series': [
        'rgba(212,140,72,1)',
        'rgba(230,196,150,1)',
        'rgba(198,110,80,1)',
        'rgba(158,122,96,1)',
        'rgba(240,220,190,1)',
        'rgba(180,90,60,1)',
        'rgba(210,170,130,1)',
        'rgba(140,100,80,1)'
    ],
}

PALETTES['morandi_cool'] = {
    'ink': 'rgba(48,52,58,1)',
    'accent': 'rgba(108,132,148,1)',
    'secondary': 'rgba(128,142,146,1)',
    'bg': 'rgba(240,240,238,1)',
    'muted': 'rgba(115,120,125,0.65)',
    'series': [
        'rgba(108,132,148,1)',
        'rgba(128,142,146,1)',
        'rgba(148,158,152,1)',
        'rgba(162,152,162,1)',
        'rgba(92,116,132,1)',
        'rgba(178,172,168,1)'
    ],
}

PALETTES['morandi_moss'] = {
    'ink': 'rgba(45,50,42,1)',
    'accent': 'rgba(130,142,108,1)',
    'secondary': 'rgba(158,148,124,1)',
    'bg': 'rgba(242,240,232,1)',
    'muted': 'rgba(100,105,90,0.65)',
    'series': [
        'rgba(130,142,108,1)',
        'rgba(158,148,124,1)',
        'rgba(96,112,90,1)',
        'rgba(188,178,150,1)',
        'rgba(118,128,118,1)',
        'rgba(172,164,132,1)',
        'rgba(78,92,72,1)',
        'rgba(200,196,180,1)'
    ],
}

PALETTES['morandi_warm'] = {
    'ink': 'rgba(58,52,48,1)',
    'accent': 'rgba(178,120,102,1)',
    'secondary': 'rgba(148,138,120,1)',
    'bg': 'rgba(245,241,235,1)',
    'muted': 'rgba(120,110,100,0.65)',
    'series': [
        'rgba(178,120,102,1)',
        'rgba(148,138,120,1)',
        'rgba(196,168,140,1)',
        'rgba(158,128,118,1)',
        'rgba(184,158,130,1)',
        'rgba(132,120,108,1)',
        'rgba(206,178,152,1)',
        'rgba(168,140,124,1)'
    ],
}

PALETTES['nightlab'] = {
    'ink': 'rgba(240,240,232,1)',
    'accent': 'rgba(212,233,44,1)',
    'secondary': 'rgba(96,140,190,1)',
    'bg': 'rgba(16,20,28,1)',
    'muted': 'rgba(190,194,200,0.75)',
    'series': [
        'rgba(212,233,44,1)',
        'rgba(96,140,190,1)',
        'rgba(240,240,232,1)',
        'rgba(180,150,210,1)',
        'rgba(230,150,80,1)'
    ],
}

PALETTES['ochre_stone'] = {
    'ink': 'rgba(45,38,32,1)',
    'accent': 'rgba(174,120,54,1)',
    'secondary': 'rgba(115,105,92,1)',
    'bg': 'rgba(250,247,242,1)',
    'muted': 'rgba(120,110,100,0.65)',
    'series': [
        'rgba(174,120,54,1)',
        'rgba(115,105,92,1)',
        'rgba(210,168,110,1)',
        'rgba(90,72,54,1)',
        'rgba(160,148,132,1)',
        'rgba(138,86,40,1)',
        'rgba(196,182,158,1)'
    ],
}

PALETTES['pine_engineering'] = {
    'ink': 'rgba(30,50,45,1)',
    'accent': 'rgba(76,122,90,1)',
    'secondary': 'rgba(115,138,125,1)',
    'bg': 'rgba(244,246,245,1)',
    'muted': 'rgba(80,95,88,0.65)',
    'series': [
        'rgba(76,122,90,1)',
        'rgba(150,170,135,1)',
        'rgba(58,92,96,1)',
        'rgba(178,160,110,1)',
        'rgba(115,138,125,1)',
        'rgba(94,110,72,1)',
        'rgba(160,124,88,1)',
        'rgba(200,205,190,1)'
    ],
}

PALETTES['rust_terracotta'] = {
    'ink': 'rgba(38,30,26,1)',
    'accent': 'rgba(184,84,44,1)',
    'secondary': 'rgba(148,110,92,1)',
    'bg': 'rgba(246,240,228,1)',
    'muted': 'rgba(120,105,95,0.65)',
    'series': [
        'rgba(184,84,44,1)',
        'rgba(148,110,92,1)',
        'rgba(96,66,52,1)',
        'rgba(202,148,96,1)',
        'rgba(92,104,102,1)',
        'rgba(58,50,44,1)',
        'rgba(168,132,80,1)',
        'rgba(128,72,52,1)'
    ],
}

PALETTES['sage_review'] = {
    'ink': 'rgba(38,45,42,1)',
    'accent': 'rgba(184,76,58,1)',
    'secondary': 'rgba(115,138,120,1)',
    'bg': 'rgba(236,234,228,1)',
    'muted': 'rgba(95,102,98,0.65)',
    'series': [
        'rgba(115,138,120,1)',
        'rgba(184,76,58,1)',
        'rgba(78,102,92,1)',
        'rgba(158,142,110,1)',
        'rgba(108,120,132,1)',
        'rgba(160,180,158,1)',
        'rgba(140,96,80,1)'
    ],
}

PALETTES['sapphire_dev'] = {
    'ink': 'rgba(0,28,84,1)',
    'accent': 'rgba(0,112,186,1)',
    'secondary': 'rgba(71,85,105,1)',
    'bg': 'rgba(255,255,255,1)',
    'muted': 'rgba(90,100,115,0.65)',
    'series': [
        'rgba(0,28,84,1)',
        'rgba(0,112,186,1)',
        'rgba(56,146,213,1)',
        'rgba(120,182,225,1)',
        'rgba(71,85,105,1)',
        'rgba(148,163,184,1)',
        'rgba(30,58,138,1)',
        'rgba(14,116,144,1)'
    ],
}

PALETTES['stone_ink'] = {
    'ink': 'rgba(28,28,28,1)',
    'accent': 'rgba(184,72,52,1)',
    'secondary': 'rgba(110,110,108,1)',
    'bg': 'rgba(238,236,230,1)',
    'muted': 'rgba(105,105,105,0.65)',
    'series': [
        'rgba(184,72,52,1)',
        'rgba(60,58,54,1)',
        'rgba(150,148,140,1)',
        'rgba(96,94,88,1)',
        'rgba(200,140,88,1)',
        'rgba(130,60,50,1)',
        'rgba(180,178,168,1)',
        'rgba(78,76,72,1)'
    ],
}

PALETTES['tea_ceremony'] = {
    'ink': 'rgba(38,32,26,1)',
    'accent': 'rgba(168,108,58,1)',
    'secondary': 'rgba(148,124,98,1)',
    'bg': 'rgba(244,237,224,1)',
    'muted': 'rgba(115,105,90,0.65)',
    'series': [
        'rgba(168,108,58,1)',
        'rgba(120,140,110,1)',
        'rgba(148,124,98,1)',
        'rgba(196,150,92,1)',
        'rgba(96,72,54,1)',
        'rgba(180,86,58,1)',
        'rgba(108,124,120,1)',
        'rgba(212,182,132,1)'
    ],
}

PALETTES['terminal_neon'] = {
    'ink': 'rgba(224,240,208,1)',
    'accent': 'rgba(190,255,60,1)',
    'secondary': 'rgba(110,220,140,1)',
    'bg': 'rgba(14,20,18,1)',
    'muted': 'rgba(150,180,150,0.7)',
    'series': [
        'rgba(190,255,60,1)',
        'rgba(80,220,140,1)',
        'rgba(60,220,210,1)',
        'rgba(230,255,120,1)',
        'rgba(140,190,90,1)',
        'rgba(180,230,180,1)',
        'rgba(100,160,110,1)',
        'rgba(220,240,180,1)'
    ],
}

PALETTES['titanium_olive'] = {
    'ink': 'rgba(45,50,42,1)',
    'accent': 'rgba(140,112,72,1)',
    'secondary': 'rgba(85,90,80,1)',
    'bg': 'rgba(231,232,229,1)',
    'muted': 'rgba(90,92,85,0.6)',
    'series': [
        'rgba(140,112,72,1)',
        'rgba(85,90,80,1)',
        'rgba(112,124,88,1)',
        'rgba(158,138,102,1)',
        'rgba(76,80,68,1)',
        'rgba(180,168,130,1)',
        'rgba(120,100,70,1)',
        'rgba(96,110,84,1)'
    ],
}

# ==== END AGENT-TUNED PALETTES ====

# ============================================================
# BRIGHT VARIANTS（明亮版）· 28 个 *_bright palette
# ============================================================
#
# 原则：保留 bg / ink / muted 不动，只把 accent 与 series 的
# 饱和度和亮度往上推 10-20%。适合投屏、PPT 演示、需要视觉冲击
# 的场景。稳重印刷体裁请继续用原版。
#
# 三种策略：
# - 白底组（bg 近白）: 用中饱和度深亮色 accent，避免刺眼
#   例：burgundy_analyst_bright / ink_jade_bright
# - 浅底组（米/象牙/石纸底）: 多色高饱和 series，甜蜜区
#   例：classroom_indigo_bright / archive_ink_bright
# - 深底组（深墨/深绿/深靛底）: 亮色在深底上跳，可上荧光
#   例：merlot_pitch_bright / forest_luxe_bright
#
# 用法与原版一致：make_xxx(..., palette='sankey_bright') 或 直接
# 传 dict。也可从 STYLE_PALETTES_BRIGHT 里按场景取。
PALETTES['archive_ink_bright'] = {
    'ink': 'rgba(28,25,20,1)',
    'accent': 'rgba(220,110,50,1)',
    'secondary': 'rgba(90,140,160,1)',
    'bg': 'rgba(241,233,218,1)',
    'muted': 'rgba(94,80,62,0.6)',
    'series': [
        'rgba(220,110,50,1)',
        'rgba(90,140,160,1)',
        'rgba(200,160,60,1)',
        'rgba(140,80,170,1)',
        'rgba(80,160,110,1)',
        'rgba(210,90,110,1)',
        'rgba(180,140,90,1)',
        'rgba(100,120,180,1)',
    ],
}

PALETTES['ivory_indigo_bright'] = {
    'ink': 'rgba(22,32,72,1)',
    'accent': 'rgba(220,60,50,1)',
    'secondary': 'rgba(60,110,180,1)',
    'bg': 'rgba(247,243,232,1)',
    'muted': 'rgba(80,90,110,0.6)',
    'series': [
        'rgba(220,60,50,1)',
        'rgba(60,110,180,1)',
        'rgba(230,150,50,1)',
        'rgba(70,160,140,1)',
        'rgba(150,80,180,1)',
        'rgba(240,190,60,1)',
        'rgba(220,110,140,1)',
        'rgba(100,140,60,1)',
    ],
}

PALETTES['titanium_olive_bright'] = {
    'ink': 'rgba(45,50,42,1)',
    'accent': 'rgba(220,170,80,1)',
    'secondary': 'rgba(160,190,110,1)',
    'bg': 'rgba(231,232,229,1)',
    'muted': 'rgba(90,92,85,0.6)',
    'series': [
        'rgba(220,170,80,1)',
        'rgba(160,190,110,1)',
        'rgba(90,150,190,1)',
        'rgba(220,120,90,1)',
        'rgba(160,110,190,1)',
        'rgba(220,200,140,1)',
        'rgba(90,180,140,1)',
        'rgba(210,90,110,1)',
    ],
}

PALETTES['nightlab_bright'] = {
    'ink': 'rgba(240,240,232,1)',
    'accent': 'rgba(220,240,80,1)',
    'secondary': 'rgba(140,180,220,1)',
    'bg': 'rgba(16,20,28,1)',
    'muted': 'rgba(190,194,200,0.7)',
    'series': [
        'rgba(220,240,80,1)',
        'rgba(140,180,220,1)',
        'rgba(240,180,110,1)',
        'rgba(200,150,220,1)',
        'rgba(120,220,180,1)',
        'rgba(240,140,140,1)',
        'rgba(180,220,140,1)',
        'rgba(240,220,140,1)',
    ],
}

PALETTES['burgundy_analyst_bright'] = {
    'ink': 'rgba(30,25,28,1)',
    'accent': 'rgba(180,50,70,1)',
    'secondary': 'rgba(80,110,150,1)',
    'bg': 'rgba(255,255,255,1)',
    'muted': 'rgba(90,88,90,0.65)',
    'series': [
        'rgba(180,50,70,1)',
        'rgba(80,110,150,1)',
        'rgba(200,140,60,1)',
        'rgba(70,140,120,1)',
        'rgba(160,90,150,1)',
        'rgba(200,180,80,1)',
        'rgba(130,130,140,1)',
        'rgba(210,110,90,1)',
    ],
}

PALETTES['ink_jade_bright'] = {
    'ink': 'rgba(20,35,60,1)',
    'accent': 'rgba(50,170,150,1)',
    'secondary': 'rgba(70,130,180,1)',
    'bg': 'rgba(255,255,255,1)',
    'muted': 'rgba(100,110,125,0.65)',
    'series': [
        'rgba(50,170,150,1)',
        'rgba(70,130,180,1)',
        'rgba(200,110,70,1)',
        'rgba(140,100,180,1)',
        'rgba(200,170,60,1)',
        'rgba(100,170,90,1)',
        'rgba(230,130,140,1)',
        'rgba(90,150,170,1)',
    ],
}

PALETTES['ochre_stone_bright'] = {
    'ink': 'rgba(45,38,32,1)',
    'accent': 'rgba(220,150,60,1)',
    'secondary': 'rgba(180,120,90,1)',
    'bg': 'rgba(250,247,242,1)',
    'muted': 'rgba(120,110,100,0.6)',
    'series': [
        'rgba(220,150,60,1)',
        'rgba(180,120,90,1)',
        'rgba(230,90,80,1)',
        'rgba(90,150,180,1)',
        'rgba(200,180,80,1)',
        'rgba(150,100,180,1)',
        'rgba(240,190,140,1)',
        'rgba(80,160,120,1)',
    ],
}

PALETTES['exec_navy_bright'] = {
    'ink': 'rgba(22,40,60,1)',
    'accent': 'rgba(230,150,60,1)',
    'secondary': 'rgba(80,130,190,1)',
    'bg': 'rgba(247,243,232,1)',
    'muted': 'rgba(100,108,120,0.65)',
    'series': [
        'rgba(230,150,60,1)',
        'rgba(80,130,190,1)',
        'rgba(210,80,80,1)',
        'rgba(70,160,140,1)',
        'rgba(180,130,200,1)',
        'rgba(220,190,90,1)',
        'rgba(200,120,140,1)',
        'rgba(120,170,90,1)',
    ],
}

PALETTES['sage_review_bright'] = {
    'ink': 'rgba(38,45,42,1)',
    'accent': 'rgba(230,90,70,1)',
    'secondary': 'rgba(150,190,140,1)',
    'bg': 'rgba(236,234,228,1)',
    'muted': 'rgba(95,102,98,0.65)',
    'series': [
        'rgba(150,190,140,1)',
        'rgba(230,90,70,1)',
        'rgba(90,150,170,1)',
        'rgba(220,180,90,1)',
        'rgba(180,130,190,1)',
        'rgba(200,170,140,1)',
        'rgba(240,130,100,1)',
        'rgba(100,170,120,1)',
    ],
}

PALETTES['mocha_kpi_bright'] = {
    'ink': 'rgba(240,236,228,1)',
    'accent': 'rgba(240,160,80,1)',
    'secondary': 'rgba(220,190,150,1)',
    'bg': 'rgba(26,26,32,1)',
    'muted': 'rgba(180,178,170,0.7)',
    'series': [
        'rgba(240,160,80,1)',
        'rgba(240,200,120,1)',
        'rgba(230,110,90,1)',
        'rgba(150,200,220,1)',
        'rgba(220,140,190,1)',
        'rgba(180,220,150,1)',
        'rgba(200,170,240,1)',
        'rgba(240,180,110,1)',
    ],
}

PALETTES['merlot_pitch_bright'] = {
    'ink': 'rgba(240,235,222,1)',
    'accent': 'rgba(230,90,130,1)',
    'secondary': 'rgba(230,180,110,1)',
    'bg': 'rgba(22,18,22,1)',
    'muted': 'rgba(180,175,165,0.7)',
    'series': [
        'rgba(230,90,130,1)',
        'rgba(255,180,80,1)',
        'rgba(140,200,255,1)',
        'rgba(100,220,180,1)',
        'rgba(255,120,150,1)',
        'rgba(200,150,255,1)',
        'rgba(255,220,120,1)',
        'rgba(120,240,200,1)',
    ],
}

PALETTES['forest_luxe_bright'] = {
    'ink': 'rgba(238,235,228,1)',
    'accent': 'rgba(230,190,110,1)',
    'secondary': 'rgba(150,200,160,1)',
    'bg': 'rgba(30,50,42,1)',
    'muted': 'rgba(180,180,170,0.7)',
    'series': [
        'rgba(230,190,110,1)',
        'rgba(150,200,160,1)',
        'rgba(230,150,100,1)',
        'rgba(180,220,220,1)',
        'rgba(220,180,220,1)',
        'rgba(240,220,140,1)',
        'rgba(180,150,220,1)',
        'rgba(240,180,140,1)',
    ],
}

PALETTES['rust_terracotta_bright'] = {
    'ink': 'rgba(38,30,26,1)',
    'accent': 'rgba(230,110,60,1)',
    'secondary': 'rgba(200,160,110,1)',
    'bg': 'rgba(246,240,228,1)',
    'muted': 'rgba(120,105,95,0.65)',
    'series': [
        'rgba(230,110,60,1)',
        'rgba(200,160,110,1)',
        'rgba(230,180,80,1)',
        'rgba(80,150,180,1)',
        'rgba(180,80,110,1)',
        'rgba(140,180,100,1)',
        'rgba(150,110,190,1)',
        'rgba(220,140,150,1)',
    ],
}

PALETTES['grape_eclectic_bright'] = {
    'ink': 'rgba(38,28,42,1)',
    'accent': 'rgba(160,80,190,1)',
    'secondary': 'rgba(230,150,110,1)',
    'bg': 'rgba(245,240,235,1)',
    'muted': 'rgba(110,95,115,0.65)',
    'series': [
        'rgba(160,80,190,1)',
        'rgba(230,150,110,1)',
        'rgba(230,120,180,1)',
        'rgba(90,160,180,1)',
        'rgba(240,180,80,1)',
        'rgba(220,90,120,1)',
        'rgba(140,180,110,1)',
        'rgba(100,120,200,1)',
    ],
}

PALETTES['sapphire_dev_bright'] = {
    'ink': 'rgba(0,28,84,1)',
    'accent': 'rgba(30,144,255,1)',
    'secondary': 'rgba(59,130,246,1)',
    'bg': 'rgba(255,255,255,1)',
    'muted': 'rgba(100,116,139,0.7)',
    'series': [
        'rgba(30,144,255,1)',
        'rgba(6,182,212,1)',
        'rgba(139,92,246,1)',
        'rgba(59,130,246,1)',
        'rgba(14,165,233,1)',
        'rgba(37,99,235,1)',
        'rgba(96,165,250,1)',
        'rgba(147,197,253,1)',
    ],
}

PALETTES['deep_indigo_bright'] = {
    'ink': 'rgba(13,19,38,1)',
    'accent': 'rgba(90,110,240,1)',
    'secondary': 'rgba(180,100,220,1)',
    'bg': 'rgba(242,244,248,1)',
    'muted': 'rgba(100,110,130,0.65)',
    'series': [
        'rgba(90,110,240,1)',
        'rgba(180,100,220,1)',
        'rgba(30,180,200,1)',
        'rgba(240,120,90,1)',
        'rgba(120,200,140,1)',
        'rgba(240,190,60,1)',
        'rgba(230,100,180,1)',
        'rgba(80,160,240,1)',
    ],
}

PALETTES['terminal_neon_bright'] = {
    'ink': 'rgba(224,240,208,1)',
    'accent': 'rgba(190,255,60,1)',
    'secondary': 'rgba(0,255,200,1)',
    'bg': 'rgba(14,20,18,1)',
    'muted': 'rgba(150,180,150,0.7)',
    'series': [
        'rgba(190,255,60,1)',
        'rgba(0,255,200,1)',
        'rgba(80,220,255,1)',
        'rgba(255,220,80,1)',
        'rgba(255,120,180,1)',
        'rgba(180,120,255,1)',
        'rgba(255,180,80,1)',
        'rgba(130,255,180,1)',
    ],
}

PALETTES['pine_engineering_bright'] = {
    'ink': 'rgba(30,50,45,1)',
    'accent': 'rgba(90,170,110,1)',
    'secondary': 'rgba(220,180,90,1)',
    'bg': 'rgba(244,246,245,1)',
    'muted': 'rgba(80,95,88,0.65)',
    'series': [
        'rgba(90,170,110,1)',
        'rgba(220,180,90,1)',
        'rgba(80,150,200,1)',
        'rgba(220,120,80,1)',
        'rgba(150,120,190,1)',
        'rgba(200,190,140,1)',
        'rgba(230,90,110,1)',
        'rgba(120,190,180,1)',
    ],
}

PALETTES['tea_ceremony_bright'] = {
    'ink': 'rgba(38,32,26,1)',
    'accent': 'rgba(220,140,60,1)',
    'secondary': 'rgba(160,180,110,1)',
    'bg': 'rgba(244,237,224,1)',
    'muted': 'rgba(115,105,90,0.6)',
    'series': [
        'rgba(220,140,60,1)',
        'rgba(160,180,110,1)',
        'rgba(210,90,70,1)',
        'rgba(230,200,90,1)',
        'rgba(90,140,150,1)',
        'rgba(180,120,180,1)',
        'rgba(230,170,130,1)',
        'rgba(80,170,110,1)',
    ],
}

PALETTES['stone_ink_bright'] = {
    'ink': 'rgba(28,28,28,1)',
    'accent': 'rgba(230,90,60,1)',
    'secondary': 'rgba(180,180,180,1)',
    'bg': 'rgba(238,236,230,1)',
    'muted': 'rgba(105,105,105,0.65)',
    'series': [
        'rgba(230,90,60,1)',
        'rgba(180,180,180,1)',
        'rgba(230,180,90,1)',
        'rgba(90,140,180,1)',
        'rgba(170,90,180,1)',
        'rgba(230,140,90,1)',
        'rgba(100,180,140,1)',
        'rgba(230,130,150,1)',
    ],
}

PALETTES['candlelight_bright'] = {
    'ink': 'rgba(240,232,214,1)',
    'accent': 'rgba(240,180,90,1)',
    'secondary': 'rgba(220,140,90,1)',
    'bg': 'rgba(28,22,20,1)',
    'muted': 'rgba(190,180,168,0.7)',
    'series': [
        'rgba(240,180,90,1)',
        'rgba(220,140,90,1)',
        'rgba(230,100,100,1)',
        'rgba(180,210,190,1)',
        'rgba(220,170,220,1)',
        'rgba(240,220,150,1)',
        'rgba(160,190,230,1)',
        'rgba(240,150,160,1)',
    ],
}

PALETTES['linen_plum_bright'] = {
    'ink': 'rgba(40,26,38,1)',
    'accent': 'rgba(180,80,120,1)',
    'secondary': 'rgba(220,160,130,1)',
    'bg': 'rgba(246,240,230,1)',
    'muted': 'rgba(115,95,105,0.6)',
    'series': [
        'rgba(180,80,120,1)',
        'rgba(230,160,130,1)',
        'rgba(220,110,160,1)',
        'rgba(140,110,200,1)',
        'rgba(240,180,100,1)',
        'rgba(90,170,180,1)',
        'rgba(230,80,90,1)',
        'rgba(170,190,110,1)',
    ],
}

PALETTES['classroom_indigo_bright'] = {
    'ink': 'rgba(28,42,72,1)',
    'accent': 'rgba(255,140,50,1)',
    'secondary': 'rgba(60,130,220,1)',
    'bg': 'rgba(252,249,244,1)',
    'muted': 'rgba(90,100,120,0.6)',
    'series': [
        'rgba(255,140,50,1)',
        'rgba(40,130,220,1)',
        'rgba(60,180,120,1)',
        'rgba(230,60,90,1)',
        'rgba(140,90,220,1)',
        'rgba(255,200,60,1)',
        'rgba(0,180,180,1)',
        'rgba(255,110,160,1)',
    ],
}

PALETTES['meadow_science_bright'] = {
    'ink': 'rgba(32,45,38,1)',
    'accent': 'rgba(240,140,50,1)',
    'secondary': 'rgba(150,190,100,1)',
    'bg': 'rgba(250,247,238,1)',
    'muted': 'rgba(90,105,90,0.6)',
    'series': [
        'rgba(240,140,50,1)',
        'rgba(140,190,90,1)',
        'rgba(60,150,180,1)',
        'rgba(230,190,60,1)',
        'rgba(200,80,90,1)',
        'rgba(120,80,180,1)',
        'rgba(80,180,150,1)',
        'rgba(220,120,180,1)',
    ],
}

PALETTES['coral_patient_bright'] = {
    'ink': 'rgba(46,32,38,1)',
    'accent': 'rgba(240,90,90,1)',
    'secondary': 'rgba(230,140,90,1)',
    'bg': 'rgba(250,245,240,1)',
    'muted': 'rgba(115,95,95,0.6)',
    'series': [
        'rgba(240,90,90,1)',
        'rgba(240,160,80,1)',
        'rgba(90,170,180,1)',
        'rgba(230,190,80,1)',
        'rgba(180,100,200,1)',
        'rgba(90,180,140,1)',
        'rgba(240,140,180,1)',
        'rgba(60,130,200,1)',
    ],
}

PALETTES['morandi_warm_bright'] = {
    'ink': 'rgba(58,52,48,1)',
    'accent': 'rgba(220,120,110,1)',
    'secondary': 'rgba(200,170,140,1)',
    'bg': 'rgba(245,241,235,1)',
    'muted': 'rgba(120,110,100,0.65)',
    'series': [
        'rgba(220,120,110,1)',
        'rgba(200,170,140,1)',
        'rgba(230,180,110,1)',
        'rgba(150,170,120,1)',
        'rgba(180,130,180,1)',
        'rgba(230,150,90,1)',
        'rgba(150,180,190,1)',
        'rgba(200,90,110,1)',
    ],
}

PALETTES['morandi_cool_bright'] = {
    'ink': 'rgba(48,52,58,1)',
    'accent': 'rgba(80,150,190,1)',
    'secondary': 'rgba(180,160,170,1)',
    'bg': 'rgba(240,240,238,1)',
    'muted': 'rgba(115,120,125,0.65)',
    'series': [
        'rgba(80,150,190,1)',
        'rgba(200,140,150,1)',
        'rgba(150,170,120,1)',
        'rgba(220,180,110,1)',
        'rgba(150,130,190,1)',
        'rgba(200,180,180,1)',
        'rgba(110,180,180,1)',
        'rgba(220,150,110,1)',
    ],
}

PALETTES['morandi_moss_bright'] = {
    'ink': 'rgba(45,50,42,1)',
    'accent': 'rgba(140,180,90,1)',
    'secondary': 'rgba(210,170,110,1)',
    'bg': 'rgba(242,240,232,1)',
    'muted': 'rgba(100,105,90,0.65)',
    'series': [
        'rgba(140,180,90,1)',
        'rgba(210,170,110,1)',
        'rgba(220,140,80,1)',
        'rgba(100,160,180,1)',
        'rgba(200,110,130,1)',
        'rgba(180,170,90,1)',
        'rgba(150,120,180,1)',
        'rgba(90,180,140,1)',
    ],
}


STYLE_PALETTES_BRIGHT = {
    'academic-research'             : ['archive_ink_bright', 'ivory_indigo_bright', 'titanium_olive_bright', 'nightlab_bright'],
    'strategy-and-analysis'         : ['burgundy_analyst_bright', 'ink_jade_bright', 'ochre_stone_bright'],
    'business-review'               : ['exec_navy_bright', 'sage_review_bright', 'mocha_kpi_bright'],
    'business-pitch'                : ['merlot_pitch_bright', 'forest_luxe_bright', 'rust_terracotta_bright', 'grape_eclectic_bright'],
    'technical-presentation'        : ['sapphire_dev_bright', 'deep_indigo_bright', 'terminal_neon_bright', 'pine_engineering_bright'],
    'brand-storytelling'            : ['tea_ceremony_bright', 'stone_ink_bright', 'candlelight_bright', 'linen_plum_bright'],
    'learning-and-training'         : ['classroom_indigo_bright', 'meadow_science_bright', 'coral_patient_bright'],
    'fallback'                      : ['morandi_warm_bright', 'morandi_cool_bright', 'morandi_moss_bright'],
}


# ============================================================
# EXTENDED PALETTES · 从 9 张色系参考图提取 + 自补
# ============================================================
#
# 命名对应关系（ref → palette）：
# 20260831-002320.jpg  薄荷曼波 (Nature 童趣)  → mint_mambo
# 20260831-002328.jpg  Nature 青绿 (科研)      → nature_teal
# 20260831-002332.jpg  蓝绿科研 (biology)      → sci_bluegreen
# 20260831-002337.jpg  简约学术 RdBu           → rdbu_scholar
# 20260831-002342.jpg  青绿山水 JADE           → jade_landscape
# 20260831-002346.jpg  淡彩粉紫 (pastel)       → pastel_dream
# 20260831-002350.jpg  莓果紫红 (berry wine)   → berry_wine
# 20260831-002354.jpg  生物医学 pink-blue      → biomed_diverging
# 20260831-002358.jpg  深海麦霜 Origin          → deep_sea_navy
#
# 自补：
# nordic_slate         北欧板岩 (冷灰+深靛)     · academic 备选
# sunset_terracotta    日落陶土                · brand storytelling
# forest_moss_v2       森林苔藓 + 铜金          · brand luxe
# charcoal_neon        炭黑 + 荧光青            · tech pitch
# ============================================================

PALETTES['mint_mambo'] = {
    # 来自 20260831-002320.jpg：#3D9F3C 深草绿 · #9ED17B 浅草绿 · #367DB0 湖蓝 · #9DC7DD 淡蓝
    # 童趣科研；教育 · 亲和 · 生物类
    'ink':       'rgba(28,52,72,1)',       # 深湖蓝墨
    'accent':    'rgba(61,159,60,1)',      # 深草绿 accent
    'secondary': 'rgba(54,125,176,1)',     # 湖蓝 secondary
    'bg':        'rgba(248,251,254,1)',    # 云白
    'muted':     'rgba(100,120,140,0.65)',
    'series': [
        'rgba(61,159,60,1)',
        'rgba(54,125,176,1)',
        'rgba(158,209,123,1)',
        'rgba(157,199,221,1)',
        'rgba(45,110,90,1)',
        'rgba(120,180,220,1)',
        'rgba(200,225,180,1)',
        'rgba(70,140,155,1)',
    ],
}

PALETTES['nature_teal'] = {
    # 来自 20260831-002328.jpg：#33c5b2 青绿 · #32a4b4 靛青 · #024e52 深湖 · #a3b1ae 灰绿 · #8a83a0 冷紫灰
    # Nature 期刊风 · 科研 · 生化领域
    'ink':       'rgba(20,45,50,1)',       # 深湖墨
    'accent':    'rgba(51,197,178,1)',     # 青绿 accent
    'secondary': 'rgba(2,78,82,1)',        # 深湖 secondary
    'bg':        'rgba(247,247,244,1)',    # 米白纸
    'muted':     'rgba(120,124,130,0.65)',
    'series': [
        'rgba(51,197,178,1)',
        'rgba(50,164,180,1)',
        'rgba(2,78,82,1)',
        'rgba(163,177,174,1)',
        'rgba(138,131,160,1)',
        'rgba(178,201,206,1)',
        'rgba(120,111,118,1)',
        'rgba(213,234,218,1)',
    ],
}

PALETTES['sci_bluegreen'] = {
    # 来自 20260831-002332.jpg：#3D9F3C 草绿 · #519D78 森绿 · #367DB0 深蓝 · #5385BD 靛蓝
    # 深底科研；CS / biotech / ML
    'ink':       'rgba(24,38,58,1)',       # 深靛墨
    'accent':    'rgba(83,133,189,1)',     # 靛蓝 accent
    'secondary': 'rgba(81,157,120,1)',     # 森绿 secondary
    'bg':        'rgba(252,252,250,1)',    # 象牙
    'muted':     'rgba(105,120,140,0.6)',
    'series': [
        'rgba(83,133,189,1)',
        'rgba(81,157,120,1)',
        'rgba(54,125,176,1)',
        'rgba(61,159,60,1)',
        'rgba(155,199,223,1)',
        'rgba(139,207,139,1)',
        'rgba(30,60,120,1)',
        'rgba(28,90,60,1)',
    ],
}

PALETTES['rdbu_scholar'] = {
    # 来自 20260831-002337.jpg：#B2182B 深绯红 · #D6604D 砖红 · #F4A582 蜜桃 · #92C5DE 天青 · #4393C3 湖蓝 · #2166AC 深海蓝
    # 简约·学术·清晰 · 红蓝双色对比 · 学术版
    'ink':       'rgba(28,32,38,1)',       # 墨黑
    'accent':    'rgba(33,102,172,1)',     # 深海蓝 accent（主结论一侧）
    'secondary': 'rgba(178,24,43,1)',      # 深绯红 secondary（对比一侧）
    'bg':        'rgba(255,255,255,1)',    # 白底
    'muted':     'rgba(120,124,130,0.65)',
    'series': [
        'rgba(33,102,172,1)',
        'rgba(178,24,43,1)',
        'rgba(67,147,195,1)',
        'rgba(214,96,77,1)',
        'rgba(146,197,222,1)',
        'rgba(244,165,130,1)',
        'rgba(209,229,240,1)',
        'rgba(253,219,199,1)',
    ],
}

PALETTES['jade_landscape'] = {
    # 来自 20260831-002342.jpg：#EEF7F2 月白 · #B9DEC9 竹篁绿 · #1BA784 竹绿 · #63BBD0 霁青 · #134857 苍蓝
    # 中国青绿山水 · JADE · 生态 · 高端印刷
    'ink':       'rgba(19,72,87,1)',       # 苍蓝墨
    'accent':    'rgba(27,167,132,1)',     # 竹绿 accent
    'secondary': 'rgba(99,187,208,1)',     # 霁青 secondary
    'bg':        'rgba(238,247,242,1)',    # 月白 bg
    'muted':     'rgba(85,120,125,0.6)',
    'series': [
        'rgba(27,167,132,1)',
        'rgba(19,72,87,1)',
        'rgba(99,187,208,1)',
        'rgba(185,222,201,1)',
        'rgba(58,120,110,1)',
        'rgba(45,145,150,1)',
        'rgba(120,180,175,1)',
        'rgba(24,90,105,1)',
    ],
}

PALETTES['pastel_dream'] = {
    # 来自 20260831-002346.jpg：#D9D3E8 淡紫 · #DAEDD8 薄荷 · #F0E8D8 米白 · #F2C17E 蜜橙 · #E79C96 珊瑚粉
    # 柔和 5 色 · 教育培训 · 亲和不幼稚 · 也可用于消费 lifestyle
    'ink':       'rgba(74,60,72,1)',       # 深紫墨
    'accent':    'rgba(231,156,150,1)',    # 珊瑚粉 accent
    'secondary': 'rgba(242,193,126,1)',    # 蜜橙 secondary
    'bg':        'rgba(252,250,246,1)',    # 米白 bg
    'muted':     'rgba(120,110,120,0.6)',
    'series': [
        'rgba(231,156,150,1)',
        'rgba(242,193,126,1)',
        'rgba(217,211,232,1)',
        'rgba(218,237,216,1)',
        'rgba(180,140,180,1)',
        'rgba(140,180,150,1)',
        'rgba(230,180,150,1)',
        'rgba(200,160,180,1)',
    ],
}

PALETTES['berry_wine'] = {
    # 来自 20260831-002350.jpg：#A23E3E 酒红 · #CD74BA 玫红 · #7A3086 深葡萄紫 · #E674A3 粉红 · #C8BC46 芥末黄
    # 莓果酒红 · 品牌 / 生活方式 / 女性向
    'ink':       'rgba(50,32,52,1)',       # 深紫墨
    'accent':    'rgba(122,48,134,1)',     # 深葡萄紫 accent
    'secondary': 'rgba(162,62,62,1)',      # 酒红 secondary
    'bg':        'rgba(250,246,238,1)',    # 米白
    'muted':     'rgba(115,95,110,0.65)',
    'series': [
        'rgba(122,48,134,1)',
        'rgba(162,62,62,1)',
        'rgba(205,116,186,1)',
        'rgba(230,116,163,1)',
        'rgba(200,188,70,1)',
        'rgba(180,90,140,1)',
        'rgba(140,60,110,1)',
        'rgba(235,200,208,1)',
    ],
}

PALETTES['biomed_diverging'] = {
    # 来自 20260831-002354.jpg：粉红蓝色发散色 (Nature 生物医学 heatmap)
    # 主色深蓝墨 + 粉红/蓝双色发散；生物医学 · 实验分组 · heat map
    'ink':       'rgba(38,42,58,1)',       # 深靛墨
    'accent':    'rgba(220,110,150,1)',    # 生物粉红 accent
    'secondary': 'rgba(70,120,190,1)',     # 深蓝 secondary
    'bg':        'rgba(253,251,250,1)',    # 象牙
    'muted':     'rgba(120,120,130,0.65)',
    'series': [
        'rgba(70,120,190,1)',
        'rgba(220,110,150,1)',
        'rgba(140,175,220,1)',
        'rgba(240,180,205,1)',
        'rgba(40,80,140,1)',
        'rgba(180,70,110,1)',
        'rgba(200,220,240,1)',
        'rgba(250,220,230,1)',
    ],
}

PALETTES['deep_sea_navy'] = {
    # 来自 20260831-002358.jpg：#1D1B1C 墨黑 · #224669 深靛蓝 · #3E739E 湖蓝 · #E5E3E5 银白 · #ECC9A3 麦色
    # 深海麦霜 Origin · 商业 pitch · 金融演讲 · 电影感
    'ink':       'rgba(229,227,229,1)',    # 银白正文
    'accent':    'rgba(236,201,163,1)',    # 麦色 accent
    'secondary': 'rgba(62,115,158,1)',     # 湖蓝 secondary
    'bg':        'rgba(29,27,28,1)',       # 深墨底
    'muted':     'rgba(180,180,190,0.7)',
    'series': [
        'rgba(236,201,163,1)',
        'rgba(62,115,158,1)',
        'rgba(34,70,105,1)',
        'rgba(200,170,130,1)',
        'rgba(120,150,180,1)',
        'rgba(160,120,80,1)',
        'rgba(80,110,150,1)',
        'rgba(220,220,225,1)',
    ],
}

PALETTES['nordic_slate'] = {
    # 自补：北欧板岩 · 冷灰 + 深靛 accent
    # 学术备选：适合数据科学、社科理论 · 极简 · 高级感
    'ink':       'rgba(28,34,42,1)',       # 深板岩
    'accent':    'rgba(46,72,120,1)',      # 深靛 accent
    'secondary': 'rgba(120,132,148,1)',    # 冷灰 secondary
    'bg':        'rgba(240,242,244,1)',    # 板岩白
    'muted':     'rgba(105,115,128,0.65)',
    'series': [
        'rgba(46,72,120,1)',
        'rgba(120,132,148,1)',
        'rgba(75,95,125,1)',
        'rgba(160,168,180,1)',
        'rgba(30,50,90,1)',
        'rgba(140,150,165,1)',
        'rgba(65,85,110,1)',
        'rgba(200,205,215,1)',
    ],
}

PALETTES['sunset_terracotta'] = {
    # 自补：日落陶土 · 焦橙 + 陶粉 + 米色
    # brand storytelling · 生活方式 · 家居 · 空间设计
    'ink':       'rgba(48,32,26,1)',       # 深胡桃墨
    'accent':    'rgba(214,110,66,1)',     # 日落焦橙 accent
    'secondary': 'rgba(196,142,110,1)',    # 陶土 secondary
    'bg':        'rgba(247,240,228,1)',    # 米白
    'muted':     'rgba(130,105,90,0.65)',
    'series': [
        'rgba(214,110,66,1)',
        'rgba(196,142,110,1)',
        'rgba(158,88,54,1)',
        'rgba(228,180,140,1)',
        'rgba(120,72,50,1)',
        'rgba(212,158,110,1)',
        'rgba(180,110,80,1)',
        'rgba(240,215,180,1)',
    ],
}

PALETTES['forest_moss_v2'] = {
    # 自补：深森林苔藓 + 铜金
    # brand luxe · 奢侈品 / 户外 / 可持续消费
    'ink':       'rgba(235,231,220,1)',    # 象牙
    'accent':    'rgba(198,158,84,1)',     # 古铜金 accent
    'secondary': 'rgba(120,148,120,1)',    # 苔绿 secondary
    'bg':        'rgba(28,42,36,1)',       # 深森林底
    'muted':     'rgba(170,175,165,0.7)',
    'series': [
        'rgba(198,158,84,1)',
        'rgba(120,148,120,1)',
        'rgba(158,178,140,1)',
        'rgba(215,195,155,1)',
        'rgba(90,120,95,1)',
        'rgba(170,138,80,1)',
        'rgba(220,210,180,1)',
        'rgba(140,120,80,1)',
    ],
}

PALETTES['charcoal_neon'] = {
    # 自补：炭黑底 + 荧光青
    # technical-presentation · devops · security · monitoring
    'ink':       'rgba(232,236,240,1)',    # 银白正文
    'accent':    'rgba(56,232,208,1)',     # 荧光青 accent
    'secondary': 'rgba(122,180,255,1)',    # 荧光蓝 secondary
    'bg':        'rgba(18,22,28,1)',       # 炭黑底
    'muted':     'rgba(160,170,180,0.7)',
    'series': [
        'rgba(56,232,208,1)',
        'rgba(122,180,255,1)',
        'rgba(240,200,90,1)',
        'rgba(230,120,180,1)',
        'rgba(150,220,140,1)',
        'rgba(100,150,200,1)',
        'rgba(220,220,240,1)',
        'rgba(80,180,180,1)',
    ],
}


# 更新 style → palette 推荐映射（追加，不覆盖）
STYLE_PALETTES_EXTENDED = {
    'academic-research':      ['nature_teal', 'sci_bluegreen', 'rdbu_scholar', 'nordic_slate', 'jade_landscape'],
    'strategy-and-analysis':  ['nordic_slate', 'rdbu_scholar', 'nature_teal'],
    'business-review':        ['deep_sea_navy', 'nordic_slate', 'jade_landscape'],
    'business-pitch':         ['deep_sea_navy', 'berry_wine', 'forest_moss_v2', 'sunset_terracotta'],
    'technical-presentation': ['charcoal_neon', 'sci_bluegreen', 'nordic_slate'],
    'brand-storytelling':     ['sunset_terracotta', 'forest_moss_v2', 'berry_wine', 'jade_landscape', 'deep_sea_navy'],
    'learning-and-training':  ['mint_mambo', 'pastel_dream', 'jade_landscape'],
    'fallback':               ['pastel_dream', 'nordic_slate'],
}
