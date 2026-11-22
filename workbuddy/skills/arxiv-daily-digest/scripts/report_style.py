# report_style.py
# Default HTML style for the arXiv daily digest report.
#
# The style is a SHIPPED DEFAULT, not a machine-locked template: it is bundled as
# assets/default_style.css and also kept inline as the CSS constant below so the
# module stays self-contained. Callers may override it entirely by passing
# ctx["css"] (a custom stylesheet string) or by pointing build_report.py at a
# different --style file. Do NOT reference any machine-specific report path.
import html

CSS = """<style>
  body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
       background:#f4f5f7;color:#1f2328;margin:0;padding:24px;line-height:1.65;}
  .wrap{max-width:920px;margin:0 auto;}
  .hero{background:linear-gradient(135deg,#0d1117,#1f6feb);color:#fff;border-radius:14px;padding:26px 28px;margin-bottom:20px;}
  .hero h1{margin:0 0 6px;font-size:22px;}
  .hero p{margin:2px 0;opacity:.9;font-size:13.5px;}
  .note{background:#fff8e5;border:1px solid #f0d58c;color:#6b5300;border-radius:10px;padding:10px 14px;font-size:13px;margin-bottom:18px;}
  .card{display:flex;gap:14px;background:#fff;border:1px solid #e3e6ea;border-radius:12px;padding:18px 20px;margin-bottom:14px;box-shadow:0 1px 3px rgba(0,0,0,.04);}
  .rank{flex:0 0 42px;height:42px;width:42px;border-radius:50%;background:#1f6feb;color:#fff;font-weight:700;font-size:17px;display:flex;align-items:center;justify-content:center;}
  .body{flex:1;min-width:0;}
  .head{display:flex;flex-wrap:wrap;justify-content:space-between;gap:8px;align-items:flex-start;}
  .title{font-size:16.5px;font-weight:700;color:#0d1117;text-decoration:none;}
  .title:hover{text-decoration:underline;}
  .tags{display:flex;gap:6px;flex-wrap:wrap;}
  .tag{color:#fff;font-size:11.5px;padding:2px 8px;border-radius:20px;white-space:nowrap;}
  .meta{margin:6px 0 10px;font-size:12.5px;color:#57606a;}
  .venue{display:inline-block;background:#ddf4e4;color:#1a7f37;border:1px solid #aadfb9;border-radius:6px;padding:1px 8px;margin-right:8px;font-weight:600;}
  .sec{margin:9px 0;}
  .lbl{display:inline-block;font-weight:700;font-size:12.5px;color:#1f6feb;background:#eaf2ff;border-radius:5px;padding:1px 7px;margin-bottom:3px;}
  .sec p{margin:3px 0 0;font-size:13.6px;}
  .sec ul{margin:4px 0 0;padding-left:20px;font-size:13.4px;}
  .sec ul li{margin:3px 0;}
  .abs{font-size:12.8px;color:#3a4149;background:#f6f8fa;border-left:3px solid #d0d7de;padding:8px 12px;border-radius:0 6px 6px 0;}
  .links{margin-top:10px;font-size:12.5px;}
  .links a{color:#1f6feb;text-decoration:none;margin-right:16px;font-weight:600;}
  .links a:hover{text-decoration:underline;}
  .foot{text-align:center;color:#8b949e;font-size:12px;margin:20px 0 6px;}
  .au-list{margin:4px 0 0;}
  .au{margin:2px 0;font-size:13px;line-height:1.5;}
  .au-name{font-weight:600;color:#0d1117;}
  .badge{display:inline-block;font-size:10.5px;font-weight:700;padding:1px 6px;border-radius:4px;margin-left:5px;vertical-align:middle;white-space:nowrap;}
  .badge-first{background:#1f6feb;color:#fff;}
  .badge-eq{background:#8957e5;color:#fff;}
  .badge-corr{background:#1a7f37;color:#fff;}
  .au-aff{color:#57606a;font-size:12px;margin-left:6px;}
  .au-warn{color:#9a6700;font-size:11px;margin-left:6px;}
  .inst-list{margin:6px 0 0;font-size:12px;color:#3a4149;}
  .inst-list .lbl{margin-right:6px;}
  .inst{margin:1px 0;}
</style>"""

# theme key -> (label, color)  — built-in default theme dictionary
THEME_LABEL = {"embodied": "具身智能", "cv": "计算机视觉", "3d": "3D 重建"}
THEME_COLOR = {"embodied": "#1f6feb", "cv": "#1a7f37", "3d": "#8957e5"}


def load_css(path=None):
    """Return the stylesheet to embed.

    If ``path`` is given and readable, load the custom stylesheet from that
    file (user override). Otherwise return the bundled DEFAULT_STYLE (light
    theme). Raise SystemExit on a bad path so the caller fails loudly rather
    than silently falling back to the default.

    The returned string is always wrapped in a single ``<style>…</style>``
    block to match the render template: the inline ``CSS`` constant is already
    wrapped, while a ``.css`` asset file normally contains raw CSS and gets
    wrapped here.
    """
    if path:
        try:
            with open(path, encoding="utf-8") as fh:
                s = fh.read()
        except OSError as e:
            raise SystemExit(f"cannot read style file {path}: {e}")
        if "<style" not in s:
            s = f"<style>\n{s}\n</style>"
        return s
    return CSS


# Convenience alias for the bundled default (kept inline so the module is
# self-contained even without the assets/ copy).
DEFAULT_STYLE = CSS


def theme_tags(theme_keys, custom=None):
    spans = []
    for k in theme_keys:
        if k in THEME_LABEL:
            label, color = THEME_LABEL[k], THEME_COLOR[k]
        elif custom:
            label, color = custom.get("label", k), custom.get("color", "#1f6feb")
        else:
            label, color = k, "#1f6feb"
        spans.append(f'<span class="tag" style="background:{color}">{html.escape(label)}</span>')
    return '<div class="tags">' + "".join(spans) + '</div>'


def render_authors(detail, plain=None):
    """Render the per-author block (name + 一作/共一/通讯 badges + affiliations +
    contact emails).

    Returns HTML string. When no structured metadata is available (or the
    structured record carries no author names), falls back to the plain author
    line passed by the caller."""
    if not detail or not detail.get("ok"):
        return None
    affs = detail.get("affiliations", {})
    authors = detail.get("authors", [])
    if not authors:
        # institutions / emails resolved but names came only from arXiv listing
        block = '<div class="au-list"><div class="au"><span class="au-name">%s</span></div></div>' \
                % html.escape(plain or "")
        if affs:
            items = "".join('<div class="inst"><b>%s</b> %s</div>'
                            % (html.escape(k), html.escape(v)) for k, v in affs.items())
            block += '<div class="inst-list"><span class="lbl">机构列表</span>%s</div>' % items
        emails = detail.get("emails") or []
        if emails:
            block += '<div class="inst-list"><span class="lbl">联系方式</span>%s</div>' \
                     % (" · ".join(html.escape(e) for e in emails))
        return block
    rows = []
    for a in authors:
        badges = []
        if a.get("first"):
            badges.append('<span class="badge badge-first">一作</span>')
        if a.get("equal"):
            badges.append('<span class="badge badge-eq">共一</span>')
        if a.get("corr"):
            badges.append('<span class="badge badge-corr">通讯</span>')
        linked = [affs.get(str(x), "") for x in a.get("affs", [])]
        linked = [x for x in linked if x]
        if linked:
            aff_html = ' <span class="au-aff">%s</span>' % html.escape(" / ".join(linked))
        elif affs:
            aff_html = ' <span class="au-warn">（机构未在 arXiv 渲染中关联）</span>'
        else:
            aff_html = ""
        rows.append('<div class="au"><span class="au-name">%s</span>%s%s</div>'
                    % (html.escape(a.get("name", "")), "".join(badges), aff_html))
    block = '<div class="au-list">' + "".join(rows) + '</div>'
    # When no author could be linked to an institution (LLNCS/B dialect with
    # marker-only superscripts), surface the numbered institution list so the
    # institutions are still visible.
    if affs and not any(a.get("affs") for a in authors):
        items = "".join('<div class="inst"><b>%s</b> %s</div>'
                        % (html.escape(k), html.escape(v)) for k, v in affs.items())
        block += '<div class="inst-list"><span class="lbl">机构列表</span>%s</div>' % items
    # Contact emails (from HTML ltx_role_email or LaTeX e-print source)
    emails = detail.get("emails") or []
    if emails:
        block += '<div class="inst-list"><span class="lbl">联系方式</span>%s</div>' \
                 % (" · ".join(html.escape(e) for e in emails))
    return block


def render_card(c, rank, ctx=None):
    custom = (ctx or {}).get("custom_theme")
    tags = theme_tags(c.get("themes", []), custom)
    venue = html.escape(c.get("venue", "预印本 (Preprint)"))
    date = html.escape(c.get("date", ""))
    authors_plain = html.escape(c.get("authors", ""))
    title = html.escape(c.get("title", ""))
    link = c.get("link", "")
    pdf = c.get("pdf", link.replace("/abs/", "/pdf/"))
    abstract = html.escape(c.get("abstract", ""))
    topic = html.escape(c.get("topic", ""))
    content = html.escape(c.get("content", ""))
    inn = "".join(f"<li>{html.escape(x)}</li>" for x in c.get("innovations", []))
    ablock = render_authors(c.get("authors_detail"), authors_plain)
    if ablock is None:
        ablock = '<div class="au-list"><div class="au"><span class="au-name">%s</span></div></div>' % authors_plain
    return f"""
    <div class="card">
      <div class="rank">#{rank}</div>
      <div class="body">
        <div class="head">
          <a class="title" href="{link}">{title}</a>
          {tags}
        </div>
        <div class="meta">
          <span class="venue">{venue}</span>
          {'提交日期：' + date if date else ''}
        </div>
        <div class="sec"><span class="lbl">作者与机构</span>{ablock}</div>
        <div class="sec"><span class="lbl">主题</span><p>{topic}</p></div>
        <div class="sec"><span class="lbl">主要创新点</span><ul>{inn}</ul></div>
        <div class="sec"><span class="lbl">主要内容</span><p>{content}</p></div>
        <div class="sec"><span class="lbl">摘要</span><p class="abs">{abstract}</p></div>
        <div class="links">
          <a href="{link}">arXiv 摘要页 ↗</a>
          <a href="{pdf}">PDF ↗</a>
        </div>
      </div>
    </div>"""


def render(cards, ctx):
    date_label = ctx.get("date_label", "")
    batch = ctx.get("batch", "")
    scope = ctx.get("scope", "")
    note = ctx.get("note", "")
    foot = ctx.get("foot", "自动生成 · 数据来源 arXiv.org")
    custom = ctx.get("custom_theme")
    css = ctx.get("css") or DEFAULT_STYLE
    title = ctx.get("title") or "arXiv 每日精选"
    if date_label and "（" not in title and ")" not in title:
        title = f"{title}（{date_label}）"
    hero_title = ctx.get("hero_title") or title
    cards_html = "\n".join(render_card(c, i + 1, ctx) for i, c in enumerate(cards))
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
{css}</head>
<body><div class="wrap">
  <div class="hero">
    <h1>{html.escape(hero_title)}</h1>
    <p>批次：{html.escape(batch)}</p>
    <p>范围：{html.escape(scope)}</p>
  </div>
  <div class="note">说明：{note}</div>
{cards_html}
  <div class="foot">{foot}</div>
</div></body></html>"""
