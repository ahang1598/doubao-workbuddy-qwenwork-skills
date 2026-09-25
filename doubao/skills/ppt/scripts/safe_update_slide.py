#!/usr/bin/env python3
"""safe_update_slide.py — write-guard 包装 `lark-cli slides +update-slide`。

四步事务（**目标页级**并发保护，不是 presentation 级）：
1. `+xml-get --slide-id <sid>` 拉服务端**这一页**的当前 XML。
2. 语义 diff：把服务端当前 XML 与本地缓存 XML 都解析成元素签名（element_count / by_type /
   id → type / id → text_preview），比较签名是否一致。
   · **一致** → 说明这一页从本地缓存以来没被别人改过 → 走 3。
   · **不一致** → 说明这一页在你上次同步之后被改过 → abort，用服务端最新版覆盖本地。
3. 裸调 `+update-slide`（默认 revision-id=-1；不要显式传 rev，飞书 API 的 rev 是 presentation 级
   不是页级，且传旧 rev 会以旧快照重建反而更糟）。
4. 立即 `+xml-get --slide-id <sid>` 回读，同步本地缓存。

不用 revision_id 的原因：
- revision_id 是 presentation 级 —— MainAgent 在别的页 `+add-slide` 也会让整个 rev +1
- 但你要动的这一页并没有变，用 rev 做基线会大量误报 stale_local
- 唯一可靠的基线是"这一页内容的语义指纹"本身

CLI:
    python3 safe_update_slide.py \
        --presentation <token_or_url> \
        --slide-id <sid> \
        --content <path/to/target.xml> \
        --local-cache <path/to/slides/slide-NN.xml>

Exit codes:
    0  status=ok             写入成功
    2  status=abort          本地过期或缺基线，本地已被覆盖为服务端最新版
    3  status=error          server_rejected / xml_get_failed / update_failed / content_not_found

stdout 一律输出结构化 JSON，供 agent 直接解析。message 字段是自然语言诊断，写给弱模型看。
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Any


LARK_CLI = os.environ.get("LARK_CLI", "lark-cli")
XML_GET_TIMEOUT_SEC = 60
UPDATE_TIMEOUT_SEC = 120


def _run(
    argv: list[str], timeout: int, cwd: str | None = None
) -> tuple[int, str, str]:
    """Run subprocess and return (returncode, stdout, stderr).

    cwd 用于绕开 `lark-cli slides +xml-get --output` 「只接受 cwd 内相对路径」的限制：
    调用方把 cwd 设成目标目录，argv 里的 `--output` / `@content` 只放文件名。
    """
    try:
        proc = subprocess.run(
            argv,
            check=False,
            timeout=timeout,
            capture_output=True,
            text=True,
            cwd=cwd,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s"
    except FileNotFoundError as e:
        return 127, "", f"binary not found: {e}"


def _parse_cli_json(stdout: str) -> dict[str, Any] | None:
    """lark-cli 返回 JSON envelope on stdout；有些 shortcut 前面还有进度行，找第一个 '{'."""
    stdout = stdout.strip()
    if not stdout:
        return None
    idx = stdout.find("{")
    if idx < 0:
        return None
    try:
        return json.loads(stdout[idx:])
    except json.JSONDecodeError:
        return None


def xml_get_slide(
    presentation: str, sid: str, output_path: Path
) -> tuple[bool, str]:
    """Fetch a single slide's latest XML to output_path. Returns (ok, raw_stdout).

    `lark-cli slides +xml-get --output` 老版本只接受当前目录内的**相对路径**，绝对路径
    会被 CLI 直接拒。所以把子进程 cwd 设成 output_path.parent，`--output` 只传文件名。
    """
    argv = [
        LARK_CLI, "slides", "+xml-get",
        "--presentation", presentation,
        "--slide-id", sid,
        "--output", output_path.name,
        "--json",
    ]
    rc, out, err = _run(argv, XML_GET_TIMEOUT_SEC, cwd=str(output_path.parent))
    if rc != 0:
        return False, (out + "\n" + err).strip()
    envelope = _parse_cli_json(out)
    if not envelope or not envelope.get("ok"):
        return False, out
    if not output_path.exists() or output_path.stat().st_size == 0:
        return False, f"xml-get succeeded but {output_path} is empty"
    return True, out


def update_slide_raw(
    presentation: str, sid: str, content_path: Path
) -> tuple[bool, dict[str, Any] | str]:
    """裸调 update-slide, 不带 --revision-id (默认 -1). 返回 (ok, envelope_or_raw).

    默认带 --no-lint：语义 diff 已经在本脚本 Step 2 做过基线校验，服务端 lint 只会
    对预置几何/字体做二次拦截，反而误报正常写入。lark-cli < 1.0.96 没有这个 flag，
    首次遇到 `unknown flag "--no-lint"` 时自动去掉重试，保持老版本兼容。
    """
    base_argv = [
        LARK_CLI, "slides", "+update-slide",
        "--presentation", presentation,
        "--slide-id", sid,
        "--content", f"@{content_path}",
    ]
    envelope: dict[str, Any] | None = None
    out = ""
    err = ""
    for flags in (["--no-lint"], []):
        rc, out, err = _run(base_argv + flags, UPDATE_TIMEOUT_SEC)
        envelope = _parse_cli_json(out)
        if envelope and envelope.get("ok"):
            return True, envelope
        if flags and _is_unknown_flag_error(envelope, out + err, "--no-lint"):
            # 老版本 CLI，去掉 --no-lint 重跑
            continue
        return False, envelope or (out + "\n" + err).strip()
    return False, envelope or (out + "\n" + err).strip()


def _is_unknown_flag_error(
    envelope: dict[str, Any] | None, raw_text: str, flag: str
) -> bool:
    """判断 CLI 是否因为不认识 `flag` 而报错（区分于服务端拒收）."""
    if envelope:
        err = envelope.get("error") or {}
        if err.get("subtype") == "invalid_argument":
            msg = err.get("message") or ""
            if "unknown flag" in msg and flag in msg:
                return True
            for p in err.get("params") or []:
                if p.get("name") == flag and p.get("reason") == "unknown flag":
                    return True
    if "unknown flag" in raw_text and flag in raw_text:
        return True
    return False


# ─── XML semantic signature ───

SML_NS_SUFFIX = "/sml/2.0"


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def summarize_elements(xml_path: Path) -> dict[str, Any]:
    """Extract a lightweight, id-independent element fingerprint from a slide XML.

    **不用 id 做匹配键**：MainAgent 首次落 XML 时元素不带 id（SKILL.md 硬红线：ID 由服务端分配），
    服务端 `+xml-get` 回来的 XML 每个元素都会分配 id，两边 id 集合天然不同——上一版用 id 做键
    100% 误报 stale_local。

    改用**位置排序后的元素序列**：每个元素表示为 (kind, x, y, w, h, text_hash)，然后按
    (y, x, kind) 稳定排序。两份 XML 语义等价当且仅当排序后的序列相等。

    刻意忽略：
    - 属性顺序（服务端可能规整）
    - 空白 / xml declaration
    - element id（服务端分配，语义无关）
    - 无关的默认属性（服务端可能补 presetHandlers="0" 等）

    Returns:
        {
          "element_count": int,
          "by_type": {"shape:text": 5, "shape:rect": 2, "img": 1, ...},
          "elements": [
              {"kind": "shape:text", "x": "60", "y": "60", "w": "400", "h": "30",
               "text": "旧标题"},
              ...
          ]   # 已按 (y, x, kind) 排序
        }
    """
    result = {
        "element_count": 0,
        "by_type": {},
        "elements": [],
    }
    if not xml_path.exists():
        return result
    try:
        root = ET.parse(xml_path).getroot()
    except ET.ParseError:
        return result
    slides = []
    if _local_name(root.tag) == "presentation":
        slides = [child for child in root if _local_name(child.tag) == "slide"]
    elif _local_name(root.tag) == "slide":
        slides = [root]
    if not slides:
        return result
    slide = slides[0]
    raw: list[dict[str, Any]] = []
    for data_node in slide:
        if _local_name(data_node.tag) != "data":
            continue
        for child in data_node:
            name = _local_name(child.tag)
            if name == "shape":
                sub = child.get("type") or "shape"
                kind = f"shape:{sub}"
            else:
                kind = name
            entry = {
                "kind": kind,
                "x": _normalize_number(child.get("topLeftX", "0")),
                "y": _normalize_number(child.get("topLeftY", "0")),
                "w": _normalize_number(child.get("width", "0")),
                "h": _normalize_number(child.get("height", "0")),
                "text": " ".join("".join(child.itertext()).split())[:60],
            }
            raw.append(entry)
            result["element_count"] += 1
            result["by_type"][kind] = result["by_type"].get(kind, 0) + 1
    # 稳定排序：按 y、然后 x、然后 kind、然后 text —— 提交顺序与服务端返回顺序可能不同
    def sort_key(e: dict[str, Any]) -> tuple:
        try:
            return (float(e["y"]), float(e["x"]), e["kind"], e["text"])
        except ValueError:
            return (0.0, 0.0, e["kind"], e["text"])
    result["elements"] = sorted(raw, key=sort_key)
    return result


def _normalize_number(v: str) -> str:
    """把 "60" / "60.0" / "60.00" 归一化到同一个形式，避免服务端 float roundtrip 误报."""
    v = (v or "").strip()
    if not v:
        return "0"
    try:
        f = float(v)
        if f == int(f):
            return str(int(f))
        return f"{f:.3f}".rstrip("0").rstrip(".")
    except ValueError:
        return v


def signatures_equal(
    local_sig: dict[str, Any], server_sig: dict[str, Any]
) -> tuple[bool, str]:
    """两份签名语义等价 → (True, "")；不等 → (False, 简短原因描述).

    比较 id-independent 的元素序列。已按 (y, x, kind, text) 排序，可直接逐个对齐。
    """
    if local_sig["element_count"] != server_sig["element_count"]:
        return False, (
            f"元素数 {local_sig['element_count']} → {server_sig['element_count']}"
        )
    if local_sig["by_type"] != server_sig["by_type"]:
        return False, (
            f"元素类型分布变化: 本地={local_sig['by_type']} 服务端={server_sig['by_type']}"
        )
    for i, (le, se) in enumerate(zip(local_sig["elements"], server_sig["elements"])):
        if le["kind"] != se["kind"]:
            return False, f"元素[{i}] 类型: {le['kind']} → {se['kind']}"
        if (le["x"], le["y"], le["w"], le["h"]) != (se["x"], se["y"], se["w"], se["h"]):
            return False, (
                f"元素[{i}] ({le['kind']}) 几何: "
                f"{le['x']},{le['y']},{le['w']},{le['h']} → "
                f"{se['x']},{se['y']},{se['w']},{se['h']}"
            )
        if le["text"] != se["text"]:
            return False, (
                f'元素[{i}] ({le["kind"]}) 文本: "{le["text"][:30]}" → "{se["text"][:30]}"'
            )
    return True, ""


def describe_changes(local_sig: dict[str, Any], server_sig: dict[str, Any]) -> str:
    """Human-readable diff hint (更详细版, 用于 stale_local 消息里).

    对已按 (y, x, kind, text) 排序的元素序列做**多重集差异**：以 (kind, x, y, w, h) 为对齐键
    找出"新增元素" / "删除元素"；对相同键的对，检查文本是否变化。
    """
    def key(e: dict[str, Any]) -> tuple:
        return (e["kind"], e["x"], e["y"], e["w"], e["h"])

    local_bag: dict[tuple, list[str]] = {}
    for e in local_sig["elements"]:
        local_bag.setdefault(key(e), []).append(e["text"])
    server_bag: dict[tuple, list[str]] = {}
    for e in server_sig["elements"]:
        server_bag.setdefault(key(e), []).append(e["text"])

    added: list[tuple] = []
    removed: list[tuple] = []
    text_changes: list[tuple] = []
    for k in set(local_bag) | set(server_bag):
        lt = local_bag.get(k, [])
        st = server_bag.get(k, [])
        # 按位置成对
        for i in range(max(len(lt), len(st))):
            a = lt[i] if i < len(lt) else None
            b = st[i] if i < len(st) else None
            if a is None:
                added.append((k, b))
            elif b is None:
                removed.append((k, a))
            elif a != b:
                text_changes.append((k, a, b))

    parts = []
    delta = server_sig["element_count"] - local_sig["element_count"]
    parts.append(
        f"元素数 {local_sig['element_count']} → {server_sig['element_count']} "
        f"({'+' if delta >= 0 else ''}{delta})"
    )
    if added:
        types = Counter(k[0] for k, _ in added)
        parts.append(f"新增 {len(added)} 个元素: {dict(types)}")
        for k, t in added[:2]:
            parts.append(f'  + {k[0]} @({k[1]},{k[2]}) "{(t or "")[:30]}"')
    if removed:
        types = Counter(k[0] for k, _ in removed)
        parts.append(f"删除 {len(removed)} 个元素: {dict(types)}")
        for k, t in removed[:2]:
            parts.append(f'  - {k[0]} @({k[1]},{k[2]}) "{(t or "")[:30]}"')
    if text_changes:
        parts.append(f"文本改动 {len(text_changes)} 处")
        for k, a, b in text_changes[:3]:
            parts.append(f'  [{k[0]} @({k[1]},{k[2]})] "{(a or "")[:30]}" → "{(b or "")[:30]}"')
    if not (added or removed or text_changes) and delta == 0:
        parts.append("(无显著差异 · 可能只是属性顺序或服务端默认值补齐)")
    return "；".join(parts)


# ─── main flow ───


def run_guarded(
    presentation: str,
    sid: str,
    content: Path,
    local_cache: Path,
) -> dict[str, Any]:
    server_snapshot = local_cache.parent / (
        local_cache.stem + "._server_now" + local_cache.suffix
    )

    # ── Step 1: pull server latest for this slide ──
    ok, raw = xml_get_slide(presentation, sid, server_snapshot)
    if not ok:
        server_snapshot.unlink(missing_ok=True)
        return {
            "status": "error",
            "reason": "xml_get_failed",
            "message": (
                f"步 1 拉取服务端最新版失败：`+xml-get --slide-id {sid}` 没有返回可解析的 JSON 或输出文件为空。"
                "常见原因：presentation token 错、slide_id 已被删除、网络问题、lark-cli 未鉴权。"
                f"下一步：手动跑一次 `lark-cli slides +xml-get --presentation <...> --slide-id {sid} --output /tmp/t.xml`"
                "查错误码；本次修改未提交，本地缓存未变。"
                f"原始输出片段: {str(raw)[:300]}"
            ),
            "presentation": presentation,
            "slide_id": sid,
        }

    # ── Step 2a: no baseline (local cache missing) ──
    if not local_cache.exists():
        shutil.move(str(server_snapshot), str(local_cache))
        return {
            "status": "abort",
            "reason": "no_baseline",
            "message": (
                f"本地缓存 {local_cache.name} 不存在。已把服务端 slide_id={sid} 覆盖到本地。"
                f"下一步:Read 本地文件 → 在此基础上重做修改 → 再次调用 safe_update_slide.py。"
            ),
            "presentation": presentation,
            "slide_id": sid,
            "local_xml_updated": str(local_cache),
        }

    # ── Step 2b: semantic diff ──
    try:
        server_sig = summarize_elements(server_snapshot)
        local_sig = summarize_elements(local_cache)
    except Exception as e:
        server_snapshot.unlink(missing_ok=True)
        return {
            "status": "error",
            "reason": "signature_extraction_failed",
            "message": (
                f"步 2 解析 XML 提取语义签名失败: {e}。"
                f"检查本地 {local_cache.name} 或服务端返回的 XML 是否为合法 SML 2.0。"
                "本次修改未提交。"
            ),
        }

    equal, mismatch_reason = signatures_equal(local_sig, server_sig)
    if not equal:
        hint = describe_changes(local_sig, server_sig)
        shutil.move(str(server_snapshot), str(local_cache))
        return {
            "status": "abort",
            "reason": "stale_local",
            "message": (
                f"本地 {local_cache.name} 与服务端 slide_id={sid} 不一致 · {mismatch_reason}。"
                f"变化摘要:{hint}。已把服务端最新版覆盖到本地。"
                f"下一步:Read 新本地文件 → 判断 (A) 别人改动正交 → 合并再调;"
                f"(B) 已被别人改好 → 落 log skip;(C) 别人改坏了 → 汇报给 MainAgent。"
                f"不要重跑旧 XML。"
            ),
            "presentation": presentation,
            "slide_id": sid,
            "mismatch_reason": mismatch_reason,
            "diff_hint": hint,
            "local_xml_updated": str(local_cache),
        }

    # 一致：清掉临时 snapshot
    server_snapshot.unlink(missing_ok=True)

    # ── Step 3: real write ──
    ok, envelope_or_raw = update_slide_raw(presentation, sid, content)
    if not ok:
        code, err_hint = "", ""
        if isinstance(envelope_or_raw, dict):
            code = envelope_or_raw.get("code") or (envelope_or_raw.get("error", {}) or {}).get("code", "")
            err_hint = (envelope_or_raw.get("msg") or (envelope_or_raw.get("error", {}) or {}).get("message", ""))
            raw_dump = json.dumps(envelope_or_raw, ensure_ascii=False)[:500]
        else:
            raw_dump = str(envelope_or_raw)[:500]
        return {
            "status": "error",
            "reason": "update_failed",
            "message": (
                f"步 3 提交 +update-slide 被服务端拒绝，错误码 {code or '未知'}。"
                f"服务端消息：{err_hint or '（无）'}。"
                "常见原因："
                "3350001 = XML 结构非法 / 缺 `<content/>` / 坐标越界 / slide_id 已被删除；"
                "3350002 = revision-id 传了不存在的版本（本脚本默认不传，一般不该出现）。"
                f"本次修改未提交，本地缓存也未变。"
                "下一步：按 `references/workflow/error-handling.md` 查错误码，先修 XML 再重试；**不要盲目重试原样命令**。"
                f"原始响应片段：{raw_dump}"
            ),
            "presentation": presentation,
            "slide_id": sid,
            "raw_response": envelope_or_raw if isinstance(envelope_or_raw, dict) else raw_dump,
        }

    # ── Step 4: post-write sync (回读一次让本地跟服务端保持一致) ──
    ok2, raw2 = xml_get_slide(presentation, sid, local_cache)
    if not ok2:
        return {
            "status": "ok_but_sync_failed",
            "reason": "post_write_xml_get_failed",
            "message": (
                f"步 3 +update-slide 已成功，但步 4 回读同步本地缓存失败：{str(raw2)[:200]}。"
                "本地 XML 缓存现在处于过期状态，下次别人基于它改会撞 stale_local。"
                f"下一步：手动跑一次 `lark-cli slides +xml-get --slide-id {sid} --output {local_cache}` 修复本地缓存。"
            ),
            "presentation": presentation,
            "slide_id": sid,
        }
    return {
        "status": "ok",
        "message": (
            f"整页覆盖成功。slide_id={sid} 已更新，本地 {local_cache.name} 已同步到服务端最新版。可以进入下一页。"
        ),
        "presentation": presentation,
        "slide_id": sid,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="write-guard 包装 `lark-cli slides +update-slide`，"
        "对目标页做语义级 diff → 写入 → 回读同步，防并发覆盖。"
    )
    ap.add_argument("--presentation", required=True, help="presentation token / URL")
    ap.add_argument("--slide-id", required=True, help="目标页 slide_id")
    ap.add_argument("--content", required=True, help="本次要写入的目标 XML 文件路径")
    ap.add_argument(
        "--local-cache",
        required=True,
        help="共享本地缓存路径（如 slides/slide-05.xml）。记录你上次读到的这一页状态，用作语义 diff 基线。",
    )
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    content = Path(args.content).resolve()
    local_cache = Path(args.local_cache).resolve()
    if not content.exists():
        print(
            json.dumps(
                {
                    "status": "error",
                    "reason": "content_not_found",
                    "message": f"--content 指向的文件不存在: {content}",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 3
    local_cache.parent.mkdir(parents=True, exist_ok=True)

    result = run_guarded(args.presentation, args.slide_id, content, local_cache)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    status = result.get("status")
    if status == "ok":
        return 0
    if status == "abort":
        return 2
    return 3


if __name__ == "__main__":
    raise SystemExit(main())