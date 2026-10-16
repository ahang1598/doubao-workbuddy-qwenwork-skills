"""
3 种 page skeleton · 输入 (kicker/title/subtitle/img_ref/takeaway/section/page_num, palette)
输出完整 slide XML（960×540 · Lark SXSD 合规 · lint pass）

这里的关键是：**页面 chrome 是专业感的关键 60%**，pattern 图本身只占 40%。
所以 skeleton 要严格模仿 reference deck 的 chrome：
  masthead (kicker + right meta)
  main title
  subtitle (encoding / method note)
  main image (900x400 aspect · 严格匹配 SVG viewBox)
  takeaway bracketed line
  bottom folio (deck name + section + page num)
"""
from typing import Optional
from .palettes import Palette


def _esc(s: str) -> str:
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;"))


def _rgba(hex_or_rgb: str) -> str:
    """把 #RRGGBB / #RRGGBBAA / 已经是 rgba() 的都规范成 rgba(r,g,b,a)"""
    s = hex_or_rgb.strip()
    if s.startswith("rgba"):
        return s
    if s.startswith("rgb("):
        return s.replace("rgb(", "rgba(").rstrip(")") + ",1)"
    if s.startswith("#"):
        h = s[1:]
        if len(h) == 6:
            r = int(h[0:2], 16); g = int(h[2:4], 16); b = int(h[4:6], 16)
            return f"rgba({r},{g},{b},1)"
        if len(h) == 8:
            r = int(h[0:2], 16); g = int(h[2:4], 16); b = int(h[4:6], 16)
            a = int(h[6:8], 16) / 255
            return f"rgba({r},{g},{b},{a:.2f})"
    return s


# ═════════════════════════════════════════════════════════════════
# Slide XML primitives
# ═════════════════════════════════════════════════════════════════

def _txt(x, y, w, h, s, *, palette=None, font=None, size=12, bold=False,
         italic=False, color=None, letter=None, align=None, line_h=None):
    font = font or (palette.body_family if palette else "sans-serif")
    color = _rgba(color or (palette.ink if palette else "#1E2028"))
    ca = [f'fontFamily="{font}"', f'fontSize="{size}"', f'color="{color}"',
          'autoFit="normal-auto-fit"', 'wrap="true"']
    if bold: ca.append('bold="true"')
    if italic: ca.append('italic="true"')
    if letter is not None: ca.append(f'letterSpacing="{letter}"')
    if align: ca.append(f'textAlign="{align}"')
    if line_h is not None: ca.append(f'lineSpacing="multiple:{line_h}"')
    if isinstance(s, str):
        body = f'<p>{_esc(s)}</p>'
    else:
        body = "".join(f'<p>{_esc(ln)}</p>' for ln in s)
    return (f'<shape type="text" topLeftX="{x}" topLeftY="{y}" '
            f'width="{w}" height="{h}"><content {" ".join(ca)}>{body}</content></shape>')


def _rect(x, y, w, h, fill=None, border=None, border_w=1):
    parts = [f'<shape type="rect" topLeftX="{x}" topLeftY="{y}" '
             f'width="{w}" height="{h}">']
    if fill:
        parts.append(f'<fill><fillColor color="{_rgba(fill)}"/></fill>')
    if border:
        parts.append(f'<border color="{_rgba(border)}" width="{int(border_w)}"/>')
    parts.append('</shape>')
    return "".join(parts)


def _hline(x1, y1, x2, y2, color, w=1):
    return (f'<line startX="{x1}" startY="{y1}" endX="{x2}" endY="{y2}">'
            f'<border color="{_rgba(color)}" width="{int(w)}"/></line>')


def _img(src, x, y, w, h):
    return f'<img src="{src}" topLeftX="{x}" topLeftY="{y}" width="{w}" height="{h}"/>'


def _slide(sid, parts, bg):
    return (f'<slide id="{sid}">'
            f'<style><fill><fillColor color="{_rgba(bg)}"/></fill></style>'
            f'<data>{"".join(parts)}</data></slide>')


# ═════════════════════════════════════════════════════════════════
# Chrome 组件
# ═════════════════════════════════════════════════════════════════

def _masthead(palette: Palette, kicker: str, right_meta: str = ""):
    """顶部两条 hairline + kicker + 右 meta"""
    p = []
    # 顶部粗线（primary 色）
    p.append(_hline(30, 22, 930, 22, palette.primary, w=2))
    p.append(_txt(30, 26, 500, 14, kicker, palette=palette,
                  font=palette.mono_family, size=8, bold=True,
                  letter=palette.kicker_letter_spacing,
                  color=palette.primary))
    if right_meta:
        p.append(_txt(560, 26, 370, 14, right_meta, palette=palette,
                      font=palette.mono_family, size=8, bold=True,
                      letter=2.0, color=palette.gray, align="right"))
    # 底部细线
    p.append(_hline(30, 42, 930, 42, palette.hair, w=1))
    return p


def _folio(palette: Palette, page_num: int, total: int, section: str = ""):
    p = []
    p.append(_hline(30, 512, 930, 512, palette.primary, w=1))
    p.append(_txt(30, 520, 400, 14, palette.signature_note or "",
                  palette=palette, font=palette.mono_family, size=7,
                  bold=True, letter=2.0, color=palette.primary))
    if section:
        p.append(_txt(430, 520, 200, 14, section, palette=palette,
                      font=palette.mono_family, size=7, bold=True,
                      letter=2.0, color=palette.gray, align="center"))
    p.append(_txt(730, 520, 200, 14,
                  f"PAGE {page_num:02d} / {total:02d}",
                  palette=palette, font=palette.mono_family, size=8,
                  bold=True, letter=1.6, color=palette.gray,
                  align="right"))
    return p


def _takeaway(palette: Palette, takeaway: str, y: int = 490):
    """底部 [TAKEAWAY] 行 · 一根 hairline + 短 label + 结论"""
    p = []
    p.append(_hline(30, y, 930, y, palette.accent, w=1))
    p.append(_txt(30, y + 4, 700, 14,
                  f"[TAKEAWAY] {takeaway}",
                  palette=palette, font=palette.mono_family, size=9,
                  bold=True, letter=1.5, color=palette.accent_dim))
    return p


# ═════════════════════════════════════════════════════════════════
# Skeleton 1 · Full-Bleed （默认 · 70% pattern 页用它）
# ═════════════════════════════════════════════════════════════════

def full_bleed(
    slide_id: str,
    palette: Palette,
    *,
    kicker: str,              # § 01 · FIG 1 · MILESTONE TIMELINE · BUBBLE TIMELINE
    right_meta: str,          # ALZHEIMER'S REVIEW · ar V5
    title: str,               # Fig. 1 | Thirty years, five paradigms, seventeen landmarks
    subtitle: str,            # Colour codes mechanism class · circles = approval · crosses = failure
    img_src: str,             # @./pngs/F.png · 需要 pattern 的 PNG（900×400 aspect）
    takeaway: str,            # 27 years symptomatic-only therapy · then three anti-amyloid...
    section: str,             # III  or  BUSINESS · V3
    page_num: int,
    total_pages: int,
    figure_caption: str = "", # 图正下方 · Fig. 1 | Landmark approvals and pivotal trials...
    encoding_note: str = "",  # 图上方或下方 encoding · Symbol key · Circles = approval
    source_line: str = "",    # Source · EMA/FDA registries, accessed Aug 2026
) -> str:
    """
    Full-bleed layout · main image 主导 · 左右满宽

    坐标布局（960×540）：
      y  22   masthead 粗线
      y  26   masthead kicker
      y  42   masthead 细线
      y  55   main title
      y  86   subtitle
      y 106   encoding_note (可选)
      y 122   main image (30, 122, 900, 336) · aspect 900:336 ≈ 2.68:1
      y 462   figure caption (可选)
      y 476   source line (可选)
      y 498   [TAKEAWAY] hairline + line
      y 512   folio 分隔线
      y 520   folio content
    """
    parts = _masthead(palette, kicker, right_meta)

    # main title (serif bold or sans bold)
    title_font = palette.head_family if palette.title_style.startswith("serif") else palette.body_family
    title_italic = palette.title_style.endswith("italic")
    parts.append(_txt(30, 52, 900, 32, title, palette=palette,
                      font=title_font, size=24, bold=True, italic=title_italic,
                      color=palette.ink))
    # subtitle
    subtitle_font = palette.head_family if palette.subtitle_style.startswith("serif") else palette.body_family
    subtitle_italic = palette.subtitle_style.endswith("italic")
    parts.append(_txt(30, 84, 900, 16, subtitle, palette=palette,
                      font=subtitle_font, size=12, italic=subtitle_italic,
                      color=palette.gray))

    # optional encoding note above image
    img_y = 122
    if encoding_note:
        parts.append(_txt(30, 104, 900, 14, encoding_note, palette=palette,
                          font=palette.body_family, size=9, italic=True,
                          color=palette.gray))
        img_y = 124

    # ─── main image (aspect 900:336) ───
    parts.append(_img(img_src, 30, img_y, 900, 336))

    # figure caption + source
    caption_y = img_y + 340
    if figure_caption:
        parts.append(_txt(30, caption_y, 900, 12, figure_caption, palette=palette,
                          font=palette.body_family, size=9, italic=True,
                          color=palette.gray))
    if source_line:
        parts.append(_txt(30, caption_y + 14, 900, 12, source_line,
                          palette=palette, font=palette.mono_family, size=8,
                          letter=1.2, color=palette.gray))

    # takeaway + folio
    parts.extend(_takeaway(palette, takeaway))
    parts.extend(_folio(palette, page_num, total_pages, section))

    return _slide(slide_id, parts, palette.bg)


# ═════════════════════════════════════════════════════════════════
# Skeleton 2 · Left Rail Text（学术页型 · 左文右大图）
# ═════════════════════════════════════════════════════════════════

def left_rail_text(
    slide_id: str,
    palette: Palette,
    *,
    kicker: str,
    right_meta: str,
    title: str,
    subtitle: str,
    left_paragraphs: list,    # 左侧多段文本 · 每项 (heading, body) 或 str
    img_src: str,             # 右侧大图 · 710×340 aspect ≈ 2.09:1
    takeaway: str,
    section: str,
    page_num: int,
    total_pages: int,
) -> str:
    """
    左侧 200px 文本栏 + 右侧 710×340 大图。

    坐标：
      x  30..220  · left rail
      x 240..930  · right image (710×340)
    """
    parts = _masthead(palette, kicker, right_meta)

    # title / subtitle 撑满宽度
    title_font = palette.head_family if palette.title_style.startswith("serif") else palette.body_family
    title_italic = palette.title_style.endswith("italic")
    parts.append(_txt(30, 52, 900, 30, title, palette=palette,
                      font=title_font, size=22, bold=True, italic=title_italic,
                      color=palette.ink))
    subtitle_italic = palette.subtitle_style.endswith("italic")
    parts.append(_txt(30, 82, 900, 16, subtitle, palette=palette,
                      font=palette.body_family, size=11, italic=subtitle_italic,
                      color=palette.gray))

    # left rail
    y = 118
    for item in left_paragraphs:
        if isinstance(item, tuple):
            heading, body_text = item
        else:
            heading, body_text = None, item
        if heading:
            parts.append(_txt(30, y, 180, 14, heading, palette=palette,
                              font=palette.mono_family, size=8, bold=True,
                              letter=1.8, color=palette.primary))
            y += 16
        parts.append(_txt(30, y, 200, 60, body_text, palette=palette,
                          font=palette.body_family, size=10, line_h=1.5,
                          color=palette.ink))
        y += 70

    # right image · 710×340
    parts.append(_img(img_src, 240, 122, 690, 340))

    parts.extend(_takeaway(palette, takeaway))
    parts.extend(_folio(palette, page_num, total_pages, section))
    return _slide(slide_id, parts, palette.bg)


# ═════════════════════════════════════════════════════════════════
# Skeleton 3 · Main + Right Rail（F 骨架 · 主图 + 右上 mini + 右下 focal card）
# ═════════════════════════════════════════════════════════════════

def main_right_rail(
    slide_id: str,
    palette: Palette,
    *,
    kicker: str,
    right_meta: str,
    title: str,
    subtitle: str,
    main_img_src: str,        # 主图 · 570×340 aspect ≈ 1.68:1
    mini_img_src: str = "",   # 右上 mini · 300×160 aspect
    focal_title: str = "",    # 焦点卡标题
    focal_metric: str = "",   # 大号数字
    focal_body: str = "",     # 焦点卡正文（可多行）
    takeaway: str = "",
    section: str = "",
    page_num: int = 1,
    total_pages: int = 1,
) -> str:
    """
    F 骨架 · 主图 + 右上 mini + 右下 focal card。

    坐标：
      main   30, 122, 570, 340
      mini  620, 122, 310, 160
      focal 620, 302, 310, 160
    """
    parts = _masthead(palette, kicker, right_meta)

    title_font = palette.head_family if palette.title_style.startswith("serif") else palette.body_family
    title_italic = palette.title_style.endswith("italic")
    parts.append(_txt(30, 52, 900, 30, title, palette=palette,
                      font=title_font, size=22, bold=True, italic=title_italic,
                      color=palette.ink))
    parts.append(_txt(30, 82, 900, 16, subtitle, palette=palette,
                      font=palette.body_family, size=11, italic=True,
                      color=palette.gray))

    # main image
    parts.append(_img(main_img_src, 30, 122, 570, 340))

    # mini image
    if mini_img_src:
        parts.append(_img(mini_img_src, 620, 122, 310, 160))
    else:
        parts.append(_rect(620, 122, 310, 160, fill=palette.bg_alt))

    # focal card
    parts.append(_rect(620, 302, 310, 160, fill=palette.bg_alt))
    parts.append(_hline(620, 302, 930, 302, palette.accent, w=2))
    if focal_title:
        parts.append(_txt(635, 316, 290, 14, f"FOCAL · {focal_title}",
                          palette=palette, font=palette.mono_family, size=9,
                          bold=True, letter=1.5, color=palette.accent_dim))
    if focal_metric:
        parts.append(_txt(635, 336, 290, 32, focal_metric, palette=palette,
                          font=palette.head_family, size=26, bold=True,
                          color=palette.ink))
    if focal_body:
        parts.append(_txt(635, 380, 290, 76, focal_body, palette=palette,
                          font=palette.body_family, size=10, line_h=1.5,
                          color=palette.ink))

    parts.extend(_takeaway(palette, takeaway))
    parts.extend(_folio(palette, page_num, total_pages, section))
    return _slide(slide_id, parts, palette.bg)
