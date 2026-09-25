#!/usr/bin/env python3
"""purge_deck.py — 慢速清理飞书 deck · 只保留第 1 页并把它清空。

用法:
  python3 purge_deck.py --deck <deck_id>                              # 拉全稿 · 删除除第 1 页外所有页 + 清空第 1 页
  python3 purge_deck.py --deck <deck_id> --slide-ids ID1,ID2,...      # 只删指定 slide_id(不清第 1 页,除非同时给 --first-slide-id)
  python3 purge_deck.py --deck <deck_id> --slide-ids ID1,... --first-slide-id ID0  # 指定第 1 页清空
  python3 purge_deck.py --deck <deck_id> --no-clear-first             # 保留原模板首页(不覆盖成空白)
  python3 purge_deck.py --deck <deck_id> --pace 1.5                   # 每页间 sleep 1.5s(默认 1s = 1 QPS)
  python3 purge_deck.py --deck <deck_id> --max-rounds 5               # 失败页多轮重试(默认 5 轮)

设计:
- 单线程 · 每页间 sleep(默认 1s = 1 QPS)· 保守节流避开 rate_limit
- 单页失败立即 skip(不 block)· 汇总失败页
- 全部扫完后 · 剩余失败页多轮重试(每轮之间 sleep 更长)
- 最后清空第 1 页成空白 slide(短退避重试)
- 打印 JSON 报告:deleted / first_page_cleared / failed_slide_ids
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path


def _run_lark_cli(cmd: list[str], timeout: int = 20, cwd: str | None = None) -> tuple[int, str, str]:
    """跑 lark-cli · 返回 (rc, stdout, stderr)。"""
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return -1, "", f"timeout after {timeout}s"
    except FileNotFoundError:
        return -2, "", "lark-cli binary not found"


def _fetch_all_slide_ids(deck_id: str, work: Path) -> tuple[list[str], str]:
    """拉全稿 · 返回 (slide_ids, error)。error 为空表示 ok。"""
    out_path = work / "_purge_probe.xml"
    cmd = [
        "lark-cli", "slides", "+xml-get",
        "--presentation", deck_id,
        "--output", str(out_path.name),
        "--json",
    ]
    rc, stdout, stderr = _run_lark_cli(cmd, timeout=120, cwd=str(work))
    if rc != 0:
        return [], f"xml-get failed rc={rc}: {(stdout or stderr)[:300]}"
    if not out_path.exists():
        return [], f"xml-get 无输出文件: {out_path}"
    content = out_path.read_text(encoding="utf-8", errors="ignore")
    slide_ids = re.findall(r'<slide[^>]*\bid="([^"]+)"', content)
    try:
        out_path.unlink()
    except Exception:
        pass
    return slide_ids, ""


def _delete_slide(deck_id: str, sid: str, work: Path, timeout: int = 15) -> tuple[bool, str]:
    """删单页 · 单次尝试 · 无重试。返回 (ok, err)。"""
    cmd = [
        "lark-cli", "slides", "+delete-slide",
        "--presentation", deck_id,
        "--slide-id", sid,
        "--json",
    ]
    rc, stdout, stderr = _run_lark_cli(cmd, timeout=timeout, cwd=str(work))
    if rc == 0:
        return True, ""
    detail = (stdout or stderr or "").strip()[:200]
    return False, f"rc={rc}: {detail}"


def _clear_first_page(deck_id: str, first_sid: str, work: Path,
                       timeout: int = 30, max_attempts: int = 3) -> tuple[bool, str]:
    """把第 1 页覆盖成空白 slide · 短退避重试(2s/4s)。"""
    empty_xml = work / ".purge-empty-slide.xml"
    empty_xml.write_text(
        f'<slide xmlns="https://www.larkoffice.com/sml/2.0" id="{first_sid}"></slide>',
        encoding="utf-8",
    )
    cmd = [
        "lark-cli", "slides", "+update-slide",
        "--presentation", deck_id,
        "--slide-id", first_sid,
        "--content", "@" + empty_xml.name,
        "--json",
    ]
    err = ""
    rc = -1
    for attempt in range(1, max_attempts + 1):
        rc, stdout, stderr = _run_lark_cli(cmd, timeout=timeout, cwd=str(work))
        if rc == 0:
            try:
                empty_xml.unlink()
            except Exception:
                pass
            return True, ""
        err = (stdout or stderr or "").strip()[:200]
        if attempt < max_attempts:
            time.sleep(2 * attempt)  # 2s / 4s
    try:
        empty_xml.unlink()
    except Exception:
        pass
    return False, f"rc={rc}: {err}"


def _delete_sequence(deck_id: str, slide_ids: list[str], work: Path,
                      pace_sec: float, label: str = "") -> tuple[int, list[tuple[str, str]]]:
    """单轮串行删除 · 每页间 sleep pace_sec。返回 (deleted, failures)。"""
    deleted = 0
    failures: list[tuple[str, str]] = []
    total = len(slide_ids)
    for i, sid in enumerate(slide_ids):
        if i > 0:
            time.sleep(pace_sec)
        ok, err = _delete_slide(deck_id, sid, work, timeout=15)
        if ok:
            deleted += 1
            if (i + 1) % 20 == 0 or i == total - 1:
                print(f"  [{label}] progress: {i+1}/{total} · deleted so far: {deleted}",
                      file=sys.stderr, flush=True)
        else:
            failures.append((sid, err))
    return deleted, failures


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--deck", required=True, help="xml_presentation_id or /slides/ URL")
    ap.add_argument("--work-dir", default=".",
                    help="工作目录(用于放临时 xml-get output 文件)。默认当前目录。")
    ap.add_argument("--slide-ids", default=None,
                    help="逗号分隔的 slide_id 列表 · 指定就删这些;不指定就拉全稿(除第 1 页外全删)。")
    ap.add_argument("--keep-first", action="store_true", default=True,
                    help="保留第 1 页(默认 True · 避免删空后 add-slide 报 block is empty)")
    ap.add_argument("--no-keep-first", dest="keep_first", action="store_false",
                    help="不保留第 1 页(慎用 · 会导致后续 +add-slide 失败)")
    ap.add_argument("--clear-first", action="store_true", default=True,
                    help="若保留了第 1 页,把它 +update-slide 覆盖成空白(默认 True · 让 MainAgent 后续 update-slide 覆盖时干净)")
    ap.add_argument("--no-clear-first", dest="clear_first", action="store_false",
                    help="关闭覆盖第 1 页(保留原模板首页作为占位)")
    ap.add_argument("--first-slide-id", default=None,
                    help="要覆盖为空白的第 1 页 slide_id;仅在 --slide-ids 模式下用(--slide-ids 模式不拉全稿,无法自动识别第 1 页)")
    ap.add_argument("--pace", type=float, default=1.0,
                    help="每页 delete 之间的 sleep(秒)· 默认 1.0(1 QPS 保守节流)")
    ap.add_argument("--max-rounds", type=int, default=5,
                    help="失败页多轮重试的最大轮数(默认 5)")
    ap.add_argument("--round-sleep", type=float, default=15.0,
                    help="重试轮次之间的 sleep(秒)· 默认 15s 让服务端限流窗口过去")
    args = ap.parse_args()

    # 从 URL 抽 deck_id
    deck_id = args.deck
    m = re.search(r'/slides/([A-Za-z0-9]+)', deck_id)
    if m:
        deck_id = m.group(1)

    work = Path(args.work_dir).resolve()
    if not work.exists():
        print(json.dumps({"ok": False, "error": f"work dir not found: {work}"}))
        return 2

    start = time.monotonic()

    # 1) 决定要删的 slide_ids
    if args.slide_ids:
        to_delete = [s.strip() for s in args.slide_ids.split(",") if s.strip()]
        print(f"[purge] using --slide-ids · {len(to_delete)} pages to delete",
              file=sys.stderr, flush=True)
        # --slide-ids 模式:第 1 页 id 用户指定
        first_id = args.first_slide_id
    else:
        print(f"[purge] fetching deck full xml to enumerate slide_ids...",
              file=sys.stderr, flush=True)
        all_ids, err = _fetch_all_slide_ids(deck_id, work)
        if err:
            print(json.dumps({"ok": False, "error": f"fetch failed: {err}"}))
            return 3
        if not all_ids:
            print(json.dumps({"ok": True, "deck": deck_id, "message": "deck is empty · nothing to delete",
                              "elapsed_sec": round(time.monotonic() - start, 2)}))
            return 0
        first_id = all_ids[0]
        to_delete = all_ids[1:] if args.keep_first else all_ids
        print(f"[purge] deck has {len(all_ids)} pages · will delete {len(to_delete)}"
              f"{' (keeping first: ' + first_id + ')' if args.keep_first else ''}",
              file=sys.stderr, flush=True)

    if not to_delete and not (args.clear_first and first_id):
        print(json.dumps({"ok": True, "deck": deck_id, "deleted": 0,
                          "message": "nothing to delete or clear",
                          "elapsed_sec": round(time.monotonic() - start, 2)}))
        return 0

    # 2) 主删除阶段:一趟扫 · pace 节流(to_delete 可能为空 · 跳过)
    total_deleted = 0
    failures: list[tuple[str, str]] = []
    if to_delete:
        print(f"[purge] round 1 · pace={args.pace}s · deleting {len(to_delete)} pages...",
              file=sys.stderr, flush=True)
        deleted, failures = _delete_sequence(deck_id, to_delete, work, args.pace, label="round 1")
        total_deleted += deleted
        print(f"[purge] round 1 done · deleted {deleted} · failed {len(failures)}",
              file=sys.stderr, flush=True)

    # 3) 多轮重试
    for round_idx in range(2, args.max_rounds + 1):
        if not failures:
            break
        print(f"[purge] round {round_idx} · sleeping {args.round_sleep}s then retrying {len(failures)} pages...",
              file=sys.stderr, flush=True)
        time.sleep(args.round_sleep)
        remaining = [sid for sid, _ in failures]
        deleted, failures = _delete_sequence(deck_id, remaining, work, args.pace,
                                              label=f"round {round_idx}")
        total_deleted += deleted
        print(f"[purge] round {round_idx} done · deleted {deleted} · remaining failures {len(failures)}",
              file=sys.stderr, flush=True)

    # 4) 清空第 1 页(如果开启且有 first_id)
    cleared_first = None
    clear_err = None
    if args.clear_first and args.keep_first and first_id:
        print(f"[purge] clearing first page {first_id} to blank...",
              file=sys.stderr, flush=True)
        ok, err = _clear_first_page(deck_id, first_id, work)
        cleared_first = ok
        if not ok:
            clear_err = err
            print(f"[purge] clear first page failed (non-fatal): {err}",
                  file=sys.stderr, flush=True)
        else:
            print(f"[purge] first page cleared to blank",
                  file=sys.stderr, flush=True)

    elapsed = round(time.monotonic() - start, 2)
    result = {
        "ok": True,
        "deck": deck_id,
        "first_page_kept": first_id if args.keep_first else None,
        "first_page_cleared": cleared_first,
        "total_deleted": total_deleted,
        "failed_count": len(failures),
        "failed_slide_ids": [sid for sid, _ in failures[:50]],
        "elapsed_sec": elapsed,
    }
    if clear_err:
        result["clear_first_error"] = clear_err
    if failures:
        result["hint"] = (
            f"仍有 {len(failures)} 页未删掉;可再跑一次:\n"
            f"  python3 purge_deck.py --deck {deck_id} --slide-ids "
            f"{','.join(sid for sid, _ in failures[:10])}{'...' if len(failures) > 10 else ''}"
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
