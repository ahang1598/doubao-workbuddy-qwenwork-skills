#!/usr/bin/env python3
"""
kb_pipeline.py · 知识管家统一入口

4 个子命令：
  init           初始化知识管家骨架
  preflight-day  拉某天某分类的听记原文 + 维护 uuid→路径索引
  read-source    输出指定听记的完整原文（强制全文）
  compile-day    从 stdin 读 JSON，原子写入所有摘要 + 专题 + 索引
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# 复用 wukong_minutes_to_md 的内部函数（避免重复造轮子）
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from wukong_minutes_to_md import (  # noqa: E402
    list_minutes,
    filter_by_categories,
    fetch_one_with_retry,
    decode_uuid,
    build_filename,
    atomic_write,
)

# ─────────────────────────────────────────────
# 路径与缓存
# ─────────────────────────────────────────────


def kb_root() -> Path:
    """解析 KB_ROOT（环境变量优先，默认桌面知识管家）。"""
    env = os.environ.get("KB_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    return (Path.home() / "Desktop" / "知识管家").resolve()


def cache_path() -> Path:
    """uuid → 文件路径的 session 缓存。"""
    return kb_root() / "3-AI工作记录" / ".session-cache.json"


def load_cache() -> dict:
    p = cache_path()
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def save_cache(cache: dict) -> None:
    p = cache_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


# ─────────────────────────────────────────────
# init 子命令
# ─────────────────────────────────────────────


INIT_FILES = {
    "0-使用说明.md": """# 知识管家使用说明

欢迎！这是你的个人 AI 知识库。

## 三个区域

- **1-素材/** — 你投喂的原始材料（文稿/录音/收藏）
- **2-AI知识库/** — 我编织出来的知识（摘要/专题/洞察）
- **3-AI工作记录/** — 我的工作日志（你可以审计）

## 三步上手

1. 投喂素材："帮我整理这份材料" + 拖文件 / 贴链接
2. 提问："xxx 这个客户最近怎么样？"
3. 看变化：每天早晨说"日报"看看 AI 知识库长出了什么

## 规则手册

`规则手册.md` 是你告诉我"希望我怎么工作"的偏好文件。
有任何不喜欢的地方，直接改它，下次任务我会按新规则做事。
""",
    "1-素材/1-素材说明.md": """# 素材区

这里放你的原始材料——我**只读不修改**，即使发现错别字。

- **文稿/** — 你自己写的文字（笔记、想法、草稿）
- **录音/** — 录音转写、AI 听记
- **收藏/** — 外部文章、剪藏（含 PDF 等附件）

## 怎么投喂

- 拖文件到对应子目录 → 跟我说"整理一下这堆"
- 直接发文字给我："帮我存这段：" + 内容
- 同步钉钉听记："整理最近 3 天的会议"
""",
    "2-AI知识库/2-AI知识库说明.md": """# AI 知识库

这里是我编织你素材后产出的活知识——**你只读，我维护**。

- **素材摘要/** — 每份素材的浓缩
- **专题/** — 值得追踪的"它"（人/组织/项目/产品/方法论）
- **洞察/** — 跨多专题的综合发现 / Q&A 归档

## 双向链接

专题/洞察页里有 `[[xxx]]` 双链——点击可跳转，让知识互相串联。
""",
    "3-AI工作记录/3-AI工作记录说明.md": """# AI 工作记录

我的工作档案——**透明可审计**。

- **目录.md** — AI 知识库的全索引
- **操作记录.md** — 我做过的每件事（append-only，永不删除）
- **日报/** — 每日 AI 知识库变化总结
""",
    "3-AI工作记录/目录.md": """# AI 知识库索引

（初始为空——投喂第一份素材后会自动填充）
""",
}


RULES_TEMPLATE_RELATIVE = "templates/规则手册.md"


def cmd_init(args) -> int:
    """初始化骨架——写说明文件 + 规则手册 + 操作记录初始条目。"""
    root = kb_root()
    today = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().strftime("%H:%M")

    created = 0
    skipped = 0

    # 建目录骨架
    for sub in [
        "1-素材/文稿", "1-素材/录音", "1-素材/收藏/附件",
        "2-AI知识库/素材摘要", "2-AI知识库/专题", "2-AI知识库/洞察",
        "3-AI工作记录",
    ]:
        (root / sub).mkdir(parents=True, exist_ok=True)

    # 写 5 个固定内容说明文件
    for relative, content in INIT_FILES.items():
        target = root / relative
        if target.exists() and args.mode == "upgrade":
            skipped += 1
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        created += 1

    # 写规则手册（从模板复制 + 替换日期）
    template_path = SCRIPT_DIR.parent / RULES_TEMPLATE_RELATIVE
    rules_target = root / "规则手册.md"
    if not (rules_target.exists() and args.mode == "upgrade"):
        if template_path.exists():
            tpl = template_path.read_text(encoding="utf-8")
            rules_target.write_text(
                tpl.replace("TODO_DATE", today),
                encoding="utf-8",
            )
            created += 1
        else:
            print(
                f"⚠️ 规则手册模板不存在: {template_path}",
                file=sys.stderr,
            )

    # 写操作记录初始条目（仅 mode=full 时）
    log_target = root / "3-AI工作记录" / "操作记录.md"
    if not log_target.exists():
        log_target.write_text(
            f"# 操作记录（append-only）\n\n"
            f"## [{today} {now}] 初始化 | 知识管家首次创建\n\n"
            f"- 创建目录结构：1-素材/、2-AI知识库/、3-AI工作记录/\n"
            f"- 创建说明文件 + 规则手册.md + 目录.md\n"
            f"- 状态：全新初始化完成\n",
            encoding="utf-8",
        )
        created += 1

    print(json.dumps(
        {"created": created, "skipped": skipped, "mode": args.mode},
        ensure_ascii=False,
    ))
    return 0


# ─────────────────────────────────────────────
# preflight-day 子命令
# ─────────────────────────────────────────────


def cmd_preflight_day(args) -> int:
    """拉某天某分类的听记原文 + 维护 uuid→路径索引，stdout 返回 items 清单。"""
    date = args.date  # YYYY-MM-DD
    start = f"{date}T00:00:00"
    end = f"{date}T23:59:59"

    raw_items = list_minutes(
        scope=args.scope,
        start=start,
        end=end,
        query=None,
    )

    if args.category:
        cats = [c.strip() for c in args.category.split(",") if c.strip()]
        raw_items = filter_by_categories(raw_items, cats)

    output_dir = kb_root() / "1-素材" / "录音"
    output_dir.mkdir(parents=True, exist_ok=True)

    items_out = []
    cache = load_cache()

    for it in raw_items:
        uuid = it.get("uuid", "")
        title = it.get("title", "untitled")
        start_ms = it.get("startTime") or 0
        duration_micros = it.get("durationMicros") or 0
        duration_min = round(duration_micros / 60_000_000, 1) if duration_micros else 0

        # 检查是否已经拉过（按 build_filename 命名查重）
        meta = {
            "uuid": uuid,
            "title": title,
            "startTime": start_ms,
            "durationMicros": duration_micros,
            "keywordsInfo": it.get("keywordsInfo", {}),
        }
        filename = build_filename(meta)
        target_path = output_dir / filename

        if not target_path.exists():
            # fetch_one_with_retry 返回 (filename, md_content)
            result = fetch_one_with_retry(meta, retry=2)
            if result:
                _, md = result
                atomic_write(target_path, md)
            else:
                print(
                    f"⚠️ 拉取失败：{uuid[:16]}...",
                    file=sys.stderr,
                )
                continue

        # 维护 uuid → 路径索引
        cache[uuid] = str(target_path)

        uuid_info = decode_uuid(uuid) or {}
        items_out.append({
            "uuid": uuid,
            "title": title,
            "category": uuid_info.get("category", "其他"),
            "duration_min": duration_min,
        })

    save_cache(cache)

    print(json.dumps(
        {"date": date, "items": items_out, "total": len(items_out)},
        ensure_ascii=False,
    ))
    return 0


# ─────────────────────────────────────────────
# read-source 子命令
# ─────────────────────────────────────────────


def cmd_read_source(args) -> int:
    """从 uuid 读完整原文输出到 stdout（强制全文，确保摘要基于完整内容）。"""
    cache = load_cache()
    uuid = args.uuid

    if uuid not in cache:
        print(
            f"❌ uuid 未在 session-cache 中找到：{uuid[:16]}...\n"
            f"   先跑 preflight-day 拉取听记后再 read-source",
            file=sys.stderr,
        )
        return 1

    path = Path(cache[uuid])
    if not path.exists():
        print(
            f"❌ 文件不存在：{path}",
            file=sys.stderr,
        )
        return 2

    # 直接输出完整原文 —— 无截断、无 limit
    sys.stdout.write(path.read_text(encoding="utf-8"))
    return 0


# ─────────────────────────────────────────────
# compile-day 子命令
# ─────────────────────────────────────────────


REQUIRED_SUMMARY_FIELDS = {"uuid", "summary_md"}
REQUIRED_TOPIC_FIELDS = {"name", "kind", "page_md"}
VALID_TOPIC_KINDS = {"person", "org", "project", "product", "method", "topic", "other"}


def _validate_compile_payload(payload: dict) -> list[str]:
    """返回错误清单（空列表 = 通过）。"""
    errors = []
    if not isinstance(payload, dict):
        return ["payload 必须是 dict"]
    summaries = payload.get("summaries")
    if not isinstance(summaries, list):
        return ["payload.summaries 必须是 list"]

    for i, s in enumerate(summaries):
        if not isinstance(s, dict):
            errors.append(f"summaries[{i}] 必须是 dict")
            continue
        missing = REQUIRED_SUMMARY_FIELDS - set(s.keys())
        if missing:
            errors.append(f"summaries[{i}] 缺字段: {missing}")
        # 校验 ## 涉及实体 段（P6 必含）
        sm = s.get("summary_md", "")
        if "## 涉及实体" not in sm:
            errors.append(
                f"summaries[{i}](uuid={s.get('uuid', '?')[:16]}...) summary_md 必须含 '## 涉及实体' 段（compile-once-use-many）"
            )
        # 校验 topics 子结构
        topics = s.get("topics", [])
        if not isinstance(topics, list):
            errors.append(f"summaries[{i}].topics 必须是 list（可空）")
        else:
            for j, t in enumerate(topics):
                if not isinstance(t, dict):
                    errors.append(f"summaries[{i}].topics[{j}] 必须是 dict")
                    continue
                missing_t = REQUIRED_TOPIC_FIELDS - set(t.keys())
                if missing_t:
                    errors.append(
                        f"summaries[{i}].topics[{j}] 缺字段: {missing_t}"
                    )
                if t.get("kind") not in VALID_TOPIC_KINDS:
                    errors.append(
                        f"summaries[{i}].topics[{j}].kind 无效（必须是 {VALID_TOPIC_KINDS}）"
                    )

    return errors


def _summary_filename(date: str, title: str) -> str:
    """摘要文件命名：摘要-MM-DD-{slug}.md（保持向后兼容）。"""
    # 提取 MM-DD
    try:
        dt = datetime.strptime(date, "%Y-%m-%d")
        md = dt.strftime("%m-%d")
    except ValueError:
        md = "unknown"
    # title 清洗：替换特殊字符
    slug = re.sub(r"[\\/:*?\"<>|]", "_", title)[:60].strip()
    return f"摘要-{md}-{slug}.md"


def cmd_compile_day(args) -> int:
    """从 stdin 读 JSON，原子写入所有摘要 + 专题 + 更新索引。"""
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(
            f"❌ stdin JSON 解析失败：{e}\n"
            f"   提示：用 heredoc <<'PIPELINE_EOF' ... PIPELINE_EOF 包裹 JSON",
            file=sys.stderr,
        )
        return 10

    errors = _validate_compile_payload(payload)
    if errors:
        print(
            "❌ payload schema 验证失败：\n  - " + "\n  - ".join(errors),
            file=sys.stderr,
        )
        return 11

    date = payload.get("date", datetime.now().strftime("%Y-%m-%d"))
    summaries = payload["summaries"]

    root = kb_root()
    summaries_dir = root / "2-AI知识库" / "素材摘要"
    topics_dir = root / "2-AI知识库" / "专题"
    summaries_dir.mkdir(parents=True, exist_ok=True)
    topics_dir.mkdir(parents=True, exist_ok=True)

    cache = load_cache()
    summaries_written = 0
    topics_new = 0
    topics_updated = 0
    links_added = 0

    new_index_lines = []

    for s in summaries:
        uuid = s["uuid"]
        # 摘要文件命名
        # 从 cache 拿 title（preflight-day 时已写）
        source_path = cache.get(uuid)
        if source_path:
            # 从原文 frontmatter 提 title（更稳）
            try:
                source_text = Path(source_path).read_text(encoding="utf-8")
                m = re.search(r"^title:\s*(.+)$", source_text, re.MULTILINE)
                title = m.group(1).strip() if m else f"听记-{uuid[:8]}"
            except Exception:
                title = f"听记-{uuid[:8]}"
        else:
            title = f"听记-{uuid[:8]}"

        summary_filename = _summary_filename(date, title)
        summary_path = summaries_dir / summary_filename
        summary_path.write_text(s["summary_md"], encoding="utf-8")
        summaries_written += 1
        new_index_lines.append(
            f"- [[{summary_filename[:-3]}]] — {title}（{date}）"
        )

        # 写关联专题（kind 区分新建 vs 更新）
        for t in s.get("topics", []):
            topic_filename = f"{t['name']}.md"
            topic_path = topics_dir / topic_filename
            if topic_path.exists():
                # 已有 → append 一行 ## 被提到（最简实现：模板末尾追加）
                old = topic_path.read_text(encoding="utf-8")
                # 检测 ## 被提到 段
                if "## 被提到" in old:
                    new = old + (
                        f"\n- **{date}** | [[{summary_filename[:-3]}]] — "
                        f"{t.get('relation', '出现').strip()}\n"
                    )
                else:
                    new = old + (
                        f"\n## 被提到\n（以下素材/专题/洞察提到过这个对象）\n\n"
                        f"- **{date}** | [[{summary_filename[:-3]}]] — "
                        f"{t.get('relation', '出现').strip()}\n"
                    )
                topic_path.write_text(new, encoding="utf-8")
                topics_updated += 1
                links_added += 1
            else:
                # 新建专题页（用 LLM 提供的 page_md，或简洁默认模板）
                page_md = t.get("page_md") or (
                    f"---\ntitle: {t['name']}\ntype: topic\n"
                    f"entity_kind: {t['kind']}\ncreated: {date}\n---\n\n"
                    f"## 简介\n\n（待补充）\n\n"
                    f"## 被提到\n（以下素材/专题/洞察提到过这个对象）\n\n"
                    f"- **{date}** | [[{summary_filename[:-3]}]] — "
                    f"{t.get('relation', '首次出现').strip()}\n"
                )
                topic_path.write_text(page_md, encoding="utf-8")
                topics_new += 1
                links_added += 1

    # 追加目录.md 索引
    catalog_path = root / "3-AI工作记录" / "目录.md"
    if catalog_path.exists():
        existing = catalog_path.read_text(encoding="utf-8")
    else:
        existing = "# AI 知识库索引\n\n"
    catalog_path.write_text(
        existing + "\n## " + date + " 新增\n\n" + "\n".join(new_index_lines) + "\n",
        encoding="utf-8",
    )

    # 追加操作记录.md
    log_path = root / "3-AI工作记录" / "操作记录.md"
    now = datetime.now().strftime("%H:%M")
    today = datetime.now().strftime("%Y-%m-%d")
    log_entry = (
        f"\n- **{today} {now}** | workflow 5 完成 | "
        f"整理 {summaries_written} 条 | 新建专题 {topics_new} 个 | "
        f"反向链接 {links_added} 处\n"
    )
    if log_path.exists():
        log_path.write_text(
            log_path.read_text(encoding="utf-8") + log_entry,
            encoding="utf-8",
        )
    else:
        log_path.write_text(
            f"# 操作记录（append-only）\n{log_entry}",
            encoding="utf-8",
        )

    print(json.dumps({
        "summaries": summaries_written,
        "topics_new": topics_new,
        "topics_updated": topics_updated,
        "links_added": links_added,
        "date": date,
    }, ensure_ascii=False))

    return 0


# ─────────────────────────────────────────────
# CLI 入口
# ─────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="kb_pipeline",
        description="知识管家统一入口（init / preflight-day / read-source / compile-day）",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # init
    p_init = sub.add_parser("init", help="初始化知识管家骨架（7 个说明文件）")
    p_init.add_argument(
        "--mode",
        choices=["full", "upgrade"],
        default="full",
        help="full=覆盖写所有；upgrade=已存在则跳过",
    )
    p_init.set_defaults(func=cmd_init)

    # preflight-day
    p_pre = sub.add_parser(
        "preflight-day",
        help="拉某天某分类的听记原文，维护 uuid→路径索引",
    )
    p_pre.add_argument("--date", required=True, help="YYYY-MM-DD")
    p_pre.add_argument("--category", help="分类，逗号分隔（如 'AI硬件,AI听记'）")
    p_pre.add_argument(
        "--scope",
        choices=["mine", "all"],
        default="mine",
        help="mine=我的听记，all=全部",
    )
    p_pre.set_defaults(func=cmd_preflight_day)

    # read-source
    p_read = sub.add_parser(
        "read-source",
        help="按 uuid 输出听记原文全文（强制不可截断）",
    )
    p_read.add_argument("--uuid", required=True, help="听记 taskUuid")
    p_read.set_defaults(func=cmd_read_source)

    # compile-day
    p_comp = sub.add_parser(
        "compile-day",
        help="从 stdin 读 JSON，原子写入所有摘要+专题+索引",
    )
    p_comp.set_defaults(func=cmd_compile_day)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
