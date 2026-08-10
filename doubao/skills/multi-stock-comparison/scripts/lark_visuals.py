#!/usr/bin/env python3
"""Build Lark HTML-block and whiteboard visuals for multi-stock comparison."""

import argparse
import html
import json
import math
import sys
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path


MAX_HTML_CHARS = 900000
GROUP_COLORS = [
    "#2563EB", "#D64A52", "#14936B", "#8B5CF6",
    "#D97706", "#0891B2", "#BE185D", "#4B5563",
]
PALETTES = {
    "cn": {"up": "#D64A52", "down": "#14936B"},
    "global": {"up": "#14936B", "down": "#D64A52"},
}


def emit(message):
    sys.stderr.write(f"{message}\n")


def load_object(path):
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("输入 JSON 顶层必须是对象")
    return value


def finite_number(value, label, *, positive=False, nonnegative=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} 必须是数值")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{label} 必须是有限数")
    if positive and number <= 0:
        raise ValueError(f"{label} 必须大于 0")
    if nonnegative and number < 0:
        raise ValueError(f"{label} 不得小于 0")
    return number


def iso_date(value, label):
    if not isinstance(value, str):
        raise ValueError(f"{label} 必须是 YYYY-MM-DD")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{label} 必须是 YYYY-MM-DD") from exc
    return value


def text_value(value, label, *, default="", max_length=120):
    if value is None:
        return default
    if not isinstance(value, str):
        raise ValueError(f"{label} 必须是字符串")
    value = value.strip()
    if len(value) > max_length:
        raise ValueError(f"{label} 最长 {max_length} 个字符")
    return value


def safe_script_json(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def write_output(path, content, input_path):
    output = Path(path).resolve()
    if output == Path(input_path).resolve():
        raise ValueError("输出路径不能覆盖输入文件")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    return output


def validate_kline(data):
    title = text_value(data.get("title"), "title", max_length=80)
    if not title:
        raise ValueError("title 不能为空")
    palette = data.get("palette", "cn")
    if palette not in PALETTES:
        raise ValueError("palette 必须是 cn 或 global")
    series = data.get("series")
    if not isinstance(series, list) or len(series) < 2:
        raise ValueError("series 至少需要 2 根 K 线")
    if len(series) > 1200:
        raise ValueError("series 最多支持 1200 根 K 线；请先按分析窗口截取")

    bars = []
    seen_dates = set()
    for index, raw in enumerate(series):
        if not isinstance(raw, dict):
            raise ValueError(f"series[{index}] 必须是对象")
        day = iso_date(raw.get("date"), f"series[{index}].date")
        if day in seen_dates:
            raise ValueError(f"series 存在重复日期: {day}")
        seen_dates.add(day)
        opening = finite_number(raw.get("open"), f"series[{index}].open", positive=True)
        high = finite_number(raw.get("high"), f"series[{index}].high", positive=True)
        low = finite_number(raw.get("low"), f"series[{index}].low", positive=True)
        close = finite_number(raw.get("close"), f"series[{index}].close", positive=True)
        if high < max(opening, close, low):
            raise ValueError(f"series[{index}].high 低于开盘/收盘/最低价")
        if low > min(opening, close, high):
            raise ValueError(f"series[{index}].low 高于开盘/收盘/最高价")
        bar = {"date": day, "open": opening, "high": high, "low": low, "close": close}
        if raw.get("volume") is not None:
            bar["volume"] = finite_number(
                raw.get("volume"), f"series[{index}].volume", nonnegative=True
            )
        bars.append(bar)
    if [item["date"] for item in bars] != sorted(item["date"] for item in bars):
        raise ValueError("series 必须按交易日严格升序")

    events = []
    raw_events = data.get("events", [])
    if not isinstance(raw_events, list) or len(raw_events) > 20:
        raise ValueError("events 必须是数组且最多 20 项")
    for index, raw in enumerate(raw_events):
        if not isinstance(raw, dict):
            raise ValueError(f"events[{index}] 必须是对象")
        event_day = iso_date(raw.get("date"), f"events[{index}].date")
        label = text_value(raw.get("label"), f"events[{index}].label", max_length=50)
        if not label:
            raise ValueError(f"events[{index}].label 不能为空")
        events.append({"date": event_day, "label": label})

    return {
        "title": title,
        "subtitle": text_value(data.get("subtitle"), "subtitle", max_length=120),
        "symbol": text_value(data.get("symbol"), "symbol", max_length=30),
        "market": text_value(data.get("market"), "market", max_length=30),
        "currency": text_value(data.get("currency"), "currency", default="", max_length=20),
        "adjustment": text_value(
            data.get("adjustment"), "adjustment", default="未注明复权口径", max_length=30
        ),
        "source_note": text_value(data.get("source_note"), "source_note", max_length=160),
        "palette": palette,
        "colors": PALETTES[palette],
        "series": bars,
        "events": events,
    }


KLINE_TEMPLATE = r'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="use-iframe" content="true">
  <meta name="html-box-height-mode" content="auto">
  <meta name="description" content="__DESCRIPTION__">
  <title>__TITLE__</title>
  <style>
    :root{color-scheme:light;--ink:#172033;--muted:#667085;--line:#E5EAF0;--soft:#F7F9FC;--blue:#2563EB}
    *{box-sizing:border-box}html,body{margin:0;padding:0;background:#fff;color:var(--ink);font-family:Inter,"Noto Sans SC","PingFang SC",Arial,sans-serif}
    .root{width:100%;max-width:100%;padding:18px}.card{border:1px solid var(--line);border-radius:18px;background:#fff;box-shadow:0 10px 28px rgba(23,32,51,.07);overflow:hidden}
    header{padding:20px 22px 14px;border-bottom:1px solid var(--line);background:linear-gradient(135deg,#fff 0%,#F6F9FF 100%)}
    .eyebrow{font-size:12px;letter-spacing:.08em;color:var(--blue);font-weight:700;text-transform:uppercase}.title-row{display:flex;justify-content:space-between;gap:16px;align-items:flex-end;margin-top:7px}
    h1{font-size:22px;line-height:1.25;margin:0}.subtitle{margin-top:6px;color:var(--muted);font-size:13px}.legend{display:flex;gap:12px;align-items:center;color:var(--muted);font-size:12px;white-space:nowrap}
    .dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:5px}.metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;padding:14px 18px 4px}
    .metric{background:var(--soft);border:1px solid #EEF1F5;border-radius:12px;padding:10px 12px}.metric span{display:block;color:var(--muted);font-size:11px}.metric b{display:block;font-size:16px;margin-top:3px;font-variant-numeric:tabular-nums}
    .chart-wrap{position:relative;padding:8px 12px 2px}.chart{display:block;width:100%;height:470px}.tooltip{position:absolute;display:none;pointer-events:none;z-index:3;min-width:168px;padding:9px 11px;border-radius:10px;background:rgba(20,28,45,.94);color:#fff;font-size:12px;line-height:1.55;box-shadow:0 8px 24px rgba(0,0,0,.18);font-variant-numeric:tabular-nums}
    footer{padding:6px 20px 16px;color:var(--muted);font-size:11px;line-height:1.5}.positive{color:#B4232C}.negative{color:#087A59}
    @media(max-width:620px){.root{padding:8px}.title-row{display:block}.legend{margin-top:10px}.metrics{grid-template-columns:repeat(2,1fr)}.chart{height:430px}}
  </style>
</head>
<body>
<main class="root"><section class="card" aria-label="交互式 K 线图">
  <header><div class="eyebrow" id="eyebrow"></div><div class="title-row"><div><h1 id="title"></h1><div class="subtitle" id="subtitle"></div></div><div class="legend"><span><i class="dot" id="up-dot"></i><span id="up-label"></span></span><span><i class="dot" id="down-dot"></i><span id="down-label"></span></span></div></div></header>
  <div class="metrics"><div class="metric"><span>最新收盘</span><b id="latest"></b></div><div class="metric"><span>区间涨跌</span><b id="return"></b></div><div class="metric"><span>区间最高</span><b id="high"></b></div><div class="metric"><span>区间最低</span><b id="low"></b></div></div>
  <div class="chart-wrap" id="wrap"><canvas class="chart" id="chart"></canvas><div class="tooltip" id="tooltip"></div></div>
  <footer id="note"></footer>
</section></main>
<script>
const MODEL=__MODEL__;
const bars=MODEL.series,eventsByDate=new Map();for(const e of MODEL.events){if(!eventsByDate.has(e.date))eventsByDate.set(e.date,[]);eventsByDate.get(e.date).push(e.label)}
const $=id=>document.getElementById(id),canvas=$("chart"),wrap=$("wrap"),tip=$("tooltip"),ctx=canvas.getContext("2d");let hover=-1;
const fmt=(v,d=2)=>Number(v).toLocaleString("zh-CN",{minimumFractionDigits:d,maximumFractionDigits:d});
const esc=s=>String(s).replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[m]));
const volumeFmt=v=>v==null?"—":v>=1e8?fmt(v/1e8,2)+" 亿":v>=1e4?fmt(v/1e4,1)+" 万":fmt(v,0);
const first=bars[0],last=bars[bars.length-1],periodReturn=(last.close/first.close-1)*100,periodHigh=Math.max(...bars.map(d=>d.high)),periodLow=Math.min(...bars.map(d=>d.low));
$("eyebrow").textContent=[MODEL.market,MODEL.symbol,MODEL.currency].filter(Boolean).join(" · ")||"PRICE ACTION";$("title").textContent=MODEL.title;$("subtitle").textContent=MODEL.subtitle||`${first.date} 至 ${last.date} · ${MODEL.adjustment}`;
$("latest").textContent=fmt(last.close);$("return").textContent=`${periodReturn>=0?"+":""}${fmt(periodReturn)}%`;$("return").className=periodReturn>=0?"positive":"negative";$("high").textContent=fmt(periodHigh);$("low").textContent=fmt(periodLow);
$("up-dot").style.background=MODEL.colors.up;$("down-dot").style.background=MODEL.colors.down;$("up-label").textContent=MODEL.palette==="cn"?"上涨":"Up";$("down-label").textContent=MODEL.palette==="cn"?"下跌":"Down";
$("note").textContent=[`口径：${MODEL.adjustment}`,MODEL.source_note,`共 ${bars.length} 个交易日；悬停查看 OHLC、成交量与事件`].filter(Boolean).join(" ｜ ");
function draw(){const box=canvas.getBoundingClientRect(),dpr=Math.max(1,window.devicePixelRatio||1),W=Math.max(320,box.width),H=box.height;canvas.width=Math.round(W*dpr);canvas.height=Math.round(H*dpr);ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,W,H);
  const L=18,R=76,T=24,PB=Math.round(H*.71),VT=Math.round(H*.79),B=30,PW=W-L-R,PH=PB-T,VH=H-VT-B,step=PW/bars.length,cw=Math.max(2,Math.min(12,step*.62));
  let pmin=Math.min(...bars.map(d=>d.low)),pmax=Math.max(...bars.map(d=>d.high));const pad=(pmax-pmin||pmax*.02)*.08;pmin-=pad;pmax+=pad;const vmax=Math.max(1,...bars.map(d=>d.volume||0));
  const x=i=>L+step*(i+.5),yp=v=>T+(pmax-v)/(pmax-pmin)*PH,yv=v=>VT+VH-(v/vmax)*VH;
  ctx.font='11px Inter,"Noto Sans SC",sans-serif';ctx.textAlign="left";ctx.textBaseline="middle";
  for(let i=0;i<=5;i++){const y=T+PH*i/5,v=pmax-(pmax-pmin)*i/5;ctx.strokeStyle="#E8ECF2";ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(L,y);ctx.lineTo(W-R,y);ctx.stroke();ctx.fillStyle="#667085";ctx.fillText(fmt(v),W-R+8,y)}
  const ticks=Math.min(6,bars.length);for(let i=0;i<ticks;i++){const idx=Math.round(i*(bars.length-1)/Math.max(1,ticks-1));ctx.fillStyle="#667085";ctx.textAlign=i===0?"left":i===ticks-1?"right":"center";ctx.fillText(bars[idx].date.slice(5),x(idx),H-12)}
  bars.forEach((d,i)=>{const color=d.close>=d.open?MODEL.colors.up:MODEL.colors.down,xx=x(i);ctx.strokeStyle=color;ctx.lineWidth=1.2;ctx.beginPath();ctx.moveTo(xx,yp(d.high));ctx.lineTo(xx,yp(d.low));ctx.stroke();const y1=yp(Math.max(d.open,d.close)),y2=yp(Math.min(d.open,d.close));ctx.fillStyle=color;ctx.fillRect(xx-cw/2,y1,cw,Math.max(1.5,y2-y1));if(d.volume!=null){ctx.globalAlpha=.34;ctx.fillRect(xx-cw/2,yv(d.volume),cw,VT+VH-yv(d.volume));ctx.globalAlpha=1}});
  for(const [day] of eventsByDate){const i=bars.findIndex(d=>d.date===day);if(i<0)continue;const xx=x(i);ctx.setLineDash([4,4]);ctx.strokeStyle="#7C3AED";ctx.beginPath();ctx.moveTo(xx,T);ctx.lineTo(xx,PB);ctx.stroke();ctx.setLineDash([]);ctx.fillStyle="#7C3AED";ctx.beginPath();ctx.moveTo(xx,T+2);ctx.lineTo(xx-5,T+11);ctx.lineTo(xx+5,T+11);ctx.closePath();ctx.fill()}
  if(hover>=0&&hover<bars.length){const d=bars[hover],xx=x(hover);ctx.setLineDash([3,3]);ctx.strokeStyle="#344054";ctx.beginPath();ctx.moveTo(xx,T);ctx.lineTo(xx,VT+VH);ctx.stroke();ctx.setLineDash([]);ctx.fillStyle="#344054";ctx.beginPath();ctx.arc(xx,yp(d.close),3.5,0,Math.PI*2);ctx.fill()}
}
function showAt(ev){const r=canvas.getBoundingClientRect(),L=18,R=76,PW=r.width-L-R,idx=Math.max(0,Math.min(bars.length-1,Math.floor((ev.clientX-r.left-L)/(PW/bars.length))));hover=idx;const d=bars[idx],events=eventsByDate.get(d.date)||[];tip.innerHTML=`<b>${d.date}</b><br>开 ${fmt(d.open)}　高 ${fmt(d.high)}<br>低 ${fmt(d.low)}　收 ${fmt(d.close)}<br>成交量 ${volumeFmt(d.volume)}${events.length?`<br><span style="color:#C4B5FD">事件：${events.map(esc).join("；")}</span>`:""}`;tip.style.display="block";const x=Math.min(r.width-184,Math.max(8,ev.clientX-r.left+12)),y=Math.max(8,ev.clientY-r.top-74);tip.style.left=x+"px";tip.style.top=y+"px";draw()}
canvas.addEventListener("pointermove",showAt);canvas.addEventListener("pointerleave",()=>{hover=-1;tip.style.display="none";draw()});if("ResizeObserver" in window)new ResizeObserver(draw).observe(canvas);else window.addEventListener("resize",draw);draw();
setTimeout(()=>{const m=window.magic;if(m&&typeof m.updateHeight==="function")m.updateHeight()},80);
</script>
</body></html>'''


def render_kline(data):
    model = validate_kline(data)
    description = (
        f"{model['title']} K 线图，期间 {model['series'][0]['date']} 至 "
        f"{model['series'][-1]['date']}，口径 {model['adjustment']}"
    )
    output = KLINE_TEMPLATE
    output = output.replace("__DESCRIPTION__", html.escape(description, quote=True))
    output = output.replace("__TITLE__", html.escape(model["title"]))
    output = output.replace("__MODEL__", safe_script_json(model))
    if len(output) > MAX_HTML_CHARS:
        raise ValueError(f"生成 HTML 超过 {MAX_HTML_CHARS} 字符限制")
    return output


def validate_timeseries(data):
    title = text_value(data.get("title"), "title", max_length=80)
    if not title:
        raise ValueError("title 不能为空")
    normalize = data.get("normalize_to_100", False)
    if not isinstance(normalize, bool):
        raise ValueError("normalize_to_100 必须是布尔值")
    raw_series = data.get("series")
    if not isinstance(raw_series, list) or not 1 <= len(raw_series) <= 8:
        raise ValueError("series 必须包含 1–8 个序列")
    common_dates = None
    series = []
    names = set()
    for series_index, raw in enumerate(raw_series):
        if not isinstance(raw, dict):
            raise ValueError(f"series[{series_index}] 必须是对象")
        name = text_value(raw.get("name"), f"series[{series_index}].name", max_length=24)
        if not name or name in names:
            raise ValueError(f"series[{series_index}].name 不能为空且不得重复")
        names.add(name)
        raw_values = raw.get("values")
        if not isinstance(raw_values, list) or not 2 <= len(raw_values) <= 600:
            raise ValueError(f"series[{series_index}].values 必须包含 2–600 项")
        dates, values = [], []
        for value_index, item in enumerate(raw_values):
            if not isinstance(item, dict):
                raise ValueError(f"series[{series_index}].values[{value_index}] 必须是对象")
            dates.append(
                iso_date(
                    item.get("date"),
                    f"series[{series_index}].values[{value_index}].date",
                )
            )
            values.append(
                finite_number(
                    item.get("value"),
                    f"series[{series_index}].values[{value_index}].value",
                )
            )
        if dates != sorted(dates) or len(set(dates)) != len(dates):
            raise ValueError(f"series[{series_index}].values 日期必须严格升序且不重复")
        if common_dates is None:
            common_dates = dates
        elif dates != common_dates:
            raise ValueError("全部序列必须使用相同日期；请先对齐共同交易日/期间")
        period_change = None if values[0] == 0 else (values[-1] / values[0] - 1) * 100
        if normalize:
            if values[0] == 0:
                raise ValueError(f"series[{series_index}] 首值为 0，无法归一化到 100")
            plotted = [value / values[0] * 100 for value in values]
        else:
            plotted = values
        series.append({
            "name": name,
            "color": GROUP_COLORS[series_index % len(GROUP_COLORS)],
            "values": plotted,
            "period_change_pct": period_change,
        })

    events = []
    raw_events = data.get("events", [])
    if not isinstance(raw_events, list) or len(raw_events) > 16:
        raise ValueError("events 必须是数组且最多 16 项")
    for index, raw in enumerate(raw_events):
        if not isinstance(raw, dict):
            raise ValueError(f"events[{index}] 必须是对象")
        event_day = iso_date(raw.get("date"), f"events[{index}].date")
        if event_day not in common_dates:
            raise ValueError(f"events[{index}].date 必须位于共同日期序列中")
        label = text_value(raw.get("label"), f"events[{index}].label", max_length=50)
        if not label:
            raise ValueError(f"events[{index}].label 不能为空")
        events.append({"date": event_day, "label": label})

    return {
        "title": title,
        "subtitle": text_value(data.get("subtitle"), "subtitle", max_length=120),
        "unit": "基期=100" if normalize else text_value(
            data.get("unit"), "unit", default="", max_length=20
        ),
        "normalize_to_100": normalize,
        "dates": common_dates,
        "series": series,
        "events": events,
        "source_note": text_value(data.get("source_note"), "source_note", max_length=180),
    }


TIMESERIES_TEMPLATE = r'''<!doctype html>
<html lang="zh-CN"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="use-iframe" content="true"><meta name="html-box-height-mode" content="auto">
<meta name="description" content="__DESCRIPTION__"><title>__TITLE__</title>
<style>
:root{--ink:#172033;--muted:#667085;--line:#E5EAF0;--soft:#F7F9FC}
*{box-sizing:border-box}html,body{margin:0;background:#fff;color:var(--ink);font-family:Inter,"Noto Sans SC","PingFang SC",Arial,sans-serif}
.root{width:100%;max-width:100%;padding:18px}.card{border:1px solid var(--line);border-radius:18px;overflow:hidden;box-shadow:0 10px 28px rgba(23,32,51,.07)}
header{padding:20px 22px 12px;background:linear-gradient(135deg,#fff,#F6F9FF);border-bottom:1px solid var(--line)}h1{margin:0;font-size:22px}.sub{margin-top:6px;color:var(--muted);font-size:13px}
.legend{display:flex;flex-wrap:wrap;gap:8px;padding:12px 18px 0}.chip{display:flex;align-items:center;gap:7px;background:var(--soft);border:1px solid #EEF1F5;border-radius:999px;padding:6px 9px;font-size:12px}.dot{width:8px;height:8px;border-radius:50%}.chg{font-variant-numeric:tabular-nums;color:var(--muted)}
.wrap{position:relative;padding:8px 12px 0}.chart{display:block;width:100%;height:430px}.tip{display:none;position:absolute;pointer-events:none;z-index:3;min-width:190px;padding:9px 11px;border-radius:10px;background:rgba(20,28,45,.94);color:#fff;font-size:12px;line-height:1.55;box-shadow:0 8px 24px rgba(0,0,0,.18)}
footer{padding:7px 20px 16px;color:var(--muted);font-size:11px}@media(max-width:620px){.root{padding:8px}.chart{height:390px}}
</style></head><body><main class="root"><section class="card" aria-label="交互式多序列趋势图">
<header><h1 id="title"></h1><div class="sub" id="subtitle"></div></header><div class="legend" id="legend"></div>
<div class="wrap"><canvas class="chart" id="chart"></canvas><div class="tip" id="tip"></div></div><footer id="note"></footer>
</section></main><script>
const M=__MODEL__,$=id=>document.getElementById(id),cv=$("chart"),ctx=cv.getContext("2d"),tip=$("tip");let hover=-1;
const fmt=v=>Number(v).toLocaleString("zh-CN",{maximumFractionDigits:2});const esc=s=>String(s).replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[m]));
$("title").textContent=M.title;$("subtitle").textContent=M.subtitle||`${M.dates[0]} 至 ${M.dates[M.dates.length-1]} · ${M.unit||"统一口径"}`;
$("legend").innerHTML=M.series.map(s=>`<span class="chip"><i class="dot" style="background:${s.color}"></i><b>${esc(s.name)}</b><span class="chg">${s.period_change_pct==null?"—":`${s.period_change_pct>=0?"+":""}${fmt(s.period_change_pct)}%`}</span></span>`).join("");
$("note").textContent=[M.normalize_to_100?"共同基期归一化为 100":"原始同口径数值",M.source_note,"悬停查看同日全部序列"].filter(Boolean).join(" ｜ ");
const events=new Map(M.events.map(e=>[e.date,e.label]));
function draw(){const r=cv.getBoundingClientRect(),dpr=Math.max(1,devicePixelRatio||1),W=Math.max(320,r.width),H=r.height;cv.width=Math.round(W*dpr);cv.height=Math.round(H*dpr);ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,W,H);
 const L=18,R=74,T=25,B=42,PW=W-L-R,PH=H-T-B,all=M.series.flatMap(s=>s.values);let lo=Math.min(...all),hi=Math.max(...all),pad=(hi-lo||Math.abs(hi)||1)*.08;lo-=pad;hi+=pad;const x=i=>L+PW*i/(M.dates.length-1),y=v=>T+(hi-v)/(hi-lo)*PH;
 ctx.font='11px Inter,"Noto Sans SC",sans-serif';ctx.textBaseline="middle";for(let i=0;i<=5;i++){const yy=T+PH*i/5,v=hi-(hi-lo)*i/5;ctx.strokeStyle="#E8ECF2";ctx.beginPath();ctx.moveTo(L,yy);ctx.lineTo(W-R,yy);ctx.stroke();ctx.fillStyle="#667085";ctx.textAlign="left";ctx.fillText(fmt(v),W-R+8,yy)}
 const ticks=Math.min(6,M.dates.length);for(let i=0;i<ticks;i++){const idx=Math.round(i*(M.dates.length-1)/Math.max(1,ticks-1));ctx.fillStyle="#667085";ctx.textAlign=i===0?"left":i===ticks-1?"right":"center";ctx.fillText(M.dates[idx].slice(5),x(idx),H-16)}
 for(const e of M.events){const idx=M.dates.indexOf(e.date),xx=x(idx);ctx.setLineDash([4,4]);ctx.strokeStyle="#98A2B3";ctx.beginPath();ctx.moveTo(xx,T);ctx.lineTo(xx,T+PH);ctx.stroke();ctx.setLineDash([])}
 for(const s of M.series){ctx.strokeStyle=s.color;ctx.lineWidth=2.2;ctx.beginPath();s.values.forEach((v,i)=>i?ctx.lineTo(x(i),y(v)):ctx.moveTo(x(i),y(v)));ctx.stroke();if(hover>=0){ctx.fillStyle=s.color;ctx.beginPath();ctx.arc(x(hover),y(s.values[hover]),3.5,0,Math.PI*2);ctx.fill()}}
 if(hover>=0){const xx=x(hover);ctx.setLineDash([3,3]);ctx.strokeStyle="#344054";ctx.beginPath();ctx.moveTo(xx,T);ctx.lineTo(xx,T+PH);ctx.stroke();ctx.setLineDash([])}
}
function show(ev){const r=cv.getBoundingClientRect(),L=18,R=74,idx=Math.max(0,Math.min(M.dates.length-1,Math.round((ev.clientX-r.left-L)/(r.width-L-R)*(M.dates.length-1))));hover=idx;const day=M.dates[idx],rows=M.series.map(s=>`<span style="color:${s.color}">●</span> ${esc(s.name)}：${fmt(s.values[idx])}`).join("<br>");tip.innerHTML=`<b>${day}</b>${events.has(day)?`<br><span style="color:#C4B5FD">${esc(events.get(day))}</span>`:""}<br>${rows}`;tip.style.display="block";tip.style.left=Math.min(r.width-205,Math.max(8,ev.clientX-r.left+12))+"px";tip.style.top=Math.max(8,ev.clientY-r.top-70)+"px";draw()}
cv.addEventListener("pointermove",show);cv.addEventListener("pointerleave",()=>{hover=-1;tip.style.display="none";draw()});if("ResizeObserver"in window)new ResizeObserver(draw).observe(cv);else addEventListener("resize",draw);draw();setTimeout(()=>{const m=window.magic;if(m&&typeof m.updateHeight==="function")m.updateHeight()},80);
</script></body></html>'''


def render_timeseries(data):
    model = validate_timeseries(data)
    description = (
        f"{model['title']} 多序列趋势图，期间 {model['dates'][0]} 至 {model['dates'][-1]}"
    )
    output = TIMESERIES_TEMPLATE
    output = output.replace("__DESCRIPTION__", html.escape(description, quote=True))
    output = output.replace("__TITLE__", html.escape(model["title"]))
    output = output.replace("__MODEL__", safe_script_json(model))
    if len(output) > MAX_HTML_CHARS:
        raise ValueError(f"生成 HTML 超过 {MAX_HTML_CHARS} 字符限制")
    return output


def validate_heatmap(data):
    title = text_value(data.get("title"), "title", max_length=80)
    if not title:
        raise ValueError("title 不能为空")
    raw_rows, raw_columns, raw_values = data.get("rows"), data.get("columns"), data.get("values")
    if not isinstance(raw_rows, list) or not 1 <= len(raw_rows) <= 20:
        raise ValueError("rows 必须包含 1–20 项")
    if not isinstance(raw_columns, list) or not 1 <= len(raw_columns) <= 12:
        raise ValueError("columns 必须包含 1–12 项")
    rows = [text_value(item, f"rows[{i}]", max_length=24) for i, item in enumerate(raw_rows)]
    columns = [
        text_value(item, f"columns[{i}]", max_length=24)
        for i, item in enumerate(raw_columns)
    ]
    if any(not item for item in rows + columns) or len(set(rows)) != len(rows) or len(set(columns)) != len(columns):
        raise ValueError("rows/columns 标签不能为空且不得重复")
    if not isinstance(raw_values, list) or len(raw_values) != len(rows):
        raise ValueError("values 行数必须等于 rows")
    values, finite_values = [], []
    for row_index, raw_row in enumerate(raw_values):
        if not isinstance(raw_row, list) or len(raw_row) != len(columns):
            raise ValueError(f"values[{row_index}] 列数必须等于 columns")
        row = []
        for column_index, value in enumerate(raw_row):
            if value is None:
                row.append(None)
            else:
                number = finite_number(value, f"values[{row_index}][{column_index}]")
                row.append(number)
                finite_values.append(number)
        values.append(row)
    if not finite_values:
        raise ValueError("values 至少需要一个非空数值")
    scale = data.get("scale", "sequential")
    if scale not in {"sequential", "diverging"}:
        raise ValueError("scale 必须是 sequential 或 diverging")
    center = finite_number(data.get("center", 0), "center")
    if scale == "diverging" and not min(finite_values) <= center <= max(finite_values):
        raise ValueError("diverging 色阶的 center 必须位于数值范围内")
    value_format = data.get("value_format", "number")
    if value_format not in {"number", "percent", "multiple"}:
        raise ValueError("value_format 必须是 number、percent 或 multiple")
    precision = data.get("precision", 1)
    if isinstance(precision, bool) or not isinstance(precision, int) or not 0 <= precision <= 4:
        raise ValueError("precision 必须是 0–4 的整数")
    return {
        "title": title,
        "subtitle": text_value(data.get("subtitle"), "subtitle", max_length=120),
        "rows": rows,
        "columns": columns,
        "values": values,
        "scale": scale,
        "center": center,
        "minimum": min(finite_values),
        "maximum": max(finite_values),
        "value_format": value_format,
        "precision": precision,
        "unit": text_value(data.get("unit"), "unit", max_length=20),
        "source_note": text_value(data.get("source_note"), "source_note", max_length=180),
    }


HEATMAP_TEMPLATE = r'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="use-iframe" content="true"><meta name="html-box-height-mode" content="auto"><meta name="description" content="__DESCRIPTION__"><title>__TITLE__</title>
<style>
:root{--ink:#172033;--muted:#667085;--line:#E5EAF0}*{box-sizing:border-box}html,body{margin:0;background:#fff;color:var(--ink);font-family:Inter,"Noto Sans SC","PingFang SC",Arial,sans-serif}.root{width:100%;max-width:100%;padding:18px}.card{border:1px solid var(--line);border-radius:18px;overflow:hidden;box-shadow:0 10px 28px rgba(23,32,51,.07)}header{padding:20px 22px 13px;background:linear-gradient(135deg,#fff,#F6F9FF);border-bottom:1px solid var(--line)}h1{font-size:22px;margin:0}.sub{font-size:13px;color:var(--muted);margin-top:6px}.table-wrap{overflow:auto;padding:14px 16px 8px}table{width:100%;border-collapse:separate;border-spacing:4px;min-width:520px}th{font-size:12px;color:#475467;font-weight:700;padding:7px 8px;text-align:center}th.row{text-align:left;white-space:nowrap;background:#F7F9FC;border-radius:8px}td{min-width:64px;padding:11px 8px;text-align:center;border-radius:8px;font-size:12px;font-weight:700;font-variant-numeric:tabular-nums;border:1px solid rgba(255,255,255,.5)}.legend{display:flex;align-items:center;gap:8px;padding:0 20px 7px;color:var(--muted);font-size:11px}.bar{width:150px;height:8px;border-radius:999px}footer{padding:5px 20px 16px;color:var(--muted);font-size:11px}@media(max-width:620px){.root{padding:8px}}
</style></head><body><main class="root"><section class="card" aria-label="矩阵热力图"><header><h1 id="title"></h1><div class="sub" id="subtitle"></div></header><div class="table-wrap" id="table"></div><div class="legend"><span id="low"></span><i class="bar" id="bar"></i><span id="high"></span></div><footer id="note"></footer></section></main>
<script>
const M=__MODEL__,$=id=>document.getElementById(id);$("title").textContent=M.title;$("subtitle").textContent=M.subtitle||`${M.rows.length} × ${M.columns.length} 矩阵 · ${M.unit||"统一口径"}`;
const fmt=v=>v==null?"—":Number(v).toLocaleString("zh-CN",{minimumFractionDigits:M.precision,maximumFractionDigits:M.precision})+(M.value_format==="percent"?"%":M.value_format==="multiple"?"x":"");const esc=s=>String(s).replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[m]));
const mix=(a,b,t)=>a.map((v,i)=>Math.round(v+(b[i]-v)*t)),rgb=a=>`rgb(${a.join(",")})`;
function color(v){if(v==null)return{bg:"#F2F4F7",fg:"#98A2B3"};if(M.scale==="sequential"){const d=M.maximum-M.minimum||1,t=(v-M.minimum)/d,bg=mix([239,246,255],[30,90,180],t);return{bg:rgb(bg),fg:t>.58?"#fff":"#172033"}}const span=Math.max(Math.abs(M.minimum-M.center),Math.abs(M.maximum-M.center),1e-9),t=Math.min(1,Math.abs(v-M.center)/span),bg=v<M.center?mix([255,255,255],[210,76,70],t):mix([255,255,255],[37,99,190],t);return{bg:rgb(bg),fg:t>.62?"#fff":"#172033"}}
let out="<table><thead><tr><th></th>"+M.columns.map(c=>`<th>${esc(c)}</th>`).join("")+"</tr></thead><tbody>";M.rows.forEach((r,i)=>{out+=`<tr><th class="row">${esc(r)}</th>`;M.values[i].forEach((v,j)=>{const c=color(v),label=`${r} / ${M.columns[j]}：${fmt(v)}`;out+=`<td style="background:${c.bg};color:${c.fg}" title="${esc(label)}" aria-label="${esc(label)}">${fmt(v)}</td>`});out+="</tr>"});out+="</tbody></table>";$("table").innerHTML=out;
$("low").textContent=fmt(M.minimum);$("high").textContent=fmt(M.maximum);$("bar").style.background=M.scale==="sequential"?"linear-gradient(90deg,#EFF6FF,#1E5AB4)":"linear-gradient(90deg,#D24C46,#FFFFFF,#2563BE)";$("note").textContent=[`配色：${M.scale==="sequential"?"顺序色阶":"以 "+fmt(M.center)+" 为中心的发散色阶"}`,M.source_note].filter(Boolean).join(" ｜ ");setTimeout(()=>{const m=window.magic;if(m&&typeof m.updateHeight==="function")m.updateHeight()},80);
</script></body></html>'''


def render_heatmap(data):
    model = validate_heatmap(data)
    output = HEATMAP_TEMPLATE
    output = output.replace(
        "__DESCRIPTION__",
        html.escape(f"{model['title']}，{len(model['rows'])} 行 {len(model['columns'])} 列热力图", quote=True),
    )
    output = output.replace("__TITLE__", html.escape(model["title"]))
    output = output.replace("__MODEL__", safe_script_json(model))
    if len(output) > MAX_HTML_CHARS:
        raise ValueError(f"生成 HTML 超过 {MAX_HTML_CHARS} 字符限制")
    return output


def validate_waterfall(data):
    title = text_value(data.get("title"), "title", max_length=80)
    if not title:
        raise ValueError("title 不能为空")
    start = finite_number(data.get("start"), "start")
    raw_changes = data.get("changes")
    if not isinstance(raw_changes, list) or not 1 <= len(raw_changes) <= 12:
        raise ValueError("changes 必须包含 1–12 项")
    changes = []
    labels = set()
    for index, raw in enumerate(raw_changes):
        if not isinstance(raw, dict):
            raise ValueError(f"changes[{index}] 必须是对象")
        label = text_value(raw.get("label"), f"changes[{index}].label", max_length=18)
        if not label or label in labels:
            raise ValueError(f"changes[{index}].label 不能为空且不得重复")
        labels.add(label)
        changes.append({
            "label": label,
            "value": finite_number(raw.get("value"), f"changes[{index}].value"),
        })
    precision = data.get("precision", 1)
    if isinstance(precision, bool) or not isinstance(precision, int) or not 0 <= precision <= 3:
        raise ValueError("precision 必须是 0–3 的整数")
    return {
        "title": title,
        "subtitle": text_value(data.get("subtitle"), "subtitle", max_length=120),
        "start_label": text_value(data.get("start_label"), "start_label", default="起点", max_length=18),
        "end_label": text_value(data.get("end_label"), "end_label", default="终点", max_length=18),
        "start": start,
        "changes": changes,
        "unit": text_value(data.get("unit"), "unit", max_length=20),
        "precision": precision,
        "source_note": text_value(data.get("source_note"), "source_note", max_length=180),
    }


def render_waterfall(data):
    model = validate_waterfall(data)
    cumulative = [model["start"]]
    for change in model["changes"]:
        cumulative.append(cumulative[-1] + change["value"])
    values = [0, model["start"], cumulative[-1], *cumulative]
    minimum, maximum = min(values), max(values)
    pad = (maximum - minimum or abs(maximum) or 1) * 0.12
    minimum -= pad
    maximum += pad
    left, top, width, height = 95, 150, 1010, 430
    bars = len(model["changes"]) + 2
    step = width / bars
    bar_width = min(92, step * 0.62)

    def sy(value):
        return top + (maximum - value) / (maximum - minimum) * height

    def fmt(value):
        return f"{value:,.{model['precision']}f}{model['unit']}"

    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="720" viewBox="0 0 1200 720" role="img" aria-labelledby="wf-title wf-desc">',
        f'<title id="wf-title">{xml_text(model["title"])}</title>',
        f'<desc id="wf-desc">{xml_text(model["subtitle"] or "财务与经营指标桥接瀑布图")}</desc>',
        '<rect x="0" y="0" width="1200" height="720" rx="28" fill="#FFFFFF"/>',
        f'<text x="72" y="82" font-family="Noto Sans SC, sans-serif" font-size="30" font-weight="700" fill="#172033">{xml_text(model["title"])}</text>',
        f'<text x="72" y="116" font-family="Noto Sans SC, sans-serif" font-size="15" fill="#667085">{xml_text(model["subtitle"])}</text>',
    ]
    for index in range(5):
        value = minimum + (maximum - minimum) * index / 4
        y = sy(value)
        parts.extend([
            f'<line x1="{left}" y1="{y:.1f}" x2="{left+width}" y2="{y:.1f}" stroke="#E8ECF2" stroke-width="1"/>',
            f'<text x="{left-12}" y="{y+4:.1f}" text-anchor="end" font-family="Noto Sans SC, sans-serif" font-size="12" fill="#667085">{xml_text(fmt(value))}</text>',
        ])
    zero_y = sy(0)
    parts.append(f'<line x1="{left}" y1="{zero_y:.1f}" x2="{left+width}" y2="{zero_y:.1f}" stroke="#98A2B3" stroke-width="1.5"/>')

    labels = [model["start_label"]] + [item["label"] for item in model["changes"]] + [model["end_label"]]
    bar_specs = [(0, model["start"], "#344054", model["start"])]
    for index, change in enumerate(model["changes"]):
        before, after = cumulative[index], cumulative[index + 1]
        bar_specs.append((min(before, after), max(before, after), "#2563EB" if change["value"] >= 0 else "#D97706", change["value"]))
    bar_specs.append((0, cumulative[-1], "#172033", cumulative[-1]))

    for index, (lower, upper, color, displayed) in enumerate(bar_specs):
        x = left + step * index + (step - bar_width) / 2
        y1, y2 = sy(upper), sy(lower)
        parts.extend([
            f'<rect x="{x:.1f}" y="{min(y1,y2):.1f}" width="{bar_width:.1f}" height="{max(2,abs(y2-y1)):.1f}" rx="7" fill="{color}" opacity="0.92"/>',
            f'<text x="{x+bar_width/2:.1f}" y="{min(y1,y2)-10:.1f}" text-anchor="middle" font-family="Noto Sans SC, sans-serif" font-size="13" font-weight="700" fill="#172033">{xml_text(("+" if 0 < index < bars-1 and displayed >= 0 else "") + fmt(displayed))}</text>',
            f'<text x="{x+bar_width/2:.1f}" y="{top+height+31}" text-anchor="middle" font-family="Noto Sans SC, sans-serif" font-size="13" fill="#475467">{xml_text(labels[index])}</text>',
        ])
        if 0 < index < bars - 1:
            connector_y = sy(cumulative[index])
            parts.append(
                f'<line x1="{x-step+bar_width:.1f}" y1="{connector_y:.1f}" x2="{x:.1f}" y2="{connector_y:.1f}" stroke="#98A2B3" stroke-width="1.5" stroke-dasharray="4 4"/>'
            )
    final_connector_y = sy(cumulative[-1])
    final_x = left + step * (bars - 1) + (step - bar_width) / 2
    parts.append(
        f'<line x1="{final_x-step+bar_width:.1f}" y1="{final_connector_y:.1f}" x2="{final_x:.1f}" y2="{final_connector_y:.1f}" stroke="#98A2B3" stroke-width="1.5" stroke-dasharray="4 4"/>'
    )
    parts.extend([
        '<rect x="74" y="646" width="12" height="12" rx="3" fill="#2563EB"/><text x="94" y="657" font-family="Noto Sans SC, sans-serif" font-size="12" fill="#667085">正向桥接项</text>',
        '<rect x="190" y="646" width="12" height="12" rx="3" fill="#D97706"/><text x="210" y="657" font-family="Noto Sans SC, sans-serif" font-size="12" fill="#667085">负向桥接项</text>',
        f'<text x="1120" y="657" text-anchor="end" font-family="Noto Sans SC, sans-serif" font-size="12" fill="#98A2B3">{xml_text(model["source_note"])}</text>',
        "</svg>",
    ])
    output = "\n".join(parts) + "\n"
    ET.fromstring(output)
    return output


def wrap_text(value, width=34, max_lines=2):
    value = value.strip()
    lines = [value[index:index + width] for index in range(0, len(value), width)]
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1][:-1] + "…"
    return lines or [""]


def validate_timeline(data):
    title = text_value(data.get("title"), "title", max_length=80)
    if not title:
        raise ValueError("title 不能为空")
    raw_events = data.get("events")
    if not isinstance(raw_events, list) or not 2 <= len(raw_events) <= 14:
        raise ValueError("events 必须包含 2–14 项")
    events, seen = [], set()
    for index, raw in enumerate(raw_events):
        if not isinstance(raw, dict):
            raise ValueError(f"events[{index}] 必须是对象")
        event_date = iso_date(raw.get("date"), f"events[{index}].date")
        label = text_value(raw.get("label"), f"events[{index}].label", max_length=26)
        category = text_value(raw.get("category"), f"events[{index}].category", default="事件", max_length=16)
        stage = text_value(raw.get("stage"), f"events[{index}].stage", max_length=16)
        effect = raw.get("effect", "neutral")
        if effect not in {"positive", "negative", "mixed", "neutral"}:
            raise ValueError(f"events[{index}].effect 必须是 positive、negative、mixed 或 neutral")
        if not label:
            raise ValueError(f"events[{index}].label 不能为空")
        signature = (event_date, label)
        if signature in seen:
            raise ValueError("events 的日期与标题组合不得重复")
        seen.add(signature)
        events.append({
            "date": event_date,
            "label": label,
            "category": category or "事件",
            "stage": stage,
            "effect": effect,
            "note": text_value(raw.get("note"), f"events[{index}].note", max_length=80),
        })
    if [event["date"] for event in events] != sorted(event["date"] for event in events):
        raise ValueError("events 必须按日期升序")
    return {
        "title": title,
        "subtitle": text_value(data.get("subtitle"), "subtitle", max_length=120),
        "events": events,
        "as_of": text_value(data.get("as_of"), "as_of", max_length=20),
        "source_note": text_value(data.get("source_note"), "source_note", max_length=180),
    }


def render_timeline(data):
    model = validate_timeline(data)
    height = 190 + len(model["events"]) * 112
    center = 600
    effect_label = {
        "positive": "偏正面", "negative": "偏负面", "mixed": "影响混合", "neutral": "中性/待验证"
    }
    effect_color = {
        "positive": "#2563EB", "negative": "#D97706", "mixed": "#7C3AED", "neutral": "#667085"
    }
    categories = []
    for event in model["events"]:
        if event["category"] not in categories:
            categories.append(event["category"])
    category_colors = {
        category: GROUP_COLORS[index % len(GROUP_COLORS)]
        for index, category in enumerate(categories)
    }
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="{height}" viewBox="0 0 1200 {height}" role="img" aria-labelledby="tl-title tl-desc">',
        f'<title id="tl-title">{xml_text(model["title"])}</title>',
        f'<desc id="tl-desc">{xml_text(model["subtitle"] or "公司、监管与供应链事件时间线")}</desc>',
        f'<rect x="0" y="0" width="1200" height="{height}" rx="28" fill="#FFFFFF"/>',
        f'<text x="72" y="78" font-family="Noto Sans SC, sans-serif" font-size="30" font-weight="700" fill="#172033">{xml_text(model["title"])}</text>',
        f'<text x="72" y="112" font-family="Noto Sans SC, sans-serif" font-size="15" fill="#667085">{xml_text(model["subtitle"])}</text>',
        f'<line x1="{center}" y1="150" x2="{center}" y2="{height-72}" stroke="#D8DEE8" stroke-width="4"/>',
    ]
    for index, event in enumerate(model["events"]):
        y = 175 + index * 112
        left_side = index % 2 == 0
        card_x = 90 if left_side else 650
        card_width = 460
        connector_end = card_x + card_width if left_side else card_x
        color = category_colors[event["category"]]
        effect = effect_color[event["effect"]]
        parts.extend([
            f'<line x1="{center}" y1="{y+35}" x2="{connector_end}" y2="{y+35}" stroke="#D8DEE8" stroke-width="2"/>',
            f'<circle cx="{center}" cy="{y+35}" r="11" fill="{color}" stroke="#FFFFFF" stroke-width="4"/>',
            f'<rect x="{card_x}" y="{y}" width="{card_width}" height="82" rx="16" fill="#F8FAFC" stroke="#E5EAF0" stroke-width="1.5"/>',
            f'<rect x="{card_x}" y="{y}" width="7" height="82" rx="3.5" fill="{color}"/>',
            f'<text x="{card_x+20}" y="{y+24}" font-family="Noto Sans SC, sans-serif" font-size="13" font-weight="700" fill="{color}">{xml_text(event["date"])} · {xml_text(event["category"])}</text>',
            f'<text x="{card_x+card_width-18}" y="{y+24}" text-anchor="end" font-family="Noto Sans SC, sans-serif" font-size="12" font-weight="700" fill="{effect}">{xml_text(effect_label[event["effect"]])}</text>',
            f'<text x="{card_x+20}" y="{y+49}" font-family="Noto Sans SC, sans-serif" font-size="16" font-weight="700" fill="#172033">{xml_text(event["label"])}</text>',
        ])
        note = " · ".join(filter(None, [event["stage"], event["note"]]))
        for line_index, line in enumerate(wrap_text(note, width=34, max_lines=1)):
            parts.append(
                f'<text x="{card_x+20}" y="{y+69+line_index*16}" font-family="Noto Sans SC, sans-serif" font-size="12" fill="#667085">{xml_text(line)}</text>'
            )
    note = " ｜ ".join(filter(None, [model["as_of"] and f"截至 {model['as_of']}", model["source_note"]]))
    parts.extend([
        f'<text x="1120" y="{height-28}" text-anchor="end" font-family="Noto Sans SC, sans-serif" font-size="12" fill="#98A2B3">{xml_text(note)}</text>',
        "</svg>",
    ])
    output = "\n".join(parts) + "\n"
    ET.fromstring(output)
    return output


def validate_axis(raw, label, values):
    if not isinstance(raw, dict):
        raise ValueError(f"{label} 必须是对象")
    minimum = finite_number(raw.get("min", min(values)), f"{label}.min")
    maximum = finite_number(raw.get("max", max(values)), f"{label}.max")
    if maximum <= minimum:
        raise ValueError(f"{label}.max 必须大于 min")
    split = finite_number(raw.get("split", (minimum + maximum) / 2), f"{label}.split")
    if not minimum < split < maximum:
        raise ValueError(f"{label}.split 必须位于 min 与 max 之间")
    axis_label = text_value(raw.get("label"), f"{label}.label", max_length=40)
    if not axis_label:
        raise ValueError(f"{label}.label 不能为空")
    return {
        "label": axis_label,
        "low": text_value(raw.get("low"), f"{label}.low", default="低", max_length=20),
        "high": text_value(raw.get("high"), f"{label}.high", default="高", max_length=20),
        "min": minimum,
        "max": maximum,
        "split": split,
    }


def validate_quadrant(data):
    title = text_value(data.get("title"), "title", max_length=80)
    if not title:
        raise ValueError("title 不能为空")
    raw_points = data.get("points")
    if not isinstance(raw_points, list) or not 1 <= len(raw_points) <= 30:
        raise ValueError("points 必须包含 1–30 项")
    points = []
    labels = set()
    for index, raw in enumerate(raw_points):
        if not isinstance(raw, dict):
            raise ValueError(f"points[{index}] 必须是对象")
        label = text_value(raw.get("label"), f"points[{index}].label", max_length=24)
        if not label or label in labels:
            raise ValueError(f"points[{index}].label 不能为空且不得重复")
        labels.add(label)
        points.append({
            "label": label,
            "x": finite_number(raw.get("x"), f"points[{index}].x"),
            "y": finite_number(raw.get("y"), f"points[{index}].y"),
            "size": finite_number(raw.get("size", 1), f"points[{index}].size", positive=True),
            "group": text_value(raw.get("group"), f"points[{index}].group", default="其他", max_length=20) or "其他",
        })
    x_axis = validate_axis(data.get("x_axis"), "x_axis", [p["x"] for p in points])
    y_axis = validate_axis(data.get("y_axis"), "y_axis", [p["y"] for p in points])
    for point in points:
        if not x_axis["min"] <= point["x"] <= x_axis["max"]:
            raise ValueError(f"{point['label']} 的 x 超出 x_axis 范围")
        if not y_axis["min"] <= point["y"] <= y_axis["max"]:
            raise ValueError(f"{point['label']} 的 y 超出 y_axis 范围")
    raw_labels = data.get("quadrants", {})
    if not isinstance(raw_labels, dict):
        raise ValueError("quadrants 必须是对象")
    quadrants = {
        key: text_value(raw_labels.get(key), f"quadrants.{key}", default=default, max_length=24)
        for key, default in {
            "top_left": "重点观察", "top_right": "优先研究",
            "bottom_left": "低优先级", "bottom_right": "估值/执行权衡",
        }.items()
    }
    return {
        "title": title,
        "subtitle": text_value(data.get("subtitle"), "subtitle", max_length=120),
        "as_of": text_value(data.get("as_of"), "as_of", max_length=20),
        "source_note": text_value(data.get("source_note"), "source_note", max_length=180),
        "x_axis": x_axis,
        "y_axis": y_axis,
        "quadrants": quadrants,
        "points": points,
    }


def xml_text(value):
    return html.escape(str(value), quote=True)


def render_quadrant(data):
    model = validate_quadrant(data)
    x_axis, y_axis = model["x_axis"], model["y_axis"]
    left, top, width, height = 130, 155, 930, 525

    def sx(value):
        return left + (value - x_axis["min"]) / (x_axis["max"] - x_axis["min"]) * width

    def sy(value):
        return top + height - (value - y_axis["min"]) / (y_axis["max"] - y_axis["min"]) * height

    split_x, split_y = sx(x_axis["split"]), sy(y_axis["split"])
    groups = []
    for point in model["points"]:
        if point["group"] not in groups:
            groups.append(point["group"])
    group_color = {group: GROUP_COLORS[i % len(GROUP_COLORS)] for i, group in enumerate(groups)}
    sizes = [p["size"] for p in model["points"]]
    size_min, size_max = min(sizes), max(sizes)

    def radius(value):
        if size_max == size_min:
            return 16
        return 11 + (value - size_min) / (size_max - size_min) * 13

    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="820" viewBox="0 0 1200 820" role="img" aria-labelledby="chart-title chart-desc">',
        f'<title id="chart-title">{xml_text(model["title"])}</title>',
        f'<desc id="chart-desc">{xml_text(model["subtitle"] or "多股票比较象限分析")}</desc>',
        '<rect x="0" y="0" width="1200" height="820" rx="28" fill="#FFFFFF"/>',
        '<path d="M56 48 H1144" stroke="#E8ECF2" stroke-width="2"/>',
        f'<text x="72" y="90" font-family="Noto Sans SC, sans-serif" font-size="30" font-weight="700" fill="#172033">{xml_text(model["title"])}</text>',
        f'<text x="72" y="121" font-family="Noto Sans SC, sans-serif" font-size="15" fill="#667085">{xml_text(model["subtitle"])}</text>',
        f'<rect x="{left}" y="{top}" width="{split_x-left:.1f}" height="{split_y-top:.1f}" fill="#F2F7FF"/>',
        f'<rect x="{split_x:.1f}" y="{top}" width="{left+width-split_x:.1f}" height="{split_y-top:.1f}" fill="#EEFAF4"/>',
        f'<rect x="{left}" y="{split_y:.1f}" width="{split_x-left:.1f}" height="{top+height-split_y:.1f}" fill="#F7F8FA"/>',
        f'<rect x="{split_x:.1f}" y="{split_y:.1f}" width="{left+width-split_x:.1f}" height="{top+height-split_y:.1f}" fill="#FFF5F0"/>',
        f'<rect x="{left}" y="{top}" width="{width}" height="{height}" fill="none" stroke="#D8DEE8" stroke-width="2"/>',
        f'<line x1="{split_x:.1f}" y1="{top}" x2="{split_x:.1f}" y2="{top+height}" stroke="#98A2B3" stroke-width="2" stroke-dasharray="7 7"/>',
        f'<line x1="{left}" y1="{split_y:.1f}" x2="{left+width}" y2="{split_y:.1f}" stroke="#98A2B3" stroke-width="2" stroke-dasharray="7 7"/>',
        f'<text x="{left+18}" y="{top+30}" font-family="Noto Sans SC, sans-serif" font-size="18" font-weight="700" fill="#3B5B8A">{xml_text(model["quadrants"]["top_left"])}</text>',
        f'<text x="{left+width-18}" y="{top+30}" text-anchor="end" font-family="Noto Sans SC, sans-serif" font-size="18" font-weight="700" fill="#147A55">{xml_text(model["quadrants"]["top_right"])}</text>',
        f'<text x="{left+18}" y="{top+height-18}" font-family="Noto Sans SC, sans-serif" font-size="18" font-weight="700" fill="#667085">{xml_text(model["quadrants"]["bottom_left"])}</text>',
        f'<text x="{left+width-18}" y="{top+height-18}" text-anchor="end" font-family="Noto Sans SC, sans-serif" font-size="18" font-weight="700" fill="#A04426">{xml_text(model["quadrants"]["bottom_right"])}</text>',
        f'<line x1="{left}" y1="{top+height+24}" x2="{left+width}" y2="{top+height+24}" stroke="#344054" stroke-width="2"/>',
        f'<polygon points="{left+width},{top+height+24} {left+width-12},{top+height+17} {left+width-12},{top+height+31}" fill="#344054"/>',
        f'<text x="{left}" y="{top+height+51}" font-family="Noto Sans SC, sans-serif" font-size="13" fill="#667085">{xml_text(x_axis["low"])}</text>',
        f'<text x="{left+width}" y="{top+height+51}" text-anchor="end" font-family="Noto Sans SC, sans-serif" font-size="13" fill="#667085">{xml_text(x_axis["high"])}</text>',
        f'<text x="{left+width/2}" y="{top+height+53}" text-anchor="middle" font-family="Noto Sans SC, sans-serif" font-size="16" font-weight="700" fill="#344054">{xml_text(x_axis["label"])}</text>',
        f'<line x1="{left-24}" y1="{top+height}" x2="{left-24}" y2="{top}" stroke="#344054" stroke-width="2"/>',
        f'<polygon points="{left-24},{top} {left-31},{top+12} {left-17},{top+12}" fill="#344054"/>',
        f'<text x="{left-52}" y="{top+height}" text-anchor="middle" font-family="Noto Sans SC, sans-serif" font-size="13" fill="#667085">{xml_text(y_axis["low"])}</text>',
        f'<text x="{left-52}" y="{top+7}" text-anchor="middle" font-family="Noto Sans SC, sans-serif" font-size="13" fill="#667085">{xml_text(y_axis["high"])}</text>',
        f'<text x="42" y="{top+height/2}" text-anchor="middle" transform="rotate(-90 42 {top+height/2})" font-family="Noto Sans SC, sans-serif" font-size="16" font-weight="700" fill="#344054">{xml_text(y_axis["label"])}</text>',
    ]

    for index, point in enumerate(model["points"]):
        x, y, r = sx(point["x"]), sy(point["y"]), radius(point["size"])
        color = group_color[point["group"]]
        anchor = "end" if x > split_x else "start"
        label_x = x - r - 7 if anchor == "end" else x + r + 7
        label_y = y + (-7 if index % 2 else 6)
        parts.extend([
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r+5:.1f}" fill="{color}" opacity="0.10"/>',
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{color}" opacity="0.88" stroke="#FFFFFF" stroke-width="3"/>',
            f'<text x="{label_x:.1f}" y="{label_y:.1f}" text-anchor="{anchor}" font-family="Noto Sans SC, sans-serif" font-size="14" font-weight="700" fill="#172033">{xml_text(point["label"])}</text>',
        ])

    legend_x, legend_y = 150, 748
    for index, group in enumerate(groups):
        x = legend_x + (index % 5) * 175
        y = legend_y + (index // 5) * 28
        parts.extend([
            f'<circle cx="{x}" cy="{y}" r="6" fill="{group_color[group]}"/>',
            f'<text x="{x+12}" y="{y+5}" font-family="Noto Sans SC, sans-serif" font-size="13" fill="#475467">{xml_text(group)}</text>',
        ])
    note = " ｜ ".join(filter(None, [model["as_of"] and f"截至 {model['as_of']}", model["source_note"]]))
    parts.append(f'<text x="1140" y="808" text-anchor="end" font-family="Noto Sans SC, sans-serif" font-size="12" fill="#98A2B3">{xml_text(note)}</text>')
    parts.append("</svg>")
    output = "\n".join(parts) + "\n"
    ET.fromstring(output)
    return output


def self_test():
    kline = {
        "title": "示例公司股价路径", "symbol": "TEST", "market": "A股",
        "currency": "CNY", "adjustment": "前复权", "palette": "cn",
        "series": [
            {"date": "2026-07-01", "open": 10, "high": 11, "low": 9.8, "close": 10.7, "volume": 1000},
            {"date": "2026-07-02", "open": 10.7, "high": 11.2, "low": 10.2, "close": 10.4, "volume": 1200},
            {"date": "2026-07-03", "open": 10.4, "high": 11.5, "low": 10.3, "close": 11.3, "volume": 1800},
        ],
        "events": [{"date": "2026-07-03", "label": "业绩预告 </script>"}],
    }
    html_output = render_kline(kline)
    if ("<canvas" not in html_output or "html-box-height-mode" not in html_output
            or "业绩预告" not in html_output or "<\\/script>" not in html_output
            or html_output.count("</script>") != 1 or "https://" in html_output):
        raise AssertionError("K 线 HTML 自测失败")
    invalid_kline = json.loads(json.dumps(kline))
    del invalid_kline["series"][0]["open"]
    try:
        render_kline(invalid_kline)
    except ValueError:
        pass
    else:
        raise AssertionError("缺少 OHLC 时应拒绝生成 K 线")

    timeseries = {
        "title": "公司与板块相对表现",
        "normalize_to_100": True,
        "series": [
            {
                "name": "公司 A",
                "values": [
                    {"date": "2026-07-01", "value": 10},
                    {"date": "2026-07-02", "value": 10.8},
                    {"date": "2026-07-03", "value": 11.2},
                ],
            },
            {
                "name": "行业指数",
                "values": [
                    {"date": "2026-07-01", "value": 200},
                    {"date": "2026-07-02", "value": 202},
                    {"date": "2026-07-03", "value": 203},
                ],
            },
        ],
        "events": [{"date": "2026-07-02", "label": "公司公告 </script>"}],
        "source_note": "共同交易日示例",
    }
    timeseries_output = render_timeseries(timeseries)
    if (
        "交互式多序列趋势图" not in timeseries_output
        or "基期=100" not in timeseries_output
        or "<\\/script>" not in timeseries_output
        or timeseries_output.count("</script>") != 1
        or "https://" in timeseries_output
    ):
        raise AssertionError("多序列趋势 HTML 自测失败")
    invalid_timeseries = json.loads(json.dumps(timeseries))
    invalid_timeseries["series"][1]["values"][1]["date"] = "2026-07-04"
    try:
        render_timeseries(invalid_timeseries)
    except ValueError:
        pass
    else:
        raise AssertionError("日期未对齐时应拒绝生成多序列趋势图")

    heatmap = {
        "title": "估值敏感性",
        "rows": ["WACC 8%", "WACC 9%"],
        "columns": ["g 2%", "g 3%", "g 4%"],
        "values": [[12.1, 13.4, 14.9], [10.8, 11.9, None]],
        "scale": "sequential",
        "value_format": "multiple",
        "precision": 1,
        "source_note": "示例模型",
    }
    heatmap_output = render_heatmap(heatmap)
    if (
        "矩阵热力图" not in heatmap_output
        or "WACC 8%" not in heatmap_output
        or "https://" in heatmap_output
    ):
        raise AssertionError("热力图 HTML 自测失败")

    quadrant = {
        "title": "同业增长质量象限", "subtitle": "横轴为估值吸引力，纵轴为盈利确定性",
        "x_axis": {"label": "估值吸引力", "low": "低", "high": "高", "min": 0, "max": 10, "split": 5},
        "y_axis": {"label": "盈利确定性", "low": "低", "high": "高", "min": 0, "max": 10, "split": 5},
        "points": [
            {"label": "公司 A", "x": 7.5, "y": 8, "size": 4, "group": "平台"},
            {"label": "公司 B", "x": 3.5, "y": 6, "size": 2, "group": "制造"},
            {"label": "公司 C", "x": 6, "y": 3, "size": 1, "group": "制造"},
        ],
        "as_of": "2026-07-20", "source_note": "示例数据",
    }
    svg_output = render_quadrant(quadrant)
    root = ET.fromstring(svg_output)
    if not root.tag.endswith("svg") or "公司 A" not in svg_output or "clipPath" in svg_output:
        raise AssertionError("象限 SVG 自测失败")
    invalid_quadrant = json.loads(json.dumps(quadrant))
    invalid_quadrant["x_axis"]["label"] = ""
    try:
        render_quadrant(invalid_quadrant)
    except ValueError:
        pass
    else:
        raise AssertionError("象限轴缺少定义时应拒绝生成")

    waterfall = {
        "title": "利润率变化桥",
        "start_label": "上期",
        "start": 20,
        "changes": [
            {"label": "售价", "value": 2.5},
            {"label": "原材料", "value": -1.2},
            {"label": "利用率", "value": 0.8},
        ],
        "end_label": "本期",
        "unit": "ppt",
        "source_note": "示例拆分",
    }
    waterfall_output = render_waterfall(waterfall)
    waterfall_root = ET.fromstring(waterfall_output)
    if (
        not waterfall_root.tag.endswith("svg")
        or "原材料" not in waterfall_output
        or "clipPath" in waterfall_output
    ):
        raise AssertionError("瀑布图 SVG 自测失败")

    timeline = {
        "title": "监管与公司事件",
        "events": [
            {
                "date": "2026-07-01", "label": "征求意见稿发布",
                "category": "监管", "stage": "提案", "effect": "mixed",
                "note": "适用范围仍待确认",
            },
            {
                "date": "2026-07-15", "label": "公司更新指引",
                "category": "公司", "stage": "已公告", "effect": "positive",
                "note": "上调收入区间",
            },
        ],
        "as_of": "2026-07-20",
        "source_note": "示例事件",
    }
    timeline_output = render_timeline(timeline)
    timeline_root = ET.fromstring(timeline_output)
    if (
        not timeline_root.tag.endswith("svg")
        or "征求意见稿发布" not in timeline_output
        or "clipPath" in timeline_output
    ):
        raise AssertionError("时间线 SVG 自测失败")
    emit("SELF_TEST_PASS")


def build_parser():
    parser = argparse.ArgumentParser(description="生成飞书多股票比较高级可视化。")
    parser.add_argument("--self-test", action="store_true")
    subparsers = parser.add_subparsers(dest="command")
    for name, help_text in (
        ("kline", "生成自包含的交互式 K 线 HTML block"),
        ("timeseries", "生成自包含的交互式多序列趋势 HTML block"),
        ("heatmap", "生成自包含的矩阵热力图 HTML block"),
        ("quadrant", "生成可导入 whiteboard 的多象限 SVG"),
        ("waterfall", "生成可导入 whiteboard 的桥接瀑布图 SVG"),
        ("timeline", "生成可导入 whiteboard 的事件时间线 SVG"),
    ):
        sub = subparsers.add_parser(name, help=help_text)
        sub.add_argument("input_json")
        sub.add_argument("--output", required=True)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.self_test:
        self_test()
        return 0
    if args.command is None:
        parser.error(
            "请选择 kline、timeseries、heatmap、quadrant、waterfall 或 timeline，"
            "或使用 --self-test"
        )
    try:
        data = load_object(args.input_json)
        renderers = {
            "kline": render_kline,
            "timeseries": render_timeseries,
            "heatmap": render_heatmap,
            "quadrant": render_quadrant,
            "waterfall": render_waterfall,
            "timeline": render_timeline,
        }
        content = renderers[args.command](data)
        output = write_output(args.output, content, args.input_json)
    except Exception as exc:
        emit(f"[错误] {exc}")
        return 1
    emit(f"已生成: {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
