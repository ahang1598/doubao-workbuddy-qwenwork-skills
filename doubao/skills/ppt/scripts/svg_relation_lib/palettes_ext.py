"""
svg_relation_lib.palettes_ext · palette registry (与 skin 正交)

**核心思想**:
    skin  = 结构骨架 (字体 / 装饰母题 / marker 形状 / chrome / defs prefix)
    palette = 颜色系统 (8 支 hue + bg + ink + accent)
    两者正交组合: `make_relation('...', skin='boardroom_navy', palette='exec_navy')`

**Palette schema** (与 chart 侧 palette 语义对齐, 但字段数为 relation 定制):
    - bg       : 页面主背景
    - ink      : 主文字
    - primary  : 主色 (=hues['rust'] · 与 skin 里 palette.primary 一致)
    - accent   : 强调色 (=hues['gold_p'])
    - hues     : Dict[str, str] 8 支分类 hue
                 rust / orange / magenta / blue / green / olive / cinnamon / gold_p

**Palette 命名对齐 chart 侧**:
    - 直接使用 chart palette 的名字 (如 `exec_navy`, `sage_review`, `mocha_kpi` 等)
    - 每个 style 文档推荐的 chart palette, 在 relation 侧应能找到同名 palette
    - 关系图和 chart 图共用同一套 palette 名, 保持 deck 视觉统一
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class RelationPalette:
    name: str              # 显示名
    bg: str                # 背景 hex
    ink: str               # 主墨 hex
    primary: str           # 主色 hex (= hues['rust'])
    accent: str            # 强调 hex (= hues['gold_p'])
    hues: Dict[str, str] = field(default_factory=dict)
    # 8 支必须齐: rust orange magenta blue green olive cinnamon gold_p
    tone: str = "warm"     # warm / cool / dark (给模型选图时的粗分类)
    origin: str = ""       # 从哪个 chart palette / skin 派生


# ═════════════════════════════════════════════════════════════════
# 8 套核心 palette (对齐 8 skin 的默认色)
# ═════════════════════════════════════════════════════════════════

BONE_RUST = RelationPalette(
    name="Bone Rust · Editorial Atelier",
    bg="#F1E9DA", ink="#1C1914",
    primary="#A35832", accent="#D9A448",
    hues={
        "rust": "#A35832", "orange": "#C87F3D", "magenta": "#A63C6E",
        "blue": "#3F6892", "green": "#558045", "olive": "#7A6A3A",
        "cinnamon": "#8B5A3C", "gold_p": "#D9A448",
        "slate": "#3F5C7A",   # atelier slate · 偏冷灰蓝 · 与 blue 邻近但更深偏灰
    },
    tone="warm",
    origin="editorial_atelier default",
)

EXEC_NAVY = RelationPalette(
    name="Exec Navy · Boardroom",
    bg="#F7F3E8", ink="#0D1B2A",
    primary="#0D1B2A", accent="#C9A66B",
    hues={
        "rust": "#0D1B2A", "orange": "#465667", "magenta": "#96322D",
        "blue": "#3A5A7C", "green": "#3C6E50", "olive": "#8A8477",
        "cinnamon": "#64748B", "gold_p": "#C9A66B",
        "slate": "#253C54",   # boardroom slate · 深钢青 · 比 blue 更暗
    },
    tone="warm",
    origin="chart palette exec_navy",
)

CLASSROOM_INDIGO = RelationPalette(
    name="Classroom Indigo · Duolingo",
    bg="#FFF9E8", ink="#1F2E5A",
    primary="#3B4F8A", accent="#58CC02",
    hues={
        "rust": "#3B4F8A", "orange": "#E8720C", "magenta": "#E64980",
        "blue": "#58ACF6", "green": "#58CC02", "olive": "#8B8B4C",
        "cinnamon": "#C97D3E", "gold_p": "#FFC800",
    },
    tone="warm",
    origin="chart palette classroom_indigo (Duolingo)",
)

MERLOT_PITCH = RelationPalette(
    name="Merlot Pitch · Neon Deep",
    bg="#0F0B14", ink="#F5F0EA",
    primary="#7FE3C4", accent="#E85D75",
    hues={
        "rust": "#7FE3C4", "orange": "#B8A0AF", "magenta": "#E85D75",
        "blue": "#4A90E2", "green": "#6EFCB0", "olive": "#8E7A88",
        "cinnamon": "#5A4E58", "gold_p": "#7FE3C4",
    },
    tone="dark",
    origin="chart palette merlot_pitch (pitch dark)",
)

FOREST_LUXE = RelationPalette(
    name="Forest Luxe · Design Manual",
    bg="#F5F0E8", ink="#1F2E23",
    primary="#1F2E23", accent="#C4A96B",
    hues={
        "rust": "#1F2E23", "orange": "#C4A96B", "magenta": "#8B4A5E",
        "blue": "#3E5062", "green": "#2E4A38", "olive": "#6E6656",
        "cinnamon": "#A69C8B", "gold_p": "#C4A96B",
    },
    tone="warm",
    origin="chart palette forest_luxe",
)

BURGUNDY_ANALYST = RelationPalette(
    name="Burgundy Analyst · MBB",
    bg="#FFFFFF", ink="#1A1A1A",
    primary="#7B2532", accent="#7B2532",
    hues={
        "rust": "#7B2532", "orange": "#B47278", "magenta": "#3C1017",
        "blue": "#4A5560", "green": "#5B6E5A", "olive": "#9B9B9B",
        "cinnamon": "#7A6A5C", "gold_p": "#7B2532",
        "slate": "#322D37",   # mbb slate · 勃艮第基底冷灰 · 单色规则下的深中性
    },
    tone="cool",
    origin="chart palette burgundy_analyst (MBB)",
)

IVORY_INDIGO = RelationPalette(
    name="Ivory Indigo · Journal",
    bg="#F7F3E8", ink="#1A1A2E",
    primary="#1E2A5E", accent="#4A7C6E",
    hues={
        "rust": "#1E2A5E", "orange": "#4A7C6E", "magenta": "#6B2E4E",
        "blue": "#2C4370", "green": "#3D5A4E", "olive": "#4F4A3E",
        "cinnamon": "#7A6A3E", "gold_p": "#B58A3E",
    },
    tone="warm",
    origin="chart palette ivory_indigo (academic)",
)

SAPPHIRE_DEV = RelationPalette(
    name="Sapphire Dev · Whitepaper",
    bg="#F2F4F8", ink="#0F1729",
    primary="#003087", accent="#0070BA",
    hues={
        "rust": "#003087", "orange": "#0070BA", "magenta": "#C9302C",
        "blue": "#3F6892", "green": "#3C6E50", "olive": "#64748B",
        "cinnamon": "#8A94A5", "gold_p": "#C9302C",
    },
    tone="cool",
    origin="chart palette sapphire_dev (whitepaper)",
)


# ═════════════════════════════════════════════════════════════════
# 17 套扩展 palette · 从 chart 侧 palette 系统投影
# 投影规则:
#   chart.bg          → bg
#   chart.ink         → ink
#   chart.accent      → primary  (chart 的"点睛色" == relation 的主色)
#   chart.series[0]   → accent   (系列首色作为强调)
#   hues 8 支从 series/accent/secondary 里挑, 优先保证 rust/orange/
#   magenta/blue/green/olive/cinnamon/gold_p 之间色相有区分度
# ═════════════════════════════════════════════════════════════════

ARCHIVE_INK = RelationPalette(
    name="Archive Ink · Academic",
    bg="#F1E9DA", ink="#1C1914",
    primary="#A35832", accent="#A35832",
    hues={
        "rust": "#A35832", "orange": "#C87F3D", "magenta": "#B44738",
        "blue": "#4A445A", "green": "#3C4A42", "olive": "#5A6050",
        "cinnamon": "#785A3C", "gold_p": "#947848",
    },
    tone="warm",
    origin="chart palette archive_ink (academic historical)",
)

GS_RESEARCH = RelationPalette(
    name="GS Research · Deep Blue Gold",
    bg="#FCFAF4", ink="#121E32",
    primary="#B48C48", accent="#121E32",
    hues={
        "rust": "#B48C48", "orange": "#C8AA78", "magenta": "#96322D",
        "blue": "#46648C", "green": "#3C6E50", "olive": "#8C7450",
        "cinnamon": "#96603C", "gold_p": "#C9A66B",
    },
    tone="cool",
    origin="synthesized · gs research deep blue gold (exec_navy variant)",
)

HBS_CASE = RelationPalette(
    name="HBS Case · Academic Red",
    bg="#FCFAF6", ink="#1E191C",
    primary="#96202C", accent="#96202C",
    hues={
        "rust": "#96202C", "orange": "#AA5A46", "magenta": "#7A202C",
        "blue": "#3C5A78", "green": "#5B6E5A", "olive": "#78504A",
        "cinnamon": "#B47250", "gold_p": "#C4A86E",
    },
    tone="warm",
    origin="synthesized · HBS case-study red (cell_press variant)",
)

CELL_PRESS = RelationPalette(
    name="Cell Press · Academic Plum Red",
    bg="#FFFFFF", ink="#1C1420",
    primary="#B43250", accent="#B43250",
    hues={
        "rust": "#B43250", "orange": "#C85A78", "magenta": "#6B2E4E",
        "blue": "#3C6EAA", "green": "#3A786E", "olive": "#78508C",
        "cinnamon": "#8C5A3C", "gold_p": "#96322D",
    },
    tone="warm",
    origin="synthesized · cell press academic (white plum red)",
)

MOCHA_KPI = RelationPalette(
    name="Mocha KPI · Growth Dark",
    bg="#1A1A20", ink="#F0ECE4",
    primary="#D48C48", accent="#D48C48",
    hues={
        "rust": "#D48C48", "orange": "#E6C496", "magenta": "#C66E50",
        "blue": "#7896B4", "green": "#B4C4A0", "olive": "#9E7A60",
        "cinnamon": "#B45A3C", "gold_p": "#F0DCBE",
    },
    tone="dark",
    origin="chart palette mocha_kpi (growth monthly dark)",
)

SAGE_REVIEW = RelationPalette(
    name="Sage Review · HR Policy",
    bg="#ECEAE4", ink="#262D2A",
    primary="#B84C3A", accent="#738A78",
    hues={
        "rust": "#B84C3A", "orange": "#C87F3D", "magenta": "#8C4A5E",
        "blue": "#6C7884", "green": "#738A78", "olive": "#9E8E6E",
        "cinnamon": "#8C6050", "gold_p": "#A0B49E",
    },
    tone="cool",
    origin="chart palette sage_review (HR / government)",
)

RUST_TERRACOTTA = RelationPalette(
    name="Rust Terracotta · Industrial",
    bg="#F6F0E4", ink="#261E1A",
    primary="#B8542C", accent="#B8542C",
    hues={
        "rust": "#B8542C", "orange": "#CA9460", "magenta": "#A03C2C",
        "blue": "#5C6866", "green": "#7A8A72", "olive": "#8A7654",
        "cinnamon": "#946E5C", "gold_p": "#A88450",
    },
    tone="warm",
    origin="chart palette rust_terracotta (industrial ivory)",
)

GRAPE_ECLECTIC = RelationPalette(
    name="Grape Eclectic · Ivory Plum",
    bg="#F5F0EB", ink="#261C2A",
    primary="#60346E", accent="#60346E",
    hues={
        "rust": "#60346E", "orange": "#B4916E", "magenta": "#8C5A78",
        "blue": "#5C6C90", "green": "#7A8C6E", "olive": "#806648",
        "cinnamon": "#946478", "gold_p": "#C4A88C",
    },
    tone="cool",
    origin="chart palette grape_eclectic (feminine content)",
)

NIGHTLAB = RelationPalette(
    name="Nightlab · CS/Data Dark",
    bg="#10141C", ink="#F0F0E8",
    primary="#D4E92C", accent="#D4E92C",
    hues={
        "rust": "#D4E92C", "orange": "#E69650", "magenta": "#E85D75",
        "blue": "#608CBE", "green": "#7A8B2C", "olive": "#B496D2",
        "cinnamon": "#B47850", "gold_p": "#F0F0E8",
    },
    tone="dark",
    origin="chart palette nightlab (data science dark indigo)",
)

TERMINAL_NEON = RelationPalette(
    name="Terminal Neon · DevOps",
    bg="#0E1412", ink="#E0F0D0",
    primary="#BEFF3C", accent="#BEFF3C",
    hues={
        "rust": "#BEFF3C", "orange": "#E6FF78", "magenta": "#FF80A0",
        "blue": "#3CDCD2", "green": "#50DC8C", "olive": "#8CBE5A",
        "cinnamon": "#B4E6B4", "gold_p": "#DCFF80",
    },
    tone="dark",
    origin="chart palette terminal_neon (devops security)",
)

PINE_ENGINEERING = RelationPalette(
    name="Pine Engineering · ESG",
    bg="#F4F6F5", ink="#1E322D",
    primary="#4C7A5A", accent="#4C7A5A",
    hues={
        "rust": "#4C7A5A", "orange": "#B2A06E", "magenta": "#A07C58",
        "blue": "#3A5C60", "green": "#5E9670", "olive": "#96AA87",
        "cinnamon": "#8C6C4C", "gold_p": "#C8B476",
    },
    tone="cool",
    origin="chart palette pine_engineering (sustainable energy)",
)

TEA_CEREMONY = RelationPalette(
    name="Tea Ceremony · Eastern",
    bg="#F4EDE0", ink="#26201A",
    primary="#A86C3A", accent="#A86C3A",
    hues={
        "rust": "#A86C3A", "orange": "#C4965C", "magenta": "#B4563A",
        "blue": "#6C7C78", "green": "#788C6E", "olive": "#948057",
        "cinnamon": "#604836", "gold_p": "#D4B684",
    },
    tone="warm",
    origin="chart palette tea_ceremony (eastern aesthetic)",
)

STONE_INK = RelationPalette(
    name="Stone Ink · Photography",
    bg="#EEECE6", ink="#1C1C1C",
    primary="#B84834", accent="#B84834",
    hues={
        "rust": "#B84834", "orange": "#C88C58", "magenta": "#823C32",
        "blue": "#606A78", "green": "#7A8478", "olive": "#605E58",
        "cinnamon": "#8C5C40", "gold_p": "#B4B2A8",
    },
    tone="warm",
    origin="chart palette stone_ink (photography / space design)",
)

CANDLELIGHT = RelationPalette(
    name="Candlelight · Cinematic",
    bg="#1C1614", ink="#F0E8D6",
    primary="#E8AC50", accent="#E8AC50",
    hues={
        "rust": "#E8AC50", "orange": "#F0C878", "magenta": "#C85A46",
        "blue": "#6E8C96", "green": "#968C5A", "olive": "#B48248",
        "cinnamon": "#8C6444", "gold_p": "#F0E4B4",
    },
    tone="dark",
    origin="chart palette candlelight (cinematic walnut)",
)

LINEN_PLUM = RelationPalette(
    name="Linen Plum · Feminine Brand",
    bg="#F6F0E6", ink="#281A26",
    primary="#7A3450", accent="#7A3450",
    hues={
        "rust": "#7A3450", "orange": "#A8846E", "magenta": "#B48292",
        "blue": "#4A5A78", "green": "#7A9078", "olive": "#D2B49E",
        "cinnamon": "#946478", "gold_p": "#E4D0BE",
    },
    tone="warm",
    origin="chart palette linen_plum (feminine brand)",
)

MEADOW_SCIENCE = RelationPalette(
    name="Meadow Science · Biology",
    bg="#FAF7EE", ink="#202D26",
    primary="#CC843A", accent="#7A9B66",
    hues={
        "rust": "#CC843A", "orange": "#DBB260", "magenta": "#9B5F32",
        "blue": "#4E7856", "green": "#7A9B66", "olive": "#A0B478",
        "cinnamon": "#B4783E", "gold_p": "#C8D0A8",
    },
    tone="warm",
    origin="chart palette meadow_science (biology / popular sci)",
)

DEEP_SEA_NAVY = RelationPalette(
    name="Deep Sea Navy · Wheat Ocean",
    bg="#1D1B1C", ink="#E5E3E5",
    primary="#ECC9A3", accent="#ECC9A3",
    hues={
        "rust": "#ECC9A3", "orange": "#C8AA82", "magenta": "#A07850",
        "blue": "#3E739E", "green": "#7896B4", "olive": "#224669",
        "cinnamon": "#8C6644", "gold_p": "#DCDCDF",
    },
    tone="dark",
    origin="chart palette deep_sea_navy (financial cinematic)",
)


# ═════════════════════════════════════════════════════════════════
# Registry
# ═════════════════════════════════════════════════════════════════

_PALETTES: Dict[str, RelationPalette] = {
    # ---- 8 套核心 palette ----
    "bone_rust":         BONE_RUST,          # editorial_atelier default
    "exec_navy":         EXEC_NAVY,          # business-review 董事会
    "classroom_indigo":  CLASSROOM_INDIGO,   # learning-and-training 教育
    "merlot_pitch":      MERLOT_PITCH,       # business-pitch 融资 (深底)
    "forest_luxe":       FOREST_LUXE,        # design-proposal 奢侈品牌
    "burgundy_analyst":  BURGUNDY_ANALYST,   # strategy-and-analysis MBB
    "ivory_indigo":      IVORY_INDIGO,       # academic-research 期刊
    "sapphire_dev":      SAPPHIRE_DEV,       # technical-presentation 白皮书
    # ---- 17 套扩展 palette (chart 侧投影) ----
    "archive_ink":       ARCHIVE_INK,        # academic 米底 rust
    "gs_research":       GS_RESEARCH,        # exec_navy 替代 · 深蓝金
    "hbs_case":          HBS_CASE,           # cell_press 变体 · academic red
    "cell_press":        CELL_PRESS,         # academic 白紫红
    "mocha_kpi":         MOCHA_KPI,          # 深底墨黑 · 摩卡橘 · 增长月报
    "sage_review":       SAGE_REVIEW,        # 浅石灰 sage · 人力政务
    "rust_terracotta":   RUST_TERRACOTTA,    # 米白锈橙 · 工业
    "grape_eclectic":    GRAPE_ECLECTIC,     # 象牙紫 · 女性向
    "nightlab":          NIGHTLAB,           # 深底靛蓝 · CS/data
    "terminal_neon":     TERMINAL_NEON,      # 深底荧光绿 · DevOps
    "pine_engineering":  PINE_ENGINEERING,   # 白底松绿 · ESG
    "tea_ceremony":      TEA_CEREMONY,       # 茶汤陶土 · 东方美学
    "stone_ink":         STONE_INK,          # 石纸墨黑 · 摄影空间
    "candlelight":       CANDLELIGHT,        # 深底胡桃 · 电影感
    "linen_plum":        LINEN_PLUM,         # 亚麻梅子 · 女性品牌
    "meadow_science":    MEADOW_SCIENCE,     # 青草象牙 · 生物科普
    "deep_sea_navy":     DEEP_SEA_NAVY,      # 深底海蓝
}


def get_palette(name: str) -> RelationPalette:
    """按名字查 palette · 未知名 raise KeyError."""
    if name not in _PALETTES:
        raise KeyError(
            f"unknown palette: {name!r} · available: {list(_PALETTES.keys())}"
        )
    return _PALETTES[name]


def list_palettes(tone: Optional[str] = None) -> List[str]:
    """列出全部 palette 名 (可按 tone 过滤: warm / cool / dark)."""
    if tone is None:
        return list(_PALETTES.keys())
    return [n for n, p in _PALETTES.items() if p.tone == tone]


def register_palette(name: str, palette: RelationPalette) -> None:
    """运行时注册新 palette (供插件用)."""
    _PALETTES[name] = palette


__all__ = [
    "RelationPalette",
    "get_palette", "list_palettes", "register_palette",
    # 8 core
    "BONE_RUST", "EXEC_NAVY", "CLASSROOM_INDIGO", "MERLOT_PITCH",
    "FOREST_LUXE", "BURGUNDY_ANALYST", "IVORY_INDIGO", "SAPPHIRE_DEV",
    # 17 chart-projected
    "ARCHIVE_INK", "GS_RESEARCH", "HBS_CASE", "CELL_PRESS",
    "MOCHA_KPI", "SAGE_REVIEW", "RUST_TERRACOTTA", "GRAPE_ECLECTIC",
    "NIGHTLAB", "TERMINAL_NEON", "PINE_ENGINEERING", "TEA_CEREMONY",
    "STONE_INK", "CANDLELIGHT", "LINEN_PLUM", "MEADOW_SCIENCE",
    "DEEP_SEA_NAVY",
]
