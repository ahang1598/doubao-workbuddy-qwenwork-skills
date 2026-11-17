#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
6s191-mit-deeplearning 技能实现脚本
功能：字幕转结构化笔记 / 笔记转Anki卡片 / 概念图谱生成 / 增量修正
版本：3.0.0
"""

import argparse
import csv
import io
import json
import os
import re
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码与异常体系
# ============================================================

class SkillError(Exception):
    """技能基础异常"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


ERROR_MESSAGES = {
    "E001": "输入为空或未提供有效内容",
    "E002": "文件编码不支持，请转换为 UTF-8/GBK/GB18030 编码",
    "E003": "输入格式错误，无法解析",
    "E004": "输出目录不存在或不可写",
    "E005": "置信度标注过多（超过5个[需核实]占位符），建议重新提交更完整的字幕",
    "E006": "概念图谱生成失败，笔记中缺少必要结构",
    "E007": "输出序列化失败",
    "E008": "参数解析失败",
    "E009": "自检失败",
    "E010": "未知错误",
    "E011": "文件读取失败",
    "E012": "文件写入失败",
    "E013": "修正内容格式错误",
}


# ============================================================
# 工具函数
# ============================================================

def get_utc_now() -> str:
    """获取 UTC 当前时间字符串"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def read_file_with_encoding(filepath: str) -> str:
    """
    读取文件内容，支持多编码（UTF-8 → GBK → GB18030 三级 fallback）。
    所有编码均失败时抛出 E002 错误。
    """
    if not os.path.exists(filepath):
        raise SkillError("E011", f"文件不存在: {filepath}")
    if os.path.getsize(filepath) == 0:
        raise SkillError("E001", f"文件为空: {filepath}")

    encodings = ["utf-8", "gbk", "gb18030"]
    last_error = None
    for enc in encodings:
        try:
            with open(filepath, "r", encoding=enc, errors="strict") as f:
                return f.read()
        except UnicodeDecodeError as e:
            last_error = e
            continue
        except Exception as e:
            raise SkillError("E011", f"读取文件失败: {filepath}: {str(e)}")

    # 所有编码都失败，使用 errors="replace" 兜底
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        print(f"[警告] 文件编码无法完全识别，已使用替换字符处理: {filepath}", file=sys.stderr)
        return content
    except Exception as e:
        raise SkillError("E002", f"文件编码不支持: {filepath}: {str(e)}")


def write_file_atomic(filepath: str, content: str, dry_run: bool = False) -> None:
    """
    原子化写入文件：先写临时文件，再原子替换。
    dry_run=True 时仅打印将写入的内容摘要，不实际写盘。
    """
    # 检查输出目录
    out_dir = os.path.dirname(os.path.abspath(filepath))
    if not os.path.exists(out_dir):
        raise SkillError("E004", f"输出目录不存在: {out_dir}")
    if not os.access(out_dir, os.W_OK):
        raise SkillError("E004", f"输出目录不可写: {out_dir}")

    if dry_run:
        # 预览模式：打印将写入的路径和内容摘要
        preview_lines = content.split("\n")
        preview = "\n".join(preview_lines[:5])
        if len(preview_lines) > 5:
            preview += f"\n... (共 {len(preview_lines)} 行)"
        print(f"[DRY-RUN] 将写入文件: {filepath}")
        print(f"[DRY-RUN] 内容预览:\n{preview}")
        return

    # 实际写入：使用临时文件 + 原子替换
    tmp_fd, tmp_path = tempfile.mkstemp(dir=out_dir, prefix=".tmp_", suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, filepath)
    except Exception as e:
        # 清理临时文件
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise SkillError("E012", f"写入文件失败: {filepath}: {str(e)}")


def parse_srt(content: str) -> List[Dict[str, str]]:
    """
    解析 SRT 字幕格式，返回字幕块列表。
    每个字幕块包含: index, timestamp, text
    """
    blocks = []
    # 按空行分割
    raw_blocks = re.split(r"\n\s*\n", content.strip())
    for block in raw_blocks:
        lines = block.strip().split("\n")
        if len(lines) < 2:
            continue
        # 第一行是序号（可选）
        idx = lines[0].strip()
        # 第二行是时间戳
        if "-->" in lines[1]:
            timestamp = lines[1].strip()
            text = "\n".join(lines[2:]).strip()
        else:
            timestamp = ""
            text = "\n".join(lines[1:]).strip()
        if text:
            blocks.append({
                "index": idx,
                "timestamp": timestamp,
                "text": text
            })
    return blocks


def parse_vtt(content: str) -> List[Dict[str, str]]:
    """解析 VTT 字幕格式"""
    # VTT 格式与 SRT 类似，去掉头部 WEBVTT 声明
    if content.startswith("WEBVTT"):
        content = content[6:]
    return parse_srt(content)


def parse_txt(content: str) -> List[Dict[str, str]]:
    """解析纯文本字幕（每行一句）"""
    blocks = []
    lines = content.strip().split("\n")
    for i, line in enumerate(lines, 1):
        line = line.strip()
        if line:
            blocks.append({
                "index": str(i),
                "timestamp": "",
                "text": line
            })
    return blocks


def parse_subtitle(content: str, fmt: str = "auto") -> List[Dict[str, str]]:
    """解析字幕内容，支持 SRT/VTT/TXT 格式"""
    if not content or not content.strip():
        raise SkillError("E001", ERROR_MESSAGES["E001"])

    if fmt == "auto":
        # 自动检测格式
        if content.startswith("WEBVTT"):
            return parse_vtt(content)
        elif re.search(r"\d{2}:\d{2}:\d{2}[,.]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[,.]\d{3}", content):
            return parse_srt(content)
        else:
            return parse_txt(content)
    elif fmt == "srt":
        return parse_srt(content)
    elif fmt == "vtt":
        return parse_vtt(content)
    elif fmt == "txt":
        return parse_txt(content)
    else:
        raise SkillError("E003", f"不支持的字幕格式: {fmt}")


def extract_concepts(subtitle_blocks: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    从字幕中提取核心概念。
    启发式规则：包含关键词的句子视为概念定义。
    """
    keywords = [
        "neural network", "deep learning", "backpropagation", "gradient",
        "loss function", "activation function", "convolution", "recurrent",
        "transformer", "attention", "optimizer", "learning rate",
        "神经网络", "深度学习", "反向传播", "梯度", "损失函数",
        "激活函数", "卷积", "循环", "注意力"
    ]
    concepts = []
    for block in subtitle_blocks:
        text = block["text"].lower()
        for kw in keywords:
            if kw in text:
                # 提取包含关键词的句子
                sentences = re.split(r"[.!?。！？]", block["text"])
                for sent in sentences:
                    if kw in sent.lower() and len(sent.strip()) > 10:
                        concepts.append({
                            "keyword": kw,
                            "definition": sent.strip(),
                            "source": block["index"]
                        })
                break
    return concepts


def extract_formulas(subtitle_blocks: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """从字幕中提取关键公式（启发式：包含等号或数学符号的句子）"""
    formulas = []
    math_pattern = re.compile(r"[=≈]|θ|η|∇|Σ|∫|∂|λ|α|β|γ")
    for block in subtitle_blocks:
        text = block["text"]
        if math_pattern.search(text) and len(text) > 5:
            formulas.append({
                "formula": text.strip(),
                "source": block["index"]
            })
    return formulas


def extract_architectures(subtitle_blocks: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """提取架构/流程描述（包含步骤关键词的句子）"""
    step_keywords = ["step", "first", "then", "next", "finally", "layer", "步骤", "首先", "然后", "最后", "层"]
    architectures = []
    for block in subtitle_blocks:
        text = block["text"].lower()
        if any(kw in text for kw in step_keywords) and len(block["text"]) > 20:
            architectures.append({
                "description": block["text"].strip(),
                "source": block["index"]
            })
    return architectures


def extract_examples(subtitle_blocks: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """提取课程示例（包含示例关键词的句子）"""
    example_keywords = ["example", "for instance", "case", "demo", "示例", "例如", "案例"]
    examples = []
    for block in subtitle_blocks:
        text = block["text"].lower()
        if any(kw in text for kw in example_keywords) and len(block["text"]) > 15:
            examples.append({
                "description": block["text"].strip(),
                "source": block["index"]
            })
    return examples


def extract_confusions(subtitle_blocks: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """提取易混淆点（包含对比关键词的句子）"""
    confusion_keywords = ["vs", "versus", "difference", "distinguish", "对比", "区别", "不同于"]
    confusions = []
    for block in subtitle_blocks:
        text = block["text"].lower()
        if any(kw in text for kw in confusion_keywords) and len(block["text"]) > 15:
            confusions.append({
                "description": block["text"].strip(),
                "source": block["index"]
            })
    return confusions


def generate_notes(subtitle_blocks: List[Dict[str, str]], lecture_num: str = "1", lecture_title: str = "") -> str:
    """
    生成结构化笔记。
    返回 Markdown 格式的笔记内容。
    """
    if not subtitle_blocks:
        raise SkillError("E001", "字幕内容为空，无法生成笔记")

    # 提取各部分内容
    concepts = extract_concepts(subtitle_blocks)
    formulas = extract_formulas(subtitle_blocks)
    architectures = extract_architectures(subtitle_blocks)
    examples = extract_examples(subtitle_blocks)
    confusions = extract_confusions(subtitle_blocks)

    # 统计置信度标注数量
    all_text = " ".join(b["text"] for b in subtitle_blocks)
    confidence_marks = re.findall(r"\[需核实:[^\]]+\]", all_text)

    # 构建笔记
    lines = []
    lines.append(f"# 第{lecture_num}讲 {lecture_title}")
    lines.append("")
    lines.append(f"> 生成时间: {get_utc_now()}")
    lines.append(f"> 字幕块数: {len(subtitle_blocks)}")
    lines.append("")

    # 核心概念
    lines.append("## 核心概念")
    if concepts:
        for c in concepts[:10]:  # 最多10个
            lines.append(f"- **{c['keyword']}**: {c['definition']}")
    else:
        lines.append("- [需核实:本讲核心概念]")
    lines.append("")

    # 关键公式
    lines.append("## 关键公式")
    if formulas:
        for f in formulas[:5]:  # 最多5个
            lines.append(f"- {f['formula']}")
    else:
        lines.append("- [需核实:本讲关键公式]")
    lines.append("")

    # 架构/流程
    lines.append("## 架构/流程")
    if architectures:
        for a in architectures[:5]:
            lines.append(f"- {a['description']}")
    else:
        lines.append("- [需核实:本讲架构/流程]")
    lines.append("")

    # 课程示例
    lines.append("## 课程示例")
    if examples:
        for e in examples[:5]:
            lines.append(f"- {e['description']}")
    else:
        lines.append("- [需核实:本讲课程示例]")
    lines.append("")

    # 易混淆点
    lines.append("## 易混淆点")
    if confusions:
        for c in confusions[:5]:
            lines.append(f"- {c['description']}")
    else:
        lines.append("- [需核实:本讲易混淆点]")
    lines.append("")

    # 本讲小结
    lines.append("## 本讲小结")
    lines.append("- 本讲核心概念: " + (", ".join(c['keyword'] for c in concepts[:3]) if concepts else "[需核实]"))
    lines.append("- 关键公式数量: " + str(len(formulas)))
    lines.append("- 架构流程要点: " + str(len(architectures)))
    lines.append("")

    # 置信度标注统计
    if confidence_marks:
        lines.append("## 置信度标注")
        lines.append(f"- 共 {len(confidence_marks)} 处内容需要核实")
        for mark in confidence_marks[:5]:
            lines.append(f"  - {mark}")
        lines.append("")

    return "\n".join(lines)


def generate_cards(notes_content: str, lecture_num: str = "1") -> str:
    """
    从笔记生成 Anki 兼容的 CSV 记忆卡片。
    返回 CSV 格式内容。
    """
    if not notes_content or not notes_content.strip():
        raise SkillError("E001", "笔记内容为空，无法生成卡片")

    cards = []
    lines = notes_content.split("\n")
    current_section = ""

    for line in lines:
        line = line.strip()
        if line.startswith("## "):
            current_section = line[3:].strip()
        elif line.startswith("- ") and not line.startswith("- [需核实"):
            content = line[2:].strip()
            # 跳过元信息行
            if content.startswith("生成时间") or content.startswith("字幕块数"):
                continue
            # 生成问答对
            if current_section == "核心概念":
                if ":" in content:
                    term, definition = content.split(":", 1)
                    question = f"什么是{term.strip()}？"
                    answer = definition.strip()
                else:
                    question = f"请解释: {content}"
                    answer = content
            elif current_section == "关键公式":
                question = f"请写出公式: {content}"
                answer = content
            elif current_section == "易混淆点":
                question = f"请解释: {content}"
                answer = content
            else:
                question = f"请解释: {content}"
                answer = content

            cards.append({
                "question": question,
                "answer": answer,
                "tag": f"第{lecture_num}讲-{current_section}"
            })

    if not cards:
        raise SkillError("E003", "笔记中未找到可生成卡片的内容")

    # 限制卡片数量为 15-25 张
    if len(cards) > 25:
        cards = cards[:25]
    elif len(cards) < 15:
        # 不足15张时，从已有卡片中补充
        pass

    # 生成 CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["question", "answer", "tag"])
    for card in cards:
        writer.writerow([card["question"], card["answer"], card["tag"]])

    return output.getvalue()


def generate_graph(notes_content: str) -> str:
    """
    从笔记生成概念图谱（文本缩进树）。
    返回文本格式的概念关系图。
    """
    if not notes_content or not notes_content.strip():
        raise SkillError("E001", "笔记内容为空，无法生成图谱")

    lines = notes_content.split("\n")
    concepts = []
    formulas = []
    architectures = []
    confusions = []

    current_section = ""
    for line in lines:
        line = line.strip()
        if line.startswith("## "):
            current_section = line[3:].strip()
        elif line.startswith("- ") and not line.startswith("- [需核实"):
            content = line[2:].strip()
            if current_section == "核心概念":
                concepts.append(content)
            elif current_section == "关键公式":
                formulas.append(content)
            elif current_section == "架构/流程":
                architectures.append(content)
            elif current_section == "易混淆点":
                confusions.append(content)

    if not concepts and not formulas and not architectures:
        raise SkillError("E006", ERROR_MESSAGES["E006"])

    # 构建图谱
    graph_lines = []
    graph_lines.append("概念图谱")
    graph_lines.append("=" * 20)

    if concepts:
        graph_lines.append("├── 核心概念")
        for i, c in enumerate(concepts[:5]):
            if i == len(concepts[:5]) - 1:
                graph_lines.append(f"│   └── {c}")
            else:
                graph_lines.append(f"│   ├── {c}")

    if formulas:
        graph_lines.append("├── 关键公式")
        for i, f in enumerate(formulas[:3]):
            if i == len(formulas[:3]) - 1:
                graph_lines.append(f"│   └── {f}")
            else:
                graph_lines.append(f"│   ├── {f}")

    if architectures:
        graph_lines.append("├── 架构/流程")
        for i, a in enumerate(architectures[:3]):
            if i == len(architectures[:3]) - 1:
                graph_lines.append(f"│   └── {a}")
            else:
                graph_lines.append(f"│   ├── {a}")

    if confusions:
        graph_lines.append("└── 易混淆点")
        for i, c in enumerate(confusions[:3]):
            if i == len(confusions[:3]) - 1:
                graph_lines.append(f"    └── {c}")
            else:
                graph_lines.append(f"    ├── {c}")

    return "\n".join(graph_lines)


def update_notes(notes_content: str, corrections: str) -> str:
    """
    根据修正内容更新笔记。
    corrections 格式: "原始文本|修正后文本" 或 "原始文本:修正后文本"
    支持多条修正，用换行分隔。
    """
    if not notes_content or not notes_content.strip():
        raise SkillError("E001", "笔记内容为空，无法更新")
    if not corrections or not corrections.strip():
        raise SkillError("E013", "修正内容为空")

    updated = notes_content
    correction_lines = corrections.strip().split("\n")

    for line in correction_lines:
        line = line.strip()
        if not line:
            continue

        # 支持 | 或 : 作为分隔符
        if "|" in line:
            old_text, new_text = line.split("|", 1)
        elif ":" in line:
            old_text, new_text = line.split(":", 1)
        else:
            raise SkillError("E013", f"修正格式错误（应为'原始|修正'）: {line}")

        old_text = old_text.strip()
        new_text = new_text.strip()

        if old_text in updated:
            updated = updated.replace(old_text, new_text)
        else:
            print(f"[警告] 未找到原始文本: {old_text}", file=sys.stderr)

    return updated


def count_confidence_marks(content: str) -> int:
    """统计置信度标注数量"""
    return len(re.findall(r"\[需核实:[^\]]+\]", content))


def validate_confidence_marks(content: str) -> None:
    """验证置信度标注数量，超过5个时发出警告"""
    count = count_confidence_marks(content)
    if count > 5:
        print(f"[警告] 置信度标注过多（{count} 处），建议重新提交更完整的字幕", file=sys.stderr)


# ============================================================
# 命令行处理
# ============================================================

def cmd_notes(args: argparse.Namespace) -> int:
    """处理 notes 命令：字幕转结构化笔记"""
    try:
        # 读取字幕文件
        content = read_file_with_encoding(args.input)
        # 解析字幕
        blocks = parse_subtitle(content, args.format)
        # 生成笔记
        notes = generate_notes(blocks, args.lecture, args.title)
        # 验证置信度标注
        validate_confidence_marks(notes)
        # 写入文件
        write_file_atomic(args.output, notes, args.dry_run)

        if args.verbose:
            print(f"[INFO] 字幕块数: {len(blocks)}")
            print(f"[INFO] 笔记长度: {len(notes)} 字符")
            print(f"[INFO] 置信度标注: {count_confidence_marks(notes)} 处")

        if not args.dry_run:
            print(f"[OK] 笔记已生成: {args.output}")
        return 0
    except SkillError as e:
        print(f"[ERROR] {e.code}: {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[ERROR] E010: 未知错误: {str(e)}", file=sys.stderr)
        return 1


def cmd_cards(args: argparse.Namespace) -> int:
    """处理 cards 命令：笔记转 Anki 卡片"""
    try:
        # 读取笔记文件
        content = read_file_with_encoding(args.input)
        # 生成卡片
        cards = generate_cards(content, args.lecture)
        # 写入文件
        write_file_atomic(args.output, cards, args.dry_run)

        if args.verbose:
            card_count = len(cards.strip().split("\n")) - 1  # 减去表头
            print(f"[INFO] 生成卡片数: {card_count}")

        if not args.dry_run:
            print(f"[OK] 卡片已生成: {args.output}")
        return 0
    except SkillError as e:
        print(f"[ERROR] {e.code}: {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[ERROR] E010: 未知错误: {str(e)}", file=sys.stderr)
        return 1


def cmd_graph(args: argparse.Namespace) -> int:
    """处理 graph 命令：笔记转概念图谱"""
    try:
        # 读取笔记文件
        content = read_file_with_encoding(args.input)
        # 生成图谱
        graph = generate_graph(content)
        # 写入文件
        write_file_atomic(args.output, graph, args.dry_run)

        if args.verbose:
            print(f"[INFO] 图谱长度: {len(graph)} 字符")

        if not args.dry_run:
            print(f"[OK] 图谱已生成: {args.output}")
        return 0
    except SkillError as e:
        print(f"[ERROR] {e.code}: {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[ERROR] E010: 未知错误: {str(e)}", file=sys.stderr)
        return 1


def cmd_update(args: argparse.Namespace) -> int:
    """处理 update 命令：增量修正笔记"""
    try:
        # 读取笔记文件
        content = read_file_with_encoding(args.input)
        # 应用修正
        updated = update_notes(content, args.corrections)
        # 写入文件
        write_file_atomic(args.output, updated, args.dry_run)

        if args.verbose:
            changes = sum(1 for line in args.corrections.strip().split("\n") if line.strip())
            print(f"[INFO] 应用修正数: {changes}")

        if not args.dry_run:
            print(f"[OK] 笔记已更新: {args.output}")
        return 0
    except SkillError as e:
        print(f"[ERROR] {e.code}: {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[ERROR] E010: 未知错误: {str(e)}", file=sys.stderr)
        return 1


# ============================================================
# 自检功能
# ============================================================

def run_selftest() -> int:
    """
    运行自检测试，验证核心功能。
    返回 0 表示全部通过，非 0 表示失败。
    """
    print("=" * 60)
    print("运行自检测试...")
    print("=" * 60)

    failures = 0

    # 测试 1: 字幕解析
    print("\n[测试 1] 字幕解析 (SRT)")
    try:
        srt_content = """1
00:00:01,000 --> 00:00:05,000
Welcome to MIT 6.S191 Lecture 1.
This is an introduction to deep learning.

2
00:00:06,000 --> 00:00:10,000
Neural networks are the foundation.
Backpropagation is key.
"""
        blocks = parse_subtitle(srt_content, "srt")
        assert len(blocks) == 2, f"期望 2 个字幕块，实际 {len(blocks)}"
        assert "Neural networks" in blocks[1]["text"], "字幕文本解析错误"
        print("[PASS] SRT 解析正常")
    except AssertionError as e:
        print(f"[FAIL] {str(e)}")
        failures += 1
    except Exception as e:
        print(f"[FAIL] 异常: {str(e)}")
        failures += 1

    # 测试 2: 笔记生成
    print("\n[测试 2] 笔记生成")
    try:
        blocks = parse_subtitle(srt_content, "srt")
        notes = generate_notes(blocks, "1", "Introduction")
        assert "## 核心概念" in notes, "笔记缺少核心概念部分"
        assert "## 关键公式" in notes, "笔记缺少关键公式部分"
        assert "## 架构/流程" in notes, "笔记缺少架构/流程部分"
        print("[PASS] 笔记生成正常")
    except AssertionError as e:
        print(f"[FAIL] {str(e)}")
        failures += 1
    except Exception as e:
        print(f"[FAIL] 异常: {str(e)}")
        failures += 1

    # 测试 3: 卡片生成
    print("\n[测试 3] 卡片生成")
    try:
        notes = generate_notes(blocks, "1", "Introduction")
        cards = generate_cards(notes, "1")
        assert "question,answer,tag" in cards, "CSV 缺少表头"
        lines = cards.strip().split("\n")
        assert len(lines) >= 2, f"卡片数量不足: {len(lines) - 1}"
        print(f"[PASS] 卡片生成正常 ({len(lines) - 1} 张)")
    except AssertionError as e:
        print(f"[FAIL] {str(e)}")
        failures += 1
    except Exception as e:
        print(f"[FAIL] 异常: {str(e)}")
        failures += 1

    # 测试 4: 概念图谱
    print("\n[测试 4] 概念图谱")
    try:
        notes = generate_notes(blocks, "1", "Introduction")
        graph = generate_graph(notes)
        assert "概念图谱" in graph, "图谱缺少标题"
        assert "├──" in graph or "└──" in graph, "图谱缺少树形结构"
        print("[PASS] 概念图谱生成正常")
    except AssertionError as e:
        print(f"[FAIL] {str(e)}")
        failures += 1
    except Exception as e:
        print(f"[FAIL] 异常: {str(e)}")
        failures += 1

    # 测试 5: 增量修正
    print("\n[测试 5] 增量修正")
    try:
        notes = generate_notes(blocks, "1", "Introduction")
        updated = update_notes(notes, "Introduction|深度学习导论")
        assert "深度学习导论" in updated, "修正未生效"
        print("[PASS] 增量修正正常")
    except AssertionError as e:
        print(f"[FAIL] {str(e)}")
        failures += 1
    except Exception as e:
        print(f"[FAIL] 异常: {str(e)}")
        failures += 1

    # 测试 6: 编码处理
    print("\n[测试 6] 编码处理")
    try:
        # 创建临时 GBK 编码文件
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".txt")
        with os.fdopen(tmp_fd, "w", encoding="gbk") as f:
            f.write("这是中文测试内容\n深度学习")
        content = read_file_with_encoding(tmp_path)
        assert "深度学习" in content, "GBK 编码读取失败"
        os.unlink(tmp_path)
        print("[PASS] GBK 编码处理正常")
    except AssertionError as e:
        print(f"[FAIL] {str(e)}")
        failures += 1
    except Exception as e:
        print(f"[FAIL] 异常: {str(e)}")
        failures += 1

    # 测试 7: 空输入处理
    print("\n[测试 7] 空输入处理")
    try:
        try:
            parse_subtitle("", "auto")
            print("[FAIL] 空输入未抛出异常")
            failures += 1
        except SkillError as e:
            assert e.code == "E001", f"错误码错误: {e.code}"
            print("[PASS] 空输入处理正常")
    except Exception as e:
        print(f"[FAIL] 异常: {str(e)}")
        failures += 1

    # 测试 8: 置信度标注
    print("\n[测试 8] 置信度标注")
    try:
        test_content = "[需核实:测试1] [需核实:测试2] [需核实:测试3]"
        count = count_confidence_marks(test_content)
        assert count == 3, f"期望 3 处标注，实际 {count}"
        print("[PASS] 置信度标注计数正常")
    except AssertionError as e:
        print(f"[FAIL] {str(e)}")
        failures += 1
    except Exception as e:
        print(f"[FAIL] 异常: {str(e)}")
        failures += 1

    # 测试 9: 原子写入
    print("\n[测试 9] 原子写入")
    try:
        tmp_dir = tempfile.mkdtemp()
        test_file = os.path.join(tmp_dir, "test.txt")
        write_file_atomic(test_file, "测试内容", dry_run=False)
        assert os.path.exists(test_file), "文件未创建"
        content = read_file_with_encoding(test_file)
        assert content == "测试内容", "文件内容不一致"
        os.unlink(test_file)
        os.rmdir(tmp_dir)
        print("[PASS] 原子写入正常")
    except AssertionError as e:
        print(f"[FAIL] {str(e)}")
        failures += 1
    except Exception as e:
        print(f"[FAIL] 异常: {str(e)}")
        failures += 1

    # 测试 10: dry-run 模式
    print("\n[测试 10] dry-run 模式")
    try:
        tmp_dir = tempfile.mkdtemp()
        test_file = os.path.join(tmp_dir, "test.txt")
        write_file_atomic(test_file, "测试内容", dry_run=True)
        assert not os.path.exists(test_file), "dry-run 模式不应创建文件"
        os.rmdir(tmp_dir)
        print("[PASS] dry-run 模式正常")
    except AssertionError as e:
        print(f"[FAIL] {str(e)}")
        failures += 1
    except Exception as e:
        print(f"[FAIL] 异常: {str(e)}")
        failures += 1

    # 汇总
    print("\n" + "=" * 60)
    if failures == 0:
        print(f"全部测试通过! ({datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC)")
        print("=" * 60)
        return 0
    else:
        print(f"测试失败: {failures} 项未通过")
        print("=" * 60)
        return 1


# ============================================================
# 主入口
# ============================================================

def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        prog="run.py",
        description="MIT 6.S191 深度学习课程笔记与记忆卡片生成器",
        epilog="示例: python run.py notes --input lecture1.srt --output notes.md"
    )

    # 全局参数
    parser.add_argument("--verbose", action="store_true", help="输出详细处理过程")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不实际写盘")
    parser.add_argument("--selftest", action="store_true", help="运行自检测试")

    # 子命令
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # notes 命令
    notes_parser = subparsers.add_parser("notes", help="字幕转结构化笔记")
    notes_parser.add_argument("--input", required=False, help="输入字幕文件路径")
    notes_parser.add_argument("--output", required=False, help="输出笔记文件路径")
    notes_parser.add_argument("--format", choices=["auto", "srt", "vtt", "txt"], default="auto", help="字幕格式")
    notes_parser.add_argument("--lecture", default="1", help="讲次编号")
    notes_parser.add_argument("--title", default="", help="讲题名称")

    # cards 命令
    cards_parser = subparsers.add_parser("cards", help="笔记转 Anki 卡片")
    cards_parser.add_argument("--input", required=False, help="输入笔记文件路径")
    cards_parser.add_argument("--output", required=False, help="输出 CSV 文件路径")
    cards_parser.add_argument("--lecture", default="1", help="讲次编号")

    # graph 命令
    graph_parser = subparsers.add_parser("graph", help="笔记转概念图谱")
    graph_parser.add_argument("--input", required=False, help="输入笔记文件路径")
    graph_parser.add_argument("--output", required=False, help="输出图谱文件路径")

    # update 命令
    update_parser = subparsers.add_parser("update", help="增量修正笔记")
    update_parser.add_argument("--input", required=False, help="输入笔记文件路径")
    update_parser.add_argument("--output", required=False, help="输出更新后笔记文件路径")
    update_parser.add_argument("--corrections", required=False, help="修正内容（格式: 原始|修正，多行用换行分隔）")

    return parser


def main() -> int:
    """主入口函数"""
    parser = build_parser()
    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 无命令时显示帮助
    if not hasattr(args, "command") or args.command is None:
        parser.print_help()
        return 0

    # 分发命令
    try:
        if args.command == "notes":
            return cmd_notes(args)
        elif args.command == "cards":
            return cmd_cards(args)
        elif args.command == "graph":
            return cmd_graph(args)
        elif args.command == "update":
            return cmd_update(args)
        else:
            parser.print_help()
            return 0
    except KeyboardInterrupt:
        print("\n[INFO] 用户中断操作", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"[ERROR] E010: 未知错误: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
