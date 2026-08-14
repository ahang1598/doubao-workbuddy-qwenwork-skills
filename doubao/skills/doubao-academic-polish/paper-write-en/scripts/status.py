#!/usr/bin/env python3
"""三态判定层（英文侧）：只读 .workflow 物理产物，给出最终交付状态。

模型不得自行总结完成度，最终回答必须以本脚本结论为准。判定只看真实文件。三态：

- PASS：正文检查通过，且飞书已交付（或用户显式跳过），交付完成。
- BLOCKED：最早未满足的阶段及其修复指令；流程卡住，未交付。
- DRAFT_ONLY：正文文件存在但检查未过或未交付；只是未验收草稿，禁止称完成。

另透传 prepare 阶段的验真模式（online/offline/degraded），在 PASS 时如实标注
文献真实性是否已联网核验，不假装验过。

exit code: 0 表示 PASS，1 表示 BLOCKED 或 DRAFT_ONLY，2 环境错误。
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def emit(payload: dict[str, Any], exit_code: int = 0) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(exit_code)


def load_report(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
        emit({"status": "ERROR", "reason": f"无法读取检查报告 {path.name}：{exc}"}, 2)
    return data if isinstance(data, dict) else None


def non_empty(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        return bool(path.read_text(encoding="utf-8-sig").strip())
    except (UnicodeDecodeError, OSError) as exc:
        emit({"status": "ERROR", "reason": f"无法读取产物 {path.name}：{exc}"}, 2)
    return False


def file_sha256(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8-sig")
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
    except (OSError, UnicodeDecodeError) as exc:
        emit({"status": "ERROR", "reason": f"无法读取产物 {path.name}：{exc}"}, 2)
    return ""


def file_bytes_sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        emit({"status": "ERROR", "reason": f"无法读取产物 {path.name}：{exc}"}, 2)
    return ""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflow", default=".workflow", help=".workflow 目录")
    parser.add_argument(
        "--allow-lark-skip",
        action="store_true",
        help="兼容参数；不能覆盖meta，只有output_target=markdown_only时有效",
    )
    return parser


def verification_note(prepare_report: dict[str, Any] | None) -> str:
    if not prepare_report:
        return ""
    mode = prepare_report.get("verification_mode", "")
    if mode in {"degraded", "offline"}:
        return f"注意：文献真实性未联网核验（{mode}）。{prepare_report.get('verification_note', '')}"
    if mode == "online":
        return prepare_report.get("verification_note", "文献已联网核验")
    return ""


def main() -> None:
    args = build_parser().parse_args()
    wf = Path(args.workflow)

    prepare_report = load_report(wf / "prepare_check.json")
    draft_report = load_report(wf / "draft_check.json")
    lark_report = load_report(wf / "lark_check.json")
    meta = load_report(wf / "meta.json")
    output_target = str((meta or {}).get("output_target") or "")
    allow_lark_skip = output_target == "markdown_only"
    if args.allow_lark_skip and not allow_lark_skip:
        emit({"status": "BLOCKED", "stage": "deliver",
              "reason": "--allow-lark-skip 与当前 meta.output_target 冲突。",
              "next": "不要直接传跳过参数；如用户只要Markdown，在meta中设置output_target=markdown_only并重跑prepare。"}, 1)

    draft_exists = non_empty(wf / "paper_draft.md")
    final_exists = non_empty(wf / "paper_final.md")

    if prepare_report is None:
        emit({"status": "BLOCKED", "stage": "prepare",
              "reason": "尚未通过准备阶段检查（缺 prepare_check.json）。",
              "next": "运行 make prepare，按提示补齐 meta.json 与候选文献 JSON。"}, 1)
    if prepare_report.get("status") != "pass":
        emit({"status": "BLOCKED", "stage": "prepare", "reason": "准备阶段检查未通过。",
              "failures": prepare_report.get("failures", []),
              "next": "按 failures 修正后重跑 make prepare。"}, 1)
    prepare_result = prepare_report.get("result") or {}
    if not (wf / "meta.json").exists() or prepare_result.get("meta_sha256") != file_sha256(wf / "meta.json"):
        emit({"status": "BLOCKED", "stage": "prepare",
              "reason": "prepare_check.json 不属于当前 meta.json。",
              "next": "运行 make prepare 重新检查任务元数据。"}, 1)
    if prepare_report.get("needs_citation") == "yes":
        candidates = wf / "candidates.json"
        if not candidates.exists() or prepare_result.get("candidates_sha256") != file_sha256(candidates):
            emit({"status": "BLOCKED", "stage": "prepare",
                  "reason": "prepare_check.json 不属于当前 candidates.json。",
                  "next": "运行 make prepare 重新验真候选文献。"}, 1)

    if not draft_exists:
        emit({"status": "BLOCKED", "stage": "write",
              "reason": "正文 paper_draft.md 不存在或为空。",
              "next": "写正文到 .workflow/paper_draft.md，然后运行 make write。"}, 1)

    if draft_report is None or draft_report.get("status") != "pass":
        emit({"status": "DRAFT_ONLY", "stage": "write",
              "reason": "正文存在但未通过写作检查，只是未验收草稿，不能称完成。",
              "failures": (draft_report or {}).get("failures", ["未运行 make write 检查"]),
              "next": "按 failures 修正 paper_draft.md，重跑 make write。"}, 1)
    draft_sha = file_sha256(wf / "paper_draft.md")
    draft_result = draft_report.get("result") or {}
    report_sha = str(draft_result.get("input_sha256") or "")
    if report_sha != draft_sha:
        emit({"status": "DRAFT_ONLY", "stage": "write",
              "reason": "draft_check.json 不属于当前 paper_draft.md，正文修改后尚未重新检查。",
              "next": "运行 make write 重新生成写作检查报告。"}, 1)
    current_meta_sha = file_sha256(wf / "meta.json")
    if str(draft_result.get("meta_sha256") or "") != current_meta_sha:
        emit({"status": "DRAFT_ONLY", "stage": "write",
              "reason": "draft_check.json 不属于当前 meta.json，任务元数据变化后尚未重新检查正文。",
              "next": "运行 make write 重新生成写作检查报告。"}, 1)
    verified_refs = wf / "verified_refs.json"
    if prepare_report.get("needs_citation") == "yes" and not verified_refs.exists():
        emit({"status": "DRAFT_ONLY", "stage": "write",
              "reason": "当前任务需要引用，但 verified_refs.json 不存在。",
              "next": "先运行 make prepare 重新验真文献，再运行 make write。"}, 1)
    current_verified_refs_sha = file_sha256(verified_refs) if verified_refs.exists() else ""
    if str(draft_result.get("verified_refs_sha256") or "") != current_verified_refs_sha:
        emit({"status": "DRAFT_ONLY", "stage": "write",
              "reason": "draft_check.json 不属于当前 verified_refs.json，文献验真结果变化后尚未重新检查正文。",
              "next": "运行 make write 重新生成写作检查报告。"}, 1)
    if str((meta or {}).get("task_scope") or "").strip().lower() == "revise":
        for filename, field in (
            ("original_draft.md", "original_sha256"),
            ("revision_contract.json", "revision_contract_sha256"),
        ):
            path = wf / filename
            if not path.exists() or str(draft_result.get(field) or "") != file_sha256(path):
                emit({"status": "DRAFT_ONLY", "stage": "write",
                      "reason": f"draft_check.json 不属于当前 {filename}，修订基线或授权合同变化后尚未重新检查。",
                      "next": "运行 make write 重新执行修订保真检查。"}, 1)

    note = verification_note(prepare_report)

    if allow_lark_skip:
        if not final_exists:
            emit({"status": "DRAFT_ONLY", "stage": "deliver",
                  "reason": "写作已过但缺终稿 paper_final.md。",
                  "next": "运行 make deliver 生成终稿（已跳过飞书）。"}, 1)
        if file_sha256(wf / "paper_final.md") != draft_sha:
            emit({"status": "DRAFT_ONLY", "stage": "deliver",
                  "reason": "paper_final.md 与当前已检查正文不一致。",
                  "next": "运行 make deliver 重新生成终稿。"}, 1)
        emit({"status": "PASS", "stage": "deliver",
              "reason": "写作检查通过，终稿已生成，用户已跳过飞书交付。",
              "lark": "skipped_by_user", "verification": note}, 0)

    if not final_exists or lark_report is None:
        emit({"status": "DRAFT_ONLY", "stage": "deliver",
              "reason": "写作已过但尚未完成飞书交付与读回校验。",
              "next": "运行 make deliver 创建飞书文档并读回校验。"}, 1)
    if lark_report.get("status") != "pass":
        emit({"status": "BLOCKED", "stage": "deliver", "reason": "飞书读回校验未通过。",
              "failures": lark_report.get("failures", []),
              "next": "按 failures 修复飞书文档后重跑 make deliver。"}, 1)
    final_sha = file_sha256(wf / "paper_final.md")
    if final_sha != draft_sha:
        emit({"status": "DRAFT_ONLY", "stage": "deliver",
              "reason": "paper_final.md 与当前已检查正文不一致。",
              "next": "运行 make deliver 重新生成终稿。"}, 1)
    lark_result = lark_report.get("result") or {}
    lark_source_sha = str(lark_result.get("source_sha256") or "")
    if lark_source_sha != final_sha:
        emit({"status": "DRAFT_ONLY", "stage": "deliver",
              "reason": "lark_check.json 不属于当前终稿，飞书需重新交付并读回。",
              "next": "运行 make deliver 重新生成飞书读回报告。"}, 1)
    if str(lark_result.get("meta_sha256") or "") != current_meta_sha:
        emit({"status": "DRAFT_ONLY", "stage": "deliver",
              "reason": "lark_check.json 不属于当前 meta.json，交付目标或引用体例变化后尚未重新读回。",
              "next": "运行 make deliver 重新生成飞书读回报告。"}, 1)

    expected_snapshot = (wf / "lark_permission.json").resolve()
    snapshot_value = str(lark_result.get("permission_snapshot_file") or "").strip()
    if not snapshot_value:
        emit({"status": "BLOCKED", "stage": "deliver",
              "reason": "lark_check.json 缺少 permission_snapshot_file，无法证明当前飞书权限。",
              "next": "运行 make deliver 重新读取权限快照并生成交付报告。"}, 1)
    snapshot_path = Path(snapshot_value)
    reported_candidates = (
        {snapshot_path.resolve()}
        if snapshot_path.is_absolute()
        else {snapshot_path.resolve(), (wf / snapshot_path).resolve()}
    )
    if expected_snapshot not in reported_candidates or not expected_snapshot.is_file():
        emit({"status": "BLOCKED", "stage": "deliver",
              "reason": "permission_snapshot_file 不存在或不属于当前工作流目录。",
              "next": "运行 make deliver 重新读取当前文档的权限快照。"}, 1)
    snapshot_sha = file_bytes_sha256(expected_snapshot)
    if str(lark_result.get("permission_snapshot_sha256") or "") != snapshot_sha:
        emit({"status": "BLOCKED", "stage": "deliver",
              "reason": "lark_check.json 记录的权限快照 SHA 与当前文件不一致。",
              "next": "运行 make deliver 重新读取并校验飞书权限。"}, 1)
    try:
        snapshot_payload = json.loads(expected_snapshot.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
        emit({"status": "BLOCKED", "stage": "deliver",
              "reason": f"权限快照不是可解析的 JSON：{exc}",
              "next": "运行 make deliver 重新读取飞书权限。"}, 1)
    permission_public = (
        (snapshot_payload.get("data") or {}).get("permission_public")
        if isinstance(snapshot_payload, dict)
        else None
    )
    if not isinstance(permission_public, dict) or lark_result.get("permission_public") != permission_public:
        emit({"status": "BLOCKED", "stage": "deliver",
              "reason": "lark_check.json 的 permission_public 与权限快照不一致或字段缺失。",
              "next": "运行 make deliver 重新读取并校验飞书权限。"}, 1)
    permission_mode = str(lark_result.get("permission_mode") or "")
    if permission_mode == "non_public":
        permission_ok = (
            permission_public.get("external_access") is False
            and permission_public.get("link_share_entity") == "closed"
        )
    elif permission_mode == "public_anyone_readable":
        permission_ok = (
            permission_public.get("external_access") is True
            and permission_public.get("link_share_entity") == "anyone_readable"
        )
    else:
        permission_ok = False
    if not permission_ok:
        emit({"status": "BLOCKED", "stage": "deliver",
              "reason": f"飞书权限快照不符合 permission_mode={permission_mode!r} 的交付合同。",
              "next": "按授权模式修正权限后重新运行 make deliver 并读回。"}, 1)

    emit({"status": "PASS", "stage": "deliver",
          "reason": "写作检查通过，飞书文档已创建并读回校验通过。",
          "verification": note}, 0)


if __name__ == "__main__":
    main()
