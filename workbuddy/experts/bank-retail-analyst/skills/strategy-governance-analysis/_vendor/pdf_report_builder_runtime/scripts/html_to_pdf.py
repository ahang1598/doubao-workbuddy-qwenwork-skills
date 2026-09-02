#!/usr/bin/env python3
"""
PDF 渲染引擎
============
核心功能：
1. Jinja2 渲染 HTML（base_template + 业务模板）
2. Playwright 分两次导出 PDF（封面 + 正文）
3. pypdf 合并

用法::

    from html_to_pdf import build_report
    build_report(
        ctx={...},
        template_path="/abs/path/to/current-skill/assets/report_template.html",
        output_html="~/RetailAnalysis/output/<bank_short>/report.html",
        output_pdf="~/RetailAnalysis/output/<bank_short>/报告.pdf",
        style_overrides_path="/abs/path/to/current-skill/assets/style_overrides.css",
        base_bank="浦发",
        margin_top="25mm",
        margin_bottom="16mm",
    )
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup, escape as _html_escape

# 优先使用同级 paths.py
sys.path.insert(0, str(Path(__file__).parent))
from paths import (
    BASE_TEMPLATE_HTML,
    HEADER_FOOTER_HTML,
    LOGO_BASE64,
    LOGO_SOURCE,
    OUTPUT_DIR,
    PALETTE_JSON,
    RUNTIME_ASSETS_DIR,
    STYLE_GUIDE_CSS,
    ensure_dirs,
)

try:
    from bank_context import BankContext, resolve as resolve_bank  # type: ignore
except Exception:  # pragma: no cover - bank_context 未部署时降级
    BankContext = None  # type: ignore[misc,assignment]
    resolve_bank = None  # type: ignore[assignment]


def _legacy_logo_belongs_to(bank_ctx: "BankContext") -> bool:
    """判断 legacy 全局 LOGO 是否"确实属于"该基准行。

    校验双重条件，任一不通过都返回 False（不允许使用该 legacy LOGO）：
      A) legacy ``report_assets/vis/palette.json`` 的 primary 与该行官方色 ΔE<15；
      B) legacy ``report_assets/logo/logo_source.txt`` 包含该行识别词
         （短名 / 全称 / 别名 / 股票代码）。

    这是 2026-04-29 事故的护栏：之前光大基准行的 PDF 把 legacy 中信 LOGO
    直接塞给封面，导致视觉彻底污染。
    """
    if bank_ctx is None:
        return False

    # A) 色相校验：若无 legacy palette 则无法判定，视为不通过
    if not PALETTE_JSON.exists():
        return False
    try:
        with open(PALETTE_JSON) as f:
            legacy_primary = (json.load(f).get("primary") or "").upper()
    except Exception:
        return False
    official = (bank_ctx.primary_color or "").upper()
    if not legacy_primary or not official:
        return False
    try:
        # 简易 CIE76 ΔE（避免依赖外部模块）
        def _to_rgb(h):
            h = h.lstrip("#")
            return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

        def _to_lab(rgb):
            import math
            r, g, b = [c / 255.0 for c in rgb]
            def _lin(c):
                return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
            r, g, b = _lin(r), _lin(g), _lin(b)
            x = r * 0.4124564 + g * 0.3575761 + b * 0.1804375
            y = r * 0.2126729 + g * 0.7151522 + b * 0.0721750
            z = r * 0.0193339 + g * 0.1191920 + b * 0.9503041
            xn, yn, zn = 0.95047, 1.0, 1.08883
            def _f(t):
                return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
            fx, fy, fz = _f(x / xn), _f(y / yn), _f(z / zn)
            return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))

        import math as _math
        l1, a1, b1 = _to_lab(_to_rgb(legacy_primary))
        l2, a2, b2 = _to_lab(_to_rgb(official))
        de = _math.sqrt((l1 - l2) ** 2 + (a1 - a2) ** 2 + (b1 - b2) ** 2)
        if de >= 15:
            return False
    except Exception:
        return False

    # B) 身份校验：legacy logo_source.txt 必须含该行识别词
    if not LOGO_SOURCE.exists():
        return False
    try:
        src = LOGO_SOURCE.read_text(encoding="utf-8", errors="ignore").lower()
    except Exception:
        return False
    hints = [bank_ctx.short_name, bank_ctx.full_name]
    for a in (bank_ctx.config.get("aliases") or []):
        if a:
            hints.append(str(a))
    sc = bank_ctx.config.get("stock_code_a")
    if sc:
        hints.append(str(sc))
    for h in hints:
        hh = str(h).lower()
        if hh and len(hh) >= 2 and hh in src:
            return True
    return False


def load_logo_base64(bank_ctx: Optional["BankContext"] = None) -> str:
    """加载 LOGO base64。

    优先级（2026-04-29 修复视觉污染回归）：
        1. 基准行专属资产 `report_assets/by_bank/<bank>/logo/logo_base64.txt`
        2. 仅当 legacy 全局 LOGO 通过「身份 + 色相」双重校验与该基准行匹配时，
           才回退到 `report_assets/logo/logo_base64.txt`
        3. 返回空字符串 —— base_template.html 会自动降级为"官方名称大字标题"
           （颜色由 palette.primary 驱动，仍是该行官方色系）

    之前的 v1 实现会无条件回退到 legacy 全局 LOGO，导致"光大基准却显示中信 LOGO"
    的污染；本 v2 加入身份 + 色相双重校验。
    """
    if bank_ctx is not None:
        p = bank_ctx.logo_base64_txt
        if p.exists():
            txt = p.read_text().strip()
            if txt:
                return txt
        # 不匹配当前基准行的 legacy LOGO 绝对不用
        if not _legacy_logo_belongs_to(bank_ctx):
            return ""
    if LOGO_BASE64.exists():
        return LOGO_BASE64.read_text().strip()
    return ""


def load_palette(bank_ctx: Optional["BankContext"] = None) -> dict:
    """加载配色。

    优先级：
        1. 基准行专属 `report_assets/by_bank/<bank>/vis/palette.json`
        2. 旧版全局 `report_assets/vis/palette.json`
        3. 基准行 `brand_identity` 合成的 fallback palette（保证主色/辅色反映该行）
        4. 空 dict
    """
    if bank_ctx is not None:
        p = bank_ctx.palette_json
        if p.exists():
            try:
                with open(p) as f:
                    return json.load(f)
            except Exception:
                pass
    if PALETTE_JSON.exists():
        try:
            with open(PALETTE_JSON) as f:
                data = json.load(f)
            # 如果调用方指定了 base_bank 且 legacy palette 的 primary 与该行
            # brand_identity.primary_official 不匹配，则改用 fallback，避免
            # "光大基准但套用中信红" 这种跨行污染。
            if bank_ctx is not None:
                legacy_primary = (data.get("primary") or "").upper()
                expected = (bank_ctx.primary_color or "").upper()
                if expected and legacy_primary and legacy_primary != expected:
                    return bank_ctx.fallback_palette()
            return data
        except Exception:
            pass
    if bank_ctx is not None:
        return bank_ctx.fallback_palette()
    return {}


def load_css(path: Path) -> str:
    """加载 CSS 文件内容。"""
    if path.exists():
        return path.read_text()
    return ""


def _normalize_skill3_ctx(ctx: dict) -> dict:
    """
    兼容 Skill 3 的简化 `insight_result.json` schema。

    当前 Skill 3 的主输出经常只有：
    - executive_summary
    - insights
    - high_frequency_analysis
    - org_structure_changes

    但 PDF 模板需要更完整的 `meta / toc_items / org_primary / ...` 字段。
    这里补一层向后兼容，避免目录空白、字段名不匹配、银行差异化表述大面积空值。
    """
    bank_order = ["中信", "招商", "兴业", "平安", "浦发", "光大", "民生"]
    normalized = dict(ctx)

    insights = list(normalized.get("insights") or [])
    freq = dict(normalized.get("high_frequency_analysis") or {})
    freq_banks = dict(freq.get("banks") or {})
    org_changes = dict(normalized.get("org_structure_changes") or {})
    org_banks = dict(org_changes.get("banks") or {})

    meta = dict(normalized.get("meta") or {})
    base_bank_short = str(meta.get("base_bank_short") or meta.get("base_bank") or "").removesuffix("银行")
    if not base_bank_short:
        raise ValueError("meta 中未指定 base_bank / base_bank_short。请在调用 build_report 前由用户指定基准银行。")
    base_bank_full = str(meta.get("base_bank_full") or f"{base_bank_short}银行")
    meta.setdefault("base_bank_short", base_bank_short)
    meta.setdefault("base_bank_full", base_bank_full)
    meta.setdefault("title", "同业战略洞察报告")
    meta.setdefault(
        "subtitle",
        "基于 7 家股份制银行零售业务文本、组织架构与经营数据的综合洞察",
    )
    meta.setdefault("kicker", "")  # 默认不显示 SKILL X 标识；业务 Skill 可主动覆盖
    meta.setdefault("base_bank", base_bank_short)
    meta.setdefault(
        "cover_meta",
        [
            {"label": "基准行", "value": base_bank_full},
            {"label": "对标范围", "value": "7 家股份制银行"},
            {"label": "生成日期", "value": datetime.now().strftime("%Y年%m月%d日")},
        ],
    )
    normalized["meta"] = meta

    if not normalized.get("toc_items"):
        normalized["toc_items"] = [
            ("01", "执行摘要", ""),
            ("02", "行业全景", ""),
            ("03", f"{len(insights) or 0} 条核心洞察", ""),
            ("04", f"{base_bank_short} vs 同业战略雷达", ""),
            ("05", f"给管理层的 {len(insights) or 0} 条建议", ""),
            ("06", "附录", ""),
        ]

    if not normalized.get("industry_common_trends"):
        cross_bank = list(freq.get("cross_bank_trends") or [])
        normalized["industry_common_trends"] = (
            "、".join(cross_bank)
            if cross_bank
            else "未提取到稳定的行业共同高频词，建议结合各行零售章节原文复核。"
        )

    bank_specific = dict(freq.get("bank_specific") or {})
    for bank in bank_order:
        if bank_specific.get(bank):
            continue
        bank_profile = dict(freq_banks.get(bank) or {})
        retail_focus = list(bank_profile.get("retail_focus") or [])
        top_words = [
            item.get("word")
            for item in list(bank_profile.get("top_words") or [])
            if isinstance(item, dict) and item.get("word")
        ]
        words = retail_focus[:5] or top_words[:5]
        if words:
            bank_specific[bank] = words
        else:
            bank_specific[bank] = ["未提取到显著差异词，当前表述与行业共性重合"]
    freq["bank_specific"] = bank_specific
    normalized["high_frequency_analysis"] = freq

    normalized.setdefault("cross_period_comparison", {})

    org_primary = dict(normalized.get("org_primary") or {})
    base_org = dict(org_banks.get(base_bank_short) or {})
    org_primary.setdefault("current_departments", [])
    if not org_primary["current_departments"]:
        retail_org = base_org.get("retail_org_structure")
        if retail_org:
            org_primary["current_departments"] = [retail_org]
        else:
            org_primary["current_departments"] = ["未获取到组织架构信息"]
    org_primary.setdefault("change_frequency", "未提取到变化频次")
    org_primary.setdefault("latest_changes", "未提取到最新动作")
    normalized.setdefault("org_primary_bank", base_bank_full)
    normalized["org_primary"] = org_primary

    if not normalized.get("org_other_banks"):
        industry_trends = list(org_changes.get("industry_trends") or [])
        normalized["org_other_banks"] = (
            "；".join(industry_trends)
            if industry_trends
            else "未提取到同业组织架构变化。"
        )

    normalized.setdefault(
        "strategic_execution_done_not_said",
        [
            "未结构化提取到稳定的“做了没说”事项，建议回看 partial/insight_stratreview.json。",
        ],
    )
    normalized.setdefault(
        "strategic_execution_said_not_done",
        [
            "未结构化提取到稳定的“说了没做到”事项，建议回看 partial/insight_stratreview.json。",
        ],
    )

    normalized_insights = []
    for idx, ins in enumerate(insights, start=1):
        item = dict(ins)
        priority_type = item.get("priority_type") or "效率提升"
        priority_class = item.get("priority_class")
        if not priority_class:
            priority_class = {
                "增长机会": "growth",
                "风险预警": "risk",
                "效率提升": "efficiency",
            }.get(priority_type, "efficiency")
        item.setdefault("id", idx)
        item.setdefault("priority_type", priority_type)
        item.setdefault("priority_class", priority_class)
        item.setdefault("business_implication", item.get("business_meaning", ""))
        item.setdefault("action_recommendation", item.get("action_suggestion", ""))
        item.setdefault("risk_warning", item.get("risk_note", ""))
        item.setdefault("source_label", item.get("source", ""))
        normalized_insights.append(item)
    normalized["insights"] = normalized_insights
    normalized["insight_count"] = len(normalized_insights)

    return normalized


def normalize_ctx(ctx: dict, template_path: str) -> dict:
    """按业务模板对上下文做轻量兼容补齐。"""
    template_hint = str(template_path)
    if (
        "strategic-insight" in template_hint
        or (
            "executive_summary" in ctx
            and "high_frequency_analysis" in ctx
            and "org_structure_changes" in ctx
        )
    ):
        return _normalize_skill3_ctx(ctx)
    return ctx


def render_html(
    ctx: dict,
    template_path: str,
    output_html: str,
    *,
    style_overrides_path: Optional[str] = None,
    bank_ctx: Optional["BankContext"] = None,
) -> str:
    """
    使用 Jinja2 渲染 HTML。

    参数:
        ctx: 数据上下文
        template_path: 业务模板路径（继承 base_template）
        output_html: 输出 HTML 路径
        style_overrides_path: 可选的业务覆盖 CSS 路径
        bank_ctx: 可选的基准行上下文；若提供则优先使用该行的 logo 和 palette
    """
    ensure_dirs()
    ctx = normalize_ctx(ctx, template_path)

    # 准备全局数据
    logo_b64 = load_logo_base64(bank_ctx)
    palette = load_palette(bank_ctx)
    base_css = load_css(STYLE_GUIDE_CSS)
    override_css = load_css(Path(style_overrides_path)) if style_overrides_path else ""

    # Jinja2 环境：从业务模板所在目录加载
    template_dir = Path(template_path).parent
    env = Environment(
        loader=FileSystemLoader([str(template_dir), str(RUNTIME_ASSETS_DIR)]),
        autoescape=select_autoescape(["html", "xml"]),
    )
    # 注册 rich_text 白名单过滤器：放行受控的 inline 富文本标签
    env.filters["rich_text"] = _rich_text_filter

    # 业务模板名
    template_name = Path(template_path).name

    # 渲染
    template = env.get_template(template_name)
    html_content = template.render(
        ctx=ctx,
        logo_base64=logo_b64,
        palette=palette,
        base_css=base_css,
        override_css=override_css,
        meta=ctx.get("meta", {}),
        toc_items=ctx.get("toc_items", []),
    )

    # ------------------------------------------------------------------
    # 渲染完整性守卫（post-mortem 20260429）
    # ------------------------------------------------------------------
    # 历史故障：某次运行把业务模板源码直接拼接到正文内，导致 PDF 出现大量
    # 裸 Jinja2 标签 (`{{ ctx.xxx }}`、`{% for ... %}`)。为杜绝此类回归，
    # 在写盘前扫描渲染后的 HTML：若仍含未渲染占位符则立即 raise，不产出 PDF。
    residuals = _detect_jinja_residuals(html_content)
    if residuals:
        sample = "\n".join(f"  L{lineno}: {text}" for lineno, text in residuals[:5])
        raise RuntimeError(
            "模板渲染完整性校验失败：HTML 中仍含未渲染的 Jinja2 占位符。\n"
            f"共检测到 {len(residuals)} 处残留，前 5 处示例：\n{sample}\n\n"
            "常见原因：\n"
            "  1) ctx 字段名与业务模板不匹配（如模板用 ctx.kpi_cards 但 ctx 里是 kpi_cards）；\n"
            "  2) 业务模板把 base_template 的内容拼接在 {% extends %} 之外；\n"
            "  3) 使用字符串拼接写 HTML 而未走 env.get_template().render()。\n"
            "请先修复再重新生成 PDF。"
        )

    # 写入
    out_path = Path(output_html).expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_content, encoding="utf-8")

    return str(out_path)


_JINJA_PATTERN = re.compile(r"(\{\{(?!\s*#).*?\}\}|\{%(?!\s*#).*?%\})", re.DOTALL)


# -----------------------------------------------------------------------------
# rich_text 白名单过滤器（2026-04-29 新增）
# -----------------------------------------------------------------------------
# 背景：skill3/4/5 的 ctx 字段里（如 executive_summary、insight.* 等自然语言
# 字符串）业务侧习惯使用 <b>…</b> / <strong>…</strong> / <br> 做关键词高亮。
# 但 Jinja2 环境 autoescape=True 会把它们转义为 &lt;b&gt;，PDF 里就出现大量
# 字面的 "<b>核心判断</b>"。
#
# 本过滤器实现"受控放行"：
#   - 默认 HTML 转义整段文本（安全）
#   - 仅对白名单里的 inline 标签（b/strong/em/i/u/br/sub/sup/code）重新解转义
#   - 其他标签（script/style/iframe/img/a 等）保持转义，杜绝注入风险
#
# 业务模板使用约定：对"可能含 <b> 的自然语言字段"写 `{{ field | rich_text }}`；
# 对完整的 HTML 片段（如 resilience_radar_html）继续使用 `| safe`。
# -----------------------------------------------------------------------------

_RICH_TEXT_WHITELIST = ("b", "strong", "em", "i", "u", "br", "sub", "sup", "code")
_RICH_TEXT_PATTERN = re.compile(
    r"&lt;(/?)(" + "|".join(_RICH_TEXT_WHITELIST) + r")\s*/?&gt;",
    flags=re.IGNORECASE,
)


def _rich_text_filter(value):
    """
    渲染自然语言文本中的受控 inline 富文本标签。

    用法::

        {{ ctx.insight.description | rich_text }}

    当 value 为 None 时返回空 Markup。对非字符串输入先做 str() 转换。
    """
    if value is None:
        return Markup("")
    if not isinstance(value, str):
        value = str(value)
    # 先全部 HTML 转义
    escaped = str(_html_escape(value))
    # 再把白名单标签解转义
    rendered = _RICH_TEXT_PATTERN.sub(lambda m: f"<{m.group(1)}{m.group(2).lower()}>", escaped)
    return Markup(rendered)


def _detect_jinja_residuals(html: str) -> list[tuple[int, str]]:
    """
    检测 HTML 中是否仍含未渲染的 Jinja2 占位符，返回 [(lineno, snippet), ...]。
    只检测 {{ ... }} 与 {% ... %}（不含纯注释 {# #}）。
    """
    residuals: list[tuple[int, str]] = []
    for m in _JINJA_PATTERN.finditer(html):
        # 跳过明显无害的：CSS 变量里嵌入的 var(--x)、data URI 中的 base64 花括号
        snippet = m.group(0)
        if len(snippet) > 200:
            snippet = snippet[:200] + "..."
        lineno = html.count("\n", 0, m.start()) + 1
        residuals.append((lineno, snippet))
    return residuals


def render_pdf(
    html_path: str,
    output_pdf: str,
    *,
    margin_top: str = "22mm",
    margin_bottom: str = "15mm",
    cover_height: str = "297mm",
    header_text: str = "",
    footer_text: str = "本报告仅作研究参考，不构成任何投资建议",
    bank_ctx: Optional["BankContext"] = None,
) -> str:
    """
    使用 Playwright 分两次导出 PDF + pypdf 合并。

    参数:
        html_path: 输入 HTML 路径
        output_pdf: 输出 PDF 路径
        margin_top: 正文页顶部 margin（默认 22mm）
        margin_bottom: 正文页底部 margin（默认 15mm）
        cover_height: 封面高度（skill3=296mm, skill4/5=297mm）
        header_text: 页眉中间文字
        footer_text: 页脚左侧文字
        bank_ctx: 可选基准行上下文，用于选取页眉 logo
    """
    from playwright.sync_api import sync_playwright

    html_path = Path(html_path).expanduser().resolve()
    output_pdf = Path(output_pdf).expanduser()
    output_pdf.parent.mkdir(parents=True, exist_ok=True)

    # 临时文件
    tmp_cover = output_pdf.parent / f"_tmp_{output_pdf.stem}_cover.pdf"
    tmp_body = output_pdf.parent / f"_tmp_{output_pdf.stem}_body.pdf"

    # 兜底：若调用方忘了传 bank_ctx，尝试从 output_pdf 路径中推断基准行短名
    # （典型结构 ~/RetailAnalysis/output/<bank_short>/xxx.pdf）。这可以避免
    # 「页眉走到 legacy 全局 LOGO（常为中信）」的回归问题。
    if bank_ctx is None:
        try:
            from bank_context import resolve as _resolve_bank, _SHORT_MAP  # type: ignore
            parts = output_pdf.resolve().parts
            inferred: Optional[str] = None
            for p in reversed(parts):
                if p in _SHORT_MAP:
                    inferred = p
                    break
            if inferred:
                bank_ctx = _resolve_bank(base_bank=inferred)
                print(
                    f"[render_pdf] bank_ctx=None → 从 output_pdf 路径推断基准行为『{inferred}』，"
                    f"页眉将使用 by_bank/{inferred}/logo。"
                    "建议业务脚本显式传入 bank_ctx 以避免歧义。",
                    file=sys.stderr,
                )
        except Exception:
            pass

    # LOGO base64 用于页眉
    logo_b64 = load_logo_base64(bank_ctx)

    # 页眉模板（内联样式）
    header_template = f"""
    <div style="width:100%; display:flex; align-items:center; justify-content:space-between; padding:0 15mm; border-bottom:1pt solid #E0E0E0; padding-bottom:4mm; font-family:'PingFang SC','Noto Sans SC','Microsoft YaHei',sans-serif;">
        <img src="data:image/png;base64,{logo_b64}" style="width:52px; height:16px; object-fit:fill; display:block;" alt="logo">
        <div style="font-size:9pt; color:#555555; letter-spacing:0.5pt;">{header_text}</div>
        <div style="font-size:8.5pt; color:#555555;">第 <span class="pageNumber"></span> / <span class="totalPages"></span> 页</div>
    </div>
    """

    # 页脚模板
    footer_template = f"""
    <div style="width:100%; display:flex; justify-content:space-between; padding:0 15mm; border-top:1pt solid #E0E0E0; padding-top:3mm; font-family:'PingFang SC','Noto Sans SC','Microsoft YaHei',sans-serif; font-size:8pt; color:#555555;">
        <span>{footer_text}</span>
        <span>{header_text}</span>
    </div>
    """

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(f"file://{html_path}")
        page.wait_for_load_state("networkidle")
        page.add_style_tag(
            content=(
                ".cover{"
                f"height:{cover_height}!important;"
                f"min-height:{cover_height}!important;"
                f"max-height:{cover_height}!important;"
                "}"
            )
        )

        # 第 1 次：封面（第 1 页，margin=0，无页眉页脚）
        page.pdf(
            path=str(tmp_cover),
            page_ranges="1",
            format="A4",
            margin={"top": "0mm", "right": "0mm", "bottom": "0mm", "left": "0mm"},
            display_header_footer=False,
            print_background=True,
        )

        # 第 2 次：正文（第 2 页起，有页眉页脚）
        # 关键修复：
        # - 仅靠 CSS 折叠封面，Chromium 仍可能把封面文本残留到正文导出里，
        #   造成“封面跨页 / 目录后移”。
        # - 这里直接把 DOM 中的 `.cover` 替换成一个纯空白的 A4 占位页，
        #   彻底移除封面文字，只保留正文从第 2 页开始的分页语义。
        page.evaluate(
            """() => {
                const cover = document.querySelector('.cover');
                if (!cover) return;
                const placeholder = document.createElement('div');
                placeholder.className = 'cover-placeholder';
                placeholder.setAttribute(
                    'style',
                    [
                        'height:1px',
                        'min-height:1px',
                        'max-height:1px',
                        'margin:0',
                        'padding:0',
                        'overflow:hidden',
                        'background:transparent',
                        'page-break-after:always',
                        'break-after:page',
                    ].join(';')
                );
                cover.replaceWith(placeholder);
            }""",
        )

        # 解析 margin
        def parse_mm(s: str) -> str:
            return s if s.endswith("mm") else f"{s}mm"

        page.pdf(
            path=str(tmp_body),
            page_ranges="2-",
            format="A4",
            margin={
                "top": parse_mm(margin_top),
                "right": "0mm",
                "bottom": parse_mm(margin_bottom),
                "left": "0mm",
            },
            display_header_footer=True,
            header_template=header_template,
            footer_template=footer_template,
            print_background=True,
        )

        browser.close()

    # 合并（pypdf 3.x 兼容）
    from pypdf import PdfReader, PdfWriter
    
    writer = PdfWriter()
    
    # 追加封面
    reader_cover = PdfReader(str(tmp_cover))
    for page in reader_cover.pages:
        writer.add_page(page)
    
    # 追加正文
    reader_body = PdfReader(str(tmp_body))
    for page in reader_body.pages:
        writer.add_page(page)
    
    # 写入
    with open(output_pdf, "wb") as f:
        writer.write(f)

    # 清理临时文件
    tmp_cover.unlink(missing_ok=True)
    tmp_body.unlink(missing_ok=True)

    return str(output_pdf)


def _infer_base_bank_from_ctx(ctx: dict) -> Optional[str]:
    """从业务上下文读取客户名称，兼容 Skill 3/4/5 的常用字段。"""
    if not isinstance(ctx, dict):
        return None
    meta = ctx.get("meta") if isinstance(ctx.get("meta"), dict) else {}
    for value in (
        meta.get("base_bank_short"),
        meta.get("base_bank"),
        ctx.get("base_bank_short"),
        ctx.get("base_bank"),
        ctx.get("bank_key"),
        ctx.get("bank"),
    ):
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _customer_scoped_report_path(raw_path: str, bank_ctx: "BankContext") -> Path:
    """保证 OUTPUT_DIR 内报告统一落到 ``<bank_short>/``，外部显式路径保持不变。"""
    path = Path(raw_path).expanduser()
    resolved = path.resolve()
    output_root = Path(OUTPUT_DIR).expanduser().resolve()
    expected_dir = bank_ctx.output_dir.resolve()
    try:
        resolved.relative_to(output_root)
    except ValueError:
        return path

    if resolved.parent != expected_dir:
        scoped = expected_dir / resolved.name
        sys.stderr.write(
            f"[共享 PDF Runtime] 已将客户『{bank_ctx.short_name}』报告从 {resolved} "
            f"规范到 {scoped}\n"
        )
        return scoped
    return path


def build_report(
    ctx: dict,
    template_path: str,
    output_html: str,
    output_pdf: str,
    *,
    style_overrides_path: Optional[str] = None,
    margin_top: str = "22mm",
    margin_bottom: str = "15mm",
    cover_height: str = "297mm",
    header_text: str = "",
    footer_text: str = "本报告仅作研究参考，不构成任何投资建议",
    base_bank: Optional[str] = None,
    bank_ctx: Optional["BankContext"] = None,
    runtime_acknowledged: bool = False,
) -> str:
    """
    完整流程：渲染 HTML → 生成 PDF。

    新增参数:
        base_bank: 基准行短名（如 "光大"），用于自动选取 per-bank LOGO / palette。
                   若同时指定 bank_ctx，以 bank_ctx 为准。
        bank_ctx:  已构造好的 BankContext，优先级最高。
        runtime_acknowledged: 软门禁。Agent/业务脚本调用前应先 `read_file` RUNTIME.md
                   并在调用时传入 True，表示已阅读并遵守规范。传 False 时本函数会打印
                   详细 warning（指向 RUNTIME.md 的路径），但不会 raise，以保持
                   向后兼容。

    当 base_bank 或 bank_ctx 任一提供时：
        - LOGO / palette 从 ``report_assets/by_bank/<bank>/`` 读取
        - 若该行 per-bank 资产不存在，自动降级为 ``banks.yaml`` 中的品牌色合成
          fallback palette（保证主色反映基准行），LOGO 则继续尝试 legacy 全局目录

    返回生成的 PDF 路径。
    """
    if not runtime_acknowledged:
        # 定位 RUNTIME.md 路径（vendored 态 or 源码态）
        candidates = []
        runtime_md = Path(__file__).resolve().parent.parent / "RUNTIME.md"
        candidates.append(runtime_md)
        msg = (
            "\n"
            "============================================================\n"
            "[共享 PDF Runtime · WARNING] runtime_acknowledged=False\n"
            "------------------------------------------------------------\n"
            "你正在调用 build_report() 但未确认已阅读 RUNTIME.md。\n"
            "RUNTIME.md 是 skill3/4/5 生成 PDF 的权威规约，包含：\n"
            "  - 模板渲染完整性守卫（杜绝 Jinja 残留）\n"
            "  - rich_text 过滤器使用约定\n"
            "  - 按行基准解析与按行视觉资产隔离\n"
            "  - 自动下载 + 多级质量核验\n"
            "  - P0 VIS 资产验收 / 5 项 PDF 校验\n"
            "请执行：\n"
            f"  read_file {runtime_md}\n"
            "确认后再次调用时传入 runtime_acknowledged=True。\n"
            "本次调用将继续执行（向后兼容），但再次发现 F 级资产时不负责结果。\n"
            "============================================================\n"
        )
        try:
            sys.stderr.write(msg)
        except Exception:
            print(msg)

    # 统一解析客户上下文：显式参数优先，其次报告 meta，最后由 banks.yaml 默认值兜底。
    if bank_ctx is None and resolve_bank is not None:
        bank_ctx = resolve_bank(base_bank=base_bank or _infer_base_bank_from_ctx(ctx))
    if bank_ctx is None:
        raise RuntimeError("无法解析报告客户；请传入 base_bank 或 bank_ctx")

    # OUTPUT_DIR 内的 HTML/PDF 强制按客户简称隔离，避免多个客户互相覆盖。
    output_html = str(_customer_scoped_report_path(output_html, bank_ctx))
    output_pdf = str(_customer_scoped_report_path(output_pdf, bank_ctx))

    # 资产质量闸门（软门禁）：若存在 quality_report.yaml 且 grade=F，打印警告
    if bank_ctx is not None:
        qr = bank_ctx.assets_dir / "quality_report.yaml"
        if qr.exists():
            try:
                import yaml as _yaml  # type: ignore
                _data = _yaml.safe_load(qr.read_text(encoding="utf-8")) or {}
                grade = _data.get("grade")
                if grade == "F":
                    try:
                        from bank_context import portable_path as _pp  # type: ignore
                        _qr_str = _pp(qr)
                    except Exception:
                        _qr_str = str(qr)
                    sys.stderr.write(
                        f"[共享 PDF Runtime · WARNING] {bank_ctx.short_name} 视觉资产 "
                        f"grade=F（critical 问题未修复）。详见 {_qr_str}。\n"
                        f"建议先运行：python _vendor/pdf_report_builder_runtime/scripts/"
                        f"build_by_bank_vis.py --bank {bank_ctx.short_name} --auto-download\n"
                    )
            except Exception:
                pass

    html_path = render_html(
        ctx=ctx,
        template_path=template_path,
        output_html=output_html,
        style_overrides_path=style_overrides_path,
        bank_ctx=bank_ctx,
    )
    pdf_path = render_pdf(
        html_path=html_path,
        output_pdf=output_pdf,
        margin_top=margin_top,
        margin_bottom=margin_bottom,
        cover_height=cover_height,
        header_text=header_text,
        footer_text=footer_text,
        bank_ctx=bank_ctx,
    )
    return pdf_path


def main() -> int:
    parser = argparse.ArgumentParser(description="PDF 渲染引擎")
    parser.add_argument("--ctx", required=True, help="数据上下文 JSON 文件路径")
    parser.add_argument("--template", required=True, help="业务模板路径")
    parser.add_argument("--output-html", required=True, help="输出 HTML 路径")
    parser.add_argument("--output-pdf", required=True, help="输出 PDF 路径")
    parser.add_argument("--overrides", help="业务覆盖 CSS 路径")
    parser.add_argument("--margin-top", default="22mm", help="正文顶部 margin")
    parser.add_argument("--margin-bottom", default="15mm", help="正文底部 margin")
    parser.add_argument("--header-text", default="", help="页眉文字")
    parser.add_argument("--footer-text", default="本报告仅作研究参考，不构成任何投资建议", help="页脚文字")
    parser.add_argument("--base-bank", default=None,
                        help="基准行短名（如 光大 / 中信 / 招商），用于选取 per-bank 视觉资产")
    parser.add_argument("--runtime-acknowledged", action="store_true",
                        help="传入此 flag 表示调用方已阅读 RUNTIME.md（去掉 warning）")
    args = parser.parse_args()

    with open(args.ctx) as f:
        ctx = json.load(f)

    pdf_path = build_report(
        ctx=ctx,
        template_path=args.template,
        output_html=args.output_html,
        output_pdf=args.output_pdf,
        style_overrides_path=args.overrides,
        margin_top=args.margin_top,
        margin_bottom=args.margin_bottom,
        header_text=args.header_text,
        footer_text=args.footer_text,
        base_bank=args.base_bank,
        runtime_acknowledged=args.runtime_acknowledged,
    )
    print(f"PDF 已生成: {pdf_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
