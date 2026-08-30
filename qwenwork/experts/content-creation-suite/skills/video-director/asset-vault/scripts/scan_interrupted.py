#!/usr/bin/env python3
"""
扫描待补做项目脚本

功能：扫描 projects/ 下所有 metadata.json，输出待补做汇总的项目列表。
当前包含两类项目：
- status = "interrupted" 的中断项目
- status = "in_progress" 且 updated_at 超过 24 小时的超时项目

使用方式：
  python scripts/scan_interrupted.py [--vault-path <path>]

输出格式：JSON 列表，每项包含项目路径、待补做原因、已有产物信息。
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


STALE_IN_PROGRESS_THRESHOLD = timedelta(hours=24)


def find_vault_path():
    if len(sys.argv) > 2 and sys.argv[1] == "--vault-path":
        return Path(sys.argv[2])
    return Path(__file__).parent.parent


def parse_metadata_datetime(value: str | None) -> datetime | None:
    """解析 metadata 中的时间字段，支持 ISO8601 与结尾 Z 的 UTC 写法。"""
    if not value:
        return None

    try:
        normalized_value = value.replace("Z", "+00:00")
        parsed_datetime = datetime.fromisoformat(normalized_value)
    except ValueError:
        return None

    if parsed_datetime.tzinfo is None:
        return parsed_datetime.replace(tzinfo=timezone.utc)
    return parsed_datetime.astimezone(timezone.utc)


def is_stale_in_progress(metadata: dict, now: datetime) -> bool:
    """判断 in_progress 项目是否超过 24 小时未更新。"""
    if metadata.get("status") != "in_progress":
        return False

    updated_at = parse_metadata_datetime(metadata.get("updated_at"))
    if updated_at is None:
        return False

    return now - updated_at > STALE_IN_PROGRESS_THRESHOLD


def build_project_record(project_dir: Path, vault_path: Path, metadata: dict, reason_type: str) -> dict:
    """构造待补做项目的输出记录。"""
    existing_files = [
        file_path.name for file_path in project_dir.iterdir()
        if file_path.is_file() and file_path.suffix == ".md"
    ]
    interruption_info = metadata.get("interruption", {})

    return {
        "path": str(project_dir.relative_to(vault_path)),
        "dir_name": project_dir.name,
        "client": metadata.get("client", ""),
        "project": metadata.get("project", ""),
        "industry": metadata.get("industry", ""),
        "date": metadata.get("date", ""),
        "status": metadata.get("status", ""),
        "reason_type": reason_type,
        "interrupted_at": interruption_info.get("interrupted_at"),
        "reason": interruption_info.get("reason"),
        "updated_at": metadata.get("updated_at"),
        "existing_files": existing_files,
        "has_step_01": any(file_name.startswith("step_01_") for file_name in existing_files),
        "has_final_script": "final_script.md" in existing_files,
        "step_count": sum(1 for file_name in existing_files if file_name.startswith("step_")),
    }


def scan_interrupted(vault_path: Path) -> list:
    """扫描中断项目和超过 24 小时未更新的进行中项目。"""
    projects_dir = vault_path / "projects"
    if not projects_dir.exists():
        return []

    now = datetime.now(timezone.utc)
    pending_projects = []

    for project_dir in sorted(projects_dir.iterdir()):
        if not project_dir.is_dir():
            continue
        metadata_path = project_dir / "metadata.json"
        if not metadata_path.exists():
            continue

        try:
            with open(metadata_path, "r", encoding="utf-8") as metadata_file:
                metadata = json.load(metadata_file)
        except (json.JSONDecodeError, IOError):
            continue

        if metadata.get("status") == "interrupted":
            pending_projects.append(
                build_project_record(project_dir, vault_path, metadata, "interrupted")
            )
            continue

        if is_stale_in_progress(metadata, now):
            pending_projects.append(
                build_project_record(project_dir, vault_path, metadata, "stale_in_progress")
            )

    return pending_projects


def main():
    vault_path = find_vault_path()
    pending_projects = scan_interrupted(vault_path)

    if not pending_projects:
        print("✅ 无中断或超时项目")
        return

    print(f"发现 {len(pending_projects)} 个待补做项目：\n")

    for project in pending_projects:
        print(f"📁 {project['dir_name']}")
        print(f"   路径：{project['path']}")
        print(f"   状态：{project['status']} | 原因：{project['reason_type']}")
        if project["client"]:
            print(f"   客户：{project['client']}")
        if project["updated_at"]:
            print(f"   最近更新：{project['updated_at']}")
        if project["interrupted_at"]:
            print(f"   中断位置：{project['interrupted_at']}")
        if project["reason"]:
            print(f"   中断原因：{project['reason']}")
        print(f"   已有文件：{len(project['existing_files'])} 个（{project['step_count']} 个步骤文件）")
        print(f"   有首步产物：{'✅' if project['has_step_01'] else '❌'} | 有最终脚本：{'✅' if project['has_final_script'] else '❌'}")
        print()

    output_path = vault_path / "_index" / "interrupted_projects.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as output_file:
        json.dump(pending_projects, output_file, ensure_ascii=False, indent=2)
    print(f"详细信息已保存到：{output_path}")


if __name__ == "__main__":
    main()
