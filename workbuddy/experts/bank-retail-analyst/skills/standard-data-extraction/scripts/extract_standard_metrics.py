#!/usr/bin/env python3
"""
编排脚本：串联单个 (银行 × 报告期) 的标准数据提取流水线。

流程：
  [parse ]  腾讯云文档解析 -> zip          （可选，依赖 tencent_doc_parser）
  [unzip ]  解压 zip 取 Markdown           （内置）
  [coarse]  关键字粗筛 -> candidates.json  （调用 coarse_filter.coarse_filter）
  [bundle]  构造精筛 bundle/*.json         （调用 fine_extractor.build_bundles）
  ------- 以下阶段由主 Agent 的 LLM 子代理完成 --------
  [fine  ]  主 Agent 逐个 bundle 调用 task 工具，按 fine_extractor_prompt.md 输出
             extraction/<bucket>.json
  ----------------------------------------------------
  [merge ]  把所有 extraction/*.json 合并为 partial_<bank>_<period>.json 并做校验
             （调用 fine_extractor.validate_extraction + 规则 S2 加总校验）

CLI 子命令：
  prepare : 执行 parse(可选) + unzip + coarse + bundle，产出精筛 bundle
  merge   : 读入 extraction/*.json，校验、加总检查、合并为 partial_*.json
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import zipfile
from typing import Any, Dict, List, Optional

# 允许同目录 import
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from coarse_filter import coarse_filter  # noqa: E402
from fine_extractor import build_bundles, validate_extraction  # noqa: E402

# ---------------------------------------------------------------------------
# 共享路径约定：默认从 $RETAIL_ANALYSIS_HOME（默认 ~/RetailAnalysis）读取配置
# ---------------------------------------------------------------------------
# 上面 sys.path 已加入同目录；paths.py 在本 Skill scripts/ 下有副本
try:  # pragma: no cover
    try:
        import paths as _PATHS  # type: ignore
    except ImportError:
        _SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
        _repo_scripts = _SCRIPT_DIR.parent.parent.parent / "scripts"
        if _repo_scripts.is_dir() and str(_repo_scripts) not in sys.path:
            sys.path.insert(0, str(_repo_scripts))
        import paths as _PATHS  # type: ignore
except Exception:  # noqa: BLE001
    _PATHS = None  # type: ignore


def _resolve_metrics_config(
    explicit_path: Optional[str] = None,
) -> tuple[pathlib.Path, Dict[str, Any]]:
    """解析 Skill 1 指标配置并生成可复现元数据。"""
    if _PATHS is not None:
        path, source = _PATHS.resolve_config_file(
            "skill1", "metrics.yaml", explicit_path=explicit_path,
        )
        return path, _PATHS.config_file_metadata(path, source)

    path = pathlib.Path(explicit_path or pathlib.Path(__file__).resolve().parent.parent / "config" / "metrics.yaml")
    path = path.expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"配置文件不存在：{path}")
    import hashlib
    return path, {
        "source": "cli-explicit" if explicit_path else "skill-bundled",
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


# ---------------------------------------------------------------------------
# unzip
# ---------------------------------------------------------------------------

def unzip_parse_result(zip_path: pathlib.Path, out_dir: pathlib.Path) -> pathlib.Path:
    """解压腾讯云解析 zip，返回其中主 Markdown 文件的路径。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(out_dir)

    # 选取最大的 .md 文件作为主 Markdown
    md_files = sorted(out_dir.rglob("*.md"), key=lambda p: p.stat().st_size, reverse=True)
    if not md_files:
        raise RuntimeError(f"zip 中未找到 .md 文件: {zip_path}")
    return md_files[0]


# ---------------------------------------------------------------------------
# MD 完整性检查（DocParse 截断检测）
# ---------------------------------------------------------------------------

# 附注中分部报告相关的关键词，用于检测 MD 是否覆盖到附注章节
_SEGMENT_ANNEX_KEYWORDS = [
    "经营分部信息", "分部报告", "业务分部", "经营分部",
    "分部经营数据", "分部财务数据", "按业务分部",
]


def _check_md_completeness(
    md_path: pathlib.Path,
    coarse_result: dict,
    bank: str,
    manifest_warnings: Optional[list] = None,
) -> List[str]:
    """
    检查粗筛结果中是否包含 segment_report 类型的章节候选。
    若无，则扫描 MD 原文看是否提及"经营分部信息"等关键词
    （判断是 DocParse 截断 vs 确实不存在）。
    返回 warnings 列表。
    """
    warnings: List[str] = []

    # 检查粗筛是否发现了分部报告相关章节
    has_segment = any(
        c.get("chapter_group") == "segment_report"
        for c in coarse_result.get("chapter_candidates", [])
    )
    # 也检查表格候选中是否有分部报告类别
    has_segment_table = "分部报告" in coarse_result.get("table_candidates_by_category", {})

    if has_segment or has_segment_table:
        return warnings  # 正常，无需告警

    # 粗筛未发现分部报告 -> 检查 MD 原文中是否有关键词（判断截断 vs 不存在）
    try:
        md_text = md_path.read_text(encoding="utf-8")
    except Exception:
        warnings.append(f"[MD完整性] 无法读取 {md_path}，跳过完整性检查")
        return warnings

    md_lines = len(md_text.splitlines())
    found_keywords = [kw for kw in _SEGMENT_ANNEX_KEYWORDS if kw in md_text]

    if found_keywords:
        # MD 中提到了分部报告但粗筛没命中 -> 可能是章节名不在 CHAPTER_KEYWORDS 中
        msg = (
            f"[MD完整性·{bank}] ⚠️ MD 原文中发现关键词 {found_keywords}，"
            f"但粗筛未命中 segment_report 章节。请检查 coarse_filter.py 的 "
            f"CHAPTER_KEYWORDS['segment_report'] 是否缺少该银行的章节名变体。"
            f"（MD 共 {md_lines} 行）"
        )
    else:
        # MD 中完全没提到 -> 大概率是 DocParse 截断了附注部分
        msg = (
            f"[MD完整性·{bank}] ⚠️ MD 原文中未发现分部报告相关关键词"
            f"（经营分部信息/分部报告/业务分部等），且 MD 仅 {md_lines} 行。"
            f"该银行的分部报告表可能位于「第八章财务报告·附注·经营分部信息」，"
            f"但 DocParse 产出的 Markdown 未覆盖到该章节。"
            f"建议：重跑 DocParse 确保附注章节完整（检查 MD 是否包含'经营分部信息'小节）。"
        )

    warnings.append(msg)
    print(msg, flush=True)

    if manifest_warnings is not None:
        manifest_warnings.extend(warnings)

    return warnings


# ---------------------------------------------------------------------------
# prepare
# ---------------------------------------------------------------------------

def cmd_prepare(args: argparse.Namespace) -> None:
    work_dir = pathlib.Path(args.work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    metrics_yaml, metrics_meta = _resolve_metrics_config(args.metrics_yaml)
    print(
        f"[config] metrics={metrics_yaml} source={metrics_meta['source']} "
        f"sha256={metrics_meta['sha256'][:12]}",
        flush=True,
    )

    # 1. 定位 Markdown
    if args.markdown:
        md_path = pathlib.Path(args.markdown)
    elif args.parse_zip:
        unzip_dir = work_dir / "unzipped"
        md_path = unzip_parse_result(pathlib.Path(args.parse_zip), unzip_dir)
        print(f"[unzip] markdown -> {md_path}", flush=True)
    else:
        raise SystemExit("必须提供 --markdown 或 --parse-zip 其中之一")

    # 2. 粗筛
    coarse_result = coarse_filter(
        markdown_path=md_path,
        metrics_yaml=metrics_yaml,
        context_above=args.context_above,
        context_below=args.context_below,
    )
    coarse_path = work_dir / "coarse.json"
    coarse_path.write_text(
        json.dumps(coarse_result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        f"[coarse] chapter_candidates={len(coarse_result['chapter_candidates'])} "
        f"table_candidates={len(coarse_result['table_candidates'])} "
        f"-> {coarse_path}",
        flush=True,
    )

    # ---- MD 完整性检查（DocParse 截断检测） ----
    _check_md_completeness(md_path, coarse_result, args.bank, manifest_warnings=[])

    # 3. 构造精筛 bundle
    bundle_dir = work_dir / "bundles"
    bundles = build_bundles(
        coarse_json=coarse_path,
        metrics_yaml=metrics_yaml,
        bank=args.bank,
        period=args.period,
        output_dir=bundle_dir,
        max_candidates_per_bucket=args.max_candidates_per_bucket,
    )
    print(f"[bundle] {len(bundles)} bundle(s) -> {bundle_dir}", flush=True)
    for b in bundles:
        size_kb = b.stat().st_size / 1024
        print(f"  - {b.name}  ({size_kb:.1f} KiB)", flush=True)

    # 4. 产出工作清单，供主 Agent 知道要 spawn 多少个精筛子代理
    extraction_dir = work_dir / "extraction"
    prompt_template = (
        pathlib.Path(__file__).resolve().parent / "fine_extractor_prompt.md"
    ).resolve()

    # 4.1 生成机器可读的子代理任务清单（强制并行 spawn 的依据）
    fine_tasks = _build_fine_tasks(
        bundles=bundles,
        extraction_dir=extraction_dir,
        prompt_template=prompt_template,
        bank=args.bank,
        period=args.period,
        concurrency=args.concurrency,
    )
    fine_tasks_path = work_dir / "fine_tasks.json"
    fine_tasks_path.write_text(
        json.dumps(fine_tasks, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        f"[fine_tasks] {len(fine_tasks['tasks'])} task(s) in "
        f"{len(fine_tasks['batches'])} batch(es) (concurrency={args.concurrency}) "
        f"-> {fine_tasks_path}",
        flush=True,
    )

    manifest = {
        "bank": args.bank,
        "period": args.period,
        "markdown_path": str(md_path),
        "coarse_json": str(coarse_path),
        "bundles": [str(p) for p in bundles],
        "extraction_dir": str(extraction_dir),
        "partial_output": str(pathlib.Path(args.partial_output).resolve()),
        "prompt_template": str(prompt_template),
        "fine_tasks_json": str(fine_tasks_path),
        "concurrency": args.concurrency,
        "config": {"metrics": metrics_meta},
        "md_completeness_warnings": _check_md_completeness(
            md_path, coarse_result, args.bank, manifest_warnings=None
        ),
    }
    manifest_path = work_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[manifest] -> {manifest_path}", flush=True)
    # 主 Agent 可读取 fine_tasks.json 按 batches 分批并发 spawn 子代理
    print(
        f"[next] 主 Agent 请读取 {fine_tasks_path} 并按 batches 并发 spawn 子代理 "
        f"(默认并发 {args.concurrency})",
        flush=True,
    )


# ---------------------------------------------------------------------------
# 子代理任务清单构造
# ---------------------------------------------------------------------------

def _build_fine_tasks(
    bundles: List[pathlib.Path],
    extraction_dir: pathlib.Path,
    prompt_template: pathlib.Path,
    bank: str,
    period: str,
    concurrency: int,
) -> Dict[str, Any]:
    """
    为每个 bundle 构造一个子代理任务，并按 concurrency 分批。

    输出结构（宿主无关 / Host-agnostic，CodeBuddy/Cursor/WorkBuddy 都能用）：
    {
      "bank": "...", "period": "...",
      "concurrency": 3,
      "prompt_template": "/abs/path/fine_extractor_prompt.md",
      "extraction_dir": "/abs/path/extraction",
      "tasks": [
        {
          "task_id": "fine-某甲-2025年度-分部报告",
          "bucket": "分部报告",
          "bundle_path": "/abs/path/bundles/bundle_分部报告.json",
          "output_path": "/abs/path/extraction/分部报告.json",
          "batch_index": 0,
          "spawn_prompt": "完整可粘贴的 subagent prompt（含文件路径+契约）"
        },
        ...
      ],
      "batches": [
        ["fine-某甲-2025年度-分部报告", "fine-某甲-2025年度-零售存款", "fine-某甲-2025年度-零售贷款"],
        [...]
      ]
    }

    宿主映射：
      - CodeBuddy: `task(subagent_name="code-explorer"/"fine-extractor", prompt=spawn_prompt, ...)`
        或 team 模式 `task(name=task_id, team_name=..., prompt=spawn_prompt)`
      - Cursor:    Agent "Run in parallel" / "Send to background" with spawn_prompt
      - WorkBuddy: 并行子任务 / 后台任务入口传入 spawn_prompt

    主 Agent 只需按 batches 顺序、同一 batch 内并发 spawn，即可实现默认并发 3。
    """
    extraction_dir.mkdir(parents=True, exist_ok=True)

    concurrency = max(1, int(concurrency))
    tasks: List[Dict[str, Any]] = []

    for idx, bundle in enumerate(bundles):
        # bundle 文件名约定：bundle_<bucket>.json
        stem = bundle.stem
        bucket = stem[len("bundle_"):] if stem.startswith("bundle_") else stem
        output_path = extraction_dir / f"{bucket}.json"
        batch_index = idx // concurrency

        task_id = f"fine-{bank}-{period}-{bucket}"
        spawn_prompt = _render_spawn_prompt(
            bank=bank,
            period=period,
            bucket=bucket,
            bundle_path=bundle.resolve(),
            output_path=output_path.resolve(),
            prompt_template=prompt_template,
        )
        tasks.append({
            "task_id": task_id,
            "bucket": bucket,
            "bundle_path": str(bundle.resolve()),
            "output_path": str(output_path.resolve()),
            "batch_index": batch_index,
            "spawn_prompt": spawn_prompt,
        })

    # 组装 batches：同一 batch_index 的 task_id 放一起，按 batch_index 排序
    batches: List[List[str]] = []
    if tasks:
        max_batch = max(t["batch_index"] for t in tasks)
        batches = [[] for _ in range(max_batch + 1)]
        for t in tasks:
            batches[t["batch_index"]].append(t["task_id"])

    return {
        "bank": bank,
        "period": period,
        "concurrency": concurrency,
        "prompt_template": str(prompt_template),
        "extraction_dir": str(extraction_dir.resolve()),
        "tasks": tasks,
        "batches": batches,
    }


def _render_spawn_prompt(
    bank: str,
    period: str,
    bucket: str,
    bundle_path: pathlib.Path,
    output_path: pathlib.Path,
    prompt_template: pathlib.Path,
) -> str:
    """构造可直接粘贴给子代理的完整 prompt（含系统契约 + I/O 路径）。

    子代理只需：
      1. 打开 prompt_template 阅读契约
      2. 打开 bundle_path 读取 input_bundle
      3. 按契约输出纯 JSON 写入 output_path
    """
    return (
        f"你是 Skill1 精筛子代理，负责银行「{bank}」报告期「{period}」的 "
        f"「{bucket}」bucket。\n\n"
        f"执行步骤：\n"
        f"1. 先阅读系统提示文件（这是你的契约）：\n"
        f"   {prompt_template}\n"
        f"2. 读取 input_bundle（这是你此次任务的唯一数据源）：\n"
        f"   {bundle_path}\n"
        f"3. 严格遵守 fine_extractor_prompt.md 中的规则，**只从 candidates[*].context_markdown 取值，"
        f"禁止编造**；未找到的指标 values 必须返回空数组 []。\n"
        f"4. 输出**纯 JSON**（不要 markdown 代码块、不要解释文字），写入：\n"
        f"   {output_path}\n"
        f"5. 写入完成后，简要回报「bucket / metrics 数 / warnings 数 / 输出路径」，不要贴 JSON 原文。\n"
        f"\n"
        f"完成标志：{output_path} 文件已存在且为合法 JSON。"
    )


# ---------------------------------------------------------------------------
# merge
# ---------------------------------------------------------------------------

def _sum_check_rules(metrics: List[Dict[str, Any]]) -> List[str]:
    """规则 S2：细项加总 ≈ 合计，差异 > 0.5% 生成 warning。"""
    warnings: List[str] = []

    # 构造 {standard_name: {period_label: value}}
    table: Dict[str, Dict[str, float]] = {}
    for m in metrics:
        name = m["standard_name"]
        table[name] = {}
        for v in m.get("values", []) or []:
            pl = v.get("period_label")
            val = v.get("value")
            if isinstance(val, (int, float)) and pl:
                table[name][pl] = float(val)

    # 约定的加总关系
    sum_rules = [
        # (合计, [细项...])
        ("个人存款-合计-时点余额", ["个人存款-活期-时点余额", "个人存款-定期-时点余额"]),
        ("个人存款-合计-平均余额", ["个人存款-活期-平均余额", "个人存款-定期-平均余额"]),
        # 零售贷款：合计 ≈ 信用卡 + 按揭 + 消费 + 经营 + 其他
        ("个人贷款-合计-时点余额", [
            "信用卡贷款-时点余额",
            "住房按揭贷款-时点余额",
            "消费贷款-时点余额",
            "经营贷款-时点余额",
            "其他个人贷款-时点余额",
        ]),
    ]

    for total_name, parts in sum_rules:
        if total_name not in table:
            continue
        for period, total_val in table[total_name].items():
            part_sum = 0.0
            missing = []
            for p in parts:
                if p in table and period in table[p]:
                    part_sum += table[p][period]
                else:
                    missing.append(p)
            if missing:
                # 允许缺失项（非所有银行都披露所有细项），但要记录
                warnings.append(
                    f"S2 加总校验跳过：{total_name}({period}) 缺少细项 {missing}"
                )
                continue
            if total_val == 0:
                continue
            diff_pct = abs(part_sum - total_val) / abs(total_val) * 100
            if diff_pct > 0.5:
                warnings.append(
                    f"⚠️ 细项加总不等于合计（规则 S2）：{total_name}({period}) "
                    f"合计={total_val} 细项之和={part_sum:.2f} 差异率={diff_pct:.2f}%"
                )

    return warnings


def cmd_merge(args: argparse.Namespace) -> None:
    manifest_path = pathlib.Path(args.manifest)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    extraction_dir = pathlib.Path(manifest["extraction_dir"])
    if not extraction_dir.exists():
        raise SystemExit(
            f"extraction 目录不存在：{extraction_dir}\n"
            f"请先让 LLM 子代理按 {manifest['prompt_template']} 处理每个 bundle，"
            f"把产物写到该目录。"
        )

    ext_files = sorted(extraction_dir.glob("*.json"))
    if not ext_files:
        raise SystemExit(f"extraction 目录为空：{extraction_dir}")

    manifest_metrics = (manifest.get("config") or {}).get("metrics") or {}
    pinned_path = manifest_metrics.get("path")
    if args.metrics_yaml:
        metrics_yaml, metrics_meta = _resolve_metrics_config(args.metrics_yaml)
    elif pinned_path and pathlib.Path(pinned_path).is_file():
        metrics_yaml, metrics_meta = _resolve_metrics_config(str(pinned_path))
        metrics_meta["source"] = manifest_metrics.get("source", "manifest-pinned")
    else:
        metrics_yaml, metrics_meta = _resolve_metrics_config()

    expected_sha256 = manifest_metrics.get("sha256")
    if expected_sha256 and metrics_meta["sha256"] != expected_sha256:
        raise SystemExit(
            "prepare/merge 使用的 metrics.yaml 不一致：\n"
            f"  prepare sha256={expected_sha256}\n"
            f"  merge   sha256={metrics_meta['sha256']} ({metrics_yaml})\n"
            "请使用 prepare 阶段记录的同一份配置重新执行。"
        )
    print(
        f"[config] metrics={metrics_yaml} source={metrics_meta['source']} "
        f"sha256={metrics_meta['sha256'][:12]}",
        flush=True,
    )

    merged_metrics: List[Dict[str, Any]] = []
    merged_notes: List[str] = []
    merged_warnings: List[str] = []

    for ef in ext_files:
        validated = validate_extraction(ef, metrics_yaml)
        merged_metrics.extend(validated.get("metrics", []) or [])
        merged_notes.extend(validated.get("notes", []) or [])
        merged_warnings.extend(validated.get("warnings", []) or [])

    # 规则 S2 加总校验
    s2_warnings = _sum_check_rules(merged_metrics)
    merged_warnings.extend(s2_warnings)

    output = {
        "bank": manifest["bank"],
        "period": manifest["period"],
        "source_markdown": manifest["markdown_path"],
        "config": {"metrics": metrics_meta},
        "metrics": merged_metrics,
        "notes": merged_notes,
        "warnings": merged_warnings,
    }
    out_path = pathlib.Path(manifest["partial_output"])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        f"[merge] metrics={len(merged_metrics)} warnings={len(merged_warnings)} "
        f"-> {out_path}",
        flush=True,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Skill1 标准数据提取编排器（粗筛+精筛）")
    sub = p.add_subparsers(dest="cmd", required=True)

    prep = sub.add_parser("prepare", help="解析/粗筛/bundle 准备（LLM 前置）")
    prep.add_argument("--bank", required=True, help="银行简称，如 某某银行")
    prep.add_argument("--period", required=True, help="报告期，如 2025年度")
    prep.add_argument("--parse-zip", help="腾讯云解析 zip 路径（与 --markdown 二选一）")
    prep.add_argument("--markdown", help="已解压 Markdown 路径（与 --parse-zip 二选一）")
    prep.add_argument(
        "--metrics-yaml",
        default=None,
        help="显式指标字典；默认按 RETAIL_ANALYSIS_CONFIG_DIR/skill1/metrics.yaml、Skill 本地 config/ 顺序解析",
    )
    prep.add_argument("--work-dir", required=True, help="工作目录，存放 coarse.json / bundles / manifest.json")
    prep.add_argument(
        "--partial-output",
        required=True,
        help="最终 partial JSON 路径（merge 阶段写入）",
    )
    prep.add_argument("--context-above", type=int, default=20)
    prep.add_argument("--context-below", type=int, default=5)
    prep.add_argument("--max-candidates-per-bucket", type=int, default=6)
    prep.add_argument(
        "--concurrency",
        type=int,
        default=3,
        help="精筛子代理并发度（默认 3），用于将 bundle 任务分批；主 Agent 按 batches 并发 spawn",
    )

    mrg = sub.add_parser("merge", help="合并 LLM 子代理的 extraction/*.json 并做校验")
    mrg.add_argument("--manifest", required=True, help="prepare 阶段生成的 manifest.json")
    mrg.add_argument(
        "--metrics-yaml",
        default=None,
        help="显式指标字典；默认沿用 manifest 中 prepare 阶段锁定的配置",
    )

    return p.parse_args()


def main() -> None:
    args = build_args()
    if args.cmd == "prepare":
        cmd_prepare(args)
    elif args.cmd == "merge":
        cmd_merge(args)


if __name__ == "__main__":
    main()
