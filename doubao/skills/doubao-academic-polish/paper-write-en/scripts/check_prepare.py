#!/usr/bin/env python3
"""准备阶段门卫（英文侧）：校验任务元数据与候选文献验真。

本脚本不判断学术质量，只做确定性检查与文献真实性核验的编排：
1. 校验 meta.json 字段在枚举内。
2. 需要引用时，校验候选文献 JSON（references 数组）存在且每条字段完整。
3. 联网模式（默认）调用 verify_literature.py 做真实性核验，只有 A/B 级、
   通过 title/author/doi 校验的文献进 core_literature；产出 verified_refs.json。
4. 离线模式（--offline，或联网失败降级）只做结构与字段完整性校验，并如实
   标注“真实性未联网核验”。

exit code: 0 通过 / 1 阻断（可修复）/ 2 环境或参数错误。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent

# meta.json 各字段合法取值。英文侧无中文学科分支，用论文类型与引用体例。
ALLOWED = {
    "mode": {"draft", "final"},
    "task_scope": {"full_paper", "section", "revise", "abstract"},
    "paper_type": {"research_article", "review_article", "term_paper", "journal_article", "conference_paper", "thesis", "proposal", "other"},
    "citation_style": {"apa7", "mla9", "chicago18_author_date"},
    "needs_citation": {"yes", "no"},
    "output_target": {"lark", "markdown_only"},
}

REQUIRED_META = (
    "mode",
    "task_scope",
    "paper_type",
    "citation_style",
    "needs_citation",
    "output_target",
)

# 候选文献每条必备字段（进验真前的最低结构要求）。
CANDIDATE_REQUIRED = ("title", "first_author", "url")

DEFAULT_MIN_CORE = 1


def emit(payload: dict[str, Any], exit_code: int = 0) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(exit_code)


def norm(value: Any) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value).strip().lower()


def text_sha256(path: Path) -> str:
    text = path.read_text(encoding="utf-8-sig")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_json(path: Path, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        emit(
            {
                "status": "fail",
                "stage": "prepare",
                "failures": [f"缺少 {label}：{path.name}"],
                "fix": f"创建 {path}。",
            },
            1,
        )
    except json.JSONDecodeError as exc:
        emit({"status": "error", "stage": "prepare", "failures": [f"{path.name} 不是合法 JSON：{exc}"]}, 2)


def check_meta(meta: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if not isinstance(meta, dict):
        return ["meta.json 顶层必须是对象"]
    for key in REQUIRED_META:
        if key not in meta:
            failures.append(f"meta.json 缺少字段 {key}")
            continue
        if norm(meta[key]) not in ALLOWED[key]:
            failures.append(f"meta.json 的 {key} 取值 {meta[key]!r} 不合法，应为 {sorted(ALLOWED[key])} 之一")
    limits: dict[str, int] = {}
    for field in ("min_words", "max_words"):
        if meta.get(field) in (None, ""):
            continue
        if type(meta[field]) is not int:
            failures.append(f"meta.json 的 {field} 必须是非负整数")
            continue
        value = meta[field]
        if value < 0:
            failures.append(f"meta.json 的 {field} 必须是非负整数")
            continue
        limits[field] = value
    if (
        "min_words" in limits
        and "max_words" in limits
        and limits["min_words"] > limits["max_words"]
    ):
        failures.append("meta.json 的 min_words 不能大于 max_words")
    return failures


def check_candidates_structure(candidates_path: Path) -> tuple[list[str], int]:
    """离线结构校验：references 数组存在、每条含标题/作者/URL。"""
    failures: list[str] = []
    data = load_json(candidates_path, "候选文献 JSON")
    refs = data.get("references") if isinstance(data, dict) else None
    if not isinstance(refs, list) or not refs:
        return ([f"{candidates_path.name} 需含非空的 references 数组"], 0)
    for i, ref in enumerate(refs):
        if not isinstance(ref, dict):
            failures.append(f"references[{i}] 必须是对象")
            continue
        for field in CANDIDATE_REQUIRED:
            if not str(ref.get(field, "")).strip():
                failures.append(f"references[{i}] 缺少 {field}（真实文献必须有标题、第一作者、可访问 URL）")
    return (failures, len(refs))


def run_online_verification(
    candidates_path: Path, wf: Path, min_core: int, registry: Path | None, timeout: int
) -> tuple[list[str], dict[str, Any]]:
    """联网调 verify_literature.py，读回它产出的 handoff 判定。"""
    verify_script = HERE / "verify_literature.py"
    if not verify_script.exists():
        return ([f"缺少验真引擎 {verify_script.name}"], {})
    report_path = wf / "verification_report.json"
    handoff_path = wf / "verified_refs.json"
    cmd = [
        sys.executable,
        str(verify_script),
        str(candidates_path),
        "--out",
        str(report_path),
        "--handoff",
        str(handoff_path),
        "--min-core",
        str(min_core),
    ]
    if registry and registry.exists():
        cmd += ["--quality-registry", str(registry)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return (["online"], {"degraded": True, "reason": f"验真联网超时（>{timeout}s）"})
    except OSError as exc:
        return (["online"], {"degraded": True, "reason": f"验真进程启动失败：{exc}"})
    # verify_literature 内部联网失败不会崩，只会让 core_literature 为空；
    # 这里读它产出的 handoff 做判定。
    if not handoff_path.exists():
        return (["online"], {"degraded": True, "reason": "验真未产出 verified_refs.json（可能网络不可用）"})
    handoff = load_json(handoff_path, "verified_refs.json")
    core = handoff.get("core_literature") if isinstance(handoff, dict) else None
    failures: list[str] = []
    if not isinstance(core, list) or len(core) < min_core:
        failures.append(
            f"通过真实性核验的 A/B 级文献 {len(core) if isinstance(core, list) else 0} 条，"
            f"少于要求的 {min_core} 条；补充可核验来源或修正 DOI/标题/作者后重跑 make prepare"
        )
    return (failures, {"degraded": False, "core_count": len(core) if isinstance(core, list) else 0})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--meta", required=True, help="meta.json 路径")
    parser.add_argument("--candidates", required=True, help="候选文献 JSON 路径（references 数组）")
    parser.add_argument("--workflow", default=".workflow", help=".workflow 目录")
    parser.add_argument("--min-core", type=int, default=DEFAULT_MIN_CORE)
    parser.add_argument("--quality-registry", default="", help="可选质量凭据登记表 JSON")
    parser.add_argument("--timeout", type=int, default=180, help="联网验真总超时秒数")
    parser.add_argument("--offline", action="store_true", help="强制离线：只做结构校验，不联网验真")
    parser.add_argument("--write-report", default=None)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    wf = Path(args.workflow)
    wf.mkdir(parents=True, exist_ok=True)
    # 每次prepare先清理上一轮验真产物，防止离线/降级运行误用旧core_literature。
    for stale_name in ("verified_refs.json", "verification_report.json"):
        stale = wf / stale_name
        if stale.exists():
            stale.unlink()

    meta = load_json(Path(args.meta), "meta.json")
    failures = check_meta(meta)

    needs_citation = norm(meta.get("needs_citation", "yes")) == "yes" if isinstance(meta, dict) else True
    verification_mode = "skipped"
    verification_note = ""

    if needs_citation:
        candidates_path = Path(args.candidates)
        struct_failures, count = check_candidates_structure(candidates_path)
        failures.extend(struct_failures)
        # 结构无误才进入验真；结构错先让模型修结构。
        if not struct_failures:
            if args.offline:
                verification_mode = "offline"
                verification_note = "需要引用的任务不能在离线模式完成真实性验真"
                failures.append("needs_citation=yes 时禁止 OFFLINE=1；恢复联网验真或改为不含引用的任务")
            else:
                registry = Path(args.quality_registry) if args.quality_registry else None
                verify_failures, info = run_online_verification(
                    candidates_path, wf, args.min_core, registry, args.timeout
                )
                if info.get("degraded"):
                    # 联网失败降级：不因网络问题阻断，但如实标注未联网核验。
                    verification_mode = "degraded"
                    verification_note = f"真实性联网核验失败：{info.get('reason', '')}"
                    failures.append("文献真实性未完成联网核验，prepare 不得通过")
                else:
                    verification_mode = "online"
                    verification_note = f"联网核验通过，A/B 级核心文献 {info.get('core_count', 0)} 条"
                    failures.extend(verify_failures)

    status = "pass" if not failures else "fail"
    payload: dict[str, Any] = {
        "status": status,
        "stage": "prepare",
        "needs_citation": "yes" if needs_citation else "no",
        "verification_mode": verification_mode,
        "verification_note": verification_note,
        "failures": failures,
        "result": {
            "meta_sha256": text_sha256(Path(args.meta)),
            "candidates_sha256": text_sha256(Path(args.candidates))
            if needs_citation and Path(args.candidates).exists()
            else "",
        },
    }
    if failures:
        payload["fix"] = "按 failures 修正 meta.json 与候选文献 JSON，再重跑 make prepare。"

    report_path = Path(args.write_report) if args.write_report else (wf / "prepare_check.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    emit(payload, 0 if status == "pass" else 1)


if __name__ == "__main__":
    main()
