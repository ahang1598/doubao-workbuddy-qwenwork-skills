#!/usr/bin/env python3
"""Focused workflow checks for doubao-creative-drama.

The lint gate only checks deterministic workflow relationships: types, enums,
IDs, durations, declared files, references, stage order, and exact prompt media
markers. It does not score natural-language wording, creative quality, pacing,
performance, visual quality, or other subjective content.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import unquote


STAGES = ("planning", "script", "assets", "storyboard", "keyframes", "video", "final")
EPISODE_STAGES = set(STAGES[1:])
STATUS_VALUES = {"pending", "in_progress", "awaiting_confirmation", "confirmed", "merged", "invalidated", "blocked"}
ASSET_STATUS_VALUES = {"draft", "reviewed", "approved", "rejected", "superseded"}
VISUAL_REFERENCE_DECISIONS = {"used", "none_available", "explicit_user_override"}
PROJECT_VISUAL_MODES = {"live_action", "photoreal", "2d_comic", "anime", "ink_animation", "illustration", "stylized_3d", "mixed_with_explicit_scope"}
VIDEO_STATUS_VALUES = {"candidate", "accepted", "rejected", "blocked"}
VIDEO_TOOL_MODES = {"text_to_video", "media_to_video", "image_to_video", "video_edit"}
IMAGE_GENERATION_TOOLS = {"image_gen", "image_edit"}
FORBIDDEN_TOOL_TERMS = ("ffmpeg", "text_to_image")
DEFAULT_MEDIA_VIDEO_TOTAL_LIMIT_S = 14
DEFAULT_MEDIA_AUDIO_TOTAL_LIMIT_S = 15
SEEDANCE25_MEDIA_VIDEO_TOTAL_LIMIT_S = 28
SEEDANCE25_MEDIA_AUDIO_TOTAL_LIMIT_S = 30
EPISODE_KEYFRAME_MIN = 3
EPISODE_KEYFRAME_MAX = 4
SEGMENT_KEYFRAME_MAX = 2

REFERENCE_ROLES = {
    "previous_tail_as_start_frame",
    "previous_scene_anchor_reference",
    "previous_character_state_reference",
    "previous_prop_state_reference",
    "segment_highlight_reference",
    "identity_reference",
    "character_state_reference",
    "scene_layout",
    "prop_structure",
    "prop_state_reference",
    "style_reference",
}
VIDEO_INPUT_ROLES = {
    "previous_segment_video_reference",
    "style_video_reference",
    "character_video_reference",
    "scene_video_reference",
    "source_video_for_edit",
}
AUDIO_INPUT_ROLES = {
    "voice_audio_reference",
    "music_reference",
    "sound_effect_reference",
    "ambient_reference",
}
STATE_REFERENCE_ROLES = {"character_state_reference", "prop_state_reference"}
ASSET_PREFIX_BY_CATEGORY = {
    "character": "CHR",
    "scene": "SCN",
    "prop": "PROP",
    "voice": "VOICE",
    "style": "STYLE",
}
MERGEABLE_LIGHTWEIGHT_STAGES = {"script", "assets", "storyboard", "keyframes", "video"}
CURRENT_STAGE_ACTIVE_VALUES = {"in_progress", "awaiting_confirmation", "invalidated", "blocked"}
CONFIRMATION_MODES = {"full", "incremental"}
IMAGE_INPUT_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
ISO_TIME_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})")


def issue(level: str, code: str, message: str, path: Path | None = None, hint: str = "") -> dict[str, Any]:
    data: dict[str, Any] = {"level": level, "code": code, "message": message, "hint": hint}
    if path is not None:
        data["path"] = str(path)
    return data


def load_json(path: Path, issues: list[dict[str, Any]], required: bool = True) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        if required:
            issues.append(issue("error", "file_missing", "缺少流程所需文件。", path))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        issues.append(issue("error", "json_invalid", f"JSON 无法读取或解析，后续关系无法确认：{exc}", path))
    return None


def relative_file(root: Path, value: Any) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    rel = Path(value)
    if rel.is_absolute() or ".." in rel.parts:
        return None
    try:
        target = (root / rel).resolve()
        target.relative_to(root.resolve())
    except (OSError, ValueError):
        return None
    return target


def file_exists(root: Path, value: Any) -> bool:
    target = relative_file(root, value)
    return target is not None and target.is_file()


def parse_iso_time(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not ISO_TIME_PATTERN.fullmatch(text):
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def nonempty_strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def has_meaningful_value(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return bool(value) and all(has_meaningful_value(item) for item in value)
    if isinstance(value, dict):
        return bool(value) and any(has_meaningful_value(item) for item in value.values())
    return False


def combined_strings(*owners: Any, field: str) -> list[str]:
    values: list[str] = []
    for owner in owners:
        if isinstance(owner, dict):
            values.extend(nonempty_strings(owner.get(field)))
    return values


def check_style_anchor_contract(
    root: Path,
    owner_path: Path,
    owner_label: str,
    tool: Any,
    prompt_path_value: Any,
    style_anchor_refs: list[str],
    terms: list[str],
    adopt: list[str],
    exclude: list[str],
    issues: list[dict[str, Any]],
    visual_reference_decision: Any = None,
) -> None:
    if not style_anchor_refs:
        return
    if tool != "image_edit":
        issues.append(issue("error", "style_anchor_requires_image_edit", f"{owner_label} 使用 style_anchor_reference 时必须走 image_edit。", owner_path))
    if visual_reference_decision == "none_available":
        issues.append(issue("error", "style_anchor_visual_reference_decision_conflict", f"{owner_label} 使用 style_anchor_reference 时 visual_reference_decision 不能写 none_available。", owner_path))
    if not terms:
        issues.append(issue("error", "style_prompt_terms_missing", f"{owner_label} 使用 style_anchor_reference 时 style_prompt_terms 必须是非空字符串数组。", owner_path))
    if not adopt:
        issues.append(issue("error", "style_adopt_missing", f"{owner_label} 使用 style_anchor_reference 时 style_adopt 必须是非空字符串数组。", owner_path))
    if not exclude:
        issues.append(issue("error", "style_exclude_missing", f"{owner_label} 使用 style_anchor_reference 时 style_exclude 必须是非空字符串数组。", owner_path))
    prompt_path = relative_file(root, prompt_path_value)
    if prompt_path is None:
        issues.append(issue("error", "style_prompt_path_missing", f"{owner_label} 使用 style_anchor_reference 时必须登记项目相对 prompt_path。", owner_path))
    elif not prompt_path.is_file():
        issues.append(issue("error", "style_prompt_file_missing", f"{owner_label} style_anchor_reference 对应 Prompt 文件不存在。", prompt_path))


def check_generation_prompt_file(
    root: Path,
    owner_path: Path,
    owner_label: str,
    tool: Any,
    prompt_path_value: Any,
    issues: list[dict[str, Any]],
) -> None:
    if tool not in IMAGE_GENERATION_TOOLS:
        return
    prompt_path = relative_file(root, prompt_path_value)
    if prompt_path is None:
        issues.append(issue("error", "generation_prompt_path_missing", f"{owner_label} 使用 {tool} 生成图片时必须登记项目相对 prompt_path。", owner_path))
    elif not prompt_path.is_file():
        issues.append(issue("error", "generation_prompt_file_missing", f"{owner_label} 生成图片 Prompt 文件不存在。", prompt_path))
    else:
        try:
            prompt_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            issues.append(issue("error", "generation_prompt_unreadable", f"{owner_label} 生成图片 Prompt 无法读取：{exc}", prompt_path))


def file_inside(root: Path, value: Any, directory: Path) -> bool:
    target = relative_file(root, value)
    if target is None or not target.is_file():
        return False
    try:
        target.relative_to(directory.resolve())
    except ValueError:
        return False
    return True


def expected_duration_display(seconds: int | float) -> str:
    total = int(round(float(seconds)))
    if total <= 60:
        return f"{total}秒"
    minutes, rest = divmod(total, 60)
    return f"{minutes}分钟" if rest == 0 else f"{minutes}分{rest}秒"


def expected_total_duration_display(seconds: int | float) -> str:
    total = int(round(float(seconds)))
    natural = expected_duration_display(total)
    return natural if total <= 60 else f"{total}秒/{natural}"


def check_duration_pair(
    seconds: Any,
    display: Any,
    path: Path,
    label: str,
    issues: list[dict[str, Any]],
    *,
    total_display: bool = False,
) -> None:
    if not isinstance(seconds, (int, float)) or isinstance(seconds, bool):
        issues.append(issue("error", "duration_invalid", f"{label} duration_s 必须是数字。", path))
        return
    if isinstance(display, str) and display.strip():
        expected = expected_total_duration_display(seconds) if total_display else expected_duration_display(seconds)
        if display != expected:
            issues.append(issue("error", "duration_display_invalid", f"{label} duration_display 应为 {expected}。", path))


def check_unique(items: list[Any], field: str, path: Path, issues: list[dict[str, Any]], scope: str) -> set[str]:
    seen: set[str] = set()
    values: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        value = item.get(field)
        if not isinstance(value, str) or not value.strip():
            issues.append(issue("error", f"{field}_missing", f"{scope} 缺少 {field}。", path))
            continue
        if value in seen:
            issues.append(issue("error", f"{field}_duplicate", f"{scope} 中 {field} 重复：{value}", path))
        seen.add(value)
        values.add(value)
    return values


def manifest_path(root: Path, episode_id: str, stage: str) -> Path | None:
    episode_root = root / "episodes" / episode_id
    paths = {
        "script": episode_root / f"01_剧本/script_contract_{episode_id}.json",
        "assets": episode_root / f"03_资产/asset_usage_{episode_id}.json",
        "storyboard": episode_root / f"02_分镜/storyboard_{episode_id}.json",
        "keyframes": episode_root / f"03_资产/keyframe_manifest_{episode_id}.json",
        "video": episode_root / f"04_视频片段/video_manifest_{episode_id}.json",
        "final": episode_root / f"05_成片/delivery_manifest_{episode_id}.json",
    }
    return paths.get(stage)


def check_episode_directories(root: Path, expected_durations: dict[str, int], issues: list[dict[str, Any]]) -> None:
    if not expected_durations:
        return
    expected = set(expected_durations)
    actual = {episode_id for episode_id, _ in episode_dirs(root)}
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    episodes_root = root / "episodes"
    if missing:
        issues.append(issue("error", "episode_directory_missing", f"计划内分集缺少目录：{missing}", episodes_root))
    if extra:
        issues.append(issue("error", "episode_directory_unplanned", f"存在计划外分集目录：{extra}", episodes_root))


def check_episode_manifest_ids(root: Path, stage: str, issues: list[dict[str, Any]], episode_filter: str | None = None) -> None:
    for episode_id, _ in episode_dirs(root, episode_filter):
        path = manifest_path(root, episode_id, stage)
        if path is None or not path.exists():
            continue
        data = load_json(path, issues, required=False)
        if isinstance(data, dict) and data.get("episode_id") != episode_id:
            issues.append(issue("error", "episode_id_mismatch", f"{stage} episode_id 必须等于目录 ID：{episode_id}", path))


def check_episode_entry_manifests(root: Path, issues: list[dict[str, Any]], lightweight: bool = False) -> None:
    for episode_id, episode_root in episode_dirs(root):
        path = episode_root / f"episode_manifest_{episode_id}.json"
        data = load_json(path, issues, required=True)
        if not isinstance(data, dict):
            continue
        if data.get("episode_id") != episode_id:
            issues.append(issue("error", "episode_id_mismatch", f"episode_manifest episode_id 必须等于目录 ID：{episode_id}", path))
        stage_manifests = data.get("stage_manifests")
        if not isinstance(stage_manifests, dict):
            issues.append(issue("error", "stage_manifests_missing", "episode_manifest 必须使用顶层 stage_manifests，不得使用旧字段 manifests。", path))
            continue
        if lightweight:
            expected = {
                "script": "",
                "storyboard": f"episodes/{episode_id}/02_分镜/分镜_完整分镜表_{episode_id}.md",
                "assets": "",
                "keyframes": "",
                "video": f"episodes/{episode_id}/04_视频片段/video_manifest_{episode_id}.json",
                "continuity": "",
                "delivery": f"episodes/{episode_id}/05_成片/delivery_manifest_{episode_id}.json",
            }
        else:
            expected = {
                "script": f"episodes/{episode_id}/01_剧本/script_contract_{episode_id}.json",
                "storyboard": f"episodes/{episode_id}/02_分镜/storyboard_{episode_id}.json",
                "assets": f"episodes/{episode_id}/03_资产/asset_usage_{episode_id}.json",
                "keyframes": f"episodes/{episode_id}/03_资产/keyframe_manifest_{episode_id}.json",
                "video": f"episodes/{episode_id}/04_视频片段/video_manifest_{episode_id}.json",
                "continuity": f"episodes/{episode_id}/04_视频片段/continuity_{episode_id}.json",
                "delivery": f"episodes/{episode_id}/05_成片/delivery_manifest_{episode_id}.json",
            }
        for stage, expected_path in expected.items():
            if stage_manifests.get(stage) != expected_path:
                issues.append(issue("error", "stage_manifest_path_invalid", f"episode_manifest.stage_manifests.{stage} 必须指向 {expected_path}。", path))


def plan_revision(plan: Any, state: dict[str, Any]) -> int | None:
    for source in (state, plan if isinstance(plan, dict) else {}):
        value = source.get("revision") if isinstance(source, dict) else None
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    return None


def is_lightweight_plan(plan: Any) -> bool:
    return isinstance(plan, dict) and isinstance(plan.get("objective"), dict) and plan["objective"].get("workflow_mode") == "lightweight"


def lightweight_constraints_valid(plan: Any) -> bool:
    if not isinstance(plan, dict):
        return False
    scale = plan.get("scale_plan") if isinstance(plan.get("scale_plan"), dict) else {}
    count = scale.get("episode_count")
    total = scale.get("total_duration_s")
    if count != 1 or not isinstance(total, (int, float)) or isinstance(total, bool):
        return False
    model_plan = plan.get("model_plan") if isinstance(plan.get("model_plan"), dict) else {}
    video_plan = model_plan.get("video") if isinstance(model_plan.get("video"), dict) else {}
    model_text = " ".join(
        str(video_plan.get(key) or "")
        for key in ("model", "name", "user_requested_model", "display_name")
    ).lower()
    limit_s = 30 if "seedance 2.5" in model_text else 15
    return float(total) <= limit_s


def target_stage(plan: Any) -> str | None:
    objective = plan.get("objective") if isinstance(plan, dict) else None
    value = objective.get("target_stage") if isinstance(objective, dict) else None
    return value if value in STAGES else None


def load_confirmation_records(
    root: Path,
    issues: list[dict[str, Any]],
    required: bool,
    require_planning_interaction: bool = False,
    lightweight: bool = False,
) -> list[dict[str, Any]]:
    path = root / "00_制作控制/用户确认记录.jsonl"
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        if required:
            issues.append(issue("error", "confirmation_log_missing", "阶段已确认或推进到后续阶段时必须存在用户确认记录。", path))
        return []
    except (OSError, UnicodeError) as exc:
        issues.append(issue("error", "confirmation_log_unreadable", f"用户确认记录无法读取：{exc}", path))
        return []

    records: list[dict[str, Any]] = []
    full_revisions_by_scope: dict[tuple[str, str], set[int]] = {}
    interaction_call_ids: dict[str, tuple[str, str, str]] = {}
    for line_number, line in enumerate(raw.splitlines(), start=1):
        if not line.strip():
            issues.append(issue("error", "confirmation_log_blank_line", f"用户确认记录第 {line_number} 行为空行。", path))
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError as exc:
            issues.append(issue("error", "confirmation_log_json_invalid", f"用户确认记录第 {line_number} 行不是有效 JSON：{exc}", path))
            continue
        if not isinstance(data, dict):
            issues.append(issue("error", "confirmation_log_row_invalid", f"用户确认记录第 {line_number} 行必须是对象。", path))
            continue
        stage = data.get("stage")
        if stage not in STAGES:
            issues.append(issue("error", "confirmation_stage_invalid", f"用户确认记录第 {line_number} 行 stage 无效。", path))
        episode_id = str(data.get("episode_id") or "")
        if episode_id and not re.fullmatch(r"ep_[1-9]\d*", episode_id):
            issues.append(issue("error", "confirmation_episode_id_invalid", f"用户确认记录第 {line_number} 行 episode_id 无效。", path))
        if stage == "planning" and episode_id:
            issues.append(issue("error", "project_confirmation_has_episode", f"用户确认记录第 {line_number} 行 planning 阶段不得填写 episode_id。", path))
        if stage in EPISODE_STAGES - {"script"} and not episode_id:
            issues.append(issue("error", "episode_confirmation_missing_episode_id", f"用户确认记录第 {line_number} 行 {stage} 阶段必须填写 episode_id。", path))
        if data.get("decision") != "confirmed":
            issues.append(issue("error", "confirmation_decision_invalid", f"用户确认记录第 {line_number} 行 decision 必须是 confirmed。", path))
        if data.get("confirmation_mode") not in CONFIRMATION_MODES:
            issues.append(issue("error", "confirmation_mode_invalid", f"用户确认记录第 {line_number} 行 confirmation_mode 无效。", path))
        if not isinstance(data.get("revision"), int) or isinstance(data.get("revision"), bool):
            issues.append(issue("error", "confirmation_revision_invalid", f"用户确认记录第 {line_number} 行 revision 必须是整数。", path))
        if not str(data.get("user_message") or "").strip():
            issues.append(issue("error", "confirmation_user_message_missing", f"用户确认记录第 {line_number} 行 user_message 不能为空。", path))
        confirmed_at = str(data.get("confirmed_at") or "")
        if parse_iso_time(confirmed_at) is None:
            issues.append(issue("error", "confirmation_time_invalid", f"用户确认记录第 {line_number} 行 confirmed_at 必须是带时区 ISO-8601 时间。", path))
        call_id = str(data.get("interaction_ask_call_id") or "").strip()
        if call_id:
            purpose_key = (str(data.get("confirmation_purpose") or ""), str(data.get("interaction_ask_result") or ""), f"{stage}:{episode_id}")
            previous_purpose = interaction_call_ids.get(call_id)
            if previous_purpose is not None and previous_purpose != purpose_key:
                issues.append(issue("error", "interaction_call_id_reused", f"用户确认记录第 {line_number} 行 interaction_ask_call_id 已被其他用途使用。", path))
            interaction_call_ids[call_id] = purpose_key
        if data.get("confirmation_mode") == "incremental":
            base_revision = data.get("base_revision")
            if not isinstance(base_revision, int) or isinstance(base_revision, bool):
                issues.append(issue("error", "confirmation_base_revision_invalid", f"用户确认记录第 {line_number} 行 incremental 必须填写整数 base_revision。", path))
            elif base_revision not in full_revisions_by_scope.get((str(stage), episode_id), set()):
                issues.append(issue("error", "confirmation_base_revision_missing", f"用户确认记录第 {line_number} 行找不到同阶段对应的全量确认 base_revision。", path))
            if not isinstance(data.get("changed_artifacts"), list) or not data.get("changed_artifacts"):
                issues.append(issue("error", "confirmation_changed_artifacts_missing", f"用户确认记录第 {line_number} 行 incremental 必须填写 changed_artifacts。", path))
            if not isinstance(data.get("impact_scope"), list) or not data.get("impact_scope"):
                issues.append(issue("error", "confirmation_impact_scope_missing", f"用户确认记录第 {line_number} 行 incremental 必须填写 impact_scope。", path))
        elif data.get("confirmation_mode") == "full" and isinstance(data.get("revision"), int) and not isinstance(data.get("revision"), bool):
            full_revisions_by_scope.setdefault((str(stage), episode_id), set()).add(data["revision"])
        records.append(data)
    if require_planning_interaction:
        planning_records = [record for record in records if record.get("stage") == "planning"]
        latest_revision = max(
            (
                record.get("revision")
                for record in planning_records
                if isinstance(record.get("revision"), int) and not isinstance(record.get("revision"), bool)
            ),
            default=None,
        )
        latest_records = [record for record in planning_records if record.get("revision") == latest_revision]
        expected_purpose = "video_generation" if lightweight else "project_execution"
        expected_result = "generate" if lightweight else "proceed_project"
        if not any(
            record.get("confirmation_purpose") == expected_purpose
            and str(record.get("interaction_ask_call_id") or "").strip()
            and record.get("interaction_ask_result") == expected_result
            for record in latest_records
        ):
            issues.append(issue("error", "planning_interaction_confirmation_missing", f"最新 planning 确认必须记录 {expected_purpose}、真实 interaction_ask_call_id 和 {expected_result}。", path))
    return records


def check_operation_log_tools(root: Path, issues: list[dict[str, Any]]) -> None:
    path = root / "00_制作控制/操作日志.jsonl"
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return
    except (OSError, UnicodeError) as exc:
        issues.append(issue("error", "operation_log_unreadable", f"操作日志无法读取：{exc}", path))
        return
    for line_number, line in enumerate(raw.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        tool_name = str(data.get("tool") or "").strip().lower()
        if tool_name in FORBIDDEN_TOOL_TERMS:
            issues.append(issue("error", "forbidden_media_tool_used", f"操作日志第 {line_number} 行登记了禁用工具 {tool_name}；媒体处理必须使用 mediakit。", path))


def has_confirmation(
    records: list[dict[str, Any]],
    stage: str,
    revision: int | None,
    episode_id: str | None = None,
) -> bool:
    for record in records:
        if record.get("stage") != stage or record.get("decision") != "confirmed":
            continue
        if revision is not None and record.get("revision") != revision:
            continue
        record_episode = str(record.get("episode_id") or "")
        if episode_id is not None and record_episode != episode_id:
            continue
        if episode_id is None and record_episode:
            continue
        if str(record.get("user_message") or "").strip():
            return True
    return False


def check_state(root: Path, plan: Any, issues: list[dict[str, Any]]) -> None:
    state_path = root / "00_制作控制/制作状态.json"
    state = load_json(state_path, issues, required=False)
    if not isinstance(state, dict):
        return
    current = state.get("current_stage")
    current_episode = state.get("current_episode")
    phases = state.get("phases")
    if current not in STAGES:
        issues.append(issue("error", "current_stage_invalid", "current_stage 不是有效阶段。", state_path))
    if not isinstance(phases, dict):
        issues.append(issue("error", "phases_invalid", "phases 必须是对象。", state_path))
        return
    revision = plan_revision(plan, state)
    lightweight = is_lightweight_plan(plan)
    lightweight_valid = lightweight and lightweight_constraints_valid(plan)
    target = target_stage(plan)
    objective = plan.get("objective") if isinstance(plan, dict) else {}
    if not isinstance(objective, dict) or objective.get("target_stage") not in STAGES:
        issues.append(issue("error", "target_stage_invalid", "drama_plan.objective.target_stage 必须是有效阶段。", state_path))
    episode_ids = [episode_id for episode_id, _ in episode_dirs(root)]
    needs_confirmations = False
    for stage in STAGES:
        value = phases.get(stage)
        if value not in STATUS_VALUES:
            issues.append(issue("error", "phase_status_invalid", f"{stage} 状态无效。", state_path))
        if value == "confirmed":
            needs_confirmations = True
    project_level_stage = current == "planning" or (current == "script" and current_episode in {None, ""})
    if project_level_stage:
        if current_episode not in {None, ""}:
            issues.append(issue("error", "current_episode_must_be_empty", f"current_stage={current} 时 current_episode 必须为空。", state_path))
        current_index = STAGES.index(current)
        for index, stage in enumerate(STAGES):
            value = phases.get(stage)
            if index < current_index and value not in {"confirmed", "merged"}:
                issues.append(issue("error", "phase_order_invalid", f"{stage} 应先完成后再进入 {current}。", state_path))
            if index > current_index and value not in {"pending", "invalidated"}:
                issues.append(issue("error", "future_phase_status_invalid", f"{stage} 晚于 current_stage={current}，只能是 pending 或 invalidated。", state_path))
            if index == current_index:
                allowed_current = set(CURRENT_STAGE_ACTIVE_VALUES)
                if current == "final" or current == target:
                    allowed_current.add("confirmed")
                if lightweight_valid and stage in MERGEABLE_LIGHTWEIGHT_STAGES:
                    allowed_current.add("merged")
                if value not in allowed_current:
                    issues.append(issue("error", "current_phase_status_invalid", f"{stage} 是 current_stage，状态不能是 {value}。", state_path))
            if value == "merged" and (not lightweight_valid or stage not in MERGEABLE_LIGHTWEIGHT_STAGES):
                issues.append(issue("error", "phase_merged_invalid", f"{stage} 不能标记为 merged。", state_path))
        if current_index > 0:
            needs_confirmations = True
    elif current in EPISODE_STAGES:
        if current_episode not in episode_ids:
            issues.append(issue("error", "current_episode_invalid", "逐集生产阶段必须把 current_episode 指向计划内分集。", state_path))
        if target in STAGES and STAGES.index(current) > STAGES.index(target):
            issues.append(issue("error", "current_stage_beyond_target", f"current_stage={current} 不得晚于 objective.target_stage={target}。", state_path))
        if phases.get("planning") != "confirmed":
            issues.append(issue("error", "project_prerequisite_not_confirmed", "进入逐集生产前 phases.planning 必须为 confirmed。", state_path))
        allowed_script_statuses = {"confirmed", "merged"} if lightweight_valid else {"confirmed"}
        if phases.get("script") not in allowed_script_statuses:
            issues.append(issue("error", "project_prerequisite_not_confirmed", "进入逐集生产前项目级 phases.script 必须为 confirmed；合法轻量模式可为 merged。", state_path))
        for stage in STAGES[2:]:
            value = phases.get(stage)
            if value == "merged" and (not lightweight_valid or stage not in MERGEABLE_LIGHTWEIGHT_STAGES):
                issues.append(issue("error", "phase_merged_invalid", f"{stage} 不能标记为 merged。", state_path))
        needs_confirmations = True
    if lightweight and not lightweight_valid:
        issues.append(issue("error", "lightweight_scope_invalid", "lightweight 只允许单集，且总时长不得超过当前视频模型轻量上限：seedance 2.0 系列 15 秒，seedance 2.5 为 30 秒。", state_path))
    confirmations = load_confirmation_records(
        root,
        issues,
        needs_confirmations,
        require_planning_interaction=target in {"video", "final"},
        lightweight=lightweight_valid,
    )
    for stage in ("planning", "script"):
        value = phases.get(stage)
        required_revision = revision if stage == current and current_episode in {None, ""} else None
        if value == "confirmed" and not has_confirmation(confirmations, stage, required_revision):
            detail = "同阶段、同 revision" if stage == current else "同阶段"
            issues.append(issue("error", "phase_confirmation_missing", f"{stage} 已 confirmed，但缺少{detail}的有效用户确认记录。", state_path))
    episodes = state.get("episodes")
    if not isinstance(episodes, dict):
        issues.append(issue("error", "episode_states_invalid", "制作状态.json.episodes 必须是对象并覆盖全部计划分集。", state_path))
        return
    state_episode_ids = set(episodes)
    expected_episode_ids = set(episode_ids)
    if state_episode_ids != expected_episode_ids:
        missing = sorted(expected_episode_ids - state_episode_ids)
        extra = sorted(state_episode_ids - expected_episode_ids)
        if missing:
            issues.append(issue("error", "episode_states_missing", f"制作状态.json.episodes 缺少计划分集：{missing}", state_path))
        if extra:
            issues.append(issue("error", "episode_states_unplanned", f"制作状态.json.episodes 包含计划外分集：{extra}", state_path))
    if isinstance(episodes, dict):
        for episode_id, episode_state in episodes.items():
            if not re.fullmatch(r"ep_[1-9]\d*", str(episode_id)):
                issues.append(issue("error", "episode_id_invalid", f"分集 ID 无效：{episode_id}", state_path))
            statuses = episode_state.get("stage_status") if isinstance(episode_state, dict) else None
            if not isinstance(statuses, dict):
                issues.append(issue("error", "episode_stage_statuses_invalid", f"{episode_id}.stage_status 必须是对象。", state_path))
                continue
            missing_stages = [stage for stage in EPISODE_STAGES if stage not in statuses]
            if missing_stages:
                issues.append(issue("error", "episode_stage_statuses_missing", f"{episode_id}.stage_status 缺少阶段：{missing_stages}", state_path))
            if isinstance(statuses, dict):
                for stage, value in statuses.items():
                    if stage in EPISODE_STAGES and value not in STATUS_VALUES:
                        issues.append(issue("error", "episode_stage_status_invalid", f"{episode_id}.{stage} 状态无效。", state_path))
                    if stage in EPISODE_STAGES and value == "merged" and (not lightweight_valid or stage not in MERGEABLE_LIGHTWEIGHT_STAGES):
                        issues.append(issue("error", "episode_phase_merged_invalid", f"{episode_id}.{stage} 不能标记为 merged。", state_path))
                if current == "planning":
                    for stage in EPISODE_STAGES:
                        value = statuses.get(stage)
                        if value is not None and value not in {"pending", "invalidated"}:
                            issues.append(issue("error", "episode_stage_before_planning_confirmed", f"项目仍在 planning，{episode_id}.{stage} 只能是 pending 或 invalidated。", state_path))
                elif current == "script" and current_episode in {None, ""}:
                    script_value = statuses.get("script")
                    if script_value not in {"pending", "invalidated"}:
                        issues.append(issue("error", "episode_script_started_before_global_confirmation", f"{episode_id}.script 在项目级故事包确认前只能是 pending 或 invalidated。", state_path))
                    for stage in STAGES[2:]:
                        value = statuses.get(stage)
                        if value is not None and value not in {"pending", "invalidated"}:
                            issues.append(issue("error", "episode_stage_before_script_confirmed", f"项目级故事包尚未确认，{episode_id}.{stage} 只能是 pending 或 invalidated。", state_path))
                elif current in EPISODE_STAGES and current_episode in episode_ids:
                    episode_position = episode_ids.index(episode_id) if episode_id in episode_ids else -1
                    active_position = episode_ids.index(str(current_episode))
                    if episode_position < active_position:
                        completed_through = STAGES.index(target) if target in EPISODE_STAGES else STAGES.index("final")
                        for stage in EPISODE_STAGES:
                            stage_index = STAGES.index(stage)
                            if stage_index <= completed_through:
                                allowed_completed = {"confirmed", "merged"} if lightweight_valid and stage in MERGEABLE_LIGHTWEIGHT_STAGES else {"confirmed"}
                                if statuses.get(stage) not in allowed_completed:
                                    issues.append(issue("error", "previous_episode_incomplete", f"{episode_id}.{stage} 必须完成后才能推进 {current_episode}。", state_path))
                            elif statuses.get(stage) not in {"pending", "invalidated"}:
                                issues.append(issue("error", "previous_episode_beyond_target", f"{episode_id}.{stage} 超出 target_stage={target}，只能是 pending 或 invalidated。", state_path))
                    elif episode_position > active_position:
                        if statuses.get("script") not in {"pending", "invalidated"}:
                            issues.append(issue("error", "future_episode_script_started_early", f"{episode_id}.script 在该集开始制作前只能是 pending 或 invalidated。", state_path))
                        for stage in STAGES[2:]:
                            if statuses.get(stage) not in {"pending", "invalidated"}:
                                issues.append(issue("error", "future_episode_started_early", f"{episode_id}.{stage} 在 {current_episode} 达到目标前只能是 pending 或 invalidated。", state_path))
                    else:
                        current_episode_index = STAGES.index(current)
                        if current != "script" and statuses.get("script") not in allowed_script_statuses:
                            issues.append(issue("error", "current_episode_script_incomplete", f"{episode_id}.script 必须在后续生产前确认为 confirmed；合法轻量模式可为 merged。", state_path))
                        for stage in EPISODE_STAGES:
                            value = statuses.get(stage)
                            index = STAGES.index(stage)
                            if index < current_episode_index and value not in {"confirmed", "merged"}:
                                issues.append(issue("error", "episode_phase_order_invalid", f"{episode_id}.{stage} 应先完成后再进入 {current}。", state_path))
                            if index > current_episode_index and value not in {"pending", "invalidated"}:
                                issues.append(issue("error", "episode_future_phase_status_invalid", f"{episode_id}.{stage} 晚于当前集 current_stage={current}，只能是 pending 或 invalidated。", state_path))
                            if index == current_episode_index:
                                allowed_current = set(CURRENT_STAGE_ACTIVE_VALUES)
                                current_is_last_episode = episode_position == len(episode_ids) - 1
                                if current_is_last_episode and current in {"final", target}:
                                    allowed_current.add("confirmed")
                                if lightweight_valid and stage in MERGEABLE_LIGHTWEIGHT_STAGES:
                                    allowed_current.add("merged")
                                if value not in allowed_current:
                                    issues.append(issue("error", "episode_current_phase_status_invalid", f"{episode_id}.{stage} 是当前集阶段，状态不能是 {value}。", state_path))
                for stage in EPISODE_STAGES:
                    if statuses.get(stage) != "confirmed":
                        continue
                    if stage == "script":
                        if not has_confirmation(confirmations, "script", None, episode_id):
                            issues.append(issue("error", "episode_script_confirmation_missing", f"{episode_id}.script 已 confirmed，但缺少绑定该集的详细剧本确认记录。", state_path))
                        continue
                    required_revision = revision if episode_id == current_episode and stage == current else None
                    if not has_confirmation(
                        confirmations,
                        stage,
                        required_revision,
                        episode_id,
                    ):
                        issues.append(issue("error", "episode_confirmation_missing", f"{episode_id}.{stage} 已 confirmed，但缺少绑定该集的有效确认记录。", state_path))
        for stage in STAGES[2:]:
            if phases.get(stage) != "confirmed":
                continue
            stage_values = [
                episode_state.get("stage_status", {}).get(stage)
                for episode_state in episodes.values()
                if isinstance(episode_state, dict) and isinstance(episode_state.get("stage_status"), dict)
            ]
            if not stage_values or any(value not in {"confirmed", "merged"} for value in stage_values):
                issues.append(issue("error", "aggregate_phase_confirmed_early", f"phases.{stage} 只有在全部分集该阶段完成后才能写 confirmed。", state_path))
        if current in EPISODE_STAGES and current_episode in episodes:
            current_statuses = episodes[current_episode].get("stage_status") if isinstance(episodes[current_episode], dict) else {}
            current_index = STAGES.index(current)
            for stage in STAGES[2:]:
                phase_value = phases.get(stage)
                stage_index = STAGES.index(stage)
                completed_values = {"confirmed", "merged"} if lightweight_valid and stage in MERGEABLE_LIGHTWEIGHT_STAGES else {"confirmed"}
                all_completed = all(
                    isinstance(episode_state, dict)
                    and isinstance(episode_state.get("stage_status"), dict)
                    and episode_state["stage_status"].get(stage) in completed_values
                    for episode_state in episodes.values()
                )
                any_completed = any(
                    isinstance(episode_state, dict)
                    and isinstance(episode_state.get("stage_status"), dict)
                    and episode_state["stage_status"].get(stage) in completed_values
                    for episode_state in episodes.values()
                )
                if all_completed:
                    if phase_value != "confirmed" and not (lightweight_valid and stage in MERGEABLE_LIGHTWEIGHT_STAGES and phase_value == "merged"):
                        issues.append(issue("error", "aggregate_phase_status_mismatch", f"phases.{stage} 必须反映全部分集已完成。", state_path))
                elif stage == current:
                    current_value = current_statuses.get(stage) if isinstance(current_statuses, dict) else None
                    if phase_value != current_value:
                        issues.append(issue("error", "aggregate_current_phase_mismatch", f"phases.{stage} 必须与 {current_episode}.{stage} 当前活动状态一致。", state_path))
                elif stage_index > current_index and phase_value not in ({"pending", "invalidated", "in_progress"} if any_completed else {"pending", "invalidated"}):
                    issues.append(issue("error", "aggregate_future_phase_started", f"phases.{stage} 与已完成分集的聚合状态不一致。", state_path))
                elif stage_index < current_index and phase_value not in {"in_progress", "confirmed", "merged"}:
                    issues.append(issue("error", "aggregate_previous_phase_invalid", f"phases.{stage} 已有分集完成但尚未全量完成，必须保持 in_progress 或合法完成态。", state_path))


def episode_dirs(root: Path, episode_filter: str | None = None) -> list[tuple[str, Path]]:
    episodes_root = root / "episodes"
    if not episodes_root.is_dir():
        return []
    entries = [
        (child.name, child)
        for child in episodes_root.iterdir()
        if child.is_dir() and re.fullmatch(r"ep_[1-9]\d*", child.name)
        and (episode_filter is None or child.name == episode_filter)
    ]
    return sorted(entries, key=lambda item: int(item[0].split("_", 1)[1]))


def check_stage_artifacts(
    root: Path,
    stage: str,
    issues: list[dict[str, Any]],
    episode_filter: str | None = None,
    lightweight: bool = False,
) -> None:
    required = [root / "00_制作控制/drama_plan.json", root / "00_制作控制/制作状态.json"]
    state = load_json(root / "00_制作控制/制作状态.json", issues, required=False)
    script_status = state.get("phases", {}).get("script") if isinstance(state, dict) and isinstance(state.get("phases"), dict) else None
    script_should_exist = not lightweight or script_status == "confirmed"
    episode_states = state.get("episodes", {}) if isinstance(state, dict) and isinstance(state.get("episodes"), dict) else {}
    if stage == "planning":
        required += [
            root / "00_制作控制/project_manifest.json",
            root / "00_制作控制/source_manifest.json",
            root / "episodes",
        ]
    if stage == "script" and script_should_exist:
        required += [
            root / "00_制作控制/project_data_card.json",
            root / "01_剧本/project_script_manifest.json",
            root / "01_剧本/项目_事实与假设.md",
            root / "01_剧本/项目设定卡.md",
            root / "01_剧本/剧本_全局设定与分集总纲.md",
            root / "01_剧本/剧本_全剧完整剧本.md",
        ]
    if stage in {"assets", "storyboard", "keyframes", "video", "final"} and not lightweight:
        required.append(root / "00_制作控制/project_data_card.json")
    for episode_id, episode_root in episode_dirs(root):
        if episode_filter is not None and episode_id != episode_filter:
            continue
        if stage == "planning":
            required.append(episode_root / f"episode_manifest_{episode_id}.json")
        episode_script_status = (
            episode_states.get(episode_id, {}).get("stage_status", {}).get("script")
            if isinstance(episode_states.get(episode_id), dict)
            and isinstance(episode_states.get(episode_id, {}).get("stage_status"), dict)
            else None
        )
        require_episode_script = (
            not lightweight
            and (
                stage in {"assets", "storyboard", "keyframes", "video", "final"}
                or (
                    stage == "script"
                    and (
                        episode_filter == episode_id
                        or episode_script_status in {"in_progress", "awaiting_confirmation", "confirmed", "blocked"}
                    )
                )
            )
        )
        if require_episode_script:
            required += [
                episode_root / f"01_剧本/script_contract_{episode_id}.json",
                episode_root / f"01_剧本/剧本_分集梗概_{episode_id}.md",
                episode_root / f"01_剧本/剧本_分集人物状态_{episode_id}.md",
                episode_root / f"01_剧本/剧本_人物关系张力矩阵_{episode_id}.md",
                episode_root / f"01_剧本/剧本_分集主要场景_{episode_id}.md",
                episode_root / f"01_剧本/剧本_完整剧本_{episode_id}.md",
            ]
        if stage in {"assets", "storyboard", "keyframes", "video", "final"} and not lightweight:
            required += [root / "shared/03_资产/asset_registry.json", episode_root / f"03_资产/asset_usage_{episode_id}.json"]
        if stage in {"storyboard", "keyframes", "video", "final"} and lightweight:
            required.append(episode_root / f"02_分镜/分镜_完整分镜表_{episode_id}.md")
        elif stage in {"storyboard", "keyframes", "video", "final"}:
            required += [
                episode_root / f"02_分镜/storyboard_{episode_id}.json",
                episode_root / f"02_分镜/分镜_阅读稿_{episode_id}.md",
                episode_root / f"02_分镜/导演总控卡_{episode_id}.md",
                episode_root / f"02_分镜/分镜_完整分镜表_{episode_id}.md",
            ]
        if stage in {"keyframes", "video", "final"} and not lightweight:
            required += [episode_root / f"03_资产/keyframe_manifest_{episode_id}.json"]
        if stage in {"video", "final"}:
            required += [episode_root / f"04_视频片段/video_manifest_{episode_id}.json"]
        if stage == "final":
            required += [episode_root / f"05_成片/delivery_manifest_{episode_id}.json"]
    for path in required:
        if not path.exists():
            issues.append(issue("error", "required_artifact_missing", "缺少当前阶段所需产物。", path))
    if lightweight and stage in {"storyboard", "keyframes", "video", "final"}:
        for episode_id, episode_root in episode_dirs(root, episode_filter):
            storyboard_path = episode_root / f"02_分镜/分镜_完整分镜表_{episode_id}.md"
            if not storyboard_path.is_file():
                continue
            try:
                storyboard_text = storyboard_path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                issues.append(issue("error", "storyboard_source_markdown_unreadable", f"十五列完整分镜表无法读取：{exc}", storyboard_path))
            else:
                if 15 not in markdown_table_column_counts(storyboard_text):
                    issues.append(issue("error", "storyboard_fifteen_columns_missing", "完整分镜表必须包含一个十五列表格。", storyboard_path))
    if stage == "script" and script_should_exist:
        combined_path = root / "01_剧本/剧本_全局设定与分集总纲.md"
        if combined_path.is_file():
            try:
                combined_text = combined_path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                issues.append(issue("error", "combined_story_outline_unreadable", f"合并剧本文档无法读取：{exc}", combined_path))
            else:
                for heading in ("全局故事圣经", "分集推进总纲"):
                    if re.search(rf"^#{{1,6}}\s+{re.escape(heading)}\s*$", combined_text, flags=re.MULTILINE) is None:
                        issues.append(issue("error", "combined_story_outline_section_missing", f"合并剧本文档缺少“{heading}”章节。", combined_path))
        script_manifest_path = root / "01_剧本/project_script_manifest.json"
        script_manifest = load_json(script_manifest_path, issues, required=False)
        if isinstance(script_manifest, dict):
            expected = "01_剧本/剧本_全局设定与分集总纲.md"
            if script_manifest.get("global_story_and_episode_outline") != expected:
                issues.append(issue("error", "combined_story_outline_reference_invalid", f"project_script_manifest.global_story_and_episode_outline 必须指向 {expected}。", script_manifest_path))
        if not lightweight:
            for episode_id, episode_root in episode_dirs(root, episode_filter):
                episode_script_status = (
                    episode_states.get(episode_id, {}).get("stage_status", {}).get("script")
                    if isinstance(episode_states.get(episode_id), dict)
                    and isinstance(episode_states.get(episode_id, {}).get("stage_status"), dict)
                    else None
                )
                if stage == "script" and episode_filter is None and episode_script_status not in {"in_progress", "awaiting_confirmation", "confirmed", "blocked"}:
                    continue
                contract_path = episode_root / f"01_剧本/script_contract_{episode_id}.json"
                contract = load_json(contract_path, issues, required=False)
                if not isinstance(contract, dict):
                    continue
                highlight_ledger = contract.get("highlight_ledger")
                if not isinstance(highlight_ledger, list):
                    issues.append(issue("error", "highlight_ledger_invalid", "完整模式 script_contract.highlight_ledger 必须是数组。", contract_path))
                    continue
                primary_entries = [
                    item
                    for item in highlight_ledger
                    if isinstance(item, dict) and item.get("role") == "primary" and str(item.get("highlight_id") or "").strip()
                ]
                if not primary_entries:
                    issues.append(issue("error", "primary_highlight_missing", "完整模式每集 script_contract.highlight_ledger 必须至少包含一个有效的 primary 亮点。", contract_path))


def check_plan_durations(root: Path, plan: Any, issues: list[dict[str, Any]]) -> dict[str, int]:
    expected: dict[str, int] = {}
    if not isinstance(plan, dict):
        return expected
    path = root / "00_制作控制/drama_plan.json"
    if not isinstance(plan.get("revision"), int) or isinstance(plan.get("revision"), bool) or plan.get("revision") < 1:
        issues.append(issue("error", "plan_revision_invalid", "drama_plan.revision 必须是正整数。", path))
    objective = plan.get("objective")
    if not isinstance(objective, dict) or objective.get("target_stage") not in STAGES:
        issues.append(issue("error", "target_stage_invalid", "drama_plan.objective.target_stage 必须是有效阶段。", path))
    if not str(plan.get("selected_direction_id") or "").strip():
        issues.append(issue("error", "selected_direction_missing", "drama_plan 必须锁定 selected_direction_id。", path))
    creative_mechanism = plan.get("creative_mechanism")
    if not isinstance(creative_mechanism, dict):
        issues.append(issue("error", "creative_mechanism_missing", "drama_plan 必须填写 creative_mechanism。", path))
    else:
        selection_mode = creative_mechanism.get("selection_mode")
        if selection_mode not in {"divergent", "user_locked"}:
            issues.append(issue("error", "creative_mechanism_selection_mode_invalid", "creative_mechanism.selection_mode 必须为 divergent 或 user_locked。", path))
        candidates = creative_mechanism.get("candidates")
        candidate_primaries: list[str] = []
        expected_counts = {3} if selection_mode == "divergent" else {1, 2, 3}
        if not isinstance(candidates, list) or len(candidates) not in expected_counts:
            expected_text = "恰好 3 个" if selection_mode == "divergent" else "1-3 个"
            issues.append(issue("error", "creative_mechanism_candidates_invalid", f"当前 selection_mode 的 creative_mechanism.candidates 必须包含{expected_text}候选。", path))
        else:
            for index, candidate in enumerate(candidates, start=1):
                supporting = candidate.get("supporting") if isinstance(candidate, dict) else None
                if not isinstance(candidate, dict) or not has_meaningful_value(candidate.get("primary")):
                    issues.append(issue("error", "creative_mechanism_primary_missing", f"创意机制候选 {index} 必须填写主机制。", path))
                else:
                    candidate_primaries.append(str(candidate["primary"]).strip())
                if not isinstance(supporting, list) or not 1 <= len(supporting) <= 3:
                    issues.append(issue("error", "creative_mechanism_supporting_invalid", f"创意机制候选 {index} 必须包含 1-3 个同源辅助机制。", path))
        selected_primary = str(creative_mechanism.get("primary") or "").strip()
        if not selected_primary:
            issues.append(issue("error", "creative_mechanism_selected_missing", "creative_mechanism.primary 必须锁定唯一主机制。", path))
        elif candidate_primaries and selected_primary not in candidate_primaries:
            issues.append(issue("error", "creative_mechanism_selected_unknown", "creative_mechanism.primary 必须来自当前候选主机制之一。", path))
        selected_supporting = creative_mechanism.get("supporting")
        if not isinstance(selected_supporting, list) or not 1 <= len(selected_supporting) <= 3:
            issues.append(issue("error", "creative_mechanism_selected_supporting_invalid", "creative_mechanism.supporting 必须保留 1-3 个辅助机制。", path))
    rhythm_design = plan.get("rhythm_design")
    rhythm_fields = ("immutable_nodes", "node_loads", "primary_downbeat", "transition_choices", "duration_allocation", "intensity_sequence", "selected_wave")
    if not isinstance(rhythm_design, dict):
        issues.append(issue("error", "rhythm_design_missing", "drama_plan 必须填写六步推导后的 rhythm_design。", path))
    else:
        for field in rhythm_fields:
            if not has_meaningful_value(rhythm_design.get(field)):
                issues.append(issue("error", "rhythm_design_field_missing", f"rhythm_design.{field} 必须填写。", path))
        intensity = rhythm_design.get("intensity_sequence")
        if isinstance(intensity, list) and any(not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 5 for value in intensity):
            issues.append(issue("error", "rhythm_intensity_invalid", "rhythm_design.intensity_sequence 只能包含 1-5 的整数。", path))
    strategy_contracts = {
        "audience_plan": (
            "target_audience",
            "core_pain_or_desire",
            "platform",
            "evidence_status",
            "viewing_focus",
            "emotional_payoff",
            "platform_viewing_context",
            "expression_boundaries",
        ),
        "type_strategy": ("format", "subject_route", "genre", "story_engine", "audience_promise", "narrative_structure", "main_path"),
        "highlight_strategy": ("primary_story_engine_id", "project_signature", "highlight_pillars", "distribution_policy", "rejected_cliches"),
        "style_contract": ("anchor_type", "anchor", "lighting", "color", "composition", "material", "camera_tendency", "sound_tendency", "excluded_mechanisms"),
    }
    for contract_name, required_fields in strategy_contracts.items():
        contract = plan.get(contract_name)
        if not isinstance(contract, dict):
            issues.append(issue("error", f"{contract_name}_missing", f"drama_plan 缺少 {contract_name}。", path))
            continue
        for field in required_fields:
            if not has_meaningful_value(contract.get(field)):
                issues.append(issue("error", f"{contract_name}_field_missing", f"{contract_name}.{field} 必须填写。", path))
        if contract_name == "audience_plan" and isinstance(contract, dict):
            source_values = contract.get("execution_sources")
            expected_sources = {
                "viewing_focus": "audience_plan.viewing_focus",
                "emotional_payoff": "audience_plan.emotional_payoff",
                "platform_viewing_context": "audience_plan.platform_viewing_context",
                "expression_boundaries": "audience_plan.expression_boundaries",
            }
            if source_values != expected_sources:
                issues.append(issue("error", "audience_plan_execution_sources_invalid", "audience_plan.execution_sources 必须逐项锁定四个 audience_execution 源字段。", path))
    scale = plan.get("scale_plan")
    if not isinstance(scale, dict):
        issues.append(issue("error", "scale_plan_missing", "drama_plan 缺少 scale_plan。", path))
        return expected
    count = scale.get("episode_count")
    durations = scale.get("episode_durations_s")
    displays = scale.get("episode_duration_displays")
    total = scale.get("total_duration_s")
    total_display = scale.get("total_duration_display")
    if not isinstance(count, int) or isinstance(count, bool) or count < 1:
        issues.append(issue("error", "episode_count_invalid", "episode_count 必须是正整数。", path))
        return expected
    if not isinstance(durations, list) or len(durations) != count:
        issues.append(issue("error", "episode_durations_invalid", "episode_durations_s 数量必须等于 episode_count。", path))
        return expected
    if isinstance(displays, list) and len(displays) != count:
        issues.append(issue("error", "episode_duration_displays_invalid", "episode_duration_displays 数量必须等于 episode_count。", path))
    numeric: list[int] = []
    for index, seconds in enumerate(durations, start=1):
        if not isinstance(seconds, (int, float)) or isinstance(seconds, bool):
            issues.append(issue("error", "episode_duration_invalid", f"第 {index} 集时长必须是数字。", path))
            continue
        value = int(round(float(seconds)))
        numeric.append(value)
        expected[f"ep_{index}"] = value
        display = displays[index - 1] if isinstance(displays, list) and index - 1 < len(displays) else None
        check_duration_pair(value, display, path, f"ep_{index}", issues)
    if isinstance(total, (int, float)) and not isinstance(total, bool):
        if numeric and int(round(float(total))) != sum(numeric):
            issues.append(issue("error", "total_duration_mismatch", "total_duration_s 必须等于各集 episode_durations_s 之和。", path))
        check_duration_pair(total, total_display, path, "total", issues, total_display=True)
    else:
        issues.append(issue("error", "total_duration_invalid", "total_duration_s 必须是数字。", path))
    delivery = plan.get("delivery_settings")
    if isinstance(delivery, dict):
        subtitle_enabled = delivery.get("subtitle_enabled")
        if not isinstance(subtitle_enabled, bool):
            issues.append(issue("error", "subtitle_enabled_invalid", "delivery_settings.subtitle_enabled 必须是布尔值；默认 false，用户明确要求字幕时为 true。", path))
        if subtitle_enabled is False and delivery.get("subtitle_policy") != "disabled":
            issues.append(issue("error", "subtitle_disabled_policy_missing", "字幕关闭时 subtitle_policy 必须为 disabled。", path))
        expected_deliverables = ["subtitle_master"] if subtitle_enabled is True else ["clean_master"]
        if delivery.get("final_deliverables") != expected_deliverables:
            issues.append(issue("error", "final_deliverables_invalid", f"final_deliverables 必须只包含单一最终视频版本：{expected_deliverables}。", path))
    return expected


def load_storyboard_index(root: Path, episode_id: str, issues: list[dict[str, Any]]) -> dict[str, Any]:
    path = root / f"episodes/{episode_id}/02_分镜/storyboard_{episode_id}.json"
    data = load_json(path, issues, required=False)
    if not isinstance(data, dict):
        return {
            "segments": set(),
            "shots": set(),
            "shot_durations": {},
            "segment_shots": {},
            "segment_durations": {},
            "required_reference_roles": {},
            "required_keyframe_roles": {},
            "keyframe_requests": {},
        }
    shots = data.get("shots") if isinstance(data.get("shots"), list) else []
    segments = data.get("segments") if isinstance(data.get("segments"), list) else []
    return {
        "segments": {item.get("segment_id") for item in segments if isinstance(item, dict) and isinstance(item.get("segment_id"), str)},
        "shots": {item.get("shot_id") for item in shots if isinstance(item, dict) and isinstance(item.get("shot_id"), str)},
        "shot_durations": {
            item.get("shot_id"): item.get("duration_s")
            for item in shots
            if isinstance(item, dict) and isinstance(item.get("shot_id"), str) and isinstance(item.get("duration_s"), (int, float))
        },
        "segment_shots": {
            item.get("segment_id"): item.get("shot_ids")
            for item in segments
            if isinstance(item, dict) and isinstance(item.get("segment_id"), str) and isinstance(item.get("shot_ids"), list)
        },
        "segment_durations": {
            item.get("segment_id"): item.get("duration_s")
            for item in segments
            if isinstance(item, dict) and isinstance(item.get("segment_id"), str) and isinstance(item.get("duration_s"), (int, float))
        },
        "required_reference_roles": {
            item.get("segment_id"): {role for role in item.get("required_reference_roles") if isinstance(role, str)}
            for item in segments
            if isinstance(item, dict) and isinstance(item.get("segment_id"), str) and isinstance(item.get("required_reference_roles"), list)
        },
        "required_keyframe_roles": {
            item.get("segment_id"): {role for role in item.get("required_keyframe_roles") if isinstance(role, str)}
            for item in segments
            if isinstance(item, dict) and isinstance(item.get("segment_id"), str) and isinstance(item.get("required_keyframe_roles"), list)
        },
        "keyframe_requests": {
            item.get("segment_id"): item.get("keyframe_requests")
            for item in segments
            if isinstance(item, dict) and isinstance(item.get("segment_id"), str) and isinstance(item.get("keyframe_requests"), list)
        },
    }


def video_model_name(plan: Any, storyboard: dict[str, Any], segment: dict[str, Any]) -> str:
    for value in (
        segment.get("video_model"),
        segment.get("model"),
        storyboard.get("video_model"),
        storyboard.get("model"),
    ):
        if isinstance(value, str) and value.strip():
            return value
    model_plan = plan.get("model_plan") if isinstance(plan, dict) else None
    video_plan = model_plan.get("video") if isinstance(model_plan, dict) else None
    if isinstance(video_plan, dict):
        for field in ("model", "model_name", "selected_model"):
            value = video_plan.get(field)
            if isinstance(value, str) and value.strip():
                return value
    if isinstance(video_plan, str):
        return video_plan
    return ""


def media_to_video_limits(model_name: str) -> tuple[int, int]:
    if "seedance 2.5" in model_name.lower():
        return SEEDANCE25_MEDIA_VIDEO_TOTAL_LIMIT_S, SEEDANCE25_MEDIA_AUDIO_TOTAL_LIMIT_S
    return DEFAULT_MEDIA_VIDEO_TOTAL_LIMIT_S, DEFAULT_MEDIA_AUDIO_TOTAL_LIMIT_S


def check_segment_shot_count(
    segment_id: Any,
    duration_s: int,
    shot_count: int,
    shot_mode: Any,
    density_profile: Any,
    path: Path,
    issues: list[dict[str, Any]],
) -> None:
    label = str(segment_id or "segment")
    density_profiles = {"high_density_short", "dialogue_emotional", "suspense_build", "micro_film", "custom"}
    if density_profile not in density_profiles:
        issues.append(issue("error", "segment_density_profile_invalid", f"{label} density_profile 无效。", path))
    if shot_mode not in {"edited", "true_one_take"}:
        issues.append(issue("error", "segment_shot_mode_invalid", f"{label} shot_mode 必须为 edited 或 true_one_take。", path))
        return
    if shot_mode == "true_one_take":
        if shot_count != 1:
            issues.append(issue("error", "true_one_take_shot_count_invalid", f"{label} 标记为 true_one_take 时必须且只能包含 1 个镜头。", path))
        return
    if density_profile == "high_density_short" and duration_s == 15 and shot_count < 8:
        issues.append(issue("error", "segment_shot_count_invalid", f"{label} 为 high_density_short 的 15 秒剪辑型视频，至少需要 8 个有效镜头。", path))


def check_keyframe_request_plan(
    segment: dict[str, Any],
    path: Path,
    issues: list[dict[str, Any]],
    max_per_segment: int = SEGMENT_KEYFRAME_MAX,
) -> int:
    segment_id = str(segment.get("segment_id") or "segment")
    requests = segment.get("keyframe_requests")
    if requests is None:
        return 0
    if not isinstance(requests, list):
        issues.append(issue("error", "keyframe_requests_invalid", f"{segment_id} keyframe_requests 必须是数组；未选中本集高光时可省略或填空数组。", path))
        return 0
    count = len(requests)
    if count > max_per_segment:
        issues.append(issue("error", "keyframe_request_count_invalid", f"{segment_id} 单段 keyframe_requests 最多 {max_per_segment} 张；关键帧按集总量规划，不得把普通镜头都升级为 KF。", path))
    roles = segment.get("required_keyframe_roles")
    if count and isinstance(roles, list) and "highlight" not in roles:
        issues.append(issue("error", "keyframe_role_missing", f"{segment_id} 已规划 keyframe_requests 时，required_keyframe_roles 必须包含 highlight。", path))
    if not count and isinstance(roles, list) and "highlight" in roles:
        issues.append(issue("error", "keyframe_role_without_request", f"{segment_id} 标记了 highlight 但没有 keyframe_requests；未选中本集高光时不要登记关键帧职责。", path))
    return count


def check_episode_keyframe_request_plan(segments: list[Any], lightweight: bool, path: Path, issues: list[dict[str, Any]]) -> None:
    valid_segments = [segment for segment in segments if isinstance(segment, dict)]
    max_per_segment = EPISODE_KEYFRAME_MAX if len(valid_segments) == 1 else SEGMENT_KEYFRAME_MAX
    total = 0
    for segment in valid_segments:
        total += check_keyframe_request_plan(segment, path, issues, max_per_segment)
    if total == 0:
        if not lightweight:
            issues.append(issue("error", "episode_keyframe_requests_missing", f"完整模式每集必须按集规划 {EPISODE_KEYFRAME_MIN}-{EPISODE_KEYFRAME_MAX} 张剧情高光关键帧；不是每个 SEG 都需要，但全集不能为 0。", path))
        return
    if total < EPISODE_KEYFRAME_MIN or total > EPISODE_KEYFRAME_MAX:
        issues.append(issue("error", "episode_keyframe_request_count_invalid", f"本集 keyframe_requests 总数为 {total}，必须按集规划 {EPISODE_KEYFRAME_MIN}-{EPISODE_KEYFRAME_MAX} 张剧情高光关键帧；不是每个 SEG 都需要关键帧。", path))


def check_storyboards(
    root: Path,
    expected_durations: dict[str, int],
    plan: Any,
    issues: list[dict[str, Any]],
    episode_filter: str | None = None,
) -> None:
    lightweight = is_lightweight_plan(plan) and lightweight_constraints_valid(plan)
    for episode_id, episode_root in episode_dirs(root, episode_filter):
        path = episode_root / f"02_分镜/storyboard_{episode_id}.json"
        data = load_json(path, issues, required=False)
        if not isinstance(data, dict):
            continue
        if data.get("episode_id") != episode_id:
            issues.append(issue("error", "episode_id_mismatch", "storyboard episode_id 与目录不一致。", path))
        expected_director_card = f"episodes/{episode_id}/02_分镜/导演总控卡_{episode_id}.md"
        if data.get("director_control_card") != expected_director_card:
            issues.append(issue("error", "director_control_card_invalid", f"storyboard.director_control_card 必须指向 {expected_director_card}。", path))
        elif not file_exists(root, expected_director_card):
            issues.append(issue("error", "director_control_card_missing", "分镜阶段必须存在唯一导演总控卡。", path))
        expected_source_markdown = f"episodes/{episode_id}/02_分镜/分镜_完整分镜表_{episode_id}.md"
        source_markdown = relative_file(root, data.get("source_markdown"))
        if data.get("source_markdown") != expected_source_markdown:
            issues.append(issue("error", "storyboard_source_markdown_invalid", f"storyboard.source_markdown 必须指向 {expected_source_markdown}。", path))
        elif source_markdown is None or not source_markdown.is_file():
            issues.append(issue("error", "storyboard_source_markdown_missing", "十五列完整分镜表文件不存在。", path))
        else:
            try:
                table_text = source_markdown.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                issues.append(issue("error", "storyboard_source_markdown_unreadable", f"十五列完整分镜表无法读取：{exc}", source_markdown))
            else:
                if 15 not in markdown_table_column_counts(table_text):
                    issues.append(issue("error", "storyboard_fifteen_columns_missing", "完整分镜表必须包含一个十五列表格。", source_markdown))
        if episode_id in expected_durations and isinstance(data.get("duration_s"), (int, float)) and int(round(float(data["duration_s"]))) != expected_durations[episode_id]:
            issues.append(issue("error", "storyboard_duration_mismatch", "分镜总时长必须等于计划中的本集时长。", path))
        shots = data.get("shots")
        segments = data.get("segments")
        if not isinstance(shots, list) or not isinstance(segments, list):
            issues.append(issue("error", "storyboard_shape_invalid", "storyboard 必须包含 shots 和 segments 数组。", path))
            continue
        shot_ids = check_unique(shots, "shot_id", path, issues, "shots")
        segment_ids = check_unique(segments, "segment_id", path, issues, "segments")
        shot_to_segment = {
            item.get("shot_id"): item.get("segment_id")
            for item in shots
            if isinstance(item, dict) and isinstance(item.get("shot_id"), str)
        }
        scene_ids = {
            item.get("scene_id")
            for item in shots
            if isinstance(item, dict) and isinstance(item.get("scene_id"), str) and item.get("scene_id").strip()
        }
        shot_durations = {
            item.get("shot_id"): item.get("duration_s")
            for item in shots
            if isinstance(item, dict) and isinstance(item.get("shot_id"), str) and isinstance(item.get("duration_s"), (int, float))
        }
        if shot_durations and isinstance(data.get("duration_s"), (int, float)):
            if int(round(float(data["duration_s"]))) != int(round(sum(float(v) for v in shot_durations.values()))):
                issues.append(issue("error", "shot_duration_total_mismatch", "shots.duration_s 之和必须等于 storyboard.duration_s。", path))
        covered: list[str] = []
        lightweight = is_lightweight_plan(plan) and lightweight_constraints_valid(plan)
        for index, segment in enumerate(segments, start=1):
            if not isinstance(segment, dict):
                continue
            segment_id = segment.get("segment_id")
            segment_shots = segment.get("shot_ids")
            if not isinstance(segment_shots, list):
                issues.append(issue("error", "segment_shot_ids_invalid", f"{segment_id or index} 缺少 shot_ids 数组。", path))
                continue
            for shot_id in segment_shots:
                if shot_id not in shot_ids:
                    issues.append(issue("error", "segment_unknown_shot", f"{segment_id} 引用了不存在的 shot_id：{shot_id}", path))
                elif shot_to_segment.get(shot_id) not in {None, segment_id}:
                    issues.append(issue("error", "shot_segment_mismatch", f"{shot_id} 的 segment_id 与 segments[].shot_ids 不一致。", path))
            covered.extend(str(item) for item in segment_shots)
            if isinstance(segment.get("duration_s"), (int, float)):
                declared = int(round(float(segment["duration_s"])))
                calculated = int(round(sum(float(shot_durations[s]) for s in segment_shots if s in shot_durations)))
                if calculated and declared != calculated:
                    issues.append(issue("error", "segment_duration_mismatch", f"{segment_id} duration_s 必须等于其 shot_ids 时长之和。", path))
                check_segment_shot_count(
                    segment_id,
                    declared,
                    len(segment_shots),
                    segment.get("shot_mode"),
                    segment.get("density_profile"),
                    path,
                    issues,
                )
            tail_mode = segment.get("tail_mode")
            if tail_mode not in {"continuous_motion", "cuttable_completion", "stable_hold", "loop_continuation"}:
                issues.append(issue("error", "segment_tail_mode_invalid", f"{segment_id or index} tail_mode 无效。", path))
            if index < len(segments) and tail_mode == "stable_hold" and not has_meaningful_value(segment.get("tail_hold_reason")):
                issues.append(issue("error", "intermediate_stable_hold_reason_missing", f"{segment_id or index} 是中间片段，使用 stable_hold 时必须填写 tail_hold_reason。", path))
            check_reference_plan(segment, path, issues)
        check_episode_keyframe_request_plan(segments, lightweight, path, issues)
        missing = shot_ids - set(covered)
        duplicated = {shot_id for shot_id in covered if covered.count(shot_id) > 1}
        if missing:
            issues.append(issue("error", "shots_not_covered", f"以下镜头未被任何 segment 覆盖：{sorted(missing)}", path))
        if duplicated:
            issues.append(issue("error", "shots_covered_multiple_times", f"以下镜头被多个 segment 重复覆盖：{sorted(duplicated)}", path))
        unknown_segment_refs = {seg for seg in shot_to_segment.values() if isinstance(seg, str) and seg not in segment_ids}
        if unknown_segment_refs:
            issues.append(issue("error", "shot_unknown_segment", f"shots 中引用了不存在的 segment_id：{sorted(unknown_segment_refs)}", path))
        audience_execution = data.get("audience_execution")
        if not isinstance(audience_execution, dict):
            issues.append(issue("error", "audience_execution_missing", "storyboard 必须登记从已确认 audience_plan 派生的 audience_execution。", path))
        else:
            source_revision = audience_execution.get("source_plan_revision")
            if not isinstance(source_revision, int) or isinstance(source_revision, bool) or source_revision < 1:
                issues.append(issue("error", "audience_execution_revision_invalid", "audience_execution.source_plan_revision 必须是正整数。", path))
            elif isinstance(plan, dict) and isinstance(plan.get("revision"), int) and source_revision != plan.get("revision"):
                issues.append(issue("error", "audience_execution_revision_mismatch", "audience_execution.source_plan_revision 必须等于当前已确认 drama_plan revision。", path))
            audience_plan = plan.get("audience_plan") if isinstance(plan, dict) and isinstance(plan.get("audience_plan"), dict) else {}
            for field in ("viewing_focus", "emotional_payoff", "platform_viewing_context", "expression_boundaries"):
                execution = audience_execution.get(field)
                if not isinstance(execution, dict) or not str(execution.get("contract") or "").strip():
                    issues.append(issue("error", "audience_execution_field_missing", f"audience_execution.{field} 必须填写 contract。", path))
                    continue
                expected_source = f"audience_plan.{field}"
                if execution.get("source_field") != expected_source:
                    issues.append(issue("error", "audience_execution_source_field_invalid", f"audience_execution.{field}.source_field 必须为 {expected_source}。", path))
                if execution.get("contract") != audience_plan.get(field):
                    issues.append(issue("error", "audience_execution_contract_mismatch", f"audience_execution.{field}.contract 必须逐字继承已确认 audience_plan.{field}。", path))
                refs = execution.get("scene_or_shot_ids")
                if not isinstance(refs, list) or not refs or not all(isinstance(ref, str) and ref.strip() for ref in refs):
                    issues.append(issue("error", "audience_execution_refs_missing", f"audience_execution.{field}.scene_or_shot_ids 必须列出落地场次或镜头。", path))
                    continue
                unknown_refs = sorted(set(refs) - shot_ids - scene_ids)
                if unknown_refs:
                    issues.append(issue("error", "audience_execution_ref_invalid", f"audience_execution.{field} 引用了不存在的场次或镜头：{unknown_refs}", path))
        script_path = episode_root / f"01_剧本/script_contract_{episode_id}.json"
        script_contract = load_json(script_path, issues, required=not lightweight)
        highlight_ledger = script_contract.get("highlight_ledger") if isinstance(script_contract, dict) else []
        if isinstance(script_contract, dict) and not isinstance(highlight_ledger, list):
            issues.append(issue("error", "highlight_ledger_invalid", "script_contract.highlight_ledger 必须是数组。", script_path))
            highlight_ledger = []
        if not lightweight and isinstance(highlight_ledger, list):
            primary_entries = [
                item
                for item in highlight_ledger
                if isinstance(item, dict) and item.get("role") == "primary" and str(item.get("highlight_id") or "").strip()
            ]
            if not primary_entries:
                issues.append(issue("error", "primary_highlight_missing", "完整模式每集 script_contract.highlight_ledger 必须至少包含一个有效的 primary 亮点。", script_path))
        primary_highlights = {
            item.get("highlight_id")
            for item in highlight_ledger or []
            if isinstance(item, dict) and item.get("role") == "primary" and isinstance(item.get("highlight_id"), str)
        }
        known_highlights = {
            item.get("highlight_id")
            for item in highlight_ledger or []
            if isinstance(item, dict) and isinstance(item.get("highlight_id"), str)
        }
        highlight_bindings = data.get("highlight_bindings")
        if not isinstance(highlight_bindings, list):
            issues.append(issue("error", "highlight_bindings_missing", "storyboard.highlight_bindings 必须是数组并覆盖剧本主要亮点。", path))
            highlight_bindings = []
        binding_ids = check_unique(highlight_bindings, "highlight_id", path, issues, "highlight_bindings")
        shot_positions = {
            shot_id: index
            for index, shot_id in enumerate(
                [
                    item.get("shot_id")
                    for item in shots
                    if isinstance(item, dict) and isinstance(item.get("shot_id"), str)
                ]
            )
        }
        inherited_aftereffects = data.get("inherited_aftereffect_bindings", [])
        if not isinstance(inherited_aftereffects, list):
            issues.append(issue("error", "inherited_aftereffect_bindings_invalid", "inherited_aftereffect_bindings 必须是数组。", path))
            inherited_aftereffects = []
        for inherited in inherited_aftereffects:
            if not isinstance(inherited, dict):
                issues.append(issue("error", "inherited_aftereffect_binding_invalid", "inherited_aftereffect_bindings 每项必须是对象。", path))
                continue
            binding_id = str(inherited.get("binding_id") or "")
            source_episode = str(inherited.get("source_episode_id") or "")
            source_highlight = str(inherited.get("source_highlight_id") or "")
            shot_refs = inherited.get("shot_ids")
            if not binding_id or not re.fullmatch(r"ep_[1-9]\d*", source_episode) or not source_highlight:
                issues.append(issue("error", "inherited_aftereffect_binding_fields_missing", "inherited_aftereffect_bindings 必须填写 binding_id、source_episode_id 和 source_highlight_id。", path))
            if not isinstance(shot_refs, list) or not shot_refs or not all(isinstance(ref, str) and ref.strip() for ref in shot_refs):
                issues.append(issue("error", "inherited_aftereffect_binding_shots_missing", f"{binding_id or '跨集余震承接'} 必须绑定本集真实 shot_ids。", path))
            else:
                unknown_refs = sorted(set(shot_refs) - shot_ids)
                if unknown_refs:
                    issues.append(issue("error", "inherited_aftereffect_binding_shot_invalid", f"{binding_id or '跨集余震承接'} 引用了不存在的本集镜头：{unknown_refs}", path))
            source_storyboard = load_json(root / f"episodes/{source_episode}/02_分镜/storyboard_{source_episode}.json", issues, required=False)
            source_bindings = source_storyboard.get("highlight_bindings") if isinstance(source_storyboard, dict) else []
            matching_sources = [
                item
                for item in source_bindings or []
                if isinstance(item, dict)
                and item.get("highlight_id") == source_highlight
                and isinstance(item.get("deferred_aftereffect_ref"), dict)
                and item["deferred_aftereffect_ref"].get("binding_id") == binding_id
                and item["deferred_aftereffect_ref"].get("episode_id") == episode_id
            ]
            if not matching_sources:
                issues.append(issue("error", "inherited_aftereffect_source_missing", f"{binding_id or '跨集余震承接'} 找不到来源集对应 deferred_aftereffect_ref。", path))
        for binding in highlight_bindings:
            if not isinstance(binding, dict):
                issues.append(issue("error", "highlight_binding_invalid", "highlight_bindings 每项必须是对象。", path))
                continue
            highlight_id = str(binding.get("highlight_id") or "")
            if known_highlights and highlight_id not in known_highlights:
                issues.append(issue("error", "highlight_binding_unknown", f"分镜绑定了剧本中不存在的亮点：{highlight_id}", path))
            segment_id = binding.get("segment_id")
            if segment_id not in segment_ids:
                issues.append(issue("error", "highlight_binding_segment_invalid", f"{highlight_id or '亮点绑定'} 引用了不存在的 segment_id：{segment_id}", path))
            payoff_positions: list[int] = []
            reaction_positions: list[int] = []
            for field in ("payoff_shot_ids", "reaction_shot_ids"):
                refs = binding.get(field)
                if not isinstance(refs, list) or not refs or not all(isinstance(ref, str) and ref.strip() for ref in refs):
                    issues.append(issue("error", "highlight_binding_shots_missing", f"{highlight_id or '亮点绑定'}.{field} 必须至少包含一个镜头。", path))
                    continue
                unknown_refs = sorted(set(refs) - shot_ids)
                if unknown_refs:
                    issues.append(issue("error", "highlight_binding_shot_invalid", f"{highlight_id or '亮点绑定'}.{field} 引用了不存在的镜头：{unknown_refs}", path))
                wrong_segment = sorted(ref for ref in refs if field == "payoff_shot_ids" and shot_to_segment.get(ref) not in {None, segment_id})
                if wrong_segment:
                    issues.append(issue("error", "highlight_binding_segment_mismatch", f"{highlight_id or '亮点绑定'} 的镜头不属于 {segment_id}：{wrong_segment}", path))
                valid_positions = [shot_positions[ref] for ref in refs if ref in shot_positions]
                if field == "payoff_shot_ids":
                    payoff_positions.extend(valid_positions)
                else:
                    reaction_positions.extend(valid_positions)
            if payoff_positions and reaction_positions and min(reaction_positions) < min(payoff_positions):
                issues.append(issue("error", "highlight_binding_reaction_before_payoff", f"{highlight_id or '亮点绑定'} 的反应镜头不得早于兑现镜头。", path))
            aftereffect_refs = binding.get("aftereffect_shot_ids")
            deferred_aftereffect_ref = binding.get("deferred_aftereffect_ref")
            if not isinstance(aftereffect_refs, list) or not all(isinstance(ref, str) and ref.strip() for ref in aftereffect_refs):
                issues.append(issue("error", "highlight_binding_aftereffect_invalid", f"{highlight_id or '亮点绑定'}.aftereffect_shot_ids 必须是数组。", path))
            elif aftereffect_refs:
                unknown_refs = sorted(set(aftereffect_refs) - shot_ids)
                if unknown_refs:
                    issues.append(issue("error", "highlight_binding_shot_invalid", f"{highlight_id or '亮点绑定'}.aftereffect_shot_ids 引用了不存在的本集镜头：{unknown_refs}", path))
                aftereffect_positions = [shot_positions[ref] for ref in aftereffect_refs if ref in shot_positions]
                preceding_positions = payoff_positions + reaction_positions
                if aftereffect_positions and preceding_positions and min(aftereffect_positions) < max(preceding_positions):
                    issues.append(issue("error", "highlight_binding_aftereffect_before_payoff", f"{highlight_id or '亮点绑定'} 的余震镜头不得早于兑现或反应镜头。", path))
                if deferred_aftereffect_ref not in (None, {}):
                    issues.append(issue("error", "highlight_binding_aftereffect_scope_conflict", f"{highlight_id or '亮点绑定'} 已填写本集余震时 deferred_aftereffect_ref 必须为空。", path))
            elif not isinstance(deferred_aftereffect_ref, dict):
                issues.append(issue("error", "highlight_binding_aftereffect_missing", f"{highlight_id or '亮点绑定'} 必须填写本集 aftereffect_shot_ids 或跨集 deferred_aftereffect_ref。", path))
            else:
                target_episode = str(deferred_aftereffect_ref.get("episode_id") or "")
                binding_id = str(deferred_aftereffect_ref.get("binding_id") or "")
                if not re.fullmatch(r"ep_[1-9]\d*", target_episode) or target_episode not in {item[0] for item in episode_dirs(root)}:
                    issues.append(issue("error", "highlight_binding_deferred_episode_invalid", f"{highlight_id or '亮点绑定'} deferred_aftereffect_ref.episode_id 必须是计划内分集。", path))
                elif int(target_episode.split("_", 1)[1]) <= int(episode_id.split("_", 1)[1]):
                    issues.append(issue("error", "highlight_binding_deferred_episode_order_invalid", f"{highlight_id or '亮点绑定'} deferred_aftereffect_ref 必须指向后续分集。", path))
                target_highlight = str(deferred_aftereffect_ref.get("highlight_id") or "")
                if not target_highlight or not binding_id:
                    issues.append(issue("error", "highlight_binding_deferred_ref_invalid", f"{highlight_id or '亮点绑定'} deferred_aftereffect_ref 必须填写 highlight_id 和 binding_id。", path))
                target_script = load_json(root / f"episodes/{target_episode}/01_剧本/script_contract_{target_episode}.json", issues, required=False)
                target_ledger = target_script.get("highlight_ledger") if isinstance(target_script, dict) else []
                target_highlight_ids = {
                    str(item.get("highlight_id"))
                    for item in target_ledger or []
                    if isinstance(item, dict) and str(item.get("highlight_id") or "").strip()
                }
                if target_highlight and target_highlight not in target_highlight_ids:
                    issues.append(issue("error", "highlight_binding_deferred_highlight_missing", f"{highlight_id or '亮点绑定'} deferred_aftereffect_ref.highlight_id 必须存在于目标集 script_contract.highlight_ledger。", path))
            for field in ("visual_execution", "performance_execution", "audio_execution", "compile_notes"):
                if not str(binding.get(field) or "").strip():
                    issues.append(issue("error", "highlight_binding_execution_missing", f"{highlight_id or '亮点绑定'} 缺少 {field}。", path))
        missing_primary = sorted(primary_highlights - binding_ids)
        if missing_primary:
            issues.append(issue("error", "primary_highlight_binding_missing", f"以下主要亮点未绑定到分镜：{missing_primary}", path))


def check_reference_plan(
    segment: dict[str, Any],
    path: Path,
    issues: list[dict[str, Any]],
) -> None:
    refs = segment.get("reference_input_plan")
    if refs is None:
        issues.append(issue("error", "reference_input_plan_missing", "每个 SEG 必须填写 reference_input_plan。", path))
        return
    if not isinstance(refs, list):
        issues.append(issue("error", "reference_input_plan_invalid", "reference_input_plan 必须是数组。", path))
        return
    orders: list[int] = []
    for index, ref in enumerate(refs, start=1):
        if not isinstance(ref, dict):
            issues.append(issue("error", "reference_input_plan_invalid", f"第 {index} 条参考计划必须是对象。", path))
            continue
        order = ref.get("order")
        role = ref.get("role")
        if isinstance(order, int) and not isinstance(order, bool):
            orders.append(order)
            binding = str(ref.get("opening_binding", "") or "")
            if not re.search(marker_pattern("image", order), binding, flags=re.I):
                issues.append(issue("error", "opening_binding_marker_missing", f"第 {order} 张参考图缺少对应 <图片{order}>/<IMG{order}> 标记。", path))
        else:
            issues.append(issue("error", "reference_order_invalid", "参考图 order 必须是整数。", path))
        if role not in REFERENCE_ROLES:
            issues.append(issue("error", "reference_role_invalid", f"参考图职责无效：{role}", path))
        for field in ("planned_source", "opening_binding", "adopt", "exclude"):
            if not str(ref.get(field, "") or "").strip():
                issues.append(issue("error", "reference_input_plan_incomplete", f"参考图计划缺少 {field}。", path))
    if orders and sorted(orders) != list(range(1, len(orders) + 1)):
        issues.append(issue("error", "reference_order_not_contiguous", "参考图 order 必须从 1 连续递增。", path))


def asset_version_key(asset_id: str, version: str, separator: str = "_") -> str:
    return f"{asset_id}{separator}{version}"


def version_rank(version: str) -> int:
    match = re.search(r"\d+", version)
    return int(match.group()) if match else -1


def split_asset_version_ref(ref: Any) -> tuple[str, str] | None:
    if not isinstance(ref, str):
        return None
    for separator in ("_", ":"):
        head, sep, tail = ref.rpartition(separator)
        if sep and head and re.fullmatch(r"v\d+", tail, flags=re.I):
            return head, tail
    return None


def blank_asset_index() -> dict[str, Any]:
    return {
        "known_asset_ids": set(),
        "known_version_refs": set(),
        "approved_version_refs": set(),
        "approved_versions_by_asset": {},
        "latest_approved_version": {},
        "known_state_refs": set(),
        "approved_state_refs": set(),
    }


def remember_asset_version(index: dict[str, Any], asset_id: str, version: str, status: Any) -> None:
    index["known_asset_ids"].add(asset_id)
    if version:
        underscore_ref = asset_version_key(asset_id, version, "_")
        colon_ref = asset_version_key(asset_id, version, ":")
        index["known_version_refs"].add(underscore_ref)
        index["known_version_refs"].add(colon_ref)
        if status == "approved":
            index["approved_version_refs"].add(underscore_ref)
            index["approved_version_refs"].add(colon_ref)
            approved = index["approved_versions_by_asset"].setdefault(asset_id, set())
            approved.add(version)
            latest = index["latest_approved_version"].get(asset_id)
            if latest is None or version_rank(version) > version_rank(latest):
                index["latest_approved_version"][asset_id] = version


def state_ref_keys(asset_id: str, state_id: str, version: str = "") -> set[str]:
    refs = {f"{asset_id}:{state_id}"}
    if version:
        refs.add(f"{asset_id}:{state_id}_{version}")
        refs.add(f"{asset_id}:{state_id}:{version}")
    return refs


def remember_state_version(index: dict[str, Any], asset_id: str, state_id: str, version: str, status: Any) -> None:
    refs = state_ref_keys(asset_id, state_id, version)
    index["known_state_refs"].update(refs)
    if status == "approved":
        index["approved_state_refs"].update(refs)


def check_stale_asset_version(ref: Any, index: dict[str, Any], path: Path, issues: list[dict[str, Any]], owner: str) -> None:
    parsed = split_asset_version_ref(ref)
    if parsed is None:
        return
    asset_id, version = parsed
    latest = index["latest_approved_version"].get(asset_id)
    if latest and version_rank(version) < version_rank(latest):
        issues.append(issue("error", "downstream_asset_version_stale", f"{owner} 仍引用旧资产版本 {ref}；最新 approved 版本是 {asset_version_key(asset_id, latest)}。", path))


def check_assets(root: Path, issues: list[dict[str, Any]], episode_filter: str | None = None) -> dict[str, Any]:
    registry_path = root / "shared/03_资产/asset_registry.json"
    registry = load_json(registry_path, issues, required=False)
    index = blank_asset_index()
    source_usage_cache: dict[str, dict[str, Any] | None] = {}
    if isinstance(registry, dict):
        assets = registry.get("assets")
        if isinstance(assets, list):
            version_keys: set[tuple[str, str]] = set()
            for asset in assets:
                if not isinstance(asset, dict):
                    continue
                asset_id = asset.get("asset_id")
                category = asset.get("category")
                version = str(asset.get("version") or "")
                if isinstance(asset_id, str) and asset_id.strip():
                    remember_asset_version(index, asset_id, version, asset.get("status"))
                    key = (asset_id, version)
                    if key in version_keys:
                        issues.append(issue("error", "asset_version_duplicate", f"asset_id + version 重复：{asset_id} {version}", registry_path))
                    version_keys.add(key)
                    expected_prefix = ASSET_PREFIX_BY_CATEGORY.get(str(category))
                    if expected_prefix and not asset_id.startswith(expected_prefix):
                        issues.append(issue("error", "asset_id_prefix_mismatch", f"{asset_id} 与 category={category} 的前缀不一致。", registry_path))
                else:
                    issues.append(issue("error", "asset_id_missing", "资产缺少 asset_id。", registry_path))
                status = asset.get("status")
                if status is not None and status not in ASSET_STATUS_VALUES:
                    issues.append(issue("error", "asset_status_invalid", f"资产状态无效：{status}", registry_path))
                state_id = str(asset.get("state_id") or "")
                if isinstance(asset_id, str) and asset_id.strip() and state_id:
                    remember_state_version(index, asset_id, state_id, version, status)
                for file_value in asset.get("files") or []:
                    if not file_exists(root, file_value):
                        issues.append(issue("error", "asset_file_missing", f"资产文件不存在：{file_value}", registry_path))
                generation = asset.get("generation") if isinstance(asset.get("generation"), dict) else {}
                tool = generation.get("tool")
                refs = [*asset.get("reference_asset_ids", [])] if isinstance(asset.get("reference_asset_ids"), list) else []
                available_visual_refs = []
                for field_owner in (asset, generation):
                    value = field_owner.get("available_visual_reference_ids") if isinstance(field_owner, dict) else None
                    if isinstance(value, list):
                        available_visual_refs.extend(item for item in value if isinstance(item, str) and item.strip())
                visual_reference_decision = asset.get("visual_reference_decision") or generation.get("visual_reference_decision")
                if visual_reference_decision is not None and visual_reference_decision not in VISUAL_REFERENCE_DECISIONS:
                    issues.append(issue("error", "visual_reference_decision_invalid", f"{asset_id} visual_reference_decision 无效：{visual_reference_decision}", registry_path))
                visual_inputs = []
                for field in ("reference_inputs", "input_files", "input_images"):
                    value = generation.get(field)
                    if isinstance(value, list):
                        visual_inputs.extend(value)
                style_anchor_refs = combined_strings(asset, generation, field="style_anchor_reference_ids")
                style_terms = combined_strings(asset, generation, field="style_prompt_terms")
                project_visual_mode = asset.get("project_visual_mode") or generation.get("project_visual_mode")
                if category in {"character", "scene", "prop", "style"} and status == "approved":
                    if project_visual_mode not in PROJECT_VISUAL_MODES:
                        issues.append(issue("error", "project_visual_mode_missing_or_invalid", f"{asset_id or '资产'} approved 图片资产必须登记有效 project_visual_mode。", registry_path))
                if tool == "image_gen" and (refs or visual_inputs):
                    issues.append(issue("error", "image_gen_should_not_have_visual_inputs", f"{asset_id} 使用 image_gen 时不应登记图片参考输入。", registry_path))
                if tool == "image_gen" and available_visual_refs and visual_reference_decision != "explicit_user_override":
                    issues.append(issue("error", "image_gen_visual_reference_available", f"{asset_id} 已登记可用视觉参考，必须使用 image_edit；除非用户明确要求不参考并记录 explicit_user_override。", registry_path))
                if tool == "image_gen" and visual_reference_decision == "used":
                    issues.append(issue("error", "image_gen_visual_reference_decision_conflict", f"{asset_id} visual_reference_decision=used 时不能使用 image_gen。", registry_path))
                if tool == "image_edit" and not (refs or visual_inputs or style_anchor_refs):
                    issues.append(issue("error", "image_edit_reference_missing", f"{asset_id} 使用 image_edit 时必须登记实际参考来源。", registry_path))
                if tool == "image_edit" and visual_reference_decision == "none_available":
                    issues.append(issue("error", "image_edit_visual_reference_decision_conflict", f"{asset_id} 使用 image_edit 时 visual_reference_decision 不能写 none_available。", registry_path))
                if category == "character" and state_id and tool == "image_gen" and visual_reference_decision != "explicit_user_override":
                    issues.append(issue("error", "character_state_asset_requires_image_edit", f"{asset_id or '角色状态资产'} 是人物状态资产时必须基于已批准人物图使用 image_edit；除非用户明确要求重做并记录 explicit_user_override。", registry_path))
                check_generation_prompt_file(root, registry_path, str(asset_id or "资产"), tool, generation.get("prompt_path"), issues)
                check_style_anchor_contract(
                    root,
                    registry_path,
                    str(asset_id or "资产"),
                    tool,
                    generation.get("prompt_path"),
                    style_anchor_refs,
                    style_terms,
                    combined_strings(asset, generation, field="style_adopt"),
                    combined_strings(asset, generation, field="style_exclude"),
                    issues,
                    visual_reference_decision,
                )
                if category == "style" and asset_id == "STYLE001":
                    style_asset_type = asset.get("style_asset_type") or generation.get("style_asset_type")
                    if status == "approved" and style_asset_type is None:
                        issues.append(issue("error", "style_asset_type_missing", "STYLE001 approved 前必须登记 style_asset_type=global_visual_language_moodboard。", registry_path))
                    if style_asset_type is not None and style_asset_type != "global_visual_language_moodboard":
                        issues.append(issue("error", "style_asset_type_invalid", "STYLE001 必须登记为 global_visual_language_moodboard。", registry_path))
                    scene_links = asset.get("style_scene_atmosphere_links") or generation.get("style_scene_atmosphere_links")
                    if status == "approved" and (not isinstance(scene_links, list) or not any(str(item).strip() for item in scene_links)):
                        issues.append(issue("error", "style_scene_atmosphere_links_missing", "STYLE001 approved 时 style_scene_atmosphere_links 必须是非空数组。", registry_path))
                    visual_language = asset.get("style_visual_language") or generation.get("style_visual_language")
                    if status == "approved":
                        if not isinstance(visual_language, dict):
                            issues.append(issue("error", "style_visual_language_missing", "STYLE001 必须登记色彩、光线、构图、材质或空间氛围等视觉语言。", registry_path))
                        else:
                            filled = [
                                key
                                for key, value in visual_language.items()
                                if isinstance(value, list) and any(str(item).strip() for item in value)
                            ]
                            if len(filled) < 2:
                                issues.append(issue("error", "style_visual_language_too_sparse", "STYLE001 视觉语言至少填写两类：palette/lighting/composition/materials/space_atmosphere/texture_or_grain。", registry_path))
                    if asset.get("contains_story_characters") is not False and generation.get("contains_story_characters") is not False:
                        issues.append(issue("error", "style_moodboard_contains_characters_unknown", "STYLE001 全局风格 moodboard 必须明确 contains_story_characters=false。", registry_path))
                    if asset.get("contains_story_props") is not False and generation.get("contains_story_props") is not False:
                        issues.append(issue("error", "style_moodboard_contains_props_unknown", "STYLE001 全局风格 moodboard 必须明确 contains_story_props=false。", registry_path))
        elif assets is not None:
            issues.append(issue("error", "assets_invalid", "asset_registry.assets 必须是数组。", registry_path))
    for episode_id, episode_root in episode_dirs(root, episode_filter):
        path = episode_root / f"03_资产/asset_usage_{episode_id}.json"
        usage = load_json(path, issues, required=False)
        if not isinstance(usage, dict):
            continue
        shared = usage.get("shared_assets")
        reused_episode_assets = usage.get("reused_episode_assets")
        episode_assets = usage.get("episode_assets")
        if isinstance(shared, list):
            seen_shared: set[tuple[str, str]] = set()
            for item in shared:
                if not isinstance(item, dict):
                    continue
                asset_id = item.get("asset_id")
                version = str(item.get("version") or "")
                if isinstance(asset_id, str):
                    if index["known_asset_ids"] and asset_id not in index["known_asset_ids"]:
                        issues.append(issue("error", "asset_usage_unknown_shared_asset", f"{episode_id} 引用了 registry 中不存在的共享资产：{asset_id}", path))
                    if not version:
                        issues.append(issue("error", "asset_usage_shared_version_missing", f"{episode_id} 共享资产必须填写 version：{asset_id}", path))
                    else:
                        refs = {asset_version_key(asset_id, version, "_"), asset_version_key(asset_id, version, ":")}
                        if index["known_version_refs"] and not (refs & index["known_version_refs"]):
                            issues.append(issue("error", "asset_usage_unknown_shared_version", f"{episode_id} 引用了 registry 中不存在的共享资产版本：{asset_id} {version}", path))
                        elif index["known_version_refs"] and not (refs & index["approved_version_refs"]):
                            issues.append(issue("error", "asset_usage_shared_not_approved", f"{episode_id} 只能引用 registry 中 approved 的共享资产版本：{asset_id} {version}", path))
                    key = (asset_id, version)
                    if key in seen_shared:
                        issues.append(issue("error", "asset_usage_duplicate", f"{episode_id} 共享资产重复：{asset_id} {version}", path))
                    seen_shared.add(key)
        if reused_episode_assets is not None and not isinstance(reused_episode_assets, list):
            issues.append(issue("error", "reused_episode_assets_invalid", f"{episode_id} reused_episode_assets 必须是数组。", path))
        if isinstance(reused_episode_assets, list):
            seen_reused: set[tuple[str, str, str, str]] = set()
            for item in reused_episode_assets:
                if not isinstance(item, dict):
                    issues.append(issue("error", "reused_episode_asset_invalid", f"{episode_id} reused_episode_assets 每项必须是对象。", path))
                    continue
                source_episode_id = str(item.get("source_episode_id") or "")
                asset_id = str(item.get("asset_id") or "")
                state_id = str(item.get("state_id") or "")
                version = str(item.get("version") or "")
                status = item.get("status")
                source_valid = True
                if not source_episode_id:
                    issues.append(issue("error", "reused_episode_source_missing", f"{episode_id} 复用分集资产必须填写 source_episode_id。", path))
                    source_valid = False
                elif not re.fullmatch(r"ep_[1-9]\d*", source_episode_id) or int(source_episode_id.split("_", 1)[1]) >= int(episode_id.split("_", 1)[1]):
                    issues.append(issue("error", "reused_episode_source_invalid", f"{episode_id} 只能复用更早分集的 approved 资产：{source_episode_id}", path))
                    source_valid = False
                if not asset_id or not version:
                    issues.append(issue("error", "reused_episode_asset_ref_missing", f"{episode_id} 复用分集资产必须填写 asset_id 和 version。", path))
                    source_valid = False
                if status != "approved":
                    issues.append(issue("error", "reused_episode_asset_not_approved", f"{episode_id} 只能复用 approved 分集资产：{asset_id} {state_id} {version}", path))
                    source_valid = False
                if source_valid:
                    if source_episode_id not in source_usage_cache:
                        source_path = root / f"episodes/{source_episode_id}/03_资产/asset_usage_{source_episode_id}.json"
                        source_usage = load_json(source_path, issues, required=False)
                        source_usage_cache[source_episode_id] = source_usage if isinstance(source_usage, dict) else None
                    source_usage = source_usage_cache[source_episode_id]
                    source_candidates = []
                    if isinstance(source_usage, dict):
                        for field in ("episode_assets", "reused_episode_assets"):
                            values = source_usage.get(field)
                            if isinstance(values, list):
                                source_candidates.extend(candidate for candidate in values if isinstance(candidate, dict))
                    matching_source = next(
                        (
                            candidate
                            for candidate in source_candidates
                            if str(candidate.get("asset_id") or "") == asset_id
                            and str(candidate.get("state_id") or "") == state_id
                            and str(candidate.get("version") or "") == version
                            and candidate.get("status") == "approved"
                        ),
                        None,
                    )
                    if matching_source is None:
                        issues.append(issue("error", "reused_episode_asset_source_not_found", f"{episode_id} 复用资产在 {source_episode_id} 中找不到一致的 approved 来源：{asset_id} {state_id} {version}", path))
                        source_valid = False
                    elif sorted(item.get("files") or []) != sorted(matching_source.get("files") or []):
                        issues.append(issue("error", "reused_episode_asset_files_mismatch", f"{episode_id} 复用资产文件必须与 {source_episode_id} 来源记录一致：{asset_id} {state_id} {version}", path))
                        source_valid = False
                if asset_id and source_valid:
                    remember_asset_version(index, asset_id, version, "approved" if status == "approved" else status)
                if asset_id and state_id and source_valid:
                    remember_state_version(index, asset_id, state_id, version, status)
                key = (source_episode_id, asset_id, state_id, version)
                if key in seen_reused:
                    issues.append(issue("error", "reused_episode_asset_duplicate", f"{episode_id} 复用分集资产重复：{source_episode_id} {asset_id} {state_id} {version}", path))
                seen_reused.add(key)
                for file_value in item.get("files") or []:
                    if not file_exists(root, file_value):
                        issues.append(issue("error", "reused_episode_asset_file_missing", f"复用分集资产文件不存在：{file_value}", path))
        if isinstance(episode_assets, list):
            state_keys: set[tuple[str, str, str]] = set()
            for item in episode_assets:
                if not isinstance(item, dict):
                    continue
                asset_id = str(item.get("asset_id") or "")
                state_id = str(item.get("state_id") or "")
                version = str(item.get("version") or "")
                if asset_id:
                    remember_asset_version(index, asset_id, version, item.get("status"))
                if asset_id and state_id:
                    remember_state_version(index, asset_id, state_id, version, item.get("status"))
                key = (asset_id, state_id, version)
                if key in state_keys:
                    issues.append(issue("error", "episode_asset_duplicate", f"{episode_id} 分集资产重复：{asset_id} {state_id} {version}", path))
                state_keys.add(key)
                if item.get("status") is not None and item.get("status") not in ASSET_STATUS_VALUES:
                    issues.append(issue("error", "episode_asset_status_invalid", f"分集资产状态无效：{item.get('status')}", path))
                generation = item.get("generation") if isinstance(item.get("generation"), dict) else {}
                tool = generation.get("tool")
                refs = [*item.get("reference_asset_ids", [])] if isinstance(item.get("reference_asset_ids"), list) else []
                available_visual_refs = []
                for field_owner in (item, generation):
                    value = field_owner.get("available_visual_reference_ids") if isinstance(field_owner, dict) else None
                    if isinstance(value, list):
                        available_visual_refs.extend(ref for ref in value if isinstance(ref, str) and ref.strip())
                visual_reference_decision = item.get("visual_reference_decision") or generation.get("visual_reference_decision")
                if visual_reference_decision is not None and visual_reference_decision not in VISUAL_REFERENCE_DECISIONS:
                    issues.append(issue("error", "episode_visual_reference_decision_invalid", f"{asset_id or '分集资产'} visual_reference_decision 无效：{visual_reference_decision}", path))
                visual_inputs = []
                for field in ("reference_inputs", "input_files", "input_images"):
                    value = generation.get(field)
                    if isinstance(value, list):
                        visual_inputs.extend(value)
                style_anchor_refs = combined_strings(item, generation, field="style_anchor_reference_ids")
                style_terms = combined_strings(item, generation, field="style_prompt_terms")
                project_visual_mode = item.get("project_visual_mode") or generation.get("project_visual_mode")
                category = item.get("category")
                if category in {"character", "scene", "prop", "style"} and item.get("status") == "approved":
                    if project_visual_mode not in PROJECT_VISUAL_MODES:
                        issues.append(issue("error", "episode_project_visual_mode_missing_or_invalid", f"{asset_id or '分集资产'} approved 图片资产必须登记有效 project_visual_mode。", path))
                if tool == "image_gen" and (refs or visual_inputs or style_anchor_refs):
                    issues.append(issue("error", "episode_image_gen_should_not_have_visual_inputs", f"{asset_id or '分集资产'} 使用 image_gen 时不应登记图片参考输入。", path))
                if tool == "image_gen" and available_visual_refs and visual_reference_decision != "explicit_user_override":
                    issues.append(issue("error", "episode_image_gen_visual_reference_available", f"{asset_id or '分集资产'} 已登记可用视觉参考，必须使用 image_edit；除非用户明确要求不参考并记录 explicit_user_override。", path))
                if tool == "image_gen" and visual_reference_decision == "used":
                    issues.append(issue("error", "episode_image_gen_visual_reference_decision_conflict", f"{asset_id or '分集资产'} visual_reference_decision=used 时不能使用 image_gen。", path))
                if tool == "image_edit" and not (refs or visual_inputs or style_anchor_refs):
                    issues.append(issue("error", "episode_image_edit_reference_missing", f"{asset_id or '分集资产'} 使用 image_edit 时必须登记实际参考来源。", path))
                if tool == "image_edit" and visual_reference_decision == "none_available":
                    issues.append(issue("error", "episode_image_edit_visual_reference_decision_conflict", f"{asset_id or '分集资产'} 使用 image_edit 时 visual_reference_decision 不能写 none_available。", path))
                state_id = str(item.get("state_id") or "")
                if category == "character" and state_id and tool == "image_gen" and visual_reference_decision != "explicit_user_override":
                    issues.append(issue("error", "episode_character_state_asset_requires_image_edit", f"{asset_id or '角色状态资产'} 是人物状态资产时必须基于已批准人物图使用 image_edit；除非用户明确要求重做并记录 explicit_user_override。", path))
                check_generation_prompt_file(root, path, str(asset_id or "分集资产"), tool, generation.get("prompt_path"), issues)
                for file_value in item.get("files") or []:
                    if not file_exists(root, file_value):
                        issues.append(issue("error", "episode_asset_file_missing", f"分集资产文件不存在：{file_value}", path))
    return index


def ordered_inputs(root: Path, items: Any, allowed_roles: set[str], kind: str, path: Path, issues: list[dict[str, Any]]) -> tuple[list[int], set[str]]:
    if items is None:
        return [], set()
    if not isinstance(items, list):
        issues.append(issue("error", f"{kind}_inputs_invalid", f"{kind}_inputs 必须是数组。", path))
        return [], set()
    orders: list[int] = []
    roles: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            issues.append(issue("error", f"{kind}_input_invalid", f"{kind}_inputs 每项必须是对象。", path))
            continue
        order = item.get("order")
        if isinstance(order, int) and not isinstance(order, bool):
            orders.append(order)
        else:
            issues.append(issue("error", f"{kind}_input_order_invalid", f"{kind}_inputs.order 必须是整数。", path))
        role = item.get("role")
        if role in allowed_roles:
            roles.add(role)
        elif allowed_roles:
            issues.append(issue("error", f"{kind}_input_role_invalid", f"{kind}_inputs.role 无效：{role}", path))
        required_fields = ("source_id", "file", "adopt", "exclude") if kind == "reference" else ("resource_id", "file", "adopt", "exclude")
        for field in required_fields:
            if not str(item.get(field) or "").strip():
                issues.append(issue("error", f"{kind}_input_field_missing", f"{kind}_inputs.{field} 必须填写。", path))
        file_value = item.get("file")
        if file_value and not file_exists(root, file_value):
            issues.append(issue("error", f"{kind}_input_file_missing", f"输入文件不存在或不是项目相对路径：{file_value}", path))
        if kind == "reference" and isinstance(file_value, str) and Path(file_value).suffix.lower() not in IMAGE_INPUT_SUFFIXES:
            issues.append(issue("error", "reference_input_file_suffix_invalid", f"reference_inputs.file 必须是图片文件：{file_value}", path))
    if orders and sorted(orders) != list(range(1, len(orders) + 1)):
        issues.append(issue("error", f"{kind}_input_order_not_contiguous", f"{kind}_inputs.order 必须从 1 连续递增。", path))
    return orders, roles


def check_asset_ref(ref: Any, index: dict[str, Any], path: Path, issues: list[dict[str, Any]], owner: str) -> None:
    if not isinstance(ref, str) or not ref.strip():
        issues.append(issue("error", "asset_ref_invalid", f"{owner} 的 asset_refs 必须是非空字符串。", path))
        return
    if ref in index["known_asset_ids"]:
        issues.append(issue("error", "asset_ref_version_missing", f"{owner} 引用资产 {ref} 时必须带版本号。", path))
        return
    if ref not in index["known_version_refs"]:
        issues.append(issue("error", "asset_ref_unknown", f"{owner} 引用了不存在的资产版本：{ref}", path))
        return
    if ref not in index["approved_version_refs"]:
        issues.append(issue("error", "downstream_asset_not_approved", f"{owner} 引用了未 approved 的资产版本：{ref}", path))
        return
    check_stale_asset_version(ref, index, path, issues, owner)


def check_state_ref(ref: Any, index: dict[str, Any], path: Path, issues: list[dict[str, Any]], owner: str) -> None:
    if not isinstance(ref, str) or not ref.strip():
        issues.append(issue("error", "state_ref_invalid", f"{owner} 的 state_refs 必须是非空字符串。", path))
        return
    if ref not in index["known_state_refs"]:
        issues.append(issue("error", "state_ref_unknown", f"{owner} 引用了不存在的状态资产：{ref}", path))
        return
    if ref not in index["approved_state_refs"]:
        issues.append(issue("error", "downstream_state_not_approved", f"{owner} 引用了未 approved 的状态资产：{ref}", path))
        return
    check_stale_asset_version(ref, index, path, issues, owner)


def load_keyframe_ids(root: Path, episode_id: str, issues: list[dict[str, Any]]) -> set[str]:
    path = root / f"episodes/{episode_id}/03_资产/keyframe_manifest_{episode_id}.json"
    data = load_json(path, issues, required=False)
    keyframes = data.get("keyframes") if isinstance(data, dict) else None
    if not isinstance(keyframes, list):
        return set()
    return {item.get("keyframe_id") for item in keyframes if isinstance(item, dict) and isinstance(item.get("keyframe_id"), str)}


def marker_pattern(kind: str, order: int) -> str:
    patterns = {
        "image": rf"<(?:图片\s*{order}(?:\s*-\s*第\s*\d+\s*格)?|IMG\s*{order}(?:\s*-\s*Cell\s*\d+)?)\s*>",
        "video": rf"<(?:视频|VID)\s*{order}\s*>",
        "audio": rf"<(?:音频|AUD)\s*{order}\s*>",
    }
    return patterns[kind]


def extract_marker_orders(text: str, kind: str) -> list[int]:
    if kind == "image":
        pattern = r"<(?:图片\s*(\d+)(?:\s*-\s*第\s*\d+\s*格)?|IMG\s*(\d+)(?:\s*-\s*Cell\s*\d+)?)\s*>"
        orders: list[int] = []
        for cn_order, en_order in re.findall(pattern, text, flags=re.I):
            orders.append(int(cn_order or en_order))
        return orders
    patterns = {
        "video": r"<(?:视频|VID)\s*(\d+)\s*>",
        "audio": r"<(?:音频|AUD)\s*(\d+)\s*>",
    }
    return [int(match) for match in re.findall(patterns[kind], text, flags=re.I)]


def extract_subject_marker_orders(text: str) -> set[int]:
    orders: set[int] = set()
    pattern = r"<(?:主体\s*(\d+)|SUBJ\s*(\d+))\s*>"
    for cn_order, en_order in re.findall(pattern, text, flags=re.I):
        orders.add(int(cn_order or en_order))
    return orders


def check_prompt_markers(
    prompt_path: Path,
    image_orders: list[int],
    video_orders: list[int],
    audio_orders: list[int],
    speech_lines: Any,
    subtitle_enabled: bool,
    require_five_sections: bool,
    issues: list[dict[str, Any]],
) -> None:
    if not prompt_path.is_file():
        issues.append(issue("error", "prompt_missing", "Prompt 文件不存在。", prompt_path))
        return
    try:
        text = prompt_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        issues.append(issue("error", "prompt_unreadable", f"Prompt 无法读取：{exc}", prompt_path))
        return
    if require_five_sections:
        paragraph_count = len([block for block in re.split(r"\n\s*\n", text.strip()) if block.strip()])
        if paragraph_count != 5:
            issues.append(issue("error", "prompt_five_sections_invalid", f"最终视频 Prompt 必须恰好包含 5 个按空行分隔的信息段，当前为 {paragraph_count} 段。", prompt_path))
    expected_by_kind = {"image": sorted(image_orders), "video": sorted(video_orders), "audio": sorted(audio_orders)}
    for kind, expected in expected_by_kind.items():
        actual = sorted(set(extract_marker_orders(text, kind)))
        label = {"image": "图片", "video": "视频", "audio": "音频"}[kind]
        if actual != expected:
            issues.append(issue("error", f"prompt_{kind}_markers_mismatch", f"Prompt 中{label}标记 {actual} 必须与实际输入 order {expected} 一致。", prompt_path))
        for order in expected:
            if re.search(marker_pattern(kind, order), text, flags=re.I) is None:
                issues.append(issue("error", f"prompt_{kind}_marker_missing", f"Prompt 缺少第 {order} 个{label}标记。", prompt_path))
    cn = re.search(r"<(?:图片\s*\d+(?:\s*-\s*第\s*\d+\s*格)?|视频\s*\d+|音频\s*\d+|主体\s*\d+)\s*>", text)
    en = re.search(r"<(?:IMG\s*\d+(?:\s*-\s*Cell\s*\d+)?|VID\s*\d+|AUD\s*\d+|SUBJ\s*\d+)\s*>", text, flags=re.I)
    if cn and en:
        issues.append(issue("error", "prompt_marker_language_mixed", "同一 Prompt 不要混用中文和英文多媒体标记。", prompt_path))
    for order in sorted(extract_subject_marker_orders(text)):
        cn_labeled = rf"<\s*主体\s*{order}\s*>\s*[（(][^（）()\n]+[）)]"
        en_labeled = rf"<\s*SUBJ\s*{order}\s*>\s*[（(][^（）()\n]+[）)]"
        if not re.search(cn_labeled, text) and not re.search(en_labeled, text, flags=re.I):
            issues.append(issue("error", "prompt_subject_marker_label_missing", f"Prompt 使用 <主体{order}>/<SUBJ{order}> 时，必须至少一次写成 <主体{order}>(名称) 或 <SUBJ{order}>(name) 绑定主体身份。", prompt_path))
    if ("【" in text or "】" in text) and not subtitle_enabled:
        issues.append(issue("error", "prompt_subtitle_bracket_invalid", "未启用字幕时，最终视频 Prompt 不允许出现【】字幕源标识。", prompt_path))
    expected_speech: set[str] = set()
    if isinstance(speech_lines, list):
        for index, line in enumerate(speech_lines, start=1):
            if not isinstance(line, dict):
                issues.append(issue("error", "speech_line_invalid", f"speech_lines 第 {index} 条必须是对象。", prompt_path))
                continue
            spoken = str(line.get("spoken_text") or "").strip()
            if not spoken:
                issues.append(issue("error", "speech_line_spoken_text_missing", f"speech_lines 第 {index} 条缺少 spoken_text。", prompt_path))
                continue
            expected_speech.add(spoken)
            if f"{{{spoken}}}" not in text:
                issues.append(issue("error", "prompt_speech_line_missing", f"Prompt 缺少当前 SEG 台词：{{{spoken}}}", prompt_path))
    prompt_braces = {match.strip() for match in re.findall(r"\{([^{}\n]+)\}", text) if match.strip()}
    if expected_speech:
        extras = sorted(prompt_braces - expected_speech)
        if extras:
            issues.append(issue("error", "prompt_speech_line_extra", f"Prompt 中 {{}} 只能包裹当前 SEG 的 spoken_text，发现额外内容：{extras[:5]}", prompt_path))
    elif prompt_braces:
        issues.append(issue("error", "prompt_speech_line_unplanned", "Prompt 中出现花括号台词标记，但当前 SEG 未登记 speech_lines。", prompt_path))


def media_duration_s(item: dict[str, Any]) -> float | None:
    for field in ("duration_s", "uploaded_duration_s", "input_duration_s", "trimmed_duration_s", "source_duration_s"):
        value = item.get(field)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
    return None


def check_media_input_durations(segment: dict[str, Any], model_name: str, path: Path, issues: list[dict[str, Any]]) -> None:
    video_limit, audio_limit = media_to_video_limits(model_name)
    audio_inputs = segment.get("audio_inputs") or []
    video_inputs = segment.get("video_inputs") or []
    is_seedance20 = "seedance 2.0" in model_name.lower()
    if is_seedance20:
        if isinstance(video_inputs, list) and len(video_inputs) > 3:
            issues.append(issue("error", "seedance20_video_input_count_over_limit", f"{segment.get('segment_id') or 'segment'} 使用 seedance 2.0 时最多登记 3 个视频参考。", path))
        if isinstance(audio_inputs, list) and len(audio_inputs) > 3:
            issues.append(issue("error", "seedance20_audio_input_count_over_limit", f"{segment.get('segment_id') or 'segment'} 使用 seedance 2.0 时最多登记 3 个音频参考。", path))
    audio_total = 0.0
    audio_seen = False
    for item in audio_inputs:
        if not isinstance(item, dict):
            continue
        duration = media_duration_s(item)
        if duration is not None:
            audio_seen = True
            audio_total += duration
            if is_seedance20 and duration < 2:
                issues.append(issue("error", "seedance20_audio_input_too_short", f"{segment.get('segment_id') or 'segment'} 使用 seedance 2.0 时每个音频参考必须不少于 2 秒。", path))
    if audio_seen and audio_total > audio_limit:
        issues.append(issue("error", "audio_inputs_duration_over_limit", f"{segment.get('segment_id') or 'segment'} 上传音频合计 {audio_total:g} 秒，当前 media_to_video 模型上限为 {audio_limit} 秒。", path))
    video_total = 0.0
    video_seen = False
    for item in video_inputs:
        if not isinstance(item, dict):
            continue
        duration = media_duration_s(item)
        if duration is not None:
            video_seen = True
            video_total += duration
            if is_seedance20 and duration < 2:
                issues.append(issue("error", "seedance20_video_input_too_short", f"{segment.get('segment_id') or 'segment'} 使用 seedance 2.0 时每个视频参考必须不少于 2 秒。", path))
            if video_limit == DEFAULT_MEDIA_VIDEO_TOTAL_LIMIT_S and duration > DEFAULT_MEDIA_VIDEO_TOTAL_LIMIT_S:
                issues.append(issue("error", "video_input_duration_over_limit", f"{segment.get('segment_id') or 'segment'} 上传视频参考 {duration:g} 秒，默认 media_to_video 单条视频参考上限为 {DEFAULT_MEDIA_VIDEO_TOTAL_LIMIT_S} 秒；先裁剪 1-2 秒作为上传副本。", path))
    if video_seen and video_total > video_limit:
        issues.append(issue("error", "video_inputs_duration_over_limit", f"{segment.get('segment_id') or 'segment'} 上传视频参考总时长 {video_total:g} 秒，当前 media_to_video 模型上限为 {video_limit} 秒。", path))


def check_video_state_refs(segment: dict[str, Any], image_roles: set[str], asset_index: dict[str, Any], path: Path, issues: list[dict[str, Any]]) -> None:
    if not (image_roles & STATE_REFERENCE_ROLES):
        return
    state_refs = segment.get("state_refs")
    if not isinstance(state_refs, list) or not state_refs:
        issues.append(issue("error", "video_state_refs_missing", f"{segment.get('segment_id') or 'segment'} 传入角色/道具状态参考图时必须登记 approved state_refs。", path))
        return
    for ref in state_refs:
        check_state_ref(ref, asset_index, path, issues, str(segment.get("segment_id") or "视频片段"))


def generated_segment_indexes(segments: list[Any]) -> list[int]:
    indexes: list[int] = []
    for fallback_index, segment in enumerate(segments, start=1):
        if not isinstance(segment, dict):
            continue
        has_output = bool(str(segment.get("output_file") or "").strip())
        status = segment.get("status")
        if not has_output and status not in {"candidate", "accepted"}:
            continue
        index = segment.get("episode_segment_index")
        if isinstance(index, int) and not isinstance(index, bool):
            indexes.append(index)
        else:
            indexes.append(fallback_index)
    return sorted(set(indexes))


def markdown_table_column_counts(text: str) -> list[int]:
    counts: list[int] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        cells = [cell.strip() for cell in stripped[1:-1].split("|")]
        if cells and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            counts.append(len(cells))
    return counts


def check_video_generation_confirmations(
    data: dict[str, Any],
    segments: list[Any],
    path: Path,
    issues: list[dict[str, Any]],
    lightweight: bool = False,
) -> None:
    generated = generated_segment_indexes(segments)
    segments_by_index: dict[int, dict[str, Any]] = {}
    declared_indexes: list[int] = []
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        index_value = segment.get("episode_segment_index")
        if not isinstance(index_value, int) or isinstance(index_value, bool) or index_value < 1:
            issues.append(issue("error", "episode_segment_index_invalid", "每个视频片段必须填写从 1 开始的正整数 episode_segment_index。", path))
            continue
        if index_value in segments_by_index:
            issues.append(issue("error", "episode_segment_index_duplicate", f"episode_segment_index 重复：{index_value}", path))
            continue
        declared_indexes.append(index_value)
        segments_by_index[index_value] = segment
    if sorted(declared_indexes) != list(range(1, len(segments_by_index) + 1)):
        issues.append(issue("error", "episode_segment_index_not_contiguous", "episode_segment_index 必须唯一并按 1..N 连续编号。", path))
    confirmations = data.get("generation_confirmations")
    if not generated and not confirmations:
        return
    if not isinstance(confirmations, list):
        issues.append(issue("error", "video_generation_confirmations_missing", "视频阶段每轮生成都必须记录用户参数确认；每轮最多 2 个视频。", path))
        return
    if lightweight and confirmations and (
        not isinstance(confirmations[0], dict)
        or confirmations[0].get("confirmation_source") != "planning_preview"
    ):
        issues.append(issue("error", "lightweight_planning_confirmation_missing", "轻量模式首次生成确认必须来源于规划参数与五列预览。", path))
    confirmed_ranges: list[tuple[int, int]] = []
    confirmation_items: list[tuple[int, int, dict[str, Any], datetime | None]] = []
    previous_confirmations: list[tuple[int, int, str, datetime | None, int | None]] = []
    confirmation_ids: set[str] = set()
    for item in confirmations:
        if not isinstance(item, dict):
            issues.append(issue("error", "video_generation_confirmation_invalid", "generation_confirmations 每项必须是对象。", path))
            continue
        start = item.get("batch_start_segment_index")
        end = item.get("batch_end_segment_index")
        planned_count = item.get("planned_video_count")
        attempt = item.get("attempt")
        if not isinstance(attempt, int) or isinstance(attempt, bool) or attempt < 1:
            issues.append(issue("error", "video_generation_confirmation_attempt_invalid", "generation_confirmations.attempt 必须是从 1 开始的正整数。", path))
        confirmation_id = str(item.get("confirmation_id") or "").strip()
        if confirmation_id in confirmation_ids:
            issues.append(issue("error", "video_generation_confirmation_id_duplicate", f"generation_confirmations.confirmation_id 重复：{confirmation_id}", path))
        elif confirmation_id:
            confirmation_ids.add(confirmation_id)
        if not isinstance(start, int) or isinstance(start, bool) or not isinstance(end, int) or isinstance(end, bool):
            issues.append(issue("error", "video_generation_confirmation_range_invalid", "generation_confirmations 必须填写整数 batch_start_segment_index 和 batch_end_segment_index。", path))
            continue
        covered_count = end - start + 1
        if start < 1 or covered_count < 1 or covered_count > 2:
            issues.append(issue("error", "video_generation_confirmation_too_large", "一次用户确认只能覆盖连续的 1-2 个视频，且索引必须从 1 开始。", path))
            continue
        if start not in segments_by_index or end not in segments_by_index:
            issues.append(issue("error", "video_generation_confirmation_unknown_segment", "视频生成参数确认范围必须对应 video_manifest 中真实存在的连续 SEG。", path))
            continue
        confirmed_ranges.append((start, end))
        confirmed_at = parse_iso_time(item.get("confirmed_at"))
        confirmation_items.append((start, end, item, confirmed_at))
        supersedes = item.get("supersedes_confirmation_ids", [])
        if not isinstance(supersedes, list) or not all(isinstance(value, str) and value.strip() for value in supersedes):
            issues.append(issue("error", "video_generation_supersedes_invalid", "supersedes_confirmation_ids 必须是确认 ID 字符串数组。", path))
            supersedes = []
        overlapping_prior = [
            prior
            for prior in previous_confirmations
            if prior[0] <= end and start <= prior[1]
        ]
        overlapping_ids = {prior[2] for prior in overlapping_prior if prior[2]}
        if overlapping_ids and not overlapping_ids.issubset(set(supersedes)):
            issues.append(issue("error", "video_generation_confirmation_overlap", "重生或返修覆盖既有 SEG 时，必须通过 supersedes_confirmation_ids 显式替代所有重叠的旧确认。", path))
        unknown_supersedes = sorted(set(supersedes) - {prior[2] for prior in previous_confirmations})
        if unknown_supersedes:
            issues.append(issue("error", "video_generation_supersedes_unknown", f"supersedes_confirmation_ids 引用了不存在或尚未发生的确认：{unknown_supersedes}", path))
        unrelated_supersedes = sorted(set(supersedes) - overlapping_ids)
        if unrelated_supersedes:
            issues.append(issue("error", "video_generation_supersedes_unrelated", f"supersedes_confirmation_ids 只能列出与本次范围重叠的旧确认：{unrelated_supersedes}", path))
        for prior in overlapping_prior:
            if prior[2] in supersedes and confirmed_at is not None and prior[3] is not None and confirmed_at <= prior[3]:
                issues.append(issue("error", "video_generation_supersedes_time_invalid", "替代确认的 confirmed_at 必须晚于被替代确认。", path))
        if overlapping_prior and isinstance(attempt, int) and not isinstance(attempt, bool):
            prior_attempts = [prior[4] for prior in overlapping_prior if isinstance(prior[4], int)]
            if prior_attempts and attempt <= max(prior_attempts):
                issues.append(issue("error", "video_generation_confirmation_attempt_not_incremented", "返修或重生确认的 attempt 必须高于其覆盖的旧确认。", path))
        elif not overlapping_prior and attempt != 1:
            issues.append(issue("error", "video_generation_confirmation_initial_attempt_invalid", "首次覆盖一组 SEG 的确认 attempt 必须为 1。", path))
        previous_confirmations.append((start, end, confirmation_id, confirmed_at, attempt if isinstance(attempt, int) else None))
        if not isinstance(planned_count, int) or isinstance(planned_count, bool) or planned_count < 1 or planned_count > 2:
            issues.append(issue("error", "video_generation_count_invalid", "planned_video_count 必须是 1 或 2。", path))
        elif planned_count != covered_count:
            issues.append(issue("error", "video_generation_count_mismatch", "planned_video_count 必须等于本轮确认覆盖的 SEG 数。", path))
        for field in (
            "confirmation_id",
            "model",
            "aspect_ratio",
            "duration_s",
            "planned_video_count",
            "creative_direction",
            "cost_notice",
            "final_parameters_text",
            "interaction_ask_call_id",
            "interaction_ask_result",
            "user_message",
            "confirmed_at",
        ):
            if not str(item.get(field) or "").strip():
                issues.append(issue("error", "video_generation_confirmation_field_missing", f"视频生成参数确认缺少 {field}。", path))
        planning_preview_confirmation = lightweight and item.get("confirmation_source") == "planning_preview"
        if planning_preview_confirmation and (start != 1 or end != 1 or planned_count != 1):
            issues.append(issue("error", "lightweight_generation_scope_invalid", "轻量模式规划确认只能授权唯一一个视频。", path))
        expected_segments = [segments_by_index.get(index) for index in range(start, end + 1)]
        if any(segment is None for segment in expected_segments):
            issues.append(issue("error", "video_generation_confirmation_unknown_segment", "视频生成参数确认范围必须对应 video_manifest 中真实存在的连续 SEG。", path))
            expected_segments = []
        segment_durations = item.get("segment_durations")
        if not isinstance(segment_durations, list) or len(segment_durations) != covered_count:
            issues.append(issue("error", "video_generation_segment_durations_invalid", "segment_durations 必须逐 SEG 记录，项数等于本批次数量。", path))
        elif expected_segments:
            for offset, (duration_item, segment) in enumerate(zip(segment_durations, expected_segments), start=start):
                if not isinstance(duration_item, dict):
                    issues.append(issue("error", "video_generation_segment_duration_invalid", f"本批第 {offset} 个 segment_durations 必须是对象。", path))
                    continue
                expected_id = str(segment.get("segment_id") or "")
                expected_duration = segment.get("duration_s")
                if duration_item.get("segment_id") != expected_id:
                    issues.append(issue("error", "video_generation_segment_duration_id_mismatch", f"本批第 {offset} 个逐段时长必须对应 {expected_id}。", path))
                if duration_item.get("duration_s") != expected_duration:
                    issues.append(issue("error", "video_generation_segment_duration_mismatch", f"{expected_id} 的确认时长必须等于实际片段时长。", path))
            expected_total = sum(
                float(segment.get("duration_s"))
                for segment in expected_segments
                if isinstance(segment.get("duration_s"), (int, float)) and not isinstance(segment.get("duration_s"), bool)
            )
            if item.get("duration_s") != expected_total:
                issues.append(issue("error", "video_generation_total_duration_mismatch", "批次 duration_s 必须等于逐段时长之和。", path))
        displayed_parameters = item.get("displayed_parameter_table")
        required_parameter_fields = (
            "task_type",
            "delivery_format",
            "segment_durations",
            "total_duration",
            "aspect_ratio_and_resolution",
            "model",
            "visual_and_continuity",
            "audio_and_subtitles",
            "reference_materials",
            "tool_limits_and_cost",
        )
        if planning_preview_confirmation:
            required_lightweight_fields = {
                "task_type",
                "delivery_format",
                "quantity",
                "total_duration",
                "aspect_ratio_and_resolution",
                "model",
                "visual_and_continuity",
                "audio_and_subtitles",
                "reference_materials",
                "tool_limits_and_cost",
            }
            if not isinstance(displayed_parameters, dict):
                issues.append(issue("error", "lightweight_planning_parameters_missing", "轻量模式生成确认必须登记已展示的规划参数列表。", path))
            else:
                missing_fields = sorted(
                    field
                    for field in required_lightweight_fields
                    if not str(displayed_parameters.get(field) or "").strip()
                )
                if missing_fields:
                    issues.append(issue("error", "lightweight_planning_parameters_incomplete", f"轻量模式规划参数缺少视频生成确认字段：{missing_fields}", path))
                if displayed_parameters.get("quantity") != 1:
                    issues.append(issue("error", "lightweight_planning_quantity_invalid", "轻量模式视频数量必须为 1。", path))
        elif not isinstance(displayed_parameters, dict):
            issues.append(issue("error", "video_generation_parameter_table_missing", "必须登记实际展示的一张本批次合并参数确认表。", path))
        else:
            if displayed_parameters.get("quantity") != planned_count:
                issues.append(issue("error", "video_generation_displayed_quantity_mismatch", "参数确认表“数量”必须等于 planned_video_count。", path))
            for field in required_parameter_fields:
                value = displayed_parameters.get(field)
                if isinstance(value, list):
                    valid = bool(value) and all(str(entry).strip() for entry in value)
                else:
                    valid = bool(str(value or "").strip())
                if not valid:
                    issues.append(issue("error", "video_generation_parameter_table_field_missing", f"合并参数确认表缺少 {field}。", path))
                elif isinstance(value, list):
                    for entry in value:
                        if str(entry).strip() not in str(item.get("final_parameters_text") or ""):
                            issues.append(issue("error", "video_generation_parameter_table_text_mismatch", f"合并参数确认表展示文本缺少 {field} 项：{entry}。", path))
                elif str(value).strip() not in str(item.get("final_parameters_text") or ""):
                    issues.append(issue("error", "video_generation_parameter_table_text_mismatch", f"合并参数确认表展示文本缺少 {field} 的确认值。", path))
            displayed_durations = displayed_parameters.get("segment_durations")
            if isinstance(displayed_durations, list) and len(displayed_durations) != covered_count:
                issues.append(issue("error", "video_generation_displayed_duration_count_mismatch", "参数确认表必须按 SEG 分别展示时长，项数等于“数量”。", path))
            elif isinstance(displayed_durations, list) and expected_segments:
                for displayed_duration, segment in zip(displayed_durations, expected_segments):
                    expected_id = str(segment.get("segment_id") or "")
                    expected_duration = segment.get("duration_s")
                    duration_text = f"{expected_duration:g}" if isinstance(expected_duration, (int, float)) and not isinstance(expected_duration, bool) else str(expected_duration or "")
                    rendered = str(displayed_duration)
                    if expected_id not in rendered or not re.search(rf"{re.escape(duration_text)}\s*(?:秒|s\b|sec(?:ond)?s?\b)", rendered, flags=re.I):
                        issues.append(issue("error", "video_generation_displayed_duration_mismatch", f"参数确认表必须单独显示 {expected_id} 的真实时长。", path))
            displayed_model = str(displayed_parameters.get("model") or "")
            if str(item.get("model") or "") not in displayed_model:
                issues.append(issue("error", "video_generation_displayed_model_mismatch", "参数确认表中的视频模型必须匹配本批次 model。", path))
            displayed_format = str(displayed_parameters.get("aspect_ratio_and_resolution") or "")
            if str(item.get("aspect_ratio") or "") not in displayed_format:
                issues.append(issue("error", "video_generation_displayed_aspect_ratio_mismatch", "参数确认表中的画幅必须匹配本批次 aspect_ratio。", path))
            if expected_segments:
                expected_total = sum(
                    float(segment.get("duration_s"))
                    for segment in expected_segments
                    if isinstance(segment.get("duration_s"), (int, float)) and not isinstance(segment.get("duration_s"), bool)
                )
                total_text = f"{expected_total:g}"
                if not re.search(rf"{re.escape(total_text)}\s*(?:秒|s\b|sec(?:ond)?s?\b)", str(displayed_parameters.get("total_duration") or ""), flags=re.I):
                    issues.append(issue("error", "video_generation_displayed_total_duration_mismatch", "参数确认表中的总时长必须等于本批次逐段时长之和。", path))
        storyboard_rows = item.get("displayed_storyboard_rows")
        if planning_preview_confirmation:
            if not isinstance(storyboard_rows, list) or not 1 <= len(storyboard_rows) <= 8:
                issues.append(issue("error", "lightweight_planning_preview_rows_invalid", "轻量模式规划五列预览必须为 1-8 行。", path))
            elif any(not isinstance(row, dict) or not all(str(row.get(field) or "").strip() for field in ("time_range", "story_and_action", "audio", "camera_transition", "hook")) for row in storyboard_rows):
                issues.append(issue("error", "lightweight_planning_preview_field_missing", "轻量模式规划五列预览每行必须填写时间、剧情动作、声音、运镜衔接和钩子。", path))
        elif not isinstance(storyboard_rows, list) or len(storyboard_rows) != covered_count:
            issues.append(issue("error", "video_generation_storyboard_rows_invalid", "本批次五列分镜表必须每个 SEG 恰好一行，行数等于“数量”。", path))
        elif expected_segments:
            for offset, (row, segment) in enumerate(zip(storyboard_rows, expected_segments), start=start):
                if not isinstance(row, dict):
                    issues.append(issue("error", "video_generation_storyboard_row_invalid", f"本批第 {offset} 行分镜必须是对象。", path))
                    continue
                expected_id = str(segment.get("segment_id") or "")
                if row.get("segment_id") != expected_id or row.get("duration_s") != segment.get("duration_s"):
                    issues.append(issue("error", "video_generation_storyboard_segment_mismatch", f"本批五列分镜第 {offset} 行的片段与时长必须匹配 {expected_id}。", path))
                for field in ("visual_content", "subject_action", "audio", "camera_and_materials"):
                    if not str(row.get(field) or "").strip():
                        issues.append(issue("error", "video_generation_storyboard_field_missing", f"{expected_id} 五列分镜缺少 {field}。", path))
                    elif str(row.get(field)).strip() not in str(item.get("final_parameters_text") or ""):
                        issues.append(issue("error", "video_generation_storyboard_text_mismatch", f"final_parameters_text 缺少 {expected_id} 五列分镜中的 {field} 内容。", path))
                row_audio = str(row.get("audio") or "")
                for speech_line in segment.get("speech_lines") or []:
                    if not isinstance(speech_line, dict):
                        continue
                    spoken_text = str(speech_line.get("spoken_text") or "").strip()
                    if spoken_text and spoken_text not in row_audio:
                        issues.append(issue("error", "video_generation_storyboard_speech_missing", f"{expected_id} 五列分镜必须完整列出本段台词：{spoken_text}", path))
        final_parameters_text = str(item.get("final_parameters_text") or "")
        expected_table_counts = [5] if planning_preview_confirmation else [2, 5]
        if markdown_table_column_counts(final_parameters_text) != expected_table_counts:
            issues.append(issue("error", "video_generation_confirmation_tables_invalid", "视频生成确认展示结构与当前模式不一致。", path))
        if expected_segments and not planning_preview_confirmation:
            for segment in expected_segments:
                segment_id = str(segment.get("segment_id") or "")
                duration = segment.get("duration_s")
                duration_text = f"{duration:g}" if isinstance(duration, (int, float)) and not isinstance(duration, bool) else str(duration or "")
                if segment_id not in final_parameters_text or not re.search(rf"{re.escape(duration_text)}\s*(?:秒|s\b|sec(?:ond)?s?\b)", final_parameters_text, flags=re.I):
                    issues.append(issue("error", "video_generation_segment_details_not_displayed", f"final_parameters_text 必须分别显示 {segment_id} 及其时长。", path))
        if confirmed_at is None:
            issues.append(issue("error", "video_generation_confirmation_time_invalid", "视频生成参数确认 confirmed_at 必须是带时区 ISO-8601 时间。", path))
        if str(item.get("interaction_ask_result") or "").strip() != "generate":
            issues.append(issue("error", "video_generation_interaction_confirmation_missing", "视频生成参数确认必须登记 interaction.ask 返回 generate；普通文字确认不能替代执行确认。", path))
        cost_notice = str(item.get("cost_notice") or "")
        if not cost_notice.strip():
            issues.append(issue("error", "video_generation_cost_notice_missing", "视频生成参数确认必须登记非空 cost_notice；具体措辞由主 Agent 人工复核。", path))
        model = str(item.get("model") or "")
        if "seedance 2.5" in model.lower():
            membership_notice = str(item.get("membership_notice") or "")
            if not membership_notice.strip():
                issues.append(issue("error", "video_generation_membership_notice_missing", "使用 seedance 2.5 时必须登记非空 membership_notice；具体措辞由主 Agent 人工复核。", path))
    for index in generated:
        if not any(start <= index <= end for start, end in confirmed_ranges):
            issues.append(issue("error", "video_generation_confirmation_missing", f"生成 SEG{index:03d} 前必须先取得覆盖该片段的用户确认。", path))
    for fallback_index, segment in enumerate(segments, start=1):
        if not isinstance(segment, dict):
            continue
        generated_segment = bool(str(segment.get("output_file") or "").strip()) or segment.get("status") in {"candidate", "accepted"}
        if not generated_segment:
            continue
        index_value = segment.get("episode_segment_index")
        segment_index = index_value if isinstance(index_value, int) and not isinstance(index_value, bool) else fallback_index
        matching = [item for item in confirmation_items if item[0] <= segment_index <= item[1]]
        if not matching:
            continue
        confirmation_id = str(segment.get("generation_confirmation_id") or "").strip()
        if not confirmation_id:
            issues.append(issue("error", "video_generation_confirmation_id_missing", f"SEG{segment_index:03d} 已生成，必须登记 generation_confirmation_id。", path))
        elif all(str(item[2].get("confirmation_id") or "").strip() != confirmation_id for item in matching):
            issues.append(issue("error", "video_generation_confirmation_id_mismatch", f"SEG{segment_index:03d} generation_confirmation_id 必须匹配覆盖该片段的视频生成参数确认。", path))
        else:
            latest = matching[-1]
            if confirmation_id != str(latest[2].get("confirmation_id") or "").strip():
                issues.append(issue("error", "video_generation_confirmation_not_latest", f"SEG{segment_index:03d} 必须引用覆盖该片段的最新有效确认。", path))
        if not str(segment.get("tool_call_id") or "").strip():
            issues.append(issue("error", "video_tool_call_id_missing", f"SEG{segment_index:03d} 已生成，必须登记实际视频工具 tool_call_id。", path))
        called_at = parse_iso_time(segment.get("tool_called_at"))
        if called_at is None:
            issues.append(issue("error", "video_tool_called_at_invalid", f"SEG{segment_index:03d} 已生成，必须登记带时区 ISO-8601 tool_called_at。", path))
            continue
        latest_confirmed_at = matching[-1][3]
        if latest_confirmed_at is None or latest_confirmed_at >= called_at:
            issues.append(issue("error", "video_confirmation_after_tool_call", f"SEG{segment_index:03d} 的视频生成参数确认时间必须早于视频工具调用时间。", path))


def check_voice_audio_inputs(segment: dict[str, Any], audio_roles: set[str], path: Path, issues: list[dict[str, Any]]) -> None:
    speech_lines = segment.get("speech_lines")
    if not isinstance(speech_lines, list) or not speech_lines:
        return
    segment_label = str(segment.get("segment_id") or "segment")
    audio_input_supported = segment.get("audio_input_supported") is True
    has_voice_audio_reference = "voice_audio_reference" in audio_roles
    voice_inputs = segment.get("voice_inputs")

    if not audio_input_supported and not has_voice_audio_reference:
        if isinstance(voice_inputs, list) and voice_inputs:
            issues.append(issue("error", "voice_inputs_without_audio_reference", f"{segment_label} 未传 VOICE 音频时不得登记 voice_inputs；请改用 speech_lines.voice_anchor 作为文字音色锚点。", path))
        for index, line in enumerate(speech_lines, start=1):
            if not isinstance(line, dict):
                continue
            if not str(line.get("voice_anchor") or "").strip():
                issues.append(issue("error", "speech_line_voice_anchor_missing", f"{segment_label} speech_lines 第 {index} 条未传 VOICE 音频时必须填写固定 voice_anchor。", path))
        return

    if audio_input_supported and not has_voice_audio_reference:
        issues.append(issue("error", "voice_audio_input_missing", f"{segment_label} 支持音频输入且有 speech_lines 时必须上传 approved VOICE 音频。", path))
    if has_voice_audio_reference and not audio_input_supported:
        issues.append(issue("error", "voice_audio_support_flag_missing", f"{segment_label} 已传 voice_audio_reference 时 audio_input_supported 必须为 true。", path))
    if not isinstance(voice_inputs, list) or not voice_inputs:
        issues.append(issue("error", "voice_inputs_missing", f"{segment_label} 有 speech_lines 时必须登记 voice_inputs。", path))
        return
    voice_ids = {
        item.get("voice_id")
        for item in voice_inputs
        if isinstance(item, dict) and isinstance(item.get("voice_id"), str) and item.get("voice_id").strip()
    }
    resource_ids = {
        item.get("resource_id")
        for item in voice_inputs
        if isinstance(item, dict) and isinstance(item.get("resource_id"), str) and item.get("resource_id").strip()
    }
    if not voice_ids or not resource_ids:
        issues.append(issue("error", "voice_inputs_incomplete", f"{segment_label} voice_inputs 必须填写 voice_id 和 resource_id。", path))
    for index, line in enumerate(speech_lines, start=1):
        if not isinstance(line, dict):
            continue
        voice_id = line.get("voice_id")
        if isinstance(voice_id, str) and voice_id.strip() and voice_id not in voice_ids:
            issues.append(issue("error", "speech_line_voice_input_missing", f"{segment_label} speech_lines 第 {index} 条 voice_id 未在 voice_inputs 中登记：{voice_id}", path))


def check_voice_anchor_consistency(segment: dict[str, Any], seen: dict[str, str], path: Path, issues: list[dict[str, Any]]) -> None:
    speech_lines = segment.get("speech_lines")
    if not isinstance(speech_lines, list):
        return
    segment_label = str(segment.get("segment_id") or "segment")
    for index, line in enumerate(speech_lines, start=1):
        if not isinstance(line, dict):
            continue
        voice_id = str(line.get("voice_id") or "").strip()
        if not voice_id:
            continue
        voice_anchor = str(line.get("voice_anchor") or "").strip()
        if not voice_anchor:
            issues.append(issue("error", "speech_line_voice_anchor_missing", f"{segment_label} speech_lines 第 {index} 条有 voice_id 但缺少固定 voice_anchor。", path))
            continue
        previous = seen.get(voice_id)
        if previous is None:
            seen[voice_id] = voice_anchor
        elif previous != voice_anchor:
            issues.append(issue("error", "speech_line_voice_anchor_inconsistent", f"{segment_label} speech_lines 第 {index} 条 voice_id={voice_id} 的 voice_anchor 必须与同一人物前文完全一致。", path))


def check_prompt_preflight(segment: dict[str, Any], expected_shot_ids: list[str], path: Path, issues: list[dict[str, Any]]) -> None:
    label = str(segment.get("segment_id") or "segment")
    preflight = segment.get("prompt_preflight")
    if not isinstance(preflight, dict):
        issues.append(issue("error", "prompt_preflight_missing", f"{label} 必须登记一次集中 Prompt 预检和一次最终客观校验。", path))
        return
    if preflight.get("review_count") != 1:
        issues.append(issue("error", "prompt_preflight_review_count_invalid", f"{label} prompt_preflight.review_count 必须为 1。", path))
    revision_count = preflight.get("revision_count")
    if revision_count not in {0, 1}:
        issues.append(issue("error", "prompt_preflight_revision_count_invalid", f"{label} Prompt 集中修订最多 1 次。", path))
    if preflight.get("final_validation_count") != 1:
        issues.append(issue("error", "prompt_final_validation_count_invalid", f"{label} prompt_preflight.final_validation_count 必须为 1。", path))
    if preflight.get("five_sections_in_order") is not True:
        issues.append(issue("error", "prompt_five_sections_not_verified", f"{label} 必须确认五段式顺序完整。", path))
    compiled_once = preflight.get("shot_ids_compiled_once")
    if not isinstance(compiled_once, list) or compiled_once != expected_shot_ids or len(set(compiled_once)) != len(compiled_once):
        issues.append(issue("error", "prompt_shot_preflight_mismatch", f"{label} shot_ids_compiled_once 必须按分镜顺序恰好列出每个镜头一次。", path))
    if preflight.get("result") != "passed":
        issues.append(issue("error", "prompt_preflight_not_passed", f"{label} 最终客观校验必须通过后才能生成。", path))


def check_keyframes(
    root: Path,
    asset_index: dict[str, Any],
    issues: list[dict[str, Any]],
    episode_filter: str | None = None,
) -> None:
    for episode_id, episode_root in episode_dirs(root, episode_filter):
        path = episode_root / f"03_资产/keyframe_manifest_{episode_id}.json"
        data = load_json(path, issues, required=False)
        if not isinstance(data, dict):
            continue
        if data.get("episode_id") != episode_id:
            issues.append(issue("error", "episode_id_mismatch", "keyframe_manifest episode_id 与目录不一致。", path))
        index = load_storyboard_index(root, episode_id, issues)
        keyframes = data.get("keyframes")
        if not isinstance(keyframes, list):
            issues.append(issue("error", "keyframes_invalid", "keyframes 必须是数组。", path))
            continue
        check_unique(keyframes, "keyframe_id", path, issues, "keyframes")
        planned_keyframes = {
            segment_id: len(requests)
            for segment_id, requests in index.get("keyframe_requests", {}).items()
            if isinstance(segment_id, str) and isinstance(requests, list)
        }
        actual_keyframes: dict[str, int] = {}
        seen_highlight_indexes: set[tuple[str, int]] = set()
        for item in keyframes:
            if not isinstance(item, dict):
                continue
            keyframe_id = item.get("keyframe_id")
            segment_id = item.get("segment_id")
            shot_id = item.get("shot_id")
            if isinstance(segment_id, str) and index["segments"] and segment_id not in index["segments"]:
                issues.append(issue("error", "keyframe_unknown_segment", f"关键帧引用了不存在的 segment_id：{segment_id}", path))
            if isinstance(shot_id, str) and index["shots"] and shot_id not in index["shots"]:
                issues.append(issue("error", "keyframe_unknown_shot", f"关键帧引用了不存在的 shot_id：{shot_id}", path))
            status = str(item.get("status") or "").strip()
            if isinstance(segment_id, str) and status not in {"rejected", "superseded"}:
                actual_keyframes[segment_id] = actual_keyframes.get(segment_id, 0) + 1
            if item.get("role") != "highlight":
                issues.append(issue("error", "keyframe_role_invalid", f"{keyframe_id or '关键帧'} role 必须为 highlight。", path))
            highlight_index = item.get("highlight_index")
            if not isinstance(highlight_index, int) or isinstance(highlight_index, bool) or highlight_index < 1:
                issues.append(issue("error", "keyframe_highlight_index_invalid", f"{keyframe_id or '关键帧'} highlight_index 必须是从 1 开始的正整数。", path))
            elif isinstance(segment_id, str):
                key = (segment_id, highlight_index)
                if key in seen_highlight_indexes:
                    issues.append(issue("error", "keyframe_highlight_index_duplicate", f"{segment_id} 的 highlight_index={highlight_index} 重复。", path))
                seen_highlight_indexes.add(key)
            for used_segment in item.get("used_by_segments") or []:
                if index["segments"] and used_segment not in index["segments"]:
                    issues.append(issue("error", "keyframe_unknown_used_segment", f"used_by_segments 引用了不存在的 segment_id：{used_segment}", path))
            file_value = item.get("file")
            if file_value and not file_exists(root, file_value):
                issues.append(issue("error", "keyframe_file_missing", f"关键帧文件不存在：{file_value}", path))
            if isinstance(file_value, str) and not re.search(r"关键帧_KF\d+_SEG\d+_highlight-\d+_v\d+_ep_[1-9]\d*\.[A-Za-z0-9]+$", file_value):
                issues.append(issue("error", "keyframe_file_name_invalid", f"{keyframe_id or '关键帧'} 文件名必须使用 highlight-N 高光序号。", path))
            if item.get("tool") != "image_edit":
                issues.append(issue("error", "keyframe_tool_not_image_edit", f"{keyframe_id or '关键帧'} 必须使用 image_edit I2I 生成，不得使用 image_gen 或纯文生图。", path))
            asset_refs = item.get("asset_refs")
            if asset_refs is not None:
                if not isinstance(asset_refs, list):
                    issues.append(issue("error", "asset_refs_invalid", f"{keyframe_id or '关键帧'} asset_refs 必须是数组。", path))
                else:
                    for ref in asset_refs:
                        check_asset_ref(ref, asset_index, path, issues, str(keyframe_id or "关键帧"))
            state_refs = item.get("state_refs")
            if state_refs is not None:
                if not isinstance(state_refs, list):
                    issues.append(issue("error", "state_refs_invalid", f"{keyframe_id or '关键帧'} state_refs 必须是数组。", path))
                else:
                    for ref in state_refs:
                        check_state_ref(ref, asset_index, path, issues, str(keyframe_id or "关键帧"))
            style_terms = combined_strings(item, field="style_prompt_terms")
            check_style_anchor_contract(
                root,
                path,
                str(keyframe_id or "关键帧"),
                item.get("tool"),
                item.get("prompt_path"),
                combined_strings(item, field="style_anchor_reference_ids"),
                style_terms,
                combined_strings(item, field="style_adopt"),
                combined_strings(item, field="style_exclude"),
                issues,
            )
            check_generation_prompt_file(root, path, str(keyframe_id or "关键帧"), item.get("tool"), item.get("prompt_path"), issues)
        for segment_id, actual_count in actual_keyframes.items():
            if planned_keyframes.get(segment_id, 0) == 0 and actual_count:
                issues.append(issue("error", "keyframe_unplanned_segment", f"{segment_id} 实际生成了 {actual_count} 张有效关键帧，但 storyboard.keyframe_requests 未规划该段关键帧。", path))
        planned_total = sum(planned_keyframes.values())
        actual_total = sum(actual_keyframes.values())
        if planned_total and actual_total != planned_total:
            issues.append(issue("error", "episode_keyframe_count_mismatch", f"本集实际有效关键帧数量 {actual_total} 必须等于 storyboard.keyframe_requests 规划总数 {planned_total}。", path))
        for segment_id, planned_count in planned_keyframes.items():
            actual_count = actual_keyframes.get(segment_id, 0)
            if actual_count != planned_count:
                issues.append(issue("error", "keyframe_count_mismatch", f"{segment_id} 实际有效关键帧数量 {actual_count} 必须等于 storyboard.keyframe_requests 规划数量 {planned_count}。", path))

def check_video(
    root: Path,
    asset_index: dict[str, Any],
    plan: Any,
    issues: list[dict[str, Any]],
    episode_filter: str | None = None,
    require_accepted: bool = True,
) -> None:
    lightweight = is_lightweight_plan(plan) and lightweight_constraints_valid(plan)
    for episode_id, episode_root in episode_dirs(root, episode_filter):
        path = episode_root / f"04_视频片段/video_manifest_{episode_id}.json"
        data = load_json(path, issues, required=False)
        if not isinstance(data, dict):
            continue
        if data.get("episode_id") != episode_id:
            issues.append(issue("error", "episode_id_mismatch", "video_manifest episode_id 与目录不一致。", path))
        index = load_storyboard_index(root, episode_id, issues)
        keyframe_ids = load_keyframe_ids(root, episode_id, issues)
        segments = data.get("segments")
        if not isinstance(segments, list):
            issues.append(issue("error", "video_segments_invalid", "video_manifest.segments 必须是数组。", path))
            continue
        if lightweight and len(segments) != 1:
            issues.append(issue("error", "lightweight_video_count_invalid", "轻量模式必须只生成一个最终视频；多个独立视频必须拆为独立任务。", path))
        check_video_generation_confirmations(data, segments, path, issues, lightweight)
        if lightweight and isinstance(data.get("generation_confirmations"), list) and data["generation_confirmations"]:
            planning_records = [
                record
                for record in load_confirmation_records(root, issues, required=True)
                if record.get("stage") == "planning"
                and record.get("confirmation_purpose") == "video_generation"
                and record.get("interaction_ask_result") == "generate"
            ]
            latest_planning = max(planning_records, key=lambda record: record.get("revision", 0), default={})
            first_generation = data["generation_confirmations"][0]
            if not isinstance(first_generation, dict) or first_generation.get("interaction_ask_call_id") != latest_planning.get("interaction_ask_call_id"):
                issues.append(issue("error", "lightweight_confirmation_call_mismatch", "轻量模式 planning 与首次视频生成记录必须复用同一个 interaction.ask 调用 ID。", path))
        video_segment_ids = check_unique(segments, "segment_id", path, issues, "video segments")
        if index["segments"]:
            missing_segments = sorted(index["segments"] - video_segment_ids)
            extra_segments = sorted(video_segment_ids - index["segments"])
            if missing_segments:
                issues.append(issue("error", "video_segment_missing", f"video_manifest 缺少 storyboard segment：{missing_segments}", path))
            if extra_segments:
                issues.append(issue("error", "video_segment_unplanned", f"video_manifest 含 storyboard 中不存在的 segment：{extra_segments}", path))
        if isinstance(data.get("duration_s"), (int, float)):
            calculated = int(round(sum(float(s.get("duration_s")) for s in segments if isinstance(s, dict) and isinstance(s.get("duration_s"), (int, float)))))
            if calculated and int(round(float(data["duration_s"]))) != calculated:
                issues.append(issue("error", "video_duration_mismatch", "video_manifest.duration_s 必须等于 segments.duration_s 之和。", path))
        seen_voice_anchors: dict[str, str] = {}
        for segment in segments:
            if not isinstance(segment, dict):
                issues.append(issue("error", "video_segment_invalid", "segments 每项必须是对象。", path))
                continue
            segment_id = segment.get("segment_id")
            if isinstance(segment_id, str) and index["segments"] and segment_id not in index["segments"]:
                issues.append(issue("error", "video_unknown_segment", f"视频引用了分镜中不存在的 segment_id：{segment_id}", path))
            storyboard_duration = index["segment_durations"].get(segment_id)
            if storyboard_duration is not None and isinstance(segment.get("duration_s"), (int, float)):
                if int(round(float(segment["duration_s"]))) != int(round(float(storyboard_duration))):
                    issues.append(issue("error", "video_segment_duration_mismatch", f"{segment_id} 时长必须与分镜片段时长一致。", path))
            tool_mode = segment.get("tool_mode")
            image_orders, image_roles = ordered_inputs(root, segment.get("reference_inputs"), REFERENCE_ROLES, "reference", path, issues)
            video_orders, video_roles = ordered_inputs(root, segment.get("video_inputs"), VIDEO_INPUT_ROLES, "video", path, issues)
            audio_orders, audio_roles = ordered_inputs(root, segment.get("audio_inputs"), AUDIO_INPUT_ROLES, "audio", path, issues)
            required_roles = segment.get("required_reference_roles")
            model_name = video_model_name(plan, data, segment)
            if tool_mode not in VIDEO_TOOL_MODES:
                issues.append(issue("error", "video_tool_mode_invalid", f"{segment_id or 'segment'} tool_mode 无效：{tool_mode}", path))
            else:
                check_voice_anchor_consistency(segment, seen_voice_anchors, path, issues)
            if tool_mode == "text_to_video":
                if image_orders or video_orders or audio_orders or segment.get("voice_inputs"):
                    issues.append(issue("error", "text_to_video_input_invalid", "text_to_video 只能用于没有图片、视频、音频或 voice_inputs 的片段。", path))
            if tool_mode == "media_to_video":
                check_media_input_durations(segment, model_name, path, issues)
                check_voice_audio_inputs(segment, audio_roles, path, issues)
                check_video_state_refs(segment, image_roles, asset_index, path, issues)
                if not video_orders and not audio_orders:
                    issues.append(issue("error", "media_to_video_media_missing", "media_to_video 必须至少登记一个真实视频或音频输入。", path))
                planned_roles = index["required_reference_roles"].get(segment_id, set()) if isinstance(segment_id, str) else set()
                declared_roles = set(required_roles) if isinstance(required_roles, list) else set()
                if image_orders or planned_roles:
                    if not isinstance(required_roles, list) or not required_roles:
                        issues.append(issue("error", "required_reference_roles_missing", "media_to_video 使用图片或分镜声明图片职责时必须填写 required_reference_roles。", path))
                    elif any(role not in REFERENCE_ROLES for role in required_roles):
                        issues.append(issue("error", "required_reference_role_invalid", "required_reference_roles 含无效职责。", path))
                    elif not set(required_roles).issubset(image_roles):
                        missing = sorted(set(required_roles) - image_roles)
                        issues.append(issue("error", "required_reference_role_not_passed", f"required_reference_roles 未真实传入：{missing}", path))
                elif required_roles not in (None, []):
                    issues.append(issue("error", "required_reference_roles_unexpected", "media_to_video 没有图片输入时 required_reference_roles 应为空或省略。", path))
                if planned_roles and not planned_roles.issubset(declared_roles):
                    missing = sorted(planned_roles - declared_roles)
                    issues.append(issue("error", "storyboard_required_role_not_inherited", f"{segment_id} 未继承 storyboard.required_reference_roles：{missing}", path))
                if planned_roles and not planned_roles.issubset(image_roles):
                    missing = sorted(planned_roles - image_roles)
                    issues.append(issue("error", "storyboard_required_role_not_passed", f"{segment_id} 的 storyboard.required_reference_roles 未真实传入：{missing}", path))
            if tool_mode == "image_to_video":
                check_video_state_refs(segment, image_roles, asset_index, path, issues)
                if not image_orders:
                    issues.append(issue("error", "image_to_video_reference_missing", "image_to_video 必须登记实际传入参考图。", path))
                if video_orders or audio_orders or segment.get("voice_inputs"):
                    issues.append(issue("error", "image_to_video_input_invalid", "image_to_video 不支持上传视频、音频或 voice_inputs；本路由只能传参考图。", path))
                if not isinstance(required_roles, list) or not required_roles:
                    issues.append(issue("error", "required_reference_roles_missing", "image_to_video 必须声明 required_reference_roles。", path))
                elif any(role not in REFERENCE_ROLES for role in required_roles):
                    issues.append(issue("error", "required_reference_role_invalid", "required_reference_roles 含无效职责。", path))
                elif not set(required_roles).issubset(image_roles):
                    missing = sorted(set(required_roles) - image_roles)
                    issues.append(issue("error", "required_reference_role_not_passed", f"required_reference_roles 未真实传入：{missing}", path))
                planned_roles = index["required_reference_roles"].get(segment_id, set()) if isinstance(segment_id, str) else set()
                declared_roles = set(required_roles) if isinstance(required_roles, list) else set()
                if planned_roles and not planned_roles.issubset(declared_roles):
                    missing = sorted(planned_roles - declared_roles)
                    issues.append(issue("error", "storyboard_required_role_not_inherited", f"{segment_id} 未继承 storyboard.required_reference_roles：{missing}", path))
                if planned_roles and not planned_roles.issubset(image_roles):
                    missing = sorted(planned_roles - image_roles)
                    issues.append(issue("error", "storyboard_required_role_not_passed", f"{segment_id} 的 storyboard.required_reference_roles 未真实传入：{missing}", path))
            if tool_mode == "video_edit":
                if image_orders or audio_orders or segment.get("voice_inputs"):
                    issues.append(issue("error", "video_edit_input_invalid", "video_edit 只登记源视频，不登记图片、音频或 voice_inputs。", path))
                if video_roles != {"source_video_for_edit"} or len(video_orders) != 1:
                    issues.append(issue("error", "video_edit_source_invalid", "video_edit 必须且只能登记一个 source_video_for_edit 源视频。", path))
            for input_item in segment.get("reference_inputs") or []:
                if not isinstance(input_item, dict):
                    continue
                source_type = input_item.get("source_type")
                source_id = input_item.get("source_id")
                role = input_item.get("role")
                if role == "previous_tail_as_start_frame" and source_type != "frame":
                    issues.append(issue("error", "previous_tail_source_type_invalid", f"{segment_id} 上一段尾帧必须以 source_type=frame 真实传入。", path))
                if source_type == "asset":
                    if role in STATE_REFERENCE_ROLES:
                        check_state_ref(source_id, asset_index, path, issues, f"{segment_id or '视频片段'} reference_inputs")
                    else:
                        check_asset_ref(source_id, asset_index, path, issues, f"{segment_id or '视频片段'} reference_inputs")
                if source_type == "keyframe" and isinstance(source_id, str) and keyframe_ids and source_id not in keyframe_ids:
                    issues.append(issue("error", "video_reference_unknown_keyframe", f"{segment_id} 引用了不存在的关键帧：{source_id}", path))
            prompt_file = segment.get("compiled_prompt_file")
            prompt_path = relative_file(root, prompt_file)
            if lightweight:
                raw_shot_ids = segment.get("shot_ids")
                expected_shot_ids = raw_shot_ids if isinstance(raw_shot_ids, list) else []
            else:
                expected_shot_ids = index["segment_shots"].get(segment_id, []) if isinstance(segment_id, str) else []
            if tool_mode != "video_edit":
                check_prompt_preflight(segment, expected_shot_ids, path, issues)
            if prompt_path is not None:
                check_prompt_markers(
                    prompt_path,
                    image_orders,
                    video_orders,
                    audio_orders,
                    segment.get("speech_lines"),
                    segment.get("subtitle_enabled") is True,
                    tool_mode != "video_edit",
                    issues,
                )
                prompt_sha256 = str(segment.get("prompt_sha256") or "").strip()
                if prompt_sha256:
                    try:
                        actual_sha256 = file_sha256(prompt_path)
                    except OSError as exc:
                        issues.append(issue("error", "prompt_sha256_unreadable", f"无法读取 Prompt 计算 sha256：{exc}", prompt_path))
                    else:
                        if actual_sha256 != prompt_sha256:
                            issues.append(issue("error", "prompt_sha256_mismatch", f"{segment_id} prompt_sha256 与实际 Prompt 文件不一致。", prompt_path))
            elif prompt_file:
                issues.append(issue("error", "prompt_path_invalid", "compiled_prompt_file 必须是项目相对路径。", path))
            generated_segment = bool(str(segment.get("output_file") or "").strip()) or segment.get("status") in {"candidate", "accepted"}
            if generated_segment and (prompt_path is None or not prompt_path.is_file()):
                issues.append(issue("error", "generated_segment_prompt_missing", f"{segment_id} 已生成或进入候选/验收状态，必须登记真实存在的 compiled_prompt_file。", path))
            if generated_segment and not str(segment.get("prompt_sha256") or "").strip():
                issues.append(issue("error", "generated_segment_prompt_sha256_missing", f"{segment_id} 已生成或进入候选/验收状态，必须登记实际提交 Prompt 文件的 prompt_sha256。", path))
            status = segment.get("status")
            if status not in {None, *VIDEO_STATUS_VALUES}:
                issues.append(issue("error", "video_status_invalid", f"视频片段状态无效：{status}", path))
            elif require_accepted and status != "accepted":
                issues.append(issue("error", "video_segment_not_accepted", f"{segment_id or '视频片段'} 必须在进入成片阶段前登记 status=accepted。", path))
            elif not require_accepted and generated_segment and status not in {"candidate", "accepted"}:
                issues.append(issue("error", "video_segment_not_ready_for_confirmation", f"{segment_id or '视频片段'} 在发起拼接确认前必须登记 status=candidate 或 accepted。", path))
            if status == "candidate" and not file_exists(root, segment.get("output_file")):
                issues.append(issue("error", "video_segment_output_missing", f"{segment_id} 已进入候选状态，但 output_file 不存在。", path))
            if status == "accepted":
                if not file_exists(root, segment.get("output_file")):
                    issues.append(issue("error", "accepted_segment_output_missing", f"{segment_id} 已 accepted，但 output_file 不存在。", path))
                if prompt_path is None or not prompt_path.is_file():
                    issues.append(issue("error", "accepted_segment_prompt_missing", f"{segment_id} 已 accepted，但 compiled_prompt_file 不存在。", path))


def accepted_video_segments(root: Path, episode_id: str, issues: list[dict[str, Any]]) -> set[str]:
    path = root / f"episodes/{episode_id}/04_视频片段/video_manifest_{episode_id}.json"
    data = load_json(path, issues, required=False)
    segments = data.get("segments") if isinstance(data, dict) else None
    if not isinstance(segments, list):
        return set()
    return {
        item.get("segment_id")
        for item in segments
        if isinstance(item, dict) and isinstance(item.get("segment_id"), str) and item.get("status") == "accepted"
    }


def accepted_video_segment_order(
    root: Path,
    episode_id: str,
    issues: list[dict[str, Any]],
    allow_candidate: bool = False,
) -> list[str]:
    path = root / f"episodes/{episode_id}/04_视频片段/video_manifest_{episode_id}.json"
    data = load_json(path, issues, required=False)
    segments = data.get("segments") if isinstance(data, dict) else None
    if not isinstance(segments, list):
        return []
    return [
        item["segment_id"]
        for item in segments
        if isinstance(item, dict)
        and isinstance(item.get("segment_id"), str)
        and item.get("status") in ({"candidate", "accepted"} if allow_candidate else {"accepted"})
    ]


def delivery_segment_refs(data: dict[str, Any]) -> set[str]:
    refs: set[str] = set()
    direct_fields = ("source_segments", "segment_ids", "used_segments", "video_segments", "accepted_segments")
    for field in direct_fields:
        value = data.get(field)
        if isinstance(value, list):
            refs.update(item for item in value if isinstance(item, str))
            for item in value:
                if isinstance(item, dict) and isinstance(item.get("segment_id"), str):
                    refs.add(item["segment_id"])
    for field in ("segments", "segment_outputs", "outputs"):
        value = data.get(field)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict) and isinstance(item.get("segment_id"), str):
                    refs.add(item["segment_id"])
    return refs


def output_values(data: dict[str, Any]) -> list[str] | None:
    outputs = data.get("outputs")
    if not isinstance(outputs, list):
        return None
    values: list[str] = []
    for item in outputs:
        if isinstance(item, str):
            values.append(item)
        elif isinstance(item, dict) and isinstance(item.get("file"), str):
            values.append(item["file"])
        else:
            return None
    return values


def report_is_blocked(root: Path, entry: Any) -> bool:
    if isinstance(entry, dict):
        return entry.get("status") == "blocked" or entry.get("result") == "blocked"
    target = relative_file(root, entry)
    if target is None or not target.is_file() or target.suffix.lower() != ".json":
        return False
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False
    return isinstance(data, dict) and (data.get("status") == "blocked" or data.get("result") == "blocked")


def check_report_entries(root: Path, entries: Any, expected_count: int, path: Path, issues: list[dict[str, Any]]) -> None:
    if not isinstance(entries, list):
        issues.append(issue("error", "basic_qc_reports_invalid", "basic_qc_reports 必须是数组。", path))
        return
    if len(entries) != expected_count:
        issues.append(issue("error", "basic_qc_reports_count_invalid", f"basic_qc_reports 数量应为 {expected_count}。", path))
    for entry in entries:
        if isinstance(entry, str):
            if not file_exists(root, entry):
                issues.append(issue("error", "basic_qc_report_missing", f"基础质检报告不存在：{entry}", path))
        elif isinstance(entry, dict):
            report_file = entry.get("file")
            if report_file and not file_exists(root, report_file):
                issues.append(issue("error", "basic_qc_report_missing", f"基础质检报告不存在：{report_file}", path))
        else:
            issues.append(issue("error", "basic_qc_report_invalid", "basic_qc_reports 每项必须是路径或对象。", path))
        if report_is_blocked(root, entry):
            issues.append(issue("error", "basic_qc_report_blocked", "基础媒体可用性检查结果为 blocked，不得交付。", path))


def check_continuity_for_delivery(root: Path, episode_id: str, accepted_order: list[str], issues: list[dict[str, Any]]) -> None:
    path = root / f"episodes/{episode_id}/04_视频片段/continuity_{episode_id}.json"
    data = load_json(path, issues, required=bool(accepted_order))
    if not isinstance(data, dict):
        return
    if data.get("episode_id") != episode_id:
        issues.append(issue("error", "episode_id_mismatch", "continuity episode_id 与目录不一致。", path))
    frames = data.get("frames")
    if not isinstance(frames, list):
        issues.append(issue("error", "continuity_frames_invalid", "continuity.frames 必须是数组。", path))
        frames = []
    roles_by_segment: dict[str, set[str]] = {}
    for frame in frames:
        if not isinstance(frame, dict):
            continue
        segment_id = frame.get("segment_id")
        role = frame.get("role")
        if isinstance(segment_id, str) and isinstance(role, str):
            roles_by_segment.setdefault(segment_id, set()).add(role)
        file_value = frame.get("file")
        if file_value and not file_exists(root, file_value):
            issues.append(issue("error", "continuity_frame_file_missing", f"连续性抽帧文件不存在：{file_value}", path))
        if isinstance(file_value, str) and Path(file_value).suffix.lower() not in IMAGE_INPUT_SUFFIXES:
            issues.append(issue("error", "continuity_frame_suffix_invalid", f"连续性抽帧必须是图片文件：{file_value}", path))
    for segment_id in accepted_order:
        roles = roles_by_segment.get(segment_id, set())
        missing = sorted({"start", "scene", "tail"} - roles)
        if missing:
            issues.append(issue("warning", "continuity_frame_roles_missing", f"{segment_id} accepted 后建议 continuity.frames 覆盖 start|scene|tail，当前缺少：{missing}；该缺口只作内部连续性备注，不阻断已生成视频交付。", path))
    seams = data.get("seams")
    if not isinstance(seams, list):
        issues.append(issue("error", "continuity_seams_invalid", "continuity.seams 必须是数组。", path))
        seams = []
    seams_by_pair = {
        (item.get("from_segment"), item.get("to_segment")): item
        for item in seams
        if isinstance(item, dict)
    }
    for left, right in zip(accepted_order, accepted_order[1:]):
        seam = seams_by_pair.get((left, right))
        if not isinstance(seam, dict):
            issues.append(issue("warning", "continuity_seam_missing", f"缺少 {left} -> {right} 的 seam 记录；该缺口只作内部连续性备注，不阻断已生成视频交付。", path))
            continue
        if seam.get("status") != "verified":
            issues.append(issue("warning", "continuity_seam_not_verified", f"{left} -> {right} seam 建议为 verified；未验证只作内部连续性备注，不触发自动重生。", path))
        if not isinstance(seam.get("selected_cut"), dict) or not seam.get("selected_cut"):
            issues.append(issue("warning", "continuity_seam_cut_missing", f"{left} -> {right} seam 建议登记 selected_cut；缺口只作内部连续性备注。", path))
        for field in ("outgoing_window_frames", "incoming_window_frames"):
            value = seam.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or value < 12:
                issues.append(issue("warning", "continuity_seam_window_invalid", f"{left} -> {right} {field} 建议不少于 12；不足时记录 best available，不阻断已生成视频交付。", path))


def check_delivery(
    root: Path,
    expected_durations: dict[str, int],
    issues: list[dict[str, Any]],
    episode_filter: str | None = None,
    lightweight: bool = False,
) -> None:
    for episode_id, episode_root in episode_dirs(root, episode_filter):
        path = episode_root / f"05_成片/delivery_manifest_{episode_id}.json"
        data = load_json(path, issues, required=False)
        if not isinstance(data, dict):
            continue
        if data.get("episode_id") != episode_id:
            issues.append(issue("error", "episode_id_mismatch", "delivery_manifest episode_id 与目录不一致。", path))
        assembly_confirmation = data.get("assembly_confirmation")
        if lightweight:
            if assembly_confirmation not in (None, {}):
                issues.append(issue("error", "lightweight_assembly_confirmation_invalid", "轻量模式单条视频不得创建拼接确认。", path))
            assembly_confirmation = {}
        elif not isinstance(assembly_confirmation, dict):
            issues.append(issue("error", "assembly_confirmation_missing", "delivery_manifest 必须登记进入成片拼接的 interaction.ask 确认。", path))
            assembly_confirmation = {}
        if not lightweight and assembly_confirmation.get("confirmation_purpose") != "final_assembly":
            issues.append(issue("error", "assembly_confirmation_purpose_invalid", "assembly_confirmation.confirmation_purpose 必须为 final_assembly。", path))
        if not lightweight and not str(assembly_confirmation.get("interaction_ask_call_id") or "").strip():
            issues.append(issue("error", "assembly_confirmation_call_id_missing", "assembly_confirmation 必须记录 interaction_ask_call_id。", path))
        if not lightweight and assembly_confirmation.get("interaction_ask_result") != "proceed_assembly":
            issues.append(issue("error", "assembly_confirmation_result_invalid", "assembly_confirmation.interaction_ask_result 必须为 proceed_assembly。", path))
        if not lightweight and not str(assembly_confirmation.get("user_message") or "").strip():
            issues.append(issue("error", "assembly_confirmation_user_message_missing", "assembly_confirmation.user_message 不能为空。", path))
        if not lightweight and parse_iso_time(assembly_confirmation.get("confirmed_at")) is None:
            issues.append(issue("error", "assembly_confirmation_time_invalid", "assembly_confirmation.confirmed_at 必须是带时区 ISO-8601 时间。", path))
        confirmation_records = load_confirmation_records(root, issues, required=True)
        matching_video_confirmations = [
            record
            for record in confirmation_records
            if record.get("stage") == "video"
            and record.get("episode_id") == episode_id
            and record.get("confirmation_purpose") == "video_acceptance_and_final_assembly"
            and record.get("interaction_ask_call_id") == assembly_confirmation.get("interaction_ask_call_id")
            and record.get("interaction_ask_result") == "proceed_assembly"
        ]
        if not lightweight and not matching_video_confirmations:
            issues.append(issue("error", "assembly_confirmation_video_record_missing", "assembly_confirmation 必须与同集 stage=video 用户确认记录使用同一 interaction.ask 调用 ID 和 proceed_assembly 结果。", path))
        subtitle_enabled = data.get("subtitle_enabled")
        if not isinstance(subtitle_enabled, bool):
            issues.append(issue("error", "subtitle_enabled_invalid", "subtitle_enabled 必须是布尔值；默认 false，用户明确要求字幕时为 true。", path))
        if data.get("status") not in {"deliverable", "candidate"}:
            issues.append(issue("error", "delivery_status_not_deliverable", "delivery_manifest.status 必须为 deliverable 或 candidate；blocked 不得交付。", path))
        duration = data.get("duration_s")
        if isinstance(duration, (int, float)) and not isinstance(duration, bool):
            check_duration_pair(duration, data.get("duration_display"), path, "delivery", issues)
            if episode_id in expected_durations and int(round(float(duration))) != expected_durations[episode_id]:
                issues.append(issue("error", "delivery_duration_mismatch", "delivery_manifest.duration_s 必须等于计划中的本集时长。", path))
        else:
            issues.append(issue("error", "delivery_duration_invalid", "delivery_manifest.duration_s 必须是数字。", path))
        if not file_inside(root, data.get("clean_master"), episode_root):
            issues.append(issue("error", "clean_master_missing", "clean_master 必须指向当前分集目录下真实媒体文件。", path))
        if subtitle_enabled is True and not file_inside(root, data.get("subtitle_master"), episode_root):
            issues.append(issue("error", "subtitle_master_missing", "字幕开启时 subtitle_master 必须指向当前分集目录下真实媒体文件。", path))
        if subtitle_enabled is False:
            for field in ("subtitle_master", "asr_source", "subtitle_final", "subtitle_source", "subtitle_burn_params", "asr_alignment_report"):
                if str(data.get(field) or "").strip():
                    issues.append(issue("error", "subtitle_disabled_field_not_empty", f"字幕关闭时 {field} 必须留空。", path))
        outputs = output_values(data)
        if outputs is None:
            issues.append(issue("error", "outputs_invalid", "outputs 必须是路径数组，或每项包含 file。", path))
        elif subtitle_enabled is False and outputs != [data.get("clean_master")]:
            issues.append(issue("error", "outputs_mismatch", "outputs 必须与用户可见正式交付文件精确一致：字幕关闭时只交付 [clean_master]。", path))
        elif subtitle_enabled is True and outputs != [data.get("subtitle_master")]:
            issues.append(issue("error", "outputs_mismatch", "outputs 必须与用户可见正式交付文件精确一致：字幕开启时只交付 [subtitle_master]。", path))
        reports = data.get("basic_qc_reports")
        if reports not in (None, []):
            if isinstance(reports, list):
                check_report_entries(root, reports, len(reports), path, issues)
            else:
                issues.append(issue("error", "basic_qc_reports_invalid", "basic_qc_reports 必须是数组。", path))
        if subtitle_enabled is True:
            asr_alignment_report = data.get("asr_alignment_report")
            if str(asr_alignment_report or "").strip() and (not file_inside(root, asr_alignment_report, episode_root) or report_is_blocked(root, asr_alignment_report)):
                issues.append(issue("error", "asr_alignment_report_invalid", "asr_alignment_report 如存在，必须指向当前分集目录下未 blocked 的内部追溯文件。", path))
            subtitle_source = data.get("subtitle_source")
            if not file_inside(root, subtitle_source, episode_root):
                issues.append(issue("error", "subtitle_source_missing", "字幕开启时必须存在当前分集目录下的 subtitle_source。", path))
            elif isinstance(subtitle_source, str) and not re.search(r"字幕_时间轴_v\d+_ep_[1-9]\d*\.srt$", subtitle_source):
                issues.append(issue("error", "subtitle_source_name_invalid", "subtitle_source 应指向 字幕_时间轴_vNN_ep_N.srt。", path))
            subtitle_final = data.get("subtitle_final")
            if not file_inside(root, subtitle_final, episode_root):
                issues.append(issue("error", "subtitle_final_missing", "字幕开启时必须存在当前分集目录下的 subtitle_final。", path))
            elif isinstance(subtitle_final, str) and not re.search(r"字幕_最终版_v\d+_ep_[1-9]\d*\.json$", subtitle_final):
                issues.append(issue("error", "subtitle_final_name_invalid", "subtitle_final 应指向 字幕_最终版_vNN_ep_N.json。", path))
        accepted_order = accepted_video_segment_order(root, episode_id, issues, allow_candidate=lightweight)
        accepted = set(accepted_order)
        if not lightweight and assembly_confirmation.get("segment_ids") != accepted_order:
            issues.append(issue("error", "assembly_confirmation_segments_mismatch", "assembly_confirmation.segment_ids 必须按顺序精确等于当前成片采用的 accepted SEG。", path))
        for segment_id in sorted(delivery_segment_refs(data)):
            if segment_id not in accepted:
                issues.append(issue("error", "delivery_non_accepted_segment", f"delivery 使用了不符合当前模式状态要求的视频片段：{segment_id}", path))
        if not lightweight:
            check_continuity_for_delivery(root, episode_id, accepted_order, issues)


def dedupe_issues(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    result: list[dict[str, Any]] = []
    for item in issues:
        key = (item.get("level"), item.get("code"), item.get("message"), item.get("path"))
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def check_skill_package(root: Path, issues: list[dict[str, Any]]) -> None:
    skill_path = root / "SKILL.md"
    try:
        text = skill_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        issues.append(issue("error", "skill_file_missing", "Skill 根目录缺少 SKILL.md。", skill_path))
        return
    except (OSError, UnicodeError) as exc:
        issues.append(issue("error", "skill_file_unreadable", f"SKILL.md 无法读取：{exc}", skill_path))
        return

    frontmatter = re.match(r"\A---\n(.*?)\n---\n", text, flags=re.DOTALL)
    if frontmatter is None:
        issues.append(issue("error", "skill_frontmatter_missing", "SKILL.md 缺少合法的 YAML frontmatter。", skill_path))
        return
    fields: dict[str, str] = {}
    for line in frontmatter.group(1).splitlines():
        match = re.fullmatch(r"([a-z_]+):\s*(.*)", line)
        if match:
            fields[match.group(1)] = match.group(2).strip()
    name = fields.get("name", "")
    description = fields.get("description", "")
    if not 2 <= len(name) <= 64 or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        issues.append(issue("error", "skill_name_invalid", "Skill name 必须是 2-64 位小写字母、数字或单连字符。", skill_path))
    if name != root.name:
        issues.append(issue("error", "skill_name_path_mismatch", "Skill name 必须与目录名一致。", skill_path))
    if not description or description[:1] in {'"', "'"} or description[-1:] in {'"', "'"}:
        issues.append(issue("error", "skill_description_invalid", "Skill description 必须是非空、未加引号的单行标量。", skill_path))
    if ": " in description or "<" in description or ">" in description or "TODO" in description:
        issues.append(issue("error", "skill_description_forbidden_text", "Skill description 含禁止的格式或占位内容。", skill_path))
    if not text[frontmatter.end():].strip():
        issues.append(issue("error", "skill_body_empty", "SKILL.md 正文不能为空。", skill_path))

    referenced_paths = set(re.findall(r"`((?:references|scripts)/[^`\s]+?\.(?:md|py))`", text))
    for relative in sorted(referenced_paths):
        target = root / relative
        if not target.is_file():
            issues.append(issue("error", "skill_reference_missing", f"SKILL.md 引用的本地文件不存在：{relative}", skill_path))

    markdown_paths = [
        path
        for path in sorted(root.glob("references/**/*.md"))
        if "references/cli" not in path.as_posix()
    ] + [skill_path]
    for markdown_path in markdown_paths:
        try:
            markdown_text = markdown_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            issues.append(issue("error", "markdown_file_unreadable", f"Markdown 文件无法读取：{exc}", markdown_path))
            continue
        for match in re.finditer(r"(?<!!)\[[^\]\n]+\]\(([^)\n]+)\)", markdown_text):
            raw_target = match.group(1).strip()
            if not raw_target or raw_target.startswith(("#", "http://", "https://", "mailto:", "app://", "codex://")):
                continue
            if " " in raw_target and not (raw_target.startswith("<") and raw_target.endswith(">")):
                raw_target = raw_target.split()[0]
            raw_target = raw_target.strip("<>")
            path_part = raw_target.split("#", 1)[0].split("?", 1)[0]
            if not path_part:
                continue
            target = markdown_path.parent / unquote(path_part)
            if not target.exists():
                issues.append(issue("error", "markdown_link_missing", f"Markdown 相对链接不存在：{raw_target}", markdown_path))


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Focused doubao-creative-drama workflow validator.")
    parser.add_argument("skill_root", nargs="?", default=".")
    parser.add_argument("--project-root")
    parser.add_argument("--stage", choices=("skill", *STAGES, "all"), default="skill")
    parser.add_argument("--fix", action="store_true", help="kept for compatibility; no automatic fixes are applied")
    parser.add_argument("--changed-file", action="append", default=[], help="kept for compatibility; runs the same focused checks")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    project_root = Path(args.project_root).resolve() if args.project_root else Path(args.skill_root).resolve()
    issues: list[dict[str, Any]] = []

    if args.stage == "skill":
        check_skill_package(project_root, issues)
        issues = dedupe_issues(issues)
        error_count = sum(1 for item in issues if item["level"] == "error")
        payload = {
            "summary": {
                "error_count": error_count,
                "warning_count": sum(1 for item in issues if item["level"] == "warning"),
                "scope": args.stage,
            },
            "release_ready": error_count == 0,
            "issues": issues,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1 if error_count else 0

    plan = load_json(project_root / "00_制作控制/drama_plan.json", issues, required=False)
    expected_durations = check_plan_durations(project_root, plan, issues)
    lightweight = is_lightweight_plan(plan) and lightweight_constraints_valid(plan)
    check_episode_directories(project_root, expected_durations, issues)
    check_episode_entry_manifests(project_root, issues, lightweight)
    check_state(project_root, plan, issues)
    check_operation_log_tools(project_root, issues)

    state = load_json(project_root / "00_制作控制/制作状态.json", issues, required=False)
    active_episode = state.get("current_episode") if isinstance(state, dict) else None
    stages_to_check = STAGES if args.stage == "all" else (args.stage,)
    for stage in stages_to_check:
        episode_filter = active_episode if args.stage != "all" and stage in EPISODE_STAGES else None
        check_stage_artifacts(project_root, stage, issues, episode_filter, lightweight)
        if stage in EPISODE_STAGES:
            check_episode_manifest_ids(project_root, stage, issues, episode_filter)
    episode_filter = active_episode if args.stage != "all" and args.stage in EPISODE_STAGES else None
    asset_index = blank_asset_index()
    if args.stage in {"assets", "storyboard", "keyframes", "video", "final", "all"}:
        asset_index = check_assets(project_root, issues, episode_filter)
    if args.stage in {"storyboard", "keyframes", "video", "final", "all"}:
        check_storyboards(project_root, expected_durations, plan, issues, episode_filter)
    if args.stage in {"keyframes", "video", "final", "all"}:
        check_keyframes(project_root, asset_index, issues, episode_filter)
    if args.stage in {"video", "final", "all"}:
        check_video(
            project_root,
            asset_index,
            plan,
            issues,
            episode_filter,
            require_accepted=args.stage in {"final", "all"} and not lightweight,
        )
    if args.stage in {"final", "all"}:
        check_delivery(project_root, expected_durations, issues, episode_filter, lightweight)

    issues = dedupe_issues(issues)
    error_count = sum(1 for item in issues if item["level"] == "error")
    payload = {
        "summary": {
            "error_count": error_count,
            "warning_count": sum(1 for item in issues if item["level"] == "warning"),
            "scope": args.stage,
        },
        "release_ready": error_count == 0,
        "issues": issues,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 1 if error_count else 0


if __name__ == "__main__":
    sys.exit(main())
