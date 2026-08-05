#!/usr/bin/env python3
"""SkillHub Daily v6.2 - 每日抓取 SkillHub Top100+7分类，计算收藏率/潜力分，输出结构化数据。

v6.2 升级：
- 增强 find_python 版本检查（要求 ≥ 3.10）
- 优化 User-Agent 为 SkillHub-Daily/6.2
- 主入口添加 Python 版本检查与友好错误提示

设计原则：
- 脚本只做数据采集+指标计算，不做个性化（个性化由 Agent 层基于用户记忆完成）
- 输出丰富的结构化 JSON，让 Agent 可以按类别、指标灵活筛选
- HTML 报告仅展示全站数据，不包含用户个性化
- --slim 模式裁剪冗余字段，保留完整覆盖（240个Skill不减少）

核心指标：
1. 收藏率 = stars/downloads — 判断 Skill 质量的核心指标
2. 安装转化率 = installs/downloads — 下载后真正安装的比例
3. 综合潜力分 = 收藏率(40%) + 安装转化率(30%) + 活跃安装率(20%) + 星标量级(10%)
4. 被埋没的金子 — 高收藏率但下载排名不在前20的 Skill

数据源：SkillHub (https://skillhub.cn) - 腾讯生态 AI 技能聚合站
API 基地址：https://api.skillhub.cn
核心接口：GET /api/skills?page=N&pageSize=50&sortBy=downloads&order=desc

多平台适配：WorkBuddy / qclaw / OpenClaw / Hermes Agent / 纯脚本
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import urllib.request
import urllib.parse
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any


# ── 数据源配置 ──────────────────────────────────────────────
API_BASE = "https://api.skillhub.cn"
SKILLS_ENDPOINT = "/api/skills"
DETAIL_ENDPOINT = "/api/v1/skills"
SOURCE_URL = "https://skillhub.cn/skills?sort=downloads"

PAGE_SIZE = 50
PAGES_REQUESTED = 2  # Top100
DEFAULT_SORT = "downloads"
DEFAULT_ORDER = "desc"
CATEGORY_PAGE_SIZE = 20
CATEGORIES_ENDPOINT = "/api/v1/categories"

# 类别中文名映射
CATEGORY_NAMES: dict[str, str] = {
    "ai-intelligence": "AI 智能",
    "developer-tools": "开发工具",
    "productivity": "效率提升",
    "data-analysis": "数据分析",
    "content-creation": "内容创作",
    "security-compliance": "安全合规",
    "communication-collaboration": "通讯协作",
}

# ── 跨平台工具检测 ──────────────────────────────────────────

MIN_PYTHON = (3, 10)


def find_python() -> str | None:
    """检测可用的 Python 解释器（要求 ≥ 3.10）。"""
    version = sys.version_info
    if version >= MIN_PYTHON:
        return sys.executable or "python"

    # 当前解释器版本过低，尝试查找其他 Python
    for cmd in ["python3", "python3.12", "python3.11", "python3.10", "python"]:
        path = shutil.which(cmd)
        if not path:
            continue
        # 解析版本号
        try:
            result = subprocess.run(
                [path, "--version"], capture_output=True, text=True, timeout=5
            )
            output = (result.stdout + result.stderr).strip()
            # 解析 "Python 3.11.x" 格式
            parts = output.split()
            if len(parts) >= 2 and parts[0] == "Python":
                ver_parts = parts[1].split(".")
                major = int(ver_parts[0])
                minor = int(ver_parts[1]) if len(ver_parts) > 1 else 0
                if (major, minor) >= MIN_PYTHON:
                    return path
        except (subprocess.TimeoutExpired, ValueError, IndexError):
            continue

    return None


def find_node() -> str | None:
    """检测可用的 Node.js 解释器。"""
    # 1. 系统PATH
    node_path = shutil.which("node")
    if node_path:
        return node_path
    # 2. WorkBuddy 内置
    if platform.system() == "Windows":
        wb_node = Path(os.environ.get("USERPROFILE", "")) / ".workbuddy" / "binaries" / "node" / "versions"
        if wb_node.exists():
            versions = sorted(wb_node.iterdir(), reverse=True)
            for v in versions:
                candidate = v / "node.exe"
                if candidate.exists():
                    return str(candidate)
    return None


def get_skill_dir() -> Path:
    """获取技能安装目录（跨平台）。"""
    # 1. 环境变量
    env_dir = os.environ.get("SKILLHUB_DAILY_DIR")
    if env_dir:
        return Path(env_dir)
    # 2. 脚本所在目录的上一级
    script_dir = Path(__file__).resolve().parent
    skill_dir = script_dir.parent
    if (skill_dir / "SKILL.md").exists():
        return skill_dir
    # 3. 当前工作目录
    return Path.cwd()


# ── 时间工具 ────────────────────────────────────────────────

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def number(value: Any) -> int | None:
    if value is None:
        return None
    try:
        if isinstance(value, bool):
            return int(value)
        return int(float(value))
    except (TypeError, ValueError):
        return None


def get_json(url: str, timeout: int = 20) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={
        "User-Agent": "SkillHub-Daily/6.2",
        "Accept": "application/json",
        "Referer": "https://skillhub.cn/",
        "Origin": "https://skillhub.cn",
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ── 抓取逻辑 ────────────────────────────────────────────────

@dataclass
class FetchResult:
    rows: list[dict[str, Any]]
    total_available: int
    pages_succeeded: int
    limitations: list[str]


def fetch_top_skills() -> FetchResult:
    limitations: list[str] = []
    all_skills: list[dict[str, Any]] = []
    total_available = 0
    pages_succeeded = 0

    for page_no in range(1, PAGES_REQUESTED + 1):
        params = urllib.parse.urlencode({
            "page": page_no,
            "pageSize": PAGE_SIZE,
            "sortBy": DEFAULT_SORT,
            "order": DEFAULT_ORDER,
        })
        url = f"{API_BASE}{SKILLS_ENDPOINT}?{params}"
        try:
            data = get_json(url)
        except Exception as exc:
            limitations.append(f"分页失败：第 {page_no} 页请求失败：{exc!r}")
            break
        if data.get("code") != 0:
            limitations.append(f"分页失败：第 {page_no} 页 code={data.get('code')}")
            break
        skills = data.get("data", {}).get("skills", [])
        total_available = data.get("data", {}).get("total", 0)
        if not isinstance(skills, list):
            limitations.append(f"接口字段变化：第 {page_no} 页 data.skills 不是 list")
            break
        all_skills.extend(skills)
        pages_succeeded += 1

    if len(all_skills) < 100:
        limitations.append(f"Top100 不完整：本次只得到 {len(all_skills)} 条")

    return FetchResult(
        rows=all_skills[:100],
        total_available=total_available,
        pages_succeeded=pages_succeeded,
        limitations=limitations,
    )


def fetch_skill_detail(slug: str) -> dict[str, Any] | None:
    """获取单个 Skill 的详情数据。"""
    try:
        url = f"{API_BASE}{DETAIL_ENDPOINT}/{urllib.parse.quote(slug)}"
        data = get_json(url)
        if data.get("skill"):
            return data
    except Exception:
        pass
    return None


def fetch_categories() -> list[dict[str, Any]]:
    """获取 SkillHub 的所有分类列表。"""
    try:
        data = get_json(f"{API_BASE}{CATEGORIES_ENDPOINT}")
        items = data.get("items", [])
        return [item for item in items if item.get("active", False)]
    except Exception:
        # 降级：使用硬编码分类
        return [
            {"key": k, "name": v, "nameEn": k, "sortOrder": i * 10, "active": True}
            for i, (k, v) in enumerate(CATEGORY_NAMES.items())
        ]


def fetch_category_skills(categories: list[dict[str, Any]]) -> dict[str, Any]:
    """按分类抓取每个分类的 Top20 Skill。"""
    result: dict[str, Any] = {}
    total_fetched = 0
    limitations: list[str] = []

    for cat in categories:
        cat_key = cat.get("key", "")
        cat_name = cat.get("name", cat_key)
        if not cat_key:
            continue

        params = urllib.parse.urlencode({
            "page": 1,
            "pageSize": CATEGORY_PAGE_SIZE,
            "category": cat_key,
            "sortBy": DEFAULT_SORT,
            "order": DEFAULT_ORDER,
        })
        url = f"{API_BASE}{SKILLS_ENDPOINT}?{params}"
        try:
            data = get_json(url)
        except Exception as exc:
            limitations.append(f"分类 {cat_name} 请求失败：{exc!r}")
            result[cat_key] = {"skills": [], "total": 0, "error": str(exc)}
            continue

        if data.get("code") != 0:
            limitations.append(f"分类 {cat_name} code={data.get('code')}")
            result[cat_key] = {"skills": [], "total": 0, "error": f"code={data.get('code')}"}
            continue

        skills_raw = data.get("data", {}).get("skills", [])
        total = data.get("data", {}).get("total", 0)
        cat_items = [normalize_item(row, rank) for rank, row in enumerate(skills_raw, 1)]
        compute_potential_scores(cat_items)

        result[cat_key] = {
            "category_zh": cat_name,
            "category_en": cat.get("nameEn", cat_key),
            "total_in_category": total,
            "fetched": len(cat_items),
            "skills": cat_items,
        }
        total_fetched += len(cat_items)

    result["_meta"] = {
        "categories_scanned": len(categories),
        "total_skills_fetched": total_fetched,
        "limitations": limitations,
    }
    return result


# ── 标准化 + 衍生指标 ──────────────────────────────────────

def normalize_item(raw: dict[str, Any], rank: int) -> dict[str, Any]:
    slug = raw.get("slug") or ""
    name = raw.get("name") or slug or "Unknown"
    author = raw.get("ownerName") or "Unknown"
    compare_key = slug or f"{author}/{name}".lower()
    downloads = number(raw.get("downloads"))
    installs = number(raw.get("installs"))
    stars = number(raw.get("stars"))

    star_rate = (stars / downloads * 100) if downloads and downloads > 0 and stars else 0.0
    install_rate = (installs / downloads * 100) if downloads and downloads > 0 and installs else 0.0
    active_rate = (stars / installs * 100) if installs and installs > 0 and stars else 0.0

    return {
        "rank": rank,
        "name": name,
        "author": author,
        "slug": slug,
        "source": raw.get("source", ""),
        "category": raw.get("category", ""),
        "category_zh": CATEGORY_NAMES.get(raw.get("category", ""), raw.get("category", "")),
        "description_zh": raw.get("description_zh") or raw.get("description") or "",
        "version": raw.get("version"),
        "downloads": downloads,
        "installs": installs,
        "stars": stars,
        "score": number(raw.get("score")),
        "requires_api_key": (raw.get("labels") or {}).get("requires_api_key"),
        "homepage": raw.get("homepage", ""),
        "compare_key": compare_key,
        "star_rate": round(star_rate, 4),
        "install_rate": round(install_rate, 2),
        "active_rate": round(active_rate, 4),
        "prev_rank": None,
        "download_delta": None,
        "install_delta": None,
        "star_delta": None,
        "rank_change": None,
        "star_rate_delta": None,
    }


def compute_potential_scores(items: list[dict[str, Any]]) -> None:
    """计算综合潜力分并写入每个 item。"""
    if not items:
        return
    max_sr = max(item["star_rate"] for item in items) or 1
    max_ir = max(item["install_rate"] for item in items) or 1
    max_ar = max(item["active_rate"] for item in items) or 1

    for item in items:
        sr_norm = item["star_rate"] / max_sr if max_sr > 0 else 0
        ir_norm = item["install_rate"] / max_ir if max_ir > 0 else 0
        ar_norm = item["active_rate"] / max_ar if max_ar > 0 else 0
        stars = item["stars"] or 0
        star_bonus = 1.0 if stars > 500 else (0.6 if stars > 200 else 0.2)
        item["potential_score"] = round(sr_norm * 40 + ir_norm * 30 + ar_norm * 20 + star_bonus * 10, 2)


# ── 历史对比 ────────────────────────────────────────────────

def nearest_previous_snapshot(snapshot_dir: Path, snapshot_date: str) -> Path | None:
    candidates = sorted(path for path in snapshot_dir.glob("*.json") if path.stem < snapshot_date)
    return candidates[-1] if candidates else None


def apply_comparison(
    items: list[dict[str, Any]],
    prev_path: Path | None,
    snapshot_date: str,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    limitations: list[str] = []
    dropped: list[dict[str, Any]] = []

    if not prev_path:
        limitations.append("缺少历史切片，本次不做严格日环比。")
        return {
            "previous_snapshot": None,
            "strict_daily": False,
            "note": "缺少历史切片，本次不做严格日环比。",
        }, dropped, limitations

    prev = read_json(prev_path)
    prev_items = prev.get("items") or []
    prev_by_key = {item.get("compare_key"): item for item in prev_items if item.get("compare_key")}
    current_keys = {item["compare_key"] for item in items}

    for item in items:
        old = prev_by_key.get(item["compare_key"])
        if not old:
            continue
        item["prev_rank"] = old.get("rank")
        if item.get("downloads") is not None and old.get("downloads") is not None:
            item["download_delta"] = item["downloads"] - old["downloads"]
        if item.get("installs") is not None and old.get("installs") is not None:
            item["install_delta"] = item["installs"] - old["installs"]
        if item.get("stars") is not None and old.get("stars") is not None:
            item["star_delta"] = item["stars"] - old["stars"]
        if item["prev_rank"] is not None:
            item["rank_change"] = item["prev_rank"] - item["rank"]
        if old.get("star_rate") is not None and item["star_rate"] is not None:
            item["star_rate_delta"] = round(item["star_rate"] - old["star_rate"], 4)

    for key, old in prev_by_key.items():
        if key not in current_keys:
            dropped.append(old)

    previous_day = (date.fromisoformat(snapshot_date) - timedelta(days=1)).isoformat()
    strict_daily = prev.get("snapshot_date") == previous_day
    if strict_daily:
        note = f"与前一日快照 {prev_path.name} 对比。"
    else:
        note = f"与最近历史快照 {prev_path.name} 对比，不是严格日环比。"
        limitations.append("缺少前一日快照，差分不是严格 24 小时日环比。")

    return {
        "previous_snapshot": str(prev_path),
        "strict_daily": strict_daily,
        "note": note,
    }, dropped, limitations


# ── 排序辅助 ────────────────────────────────────────────────

def top_by(items: list[dict[str, Any]], field: str, limit: int) -> list[dict[str, Any]]:
    valid = [item for item in items if isinstance(item.get(field), int)]
    return sorted(valid, key=lambda item: (-item[field], item["rank"]))[:limit]


# ── 潜力 Skill 筛选 ───────────────────────────────────────

def potential_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """潜力筛选规则（收藏率加权，去重合并）。"""
    has_history = any(item.get("prev_rank") is not None for item in items)
    out_by_key: dict[str, dict[str, Any]] = {}

    def _add(item: dict[str, Any], reason: str) -> None:
        key = item["compare_key"]
        if key not in out_by_key:
            out_by_key[key] = dict(item)
            out_by_key[key]["potential_reasons"] = []
        if reason not in out_by_key[key]["potential_reasons"]:
            out_by_key[key]["potential_reasons"].append(reason)

    # 规则1：收藏率 Top10
    by_sr = sorted(items, key=lambda x: x.get("star_rate", 0), reverse=True)[:10]
    for item in by_sr:
        if item["star_rate"] > 0:
            _add(item, f"收藏率 {item['star_rate']:.2f}%（Top10）")

    # 规则2：被埋没的金子
    buried = sorted(
        [s for s in items if s["rank"] > 20 and s["star_rate"] > 0],
        key=lambda x: x["star_rate"], reverse=True
    )[:5]
    for item in buried:
        _add(item, f"被埋没的金子：收藏率 {item['star_rate']:.2f}% 但排名仅 #{item['rank']}")

    # 规则3-7：需要历史数据
    if has_history:
        download_top20 = {item["compare_key"] for item in top_by(items, "download_delta", 20)}
        star_top30 = {item["compare_key"] for item in top_by(items, "star_delta", 30)}
        install_top15 = {item["compare_key"] for item in top_by(items, "install_delta", 15)}

        for item in items:
            if item["compare_key"] in out_by_key:
                continue
            reasons: list[str] = []
            if item.get("prev_rank") is None:
                reasons.append("新进 Top100")
            if item["compare_key"] in download_top20 and item["compare_key"] in star_top30:
                reasons.append("下载增量 Top20 且星标增量 Top30")
            if item["compare_key"] in install_top15:
                reasons.append("安装增量 Top15")
            if isinstance(item.get("rank_change"), int) and item["rank_change"] >= 8:
                reasons.append("排名上升 >= 8 位")
            if item.get("star_rate_delta") and item["star_rate_delta"] > 0:
                reasons.append(f"收藏率上升 {item['star_rate_delta']:.2f}%")
            for r in reasons:
                _add(item, r)

    out = list(out_by_key.values())
    out.sort(key=lambda x: x.get("potential_score", 0), reverse=True)
    return out[:15]


# ── 类别分析 ────────────────────────────────────────────────

def build_category_analysis(items: list[dict[str, Any]], category_skills: dict[str, Any] | None = None) -> dict[str, Any]:
    """按类别分组，输出每个类别的 Top Skill、平均收藏率等。"""
    cat_map: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        cat = item.get("category") or "unknown"
        if cat not in cat_map:
            cat_map[cat] = []
        cat_map[cat].append(item)

    result: dict[str, Any] = {}
    for cat, cat_items in cat_map.items():
        by_star_rate = sorted(cat_items, key=lambda x: x.get("star_rate", 0), reverse=True)
        by_potential = sorted(cat_items, key=lambda x: x.get("potential_score", 0), reverse=True)

        total_downloads = sum(s.get("downloads") or 0 for s in cat_items)
        total_stars = sum(s.get("stars") or 0 for s in cat_items)
        total_installs = sum(s.get("installs") or 0 for s in cat_items)
        avg_star_rate = sum(s.get("star_rate", 0) for s in cat_items) / len(cat_items)

        entry: dict[str, Any] = {
            "category_zh": CATEGORY_NAMES.get(cat, cat),
            "count": len(cat_items),
            "total_downloads": total_downloads,
            "total_stars": total_stars,
            "total_installs": total_installs,
            "avg_star_rate": round(avg_star_rate, 4),
            "top_by_star_rate": [
                {
                    "rank": s["rank"], "name": s["name"], "slug": s["slug"],
                    "author": s["author"], "star_rate": s["star_rate"],
                    "potential_score": s.get("potential_score", 0),
                    "downloads": s["downloads"], "stars": s["stars"],
                    "description_zh": s.get("description_zh", "")[:100],
                }
                for s in by_star_rate[:5]
            ],
            "top_by_potential": [
                {
                    "rank": s["rank"], "name": s["name"], "slug": s["slug"],
                    "author": s["author"], "star_rate": s["star_rate"],
                    "potential_score": s.get("potential_score", 0),
                    "downloads": s["downloads"], "stars": s["stars"],
                    "description_zh": s.get("description_zh", "")[:100],
                }
                for s in by_potential[:5]
            ],
        }

        # 合并分类扫描数据
        if category_skills and cat in category_skills:
            cat_scan = category_skills[cat]
            cat_scan_skills = cat_scan.get("skills", [])
            cat_by_star_rate = sorted(cat_scan_skills, key=lambda x: x.get("star_rate", 0), reverse=True)[:5]
            entry["category_top"] = [
                {
                    "name": s["name"], "slug": s["slug"], "author": s["author"],
                    "star_rate": s["star_rate"], "potential_score": s.get("potential_score", 0),
                    "downloads": s["downloads"], "stars": s["stars"],
                    "description_zh": s.get("description_zh", "")[:200],
                }
                for s in cat_by_star_rate
            ]
            entry["total_in_category"] = cat_scan.get("total_in_category", 0)
            top100_slugs = {item["slug"] for item in items}
            entry["hidden_gems_in_category"] = [
                {
                    "name": s["name"], "slug": s["slug"], "author": s["author"],
                    "star_rate": s["star_rate"], "potential_score": s.get("potential_score", 0),
                    "downloads": s["downloads"], "stars": s["stars"],
                    "description_zh": s.get("description_zh", "")[:200],
                }
                for s in cat_by_star_rate if s["slug"] not in top100_slugs
            ]

        result[cat] = entry
    return result


# ── 格式化辅助 ──────────────────────────────────────────────

def fmt_delta(value: Any) -> str:
    if value is None:
        return "n/a"
    return f"+{value}" if value > 0 else str(value)


def fmt_number(value: Any) -> str:
    if value is None:
        return "n/a"
    v = int(value)
    if v >= 10000:
        return f"{v / 10000:.1f}万"
    return str(v)


# ── Markdown 日报生成 ───────────────────────────────────────

def render_markdown_report(snapshot: dict[str, Any], dropped: list[dict[str, Any]], potentials: list[dict[str, Any]], category_analysis: dict[str, Any]) -> str:
    items = snapshot["items"]
    lines = [
        f"# SkillHub每日推荐 {snapshot['snapshot_date']}",
        "",
        "## 抓取状态", "",
        f"- 抓取时间：`{snapshot['fetched_at']}`",
        f"- 数据源：SkillHub（腾讯生态 AI 技能聚合站）",
        f"- 本次条目：{len(items)}（库中共 {snapshot['source']['total_available']} 个 Skill）",
        f"- 对比口径：{snapshot['comparison_basis']['note']}",
        "",
        "## 限制说明", "",
    ]
    if snapshot.get("limitations"):
        lines.extend(f"- {item}" for item in snapshot["limitations"])
    else:
        lines.append("- 暂无已知限制。")

    lines += ["", "## 💎 潜力 Skill 排行（收藏率加权）", ""]
    for s in potentials[:10]:
        reasons = "；".join(s.get("potential_reasons", []))
        lines += [
            f"### #{s['rank']} {s['name']}（潜力分 {s.get('potential_score', 0):.0f}）",
            f"- 作者：{s['author']} | 分类：{s.get('category_zh', s.get('category', 'n/a'))}",
            f"- 下载 {fmt_number(s.get('downloads'))} | 安装 {fmt_number(s.get('installs'))} | 星标 {fmt_number(s.get('stars'))}",
            f"- **收藏率 {s.get('star_rate', 0):.2f}%** | 安装转化率 {s.get('install_rate', 0):.1f}%",
            f"- 命中原因：{reasons}",
            f"- 链接：https://skillhub.cn/skills/{s.get('slug', '')}",
            "",
        ]

    buried = sorted([s for s in items if s["rank"] > 20 and s["star_rate"] > 0], key=lambda x: x["star_rate"], reverse=True)[:5]
    lines += ["", "## 🔥 被埋没的金子", ""]
    for s in buried:
        lines.append(f"- 榜#{s['rank']} **{s['name']}**（{s['author']}）| 收藏率 {s['star_rate']:.2f}% | {fmt_number(s.get('downloads'))}下载")

    lines += ["", "## 🗂️ 按类别深挖", ""]
    for cat, cat_data in sorted(category_analysis.items(), key=lambda x: -x[1]["count"]):
        total_in_cat = cat_data.get("total_in_category", cat_data["count"])
        lines.append(f"### {cat_data['category_zh']}（Top100内 {cat_data['count']} 个，全站 {total_in_cat} 个，平均收藏率 {cat_data['avg_star_rate']:.2f}%）")
        for s in cat_data["top_by_star_rate"][:3]:
            lines.append(f"- #{s['rank']} **{s['name']}**（{s['author']}）| 收藏率 {s['star_rate']:.2f}% | {fmt_number(s['downloads'])}下载")
        hidden_gems = cat_data.get("hidden_gems_in_category", [])
        if hidden_gems:
            lines.append(f"  - 🔍 分类内隐藏好货（不在全站Top100）：")
            for gem in hidden_gems[:3]:
                lines.append(f"    - **{gem['name']}**（{gem['author']}）| 收藏率 {gem['star_rate']:.2f}% | {fmt_number(gem['downloads'])}下载 | https://skillhub.cn/skills/{gem['slug']}")
        lines.append("")

    lines += ["", "## 🏆 下载榜 Top10", ""]
    for s in items[:10]:
        lines.append(f"- #{s['rank']} **{s['name']}**（{s['author']}）| 下载 {fmt_number(s.get('downloads'))} | 收藏率 {s.get('star_rate', 0):.2f}%")

    return "\n".join(lines) + "\n"


# ── 日期索引更新 ────────────────────────────────────────────

def update_dates(data_dir: Path, snapshot_date: str) -> None:
    dates_path = data_dir / "dates.json"
    if dates_path.exists():
        payload = read_json(dates_path)
        dates = payload.get("dates") or []
    else:
        dates = []
    if snapshot_date not in dates:
        dates.append(snapshot_date)
    dates = sorted(set(dates), reverse=True)
    write_json(dates_path, {"latest": dates[0], "dates": dates})


# ── 构建快照 ────────────────────────────────────────────────

def build_snapshot(snapshot_date: str, data_dir: Path) -> dict[str, Any]:
    result = fetch_top_skills()
    items = [normalize_item(row, rank) for rank, row in enumerate(result.rows, 1)]
    comparison, dropped, comparison_limits = apply_comparison(
        items,
        nearest_previous_snapshot(data_dir / "snapshots", snapshot_date),
        snapshot_date,
    )
    limitations = [*result.limitations, *comparison_limits]

    compute_potential_scores(items)

    snapshot = {
        "snapshot_date": snapshot_date,
        "fetched_at": utc_now(),
        "source": {
            "url": SOURCE_URL,
            "api_base": API_BASE,
            "endpoint": SKILLS_ENDPOINT,
            "sort": DEFAULT_SORT,
            "order": DEFAULT_ORDER,
            "page_size": PAGE_SIZE,
            "pages_requested": PAGES_REQUESTED,
            "pages_succeeded": result.pages_succeeded,
            "total_available": result.total_available,
        },
        "comparison_basis": {
            "primary_ranking": f"GET {API_BASE}{SKILLS_ENDPOINT}?sortBy={DEFAULT_SORT}&order={DEFAULT_ORDER}&pageSize={PAGE_SIZE}, first {PAGES_REQUESTED} pages.",
            "compare_key": "slug, fallback owner/name",
            **comparison,
        },
        "limitations": limitations,
        "dropped_items": dropped,
        "items": items,
    }
    return snapshot


# ── 主入口 ──────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="SkillHub Daily v6.2 - 每日抓取 SkillHub 下载榜 Top100 + 7分类扫描")
    parser.add_argument("--date", default=date.today().isoformat(), help="Snapshot date, format: YYYY-MM-DD")
    parser.add_argument("--data-dir", default=None, help="Output data directory (default: auto-detect)")
    parser.add_argument("--no-html", action="store_true", default=True, help="Skip HTML report (default: skip)")
    parser.add_argument("--html", action="store_true", help="Generate HTML report")
    parser.add_argument("--fetch-details", action="store_true", help="Fetch detail API for top potential skills")
    parser.add_argument("--slim", action="store_true", help="Slim mode: strip unnecessary fields to reduce token usage by ~32 percent")
    args = parser.parse_args()

    # 自动检测数据目录
    if args.data_dir:
        data_dir = Path(args.data_dir)
    else:
        skill_dir = get_skill_dir()
        data_dir = skill_dir / "data"

    # 0. Python 版本检查
    py_path = find_python()
    if py_path is None:
        print(
            "❌ 错误：未找到满足要求的 Python 解释器。\n"
            "本技能需要 Python 3.10 或更高版本。\n"
            "请前往 https://www.python.org/downloads/ 下载安装。",
            file=sys.stderr,
        )
        return 2

    # 1. 构建快照
    print("Step 1: Fetching Top100 from SkillHub API...")
    snapshot = build_snapshot(args.date, data_dir)
    items = snapshot["items"]

    # 2. 分类扫描
    print("Step 2: Fetching categories and scanning each category Top20...")
    categories = fetch_categories()
    category_skills = fetch_category_skills(categories)
    cat_meta = category_skills.get("_meta", {})
    print(f"  Scanned {cat_meta.get('categories_scanned', 0)} categories, "
          f"fetched {cat_meta.get('total_skills_fetched', 0)} skills total")

    # 3. 计算潜力 Skill
    potentials = potential_items(items)
    print(f"Step 3: {len(potentials)} potential skills identified")

    # 4. 类别分析
    category_analysis = build_category_analysis(items, category_skills)
    print(f"Step 4: {len(category_analysis)} categories analyzed")

    # 5. 获取详情数据（可选）
    if args.fetch_details and potentials:
        print("Step 5: Fetching detail data for potential skills...")
        for p in potentials[:5]:
            slug = p.get("slug", "")
            if slug:
                fetch_skill_detail(slug)

    # 6. 保存快照
    snapshot_path = data_dir / "snapshots" / f"{args.date}.json"
    write_json(snapshot_path, snapshot)
    write_json(data_dir / "latest.json", snapshot)

    # 7. 保存潜力分析结果
    potential_data = {
        "date": args.date,
        "total_skills": len(items),
        "scan_summary": {
            "top100_fetched": len(items),
            "categories_scanned": cat_meta.get("categories_scanned", 0),
            "category_skills_fetched": cat_meta.get("total_skills_fetched", 0),
            "scan_coverage": "Top100全站 + 7大分类各Top20",
        },
        "potential_skills": [
            {
                "rank": p["rank"], "name": p["name"], "slug": p["slug"],
                "author": p["author"], "category": p["category"],
                "category_zh": p.get("category_zh", ""),
                "star_rate": p["star_rate"], "install_rate": p["install_rate"],
                "potential_score": p["potential_score"],
                "downloads": p["downloads"], "installs": p["installs"], "stars": p["stars"],
                "description_zh": p.get("description_zh", "")[:100],
                "reasons": p.get("potential_reasons", []),
            }
            for p in potentials
        ],
        "buried_gold": [
            {
                "rank": s["rank"], "name": s["name"], "slug": s["slug"],
                "author": s["author"], "category": s["category"],
                "category_zh": s.get("category_zh", ""),
                "star_rate": s["star_rate"], "downloads": s["downloads"], "stars": s["stars"],
                "description_zh": s.get("description_zh", "")[:100],
            }
            for s in sorted(
                [s for s in items if s["rank"] > 20 and s["star_rate"] > 0],
                key=lambda x: x["star_rate"], reverse=True
            )[:5]
        ],
        "category_analysis": category_analysis,
        "category_skills": {k: v for k, v in category_skills.items() if k != "_meta"},
    }
    write_json(data_dir / "potential.json", potential_data)

    # 8. Slim 模式
    if args.slim:
        SLIM_FIELDS = {"rank", "name", "slug", "category", "category_zh",
                       "star_rate", "install_rate", "potential_score",
                       "downloads", "installs", "stars", "description_zh", "reasons"}
        slim_cs = {}
        for cat, data in potential_data.get("category_skills", {}).items():
            slim_skills = [{k: v for k, v in s.items() if k in SLIM_FIELDS}
                          for s in data.get("skills", [])]
            slim_cs[cat] = {
                "category_zh": data.get("category_zh", ""),
                "category_en": data.get("category_en", ""),
                "total_in_category": data.get("total_in_category", 0),
                "fetched": data.get("fetched", 0),
                "skills": slim_skills,
            }
        potential_data["category_skills"] = slim_cs
        write_json(data_dir / "potential_slim.json", potential_data)

    # 9. 生成 Markdown 报告
    report_path = data_dir / "reports" / f"{args.date}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        render_markdown_report(snapshot, snapshot.get("dropped_items", []), potentials, category_analysis),
        encoding="utf-8",
    )

    update_dates(data_dir, args.date)

    result = {
        "snapshot": str(snapshot_path),
        "report": str(report_path),
        "items": len(items),
        "potential_skills": len(potentials),
        "categories": len(category_analysis),
        "slim": args.slim,
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
