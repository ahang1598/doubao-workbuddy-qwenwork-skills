"""用无头浏览器 (Playwright / Chromium) 对生成的 HTML 报告做真渲染校验。

设计：直接以 file:// 加载报告 HTML，注册 pageerror / console 监听 + 触发懒错误路径，
再 evaluate 诊断 ECharts 实例/容器状态，据此判定报告是否会白屏/报错。

公开入口：`run_browser_check(html_path, timeout=15) -> RuntimeCheckResult | None`
- 返回 None 表示无头浏览器不可用（未安装 playwright 或未安装 Chromium），
  调用方应降级为纯静态校验
- 返回 dict 表示已完成真渲染校验，包含 ok/issues/warnings/page_errors/console_errors/echarts

健壮性保障：
- 探活：import playwright 失败 / 浏览器启动失败 → 返回 None，诊断记入 _LOCATE_DIAG
- Chromium 直接支持 file:// 协议，无需本地 http server / 跨域脚本本地化
- 整体硬上限 timeout 秒；单页操作超时不阻塞整体降级
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote, unquote

# Windows 兼容：默认 stdout 编码是 cp936（GBK），中文 JSON 输出会乱码。
# 显式重设为 utf-8 + errors='replace' 保证跨平台一致输出。
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (ValueError, AttributeError):
        pass  # 非 TTY 或已重定向时可能失败，不影响功能


# ── 超时配置 ───────────────────────────────────────────────────────────
_DEFAULT_TOTAL_TIMEOUT = 30      # 整体硬截止默认值（秒）
_WAIT_FOR_NETWORKIDLE_MS = 5000  # networkidle 等待上限
_LAYOUT_SETTLE_SEC = 0.8         # 渲染稳定 + pageerror flush
_TRIGGER_SETTLE_SEC = 0.6        # resize/hover 触发后等异步 error handler flush
_PAGEERROR_RETRY_DELAY_SEC = 0.5 # page_errors 为空时的二次抓取间隔


# ── 探活诊断 ───────────────────────────────────────────────────────────
# 全局 locate 诊断记录，html_report 降级时回传给模型作为 reason。
_LOCATE_DIAG: list[dict] = []


def get_locate_diag() -> list[dict]:
    """供调用方读取无头浏览器探活的诊断细节。"""
    return list(_LOCATE_DIAG)


def _locate_playwright():
    """尝试加载 playwright.sync_api，**任何异常都静默降级**，记录到 _LOCATE_DIAG。

    返回 sync_playwright 可调用对象；不可用返回 None。
    调用方可读 get_locate_diag() 拿到详细原因传到 transcript。
    """
    _LOCATE_DIAG.clear()
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
        _LOCATE_DIAG.append({"candidate": "playwright.sync_api", "status": "ok"})
        return sync_playwright
    except ImportError as e:
        _LOCATE_DIAG.append({
            "candidate": "playwright", "status": "unavailable",
            "error_type": "ImportError",
            "error": str(e)[:200],
        })
    except Exception as e:  # noqa: BLE001 - 兜底，绝不让异常逃出
        _LOCATE_DIAG.append({
            "candidate": "playwright", "status": "unexpected_error",
            "error_type": type(e).__name__,
            "error": str(e)[:200],
        })
    return None


# ── Early error listener（页面加载最早期注册，接住 hook 装上前的错）──────
#
# 通过 add_init_script 在任何业务脚本 / ECharts 加载之前注册 window.error /
# unhandledrejection，把错存到 window.__rewindEarlyErrors。
# 双保险：addEventListener + onerror + unhandledrejection + onunhandledrejection。
_EARLY_LISTENER_INIT = (
    "(function(){"
    "var errs=window.__rewindEarlyErrors=window.__rewindEarlyErrors||[];"
    "function push(msg,file,ln,col,stk,via){"
    "errs.push({message:msg||'unknown',filename:file||'',lineno:ln||0,colno:col||0,"
    "stack:stk||'',via:via,ts:Date.now()});"
    "}"
    "window.addEventListener('error',function(e){"
    "push(e.message||(e.error&&e.error.message),e.filename,e.lineno,e.colno,"
    "e.error&&e.error.stack,'addEventListener');"
    "},true);"
    "var _pre=window.onerror;"
    "window.onerror=function(msg,src,ln,col,err){"
    "push(msg,src,ln,col,err&&err.stack,'onerror');"
    "if(typeof _pre==='function'){try{return _pre.apply(this,arguments);}catch(e){}}"
    "return false;"
    "};"
    "window.addEventListener('unhandledrejection',function(e){"
    "var r=e.reason;"
    "push('Unhandled rejection: '+((r&&r.message)||String(r)),"
    "'unhandledrejection',0,0,r&&r.stack,'addEventListener');"
    "},true);"
    "var _preR=window.onunhandledrejection;"
    "window.onunhandledrejection=function(e){"
    "var r=e.reason;"
    "push('Unhandled rejection: '+((r&&r.message)||String(r)),"
    "'onunhandledrejection',0,0,r&&r.stack,'onunhandledrejection');"
    "if(typeof _preR==='function'){try{return _preR.apply(this,arguments);}catch(e){}}"
    "};"
    "})();"
)


# ── 诊断 JS（在页面上跑，返回 ECharts/容器/库 状态）──────────────────

TRIGGER_FN = r"""
() => {
  // 主动触发常见"懒触发"错误路径：
  // 1) window.resize → ECharts chart.resize() 内部错（如 'c.resize is not a function'）
  // 2) chart 中心 mouseover/mousemove → tooltip formatter / getAttribute 错
  // 注意：仅触发可见 chart，避免 0x0 容器抛额外错（display:none tab 内 chart 跳过）。
  try { window.dispatchEvent(new Event('resize')); } catch(e) {}
  if (typeof echarts === 'undefined') return { triggered: 0 };
  let triggered = 0;
  document.querySelectorAll('*').forEach(el => {
    let inst = null;
    try { inst = echarts.getInstanceByDom(el); } catch(e) {}
    if (!inst) return;
    const r = el.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) return; // 跳过隐藏 / 未挂载的 chart
    const cx = r.left + r.width / 2;
    const cy = r.top + r.height / 2;
    ['mouseover', 'mousemove'].forEach(t => {
      try {
        el.dispatchEvent(new MouseEvent(t, { clientX: cx, clientY: cy, bubbles: true }));
      } catch (e) {}
    });
    triggered++;
  });
  return { triggered };
}
"""

DIAG_FN = r"""
() => {
  const out = {
    hasEcharts: typeof echarts !== 'undefined',
    echartsCount: 0, instances: [],
    chartLikeContainers: 0, chartLibLoaded: false,
    canvasCount: 0, staticImgCount: 0,
  };
  out.chartLikeContainers = document.querySelectorAll(
    '[id*="chart" i], [class*="chart" i], [id*="figure" i], [class*="figure" i]'
  ).length;
  out.canvasCount = document.querySelectorAll('canvas').length;
  out.staticImgCount = Array.from(document.querySelectorAll('img[src]'))
    .filter(i => !/^data:/.test(i.getAttribute('src') || '')).length;
  const scripts = Array.from(document.scripts).map(s => s.src || '');
  out.chartLibLoaded = scripts.some(s => /echarts|chart\.js|chartjs|d3\.|plotly|highcharts/i.test(s))
    || typeof echarts !== 'undefined' || typeof Chart !== 'undefined'
    || typeof d3 !== 'undefined' || typeof Plotly !== 'undefined';
  if (!out.hasEcharts) return out;
  // 判定 chart 是否处于 display:none 祖先内（合法的 tab/折叠 UI）
  const isInHiddenAncestor = (el) => {
    for (let n = el; n && n !== document.body; n = n.parentElement) {
      const st = window.getComputedStyle(n);
      if (st && (st.display === 'none' || st.visibility === 'hidden')) return true;
    }
    return false;
  };
  // 递归数 numeric — 处理 radar (value 是 array) / treemap-sunburst (children) 等
  // 结构化 data 形态。深度上限 10 防意外大数据循环。
  const countNumeric = (arr, depth) => {
    let n = 0, nz = 0;
    if (!Array.isArray(arr) || depth > 10) return { n, nz };
    for (const v of arr) {
      if (v === null || v === undefined) continue;
      if (typeof v === 'number') {
        if (isFinite(v)) { n++; if (v !== 0) nz++; }
      } else if (Array.isArray(v)) {
        for (const x of v) if (typeof x === 'number' && isFinite(x)) { n++; if (x !== 0) nz++; }
      } else if (typeof v === 'object') {
        if (typeof v.value === 'number' && isFinite(v.value)) {
          n++; if (v.value !== 0) nz++;
        } else if (Array.isArray(v.value)) {
          for (const x of v.value) if (typeof x === 'number' && isFinite(x)) { n++; if (x !== 0) nz++; }
        }
        if (Array.isArray(v.children)) {
          const sub = countNumeric(v.children, depth + 1);
          n += sub.n; nz += sub.nz;
        }
      }
    }
    return { n, nz };
  };
  document.querySelectorAll('*').forEach(el => {
    let inst = null;
    try { inst = echarts.getInstanceByDom(el); } catch(e) {}
    if (!inst) return;
    let opt = {};
    try { opt = inst.getOption() || {}; } catch(e) {}
    const series = (opt.series || []).map(s => {
      const arr = Array.isArray(s.data) ? s.data : null;
      const counts = arr ? countNumeric(arr, 0) : { n: 0, nz: 0 };
      return {
        type: s.type,
        dataLen: arr ? arr.length : (s.data == null ? -1 : -2),
        numericCount: counts.n,
        nonZeroCount: counts.nz,
      };
    });
    const xAxis = (opt.xAxis || []).map(a => ({
      dataLen: Array.isArray(a.data) ? a.data.length : (a.data == null ? -1 : -2)
    }));
    const r = el.getBoundingClientRect();
    out.instances.push({
      id: el.id || null,
      width: Math.round(r.width),
      height: Math.round(r.height),
      hiddenByAncestor: isInHiddenAncestor(el),
      series, xAxis
    });
  });
  out.echartsCount = out.instances.length;
  // 反向扫: 找带 id 的 chart/figure 容器, 看是否被 echarts init
  // 4 重启发式过滤防误报: 已 init / 内部有 canvas|svg / 内部有实质内容 / 容器过小
  out.orphanChartDivs = [];
  document.querySelectorAll('div[id*="chart" i], div[id*="figure" i]').forEach(el => {
    let inst = null;
    try { inst = echarts.getInstanceByDom(el); } catch(e) {}
    if (inst) return;
    if (el.querySelector('canvas, svg')) return;
    if ((el.textContent || '').trim().length > 20) return;
    if (el.querySelector('img[src]:not([src^="data:"])')) return;
    const r = el.getBoundingClientRect();
    if (r.width < 80 || r.height < 50) return;
    out.orphanChartDivs.push({ id: el.id, width: Math.round(r.width), height: Math.round(r.height) });
  });
  return out;
}
"""


# ── 错误信息处理 ──────────────────────────────────────────────────────

def _format_source_location(source: str) -> str:
    """把 'file:///path/encoded%20name.html:LINE:COL' → '<filename>:LINE:COL'。
    便于模型直接定位到 HTML 哪一行。
    """
    if not source:
        return ""
    m = re.match(r'^(.*?)(:\d+(?::\d+)?)$', source)
    if not m:
        return source
    url_part, line_col = m.group(1), m.group(2)
    try:
        last = url_part.rsplit("/", 1)[-1]
        return f"{unquote(last)}{line_col}"
    except Exception:
        return f"{url_part.rsplit('/', 1)[-1]}{line_col}"


def _summarize_stack(stack: str, max_frames: int = 2) -> str:
    """取 stack 前几帧 + 同样 URL→filename 化。空 → 空字符串。"""
    if not stack:
        return ""
    frames = [ln.strip() for ln in stack.splitlines() if ln.strip()][:max_frames]
    cleaned = []
    for f in frames:
        cleaned.append(re.sub(
            r'(?:file://|https?://[^/\s]+)/([^\s)]+)',
            lambda m: unquote(m.group(1).rsplit("/", 1)[-1]),
            f,
        ))
    return " | ".join(cleaned)


def _is_opaque_error(msg: str) -> bool:
    """识别因 CORS 跨域脚本而无法定位的笼统 'Script error.' 类消息。
    这类错误信息量极低且常因为 hover/resize 触发跨域 CDN 脚本的 catch-all
    handler 产生，难以判定是真 bug 还是浏览器策略，**不应据此标 fail**。
    """
    if not msg: return False
    s = msg.strip().lower()
    return s in ("script error.", "script error", "[object event]")


def _is_echarts_lifecycle_error(msg: str) -> bool:
    """识别 ECharts 内部 lifecycle 错（如 c.resize is not a function）。

    这类错误特征：
    - resize handler 内部对已销毁/未初始化的 chart 实例调 .resize()
    - 错误存在但图正常显示，刷新后消失
    - 我们主动 dispatchEvent('resize') 触发，正常浏览器使用也可能遇到
    - 单变量名（c/e/d 等）后跟 .resize/.dispose 是 ECharts minified 代码典型模式
    """
    if not msg: return False
    return bool(re.search(r'\b[a-z]\.(resize|dispose|render|setOption)\s+is not a function',
                          msg, re.IGNORECASE))


def _analyse(diag, page_errors, console_errors,
             baseline_page_errors=None) -> tuple[bool, list[str], list[str]]:
    """分析渲染信号 → (ok, errors, warnings)。

    判定原则：**允许漏检不得误报**。
    - errors 才参与 ok 判定；warnings 仅提示不阻塞。
    - 信号必须具体可定位（line:col / chart id / 容器尺寸），不靠模糊启发式。
    """
    errors: list[str] = []
    warnings: list[str] = []

    # ── page_errors ────
    for e in page_errors or []:
        msg = e.get("message", "")
        src = e.get("source", "")
        loc = _format_source_location(src)
        stack_brief = _summarize_stack(e.get("stack", ""))
        # 跨域笼统错误（"Script error." 无定位）→ 跳过（无法定位 + 高 FP 风险）
        if _is_opaque_error(msg) and not loc.strip(":0"):
            continue
        parts = [f"[pageerror] {msg}"]
        if loc: parts.append(f"位置: {loc}")
        if stack_brief and stack_brief != loc: parts.append(f"调用栈: {stack_brief}")
        line = "  ".join(parts)
        # ECharts 内部 lifecycle 错（c.resize / e.dispose 等）→ warning 不参与 ok
        if _is_echarts_lifecycle_error(msg):
            warnings.append(f"[echarts-lifecycle] {line}（ECharts 内部 resize/dispose 错，通常不影响渲染）")
        else:
            errors.append(line)

    # ── console_errors ────
    for m in console_errors or []:
        txt = m.get("message") or m.get("text") or str(m)
        if any(s in txt for s in ("favicon", "DevTools")): continue
        if _is_opaque_error(txt): continue
        # 纯版本/弃用告警（不影响渲染）→ warning 不 error
        stripped = txt.lstrip()
        if (stripped.startswith("WARNING:") or stripped.startswith("DEPRECATED:")
                or stripped.startswith("[Deprecation]")):
            warnings.append(f"[console.warn] {txt[:200]}")
            continue
        loc = _format_source_location(m.get("source", ""))
        errors.append(f"[console.error] {txt}" + (f"  位置: {loc}" if loc else ""))

    # ── diag 信号（仅基于 chart 实例的具体证据，不靠 chart-div / lib 启发式）────
    if diag:
        echarts_count = diag.get("echartsCount", 0)
        chart_div = diag.get("chartLikeContainers", 0)
        img_count = diag.get("staticImgCount", 0)
        if echarts_count == 0 and chart_div > 0 and img_count > 0:
            severity = ("多 chart 占位 + 多静态图 (高概率 matplotlib/PIL 替代)"
                        if chart_div >= 2 and img_count >= 2
                        else "单图场景 (可能是合理插图)")
            warnings.append(
                f"[no-chart-lib] 页面含 {chart_div} 个 chart 占位 div + "
                f"{img_count} 张静态图片，{severity}。如 prompt 要求交互图表请改 ECharts。"
            )

        for inst in diag.get("instances", []):
            cid = inst.get("id") or "<no-id>"
            # display:none 祖先（tab/折叠 UI）合法：跳过 layout 检查但仍校验数据
            if (inst["width"] == 0 or inst["height"] == 0) and not inst.get("hiddenByAncestor"):
                errors.append(f"chart '{cid}' 容器尺寸 {inst['width']}x{inst['height']}（layout 异常）")
            series_arr = inst.get("series") or []
            if not series_arr and not inst.get("hiddenByAncestor"):
                errors.append(
                    f"chart '{cid}' 无 series 配置（chart 实例创建但 series=[]，"
                    f"模型缺 setOption 或 setOption 失败）— 渲染白图"
                )
                continue
            for s in series_arr:
                if s["dataLen"] == 0:
                    errors.append(f"chart '{cid}' series.{s['type']}.data=[] (空数据)")
                elif s["dataLen"] == -1:
                    errors.append(f"chart '{cid}' series.{s['type']}.data=null")
                else:
                    numeric = s.get("numericCount", -1)
                    if numeric == 0:
                        errors.append(
                            f"chart '{cid}' series.{s['type']}.data 共 {s['dataLen']} 项但"
                            f"无有效数值（全 null/NaN/非数字）— 渲染白图"
                        )
                    elif s["dataLen"] >= 5 and s.get("nonZeroCount", -1) == 0 and numeric > 0:
                        warnings.append(
                            f"[all-zero-data] chart '{cid}' series.{s['type']}.data 共 "
                            f"{s['dataLen']} 项数值全为 0 — 可能数据未填充, 也可能真为 0"
                        )
            for ax in inst.get("xAxis", []):
                if ax["dataLen"] == 0:
                    errors.append(f"chart '{cid}' xAxis.data=[] (空轴标签)")

        # ── orphan chart div: 有 id 的 chart/figure 容器但未被 echarts init ──
        orphans = diag.get("orphanChartDivs") or []
        if orphans:
            ids = [o.get("id") for o in orphans]
            errors.append(
                f"orphan_chart_div: {len(orphans)} 个 chart 容器未渲染 (有 id 但无 echarts.init): "
                f"{ids[:8]}{' ...' if len(ids) > 8 else ''} — 用户视觉上是白图。"
                f"修复: 给每个容器加 echarts.init(document.getElementById('<id>')).setOption({{...}})."
            )

    ok = len(errors) == 0
    return ok, errors, warnings


# ── 公开入口 ───────────────────────────────────────────────────────────

def run_browser_check(
    html_path: str | Path,
    timeout: float = _DEFAULT_TOTAL_TIMEOUT,
    **_ignored: Any,
) -> Optional[dict[str, Any]]:
    """对单个 HTML 做无头浏览器真渲染校验。

    返回 None 表示无头浏览器不可用（未安装 playwright 或未安装 Chromium），
    调用方应降级为纯静态校验。

    成功时返回 dict:
        {
          ok: bool,
          source: "headless-browser",
          issues: list[str],       # 人类可读问题（拼到上游 errors）
          warnings: list[str],
          page_errors: list[{msg, source}],
          console_errors: list[str],
          echarts: {echartsCount, chartLikeContainers, ..., instances: [...]},
          elapsed_ms: int,
        }

    额外 kwargs（如旧版 localize* 参数）被忽略，保持向后兼容。
    """
    sync_playwright = _locate_playwright()
    if sync_playwright is None:
        # 降级：playwright 不可用，html_report.py 会读 get_locate_diag() 拿详细原因
        return None

    p = Path(html_path).resolve()
    if not p.is_file():
        return {
            "ok": False, "source": "headless-browser",
            "issues": [f"文件不存在: {p}"], "warnings": [],
            "page_errors": [], "console_errors": [], "echarts": {},
            "elapsed_ms": 0,
        }

    t0 = time.time()
    url = "file://" + quote(str(p))

    page_errors: list[dict] = []
    console_errors: list[dict] = []

    try:
        with sync_playwright() as pw:
            try:
                browser = pw.chromium.launch(headless=True)
            except Exception as e:  # noqa: BLE001 - 浏览器未安装 / 启动失败 → 降级
                _LOCATE_DIAG.append({
                    "candidate": "chromium", "status": "browser_launch_failed",
                    "error_type": type(e).__name__,
                    "error": str(e)[:200],
                })
                return None

            try:
                context = browser.new_context(viewport={"width": 1440, "height": 900})
                context.add_init_script(_EARLY_LISTENER_INIT)
                page = context.new_page()

                def _on_pageerror(exc: Any) -> None:
                    try:
                        msg = getattr(exc, "message", None) or str(exc)
                        stack = getattr(exc, "stack", "") or ""
                    except Exception:
                        msg, stack = str(exc), ""
                    # 从 stack 首帧尝试抽取 source 位置
                    src = ""
                    m = re.search(r'((?:file://|https?://)[^\s)]+:\d+:\d+)', stack or "")
                    if m:
                        src = m.group(1)
                    page_errors.append({"message": msg, "source": src, "stack": stack})

                def _on_console(msg: Any) -> None:
                    try:
                        if msg.type != "error":
                            return
                        loc = msg.location or {}
                        src = ""
                        if loc.get("url"):
                            src = f"{loc.get('url')}:{loc.get('lineNumber', 0)}:{loc.get('columnNumber', 0)}"
                        console_errors.append({"message": msg.text, "source": src})
                    except Exception:
                        pass

                page.on("pageerror", _on_pageerror)
                page.on("console", _on_console)

                deadline = t0 + timeout
                goto_timeout_ms = max(1000, int((deadline - time.time()) * 1000))
                try:
                    page.goto(url, wait_until="networkidle",
                              timeout=min(goto_timeout_ms, _WAIT_FOR_NETWORKIDLE_MS + 3000))
                except Exception:
                    # networkidle 在外部 CDN 不稳定时可能达不到；已加载即可继续
                    pass

                time.sleep(_LAYOUT_SETTLE_SEC)

                # 主动触发懒发错误：resize + 每个可见 chart hover
                try:
                    page.evaluate(TRIGGER_FN)
                except Exception:
                    pass
                time.sleep(_TRIGGER_SETTLE_SEC)

                # 合并 early-listener buffer 里的错（去重）
                try:
                    early = page.evaluate("() => (window.__rewindEarlyErrors || []).slice(0, 100)") or []
                except Exception:
                    early = []
                existing = {(e.get("message") or "").strip() for e in page_errors}
                for ee in early:
                    if not isinstance(ee, dict):
                        continue
                    m = (ee.get("message") or "").strip()
                    if not m or m in existing:
                        continue
                    file = ee.get("filename") or ""
                    ln = ee.get("lineno") or 0
                    col = ee.get("colno") or 0
                    src = f"{file}:{ln}:{col}" if file else ""
                    page_errors.append({
                        "message": m, "source": src,
                        "stack": ee.get("stack") or "", "_origin": "early-listener",
                    })
                    existing.add(m)

                try:
                    diag = page.evaluate(DIAG_FN) or {}
                except Exception:
                    diag = {}

                # 闪烁修补：page_errors/console 都空时短暂等待再抓一次 early buffer
                if (not page_errors and not console_errors
                        and time.time() < deadline - _PAGEERROR_RETRY_DELAY_SEC):
                    time.sleep(_PAGEERROR_RETRY_DELAY_SEC)
                    try:
                        early2 = page.evaluate("() => (window.__rewindEarlyErrors || []).slice(0, 100)") or []
                    except Exception:
                        early2 = []
                    for ee in early2:
                        if not isinstance(ee, dict):
                            continue
                        m = (ee.get("message") or "").strip()
                        if not m or m in existing:
                            continue
                        page_errors.append({
                            "message": m, "source": "", "stack": ee.get("stack") or "",
                            "_origin": "early-listener",
                        })
                        existing.add(m)

                ok, issues, warnings_list = _analyse(diag, page_errors, console_errors)
                return {
                    "ok": ok,
                    "source": "headless-browser",
                    "issues": issues,
                    "warnings": warnings_list,
                    "page_errors": [{"msg": e.get("message"), "source": e.get("source")} for e in page_errors],
                    "console_errors": [m.get("message") or m.get("text") for m in console_errors],
                    "echarts": diag,
                    "elapsed_ms": int((time.time() - t0) * 1000),
                }
            finally:
                try:
                    browser.close()
                except Exception:
                    pass
    except Exception as e:  # noqa: BLE001 - playwright runtime 兜底 → 降级
        _LOCATE_DIAG.append({
            "candidate": "playwright-runtime", "status": "runtime_error",
            "error_type": type(e).__name__,
            "error": str(e)[:200],
        })
        return _err_result(t0, f"无头浏览器运行失败: {type(e).__name__}: {e}")


def _err_result(t0: float, msg: str,
                warnings: Optional[list[str]] = None) -> dict[str, Any]:
    """无头浏览器调用失败 / 超时等降级路径的统一返回。"""
    return {
        "ok": False, "source": "headless-browser",
        "issues": [msg], "warnings": list(warnings or []),
        "page_errors": [], "console_errors": [], "echarts": {},
        "elapsed_ms": int((time.time() - t0) * 1000),
    }


# ── CLI（独立使用 / 调试）──────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="单独跑无头浏览器真渲染校验")
    ap.add_argument("html", help="HTML 文件路径")
    ap.add_argument("--timeout", type=float, default=_DEFAULT_TOTAL_TIMEOUT)
    ns = ap.parse_args()
    r = run_browser_check(ns.html, timeout=ns.timeout)
    if r is None:
        print(json.dumps({
            "ok": None,
            "reason": "无头浏览器不可用（请先 pip install playwright 并执行 playwright install chromium）",
            "locate_diag": get_locate_diag(),
        }, ensure_ascii=False, indent=2))
        sys.exit(2)
    print(json.dumps(r, ensure_ascii=False, indent=2))
    sys.exit(0 if r["ok"] else 1)
