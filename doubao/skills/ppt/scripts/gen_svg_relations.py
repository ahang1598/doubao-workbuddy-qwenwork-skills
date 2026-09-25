#!/usr/bin/env python3
"""
gen_svg_relations.py · 11 种树状图 SVG 的统一入口 (v2)

按参数生成当前 PPT skill 支持的树状图。用于飞书 Slides 时默认应输出
可编辑的 slide-native 元素：
优先调用 `make_relation_atomized(...)` 或 CLI `--atomized`。`make_relation(...)`
只返回整块 SVG 字符串，适合预览、导出或明确允许不可编辑 `<embed>` 的场景。

当前仅支持 11 种树状图：
  al_fishbone / py_pmf / bl_bloom / j1_osi / mp_mindmap / tx_taxonomy /
  kp_kpi / e2_5why / cu2_curriculum / ft_faulttree / cs_c4

命令行用法:
  python3 gen_svg_relations.py --type al_fishbone --data-file fishbone.json --atomized > out.xml
  python3 gen_svg_relations.py --type al_fishbone --sample-data > out.svg  # 仅预览/测试样例
  python3 gen_svg_relations.py --list                    # 全部支持的 slug
  python3 gen_svg_relations.py --help-slug al_fishbone   # 单张详情

Python 调用:
  from gen_svg_relations import make_relation_atomized, make_relation, relation_help
  fragment = make_relation_atomized('al_fishbone', build_kwargs={...})  # 飞书 Slides 推荐：可编辑
  svg = make_relation('al_fishbone', allow_sample_data=True)            # 仅预览/测试样例
  print(relation_help())                                    # 总览
  print(relation_help('al_fishbone'))                       # 单张详情

输出:
  - `make_relation_atomized(...)` / `--atomized` 返回 `<slide><data>...</data></slide>`，
    其中主体拆成 `<shape>` / `<line>` / `<shape type="text">`，可在 Slides 中选择和编辑。
  - `make_relation(...)` 返回 SVG 字符串；把它整体塞进 `<embed>` 后不可逐元素编辑。

palette:
  所有 preset 默认使用 BONE_RUST palette (editorial_atelier skin)
  · 传 palette=<Palette> 覆盖 (见 svg_relation_lib.palettes)

数据格式 (data 参数):
  每张 relation 的 data 结构不同. 详情用 relation_help('<slug>') 查询.
  多数 preset 提供 `build_<slug>_data(...)` factory 帮你构造.
  正式 PPT 必须传 data 或 build_kwargs；内置 HERO_*_DATA 样例只在显式
  allow_sample_data=True / CLI --sample-data 时启用，避免假业务内容误入交付物。
"""
from __future__ import annotations

import argparse
import importlib
import json
import os as _os
import sys as _sys
from typing import Any, Callable, Dict, List, Optional, Tuple

# ensure svg_relation_lib on sys.path (script may be invoked from anywhere,
# e.g. `python3 scripts/gen_svg_relations.py` OR
# `python3 -c "from scripts.gen_svg_relations import relation_help; ..."`)
_HERE = _os.path.dirname(_os.path.abspath(__file__))
if _HERE not in _sys.path:
    _sys.path.insert(0, _HERE)


# ═════════════════════════════════════════════════════════════════
# 支持类别说明
# ═════════════════════════════════════════════════════════════════

_SCHEMA_DESCRIPTIONS: Dict[str, str] = {
    "tree": (
        "**Tree / hierarchy**：当前支持的树状图围绕层级、分解、链路或容器关系组织；"
        "每个图的具体数据格式以 `relation_help('<slug>')` 为准。"
    ),
}


# ═════════════════════════════════════════════════════════════════
# Preset manifest · 11 种 v2 tree diagram
# (slug, module_suffix, render_fn, build_fn, schema, one_line_scene, data_hint)
# ═════════════════════════════════════════════════════════════════

_RELATION_META: List[Tuple[str, str, str, str, str, str, str]] = [
    # ─────────── 当前支持的树状图 (11 种) ───────────
    ("al_fishbone", "hero_embed_01_AL_fishbone_v2", "render_hero_embed_al_fishbone_v2", "build_al_tree",
     "tree", "鱼骨 · root=effect + N branch × M sub-cause",
     "root(effect) → 3-6 category → 每 category 1-5 sub-cause · 一根脊柱 + 上下分支"),
    ("py_pmf", "hero_embed_02_PY_pmf_v2", "render_hero_embed_py_pmf_v2", "build_py_tree",
     "tree", "3 层金字塔 · Problem / Method / Findings",
     "root + 3 层堆叠 · 每层 3-4 支点"),
    ("bl_bloom", "hero_embed_03_BL_bloom_v2", "render_hero_embed_bl_bloom_v2", "build_bloom_tree",
     "tree", "Bloom 认知金字塔 · N 层水平条堆叠",
     "root + n_layers ∈ [3,7] · 每层含 name / verbs list / example · 无 branch (线性链)"),
    ("j1_osi", "hero_embed_04_J1_osi_v2", "render_hero_embed_j1_osi_v2", "build_osi_tree",
     "tree", "OSI 分层协议栈 · 3-8 layer × 协议 chip",
     "root + n_layers ∈ [3,8] · 每 layer 有 short/name/hue + 2-6 proto chip"),
    ("mp_mindmap", "hero_embed_05_MP_mindmap_v2", "render_hero_embed_mp_mindmap_v2", "build_mp_tree",
     "tree", "mindmap · hub 中心 + N 分支放射",
     "root(hub) + 3-8 branch · 每 branch 2-5 leaf"),
    ("tx_taxonomy", "hero_embed_07_TX_taxonomy_v2", "render_hero_embed_tx_taxonomy_v2", "build_tx_tree",
     "tree", "四象限 / radial taxonomy",
     "root + 4 category × N item"),
    ("kp_kpi", "hero_embed_08_KP_kpi_v2", "render_hero_embed_kp_kpi_v2", "build_kpi_tree",
     "tree", "KPI cascade · north-star → leading → lagging",
     "root(north-star) + 2-5 leading · 每 leading 2-5 lagging · 每 KPI 有 stat/trend/healthy"),
    ("e2_5why", "hero_embed_09_E2_5why_v2", "render_hero_embed_e2_5why_v2", "build_e2_tree",
     "tree", "5-Why 追因阶梯 · 线性因果链",
     "root(problem) + 2-7 why 深度 · 单链条"),
    ("cu2_curriculum", "hero_embed_32_CU2_curriculum_v2", "render_hero_embed_cu2_curriculum_v2", "build_curriculum_tree",
     "tree", "课程大纲 · module + lesson",
     "root + 3-8 module · 每 module 1-10 lesson"),
    ("ft_faulttree", "hero_embed_49_FT_faulttree_v2", "render_hero_embed_ft_faulttree_v2", "build_ft_tree",
     "tree", "故障树 · top event + AND/OR gate + basic events",
     "root(top event) · 中间节点 gate=AND/OR · 叶子是 basic event"),
    ("cs_c4", "hero_embed_10_CS_c4_v2", "render_hero_embed_cs_c4_v2", "build_cs_c4_data",
     "tree", "C4 · System > Boundary > Container (dandelion-migrated)",
     "root(system) → 2-5 boundary → 每 boundary 1-6 container · edges 在 root.extra['edges']"),
]

_SLUG_TO_META: Dict[str, Tuple[str, str, str, str, str, str, str]] = {
    m[0]: m for m in _RELATION_META
}

# Keep this note generic so future curve-based tree presets do not need a separate registry.
_CURVE_LINT_NOTE = "部分树状图可能使用曲线/自定义 path；若 lint 报元素重叠，不一定是真实渲染错误，先做截图检查确认后再调整。"

_SCHEMA_ORDER = ["tree"]


# ═════════════════════════════════════════════════════════════════
# lazy import · 只在调用时加载对应 preset
# ═════════════════════════════════════════════════════════════════

def _load_preset(slug: str) -> Tuple[Callable, Callable, Any]:
    """按 slug 加载 (render_fn, build_fn, hero_default).

    hero_default: 若模块提供 HERO_<TAG>_DATA 之类的常量, 仅作显式 sample-data 用.
    """
    if slug not in _SLUG_TO_META:
        raise KeyError(f"unknown relation slug: {slug!r} · use --list to see all")
    _, mod_suffix, render_name, build_name, *_ = _SLUG_TO_META[slug]
    module = importlib.import_module(f"svg_relation_lib.presets.{mod_suffix}")
    render_fn = getattr(module, render_name)
    build_fn = getattr(module, build_name, None)
    hero_default = None
    for attr in dir(module):
        if attr.startswith("HERO_") and attr.endswith("_DATA"):
            val = getattr(module, attr)
            if val is not None:
                hero_default = val
                break
    return render_fn, build_fn, hero_default


def _sample_data_error(slug: str) -> str:
    return (
        f"{slug}: relation data is required. Built-in HERO_*_DATA sample content is "
        "disabled by default to prevent fake business content from entering formal "
        "Slides. Pass data= or build_kwargs with real case content. For local "
        "preview/regression fixtures only, pass allow_sample_data=True or CLI "
        "--sample-data."
    )


_CHROME_ONLY_BUILD_KEYS = {
    "kicker",
    "figure_title",
    "title",
    "figure_subtitle",
    "subtitle",
    "figure_caption",
    "caption",
    "source",
    "footer_source",
    "footer_method",
    "footer_ref",
    "encoding_note",
}


def _has_payload_build_kwargs(build_kwargs: Dict[str, Any]) -> bool:
    return any(str(key).lower() not in _CHROME_ONLY_BUILD_KEYS for key in build_kwargs)


def _build_relation_data(
    slug: str,
    build_fn: Optional[Callable],
    hero_default: Any,
    build_kwargs: Optional[Dict[str, Any]],
    *,
    allow_sample_data: bool,
) -> Any:
    """Resolve relation data without silently falling back to sample content."""
    kwargs = build_kwargs or {}
    has_build_kwargs = bool(kwargs)

    if not has_build_kwargs and not allow_sample_data:
        raise RuntimeError(_sample_data_error(slug))
    if has_build_kwargs and not allow_sample_data and not _has_payload_build_kwargs(kwargs):
        raise RuntimeError(
            f"{slug}: build_kwargs only contains title/chrome fields. Pass actual "
            "relation payload fields such as root, children, branches, layers, "
            "modules, or data=; use allow_sample_data=True only for "
            "local preview/regression fixtures."
        )

    built = None
    if build_fn is not None:
        try:
            built = build_fn(**kwargs)
        except TypeError as e:
            if not allow_sample_data:
                raise TypeError(
                    f"{slug}: build_kwargs are invalid and sample fallback is disabled: {e}"
                ) from e
            import warnings
            warnings.warn(
                f"{slug}: build_fn(**build_kwargs) raised TypeError: {e}. "
                "Using explicitly requested sample data.",
                RuntimeWarning,
            )
    elif has_build_kwargs:
        raise RuntimeError(f"{slug}: preset has no build function; pass data= instead.")

    if built is None or isinstance(built, (tuple, list)):
        if allow_sample_data and hero_default is not None:
            return hero_default
        raise RuntimeError(
            f"{slug}: build function did not return relation data and sample fallback "
            "is disabled. Pass data= or valid build_kwargs."
        )
    return built


# ═════════════════════════════════════════════════════════════════
# public API
# ═════════════════════════════════════════════════════════════════

def make_relation(slug: str,
                    data: Optional[Any] = None,
                    build_kwargs: Optional[Dict[str, Any]] = None,
                    skin: Optional[str] = None,
                    palette: Optional[str] = None,
                    font_family: Optional[str] = None,
                    allow_sample_data: bool = False,
                    shrink: bool = True,
                    return_meta: bool = False,
                    **render_kwargs: Any):
    """按 slug 生成 SVG 字符串 (可选 shrink viewBox / 返回元数据).

    Args:
        slug: relation type key (见 _RELATION_META, 或 --list)
        data: 已构造的 schema 对象. 正式 PPT 推荐直接传 data.
        build_kwargs: 传给 build_<slug>_data(...) 的 kwargs. 正式 PPT 必须来自真实业务内容.
        skin: **skin = 结构骨架** (字体 / 装饰母题 / marker / chrome).
            默认 `editorial_atelier`. 可选见 `svg_relation_lib.skins.registry.list_skins()`.
        palette: **palette = 颜色系统** (bg / ink / 8 支 hue).
        font_family: **统一字体** (可选). 传字符串 (如 `'PingFang SC, sans-serif'` 或
            `'Georgia, serif'`) 时, body 与 heading 都用它——让 svg 里的字跟 slide 主字体保持一致.
            None (默认) 时, 由 skin 决定字体 (跟 chart 侧 make_chart(font_family=...) 语义对齐).
        allow_sample_data: 默认 False. 只有本地预览/回归测试才传 True, 允许使用内置 HERO_*_DATA.
            正式 PPT 不允许隐式样例数据, 避免假业务内容误入交付物.
        shrink: 自动收紧 viewBox 到实际内容 bbox (默认 True). 收紧后 embed 时无留白.
        return_meta: 若 True 返回 dict `{svg, viewBox, embed_sizes}`; 默认 False 只返回 svg str.
        **render_kwargs: 传给 render_fn 的其他 kwargs.

    Returns:
        默认: SVG string
        return_meta=True 时: dict
          - svg: str
          - viewBox: (x, y, w, h) tuple (shrink 后)
          - embed_sizes: {"1.0": (w,h), "0.8": ..., "0.7": ..., "0.6": ...} 4 档等比缩放
    """
    render_fn, build_fn, hero_default = _load_preset(slug)
    if data is None:
        data = _build_relation_data(
            slug,
            build_fn,
            hero_default,
            build_kwargs,
            allow_sample_data=allow_sample_data,
        )

    # 决定是否要 skin/palette/font 切换
    need_switch = (skin and skin != "editorial_atelier") or palette or font_family
    if need_switch:
        with _apply_skin_palette(skin, palette, font_family) as override_palette:
            if override_palette is not None and "palette" not in render_kwargs:
                render_kwargs["palette"] = override_palette
            svg = render_fn(data, **render_kwargs)
    else:
        svg = render_fn(data, **render_kwargs)

    if shrink:
        from svg_relation_lib._viewbox import shrink_viewbox
        # pad_y=20 bottom-pad reserves 4-5pt slide-space buffer after atomize ·
        # keeps text descenders + shape halos inside slide canvas at slide_h=440.
        svg = shrink_viewbox(svg, pad_x=12.0, pad_y=20.0)

    if return_meta:
        from svg_relation_lib._viewbox import extract_viewbox, embed_sizes
        vb = extract_viewbox(svg)
        return {
            "svg": svg,
            "viewBox": vb,
            "embed_sizes": embed_sizes(vb) if vb else {},
        }
    return svg


def make_relation_atomized(slug: str,
                             slide_x0: float = 30.0,
                             slide_y0: float = 102.0,
                             slide_w: float = 900.0,
                             slide_h: float = 463.0,
                             *,
                             data: Optional[Any] = None,
                             build_kwargs: Optional[Dict[str, Any]] = None,
                             skin: Optional[str] = None,
                             palette: Optional[str] = None,
                             font_family: Optional[str] = None,
                             allow_sample_data: bool = False,
                             drop_background: bool = True,
                             drop_micro_gray_below: int = 0,
                             drop_text_below: int = 0,
                             min_slide_font_size: int = 10,
                             subtitle_svg_threshold: int = 0,
                             min_slide_font_size_subtitle: int = 8,
                             subtitle_slide_font_cap: int = 0,
                             subtitle_letter_spacing: float = 0.0,
                             subtitle_color_override: str = "",
                             strict_no_embed: bool = True,
                             return_svg: bool = False,
                             auto_size: bool = False,
                             **render_kwargs: Any):
    """按 slug 生成 SVG · 再原子化拆成 slide-native 元素 (可编辑 shape/line/text/custom).

    对比 make_relation:
      - make_relation → 返回整块 SVG string · 用 <embed> 塞一整张进 slide (模式 A)
      - make_relation_atomized → 返回 slide XML fragment (含独立 <shape>/<line>/custom shape) ·
        每元素可 select / move / delete / edit · 便于外部覆盖旁注/图标/KPI (模式 B)

    Args:
        slug: relation type key
        slide_x0/slide_y0: SVG 内容映射到 slide 的左上角坐标 (points)
        slide_w/slide_h: slide 上占位区域宽高 (points) · SVG viewBox 按此等比缩放
        data / build_kwargs / skin / palette / font_family / allow_sample_data / **render_kwargs: 同 make_relation
        drop_background: 默认 True · 跳过覆盖 viewBox ≥90% 的 canvas 底色 rect ·
            让关系图透明融入 slide 背景色 · 若你故意想要一个底色框包住关系图 · 传 False
        drop_micro_gray_below: 默认 0 (关) · 保守版 · >0 时跳过字号 < 该值 且颜色是中灰的 text ·
            仅当你需要保留有色小字但只想清灰噪点时开 (推荐值 8)
        drop_text_below: 默认 0 (关) · 保留所有 text 不做过滤 ·
            按字号一刀切容易误删中文主 label · 默认关闭让 relation 图完整呈现 ·
            如需清小字 (英文主导 + 只留主结构): 显式传 7-9pt 阈值 · 传越大越狠
        min_slide_font_size: 默认 10 · slide-space 最小字号硬 clamp ·
            avoid slide_h 非等比缩小 (Y-scale<1) 导致 text < 10pt 挤成一坨 ·
            传 0 关闭 clamp (旧行为)
        strict_no_embed: 默认 True · 如果 atomized 输出仍残留 `<embed>` 直接失败，
            避免关系图静默退化为不可编辑图元。只有明确接受小 SVG fallback 保真时才传 False.
        return_svg: True 则返回 (fragment, svg_str) · False (默认) 只返回 fragment

    Returns:
        默认: slide XML fragment str · 格式 `<slide><data>...</data></slide>`
          调用者取 `<data>` 内子元素追加到自己的 slide XML 主体 · 或直接把整块 append
        return_svg=True: (fragment, svg_str) 二元组

    典型用法 (在自己 slide 里嵌鱼骨图 · 保留可编辑元素):
        from gen_svg_relations import make_relation_atomized
        frag = make_relation_atomized('al_fishbone',
                                        slide_x0=40, slide_y0=110,
                                        slide_w=880, slide_h=440,
                                        build_kwargs={'effect': '...', 'branches': [...]})
        # frag 里的 <shape>/<line> 直接放到 slide XML 的 <data> 里
        # 想加旁注只需外面另加 <shape type="text" ...>
    """
    import re
    # Bucket F 新方向 (2026-09-12): auto_size · 每 preset 有 recommended slide size
    # 若 auto_size=True 且 caller 用默认 900×463 · 用 preset 推荐尺寸覆盖 · 让复杂 preset 获得更大空间
    # 覆盖标准: viewBox 大或 y-span 长的保留 preset → 900×540
    _RECOMMENDED_ATOMIZE_SIZE = {
        # 复杂 preset · 主图 y-span >700 · 元素密度高 · 需要 slide_h 540 让主图不缩小
        # 关键: slide canvas 硬边界 960×540 · 所以 slide_w ≤ 900 (留 30pt padding × 2), slide_h ≤ 540
        "tx_taxonomy": (900, 540),
        "cs_c4": (900, 540),
        "cu2_curriculum": (900, 540),  # audit group1 FAIL · 与 tx_taxonomy 同级复杂度
        "bl_bloom": (900, 540),  # audit group1 · 双 legend + KPI 侧栏需要 540 高
        # ~2:1 常规 preset 保持默认
    }
    if auto_size and slide_w == 900.0 and slide_h == 463.0 and slug in _RECOMMENDED_ATOMIZE_SIZE:
        rw, rh = _RECOMMENDED_ATOMIZE_SIZE[slug]
        slide_w, slide_h = float(rw), float(rh)
        # 关键 · auto_size 覆盖 slide_h 时 · 若 caller 用默认 slide_y0=102 或 30 → 底 y 会溢出 canvas 540
        # 主动把 slide_y0 拉到 canvas 允许的最大 top offset: canvas_h(540) - slide_h · 保底 0
        _CANVAS_H = 540.0
        max_y0 = max(0.0, _CANVAS_H - slide_h)
        if slide_y0 > max_y0:
            slide_y0 = max_y0
    # 复用 make_relation 拿 shrunk SVG
    svg_str = make_relation(
        slug, data=data, build_kwargs=build_kwargs,
        skin=skin, palette=palette, font_family=font_family,
        allow_sample_data=allow_sample_data,
        shrink=True,
        return_meta=False, **render_kwargs,
    )

    # 取 shrunk viewBox (原子化用它做坐标映射)
    vb_m = re.search(r'viewBox="([^"]+)"', svg_str)
    if not vb_m:
        raise RuntimeError(f"{slug}: shrunk SVG missing viewBox")
    vb_parts = vb_m.group(1).split()
    svg_vb_x, svg_vb_y, svg_vb_w, svg_vb_h = (float(v) for v in vb_parts)

    # 把 SVG 写到临时文件 (atomize_svg_to_slide 要 Path 输入)
    import tempfile, os
    from pathlib import Path
    from atomize_svg_to_slide import atomize_svg_to_slide, set_mapping, set_drop_background, set_drop_micro_gray, set_drop_text_below, set_min_slide_font_size, set_subtitle_relax

    # 关键 · atomize 用 viewBox 空间坐标 · 但 viewBox 可能不从 (0,0) 起
    # atomize 内部 _sx(x) = slide_x0 + x * slide_w / svg_w · 只对 (0,0) 起的 viewBox 正确
    # 若 shrunk viewBox 非 (0,0) · 需要外部先把 SVG 的坐标全平移到 (0,0) 起
    # 简单方案: 让 atomize 认为 svg 尺寸是 viewBox 的 w/h · 平移由 svg 自身承担
    # 但 atomize 是逐元素 parse tag 属性 · 元素属性里的 x/y 是原坐标系 · 未减去 viewBox 起点
    # 所以正确做法: 把 slide_x0 相对减去 (svg_vb_x, svg_vb_y) 的映射
    # 即 slide 坐标 = slide_x0 + (elem_x - svg_vb_x) * slide_w / svg_vb_w
    # 等价于 set_mapping(svg_w=svg_vb_w, svg_h=svg_vb_h, slide_x0=slide_x0 - svg_vb_x * (slide_w/svg_vb_w), ...)
    scale_x = slide_w / svg_vb_w
    scale_y = slide_h / svg_vb_h
    adj_slide_x0 = slide_x0 - svg_vb_x * scale_x
    adj_slide_y0 = slide_y0 - svg_vb_y * scale_y
    set_mapping(svg_w=svg_vb_w, svg_h=svg_vb_h,
                slide_x0=adj_slide_x0, slide_y0=adj_slide_y0,
                slide_w=slide_w, slide_h=slide_h)
    set_drop_background(drop_background)
    set_drop_micro_gray(drop_micro_gray_below)
    set_drop_text_below(drop_text_below)
    set_min_slide_font_size(min_slide_font_size)
    set_subtitle_relax(
        svg_threshold=subtitle_svg_threshold,
        min_slide_font=min_slide_font_size_subtitle,
        slide_font_cap=subtitle_slide_font_cap,
        letter_spacing=subtitle_letter_spacing,
        color_override=subtitle_color_override,
    )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".svg", delete=False) as f:
        f.write(svg_str)
        tmp_path = f.name
    try:
        fragment = atomize_svg_to_slide(Path(tmp_path))
    finally:
        os.unlink(tmp_path)

    if strict_no_embed and "<embed" in fragment:
        raise RuntimeError(
            f"{slug}: atomized relation output still contains {fragment.count('<embed')} <embed> element(s); "
            "fix atomize_svg_to_slide.py or pass strict_no_embed=False only for explicit non-editable fallback."
        )

    if return_svg:
        return fragment, svg_str
    return fragment


import contextlib

@contextlib.contextmanager
def _apply_skin_palette(skin_name: Optional[str],
                         palette_name: Optional[str],
                         font_family: Optional[str] = None):
    """临时应用 skin/palette/font_family 到 editorial_atelier module.

    skin (结构骨架) 决定 svg_defs / hero_chrome / hero_footer / chip_pill 等函数行为
    palette (颜色系统) 决定 HUE 字典和 PALETTE 对象
    font_family (可选) 覆盖 skin 里的 FONT_SANS / FONT_SERIF, body+heading 都用它 ·
        跟 chart 侧 `make_chart(font_family=...)` 语义一致 · 让 svg 字体跟 slide 主字体对齐

    Yields:
        override_palette (Palette or None) · 若指定了 skin/palette 则为对应 Palette 对象
    """
    from svg_relation_lib.skins.registry import (
        get_skin as _get_skin,
        set_active_skin as _set_active_skin,
        clear_active_skin as _clear_active_skin,
    )
    from svg_relation_lib.skins import editorial_atelier as ea

    # 备份原值
    original_hue = dict(ea.HUE)
    original_palette = ea.BONE_RUST
    original_font_sans = ea.FONT_SANS
    original_font_serif = ea.FONT_SERIF

    # 决定新 HUE + 新 palette + active skin module
    new_hue = original_hue
    new_palette_obj = None  # Palette dataclass (skin 里 PALETTE / BONE_RUST)
    skin_mod = None         # active skin · 用于 preset opt-in draw_node 分流

    if skin_name and skin_name != "editorial_atelier":
        skin_mod = _get_skin(skin_name)
        new_hue = dict(skin_mod.HUE)
        new_palette_obj = skin_mod.PALETTE

    if palette_name:
        # palette 覆盖 skin 的颜色
        from svg_relation_lib.palettes_ext import get_palette
        pal = get_palette(palette_name)
        new_hue = dict(pal.hues)
        # 用 palette 的 bg/ink 造一个 Palette dataclass override
        # 注意: 我们需要保留 skin 的字体/kicker 参数, 只覆盖 bg/ink/primary/accent
        base_palette = new_palette_obj or original_palette
        from dataclasses import replace
        new_palette_obj = replace(
            base_palette,
            name=pal.name,
            bg=pal.bg,
            ink=pal.ink,
            primary=pal.primary,
            accent=pal.accent,
        )

    # 应用
    if new_hue is not original_hue:
        ea.HUE.clear()
        ea.HUE.update(new_hue)
    if new_palette_obj is not None:
        ea.BONE_RUST = new_palette_obj
    if skin_mod is not None:
        _set_active_skin(skin_mod)
    # font_family 覆盖: 单字体, body + heading 都用它 · 跟 chart 侧一致
    # 同时覆写 active skin 模块的 FONT_SANS / FONT_SERIF, 让 skin.draw_node 也响应
    skin_font_backup = None
    if font_family:
        ea.FONT_SANS = font_family
        ea.FONT_SERIF = font_family
        # 同步覆盖 palette 上的 font_families (skin 可能通过 palette 读)
        if new_palette_obj is not None:
            try:
                from dataclasses import replace
                new_palette_obj = replace(
                    new_palette_obj,
                    head_family=font_family,
                    body_family=font_family,
                )
                ea.BONE_RUST = new_palette_obj
            except Exception:
                # replace 失败时 (字段不存在), 静默兜底 · font 仍通过 FONT_SANS/FONT_SERIF 生效
                pass
        # active skin module 里的 FONT_SANS / FONT_SERIF 也覆写 (skin.draw_node 用它们)
        if skin_mod is not None:
            skin_font_backup = {}
            for k in ("FONT_SANS", "FONT_SERIF"):
                if hasattr(skin_mod, k):
                    skin_font_backup[k] = getattr(skin_mod, k)
                    setattr(skin_mod, k, font_family)

    try:
        yield new_palette_obj
    finally:
        ea.HUE.clear()
        ea.HUE.update(original_hue)
        ea.BONE_RUST = original_palette
        ea.FONT_SANS = original_font_sans
        ea.FONT_SERIF = original_font_serif
        if skin_font_backup and skin_mod is not None:
            for k, v in skin_font_backup.items():
                setattr(skin_mod, k, v)
        if skin_mod is not None:
            _clear_active_skin()


def list_relations(schema: Optional[str] = None) -> List[str]:
    """列出全部 relation slug (可选按 schema 过滤)."""
    if schema is None:
        return [m[0] for m in _RELATION_META]
    return [m[0] for m in _RELATION_META if m[4] == schema]


def list_schemas() -> List[str]:
    """列出全部支持的 data schema 类型."""
    return list(_SCHEMA_ORDER)


# ═════════════════════════════════════════════════════════════════
# relation_help(slug=None) · 类似 chart_help
# ═════════════════════════════════════════════════════════════════

def relation_help(name: Optional[str] = None) -> str:
    """列出全部树状图的调用范式.

    relation_help()               → 总览 (11 种)
    relation_help('al_fishbone')  → 单张详情
    relation_help('tree')         → 当前支持的 relation 列表
    """
    if name is None:
        lines = [
            "# 11 种 SVG 树状图总览 (v2)",
            "",
            "## ⚠ 必读硬规则 (违反必崩)",
            "  1. **飞书 Slides 中的树状图必须可编辑**: 当前仅支持下方 11 个 slug。默认用 `make_relation_atomized(..., strict_no_embed=True)`，把图拆成 slide-native `<shape>` / `<line>` / `<shape type=\"text\">` / custom shape；残留 `<embed>` 会直接失败。不要把 `make_relation()` 的整块 SVG 直接塞进 `<embed>` 当最终页面主体。",
            "  2. **坐标框自适应**: `make_relation_atomized(..., slide_x0=..., slide_y0=..., slide_w=..., slide_h=...)` 会按 SVG viewBox 映射到 slide 区域；复杂 preset 可加 `auto_size=True`。",
            f"  3. **曲线 lint 提醒**: {_CURVE_LINT_NOTE}",
            "  4. **非编辑型 SVG 只用于预览/导出**: 只有用户明确接受不可编辑插图，才用 `make_relation(..., return_meta=True)` 再写 `<embed>`。",
            "  5. **底色留白**: SVG 自带满版底色 (匹配 palette.bg). 若 slide 底色跟 palette.bg 不一致会显得突兀. 简单做法: 保证 slide 底色与所选 palette.bg 一致.",
            "  6. **kicker 是可选装饰**: 默认为空字符串. 想加分类小标签时 build_kwargs 传 kicker; 别放框架名 (如 `FISHBONE`) 那对读者没语义.",
            "",
            "## 通用规则",
            "  - **正式 PPT 必须传真实数据**：Python 传 `data=` 或 `build_kwargs={...}`；CLI 传 `--data-file real_case.json`。",
            "  - **无参默认样例已关闭**：内置 HERO_*_DATA 只允许本地预览/回归测试显式启用 `allow_sample_data=True` 或 CLI `--sample-data`。",
            "  - Python: `frag = make_relation_atomized('slug', build_kwargs={...}, slide_x0=40, slide_y0=90, slide_w=880, slide_h=360, auto_size=True)`；把返回片段中 `<data>` 的子元素并入你的 slide `<data>`。",
            "  - CLI: `python3 scripts/gen_svg_relations.py --type <slug> --data-file real_case.json --atomized > relation.xml` 输出可编辑 slide fragment。",
            "  - 只有做非编辑型 SVG 预览时才用：`res = make_relation('slug', build_kwargs={...}, return_meta=True); svg = res['svg']`。",
            "  - 仅本地看样例：`make_relation('slug', allow_sample_data=True)` 或 `python3 scripts/gen_svg_relations.py --type <slug> --sample-data`。",
            "",
            "## skin × palette × font_family (正交切换)",
            "  - **skin** = 结构骨架 (字体 / 装饰母题 / marker / chrome). 每个场景推荐一个 skin.",
            "  - **palette** = 颜色系统 (bg / ink / 8 支 hue). 与 skin 正交, deck 里换色只换 palette.",
            "  - **font_family** = 覆盖 skin 字体 · 单字符串, body+heading 都用它 (跟 chart 侧 `make_chart(font_family=)` 语义一致). 用来让 svg 里的字跟 slide 主字体保持一致.",
            "  - 8 skin: `editorial_atelier` · `boardroom_navy` · `duolingo_cream` · `pitch_neon` · `luxury_manual` · `mbb_consulting` · `journal_ivory` · `technical_whitepaper`",
            "  - 25 palette (跟 chart 侧 palette 名对齐, deck 里 chart 和 relation 用同一个 palette 名保持视觉一致):",
            "    - **warm 底 (13)**: `bone_rust` · `exec_navy` · `classroom_indigo` · `forest_luxe` · `ivory_indigo` · `archive_ink` · `hbs_case` · `cell_press` · `rust_terracotta` · `tea_ceremony` · `stone_ink` · `linen_plum` · `meadow_science`",
            "    - **cool 底 (6)**: `burgundy_analyst` · `sapphire_dev` · `gs_research` · `sage_review` · `grape_eclectic` · `pine_engineering`",
            "    - **dark 深底 (6)**: `merlot_pitch` · `mocha_kpi` · `nightlab` · `terminal_neon` · `candlelight` · `deep_sea_navy`",
            "  - 用法: `make_relation('al_fishbone', build_kwargs={...}, skin='boardroom_navy', palette='mocha_kpi', font_family='PingFang SC, sans-serif')`",
            "",
            "## 如何选图",
            "  1. 先在支持清单中选最贴近的树状结构",
            "  2. 用 `relation_help('<slug>')` 查看该 preset 的详细数据格式",
            "",
        ]
        for schema in _SCHEMA_ORDER:
            items = [m for m in _RELATION_META if m[4] == schema]
            if not items:
                continue
            desc = _SCHEMA_DESCRIPTIONS.get(schema, "")
            lines.append(f"## `{schema}` schema ({len(items)} 张)")
            lines.append(f"  {desc}")
            lines.append("")
            for slug, _, _, _, _, scene, hint in items:
                lines.append(f"  - `{slug}` · {scene}")
                lines.append(f"    数据: {hint}")
            lines.append("")
        lines.append("查看单张详情: `relation_help('al_fishbone')`")
        lines.append("查看当前支持列表: `relation_help('tree')`")
        return "\n".join(lines)

    # schema 名 → 列出该 schema 下所有 preset
    if name in _SCHEMA_ORDER:
        items = [m for m in _RELATION_META if m[4] == name]
        desc = _SCHEMA_DESCRIPTIONS.get(name, "")
        lines = [
            f"# `{name}` schema ({len(items)} 张)",
            "",
            desc,
            "",
        ]
        for slug, _, _, _, _, scene, hint in items:
            lines.append(f"## `{slug}` · {scene}")
            lines.append(f"  数据: {hint}")
            lines.append("")
        return "\n".join(lines)

    # 单张详情
    if name not in _SLUG_TO_META:
        return (
            f"'{name}' not found. Available slugs: "
            + ", ".join(m[0] for m in _RELATION_META)
            + f"\nAvailable schemas: {', '.join(_SCHEMA_ORDER)}"
        )
    slug, mod_suffix, render_name, build_name, schema, scene, hint = _SLUG_TO_META[name]
    docstring = ""
    build_doc = ""
    try:
        render_fn, build_fn, _ = _load_preset(slug)
        docstring = render_fn.__doc__ or "(no docstring)"
        build_doc = build_fn.__doc__ if build_fn else ""
    except Exception as e:
        docstring = f"(failed to load: {e})"

    schema_desc = _SCHEMA_DESCRIPTIONS.get(schema, "")
    return (
        f"# {slug} · {scene}\n\n"
        f"**data schema**: `{schema}` · {schema_desc}\n\n"
        f"**module**: `svg_relation_lib.presets.{mod_suffix}`\n"
        f"**render fn**: `{render_name}`\n"
        f"**build fn**: `{build_name}`\n\n"
        f"**数据格式**: {hint}\n\n"
        f"**⚠ 可编辑硬规则**: 飞书 Slides 正式页面默认调用 `make_relation_atomized('{slug}', ..., strict_no_embed=True)`，"
        f"把树状图拆成可编辑 `<shape>` / `<line>` / 文本框 / custom shape；残留 `<embed>` 会直接失败，不要用整块 `<embed>` 作为树状图主体。"
        f"`make_relation()` 仅用于非编辑型 SVG 预览或导出。\n\n"
        f"**曲线 lint 提醒**: {_CURVE_LINT_NOTE}\n\n"
        f"**数据安全规则**: 正式 PPT 必须传 `data=` 或真实业务 `build_kwargs={{...}}`; "
        f"无参内置样例默认禁用。只有本地预览/回归测试才传 `allow_sample_data=True` 或 CLI `--sample-data`.\n\n"
        f"**kicker 提示**: 默认空. 想加分类小标签就传 `build_kwargs={{'kicker': '业务名', ...}}`; "
        f"别放框架名 (如 `FISHBONE`) — 那对读者没语义.\n\n"
        f"**调用示例**:\n"
        f"```python\n"
        f"from gen_svg_relations import make_relation_atomized\n"
        f"frag = make_relation_atomized('{slug}', build_kwargs={{...}}, slide_x0=40, slide_y0=90, slide_w=880, slide_h=360, auto_size=True)\n"
        f"# 把 frag 的 <data> 子元素并入当前 slide 的 <data>；主体元素可在 Slides 中选择和编辑\n"
        f"# 仅本地预览内置样例:\n"
        f"# frag = make_relation_atomized('{slug}', allow_sample_data=True, slide_x0=40, slide_y0=90, slide_w=880, slide_h=360)\n"
        f"```\n\n"
        f"**render fn docstring**:\n```\n{docstring}\n```\n\n"
        + (f"**build fn docstring**:\n```\n{build_doc}\n```\n" if build_doc else "")
    )


# ═════════════════════════════════════════════════════════════════
# CLI
# ═════════════════════════════════════════════════════════════════

def _cli():
    ap = argparse.ArgumentParser(
        description="11 种 v2 树状图的统一 SVG 生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--type", help="relation slug (见 --list)")
    ap.add_argument("--data-file", help="JSON 文件, 传给 build_<slug>_data(**json) 的 kwargs")
    ap.add_argument("--skin", help="skin 骨架 (editorial_atelier / boardroom_navy / duolingo_cream / pitch_neon / luxury_manual / mbb_consulting / journal_ivory / technical_whitepaper)")
    ap.add_argument("--palette", help="palette 颜色 (bone_rust / exec_navy / mocha_kpi / nightlab / ... 见 --list-palettes)")
    ap.add_argument("--font-family", help="统一字体 · 单字符串, body+heading 都用它 (如 'PingFang SC, sans-serif' 或 'Georgia, serif'). 跟 chart 侧 make_chart(font_family=) 语义一致.")
    ap.add_argument("--sample-data", "--allow-sample-data", dest="sample_data", action="store_true", help="仅本地预览/回归测试使用: 允许在未提供 --data-file 时使用内置 HERO_*_DATA 样例")
    ap.add_argument("--atomized", action="store_true", help="输出可编辑 slide-native XML fragment，而不是整块 SVG")
    ap.add_argument("--slide-x0", type=float, default=30.0, help="--atomized 输出映射到 slide 的左上角 X")
    ap.add_argument("--slide-y0", type=float, default=102.0, help="--atomized 输出映射到 slide 的左上角 Y")
    ap.add_argument("--slide-w", type=float, default=900.0, help="--atomized 输出映射到 slide 的宽度")
    ap.add_argument("--slide-h", type=float, default=463.0, help="--atomized 输出映射到 slide 的高度")
    ap.add_argument("--auto-size", action="store_true", help="--atomized 时按复杂 preset 推荐尺寸自动调整")
    ap.add_argument("--out", help="输出文件路径 (默认 stdout)")
    ap.add_argument("--list", action="store_true", help="列出全部支持的 slug")
    ap.add_argument("--list-skins", action="store_true", help="列出全部 skin")
    ap.add_argument("--list-palettes", action="store_true", help="列出全部 palette (按 tone 分组)")
    ap.add_argument("--help-slug", help="展示单张 relation 或整个 schema 的详情")
    ap.add_argument("--category", help=f"过滤 schema (与 --list 联用) · 可选: {', '.join(_SCHEMA_ORDER)}")
    args = ap.parse_args()

    if args.list_skins:
        from svg_relation_lib.skins.registry import list_skins, get_skin
        for name in list_skins():
            s = get_skin(name)
            print(f"  {name:22s} bg={s.PALETTE.bg:8s} primary={s.HUE['rust']}")
        return

    if args.list_palettes:
        from svg_relation_lib.palettes_ext import list_palettes, get_palette
        by_tone: Dict[str, List[str]] = {"warm": [], "cool": [], "dark": []}
        for name in list_palettes():
            by_tone[get_palette(name).tone].append(name)
        for tone in ["warm", "cool", "dark"]:
            print(f"## {tone} ({len(by_tone[tone])})")
            for name in by_tone[tone]:
                p = get_palette(name)
                print(f"  {name:22s} bg={p.bg:8s} primary={p.primary:8s} · {p.origin}")
            print()
        return

    if args.list:
        by_schema: Dict[str, List[str]] = {}
        for m in _RELATION_META:
            if args.category and m[4] != args.category:
                continue
            by_schema.setdefault(m[4], []).append(m[0])
        for schema in _SCHEMA_ORDER:
            slugs = by_schema.get(schema, [])
            if not slugs:
                continue
            print(f"## {schema} schema ({len(slugs)})")
            for s in slugs:
                meta = _SLUG_TO_META[s]
                print(f"  {s:20s} {meta[5]}")
            print()
        return

    if args.help_slug:
        print(relation_help(args.help_slug))
        return

    if not args.type:
        ap.error("必须传 --type <slug> 或 --list · 或 --help-slug <slug|schema>")

    build_kwargs: Dict[str, Any] = {}
    if args.data_file:
        with open(args.data_file) as f:
            build_kwargs = json.load(f)

    if args.atomized:
        fragment = make_relation_atomized(
            args.type,
            slide_x0=args.slide_x0,
            slide_y0=args.slide_y0,
            slide_w=args.slide_w,
            slide_h=args.slide_h,
            build_kwargs=build_kwargs,
            skin=args.skin,
            palette=args.palette,
            font_family=args.font_family,
            allow_sample_data=args.sample_data,
            auto_size=args.auto_size,
        )
        if args.out:
            with open(args.out, "w") as f:
                f.write(fragment)
            print(f"[write] {args.out} · {len(fragment)} chars · atomized", file=_sys.stderr)
        else:
            print(fragment)
        print(
            f"[atomized] shape={fragment.count('<shape')} line={fragment.count('<line')} embed={fragment.count('<embed')}",
            file=_sys.stderr,
        )
        return

    result = make_relation(args.type, build_kwargs=build_kwargs,
                            skin=args.skin, palette=args.palette,
                            font_family=args.font_family,
                            allow_sample_data=args.sample_data,
                            return_meta=True)
    svg = result["svg"]
    vb = result["viewBox"]
    sizes = result["embed_sizes"]

    if args.out:
        with open(args.out, "w") as f:
            f.write(svg)
        print(f"[write] {args.out} · {len(svg)} chars", file=_sys.stderr)
    else:
        print(svg)

    # 元数据 · 帮助模型决定 embed 尺寸
    if vb:
        vx, vy, vw, vh = vb
        print(f"[viewBox] x={vx:.0f} y={vy:.0f} w={vw:.0f} h={vh:.0f} "
              f"(aspect ratio {vw/vh:.2f}:1)", file=_sys.stderr)
    if sizes:
        print(f"[embed sizes · pick one · width:height must equal viewBox]:",
              file=_sys.stderr)
        for scale, (w, h) in sizes.items():
            print(f"  {scale}× : <embed width={w} height={h}>", file=_sys.stderr)


if __name__ == "__main__":
    _cli()
