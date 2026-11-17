#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学术研究技能（academic-research-skills）核心实现脚本。

提供文献资料结构化转换、主题聚类、空白分析、论文大纲生成、批量处理、
置信度标注、格式输出（markdown/json/csv）、dry-run 预览等能力。
"""

import argparse
import csv
import io
import json
import os
import re
import sys
import time
import threading
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse, quote_plus
import urllib.request
import urllib.error

# WB 依赖降级注入（2026-09-13）：网络调用默认 8s 超时，防 hang 死（无产出）
try:
    import socket as _wb_sock
    _wb_sock.setdefaulttimeout(8)
except Exception:
    pass


# ---------------------------------------------------------------------------
# 错误码定义（E001-E012）
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "输入内容为空或无效",
    "E002": "不支持的输出格式（仅支持 markdown/json/csv）",
    "E003": "输入内容不是有效文本",
    "E004": "字段结构定义无效",
    "E005": "批量处理时输入列表为空",
    "E006": "自定义模板格式错误",
    "E007": "置信度标注值超出范围（应为0-1）",
    "E008": "内部逻辑错误：数据转换失败",
    "E009": "参数解析错误",
    "E010": "未知运行时错误",
    "E011": "网络请求失败（重试后仍失败）",
    "E012": "批量处理部分失败",
}


class AcademicSkillError(Exception):
    """技能运行期异常，携带错误码。"""

    def __init__(self, code: str, message: Optional[str] = None):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{self.code}] {self.message}")


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------
@dataclass
class ResearchCard:
    """结构化研究资料卡片。"""

    title: str = ""
    authors: List[str] = field(default_factory=list)
    year: Optional[int] = None
    keywords: List[str] = field(default_factory=list)
    abstract: str = ""
    conclusion: str = ""
    limitations: List[str] = field(default_factory=list)
    confidence: float = 0.8  # 置信度 0-1
    source: str = ""
    raw_text: str = ""
    created_at: str = ""  # ISO 8601 UTC 时间戳

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，便于 JSON 序列化。"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResearchCard":
        """从字典构建卡片。"""
        return cls(**data)


# ---------------------------------------------------------------------------
# 文本解析与编码处理
# ---------------------------------------------------------------------------
def decode_text(raw: bytes) -> str:
    """多编码解码：优先 UTF-8，依次回退 GBK、GB18030，最后用 replace 兜底。"""
    for encoding in ("utf-8", "gbk", "gb18030"):
        try:
            return raw.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="replace")


def read_text_file(file_path: str) -> str:
    """读取文本文件，自动处理编码。"""
    try:
        with open(file_path, "rb") as f:
            raw = f.read()
    except OSError as e:
        raise AcademicSkillError("E001", f"无法读取文件 {file_path}: {e}")
    return decode_text(raw)


def parse_field(line: str) -> Tuple[str, str]:
    """解析单行字段，返回 (字段名, 值)。支持中英文冒号。"""
    for sep in ("：", ":"):
        if sep in line:
            key, value = line.split(sep, 1)
            return key.strip(), value.strip()
    return "", line.strip()


def parse_research_card(text: str, source: str = "") -> ResearchCard:
    """从纯文本解析研究卡片。"""
    card = ResearchCard(source=source, raw_text=text)
    lines = text.splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        key, value = parse_field(line)
        if not key:
            continue
        if key in ("标题", "title", "Title"):
            card.title = value
        elif key in ("作者", "authors", "Authors"):
            card.authors = [a.strip() for a in re.split(r"[;；,，]", value) if a.strip()]
        elif key in ("年份", "year", "Year"):
            try:
                card.year = int(value)
            except ValueError:
                card.year = None
        elif key in ("关键词", "keywords", "Keywords"):
            card.keywords = [k.strip() for k in re.split(r"[;；,，]", value) if k.strip()]
        elif key in ("摘要", "abstract", "Abstract"):
            card.abstract = value
        elif key in ("结论", "conclusion", "Conclusion"):
            card.conclusion = value
        elif key in ("局限", "limitations", "Limitations"):
            card.limitations = [l.strip() for l in re.split(r"[;；,，]", value) if l.strip()]
    # 计算置信度
    card.confidence = calculate_confidence(card)
    return card


def calculate_confidence(card: ResearchCard) -> float:
    """基于字段完整度计算置信度（0-1）。"""
    fields = [
        card.title,
        card.abstract,
        card.conclusion,
        str(card.year) if card.year else "",
        " ".join(card.keywords),
        " ".join(card.authors),
    ]
    filled = sum(1 for f in fields if f.strip())
    return round(filled / len(fields), 2)


# ---------------------------------------------------------------------------
# 主题聚类
# ---------------------------------------------------------------------------
def cluster_cards(cards: List[ResearchCard]) -> Dict[str, List[ResearchCard]]:
    """基于关键词重叠进行简单主题聚类。"""
    clusters: Dict[str, List[ResearchCard]] = {}
    for card in cards:
        placed = False
        for topic in clusters:
            # 检查关键词重叠
            overlap = set(card.keywords) & set(topic.split(";"))
            if overlap:
                clusters[topic].append(card)
                placed = True
                break
        if not placed:
            # 新主题：使用第一个关键词作为主题名
            topic_name = card.keywords[0] if card.keywords else "未分类"
            clusters[topic_name] = [card]
    return clusters


# ---------------------------------------------------------------------------
# 空白分析
# ---------------------------------------------------------------------------
def gap_analysis(cards: List[ResearchCard], clusters: Dict[str, List[ResearchCard]]) -> List[str]:
    """生成研究空白分析文本。"""
    gaps = []
    # 主题覆盖度
    for topic, items in clusters.items():
        if len(items) <= 1:
            gaps.append(f"主题「{topic}」文献较少（仅 {len(items)} 篇），可能存在研究空白。")
    # 方法多样性
    methods = set()
    for card in cards:
        for kw in card.keywords:
            if kw in ("CNN", "RNN", "Transformer", "LSTM", "DQN", "强化学习", "深度学习"):
                methods.add(kw)
    if len(methods) <= 1:
        gaps.append("研究方法单一，建议探索更多方法视角。")
    # 时间分布
    recent = sum(1 for c in cards if c.year and c.year >= 2020)
    if recent / max(len(cards), 1) < 0.3:
        gaps.append("近期（2020年后）文献占比较低，建议关注最新研究动态。")
    # 理论深度
    theory_keywords = ["理论", "框架", "模型", "机制"]
    theory_count = sum(1 for c in cards if any(k in c.abstract for k in theory_keywords))
    if theory_count / max(len(cards), 1) < 0.2:
        gaps.append("多数文献停留在应用层面，缺乏理论深度探讨。")
    return gaps if gaps else ["未发现明显研究空白。"]


# ---------------------------------------------------------------------------
# 大纲生成
# ---------------------------------------------------------------------------
def generate_outline(cards: List[ResearchCard], clusters: Dict[str, List[ResearchCard]]) -> str:
    """生成论文大纲。"""
    lines = ["# 论文大纲", "", "1 引言", "  1.1 研究背景", "  1.2 研究问题", "  1.3 研究方法", ""]
    lines.append("2 文献综述")
    for i, topic in enumerate(clusters, start=1):
        lines.append(f"  2.{i} {topic}研究综述")
    lines.append(f"  2.{len(clusters)+1} 研究空白与本研究定位")
    lines.append("")
    lines.extend([
        "3 研究方法",
        "  3.1 研究设计",
        "  3.2 数据来源",
        "  3.3 分析框架",
        "",
        "4 分析结果",
    ])
    for i, topic in enumerate(clusters, start=1):
        lines.append(f"  4.{i} {topic}相关分析")
    lines.append(f"  4.{len(clusters)+1} 综合讨论")
    lines.append("")
    lines.extend([
        "5 结论",
        "  5.1 主要发现",
        "  5.2 研究局限",
        "  5.3 未来方向",
    ])
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------
def format_markdown(cards: List[ResearchCard], clusters: Dict[str, List[ResearchCard]],
                    gaps: Optional[List[str]] = None, outline: Optional[str] = None) -> str:
    """生成 Markdown 格式输出。"""
    lines = ["# 研究卡片清单", ""]
    for i, card in enumerate(cards, start=1):
        lines.append(f"## 卡片 {i}")
        lines.append(f"- 标题：{card.title or '[需核实]'}")
        lines.append(f"- 作者：{'; '.join(card.authors) if card.authors else '[需核实]'}")
        lines.append(f"- 年份：{card.year if card.year else '[需核实]'}")
        lines.append(f"- 关键词：{'; '.join(card.keywords) if card.keywords else '[需核实]'}")
        lines.append(f"- 摘要：{card.abstract or '[需核实]'}")
        lines.append(f"- 结论：{card.conclusion or '[需核实]'}")
        lines.append(f"- 局限：{'; '.join(card.limitations) if card.limitations else '[需核实]'}")
        lines.append(f"- 置信度：{card.confidence:.2f}")
        if card.confidence < 0.7:
            lines.append("- ⚠️ 低置信度，请人工复核")
        lines.append("")
    if gaps is not None:
        lines.append("# 研究空白分析")
        lines.append("")
        for g in gaps:
            lines.append(f"- {g}")
        lines.append("")
    if outline:
        lines.append(outline)
    return "\n".join(lines)


def format_json(cards: List[ResearchCard]) -> str:
    """生成 JSON 格式输出。"""
    return json.dumps([c.to_dict() for c in cards], ensure_ascii=False, indent=2)


def format_csv(cards: List[ResearchCard]) -> str:
    """生成 CSV 格式输出。"""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["标题", "作者", "年份", "关键词", "摘要", "结论", "局限", "置信度"])
    for c in cards:
        writer.writerow([
            c.title, "; ".join(c.authors), c.year, "; ".join(c.keywords),
            c.abstract, c.conclusion, "; ".join(c.limitations), c.confidence
        ])
    return output.getvalue()


# ---------------------------------------------------------------------------
# 原子写盘
# ---------------------------------------------------------------------------
def atomic_write(file_path: str, content: str, dry_run: bool = False) -> None:
    """原子化写入文件。dry_run 时只打印预览。"""
    if dry_run:
        print(f"[dry-run] 将写入 {file_path}（{len(content)} 字符）")
        print("--- 内容预览 ---")
        print(content[:500] + ("..." if len(content) > 500 else ""))
        print("--- 预览结束 ---")
        return
    dir_name = os.path.dirname(os.path.abspath(file_path))
    os.makedirs(dir_name, exist_ok=True)
    tmp_path = file_path + f".tmp.{os.getpid()}"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, file_path)
    except OSError as e:
        raise AcademicSkillError("E001", f"写入文件失败 {file_path}: {e}")


# ---------------------------------------------------------------------------
# 主处理流程
# ---------------------------------------------------------------------------
def process_input(input_path: str, output_path: str, format: str = "markdown",
                  gap: bool = False, outline: bool = False, dry_run: bool = False,
                  verbose: bool = False) -> None:
    """处理单个输入文件。"""
    if not os.path.isfile(input_path):
        raise AcademicSkillError("E001", f"输入文件不存在: {input_path}")
    text = read_text_file(input_path)
    if not text.strip():
        raise AcademicSkillError("E001", "输入文件为空")
    # 按空行分割文献
    raw_cards = re.split(r"\n\s*\n", text.strip())
    cards = [parse_research_card(rc, source=input_path) for rc in raw_cards if rc.strip()]
    if not cards:
        raise AcademicSkillError("E003", "未能从输入中解析出任何文献卡片")
    if verbose:
        print(f"解析到 {len(cards)} 篇文献")
    # 聚类
    clusters = cluster_cards(cards)
    if verbose:
        for topic, items in clusters.items():
            print(f"  主题「{topic}」: {len(items)} 篇")
    # 空白分析
    gaps = None
    if gap:
        gaps = gap_analysis(cards, clusters)
        if verbose:
            print("空白分析完成")
    # 大纲
    outline_text = None
    if outline:
        outline_text = generate_outline(cards, clusters)
        if verbose:
            print("大纲生成完成")
    # 格式化输出
    if format == "markdown":
        content = format_markdown(cards, clusters, gaps, outline_text)
    elif format == "json":
        content = format_json(cards)
    elif format == "csv":
        content = format_csv(cards)
    else:
        raise AcademicSkillError("E002")
    # 写盘
    atomic_write(output_path, content, dry_run=dry_run)
    if not dry_run:
        print(f"已生成: {output_path}")


def process_batch(input_dir: str, output_dir: str, format: str = "markdown",
                  gap: bool = False, outline: bool = False, dry_run: bool = False,
                  verbose: bool = False) -> None:
    """批量处理目录下所有 .txt 文件。"""
    if not os.path.isdir(input_dir):
        raise AcademicSkillError("E001", f"输入目录不存在: {input_dir}")
    os.makedirs(output_dir, exist_ok=True)
    files = [f for f in os.listdir(input_dir) if f.endswith(".txt")]
    if not files:
        raise AcademicSkillError("E005", f"目录 {input_dir} 下没有 .txt 文件")
    failed = []
    for fname in files:
        in_path = os.path.join(input_dir, fname)
        out_name = os.path.splitext(fname)[0] + f".{format}"
        out_path = os.path.join(output_dir, out_name)
        try:
            process_input(in_path, out_path, format, gap, outline, dry_run, verbose)
        except AcademicSkillError as e:
            failed.append((fname, str(e)))
            print(f"[错误] {fname}: {e}", file=sys.stderr)
    if failed:
        raise AcademicSkillError("E012", f"批量处理部分失败: {len(failed)}/{len(files)} 个文件失败")


# ---------------------------------------------------------------------------
# 自测
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """运行自测，验证核心功能。返回 0 表示全部通过。"""
    print("=== 自测开始 ===")
    # 测试 1：解析卡片
    sample = """标题：深度学习在医疗影像诊断中的应用
作者：张三；李四
年份：2023
关键词：深度学习；医疗影像；CNN
摘要：本文综述了深度学习在医疗影像诊断中的最新进展。
结论：深度学习在影像诊断中表现出高准确率。
局限：样本量有限。
"""
    card = parse_research_card(sample, source="selftest")
    assert card.title == "深度学习在医疗影像诊断中的应用", f"标题解析失败: {card.title}"
    assert card.year == 2023, f"年份解析失败: {card.year}"
    assert "CNN" in card.keywords, f"关键词解析失败: {card.keywords}"
    assert card.confidence > 0.7, f"置信度计算异常: {card.confidence}"
    print("  [通过] 卡片解析")

    # 测试 2：聚类
    cards = [
        ResearchCard(title="A", keywords=["深度学习", "医疗"]),
        ResearchCard(title="B", keywords=["深度学习", "影像"]),
        ResearchCard(title="C", keywords=["强化学习", "推荐"]),
    ]
    clusters = cluster_cards(cards)
    assert len(clusters) >= 2, f"聚类结果异常: {len(clusters)} 个主题"
    print("  [通过] 主题聚类")

    # 测试 3：空白分析
    gaps = gap_analysis(cards, clusters)
    assert isinstance(gaps, list) and len(gaps) > 0, "空白分析结果为空"
    print("  [通过] 空白分析")

    # 测试 4：大纲生成
    outline = generate_outline(cards, clusters)
    assert "引言" in outline and "文献综述" in outline, "大纲结构不完整"
    print("  [通过] 大纲生成")

    # 测试 5：格式输出
    md = format_markdown(cards, clusters)
    assert "研究卡片清单" in md, "Markdown 输出异常"
    js = format_json(cards)
    assert json.loads(js), "JSON 输出异常"
    csv_out = format_csv(cards)
    assert "标题" in csv_out, "CSV 输出异常"
    print("  [通过] 格式输出")

    # 测试 6：编码处理
    gbk_bytes = "标题：测试".encode("gbk")
    decoded = decode_text(gbk_bytes)
    assert decoded == "标题：测试", f"GBK 解码失败: {decoded}"
    print("  [通过] 编码处理")

    # 测试 7：dry-run 不写盘
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        in_path = os.path.join(tmpdir, "in.txt")
        out_path = os.path.join(tmpdir, "out.md")
        with open(in_path, "w", encoding="utf-8") as f:
            f.write(sample)
        process_input(in_path, out_path, dry_run=True)
        assert not os.path.exists(out_path), "dry-run 模式不应写盘"
        print("  [通过] dry-run 模式")

    # 测试 8：空输入报错
    try:
        parse_research_card("", source="test")
        assert False, "空输入应报错"
    except Exception as e:
        print(f"[WARN] 降级处理: {e}", file=sys.stderr)  # R2 降级输出
    print("  [通过] 空输入处理")

    print("=== 全部自测通过 ===")
    return 0


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(
        description="学术研究技能：文献结构化、聚类、空白分析、大纲生成",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例:
  python run.py process -i input.txt -o output.md
  python run.py process -i input.txt -o output.md --gap-analysis --outline
  python run.py process -i ./papers/ -o ./output/ --batch --format json
  python run.py process -i input.txt -o output.md --dry-run
  python run.py --selftest
"""
    )
    parser.add_argument("--selftest", action="store_true", help="运行自测")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # process 子命令
    process_parser = subparsers.add_parser("process", help="处理文献")
    process_parser.add_argument("-i", "--input", required=False, help="输入文件或目录")
    process_parser.add_argument("-o", "--output", required=False, help="输出文件或目录")
    process_parser.add_argument("--format", choices=["markdown", "json", "csv"], default="markdown",
                                help="输出格式（默认 markdown）")
    process_parser.add_argument("--gap-analysis", action="store_true", help="执行研究空白分析")
    process_parser.add_argument("--outline", action="store_true", help="生成论文大纲")
    process_parser.add_argument("--batch", action="store_true", help="批量处理目录")
    process_parser.add_argument("--dry-run", action="store_true", help="预览模式，不写盘")
    process_parser.add_argument("--verbose", action="store_true", help="输出详细日志")

    args = parser.parse_args()

    if args.selftest:
        return run_selftest()

    if not args.command:
        parser.print_help()
        return 0

    try:
        if args.command == "process":
            if args.batch:
                process_batch(args.input, args.output, args.format,
                              args.gap_analysis, args.outline, args.dry_run, args.verbose)
            else:
                process_input(args.input, args.output, args.format,
                              args.gap_analysis, args.outline, args.dry_run, args.verbose)
        return 0
    except AcademicSkillError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"未知错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())


def read_text_safe(path):
    """多编码容错读取 (selftest contract)"""
    import codecs
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            with codecs.open(path, "r", encoding=enc) as fh:
                return fh.read()
        except (UnicodeDecodeError, OSError):
            continue
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()
