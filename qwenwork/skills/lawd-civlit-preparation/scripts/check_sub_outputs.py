#!/usr/bin/env python3
"""lawd-civlit-preparation 庭前准备编排器完整性门禁（防缺漏 + 防假通过）。

检查四份子产物是否**真的做完了**（产出来源已按套件合并后的新接线更新）：
    evidence-analysis   证据分析      ← lawd-civil-evidence-enhanced 模式A（综合证据分析）
    dispute-focus       争议焦点分析  ← lawd-complaint-analyzer 模式B（争议焦点分析）
    questioning         庭审发问策略  ← lawd-civlit-preparation 内部模式B（不再跨技能调用）
    judge-simulation    模拟裁判报告  ← lawd-civlit-judge-simulation（未变）

推荐文件名（编排时按此落盘，便于人工辨认）
------------------------------------------
    sub-evidence-analysis.md / sub-dispute-focus.md
    sub-questioning.md       / sub-judge-simulation.md

判据：内容级识别（主）+ 文件名（辅）
------------------------------------
文件名**不再单独构成通过依据**。一份文件要被认定为某子产物，必须同时满足：

1. **文件类型可读**：仅 .md/.markdown/.txt/.text/.docx 可作为子产物凭据；
   .pdf/.png/.jpg/.xlsx 等一律不认（律师原始输入材料多为此类）。
2. **产物标记**：标题行（前 12 个非空行）含该子产物的报告称谓，例如
       【证据专项分析报告】 / 证据专项分析报告
       【争议焦点专业分析报告】 / 争议焦点分析报告
       《XX案-庭审发问策略报告》 / 庭审发问策略报告
       《XX案-模拟裁判报告》 / 模拟裁判报告
   合并型产物（一个文件覆盖多个子技能）允许把标记写成正文中的小节标题
   （如 "## 二、争议焦点专业分析报告"），同样识别为覆盖该子技能。
3. **实质内容阈值**：去空白与控制字符后 ≥ --min-chars（默认 300）字符。
4. **必备小节**：该子产物应有的核心小节至少命中 N 项（见 SUBSKILLS.min_sections）。

模板/知识库类文件（文件名或标题含 template/知识库/示例/规范/清单模板 等）
一律排除，避免 --dir 误指向 references/ 时把 questioning-knowledge-base.md、
questioning-output-format-template.md 之类误判为子产物。

模式
----
- --mode full  ：要求 4 份产物齐全且内容合规，缺一即拦截；
- --mode single：配合 --skill 指定单份子产物，只检查对应 1 份。

产物来源（二选一）
------------------
- --dir   ：递归扫描目录内的产物文件；
- --files ：显式给出产物文件列表（准确性最高，推荐）。

拦截原因分类（照着提示就能修）
------------------------------
    [缺失]        目录/列表里没有任何该子产物候选文件
    [内容过短]    有产物标记但实质内容不足 --min-chars
    [缺必备小节]  有产物标记、篇幅够，但缺核心小节（列出缺哪几节）
    [格式无法识别]文件名像子产物，但内容里没有产物标记（多为原始输入材料/草稿）
    [格式不支持]  文件名像子产物，但为 pdf/png 等非文本类，不能作为凭据
    [读取失败]    文件损坏或编码无法解析

退出码：0=通过；1=拦截；2=输入错误。
"""

from __future__ import annotations

import argparse
import html
import re
import sys
import unicodedata
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

DEFAULT_MIN_CHARS = 300
TITLE_ZONE_LINES = 12          # 前 12 个非空行视为标题区
HEADING_MAX_LEN = 60           # 小节标题行的最大长度（超长视为正文引述，不算标记）

# 可作为子产物凭据的文本类扩展名
TEXT_SUFFIXES = {".md", ".markdown", ".txt", ".text"}
DOCX_SUFFIXES = {".docx"}
ALLOWED_SUFFIXES = TEXT_SUFFIXES | DOCX_SUFFIXES

# 模板 / 知识库 / 示例类文件：既不做候选，也不能凭内容通过
EXCLUDE_NAME_PATTERNS = (
    "template", "knowledge-base", "knowledge_base", "example", "sample",
    "checklist", "guide", "standard", "readme", "changelog", "skill.md",
    "知识库", "模板", "示例", "样例", "规范", "指引",
)
EXCLUDE_TITLE_PATTERNS = (
    "模板", "template", "示例", "样例", "example", "知识库", "格式规范",
    "输出格式", "填写说明", "checklist",
)

SUBSKILLS: Tuple[Dict[str, object], ...] = (
    {
        "id": "evidence-analysis",
        "label": "证据分析",
        "source": "lawd-civil-evidence-enhanced 模式A",
        # 内容级判据：报告称谓（标题行或合并型产物的小节标题）
        "title_markers": ("证据专项分析报告", "证据专项分析", "综合证据分析报告",
                          "证据分析报告", "证据分析子报告"),
        # 必备小节：(展示名, 任一命中即算该节存在)
        "sections": (
            ("证明责任/举证责任分配", ("证明责任", "举证责任")),
            ("证据审查/证据链分析", ("证据链", "证据审查", "三性审查", "证据三性")),
            ("对方证据质证意见", ("质证",)),
            ("举证策略/庭审证据应对", ("举证策略", "庭审证据应对", "举证方案", "证据缺漏", "补强")),
        ),
        "min_sections": 3,
        # 文件名关键词：仅作候选筛选与诊断，不能单独构成通过依据
        "filename_keywords": ("sub-evidence-analysis", "evidence-analysis",
                              "evidence_analysis", "证据分析", "证据专项",
                              "证据清单", "证据报告", "质证", "举证",
                              "lawd-civil-evidence-enhanced", "lawd-civlit-evidence"),
    },
    {
        "id": "dispute-focus",
        "label": "争议焦点分析",
        "source": "lawd-complaint-analyzer 模式B",
        "title_markers": ("争议焦点专业分析报告", "争议焦点专业分析",
                          "争议焦点分析报告", "争议焦点分析子报告"),
        "sections": (
            ("争议焦点体系/焦点清单", ("争议焦点体系", "焦点体系", "焦点清单", "核心焦点")),
            ("各焦点深度分析", ("深度分析", "焦点1", "焦点一", "焦点 1")),
            ("焦点攻防路线/应对预案", ("攻防", "应对路线", "应对预案", "攻防路线")),
            ("法庭辩论推演", ("辩论推演", "法庭辩论", "辩论")),
        ),
        "min_sections": 3,
        "filename_keywords": ("sub-dispute-focus", "dispute-focus", "dispute_focus",
                              "争议焦点", "争点",
                              "lawd-complaint-analyzer", "complaint-analyzer",
                              "lawd-civlit-dispute-focus"),
    },
    {
        "id": "questioning",
        "label": "庭审发问策略",
        "source": "lawd-civlit-preparation 内部模式B",
        "title_markers": ("庭审发问策略报告", "庭审发问策略", "发问策略报告",
                          "发问策略子报告"),
        "sections": (
            ("向对方发问设计", ("向对方发问", "发问设计", "发问提纲")),
            ("法官/仲裁员发问预判", ("法官发问", "仲裁员发问", "发问预判")),
            ("对方策略预判", ("对方策略预判", "对方策略", "对方预判")),
            ("应答准备与风险防控", ("应答准备", "风险防控", "应答口径")),
        ),
        "min_sections": 3,
        "filename_keywords": ("sub-questioning", "questioning", "庭审发问",
                              "发问策略", "发问提纲", "发问设计",
                              "courtroom-questioning",
                              "lawd-civlit-courtroom-questioning"),
    },
    {
        "id": "judge-simulation",
        "label": "模拟裁判报告",
        "source": "lawd-civlit-judge-simulation",
        "title_markers": ("模拟裁判报告", "模拟裁判子报告", "裁判预判报告",
                          "模拟裁判分析"),
        "sections": (
            ("事实法庭认定模拟", ("法庭认定", "事实认定", "认定模拟")),
            ("争议焦点法庭归纳", ("焦点法庭归纳", "争议焦点归纳", "法庭归纳", "争议焦点")),
            ("模拟裁判文书/结果预判", ("模拟裁判文书", "裁判结果预判", "裁判文书", "判决预测")),
            ("弱点识别与补强建议", ("弱点识别", "补强建议", "弱点")),
        ),
        "min_sections": 3,
        "filename_keywords": ("sub-judge-simulation", "judge-simulation",
                              "judge_simulation", "模拟裁判", "裁判预判", "法官视角",
                              "lawd-civlit-judge-simulation"),
    },
)

# 短别名与已合并的旧技能名 → 新子产物 id（--skill 旧写法保持可用）
ALIASES = {
    "evidence": "evidence-analysis",
    "lawd-civlit-evidence": "evidence-analysis",
    "lawd-civil-evidence-enhanced": "evidence-analysis",
    "lawd-civlit-dispute-focus": "dispute-focus",
    "lawd-complaint-analyzer": "dispute-focus",
    "courtroom-questioning": "questioning",
    "lawd-civlit-courtroom-questioning": "questioning",
    "lawd-civlit-judge-simulation": "judge-simulation",
}

SKILL_BY_ID = {s["id"]: s for s in SUBSKILLS}


class InputError(Exception):
    """输入层错误，退出码 2。"""


# ---------------------------------------------------------------- 文本提取


def _docx_text(path: Path) -> str:
    """极简 docx 取文：解 zip 取 word/document.xml，按段落还原纯文本。"""
    with zipfile.ZipFile(path) as zf:
        xml = zf.read("word/document.xml").decode("utf-8", errors="replace")
    xml = re.sub(r"<w:tab\b[^>]*/>", "\t", xml)
    xml = re.sub(r"<w:br\b[^>]*/>", "\n", xml)
    xml = re.sub(r"</w:p\s*>", "\n", xml)
    xml = re.sub(r"<[^>]+>", "", xml)
    return html.unescape(xml)


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in DOCX_SUFFIXES:
        return _docx_text(path)
    return path.read_text(encoding="utf-8", errors="replace")


def substantive_length(text: str) -> int:
    """实质字符数：去掉空白、控制字符与解码失败的替换符。"""
    count = 0
    for ch in text:
        if ch.isspace() or ch == "\ufffd":
            continue
        if unicodedata.category(ch) in {"Cc", "Cf", "Cs", "Co", "Cn"}:
            continue
        count += 1
    return count


def heading_lines(text: str) -> List[str]:
    """返回"看起来像标题"的短行（含标题区与正文小节标题）。"""
    return [ln.strip() for ln in text.splitlines()
            if ln.strip() and len(ln.strip()) <= HEADING_MAX_LEN]


# ---------------------------------------------------------------- 单文件分析


class Verdict:
    """(文件, 子产物) 的判定结果。"""

    __slots__ = ("status", "title_hit", "detail", "missing")

    def __init__(self, status: str, title_hit: bool = False,
                 detail: str = "", missing: Sequence[str] = ()) -> None:
        self.status = status          # ok / short / sections / no-marker / unsupported / unreadable / none
        self.title_hit = title_hit
        self.detail = detail
        self.missing = list(missing)


class FileInfo:
    """一份候选文件的完整分析结果。"""

    def __init__(self, path: Path, min_chars: int) -> None:
        self.path = path
        self.excluded_reason: Optional[str] = None
        self.text: str = ""
        self.length: int = 0
        self.read_error: Optional[str] = None
        self.verdicts: Dict[str, Verdict] = {}
        self._analyze(min_chars)

    # -- 内部 --------------------------------------------------------
    def _analyze(self, min_chars: int) -> None:
        name = self.path.name.lower()
        suffix = self.path.suffix.lower()

        if any(p in name for p in EXCLUDE_NAME_PATTERNS):
            self.excluded_reason = "模板/知识库/示例类文件，不作为子产物"
        supported = suffix in ALLOWED_SUFFIXES

        if not supported:
            for s in SUBSKILLS:
                if self.filename_hits(s):
                    self.verdicts[s["id"]] = Verdict(
                        "unsupported",
                        detail=f"扩展名 {suffix or '(无)'} 不是文本类，无法核验内容")
            return

        try:
            self.text = extract_text(self.path)
        except (OSError, zipfile.BadZipFile, KeyError, ValueError) as exc:
            self.read_error = f"{type(exc).__name__}: {exc}"
            for s in SUBSKILLS:
                if self.filename_hits(s):
                    self.verdicts[s["id"]] = Verdict("unreadable", detail=self.read_error)
            return

        self.length = substantive_length(self.text)
        headings = heading_lines(self.text)
        title_zone = headings[:TITLE_ZONE_LINES]

        if self.excluded_reason is None and any(
                p in ln.lower() for ln in title_zone for p in EXCLUDE_TITLE_PATTERNS):
            self.excluded_reason = "标题标明为模板/示例/知识库，不作为子产物"

        for s in SUBSKILLS:
            sid = str(s["id"])
            markers = tuple(s["title_markers"])  # type: ignore[arg-type]
            title_hit = any(m in ln for ln in title_zone for m in markers)
            anchor_hit = title_hit or any(m in ln for ln in headings for m in markers)

            if self.excluded_reason is not None:
                if title_hit or anchor_hit or self.filename_hits(s):
                    self.verdicts[sid] = Verdict("excluded", detail=self.excluded_reason)
                continue

            if not anchor_hit:
                if self.filename_hits(s):
                    extra = "" if self.length >= min_chars else f"，且实质内容仅 {self.length} 字"
                    self.verdicts[sid] = Verdict(
                        "no-marker",
                        detail=f"内容里找不到产物标记（应有标题含：{markers[0]}）{extra}")
                continue

            if self.length < min_chars:
                self.verdicts[sid] = Verdict(
                    "short", title_hit=title_hit,
                    detail=f"实质内容仅 {self.length} 字（阈值 {min_chars} 字）")
                continue

            missing = [label for label, alts in s["sections"]  # type: ignore[misc]
                       if not any(a in self.text for a in alts)]
            present = len(s["sections"]) - len(missing)  # type: ignore[arg-type]
            if present < int(s["min_sections"]):
                self.verdicts[sid] = Verdict(
                    "sections", title_hit=title_hit,
                    detail=f"必备小节仅命中 {present}/{len(s['sections'])} 项"
                           f"（至少 {s['min_sections']} 项）",
                    missing=missing)
                continue

            self.verdicts[sid] = Verdict("ok", title_hit=title_hit,
                                         detail=f"实质内容 {self.length} 字，"
                                                f"必备小节 {present}/{len(s['sections'])} 项")

    # -- 对外 --------------------------------------------------------
    def filename_hits(self, skill: Dict[str, object]) -> bool:
        name = self.path.name.lower()
        return any(str(k).lower() in name for k in skill["filename_keywords"])  # type: ignore[union-attr]


# ---------------------------------------------------------------- 收集与分配


def gather_files(args: argparse.Namespace) -> List[Path]:
    if args.files:
        files = [Path(f) for f in args.files]
        missing = [str(f) for f in files if not f.exists()]
        if missing:
            raise InputError("以下文件不存在：" + "、".join(missing))
        not_file = [str(f) for f in files if not f.is_file()]
        if not_file:
            raise InputError("以下路径不是文件：" + "、".join(not_file))
        return files
    return sorted(p for p in args.dir.rglob("*")
                  if p.is_file() and not p.name.startswith("."))


def assign(infos: List[FileInfo], targets: Sequence[str]) -> Dict[str, FileInfo]:
    """为每个子产物挑一份内容合规的产物。

    先用"标题行即该子产物"的独占文件（最强证据），再用未占用的合规文件，
    最后允许复用同一份合并型产物（一个文件同时覆盖多个子技能）。
    """
    ok: Dict[str, List[FileInfo]] = {sid: [] for sid in targets}
    for info in infos:
        for sid in targets:
            v = info.verdicts.get(sid)
            if v is not None and v.status == "ok":
                ok[sid].append(info)

    assigned: Dict[str, FileInfo] = {}
    used: set = set()

    for sid in targets:                                  # 一轮：标题独占
        cands = [i for i in ok[sid]
                 if i.verdicts[sid].title_hit and i.path not in used]
        if cands:
            assigned[sid] = cands[0]
            used.add(cands[0].path)
    for sid in targets:                                  # 二轮：未占用的合规文件
        if sid in assigned:
            continue
        cands = [i for i in ok[sid] if i.path not in used]
        if cands:
            assigned[sid] = cands[0]
            used.add(cands[0].path)
    for sid in targets:                                  # 三轮：允许合并型产物复用
        if sid in assigned and ok[sid]:
            continue
        if ok[sid]:
            assigned[sid] = ok[sid][0]
    return assigned


_REASON_PRIORITY = ("sections", "short", "no-marker", "unreadable",
                    "unsupported", "excluded")
_REASON_TAG = {
    "sections": "缺必备小节",
    "short": "内容过短",
    "no-marker": "格式无法识别",
    "unreadable": "读取失败",
    "unsupported": "格式不支持",
    "excluded": "非产物文件",
}


def failure_message(skill: Dict[str, object], infos: List[FileInfo]) -> str:
    sid = str(skill["id"])
    head = f"{skill['label']}（{sid} ← {skill['source']}）"
    candidates: Dict[str, List[FileInfo]] = {}
    for info in infos:
        v = info.verdicts.get(sid)
        if v is not None and v.status != "ok":
            candidates.setdefault(v.status, []).append(info)

    for status in _REASON_PRIORITY:
        hits = candidates.get(status)
        if not hits:
            continue
        parts = []
        for info in hits[:3]:
            v = info.verdicts[sid]
            note = v.detail
            if v.missing:
                note += "；缺：" + "、".join(v.missing)
            parts.append(f"{info.path}（{note}）")
        fix = {
            "sections": "补齐缺失小节后重跑该子工作",
            "short": "该文件基本是空壳，请重跑子工作生成完整报告",
            "no-marker": "这看起来是原始输入材料或草稿，不是子产物；"
                         "请重跑子工作并让报告首行带上产物标记",
            "unreadable": "文件损坏或编码异常，请重新落盘",
            "unsupported": "pdf/png 等原始材料不能当子产物，请落盘为 .md/.txt/.docx 报告",
            "excluded": "该文件是模板/知识库/示例，不是本次子产物",
        }[status]
        return (f"[{_REASON_TAG[status]}] {head}：" + "；".join(parts)
                + f" → 处理：{fix}")

    markers = "/".join(str(m) for m in list(skill["title_markers"])[:2])  # type: ignore[arg-type]
    return (f"[缺失] {head} 产物缺失：目录/列表内无任何候选文件"
            f" → 处理：重跑该子工作，落盘 .md 报告（推荐文件名 sub-{sid}.md，"
            f"标题行需含「{markers}」）")


# ---------------------------------------------------------------- 主流程


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="庭前准备编排器完整性门禁：按内容核验 4 份子产物是否真的做完",
        epilog="子产物名：" + "、".join(str(s["id"]) for s in SUBSKILLS)
               + "；single 模式亦接受别名 evidence 及已合并的旧技能名"
                 "（lawd-civlit-evidence / lawd-civlit-dispute-focus /"
                 " lawd-civlit-courtroom-questioning / lawd-civlit-judge-simulation）。"
                 " 判据=内容级产物标记 + 实质字数 + 必备小节；文件名仅作辅助。",
    )
    parser.add_argument("--mode", required=True, choices=["full", "single"],
                        help="full=检查全部 4 份产物；single=配合 --skill 只查 1 份")
    parser.add_argument("--dir", type=Path, help="产物目录（递归扫描）")
    parser.add_argument("--files", nargs="+", help="产物文件列表（显式给出，推荐）")
    parser.add_argument("--skill",
                        choices=[str(s["id"]) for s in SUBSKILLS] + list(ALIASES),
                        help="single 模式下要检查的子产物（含历史别名）")
    parser.add_argument("--min-chars", type=int, default=DEFAULT_MIN_CHARS,
                        metavar="N",
                        help=f"单份子产物的最小实质字符数（默认 {DEFAULT_MIN_CHARS}）")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    if bool(args.dir) == bool(args.files):
        print("输入错误：--dir 与 --files 必须且只能指定其一", file=sys.stderr)
        return 2
    if args.dir is not None and not args.dir.is_dir():
        print(f"输入错误：目录不存在：{args.dir}", file=sys.stderr)
        return 2
    if args.mode == "single" and not args.skill:
        print("输入错误：single 模式必须指定 --skill", file=sys.stderr)
        return 2
    if args.mode == "full" and args.skill:
        print("输入错误：full 模式不接受 --skill", file=sys.stderr)
        return 2
    if args.min_chars < 0:
        print("输入错误：--min-chars 不能为负数", file=sys.stderr)
        return 2

    try:
        files = gather_files(args)
    except InputError as exc:
        print(f"输入错误：{exc}", file=sys.stderr)
        return 2

    targets = ([ALIASES.get(args.skill, args.skill)] if args.mode == "single"
               else [str(s["id"]) for s in SUBSKILLS])

    infos = [FileInfo(p, args.min_chars) for p in files]
    assigned = assign(infos, targets)

    shared = [sid for sid in targets if sid in assigned]
    counts: Dict[Path, int] = {}
    for sid in shared:
        counts[assigned[sid].path] = counts.get(assigned[sid].path, 0) + 1

    checks: List[str] = []
    errors: List[str] = []
    for sid in targets:
        s = SKILL_BY_ID[sid]
        if sid in assigned:
            info = assigned[sid]
            v = info.verdicts[sid]
            merged = "（合并型产物，同时覆盖多个子技能）" if counts.get(info.path, 0) > 1 else ""
            checks.append(f"[齐备] {s['label']}（{sid} ← {s['source']}）"
                          f"→ {info.path}{merged}｜{v.detail}")
        else:
            errors.append(failure_message(s, infos))

    print(f"== 庭前准备产物完整性门禁（mode={args.mode}，候选文件 {len(files)} 个，"
          f"最小实质字数 {args.min_chars}）：通过清单 ==")
    for item in checks:
        print(f"- {item}")
    if not checks:
        print("-（无）")
    if errors:
        print("== 拦截清单 ==", file=sys.stderr)
        for item in errors:
            print(f"- {item}", file=sys.stderr)
        print(f"门禁不通过：共拦截 {len(errors)} 项", file=sys.stderr)
        return 1
    print(f"门禁通过：{len(targets)} 份子产物齐全，且内容级校验（产物标记 + 实质字数"
          f" + 必备小节）全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
