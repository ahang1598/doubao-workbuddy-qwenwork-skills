"""HERO EMBED · 10_CS_c4 V2 · dandelion architecture C4 · container view

彻底重写: 参考 step1 `c4_hero_reference.svg` 的顶级视觉:
    * cream canvas 1400×720
    * 顶部 chrome (kicker rust caps / serif title / sans subtitle / hairline /
      figure line)
    * N 条水平 boundary 色带 (tint bg + 左粗竖 rib + label kicker + 右侧 note)
    * 每 boundary 内 M 个 container 卡片 (top hue bar + 主名 + tech tag + kicker)
    * 双层箭头 · halo 4.4px + 实线 1.5px + hue marker; async 走 dashed grey
    * 底部 hairline + LEGEND (boundary swatches + arrow variants) + footer notes

viewBox 1400×720; make_relation(shrink=True) 自动裁掉多余留白.

数据 schema: Tree
    root: TreeNode
        label = system_name (e.g. "Doubao Infer · container view")
        sublabel = system_subtitle (chrome subtitle)
        detail = figure_note (顶部 figure line 中间小字)
        extra:
            kicker: str
            source: str
            legend_note: str
            notation_note: str (右上小字)
            edges: List[C4Edge dict]
    root.children = boundaries (每 TreeNode)
        label = "EDGE"
        sublabel = 右侧 note italic
        detail = 未使用
        group = hue key
        extra = {index}
        children = containers (每 TreeNode)
            label = "Client SDK"
            sublabel = tech tag (italic 小字)
            detail = kicker caps (bottom small line)
            group = hue key (通常与 boundary 相同)

edges 存在 root.extra["edges"]:
    Each edge dict:
        src: (boundary_idx, container_idx) or "system"
        dst: (boundary_idx, container_idx)
        label: str
        kind: "sync" | "async" | "cross"  (async 走 dashed grey)
        hue: str (可选; 默认继承 dst boundary)
        route: 可选路径提示 ("horizontal" | "vertical" | "up_back")
                — 影响拐点计算
        anchor_src: "right" | "left" | "top" | "bottom" (可选)
        anchor_dst: 同上
"""
from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..schemas import Tree, TreeNode
from ..palettes import Palette
from ..engine import esc
from ..layouts.c4_container_v2 import (
    c4_container_v2_layout, LayoutOverflow, C4ContainerParams,
)
from ..skins.editorial_atelier import (
    BONE_RUST, HUE, FONT_SANS, FONT_SERIF,
)
from ..skins.registry import get_active_skin as _get_active_skin
from ..skins._base import _fit_font_size, _wrap_lines, _luminance, _visual_width


# ═════════════════════════════════════════════════════════════════
# Font size × 1.65 · so slide_w/svg_w (~0.65) × 1.65 ≈ 1.07x  →  ≥10pt in slide
# ═════════════════════════════════════════════════════════════════
_FS_SCALE = 1.65


def _fs(base: float) -> float:
    return base * _FS_SCALE


def _estimate_text_w_svg(text: str, fs: float) -> float:
    """Match atomize's est_w_svg formula so halo bbox actually contains text shape.

    atomize (scripts/atomize_svg_to_slide.py convert_text · _char_width):
      - CJK glyph = fs * 1.0
      - space = fs * 0.35
      - punctuation (· × → ↑ ↓ ← ◆ ◈ §) = fs * 0.7
      - upper case = fs * 0.7
      - digit / lower / other = fs * 0.55
      - final width = sum + fs * 0.5 (pad)
    """
    total = 0.0
    for c in text:
        if ord(c) > 0x2E80:  # CJK
            total += fs * 1.0
        elif c.isspace():
            total += fs * 0.35
        elif c in '·×→↑↓←◆◈§':
            total += fs * 0.7
        elif c.isupper():
            total += fs * 0.7
        elif c.isdigit():
            total += fs * 0.55
        else:
            total += fs * 0.55
    return total + fs * 0.5


def _container_name_text_bbox(
    cp: Dict[str, Any],
) -> Optional[Tuple[float, float, float, float]]:
    """Return the atomize-space bbox of container's NAME text · matching
    _render_container's positioning logic. Used to guarantee edge label halos
    stay disjoint from container names (R3 fix 2026-09-11).

    Returns None if container has no name.
    """
    x, y, w, h = cp["x"], cp["y"], cp["w"], cp["h"]
    name = cp.get("label") or ""
    if not name:
        return None
    has_tech = bool(cp.get("sublabel")) and h >= 60
    has_kicker = bool(cp.get("detail")) and h >= 76
    # Match _render_container fs_base selection.
    if h >= 76:
        name_fs_base = 13.0
    elif h >= 60:
        name_fs_base = 11.0
    else:
        name_fs_base = 10.0
    # Fitted fs (reuse _fit_font_size).
    fs, _txt = _fit_font_size(name, w - 16, _fs(name_fs_base),
                                min_size=_fs(10.0))
    # Match _render_container baseline logic.
    if not has_tech and not has_kicker:
        if fs <= _fs(10.5) + 0.1 and len(name) > 16 and h >= 60:
            lines = _wrap_lines(name, w - 16, char_w=6.6 * _FS_SCALE,
                                max_lines=2)
            if len(lines) > 1:
                line_fs = min(_fs(12.0), _fs(name_fs_base))
                line_h = line_fs * 1.22
                stack_h = (len(lines) - 1) * line_h + 1.6 * line_fs
                hue_bar_h = cp.get("top_hue_bar_h", 4.0)
                top = y + max(hue_bar_h + 4.0, (h - stack_h) / 2)
                bot = top + stack_h
                text_w = max(_estimate_text_w_svg(ln, line_fs)
                             for ln in lines)
                cx = x + w / 2
                return (cx - text_w / 2, top, cx + text_w / 2, bot)
        name_y = y + h / 2 + fs * 0.15
    elif h >= 76:
        name_y = y + 28
    elif h >= 60:
        name_y = y + 26
    else:
        name_y = y + h / 2 + fs * 0.15
    # atomize text shape: top = baseline - 1.15*fs · h = 1.6*fs.
    top = name_y - 1.15 * fs
    bot = top + 1.6 * fs
    # text-anchor="middle" · width = fitted text width.
    text_w = _estimate_text_w_svg(name, fs)
    cx = x + w / 2
    x0 = cx - text_w / 2
    x1 = cx + text_w / 2
    return (x0, top, x1, bot)


# ═════════════════════════════════════════════════════════════════
# baseline data · 对齐 step1 参考 SVG (Doubao Infer · 11 container · 3 boundary)
# ═════════════════════════════════════════════════════════════════

BASELINE_BOUNDARIES: List[Dict[str, Any]] = [
    {
        "label": "EDGE  ·  BOUNDARY 1",
        "note": "TLS termination · authn · rate-limit  ·  reachable from Internet",
        "hue": "purple",
        "containers": [
            {"name": "Client SDK",    "tech": "Python · TypeScript · Go",
             "kicker": "SDK · STREAMING"},
            {"name": "API Gateway",   "tech": "Envoy · gRPC + HTTP/2",
             "kicker": "TLS · RATE-LIMIT · JWT"},
            {"name": "Auth Service",  "tech": "Go · OAuth2 · JWKS",
             "kicker": "TENANT · QUOTA"},
            {"name": "Admin Console", "tech": "React · Next.js · SSR",
             "kicker": "INTERNAL ONLY"},
        ],
    },
    {
        "label": "ORCHESTRATION  ·  BOUNDARY 2",
        "note": ("Request scheduling · batching · KV-cache placement  "
                 "·  cluster-local"),
        "hue": "teal",
        "containers": [
            {"name": "Router",       "tech": "Rust · consistent hash",
             "kicker": "PREFIX-AWARE ROUTING"},
            {"name": "Scheduler",    "tech": "Go · priority queue",
             "kicker": "SLA-AWARE · PREEMPT"},
            {"name": "Batcher",      "tech": "C++ · continuous batching",
             "kicker": "DYNAMIC MERGE"},
            {"name": "KV-Cache Mgr", "tech": "C++ · paged blocks",
             "kicker": "HBM · CPU · REMOTE"},
            {"name": "Prefill Queue", "tech": "shared-memory ring",
             "kicker": "SUB-MS ENQUEUE"},
            {"name": "Telemetry Bus", "tech": "Kafka topics",
             "kicker": "TRACES · BILLING"},
        ],
    },
    {
        "label": "RUNTIME  ·  BOUNDARY 3",
        "note": ("GPU model execution · state store · read-only weight blobs "
                 " ·  data-plane"),
        "hue": "rust",
        "containers": [
            {"name": "GPU Runner",   "tech": "CUDA · FlashAttn-3 · TP=8",
             "kicker": "H100 · PAGED-ATTN · NCCL"},
            {"name": "Weight Store", "tech": "S3 + local NVMe cache",
             "kicker": "SAFETENSORS · SHA256"},
            {"name": "Vector Store", "tech": "Milvus · HNSW · 1536-d",
             "kicker": "RAG · CONTEXT LOOKUP"},
            {"name": "Metrics DB",   "tech": "Prometheus · TSDB · 30d",
             "kicker": "SLO · P99 · GPU UTIL"},
        ],
    },
]


BASELINE_EDGES: List[Dict[str, Any]] = [
    # boundary 1 · horizontal chain
    {"src": (0, 0), "dst": (0, 1), "label": "HTTPS · SSE",  "kind": "sync"},
    {"src": (0, 1), "dst": (0, 2), "label": "verify JWT",   "kind": "sync"},
    # admin console 回环 API Gateway (dashed grey)
    {"src": (0, 3), "dst": (0, 1), "label": "admin API · policy push",
     "kind": "async", "route": "up_back"},
    # cross to orchestration
    {"src": (0, 1), "dst": (1, 0), "label": "gRPC · InferRequest",
     "kind": "cross"},
    {"src": (1, 0), "dst": (1, 1), "label": "hash → shard",
     "kind": "sync"},
    {"src": (1, 1), "dst": (1, 2), "label": "dispatch slot",
     "kind": "sync"},
    {"src": (1, 2), "dst": (1, 3), "label": "alloc blocks",
     "kind": "sync"},
    # scheduler / batcher → queues
    {"src": (1, 1), "dst": (1, 4), "label": "enqueue",
     "kind": "sync"},
    {"src": (1, 3), "dst": (1, 5), "label": "async metrics",
     "kind": "async"},
    # boundary 2 → runtime
    {"src": (1, 4), "dst": (2, 0), "label": "prefill · token[0..n]",
     "kind": "cross"},
    {"src": (1, 5), "dst": (2, 3), "label": "metrics ingest",
     "kind": "cross"},
    # inside runtime
    {"src": (2, 0), "dst": (2, 1), "label": "mmap",     "kind": "sync"},
    {"src": (2, 0), "dst": (2, 2), "label": "RAG · top-k", "kind": "sync"},
    {"src": (2, 0), "dst": (2, 3), "label": "async · P99 latency",
     "kind": "async"},
]


def build_c4_tree(
    system_name: str = "Doubao Infer · container view",
    # NOTE (2026-09-13 · P1 audit): 副标追加"边标签紧靠箭头方向"说明 · 补足读者对
    # "消费/去重"等边标语义定位的解释 (标签写在起点侧 · 方向即箭头方向).
    subtitle: str = ("End-to-end request path across edge, orchestration and "
                     "runtime · every box is a deployable container · "
                     "labelled protocols on edges · 边标签紧邻起点箭头 · 方向由箭头指示"),
    kicker: str = "§ ARCHITECTURE · C4 · CONTAINER DIAGRAM",
    figure_note: str = ("System scope · Doubao Infer · 11 containers grouped "
                        "into 3 trust boundaries · read top-to-bottom for a "
                        "request"),
    notation_note: str = "Notation · C4 model · Simon Brown 2018",
    boundaries: Optional[Sequence[Dict[str, Any]]] = None,
    edges: Optional[Sequence[Dict[str, Any]]] = None,
    source: str = ("A C4 container view: edge shields the perimeter, "
                    "orchestration schedules and batches, runtime executes on "
                    "GPU and persists state. Every box is a deployable unit."),
    source_tail: str = "Source · Platform arch doc · 2026-09 · illustrative",
    legend_note: str = "LEGEND · containers & edges",
    figure_id: str = "FIGURE 10 · C4-L2",
) -> Tree:
    """Build a C4 Tree for c4_container_v2_layout.

    Parameters
    ----------
    boundaries : list of dicts
        每个 dict:
            label:  str · 顶部 kicker (upper 化后显示)
            note:   str · 右侧 italic 小字
            hue:    str · hue key (rust/purple/teal/green/olive/cinnamon...)
            containers: list of dict {name, tech, kicker, hue(可选)}
    edges : list of dicts
        {src: (b_idx, c_idx) | "system", dst: (b_idx, c_idx),
         label: str, kind: "sync"/"async"/"cross",
         hue: optional str, route: optional str,
         anchor_src / anchor_dst: optional str}
    """
    src_boundaries = list(boundaries) if boundaries is not None else BASELINE_BOUNDARIES
    src_edges = list(edges) if edges is not None else BASELINE_EDGES

    root = TreeNode(
        id="system",
        label=system_name,
        sublabel=subtitle,
        detail=figure_note,
        extra={
            "kicker": kicker,
            "source": source,
            "source_tail": source_tail,
            "legend_note": legend_note,
            "notation_note": notation_note,
            "figure_id": figure_id,
            "edges": [dict(e) for e in src_edges],
        },
    )

    for i, b in enumerate(src_boundaries):
        b_node = TreeNode(
            id=f"b{i}",
            label=b.get("label", f"BOUNDARY {i + 1}"),
            sublabel=b.get("note", ""),
            group=b.get("hue", "rust"),
            extra={"index": i},
        )
        for j, c in enumerate(b.get("containers", [])):
            c_node = TreeNode(
                id=f"b{i}_c{j}",
                label=c.get("name", "") or "",
                sublabel=c.get("tech", "") or "",
                detail=c.get("kicker", "") or "",
                group=c.get("hue", "") or b_node.group,
                extra={"boundary_index": i, "index_in_boundary": j},
            )
            b_node.children.append(c_node)
        root.children.append(b_node)

    return Tree(
        root=root, kicker=kicker,
        figure_title=system_name,
        figure_caption=subtitle,
        source=source_tail,
        encoding_note=notation_note,
    )


HERO_CS_C4_V2_DATA = build_c4_tree()

# v1 兼容别名
HERO_CS_V2_DATA = HERO_CS_C4_V2_DATA


# ═════════════════════════════════════════════════════════════════
# ECOM variant · 3 boundary · fan-out from API Gateway → 4 微服务
# ═════════════════════════════════════════════════════════════════

ECOM_BOUNDARIES: List[Dict[str, Any]] = [
    {
        "label": "EDGE  ·  BOUNDARY 1",
        "note": "CDN · WAF · auth  ·  reachable from Internet",
        "hue": "purple",
        "containers": [
            {"name": "Web Storefront", "tech": "Next.js · SSR + ISR",
             "kicker": "STOREFRONT · SPA"},
            {"name": "Mobile App",     "tech": "React Native · gRPC",
             "kicker": "iOS · ANDROID"},
            {"name": "API Gateway",    "tech": "Kong · TLS · JWT",
             "kicker": "RATE-LIMIT · CIRCUIT-BREAK"},
        ],
    },
    {
        "label": "MICROSERVICES  ·  BOUNDARY 2",
        "note": ("Domain services · stateless · horizontally scaled  ·  "
                 "cluster-local"),
        "hue": "teal",
        "containers": [
            {"name": "Catalog Svc",   "tech": "Go · Redis cache",
             "kicker": "PRODUCT · SEARCH"},
            {"name": "Cart Svc",      "tech": "Node.js · Redis",
             "kicker": "SESSION · COUPON"},
            {"name": "Order Svc",     "tech": "Java · Kafka producer",
             "kicker": "STATE MACHINE · SAGA"},
            {"name": "Payment Svc",   "tech": "Go · Stripe SDK",
             "kicker": "PSP · 3DS · WEBHOOK"},
        ],
    },
    {
        "label": "DATA & EVENT  ·  BOUNDARY 3",
        "note": ("Persistent stores · async pipelines · read-only replicas  "
                 " ·  data-plane"),
        "hue": "rust",
        "containers": [
            {"name": "Postgres",     "tech": "PG 16 · logical repl",
             "kicker": "OLTP · WRITE-PRIMARY"},
            {"name": "Elasticsearch", "tech": "ES 8 · ILM policy",
             "kicker": "SEARCH INDEX"},
            {"name": "Kafka",        "tech": "MSK · 3-AZ · exactly-once",
             "kicker": "DOMAIN EVENTS"},
            {"name": "S3 Assets",    "tech": "S3 · CloudFront origin",
             "kicker": "IMAGES · INVOICES"},
        ],
    },
]

ECOM_EDGES: List[Dict[str, Any]] = [
    {"src": (0, 0), "dst": (0, 2), "label": "HTTPS · SSE", "kind": "sync"},
    {"src": (0, 1), "dst": (0, 2), "label": "HTTPS · gRPC", "kind": "sync"},
    # fan-out API Gateway → 4 microservices
    {"src": (0, 2), "dst": (1, 0), "label": "GET /catalog", "kind": "cross"},
    {"src": (0, 2), "dst": (1, 1), "label": "POST /cart", "kind": "cross"},
    {"src": (0, 2), "dst": (1, 2), "label": "POST /order", "kind": "cross"},
    {"src": (0, 2), "dst": (1, 3), "label": "POST /pay", "kind": "cross"},
    # microservices → data stores
    {"src": (1, 0), "dst": (2, 1), "label": "index",  "kind": "cross"},
    {"src": (1, 2), "dst": (2, 0), "label": "SQL",    "kind": "cross"},
    {"src": (1, 2), "dst": (2, 2), "label": "publish", "kind": "cross"},
    {"src": (1, 3), "dst": (2, 2), "label": "publish", "kind": "cross"},
    # async cross-service events
    {"src": (1, 1), "dst": (1, 2), "label": "checkout", "kind": "sync"},
    {"src": (1, 0), "dst": (2, 3), "label": "asset ref",
     "kind": "async"},
]


def build_ecom_data() -> Tree:
    return build_c4_tree(
        system_name="Shop-X · container view",
        subtitle=("End-to-end request path across edge, microservices and "
                   "data stores · every box is a deployable container · "
                   "labelled protocols on edges"),
        kicker="§ ARCHITECTURE · C4 · CONTAINER DIAGRAM",
        figure_note=("System scope · Shop-X e-commerce · 11 containers "
                      "grouped into 3 trust boundaries · read top-to-bottom"),
        notation_note="Notation · C4 model · Simon Brown 2018",
        boundaries=ECOM_BOUNDARIES,
        edges=ECOM_EDGES,
        source=("An e-commerce container view: edge terminates TLS and "
                 "routes to microservices; services own their data stores; "
                 "Kafka carries domain events between contexts."),
        source_tail="Source · Platform arch doc · 2026-09 · illustrative",
        legend_note="LEGEND · containers & edges",
        figure_id="FIGURE 10 · C4-L2",
    )


# ═════════════════════════════════════════════════════════════════
# BANK variant · 3 boundary · fan-in 3 login channels → Auth · fan-in 2 pay → Ledger
# ═════════════════════════════════════════════════════════════════

BANK_BOUNDARIES: List[Dict[str, Any]] = [
    {
        "label": "CHANNEL  ·  BOUNDARY 1",
        "note": ("Client access channels · TLS + MFA + fraud check  ·  "
                 "reachable from Internet"),
        "hue": "purple",
        "containers": [
            {"name": "Mobile Bank",   "tech": "iOS · Android",
             "kicker": "BIOMETRIC · MFA"},
            {"name": "Web Bank",      "tech": "React · WebAuthn",
             "kicker": "OAUTH · PIN"},
            {"name": "Branch POS",    "tech": "Kiosk · smart-card",
             "kicker": "CHIP · PIN · SIGNATURE"},
        ],
    },
    {
        "label": "CORE  ·  BOUNDARY 2",
        "note": ("Business services · account · card · transfer  ·  "
                 "core banking cluster"),
        "hue": "teal",
        "containers": [
            {"name": "Auth Svc",      "tech": "Go · OAuth2 · JWKS",
             "kicker": "SESSION · CONSENT"},
            {"name": "Account Svc",   "tech": "Java · JPA",
             "kicker": "BALANCE · STATEMENT"},
            {"name": "Card Svc",      "tech": "Java · HSM SDK",
             "kicker": "PAN VAULT · TOKENIZE"},
            {"name": "Transfer Svc",  "tech": "Go · SEPA/SWIFT",
             "kicker": "PAY-IN · PAY-OUT"},
        ],
    },
    {
        "label": "LEDGER & AUDIT  ·  BOUNDARY 3",
        "note": ("Immutable ledger · audit trail · reg reports  ·  "
                 "data-plane, append-only"),
        "hue": "rust",
        "containers": [
            {"name": "Ledger DB",     "tech": "Oracle · WORM",
             "kicker": "DOUBLE-ENTRY · APPEND-ONLY"},
            {"name": "Audit Store",   "tech": "S3 Object Lock",
             "kicker": "IMMUTABLE · 7Y RETENTION"},
            {"name": "Reg Reports",   "tech": "Airflow · SFTP",
             "kicker": "MICA · BASEL · AML"},
        ],
    },
]

BANK_EDGES: List[Dict[str, Any]] = [
    # fan-in: 3 channels → Auth
    {"src": (0, 0), "dst": (1, 0), "label": "login", "kind": "cross"},
    {"src": (0, 1), "dst": (1, 0), "label": "login", "kind": "cross"},
    {"src": (0, 2), "dst": (1, 0), "label": "login", "kind": "cross"},
    # inside core
    {"src": (1, 0), "dst": (1, 1), "label": "session", "kind": "sync"},
    {"src": (1, 1), "dst": (1, 2), "label": "card ref", "kind": "sync"},
    {"src": (1, 1), "dst": (1, 3), "label": "debit", "kind": "sync"},
    # fan-in: pay + post entry → Ledger
    {"src": (1, 2), "dst": (2, 0), "label": "pay",         "kind": "cross"},
    {"src": (1, 3), "dst": (2, 0), "label": "post entry", "kind": "cross"},
    # async audit
    {"src": (1, 1), "dst": (2, 1), "label": "audit",         "kind": "async"},
    {"src": (2, 0), "dst": (2, 2), "label": "reg extract", "kind": "async"},
]


def build_bank_data() -> Tree:
    return build_c4_tree(
        system_name="Aurora Bank · container view",
        subtitle=("Retail banking request path across channel, core and "
                   "ledger · every box is a deployable container · "
                   "labelled protocols on edges"),
        kicker="§ ARCHITECTURE · C4 · CONTAINER DIAGRAM",
        figure_note=("System scope · Aurora retail bank · 10 containers "
                      "grouped into 3 trust boundaries · read top-to-bottom"),
        notation_note="Notation · C4 model · Simon Brown 2018",
        boundaries=BANK_BOUNDARIES,
        edges=BANK_EDGES,
        source=("A retail-bank container view: channels shield the "
                 "perimeter, core banking runs stateless services, ledger "
                 "and audit are append-only stores of record."),
        source_tail="Source · Platform arch doc · 2026-09 · illustrative",
        legend_note="LEGEND · containers & edges",
        figure_id="FIGURE 10 · C4-L2",
    )


# ═════════════════════════════════════════════════════════════════
# MINI variant · 2 boundary · sparse data · crossing edges (SQL / session)
# ═════════════════════════════════════════════════════════════════

MINI_BOUNDARIES: List[Dict[str, Any]] = [
    {
        "label": "APP  ·  BOUNDARY 1",
        "note": "Web tier · stateless · behind LB  ·  cluster-local",
        "hue": "purple",
        "containers": [
            {"name": "API Server",   "tech": "Go · net/http",
             "kicker": "REST · JSON"},
            {"name": "Async Worker", "tech": "Python · Celery",
             "kicker": "BACKGROUND JOBS"},
        ],
    },
    {
        "label": "DATA  ·  BOUNDARY 2",
        "note": "Persistent state · single-writer  ·  data-plane",
        "hue": "rust",
        "containers": [
            {"name": "Postgres", "tech": "PG 16 · logical repl",
             "kicker": "OLTP"},
            {"name": "Redis",    "tech": "Redis 7 · AOF",
             "kicker": "CACHE · SESSION"},
        ],
    },
]

MINI_EDGES: List[Dict[str, Any]] = [
    # inside app
    {"src": (0, 0), "dst": (0, 1), "label": "enqueue", "kind": "sync"},
    # cross · crossing lines
    {"src": (0, 0), "dst": (1, 1), "label": "session", "kind": "cross"},
    {"src": (0, 1), "dst": (1, 0), "label": "SQL", "kind": "cross"},
    # async telemetry
    {"src": (0, 1), "dst": (1, 1), "label": "cache set", "kind": "async"},
]


def build_mini_data() -> Tree:
    return build_c4_tree(
        system_name="Micro-Blog · container view",
        subtitle=("Two-tier request path: stateless app + persistent data "
                   "· every box is a deployable container · labelled "
                   "protocols on edges"),
        kicker="§ ARCHITECTURE · C4 · CONTAINER DIAGRAM",
        figure_note=("System scope · Micro-Blog demo · 4 containers grouped "
                      "into 2 trust boundaries · read left-to-right"),
        notation_note="Notation · C4 model · Simon Brown 2018",
        boundaries=MINI_BOUNDARIES,
        edges=MINI_EDGES,
        source=("A minimal two-boundary container view: an API server + "
                 "async worker in the app tier, backed by Postgres and "
                 "Redis in the data tier. Session state lives in Redis."),
        source_tail="Source · Platform arch doc · 2026-09 · illustrative",
        legend_note="LEGEND · containers & edges",
        figure_id="FIGURE 10 · C4-L2",
    )


# ═════════════════════════════════════════════════════════════════


# ═════════════════════════════════════════════════════════════════
# hue fallback · 兼容 step1 中的 purple / teal / rust
# ═════════════════════════════════════════════════════════════════

_DANDELION_HUE: Dict[str, str] = {
    "purple":   "rgba(105,75,130,1)",
    "teal":     "rgba(40,130,160,1)",
    "rust":     "rgba(170,90,70,1)",
    "green":    "rgba(32,138,108,1)",
    "olive":    "rgba(122,106,58,1)",
    "cinnamon": "rgba(139,90,60,1)",
    "orange":   "rgba(200,127,61,1)",
    "magenta":  "rgba(166,60,110,1)",
    "gold_p":   "rgba(217,164,72,1)",
    "blue":     "rgba(63,104,146,1)",
    "ink":      "rgba(64,70,82,1)",
    "grey":     "rgba(115,120,132,1)",
}

# aliases · sync 到 skin HUE (若 skin HUE 没有 · 用 dandelion fallback)
_HUE_ALIASES: Dict[str, str] = {
    "purple": "magenta",   # editorial_atelier magenta 是紫红 · 近似
    "teal":   "blue",      # editorial_atelier blue 是青蓝
}


def _hue_rgba(name: str, alpha: float = 1.0) -> str:
    """将 hue key 解析为 rgba(...) string · alpha 参数可控透明度.

    Priority:
      1. Module-level HUE (= editorial_atelier.HUE, mutated by
         gen_svg_relations' _skin_override context). This lets an explicit
         palette override the active skin's bundled colors.
      2. Active skin's HUE dict for keys the palette does not ship.
      3. Alias map (purple→magenta, teal→blue) then re-try above lookups.
      4. _DANDELION_HUE baseline fallback.
    """
    if not name:
        name = "rust"

    def _resolve_from_dict(d: Optional[Dict[str, str]], key: str) -> Optional[str]:
        if not d:
            return None
        v = d.get(key)
        if not isinstance(v, str):
            return None
        if v.startswith("#"):
            h = v.lstrip("#")
            try:
                r, g, b = int(h[:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            except ValueError:
                return None
            return f"rgba({r},{g},{b},{alpha:.3f})"
        if v.startswith("rgba"):
            m = re.match(r"rgba\((\d+),\s*(\d+),\s*(\d+),\s*[\d.]+\)", v)
            if m:
                return f"rgba({m.group(1)},{m.group(2)},{m.group(3)},{alpha:.3f})"
            return v
        return None

    # 1) module-level HUE (ea.HUE, mutated by palette override)
    resolved = _resolve_from_dict(HUE, name)
    if resolved:
        return resolved

    # 2) active skin HUE fallback
    try:
        skin = _get_active_skin()
        if skin is not None:
            resolved = _resolve_from_dict(getattr(skin, "HUE", None), name)
            if resolved:
                return resolved
    except Exception:
        pass

    # 3) alias map · re-run skin+module lookup with alias
    alias = _HUE_ALIASES.get(name)
    if alias:
        resolved = _resolve_from_dict(HUE, alias)
        if resolved:
            return resolved
        try:
            skin = _get_active_skin()
            if skin is not None:
                resolved = _resolve_from_dict(getattr(skin, "HUE", None), alias)
                if resolved:
                    return resolved
        except Exception:
            pass

    # 4) dandelion baseline
    c = _DANDELION_HUE.get(name) or (_DANDELION_HUE.get(alias) if alias else None)
    if c is None:
        c = _DANDELION_HUE.get("rust", "rgba(170,90,70,1)")
    m = re.match(r"rgba\((\d+),\s*(\d+),\s*(\d+),\s*[\d.]+\)", c)
    if m:
        return f"rgba({m.group(1)},{m.group(2)},{m.group(3)},{alpha:.3f})"
    return c


def _hue_key_for_marker(name: str) -> str:
    """canonicalize hue key so marker id 稳定 (purple/teal/rust/...)."""
    if not name:
        return "rust"
    if name in _DANDELION_HUE:
        return name
    return _HUE_ALIASES.get(name, "rust")


# ═════════════════════════════════════════════════════════════════
# SVG render
# ═════════════════════════════════════════════════════════════════

VIEW_W = 1400
VIEW_H = 720  # tightened · legend/footer default off · content max y ≤ 700

CREAM_BG = "rgba(250,246,235,1)"
CARD_BG = CREAM_BG
EDGE_LABEL_BG = CREAM_BG
C4_EDGE_LABEL_CHIP_BG = "rgba(255,255,255,1)"
INK = "rgba(24,26,34,1)"
INK_MID = "rgba(64,70,82,1)"
GREY = "rgba(115,120,132,1)"

C4_DENSE_EDGE_THRESHOLD = 8
C4_DENSE_OVERVIEW_ALPHA = 0.58
C4_DENSE_OVERVIEW_HALO_ALPHA = 0.07


def _c4_neutral_card_bg(page_bg: str, fallback_bg_alt: Optional[str] = None) -> str:
    """Keep C4 container nodes visually stable across unrelated skins.

    C4 cards should read as neutral architecture nodes; hue is already carried
    by the border/top bar. On light pages, a white paper card avoids large
    palette-colored blocks. On dark pages, preserve the skin's dark panel fill
    so existing light text remains legible.
    """
    try:
        if _luminance(page_bg) < 120:
            return fallback_bg_alt or "rgba(255,255,255,0.10)"
    except Exception:
        pass
    return "rgba(255,255,255,0.96)"


def _arrow_marker_defs(hue_keys: Sequence[str]) -> str:
    """Emit <marker> defs for each hue + ink/grey defaults."""
    seen = set()
    ordered = []
    for h in list(hue_keys) + ["ink", "grey"]:
        key = _hue_key_for_marker(h)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(key)
    parts: List[str] = []
    for key in ordered:
        c = _hue_rgba(key, 1.0)
        parts.append(
            f'<marker id="c4_arr_{key}" viewBox="0 0 10 10" refX="9" refY="5" '
            f'markerWidth="7" markerHeight="7" orient="auto">'
            f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{c}"/></marker>'
        )
    return "".join(parts)


def _render_top_chrome(root: TreeNode, palette: Palette) -> str:
    """Emit top chrome (kicker / title / subtitle / hairline / figure line).

    Font sizes × 1.65 · y-positions adjusted so kicker/title/subtitle/hairline
    stay above layout body_y0 = 148.
    """
    extra = getattr(root, "extra", {}) or {}
    kicker = extra.get("kicker", "") or ""
    subtitle = getattr(root, "sublabel", "") or ""
    figure_note = getattr(root, "detail", "") or ""
    figure_id = extra.get("figure_id", "") or ""
    notation_note = extra.get("notation_note", "") or ""
    title = getattr(root, "label", "") or ""

    parts: List[str] = []
    # kicker (rust caps letter-spacing 2.6) · fs 16.5, baseline y=30
    if kicker:
        parts.append(
            f'<text x="60" y="30" font-family="{FONT_SANS}" '
            f'font-size="{_fs(10):.1f}" '
            f'font-weight="700" fill="{_hue_rgba("rust", 1.0)}" '
            f'letter-spacing="2.6">{esc(kicker)}</text>'
        )
    # title serif · fs 46 (28*1.65), baseline y=76
    if title:
        fs, txt = _fit_font_size(title, VIEW_W - 120, _fs(24.0),
                                   min_size=_fs(18.0))
        parts.append(
            f'<text x="60" y="76" font-family="{FONT_SERIF}" '
            f'font-size="{fs:.1f}" font-weight="600" fill="{INK}" '
            f'letter-spacing="0.1">{esc(txt)}</text>'
        )
    # subtitle · fs 20, baseline y=112 (R2: shift +8 to clear title atomize shape)
    if subtitle:
        fs, txt = _fit_font_size(subtitle, VIEW_W - 120, _fs(12.0),
                                   min_size=_fs(10.0))
        parts.append(
            f'<text x="60" y="112" font-family="{FONT_SANS}" '
            f'font-size="{fs:.1f}" fill="{INK_MID}" letter-spacing="0.2">'
            f'{esc(txt)}</text>'
        )
    # hairline · y=126
    parts.append(
        f'<line x1="60" y1="126" x2="1340" y2="126" stroke="{INK}" '
        f'stroke-width="0.8"/>'
    )
    # figure id + figure note · fs 16.5, baseline y=142 (R2: shift +4 to clear hairline)
    if figure_id:
        parts.append(
            f'<text x="60" y="142" font-family="{FONT_SANS}" '
            f'font-size="{_fs(10):.1f}" '
            f'fill="{INK_MID}" font-weight="700" letter-spacing="1.5">'
            f'{esc(figure_id)}</text>'
        )
        note_x = 235
    else:
        note_x = 60
    if figure_note:
        # R2: shorten avail_w so figure_note x-range doesn't overlap notation_note
        # R3: notation_note moved out of the figure line (to kicker line y=30) ·
        # so figure_note can use full avail_w again.
        fs, txt = _fit_font_size(figure_note, VIEW_W - note_x - 40,
                                   _fs(10.0), min_size=_fs(10.0))
        parts.append(
            f'<text x="{note_x}" y="142" font-family="{FONT_SANS}" '
            f'font-size="{fs:.1f}" fill="{GREY}" letter-spacing="0.4">'
            f'{esc(txt)}</text>'
        )
    if notation_note:
        # R3: move to kicker line (y=30) to avoid figure_note overlap on y=142.
        parts.append(
            f'<text x="1340" y="30" text-anchor="end" '
            f'font-family="{FONT_SANS}" font-size="{_fs(10):.1f}" fill="{GREY}" '
            f'letter-spacing="0.4">{esc(notation_note)}</text>'
        )
    return "".join(parts)


def _render_boundary(bp: Dict[str, Any]) -> str:
    """Emit boundary color band + rib + label + note."""
    x, y, w, h = bp["x"], bp["y"], bp["w"], bp["h"]
    hue = bp["hue"]
    label = bp["label"]
    note = bp["sublabel"]
    hue_full = _hue_rgba(hue, 1.0)
    hue_bg = _hue_rgba(hue, 0.05)
    hue_rib = _hue_rgba(hue, 0.85)
    hue_note = _hue_rgba(hue, 0.9)

    parts: List[str] = []
    # tint bg
    parts.append(
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
        f'fill="{hue_bg}" rx="8"/>'
    )
    # rib · 左粗竖条
    parts.append(
        f'<rect x="{x:.1f}" y="{y:.1f}" width="4" height="{h:.1f}" '
        f'fill="{hue_rib}" rx="2"/>'
    )
    # label · 顶部 kicker caps · fs 17.3 (10.5 × 1.65)
    if label:
        parts.append(
            f'<text x="{x + 16:.1f}" y="{y + 24:.1f}" '
            f'font-family="{FONT_SANS}" font-size="{_fs(10.5):.1f}" '
            f'font-weight="700" '
            f'fill="{hue_full}" letter-spacing="2.4">{esc(label.upper())}</text>'
        )
    # note · 右侧 italic 小字 · fs 16.5 min
    if note:
        # 自适应 · 右到 x+w-8
        avail = w - 280  # 给左侧 label 让位置 (拉大以适配 fs 17.3 caps)
        fs, txt = _fit_font_size(note, avail, _fs(10.0), min_size=_fs(10.0))
        parts.append(
            f'<text x="{x + w - 8:.1f}" y="{y + 24:.1f}" text-anchor="end" '
            f'font-family="{FONT_SANS}" font-size="{fs:.1f}" fill="{hue_note}" '
            f'letter-spacing="0.4" font-style="italic">{esc(txt)}</text>'
        )
    return "".join(parts)


def _render_container(cp: Dict[str, Any]) -> str:
    """Emit container card: cream bg + hue border + top hue bar +
    name / tech / (optional kicker if room).

    R2 fix (2026-09-11):
    - If card_h < 62 (dense 5-6 container-per-row layout) · drop kicker
      to prevent text_overflows_container. Just render name + tech.
    - If card_h < 46 · drop tech too · only name (extreme densities).
    - Scale down font sizes when card is short so all glyphs stay in-box.
    """
    x, y, w, h = cp["x"], cp["y"], cp["w"], cp["h"]
    hue = cp["hue"]
    hue_full = _hue_rgba(hue, 1.0)
    hue_bar_h = cp.get("top_hue_bar_h", 4.0)
    name = cp["label"] or ""
    tech = cp["sublabel"] or ""
    kicker = cp["detail"] or ""

    # R2 · adaptive line budget based on card_h.
    # atomize expands text shape to fs × 1.6 with ~-1.15×fs top offset · so:
    #   name (fs 21.45) shape ≈ 34px tall, top offset ≈ 25 (baseline y+22 → top y-3)
    #   tech (fs 16.5) shape ≈ 26px tall
    #   kicker (fs 16.5) shape ≈ 26px tall
    # 3-line stack (name/tech/kicker) needs card_h ≥ ~78 to avoid text_overflows_container.
    # 2-line (name/tech) with fs 11+9 needs card_h ≥ ~60 (both atomize shapes disjoint).
    # 1-line only for card_h < 60 (5-boundary × 6-container dense layout).
    if h >= 76:
        show_tech = True
        show_kicker = True
        name_fs_base = 13.0
        tech_fs_base = 10.0
        line_gap_a = 11
        line_gap_b = 12
    elif h >= 60:
        show_tech = True
        show_kicker = False
        name_fs_base = 11.0
        tech_fs_base = 9.0
        line_gap_a = 6
        line_gap_b = 0
    else:
        # dense · card_h < 60: only 1 line (name at fs 10) fits at slide ≥ 10pt.
        show_tech = False
        show_kicker = False
        name_fs_base = 10.0
        tech_fs_base = 9.0
        line_gap_a = 0
        line_gap_b = 0
    has_tech = show_tech and bool(tech)
    has_kicker = show_kicker and bool(kicker)
    name_only = not has_tech and not has_kicker

    parts: List[str] = []
    # cream body
    parts.append(
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
        f'rx="6" fill="{CARD_BG}" stroke="{hue_full}" stroke-width="1.6"/>'
    )
    # top hue bar
    parts.append(
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" '
        f'height="{hue_bar_h}" fill="{hue_full}"/>'
    )
    # ── text layout · adaptive 1-3 lines · fonts × 1.65 ──
    cx = x + w / 2

    # name 主标题 (Inter 700 · fs 12-13 × 1.65 · fit 到 min 16.5pt)
    if name:
        name_avail_w = max(28.0, w - 24.0)
        name_min_base = 6.4 if name_only else 10.0
        fs, txt = _fit_font_size(
            name, name_avail_w, _fs(name_fs_base),
            min_size=_fs(name_min_base),
        )
        dense_wrapped = False
        if name_only and len(name) > 8 \
                and _visual_width(name, fs * 0.55) > name_avail_w:
            lines = _wrap_lines(
                name, name_avail_w, char_w=fs * 0.55, max_lines=2,
            )
            if len(lines) > 1:
                line_fs = fs
                line_h = line_fs * 1.08
                block_h = (len(lines) - 1) * line_h
                start_y = y + h / 2 - block_h / 2 + line_fs * 0.15
                start_y = max(start_y, y + hue_bar_h + 2 + line_fs * 0.85)
                last_max = y + h - line_fs * 0.45 - 1
                if start_y + (len(lines) - 1) * line_h <= last_max:
                    for k, ln in enumerate(lines):
                        parts.append(
                            f'<text x="{cx:.1f}" y="{start_y + k * line_h:.1f}" '
                            f'text-anchor="middle" font-family="{FONT_SANS}" '
                            f'font-size="{line_fs:.1f}" font-weight="700" '
                            f'fill="{INK}">{esc(ln)}</text>'
                        )
                    name_bottom = (
                        start_y + (len(lines) - 1) * line_h
                        + line_fs * 0.45
                    )
                    dense_wrapped = True
        # 若 name 仍装不下 · wrap 2 行 (只在实测超长时)
        if dense_wrapped:
            pass
        elif fs <= _fs(10.5) + 0.1 and len(name) > 16 and h >= 60:
            lines = _wrap_lines(
                name, name_avail_w, char_w=6.6 * _FS_SCALE,
                max_lines=2,
            )
            if len(lines) > 1:
                line_fs = min(_fs(12.0), _fs(name_fs_base))
                if name_only:
                    line_h = line_fs * 1.22
                    stack_h = (len(lines) - 1) * line_h + 1.6 * line_fs
                    top_pad = max(hue_bar_h + 4.0, (h - stack_h) / 2)
                    start_y = y + top_pad + line_fs * 1.15
                else:
                    line_h = _fs(13.0)
                    start_y = y + int(_fs(15))
                for k, ln in enumerate(lines):
                    parts.append(
                        f'<text x="{cx:.1f}" y="{start_y + k * line_h:.1f}" '
                        f'text-anchor="middle" font-family="{FONT_SANS}" '
                        f'font-size="{line_fs:.1f}" font-weight="700" fill="{INK}">'
                        f'{esc(ln)}</text>'
                    )
                name_bottom = start_y + (len(lines) - 1) * line_h + line_fs * 0.45
            else:
                if name_only:
                    name_y = y + h / 2 + fs * 0.15
                else:
                    name_y = y + 24
                parts.append(
                    f'<text x="{cx:.1f}" y="{name_y:.1f}" '
                    f'text-anchor="middle" font-family="{FONT_SANS}" '
                    f'font-size="{fs:.1f}" font-weight="700" fill="{INK}">'
                    f'{esc(txt)}</text>'
                )
                name_bottom = name_y + fs * 0.45
        else:
            # single-line name at fixed baseline · offset to keep text shape top
            # inside container. atomize computes: shape_top_svg = y - 1.15*fs.
            # shape_bot = y - 1.15*fs + fs*1.6 = y + 0.45*fs.
            # For fs = _fs(13)=21.45 need y ≥ 25; for _fs(12)=19.8 need y ≥ 23.
            # Add +2px safety pad.
            if name_only:
                # L3 removes tech/kicker; center the remaining name instead of
                # leaving it pinned to the top of an otherwise empty card.
                name_y = y + h / 2 + fs * 0.15
            elif h >= 76:
                name_y = y + 28  # 3-line: give tech + kicker room below
            elif h >= 60:
                name_y = y + 26
            else:
                # 1-line only · vertically center in card.
                # baseline = card_top + h/2 + 0.15*fs (typography visual center)
                name_y = y + h / 2 + fs * 0.15
            parts.append(
                f'<text x="{cx:.1f}" y="{name_y:.1f}" '
                f'text-anchor="middle" font-family="{FONT_SANS}" '
                f'font-size="{fs:.1f}" font-weight="700" fill="{INK}">'
                f'{esc(txt)}</text>'
            )
            # name_bottom = actual atomize shape bottom (y + 0.45*fs)
            name_bottom = name_y + fs * 0.45
    else:
        name_bottom = y + 26

    # tech tag (italic · fs tech_fs_base × 1.65)
    if show_tech and tech:
        # atomize shape top of tech = tech_y - 1.15*tech_fs_svg.
        # Must be ≥ name_bottom (atomize shape bottom of name) · 加 2px gap.
        tech_fs_svg = _fs(tech_fs_base)
        min_tech_y = name_bottom + tech_fs_svg * 1.15 + 1
        tech_y = max(name_bottom + int(_fs(line_gap_a)), min_tech_y)
        # atomize shape bot of tech = tech_y + 0.45*tech_fs_svg. Must ≤ y+h - 1.
        max_tech_y = y + h - tech_fs_svg * 0.45 - 1
        if tech_y <= max_tech_y:
            fs, txt = _fit_font_size(
                tech, w - 12, tech_fs_svg, min_size=_fs(9.0))
            parts.append(
                f'<text x="{cx:.1f}" y="{tech_y:.1f}" text-anchor="middle" '
                f'font-family="{FONT_SANS}" font-size="{fs:.1f}" fill="{GREY}" '
                f'font-style="italic">{esc(txt)}</text>'
            )
            tech_bottom = tech_y + fs * 0.45
        else:
            tech_bottom = name_bottom
    else:
        tech_bottom = name_bottom

    # kicker (caps hue · fs 10 × 1.65 = 16.5pt min) · only when card_h ≥ 76
    if show_kicker and kicker:
        kicker_fs_svg = _fs(10.0)
        min_kicker_y = tech_bottom + kicker_fs_svg * 1.15 + 1
        kicker_y = max(tech_bottom + int(_fs(line_gap_b)), min_kicker_y)
        max_kicker_y = y + h - kicker_fs_svg * 0.45 - 1
        if kicker_y <= max_kicker_y:
            avail = w - 12
            fs, txt = _fit_font_size(kicker.upper(), avail, kicker_fs_svg,
                                       min_size=_fs(10.0))
            parts.append(
                f'<text x="{cx:.1f}" y="{kicker_y:.1f}" text-anchor="middle" '
                f'font-family="{FONT_SANS}" font-size="{fs:.1f}" '
                f'fill="{_hue_rgba(hue, 0.9)}" font-weight="700" '
                f'letter-spacing="0.6">{esc(txt)}</text>'
            )
    return "".join(parts)


def _anchor_point(cp: Dict[str, Any], side: str) -> Tuple[float, float]:
    """获取 container 在指定侧的锚点."""
    x, y, w, h = cp["x"], cp["y"], cp["w"], cp["h"]
    if side == "left":
        return (x, y + h / 2)
    if side == "right":
        return (x + w, y + h / 2)
    if side == "top":
        return (x + w / 2, y)
    if side == "bottom":
        return (x + w / 2, y + h)
    # default: 右侧
    return (x + w, y + h / 2)


def _resolve_edge_endpoints(
    edge: Dict[str, Any],
    containers_by_key: Dict[Tuple[int, int], Dict[str, Any]],
) -> Optional[Tuple[Dict[str, Any], Dict[str, Any]]]:
    """Return (src_container_pos, dst_container_pos) or None."""
    src_key = edge.get("src")
    dst_key = edge.get("dst")
    if not isinstance(src_key, tuple) or not isinstance(dst_key, tuple):
        return None
    if src_key not in containers_by_key or dst_key not in containers_by_key:
        return None
    return containers_by_key[src_key], containers_by_key[dst_key]


def _prepare_edges_for_render(
    edges: Sequence[Dict[str, Any]],
    containers_by_key: Dict[Tuple[int, int], Dict[str, Any]],
    *,
    edge_render_mode: str = "auto",
    edge_label_mode: str = "auto",
) -> List[Dict[str, Any]]:
    """Return all valid C4 edges with density-aware style metadata.

    Dense generated C4 cases often inherit a full demo dependency graph while
    their labels are substituted with arbitrary source terms. The renderer must
    never drop topology edges to make the slide cleaner; in dense auto mode it
    only suppresses labels and marks lines for subdued overview styling.
    Callers can opt back into full label detail with
    ``root.extra['edge_label_mode'] = 'full'``.
    """
    valid: List[Dict[str, Any]] = []
    for edge_idx, edge in enumerate(edges):
        if _resolve_edge_endpoints(edge, containers_by_key) is None:
            continue
        copied = dict(edge)
        copied["_c4_edge_index"] = edge_idx
        copied["_c4_edge_no"] = len(valid) + 1
        valid.append(copied)

    mode = (edge_render_mode or "auto").strip().lower()
    label_mode = (edge_label_mode or "auto").strip().lower()
    dense = mode in {"overview", "compact"} or (
        mode == "auto" and len(valid) > C4_DENSE_EDGE_THRESHOLD
    )
    if mode in {"full", "all"}:
        dense = False

    def _copy_edge(edge: Dict[str, Any]) -> Dict[str, Any]:
        copied = dict(edge)
        if dense:
            copied["_c4_overview"] = True
            if copied.get("kind") != "async":
                copied["hue"] = "ink"
        return copied

    selected = [_copy_edge(edge) for edge in valid]
    if dense:
        row_lane_buckets: Dict[Tuple[int, int, int], List[Dict[str, Any]]] = {}
        same_row_lane_buckets: Dict[Tuple[int, int], List[Dict[str, Any]]] = {}
        for edge in selected:
            src = edge.get("src")
            dst = edge.get("dst")
            if not (isinstance(src, tuple) and isinstance(dst, tuple)):
                continue
            if src not in containers_by_key or dst not in containers_by_key:
                continue
            src_cp = containers_by_key[src]
            dst_cp = containers_by_key[dst]
            if src_cp["boundary_index"] != dst_cp["boundary_index"]:
                continue
            src_row = int(src_cp.get("row", 0))
            dst_row = int(dst_cp.get("row", 0))
            if src_row == dst_row:
                key2 = (src_cp["boundary_index"], src_row)
                same_row_lane_buckets.setdefault(key2, []).append(edge)
                continue
            key = (src_cp["boundary_index"], min(src_row, dst_row), max(src_row, dst_row))
            row_lane_buckets.setdefault(key, []).append(edge)
        for bucket in row_lane_buckets.values():
            bucket.sort(key=lambda e: int(e.get("_c4_edge_index", 0)))
            mid = (len(bucket) - 1) / 2
            for idx, edge in enumerate(bucket):
                edge["_c4_lane_offset"] = idx - mid
        for bucket in same_row_lane_buckets.values():
            def _span_key(edge: Dict[str, Any]) -> Tuple[int, int, int]:
                src = edge.get("src")
                dst = edge.get("dst")
                if not (isinstance(src, tuple) and isinstance(dst, tuple)):
                    return (0, 0, int(edge.get("_c4_edge_index", 0)))
                src_col = int(containers_by_key[src].get("col", src[1]))
                dst_col = int(containers_by_key[dst].get("col", dst[1]))
                span = abs(dst_col - src_col)
                return (-span, min(src_col, dst_col), int(edge.get("_c4_edge_index", 0)))

            bucket.sort(key=_span_key)
            for idx, edge in enumerate(bucket):
                edge["_c4_same_row_lane"] = idx
                edge["_c4_same_row_lane_count"] = len(bucket)
                edge["_c4_force_detour"] = True

    # 曲线模式只通过起终点在节点边上的偏移做分流。这里预先给每个
    # source/destination 端分配槽位，避免多条曲线从同一个精确点出入后
    # 汇聚成一条看不清归属的线。
    for key_name, offset_name, count_name in (
        ("src", "_c4_src_slot_offset", "_c4_src_slot_count"),
        ("dst", "_c4_dst_slot_offset", "_c4_dst_slot_count"),
    ):
        fan_buckets: Dict[Tuple[int, int], List[Dict[str, Any]]] = {}
        for edge in selected:
            key = edge.get(key_name)
            if isinstance(key, tuple) and key in containers_by_key:
                fan_buckets.setdefault(key, []).append(edge)
        for bucket in fan_buckets.values():
            bucket.sort(key=lambda e: int(e.get("_c4_edge_index", 0)))
            mid = (len(bucket) - 1) / 2
            for idx, edge in enumerate(bucket):
                edge[offset_name] = (idx - mid) * 11.0
                edge[count_name] = len(bucket)

    if label_mode in {"off", "none", "false", "0"}:
        show_labels = False
    elif label_mode in {"on", "full", "true", "1"}:
        show_labels = True
    else:
        show_labels = True

    if not show_labels:
        for edge in selected:
            edge["label"] = ""
    return selected


def _pick_anchors(src_cp: Dict[str, Any], dst_cp: Dict[str, Any],
                    edge: Dict[str, Any]) -> Tuple[str, str]:
    """按 boundary/位置关系自动挑锚点."""
    anc_src = edge.get("anchor_src")
    anc_dst = edge.get("anchor_dst")
    if anc_src and anc_dst:
        return anc_src, anc_dst
    same_boundary = (src_cp["boundary_index"] == dst_cp["boundary_index"])
    same_row = (src_cp.get("row", 0) == dst_cp.get("row", 0))
    if same_boundary and same_row:
        # 水平: src.right → dst.left (若 src 在 dst 左) 或 逆
        if src_cp["x"] < dst_cp["x"]:
            return (anc_src or "right", anc_dst or "left")
        return (anc_src or "left", anc_dst or "right")
    if same_boundary and not same_row:
        # 同 boundary 上下行 · 垂直连
        if src_cp["y"] < dst_cp["y"]:
            return (anc_src or "bottom", anc_dst or "top")
        return (anc_src or "top", anc_dst or "bottom")
    # 跨 boundary
    if src_cp["boundary_index"] < dst_cp["boundary_index"]:
        return (anc_src or "bottom", anc_dst or "top")
    return (anc_src or "top", anc_dst or "bottom")


# ─── 避障工具 ────────────────────────────────────────────────
def _point_in_rect_interior(
    px: float, py: float, rect: Dict[str, Any], pad: float = 1.0,
) -> bool:
    """point 是否严格落在 rect 内部 (带 pad 收缩边框)."""
    x, y, w, h = rect["x"], rect["y"], rect["w"], rect["h"]
    return (x + pad < px < x + w - pad) and (y + pad < py < y + h - pad)


def _seg_intersects_rect_interior(
    x1: float, y1: float, x2: float, y2: float,
    rect: Dict[str, Any], pad: float = 1.0,
) -> bool:
    """检查水平或竖直线段是否穿越 rect 内部 (对角/斜线不支持)."""
    rx = rect["x"] + pad
    ry = rect["y"] + pad
    rr = rect["x"] + rect["w"] - pad
    rb = rect["y"] + rect["h"] - pad
    if rx >= rr or ry >= rb:
        return False
    if abs(y1 - y2) < 0.5:
        # 水平线 y=y1 · 检查 y 是否在 rect 内 · 且 x 范围与 rect 有交叠
        if not (ry < y1 < rb):
            return False
        lo, hi = (min(x1, x2), max(x1, x2))
        return not (hi <= rx or lo >= rr)
    if abs(x1 - x2) < 0.5:
        # 竖直线 x=x1
        if not (rx < x1 < rr):
            return False
        lo, hi = (min(y1, y2), max(y1, y2))
        return not (hi <= ry or lo >= rb)
    return False


def _path_hits_containers(
    pts: List[Tuple[float, float]],
    endpoint_ids: set,
    all_cps: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """检查 polyline pts 是否穿越 endpoint 之外的任何 container 内部.

    Returns list of hit rects (可能空)."""
    hits: List[Dict[str, Any]] = []
    for i in range(len(pts) - 1):
        x1, y1 = pts[i]
        x2, y2 = pts[i + 1]
        for cp in all_cps:
            if cp["id"] in endpoint_ids:
                continue
            if _seg_intersects_rect_interior(x1, y1, x2, y2, cp, pad=1.0):
                hits.append(cp)
    return hits


def _find_column_gutter_x(
    src_x: float, dst_x: float, y_range: Tuple[float, float],
    row_cps: List[Dict[str, Any]],
    exclude_ids: set,
) -> Optional[float]:
    """在同一行的卡片列之间找 gap 的中央 x · 用于跨行竖直箭头绕开中间行卡片列.

    row_cps: 中间行的 container list (只需要 x range 检查).
    y_range: 检查区段的 y 上下 (仅用于筛选相关卡片).
    Returns None if no viable gutter.
    """
    # 目标 x 在 src/dst 之间
    lo_x = min(src_x, dst_x)
    hi_x = max(src_x, dst_x)
    # 中间行内 x 与 (lo, hi) 有交叠的卡片
    blockers = []
    for cp in row_cps:
        if cp["id"] in exclude_ids:
            continue
        # 只考虑 y_range 内的
        cy_lo = cp["y"]
        cy_hi = cp["y"] + cp["h"]
        if cy_hi <= y_range[0] or cy_lo >= y_range[1]:
            continue
        blockers.append(cp)
    if not blockers:
        # 直接走 mid
        return (src_x + dst_x) / 2

    # 排序 by x
    blockers.sort(key=lambda cp: cp["x"])
    # 候选 gutter x = 相邻 blocker 之间的中央 · 或最左/最右外侧
    candidates = []
    prev_right = None
    for cp in blockers:
        if prev_right is not None:
            gap_lo = prev_right
            gap_hi = cp["x"]
            if gap_hi - gap_lo > 6:
                candidates.append((gap_lo + gap_hi) / 2)
        prev_right = cp["x"] + cp["w"]
    # 左外
    left_edge = min(cp["x"] for cp in blockers)
    if left_edge > 8:
        candidates.append(left_edge - 8)
    # 右外
    right_edge = max(cp["x"] + cp["w"] for cp in blockers)
    candidates.append(right_edge + 8)

    if not candidates:
        return None
    # 挑最接近目标 (src+dst)/2 的
    target = (src_x + dst_x) / 2
    candidates.sort(key=lambda x: abs(x - target))
    return candidates[0]


def _midway_between_boundaries(
    b0: Dict[str, Any], b1: Dict[str, Any],
) -> float:
    """两个 boundary 之间 gap 中央 y."""
    if b0["y"] < b1["y"]:
        top_b, bot_b = b0, b1
    else:
        top_b, bot_b = b1, b0
    return (top_b["y"] + top_b["h"] + bot_b["y"]) / 2


def _row_of_container(cp: Dict[str, Any]) -> Tuple[int, int]:
    return (cp["boundary_index"], cp.get("row", 0))


def _same_row(cp1: Dict[str, Any], cp2: Dict[str, Any]) -> bool:
    return _row_of_container(cp1) == _row_of_container(cp2)


def _blockers_between(
    src_cp: Dict[str, Any], dst_cp: Dict[str, Any],
    all_cps: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """同行 src → dst 之间 (排他)，x 落在 (src.right, dst.left) 或
    (dst.right, src.left) 之间的其它卡片."""
    lo_x = min(src_cp["x"] + src_cp["w"], dst_cp["x"] + dst_cp["w"])
    hi_x = max(src_cp["x"], dst_cp["x"])
    lo = min(lo_x, hi_x)
    hi = max(lo_x, hi_x)
    row = _row_of_container(src_cp)
    hits = []
    for cp in all_cps:
        if cp["id"] in (src_cp["id"], dst_cp["id"]):
            continue
        if _row_of_container(cp) != row:
            continue
        cx = cp["x"] + cp["w"] / 2
        if lo < cx < hi:
            hits.append(cp)
    return hits


# ─── 路径构建 · 返回 pts list (polyline) ───────────────────────
def _build_polyline(
    src_cp: Dict[str, Any], dst_cp: Dict[str, Any],
    edge: Dict[str, Any],
    all_cps: List[Dict[str, Any]],
    boundary_positions: List[Dict[str, Any]],
    row_cps_by_row: Dict[Tuple[int, int], List[Dict[str, Any]]],
) -> Tuple[List[Tuple[float, float]], str]:
    """构造 polyline pts (list of (x,y)) 与 kind hint.

    kind hint: "horiz_direct" | "horiz_detour" | "vert_direct"
                | "cross_boundary" | "up_back" | "generic"
    """
    route = edge.get("route", "") or ""

    # ─── up_back (admin console → gateway 回环) ─────────────────
    if route == "up_back":
        anc_src, anc_dst = "top", "top"
        x1 = src_cp["x"] + src_cp["w"] / 2
        y1 = src_cp["y"]
        x2 = dst_cp["x"] + dst_cp["w"] / 2
        y2 = dst_cp["y"]
        # 走 src 顶上方 · boundary header 与卡片顶之间的 gap
        b_top = boundary_positions[src_cp["boundary_index"]]["y"]
        # 距离卡片顶 8-10px · 保证在 header (b_top+24) 下方
        mid_y = max(b_top + 26, y1 - 10)
        if mid_y >= y1 - 4:
            mid_y = y1 - 6
        return ([(x1, y1), (x1, mid_y), (x2, mid_y), (x2, y2)], "up_back")

    same_b = (src_cp["boundary_index"] == dst_cp["boundary_index"])
    same_row = _same_row(src_cp, dst_cp)

    # ─── 同 boundary 同行 ────────────────────────────────────
    if same_b and same_row:
        # 判断中间是否有其它卡片阻挡
        blockers = _blockers_between(src_cp, dst_cp, all_cps)
        # 端点 y (卡片竖中线)
        cy = src_cp["y"] + src_cp["h"] / 2
        if src_cp["x"] < dst_cp["x"]:
            x_out = src_cp["x"] + src_cp["w"]
            x_in = dst_cp["x"]
            direction = "L2R"
        else:
            x_out = src_cp["x"]
            x_in = dst_cp["x"] + dst_cp["w"]
            direction = "R2L"
        # R2 fix (2026-09-11): 若相邻卡片 (无 blocker) 但 x-gap < 32px · 也走 detour
        # 让 label 落在 pad_top/pad_bottom gutter 而非撞卡片名字带.
        x_gap = abs(x_in - x_out)
        NARROW_GAP = 32.0  # label chip 常见宽度 · 小于此需走 detour
        force_detour = (
            bool(blockers)
            or (x_gap < NARROW_GAP)
            or bool(edge.get("_c4_force_detour"))
        )
        if not force_detour:
            # 直连 · 卡片间 gap 中央有 label
            return ([(x_out, cy), (x_in, cy)], "horiz_direct")
        # 有中间卡片 · 或 x-gap 太窄 · 走 detour:
        # R1 fix: 减小 gap 阈值 (10→4) · 让即便 boundary 收窄
        # 也能走 detour 而不是直接穿卡片
        b = boundary_positions[src_cp["boundary_index"]]
        top_of_row = min(cp["y"] for cp in row_cps_by_row[_row_of_container(src_cp)])
        bot_of_row = max(cp["y"] + cp["h"]
                            for cp in row_cps_by_row[_row_of_container(src_cp)])
        boundary_top_content = b["y"] + 30  # chip band + safety pad
        top_gap = top_of_row - boundary_top_content
        boundary_bot = b["y"] + b["h"] - 3
        bot_gap = boundary_bot - bot_of_row
        # R2 fix: label halo H≈30 SVG · gutter needs ≥8 to place label cleanly.
        # Otherwise route through inter-boundary gap.
        LABEL_GUTTER_MIN = 8
        lane = int(edge.get("_c4_same_row_lane", 0) or 0)
        top_ok = top_gap >= LABEL_GUTTER_MIN
        bot_ok = bot_gap >= LABEL_GUTTER_MIN
        if top_ok and bot_ok:
            use_top = (lane % 2 == 0)
            lane_level = lane // 2
        elif bot_ok:
            use_top = False
            lane_level = lane
        elif top_ok:
            use_top = True
            lane_level = lane
        else:
            use_top = False
            lane_level = 0
        # Red-line label rule: same-row labels sit at the routed line midpoint,
        # so same-row lanes need enough gutter distance for the full chip height
        # instead of hugging the container edge.
        lane_base = 24.0
        lane_step = 14.0
        if (not use_top) and bot_ok:
            detour_y = bot_of_row + max(
                6.0, min(bot_gap - 2, lane_base + lane_level * lane_step)
            )
            return ([
                (src_cp["x"] + src_cp["w"] / 2, src_cp["y"] + src_cp["h"]),
                (src_cp["x"] + src_cp["w"] / 2, detour_y),
                (dst_cp["x"] + dst_cp["w"] / 2, detour_y),
                (dst_cp["x"] + dst_cp["w"] / 2, dst_cp["y"] + dst_cp["h"]),
            ], "horiz_detour")
        elif top_ok:
            detour_y = top_of_row - max(
                6.0, min(top_gap - 2, lane_base + lane_level * lane_step)
            )
            return ([
                (src_cp["x"] + src_cp["w"] / 2, src_cp["y"]),
                (src_cp["x"] + src_cp["w"] / 2, detour_y),
                (dst_cp["x"] + dst_cp["w"] / 2, detour_y),
                (dst_cp["x"] + dst_cp["w"] / 2, dst_cp["y"]),
            ], "horiz_detour")
        else:
            # R2 fix: 走 boundary 之间 gap (而非 boundary 底 · 后者会撞下方 boundary 名字带)
            # 优先走下 boundary_gap · 用两 boundary 之间的空隙作 midpoint gutter
            src_bidx = src_cp["boundary_index"]
            if src_bidx + 1 < len(boundary_positions):
                next_b = boundary_positions[src_bidx + 1]
                # 两 boundary 之间的 gap 中央
                gap_mid = (b["y"] + b["h"] + next_b["y"]) / 2
                return ([
                    (src_cp["x"] + src_cp["w"] / 2, src_cp["y"] + src_cp["h"]),
                    (src_cp["x"] + src_cp["w"] / 2, gap_mid),
                    (dst_cp["x"] + dst_cp["w"] / 2, gap_mid),
                    (dst_cp["x"] + dst_cp["w"] / 2, dst_cp["y"] + dst_cp["h"]),
                ], "horiz_detour")
            elif src_bidx > 0:
                prev_b = boundary_positions[src_bidx - 1]
                gap_mid = (prev_b["y"] + prev_b["h"] + b["y"]) / 2
                return ([
                    (src_cp["x"] + src_cp["w"] / 2, src_cp["y"]),
                    (src_cp["x"] + src_cp["w"] / 2, gap_mid),
                    (dst_cp["x"] + dst_cp["w"] / 2, gap_mid),
                    (dst_cp["x"] + dst_cp["w"] / 2, dst_cp["y"]),
                ], "horiz_detour")
            else:
                # 无相邻 boundary · 兜底: 贴 boundary 底
                detour_y = boundary_bot + 2
                return ([
                    (src_cp["x"] + src_cp["w"] / 2, src_cp["y"] + src_cp["h"]),
                    (src_cp["x"] + src_cp["w"] / 2, detour_y),
                    (dst_cp["x"] + dst_cp["w"] / 2, detour_y),
                    (dst_cp["x"] + dst_cp["w"] / 2, dst_cp["y"] + dst_cp["h"]),
                ], "horiz_detour")

    # ─── 同 boundary 不同行 ─────────────────────────────────
    if same_b and not same_row:
        # 竖直连 · 走 row 间 gap. Dense overview assigns tiny lane offsets so
        # multiple cross-row edges keep their full topology without stacking on
        # the same centerline.
        x1 = src_cp["x"] + src_cp["w"] / 2
        x2 = dst_cp["x"] + dst_cp["w"] / 2
        if src_cp["y"] < dst_cp["y"]:
            y1 = src_cp["y"] + src_cp["h"]
            y2 = dst_cp["y"]
        else:
            y1 = src_cp["y"]
            y2 = dst_cp["y"] + dst_cp["h"]
        lo_y = min(y1, y2)
        hi_y = max(y1, y2)
        lane_offset = float(edge.get("_c4_lane_offset", 0.0) or 0.0)
        mid_y = (y1 + y2) / 2 + lane_offset * 5.0
        if hi_y - lo_y > 10:
            mid_y = max(lo_y + 4.0, min(hi_y - 4.0, mid_y))
        if abs(x1 - x2) < 6:
            return ([(x1, y1), (x2, y2)], "vert_direct")
        return ([(x1, y1), (x1, mid_y), (x2, mid_y), (x2, y2)],
                 "vert_direct")

    # ─── 跨 boundary ──────────────────────────────────────
    # src.bottom / dst.top (or reversed)
    src_bidx = src_cp["boundary_index"]
    dst_bidx = dst_cp["boundary_index"]
    down_dir = (src_bidx < dst_bidx)
    if down_dir:
        y_start = src_cp["y"] + src_cp["h"]
        y_end = dst_cp["y"]
        anc_src, anc_dst = "bottom", "top"
    else:
        y_start = src_cp["y"]
        y_end = dst_cp["y"] + dst_cp["h"]
        anc_src, anc_dst = "top", "bottom"
    x_start = src_cp["x"] + src_cp["w"] / 2
    x_end = dst_cp["x"] + dst_cp["w"] / 2

    # 中间 boundary index list
    if down_dir:
        mid_bidxs = list(range(src_bidx + 1, dst_bidx))
    else:
        mid_bidxs = list(range(dst_bidx + 1, src_bidx))

    if not mid_bidxs:
        # 相邻 boundary · 走 boundary 之间 gap
        gap_y = _midway_between_boundaries(
            boundary_positions[src_bidx], boundary_positions[dst_bidx])
        if abs(x_start - x_end) < 6:
            return ([(x_start, y_start), (x_end, y_end)], "cross_boundary")
        # 检查水平段是否会穿透 src/dst boundary 的其它卡片
        # src 端行 (row) & dst 端行
        # 由于水平段在 gap 里 · 卡片不在 gap 里 → 安全
        return ([
            (x_start, y_start),
            (x_start, gap_y),
            (x_end, gap_y),
            (x_end, y_end),
        ], "cross_boundary")
    # 跨多个 boundary · 需要绕开中间 boundary 里的卡片列
    # 找中间行中的 gutter x
    # 先假设走 dst_cp 上方进入 · 需要在中间行找一个不穿透卡片的 x 通道
    # 简化: 走 src.bottom → 到 src boundary bottom+3 → 水平到 gutter_x
    #       → gutter_x 竖直穿越中间 boundaries → 到 dst boundary top-3 → 水平到 dst.x_end → 进 dst
    src_bottom_gap_y = boundary_positions[src_bidx]["y"] + \
                        boundary_positions[src_bidx]["h"] + 4 if down_dir else \
                        boundary_positions[src_bidx]["y"] - 4
    dst_top_gap_y = boundary_positions[dst_bidx]["y"] - 4 if down_dir else \
                    boundary_positions[dst_bidx]["y"] + \
                    boundary_positions[dst_bidx]["h"] + 4

    # 收集所有中间 boundary 里的 container
    mid_row_cps = []
    for bi in mid_bidxs:
        for cp in all_cps:
            if cp["boundary_index"] == bi:
                mid_row_cps.append(cp)
    gutter_x = _find_column_gutter_x(
        x_start, x_end,
        (min(src_bottom_gap_y, dst_top_gap_y),
         max(src_bottom_gap_y, dst_top_gap_y)),
        mid_row_cps,
        exclude_ids={src_cp["id"], dst_cp["id"]},
    )
    if gutter_x is None:
        gutter_x = (x_start + x_end) / 2
    return ([
        (x_start, y_start),
        (x_start, src_bottom_gap_y),
        (gutter_x, src_bottom_gap_y),
        (gutter_x, dst_top_gap_y),
        (x_end, dst_top_gap_y),
        (x_end, y_end),
    ], "cross_boundary")


def _pts_to_path_d(pts: List[Tuple[float, float]]) -> str:
    parts = [f"M {pts[0][0]:.1f} {pts[0][1]:.1f}"]
    for x, y in pts[1:]:
        parts.append(f"L {x:.1f} {y:.1f}")
    return " ".join(parts)


def _emit_polyline_stroke(
    parts: List[str],
    pts: List[Tuple[float, float]],
    *,
    stroke: str,
    width: float,
    dashed: bool = False,
) -> None:
    """Emit a C4 edge stroke using primitives that survive slide atomization."""
    if len(pts) < 2:
        return
    if not dashed:
        parts.append(
            f'<path d="{_pts_to_path_d(pts)}" fill="none" stroke="{stroke}" '
            f'stroke-width="{width:.1f}" stroke-linejoin="round" '
            f'stroke-linecap="round"/>'
        )
        return

    dash_len = 8.0
    gap_len = 6.0
    for x1, y1, x2, y2, _orient in _segments_from_pts(pts):
        dx = x2 - x1
        dy = y2 - y1
        length = math.hypot(dx, dy)
        if length < 0.5:
            continue
        ux = dx / length
        uy = dy / length
        pos = 0.0
        while pos < length - 0.5:
            end = min(length, pos + dash_len)
            sx = x1 + ux * pos
            sy = y1 + uy * pos
            ex = x1 + ux * end
            ey = y1 + uy * end
            parts.append(
                f'<line x1="{sx:.1f}" y1="{sy:.1f}" '
                f'x2="{ex:.1f}" y2="{ey:.1f}" stroke="{stroke}" '
                f'stroke-width="{width:.1f}" stroke-linecap="round"/>'
            )
            pos += dash_len + gap_len


def _emit_arrowhead(
    parts: List[str],
    pts: List[Tuple[float, float]],
    *,
    fill: str,
    size: float,
) -> None:
    """Draw an arrowhead as a real polygon; SVG markers are stripped by atomize."""
    if len(pts) < 2:
        return
    tip_x, tip_y = pts[-1]
    base_x = base_y = None
    for prev_x, prev_y in reversed(pts[:-1]):
        dx = tip_x - prev_x
        dy = tip_y - prev_y
        length = math.hypot(dx, dy)
        if length > 0.5:
            ux = dx / length
            uy = dy / length
            nx = -uy
            ny = ux
            base_x = tip_x - ux * size
            base_y = tip_y - uy * size
            half = size * 0.46
            p1 = (tip_x, tip_y)
            p2 = (base_x + nx * half, base_y + ny * half)
            p3 = (base_x - nx * half, base_y - ny * half)
            parts.append(
                f'<polygon points="{p1[0]:.1f},{p1[1]:.1f} '
                f'{p2[0]:.1f},{p2[1]:.1f} {p3[0]:.1f},{p3[1]:.1f}" '
                f'fill="{fill}"/>'
            )
            return
    _ = base_x, base_y


def _side_normal(side: str) -> Tuple[float, float]:
    if side == "top":
        return (0.0, -1.0)
    if side == "bottom":
        return (0.0, 1.0)
    if side == "left":
        return (-1.0, 0.0)
    return (1.0, 0.0)


def _side_tangent(side: str) -> Tuple[float, float]:
    if side in {"top", "bottom"}:
        return (1.0, 0.0)
    return (0.0, 1.0)


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _curve_endpoint(
    cp: Dict[str, Any],
    side: str,
    offset: float,
) -> Tuple[float, float]:
    """按节点边上的偏移取曲线端点；曲率只由这些端点和边法线推导。"""
    margin_x = min(24.0, max(6.0, cp["w"] * 0.18))
    margin_y = min(16.0, max(5.0, cp["h"] * 0.22))
    cx = cp["x"] + cp["w"] / 2
    cy = cp["y"] + cp["h"] / 2
    if side == "top":
        return (_clamp(cx + offset, cp["x"] + margin_x,
                       cp["x"] + cp["w"] - margin_x), cp["y"])
    if side == "bottom":
        return (_clamp(cx + offset, cp["x"] + margin_x,
                       cp["x"] + cp["w"] - margin_x), cp["y"] + cp["h"])
    if side == "left":
        return (cp["x"], _clamp(cy + offset, cp["y"] + margin_y,
                                 cp["y"] + cp["h"] - margin_y))
    return (cp["x"] + cp["w"], _clamp(cy + offset, cp["y"] + margin_y,
                                       cp["y"] + cp["h"] - margin_y))


def _curve_side_options(
    src_cp: Dict[str, Any],
    dst_cp: Dict[str, Any],
    edge: Dict[str, Any],
) -> List[Tuple[str, str]]:
    # 中文注释：每个节点只有两个固定端口：上边中心和下边中心。
    # 这两个点不绑定“入/出”角色；上端口可以出线，下端口也可以入线。
    # 候选优先同侧，避免曲线在节点上下两侧来回绕。
    return [("top", "top"), ("bottom", "bottom"), ("bottom", "top"), ("top", "bottom")]


def _curve_controls(
    start: Tuple[float, float],
    src_side: str,
    end: Tuple[float, float],
    dst_side: str,
) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    """不设置额外路由锚点；控制点完全由端点、端点法线和距离自动推导。"""
    sx, sy = start
    ex, ey = end
    dist = math.hypot(ex - sx, ey - sy)
    strength = _clamp(dist * 0.18, 28.0, 96.0)
    if src_side == dst_side:
        strength = _clamp(dist * 0.14 + 30.0, 36.0, 112.0)
    nsx, nsy = _side_normal(src_side)
    ndx, ndy = _side_normal(dst_side)
    return (
        (sx + nsx * strength, sy + nsy * strength),
        (ex + ndx * strength, ey + ndy * strength),
    )


def _port_facing_penalty(
    cp: Dict[str, Any],
    side: str,
    other_cp: Dict[str, Any],
) -> float:
    """中文注释：端口优先选面向对端的一侧，避免跨过节点去找背面端口。"""
    cy = cp["y"] + cp["h"] / 2
    other_cy = other_cp["y"] + other_cp["h"] / 2
    dy = other_cy - cy
    if abs(dy) <= max(8.0, cp["h"] * 0.25):
        return 0.0
    if dy > 0:
        return 0.0 if side == "bottom" else 1800.0
    return 0.0 if side == "top" else 1800.0


def _sample_cubic_curve(
    p0: Tuple[float, float],
    c1: Tuple[float, float],
    c2: Tuple[float, float],
    p3: Tuple[float, float],
    *,
    steps: int = 24,
) -> List[Tuple[float, float]]:
    pts: List[Tuple[float, float]] = []
    for i in range(steps + 1):
        t = i / steps
        mt = 1 - t
        x = (
            mt ** 3 * p0[0]
            + 3 * mt ** 2 * t * c1[0]
            + 3 * mt * t ** 2 * c2[0]
            + t ** 3 * p3[0]
        )
        y = (
            mt ** 3 * p0[1]
            + 3 * mt ** 2 * t * c1[1]
            + 3 * mt * t ** 2 * c2[1]
            + t ** 3 * p3[1]
        )
        pts.append((x, y))
    return pts


def _curve_path_d(
    p0: Tuple[float, float],
    c1: Tuple[float, float],
    c2: Tuple[float, float],
    p3: Tuple[float, float],
) -> str:
    return (
        f"M {p0[0]:.1f} {p0[1]:.1f} "
        f"C {c1[0]:.1f} {c1[1]:.1f} {c2[0]:.1f} {c2[1]:.1f} "
        f"{p3[0]:.1f} {p3[1]:.1f}"
    )


def _lerp_pt(
    a: Tuple[float, float],
    b: Tuple[float, float],
    t: float,
) -> Tuple[float, float]:
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def _split_cubic_once(
    p0: Tuple[float, float],
    c1: Tuple[float, float],
    c2: Tuple[float, float],
    p3: Tuple[float, float],
    t: float,
) -> Tuple[
    Tuple[Tuple[float, float], Tuple[float, float], Tuple[float, float], Tuple[float, float]],
    Tuple[Tuple[float, float], Tuple[float, float], Tuple[float, float], Tuple[float, float]],
]:
    p01 = _lerp_pt(p0, c1, t)
    p12 = _lerp_pt(c1, c2, t)
    p23 = _lerp_pt(c2, p3, t)
    p012 = _lerp_pt(p01, p12, t)
    p123 = _lerp_pt(p12, p23, t)
    p0123 = _lerp_pt(p012, p123, t)
    return (p0, p01, p012, p0123), (p0123, p123, p23, p3)


def _cubic_segment_between(
    p0: Tuple[float, float],
    c1: Tuple[float, float],
    c2: Tuple[float, float],
    p3: Tuple[float, float],
    t0: float,
    t1: float,
) -> Tuple[Tuple[float, float], Tuple[float, float], Tuple[float, float], Tuple[float, float]]:
    if t0 <= 0 and t1 >= 1:
        return p0, c1, c2, p3
    _left, right = _split_cubic_once(p0, c1, c2, p3, t0)
    local_t = (t1 - t0) / max(0.0001, 1 - t0)
    segment, _rest = _split_cubic_once(*right, local_t)
    return segment


def _emit_curve_stroke(
    parts: List[str],
    curve: Dict[str, Any],
    *,
    stroke: str,
    width: float,
    dashed: bool = False,
) -> None:
    """中文注释：虚线曲线拆成多段短 Bezier，避免上传后 dash 样式丢失。"""
    p0, c1, c2, p3 = curve["start"], curve["c1"], curve["c2"], curve["end"]
    if not dashed:
        d = _curve_path_d(p0, c1, c2, p3)
        parts.append(
            f'<path d="{d}" fill="none" stroke="{stroke}" '
            f'stroke-width="{width:.1f}" stroke-linecap="round"/>'
        )
        return
    t = 0.0
    dash_t = 0.055
    gap_t = 0.040
    while t < 0.999:
        t1 = min(1.0, t + dash_t)
        seg = _cubic_segment_between(p0, c1, c2, p3, t, t1)
        d = _curve_path_d(*seg)
        parts.append(
            f'<path d="{d}" fill="none" stroke="{stroke}" '
            f'stroke-width="{width:.1f}" stroke-linecap="round"/>'
        )
        t = t1 + gap_t


def _curve_samples_hit_nodes(
    samples: List[Tuple[float, float]],
    all_cps: List[Dict[str, Any]],
    src_cp: Dict[str, Any],
    dst_cp: Dict[str, Any],
) -> int:
    hits = 0
    start_pt = samples[0]
    end_pt = samples[-1]
    for seg in _segments_from_pts(samples):
        p1 = (seg[0], seg[1])
        p2 = (seg[2], seg[3])
        for cp in all_cps:
            if _segment_hits_container_more_than_endpoint(
                p1, p2, cp,
                src_cp=src_cp,
                dst_cp=dst_cp,
                start_pt=start_pt,
                end_pt=end_pt,
            ):
                hits += 1
    return hits


def _curve_samples_hit_bboxes(
    samples: List[Tuple[float, float]],
    bboxes: Sequence[Tuple[float, float, float, float]],
) -> int:
    hits = 0
    for seg in _segments_from_pts(samples):
        p1 = (seg[0], seg[1])
        p2 = (seg[2], seg[3])
        for bbox in bboxes:
            if _segment_hits_bbox(p1, p2, bbox):
                hits += 1
    return hits


def _build_curve_geometry(
    edge: Dict[str, Any],
    src_cp: Dict[str, Any],
    dst_cp: Dict[str, Any],
    all_cps: List[Dict[str, Any]],
    avoid_label_bboxes: Optional[List[Tuple[float, float, float, float]]] = None,
) -> Dict[str, Any]:
    """生成单条曲线：端点只能取节点固定端口，只允许调整控制点强度。"""
    # 中文注释：端点只允许取上/下两个固定端口，且入/出角色可互换；
    # 不再通过多个端点槽位分流，防止同一节点边上出现一排细小端点。
    src_slot = 0.0
    dst_slot = 0.0
    lane_bias = 0.0
    offset_pairs = [(src_slot + lane_bias, dst_slot - lane_bias)]
    control_scales = [0.55, 0.72, 0.90, 1.10, 1.35, 1.65, 2.05]
    avoid = avoid_label_bboxes or []
    best: Optional[Dict[str, Any]] = None
    best_score = float("inf")
    for src_side, dst_side in _curve_side_options(src_cp, dst_cp, edge):
        for src_off, dst_off in offset_pairs:
            start = _curve_endpoint(src_cp, src_side, src_off)
            end = _curve_endpoint(dst_cp, dst_side, dst_off)
            base_c1, base_c2 = _curve_controls(start, src_side, end, dst_side)
            for scale in control_scales:
                # 中文注释：避让 tag/节点时只调曲线控制点强度，不移动节点端点。
                c1 = (
                    start[0] + (base_c1[0] - start[0]) * scale,
                    start[1] + (base_c1[1] - start[1]) * scale,
                )
                c2 = (
                    end[0] + (base_c2[0] - end[0]) * scale,
                    end[1] + (base_c2[1] - end[1]) * scale,
                )
                samples = _sample_cubic_curve(start, c1, c2, end)
                node_hits = _curve_samples_hit_nodes(samples, all_cps, src_cp, dst_cp)
                label_hits = _curve_samples_hit_bboxes(samples, avoid)
                length = sum(
                    math.hypot(b[0] - a[0], b[1] - a[1])
                    for a, b in zip(samples, samples[1:])
                )
                # 中文注释：评分先保证不穿节点/tag，再选面向对端的端口；
                # “同侧”只是美观偏好，不能压过就近端口，避免放着上方空闲点位
                # 不用却跨过节点去找下方点位。
                same_side_penalty = 0 if src_side == dst_side else 700
                facing_penalty = _port_facing_penalty(src_cp, src_side, dst_cp) \
                    + _port_facing_penalty(dst_cp, dst_side, src_cp)
                score = node_hits * 10000 + label_hits * 2500 \
                    + facing_penalty + same_side_penalty + length
                candidate = {
                    "start": start,
                    "end": end,
                    "c1": c1,
                    "c2": c2,
                    "samples": samples,
                    "src_side": src_side,
                    "dst_side": dst_side,
                    "node_hits": node_hits,
                    "label_hits": label_hits,
                }
                if score < best_score:
                    best_score = score
                    best = candidate
    assert best is not None
    return best


def _curve_point_at_ratio(
    samples: List[Tuple[float, float]],
    ratio: float,
) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    if len(samples) < 2:
        p = samples[0] if samples else (0.0, 0.0)
        return p, (1.0, 0.0)
    lengths: List[float] = []
    total = 0.0
    for a, b in zip(samples, samples[1:]):
        seg_len = math.hypot(b[0] - a[0], b[1] - a[1])
        lengths.append(seg_len)
        total += seg_len
    target = total * ratio
    walked = 0.0
    for idx, seg_len in enumerate(lengths):
        if walked + seg_len >= target and seg_len > 0:
            a = samples[idx]
            b = samples[idx + 1]
            t = (target - walked) / seg_len
            pt = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
            tangent = ((b[0] - a[0]) / seg_len, (b[1] - a[1]) / seg_len)
            return pt, tangent
        walked += seg_len
    a, b = samples[-2], samples[-1]
    seg_len = max(0.01, math.hypot(b[0] - a[0], b[1] - a[1]))
    return b, ((b[0] - a[0]) / seg_len, (b[1] - a[1]) / seg_len)


def _bbox_intersects_any(
    bbox: Tuple[float, float, float, float],
    blockers: Sequence[Tuple[float, float, float, float]],
) -> bool:
    x0, y0, x1, y1 = bbox
    for bx0, by0, bx1, by1 in blockers:
        if not (x1 <= bx0 or bx1 <= x0 or y1 <= by0 or by1 <= y0):
            return True
    return False


def _curve_label_svg(
    edge: Dict[str, Any],
    samples: List[Tuple[float, float]],
    *,
    hue_key: str,
    hue_full: str,
    kind: str,
    overview: bool,
    blockers: Sequence[Tuple[float, float, float, float]],
    used_labels: Optional[List[Tuple[float, float, float, float]]] = None,
) -> str:
    """在曲线中点附近放 tag；tag 不能遮挡节点、已有 tag 或文本区域。"""
    label = edge.get("label", "") or ""
    if not label:
        return ""
    italic = ' font-style="italic"' if kind == "async" else ""
    base_fs = _fs(7.0 if overview else 9.0)
    ratios = [0.50, 0.46, 0.54, 0.42, 0.58, 0.38, 0.62, 0.32, 0.68, 0.26, 0.74]
    normal_offsets = [
        0.0, -18.0, 18.0, -34.0, 34.0, -52.0, 52.0,
        -74.0, 74.0, -100.0, 100.0, -130.0, 130.0,
    ]
    tangent_offsets = [0.0, -28.0, 28.0, -56.0, 56.0, -86.0, 86.0]
    font_sizes = [
        base_fs,
        max(_fs(6.4), base_fs - 1.5),
        max(_fs(5.8), base_fs - 2.8),
        _fs(5.2),
    ]
    best: Optional[Tuple[float, float, float, Tuple[float, float, float, float]]] = None
    best_penalty: Optional[float] = None
    canvas_box = (36.0, 72.0, VIEW_W - 36.0, VIEW_H - 18.0)

    def _inside_canvas(bbox: Tuple[float, float, float, float]) -> bool:
        x0, y0, x1, y1 = bbox
        return x0 >= canvas_box[0] and y0 >= canvas_box[1] \
            and x1 <= canvas_box[2] and y1 <= canvas_box[3]

    def _overlap_penalty(
        bbox: Tuple[float, float, float, float],
    ) -> float:
        x0, y0, x1, y1 = bbox
        penalty = 0.0
        if x0 < canvas_box[0]:
            penalty += (canvas_box[0] - x0) * 20
        if y0 < canvas_box[1]:
            penalty += (canvas_box[1] - y0) * 20
        if x1 > canvas_box[2]:
            penalty += (x1 - canvas_box[2]) * 20
        if y1 > canvas_box[3]:
            penalty += (y1 - canvas_box[3]) * 20
        for bx0, by0, bx1, by1 in blockers:
            ox = min(x1, bx1) - max(x0, bx0)
            oy = min(y1, by1) - max(y0, by0)
            if ox > 0 and oy > 0:
                penalty += ox * oy
        return penalty

    for fs in font_sizes:
        label_w = max(_estimate_text_w_svg(label, fs) + 18.0, 16 * _FS_SCALE)
        halo_pad_x = 7 if overview else 8
        halo_w = label_w + 2 * halo_pad_x
        halo_h = fs * 1.6 + 4
        for ratio in ratios:
            (mx0, my0), tangent = _curve_point_at_ratio(samples, ratio)
            nx, ny = -tangent[1], tangent[0]
            for offset in normal_offsets:
                for tangent_offset in tangent_offsets:
                    # 中文注释：tag 优先在曲线中点，必要时沿法线或切线小幅滑动；
                    # 这仍然保持在曲线中段附近，但不能压住节点、文本或其他 tag。
                    mx = mx0 + nx * offset + tangent[0] * tangent_offset
                    my = my0 + ny * offset + tangent[1] * tangent_offset
                    bbox = (mx - halo_w / 2, my - halo_h / 2,
                            mx + halo_w / 2, my + halo_h / 2)
                    penalty = _overlap_penalty(bbox)
                    if best_penalty is None or penalty < best_penalty:
                        best_penalty = penalty
                        best = (mx, my, fs, bbox)
                    if penalty <= 0.0 and _inside_canvas(bbox):
                        best = (mx, my, fs, bbox)
                        break
                if best is not None and best_penalty == 0.0 and _inside_canvas(best[3]):
                    break
            if best is not None:
                if best_penalty == 0.0 and _inside_canvas(best[3]):
                    break
        if best is not None and best_penalty == 0.0 and _inside_canvas(best[3]):
            break
    if best is None:
        # 理论兜底：前面的候选循环至少会记录一个 best。
        (mx, my), _tangent = _curve_point_at_ratio(samples, 0.5)
        fs = font_sizes[-1]
        label_w = max(_estimate_text_w_svg(label, fs) + 18.0, 16 * _FS_SCALE)
        halo_pad_x = 7 if overview else 8
        halo_w = label_w + 2 * halo_pad_x
        halo_h = fs * 1.6 + 4
        bbox = (mx - halo_w / 2, my - halo_h / 2,
                mx + halo_w / 2, my + halo_h / 2)
        best = (mx, my, fs, bbox)
    else:
        mx, my, fs, bbox = best
        if best_penalty and best_penalty > 0:
            # 兜底不直接压住 blocker：把 bbox 拉回画布内，实际碰撞由审计兜底。
            x0, y0, x1, y1 = bbox
            dx = 0.0
            dy = 0.0
            if x0 < canvas_box[0]:
                dx = canvas_box[0] - x0
            elif x1 > canvas_box[2]:
                dx = canvas_box[2] - x1
            if y0 < canvas_box[1]:
                dy = canvas_box[1] - y0
            elif y1 > canvas_box[3]:
                dy = canvas_box[3] - y1
            if dx or dy:
                mx += dx
                my += dy
                bbox = (x0 + dx, y0 + dy, x1 + dx, y1 + dy)
                best = (mx, my, fs, bbox)
    mx, my, fs, bbox = best
    halo_x, halo_y, halo_x1, halo_y1 = bbox
    text_y = my + fs * 0.35
    if used_labels is not None:
        used_labels.append(bbox)
    return (
        f'<rect x="{halo_x:.1f}" y="{halo_y:.1f}" '
        f'width="{halo_x1 - halo_x:.1f}" height="{halo_y1 - halo_y:.1f}" '
        f'rx="4" fill="{C4_EDGE_LABEL_CHIP_BG}" '
        f'stroke="{_hue_rgba(hue_key, 0.20 if overview else 0.28)}" '
        f'stroke-width="0.8"/>'
        f'<text x="{mx:.1f}" y="{text_y:.1f}" text-anchor="middle" '
        f'font-family="{FONT_SANS}" font-size="{fs:.1f}" '
        f'fill="{hue_full}" font-weight="700" letter-spacing="0.2"{italic}>'
        f'{esc(label)}</text>'
    )


def _polyline_path_midpoint(
    pts: List[Tuple[float, float]],
) -> Tuple[float, float]:
    """Return the geometric midpoint by path length, not by bbox center."""
    if not pts:
        return (0.0, 0.0)
    if len(pts) == 1:
        return pts[0]
    lengths: List[float] = []
    total = 0.0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        seg_len = math.hypot(x2 - x1, y2 - y1)
        lengths.append(seg_len)
        total += seg_len
    if total <= 0.01:
        return pts[0]
    target = total / 2.0
    walked = 0.0
    for idx, seg_len in enumerate(lengths):
        if walked + seg_len >= target and seg_len > 0:
            x1, y1 = pts[idx]
            x2, y2 = pts[idx + 1]
            ratio = (target - walked) / seg_len
            return (x1 + (x2 - x1) * ratio, y1 + (y2 - y1) * ratio)
        walked += seg_len
    return pts[-1]


def _render_midpoint_edge_label(
    edge: Dict[str, Any],
    pts: List[Tuple[float, float]],
    *,
    hue_key: str,
    hue_full: str,
    kind: str,
    overview: bool,
    used_labels: Optional[List[Tuple[float, float, float, float]]] = None,
) -> str:
    """Render a C4 edge label centered on its own routed polyline.

    Red-line rule:
      * label chip center == corresponding polyline path-length midpoint;
      * label chip is emitted immediately after its own stroke, so it is above
        that corresponding line;
      * later edges must route around committed label bboxes before drawing.
    """
    label = edge.get("label", "") or ""
    if not label:
        return ""
    italic = ' font-style="italic"' if kind == "async" else ""
    fs = _fs(8.0 if overview else 10.0)
    label_w = max(_estimate_text_w_svg(label, fs) + 18.0, 16 * _FS_SCALE)
    halo_pad_x = 7 if overview else 8
    halo_w = label_w + 2 * halo_pad_x
    halo_h = fs * 1.6 + 4
    mx, my = _polyline_path_midpoint(pts)
    halo_x = mx - halo_w / 2
    halo_y = my - halo_h / 2
    text_y = my + fs * 0.35
    out = (
        f'<rect x="{halo_x:.1f}" y="{halo_y:.1f}" '
        f'width="{halo_w:.1f}" height="{halo_h:.1f}" '
        f'rx="4" fill="{C4_EDGE_LABEL_CHIP_BG}" '
        f'stroke="{_hue_rgba(hue_key, 0.20 if overview else 0.28)}" '
        f'stroke-width="0.8"/>'
        f'<text x="{mx:.1f}" y="{text_y:.1f}" text-anchor="middle" '
        f'font-family="{FONT_SANS}" font-size="{fs:.1f}" '
        f'fill="{hue_full}" font-weight="700" letter-spacing="0.3"{italic}>'
        f'{esc(label)}</text>'
    )
    if used_labels is not None:
        used_labels.append((halo_x, halo_y, halo_x + halo_w, halo_y + halo_h))
    return out


def _midpoint_label_bbox_for_edge(
    edge: Dict[str, Any],
    pts: List[Tuple[float, float]],
) -> Optional[Tuple[float, float, float, float]]:
    label = edge.get("label", "") or ""
    if not label:
        return None
    overview = bool(edge.get("_c4_overview"))
    fs = _fs(8.0 if overview else 10.0)
    label_w = max(_estimate_text_w_svg(label, fs) + 18.0, 16 * _FS_SCALE)
    halo_pad_x = 7 if overview else 8
    halo_w = label_w + 2 * halo_pad_x
    halo_h = fs * 1.6 + 4
    mx, my = _polyline_path_midpoint(pts)
    return (mx - halo_w / 2, my - halo_h / 2,
            mx + halo_w / 2, my + halo_h / 2)


def _bbox_with_pad(
    bbox: Tuple[float, float, float, float],
    pad: float,
) -> Tuple[float, float, float, float]:
    x0, y0, x1, y1 = bbox
    return (x0 - pad, y0 - pad, x1 + pad, y1 + pad)


def _segment_hits_bbox(
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    bbox: Tuple[float, float, float, float],
) -> bool:
    x1, y1 = p1
    x2, y2 = p2
    bx0, by0, bx1, by1 = bbox
    if abs(y1 - y2) < 0.5:
        lo, hi = sorted([x1, x2])
        return by0 <= y1 <= by1 and hi >= bx0 and lo <= bx1
    if abs(x1 - x2) < 0.5:
        lo, hi = sorted([y1, y2])
        return bx0 <= x1 <= bx1 and hi >= by0 and lo <= by1
    return False


def _route_around_committed_label_bboxes(
    pts: List[Tuple[float, float]],
    label_bboxes: List[Tuple[float, float, float, float]],
    *,
    pad: float = 7.0,
) -> List[Tuple[float, float]]:
    """Detour a new edge around previously painted labels.

    Red-line rule: rendering is sequential (edge A + label A, then edge B +
    label B). Before drawing edge B, this function ensures B's stroke does not
    pass through committed label chips from earlier edges. Labels therefore
    visually intersect only their own corresponding line.
    """
    if len(pts) < 2 or not label_bboxes:
        return pts
    padded = [_bbox_with_pad(b, pad) for b in label_bboxes]
    routed = list(pts)
    for _ in range(2):
        changed = False
        out: List[Tuple[float, float]] = [routed[0]]
        for idx, target in enumerate(routed[1:], start=1):
            start = out[-1]
            detour_done = False
            for bbox in padded:
                if not _segment_hits_bbox(start, target, bbox):
                    continue
                x1, y1 = start
                x2, y2 = target
                bx0, by0, bx1, by1 = bbox
                if abs(y1 - y2) < 0.5:
                    detour_y = (by0 - 2.0) if y1 <= (by0 + by1) / 2 else (by1 + 2.0)
                    out.extend([(x1, detour_y), (x2, detour_y)])
                    if idx == len(routed) - 1:
                        out.append(target)
                elif abs(x1 - x2) < 0.5:
                    detour_x = (bx0 - 2.0) if x1 <= (bx0 + bx1) / 2 else (bx1 + 2.0)
                    out.extend([(detour_x, y1), (detour_x, y2)])
                    if idx == len(routed) - 1:
                        out.append(target)
                else:
                    out.append(target)
                changed = True
                detour_done = True
                break
            if not detour_done:
                out.append(target)
        # Remove duplicate zero-length points introduced by local detours.
        compact: List[Tuple[float, float]] = []
        for pt in out:
            if not compact or math.hypot(pt[0] - compact[-1][0], pt[1] - compact[-1][1]) > 0.2:
                compact.append(pt)
        routed = compact
        if not changed:
            break
    return routed


def _line_body_overlaps_committed(
    seg: Tuple[float, float, float, float, str],
    committed: Tuple[float, float, float, float, str],
    *,
    endpoint_trim: float = 10.0,
    tol: float = 1.8,
) -> bool:
    """Check line-body overlap while allowing shared endpoints.

    Red-line rule: edge endpoints may coincide, but after trimming the first
    and last few pixels from each segment, the remaining body must not lie on
    top of a previously committed edge body.
    """
    x1, y1, x2, y2, orient = seg
    cx1, cy1, cx2, cy2, corient = committed
    if orient != corient or orient not in {"h", "v"}:
        return False
    if orient == "h":
        if abs(y1 - cy1) > tol:
            return False
        a0, a1 = sorted([x1, x2])
        b0, b1 = sorted([cx1, cx2])
    else:
        if abs(x1 - cx1) > tol:
            return False
        a0, a1 = sorted([y1, y2])
        b0, b1 = sorted([cy1, cy2])
    a0 += endpoint_trim
    a1 -= endpoint_trim
    b0 += endpoint_trim
    b1 -= endpoint_trim
    if a1 <= a0 or b1 <= b0:
        return False
    return min(a1, b1) - max(a0, b0) > tol


def _route_around_committed_line_bodies(
    pts: List[Tuple[float, float]],
    committed_segments: List[Tuple[float, float, float, float, str]],
    *,
    offset: float = 11.0,
) -> List[Tuple[float, float]]:
    """Detour current edge when its body would overlap an earlier edge body."""
    if len(pts) < 2 or not committed_segments:
        return pts
    routed = list(pts)
    for _ in range(2):
        changed = False
        out: List[Tuple[float, float]] = [routed[0]]
        for idx, target in enumerate(routed[1:], start=1):
            start = out[-1]
            segs = _segments_from_pts([start, target])
            if not segs:
                out.append(target)
                continue
            cur_seg = segs[0]
            detour_done = False
            for prior in committed_segments:
                if not _line_body_overlaps_committed(cur_seg, prior):
                    continue
                x1, y1 = start
                x2, y2 = target
                orient = cur_seg[4]
                if orient == "h":
                    py = prior[1]
                    detour_y = y1 + (-offset if y1 < py else offset)
                    out.extend([(x1, detour_y), (x2, detour_y)])
                    if idx == len(routed) - 1:
                        out.append(target)
                elif orient == "v":
                    px = prior[0]
                    detour_x = x1 + (-offset if x1 < px else offset)
                    out.extend([(detour_x, y1), (detour_x, y2)])
                    if idx == len(routed) - 1:
                        out.append(target)
                else:
                    out.append(target)
                changed = True
                detour_done = True
                break
            if not detour_done:
                out.append(target)
        compact: List[Tuple[float, float]] = []
        for pt in out:
            if not compact or math.hypot(pt[0] - compact[-1][0], pt[1] - compact[-1][1]) > 0.2:
                compact.append(pt)
        routed = compact
        if not changed:
            break
    return routed


def _label_bbox_hits_line_bodies(
    edge: Dict[str, Any],
    pts: List[Tuple[float, float]],
    committed_segments: List[Tuple[float, float, float, float, str]],
) -> bool:
    bbox = _midpoint_label_bbox_for_edge(edge, pts)
    if bbox is None:
        return False
    for x1, y1, x2, y2, _orient in committed_segments:
        if _segment_hits_bbox((x1, y1), (x2, y2), bbox):
            return True
    return False


def _route_midpoint_label_away_from_line_bodies(
    edge: Dict[str, Any],
    pts: List[Tuple[float, float]],
    committed_segments: List[Tuple[float, float, float, float, str]],
) -> List[Tuple[float, float]]:
    """Move only internal lane points until the midpoint label clears old lines.

    Red-line rule: the label remains at the corresponding line midpoint.  If
    that midpoint chip would cover an earlier line body, we reshape the current
    edge's lane while preserving both endpoints.
    """
    if len(pts) < 3 or not committed_segments:
        return pts
    if not _label_bbox_hits_line_bodies(edge, pts, committed_segments):
        return pts

    first = pts[0]
    second = pts[1]
    if abs(second[1] - first[1]) >= abs(second[0] - first[0]):
        shift_axis = "y"
        sign = 1.0 if second[1] >= first[1] else -1.0
    else:
        shift_axis = "x"
        sign = 1.0 if second[0] >= first[0] else -1.0

    for distance in (22.0, 40.0, 58.0):
        shifted = [pts[0]]
        for x, y in pts[1:-1]:
            if shift_axis == "y":
                shifted.append((x, y + sign * distance))
            else:
                shifted.append((x + sign * distance, y))
        shifted.append(pts[-1])
        if not _label_bbox_hits_line_bodies(edge, shifted, committed_segments):
            return shifted
    return pts


def _point_close(
    a: Tuple[float, float],
    b: Tuple[float, float],
    *,
    tol: float = 1.2,
) -> bool:
    return abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol


def _container_side_for_point(
    cp: Dict[str, Any],
    pt: Tuple[float, float],
) -> str:
    x, y = pt
    distances = [
        ("left", abs(x - cp["x"])),
        ("right", abs(x - (cp["x"] + cp["w"]))),
        ("top", abs(y - cp["y"])),
        ("bottom", abs(y - (cp["y"] + cp["h"]))),
    ]
    distances.sort(key=lambda item: item[1])
    return distances[0][0]


def _endpoint_stub(
    cp: Dict[str, Any],
    pt: Tuple[float, float],
    *,
    clearance: float = 14.0,
) -> Tuple[float, float]:
    side = _container_side_for_point(cp, pt)
    x, y = pt
    if side == "top":
        return (x, cp["y"] - clearance)
    if side == "bottom":
        return (x, cp["y"] + cp["h"] + clearance)
    if side == "left":
        return (cp["x"] - clearance, y)
    return (cp["x"] + cp["w"] + clearance, y)


def _endpoint_segment_ok(
    cp: Dict[str, Any],
    endpoint: Tuple[float, float],
    neighbor: Tuple[float, float],
) -> bool:
    side = _container_side_for_point(cp, endpoint)
    ex, ey = endpoint
    nx, ny = neighbor
    if side == "top":
        return abs(nx - ex) <= 0.8 and ny <= ey
    if side == "bottom":
        return abs(nx - ex) <= 0.8 and ny >= ey
    if side == "left":
        return abs(ny - ey) <= 0.8 and nx <= ex
    return abs(ny - ey) <= 0.8 and nx >= ex


def _axis_dogleg(
    a: Tuple[float, float],
    b: Tuple[float, float],
    *,
    prefer_horizontal_first: bool,
) -> List[Tuple[float, float]]:
    if abs(a[0] - b[0]) <= 0.8 or abs(a[1] - b[1]) <= 0.8:
        return [b]
    if prefer_horizontal_first:
        return [(b[0], a[1]), b]
    return [(a[0], b[1]), b]


def _enforce_endpoint_normal_departure(
    pts: List[Tuple[float, float]],
    src_cp: Dict[str, Any],
    dst_cp: Dict[str, Any],
) -> List[Tuple[float, float]]:
    """硬规则：端点只能沿节点边的法线方向出入。

    上/下边的入段或出段必须先竖直离开/进入节点；左/右边必须先水平
    离开/进入节点。这样端点可以重合，但不会出现沿节点边贴着画的线段。
    """
    if len(pts) < 2:
        return pts

    out = list(pts)
    start = out[0]
    if not _endpoint_segment_ok(src_cp, start, out[1]):
        stub = _endpoint_stub(src_cp, start)
        side = _container_side_for_point(src_cp, start)
        dogleg = _axis_dogleg(
            stub, out[1],
            prefer_horizontal_first=side in {"top", "bottom"},
        )
        out = [start, stub] + dogleg + out[2:]

    end = out[-1]
    if not _endpoint_segment_ok(dst_cp, end, out[-2]):
        stub = _endpoint_stub(dst_cp, end)
        side = _container_side_for_point(dst_cp, end)
        dogleg = _axis_dogleg(
            out[-2], stub,
            prefer_horizontal_first=side in {"top", "bottom"},
        )
        out = out[:-1] + dogleg + [end]

    compact: List[Tuple[float, float]] = []
    for pt in out:
        if not compact or math.hypot(pt[0] - compact[-1][0], pt[1] - compact[-1][1]) > 0.2:
            compact.append(pt)
    return compact


def _segment_hits_container_more_than_endpoint(
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    cp: Dict[str, Any],
    *,
    src_cp: Dict[str, Any],
    dst_cp: Dict[str, Any],
    start_pt: Tuple[float, float],
    end_pt: Tuple[float, float],
    tol: float = 0.8,
) -> bool:
    """硬规则：线段只能在本边的起点/终点与节点相交。"""
    x1, y1 = p1
    x2, y2 = p2
    cx0, cy0 = cp["x"], cp["y"]
    cx1, cy1 = cx0 + cp["w"], cy0 + cp["h"]

    if abs(y1 - y2) <= tol:
        y = (y1 + y2) / 2
        if y < cy0 - tol or y > cy1 + tol:
            return False
        lo, hi = sorted([x1, x2])
        ov0 = max(lo, cx0)
        ov1 = min(hi, cx1)
        if ov1 < ov0 - tol:
            return False
        if ov1 - ov0 <= tol:
            hit = ((ov0 + ov1) / 2, y)
            return not (
                (cp["id"] == src_cp["id"] and _point_close(hit, start_pt))
                or (cp["id"] == dst_cp["id"] and _point_close(hit, end_pt))
            )
        return True

    if abs(x1 - x2) <= tol:
        x = (x1 + x2) / 2
        if x < cx0 - tol or x > cx1 + tol:
            return False
        lo, hi = sorted([y1, y2])
        ov0 = max(lo, cy0)
        ov1 = min(hi, cy1)
        if ov1 < ov0 - tol:
            return False
        if ov1 - ov0 <= tol:
            hit = (x, (ov0 + ov1) / 2)
            return not (
                (cp["id"] == src_cp["id"] and _point_close(hit, start_pt))
                or (cp["id"] == dst_cp["id"] and _point_close(hit, end_pt))
            )
        return True

    return False


def _route_around_container_nodes(
    pts: List[Tuple[float, float]],
    all_cps: List[Dict[str, Any]],
    src_cp: Dict[str, Any],
    dst_cp: Dict[str, Any],
    *,
    avoid_label_bboxes: Optional[List[Tuple[float, float, float, float]]] = None,
    pad: float = 10.0,
) -> List[Tuple[float, float]]:
    """硬规则：除本边起点/终点外，线段不能穿过或贴住任何节点。"""
    if len(pts) < 2:
        return pts
    label_bboxes = avoid_label_bboxes or []

    def _candidate_hits_labels(candidate_pts: List[Tuple[float, float]]) -> bool:
        if not label_bboxes:
            return False
        for a, b in zip(candidate_pts, candidate_pts[1:]):
            for bbox in label_bboxes:
                if _segment_hits_bbox(a, b, bbox):
                    return True
        return False

    routed = list(pts)
    for _ in range(3):
        changed = False
        start_pt = routed[0]
        end_pt = routed[-1]
        out: List[Tuple[float, float]] = [routed[0]]
        for idx, target in enumerate(routed[1:], start=1):
            start = out[-1]
            detour_done = False
            for cp in all_cps:
                if not _segment_hits_container_more_than_endpoint(
                    start, target, cp,
                    src_cp=src_cp,
                    dst_cp=dst_cp,
                    start_pt=start_pt,
                    end_pt=end_pt,
                ):
                    continue
                x1, y1 = start
                x2, y2 = target
                cx0, cy0 = cp["x"], cp["y"]
                cx1, cy1 = cx0 + cp["w"], cy0 + cp["h"]
                if abs(y1 - y2) <= 0.8:
                    candidates = [
                        cy0 - pad,
                        cy1 + pad,
                    ]
                    if y1 > (cy0 + cy1) / 2:
                        candidates.reverse()
                    detour_y = candidates[0]
                    for cand_y in candidates:
                        candidate = [start, (x1, cand_y), (x2, cand_y)]
                        if idx == len(routed) - 1:
                            candidate.append(target)
                        if not _candidate_hits_labels(candidate):
                            detour_y = cand_y
                            break
                    out.extend([(x1, detour_y), (x2, detour_y)])
                    if idx == len(routed) - 1:
                        out.append(target)
                elif abs(x1 - x2) <= 0.8:
                    candidates = [
                        cx0 - pad,
                        cx1 + pad,
                    ]
                    if x1 > (cx0 + cx1) / 2:
                        candidates.reverse()
                    detour_x = candidates[0]
                    for cand_x in candidates:
                        candidate = [start, (cand_x, y1), (cand_x, y2)]
                        if idx == len(routed) - 1:
                            candidate.append(target)
                        if not _candidate_hits_labels(candidate):
                            detour_x = cand_x
                            break
                    out.extend([(detour_x, y1), (detour_x, y2)])
                    if idx == len(routed) - 1:
                        out.append(target)
                else:
                    out.append(target)
                changed = True
                detour_done = True
                break
            if not detour_done:
                out.append(target)

        compact: List[Tuple[float, float]] = []
        for pt in out:
            if not compact or math.hypot(pt[0] - compact[-1][0], pt[1] - compact[-1][1]) > 0.2:
                compact.append(pt)
        routed = compact
        if not changed:
            break
    return routed


def _finalize_node_intersection_rules(
    pts: List[Tuple[float, float]],
    src_cp: Dict[str, Any],
    dst_cp: Dict[str, Any],
    all_cps: List[Dict[str, Any]],
    *,
    avoid_label_bboxes: Optional[List[Tuple[float, float, float, float]]] = None,
) -> List[Tuple[float, float]]:
    """最终规整：先绕开节点，再强制端点法线出入。

    这里同时落实两条新增硬规则：端点不贴边、线与节点只允许在起点/终点
    两个点相交。重复一次是为了避免绕节点动作破坏端点法线方向。
    """
    routed = _route_around_container_nodes(
        pts, all_cps, src_cp, dst_cp,
        avoid_label_bboxes=avoid_label_bboxes,
    )
    routed = _enforce_endpoint_normal_departure(routed, src_cp, dst_cp)
    routed = _route_around_container_nodes(
        routed, all_cps, src_cp, dst_cp,
        avoid_label_bboxes=avoid_label_bboxes,
    )
    routed = _enforce_endpoint_normal_departure(routed, src_cp, dst_cp)
    return routed


def _segments_from_pts(
    pts: List[Tuple[float, float]],
) -> List[Tuple[float, float, float, float, str]]:
    """Return list of (x1,y1,x2,y2, orient) segments; orient in {'h','v','d'}."""
    segs = []
    for i in range(len(pts) - 1):
        x1, y1 = pts[i]
        x2, y2 = pts[i + 1]
        if abs(y1 - y2) < 0.5:
            segs.append((x1, y1, x2, y2, "h"))
        elif abs(x1 - x2) < 0.5:
            segs.append((x1, y1, x2, y2, "v"))
        else:
            segs.append((x1, y1, x2, y2, "d"))
    return segs


def _pick_label_position(
    pts: List[Tuple[float, float]],
    endpoint_ids: set,
    all_cps: List[Dict[str, Any]],
    label_w: float,
    kind_hint: str,
    used_labels: Optional[List[Tuple[float, float, float, float]]] = None,
) -> Tuple[float, float, str, bool]:
    """在 polyline 上挑一个 label 位置 · 保证 label bbox 不压任何 container.

    R2 fix (2026-09-11):
    - Endpoint container 也纳入 bbox 碰撞检测 (只在 label bbox 明显落在 endpoint
      container 卡片正上/正下 gap 内时才 waive).
    - Label bbox = chip background rect (含 opaque halo padding) · 用 halo full extent.
    - Fall back 候选: 卡片正上 gutter (boundary_pad_top zone) / 正下 gutter
      (boundary_pad_bottom zone) / boundary 之间 gap · 而不是压 container 顶部.

    R3 fix (2026-09-11):
    - used_labels 现在还预填 container name text bbox · 保证 label halo 不压名字.
    - 返回值加 ok bool: Pass 1-4 全部失败落到 fallback 时 ok=False · 调用方可选
      不绘制 label halo + text · 只保留 edge line (避免字压字).

    used_labels: 已放置的 label bbox 列表 [(x0,y0,x1,y1),...] · 用于避让 label 重叠
    以及 container name text bbox.

    Returns (mx, my, text_anchor, ok).
    text_anchor: 'middle' (水平段) 或 'start' (垂直段).
    ok: True iff a truly clean position (no container / no used overlap) was found.
    """
    used_labels = used_labels or []
    FS = _fs(10.0)  # ≈ 16.5
    CONTAINER_PAD = 2.0  # tighter · endpoint 卡片允许贴 2px
    HALO_TOP = FS * 1.15
    HALO_H = FS * 1.6 + 4
    HALO_PAD_X = 8

    def _bbox_of_label(cx: float, cy: float, w: float, anchor: str
                        ) -> Tuple[float, float, float, float]:
        # match halo rect emitted by _render_edge / _emit_bundle_label:
        # halo_x = cx - w/2 - HALO_PAD_X (middle) · w + 2*HALO_PAD_X wide ·
        # y = cy - HALO_TOP · h = HALO_H
        if anchor == "middle":
            x0 = cx - w / 2 - HALO_PAD_X
        elif anchor == "end":
            x0 = cx - w - HALO_PAD_X
        else:
            x0 = cx - HALO_PAD_X
        x1 = x0 + w + 2 * HALO_PAD_X
        y0 = cy - HALO_TOP
        y1 = y0 + HALO_H
        return x0, y0, x1, y1

    def _bbox_hits_used(cx: float, cy: float, w: float, anchor: str) -> bool:
        x0, y0, x1, y1 = _bbox_of_label(cx, cy, w, anchor)
        for ux0, uy0, ux1, uy1 in used_labels:
            if not (x1 < ux0 or ux1 < x0 or y1 < uy0 or uy1 < y0):
                return True
        return False

    def _bbox_hits_container(
        cx: float, cy: float, w: float, anchor: str,
        include_endpoints: bool = True,
    ) -> bool:
        """Container collision.

        R3 fix (2026-09-11): endpoint check applies to FULL card body (label
        can't sit on top of endpoint at all) · but non-endpoint check applies
        only to the NAME BAND (top ~34px of card) so labels can slide over
        tech/kicker rows without hitting names.  The name-text bbox is also
        in used_labels so hits there are caught by _bbox_hits_used.
        """
        x0, y0, x1, y1 = _bbox_of_label(cx, cy, w, anchor)
        for cp in all_cps:
            is_endpoint = cp["id"] in endpoint_ids
            if (not include_endpoints) and is_endpoint:
                continue
            # inflate container by CONTAINER_PAD
            rx0 = cp["x"] - CONTAINER_PAD
            ry0 = cp["y"] - CONTAINER_PAD
            rx1 = cp["x"] + cp["w"] + CONTAINER_PAD
            ry1 = cp["y"] + cp["h"] + CONTAINER_PAD
            if is_endpoint:
                # Endpoint: guard entire card body.
                if not (x1 < rx0 or rx1 < x0 or y1 < ry0 or ry1 < y0):
                    return True
            else:
                # Non-endpoint: only guard name-band (top ~34 SVG px covers
                # atomize name text shape for all card_h regimes).
                ry_name_bot = cp["y"] + 34
                if not (x1 < rx0 or rx1 < x0 or y1 < ry0 or ry_name_bot < y0):
                    return True
        return False

    segs = _segments_from_pts(pts)
    seg_lengths = []
    for i, (x1, y1, x2, y2, o) in enumerate(segs):
        length = abs(x2 - x1) if o == "h" else abs(y2 - y1) if o == "v" else 0
        seg_lengths.append((length, i))
    seg_lengths.sort(reverse=True)

    # Pass 1: 严格模式 · label bbox 不碰任何 container (含 endpoint) + 不碰 used
    for _, idx in seg_lengths:
        x1, y1, x2, y2, o = segs[idx]
        if o == "h":
            candidates = [(x1 + x2) / 2]
            step = 14
            for k in range(1, 14):
                candidates.append((x1 + x2) / 2 + k * step)
                candidates.append((x1 + x2) / 2 - k * step)
            # 试 above · label baseline 8px above segment
            for cx in candidates:
                lo, hi = sorted([x1, x2])
                if not (lo + label_w / 2 - 0.1 <= cx <= hi - label_w / 2 + 0.1):
                    continue
                my = y1 - 8
                if not _bbox_hits_container(cx, my, label_w, "middle",
                                              include_endpoints=True) \
                        and not _bbox_hits_used(cx, my, label_w, "middle"):
                    return (cx, my, "middle", True)
            # 试 below · label baseline 15px below segment
            for cx in candidates:
                lo, hi = sorted([x1, x2])
                if not (lo + label_w / 2 - 0.1 <= cx <= hi - label_w / 2 + 0.1):
                    continue
                my = y1 + 15
                if not _bbox_hits_container(cx, my, label_w, "middle",
                                              include_endpoints=True) \
                        and not _bbox_hits_used(cx, my, label_w, "middle"):
                    return (cx, my, "middle", True)
        elif o == "v":
            seg_lo, seg_hi = sorted([y1, y2])
            mid = (y1 + y2) / 2
            span = seg_hi - seg_lo
            step_v = max(10, span * 0.18)
            candidates = [mid]
            for k in range(1, 12):
                candidates.append(mid + k * step_v)
                candidates.append(mid - k * step_v)
            for cy in candidates:
                if not (seg_lo - 6 <= cy <= seg_hi + 6):
                    continue
                mx = x1 + 8
                if not _bbox_hits_container(mx + label_w / 2, cy, label_w, "start",
                                              include_endpoints=True) \
                        and not _bbox_hits_used(mx, cy, label_w, "start"):
                    return (mx, cy, "start", True)
                mx2 = x1 - 8
                if not _bbox_hits_container(mx2 - label_w / 2, cy, label_w, "end",
                                              include_endpoints=True) \
                        and not _bbox_hits_used(mx2, cy, label_w, "end"):
                    return (mx2, cy, "end", True)

    # Pass 2: seg-based · non-endpoint container 检查 (endpoint 可覆盖 · 因短 seg 无 choice)
    for _, idx in seg_lengths:
        x1, y1, x2, y2, o = segs[idx]
        if o == "h":
            candidates = [(x1 + x2) / 2]
            step = 8
            for k in range(1, 20):
                candidates.append((x1 + x2) / 2 + k * step)
                candidates.append((x1 + x2) / 2 - k * step)
            for cx in candidates:
                lo, hi = sorted([x1, x2])
                if not (lo + label_w / 2 - 0.1 <= cx <= hi - label_w / 2 + 0.1):
                    continue
                for my in (y1 - 8, y1 + 15, y1 - 22, y1 + 28):
                    if not _bbox_hits_container(cx, my, label_w, "middle",
                                                  include_endpoints=False) \
                            and not _bbox_hits_used(cx, my, label_w, "middle"):
                        return (cx, my, "middle", True)

    # Pass 3: 允许 label bbox 落在 endpoint 容器上方 gutter (中间 / 顶部 pad zone)
    # 前提是 x 范围与该 endpoint 卡片重叠时 · label y 落在卡片正上 15-20px gap 里
    # 这里我们直接找 endpoint cp 的 top gutter 或 bot gutter 内合适 y ·
    # 且仍要避开 pre-populated 的 chip 带 (used_labels 包含所有 chip bbox).
    endpoint_cps = [cp for cp in all_cps if cp["id"] in endpoint_ids]
    if endpoint_cps and seg_lengths:
        _, idx = seg_lengths[0]
        x1, y1, x2, y2, o = segs[idx]
        if o == "h":
            mid_x = (x1 + x2) / 2
            ecp = endpoint_cps[0]
            # 尝试多个 y 偏移 · 先上后下 · 全部检查 used_labels + non-endpoint container
            for offset in (-12, -8, 15, 20, 26, -18, 33, -24):
                cand_y = (ecp["y"] - offset) if offset < 0 else (ecp["y"] + ecp["h"] + offset - 15)
                # offset<0 → 卡片上方 |offset|px; offset≥15 → 卡片下方 (offset-15)px
                if offset < 0:
                    cand_y = ecp["y"] + offset  # ecp.y - |offset|
                else:
                    cand_y = ecp["y"] + ecp["h"] + offset
                if not _bbox_hits_container(mid_x, cand_y, label_w, "middle",
                                              include_endpoints=False) \
                        and not _bbox_hits_used(mid_x, cand_y, label_w, "middle"):
                    return (mid_x, cand_y, "middle", True)

    # Pass 4: last-resort · 全 segment 采样 · 只检查 used_labels 与 non-endpoint container
    # Wide search: try y offsets ±60 from segment y for both x and y flexibility.
    for _, idx in seg_lengths:
        x1, y1, x2, y2, o = segs[idx]
        if o == "h":
            candidates = [(x1 + x2) / 2]
            step = 8
            for k in range(1, 40):
                candidates.append((x1 + x2) / 2 + k * step)
                candidates.append((x1 + x2) / 2 - k * step)
            my_offsets = list(range(-60, 61, 6))
            for cx in candidates:
                lo, hi = sorted([x1, x2])
                if not (lo - 60 <= cx <= hi + 60):
                    continue
                for dmy in my_offsets:
                    my = y1 + dmy
                    if not _bbox_hits_container(cx, my, label_w, "middle",
                                                  include_endpoints=False) \
                            and not _bbox_hits_used(cx, my, label_w, "middle"):
                        return (cx, my, "middle", True)

    # Fallback: 最长段中点上方 · 忽略碰撞 (报告会捕获). ok=False → 调用方可选跳过.
    if seg_lengths:
        _, idx = seg_lengths[0]
        x1, y1, x2, y2, o = segs[idx]
        if o == "h":
            return ((x1 + x2) / 2, y1 - 8, "middle", False)
        return (x1 + 8, (y1 + y2) / 2, "start", False)
    return (pts[0][0], pts[0][1] - 8, "middle", False)


def _any_container_contains(
    px: float, py: float, endpoint_ids: set,
    all_cps: List[Dict[str, Any]],
    pad: float = 1.0,
) -> bool:
    for cp in all_cps:
        if cp["id"] in endpoint_ids:
            continue
        if _point_in_rect_interior(px, py, cp, pad=pad):
            return True
    return False


def _group_edges_for_bundling(
    edges: List[Dict[str, Any]],
    containers_by_key: Dict[Tuple[int, int], Dict[str, Any]],
) -> Tuple[Dict[int, Dict[str, Any]], Dict[int, int]]:
    """Detect fan-in / fan-out edge groups so we can render shared trunks.

    Rules:
      - fan-in: 2+ edges share the same dst · same kind (sync/cross OR async/grey) ·
        crossing boundaries same direction → share trunk into dst.
      - fan-out: 2+ edges share the same src · same kind → share trunk out of src.
      - We prefer fan-in over fan-out when an edge qualifies for both (rare).
      - Edges with route hint like ``up_back`` are excluded from bundles.

    Returns
    -------
    grouped: {gid: {"kind": "fan_in"|"fan_out", "edges": [...],
                    "shared_cp": endpoint_cp, "other_cps": [...],
                    "hue_key": str, "arrow_kind": "sync"|"async"}}
    bundle_map: {id(edge_dict): gid}
    """
    grouped: Dict[int, Dict[str, Any]] = {}
    bundle_map: Dict[int, int] = {}
    next_gid = 0

    # bucket by dst (fan-in) — key = (dst_key, arrow_kind)
    fan_in_buckets: Dict[Tuple[Tuple[int, int], str], List[Dict[str, Any]]] = {}
    for e in edges:
        if e.get("route"):  # skip routed specials (up_back)
            continue
        src = e.get("src"); dst = e.get("dst")
        if not (isinstance(src, tuple) and isinstance(dst, tuple)):
            continue
        if src not in containers_by_key or dst not in containers_by_key:
            continue
        kind = e.get("kind", "sync")
        arrow_kind = "async" if kind == "async" else "sync"
        fan_in_buckets.setdefault((dst, arrow_kind), []).append(e)

    # fan-out buckets — key = (src_key, arrow_kind)
    fan_out_buckets: Dict[Tuple[Tuple[int, int], str], List[Dict[str, Any]]] = {}
    for e in edges:
        if e.get("route"):
            continue
        src = e.get("src"); dst = e.get("dst")
        if not (isinstance(src, tuple) and isinstance(dst, tuple)):
            continue
        if src not in containers_by_key or dst not in containers_by_key:
            continue
        kind = e.get("kind", "sync")
        arrow_kind = "async" if kind == "async" else "sync"
        fan_out_buckets.setdefault((src, arrow_kind), []).append(e)

    used_edge_ids: set = set()

    def _same_topology(bucket: List[Dict[str, Any]], mode: str) -> bool:
        """All edges in bucket share the same src↔dst boundary+row relation ·
        avoid mixing same-row and cross-boundary in one bundle."""
        rels = []
        for e in bucket:
            src_cp = containers_by_key[e["src"]]
            dst_cp = containers_by_key[e["dst"]]
            rels.append((
                src_cp["boundary_index"] == dst_cp["boundary_index"],
                src_cp.get("row", 0) == dst_cp.get("row", 0),
            ))
        return len(set(rels)) == 1

    # emit fan-in first (2+ edges into same dst)
    for (dst_key, arrow_kind), bucket in fan_in_buckets.items():
        if len(bucket) < 2:
            continue
        # skip if any edge already used
        if any(id(e) in used_edge_ids for e in bucket):
            continue
        if not _same_topology(bucket, "fan_in"):
            continue
        dst_cp = containers_by_key[dst_key]
        src_cps = [containers_by_key[e["src"]] for e in bucket]
        # require all sources to sit "above" dst OR all sources same row/left of dst
        # → to keep bundle geometry sane. Otherwise fall through.
        if not _bundle_geometry_ok(src_cps, dst_cp, mode="fan_in"):
            continue
        # pick a shared hue: prefer dst hue for sync; grey for async
        if arrow_kind == "async":
            hue_key = "grey"
        else:
            hue_key = bucket[0].get("hue") or dst_cp.get("hue") or "rust"
        gid = next_gid; next_gid += 1
        grouped[gid] = {
            "kind": "fan_in",
            "edges": bucket,
            "shared_cp": dst_cp,
            "other_cps": src_cps,
            "hue_key": hue_key,
            "arrow_kind": arrow_kind,
        }
        for e in bucket:
            bundle_map[id(e)] = gid
            used_edge_ids.add(id(e))

    # emit fan-out (2+ edges out of same src) — skip edges already in fan-in
    for (src_key, arrow_kind), bucket in fan_out_buckets.items():
        bucket = [e for e in bucket if id(e) not in used_edge_ids]
        if len(bucket) < 2:
            continue
        if not _same_topology(bucket, "fan_out"):
            continue
        src_cp = containers_by_key[src_key]
        dst_cps = [containers_by_key[e["dst"]] for e in bucket]
        if not _bundle_geometry_ok(dst_cps, src_cp, mode="fan_out"):
            continue
        if arrow_kind == "async":
            hue_key = "grey"
        else:
            hue_key = bucket[0].get("hue") or dst_cps[0].get("hue") or src_cp.get("hue") or "rust"
        gid = next_gid; next_gid += 1
        grouped[gid] = {
            "kind": "fan_out",
            "edges": bucket,
            "shared_cp": src_cp,
            "other_cps": dst_cps,
            "hue_key": hue_key,
            "arrow_kind": arrow_kind,
        }
        for e in bucket:
            bundle_map[id(e)] = gid
            used_edge_ids.add(id(e))

    return grouped, bundle_map


def _bundle_geometry_ok(
    other_cps: List[Dict[str, Any]], shared_cp: Dict[str, Any], mode: str,
) -> bool:
    """Bundle only when other_cps sit on ONE side of shared_cp so trunk stays clean.

    For fan-in: all sources above dst OR all left OR all right OR all below.
    For fan-out: mirror.
    """
    if len(other_cps) < 2:
        return False
    sx = shared_cp["x"] + shared_cp["w"] / 2
    sy = shared_cp["y"] + shared_cp["h"] / 2
    signs_x = [1 if (cp["x"] + cp["w"] / 2) < sx else -1 if (cp["x"] + cp["w"] / 2) > sx else 0
                for cp in other_cps]
    signs_y = [1 if (cp["y"] + cp["h"] / 2) < sy else -1 if (cp["y"] + cp["h"] / 2) > sy else 0
                for cp in other_cps]
    # allow: all same y-sign (all above or all below) → vertical bundle
    if all(s == signs_y[0] and s != 0 for s in signs_y):
        return True
    # or: all same x-sign (all left or all right) → horizontal bundle
    if all(s == signs_x[0] and s != 0 for s in signs_x):
        return True
    return False


def _render_edge_bundle(
    group: Dict[str, Any],
    all_cps: List[Dict[str, Any]],
    boundary_positions: List[Dict[str, Any]],
    row_cps_by_row: Dict[Tuple[int, int], List[Dict[str, Any]]],
    used_labels: Optional[List[Tuple[float, float, float, float]]] = None,
) -> str:
    """Render fan-in / fan-out bundle:
    · shared trunk into/out of shared_cp (with ONE arrowhead marker)
    · tributaries meet trunk at branch point (no arrowhead per tributary)
    · labels stacked along tributaries in the gutter · offset y to avoid overlap.
    """
    parts: List[str] = []
    kind = group["kind"]
    arrow_kind = group["arrow_kind"]
    hue_key = group["hue_key"]
    shared_cp = group["shared_cp"]
    other_cps = group["other_cps"]
    edges = group["edges"]
    overview = any(edge.get("_c4_overview") for edge in edges)
    hue_full = _hue_rgba(hue_key, C4_DENSE_OVERVIEW_ALPHA if overview else 1.0)
    hue_halo = _hue_rgba(hue_key, C4_DENSE_OVERVIEW_HALO_ALPHA if overview else 0.14)
    marker_key = _hue_key_for_marker(hue_key)

    # sort tributaries by position to keep visual order
    if kind == "fan_in":
        dst_cp = shared_cp
        src_cps = list(other_cps)
        # determine bundle direction: vertical (sources above/below) or horizontal
        s_cy = sum(cp["y"] + cp["h"] / 2 for cp in src_cps) / len(src_cps)
        d_cy = dst_cp["y"] + dst_cp["h"] / 2
        vertical = abs(s_cy - d_cy) > (dst_cp["h"] + 20)
        # Force vertical if all endpoints share (boundary, row) — a same-row bundle
        # with horizontal trunk would cross intermediate cards.
        same_row = all(
            cp["boundary_index"] == dst_cp["boundary_index"]
            and cp.get("row", 0) == dst_cp.get("row", 0) for cp in src_cps
        )
        if same_row and len(src_cps) >= 2:
            vertical = True
    else:  # fan_out
        src_cp = shared_cp
        dst_cps = list(other_cps)
        d_cy = sum(cp["y"] + cp["h"] / 2 for cp in dst_cps) / len(dst_cps)
        s_cy = src_cp["y"] + src_cp["h"] / 2
        vertical = abs(d_cy - s_cy) > (src_cp["h"] + 20)
        same_row = all(
            cp["boundary_index"] == src_cp["boundary_index"]
            and cp.get("row", 0) == src_cp.get("row", 0) for cp in dst_cps
        )
        if same_row and len(dst_cps) >= 2:
            vertical = True

    # Vertical bundle: trunk is horizontal at branch_y; tributaries come out of source tops/bottoms.
    # Horizontal bundle: trunk is vertical at branch_x; tributaries come out of source sides.
    if vertical:
        _render_vertical_bundle(parts, group, hue_full, hue_halo, marker_key,
                                  arrow_kind, boundary_positions, all_cps,
                                  used_labels=used_labels)
    else:
        _render_horizontal_bundle(parts, group, hue_full, hue_halo, marker_key,
                                    arrow_kind, all_cps,
                                    used_labels=used_labels)

    return "".join(parts)


def _render_vertical_bundle(
    parts: List[str],
    group: Dict[str, Any],
    hue_full: str, hue_halo: str, marker_key: str,
    arrow_kind: str,
    boundary_positions: List[Dict[str, Any]],
    all_cps: List[Dict[str, Any]],
    used_labels: Optional[List[Tuple[float, float, float, float]]] = None,
) -> None:
    """Vertical bundle: trunk = horizontal segment between src rows and dst row.
    Tributaries drop from src.bottom (or rise from src.top); merge at trunk_y;
    then a single stem descends (or ascends) to dst.top (or dst.bottom) with ONE arrowhead.

    Same-row bundle (all endpoints in same boundary row) routes through the row gutter
    (above row into boundary_pad_top OR below row into boundary_pad_bottom).
    """
    kind = group["kind"]
    shared_cp = group["shared_cp"]
    other_cps = list(group["other_cps"])
    edges = list(group["edges"])

    # detect same-row bundle (all endpoints share boundary+row)
    all_endpoints = other_cps + [shared_cp]
    same_row = all(
        cp["boundary_index"] == shared_cp["boundary_index"]
        and cp.get("row", 0) == shared_cp.get("row", 0) for cp in all_endpoints
    )

    if same_row:
        bi = shared_cp["boundary_index"]
        b = boundary_positions[bi]
        row_top = min(cp["y"] for cp in all_endpoints)
        row_bot = max(cp["y"] + cp["h"] for cp in all_endpoints)
        top_gap = row_top - (b["y"] + 24)  # header + breathing
        bot_gap = (b["y"] + b["h"] - 4) - row_bot
        # prefer the bigger gutter
        use_top = top_gap >= bot_gap
        if use_top:
            gutter_y = row_top - 14  # 14px above row
            # emerge from src.top / enter dst.top
            exit_side = "top"
        else:
            gutter_y = row_bot + 14
            exit_side = "bottom"
    else:
        gutter_y = None
        exit_side = None

    if kind == "fan_in":
        dst_cp = shared_cp
        src_cps = other_cps
        if same_row:
            if exit_side == "top":
                src_exit_y = [cp["y"] for cp in src_cps]
                dst_entry = (dst_cp["x"] + dst_cp["w"] / 2, dst_cp["y"])
            else:
                src_exit_y = [cp["y"] + cp["h"] for cp in src_cps]
                dst_entry = (dst_cp["x"] + dst_cp["w"] / 2, dst_cp["y"] + dst_cp["h"])
            trunk_y = gutter_y
        else:
            all_above = all((cp["y"] + cp["h"] / 2) < (dst_cp["y"] + dst_cp["h"] / 2)
                            for cp in src_cps)
            down = all_above  # sources above dst → trunk descends into dst top
            if down:
                # tributaries emerge from src.bottom, meet trunk_y, drop to dst.top
                src_exit_y = [cp["y"] + cp["h"] for cp in src_cps]
                dst_entry = (dst_cp["x"] + dst_cp["w"] / 2, dst_cp["y"])
                # trunk_y sits between max(src_exit_y) and dst_entry.y
                src_bi = src_cps[0]["boundary_index"]
                dst_bi = dst_cp["boundary_index"]
                if src_bi != dst_bi and dst_bi > src_bi:
                    # place trunk in boundary gap
                    trunk_y = _midway_between_boundaries(
                        boundary_positions[src_bi], boundary_positions[dst_bi])
                else:
                    trunk_y = (max(src_exit_y) + dst_entry[1]) / 2
            else:
                # sources below dst → trunk above dst, tributaries emerge from src.top
                src_exit_y = [cp["y"] for cp in src_cps]
                dst_entry = (dst_cp["x"] + dst_cp["w"] / 2, dst_cp["y"] + dst_cp["h"])
                src_bi = src_cps[0]["boundary_index"]
                dst_bi = dst_cp["boundary_index"]
                if src_bi != dst_bi and src_bi > dst_bi:
                    trunk_y = _midway_between_boundaries(
                        boundary_positions[src_bi], boundary_positions[dst_bi])
                else:
                    trunk_y = (min(src_exit_y) + dst_entry[1]) / 2
        # sort src by x for label stack
        pair_list = sorted(list(zip(src_cps, edges, src_exit_y)),
                            key=lambda t: t[0]["x"])
        src_cps = [t[0] for t in pair_list]
        edges = [t[1] for t in pair_list]
        src_exit_y = [t[2] for t in pair_list]

        # trunk covers x-range: min(src cx, dst cx) .. max(src cx, dst cx)
        xs = [cp["x"] + cp["w"] / 2 for cp in src_cps] + [dst_entry[0]]
        trunk_x_lo, trunk_x_hi = min(xs), max(xs)
    else:  # fan_out
        src_cp = shared_cp
        dst_cps = other_cps
        if same_row:
            if exit_side == "top":
                src_exit = (src_cp["x"] + src_cp["w"] / 2, src_cp["y"])
                dst_entry_y = [cp["y"] for cp in dst_cps]
            else:
                src_exit = (src_cp["x"] + src_cp["w"] / 2, src_cp["y"] + src_cp["h"])
                dst_entry_y = [cp["y"] + cp["h"] for cp in dst_cps]
            trunk_y = gutter_y
        else:
            all_below = all((cp["y"] + cp["h"] / 2) > (src_cp["y"] + src_cp["h"] / 2)
                            for cp in dst_cps)
            down = all_below
            if down:
                src_exit = (src_cp["x"] + src_cp["w"] / 2, src_cp["y"] + src_cp["h"])
                dst_entry_y = [cp["y"] for cp in dst_cps]
                src_bi = src_cp["boundary_index"]
                dst_bi = dst_cps[0]["boundary_index"]
                if src_bi != dst_bi and dst_bi > src_bi:
                    trunk_y = _midway_between_boundaries(
                        boundary_positions[src_bi], boundary_positions[dst_bi])
                else:
                    trunk_y = (src_exit[1] + min(dst_entry_y)) / 2
            else:
                src_exit = (src_cp["x"] + src_cp["w"] / 2, src_cp["y"])
                dst_entry_y = [cp["y"] + cp["h"] for cp in dst_cps]
                src_bi = src_cp["boundary_index"]
                dst_bi = dst_cps[0]["boundary_index"]
                if src_bi != dst_bi and src_bi > dst_bi:
                    trunk_y = _midway_between_boundaries(
                        boundary_positions[src_bi], boundary_positions[dst_bi])
                else:
                    trunk_y = (src_exit[1] + max(dst_entry_y)) / 2
        pair_list = sorted(list(zip(dst_cps, edges, dst_entry_y)),
                            key=lambda t: t[0]["x"])
        dst_cps = [t[0] for t in pair_list]
        edges = [t[1] for t in pair_list]
        dst_entry_y = [t[2] for t in pair_list]
        xs = [cp["x"] + cp["w"] / 2 for cp in dst_cps] + [src_exit[0]]
        trunk_x_lo, trunk_x_hi = min(xs), max(xs)

    # ── emit polylines ──
    if arrow_kind == "async":
        line_style = (f'fill="none" stroke="{hue_full}" stroke-width="1.3" '
                       f'stroke-dasharray="5 4" stroke-linejoin="round" '
                       f'stroke-linecap="round"')
        halo_style = None
    else:
        line_style = (f'fill="none" stroke="{hue_full}" stroke-width="1.5" '
                       f'stroke-linejoin="round" stroke-linecap="round"')
        halo_style = (f'fill="none" stroke="{hue_halo}" stroke-width="4.4" '
                       f'stroke-linejoin="round" stroke-linecap="round"')

    if kind == "fan_in":
        # trunk from trunk_x_lo,trunk_y to trunk_x_hi,trunk_y (as one poly)
        # then stem down to dst.top (or up to dst.bottom) — single arrowhead
        trunk_pts = [(trunk_x_lo, trunk_y), (trunk_x_hi, trunk_y)]
        trunk_d = _pts_to_path_d(trunk_pts)
        # stem: (dst_cx, trunk_y) → dst_entry
        stem_pts = [(dst_entry[0], trunk_y), dst_entry]
        stem_d = _pts_to_path_d(stem_pts)
        # tributaries per src
        trib_paths: List[str] = []
        for cp, exit_y in zip(src_cps, src_exit_y):
            cx = cp["x"] + cp["w"] / 2
            trib_pts = [(cx, exit_y), (cx, trunk_y)]
            trib_paths.append(_pts_to_path_d(trib_pts))
        # emit halos first
        if halo_style:
            for d in [trunk_d, stem_d, *trib_paths]:
                parts.append(f'<path d="{d}" {halo_style}/>')
        # solid trunk + tributaries (no marker)
        for d in [trunk_d, *trib_paths]:
            parts.append(f'<path d="{d}" {line_style}/>')
        # solid stem with ONE marker
        parts.append(
            f'<path d="{stem_d}" {line_style} '
            f'marker-end="url(#c4_arr_{marker_key})"/>'
        )
        # labels: stack along each tributary in the gutter
        for cp, exit_y, e in zip(src_cps, src_exit_y, edges):
            cx = cp["x"] + cp["w"] / 2
            label_y = (exit_y + trunk_y) / 2
            _emit_bundle_label(parts, e, cx + 6, label_y, "start",
                                 hue_full, arrow_kind,
                                 used_labels=used_labels,
                                 all_cps=all_cps,
                                 endpoint_ids={cp["id"], dst_cp["id"]})
    else:  # fan_out
        trunk_pts = [(trunk_x_lo, trunk_y), (trunk_x_hi, trunk_y)]
        trunk_d = _pts_to_path_d(trunk_pts)
        stem_pts = [src_exit, (src_exit[0], trunk_y)]
        stem_d = _pts_to_path_d(stem_pts)
        trib_paths_with_marker: List[Tuple[str, Tuple[float, float]]] = []
        for cp, entry_y in zip(dst_cps, dst_entry_y):
            cx = cp["x"] + cp["w"] / 2
            trib_pts = [(cx, trunk_y), (cx, entry_y)]
            trib_paths_with_marker.append((_pts_to_path_d(trib_pts), (cx, entry_y)))
        # halos
        if halo_style:
            parts.append(f'<path d="{stem_d}" {halo_style}/>')
            parts.append(f'<path d="{trunk_d}" {halo_style}/>')
            for d, _ in trib_paths_with_marker:
                parts.append(f'<path d="{d}" {halo_style}/>')
        # solid stem/trunk (no marker)
        parts.append(f'<path d="{stem_d}" {line_style}/>')
        parts.append(f'<path d="{trunk_d}" {line_style}/>')
        # each tributary gets an arrowhead (one per dst)
        for d, entry_pt in trib_paths_with_marker:
            parts.append(
                f'<path d="{d}" {line_style} '
                f'marker-end="url(#c4_arr_{marker_key})"/>'
            )
        # labels: per tributary, staggered in the gutter (mid of tributary)
        for cp, entry_y, e in zip(dst_cps, dst_entry_y, edges):
            cx = cp["x"] + cp["w"] / 2
            label_y = (trunk_y + entry_y) / 2
            _emit_bundle_label(parts, e, cx + 6, label_y, "start",
                                 hue_full, arrow_kind,
                                 used_labels=used_labels,
                                 all_cps=all_cps,
                                 endpoint_ids={src_cp["id"], cp["id"]})


def _render_horizontal_bundle(
    parts: List[str],
    group: Dict[str, Any],
    hue_full: str, hue_halo: str, marker_key: str,
    arrow_kind: str,
    all_cps: List[Dict[str, Any]],
    used_labels: Optional[List[Tuple[float, float, float, float]]] = None,
) -> None:
    """Horizontal bundle: trunk = vertical segment; tributaries emerge from
    src.right (or src.left); labels stack along tributaries in the horizontal gutter.
    """
    kind = group["kind"]
    shared_cp = group["shared_cp"]
    other_cps = list(group["other_cps"])
    edges = list(group["edges"])
    if kind == "fan_in":
        dst_cp = shared_cp
        src_cps = other_cps
        # sources all left or all right of dst?
        left_of = all((cp["x"] + cp["w"]) < dst_cp["x"] for cp in src_cps)
        if left_of:
            src_exit_x = [cp["x"] + cp["w"] for cp in src_cps]
            dst_entry = (dst_cp["x"], dst_cp["y"] + dst_cp["h"] / 2)
            trunk_x = (max(src_exit_x) + dst_entry[0]) / 2
        else:
            src_exit_x = [cp["x"] for cp in src_cps]
            dst_entry = (dst_cp["x"] + dst_cp["w"], dst_cp["y"] + dst_cp["h"] / 2)
            trunk_x = (min(src_exit_x) + dst_entry[0]) / 2
        pair_list = sorted(list(zip(src_cps, edges, src_exit_x)),
                            key=lambda t: t[0]["y"])
        src_cps = [t[0] for t in pair_list]
        edges = [t[1] for t in pair_list]
        src_exit_x = [t[2] for t in pair_list]
        ys = [cp["y"] + cp["h"] / 2 for cp in src_cps] + [dst_entry[1]]
        trunk_y_lo, trunk_y_hi = min(ys), max(ys)
    else:  # fan_out
        src_cp = shared_cp
        dst_cps = other_cps
        right_of = all(cp["x"] > (src_cp["x"] + src_cp["w"]) for cp in dst_cps)
        if right_of:
            src_exit = (src_cp["x"] + src_cp["w"], src_cp["y"] + src_cp["h"] / 2)
            dst_entry_x = [cp["x"] for cp in dst_cps]
            trunk_x = (src_exit[0] + min(dst_entry_x)) / 2
        else:
            src_exit = (src_cp["x"], src_cp["y"] + src_cp["h"] / 2)
            dst_entry_x = [cp["x"] + cp["w"] for cp in dst_cps]
            trunk_x = (src_exit[0] + max(dst_entry_x)) / 2
        pair_list = sorted(list(zip(dst_cps, edges, dst_entry_x)),
                            key=lambda t: t[0]["y"])
        dst_cps = [t[0] for t in pair_list]
        edges = [t[1] for t in pair_list]
        dst_entry_x = [t[2] for t in pair_list]
        ys = [cp["y"] + cp["h"] / 2 for cp in dst_cps] + [src_exit[1]]
        trunk_y_lo, trunk_y_hi = min(ys), max(ys)

    if arrow_kind == "async":
        line_style = (f'fill="none" stroke="{hue_full}" stroke-width="1.3" '
                       f'stroke-dasharray="5 4" stroke-linejoin="round" '
                       f'stroke-linecap="round"')
        halo_style = None
    else:
        line_style = (f'fill="none" stroke="{hue_full}" stroke-width="1.5" '
                       f'stroke-linejoin="round" stroke-linecap="round"')
        halo_style = (f'fill="none" stroke="{hue_halo}" stroke-width="4.4" '
                       f'stroke-linejoin="round" stroke-linecap="round"')

    if kind == "fan_in":
        trunk_pts = [(trunk_x, trunk_y_lo), (trunk_x, trunk_y_hi)]
        trunk_d = _pts_to_path_d(trunk_pts)
        stem_pts = [(trunk_x, dst_entry[1]), dst_entry]
        stem_d = _pts_to_path_d(stem_pts)
        trib_paths: List[str] = []
        for cp, exit_x in zip(src_cps, src_exit_x):
            cy = cp["y"] + cp["h"] / 2
            trib_pts = [(exit_x, cy), (trunk_x, cy)]
            trib_paths.append(_pts_to_path_d(trib_pts))
        if halo_style:
            for d in [trunk_d, stem_d, *trib_paths]:
                parts.append(f'<path d="{d}" {halo_style}/>')
        for d in [trunk_d, *trib_paths]:
            parts.append(f'<path d="{d}" {line_style}/>')
        parts.append(
            f'<path d="{stem_d}" {line_style} '
            f'marker-end="url(#c4_arr_{marker_key})"/>'
        )
        for cp, exit_x, e in zip(src_cps, src_exit_x, edges):
            cy = cp["y"] + cp["h"] / 2
            label_x = (exit_x + trunk_x) / 2
            _emit_bundle_label(parts, e, label_x, cy - 4, "middle",
                                 hue_full, arrow_kind,
                                 used_labels=used_labels,
                                 all_cps=all_cps,
                                 endpoint_ids={cp["id"], dst_cp["id"]})
    else:  # fan_out
        trunk_pts = [(trunk_x, trunk_y_lo), (trunk_x, trunk_y_hi)]
        trunk_d = _pts_to_path_d(trunk_pts)
        stem_pts = [src_exit, (trunk_x, src_exit[1])]
        stem_d = _pts_to_path_d(stem_pts)
        trib_paths_with_marker: List[Tuple[str, Tuple[float, float]]] = []
        for cp, entry_x in zip(dst_cps, dst_entry_x):
            cy = cp["y"] + cp["h"] / 2
            trib_pts = [(trunk_x, cy), (entry_x, cy)]
            trib_paths_with_marker.append((_pts_to_path_d(trib_pts), (entry_x, cy)))
        if halo_style:
            parts.append(f'<path d="{stem_d}" {halo_style}/>')
            parts.append(f'<path d="{trunk_d}" {halo_style}/>')
            for d, _ in trib_paths_with_marker:
                parts.append(f'<path d="{d}" {halo_style}/>')
        parts.append(f'<path d="{stem_d}" {line_style}/>')
        parts.append(f'<path d="{trunk_d}" {line_style}/>')
        for d, entry_pt in trib_paths_with_marker:
            parts.append(
                f'<path d="{d}" {line_style} '
                f'marker-end="url(#c4_arr_{marker_key})"/>'
            )
        for cp, entry_x, e in zip(dst_cps, dst_entry_x, edges):
            cy = cp["y"] + cp["h"] / 2
            label_x = (trunk_x + entry_x) / 2
            _emit_bundle_label(parts, e, label_x, cy - 4, "middle",
                                 hue_full, arrow_kind,
                                 used_labels=used_labels,
                                 all_cps=all_cps,
                                 endpoint_ids={src_cp["id"], cp["id"]})


def _emit_bundle_label(
    parts: List[str], edge: Dict[str, Any], mx: float, my: float, anchor: str,
    hue_full: str, arrow_kind: str,
    used_labels: Optional[List[Tuple[float, float, float, float]]] = None,
    all_cps: Optional[List[Dict[str, Any]]] = None,
    endpoint_ids: Optional[set] = None,
) -> None:
    label = edge.get("label", "") or ""
    if not label:
        return
    overview = bool(edge.get("_c4_overview"))
    italic = ' font-style="italic"' if arrow_kind == "async" else ""
    # Dense C4 keeps labels inline, but uses a smaller chip so labels remain
    # attached to edges without turning the centre into a text cloud.
    fs = _fs(8.0 if overview else 10.0)
    # R2 fix: match atomize width estimate so halo fully contains text shape.
    label_w = max(_estimate_text_w_svg(label, fs) + 18.0, 16 * _FS_SCALE)
    HALO_TOP = fs * 1.15
    HALO_H = fs * 1.6 + 4
    HALO_PAD_X = 7 if overview else 8

    def _halo_bbox(m_x: float, m_y: float) -> Tuple[float, float, float, float]:
        if anchor == "middle":
            hx = m_x - label_w / 2 - HALO_PAD_X
        elif anchor == "end":
            hx = m_x - label_w - HALO_PAD_X
        else:
            hx = m_x - HALO_PAD_X
        return (hx, m_y - HALO_TOP, hx + label_w + 2 * HALO_PAD_X,
                 m_y - HALO_TOP + HALO_H)

    def _hits_used(m_x: float, m_y: float) -> bool:
        if used_labels is None:
            return False
        x0, y0, x1, y1 = _halo_bbox(m_x, m_y)
        for ux0, uy0, ux1, uy1 in used_labels:
            if not (x1 < ux0 or ux1 < x0 or y1 < uy0 or uy1 < y0):
                return True
        return False

    def _hits_container(m_x: float, m_y: float) -> bool:
        if all_cps is None:
            return False
        x0, y0, x1, y1 = _halo_bbox(m_x, m_y)
        PAD = 2.0
        for cp in all_cps:
            is_endpoint = (
                endpoint_ids is not None and cp["id"] in endpoint_ids
            )
            rx0 = cp["x"] - PAD
            ry0 = cp["y"] - PAD
            rx1 = cp["x"] + cp["w"] + PAD
            ry1 = cp["y"] + cp["h"] + PAD
            if is_endpoint:
                # Full-card guard for endpoints.
                if not (x1 < rx0 or rx1 < x0 or y1 < ry0 or ry1 < y0):
                    return True
            else:
                # R3: non-endpoint only guards name band (top ~34 SVG px);
                # name-text bbox is already in used_labels for tight check.
                ry_name_bot = cp["y"] + 34
                if not (x1 < rx0 or rx1 < x0 or y1 < ry0 or ry_name_bot < y0):
                    return True
        return False

    # R2 fix: search for a nearby my/mx offset that doesn't hit used or container.
    # R3 fix (2026-09-11): if no dy candidate works · SKIP the halo + text. Better
    # to drop a bundle label than to gouge a container name.
    orig_my = my
    if _hits_used(mx, my) or _hits_container(mx, my):
        found = False
        # Keep bundle labels visually attached to their tributary. If nearby
        # slots collide, skip the label instead of drifting into open whitespace.
        for dy in (14, -14, 26, -26):
            cand_y = orig_my + dy
            if not _hits_used(mx, cand_y) and not _hits_container(mx, cand_y):
                my = cand_y
                found = True
                break
        if not found:
            # Skip label entirely rather than gouge a container name.
            return

    if anchor == "middle":
        halo_x = mx - label_w / 2 - HALO_PAD_X
    elif anchor == "end":
        halo_x = mx - label_w - HALO_PAD_X
    else:
        halo_x = mx - HALO_PAD_X
    parts.append(
        f'<rect x="{halo_x:.1f}" y="{my - HALO_TOP:.1f}" '
        f'width="{label_w + 2 * HALO_PAD_X:.1f}" height="{HALO_H:.1f}" '
        f'rx="4" fill="{EDGE_LABEL_BG}" stroke="{hue_full}" '
        f'stroke-opacity="{0.14 if overview else 0.20}" stroke-width="0.8"/>'
    )
    parts.append(
        f'<text x="{mx:.1f}" y="{my:.1f}" text-anchor="{anchor}" '
        f'font-family="{FONT_SANS}" font-size="{fs:.1f}" fill="{hue_full}" '
        f'font-weight="700" letter-spacing="0.3"{italic}>'
        f'{esc(label)}</text>'
    )
    if used_labels is not None:
        used_labels.append(
            (halo_x, my - HALO_TOP,
             halo_x + label_w + 2 * HALO_PAD_X, my - HALO_TOP + HALO_H)
        )


def _render_edge(
    edge: Dict[str, Any],
    src_cp: Dict[str, Any], dst_cp: Dict[str, Any],
    all_cps: List[Dict[str, Any]],
    boundary_positions: List[Dict[str, Any]],
    row_cps_by_row: Dict[Tuple[int, int], List[Dict[str, Any]]],
    used_labels: Optional[List[Tuple[float, float, float, float]]] = None,
    layout_edge_meta: Optional[Dict[str, Any]] = None,
    render_stroke: bool = True,
    render_label: bool = True,
    avoid_label_bboxes: Optional[List[Tuple[float, float, float, float]]] = None,
    avoid_line_segments: Optional[List[Tuple[float, float, float, float, str]]] = None,
    commit_line_segments: Optional[List[Tuple[float, float, float, float, str]]] = None,
) -> str:
    """Emit double-layer arrow (halo + solid) + label.

    R5 (2026-09-13): if ``layout_edge_meta`` is provided (fresh output from
    :func:`c4_container_v2_layout` — includes ``label_mx``/``label_my`` +
    ``halo_x``/``halo_y``/``halo_w``/``halo_h``/``halo_fill`` with 20px
    border-avoid already applied), we skip the preset's own
    ``_pick_label_position`` and emit the halo + text at layout-given coords.
    If ``layout_edge_meta`` is None (old caller / edge count mismatch), we
    fall back to the preset's own collision-avoid path.
    """
    kind = edge.get("kind", "sync")
    overview = bool(edge.get("_c4_overview"))
    # hue 决策
    if kind == "async":
        # dashed grey
        hue_key = "grey"
    else:
        # sync: 优先自定 · 否则用 dst container hue (跨 boundary 用 dst hue)
        hue_key = edge.get("hue") or ("ink" if overview else dst_cp.get("hue")) or "rust"
    hue_full = _hue_rgba(hue_key, C4_DENSE_OVERVIEW_ALPHA if overview else 1.0)
    hue_halo = _hue_rgba(hue_key, C4_DENSE_OVERVIEW_HALO_ALPHA if overview else 0.14)
    curve = _build_curve_geometry(
        edge, src_cp, dst_cp, all_cps,
        avoid_label_bboxes=avoid_label_bboxes if render_stroke else None,
    )
    samples = curve["samples"]
    parts: List[str] = []
    if render_stroke:
        if kind == "async":
            line_w = 0.95 if overview else 1.3
            # 中文注释：曲线只输出单条 Bezier path；没有折线路由锚点。
            # 曲率由起终点位置和端点法线自动决定，分流只通过节点边上的
            # 起终点偏移完成。
            _emit_curve_stroke(
                parts, curve, stroke=hue_full, width=line_w, dashed=True
            )
            _emit_arrowhead(parts, samples, fill=hue_full,
                            size=7.0 if overview else 8.5)
        else:
            halo_w = 2.6 if overview else 4.4
            line_w = 1.0 if overview else 1.5
            _emit_curve_stroke(
                parts, curve, stroke=hue_halo, width=halo_w
            )
            _emit_curve_stroke(
                parts, curve, stroke=hue_full, width=line_w
            )
            _emit_arrowhead(parts, samples, fill=hue_full,
                            size=7.0 if overview else 8.5)

    if render_stroke and commit_line_segments is not None:
        commit_line_segments.extend(_segments_from_pts(samples))

    if not render_label:
        return "".join(parts)

    blockers: List[Tuple[float, float, float, float]] = list(avoid_label_bboxes or [])
    # 中文注释：图表标题区也是文本区域，tag 不能为了贴近曲线而压住标题/副标题。
    blockers.append((50.0, 20.0, VIEW_W - 50.0, 132.0))
    # 中文注释：tag 的避让对象包含完整节点框，避免遮挡节点内任意文本。
    for cp in all_cps:
        blockers.append((cp["x"], cp["y"], cp["x"] + cp["w"], cp["y"] + cp["h"]))
    # 中文注释：边界标题/说明也是文本区域，tag 不能压住这些静态文字。
    for bp in boundary_positions:
        blockers.append((bp["x"] + 8, bp["y"] + 2,
                         bp["x"] + min(360.0, bp["w"]), bp["y"] + 34))
        blockers.append((bp["x"] + bp["w"] - 360.0, bp["y"] + 2,
                         bp["x"] + bp["w"], bp["y"] + 34))
    parts.append(_curve_label_svg(
        edge, samples,
        hue_key=hue_key,
        hue_full=hue_full,
        kind=kind,
        overview=overview,
        blockers=blockers,
        used_labels=used_labels,
    ))
    return "".join(parts)

def _render_legend(
    boundaries: List[Dict[str, Any]],
    y_start: float, x_start: float,
    sync_hue_key: str = "teal",
) -> str:
    """Emit legend row: boundary swatches + edge variants.

    Parameters
    ----------
    sync_hue_key : str
        Hue key to use for the "Sync request" swatch/marker in the legend. Must
        be a hue that actually appears on a sync/cross edge inside the diagram
        body so we never reference a marker that isn't defined (mini variants
        may lack the teal boundary entirely).
    """
    parts: List[str] = []
    parts.append(
        f'<line x1="60" y1="{y_start:.1f}" x2="1340" y2="{y_start:.1f}" '
        f'stroke="rgba(175,178,188,1)" stroke-width="0.4"/>'
    )
    label_y = y_start + 16
    parts.append(
        f'<text x="60" y="{label_y:.1f}" font-family="{FONT_SANS}" '
        f'font-size="10.5" font-weight="700" fill="{INK}" '
        f'letter-spacing="1.4">LEGEND · containers &amp; edges</text>'
    )
    swatch_y = y_start + 32
    text_y = y_start + 43
    sub_y = y_start + 56
    sub_y2 = y_start + 68  # second wrap line when 1 line at ≥10pt overflows

    # swatch per boundary (最多 3-4 个空间)
    swatch_w = 14
    # xs positions adapt to n boundaries so short decks (2 boundaries) still fill the row
    n_b = len(boundaries)
    if n_b == 2:
        # 2 boundary + 2 arrow slots → 4-column layout · uniform 320px spacing
        xs = [60, 380, 700, 1020]
        col_w = 260  # widened to fit body text at ≥10pt
    elif n_b == 3:
        xs = [60, 285, 555, 815, 1075]
        col_w = 220
    elif n_b == 4:
        xs = [60, 260, 460, 660, 860, 1060]
        col_w = 195
    else:
        xs = [60, 240, 440, 640, 840, 1040]
        col_w = 195
    n_show = min(n_b, len(xs) - 2)  # 留 2 位置给 sync/async arrow

    for i in range(n_show):
        b = boundaries[i]
        hue = b["hue"]
        c_full = _hue_rgba(hue, 1.0)
        c_tint = _hue_rgba(hue, 0.12)
        x = xs[i]
        parts.append(
            f'<rect x="{x}" y="{swatch_y:.1f}" width="{swatch_w}" '
            f'height="14" rx="3" fill="{c_tint}" stroke="{c_full}" '
            f'stroke-width="1.3"/>'
        )
        # boundary name (前缀清洗 · e.g. "EDGE · BOUNDARY 1" → "Edge boundary")
        b_lbl = b["label"] or ""
        # 取 · 前的段
        first_seg = re.split(r'[·|]', b_lbl)[0].strip().title()
        display = f"{first_seg} boundary" if first_seg else "Boundary"
        fs, txt = _fit_font_size(display, col_w, 10.5, min_size=10.0)
        parts.append(
            f'<text x="{x + swatch_w + 8}" y="{text_y:.1f}" '
            f'font-family="{FONT_SANS}" font-size="{fs:.1f}" '
            f'font-weight="700" fill="{INK}">{esc(txt)}</text>'
        )
        # sub · list container names · wrap to 2 lines at 10pt (never shrink below 10)
        b_containers = b.get("_containers", [])
        sub_names_all = [c.get("name", "") for c in b_containers]
        sub_names_all = [s for s in sub_names_all if s]
        # target width for legend body text
        sub_body_x = x + swatch_w + 8
        # build a 2-line wrap at 10pt from the name list · use "·" separator
        # first line: as many names as fit in col_w at 10pt
        # second line: continuation ("… trailing names") · if still overflow, append "…"
        sub_lines: List[str] = []
        if sub_names_all:
            fs_body = 10.0
            # binary greedy: fit line by name-count with " · " separators
            def _fits(text: str) -> bool:
                # emulate _visual_width at font-size 10, char_w ratio 0.55
                return len(text) * fs_body * 0.55 <= col_w
            # line 1
            i_idx = 0
            line1_items: List[str] = []
            while i_idx < len(sub_names_all):
                trial_items = line1_items + [sub_names_all[i_idx]]
                trial = " · ".join(trial_items)
                if _fits(trial):
                    line1_items = trial_items
                    i_idx += 1
                else:
                    break
            if not line1_items:
                # even a single first name too long — truncate with ellipsis at 10pt
                fs2, sub_display = _fit_font_size(
                    sub_names_all[0], col_w, 10.0, min_size=10.0)
                sub_lines = [sub_display]
                i_idx = 1
            else:
                sub_lines.append(" · ".join(line1_items))
            # line 2 if we have leftovers
            if i_idx < len(sub_names_all):
                remaining = sub_names_all[i_idx:]
                line2_items: List[str] = []
                for name in remaining:
                    trial_items = line2_items + [name]
                    trial = " · ".join(trial_items)
                    if _fits(trial):
                        line2_items = trial_items
                    else:
                        break
                if line2_items:
                    line2_text = " · ".join(line2_items)
                    if len(line2_items) < len(remaining):
                        # need to signal more items — append " · +N more" (硬红线: no ellipsis)
                        n_more = len(remaining) - len(line2_items)
                        suffix = f" · +{n_more} more"
                        if _fits(line2_text + suffix):
                            line2_text = line2_text + suffix
                    sub_lines.append(line2_text)
                else:
                    # even the next name doesn't fit — truncate that name
                    fs2, sub_display = _fit_font_size(
                        remaining[0], col_w, 10.0, min_size=10.0)
                    sub_lines.append(sub_display)
        # emit sub lines at ≥10pt
        for k, line in enumerate(sub_lines[:2]):
            ly = sub_y if k == 0 else sub_y2
            parts.append(
                f'<text x="{sub_body_x}" y="{ly:.1f}" '
                f'font-family="{FONT_SANS}" font-size="10.0" '
                f'fill="{GREY}">{esc(line)}</text>'
            )

    # arrow legends (sync + async)
    # 挑两个空 slot
    arrow_x1 = xs[n_show] if n_show < len(xs) else 1000
    arrow_x2 = arrow_x1 + 300
    if arrow_x2 > 1240:
        arrow_x2 = 1160
        arrow_x1 = 830

    for (ax, ay, kind_label, kind_sub, hue_key, is_dashed) in [
        (arrow_x1, swatch_y + 7, "Sync request",
         "solid coloured line · in-boundary or cross", sync_hue_key, False),
        (arrow_x2, swatch_y + 7, "Async · telemetry",
         "dashed grey · fire-and-forget events", "grey", True),
    ]:
        hue_c = _hue_rgba(hue_key, 1.0)
        marker_key = _hue_key_for_marker(hue_key)
        dash_attr = 'stroke-dasharray="5 4"' if is_dashed else ''
        parts.append(
            f'<line x1="{ax}" y1="{ay:.1f}" x2="{ax + 44}" y2="{ay:.1f}" '
            f'stroke="{hue_c}" stroke-width="1.8" {dash_attr} '
            f'marker-end="url(#c4_arr_{marker_key})"/>'
        )
        parts.append(
            f'<text x="{ax + 54}" y="{text_y:.1f}" font-family="{FONT_SANS}" '
            f'font-size="10.5" font-weight="700" fill="{INK}">'
            f'{esc(kind_label)}</text>'
        )
        parts.append(
            f'<text x="{ax + 54}" y="{sub_y:.1f}" font-family="{FONT_SANS}" '
            f'font-size="10.0" fill="{GREY}">{esc(kind_sub)}</text>'
        )

    return "".join(parts)


def _render_footer(source: str, source_tail: str, y_start: float) -> str:
    parts: List[str] = []
    parts.append(
        f'<line x1="60" y1="{y_start:.1f}" x2="1340" y2="{y_start:.1f}" '
        f'stroke="rgba(175,178,188,1)" stroke-width="0.5"/>'
    )
    text_y = y_start + 13
    txt = (
        f'<text x="60" y="{text_y:.1f}" font-family="{FONT_SANS}" '
        f'font-size="10.0" fill="{INK_MID}">'
        f'<tspan font-weight="700">Notes.</tspan> {esc(source)} '
        f'<tspan fill="{GREY}">{esc(source_tail)}</tspan></text>'
    )
    parts.append(txt)
    # Sentinel · invisible zero-stroke line at footer descent (fs*0.2 ≈ 2 below baseline)
    # · used only to let shrink_viewbox reach past the tspan-nested <text>
    # (compute_content_bbox regex 无法匹配 tspan · 借 line 撑出 y-extent)
    sentinel_y = text_y + 3
    parts.append(
        f'<line x1="60" y1="{sentinel_y:.1f}" x2="60.1" y2="{sentinel_y:.1f}" '
        f'stroke="rgba(250,246,235,0.001)" stroke-width="0.1"/>'
    )
    return "".join(parts)


def render_hero_embed_c4_v2(
    data: Tree = HERO_CS_C4_V2_DATA,
    palette: Palette = BONE_RUST,
    params: Optional[C4ContainerParams] = None,
    *,
    subtract_level: str = "L3",
) -> str:
    """Render C4 container view · dandelion-migrated · viewBox 1400×720.

    Data schema · Tree
        root.label      → title
        root.sublabel   → subtitle
        root.detail     → figure line note
        root.extra      → {kicker, edges, figure_id, notation_note,
                            source, source_tail, legend_note}
        root.children   → boundaries (TreeNode with label/sublabel/group=hue)
        boundary.children → containers (label=name / sublabel=tech / detail=kicker)
    """
    # [FONT-PATCH-L1] font pass-through (standalone): ea.FONT_SANS/SERIF 覆写
    _MOD_FONT = globals()
    _ORIG_FONT = {
        k: _MOD_FONT[k]
        for k in (
            'FONT_SANS', 'FONT_SERIF',
            'CREAM_BG', 'CARD_BG', 'EDGE_LABEL_BG',
            'INK', 'INK_MID', 'GREY',
        )
        if k in _MOD_FONT
    }
    try:
        from ..skins import editorial_atelier as _ea_font
        if 'FONT_SANS' in _MOD_FONT and _ea_font.FONT_SANS != _MOD_FONT['FONT_SANS']:
            _MOD_FONT['FONT_SANS'] = _ea_font.FONT_SANS
        if 'FONT_SERIF' in _MOD_FONT and _ea_font.FONT_SERIF != _MOD_FONT['FONT_SERIF']:
            _MOD_FONT['FONT_SERIF'] = _ea_font.FONT_SERIF
    except Exception:
        pass
    try:
        # R1 fix: default body layout tightened · body_y0 148 to fit enlarged
        # chrome (kicker 30, title 76, subtitle 104, hairline 118, figure line
        # 138 → boundaries start 148). Body compressed so B_last bot ≤ 670
        # so edge label detour (y ≈ b_bot + 12) fits within viewBox 720 ·
        # slide bottom = 110 + 696 × (440/720) ≈ 535 < 540 canvas guard.
        if params is None:
            p = C4ContainerParams(
                body_y0=154.0,
                body_y1=672.0,
                boundary_gap_y=8.0,
                boundary_pad_top=36.0,       # chip band y+4..y+32 fully inside pad_top
                boundary_pad_bottom=18.0,
                boundary_min_h=90.0,
                container_min_h=42.0,        # 5-boundary layout: cell_h ≈ 44 → card = 42
                container_max_h=68.0,
                container_row_gap_y=10.0,
                emit_edge_label_hints=False,
            )
        else:
            p = params
        pal = palette or BONE_RUST
        bg = getattr(pal, "bg", None) or CREAM_BG
        card_bg = _c4_neutral_card_bg(
            bg,
            getattr(pal, "bg_alt", None) or bg,
        )
        ink = getattr(pal, "ink", None) or INK
        gray = getattr(pal, "gray", None) or INK_MID
        _MOD_FONT["CREAM_BG"] = bg
        _MOD_FONT["CARD_BG"] = card_bg
        _MOD_FONT["EDGE_LABEL_BG"] = bg
        _MOD_FONT["INK"] = ink
        _MOD_FONT["INK_MID"] = gray
        _MOD_FONT["GREY"] = gray

        root = getattr(data, "root", None)
        if root is None:
            raise LayoutOverflow("c4 preset: no root")
        # Bucket H (2026-09-13) · subtract_level 默认 L3 · 清空次要说明字段
        # L1: 关 legend_note · notation_note · figure_note · figure_id
        # L2: L1 + boundary.sublabel (右侧 italic note)
        # L3: L2 + container.detail (kicker caps) + container.sublabel (tech tag)
        if subtract_level and subtract_level != "L0":
            import copy as _copy
            data = _copy.deepcopy(data)
            root = data.root
            _ex = root.extra or {}
            if subtract_level in ("L1", "L2", "L3"):
                _ex["legend_note"] = ""
                _ex["notation_note"] = ""
                _ex["source"] = _ex.get("source", "")
                root.detail = ""  # figure_note
                _ex["figure_id"] = ""
            if subtract_level in ("L2", "L3"):
                for b in root.children:
                    b.sublabel = ""
            if subtract_level == "L3":
                for b in root.children:
                    for c in b.children:
                        c.detail = ""
                        c.sublabel = ""
            root.extra = _ex
        extra = getattr(root, "extra", {}) or {}

        try:
            layout_out = c4_container_v2_layout(data, params=p)
        except LayoutOverflow:
            raise

        boundary_positions = layout_out["boundaries"]
        container_positions = layout_out["containers"]

        # Layout-level edge hints are legacy midpoint hints. Rendered C4 edges
        # often detour around rows/boundaries, so labels must be placed from
        # the actual polyline route to avoid floating away from their edge.
        layout_edges_out = layout_out.get("edges") or []
        _use_layout_edges = False
        layout_edge_meta_by_key: Dict[Tuple[Any, Any], Dict[str, Any]] = {}
        if _use_layout_edges:
            for meta in layout_edges_out:
                key = (meta.get("src"), meta.get("dst"))
                layout_edge_meta_by_key[key] = meta

        # ── 收集 hue keys 用于 marker defs ──
        hue_keys = set()
        for bp in boundary_positions:
            hue_keys.add(bp["hue"])
        for cp in container_positions:
            hue_keys.add(cp["hue"])
        hue_keys.add("ink")
        hue_keys.add("grey")

        # ── 拼 SVG ──
        parts: List[str] = [
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {VIEW_W} {VIEW_H}">',
        ]
        # background
        parts.append(
            f'<rect width="{VIEW_W}" height="{VIEW_H}" fill="{CREAM_BG}"/>'
        )
        # defs · arrow markers
        parts.append("<defs>")
        parts.append(_arrow_marker_defs(list(hue_keys)))
        parts.append("</defs>")

        # top chrome
        parts.append(_render_top_chrome(root, pal))

        # boundaries
        for bp in boundary_positions:
            parts.append(_render_boundary(bp))

        # containers
        for cp in container_positions:
            parts.append(_render_container(cp))

        # edges · 建 lookup table
        containers_by_key: Dict[Tuple[int, int], Dict[str, Any]] = {
            (cp["boundary_index"], cp["index_in_boundary"]): cp
            for cp in container_positions
        }
        # row_cps_by_row: (boundary_index, row) -> [cp,...]
        row_cps_by_row: Dict[Tuple[int, int], List[Dict[str, Any]]] = {}
        for cp in container_positions:
            row_cps_by_row.setdefault(
                (cp["boundary_index"], cp.get("row", 0)), []
            ).append(cp)
        raw_edges_data = extra.get("edges", []) or []
        edges_data = _prepare_edges_for_render(
            raw_edges_data,
            containers_by_key,
            edge_render_mode=str(extra.get("edge_render_mode", "auto") or "auto"),
            edge_label_mode=str(extra.get("edge_label_mode", "auto") or "auto"),
        )
        # Round4: render every edge with its own precomputed lane. Shared
        # fan-in/fan-out trunks made dense same-layer C4 edges look bundled
        # together online, especially after SVG marker/dash loss in atomize.
        grouped_edges, bundle_map = {}, {}
        # bundle_map: id(edge_dict) → group_id (or None)
        # grouped_edges: {group_id: {"kind": "fan_in"|"fan_out"|"solo", "edges": [...],
        #                             "shared_cp": cp_dict, "other_cps": [...]}}
        edge_render_items: List[Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Optional[Dict[str, Any]]]] = []
        for edge in edges_data:
            pair = _resolve_edge_endpoints(edge, containers_by_key)
            if pair is None:
                continue
            src_cp, dst_cp = pair
            _le_meta = None
            if _use_layout_edges:
                _le_meta = layout_edge_meta_by_key.get(
                    (edge.get("src"), edge.get("dst"))
                )
            edge_render_items.append((edge, src_cp, dst_cp, _le_meta))

        # 中文注释：先预规划所有 tag，再画曲线，最后统一画 tag。
        # 曲线层会避开“除本线 tag 外”的所有 tag；tag 层在最上方，避免
        # 线上渲染时后画曲线压住已有 tag。
        planned_label_bboxes: List[Tuple[float, float, float, float]] = []
        planned_label_svgs: List[str] = []
        for edge, src_cp, dst_cp, _le_meta in edge_render_items:
            planned_label_svgs.append(_render_edge(
                edge, src_cp, dst_cp,
                all_cps=container_positions,
                boundary_positions=boundary_positions,
                row_cps_by_row=row_cps_by_row,
                used_labels=planned_label_bboxes,
                layout_edge_meta=_le_meta,
                render_stroke=False,
                avoid_label_bboxes=planned_label_bboxes,
            ))
        committed_line_segments: List[Tuple[float, float, float, float, str]] = []
        for idx, (edge, src_cp, dst_cp, _le_meta) in enumerate(edge_render_items):
            other_label_bboxes = [
                bbox for j, bbox in enumerate(planned_label_bboxes) if j != idx
            ]
            parts.append(_render_edge(
                edge, src_cp, dst_cp,
                all_cps=container_positions,
                boundary_positions=boundary_positions,
                row_cps_by_row=row_cps_by_row,
                layout_edge_meta=_le_meta,
                render_label=False,
                avoid_label_bboxes=other_label_bboxes,
                commit_line_segments=committed_line_segments,
            ))
        parts.extend(planned_label_svgs)

        # legend — R1 fix: default OFF (audit medium: bottom LEGEND chatter).
        # 若 extra['legend_note'] 非空显式声明 → render legend + footer.
        legend_note = extra.get("legend_note", "") or ""
        show_legend = bool(legend_note.strip())
        if show_legend:
            for bp in boundary_positions:
                bp["_containers"] = [
                    {"name": cp["label"]} for cp in container_positions
                    if cp["boundary_index"] == bp["index"]
                ]
            # Infer a sync_hue_key that actually appears on a sync/cross edge
            sync_hue_key = "teal"
            body_sync_hues: List[str] = []
            for edge in edges_data:
                if edge.get("kind") == "async":
                    continue
                pair = _resolve_edge_endpoints(edge, containers_by_key)
                if pair is None:
                    continue
                _src_cp, _dst_cp = pair
                hue = edge.get("hue") or _dst_cp.get("hue") or "rust"
                body_sync_hues.append(_hue_key_for_marker(hue))
            if body_sync_hues:
                if "teal" in body_sync_hues:
                    sync_hue_key = "teal"
                else:
                    sync_hue_key = body_sync_hues[0]
            last_boundary_bot = max(bp["y"] + bp["h"] for bp in boundary_positions)
            legend_y = last_boundary_bot + 16
            parts.append(_render_legend(boundary_positions, y_start=legend_y,
                                         x_start=60, sync_hue_key=sync_hue_key))

            # footer notes — only if source/source_tail supplied AND legend shown
            footer_y = legend_y + 84
            source = extra.get("source", "") or ""
            source_tail = extra.get("source_tail", "") or ""
            if source or source_tail:
                parts.append(_render_footer(source, source_tail, y_start=footer_y))

        parts.append('</svg>')
        return "".join(parts)
    finally:
        _MOD_FONT.update(_ORIG_FONT)


# v1 兼容别名
render_hero_embed_cs_c4_v2 = render_hero_embed_c4_v2

# ─── legacy shims for previous v2 API ────────────────────────────
build_cs_c4_data = build_c4_tree  # legacy name
__all__ = [
    "HERO_CS_C4_V2_DATA",
    "HERO_CS_V2_DATA",
    "build_c4_tree",
    "build_cs_c4_data",
    "build_ecom_data",
    "build_bank_data",
    "build_mini_data",
    "render_hero_embed_c4_v2",
    "render_hero_embed_cs_c4_v2",
    "BASELINE_BOUNDARIES",
    "BASELINE_EDGES",
    "ECOM_BOUNDARIES",
    "ECOM_EDGES",
    "BANK_BOUNDARIES",
    "BANK_EDGES",
    "MINI_BOUNDARIES",
    "MINI_EDGES",
    "C4ContainerParams",
]
