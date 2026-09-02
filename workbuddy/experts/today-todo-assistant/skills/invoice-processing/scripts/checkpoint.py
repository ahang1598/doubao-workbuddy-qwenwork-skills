#!/usr/bin/env python3
"""
checkpoint.py — 断点续传进度文件读写（含**重复提交防护**）

═══════════════════════════════════════════════════════════════════════════
为什么需要它
═══════════════════════════════════════════════════════════════════════════
2000 张票据到出 UI 约 19 分钟。长任务的中断有三种来源:
  ① 轮次预算软着陆主动收尾   ② 被平台截断   ③ 用户关掉客户端

CodeBuddy 官方文档**未说明** `maxTurns` 耗尽后的行为, 因此 **MUST NOT 依赖
"轮次用完平台会自动提示用户继续"** 这一未经证实的行为。续跑能力**完全**由本
脚本的进度文件保证 —— 这样三种中断方式的续跑路径完全一致, "平台是否自动提示"
变得无关紧要。

⚠️ 重复 OCR 只是浪费时间, **重复提交是真事故**(同一张票绑两次申请单)。
   所以 `stage=submitted` 的票据在 `next` / `pending_submit` 里**永不出现**。

CLI:
  python checkpoint.py --input '<JSON>'
  python checkpoint.py --input-file <path/to/input.json>

═══════════════════════════════════════════════════════════════════════════
进度文件结构
═══════════════════════════════════════════════════════════════════════════
  _tmp/session_<id>/progress.json
  {
    "session_id": "a1b2c3",
    "updated_at": 1786360000,
    "items": {
      "<md5>": { "stage": "ocr_done", "seq": 1, "updated_at": 1786359900 }
    }
  }

阶段是**单调递进**的(索引越大越靠后), `mark` 只会前进不会倒退:

  none → ocr_done → matched → uploaded → submitted

⚠️ 键是票据 PDF 的 `md5`, 不是文件路径 —— 用户换个目录重传同一份文件,
   仍应被识别为"已处理过"。md5 在光栅化之前对本地原文件计算, 不为了算md5
   而提前上传。

═══════════════════════════════════════════════════════════════════════════
四个 action
═══════════════════════════════════════════════════════════════════════════
① init—— 建/读进度文件, 返回当前统计
  { "action": "init", "progress_file": "./_tmp/session_x/progress.json",
    "session_id": "x" }
  ⚠️ 跨会话保护: 若既有 progress.json 记录 session_id 与本次传入不一致,
     自动清空旧 items(返回 session_mismatch: true), 杜绝跨会话误复用
     uploaded/submitted 状态(否则会跳过重传/重匹配, 甚至重复提交)。

② mark   —— 标记一批票据到达某阶段(**每阶段完成即调用**)
  { "action": "mark", "progress_file": "...", "stage": "ocr_done",
    "items": [ { "md5": "ab12...", "seq": 1 } ] }

③ next   —— 给定全量清单, 返回各阶段待处理子集(续跑用)
  { "action": "next", "progress_file": "...",
    "items": [ { "md5": "...", "seq": 1, "pdf_path": "..." } ] }
  出参:
  { "success": true,
    "pending_ocr":    [ ... ],   // stage < ocr_done
    "pending_match":  [ ... ],   // stage == ocr_done
    "pending_upload": [ ... ],   // stage == matched
    "pending_submit": [ ... ],   // stage == uploaded  ← submitted 的**绝不**在此
    "already_submitted": [ "<md5>", ... ],
    "summary": { "total": 2000, "ocr_done": 2000, "matched": 1400,
                 "uploaded": 1400, "submitted": 0 } }

④ guard  —— 提交前的**重复提交防护闸门**
  { "action": "guard", "progress_file": "...",
    "items": [ { "md5": "...", "application_number": "AP001" } ] }
  出参:
  { "success": true, "allowed": [ ... ], "blocked": [ ... ],
    "blocked_reason": "该票据已提交过,拒绝重复提交" }

  ⛔ SOP 在调`update_tickets` **之前必须**过一遍 guard, 只提交 `allowed`。

参考: ../SKILL.md「Checkpoint 断点续传」章节
"""
import argparse
import json
import os
import sys
import time
from typing import Dict, List, Optional

STAGES = ["ocr_done", "matched", "uploaded", "submitted"]
STAGE_INDEX = {name: i for i, name in enumerate(STAGES)}
BLOCKED_REASON = "该票据已提交过, 拒绝重复提交"


# ---------------------------------------------------------------------------
# 读写
# ---------------------------------------------------------------------------
def load_progress(path: str) -> dict:
    if not path or not os.path.exists(path):
        return {"session_id": "", "updated_at": 0, "items": {}}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        # 进度文件损坏时**不静默清空**, 交由上层决定
        raise
    if not isinstance(data, dict):
        return {"session_id": "", "updated_at": 0, "items": {}}
    data.setdefault("items", {})
    if not isinstance(data["items"], dict):
        data["items"] = {}
    return data


def save_progress(path: str, data: dict) -> str:
    directory = os.path.dirname(os.path.abspath(path))
    if directory:
        os.makedirs(directory, exist_ok=True)
    data["updated_at"] = int(time.time())
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)      # 原子替换, 防写一半被中断
    return os.path.abspath(path)


def stage_of(progress: dict, md5: str) -> Optional[str]:
    entry = (progress.get("items") or {}).get(md5)
    if isinstance(entry, dict):
        return entry.get("stage")
    if isinstance(entry, str):
        return entry
    return None


def stage_rank(stage: Optional[str]) -> int:
    """未记录 = -1; 未知阶段名也按 -1 处理(不因脏数据跳过处理)。"""
    return STAGE_INDEX.get(stage, -1) if stage else -1


def _summary(progress: dict, total: int) -> dict:
    counts = {name: 0 for name in STAGES}
    for md5 in (progress.get("items") or {}):
        rank = stage_rank(stage_of(progress, md5))
        for name in STAGES:
            if rank >= STAGE_INDEX[name]:
                counts[name] += 1
    out = {"total": total}
    out.update(counts)
    return out


# ---------------------------------------------------------------------------
# action 实现
# ---------------------------------------------------------------------------
def do_init(input_data: dict) -> dict:
    path = input_data.get("progress_file")
    if not path:
        return {"success": False, "error": "缺少 progress_file"}
    progress = load_progress(path)
    old_sid = (progress.get("session_id") or "").strip()
    new_sid = str(input_data.get("session_id") or "").strip()
    session_mismatch = False
    if old_sid and new_sid and old_sid != new_sid:
        # 跨会话: 旧进度里的 md5→stage(含 uploaded/submitted) 不可信, 必须清空,
        # 否则会把"他会话的已上传/已提交"误判为本会话可复用状态, 导致跳过
        # 重传/重匹配, 甚至对已提交票据重复提交(真事故)。
        progress["items"] = {}
        session_mismatch = True
    if new_sid:
        progress["session_id"] = new_sid
    saved = save_progress(path, progress)
    return {
        "success": True,
        "action": "init",
        "progress_file": saved,
        "session_id": progress.get("session_id") or "",
        "session_mismatch": session_mismatch,
        "known_items": len(progress.get("items") or {}),
        "summary": _summary(progress, len(progress.get("items") or {})),
    }


def do_mark(input_data: dict) -> dict:
    path = input_data.get("progress_file")
    stage = str(input_data.get("stage") or "")
    items = input_data.get("items") or []
    if not path:
        return {"success": False, "error": "缺少 progress_file"}
    if stage not in STAGE_INDEX:
        return {"success": False, "error": f"stage 非法: {stage!r}, 只支持 {'/'.join(STAGES)}"}
    if not items:
        return {"success": False, "error": "items 为空, 无可标记的票据"}

    progress = load_progress(path)
    bucket: Dict[str, dict] = progress.setdefault("items", {})
    now = int(time.time())
    advanced, kept = [], []

    for item in items:
        md5 = str((item or {}).get("md5") or "").strip() if isinstance(item, dict) else str(item or "").strip()
        if not md5:
            continue
        current = stage_rank(stage_of(progress, md5))
        if current >= STAGE_INDEX[stage]:
            # 阶段单调递进,绝不倒退(否则会把submitted 打回去 → 重复提交风险)
            kept.append(md5)
            continue
        entry = bucket.get(md5) if isinstance(bucket.get(md5), dict) else {}
        entry = dict(entry)
        entry["stage"] = stage
        entry["updated_at"] = now
        if isinstance(item, dict) and item.get("seq") is not None:
            entry["seq"] = item.get("seq")
        bucket[md5] = entry
        advanced.append(md5)

    saved = save_progress(path, progress)
    return {
        "success": True,
        "action": "mark",
        "stage": stage,
        "progress_file": saved,
        "advanced": len(advanced),
        "kept_not_regressed": len(kept),
        "summary": _summary(progress, len(bucket)),
    }


def do_next(input_data: dict) -> dict:
    path = input_data.get("progress_file")
    items = input_data.get("items") or []
    if not path:
        return {"success": False, "error": "缺少 progress_file"}
    if not items:
        return {"success": False, "error": "items 为空, 无全量清单可比对"}

    progress = load_progress(path)
    pending_ocr, pending_match, pending_upload, pending_submit = [], [], [], []
    already_submitted: List[str] = []

    for item in items:
        md5 = str((item or {}).get("md5") or "").strip()
        if not md5:
            pending_ocr.append(item)          # 没有 md5 无法判定, 保守当作全新
            continue
        rank = stage_rank(stage_of(progress, md5))
        if rank < STAGE_INDEX["ocr_done"]:
            pending_ocr.append(item)
        elif rank < STAGE_INDEX["matched"]:
            pending_match.append(item)
        elif rank < STAGE_INDEX["uploaded"]:
            pending_upload.append(item)
        elif rank < STAGE_INDEX["submitted"]:
            pending_submit.append(item)
        else:
            already_submitted.append(md5)     # ⛔ 绝不进 pending_submit

    return {
        "success": True,
        "action": "next",
        "pending_ocr": pending_ocr,
        "pending_match": pending_match,
        "pending_upload": pending_upload,
        "pending_submit": pending_submit,
        "already_submitted": already_submitted,
        "counts": {
            "pending_ocr": len(pending_ocr),
            "pending_match": len(pending_match),
            "pending_upload": len(pending_upload),
            "pending_submit": len(pending_submit),
            "already_submitted": len(already_submitted),
        },
        "summary": _summary(progress, len(items)),
    }


def do_guard(input_data: dict) -> dict:
    """提交前闸门: 已submitted 的票据一律拦下。"""
    path = input_data.get("progress_file")
    items = input_data.get("items") or []
    if not path:
        return {"success": False, "error": "缺少 progress_file"}
    if not items:
        return {"success": False, "error": "items 为空, 无可提交的票据"}

    progress = load_progress(path)
    allowed, blocked = [], []
    for item in items:
        md5 = str((item or {}).get("md5") or "").strip()
        if md5 and stage_rank(stage_of(progress, md5)) >= STAGE_INDEX["submitted"]:
            blocked.append(item)
        else:
            allowed.append(item)

    return {
        "success": True,
        "action": "guard",
        "allowed": allowed,
        "blocked": blocked,
        "allowed_count": len(allowed),
        "blocked_count": len(blocked),
        "blocked_reason": BLOCKED_REASON if blocked else "",
    }


_ACTIONS = {"init": do_init, "mark": do_mark, "next": do_next, "guard": do_guard}


def process(input_data: dict) -> dict:
    action = str(input_data.get("action") or "").strip().lower()
    handler = _ACTIONS.get(action)
    if not handler:
        return {
            "success": False,
            "error": f"action 非法: {action!r}, 只支持 {'/'.join(_ACTIONS)}",
        }
    try:
        return handler(input_data)
    except (OSError, json.JSONDecodeError) as e:
        return {"success": False, "error": f"进度文件读写失败: {e}"}
    except Exception as e:  # noqa: BLE001
        return {"success": False, "error": f"{action} 执行失败: {e}"}


def main():
    # ⚠️ Windows 实测: stdout 为管道时用 locale 编码(GBK), 中文 JSON 会写成 GBK 字节,
    #    UTF-8 读取方直接 UnicodeDecodeError。必须显式改 UTF-8。
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="JSON 格式的入参")
    parser.add_argument("--input-file", dest="input_file", help="入参 JSON 文件路径")
    args = parser.parse_args()

    if not args.input and not args.input_file:
        print(json.dumps({"success": False, "error": "必须提供 --input 或 --input-file"}), flush=True)
        sys.exit(1)

    try:
        if args.input_file:
            with open(args.input_file, "r", encoding="utf-8") as f:
                input_data = json.load(f)
        else:
            input_data = json.loads(args.input)
    except (json.JSONDecodeError, OSError) as e:
        print(json.dumps({"success": False, "error": f"入参非合法 JSON: {e}"}), flush=True)
        sys.exit(1)

    result = process(input_data)
    print(json.dumps(result, ensure_ascii=False), flush=True)
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
