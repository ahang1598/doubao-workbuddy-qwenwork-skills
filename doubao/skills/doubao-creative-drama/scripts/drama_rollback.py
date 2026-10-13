#!/usr/bin/env python3
"""Move project state back to one stage without touching artifacts."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4

STAGES = ("planning", "script", "assets", "storyboard", "keyframes", "video", "final")


def safe_write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def rollback_state(
    state: dict,
    to_stage: str,
    episode_id: str | None = None,
    cascade_later_episodes: bool = False,
) -> dict:
    if to_stage not in STAGES:
        raise ValueError(f"unknown stage: {to_stage}")
    if episode_id is None and to_stage in STAGES[2:]:
        raise ValueError("assets through final rollback requires --episode ep_N")
    if episode_id is not None and to_stage not in STAGES[1:]:
        raise ValueError("episode-scoped rollback only supports script through final")
    phases = state.get("phases")
    if not isinstance(phases, dict):
        raise ValueError("制作状态.json.phases must be an object")
    episode_states = state.get("episodes")
    if episode_id is not None and (not isinstance(episode_states, dict) or episode_id not in episode_states):
        raise ValueError(f"unknown episode: {episode_id}")
    if episode_id is not None and isinstance(episode_states, dict):
        target_number = int(episode_id.split("_", 1)[1])
        current_episode = str(state.get("current_episode") or "")
        if re.fullmatch(r"ep_[1-9]\d*", current_episode):
            current_number = int(current_episode.split("_", 1)[1])
            if target_number > current_number:
                raise ValueError(f"cannot rollback future episode before it becomes current: {episode_id}")
        target_statuses = episode_states[episode_id].get("stage_status") if isinstance(episode_states[episode_id], dict) else None
        if isinstance(target_statuses, dict) and target_statuses.get(to_stage) in {None, "pending", "invalidated"}:
            raise ValueError(f"cannot rollback unstarted stage: {episode_id}.{to_stage}")
        started_later = []
        for item_episode_id, episode_state in episode_states.items():
            item_number = int(item_episode_id.split("_", 1)[1])
            statuses = episode_state.get("stage_status") if isinstance(episode_state, dict) else None
            if item_number > target_number and isinstance(statuses, dict):
                if any(statuses.get(stage) not in {None, "pending", "invalidated"} for stage in STAGES[1:]):
                    started_later.append(item_episode_id)
        if started_later and not cascade_later_episodes:
            raise ValueError(
                "later episodes already progressed; rerun with --cascade-later-episodes "
                f"to invalidate them explicitly: {started_later}"
            )

    updated = dict(state)
    updated["revision"] = int(state.get("revision", 0) or 0) + 1
    updated["current_stage"] = to_stage
    updated["current_episode"] = episode_id if episode_id is not None else None
    updated["phases"] = dict(phases)
    target_index = STAGES.index(to_stage)
    target_status = "awaiting_confirmation" if to_stage == "planning" else "in_progress"
    if episode_id is None:
        for index, stage in enumerate(STAGES):
            if index >= target_index:
                updated["phases"][stage] = target_status if stage == to_stage else "invalidated"
    else:
        for stage in STAGES[2:]:
            stage_index = STAGES.index(stage)
            if stage_index >= max(target_index, STAGES.index("assets")):
                updated["phases"][stage] = target_status if stage == to_stage else "invalidated"

    if isinstance(episode_states, dict):
        episodes = {}
        for item_episode_id, episode_state in episode_states.items():
            if not isinstance(episode_state, dict) or not isinstance(episode_state.get("stage_status"), dict):
                episodes[item_episode_id] = episode_state
                continue
            next_state = dict(episode_state)
            statuses = dict(episode_state["stage_status"])
            if updated["current_episode"] is not None and item_episode_id != updated["current_episode"]:
                target_number = int(updated["current_episode"].split("_", 1)[1])
                item_number = int(item_episode_id.split("_", 1)[1])
                if cascade_later_episodes and item_number > target_number:
                    for stage in STAGES[1:]:
                        if stage in statuses and statuses[stage] not in {"pending", "invalidated"}:
                            statuses[stage] = "invalidated"
                next_state["stage_status"] = statuses
                episodes[item_episode_id] = next_state
                continue
            for stage in STAGES[target_index:]:
                if stage != "planning" and stage in statuses:
                    statuses[stage] = "in_progress" if stage == to_stage else "invalidated"
            next_state["stage_status"] = statuses
            episodes[item_episode_id] = next_state
        updated["episodes"] = episodes
    return updated


def append_log(
    project_root: Path,
    to_stage: str,
    episode_id: str | None,
    cascade_later_episodes: bool,
    reason: str,
    state_path: Path,
    input_revision: int,
) -> None:
    log_path = project_root / "00_制作控制/操作日志.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    operation_id = f"rollback_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}"
    record = {
        "operation_id": operation_id,
        "input_revision": input_revision,
        "stage": to_stage,
        "target_ids": [item for item in (episode_id, to_stage) if item],
        "tool": "drama_rollback.py",
        "tool_call_id": "",
        "params_summary": {
            "to_stage": to_stage,
            "episode_id": episode_id,
            "cascade_later_episodes": cascade_later_episodes,
            "reason": reason,
        },
        "attempt": 1,
        "status": "succeeded",
        "outputs": [str(state_path.relative_to(project_root))],
        "output_metadata": {"state_path": str(state_path.relative_to(project_root))},
        "tool_calls": [],
        "recovery_action": "downstream stages invalidated; regenerate affected artifacts before confirmation",
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rollback doubao-creative-drama stage state.")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--to-stage", required=True, choices=STAGES)
    parser.add_argument("--episode", help="limit rollback to one ep_N; valid for assets through final")
    parser.add_argument("--cascade-later-episodes", action="store_true", help="explicitly invalidate already-started later episodes")
    parser.add_argument("--reason", default="")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    project_root = Path(args.project_root).resolve()
    state_path = project_root / "00_制作控制/制作状态.json"
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        updated = rollback_state(state, args.to_stage, args.episode, args.cascade_later_episodes)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"error": "rollback_failed", "message": str(exc)}, ensure_ascii=False))
        return 2

    changed = state != updated
    if changed and not args.dry_run:
        try:
            safe_write_json(state_path, updated)
            append_log(
                project_root,
                args.to_stage,
                args.episode,
                args.cascade_later_episodes,
                args.reason,
                state_path,
                int(state.get("revision", 0) or 0),
            )
        except (OSError, UnicodeError) as exc:
            try:
                safe_write_json(state_path, state)
            except (OSError, UnicodeError) as restore_exc:
                print(
                    json.dumps(
                        {
                            "error": "rollback_partial_commit",
                            "message": str(exc),
                            "restore_error": str(restore_exc),
                        },
                        ensure_ascii=False,
                    )
                )
                return 3
            print(json.dumps({"error": "rollback_log_failed", "message": str(exc), "state_restored": True}, ensure_ascii=False))
            return 2

    print(
        json.dumps(
            {
                "status": "dry_run" if args.dry_run else "updated",
                "changed": changed,
                "to_stage": args.to_stage,
                "episode_id": args.episode,
                "cascade_later_episodes": args.cascade_later_episodes,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
