#!/usr/bin/env python3
"""产品情报报告 — 模板注入引擎。

用法:
    python generate_report.py <clean_data.json> [output.html] [--site amazon|shein]

接受 AI 预处理后的标准化数据 JSON，注入对应站点模板输出静态 HTML 报告。
本脚本不做任何数据解析或转换——所有字段清洗、分类、翻译由 AI 在上游完成。

标准数据格式见下方 CLEAN_DATA_SCHEMA。
"""

import json
import sys
import os
from html import escape

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PARENT = os.path.dirname(SCRIPT_DIR)
TPL_DIR = os.path.join(_PARENT, "templates")

# 向后兼容：脚本同目录下的 template.html 仍优先
_TEMPLATE_CANDIDATE = os.path.join(SCRIPT_DIR, "template.html")
if os.path.isfile(_TEMPLATE_CANDIDATE):
    TEMPLATE_PATH = _TEMPLATE_CANDIDATE
else:
    TEMPLATE_PATH = os.path.join(TPL_DIR, "report.html")

# ── 品牌色定义 ──
BRAND = {
    "amazon": {
        "ACCENT": "#4f46e5",
        "ACCENT_LIGHT": "#eef2ff",
        "ACCENT_LIGHT_BG": "#fafaff",
        "HEADER_GRADIENT": "linear-gradient(135deg, #4f46e5 0%, #7c3aed 50%, #6366f1 100%)",
        "CHART_1": "#4f46e5", "CHART_2": "#06b6d4", "CHART_3": "#8b5cf6",
        "CHART_COLORS_JS": "'#4f46e5','#06b6d4','#8b5cf6'",
    },
    "shein": {
        "ACCENT": "#4f46e5",
        "ACCENT_LIGHT": "#eef2ff",
        "ACCENT_LIGHT_BG": "#fafaff",
        "HEADER_GRADIENT": "linear-gradient(135deg, #4f46e5 0%, #7c3aed 50%, #6366f1 100%)",
        "CHART_1": "#4f46e5", "CHART_2": "#06b6d4", "CHART_3": "#8b5cf6",
        "CHART_COLORS_JS": "'#4f46e5','#06b6d4','#8b5cf6'",
    },
}

# ── 平台专属 CSS ──
PLATFORM_CSS_FILE = {
    "amazon": "_amazon.css",
    "shein": "_shein.css",
}

def _read(filename):
    """读 templates/ 下的文件，不存在返回空字符串"""
    p = os.path.join(TPL_DIR, filename)
    if os.path.isfile(p):
        with open(p, "r", encoding="utf-8") as f:
            return f.read()
    return ""

def _inject_brand(css: str, site: str) -> str:
    """替换 CSS 中的品牌色占位符"""
    b = BRAND.get(site, BRAND["amazon"])
    for key, val in b.items():
        css = css.replace("{{%s}}" % key, val)
    return css

# ──────────────────────────────────────────────
# CLEAN_DATA_SCHEMA (JSON)
# ──────────────────────────────────────────────
# {
#   "meta": {
#     "title":      "产品短标题（用于 <title> 和 report-header h1）",
#     "subtitle":   "副标题（规格摘要）",
#     "tagline":    "ASIN / 日期 / 站点 等元信息",
#     "date":       "采集日期"
#   },
#   "kpi": [
#     {"value": "$7.59", "label": "当前售价", "sub": "24% off"},
#     {"value": "", "type": "rating", "label": "4.4 / 5 · 2099 条评价", "sub": "好评率 84%（4-5星）"},
#     {"value": "1K+", "label": "月销量", "sub": "BSR #97"},
#     {"value": "<span style=\"color:#059669;\">有货</span>", "label": "库存状态", "sub": "#6 子类"}
#   ],
#   // type="rating" 时 value 必须为 "" ，星级由脚本根据 rating.score 自动生成（含半星）
#   "overview": {
#     "main_image": "URL",
#     "description":"产品概述文字（1-2 句）",
#     "info":       "品牌 · 型号 · 颜色 等",
#     "badges":     ["Badge1", "Badge2"] 或 null
#   },
#   "bullets": [
#     {"en": "原始文本", "zh": "中文翻译"}
#   ],
#   "price_variants": {
#     "current":    "$7.59",
#     "list":       "$9.99",
#     "savings":    "24% off",
#     "badge":      "Limited time deal" 或 null,
#     "dimensions": [
#       {"name":"Color","current":"Black","options":["Black","Nude",...],
#        "thumbnails":["url",...]},     // 有缩略图→圆形色块
#       {"name":"Size","current":"M","options":["XS","S","M",...],
#        "thumbnails":[]}              // 无缩略图→文字Pill
#     ],
#     // 🔴 规则: 每个变体类型必须是独立的 dimension，禁止合并。反例: ["Black","XS","S","M"] 合并到一个 dimension
#     //    每个 dimension 渲染为独立的一行（h4 + pills），不同类型天然分开展示
#     // 任意品类通用: 手机壳→1个Color维度, 食品→Flavor+Size, 内存卡→Capacity only
#     "note":       "补充说明" 或 null
#   },
#   "rating": {
#     "score":      4.4,
#     "count":      2099,
#     "good_rate":  84,
#     "histogram":  {"5": 71, "4": 13, "3": 8, "2": 3, "1": 5},
#     "aspects":    [{"name": "Fit", "count": 228}, ...] 或 null,
#     "ai_summary": "Customers say..." 或 null,
#     "note":       "样本量警告" 或 null
#   },
#   "delivery": {
#     "type":    "FBA 免邮",
#     "details": ["标准配送: ...", "Prime 配送: ..."],
#     "note":    "" 或 null
#   },
#   "images": ["url1", "url2", ...],
#   "videos": ["m3u8_url1", ...] 或 null,
#   "aplus":  ["url1", ...] 或 null,
#   "specs": [
#     {"name": "规格名称", "value": "规格值"}
#   ]
# }

# ──────────────────────────────────────────────
# HTML snippet helpers
# ──────────────────────────────────────────────

def _esc(s) -> str:
    return escape(str(s)) if s else ""

def _esc_url(s) -> str:
    return escape(str(s), quote=True) if s else ""

def _ds(date: str) -> str:
    return '<div class="data-source"><span class="ds-tool">linkfox-plugin-web-data-crawler</span> · {}</div>'.format(_esc(date))


# ──────────────────────────────────────────────
# Section builders (data in, HTML out)
# ──────────────────────────────────────────────

def _stars_html(score: float) -> str:
    """4.4 → ★★★★⯨（4 实心 + 1 半星）。≥0.3 算半星。"""
    html = '<span style="font-size:16px;vertical-align:middle;display:inline-flex;gap:1px;">'
    for i in range(1, 6):
        if score >= i:
            html += '<span style="color:#f59e0b;">★</span>'
        elif score >= i - 0.7:  # 半星: 如 4.4 → 第5颗半星
            pct = int((score - (i - 1)) * 100)
            html += '<span style="position:relative;display:inline-block;width:1em;height:1em;">'
            html += '<span style="color:#d1d5db;position:absolute;left:0;">★</span>'
            html += '<span style="color:#f59e0b;position:absolute;left:0;overflow:hidden;width:{}%;">★</span>'.format(pct)
            html += '</span>'
        else:
            html += '<span style="color:#d1d5db;">★</span>'
    html += "</span>"
    return html


def build_kpi(kpi_list: list, rating_score: float = 0) -> str:
    if not kpi_list:
        return ""
    cards = ""
    for item in kpi_list:
        sub = '<div class="kpi-sub">{}</div>'.format(_esc(item.get("sub", ""))) if item.get("sub") else ""
        val = item.get("value", "")
        # 如果 kpi type 是 rating，按 score 自动生成星级 HTML
        if item.get("type") == "rating" and rating_score > 0:
            val = _stars_html(rating_score)
        # Detect if value contains HTML
        val_cls = ' class="kpi-value"' if "<" not in val else ' class="kpi-value" style="letter-spacing:2px;"'
        cards += '<div class="kpi-card"><div{}>{}</div><div class="kpi-label">{}</div>{}</div>'.format(
            val_cls, val, _esc(item.get("label", "")), sub)
    return '<div class="kpi-grid">{}</div>'.format(cards)


def build_overview(ov: dict, date: str) -> str:
    if not ov:
        return ""

    main_img = ""
    if ov.get("main_image"):
        main_img = '<div class="overview-image"><img src="{}" alt="产品主图" loading="eager"></div>'.format(
            _esc_url(ov["main_image"]))

    badges_html = ""
    if ov.get("badges"):
        badges_html = '<div style="margin-bottom:8px;">' + " ".join(
            '<span class="tag tag-accent">{}</span>'.format(_esc(b[:40])) for b in ov["badges"]
        ) + '</div>'

    return """<section class="content-section">
  <h2>📦 产品概览与卖点</h2>
  <div class="overview-layout">
    {}
    <div class="overview-text">
      <p>{}</p>
      {}
      <div class="summary-box">
        <h4>基本信息</h4>
        <p>{}</p>
      </div>
    </div>
  </div>
  {}
  {}
</section>""".format(
        main_img,
        _esc(ov.get("description", "")),
        badges_html,
        _esc(ov.get("info", "")),
        build_bullets(ov.get("bullets")),
        _ds(date))


def build_bullets(bullets: list) -> str:
    if not bullets:
        return ""
    rows = ""
    for b in bullets:
        rows += '<tr><td class="col-en">{}</td><td class="col-zh">{}</td></tr>\n'.format(
            _esc(b.get("en", "")), _esc(b.get("zh", "")))
    return """<h3>产品卖点</h3>
  <div class="data-table-wrapper">
    <table class="bullet-compare">
      <thead><tr><th class="col-en">原始文本</th><th class="col-zh">中文</th></tr></thead>
      <tbody>{}</tbody>
    </table>
  </div>""".format(rows)


def build_price(pv: dict, date: str) -> str:
    if not pv:
        return ""
    parts = ['<section class="content-section">', '  <h2>💰 价格与可购变体</h2>']

    pinfo = "售价 <strong>{}</strong>".format(_esc(pv.get("current", "")))
    if pv.get("list"):
        pinfo += "（标价: {}）".format(_esc(pv["list"]))
    if pv.get("savings"):
        pinfo += " · {}".format(_esc(pv["savings"]))
    if pv.get("badge"):
        pinfo += ' · <span class="tag tag-accent">{}</span>'.format(_esc(pv["badge"]))
    parts.append("  <p>{}</p>".format(pinfo))

    # ── 变体渲染：多维度自适应（品类无关）──
    dims = pv.get("dimensions", [])
    if dims:
        for dim in dims:
            name = dim.get("name", "选项")
            current_val = dim.get("current", "")
            options = dim.get("options", [])
            thumbs = dim.get("thumbnails", [])

            parts.append('  <h4>{}（{} 种）</h4>'.format(_esc(name), len(options)))
            parts.append('  <div class="variant-row" style="margin:4px 0 12px 0;">')
            for i, opt in enumerate(options):
                is_current = (str(opt) == str(current_val))
                cls = " current" if is_current else ""
                if thumbs and i < len(thumbs) and thumbs[i]:
                    # 圆形色块（Color/Pattern 类）
                    parts.append(
                        '    <span class="variant-pill{}" style="padding:3px;border-radius:50%;border:none;background:transparent;" title="{}">'
                        '<img src="{}" alt="{}" style="width:42px;height:42px;border-radius:50%;object-fit:cover;display:block;border:{}">'
                        '</span>'.format(
                            cls, _esc(opt),
                            _esc_url(thumbs[i]), _esc(opt),
                            "2px solid var(--color-accent)" if is_current else "1px solid var(--color-border)"))
                else:
                    # 文字 Pill（Size/Flavor/Count 类）
                    parts.append('    <span class="variant-pill{}">{}</span>'.format(cls, _esc(opt)))
            parts.append('  </div>')
        # 组合说明
        total_opts = " × ".join(
            "{} 种 {}".format(len(d.get("options", [])), d.get("name", "")) for d in dims)
        current_str = " / ".join(
            _esc(d.get("current", "") or d.get("options", [""])[0]) for d in dims)
        parts.append(
            '  <p style="font-size:12px;color:var(--color-text-muted);">{} · 当前: {}</p>'.format(
                total_opts, current_str))
    elif pv.get("variants_text"):
        # 兼容旧格式（单维度列表）
        vlist = pv["variants_text"]
        parts.append('  <p>共 <strong>{}</strong> 个可购变体：</p>'.format(len(vlist)))
        parts.append('  <div class="variant-row" style="margin:8px 0 12px 0;">')
        for i, v in enumerate(vlist):
            cls = " current" if i == 0 else ""
            parts.append('    <span class="variant-pill{}">{}</span>'.format(cls, _esc(v)))
        parts.append('  </div>')
    else:
        parts.append('  <p style="font-size:13px;color:var(--color-text-muted);">该产品无变体选项。</p>')

    if pv.get("note"):
        parts.append('  <p style="font-size:13px;color:var(--color-text-muted);">{}</p>'.format(_esc(pv["note"])))

    parts.append('  {}'.format(_ds(date)))
    parts.append('</section>')
    return "\n".join(parts)


def build_rating(rt: dict, date: str) -> str:
    if not rt:
        return ""
    parts = ['<section class="content-section">', '  <h2>⭐ 评分与口碑分析</h2>']
    score = rt.get("score", 0)
    count = rt.get("count", 0)
    good = rt.get("good_rate", 0)
    hist = rt.get("histogram") or {}

    if score > 0:
        parts.append('  <div class="rating-hero">')
        parts.append('    <div class="big-score">{}</div>'.format(score))
        parts.append('    <div>')
        parts.append('      <div class="stars">{}</div>'.format(_stars_html(score)))
        parts.append('      <div class="meta" style="margin-top:4px;">{} 条评价 · {}% 好评率</div>'.format(
            f"{count:,}", good))
        parts.append('    </div>')
        parts.append('  </div>')

        # chart + star bars (only when histogram data exists)
        if hist:
            parts.append('  <div class="chart-row cols-2">')
            parts.append('    <div class="chart-container"><canvas id="chart_donut" width="500" height="340"></canvas></div>')
            parts.append('    <div style="display:flex;flex-direction:column;justify-content:center;gap:10px;padding:0 20px;">')
            colors = {"5": "#10b981", "4": "#f59e0b", "3": "#06b6d4", "2": "#8b5cf6", "1": "#6b7280"}
            labels = {"5": "五星", "4": "四星", "3": "三星", "2": "二星", "1": "一星"}
            for star_num in ["5", "4", "3", "2", "1"]:
                pct = hist.get(star_num, 0)
                c = colors[star_num]
                est = round(pct / 100 * count) if count > 0 else 0
                parts.append('      <div style="display:flex;align-items:center;gap:12px;">')
                parts.append('        <span style="font-size:13px;color:{};font-weight:600;width:32px;">{}</span>'.format(c, labels[star_num]))
                parts.append('        <span style="flex:1;height:6px;background:#f3f4f6;border-radius:3px;overflow:hidden;"><span style="display:block;height:100%;width:{}%;background:{};border-radius:3px;"></span></span>'.format(pct, c))
                parts.append('        <span style="font-size:13px;font-weight:600;color:{};width:36px;text-align:right;">{}%</span>'.format(c, pct))
                parts.append('        <span style="font-size:11px;color:var(--color-text-muted);width:48px;text-align:right;">{}条</span>'.format(f"{est:,}"))
                parts.append('      </div>')
            parts.append('    </div>')
            parts.append('  </div>')
    else:
        parts.append('  <p style="color:var(--color-text-muted);">暂无评分数据。</p>')

    if rt.get("aspects"):
        tags = " ".join('<span class="tag tag-accent">{}({})</span>'.format(_esc(a["name"]), a["count"]) for a in rt["aspects"])
        parts.append('  <p style="margin-top:12px;">评价话题标签：{}</p>'.format(tags))

    if rt.get("ai_summary"):
        parts.append('  <div class="summary-box">')
        parts.append('    <h4>AI 评价摘要（Customers say）</h4>')
        parts.append('    <p>{}</p>'.format(_esc(rt["ai_summary"])))
        parts.append('  </div>')

    if rt.get("note"):
        parts.append('  <div class="insight-callout"><strong>🔍 注意：</strong>{}</div>'.format(_esc(rt["note"])))

    parts.append('  {}'.format(_ds(date)))
    parts.append('</section>')
    return "\n".join(parts)


def build_chart_js(rt: dict) -> str:
    if not rt or not rt.get("histogram"):
        return ""
    hist = rt["histogram"]
    labels = {"5": "五星", "4": "四星", "3": "三星", "2": "二星", "1": "一星"}
    colors = {"5": "#10b981", "4": "#f59e0b", "3": "#06b6d4", "2": "#8b5cf6", "1": "#6b7280"}
    items = []
    for sn in ["5", "4", "3", "2", "1"]:
        items.append('{{"label":"{}","value":{},"color":"{}"}}'.format(labels[sn], hist.get(sn, 0), colors[sn]))
    center = str(rt.get("score", 0))
    return '  drawDonut("chart_donut", [{}], "{}", "综合评分");'.format(", ".join(items), center)


# ──────────────────────────────────────────────
# SHEIN-specific builders
# ──────────────────────────────────────────────

def build_fit_distribution(fit: dict) -> str:
    """SHEIN 合身度分布条（Small / True to Size / Large）"""
    if not fit:
        return ""
    fit_order = ["Small", "True to Size", "Large"]
    fit_colors = {"Small": "#ef4444", "True to Size": "#10b981", "Large": "#f59e0b"}
    bars = ""
    for key in fit_order:
        pct = fit.get(key, 0)
        c = fit_colors.get(key, "#8e8ea0")
        bars += (
            '    <div class="fit-bar-item">'
            '<div class="fit-label">{}</div>'
            '<div class="fit-pct">{}%</div>'
            '<div class="fit-bar-track"><div class="fit-bar-fill" style="width:{}%;background:{};"></div></div>'
            '</div>\n'.format(_esc(key), pct, pct, c))
    return '<div class="fit-bars">\n{}</div>'.format(bars)


def build_reviews(reviews: list, date: str) -> str:
    """SHEIN 评论卡片列表"""
    if not reviews:
        return ""
    cards = ""
    for r in reviews:
        author = _esc(r.get("author", ""))
        rdate = _esc(r.get("date", ""))
        rating = r.get("rating", 0)
        body = _esc(r.get("body", ""))
        helpful = r.get("helpful", 0)
        rimages = r.get("images", [])

        stars = "★" * int(rating)
        if isinstance(rating, float):
            reminder = rating - int(rating)
            if reminder >= 0.3:
                stars += "☆"

        helpful_str = "{} 人认为有帮助".format(helpful) if helpful > 0 else ""

        imgs_html = ""
        if rimages:
            imgs_html = '<div class="review-card-images">'
            for url in rimages:
                full_url = url if url.startswith("http") else "https:" + url
                imgs_html += '<img src="{}" data-full="{}" alt="买家秀" loading="lazy">'.format(
                    _esc_url(full_url), _esc_url(full_url))
            imgs_html += '</div>'

        cards += (
            '<div class="review-card">'
            '<div class="review-card-header">'
            '<span class="review-card-author">{}</span>'
            '<span class="review-card-rating">{}</span>'
            '<span class="review-card-date">{}</span>'
            '</div>'
            '<div class="review-card-body">{}</div>'
            '{}'
            '<div class="review-card-footer">'
            '<span class="review-card-helpful">{}</span>'
            '</div>'
            '</div>\n'.format(author, stars, rdate, body, imgs_html, helpful_str)
        )

    return """<section class="content-section">
  <h2>💬 买家真实评价<span style="font-weight:400;font-size:13px;color:var(--color-text-muted);margin-left:8px;">{} 条采样</span></h2>
  {}
  {}
</section>""".format(len(reviews), cards, _ds(date))


def build_delivery(dv: dict, date: str) -> str:
    if not dv:
        return ""
    parts = ['<section class="content-section">', '  <h2>🚚 物流配送</h2>']
    if dv.get("type"):
        parts.append('  <p>{}</p>'.format(_esc(dv["type"])))
    if dv.get("details"):
        for d in dv["details"]:
            parts.append('  <div class="delivery-card">{}</div>'.format(_esc(d)))
    if dv.get("note"):
        parts.append('  <p style="font-size:13px;color:var(--color-text-muted);">{}</p>'.format(_esc(dv["note"])))
    parts.append('  {}'.format(_ds(date)))
    parts.append('</section>')
    return "\n".join(parts)


def build_images(images: list, videos: list, date: str) -> str:
    if not images and not videos:
        return ""
    img_count = len(images) if images else 0
    vid_count = len(videos) if videos else 0

    items = ""
    # product images
    if images:
        for i, url in enumerate(images):
            u = _esc_url(url)
            label = "主图" if i == 0 else "图 {}".format(i + 1)
            items += '    <img src="{}" data-full="{}" alt="{}" loading="lazy">\n'.format(u, u, label)
    # videos — thumbnail blocks with first-frame preview + play overlay
    if videos:
        for j, url in enumerate(videos):
            u = _esc_url(url)
            items += '    <div class="gallery-video-item" data-video="{}" title="视频 {}">\n'.format(u, j + 1)
            items += '      <video src="{}" preload="metadata" muted playsinline></video>\n'.format(u)
            items += '      <div class="video-play-btn">▶</div>\n'
            items += '    </div>\n'

    parts = ["{} 张图片".format(img_count)]
    if vid_count > 0:
        parts.append("{} 个视频".format(vid_count))
    subtitle = " · ".join(parts) + " · 点击放大/播放"

    return """<section class="content-section">
  <h2>🖼️ 产品图片/视频<span style="font-weight:400;font-size:13px;color:var(--color-text-muted);margin-left:8px;">{}</span></h2>
  <div class="gallery" id="product-gallery">
{}
  </div>
  {}
</section>""".format(subtitle, items, _ds(date))


def build_aplus(aplus: list, date: str) -> str:
    if not aplus:
        return ""
    first_url = _esc_url(aplus[0])
    rest = ""
    for url in aplus[1:]:
        u = _esc_url(url)
        rest += '    <img src="{}" data-full="{}" alt="A+ 模块" loading="lazy" style="width:100%;border-radius:8px;border:1px solid var(--color-border);cursor:pointer;">\n'.format(u, u)
    return """<section class="content-section">
  <h2>📸 A+ 图文详情<span style="font-weight:400;font-size:13px;color:var(--color-text-muted);margin-left:8px;">{} 张 · 点击放大浏览</span></h2>
  <p>品牌方为产品配置了 A+ 内容（增强品牌内容），用于提升详情页转化。</p>
  <div class="aplus-banner">
    <img src="{}" data-full="{}" alt="A+ 横幅" loading="lazy" style="cursor:pointer;">
  </div>
  <div class="aplus-grid">
{}
  </div>
  {}
</section>""".format(len(aplus), first_url, first_url, rest, _ds(date))


def build_specs(specs: list, date: str) -> str:
    if not specs:
        return ""
    rows = ""
    for s in specs:
        rows += '<tr><td>{}</td><td>{}</td></tr>\n'.format(_esc(s.get("name", "")), _esc(s.get("value", "")))
    return """<section class="content-section">
  <h2>📋 产品规格</h2>
  <div class="data-table-wrapper">
    <table class="data-table">
      <thead><tr><th>规格名称</th><th>规格</th></tr></thead>
      <tbody>
{}
      </tbody>
    </table>
  </div>
  {}
</section>""".format(rows, _ds(date))


def build_footer(asin: str, date: str, site: str = "amazon") -> str:
    site_names = {"amazon": "Amazon US", "shein": "SHEIN US"}
    site_label = site_names.get(site, site.upper())
    return '<div class="report-footer">报告由 LinkFox AI 生成 · 数据采集自 {} · ID: {} · {} · 仅供内部参考</div>'.format(
        _esc(site_label), _esc(asin), _esc(date))


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def generate(input_path: str, output_path: str = None, site: str = None):
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 自动检测站点（如果未指定）
    if not site:
        meta = data.get("meta", {})
        asin = meta.get("asin", "")
        # SHEIN SKU 格式: sm 开头 + 数字；Amazon ASIN: B 开头 10 位字母数字
        if asin.startswith("sm") or asin.startswith("SKU:"):
            site = "shein"
        elif "SHEIN" in meta.get("tagline", "") or "shein" in meta.get("tagline", "").lower():
            site = "shein"
        else:
            site = "amazon"

    meta = data.get("meta", {})
    date = meta.get("date", "")

    # Build all sections
    sections = []
    rating = data.get("rating") or {}
    sections.append(build_kpi(data.get("kpi") or [], (rating or {}).get("score", 0)))

    overview = data.get("overview", {})
    if overview:
        overview["bullets"] = data.get("bullets", [])
    sections.append(build_overview(overview, date))

    sections.append(build_price(data.get("price_variants", {}), date))

    sections.append(build_rating(data.get("rating", {}), date))

    if site == "shein":
        rt = data.get("rating") or {}
        fit = rt.get("fit_distribution")
        if fit:
            sections.append('<section class="content-section"><h2>📐 合身度分布</h2>{}</section>'.format(
                build_fit_distribution(fit)))

    sections.append(build_delivery(data.get("delivery", {}), date))
    sections.append(build_images(data.get("images", []), data.get("videos", []), date))

    if site == "shein":
        sections.append(build_reviews(data.get("reviews", []), date))
    else:
        sections.append(build_aplus(data.get("aplus", []), date))

    sections.append(build_specs(data.get("specs", []), date))
    sections.append(build_footer(meta.get("asin", ""), date, site))

    content_html = "\n".join(s for s in sections if s)
    chart_js = build_chart_js(data.get("rating", {}))

    # Load template
    if not os.path.exists(TEMPLATE_PATH):
        print("ERROR: 模板文件不存在: {}".format(TEMPLATE_PATH), file=sys.stderr)
        sys.exit(1)
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template = f.read()

    # Load & inject CSS
    shared_css = _inject_brand(_read("_base.css"), site)
    platform_css = _read(PLATFORM_CSS_FILE.get(site, ""))
    brand = BRAND.get(site, BRAND["amazon"])

    html = template
    html = html.replace("{{SHARED_CSS}}", shared_css)
    html = html.replace("{{PLATFORM_CSS}}", platform_css)
    html = html.replace("{{CHART_COLORS_JS}}", brand["CHART_COLORS_JS"])
    html = html.replace("{{TITLE}}", _esc(meta.get("title", "Product Report")[:80]))
    html = html.replace("{{SUBTITLE}}", _esc(meta.get("subtitle", "")[:80]))
    html = html.replace("{{META}}", _esc(meta.get("tagline", "")))
    html = html.replace("<!-- REPORT_CONTENT -->", content_html)
    html = html.replace("<!-- CHART_INIT -->", chart_js)

    if not output_path:
        base = os.path.splitext(os.path.basename(input_path))[0]
        output_path = os.path.join(os.path.dirname(input_path) or ".", "{}_report.html".format(base))

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    size = os.path.getsize(output_path)
    print("OK 报告已生成: {}".format(os.path.abspath(output_path)))
    print("   文件大小: {:,} bytes".format(size))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python generate_report.py <clean_data.json> [output.html] [--site amazon|shein]")
        sys.exit(1)

    # parse --site
    site = None
    positional = []
    for a in sys.argv[1:]:
        if a.startswith("--site="):
            site = a.split("=", 1)[1]
        elif a == "--site":
            site = None  # will be taken from next arg
        elif site is None and positional and positional[-1] == "--site__":
            pass  # handled
        else:
            positional.append(a)

    # Simple --site parsing: find --site and its value
    args = sys.argv[1:]
    site_arg = None
    filtered = []
    i = 0
    while i < len(args):
        if args[i].startswith("--site="):
            site_arg = args[i].split("=", 1)[1]
            i += 1
        elif args[i] == "--site":
            if i + 1 < len(args):
                site_arg = args[i + 1]
                i += 2
            else:
                print("ERROR: --site 缺少参数", file=sys.stderr)
                sys.exit(1)
        else:
            filtered.append(args[i])
            i += 1

    input_file = filtered[0] if len(filtered) > 0 else None
    output_file = filtered[1] if len(filtered) > 1 else None

    if not input_file:
        print("用法: python generate_report.py <clean_data.json> [output.html] [--site amazon|shein]")
        sys.exit(1)

    generate(input_file, output_file, site_arg)
