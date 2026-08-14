#!/usr/bin/env python3
"""准备阶段门卫：校验任务元数据与可追溯来源池是否达标。

本脚本不判断学术质量，只做确定性检查：meta 字段是否在枚举内、需要引用时
来源池是否存在且条数达标、每条来源是否明确声明已核验并填写核验依据、证据层级、
可支持判断与 URL。脚本不访问来源页面，不能证明这些声明真实。失败即 exit 1，
并打印可直接执行的修复指令，供模型据此补齐，而不是自行绕过。

exit code: 0 通过 / 1 阻断（可修复）/ 2 环境或参数错误。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


# meta.json 各字段的合法取值，超出枚举视为未定位清楚，阻断。
ALLOWED = {
    "mode": {"draft", "final"},
    "task_scope": {"full_paper", "chapter", "section", "paragraph", "revise", "check"},
    "paper_type": {"journal", "degree", "course", "conference", "review", "proposal", "other"},
    "discipline_branch": {
        "technical",
        "medical",
        "law",
        "hss_empirical",
        "hss_humanities",
        "review",
    },
    "citation_style": {
        "gbt7714_numeric",
        "author_year",
        "footnote",
        "apa",
        "chicago",
        "mla",
        "template",
    },
    "needs_citation": {"yes", "no"},
    "output_target": {"markdown_and_lark", "markdown_only"},
}

# meta.json 必填字段。discipline_branch 不含 other：留在 other 说明没定位清楚。
REQUIRED_META = (
    "mode",
    "task_scope",
    "paper_type",
    "discipline_branch",
    "needs_citation",
    "output_target",
    "citation_style",
)

# 来源池默认最少条数；需要引用时低于此值阻断。可用 --min-sources 覆盖。
DEFAULT_MIN_SOURCES = 3

URL_PATTERN = re.compile(r"https?://[^\s|）)】\]]+")
VERIFIED_SOURCE_STATUSES = {"已核验", "核验通过", "verified", "confirmed"}
UNVERIFIED_SOURCE_STATUSES = {
    "待核验",
    "未核验",
    "pending",
    "unverified",
    "needs-verification",
}
EMPTY_VERIFICATION_EVIDENCE = {
    "",
    "-",
    "—",
    "无",
    "未知",
    "待补",
    "待核验",
    "n/a",
    "na",
    "none",
    "unknown",
}


def emit(payload: dict[str, Any], exit_code: int = 0) -> None:
    """打印 JSON 结果并以指定退出码结束进程。"""
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(exit_code)


def norm(value: Any) -> str:
    """统一为小写去空白字符串，布尔转 yes/no，便于与枚举比较。"""
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value).strip().lower()


def text_sha256(path: Path) -> str:
    text = path.read_text(encoding="utf-8-sig")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    """读 JSON，兼容 Windows BOM。文件缺失或格式错直接 exit 2。"""
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        emit(
            {
                "status": "fail",
                "stage": "prepare",
                "failures": [f"缺少 {path.name}"],
                "fix": f"创建 {path}，填写 mode/discipline_branch 等字段。",
            },
            1,
        )
    except json.JSONDecodeError as exc:
        emit({"status": "error", "stage": "prepare", "failures": [f"{path.name} 不是合法 JSON：{exc}"]}, 2)
    if not isinstance(data, dict):
        emit({"status": "error", "stage": "prepare", "failures": [f"{path.name} 顶层必须是对象"]}, 2)
    return data


def check_meta(meta: dict[str, Any]) -> list[str]:
    """校验 meta.json 字段齐全且取值在枚举内。返回可读失败列表。"""
    failures: list[str] = []
    for key in REQUIRED_META:
        if key not in meta:
            failures.append(f"meta.json 缺少字段 {key}")
            continue
        value = norm(meta[key])
        if value not in ALLOWED[key]:
            failures.append(
                f"meta.json 的 {key} 取值 {meta[key]!r} 不合法，应为 {sorted(ALLOWED[key])} 之一"
            )
    limits: dict[str, int] = {}
    for field in ("min_chars", "max_chars"):
        if meta.get(field) in (None, ""):
            continue
        if type(meta[field]) is not int:
            failures.append(f"meta.json 的 {field} 必须是非负整数")
            continue
        limit = meta[field]
        if limit < 0:
            failures.append(f"meta.json 的 {field} 必须是非负整数")
            continue
        limits[field] = limit
    if (
        "min_chars" in limits
        and "max_chars" in limits
        and limits["min_chars"] > limits["max_chars"]
    ):
        failures.append("meta.json 的 min_chars 不能大于 max_chars")
    return failures


def parse_source_rows(text: str) -> list[str]:
    """从 source_pool.md 提取来源行。

    识别 Markdown 表格数据行（以 | 开头且非表头分隔线），或以 - 、数字编号
    开头的列表行。返回每行原文，供逐行校验题录与 URL。
    """
    rows: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("|"):
            # 跳过表头分隔线 |---|---| 和表头行（含"来源""ID"等列名的首行由调用方容忍）
            if re.fullmatch(r"\|[\s:|-]+\|?", stripped):
                continue
            rows.append(stripped)
        elif re.match(r"^(?:[-*]|\d+[.)、])\s+", stripped):
            rows.append(stripped)
    return rows


def table_cells(row: str) -> list[str]:
    return [cell.strip() for cell in row.strip().strip("|").split("|")]


def is_table_separator(cells: list[str]) -> bool:
    return bool(cells) and all(
        re.fullmatch(r":?-{3,}:?", re.sub(r"\s+", "", cell)) for cell in cells
    )


def find_header_index(headers: list[str], field: str) -> int | None:
    normalized = [re.sub(r"\s+", "", header).casefold() for header in headers]
    if field == "ID":
        candidates = {"id", "编号", "来源id", "sourceid"}
        return next((index for index, value in enumerate(normalized) if value in candidates), None)
    if field == "URL":
        return next(
            (
                index
                for index, value in enumerate(normalized)
                if value == "url" or "链接" in value
            ),
            None,
        )
    return next(
        (index for index, value in enumerate(normalized) if field.casefold() in value),
        None,
    )


def check_source_pool(path: Path, min_sources: int, require_url: bool) -> list[str]:
    """校验来源池：存在、非空、表头完整、有效条数达标、每条含可追溯字段。

    这里只核对核验声明的结构，不判断声明、题录、URL 或核验依据是否真实。
    """
    failures: list[str] = []
    if not path.exists():
        return [f"需要引用但缺少来源池 {path.name}"]
    text = path.read_text(encoding="utf-8-sig")
    if not text.strip():
        return [f"来源池 {path.name} 为空"]

    table_lines = [line.strip() for line in text.splitlines() if line.strip().startswith("|")]
    if not table_lines:
        return [f"来源池 {path.name} 必须使用结构化 Markdown 表格，不能用任意列表行代替"]
    headers = table_cells(table_lines[0])
    required_headers = ("ID", "来源", "证据层级", "可支持", "URL", "核验状态", "核验依据")
    header_indexes = {
        name: find_header_index(headers, name) for name in required_headers
    }
    missing_headers = [
        name for name, index in header_indexes.items() if index is None
    ]
    if missing_headers:
        failures.append(
            f"来源池表头缺少字段 {missing_headers}；必须明确记录核验状态、"
            "核验依据、来源、证据层级、可支持判断和 URL"
        )

    data_rows = [
        table_cells(row)
        for row in table_lines[1:]
        if not is_table_separator(table_cells(row))
    ]
    invalid_statuses: list[str] = []
    empty_evidence: list[int] = []
    incomplete: list[int] = []
    no_url: list[int] = []
    valid_rows: list[list[str]] = []
    if not missing_headers:
        for row_number, cells in enumerate(data_rows, start=1):
            values = {
                name: cells[index].strip() if index < len(cells) else ""
                for name, index in header_indexes.items()
                if index is not None
            }
            required_values = ("ID", "来源", "证据层级", "可支持")
            if any(not values.get(name) for name in required_values):
                incomplete.append(row_number)
            status = re.sub(r"\s+", "", values.get("核验状态", "")).casefold()
            is_verified = status in VERIFIED_SOURCE_STATUSES
            is_unverified = status in UNVERIFIED_SOURCE_STATUSES
            if not is_verified and not is_unverified:
                invalid_statuses.append(
                    f"{row_number}（{values.get('核验状态') or '空'}）"
                )
            evidence = re.sub(r"\s+", "", values.get("核验依据", "")).casefold()
            if is_verified and evidence in EMPTY_VERIFICATION_EVIDENCE:
                empty_evidence.append(row_number)
            if (
                is_verified
                and require_url
                and not URL_PATTERN.search(values.get("URL", ""))
            ):
                no_url.append(row_number)
            if (
                row_number not in incomplete
                and is_verified
                and evidence not in EMPTY_VERIFICATION_EVIDENCE
                and (not require_url or row_number not in no_url)
            ):
                valid_rows.append(cells)

    if invalid_statuses:
        failures.append(
            "来源池第 "
            + ", ".join(invalid_statuses)
            + " 条核验状态无效；使用已核验、待核验或未核验等明确状态"
        )
    if empty_evidence:
        failures.append(
            f"来源池第 {empty_evidence} 条核验依据为空或占位；"
            "没有可回溯核验依据的条目不得计入可用来源"
        )
    if len(valid_rows) < min_sources:
        failures.append(
            f"来源池有效条目 {len(valid_rows)} 条，少于要求的 {min_sources} 条；"
            f"请在 {path.name} 补足明确标记已核验且含核验依据、题录与可访问 URL 的来源"
        )

    if no_url:
        failures.append(
            f"来源池第 {no_url} 条缺少可访问 URL；每条来源必须带 http(s) 链接以供核验"
        )
    if incomplete:
        failures.append(
            f"来源池第 {incomplete} 条字段不足；"
            "每条至少填写 ID、来源、证据层级和可支持判断"
        )
    return failures


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--meta", required=True, help="meta.json 路径")
    parser.add_argument("--source-pool", required=True, help="source_pool.md 路径")
    parser.add_argument("--min-sources", type=int, default=DEFAULT_MIN_SOURCES)
    parser.add_argument(
        "--require-url",
        action="store_true",
        help="要求每条来源含 URL（默认关；沙箱无外网时可不校验可达性，仅校验存在）",
    )
    parser.add_argument("--write-report", default=None)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    meta = load_json(Path(args.meta))
    failures = check_meta(meta)

    needs_citation = norm(meta.get("needs_citation", "yes")) == "yes"
    if needs_citation:
        failures.extend(check_source_pool(Path(args.source_pool), args.min_sources, args.require_url))

    status = "pass" if not failures else "fail"
    payload: dict[str, Any] = {
        "status": status,
        "stage": "prepare",
        "needs_citation": "yes" if needs_citation else "no",
        "failures": failures,
        "verification_note": (
            "本阶段只校验来源池是否明确声明已核验并填写核验依据与可追溯字段；"
            "脚本不访问页面，不能证明题录、URL、核验依据或来源真实性。"
        ),
        "result": {
            "meta_sha256": text_sha256(Path(args.meta)),
            "source_pool_sha256": text_sha256(Path(args.source_pool))
            if needs_citation and Path(args.source_pool).exists()
            else "",
        },
    }
    if failures:
        payload["fix"] = "按 failures 逐条补齐 meta.json 与 source_pool.md，再重跑 make prepare。"

    if args.write_report:
        report = Path(args.write_report)
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    emit(payload, 0 if status == "pass" else 1)


if __name__ == "__main__":
    main()
