#!/usr/bin/env python3
"""
批量运行 Skill 2 prepare（粗筛）。
为所有缺失的 (银行 × 年份) 组合运行 prepare_text_extraction.py。
"""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
from typing import List, Tuple

# 脚本目录
_SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))
try:
    import paths as _PATHS  # type: ignore
except ImportError:
    _repo_scripts = _SCRIPT_DIR.parent.parent.parent / "scripts"
    if _repo_scripts.is_dir() and str(_repo_scripts) not in sys.path:
        sys.path.insert(0, str(_repo_scripts))
    import paths as _PATHS  # type: ignore

DATA_DIR = _PATHS.DATA_DIR
WORK_DIR = _PATHS.WORK_DIR
EXTRACTED_TEXT_DIR = _PATHS.EXTRACTED_TEXT_DIR

# prepare_text_extraction.py 路径（本 Skill 自带；兜底跨包到 standard-data-extraction）
PREPARE_SCRIPT = (
    _SCRIPT_DIR / "prepare_text_extraction.py"
    if (_SCRIPT_DIR / "prepare_text_extraction.py").exists()
    else _SCRIPT_DIR.parent.parent / "standard-data-extraction" / "scripts" / "prepare_text_extraction.py"
)

# text_extractor_prompt.md 路径（本 Skill 自带；兜底跨包到 standard-data-extraction）
PROMPT_TEMPLATE = (
    _SCRIPT_DIR / "text_extractor_prompt.md"
    if (_SCRIPT_DIR / "text_extractor_prompt.md").exists()
    else _SCRIPT_DIR.parent.parent / "standard-data-extraction" / "scripts" / "text_extractor_prompt.md"
)

# 所有需要处理的 (银行全称, 中文简称, 旧英文键名, 年份) 列表
TASKS: List[Tuple[str, str, str, str]] = [
    ("招商银行", "招商", "cmb", "2021"),
    ("招商银行", "招商", "cmb", "2022"),
    ("招商银行", "招商", "cmb", "2024"),
    ("兴业银行", "兴业", "cib", "2021"),
    ("兴业银行", "兴业", "cib", "2022"),
    ("兴业银行", "兴业", "cib", "2023"),
    ("兴业银行", "兴业", "cib", "2024"),
    ("光大银行", "光大", "guangda", "2021"),
    ("光大银行", "光大", "guangda", "2022"),
    ("光大银行", "光大", "guangda", "2023"),
    ("光大银行", "光大", "guangda", "2024"),
    ("民生银行", "民生", "mingsheng", "2021"),
    ("民生银行", "民生", "mingsheng", "2022"),
    ("民生银行", "民生", "mingsheng", "2023"),
    ("民生银行", "民生", "mingsheng", "2024"),
    ("浦发银行", "浦发", "pufa", "2021"),
    ("浦发银行", "浦发", "pufa", "2022"),
    ("浦发银行", "浦发", "pufa", "2023"),
    ("浦发银行", "浦发", "pufa", "2024"),
]


def find_source(bank_short: str, legacy_key: str, year: str) -> pathlib.Path | None:
    """查找 prepare --source（markdown 或 zip）。"""
    # 1. 优先：Skill 1 work 目录中的 markdown（cmb_2021/unzipped/*.md）
    s1_work = WORK_DIR / f"{legacy_key.lower()}_{year}"
    if s1_work.is_dir():
        md_files = list(s1_work.rglob("*.md"))
        if md_files:
            return md_files[0]

    # 2. 次之：按银行分组后的 DocParse zip / 解压目录
    period = f"{year}年度"
    grouped_zip = EXTRACTED_TEXT_DIR / bank_short / f"{bank_short}_{period}_docparse.zip"
    if grouped_zip.exists():
        return grouped_zip
    grouped_dir = EXTRACTED_TEXT_DIR / bank_short / f"{bank_short}_{period}"
    if grouped_dir.is_dir():
        return grouped_dir

    # 3. 兼容旧的平铺 zip 命名
    legacy_candidates = [
        EXTRACTED_TEXT_DIR / f"{legacy_key.lower()}_{year}_docparse.zip",
        EXTRACTED_TEXT_DIR / f"{legacy_key.lower()}_{year}_annual_docparse.zip",
    ]
    if legacy_key.lower() == "mingsheng":
        legacy_candidates.append(EXTRACTED_TEXT_DIR / f"minsheng_{year}_annual_docparse.zip")
    for zip_path in legacy_candidates:
        if zip_path.exists():
            return zip_path

    # 4. 兼容旧的 extracted_text 目录命名
    legacy_dirs = [
        EXTRACTED_TEXT_DIR / f"{legacy_key}_{year}_annual",
        EXTRACTED_TEXT_DIR / f"{legacy_key.upper()}_{year}_annual",
        EXTRACTED_TEXT_DIR / f"{legacy_key.lower()}_{year}_annual",
    ]
    if legacy_key.lower() == "mingsheng":
        legacy_dirs.append(EXTRACTED_TEXT_DIR / f"minsheng_{year}_annual")
        legacy_dirs.append(EXTRACTED_TEXT_DIR / f"cmbc_{year}_annual")
    for d in legacy_dirs:
        if d.is_dir():
            return d

    # 5. 兜底：Skill 2 work 目录中的 markdown/zip（text_某甲_2021年度/）
    s2_work = WORK_DIR / f"text_{bank_short}_{year}年度"
    if s2_work.is_dir():
        md_files = list(s2_work.rglob("*.md"))
        if md_files:
            return md_files[0]
        zip_files = list(s2_work.rglob("*.zip"))
        if zip_files:
            return zip_files[0]

    return None


def run_prepare(bank: str, bank_short: str, legacy_key: str, year: str) -> bool:
    """运行单次 prepare。"""
    source = find_source(bank_short, legacy_key, year)
    if source is None:
        print(f"[warn] 未找到 source: {bank} {year}", flush=True)
        return False

    work_dir = WORK_DIR / f"text_{bank_short}_{year}年度"
    partial_output = DATA_DIR / "partial" / f"text_{bank_short}_{year}年度.json"

    cmd = [
        sys.executable,
        str(PREPARE_SCRIPT),
        "prepare",
        "--bank", bank,
        "--period", f"{year}年度",
        "--source", str(source),
        "--work-dir", str(work_dir),
        "--partial-output", str(partial_output),
        "--prompt-template", str(PROMPT_TEMPLATE),
        "--concurrency", "3",
    ]

    print(f"[prepare] 开始: {bank} {year} (source={source.name})", flush=True)
    result = subprocess.run(cmd, capture_output=False, text=True)
    if result.returncode == 0:
        print(f"[prepare] 成功: {bank} {year}", flush=True)
        return True
    print(f"[prepare] 失败 (rc={result.returncode}): {bank} {year}", flush=True)
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="批量 Skill 2 prepare（粗筛）")
    parser.add_argument("--max-parallel", type=int, default=3, help="最大并行数 (默认 3)")
    args = parser.parse_args()

    if not PREPARE_SCRIPT.exists():
        print(f"[error] 找不到 prepare 脚本: {PREPARE_SCRIPT}", flush=True)
        sys.exit(1)

    print(f"[batch] 找到 {len(TASKS)} 个待 prepare 任务", flush=True)

    success = 0
    for bank, bank_short, legacy_key, year in TASKS:
        ok = run_prepare(bank, bank_short, legacy_key, year)
        if ok:
            success += 1

    print(f"\n[batch] 完成: {success}/{len(TASKS)} 成功", flush=True)


if __name__ == "__main__":
    main()
