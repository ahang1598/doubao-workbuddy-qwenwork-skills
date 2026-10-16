"""Optional text wrapping; no shrinking, templates or implicit placement."""

from __future__ import annotations

import unicodedata
from functools import lru_cache
from ._geometry import label, _finite
from ._help import _drawing_api


def _clusters(text):
    groups = []
    for char in text:
        if groups and (
            unicodedata.combining(char) or char in ("\u200d", "\ufe0f", "\ufe0e") or groups[-1].endswith("\u200d")
        ):
            groups[-1] += char
        else:
            groups.append(char)
    return groups


@_drawing_api(
    "shapes",
    purpose="在明确宽度内换行生成文字几何。",
    returns="Geometry",
    semantics=(
        "max_width/font_size 使用源 SVG 单位；保留显式换行，折行处去掉空白，不缩小字号或截断内容。",
        "优先在空白和汉字之间换行；break_long_words=True 时可拆过长单词，组合附加符号不拆开。",
        "沿用 label 的字体测量与估算回退；单个不可拆字符组过宽时会报错。",
    ),
    example="note = wrap_label(text, max_width=width, font_size=size, **paint)",
    limits=("不是完整浏览器排版引擎；字形、连字及服务端替代字体仍影响实际宽度。",),
    style=True,
    common=False,
)
def wrap_label(content, *, max_width, font_size, font_family=None, line_height=None, break_long_words=True, **style):
    _finite(max_width, font_size)
    if max_width <= 0 or font_size <= 0:
        raise ValueError("Text width and font size must be positive")
    content = str(content)
    if len(content) > 20000:
        raise ValueError("Wrapped label exceeds 20000 characters")

    @lru_cache(maxsize=1024)
    def width(text):
        return label(text, font_size=font_size, font_family=font_family, line_height=line_height, **style).bounds.width

    lines = []
    opening = "（［｛《〈【「『“‘(["
    closing = "，。！？；：、）］｝》〉】」』”’)]"
    for paragraph in content.split("\n"):
        clusters = _clusters(paragraph)
        if not clusters:
            lines.append("")
            continue
        while clusters:
            fits = 0
            legal = []
            for end in range(1, len(clusters) + 1):
                candidate = "".join(clusters[:end]).rstrip()
                if width(candidate) > max_width + 1e-9:
                    break
                fits = end
                prev = clusters[end - 1]
                nxt = clusters[end] if end < len(clusters) else ""
                if (
                    (prev.isspace() or unicodedata.east_asian_width(prev[0]) in ("W", "F") or prev in "-/")
                    and prev not in opening
                    and (not nxt or nxt not in closing)
                ):
                    legal.append(end)
            if fits == len(clusters):
                lines.append("".join(clusters).rstrip())
                break
            if fits == 0:
                raise ValueError("A character cluster is wider than max_width")
            end = legal[-1] if legal else fits
            if not legal and not break_long_words:
                raise ValueError("A word is wider than max_width")
            lines.append("".join(clusters[:end]).rstrip())
            clusters = clusters[end:]
            while clusters and clusters[0].isspace():
                clusters.pop(0)
    return label("\n".join(lines), font_size=font_size, font_family=font_family, line_height=line_height, **style)
