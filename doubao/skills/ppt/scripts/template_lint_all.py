#!/usr/bin/env python3
"""template_lint_all.py — template-editing 分支专用的聚合 lint 入口。

一次跑三项检查：
1. xml_lint.py                XML schema / 几何 / 溢出 / 重叠 / ID 唯一性等通用检查
2. color_contrast_check.py    文字靠色（默认阈值 2.25）
3. 占位符 diff                source-slides/slide-NN.xml 与 authored 相同文本片段 → warn

Step 5 每页写入前必跑：
    python3 template_lint_all.py \\
      --authored <authoring/slide-NN.xml> \\
      --source <source-slides/slide-NN.xml> \\
      --skill-root <SKILL_ROOT>

判定：任一子项 status=blocked（xml_lint 有 error / 靠色有 FAIL）→ overall status=blocked，
禁止 +add-slide / +update-slide。占位符 diff 只产 warn，不阻断写入，但要 MainAgent 判断是否漏改。

stdout：JSON envelope，含 summary + 三项子结果 + 占位符 diff 详情。
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


# 占位符黑名单（命中就是 warn，且 message 带明确"疑似占位符"标签）
PLACEHOLDER_BLACKLIST = [
    "添加标题", "点击输入", "点击此处", "占位", "占位符",
    "示例文本", "示例文字", "示例内容", "示例",
    "Lorem ipsum", "Lorem", "Click to add", "Add title",
    "Add subtitle", "Add text", "Placeholder", "Sample text",
    "asdas", "想搞设计", "论文就是用来",
    "亮亮图文", "淘宝",
    "副标题",
]

# 模板骨架 label 白名单（命中就降级为 info、不报 warn；这些是模板设计的一部分保留合理）
SKELETON_WHITELIST = {
    # 通用骨架 label
    "目录", "章节", "内容", "标题", "副标题内容",
    "页脚", "页眉", "关键词", "备注",
    # 常见英文对照
    "CONTENTS", "OUTLINE", "AGENDA", "CHAPTER", "SECTION",
    "TITLE", "SUBTITLE", "OVERVIEW", "INTRODUCTION", "CONCLUSION",
    "APPENDIX", "REFERENCE", "REFERENCES", "THANKS", "THANK YOU",
    "BACKGROUND", "METHOD", "METHODS", "RESULTS", "DISCUSSION",
    # 通用装饰词（长度 >=4 但没意义）
    "SLIDE", "PAGE", "PART", "STEP",
}

# 中文常见极短装饰（<4 会被长度过滤掉，这里覆盖恰好 4 字的）
SKELETON_WHITELIST |= {"研究背景", "研究方法", "研究框架", "研究结论"}


def _extract_texts(xml_path: Path) -> list[str]:
    """从 XML 里抽出所有 <a:t> / <t> / text() 文本，做基本清洗后返回。"""
    if not xml_path.exists():
        return []
    try:
        tree = ET.parse(str(xml_path))
    except ET.ParseError:
        return []
    root = tree.getroot()
    texts: list[str] = []
    for elem in root.iter():
        tag = elem.tag.rsplit("}", 1)[-1]
        if tag == "t" and elem.text:
            t = elem.text.strip()
            if t:
                texts.append(t)
    return texts


def _is_meaningful_text(t: str) -> bool:
    """判断文本是否有意义（有内容差异检查的价值）。"""
    if len(t) < 4:
        return False
    # 纯数字
    if re.fullmatch(r"[\d\s.,%]+", t):
        return False
    # 纯符号
    if re.fullmatch(r"[\W_]+", t):
        return False
    return True


def _classify_common_text(t: str) -> tuple[str, str]:
    """把 source/authored 都出现的文本分类，返回 (severity, reason).

    severity ∈ {"info", "warn"}
    reason 描述为什么这样判定。
    """
    # 黑名单 → warn
    for kw in PLACEHOLDER_BLACKLIST:
        if kw in t:
            return "warn", f"疑似占位符（命中黑名单词 '{kw}'）——MainAgent 忘了替换成实际内容"
    # 白名单精确匹配 → info（不报）
    if t in SKELETON_WHITELIST or t.upper() in SKELETON_WHITELIST:
        return "info", "模板骨架 label，保留合理"
    # 其他 → warn
    return "warn", "该文本在模板 source 和 authored 中都出现且未修改——可能是漏改的原文，也可能是模板设计要保留的部分，请 MainAgent 判断"


def check_placeholders(source_xml: Path, authored_xml: Path) -> dict:
    """做 source vs authored 的相同文本 diff，返回 warning 清单。"""
    source_texts = set(_extract_texts(source_xml))
    authored_texts = _extract_texts(authored_xml)

    common: list[dict] = []
    seen: set[str] = set()
    for t in authored_texts:
        if t in seen:
            continue
        if t not in source_texts:
            continue
        if not _is_meaningful_text(t):
            continue
        seen.add(t)
        severity, reason = _classify_common_text(t)
        common.append({"text": t, "severity": severity, "reason": reason})

    warn_count = sum(1 for c in common if c["severity"] == "warn")
    info_count = sum(1 for c in common if c["severity"] == "info")

    return {
        "checked": True,
        "warning_count": warn_count,
        "info_count": info_count,
        "issues": common,
        "note": (
            "warn = source-slides 和 authoring 中都出现且未修改的文本，可能是漏改的占位内容。"
            "如果确实是模板骨架 label（如'目录'、'CONTENTS'），可忽略；否则 MainAgent 必须去 Edit authoring 改掉。"
        ),
    }


def _run_subscript(script_path: Path, args: list[str], timeout: int = 60) -> dict:
    """跑一个子脚本，返回 {ok, stdout_json, stderr, returncode}."""
    cmd = ["python3", str(script_path)] + args
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"timeout after {timeout}s"}
    except FileNotFoundError as e:
        return {"ok": False, "error": f"script not found: {e}"}

    out = proc.stdout.strip()
    idx = out.find("{")
    parsed = None
    if idx >= 0:
        try:
            parsed = json.loads(out[idx:])
        except json.JSONDecodeError:
            parsed = None
    # ok 判定收紧:必须 returncode=0 且 stdout 是合法 JSON(避免 rc!=0 时只要有一段 '{' 就当成功)
    ok = (proc.returncode == 0) and (parsed is not None)
    return {
        "ok": ok,
        "returncode": proc.returncode,
        "stdout_json": parsed,
        "stderr": proc.stderr[:500],
    }


def check_overflow_covers_below(authored_xml: Path, xml_lint_json: dict | None) -> dict:
    """检查"文本 A 溢出后是否几何覆盖同页其他 shape B"。

    两条路径：
    (1) xml_lint 已经报了 text_overflows_container 的场景——直接从 related_objects 拿 bbox 和 overflow.bottom
    (2) 兜底：任何含文本的 shape（含 rect 塞正文这种），自己估算 estimated_height，
        与 declared height 对比。这条路径覆盖 xml_lint 漏掉的场景。

    返回 {checked, fail_count, issues}。fail_count > 0 时 status=blocked。
    """
    # 从 authored XML 抽同页所有 shape 的 bbox
    try:
        tree = ET.parse(str(authored_xml))
        root = tree.getroot()
    except ET.ParseError:
        return {"checked": False, "reason": "authored xml parse failed", "fail_count": 0, "issues": []}

    def local(tag: str) -> str:
        return tag.rsplit("}", 1)[-1]

    # 找到每一页（如果整份 XML 有 <presentation><slide>...）
    slides_nodes: list[ET.Element] = []
    root_local = local(root.tag)
    if root_local == "slide":
        slides_nodes = [root]
    elif root_local == "presentation":
        for child in root:
            if local(child.tag) == "slide":
                slides_nodes.append(child)
    else:
        slides_nodes = [root]

    issues: list[dict] = []

    for slide_idx, slide in enumerate(slides_nodes, start=1):
        # 抽本页所有 shape/img
        page_shapes: list[dict] = []
        for shp in slide.iter():
            if local(shp.tag) not in ("shape", "img"):
                continue
            try:
                x = float(shp.get("topLeftX") or shp.get("left") or 0)
                y = float(shp.get("topLeftY") or shp.get("top") or 0)
                w = float(shp.get("width") or 0)
                h = float(shp.get("height") or 0)
            except (TypeError, ValueError):
                continue
            if w <= 0 or h <= 0:
                continue
            sid = shp.get("id")
            # 抽文本 + font size（取第一个 span 或 content 的 fontSize）
            texts: list[str] = []
            font_sizes: list[float] = []
            for span in shp.iter():
                if local(span.tag) in ("span", "t") and (span.text or "").strip():
                    texts.append(span.text.strip())
                fs = span.get("fontSize")
                if fs:
                    try:
                        font_sizes.append(float(fs))
                    except (TypeError, ValueError):
                        pass
            text = "".join(texts)
            # 取"最常出现"或第一个非零 fontSize
            font_size = font_sizes[0] if font_sizes else 14.0
            # 估算行高（fontSize * 1.4）
            line_h = font_size * 1.4
            # 简易估算文本占的行数（按字符宽度 ~ 0.6 * fontSize，中文按 1 * fontSize）
            def _char_w(ch: str, fs: float) -> float:
                if '一' <= ch <= '鿿':  # 中日韩汉字
                    return fs * 1.0
                return fs * 0.55
            # 减去 padding
            avail_w = max(w - 14, 1)  # 左右各留 7 padding 估
            avail_h = max(h - 8, 1)   # 上下各留 4 padding 估
            if text:
                line_widths = 0.0
                lines = 1
                for ch in text:
                    cw = _char_w(ch, font_size)
                    if line_widths + cw > avail_w:
                        lines += 1
                        line_widths = cw
                    else:
                        line_widths += cw
                estimated_h = lines * line_h + 8  # + padding
            else:
                estimated_h = 0.0

            page_shapes.append({
                "id": sid,
                "type": shp.get("type") or local(shp.tag),
                "x": x, "y": y, "w": w, "h": h,
                "x_end": x + w, "y_end": y + h,
                "text": text[:80],
                "font_size": font_size,
                "estimated_h": estimated_h,
                "overflow_bottom": max(0.0, estimated_h - h),  # 兜底估算
            })

        # 从 xml_lint 的 slide 结果里拿"确定溢出"的框（更精确）
        xml_lint_overflows: dict[str, float] = {}  # id -> bottom_over
        if xml_lint_json and xml_lint_json.get("slides"):
            slides_from_lint = xml_lint_json["slides"]
            if slide_idx - 1 < len(slides_from_lint):
                for err in slides_from_lint[slide_idx - 1].get("errors", []):
                    if err.get("code") != "text_overflows_container":
                        continue
                    overflow = err.get("overflow") or err.get("measurement", {}).get("overflow") or {}
                    bottom_over = overflow.get("bottom", 0) or 0
                    if bottom_over <= 0:
                        continue
                    related = err.get("related_objects") or []
                    if related:
                        rid = related[0].get("element_id")
                        if rid:
                            xml_lint_overflows[rid] = max(xml_lint_overflows.get(rid, 0), bottom_over)

        # 对每个溢出的框（xml_lint 精确报的 OR 兜底估算的），与同页其他 shape 做相交
        for a in page_shapes:
            if not a.get("id"):
                continue  # 无 id 的 shape 跳过 · 避免全部聚合到 None key 误判
            # 兜底估算与 xml_lint 报的取较大
            precise = xml_lint_overflows.get(a["id"], 0)
            over = max(precise, a["overflow_bottom"])
            if over <= 2:  # <=2px 忽略
                continue
            a_y_real_end = a["y_end"] + over
            for b in page_shapes:
                if b["id"] == a["id"]:
                    continue
                # 水平必须相交
                if b["x_end"] <= a["x"] or b["x"] >= a["x_end"]:
                    continue
                # b 起点必须在 a 声明范围之下（不然是原生几何重叠，xml_lint 的 bbox_overlap 会报）
                if b["y"] < a["y_end"]:
                    continue
                # b 起点必须在 a 实际结束之上
                if b["y"] >= a_y_real_end:
                    continue
                # 纵向相交
                ovl_top = max(a["y_end"], b["y"])
                ovl_bot = min(a_y_real_end, b["y_end"])
                ovl_h = ovl_bot - ovl_top
                if ovl_h <= 2:
                    continue
                issues.append({
                    "severity": "fail",
                    "code": "text_overflow_covers_below",
                    "slide_number": slide_idx,
                    "overflowing_shape": a["id"],
                    "overflowing_shape_type": a["type"],
                    "overflowing_text": a["text"],
                    "covered_shape": b["id"],
                    "covered_shape_type": b["type"],
                    "covered_text": b["text"],
                    "overflow_bottom_px": round(over, 1),
                    "vertical_overlap_px": round(ovl_h, 1),
                    "source": "xml_lint" if precise > 0 else "heuristic_estimate",
                    "reason": (
                        f"slide {slide_idx} 文本框 {a['id']}（type={a['type']}, 高 {a['h']:.0f}px）"
                        f"估算需要 {a['h'] + over:.0f}px 才装得下'{a['text'][:30]}...'，"
                        f"溢出约 {over:.0f}px 向下覆盖到 {b['id']}（type={b['type']}, "
                        f"内容'{b['text'][:20]}...'）——两段文字会在渲染时挤成一团。"
                        f"修复：加大 {a['id']} 的 height、缩短文本、或把 {b['id']} 往下挪至少 {ovl_h:.0f}px。"
                    ),
                })

    return {
        "checked": True,
        "fail_count": len(issues),
        "issues": issues,
        "note": (
            "text_overflow_covers_below = 文本 A 因为 estimated_height > declared_height 溢出容器，"
            "溢出部分向下覆盖到同页其他独立 shape B。特别处理 rect 类型塞正文的场景（xml_lint 的 "
            "text_overflows_container 不覆盖这种）。命中即 FAIL，必须修复才能写入。"
        ),
    }


def check_unexpected_wrapping(authored_xml: Path) -> dict:
    """检查"文本被强制换行到多行"——单行框但文本估算宽度超容器可用宽度。

    典型场景：模板里的封面/署名/单行 label 文本框，宽度是"刚好装下预期文本"设计的；
    MainAgent 复用时新文本长了 1-2 个字，或者忘算 bullet marginLeft/indent 吃掉的可用宽度，
    结果实际渲染时被强制换行，最后 1 个字断到下一行——视觉上很难看。

    xml_lint 的 text_may_overflow_shape 只在 wrap="false" 时才报；默认 wrap 允许多行时它不报，
    但这些"意外换行"通常也是不该发生的（模板设计意图就是单行）。

    严重度：warn（启发式估算有 ±15% 误差，不宜阻断）。
    """
    try:
        tree = ET.parse(str(authored_xml))
        root = tree.getroot()
    except ET.ParseError:
        return {"checked": False, "reason": "authored xml parse failed", "warning_count": 0, "issues": []}

    def local(tag: str) -> str:
        return tag.rsplit("}", 1)[-1]

    # 找每一页
    slides_nodes: list[ET.Element] = []
    root_local = local(root.tag)
    if root_local == "slide":
        slides_nodes = [root]
    elif root_local == "presentation":
        for child in root:
            if local(child.tag) == "slide":
                slides_nodes.append(child)
    else:
        slides_nodes = [root]

    def _char_w(ch: str, fs: float) -> float:
        """启发式字宽估算（相对 fontSize）。"""
        code = ord(ch)
        # CJK 汉字（U+4E00-U+9FFF）
        if 0x4E00 <= code <= 0x9FFF:
            return fs * 1.0
        # 全角标点（U+3000-U+303F、U+FF00-U+FFEF 大部分）
        if 0x3000 <= code <= 0x303F or (0xFF01 <= code <= 0xFF5E and code >= 0xFF01):
            return fs * 1.0
        # 半角标点
        if ch in ".,;:!?()[]{}<>-'\"`~ ":
            return fs * 0.35
        # 数字
        if ch.isdigit():
            return fs * 0.55
        # 英文字母 / 其他
        return fs * 0.55

    def _estimate_line_widths(text: str, fs: float) -> float:
        """返回单行整体宽度（不考虑换行）。"""
        return sum(_char_w(ch, fs) for ch in text)

    issues: list[dict] = []

    for slide_idx, slide in enumerate(slides_nodes, start=1):
        for shp in slide.iter():
            if local(shp.tag) != "shape":
                continue
            stype = shp.get("type")
            if stype not in ("text",):
                # 只关心 type="text" shape；rect 塞正文由 overflow_covers_below 处理
                continue
            try:
                w = float(shp.get("width") or 0)
                h = float(shp.get("height") or 0)
            except (TypeError, ValueError):
                continue
            if w <= 0 or h <= 0:
                continue
            sid = shp.get("id")

            # 找 content 节点抽 padding / autoFit / wrap
            content = None
            for c in shp:
                if local(c.tag) == "content":
                    content = c; break
            if content is None:
                continue
            wrap = content.get("wrap")
            if wrap == "false":
                # wrap=false 场景 xml_lint 已经在管
                continue
            try:
                pad_left = float(content.get("paddingLeft") or 0)
                pad_right = float(content.get("paddingRight") or 0)
                pad_top = float(content.get("paddingTop") or 0)
                pad_bottom = float(content.get("paddingBottom") or 0)
            except (TypeError, ValueError):
                pad_left = pad_right = pad_top = pad_bottom = 0

            # 遍历 <p> 节点抽 marginLeft / indent + 文本 + fontSize
            # 每个 <p> 是独立段落，独立估算
            paragraphs: list[dict] = []
            for p in content.iter():
                if local(p.tag) != "p":
                    continue
                try:
                    p_margin_left = float(p.get("marginLeft") or 0)
                    p_indent = float(p.get("indent") or 0)
                except (TypeError, ValueError):
                    p_margin_left = p_indent = 0
                p_text = ""
                p_fs = None
                for sp in p.iter():
                    lname = local(sp.tag)
                    if lname == "span" and sp.text:
                        p_text += sp.text
                        if p_fs is None:
                            try:
                                p_fs = float(sp.get("fontSize") or 0) or None
                            except (TypeError, ValueError):
                                pass
                if not p_text.strip():
                    continue
                # fallback fontSize：content 上的
                if p_fs is None:
                    try:
                        p_fs = float(content.get("fontSize") or 14)
                    except (TypeError, ValueError):
                        p_fs = 14.0
                paragraphs.append({
                    "text": p_text,
                    "font_size": p_fs,
                    "margin_left": p_margin_left,
                    "indent": p_indent,
                })

            if not paragraphs:
                continue

            # 是否为 bullet list（多个 <li>）或普通段落——bullet dot 会再占约 fontSize 宽
            has_bullet = False
            for x in content.iter():
                if local(x.tag) == "li":
                    has_bullet = True; break

            # 对每段估算是否会换行
            for p_info in paragraphs:
                text = p_info["text"]
                fs = p_info["font_size"]
                margin_l = p_info["margin_left"]
                indent = p_info["indent"]
                bullet_indent = fs * 1.2 if has_bullet else 0
                avail_w = max(1.0, w - pad_left - pad_right - margin_l - indent - bullet_indent)
                line_w = _estimate_line_widths(text, fs)

                # 估算行高
                line_h = fs * 1.4

                # 声明可容纳的行数
                avail_h = max(1.0, h - pad_top - pad_bottom)
                declared_line_capacity = max(1, int(avail_h / line_h))

                # 估算实际需要的行数（math.ceil，line_w / avail_w 后向上取整）
                import math
                estimated_lines = max(1, math.ceil(line_w / avail_w))

                if line_w <= avail_w:
                    # 单行装得下
                    continue

                # 会换行
                severity = "warn"
                # 单行框（h 只能装 1 行）却需要多行 → 更严重的"文字会掉出框"
                if declared_line_capacity == 1 and estimated_lines > 1:
                    reason_short = "单行框强制换行——最后 1-2 个字会掉到下一行、超出框底部"
                elif estimated_lines > declared_line_capacity:
                    reason_short = f"文本估算需要 {estimated_lines} 行，但框只够 {declared_line_capacity} 行"
                else:
                    reason_short = f"文本估算需要 {estimated_lines} 行（模板设计意图可能是单行）"

                issues.append({
                    "severity": severity,
                    "slide_number": slide_idx,
                    "shape_id": sid,
                    "text": text[:60],
                    "font_size": fs,
                    "shape_width": round(w, 1),
                    "shape_height": round(h, 1),
                    "avail_width": round(avail_w, 1),
                    "estimated_line_width": round(line_w, 1),
                    "estimated_lines": estimated_lines,
                    "declared_line_capacity": declared_line_capacity,
                    "has_bullet": has_bullet,
                    "reason": (
                        f"slide {slide_idx} shape {sid} '{text[:30]}': "
                        f"估算行宽 {line_w:.0f}px > 可用宽 {avail_w:.0f}px（框宽 {w:.0f} - padding {pad_left+pad_right:.0f} "
                        f"- marginLeft {margin_l:.0f} - indent {indent:.0f}"
                        f"{' - bullet ' + f'{bullet_indent:.0f}' if has_bullet else ''}）。{reason_short}。"
                        f"修法：加宽 shape width、缩短文本、去掉 bullet/indent，或明确设 wrap=\"false\" 让 xml_lint 严格拦截。"
                    ),
                })

    return {
        "checked": True,
        "warning_count": len(issues),
        "issues": issues,
        "note": (
            "unexpected_wrapping = type=text shape 的正文估算宽度 > 可用宽度（考虑 padding/margin/indent/bullet），"
            "渲染时会强制换行——通常模板设计是单行 label，MainAgent 复用时新文本长了 1-2 个字就掉行。"
            "启发式估算 ±15% 误差，因此是 warn 不阻断；MainAgent 收到 warn 后看 reason 里的 estimated vs avail 数字判断是否需要改。"
        ),
    }


# ----- 稀疏度检测（防"页眉页脚 + 几段纯文字"的空稿）-----

# 视觉元素（非文字）标签：shape 里 type != "text" 的算视觉，img/embed/chart/icon/line/table 都算
VISUAL_TAGS = {"img", "embed", "chart", "icon", "line", "table"}
# 文字类元素标签
TEXT_TAGS = {"text"}
# 长段落判定阈值：单个 text shape 正文超过这么多字符算"长段落"
LONG_PARAGRAPH_CHAR_THRESHOLD = 80


def _shape_text_length(shape_node, local_fn) -> int:
    """取一个 shape 节点内所有文字的字符数总和。
    飞书 SXSD 的文字包在 <content><p><span>text</span></p></content>；
    pptx 原生用 <a:t>text</a:t>。两种都要扫。
    """
    total = 0
    for elem in shape_node.iter():
        # 拿元素自身的 text（不含子节点）
        if elem.text:
            s = elem.text.strip()
            if s:
                total += len(s)
        # elem.tail 是尾部文本（下一个兄弟节点前的文字），一般是空但也扫一下
        if elem.tail:
            s = elem.tail.strip()
            if s:
                total += len(s)
    return total



# ---------- 模板拷贝过拟合检测（active_rebuild 页专用） ----------

def check_template_copy_overfit(authored_path: Path, source_path: Path | None,
                                 page_role: str | None,
                                 threshold_ratio: float = 0.70) -> dict:
    """检测 authored 页是否照抄了 source 页的大部分 shape（模板生搬硬套）。

    只对 active_rebuild 页生效 —— fixed_template 页本来就是"保留版式只改文字"，
    shape id 大量复用是正常的。

    判定逻辑：
    - 提取 authored 页所有 shape/line/img/icon 的 id
    - 提取 source 页所有 shape/line/img/icon 的 id
    - shared_ratio = intersect(authored_ids, source_ids) / len(authored_ids)
    - shared_ratio > 0.70 → FAIL (模板拷贝过拟合)

    Returns:
        {
          "checked": bool,
          "reason": str (若 skipped),
          "authored_shape_count": int,
          "source_shape_count": int,
          "shared_id_count": int,
          "shared_ratio": float,
          "threshold": float,
          "status": "ok" | "blocked",
          "fail_count": 0 or 1,
          "issues": [...]
        }
    """
    result = {
        "checked": False,
        "fail_count": 0,
        "issues": [],
    }

    if (page_role or "").lower() != "active_rebuild":
        result["reason"] = (
            f"template_copy_overfit 仅对 active_rebuild 页检测（fixed_template 保留版式属正常）。"
            f"本页 page_role={page_role}"
        )
        return result

    if source_path is None or not source_path.exists():
        result["reason"] = "缺 --source 参数，无法对比 authored vs source shape id"
        return result

    result["checked"] = True

    try:
        authored_xml = authored_path.read_text(encoding="utf-8")
        source_xml = source_path.read_text(encoding="utf-8")
    except Exception as e:
        result["reason"] = f"read failed: {e}"
        return result

    # 提 shape/line/img/icon 的 id 属性
    id_pattern = re.compile(r'<(?:shape|line|img|icon|table|chart|embed|polyline)\b[^>]*\bid="([^"]+)"')
    authored_ids = set(id_pattern.findall(authored_xml))
    source_ids = set(id_pattern.findall(source_xml))

    authored_n = len(authored_ids)
    source_n = len(source_ids)
    if authored_n == 0:
        result["reason"] = "authored 页无 shape id，跳过"
        return result

    shared_ids = authored_ids & source_ids
    shared_ratio = len(shared_ids) / authored_n

    result.update({
        "authored_shape_count": authored_n,
        "source_shape_count": source_n,
        "shared_id_count": len(shared_ids),
        "shared_ratio": round(shared_ratio, 3),
        "threshold": threshold_ratio,
    })

    if shared_ratio > threshold_ratio:
        result["fail_count"] = 1
        result["status"] = "blocked"
        result["issues"].append({
            "code": "template_copy_overfit",
            "severity": "error",
            "message": (
                f"authored 页 {authored_n} 个 shape 中，{len(shared_ids)} 个（{shared_ratio*100:.1f}%）的 id 与 source 页相同，"
                f"超过 {threshold_ratio*100:.0f}% 门槛。"
                f"active_rebuild 页应该按 refine-examples 的 sub-type 范本从零建骨架，"
                f"只保留跨页复用的 brand_assets（背景/页眉/页脚/装饰线），不要 cp source 保留内容占位符和装饰群。"
            ),
        })
    else:
        result["status"] = "ok"

    return result


# ---------- refine 触发规则（跟 template-editing-organizer.md 5.2 · active_rebuild 5 信号对齐） ----------
REFINE_SIGNAL_RULES = [
    ("visual_elements",           "≤",   12,   "装饰/图表偏少 · 大概率是纯文字空稿"),
    ("long_paragraph_char_ratio", ">",   0.60, "单长段占据全页文字主导（页眉页脚 + 一大段典型模式）"),
    ("total_elements",            "<",   20,   "元素太少 · 范本页型骨架至少 20 个 shape"),
    ("total_text_chars",          "<",   30,   "漏填 / 内容太少（仅 <data> 里的文字 · 不含演讲者备注 <note>）"),
    ("text_ratio",                ">",   0.80, "几乎全是文字块 · 装饰不足"),
]


def _compute_refine_triggers(authored_counts: dict, page_role: str | None) -> dict:
    """基于 6 个 refine 启动信号，产生 refine_triggers 字段。

    页型 = fixed_template 时返回 {"applicable": False, ...}——refine 只对 active_rebuild 页有意义。
    """
    if page_role is None:
        return {
            "applicable": False,
            "reason": (
                "⚠️ --page-role 未传！refine_triggers 无法计算 —— 这不是'本页不适用 refine'，"
                "而是调用方漏参数。请从 page-plan 该行「页型策略」列取值 "
                "（fixed_template / active_rebuild），加 --page-role <值> 重跑本条 lint。"
            ),
            "signal_error": "missing_page_role_argument",
        }
    if (page_role or "").lower() != "active_rebuild":
        return {
            "applicable": False,
            "reason": f"refine 仅对 active_rebuild 页生效；本页 page_role={page_role}",
        }

    ve = int(authored_counts.get("visual_shape", 0) or 0) + int(authored_counts.get("visual_other", 0) or 0)
    te = int(authored_counts.get("text", 0) or 0)
    tot = int(authored_counts.get("total", 0) or 0)
    lpr = float(authored_counts.get("long_paragraph_char_ratio", 0.0) or 0.0)
    tc = int(authored_counts.get("total_text_chars", 0) or 0)
    mf = float(authored_counts.get("max_font_size", 0.0) or 0.0)
    tr = (te / tot) if tot else 0.0

    signal_values = {
        "visual_elements": ve,
        "long_paragraph_char_ratio": round(lpr, 3),
        "total_elements": tot,
        "total_text_chars": tc,
        "text_ratio": round(tr, 3),
        "max_font_size": mf,
    }

    triggered = []
    passed = []
    for name, op, threshold, note in REFINE_SIGNAL_RULES:
        v = signal_values[name]
        hit = False
        if op == "≤":  hit = v <= threshold
        elif op == "<":  hit = v < threshold
        elif op == ">":  hit = v > threshold
        entry = {
            "signal": name,
            "value": v,
            "operator": op,
            "threshold": threshold,
            "note": note,
        }
        (triggered if hit else passed).append(entry)

    return {
        "applicable": True,
        "should_refine": len(triggered) > 0,
        "hit_count": len(triggered),
        "triggered": triggered,
        "passed": passed,
        "summary": (
            f"命中 {len(triggered)}/{len(REFINE_SIGNAL_RULES)} 个 refine 启动信号 · 应该 refine"
            if triggered
            else f"{len(REFINE_SIGNAL_RULES)} 个信号全部通过 · 无需 refine（客观指标已达范本水平）"
        ),
    }


def _classify_slide_elements(slide_node, local_fn) -> dict:
    """扫一个 slide 下 <data> 里的元素，分类计数。
    text_shape = shape 里 type="text" 或 text 元素；visual_shape = shape 里 type != "text"；
    visual_other = img/embed/chart/icon/line/table
    额外统计：text_shape_char_lengths（每个文字 shape 的字符数列表）
    **只扫 <data> 内容 · 不扫 <note>（演讲者备注） · 不扫 <style>**——refine 启动信号只看视觉呈现的内容。
    """
    counts = {"text": 0, "visual_shape": 0, "visual_other": 0}
    text_char_lengths: list[int] = []
    max_font_size = 0

    # 只扫 <data> 节点（slide → data → 元素）；找不到 data 就返回空计数（不退回扫 slide 直接子节点，避免误算 note）
    data_nodes = [c for c in slide_node if local_fn(c.tag) == "data"]

    for container in data_nodes:
        for child in container:
            tag = local_fn(child.tag)
            if tag == "shape":
                shape_type = (child.get("type") or "").lower()
                if shape_type == "text":
                    counts["text"] += 1
                    text_char_lengths.append(_shape_text_length(child, local_fn))
                    # 扫本 shape 内所有 content/font 找最大字号
                    for content in child.iter():
                        # 字号：<content fontSize="XX"> 或 <font size="XX">
                        fs = content.get("fontSize") if content.get("fontSize") else content.get("size")
                        if fs:
                            try:
                                fs_v = float(fs)
                                if fs_v > max_font_size:
                                    max_font_size = fs_v
                            except (TypeError, ValueError):
                                pass
                else:
                    counts["visual_shape"] += 1
            elif tag in VISUAL_TAGS:
                counts["visual_other"] += 1
            elif tag in TEXT_TAGS:
                counts["text"] += 1
                text_char_lengths.append(_shape_text_length(child, local_fn))
            # 其他标签（如 note）不计入 —— 已通过只扫 <data> 排除
    counts["total"] = counts["text"] + counts["visual_shape"] + counts["visual_other"]
    counts["text_char_lengths"] = text_char_lengths
    counts["max_font_size"] = max_font_size
    counts["long_paragraph_count"] = sum(
        1 for n in text_char_lengths if n >= LONG_PARAGRAPH_CHAR_THRESHOLD
    )
    counts["long_paragraph_chars"] = sum(
        n for n in text_char_lengths if n >= LONG_PARAGRAPH_CHAR_THRESHOLD
    )
    counts["total_text_chars"] = sum(text_char_lengths)
    return counts


def check_sparsity(authored_xml: Path, source_xml: Path | None,
                   page_role: str | None = None,
                   min_total: int = 3,
                   max_text_ratio: float = 0.90,
                   min_density_ratio: float = 0.60,
                   min_long_paragraphs_for_dominated: int = 1,
                   max_long_paragraph_char_ratio: float = 0.70) -> dict:
    """检测内容页是否过于稀疏或被长段落主导（"页眉页脚 + 几段纯文字"这种空稿）。

    4 个门槛（默认 active_rebuild 页 fail 触发 blocked；fixed_template 页降级为 info）：
    - total_elements >= min_total（默认 3，避免误伤 cover）
    - text_ratio <= max_text_ratio（默认 0.90，避免误伤 toc）
    - density_ratio >= min_density_ratio（默认 0.60，需 source；无则跳）
    - **not dominated_by_paragraphs**：长段落（≥ 80 字符 text shape）数 < 2
      或 长段落字符占全页字符 <= 60%（防止大段纯文字堆砌）

    page_role 传 "fixed_template" 时所有 issue 降 severity 为 info（不 blocked）
    """
    try:
        tree = ET.parse(str(authored_xml))
        root = tree.getroot()
    except Exception as e:
        return {"checked": False, "error": f"parse authored failed: {e}"}

    def local(tag: str) -> str:
        return tag.split("}", 1)[1] if "}" in tag else tag

    root_local = local(root.tag)
    if root_local == "slide":
        slides = [root]
    elif root_local == "presentation":
        slides = [c for c in root if local(c.tag) == "slide"]
    else:
        slides = [root]

    if not slides:
        return {"checked": False, "error": "no slide found in authored xml"}

    authored_counts = _classify_slide_elements(slides[0], local)

    # fixed_template 页的 issue 都降级为 info（不阻断）
    is_fixed_template = (page_role or "").lower() == "fixed_template"
    fail_severity = "info" if is_fixed_template else "fail"

    result: dict = {
        "checked": True,
        "page_role": page_role or "unknown",
        "authored": authored_counts,
        "thresholds": {
            "min_total": min_total,
            "max_text_ratio": max_text_ratio,
            "min_density_ratio": min_density_ratio,
            "long_paragraph_char_threshold": LONG_PARAGRAPH_CHAR_THRESHOLD,
            "min_long_paragraphs_for_dominated": min_long_paragraphs_for_dominated,
            "max_long_paragraph_char_ratio": max_long_paragraph_char_ratio,
        },
        "issues": [],
    }

    # 门槛 1: total >= min_total
    total = authored_counts["total"]
    if total < min_total:
        result["issues"].append({
            "code": "too_few_elements",
            "severity": fail_severity,
            "message": f"整页元素总数 {total} < {min_total}",
            "hint": "参考规则 5.2.2「默认视觉化 · 纯段落是例外」—— 加 KPI 数字带 / 编号卡片 / 时间线 / 三线表 / SVG 图 / 图 + 文",
        })

    # 门槛 2: text_ratio <= max_text_ratio
    if total > 0:
        text_ratio = authored_counts["text"] / total
        result["authored"]["text_ratio"] = round(text_ratio, 3)
        if text_ratio > max_text_ratio:
            result["issues"].append({
                "code": "text_ratio_too_high",
                "severity": fail_severity,
                "message": f"文字类元素占比 {text_ratio:.0%} > {max_text_ratio:.0%}",
                "hint": "把长段落拆成结构化视觉表达（KPI 数字 / 编号卡 / 三线表 / 时间线 / SVG 图）",
            })

    # 门槛 3: dominated_by_paragraphs —— 长段落数 + 长段落字符占比双重判定
    long_p_count = authored_counts["long_paragraph_count"]
    long_p_chars = authored_counts["long_paragraph_chars"]
    total_chars = authored_counts["total_text_chars"]
    long_p_ratio = long_p_chars / total_chars if total_chars > 0 else 0
    result["authored"]["long_paragraph_char_ratio"] = round(long_p_ratio, 3)
    if long_p_count >= min_long_paragraphs_for_dominated and long_p_ratio > max_long_paragraph_char_ratio:
        result["issues"].append({
            "code": "dominated_by_paragraphs",
            "severity": fail_severity,
            "message": (
                f"页面被大段文字主导：{long_p_count} 个长段落（≥{LONG_PARAGRAPH_CHAR_THRESHOLD} 字）"
                f"占全页文字的 {long_p_ratio:.0%}（阈值 {max_long_paragraph_char_ratio:.0%}）"
            ),
            "hint": "把长段落拆成结构化视觉表达（KPI 数字 / 编号卡 / 三线表 / 时间线 / SVG 图 / 图 + 文）",
        })

    # 门槛 4: density_ratio >= min_density_ratio（需要 source）
    if source_xml and source_xml.exists():
        try:
            s_tree = ET.parse(str(source_xml))
            s_root = s_tree.getroot()
            s_root_local = local(s_root.tag)
            if s_root_local == "slide":
                s_slides = [s_root]
            elif s_root_local == "presentation":
                s_slides = [c for c in s_root if local(c.tag) == "slide"]
            else:
                s_slides = [s_root]
            if s_slides:
                source_counts = _classify_slide_elements(s_slides[0], local)
                result["source"] = source_counts
                if source_counts["total"] > 0:
                    ratio = total / source_counts["total"]
                    result["density_ratio"] = round(ratio, 3)
                    if ratio < min_density_ratio:
                        result["issues"].append({
                            "code": "density_below_source",
                            "severity": fail_severity,
                            "message": (
                                f"新页元素数 {total} 只有源模板页 {source_counts['total']} 的 {ratio:.0%}"
                                f"（低于 {min_density_ratio:.0%}）"
                            ),
                            "hint": "参考源模板页的元素密度补充结构性视觉；不用照搬示例文字，加 KPI 数字 / 编号卡 / 分栏 / 图表让画面填满",
                        })
        except Exception as e:
            result["source_parse_error"] = str(e)
    else:
        result["density_check_skipped"] = "no source xml"

    fail_count = sum(1 for i in result["issues"] if i["severity"] == "fail")
    info_count = sum(1 for i in result["issues"] if i["severity"] == "info")
    result["fail_count"] = fail_count
    result["info_count"] = info_count
    result["status"] = "blocked" if fail_count > 0 else "ok"

    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="template-editing 分支专用的聚合 lint")
    ap.add_argument("--authored", required=True, help="MainAgent 写好的 authoring/slide-NN.xml")
    ap.add_argument("--source", help="对应的 source-slides/slide-NN.xml（用于占位符 diff）；不传则跳过 diff")
    ap.add_argument("--skill-root", required=True,
                    help="skill 根目录（找 xml_lint.py / color_contrast_check.py）")
    ap.add_argument("--contrast-threshold", type=float, default=2.25)
    ap.add_argument("--page-role", choices=["fixed_template", "active_rebuild"], default=None,
                    help="页型策略，从 page-plan 该页的「页型策略」列取。传 fixed_template 时 sparsity_check 只报 info 不 block（cover/toc/chapter 天然元素少或纯文字）；不传时按 active_rebuild 严格判定")
    args = ap.parse_args()

    authored_path = Path(args.authored).resolve()
    if not authored_path.exists():
        print(json.dumps({"ok": False, "error": f"authored not found: {authored_path}"}))
        return 2

    skill_root = Path(args.skill_root).resolve()
    xml_lint_script = skill_root / "scripts" / "xml_lint.py"
    contrast_script = skill_root / "scripts" / "color_contrast_check.py"
    if not xml_lint_script.exists():
        print(json.dumps({"ok": False, "error": f"xml_lint.py not found under {skill_root}"}))
        return 3
    if not contrast_script.exists():
        print(json.dumps({"ok": False, "error": f"color_contrast_check.py not found under {skill_root}"}))
        return 3

    # (1) xml_lint
    xml_lint_res = _run_subscript(xml_lint_script, ["--input", str(authored_path)], timeout=60)
    xml_lint_summary = (xml_lint_res.get("stdout_json") or {}).get("summary", {})
    xml_lint_error_count = xml_lint_summary.get("error_count", -1)

    # (2) 靠色
    contrast_res = _run_subscript(
        contrast_script,
        ["--xml", str(authored_path), "--format", "json",
         "--threshold", str(args.contrast_threshold)],
        timeout=60,
    )
    contrast_summary = (contrast_res.get("stdout_json") or {}).get("summary", {})
    contrast_has_blocking = contrast_summary.get("has_blocking_issues", False)

    # (3) 占位符 diff（可选）
    placeholder_res: dict | None = None
    if args.source:
        source_path = Path(args.source).resolve()
        if source_path.exists():
            placeholder_res = check_placeholders(source_path, authored_path)
        else:
            placeholder_res = {"checked": False, "error": f"source not found: {source_path}"}
    else:
        placeholder_res = {"checked": False, "reason": "no --source passed, placeholder diff skipped"}

    # (4) 溢出压邻居（基于 xml_lint 报的 text_overflows_container 做二次分析）
    overflow_covers_res = check_overflow_covers_below(
        authored_path, xml_lint_res.get("stdout_json")
    )

    # (5) 意外换行（单行框被强制多行）
    wrapping_res = check_unexpected_wrapping(authored_path)

    # (6) 稀疏度检测（防"页眉页脚 + 几段纯文字"的空稿）
    source_path_for_sparsity = Path(args.source).resolve() if args.source else None
    sparsity_res = check_sparsity(authored_path, source_path_for_sparsity,
                                  page_role=args.page_role)

    # (7) 模板拷贝过拟合检测（active_rebuild 页专用；防"authored 页 shape 90% 来自 source 页"）
    overfit_res = check_template_copy_overfit(authored_path, source_path_for_sparsity,
                                              page_role=args.page_role)

    # 聚合 status
    blocked = False
    reasons: list[str] = []
    if xml_lint_error_count > 0:
        blocked = True
        reasons.append(f"xml_lint has {xml_lint_error_count} errors")
    elif xml_lint_error_count < 0:
        # 子脚本失败/超时导致 error_count 为默认 -1 · 也要 block(否则错误被静默掩盖)
        blocked = True
        reasons.append("xml_lint subscript failed or returned no summary")
    if contrast_has_blocking:
        blocked = True
        reasons.append("color_contrast_check has FAIL")
    if overflow_covers_res.get("fail_count", 0) > 0:
        blocked = True
        reasons.append(
            f"text_overflow_covers_below has {overflow_covers_res['fail_count']} FAIL "
            "(某文本溢出后压到了同页其他文本框，用户视觉上会看到两段文字重叠)"
        )
    if sparsity_res.get("fail_count", 0) > 0:
        blocked = True
        codes = [i["code"] for i in sparsity_res.get("issues", [])]
        reasons.append(
            f"sparsity_check has {sparsity_res['fail_count']} FAIL "
            f"({', '.join(codes)}) —— 页面过于稀疏/文字化，参考 5.2.2「默认视觉化」补结构化视觉"
        )
    if overfit_res.get("fail_count", 0) > 0:
        blocked = True
        reasons.append(
            f"template_copy_overfit FAIL —— authored 页 {overfit_res['shared_ratio']*100:.0f}% 的 shape id 与 source 相同，"
            f"意味着几乎照抄模板 shape。active_rebuild 页应该按 refine-examples 的 sub-type 范本从零建骨架，"
            "只保留跨页复用的 brand_assets（背景/页眉/页脚/装饰线）。请重新生成本页。"
        )

    placeholder_warn_count = (placeholder_res or {}).get("warning_count", 0)
    wrapping_warn_count = (wrapping_res or {}).get("warning_count", 0)

    output = {
        "ok": True,
        "authored": str(authored_path),
        "status": "blocked" if blocked else "ready_to_write",
        "block_reasons": reasons,
        "placeholder_warnings": placeholder_warn_count,
        "wrapping_warnings": wrapping_warn_count,
        "summary": {
            "xml_lint_errors": xml_lint_error_count,
            "contrast_blocking": contrast_has_blocking,
            "placeholder_warn_count": placeholder_warn_count,
            "overflow_covers_below_fail_count": overflow_covers_res.get("fail_count", 0),
            "unexpected_wrapping_warn_count": wrapping_warn_count,
            "sparsity_fail_count": sparsity_res.get("fail_count", 0),
            # 元素分布信号（非阻断，供 Organizer 判断 refine 启动条件）
            "page_role": sparsity_res.get("page_role"),
            "total_elements": (sparsity_res.get("authored") or {}).get("total"),
            "text_elements": (sparsity_res.get("authored") or {}).get("text"),
            "visual_elements": (
                (sparsity_res.get("authored") or {}).get("visual_shape", 0)
                + (sparsity_res.get("authored") or {}).get("visual_other", 0)
            ),
            "long_paragraph_count": (sparsity_res.get("authored") or {}).get("long_paragraph_count"),
            "long_paragraph_char_ratio": (sparsity_res.get("authored") or {}).get("long_paragraph_char_ratio"),
            "total_text_chars": (sparsity_res.get("authored") or {}).get("total_text_chars"),
            "max_font_size": (sparsity_res.get("authored") or {}).get("max_font_size"),
            "refine_triggers": _compute_refine_triggers(sparsity_res.get("authored") or {}, sparsity_res.get("page_role")),
        },
        "checks": {
            "xml_lint": {
                "status": xml_lint_summary.get("status"),
                "error_count": xml_lint_error_count,
                "warning_count": xml_lint_summary.get("warning_count", 0),
                "raw": xml_lint_res.get("stdout_json"),
            },
            "color_contrast": {
                "has_blocking": contrast_has_blocking,
                "issue_count": contrast_summary.get("issue_count", 0),
                "raw": contrast_res.get("stdout_json"),
            },
            "placeholder_diff": placeholder_res,
            "overflow_covers_below": overflow_covers_res,
            "unexpected_wrapping": wrapping_res,
            "sparsity": sparsity_res,
            "template_copy_overfit": overfit_res,
        },
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if not blocked else 1


if __name__ == "__main__":
    sys.exit(main())
