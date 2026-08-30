#!/usr/bin/env python3
"""
资产库一致性检查脚本

功能：检查资产库的健康状态，输出体检报告。
检查项：
1. 索引一致性：catalog.md 中的项目数 vs 实际项目目录数
2. 汇总一致性：_summary.md 缺失、自动清单漏列实际资产
3. 命名一致性：同目录疑似重复资产文件名
4. 陈旧内容：超过 90 天未更新的汇总文件
5. 缺失文件：项目目录中缺少固定产物文件或目录
6. 状态异常：metadata.json 中 status 异常的项目

使用方式：
  python scripts/check_consistency.py [--vault-path <path>]
"""

import json
import re
import sys
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from pathlib import Path


PATTERN_SUMMARY_DIRECTORIES = [
    "script-structures",
    "hooks",
    "selling-points",
    "creative-techniques",
    "platform-rules",
    "methodologies",
]

AUTO_SUMMARY_START = "<!-- AUTO_ASSET_LIST_START -->"
AUTO_SUMMARY_END = "<!-- AUTO_ASSET_LIST_END -->"

FIXED_PROJECT_ARTIFACTS = [
    ("metadata.json", "file"),
    ("step_01_brief.md", "file"),
    ("step_02_creative.md", "file"),
    ("step_03_script.md", "file"),
    ("final_script.md", "file"),
    ("uploads", "directory"),
]


def find_vault_path():
    if len(sys.argv) > 2 and sys.argv[1] == "--vault-path":
        return Path(sys.argv[2])
    return Path(__file__).parent.parent


def check_index_consistency(vault_path: Path) -> list:
    """检查索引与实际文件的一致性"""
    issues = []
    projects_dir = vault_path / "projects"
    catalog_path = vault_path / "_index" / "catalog.md"

    actual_projects = []
    if projects_dir.exists():
        for project_dir in projects_dir.iterdir():
            if project_dir.is_dir():
                actual_projects.append(project_dir)

    if not catalog_path.exists():
        if actual_projects:
            issues.append({
                "type": "索引缺失",
                "severity": "high",
                "message": f"_index/catalog.md 不存在，但有 {len(actual_projects)} 个项目目录",
                "fix": "运行 scripts/update_index.py 重建索引",
            })
        return issues

    catalog_content = catalog_path.read_text(encoding="utf-8")
    catalog_project_count = len(re.findall(r"^\| \d{4}-\d{2}-\d{2} \|", catalog_content, re.MULTILINE))

    if catalog_project_count != len(actual_projects):
        issues.append({
            "type": "索引不一致",
            "severity": "medium",
            "message": f"catalog.md 记录 {catalog_project_count} 个项目，实际有 {len(actual_projects)} 个",
            "fix": "运行 scripts/update_index.py 重建索引",
        })

    return issues


def check_missing_files(vault_path: Path) -> list:
    """检查项目目录中缺少的固定产物文件和目录。"""
    issues = []
    projects_dir = vault_path / "projects"
    if not projects_dir.exists():
        return issues

    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue

        for artifact_name, artifact_type in FIXED_PROJECT_ARTIFACTS:
            artifact_path = project_dir / artifact_name
            if artifact_type == "file" and artifact_path.is_file():
                continue
            if artifact_type == "directory" and artifact_path.is_dir():
                continue

            display_type = "目录" if artifact_type == "directory" else "文件"
            fix_action = "创建目录" if artifact_type == "directory" else "补写文件"
            issues.append({
                "type": "缺失固定产物",
                "severity": "medium",
                "message": f"{project_dir.name} 缺少固定产物{display_type} {artifact_name}",
                "fix": f"{fix_action} {project_dir / artifact_name}",
            })

    return issues


def check_status_anomalies(vault_path: Path) -> list:
    """检查状态异常的项目"""
    issues = []
    projects_dir = vault_path / "projects"
    if not projects_dir.exists():
        return issues

    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue
        metadata_path = project_dir / "metadata.json"
        if not metadata_path.exists():
            continue
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
        except (json.JSONDecodeError, IOError):
            issues.append({
                "type": "文件损坏",
                "severity": "high",
                "message": f"{project_dir.name}/metadata.json 格式错误",
                "fix": "修复 JSON 格式",
            })
            continue

        status = metadata.get("status", "")

        if status == "in_progress":
            has_final = (project_dir / "final_script.md").exists()
            if has_final:
                issues.append({
                    "type": "状态异常",
                    "severity": "medium",
                    "message": f"{project_dir.name} 有 final_script.md 但 status 仍为 in_progress",
                    "fix": "先更新 status 为 delivered；资产沉淀完成后再更新为 completed",
                })

        if status == "interrupted":
            issues.append({
                "type": "中断项目",
                "severity": "low",
                "message": f"{project_dir.name} 状态为 interrupted，待补做汇总",
                "fix": "在下次任务完成后对该项目执行汇总",
            })

    return issues


def iter_summary_directories(vault_path: Path) -> list[Path]:
    """返回需要维护 _summary.md 的资产目录。"""
    directories = []

    patterns_dir = vault_path / "patterns"
    for directory_name in PATTERN_SUMMARY_DIRECTORIES:
        asset_dir = patterns_dir / directory_name
        if asset_dir.exists() and asset_dir.is_dir():
            directories.append(asset_dir)

    industry_dir = vault_path / "industry"
    if industry_dir.exists():
        for industry_subdir in sorted(industry_dir.iterdir()):
            if industry_subdir.is_dir():
                directories.append(industry_subdir)

    return directories


def list_markdown_asset_files(directory: Path) -> list[Path]:
    """列出目录下除 _summary.md 外的 Markdown 资产文件。"""
    return [
        markdown_file
        for markdown_file in sorted(directory.iterdir())
        if markdown_file.is_file()
        and markdown_file.suffix == ".md"
        and markdown_file.name != "_summary.md"
    ]


def parse_auto_summary_files(summary_path: Path) -> set[str]:
    """解析 _summary.md 自动资产清单区块中列出的文件名。"""
    content = summary_path.read_text(encoding="utf-8")
    start_index = content.find(AUTO_SUMMARY_START)
    end_index = content.find(AUTO_SUMMARY_END)
    if start_index == -1 or end_index == -1 or end_index <= start_index:
        return set()

    auto_section = content[start_index:end_index]
    return set(re.findall(r"\]\(([^)]+\.md)\)", auto_section))


def normalize_asset_name(name: str) -> str:
    """归一化资产名，用于识别同目录疑似重复命名。"""
    normalized = name.lower()
    normalized = re.sub(r"[\s_\-（）()【】\[\]·,，。.:：/\\]+", "", normalized)
    replacements = {
        "评测": "测评",
        "开场": "开头",
        "句式": "话术",
        "方法": "方法论",
    }
    for source, target in replacements.items():
        normalized = normalized.replace(source, target)
    return normalized


def is_potential_duplicate_name(left_name: str, right_name: str) -> bool:
    """判断两个资产文件名是否疑似重复。"""
    normalized_left = normalize_asset_name(left_name)
    normalized_right = normalize_asset_name(right_name)

    if normalized_left == normalized_right:
        return True
    if normalized_left in normalized_right or normalized_right in normalized_left:
        return min(len(normalized_left), len(normalized_right)) >= 4

    similarity = SequenceMatcher(None, normalized_left, normalized_right).ratio()
    return similarity >= 0.86


def check_summary_consistency(vault_path: Path) -> list:
    """检查 _summary.md 是否缺失，以及自动清单是否漏列实际资产。"""
    issues = []

    for asset_dir in iter_summary_directories(vault_path):
        asset_files = list_markdown_asset_files(asset_dir)
        if not asset_files:
            continue

        summary_path = asset_dir / "_summary.md"
        relative_dir = asset_dir.relative_to(vault_path)
        if not summary_path.exists():
            issues.append({
                "type": "汇总缺失",
                "severity": "medium",
                "message": f"{relative_dir}/_summary.md 缺失，目录下有 {len(asset_files)} 个资产文件",
                "fix": "运行 scripts/update_index.py 自动生成 _summary.md",
            })
            continue

        listed_files = parse_auto_summary_files(summary_path)
        if not listed_files:
            issues.append({
                "type": "汇总清单缺失",
                "severity": "medium",
                "message": f"{relative_dir}/_summary.md 缺少自动资产清单区块",
                "fix": "运行 scripts/update_index.py 写入自动资产清单",
            })
            continue

        actual_files = {asset_file.name for asset_file in asset_files}
        missing_files = sorted(actual_files - listed_files)
        if missing_files:
            issues.append({
                "type": "汇总漏列",
                "severity": "medium",
                "message": f"{relative_dir}/_summary.md 漏列：{', '.join(missing_files)}",
                "fix": "运行 scripts/update_index.py 更新自动资产清单",
            })

    return issues


def check_duplicate_asset_names(vault_path: Path) -> list:
    """检查同目录下疑似重复的资产文件名。"""
    issues = []

    for asset_dir in iter_summary_directories(vault_path):
        asset_files = list_markdown_asset_files(asset_dir)
        for left_index, left_file in enumerate(asset_files):
            for right_file in asset_files[left_index + 1:]:
                if not is_potential_duplicate_name(left_file.stem, right_file.stem):
                    continue
                issues.append({
                    "type": "疑似重复命名",
                    "severity": "low",
                    "message": (
                        f"{asset_dir.relative_to(vault_path)} 下存在疑似重复文件："
                        f"{left_file.name} / {right_file.name}"
                    ),
                    "fix": "人工确认是否合并为同一资产，避免重复沉淀",
                })

    return issues


def check_stale_content(vault_path: Path) -> list:
    """检查超过 90 天未更新的汇总文件"""
    issues = []
    now = datetime.now()
    stale_threshold = timedelta(days=90)

    patterns_dir = vault_path / "patterns"
    if not patterns_dir.exists():
        return issues

    for md_file in patterns_dir.rglob("*.md"):
        if md_file.name.startswith("_"):
            continue
        mtime = datetime.fromtimestamp(md_file.stat().st_mtime)
        if now - mtime > stale_threshold:
            days_old = (now - mtime).days
            issues.append({
                "type": "陈旧内容",
                "severity": "low",
                "message": f"{md_file.relative_to(vault_path)} 已 {days_old} 天未更新",
                "fix": "检查是否需要更新或归档",
            })

    return issues


def generate_report(all_issues: list) -> str:
    """生成体检报告"""
    lines = [
        "# 资产库体检报告",
        "",
        f"> 检查时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
    ]

    if not all_issues:
        lines.append("✅ **资产库状态健康，无异常**")
        return "\n".join(lines)

    high = [i for i in all_issues if i["severity"] == "high"]
    medium = [i for i in all_issues if i["severity"] == "medium"]
    low = [i for i in all_issues if i["severity"] == "low"]

    lines.append(f"共发现 **{len(all_issues)}** 个问题（🔴 严重 {len(high)} | 🟡 中等 {len(medium)} | 🟢 轻微 {len(low)}）")
    lines.append("")

    if high:
        lines.append("## 🔴 严重问题")
        lines.append("")
        for issue in high:
            lines.append(f"- **{issue['type']}**：{issue['message']}")
            lines.append(f"  - 修复建议：{issue['fix']}")
        lines.append("")

    if medium:
        lines.append("## 🟡 中等问题")
        lines.append("")
        for issue in medium:
            lines.append(f"- **{issue['type']}**：{issue['message']}")
            lines.append(f"  - 修复建议：{issue['fix']}")
        lines.append("")

    if low:
        lines.append("## 🟢 轻微问题")
        lines.append("")
        for issue in low:
            lines.append(f"- **{issue['type']}**：{issue['message']}")
            lines.append(f"  - 修复建议：{issue['fix']}")
        lines.append("")

    return "\n".join(lines)


def main():
    vault_path = find_vault_path()
    print(f"资产库路径：{vault_path}")
    print("正在检查...")
    print()

    all_issues = []
    all_issues.extend(check_index_consistency(vault_path))
    all_issues.extend(check_summary_consistency(vault_path))
    all_issues.extend(check_duplicate_asset_names(vault_path))
    all_issues.extend(check_missing_files(vault_path))
    all_issues.extend(check_status_anomalies(vault_path))
    all_issues.extend(check_stale_content(vault_path))

    report = generate_report(all_issues)
    print(report)

    report_path = vault_path / "_index" / "health_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    print(f"\n报告已保存到：{report_path}")


if __name__ == "__main__":
    main()
