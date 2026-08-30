#!/usr/bin/env python3
"""知识管家 · 昨日数据收集脚本

严格聚焦数据层：扫描知识库文件系统、计算当日 delta、判档位、
输出结构化 JSON 到 stdout 供 AI 消费。**不**生成任何文案。

一个子命令：
  collect  扫描知识库，输出当日 delta 的 JSON

使用示例：
  # 默认扫 ~/Desktop/知识管家/（2026-04-24 架构：桌面外部路径，绕开悟空 deliver bug）
  python3 daily_digest.py collect --date 2026-04-24

  # 自定义 kb 根（如果用户把知识管家放在别处）：
  python3 daily_digest.py collect --date 2026-04-24 \\
      --kb-root ~/Documents/我的知识管家/
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------- 常量 ----------

SCRIPT_VERSION = "v1.0"

# 档位阈值
SCALE_EMPTY = "空动"
SCALE_LIGHT = "轻量"
SCALE_MID = "中等"
SCALE_DEEP = "深度"

# 变化量权重
W_MATERIAL = 1.0
W_NEW_TOPIC = 2.0
W_TOUCHED_TOPIC = 0.5

# 目录结构（相对 kb-root）
DIR_RECORDINGS = Path("1-素材") / "录音"
DIR_SUMMARIES = Path("2-AI知识库") / "素材摘要"
DIR_TOPICS = Path("2-AI知识库") / "专题"
DIR_DIGESTS = Path("3-AI工作记录") / "日报"
PATH_ACTION_LOG = Path("3-AI工作记录") / "操作记录.md"

# 提取 [[专题名]] 链接；专题名内部不允许出现 ] 或 [ 或换行
WIKILINK_RE = re.compile(r"\[\[([^\[\]\n]+?)\]\]")

# frontmatter 分隔符
FM_BOUNDARY_RE = re.compile(r"^---\s*$")

# 行级 key: value（简单解析，不支持嵌套对象/多行值）
FM_LINE_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_\-]*)\s*:\s*(.*?)\s*$")

# 操作记录里的时间戳行（支持 ISO-8601 或 YYYY-MM-DD HH:MM）
ACTION_TS_RE = re.compile(
    r"(?P<ts>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2})?(?:[+\-]\d{2}:?\d{2}|Z)?)"
)
# 操作记录标题行格式：## [YYYY-MM-DD HH:MM] 动作类型 | 子类/备注
ACTION_HEADER_RE = re.compile(
    r"^\s*#{1,6}\s*\[(?P<ts>[^\]]+)\]\s*(?P<action>[^|｜\n]+?)(?:\s*[|｜]\s*(?P<sub>.+))?\s*$"
)
# 兼容 markdown list 形式：- [YYYY-MM-DD HH:MM] 动作 | 子类
ACTION_LIST_RE = re.compile(
    r"^\s*[-*]\s*\[(?P<ts>[^\]]+)\]\s*(?P<action>[^|｜\n]+?)(?:\s*[|｜]\s*(?P<sub>.+))?\s*$"
)


# ---------- frontmatter 解析 ----------


def parse_frontmatter(text: str) -> dict:
    """提取文件开头的 YAML-ish frontmatter，返回 {key: raw_string_value}。

    只支持最常见的形式：
        ---
        key: value
        ---
    遇到块级值（list 以 `-` 开头、多行字符串）一概按原字符串保留第一行，
    够用于我们关心的 fetched / created / source_material 这几个字段。
    失败返回空 dict。
    """
    if not text:
        return {}
    lines = text.splitlines()
    if not lines or not FM_BOUNDARY_RE.match(lines[0]):
        return {}
    out: dict = {}
    i = 1
    while i < len(lines):
        line = lines[i]
        if FM_BOUNDARY_RE.match(line):
            return out
        m = FM_LINE_RE.match(line)
        if m:
            key, val = m.group(1), m.group(2)
            # 去掉引号
            if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
                val = val[1:-1]
            out[key] = val
        i += 1
    # 没闭合 frontmatter
    return out


def extract_date(raw: str | None) -> str | None:
    """从 frontmatter 值里提取 YYYY-MM-DD（取前 10 位）。失败返回 None。"""
    if not raw:
        return None
    raw = raw.strip()
    if len(raw) < 10:
        return None
    candidate = raw[:10]
    try:
        datetime.strptime(candidate, "%Y-%m-%d")
        return candidate
    except ValueError:
        return None


def mtime_date(path: Path) -> str | None:
    try:
        ts = os.path.getmtime(path)
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
    except OSError:
        return None


def mtime_iso(path: Path) -> str | None:
    try:
        ts = os.path.getmtime(path)
        return datetime.fromtimestamp(ts).astimezone().isoformat()
    except OSError:
        return None


def resolve_iso(raw: str | None, fallback_path: Path) -> str | None:
    """frontmatter 里 raw 是 ISO-8601 就直接返；只有日期就补 00:00:00 本地时区；
    都没有就 fallback 到 mtime。"""
    if raw:
        raw = raw.strip().strip("'\"")
        # 已经有 T 或空格分隔的时间
        try:
            # 支持 'YYYY-MM-DD HH:MM' / 'YYYY-MM-DDTHH:MM:SS+08:00' 等
            norm = raw.replace(" ", "T")
            dt = datetime.fromisoformat(norm)
            if dt.tzinfo is None:
                dt = dt.astimezone()
            return dt.isoformat()
        except ValueError:
            pass
        # 只有日期
        try:
            d = datetime.strptime(raw[:10], "%Y-%m-%d")
            return d.astimezone().isoformat()
        except ValueError:
            pass
    return mtime_iso(fallback_path)


# ---------- 扫描器 ----------


def scan_new_materials(kb_root: Path, target_date: str) -> list[dict]:
    """列 1-素材/录音/*.md，按 frontmatter.fetched（fallback mtime）过滤当日。"""
    dir_path = kb_root / DIR_RECORDINGS
    if not dir_path.is_dir():
        return []

    results: list[dict] = []
    for md in sorted(dir_path.glob("*.md")):
        try:
            text = md.read_text(encoding="utf-8")
        except OSError as e:
            sys.stderr.write(f"[WARN] 读取失败 {md}: {e}\n")
            continue
        fm = parse_frontmatter(text)
        fetched_raw = fm.get("fetched")
        fetched_date = extract_date(fetched_raw) or mtime_date(md)
        if fetched_date != target_date:
            continue

        # duration 字段在 frontmatter 里通常是 "27.6min"；转成秒（整数）
        duration_seconds = 0
        dur_raw = fm.get("duration") or ""
        m = re.match(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*min", dur_raw)
        if m:
            try:
                duration_seconds = int(float(m.group(1)) * 60)
            except ValueError:
                duration_seconds = 0

        # 推断 title：frontmatter.title 优先，否则用文件名（去扩展）
        title = fm.get("title") or md.stem

        results.append({
            "title": title,
            "category": fm.get("category") or "其他",
            "path": str((DIR_RECORDINGS / md.name)),
            "duration_seconds": duration_seconds,
            "fetched_at": resolve_iso(fetched_raw, md),
            # 内部用：让 touched_topics 扫描时能对齐到 summaries
            "_stem": md.stem,
        })
    return results


def scan_new_topics(kb_root: Path, target_date: str) -> list[dict]:
    """列 2-AI知识库/专题/*.md，按 frontmatter.created（fallback mtime）过滤当日。"""
    dir_path = kb_root / DIR_TOPICS
    if not dir_path.is_dir():
        return []

    results: list[dict] = []
    for md in sorted(dir_path.glob("*.md")):
        try:
            text = md.read_text(encoding="utf-8")
        except OSError as e:
            sys.stderr.write(f"[WARN] 读取失败 {md}: {e}\n")
            continue
        fm = parse_frontmatter(text)
        created_raw = fm.get("created")
        created_date = extract_date(created_raw) or mtime_date(md)
        if created_date != target_date:
            continue
        results.append({
            "name": md.stem,
            "path": str((DIR_TOPICS / md.name)),
            "created_at": resolve_iso(created_raw, md),
        })
    return results


def _find_summary_for_material(kb_root: Path, material_stem: str) -> Path | None:
    """根据素材文件名匹配其素材摘要。约定：
    - 完全同名
    - 或素材摘要的 frontmatter.source_material 指向该素材文件
    优先同名。
    """
    summaries_dir = kb_root / DIR_SUMMARIES
    if not summaries_dir.is_dir():
        return None
    # 同名
    cand = summaries_dir / f"{material_stem}.md"
    if cand.is_file():
        return cand
    # 前缀匹配（素材叫 2026-04-21-xxx，摘要可能叫 2026-04-21-xxx-summary.md 等）
    for md in summaries_dir.glob("*.md"):
        if md.stem == material_stem:
            return md
        if material_stem in md.stem or md.stem in material_stem:
            return md
    return None


def extract_wikilinks(text: str) -> set[str]:
    """从 markdown 文本里抓所有 [[name]] 的 name（去空白、去可能的 |alias 别名）。"""
    names: set[str] = set()
    for m in WIKILINK_RE.finditer(text):
        raw = m.group(1).strip()
        if not raw:
            continue
        # [[target|alias]] 取 target
        target = raw.split("|", 1)[0].strip()
        # 去掉 #anchor
        target = target.split("#", 1)[0].strip()
        if target:
            names.add(target)
    return names


def scan_touched_topics(
    kb_root: Path,
    new_materials: list[dict],
    new_topics: list[dict],
) -> list[dict]:
    """对每个 new_material 文件，读它 + 它对应的素材摘要（若有），
    提取 [[专题]] 并统计触达次数，去重后返回。
    排除 new_topics（新专题不算 touched）。
    """
    if not new_materials:
        return []

    topics_dir = kb_root / DIR_TOPICS
    # 已存在的专题文件名集合——只有真正存在的专题才计入 touched
    existing_topics: set[str] = set()
    if topics_dir.is_dir():
        existing_topics = {p.stem for p in topics_dir.glob("*.md")}
    new_topic_names = {t["name"] for t in new_topics}

    # topic_name -> set(material_titles)
    touched: dict[str, set[str]] = {}

    for mat in new_materials:
        material_path = kb_root / mat["path"]
        title_display = mat["title"]
        texts_to_scan: list[str] = []
        try:
            texts_to_scan.append(material_path.read_text(encoding="utf-8"))
        except OSError:
            pass
        summary_path = _find_summary_for_material(kb_root, mat["_stem"])
        if summary_path:
            try:
                texts_to_scan.append(summary_path.read_text(encoding="utf-8"))
            except OSError:
                pass

        mentioned: set[str] = set()
        for text in texts_to_scan:
            mentioned |= extract_wikilinks(text)

        for name in mentioned:
            # 必须是已存在的专题、且不是今日新建的
            if name not in existing_topics:
                continue
            if name in new_topic_names:
                continue
            touched.setdefault(name, set()).add(title_display)

    out: list[dict] = []
    for name in sorted(touched.keys()):
        titles = sorted(touched[name])
        out.append({
            "name": name,
            "touched_by": titles,
            "count": len(titles),
        })
    return out


# ---------- 操作记录 delta ----------


def scan_action_log_delta(kb_root: Path, target_date: str) -> list[dict]:
    """读 3-AI工作记录/操作记录.md，抓当日的所有行。

    支持三种格式：
        ## [2026-04-24 10:42] 初始化 | 创建...
        - [2026-04-24T10:42:00+08:00] 投喂 | 听记
        任何包含 ISO-8601 时间戳 + 后续文字的行
    按 (action, sub_type) 聚合计数。
    """
    path = kb_root / PATH_ACTION_LOG
    if not path.is_file():
        return []

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        sys.stderr.write(f"[WARN] 读取操作记录失败: {e}\n")
        return []

    # (time, action, sub) 列表（保留所有命中行）
    entries: list[tuple[str, str, str]] = []
    for line in text.splitlines():
        m = ACTION_HEADER_RE.match(line) or ACTION_LIST_RE.match(line)
        if not m:
            continue
        ts_raw = m.group("ts").strip()
        date_part = extract_date(ts_raw)
        if date_part != target_date:
            continue
        iso_ts = _normalize_ts(ts_raw)
        action = (m.group("action") or "").strip()
        sub = (m.group("sub") or "").strip() if m.group("sub") else ""
        if not action:
            continue
        entries.append((iso_ts, action, sub))

    # 按 (action, sub) 聚合，保留每组最早时间
    bucket: dict[tuple[str, str], dict] = {}
    for ts, action, sub in entries:
        key = (action, sub)
        if key not in bucket:
            bucket[key] = {"time": ts, "action": action, "sub_type": sub, "count": 0}
        bucket[key]["count"] += 1
        # 保留最早的时间
        if ts < bucket[key]["time"]:
            bucket[key]["time"] = ts

    return sorted(bucket.values(), key=lambda x: x["time"])


def _normalize_ts(raw: str) -> str:
    """把 'YYYY-MM-DD HH:MM' 或 ISO-8601 统一成本地时区的 ISO-8601。"""
    try:
        norm = raw.replace(" ", "T")
        dt = datetime.fromisoformat(norm)
        if dt.tzinfo is None:
            dt = dt.astimezone()
        return dt.isoformat()
    except ValueError:
        return raw  # 原样返回


# ---------- 过去 7 天均值 ----------


def past_7d_avg_variance(kb_root: Path, target_date: str) -> float:
    """从 3-AI工作记录/日报/YYYY-MM-DD.md 读过去 7 天的 variance_score 求均值。"""
    dir_path = kb_root / DIR_DIGESTS
    if not dir_path.is_dir():
        return 0.0
    try:
        target_dt = datetime.strptime(target_date, "%Y-%m-%d")
    except ValueError:
        return 0.0

    scores: list[float] = []
    for md in dir_path.glob("*.md"):
        stem = md.stem  # YYYY-MM-DD
        try:
            d = datetime.strptime(stem, "%Y-%m-%d")
        except ValueError:
            continue
        delta_days = (target_dt - d).days
        if delta_days < 1 or delta_days > 7:
            continue
        try:
            fm = parse_frontmatter(md.read_text(encoding="utf-8"))
        except OSError:
            continue
        raw = fm.get("variance_score")
        if raw is None:
            continue
        try:
            scores.append(float(raw))
        except ValueError:
            continue

    if not scores:
        return 0.0
    return round(sum(scores) / len(scores), 2)


def is_first_run(kb_root: Path) -> bool:
    dir_path = kb_root / DIR_DIGESTS
    if not dir_path.is_dir():
        return True
    return not any(dir_path.glob("*.md"))


# ---------- 变化量 & 档位 ----------


def compute_variance(n_materials: int, n_new_topics: int, n_touched: int) -> float:
    score = (
        n_materials * W_MATERIAL
        + n_new_topics * W_NEW_TOPIC
        + n_touched * W_TOUCHED_TOPIC
    )
    return round(score, 2)


def classify_scale(score: float) -> str:
    if score == 0:
        return SCALE_EMPTY
    if score <= 3:
        return SCALE_LIGHT
    if score <= 10:
        return SCALE_MID
    return SCALE_DEEP


# ---------- CLI: collect ----------


def cmd_collect(args) -> int:
    # 3 层 fallback 解析 kb_root（和 SKILL.md 的 KB_ROOT 机制一致）：
    #   1. CLI --kb-root（最高优先）
    #   2. $KB_ROOT 环境变量（AI 在 Phase -1 会 export）
    #   3. 默认 $HOME/Desktop/知识管家/
    env_kb = os.environ.get("KB_ROOT")
    default_kb = Path.home() / "Desktop" / "知识管家"
    kb_root = Path(args.kb_root or env_kb or default_kb).expanduser().resolve()
    # 校验日期格式
    try:
        datetime.strptime(args.date, "%Y-%m-%d")
    except ValueError:
        print(f"[ERROR] --date 必须是 YYYY-MM-DD 格式，收到 {args.date!r}", file=sys.stderr)
        return 1

    target_date = args.date

    # 1) new_materials
    new_materials_raw = scan_new_materials(kb_root, target_date)

    # 2) new_topics
    new_topics = scan_new_topics(kb_root, target_date)

    # 3) touched_topics
    touched_topics = scan_touched_topics(kb_root, new_materials_raw, new_topics)

    # 4) action_log_delta
    action_log_delta = scan_action_log_delta(kb_root, target_date)

    # 5) stats
    first_run = is_first_run(kb_root)
    avg_7d = past_7d_avg_variance(kb_root, target_date)

    n_materials = len(new_materials_raw)
    n_new_topics = len(new_topics)
    n_touched = len(touched_topics)

    variance = compute_variance(n_materials, n_new_topics, n_touched)
    scale = classify_scale(variance)

    # 清理内部字段
    new_materials_out = [
        {k: v for k, v in m.items() if not k.startswith("_")}
        for m in new_materials_raw
    ]

    payload = {
        "date": target_date,
        "scale": scale,
        "variance_score": variance,
        "is_first_run": first_run,
        "new_materials": new_materials_out,
        "new_topics": new_topics,
        "touched_topics": touched_topics,
        "action_log_delta": action_log_delta,
        "stats": {
            "new_materials_count": n_materials,
            "new_topics_count": n_new_topics,
            "touched_topics_count": n_touched,
            "past_7d_avg_variance": avg_7d,
        },
    }

    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    return 0


# ---------- 主入口 ----------


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="daily_digest",
        description="知识管家 · 昨日数据收集脚本（纯数据层，不生成文案）",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_coll = subparsers.add_parser("collect", help="扫描知识库输出当日 delta JSON")
    p_coll.add_argument("--date", required=True, help="分析日期 YYYY-MM-DD")
    p_coll.add_argument(
        "--kb-root",
        help="知识管家根目录（不传则按 $KB_ROOT 环境变量，再 fallback 到 ~/Desktop/知识管家/）",
    )
    p_coll.set_defaults(func=cmd_collect)

    args = parser.parse_args()

    # 启动水印：第一行 stdout
    started = datetime.now(timezone.utc).astimezone().isoformat()
    print(
        f"✅ daily_digest.py/{SCRIPT_VERSION} | mode={args.command} "
        f"| date={getattr(args, 'date', 'unknown')} | started={started}"
    )

    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\n[INTERRUPT] 用户中断", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
