#!/usr/bin/env python3
"""
md2html_report.py — 将纯文字 Markdown 报告 + 实时生成的图表合成可视化 HTML

用法：
  python scripts/md2html_report.py <md_file> \
    [--code 300308] [--template <template_path>] [--output <html_path>] \
    [--no-charts]

方案 B 设计（2026-04 更新）：
  - `.md` 源文件是**纯文字**，不含任何 `![](charts/...)` 图片引用
  - 图表在此处**实时生成**（调用 chart_generator.build_charts_inmemory），
    以 inline SVG 形式直接嵌入 HTML，不落地 SVG 文件
  - 通过图表 spec 中的 `anchor` 关键词，自动定位到 Markdown 对应章节末尾插入

输出：
  默认在 .md 同目录生成同名 .html 文件（自包含、离线可看）
"""

import argparse
import os
import re
import sys
from pathlib import Path

# ── 路径推导 ──
_SCRIPT_DIR = Path(__file__).resolve().parent          # scripts/
_SKILL_DIR = _SCRIPT_DIR.parent                        # 插件根目录/
WORKSPACE = Path(os.environ.get("CODEBUDDY_WORKSPACE", _SKILL_DIR.parent.parent))

# Windows UTF-8 兜底
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════
#  Markdown 元信息提取
# ═══════════════════════════════════════════════════════════════════

#: frontmatter 白名单 —— 只有这 4 个 key 会被渲染成 meta-chip；
#: 其他形如 `**X**: Y` 的行（总体判断/测谎结论/收益风险比推导/综合胜率评估/
#: 数据来源/免责声明 等）是正文内容，必须按正文渲染。
_FRONTMATTER_KEYS = {"交易风格", "风险等级", "数据截止时间", "实时价格"}


def inject_footnote_definitions(md_text: str) -> str:
    """从 §6.x 数据信源汇总表自动生成 [^srcN] / [^src_xxx] 脚注定义块，追加到 md 末尾。

    背景（v1.16 修复）：
      报告正文广泛使用 `[^src10]` / `[^src_lc1]` 这类双轨脚注引用，但若 markdown
      源里没有匹配的 `[^id]: 说明` 定义行，python-markdown 的 footnotes 扩展无法
      转换它们，导致 HTML 中残留 `[^src10]` 字面字符串（被读者看到）。

    解决方案：
      1) 定位 `数据信源汇总表` 标题与下一个 `## | --- | 【自用声明】` 之间的表格块；
      2) 解析每一行：`数字编号<!--命名锚--> | 名称 | 类型 | URL | 时效`；
      3) 为每行同时生成数字版 `[^src{N}]: 名称 ([URL](URL)) — 时效` 和命名版
         `[^src_xxx]: 名称 ([URL](URL)) — 时效` 两条定义；
      4) 把所有定义合成一个块，追加到 md 文档末尾（footnotes 扩展会自动搬运到底部）。

    若没有信源表则不做任何处理（保持原样）。
    """
    # v27 加固：标题写成"信源汇总表"（缺"数据"二字）也要能命中锚点，
    # 不能让措辞差异导致整份文档的脚注定义永久失效（历史事故：政策面/消息面/资金面
    # 深稿标题漏"数据"二字，脚标全部裸露成 C3 泄漏）。
    m_anchor = re.search(r"(?:数据)?信源汇总表", md_text)
    if not m_anchor:
        return md_text

    tail = md_text[m_anchor.end():]
    end_m = re.search(r"\n#{1,6}\s|\n---\s*\n|\n【自用声明】", tail)
    block = tail[: end_m.start()] if end_m else tail

    # 已存在的脚注定义（避免重复注入）
    existing_defs = set(
        m.group(1) for m in re.finditer(r"^\[\^(src[\w\-]+)\]:", md_text, re.M)
    )

    # 收集 md 实际用到的所有 src 引用名
    used_refs = set(
        m.group(1) for m in re.finditer(r"\[\^(src[\w\-]+)\]", md_text)
    )

    # 解析表格行
    defs: list[tuple[str, str, str, str]] = []  # (anchor, name, url, freshness)
    for line in block.split("\n"):
        if not line.strip().startswith("|"):
            continue
        if re.match(r"^\|\s*[-:|\s]+\|", line):
            continue
        if "编号" in line and "信源名称" in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 4:
            continue
        col_id = cells[0]
        name = cells[1]
        url_cell = cells[3]
        freshness = cells[4] if len(cells) > 4 else ""
        # 数字编号
        m_num = re.search(r"\b(\d+)\b", col_id)
        # 命名锚（HTML 注释里）
        m_named = re.search(r"<!--\s*(src_[\w\-]+)\s*-->", col_id)
        # URL：取第一个 https?:// 链接
        m_url = re.search(r"https?://[^\s|;`]+", url_cell)
        url = m_url.group(0) if m_url else ""
        if m_num:
            defs.append((f"src{m_num.group(1)}", name, url, freshness))
        if m_named:
            defs.append((m_named.group(1), name, url, freshness))

    if not defs:
        return md_text

    # 仅为"正文中实际出现过的 [^src] 引用"生成脚注定义，并跳过已有定义。
    # v29：原逻辑在 used_refs 为空时会"兜底全量注入"整张信源表——但自
    # rewrite_src_refs_to_source_table() 起，正文能定位到信源表的引用已被改写成
    # 页内锚点直达信源汇总表对应行，正文不再残留 [^src]，used_refs 随之变空。
    # 若仍全量注入，会在文末再列一份与「信源汇总表」内容重复的脚注清单（正是本次要
    # 消除的重复）。故改为：没有正文引用就不注入任何定义；只对少数无法映射到信源表
    # 的"漏网引用"做兜底（此时它才会残留在 used_refs 里）。
    out_lines = ["", ""]  # 与正文留空行
    for anchor, name, url, freshness in defs:
        if anchor in existing_defs:
            continue
        if anchor not in used_refs:
            continue
        # 文本：信源名（含原表中 () 内说明）+ URL 链接 + 时效
        url_part = f" [{url}]({url})" if url else ""
        fresh_part = f" — {freshness}" if freshness else ""
        # 单行脚注定义（footnotes 扩展支持单行）
        out_lines.append(f"[^{anchor}]: {name}{url_part}{fresh_part}")

    if len(out_lines) == 2:
        # 没有新增任何定义
        return md_text

    return md_text.rstrip() + "\n" + "\n".join(out_lines) + "\n"


def rewrite_src_refs_to_source_table(md_text: str, id_prefix: str = "") -> str:
    """v29：消除 HTML 产物层"信源汇总表 + 文末脚注定义清单"的双份内容重复。

    背景：
      正文里的 `[^srcN]` / `[^src_xxx]` 上标引用，经 python-markdown footnotes 扩展
      会跳到"文末脚注定义区"；而这批脚注定义（信源名称+URL+时效）恰恰是 §五
      「信源汇总表」里同一批信源的逐条复述——读者因此看到两份内容高度重叠的信源清单。

    解决方案（信源信息单一数据源化）：
      1) 解析「信源汇总表」，建立 anchor(srcN / src_xxx) → 序号 N 的映射；
      2) 给信源汇总表首列序号单元格注入页内锚点 `<span id="{prefix}srcref-N"></span>`；
      3) 把正文中"能定位到序号 N"的 `[^srcN]` / `[^src_xxx]` 改写成直达该行的上标超链接
         `<sup class="footnote-ref src-ref"><a class="footnote-ref" href="#{prefix}srcref-N">[N]</a></sup>`。
      这样信源的名称/URL/时效只在「信源汇总表」一处呈现，点击正文上标即直达对应行，
      inject_footnote_definitions() 便不再于文末生成那份重复的脚注定义清单。

    安全边界：
      - 只改写能在信源表定位到序号 N 的引用；定位不到的"漏网引用"保持 `[^src]` 原样，
        交由既有 footnotes 兜底逻辑处理，行为与改动前完全一致，绝不新增裸脚标泄漏；
      - 跳过 `[^srcN]:` 脚注定义行开头，跳过位于信源汇总表 block 内部的匹配；
      - 复用模板既有 `.footnote-ref` 上标样式，外观与原脚注上标一致，无需改 CSS。
      - 无信源表时原样返回。
    """
    m_anchor = re.search(r"(?:数据)?信源汇总表", md_text)
    if not m_anchor:
        return md_text

    tail = md_text[m_anchor.end():]
    end_m = re.search(r"\n#{1,6}\s|\n---\s*\n|\n【自用声明】", tail)
    block_start = m_anchor.end()
    block_end = block_start + (end_m.start() if end_m else len(tail))
    block = md_text[block_start:block_end]

    # 1) 解析信源表：anchor -> 序号 N；并给首列序号单元格注入锚点 span
    anchor2num: dict[str, str] = {}
    new_lines = []
    for line in block.split("\n"):
        stripped = line.strip()
        if not stripped.startswith("|") or re.match(r"^\|\s*[-:|\s]+\|", line):
            new_lines.append(line)
            continue
        if "编号" in line or "信源名称" in line or "序号" in line:
            new_lines.append(line)
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if len(cells) < 4:
            new_lines.append(line)
            continue
        col_id = cells[0]
        m_num = re.search(r"\b(\d+)\b", col_id)
        if not m_num:
            new_lines.append(line)
            continue
        num = m_num.group(1)
        anchor2num[f"src{num}"] = num
        m_named = re.search(r"<!--\s*(src_[\w\-]+)\s*-->", col_id)
        if m_named:
            anchor2num[m_named.group(1)] = num
        # 幂等：已注入过锚点则不重复
        if "srcref-" not in col_id:
            cells[0] = f'<span id="{id_prefix}srcref-{num}"></span>{col_id}'
            line = "| " + " | ".join(cells) + " |"
        new_lines.append(line)

    if not anchor2num:
        return md_text

    md_text = md_text[:block_start] + "\n".join(new_lines) + md_text[block_end:]

    # 2) 改写正文引用。重新定位信源表 block 区间（首列注入后长度已变），
    #    用于在替换回调中排除"信源表内部"的匹配。
    m_anchor2 = re.search(r"(?:数据)?信源汇总表", md_text)
    tail2 = md_text[m_anchor2.end():]
    end_m2 = re.search(r"\n#{1,6}\s|\n---\s*\n|\n【自用声明】", tail2)
    b_start = m_anchor2.end()
    b_end = b_start + (end_m2.start() if end_m2 else len(tail2))

    def _repl(mo):
        if mo.group(2) == ":":            # [^srcN]: 脚注定义行开头，不动
            return mo.group(0)
        if b_start <= mo.start() < b_end:  # 信源汇总表内部，不动
            return mo.group(0)
        num = anchor2num.get(mo.group(1))
        if not num:                        # 定位不到 → 兜底，保持原样
            return mo.group(0)
        return (f'<sup class="footnote-ref src-ref">'
                f'<a class="footnote-ref" href="#{id_prefix}srcref-{num}">[{num}]</a></sup>')

    return re.sub(r"\[\^(src[\w\-]+)\](:?)", _repl, md_text)


def preprocess_md_for_tables(md_text: str) -> str:
    """修复 python-markdown tables 扩展的典型陷阱 —— 表格/列表前缺空行。

    场景：正文中常出现 `**标签**:` 紧跟 Markdown 表格或 `-` 列表的写法（如
    "**层级校验结果**:\\n| 层级 | ..."），markdown 会把整段吞进 <p> 而不识别表格。
    这里在这类模式之间自动补一个空行。
    """
    lines = md_text.splitlines()
    out = []
    # 只对"非块级起始行"补空行；块级起始：表格行 `|`、标题 `#`、引用 `>`、代码围栏 ```、
    # 列表行（`- ` / `* ` / `+ `，注意 `**` 开头的粗体段落不是列表）
    _is_list = re.compile(r"^(\s*)[-*+]\s")
    _is_table = re.compile(r"^\s*\|")
    _is_block_start = re.compile(r"^\s*(#|>|```)")

    def _is_block_line(s: str) -> bool:
        return bool(_is_table.match(s) or _is_block_start.match(s) or _is_list.match(s))

    for i, ln in enumerate(lines):
        out.append(ln)
        if i + 1 >= len(lines):
            continue
        nxt = lines[i + 1]
        # 当前行是"普通正文"（非空、非块级起始）；下一行是表格行或 `-` 列表 → 补空行
        if ln.strip() and not _is_block_line(ln):
            if _is_table.match(nxt) or re.match(r"^\s*-\s", nxt):
                out.append("")
    return "\n".join(out)


def parse_meta_chips(md_text: str) -> dict:
    """从 Markdown **顶部 frontmatter 区域**提取元信息行（**XX**: YY 格式）。

    严格边界：
      - 只扫描文档开头到首个 `---` 水平分隔符 或 首个 `## ` 二级标题 之前的区域
      - 仅接受 _FRONTMATTER_KEYS 白名单中的 key
      - value 须为单行、不含表格分隔符 `|`、且不跨越 Markdown 结构
    """
    meta = {}

    # 1) 锁定 frontmatter 区段 —— 文档头 → 首个 `---` 或首个 `## ` 之前
    lines = md_text.splitlines()
    fm_end = len(lines)
    for i, ln in enumerate(lines):
        s = ln.strip()
        # 跳过文档最顶端的一级标题（# 标题）
        if i == 0 or (i < 3 and s.startswith("# ")):
            continue
        if s == "---":
            fm_end = i
            break
        if s.startswith("## "):
            fm_end = i
            break
    fm_text = "\n".join(lines[:fm_end])

    # 2) 只抽取白名单 key，value 不允许含 `|`（防止吞入 Markdown 表格）
    pat = re.compile(r"^\*\*([^*|]+?)\*\*:\s*([^|\n]+?)\s*$", re.MULTILINE)
    for m in pat.finditer(fm_text):
        key = m.group(1).strip()
        val = m.group(2).strip()
        if key in _FRONTMATTER_KEYS:
            meta[key] = val
    return meta


def extract_title(md_text: str) -> str:
    """提取报告标题 = 文档顶部出现的第一个标题行（`# ` 或 `## `）。

    v1.24 修复（标题错位）：历史实现只用正则匹配首个二级标题（## 开头），存在两类错误——
      ① 汇总决策报告标题写成 `# xx交易决策报告`（H1）、章节用 `### 一、`（H3），全文无 H2，
         旧实现落到默认值 "交易决策报告"，丢失公司名；
      ② 基本面报告标题写成 `# xx基本面深度研究报告`（H1）、章节用 `## §一 摘要`（H2），
         旧实现把首个章节 `## §一 摘要 Snapshot` 误当成标题，导致 hero 大标题/页面标题全错。
    模板（templates/intent1_full_report.md 纯格式骨架 + references/faces/<face>.md §⭐ 报告输出规范）规定标题写在文档最顶部，故改为：自上而下取第一个
    H1/H2 标题行作为报告标题；兜底退化为全文首个 H2，再退化为默认值。
    这样无论标题写成 H1 还是 H2 都能正确命中，且不会被章节标题污染。
    """
    for line in md_text.splitlines():
        s = line.strip()
        if not s:
            continue
        m = re.match(r"^#{1,2}\s+(.+)$", s)
        if m:
            return m.group(1).strip()
        # 顶部的 frontmatter（**X**: Y）/ 引用 / 分隔线等非标题行：跳过，继续向下找标题
    m = re.search(r"^##\s+(.+)$", md_text, re.MULTILINE)
    return m.group(1).strip() if m else "交易决策报告"


def extract_code_from_title(title: str) -> str:
    """从标题 `XX公司（300308）交易决策报告` 中提取 6 位代码。"""
    m = re.search(r"[（(](\d{6})[）)]", title)
    return m.group(1) if m else ""


def extract_badge(meta: dict) -> str:
    style = meta.get("交易风格", "")
    risk = meta.get("风险等级", "")
    parts = [p for p in (style, risk) if p]
    return " · ".join(parts) if parts else "分析报告"


# ═══════════════════════════════════════════════════════════════════
#  HTML 结构处理
# ═══════════════════════════════════════════════════════════════════

def add_heading_ids(html: str, id_prefix: str = "") -> str:
    """为 h2~h5 添加 id 属性，用于 TOC 锚点。

    id_prefix（v24 faces-split）：合并 7 份文档时各文档传入不同前缀（如 "f1-"），
      避免跨文档同名章节（§一/§二…）id 碰撞；同时本函数内做同前缀去重（追加 -2/-3）。
    """
    seen: dict[str, int] = {}

    def replacer(m):
        tag = m.group(1)
        attrs = m.group(2) or ""
        inner = m.group(3)
        if "id=" in attrs:
            return m.group(0)
        text = re.sub(r"<[^>]+>", "", inner).strip()
        base = re.sub(r"[^\w\u4e00-\u9fff]+", "-", text).strip("-").lower()
        heading_id = f"{id_prefix}{base}"
        n = seen.get(heading_id, 0) + 1
        seen[heading_id] = n
        if n > 1:
            heading_id = f"{heading_id}-{n}"
        return f'<{tag}{attrs} id="{heading_id}">{inner}</{tag}>'
    return re.sub(r"<(h[2-5])(\s[^>]*)?>(.*?)</\1>", replacer, html)


# ── faces-split：决策稿 [详见：{面名}] 跨文档引用 → 切换到对应标签页 ──
INTENT1_FACE_NAMES = ("基本面", "政策面", "技术面", "资金面", "筹码面", "消息面")
_FACE_REF_RE = re.compile(r"\[详见\s*[：:]\s*(基本面|政策面|技术面|资金面|筹码面|消息面)\s*\]")


def convert_face_refs(html: str) -> str:
    """把决策稿里的 `[详见：{面名}]` / `[详见:{面名}]` 记号转成"切换到对应标签页"的按钮。

    v24 改版（Tab 多页面）：不再做页内锚点滚动，而是输出带 `data-target="page-{面名}"`
    的链接，由前端 JS 拦截点击 → 切换显示对应面的标签页（等同点击顶部导航栏）。
    href 作为无 JS 时的降级锚点。仅在非代码片段替换。"""
    skip_re = re.compile(r"<(code|pre)\b[^>]*>.*?</\1>", re.S | re.I)
    pieces: list[str] = []
    last = 0
    for m in skip_re.finditer(html):
        pieces.append(html[last:m.start()])
        pieces.append(m.group(0))
        last = m.end()
    pieces.append(html[last:])

    def repl(m: "re.Match") -> str:
        face = m.group(1)
        return (
            f'<a class="face-ref" data-target="page-{face}" href="#page-{face}" '
            f'title="切换到「{face}」标签页查看深度分析">详见 {face} ▸</a>'
        )

    for i in range(0, len(pieces), 2):
        pieces[i] = _FACE_REF_RE.sub(repl, pieces[i])
    return "".join(pieces)


# ── 内部交叉引用：[详见§X.X] / [详见§2.3-B1] / [详见§2.2 / §2.4] → <a class="cross-ref"> ──

def convert_cross_refs(html: str) -> str:
    """把 markdown 里 `[详见§X.X]` 形态的字面字符串转成可点击锚链接。

    规则：
      1) 先扫描 html 里所有 `<hN ... id="..."> 标题</hN>`，建立 (section_num → id) 映射；
         其中 section_num 形如 "2.1" / "2.3-b1" / "2.4c.4"（小写化）；
      2) 在正文（不含 <code>...</code> / <pre>...</pre> 代码段）里搜索
         `[详见§A.B]` / `[详见§A.B-XY]` / `[详见§A.B / §C.D]` 形态；
      3) 替换为 `<a class="cross-ref" href="#id" title="跳转到本报告章节 §X.X">详见 §X.X</a>`；
         未找到对应 id 时退回纯文本（不破坏可读性）。
    """
    # 1) 收集所有 (section_num, heading_id)
    sec_to_id: dict[str, str] = {}
    for m in re.finditer(
        r'<h[2-5][^>]*id="([^"]+)"[^>]*>(.*?)</h[2-5]>', html, re.S
    ):
        hid = m.group(1)
        # 标题文本（去内嵌标签）
        text = re.sub(r"<[^>]+>", "", m.group(2)).strip()
        # 标题开头形如 "2.1 宏观层…" / "2.3-B1 分业务…" / "2.4C.4 我 vs…" / "2.5-B3 …"
        sec_m = re.match(
            r"^([0-9]+(?:\.[0-9A-Za-z]+)*(?:-[0-9A-Za-z]+)?)\b",
            text,
        )
        if sec_m:
            sec_to_id[sec_m.group(1).lower()] = hid

    if not sec_to_id:
        return html

    # 2) 把整个 html 按 <code>...</code> 与 <pre>...</pre> 切片，仅在非代码片段做替换
    skip_re = re.compile(r"<(code|pre)\b[^>]*>.*?</\1>", re.S | re.I)
    pieces: list[str] = []
    last = 0
    for m in skip_re.finditer(html):
        pieces.append(html[last:m.start()])
        pieces.append(m.group(0))  # 原样保留
        last = m.end()
    pieces.append(html[last:])

    # `[详见§...]` 内部允许任意非 `]`/`/` 字符（含中文说明文字，如 `§0.3 北向二分识别表`），
    # 只在 repl() 里用 `§([\w\.\-]+)` 精确截取锚点编号本身，多余说明文字自动忽略。
    # v27 加固：此前限制为 `[\w\.\-]+`（不含空格）导致带附加说明的锚点整体不匹配、
    # 原样裸露成 C4 泄漏（历史事故：`[详见§0.3 北向二分识别表]`/`[详见§模块4 B2]`）。
    cross_ref_pat = re.compile(r"\[详见((?:\s*§[^\]/]+\s*/?\s*)+)\]")

    def repl(m: re.Match) -> str:
        body = m.group(1)
        # 拆分出多个 §X.X 锚
        anchors = re.findall(r"§([\w\.\-]+)", body)
        if not anchors:
            return m.group(0)
        out_parts: list[str] = []
        for sec in anchors:
            sec_key = sec.lower().rstrip(".-")
            hid = sec_to_id.get(sec_key)
            if not hid:
                # 退化匹配：尝试前缀（如 §2.4 但 id 是 2-4-…）
                hid = next(
                    (v for k, v in sec_to_id.items() if k.startswith(sec_key)),
                    None,
                )
            if hid:
                out_parts.append(
                    f'<a class="cross-ref" href="#{hid}" '
                    f'title="跳转到本报告章节 §{sec}">详见 §{sec}</a>'
                )
            else:
                # 找不到对应章节就保留纯文本（不破坏可读性）
                out_parts.append(f"详见 §{sec}")
        return " / ".join(out_parts)

    # 仅对非代码片段做替换
    for i in range(0, len(pieces), 2):
        pieces[i] = cross_ref_pat.sub(repl, pieces[i])

    return "".join(pieces)





# 中文章节序号 → 阿拉伯数字 / 罗马徽章
_CN_NUM_MAP = {
    "一": "Ⅰ", "二": "Ⅱ", "三": "Ⅲ", "四": "Ⅳ", "五": "Ⅴ",
    "六": "Ⅵ", "七": "Ⅶ", "八": "Ⅷ", "九": "Ⅸ", "十": "Ⅹ",
}


def _extract_section_num(text: str) -> tuple:
    """从章节标题提取数字徽章和正文。

    匹配模式：
      "一、核心结论..." → ("Ⅰ", "核心结论...")
      "二、公司概况"    → ("Ⅱ", "公司概况")
      "附录：..."        → ("附", "...")
      其他              → ("•", text)
    """
    # 中文数字开头
    m = re.match(r"^([一二三四五六七八九十])\s*[、.．]\s*(.+)$", text)
    if m:
        cn, rest = m.group(1), m.group(2).strip()
        return _CN_NUM_MAP.get(cn, cn), rest
    # 附录
    if text.startswith("附录") or text.startswith("附 "):
        rest = re.sub(r"^附录?\s*[：:]\s*", "", text)
        return "附", rest
    # 阿拉伯数字开头
    m = re.match(r"^(\d+)\s*[、.．]\s*(.+)$", text)
    if m:
        return m.group(1), m.group(2).strip()
    return "•", text


def _extract_subsection_label(text: str) -> tuple:
    """从子节标题提取 "1.2" / "1.2.3" 等多级编号和正文。

    "2.1 股权结构与实际控制人"     → ("2.1",   "股权结构与实际控制人")
    "3.3.1 财务表现"               → ("3.3.1", "财务表现")
    "投资概览卡"                   → ("",      "投资概览卡")
    """
    m = re.match(r"^(\d+(?:\.\d+){1,3})\s+(.+)$", text)
    if m:
        return m.group(1), m.group(2).strip()
    return "", text


def build_toc_html(body_html: str) -> str:
    """从 body_html 提取 h2/h3/h4 标题生成嵌套 TOC（v3 设计）。

    支持三层结构：
      - H2 主章节（"1. 核心结论" / "2. 公司概况" 等）→ 圆形徽章显示阿拉伯数字
      - H3 子节（"2.1 发展历程..."）              → 缩进显示完整 "2.1" 编号
      - H4 孙节（"3.3.1 财务表现"）               → 二级缩进显示完整 "3.3.1" 编号

    特殊处理：
      - 第一个 H2 若不带数字（通常是文档主标题）→ 跳过，避免与 hero 重复
      - 不带数字的 H2/H3/H4（如 "投资概览卡"）→ 仍渲染，徽章显示 "•"
      - h5 不渲染（避免 TOC 过长）

    渲染层级：H2 = toc-section（主节），H3/H4 = toc-child（子节，按层级缩进）。
    """
    # 提取所有 h2/h3/h4 标题
    # v24（faces-split）：优先读取标题真实的 id 属性（add_heading_ids 已注入，
    #   且可能带 per-page 前缀 d-/f1-…），仅在缺失时才回退到按文本重算 slug。
    #   这保证 TOC 锚点与正文标题 id 严格一致（含前缀），避免跨页 id 错位。
    items = []  # [(level_int, inner_text, heading_id), ...]
    for m in re.finditer(r"<(h[2-4])([^>]*)>(.*?)</\1>", body_html):
        level = int(m.group(1)[1])
        attrs = m.group(2) or ""
        inner = re.sub(r"<[^>]+>", "", m.group(3)).strip()
        if not inner:
            continue
        id_m = re.search(r'id="([^"]+)"', attrs)
        if id_m:
            heading_id = id_m.group(1)
        else:
            heading_id = re.sub(r"[^\w\u4e00-\u9fff]+", "-", inner).strip("-").lower()
        items.append((level, inner, heading_id))

    if not items:
        return '<ul class="toc-list"><li><a href="#">报告</a></li></ul>'

    # 跳过首个 H2 主标题（仅当它确实是"文档主标题"时）。
    # v1.24 修复：旧逻辑"首个 H2 不带阿拉伯/中文数字编号即视为主标题跳过"会误删
    #   形如 "§一 摘要 Snapshot"（以 § 开头、编号正则不识别）的正常章节，导致 §一 在 TOC 中丢失。
    #   现在标题统一为 H1 且已在正文剥离，正文首个 H2 通常就是真正的章节；
    #   仅当首个 H2 文本明确含报告主标题关键词（…研究报告/交易决策报告/…诊断报告 等）时才跳过。
    if items and items[0][0] == 2:
        _first = items[0][1]
        _title_kw = ("研究报告", "深度报告", "交易决策报告", "诊断报告", "解读报告",
                     "筛查报告", "投资策略", "调研纪要", "基本面深度", "技术面深度")
        if any(k in _first for k in _title_kw):
            items = items[1:]

    # 收集结构：H2 = section，H3/H4 = child（带 depth 标记）
    sections = []
    cur_section = None
    for level, text, hid in items:
        if level == 2:
            num, rest = _extract_section_num(text)
            cur_section = {"num": num, "text": rest, "id": hid, "children": []}
            sections.append(cur_section)
        else:
            label, rest = _extract_subsection_label(text)
            child = {"label": label, "text": rest, "id": hid, "depth": level - 2}
            if cur_section is None:
                # H3/H4 出现在 H2 之前，创建一个占位主节
                cur_section = {"num": "•", "text": "前言", "id": hid, "children": [child]}
                sections.append(cur_section)
            else:
                cur_section["children"].append(child)

    # 渲染
    html_parts = ['<ul class="toc-list">']
    for sec in sections:
        has_children = bool(sec["children"])
        html_parts.append('  <li class="toc-section">')
        html_parts.append(
            f'    <a class="toc-section-head" href="#{sec["id"]}">'
            f'<span class="toc-num">{sec["num"]}</span>'
            f'<span class="toc-section-text">{sec["text"]}</span>'
            + (f'<span class="toc-toggle">▾</span>' if has_children else '')
            + '</a>'
        )
        if has_children:
            html_parts.append('    <ul class="toc-children">')
            for ch in sec["children"]:
                # H4（depth=2）相对 H3（depth=1）再缩进 16px
                extra_indent = ' style="padding-left:52px"' if ch.get("depth", 1) >= 2 else ""
                label_html = (
                    f'<span class="toc-child-num">{ch["label"]}</span>'
                    if ch["label"] else ""
                )
                html_parts.append(
                    f'      <li class="toc-child">'
                    f'<a href="#{ch["id"]}"{extra_indent}>{label_html}{ch["text"]}</a></li>'
                )
            html_parts.append('    </ul>')
        html_parts.append('  </li>')
    html_parts.append('</ul>')
    return "\n".join(html_parts)


# ═══════════════════════════════════════════════════════════════════
#  图表注入（基于 anchor 关键词定位章节）
# ═══════════════════════════════════════════════════════════════════

#: 每张图表 key → 资料来源标注（图表目录与 figcaption 显示）
_CHART_SOURCE_MAP = {
    "kline":     "东方财富日 K 线数据，本报告测算 MA/布林带/支撑压力位",
    "annual":    "上市公司定期报告（来自 akshare 财务接口），本报告测算 YoY",
    "gm":        "上市公司定期报告（来自 akshare 财务接口）",
    "cashflow":  "上市公司定期报告（来自 akshare 财务接口）",
    "fcf":       "上市公司定期报告（来自 akshare 财务接口），本报告测算 FCF=经营现金流−资本开支",
    "valuation": "Wind/东方财富历史 PE/PB 时间序列，本报告测算分位数",
    "peer":      "可比公司公开披露财报（来自 akshare），本报告整理",
    "winrate":   "本报告六维加权胜率/赔率模型测算",
    "pe_band":   "东方财富/Wind 历史 PE/PB 时间序列，本报告测算分位带",
    "price_excess": "东方财富日线行情，本报告测算相对沪深 300 超额收益",
    "timeline":  "公司公告/年报披露的关键里程碑，本报告整理",
    "ownership": "上市公司最新定期报告披露的股权结构，本报告整理",
    "sentiment": "行业上游 CAPEX / 产能利用率 / 价格指数等公开数据，本报告整理",
}


def _render_chart_card(chart: dict, fig_num: int = None, id_prefix: str = "") -> str:
    """把一个 in-memory chart dict 渲染为带 <figure> + <figcaption> 编号包装的卡片 HTML。

    figure 编号策略：
      - fig_num 不为 None 时，渲染 `<figcaption>图 {N}：{title} · 资料来源：{src}</figcaption>`
      - SVG 内部已带 title/subtitle 文字（独立分发用），所以 figcaption 不重复 subtitle
      - 失败的图表也带编号，但 figcaption 显示"图 N（生成失败）：title"

    id_prefix（v24 faces-split）：多页面合并时各页传不同前缀（d-/f1-…），
      使 fig id 形如 `d-fig-1` 跨页唯一，避免标签页间锚点碰撞。

    注意：CSS 选择器 `figure.chart-figure` / `.chart-figure>figcaption` 在 b_fundamental.html 等
    模板中已定义。SVG 本身在内部画了 title/subtitle，外层 figcaption 提供页面级编号 + 资料来源。
    """
    key = chart.get("key", "")
    title = chart.get("title", "")
    src_label = _CHART_SOURCE_MAP.get(key, "本报告整理")
    fig_id = f'{id_prefix}fig-{fig_num}' if fig_num else ""

    if not chart.get("ok"):
        cap = (
            f'<figcaption class="chart-caption chart-caption-error">'
            f'图 {fig_num}（生成失败）：{title}' if fig_num else
            f'<figcaption class="chart-caption chart-caption-error">图（生成失败）：{title}'
        ) + '</figcaption>'
        return (
            f'<figure class="chart-figure chart-error"' + (f' id="{fig_id}"' if fig_id else '') + '>'
            f'{cap}'
            f'<div class="chart-error-msg">[图表未生成] {chart.get("err", "未知原因")}</div>'
            f'</figure>'
        )

    caption_text = f'图 {fig_num}：{title}' if fig_num else f'图：{title}'
    return (
        f'<figure class="chart-figure"' + (f' id="{fig_id}"' if fig_id else '') + '>'
        f'<div class="svg-wrap">{chart["svg"]}</div>'
        f'<figcaption class="chart-caption">'
        f'<span class="cap-num">{caption_text}</span>'
        f'<span class="cap-src">资料来源：{src_label}</span>'
        f'</figcaption>'
        f'</figure>'
    )


#: v25 图表占位符 token：作者在 markdown 出图处写 [[chart:kline]] / [[图:kline]]
#  显式声明位置（markdown→html 后通常为 <p>[[chart:kline]]</p>，亦兼容裸 token）。
#  这是"结构化数据图表"的确定性放置入口，优先级高于 anchor 关键词匹配。
_CHART_PLACEHOLDER_RE = re.compile(
    r"(?:<p>\s*)?\[\[\s*(?:chart|图)\s*[:：]\s*([A-Za-z_][\w\-]*)\s*\]\](?:\s*</p>)?",
    re.IGNORECASE,
)


def inject_charts_by_anchor(body_html: str, charts: list, id_prefix: str = "",
                            strict: bool = False, used: set = None) -> str:
    """按 anchor 关键词，把每张图表插入到对应章节的末尾（下一个同级或更高级 heading 之前）。

    核心策略（2026-04 改版）：
      1. **多关键词匹配**：anchor 支持 str 或 list/tuple，按顺序 OR 匹配，首个命中即定位
      2. **h2~h5 全扫描**：覆盖 `### 四、多维度分析`、`#### 4.1 基本面` 这类子章节
      3. **层级感知边界**：插入到"下一个同级或更高级"标题前（如 h4 命中则找下一个 h4/h3/h2）
      4. **主题兜底映射**：anchor 未命中时，按图表 key 的业务主题，兜底匹配就近大章节；
         **不再把未命中图表塞到文末"附录：图表"**。
      5. **统一编号**：按文档阅读顺序为每张图分配 "图 N" 编号，在 figcaption 中显示，
         并通过 `id="fig-N"` 支持双向引用（正文 `图 1` 可跳转）。

    v25 占位符 token（最高优先级，零猜测）：
      作者可在 markdown 出图处写 `[[chart:kline]]`（或 `[[图:kline]]`）显式声明位置，
      渲染器整段替换为对应图卡，并将该 key 计入 used；anchor/fallback 仅处理
      **未用占位符声明**的图表（向后兼容）。占位符引用的 key 若未生成/未知/重复，
      则整段删除，不会把 `[[chart:xxx]]` 字面量泄漏到页面。
      可用 key 见 chart_generator.CHART_SPECS（kline/annual/gm/cashflow/fcf/
      valuation/ownership/peer/winrate/timeline/sentiment/pe_band/price_excess）。

    v24 faces-split 多页面参数：
      - id_prefix：fig id 前缀（如 "f1-"），保证跨标签页 id 唯一。
      - strict：True 时，anchor 与 fallback 关键词均未命中本页任何标题的图表 **不强行塞入文末**，
        而是跳过（留给其它标签页匹配）。这样每张图只落在"含其对应章节"的那一页。
      - used：跨页共享的"已放置图表 key"集合；已放置的图表本页跳过，避免重复出现在多页。
    """
    if used is None:
        used = set()
    # 业务主题兜底映射：anchor 全部失败时，按 key 匹配这些关键词，定位到就近大章节
    # v1.7.1（2026-05 修复）：兜底关键词从泛词"基本面/财务"改为 v1.7 模板的具体子章节名，
    # 避免命中文档主标题（H2"xxx基本面深度研究报告"）导致所有图堆在文档开头。
    FALLBACK_KEYWORDS = {
        "kline":     ("投资概览卡", "核心结论", "关键价位", "支撑/压力", "技术面", "K 线", "K线"),
        "annual":    ("分业务预测矩阵", "盈利预测", "营收与净利润", "财务表现"),
        "gm":        ("利润表预测", "近年财务轨迹", "关键财务比率矩阵", "盈利预测", "毛利率", "财务表现"),
        "cashflow":  ("三表预测", "关键财务比率矩阵", "现金流", "财务表现"),
        "fcf":       ("DCF 估值", "DCF估值", "三表预测", "自由现金流", "财务表现"),
        "valuation": ("PE/PB-Band 历史分位分析", "PE/PB-Band", "历史分位", "估值分位", "估值与定价", "估值定价"),
        "peer":      ("可比公司估值", "竞争格局", "同业对比", "行业分析"),
        "winrate":   ("三档目标价情景", "综合研判", "交易计划", "核心结论"),
        "pe_band":   ("PE/PB-Band 历史分位分析", "PE/PB-Band", "估值定价", "估值分位"),
        "price_excess": ("投资概览卡", "核心结论", "市场表现", "走势"),
        "timeline":  ("发展历程与定位", "发展历程", "公司沿革", "公司概况"),
        "ownership": ("筹码面", "股东结构", "股东研究", "筹码", "公司画像", "公司定位", "公司概况", "股权结构与管理层", "股权结构"),
        "sentiment": ("全球光模块市场规模", "行业分析", "行业景气度", "行业层"),
    }

    # 扫描所有 h2~h5 标题
    heading_re = re.compile(r"<(h[2-5])[^>]*>(.*?)</\1>", re.IGNORECASE)
    headings = []  # [(start, end, level_int, text), ...]
    for m in heading_re.finditer(body_html):
        level = int(m.group(1)[1])  # 2/3/4/5
        text = re.sub(r"<[^>]+>", "", m.group(2)).strip()
        headings.append((m.start(), m.end(), level, text))

    # v1.7.1（2026-05 修复）：识别"文档主标题"——首个 H2 且形如 "xx（代码）基本面/技术面/...研究报告"
    # 该 H2 跨度极大（覆盖整篇文章），任何 fallback 关键词命中"基本面"都会落到主标题下方，
    # 导致 fig-2/3/4/5 全部堆在 §1 之前的"无人区"。
    # 处理：构造 _SKIP_HEADING_IDX 集合，_match_heading 与 fallback 时跳过这些"顶层标题"。
    _skip_idx = set()
    _title_keywords = ("研究报告", "深度报告", "投资策略", "调研纪要", "基本面深度", "技术面深度")
    for i, (_s, _e, lv, text) in enumerate(headings):
        if lv == 2 and any(k in text for k in _title_keywords):
            _skip_idx.add(i)
            break  # 只跳过首个匹配项作为"主标题"


    def _match_heading(keywords):
        """在 headings 中按 keywords 顺序找第一个文字包含任一关键词的标题，返回索引，否则 -1。
        v1.7.1：跳过 _skip_idx 中的"文档主标题"，避免 fallback 命中超大覆盖范围导致图表错位。
        """
        if isinstance(keywords, str):
            keywords = (keywords,)
        for kw in keywords:
            if not kw:
                continue
            for i, (_s, _e, _lv, text) in enumerate(headings):
                if i in _skip_idx:
                    continue
                if kw in text:
                    return i
        return -1

    def _section_end_pos(idx):
        """标题 idx 所在章节结束位置 = 下一个同级或更高级（level 更小）标题的 start。
        如果没有，则到 body 末尾。"""
        cur_level = headings[idx][2]
        for j in range(idx + 1, len(headings)):
            if headings[j][2] <= cur_level:
                return headings[j][0]
        return len(body_html)

    # ── v1.7.2（2026-05 修复）：图表编号改为按"文档出现顺序"分配，而非 CHART_SPECS 声明顺序 ──
    # 旧逻辑：fig-N 按 CHART_SPECS 中声明的顺序（kline=1, annual=2, gm=3, ...），
    #   结果文档中阅读顺序为 fig-1 → fig-7 → fig-2 → fig-4 → fig-3 → fig-6 → fig-5，乱跳。
    # 新逻辑：先把每张 ok 图的 (chart, insert_pos) 全部解析出来，按 insert_pos 升序排序后
    #   重新分配 fig-1, fig-2, fig-3 ... 这样文档阅读顺序与图编号严格一致。
    # 步骤：
    #   1) 第一轮：anchor 匹配，得到 (chart, insert_pos)；未命中走第二轮
    #   2) 第二轮：fallback 匹配；仍未命中放 body 末尾
    #   3) 按 insert_pos 升序排序，分配 fig-1..fig-N
    #   4) 渲染 chart_card，从后往前插入 body_html

    # pending 元素统一为 (chart, sort_pos, span_start, span_end)：
    #   - anchor/fallback 插入点：span_start == span_end == insert_pos（点插入）
    #   - 占位符替换：span_start/span_end 为 [[chart:key]] 段落的起止（整段替换）
    # sort_pos 用于"按文档阅读顺序统一分配 图 N"。
    pending = []
    removals = []   # 无法落图的占位符（未知 key / 该图未生成 / 重复）→ 整段删除 [(s, e)]

    ok_by_key = {c.get("key"): c for c in charts if c.get("ok")}

    # ── v25：占位符 token 直接放置（最高优先级，零猜测）──
    # 作者在 markdown 中写 [[chart:kline]] / [[图:kline]] 显式声明出图位置，
    # markdown→html 后通常为 <p>[[chart:kline]]</p>（也兼容裸 token）。
    # 命中占位符的图：整段替换为图卡，key 计入 used，后续 anchor/fallback 不再重复。
    # key 未生成/未知/重复者：整段删除，避免把 [[chart:xxx]] 字面量泄漏到页面。
    for m in _CHART_PLACEHOLDER_RE.finditer(body_html):
        key = m.group(1).strip()
        s, e = m.start(), m.end()
        chart = ok_by_key.get(key)
        if chart is not None and key not in used:
            pending.append((chart, s, s, e))
            used.add(key)
        else:
            removals.append((s, e))

    # 第一轮：按 anchor（primary）匹配（占位符已放置的 key 自动跳过）
    for chart in charts:
        if not chart.get("ok"):
            continue
        if chart.get("key") in used:
            continue
        anchor = chart.get("anchor", "")
        idx = _match_heading(anchor) if anchor else -1
        if idx == -1:
            continue
        insert_pos = _section_end_pos(idx)
        pending.append((chart, insert_pos, insert_pos, insert_pos))
        used.add(chart.get("key"))

    # 第二轮：未命中的图表按业务主题兜底
    for chart in charts:
        if not chart.get("ok"):
            continue
        key = chart.get("key")
        if key in used:
            continue
        fallback = FALLBACK_KEYWORDS.get(key, ())
        idx = _match_heading(fallback)
        if idx == -1:
            # strict（faces-split 多页面）：本页无任何匹配章节 → 不强行塞入，留给其它标签页
            if strict:
                continue
            # 极端情况：所有 heading 都匹配不上 → 退化为 body 末尾
            insert_pos = len(body_html)
        else:
            insert_pos = _section_end_pos(idx)
        pending.append((chart, insert_pos, insert_pos, insert_pos))
        used.add(key)

    # ── 按 sort_pos 升序排序 → 按文档阅读顺序统一分配 fig-N（占位符图与 anchor 图统一编号）──
    # 同 pos 时按 CHART_SPECS 声明顺序作为稳定排序键
    chart_order = {c.get("key"): i for i, c in enumerate(charts)}
    pending.sort(key=lambda x: (x[1], chart_order.get(x[0].get("key"), 999)))

    # 构造编辑操作 ops = [(start, end, html)]：
    #   - 点插入：start == end
    #   - 占位符替换：start < end（替换 [[chart:key]] 整段）
    # 同一插入点的多张图需合并成一块按 fig 升序拼接（避免后插入图跑到先插入图前面）。
    _insert_groups = {}   # pos -> [html, ...]（保持 fig 升序）
    _replace_ops = []     # [(start, end, html), ...]
    for fig_n, (chart, _sort_pos, span_s, span_e) in enumerate(pending, start=1):
        card = _render_chart_card(chart, fig_n, id_prefix)
        if span_s == span_e:
            _insert_groups.setdefault(span_s, []).append(card)
        else:
            _replace_ops.append((span_s, span_e, card))

    ops = list(_replace_ops)
    for pos, htmls in _insert_groups.items():
        ops.append((pos, pos, "".join(htmls)))   # 点插入：end==start
    # 未能落图的占位符整段删除（替换为空）
    ops.extend((s, e, "") for (s, e) in removals)

    # 从后往前应用，避免前面的编辑影响后面操作的绝对偏移
    for start, end, html in sorted(ops, key=lambda x: x[0], reverse=True):
        body_html = body_html[:start] + html + body_html[end:]

    return body_html


# ═══════════════════════════════════════════════════════════════════
#  表格编号 & 图表目录
# ═══════════════════════════════════════════════════════════════════

def number_tables(body_html: str, id_prefix: str = "") -> str:
    """为正文 markdown 表格自动加上 `<figure class="table-figure" id="tab-N">` 包装 + 编号。

    抓取规则：
      - 表格上方紧邻的 `<p><strong>表 N：xxx</strong></p>` 段落，作为 caption 文字
      - 若无显式 caption，则用 `表 N`（仅编号）

    id_prefix（v24 faces-split）：多页面合并时各页传不同前缀（d-/f1-…），
      使 tab id 形如 `f1-tab-1` 跨页唯一；可见编号（表 N）仍按本页从 1 计起。

    扫描所有 `<table>...</table>`（python-markdown tables 扩展输出），逐个包装。
    """
    n = 0
    out = []
    last = 0

    table_re = re.compile(r'(<table\b[^>]*>.*?</table>)', re.DOTALL | re.IGNORECASE)
    # 表格上方紧邻的加粗段落（caption）：</p>\s*<table>，且 <p> 内是 <strong>表 N：xxx</strong>
    cap_pat = re.compile(
        r'<p>\s*<strong>\s*(表\s*\d+\s*[：:].*?)\s*</strong>\s*</p>\s*$',
        re.DOTALL,
    )

    for m in table_re.finditer(body_html):
        n += 1
        s, e = m.start(), m.end()
        before = body_html[last:s]
        # 看看 before 末尾是否有紧邻的"**表 N：xxx**"加粗段
        cap_match = cap_pat.search(before)
        if cap_match:
            cap_text = re.sub(r'<[^>]+>', '', cap_match.group(1)).strip()
            # 把该 caption 段落从 before 中去掉，移到 figcaption
            before = before[:cap_match.start()] + before[cap_match.end():]
            caption_text = cap_text
        else:
            caption_text = f'表 {n}'

        figure_html = (
            f'<figure class="table-figure" id="{id_prefix}tab-{n}">'
            f'<figcaption class="table-caption"><span class="cap-num">{caption_text}</span></figcaption>'
            f'{m.group(1)}'
            f'</figure>'
        )
        out.append(before)
        out.append(figure_html)
        last = e

    out.append(body_html[last:])
    return ''.join(out)


def build_figure_index_html(body_html: str) -> str:
    """扫描 body_html 中的 `<figure id="fig-N">` 和 `<figure id="tab-N">`，
    抽取 figcaption 文字，构建"📊 图表目录"。

    返回 HTML 片段：双列布局（图 / 表 各一列），可点击跳转到对应 figure。
    若全文没有任何图/表，返回空串。
    """
    fig_pat = re.compile(
        r'<figure[^>]*\bid="([\w\-]*fig-\d+)"[^>]*>.*?<figcaption[^>]*>(.*?)</figcaption>',
        re.DOTALL,
    )
    tab_pat = re.compile(
        r'<figure[^>]*\bid="([\w\-]*tab-\d+)"[^>]*>\s*<figcaption[^>]*>(.*?)</figcaption>',
        re.DOTALL,
    )

    figs, tabs = [], []
    for m in fig_pat.finditer(body_html):
        fid = m.group(1)
        text = re.sub(r'<[^>]+>', ' ', m.group(2))
        text = re.sub(r'\s+', ' ', text).strip()
        # 只截到"资料来源"之前
        text = re.split(r'资料来源[：:]', text)[0].strip()
        figs.append((fid, text))

    for m in tab_pat.finditer(body_html):
        tid = m.group(1)
        text = re.sub(r'<[^>]+>', ' ', m.group(2))
        text = re.sub(r'\s+', ' ', text).strip()
        tabs.append((tid, text))

    if not figs and not tabs:
        return ''

    # v1.7.1（2026-05 修复）：改为可折叠 <details>，默认折叠态，不抢占视觉
    parts = [
        '<style>'
        'details.figure-index{margin:14px 0 20px;padding:14px 18px;border:1px solid #e6ebf2;'
        'background:linear-gradient(180deg,#fbfcfe 0%,#f5f8fc 100%);border-radius:12px}'
        'details.figure-index>summary.figure-index-title{cursor:pointer;list-style:none;'
        'font-size:14.5px;font-weight:700;color:#1a1a1a;letter-spacing:.02em;'
        'padding:0;margin:0;border:0;display:flex;align-items:center;gap:8px;user-select:none}'
        'details.figure-index>summary.figure-index-title::-webkit-details-marker{display:none}'
        'details.figure-index>summary.figure-index-title::before{'
        'content:"▶";font-size:11px;color:#888;transition:transform .2s;display:inline-block}'
        'details.figure-index[open]>summary.figure-index-title::before{transform:rotate(90deg)}'
        'details.figure-index .figure-index-count{font-weight:500;color:#888;font-size:12.5px;margin-left:auto}'
        'details.figure-index>.figure-index-grid{margin-top:12px;display:grid;'
        'grid-template-columns:1fr 1fr;gap:18px}'
        '@media (max-width:720px){details.figure-index>.figure-index-grid{grid-template-columns:1fr;gap:12px}}'
        '</style>'
        '<details class="figure-index">'
        '<summary class="figure-index-title">📊 图表目录'
        f'<span class="figure-index-count">（{len(figs)} 图 / {len(tabs)} 表）</span>'
        '</summary>'
        '<div class="figure-index-grid">'
    ]

    if figs:
        parts.append('<div class="figure-index-col"><div class="figure-index-col-title">'
                     f'图（{len(figs)}）</div><ol class="figure-index-list">')
        for fid, text in figs:
            parts.append(f'<li><a href="#{fid}">{text}</a></li>')
        parts.append('</ol></div>')

    if tabs:
        parts.append('<div class="figure-index-col"><div class="figure-index-col-title">'
                     f'表（{len(tabs)}）</div><ol class="figure-index-list">')
        for tid, text in tabs:
            parts.append(f'<li><a href="#{tid}">{text}</a></li>')
        parts.append('</ol></div>')

    parts.append('</div></details>')
    return ''.join(parts)


# ═══════════════════════════════════════════════════════════════════
#  faces-split（v24 不合稿）：决策稿 + 6 份分面深稿 → 单文件 Tab 多页面 HTML
#  （7 个独立"页面"：交易建议 + 六个面，顶部导航栏切换；每页等同 Intent-2 单报告）
# ═══════════════════════════════════════════════════════════════════

FACES_SPLIT_MARKER_RE = re.compile(r"<!--\s*INTENT1_ARCH\s*:\s*faces-split", re.I)

#: 导航栏分区定义（顺序即导航栏顺序）：(锚 id 后缀, 导航标签, 图标)
_FACE_NAV = [
    ("基本面", "基本面", "📈"),
    ("政策面", "政策面", "🏛"),
    ("技术面", "技术面", "📉"),
    ("资金面", "资金面", "💰"),
    ("筹码面", "筹码面", "🧮"),
    ("消息面", "消息面", "📰"),
]

#: faces-split 图表"归属面"映射：chart key → 应落在哪个 Tab 页。
#  仅多页面模式生效。每个面页只接收归属本面的图，避免 kline 的 anchor 含
#  "核心结论/关键价位"等通用词被"排第一处理"的基本面页抢走（每个面深稿都有
#  核心结论标题）。未列出的 key 归"决策"页（如 winrate=三档目标价情景图）。
_CHART_FACE_OWNER = {
    "kline":        "技术面",
    "price_excess": "技术面",
    "annual":       "基本面",
    "gm":           "基本面",
    "cashflow":     "基本面",
    "fcf":          "基本面",
    "valuation":    "基本面",
    "pe_band":      "基本面",
    "peer":         "基本面",
    "timeline":     "基本面",
    "ownership":    "基本面",
    "sentiment":    "消息面",
    "winrate":      "决策",
}


def is_faces_split(md_text: str) -> bool:
    """决策稿是否带 faces-split 架构标记。"""
    return bool(FACES_SPLIT_MARKER_RE.search(md_text or ""))


def discover_face_drafts(decision_md_path: Path) -> dict:
    """从决策稿路径推断同时间戳的 6 份分面深稿。
    决策稿命名：交易决策报告_{tail}.md；深稿命名：分面深稿_{面}_{tail}.md。
    返回 {面名: Path}，仅含实际存在的文件。"""
    m = re.match(r"交易决策报告_(.+)$", decision_md_path.stem)
    if not m:
        return {}
    tail = m.group(1)
    outdir = decision_md_path.parent
    found = {}
    for face, _label, _icon in _FACE_NAV:
        p = outdir / f"分面深稿_{face}_{tail}.md"
        if p.exists():
            found[face] = p
    return found


def _render_doc_inner(md_text: str, id_prefix: str, forecast_data: dict = None) -> str:
    """把单份 md 文档渲染为内部 HTML（不含模板、不注入图表）：
    预处理表格 → 注入脚注定义 → markdown 转换 → 去首个 H1 →
    **数据组件注入（[[table:KEY]] 等，从 forecast.json 渲染，须在编号前）** →
    加 id（带前缀去重）→ 内部 [详见§X.X] 交叉引用（仅本文档内）→ 表格编号（带前缀）。
    图表注入、[详见：{面名}] 跨页切换由调用方在本函数之后按页处理。"""
    import markdown
    conv = markdown.Markdown(extensions=["tables", "md_in_html", "sane_lists", "footnotes"])
    md_for_render = preprocess_md_for_tables(md_text)
    # v29：先把正文能定位到「信源汇总表」的 [^src] 引用改写成直达该表对应行的锚点上标，
    # 使信源信息单一数据源化；随后 inject 仅对无法映射的漏网引用兜底，文末不再生成
    # 与信源汇总表内容重复的脚注定义清单。
    md_for_render = rewrite_src_refs_to_source_table(md_for_render, id_prefix=id_prefix)
    md_for_render = inject_footnote_definitions(md_for_render)
    html = conv.convert(md_for_render)
    html = re.sub(r"^\s*<h1[^>]*>.*?</h1>\s*", "", html, count=1, flags=re.DOTALL | re.IGNORECASE)
    # v26：结构化数据组件（[[table:KEY]] 等）由代码从 forecast.json 渲染入槽。
    # 必须在 number_tables 之前，使渲染出的 <table> 被统一编号为"表 N"。
    if forecast_data:
        try:
            from report_components import inject_data_components
            html = inject_data_components(html, forecast_data, id_prefix=id_prefix)
        except Exception as e:
            print(f"[WARN] 数据组件注入失败: {e}", file=sys.stderr)
    html = add_heading_ids(html, id_prefix=id_prefix)
    html = convert_cross_refs(html)   # 同文档内 §X.X 交叉引用
    html = number_tables(html, id_prefix=id_prefix)
    return html


def _load_base_css() -> str:
    """从 a_decision.html 模板提取 <style>…</style> 中的 CSS 作为 Tab 文档的样式底座，
    保持单一样式来源（:root 配色变量、hero/content/footer、TOC 侧边栏、figure/table/chart、
    脚注、cross-ref、print 媒体查询等全部复用）。读取失败时返回空串。"""
    tpl = _SKILL_DIR / "assets" / "html_templates" / "a_decision.html"
    try:
        t = tpl.read_text(encoding="utf-8")
        m = re.search(r"<style>(.*?)</style>", t, re.S)
        return m.group(1) if m else ""
    except Exception:
        return ""


#: Tab 多页面专属样式（叠加在 base_css 之上）
_TAB_EXTRA_CSS = (
    "body{background:var(--bg)}"
    # ── 顶部导航栏（标签页切换）：白底 + 居中 ──
    ".tab-nav{position:sticky;top:0;z-index:300;display:flex;flex-wrap:wrap;"
    "justify-content:center;gap:6px;padding:9px 14px;background:#ffffff;"
    "border-bottom:1px solid var(--line);box-shadow:0 1px 8px rgba(0,0,0,.05)}"
    ".tab-nav .tab-btn{appearance:none;-webkit-appearance:none;cursor:pointer;"
    "display:inline-flex;align-items:center;gap:5px;padding:7px 15px;border-radius:999px;"
    "background:var(--line-2);color:var(--text-2);border:1px solid var(--line);"
    "font-size:13px;font-weight:600;"
    "font-family:inherit;line-height:1.2;transition:background .15s,color .15s,border-color .15s}"
    ".tab-nav .tab-btn:hover{background:#e3e8ef;color:var(--brand);border-color:var(--brand-bd)}"
    ".tab-nav .tab-btn.active{background:var(--brand);color:#fff;border-color:var(--brand);"
    "box-shadow:0 2px 8px var(--brand-shadow)}"
    # ── 标签页：仅 .active 显示 ──
    ".report-page{display:none}"
    ".report-page.active{display:block;animation:pagefade .22s ease}"
    "@keyframes pagefade{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}"
    # TOC 侧边栏下移到导航栏之下（高于 base_css 的 .toc-bar{top:24px}）
    ".report-page .toc-bar{top:62px;max-height:calc(100vh - 86px)}"
    "h2[id],h3[id],h4[id],h5[id]{scroll-margin-top:74px}"
    # 决策稿 [详见：面名] 切页按钮
    "a.face-ref{display:inline-block;padding:1px 9px;border-radius:6px;background:var(--brand-soft);"
    "color:var(--brand);font-size:13px;font-weight:600;text-decoration:none;border:1px solid var(--brand-bd);cursor:pointer}"
    "a.face-ref:hover{background:var(--brand);color:#fff}"
    "@media print{.tab-nav{display:none!important}.report-page{display:block!important}"
    ".report-page+.report-page{page-break-before:always}}"
)


#: Tab 多页面交互 JS（标签页切换 / [详见]切页 / per-page TOC 折叠·滚动·高亮 / 回到顶部 / hash）
_TAB_JS = """
(function(){
  var pages = Array.prototype.slice.call(document.querySelectorAll('.report-page'));
  var tabBtns = Array.prototype.slice.call(document.querySelectorAll('.tab-nav .tab-btn'));

  function showTab(pid){
    var hit=false;
    pages.forEach(function(p){ var on=(p.id===pid); p.classList.toggle('active', on); if(on)hit=true; });
    if(!hit) return;
    tabBtns.forEach(function(b){ b.classList.toggle('active', b.getAttribute('data-target')===pid); });
    try{ history.replaceState(null,'','#'+pid); }catch(e){}
    window.scrollTo(0,0);
    highlight();
  }

  // 顶部导航栏标签切换
  tabBtns.forEach(function(b){
    b.addEventListener('click', function(){ showTab(b.getAttribute('data-target')); });
  });

  // 正文里任意 [data-target]（如决策稿 [详见：面名] 链接） → 切到对应标签页
  document.querySelectorAll('[data-target]').forEach(function(el){
    if(el.closest('.tab-nav')) return;
    el.addEventListener('click', function(e){ e.preventDefault(); showTab(el.getAttribute('data-target')); });
  });

  // TOC 折叠/展开（作用于各页，仅可见页可点）
  document.querySelectorAll('.toc-section-head').forEach(function(head){
    head.addEventListener('click', function(e){
      var section=head.closest('.toc-section');
      if(e.target.classList.contains('toc-toggle')){ e.preventDefault(); section.classList.toggle('collapsed'); }
      else{ section.classList.remove('collapsed'); }
    });
  });

  // TOC 链接平滑滚动（页内）
  document.querySelectorAll('.toc-bar a[href^="#"]').forEach(function(a){
    a.addEventListener('click', function(e){
      var href=a.getAttribute('href');
      if(href && href.length>1){
        var t=document.getElementById(href.slice(1));
        if(t){ e.preventDefault(); var y=t.getBoundingClientRect().top+window.pageYOffset-72;
               window.scrollTo({top:y, behavior:'smooth'}); }
      }
    });
  });

  // 当前可见页的 TOC active 高亮
  function highlight(){
    var page=document.querySelector('.report-page.active'); if(!page) return;
    var heads=Array.prototype.slice.call(page.querySelectorAll('.content h3[id], .content h4[id]'));
    page.querySelectorAll('.toc-bar a.active, .toc-section-head.active').forEach(function(a){ a.classList.remove('active'); });
    if(!heads.length) return;
    var curId=heads[0].id;
    heads.forEach(function(h){ if(h.getBoundingClientRect().top-100<=0){ curId=h.id; } });
    var links=Array.prototype.slice.call(page.querySelectorAll('.toc-bar a[href]'));
    var link=null;
    for(var i=0;i<links.length;i++){ if(links[i].getAttribute('href')==='#'+curId){ link=links[i]; break; } }
    if(link){
      link.classList.add('active');
      var sec=link.closest('.toc-section');
      if(sec){ var hd=sec.querySelector('.toc-section-head'); if(hd) hd.classList.add('active'); }
    }
  }
  window.addEventListener('scroll', highlight, {passive:true});

  // 回到顶部
  var btn=document.getElementById('back-to-top');
  if(btn){
    window.addEventListener('scroll', function(){
      if(window.pageYOffset>400){ btn.classList.add('show'); } else { btn.classList.remove('show'); }
    });
    btn.addEventListener('click', function(){ window.scrollTo({top:0, behavior:'smooth'}); });
  }

  // 每页 TOC 计数
  pages.forEach(function(p){
    var c=p.querySelectorAll('.toc-bar a[href]').length;
    var el=p.querySelector('.toc-count'); if(el) el.textContent=c;
  });

  // 初始：按 location.hash 激活对应标签页（否则默认首页）
  var h=(location.hash||'').slice(1);
  if(h && document.getElementById(h) && document.getElementById(h).classList.contains('report-page')){ showTab(h); }
  else { highlight(); }
})();
"""


def _build_page_hero(md_text: str, fallback_title: str, fallback_badge: str) -> str:
    """为单个标签页生成 hero 头（标题 + 徽章 + 元信息 chips），复用 a_decision.html 的 .hero 样式。"""
    title = extract_title(md_text) or fallback_title
    meta = parse_meta_chips(md_text)
    badge = extract_badge(meta)
    if badge == "分析报告":
        badge = fallback_badge
    lead = f"{meta.get('交易风格', '')} {meta.get('风险等级', '')}".strip()
    chips = ""
    for k, v in meta.items():
        chips += f'<span class="meta-chip"><span class="meta-k">{k}</span>{v}</span>'
    return (
        '<header class="hero">'
        f'<div class="badge">{badge}</div>'
        f'<h1>{title}</h1>'
        + (f'<p class="lead">{lead}</p>' if lead else '')
        + f'<div class="meta-bar">{chips}</div>'
        '</header>'
    )


def _load_forecast(md_path: Path) -> dict:
    """加载与某份 md 同名配套的 forecast.json（`<stem>_forecast.json`），无则返回 None。

    用于驱动 `[[table:KEY]]` 等结构化数据组件（基本面深稿同目录下有此文件）。
    """
    try:
        fp = md_path.with_name(md_path.stem + "_forecast.json")
        if fp.exists():
            import json
            return json.loads(fp.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[WARN] 读取 forecast.json 失败 ({md_path.name}): {e}", file=sys.stderr)
    return None


def _gen_charts(code: str, skip_charts: bool, report_type: str, tag: str = "") -> list:
    """实时生成图表（in-memory）；失败返回 []。单面 / 多页面共用。"""
    if skip_charts or not code:
        return []
    suffix = f"，{tag}" if tag else ""
    print(f"[info] 实时生成图表（code={code}{suffix}）...")
    try:
        from chart_generator import build_charts_inmemory
        charts = build_charts_inmemory(code, verbose=True, report_type=report_type)
        ok = sum(1 for c in charts if c.get("ok"))
        print(f"[ok]   {ok}/{len(charts)} 张图表生成成功")
        return charts
    except Exception as e:
        print(f"[WARN] 图表生成失败: {e}；HTML 将不含图表。", file=sys.stderr)
        return []


def _make_page(
    md_text: str,
    id_prefix: str,
    page_id: str,
    label: str,
    icon: str,
    fallback_title: str,
    fallback_badge: str,
    charts: list,
    used_chart_keys: set,
    is_decision: bool = False,
    strict: bool = True,
    forecast_data: dict = None,
) -> dict:
    """把单份 md 渲染为一个"页面"对象（hero + TOC + 图表目录 + 正文）。

    这是**单面渲染的唯一内核**：Intent-2 单面报告 与 Intent-1 的每个 Tab 页
    都经由本函数产出，从而保证两者呈现完全同构（同一 hero / TOC / 正文 / 图表注入逻辑）。

    strict：传入 inject_charts_by_anchor。faces-split 下面页用 strict=False，
    保证"归属本面"的图即使无精确锚点也能落到本页（兜底到章节/页尾），不丢图。

    forecast_data：本页配套的 forecast.json（dict），用于渲染 [[table:KEY]] 等
    结构化数据组件；无则为 None（组件占位符将被删除，不泄漏字面量）。
    """
    inner = _render_doc_inner(md_text, id_prefix=id_prefix, forecast_data=forecast_data)
    if is_decision:
        inner = convert_face_refs(inner)   # 决策稿 [详见：面名] → 切页链接（仅多页面有效）
    # 始终调用：即便本页无图（如 --no-charts），也借此清理残留的 [[chart:KEY]] 占位符，
    # 避免字面量泄漏到页面（charts 为空时所有占位符按"未生成"整段删除）。
    inner = inject_charts_by_anchor(
        inner, charts or [], id_prefix=id_prefix, strict=strict, used=used_chart_keys
    )
    return {
        "id": page_id,
        "label": label,
        "icon": icon,
        "hero": _build_page_hero(md_text, fallback_title, fallback_badge),
        "toc": build_toc_html(inner),
        "figidx": build_figure_index_html(inner),
        "body": inner,
    }


def _wrap_section_html(page: dict, footer_note: str, active: bool) -> str:
    """页面对象 → <section class="report-page">…（单页 / Tab 页共用同一结构）。"""
    a = " active" if active else ""
    return (
        f'<section class="report-page{a}" id="{page["id"]}">'
        '<div class="shell">'
        f'{page["hero"]}'
        '<nav class="toc-bar" aria-label="目录">'
        '<div class="toc-header"><span class="toc-title">目录</span>'
        '<span class="toc-count">—</span></div>'
        f'{page["toc"]}</nav>'
        f'<main class="content">{page["figidx"]}{page["body"]}</main>'
        f'<footer class="footer">{footer_note}</footer>'
        '</div></section>'
    )


def build_document(pages: list, doc_title: str, footer_note: str) -> str:
    """把 1..N 个页面对象组装为完整 HTML 文档。

      - ``len(pages) == 1`` → 单面报告（**Intent-2**，无顶部导航栏）；
      - ``len(pages) > 1``  → Tab 多页面（**Intent-1**，顶部 7 个导航标签切换）。

    单页与多页共用同一套 CSS（base_css + _TAB_EXTRA_CSS）与 JS（_TAB_JS），
    因此 Intent-1 的六个面 Tab 与 Intent-2 单面报告呈现**逐字节同构**。
    """
    multi = len(pages) > 1

    nav_html = ""
    if multi:
        btns = []
        for i, pg in enumerate(pages):
            active = " active" if i == 0 else ""
            btns.append(
                f'<button class="tab-btn{active}" data-target="{pg["id"]}">'
                f'{pg["icon"]} {pg["label"]}</button>'
            )
        nav_html = '<nav class="tab-nav" aria-label="报告导航">' + "".join(btns) + '</nav>\n'

    sections = [
        _wrap_section_html(pg, footer_note, active=(i == 0))
        for i, pg in enumerate(pages)
    ]

    base_css = _load_base_css()
    return (
        '<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n'
        '<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        f'<title>{doc_title}</title>\n'
        '<style>\n' + base_css + "\n" + _TAB_EXTRA_CSS + '\n</style>\n'
        '</head>\n<body>\n'
        + nav_html
        + "\n".join(sections) + "\n"
        '<button class="back-to-top" id="back-to-top" aria-label="回到顶部" title="回到顶部">↑</button>\n'
        '<script>' + _TAB_JS + '</script>\n'
        '</body>\n</html>\n'
    )


def build_faces_split_document(
    decision_md_path: Path,
    decision_text: str,
    code: str,
    skip_charts: bool,
    footer_note: str,
) -> str:
    """**Intent-1**：决策稿 + 6 份分面深稿 → 单文件 Tab 多页面 HTML。

    每个 Tab 页都经由 :func:`_make_page` 渲染，与 Intent-2 单面报告完全同构。
    若未发现任何分面深稿则返回 ``None``（由调用方决定如何处理）。
    """
    drafts = discover_face_drafts(decision_md_path)
    if not drafts:
        print("[WARN] faces-split 标记存在但未发现任何分面深稿。", file=sys.stderr)
        return None

    # 图表只生成一次，按"归属面"分配到对应 Tab 页（每张图只落在它归属的那一页）
    charts = _gen_charts(code, skip_charts, report_type="trade", tag="faces-split 多页面")
    used: set = set()

    def _charts_for(owner: str) -> list:
        """取归属 owner 的图表子列表（key 未登记的默认归"决策"）。"""
        return [c for c in charts
                if _CHART_FACE_OWNER.get(c.get("key"), "决策") == owner]

    # ① 决策稿：只放归属"决策"的图（如 winrate 三档目标价情景），
    #    K 线/股权结构树等面专属图按映射落到对应面页，不再出现在决策页。
    decision_page = _make_page(
        decision_text, "d-", "page-决策", "交易建议", "⬛",
        "交易决策报告", "综合决策", _charts_for("决策"), used,
        is_decision=True, strict=True,
        forecast_data=_load_forecast(decision_md_path),
    )

    # ② 六个面深稿（按导航顺序，仅渲染实际存在的）：各自只接收归属本面的图。
    #    面页用 strict=False —— 归属本面的图即使无精确锚点也兜底落到本页，不丢图。
    pages = [decision_page]
    for idx, (face, label, icon) in enumerate(_FACE_NAV, start=1):
        p = drafts.get(face)
        if not p:
            continue
        try:
            face_text = p.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            print(f"[WARN] 读取分面深稿失败 {p.name}: {e}", file=sys.stderr)
            continue
        pages.append(
            _make_page(
                face_text, f"f{idx}-", f"page-{face}", label, icon,
                f"{label}深度分析", f"{label}深度分析", _charts_for(face), used,
                strict=False,
                forecast_data=_load_forecast(p),
            )
        )

    doc_title = extract_title(decision_text) or "交易决策报告"
    return build_document(pages, doc_title, footer_note)


# ═══════════════════════════════════════════════════════════════════
#  主转换
# ═══════════════════════════════════════════════════════════════════

def _build_rating_footer(data_cut: str = "N/A") -> str:
    """评级说明 + 风险等级 + AI 生成声明/免责声明 标准化 footer 模块（单/多页面共用）。"""
    return (
        '<div class="report-footer-rich">'
        '<style>'
        '.report-footer-rich{font-size:12px;color:#555;line-height:1.7;padding:18px 20px;background:#fafbfc;border-top:2px solid #d84033;margin-top:24px;border-radius:6px}'
        '.report-footer-rich .ff-sec{margin-bottom:14px}'
        '.report-footer-rich .ff-sec:last-child{margin-bottom:0}'
        '.report-footer-rich .ff-title{font-weight:700;color:#d84033;margin-bottom:6px;font-size:13px}'
        '.report-footer-rich .ff-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:6px 12px}'
        '.report-footer-rich .ff-grid div{padding:2px 0}'
        '.report-footer-rich .ff-mute{color:#888;font-size:11px;margin-top:8px}'
        '</style>'
        '<div class="ff-sec">'
        '<div class="ff-title">📊 投资评级体系（相对沪深300，6个月内预期收益）</div>'
        '<div class="ff-grid">'
        '<div><b>买入</b>：≥ +20%</div>'
        '<div><b>增持</b>：+5% ~ +20%</div>'
        '<div><b>中性</b>：-5% ~ +5%</div>'
        '<div><b>减持</b>：-15% ~ -5%</div>'
        '<div><b>卖出</b>：≤ -15%</div>'
        '</div>'
        '</div>'
        '<div class="ff-sec">'
        '<div class="ff-title">⚠️ 风险等级（R1-R5，匹配投资者适当性）</div>'
        '<div class="ff-grid">'
        '<div><b>R1</b> 极低风险（货基/存款）</div>'
        '<div><b>R2</b> 低风险（高等级债/银行理财）</div>'
        '<div><b>R3</b> 中风险（蓝筹/混合基金）</div>'
        '<div><b>R4</b> 中高风险（成长股/行业ETF）</div>'
        '<div><b>R5</b> 高风险（题材股/杠杆/期权）</div>'
        '</div>'
        '</div>'
        '<div class="ff-sec">'
        '<div class="ff-title">🤖 AI 生成声明 与 风险提示</div>'
        '<div><b>本报告由 AI 自动生成，非持牌分析师作品。</b>报告内容基于公开渠道的财务报表、市场数据、行业研究、新闻舆情等信息，由大语言模型结合本团队内置的分析框架（卖方研究范式 + 量化筛选规则 + 财务三表勾稽）自动撰写，<u>未经任何具有证券投资咨询资质的自然人或机构审核确认</u>。</div>'
        '<div style="margin-top:6px"><b>AI 局限性：</b>① 数据可能存在抓取错误或时效滞后；② 行业判断与盈利预测来自模型推理，可能与未来实际情况偏离；③ 对突发事件、政策变化、技术变革的反应可能滞后或失真；④ 同一问题不同时段可能输出不同结论。<b>所有数字、观点、目标价均需读者自行交叉验证后方可参考使用。</b></div>'
        '<div style="margin-top:6px"><b>非投资建议：</b>报告中的评级、目标价、买卖建议、估值结论仅作为研究学习的素材，<u>不构成任何形式的投资建议、要约或承诺</u>，不应作为投资决策的唯一依据。证券市场有风险，投资需谨慎，盈亏自负。</div>'
        '<div style="margin-top:6px"><b>使用范围：</b>本报告仅供报告生成者个人研究、学习、复盘使用；<u>禁止以任何形式公开传播、转载、发布、商用，或用于诱导他人投资决策</u>。如违规使用造成第三方损失，由使用者本人承担全部法律责任。</div>'
        '</div>'
        f'<div class="ff-mute">数据截止 {data_cut} ｜ 由 ETF 顾问团队自动生成（基于公开数据 + LLM 推理） ｜ 个人研究用途</div>'
        '</div>'
    )


def _detect_report_type(title: str) -> str:
    """从标题判断报告类型，用于图表筛选（基本面深度 → fundamental，其余 → trade）。"""
    if re.search(r"基本面(研究|深度|分析)|基本面深度研究", title or ""):
        return "fundamental"
    return "trade"


def _scan_render_leaks(doc_html: str) -> list:
    """转换器自检（缺陷前移）：扫描生成后的 HTML 是否残留"本应被转换/替换/删除"的字面量。

    这是把 HTML 阶段门禁（html_gate.py C2/C3/C4）的同类缺陷**前移到转换器**——
    转换器一旦发现残留就当场告警，便于在生成环节即时定位（而非等终检门禁打回返工）。
    扫描前剔除 <script>/<style>/<svg>/<code>/<pre>（这些区段可能合法含相关字符）。

    返回 [(标签, 次数), ...]；空列表表示无泄漏。
    """
    scan = doc_html
    for tag in ("script", "style", "svg", "code", "pre"):
        scan = re.sub(rf"<{tag}\b[^>]*>.*?</{tag}>", " ", scan, flags=re.S | re.I)
    leaks = []
    for pat, label in (
        (r"\[\[\s*chart\s*[:：]", "[[chart:]] 图表占位符"),
        (r"\[\[\s*图\s*[:：]", "[[图:]] 图表占位符"),
        (r"\[\[\s*table\s*[:：]", "[[table:]] 数据组件占位符"),
        (r"\[\^src[\w\-]*\]", "[^src…] 裸脚标引用"),
        (r"\[详见\s*[：:]\s*(?:基本面|政策面|技术面|资金面|筹码面|消息面)\s*\]", "[详见：{面}] 跨页记号"),
        (r"\[详见\s*§", "[详见§…] 章节交叉引用"),
    ):
        cnt = len(re.findall(pat, scan, re.I))
        if cnt:
            leaks.append((label, cnt))
    return leaks


#: 未过门禁强制降级时注入的"不可交付"红色水印条（固定在页面顶部，打印亦可见）。
_UNVERIFIED_WATERMARK = (
    '<div style="position:sticky;top:0;z-index:99999;background:#c0241b;color:#fff;'
    'font-weight:700;text-align:center;padding:8px 12px;font-size:14px;letter-spacing:.03em;'
    'box-shadow:0 2px 8px rgba(0,0,0,.25)">'
    '⛔ 未通过交付门禁 · 不可交付（DEBUG ONLY）—— 本文件由 --force-unverified 强制生成，'
    '内容未经质量门禁自证，严禁作为正式交付物使用。'
    '</div>\n'
)


def _inject_unverified_watermark(doc_html: str) -> str:
    """在 <body> 之后注入红色"不可交付"水印条。"""
    return re.sub(r"(<body[^>]*>\s*)", r"\1" + _UNVERIFIED_WATERMARK, doc_html, count=1)


def convert_md_to_html(
    md_path: Path,
    code: str = None,
    template_path: Path = None,   # 已废弃：保留参数仅为向后兼容，CSS 统一取自 a_decision.html
    output_path: Path = None,
    skip_charts: bool = False,
    unverified: bool = False,
) -> Path:
    try:
        import markdown  # noqa: F401  仅用于提前校验依赖，实际转换在子函数内进行
    except ImportError:
        print("[ERROR] 需要 markdown 库，请运行: pip install markdown", file=sys.stderr)
        sys.exit(1)

    md_text = md_path.read_text(encoding="utf-8")
    meta = parse_meta_chips(md_text)
    title = extract_title(md_text)

    # 推断股票代码
    if not code:
        code = extract_code_from_title(title)
    if not code and not skip_charts:
        print("[WARN] 未能从标题推断股票代码，且未传 --code；将跳过图表生成。", file=sys.stderr)
        skip_charts = True

    footer = _build_rating_footer(meta.get("数据截止时间", "N/A"))

    if is_faces_split(md_text):
        # ── Intent-1：决策稿带 faces-split 标记 → 单文件 Tab 多页面（决策 + 六个面） ──
        print("[info] 检测到 INTENT1_ARCH: faces-split，生成 Tab 多页面 HTML（决策稿 + 六个面）...")
        doc_html = build_faces_split_document(md_path, md_text, code, skip_charts, footer)
        if doc_html is None:
            print(
                "[ERROR] faces-split 标记存在但未发现配套的 6 份分面深稿，无法生成多页面 HTML。\n"
                "        请先在同目录产出『分面深稿_<面>_<同时间戳>.md』后重试。",
                file=sys.stderr,
            )
            sys.exit(1)
    else:
        # ── Intent-2：单面 / 单份报告 → 单页 HTML（与 Intent-1 各 Tab 页同构） ──
        charts = _gen_charts(code, skip_charts, _detect_report_type(title))
        page = _make_page(
            md_text, "d-", "page-main",
            title or "分析报告", "📄",
            title or "分析报告", extract_badge(meta),
            charts, set(),
            forecast_data=_load_forecast(md_path),
        )
        doc_html = build_document([page], title or "分析报告", footer)

    # ── 转换器自检（缺陷前移）：残留占位符/脚标/跨引用字面量当场告警 ──
    leaks = _scan_render_leaks(doc_html)
    if leaks:
        detail = "、".join(f"{lab}×{n}" for lab, n in leaks)
        print(
            "[WARN] 转换自检发现残留字面量（HTML 终检门禁 html_gate.py 将判 FAIL，请回查源 .md "
            "占位符/信源表/跨引用是否正确）: " + detail,
            file=sys.stderr,
        )

    # ── 未过门禁的强制降级：改名 _UNVERIFIED + 注入红色"不可交付"水印 ──
    if unverified:
        doc_html = _inject_unverified_watermark(doc_html)

    if output_path is None:
        output_path = md_path.with_suffix(".html")
    if unverified:
        # 在 .html 前插入 _UNVERIFIED，杜绝"无痕绕过"——降级产物文件名即自带不可交付标记
        output_path = output_path.with_name(output_path.stem + "_UNVERIFIED" + output_path.suffix)

    output_path.write_text(doc_html, encoding="utf-8")
    if unverified:
        print(f"[⚠️ 降级产物] 未过门禁的 HTML 已生成（带不可交付水印、文件名含 _UNVERIFIED）: {output_path}")
    else:
        print(f"[OK] HTML 报告已生成: {output_path}")
    return output_path


#: 交互式降级确认码——人工必须逐字键入此码，--force-unverified 才生效。
_UNVERIFIED_CONFIRM_CODE = "DEBUG-ONLY"


def _interactive_unverified_confirm() -> bool:
    """人工交互确认门（v26·根治历史事故）：

    `--force-unverified` 生效前，要求操作者在**真实交互终端**中逐字键入确认码
    `DEBUG-ONLY`。设计要点：

      • agent / CI / 管道等非交互式调用走的是重定向 stdin，`isatty()` 为 False，
        直接拒绝——把"钥匙"从『agent 能自己摸到的命令行/环境变量』换成『只有人能
        在键盘上拧的确认码』，从物理上杜绝自动化顺手绕过。
      • 即便在交互终端，也必须精确键入确认码，防误触。

    返回 True 表示人工确认通过、允许降级；False 表示拒绝。
    """
    # 非交互式（stdin 非 tty，典型为 agent/管道/CI 调用）→ 直接拒绝，无从键入确认码
    if not sys.stdin.isatty():
        print(
            "[⛔ 交付闸·拒绝降级] --force-unverified 需人工在交互终端键入确认码，但当前 stdin "
            "非交互式终端（检测为管道/重定向/自动化调用），无法完成人工确认，拒绝降级生成。",
            file=sys.stderr,
        )
        return False
    print(
        "\n[⚠️ 交付闸·人工降级确认] 你正在请求跳过交付台账 OVERALL: PASS 硬校验，强制生成"
        "*未通过门禁* 的 HTML（仅供本地调试，严禁作为交付物）。\n"
        f"  如确认继续，请逐字键入确认码：{_UNVERIFIED_CONFIRM_CODE}\n"
        "  （直接回车或键入任何其他内容，将放弃降级）",
        file=sys.stderr,
    )
    try:
        typed = input("确认码 > ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n[交付闸] 未获得有效确认，放弃降级。", file=sys.stderr)
        return False
    if typed == _UNVERIFIED_CONFIRM_CODE:
        return True
    print("[交付闸] 确认码不匹配，放弃降级。", file=sys.stderr)
    return False


def verify_delivery_gate(md_path: Path) -> tuple[bool, str]:
    """交付前自证硬闸（交付铁律配套）：

    交易决策报告_ 汇总报告生成 HTML 前，硬校验同 tail 的交付台账
    `_delivery_gate_ledger.md` 存在且显示 `OVERALL: PASS`。

    这把"报告没通过门禁就不应该收尾/交付"从纸面纪律升级为**产物边界的机器拦截**：
    门禁 FAIL（或根本没跑 gate_all.py）时，最终用户可见的 HTML 产物**生不出来**，
    杜绝历史事故"FAIL 也当成完成、还顺手把 HTML 交付出去"。

    返回 (是否放行, 说明)。非 交易决策报告_（单面深稿/专项）不强制，直接放行。
    """
    stem = md_path.stem
    if not stem.startswith("交易决策报告_"):
        return True, "非汇总决策报告，HTML 生成不强制台账校验"
    tail = stem[len("交易决策报告_"):]  # {code}_{简称}_{ts}
    ledger = md_path.parent / "_delivery_gate_ledger.md"
    if not ledger.exists():
        return False, (
            f"未找到交付台账 {ledger.name}：尚未运行 gate_all.py。\n"
            f"  请先运行：python scripts/gate_all.py --report \"{md_path}\"\n"
            f"  直到 OVERALL: PASS (exit 0) 后再生成 HTML。"
        )
    try:
        ltext = ledger.read_text(encoding="utf-8", errors="replace")
    except Exception as e:  # noqa: BLE001
        return False, f"读取台账失败: {e}"
    # 台账须属于本报告（tail 匹配）且 OVERALL 裁决行为 PASS
    tail_ok = (tail in ltext) or (md_path.name in ltext)
    # ❗精确解析 `## OVERALL: PASS/FAIL` 裁决行——不能用子串 "OVERALL: PASS"
    #   做模糊匹配：FAIL 台账的指引文字含"…直到 OVERALL: PASS"会造成假阳性放行。
    overall_m = re.search(r"^##\s*OVERALL:\s*(PASS|FAIL)", ltext, re.MULTILINE)
    pass_ok = bool(overall_m and overall_m.group(1) == "PASS")
    if not tail_ok:
        return False, (
            f"台账 {ledger.name} 不属于本报告（未匹配 tail『{tail}』）：可能是旧报告的台账。\n"
            f"  请对本报告复跑：python scripts/gate_all.py --report \"{md_path}\""
        )
    if not pass_ok:
        verdict = overall_m.group(1) if overall_m else "缺失/无法解析"
        return False, (
            f"台账 {ledger.name} 的裁决行 OVERALL = {verdict}（非 PASS）。\n"
            f"  报告没通过门禁不得收尾/交付：请按台账『未通过明细』逐项补深，复跑 gate_all.py 直到 OVERALL: PASS。"
        )
    return True, f"台账 {ledger.name} 校验通过（OVERALL: PASS，tail 匹配）"


def main():
    parser = argparse.ArgumentParser(description="将 Markdown 报告转换为带内嵌图表的 HTML 可视化报告（方案 B）")
    parser.add_argument("md_file", help="Markdown 报告文件路径")
    parser.add_argument("--code", help="股票代码（未提供时从 .md 标题中自动提取）")
    parser.add_argument("--template", help="[已废弃，忽略] 样式统一取自 a_decision.html，无需指定模板")
    parser.add_argument("--output", help="输出 HTML 文件路径（默认与 .md 同名 .html）")
    parser.add_argument("--no-charts", action="store_true", help="不生成图表（仅转文字）")
    parser.add_argument(
        "--force-unverified",
        action="store_true",
        help="[强烈不建议·仅本地调试] 跳过交付台账 OVERALL: PASS 硬校验。"
             "❗v26 起改为交互式人工确认门控：本 flag 生效前会在终端提示手动键入确认码 "
             "『DEBUG-ONLY』，且要求 stdin 为真实交互终端（tty）——非交互式管道调用（如 agent "
             "自动化）一律拒绝，无法通过键盘确认即无法降级。即便人工确认通过，产物也会强制降级为 "
             "*_UNVERIFIED.html + 红色『不可交付』水印，无法冒充正式交付物。正式交付严禁使用本 flag。",
    )
    args = parser.parse_args()

    md_path = Path(args.md_file)
    if not md_path.exists():
        print(f"[ERROR] 文件不存在: {md_path}", file=sys.stderr)
        sys.exit(1)

    # ── 交付前自证硬闸（铁律#11 配套）：交易决策报告 HTML 必须先过门禁 ──
    ok, why = verify_delivery_gate(md_path)
    unverified = False
    if not ok:
        # ❗❗ 逃生门·人工交互确认门控（v26 加固·根治历史事故）：
        #   历史事故根因——`--force-unverified` 仅靠命令行参数（v25 加了环境变量仍属"agent
        #   能自己摸到的钥匙"）即可绕过台账校验，在上下文压力下被 agent「顺手」滥用，把 FAIL
        #   的降级产物当成交付物。
        #   v26 把钥匙从『命令行/环境变量』换成『真实交互终端里人工逐字键入确认码 DEBUG-ONLY』——
        #   agent/CI/管道走的是非交互式 stdin（isatty=False），从物理上无法完成键盘确认，
        #   彻底杜绝自动化顺手触发；只有人在终端调试时才能拧开。
        if args.force_unverified:
            if _interactive_unverified_confirm():
                unverified = True
                print(
                    "[⚠️ 交付闸·强制降级] 人工确认码校验通过，已跳过台账校验，仅供调试；正式交付严禁。\n"
                    "  → 产物将改名为 *_UNVERIFIED.html 并注入红色『不可交付』水印，杜绝无痕绕过。\n"
                    "  原因：\n  " + why,
                    file=sys.stderr,
                )
            else:
                # 未通过人工确认（非交互终端 / 确认码不符 / 主动放弃）→ 拒绝生成
                print(
                    "[⛔ 交付闸·拒绝生成 HTML] --force-unverified 未通过人工交互确认，按门控拒绝降级。\n  "
                    + why
                    + "\n  ❗正确做法：按台账『未通过明细』补深 → 复跑 gate_all.py 直到 OVERALL: PASS，"
                    "由其自动生成正式 HTML。",
                    file=sys.stderr,
                )
                sys.exit(1)
        else:
            print(
                "[⛔ 交付闸·拒绝生成 HTML] 报告未通过门禁自证，禁止生成可交付的 HTML 产物。\n  "
                + why
                + "\n  ❗唯一正确动作：按台账未通过明细逐项补深 → 复跑 gate_all.py 直到 OVERALL: PASS，由其自动产出正式 HTML。",
                file=sys.stderr,
            )
            sys.exit(1)
    else:
        print(f"[交付闸·放行] {why}", file=sys.stderr)

    # 让 chart_generator 可以被 import
    sys.path.insert(0, str(_SCRIPT_DIR))

    convert_md_to_html(
        md_path,
        code=args.code,
        template_path=Path(args.template) if args.template else None,
        output_path=Path(args.output) if args.output else None,
        skip_charts=args.no_charts,
        unverified=unverified,
    )


if __name__ == "__main__":
    main()
