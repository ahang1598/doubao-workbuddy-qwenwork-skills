#!/usr/bin/env python3
"""
把 HTML 引用的本地静态资源（图片、字体等）以 Base64 data URI 内嵌，产出单文件 HTML。

用途：云端虚拟机场景下 HTML 只能单文件交付，`assets/` 里的图片必须内嵌，
      否则用户拿到的页面全是裂图。

用法：
  python3 embed.py index.html
      # 产出同目录 index_embed.html，JSON 报告打到 stdout

  python3 embed.py index.html -o dist/final.html      # 指定输出路径
  python3 embed.py index.html --dry-run               # 只报告不写文件
  python3 embed.py index.html --allow-outside         # 允许内嵌 HTML 所在目录之外的文件
  python3 embed.py index.html --max-file-bytes 2097152  # 跳过大于 2MiB 的单个文件

会处理：
  - 标签属性：src / srcset / poster / data-src 等，<link href>（icon 类），
    <image href> 与 <image xlink:href>
  - CSS：<style> 块与 style="" 属性里的 url(...)（含 @font-face、image-set）
不会改写 <script> 里的任何东西：同一个字符串在 JS 里可能是资源地址，也可能是
下载名 / 显示名 / 比较常量，脚本无法可靠区分。这类位置只检测并在 warnings 里
报出来，交给调用方处理。

不会处理（都记在 skipped 里并附原因）：
  - 远程 URL、已经是 data: 的引用
  - 外链 .css / .js —— data URI 内的相对路径会失效，按 skill 要求本就该内联
  - SVG sprite（`x.svg#icon`）—— data URI + fragment 浏览器支持不一致
  - <iframe> / <embed> / <object> / <use>
  - HTML 所在目录之外的文件（除非 --allow-outside）

Exit codes:
  0  产出成功（missing / skipped 不改变退出码，看 JSON 报告）
  2  参数或输入错误（文件不存在、输入本身已是 _embed 产物、输出不可写）
  3  未预期的内部错误

任何情况下 stdout 都是合法 JSON，不会裸抛 traceback。
"""

import argparse
import base64
import json
import mimetypes
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import unquote, urlparse

# ---------------------------------------------------------------- 正则与常量

# <script> / <style> / 注释：这三类区域要用各自的规则处理，不能当普通标签扫
REGION_RE = re.compile(
    r"<!--.*?-->"
    r"|<script\b[^>]*>.*?</script\s*>"
    r"|<style\b[^>]*>.*?</style\s*>",
    re.DOTALL | re.IGNORECASE,
)

# 属性感知的标签匹配：引号内的 ">" 不会提前截断
TAG_RE = re.compile(r"""<([a-zA-Z][a-zA-Z0-9:_-]*)((?:"[^"]*"|'[^']*'|[^>"'])*)>""")

# 组 3/4/5 分别是 双引号内 / 单引号内 / 无引号 的属性值
ATTR_RE = re.compile(
    r"""([a-zA-Z_:][a-zA-Z0-9_:.\-]*)\s*=\s*("([^"]*)"|'([^']*)'|([^\s"'>=`]+))"""
)

# 组 1/2/3 分别是 双引号内 / 单引号内 / 无引号 的 url() 内容
CSS_URL_RE = re.compile(
    r"""url\(\s*(?:"([^"]*)"|'([^']*)'|([^)"']*))\s*\)""", re.IGNORECASE
)

# <script> 里的图片路径字面量：只认图片后缀，且必须在磁盘上真实存在才改写
SCRIPT_STR_RE = re.compile(
    r"""(["'`])([^"'`\n\\]{1,400}?\.(?:png|jpe?g|gif|webp|avif|svg|bmp|ico))\1""",
    re.IGNORECASE,
)

# 只有字符串出现在「明显用作资源 URL」的位置才改写。宁可漏也不错改——
# 漏了是裂图，自检截图能看见；错改是静默破坏（比如把 localStorage 键换成 data URI）。
SCRIPT_URL_CTX_RE = re.compile(
    r"(?:src|srcset|href|poster|image|images|img|imgs|bg|background|backgroundimage|"
    r"icon|icons|thumb|thumbnail|avatar|logo|photo|photos|pic|pics|picture|pictures|"
    r"url|urls|banner|cover|wallpaper|sprite|texture|frame|frames|slide|slides|gallery)"
    r"""\s*[=:]\s*(?:new\s+Image\s*\(\s*)?(?:\[\s*)?"""
    r"""(?:(?:'[^'\n]*'|"[^"\n]*"|`[^`\n]*`)\s*,\s*)*$""",
    re.IGNORECASE,
)
SCRIPT_SETATTR_CTX_RE = re.compile(
    r"""(?:setAttribute|setAttributeNS)\s*\([^()]{0,40}['"](?:src|srcset|href|poster)['"]\s*,\s*$""",
    re.IGNORECASE,
)

# CSS image-set() / -webkit-image-set()：候选项可以是裸字符串，不走 url()
IMAGE_SET_RE = re.compile(r"(?:-webkit-)?image-set\s*\(", re.IGNORECASE)
QUOTED_RE = re.compile(r"""(["'])([^"'\n]*)\1""")

# <script> 里的远程资源链接。豆包 CDN / byteimg 签名链没有图片后缀，
# 靠域名识别；它们又恰好是「几天到几周后过期」的那一类，必须报出来。
SCRIPT_REMOTE_RE = re.compile(
    r"""(['"`])(https?://[^'"`\s]*(?:doubaocdn\.com|byteimg\.com)[^'"`\s]*)\1""",
    re.IGNORECASE,
)

# SKILL.md 明确要求走这些域（JS 库、字体镜像），不能对它们报「远程资源」告警
SANCTIONED_HOSTS = (
    "cdn.jsdelivr.net", "cdnjs.cloudflare.com", "unpkg.com",
    "miaoda.feishu.cn", "fonts.googleapis.com", "fonts.gstatic.com",
)

# 这些域发的是带 x-expires 的临时签名链接，会过期
EXPIRING_HOSTS = ("doubaocdn.com", "byteimg.com")

HOST_RE = re.compile(r"^(?://|https?://)([^/?#]+)", re.IGNORECASE)


def host_of(ref: str) -> str:
    m = HOST_RE.match(ref.strip())
    return m.group(1).lower() if m else ""

SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*:")

# 这些 scheme 本身就是内联/非文件，不动
NON_FILE_SCHEMES = ("data:", "blob:", "javascript:", "mailto:", "tel:", "about:", "cid:")

# 值里出现这些属性名就尝试内嵌
URL_ATTRS = {
    "src", "srcset", "poster",
    "data-src", "data-srcset", "data-original", "data-bg", "data-background",
}

# 这些标签上的 src 不能内嵌（子文档 / 外链脚本）
SRC_VETO_TAGS = {"script", "iframe", "frame", "embed", "object", "portal"}

VETO_REASON = {
    "script": "external_js_not_inlined",
    "iframe": "subdocument_not_embedded",
    "frame": "subdocument_not_embedded",
    "embed": "subdocument_not_embedded",
    "object": "subdocument_not_embedded",
    "portal": "subdocument_not_embedded",
}

# <link rel> 里可以内嵌的（图标类）
ICON_RELS = {"icon", "shortcut icon", "apple-touch-icon", "apple-touch-icon-precomposed", "mask-icon"}

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".svg", ".bmp", ".ico", ".tif", ".tiff"}

# 魔术字节 → MIME。下载来的图片经常后缀不对，嗅探比看后缀可靠
MAGIC = [
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
    (b"BM", "image/bmp"),
    (b"\x00\x00\x01\x00", "image/x-icon"),
    (b"\x00\x00\x02\x00", "image/x-icon"),
    (b"wOFF", "font/woff"),
    (b"wOF2", "font/woff2"),
    (b"OTTO", "font/otf"),
    (b"ttcf", "font/collection"),
    (b"\x00\x01\x00\x00", "font/ttf"),
    (b"true", "font/ttf"),
    (b"II*\x00", "image/tiff"),
    (b"MM\x00*", "image/tiff"),
    (b"%PDF-", "application/pdf"),
]

DEFAULT_WARN_TOTAL = 5 * 1024 * 1024  # 输出超过这个体积就在报告里告警


# ---------------------------------------------------------------- 小工具


def sniff_mime(head: bytes, path: Path) -> str:
    """先嗅探魔术字节，再退回后缀，最后 octet-stream。"""
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    if head[4:8] == b"ftyp":
        brand = head[8:12]
        if brand in (b"avif", b"avis"):
            return "image/avif"
        if brand in (b"heic", b"heix", b"hevc", b"mif1"):
            return "image/heic"
        if brand in (b"mp42", b"isom", b"iso2", b"mp41", b"M4V "):
            return "video/mp4"
    for magic, mime in MAGIC:
        if head.startswith(magic):
            return mime
    probe = head[:1024].lstrip()
    if probe.startswith(b"<?xml") or probe.startswith(b"<svg") or b"<svg" in head[:1024]:
        return "image/svg+xml"

    guessed, _ = mimetypes.guess_type(path.name)
    if guessed:
        return guessed
    return "application/octet-stream"


def is_within(child: Path, parent: Path) -> bool:
    """child 是否在 parent 目录树内（已 resolve，因此符号链接指向外部也会被判 False）。"""
    try:
        c, p = str(child.resolve()), str(parent.resolve())
    except Exception:
        return False
    try:
        return os.path.commonpath([c, p]) == p
    except ValueError:  # Windows 不同盘符
        return False


def decode_html(raw: bytes):
    """返回 (text, encoding_name, bom)。保留原编码，写回时用同一种。"""
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw[3:].decode("utf-8", "replace"), "utf-8", b"\xef\xbb\xbf"
    if raw.startswith(b"\xff\xfe"):
        return raw.decode("utf-16"), "utf-16", b""
    if raw.startswith(b"\xfe\xff"):
        return raw.decode("utf-16"), "utf-16", b""
    for enc in ("utf-8", "gb18030"):
        try:
            return raw.decode(enc), enc, b""
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1"), "latin-1", b""


def fmt_size(n: int) -> str:
    if n < 1024:
        return f"{n}B"
    if n < 1024 * 1024:
        return f"{n / 1024:.0f}KB"
    return f"{n / 1024 / 1024:.2f}MB"


def match_paren(text: str, open_at: int, limit: int = 20000) -> int:
    """从 open_at 处的 '(' 找到配对的 ')'，跳过引号内部。找不到返回 -1。

    两道上界，防止 CSS 里出现未闭合括号时每个 image-set( 都扫到文件末尾
    （N 个未闭合 → O(N × 文件长度)，实测 0.2MB / 4000 个要 24s）：
      - 遇到 '}' 立即停：CSS 函数值不可能跨过所属声明块的右花括号；
      - 最多向前看 limit 个字符，给没有花括号的场景（如 style="" 属性）兜底。
    """
    depth, i = 0, open_at
    n = min(len(text), open_at + limit)
    while i < n:
        c = text[i]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return i
        elif c == "}":
            return -1
        elif c in "\"'":
            q = c
            i += 1
            while i < n and text[i] != q:
                i += 1
        i += 1
    return -1


# ---------------------------------------------------------------- 核心


class Embedder:
    def __init__(self, html_path: Path, opts):
        self.html_path = html_path
        self.base_dir = html_path.parent
        self.opts = opts
        self.cache = {}          # realpath -> data uri（同一文件只编码一次）
        self.assets = {}         # realpath -> 资产记录
        self.missing = {}        # ref -> 记录
        self.skipped = {}        # (ref, reason) -> 记录
        self.remote = {}         # ref -> 次数
        self.warnings = []
        self.replaced = 0

    # ---- 记账

    def _note_skip(self, ref, reason, where, extra=None):
        key = (ref, reason)
        rec = self.skipped.get(key)
        if rec is None:
            rec = {"ref": ref[:300], "reason": reason, "where": where, "uses": 0}
            if extra:
                rec.update(extra)
            self.skipped[key] = rec
        rec["uses"] += 1

    def _note_missing(self, ref, resolved, where):
        rec = self.missing.get(ref)
        if rec is None:
            rec = {"ref": ref[:300], "resolved": str(resolved), "where": where, "uses": 0}
            self.missing[ref] = rec
        rec["uses"] += 1

    # ---- 引用 → data URI

    def resolve(self, ref: str):
        """把引用解析成本地文件路径。返回 (path, None) 或 (None, reason)。"""
        s = ref.strip()
        if not s:
            return None, "empty"
        low = s.lower()
        if low.startswith(NON_FILE_SCHEMES):
            return None, "already_inline" if low.startswith("data:") else "non_file_scheme"
        if s.startswith("#"):
            return None, "fragment_only"
        if s.startswith("//"):
            return None, "remote"

        if low.startswith("file:"):
            parsed = urlparse(s)
            p = unquote(parsed.path)
            if os.name == "nt" and re.match(r"^/[a-zA-Z]:", p):
                p = p[1:]
            return Path(p), None

        if SCHEME_RE.match(s):
            return None, "remote"

        # 去掉 query / fragment
        frag = ""
        if "#" in s:
            s, frag = s.split("#", 1)
        if "?" in s:
            s = s.split("?", 1)[0]
        if not s:
            return None, "fragment_only"

        s = unquote(s).replace("\\", "/")
        if frag and s.lower().endswith(".svg"):
            return None, "svg_fragment"

        p = Path(s)
        if not p.is_absolute():
            p = self.base_dir / p
        return p, None

    def data_uri(self, ref: str, where: str):
        """返回 data URI；返回 None 表示这条引用不改写（原因已记账）。"""
        path, reason = self.resolve(ref)
        if reason == "remote":
            self.remote[ref[:300]] = self.remote.get(ref[:300], 0) + 1
            self._note_skip(ref, "remote_url", where)
            return None
        if reason:
            if reason not in ("already_inline", "fragment_only", "empty"):
                self._note_skip(ref, reason, where)
            return None

        try:
            real = path.resolve()
        except Exception:
            self._note_missing(ref, path, where)
            return None

        if real in self.cache:
            self.assets[real]["uses"] += 1
            self.replaced += 1
            return self.cache[real]

        if not real.is_file():
            self._note_missing(ref, real, where)
            return None

        if not self.opts.allow_outside and not is_within(real, self.base_dir):
            self._note_skip(ref, "outside_base_dir", where, {"resolved": str(real)})
            return None

        try:
            size = real.stat().st_size
        except OSError as e:
            self._note_skip(ref, "unreadable", where, {"detail": str(e)[:200]})
            return None

        if self.opts.max_file_bytes and size > self.opts.max_file_bytes:
            self._note_skip(ref, "too_large", where, {"bytes": size})
            return None

        try:
            raw = real.read_bytes()
        except OSError as e:
            self._note_skip(ref, "unreadable", where, {"detail": str(e)[:200]})
            return None

        if not raw:
            self._note_skip(ref, "empty_file", where)
            return None

        mime = sniff_mime(raw[:64], real)
        uri = "data:%s;base64,%s" % (mime, base64.b64encode(raw).decode("ascii"))
        self.cache[real] = uri
        self.assets[real] = {
            "ref": ref[:300],
            "file": str(real),
            "bytes": len(raw),
            "base64Bytes": len(uri),
            "mime": mime,
            "uses": 1,
        }
        self.replaced += 1
        return uri

    def srcset_value(self, value: str, where: str):
        """改写 srcset。已含 data: 的整条不动，避免按逗号切坏 data URI。"""
        if "data:" in value.lower():
            self._note_skip(value[:80], "srcset_contains_data_uri", where)
            return None
        parts, changed = [], False
        for chunk in value.split(","):
            stripped = chunk.strip()
            if not stripped:
                continue
            bits = stripped.split(None, 1)
            url = bits[0]
            desc = (" " + bits[1].strip()) if len(bits) > 1 else ""
            uri = self.data_uri(url, where)
            if uri:
                changed = True
                parts.append(uri + desc)
            else:
                parts.append(stripped)
        return ", ".join(parts) if changed else None

    def css_text(self, text: str, offset: int, where: str, edits: list):
        """处理一段 CSS 里所有 url(...) 与 image-set(...)，把编辑塞进 edits。"""
        for m in CSS_URL_RE.finditer(text):
            raw = m.group(1) or m.group(2) or m.group(3) or ""
            raw = raw.strip()
            if not raw:
                continue
            uri = self.data_uri(raw, where)
            if uri:
                # 整个 url(...) 一起换掉，顺手把引号规范成双引号
                edits.append((offset + m.start(), offset + m.end(), 'url("%s")' % uri))
        self.image_set(text, offset, where, edits)

    def image_set(self, text: str, offset: int, where: str, edits: list):
        """image-set() / -webkit-image-set() 里的**裸字符串候选**。

        只改裸字符串——`url(...)` 形态交给 CSS_URL_RE，两者的 span 天然不相交，
        不会在 _apply 里撞成重叠编辑。`type("image/avif")` 这类描述符也不能碰，
        判据是「紧邻的前一个非空字符必须是 image-set 自己的开括号或逗号」。
        """
        for m in IMAGE_SET_RE.finditer(text):
            open_at = m.end() - 1
            close_at = match_paren(text, open_at)
            if close_at < 0:
                continue
            inner = text[open_at + 1:close_at]
            base = offset + open_at + 1
            for sm in QUOTED_RE.finditer(inner):
                prev = inner[:sm.start()].rstrip()
                if prev and not prev.endswith(","):
                    continue          # url( / type( 里面的，跳过
                ref = sm.group(2).strip()
                if not ref:
                    continue
                uri = self.data_uri(ref, where + " image-set")
                if uri:
                    edits.append((base + sm.start(2), base + sm.end(2), uri))

    # ---- 主流程

    def run(self, text: str) -> str:
        edits = []
        regions = []
        for m in REGION_RE.finditer(text):
            head = m.group(0)[:7].lower()
            kind = "comment" if head.startswith("<!--") else ("script" if head.startswith("<script") else "style")
            regions.append((m.start(), m.end(), kind, m.group(0)))

        cursor = 0
        for start, end, kind, body in regions:
            if start > cursor:
                self._scan_tags(text, cursor, start, edits)
            inner_start = body.find(">") + 1
            if kind in ("style", "script") and inner_start > 0:
                # 开标签本身仍要过一遍：<script src="x.js"> 这类引用需要被记账
                self._scan_tags(text, start, start + inner_start, edits)
            if kind == "style":
                inner_end = body.lower().rfind("</style")
                if inner_start > 0 and inner_end > inner_start:
                    self.css_text(body[inner_start:inner_end], start + inner_start, "style block", edits)
            elif kind == "script":
                if inner_start > 0:
                    inner_end = body.lower().rfind("</script")
                    if inner_end > inner_start:
                        self._scan_script(body[inner_start:inner_end], start + inner_start, edits)
            cursor = end
        if cursor < len(text):
            self._scan_tags(text, cursor, len(text), edits)

        return self._apply(text, edits)

    def _scan_script(self, text: str, offset: int, edits: list):
        """<script> 里的资源引用——**只检测、从不改写**。

        为什么不改：同一个字符串在 JS 里可能是资源地址，也可能是下载名、显示名、
        localStorage 键、比较用的常量（真实语料里 download / name / children / value
        这些键名占了多数）。零依赖下无法可靠区分，改错是静默破坏（报告显示成功，
        交付后才炸），漏改只是裂图（自检截图看得见）。所以这个两难不由脚本裁决，
        而是报出来交给模型处理。

        edits 参数保留但不写入——签名与其它 _scan_* 保持一致。
        """
        for m in SCRIPT_STR_RE.finditer(text):
            ref = m.group(2)
            path, reason = self.resolve(ref)
            if reason or path is None:
                continue
            try:
                if not path.resolve().is_file():
                    continue
            except Exception:
                continue
            left = text[max(0, m.start() - 200):m.start()]
            url_like = bool(SCRIPT_URL_CTX_RE.search(left) or SCRIPT_SETATTR_CTX_RE.search(left))
            self._note_skip(ref,
                            "script_literal_url_like" if url_like else "script_literal_not_url_like",
                            "script literal")

        # 豆包 CDN / byteimg 临时签名链没有图片后缀，上面那条正则抓不到，单独扫
        for m in SCRIPT_REMOTE_RE.finditer(text):
            ref = m.group(2)
            self.remote[ref[:300]] = self.remote.get(ref[:300], 0) + 1
            self._note_skip(ref, "remote_url", "script literal")

    def _scan_tags(self, text: str, lo: int, hi: int, edits: list):
        for m in TAG_RE.finditer(text, lo, hi):
            tag = m.group(1).lower()
            chunk = m.group(2)
            if not chunk:
                continue
            chunk_off = m.start(2)

            attrs = {}
            for a in ATTR_RE.finditer(chunk):
                name = a.group(1).lower()
                val = a.group(3) if a.group(3) is not None else (
                    a.group(4) if a.group(4) is not None else (a.group(5) or "")
                )
                attrs.setdefault(name, val)
            rel = (attrs.get("rel") or "").strip().lower()

            for a in ATTR_RE.finditer(chunk):
                name = a.group(1).lower()
                if a.group(3) is not None:
                    vi, quote = 3, '"'
                elif a.group(4) is not None:
                    vi, quote = 4, "'"
                else:
                    vi, quote = 5, ""
                value = a.group(vi)
                if value is None:
                    continue
                vstart, vend = chunk_off + a.start(vi), chunk_off + a.end(vi)

                # style="" 里的 url()
                if name == "style":
                    self.css_text(value, vstart, "%s@style" % tag, edits)
                    continue

                new = self._attr_value(tag, name, rel, value)
                if new is None:
                    continue
                # 无引号的属性值统一补上双引号，data URI 才不会被解析歧义
                if quote:
                    edits.append((vstart, vend, new))
                else:
                    edits.append((vstart, vend, '"%s"' % new))

    def _attr_value(self, tag: str, name: str, rel: str, value: str):
        where = "%s@%s" % (tag, name)

        if name in ("href", "xlink:href"):
            if tag == "image":
                pass                       # SVG <image href>，可内嵌
            elif tag == "use":
                if value.strip() and not value.strip().startswith("#"):
                    self._note_skip(value, "svg_sprite_use", where)
                return None
            elif tag == "link":
                if rel in ICON_RELS:
                    pass
                elif rel == "stylesheet":
                    if value.strip() and not SCHEME_RE.match(value.strip()):
                        self._note_skip(value, "external_css_not_inlined", where)
                    return None
                else:
                    return None            # preload / manifest / prefetch 等，内嵌无意义
            else:
                # <a href> / <area href> 不内嵌，但如果指向真实存在的本地**附件**，
                # 说明这是个下载链接——单文件交付后会失效，必须报出来。
                # 排除 .html/.htm（那是页内或跨页导航，不是附件）和指向自身的链接。
                if tag in ("a", "area"):
                    p, why = self.resolve(value)
                    if p is not None and not why and p.suffix.lower() not in (".html", ".htm", ".xhtml"):
                        try:
                            rp = p.resolve()
                            if rp.is_file() and rp != self.html_path.resolve():
                                self._note_skip(value, "local_download_link", where)
                        except OSError:
                            pass
                return None
        elif name in URL_ATTRS:
            if name in ("src", "data-src") and tag in SRC_VETO_TAGS:
                if value.strip() and not SCHEME_RE.match(value.strip()):
                    self._note_skip(value, VETO_REASON.get(tag, "not_embeddable"), where)
                return None
        else:
            return None

        if name in ("srcset", "data-srcset"):
            return self.srcset_value(value, where)
        return self.data_uri(value, where)

    @staticmethod
    def _apply(text: str, edits: list) -> str:
        if not edits:
            return text
        edits.sort(key=lambda e: (e[0], e[1]))
        out, last = [], 0
        for start, end, new in edits:
            if start < last:      # 理论上不会重叠；真重叠了宁可丢弃也不产出坏 HTML
                continue
            out.append(text[last:start])
            out.append(new)
            last = end
        out.append(text[last:])
        return "".join(out)


# ---------------------------------------------------------------- CLI


def _fail_json(code: int, message: str, err_code="invalid_argument"):
    print(json.dumps({"error": {"code": err_code, "message": message}}, ensure_ascii=False, indent=2))
    sys.exit(code)


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("html", help="要处理的 HTML 路径")
    ap.add_argument("-o", "--out", help="输出路径，默认 <stem>_embed<suffix>")
    ap.add_argument("--dry-run", action="store_true", help="只报告不写文件")
    ap.add_argument("--allow-outside", action="store_true",
                    help="允许内嵌 HTML 所在目录之外的文件（默认跳过并告警）")
    ap.add_argument("--max-file-bytes", type=int, default=0,
                    help="单个文件超过该字节数就跳过；0 表示不限制（默认）")
    ap.add_argument("--warn-total-bytes", type=int, default=DEFAULT_WARN_TOTAL,
                    help="输出超过该字节数就在报告里告警，默认 5MiB")
    ap.add_argument("--force", action="store_true",
                    help="允许对已经是 _embed 产物的文件再跑一次")
    args = ap.parse_args()

    t0 = time.time()

    src = Path(args.html)
    if not src.exists():
        _fail_json(2, "文件不存在: %s" % src)
    if not src.is_file():
        _fail_json(2, "不是文件: %s" % src)

    if src.stem.endswith("_embed") and not args.force:
        _fail_json(2,
                   "输入 %s 本身就是内嵌产物。请对原始 HTML 运行本脚本——"
                   "_embed.html 是一次性派生产物，不要在它上面改。确需重跑加 --force。" % src.name,
                   err_code="input_is_embedded")

    out = Path(args.out) if args.out else src.with_name("%s_embed%s" % (src.stem, src.suffix or ".html"))
    try:
        if out.exists() and out.resolve() == src.resolve():
            _fail_json(2, "输出路径和输入相同: %s" % out)
    except OSError:
        pass

    try:
        raw = src.read_bytes()
    except OSError as e:
        _fail_json(2, "读不了输入文件: %s\n%s" % (src, e))

    result = {
        "src": str(src),
        "out": str(out),
        "dryRun": bool(args.dry_run),
    }

    try:
        text, encoding, bom = decode_html(raw)
        result["encoding"] = encoding

        emb = Embedder(src, args)
        new_text = emb.run(text)

        payload = bom + new_text.encode(encoding, "xmlcharrefreplace")

        assets = sorted(emb.assets.values(), key=lambda a: -a["bytes"])
        result.update({
            "embedded": emb.replaced,
            "uniqueFiles": len(assets),
            "bytesIn": len(raw),
            "bytesOut": len(payload),
            "assetBytes": sum(a["bytes"] for a in assets),
            "assets": assets,
            "missing": sorted(emb.missing.values(), key=lambda r: r["ref"]),
            "skipped": sorted(emb.skipped.values(), key=lambda r: (r["reason"], r["ref"])),
            "remoteRefs": sorted(emb.remote.keys()),
        })

        warnings = list(emb.warnings)
        if result["missing"]:
            n = sum(r["uses"] for r in result["missing"])
            warnings.append(
                "有 %d 处引用找不到对应文件（%d 个不同路径），这些位置在交付页面里会是裂图。"
                "先把文件补齐或改正路径，再重新 embed。" % (n, len(result["missing"]))
            )
        if len(payload) > args.warn_total_bytes:
            top = "、".join("%s(%s)" % (Path(a["file"]).name, fmt_size(a["bytes"])) for a in assets[:5])
            warnings.append(
                "输出 %s，超过 %s 阈值。体积大头：%s。"
                "内嵌后体积约为原图 1.37 倍，过大的页面可能交付失败——考虑压缩或减少图片。"
                % (fmt_size(len(payload)), fmt_size(args.warn_total_bytes), top)
            )
        # 远程引用：按域名分档。SKILL.md 指定的库/字体域不报，临时签名链最优先报。
        expiring, other_remote = [], []
        for ref in result["remoteRefs"]:
            h = host_of(ref)
            if any(h == s or h.endswith("." + s) for s in SANCTIONED_HOSTS):
                continue
            (expiring if any(e in h for e in EXPIRING_HOSTS) else other_remote).append(ref)
        if expiring:
            warnings.append(
                "有 %d 处资源用的是临时签名链接（%s）。这类链接几天到几周后就会失效，"
                "届时已经交付出去的页面会全部裂图，而且用户手上的文件无法补救。"
                "**必须先把它们下载到 `assets/` 目录，在 HTML 里改成相对路径引用"
                "（如 `<img src=\"assets/hero.jpg\">`），然后重新跑本脚本。**"
                % (len(expiring), "、".join(sorted({host_of(r) for r in expiring})))
            )
        if other_remote:
            warnings.append(
                "有 %d 处资源是远程 URL（%s），未被内嵌。单文件交付后这些位置依赖外网，"
                "离线或换网络环境就打不开。要真正自包含，先下载到 `assets/` 再重新跑本脚本。"
                % (len(other_remote), "、".join(sorted({host_of(r) for r in other_remote})[:5]))
            )

        url_like = [r for r in result["skipped"] if r["reason"] == "script_literal_url_like"]
        if url_like:
            refs = "、".join(r["ref"] for r in url_like[:5])
            warnings.append(
                "`<script>` 里有 %d 处本地图片路径（%s）看起来是资源引用。本脚本不改写 JS 代码——"
                "同样的字符串也可能是下载名、显示名或用于比较的常量，改了会静默出错。"
                "这些位置在单文件交付后会裂图，需要你自己处理：把路径挪到 HTML 属性或 CSS `url()` 里"
                "（推荐，改完重跑本脚本即可），或在 JS 里直接写成 data URI。"
                % (len(url_like), refs)
            )
        # 按原因合并同类项。一个 React 工程会有十几个 <script src="src/xxx.jsx">，
        # 逐条报等于把真正要紧的那条告警冲掉。
        NOISY_REASONS = {
            "external_js_not_inlined": "外链 JS",
            "external_css_not_inlined": "外链 CSS",
            "subdocument_not_embedded": "子文档引用（iframe / embed / object）",
            "svg_sprite_use": "SVG sprite（<use>）",
            "svg_fragment": "带 #fragment 的 SVG",
            "outside_base_dir": "HTML 所在目录之外的文件",
            "too_large": "超过 --max-file-bytes 上限的文件",
            "unreadable": "读不了的文件",
            "empty_file": "空文件",
            "local_download_link": "指向本地附件的下载链接",
        }
        grouped = {}
        for rec in result["skipped"]:
            if rec["reason"] in NOISY_REASONS:
                grouped.setdefault(rec["reason"], []).append(rec["ref"])
        for reason in sorted(grouped):
            refs = grouped[reason]
            warnings.append(
                "跳过 %d 处%s（%s%s）——这些引用没有被内嵌，在单文件交付里会失效。"
                % (len(refs), NOISY_REASONS[reason], "、".join(refs[:3]),
                   " 等" if len(refs) > 3 else "")
            )
        if (emb.replaced == 0 and not result["missing"]
                and not result["remoteRefs"] and not result["skipped"]):
            # 只在「确实什么资源引用都没扫到」时才说这句。
            # 如果有远程链接或被跳过的项，上面已经给出了更准确的原因，
            # 再说一句「检查 src 路径是否写对」只会和它们互相矛盾。
            warnings.append("没有找到任何可内嵌的本地资源引用。如果页面本该有图，检查 src 路径是否写对。")
        result["warnings"] = warnings

        if not args.dry_run:
            tmp = out.with_name(out.name + ".tmp%d" % os.getpid())
            try:
                # mkdir 必须和写入放在同一个 try 里：父目录创建失败（路径上有普通文件、
                # 目录不可写）属于文档里 exit 2 承诺的「输出不可写」，
                # 漏在外面会被兜底 except 归成 unexpected/exit 3。
                out.parent.mkdir(parents=True, exist_ok=True)
                tmp.write_bytes(payload)
                os.replace(str(tmp), str(out))
            except OSError as e:
                try:
                    tmp.unlink()
                except OSError:
                    pass
                result["error"] = {"code": "write_failed", "message": "%s: %s" % (out, e)}
                result["elapsedSec"] = round(time.time() - t0, 2)
                print(json.dumps(result, ensure_ascii=False, indent=2))
                return 2

    except Exception as e:  # 兜底：任何未预期异常也走 JSON 通道
        result["error"] = {"code": "unexpected", "message": ("%s: %s" % (type(e).__name__, e))[:1000]}
        result["elapsedSec"] = round(time.time() - t0, 2)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 3

    result["elapsedSec"] = round(time.time() - t0, 2)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
