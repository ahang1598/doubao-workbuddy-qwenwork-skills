#!/usr/bin/env python3
"""Build self-contained Lark HTML-block visuals for equity research."""

import argparse
import html
import json
import math
import sys
from datetime import date, datetime
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
THEMES = {"terminal-light", "terminal-dark"}


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


def iso_timestamp(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} 必须是 ISO 日期或时间")
    normalized = value.strip()
    candidate = normalized.replace("Z", "+00:00")
    if " " in candidate and "T" not in candidate:
        candidate = candidate.replace(" ", "T", 1)
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise ValueError(
            f"{label} 必须是 YYYY-MM-DD 或 YYYY-MM-DD HH:MM[:SS]"
        ) from exc
    return normalized, parsed.isoformat()


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
    theme = data.get("theme", "terminal-light")
    if theme not in THEMES:
        raise ValueError("theme 必须是 terminal-light 或 terminal-dark")
    raw_ma_windows = data.get("ma_windows", [5, 10, 20])
    if not isinstance(raw_ma_windows, list) or len(raw_ma_windows) > 5:
        raise ValueError("ma_windows 必须是最多 5 项的数组")
    ma_windows = []
    for index, window in enumerate(raw_ma_windows):
        if isinstance(window, bool) or not isinstance(window, int) or not 2 <= window <= 250:
            raise ValueError(f"ma_windows[{index}] 必须是 2–250 的整数")
        if window in ma_windows:
            raise ValueError("ma_windows 不得重复")
        ma_windows.append(window)
    show_volume = data.get("show_volume", True)
    if not isinstance(show_volume, bool):
        raise ValueError("show_volume 必须是布尔值")
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
        "theme": theme,
        "timeframe": text_value(
            data.get("timeframe"), "timeframe", default="日 K", max_length=20
        ),
        "ma_windows": ma_windows,
        "show_volume": show_volume,
        "series": bars,
        "events": events,
    }


def validate_price_chart(data):
    title = text_value(data.get("title"), "title", max_length=80)
    if not title:
        raise ValueError("title 不能为空")
    palette = data.get("palette", "cn")
    if palette not in PALETTES:
        raise ValueError("palette 必须是 cn 或 global")
    theme = data.get("theme", "terminal-light")
    if theme not in THEMES:
        raise ValueError("theme 必须是 terminal-light 或 terminal-dark")
    series = data.get("series")
    if not isinstance(series, list) or len(series) < 2:
        raise ValueError("series 至少需要 2 个价格点")
    if len(series) > 5000:
        raise ValueError("series 最多支持 5000 个价格点；请先截取分析窗口")

    points = []
    seen_times = set()
    ordering = []
    for index, raw in enumerate(series):
        if not isinstance(raw, dict):
            raise ValueError(f"series[{index}] 必须是对象")
        raw_time = raw.get("time", raw.get("date"))
        label_time, sort_time = iso_timestamp(raw_time, f"series[{index}].time")
        if sort_time in seen_times:
            raise ValueError(f"series 存在重复时间: {label_time}")
        seen_times.add(sort_time)
        ordering.append(sort_time)
        point = {
            "time": label_time,
            "close": finite_number(raw.get("close"), f"series[{index}].close", positive=True),
        }
        if raw.get("average") is not None:
            point["average"] = finite_number(
                raw.get("average"), f"series[{index}].average", positive=True
            )
        if raw.get("volume") is not None:
            point["volume"] = finite_number(
                raw.get("volume"), f"series[{index}].volume", nonnegative=True
            )
        points.append(point)
    if ordering != sorted(ordering):
        raise ValueError("series 必须按时间严格升序")

    previous_close = finite_number(
        data.get("previous_close", points[0]["close"]),
        "previous_close",
        positive=True,
    )
    raw_decimals = data.get("price_decimals", 2)
    if (
        isinstance(raw_decimals, bool)
        or not isinstance(raw_decimals, int)
        or not 0 <= raw_decimals <= 6
    ):
        raise ValueError("price_decimals 必须是 0–6 的整数")

    events = []
    raw_events = data.get("events", [])
    if not isinstance(raw_events, list) or len(raw_events) > 20:
        raise ValueError("events 必须是数组且最多 20 项")
    for index, raw in enumerate(raw_events):
        if not isinstance(raw, dict):
            raise ValueError(f"events[{index}] 必须是对象")
        event_time, _ = iso_timestamp(
            raw.get("time", raw.get("date")), f"events[{index}].time"
        )
        label = text_value(raw.get("label"), f"events[{index}].label", max_length=50)
        if not label:
            raise ValueError(f"events[{index}].label 不能为空")
        events.append({"time": event_time, "label": label})

    return {
        "title": title,
        "subtitle": text_value(data.get("subtitle"), "subtitle", max_length=120),
        "symbol": text_value(data.get("symbol"), "symbol", max_length=30),
        "market": text_value(data.get("market"), "market", max_length=30),
        "currency": text_value(data.get("currency"), "currency", default="", max_length=20),
        "adjustment": text_value(
            data.get("adjustment"), "adjustment", default="未注明复权口径", max_length=30
        ),
        "timeframe": text_value(
            data.get("timeframe"), "timeframe", default="价格走势", max_length=20
        ),
        "source_note": text_value(data.get("source_note"), "source_note", max_length=160),
        "palette": palette,
        "colors": PALETTES[palette],
        "theme": theme,
        "previous_close": previous_close,
        "price_decimals": raw_decimals,
        "series": points,
        "events": events,
    }


PRICE_TEMPLATE = r'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="use-iframe" content="true">
  <meta name="html-box-height-mode" content="auto">
  <meta name="description" content="__DESCRIPTION__">
  <title>__TITLE__</title>
  <style>
    :root{color-scheme:light;--bg:#fff;--panel:#fff;--ink:#172033;--muted:#667085;--line:#E5EAF0;--soft:#F7F9FC;--blue:#2F6BFF;--grid:#E8ECF2;--tip:rgba(20,28,45,.95)}
    body[data-theme="terminal-dark"]{color-scheme:dark;--bg:#0D111A;--panel:#121824;--ink:#EEF2F8;--muted:#98A2B3;--line:#293241;--soft:#18202D;--blue:#5B8CFF;--grid:#273142;--tip:rgba(3,7,18,.96)}
    *{box-sizing:border-box}html,body{margin:0;padding:0;background:var(--bg);color:var(--ink);font-family:Inter,"Noto Sans SC","PingFang SC",Arial,sans-serif}
    .root{width:100%;padding:12px}.terminal{border:1px solid var(--line);border-radius:10px;background:var(--panel);overflow:hidden}
    header{display:flex;justify-content:space-between;gap:14px;padding:14px 16px 11px;border-bottom:1px solid var(--line)}
    .identity{min-width:0}.eyebrow{font-size:11px;color:var(--muted);letter-spacing:.06em}.title-row{display:flex;align-items:baseline;gap:10px;margin-top:4px;flex-wrap:wrap}
    h1{font-size:19px;line-height:1.25;margin:0}.latest{font-size:22px;font-weight:750;font-variant-numeric:tabular-nums}.change{font-size:13px;font-weight:700}
    .subtitle{color:var(--muted);font-size:12px;margin-top:5px}.toolbar{display:flex;gap:6px;align-items:flex-start;flex-wrap:wrap;justify-content:flex-end}
    .chip{border:1px solid var(--line);border-radius:5px;background:var(--soft);padding:4px 7px;color:var(--muted);font-size:11px}.chip.active{color:var(--blue);border-color:var(--blue);background:transparent}
    .metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));border-bottom:1px solid var(--line)}
    .metric{padding:9px 14px;border-right:1px solid var(--line)}.metric:last-child{border-right:0}.metric span{display:block;color:var(--muted);font-size:10px}.metric b{display:block;font-size:14px;margin-top:2px;font-variant-numeric:tabular-nums}
    .legend{display:flex;gap:14px;align-items:center;padding:8px 16px 0;color:var(--muted);font-size:11px}.legend i{display:inline-block;width:14px;height:2px;margin-right:5px;vertical-align:middle}
    .chart-wrap{position:relative;padding:2px 8px 0}.chart{display:block;width:100%;height:455px}.tooltip{position:absolute;display:none;pointer-events:none;z-index:3;min-width:170px;padding:9px 11px;border-radius:7px;background:var(--tip);color:#fff;font-size:12px;line-height:1.55;box-shadow:0 8px 24px rgba(0,0,0,.24);font-variant-numeric:tabular-nums}
    footer{padding:6px 16px 12px;color:var(--muted);font-size:10px;line-height:1.5}
    @media(max-width:620px){.root{padding:6px}header{display:block}.toolbar{justify-content:flex-start;margin-top:10px}.metrics{grid-template-columns:repeat(2,1fr)}.metric:nth-child(2){border-right:0}.metric:nth-child(-n+2){border-bottom:1px solid var(--line)}.chart{height:420px}}
  </style>
</head>
<body>
<main class="root"><section class="terminal" aria-label="交互式股价图">
  <header><div class="identity"><div class="eyebrow" id="eyebrow"></div><div class="title-row"><h1 id="title"></h1><span class="latest" id="latest"></span><span class="change" id="change"></span></div><div class="subtitle" id="subtitle"></div></div><div class="toolbar"><span class="chip active" id="timeframe"></span><span class="chip" id="adjustment"></span></div></header>
  <div class="metrics"><div class="metric"><span>区间最高</span><b id="high"></b></div><div class="metric"><span>区间最低</span><b id="low"></b></div><div class="metric"><span>区间振幅</span><b id="range"></b></div><div class="metric"><span>累计成交量</span><b id="volume"></b></div></div>
  <div class="legend"><span><i style="background:var(--blue)"></i>价格</span><span id="avg-legend"><i style="background:#D99A2B"></i>均价</span><span><i style="border-top:1px dashed #98A2B3;height:1px"></i>昨收/基准</span></div>
  <div class="chart-wrap"><canvas class="chart" id="chart"></canvas><div class="tooltip" id="tooltip"></div></div>
  <footer id="note"></footer>
</section></main>
<script>
const MODEL=__MODEL__;document.body.dataset.theme=MODEL.theme;
const points=MODEL.series,eventMap=new Map();for(const e of MODEL.events){if(!eventMap.has(e.time))eventMap.set(e.time,[]);eventMap.get(e.time).push(e.label)}
const $=id=>document.getElementById(id),canvas=$("chart"),tip=$("tooltip"),ctx=canvas.getContext("2d");let hover=-1;
const dark=MODEL.theme==="terminal-dark",grid=dark?"#273142":"#E8ECF2",muted=dark?"#98A2B3":"#667085",ink=dark?"#EEF2F8":"#172033",blue=dark?"#5B8CFF":"#2F6BFF";
const fmt=(v,d=MODEL.price_decimals)=>Number(v).toLocaleString("zh-CN",{minimumFractionDigits:d,maximumFractionDigits:d});
const volumeFmt=v=>v==null?"—":v>=1e8?fmt(v/1e8,2)+" 亿":v>=1e4?fmt(v/1e4,1)+" 万":fmt(v,0);
const esc=s=>String(s).replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[m]));
const first=points[0],last=points[points.length-1],closes=points.map(d=>d.close),high=Math.max(...closes),low=Math.min(...closes),change=(last.close/MODEL.previous_close-1)*100,totalVolume=points.reduce((s,d)=>s+(d.volume||0),0),hasAverage=points.some(d=>d.average!=null),hasVolume=points.some(d=>d.volume!=null);
$("eyebrow").textContent=[MODEL.market,MODEL.symbol,MODEL.currency].filter(Boolean).join(" · ")||"PRICE";$("title").textContent=MODEL.title;$("latest").textContent=fmt(last.close);$("change").textContent=`${change>=0?"+":""}${fmt(change,2)}%`;$("change").style.color=change>=0?MODEL.colors.up:MODEL.colors.down;
$("subtitle").textContent=MODEL.subtitle||`${first.time} 至 ${last.time}`;$("timeframe").textContent=MODEL.timeframe;$("adjustment").textContent=MODEL.adjustment;$("high").textContent=fmt(high);$("low").textContent=fmt(low);$("range").textContent=fmt((high/low-1)*100,2)+"%";$("volume").textContent=hasVolume?volumeFmt(totalVolume):"—";$("avg-legend").style.display=hasAverage?"inline":"none";
$("note").textContent=[`口径：${MODEL.adjustment}`,MODEL.source_note,`基准价：${fmt(MODEL.previous_close)}`,`共 ${points.length} 个价格点；悬停查看明细`].filter(Boolean).join(" ｜ ");
function shortTime(v){return v.length<=10?v.slice(5):v.replace("T"," ").slice(5,16)}
function draw(){const box=canvas.getBoundingClientRect(),dpr=Math.max(1,window.devicePixelRatio||1),W=Math.max(320,box.width),H=box.height;canvas.width=Math.round(W*dpr);canvas.height=Math.round(H*dpr);ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,W,H);
  const L=22,R=76,T=22,PB=hasVolume?Math.round(H*.72):H-40,VT=hasVolume?Math.round(H*.81):PB,B=30,PW=W-L-R,PH=PB-T,VH=hasVolume?H-VT-B:0;
  const all=[...closes,MODEL.previous_close,...points.filter(d=>d.average!=null).map(d=>d.average)],rawMin=Math.min(...all),rawMax=Math.max(...all),pad=(rawMax-rawMin||rawMax*.01)*.1,pmin=rawMin-pad,pmax=rawMax+pad,vmax=Math.max(1,...points.map(d=>d.volume||0));
  const x=i=>L+PW*i/Math.max(1,points.length-1),yp=v=>T+(pmax-v)/(pmax-pmin)*PH,yv=v=>VT+VH-(v/vmax)*VH;
  ctx.font='11px Inter,"Noto Sans SC",sans-serif';ctx.textBaseline="middle";for(let i=0;i<=5;i++){const y=T+PH*i/5,v=pmax-(pmax-pmin)*i/5;ctx.strokeStyle=grid;ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(L,y);ctx.lineTo(W-R,y);ctx.stroke();ctx.fillStyle=muted;ctx.textAlign="left";ctx.fillText(fmt(v),W-R+8,y)}
  const refY=yp(MODEL.previous_close);ctx.setLineDash([5,4]);ctx.strokeStyle="#98A2B3";ctx.beginPath();ctx.moveTo(L,refY);ctx.lineTo(W-R,refY);ctx.stroke();ctx.setLineDash([]);ctx.fillStyle=muted;ctx.fillText(fmt(MODEL.previous_close),W-R+8,refY);
  const ticks=Math.min(6,points.length);for(let i=0;i<ticks;i++){const idx=Math.round(i*(points.length-1)/Math.max(1,ticks-1));ctx.fillStyle=muted;ctx.textAlign=i===0?"left":i===ticks-1?"right":"center";ctx.fillText(shortTime(points[idx].time),x(idx),H-12)}
  const gradient=ctx.createLinearGradient(0,T,0,PB);gradient.addColorStop(0,dark?"rgba(91,140,255,.28)":"rgba(47,107,255,.23)");gradient.addColorStop(1,"rgba(47,107,255,0)");ctx.beginPath();points.forEach((d,i)=>i?ctx.lineTo(x(i),yp(d.close)):ctx.moveTo(x(i),yp(d.close)));ctx.lineTo(x(points.length-1),PB);ctx.lineTo(x(0),PB);ctx.closePath();ctx.fillStyle=gradient;ctx.fill();
  ctx.beginPath();points.forEach((d,i)=>i?ctx.lineTo(x(i),yp(d.close)):ctx.moveTo(x(i),yp(d.close)));ctx.strokeStyle=blue;ctx.lineWidth=2;ctx.stroke();
  if(hasAverage){let started=false;ctx.beginPath();points.forEach((d,i)=>{if(d.average==null)return;started?ctx.lineTo(x(i),yp(d.average)):ctx.moveTo(x(i),yp(d.average));started=true});ctx.strokeStyle="#D99A2B";ctx.lineWidth=1.4;ctx.stroke()}
  if(hasVolume){const bw=Math.max(1,Math.min(8,PW/points.length*.7));points.forEach((d,i)=>{if(d.volume==null)return;ctx.globalAlpha=.4;ctx.fillStyle=i===0||d.close>=points[i-1].close?MODEL.colors.up:MODEL.colors.down;ctx.fillRect(x(i)-bw/2,yv(d.volume),bw,VT+VH-yv(d.volume));ctx.globalAlpha=1})}
  for(const [time] of eventMap){const i=points.findIndex(d=>d.time===time);if(i<0)continue;const xx=x(i);ctx.fillStyle="#8B5CF6";ctx.beginPath();ctx.arc(xx,yp(points[i].close),4.5,0,Math.PI*2);ctx.fill()}
  if(hover>=0&&hover<points.length){const d=points[hover],xx=x(hover),yy=yp(d.close);ctx.setLineDash([3,3]);ctx.strokeStyle=ink;ctx.beginPath();ctx.moveTo(xx,T);ctx.lineTo(xx,hasVolume?VT+VH:PB);ctx.stroke();ctx.setLineDash([]);ctx.fillStyle=blue;ctx.beginPath();ctx.arc(xx,yy,4,0,Math.PI*2);ctx.fill();ctx.strokeStyle=dark?"#121824":"#fff";ctx.lineWidth=2;ctx.stroke()}
}
function showAt(ev){const r=canvas.getBoundingClientRect(),L=22,R=76,PW=r.width-L-R,idx=Math.max(0,Math.min(points.length-1,Math.round((ev.clientX-r.left-L)/PW*(points.length-1))));hover=idx;const d=points[idx],events=eventMap.get(d.time)||[];tip.innerHTML=`<b>${esc(d.time)}</b><br>价格 ${fmt(d.close)}${d.average!=null?`<br>均价 ${fmt(d.average)}`:""}<br>成交量 ${volumeFmt(d.volume)}${events.length?`<br><span style="color:#C4B5FD">事件：${events.map(esc).join("；")}</span>`:""}`;tip.style.display="block";tip.style.left=Math.min(r.width-184,Math.max(8,ev.clientX-r.left+12))+"px";tip.style.top=Math.max(8,ev.clientY-r.top-72)+"px";draw()}
canvas.addEventListener("pointermove",showAt);canvas.addEventListener("pointerleave",()=>{hover=-1;tip.style.display="none";draw()});if("ResizeObserver" in window)new ResizeObserver(draw).observe(canvas);else window.addEventListener("resize",draw);draw();
setTimeout(()=>{const m=window.magic;if(m&&typeof m.updateHeight==="function")m.updateHeight()},80);
</script>
</body></html>'''


def render_price_chart(data):
    model = validate_price_chart(data)
    description = (
        f"{model['title']} 股价图，期间 {model['series'][0]['time']} 至 "
        f"{model['series'][-1]['time']}，口径 {model['adjustment']}"
    )
    output = PRICE_TEMPLATE
    output = output.replace("__DESCRIPTION__", html.escape(description, quote=True))
    output = output.replace("__TITLE__", html.escape(model["title"]))
    output = output.replace("__MODEL__", safe_script_json(model))
    if len(output) > MAX_HTML_CHARS:
        raise ValueError(f"生成 HTML 超过 {MAX_HTML_CHARS} 字符限制")
    return output


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
    :root{color-scheme:light;--bg:#fff;--panel:#fff;--ink:#172033;--muted:#667085;--line:#E5EAF0;--soft:#F7F9FC;--blue:#2563EB;--grid:#E8ECF2;--tip:rgba(20,28,45,.94)}
    body[data-theme="terminal-dark"]{color-scheme:dark;--bg:#0D111A;--panel:#121824;--ink:#EEF2F8;--muted:#98A2B3;--line:#293241;--soft:#18202D;--blue:#5B8CFF;--grid:#273142;--tip:rgba(3,7,18,.96)}
    *{box-sizing:border-box}html,body{margin:0;padding:0;background:var(--bg);color:var(--ink);font-family:Inter,"Noto Sans SC","PingFang SC",Arial,sans-serif}
    .root{width:100%;max-width:100%;padding:12px}.card{border:1px solid var(--line);border-radius:10px;background:var(--panel);overflow:hidden}
    header{padding:14px 16px 10px;border-bottom:1px solid var(--line)}
    .eyebrow{font-size:12px;letter-spacing:.08em;color:var(--blue);font-weight:700;text-transform:uppercase}.title-row{display:flex;justify-content:space-between;gap:16px;align-items:flex-end;margin-top:7px}
    h1{font-size:20px;line-height:1.25;margin:0}.subtitle{margin-top:5px;color:var(--muted);font-size:12px}.legend{display:flex;gap:12px;align-items:center;color:var(--muted);font-size:11px;white-space:nowrap}
    .dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:5px}.metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;padding:14px 18px 4px}
    .metric{background:var(--soft);border:1px solid var(--line);border-radius:7px;padding:9px 11px}.metric span{display:block;color:var(--muted);font-size:10px}.metric b{display:block;font-size:15px;margin-top:3px;font-variant-numeric:tabular-nums}
    .toolbar,.ma-legend{display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin-top:9px}.chip{border:1px solid var(--line);border-radius:5px;background:var(--soft);padding:3px 7px;color:var(--muted);font-size:10px}.chip.active{color:var(--blue);border-color:var(--blue);background:transparent}.ma-legend{gap:12px;color:var(--muted);font-size:10px}.ma-legend i{display:inline-block;width:14px;height:2px;margin-right:4px;vertical-align:middle}
    .chart-wrap{position:relative;padding:8px 12px 2px}.chart{display:block;width:100%;height:470px}.tooltip{position:absolute;display:none;pointer-events:none;z-index:3;min-width:168px;padding:9px 11px;border-radius:7px;background:var(--tip);color:#fff;font-size:12px;line-height:1.55;box-shadow:0 8px 24px rgba(0,0,0,.18);font-variant-numeric:tabular-nums}
    footer{padding:6px 20px 16px;color:var(--muted);font-size:11px;line-height:1.5}.positive{color:#B4232C}.negative{color:#087A59}
    @media(max-width:620px){.root{padding:8px}.title-row{display:block}.legend{margin-top:10px}.metrics{grid-template-columns:repeat(2,1fr)}.chart{height:430px}}
  </style>
</head>
<body>
<main class="root"><section class="card" aria-label="交互式 K 线图">
  <header><div class="eyebrow" id="eyebrow"></div><div class="title-row"><div><h1 id="title"></h1><div class="subtitle" id="subtitle"></div></div><div class="legend"><span><i class="dot" id="up-dot"></i><span id="up-label"></span></span><span><i class="dot" id="down-dot"></i><span id="down-label"></span></span></div></div><div class="toolbar"><span class="chip active" id="timeframe"></span><span class="chip" id="adjustment"></span><span class="chip" id="count"></span></div><div class="ma-legend" id="ma-legend"></div></header>
  <div class="metrics"><div class="metric"><span>最新收盘</span><b id="latest"></b></div><div class="metric"><span>区间涨跌</span><b id="return"></b></div><div class="metric"><span>区间最高</span><b id="high"></b></div><div class="metric"><span>区间最低</span><b id="low"></b></div></div>
  <div class="chart-wrap" id="wrap"><canvas class="chart" id="chart"></canvas><div class="tooltip" id="tooltip"></div></div>
  <footer id="note"></footer>
</section></main>
<script>
const MODEL=__MODEL__;document.body.dataset.theme=MODEL.theme;
const bars=MODEL.series,eventsByDate=new Map();for(const e of MODEL.events){if(!eventsByDate.has(e.date))eventsByDate.set(e.date,[]);eventsByDate.get(e.date).push(e.label)}
const $=id=>document.getElementById(id),canvas=$("chart"),wrap=$("wrap"),tip=$("tooltip"),ctx=canvas.getContext("2d");let hover=-1;
const dark=MODEL.theme==="terminal-dark",grid=dark?"#273142":"#E8ECF2",muted=dark?"#98A2B3":"#667085",ink=dark?"#EEF2F8":"#172033",maColors=["#E3A72F","#7C66DC","#2F85EB","#16A085","#C25A9B"];
const movingAverages=MODEL.ma_windows.map((window,j)=>({window,color:maColors[j],values:bars.map((_,i)=>i+1<window?null:bars.slice(i-window+1,i+1).reduce((s,d)=>s+d.close,0)/window)}));
const fmt=(v,d=2)=>Number(v).toLocaleString("zh-CN",{minimumFractionDigits:d,maximumFractionDigits:d});
const esc=s=>String(s).replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[m]));
const volumeFmt=v=>v==null?"—":v>=1e8?fmt(v/1e8,2)+" 亿":v>=1e4?fmt(v/1e4,1)+" 万":fmt(v,0);
const first=bars[0],last=bars[bars.length-1],periodReturn=(last.close/first.close-1)*100,periodHigh=Math.max(...bars.map(d=>d.high)),periodLow=Math.min(...bars.map(d=>d.low));
$("eyebrow").textContent=[MODEL.market,MODEL.symbol,MODEL.currency].filter(Boolean).join(" · ")||"PRICE ACTION";$("title").textContent=MODEL.title;$("subtitle").textContent=MODEL.subtitle||`${first.date} 至 ${last.date} · ${MODEL.adjustment}`;
$("latest").textContent=fmt(last.close);$("return").textContent=`${periodReturn>=0?"+":""}${fmt(periodReturn)}%`;$("return").style.color=periodReturn>=0?MODEL.colors.up:MODEL.colors.down;$("high").textContent=fmt(periodHigh);$("low").textContent=fmt(periodLow);
$("up-dot").style.background=MODEL.colors.up;$("down-dot").style.background=MODEL.colors.down;$("up-label").textContent=MODEL.palette==="cn"?"上涨":"Up";$("down-label").textContent=MODEL.palette==="cn"?"下跌":"Down";
$("timeframe").textContent=MODEL.timeframe;$("adjustment").textContent=MODEL.adjustment;$("count").textContent=`${bars.length} 根`;$("ma-legend").innerHTML=movingAverages.map(m=>`<span><i style="background:${m.color}"></i>MA${m.window}</span>`).join("");
$("note").textContent=[`口径：${MODEL.adjustment}`,MODEL.source_note,`共 ${bars.length} 个交易日；悬停查看 OHLC、成交量与事件`].filter(Boolean).join(" ｜ ");
function draw(){const box=canvas.getBoundingClientRect(),dpr=Math.max(1,window.devicePixelRatio||1),W=Math.max(320,box.width),H=box.height;canvas.width=Math.round(W*dpr);canvas.height=Math.round(H*dpr);ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,W,H);
  const L=18,R=76,T=24,PB=MODEL.show_volume?Math.round(H*.71):H-34,VT=MODEL.show_volume?Math.round(H*.79):PB,B=30,PW=W-L-R,PH=PB-T,VH=MODEL.show_volume?H-VT-B:0,step=PW/bars.length,cw=Math.max(2,Math.min(12,step*.62));
  let pmin=Math.min(...bars.map(d=>d.low)),pmax=Math.max(...bars.map(d=>d.high));const pad=(pmax-pmin||pmax*.02)*.08;pmin-=pad;pmax+=pad;const vmax=Math.max(1,...bars.map(d=>d.volume||0));
  const x=i=>L+step*(i+.5),yp=v=>T+(pmax-v)/(pmax-pmin)*PH,yv=v=>VT+VH-(v/vmax)*VH;
  ctx.font='11px Inter,"Noto Sans SC",sans-serif';ctx.textAlign="left";ctx.textBaseline="middle";
  for(let i=0;i<=5;i++){const y=T+PH*i/5,v=pmax-(pmax-pmin)*i/5;ctx.strokeStyle=grid;ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(L,y);ctx.lineTo(W-R,y);ctx.stroke();ctx.fillStyle=muted;ctx.fillText(fmt(v),W-R+8,y)}
  const ticks=Math.min(6,bars.length);for(let i=0;i<ticks;i++){const idx=Math.round(i*(bars.length-1)/Math.max(1,ticks-1));ctx.fillStyle=muted;ctx.textAlign=i===0?"left":i===ticks-1?"right":"center";ctx.fillText(bars[idx].date.slice(5),x(idx),H-12)}
  bars.forEach((d,i)=>{const color=d.close>=d.open?MODEL.colors.up:MODEL.colors.down,xx=x(i);ctx.strokeStyle=color;ctx.lineWidth=1.2;ctx.beginPath();ctx.moveTo(xx,yp(d.high));ctx.lineTo(xx,yp(d.low));ctx.stroke();const y1=yp(Math.max(d.open,d.close)),y2=yp(Math.min(d.open,d.close));ctx.fillStyle=color;ctx.fillRect(xx-cw/2,y1,cw,Math.max(1.5,y2-y1));if(MODEL.show_volume&&d.volume!=null){ctx.globalAlpha=.34;ctx.fillRect(xx-cw/2,yv(d.volume),cw,VT+VH-yv(d.volume));ctx.globalAlpha=1}});
  for(const m of movingAverages){let started=false;ctx.beginPath();m.values.forEach((v,i)=>{if(v==null)return;started?ctx.lineTo(x(i),yp(v)):ctx.moveTo(x(i),yp(v));started=true});ctx.strokeStyle=m.color;ctx.lineWidth=1.25;ctx.stroke()}
  for(const [day] of eventsByDate){const i=bars.findIndex(d=>d.date===day);if(i<0)continue;const xx=x(i);ctx.setLineDash([4,4]);ctx.strokeStyle="#7C3AED";ctx.beginPath();ctx.moveTo(xx,T);ctx.lineTo(xx,PB);ctx.stroke();ctx.setLineDash([]);ctx.fillStyle="#7C3AED";ctx.beginPath();ctx.moveTo(xx,T+2);ctx.lineTo(xx-5,T+11);ctx.lineTo(xx+5,T+11);ctx.closePath();ctx.fill()}
  if(hover>=0&&hover<bars.length){const d=bars[hover],xx=x(hover);ctx.setLineDash([3,3]);ctx.strokeStyle=ink;ctx.beginPath();ctx.moveTo(xx,T);ctx.lineTo(xx,MODEL.show_volume?VT+VH:PB);ctx.stroke();ctx.setLineDash([]);ctx.fillStyle=ink;ctx.beginPath();ctx.arc(xx,yp(d.close),3.5,0,Math.PI*2);ctx.fill()}
}
const safeDraw=()=>{try{draw();window.__chartError=""}catch(error){window.__chartError=String(error);console.error(error)}};
function showAt(ev){const r=canvas.getBoundingClientRect(),L=18,R=76,PW=r.width-L-R,idx=Math.max(0,Math.min(bars.length-1,Math.floor((ev.clientX-r.left-L)/(PW/bars.length))));hover=idx;const d=bars[idx],events=eventsByDate.get(d.date)||[],maText=movingAverages.map(m=>m.values[idx]==null?"":`MA${m.window} ${fmt(m.values[idx])}`).filter(Boolean).join("　");tip.innerHTML=`<b>${d.date}</b><br>开 ${fmt(d.open)}　高 ${fmt(d.high)}<br>低 ${fmt(d.low)}　收 ${fmt(d.close)}${maText?`<br>${maText}`:""}<br>成交量 ${volumeFmt(d.volume)}${events.length?`<br><span style="color:#C4B5FD">事件：${events.map(esc).join("；")}</span>`:""}`;tip.style.display="block";const x=Math.min(r.width-184,Math.max(8,ev.clientX-r.left+12)),y=Math.max(8,ev.clientY-r.top-74);tip.style.left=x+"px";tip.style.top=y+"px";safeDraw()}
canvas.addEventListener("pointermove",showAt);canvas.addEventListener("pointerleave",()=>{hover=-1;tip.style.display="none";safeDraw()});if("ResizeObserver" in window)new ResizeObserver(safeDraw).observe(canvas);else window.addEventListener("resize",safeDraw);safeDraw();
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


def render_quadrant(data):
    model = validate_quadrant(data)
    groups = []
    for point in model["points"]:
        if point["group"] not in groups:
            groups.append(point["group"])
    model["groups"] = groups
    note = " ｜ ".join(
        filter(
            None,
            [
                model["as_of"] and f"截至 {model['as_of']}",
                model["source_note"],
            ],
        )
    )
    output = f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="use-iframe" content="true"><meta name="html-box-height-mode" content="auto"><title>{html.escape(model["title"])}</title>
<style>
*{{box-sizing:border-box}}body{{margin:0;background:#fff;color:#172033;font-family:Inter,"Noto Sans SC","PingFang SC",Arial,sans-serif}}
.root{{padding:18px}}.card{{border:1px solid #E5EAF0;border-radius:18px;padding:20px;box-shadow:0 10px 28px rgba(23,32,51,.07);overflow:auto}}
h1{{font-size:22px;margin:0}}.sub{{font-size:13px;color:#667085;margin:6px 0 12px}}.canvas-wrap{{width:100%;min-width:720px;height:520px}}canvas{{display:block;width:100%;height:100%}}
footer{{font-size:11px;color:#98A2B3;margin-top:10px}}
</style></head><body><main class="root"><section class="card" aria-label="多象限分析">
<h1>{html.escape(model["title"])}</h1><div class="sub">{html.escape(model["subtitle"])}</div>
<div class="canvas-wrap"><canvas id="chart"></canvas></div><footer>{html.escape(note)}</footer>
</section></main><script>
const MODEL={safe_script_json(model)},COLORS={safe_script_json(GROUP_COLORS)},canvas=document.getElementById("chart"),ctx=canvas.getContext("2d");
function setup(){{const r=canvas.getBoundingClientRect(),d=Math.min(window.devicePixelRatio||1,2);canvas.width=Math.round(r.width*d);canvas.height=Math.round(r.height*d);ctx.setTransform(d,0,0,d,0,0);return{{w:r.width,h:r.height}}}}
function line(x1,y1,x2,y2,color="#98A2B3",width=1,dash=[]){{ctx.beginPath();ctx.setLineDash(dash);ctx.moveTo(x1,y1);ctx.lineTo(x2,y2);ctx.strokeStyle=color;ctx.lineWidth=width;ctx.stroke();ctx.setLineDash([])}}
function text(v,x,y,align="center",color="#667085",size=12,weight=500){{ctx.fillStyle=color;ctx.font=`${{weight}} ${{size}}px Inter,"Noto Sans SC","PingFang SC",Arial,sans-serif`;ctx.textAlign=align;ctx.textBaseline="middle";ctx.fillText(v,x,y)}}
function draw(){{const{{w,h}}=setup(),p={{l:82,r:28,t:30,b:70}},cw=w-p.l-p.r,ch=h-p.t-p.b,x=MODEL.x_axis,y=MODEL.y_axis,sx=v=>p.l+(v-x.min)/(x.max-x.min)*cw,sy=v=>p.t+ch-(v-y.min)/(y.max-y.min)*ch,splitX=sx(x.split),splitY=sy(y.split);
ctx.clearRect(0,0,w,h);ctx.fillStyle="#F2F7FF";ctx.fillRect(p.l,p.t,splitX-p.l,splitY-p.t);ctx.fillStyle="#EEFAF4";ctx.fillRect(splitX,p.t,w-p.r-splitX,splitY-p.t);ctx.fillStyle="#F7F8FA";ctx.fillRect(p.l,splitY,splitX-p.l,p.t+ch-splitY);ctx.fillStyle="#FFF5F0";ctx.fillRect(splitX,splitY,w-p.r-splitX,p.t+ch-splitY);
line(splitX,p.t,splitX,p.t+ch,"#98A2B3",1.5,[6,6]);line(p.l,splitY,p.l+cw,splitY,"#98A2B3",1.5,[6,6]);line(p.l,p.t+ch,p.l+cw,p.t+ch,"#344054",1.5);line(p.l,p.t,p.l,p.t+ch,"#344054",1.5);
text(MODEL.quadrants.top_left,p.l+12,p.t+18,"left","#3B5B8A",13,700);text(MODEL.quadrants.top_right,p.l+cw-12,p.t+18,"right","#147A55",13,700);text(MODEL.quadrants.bottom_left,p.l+12,p.t+ch-18,"left","#667085",13,700);text(MODEL.quadrants.bottom_right,p.l+cw-12,p.t+ch-18,"right","#A04426",13,700);
text(x.low,p.l,h-44,"left");text(x.high,p.l+cw,h-44,"right");text(x.label,p.l+cw/2,h-22,"center","#344054",13,700);ctx.save();ctx.translate(22,p.t+ch/2);ctx.rotate(-Math.PI/2);text(y.label,0,0,"center","#344054",13,700);ctx.restore();
const sizes=MODEL.points.map(p=>p.size),lo=Math.min(...sizes),hi=Math.max(...sizes),radius=v=>hi===lo?14:10+(v-lo)/(hi-lo)*12;MODEL.points.forEach((point,i)=>{{const px=sx(point.x),py=sy(point.y),r=radius(point.size),color=COLORS[MODEL.groups.indexOf(point.group)%COLORS.length];ctx.globalAlpha=.12;ctx.beginPath();ctx.arc(px,py,r+5,0,Math.PI*2);ctx.fillStyle=color;ctx.fill();ctx.globalAlpha=.88;ctx.beginPath();ctx.arc(px,py,r,0,Math.PI*2);ctx.fill();ctx.globalAlpha=1;ctx.strokeStyle="#fff";ctx.lineWidth=3;ctx.stroke();text(point.label,px+(px>splitX?-r-7:r+7),py+(i%2?-7:7),px>splitX?"right":"left","#172033",12,700)}});
MODEL.groups.forEach((g,i)=>{{const lx=p.l+i*145;ctx.beginPath();ctx.arc(lx,h-6,5,0,Math.PI*2);ctx.fillStyle=COLORS[i%COLORS.length];ctx.fill();text(g,lx+10,h-6,"left","#475467",11,500)}})}}
new ResizeObserver(draw).observe(canvas.parentElement);draw();
</script></body></html>'''
    if len(output) > MAX_HTML_CHARS:
        raise ValueError(f"生成 HTML 超过 {MAX_HTML_CHARS} 字符限制")
    return output


def self_test():
    price_chart = {
        "title": "示例公司分时走势",
        "symbol": "TEST",
        "market": "港股",
        "currency": "HKD",
        "adjustment": "不复权",
        "timeframe": "分时",
        "previous_close": 99.5,
        "theme": "terminal-dark",
        "series": [
            {"time": "2026-07-23 09:30", "close": 100.0, "average": 100.0, "volume": 1000},
            {"time": "2026-07-23 10:00", "close": 101.2, "average": 100.5, "volume": 1800},
            {"time": "2026-07-23 10:30", "close": 100.8, "average": 100.7, "volume": 900},
        ],
        "events": [{"time": "2026-07-23 10:00", "label": "公告 </script>"}],
    }
    price_output = render_price_chart(price_chart)
    if (
        "<canvas" not in price_output
        or "html-box-height-mode" not in price_output
        or "terminal-dark" not in price_output
        or "<\\/script>" not in price_output
        or price_output.count("</script>") != 1
        or "https://" in price_output
    ):
        raise AssertionError("股价图 HTML 自测失败")
    invalid_price = json.loads(json.dumps(price_chart))
    invalid_price["series"][1]["time"] = invalid_price["series"][0]["time"]
    try:
        render_price_chart(invalid_price)
    except ValueError:
        pass
    else:
        raise AssertionError("股价图重复时间应被拒绝")

    kline = {
        "title": "示例公司股价路径", "symbol": "TEST", "market": "A股",
        "currency": "CNY", "adjustment": "前复权", "palette": "cn",
        "theme": "terminal-light", "timeframe": "日 K", "ma_windows": [2, 3],
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
            or '"ma_windows":[2,3]' not in html_output
            or html_output.count("</script>") != 1
            or "https://" in html_output):
        raise AssertionError("K 线 HTML 自测失败")
    invalid_kline = json.loads(json.dumps(kline))
    del invalid_kline["series"][0]["open"]
    try:
        render_kline(invalid_kline)
    except ValueError:
        pass
    else:
        raise AssertionError("缺少 OHLC 时应拒绝生成 K 线")

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
    quadrant_output = render_quadrant(quadrant)
    if (
        "<canvas" not in quadrant_output
        or "html-box-height-mode" not in quadrant_output
        or "公司 A" not in quadrant_output
        or quadrant_output.count("</script>") != 1
    ):
        raise AssertionError("象限 HTML 自测失败")
    invalid_quadrant = json.loads(json.dumps(quadrant))
    invalid_quadrant["x_axis"]["label"] = ""
    try:
        render_quadrant(invalid_quadrant)
    except ValueError:
        pass
    else:
        raise AssertionError("象限轴缺少定义时应拒绝生成")
    emit("SELF_TEST_PASS")


def build_parser():
    parser = argparse.ArgumentParser(description="生成飞书股票研究高级可视化。")
    parser.add_argument("--self-test", action="store_true")
    subparsers = parser.add_subparsers(dest="command")
    for name, help_text in (
        ("price", "生成自包含的交互式股价/分时 HTML block"),
        ("kline", "生成自包含的交互式 K 线 HTML block"),
        ("quadrant", "生成自包含的交互式多象限 HTML block"),
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
        parser.error("请选择 price、kline 或 quadrant，或使用 --self-test")
    try:
        data = load_object(args.input_json)
        if args.command == "price":
            content = render_price_chart(data)
        elif args.command == "kline":
            content = render_kline(data)
        else:
            content = render_quadrant(data)
        output = write_output(args.output, content, args.input_json)
    except Exception as exc:
        emit(f"[错误] {exc}")
        return 1
    emit(f"已生成: {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
