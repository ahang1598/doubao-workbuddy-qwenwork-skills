#!/usr/bin/env python3
"""真值门 —— 全部在真实浏览器里量，全部是"看图看不出、但读者受损"的项。

没有这条通路的包有 50 条登记在册的门、10,224 行校验器，产物依然丑。
原因不是门写得不好，是**门守的是下限，抬不高上限**；
而"丑"的主要来源（构成错）根本不是能从 DOM 里查出来的属性。
所以这里只留下限，上限交给 shoot.py + observe.py 的看图闭环。

设计原则（每条都有代价换来的证据）：
  · 只留数值可判的项，形态类判据一律不做门
    （旧包「每个数据屏必须有 >=48px 巨数字」会判死词云屏和称号屏两种正当版式）
  · 对比度必须跳过背景不可信的文字
    （不跳过会把压在满版照片上的白字导航判成 1.18:1）
  · **任何门在"目标集合为空"时必须 FAIL，不能 PASS**（见 add() 的 subject 参数）
  · 任何 BLOCK 门判死参照案例里的产物，就是这条判据不对

用法：
    python3 check.py --url <URL|本地路径> --profile web|h5|app-screen|doc [--aesthetic]
    python3 check.py --canvas <画布.html> [--doc-voice]
"""
from __future__ import annotations

import argparse
import hashlib
import http.server
import json
import re
import socket
import socketserver
import sys
import threading
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import runstate  # noqa: E402

# ── 只有这些是 BLOCK，其余 REPORT。想把任何一条加进 BLOCK 之前，先拿 gold 跑一遍 ──
# element-overlap 对应的是肉眼能直接看到的缺陷
# ——固定 CTA 盖住第二张路线卡。实测 gold 三个产物 0 命中，低分参照样本 首页 7 命中。
# 这两条 BLOCK 都对应肉眼能直接看到的缺陷：
# img-upscaled       连续三轮造成同一个缺陷（"文档里图片模糊"），且判据本身量错了单位
# prototype-not-deck 「小程序首页改版」被做成 5 屏宣讲 deck —— 严重缺陷
# 门的收支（说准数，不许含糊）：
# 删 2 道判据（content-under-dock 的 **app-screen 分支**、screen-fit），
# 加 1 条 BLOCK（frame-intact）。
# **BLOCK 集合 13 → 14**（content-under-dock 留在集合里，因为 h5 分屏版还在用它）。
# 七种载体共用这一套：新载体靠 SKIP_BY_PROFILE **关掉**不适用的，不加新门。
# 三条改动各自的理由：
# 删 content-under-dock 的 **app-screen 分支**（h5 分屏版保留，见下面 B2 那段注释）
# 删 screen-fit（frame 兜底到 body，`html,body{height:100%}` 的骨架家族**恒真**）
# 加 frame-intact（移动端在 1440 下版心必须 <=520px —— 用户报的
# 「h5 没走移动端的模板」就是它，而全包此前**零处判据**）
BLOCK = {"text-invisible", "img-broken", "first-view-media", "overflow-x",
         "screen-height", "content-under-dock", "element-overlap", "orphan-row",
         "canvas-structure()", "canvas-oversize", "placeholder",
         "img-upscaled", "prototype-not-deck", "frame-intact", "device-scale"}
# device-scale 升 BLOCK 的标定：三份 doc gold + 两份真实画布跑过，
# 只有「手机截图通栏铺开」那一份该红。它对应汇报受众一眼能看到的缺陷，
# 与 img-upscaled 同一类（"文档里的图不对"），而不是审美偏好。

LARK_HTML5_MAX_BYTES = 512_000
STRUCT_TAGS = re.compile(r"</?(?:html|head|body|style|script)\b", re.I)

PROFILES = {"web": (1440, 900), "h5": (390, 844),
            "app-screen": (390, 844), "doc": (698, 900),
            # 新增四种载体。**新增门码 0 条** ——
            # 它们的分化靠"关掉不适用的门"，不靠加门（见 SKIP_BY_PROFILE）。
            "web-console": (1440, 900), "spec-board": (1600, 1000),
            "big-screen": (1920, 1080), "long-image": (750, 1200)}

# 哪些门对哪种载体**不适用**。这是 唯一的分化机制：
# 七种载体共用同一套门码，靠减法而不是加法。
#
# web-console   B 端 40% 是图就是设计错误（"满屏图表没有操作入口"是失分项）
# spec-board    展板是**给人看的方案图**，不是可运行界面：没有首屏、不触控、横向本来就宽
# big-screen    大屏不滚动、不触控（24px 热区对 4001px 画布无意义）
# long-image    单栏纵向，没有"屏"也没有栏
SKIP_BY_PROFILE = {
    # aes-flat-ground 的判据是"浅底 + 首屏影像 <15% = 白卡片阵列"。
    # 对 B 端这条是**反的**：评分细则明写"满屏图表没有操作入口"是失分项，
    # 亮底 + 低影像正是一张监控页该有的样子。
    "web-console": {"first-view-media", "aes-flat-ground"},
    "spec-board": {"first-view-media", "overflow-x", "hit-area", "screen-height",
                   "dock-at-bottom", "reading-gutter"},
    "big-screen": {"first-view-media", "overflow-x", "hit-area", "screen-height",
                   "dock-at-bottom"},
    "long-image": {"first-view-media", "screen-height", "dock-at-bottom", "hit-area"},
}
# 飞书块宽在 560–1145 之间浮动。只量 698 / 820 两个"典型值"是不够的，
# 而图被放大得最狠的恰恰是**最宽**的那个块 —— 判据没量最坏情况，等于没量。
# 画布 .cv 有 max-width:900，所以 1145 之后版心不再变宽，1145 就是最坏情况。
DOC_WIDTHS = [698, 820, 1145]

RUNTIME_PROBE = r"""
(cfg) => {
  const profile = cfg.profile, wantAesthetic = cfg.aesthetic;
  /* 真实视觉资产的下限**按载体分**。8 标定自影像驱动的稿（gold web-pulse 17、
     h5-qq2026 14）；拿同一个数去要求一张 B 端监控页、一块流程展板，
     量的是错的东西 —— 那几类的"画面"就是图表、表格和界面本身。
     每个数字的依据（不是拿 gold 的实测值回填，那是把阈值拟合到样本上）：
       app-screen  5  产品界面靠列表和数据，内容即画面
       web-console 3  评分细则明写"数据单纯罗列没有图表"是扣分项 →
                      一张合格的监控页至少要有趋势/构成/对比三类图
       big-screen  3  同上，且大屏的地图本身算一个
       spec-board  0  展板的画面是帧内界面，它们是 HTML 画的，不计入资产 —— 这条不适用
       long-image  6  长图必须有真实素材（礼品图、人像），否则就是一根纯文字面条 */
  const ASSET_FLOOR = {'web': 8, 'h5': 8, 'app-screen': 5, 'doc': 8,
                       'web-console': 3, 'big-screen': 3, 'spec-board': 0,
                       'long-image': 6};
  const out = [];
  /* 目标集合为空时一律 FAIL。
     空真空通过已经出过三次事故：图片门（0 张图报绿）、分屏门（选择器不匹配报绿）、
     App 关键屏（.screen 一个都不匹配，four 道门静默跳过，every() 对空数组返回 true）。
     所以凡是"这道门要检查的东西"本身可能为空的，都必须把 subject 传进来。 */
  const add = (code, ok, detail, want, subject) => {
    if (subject === 0) {
      ok = false;
      detail = (detail || '') + '（这道门的目标集合为空——大概率是选择器没匹配上）';
    }
    out.push({code, ok, detail: String(detail), want});
  };
  const vw = innerWidth, vh = innerHeight, VA = vw * vh;
  const area = r => Math.max(0, r.width) * Math.max(0, r.height);
  /* 祖先链一起看：父级 opacity:0 / visibility:hidden 的元素在 DOM 里有盒子，
     但画面上没有。不看祖先链，重叠门会在 gold/web-pulse 上报 40 处假阳性
     （尺码选择器是 hover 才显形的，它的盒子一直压在标题上）。 */
  const painted = e => {
    let q = e;
    while (q && q.nodeType === 1) {
      const s = getComputedStyle(q);
      if (s.display === 'none' || s.visibility === 'hidden') return false;
      if (parseFloat(s.opacity) < .06) return false;
      q = q.parentElement;
    }
    return true;
  };
  const inFold = r => r.top < vh && r.bottom > 0;

  /* 1 图片真的解码且渲染出来了 —— 旧包量的是 HTML 属性里写的尺寸，
        于是 152×113 的缩略图和渲染成 1×0 的图都报 PASS */
  // 这道门只管"贴进来的图有没有坏"。
  // "页面上有没有画面"由 first-view-media 管 —— 两件事分开，
  // 否则会判死画面全是 SVG/CSS 手绘的稿（复古像素 H5 一张 <img> 都没有，但它并不缺画面）。
  const imgs = [...document.images];
  const broken = imgs.filter(i =>
    i.naturalWidth === 0 || i.getBoundingClientRect().width < 8
                         || i.getBoundingClientRect().height < 8)
    .map(i => (i.currentSrc || i.src).split('/').pop());
  add('img-broken', broken.length === 0, broken.slice(0, 5).join(','),
      '贴进来的图都解码且渲染 >8px');

  /* 1a 成品页引用了外链图 —— **在交付端一定碎**，而这里可能是绿的。
        已知失败条件：页面里 11 张图全是宿主搜索结果的地址
        （p3-doubao-search-sign.byteimg.com/…&x-signature=…、aka.doubaocdn.com/s/…）。
        app_builder 沙箱取不到它们，用户打开卡片看到的是一排 alt 文字。
        本地量的时候这些 URL 有时还能取到，所以 img-broken 不一定报——
        **判据必须是引用形态，不是"此刻能不能取到"，那是两件事。**
        doc 画布不查这条：它有自己的 canvas-img-embedded（必须 data: URI）。 */
  if (profile !== 'doc') {
    const remote = imgs.map(i => i.getAttribute('src') || '')
      .filter(s => /^(https?:)?\/\//.test(s))
      .map(s => s.replace(/^https?:\/\//, '').slice(0, 34));
    /* 这条判据只管**盘上这一份成品页**。交付出去的是另一份产物：
       `deliver.py` 会把这些相对路径换成公网 URL，那是 app_builder 唯一能取到图的形态。
       两边不冲突 —— 说清楚这一点，否则执行者会以为交付路径本身是错的。 */
    add('img-remote-src', remote.length === 0, remote.slice(0, 3).join(','),
        '成品页的 <img src> 只能是本地相对路径或 data: URI —— '
        + '成品页要在本机截图、跑门、离线复现，外链让这三件事都不可靠；'
        + '带签名参数的地址（x-signature / x-expires / *-sign.*）还会过期。'
        + '把图下到 assets/ 再引用。'
        + '（交付那一份由 deliver.py 换成公网 URL，不用你手工改成外链）');
  }


  /* 1b 图被放大了 —— "图看不清"的唯一成因，而 img-broken 看不见它。
        把它升成 BLOCK，理由是它**连续三轮**造成同一个用户可见缺陷。

        三条真实 trace 的压缩流水线长得一模一样：
          sips -Z 600 → -Z 500 → -Z 400  ／  PIL max_width=800 → 400
        每次撞上飞书 512KB 的上限，第一反应都是**再降尺寸**，从来没有"只降质量"。
        而 -Z 压的是长边：对一张竖着的手机截图，-Z 400 意味着宽度只剩 185px，
        放进 795px 的版心里是 4.3 倍放大。

        判据不能写成 naturalWidth < renderedWidth * 0.9 且只在 698/820 量。
        两个错：0.9 放行了"刚好不够"的图；不量 1145 就没量最坏情况。
        现在：**原始像素不得小于渲染宽度**（比值 <1.0 即 BLOCK），三个宽度都量。
        目标值是 2.0（视网膜）—— 达不到 2.0 不拦你，但那是"发虚"和"清晰"的分界。
        产能在 scripts/pack_img.py：宽度和质量各有下限，长图自动切段。 */
  const ratio = i => i.naturalWidth / Math.max(1, i.getBoundingClientRect().width);
  const up = imgs.filter(i => {
    const r = i.getBoundingClientRect();
    return r.width > 40 && i.naturalWidth > 0 && ratio(i) < 1.0;
  }).map(i => `${(i.currentSrc || i.src).split('/').pop().slice(0, 18)} `
             + `原图${i.naturalWidth}→显示${Math.round(i.getBoundingClientRect().width)}`
             + `（${ratio(i).toFixed(2)}×）`);
  const soft = imgs.filter(i => i.getBoundingClientRect().width > 40
                             && i.naturalWidth > 0 && ratio(i) >= 1.0 && ratio(i) < 1.6);
  add('img-upscaled', up.length === 0,
      up.slice(0, 3).join('｜')
      + (up.length === 0 && soft.length
         ? `（另有 ${soft.length} 张倍率 1.0–1.6，2× 屏上会发虚，够用但不清晰）` : ''),
      '原始像素 >= 渲染宽度（目标 2.0×）；pack_img.py 会在宽度和质量下限内协商');

  /* 2 首屏媒体占比 —— 下沿 40% 来自四个获奖参考站的实测 */
  // 用网格采样求"并集面积"，而不是各自面积相加 —— 相加会因重叠算出 >100%。
  // 同时把 CSS 画出来的画面（渐变/背景图）算进去：H5 的封面主角是一台 CSS 画的电视，
  // 只数 <img> 会得出 3%，那是量错了对象，不是页面没画面。
  const rects = [], mediaRects = [];
  document.querySelectorAll('img,video,canvas,svg,[data-visual]').forEach(m => {
    const r = m.getBoundingClientRect();
    if (r.width > 24 && r.height > 24) { rects.push(r); mediaRects.push(r); }
  });
  document.querySelectorAll('*').forEach(m => {
    const bi = getComputedStyle(m).backgroundImage;
    if (bi === 'none') return;
    const r = m.getBoundingClientRect();
    if (r.width > 60 && r.height > 60 && r.width * r.height < VA * 1.4) rects.push(r);
  });
  const NX = 48, NY = 48;
  const union = rs => { let n = 0;
    for (let i = 0; i < NX; i++) for (let j = 0; j < NY; j++) {
      const x = (i + .5) * vw / NX, y = (j + .5) * vh / NY;
      if (rs.some(r => x >= r.left && x <= r.right && y >= r.top && y <= r.bottom)) n++;
    }
    return Math.round(n / (NX * NY) * 1000) / 10; };
  const pct = union(rects);
  // 「有画面」和「有影像」是两件事，要分开量。
  // pct 把 CSS 渐变也算画面（对 first-view-media 是对的：H5 封面的电视是 CSS 画的）；
  // 但判断"这一稿是不是白卡片阵列"时，一个 56×56 的渐变天气图标不该算影像
  // —— 低分参照样本 正是靠这些小渐变把 pct 顶到 19%，而它真实影像是 0。
  const imgPct = union(mediaRects);
  // 这才是「案例 1 整站没有图片」那条死因对应的门，所以它是 BLOCK。
  // 文档画布是文本主导的版面，不适用（它的画面在通栏 plate 里，不在首屏）。
  if (profile !== 'doc')
    add('first-view-media', pct >= 40, pct + '%',
        '>=40%（含 CSS/SVG 画的画面；下沿取自 4 个获奖参考站实测）');

  /* 3 文字对比度 —— 背景不可信一律跳过，这是这道门唯一正确的写法 */
  const lum = c => {
    const m = c.match(/[\d.]+/g); if (!m) return null;
    const [r, g, b] = m.slice(0, 3).map(Number).map(v => {
      v /= 255; return v <= .03928 ? v / 12.92 : Math.pow((v + .055) / 1.055, 2.4);
    });
    return .2126 * r + .7152 * g + .0722 * b;
  };
  const parse = c => { const m = (c || '').match(/[\d.]+/g);
    if (!m) return null;
    return {r:+m[0], g:+m[1], b:+m[2], a: m[3] === undefined ? 1 : +m[3]}; };
  // 半透明底色必须和它背后的东西合成。不合成的话
  // rgba(243,238,225,.14) 的头像底会被当成"接近白"，白字压上去算出 1:1 —— 假阳性。
  const composite = n => {
    const stack = [];
    let q = n;
    while (q) {
      const b = getComputedStyle(q);
      if (b.backgroundImage !== 'none') return null;                    // 压在图/渐变上：不可信
      if ((b.position === 'fixed' || b.position === 'absolute')
          && b.backgroundColor.includes('rgba(0, 0, 0, 0)')) return null; // 透明定位层：不可信
      const c = parse(b.backgroundColor);
      if (c && c.a > 0) { stack.push(c); if (c.a >= .999) break; }
      q = q.parentElement;
    }
    if (!stack.length || stack[stack.length - 1].a < .999) return null;  // 底不封口：不可信
    let out = stack.pop();                                               // 最底下那层是实色
    while (stack.length) {                                               // 由下往上叠
      const t = stack.pop();
      out = {r: t.r * t.a + out.r * (1 - t.a),
             g: t.g * t.a + out.g * (1 - t.a),
             b: t.b * t.a + out.b * (1 - t.a), a: 1};
    }
    return `rgb(${out.r}, ${out.g}, ${out.b})`;
  };
  let worst = 99, who = null, worstFg = null, worstBg = null, worstEl = null;
  /* 补洞：`div` 原本**不在这张表里**。
     真实漏网（在 gold/board-flow 上抓到的）：`<div class="top">选择账户</div>`
     继承了 body 的浅色字，压在弹窗的白底上，实测 1.05:1 —— 肉眼一看就是空的，
     而这道门报 PASS。**判据的对象漏了一整类元素，比阈值定错更隐蔽。**

     加 div 有一个前提，否则会造出一片假阳性：**只量自己有文本节点的元素**。
     包装型 div 的 textContent 包含所有后代，而后代往往自己改了颜色 ——
     拿包装层的 color 去配后代的文字，量的是一个不存在的组合。 */
  document.querySelectorAll('p,h1,h2,h3,h4,h5,span,a,button,li,dd,dt,small,td,th,'
      + 'div,figcaption,label,b,strong,em')
    .forEach(n => {
      const own = [...n.childNodes].some(
        k => k.nodeType === 3 && k.textContent.trim().length >= 2);
      if (!own) return;
      const s = getComputedStyle(n);
      if (s.visibility === 'hidden' || s.opacity === '0' || s.display === 'none') return;
      const bg = composite(n);
      if (!bg) return;
      const l1 = lum(s.color), l2 = lum(bg);
      if (l1 === null || l2 === null) return;
      const c = (Math.max(l1, l2) + .05) / (Math.min(l1, l2) + .05);
      if (c < worst) {
        worst = c;
        who = n.tagName + ':' + n.textContent.trim().slice(0, 16);
        worstFg = s.color; worstBg = bg; worstEl = n;
      }
    });
  /* 只报比值 = 让人蒙。实测代价：同一条 BLOCK 连报 9 次，
     执行者改了 8 处硬编码色值都没命中，最后靠改暗品牌主色才过 ——
     门把设计决定改了，那不是门该有的权力。
     所以三件事一起给：**前景 hex、背景 hex、一个算好的同色相替代值**，
     再加上到底是哪个元素（选择器路径），改一次就能对。 */
  const toHex = rgb => {
    const m = (rgb || '').match(/[\d.]+/g); if (!m) return rgb;
    return '#' + m.slice(0, 3).map(v => (+v | 0).toString(16).padStart(2, '0'))
      .join('').toUpperCase();
  };
  const relL = rgb => lum(rgb);
  const darken = (fg, bg, need) => {
    /* 沿同一色相把前景压暗（或提亮）到刚好够，保留设计意图里的颜色关系 */
    const m = (fg || '').match(/[\d.]+/g); if (!m) return '';
    const lb = relL(bg); if (lb === null) return '';
    let best = '', rgb = m.slice(0, 3).map(Number);
    const goDark = lb > 0.18;               // 底亮就压暗字，底暗就提亮字
    for (let k = 1; k <= 100; k++) {
      const f = goDark ? 1 - k / 100 : 1 + k / 100 * 3;
      const t = rgb.map(v => Math.max(0, Math.min(255, Math.round(v * f))));
      const lf = relL(`rgb(${t.join(',')})`);
      const cc = (Math.max(lf, lb) + .05) / (Math.min(lf, lb) + .05);
      if (cc >= need) { best = toHex(`rgb(${t.join(',')})`) + '（' + cc.toFixed(2) + ':1）'; break; }
    }
    return best;
  };
  const path = el => {
    if (!el) return '';
    const bits = [];
    for (let e = el; e && e.tagName && bits.length < 3; e = e.parentElement) {
      bits.unshift(e.tagName.toLowerCase()
        + (e.className && typeof e.className === 'string'
           ? '.' + e.className.trim().split(/\s+/).slice(0, 2).join('.') : ''));
    }
    return bits.join(' > ');
  };
  const fix = worst >= 3.0 ? '' :
    ('　' + toHex(worstFg) + ' 压在 ' + toHex(worstBg) + ' 上'
     + '　在哪：' + path(worstEl)
     + (darken(worstFg, worstBg, 3.0)
        ? '　改成：' + darken(worstFg, worstBg, 3.0) + ' —— 同色相压暗，不用动风格签名'
        : '　同色相压暗到 3:1 不可达，改底色'));
  add('text-invisible', worst >= 3.0,
      (Math.round(worst * 100) / 100) + ':1 @ ' + who + fix,
      '>=3.0:1（背景可信的文字）');

  /* 4 最小字号 —— 装饰字形用 data-decor 显式豁免，豁免要写理由 */
  const tiny = [];
  document.querySelectorAll('*').forEach(e => {
    if (e.closest('[data-decor]')) return;
    if (![...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) return;
    const s = getComputedStyle(e);
    if (s.visibility === 'hidden' || s.opacity === '0') return;
    const f = parseFloat(s.fontSize);
    if (f < 10) tiny.push((e.className || e.tagName) + ':' + f);
  });
  add('font-too-small', tiny.length === 0, tiny.slice(0, 4).join(','), '无 <10px 正文');

  /* 5 单位/后缀不能被 em 坑掉 —— 真实 bug：.unit 是巨数字的兄弟节点不是子节点，
        font-size:.26em 按父级 16px 算 = 4.16px，六处单位全隐形，肉眼几乎发现不了。
        这道门是"有就查，没有跳过"，所以**不传 subject** —— 页面没有单位标签是正当的。 */
  const units = [...document.querySelectorAll('.unit,[data-unit]')]
    .map(u => parseFloat(getComputedStyle(u).fontSize));
  add('unit-too-small', units.length === 0 || Math.min(...units) >= 14,
      units.join(','), '单位标签 >=14px（有就查，没有跳过）');

  /* 6 横向溢出 */
  const ovf = document.documentElement.scrollWidth - vw;
  add('overflow-x', ovf <= 1, ovf + 'px', '<=1px');

  /* 7 占位符残留。
     除了 TODO 这类通用词，**脚本自己产的图位说明也是占位符** ——
     它由 cfg.slotCaptions 传进来（唯一来源是 pack_img.py 的那几个常量），
     不在这里再抄一份，否则改了文案门还认旧的。
     实测代价：图位说明原样发布给汇报受众，同一句话出现 6 次。 */
  const slotCaps = (cfg.slotCaptions || []).filter(Boolean)
    .map(s => s.replace(/[.*+?^${}|[\\]\\\\]/g, '\\\\$&'));
  const reAll = new RegExp(
    ['<填[：:][^>]*>', 'TODO', 'Lorem ipsum', '待填'].concat(slotCaps).join('|'), 'g');
  const ph = (document.body.innerText.match(reAll) || []);
  add('placeholder', ph.length === 0, ph.slice(0, 3).join(','),
      '无占位符（含图位说明：脚本给的那句话要换成你自己的）');

  /* 8 交互元素可达 */
  const small = [...document.querySelectorAll('button,a[href],input,select')]
    .filter(e => { const r = e.getBoundingClientRect();
      return r.width > 0 && r.height > 0 && (r.height < 24 || r.width < 24); }).length;
  add('hit-area', small === 0, small + ' 个', '可点元素 >=24px');

  /* 9 元素重叠 —— 对应肉眼能直接看到的缺陷。
        两条判别缺一不可，少任何一条都会在 gold 上报几十处假阳性：
          a) painted()：祖先链 opacity/visibility 都要看
          b) elementFromPoint：交叠区中心必须真的被 A 或 B 画着
        实测 gold 三个产物 0 命中；低分参照样本 首页 7 命中，
        其中就是用户报的「固定 CTA 盖住第二张路线卡」。 */
  /* 贴底常驻栏：按几何认，三种定位都要认。
     只认 fixed|sticky 是不够的，而两份骨架的底栏都是 absolute（它们在 #app 取景框里），
     于是 app-screen 的 content-under-dock 目标集合永远为空 —— **空真空通过**。
     这里统一算一次，下面三道门共用。 */
  const BOTTOM_BARS = [...document.querySelectorAll('*')].filter(e => {
    const s = getComputedStyle(e);
    if (!['fixed', 'sticky', 'absolute'].includes(s.position)) return false;
    if (!painted(e)) return false;
    const r = e.getBoundingClientRect();
    // 子元素只数**个数**，不数标签名。不要写成 'a,button,li,span,svg' >= 2，
    // 而阳性对照 tests/regressions/floating-dock 的 tab 项是 <div class="tab-item">
    // —— 一个都不匹配，于是那道门在它自己的阳性对照上**从来没有 FAIL 过**，
    // 而断言只查了"门名出现在输出里"，所以一路绿灯。
    // 否定式的标签枚举挡不住换个标签，这已经是第三次了。
    return r.width >= vw * 0.6 && r.height >= 36 && r.height <= vh * 0.35
           && r.bottom > vh * 0.55 && e.children.length >= 2;
  });
  /* 滚动容器有没有给底栏**预留位置**。这才是"内容被压住"和"内容滚过去"的分界：
     内容从底栏下面滚过去是每个 App 都这样（iOS / Android 都是），不是缺陷；
     缺陷是**滚到底也压着**，因为容器没给底栏留 padding。低分参照样本 就是后者。 */
  /* 只有**贴底细条**才要求预留位置。实测：叫车页的底部上浮面板高 225px
     （27% 视口），地图故意从它下面延伸出去 —— 那是 bottom sheet，不是常驻底栏，
     没有"滚到底还压着"这回事。>18% 视口高的一律当面板，不进这条。
     另外：整页没有可滚动容器时（纯地图/纯画布）也跳过。 */
  const barsForReserve = BOTTOM_BARS.filter(
    b => b.getBoundingClientRect().height <= vh * 0.18);
  const scrollers = [...document.querySelectorAll('*')].filter(
    e => /auto|scroll/.test(getComputedStyle(e).overflowY)
         && e.scrollHeight > e.clientHeight + 8);
  const barH = barsForReserve.length
    ? Math.max(...barsForReserve.map(b => b.getBoundingClientRect().height)) : 0;
  const reserved = !barH || !scrollers.length
    || scrollers.some(e => parseFloat(getComputedStyle(e).paddingBottom) >= barH - 6)
    || parseFloat(getComputedStyle(document.body).paddingBottom) >= barH - 6;

  const inBar = e => BOTTOM_BARS.some(b => b.contains(e));
  const tn = [...document.querySelectorAll('*')].filter(e => {
    if (e.closest('[data-decor]')) return false;
    if (![...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) return false;
    if (!painted(e)) return false;
    const r = e.getBoundingClientRect();
    return r.width > 8 && r.height > 8 && r.bottom > 0 && r.top < vh;
  });
  const laps = [];
  for (let i = 0; i < tn.length; i++) for (let j = i + 1; j < tn.length; j++) {
    const A = tn[i], B = tn[j];
    if (A.contains(B) || B.contains(A)) continue;
    const a = A.getBoundingClientRect(), b = B.getBoundingClientRect();
    const w = Math.min(a.right, b.right) - Math.max(a.left, b.left);
    const h = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
    if (w <= 2 || h <= 2) continue;
    if ((w * h) / Math.min(area(a), area(b)) <= .15) continue;
    const cx = (Math.max(a.left, b.left) + Math.min(a.right, b.right)) / 2;
    const cy = (Math.max(a.top, b.top) + Math.min(a.bottom, b.bottom)) / 2;
    const top = document.elementFromPoint(cx, cy);
    if (!top || !(A.contains(top) || B.contains(top)
                  || top.contains(A) || top.contains(B))) continue;
    /* 交叠区被**不透明的常驻底栏**盖住，而滚动容器又给底栏留了位置 ——
       那是**遮挡**不是**碰撞**：内容从底栏下面滚过去，用户什么也没丢，
       这是每个 App 都这样。判据必须落在"盖在上面的那一层"上，
       不能只看"两个元素分属栏内栏外"——低分参照样本 的真实缺陷正好相反：
       那里是两块内容自己撞在一起，跟底栏无关。
       "滚到底还压着"由 dock-reserved 管，不由这道门管。 */
    if (reserved && inBar(top)) {
      const bar = BOTTOM_BARS.find(x => x.contains(top));
      const bg = getComputedStyle(bar).backgroundColor;
      const m = bg.match(/rgba?\(([^)]+)\)/);
      const alpha = m ? parseFloat((m[1].split(',')[3] || '1')) : 1;
      if (alpha >= 0.85) continue;
    }
    laps.push(`「${A.textContent.trim().slice(0, 8)}」∩「${B.textContent.trim().slice(0, 8)}」`);
  }
  add('element-overlap', laps.length === 0, laps.slice(0, 4).join(' '),
      '同层文字元素两两不相交');

  /* 10 正文不许贴着版心边 —— 这条原本只在 doc profile 跑，实测证明它对**每种载体**都成立。
        已知失败条件：`.specs{padding:120px 0}` 写在 `.wrap{padding-inline:var(--gut)}`
        后面，**padding 简写把 padding-inline 清零了**，于是整段左右留白变 0，
        标题第一个字和右列数值都被切在边缘上。声明写了，被静默清掉了。
        所以判据不看你写没写 padding，只看**文字实际离边多远**。 */
  const host = document.querySelector('.cv') || document.body;
  const hostBox = host.getBoundingClientRect();
  const proseSel = 'p,h1,h2,h3,li,dd,td,figcaption,[data-body]';
  /* 门槛从 30 字降到 8 字。实测：排行榜页每行 14 字、叫车面板一句话都没有 30 字，
     于是 prose 为空 → subject=0 → **强制 FAIL 一个完全正当的产品界面**。
     "目标集合为空必须 FAIL" 治的是选择器写错，不该用来治"这个产品本来就没有长段落"。
     所以两件事一起改：门槛降到 8 字（短行也会贴边，也该量），
     并且真的一个文本块都没有时（纯地图 / 纯画布）跳过而不是判死。 */
  const prose = [...host.querySelectorAll(proseSel)].filter(e => {
    if (e.textContent.trim().length < 8) return false;
    if (!painted(e)) return false;
    const r = e.getBoundingClientRect();
    if (r.width <= 60 || r.height <= 4 || r.width > vw + 2) return false;
    // 跑马灯 / 横向轨道里的项**本来就该伸出版心**，不是贴边缺陷。
    // 靠"至少 30 字"筛掉它们是不行的，代价是排行榜页每行 14 字也被筛掉，
    // 于是目标集合为空、强制 FAIL 了一个正当的产品界面。
    // 改成按几何认：盒子必须整个落在版心之内，才轮得到量它离边多远。
    return r.left >= hostBox.left - 1 && r.right <= hostBox.right + 1;
  });
  const gaps = prose.map(e => {
    const r = e.getBoundingClientRect();
    return {l: r.left - Math.max(hostBox.left, 0),
            r: Math.min(hostBox.right, vw) - r.right,
            t: e.textContent.trim().slice(0, 10)};
  });
  const minL = gaps.length ? Math.min(...gaps.map(g => g.l)) : null;
  const minR = gaps.length ? Math.min(...gaps.map(g => g.r)) : null;
  const tight = gaps.filter(g => g.l < 16 || g.r < 16);
  add('reading-gutter', tight.length === 0,
      prose.length ? `最小左${Math.round(minL)} 右${Math.round(minR)}｜`
                     + tight.slice(0, 2).map(g => `「${g.t}」`).join('')
                   : '页面上没有文本块（纯地图/纯画布），这条不适用',
      '正文左右离版心边 >=16px（padding 简写会把 padding-inline 清零，要看实测不看声明）');

  /* 11 常驻底栏必须真的在底 —— 按几何认，不按类名认。
        已知失败条件：底部 Tab 用 `position:sticky;bottom:0`，而滚动容器又留了
        `padding-bottom:76px` 给它，于是它被顶高 76px 卡在半空，下面还露出内容。
        sticky 是**在流里**的，padding 会把它推上去；absolute/fixed 才脱离流。
        这道门不能只找 `.dock`，产物叫 `.tab-bar` —— 于是它什么也没查到。 */
  const bars = BOTTOM_BARS;      // 同一个检测器，别写第二份
  const floating = bars.filter(e => Math.abs(vh - e.getBoundingClientRect().bottom) > 2)
    .map(e => `${(e.className || e.tagName).toString().slice(0, 16)} `
            + `离底 ${Math.round(vh - e.getBoundingClientRect().bottom)}px`);
  // 没有常驻底栏是正当的（官网就没有），所以**不传 subject**：有就查，没有跳过。
  add('dock-at-bottom', floating.length === 0, floating.slice(0, 2).join('｜'),
      '常驻底栏的下边缘 = 视口底（sticky 会被容器 padding 顶高，用 absolute/fixed）');

  /* ── 多屏 H5 ────────────────────────────────────────────── */
  if (profile === 'h5') {
    const scr = [...document.querySelectorAll('.screen,[data-screen]')];
    const n = scr.length;
    /* 一屏 = 一个视口高 —— 旧包实测分屏高度从 330 到 895 不等，就是被压窄的桌面页 */
    const hs = scr.map(s => Math.round(s.getBoundingClientRect().height));
    add('screen-height', hs.every(x => Math.abs(x - vh) <= 2),
        hs.join(','), `每屏 = ${vh}±2`, n);
    /* 正文不被底部固定条压住 */
    const dock = document.querySelector('.dock,[data-dock]');
    const dh = dock ? dock.getBoundingClientRect().height : 0;
    let under = 0;
    scr.forEach(s => s.querySelectorAll('h1,h2,p,.lead,.num,[data-body]').forEach(e => {
      const r = e.getBoundingClientRect();
      if (r.height > 0 && r.bottom > vh - dh + 6 && r.top < vh) under++;
    }));
    add('content-under-dock', under === 0, under + ' 个', '正文不被操作条遮住', n);
    /* 无空屏 */
    const thin = scr.map((s, i) => ({ i: i + 1, n: s.innerText.replace(/\s/g, '').length }))
                    .filter(o => o.n < 28);
    add('empty-screen', thin.length === 0, JSON.stringify(thin), '每屏正文 >=28 字', n);
    /* 每屏有视觉主角 —— 多选一。不写成"必须有巨数字"，那会判死词云屏与称号屏 */
    const noHero = scr.slice(1).map((s, i) => {
      const box = s.getBoundingClientRect();
      const f = [...s.querySelectorAll('*')].filter(e => e.textContent.trim())
        .map(e => parseFloat(getComputedStyle(e).fontSize));
      const maxFont = f.length ? Math.max(...f) : 0;
      let block = 0;
      s.querySelectorAll('img,video,canvas,svg,.card2026,[data-hero]').forEach(e => {
        const r = e.getBoundingClientRect();
        block = Math.max(block, (r.width * r.height) / (box.width * box.height));
      });
      [...s.querySelectorAll('*')].forEach(e => {
        if (getComputedStyle(e).backgroundImage === 'none') return;
        const r = e.getBoundingClientRect();
        const a = (r.width * r.height) / (box.width * box.height);
        if (a < .96) block = Math.max(block, a);
      });
      return { p: i + 2, maxFont, block: Math.round(block * 100) };
    }).filter(o => o.maxFont < 30 && o.block < 20);
    add('no-visual-lead', noHero.length === 0, JSON.stringify(noHero),
        '每屏有主角：>=30px 巨字 或 >=20% 屏面积的画面/卡片', n);
  }

  /* ── 移动端交互合同（REPORT）────────────────────────────
     来源是用户逐条点名的 QQ 年报交互优点：
       「顶部用数字页码 + 分段进度条双重表达进度」
       「底部把继续做成最强、最顺手的拇指操作」
       「到了末页，文案自动变成再看一遍，控件会响应当前状态」
       「分享跳转还会出现 Toast 解释发生了什么」
     并问：这些能不能也长到别的产品上。能 —— 这五条讲的都是
     「控件和内容怎么响应状态」，与题材无关。完整九条见 craft/interaction-contract.md。

     **按几何与行为认，不按类名认。** dock-at-bottom 已经证实按类名会漏：
     产物把 .dock 改名叫 .tab-bar，门就查不到了。
     这里读的是产物自己的脚本文本 —— 那不是"声明"，那就是行为本身。 */
  if (profile === 'h5' || profile === 'app-screen') {
    const code = [...document.scripts].map(s => s.textContent || '').join('\n')
               + '\n' + document.documentElement.outerHTML;
    const miss = [];

    /* 1 位置/进度要有表达 —— **形式不指定**。
       用户明确提醒过：不能把 QQ 年报的机箱抄到每个产品上，
       「有些 app 没有 qq 年终报告顶部和底部的这些按钮」。他是对的。
       所以这里量的是"他知不知道自己在哪"，不是"有没有分段进度条"：
         年报 H5   → 页码 + 分段进度条
         产品首页  → 底部 tab 的选中态 / 分段控件 / 轮播圆点 / 已读态
         表单流程  → 步骤条
       任何**一组同级元素里有一个带选中态**都算，不限高度、不限类名。
       只有一屏 / 一个状态时整条跳过 —— 那时没有"位置"这回事。 */
    const units = document.querySelectorAll(
      '.screen,[data-screen],[role=tab],[data-tab],[data-view],[data-panel]').length;
    const ACTIVE = /(^|[\s_-])(on|active|current|selected|checked|is-[a-z]+)([\s_-]|$)/;
    const hasActive = [...document.querySelectorAll('*')].some(e => {
      const kids = [...e.children];
      if (kids.length < 2) return false;
      return kids.some(k => ACTIVE.test(k.className || '')
                         || k.getAttribute('aria-current')
                         || k.getAttribute('aria-selected') === 'true'
                         || k.getAttribute('data-active') != null);
    });
    const hasPager = [...document.querySelectorAll('*')].some(
      e => e.children.length <= 3
           && /^\s*\d{1,2}\s*\/\s*\d{1,2}\s*$/.test((e.textContent || '')));
    if (units > 1 && !hasActive && !hasPager) miss.push('位置表达（选中态/页码/步骤）');

    /* 2 主操作在拇指区 —— 同样**不指定形式**。
       不是"必须有一个占满宽度的继续按钮"。信息流 App 的主操作就是内容本身，
       底部 tab 就是它的拇指区控件。两种都算：
         a 存在贴底的固定/粘性条，且条里有可点元素
         b 最大的那个可点元素落在下半屏
       两条都不成立 = 所有可点的东西都堆在屏幕上半部分，拇指够不着。 */
    const clickable = [...document.querySelectorAll(
      'button,a[href],[role=button],[role=tab],[onclick],input,select')]
      .filter(e => { const r = e.getBoundingClientRect();
                     return r.width > 24 && r.height > 24; });
    const areaOf = e => { const r = e.getBoundingClientRect();
                          return r.width * r.height; };
    const bottomBar = [...document.querySelectorAll('*')].some(e => {
      const s = getComputedStyle(e);
      if (s.position !== 'fixed' && s.position !== 'sticky') return false;
      const r = e.getBoundingClientRect();
      return r.bottom > vh - 8 && r.height > 32
             && e.querySelector('button,a[href],[role=button],[role=tab]');
    });
    const biggest = clickable.slice().sort((a, b) => areaOf(b) - areaOf(a))[0];
    const lowest = biggest && biggest.getBoundingClientRect().bottom > vh * 0.6;
    if (!bottomBar && !lowest) miss.push('主操作在拇指区');

    // 3 控件文案响应状态：脚本里有对按钮文字的赋值
    if (!/(textContent|innerHTML|innerText)\s*=/.test(code)) miss.push('控件响应状态');

    /* 4 一个意图多条通路 —— **只在"有得翻"的时候要求**。
       实测：叫车页只有一个地图和一个面板，键盘翻页在它身上没有意义；
       要求每个产品都支持四路翻页，就是把年报的机箱抄过去。
       所以只有页面存在多个可导航单元（多屏 / 多 tab / 多面板）时才查。 */
    if (units > 1) {
      const paths = ['click', 'keydown|keyup', 'scroll|IntersectionObserver',
                     'touchstart|touchend|pointerdown']
        .filter(p => new RegExp(p).test(code)).length;
      if (paths < 2) miss.push('多通路（现在只有 ' + paths + ' 条）');
    }

    /* 5 副作用有解释 —— **不指定必须是 toast**。
       收藏按钮点完变成实心红心，那颗心就是解释；
       「预订」变成「已预订」，那句话就是解释。
       toast 只是其中一种形式，而且只有在"效果不在原地可见"时才必需
       （分享 / 复制 / 提交给远端）。所以三种都算：
         a toast / snackbar 一类的说明条
         b aria-live / role=status 这类无障碍播报
         c 点击后**改变自身文案或状态**的控件（原地就把话说了） */
    /* 而且**只在页面上真的有这类动作时才要求**。一个纯浏览的排行榜页
       点来点去都是换列表，效果全在眼前，不需要额外解释一句。 */
    const SIDE = /分享|复制|保存|收藏|提交|删除|发送|下单|支付|预订|预约|加入|订阅|举报|关注|申请/;
    const hasSideEffect = [...document.querySelectorAll(
      'button,a[href],[role=button],input[type=submit]')]
      .some(e => SIDE.test((e.textContent || '') + (e.getAttribute('aria-label') || '')));
    const explains = /toast|Toast|snackbar|提示条|已复制|已保存|已分享/.test(code)
      || /aria-live|role=["']?status|role=["']?alert/.test(code)
      || /(this|e\.target)\s*\.\s*(textContent|innerHTML|innerText)\s*=/.test(code)
      || document.querySelector('[aria-live],[role=status],[role=alert]') !== null;
    if (hasSideEffect && !explains)
      miss.push('分享/收藏/提交这类动作没有任何反馈（toast / aria-live / 控件自身变化，三选一）');

    add('interaction-contract', miss.length === 0, miss.join('｜'),
        '五件：位置表达 / 主操作在拇指区 / 控件响应状态 / 多通路 / 副作用反馈'
        + '（**只查有没有，不指定长什么样** —— 不要把年报的机箱抄到产品界面上）'
        + ' —— 见 craft/interaction-contract.md');
  }

  /* ── App / 小程序 单屏稿：第四种 HTML ─────────────────────
     这个 profile 是 低分参照样本 逼出来的。它的关键屏是 screens/screenN.html 这种
     单屏独立文件，类名 .phone-frame / .app-screen，h5 profile 的
     `.screen,[data-screen]` 一个都不匹配 —— 四道门于是静默跳过，
     而 every() 对空数组返回 true，**空真空通过**。
     所以这里不要求 scroll-snap，只查单屏该有的东西。 */
  if (profile === 'app-screen') {
    /* 删掉了这里的 `screen-fit`：它的 frame 兜底到 `body`，
       而这一家骨架都写 `html,body{height:100%}` —— **判据恒真**。
       一条永远不会 FAIL 的门不是保险，是噪音（它还占着一行输出，
       而输出长度本身就是到达率机制）。 */

    /* 固定底栏 / 悬浮 CTA。高度上限 35% 视口是必需的：桌面取景框那层
       `.stage{position:fixed;inset:0}` 满足"固定 + 够宽 + 贴底"三条，
       会被当成底栏，然后 safe-area 报它没留安全区。
       **底栏是一条，不是一整屏。** */
    const fixed = [...document.querySelectorAll('*')].filter(e => {
      const s = getComputedStyle(e);
      if (s.position !== 'fixed' && s.position !== 'sticky') return false;
      if (!painted(e)) return false;
      const r = e.getBoundingClientRect();
      return r.height > 20 && r.height <= vh * .35
             && r.width > vw * .5 && r.bottom > vh * .6;
    });
    /* 底栏必须被"预留位置"，否则滚到底也压着 —— 低分参照样本 的真实缺陷。
       这条是几何的，和底栏用什么定位、叫什么类名都无关。 */
    add('dock-reserved', reserved,
        barH ? `底栏高 ${Math.round(barH)}px，滚动容器 padding-bottom `
               + (reserved ? '够' : '不够')
             : '没有贴底细条（上浮面板 / 无底栏都不适用）',
        '有常驻底栏且下面有可滚动内容时，容器要给它留出 >=底栏高度的 padding-bottom，'
        + '否则滚到底内容还压在它下面');

    /* 删掉了这里的 `content-under-dock`（**只删 app-screen 这一支**，
       h5 分屏版保留）。三条理由，每条都在本机复现过：

         a 它把 `transform:translateY(100%)`、完全移出屏幕的 bottom-sheet
           当成常驻底栏 —— 实测 `publish-modal` 的 rect 是 844–1124，
           而视口只有 844 高。
         b 它不看 `reserved`，而同一段代码算出的 `reserved` 只给
           `dock-reserved` 用 —— 于是 `dock-reserved PASS` 与
           `content-under-dock BLOCK` **在同一份产物上同时出现**。
           两道门对同一份几何给出相反结论，等于没有门。
         c 它只在 `absolute` 骨架上验过（参照案例与骨架的底栏都在 `#app`
           取景框里），目标集合恒空 → 恒 PASS。真机上产物一旦用 `fixed`
           就开始命中，而它命中的**不是缺陷**。

       包自己在 element-overlap 的注释里早写对了道理：
       「内容从底栏下面滚过去是每个 App 都这样，不是缺陷；缺陷是**滚到底也压着**。」
       ——"滚到底也压着"由 `dock-reserved` 管，它在。
       真实代价：一条真实 trace 在这道门上死磕 15 分 14 秒 / 约 52 次调用。 */

    /* 安全区：底部固定条要给 safe-area 留位，顶部内容不能顶到状态栏 */
    const safeBad = fixed.filter(d => {
      const pb = getComputedStyle(d).paddingBottom;
      return parseFloat(pb) < 12;
    }).length;
    add('safe-area', safeBad === 0, safeBad + ' 个固定条没留安全区',
        '固定底栏 padding-bottom >= env(safe-area-inset-bottom) + 12px');

    /* ── 交的是产品，不是关于产品的幻灯片 ──────────────── BLOCK
       典型失败：移动端交的是设计方案的说明页，而不是真实产品界面。
       这算严重 bug 了！」

       实测：query 是「咖啡点单小程序首页改版」，
       交出去的网页卡是 5 屏 deck，第 3 屏标题 `03 / FULL VIEW · 完整首页 ·
       改版后全貌`，屏中央贴着一张 400px 宽的首页缩略图。
       用户想点的是咖啡点单首页，拿到的是一份关于它的幻灯片。

       口径是**正向**的，不是"不许出现封面屏"那种否定式窄枚举
       （换个说法就绕过去了）。三条正向判据，都量产物：
         A 首屏有真实的产品操作面（>=3 个可点元素在第一屏里）
         B 首屏文案讲的是产品，不是关于产品的元叙述
         C 至少 2 个真实的界面状态切换 —— 这一条由 Python 侧真的去点，见下面
       C 是主判据；A/B 是它的两个前置条件。 */
    const firstView = [...document.querySelectorAll(
      'button,a[href],input,select,textarea,[role=button],[role=tab],'
      + '[data-tab],[data-target],[onclick],label')]
      .filter(e => {
        const r = e.getBoundingClientRect();
        return r.width >= 20 && r.height >= 20 && r.top < vh && r.bottom > 0;
      });
    add('prototype-controls', firstView.length >= 3, firstView.length + ' 个',
        '首屏 >=3 个可操作元素 —— 首屏是产品首页本身，不是封面页');

    /* 元叙述词：这些词属于 doc，不属于原型。查的是**首屏可见文字**，
       不是整页 —— 产品里出现"方案"两个字未必是错（比如"套餐方案"），
       但首屏标题里出现「改版后全貌」「设计总结」就一定是幻灯片。 */
    const META = new RegExp('设计方案|方案总结|设计总结|改版前|改版后|全貌'
      + '|完整首页|关键屏|视觉语言|设计主张|封面页|结束页|本方案|以上为|设计说明');
    const metaHits = [];
    document.querySelectorAll('h1,h2,h3,h4,.kicker,[data-kicker],.title')
      .forEach(e => {
        const r = e.getBoundingClientRect();
        if (r.top >= vh || r.bottom <= 0) return;
        const t = (e.textContent || '').replace(/\s/g, '');
        if (META.test(t)) metaHits.push(t.slice(0, 20));
      });
    add('prototype-voice', metaHits.length === 0, metaHits.slice(0, 3).join('｜'),
        '首屏标题里 0 处元叙述词（方案/全貌/总结/封面/结束）—— 那些属于 doc');
  }

  /* ── 文档画布的排版正向判据（REPORT）──────────────────────
     治 F5：低分参照样本 的关键屏区退化成 5 行完全相同的「左手机 + 右三段清单」。
     这不是"能不能读"的问题，是"平庸 vs 优秀"的问题，所以全部 REPORT。 */
  if (profile === 'doc') {
    const secs = [...document.querySelectorAll('.sec,section')];
    // 版式重复度：相邻 3 节的 DOM 结构指纹相同 = 退化成模板了
    const fp = secs.map(s => [...s.querySelectorAll('*')]
      .slice(0, 40).map(e => e.tagName).join('>'));
    let rep = 0;
    for (let i = 2; i < fp.length; i++)
      if (fp[i] && fp[i] === fp[i-1] && fp[i] === fp[i-2]) rep++;
    add('doc-layout-repeat', rep === 0, rep + ' 处相邻三节同构',
        '相邻 3 节结构指纹不得全同（同构 = 退化成模板）', secs.length);

    /* ── 手机怎么放进文档 ──────────────────────────────
       要求：文档里放移动端页面时要好看，
       而且图片有点模糊，需要高清一点。」并给了三张参考图。
       实测那三张：手机机身宽度占容器 **15%–26%**，两侧各留 30%+ 的场，
       场是有内容的（渐变／装饰物／满版美术），机身有圆角边框与投影
       —— 它看起来是"一台手机"，不是"一张竖图"。

       而我们的实测：一张 600×2464 的手机长图装在通栏 .plate 里，
       在 795px 版心下被拉满整栏。**"模糊"和"不成比例"是同一件事的两面**：
       既然要铺满 795px，就得塞进 512KB，就只能把像素宽砍到 400。
       把手机缩到 22%，它需要的像素只有原来的 1/14，糊的问题自己就没了。 */
    const bodyW = Math.max(0, ...[...document.querySelectorAll(
      'section,.sec,table,.quad,.claim,.plate,.screens,.gain')]
      .map(e => e.getBoundingClientRect().width));
    const measure = bodyW || vw;
    const tallImgs = imgs.filter(i => {
      const r = i.getBoundingClientRect();
      return r.width > 40 && i.naturalWidth > 0
             && i.naturalHeight / i.naturalWidth >= 1.4;   // 竖图（手机屏 ≈2.16）
    });
    const oversize = tallImgs.filter(
      i => i.getBoundingClientRect().width > measure * 0.40)
      .map(i => `${(i.currentSrc || i.src).split('/').pop().slice(0, 14)} `
              + `占版心 ${Math.round(100 * i.getBoundingClientRect().width / measure)}%`);
    /* 通栏铺开的手机截图 = 「一张竖图」；要的是「一台手机站在一块场里」。
       FIX 给的是可直接照做的一步，不是让人再去想怎么改。 */
    add('device-scale', oversize.length === 0, oversize.slice(0, 3).join('｜')
        + (oversize.length ? '　FIX: 把这些 <figure> 包进 '
           + '<div class="ui-stage ui-stage-row" style="--phone:22%">…</div>'
           + '（`ui.py ship` 生成的 doc/screens/screens-figures.html 就是这个形态，'
           + '自带样式，整段替换即可）' : ''),
        '竖图（手机屏）在画布里渲染宽 <=版心 40% —— 手机要有机身和场，'
        + '参考图实测机身占 15–26%',
        tallImgs.length || 1);

    /* 长图不该整张进文档：像素总量 = 宽 × 高，要塞进 512KB 高度砍不得，
       被牺牲的一定是宽度。高宽比越大，宽度被牺牲得越狠。
       实测最极端的一张 152×800 —— 宽度只剩 152px。 */
    const longImgs = imgs.filter(i => i.naturalWidth > 0
      && i.naturalHeight / i.naturalWidth > 2.5
      && i.getBoundingClientRect().width > 40)
      .map(i => `${(i.currentSrc || i.src).split('/').pop().slice(0, 14)} `
              + `${i.naturalWidth}×${i.naturalHeight}`
              + `（${(i.naturalHeight / i.naturalWidth).toFixed(1)}:1）`);
    add('doc-image-aspect', longImgs.length === 0, longImgs.slice(0, 3).join('｜'),
        '内嵌图高宽比 <=2.5 —— 整页长图切段（pack_img.py 会自动切）'
        + '或改用元素级截图 pg.locator(".band").screenshot()',
        imgs.length || 1);

    /* ── 关键界面的槽位空着 ──────────────────────────────
       典型失败：doc 里的界面图全部丢失。
       典型失败：关键屏都截了（p01–p10 各 932KB 躺在 shots/ 里），
       **进 doc 的是 0 张** —— 一份把 .screens 和 .device-showcase 两个容器
       建得整整齐齐却全空着，另一份在 500KB 压力下把截图丢了、留下素材照片。
       两份的所有门都是绿的，因为**没有一道门冲这一节去**。
       产能在 `pack_img.py --for-doc-screens`：一条命令出图 + 内嵌 + 排版。 */
    const SLOT_SEL = '.screens,.device,.device-row,.device-showcase,'
                   + '.ui-stage,.ui-plate,[data-screens]';
    const slots = [...document.querySelectorAll(SLOT_SEL)];
    const empty = slots.filter(s => s.querySelectorAll('img,video,canvas').length === 0)
      .map(s => (s.className || s.tagName).toString().slice(0, 20));
    /* 「类名写了但没有对应 CSS 规则」由 grid-declared-vs-actual 量（看计算样式，
       不看源码文本）。这里不再拿正则去扫源码：`\bdevice\b` 会命中 `device-cap`，
       把正当版式判成缺陷 —— 判据要落在渲染结果上，不落在类名长什么样。 */
    add('doc-screens-empty', empty.length === 0, empty.slice(0, 3).join('｜'),
        '关键界面的图位里要有图 —— 空槽位说明成品页的截图没进来。'
        + ' `ui.py ship` 的第①段会自动把真机截图写进 KEY-SCREENS 标记块，'
        + '写进去的片段自带样式；报这一条说明标记块与图位容器都不在了。',
        slots.length || 1);
    // 图文比这道门**没有通过标定，已经删掉**，理由见文件末尾的标定记录：
    // 三份都被认可的 gold 实测跨度 0.17 → 3.45，而它们都是好稿。
    // 一个把好稿判成两头都错的指标，量的不是质量，是版面类型。

    /* ── 版面工艺：所有门都是绿的，用户一眼说"乱" ───────────────
       手工把三份 doc 从"乱"改到"好多了"的过程里，13 个错有 9 个是
       **技术上全对、看起来就是不对**。下面这几条就是那 9 个里能量出来的部分。
       它们量的不是"能不能读"，是"整不整齐"——而整齐恰恰是能被量出来的那部分上限。 */

    // G1 孤儿行：列数必须整除项数。版面显得"乱"，多半就是这个。 —— BLOCK
    // 根因：repeat(auto-fit,minmax(…)) 的列数随宽度浮动，而飞书块宽在 560–1145 之间跳，
    // 任何一个 min-width 取值都会在某个宽度上产生非整除列数（四宫格 3+1、六屏 5+1）。
    // 修法是让**项数**决定列数：repeat(var(--cols),minmax(0,1fr))。
    //
    // 只查"等宽轨"的网格。`auto 1fr` 这种（章节头、左标签右正文）是刻意的不等分，
    // 拿整除去要求它会把正当版式判成缺陷。
    /* 类名/内联变量声明了自己是网格，但**计算出来根本不是 grid** ——
       说明这条类名在这份画布里没有对应的 CSS 规则，它只是个裸 div。
       后果是所有子项按块级流通栏竖排，而下面那两条门的目标集合为空、
       一路绿灯。目标集合为空必须 FAIL，这是门的立场第 2 条。 */
    const GRID_CLASS = /\b(screens|quad|gain|duo)\b/;
    const declaredNotGrid = [...document.querySelectorAll('[class],[style]')]
      .filter(g => {
        const cn = (g.className || '').toString();
        if (!GRID_CLASS.test(cn) && !/--cols\s*:/.test(g.getAttribute('style') || ''))
          return false;
        return !getComputedStyle(g).display.includes('grid')
               && [...g.children].length >= 2;
      })
      .map(g => (g.className || g.tagName).toString().slice(0, 20));

    const grids = [];
    document.querySelectorAll('*').forEach(g => {
      const s = getComputedStyle(g);
      if (!s.display.includes('grid')) return;
      const tracks = s.gridTemplateColumns.split(' ').map(parseFloat).filter(x => x > 0);
      const declared = parseInt(s.getPropertyValue('--cols')) || null;
      // 声明了 --cols 的一律收进来，**哪怕它现在只有一条轨**——
      // 那正是要抓的那个场景：声明被非法值静默丢弃，网格塌成一列，没有任何报错。
      if (!declared) {
        if (tracks.length < 2) return;
        if (Math.max(...tracks) - Math.min(...tracks) > 2) return; // 不等分轨：跳过
      }
      const kids = [...g.children].filter(c => {
        const r = c.getBoundingClientRect();
        return r.width > 4 && r.height > 4 && painted(c);
      });
      if (kids.length < 3) return;
      grids.push({ who: (g.className || g.tagName).toString().slice(0, 20),
                   n: kids.length, cols: Math.max(1, tracks.length), declared });
    });
    const orphan = grids.filter(g => g.n % g.cols !== 0);
    add('orphan-row', orphan.length === 0,
        orphan.map(g => `${g.who} ${g.n}项/${g.cols}列`).join(' '),
        '每个等分网格的列数整除项数（否则出现 3+1 / 5+1 孤儿行，整版立刻显乱）');

    // G2 声明的列数有没有真的生效 —— 专治"写了但没生效"这一整类
    const mismatch = grids.filter(g => g.declared && g.declared !== g.cols);
    add('grid-declared-vs-actual',
        mismatch.length === 0 && declaredNotGrid.length === 0,
        mismatch.map(g => `${g.who} 声明${g.declared} 实际${g.cols}`).join(' ')
        + (declaredNotGrid.length
           ? (mismatch.length ? '｜' : '')
             + declaredNotGrid.slice(0, 3).join('、')
             + ' 写了网格类名但计算出来不是 grid（这份画布里没有对应的 CSS 规则，'
             + '子项会通栏竖排）—— 用 `ui.py ship` 生成的自带样式片段整段替换'
           : ''),
        '声明的 --cols 与实际渲染列数一致，且网格类名要真的有对应规则');

    // 阅读边距（reading-gutter）已提升为**全 profile 通用**门，见上面第 10 条 ——
    // 实测证明官网也会犯同一个错（padding 简写清零 padding-inline）。这里只留左右均衡。

    // G4 左右不对称：右侧余量堆积
    // 实测：画布上限 980 而正文行宽 38em，1145px 宽时右边空了 311px，看着像没排版。
    const cvBox2 = (document.querySelector('.cv') || document.body).getBoundingClientRect();
    const bodyPs = [...document.querySelectorAll('.cv p,.cv h2,.cv li')]
      .filter(p => p.textContent.trim().length > 30 && painted(p));
    const gutL = bodyPs.length
      ? Math.min(...bodyPs.map(p => p.getBoundingClientRect().left - cvBox2.left)) : null;
    const gutR = bodyPs.length
      ? Math.min(...bodyPs.map(p => cvBox2.right - p.getBoundingClientRect().right)) : null;
    add('gutter-balance',
        gutL === null || Math.abs(gutL - gutR) <= Math.max(gutL, 40) * 1.6,
        `左${Math.round(gutL)} 右${Math.round(gutR)}`,
        '画布上限与正文行宽要匹配，右侧余量不该单独堆积', bodyPs.length);

    // G5 示例字折行：字阶/色板示例断成两行会让人以为坏了
    // 用高度判，不用 getClientRects().length 判：示例字通常是 flex 项，
    // 而 flex 项是块级盒，折了行 rects 仍然是 1 —— 已知失败条件：折成两行照样报绿。
    const samples = [...document.querySelectorAll('.ts b,.sw span,.rd span,[data-sample]')]
      .filter(painted);
    const wrapped = samples.filter(e => {
      const s = getComputedStyle(e);
      const lh = parseFloat(s.lineHeight) || parseFloat(s.fontSize) * 1.4;
      return e.getBoundingClientRect().height > lh * 1.6;
    }).map(e => e.textContent.trim().slice(0, 10));
    add('sample-wrap', wrapped.length === 0, wrapped.slice(0, 3).join(','),
        '字阶/色板示例不许折行（加 white-space:nowrap）');

    // 阅读轴：**一条**主轴，行宽 45–75 中文字符。
    // 只量主轴上的段落（宽度 >= 半个版心）。三栏效益块里每格 16 个中文字一行
    // 是正当版式，不是"行太窄"—— 拿主轴的尺子去量分栏格子，量错了对象。
    const cw = document.body.getBoundingClientRect().width || vw;
    const ps = [...document.querySelectorAll('p')].filter(p =>
      p.textContent.trim().length > 40 && p.getBoundingClientRect().width >= cw * .5);
    const bad = ps.filter(p => {
      const w = p.getBoundingClientRect().width;
      const fs = parseFloat(getComputedStyle(p).fontSize) || 15;
      const cpl = w / fs;                       // 中文一个字约等于一个 font-size
      return cpl < 20 || cpl > 46;
    }).length;
    add('doc-reading-axis', bad === 0, bad + ' 段行宽越界',
        '主轴正文行宽 20–46 个中文字（换算 45–75 西文字符）', ps.length);
  }

  /* ── 文档人格：13 个解析后的视觉角色 ────────────────────────
     典型失败：两份不同项目的 doc 画布看起来是同一套模板。
     而当时的判据（视觉层 CSS 的 Jaccard）报的是 PASS 0.472。
     判据错在量**声明文本**：两份都写 `color:var(--ink)`，字面一样，
     变量背后的值却不同——它既看不见相同，也看不见不同。

     改成量**解析后的值**之后，真相是：两份稿颜色其实不一样（13 个角色里只有 1 个同），
     它们像，是因为**刻度和构成一样**——15px 正文、26.7px 行高、30px 等宽编号、
     26px 标题、2px 墨线、同一串组件。而这些全部来自骨架的出厂值。
     实测：案例 × 骨架 = 10/13 相同，gold PULSE × 骨架 = 9/13。
     **骨架才是那个共同祖先。**

     阈值取自三份 gold 两两之间的最大值 5：PULSE×QQ 5、PULSE×骑不骑 0、QQ×骑不骑 1。
     所以 >5 判为"和某份 gold 是同一套模板"。 */
  if (profile === 'doc' && cfg.personas) {
    const cvp = document.querySelector('.cv') || document.body;
    const cp = getComputedStyle(cvp);
    const qq = (sel, prop, d) => { const e = document.querySelector(sel);
      return e ? getComputedStyle(e)[prop] : (d || '-'); };
    const fam = f => (f || '').split(',')[0].replace(/["']/g, '').trim();
    const mine = {paper: cp.backgroundColor, ink: cp.color,
      muted: qq('.sub,.body,figcaption,small', 'color', qq('p', 'color')),
      rule: qq('.sec-top', 'borderTopWidth') + ' ' + qq('.sec-top', 'borderTopStyle'),
      font: fam(cp.fontFamily),
      radius: qq('.plate img', 'borderRadius', qq('img', 'borderRadius', '0px')),
      accent: qq('.sn', 'color'), bodySize: cp.fontSize, lineH: cp.lineHeight,
      h2Size: qq('.sec-top h2', 'fontSize'), numSize: qq('.sn', 'fontSize'),
      numFont: fam(qq('.sn', 'fontFamily')), secGap: qq('.sec', 'paddingTop')};
    let worstName = null, worstSame = [];
    for (const [name, fp] of Object.entries(cfg.personas)) {
      const same = Object.keys(mine).filter(k => mine[k] === fp[k]);
      if (same.length > worstSame.length) { worstSame = same; worstName = name; }
    }
    add('doc-persona-clone', worstSame.length <= 5,
        `与 gold/${worstName} 有 ${worstSame.length}/13 个视觉角色相同：${worstSame.join(',')}`,
        '与任何一份 gold 相同的视觉角色 <=5（三份 gold 两两之间实测最多 5）');
  }

  /* ── 审美正向判据（全部 REPORT，永不阻断交付）────────────────
     为什么是 REPORT：这些是"平庸 vs 优秀"的判据，不是"能不能读"的判据。
     设成 BLOCK 会判死正当的克制型设计（获奖站 lunge 首屏只有 14 段文字）。
     但必须打印出来，让你在改稿时看见自己离得奖级差在哪。

     **每一条都拿参照案例验过不会判死好稿，实测数字写在后面。**
     初版提的六条里有三条没通过标定，已经删掉，理由见文件末尾的注释 ——
     不要在没有新证据的情况下把它们加回来。 */
  if (wantAesthetic) {
    // 真实视觉资产：img/video/canvas + 渲染面积 >=3% 的 svg/CSS 画面
    // 这里用 self（只看元素自己）而不是 painted()（看整条祖先链）：
    // 进屏才显形的 reveal 包装层 opacity 是 0，但那张图**确实在页面上**。
    // 实测差别：gold/web-pulse 用 painted() 只数到 5 个，用 self 数到 17 个。
    const self = e => { const s = getComputedStyle(e);
      return s.display !== 'none' && s.visibility !== 'hidden'; };
    const assets = [];
    document.querySelectorAll('img,video,canvas').forEach(m => {
      const r = m.getBoundingClientRect();
      if (r.width >= 24 && r.height >= 24 && self(m)) assets.push('media');
    });
    /* 小圆头像、列表缩略图这类**重复的小画面**也是真实视觉资产。
       实测：参考库里的排行榜页每行一个 38px 头像、共 12 个，
       而 svg/cssart 的 3% 面积门槛（≈100×100）把它们全筛掉了，
       于是一个内容扎实的产品界面被判成"页面上没有画面"。
       面积门槛是给"整块渐变底"设的，不该用来筛内容缩略图。 */
    document.querySelectorAll('[class*=avatar],[class*=thumb],[class*=av],li,'
      + '[class*=item],[class*=card]').forEach(m => {
      if (!self(m)) return;
      const r = m.getBoundingClientRect();
      if (r.width < 24 || r.height < 24 || r.width > vw * .9) return;
      const s = getComputedStyle(m);
      if (s.backgroundImage !== 'none') assets.push('thumb');
    });
    /* 面积门槛的**分母是一屏，不是整张画布**。
       原来用 VA（vw × vh），而 vh 对长图是 4200、对大屏是 2251 ——
       同一个 111×111 的手绘礼品图，在 390×844 的 H5 里算 3.9%（计入），
       在 750×4200 的长图里算 0.4%（被筛掉）。**载体越长，画面越不算数**，
       这显然是分母选错了：这条门问的是"它在一屏里占多大"，
       不是"它在整卷长图里占多大"。 */
    const SA = vw * Math.min(vh, 1000);
    document.querySelectorAll('svg').forEach(m => {
      if (area(m.getBoundingClientRect()) / SA >= .03 && self(m)) assets.push('svg');
    });
    document.querySelectorAll('*').forEach(m => {
      const s = getComputedStyle(m);
      if (s.backgroundImage === 'none') return;
      const f = area(m.getBoundingClientRect()) / SA;
      if (f >= .03 && f <= 3 && self(m))
        assets.push(s.backgroundImage.includes('url(') ? 'bgimg' : 'cssart');
    });
    const nAsset = assets.length;
    const nCssArt = assets.filter(k => k === 'cssart').length;

    // A1 素材闭包：成品页必须有 >=8 个真实视觉资产。
    // 实测 gold web-pulse 17、gold h5 14、低分参照样本 首页 **2**（且全是 emoji 冒充）。
    // 采素材是 20 多次调用的苦活，不设闭包一定被跳过 —— publish.py 把它变成硬闭包。
    const floor = ASSET_FLOOR[profile] === undefined ? 8 : ASSET_FLOOR[profile];
    if (floor > 0)
      add('asset-count', nAsset >= floor, nAsset + ' 个 ' + JSON.stringify(
          assets.reduce((o,k)=>{o[k]=(o[k]||0)+1;return o;},{})),
          '>=' + floor + ' 个真实视觉资产（下限按载体分，见 ASSET_FLOOR 那段注释）');

    // A2 emoji 冒充图标。**单看 emoji 数量无效**（gold web-pulse 有 8 个，
    // 是跑马灯里的 ✦ 分隔符，不是图标冒充）。有判别力的是比值：
    // 实测 gold-web 0.47、gold-h5 0.07、低分参照样本 **5.0**。
    const emo = (document.body.innerText.match(/\p{Extended_Pictographic}/gu) || []).length;
    const maxFont = Math.max(16, ...[...document.querySelectorAll('h1,h2,h3,p,li,span,div')]
      .filter(e => [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim().length > 1))
      .filter(e => { const st = getComputedStyle(e);
        return st.display !== 'none' && st.visibility !== 'hidden'; })
      .map(e => parseFloat(getComputedStyle(e).fontSize) || 0));
    const per = Math.round(emo / Math.max(1, nAsset) * 100) / 100;
    add('aes-emoji-per-asset', per <= 1.0, per + `（${emo} emoji / ${nAsset} 资产）`,
        '<=1.0（gold 实测 0.47 / 0.07，低分参照样本 实测 5.0）');

    // A3 底色承诺。**底色明度单看无效**（gold-web 0.84 也是浅底，但它是好稿）。
    // 只有「浅底 **且** 首屏没画面」才是问题 —— 那才是白卡片阵列。
    const bl = lum(getComputedStyle(document.body).backgroundColor);
    const flat = bl !== null && bl > .6 && imgPct < 15;
    add('aes-flat-ground', !flat,
        `底色明度 ${bl === null ? '?' : Math.round(bl*100)/100}｜首屏影像 ${imgPct}%`,
        '浅底可以，但浅底 + 首屏影像 <15% = 白卡片阵列'
        + '（gold-web 0.84 浅底但影像 100%，是好稿；低分参照样本 0.91 浅底 + 影像 0%）');

    /* ── 实测 vs 获奖参考区间的对照 ────────────────────────────
       这一段**不判对错**，只把你的数和 12 份获奖稿的分布并排放。

       为什么不做成门：这两项都会判死参照案例里的好稿。
         · 字阶断崖：下沿 2.8 对官网和年报成立，对 App 界面不成立
           （真实 App 的标题就是 24–32px）。而"这稿是不是 App 界面"
           从 DOM 里判不出来 —— 判错了就会把一份正确的 App 稿判成缺陷。
         · 圆角：参考库中位 3px 而我们中位 50px，看着是条大偏差；
           但 gold/web-pulse 中位也是 50（它的规矩是"只有可点的才是圆的"，
           胶囊多所以中位高）。改量"圆角角色数"之后 gold 4/4/3、试跑 3/3 —— 不区分。

       **量不出好坏的东西就不要做成门。** 但把数摆出来是有用的：
       你至少知道自己掉没掉出所有获奖稿的范围。怎么办由你定。 */
    const cliff = Math.round(maxFont / (parseFloat(getComputedStyle(document.body).fontSize) || 16) * 10) / 10;
    const radii = [...document.querySelectorAll('*')].filter(e => {
      const r = e.getBoundingClientRect(); return r.width > 18 && r.height > 18;
    }).map(e => parseFloat(getComputedStyle(e).borderRadius) || 0).filter(x => x > 0).sort((a,b)=>a-b);
    const radMid = radii.length ? radii[Math.floor(radii.length / 2)] : 0;
    const radLevels = new Set(radii.map(x => Math.round(x))).size;
    out.push({code: 'ref-scale', ok: true, want: '对照 craft/scale-atlas.md，不是判对错',
      detail: `字阶断崖 ${cliff}（获奖库 p10 2.8 / 中位 3.6 / p90 6.9）`
            + `｜圆角中位 ${Math.round(radMid)}px（获奖库中位 3，12 份里 4 份纯直角）`
            + `｜正文 ${parseFloat(getComputedStyle(document.body).fontSize)}px（获奖库中位 16）`});

    /* ── M3 的原料：并排对照板量的那几个数 ────────────────────
       它**不判对错**，一条都不阻断。它回答的是另一个问题：
       「离好还差多远」。`--aesthetic` 原有的四条是**判定式**的
       （告诉你没犯错），而没犯错和好看是两件事。 */
    const sat = c => { const m = (c || '').match(/[\d.]+/g); if (!m) return -1;
      const [r, g, b] = m.slice(0, 3).map(Number).map(v => v / 255);
      const mx = Math.max(r, g, b), mn = Math.min(r, g, b), l = (mx + mn) / 2;
      if (mx === mn) return 0;
      return l > .5 ? (mx - mn) / (2 - mx - mn) : (mx - mn) / (mx + mn); };
    let satMax = 0;
    document.querySelectorAll('*').forEach(e => {
      const r = e.getBoundingClientRect();
      if (r.width * r.height < 400 || !self(e)) return;
      const s = getComputedStyle(e);
      [s.color, s.backgroundColor].forEach(c => {
        const v = sat(c); if (v > satMax) satMax = v; });
    });
    const nScreens = Math.max(1, document.querySelectorAll('.screen,[data-screen]').length);
    out.push({code: 'ref-board', ok: true, want: '并排对照板的原料',
      detail: JSON.stringify({cliff, radMid: Math.round(radMid), radLevels,
        accentSat: Math.round(satMax * 100) / 100, imgPct,
        assets: nAsset, perScreen: Math.round(nAsset / nScreens * 10) / 10,
        body: parseFloat(getComputedStyle(document.body).fontSize)})});

    // A4 `aes-no-real-imagery` 已在 删除 —— 新增一条 BLOCK/REPORT 必须同时删一条，
    // 而它和上面的 `asset-count` 量的是同一件事：三份形态样本上两条每次同时报，
    // 且对"内容即画面"的产品界面（排行榜 / 叫车 / 交易流水）系统性误报。
    // 删的是重复的那一条，不是有判别力的那一条。
  }
  return out;
}
"""


def canvas_gates(path: Path) -> list[dict]:
    """飞书 html5-block 画布的静态结构门。四条都是真事故换来的。"""
    t = path.read_text(encoding="utf-8", errors="ignore")
    res = []
    low = t.lstrip().lower()
    full = low.startswith("<!doctype html") and "<head" in low and "</html>" in low
    res.append({"code": "canvas-structure()", "ok": full,
                "detail": path.name, "want": "完整 HTML 文档（否则飞书按片段渲染）"})
    # 注释里出现结构标签字面量 → 消费方会从注释处截断，把 CSS 当正文印出来
    comments = re.findall(r"/\*.*?\*/", t, re.S) + re.findall(r"<!--.*?-->", t, re.S)
    hits = STRUCT_TAGS.findall("".join(comments))
    res.append({"code": "canvas-comment-tags", "ok": not hits,
                "detail": ",".join(hits[:3]), "want": "注释/样式里无结构标签字面量"})
    # 画布里的图必须是 data: URI —— 这是正向口径，不是禁用词枚举。
    # 已知失败条件：画布写 src="../h5/assets/hero-bg.jpg" 与 src="../shots/full-3.png"，
    # 飞书把相对路径**静默丢掉**，用户打开文档看到三个裂图占位符。
    # 规则不能写成 `if 'src="assets/' in t`（否定式窄枚举），
    # `../h5/assets/` 和 `../shots/` 两种写法都从它旁边溜了过去。
    srcs = re.findall(r'<img[^>]+src=["\']([^"\']{0,80})', t, re.I)
    # 空 src 是骨架的占位，不是裂图 —— 那由 placeholder 门管。
    # 不排掉的话每一份新拷的骨架都会报一次，而噪音会训练人忽略这条门。
    bad_src = [x[:40] for x in srcs if x.strip() and not x.startswith("data:")]
    res.append({"code": "canvas-img-embedded", "ok": not bad_src,
                "detail": f"{len(bad_src)} 处 {bad_src[:2]}",
                "want": "画布里每个 <img src> 都是 data: URI"
                        "（相对路径与外链在飞书里都会被静默丢弃 → 裂图）"})
    # 自己画的 SVG 示意图冒充证据 —— data: URI 门是绿的，用户看到的是两个空框。
    # 已知失败条件：02「我们看到的机会」的竞品对照，
    # 左边是一个浅蓝矩形加一个圆，右边是一个灰圆加一行「安静的材料感」，
    # 两张都是手写的 data:image/svg+xml —— 看起来就是两个空图位。
    # 判据只认 <img src="data:image/svg+xml">：真图标是 inline <svg>，不走 <img>，
    # 所以这条不会波及图标（六份画布 + 三份封面 0 命中）。
    fake = [x for x in srcs if x.startswith("data:image/svg+xml")]
    res.append({"code": "doc-fake-figure", "ok": not fake,
                "detail": f"{len(fake)} 张手画的 SVG 示意图",
                "want": "图位里放的是**证据**（竞品实拍截图 / 真机截图 / 素材照片），"
                        "不是自己画的示意图 —— 手画的方框在客户眼里就是没做完。"
                        "图标用 inline <svg>，不受这条限制"})
    size = len(t.encode())
    res.append({"code": "canvas-oversize", "ok": size <= LARK_HTML5_MAX_BYTES,
                "detail": f"{size // 1024}KB", "want": f"<= {LARK_HTML5_MAX_BYTES // 1024}KB"})
    # 模板转义残留 —— CSS 里的非法值**不报错，只是静默丢弃那一条声明**。
    # 已知失败条件：从做 % 格式化的文件抄 CSS 到不做格式化的文件，
    # `minmax(min(100%%,250px),1fr)` 原样输出 → 非法值 →
    # 整条 grid-template-columns 被丢弃 → 四宫格塌成一列，而且没有任何报错。
    # 先把注释剥掉再找 —— 否则这道门会把"警告不要写 %% 的那句注释"本身判成违规，
    # 于是门会禁止记录经验本身。断言要写行为，不写措辞。
    body_only = re.sub(r"/\*.*?\*/", " ", t, flags=re.S)
    body_only = re.sub(r"<!--.*?-->", " ", body_only, flags=re.S)
    esc = re.findall(r"%%|\{\{|\}\}", body_only)
    res.append({"code": "css-escape-leftover", "ok": not esc,
                "detail": f"{len(esc)} 处 {sorted(set(esc))}",
                "want": "画布里不得有 %% / {{ }} 残留（非法值会让整条声明被静默丢弃）"})
    # 断点在飞书里必崩：块宽在 560–1145 之间浮动
    bp = re.findall(r"@media[^{]*\(\s*(?:min|max)-width", t)
    res.append({"code": "canvas-breakpoint", "ok": len(bp) == 0,
                "detail": f"{len(bp)} 处 @media",
                "want": "窄栏画布用 min()/auto-fit，不用断点（飞书块宽 560–1145 浮动）"})
    return res


# ── doc 的口吻判据（REPORT）—— 治「把内部方法的严谨当成汇报的内容」 ──
# 内部严谨（拒绝清单、门、断言、边界）是我们怎么保证不做砸，是乙方的家务事；
# 汇报是让客户看懂并想采纳。客户不关心你不做什么，只关心你要做什么、凭什么、对他有什么用。
# 把这两条禁词表改窄了。过宽的禁词表会**禁掉评分表明确给分的东西**：
# 「素材与数据说明」「最终自检」「组件规范」「Design Token」四个标题全在禁词表里，
# 而「虚构数据未标注示例/来源」在两道题里是**一票否决**。
# 我们在门里禁止的，正是评分表里给分的。
# 现在只留"确实是工程记录"的那几个：内部断言、校验、状态枚举、实现细节。
# 「规范 / 原则 / 验收 / 边界 / token / 诚实性」全部移出 —— 它们在客户文档里
# 有正当写法（"组件规范""设计原则""素材与数据说明"）。
TECH_TITLE = re.compile(r"(断言|门槛|校验|收据|状态枚举|技术选型|实现细节|"
                        r"埋点方案|接口约定)", re.I)
BANNED_SECTION = re.compile(r"(明确拒绝|拒绝清单|不做的事|反模式清单)")
# 正向：这几节**该有**，缺了只提示不阻断。
# 前两条对应评测 rubric 里的两处一票否决：
# 「虚构数据当真实事实且无示例/来源/非实时标注」
# 「完整设计 Doc 缺节」
WANTED_SECTION = [
    ("素材与数据说明", r"素材|数据说明|示例数据|来源|非实时|待确认|仅为示例"),
    ("设计系统 / 组件规范", r"设计系统|组件|规范|token|色板|字阶"),
    ("最终自检 / 下一步", r"自检|下一步|后续|落地建议|交付清单"),
]
# 数值区（四宫格、附录）用 data-spec 标出来，这几条就会跳过它 ——
# 色板的十六进制值该在四宫格里被**看见**，不该在正文里被**读出来**。
TAGS = re.compile(r"<[^>]+>")
SPEC_OPEN = re.compile(r"<(\w+)([^>]*\bdata-spec\b[^>]*)>", re.I)


def strip_spec(html: str) -> str:
    """把带 data-spec 的元素整块删掉，按标签配对删，不能用非贪婪正则 ——
    `<div data-spec>…</div>` 里还有嵌套 div，非贪婪会停在第一个 </div> 上，
    结果只删掉一小截，四宫格里的数值照样被当成正文（这道门就白设了）。"""
    while True:
        m = SPEC_OPEN.search(html)
        if not m:
            return html
        tag, i, depth = m.group(1), m.end(), 1
        pat = re.compile(rf"</?{tag}\b", re.I)
        while depth and (n := pat.search(html, i)):
            depth += -1 if n.group(0).startswith("</") else 1
            i = html.find(">", n.end())
            if i < 0:
                return html[:m.start()]
            i += 1
        html = html[:m.start()] + " " + html[i:]


def doc_voice_gates(path: Path) -> list[dict]:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    body = re.sub(r"<(style|script)\b.*?</\1>", " ", raw, flags=re.I | re.S)
    body = strip_spec(body)
    titles = re.findall(r"<h[1-4][^>]*>(.*?)</h[1-4]>", body, re.I | re.S)
    titles = [TAGS.sub("", t).strip() for t in titles]
    text = TAGS.sub(" ", body)
    res = []

    tech = re.findall(r"\b\d+px\b|#[0-9a-fA-F]{6}\b|\.[a-z][\w-]*\s*\{", text)
    res.append({"code": "doc-voice-jargon", "ok": len(tech) == 0,
                "detail": f"{len(tech)} 处 {tech[:4]}",
                "want": "正文 0 处 px / hex / 选择器（四宫格与附录用 data-spec 标出即跳过）"})

    bad_t = [t for t in titles if TECH_TITLE.search(t)]
    res.append({"code": "doc-voice-title", "ok": not bad_t, "detail": ",".join(bad_t[:3]),
                "want": "章节标题 0 个技术词"})

    bad_s = BANNED_SECTION.findall(" ".join(titles))
    res.append({"code": "doc-voice-section", "ok": not bad_s, "detail": ",".join(bad_s[:3]),
                "want": "没有「拒绝清单」「验收与边界」这类整节（那是我们的方法，不是给客户看的）"})

    # 「讲为什么的段落占比」这道门**没有通过标定，已经删掉**：
    # 三份被认可的 gold 实测 0.17 / 0.12 / 0.15，而已知的反例（写成工程记录的
    # 那份 doc）实测 **0.2 —— 比 gold 还高**。
    # 因为它数的是"因为/所以/为什么"这些连接词，而好的汇报常常
    # 直接说"他在这里想干什么"，一个连接词都不用。**数措辞量不出讲不讲道理。**

    thesis = [TAGS.sub("", m).strip() for m in
              re.findall(r"<(?:strong|b)[^>]*>(.*?)</(?:strong|b)>", body, re.I | re.S)]
    thesis = [t for t in thesis if 8 <= len(t) <= 40]
    res.append({"code": "doc-voice-thesis", "ok": len(thesis) >= 1,
                "detail": (thesis[0] if thesis else "无"),
                "want": "至少 1 句 <=40 字的加粗设计主张（客户要能复述给他老板听）"})

    return res


def doc_whole_gates(paths: list[Path]) -> list[dict]:
    """**量整份 doc，不是量一块画布。**

    这三条是评分表里给分的东西（其中两条是一票否决）。它们必须量整份文档：
    gold 的 canvas-a 是上篇、canvas-b 是下篇，「下一步」天然只在下篇里。
    第一版按单块画布量，于是六份 gold 全部报警 ——
    **判据的对象错了，比没有判据更危险**（这个错包里犯过一次：
    闭包查的是「cover.html 这个文件在不在」，而用户看的是文档里有没有封面）。
    """
    whole = ""
    for p in paths:
        raw = p.read_text(encoding="utf-8", errors="ignore")
        body = re.sub(r"<(style|script)\b.*?</\1>", " ", raw, flags=re.I | re.S)
        whole += " " + TAGS.sub(" ", body)
    res = []
    for name, pat in WANTED_SECTION:
        res.append({"code": "doc-has-" + name.split()[0],
                    "ok": bool(re.search(pat, whole, re.I)),
                    "detail": "整份 doc 里都没找到", "want": f"有一节讲「{name}」"})
    # 虚构数据要标注。评测里的一票否决，而包里此前**方向是反的**：
    # 「数据诚实性」这个词曾经在禁词表里 —— 我们禁止的正是评分表要的。
    nums = re.findall(r"\d[\d,.]{2,}", whole)
    marked = re.search(r"示例|样例|非实时|模拟数据|数据来源|截至|统计口径|"
                       r"仅供参考|示意", whole)
    res.append({"code": "doc-data-honest", "ok": not (len(nums) >= 8 and not marked),
                "detail": f"{len(nums)} 处成组数字，0 处示例/来源/非实时标注",
                "want": "文档里出现成组数字时，标一句「示例数据 / 数据来源 / 截至…」"
                        "——虚构数据当真实事实是评分表里的一票否决"})
    return res


class _Serve:
    def __init__(self, directory: Path):
        with closing(socket.socket()) as s:
            s.bind(("127.0.0.1", 0))
            self.port = s.getsockname()[1]
        handler = type("H", (http.server.SimpleHTTPRequestHandler,),
                       {"__init__": lambda s, *a, **k:
                        http.server.SimpleHTTPRequestHandler.__init__(
                            s, *a, directory=str(directory), **k),
                        "log_message": lambda *a: None})
        self.httpd = socketserver.TCPServer(("127.0.0.1", self.port), handler)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self) -> None:
        try:
            self.httpd.shutdown()
        except Exception:
            pass


def resolve(target: str) -> tuple[str, _Serve | None]:
    """和 shoot.py 同一条规矩：传本地路径就自己托管，端口冲突不该是你的问题。"""
    if target.startswith(("http://", "https://")):
        return target, None
    p = Path(target).resolve()
    if p.is_dir():
        srv = _Serve(p)
        return f"http://127.0.0.1:{srv.port}/index.html", srv
    srv = _Serve(p.parent)
    return f"http://127.0.0.1:{srv.port}/{p.name}", srv


# 三份 gold 的文档人格指纹（实测值，`gold/doc-personas.json` 由 gold 现场量出）。
# 它们是"可以看不可以抄"的那条规则唯一可判定的形式。
try:
    PERSONAS = json.loads((Path(__file__).resolve().parent.parent
                           / "gold" / "doc-personas.json").read_text(encoding="utf-8"))
except Exception:
    PERSONAS = {}

# 图位说明的占位串。**唯一来源是 pack_img.py** —— 那里也是产出它们的地方。
# 抄一份到这里就会出现「改了文案、门还认旧的」，两份抄本必然分叉。
try:
    import pack_img as _pack
    SLOT_CAPTIONS = _pack.PLACEHOLDER_CAPTIONS
except Exception:
    SLOT_CAPTIONS = ()


# ── frame-intact：**纯几何**，一个类名都不查（P0-7）────────────
#
# 症状是「h5 没走移动端的模板」。物理成因是：
# 产物被并发会话清空 → 只能从宿主的"工作记忆压缩存档"重建 →
# 存档的「取景框设置」只抄了 CSS 变量的**色值**，
# **一条几何规则都没抄**（`.stage{position:fixed;inset:0}` 从来没进过任何一次存档）
# → 重建出的 v2 无 `.stage`、无 `#app`，状态栏/顶栏/底栏一律
# `position:fixed;left:0;right:0` → app_builder_agent 在桌面宽度渲染 →
# 状态栏与 Tab 栏横贯 1440px。
#
# 而全包对这件事**零处判据**：`check.py` 里 `.stage` 只出现在一句注释里，
# 移动端的取景又只有 390 一档 —— **门在 390 下量，产物在 1440 下被用户看。**
#
# 判据必须是几何，不能是类名清单：登录页、详情页、全屏沉浸式 H5
# 合法地没有 `.tabbar` / `.statusbar`。只问一件事：
# **在 1440 宽下，最外层内容盒有没有被约束在 520px 以内**——
# 用 `.stage`、`.phone`、还是裸 `max-width` 都行，不问实现。
# 量的是**画着东西的那一片有多宽**，不是某个盒子有多宽。
# 第一版量的是"最外层内容盒"，在 gold/app-home 上直接报 1440 ——
# 因为它的取景框 `.stage{position:fixed;inset:0}` 是个**居中层**：
# 盒子铺满视口，内容只在中间那 390px 里。**门 FAIL 掉 gold 就是门错。**
# 所以判据换成：把所有"真的写着字 / 真的贴着图"的元素取并集包围盒，
# 手机形态下它天然是一条窄栏，桌面形态下它天然铺开。包装层多厚都不影响。
FRAME_PROBE = """ () => {
  const vw = innerWidth, vh = innerHeight;
  const painted = e => { let q = e;
    while (q && q.nodeType === 1) { const s = getComputedStyle(q);
      if (s.display === 'none' || s.visibility === 'hidden') return false;
      if (parseFloat(s.opacity) < .06) return false;
      q = q.parentElement; }
    return true; };
  const marks = [];
  document.querySelectorAll('*').forEach(e => {
    const ownText = [...e.childNodes].some(
      n => n.nodeType === 3 && n.textContent.trim().length >= 2);
    const isMedia = /^(IMG|VIDEO|CANVAS|SVG)$/.test(e.tagName);
    if (!ownText && !isMedia) return;
    if (!painted(e)) return;
    const r = e.getBoundingClientRect();
    if (r.width < 8 || r.height < 8) return;
    if (r.bottom < 0 || r.top > vh * 4) return;          /* 屏外的不算 */
    marks.push(r);
  });
  if (!marks.length) return {width: vw, who: '（页面上没有可量的文字或图）', vw, n: 0};
  /* 取 p10(left) 与 p90(right)，**不取 min/max**。
     用极值会被一个元素带偏：gold/h5-qq2026 有一条刻意做成通栏的
     `.deskhint`（桌面上提示怎么翻页，它本来就在手机框外面），
     min/max 于是报 0–1440，而它其余 55 处内容全部落在 551–889。
     **一条门被一个正当元素判死一份 gold，就是门错。** */
  const lefts = marks.map(r => r.left).sort((a, b) => a - b);
  const rights = marks.map(r => r.right).sort((a, b) => a - b);
  const n = marks.length;
  const left = lefts[Math.floor(n * 0.1)];
  const right = rights[Math.max(0, Math.ceil(n * 0.9) - 1)];
  const outside = marks.filter(r => r.left < left - 1 || r.right > right + 1).length;
  return {width: Math.round(right - left),
          who: `${n} 处文字/图，主体横跨 ${Math.round(left)}–${Math.round(right)}`
               + (outside ? `（另有 ${outside} 处更宽，按通栏元素放过）` : ''),
          vw, n};
}"""


def probe_frame(url: str, w: int = 1440, h: int = 900) -> dict:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": w, "height": h})
        try:
            pg.goto(url, wait_until="load", timeout=30000)
            pg.wait_for_timeout(700)
            got = pg.evaluate(FRAME_PROBE)
        except Exception as e:
            got = {"width": 0, "who": f"({type(e).__name__})", "vw": w}
        b.close()
    ok = 0 < got["width"] <= 520
    return {"code": "frame-intact", "ok": ok,
            "detail": f"@{w}px 版心 {got['width']}px（{got['who']}）",
            "want": f"移动端产物在 {w} 宽下版心 <=520px（取景框/max-width/margin:auto "
                    f"都行，不问实现）—— 卡片就是在这个宽度下被打开的"}


FRAME_FIX = """  取景框最小可用形态（贴进 <body> 的第一层，把你的内容放进 #app）：

    <style>
      body{background:#111;display:grid;place-items:center;min-height:100vh}
      .stage{position:fixed;inset:0;display:grid;place-items:center}
      #app{position:relative;width:390px;height:844px;max-width:100vw;
           max-height:100dvh;overflow:hidden;border-radius:38px;background:#fff}
      /* 状态栏 / 顶栏 / 底栏一律 absolute，**不要 fixed** —— fixed 会脱出
         #app 贴到视口上，桌面宽度下就横贯 1440px。 */
      .statusbar,.topbar,.tabbar{position:absolute;left:0;right:0}
    </style>
    <div class="stage"><div id="app"> …你的界面… </div></div>"""


def probe(url: str, profile: str, w: int, h: int, aesthetic: bool,
          no_persona: bool = False) -> list[dict]:
    from playwright.sync_api import sync_playwright
    out: list[dict] = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": w, "height": h})
        errs: list[str] = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        # 三件事必须在量之前做完，缺一条就会量到一个不存在的页面：
        # 1 懒加载图要解码 —— 少等一秒，gold/web-pulse 的 17 个资产只数到 5 个
        # 2 入场动画要落终态 —— 和 shoot.py 用同一个 SETTLE_JS，不重复实现
        # 3 开机/引导层要自己走完 —— gold/h5 的 .boot 是 2.5 秒后才
        # 加 .off{opacity:0}。早量 0.3 秒，重叠门就会把开机日志和电视机
        # 底标报成"两块文字压在一起"，而那是它自己产物里的一个瞬间。
        from shoot import SETTLE_JS
        ready = (" () => Array.from(document.images)"
                 ".every(i => i.complete && i.naturalWidth > 0)")
        for fn in (lambda: pg.goto(url, wait_until="load", timeout=30000),
                   lambda: pg.wait_for_timeout(800),
                   lambda: pg.evaluate("() =>document.querySelectorAll('img[loading=lazy]')"
                                       ".forEach(i=>i.loading='eager')"),
                   lambda: pg.wait_for_function(ready, timeout=12000),
                   lambda: pg.evaluate(SETTLE_JS),
                   lambda: pg.wait_for_timeout(2600)):
            try:
                fn()
            except Exception:
                pass          # 和 shoot.py 同一条规矩：超时只降级，不抛异常
        out += pg.evaluate(RUNTIME_PROBE, {"profile": profile, "aesthetic": aesthetic,
                                   "personas": {} if no_persona else PERSONAS,
                                   "slotCaptions": list(SLOT_CAPTIONS)})
        if profile == "app-screen":
            out.append(state_switches(pg))
        out.append({"code": "js-error", "ok": not errs,
                    "detail": " | ".join(errs[:2]), "want": "零 JS 报错"})
        b.close()
    return out


# 候选控件：先按语义找，找不到再退回"看起来像 tab 的一排东西"。
STATE_SEL = ("[role=tab],[aria-selected],[data-tab],[data-view],[data-target],"
             "[data-screen-to],.tab,.tabs>*,nav button,nav a,"
             "button,a[href^='#'],[role=button]")


def state_switches(pg) -> dict:
    """真的去点一遍，数有几个控件改变了界面。—— prototype-not-deck 的主判据。

    为什么必须真点：`prototype-controls` 只能证明"页面上有按钮"，
    而 那份 deck 也有按钮（上一页 / 下一页）。
    区别在于**点了之后界面变不变成另一个产品状态**。
    幻灯片点了只是换一屏，产品点了会换 tab、展开详情、切筛选。

    实现：记录点击前后的"可见文字 + 可见元素 rect 集合"指纹，逐个点，
    统计有多少个控件让指纹变了。不 reload，允许状态累积 ——
    这正是真实使用的样子。
    """
    SIG = """ () => {
      const vh = innerHeight, vw = innerWidth;
      const parts = [];
      document.querySelectorAll('*').forEach(e => {
        const r = e.getBoundingClientRect();
        if (r.width < 4 || r.height < 4 || r.top > vh || r.bottom < 0
            || r.left > vw || r.right < 0) return;
        const cs = getComputedStyle(e);
        if (cs.visibility === 'hidden' || cs.opacity === '0') return;
        parts.push(Math.round(r.top) + ',' + Math.round(r.left) + ','
                 + Math.round(r.width) + ',' + Math.round(r.height)
                 + ',' + cs.backgroundColor);
      });
      return parts.join('|') + '##' + (document.body.innerText || '').slice(0, 4000);
    }"""
    try:
        before = pg.evaluate(SIG)
        n = pg.evaluate(f" () => document.querySelectorAll(\"{STATE_SEL}\").length")
        changed, tried = 0, 0
        for i in range(min(int(n), 14)):
            try:
                el = pg.query_selector_all(STATE_SEL)[i]
                if not el or not el.is_visible():
                    continue
                box = el.bounding_box()
                if not box or box["width"] < 20 or box["height"] < 20:
                    continue
                tried += 1
                el.click(timeout=1500, force=True)
                pg.wait_for_timeout(420)
                after = pg.evaluate(SIG)
                if after != before:
                    changed += 1
                    before = after
            except Exception:
                continue
        ok = changed >= 2
        return {"code": "prototype-not-deck", "ok": ok,
                "detail": f"点了 {tried} 个控件，{changed} 个真的改变了界面",
                "want": "至少 2 个控件点下去会切换到另一个产品状态"
                        "（切 tab / 进详情 / 展开 / 筛选）—— "
                        "交的是能用的产品原型，不是关于产品的幻灯片"}
    except Exception as e:                       # 探测本身失败 = 不算通过
        return {"code": "prototype-not-deck", "ok": False,
                "detail": f"交互探测失败：{str(e)[:80]}",
                "want": "至少 2 个控件点下去会切换到另一个产品状态"}


# ── M3 · 并排指纹对照板（§5.8）────────────────────────────
# **它一条都不阻断，也一句建议都不给。** 三条设计判据：
#
# 1 只印数值，不给建议。一给建议就变成规则，而规则会被照抄成模板脸。
# 2 区间来自实测（reference/fingerprints/index.json 的说明里写着"不是估计值"），
# 且**区间不是目标值**——scale-atlas.json 的原文：
# 「参考库里 H1/正文 从 2.4 到 9.8 都是获奖稿。区间只回答一件事：
# 你现在这个数是不是掉在所有获奖稿之外」。
# 3 **按 surface 取对的区间**。字阶下沿 2.8 对年报/活动 H5 成立，
# 对 App / 小程序界面稿不成立（真实 App 的标题就是 24–32px）。
# plan.py 早就有这个意识，M3 把它从一句提示变成一列真实数值。
GOLD_FOR = {"app-screen": "app-home", "h5": "h5-cycle", "web": "web-pulse",
            "web-console": "console-api", "big-screen": "screen-hotan",
            "spec-board": "board-flow", "long-image": "longimg-summit"}
BANDS = {   # (标签, 取值键, App 稿的区间, 年报/官网稿的区间)
    "字阶比": ("cliff", "真实 App 的标题就是 24–32px，gold 实测 1.3",
             "H5/官网 p10 2.8 / 中位 3.6 / p90 6.9"),
    "圆角中位": ("radMid", "gold/app-home 实测 10px", "获奖库中位 3px，12 份里 4 份纯直角"),
    "圆角取值数": ("radLevels", "只有 1 个值＝一个圆角套所有东西", "同左"),
    "强调色饱和": ("accentSat", "获奖库中位 0.80，12 份里 10 份 >=0.6", "同左"),
    "首屏影像占比": ("imgPct", "门的下沿 40%；gold 实测 16.5（内容即画面）",
                "cowboy 100% · lunge 100% · fuse 79%"),
    "真实视觉资产": ("assets", "产品界面下限 5，gold 实测 9", "影像驱动稿下限 8，gold 实测 17 / 14"),
}


def _w(s: str) -> int:
    import unicodedata
    return sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in str(s))


def _pad(s: str, n: int, right: bool = False) -> str:
    gap = " " * max(0, n - _w(s))
    return (gap + str(s)) if right else (str(s) + gap)


def _fp_gold(profile: str) -> dict:
    p = (Path(__file__).resolve().parent.parent / "reference" / "fingerprints"
         / "gold.json")
    try:
        return json.loads(p.read_text(encoding="utf-8")).get(
            GOLD_FOR.get(profile, ""), {})
    except Exception:
        return {}


def fingerprint_board(mine: dict, profile: str, url: str) -> str:
    if "/gold/" in str(Path(url).resolve()).replace("\\", "/"):
        return ""                       # gold 和自己比没有意义
    g = _fp_gold(profile)
    gname = GOLD_FOR.get(profile, "-")
    app_like = profile in ("app-screen",)
    L = ["", "── 并排对照（不是门，一条都不阻断）" + "─" * 34,
         _pad("", 14) + _pad("你这一稿", 12, True)
         + _pad("gold/" + gname, 18, True) + "   外部锚点 / 获奖库区间"]
    for label, (key, app_band, other_band) in BANDS.items():
        L.append(_pad(label, 14) + _pad(mine.get(key, "—"), 12, True)
                 + _pad(g.get(key, "—"), 18, True) + "   "
                 + (app_band if app_like else other_band))
    L += ["",
          "  这些数只回答一件事：**你现在这个数是不是掉在所有获奖稿之外。**",
          "  区间不是目标值，落在哪一段由你这一稿的签名定；怎么补是你的事。",
          "  想看它们长什么样：reference/fingerprints/thumbs/ 三张 + "
          "gold/ 五组带源码的产物。", "─" * 70]
    return "\n".join(L)


def file_sha(p: Path) -> str:
    """内容指纹，取前 12 位够用（收据是给「变没变」用的，不是防篡改）。"""
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()[:12]
    except OSError:
        return ""


def target_shas(a) -> dict[str, str]:
    """本次量过的每个目标 → 内容哈希。目标不是本地文件（URL）时留空。"""
    out: dict[str, str] = {}
    for rel in list(a.canvas or []) + ([a.url] if a.url else []):
        p = Path(rel)
        if p.is_file():
            out[str(rel)] = file_sha(p)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="真值门")
    runstate.add_run_arg(ap)
    ap.add_argument("--url", help="URL 或本地文件/目录路径")
    ap.add_argument("--canvas", nargs="*", default=[])
    ap.add_argument("--profile", default="web", choices=list(PROFILES))
    ap.add_argument("--aesthetic", action="store_true",
                    help="加跑审美正向判据（全部 REPORT，不阻断交付）")
    ap.add_argument("--doc-voice", action="store_true",
                    help="加跑汇报口吻判据（配 --canvas 用，全部 REPORT）")
    ap.add_argument("--viewport",
                    help="WxH 覆盖 profile 的默认取景 —— 大屏/展板/长图的尺寸"
                         "由 query 决定，不是载体默认（合同里的 canvas 字段）")
    ap.add_argument("--json")
    a = ap.parse_args()

    results: list[dict] = []
    for c in a.canvas:
        results += canvas_gates(Path(c))
        if a.doc_voice:
            results += doc_voice_gates(Path(c))
    if a.doc_voice and a.canvas:
        results += doc_whole_gates([Path(c) for c in a.canvas])

    if a.url:
        try:
            import playwright.sync_api  # noqa: F401
        except ImportError:
            print("PLAYWRIGHT_MISSING —— 运行时门跳过；静态门仍已执行。", file=sys.stderr)
        else:
            url, srv = resolve(a.url)
            try:
                vw, vh = PROFILES[a.profile]
                if a.viewport and re.fullmatch(r"\d+x\d+", a.viewport.lower()):
                    vw, vh = (int(x) for x in a.viewport.lower().split("x"))
                widths = DOC_WIDTHS if a.profile == "doc" else [vw]
                h = vh
                # gold 自己就是参照物，拿它和自己比恒等于 13/13 —— 没有意义。
                is_gold = "/gold/" in str(Path(a.url).resolve()).replace("\\", "/")
                # 三个宽度**逐个量，但每道门只报一行**：取最坏的那个宽度。
                # 每个宽度各印一遍，doc 一次返回 63 条
                # （21 道门 × 3 个宽度）—— 信息量没变，噪声翻了三倍，
                # 而守则的红线是"最小合法输入实跑返回 >20 条即过载"。
                worst: dict[str, dict] = {}
                for w in widths:
                    for r in probe(url, a.profile, w, h, a.aesthetic,
                                   no_persona=is_gold):
                        prev = worst.get(r["code"])
                        if len(widths) > 1:
                            r["detail"] = f"@{w}px {r['detail']}".strip()
                        # 已经有失败的就不被后面的 PASS 覆盖
                        if prev is None or (prev["ok"] and not r["ok"]):
                            worst[r["code"]] = r
                results += list(worst.values())
                # 移动端**必须量两档**：390 是真机，1440 是卡片被用户看到的宽度。
                # 这里只在 1440 那一档量 frame-intact 一条 —— 把整套门搬到桌面宽度
                # 跑一遍会造出一堆假阳性（一个手机页在 1440 下当然"首屏没画面"），
                # 而那正是"两道门对同一份几何给出相反结论"的做法。
                if a.profile in ("h5", "app-screen"):
                    results.append(probe_frame(url))
            finally:
                if srv:
                    srv.close()

    skip = SKIP_BY_PROFILE.get(a.profile, set())
    if skip:
        results = [r for r in results if r["code"] not in skip]
        print(f"（{a.profile}：{len(skip)} 条门对这种载体不适用，已关掉 —— "
              f"{'、'.join(sorted(skip))}）")
    blocked = [r for r in results if not r["ok"] and r["code"] in BLOCK]
    reported = [r for r in results if not r["ok"] and r["code"] not in BLOCK
                and r["code"] != "ref-scale"]
    for r in results:
        if r["code"] == "ref-board":
            continue                      # 它是对照板的原料，不是一行门
        if r["code"] == "ref-scale":
            print(f"  参考   {r['code']:22}{r['detail']}")
            continue
        tag = "  PASS  " if r["ok"] else ("✗ BLOCK  " if r["code"] in BLOCK else "· REPORT ")
        line = f"{tag}{r['code']:22}{r['want']}"
        if not r["ok"]:
            line += f"   → 实测 {r['detail']}"
        print(line)
    n_shown = len([r for r in results if r["code"] != "ref-board"])
    print(f"\n{len([r for r in results if r['ok'] and r['code'] != 'ref-board'])}"
          f"/{n_shown} 通过｜BLOCK {len(blocked)}｜REPORT {len(reported)}")
    if a.aesthetic and not blocked:
        board = next((r for r in results if r["code"] == "ref-board"), None)
        if board:
            print(fingerprint_board(json.loads(board["detail"]), a.profile,
                                    a.url or ""))

    assets = next((r for r in results if r["code"] == "asset-count"), None)
    # 收据要记**内容哈希**，不只是文件名。
    # 「这个文件跑过门没有」按文件名判时，两条命令之间手工改过的产物
    # 会被当成已经跑过，最后一次修改永远不被任何门看见。
    runstate.add_receipt(runstate.find(a.run), "check", {
        "profile": a.profile, "target": a.url or ",".join(a.canvas),
        "sha": target_shas(a),
        "block": [r["code"] for r in blocked],
        "report": [r["code"] for r in reported],
        "assetCount": int(re.match(r"\d+", assets["detail"]).group()) if assets else None,
        "passed": not blocked,
    })

    if a.json:
        Path(a.json).write_text(json.dumps(results, ensure_ascii=False, indent=2),
                                encoding="utf-8")
    if blocked:
        # 不要写成「BLOCK 的含义是"预算内要重出一次"，不是"不能交付"」。
        # 本意是防死锁，实际效果是**发了一张"可以不改"的许可**：
        # 一份真实产物连跑 8 次门，8 次都是 img-broken + text-invisible，
        # 一次都没改，稿照样交了出去，用户看到的就是一排 alt 文字和压在一起的字。
        # 所以现在先点名"交付端一定碎"的那几条，再说防死锁。
        codes = {r["code"] for r in blocked}
        if "frame-intact" in codes:
            print("\n**frame-intact 说的是「这一稿在桌面宽度下不是手机形态」。**\n"
                  "  卡片就是在 1440 宽下被用户打开的 —— 状态栏和 Tab 栏横贯整屏，\n"
                  "  用户看到的就是「h5 没走移动端的模板」。\n" + FRAME_FIX)
        hard = [c for c in ("img-broken", "img-remote-src", "element-overlap",
                            "content-under-dock", "overflow-x", "placeholder")
                if c in codes]
        if hard:
            print(f"\n**{'、'.join(hard)} 不是审美问题，是坏掉。**\n"
                  "  它们在交付端一定碎：图取不到就是一排 alt 文字，"
                  "重叠就是字压着字。\n"
                  "  用户看到的就是这个 —— 交付之前必须修掉，别往下走。")
        print("\n其余 BLOCK 的含义是「预算内要重出一次」，不是「不能交付」。\n"
              "  在改稿之前先问一句：这条门 FAIL 掉 gold/ 里的产物吗？\n"
              "  会 —— 那多半是这条判据不对，先怀疑门。")
    if reported:
        print("REPORT 不拦你，但它是「离得奖级还差什么」的清单 —— 改稿前读一遍。")
    return 1 if blocked else 0


# ── 标定记录：初版提的六条审美判据里，有三条没通过 gold 标定，已经删掉 ──────
#
# 判据            gold-web   gold-h5   低分参照样本   结论
# 主角占比 >=0.35    1.00      0.17      0.10     ✗ 判死 gold-h5（它的美术是 CSS 画的，
# 换成"最大视觉簇"后 低分参照样本 反涨到 0.95，
# 两个方向都不成立）
# 强调色面积 3–12%   0.6%     22.5%      5.3%     ✗ 完全反了：gold 两个都在区间外，
# 低分参照样本 反而在区间内
# 卡片等分度         0.82      0.25      1.08     ✗ 不区分：低分参照样本 最高，
# 而 gold doc 的关键屏网格是 0（等分是它的正当版式）
#
# 又删掉一条 —— doc 的「图文比 0.8–2.5」：
#
# pulse-a 0.17 ｜ pulse-b 1.4 ｜ qq-b 2.1 ｜ cycle-b 3.45
#
# 四块画布都是被验收通过的稿，跨度却是 20 倍。
# 因为它量的其实是**版面类型**（理解/主张那半篇天生少图，逐屏那半篇天生多图），
# 不是质量。判据一旦把好稿判成"两头都错"，它就是个噪音源。
#
# 还删掉一条 —— doc 的「讲为什么的段落占比 >=0.30」：
#
# gold pulse-a 0.17 ｜ cycle-a 0.15 ｜ cycle-b 0.12 ｜ **反例 低分参照样本 doc 0.2**
#
# 反例比三份 gold 都高。因为它数的是"因为/所以/为什么"这些连接词，
# 而好的汇报常常直接说"他在这里想干什么"，一个连接词都不用。
# **数措辞量不出讲不讲道理。**
#
# 教训还是那句：**单一指标不区分好坏，比值和组合才区分。**
# 留下来的四条都是比值或组合，且都做到了「跑 gold 零报警、跑 低分参照样本 全报警」。
# 想把上面三条加回来，先拿出新的定义和新的标定数据。

if __name__ == "__main__":
    sys.exit(main())
