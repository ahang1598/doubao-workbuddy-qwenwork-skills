#!/usr/bin/env python3
"""parse_template.py — 一步产出模板全部本地资源,供 template-editing 流程用。

流程:
1. 离线解压 pptx → manifest + assets + 联图
2. lark-cli drive +import 导入飞书拿 deck(直接当交付目标 · 不新建)
3. lark-cli slides +xml-get 拉全稿 SXSD → 拆 $WORK_DIR/source-slides/slide-NN.xml
4. 单线程串行 +delete-slide 除第 1 页外所有页 → +update-slide 覆盖第 1 页为空白
   撞 rate_limit 的页跳过,slide_id 塞进 lark.deck.purge_failed_slide_ids · 让 MainAgent 调 purge_deck.py 补删
5. 抽 file_token 到 template-index.json.assets_with_tokens(**deck-scope 绑定 · 跨 deck 会 relation mismatch**)

关键 lark 字段(在 template-index.json 的 `lark` 下):
- lark.deck.xml_presentation_id       用户可见的目标 deck
- lark.deck.url                       Step 3 present_files 用
- lark.deck.first_page_slide_id       第 1 页 id · Step 5 首页用 +update-slide 覆盖
- lark.deck.first_page_state          "blank" = 已清空 · "template_remnant" = 清空失败(非致命)
- lark.deck.purge_failed_slide_ids    残留页 · MainAgent 需调 purge_deck.py --slide-ids 补删

产物:
- $WORK_DIR/manifest/template-index.json      轻量索引 · MainAgent Step 2 唯一 Read 的产物
- $WORK_DIR/manifest/slides/slide-NN.json     每页详情(脚本产 · MainAgent 一般不 Read)
- $WORK_DIR/manifest/content-skeletons/*      内容页干净骨架(active_rebuild cp 起点)
- $WORK_DIR/manifest/theme.json               配色 + 字体
- $WORK_DIR/assets/image*.{png,jpg,jpeg,emf}  模板内图片本地文件
- $WORK_DIR/assets_index.json                 assets_with_tokens 镜像(向后兼容)
- $WORK_DIR/thumbs/overview*.jpg              全稿联图 · 大 deck 分片成 overview-1/2/...jpg
- $WORK_DIR/source-slides/slide-NN.xml        每页 SXSD · MainAgent 写入起点
- $WORK_DIR/source-slides/full.xml            全稿 SXSD · Organizer 参考用

用法:
  python3 parse_template.py --pptx <path> --work-dir <WORK_DIR>
  python3 parse_template.py --pptx <path> --work-dir <WORK_DIR> --deck-title "..."
  python3 parse_template.py --pptx <path> --work-dir <WORK_DIR> --offline-only

依赖:
  python-pptx   缺 → zipfile + xml.etree 降级 parser
  pypdfium2     缺 → PDF 直接拷贝到 thumbs/overview.pdf(BSD 许可)
  Pillow        缺 → 同上
  lxml          缺 → xml.etree 降级
  soffice       缺 → lark screenshot 云端兜底 → lark drive +export pdf 兜底
  lark-cli      --offline-only 时可无

main() 开头 _ensure_pip_deps() 尝试补装缺失 pip 包 · 用当前解释器的 pip · 单包超时 60s · 失败静默。

capability_level:
  full      所有 pip + soffice + lark-cli 齐 · 产物完整
  degraded  部分缺 · 走 fallback
  minimal   多依赖缺 · 仅产 assets + source-slides + 最简 index
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROLE_KEYWORDS = {
    "cover": ["封面", "cover", "title slide"],
    "toc": ["目录", "contents", "agenda", "outline"],
    "chapter": ["章节", "chapter", "section", "part "],
    "transition": ["过渡", "transition"],
    "ending": ["感谢", "thanks", "谢谢", "结束", "ending", "the end"],
}

PLACEHOLDER_PATTERNS = [
    r"添加标题", r"点击输入", r"点击此处", r"占位", r"示例文本", r"示例文字",
    r"Lorem ipsum", r"Lorem", r"Click to add", r"Add title", r"Add subtitle",
    r"Add text", r"Placeholder", r"Sample text",
    r"论文就是用来", r"想搞设计", r"asdas",
]


def _emu_to_inch(v: int | None) -> float:
    if v is None:
        return 0.0
    return round(v / 914400.0, 4)


def _emu_to_pt(v: int | None) -> float:
    if v is None:
        return 0.0
    return round(v / 12700.0, 2)


def _shape_text(shape) -> str:
    if not shape.has_text_frame:
        return ""
    parts = []
    for para in shape.text_frame.paragraphs:
        for run in para.runs:
            if run.text:
                parts.append(run.text)
        parts.append("\n")
    return "".join(parts).strip()


# ============================================================
# python-pptx 缺失时的降级 parser：直接解析 pptx zip 里的 slide{N}.xml
# 只用标准库 zipfile + xml.etree.ElementTree
# ============================================================

# OOXML 命名空间
_OOXML_NS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


class _FallbackShape:
    """模拟 python-pptx Shape 对象的最小接口。"""
    __slots__ = ("shape_id", "shape_type", "left", "top", "width", "height", "_text")

    def __init__(self, shape_id, shape_type, left, top, width, height, text):
        self.shape_id = shape_id
        self.shape_type = shape_type
        self.left = left
        self.top = top
        self.width = width
        self.height = height
        self._text = text

    @property
    def has_text_frame(self) -> bool:
        return bool(self._text)


def _parse_shape_from_element(elem, ns_p: str, ns_a: str) -> list[_FallbackShape]:
    """递归解析 p:sp / p:pic / p:grpSp / p:cxnSp 元素，返回 shape 列表。

    子 shape （group 内）会打平展开。"""
    tag = elem.tag
    local = tag.split("}", 1)[-1] if "}" in tag else tag

    if local == "grpSp":
        # 递归子元素
        out = []
        for child in elem:
            child_local = child.tag.split("}", 1)[-1]
            if child_local in ("sp", "pic", "grpSp", "cxnSp"):
                out.extend(_parse_shape_from_element(child, ns_p, ns_a))
        return out

    # sp / pic / cxnSp：单个 shape
    # 找 cNvPr 拿 id/name
    shape_id = None
    for cnvpr in elem.iter(f"{{{ns_p}}}cNvPr"):
        try:
            shape_id = int(cnvpr.get("id", "0"))
        except (ValueError, TypeError):
            shape_id = None
        break

    # 找 spPr/xfrm/off + ext 拿坐标（EMU）
    left = top = width = height = 0
    for xfrm in elem.iter(f"{{{ns_a}}}xfrm"):
        off = xfrm.find(f"{{{ns_a}}}off")
        ext = xfrm.find(f"{{{ns_a}}}ext")
        if off is not None:
            try:
                left = int(off.get("x", "0"))
                top = int(off.get("y", "0"))
            except (ValueError, TypeError):
                pass
        if ext is not None:
            try:
                width = int(ext.get("cx", "0"))
                height = int(ext.get("cy", "0"))
            except (ValueError, TypeError):
                pass
        break  # 只取第一个 xfrm，不下钻

    # 找所有 a:t 拿文本
    texts = []
    for t in elem.iter(f"{{{ns_a}}}t"):
        if t.text:
            texts.append(t.text)
    text = "".join(texts).strip()

    # shape 类型：sp/pic/cxnSp 映射
    shape_type_map = {
        "sp": "AUTO_SHAPE" if not text else "TEXT_BOX",
        "pic": "PICTURE",
        "cxnSp": "LINE",
    }
    shape_type = shape_type_map.get(local, "UNKNOWN")

    return [_FallbackShape(shape_id, shape_type, left, top, width, height, text)]


def _parse_pptx_fallback(pptx_path: Path) -> tuple[float, float, list[list[_FallbackShape]]]:
    """无 python-pptx 时的降级解析。返回 (canvas_w_emu, canvas_h_emu, list_of_slides_shapes)."""
    canvas_w = canvas_h = 0
    with zipfile.ZipFile(pptx_path) as z:
        # 读 presentation.xml 拿画布
        try:
            xml = z.read("ppt/presentation.xml").decode("utf-8", errors="ignore")
            m = re.search(r'<p:sldSz[^>]*cx="(\d+)"[^>]*cy="(\d+)"', xml)
            if not m:
                m = re.search(r'<p:sldSz[^>]*cy="(\d+)"[^>]*cx="(\d+)"', xml)
                if m:
                    canvas_h, canvas_w = int(m.group(1)), int(m.group(2))
            else:
                canvas_w, canvas_h = int(m.group(1)), int(m.group(2))
        except Exception:
            pass

        # 找到所有 slide{N}.xml，按 N 排序
        slide_names = sorted(
            [n for n in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n)],
            key=lambda n: int(re.search(r"slide(\d+)", n).group(1)),
        )

        slides_shapes: list[list[_FallbackShape]] = []
        import xml.etree.ElementTree as ET
        for name in slide_names:
            try:
                xml = z.read(name).decode("utf-8", errors="ignore")
                root = ET.fromstring(xml)
            except Exception:
                slides_shapes.append([])
                continue

            # 从 root 找 p:cSld/p:spTree/{sp,pic,grpSp,cxnSp}
            shapes: list[_FallbackShape] = []
            ns_p = _OOXML_NS["p"]
            ns_a = _OOXML_NS["a"]
            sp_tree = root.find(f"{{{ns_p}}}cSld/{{{ns_p}}}spTree")
            if sp_tree is not None:
                for child in sp_tree:
                    child_local = child.tag.split("}", 1)[-1]
                    if child_local in ("sp", "pic", "grpSp", "cxnSp"):
                        shapes.extend(_parse_shape_from_element(child, ns_p, ns_a))
            slides_shapes.append(shapes)

    # canvas 兜底:pptx presentation.xml 读取失败时用 16:9 默认(EMU)· 避免下游除零 / 阈值全 0
    if not canvas_w or not canvas_h:
        canvas_w = canvas_w or 12192000  # 13.333" · 16:9 标准
        canvas_h = canvas_h or 6858000   # 7.5"

    return canvas_w, canvas_h, slides_shapes


def _classify_role(slide_num: int, total: int, texts: list[str]) -> str:
    """按位置+文本内容启发式判定页面角色。"""
    joined = " ".join(texts).lower()
    for role, kws in ROLE_KEYWORDS.items():
        for kw in kws:
            if kw.lower() in joined:
                return role
    if slide_num == 1:
        return "cover"
    if slide_num == total:
        return "ending"
    if slide_num == 2 and any("目录" in t or "content" in t.lower() for t in texts):
        return "toc"
    if len(texts) <= 3 and any(len(t) < 40 for t in texts):
        return "chapter"
    return "content"


def _extract_shell_shapes(slide, slide_num: int, master_shape_ids: set[int],
                            canvas_w: float = 13.3333, canvas_h: float = 7.5) -> tuple[list[dict], list[dict]]:
    """区分壳层 shape(跨页复用/靠近边缘/装饰性)与内容 shape(可替换文本框)。

    简化启发式(用画布比例 · 不硬编码 4:3/16:9):
    - GROUP 且面积 > 20% 画布 → 壳层
    - PICTURE 且 (顶部/底部 5% 内 或 出现次数 >= 3 页) → 壳层
    - AUTO_SHAPE 且无文字且面积 < 3% 画布 → 壳层装饰
    - LINE → 壳层
    - TEXT_BOX / AUTO_SHAPE 有可编辑文字 → content_shapes
    """
    # 从画布比例计算判据 · 兼容 16:9 / 4:3 / 竖版 / 自定义画布
    canvas_area = max(canvas_w * canvas_h, 1e-6)
    edge_top_thresh = canvas_h * 0.053   # 原 0.4 / 7.5
    edge_bottom_thresh = canvas_h * 0.947  # 原 7.1 / 7.5
    edge_left_thresh = canvas_w * 0.0375   # 原 0.5 / 13.333
    edge_right_thresh = canvas_w * 0.96    # 原 12.8 / 13.333
    small_logo_area = canvas_area * 0.01   # 原 1.0 / 100
    large_group_area = canvas_area * 0.2   # 原 20.0 / 100
    small_shape_area = canvas_area * 0.03  # 原 3.0 / 100

    shell, content = [], []
    for shp in slide.shapes:
        try:
            # python-pptx 的 shape_type 是 MSO_SHAPE_TYPE enum · .name 拿到纯枚举名(PICTURE/LINE/GROUP/AUTO_SHAPE/TEXT_BOX)
            # 直接 str() 会得到 "PICTURE (13)" 之类带数字 · 后续 == 判断全失效
            try:
                shape_type_name = shp.shape_type.name if shp.shape_type else "UNKNOWN"
            except AttributeError:
                shape_type_name = str(shp.shape_type).replace("MSO_SHAPE_TYPE.", "").split()[0] if shp.shape_type else "UNKNOWN"
        except Exception:
            shape_type_name = "UNKNOWN"

        try:
            left = _emu_to_inch(shp.left)
            top = _emu_to_inch(shp.top)
            width = _emu_to_inch(shp.width)
            height = _emu_to_inch(shp.height)
        except Exception:
            left, top, width, height = 0.0, 0.0, 0.0, 0.0

        text = ""
        try:
            text = _shape_text(shp)
        except Exception:
            pass

        base = {
            "id": shp.shape_id if hasattr(shp, "shape_id") else None,
            "type": shape_type_name,
            "left": left,
            "top": top,
            "width": width,
            "height": height,
            "text": text[:100],
        }

        is_shell = False
        if shape_type_name == "LINE":
            is_shell = True
        elif shape_type_name == "PICTURE":
            if top < edge_top_thresh or top + height > edge_bottom_thresh:
                is_shell = True
            elif width * height < small_logo_area and (left < edge_left_thresh or left + width > edge_right_thresh):
                is_shell = True
        elif shape_type_name == "GROUP":
            if width * height > large_group_area:
                is_shell = True
        elif shape_type_name == "AUTO_SHAPE" and not text and width * height < small_shape_area:
            is_shell = True

        if is_shell:
            shell.append(base)
        else:
            content.append(base)

    return shell, content


def _extract_available_regions(shell_shapes: list[dict], content_shapes: list[dict],
                                canvas_w: float, canvas_h: float) -> list[dict]:
    """粗略计算可用文字区：把画布划分成 4x3 网格，标记被壳层或内容压住的格子；剩下的相邻空白格子合并成矩形。"""
    cols, rows = 4, 3
    cw, ch = canvas_w / cols, canvas_h / rows
    occupied = [[False] * cols for _ in range(rows)]
    for shp in shell_shapes + content_shapes:
        l, t, w, h = shp["left"], shp["top"], shp["width"], shp["height"]
        for r in range(rows):
            for c in range(cols):
                cell_l, cell_t = c * cw, r * ch
                if not (l + w < cell_l or l > cell_l + cw or t + h < cell_t or t > cell_t + ch):
                    occupied[r][c] = True
    regions = []
    for r in range(rows):
        for c in range(cols):
            if not occupied[r][c]:
                regions.append({
                    "left": round(c * cw, 2),
                    "top": round(r * ch, 2),
                    "width": round(cw, 2),
                    "height": round(ch, 2),
                })
    return regions


def _extract_images_used(slide_rels_path: Path) -> list[str]:
    """从 slide{N}.xml.rels 里抽出该页引用的所有 image 文件名（去掉 ../media/ 前缀）。"""
    if not slide_rels_path.exists():
        return []
    text = slide_rels_path.read_text(encoding="utf-8")
    imgs = re.findall(r'Target="\.\./media/([^"]+)"', text)
    return imgs


def _detect_placeholders(all_texts: list[str]) -> list[str]:
    """扫全模板文本，找出所有可能的占位符（用于告知 MainAgent 必须替换）。"""
    hits = []
    pat = re.compile("|".join(PLACEHOLDER_PATTERNS))
    seen = set()
    for t in all_texts:
        for m in pat.finditer(t):
            found = m.group(0)
            if found not in seen:
                hits.append(found)
                seen.add(found)
    return hits


def _extract_theme(pptx_path: Path) -> dict:
    """从 pptx 的 theme1.xml 提主色/辅色/字体（中英文各一）。"""
    theme = {"colors": [], "major_font": None, "minor_font": None,
             "major_font_ea": None, "minor_font_ea": None}
    try:
        with zipfile.ZipFile(pptx_path) as z:
            for name in z.namelist():
                if name.startswith("ppt/theme/theme") and name.endswith(".xml"):
                    xml = z.read(name).decode("utf-8", errors="ignore")
                    # srgbClr / sysClr
                    theme["colors"] = re.findall(r'<a:srgbClr val="([0-9A-Fa-f]{6})"', xml)[:8]
                    # 拉丁字体（英文/数字）
                    m_major = re.search(r'<a:majorFont>.*?<a:latin typeface="([^"]+)"', xml, re.DOTALL)
                    m_minor = re.search(r'<a:minorFont>.*?<a:latin typeface="([^"]+)"', xml, re.DOTALL)
                    if m_major:
                        theme["major_font"] = m_major.group(1)
                    if m_minor:
                        theme["minor_font"] = m_minor.group(1)
                    # 东亚字体（中文）—— ea typeface 在 majorFont / minorFont 里紧跟 latin
                    m_major_ea = re.search(r'<a:majorFont>.*?<a:ea typeface="([^"]*)"', xml, re.DOTALL)
                    m_minor_ea = re.search(r'<a:minorFont>.*?<a:ea typeface="([^"]*)"', xml, re.DOTALL)
                    if m_major_ea and m_major_ea.group(1):
                        theme["major_font_ea"] = m_major_ea.group(1)
                    if m_minor_ea and m_minor_ea.group(1):
                        theme["minor_font_ea"] = m_minor_ea.group(1)
                    break
    except Exception as e:
        theme["error"] = str(e)
    return theme


def _pptx_to_pdf(pptx_path: Path, out_dir: Path) -> Path | None:
    """soffice pptx → pdf。返回 pdf 路径或 None（soffice 缺）。"""
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        return None
    try:
        subprocess.run(
            [soffice, "--headless", "--convert-to", "pdf", "--outdir", str(out_dir),
             str(pptx_path)],
            check=True, capture_output=True, timeout=120,
        )
    except Exception:
        return None
    pdf_path = out_dir / (pptx_path.stem + ".pdf")
    return pdf_path if pdf_path.exists() else None


def _screenshot_batch(deck_id: str, slide_numbers: list[int], out_dir: Path,
                      cwd: Path) -> list[Path]:
    """一次 `+screenshot` 拉一批（≤10）页截图。返回按 slide_number 升序排列的本地图片路径列表。

    只走 --slide-number（Step 1 之后 deck 才刚导入完，还没有稳定的 slide_id 映射需要透出）。
    lark-cli 要求 --output-dir 是 cwd 内的相对路径，所以调用方必须传 cwd。
    失败时返回空 list（外层决定继续走 pdf 兜底）。
    """
    if not slide_numbers or not shutil.which("lark-cli"):
        return []
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        rel_out = out_dir.resolve().relative_to(cwd.resolve())
    except ValueError:
        # out_dir 不在 cwd 内 —— 不该发生（外层已经把 out_dir 建在 cwd 里）
        return []
    cmd = ["lark-cli", "slides", "+screenshot",
           "--presentation", deck_id,
           "--output-dir", str(rel_out),
           "--format", "json"]
    for n in slide_numbers:
        cmd += ["--slide-number", str(n)]
    rc, stdout, stderr, timed_out = _run_with_retry(
        cmd, cwd=str(cwd), timeout=120, max_attempts=3, op_name=f"screenshot batch {slide_numbers[0]}-{slide_numbers[-1]}"
    )
    if rc != 0:
        return []
    # 解析 stdout JSON 拿 file paths；envelope 里字段名可能是 files / images / data.files
    try:
        payload = json.loads(stdout)
    except Exception:
        return []
    # 尽量宽松地扒路径
    candidates: list[str] = []
    def _walk(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in ("path", "file_path", "local_path") and isinstance(v, str) and v.lower().endswith((".png", ".jpg", ".jpeg")):
                    candidates.append(v)
                else:
                    _walk(v)
        elif isinstance(obj, list):
            for v in obj:
                _walk(v)
    _walk(payload)
    # 兜底：扫 out_dir 里新出现的图片文件（mtime 靠前 N 张）
    if len(candidates) < len(slide_numbers):
        recent = sorted(
            [p for p in out_dir.glob("*.png")] + [p for p in out_dir.glob("*.jpg")] + [p for p in out_dir.glob("*.jpeg")],
            key=lambda p: p.stat().st_mtime, reverse=True
        )[:len(slide_numbers)]
        # mtime 降序 -> 反转成升序（近似 slide_number 顺序，lark-cli 命名一般带页号）
        candidates = [str(p) for p in reversed(recent)]
    # 存在性过滤
    paths = [Path(p) for p in candidates if Path(p).exists()]
    return paths[:len(slide_numbers)]


def _render_overview_via_screenshot(deck_id: str, total_slides: int,
                                    thumbs_dir: Path,
                                    cwd: Path | None = None) -> tuple[bool, str]:
    """并发拉 lark screenshot 分批（10 页/批） + PIL 缩率拼 5 列联图。

    返回 (ok, reason)。成功时产 thumbs/overview.jpg。
    依赖：lark-cli + Pillow；PIL 缺 → 返回 False 让外层落到 PDF 兜底。
    cwd 用作 lark-cli 的工作目录；未指定时默认用 thumbs_dir 的祖父（一般是 WORK_DIR）。
    """
    if not shutil.which("lark-cli"):
        return False, "lark_cli_missing"
    try:
        from PIL import Image  # type: ignore
    except ImportError:
        return False, "pil_missing"

    thumbs_dir.mkdir(parents=True, exist_ok=True)
    shots_dir = thumbs_dir.parent / "_tmp_screenshots"
    shots_dir.mkdir(parents=True, exist_ok=True)
    # lark-cli 要求 --output-dir 是相对路径，需要在 cwd 内跑；默认取 thumbs_dir 的父（即 WORK_DIR）
    call_cwd = cwd if cwd is not None else thumbs_dir.parent

    # 分批：每批 10 页
    batches: list[list[int]] = []
    for start in range(1, total_slides + 1, 10):
        batches.append(list(range(start, min(start + 10, total_slides + 1))))

    # 并发拉截图(每批一个线程,_run_with_retry 内部已含 3 次重试 + 指数退避)
    # 用 wait(timeout=5) 轮询 + wait=True shutdown · 避免死锁
    from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
    import time as _time

    per_batch_results: dict[int, list[Path]] = {}
    max_workers = min(4, len(batches))  # 限制并发数,避免打爆飞书侧
    # 阶段预算:每批 60s · 至少 5 分钟 · 最多 15 分钟
    ss_phase_deadline_sec = max(300.0, min(900.0, len(batches) * 60.0))
    ss_deadline = _time.monotonic() + ss_phase_deadline_sec

    pool = ThreadPoolExecutor(max_workers=max_workers)
    try:
        future_to_idx = {
            pool.submit(_screenshot_batch, deck_id, batch, shots_dir / f"batch-{i}", call_cwd): i
            for i, batch in enumerate(batches)
        }
        pending = set(future_to_idx.keys())
        while pending:
            done, pending = wait(pending, timeout=5.0, return_when=FIRST_COMPLETED)
            for fut in done:
                idx = future_to_idx[fut]
                try:
                    per_batch_results[idx] = fut.result(timeout=0)
                except Exception:
                    per_batch_results[idx] = []
            if _time.monotonic() >= ss_deadline:
                for fut in pending:
                    idx = future_to_idx[fut]
                    fut.cancel()
                    per_batch_results.setdefault(idx, [])
                pending = set()
                break
    finally:
        pool.shutdown(wait=True, cancel_futures=True)

    # 按批次顺序汇总所有图片路径
    all_paths: list[Path] = []
    for i in range(len(batches)):
        got = per_batch_results.get(i, [])
        if len(got) < len(batches[i]):
            # 该批部分或全部失败 —— 后续拼图会露白，视为整体失败让外层走 pdf 兜底
            return False, f"screenshot_batch_{i}_incomplete:got_{len(got)}_of_{len(batches[i])}"
        all_paths.extend(got)

    if not all_paths:
        return False, "screenshot_all_failed"

    # PIL 缩率 + 分片拼图 · 单张 ≤ 3800px(Read 工具限制)
    try:
        # 每张缩到 ~400px 宽(对齐 soffice+pdfium@40dpi 主路径的 tile 尺寸;lark screenshot 源图分辨率高,压太狠浪费)
        target_w = 400
        thumbs = []
        for p in all_paths:
            with Image.open(p) as im:
                w, h = im.size
                scale = target_w / w
                thumbs.append(im.convert("RGB").resize((target_w, int(h * scale)), Image.LANCZOS))
        saved = _compose_overview_grid(thumbs, thumbs_dir, base_name="overview",
                                        max_side=3800, quality=78)
        if not saved:
            return False, "compose_failed"
        return True, "ok_via_screenshot" if len(saved) == 1 else f"ok_via_screenshot_sharded_{len(saved)}"
    except Exception as e:
        return False, f"pil_composite_error:{e}"


def _export_deck_pdf_via_lark(deck_id: str, out_dir: Path) -> Path | None:
    """lark-cli drive +export --doc-type slides --file-extension pdf.

    soffice 缺的兜底：让飞书云端渲染 pdf。返回 pdf 路径或 None。
    需要 deck 已经导入到飞书（Step 1 已完成），才能拿到 deck_id 走本路径。
    """
    if not shutil.which("lark-cli"):
        return None
    out_dir.mkdir(parents=True, exist_ok=True)
    file_name = f"overview-{deck_id[:12]}.pdf"
    try:
        proc = subprocess.run(
            ["lark-cli", "drive", "+export",
             "--token", deck_id, "--doc-type", "slides",
             "--file-extension", "pdf",
             "--output-dir", str(out_dir),
             "--file-name", file_name,
             "--overwrite"],
            capture_output=True, timeout=180, text=True,
        )
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    pdf_path = out_dir / file_name
    if pdf_path.exists():
        return pdf_path
    # lark-cli 有时会用不同的 basename，兜底扫 out_dir 里最新的 .pdf
    pdfs = sorted(out_dir.glob("*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True)
    return pdfs[0] if pdfs else None


def _compose_overview_grid(tiles: list, out_dir: Path, base_name: str = "overview",
                            max_side: int = 3800, gap: int = 6,
                            quality: int = 78) -> list[str]:
    """把一组 PIL Image tile 拼成 overview 联图 · 单张超 max_side 时自动分片。

    tile: 已经 resize 好的 PIL.Image 列表(全部同尺寸)
    max_side: 单张 JPG 的长/宽上限(留 buffer 给 Read 工具 4000px 限制)
    返回:相对 out_dir 的产物路径列表(单张=1 项 · 多张=N 项 · 顺序即页序)

    分片策略:
    - 单张最多容纳 max_pages · s.t. 长宽都 ≤ max_side
    - num_shards = ceil(N / max_pages)
    - 每片均分页数 · 内部 cols = ceil(sqrt(pages_per_shard))
    - 每片长宽尽量接近方形
    """
    if not tiles:
        return []
    from PIL import Image  # type: ignore
    import math

    tw, th = tiles[0].size
    n = len(tiles)

    # 单张最多容纳的页数 · 满足 cols*tw + (cols+1)*gap ≤ max_side (rows 同理)
    max_cols_by_w = max(1, (max_side - gap) // (tw + gap))
    max_rows_by_h = max(1, (max_side - gap) // (th + gap))
    # 近似方形约束:sqrt(pages)*tw ≤ max_side · sqrt(pages)*th ≤ max_side
    # 取 min 即"要方形又要装得下"的联合上限
    max_pages_by_w = max_cols_by_w * max_cols_by_w  # 假设 cols=rows(方形)
    max_pages_by_h = max_rows_by_h * max_rows_by_h
    max_pages_per_shard = max(1, min(max_pages_by_w, max_pages_by_h))

    # 若单张塞得下就一张出;否则均匀分片
    num_shards = max(1, math.ceil(n / max_pages_per_shard))
    pages_per_shard = math.ceil(n / num_shards)

    saved_paths: list[str] = []
    for shard_idx in range(num_shards):
        start = shard_idx * pages_per_shard
        end = min(start + pages_per_shard, n)
        shard_tiles = tiles[start:end]
        if not shard_tiles:
            continue

        # 单片内部 sqrt 网格(尽量方形)
        m = len(shard_tiles)
        cols = max(1, math.ceil(math.sqrt(m)))
        rows = math.ceil(m / cols)

        # 若单方向仍超 max_side · 重新平衡(优先压缩超边)
        # 只在极端窄长 tile 场景才触发 · 通常 sqrt 网格已符合
        if cols * (tw + gap) + gap > max_side:
            cols = max(1, (max_side - gap) // (tw + gap))
            rows = math.ceil(m / cols)
        if rows * (th + gap) + gap > max_side:
            rows = max(1, (max_side - gap) // (th + gap))
            # 若这时 cols*rows < m · 说明单片仍装不下 · 本函数已尽最大努力
            # 上层 max_pages_per_shard 计算已经预防了这种情况 · 这里只是双保险

        grid_w = cols * tw + (cols + 1) * gap
        grid_h = rows * th + (rows + 1) * gap
        grid = Image.new("RGB", (grid_w, grid_h), "white")
        for i, t in enumerate(shard_tiles):
            r, c = i // cols, i % cols
            grid.paste(t, (gap + c * (tw + gap), gap + r * (th + gap)))

        if num_shards == 1:
            out_path = out_dir / f"{base_name}.jpg"
        else:
            out_path = out_dir / f"{base_name}-{shard_idx + 1}.jpg"
        grid.save(str(out_path), quality=quality, optimize=True)
        saved_paths.append(str(out_path.relative_to(out_dir.parent)))

    return saved_paths


def _render_overview(pptx_path: Path, thumbs_dir: Path,
                     deck_id: str | None = None) -> tuple[bool, str]:
    """渲染全稿联图到 thumbs/overview.jpg。返回 (ok, reason_if_not)。

    主路径：soffice → pdf → pypdfium2 逐页渲染 → Pillow 拼 sqrt(N) 列网格 JPG。
    fallback 1: PIL 缺 → 直接把 pdf 拷到 thumbs/overview.pdf 供 MainAgent 自看。
    fallback 2: pypdfium2 缺 → 直接把 PDF 拷到 thumbs/overview.pdf 供 MainAgent 自看。
    fallback 3: soffice 缺 → 若 deck_id 已就绪，走 lark-cli drive +export 让飞书云端渲染 pdf；否则返回 (False, 'soffice_missing')。
    """
    thumbs_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = _pptx_to_pdf(pptx_path, thumbs_dir.parent / "_tmp_pdf")
    if not pdf_path and deck_id:
        # soffice 缺，走飞书云端导出兜底
        pdf_path = _export_deck_pdf_via_lark(deck_id, thumbs_dir.parent / "_tmp_pdf")
    if not pdf_path:
        # 到这里说明 soffice 缺且 (deck_id 未就绪 或 lark-cli 也不可用/失败)
        return False, "soffice_missing_and_lark_export_unavailable"

    try:
        import pypdfium2 as pdfium  # type: ignore
    except ImportError:
        # fallback 3: 直接把 pdf 拷过去
        shutil.copy2(pdf_path, thumbs_dir / "overview.pdf")
        return True, "pypdfium2_missing_pdf_used"

    try:
        from PIL import Image  # type: ignore
    except ImportError:
        # fallback 2: 无 PIL，用 pdfium 自己产一张大图
        # 策略：把每页 render 到 bitmap，靠 pdfium 单独做多 bitmap 拼接不现实，索性保留 PDF
        return _render_overview_no_pil(pdf_path, thumbs_dir)

    # 主路径:pypdfium2 + PIL 拼图 · 自动分片(单张 ≤ 3800px 给 Read 工具留 buffer)
    try:
        pdf = pdfium.PdfDocument(str(pdf_path))
        tiles = []
        # pdfium 用 scale (PDF 默认 72 dpi) · 40 dpi → scale = 40/72
        scale = 40.0 / 72.0
        for i in range(len(pdf)):
            page = pdf[i]
            bitmap = page.render(scale=scale)
            tiles.append(bitmap.to_pil().convert("RGB"))
            page.close()
        pdf.close()
        if not tiles:
            return False, "empty_pdf"
        saved = _compose_overview_grid(tiles, thumbs_dir, base_name="overview",
                                        max_side=3800, quality=60)
        if not saved:
            return False, "compose_failed"
        return True, "ok" if len(saved) == 1 else f"ok_sharded_{len(saved)}"
    except Exception as e:
        return False, f"render_error:{e}"


def _render_overview_no_pil(pdf_path: Path, thumbs_dir: Path) -> tuple[bool, str]:
    """无 PIL 时的兜底：直接把 PDF 拷贝到 thumbs/overview.pdf 供 MainAgent 查看。

    比拼接大图差点意思，但 pdfium 自己没法方便地做多 bitmap 拼接，索性保留 PDF。
    """
    try:
        shutil.copy2(pdf_path, thumbs_dir / "overview.pdf")
        return True, "pil_missing_pdf_used"
    except Exception as e:
        return False, f"copy_pdf_failed:{e}"


def _extract_images(pptx_path: Path, assets_dir: Path) -> list[dict]:
    """把 pptx 里所有 ppt/media/* 抽出来存到 assets/，返回清单。"""
    assets_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    with zipfile.ZipFile(pptx_path) as z:
        for name in z.namelist():
            if name.startswith("ppt/media/"):
                out_name = name.split("/")[-1]
                out_path = assets_dir / out_name
                out_path.write_bytes(z.read(name))
                manifest.append({
                    "filename": out_name,
                    "size_bytes": out_path.stat().st_size,
                    "local_path": str(out_path.relative_to(assets_dir.parent)),
                })
    return manifest


def _detect_capabilities() -> tuple[dict, list[str]]:
    """探测 4 个 pip 包 + soffice 是否可用。返回 (capabilities, install_hints)。"""
    caps = {
        "python_pptx": False,
        "pypdfium2":   False,
        "pil":         False,
        "lxml":        False,
        "soffice":     bool(shutil.which("soffice") or shutil.which("libreoffice")),
    }
    hints: list[str] = []

    try:
        from pptx import Presentation  # type: ignore  # noqa: F401
        caps["python_pptx"] = True
    except ImportError:
        hints.append("python-pptx 缺失——已用标准库降级 parser，manifest 字段精度略降")

    try:
        import pypdfium2  # type: ignore  # noqa: F401
        caps["pypdfium2"] = True
    except ImportError:
        hints.append("pypdfium2 缺失——联图渲染跳过或用 PDF 兜底")

    try:
        from PIL import Image  # type: ignore  # noqa: F401
        caps["pil"] = True
    except ImportError:
        hints.append("Pillow 缺失——联图无法拼接，改用 PDF 兜底")

    try:
        from lxml import etree  # type: ignore  # noqa: F401
        caps["lxml"] = True
    except ImportError:
        pass  # xml.etree fallback 已在 _fetch_and_split_slides 里

    return caps, hints


def _ensure_pip_deps(missing: list[str], per_pkg_timeout: int = 60) -> list[dict]:
    """尝试用当前解释器的 pip 补装缺失的包。

    - 不指定 --index-url · 依赖运行环境（豆包客户端）内置 pip 源
    - 每个包单独 timeout · 失败/超时静默返回状态,不阻塞主流程
    - 已有 fallback 会兜住所有失败场景（pypdfium2 缺 → PDF 兜底 · lxml 缺 → xml.etree 兜底 等）

    返回每个包的安装结果 [{"pkg": ..., "ok": ..., "reason": ...}] 供 stdout 日志用。
    """
    report: list[dict] = []
    for pkg in missing:
        cmd = [sys.executable, "-m", "pip", "install", "--quiet", "--disable-pip-version-check", pkg]
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=per_pkg_timeout,
            )
            if proc.returncode == 0:
                report.append({"pkg": pkg, "ok": True, "reason": "installed"})
            else:
                # pip 失败 · 常见原因:网络 / 权限 / 找不到包
                tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-1:]
                reason = "; ".join(tail)[:200] if tail else f"exit {proc.returncode}"
                report.append({"pkg": pkg, "ok": False, "reason": f"pip_failed:{reason}"})
        except subprocess.TimeoutExpired:
            report.append({"pkg": pkg, "ok": False, "reason": f"pip_timeout_after_{per_pkg_timeout}s"})
        except FileNotFoundError:
            report.append({"pkg": pkg, "ok": False, "reason": "python_or_pip_missing"})
            break  # pip 都没有 · 后续都装不上
        except Exception as e:
            report.append({"pkg": pkg, "ok": False, "reason": f"exception:{type(e).__name__}"})
    return report


def _is_retryable_error(returncode: int | None, stderr: str, timed_out: bool,
                        stdout: str = "") -> bool:
    """判定一次 subprocess 失败是否值得重试。

    重试：timeout / 网络类关键词 / 5xx / 429
    不重试：4xx / auth / param / 明确的业务错误

    注意:lark-cli 会把 API 侧错误 JSON 直接写在 stdout 里(rc≠0),所以需要同时扫 stdout 和 stderr。
    """
    if timed_out:
        return True

    s = ((stderr or "") + "\n" + (stdout or "")).lower()

    # 明确不重试的信号（fail-fast）
    non_retryable_signals = [
        "unauthorized", "unauthenticated", "forbidden",
        "invalid param", "bad request", "not found",
        "no such file", "permission denied",
        "401", "403", "404",
        "400 ", "400:", "code\":400",
        "invalid_grant", "invalid_token", "invalid_arg",
        # 注意:"token expired" 不放在这里 · lark-cli 的 temporary token 过期是常态,
        # subprocess 重启会自动 re-auth · 应该重试(见 retryable_signals)
    ]
    for sig in non_retryable_signals:
        if sig in s:
            return False

    # 明确要重试的信号
    retryable_signals = [
        "timeout", "timed out",
        "connection reset", "connection refused", "connection aborted",
        "connection error", "network is unreachable", "network error",
        "temporary failure", "eof", "broken pipe",
        "5xx", "internal server error", "bad gateway", "service unavailable", "gateway timeout",
        "500 ", "502 ", "503 ", "504 ",
        "429", "rate limit", "too many requests",
        # lark-cli 特有:临时 token 过期(subprocess 重启会自动重新 auth · 值得重试)
        "temporary token expired", "token expired",
        # lark-cli 特有:非标 JSON 响应(内部错误 · 值得重试)
        "invalid_response", "invalid json response",
    ]
    for sig in retryable_signals:
        if sig in s:
            return True

    # returncode 非 0 但 stderr 没啥明显信号：默认不重试（避免死循环重试参数错）
    return False


def _is_unknown_flag(stdout: str, stderr: str, flag: str) -> bool:
    """判断 CLI 输出是否为「不认识 flag」错误(区分于服务端拒收)。

    lark-cli 老版本(<1.0.96)缺 --no-lint,首次调用会报 invalid_arg + `unknown flag "--no-lint"`,
    此时调用方应去掉该 flag 重试;若是服务端 3350001/3350002 拒收,则不该重试。
    """
    text = (stdout or "") + "\n" + (stderr or "")
    if "unknown flag" in text and flag in text:
        return True
    # lark-cli JSON envelope: error.subtype=invalid_argument + params[].reason=unknown flag
    try:
        idx = text.find("{")
        if idx >= 0:
            envelope = json.loads(text[idx:])
            err = (envelope or {}).get("error") or {}
            if err.get("subtype") == "invalid_argument":
                for p in err.get("params") or []:
                    if p.get("name") == flag and p.get("reason") == "unknown flag":
                        return True
    except Exception:
        pass
    return False


def _run_with_retry(cmd: list[str], cwd: str | None, timeout: int,
                    max_attempts: int = 3, backoff_base: float = 2.0,
                    op_name: str = "", max_backoff: float = 30.0,
                    total_deadline_sec: float | None = None) -> tuple[int | None, str, str, bool]:
    """联网 subprocess 包装。3 次尝试、指数退避 2s/4s（+jitter），只在可重试错误上重试。

    - max_backoff:单次退避上限(秒)· 默认 30s · 避免退到 128/256s 的死等
    - total_deadline_sec:整个 retry 循环的总时间预算(秒)· 到点即使还有 attempts 也停

    返回 (returncode, stdout, stderr, timed_out)。
    timed_out=True 时 returncode 可能为 None、stderr 是超时说明。
    op_name 只用于日志。
    """
    import random
    import time as _time

    last_rc: int | None = -1
    last_stdout, last_stderr, last_timeout = "", "", False
    deadline = _time.monotonic() + total_deadline_sec if total_deadline_sec else None

    for attempt in range(1, max_attempts + 1):
        try:
            proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
            last_rc = proc.returncode
            last_stdout = proc.stdout
            last_stderr = proc.stderr
            last_timeout = False
            if proc.returncode == 0:
                return proc.returncode, proc.stdout, proc.stderr, False
        except subprocess.TimeoutExpired:
            last_rc = None
            last_stdout = ""
            last_stderr = f"timeout after {timeout}s ({op_name or ' '.join(cmd[:3])})"
            last_timeout = True
        except FileNotFoundError:
            # binary 缺失，重试没意义
            return None, "", f"binary not found: {cmd[0]}", False

        # 判断是否值得重试
        if not _is_retryable_error(last_rc, last_stderr, last_timeout, stdout=last_stdout):
            break
        if attempt >= max_attempts:
            break
        # deadline 检查:总预算耗尽就停(避免长期死等)
        if deadline is not None and _time.monotonic() >= deadline:
            last_stderr = (last_stderr or "") + f" | total_deadline_{total_deadline_sec}s_exhausted"
            break

        # 指数退避 + jitter · 单次不超过 max_backoff
        # rate_limit 时 jitter 加大到 100%(full jitter),避免多个并发调用同步撞在同一秒
        sleep_sec = min(max_backoff, backoff_base * (2 ** (attempt - 1)))
        s_lower = ((last_stderr or "") + "\n" + (last_stdout or "")).lower()
        jitter_ratio = 1.0 if ("rate_limit" in s_lower or "rate limit" in s_lower
                                or "too many requests" in s_lower or "429" in s_lower) else 0.25
        sleep_sec += random.uniform(0, sleep_sec * jitter_ratio)
        # deadline 检查:若睡完就超时,少睡点(留点余地跑最后一次)
        if deadline is not None:
            remaining = deadline - _time.monotonic()
            if remaining <= 0:
                break
            sleep_sec = min(sleep_sec, remaining - 0.5)
            if sleep_sec <= 0:
                continue
        _time.sleep(sleep_sec)

    return last_rc, last_stdout, last_stderr, last_timeout


def _import_pptx_to_lark(pptx_path: Path, work: Path, deck_title: str | None = None,
                          timeout: int = 300, max_attempts: int = 5) -> dict:
    """`lark-cli drive +import` 导入 pptx 到飞书，返回 {ok, xml_presentation_id, url, revision_id, error}.

    输入 pptx 必须已经复制到 work 目录内（--file 只接受相对路径）。
    deck_title 可选：传了就作为 --name 参数覆盖默认（默认走本地 pptx 文件名）。
    """
    # 保证 pptx 在 work 内
    try:
        rel_pptx = pptx_path.relative_to(work)
    except ValueError:
        target = work / pptx_path.name
        if not target.exists():
            shutil.copy2(pptx_path, target)
        rel_pptx = target.relative_to(work)

    cmd = [
        "lark-cli", "drive", "+import",
        "--file", f"./{rel_pptx}",
        "--type", "slides",
        "--json",
    ]
    if deck_title:
        cmd += ["--name", deck_title]
    rc, stdout, stderr, timed_out = _run_with_retry(
        cmd, cwd=str(work), timeout=timeout, max_attempts=max_attempts, op_name="drive +import"
    )
    if stderr and "binary not found" in stderr:
        return {"ok": False, "error": "lark-cli binary not found in PATH"}
    if timed_out:
        return {"ok": False, "error": stderr or f"lark-cli drive +import timeout after {timeout}s (all retries exhausted)"}
    if rc != 0:
        return {"ok": False, "error": f"drive +import exit {rc}: {(stderr or '')[:500]}"}

    # 找第一个 JSON 对象
    stdout = stdout.strip()
    idx = stdout.find("{")
    if idx < 0:
        return {"ok": False, "error": f"no JSON in stdout: {stdout[:300]}"}
    try:
        env = json.loads(stdout[idx:])
    except json.JSONDecodeError as e:
        return {"ok": False, "error": f"json decode failed: {e}; stdout={stdout[:300]}"}

    if not env.get("ok"):
        return {"ok": False, "error": f"import returned ok=false: {env}"}

    # 关键字段：drive +import 可能同步返回，也可能返回 ticket 需要再查
    data = env.get("data", {})
    pres_id = data.get("xml_presentation_id") or data.get("token") or data.get("obj_token")
    url = data.get("url")
    if pres_id:
        return {
            "ok": True,
            "xml_presentation_id": pres_id,
            "url": url or "",
            "revision_id": data.get("revision_id"),
        }

    # 无 pres_id · 检查是否是 async ticket（大文件 · > 5-10 MB 走这条路径）
    ticket = data.get("ticket")
    if not ticket:
        return {"ok": False, "error": f"no xml_presentation_id in response: {data}"}

    # 轮询 ticket 直到 ready · 递增间隔 2s → 5s → 10s · 上限 5 分钟
    import time as _time
    poll_intervals = [2, 3, 5, 5, 10, 10, 10, 15, 15, 20, 20, 30, 30, 30, 30, 30, 30, 30, 30]
    elapsed = 0
    for wait_sec in poll_intervals:
        _time.sleep(wait_sec)
        elapsed += wait_sec
        poll_cmd = [
            "lark-cli", "drive", "+task_result",
            "--scenario", "import",
            "--ticket", str(ticket),
            "--json",
        ]
        prc, pstdout, pstderr, ptimeout = _run_with_retry(
            poll_cmd, cwd=str(work), timeout=60, op_name=f"task_result ticket={ticket}"
        )
        if ptimeout or prc != 0:
            continue  # 单次 poll 失败 · 继续下轮
        pidx = pstdout.find("{")
        if pidx < 0:
            continue
        try:
            penv = json.loads(pstdout[pidx:])
        except json.JSONDecodeError:
            continue
        if not penv.get("ok"):
            continue
        pdata = penv.get("data", {})
        # 检查完成状态
        if pdata.get("failed"):
            return {"ok": False, "error": f"import ticket={ticket} failed: {pdata.get('job_error_msg', 'unknown')}"}
        if pdata.get("ready"):
            # 完成 · 取 token
            pres_id = pdata.get("token") or pdata.get("xml_presentation_id") or pdata.get("obj_token")
            if not pres_id:
                return {"ok": False, "error": f"import ticket={ticket} ready but no token: {pdata}"}
            return {
                "ok": True,
                "xml_presentation_id": pres_id,
                "url": pdata.get("url") or "",
                "revision_id": pdata.get("revision_id"),
            }
        # ready=false · 继续等
    return {"ok": False, "error": f"import ticket={ticket} not ready after {elapsed}s polling · timeout"}


def _fetch_single_slide_xml(xml_presentation_id: str, slide_number: int,
                             work: Path, source_dir: Path,
                             timeout: int, max_attempts: int) -> tuple[int, dict | None]:
    """单页拉一页 SXSD · 返回 (slide_number, {slide_id, path} 或 None)。

    走 --slide-number 单页拉,失败返回 None(不阻塞其他页)。
    """
    rel_output = f"source-slides/slide-{slide_number:02d}.xml"
    cmd = [
        "lark-cli", "slides", "+xml-get",
        "--presentation", xml_presentation_id,
        "--slide-number", str(slide_number),
        "--output", rel_output,
        "--json",
    ]
    rc, _stdout, _stderr, _ = _run_with_retry(
        cmd, cwd=str(work), timeout=timeout, max_attempts=max_attempts,
        op_name=f"+xml-get slide {slide_number}"
    )
    if rc != 0:
        return slide_number, None
    xml_path = source_dir / f"slide-{slide_number:02d}.xml"
    if not xml_path.exists():
        return slide_number, None
    # 从单页 XML 里抽 slide_id(顶层 <slide id="...">)
    try:
        content = xml_path.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r'<slide[^>]*\bid="([^"]+)"', content)
        slide_id = m.group(1) if m else ""
    except Exception:
        slide_id = ""
    return slide_number, {
        "slide_id": slide_id,
        "local_xml_path": str(xml_path.relative_to(work)),
    }


def _fetch_slides_per_page(xml_presentation_id: str, work: Path, source_dir: Path,
                            total_slides: int, timeout: int, max_attempts: int,
                            concurrency: int = 4,
                            phase_deadline_sec: float | None = None) -> dict:
    """分页兜底:并发单页拉 SXSD。用在全稿 +xml-get 因服务端 timeout 失败后。

    concurrency 默认 4(读 API 限流比写宽松,飞书 read ~= 20 QPS)。
    用 wait(timeout=5) 轮询 + pool.shutdown(wait=True) 保证不死锁。
    phase_deadline_sec:阶段总预算 · 默认 max(300, 页数 × 2s) · 到点即停,归入 failed。
    返回 {ok, slides: [...], failed: [...], error}。
    """
    from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
    import time as _time

    if phase_deadline_sec is None:
        phase_deadline_sec = max(300.0, min(1200.0, total_slides * 2.0))
    phase_deadline = _time.monotonic() + phase_deadline_sec

    results: dict[int, dict | None] = {}
    pool = ThreadPoolExecutor(max_workers=concurrency)
    try:
        futures = {
            pool.submit(_fetch_single_slide_xml, xml_presentation_id, n,
                        work, source_dir, timeout, max_attempts): n
            for n in range(1, total_slides + 1)
        }
        pending = set(futures.keys())
        while pending:
            done, pending = wait(pending, timeout=5.0, return_when=FIRST_COMPLETED)
            for fut in done:
                try:
                    n, meta = fut.result(timeout=0)
                    results[n] = meta
                except Exception:
                    n = futures[fut]
                    results[n] = None
            if _time.monotonic() >= phase_deadline:
                for fut in pending:
                    n = futures[fut]
                    fut.cancel()
                    results.setdefault(n, None)
                pending = set()
                break
    finally:
        pool.shutdown(wait=True, cancel_futures=True)

    slides_meta = []
    failed = []
    for n in range(1, total_slides + 1):
        m = results.get(n)
        if m is None:
            failed.append(n)
        else:
            slides_meta.append({
                "slide_num": n,
                "slide_id": m["slide_id"],
                "local_xml_path": m["local_xml_path"],
            })

    if failed:
        return {
            "ok": False,
            "slides": slides_meta,
            "failed": failed,
            "error": f"per-page fetch failed for {len(failed)}/{total_slides} slides: {failed[:20]}",
        }
    return {"ok": True, "slides": slides_meta}


def _fetch_and_split_slides(xml_presentation_id: str, work: Path,
                             timeout: int = 300, max_attempts: int = 5,
                             total_slides_hint: int | None = None,
                             prefer_per_page_threshold: int = 30) -> dict:
    """`+xml-get` 拉全稿 SXSD → 拆成每页 XML 落到 source-slides/slide-NN.xml。

    路径选择:
    - 小 deck(页数 < prefer_per_page_threshold,默认 30)· 或页数未知 → 走整包一次拉(1 API 调用 · 秒完)
    - 大 deck(页数 >= 30)→ **直接** 4 并发单页拉 · 跳过整包(避免服务端 timeout 之后再兜底,浪费 5-15 分钟)

    整包失败时也会兜底到单页并发(用作双保险 · 但主路径已经能避开)。

    返回 {ok, full_xml_path, slides: [{slide_num, slide_id, local_xml_path}], error}
    """
    source_dir = work / "source-slides"
    source_dir.mkdir(parents=True, exist_ok=True)

    # 大 deck 直接走单页并发(整包 API 服务端序列化慢 · 常 timeout)
    if total_slides_hint and total_slides_hint >= prefer_per_page_threshold:
        per_page_result = _fetch_slides_per_page(
            xml_presentation_id, work, source_dir, total_slides_hint,
            timeout=90, max_attempts=3, concurrency=4,
        )
        got_slides = per_page_result.get("slides", [])
        if per_page_result["ok"] or (got_slides and len(got_slides) >= total_slides_hint * 0.8):
            failed_pages = per_page_result.get("failed", [])
            return {
                "ok": True,
                "full_xml_path": None,
                "slides": got_slides,
                "fallback_used": "per_page_fetch_direct" if per_page_result["ok"] else "per_page_fetch_direct_partial",
                "per_page_failed_pages": failed_pages,
            }
        # 单页兜底也大量失败(<80%) · hard fail
        return {
            "ok": False,
            "error": f"per-page fetch failed for {len(per_page_result.get('failed', []))}/{total_slides_hint} slides",
            "partial_slides": got_slides,
            "failed_slide_numbers": per_page_result.get("failed", []),
        }

    # 小 deck / 未知页数 → 走整包一次拉
    rel_output = "source-slides/full.xml"
    cmd = [
        "lark-cli", "slides", "+xml-get",
        "--presentation", xml_presentation_id,
        "--output", rel_output,
        "--json",
    ]
    rc, _stdout, stderr, timed_out = _run_with_retry(
        cmd, cwd=str(work), timeout=timeout, max_attempts=max_attempts, op_name="slides +xml-get"
    )
    if stderr and "binary not found" in stderr:
        return {"ok": False, "error": "lark-cli binary not found in PATH"}

    # 整包失败(小 deck 但服务端偶发)→ 兜底单页并发
    if (timed_out or rc != 0) and total_slides_hint and total_slides_hint > 0:
        per_page_result = _fetch_slides_per_page(
            xml_presentation_id, work, source_dir, total_slides_hint,
            timeout=90, max_attempts=3, concurrency=4,
        )
        got_slides = per_page_result.get("slides", [])
        if per_page_result["ok"] or (got_slides and len(got_slides) >= total_slides_hint * 0.8):
            failed_pages = per_page_result.get("failed", [])
            return {
                "ok": True,
                "full_xml_path": None,
                "slides": got_slides,
                "fallback_used": "per_page_fetch" if per_page_result["ok"] else "per_page_fetch_partial",
                "full_xml_error": f"server timeout on full fetch: {(_stdout or stderr or '')[:200]}",
                "per_page_failed_pages": failed_pages,
            }
        detail = (_stdout or stderr or '').strip()[:400]
        return {
            "ok": False,
            "error": (
                f"+xml-get full fetch exit {rc} ({'timeout' if timed_out else 'server error'}): {detail}\n"
                f"per-page fallback also failed: {per_page_result['error']}"
            ),
            "partial_slides": per_page_result.get("slides", []),
            "failed_slide_numbers": per_page_result.get("failed", []),
        }

    if timed_out:
        return {"ok": False, "error": stderr or f"lark-cli +xml-get timeout after {timeout}s (all retries exhausted)"}
    if rc != 0:
        detail = (_stdout or stderr or '').strip()[:800]
        return {"ok": False, "error": f"+xml-get exit {rc}: {detail}"}

    full_xml_path = source_dir / "full.xml"
    if not full_xml_path.exists():
        return {"ok": False, "error": f"full.xml not written: {full_xml_path}"}

    # 用 lxml 解析拆页；命名空间从根元素读，不硬编码
    try:
        from lxml import etree as LET
    except ImportError:
        import xml.etree.ElementTree as LET  # type: ignore

    tree = LET.parse(str(full_xml_path))
    root = tree.getroot()
    # 命名空间：从 tag 里抠出来，形如 "{ns}presentation"
    m = re.match(r"\{([^}]+)\}", root.tag)
    ns = m.group(1) if m else ""
    slide_tag = f"{{{ns}}}slide" if ns else "slide"
    slides_meta = []
    for i, slide in enumerate(root.findall(slide_tag), start=1):
        slide_id = slide.get("id") or ""
        # 序列化单页
        try:
            # lxml 优先
            xml_str = LET.tostring(slide, encoding="unicode")  # type: ignore[attr-defined]
        except TypeError:
            # xml.etree
            import xml.etree.ElementTree as StdET
            xml_str = StdET.tostring(slide, encoding="unicode")

        # 补上根 xmlns 声明，让每页 XML 是可解析的独立 fragment
        if ns and f"xmlns=" not in xml_str[:200]:
            xml_str = xml_str.replace(
                f"<{{{ns}}}slide", f"<slide xmlns=\"{ns}\"", 1
            )
        # lxml 输出的 tag 会带 {ns} 前缀，需要清理成纯 slide 标签
        if ns:
            xml_str = xml_str.replace(f"{{{ns}}}", "")

        out_path = source_dir / f"slide-{i:02d}.xml"
        out_path.write_text(xml_str, encoding="utf-8")
        slides_meta.append({
            "slide_num": i,
            "slide_id": slide_id,
            "local_xml_path": str(out_path.relative_to(work)),
        })

    return {
        "ok": True,
        "full_xml_path": str(full_xml_path.relative_to(work)),
        "slides": slides_meta,
    }


def _delete_single_slide_no_retry(deck_id: str, sid: str, work: Path,
                                    timeout: int = 15) -> tuple[str, bool, str]:
    """删单页 · **单次尝试 · 不重试**。失败立即返回 · 交给上层批量收集。

    专门给"扫过一遍先删能删的 · 剩下的报告给上层重试"这种模式用。
    """
    cmd = [
        "lark-cli", "slides", "+delete-slide",
        "--presentation", deck_id,
        "--slide-id", sid,
        "--json",
    ]
    try:
        proc = subprocess.run(cmd, cwd=str(work), capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return sid, False, f"timeout after {timeout}s"
    except FileNotFoundError:
        return sid, False, "lark-cli binary not found"
    if proc.returncode == 0:
        return sid, True, ""
    detail = (proc.stdout or proc.stderr or "").strip()[:200]
    return sid, False, f"exit {proc.returncode}: {detail}"


def _purge_deck_to_one_page(deck_id: str, slide_ids: list[str], work: Path,
                             phase_deadline_sec: float | None = None) -> dict:
    """删掉除第 1 页外的所有页 + 把第 1 页覆盖成空白 slide。

    一趟扫 · 单次尝试 · 无退避 · 失败即跳。失败页 slide_id 汇总到 failed_slide_ids · MainAgent 调 purge_deck.py 补删。
    保留第 1 页做 master/theme 锚点(全删则后续 +add-slide 报 block is empty)。
    phase_deadline_sec 默认按页数动态:每页 2s · 3-15 分钟。

    返回 {ok, first_page_slide_id, deleted_count, cleared_first_page,
          failed_slide_ids, next_action_hint, error}。
    """
    if not slide_ids:
        return {"ok": False, "error": "empty slide_ids"}

    first_id = slide_ids[0]
    to_delete = slide_ids[1:]

    if phase_deadline_sec is None:
        phase_deadline_sec = max(180.0, min(900.0, len(to_delete) * 2.0))

    import time as _time
    phase_deadline = _time.monotonic() + phase_deadline_sec

    # (1) 一趟扫 · 无退避 · 单次尝试 · 失败即跳
    deleted = 0
    failures: list[tuple[str, str]] = []

    for i, sid in enumerate(to_delete):
        if _time.monotonic() >= phase_deadline:
            failures.extend([(s, "phase_deadline_exhausted") for s in to_delete[i:]])
            break
        _, ok, err = _delete_single_slide_no_retry(deck_id, sid, work, timeout=15)
        if ok:
            deleted += 1
        else:
            failures.append((sid, err))

    # (2) 把第 1 页清空成空白 slide(+update-slide 覆盖)· 这一步用带重试的版本(只 1 次调用 · 重试可控)
    # 默认带 --no-lint(空白页只是占位 · 服务端 lint 只会误报)· lark-cli < 1.0.96 无此 flag,
    # 遇到 unknown flag 就去掉重试。unknown flag 属于 invalid_arg,_is_retryable_error 归类为
    # 非重试,首次失败就返回,不会浪费重试次数。
    empty_xml_path = work / ".empty-slide.xml"
    empty_xml_path.write_text(
        f'<slide xmlns="https://www.larkoffice.com/sml/2.0" id="{first_id}"></slide>',
        encoding="utf-8",
    )
    cleared_first_page = False
    clear_error = None
    try:
        base_cmd = [
            "lark-cli", "slides", "+update-slide",
            "--presentation", deck_id,
            "--slide-id", first_id,
            "--content", "@.empty-slide.xml",
            "--json",
        ]
        rc, _stdout, stderr = None, "", ""
        timed_out = False
        for extra_flags in (["--no-lint"], []):
            rc, _stdout, stderr, timed_out = _run_with_retry(
                base_cmd + extra_flags, cwd=str(work), timeout=60, max_attempts=3,
                op_name="+update-slide (clear first page)",
                max_backoff=10.0,
                total_deadline_sec=45.0,
            )
            if not timed_out and rc == 0:
                break
            if extra_flags and _is_unknown_flag(_stdout, stderr, "--no-lint"):
                continue
            break
        empty_xml_path.unlink(missing_ok=True)
        if timed_out or rc != 0:
            clear_error = f"clear first page failed (non-fatal): rc={rc}: {(stderr or 'timeout')[:200]}"
        else:
            cleared_first_page = True
    except Exception as e:
        empty_xml_path.unlink(missing_ok=True)
        clear_error = f"clear first page exception: {e}"

    # (3) 汇总结果
    failed_sids = [sid for sid, _ in failures]
    result = {
        "ok": True,  # 一趟扫完就算 ok · 残留页交给上层处理
        "first_page_slide_id": first_id,
        "deleted_count": deleted,
        "failed_count": len(failed_sids),
        "failed_slide_ids": failed_sids,
        "cleared_first_page": cleared_first_page,
    }
    if clear_error:
        result["clear_error"] = clear_error
    if failed_sids:
        result["next_action_hint"] = (
            f"{len(failed_sids)} 页未删 · MainAgent 应调 purge_deck.py --slide-ids <逗号分隔>"
        )
    return result


# ============================================================
# content-skeleton 提取: 从每个 active_rebuild content 页里, 只保留跨 3+ 页复用的
# brand_assets(背景/页眉/页脚/装饰线/logo/水印), 中部留空。Step 5.2 应 cp 骨架而非
# cp source-slides/slide-NN.xml, 防止 template_copy_overfit lint P0 阻断。
# ============================================================

_SKELETON_SXSD_NS = "https://www.larkoffice.com/sml/2.0"


def _skel_local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _skel_round_to(v: str, step: int = 10) -> int:
    try:
        return int(round(float(v))) // step * step
    except Exception:
        return 0


def _skel_extract_fill_sig(elem: ET.Element) -> str:
    """从 shape 的 <fill> 子节点抽出一个短签名 —— fillColor / fillImg src / 首个 fillColor 值。"""
    parts = []
    for child in elem.iter():
        tag = _skel_local(child.tag)
        if tag == "fillColor":
            color = (child.get("color") or "")[:40]
            parts.append(f"c={color}")
            break
        if tag == "fillImg":
            src = (child.get("src") or "")[:20]
            parts.append(f"i={src}")
            break
    return "|".join(parts) or "-"


def _skel_shape_signature(elem: ET.Element) -> tuple:
    """位置+尺寸+fill 综合签名 —— 相同签名的元素视为同一 brand asset。"""
    tag = _skel_local(elem.tag)
    if tag == "img":
        src = (elem.get("src") or "")[:20]
        w = _skel_round_to(elem.get("width", "0"), 10)
        h = _skel_round_to(elem.get("height", "0"), 10)
        x = _skel_round_to(elem.get("topLeftX", "0"), 10)
        y = _skel_round_to(elem.get("topLeftY", "0"), 10)
        return (tag, "img", src, w, h, x, y)
    if tag == "line":
        sx = _skel_round_to(elem.get("startX", "0"), 10)
        sy = _skel_round_to(elem.get("startY", "0"), 10)
        ex = _skel_round_to(elem.get("endX", "0"), 10)
        ey = _skel_round_to(elem.get("endY", "0"), 10)
        return (tag, "line", sx, sy, ex, ey)
    typ = elem.get("type", "?")
    w = _skel_round_to(elem.get("width", "0"), 10)
    h = _skel_round_to(elem.get("height", "0"), 10)
    x = _skel_round_to(elem.get("topLeftX", "0"), 10)
    y = _skel_round_to(elem.get("topLeftY", "0"), 10)
    fill = _skel_extract_fill_sig(elem)
    return (tag, typ, w, h, x, y, fill)


def _skel_has_text_content(elem: ET.Element) -> bool:
    """判断 shape 是否含实际文字(非纯空格)—— 有文字的 shape 大概率是内容占位符,不是纯装饰。"""
    for span in elem.iter():
        if _skel_local(span.tag) != "span":
            continue
        text = (span.text or "").strip()
        if text:
            return True
    return False


def _skel_load_source_slides(source_dir: Path) -> list[tuple[int, str, ET.Element]]:
    """读所有 source-slides/slide-NN.xml, 返回 [(slide_num, sid, root_element), ...]"""
    slides = []
    for xml_path in sorted(source_dir.glob("slide-*.xml")):
        m = re.search(r'slide-(\d+)', xml_path.name)
        if not m:
            continue
        n = int(m.group(1))
        try:
            root = ET.fromstring(xml_path.read_text(encoding="utf-8"))
            sid = root.get("id", "")
            slides.append((n, sid, root))
        except ET.ParseError as e:
            print(f"WARN: parse failed for {xml_path.name}: {e}", file=sys.stderr)
    return slides


def _skel_compute_brand_asset_signatures(slides: list[tuple[int, str, ET.Element]],
                                          content_page_nums: set[int],
                                          min_cross_page: int = 3,
                                          min_size: int = 20,
                                          max_per_page_dup: int = 3) -> set[tuple]:
    """扫全部 content 页的 <data> 子元素, 统计每个 signature 出现在多少页。

    出现在 >= min_cross_page 个 content 页的 signature = brand_asset 候选。

    过滤两类"装饰噪音"(非真正 brand_asset):
    1. **小尺寸装饰**(w < min_size 且 h < min_size): 模板作者用几百个小 shape 拼装饰纹理,
       每页复用但不是品牌资产, 是需要删的模板残留(例: sl079/problem_deck 的 5x5 小圆点群)
    2. **单页高频复用**(同签名在同一页出现 > max_per_page_dup 次): 真正的 brand_asset
       每页至多 1-2 个(logo/页眉/页脚), 出现更多次说明是装饰群
    """
    sig_pages: dict[tuple, set[int]] = defaultdict(set)
    sig_per_page_count: dict[tuple, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    sig_min_size: dict[tuple, tuple[int, int]] = {}

    for n, _sid, root in slides:
        if n not in content_page_nums:
            continue
        for data in root:
            if _skel_local(data.tag) != "data":
                continue
            for child in data:
                tag = _skel_local(child.tag)
                if tag not in ("shape", "line", "img", "icon", "table", "chart", "embed", "polyline"):
                    continue
                sig = _skel_shape_signature(child)
                sig_pages[sig].add(n)
                sig_per_page_count[sig][n] += 1
                if sig not in sig_min_size:
                    try:
                        w = int(round(float(child.get("width", "0"))))
                        h = int(round(float(child.get("height", "0"))))
                    except Exception:
                        w = h = 0
                    sig_min_size[sig] = (w, h)

    brand_sigs = set()
    for sig, pages in sig_pages.items():
        if len(pages) < min_cross_page:
            continue
        max_per_page = max(sig_per_page_count[sig].values())
        if max_per_page > max_per_page_dup:
            continue
        w, h = sig_min_size.get(sig, (0, 0))
        tag = sig[0]
        if tag != "line" and 0 < w < min_size and 0 < h < min_size:
            continue
        brand_sigs.add(sig)
    return brand_sigs


def _skel_extract_for_page(root: ET.Element, brand_sigs: set[tuple]) -> str:
    """从一个 slide 的 root 提取只含 brand_assets 的骨架 XML。

    保留: <style> 节点、<data> 里 signature ∈ brand_sigs 且不含文字的 shape
    删除: <note>、内容占位 shape、非 brand_asset 装饰
    """
    ET.register_namespace("", _SKELETON_SXSD_NS)

    new_root = ET.Element(root.tag, attrib=dict(root.attrib))

    for child in root:
        tag = _skel_local(child.tag)
        if tag == "note":
            continue
        if tag == "style":
            new_root.append(child)
            continue
        if tag == "data":
            new_data = ET.SubElement(new_root, child.tag, attrib=dict(child.attrib))
            for gc in child:
                gc_tag = _skel_local(gc.tag)
                if gc_tag not in ("shape", "line", "img", "icon", "table", "chart", "embed", "polyline"):
                    new_data.append(gc)
                    continue
                sig = _skel_shape_signature(gc)
                if sig in brand_sigs and not _skel_has_text_content(gc):
                    new_data.append(gc)
            content_hint = ET.Comment(
                " 内容区留空 · 按 refine-examples/<style>/<sub-type>.md 里的页型骨架从零填内容 shape。"
                "禁止 cp source-slides 保留内容占位符和装饰群(会触发 template_copy_overfit lint P0 阻断)。 "
            )
            new_data.append(content_hint)
            continue
        new_root.append(child)

    xml_bytes = ET.tostring(new_root, encoding="utf-8", xml_declaration=False)
    xml_str = xml_bytes.decode("utf-8")

    header = (
        "<!-- 内容页骨架 · 由 parse_template.py 自动生成 · 仅保留跨 3+ 页复用的 brand_assets。"
        "Step 5.2 应 cp 本文件到 authoring/slide-NN.xml, 然后 Write 填内容 shape。 -->\n"
    )
    return header + xml_str


def _extract_content_skeletons(source_dir: Path, out_dir: Path,
                                total_slides: int,
                                min_cross_page: int = 3) -> dict[int, str]:
    """对 source-slides/ 里除首页/尾页(和第 2 页的 TOC)外的所有页, 产 content-skeleton 骨架。

    返回 {slide_num: 骨架文件相对 out_dir.parent.parent(即 work_dir) 的路径}。
    产物落到 out_dir/slide-NN.content-skeleton.xml。
    """
    slides = _skel_load_source_slides(source_dir)
    if not slides:
        return {}

    all_nums = [n for n, _, _ in slides]
    # 启发式判定 content 页: 除首页/尾页外都算 content;>=4 页时排除第 2 页(TOC 候选)
    if len(all_nums) <= 2:
        content_page_nums: set[int] = set(all_nums)
    else:
        content_page_nums = set(all_nums) - {min(all_nums), max(all_nums)}
        if len(all_nums) >= 4:
            content_page_nums.discard(sorted(all_nums)[1])

    brand_sigs = _skel_compute_brand_asset_signatures(
        slides, content_page_nums, min_cross_page=min_cross_page
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    work_dir = out_dir.parent.parent  # manifest/content-skeletons/ -> WORK_DIR
    paths: dict[int, str] = {}
    for n, _sid, root in slides:
        if n not in content_page_nums:
            continue
        skel = _skel_extract_for_page(root, brand_sigs)
        out_path = out_dir / f"slide-{n:02d}.content-skeleton.xml"
        out_path.write_text(skel, encoding="utf-8")
        try:
            paths[n] = str(out_path.relative_to(work_dir))
        except ValueError:
            paths[n] = str(out_path)
    return paths


def _extract_decorations(source_slides_dir: Path) -> dict:
    """扫 source-slides/*.xml，抽出每页的**非图片装饰** shape 清单。

    装饰指："纯 shape"（rect / ellipse / line / triangle / round-rect / custom / cxnSp 等），
    不含 <img>、不含带正文文本的 shape。这些是 MainAgent 做"borrow-decorations"策略时的
    候选池——可以从模板的某页借装饰形状到另一页，跨 deck 时 img 会失败但纯 shape 安全。

    产物结构：
        {
          "by_slide": {
            "1": [
              {
                "shape_id": "btu",
                "type": "rect",
                "bbox": {"x": 0, "y": 411.28, "w": 960, "h": 128.72},
                "fill": "rgba(34, 69, 129, 1)",
                "signature": "rect|fill=rgba(34,69,129,1)|w=960|h=129"
              },
              ...
            ],
            ...
          },
          "total_decorations": N,
          "scanned_slides": M
        }

    signature 用于跨页去重与"多页复用"判定（brand_assets 的核心线索）。
    """
    if not source_slides_dir.exists():
        return {"by_slide": {}, "total_decorations": 0, "scanned_slides": 0}

    try:
        from lxml import etree as LET  # type: ignore
    except ImportError:
        import xml.etree.ElementTree as LET  # type: ignore

    by_slide: dict[str, list[dict]] = {}
    total = 0
    scanned = 0

    # 纯装饰形状类型白名单（含 SXSD 常见 preset 名）
    DECOR_TYPES = {
        "rect", "round-rect", "ellipse", "line", "triangle",
        "diamond", "pentagon", "hexagon", "octagon", "parallelogram",
        "trapezoid", "custom", "arc", "chord", "pie", "cxnSp",
        "right-triangle", "star-5", "star-4", "star-6", "arrow",
    }

    for xml_path in sorted(source_slides_dir.glob("slide-*.xml")):
        m = re.search(r"slide-(\d+)", xml_path.name)
        if not m:
            continue
        slide_num = int(m.group(1))
        scanned += 1

        try:
            tree = LET.parse(str(xml_path))
        except Exception:
            continue

        root = tree.getroot()
        # 去 namespace 后遍历所有子元素
        decorations: list[dict] = []
        for elem in root.iter():
            tag = elem.tag.rsplit("}", 1)[-1] if "}" in elem.tag else elem.tag
            if tag not in ("shape", "line"):
                continue

            shape_type = elem.get("type", "unknown")
            # 只收装饰形状类型（跳过 text / TEXT_BOX 等含正文的）
            if shape_type not in DECOR_TYPES and tag != "line":
                continue

            # 跳过含正文文本的 shape（不是纯装饰）
            has_text = False
            for t in elem.iter():
                t_local = t.tag.rsplit("}", 1)[-1] if "}" in t.tag else t.tag
                if t_local in ("t",) and t.text and t.text.strip():
                    has_text = True
                    break
            if has_text:
                continue

            shape_id = elem.get("id", "")

            # 收 bbox
            if tag == "line":
                try:
                    sx = float(elem.get("startX", "0"))
                    sy = float(elem.get("startY", "0"))
                    ex = float(elem.get("endX", "0"))
                    ey = float(elem.get("endY", "0"))
                    bbox = {
                        "x": round(min(sx, ex), 2),
                        "y": round(min(sy, ey), 2),
                        "w": round(abs(ex - sx), 2),
                        "h": round(abs(ey - sy), 2),
                    }
                except (ValueError, TypeError):
                    bbox = {"x": 0, "y": 0, "w": 0, "h": 0}
            else:
                try:
                    bbox = {
                        "x": round(float(elem.get("topLeftX", "0")), 2),
                        "y": round(float(elem.get("topLeftY", "0")), 2),
                        "w": round(float(elem.get("width", "0")), 2),
                        "h": round(float(elem.get("height", "0")), 2),
                    }
                except (ValueError, TypeError):
                    bbox = {"x": 0, "y": 0, "w": 0, "h": 0}

            # 找 fillColor（可能在 fill/fillColor 子节点）
            fill = ""
            for child in elem.iter():
                c_local = child.tag.rsplit("}", 1)[-1] if "}" in child.tag else child.tag
                if c_local == "fillColor":
                    fill = child.get("color", "")
                    break

            # signature：type + fill(去空格) + 尺寸取整——用于跨页复用判定
            fill_norm = re.sub(r"\s+", "", fill)
            sig = f"{shape_type}|fill={fill_norm}|w={int(bbox['w'])}|h={int(bbox['h'])}"

            decorations.append({
                "shape_id": shape_id,
                "type": shape_type,
                "bbox": bbox,
                "fill": fill,
                "signature": sig,
            })
            total += 1

        if decorations:
            by_slide[str(slide_num)] = decorations

    return {
        "by_slide": by_slide,
        "total_decorations": total,
        "scanned_slides": scanned,
    }


# 占位符黑名单（与 template_lint_all.py 保持一致；此处 inline 一份避免脚本依赖）
_TAXONOMY_PLACEHOLDER_BLACKLIST = [
    "添加标题", "点击输入", "点击此处", "占位", "占位符",
    "示例文本", "示例文字", "示例内容", "示例",
    "Lorem ipsum", "Lorem", "Click to add", "Add title",
    "Add subtitle", "Add text", "Placeholder", "Sample text",
    "asdas", "想搞设计", "论文就是用来",
    "亮亮图文", "淘宝",
    "副标题",
]


def _extract_taxonomy_candidates(slides_manifest: list[dict],
                                  source_slides_dir: Path,
                                  decorations: dict,
                                  canvas_w: float, canvas_h: float) -> dict:
    """启发式识别模板 5 类资产的**初步候选**。MainAgent Step 2 在此基础上补充判断。

    5 类：
    1. brand_assets：多页复用的 shape/img（logo、水印、页脚）——判定：
       - 同一 file_token 或同一 signature（type+fill+尺寸）在 >= 3 页出现
    2. visual_language：主色 fill 频次 top 3、字体族频次 top 2、装饰形状类型频次
    3. layout_skeleton：每种 role 的骨架 shape 结构 hints（title_bar / content_area bbox）
    4. placeholder_images：> 20% 画布面积的 <img> 且非多页复用（可能是内容示意图）
    5. sample_texts：命中 PLACEHOLDER_BLACKLIST + 长度 >= 4 的文本

    返回结构：见 taxonomy-candidates.json schema。
    """
    # SXSD 坐标空间不同于 pptx 的 inch——从 full.xml 读 SXSD 画布 (pt)
    # img/shape bbox 都在 SXSD 空间，area_ratio 必须用 SXSD 画布
    sxsd_w = sxsd_h = 0.0
    full_xml = source_slides_dir / "full.xml"
    if full_xml.exists():
        try:
            head = full_xml.read_text(encoding="utf-8", errors="ignore")[:2000]
            mw = re.search(r'<presentation[^>]*\bwidth="([\d.]+)"', head)
            mh = re.search(r'<presentation[^>]*\bheight="([\d.]+)"', head)
            if mw:
                sxsd_w = float(mw.group(1))
            if mh:
                sxsd_h = float(mh.group(1))
        except Exception:
            pass
    if not sxsd_w or not sxsd_h:
        # fallback：常见 SXSD 画布是 960x540（16:9 pt）
        sxsd_w, sxsd_h = 960.0, 540.0
    sxsd_area = max(sxsd_w * sxsd_h, 1e-6)

    # === 1. brand_assets：多页复用 ===
    # 1a. 图片：从 source-slides 扫 <img src> 统计出现页
    img_usage: dict[str, dict] = {}  # file_token -> {pages, bboxes}
    if source_slides_dir.exists():
        for xml_path in sorted(source_slides_dir.glob("slide-*.xml")):
            m = re.search(r"slide-(\d+)", xml_path.name)
            if not m:
                continue
            slide_num = int(m.group(1))
            try:
                content = xml_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for im in re.finditer(
                r'<img[^>]*\bid="([^"]*)"[^>]*\bsrc="([^"]+)"[^>]*\bwidth="([^"]+)"[^>]*\bheight="([^"]+)"[^>]*\btopLeftX="([^"]+)"[^>]*\btopLeftY="([^"]+)"',
                content,
            ):
                _iid, src, w, h, tlx, tly = im.groups()
                if src.startswith("@") or src.startswith("http"):
                    continue
                try:
                    bbox = {
                        "x": round(float(tlx), 2),
                        "y": round(float(tly), 2),
                        "w": round(float(w), 2),
                        "h": round(float(h), 2),
                    }
                except (ValueError, TypeError):
                    bbox = {"x": 0, "y": 0, "w": 0, "h": 0}
                if src not in img_usage:
                    img_usage[src] = {"pages": [], "bbox_sample": bbox}
                if slide_num not in img_usage[src]["pages"]:
                    img_usage[src]["pages"].append(slide_num)

    # 1b. 装饰 shape：按 signature 聚合，找 >= 3 页复用的
    sig_pages: dict[str, list[int]] = {}
    sig_meta: dict[str, dict] = {}
    for slide_num_str, decs in decorations.get("by_slide", {}).items():
        try:
            slide_num = int(slide_num_str)
        except ValueError:
            continue
        for d in decs:
            sig = d["signature"]
            if sig not in sig_pages:
                sig_pages[sig] = []
                sig_meta[sig] = {"type": d["type"], "bbox_sample": d["bbox"], "fill": d["fill"]}
            if slide_num not in sig_pages[sig]:
                sig_pages[sig].append(slide_num)

    brand_assets: list[dict] = []
    for src, info in img_usage.items():
        pages = info["pages"]
        bbox = info["bbox_sample"]
        area_ratio = (bbox["w"] * bbox["h"]) / sxsd_area if sxsd_area else 0
        if len(pages) >= 3 or (len(pages) >= 2 and area_ratio < 0.05):
            brand_assets.append({
                "type": "img",
                "file_token": src,
                "used_in_pages": sorted(pages),
                "bbox": bbox,
                "area_ratio": round(area_ratio, 3),
                "confidence": "high" if len(pages) >= 3 else "medium",
                "note": "多页复用图 → Logo/水印/页脚候选" if len(pages) >= 3 else "2 页复用的小图 → 可能是 Logo",
            })
    for sig, pages in sig_pages.items():
        if len(pages) < 3:
            continue
        meta = sig_meta[sig]
        brand_assets.append({
            "type": "shape",
            "shape_signature": sig,
            "shape_type": meta["type"],
            "fill": meta["fill"],
            "bbox_sample": meta["bbox_sample"],
            "used_in_pages": sorted(pages),
            "confidence": "high" if len(pages) >= 5 else "medium",
            "note": f"{len(pages)} 页出现同 signature → 品牌骨架 shape 候选（页眉/页脚条/角标）",
        })

    # === 2. visual_language：主色 + 字体 + 装饰形状分布 ===
    color_counter: Counter = Counter()
    font_counter: Counter = Counter()
    shape_type_counter: Counter = Counter()

    if source_slides_dir.exists():
        for xml_path in sorted(source_slides_dir.glob("slide-*.xml")):
            try:
                content = xml_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            # fillColor
            for m in re.finditer(r'fillColor[^>]*\bcolor="([^"]+)"', content):
                color_counter[m.group(1)] += 1
            # 单色 color 属性（content 里的文字色）
            for m in re.finditer(r'<content[^>]*\bcolor="([^"]+)"', content):
                color_counter[m.group(1)] += 1
            # fontFamily
            for m in re.finditer(r'fontFamily="([^"]+)"', content):
                font_counter[m.group(1)] += 1
            # 装饰形状类型（含 line）
            for m in re.finditer(r'<shape[^>]*\btype="([^"]+)"', content):
                shape_type_counter[m.group(1)] += 1
            shape_type_counter["line"] += len(re.findall(r"<line\b", content))

    # 从 decorations 补一份形状类型统计（更精准，因为过滤了文本 shape）
    decor_type_counter: Counter = Counter()
    for _slide, decs in decorations.get("by_slide", {}).items():
        for d in decs:
            decor_type_counter[d["type"]] += 1

    visual_language = {
        "primary_colors": [c for c, _ in color_counter.most_common(6)],
        "primary_colors_with_count": [
            {"color": c, "count": n} for c, n in color_counter.most_common(6)
        ],
        "fonts": [{"name": f, "count": n} for f, n in font_counter.most_common(4)],
        "shape_type_distribution": [
            {"type": t, "count": n} for t, n in shape_type_counter.most_common(10)
        ],
        "decorative_shape_types": [
            {"type": t, "count": n} for t, n in decor_type_counter.most_common(10)
        ],
    }

    # === 3. layout_skeleton：按 role 汇总每类页面的骨架 hints ===
    role_to_slides: dict[str, list[int]] = {}
    for meta in slides_manifest:
        role = meta.get("role", "content")
        role_to_slides.setdefault(role, []).append(meta["slide_num"])

    layout_skeleton_by_role: dict[str, dict] = {}
    for role, nums in role_to_slides.items():
        # 采样第一页做代表——真实使用时 MainAgent 会 Read 具体 XML
        sample_num = nums[0] if nums else None
        sample_meta = next((m for m in slides_manifest if m["slide_num"] == sample_num), None)
        if not sample_meta:
            continue
        # 从 shell_shapes 里挑靠近边缘的（页眉页脚候选）
        shell = sample_meta.get("shell_shapes", [])
        content_shapes = sample_meta.get("content_shapes", [])
        # 找宽度接近画布宽度的横条（title bar / footer bar 候选）
        wide_bars = []
        for s in shell + content_shapes:
            w, h = s.get("width", 0), s.get("height", 0)
            top = s.get("top", 0)
            if w >= canvas_w * 0.6 and 0 < h < canvas_h * 0.2:
                wide_bars.append({
                    "id": s.get("id"),
                    "type": s.get("type"),
                    "bbox": {"x": s.get("left"), "y": top, "w": w, "h": h},
                    "position_hint": "top" if top < canvas_h * 0.3 else (
                        "bottom" if top > canvas_h * 0.7 else "middle"
                    ),
                })
        layout_skeleton_by_role[role] = {
            "sample_slide_num": sample_num,
            "slides": sorted(nums),
            "shell_shape_count": len(shell),
            "content_shape_count": len(content_shapes),
            "wide_bars_hint": wide_bars[:5],
            "note": f"role={role} 共 {len(nums)} 页；MainAgent 需 Read source-slides/slide-{sample_num:02d}.xml 印证骨架",
        }

    # === 4. placeholder_images：> 20% 面积 + 单页使用 ===
    placeholder_images_candidates: list[dict] = []
    for src, info in img_usage.items():
        pages = info["pages"]
        bbox = info["bbox_sample"]
        area_ratio = (bbox["w"] * bbox["h"]) / sxsd_area if sxsd_area else 0
        if area_ratio > 0.20 and len(pages) == 1:
            placeholder_images_candidates.append({
                "slide_num": pages[0],
                "file_token": src,
                "bbox": bbox,
                "area_ratio": round(area_ratio, 3),
                "note": "single-page use + 面积 > 20%，很可能是内容示意图（切题就换、不切题删）",
            })

    # === 5. sample_texts：命中黑名单 + 长度 >= 4 ===
    sample_texts_hits: list[dict] = []
    seen_hits: set[tuple] = set()
    for meta in slides_manifest:
        slide_num = meta["slide_num"]
        for shp in meta.get("content_shapes", []) + meta.get("shell_shapes", []):
            text = (shp.get("text") or "").strip()
            if len(text) < 4:
                continue
            for kw in _TAXONOMY_PLACEHOLDER_BLACKLIST:
                if kw in text:
                    key = (slide_num, text[:80])
                    if key in seen_hits:
                        break
                    seen_hits.add(key)
                    sample_texts_hits.append({
                        "slide_num": slide_num,
                        "text": text[:120],
                        "matched_placeholder": kw,
                    })
                    break

    return {
        "brand_assets": brand_assets,
        "visual_language": visual_language,
        "layout_skeleton": {"by_role": layout_skeleton_by_role},
        "placeholder_images_candidates": placeholder_images_candidates,
        "sample_texts_hits": sample_texts_hits,
        "meta": {
            "note": "启发式初步候选。MainAgent Step 2 需要 Read source-slides + thumbs/overview.jpg 补充与订正，最终产物落到 manifest/template-taxonomy.md。",
            "canvas_inch": {"w": canvas_w, "h": canvas_h},
            "canvas_sxsd_pt": {"w": sxsd_w, "h": sxsd_h},
            "scanned_slides": len(slides_manifest),
        },
    }


def _extract_file_tokens_from_source_slides(source_slides_dir: Path) -> list[dict]:
    """扫 source-slides/*.xml 抽出所有 <img src="box_xxx"> 里的 file_token，去重后返回。

    产物按出现顺序返回 [{"file_token": "box_xxx", "used_in_slide_num": [1, 3]}, ...]
    MainAgent 需要复用图片时直接从这里拿 file_token，不需要 +media-upload。
    """
    tokens: dict[str, list[int]] = {}
    for xml_path in sorted(source_slides_dir.glob("slide-*.xml")):
        try:
            slide_num = int(re.search(r"slide-(\d+)", xml_path.name).group(1))
        except (AttributeError, ValueError):
            continue
        content = xml_path.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r'<img[^>]*\bsrc="([^"]+)"', content):
            src = m.group(1)
            # 只收 file_token（box_ / boxcn 开头之类），跳过占位符 @path 或 http 外链
            if src.startswith("@") or src.startswith("http"):
                continue
            tokens.setdefault(src, [])
            if slide_num not in tokens[src]:
                tokens[src].append(slide_num)

    return [
        {"file_token": tok, "used_in_slide_num": pages, "source": "template"}
        for tok, pages in tokens.items()
    ]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pptx", required=True, help="Path to input .pptx")
    ap.add_argument("--work-dir", required=True, help="Output work dir (usually $WORK_DIR)")
    ap.add_argument("--offline-only", action="store_true",
                    help="Skip drive +import and slides +xml-get; only produce manifest/assets/overview")
    ap.add_argument("--deck-title", default=None,
                    help="Title of the imported deck on Lark (透传到 drive +import --name). "
                         "省略时走本地 pptx 文件名默认。建议 MainAgent 用用户主题命名，避免 deck 全叫 'template'。")
    ap.add_argument("--lark-timeout", type=int,
                    default=int(os.environ.get("PARSE_TEMPLATE_LARK_TIMEOUT", "300")),
                    help="lark-cli 每次调用的单次超时(秒)。默认 300s;可用 env PARSE_TEMPLATE_LARK_TIMEOUT 覆盖。"
                         "大 deck(>100 页)服务端序列化慢建议调到 600s。")
    ap.add_argument("--lark-max-attempts", type=int,
                    default=int(os.environ.get("PARSE_TEMPLATE_LARK_MAX_ATTEMPTS", "5")),
                    help="lark-cli 可重试错误的最大尝试次数。默认 5;可用 env PARSE_TEMPLATE_LARK_MAX_ATTEMPTS 覆盖。")
    args = ap.parse_args()

    pptx_path = Path(args.pptx).resolve()
    work = Path(args.work_dir).resolve()
    if not pptx_path.exists():
        print(json.dumps({"ok": False, "error": f"pptx not found: {pptx_path}"}))
        return 2
    if not pptx_path.suffix.lower() == ".pptx":
        print(json.dumps({"ok": False, "error": f"expected .pptx, got {pptx_path.suffix}"}))
        return 2

    manifest_dir = work / "manifest"
    assets_dir = work / "assets"
    thumbs_dir = work / "thumbs"
    manifest_dir.mkdir(parents=True, exist_ok=True)

    # === 依赖探测 ===
    # 先跑一次探测 → 若有缺失则调用 _ensure_pip_deps() 尝试补装（不指定 index-url · 依赖客户端内置 pip 源）
    # 每个包单独 timeout · 失败/超时静默,已有 fallback 会兜住
    capabilities, install_hints = _detect_capabilities()
    missing_pip = [name for name, ok in [
        ("python-pptx", capabilities["python_pptx"]),
        ("pypdfium2",   capabilities["pypdfium2"]),
        ("Pillow",      capabilities["pil"]),
        ("lxml",        capabilities["lxml"]),
    ] if not ok]

    auto_install_report: list[dict] = []
    if missing_pip:
        auto_install_report = _ensure_pip_deps(missing_pip, per_pkg_timeout=60)
        # 补装完重探,更新 capabilities（也过滤掉已解决的 install_hints）
        capabilities, install_hints = _detect_capabilities()

    if not capabilities["soffice"]:
        install_hints.append("soffice/libreoffice 缺失（macOS: `brew install libreoffice`；Ubuntu: `apt install libreoffice`；Win: 官网下载后加入 PATH）——本地联图无法生成；若 lark-cli + Pillow 可用会走 screenshot 云端联图兜底，仅 lark-cli 可用则走 drive +export pdf 兜底")

    # === 解析 pptx（主路径 python-pptx，fallback 标准库）===
    all_texts_flat: list[str] = []
    slides_manifest = []

    if capabilities["python_pptx"]:
        from pptx import Presentation  # type: ignore
        prs = Presentation(str(pptx_path))
        canvas_w = _emu_to_inch(prs.slide_width)
        canvas_h = _emu_to_inch(prs.slide_height)
        total = len(prs.slides)

        for i, slide in enumerate(prs.slides, start=1):
            texts_this_page = []
            for shp in slide.shapes:
                try:
                    t = _shape_text(shp)
                    if t:
                        texts_this_page.append(t)
                        all_texts_flat.append(t)
                except Exception:
                    pass
            role = _classify_role(i, total, texts_this_page)
            shell, content = _extract_shell_shapes(slide, i, set(), canvas_w, canvas_h)
            regions = _extract_available_regions(shell, content, canvas_w, canvas_h)
            slides_manifest.append({
                "slide_num": i,
                "role": role,
                "shell_shapes": shell,
                "content_shapes": content,
                "available_regions": regions,
                "images_used": [],  # 下面填
                "slide_id": None,
                "local_xml_path": None,
            })
    else:
        # 降级路径：标准库 zipfile + xml.etree
        canvas_w_emu, canvas_h_emu, slides_shapes = _parse_pptx_fallback(pptx_path)
        canvas_w = _emu_to_inch(canvas_w_emu)
        canvas_h = _emu_to_inch(canvas_h_emu)
        total = len(slides_shapes)

        for i, shapes in enumerate(slides_shapes, start=1):
            texts_this_page = [s._text for s in shapes if s._text]
            all_texts_flat.extend(texts_this_page)
            role = _classify_role(i, total, texts_this_page)
            # 简易 shell/content 分类：走同样的 _extract_shell_shapes 逻辑，只是输入变成 _FallbackShape
            # _extract_shell_shapes 内部访问 shp.shape_type / left/top/width/height，接口兼容
            # 但 _shape_text 走 python-pptx API，需要传 _text 属性给它——已在 _FallbackShape 里
            shell, content = _extract_shell_shapes_fallback(shapes, i, canvas_w, canvas_h)
            regions = _extract_available_regions(shell, content, canvas_w, canvas_h)
            slides_manifest.append({
                "slide_num": i,
                "role": role,
                "shell_shapes": shell,
                "content_shapes": content,
                "available_regions": regions,
                "images_used": [],
                "slide_id": None,
                "local_xml_path": None,
            })

    # 抽图片到 assets/（纯 zipfile，任何环境都能跑）
    assets_manifest = _extract_images(pptx_path, assets_dir)

    # 渲染联图 overview（thumbs/overview.jpg 或 thumbs/overview.pdf 兜底）
    # 首次尝试用本地 soffice；若缺 soffice，deck 导入完成后会二次重试走飞书云端导出 pdf 兜底
    overview_ok, overview_reason = _render_overview(pptx_path, thumbs_dir)

    # 解压临时目录读 slide{N}.xml.rels 拿 images_used
    tmp_unpack = manifest_dir / "_pptx_raw"
    tmp_unpack.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(pptx_path) as z:
        z.extractall(tmp_unpack)
    for i, meta in enumerate(slides_manifest, start=1):
        rels_path = tmp_unpack / "ppt" / "slides" / "_rels" / f"slide{i}.xml.rels"
        meta["images_used"] = _extract_images_used(rels_path)

    placeholders = _detect_placeholders(all_texts_flat)
    theme = _extract_theme(pptx_path)

    # 每页 preview_text（前 100 字文本），用于 template-index.json 的候选页挑选
    for meta in slides_manifest:
        text_parts = [c.get("text", "") for c in meta.get("content_shapes", []) if c.get("text")]
        # 200 字预览：让 MainAgent 通过 template-index.json 轻量看清每页大致内容
        meta["preview_text"] = " / ".join(text_parts)[:200]

    # === 联网部分：导入 deck + 拉 SXSD + 清空到 1 页 + 抽 file_token ===
    # 导入的 deck 直接当交付目标：MainAgent 用 +update-slide 覆盖第 1 页、+add-slide 追加后续页
    # 优点：省一次 +create；模板自带图的 file_token 可以直接复用不用重传
    lark_info: dict[str, Any] = {"template_imported": False, "deck": None}
    template_id_internal: str | None = None
    file_tokens: list[dict] = []  # 模板自带图 file_token 清单，offline 模式下为空列表
    if not args.offline_only:
        # (1) 导入模板到飞书（只读参考，用于拉 SXSD；id 只脚本内部用）
        imp = _import_pptx_to_lark(pptx_path, work, deck_title=args.deck_title,
                                    timeout=args.lark_timeout,
                                    max_attempts=args.lark_max_attempts)
        if not imp["ok"]:
            print(json.dumps({
                "ok": False,
                "phase": "drive_import",
                "error": imp["error"],
                "hint": "导入失败可加 --offline-only 只跑离线部分先看 manifest；确认 lark-cli 已装且能访问飞书后再重跑。",
                "capabilities": capabilities,
                "install_hints": install_hints,
            }, ensure_ascii=False, indent=2))
            shutil.rmtree(tmp_unpack, ignore_errors=True)
            return 4

        template_id_internal = imp["xml_presentation_id"]
        lark_info["template_imported"] = True

        # (1.5) 若首次 render_overview 因缺 soffice 失败，此时 deck 已就绪，走云端兜底：
        #   优先级: lark screenshot 分批并发 + PIL 拼图  →  lark drive +export pdf
        #   screenshot 路径视觉最准（和线上一致）；PDF 路径不依赖 PIL 也能出兜底文件
        if not overview_ok and overview_reason.startswith("soffice_missing"):
            ss_ok, ss_reason = _render_overview_via_screenshot(
                template_id_internal, total, thumbs_dir, cwd=work
            )
            if ss_ok:
                overview_ok, overview_reason = True, ss_reason
            else:
                # screenshot 兜底失败，落到 pdf 兜底（走 _render_overview + deck_id）
                overview_ok, overview_reason = _render_overview(
                    pptx_path, thumbs_dir, deck_id=template_id_internal
                )
                if not overview_ok:
                    # 把 screenshot 的失败原因也记进去，便于排障
                    overview_reason = f"{overview_reason} ; screenshot_fallback: {ss_reason}"

        # (2) 拉全稿 SXSD 拆成每页
        split = _fetch_and_split_slides(template_id_internal, work,
                                         timeout=args.lark_timeout,
                                         max_attempts=args.lark_max_attempts,
                                         total_slides_hint=total)
        if not split["ok"]:
            print(json.dumps({
                "ok": False,
                "phase": "xml_get_split",
                "error": split["error"],
                # 仅在失败排障场景暴露 template id，方便人手动补拆
                "template_id_for_manual_recovery": template_id_internal,
                "hint": f"导入成功但拉 SXSD 失败，可手动跑：lark-cli slides +xml-get --presentation {template_id_internal} --output source-slides/full.xml",
                "capabilities": capabilities,
                "install_hints": install_hints,
            }, ensure_ascii=False, indent=2))
            shutil.rmtree(tmp_unpack, ignore_errors=True)
            return 5

        for split_slide in split["slides"]:
            idx = split_slide["slide_num"] - 1
            if 0 <= idx < len(slides_manifest):
                slides_manifest[idx]["slide_id"] = split_slide["slide_id"]
                slides_manifest[idx]["local_xml_path"] = split_slide["local_xml_path"]

        # (3) 清空导入 deck 到 1 页 —— 单线程串行删 + 保留第 1 页(revert 会连 master/theme 一起删,导致后续 +add-slide 报 block is empty)
        # MainAgent 后续用 +update-slide 覆盖第 1 页 · +add-slide 追加后续页
        deck_url = imp.get("url") or ""
        all_slide_ids = [s["slide_id"] for s in split["slides"] if s.get("slide_id")]

        # 补拉:分页 fetch 有部分页失败(没有 slide_id) → 那些页不会被 delete · 会成为残留
        # 单独串行重试一次 · 只求拿到 slide_id(不 care XML 内容 · 拿到 id 就 delete 掉)
        failed_page_nums = split.get("per_page_failed_pages") or []
        source_dir = work / "source-slides"
        extra_ids_recovered = 0
        for page_num in failed_page_nums:
            _n, meta = _fetch_single_slide_xml(
                template_id_internal, int(page_num),
                work, source_dir, timeout=60, max_attempts=5,
            )
            if meta and meta.get("slide_id"):
                sid = meta["slide_id"]
                if sid not in all_slide_ids:
                    all_slide_ids.append(sid)
                    extra_ids_recovered += 1
                # 顺便补回 slides_manifest 里
                idx = int(page_num) - 1
                if 0 <= idx < len(slides_manifest):
                    slides_manifest[idx]["slide_id"] = sid
                    slides_manifest[idx]["local_xml_path"] = meta["local_xml_path"]

        # 若所有 fetch 都失败拿不到 slide_id · 直接 hard fail 避免后续 KeyError
        if not all_slide_ids:
            print(json.dumps({
                "ok": False,
                "phase": "purge_to_one_page",
                "error": "no slide_id recovered from fetch · cannot purge",
                "template_id_for_manual_recovery": template_id_internal,
                "hint": "分页 fetch 全失败;手动跑 lark-cli slides +xml-get 拉一下 deck 看看状态",
                "capabilities": capabilities,
                "install_hints": install_hints,
            }, ensure_ascii=False, indent=2))
            shutil.rmtree(tmp_unpack, ignore_errors=True)
            return 6

        purge = _purge_deck_to_one_page(template_id_internal, all_slide_ids, work)
        # 新版 purge 一趟扫 · 总是 ok=true(除非空 slide_ids)· 部分失败通过 failed_slide_ids 报告
        purge_deleted = purge.get("deleted_count", 0)
        purge_failed_sids = purge.get("failed_slide_ids", [])
        purge_partial_warning = None
        if purge_failed_sids:
            purge_partial_warning = (
                f"{purge_deleted}/{len(all_slide_ids) - 1} deleted, {len(purge_failed_sids)} remain. "
                f"MainAgent 需调 purge_deck.py --deck {template_id_internal} --slide-ids <见 purge_failed_slide_ids>"
            )

        # (4) 抽 file_token —— 塞进 template-index.json 顶层 assets_with_tokens
        # MainAgent 复用模板图必须**用同一个 deck**(deck-scope 绑定 · 跨 deck 会 relation mismatch)
        file_tokens = _extract_file_tokens_from_source_slides(work / "source-slides")
        assets_index_path = work / "assets_index.json"
        assets_index_path.write_text(
            json.dumps(file_tokens, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        lark_info["deck"] = {
            "xml_presentation_id": template_id_internal,
            "url": deck_url,
            "first_page_slide_id": purge["first_page_slide_id"],
            "first_page_state": "blank" if purge.get("cleared_first_page") else "template_remnant",
        }
        if purge.get("clear_error"):
            lark_info["deck"]["clear_first_page_warning"] = purge["clear_error"]
        if purge_partial_warning:
            lark_info["deck"]["purge_partial_warning"] = purge_partial_warning
            lark_info["deck"]["purge_failed_slide_ids"] = purge.get("failed_slide_ids", [])
        lark_info["template_imported"] = True

    # 判定 capability_level
    if capabilities["python_pptx"] and capabilities["pypdfium2"] and capabilities["pil"] and capabilities["soffice"]:
        capability_level = "full"
    elif not capabilities["python_pptx"] and not overview_ok:
        capability_level = "minimal"
    else:
        capability_level = "degraded"

    # === 装饰形状 + taxonomy 候选（offline 模式下 by_slide 会为空，只跑得出 sample_texts + visual_language fallback）===
    source_slides_dir = work / "source-slides"
    decorations = _extract_decorations(source_slides_dir)
    decorations_path = manifest_dir / "decorations.json"
    decorations_path.write_text(
        json.dumps(decorations, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # === 内容页骨架自动提取（防"cp source 生搬硬套"） ===
    # 对每个 content 页产 manifest/content-skeletons/slide-NN.content-skeleton.xml，
    # 只含跨页复用的 brand_assets（背景/页眉/页脚/装饰线），中部留空。
    # Step 5.2 的 active_rebuild 页应 cp 这个骨架而非 cp source-slides/slide-NN.xml。
    content_skeletons_dir = manifest_dir / "content-skeletons"
    content_skeleton_paths: dict[int, str] = {}
    if source_slides_dir.exists() and list(source_slides_dir.glob("slide-*.xml")):
        try:
            content_skeleton_paths = _extract_content_skeletons(
                source_slides_dir, content_skeletons_dir, total,
            )
        except Exception as e:
            # 骨架提取失败不阻塞主流程
            print(f"WARN: extract_content_skeletons failed: {e}", file=sys.stderr)

    taxonomy_candidates = _extract_taxonomy_candidates(
        slides_manifest=slides_manifest,
        source_slides_dir=source_slides_dir,
        decorations=decorations,
        canvas_w=canvas_w,
        canvas_h=canvas_h,
    )
    taxonomy_path = manifest_dir / "taxonomy-candidates.json"
    taxonomy_path.write_text(
        json.dumps(taxonomy_candidates, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # === 拆分 manifest：template-index.json（轻量）+ slides/slide-NN.json（单页详情）===
    slides_dir = manifest_dir / "slides"
    slides_dir.mkdir(parents=True, exist_ok=True)

    # template-index.json：MainAgent Step 2 唯一需要 Read 的轻量索引
    index_slides = []
    for meta in slides_manifest:
        n = meta["slide_num"]
        index_slides.append({
            "slide_num": n,
            "role": meta["role"],
            "slide_id": meta.get("slide_id"),
            "local_xml_path": meta.get("local_xml_path"),
            # preview_text 从 100 字扩到 200 字，让 MainAgent 轻量看每页大致文字
            "preview_text": (meta.get("preview_text") or "")[:200],
            "images_used": meta.get("images_used", []),
            "shape_count": {
                "shell": len(meta.get("shell_shapes", [])),
                "content": len(meta.get("content_shapes", [])),
            },
            # 内容页骨架（brand_assets only）· active_rebuild 页 Step 5.2 应 cp 这个而非 source
            # 非 content 页（cover/toc/ending）该字段为 null
            "content_skeleton_path": content_skeleton_paths.get(n),
        })

    # visual_language：主色 palette + 字体族（合并 theme.xml 声明 + SXSD 实际统计）
    # MainAgent Step 2 扫模板时直接从 template-index.json 顶层拿这些，写 XML 时字体族/主色照搬
    tc_vl = taxonomy_candidates.get("visual_language", {}) if isinstance(taxonomy_candidates, dict) else {}
    visual_language = {
        # 主色 palette top 6（从 SXSD 里 fillColor / content color 出现次数排出来的）
        "primary_colors": tc_vl.get("primary_colors", []),
        # 字体族（合并两个来源）：
        # - theme.xml 声明的 majorFont/minorFont（可能未在正文实际使用）
        # - SXSD 里 fontFamily 属性实际出现的频次 top 4（最真实的信号）
        "fonts_declared": {
            "major_latin": theme.get("major_font"),
            "minor_latin": theme.get("minor_font"),
            "major_ea": theme.get("major_font_ea"),
            "minor_ea": theme.get("minor_font_ea"),
        },
        "fonts_used": tc_vl.get("fonts", []),  # [{"name": "...", "count": N}, ...]
    }

    # overview 产物路径:成功时收集所有 thumbs/overview*.jpg(单张)或 thumbs/overview-N.jpg(多张分片)
    # 兜底 PDF 场景下就是 thumbs/overview.pdf
    overview_paths: list[str] = []
    if overview_ok:
        if overview_reason in ("pypdfium2_missing_pdf_used", "pil_missing_pdf_used"):
            if (thumbs_dir / "overview.pdf").exists():
                overview_paths = ["thumbs/overview.pdf"]
        else:
            # 按数字排序 · 避免字典序把 overview-10 排在 overview-2 前面
            def _shard_num(p):
                m = re.search(r"overview-?(\d+)?", p.stem)
                return int(m.group(1)) if m and m.group(1) else 0
            jpg_shards = sorted(thumbs_dir.glob("overview*.jpg"), key=_shard_num)
            overview_paths = [f"thumbs/{p.name}" for p in jpg_shards]

    template_index = {
        "ok": True,
        "pptx": str(pptx_path.relative_to(work) if pptx_path.is_relative_to(work) else pptx_path),
        "canvas": {"width_inch": canvas_w, "height_inch": canvas_h},
        "total_slides": total,
        "capability_level": capability_level,
        "capabilities": capabilities,
        "overview": {
            "ok": overview_ok,
            "reason": overview_reason,
            # 兼容旧字段:单张时 path 是字符串;多张分片时是数组第一项(向后兼容)
            "path": overview_paths[0] if overview_paths else None,
            # 新字段:所有分片路径(MainAgent 大 deck 时按顺序 Read)
            "paths": overview_paths,
            "sharded": len(overview_paths) > 1,
            "shard_count": len(overview_paths),
        },
        "lark": lark_info,
        # 品牌视觉语言：主色 palette + 字体族。MainAgent 写内容页时字体和主色照这里搬（规则 5.2.1）
        "visual_language": visual_language,
        # 模板 pptx 内嵌的原始图片本地文件清单（供脚本/调试用，MainAgent 通过 file_token 引用图片不需要读本地文件）
        "assets_local_files": assets_manifest,
        # 模板自带图的 file_token 清单（合并自原 assets_index.json）——
        # MainAgent 复用模板图时直接引用这里列的 file_token，不需要 +media-upload
        "assets_with_tokens": file_tokens,
        "sample_placeholders": placeholders,
        "slides": index_slides,
    }
    (manifest_dir / "template-index.json").write_text(
        json.dumps(template_index, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 每页详情单独存
    for meta in slides_manifest:
        detail = {
            "slide_num": meta["slide_num"],
            "role": meta["role"],
            "slide_id": meta.get("slide_id"),
            "local_xml_path": meta.get("local_xml_path"),
            "shell_shapes": meta.get("shell_shapes", []),
            "content_shapes": meta.get("content_shapes", []),
            "available_regions": meta.get("available_regions", []),
            "images_used": meta.get("images_used", []),
        }
        (slides_dir / f"slide-{meta['slide_num']:02d}.json").write_text(
            json.dumps(detail, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    (manifest_dir / "theme.json").write_text(
        json.dumps(theme, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 清理临时解压目录 + 中间 pdf
    shutil.rmtree(tmp_unpack, ignore_errors=True)
    tmp_pdf_dir = thumbs_dir.parent / "_tmp_pdf"
    if tmp_pdf_dir.exists():
        shutil.rmtree(tmp_pdf_dir, ignore_errors=True)

    output = {
        "ok": True,
        "template_index_path": "manifest/template-index.json",
        "slides_detail_dir": "manifest/slides/",
        "theme_path": "manifest/theme.json",
        "decorations_path": "manifest/decorations.json",
        "taxonomy_candidates_path": "manifest/taxonomy-candidates.json",
        "total_slides": total,
        "canvas": {"width_inch": canvas_w, "height_inch": canvas_h},
        "assets_count": len(assets_manifest),
        "decorations_count": decorations.get("total_decorations", 0),
        "taxonomy_summary": {
            "brand_assets_count": len(taxonomy_candidates.get("brand_assets", [])),
            "placeholder_images_candidates_count": len(taxonomy_candidates.get("placeholder_images_candidates", [])),
            "sample_texts_hits_count": len(taxonomy_candidates.get("sample_texts_hits", [])),
            "primary_colors_top3": taxonomy_candidates.get("visual_language", {}).get("primary_colors", [])[:3],
        },
        "capability_level": capability_level,
        "capabilities": capabilities,
        "overview": template_index["overview"],
        "sample_placeholders_count": len(placeholders),
        "lark": lark_info,
    }
    if install_hints:
        output["install_hints"] = install_hints
    if auto_install_report:
        output["auto_install_report"] = auto_install_report
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


def _extract_shell_shapes_fallback(shapes: list, slide_num: int,
                                    canvas_w: float, canvas_h: float) -> tuple[list[dict], list[dict]]:
    """降级 shape 分类。输入是 _FallbackShape 列表;输出与 _extract_shell_shapes 兼容。"""
    canvas_area = max(canvas_w * canvas_h, 1e-6)
    edge_top_thresh = canvas_h * 0.053
    edge_bottom_thresh = canvas_h * 0.947
    edge_left_thresh = canvas_w * 0.0375
    edge_right_thresh = canvas_w * 0.96
    small_logo_area = canvas_area * 0.01
    small_shape_area = canvas_area * 0.03

    shell, content = [], []
    for shp in shapes:
        left = _emu_to_inch(shp.left)
        top = _emu_to_inch(shp.top)
        width = _emu_to_inch(shp.width)
        height = _emu_to_inch(shp.height)
        text = shp._text

        base = {
            "id": shp.shape_id,
            "type": shp.shape_type,
            "left": left,
            "top": top,
            "width": width,
            "height": height,
            "text": text[:200] if text else "",
        }

        is_shell = False
        if shp.shape_type == "LINE":
            is_shell = True
        elif shp.shape_type == "PICTURE":
            if top < edge_top_thresh or top + height > edge_bottom_thresh:
                is_shell = True
            elif width * height < small_logo_area and (left < edge_left_thresh or left + width > edge_right_thresh):
                is_shell = True
        elif shp.shape_type == "AUTO_SHAPE" and not text and width * height < small_shape_area:
            is_shell = True

        if is_shell:
            shell.append(base)
        else:
            content.append(base)

    return shell, content


if __name__ == "__main__":
    sys.exit(main())