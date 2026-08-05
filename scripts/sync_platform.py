#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path, PurePosixPath

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None


DEFAULT_TIMEZONE = "Asia/Shanghai"


@dataclass(frozen=True)
class SourceSpec:
    name: str
    title: str
    source: Path
    target: str
    item_kind: str
    source_is_file: bool = False


@dataclass(frozen=True)
class PlatformSpec:
    name: str
    title: str
    root: str
    readme: str
    task_name: str
    sources: tuple[SourceSpec, ...]


@dataclass(frozen=True)
class ChangeSet:
    added: tuple[str, ...]
    modified: tuple[str, ...]
    deleted: tuple[str, ...]
    new_items: tuple[str, ...]
    removed_items: tuple[str, ...]

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.modified or self.deleted)


PLATFORMS: dict[str, PlatformSpec] = {
    "doubao": PlatformSpec(
        name="doubao",
        title="Doubao",
        root="doubao",
        readme="README-doubao.md",
        task_name="DoubaoSkillsDailySync",
        sources=(
            SourceSpec(
                name="skills",
                title="Skills",
                source=Path(
                    "/mnt/c/Users/15805/AppData/Local/Doubao/User Data/Default/"
                    ".doubao/agent_mode/workspace/.skills"
                ),
                target="skills",
                item_kind="skill",
            ),
        ),
    ),
    "workbuddy": PlatformSpec(
        name="workbuddy",
        title="WorkBuddy",
        root="workbuddy",
        readme="README-workbuddy.md",
        task_name="WorkbuddySkillsDailySync",
        sources=(
            SourceSpec(
                name="experts",
                title="Marketplace Experts",
                source=Path("/mnt/c/Users/15805/.workbuddy/plugins/marketplaces/experts/plugins"),
                target="experts",
                item_kind="expert",
            ),
            SourceSpec(
                name="official_external",
                title="Official Experts / External Plugins",
                source=Path(
                    "/mnt/c/Users/15805/.workbuddy/plugins/marketplaces/"
                    "codebuddy-plugins-official/external_plugins"
                ),
                target="official_experts/external_plugins",
                item_kind="official expert",
            ),
            SourceSpec(
                name="official_plugins",
                title="Official Experts / Plugins",
                source=Path(
                    "/mnt/c/Users/15805/.workbuddy/plugins/marketplaces/"
                    "codebuddy-plugins-official/plugins"
                ),
                target="official_experts/plugins",
                item_kind="official expert",
            ),
            SourceSpec(
                name="cb_teams_experts",
                title="CB Teams Experts",
                source=Path(
                    "/mnt/c/Users/15805/.workbuddy/plugins/marketplaces/"
                    "cb_teams_marketplace/plugins"
                ),
                target="cb_teams_experts/plugins",
                item_kind="team expert",
            ),
            SourceSpec(
                name="cb_teams_analysis",
                title="CB Teams Analysis Reference",
                source=Path(
                    "/mnt/c/Users/15805/.workbuddy/plugins/marketplaces/"
                    "cb_teams_marketplace/plugins_analysis_company_analysis.md"
                ),
                target="cb_teams_experts/plugins_analysis_company_analysis.md",
                item_kind="reference",
                source_is_file=True,
            ),
            SourceSpec(
                name="skills",
                title="Skills",
                source=Path("/mnt/c/Users/15805/.workbuddy/skills"),
                target="skills",
                item_kind="skill",
            ),
        ),
    ),
    "qwenwork": PlatformSpec(
        name="qwenwork",
        title="QwenWork",
        root="qwenwork",
        readme="README-qwenwork.md",
        task_name="QwenworkSkillsDailySync",
        sources=(
            SourceSpec(
                name="experts",
                title="Experts",
                source=Path("/mnt/c/Users/15805/.qwenworkcn/plugins"),
                target="experts",
                item_kind="expert",
            ),
            SourceSpec(
                name="skills",
                title="Skills",
                source=Path("/mnt/c/Users/15805/.qwenworkcn/skills"),
                target="skills",
                item_kind="skill",
            ),
        ),
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync one configured AI workspace platform.")
    parser.add_argument("--platform", choices=sorted(PLATFORMS), required=True)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--refresh-docs", action="store_true")
    parser.add_argument("--commit", action="store_true")
    parser.add_argument("--push", action="store_true")
    parser.add_argument("--timezone", default=DEFAULT_TIMEZONE)
    return parser.parse_args()


def now_in_timezone(name: str) -> datetime:
    if ZoneInfo is None:
        return datetime.now().astimezone()
    return datetime.now(ZoneInfo(name))


def acquire_lock(path: Path, blocking: bool):
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("w", encoding="utf-8")
    if fcntl is not None:
        flags = fcntl.LOCK_EX if blocking else fcntl.LOCK_EX | fcntl.LOCK_NB
        try:
            fcntl.flock(handle.fileno(), flags)
        except BlockingIOError:
            raise RuntimeError(f"another sync process is already running: {path}")
    handle.write(f"pid={os.getpid()}\n")
    handle.flush()
    return handle


def rel_join(*parts: str) -> str:
    return PurePosixPath(*parts).as_posix()


def path_from_rel(root: Path, rel: str) -> Path:
    return root.joinpath(*PurePosixPath(rel).parts)


def file_hash(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def list_source_files(source: SourceSpec) -> dict[str, Path]:
    if not source.source.exists():
        raise FileNotFoundError(f"source does not exist: {source.source}")
    if source.source_is_file:
        if not source.source.is_file():
            raise FileNotFoundError(f"source is not a file: {source.source}")
        return {source.target: source.source}
    if not source.source.is_dir():
        raise NotADirectoryError(f"source is not a directory: {source.source}")
    files: dict[str, Path] = {}
    for path in source.source.rglob("*"):
        if path.is_file():
            rel = path.relative_to(source.source).as_posix()
            files[rel_join(source.target, rel)] = path
    return files


def list_target_files(platform_root: Path, source: SourceSpec) -> dict[str, Path]:
    target = path_from_rel(platform_root, source.target)
    if not target.exists():
        return {}
    if source.source_is_file:
        return {source.target: target} if target.is_file() else {}
    files: dict[str, Path] = {}
    for path in target.rglob("*"):
        if path.is_file():
            files[path.relative_to(platform_root).as_posix()] = path
    return files


def item_name(rel: str) -> str:
    parts = PurePosixPath(rel).parts
    if len(parts) <= 1:
        return parts[0] if parts else "(root)"
    if parts[0] == "official_experts" and len(parts) > 2:
        return f"{parts[0]}/{parts[1]}/{parts[2]}"
    if parts[0] == "cb_teams_experts" and len(parts) > 2 and parts[1] == "plugins":
        return f"{parts[0]}/{parts[2]}"
    return f"{parts[0]}/{parts[1]}"


def detect_changes(source_files: dict[str, Path], target_files: dict[str, Path]) -> ChangeSet:
    source_rels = set(source_files)
    target_rels = set(target_files)
    added = tuple(sorted(source_rels - target_rels))
    deleted = tuple(sorted(target_rels - source_rels))
    modified = tuple(
        rel
        for rel in sorted(source_rels & target_rels)
        if file_hash(source_files[rel]) != file_hash(target_files[rel])
    )
    old_items = {item_name(rel) for rel in target_rels}
    new_items = {item_name(rel) for rel in source_rels}
    return ChangeSet(
        added=added,
        modified=modified,
        deleted=deleted,
        new_items=tuple(sorted(new_items - old_items)),
        removed_items=tuple(sorted(old_items - new_items)),
    )


def copy_files(platform_root: Path, files: dict[str, Path], rels: tuple[str, ...]) -> None:
    for rel in rels:
        target = path_from_rel(platform_root, rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(files[rel], target)


def archive_deleted(platform_root: Path, archive_root: Path, deleted: tuple[str, ...]) -> None:
    for rel in deleted:
        source = path_from_rel(platform_root, rel)
        if not source.exists():
            continue
        archived = path_from_rel(archive_root, rel)
        archived.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(archived))
    remove_empty_dirs(platform_root)


def remove_empty_dirs(root: Path) -> None:
    if not root.exists():
        return
    skip_names = {"archive", "change-logs"}
    dirs = [path for path in root.rglob("*") if path.is_dir() and path.name not in skip_names]
    for path in sorted(dirs, key=lambda p: len(p.parts), reverse=True):
        try:
            path.rmdir()
        except OSError:
            pass


def parse_front_matter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    block: list[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        block.append(line)
    data: dict[str, str] = {}
    i = 0
    while i < len(block):
        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", block[i])
        if not match:
            i += 1
            continue
        key, raw = match.groups()
        value = raw.strip()
        if value in {"|", ">"}:
            i += 1
            collected: list[str] = []
            while i < len(block) and not re.match(r"^[A-Za-z0-9_-]+:\s*", block[i]):
                if block[i].strip():
                    collected.append(block[i].strip())
                i += 1
            data[key] = " ".join(collected)
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        data[key] = value
        i += 1
    return data


def one_line(text: str, limit: int = 220) -> str:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def load_json(path: Path) -> dict:
    try:
        return json.loads(read_text(path))
    except Exception:
        return {}


def localized(value) -> str:
    if isinstance(value, dict):
        return str(value.get("zh") or value.get("en") or next(iter(value.values()), ""))
    if isinstance(value, list):
        return ", ".join(localized(item) for item in value[:4])
    return str(value or "")


def read_readme_summary(item_dir: Path) -> str:
    for name in ("README.md", "README_zh.md", "README.en.md", "README_EN.md"):
        path = item_dir / name
        if not path.exists():
            continue
        lines = read_text(path).splitlines()
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or stripped.startswith("---"):
                continue
            stripped = re.sub(r"^\*\*(.*?)\*\*\s*[—-]\s*", r"\1 - ", stripped)
            return stripped
    return ""


def metadata_for_item(item_dir: Path, fallback_name: str) -> tuple[str, str, str]:
    plugin_paths = [
        item_dir / ".codebuddy-plugin" / "plugin.json",
        item_dir / ".qoder-plugin" / "plugin.json",
        item_dir / ".codex-plugin" / "plugin.json",
        item_dir / "plugin.json",
    ]
    for path in plugin_paths:
        if path.exists():
            data = load_json(path)
            name = localized(data.get("displayName")) or data.get("name") or fallback_name
            description = (
                localized(data.get("displayDescription"))
                or data.get("description")
                or data.get("description_en")
                or read_readme_summary(item_dir)
            )
            category = localized(data.get("category")) or data.get("categoryId") or data.get("expertType") or ""
            return str(name), one_line(str(description)), str(category)

    skill_md = item_dir / "SKILL.md"
    if skill_md.exists():
        front = parse_front_matter(read_text(skill_md))
        return (
            front.get("name") or fallback_name,
            one_line(front.get("description") or read_readme_summary(item_dir)),
            "",
        )

    return fallback_name, one_line(read_readme_summary(item_dir) or "No description found."), ""


def parse_cb_teams_analysis(path: Path) -> dict[str, tuple[str, str]]:
    if not path.exists():
        return {}
    current_category = ""
    mapping: dict[str, tuple[str, str]] = {}
    for line in read_text(path).splitlines():
        heading = re.match(r"^###\s+(.+?)（", line.strip())
        if heading:
            current_category = heading.group(1)
        item = re.match(r"^\d+\.\s+\*\*(.+?)\*\*\s*-\s*(.+)$", line.strip())
        if item:
            mapping[item.group(1)] = (current_category, one_line(item.group(2)))
    return mapping


def escape_cell(text: str) -> str:
    return str(text).replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ")


def source_entries(platform_root: Path, source: SourceSpec, cb_analysis: dict[str, tuple[str, str]]):
    target = path_from_rel(platform_root, source.target)
    if source.source_is_file:
        return []
    if not target.exists():
        return []
    entries = []
    for item in sorted((p for p in target.iterdir() if p.is_dir()), key=lambda p: p.name):
        name, description, category = metadata_for_item(item, item.name)
        if source.name == "cb_teams_experts":
            override = cb_analysis.get(item.name)
            if override:
                category = override[0] or category
                description = override[1] or description
        file_count = sum(1 for p in item.rglob("*") if p.is_file())
        entries.append((name, item.name, category or source.item_kind, file_count, description))
    return entries


def read_log_summary(path: Path) -> str:
    lines = read_text(path).splitlines()
    capture = False
    summary: list[str] = []
    for line in lines:
        if line.strip() == "## Summary":
            capture = True
            continue
        if capture and line.startswith("## "):
            break
        if capture and line.startswith("- "):
            summary.append(line[2:].strip())
    return one_line(" ".join(summary), 180) if summary else "No summary found."


def recent_logs(repo_root: Path, change_logs_dir: Path, limit: int = 20):
    if not change_logs_dir.exists():
        return []
    rows = []
    for path in sorted(change_logs_dir.glob("*.md"), reverse=True)[:limit]:
        rows.append((path.stem, path.relative_to(repo_root).as_posix(), read_log_summary(path)))
    return rows


def summarize_changes(platform: PlatformSpec, changes: ChangeSet) -> list[str]:
    lines = [
        f"{platform.title} 本次同步新增 {len(changes.added)} 个文件、修改 {len(changes.modified)} 个文件、删除 {len(changes.deleted)} 个文件。"
    ]
    if changes.new_items:
        visible = ", ".join(changes.new_items[:12])
        if len(changes.new_items) > 12:
            visible += f" 等 {len(changes.new_items)} 项"
        lines.append(f"新增条目：{visible}。")
    if changes.removed_items:
        visible = ", ".join(changes.removed_items[:12])
        if len(changes.removed_items) > 12:
            visible += f" 等 {len(changes.removed_items)} 项"
        lines.append(f"移除条目已归档：{visible}。")
    affected = sorted({item_name(rel) for rel in (*changes.added, *changes.modified, *changes.deleted)})
    if affected:
        visible = ", ".join(affected[:12])
        if len(affected) > 12:
            visible += f" 等 {len(affected)} 项"
        lines.append(f"受影响范围：{visible}。")
    return lines


def render_file_list(paths: tuple[str, ...], prefix: str) -> str:
    if not paths:
        return "- 无\n"
    return "\n".join(f"- `{prefix}/{path}`" for path in paths) + "\n"


def render_deleted_list(paths: tuple[str, ...], root: str, archive_rel: str) -> str:
    if not paths:
        return "- 无\n"
    return "\n".join(f"- `{root}/{path}` -> `{archive_rel}/{path}`" for path in paths) + "\n"


def render_changed_items(changes: ChangeSet) -> str:
    counts: Counter[str] = Counter()
    for rel in (*changes.added, *changes.modified, *changes.deleted):
        counts[item_name(rel)] += 1
    if not counts:
        return "- 无\n"
    rows = ["| Item | Changed Files |", "| --- | ---: |"]
    for name, count in sorted(counts.items()):
        rows.append(f"| `{escape_cell(name)}` | {count} |")
    return "\n".join(rows) + "\n"


def write_change_log(
    platform: PlatformSpec,
    repo_root: Path,
    timestamp: datetime,
    changes: ChangeSet,
    archive_root: Path,
) -> Path:
    change_logs_dir = repo_root / platform.root / "change-logs"
    change_logs_dir.mkdir(parents=True, exist_ok=True)
    slug = timestamp.strftime("%Y-%m-%d-%H%M%S")
    path = change_logs_dir / f"{slug}.md"
    archive_rel = archive_root.relative_to(repo_root).as_posix()
    summary = "\n".join(f"- {line}" for line in summarize_changes(platform, changes))
    content = f"""# {platform.title} Sync - {timestamp.strftime('%Y-%m-%d %H:%M:%S %z')}

## Summary
{summary}

## Changed Items
{render_changed_items(changes)}
## Added Files ({len(changes.added)})
{render_file_list(changes.added, platform.root)}
## Modified Files ({len(changes.modified)})
{render_file_list(changes.modified, platform.root)}
## Deleted And Archived Files ({len(changes.deleted)})
{render_deleted_list(changes.deleted, platform.root, archive_rel)}
"""
    path.write_text(content, encoding="utf-8")
    return path


def render_readme(platform: PlatformSpec, repo_root: Path, latest_log: Path | None) -> str:
    platform_root = repo_root / platform.root
    change_logs_dir = platform_root / "change-logs"
    logs = recent_logs(repo_root, change_logs_dir)
    if latest_log is not None:
        latest_line = (
            f"[{latest_log.stem}]({latest_log.relative_to(repo_root).as_posix()})"
            f" - {read_log_summary(latest_log)}"
        )
    elif logs:
        latest_line = f"[{logs[0][0]}]({logs[0][1]}) - {logs[0][2]}"
    else:
        latest_line = "暂无同步变更记录。"

    cb_analysis = parse_cb_teams_analysis(
        platform_root / "cb_teams_experts" / "plugins_analysis_company_analysis.md"
    )
    sections: list[str] = []
    total_items = 0
    total_files = 0
    for source in platform.sources:
        entries = source_entries(platform_root, source, cb_analysis)
        if not entries:
            if source.source_is_file and path_from_rel(platform_root, source.target).exists():
                continue
            sections.append(f"### {source.title}\n\n暂无可索引目录。\n")
            continue
        total_items += len(entries)
        rows = ["| Name | Directory | Category | Files | Description |", "| --- | --- | --- | ---: | --- |"]
        for name, directory, category, file_count, description in entries:
            total_files += file_count
            target_dir = rel_join(platform.root, source.target, directory)
            rows.append(
                f"| {escape_cell(name)} | `{escape_cell(target_dir)}` | "
                f"{escape_cell(category)} | {file_count} | {escape_cell(description)} |"
            )
        sections.append(f"### {source.title}\n\n" + "\n".join(rows) + "\n")

    if logs:
        log_rows = ["| Date | Change Log | Summary |", "| --- | --- | --- |"]
        for slug, log_path, summary in logs:
            log_rows.append(f"| {slug} | [{slug}]({log_path}) | {escape_cell(summary)} |")
        recent = "\n".join(log_rows)
    else:
        recent = "暂无。"

    source_lines = "\n".join(
        f"- `{source.target}` <= `{source.source}`" for source in platform.sources
    )

    return f"""# {platform.title} Skills And Experts

本文件由 `scripts/sync_platform.py --platform {platform.name}` 自动生成，整理 `{platform.root}/` 下同步的技能、专家团和插件索引。

## 同步概览

- 平台目录：`{platform.root}/`
- 定时任务：`{platform.task_name}`，每天 18:00 运行
- 当前索引条目数：{total_items}
- 当前索引文件数：{total_files}
- 最近变更：{latest_line}

## 数据来源

{source_lines}

## 分类索引

{chr(10).join(sections)}
## 最近变更

{recent}
"""


def write_readme(platform: PlatformSpec, repo_root: Path, latest_log: Path | None) -> Path:
    path = repo_root / platform.readme
    path.write_text(render_readme(platform, repo_root, latest_log), encoding="utf-8")
    return path


def run_git(repo_root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=True,
    )


def commit_and_maybe_push(repo_root: Path, platform: PlatformSpec, timestamp: datetime, push: bool) -> None:
    git_lock = acquire_lock(repo_root / ".git-sync.lock", blocking=True)
    try:
        paths = [platform.root, platform.readme, "README.md", "scripts"]
        run_git(repo_root, ["add", *paths])
        staged = run_git(repo_root, ["diff", "--cached", "--name-only"]).stdout.strip()
        if not staged:
            print("No staged changes to commit.")
            return
        message = f"sync {platform.name}: {timestamp.strftime('%Y-%m-%d %H:%M')}"
        print(run_git(repo_root, ["commit", "-m", message]).stdout.strip())
        if push:
            gh = shutil.which("gh")
            if gh is None:
                raise RuntimeError("gh CLI is required for --push but was not found")
            subprocess.run(["gh", "auth", "setup-git", "-h", "github.com"], cwd=repo_root, check=True)
            print(run_git(repo_root, ["push", "-u", "origin", "main"]).stdout.strip())
    finally:
        git_lock.close()


def write_root_readme(repo_root: Path) -> None:
    path = repo_root / "README.md"
    path.write_text(
        """# AI Skills And Experts Archive

本仓库按平台同步本机 AI 工具的 skills、experts 和插件市场内容。

| Platform | Directory | Index |
| --- | --- | --- |
| Doubao | `doubao/` | [README-doubao.md](README-doubao.md) |
| WorkBuddy | `workbuddy/` | [README-workbuddy.md](README-workbuddy.md) |
| QwenWork | `qwenwork/` | [README-qwenwork.md](README-qwenwork.md) |

每个平台目录内都有独立的 `change-logs/` 和 `archive/deleted/`。定时任务每天 18:00 分别运行，三个平台的同步范围互不重叠。
""",
        encoding="utf-8",
    )


def sync_platform(args: argparse.Namespace) -> int:
    platform = PLATFORMS[args.platform]
    repo_root = args.repo_root.resolve()
    platform_root = repo_root / platform.root
    timestamp = now_in_timezone(args.timezone)
    slug = timestamp.strftime("%Y-%m-%d-%H%M%S")
    archive_root = platform_root / "archive" / "deleted" / slug

    lock = acquire_lock(repo_root / f".sync-{platform.name}.lock", blocking=False)
    try:
        source_files: dict[str, Path] = {}
        target_files: dict[str, Path] = {}
        for source in platform.sources:
            source_files.update(list_source_files(source))
            target_files.update(list_target_files(platform_root, source))
        changes = detect_changes(source_files, target_files)
        print(
            f"{platform.name}: {len(changes.added)} added, "
            f"{len(changes.modified)} modified, {len(changes.deleted)} deleted"
        )
        if args.dry_run:
            return 0

        latest_log: Path | None = None
        if changes.has_changes:
            platform_root.mkdir(parents=True, exist_ok=True)
            copy_files(platform_root, source_files, (*changes.added, *changes.modified))
            if changes.deleted:
                archive_deleted(platform_root, archive_root, changes.deleted)
            latest_log = write_change_log(platform, repo_root, timestamp, changes, archive_root)
        elif not args.refresh_docs:
            print(f"{platform.name}: no source changes; docs were left untouched")
            return 0

        (platform_root / "archive" / "deleted").mkdir(parents=True, exist_ok=True)
        (platform_root / "change-logs").mkdir(parents=True, exist_ok=True)
        write_readme(platform, repo_root, latest_log)
        write_root_readme(repo_root)
        if args.commit or args.push:
            commit_and_maybe_push(repo_root, platform, timestamp, args.push)
        return 0
    finally:
        lock.close()


def main() -> int:
    args = parse_args()
    if args.push:
        args.commit = True
    try:
        return sync_platform(args)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
