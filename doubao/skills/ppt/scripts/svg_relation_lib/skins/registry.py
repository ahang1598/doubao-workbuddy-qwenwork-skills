"""
Skin registry · 让 preset 通过 name lookup 拿到完整 skin module

设计意图
────────
每个 skin 都是"完整视觉方言" (palette + canvas + chrome + fonts + defs)。
preset 不再硬编码 `from ..skins.editorial_atelier import ...`，而是：

    from ..skins.registry import get_skin
    skin = get_skin("boardroom_navy")
    hero_chrome = skin.hero_chrome
    palette = skin.PALETTE
    HUE = skin.HUE
    ...

Skin 契约 (9 个必备符号)
────────────────────────
每个 registered skin 必须在 module top-level 导出:

    ┌── data ────────────────────────────────────────────────
    │ PALETTE       : Palette                    12 色槽 + 3 字体族
    │ HUE           : Dict[str, str]             hue key → hex
    │ HERO_CANVAS   : CanvasProfile              1400×820 图纸尺寸
    │ EMBED_CANVAS  : CanvasProfile              900×336 legacy
    │ FONT_SANS     : str                        sans-family fallback chain
    │ FONT_SERIF    : str                        serif-family fallback chain
    │
    ┌── functions ───────────────────────────────────────────
    │ svg_defs(hues, include_markers=True, include_gradients=True) → str
    │ hero_chrome(*, kicker, title, subtitle, ..., palette, canvas) → str
    │ hero_footer(*, caption, source, read_lines, ..., palette, canvas) → str
    │ tspan(word, *, color=?, weight=700) → str

get_skin 会主动校验这 9 个符号 · 缺任何一个立即 AttributeError
（快速失败 · 免得 preset 半天后才在渲染路径炸掉）。

Usage
─────
    >>> from svg_relation_lib.skins.registry import get_skin, list_skins
    >>> list_skins()
    ['editorial_atelier', 'boardroom_navy']
    >>> skin = get_skin('boardroom_navy')
    >>> skin.HUE['rust']
    '#0D1B2A'
"""
from __future__ import annotations

import importlib
from types import ModuleType
from typing import Dict, List, Tuple

# ─────────── Skin 契约 · 9 个必备符号 ───────────
# 用一个 tuple 存 · list_missing_symbols 直接迭代
REQUIRED_SYMBOLS: Tuple[str, ...] = (
    # 数据
    "PALETTE",
    "HUE",
    "HERO_CANVAS",
    "EMBED_CANVAS",
    "FONT_SANS",
    "FONT_SERIF",
    # 函数
    "svg_defs",
    "hero_chrome",
    "hero_footer",
    "tspan",
)


# ─────────── Skin registry table ───────────
# key = skin name (preset 传的 str) · value = module 相对导入路径 (基于 svg_relation_lib.skins)
_SKIN_MODULES: Dict[str, str] = {
    "editorial_atelier":     ".editorial_atelier",
    "boardroom_navy":        ".boardroom_navy",
    "duolingo_cream":        ".duolingo_cream",
    "pitch_neon":            ".pitch_neon",
    "pitch_ivory":           ".pitch_ivory",
    "luxury_manual":         ".luxury_manual",
    "mbb_consulting":        ".mbb_consulting",
    "journal_ivory":         ".journal_ivory",
    "technical_whitepaper":  ".technical_whitepaper",
    "couture_noir":          ".couture_noir",
    "medical_chart":         ".medical_chart",
    "art_deco":              ".art_deco",
    "arxiv_pastel": ".arxiv_pastel",
    "manuscript_sepia": ".manuscript_sepia",
    "oxford_indigo": ".oxford_indigo",
    "symposium_ash": ".symposium_ash",
    "bcg_forest": ".bcg_forest",
    "bain_scarlet": ".bain_scarlet",
    "deloitte_lime": ".deloitte_lime",
    "roland_terracotta": ".roland_terracotta",
    "goldman_slate": ".goldman_slate",
    "wsj_broadsheet": ".wsj_broadsheet",
    "bloomberg_amber": ".bloomberg_amber",
    "annual_report_ivory": ".annual_report_ivory",
    "terminal_matrix": ".terminal_matrix",
    "blueprint_grid": ".blueprint_grid",
    "engineering_kraft": ".engineering_kraft",
    "arxiv_clean": ".arxiv_clean",
    "pitch_midnight": ".pitch_midnight",
    "pitch_bauhaus": ".pitch_bauhaus",
    "pitch_sunset": ".pitch_sunset",
    "khan_teal": ".khan_teal",
    "notebook_grid": ".notebook_grid",
    "coursera_indigo": ".coursera_indigo",
    "chalkboard_slate": ".chalkboard_slate",
    "monocle_ecru": ".monocle_ecru",
    "hermes_orange": ".hermes_orange",
    "bauhaus_primary": ".bauhaus_primary",
    "swiss_grid": ".swiss_grid",
    "wabi_sabi": ".wabi_sabi",
    "riso_duotone": ".riso_duotone",
}


# ─────────── Legacy palette aliases ───────────
# 老 skin (editorial_atelier) 用 BONE_RUST 作为 palette 常量名，不是通用 PALETTE。
# 这里做一次兼容适配，让老 skin 无需修改源码即可通过契约校验。
# 未来新 skin 一律直接导出 PALETTE。
_LEGACY_PALETTE_ALIAS: Dict[str, str] = {
    "editorial_atelier": "BONE_RUST",
}


# ─────────── 缓存 · 避免每次 get_skin 都 re-import ───────────
_LOADED: Dict[str, ModuleType] = {}


# ─────────── Active skin (runtime hook) ───────────
# preset 需要 opt-in 分流到 skin.draw_node 时,通过 get_active_skin() 查询。
# make_relation 在切换 skin 时会 set_active_skin,退出后 clear_active_skin。
# preset 用法:
#     skin = get_active_skin()
#     if skin and hasattr(skin, "draw_node"):
#         return skin.draw_node(x, y, w, h, label, kind="category_card", ...)
#     # else 走原来的裸拼 SVG 分支
# 保持"缺省 = None = 原路径"能保证当前 11 个 preset 不动就继续跑。
_ACTIVE_SKIN: List[ModuleType] = []  # stack · 支持嵌套 (虽然当前只用一层)


def set_active_skin(mod) -> None:
    """把 mod 压入 active skin 栈 · 由 make_relation 在 with-block 里调。"""
    _ACTIVE_SKIN.append(mod)


def clear_active_skin() -> None:
    """弹出栈顶 · 与 set_active_skin 成对使用。"""
    if _ACTIVE_SKIN:
        _ACTIVE_SKIN.pop()


def get_active_skin():
    """preset 在渲染时调 · 返回当前 active skin module 或 None。"""
    return _ACTIVE_SKIN[-1] if _ACTIVE_SKIN else None


def _apply_legacy_aliases(mod: ModuleType, name: str) -> None:
    """给老 skin 补上 PALETTE 别名 (指向 BONE_RUST/等旧常量) · 不动源文件。"""
    if not hasattr(mod, "PALETTE"):
        legacy_name = _LEGACY_PALETTE_ALIAS.get(name)
        if legacy_name and hasattr(mod, legacy_name):
            setattr(mod, "PALETTE", getattr(mod, legacy_name))


def _list_missing_symbols(mod: ModuleType) -> List[str]:
    """返回 skin module 缺失的必备符号列表 (空列表 = 契约完整)。"""
    return [sym for sym in REQUIRED_SYMBOLS if not hasattr(mod, sym)]


def _assert_contract(mod: ModuleType, name: str) -> None:
    """契约校验 · 缺任何必备符号立即 AttributeError。"""
    missing = _list_missing_symbols(mod)
    if missing:
        raise AttributeError(
            f"[skins.registry] skin '{name}' violates contract · "
            f"missing symbols: {missing}. "
            f"Required 9 symbols: {list(REQUIRED_SYMBOLS)}"
        )


def get_skin(name: str) -> ModuleType:
    """按 name 返回 skin module · 缺失则 KeyError · 契约不完整则 AttributeError。

    Args:
        name: skin key (见 list_skins())

    Returns:
        skin module · 保证有 REQUIRED_SYMBOLS 里全部 9 个 attr

    Raises:
        KeyError:        name 不在 registry
        AttributeError:  skin module 缺必备符号
        ImportError:     skin module import 失败
    """
    if name in _LOADED:
        return _LOADED[name]
    if name not in _SKIN_MODULES:
        raise KeyError(
            f"[skins.registry] unknown skin '{name}'. "
            f"registered: {list(_SKIN_MODULES)}"
        )
    mod = importlib.import_module(
        _SKIN_MODULES[name], package="svg_relation_lib.skins"
    )
    _apply_legacy_aliases(mod, name)
    _assert_contract(mod, name)
    _LOADED[name] = mod
    return mod


def list_skins() -> List[str]:
    """返回 registered skin name 列表 · preset UI / debug 用。"""
    return list(_SKIN_MODULES.keys())


def register_skin(name: str, module_path: str) -> None:
    """在运行时注册 skin (通常用不到 · 供未来 out-of-tree skin 插件用)。

    module_path 可以是绝对 (svg_relation_lib.skins.foo) 或相对 (.foo)。
    """
    _SKIN_MODULES[name] = module_path
    _LOADED.pop(name, None)   # 清缓存 · 下次 get_skin 重新校验


__all__ = [
    "get_skin",
    "list_skins",
    "register_skin",
    "set_active_skin",
    "clear_active_skin",
    "get_active_skin",
    "REQUIRED_SYMBOLS",
]
