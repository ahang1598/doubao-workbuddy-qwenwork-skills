"""
5 signature palettes + font packs · 从 104 deck 的 B12/B13 顶级商业方言萃取

每套 palette 都是一个 dataclass，包含 12 色槽 + 3 字体族 fallback chain + dialect motif
(chrome kicker / section 编号 / folio 格式的约定)。

选一套 palette 的时候，直接 import 常量：
    from pattern_kit.palettes import INSTITUTIONAL_WHITE, GS_RESEARCH, HBS_CASE, CELL_PRESS, CONSUMER_CHRONICLE
"""
from dataclasses import dataclass, field
from typing import Dict


@dataclass(frozen=True)
class Palette:
    name: str
    # ─── 色槽 · 12 slot ───
    bg: str          # 页面主背景
    bg_alt: str      # 次背景 · card / panel
    bg_dim: str      # 三级背景 · deep card
    ink: str         # 主文字
    gray: str        # 二级文字
    hair: str        # 分隔线
    primary: str     # 主色 · 承担 60% 视觉权重
    primary_dim: str # 主色低饱和 · 二级 encoding
    accent: str      # 强调 · 数字 / 关键结论 / hairline
    accent_dim: str  # 强调色深 · legend / hover
    positive: str    # 正 delta
    negative: str    # 负 delta
    # ─── 字体 · 3 face ───
    head_family: str    # 大标题
    body_family: str    # 正文
    mono_family: str    # 编号 / kicker / tabular numbers
    # ─── Chrome motif（服务专业感）───
    kicker_letter_spacing: float = 2.5   # § 01 · FIG 1 · ... 的字距
    kicker_case: str = "upper"            # upper / small_caps / mixed
    section_numbering: str = "roman"      # roman / arabic / hex
    folio_style: str = "hairline"         # hairline / dot / rule
    title_style: str = "sans_bold"        # sans_bold / serif_bold / serif_italic
    subtitle_style: str = "sans_italic"   # sans_italic / serif_italic / mono
    figure_caption_prefix: str = "Fig."   # Fig. / § / [FIG]
    signature_note: str = ""              # 底部 signature 一句话 · dialect 招牌


# ═════════════════════════════════════════════════════════════════
# 1. INSTITUTIONAL WHITE · 通用高级白底（GS Research 简化版）
# ═════════════════════════════════════════════════════════════════
INSTITUTIONAL_WHITE = Palette(
    name="Institutional White",
    bg="#FFFFFF",
    bg_alt="#F5F5F8",
    bg_dim="#EAEBF0",
    ink="#1E2028",
    gray="#7A7C88",
    hair="#D4D6DC",
    primary="#003A84",
    primary_dim="#5A88BC",
    accent="#C8AA6E",
    accent_dim="#A58750",
    positive="#3C6E50",
    negative="#96322D",
    head_family="Chronicle Display, Söhne, Georgia, serif",
    body_family="Söhne, Helvetica Neue, Arial, sans-serif",
    mono_family="Söhne Mono, JetBrains Mono, Menlo, monospace",
    kicker_case="upper",
    section_numbering="arabic",
    folio_style="hairline",
    title_style="sans_bold",
    subtitle_style="sans_italic",
    figure_caption_prefix="FIG",
    signature_note="INSTITUTIONAL RESEARCH",
)


# ═════════════════════════════════════════════════════════════════
# 2. GS RESEARCH · 深蓝金 · IB analyst note
# ═════════════════════════════════════════════════════════════════
GS_RESEARCH = Palette(
    name="Goldman Sachs Research",
    bg="#FFFFFF",
    bg_alt="#FAFAFB",
    bg_dim="#EEEEF2",
    ink="#232328",
    gray="#787882",
    hair="#D2D2D7",
    primary="#003A84",       # GS 深蓝
    primary_dim="#2D5FA5",
    accent="#C8AA6E",        # 精细金
    accent_dim="#A58750",
    positive="#3C6E50",
    negative="#96322D",
    head_family="Chronicle Display, Söhne, Georgia, serif",
    body_family="Söhne, Helvetica Neue, Arial, sans-serif",
    mono_family="Söhne Mono, JetBrains Mono, Menlo, monospace",
    kicker_letter_spacing=3.0,
    kicker_case="upper",
    section_numbering="roman",
    folio_style="hairline",
    title_style="sans_bold",
    subtitle_style="sans_italic",
    figure_caption_prefix="FIG",
    signature_note="GOLDMAN SACHS GLOBAL INVESTMENT RESEARCH",
)


# ═════════════════════════════════════════════════════════════════
# 3. HBS CASE · 深红象牙 · Harvard Business School case study
# ═════════════════════════════════════════════════════════════════
HBS_CASE = Palette(
    name="HBS Case Study",
    bg="#FBF7EE",            # 象牙 cream
    bg_alt="#F3EEE0",
    bg_dim="#E8E1CE",
    ink="#1A1A1E",
    gray="#7A7570",
    hair="#C8C0AC",
    primary="#A5182E",       # Harvard crimson
    primary_dim="#C85263",
    accent="#233752",        # 深靛
    accent_dim="#3E5670",
    positive="#3B6B47",
    negative="#8B2C1D",
    head_family="Baskerville, EB Garamond, Georgia, serif",
    body_family="Söhne, Helvetica Neue, Arial, sans-serif",
    mono_family="Söhne Mono, JetBrains Mono, Menlo, monospace",
    kicker_letter_spacing=2.0,
    kicker_case="mixed",
    section_numbering="roman",
    folio_style="rule",
    title_style="serif_bold",
    subtitle_style="serif_italic",
    figure_caption_prefix="Exhibit",
    signature_note="HBS · CASE 9-527-081",
)


# ═════════════════════════════════════════════════════════════════
# 4. CELL PRESS · 白紫红 · 双栏学术顶刊
# ═════════════════════════════════════════════════════════════════
CELL_PRESS = Palette(
    name="Cell Press",
    bg="#FFFFFF",
    bg_alt="#F8F8FA",
    bg_dim="#EEEEF2",
    ink="#2A2A32",
    gray="#7C7C86",
    hair="#D2D2D8",
    primary="#D23C6E",       # 品红紫
    primary_dim="#E68AA5",
    accent="#1E3B6F",        # 学术深靛
    accent_dim="#4A6499",
    positive="#3F7A4E",
    negative="#B22E42",
    head_family="Adobe Garamond, EB Garamond, Georgia, serif",
    body_family="Söhne, Helvetica Neue, Arial, sans-serif",
    mono_family="Söhne Mono, JetBrains Mono, Menlo, monospace",
    kicker_letter_spacing=2.5,
    kicker_case="upper",
    section_numbering="arabic",
    folio_style="dot",
    title_style="serif_bold",
    subtitle_style="serif_italic",
    figure_caption_prefix="Figure",
    signature_note="Cell · Vol 194 · Issue 6",
)


# ═════════════════════════════════════════════════════════════════
# 5. CONSUMER CHRONICLE · 报纸米黑红 · WSJ / FT broadsheet
# ═════════════════════════════════════════════════════════════════
CONSUMER_CHRONICLE = Palette(
    name="Consumer Chronicle",
    bg="#F1EBD8",            # 报纸米
    bg_alt="#E8E1CB",
    bg_dim="#DCD4B9",
    ink="#141410",
    gray="#7A756A",
    hair="#B8B29B",
    primary="#8B1728",       # 深报纸红
    primary_dim="#B8465A",
    accent="#3B6B47",        # 深报纸绿
    accent_dim="#5A8968",
    positive="#3B6B47",
    negative="#8B1728",
    head_family="GT Sectra, Playfair Display, Georgia, serif",
    body_family="Söhne, Helvetica Neue, Arial, sans-serif",
    mono_family="Söhne Mono, JetBrains Mono, Menlo, monospace",
    kicker_letter_spacing=2.5,
    kicker_case="upper",
    section_numbering="roman",
    folio_style="rule",
    title_style="serif_italic",
    subtitle_style="serif_italic",
    figure_caption_prefix="FIG.",
    signature_note="THE CONSUMER CHRONICLE",
)


# ═════════════════════════════════════════════════════════════════
# 索引 · 让下一个模型能用 name lookup
# ═════════════════════════════════════════════════════════════════
ALL_PALETTES: Dict[str, Palette] = {
    "institutional_white": INSTITUTIONAL_WHITE,
    "gs_research":         GS_RESEARCH,
    "hbs_case":            HBS_CASE,
    "cell_press":          CELL_PRESS,
    "consumer_chronicle":  CONSUMER_CHRONICLE,
}


def get_palette(key: str) -> Palette:
    if key not in ALL_PALETTES:
        raise KeyError(f"palette '{key}' not in {list(ALL_PALETTES)}")
    return ALL_PALETTES[key]
