#!/usr/bin/env python3
"""悟空听记归档脚本 · 知识管家专用

四个子命令：
  preflight  预检：列完整清单 + 生成 session_id（batch 强制依赖）
  list       列出听记元信息（不抓转写，供调试 / 兼容用）
  fetch      抓单条听记的完整转写 → markdown
  batch      批量抓取（必须带 --session-id；增量去重 + 失败重试 + 进度流）

bizType 分类（通过 UUID 解码得到）：
  0, 9  → 会议（视频会议录制 / AI 智能摘要）
  2     → AI 硬件（录音硬件上传）
  5     → AI 听记（手机录音、语音通话等）
  其他  → 其他（闪记/直播/钉钉文档/通话闪记等）

DWS 依赖：
  ~/.real/.bin/dws/bin/dws（钉钉 AI 听记 API 的 CLI 入口，每个悟空用户 $HOME 下独立）

使用示例：
  # 列出最近 3 天的听记元信息
  python3 wukong_minutes_to_md.py list --days 3 -f json

  # 抓单条听记
  python3 wukong_minutes_to_md.py fetch <uuid> -o out.md

  # 批量整理（preflight → batch 两步走，对应 SKILL.md workflow 5）
  python3 wukong_minutes_to_md.py preflight --days 7 --category 会议,AI听记,AI硬件
  python3 wukong_minutes_to_md.py batch --session-id <preflight 返回的 id> \\
      --output-dir "$HOME/Desktop/知识管家/1-素材/录音/" \\
      --skip-existing
  # 2026-04-24 起架构约定：知识管家根 = ~/Desktop/知识管家/
  # 放 workspace 外是为了绕开悟空 deliver_artifacts 自我递归 bug
"""
from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

# ---------- 常量 ----------

SCRIPT_VERSION = "v1.2"

DWS = os.path.expanduser("~/.real/.bin/dws/bin/dws")  # 每个悟空用户 $HOME 下有自己的 .real/
FETCH_TIMEOUT_SEC = 30
DEFAULT_RETRY = 3
DEFAULT_PAGE_SIZE = 50  # DWS list 一页的条数

# 脚本水印:写进每个 md 的 frontmatter,用于验证文件真的是脚本生成的(不是 Agent 手写)
GENERATOR_SIGNATURE = f"wukong_minutes_to_md.py/{SCRIPT_VERSION}"

# Session 持久化目录（跨平台：macOS/Linux/Windows 统一 ~/.cache）
SESSION_DIR = Path.home() / ".cache" / "wukong-knowledge-butler" / "sessions"
SESSION_TTL_SECONDS = 5 * 60  # 5 分钟

# bizType → 分类名的映射
BIZ_TYPE_CATEGORY = {
    0: "会议",
    9: "会议",
    2: "AI硬件",
    5: "AI听记",
}
# biz_type 原始语义（来自钉钉内部说明书，供 references/ 文档参考）
BIZ_TYPE_RAW_MEANING = {
    0: "视频会议录制",
    1: "闪记（线上）",
    2: "录音上传",
    3: "直播录制",
    4: "直播回放",
    5: "手机录音（线下）",
    6: "闪会（线下）",
    7: "钉钉文档（线下）",
    8: "通话闪记",
    9: "智能摘要",
}
DEFAULT_CATEGORIES = ["会议", "AI硬件", "AI听记"]  # 默认勾选的分类（不含"其他"）

# ---------- UUID 解码 ----------


def decode_uuid(uuid: str) -> dict | None:
    """解 hex UUID → {task_id, creator_uid, biz_type, category}

    UUID 是 hex(f'v2uid{task_id}_{creator_uid}_{biz_type}') 编码。
    返回 None 表示解码失败（应当仍归档，但分类为"其他"）。
    """
    try:
        decoded = bytes.fromhex(uuid).decode("utf-8")
    except Exception:
        return None
    m = re.match(r"^v2uid(\d+)_(\d+)_(\d+)$", decoded)
    if not m:
        return None
    task_id, creator_uid, biz_type_str = m.group(1), m.group(2), m.group(3)
    biz_type = int(biz_type_str)
    category = BIZ_TYPE_CATEGORY.get(biz_type, "其他")
    return {
        "task_id": task_id,
        "creator_uid": creator_uid,
        "biz_type": biz_type,
        "biz_type_raw": BIZ_TYPE_RAW_MEANING.get(biz_type, "未知"),
        "category": category,
    }


# ---------- DWS 调用 ----------


def run_dws(args: list[str], timeout: int = FETCH_TIMEOUT_SEC) -> dict:
    """调用 DWS CLI 返回 JSON 结果。"""
    cmd = [DWS, *args, "-f", "json"]
    try:
        out = subprocess.check_output(cmd, text=True, timeout=timeout)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"DWS 命令失败: {' '.join(args)}\n{e.output or e.stderr}")
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"DWS 命令超时（>{timeout}s）: {' '.join(args)}")
    try:
        return json.loads(out)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"DWS 返回非 JSON: {e}\n{out[:500]}")


def list_minutes(
    scope: str = "mine",
    start: str | None = None,
    end: str | None = None,
    query: str | None = None,
    max_per_page: int = DEFAULT_PAGE_SIZE,
) -> list[dict]:
    """翻完整分页列出听记元信息。

    scope: mine | all | shared
    start/end: ISO-8601 字符串（None 表示不限）
    query: 标题关键词筛选
    """
    if scope not in ("mine", "all", "shared"):
        raise ValueError(f"scope 必须是 mine/all/shared，收到 {scope!r}")

    items: list[dict] = []
    next_token: str | None = None
    while True:
        args = ["minutes", "list", scope, "--max", str(max_per_page)]
        if start:
            args.extend(["--start", start])
        if end:
            args.extend(["--end", end])
        if query:
            args.extend(["--query", query])
        if next_token:
            args.extend(["--next-token", next_token])

        payload = run_dws(args)
        result = payload.get("result", {})
        page_items = result.get("itemList") or []
        items.extend(page_items)

        has_more = result.get("hasMore")
        next_token = result.get("nextToken")
        if not has_more or not next_token:
            break
    return items


def fetch_transcription(uuid: str) -> list[dict]:
    """分页获取某条听记的全部转写段落。"""
    paragraphs: list[dict] = []
    next_token: str | None = None
    while True:
        args = ["minutes", "get", "transcription", "--id", uuid]
        if next_token:
            args.extend(["--next-token", next_token])
        payload = run_dws(args)
        result = payload.get("result", {})
        page_paras = result.get("paragraphList") or []
        paragraphs.extend(page_paras)
        if not result.get("hasNext"):
            break
        next_token = result.get("nextToken")
        if not next_token:
            break
    return paragraphs


def fetch_info(uuid: str) -> dict | None:
    """获取单条听记的基础信息（标题/时间/url 等）。"""
    try:
        payload = run_dws(["minutes", "get", "info", "--id", uuid])
        return payload.get("result") or None
    except RuntimeError:
        return None


# ---------- 过滤和筛选 ----------


def filter_by_categories(items: list[dict], categories: list[str]) -> list[dict]:
    """按分类过滤。categories 里包含 '其他' 会保留未知 biz_type。"""
    if not categories:
        return items
    keep = []
    for it in items:
        info = decode_uuid(it.get("uuid", ""))
        cat = (info or {}).get("category", "其他")
        if cat in categories:
            keep.append(it)
    return keep


def filter_existing(items: list[dict], output_dir: Path) -> list[dict]:
    """扫 output_dir 下所有 md 的 uuid，过滤掉已归档的。

    兼容两种 schema：
    - 新版（v1.3+）：uuid 在文件末尾 HTML 注释里 `<!-- ... uuid: xxx ... -->`
    - 旧版（v1.2 及之前）：uuid 在 frontmatter 顶部 `uuid: xxx`
    """
    if not output_dir.exists():
        return items

    existing_uuids: set[str] = set()
    # 匹配 "uuid: xxx" 不带行首锚定——能命中 frontmatter 也能命中末尾注释
    uuid_pattern = re.compile(r"^uuid:\s*([^\s\n]+)", re.MULTILINE)
    for md in output_dir.glob("*.md"):
        try:
            text = md.read_text(encoding="utf-8")
            m = uuid_pattern.search(text)
            if m:
                existing_uuids.add(m.group(1).strip().strip("\"'"))
        except Exception:
            continue

    return [it for it in items if it.get("uuid") not in existing_uuids]


def days_to_iso_range(days: int, now: datetime | None = None) -> tuple[str, str]:
    """将 --days N 转成 ISO-8601 的 (start, end)。"""
    now = now or datetime.now(timezone.utc).astimezone()
    end = now
    start = end - timedelta(days=days)
    return (start.isoformat(), end.isoformat())


# ---------- 渲染 ----------


def ms_to_ts(ms: int) -> str:
    """毫秒数 → [mm:ss] 时间戳。"""
    s = int(ms) // 1000
    return f"[{s // 60:02d}:{s % 60:02d}]"


def slugify(title: str, max_len: int = 40) -> str:
    """标题 → 文件名友好的 slug。保留中文，去特殊字符。"""
    # 去掉不适合文件名的字符
    s = re.sub(r'[\\/:*?"<>|\n\r\t]', "_", title)
    s = re.sub(r"_+", "_", s).strip("_ ")
    if len(s) > max_len:
        s = s[:max_len]
    return s or "untitled"


def build_filename(item: dict) -> str:
    """基于 meta 生成标准文件名：YYYY-MM-DD：{cleaned_slug}.md

    cleaned_slug 是从 title 中去掉前缀日期模式后的版本——避免钉钉听记的
    title（如"04-22 客户会议"）导致最终文件名 YYYY-MM-DD-MM-DD-... 日期重复。

    分隔符使用全角冒号 ：（U+FF1A），视觉分隔比 ASCII `-` 更清晰，
    macOS / Windows / iCloud 都合法。
    """
    start_ms = item.get("startTime") or 0
    date_str = datetime.fromtimestamp(start_ms / 1000).strftime("%Y-%m-%d") if start_ms else "unknown"

    title = item.get("title") or "untitled"
    # 去掉 title 前缀的日期模式（覆盖钉钉常见的几种格式）
    # 匹配：04-22 / 04/22 / 04.22 / 2026-04-22 / 2026/04/22 等
    title_cleaned = re.sub(
        r"^(?:\d{4}[-/.])?\d{1,2}[-/.]\d{1,2}\s*",
        "",
        title,
    ).strip()
    if not title_cleaned:
        title_cleaned = "untitled"

    title_slug = slugify(title_cleaned)
    return f"{date_str}：{title_slug}.md"   # 全角冒号


def render_markdown(meta: dict, paragraphs: list[dict], info: dict | None = None) -> str:
    """把听记元信息 + 段落渲染成 knowledge-butler 格式的 md。"""
    uuid = meta.get("uuid", "")
    uuid_info = decode_uuid(uuid) or {}
    title_raw = meta.get("title") or "悟空听记"
    # P4 跨平台命名安全：半角 ASCII 标点 → 全角中文标点
    # 半角 `:` 在 macOS 合法但 Windows/iCloud/GoogleDrive 同步会失败
    # 半角 `/` 在所有 POSIX 文件系统都被解释为路径分隔符
    title = title_raw.replace(":", "：").replace("/", "／")
    speakers = sorted({p.get("nickName") or "" for p in paragraphs if p.get("nickName")})
    has_speaker_sep = len(speakers) > 1

    # frontmatter
    start_ms = meta.get("startTime") or 0
    start_str = datetime.fromtimestamp(start_ms / 1000).strftime("%Y-%m-%d %H:%M") if start_ms else "unknown"
    duration_min = round((meta.get("durationMicros") or 0) / 60_000_000, 1)
    fetched = datetime.now().strftime("%Y-%m-%d")
    source_url = (info or {}).get("url") or ""
    keywords = ((meta.get("keywordsInfo") or {}).get("keywords") or [])

    # 用户面 frontmatter（仅 2 字段：用户读笔记需要的）
    fm_lines = [
        "---",
        f"title: {title}",
        f"source_url: {source_url}",
        "---",
    ]

    lines = fm_lines + ["", f"# {title}", ""]

    # meta 概述（正文第一行——用户读笔记主要看这里）
    meta_summary = f"> 开始时间：{start_str} · 时长 {duration_min} 分钟 · 共 {len(paragraphs)} 段"
    if speakers:
        meta_summary += f" · 发言人：{', '.join(speakers)}"
    lines.append(meta_summary)
    if keywords:
        lines.append(f"> 关键词：{', '.join(keywords)}")
    lines.append("")

    if not has_speaker_sep and paragraphs:
        lines.append("> ⚠️ 未区分发言人（声纹分离未生效），需结合上下文判断。")
        lines.append("")

    # 正文：段落
    for p in paragraphs:
        text = (p.get("paragraph") or "").strip()
        if not text:
            continue
        ts = ms_to_ts(p.get("startTime", 0))
        if has_speaker_sep:
            speaker = p.get("nickName") or "未知"
            lines.append(f"{ts} **{speaker}**：{text}")
        else:
            lines.append(f"{ts} {text}")
        lines.append("")

    # 文件末尾隐藏水印（机器读：去重 + 分类筛选 + Phase 7 验证用 · 用户面隐藏）
    lines.append("")
    lines.append("<!-- 机器水印（用户请忽略，脚本去重/分类筛选/验证使用）")
    lines.append(f"generator: {GENERATOR_SIGNATURE}")
    lines.append(f"uuid: {uuid}")
    lines.append(f"category: {uuid_info.get('category', '其他')}")
    lines.append(f"fetched: {fetched}")
    lines.append("-->")

    return "\n".join(lines)


def atomic_write(path: Path, content: str) -> None:
    """原子写入：先写 .tmp 再 rename。防止中断留半文件。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


# ---------- 带重试的单条 fetch ----------


def fetch_one_with_retry(meta: dict, retry: int = DEFAULT_RETRY) -> tuple[str, str] | None:
    """抓一条听记 → (filename, markdown_content)。失败返回 None。"""
    uuid = meta.get("uuid", "")
    if not uuid:
        return None

    last_err: str = ""
    for attempt in range(retry):
        try:
            paragraphs = fetch_transcription(uuid)
            info = fetch_info(uuid)
            md = render_markdown(meta, paragraphs, info)
            filename = build_filename(meta)
            return (filename, md)
        except Exception as e:
            last_err = str(e)
            if attempt < retry - 1:
                time.sleep(2 ** attempt)  # 指数退避：1s, 2s, 4s
            continue
    # 所有重试都失败
    sys.stderr.write(f"[FAILED] uuid={uuid} title={meta.get('title')!r} — {last_err}\n")
    return None


# ---------- CLI: list ----------


def cmd_list(args) -> int:
    start, end = None, None
    if args.days:
        start, end = days_to_iso_range(args.days)
    else:
        if args.since:
            start = args.since
        if args.until:
            end = args.until

    items = list_minutes(scope=args.scope, start=start, end=end, query=args.query)

    # 按分类过滤
    if args.category:
        categories = [c.strip() for c in args.category.split(",")]
        items = filter_by_categories(items, categories)

    # 丰富每条的分类信息
    enriched = []
    for it in items:
        uuid_info = decode_uuid(it.get("uuid", "")) or {}
        enriched.append({
            "uuid": it.get("uuid"),
            "title": it.get("title"),
            "startTime": it.get("startTime"),
            "start_str": (
                datetime.fromtimestamp(it.get("startTime", 0) / 1000).strftime("%Y-%m-%d %H:%M")
                if it.get("startTime") else ""
            ),
            "duration_min": round((it.get("durationMicros") or 0) / 60_000_000, 1),
            "speaker_count": 1,  # list 不返回段落，只能留待 fetch 时补
            "keywords": (it.get("keywordsInfo") or {}).get("keywords") or [],
            "category": uuid_info.get("category", "其他"),
            "biz_type": uuid_info.get("biz_type"),
            "biz_type_raw": uuid_info.get("biz_type_raw"),
            "orgName": it.get("orgName"),  # list all/shared 才有
        })

    if args.format == "json":
        print(json.dumps(enriched, ensure_ascii=False, indent=2))
    else:
        # 文本模式：人读友好的表格
        print(f"{'category':<8}{'date':<18}{'title':<50}{'uuid'}")
        print("-" * 120)
        for it in enriched:
            print(f"{it['category']:<8}{it['start_str']:<18}{(it['title'] or '')[:48]:<50}{it['uuid']}")
        print()
        # 分类汇总
        from collections import Counter
        cats = Counter(it["category"] for it in enriched)
        print(f"共 {len(enriched)} 条: " + " / ".join(f"{k} {v}" for k, v in cats.most_common()))
    return 0


# ---------- CLI: fetch ----------


def cmd_fetch(args) -> int:
    uuid = args.uuid
    # 先查到 meta（必须能精确定位，不能只扫最近 50）——通过 get info 拿
    info = fetch_info(uuid)
    if not info:
        print(f"[ERROR] 未找到听记 uuid={uuid}", file=sys.stderr)
        return 1

    # info 返回字段: duration, endTime, startTime, taskUuid, title, url
    # 组装成 list meta 的相同形态，以便 render_markdown 统一处理
    meta = {
        "uuid": uuid,
        "title": info.get("title"),
        "startTime": info.get("startTime"),
        "durationMicros": (info.get("duration") or 0) * 1000,
        # 关键词通常只有 list 才返回；fetch 场景下留空
        "keywordsInfo": {},
    }

    result = fetch_one_with_retry(meta, retry=args.retry)
    if not result:
        return 1
    filename, md = result

    # 输出策略优先级：--output-dir（推荐）> --output（兼容老用法）> stdout
    if args.output_dir:
        # P1 推荐路径：按 build_filename 自动生成规范文件名
        # 避免 LLM 用 -o 临时文件名后再 mv 重命名（命名规则会被绕过）
        out_dir = Path(args.output_dir).expanduser()
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / filename
        atomic_write(out_path, md)
        print(f"已写入 {out_path}")
    elif args.output:
        # 老兼容：用户明确指定 -o 完整路径
        out_path = Path(args.output)
        atomic_write(out_path, md)
        print(f"已写入 {out_path}")
    else:
        sys.stdout.write(md)
    return 0


# ---------- Session 持久化 ----------


def _session_path(session_id: str) -> Path:
    return SESSION_DIR / f"{session_id}.json"


def _new_session_id() -> str:
    """8 字符 hex session id。"""
    return secrets.token_hex(8)[:8]


def save_session(session: dict) -> Path:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    p = _session_path(session["session_id"])
    p.write_text(json.dumps(session, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def load_session(session_id: str) -> dict:
    """读取 session；不存在或过期抛 FileNotFoundError / RuntimeError。"""
    p = _session_path(session_id)
    if not p.exists():
        raise FileNotFoundError(f"session 文件不存在: {p}")
    data = json.loads(p.read_text(encoding="utf-8"))
    expires_at = data.get("expires_at")
    if expires_at:
        try:
            exp = datetime.fromisoformat(expires_at)
        except ValueError:
            exp = None
        now = datetime.now(timezone.utc).astimezone()
        if exp and exp < now:
            raise RuntimeError(f"session 已过期（expires_at={expires_at}）")
    return data


# ---------- CLI: preflight ----------


def cmd_preflight(args) -> int:
    # 解析时间范围
    start, end = None, None
    if args.days:
        start, end = days_to_iso_range(args.days)
    else:
        if args.since:
            start = args.since
        if args.until:
            end = args.until

    # 拉完整清单（不截断、不加 max 限制——list_minutes 内部会分页走完）
    raw_items = list_minutes(scope=args.scope, start=start, end=end, query=args.query)

    # 分类过滤
    categories_list: list[str] = []
    if args.category:
        categories_list = [c.strip() for c in args.category.split(",") if c.strip()]
        raw_items = filter_by_categories(raw_items, categories_list)

    # 组装 items：尽量带 link
    link_missing = 0
    items_out: list[dict] = []
    durations_s: list[int] = []
    for it in raw_items:
        uuid_info = decode_uuid(it.get("uuid", "")) or {}
        start_ms = it.get("startTime") or 0
        duration_micros = it.get("durationMicros") or 0
        duration_s = int(duration_micros / 1_000_000) if duration_micros else 0
        if duration_s:
            durations_s.append(duration_s)
        # 尝试从 list 返回里抓 link 字段（钉钉 API 不同 scope 下字段名不一致）
        link = (
            it.get("url")
            or it.get("link")
            or it.get("shareLink")
            or it.get("shareUrl")
        )
        if not link:
            link_missing += 1
        items_out.append({
            "uuid": it.get("uuid"),
            "title": it.get("title"),
            "category": uuid_info.get("category", "其他"),
            "bizType": uuid_info.get("biz_type"),
            "duration_seconds": duration_s,
            "link": link,
            "created_at": (
                datetime.fromtimestamp(start_ms / 1000).astimezone().isoformat()
                if start_ms else None
            ),
        })

    avg_duration = int(sum(durations_s) / len(durations_s)) if durations_s else 0
    now = datetime.now(timezone.utc).astimezone()
    expires = now + timedelta(seconds=SESSION_TTL_SECONDS)
    session_id = _new_session_id()

    params: dict = {"scope": args.scope}
    if args.days:
        params["days"] = args.days
    if args.since:
        params["since"] = args.since
    if args.until:
        params["until"] = args.until
    if categories_list:
        params["category"] = categories_list
    if args.query:
        params["query"] = args.query

    session = {
        "session_id": session_id,
        "created_at": now.isoformat(),
        "expires_at": expires.isoformat(),
        "params": params,
        "total": len(items_out),
        "items": items_out,
        "avg_duration_seconds": avg_duration,
    }

    save_session(session)

    # 如果 link 缺失,给 stderr warning,不影响 stdout 的 JSON 格式
    if link_missing:
        print(
            f"⚠️ 本次 preflight 未拿到 link 字段（{link_missing}/{len(items_out)} 条），"
            f"请检查 dws minutes list 是否返回了 url",
            file=sys.stderr,
        )

    # 紧凑 JSON 到 stdout,便于 AI 读取填 Phase 0b 模板
    print(json.dumps(session, ensure_ascii=False, separators=(",", ":")))
    return 0


# ---------- CLI: batch ----------


def cmd_batch(args) -> int:
    output_dir = Path(args.output_dir).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)

    # 强制 session 校验
    try:
        session = load_session(args.session_id)
    except FileNotFoundError:
        print(
            "❌ session 未找到。请先运行 preflight 生成 session",
            file=sys.stderr,
        )
        return 1
    except RuntimeError:
        print(
            "❌ session 已过期（5 分钟 TTL），请重新 preflight",
            file=sys.stderr,
        )
        return 1

    # 按 session.items 逐条 fetch（不再自己调 list，保证与预检页一致）
    session_items: list[dict] = session.get("items") or []
    # 构造 meta（保留原有结构：需要 uuid/title/startTime/durationMicros/keywordsInfo）
    items: list[dict] = []
    for s in session_items:
        start_iso = s.get("created_at")
        start_ms = 0
        if start_iso:
            try:
                start_ms = int(datetime.fromisoformat(start_iso).timestamp() * 1000)
            except Exception:
                start_ms = 0
        dur_s = s.get("duration_seconds") or 0
        items.append({
            "uuid": s.get("uuid"),
            "title": s.get("title"),
            "startTime": start_ms,
            "durationMicros": int(dur_s) * 1_000_000,
            "keywordsInfo": {},
        })

    # 增量去重（保留已验证逻辑）
    skipped_existing = 0
    if args.skip_existing:
        before = len(items)
        items = filter_existing(items, output_dir)
        skipped_existing = before - len(items)

    total = len(items)
    print(
        f"[INFO] session={session['session_id']} 本次将归档 {total} 条"
        f"（跳过已存在 {skipped_existing} 条）",
        file=sys.stderr,
    )
    if args.dry_run:
        for it in items:
            print(f"[DRY-RUN] {it.get('uuid')} {it.get('title')}")
        return 0

    # 批处理：逐条 fetch，带进度 JSON 流
    failed_records: list[dict] = []
    succeeded = 0
    for idx, meta in enumerate(items, start=1):
        uuid = meta.get("uuid")
        title = (meta.get("title") or "")[:40]
        print(f"[{idx}/{total}] 抓取 {title}...", file=sys.stderr)

        result = fetch_one_with_retry(meta, retry=args.retry)
        if not result:
            failed_records.append({
                "uuid": uuid,
                "title": meta.get("title"),
                "reason": "fetch_failed_after_retry",
            })
            # 进度流
            print(json.dumps({
                "uuid": uuid, "title": meta.get("title"),
                "status": "failed", "path": None,
            }, ensure_ascii=False))
            continue

        filename, md = result
        out_path = output_dir / filename
        atomic_write(out_path, md)
        succeeded += 1

        # 进度流
        print(json.dumps({
            "uuid": uuid, "title": meta.get("title"),
            "status": "ok", "path": str(out_path),
        }, ensure_ascii=False))

    # 完成回执
    print(f"\n[完成] 成功 {succeeded} / {total},失败 {len(failed_records)}", file=sys.stderr)

    # 失败记录写到 failed.jsonl
    if failed_records:
        failed_path = output_dir / "_failed.jsonl"
        with failed_path.open("a", encoding="utf-8") as f:
            for rec in failed_records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"[WARN] 失败条目已记录到 {failed_path}", file=sys.stderr)

    return 0 if not failed_records else 2


# ---------- 主入口 ----------


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="wukong_minutes_to_md",
        description="悟空听记归档脚本 · 知识管家专用",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # preflight
    p_pre = subparsers.add_parser(
        "preflight",
        help="预检：列完整清单 + 生成 session_id（batch 强制依赖）",
    )
    p_pre.add_argument("--scope", choices=["mine", "all", "shared"], default="mine")
    p_pre.add_argument("--days", type=int, help="最近 N 天")
    p_pre.add_argument("--since", help="起始时间 ISO-8601")
    p_pre.add_argument("--until", help="结束时间 ISO-8601")
    p_pre.add_argument("--query", help="标题关键词筛选")
    p_pre.add_argument("--category", help="分类筛选（逗号分隔，如 '会议,AI听记'；不传则全部）")
    p_pre.set_defaults(func=cmd_preflight)

    # list
    p_list = subparsers.add_parser("list", help="列出听记元信息（不抓转写）")
    p_list.add_argument("--scope", choices=["mine", "all", "shared"], default="mine")
    p_list.add_argument("--days", type=int, help="最近 N 天")
    p_list.add_argument("--since", help="起始时间 ISO-8601")
    p_list.add_argument("--until", help="结束时间 ISO-8601")
    p_list.add_argument("--query", help="标题关键词筛选")
    p_list.add_argument("--category", help="分类筛选（逗号分隔，如 '会议,AI听记'；不传则全部）")
    p_list.add_argument("-f", "--format", choices=["json", "table"], default="table")
    p_list.set_defaults(func=cmd_list)

    # fetch
    p_fetch = subparsers.add_parser("fetch", help="抓单条听记转写")
    p_fetch.add_argument("uuid", help="听记 taskUuid")
    p_fetch.add_argument(
        "-d", "--output-dir",
        help="输出目录（推荐用法）：文件名按 build_filename 自动生成（YYYY-MM-DD：title.md），"
             "避免 LLM 用 -o 临时文件名后再 mv 绕过命名规则",
    )
    p_fetch.add_argument(
        "-o", "--output",
        help="输出文件完整路径（兼容老用法，不推荐——绕过 build_filename 自动命名）。"
             "不传 -o 也不传 -d 则输出到 stdout。",
    )
    p_fetch.add_argument("--retry", type=int, default=DEFAULT_RETRY, help="失败重试次数")
    p_fetch.set_defaults(func=cmd_fetch)

    # batch
    p_batch = subparsers.add_parser("batch", help="批量归档到目录（必须带 --session-id）")
    p_batch.add_argument(
        "--session-id",
        required=True,
        help="由 preflight 子命令产出的 session_id（强制，防止绕过预检直调）",
    )
    p_batch.add_argument("--output-dir", required=True, help="归档目录")
    p_batch.add_argument("--skip-existing", action="store_true",
                         help="跳过 output-dir 中 frontmatter.uuid 已存在的条目")
    p_batch.add_argument("--retry", type=int, default=DEFAULT_RETRY, help="单条失败重试次数")
    p_batch.add_argument("--dry-run", action="store_true", help="仅列出将归档的条目，不实际抓取")
    p_batch.set_defaults(func=cmd_batch)

    args = parser.parse_args()

    # 启动水印：第一行 stdout，让 grep 能确认脚本真的被调用
    session_tag = getattr(args, "session_id", None) or "none"
    started = datetime.now(timezone.utc).astimezone().isoformat()
    print(
        f"✅ wukong_minutes_to_md.py/{SCRIPT_VERSION} | mode={args.command} "
        f"| session={session_tag} | started={started}"
    )

    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\n[INTERRUPT] 用户中断，已写入的文件保留，下次加 --skip-existing 续跑", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
