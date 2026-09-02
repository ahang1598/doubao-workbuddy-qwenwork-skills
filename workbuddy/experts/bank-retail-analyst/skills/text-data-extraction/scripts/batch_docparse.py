#!/usr/bin/env python3
"""
批量运行 DocParse（腾讯云文档解析）。
为光大、民生、浦发（2021-2024）批量解析 PDF。
"""

from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys
from typing import List, Tuple

# 添加脚本目录到 Python 路径
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

REPORTS_DIR = _PATHS.REPORTS_DIR
EXTRACTED_TEXT_DIR = _PATHS.EXTRACTED_TEXT_DIR

# 需要解析的 (PDF 所在子目录, 银行简称, 年份) 列表
TARGETS: List[Tuple[str, str, str]] = [
    ("光大银行", "光大", "2021"),
    ("光大银行", "光大", "2022"),
    ("光大银行", "光大", "2023"),
    ("光大银行", "光大", "2024"),
    ("民生银行", "民生", "2021"),
    ("民生银行", "民生", "2022"),
    ("民生银行", "民生", "2023"),
    ("民生银行", "民生", "2024"),
    ("浦发银行", "浦发", "2021"),
    ("浦发银行", "浦发", "2022"),
    ("浦发银行", "浦发", "2023"),
    ("浦发银行", "浦发", "2024"),
]


def find_pdf(reports_dir: pathlib.Path, bank_dir: str, year: str) -> pathlib.Path | None:
    """查找 PDF 文件（支持多种命名模式）。"""
    bank_path = reports_dir / bank_dir
    if not bank_path.is_dir():
        print(f"[warn] 目录不存在: {bank_path}")
        return None

    # 匹配模式：包含年份的 PDF
    year_int = int(year) if year.isdigit() else 0
    patterns = [
        f"{year}年度",
        f"{year}年年度报告",
        f"{year_int - 1}-{year_int}年度报告" if year_int else "",
    ]

    for pdf_path in bank_path.glob("*.pdf"):
        pdf_name = pdf_path.name
        if any(p in pdf_name for p in patterns):
            return pdf_path

    # 兜底：返回目录中最新修改的 PDF
    pdfs = sorted(bank_path.glob("*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True)
    if pdfs:
        print(f"[warn] 未找到明确匹配 {year}，使用: {pdfs[0].name}")
        return pdfs[0]
    return None


def run_docparse(parser_script: pathlib.Path, pdf_path: pathlib.Path,
                 output_zip: pathlib.Path, env_file: pathlib.Path) -> bool:
    """运行单次 DocParse。"""
    cmd = [
        sys.executable,
        str(parser_script),
        "--env-file", str(env_file),
        "--file-type", "PDF",
        "--file-path", str(pdf_path),
        "--output-zip", str(output_zip),
    ]
    print(f"[docparse] 开始: {pdf_path.name}", flush=True)
    result = subprocess.run(
        cmd,
        capture_output=False,
        text=True,
    )
    if result.returncode == 0:
        print(f"[docparse] 成功: {output_zip.name}", flush=True)
        return True
    print(f"[docparse] 失败 (rc={result.returncode}): {pdf_path.name}", flush=True)
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="批量 DocParse")
    parser.add_argument("--max-parallel", type=int, default=3, help="最大并行数 (默认 3)")
    args = parser.parse_args()

    script_dir = pathlib.Path(__file__).resolve().parent
    # tencent_doc_parser.py 由 standard-data-extraction（skill1）提供，本 Skill 需跨包定位。
    standard_dir = _PATHS.SKILL_DIRS.get("skill1")
    parser_script = None
    if standard_dir is not None:
        cand = standard_dir / "scripts" / "tencent_doc_parser.py"
        if cand.exists():
            parser_script = cand
    if parser_script is None or not parser_script.exists():
        # 兜底：在同级 skills 目录内搜索（兼容不同安装布局）
        for p in script_dir.parent.parent.rglob("tencent_doc_parser.py"):
            parser_script = p
            break
    # .env 位于 standard-data-extraction 根目录（由 skill1 独占，用户自建）。
    env_file = (standard_dir / ".env") if standard_dir is not None else script_dir.parent / ".env"

    if not parser_script.exists():
        print(f"[error] 找不到 DocParse 脚本: {parser_script}")
        sys.exit(1)
    if not env_file.exists():
        print(f"[error] 找不到 .env 文件: {env_file}")
        sys.exit(1)

    # 查找所有 PDF
    tasks: List[Tuple[str, str, pathlib.Path, pathlib.Path]] = []
    for bank_dir, bank_short, year in TARGETS:
        pdf = find_pdf(REPORTS_DIR, bank_dir, year)
        if pdf is None:
            print(f"[warn] 未找到 PDF: {bank_dir} {year}")
            continue
        output_zip = EXTRACTED_TEXT_DIR / bank_short / f"{bank_short}_{year}年度_docparse.zip"
        tasks.append((bank_short, year, pdf, output_zip))

    print(f"[batch] 找到 {len(tasks)} 个待解析任务", flush=True)

    # 顺序运行（DocParse 有 COS 并发限制，建议不超过 3 并行）
    success = 0
    for bank_key, year, pdf, output_zip in tasks:
        ok = run_docparse(parser_script, pdf, output_zip, env_file)
        if ok:
            success += 1

    print(f"\n[batch] 完成: {success}/{len(tasks)} 成功", flush=True)


if __name__ == "__main__":
    main()
