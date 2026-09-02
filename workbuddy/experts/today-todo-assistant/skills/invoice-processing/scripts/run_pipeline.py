#!/usr/bin/env python3
"""
run_pipeline.py — 票据处理单脚本编排器（full 单模式）

定位: 把 invoice-processing 的「本地处理 → 远程匹配 → 组装 UiReq」
      全链路合并为一个脚本, 单次调用 O(1) 跑完。agent 侧只剩三件事:
        1. 把用户给的 PDF 链接写入 manifest.json
        2. 调一次 `python run_pipeline.py --input-file manifest.json`
        3. 用落盘的 `ui_req.json` 调 `build_invoice_match_ui_params.py` 得到 `data_cache_id`,
           再用 `{caller_expert_id, data_cache_id}` 调 open_invoice_match_review_ui 呼起页面

      提交在 UI 内直接完成;「提交票据到远程」步骤的剔除已提交项由
      title_normalizer.py 的 `prune` mode 承担(不在本脚本)。

⚠️ MCP 调用边界（统一走 skills/_common/mcp_client.py, 已与 alert-expert 同源校验）:
      get_project_list / list_pending_tickets 由本脚本**内部**直接调
      gongyi-open-mcp（经 mcp_client 直连, 自动握手 + 鉴权 + 重试）,
      因此真正的「一次性做完」成立, 不需要 agent 显式中转这两个 MCP。
      ⛔ 仅 open_invoice_match_review_ui 呼起页面必须由 agent 调（脚本无法替代）。

═══════════════════════════════════════════════════════════════
manifest 格式
═══════════════════════════════════════════════════════════════
全量:
  {
    "mode": "full",
    "org_no": "44050126",
    "session_id": "a1b2c3",
    "workspace": "./_tmp/session_a1b2c3",
    "pdf_paths": ["/abs/a.pdf", "/abs/b.pdf"],
    "dpi": 200, "raster_workers": 8, "ocr_workers": 4,
    "ocr_threads_per_worker": 2, "upload_workers": 16,
    "logical_batch_size": 20,             // 可选, 最大 20
    "progress_log": "./_tmp/session_a1b2c3/progress.log"  // 可选, 进度日志文件路径
  }
═══════════════════════════════════════════════════════════════
stdout 输出（一行 JSON）
═══════════════════════════════════════════════════════════════
  进度日志（可选, 由 manifest.progress_log 指定路径）:
    脚本在「每个处理节点进入/完成」以及「节点内分批(光栅化/OCR 实时轮询、
    远程匹配每批)」时, 向该文件追加一行用户可读的中文进度文案并立即 flush, 例如:
      🔍 OCR识别阶段：已处理 10/100
      🎉 全部完成：已识别、匹配并上传原件，准备呼起确认页
      ❌ 处理失败：<原因>
    agent 侧定时 `tail -n 1 <progress_log>` 读取末行原样转述给用户, 结束再读全量核对。
    ⛔ 进度日志走独立文件, 不影响 stdout 的最终 JSON(仍只在其一行输出)。

  { "success": true, "mode": "full",
    "ui_req": { ... 完整 UiReq, agent 原样传给 open_invoice_match_review_ui ... },
    "summary": { "total": N, "matched": M, "failed": K, "failed_breakdown": {...} },
    "duplicates": [...], "warnings": [...], "workspace": "...", ... }
  ⛔ 失败: { "success": false, "error_code": "pipeline_failed|auth_failed", "message": "...", ... }

  落盘（与 stdout 同源，防止大 ui_req 经后台任务 stdout 被截断）:
    <workspace>/result.json  —— 完整最终 JSON（含 ui_req / 阶段耗时等）
    <workspace>/ui_req.json  —— 仅 ui_req，便于 agent 直接读取后原样呼起 UI
  agent 侧优先从文件读取 ui_req，⛔ 不得依赖可能被截断的后台任务 stdout。
"""
import argparse
import contextlib
import hashlib
import io
import json
import os
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# 同目录脚本（无论 cwd 在哪都能 import）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# _common 公共库（mcp_client / observe_bootstrap 等）
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "_common")))

import pdf_to_images            # noqa: E402
import local_ocr_batch          # noqa: E402
import amount_conversion        # noqa: E402
import project_matcher          # noqa: E402
import title_normalizer         # noqa: E402
import checkpoint               # noqa: E402
import cos_batch_upload as cb   # noqa: E402  复用其极简 MCP client + COS 上传
from observe_bootstrap import (  # noqa: E402
    galileo_observer,
    expert_version,
    galileo_topic,
    record_stage_timings,
)


LOGICAL_BATCH_SIZE = 20


# ---------------------------------------------------------------------------
# 通用辅助
# ---------------------------------------------------------------------------
class _StageError(Exception):
    """阶段失败：携带稳定 error_code 与附加诊断字段（install_log 等）。

    message 只放简短人话；install_log 这类可能含本机路径/命令输出的诊断信息，
    通过独立字段透传，绝不拼进 message，避免污染埋点上报（隐私）。
    """
    def __init__(self, error_code, message, install_log=None):
        super().__init__(message)
        self.error_code = error_code
        self.install_log = install_log


def _fail(error, extra=None, error_code="pipeline_failed"):
    out = {"success": False, "error_code": error_code, "message": error}
    if extra:
        out.update(extra)
    # 鉴权失败（need_refresh）时归类为 auth_failed，供埋点/告警聚合
    if out.get("need_refresh"):
        out["error_code"] = "auth_failed"
    return out


def _write_json(path, obj):
    """在目标目录内原子写 JSON，避免进程中断留下半个结果文件。"""
    directory = os.path.dirname(os.path.abspath(path))
    if directory:
        os.makedirs(directory, exist_ok=True)
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=directory or None,
            prefix=f".{os.path.basename(path)}.", suffix=".tmp", delete=False,
        ) as f:
            tmp_path = f.name
            json.dump(obj, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        raise


def _load_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


def _timed(fn, *args, **kwargs):
    started = time.monotonic()
    value = fn(*args, **kwargs)
    return value, int((time.monotonic() - started) * 1000)


def _checkpoint_mark(progress_file, stage, items):
    payload = [
        {"md5": str(i.get("md5") or ""), "seq": i.get("seq")}
        for i in items if i.get("md5")
    ]
    if not payload:
        return
    out = checkpoint.process({
        "action": "mark", "progress_file": str(progress_file),
        "stage": stage, "items": payload,
    })
    if not out.get("success"):
        raise RuntimeError(f"checkpoint mark {stage} 失败: {out.get('error')}")


def _stage_at_least(progress, md5, stage):
    current = checkpoint.stage_of(progress, str(md5 or ""))
    return checkpoint.STAGE_INDEX.get(current, -1) >= checkpoint.STAGE_INDEX[stage]


def _try_write_result(result):
    """把最终结果 JSON 落盘，避免大 ui_req 经后台任务 stdout 被截断导致呼起 UI 失败。

    落盘到 result.get('workspace') 或当前目录，文件名 result.json（完整结果，含 ui_req）
    与 ui_req.json（仅 ui_req 便于 agent 直接读取）。落盘失败仅记 stderr，
    不影响 stdout 输出。
    """
    try:
        out_dir = str(result.get("workspace") or os.getcwd())
        _write_json(os.path.join(out_dir, "result.json"), result)
        ui_req = result.get("ui_req")
        if ui_req is not None:
            _write_json(os.path.join(out_dir, "ui_req.json"), ui_req)
    except Exception as e:  # noqa: BLE001
        sys.stderr.write(f"[warn] 落盘最终结果 JSON 失败: {e}\n")
        sys.stderr.flush()


def _progress(log_path, step, total, msg):
    """追加一行进度到日志文件。

    每次都重新打开文件并 flush, 确保外部(agent 定时 tail)随时能读到最新一行,
    而不是攒在缓冲区里直到脚本结束。log_path 为空时静默跳过。
    """
    if not log_path:
        return
    # 直接写出用户可读的中文进度文案（agent 会 tail -n 1 原样转述给用户）
    line = f"{msg}\n"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line)
        f.flush()


def _count_files(directory, ext):
    d = Path(str(directory))
    if not d.exists():
        return 0
    ext = ext.lower()
    return sum(1 for p in d.rglob("*") if p.is_file() and p.suffix.lower() == ext)


def _count_dirs(directory):
    d = Path(str(directory))
    if not d.exists():
        return 0
    return sum(1 for p in d.iterdir() if p.is_dir())


def _poll_progress(log_path, total, label, count_fn, stop, interval=5):
    """后台轮询线程: 定期统计已完成数并写进度, 直到 stop 置位或 done>=total。

    用于多线程阶段(光栅化 / OCR), 主线程阻塞在并行任务上, 由本线程数输出文件数
    来给出实时 k/N, 解决长任务(如 OCR 500 份)长时间无反馈的痛点。
    """
    while not stop.is_set():
        try:
            done = count_fn()
        except Exception:  # noqa: BLE001
            done = 0
        _progress(log_path, done, total, f"{label}：已处理 {done}/{total}")
        if total and done >= total:
            break
        stop.wait(interval)


def _quiet(fn, *args, **kwargs):
    """捕获同进程 stdout 噪声(第三方库/子脚本的 print), 转 stderr。"""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        result = fn(*args, **kwargs)
    noise = buf.getvalue()
    if noise.strip():
        sys.stderr.write(noise)
        sys.stderr.flush()
    return result


def md5_file(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# MCP client（统一走 skills/_common/mcp_client.py）
# ---------------------------------------------------------------------------
def _ensure_requests():
    """确保 cos_batch_upload 的 requests 全局可用（缺则自助安装）。"""
    if not cb._probe_requests():
        ok, _log = cb._try_install_requests()
        if not ok:
            raise RuntimeError("缺少 requests 且自动安装失败, 无法调用 MCP")


_MCP = None


def _mcp_client():
    """延迟导入 mcp_client（mcp_client 硬依赖 requests, 需在 _ensure_requests 之后）。"""
    global _MCP
    if _MCP is None:
        import os as _os
        import sys as _sys
        _sys.path.insert(
            0,
            _os.path.normpath(
                _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", "_common")
            ),
        )
        from mcp_client import call_mcp, _sanitize
        _MCP = (call_mcp, _sanitize)
    return _MCP


_CID = None


def _caller_expert_id():
    """延迟导入 mcp_client.CALLER_EXPERT_ID（与 _mcp_client 同理，硬依赖 requests）。

    埋点身份与 MCP 调用身份同源：独立运行时为 invoice-expert，合并进专家团后
    随 _common 重定向自动切换为专家团身份。
    """
    global _CID
    if _CID is None:
        import os as _os
        import sys as _sys
        _sys.path.insert(
            0,
            _os.path.normpath(
                _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", "_common")
            ),
        )
        from mcp_client import CALLER_EXPERT_ID as _cid
        _CID = _cid
    return _CID


def _mcp_invoke(tool, arguments, timeout=30):
    """调 MCP 工具，返回 data dict；失败抛 RuntimeError（鉴权失败由 mcp_client 直接退出）。"""
    call_mcp, _san = _mcp_client()
    r = call_mcp(tool, arguments, timeout)
    if r.get("is_error"):
        raise RuntimeError(f"MCP {tool} 调用失败: " + _san(str(r.get("text")))[:300])
    data = r.get("data")
    if data is None:
        raise RuntimeError(f"MCP {tool} 回包解析失败: " + _san(str(r.get("text")))[:300])
    return data


def _slim_project(p):
    """只保留 project_no / project_name 两字段（project_matcher 仅用这俩）。

    兼容上游别名命名: project_no↔project_id↔projectId↔id↔no,
    project_name↔projectName↔name↔title（与 project_matcher._normalize_projects 一致）。
    无项目名的不入字典。
    """
    if not isinstance(p, dict):
        return None
    pid = (p.get("project_no") or p.get("project_id")
           or p.get("projectId") or p.get("id") or p.get("no") or "")
    pname = (p.get("project_name") or p.get("projectName")
             or p.get("name") or p.get("title") or "")
    if not pname:
        return None
    return {"project_no": str(pid), "project_name": str(pname)}


def fetch_projects(timeout=30):
    """get_project_list 分页拉全机构项目库（机构由 token 绑定, 无需 org_no）。

    落盘与内存都只保留 project_no / project_name, 不存其它冗余字段。
    """
    projects, page = [], 1
    while True:
        args = {
            "page_index": page, "page_size": 2000,
            "no_sub_project": True, "is_online": True,
        }
        data = _mcp_invoke("get_project_list", args, timeout)
        lst = data.get("list") or []
        for p in lst:
            slim = _slim_project(p)
            if slim:
                projects.append(slim)
        if len(lst) < 2000:
            break
        page += 1
    return projects


def fetch_candidates(org_no, matchable, timeout=60, progress=None):
    """list_pending_tickets 分批(≤20, 串行)拉候选池, 合并 pending + success。

    matchable 每项: { title_norm, amount(int 分), project_id }
    ⛔ 严格遵守「filters ≤20 条 / 串行」硬约束（需求方铁律）。
    progress(i, total): 可选回调, 每批结束后上报批次进度。
    """
    pending, success = [], []
    req_id = 1
    total_batches = max(1, (len(matchable) + 19) // 20) if matchable else 0
    for batch_no, i in enumerate(range(0, len(matchable), 20), start=1):
        batch = matchable[i:i + 20]
        filters = [
            {"title": b["title_norm"], "amount": int(b["amount"]),
             "project_id": str(b.get("project_id") or "")}
            for b in batch
        ]
        first = filters[0]
        args = {
            "org_no": str(org_no),
            "title": first["title"],
            "amount": first["amount"],
            "project_id": first["project_id"],
            "filters": filters,
        }
        try:
            data = _mcp_invoke("list_pending_tickets", args, timeout)
        except Exception as e:  # noqa: BLE001
            # 单批失败 → 该批票据标 match_status=2, 整体不阻断
            sys.stderr.write(f"[warn] list_pending_tickets 第 {req_id} 批失败: {e}\n")
            req_id += 1
            continue
        req_id += 1
        pending.extend(data.get("pending_list") or [])
        success.extend(data.get("success_list") or [])
        if progress:
            progress(batch_no, total_batches)
    return pending, success


# ---------------------------------------------------------------------------
# 本地段: 光栅化 / OCR / 前段组装
# ---------------------------------------------------------------------------
def _rasterize(raster_items, dpi, workers):
    in_items = [
        {"pdf_path": r["pdf_path"], "output_dir": r["output_dir"]}
        for r in raster_items if r["dup_of"] is None
    ]
    out = _quiet(pdf_to_images.process, {"items": in_items, "dpi": dpi, "workers": workers})
    if not out.get("success"):
        raise _StageError(
            "rasterize_failed",
            "光栅化失败: " + str(out.get("error")),
            out.get("install_log"),
        )
    return out


def _images_for(raster_out, pdf_path):
    for res in raster_out.get("results") or []:
        if res.get("pdf_path") == pdf_path:
            return res.get("images") or res.get("image_paths") or []
    return []


def _ocr(
    raster_items,
    raster_out,
    ocr_dir,
    workers,
    result_callback=None,
    threads_per_worker=2,
):
    in_items = []
    for r in raster_items:
        if r["dup_of"] is not None:
            continue
        imgs = _images_for(raster_out, r["pdf_path"])
        in_items.append({"seq": r["seq"], "md5": r["md5"],
                         "pdf_path": r["pdf_path"], "images": imgs})
    payload = {
        "items": in_items, "output_dir": str(ocr_dir),
        "workers": workers, "threads_per_worker": threads_per_worker, "lang": "ch",
    }
    if result_callback:
        payload["_result_callback"] = result_callback
    out = _quiet(local_ocr_batch.process, payload)
    if not out.get("success"):
        raise _StageError(
            "ocr_failed",
            "OCR 失败: " + str(out.get("error")),
            out.get("install_log"),
        )
    return out


def _load_ocr(ocr_dir, seq):
    with open(os.path.join(str(ocr_dir), f"{seq}.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def _assemble_items(raster_items, raster_out, ocr_dir):
    """逐票: 读 OCR JSON → 金额换算 → 组装 all_items（含 md5 重复复用首张 OCR）。"""
    all_items, ocr_cache = [], {}
    for r in raster_items:
        seq = r["seq"]
        if r["dup_of"] is None:
            ocr = _load_ocr(ocr_dir, seq)
            ocr_cache[seq] = ocr
        else:
            ocr = ocr_cache[r["dup_of"]]
        title = str(ocr.get("title") or "")
        amt = amount_conversion.process(
            {"upper": ocr.get("amount_upper"), "lower": ocr.get("amount_lower")})
        cents = amt.get("value_cents") if amt.get("success") else None
        incomplete = (not title) or (cents is None)
        all_items.append({
            "seq": seq,
            "md5": r["md5"],
            "md5_duplicate": r["dup_of"] is not None,
            "duplicate_of_seq": r["dup_of"],
            "pdf_filename": os.path.basename(r["pdf_path"]),
            "pdf_path": r["pdf_path"],
            "invoice_url": "",
            "title": title,
            "amount": cents,
            "project_name_list": [],
            "project_id": "",
            "incomplete": incomplete,
            "_pm": {
                "project_name_raw": ocr.get("project_name_raw") or "",
                "remarks": ocr.get("remarks") or "",
                "other_info": ocr.get("other_info") or "",
            },
        })
    return all_items


def _match_projects(all_items, projects):
    """批量项目匹配: 内存传 projects（不逐票读盘）, 由 project_matcher 内部归一。"""
    for it in all_items:
        if it.get("md5_duplicate") or it.get("incomplete"):
            continue
        pm = project_matcher.process({"texts": it["_pm"], "projects": projects})
        it["project_name_list"] = pm.get("project_name_list") or []
        it["project_id"] = pm.get("project_id") or ""
        del it["_pm"]


# ---------------------------------------------------------------------------
# full 模式
# ---------------------------------------------------------------------------
def run_full(m):
    workflow_started = time.monotonic()
    org_no = str(m.get("org_no") or "")
    org_name = str(m.get("org_name") or "")
    if not org_no or not org_name:
        # manifest 未提供机构信息时自查（token 绑定机构），补齐 org_no/org_name 供展示
        try:
            _org = _mcp_invoke("get_user_and_org_info", {})
            if isinstance(_org, dict):
                org_no = org_no or str(_org.get("org_no") or "")
                org_name = org_name or str(_org.get("org_name") or "")
        except Exception:
            pass
    session_id = str(m.get("session_id") or "")
    if not session_id:
        session_id = hashlib.md5(str(m.get("pdf_paths")).encode()).hexdigest()[:8]
    ws = Path(str(m.get("workspace") or f"./_tmp/session_{session_id}"))
    ws.mkdir(parents=True, exist_ok=True)
    pdf_paths = [str(p) for p in (m.get("pdf_paths") or [])]
    if not pdf_paths:
        return _fail("manifest.pdf_paths 为空, 无可处理票据")
    dpi = int(m.get("dpi") or 200)
    raster_workers = int(m.get("raster_workers") or 8)
    ocr_workers = int(m.get("ocr_workers") or 4)
    ocr_threads_per_worker = max(
        1, min(int(m.get("ocr_threads_per_worker") or 2), 8)
    )
    upload_workers = int(m.get("upload_workers") or 16)
    logical_batch_size = max(1, min(int(m.get("logical_batch_size") or LOGICAL_BATCH_SIZE), 20))

    pages_dir = ws / "pages"
    ocr_dir = ws / "ocr"
    pages_dir.mkdir(exist_ok=True)
    ocr_dir.mkdir(exist_ok=True)
    batch_dir = ws / "batches"
    batch_dir.mkdir(exist_ok=True)
    progress_file = ws / "progress.json"
    init_out = checkpoint.process({
        "action": "init", "progress_file": str(progress_file), "session_id": session_id,
    })
    if not init_out.get("success"):
        return _fail("checkpoint 初始化失败: " + str(init_out.get("error")))

    progress_log = str(m.get("progress_log") or "")

    # 启动行（用户可读）
    _progress(progress_log, 0, 0, f"🚀 票据处理已启动，本批共 {len(pdf_paths)} 张")
    stage_elapsed = {
        "md5": 0, "rasterize": 0, "ocr": 0, "project_fetch": 0,
        "project_match": 0, "remote_match": 0, "upload": 0,
        "allocate": 0,
    }

    def fail_with_timing(error, extra=None, error_code="pipeline_failed"):
        stage_elapsed["total"] = int((time.monotonic() - workflow_started) * 1000)
        details = {"workspace": str(ws), "stage_elapsed_ms": stage_elapsed}
        if extra:
            details.update(extra)
        return _fail(error, details, error_code=error_code)

    # 1) md5 去重 + 光栅化输入
    md5_started = time.monotonic()
    _progress(progress_log, 1, 9, "📋 准备阶段：收集 PDF 并完成去重")
    seen_md5, raster_items = {}, []
    for idx, p in enumerate(pdf_paths, start=1):
        if not os.path.exists(p):
            _progress(progress_log, 0, 0, f"❌ 处理失败：PDF 不存在: {p}")
            return fail_with_timing(f"PDF 不存在: {p}")
        md5 = md5_file(p)
        dup_of = seen_md5.get(md5)
        if dup_of is None:
            seen_md5[md5] = idx
        raster_items.append({
            "seq": idx, "pdf_path": p, "md5": md5, "dup_of": dup_of,
            "output_dir": str(pages_dir / f"{idx:04d}"),
        })
    unique_n = sum(1 for r in raster_items if r["dup_of"] is None)
    dup_n = len(raster_items) - unique_n
    stage_elapsed["md5"] = int((time.monotonic() - md5_started) * 1000)
    _progress(progress_log, 1, 9,
              f"📋 准备阶段：收集完成，共 {len(raster_items)} 张（去重 {dup_n} 份）")

    progress_state = checkpoint.load_progress(str(progress_file))
    unique_items = [r for r in raster_items if r["dup_of"] is None]

    def has_matching_ocr_cache(item):
        cached = _load_json(str(ocr_dir / f"{item['seq']}.json"), {}) or {}
        return str(cached.get("md5") or "") == item["md5"]

    reusable_ocr = {
        r["seq"] for r in unique_items
        if _stage_at_least(progress_state, r["md5"], "ocr_done")
        and has_matching_ocr_cache(r)
    }
    pending_raster_items = [r for r in unique_items if r["seq"] not in reusable_ocr]

    # 上传结果持久化：断线重跑时仅补传未成功项。
    upload_cache_path = ws / "upload_results.json"
    upload_cache_lock = threading.Lock()
    upload_cache = _load_json(str(upload_cache_path), {}) or {}
    current_md5s = {r["md5"] for r in unique_items}
    cached_upload_results = [] if init_out.get("session_mismatch") else [
        row for row in (upload_cache.get("results") or [])
        if str(row.get("md5") or "") in current_md5s
    ]
    cached_url_by_md5 = {
        str(r.get("md5")): r.get("invoice_url")
        for r in cached_upload_results if r.get("success") and r.get("invoice_url")
        and r.get("md5")
    }
    upload_files = [
        {"seq": r["seq"], "md5": r["md5"], "pdf_path": r["pdf_path"]}
        for r in unique_items if r["md5"] not in cached_url_by_md5
    ]

    def upload_missing():
        if not upload_files:
            return {"success": True, "total": 0, "succeeded": 0, "failed": 0,
                    "elapsed_ms": 0, "results": []}
        return cb.process({"files": upload_files, "workers": upload_workers})

    def merge_upload_results(new_results):
        upload_by_md5 = {}
        for row in cached_upload_results + list(new_results or []):
            md5 = str(row.get("md5") or "")
            if md5 and (row.get("success") or md5 not in upload_by_md5):
                upload_by_md5[md5] = row
        return list(upload_by_md5.values())

    def persist_upload_result(future):
        """上传一完成就落盘；即使主 OCR 随后中断，重跑也不会重复上传。"""
        try:
            upload_out, _elapsed = future.result()
            with upload_cache_lock:
                _write_json(str(upload_cache_path), {
                    "results": merge_upload_results(upload_out.get("results") or [])
                })
        except Exception as exc:  # noqa: BLE001
            sys.stderr.write(f"[warn] 上传结果断点落盘失败: {exc}\n")
            sys.stderr.flush()

    # 项目库拉取和原件上传都不依赖 OCR，与本地转图/OCR 并行。
    background = ThreadPoolExecutor(max_workers=2, thread_name_prefix="invoice-pipeline")
    projects_future = background.submit(_timed, fetch_projects)
    upload_future = background.submit(_timed, upload_missing)
    upload_future.add_done_callback(persist_upload_result)

    try:
        # 2) 光栅化：断点中已有 OCR JSON 的票据直接跳过。
        _progress(progress_log, 2, 9,
                  f"🖼️ 光栅化阶段：开始处理 {len(pending_raster_items)} 张"
                  f"（复用 {len(reusable_ocr)} 张）")
        _raster_stop = threading.Event()
        _raster_thread = threading.Thread(
            target=_poll_progress,
            args=(progress_log, len(pending_raster_items), "光栅化阶段",
                  lambda: _count_dirs(pages_dir), _raster_stop),
            daemon=True)
        _raster_thread.start()
        try:
            if pending_raster_items:
                raster_out, stage_elapsed["rasterize"] = _timed(
                    _rasterize, pending_raster_items, dpi, raster_workers
                )
            else:
                raster_out = {"success": True, "results": [], "workers": raster_workers,
                              "effective_workers": 0, "fallback_to_serial": False}
        finally:
            _raster_stop.set()
            _raster_thread.join(timeout=2)
        _progress(progress_log, 2, 9, "🖼️ 光栅化阶段：完成")

        # 固定 20 张逻辑批次。OCR 每完成一个有序批次，立即做项目匹配和
        # 串行远程匹配；后续 OCR worker 仍在后台继续计算。
        chunks = [
            unique_items[i:i + logical_batch_size]
            for i in range(0, len(unique_items), logical_batch_size)
        ]
        ready_seqs = set(reusable_ocr)
        processed_by_seq = {}
        candidate_pending, candidate_success = [], []
        next_chunk = 0
        project_match_ms = 0
        remote_match_ms = 0
        projects_holder = {"value": None}

        def ensure_projects():
            if projects_holder["value"] is None:
                projects, elapsed = projects_future.result()
                projects_holder["value"] = projects
                stage_elapsed["project_fetch"] = elapsed
                _write_json(str(ws / "projects.json"), projects)
            return projects_holder["value"]

        def process_chunk(chunk_index, chunk):
            nonlocal project_match_ms, remote_match_ms
            batch_path = batch_dir / f"candidates_{chunk_index + 1:04d}.json"
            chunk_items = _assemble_items(chunk, raster_out, ocr_dir)
            # OCR 产物已逐张落盘，先推进断点；后续项目库或远程接口异常时可直接复用。
            _checkpoint_mark(progress_file, "ocr_done", chunk)
            projects = ensure_projects()
            _, elapsed = _timed(_match_projects, chunk_items, projects)
            project_match_ms += elapsed
            for item in chunk_items:
                processed_by_seq[item["seq"]] = item

            matchable = [
                {"title_norm": title_normalizer.normalize_title(it["title"])[0],
                 "amount": int(it["amount"]), "project_id": it["project_id"]}
                for it in chunk_items
                if not it.get("incomplete") and it.get("title")
                and it.get("amount") is not None
            ]

            latest_progress = checkpoint.load_progress(str(progress_file))
            cached_batch = _load_json(str(batch_path), None)
            can_reuse = (
                cached_batch
                and cached_batch.get("md5s") == [it["md5"] for it in chunk]
                and all(
                _stage_at_least(latest_progress, it["md5"], "matched") for it in chunk
                )
            )
            if can_reuse:
                pending = cached_batch.get("pending_list") or []
                success = cached_batch.get("success_list") or []
            else:
                started = time.monotonic()
                pending, success = fetch_candidates(
                    org_no, matchable,
                    progress=lambda i, t: _progress(
                        progress_log, i, t,
                        f"🌐 远程匹配阶段：逻辑批次 {chunk_index + 1}/{len(chunks)}，"
                        f"子批 {i}/{t}"
                    ),
                ) if matchable else ([], [])
                remote_match_ms += int((time.monotonic() - started) * 1000)
                _write_json(str(batch_path), {
                    "seqs": [it["seq"] for it in chunk],
                    "md5s": [it["md5"] for it in chunk],
                    "pending_list": pending, "success_list": success,
                })
                _checkpoint_mark(progress_file, "matched", chunk)
            candidate_pending.extend(pending)
            candidate_success.extend(success)
            _progress(
                progress_log, chunk_index + 1, len(chunks),
                f"🧩 分批处理：已完成 {chunk_index + 1}/{len(chunks)} 批"
            )

        def drain_ready_chunks():
            nonlocal next_chunk
            while next_chunk < len(chunks):
                chunk = chunks[next_chunk]
                if not all(it["seq"] in ready_seqs for it in chunk):
                    break
                process_chunk(next_chunk, chunk)
                next_chunk += 1

        _progress(progress_log, 3, 9,
                  f"🔍 OCR识别阶段：开始识别 {len(pending_raster_items)} 张"
                  f"（逻辑分 {len(chunks)} 批）")
        _ocr_stop = threading.Event()
        _ocr_thread = threading.Thread(
            target=_poll_progress,
            args=(progress_log, unique_n, "OCR识别阶段",
                  lambda: _count_files(ocr_dir, ".json"), _ocr_stop),
            daemon=True)
        _ocr_thread.start()

        def on_ocr_result(result):
            if result.get("success"):
                ready_seqs.add(int(result.get("seq")))
                drain_ready_chunks()

        try:
            drain_ready_chunks()
            if pending_raster_items:
                ocr_out, stage_elapsed["ocr"] = _timed(
                    _ocr, pending_raster_items, raster_out, ocr_dir,
                    ocr_workers, on_ocr_result, ocr_threads_per_worker,
                )
            else:
                ocr_out = {"success": True, "results": [], "workers": ocr_workers,
                           "threads_per_worker": ocr_threads_per_worker,
                           "effective_workers": 0,
                           "effective_total_inference_threads": 0,
                           "fallback_to_serial": False}
            drain_ready_chunks()
        finally:
            _ocr_stop.set()
            _ocr_thread.join(timeout=2)
        if next_chunk != len(chunks):
            missing = sorted(
                it["seq"] for chunk in chunks[next_chunk:] for it in chunk
                if it["seq"] not in ready_seqs
            )
            raise RuntimeError(f"OCR 完成后仍缺少结果: seq={missing}")
        stage_elapsed["project_match"] = project_match_ms
        stage_elapsed["remote_match"] = remote_match_ms
        _progress(progress_log, 3, 9, "🔍 OCR识别与分批匹配阶段：完成")

        # 4) 组装全量票据，复用分批阶段的项目匹配结果。
        all_items = _assemble_items(raster_items, raster_out, ocr_dir)
        for item in all_items:
            done = processed_by_seq.get(item["seq"])
            if done:
                item["project_name_list"] = done.get("project_name_list") or []
                item["project_id"] = done.get("project_id") or ""
            item.pop("_pm", None)
        projects = ensure_projects()
        _progress(progress_log, 4, 9,
                  f"📝 字段抽取阶段：完成 {len(all_items)} 张（含金额换算）")

        pending, success = candidate_pending, candidate_success
        _write_json(str(ws / "candidates.json"),
                    {"pending_list": pending, "success_list": success})
        _progress(progress_log, 5, 9,
                  f"🌐 远程匹配阶段：完成（已处理 {len(success) + len(pending)}/"
                  f"{len(success) + len(pending)}，自动匹配 {len(success)} 笔，"
                  f"待人工确认 {len(pending)} 笔）")

        # 6) 收口并行上传分支，合并断点前的成功结果。
        _progress(progress_log, 6, 9, f"☁️ 原件上传阶段：等待并行上传完成")
        up_out, upload_wall_ms = upload_future.result()
        stage_elapsed["upload"] = upload_wall_ms
        # 按 PDF 内容保留最后一次成功结果；断点重跑即使输入顺序改变也不会串票。
        merged_upload_results = merge_upload_results(up_out.get("results") or [])
        with upload_cache_lock:
            _write_json(str(upload_cache_path), {"results": merged_upload_results})
        succeeded_uploads = [r for r in merged_upload_results if r.get("success")]
        if not succeeded_uploads:
            _progress(progress_log, 0, 0, "❌ 处理失败：COS 上传全部失败")
            return fail_with_timing(
                "COS 上传全部失败: " + str(up_out.get("error")), {"upload": up_out}
            )
        url_by_md5 = {str(r["md5"]): r.get("invoice_url") for r in succeeded_uploads}
        for it in all_items:
            it["invoice_url"] = url_by_md5.get(it["md5"], "")
        uploaded_items = [it for it in all_items if it.get("invoice_url")]
        _checkpoint_mark(progress_file, "uploaded", uploaded_items)
        upload_failed = unique_n - len(succeeded_uploads)
        _progress(progress_log, 6, 9,
                  f"☁️ 原件上传阶段：完成（成功 {len(succeeded_uploads)} / 失败 {upload_failed}）")

        # 7) 统一全局 m:n 分配；不分批打开 UI，避免跨批申请单占用冲突。
        _progress(progress_log, 7, 9, "🧩 组装阶段：分配票据并组装确认数据")
        alloc_out, stage_elapsed["allocate"] = _timed(
            _quiet, title_normalizer.do_allocate,
            {"mode": "allocate", "org_no": org_no, "items": all_items,
             "candidates_file": str(ws / "candidates.json"),
             "output_items_file": str(ws / "items.json"),
             "expected_total": len(all_items)}, None,
        )
        if not alloc_out.get("success"):
            _progress(progress_log, 0, 0, "❌ 处理失败：分配一致性断言失败，不得呼起 UI")
            return fail_with_timing(
                "分配一致性断言失败, 不得呼起 UI: " + str(alloc_out.get("error")),
                {"assertions": alloc_out.get("assertions")},
            )
        ui_req = alloc_out["ui_req"]
        _progress(progress_log, 8, 9, "🧩 组装阶段：完成")
        _progress(progress_log, 9, 9, "🎉 全部完成：已识别、匹配并上传原件，准备呼起确认页")
    except _StageError as e:
        # 阶段失败：message 简短、error_code 稳定；install_log 作为独立字段透传，
        # 不含入埋点上报（避免本机路径等隐私信息外泄）。
        _progress(progress_log, 0, 0, f"❌ 处理失败：{e}")
        extra = {"install_log": e.install_log} if e.install_log else None
        return fail_with_timing(f"pipeline 执行异常: {e}", extra, error_code=e.error_code)
    except Exception as e:  # noqa: BLE001
        _progress(progress_log, 0, 0, f"❌ 处理失败：{e}")
        return fail_with_timing(f"pipeline 执行异常: {e}")
    finally:
        background.shutdown(wait=True, cancel_futures=False)

    stage_elapsed["total"] = int((time.monotonic() - workflow_started) * 1000)
    # 透传子模块的 install_log（自动安装日志 / 串行回退说明），供上层 Agent 如实上报。
    # 属附加信息字段，与统一错误格式的关键字段（success/error_code/message）相互独立。
    install_log = {}
    if raster_out.get("install_log"):
        install_log["rasterize"] = raster_out["install_log"]
    if ocr_out.get("install_log"):
        install_log["ocr"] = ocr_out["install_log"]
    return {
        "success": True, "mode": "full",
        "org": {"org_no": org_no, "org_name": org_name},
        "ui_req": ui_req,
        "summary": alloc_out.get("summary"),
        "duplicates": alloc_out.get("duplicates"),
        "warnings": alloc_out.get("warnings", []),
        "workspace": str(ws),
        "progress_log": progress_log or None,
        "projects_count": len(projects),
        "pending_pool_size": len(pending),
        "success_pool_size": len(success),
        "upload": {"succeeded": len(succeeded_uploads), "failed": upload_failed},
        "stage_elapsed_ms": stage_elapsed,
        "logical_batch_size": logical_batch_size,
        "logical_batches": len(chunks),
        "runtime": {
            "raster_workers_requested": raster_workers,
            "raster_workers_effective": raster_out.get("effective_workers", raster_out.get("workers")),
            "raster_fallback_to_serial": bool(raster_out.get("fallback_to_serial")),
            "raster_fallback_reason": raster_out.get("fallback_reason") or None,
            "ocr_workers_requested": ocr_workers,
            "ocr_workers_effective": ocr_out.get("effective_workers", ocr_out.get("workers")),
            "ocr_threads_per_worker": ocr_out.get(
                "threads_per_worker", ocr_threads_per_worker
            ),
            "ocr_total_inference_threads_effective": ocr_out.get(
                "effective_total_inference_threads"
            ),
            "ocr_engine": ocr_out.get("engine", local_ocr_batch.ENGINE),
            "ocr_model": ocr_out.get("model", local_ocr_batch.MODEL_NAME),
            "ocr_fallback_to_serial": bool(ocr_out.get("fallback_to_serial")),
            "ocr_fallback_reason": ocr_out.get("fallback_reason") or None,
        },
        "install_log": install_log or None,
        "checkpoint_file": str(progress_file),
        # WB 沙箱会拦截一次性递归删除大量 PNG。临时页不进入业务关键路径，
        # 由 workspace 生命周期/外部 TTL 清理，绝不能因清理失败推翻成功任务。
        "temporary_files": {
            "pages_dir": str(pages_dir),
            "rendered_pages": _count_files(pages_dir, ".png"),
            "cleanup": "deferred",
        },
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="manifest JSON 字符串")
    parser.add_argument("--input-file", dest="input_file", help="manifest JSON 文件路径")
    args = parser.parse_args()

    if not args.input and not args.input_file:
        print(json.dumps(_fail("必须提供 --input 或 --input-file")), flush=True)
        sys.exit(1)

    try:
        if args.input_file:
            with open(args.input_file, "r", encoding="utf-8") as f:
                m = json.load(f)
        else:
            m = json.loads(args.input)
    except (json.JSONDecodeError, OSError) as e:
        print(json.dumps(_fail(f"manifest 非合法 JSON: {e}"), ensure_ascii=False), flush=True)
        sys.exit(1)

    mode = str(m.get("mode") or "full").strip().lower()
    if mode != "full":
        print(json.dumps(_fail(f"mode 非法: {mode!r}, 只支持 full"), ensure_ascii=False), flush=True)
        sys.exit(1)
    workspace = str(m.get("workspace") or os.getcwd())
    # 埋点身份与 MCP 调用身份同源（mcp_client.CALLER_EXPERT_ID）；mcp_client 硬依赖
    # requests，需先确保依赖再延迟导入。
    _ensure_requests()
    observer = galileo_observer(
        _caller_expert_id(), expert_version(),
        galileo_topic=galileo_topic(),
        spool_dir=os.path.join(workspace, ".observe"),
    )
    with observer.trace(
        f"invoice.pipeline.{mode}",
        run_id=str(m.get("session_id") or "") or None,
        session_id=str(m.get("session_id") or "") or None,
        attributes={"mode": mode, "item_count": len(m.get("pdf_paths") or [])},
    ) as observe_trace:
        try:
            result = run_full(m)
        except Exception as e:  # noqa: BLE001
            result = _fail(f"未捕获异常: {e}")

        record_stage_timings(
            observe_trace, result.get("stage_elapsed_ms") or {}, prefix="invoice"
        )
        summary = result.get("summary") or {}
        success = bool(result.get("success"))
        error_code = result.get("error_code")
        observe_trace.set_result(
            success=success,
            error_type=(error_code.upper() if error_code
                        else ("PIPELINE_FAILED" if not success else None)),
            status_message=None if success else (result.get("message") or "invoice pipeline failed"),
            attributes={
                "matched_count": summary.get("matched"),
                "failed_count": summary.get("failed"),
                "duplicate_count": len(result.get("duplicates") or []),
                "warning_count": len(result.get("warnings") or []),
                "logical_batches": result.get("logical_batches"),
            },
        )

        # 落盘最终 JSON（含 ui_req），避免大 JSON 经后台任务 stdout 被截断导致呼起 UI 失败
        _try_write_result(result)
        print(json.dumps(result, ensure_ascii=False), flush=True)

    return 0 if result.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())
