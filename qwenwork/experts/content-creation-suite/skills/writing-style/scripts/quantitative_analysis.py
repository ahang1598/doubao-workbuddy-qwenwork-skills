#!/usr/bin/env python3
"""Quantitative style analysis for writing style extraction.

Computes sentence-level and paragraph-level statistics from plain text,
outputting a JSON object for downstream style profiling.

Metrics:
  - avg_sentence_length: mean sentence length in characters
  - sentence_length_std: standard deviation (rhythm fingerprint)
  - type_token_ratio: vocabulary richness (0-1)
  - avg_paragraph_length: mean paragraph length in sentences
  - paragraph_count: total paragraphs

Usage:
  python quantitative_analysis.py --input <text_file>
  echo "一段文字" | python quantitative_analysis.py --stdin
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys

from logic_analyzer import analyze_logic_density
from emotion_mapper import analyze_emotion_arc
from platform_scorer import calculate_platform_fit
from rhetoric_detector import detect_rhetoric


def _split_sentences(text: str) -> list[str]:
    """Split Chinese/mixed text into sentences.

    Handles Chinese punctuation (。！？；) and Western punctuation (.!?;).
    Preserves sentence content, filters empty results.
    """
    # Split on sentence-ending punctuation, keeping the delimiter
    parts = re.split(r'([。！？；!?;…]+)', text)
    sentences: list[str] = []
    i = 0
    while i < len(parts):
        seg = parts[i].strip()
        # Attach trailing punctuation to the preceding segment
        if i + 1 < len(parts):
            seg += parts[i + 1].strip()
            i += 2
        else:
            i += 1
        # Filter out very short fragments (< 4 chars) as noise
        if len(seg) >= 4:
            sentences.append(seg)
    return sentences


def _split_paragraphs(text: str) -> list[str]:
    """Split text into paragraphs by blank lines or newlines."""
    paragraphs = re.split(r'\n\s*\n|\n', text)
    return [p.strip() for p in paragraphs if p.strip()]


def _tokenize_chinese(text: str) -> list[str]:
    """Simple character-level + word-level tokenization for TTR.

    For Chinese text, each character is a token (since we don't have jieba).
    For mixed text, English words are kept as tokens.
    """
    tokens: list[str] = []
    # Extract English words
    english_words = re.findall(r'[a-zA-Z]+', text)
    tokens.extend(w.lower() for w in english_words)
    # Extract Chinese characters (CJK Unified Ideographs)
    chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
    tokens.extend(chinese_chars)
    return tokens


def analyze(text: str) -> dict:
    """Run quantitative analysis on plain text, return metrics dict."""
    paragraphs = _split_paragraphs(text)
    all_sentences: list[str] = []
    para_sentence_counts: list[int] = []

    for para in paragraphs:
        sents = _split_sentences(para)
        all_sentences.extend(sents)
        para_sentence_counts.append(len(sents) if sents else 1)

    # Sentence length statistics
    if all_sentences:
        lengths = [len(s) for s in all_sentences]
        avg_len = sum(lengths) / len(lengths)
        variance = sum((l - avg_len) ** 2 for l in lengths) / len(lengths)
        std_len = math.sqrt(variance)
    else:
        avg_len = 0.0
        std_len = 0.0

    # Type-Token Ratio (vocabulary richness)
    tokens = _tokenize_chinese(text)
    if tokens:
        ttr = len(set(tokens)) / len(tokens)
    else:
        ttr = 0.0

    # Paragraph statistics
    para_count = len(paragraphs)
    if para_sentence_counts:
        avg_para_len = sum(para_sentence_counts) / len(para_sentence_counts)
    else:
        avg_para_len = 0.0

    result = {
        "basic_stats": {
            "avg_sentence_length": round(avg_len, 1),
            "sentence_length_std": round(std_len, 1),
            "type_token_ratio": round(ttr, 3),
            "avg_paragraph_length": round(avg_para_len, 1),
            "paragraph_count": para_count,
            "total_sentences": len(all_sentences),
            "total_tokens": len(tokens),
        },
        "cognitive_logic": analyze_logic_density(text),
        "emotional_arc": analyze_emotion_arc(text),
        "platform_fit": calculate_platform_fit(text),
        "rhetoric_anchors": detect_rhetoric(text)
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Quantitative writing style analysis"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--input", help="Path to plain text file")
    group.add_argument(
        "--stdin", action="store_true",
        help="Read text from stdin"
    )
    args = parser.parse_args()

    if args.stdin:
        text = sys.stdin.read()
    else:
        # Resolve input path to absolute for robustness
        input_path = os.path.abspath(args.input)
        with open(input_path, "r", encoding="utf-8") as f:
            text = f.read()

    if not text.strip():
        print(json.dumps({"error": "Empty input"}, ensure_ascii=False))
        sys.exit(2)

    result = analyze(text)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
