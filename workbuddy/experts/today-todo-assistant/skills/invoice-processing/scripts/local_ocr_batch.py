#!/usr/bin/env python3
"""
local_ocr_batch.py — 批量模式的本地 OCR（脚本内多进程并发）

═══════════════════════════════════════════════════════════════════════════
⛔ 调用边界：**只有批量模式才允许触达本脚本**
═══════════════════════════════════════════════════════════════════════════
| 时机| 行为                                      |
|-------------------------------|-------------------------------------------|
| 精细模式(≤1 张)               | **完全不调用、不探测、不提示安装**|
| 批量模式(>1 张) + 引擎可用    | **静默使用**, 不提示                      |
| 批量模式 + 引擎缺失           | **此时才**提示并安装|

⛔ **严禁**在会话开始、环境自检(Step -1)、精细模式流程中调用本脚本做
   任何"顺手探测一下环境"的动作 —— 那等于无条件提示安装, 需求方明确禁止。
   本脚本**没有** probe-only 模式, 就是为了从结构上排除这种误用。

原因: RapidOCR + ONNX Runtime + PP-OCRv6 small 模型与运行时体积较大。只处理
      1 张票的用户走精细模式,
      根本用不到本地引擎, 不该被迫下载。因此 `requirements.txt` 里
      **不写** rapidocr / onnxruntime。

═══════════════════════════════════════════════════════════════════════════
为什么批量模式必须用本地 OCR
═══════════════════════════════════════════════════════════════════════════
`llm_vision_invoice` 的底层是「codebuddy 多模态视觉能力」= **agent 自己看图**,
不是可在脚本里并发调用的 API(2026-08-10 实测: 环境变量无任何模型凭证)。
2000 张走 LLM 视觉需要约 500 个 OCR turn, 无论怎么分段都超预算。

本地 OCR 把 OCR 的 **agent turn 成本从 `N/4` 降到常数 1-2** —— 脚本内并发
不消耗 agent turn。这是2000 张容量成立的唯一前提。

⚠️ 代价: 精度低于 LLM 视觉(印章/手写体较差), 批量模式未匹配率预期上升
   10~20%。SOP **必须**向用户明示本批使用了本地引擎、请在确认页重点核对。

CLI:
  python local_ocr_batch.py --input-file <path/to/input.json>

═══════════════════════════════════════════════════════════════════════════
入参 JSON
═══════════════════════════════════════════════════════════════════════════
  {
    "items": [
      { "seq": 1, "md5": "ab12...", "pdf_path": "D:/票据/1.pdf",
        "images": ["/tmp/1/page_1.png"] }
    ],
    "output_dir": "./_tmp/session_x/ocr",// 逐条落盘 <seq>.json
    "workers": 4,                            // 可选, 默认 4 个进程
    "threads_per_worker": 2,                 // 可选, 默认每进程 2 线程
    "lang": "ch",// 可选, 默认 ch
    "auto_install": true                     // 可选, 默认 true
  }

═══════════════════════════════════════════════════════════════════════════
出参 JSON (stdout) —— **只回摘要, 不回 OCR 全文**(token 治理)
═══════════════════════════════════════════════════════════════════════════
  {
    "success": true,
    "engine": "rapidocr_onnx_ppocrv6_small",
    "output_dir": "./_tmp/session_x/ocr",
    "total": 150, "succeeded": 148, "failed": 2,
    "incomplete": 12,                 // 抬头或金额缺失, 这些票直接判match_status=2
    "elapsed_ms": 28400,
    "avg_ms_per_file": 189,
    "results": [
      { "seq": 1, "md5": "ab12...", "success": true, "json_path": "..../1.json",
        "has_title": true, "has_amount": true, "incomplete": false }
    ]
  }

安装失败时:
  {
    "success": false,
    "engine": "rapidocr_onnx_ppocrv6_small",
    "error": "本地 OCR 引擎不可用",
    "attempted_remediation": "$ pip install ... rc=1 err=...",
    "fallback_hint": "请改为分多次走精细模式(每批 ≤100 张, LLM 视觉识别)"
  }
  ⛔ 此时 MUST NOT 静默使用低质结果继续流程。

═══════════════════════════════════════════════════════════════════════════
逐条落盘的 JSON 结构（★ 与 llm_vision_invoice 字段对齐, 下游脚本无需分支）
═══════════════════════════════════════════════════════════════════════════
  {
    "seq": 1, "md5": "ab12...",
    "title": "张三",
    "amount_upper": "壹万贰仟叁佰肆拾伍元捌角柒分",
    "amount_lower": "12345.87",
    "project_name_raw": "乡村教育扶贫计划",
    "remarks": null,
    "other_info": null,
    "confidence": "medium",          // 本地引擎固定 medium(低于 LLM 视觉)
    "raw_ocr_text": "...",           // ⛔ 不进agent 上下文
    "engine": "rapidocr_onnx_ppocrv6_small"
  }

⚠️ 本脚本**不做**金额换算(那是 amount_conversion.py 的事)、
   **不做**项目匹配(那是 project_matcher.py 的事)。
"""
import argparse
import contextlib
import io
import json
import os
import re
import subprocess
import sys
import time
import uuid
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ENGINE = "rapidocr_onnx_ppocrv6_small"
MODEL_NAME = "PP-OCRv6-small"
RUNTIME_NAME = "onnxruntime"
RUNTIME_BUNDLE_VERSION = "rapidocr-3.9.2-onnxruntime-ppocrv6-small-v1"
DEFAULT_WORKERS = 4
DEFAULT_THREADS_PER_WORKER = 2
MAX_WORKERS = 16
MAX_THREADS_PER_WORKER = 8

_OCR = None          # 子进程内的全局引擎实例(每进程只初始化一次)


# ---------------------------------------------------------------------------
# stdout 纯净化（⚠️ 2026-08-10 实测事故, 别删）
# ---------------------------------------------------------------------------
# 本脚本契约是「stdout 只有一行 JSON」。但:
#   · RapidOCR / ONNX Runtime 在import 与首次推理时可能往 **stdout** 打日志
#     (模型下载进度、算子注册、`ppocr DEBUG` 等), `show_log=False` 挡不住全部
#   · 同类事故已在 `pdf_to_images.py` 实测复现(`import fitz` 打 deprecation 警告)
# 这些噪音会让调用方 `json.loads(stdout)` 直接崩, 表现为"脚本明明跑成功了,
# 但 agent 说返回值解析失败"。
#
# 因此: 处理期间的一切 stdout **一律转到 stderr**, JSON 在恢复后才打。
# ⚠️ 并发子进程有独立 stdout fd, 父进程重定向管不到, 所以 `_init_worker` /
#    `_recognize_one` 内部必须**各自**再重定向一次。
def _run_quiet(fn, *args, **kwargs):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        result = fn(*args, **kwargs)
    noise = buf.getvalue()
    if noise.strip():
        sys.stderr.write(noise)
        sys.stderr.flush()
    return result


# ---------------------------------------------------------------------------
# 引擎探测与**按需**安装
# ---------------------------------------------------------------------------
def _managed_runtime_root() -> Path:
    configured = os.environ.get("INVOICE_OCR_RUNTIME_DIR")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".workbuddy" / "runtimes" / "invoice-expert" / RUNTIME_BUNDLE_VERSION


def _activate_managed_runtime() -> bool:
    """激活由本专家安装的隔离运行时；不会修改 WB 共享 Python 环境。"""
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
    return True


def _engine_importable() -> bool:
    try:
        import onnxruntime  # noqa: F401
        from rapidocr import RapidOCR  # noqa: F401
        return True
    except Exception:
        return False


def _probe_engine() -> bool:
    if _engine_importable():
        return True
    return _activate_managed_runtime() and _engine_importable()


def _try_auto_install() -> tuple:
    """按需安装到插件专属目录；带进程锁且不覆盖 WB 共享环境。"""
    # RapidOCR 声明依赖 opencv-python；WB 无 GUI，必须显式使用 headless 版本。
    # 因此先安装完整运行时依赖，再用 --no-deps 安装 RapidOCR，避免两个 cv2 包互相覆盖。
    runtime_pkgs = [
        "onnxruntime>=1.17.0,<2.0",
        "opencv-python-headless>=4.6.0,<5.0",
        "numpy>=1.24.0,<3.0",
        "pyclipper>=1.2.0",
        "six>=1.15.0",
        "Shapely>=1.7.1,!=2.0.4",
        "PyYAML>=6.0",
        "Pillow>=10.0.0",
        "tqdm>=4.64.0",
        "omegaconf>=2.3.0",
        "requests>=2.28.0",
        "colorlog>=6.7.0",
    ]
    root = _managed_runtime_root()
    root.mkdir(parents=True, exist_ok=True)
    logs = []
    lock_file = (root / "install.lock").open("a+", encoding="utf-8")
    try:
        try:
            import fcntl
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        except (ImportError, OSError):
            # WB 正式运行环境为 Linux；其他环境缺少 fcntl 时仍保持单入口安装。
            pass

        # 其他会话可能在等待锁期间已经完成初始化。
        if _probe_engine():
            return True, "OCR 隔离运行时已由其他任务初始化，直接复用"

        staging = root / f"site-packages-{os.getpid()}-{uuid.uuid4().hex[:8]}"
        cmds = [
            [sys.executable, "-m", "pip", "install", "--quiet",
             "--target", str(staging), *runtime_pkgs],
            [sys.executable, "-m", "pip", "install", "--quiet",
             "--target", str(staging), "--no-deps", "rapidocr==3.9.2"],
        ]
        for cmd in cmds:
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
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

        # 用独立子进程验证，避免失败安装污染当前解释器的 import 缓存。
        env = os.environ.copy()
        old_pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(staging) + (os.pathsep + old_pythonpath if old_pythonpath else "")
        verify = subprocess.run(
            [sys.executable, "-c", "import onnxruntime; from rapidocr import RapidOCR"],
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
                "bundle": RUNTIME_BUNDLE_VERSION,
                "site_packages": str(staging),
                "python": sys.executable,
            }, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(str(marker_tmp), str(root / "active.json"))
        if not _activate_managed_runtime() or not _engine_importable():
            logs.append("隔离运行时激活后导入失败")
            return False, "\n".join(logs)
        return True, "\n".join(logs)
    finally:
        try:
            import fcntl
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        except (ImportError, OSError):
            pass
        lock_file.close()


# ---------------------------------------------------------------------------
# 字段抽取（确定性正则, 不是 LLM 心算）
# ---------------------------------------------------------------------------
_TITLE_KEYS = ("交款人", "付款方", "付款人", "捐赠人", "抬头", "单位名称", "缴款人")
_PROJECT_KEYS = ("捐赠项目", "收款项目", "项目名称", "商品名称", "项目")
_REMARK_KEYS = ("备注", "摘要", "说明")

_SEP = r"[：:\s]*"
_UPPER_AMOUNT = re.compile(r"[零壹贰叁肆伍陆柒捌玖拾佰仟萬万億亿元圆角分整]{2,}")
_LOWER_AMOUNT = re.compile(r"(?:[¥￥]|小写|小\s*写|\(小写\)|（小写）)[：:\s)]*([0-9][0-9,]*(?:\.\d{1,2})?)")
_ANY_NUMBER = re.compile(r"\b([0-9][0-9,]*\.\d{2})\b")


def _grab_after(text: str, keys, max_len: int = 60, reject_prefix: tuple = ()):
    """在整段文本里找`关键词[:：]值`, 取到行尾或下一个字段名为止。"""
    for key in keys:
        pattern = re.compile(re.escape(key) + _SEP + r"([^\r\n]{1,%d})" % max_len)
        for m in pattern.finditer(text):
            value = m.group(1).strip()
            # 截到下一个明显的字段名之前
            value = re.split(r"(?:金额|大写|小写|备注|日期|票号|编号|证件)", value)[0]
            value = value.strip(" \t|·-—:：，,。")
            if not value:
                continue
            # 跳过干扰前缀: 如 "统一社会信用代码" (抬头匹配时不能把信用代码当抬头)
            if reject_prefix and value.startswith(reject_prefix):
                continue
            return value
    return None


_PROJECT_CODE = re.compile(r"^[A-Za-z]{0,4}\d+$")


def _is_project_code(v: str) -> bool:
    """项目编码(如 JZ0001 / 99900003)严禁进入任何字段, 否则干扰真实机构项目。"""
    return bool(v) and _PROJECT_CODE.fullmatch(v.strip())


def _clean(v: str) -> str:
    return re.sub(r"\s+", "", v).strip(" \t|·-—:：，,。")


def _extract_project(flat: str):
    """多版式抽取项目名, 严禁返回项目编码形态的值。

    票据项目名位置不固定: 可能在「捐赠款」后、可能在「金额合计」前、
    可能在页脚方括号标注、也可能是含「捐赠」的长描述名。
    """
    # A. "捐赠款" + 项目名
    m = re.search(r"捐赠款\s*([\u4e00-\u9fff]{2,})", flat)
    if m:
        v = re.split(r"(?:元|金额|小写|大写|数量|单位|标准)", m.group(1))[0]
        v = _clean(v)
        if v and len(v) >= 2 and not _is_project_code(v):
            return v
    # B. 金额行后、"金额合计"前的汉字串
    m = re.search(r"\d+\.\d{2}\s*([\u4e00-\u9fff]{2,}?)\s*金额合计", flat)
    if m:
        v = _clean(m.group(1))
        if v and not _is_project_code(v):
            return v
    # C. 方括号标注的项目名(仅 ASCII 括号, 避免误吞【】整句)
    m = re.search(r"[\[]([\u4e00-\u9fff]{2,})[\]]", flat)
    if m:
        v = _clean(m.group(1))
        if v and not _is_project_code(v):
            return v
    # D. 含"捐赠"的描述性长串兜底(如福建红十字会长名被 OCR 拆行)
    m = re.search(r"([\u4e00-\u9fff]{2,}捐赠[\u4e00-\u9fff]*)", flat)
    if m:
        v = _clean(m.group(1))
        if v and len(v) >= 4 and not _is_project_code(v):
            return v
    return None


def extract_fields(raw_text: str) -> dict:
    """从 OCR 全文抽取字段, 口径与 llm_vision_invoice 一致。"""
    text = raw_text or ""
    flat = text.replace("\u3000", " ")

    upper_candidates = _UPPER_AMOUNT.findall(flat)
    amount_upper = max(upper_candidates, key=len) if upper_candidates else None

    m = _LOWER_AMOUNT.search(flat)
    if m:
        amount_lower = m.group(1).replace(",", "")
    else:
        nums = _ANY_NUMBER.findall(flat)
        amount_lower = max(nums, key=lambda s: len(s.replace(",", ""))).replace(",", "") if nums else None

    # remarks: 仅接受「备注：」后确有值、且不像项目编码(如 JZ0001/99900003)的内容,
    # 避免把表格「备注」列头下一行的项目编码误当备注。
    remarks = None
    m = re.search(r"备注[：:]\s*([^\r\n]{1,60})", flat)
    if m:
        v = m.group(1).strip(" \t|·-—:：，,。")
        if v and not _is_project_code(v):
            remarks = v
    # other_info: 「其他信息」框(收款单位/复核人/收款人)
    m = re.search(r"收款单位[^\r\n]*\s*复核人[^\r\n]*\s*收款人[^\r\n]*", flat)
    other_info = m.group(0).replace("\r", "").replace("\n", " ") if m else None

    return {
        "title": _grab_after(flat, _TITLE_KEYS, reject_prefix=("统一社会信用代码",)),
        "amount_upper": amount_upper,
        "amount_lower": amount_lower,
        "project_name_raw": _extract_project(flat),
        "remarks": remarks,
        "other_info": other_info,
        # 本地引擎精度低于 LLM 视觉, 固定 medium。
        # 注意: 这是**OCR 识别置信度**, 与已废除的 match_confidence 无关,
        #MUST NOT 用它推导 match_status。
        "confidence": "medium",
        "engine": ENGINE,
    }


# ---------------------------------------------------------------------------
# 子进程
# ---------------------------------------------------------------------------
def _init_worker(lang: str, threads_per_worker: int = DEFAULT_THREADS_PER_WORKER):
    global _OCR
    # 子进程独立 stdout fd,引擎初始化的日志必须自己挡到 stderr
    with contextlib.redirect_stdout(sys.stderr):
        from rapidocr import RapidOCR
        from rapidocr.utils.typings import LangDet, LangRec, ModelType, OCRVersion

        if lang != "ch":
            raise ValueError(f"PP-OCRv6 small 当前仅启用中文票据模型, lang={lang!r}")
        threads = max(1, min(int(threads_per_worker), MAX_THREADS_PER_WORKER))
        _OCR = RapidOCR(params={
            "Global.log_level": "error",
            "Global.use_cls": False,
            "EngineConfig.onnxruntime.intra_op_num_threads": threads,
            "EngineConfig.onnxruntime.inter_op_num_threads": 1,
            "Det.ocr_version": OCRVersion.PPOCRV6,
            "Det.model_type": ModelType.SMALL,
            "Det.lang_type": LangDet.CH,
            "Det.limit_side_len": 736,
            "Det.limit_type": "min",
            "Rec.ocr_version": OCRVersion.PPOCRV6,
            "Rec.model_type": ModelType.SMALL,
            "Rec.lang_type": LangRec.CH,
        })


def _ocr_images(images) -> str:
    lines = []
    with contextlib.redirect_stdout(sys.stderr):
        for path in images:
            # 电子票据均为正向页面，关闭方向分类；异常旋转票据由字段完整性门禁拦截。
            result = _OCR(path, use_cls=False)
            for txt in result.txts or ():
                if txt:
                    lines.append(str(txt))
    return "\n".join(lines)


def _recognize_one(task: tuple) -> dict:
    """(item, output_dir) →摘要 dict; 全文与字段落盘, 不回上下文。"""
    item, output_dir = task
    started = time.time()
    seq = item.get("seq")
    out = {"seq": seq, "md5": item.get("md5") or "", "pdf_path": item.get("pdf_path") or ""}
    try:
        images = list(item.get("images") or [])
        if not images:
            raise RuntimeError("缺少 images(需先用 pdf_to_images.py 光栅化)")

        raw_text = _ocr_images(images)
        fields = extract_fields(raw_text)
        payload = {"seq": seq, "md5": out["md5"], "pdf_path": out["pdf_path"]}
        payload.update(fields)
        payload["raw_ocr_text"] = raw_text

        os.makedirs(output_dir, exist_ok=True)
        json_path = os.path.join(output_dir, f"{seq if seq is not None else out['md5'][:8]}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        has_title = bool(fields.get("title"))
        has_amount = bool(fields.get("amount_upper") or fields.get("amount_lower"))
        out.update(
            {
                "success": True,
                "json_path": json_path,
                "has_title": has_title,
                "has_amount": has_amount,
                "incomplete": not (has_title and has_amount),
                "elapsed_ms": int((time.time() - started) * 1000),
            }
        )
    except Exception as e:  # noqa: BLE001
        out.update(
            {
                "success": False,
                "error": str(e),
                "incomplete": True,
                "elapsed_ms": int((time.time() - started) * 1000),
            }
        )
    return out


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def process(input_data: dict) -> dict:
    items = input_data.get("items") or []
    output_dir = str(input_data.get("output_dir") or "").strip()
    if not items:
        return {"success": False, "engine": ENGINE, "error": "items 为空"}
    if not output_dir:
        return {"success": False, "engine": ENGINE, "error": "缺少 output_dir(OCR 结果必须落盘)"}

    install_log = ""
    if not _probe_engine():
        if not bool(input_data.get("auto_install", True)):
            return {
                "success": False,
                "engine": ENGINE,
                "error": "本地 OCR 引擎缺失且 auto_install=false",
                "fix_hint": f"{sys.executable} -m pip install 'onnxruntime>=1.17,<2' "
                            "'opencv-python-headless>=4.6,<5' && "
                            f"{sys.executable} -m pip install --no-deps 'rapidocr==3.9.2'",
                "fallback_hint": "或改为分多次走精细模式(每批 ≤100 张)",
            }
        ok, install_log = _try_auto_install()
        if not ok:
            return {
                "success": False,
                "engine": ENGINE,
                "error": "本地 OCR 引擎不可用: RapidOCR / ONNX Runtime 安装失败",
                "attempted_remediation": install_log,
                "fallback_hint": "请改为分多次走精细模式(每批 ≤100 张, LLM 视觉识别); "
                                "严禁静默使用低质结果继续流程",
            }

    lang = str(input_data.get("lang") or "ch")
    workers = int(input_data.get("workers", DEFAULT_WORKERS) or DEFAULT_WORKERS)
    workers = max(1, min(workers, MAX_WORKERS))
    threads_per_worker = int(
        input_data.get("threads_per_worker", DEFAULT_THREADS_PER_WORKER)
        or DEFAULT_THREADS_PER_WORKER
    )
    threads_per_worker = max(1, min(threads_per_worker, MAX_THREADS_PER_WORKER))

    tasks = [(item, output_dir) for item in items]
    effective_pool_workers = min(workers, len(tasks))
    result_callback = input_data.get("_result_callback")
    started = time.time()
    results = []
    fallback_to_serial = False
    fallback_reason = ""

    def publish(result):
        results.append(result)
        if callable(result_callback):
            try:
                result_callback(result)
            except Exception as e:  # noqa: BLE001
                sys.stderr.write(f"OCR result_callback 执行失败: {e}\n")
                sys.stderr.flush()

    if effective_pool_workers == 1:
        _init_worker(lang, threads_per_worker)
        results = []
        for idx, t in enumerate(tasks, 1):
            publish(_recognize_one(t))
            sys.stderr.write(f"OCR 进度 {idx}/{len(tasks)}\n")
            sys.stderr.flush()
    else:
        failed_tasks = []
        try:
            with ProcessPoolExecutor(
                max_workers=effective_pool_workers,
                initializer=_init_worker,
                initargs=(lang, threads_per_worker),
            ) as pool:
                futures = {pool.submit(_recognize_one, t): t for t in tasks}
                done = 0
                for fut in as_completed(futures):
                    task = futures[fut]
                    try:
                        result = fut.result()
                    except Exception as e:  # noqa: BLE001
                        failed_tasks.append(task)
                        sys.stderr.write(
                            f"OCR 并发任务 seq={task[0].get('seq')} 失败，将单张串行重试: {e}\n"
                        )
                    else:
                        if result.get("success"):
                            publish(result)
                        else:
                            failed_tasks.append(task)
                    done += 1
                    sys.stderr.write(f"OCR 进度 {done}/{len(tasks)}\n")
                    sys.stderr.flush()
        except Exception as e:  # noqa: BLE001
            # 保留已成功结果，只重试未完成项；避免整批从头串行重跑。
            done_seqs = {r.get("seq") for r in results if r.get("success")}
            failed_tasks.extend(t for t in tasks if t[0].get("seq") not in done_seqs)
            fallback_reason = str(e)

        if failed_tasks:
            fallback_to_serial = True
            # 异常路径可能把同一任务放入多次，按 seq 去重。
            pending_by_seq = {t[0].get("seq"): t for t in failed_tasks}
            _init_worker(lang, threads_per_worker)
            for task in pending_by_seq.values():
                publish(_recognize_one(task))
            fallback_reason = fallback_reason or "个别并发任务失败"
            install_log = (
                install_log
                + f"\n并发异常, 仅对 {len(pending_by_seq)} 张执行串行重试: {fallback_reason}"
            ).strip()

    order = {t[0].get("seq"): i for i, t in enumerate(tasks)}
    results.sort(key=lambda r: order.get(r.get("seq"), 0))

    elapsed_ms = int((time.time() - started) * 1000)
    succeeded = sum(1 for r in results if r.get("success"))
    incomplete = sum(1 for r in results if r.get("incomplete"))

    out = {
        "success": succeeded > 0,
        "engine": ENGINE,
        "output_dir": output_dir,
        "workers": workers,
        "threads_per_worker": threads_per_worker,
        "total_inference_threads": workers * threads_per_worker,
        "effective_workers": 1 if fallback_to_serial else effective_pool_workers,
        "effective_total_inference_threads": (
            threads_per_worker
            if fallback_to_serial
            else effective_pool_workers * threads_per_worker
        ),
        "model": MODEL_NAME,
        "runtime": RUNTIME_NAME,
        "runtime_bundle": RUNTIME_BUNDLE_VERSION,
        "orientation_classifier": False,
        "fallback_to_serial": fallback_to_serial,
        "fallback_reason": fallback_reason,
        "total": len(results),
        "succeeded": succeeded,
        "failed": len(results) - succeeded,
        "incomplete": incomplete,
        "elapsed_ms": elapsed_ms,
        "avg_ms_per_file": int(elapsed_ms / len(results)) if results else 0,
        "results": results,
        "precision_notice": "本批使用本地识别引擎, 精度低于 LLM 视觉, 请在确认页面重点核对",
    }
    if succeeded == 0:
        out["error"] = "全部票据本地识别失败, 详见 results"
    if install_log:
        out["install_log"] = install_log
    return out


def main():
    # ⚠️ Windows 实测: stdout 为管道时用 locale 编码(GBK), 中文 JSON 会写成 GBK 字节,
    #    UTF-8 读取方直接 UnicodeDecodeError。OCR 结果必然含中文, 必须显式改 UTF-8。
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="JSON 入参")
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
