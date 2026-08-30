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

# Name of the generated navigation file written at each sync target root.
SUMMARY_FILENAME = "SUMMARY.md"

# Ordered scenario catalog. Each value is a tuple of substrings (matched
# case-insensitively against an item's name, description and keywords). An item
# may match several scenarios; the first match becomes its primary category in
# the full table. Items matching nothing fall back to "其他".
#
# Ordering matters: more specific domains come first so an item's primary
# category reflects its true purpose (e.g. a document plugin is "文档/表格/PPT"
# rather than "代码开发", even though its description mentions Codex).
SCENARIOS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("金融研究", (
        "finance", "financial", "stock", "equity", "earnings", "investment",
        "valuation", "dcf", "lbo", "trading", "trade", "hedge", "wealth",
        "broker", "券商", "财报", "股票", "估值", "投资",
        "金融", "证券", "市值", "资本", "盘面",
    )),
    ("投资银行/私募", (
        "investment-banking", "private-equity", "pe-vc", "m&a", "ma ",
        "投行", "私募", "融资", "募资", "并购",
    )),
    ("数据分析", (
        # Keep this scenario precise: bare "数据"/"查询"/"excel" are too
        # generic (they appear in almost every skill description). Match on
        # analytics-specific terms and tooling instead.
        "data-analytics", "data-analysis", "analytics", "sql", "dashboard",
        "etl", "数据可视化", "数据建模", "数据探索", "仪表盘", "数据看板",
        "数据科学", "data science", "data pipeline", "bi ", "business intelligence",
    )),
    ("文档/表格/PPT", (
        "docx", "pdf", "xlsx", "pptx", "spreadsheet", "word文档", "word 文档",
        "google docs", "google doc", "google sheets", "powerpoint",
        "会议纪要", "表格", "文档生成", "word 报告", "word文件",
    )),
    ("设计可视化", (
        "creative-design", "visualization", "海报", "图表", "可视化", "设计",
        "imagegen", "图像生成", "主视觉", "banner", "海报设计", "视觉设计",
        "echarts", "data viz", "信息图",
    )),
    ("研究/调研", (
        "research", "deep-research", "arxiv", "调研", "深度研究", "研究报告",
        "academic", "文献", "论文", "智库", "学术研究", "literature review",
    )),
    ("营销/内容运营", (
        "marketing", "seo", "newmedia", "新媒体", "小红书", "公众号",
        "社媒", "运营", "推广", "增长", "monetization", "distribution",
        "oceanengine", "巨量", "广告投放", "内容营销", "营销活动",
        "cross-border", "跨境电商", "电商", "商品", "带货", "直播",
    )),
    ("协作/办公", (
        # Lark/Feishu/Slack ecosystems plus concrete collaboration nouns.
        # Avoid generic "task"/"note"/"wiki"/"project" which match too broadly.
        "lark-", "feishu", "飞书", "slack", "考勤", "审批", "okr",
        "日程", "会议纪要", "站会", "standup", "minutes", "协作平台",
    )),
    ("法务/合规", (
        "legal", "contract", "compliance", "tax", "法务", "合同", "合规",
        "税务", "审计", "发票", "invoice", "专利", "patent",
    )),
    ("医疗", (
        "medical", "clinical", "医学", "临床", "病历", "诊断",
    )),
    ("教育/考试", (
        "gaokao", "ncre", "ket", "高考", "考试", "教学", "课程", "课件",
    )),
    ("代码开发", (
        "coding", "code-", "code ", "codebase", "code review",
        "develop", "sdk", "backend", "frontend", "webapp", "web-app",
        "typescript", "javascript", "dockerfile", "refactor", "review-agent",
        "scaffolding", "lsp", "cicd", "ci/cd", "github", "gitlab",
        "codebuddy", "programming", "compiler", "debug", "app-builder",
        "product-qa", "产品qa",
    )),
    ("通用工具/平台", (
        "identity", "cron", "scheduler", "record", "skill-creator",
        "plugin-creator", "skill-installer", "browser", "computer-use",
        "sites", "template", "通用", "工具", "平台", "skillhub",
        "openai-docs", "cron-scheduler", "录音", "video-extract", "视频提取",
        "audio", "语音合成", "tts", "pc-optimizer", "系统优化",
    )),
)

FALLBACK_SCENARIO = "其他"


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
            SourceSpec(
                name="connectors_marketplace",
                title="Connectors / Marketplace",
                source=Path("/mnt/c/Users/15805/.workbuddy/connectors-marketplace"),
                target="connectors/marketplace",
                item_kind="connector",
            ),
            SourceSpec(
                name="connectors_default",
                title="Connectors / Default MCP Config",
                source=Path("/mnt/c/Users/15805/.workbuddy/connectors/default/mcp.json"),
                target="connectors/default/mcp.json",
                item_kind="connector config",
                source_is_file=True,
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
    "chatgpt": PlatformSpec(
        name="chatgpt",
        title="ChatGPT",
        root="chatgpt",
        readme="README-chatgpt.md",
        task_name="ChatgptSkillsDailySync",
        sources=(
            SourceSpec(
                name="skills",
                title="System Skills",
                source=Path("/mnt/c/Users/15805/.codex/skills/.system"),
                target="skills",
                item_kind="skill",
            ),
            SourceSpec(
                name="plugins",
                title="Plugin Cache",
                source=Path("/mnt/c/Users/15805/.codex/plugins/cache"),
                target="plugins",
                item_kind="plugin cache",
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


def protected_summary_rel(source: SourceSpec) -> str:
    """The repo-relative path of the generated SUMMARY.md for ``source``."""
    return rel_join(source.target, SUMMARY_FILENAME)


def list_source_files(source: SourceSpec) -> dict[str, Path]:
    if not source.source.exists():
        raise FileNotFoundError(f"source does not exist: {source.source}")
    if source.source_is_file:
        if not source.source.is_file():
            raise FileNotFoundError(f"source is not a file: {source.source}")
        return {source.target: source.source}
    if not source.source.is_dir():
        raise NotADirectoryError(f"source is not a directory: {source.source}")
    generated_rel = SUMMARY_FILENAME  # the SUMMARY.md that would sit at the source root
    files: dict[str, Path] = {}
    for path in source.source.rglob("*"):
        if path.is_file():
            rel = path.relative_to(source.source).as_posix()
            if not source.source_is_file and rel == generated_rel:
                # A SUMMARY.md at the source root would collide with our
                # generated navigation file; skip it to avoid overwriting.
                print(
                    f"WARNING: skipping source-root {SUMMARY_FILENAME} at "
                    f"{source.source} to protect the generated navigation file."
                )
                continue
            files[rel_join(source.target, rel)] = path
    return files


def list_target_files(platform_root: Path, source: SourceSpec) -> dict[str, Path]:
    target = path_from_rel(platform_root, source.target)
    if not target.exists():
        return {}
    if source.source_is_file:
        return {source.target: target} if target.is_file() else {}
    protected = protected_summary_rel(source)
    files: dict[str, Path] = {}
    for path in target.rglob("*"):
        if path.is_file():
            rel = path.relative_to(platform_root).as_posix()
            if rel == protected:
                # Generated navigation file — never treat as a tracked target.
                continue
            files[rel] = path
    return files


def item_name(rel: str) -> str:
    parts = PurePosixPath(rel).parts
    if len(parts) <= 1:
        return parts[0] if parts else "(root)"
    if parts[0] == "plugins" and len(parts) > 3 and parts[3] == ".codex-remote-plugin-install.json":
        return f"{parts[0]}/{parts[1]}/{parts[2]}"
    if parts[0] == "plugins" and len(parts) > 3:
        return f"{parts[0]}/{parts[1]}/{parts[2]}/{parts[3]}"
    if parts[0] == "official_experts" and len(parts) > 2:
        return f"{parts[0]}/{parts[1]}/{parts[2]}"
    if parts[0] == "cb_teams_experts" and len(parts) > 2 and parts[1] == "plugins":
        return f"{parts[0]}/{parts[2]}"
    if parts[0] == "connectors" and parts[1] == "marketplace" and len(parts) > 3:
        # Group change logs per connector; icons and the manifest index as one
        # bucket each so a refresh does not list 150 separate icon rows.
        if parts[2] in {"icons", ".codebuddy-connector"}:
            return f"{parts[0]}/{parts[1]}/{parts[2]}"
        return "/".join(parts[:4])
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


def metadata_for_item(item_dir: Path, fallback_name: str) -> tuple[str, str, str, str]:
    """Return ``(name, description, category, keywords)`` for an item dir.

    ``keywords`` is a flattened string drawn from the plugin manifest's
    ``keywords`` field when present; classification also folds the name and
    description in, so an empty string here is acceptable for SKILL.md items.
    """
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
            keywords = extract_keywords(
                name, description, data.get("keywords") or data.get("tags")
            )
            return str(name), one_line(str(description)), str(category), keywords

    # Connectors and bundled plugin layouts keep their SKILL.md one level
    # deeper (e.g. <connector>/skills/SKILL.md), so probe both locations.
    skill_md = next(
        (p for p in (item_dir / "SKILL.md", item_dir / "skills" / "SKILL.md") if p.exists()),
        None,
    )
    if skill_md is not None:
        front = parse_front_matter(read_text(skill_md))
        name = front.get("name") or fallback_name
        description = one_line(front.get("description") or read_readme_summary(item_dir))
        return name, description, "", extract_keywords(name, description, None)

    description = one_line(read_readme_summary(item_dir) or "No description found.")
    return fallback_name, description, "", extract_keywords(fallback_name, description, None)


def extract_keywords(name: str, description: str, raw_keywords) -> str:
    """Best-effort keyword string for classification and display.

    Prefers explicit manifest ``keywords``/``tags``; otherwise falls back to
    the item name. The description is intentionally NOT folded in here (it is
    passed separately to :func:`classify_item`), so the displayed keyword
    column stays concise.
    """
    parts: list[str] = []
    if isinstance(raw_keywords, list):
        parts.extend(localized(k) for k in raw_keywords if localized(k))
    elif isinstance(raw_keywords, str) and raw_keywords.strip():
        parts.append(raw_keywords.strip())
    if name:
        parts.append(str(name))
    return one_line(" ".join(parts), 200)


def classify_item(name: str, description: str, keywords: str) -> list[str]:
    """Return the ordered list of scenario labels an item matches. The first
    entry is its primary category for the full directory table. Falls back to
    ``FALLBACK_SCENARIO`` when nothing matches."""
    haystack = f"{name} {description} {keywords}".lower()
    matched: list[str] = []
    for label, rules in SCENARIOS:
        for token in rules:
            if token.lower() in haystack:
                matched.append(label)
                break
    return matched or [FALLBACK_SCENARIO]


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


def chatgpt_plugin_entries(target: Path, source: SourceSpec):
    """Entries for the nested ChatGPT plugin cache.

    Returns 6-tuples ``(name, directory, category, file_count, description,
    keywords)``. ``directory`` is the concrete versioned plugin path such as
    ``openai-bundled/browser/26.727.51351`` rather than the top-level cache dir.
    """
    entries = []
    manifests = sorted(target.glob("*/*/*/.codex-plugin/plugin.json"))
    for manifest in manifests:
        item = manifest.parents[1]
        rel_dir = item.relative_to(target).as_posix()
        parts = PurePosixPath(rel_dir).parts
        fallback_name = parts[1] if len(parts) > 1 else item.name
        name, description, category, keywords = metadata_for_item(item, fallback_name)
        file_count = sum(1 for p in item.rglob("*") if p.is_file())
        provider = parts[0] if parts else source.item_kind
        version = parts[2] if len(parts) > 2 else item.name
        entries.append((
            name,
            rel_dir,
            category or provider,
            file_count,
            f"{description} Version: {version}.",
            keywords,
        ))
    return entries


def connector_marketplace_entries(target: Path, source: SourceSpec):
    """Entries for the WorkBuddy connectors marketplace.

    The marketplace root syncs ``connectors/`` (one dir per connector),
    ``icons/`` and the ``.codebuddy-connector/connectors.json`` manifest. The
    index enumerates the inner ``connectors/*`` dirs and prefers the manifest's
    per-connector metadata (id/name/description_zh/type), falling back to each
    item's ``skills/SKILL.md`` front matter.
    """
    manifest = load_json(target / ".codebuddy-connector" / "connectors.json")
    meta_by_id: dict[str, dict] = {}
    for conn in manifest.get("connectors", []) or []:
        if isinstance(conn, dict) and conn.get("id"):
            meta_by_id[str(conn["id"])] = conn

    entries = []
    items_root = target / "connectors"
    for item in sorted((p for p in items_root.iterdir() if p.is_dir()), key=lambda p: p.name):
        meta = meta_by_id.get(item.name, {})
        name = (
            str(meta.get("name") or meta.get("name_en") or item.name)
            if meta
            else item.name
        )
        description = ""
        category = ""
        if meta:
            description = one_line(str(meta.get("description_zh") or meta.get("description") or meta.get("description_en") or ""))
            category = str(meta.get("type") or "")
            version = meta.get("version")
            if version:
                description = one_line(f"{description} Version: {version}.")
        if not description:
            _fb_name, fb_desc, _fb_cat, _fb_kw = metadata_for_item(item, item.name)
            description = fb_desc
        keywords = extract_keywords(f"{name} {meta.get('name_en', '') or item.name}", description, None)
        file_count = sum(1 for p in item.rglob("*") if p.is_file())
        entries.append((
            name,
            f"connectors/{item.name}",
            category or source.item_kind,
            file_count,
            description,
            keywords,
        ))
    return entries


def source_entries(platform_root: Path, source: SourceSpec, cb_analysis: dict[str, tuple[str, str]]):
    """Entries for a directory source as 6-tuples
    ``(name, directory, category, file_count, description, keywords)``."""
    target = path_from_rel(platform_root, source.target)
    if source.source_is_file:
        return []
    if not target.exists():
        return []
    if source.name == "plugins" and (target / "openai-bundled").exists():
        entries = chatgpt_plugin_entries(target, source)
        if entries:
            return entries
    if source.name == "connectors_marketplace" and (target / "connectors").is_dir():
        entries = connector_marketplace_entries(target, source)
        if entries:
            return entries
    entries = []
    for item in sorted((p for p in target.iterdir() if p.is_dir()), key=lambda p: p.name):
        name, description, category, keywords = metadata_for_item(item, item.name)
        if source.name == "cb_teams_experts":
            override = cb_analysis.get(item.name)
            if override:
                category = override[0] or category
                description = override[1] or description
                keywords = extract_keywords(name, description, override[1])
        file_count = sum(1 for p in item.rglob("*") if p.is_file())
        entries.append((name, item.name, category or source.item_kind, file_count, description, keywords))
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


def last_sync_time(change_logs_dir: Path, timezone_name: str, fallback: str) -> str:
    """Return the timestamp string of the most recent real sync, parsed from
    the latest change-log filename (``YYYY-MM-DD-HHMMSS`` in local time) and
    re-formatted exactly like a real-sync stamp (``%Y-%m-%d %H:%M:%S %z``).

    Used as the SUMMARY "最近同步" value on no-source-change runs so the file
    stays byte-identical to disk and a no-op run writes nothing. Falls back to
    ``fallback`` when there are no parseable logs yet."""
    if not change_logs_dir.exists():
        return fallback
    logs = sorted(change_logs_dir.glob("*.md"), reverse=True)
    if not logs:
        return fallback
    stem = logs[0].stem  # e.g. 2026-08-10-160232
    match = re.match(r"^(\d{4})-(\d{2})-(\d{2})-(\d{2})(\d{2})(\d{2})$", stem)
    if not match:
        return fallback
    y, mo, d, h, mi, s = (int(g) for g in match.groups())
    tz = ZoneInfo(timezone_name) if ZoneInfo is not None else None
    try:
        naive = datetime(y, mo, d, h, mi, s)
        aware = naive.replace(tzinfo=tz) if tz is not None else naive.astimezone()
        return aware.strftime("%Y-%m-%d %H:%M:%S %z")
    except ValueError:
        return fallback


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
    nav_lines: list[str] = []
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
        for name, directory, category, file_count, description, _keywords in entries:
            total_files += file_count
            target_dir = rel_join(platform.root, source.target, directory)
            rows.append(
                f"| {escape_cell(name)} | `{escape_cell(target_dir)}` | "
                f"{escape_cell(category)} | {file_count} | {escape_cell(description)} |"
            )
        sections.append(f"### {source.title}\n\n" + "\n".join(rows) + "\n")
        if not source.source_is_file:
            summary_rel = rel_join(platform.root, source.target, SUMMARY_FILENAME)
            nav_lines.append(
                f"- [{source.title}]({summary_rel}) — `{source.target}/` 功能导航"
            )

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
    nav_block = "\n".join(nav_lines) if nav_lines else "暂无。"

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

## 导航文件

各同步目录根部的 `{SUMMARY_FILENAME}` 提供按用途分组的场景导航，便于快速定位：

{nav_block}

## 分类索引

{chr(10).join(sections)}
## 最近变更

{recent}
"""


def write_readme(platform: PlatformSpec, repo_root: Path, latest_log: Path | None) -> tuple[Path, bool]:
    path = repo_root / platform.readme
    changed = write_if_changed(path, render_readme(platform, repo_root, latest_log))
    return path, changed


def render_summary(
    platform: PlatformSpec,
    repo_root: Path,
    source: SourceSpec,
    entries: list[tuple],
    sync_time: str,
) -> str:
    """Render the 3-section navigation file for one source directory.

    ``entries`` are the 6-tuples produced by :func:`source_entries``.
    ``sync_time`` is the pre-formatted "最近同步" timestamp string; on a
    no-source-change run it is the last *real* sync time (read from the latest
    change-log) rather than "now", so the file stays byte-identical and a no-op
    run produces no diff.
    Layout: 概览 (overview) -> 场景导航 (scenario navigation, multi-scenario)
    -> 完整目录表 (full directory table with primary scenario as 类型).
    """
    total_files = sum(entry[3] for entry in entries)
    target_dir_rel = rel_join(platform.root, source.target)
    stamp = sync_time

    # ---- Overview ----
    overview_lines = [
        f"- 目录：`{target_dir_rel}/`",
        f"- 来源：`{source.source}`",
        f"- 条目数：{len(entries)}",
        f"- 文件数：{total_files}",
        f"- 最近同步：{stamp}",
    ]
    if source.name == "cb_teams_experts":
        overview_lines.append(
            "- 原始分析报告：[plugins_analysis_company_analysis.md]"
            "(../plugins_analysis_company_analysis.md)"
        )

    # ---- Scenario navigation (multi-scenario) ----
    # Map each entry to its matched scenario list; primary = first.
    entry_scenarios: list[tuple[tuple, list[str]]] = []
    for entry in entries:
        name, _directory, _category, _file_count, description, keywords = entry
        entry_scenarios.append((entry, classify_item(name, description, keywords)))

    ordered_labels = [label for label, _ in SCENARIOS] + [FALLBACK_SCENARIO]
    scenario_blocks: list[str] = []
    for label in ordered_labels:
        members = [
            (entry, scenarios)
            for entry, scenarios in entry_scenarios
            if label in scenarios
        ]
        if not members:
            continue
        lines = [f"### {label}"]
        for (name, _directory, _category, _file_count, description, _kw), _scen in members:
            lines.append(f"- **{escape_cell(name)}** — {escape_cell(description)}")
        scenario_blocks.append("\n".join(lines))
    scenario_section = "\n\n".join(scenario_blocks) if scenario_blocks else "暂无条目。"

    # ---- Full directory table ----
    rows = ["| 名称 | 目录 | 类型 | 关键词 | 文件数 | 说明 |", "| --- | --- | --- | --- | ---: | --- |"]
    for entry, scenarios in entry_scenarios:
        name, directory, _category, file_count, description, keywords = entry
        primary = scenarios[0]
        full_dir = rel_join(platform.root, source.target, directory)
        rows.append(
            f"| {escape_cell(name)} | `{escape_cell(full_dir)}` | "
            f"{escape_cell(primary)} | {escape_cell(keywords)} | {file_count} | "
            f"{escape_cell(description)} |"
        )
    full_table = "\n".join(rows)

    return f"""# {platform.title} / {source.title} 功能导航

本文件由 `scripts/sync_platform.py --platform {platform.name}` 自动生成，是 `{target_dir_rel}/` 下条目的使用导航。平台总索引见 [{platform.readme}](../../{platform.readme})。

## 概览

{chr(10).join(overview_lines)}

## 场景导航（按用途）

{scenario_section}

## 完整目录表

{full_table}
"""


def write_summary_file(
    platform: PlatformSpec,
    repo_root: Path,
    source: SourceSpec,
    entries: list[tuple],
    sync_time: str,
) -> tuple[Path, bool] | None:
    """Write the SUMMARY.md for one source only when its content changed.

    Returns ``(path, changed)`` where ``changed`` is True when the file was
    rewritten. Returns ``None`` for file sources or empty entry sets."""
    if source.source_is_file or not entries:
        return None
    target_dir = path_from_rel(repo_root / platform.root, source.target)
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / SUMMARY_FILENAME
    changed = write_if_changed(path, render_summary(platform, repo_root, source, entries, sync_time))
    return path, changed


def write_if_changed(path: Path, content: str) -> bool:
    """Write ``content`` to ``path`` only when it differs from the current
    file. Returns True when the file was (re)written, False when it was already
    up to date. This keeps no-op runs from touching mtimes or creating empty
    git diffs."""
    try:
        existing = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        existing = None
    if existing == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


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


def write_root_readme(repo_root: Path) -> bool:
    path = repo_root / "README.md"
    return write_if_changed(
        path,
        """# AI Skills And Experts Archive

本仓库按平台同步本机 AI 工具的 skills、experts 和插件市场内容。

| Platform | Directory | Index |
| --- | --- | --- |
| Doubao | `doubao/` | [README-doubao.md](README-doubao.md) |
| WorkBuddy | `workbuddy/` | [README-workbuddy.md](README-workbuddy.md) |
| QwenWork | `qwenwork/` | [README-qwenwork.md](README-qwenwork.md) |
| ChatGPT | `chatgpt/` | [README-chatgpt.md](README-chatgpt.md) |

每个平台目录内都有独立的 `change-logs/` 和 `archive/deleted/`。定时任务每天 18:00 分别运行，各平台的同步范围互不重叠。
""",
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
            # Daily cron path: no source changes, no manual doc refresh.
            # Skip README/SUMMARY regeneration and commit/push entirely so a
            # no-op run produces no git activity.
            print(f"{platform.name}: no source changes; skipped SUMMARY/README + commit/push")
            return 0

        (platform_root / "archive" / "deleted").mkdir(parents=True, exist_ok=True)
        (platform_root / "change-logs").mkdir(parents=True, exist_ok=True)

        # "最近同步" time for generated docs. On a real sync this is "now";
        # on a no-source-change run it is the last *real* sync time (from the
        # latest change-log) so the SUMMARY content stays byte-identical and a
        # no-op run writes nothing.
        now_stamp = timestamp.strftime("%Y-%m-%d %H:%M:%S %z")
        if changes.has_changes:
            sync_time = now_stamp
        else:
            sync_time = last_sync_time(platform_root / "change-logs", args.timezone, now_stamp)

        # Regenerate docs, but only write files whose content actually changed.
        # On a no-change --refresh-docs run this touches nothing on disk.
        docs_changed = False
        _readme_path, readme_changed = write_readme(platform, repo_root, latest_log)
        docs_changed = docs_changed or readme_changed
        docs_changed = write_root_readme(repo_root) or docs_changed
        cb_analysis = parse_cb_teams_analysis(
            platform_root / "cb_teams_experts" / "plugins_analysis_company_analysis.md"
        )
        for source in platform.sources:
            entries = source_entries(platform_root, source, cb_analysis)
            if source.source_is_file or not entries:
                continue
            result = write_summary_file(platform, repo_root, source, entries, sync_time)
            if result and result[1]:
                docs_changed = True

        if not changes.has_changes and not docs_changed:
            # Reached here via --refresh-docs with no source changes, and every
            # generated doc was byte-identical to disk. Nothing to commit.
            print(f"{platform.name}: no source changes; SUMMARY/README already up to date, skipped commit/push")
            return 0
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
