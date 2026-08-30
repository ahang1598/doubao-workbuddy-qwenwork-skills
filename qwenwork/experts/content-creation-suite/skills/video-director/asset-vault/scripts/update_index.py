#!/usr/bin/env python3
"""
资产库索引更新脚本

功能：扫描 asset-vault 目录，自动生成/更新以下索引文件：
- _index/catalog.md（人可读的资产总目录）
- _index/by_industry.json（按行业索引）
- _index/by_platform.json（按平台索引）
- _index/by_type.json（按类型索引）
- patterns/*/_summary.md 与 industry/*/_summary.md 中的自动资产清单

使用方式：
  python scripts/update_index.py [--vault-path <path>]

默认 vault-path 为脚本所在目录的上一级（即 asset-vault/）
"""

import json
import sys
from datetime import datetime
from pathlib import Path


PATTERN_SUMMARY_DIRECTORIES = [
    ("script-structures", "脚本结构"),
    ("hooks", "Hook 句式"),
    ("selling-points", "卖点规律"),
    ("creative-techniques", "创作技巧"),
    ("platform-rules", "平台规律"),
    ("methodologies", "方法论"),
]

AUTO_SUMMARY_START = "<!-- AUTO_ASSET_LIST_START -->"
AUTO_SUMMARY_END = "<!-- AUTO_ASSET_LIST_END -->"


def find_vault_path():
    """确定 asset-vault 根目录"""
    if len(sys.argv) > 2 and sys.argv[1] == "--vault-path":
        return Path(sys.argv[2])
    return Path(__file__).parent.parent


def load_metadata(project_dir: Path) -> dict:
    """读取项目的 metadata.json"""
    metadata_path = project_dir / "metadata.json"
    if metadata_path.exists():
        with open(metadata_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def scan_projects(vault_path: Path) -> list:
    """扫描所有项目目录，收集元信息（一级扁平结构）"""
    projects_dir = vault_path / "projects"
    if not projects_dir.exists():
        return []

    projects = []
    for project_dir in sorted(projects_dir.iterdir()):
        if not project_dir.is_dir():
            continue
        metadata = load_metadata(project_dir)
        projects.append({
            "path": str(project_dir.relative_to(vault_path)),
            "dir_name": project_dir.name,
            **metadata,
        })
    return projects


def scan_patterns(vault_path: Path) -> dict:
    """扫描汇总层的 patterns 和 industry 目录"""
    result = {
        "script_structures": [],
        "hooks": [],
        "selling_points": [],
        "creative_techniques": [],
        "platform_rules": [],
        "methodologies": [],
        "industries": [],
    }

    patterns_dir = vault_path / "patterns"
    if patterns_dir.exists():
        for subdir_name, key in [
            ("script-structures", "script_structures"),
            ("hooks", "hooks"),
            ("selling-points", "selling_points"),
            ("creative-techniques", "creative_techniques"),
            ("platform-rules", "platform_rules"),
            ("methodologies", "methodologies"),
        ]:
            subdir = patterns_dir / subdir_name
            if subdir.exists():
                for f in sorted(subdir.iterdir()):
                    if f.is_file() and f.suffix == ".md" and f.name != "_summary.md":
                        result[key].append(f.stem)

    industry_dir = vault_path / "industry"
    if industry_dir.exists():
        for d in sorted(industry_dir.iterdir()):
            if d.is_dir():
                result["industries"].append(d.name)

    return result


def generate_catalog(vault_path: Path, projects: list, patterns: dict) -> str:
    """生成 catalog.md 内容"""
    now = datetime.now().strftime("%Y-%m-%d")
    lines = [
        "# 资产库目录",
        "",
        f"> 最后更新：{now} | 项目总数：{len(projects)}",
        "",
        "## 项目归档（projects/）",
        "",
        "| 日期 | 客户 | 项目 | 行业 | 平台 | 脚本类型 | 状态 |",
        "|------|------|------|------|------|---------|------|",
    ]

    for p in projects:
        date = p.get("date", "")
        client = p.get("client", "")
        project = p.get("project", "")
        industry = p.get("industry", "")
        platform = p.get("platform", "")
        script_type = p.get("script_type", "")
        status = p.get("status", "")
        lines.append(f"| {date} | {client} | {project} | {industry} | {platform} | {script_type} | {status} |")

    lines.extend([
        "",
        "## 内容模式（patterns/）",
        "",
        "### 脚本结构",
    ])
    if patterns["script_structures"]:
        for item in patterns["script_structures"]:
            lines.append(f"- {item}")
    else:
        lines.append("（暂无）")

    lines.extend(["", "### Hook 句式"])
    if patterns["hooks"]:
        for item in patterns["hooks"]:
            lines.append(f"- {item}")
    else:
        lines.append("（暂无）")

    lines.extend(["", "### 卖点规律"])
    if patterns["selling_points"]:
        for item in patterns["selling_points"]:
            lines.append(f"- {item}")
    else:
        lines.append("（暂无）")

    lines.extend(["", "### 创作技巧"])
    if patterns["creative_techniques"]:
        for item in patterns["creative_techniques"]:
            lines.append(f"- {item}")
    else:
        lines.append("（暂无）")

    lines.extend(["", "### 平台规律"])
    if patterns["platform_rules"]:
        for item in patterns["platform_rules"]:
            lines.append(f"- {item}")
    else:
        lines.append("（暂无）")

    lines.extend(["", "### 方法论"])
    if patterns["methodologies"]:
        for item in patterns["methodologies"]:
            lines.append(f"- {item}")
    else:
        lines.append("（暂无）")

    lines.extend(["", "## 行业知识（industry/）", ""])
    if patterns["industries"]:
        for industry in patterns["industries"]:
            count = sum(1 for p in projects if p.get("industry") == industry)
            lines.append(f"- {industry}（{count} 个项目）")
    else:
        lines.append("（暂无）")

    lines.extend(["", "## 数据基准（benchmarks/）", ""])
    benchmarks_dir = vault_path / "benchmarks"
    if benchmarks_dir.exists() and any(benchmarks_dir.rglob("*.md")):
        for f in benchmarks_dir.rglob("*.md"):
            lines.append(f"- {f.relative_to(benchmarks_dir)}")
    else:
        lines.append("（暂无）")

    return "\n".join(lines) + "\n"


def read_markdown_title(file_path: Path) -> str:
    """从 Markdown 文件中提取标题，优先使用 frontmatter title，其次使用一级标题，最后使用文件名。"""
    try:
        content = file_path.read_text(encoding="utf-8")
    except OSError:
        return file_path.stem

    lines = content.splitlines()
    if lines and lines[0].strip() == "---":
        for line in lines[1:]:
            if line.strip() == "---":
                break
            if line.startswith("title:"):
                title = line.split(":", 1)[1].strip().strip('"').strip("'")
                if title:
                    return title

    for line in lines:
        if line.startswith("# "):
            return line.removeprefix("# ").strip()

    return file_path.stem


def list_markdown_assets(directory: Path) -> list[dict]:
    """列出目录下除 _summary.md 外的 Markdown 资产。"""
    if not directory.exists():
        return []

    assets = []
    for markdown_file in sorted(directory.iterdir()):
        if not markdown_file.is_file():
            continue
        if markdown_file.suffix != ".md" or markdown_file.name == "_summary.md":
            continue
        assets.append({
            "name": markdown_file.stem,
            "title": read_markdown_title(markdown_file),
            "file": markdown_file.name,
        })
    return assets


def build_auto_asset_list_section(assets: list[dict]) -> str:
    """生成 _summary.md 中由脚本维护的资产清单区块。"""
    now = datetime.now().strftime("%Y-%m-%d")
    lines = [
        AUTO_SUMMARY_START,
        "",
        "## 自动资产清单",
        "",
        f"> 由 `update_index.py` 自动维护，最后更新：{now}",
        "",
    ]

    if assets:
        for asset in assets:
            lines.append(f"- [{asset['title']}]({asset['file']})")
    else:
        lines.append("（暂无资产）")

    lines.extend(["", AUTO_SUMMARY_END])
    return "\n".join(lines)


def merge_auto_summary_section(existing_content: str, auto_section: str) -> str:
    """保留人工内容，仅替换自动资产清单区块。"""
    start_index = existing_content.find(AUTO_SUMMARY_START)
    end_index = existing_content.find(AUTO_SUMMARY_END)

    if start_index != -1 and end_index != -1 and end_index > start_index:
        end_index += len(AUTO_SUMMARY_END)
        merged = existing_content[:start_index].rstrip()
        merged += "\n\n" + auto_section
        trailing_content = existing_content[end_index:].strip()
        if trailing_content:
            merged += "\n\n" + trailing_content
        return merged.rstrip() + "\n"

    if existing_content.strip():
        return existing_content.rstrip() + "\n\n" + auto_section + "\n"
    return auto_section + "\n"


def ensure_summary_file(directory: Path, title: str) -> bool:
    """确保指定目录存在 _summary.md，并维护其中的自动资产清单。"""
    if not directory.exists() or not directory.is_dir():
        return False

    assets = list_markdown_assets(directory)
    summary_path = directory / "_summary.md"
    auto_section = build_auto_asset_list_section(assets)

    if summary_path.exists():
        existing_content = summary_path.read_text(encoding="utf-8")
    else:
        today = datetime.now().strftime("%Y-%m-%d")
        existing_content = (
            f"---\n"
            f"title: {title}\n"
            f"type: summary\n"
            f"created: {today}\n"
            f"updated: {today}\n"
            f"---\n\n"
            f"# {title}\n"
        )

    new_content = merge_auto_summary_section(existing_content, auto_section)
    if summary_path.exists() and summary_path.read_text(encoding="utf-8") == new_content:
        return False

    summary_path.write_text(new_content, encoding="utf-8")
    return True


def update_summary_files(vault_path: Path) -> int:
    """自动更新 patterns 子目录和 industry 子目录下的 _summary.md。"""
    updated_count = 0

    patterns_dir = vault_path / "patterns"
    for directory_name, display_name in PATTERN_SUMMARY_DIRECTORIES:
        if ensure_summary_file(patterns_dir / directory_name, display_name):
            updated_count += 1

    industry_dir = vault_path / "industry"
    if industry_dir.exists():
        for industry_subdir in sorted(industry_dir.iterdir()):
            if not industry_subdir.is_dir():
                continue
            if ensure_summary_file(industry_subdir, f"{industry_subdir.name} 行业知识总览"):
                updated_count += 1

    return updated_count


def generate_by_industry(projects: list) -> dict:
    """生成按行业索引"""
    index = {}
    for p in projects:
        industry = p.get("industry", "未分类")
        if industry not in index:
            index[industry] = []
        index[industry].append({
            "path": p["path"],
            "date": p.get("date", ""),
            "client": p.get("client", ""),
            "project": p.get("project", ""),
            "platform": p.get("platform", ""),
            "status": p.get("status", ""),
        })
    return index


def generate_by_platform(projects: list) -> dict:
    """生成按平台索引"""
    index = {}
    for p in projects:
        platform = p.get("platform", "未分类")
        if platform not in index:
            index[platform] = []
        index[platform].append({
            "path": p["path"],
            "date": p.get("date", ""),
            "client": p.get("client", ""),
            "project": p.get("project", ""),
            "industry": p.get("industry", ""),
            "status": p.get("status", ""),
        })
    return index


def generate_by_type(projects: list) -> dict:
    """生成按脚本类型索引"""
    index = {}
    for p in projects:
        script_type = p.get("script_type", "未分类")
        if not script_type:
            script_type = "未分类"
        if script_type not in index:
            index[script_type] = []
        index[script_type].append({
            "path": p["path"],
            "date": p.get("date", ""),
            "client": p.get("client", ""),
            "project": p.get("project", ""),
            "industry": p.get("industry", ""),
            "platform": p.get("platform", ""),
            "status": p.get("status", ""),
        })
    return index


def main():
    vault_path = find_vault_path()
    print(f"资产库路径：{vault_path}")

    index_dir = vault_path / "_index"
    index_dir.mkdir(parents=True, exist_ok=True)

    projects = scan_projects(vault_path)
    patterns = scan_patterns(vault_path)

    print(f"扫描到 {len(projects)} 个项目")

    catalog_content = generate_catalog(vault_path, projects, patterns)
    (index_dir / "catalog.md").write_text(catalog_content, encoding="utf-8")
    print("✅ 已更新 _index/catalog.md")

    by_industry = generate_by_industry(projects)
    (index_dir / "by_industry.json").write_text(
        json.dumps(by_industry, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("✅ 已更新 _index/by_industry.json")

    by_platform = generate_by_platform(projects)
    (index_dir / "by_platform.json").write_text(
        json.dumps(by_platform, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("✅ 已更新 _index/by_platform.json")

    by_type = generate_by_type(projects)
    (index_dir / "by_type.json").write_text(
        json.dumps(by_type, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("✅ 已更新 _index/by_type.json")

    summary_updated_count = update_summary_files(vault_path)
    print(f"✅ 已更新 {summary_updated_count} 个 _summary.md 自动资产清单")

    print(f"\n索引更新完成！项目数：{len(projects)} | 行业数：{len(patterns['industries'])}")


if __name__ == "__main__":
    main()
