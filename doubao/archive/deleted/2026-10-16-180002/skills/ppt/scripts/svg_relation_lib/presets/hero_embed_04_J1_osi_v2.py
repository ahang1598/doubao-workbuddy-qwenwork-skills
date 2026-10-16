"""HERO EMBED · 04_J1_osi V2 · OSI hero (1400×720) codified.

Replaces the embed-only v1 (900×336) with a 1:1 codification of
`final_svg_relation/04_J1_osi/step1_reference/osi_hero_reference.svg`:

  - viewBox 1400 × 720
  - Chrome: serif title + subtitle + hairline + FIGURE tag
  - Left USER-VISIBLE / BITS & SIGNALS axis with two-way arrows
  - 4-8 horizontal layer bars, each carrying accent slab + serif number badge
    + name + purpose caption + PDU pill + protocols headline + italic note
  - Optional right TCP/IP mapping panel (groups of consecutive OSI layers)
  - Optional bottom encapsulation strip (L7 outer envelope → L4 → L3 → L2
    header → payload → L2 trailer → serialize arrow → L1 wire + bit ticks)
    with SEND / RECEIVE direction annotations
  - Footer notes hairline + one-line prose (optional)

API:
  * ``build_osi_data(...)``            — assemble a Tree with the right
    extras for the layout to consume.
  * ``render_hero_embed_j1_osi_v2(...)`` — render the hero SVG.

Extensibility:
  * ``n_layers`` ∈ [3, 8] — a 7-layer OSI baseline or a 4-layer TCP/IP.
  * TCP/IP mapping panel and encapsulation strip are both opt-in.
  * Each layer's hue is a free-form key resolved by ``_OSI_HUES``.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ..schemas import Tree, TreeNode
from ..palettes import Palette
from ..engine import esc
from ..layouts.osi_stack_v2 import (
    osi_stack_v2_layout,
    LayoutOverflow,
    OSIStackParams,
)
from ..skins.editorial_atelier import BONE_RUST, FONT_SERIF, FONT_SANS
from ..skins.registry import get_active_skin as _get_active_skin


def _try_skin_draw(kind: str, x: float, y: float, w: float, h: float,
                   label: str, palette: Palette, **kwargs) -> Optional[str]:
    """opt-in skin 分流 · 与 fishbone preset 相同的兜底策略."""
    skin_mod = _get_active_skin()
    if skin_mod is None:
        return None
    skin_inst = getattr(skin_mod, "SKIN_INSTANCE", None)
    if skin_inst is None:
        return None
    draw_fn = getattr(skin_inst, "draw_node", None)
    if draw_fn is None:
        return None
    try:
        return draw_fn(x, y, w, h, label, palette, kind=kind, **kwargs)
    except Exception:
        return None


# ═════════════════════════════════════════════════════════════════
# OSI-specific hues (match the reference SVG exactly · not editorial hues)
# ═════════════════════════════════════════════════════════════════
_OSI_HUES: Dict[str, Tuple[int, int, int]] = {
    "purple":   (105, 75, 130),
    "teal":     (40, 130, 160),
    "green":    (32, 138, 108),
    "gold":     (200, 140, 50),
    "navy":     (60, 100, 155),
    "brick":    (170, 90, 70),
    "red":      (192, 70, 85),
    # bonus slots for dense 8-layer variant
    "indigo":   (85, 95, 165),
    "olive":    (140, 130, 55),
}

_INK = "rgba(24,26,34,1)"
_GRAY = "rgba(115,120,132,1)"
_INK_SOFT = "rgba(64,70,82,1)"
_HAIR = "rgba(175,178,188,1)"
_BG = "rgba(250,246,235,1)"


def _hue(name: str, alpha: float = 1.0) -> str:
    r, g, b = _OSI_HUES.get(name, _OSI_HUES["red"])
    return f"rgba({r},{g},{b},{alpha:.3f})"


VIEW_W = 1400
VIEW_H = 720


def _est_svg_text_w(
    text: str,
    font_size: float,
    *,
    bold: bool = False,
    letter_spacing: float = 0.0,
) -> float:
    """Approximate text width using atomize_svg_to_slide's glyph buckets."""
    if not text:
        return 0.0
    total = 0.0
    for ch in text:
        cp = ord(ch)
        if cp > 0x2E80:
            total += font_size * 1.05
        elif ch.isspace():
            total += font_size * 0.35
        elif ch in "·×→↑↓←◆◈§":
            total += font_size * 0.7
        elif ch.isupper():
            total += font_size * 0.72
        elif ch.isdigit():
            total += font_size * 0.55
        else:
            total += font_size * 0.58
    if bold:
        total *= 1.04
    if len(text) > 1 and letter_spacing:
        total += (len(text) - 1) * letter_spacing
    return total


def _fit_svg_font_size(
    text: str,
    max_w: float,
    base_size: float,
    *,
    min_size: float,
    bold: bool = False,
    letter_spacing: float = 0.0,
) -> float:
    """Shrink a single SVG text run enough to fit its reserved width."""
    if not text or max_w <= 0:
        return base_size
    width = _est_svg_text_w(
        text, base_size, bold=bold, letter_spacing=letter_spacing
    )
    if width <= max_w:
        return base_size
    return max(min_size, base_size * max_w / width)


# ═════════════════════════════════════════════════════════════════
# Baseline data · 7-layer OSI (matches osi_hero_reference.svg)
# ═════════════════════════════════════════════════════════════════
BASELINE_LAYERS: List[Dict[str, Any]] = [
    {
        "no": 7, "short": "L7", "name": "Application", "hue": "purple",
        "purpose": "User-facing services · what apps talk",
        "pdu": "DATA",
        "protocols": "HTTP · SMTP · DNS · SSH · FTP",
        "note": "Browsers, mail clients, APIs — the intent surface",
        "tcpip_key": "app",
    },
    {
        "no": 6, "short": "L6", "name": "Presentation", "hue": "teal",
        "purpose": "Syntax translation · encoding · encryption",
        "pdu": "DATA",
        "protocols": "TLS · SSL · JPEG · ASCII · MIME",
        "note": "Serialize, compress, cipher — talk a common tongue",
        "tcpip_key": "app",
    },
    {
        "no": 5, "short": "L5", "name": "Session", "hue": "green",
        "purpose": "Dialog control · checkpoints · resume",
        "pdu": "DATA",
        "protocols": "NetBIOS · RPC · SOCKS · SIP",
        "note": "Open, keep, tear down conversations between hosts",
        "tcpip_key": "app",
    },
    {
        "no": 4, "short": "L4", "name": "Transport", "hue": "gold",
        "purpose": "End-to-end delivery · ports · reliability",
        "pdu": "SEGMENT / DATAGRAM",
        "protocols": "TCP · UDP · QUIC · SCTP",
        "note": "Ports, flow control, retransmit — TCP reliable, UDP fast",
        "tcpip_key": "transport",
    },
    {
        "no": 3, "short": "L3", "name": "Network", "hue": "navy",
        "purpose": "Routing between networks · logical addressing",
        "pdu": "PACKET",
        "protocols": "IPv4 · IPv6 · ICMP · OSPF · BGP",
        "note": "IP address, routing tables — hop across subnets",
        "tcpip_key": "internet",
    },
    {
        "no": 2, "short": "L2", "name": "Data Link", "hue": "brick",
        "purpose": "Node-to-node frames · MAC addressing",
        "pdu": "FRAME",
        "protocols": "Ethernet · Wi-Fi · PPP · ARP · VLAN",
        "note": "MAC address, error detect — one link, one hop",
        "tcpip_key": "link",
    },
    {
        "no": 1, "short": "L1", "name": "Physical", "hue": "red",
        "purpose": "Raw signal · voltage · wavelength · pins",
        "pdu": "BIT",
        "protocols": "RJ-45 · Fiber · 802.11 radio · DSL",
        "note": "Copper, glass, air — where electrons and photons live",
        "tcpip_key": "link",
    },
]

BASELINE_TCPIP: List[Dict[str, Any]] = [
    {
        "key": "app", "label": "APPLICATION", "hue": "purple",
        "note": "TCP/IP · absorbs L5 · L6 · L7",
        "body": [
            "Covers: Application + Presentation + Session",
            "HTTP · TLS · DNS · SMTP · gRPC",
            "Serialization + encryption bundled here",
            "Kernel boundary above this line",
            "Where most application code sits",
            "Web, mail, RPC, streaming media",
        ],
    },
    {
        "key": "transport", "label": "TRANSPORT", "hue": "gold",
        "note": "", "body": ["TCP · UDP · QUIC · same as OSI L4"],
    },
    {
        "key": "internet", "label": "INTERNET", "hue": "navy",
        "note": "", "body": ["IP · ICMP · BGP · maps to OSI L3"],
    },
    {
        "key": "link", "label": "LINK", "hue": "brick",
        "note": "TCP/IP · fuses L1 + L2",
        "body": [
            "Covers: Data Link + Physical",
            "Ethernet · Wi-Fi · MAC · cabling · radio",
            "NIC drivers and firmware live here",
        ],
    },
]

BASELINE_ENCAP: List[Dict[str, Any]] = [
    {"kind": "header",  "hue": "purple", "top": "L7", "mid": "HTTP", "bot": "hdr"},
    {"kind": "header",  "hue": "gold",   "top": "L4", "mid": "TCP",  "bot": "hdr"},
    {"kind": "header",  "hue": "navy",   "top": "L3", "mid": "IP",   "bot": "hdr"},
    {"kind": "header",  "hue": "brick",  "top": "L2", "mid": "Eth",  "bot": "hdr"},
    {"kind": "payload", "top": "application payload",
     "note": "e.g. JSON body, HTML, image bytes"},
    {"kind": "trailer", "hue": "brick",  "top": "L2", "mid": "FCS",  "bot": "trailer"},
    {"kind": "wire",    "hue": "red",    "text": "L1 · bits on the wire · 1011010"},
]


# CN variant of the encap strip · auto-picked when the caller's layer names are
# CJK (see `_pick_chrome` + `build_osi_data`). Only the natural-language cells
# get localized — technical protocol names (HTTP/TCP/IP/Eth/FCS) stay Latin.
BASELINE_ENCAP_CN: List[Dict[str, Any]] = [
    {"kind": "header",  "hue": "purple", "top": "L7", "mid": "HTTP", "bot": "头"},
    {"kind": "header",  "hue": "gold",   "top": "L4", "mid": "TCP",  "bot": "头"},
    {"kind": "header",  "hue": "navy",   "top": "L3", "mid": "IP",   "bot": "头"},
    {"kind": "header",  "hue": "brick",  "top": "L2", "mid": "Eth",  "bot": "头"},
    {"kind": "payload", "top": "应用负载",
     "note": "如 JSON 报文 · HTML · 图片字节"},
    {"kind": "trailer", "hue": "brick",  "top": "L2", "mid": "FCS",  "bot": "尾"},
    {"kind": "wire",    "hue": "red",    "text": "L1 · 线上比特流 · 1011010"},
]


# ═════════════════════════════════════════════════════════════════
# Tree builder
# ═════════════════════════════════════════════════════════════════
def _has_cjk(s: str) -> bool:
    """True if any CJK character is present."""
    if not s:
        return False
    for ch in s:
        cp = ord(ch)
        if 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF:
            return True
    return False


# Default axis / TCP-IP / encap chrome text · English + Chinese variants ·
# `build_osi_data` auto-picks the CN variant when the first layer name is CJK
# (unless caller explicitly overrides the argument).
_CHROME_EN = {
    "axis_top_label": "USER-VISIBLE",
    "axis_bot_label": "BITS & SIGNALS",
    "axis_mid_label": "abstraction ↓ hardware",
    "tcpip_title": "TCP/IP MAPPING",
    "encap_headline": (
        "ENCAPSULATION · a packet gains a header at each layer going down, "
        "sheds one going up"
    ),
    "wire_caption_lines": (
        "Read left → right",
        "Each nested box is",
        "a header prepended",
    ),
    "arrow_send_text": "SEND · encapsulate down · L7 → L1",
    "arrow_recv_text": "RECEIVE · decapsulate up · L1 → L7",
}
_CHROME_CN = {
    "axis_top_label": "面向用户",
    "axis_bot_label": "比特与信号",
    "axis_mid_label": "抽象 ↓ 硬件",
    "tcpip_title": "TCP/IP 映射",
    "encap_headline": "封装 · 数据下行每层加头 · 上行每层剥头",
    "wire_caption_lines": (
        "从左到右阅读",
        "每层框都是",
        "外层的负载",
    ),
    "arrow_send_text": "发送 · 下行封装 · L7 → L1",
    "arrow_recv_text": "接收 · 上行解封装 · L1 → L7",
}


# Bucket H (2026-09-13) · subtract_level 默认预设
# L3 = 极简版 · 用户 2026-09-13 选定 · 默认参数
# L0 = 完全无减法 (老行为)
_SUBTRACT_L0: List[str] = []
_SUBTRACT_L1: List[str] = ["footer_hair", "footer_note", "layer_note"]
_SUBTRACT_L2: List[str] = _SUBTRACT_L1 + ["layer_purpose", "tcpip_sub"]
_SUBTRACT_L3: List[str] = _SUBTRACT_L2 + [
    "tcpip_brace",
    "encap_hairline", "encap_headline",
    "encap_arrow_send", "encap_arrow_recv", "encap_serialize",
    "encap_outer", "encap_header", "encap_payload", "encap_trailer",
    "encap_wire", "encap_wire_tick", "encap_wire_caption",
]
_SUBTRACT_MAP = {"L0": _SUBTRACT_L0, "L1": _SUBTRACT_L1, "L2": _SUBTRACT_L2, "L3": _SUBTRACT_L3}


def _resolve_skip_kinds(skip_kinds: Optional[List[str]], subtract_level: str) -> List[str]:
    """若 caller 显式传 skip_kinds → 用之 (含空 list = 完全无减法)
    否则用 subtract_level 映射 (默认 L3)."""
    if skip_kinds is not None:
        return list(skip_kinds)
    return list(_SUBTRACT_MAP.get(subtract_level, _SUBTRACT_L3))



def _pick_chrome(layers: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Return CN chrome dict if the first layer name is CJK · else EN."""
    if layers:
        first = str(layers[0].get("name", ""))
        if _has_cjk(first):
            return _CHROME_CN
    return _CHROME_EN


def build_osi_data(
    layers: Optional[List[Dict[str, Any]]] = None,
    *,
    figure_title: str = "OSI reference model · seven layers of network abstraction",
    figure_subtitle: str = (
        "Physical bits to application intent · each layer wraps the one "
        "below · PDU = protocol data unit · illustrative"
    ),
    figure_tag: str = "FIGURE 04",
    figure_note: str = (
        "OSI stack · layer number · PDU · common protocols · purpose · "
        "TCP/IP mapping on the right"
    ),
    axis_top_label: Optional[str] = None,
    axis_bot_label: Optional[str] = None,
    axis_mid_label: Optional[str] = None,
    tcpip_title: Optional[str] = None,
    tcpip_groups: Optional[List[Dict[str, Any]]] = None,
    encap_enabled: bool = True,
    encap_headline: Optional[str] = None,
    encap_frames: Optional[List[Dict[str, Any]]] = None,
    footer_note: str = "",
    source: str = "",
    kicker: str = "",
    skip_kinds: Optional[List[str]] = None,
    subtract_level: str = "L3",   # Bucket H default · 见 _SUBTRACT_L{1,2,3}
) -> Tree:
    """Build the OSI Tree.

    Parameters
    ----------
    layers
        List of layer dicts (see ``BASELINE_LAYERS`` for shape). Defaults
        to the 7-layer OSI baseline.
    tcpip_groups
        List of TCP/IP mapping panel groups. Pass ``[]`` to hide the panel.
    encap_enabled / encap_frames
        Set ``encap_enabled=False`` (or pass ``encap_frames=[]``) to hide
        the bottom encapsulation strip.
    axis_top_label / axis_bot_label / axis_mid_label / tcpip_title /
    encap_headline
        Chrome text. ``None`` (default) → auto-pick EN or CN variant based
        on whether the first layer name is CJK. Pass a string to override.
    """
    src_layers = layers if layers is not None else BASELINE_LAYERS
    src_tcpip = (
        tcpip_groups if tcpip_groups is not None else BASELINE_TCPIP
    )
    # auto-pick CN encap frames when layer names are CJK (unless caller overrides)
    _default_encap = (
        BASELINE_ENCAP_CN if src_layers and _has_cjk(str(src_layers[0].get("name", "")))
        else BASELINE_ENCAP
    )
    src_encap = (
        encap_frames if encap_frames is not None else _default_encap
    )

    # auto-pick EN vs CN chrome copy · caller wins if they pass a string
    chrome = _pick_chrome(src_layers)
    if axis_top_label is None:
        axis_top_label = chrome["axis_top_label"]
    if axis_bot_label is None:
        axis_bot_label = chrome["axis_bot_label"]
    if axis_mid_label is None:
        axis_mid_label = chrome["axis_mid_label"]
    if tcpip_title is None:
        tcpip_title = chrome["tcpip_title"]
    if encap_headline is None:
        encap_headline = chrome["encap_headline"]

    root = TreeNode(
        id="osi", label="OSI",
        extra={
            "figure_title": figure_title,
            "figure_subtitle": figure_subtitle,
            "figure_tag": figure_tag,
            "figure_note": figure_note,
            "axis_top_label": axis_top_label,
            "axis_bot_label": axis_bot_label,
            "axis_mid_label": axis_mid_label,
            "tcpip_title": tcpip_title,
            "tcpip_groups": list(src_tcpip),
            "encap_enabled": bool(encap_enabled) and bool(src_encap),
            "encap_headline": encap_headline,
            "encap_arrow_send_text": chrome["arrow_send_text"],
            "encap_arrow_recv_text": chrome["arrow_recv_text"],
            "encap_frames": list(src_encap),
            "footer_note": footer_note,
            "skip_kinds": _resolve_skip_kinds(skip_kinds, subtract_level),
        },
    )
    for ly in src_layers:
        root.children.append(TreeNode(
            id=str(ly.get("short", "")),
            label=str(ly.get("name", "")),
            sublabel=str(ly.get("short", "")),
            detail=str(ly.get("purpose", "")),
            group=str(ly.get("hue", "red")),
            extra={
                "layer_no": int(ly.get("no", 0)),
                "pdu": str(ly.get("pdu", "") or ""),
                "protocols": str(ly.get("protocols", "") or ""),
                "note": str(ly.get("note", "") or ""),
                "tcpip_key": str(ly.get("tcpip_key", "") or ""),
            },
        ))

    return Tree(
        root=root,
        figure_title=figure_title,
        figure_caption=figure_subtitle,
        source=source,
        encoding_note=f"{len(src_layers)} layer stack",
        kicker=kicker,
    )


HERO_J1_DATA = build_osi_data()


# Backwards-compat alias · older callers may still import build_osi_tree
build_osi_tree = build_osi_data


# ═════════════════════════════════════════════════════════════════
# Renderer
# ═════════════════════════════════════════════════════════════════
def render_hero_embed_j1_osi_v2(
    data: Tree = HERO_J1_DATA,
    palette: Palette = BONE_RUST,
    params: Optional[OSIStackParams] = None,
) -> str:
    """Render the J1 OSI hero SVG · viewBox 1400×720."""
    # [FONT-PATCH-L1] font pass-through (standalone): ea.FONT_SANS/SERIF 覆写
    _MOD_FONT = globals()
    _ORIG_FONT = {k: _MOD_FONT[k] for k in ('FONT_SANS', 'FONT_SERIF') if k in _MOD_FONT}
    try:
        from ..skins import editorial_atelier as _ea_font
        if 'FONT_SANS' in _MOD_FONT and _ea_font.FONT_SANS != _MOD_FONT['FONT_SANS']:
            _MOD_FONT['FONT_SANS'] = _ea_font.FONT_SANS
        if 'FONT_SERIF' in _MOD_FONT and _ea_font.FONT_SERIF != _MOD_FONT['FONT_SERIF']:
            _MOD_FONT['FONT_SERIF'] = _ea_font.FONT_SERIF
    except Exception:
        pass
    try:
        _ = palette  # OSI uses its own hues · palette kept for signature parity
        positions = osi_stack_v2_layout(data, params=params)

        root_extra = dict(getattr(data.root, "extra", {}) or {})
        title = str(root_extra.get("figure_title", data.figure_title or ""))
        subtitle = str(root_extra.get("figure_subtitle", data.figure_caption or ""))
        figure_tag = str(root_extra.get("figure_tag", "FIGURE 04"))
        figure_note = str(root_extra.get("figure_note", ""))

        # pluck the chrome_viewbox marker (always at head of layout output) ·
        # falls back to full 1400×720 if absent (older callers / defensive).
        view_w = VIEW_W
        view_h = VIEW_H
        if positions and positions[0].get("kind") == "chrome_viewbox":
            vb = positions[0]
            view_w = int(vb.get("w", VIEW_W))
            view_h = int(vb.get("h", VIEW_H))

        # 底色 + 语义色: 如果 active skin 提供 palette 就用 palette 值,
        # 否则用 preset baseline. 让 preset 内 36 处硬编码 _INK/_GRAY/_HAIR 引用
        # 自动跟随 skin 底色明暗. 用 globals() 临时改写模块常量, render 结束前还原.
        # (Python 无法在函数内 shadow 模块常量 · globals() 覆写是最小侵入方案)
        _MOD = globals()
        _orig_colors = {k: _MOD[k] for k in ("_BG", "_INK", "_GRAY", "_HAIR", "_INK_SOFT")}
        _active_skin = _get_active_skin()
        if _active_skin is not None:
            _skin_pal = getattr(_active_skin, "PALETTE", None)
            if _skin_pal is not None:
                if getattr(_skin_pal, "bg", None):
                    _MOD["_BG"] = _skin_pal.bg
                if getattr(_skin_pal, "ink", None):
                    _MOD["_INK"] = _skin_pal.ink
                    _MOD["_INK_SOFT"] = _skin_pal.ink
                if getattr(_skin_pal, "gray", None):
                    _MOD["_GRAY"] = _skin_pal.gray
                if getattr(_skin_pal, "hair", None):
                    _MOD["_HAIR"] = _skin_pal.hair

        try:
            parts: List[str] = [
                f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {view_w} {view_h}">',
                f'<rect width="{view_w}" height="{view_h}" fill="{_BG}"/>',
            ]

            # ─── defs · ink / grey / hue arrow markers used by encap arrows ───
            parts.append(
                '<defs>'
                '<marker id="arr_ink" viewBox="0 0 10 10" refX="9" refY="5" '
                'markerWidth="7" markerHeight="7" orient="auto">'
                '<path d="M 0 0 L 10 5 L 0 10 z" fill="' + _INK_SOFT + '"/>'
                '</marker>'
                '</defs>'
            )

            # ═════════════════════════════════════════════════════════════════
            # Chrome
            # ═════════════════════════════════════════════════════════════════
            if title:
                parts.append(
                    f'<text x="60" y="46" font-family="{FONT_SERIF}" '
                    f'font-size="36" font-weight="600" fill="{_INK}" '
                    f'letter-spacing="0.1">{esc(title)}</text>'
                )
            if subtitle:
                parts.append(
                    f'<text x="60" y="68" font-family="{FONT_SANS}" '
                    f'font-size="17.5" fill="{_INK_SOFT}" '
                    f'letter-spacing="0.2">{esc(subtitle)}</text>'
                )
            parts.append(
                f'<line x1="60" y1="82" x2="1340" y2="82" '
                f'stroke="{_INK}" stroke-width="0.8"/>'
            )
            if figure_tag:
                tag_fs = _fit_svg_font_size(
                    figure_tag,
                    190.0,
                    15.0,
                    min_size=12.0,
                    bold=True,
                    letter_spacing=1.5,
                )
                parts.append(
                    f'<text x="60" y="100" font-family="{FONT_SANS}" '
                    f'font-size="{tag_fs:.1f}" fill="{_INK_SOFT}" font-weight="600" '
                    f'letter-spacing="1.5">{esc(figure_tag)}</text>'
                )
            if figure_note:
                tag_w = (
                    _est_svg_text_w(
                        figure_tag,
                        tag_fs if figure_tag else 15.0,
                        bold=True,
                        letter_spacing=1.5,
                    )
                    if figure_tag else 0.0
                )
                note_x = max(160.0, 60.0 + tag_w + 28.0)
                note_fs = _fit_svg_font_size(
                    figure_note,
                    max(120.0, VIEW_W - note_x - 60.0),
                    15.0,
                    min_size=12.0,
                    letter_spacing=0.4,
                )
                parts.append(
                    f'<text x="{note_x:.1f}" y="100" font-family="{FONT_SANS}" '
                    f'font-size="{note_fs:.1f}" fill="{_GRAY}" letter-spacing="0.4">'
                    f'{esc(figure_note)}</text>'
                )

            # ═════════════════════════════════════════════════════════════════
            # Emit layout positions
            # ═════════════════════════════════════════════════════════════════
            # Bucket H (2026-09-13) · subtraction · caller 可通过 root.extra 传
            # `skip_kinds` = ["layer_note", "layer_purpose", ...] 跳过指定 kind
            # 也可通过 root.extra["extra_legend_lines"] = [...] 追加底部 legend 行
            _skip_kinds = set(str(k) for k in (root_extra.get("skip_kinds") or []))
            for pos in positions:
                if pos.get("kind") in _skip_kinds:
                    continue
                k = pos["kind"]

                # ─── left axis ───
                if k == "chrome_axis_top":
                    parts.append(
                        f'<text x="72" y="{pos["y"]}" font-family="{FONT_SANS}" '
                        f'font-size="15" font-weight="700" fill="{_INK}" '
                        f'letter-spacing="1.5">{esc(pos["text"])}</text>'
                    )
                elif k == "chrome_axis_bot":
                    parts.append(
                        f'<text x="72" y="{pos["y"]}" font-family="{FONT_SANS}" '
                        f'font-size="15" font-weight="700" fill="{_INK}" '
                        f'letter-spacing="1.5">{esc(pos["text"])}</text>'
                    )
                elif k == "chrome_axis_line":
                    parts.append(
                        f'<line x1="{pos["x"]}" y1="{pos["y0"]}" '
                        f'x2="{pos["x"]}" y2="{pos["y1"]}" '
                        f'stroke="rgba(115,120,132,0.55)" stroke-width="0.8"/>'
                    )
                elif k == "chrome_axis_arrow_top":
                    x = pos["x"]
                    y = pos["y"]
                    parts.append(
                        f'<path d="M {x - 4:.1f} {y + 4:.1f} L {x:.1f} '
                        f'{y - 4:.1f} L {x + 4:.1f} {y + 4:.1f} Z" '
                        f'fill="{_GRAY}"/>'
                    )
                elif k == "chrome_axis_arrow_bot":
                    x = pos["x"]
                    y = pos["y"]
                    parts.append(
                        f'<path d="M {x - 4:.1f} {y - 4:.1f} L {x:.1f} '
                        f'{y + 4:.1f} L {x + 4:.1f} {y - 4:.1f} Z" '
                        f'fill="{_GRAY}"/>'
                    )
                elif k == "chrome_axis_mid":
                    parts.append(
                        f'<text x="72" y="{pos["y"]:.1f}" '
                        f'font-family="{FONT_SANS}" font-size="15" '
                        f'fill="{_GRAY}" font-style="italic" '
                        f'transform="rotate(-90 72 {pos["y"]:.1f})" '
                        f'text-anchor="middle">{esc(pos["text"])}</text>'
                    )

                # ─── right TCP/IP header ───
                elif k == "chrome_tcpip_hdr":
                    parts.append(
                        f'<text x="{pos["x"]}" y="{pos["y"]}" '
                        f'font-family="{FONT_SANS}" font-size="15" '
                        f'font-weight="700" fill="{_INK}" letter-spacing="1.5">'
                        f'{esc(pos["text"])}</text>'
                    )
                elif k == "chrome_tcpip_rule":
                    parts.append(
                        f'<line x1="{pos["x0"]}" y1="{pos["y"]}" '
                        f'x2="{pos["x1"]}" y2="{pos["y"]}" '
                        f'stroke="rgba(24,26,34,0.35)" stroke-width="0.6"/>'
                    )

                # ─── layer bar ───
                elif k == "layer_bar":
                    hue = pos["hue"]
                    skin_svg = _try_skin_draw(
                        "osi_layer_bar", pos["x"], pos["y"], pos["w"], pos["h"],
                        "", palette, hue=hue,
                    )
                    if skin_svg is not None:
                        parts.append(skin_svg)
                        continue
                    parts.append(
                        f'<rect x="{pos["x"]}" y="{pos["y"]}" '
                        f'width="{pos["w"]}" height="{pos["h"]}" rx="4" '
                        f'fill="{_hue(hue, 0.06)}" stroke="{_hue(hue, 0.4)}" '
                        f'stroke-width="0.7"/>'
                    )
                elif k == "layer_accent":
                    hue = pos["hue"]
                    parts.append(
                        f'<rect x="{pos["x"]}" y="{pos["y"]}" '
                        f'width="{pos["w"]}" height="{pos["h"]}" rx="1.5" '
                        f'fill="{_hue(hue, 0.9)}"/>'
                    )
                elif k == "layer_num":
                    hue = pos["hue"]
                    skin_svg = _try_skin_draw(
                        "osi_layer_num", pos["x"], pos["y"], 0, 0,
                        str(pos["text"]), palette, hue=hue,
                    )
                    if skin_svg is not None:
                        parts.append(skin_svg)
                        continue
                    parts.append(
                        f'<text x="{pos["x"]}" y="{pos["y"]:.1f}" '
                        f'font-family="{FONT_SERIF}" font-size="18" '
                        f'font-weight="700" fill="{_hue(hue, 1.0)}">'
                        f'{esc(pos["text"])}</text>'
                    )
                elif k == "layer_name":
                    parts.append(
                        f'<text x="{pos["x"]}" y="{pos["y"]:.1f}" '
                        f'font-family="{FONT_SANS}" font-size="18" '
                        f'font-weight="700" fill="{_INK}">'
                        f'{esc(pos["text"])}</text>'
                    )
                elif k == "layer_purpose":
                    parts.append(
                        f'<text x="{pos["x"]}" y="{pos["y"]:.1f}" '
                        f'font-family="{FONT_SANS}" font-size="15" '
                        f'fill="{_GRAY}" font-style="italic">'
                        f'{esc(pos["text"])}</text>'
                    )
                elif k == "layer_pdu_pill":
                    hue = pos["hue"]
                    skin_svg = _try_skin_draw(
                        "osi_pdu_pill", pos["x"], pos["y"], pos["w"], pos["h"],
                        "", palette, hue=hue,
                    )
                    if skin_svg is not None:
                        parts.append(skin_svg)
                        continue
                    parts.append(
                        f'<rect x="{pos["x"]:.1f}" y="{pos["y"]:.1f}" '
                        f'width="{pos["w"]:.1f}" height="{pos["h"]}" rx="10" '
                        f'fill="{_hue(hue, 0.22)}" stroke="{_hue(hue, 0.75)}" '
                        f'stroke-width="1"/>'
                    )
                elif k == "layer_pdu_text":
                    hue = pos["hue"]
                    anchor = str(pos.get("anchor", "middle") or "middle")
                    text_x = float(pos.get("x", pos.get("cx", 0.0)) or 0.0)
                    fs = float(pos.get("font_size", 15.0) or 15.0)
                    parts.append(
                        f'<text x="{text_x:.1f}" y="{pos["cy"]:.1f}" '
                        f'text-anchor="{anchor}" font-family="{FONT_SANS}" '
                        f'font-size="{fs:.1f}" font-weight="700" '
                        f'fill="{_hue(hue, 1.0)}" letter-spacing="0.5">'
                        f'{esc(pos["text"])}</text>'
                    )
                elif k == "layer_protocols":
                    fs = float(pos.get("font_size", 17.0) or 17.0)
                    parts.append(
                        f'<text x="{pos["x"]:.1f}" y="{pos["y"]:.1f}" '
                        f'font-family="{FONT_SANS}" font-size="{fs:.1f}" '
                        f'font-weight="600" fill="{_INK}">'
                        f'{esc(pos["text"])}</text>'
                    )
                elif k == "layer_note":
                    parts.append(
                        f'<text x="{pos["x"]:.1f}" y="{pos["y"]:.1f}" '
                        f'font-family="{FONT_SANS}" font-size="15" '
                        f'fill="{_GRAY}" font-style="italic">'
                        f'{esc(pos["text"])}</text>'
                    )

                # ─── TCP/IP panel ───
                elif k == "tcpip_group":
                    hue = pos["hue"]
                    parts.append(
                        f'<rect x="{pos["x"]}" y="{pos["y"]:.1f}" '
                        f'width="{pos["w"]}" height="{pos["h"]:.1f}" rx="6" '
                        f'fill="{_hue(hue, 0.05)}" stroke="{_hue(hue, 0.5)}" '
                        f'stroke-width="0.9"/>'
                    )
                elif k == "tcpip_group_accent":
                    hue = pos["hue"]
                    parts.append(
                        f'<rect x="{pos["x"]}" y="{pos["y"]:.1f}" '
                        f'width="{pos["w"]}" height="{pos["h"]:.1f}" rx="1.5" '
                        f'fill="{_hue(hue, 0.9)}"/>'
                    )
                elif k == "tcpip_hdr":
                    hue = pos["hue"]
                    parts.append(
                        f'<text x="{pos["x"]}" y="{pos["y"]:.1f}" '
                        f'font-family="{FONT_SANS}" font-size="17" '
                        f'font-weight="700" fill="{_hue(hue, 1.0)}" '
                        f'letter-spacing="1.2">{esc(pos["text"])}</text>'
                    )
                elif k == "tcpip_sub":
                    parts.append(
                        f'<text x="{pos["x"]}" y="{pos["y"]:.1f}" '
                        f'font-family="{FONT_SANS}" font-size="15" '
                        f'fill="{_GRAY}" font-style="italic">'
                        f'{esc(pos["text"])}</text>'
                    )
                elif k == "tcpip_body":
                    is_first = pos["index"] == 0
                    fw = "600" if is_first else "500"
                    fill = _INK if is_first else _INK_SOFT
                    fs = float(pos.get("font_size", 13.0) or 13.0)
                    parts.append(
                        f'<text x="{pos["x"]}" y="{pos["y"]:.1f}" '
                        f'font-family="{FONT_SANS}" font-size="{fs:.1f}" '
                        f'font-weight="{fw}" fill="{fill}">'
                        f'{esc(pos["text"])}</text>'
                    )
                elif k == "tcpip_brace":
                    hue = pos["hue"]
                    xf = pos["x_from"]
                    xt = pos["x_to"]
                    yt = pos["y_top"]
                    yb = pos["y_bot"]
                    mid = xf + (xt - xf) / 2
                    if abs(yt - yb) < 6:
                        # collapse to horizontal tick
                        parts.append(
                            f'<path d="M {xf} {yt:.1f} L {xt} {yt:.1f}" '
                            f'fill="none" stroke="{_hue(hue, 0.55)}" '
                            f'stroke-width="1"/>'
                        )
                    else:
                        parts.append(
                            f'<path d="M {xf} {yt:.1f} L {mid} {yt:.1f} '
                            f'L {mid} {yb:.1f} L {xt} {yb:.1f}" '
                            f'fill="none" stroke="{_hue(hue, 0.55)}" '
                            f'stroke-width="1" stroke-linejoin="round"/>'
                        )

                # ─── encapsulation strip ───
                elif k == "encap_hairline":
                    parts.append(
                        f'<line x1="{pos["x0"]}" y1="{pos["y"]}" '
                        f'x2="{pos["x1"]}" y2="{pos["y"]}" '
                        f'stroke="{_HAIR}" stroke-width="0.4"/>'
                    )
                elif k == "encap_headline":
                    parts.append(
                        f'<text x="{pos["x"]}" y="{pos["y"]}" '
                        f'font-family="{FONT_SANS}" font-size="16" '
                        f'font-weight="700" fill="{_INK}" letter-spacing="1.4">'
                        f'{esc(pos["text"])}</text>'
                    )
                elif k == "encap_outer":
                    hue = pos["hue"]
                    parts.append(
                        f'<rect x="{pos["x"]}" y="{pos["y"]}" '
                        f'width="{pos["w"]:.1f}" height="{pos["h"]}" rx="3" '
                        f'fill="none" stroke="{_hue(hue, 0.9)}" '
                        f'stroke-width="1.2"/>'
                    )
                elif k == "encap_header":
                    hue = pos["hue"]
                    parts.append(
                        f'<rect x="{pos["x"]}" y="{pos["y"]}" '
                        f'width="{pos["w"]}" height="{pos["h"]}" rx="3" '
                        f'fill="{_hue(hue, 0.15)}" stroke="{_hue(hue, 0.9)}" '
                        f'stroke-width="1.2"/>'
                    )
                    cx = pos["x"] + pos["w"] / 2
                    cy = pos["y"] + pos["h"] / 2
                    # 3-line stack · font 15 needs ~17pt vertical rhythm
                    parts.append(
                        f'<text x="{cx:.1f}" y="{cy - 15:.1f}" text-anchor="middle" '
                        f'font-family="{FONT_SANS}" font-size="15" '
                        f'font-weight="700" fill="{_hue(hue, 1.0)}">'
                        f'{esc(pos.get("top", ""))}</text>'
                    )
                    parts.append(
                        f'<text x="{cx:.1f}" y="{cy + 2:.1f}" text-anchor="middle" '
                        f'font-family="{FONT_SANS}" font-size="15" '
                        f'fill="{_hue(hue, 1.0)}">'
                        f'{esc(pos.get("mid", ""))}</text>'
                    )
                    parts.append(
                        f'<text x="{cx:.1f}" y="{cy + 19:.1f}" text-anchor="middle" '
                        f'font-family="{FONT_SANS}" font-size="15" '
                        f'fill="{_hue(hue, 1.0)}">'
                        f'{esc(pos.get("bot", ""))}</text>'
                    )
                elif k == "encap_payload":
                    parts.append(
                        f'<rect x="{pos["x"]}" y="{pos["y"]}" '
                        f'width="{pos["w"]}" height="{pos["h"]}" rx="3" '
                        f'fill="{_BG}" stroke="rgba(115,120,132,0.85)" '
                        f'stroke-width="1"/>'
                    )
                    cx = pos["x"] + pos["w"] / 2
                    cy = pos["y"] + pos["h"] / 2
                    parts.append(
                        f'<text x="{cx:.1f}" y="{cy - 6:.1f}" text-anchor="middle" '
                        f'font-family="{FONT_SANS}" font-size="16" '
                        f'font-weight="700" fill="{_INK}">'
                        f'{esc(pos.get("top", ""))}</text>'
                    )
                    parts.append(
                        f'<text x="{cx:.1f}" y="{cy + 10:.1f}" text-anchor="middle" '
                        f'font-family="{FONT_SANS}" font-size="15" '
                        f'fill="{_GRAY}" font-style="italic">'
                        f'{esc(pos.get("note", ""))}</text>'
                    )
                elif k == "encap_trailer":
                    hue = pos["hue"]
                    parts.append(
                        f'<rect x="{pos["x"]}" y="{pos["y"]}" '
                        f'width="{pos["w"]}" height="{pos["h"]}" rx="3" '
                        f'fill="{_hue(hue, 0.15)}" stroke="{_hue(hue, 0.9)}" '
                        f'stroke-width="1.2"/>'
                    )
                    cx = pos["x"] + pos["w"] / 2
                    cy = pos["y"] + pos["h"] / 2
                    parts.append(
                        f'<text x="{cx:.1f}" y="{cy - 15:.1f}" text-anchor="middle" '
                        f'font-family="{FONT_SANS}" font-size="15" '
                        f'font-weight="700" fill="{_hue(hue, 1.0)}">'
                        f'{esc(pos.get("top", ""))}</text>'
                    )
                    parts.append(
                        f'<text x="{cx:.1f}" y="{cy + 2:.1f}" text-anchor="middle" '
                        f'font-family="{FONT_SANS}" font-size="15" '
                        f'fill="{_hue(hue, 1.0)}">'
                        f'{esc(pos.get("mid", ""))}</text>'
                    )
                    parts.append(
                        f'<text x="{cx:.1f}" y="{cy + 19:.1f}" text-anchor="middle" '
                        f'font-family="{FONT_SANS}" font-size="15" '
                        f'fill="{_hue(hue, 1.0)}">'
                        f'{esc(pos.get("bot", ""))}</text>'
                    )
                elif k == "encap_serialize":
                    parts.append(
                        f'<path d="M {pos["x0"]} {pos["y"]} L {pos["x1"]} '
                        f'{pos["y"]}" stroke="rgba(64,70,82,0.85)" '
                        f'stroke-width="1.4" marker-end="url(#arr_ink)"/>'
                    )
                    cx = (pos["x0"] + pos["x1"]) / 2
                    parts.append(
                        f'<text x="{cx:.1f}" y="{pos["y"] - 12:.1f}" '
                        f'text-anchor="middle" font-family="{FONT_SANS}" '
                        f'font-size="15" font-style="italic" fill="{_GRAY}">'
                        f'serialize</text>'
                    )
                elif k == "encap_wire":
                    hue = pos["hue"]
                    parts.append(
                        f'<rect x="{pos["x"]}" y="{pos["y"]}" '
                        f'width="{pos["w"]}" height="{pos["h"]}" rx="4" '
                        f'fill="{_hue(hue, 0.12)}" stroke="{_hue(hue, 0.9)}" '
                        f'stroke-width="1.2"/>'
                    )
                    cx = pos["x"] + pos["w"] / 2
                    cy = pos["y"] + pos["h"] / 2
                    parts.append(
                        f'<text x="{cx:.1f}" y="{cy + 3:.1f}" text-anchor="middle" '
                        f'font-family="{FONT_SANS}" font-size="15" '
                        f'font-weight="700" fill="{_hue(hue, 1.0)}">'
                        f'{esc(pos.get("text", ""))}</text>'
                    )
                elif k == "encap_wire_tick":
                    hue = pos["hue"]
                    parts.append(
                        f'<line x1="{pos["x"]}" y1="{pos["y0"]}" '
                        f'x2="{pos["x"]}" y2="{pos["y1"]}" '
                        f'stroke="{_hue(hue, 0.6)}" stroke-width="0.9"/>'
                    )
                elif k == "encap_arrow_send":
                    parts.append(
                        f'<path d="M {pos["x0"]} {pos["y"]} L {pos["x1"]} '
                        f'{pos["y"]}" stroke="rgba(64,70,82,0.6)" '
                        f'stroke-width="1" marker-end="url(#arr_ink)"/>'
                    )
                    cx = (pos["x0"] + pos["x1"]) / 2
                    parts.append(
                        f'<text x="{cx:.1f}" y="{pos["y"] - 6:.1f}" '
                        f'text-anchor="middle" font-family="{FONT_SANS}" '
                        f'font-size="15" font-weight="700" fill="{_INK_SOFT}" '
                        f'letter-spacing="0.4">{esc(pos.get("text", ""))}</text>'
                    )
                elif k == "encap_arrow_recv":
                    parts.append(
                        f'<path d="M {pos["x0"]} {pos["y"]} L {pos["x1"]} '
                        f'{pos["y"]}" stroke="rgba(64,70,82,0.6)" '
                        f'stroke-width="1" marker-end="url(#arr_ink)"/>'
                    )
                    cx = (pos["x0"] + pos["x1"]) / 2
                    # text placed above line (like send arrow) so we don't push
                    # SVG y past 640 · keeps atomize slide bottom within canvas.
                    parts.append(
                        f'<text x="{cx:.1f}" y="{pos["y"] - 6:.1f}" '
                        f'text-anchor="middle" font-family="{FONT_SANS}" '
                        f'font-size="15" font-weight="700" fill="{_INK_SOFT}" '
                        f'letter-spacing="0.4">{esc(pos.get("text", ""))}</text>'
                    )
                elif k == "encap_wire_caption":
                    lines = pos.get("lines", []) or []
                    for li, ln in enumerate(lines):
                        fw = "700" if li == 0 else "500"
                        fs = 16 if li == 0 else 15
                        fill = _INK if li == 0 else _GRAY
                        parts.append(
                            f'<text x="{pos["x"]}" y="{pos["y"] + li * 14:.1f}" '
                            f'font-family="{FONT_SANS}" font-size="{fs}" '
                            f'font-weight="{fw}" fill="{fill}">{esc(ln)}</text>'
                        )

                # ─── footer ───
                elif k == "footer_hair":
                    parts.append(
                        f'<line x1="{pos["x0"]}" y1="{pos["y"]}" '
                        f'x2="{pos["x1"]}" y2="{pos["y"]}" '
                        f'stroke="{_HAIR}" stroke-width="0.5"/>'
                    )
                elif k == "footer_note":
                    # split text into a bold "Notes." prefix + rest
                    text = pos["text"]
                    prefix = ""
                    rest = text
                    if text.startswith("Notes."):
                        prefix = "Notes."
                        rest = text[len("Notes."):]
                    parts.append(
                        f'<text x="{pos["x"]}" y="{pos["y"]}" '
                        f'font-family="{FONT_SANS}" font-size="15" '
                        f'fill="{_INK_SOFT}">'
                        + (f'<tspan font-weight="600">{esc(prefix)}</tspan>'
                           if prefix else '')
                        + f'{esc(rest)}</text>'
                    )

            parts.append('</svg>')
            return "".join(parts)

        finally:
            _MOD.update(_orig_colors)
    finally:
        _MOD_FONT.update(_ORIG_FONT)
__all__ = [
    "BASELINE_LAYERS",
    "BASELINE_TCPIP",
    "BASELINE_ENCAP",
    "HERO_J1_DATA",
    "build_osi_data",
    "build_osi_tree",
    "render_hero_embed_j1_osi_v2",
]
