#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
chart_generator.py — 图表生成器（方案 B：HTML 内嵌唯一承载）

功能：
  复用 chart_injector.py 里的 9 个图表函数，提供两种使用方式：

  1) **In-Memory API（推荐）**：由 md2html_report.py 在生成 HTML 时直接调用，
     返回 {key: svg_str} 字典，图表只内嵌在最终 HTML 中，不落地 SVG 文件。
     用函数 build_charts_inmemory(code, only=None) -> dict。

  2) **CLI（可选 / 对话模式备用）**：保留落地 SVG 文件的能力，
     仅在对话模式下需要可视化辅助时使用，报告模式不再调用。

用法（CLI 备用）：
  python scripts/chart_generator.py <股票代码>
  python scripts/chart_generator.py 300308 --outdir tmp/charts/300308

前置条件：
  FinancialData/{code}_fundamental.md / _fundamental.json / _realtime.json / _quote.md 已采集
  （由 trade_advisor.py / realtime_quote_enhanced.py 等脚本提前准备）
"""
import sys, os, re, json, argparse
from pathlib import Path

# Windows UTF-8 兜底
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# 复用 chart_injector 的所有图表函数（同目录下）
_SCRIPT_DIR = Path(__file__).resolve().parent  # scripts/
sys.path.insert(0, str(_SCRIPT_DIR))
from chart_injector import (  # noqa: E402
    chart_metric_cards,
    chart_kline,
    chart_annual_trend,
    chart_gross_margin,
    chart_cashflow,
    chart_fcf,
    chart_valuation_gauge,
    chart_peer_comparison,
    chart_winrate_dashboard,
    read_file,
    _fetch_kline_for_chart,
    FIN_DIR,
)

# ============================================================
# 配置
# ============================================================
WORKSPACE = Path(os.environ.get("CODEBUDDY_WORKSPACE", _SCRIPT_DIR.parent.parent.parent))

# 图表清单定义：(key, 文件名, 标题, 副标题, 注入锚点关键词或关键词列表, 默认必出)
#   注入锚点关键词 = 该图表在 Markdown 报告中应内嵌的位置（用于 Agent 决策）
#   支持两种写法：
#     - 字符串："关键价位"（向后兼容的单关键词）
#     - 列表/元组：("关键价位", "支撑压力", "技术面", ...) 按顺序 OR 匹配，命中任一即插入
#   多关键词会按列表顺序优先匹配（第一个命中的标题就定位）；
#   注入逻辑见 md2html_report.inject_charts_by_anchor，已扩展为 h2~h5 全扫描 + 主题兜底映射。
CHART_SPECS = [
    # 注：原 "metrics" 核心指标卡片已移除（用户反馈实用性低）。
    # v1.7.1（2026-05 修复）：anchor 关键词扩充为"具体子章节优先 → 业务主题次之"，
    # 避免泛词"基本面"误命中文档主标题（如"中际旭创基本面深度研究报告"H2）。
    ("kline",     "02_kline_120d.svg",      "近 120 日 K 线",    "MA5/10/20/60 + 布林带 + 真实成交量 + 支撑/压力位",
        ("投资概览卡", "核心结论", "关键价位", "支撑/压力", "技术面", "量价结构", "K 线", "K线"), True),
    ("price_excess", "02b_price_excess.svg", "股价走势 vs 沪深 300", "归一化双线 + 累计超额收益面积",
        ("市场表现", "投资概览卡", "核心结论", "走势", "K 线", "K线", "技术面"), False),
    ("annual",    "03_annual_trend.svg",    "年度营收与净利润趋势", "柱线混合 + YoY 增速",
        ("分业务预测矩阵", "盈利预测", "营收与净利润", "营收净利润", "分季度业绩", "业绩趋势", "财务表现", "企业层"), True),
    ("gm",        "04_gross_margin.svg",    "季度毛利率趋势",     "单季度毛利率走势",
        ("利润表预测", "近年财务轨迹", "关键财务比率矩阵", "盈利预测", "毛利率", "盈利能力", "产能与运营数据", "运营数据", "财务表现", "企业层"), True),
    ("cashflow",  "05_cashflow_structure.svg", "三项现金流年度结构", "经营 / 投资 / 筹资 现金流对比",
        ("三表预测", "关键财务比率矩阵", "现金流", "ROIC vs WACC", "ROIC", "盈利质量", "财务表现", "企业层"), True),
    ("fcf",       "06_fcf_trend.svg",       "自由现金流趋势",     "FCF = 经营现金流 − 资本开支",
        ("DCF 估值", "DCF估值", "三表预测", "自由现金流", "FCF", "盈利质量", "财务表现", "企业层"), True),
    ("valuation", "07_valuation_gauge.svg", "PE / PB 历史分位仪表盘", "当前分位与历史均值/±1σ 对照",
        # v1.7.3（2026-06 修复）：汇总决策报告 §4.1.5 标准标题为「估值与定价」（见 templates/intent1_full_report.md），
        # 旧 anchor 既无「估值与定价」也无「估值定价」，导致 valuation 图全部 miss → 落到文档末尾。
        # 这里把「估值与定价 / 估值定价」放到最高优先级（两者均为 §4.1.5 专属、不会误命中 4.1.2「高估值约束」
        # 或 4.1.3「估值压力」），其后再保留旧的 PE/PB-Band 等关键词作为 基本面报告兼容。
        ("PE/PB-Band 历史分位分析", "PE/PB-Band", "历史分位", "情景估值", "估值分位", "估值诊断", "估值锚", "估值与定价", "估值定价"), True),
    ("pe_band",   "07b_pe_band.svg",        "PE-Band 历史 5 年估值带", "5 档分位线 + 当前 PE-TTM 位置",
        ("PE/PB-Band 历史分位分析", "PE/PB-Band", "PE-Band", "历史估值带", "估值带", "估值分位"), False),
    ("peer",      "08_peer_comparison.svg", "同业对比（四维）",    "PE / PB / ROE / 毛利率 四维柱状对比",
        ("可比公司估值", "同业对比", "行业对比", "竞争格局", "同业比较", "行业层"), False),
    ("winrate",   "09_winrate_dashboard.svg", "胜率 / 赔率综合仪表盘", "六维胜率 × 风险收益比 × 仓位建议",
        ("三档目标价情景", "综合研判", "胜率", "赔率", "风险收益比", "交易计划", "六维加权"), False),
    ("timeline",  "10_timeline.svg",        "公司发展历程时间轴",   "关键里程碑事件交错排版",
        ("发展历程与定位", "发展历程", "公司沿革", "历史沿革", "大事记"), False),
    ("ownership", "11_ownership.svg",       "股权结构树图",        "实控人 → 主要股东 → 上市公司 → 子公司",
        ("公司画像", "公司定位", "公司概况", "股权结构与管理层", "股权结构", "实际控制", "股东"), False),
    ("sentiment", "12_sentiment_dashboard.svg", "行业景气度仪表盘", "3-4 项关键景气指标 + 微型趋势",
        ("全球光模块市场规模", "行业分析", "行业景气度", "行业层", "景气度"), False),
]

# ============================================================
# SVG 剥离：从 chart_injector 返回的 <div class="chart-card"> 中提取纯 <svg>...</svg>
# ============================================================
_SVG_EXTRACT_RE = re.compile(r'(<svg\b[^>]*>.*?</svg>)', re.DOTALL | re.IGNORECASE)


def _extract_standalone_svg(wrapped_html: str, title: str, subtitle: str) -> str:
    """从 chart_injector 返回的带 <div class="chart-card"> 外壳的 HTML 中，
    抽取内部 SVG，并补充标题/副标题到 SVG 上方（作为 <text> 节点嵌入 viewBox 上方）。

    为保持图表在对话/Markdown/浏览器中独立渲染，返回的是一个**带 XML 声明的完整 SVG 文档**。
    """
    if not wrapped_html or not wrapped_html.strip():
        return ''

    match = _SVG_EXTRACT_RE.search(wrapped_html)
    if not match:
        return ''

    svg_inner = match.group(1)

    # 解析 viewBox 用于计算标题条高度
    vb_match = re.search(r'viewBox="([\d.\s]+)"', svg_inner)
    if not vb_match:
        # viewBox 缺失时直接返回原 SVG + XML 头
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + svg_inner

    vb_parts = vb_match.group(1).split()
    if len(vb_parts) != 4:
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + svg_inner

    vb_x, vb_y, vb_w, vb_h = [float(x) for x in vb_parts]

    # 为了给标题/副标题腾空间，扩大 viewBox 上方 60px
    title_band_h = 60
    new_vb_y = vb_y - title_band_h
    new_vb_h = vb_h + title_band_h

    # 转义 XML
    def _esc(s):
        return (s or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    title_svg = (
        f'<rect x="{vb_x}" y="{new_vb_y}" width="{vb_w}" height="{title_band_h}" fill="#ffffff"/>'
        f'<text x="{vb_x + 20}" y="{new_vb_y + 26}" fill="#1a1a1a" '
        f'font-family="Segoe UI, Microsoft YaHei, sans-serif" font-size="20" font-weight="600">'
        f'{_esc(title)}</text>'
        f'<text x="{vb_x + 20}" y="{new_vb_y + 48}" fill="#6b7785" '
        f'font-family="Segoe UI, Microsoft YaHei, sans-serif" font-size="13">'
        f'{_esc(subtitle)}</text>'
    )

    # 重写 SVG 根标签
    new_svg = re.sub(
        r'viewBox="[\d.\s]+"',
        f'viewBox="{vb_x} {new_vb_y} {vb_w} {new_vb_h}"',
        svg_inner,
        count=1
    )
    # 在开标签后插入标题条
    new_svg = re.sub(
        r'(<svg\b[^>]*>)',
        r'\1' + title_svg,
        new_svg,
        count=1
    )
    # 确保有 xmlns（独立 SVG 文件必需）
    if 'xmlns=' not in new_svg[:300]:
        new_svg = new_svg.replace('<svg ', '<svg xmlns="http://www.w3.org/2000/svg" ', 1)
    # 统一背景（独立 SVG 不再被 chart-card 包裹，需要自带白色底）
    new_svg = re.sub(
        r'(<svg\b[^>]*>)',
        r'\1<rect x="' + str(vb_x) + r'" y="' + str(new_vb_y) + r'" width="' + str(vb_w) + r'" height="' + str(new_vb_h) + r'" fill="#ffffff"/>',
        new_svg,
        count=1
    )
    # 因为上一步又插入了一个 rect，要把标题条的 rect 去重 —— 实际标题条是在 svg open 之后插入的，
    # 但背景 rect 也是在 svg open 之后插入的（在标题条之前），最终顺序是：
    # <svg><rect 背景/><rect 标题条底/><text 标题/><text 副标题/>...原内容...</svg>
    # 顺序正确，无需调整

    return '<?xml version="1.0" encoding="UTF-8"?>\n' + new_svg


# ============================================================
# In-Memory API（方案 B 核心入口）
# ============================================================
def _load_data_sources(code: str) -> dict:
    """加载 FinancialData/ 下所有与图表相关的数据源，返回字典。"""
    fundamental_text = read_file(FIN_DIR / f"{code}_fundamental.md")

    realtime_data = None
    realtime_path = FIN_DIR / f"{code}_realtime.json"
    if realtime_path.exists():
        try:
            realtime_data = json.loads(realtime_path.read_text(encoding='utf-8'))
        except Exception:
            pass

    fundamental_json = None
    fundamental_json_path = FIN_DIR / f"{code}_fundamental.json"
    if fundamental_json_path.exists():
        try:
            fundamental_json = json.loads(fundamental_json_path.read_text(encoding='utf-8'))
        except Exception:
            pass

    peer_data = None
    peer_path = FIN_DIR / f"{code}_peers.json"
    if peer_path.exists():
        try:
            peer_data = json.loads(peer_path.read_text(encoding='utf-8'))
        except Exception:
            pass

    winrate_data = None
    winrate_path = FIN_DIR / f"{code}_winrate.json"
    if winrate_path.exists():
        try:
            winrate_data = json.loads(winrate_path.read_text(encoding='utf-8'))
        except Exception:
            pass

    return {
        "fundamental_text": fundamental_text,
        "realtime_data": realtime_data,
        "fundamental_json": fundamental_json,
        "peer_data": peer_data,
        "winrate_data": winrate_data,
    }


def _build_single_chart(code: str, spec: tuple, ds: dict, kline_records: list):
    """构建单张图表。返回 (key, title, subtitle, anchor, required, wrapped_or_empty, err_msg)"""
    key, fname, title, subtitle, anchor, required = spec
    try:
        if key == "kline":
            if kline_records:
                wrapped = chart_kline(kline_records, display_days=120)
            else:
                return (key, title, subtitle, anchor, required, '', "K 线数据获取失败")
        elif key == "price_excess":
            # 个股 + 沪深 300 同期日线 → 归一化双线 + 累计超额
            from chart_injector import chart_price_excess as _ce
            hs300 = _fetch_kline_for_chart("000300", 250) or []
            if not kline_records or not hs300:
                return (key, title, subtitle, anchor, required, '', "缺少股票或沪深 300 日线")
            wrapped = _ce(kline_records, hs300)
            if not wrapped:
                return (key, title, subtitle, anchor, required, '', "对齐数据不足（<30 日）")
        elif key == "annual":
            wrapped = chart_annual_trend(ds["fundamental_text"])
        elif key == "gm":
            wrapped = chart_gross_margin(ds["fundamental_text"])
        elif key == "cashflow":
            wrapped = chart_cashflow(ds["fundamental_text"])
        elif key == "fcf":
            wrapped = chart_fcf(ds["fundamental_text"])
        elif key == "valuation":
            wrapped = chart_valuation_gauge(ds["fundamental_text"])
        elif key == "pe_band":
            from chart_injector import chart_pe_band as _pb
            wrapped = _pb(ds["fundamental_text"])
            if not wrapped:
                return (key, title, subtitle, anchor, required, '', "未识别 §2.5-B0 PE-Band 表（需 基本面报告内含 5 档分位表）")
        elif key == "peer":
            if ds["peer_data"]:
                wrapped = chart_peer_comparison(ds["fundamental_text"], ds["peer_data"])
            else:
                return (key, title, subtitle, anchor, required, '', "未提供 peers.json")
        elif key == "winrate":
            if ds["winrate_data"]:
                wrapped = chart_winrate_dashboard(ds["winrate_data"])
            else:
                return (key, title, subtitle, anchor, required, '', "未提供 winrate.json")
        elif key == "timeline":
            from chart_injector import chart_timeline as _tl
            wrapped = _tl(ds["fundamental_text"])
            if not wrapped:
                return (key, title, subtitle, anchor, required, '', "未识别公司发展历程章节（需 ≥4 个里程碑）")
        elif key == "ownership":
            from chart_injector import chart_ownership as _ow
            wrapped = _ow(ds["fundamental_text"])
            if not wrapped:
                return (key, title, subtitle, anchor, required, '', "未识别股权结构表（需 ≥3 个股东）")
        elif key == "sentiment":
            from chart_injector import chart_sentiment as _se
            wrapped = _se(ds["fundamental_text"])
            if not wrapped:
                return (key, title, subtitle, anchor, required, '', "未识别行业景气度指标表（需 ≥3 项指标）")
        else:
            wrapped = ''
    except Exception as e:
        return (key, title, subtitle, anchor, required, '', f"生成失败: {e}")
    return (key, title, subtitle, anchor, required, wrapped, None)


def _load_kline_records(code: str, need_kline: bool):
    """K 线数据：优先读缓存，miss 再调 API。"""
    if not need_kline:
        return []
    kline_cache = FIN_DIR / f"{code}_kline.json"
    if kline_cache.exists():
        try:
            data = json.loads(kline_cache.read_text(encoding='utf-8'))
            records = data.get("K线数据") if isinstance(data, dict) else data
            if records:
                return records
        except Exception:
            pass
    return _fetch_kline_for_chart(code, 250)


def build_charts_inmemory(code: str, only: set = None, verbose: bool = False, report_type: str = "trade") -> list:
    """
    **方案 B 核心入口**：在内存中生成所有图表，返回清单列表。
    
    每个元素是 dict：
      {
        "key": "kline",
        "title": "近 120 日 K 线",
        "subtitle": "MA/布林带/支撑压力",
        "anchor": "关键价位",
        "required": True,
        "svg": "<svg ...>...</svg>",    # 纯 SVG 字符串（不含 XML 声明，便于直接内嵌）
        "ok": True,
        "err": None,
      }
    
    失败的图表 ok=False, svg='', err=错误消息；调用方决定是否展示错误占位。
    **此函数不写任何文件**，图表完全在内存中流转。

    v1.7.2（2026-05）：新增 report_type 参数：
      - "trade"（默认）：交易决策报告，含全部 13 张图（含 kline）
      - "fundamental"：基本面研究报告，**剔除 kline** 与其他不适用图
        （基本面框架关注 2-3 年盈利预测与估值，K 线短期技术指标与之不匹配；
         卖方研究所基本面报告同样不放 120 日 K 线）
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    ds = _load_data_sources(code)

    # v1.7.2：基本面研究报告剔除技术面短期图表
    _EXCLUDED_FOR_FUNDAMENTAL = {"kline"}

    tasks = []
    for spec in CHART_SPECS:
        if only is not None and spec[0] not in only:
            continue
        if report_type == "fundamental" and spec[0] in _EXCLUDED_FOR_FUNDAMENTAL:
            if verbose:
                print(f"  [skip] {spec[0]}: 基本面研究报告不适用（技术面短期指标）")
            continue
        tasks.append(spec)

    need_kline = any(spec[0] in ("kline", "price_excess") for spec in tasks)
    kline_records = _load_kline_records(code, need_kline)

    results = []
    with ThreadPoolExecutor(max_workers=min(9, max(1, len(tasks)))) as pool:
        futs = [pool.submit(_build_single_chart, code, spec, ds, kline_records) for spec in tasks]
        for fut in as_completed(futs):
            results.append(fut.result())

    # 保持 CHART_SPECS 中的原始顺序
    order_map = {spec[0]: i for i, spec in enumerate(CHART_SPECS)}
    results.sort(key=lambda r: order_map.get(r[0], 99))

    manifest = []
    for key, title, subtitle, anchor, required, wrapped, err in results:
        if err:
            if verbose:
                print(f"  [skip] {key}: {err}")
            manifest.append({
                "key": key, "title": title, "subtitle": subtitle,
                "anchor": anchor, "required": required,
                "svg": "", "ok": False, "err": err,
            })
            continue
        svg_doc = _extract_standalone_svg(wrapped, title, subtitle)
        # 去掉 XML 声明行（HTML 内嵌不需要），只留纯 <svg> 标签
        svg_only = re.sub(r'^<\?xml[^>]*\?>\s*', '', svg_doc).strip()
        if verbose:
            print(f"  [ok]   {key}: {len(svg_only)} bytes")
        manifest.append({
            "key": key, "title": title, "subtitle": subtitle,
            "anchor": anchor, "required": required,
            "svg": svg_only, "ok": True, "err": None,
        })
    return manifest


# ============================================================
# CLI 主流程（备用 · 落地 SVG 文件）
# ============================================================
def generate_charts(code: str, outdir: Path, only: set = None, report_path: Path = None):
    """为指定股票代码生成全部 / 指定图表到 outdir/，返回清单 dict"""
    outdir.mkdir(parents=True, exist_ok=True)

    # === 加载数据源 ===
    fundamental_text = read_file(FIN_DIR / f"{code}_fundamental.md")
    if not fundamental_text:
        print(f"[WARN] 未找到 FinancialData/{code}_fundamental.md，部分图表将无数据。")

    realtime_data = None
    realtime_path = FIN_DIR / f"{code}_realtime.json"
    if realtime_path.exists():
        try:
            realtime_data = json.loads(realtime_path.read_text(encoding='utf-8'))
        except Exception as e:
            print(f"[WARN] 读取 realtime JSON 失败: {e}")

    fundamental_json = None
    fundamental_json_path = FIN_DIR / f"{code}_fundamental.json"
    if fundamental_json_path.exists():
        try:
            fundamental_json = json.loads(fundamental_json_path.read_text(encoding='utf-8'))
        except Exception as e:
            print(f"[WARN] 读取 fundamental JSON 失败: {e}")

    peer_data = None
    peer_path = FIN_DIR / f"{code}_peers.json"
    if peer_path.exists():
        try:
            peer_data = json.loads(peer_path.read_text(encoding='utf-8'))
        except Exception as e:
            print(f"[WARN] 读取 peers JSON 失败: {e}")

    winrate_data = None
    winrate_path = FIN_DIR / f"{code}_winrate.json"
    if winrate_path.exists():
        try:
            winrate_data = json.loads(winrate_path.read_text(encoding='utf-8'))
        except Exception as e:
            print(f"[WARN] 读取 winrate JSON 失败: {e}")

    # === 逐图生成（并行，v7.1） ===
    # 9 张图的数据互相独立，用 ThreadPoolExecutor 并行；K 线 API 调用只在 kline 图任务内部发生一次。
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import time as _time
    _t_start = _time.time()

    # K 线数据：优先读缓存 FinancialData/{code}_kline.json（T-2 优化），miss 再调 API
    def _load_kline_records(need_kline: bool):
        if not need_kline:
            return []
        kline_cache = FIN_DIR / f"{code}_kline.json"
        if kline_cache.exists():
            try:
                data = json.loads(kline_cache.read_text(encoding='utf-8'))
                records = data.get("K线数据") if isinstance(data, dict) else data
                if records:
                    print(f"[cache] 复用 K 线缓存：{kline_cache.name}（{len(records)} 条）")
                    return records
            except Exception as e:
                print(f"[WARN] K 线缓存读取失败（{e}），回退到 API")
        return _fetch_kline_for_chart(code, 250)

    # 要生成的任务清单
    tasks = []
    for i, spec in enumerate(CHART_SPECS, 1):
        key = spec[0]
        if only is not None and key not in only:
            continue
        tasks.append((i, spec))

    # K 线记录只在需要时懒加载一次，避免 peer/winrate 之类不需要 K 线的任务也触发 API
    _need_kline = any(spec[0] == "kline" for _, spec in tasks)
    kline_records_cache = _load_kline_records(_need_kline)

    def _build_chart(i: int, spec):
        key, fname, title, subtitle, anchor, required = spec
        try:
            if key == "kline":
                if kline_records_cache:
                    wrapped = chart_kline(kline_records_cache, display_days=120)
                else:
                    return (i, key, fname, title, subtitle, anchor, required, '', "[!] K 线数据获取失败，跳过")
            elif key == "annual":
                wrapped = chart_annual_trend(fundamental_text)
            elif key == "gm":
                wrapped = chart_gross_margin(fundamental_text)
            elif key == "cashflow":
                wrapped = chart_cashflow(fundamental_text)
            elif key == "fcf":
                wrapped = chart_fcf(fundamental_text)
            elif key == "valuation":
                wrapped = chart_valuation_gauge(fundamental_text)
            elif key == "peer":
                if peer_data:
                    wrapped = chart_peer_comparison(fundamental_text, peer_data)
                else:
                    return (i, key, fname, title, subtitle, anchor, required, '', "[!] 未提供 peers.json，跳过")
            elif key == "winrate":
                if winrate_data:
                    wrapped = chart_winrate_dashboard(winrate_data)
                else:
                    return (i, key, fname, title, subtitle, anchor, required, '', "[!] 未提供 winrate.json，跳过")
            else:
                wrapped = ''
        except Exception as e:
            return (i, key, fname, title, subtitle, anchor, required, '', f"[ERROR] 生成失败: {e}")
        return (i, key, fname, title, subtitle, anchor, required, wrapped, None)

    # 并行执行（max_workers=9 对应最多 9 张图，I/O 轻量无需更多）
    total = len(CHART_SPECS)
    manifest_charts = []
    results = []
    with ThreadPoolExecutor(max_workers=min(9, max(1, len(tasks)))) as pool:
        futs = [pool.submit(_build_chart, i, spec) for i, spec in tasks]
        for fut in as_completed(futs):
            results.append(fut.result())

    # 按原索引排序后写文件（保证输出顺序稳定）
    results.sort(key=lambda r: r[0])
    for i, key, fname, title, subtitle, anchor, required, wrapped, skip_msg in results:
        tag = f"[{i}/{total}] {key:10s} → {fname}"
        if skip_msg:
            print(f"{tag}  {skip_msg}")
            continue

        svg_doc = _extract_standalone_svg(wrapped, title, subtitle)
        if not svg_doc:
            print(f"{tag}  [!] 无有效 SVG 输出，跳过写文件")
            continue

        fpath = outdir / fname
        fpath.write_text(svg_doc, encoding='utf-8')
        size_kb = fpath.stat().st_size / 1024
        print(f"{tag}  ✓ {size_kb:.1f} KB")

        # Markdown 引用路径（相对 OutputReport/）
        try:
            rel_to_report = fpath.relative_to(WORKSPACE / "OutputReport")
            md_path = str(rel_to_report).replace('\\', '/')
        except Exception:
            md_path = str(fpath).replace('\\', '/')

        manifest_charts.append({
            "key": key,
            "file": str(fpath.name),
            "path": str(fpath).replace('\\', '/'),
            "md_path": md_path,
            "title": title,
            "subtitle": subtitle,
            "anchor": anchor,
            "required": required,
            "size_kb": round(size_kb, 1),
            "md_snippet": f"![{title}]({md_path})",
        })

    _elapsed = _time.time() - _t_start
    print(f"\n[时间] 图表生成耗时 {_elapsed:.2f} 秒（并行 max_workers={min(9, max(1, len(tasks)))}）")

    # === 输出清单 JSON ===
    manifest = {
        "code": code,
        "outdir": str(outdir).replace('\\', '/'),
        "chart_count": len(manifest_charts),
        "charts": manifest_charts,
        "usage": (
            "在 Markdown 报告中，用每个 chart 的 md_snippet 字段直接内嵌图片；"
            "anchor 字段给出建议的章节锚点关键词（软约束，不做强制匹配）。"
        ),
    }
    manifest_path = outdir / "charts_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')

    print("")
    print(f"[OK] 共生成 {len(manifest_charts)} 张 SVG 图表")
    print(f"[OK] 清单已写入: {manifest_path}")
    print("")
    print("在 Markdown 报告中引用示例：")
    for ch in manifest_charts[:3]:
        print(f"  {ch['md_snippet']}")
    if len(manifest_charts) > 3:
        print(f"  ... 其余 {len(manifest_charts) - 3} 张见 charts_manifest.json")

    return manifest


def main():
    p = argparse.ArgumentParser(description="独立生成股票分析图表（SVG，调试/归档用；正式报告链路由 md2html_report.py 内存态调用）")
    p.add_argument("code", help="6 位股票代码，如 300308 / 600519")
    p.add_argument("--outdir", default=None,
                   help="输出目录，默认 OutputReport/charts/{code}/")
    p.add_argument("--only", default=None,
                   help="只生成指定图表，逗号分隔。可选: kline,annual,gm,cashflow,fcf,valuation,peer,winrate")
    p.add_argument("--report-path", default=None,
                   help="（可选）Markdown 报告路径，用于推导相对路径。未提供时默认假设报告位于 OutputReport/ 根下")
    args = p.parse_args()

    code = args.code.strip()
    if not re.fullmatch(r"\d{6}", code):
        print(f"[ERROR] 股票代码格式错误: {code}（应为 6 位数字）", file=sys.stderr)
        sys.exit(2)

    if args.outdir:
        outdir = Path(args.outdir)
    else:
        outdir = WORKSPACE / "OutputReport" / "charts" / code

    only = None
    if args.only:
        only = {x.strip() for x in args.only.split(",") if x.strip()}
        valid_keys = {s[0] for s in CHART_SPECS}
        invalid = only - valid_keys
        if invalid:
            print(f"[ERROR] --only 包含未知键: {invalid}；合法键: {sorted(valid_keys)}", file=sys.stderr)
            sys.exit(2)

    report_path = Path(args.report_path) if args.report_path else None
    generate_charts(code, outdir, only=only, report_path=report_path)


if __name__ == "__main__":
    main()
