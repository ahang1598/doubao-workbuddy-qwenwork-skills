#!/usr/bin/env python3
"""
pdf_to_images.py — PDF 逐页光栅化为 PNG 图片

⚠️ 本脚本做的是**光栅化渲染**（把页面画成像素图），**不是**提取文本层。
   腾讯公益票据 PDF 普遍使用 subset 加密字体，文本层字符经过 CID 映射不可信；
   必须光栅化后交给视觉 OCR 识别。详见 SKILL.md 门禁 3。

CLI:
  python pdf_to_images.py --input '<JSON>'
  python pdf_to_images.py --input-file <path/to/input.json>     # 批量时必用

入参 JSON（单文件, 向后兼容）:
  {
    "pdf_path": "/path/to/xxx.pdf",
    "output_dir": "/tmp/xxx_images",
    "dpi": 200,              // 可选, 默认 200 (票据 OCR 推荐 200-300)
    "auto_install": true     // 可选, 默认 true; 自动初始化隔离的 pypdfium2 + Pillow
  }

入参 JSON（★ 批量 + 并发, 大批量必用）:
  {
    "items": [
      { "pdf_path": "/a/1.pdf", "output_dir": "/tmp/1" },
      { "pdf_path": "/a/2.pdf", "output_dir": "/tmp/2" }
    ],
    // 或 { "pdf_paths": ["/a/1.pdf", ...], "output_root": "/tmp/pages" }
    "dpi": 200,
    "workers": 8             // 可选, 默认 8 (设计 D13 的 P_r=8); 1 = 串行
  }

  ⚠️ 批量是**省 turn**的关键: 2000 张票据若一张一次调用要2000 个 turn,
     一次批量调用只要 1-2 个。见 design D13 的 turn 预算核算。

出参 JSON (stdout) — 单文件:
  {
    "success": true,
    "images": ["/tmp/xxx_images/page_1.png", "/tmp/xxx_images/page_2.png"],
    "page_count": 2,
    "backend": "pypdfium2",
    "dpi": 200,
    "elapsed_ms": 1480
  }

出参 JSON (stdout) — 批量:
  {
    "success": true,
    "backend": "pypdfium2",
    "dpi": 200,
    "workers": 8,
    "total": 20,
    "succeeded": 20,
    "failed": 0,
    "elapsed_ms": 9120,              // 墙钟总耗时(并发后)
    "avg_ms_per_file": 456,          // ★ 供耗时预估校准使用
    "results": [
      { "pdf_path": "/a/1.pdf", "success": true, "images": [...],
        "page_count": 1, "elapsed_ms": 1420 }
    ]
  }

失败时:
  {
    "success": false,
    "error": "...",
    "tried_backends": ["pypdfium2", "fitz", "pdf2image"],
    "fix_hint": "请直接重跑；脚本会自动初始化隔离的 pypdfium2 + Pillow"
  }

⚠️ 批量模式下**部分失败不中断**其余文件: `success` 仅在**全部**失败时为 false,
   部分失败时 `success=true` 但 `failed > 0`, 失败明细在 `results` 里逐条给出。

渲染后端优先级（都是光栅化, 非文本层提取）:
  1. pypdfium2  — 纯 wheel, 无系统依赖, 速度快(首选)
  2. fitz       — PyMuPDF, 功能强 (注意 AGPL license)
  3. pdf2image  — 需要系统装 poppler (pdftoppm),兼容性兜底

参考: SKILL.md Step 2
"""
import argparse
import contextlib
import io
import json
import os
import subprocess
import sys
import time
import uuid
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

DEFAULT_DPI = 200
DEFAULT_WORKERS = 8          # 设计 D13:光栅化P_r = 8
BACKEND_PREFERENCE = ["pypdfium2", "fitz", "pdf2image"]
RENDER_RUNTIME_BUNDLE_VERSION = "pypdfium2-4-pillow-10-v1"


# --------------------------------------------------------------------------
# stdout 纯净化（⚠️ 2026-08-10 实测事故, 别删）
# --------------------------------------------------------------------------
# `import fitz` 会向 **stdout** 打印:
#     warning: The `fitz` API is deprecated and will be removed in future.
# 本脚本的契约是「stdout 只有一行 JSON」, 这行警告会让调用方
# `json.loads(stdout)` 直接抛 JSONDecodeError ——表现为"脚本明明跑成功了,
# 但 agent 说返回值解析失败", 极难排查。
#
# 因此: 处理期间的一切 stdout 输出**一律转到 stderr**, JSON 在恢复后才打。
# ⚠️ 并发子进程有**独立的 stdout fd**, 父进程的重定向管不到它们,
#    所以 `_render_one` 内部必须**自己**再重定向一次。
def _run_quiet(fn, *args, **kwargs):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        result = fn(*args, **kwargs)
    noise = buf.getvalue()
    if noise.strip():
        sys.stderr.write(noise)
        sys.stderr.flush()
    return result


# --------------------------------------------------------------------------
# 后端探测与隔离运行时
# --------------------------------------------------------------------------
def _managed_runtime_root() -> Path:
    configured = os.environ.get("INVOICE_RENDER_RUNTIME_DIR")
    if configured:
        return Path(configured).expanduser()
    return (
        Path.home() / ".workbuddy" / "runtimes" / "invoice-expert"
        / RENDER_RUNTIME_BUNDLE_VERSION
    )


def _activate_managed_runtime() -> bool:
    """激活本专家的 PDF 渲染运行时，不修改 WB 共享 Python。"""
    marker = _managed_runtime_root() / "active.json"
    try:
        with marker.open("r", encoding="utf-8") as f:
            site_packages = Path(str(json.load(f).get("site_packages") or ""))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return False
    if not site_packages.is_dir():
        return False
    site_path = str(site_packages)
    if site_path not in sys.path:
        sys.path.insert(0, site_path)
    # ProcessPool 在 spawn 模式下会启动新解释器；同步 PYTHONPATH 才能让子进程
    # 复用同一隔离运行时。fork 模式下这一步同样安全。
    pythonpath = os.environ.get("PYTHONPATH", "")
    entries = [p for p in pythonpath.split(os.pathsep) if p]
    if site_path not in entries:
        os.environ["PYTHONPATH"] = os.pathsep.join([site_path, *entries])
    return True


def _pypdfium2_runtime_importable() -> bool:
    """pypdfium2 的 PNG 输出能力必须同时具备 Pillow，二者不可拆开探测。"""
    try:
        import pypdfium2  # noqa: F401
        from PIL import Image  # noqa: F401
        return True
    except Exception:
        return False


def _probe_backend(name: str) -> bool:
    """检测某个渲染后端的完整能力，而不是只验证顶层包可导入。"""
    try:
        if name == "pypdfium2":
            if _pypdfium2_runtime_importable():
                return True
            return _activate_managed_runtime() and _pypdfium2_runtime_importable()
        elif name == "fitz":
            import fitz  # noqa: F401
        elif name == "pdf2image":
            import pdf2image  # noqa: F401
            # pdf2image 还依赖系统 poppler, 需额外探测
            from pdf2image.exceptions import PDFInfoNotInstalledError  # noqa: F401
        else:
            return False
        return True
    except Exception:
        return False


def _detect_backend() -> str:
    """按优先级返回第一个可用后端, 无可用则返回空串。"""
    for name in BACKEND_PREFERENCE:
        if _probe_backend(name):
            return name
    return ""


def _try_auto_install() -> tuple:
    """一次性安装 pypdfium2 + Pillow 到插件专属隔离目录。

    返回 (是否成功, 日志文本)
    """
    root = _managed_runtime_root()
    root.mkdir(parents=True, exist_ok=True)
    logs = []
    lock_file = (root / "install.lock").open("a+", encoding="utf-8")
    try:
        try:
            import fcntl
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        except (ImportError, OSError):
            pass

        # 另一个会话可能在等待锁期间已经完成初始化。
        if _probe_backend("pypdfium2"):
            return True, "PDF 渲染隔离运行时已由其他任务初始化，直接复用"

        staging = root / f"site-packages-{os.getpid()}-{uuid.uuid4().hex[:8]}"
        cmd = [
            sys.executable, "-m", "pip", "install", "--quiet",
            "--target", str(staging),
            "pypdfium2>=4.20.0,<5.0", "Pillow>=10.0.0,<13.0",
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            logs.append(
                f"$ {' '.join(cmd)}\n"
                f"  rc={proc.returncode} out={proc.stdout.strip()[:300]} "
                f"err={proc.stderr.strip()[:300]}"
            )
        except Exception as e:  # noqa: BLE001
            logs.append(f"$ {' '.join(cmd)}\n  exception={e}")
            return False, "\n".join(logs)
        if proc.returncode != 0:
            return False, "\n".join(logs)

        env = os.environ.copy()
        old_pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(staging) + (
            os.pathsep + old_pythonpath if old_pythonpath else ""
        )
        verify = subprocess.run(
            [sys.executable, "-c", "import pypdfium2; from PIL import Image"],
            capture_output=True, text=True, timeout=120, env=env,
        )
        logs.append(
            f"runtime verify rc={verify.returncode} err={verify.stderr.strip()[:300]}"
        )
        if verify.returncode != 0:
            return False, "\n".join(logs)

        marker_tmp = root / f"active.{os.getpid()}.tmp"
        with marker_tmp.open("w", encoding="utf-8") as f:
            json.dump({
                "bundle": RENDER_RUNTIME_BUNDLE_VERSION,
                "site_packages": str(staging),
                "python": sys.executable,
            }, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(str(marker_tmp), str(root / "active.json"))
        if not _activate_managed_runtime() or not _pypdfium2_runtime_importable():
            logs.append("PDF 渲染隔离运行时激活后导入失败")
            return False, "\n".join(logs)
        return True, "\n".join(logs)
    finally:
        try:
            import fcntl
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        except (ImportError, OSError):
            pass
        lock_file.close()


# --------------------------------------------------------------------------
# 各后端的渲染实现
# --------------------------------------------------------------------------
def _render_pypdfium2(pdf_path: str, output_dir: str, dpi: int) -> list:
    import pypdfium2 as pdfium

    scale = dpi / 72.0
    images = []
    pdf = pdfium.PdfDocument(pdf_path)
    try:
        for i in range(len(pdf)):
            page = pdf[i]
            bitmap = page.render(scale=scale)
            pil_image = bitmap.to_pil()
            out = os.path.join(output_dir, f"page_{i + 1}.png")
            pil_image.save(out, format="PNG")
            images.append(out)
    finally:
        pdf.close()
    return images


def _render_fitz(pdf_path: str, output_dir: str, dpi: int) -> list:
    import fitz  # PyMuPDF

    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    images = []
    doc = fitz.open(pdf_path)
    try:
        for i, page in enumerate(doc):
            pix = page.get_pixmap(matrix=matrix)
            out = os.path.join(output_dir, f"page_{i + 1}.png")
            pix.save(out)
            images.append(out)
    finally:
        doc.close()
    return images


def _render_pdf2image(pdf_path: str, output_dir: str, dpi: int) -> list:
    from pdf2image import convert_from_path

    pages = convert_from_path(pdf_path, dpi=dpi)
    images = []
    for i, page in enumerate(pages):
        out = os.path.join(output_dir, f"page_{i + 1}.png")
        page.save(out, "PNG")
        images.append(out)
    return images


_RENDERERS = {
    "pypdfium2": _render_pypdfium2,
    "fitz": _render_fitz,
    "pdf2image": _render_pdf2image,
}


# --------------------------------------------------------------------------
# 主流程
# --------------------------------------------------------------------------
def convert_pdf(pdf_path: str, output_dir: str, dpi: int = DEFAULT_DPI,
                auto_install: bool = True) -> dict:
    """将 PDF 光栅化为PNG 图片列表.

    返回 {"images": [...], "backend": "...", "install_log": "..."}
    失败抛 RuntimeError（含可执行的修复指令）。
    """
    backend = _detect_backend()
    install_log = ""

    if not backend and auto_install:
        ok, install_log = _try_auto_install()
        if ok:
            backend = "pypdfium2"

    if not backend:
        raise RuntimeError(
            "没有可用的 PDF 光栅化后端。已尝试: "
            + ", ".join(BACKEND_PREFERENCE)
            + (f"\n自动安装日志:\n{install_log}" if install_log else "")
        )

    images = _RENDERERS[backend](pdf_path, output_dir, dpi)
    if not images:
        raise RuntimeError(f"后端 {backend} 未产出任何图片（PDF 可能为 0 页或已损坏）")

    return {"images": images, "backend": backend, "install_log": install_log}


# --------------------------------------------------------------------------
# 批量 + 并发
# --------------------------------------------------------------------------
def _render_one(task: tuple) -> dict:
    """子进程入口: (pdf_path, output_dir, dpi, backend) → 结果 dict。

    ⚠️ 必须是模块级函数, 否则 Windows 上 ProcessPoolExecutor 无法 pickle。
    ⚠️ 子进程内**不做** auto_install —— 依赖已在主进程探测/补齐完毕。
    """
    pdf_path, output_dir, dpi, backend = task
    started = time.time()
    try:
        if not os.path.exists(pdf_path):
            raise RuntimeError(f"PDF 文件不存在: {pdf_path}")
        os.makedirs(output_dir, exist_ok=True)
        # 子进程有独立 stdout fd, 必须自己把库噪音挡到 stderr
        with contextlib.redirect_stdout(sys.stderr):
            images = _RENDERERS[backend](pdf_path, output_dir, dpi)
        if not images:
            raise RuntimeError(f"后端 {backend} 未产出任何图片（PDF 可能为 0 页或已损坏）")
        return {
            "pdf_path": pdf_path,
            "output_dir": output_dir,
            "success": True,
            "images": images,
            "page_count": len(images),
            "elapsed_ms": int((time.time() - started) * 1000),
        }
    except Exception as e:  # noqa: BLE001
        return {
            "pdf_path": pdf_path,
            "output_dir": output_dir,
            "success": False,
            "error": str(e),
            "elapsed_ms": int((time.time() - started) * 1000),
        }


def _collect_tasks(input_data: dict) -> tuple:
    """把三种入参形态统一成 [(pdf_path, output_dir), ...]。"""
    items = input_data.get("items")
    if isinstance(items, list) and items:
        out = []
        for it in items:
            if not isinstance(it, dict):
                continue
            p = str(it.get("pdf_path") or "").strip()
            d = str(it.get("output_dir") or "").strip()
            if not p:
                continue
            if not d:
                return None, "items 中某项缺少 output_dir"
            out.append((p, d))
        return out, None if out else "items 中没有合法的 pdf_path"

    paths = input_data.get("pdf_paths")
    if isinstance(paths, list) and paths:
        root = str(input_data.get("output_root") or "").strip()
        if not root:
            return None, "使用 pdf_paths 时必须提供 output_root"
        out = []
        for idx, p in enumerate(paths):
            p = str(p or "").strip()
            if not p:
                continue
            stem = os.path.splitext(os.path.basename(p))[0] or f"pdf_{idx + 1}"
            out.append((p, os.path.join(root, f"{idx + 1:04d}_{stem}")))
        return out, None if out else "pdf_paths 为空"

    return None, None      # 走单文件分支


def convert_batch(tasks: list, dpi: int, workers: int, auto_install: bool = True) -> dict:
    backend = _detect_backend()
    install_log = ""
    if not backend and auto_install:
        ok, install_log = _try_auto_install()
        if ok:
            backend = "pypdfium2"
    if not backend:
        raise RuntimeError(
            "没有可用的 PDF 光栅化后端。已尝试: "
            + ", ".join(BACKEND_PREFERENCE)
            + (f"\n自动安装日志:\n{install_log}" if install_log else "")
        )

    payload = [(p, d, dpi, backend) for p, d in tasks]
    started = time.time()
    results = []
    fallback_to_serial = False
    fallback_reason = ""

    if workers <= 1 or len(payload) == 1:
        results = []
        for idx, t in enumerate(payload, 1):
            results.append(_render_one(t))
            sys.stderr.write(f"光栅化进度 {idx}/{len(payload)}\n")
            sys.stderr.flush()
    else:
        try:
            with ProcessPoolExecutor(max_workers=workers) as pool:
                futures = {pool.submit(_render_one, t): t[0] for t in payload}
                retry_payload = []
                done = 0
                for fut in as_completed(futures):
                    pdf_path = futures[fut]
                    try:
                        result = fut.result()
                    except Exception as e:  # noqa: BLE001
                        retry_payload.extend(t for t in payload if t[0] == pdf_path)
                        sys.stderr.write(f"光栅化并发任务失败，将单文件串行重试: {e}\n")
                    else:
                        if result.get("success"):
                            results.append(result)
                        else:
                            retry_payload.extend(t for t in payload if t[0] == pdf_path)
                    done += 1
                    sys.stderr.write(
                        f"光栅化进度 {done}/{len(payload)} "
                        f"({int((time.time() - started) * 1000)}ms)\n"
                    )
                    sys.stderr.flush()
            if retry_payload:
                fallback_to_serial = True
                retry_by_path = {t[0]: t for t in retry_payload}
                results.extend(_render_one(t) for t in retry_by_path.values())
                fallback_reason = "个别并发任务失败"
                install_log = (
                    install_log + f"\n仅对 {len(retry_by_path)} 份执行串行重试"
                ).strip()
        except Exception as e:  # noqa: BLE001
            # 保留已完成结果，只对未完成 PDF 串行重试。
            fallback_to_serial = True
            done_paths = {r.get("pdf_path") for r in results if r.get("success")}
            pending = [t for t in payload if t[0] not in done_paths]
            results.extend(_render_one(t) for t in pending)
            fallback_reason = str(e)
            install_log = (
                install_log + f"\n并发不可用, 仅对 {len(pending)} 份未完成 PDF 串行重试: {e}"
            ).strip()

    order = {p: i for i, (p, _d) in enumerate(tasks)}
    results.sort(key=lambda r: order.get(r.get("pdf_path"), 0))

    elapsed_ms = int((time.time() - started) * 1000)
    succeeded = sum(1 for r in results if r.get("success"))
    return {
        "backend": backend,
        "workers": workers,
        "effective_workers": 1 if fallback_to_serial else workers,
        "fallback_to_serial": fallback_to_serial,
        "fallback_reason": fallback_reason,
        "results": results,
        "total": len(results),
        "succeeded": succeeded,
        "failed": len(results) - succeeded,
        "elapsed_ms": elapsed_ms,
        "avg_ms_per_file": int(elapsed_ms / len(results)) if results else 0,
        "install_log": install_log,
    }


def process(input_data: dict) -> dict:
    dpi = int(input_data.get("dpi", DEFAULT_DPI) or DEFAULT_DPI)
    auto_install = bool(input_data.get("auto_install", True))
    if dpi < 72 or dpi > 600:
        return {"success": False, "error": f"dpi 超出合理范围 [72, 600]: {dpi}"}

    tasks, err = _collect_tasks(input_data)
    if err:
        return {"success": False, "error": err}

    # ---------------- 批量分支 ----------------
    if tasks:
        workers = int(input_data.get("workers", DEFAULT_WORKERS) or DEFAULT_WORKERS)
        workers = max(1, min(workers, 16))
        try:
            batch = convert_batch(tasks, dpi, workers, auto_install)
        except RuntimeError as e:
            return {
                "success": False,
                "error": str(e),
                "tried_backends": BACKEND_PREFERENCE,
                "fix_hint": "请直接重跑；脚本会在隔离目录自动初始化 pypdfium2 + Pillow",
            }
        except Exception as e:  # noqa: BLE001
            return {"success": False, "error": f"批量转换失败: {e}"}

        out = {
            "success": batch["succeeded"] > 0,
            "backend": batch["backend"],
            "dpi": dpi,
            "workers": batch["workers"],
            "total": batch["total"],
            "succeeded": batch["succeeded"],
            "failed": batch["failed"],
            "elapsed_ms": batch["elapsed_ms"],
            "avg_ms_per_file": batch["avg_ms_per_file"],
            "results": batch["results"],
        }
        if batch.get("install_log"):
            out["install_log"] = batch["install_log"]
        if batch["succeeded"] == 0:
            errors = []
            for result in batch["results"]:
                error = str(result.get("error") or "").strip()
                if error and error not in errors:
                    errors.append(error)
            detail = "; ".join(errors[:3])
            out["error"] = "全部文件光栅化失败" + (f": {detail}" if detail else "")
        return out

    # ---------------- 单文件分支(向后兼容) ----------------
    pdf_path = str(input_data.get("pdf_path", "")).strip()
    output_dir = str(input_data.get("output_dir", "")).strip()

    if not pdf_path:
        return {"success": False, "error": "缺少 pdf_path（批量请用 items 或 pdf_paths）"}
    if not output_dir:
        return {"success": False, "error": "缺少 output_dir"}
    if not os.path.exists(pdf_path):
        return {"success": False, "error": f"PDF 文件不存在: {pdf_path}"}

    started = time.time()
    try:
        os.makedirs(output_dir, exist_ok=True)
        result = convert_pdf(pdf_path, output_dir, dpi=dpi, auto_install=auto_install)
        out = {
            "success": True,
            "images": result["images"],
            "page_count": len(result["images"]),
            "backend": result["backend"],
            "dpi": dpi,
            "elapsed_ms": int((time.time() - started) * 1000),
        }
        if result.get("install_log"):
            out["install_log"] = result["install_log"]
        return out
    except RuntimeError as e:
        return {
            "success": False,
            "error": str(e),
            "tried_backends": BACKEND_PREFERENCE,
            "fix_hint": "请直接重跑；脚本会在隔离目录自动初始化 pypdfium2 + Pillow",
        }
    except Exception as e:  # noqa: BLE001
        return {"success": False, "error": f"转换失败: {e}"}


def main():
    # ⚠️ Windows 实测: stdout 为管道时用 locale 编码(GBK), 中文 JSON(错误信息里的
    #    路径与提示)会写成 GBK 字节, UTF-8 读取方直接 UnicodeDecodeError。
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="JSON 格式的入参")
    parser.add_argument("--input-file", dest="input_file", help="入参 JSON 文件路径(批量必用)")
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

    result = _run_quiet(process, input_data)
    print(json.dumps(result, ensure_ascii=False), flush=True)
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
