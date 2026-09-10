#!/usr/bin/env python3
"""
HTML 自检脚本：一次完成"加载 + 截图 + 结构/错误/溢出检查"。

里列了正式接口需求，此脚本是踩过所有已知坑的一手参考。可以照它把功能
搬到 lark-cli 的 `html screenshot` 子命令下。

用法：
  python3 shot.py <path_or_url>
      # 默认在同目录 _shots/ 下产出 desktop / mobile 两张全页 JPEG
      # 同时打印 JSON 报告到 stdout

  python3 shot.py index.html --only desktop        # 只截桌面（迭代最快）
  python3 shot.py index.html --include lint        # 只跑 lint 不截图（更快）
  python3 shot.py index.html --outdir shots        # 换输出目录
  python3 shot.py index.html --desktop 1920x1080 --mobile 375x812
  python3 shot.py index.html --format png          # 保留无损

引擎选择（自动）：
  - 首选 playwright（图质量高、DOM 报告完整）
  - playwright 未装或 chromium 缺失时，自动降级到 chrome / edge / chromium 命令行
    （Mac / Linux / Windows 常见路径都会扫）。降级模式下 lint / structure 字段
    为 null，只保证截图可用。
  - 都不可用时明确报错（exit code 3，JSON 里带 error.code=no_browser）。

Exit codes:
  0  成功
  2  参数/输入错误（文件不存在、include 无效项等）
  3  浏览器不可用或渲染失败

任何情况下 stdout 都是合法 JSON，不会裸抛 traceback。
"""

import argparse
import base64
import hashlib
import io
import json
import os
import platform
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

# playwright 是可选依赖——lazy import 让 shot.py 在无 playwright 环境也能跑
try:
    from playwright.sync_api import sync_playwright  # type: ignore
    HAVE_PLAYWRIGHT = True
except Exception:
    sync_playwright = None  # type: ignore
    HAVE_PLAYWRIGHT = False


# 页面初始化阶段（goto 前）注入：patch EventTarget.addEventListener，
# 把"元素自身"或"祖先"绑过 click listener 的信息落地成 dataset 标记，
# 让 REPORT_SCRIPT 能区分"真僵尸"vs"有 listener 只是我们查不到"。
# 局限：无法覆盖 document/window 上的全局委托（那种 target 是任意元素，标不到具体按钮）
INIT_SCRIPT = r"""
(() => {
  const proto = EventTarget && EventTarget.prototype;
  if (!proto || proto.__shot_patched) return;
  proto.__shot_patched = true;
  const orig = proto.addEventListener;
  proto.addEventListener = function(type, listener, opts) {
    try {
      if (type === 'click' && this && this.nodeType === 1) {
        // 只标 Element；document/window 上的委托不标（否则每个按钮都会被误认为"有 handler"）
        this.__shot_hasClickListener = true;
        // 顺带把 listener 源码存下来。3b 的 javascript: 占位符收紧路径要用它证明
        // "祖先 handler 是否真的路由到当前元素"——通过检查源码里是否引用了元素的
        // class / id / data-* 值。listener 是箭头函数 / 普通函数时 toString 一般能拿到源码；
        // native / bound / minify 后的短名会拿不到有效标识，那种情况下判定会 fallback 到
        // 保守报（带 note 让人肉核对），不会静默漏抓。
        try {
          const src = typeof listener === 'function'
            ? Function.prototype.toString.call(listener) : '';
          if (src) (this.__shot_listenerSources = this.__shot_listenerSources || []).push(src);
        } catch (e) {}
      }
    } catch (e) {}
    return orig.call(this, type, listener, opts);
  };
})();
"""


PREP_SCRIPT = r"""
() => {
  // 常见 scroll-reveal / 动画类，强制显现——避免 opacity:0 元素在截图里空白
  const sel = [
    '.rv','.reveal','.fade','.fade-in','.fade-up','.fade-down',
    '.animate','.animated','.aos-init','.aos-animate','.wow','.sal',
    '[data-reveal]','[data-aos]','[data-animate]','[data-sal]',
  ].join(',');
  const els = document.querySelectorAll(sel);
  els.forEach(el => {
    el.classList.add('in','is-visible','aos-animate','revealed','visible','animated');
    el.style.opacity = '1';
    el.style.transform = 'none';
    el.style.visibility = 'visible';
    el.style.transition = 'none';
    el.style.animation = 'none';
  });
  // 关掉 smooth scroll，让 scrollTo 立即生效
  document.documentElement.style.scrollBehavior = 'auto';
  return els.length;
}
"""


# 渲染稳态探针：调用方每 ~120ms 跑一次，全 true 才认为可以截图。
# 判据：readyState=complete + 字体加载完成 + 全部 <img> decode 完 + 连续两帧
# scrollHeight 稳定（挡布局抖动 / 懒加载图片撑高的情况）。
# 常驻动画 / setInterval 不影响判据（我们只关心高度稳）。挂 __shot_ready_state
# 在 window 上避免每次调用都新挂 fonts.ready Promise。
READY_SCRIPT = r"""
() => {
  const S = (window.__shot_ready_state = window.__shot_ready_state || {
    fontsReady: false, lastH: -1, sameFrames: 0,
  });
  if (document.readyState !== 'complete') return false;
  if (!S.fontsReady) {
    if (document.fonts && document.fonts.status === 'loaded') {
      S.fontsReady = true;
    } else if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(() => { S.fontsReady = true; }).catch(() => { S.fontsReady = true; });
      return false;
    } else {
      S.fontsReady = true;  // 老浏览器无 document.fonts，直接跳过
    }
  }
  const imgs = document.images || [];
  for (let i = 0; i < imgs.length; i++) {
    const im = imgs[i];
    // loading=lazy 且不在视口的图不会 decode，忽略
    if (im.loading === 'lazy') continue;
    if (!im.complete) return false;
    if (im.naturalWidth === 0) return false;
  }
  const h = document.documentElement.scrollHeight;
  if (h === S.lastH) {
    S.sameFrames += 1;
  } else {
    S.sameFrames = 0;
    S.lastH = h;
  }
  return S.sameFrames >= 2;
}
"""


REPORT_SCRIPT = r"""
() => {
  const vw = window.innerWidth, vh = window.innerHeight;
  const fw = document.documentElement.scrollWidth;
  const fh = document.documentElement.scrollHeight;

  // 视口横向溢出元素（bounding rect 超出 viewport 右边）
  const overflow = [];
  const walker = document.querySelectorAll('body *');
  for (const el of walker) {
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    if (r.right > vw + 1 || r.left < -1) {
      const cls = (el.className && el.className.baseVal !== undefined)
        ? el.className.baseVal
        : (typeof el.className === 'string' ? el.className : '');
      // 过滤掉本身处于可横向滚动或裁剪容器内的子孙——外部看不到溢出
      let p = el.parentElement, inScroller = false;
      while (p && p !== document.body) {
        const cs = getComputedStyle(p);
        if (cs.overflowX === 'auto' || cs.overflowX === 'scroll' || cs.overflowX === 'hidden' || cs.overflowX === 'clip') { inScroller = true; break; }
        p = p.parentElement;
      }
      if (inScroller) continue;
      overflow.push({
        tag: el.tagName.toLowerCase(),
        cls: (cls || '').toString().split(/\s+/).filter(Boolean).slice(0, 3).join(' '),
        left: Math.round(r.left),
        right: Math.round(r.right),
        width: Math.round(r.width),
      });
      if (overflow.length >= 20) break;
    }
  }

  // 字体加载失败检测（document.fonts）
  const fontFailures = [];
  try {
    if (document.fonts && document.fonts.forEach) {
      document.fonts.forEach(f => {
        if (f.status === 'error') {
          fontFailures.push({ family: f.family, style: f.style, weight: f.weight });
        }
      });
    }
  } catch (e) {}

  // 本地图片引用检测：交付 HTML 不能含文件系统引用，图片必须走 URL 或上传后引用
  // 判据：解析后的绝对 URL 以 file:// 开头即认为是本地引用
  const localImages = [];
  const localSeen = new Set();
  const pushLocal = (tag, attr, url) => {
    if (!url || url === document.baseURI) return;
    if (typeof url !== 'string' || !url.startsWith('file://')) return;
    if (localSeen.has(url) || localImages.length >= 20) return;
    localSeen.add(url);
    localImages.push({ tag: tag, attr: attr, url: url.slice(0, 240) });
  };
  const resolveHref = (raw) => {
    try { return new URL(raw, document.baseURI).href; } catch (e) { return null; }
  };
  // <img src / srcset>
  document.querySelectorAll('img').forEach(el => {
    if (el.getAttribute('src')) pushLocal('img', 'src', el.currentSrc || el.src);
    const ss = el.getAttribute('srcset');
    if (ss) ss.split(',').forEach(part => {
      const raw = part.trim().split(/\s+/)[0];
      if (raw) pushLocal('img', 'srcset', resolveHref(raw));
    });
  });
  // <source src / srcset>（picture / video / audio）
  document.querySelectorAll('source').forEach(el => {
    const src = el.getAttribute('src');
    if (src) pushLocal('source', 'src', resolveHref(src));
    const ss = el.getAttribute('srcset');
    if (ss) ss.split(',').forEach(part => {
      const raw = part.trim().split(/\s+/)[0];
      if (raw) pushLocal('source', 'srcset', resolveHref(raw));
    });
  });
  // SVG <image href / xlink:href>
  document.querySelectorAll('image').forEach(el => {
    const href = el.getAttribute('href') || el.getAttribute('xlink:href') || '';
    if (href) pushLocal('svg-image', 'href', resolveHref(href));
  });
  // CSS background-image
  document.querySelectorAll('body *').forEach(el => {
    const bg = getComputedStyle(el).backgroundImage;
    if (!bg || bg === 'none') return;
    const re = /url\((?:"([^"]*)"|'([^']*)'|([^)]*))\)/g;
    let m;
    while ((m = re.exec(bg)) !== null) {
      const raw = (m[1] || m[2] || m[3] || '').trim();
      if (raw) pushLocal(el.tagName.toLowerCase(), 'background-image', resolveHref(raw));
    }
  });

  // 图片形变检测：渲染盒子的宽高比 vs 图片固有宽高比
  // 最高频成因是 `<img width=W height=H>` 属性 + CSS 只覆盖 width——HTML 的 width/height 属性是
  // presentational hint（等价 `width:Wpx; height:Hpx`），优先级低于任何 author CSS。CSS 写了
  // `width:100%` 只覆盖 width，height 仍是 Hpx；`aspect-ratio: auto W/H` 里的 auto 只在有一边为
  // auto 时才反推另一边，两边都确定时不产生约束；object-fit 默认 fill 于是把内容硬拉伸填满错误的盒子。
  const stretchedImages = [];
  for (const im of document.querySelectorAll('img')) {
    if (stretchedImages.length >= 12) break;
    const nw = im.naturalWidth, nh = im.naturalHeight;
    if (!nw || !nh) continue;                          // 未加载 / 解码失败，判不了
    const cs = getComputedStyle(im);
    // 只有 fill（默认值）会拉伸内容。实测 138 个产物里 cover/contain 共 133 张，
    // 其中 42% 的盒子比例本就偏离固有比例——那是刻意的，不豁免会误报 56 张
    if (cs.objectFit !== 'fill') continue;
    // 用 computed width/height，不用 getBoundingClientRect：后者含 transform，
    // 而 transform:scale(x,y) 造成的形变是刻意的，不该报
    const w = parseFloat(cs.width), h = parseFloat(cs.height);
    if (!(w >= 20 && h >= 20)) continue;               // 装饰性小图
    const dev = (w / h) / (nw / nh);
    if (dev > 0.9 && dev < 1.111) continue;            // ±10%；实测正常态精确等于 1.000，无灰色地带
    const aw = im.getAttribute('width'), ah = im.getAttribute('height');
    // HTML height 属性值 == 渲染 height，说明 CSS 压根没覆盖 height，它直接来自属性
    const fromAttr = ah && Math.abs(parseFloat(ah) - h) < 1;
    const rawSrc = im.currentSrc || im.src || '';
    stretchedImages.push({
      reason: fromAttr ? 'html-attr-height-not-overridden' : 'box-ratio-mismatch',
      natural: nw + 'x' + nh,
      rendered: Math.round(w) + 'x' + Math.round(h),
      ratioDeviation: Math.round(dev * 100) / 100,
      attrWidth: aw, attrHeight: ah,
      cssWidth: cs.width, cssHeight: cs.height,
      cls: (im.className || '').slice(0, 40),
      alt: (im.alt || '').slice(0, 40),
      src: rawSrc.startsWith('data:') ? rawSrc.slice(0, 24) + '...' : rawSrc.slice(0, 80),
    });
  }

  // ============ 文本相关规则 ============
  // 收集"含直接文本"的元素：至少一个 direct child 是非空 Text 节点
  // 这样过滤掉纯装饰 div、图标容器等；<span>xxx</span> 与其中的 <span> 都会分别入选（各自持有自己那段文本）
  const textEls = [];
  {
    const walker = document.querySelectorAll('body *');
    for (const el of walker) {
      // 跳过 script/style/head 里的东西
      const tag = el.tagName;
      if (tag === 'SCRIPT' || tag === 'STYLE' || tag === 'NOSCRIPT') continue;
      let hasText = false;
      for (const n of el.childNodes) {
        if (n.nodeType === 3 && n.nodeValue && n.nodeValue.trim().length > 0) {
          hasText = true;
          break;
        }
      }
      if (!hasText) continue;
      const r = el.getBoundingClientRect();
      if (r.width < 2 || r.height < 2) continue;
      // 视口外太远的不做（页面很长时省算力，仍覆盖全 full-page 因为我们在截图前调用一次，
      // 且下面 rect 用文档坐标而非视口坐标）
      const cs = getComputedStyle(el);
      if (cs.visibility === 'hidden' || cs.display === 'none' || +cs.opacity === 0) continue;
      textEls.push({
        el, tag: tag.toLowerCase(),
        // 用文档坐标：加 scrollX/Y，避免视口滚动位置影响
        left: r.left + window.scrollX,
        top: r.top + window.scrollY,
        right: r.right + window.scrollX,
        bottom: r.bottom + window.scrollY,
        w: r.width, h: r.height,
        area: r.width * r.height,
        text: (el.textContent || '').trim().slice(0, 60),
      });
    }
  }

  // 规则 1：文字元素之间 rect 相交
  // 过滤：父子/祖孙关系一定 contain，永远相交，噪声。交集面积 >= 16px² 才算。
  const overlappingText = [];
  {
    // 简单 O(N^2)。文本元素通常几十到几百个，够用。
    // 优化：先按 top 排序，只跟"top 在自己 bottom 以上"的比。
    textEls.sort((a, b) => a.top - b.top);
    for (let i = 0; i < textEls.length && overlappingText.length < 15; i++) {
      const a = textEls[i];
      for (let j = i + 1; j < textEls.length; j++) {
        const b = textEls[j];
        if (b.top >= a.bottom) break; // 后面所有元素都在 a 下方了
        // 过滤祖孙/包含关系
        if (a.el.contains(b.el) || b.el.contains(a.el)) continue;
        // 计算交集
        const ix = Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left));
        const iy = Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));
        const inter = ix * iy;
        if (inter < 16) continue;
        // 相对占比：两者中较小的那个如果被吃掉一大半，更可能是真 bug
        const minArea = Math.min(a.area, b.area);
        const ratio = inter / minArea;
        overlappingText.push({
          a: { tag: a.tag, text: a.text, rect: [Math.round(a.left), Math.round(a.top), Math.round(a.w), Math.round(a.h)] },
          b: { tag: b.tag, text: b.text, rect: [Math.round(b.left), Math.round(b.top), Math.round(b.w), Math.round(b.h)] },
          intersectPx: Math.round(inter),
          coverRatio: Math.round(ratio * 100) / 100,
        });
        if (overlappingText.length >= 15) break;
      }
    }
  }

  // 规则 2：文本被容器裁掉
  // 独立扫描：任何 overflow:hidden|clip 的元素，只要它子孙里有可见文字且 scroll size > client size 就报。
  // 不复用 textEls（因为卡片本身通常无直接文本，文字在子孙 <p>/<h*> 里）
  // 忽略 text-overflow:ellipsis / -webkit-line-clamp：这两个是"故意截断"的标准 UI 模式
  // 溢出 < 4px 忽略（浮点/亚像素抖动）
  const clippedText = [];
  {
    const all = document.querySelectorAll('body *');
    for (const el of all) {
      if (clippedText.length >= 15) break;
      const tag = el.tagName;
      if (tag === 'SCRIPT' || tag === 'STYLE' || tag === 'NOSCRIPT') continue;
      if (el === document.body) continue;
      const cs = getComputedStyle(el);
      const ox = cs.overflowX, oy = cs.overflowY;
      const clipsX = (ox === 'hidden' || ox === 'clip');
      const clipsY = (oy === 'hidden' || oy === 'clip');
      if (!clipsX && !clipsY) continue;
      if (cs.visibility === 'hidden' || cs.display === 'none' || +cs.opacity === 0) continue;
      // 故意的 ellipsis：单行 text-overflow:ellipsis，或多行 -webkit-line-clamp
      const ellipsisSingle = (cs.textOverflow === 'ellipsis' && cs.whiteSpace && cs.whiteSpace.indexOf('nowrap') !== -1);
      const lineClampRaw = cs.getPropertyValue ? cs.getPropertyValue('-webkit-line-clamp') : '';
      const clampMulti = lineClampRaw && lineClampRaw !== 'none' && parseInt(lineClampRaw, 10) > 0;
      if (ellipsisSingle || clampMulti) continue;
      const dx = el.scrollWidth - el.clientWidth;
      const dy = el.scrollHeight - el.clientHeight;
      const overX = clipsX && dx > 4;
      const overY = clipsY && dy > 4;
      if (!overX && !overY) continue;
      // 子孙里得有可见文字才算"文本被裁"（否则可能只是纯图形/装饰容器裁了自己的 pseudo）
      const txt = (el.textContent || '').trim();
      if (txt.length === 0) continue;
      const r = el.getBoundingClientRect();
      if (r.width < 2 || r.height < 2) continue;
      clippedText.push({
        tag: tag.toLowerCase(),
        text: txt.slice(0, 60),
        rect: [Math.round(r.left + window.scrollX), Math.round(r.top + window.scrollY), Math.round(r.width), Math.round(r.height)],
        clippedX: overX ? dx : 0,
        clippedY: overY ? dy : 0,
      });
    }
  }

  // 规则 2.5：伪元素文字溢出（::before / ::after）
  // 目标：抓 content=attr(data-i) / 显式字符串 撑破了固定 width 的方块/圆点/序号徽章。
  // 三重触发条件（同时成立才报）：
  //   (a) content 非空非纯空白（过滤 "" / none / normal / 纯 counter/attr 但结果空）
  //   (b) 伪元素有显式固定 width（width != "auto"）——不敢猜 auto 元素的意图
  //   (c) canvas measureText 量出的文字宽度 > widthPx × 1.1（10% 抖动余量）
  // 再叠加过滤：
  //   overflow:hidden + text-overflow:ellipsis → 故意截断，跳
  //   font-family 含 FontAwesome / Material / Icons / iconfont → 图标字体量不准，跳
  //   尺寸 < 4×4 → 装饰性零宽伪元素，跳
  //   display: none → 未渲染，跳
  const pseudoOverflow = [];
  {
    // 一个 canvas 共享 measure
    const mc = document.createElement('canvas');
    const mctx = mc.getContext('2d');
    const iconFontRe = /(FontAwesome|Font\s*Awesome|Material\s*Icons|Material\s*Symbols|iconfont|glyphicons|ionicons)/i;
    // content 可能是 "S1" / "S10" / '"foo"' / 'attr(...)' → computed 后都是带引号的字符串
    // 去引号 + 处理 \HHHHHH escape
    const unquoteContent = (raw) => {
      if (!raw) return '';
      const s = raw.trim();
      if (s === 'none' || s === 'normal') return '';
      // computed content 通常是 "xxx" 或 'xxx'，还可能是多个片段："pre" attr(data-x) "post"
      // 简化：把所有 " 或 ' 包围的段拼起来，剩下的忽略（counter() 等函数）
      const parts = [];
      const re = /"((?:[^"\\]|\\.)*)"|'((?:[^'\\]|\\.)*)'/g;
      let m;
      while ((m = re.exec(s)) !== null) {
        const raw2 = m[1] !== undefined ? m[1] : m[2];
        // \HH 转义
        const decoded = raw2.replace(/\\([0-9a-fA-F]{1,6})\s?/g, (_, hex) => {
          const cp = parseInt(hex, 16);
          if (cp > 0x10ffff) return '';
          return String.fromCodePoint(cp);
        }).replace(/\\(.)/g, '$1');
        parts.push(decoded);
      }
      return parts.join('');
    };
    const all = document.querySelectorAll('body *');
    for (const el of all) {
      if (pseudoOverflow.length >= 15) break;
      const tag = el.tagName;
      if (tag === 'SCRIPT' || tag === 'STYLE' || tag === 'NOSCRIPT') continue;
      for (const pseudo of ['::before', '::after']) {
        if (pseudoOverflow.length >= 15) break;
        let cs;
        try { cs = getComputedStyle(el, pseudo); } catch (e) { continue; }
        if (!cs) continue;
        if (cs.display === 'none') continue;
        if (cs.visibility === 'hidden' || +cs.opacity === 0) continue;
        // 触发条件 (b)：必须有显式 width
        const wStr = cs.width;
        if (!wStr || wStr === 'auto' || wStr.endsWith('%')) continue;
        const wPx = parseFloat(wStr);
        if (!(wPx > 0)) continue;
        // 尺寸太小的装饰跳过
        const hStr = cs.height;
        const hPx = parseFloat(hStr) || 0;
        if (wPx < 4 || hPx < 4) continue;
        // 触发条件 (a)：content 有实际文字
        const text = unquoteContent(cs.content);
        if (!text || !text.trim()) continue;
        // ellipsis 故意截断
        const ellipsis = (cs.textOverflow === 'ellipsis' && cs.overflow !== 'visible');
        if (ellipsis) continue;
        // 图标字体
        const fam = cs.fontFamily || '';
        if (iconFontRe.test(fam)) continue;
        // 测宽度
        const fSize = cs.fontSize || '14px';
        const fWeight = cs.fontWeight || '400';
        const fStyle = cs.fontStyle || 'normal';
        // canvas font 语法：style weight size family
        mctx.font = `${fStyle} ${fWeight} ${fSize} ${fam}`;
        const textW = mctx.measureText(text).width;
        // 考虑 box-sizing：如果 border-box，内容区 = width - padding - border
        // 简化：默认 content-box 就用 width 本身；border-box 减掉 padding-left/right
        let contentW = wPx;
        if (cs.boxSizing === 'border-box') {
          const pl = parseFloat(cs.paddingLeft) || 0;
          const pr = parseFloat(cs.paddingRight) || 0;
          const bl = parseFloat(cs.borderLeftWidth) || 0;
          const br = parseFloat(cs.borderRightWidth) || 0;
          contentW = Math.max(1, wPx - pl - pr - bl - br);
        }
        // 触发条件 (c)：文字量出来比 contentW 明显宽。双门槛避免 sub-pixel 抖动：
        //   相对差 > 3% 且绝对差 > 0.5px。这样 18px 盒子里的 S10(19.07px)、S15(18.86px) 都能触发；
        //   而只差 0.1-0.3px 的字体度量抖动不会误报。
        if (!(textW > contentW * 1.03 && textW - contentW > 0.5)) continue;
        // 找不到 el 的 rect 就不报（隐藏元素）
        const r = el.getBoundingClientRect();
        if (r.width < 2 || r.height < 2) continue;
        pseudoOverflow.push({
          hostTag: tag.toLowerCase(),
          hostRect: [Math.round(r.left + window.scrollX), Math.round(r.top + window.scrollY), Math.round(r.width), Math.round(r.height)],
          pseudo: pseudo,
          content: text.length > 40 ? text.slice(0, 40) + '…' : text,
          widthPx: Math.round(wPx * 10) / 10,
          contentWidthPx: Math.round(contentW * 10) / 10,
          textWidthPx: Math.round(textW * 10) / 10,
          overflowPx: Math.round((textW - contentW) * 10) / 10,
        });
      }
    }
  }

  // 规则 3：僵尸按钮 / 无效链接
  // 目标：抓那种"看起来能点、按下去什么都不发生"的元素。
  // 局限：addEventListener 绑的 handler 无法通过 DOM API 查询到（浏览器故意封的），
  //   委托模式（document.addEventListener('click', delegateHandler)）注定漏抓。
  // 已覆盖：
  //   3a  <button> 无 onclick 且无 listener
  //   3b  <a> 无有效 href（含 javascript:void(0) 占位符收紧路径）
  //   3c  非交互标签 + cursor:pointer 但无 handler（<div class="nav-item"> 假按钮）
  //   3d  <input type=button|submit|reset|image> 无 onclick 且无 listener
  //   3e  <a href="#foo"> 但 #foo 在页面里不存在（断链锚点）
  //   3f  <label for="xxx"> 但 #xxx 不存在（点击 label 无副作用）
  const deadButtons = [];
  {
    const hasDataAttr = (el) => {
      // 沿祖先链看是否有 data-*，作为"可能被委托"的启发式提示
      let p = el;
      while (p && p !== document.body) {
        if (p.attributes) {
          for (const a of p.attributes) {
            if (a.name.startsWith('data-')) return true;
          }
        }
        p = p.parentElement;
      }
      return false;
    };
    const isVisible = (el) => {
      const cs = getComputedStyle(el);
      if (cs.visibility === 'hidden' || cs.display === 'none' || +cs.opacity === 0) return false;
      const r = el.getBoundingClientRect();
      return r.width >= 4 && r.height >= 4;
    };
    // onclick 属性是"占位/no-op"字符串——生产代码里几乎没有正当用途，一律视为等同于没写。
    // 覆盖：空串 / 分号 / `return false` / `return true` / `void 0` / `void(0)` / 纯注释 / 上述组合
    const ONCLICK_NOOP_RE = /^\s*(?:\/\/[^\n]*|\/\*[\s\S]*?\*\/|;|return\s+(?:false|true)\s*;?|(?:return\s+)?void\s*\(?\s*0\s*\)?\s*;?|)\s*$/;
    const isOnclickNoop = (raw) => raw != null && ONCLICK_NOOP_RE.test(raw);
    // href 里的 javascript: 占位符——同理，作者显式关掉了 native 导航，如果 JS 侧没人接手就是纯僵尸
    const JS_PLACEHOLDER_RE = /^\s*javascript\s*:\s*(?:void\s*\(?\s*0\s*\)?\s*;?|;|)\s*$/i;
    // 沿祖先链找最近的绑过 click 的元素
    const nearestAncestorWithListener = (el) => {
      let p = el.parentElement;
      while (p && p !== document.body) {
        if (p.__shot_hasClickListener) return p;
        p = p.parentElement;
      }
      return null;
    };
    // 判断祖先的某个 listener 源码"是否引用了本元素"——用作 javascript: 占位符的
    // 收紧兜底。识别依据：class（长度≥3，过滤 "on"/"in" 等超短通用词）、id、data-* 值。
    // 全都不匹配也不代表一定没委托（listener 被 minify 或用 e.target.tagName 就没痕迹），
    // 这种情况下我们仍报出但带 note 提示"可能是委托，请核对"。
    const ancestorCoversElement = (anc, el) => {
      const srcs = anc.__shot_listenerSources || [];
      if (!srcs.length) return null;   // 有 hasClickListener 但没源码（native/bound），无法判断
      const tokens = [];
      const cls = (typeof el.className === 'string' ? el.className : '').trim().split(/\s+/);
      for (const c of cls) if (c.length >= 3) tokens.push(c);
      if (el.id && el.id.length >= 3) tokens.push(el.id);
      for (const attr of el.attributes) {
        if (attr.name.startsWith('data-') && attr.value && attr.value.length >= 2) {
          tokens.push(attr.value);
          tokens.push(attr.name);   // 属性名本身也常出现在 querySelector('[data-page]') 里
        }
      }
      if (!tokens.length) return false;
      return srcs.some(s => tokens.some(t => s.indexOf(t) !== -1));
    };
    const push = (el, reason, extra) => {
      if (deadButtons.length >= 20) return;
      const r = el.getBoundingClientRect();
      const txt = (el.textContent || '').trim();
      const rec = {
        tag: el.tagName.toLowerCase(),
        text: txt.slice(0, 60),
        reason: reason,
        rect: [Math.round(r.left + window.scrollX), Math.round(r.top + window.scrollY), Math.round(r.width), Math.round(r.height)],
      };
      if (extra) Object.assign(rec, extra);
      if (hasDataAttr(el)) {
        rec.note = 'ancestor-has-data-attr: 可能被 addEventListener 委托捕获，请核对';
      }
      deadButtons.push(rec);
    };

    // 3a：<button>
    for (const btn of document.querySelectorAll('button')) {
      if (deadButtons.length >= 20) break;
      const onclickRaw = btn.getAttribute('onclick');
      const onclickNoop = isOnclickNoop(onclickRaw);
      // onclick property 有值且不是 no-op 字符串 —— 真 handler，跳过
      if (btn.onclick != null && !onclickNoop) continue;
      // 被 addEventListener('click', ...) 绑过（自身或祖先）—— 由 INIT_SCRIPT 打的标
      if (btn.__shot_hasClickListener) continue;
      if (nearestAncestorWithListener(btn)) continue;
      // form submit / reset：原生行为不需要 onclick
      const type = (btn.getAttribute('type') || '').toLowerCase();
      const inForm = !!btn.closest('form');
      if (inForm && (type === 'submit' || type === '' || type === 'reset')) continue;
      // popover / command 触发器（原生 API）
      if (btn.hasAttribute('popovertarget') || btn.hasAttribute('commandfor')) continue;
      // aria pattern，多用委托 —— 常见 tab/menuitem/option/switch/checkbox/radio
      const role = (btn.getAttribute('role') || '').toLowerCase();
      if (role && ['tab','menuitem','option','switch','checkbox','radio','menuitemcheckbox','menuitemradio'].indexOf(role) !== -1) continue;
      // 被 <label> 包着：视觉是按钮，实际点击会走 label→input 关联
      if (btn.closest('label')) continue;
      // 必须可见、有文字（纯图标按钮先不报，避免和 icon button 假阳性打架）
      if (!isVisible(btn)) continue;
      if ((btn.textContent || '').trim().length === 0) continue;
      push(btn, onclickNoop ? 'onclick-noop' : 'button-no-onclick',
           onclickNoop ? { onclickAttr: (onclickRaw || '').slice(0, 60) } : null);
    }

    // 3b：<a>
    for (const a of document.querySelectorAll('a')) {
      if (deadButtons.length >= 20) break;
      const onclickRaw = a.getAttribute('onclick');
      const onclickNoop = isOnclickNoop(onclickRaw);
      if (a.onclick != null && !onclickNoop) continue;
      if (a.__shot_hasClickListener) continue;
      if (!isVisible(a)) continue;
      if ((a.textContent || '').trim().length === 0) continue;

      const href = a.getAttribute('href');
      const isJsPlaceholder = href !== null && JS_PLACEHOLDER_RE.test(href);
      const anc = nearestAncestorWithListener(a);

      // 分支 1：href="javascript:void(0)" / javascript:; 等占位符
      //   作者显式声明"我用 JS 接手导航"，比 href="#" 更严格——祖先 listener 必须能证明
      //   路由到当前元素才放行；证据不足直接报。
      if (isJsPlaceholder) {
        if (anc) {
          const covered = ancestorCoversElement(anc, a);
          if (covered === true) continue;                // 源码明确引用了本元素
          if (covered === null) continue;                // 有 listener 但源码不可读（native/bound），保守放行
          // covered === false：源码可读但没引用本元素 → 祖先 handler 与我无关，判为僵尸
        }
        push(a, 'a-href-javascript-noop-no-handler', { hrefAttr: href.slice(0, 80) });
        continue;
      }

      // 分支 2：其他 href —— 沿用旧逻辑，祖先只要有任意 handler 就放行
      if (anc) continue;
      if (href === null) {
        push(a, onclickNoop ? 'onclick-noop' : 'a-no-href',
             onclickNoop ? { onclickAttr: (onclickRaw || '').slice(0, 60) } : null);
      } else if (href.trim() === '') {
        push(a, 'a-href-empty');
      } else if (href.trim() === '#') {
        // href="#" 常见于占位；如果没 onclick 且没绑事件，多半是僵尸
        push(a, 'a-href-hash-no-handler');
      } else if (href.length > 1 && href.charAt(0) === '#' &&
                 href.indexOf('/') === -1 && href.indexOf('?') === -1) {
        // 3e：断链锚点。href="#foo" 但 #foo 在页面里不存在。
        //   排除 SPA hash 路由：href 含 / 或 ? 时（"#/dashboard"、"#?tab=1"）不查。
        const targetId = href.slice(1);
        let target = null;
        try {
          target = document.getElementById(decodeURIComponent(targetId));
        } catch (e) {
          target = document.getElementById(targetId);
        }
        if (!target) {
          // <a name="..."> 也算合法锚点（虽然 HTML5 已废弃，但老站还在用）
          const named = document.getElementsByName(targetId);
          if (!named || named.length === 0) {
            push(a, 'a-broken-anchor', { hrefAttr: href.slice(0, 80) });
          }
        }
      }
      // http/https/mailto/tel、真存在的 #id、#/spa-route 一律不报
    }

    // 3c：非 button/a/input 但 CSS `cursor: pointer` 伪装成按钮的元素（<div>/<span> 假按钮）
    // 触发场景：sidebar 导航项写成 <div class="nav-item">、卡片 wrapper 写成 <div class="clickable">，
    //   视觉上明确是按钮但没绑任何 handler；用户点了没反应。
    // 判据（同时成立）：
    //   (a) computed cursor === 'pointer'
    //   (b) tagName 不是原生交互元素（button/a/input/select/textarea/label/summary/option/details）
    //   (c) 自身+祖先都没被 addEventListener('click') 绑过（INIT_SCRIPT 打的标）
    //   (d) 无 onclick 属性
    //   (e) 无键盘可达 role（button/link/tab/menuitem/option/switch/checkbox/radio）—— 那些通常靠委托
    //   (f) 可见 + 有文字（避免虚报纯装饰容器 / 图标）
    // 二次过滤：
    //   - body / html 上继承 cursor:pointer 不算（作者只是给"整体"设了 pointer，不是承诺 body 可点）
    //   - 尺寸 < 24×16（比按钮小得多）默认忽略——多半是文字里的强调 <span>
    //   - 元素在 <label> / <button> / <a> 后代里：外层已经吃了点击，跳过
    for (const el of document.querySelectorAll('body *')) {
      if (deadButtons.length >= 20) break;
      const tag = el.tagName;
      if (tag === 'SCRIPT' || tag === 'STYLE' || tag === 'NOSCRIPT' || tag === 'SVG' || tag === 'PATH') continue;
      // 排除原生交互元素——它们走 3a/3b/3d
      if (['BUTTON','A','INPUT','SELECT','TEXTAREA','LABEL','SUMMARY','OPTION','DETAILS'].indexOf(tag) !== -1) continue;
      const cs = getComputedStyle(el);
      if (cs.cursor !== 'pointer') continue;
      // body/html 上继承 pointer 忽略
      if (el === document.body || el === document.documentElement) continue;
      // 父级也是 pointer —— 大概率是从父级"继承"下来的（子孙 badge/icon 等），
      // 用户修外层容器就会连带修好里面这些，不重复报避免噪声
      const parent = el.parentElement;
      if (parent && parent !== document.body && parent !== document.documentElement) {
        const pcs = getComputedStyle(parent);
        if (pcs.cursor === 'pointer') continue;
      }
      // 显式声明的键盘可达 role：作者知道自己在做什么
      const role = (el.getAttribute('role') || '').toLowerCase();
      if (role && ['button','link','tab','menuitem','option','switch','checkbox','radio',
                   'menuitemcheckbox','menuitemradio','treeitem','gridcell'].indexOf(role) !== -1) continue;
      // 外层已是 button/a/label：点击走外层
      if (el.closest('button, a, label')) continue;
      // 有 onclick 属性直接跳
      if (el.onclick != null && !isOnclickNoop(el.getAttribute('onclick'))) continue;
      // 自身或祖先被 addEventListener('click') 绑过
      if (el.__shot_hasClickListener) continue;
      if (nearestAncestorWithListener(el)) continue;
      // 可见 + 尺寸达到"按钮量级"
      if (!isVisible(el)) continue;
      const r = el.getBoundingClientRect();
      if (r.width < 24 || r.height < 16) continue;
      // 必须有可见文字（纯图标 wrapper 已在 [role=button] 分支照顾；无文字容易虚报）
      const txt = (el.textContent || '').trim();
      if (txt.length === 0) continue;
      push(el, 'cursor-pointer-no-handler');
    }

    // 3d：<input type=button|submit|reset|image>
    //   与 <button> 完全平行，但 3a 只查 <button>，input 会漏掉。
    //   input[type=submit] 在 form 里是合法的原生行为，同样豁免；纯 <input type=button value="保存">
    //   没绑任何 handler 就是僵尸。
    for (const inp of document.querySelectorAll('input[type="button"], input[type="submit"], input[type="reset"], input[type="image"]')) {
      if (deadButtons.length >= 20) break;
      const onclickRaw = inp.getAttribute('onclick');
      const onclickNoop = isOnclickNoop(onclickRaw);
      if (inp.onclick != null && !onclickNoop) continue;
      if (inp.__shot_hasClickListener) continue;
      if (nearestAncestorWithListener(inp)) continue;
      const type = (inp.getAttribute('type') || '').toLowerCase();
      const inForm = !!inp.closest('form');
      // form 里的 submit / reset：原生行为，豁免
      if (inForm && (type === 'submit' || type === 'reset')) continue;
      if (!isVisible(inp)) continue;
      // input 没有 textContent，用 value / aria-label 作为文本代表
      const label = (inp.value || inp.getAttribute('aria-label') || inp.getAttribute('title') || '').trim();
      if (!label && type !== 'image') continue;  // 无标签的按钮先不报（多半是特殊控件）
      push(inp, onclickNoop ? 'onclick-noop' : 'input-no-handler',
           Object.assign({ inputType: type },
             onclickNoop ? { onclickAttr: (onclickRaw || '').slice(0, 60) } : {}));
    }

    // 3f：<label for="xxx"> 但 #xxx 在页面里不存在
    //   典型 case：拼写错误（for="email-inpt" 而 input id="email-input"），
    //   或组件重构后 id 变了 for 忘改。用户点 label 期望 focus 到 input，实际什么都不发生。
    for (const lb of document.querySelectorAll('label[for]')) {
      if (deadButtons.length >= 20) break;
      const forVal = (lb.getAttribute('for') || '').trim();
      if (!forVal) continue;
      let target = null;
      try {
        target = document.getElementById(forVal);
      } catch (e) {}
      if (target) continue;
      if (!isVisible(lb)) continue;
      if ((lb.textContent || '').trim().length === 0) continue;
      push(lb, 'label-for-not-found', { forAttr: forVal.slice(0, 60) });
    }
  }

  // 规则 4：栅格违和 outlier
  // 找 section/main/article 的直接子级里，个别元素撑到父容器全宽、其他子级明显更窄——
  // 典型 case：HTML 标签闭合错位（如 <p> 忘关）导致本该在 .wrap 里的元素跳到了
  // section 直接子级，拿到全宽而不是栅格宽度。浏览器容错、不报 console 错、
  // 也没横向溢出，但视觉上就是"这段内容展得比周围宽"。
  // 判据：
  //   1) 容器直接可见块级子级 >=2 个
  //   2) 至少 1 个子级宽度 <= 父容器 clientWidth * 0.95（真栅格约束）
  //   3) 报"宽度 >= 父容器 clientWidth * 0.98 且 >= 栅格子级 + 80px"的子级
  const misalignedBlocks = [];
  {
    const containers = document.querySelectorAll('section, main, article');
    for (const cont of containers) {
      if (misalignedBlocks.length >= 8) break;
      const contW = cont.clientWidth;
      if (contW < 200) continue;
      const kids = [];
      for (const c of cont.children) {
        const cs = getComputedStyle(c);
        if (cs.display === 'none' || cs.visibility === 'hidden' || +cs.opacity === 0) continue;
        if (cs.display === 'inline' || cs.display === 'inline-block' || cs.display === 'contents') continue;
        if (cs.position === 'absolute' || cs.position === 'fixed') continue;
        const r = c.getBoundingClientRect();
        if (r.width < 40) continue;
        kids.push({ el: c, w: r.width, h: r.height, l: r.left, top: r.top });
      }
      if (kids.length < 2) continue;
      // 找栅格约束子级：宽度 <= 父 95%（说明有真正的栅格约束，如 .wrap max-width）
      // 排除短装饰（h<20），装饰元素宽度不代表栅格
      const gridKids = kids.filter(k => k.w <= contW * 0.95 && k.h >= 20);
      if (gridKids.length === 0) continue;
      // 取最宽的栅格子级作参考
      const gridWidth = Math.max.apply(null, gridKids.map(k => k.w));
      // 找越轨子级：宽度 ≈ 父容器全宽 且 显著宽于栅格
      for (const k of kids) {
        if (misalignedBlocks.length >= 8) break;
        if (k.w < contW * 0.98) continue;
        const delta = k.w - gridWidth;
        if (delta < 80) continue;
        misalignedBlocks.push({
          tag: k.el.tagName.toLowerCase() + (k.el.className ? '.' + String(k.el.className).split(/\s+/)[0] : ''),
          text: (k.el.textContent || '').trim().slice(0, 60),
          rect: [Math.round(k.l + window.scrollX), Math.round(k.top + window.scrollY), Math.round(k.w), Math.round(k.h)],
          widthDeltaVsGrid: Math.round(delta),
          gridWidth: Math.round(gridWidth),
          containerWidth: Math.round(contW),
          containerTag: cont.tagName.toLowerCase() + (cont.id ? '#' + cont.id : ''),
        });
      }
    }
  }

  // ============ 双列高度错配（uneven columns） ============
  // 触发：同一 grid/flex 行内两列高度差过大，短列下方出现大片空白。
  // 高频根因：**长列**里有 aspect-ratio 图/元素把长列高度锁死（等价：显式 style.height 的 px 值），
  //          短列内容较短、align-items:start 无法拉齐 → 短列下方相对空白。
  // 假阳性防线（缺一不报）：
  //   1) 容器必须是 grid 显式两列以上 / row-flex 且不换行；容器宽 >= 640；不在 header/nav/footer/aside 内
  //   2) 直接可见块级子级 top 差 < 4px（真同一行，排除 wrap 到多行）
  //   3) 必须能识别出根因：**长列**内有 aspect-ratio 元素占长列高度 ≥60%，或长列自身/子孙有 inline style.height 硬编码
  //      （不检 computed height——它永远 resolve 成 px，无法区分 fixed vs auto）
  //   4) 阈值：heightRatio >= 0.30 且 heightDelta >= 160 且 gapArea (短列宽 × delta) >= 40000
  //   5) stretch 豁免：容器 align-items:stretch 且短列 align-self 未被覆盖，且长列锁高源头不是 img 时跳过
  //      （单纯 stretch 布局本会拉齐；但 img 的 aspect-ratio 会强行反推 height，stretch 也拉不动）
  const unevenColumns = [];
  {
    const num = v => parseFloat(v) || 0;
    const inBanned = el => !!el.closest('header, nav, footer, aside');
    const isVisibleBlockKid = c => {
      const cs = getComputedStyle(c);
      if (cs.display === 'none' || cs.visibility === 'hidden' || +cs.opacity === 0) return false;
      if (cs.display === 'inline' || cs.display === 'inline-block' || cs.display === 'contents') return false;
      if (cs.position === 'absolute' || cs.position === 'fixed') return false;
      return true;
    };
    // 在长列子孙里找 aspect-ratio 锁高元素（首选 img，次之带 aspect-ratio 的 div/figure）
    const findAspectLocker = (col, colH) => {
      const nodes = col.querySelectorAll('img, figure, div, picture, video');
      for (let i = 0; i < nodes.length && i < 40; i++) {
        const el = nodes[i];
        const ics = getComputedStyle(el);
        if (ics.display === 'none' || ics.visibility === 'hidden') continue;
        if (!ics.aspectRatio || ics.aspectRatio === 'auto') continue;
        const rr = el.getBoundingClientRect();
        if (rr.height < 40) continue;
        if (rr.height >= colH * 0.6) return { el, h: rr.height, isImg: el.tagName === 'IMG' };
      }
      return null;
    };
    // inline style.height 硬编码（且非 % / auto）——computed 值永远是 px，无法可靠判定"作者写了固定值"
    const hasInlineFixedHeight = (col, colH) => {
      const check = el => {
        const h = el.style && el.style.height;
        if (!h || h === '' || h === 'auto') return false;
        if (h.endsWith('%')) return false;
        const v = num(h);
        return v >= 40 && v >= colH * 0.6;
      };
      if (check(col)) return true;
      let best = null;
      for (const c of col.children) {
        if (!isVisibleBlockKid(c)) continue;
        const r = c.getBoundingClientRect();
        if (!best || r.height > best.h) best = { el: c, h: r.height };
      }
      return best ? check(best.el) : false;
    };

    const containers = document.querySelectorAll('body *');
    for (const cont of containers) {
      if (unevenColumns.length >= 6) break;
      const cs = getComputedStyle(cont);
      const disp = cs.display;
      let isGrid = false, isFlex = false;
      if (disp === 'grid' || disp === 'inline-grid') {
        const tpl = cs.gridTemplateColumns;
        if (!tpl || tpl === 'none' || /subgrid/i.test(tpl)) continue;
        const cols = tpl.trim().split(/\s+/).filter(Boolean);
        if (cols.length < 2) continue;
        isGrid = true;
      } else if (disp === 'flex' || disp === 'inline-flex') {
        const fd = cs.flexDirection;
        if (fd !== 'row' && fd !== 'row-reverse') continue;
        if (cs.flexWrap === 'wrap' || cs.flexWrap === 'wrap-reverse') continue;
        isFlex = true;
      } else continue;

      const contR = cont.getBoundingClientRect();
      if (contR.width < 640) continue;
      if (contR.height < 300) continue;
      if (inBanned(cont)) continue;

      const kids = [];
      for (const c of cont.children) {
        if (!isVisibleBlockKid(c)) continue;
        const r = c.getBoundingClientRect();
        if (r.width < 60 || r.height < 20) continue;
        kids.push({ el: c, w: r.width, h: r.height, top: r.top });
      }
      if (kids.length < 2) continue;
      const topMin = Math.min.apply(null, kids.map(k => k.top));
      const topMax = Math.max.apply(null, kids.map(k => k.top));
      if (topMax - topMin > 4) continue;

      kids.sort((a, b) => a.h - b.h);
      const shortK = kids[0], tallK = kids[kids.length - 1];
      const delta = tallK.h - shortK.h;
      const ratio = delta / tallK.h;
      const gapArea = shortK.w * delta;
      if (ratio < 0.30) continue;
      if (delta < 160) continue;
      if (gapArea < 40000) continue;

      // 归因：只查长列
      const locker = findAspectLocker(tallK.el, tallK.h);
      let reason = null, lockerTag = null;
      if (locker) {
        reason = locker.isImg ? 'tall-column-image-aspect-ratio' : 'tall-column-aspect-ratio';
        lockerTag = locker.el.tagName.toLowerCase();
      } else if (hasInlineFixedHeight(tallK.el, tallK.h)) {
        reason = 'tall-column-fixed-height';
      }
      if (!reason) continue;

      // stretch 豁免：仅当锁高源头不是 img/aspect-ratio 时才豁免——那两种 stretch 也拉不动
      const ai = cs.alignItems;
      const shortCS = getComputedStyle(shortK.el);
      const asel = shortCS.alignSelf;
      const stretched = (asel === 'stretch') || ((asel === 'auto' || asel === 'normal') && ai === 'stretch');
      if (stretched && reason === 'tall-column-fixed-height') continue;

      const cls = e => (typeof e.className === 'string' ? e.className : '').split(/\s+/).filter(Boolean).slice(0, 2).join('.');
      const label = e => e.tagName.toLowerCase() + (cls(e) ? '.' + cls(e) : '') + (e.id ? '#' + e.id : '');
      unevenColumns.push({
        container: label(cont),
        containerDisplay: isGrid ? 'grid' : 'flex',
        containerWidth: Math.round(contR.width),
        shortChild: { tag: label(shortK.el), w: Math.round(shortK.w), h: Math.round(shortK.h) },
        tallChild: { tag: label(tallK.el), w: Math.round(tallK.w), h: Math.round(tallK.h) },
        heightDeltaPx: Math.round(delta),
        heightRatio: Math.round(ratio * 100) / 100,
        gapArea: Math.round(gapArea),
        reason: reason,
        lockerTag: lockerTag,
        alignItems: ai,
        alignSelf: asel,
      });
    }
  }

  // ============ 时间轴轴线 / 圆点对齐 ============
  // 触发：页面出现 timeline 类关键词（class/id）。时间轴是 slop 高发区，且两个根因完全机械：
  //   pseudo-content-box —— 圆点用 ::before 画且带 border。`*{box-sizing:border-box}` **不匹配伪元素**，
  //                         伪元素仍是 content-box，实际外径比作者心算大 2*border，偏移恒等于 border-width。
  //   origin-mismatch    —— 轴线挂在外层容器的 ::before 上、圆点挂在内层 item 里，
  //                         两者定位原点差一个容器 padding-left，偏移恒等于该 padding-left。
  // 伪元素拿不到 rect，按「包含块 padding 边 + left + marginLeft + 外径/2」推算；真元素直接用 rect。
  const timelineAlignment = { present: false, measured: 0, issues: [], deadDotStyles: [] };
  {
    const TLRE = /timeline|time-line|tl-|时间轴|时间线/i;
    const idcls = el => (typeof el.className === 'string' ? el.className : '') + ' ' + (el.id || '');
    // 容器类名可能就叫 .tl（Orange 那种），单靠 /tl-/ 会整棵树漏测，所以按 token 精确匹配一次
    const isTLToken = el => idcls(el).trim().split(/\s+/).some(t => /^(tl|timeline|time-?line)([-_].*)?$/i.test(t));
    const num = v => parseFloat(v) || 0;

    const roots = [];
    for (const el of document.querySelectorAll('*')) {
      if (roots.length >= 5) break;
      if (!TLRE.test(idcls(el)) && !isTLToken(el)) continue;
      if (el.children.length < 2) continue;
      if (roots.some(r => r.contains(el))) continue;   // 只取最外层，避免父子重复统计
      roots.push(el);
    }
    timelineAlignment.present = roots.length > 0;

    // 圆点声明了 width/height 却因为 display:inline 被静默忽略。
    // 这不是「对齐判断」——对齐有多种合法基准（实测 42 个纵向时间轴里 83% 圆点对齐内容首行，
    // 少数三者居中，都是合法的），判不了。而「非替换 inline 元素忽略 width/height/垂直 margin」
    // 是 CSS 规范的硬事实：任何设计意图下这么写都不生效，属于纯代码错误，零歧义。
    // 后果：border-radius:50% 作用在被 line-height 撑出来的畸形盒子上 → 椭圆；margin:auto 也不居中。
    for (const r of roots) {
      if (timelineAlignment.deadDotStyles.length >= 4) break;
      for (const el of r.querySelectorAll('span, i, b, em')) {
        if (timelineAlignment.deadDotStyles.length >= 4) break;
        const inline = el.style && el.style.cssText || '';
        const cs = getComputedStyle(el);
        if (cs.display !== 'inline') continue;                       // 只有 inline 会吞掉尺寸
        if (cs.borderRadius === '0px' || !cs.borderRadius) continue; // 不是圆/胶囊，不关心
        // 圆点是纯装饰、不该有任何文字。徽章/角标的文字常常只有 1-2 个字符（"3"、"NEW"），
        // 用长度阈值挡不住，只能要求完全没有文字内容。
        if ((el.textContent || '').trim()) continue;
        // 作者到底声明没声明 width/height —— inline style 直接看，作者样式表里的翻 CSSOM
        let declW = /(^|;)\s*width\s*:/i.test(inline), declH = /(^|;)\s*height\s*:/i.test(inline);
        if (!declW || !declH) {
          try {
            for (const sheet of document.styleSheets) {
              let rules; try { rules = sheet.cssRules; } catch (e) { continue; }   // 跨域样式表
              if (!rules) continue;
              for (const rule of rules) {
                if (!rule.selectorText || !rule.style) continue;
                if (!el.matches(rule.selectorText)) continue;
                if (rule.style.width) declW = true;
                if (rule.style.height) declH = true;
              }
            }
          } catch (e) { /* 样式表不可枚举时放弃，宁可漏报 */ }
        }
        if (!declW && !declH) continue;      // 没声明尺寸，那 inline 是有意的
        const bb = el.getBoundingClientRect();
        // 不设宽度下限：空的 inline span 被吞掉 width 后渲染宽度就是 0，圆点直接不可见——
        // 那是这个 bug 最典型的形态，恰恰不能过滤掉。只排除 display:none 之类真不该量的。
        if (cs.display === 'none' || cs.visibility === 'hidden' || +cs.opacity === 0) continue;
        timelineAlignment.deadDotStyles.push({
          sel: el.tagName.toLowerCase() + (el.className ? '.' + String(el.className).trim().split(/\s+/)[0] : ''),
          declaredWidth: declW, declaredHeight: declH,
          renderedWidth: Math.round(bb.width * 10) / 10, renderedHeight: Math.round(bb.height * 10) / 10,
          aspect: bb.height > 0 ? Math.round((bb.width / bb.height) * 100) / 100 : null,
          invisible: bb.width < 1 || bb.height < 1,
          borderRadius: cs.borderRadius, lineHeight: cs.lineHeight,
        });
      }
    }

    // 绝对定位的包含块：伪元素看宿主自身，真元素要从父级往上找（自身是 absolute 不代表它是自己的包含块）。
    // 除 position!=static 外，transform / filter / perspective 非 none 也会形成包含块。
    const containing = (host, fromSelf) => {
      let a = fromSelf ? host : host.parentElement;
      while (a && a !== document.documentElement) {
        const cs = getComputedStyle(a);
        if (cs.position !== 'static') break;
        if (cs.transform !== 'none' || cs.filter !== 'none' || cs.perspective !== 'none') break;
        a = a.parentElement;
      }
      return a || document.documentElement;
    };
    const boxOf = (host, pseudo) => {
      const cs = getComputedStyle(host, pseudo || null);
      if (pseudo && (cs.content === 'none' || cs.content === 'normal')) return null;
      const bl = num(cs.borderLeftWidth), br = num(cs.borderRightWidth);
      const bt = num(cs.borderTopWidth), bb = num(cs.borderBottomWidth);
      if (cs.display === 'none' || cs.visibility === 'hidden') return null;
      // 用户看不见的东西不参与对齐判定。**必须用 checkVisibility**：CSS opacity 不继承，
      // 祖先 opacity:0 时子元素的 computed opacity 仍是 1，只查自身会把「未揭示的滚动动画元素」
      // 当成正常元素量——它们还停在 translateX 的起始态，量出来的偏移是动画残留而非真实错位。
      try {
        if (host.checkVisibility && !host.checkVisibility({ opacityProperty: true, visibilityProperty: true })) return null;
      } catch (e) {}
      if (!pseudo) {
        const r = host.getBoundingClientRect();
        if (r.width <= 0 || r.height <= 0) return null;
        return { cx: r.left + r.width / 2, cy: r.top + r.height / 2, w: r.width, h: r.height,
                 cs, pseudo: '', anc: containing(host, false), borderX: bl, borderY: bt };
      }
      if (cs.position !== 'absolute') return null;      // 静态流伪元素无法据 left/top 推位置
      const pad = cs.boxSizing === 'border-box' ? 0 : 1;  // ← content-box 时 border 要额外计入外径
      const w = num(cs.width) + pad * (bl + br);
      const h = num(cs.height) + pad * (bt + bb);
      if (w <= 0 || h <= 0) return null;
      const anc = containing(host, true);
      const ar = anc.getBoundingClientRect();
      const acs = getComputedStyle(anc);
      const x0 = ar.left + num(acs.borderLeftWidth);
      const y0 = ar.top + num(acs.borderTopWidth);
      // 只写了 right / bottom 时，从包含块的 padding 盒尺寸倒推
      const innerW = ar.width - num(acs.borderLeftWidth) - num(acs.borderRightWidth);
      const innerH = ar.height - num(acs.borderTopWidth) - num(acs.borderBottomWidth);
      let l = parseFloat(cs.left), t = parseFloat(cs.top);
      if (isNaN(l)) { const rr = parseFloat(cs.right); if (!isNaN(rr)) l = innerW - rr - w; }
      if (isNaN(t)) { const bo = parseFloat(cs.bottom); if (!isNaN(bo)) t = innerH - bo - h; }
      const cx = isNaN(l) ? null : x0 + l + num(cs.marginLeft) + w / 2;
      const cy = isNaN(t) ? null : y0 + t + num(cs.marginTop) + h / 2;
      if (cx === null && cy === null) return null;
      return { cx, cy, w, h, cs, pseudo, anc, borderX: bl, borderY: bt };
    };
    // 轴线判向：窄而高 = 纵向时间轴（比中心 x）；宽而扁 = 横向时间轴（比中心 y）
    const axisDir = b => {
      if (b.w > 0 && b.w <= 6 && b.h >= 60 && b.cx !== null) return 'v';
      if (b.h > 0 && b.h <= 6 && b.w >= 60 && b.cy !== null) return 'h';
      return null;
    };
    const isDot = b => {
      if (b.w < 6 || b.w > 32 || Math.abs(b.w - b.h) > 3) return false;
      const r = b.cs.borderTopLeftRadius || '';
      if (r.indexOf('%') < 0 && num(r) < b.w / 2 - 1) return false;
      // 只认「被显式定位」的圆：节点圆点一定是 absolute 挂在 item 上，或 grid 里 justify-self 居中。
      // 图例色点、头像、图标那类装饰圆是普通流元素——实测就是它们造成误报，这里直接排除。
      return b.cs.position === 'absolute' || b.cs.justifySelf === 'center';
    };
    const label = (host, pseudo) =>
      host.tagName.toLowerCase() +
      (typeof host.className === 'string' && host.className ? '.' + host.className.trim().split(/\s+/)[0] : '') +
      pseudo;
    const shortSel = (el) => el.tagName.toLowerCase() +
      (typeof el.className === 'string' && el.className ? '.' + el.className.trim().split(/\s+/)[0] : '');

    for (const root of roots) {
      if (timelineAlignment.issues.length >= 6) break;
      const axes = { v: [], h: [] }, dots = [];
      const pool = [root].concat([].slice.call(root.querySelectorAll('*'), 0, 400));
      for (const el of pool) {
        for (const pseudo of ['', '::before', '::after']) {
          let b = null;
          try { b = boxOf(el, pseudo); } catch (e) { b = null; }
          if (!b) continue;
          const dir = axisDir(b);
          if (dir) axes[dir].push(Object.assign({ sel: label(el, pseudo) }, b));
          else if (isDot(b)) dots.push(Object.assign({ sel: label(el, pseudo) }, b));
        }
      }
      if (!dots.length) continue;
      for (const dir of ['v', 'h']) {
        const list = axes[dir];
        if (!list.length) continue;
        const key = dir === 'v' ? 'cx' : 'cy';
        // 主轴 = 沿轴方向最长那条
        const main = list.reduce((a, b) => (dir === 'v' ? (b.h > a.h ? b : a) : (b.w > a.w ? b : a)));
        // 先算出每个圆点的偏移，再做一致性归组。
        // 真实的对齐 bug 是**系统性**的——同一套 CSS 决定全部节点，实测负例都是 8/8、13/13 同一个偏移；
        // 孤立的离群值基本都是误判的装饰圆。只报「至少 2 个节点共同呈现」且落在轴线附近的那组。
        // 这条一致性要求同时挡掉了跨方向串味：纵向时间轴里若有装饰性横线，各节点相对它的 y 偏移互不相同，凑不成组。
        const groups = {};
        for (const d of dots) {
          if (d[key] === null) continue;
          // 圆点可能横跨多段轴线（多列/分段时间轴），取同方向上最近的一条比
          const near = list.reduce((a, b) => (Math.abs(b[key] - d[key]) < Math.abs(a[key] - d[key]) ? b : a), main);
          const off = d[key] - near[key];
          timelineAlignment.measured += 1;
          // 阈值 1.0px：人工盲测 37 个真实产物的结果——实测 0px 的 7 个全部判「不歪」，
          // 实测 0.5~1px 的 5 个judged「歪」，分界就在这里。再低会撞上亚像素舍入噪音。
          if (Math.abs(off) < 1.0) continue;
          if (Math.abs(off) > 60) continue;   // 离轴线太远，不是挂在这条轴上的节点
          const k = String(Math.round(off * 2) / 2);
          (groups[k] = groups[k] || []).push({ d: d, near: near, off: off });
        }
        const picked = Object.keys(groups).map(k => groups[k])
          .filter(g => g.length >= 2)
          .sort((a, b) => b.length - a.length)
          .slice(0, 2);
        for (const g of picked) {
          if (timelineAlignment.issues.length >= 6) break;
          const d = g[0].d, near = g[0].near, off = g[0].off;
          const dotBorder = dir === 'v' ? d.borderX : d.borderY;
          const ancPad = d.anc !== near.anc
            ? num(getComputedStyle(near.anc)[dir === 'v' ? 'paddingLeft' : 'paddingTop']) : 0;
          let reason = 'arithmetic';
          if (d.pseudo && d.cs.boxSizing === 'content-box' && dotBorder > 0 &&
              Math.abs(Math.abs(off) - dotBorder) <= 0.6) {
            reason = 'pseudo-content-box';
          } else if (d.anc !== near.anc && ancPad > 0 && Math.abs(Math.abs(off) - ancPad) <= 1.5) {
            // 只有偏移确实≈包含块的 padding 时才是"原点错位"；否则包含块不同只是写法差异，
            // 真正错的是手算的 left/top 值，别把 hint 里的修法指错方向。
            reason = 'origin-mismatch';
          }
          const rec = {
            orientation: dir === 'v' ? 'vertical' : 'horizontal',
            axis: near.sel, dot: d.sel,
            offsetPx: Math.round(off * 100) / 100,
            affectedDots: g.length,
            dotOuterSize: Math.round((dir === 'v' ? d.w : d.h) * 100) / 100,
            dotBoxSizing: d.cs.boxSizing,
            dotBorderWidth: dotBorder,
            reason: reason,
          };
          if (reason === 'origin-mismatch') {
            rec.axisOrigin = shortSel(near.anc);
            rec.dotOrigin = shortSel(d.anc);
            rec.axisOriginPadding = getComputedStyle(near.anc)[dir === 'v' ? 'paddingLeft' : 'paddingTop'];
          }
          timelineAlignment.issues.push(rec);
        }
      }
    }
  }
  // ============ 正文靠色：候选收集（判定在 python 侧做）============
  // **只收 <p>**：人工盲测 28 个真实产物的结论——低对比度的 span / div / a / button / small
  // （标签、徽章、序号、按钮、装饰小字）全部被判「不影响使用」，它们靠位置和形状就能识别；
  // 只有正文段落读不清才是真 bug。
  // 这里**不算背景色**：DOM 推不出真背景——渐变在页面不同位置颜色天差地别（同一页实测从
  // #f4ede0 米白到 #6d7275 深灰），伪元素色块和绝对定位覆盖层又不在祖先链上。真背景一律
  // 由 python 侧从已截好的图上采样，这里只交出前景色和坐标。
  const textCandidates = [];
  {
    const num = v => parseFloat(v) || 0;
    const parse = s => { const m = (s || '').match(/[\d.]+/g); if (!m) return null;
      const a = m.slice(0, 3).map(Number); a.push(m[3] !== undefined ? +m[3] : 1); return a; };
    const over = (f, b) => [0, 1, 2].map(i => f[i] * f[3] + b[i] * (1 - f[3])).concat([1]);
    // 伪元素画的色块（徽章圆底、hero 遮罩）不在 DOM 树里，向上遍历看不到
    const pseudoBg = el => {
      for (const ps of ['::before', '::after']) {
        const cs = getComputedStyle(el, ps);
        if (!cs || cs.content === 'none' || cs.content === 'normal') continue;
        if (cs.display === 'none' || cs.visibility === 'hidden' || num(cs.opacity) === 0) continue;
        if (cs.backgroundImage && cs.backgroundImage !== 'none') return true;
        const c = parse(cs.backgroundColor);
        if (c && c[3] > 0.05) return true;
      }
      return false;
    };
    // 绝对定位、铺满祖先的背景层（<div class="hero-bg"> 铺图，文字压在上面）
    const bgLayer = anc => {
      const ar = anc.getBoundingClientRect();
      if (ar.width < 1 || ar.height < 1) return false;
      for (const c of anc.children) {
        const cs = getComputedStyle(c);
        if (cs.position !== 'absolute' && cs.position !== 'fixed') continue;
        const r = c.getBoundingClientRect();
        if (r.width < ar.width * 0.85 || r.height < ar.height * 0.85) continue;
        if (c.tagName === 'IMG' || (cs.backgroundImage && cs.backgroundImage !== 'none')) return true;
        if (c.querySelector && c.querySelector('img')) return true;
      }
      return false;
    };
    // 只推导**纯色**背景：这条链路没有歧义，向上找到第一个不透明色即可。
    // 一旦遇到渐变 / 位图 / 伪元素色块 / 覆盖层就返回 null——那些必须靠像素采样，
    // 用 DOM 猜（比如取渐变色标平均色）实测会把「白字压深灰底、完全可读」误判成靠色。
    const solidBgOf = el => {
      let acc = null, a = el;
      while (a && a !== document.documentElement.parentElement) {
        const cs = getComputedStyle(a);
        if (cs.backgroundImage && cs.backgroundImage !== 'none') return null;
        if (bgLayer(a) || pseudoBg(a)) return null;
        const c = parse(cs.backgroundColor);
        if (c && c[3] > 0) { acc = acc ? over(acc, c) : c; if (c[3] >= 0.999) return acc; }
        a = a.parentElement;
      }
      return acc ? over(acc, [255, 255, 255, 1]) : [255, 255, 255, 1];
    };
    for (const el of document.querySelectorAll('p')) {
      if (textCandidates.length >= 80) break;
      let txt = '';
      for (const n of el.childNodes) if (n.nodeType === 3) txt += n.nodeValue;
      txt = txt.replace(/\s+/g, '');
      if (txt.length < 8) continue;                 // 短句多是标签式用法，不是要通读的正文
      const cs = getComputedStyle(el);
      if (cs.display === 'none' || cs.visibility === 'hidden') continue;
      try {
        if (el.checkVisibility && !el.checkVisibility({ opacityProperty: true, visibilityProperty: true })) continue;
      } catch (e) {}
      const rc = el.getBoundingClientRect();
      if (rc.width < 8 || rc.height < 8) continue;
      let op = 1;
      for (let a = el; a && a !== document.documentElement.parentElement; a = a.parentElement) op *= num(getComputedStyle(a).opacity);
      if (op < 0.5) continue;                       // 刻意淡化（未激活态），设计意图不是 bug
      if (num(cs.webkitTextStrokeWidth) > 0) continue;
      if (cs.textShadow && cs.textShadow !== 'none') continue;
      const clip = cs.webkitBackgroundClip || cs.backgroundClip || '';
      if (clip.indexOf('text') >= 0) continue;      // background-clip:text 渐变填充字
      const fg = parse(cs.color);
      if (!fg) continue;
      const solid = solidBgOf(el);
      textCandidates.push({
        text: txt.slice(0, 24),
        fg: [Math.round(fg[0]), Math.round(fg[1]), Math.round(fg[2])],
        fgAlpha: Math.round(fg[3] * 1000) / 1000,
        opacity: Math.round(op * 1000) / 1000,
        fontSizePx: Math.round(num(cs.fontSize)),
        solidBg: solid ? [Math.round(solid[0]), Math.round(solid[1]), Math.round(solid[2])] : null,
        x: Math.round(rc.left + scrollX), y: Math.round(rc.top + scrollY),
        w: Math.round(rc.width), h: Math.round(rc.height),
      });
    }
  }
  const docSize = { w: document.documentElement.scrollWidth, h: document.documentElement.scrollHeight };

  // ============ 图表容器尺寸收集 ============
  // 只做「收集」，不判断——判断在 python 侧跨视口对比时做。
  // 目标：echarts 初始化后的容器（div[_echarts_instance_]），以及未被 echarts 包裹的
  // 独立 <canvas> / <svg> 且尺寸达到「图表级」阈值（80×60）的元素。
  // 输出按 DOM 顺序编号，便于跨视口按 idx 匹配；有 id 时以 id 匹配优先。
  const chartContainers = [];
  {
    const set = new Set();
    document.querySelectorAll('[_echarts_instance_]').forEach(el => set.add(el));
    document.querySelectorAll('canvas, svg').forEach(el => {
      if (el.closest('[_echarts_instance_]')) return; // 已由 echarts 容器代表
      const r = el.getBoundingClientRect();
      if (r.width < 80 || r.height < 60) return; // 图标 / 装饰 svg 忽略
      set.add(el);
    });
    const ordered = Array.from(set).sort((a, b) => {
      const pos = a.compareDocumentPosition(b);
      if (pos & Node.DOCUMENT_POSITION_FOLLOWING) return -1;
      if (pos & Node.DOCUMENT_POSITION_PRECEDING) return 1;
      return 0;
    });
    for (const el of ordered) {
      const r = el.getBoundingClientRect();
      if (r.width < 2 || r.height < 2) continue;
      const cs = getComputedStyle(el);
      if (cs.visibility === 'hidden' || cs.display === 'none' || +cs.opacity === 0) continue;
      const cls = (el.className && el.className.baseVal !== undefined)
        ? el.className.baseVal
        : (typeof el.className === 'string' ? el.className : '');
      chartContainers.push({
        idx: chartContainers.length,
        id: el.id || '',
        tag: el.tagName.toLowerCase(),
        cls: (cls || '').toString().split(/\s+/).filter(Boolean).slice(0, 2).join(' '),
        width: Math.round(r.width),
        height: Math.round(r.height),
      });
    }
  }

  // 规则 5：SVG 用 href 而非 xlink:href（file:// 兼容硬红线）
  // 背景：Chrome 在 file:// 下会把 <use href="#id"> / <textPath href="#id"> 视为
  //   "Unsafe attempt to load URL"，同步中断当前 script 执行。表现是页面后段 JS 不跑（图表空、卡片空）。
  //   SVG1.1 的 xlink:href 兼容 file://，且现代浏览器同样识别。
  const unsafeHrefRefs = [];
  {
    const nodes = document.querySelectorAll('svg use[href], svg textPath[href]');
    for (const el of nodes) {
      if (unsafeHrefRefs.length >= 20) break;
      // 已有 xlink:href 的不报（同时写两个是兼容写法）
      const xh = el.getAttributeNS('http://www.w3.org/1999/xlink', 'href');
      if (xh) continue;
      const href = el.getAttribute('href') || '';
      // 只对 fragment 引用 (#id) 报 —— 外链 URL 用 href 不触发本 bug
      if (!href.startsWith('#')) continue;
      unsafeHrefRefs.push({
        tag: el.tagName.toLowerCase(),
        target: href.slice(0, 60),
      });
    }
  }

  // 规则 6：可能"看不见的动效元素" —— 初态被藏、但缺乏 CSS 过渡兜底
  // 目标：抓那种 opacity:0 / visibility:hidden / clip-path 藏起来等 JS 挂 class 揭出的元素，
  //   如果 JS 出错、IO 未触发、user gesture 未来，用户永远看不到内容。
  // 判据：元素处于 hidden 态 + 有 .rv/.reveal/.fade/.chart-fig 之类类名前缀 + 无 transition 属性。
  //   仅报有可见文字或子孙有图表/canvas 的元素（纯装饰不管）。
  const invisibleAnimations = [];
  {
    const revealClassRe = /(^|\s)(rv|reveal|fade|chart-fig|bee-fig|ridge-fig|bump-fig|cal-fig|slope-fig)(\s|$|-)/;
    const all = document.querySelectorAll('body *');
    for (const el of all) {
      if (invisibleAnimations.length >= 15) break;
      const cs = getComputedStyle(el);
      if (cs.display === 'none') continue;
      const op = parseFloat(cs.opacity);
      const isHidden = (op === 0) || cs.visibility === 'hidden';
      // 也抓 clip-path: inset(0 100% 0 0) 之类横切
      const cp = cs.clipPath || '';
      const clippedByPath = cp.startsWith('inset(') && /100%|0px 100%|100% 0/.test(cp);
      if (!isHidden && !clippedByPath) continue;
      // 有 CSS transition 或 animation 兜底的不算——真会自动揭出
      const hasTrans = cs.transitionProperty && cs.transitionProperty !== 'none' &&
                       parseFloat(cs.transitionDuration || '0') > 0;
      const hasAnim = cs.animationName && cs.animationName !== 'none';
      if (hasTrans || hasAnim) continue;
      // 类名启发式：有典型 reveal class 才报，减少误伤
      const cls = (el.className && el.className.baseVal !== undefined)
        ? el.className.baseVal
        : (typeof el.className === 'string' ? el.className : '');
      if (!revealClassRe.test(cls || '')) continue;
      // 有内容才值得报——纯装饰容器忽略
      const txt = (el.textContent || '').trim();
      const hasChart = el.querySelector && el.querySelector('canvas, svg, .chart, [class*="chart"]');
      if (txt.length < 4 && !hasChart) continue;
      const r = el.getBoundingClientRect();
      if (r.width < 4 || r.height < 4) continue;
      invisibleAnimations.push({
        tag: el.tagName.toLowerCase(),
        cls: (cls || '').toString().split(/\s+/).filter(Boolean).slice(0, 3).join(' '),
        text: txt.slice(0, 60),
        reason: isHidden ? (op === 0 ? 'opacity:0' : 'visibility:hidden') : 'clip-path-inset',
        rect: [Math.round(r.left + window.scrollX), Math.round(r.top + window.scrollY), Math.round(r.width), Math.round(r.height)],
      });
    }
  }

  // 规则 7：slop 高发字体（Inter / Roboto / Arial / Fraunces / Playfair）
  // 只报"实际参与渲染的字体"——computed fontFamily 的首选族，忽略 fallback 尾部。
  const slopFonts = [];
  {
    const blocklist = ['inter', 'roboto', 'arial', 'fraunces', 'playfair'];
    const seen = new Map(); // family -> {count, sampleText}
    const els = document.querySelectorAll('body h1, body h2, body h3, body p, body li, body span, body div, body a, body button');
    for (const el of els) {
      if (!el.textContent || !el.textContent.trim()) continue;
      const cs = getComputedStyle(el);
      // fontFamily 是 "族1", "族2", fallback 形式，取首选并去引号
      const first = (cs.fontFamily || '').split(',')[0].replace(/["']/g, '').trim().toLowerCase();
      if (!first) continue;
      const hit = blocklist.find(b => first === b || first.startsWith(b + ' '));
      if (!hit) continue;
      const rec = seen.get(hit) || { count: 0, sampleText: '' };
      rec.count += 1;
      if (!rec.sampleText) rec.sampleText = (el.textContent || '').trim().slice(0, 40);
      seen.set(hit, rec);
    }
    for (const [family, rec] of seen) {
      slopFonts.push({ family: family, elementCount: rec.count, sampleText: rec.sampleText });
    }
  }

  // 规则 8：emoji 出现
  // 匹配 Unicode Emoji_Presentation 平面的常见范围。ZWJ 序列、肤色调节符可能触发多次同一位置，去重。
  const emojiUsage = [];
  {
    // BMP 象形文字（云、雪花、剪刀等）+ Emoji 附加平面 + 变体选择符 U+FE0F 上文出现的 dingbat/symbols
    // 精简处理：直接匹配典型 emoji 平面 [\u{1F300}-\u{1FAFF}] 与 [\u{2600}-\u{27BF}]。
    const re = /[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/u;
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null);
    let n, hits = 0;
    while ((n = walker.nextNode()) && hits < 15) {
      const t = n.nodeValue || '';
      if (!re.test(t)) continue;
      const parent = n.parentElement;
      if (!parent) continue;
      const cs = getComputedStyle(parent);
      if (cs.display === 'none' || cs.visibility === 'hidden' || +cs.opacity === 0) continue;
      // 抓出实际的匹配片段
      const m = t.match(/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/gu) || [];
      emojiUsage.push({
        tag: parent.tagName.toLowerCase(),
        chars: m.slice(0, 8).join(''),
        contextText: t.trim().slice(0, 60),
      });
      hits++;
    }
  }

  // 是否移动端 shot —— 决定后续几条规则是否启用
  const isMobile = vw < 500;

  // 规则 9：viewport meta 缺失（无视口尺寸都要查，硬错）
  // <meta name="viewport" content="width=device-width, ..."> 缺失时，移动端浏览器
  // 会以 980px 假 viewport 渲染再缩放，页面在真机上全部变小、字如蚂蚁。
  const viewportMeta = (() => {
    const m = document.querySelector('meta[name="viewport"]');
    if (!m) return { present: false };
    const content = (m.getAttribute('content') || '').toLowerCase();
    const hasDeviceWidth = /width\s*=\s*device-width/.test(content);
    const scalableNo = /user-scalable\s*=\s*no/.test(content) ||
                       /maximum-scale\s*=\s*1(\.0)?\b/.test(content);
    return { present: true, hasDeviceWidth: hasDeviceWidth, disablesZoom: scalableNo, content: content.slice(0, 200) };
  })();

  // 规则 10：触控目标过小（仅 mobile shot 启用）
  // iOS HIG 44×44、Material 48×48。取 44 作为下限，命中即报。
  // 只查真正的可交互元素：<button>, <a>, [role=button], input[type=button|submit|checkbox|radio], [onclick]
  const touchTargetTooSmall = [];
  if (isMobile) {
    const sel = 'button, a[href], input[type="button"], input[type="submit"], input[type="checkbox"], input[type="radio"], [role="button"], [onclick]';
    const nodes = document.querySelectorAll(sel);
    for (const el of nodes) {
      if (touchTargetTooSmall.length >= 20) break;
      const cs = getComputedStyle(el);
      if (cs.display === 'none' || cs.visibility === 'hidden' || +cs.opacity === 0) continue;
      if (cs.pointerEvents === 'none') continue;
      const r = el.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) continue;
      // 忽略 inline 链接（在段落里的正文超链接，天然是 line-height 高度，不适用 44 规则）
      // 判断：<a> 元素、父元素 display 是 inline / block、且元素本身 display 是 inline
      // 简单启发：<a> 的 display 是 inline 且高度 < 26（约一行）
      if (el.tagName === 'A' && cs.display.startsWith('inline') && r.height < 26) continue;
      const tooNarrow = r.width < 44;
      const tooShort = r.height < 44;
      if (!tooNarrow && !tooShort) continue;
      const txt = (el.textContent || '').trim();
      touchTargetTooSmall.push({
        tag: el.tagName.toLowerCase(),
        text: txt.slice(0, 40),
        width: Math.round(r.width),
        height: Math.round(r.height),
        rect: [Math.round(r.left + window.scrollX), Math.round(r.top + window.scrollY), Math.round(r.width), Math.round(r.height)],
      });
    }
  }

  // 规则 11：写死宽度的元素（仅 mobile shot 启用）
  // computed width 是绝对 px、宽度 > viewport、CSS 里显式设了 width（非 100% / auto / max-content 之类）——
  //   这类元素在小屏必爆。抓 inline style 的 width、或者作者样式表里的绝对 px 宽度。
  // 局限：读不到 CSS rule 具体值，只能从 inline style + computed 反推。
  const fixedWidthElements = [];
  if (isMobile) {
    const all = document.querySelectorAll('body *');
    for (const el of all) {
      if (fixedWidthElements.length >= 15) break;
      // 跳过 SVG 内部元素：<rect> / <circle> / <path> / <text> 等在 SVG 命名空间里的 width 不参与页面 layout
      if (el.namespaceURI && el.namespaceURI !== 'http://www.w3.org/1999/xhtml') continue;
      const inlineWidth = (el.style && el.style.width) || '';
      // 只关心 inline 显式写 px 或 computed width > viewport 且比父元素还宽
      const cs = getComputedStyle(el);
      if (cs.display === 'none' || cs.visibility === 'hidden' || +cs.opacity === 0) continue;
      const w = parseFloat(cs.width);
      if (!w || w <= vw) continue;
      // 排除 overflow 容器（swiper / marquee / scroller 故意宽于视口）—— 沿祖先链找
      let anc = el.parentElement, inScroller = false;
      while (anc && anc !== document.body) {
        const acs = getComputedStyle(anc);
        if (acs.overflowX === 'auto' || acs.overflowX === 'scroll' ||
            acs.overflowX === 'hidden' || acs.overflowX === 'clip') {
          inScroller = true; break;
        }
        anc = anc.parentElement;
      }
      if (inScroller) continue;
      // 排除 body / html
      if (el === document.body || el === document.documentElement) continue;
      const r = el.getBoundingClientRect();
      if (r.width < 40) continue;
      // 判断 css 是不是 px 写死（启发：inline style 里有 px，或 computed 值明显不响应）
      const inlineIsPx = /\d+\s*px\s*$/i.test(inlineWidth);
      const inlineIsPct = /%\s*$/.test(inlineWidth);
      // computed value 是 px、且没有 inline % —— 视为可能写死
      const suspicious = inlineIsPx || (!inlineIsPct && !inlineWidth);
      if (!suspicious) continue;
      fixedWidthElements.push({
        tag: el.tagName.toLowerCase() + (el.className ? '.' + String(el.className).split(/\s+/)[0] : ''),
        text: (el.textContent || '').trim().slice(0, 40),
        computedWidth: Math.round(w),
        viewportWidth: vw,
        inlineWidth: inlineWidth || null,
      });
    }
  }

  // 规则 12：移动端字体问题（仅 mobile shot 启用）
  // (a) 正文文字 < 14px：手机上难读
  // (b) <input> / <textarea> font-size < 16px：iOS Safari 聚焦时会自动缩放（贼恶心的跳一下）
  const mobileFontIssues = [];
  if (isMobile) {
    // (a) 正文字号
    const textEls = document.querySelectorAll('body p, body li, body td, body span, body div');
    const seenSmallText = new Set();
    for (const el of textEls) {
      if (mobileFontIssues.length >= 15) break;
      // 只取有直接文本节点（非只有子元素）的 —— 避免整个 wrapper 也被算进去
      let hasDirectText = false;
      for (const child of el.childNodes) {
        if (child.nodeType === 3 && (child.nodeValue || '').trim().length > 0) { hasDirectText = true; break; }
      }
      if (!hasDirectText) continue;
      const cs = getComputedStyle(el);
      if (cs.display === 'none' || cs.visibility === 'hidden' || +cs.opacity === 0) continue;
      const fs = parseFloat(cs.fontSize);
      if (!fs || fs >= 14) continue;
      const txt = (el.textContent || '').trim().slice(0, 40);
      if (seenSmallText.has(txt)) continue;
      seenSmallText.add(txt);
      mobileFontIssues.push({
        kind: 'small-body-text',
        tag: el.tagName.toLowerCase(),
        fontSize: Math.round(fs * 10) / 10,
        text: txt,
      });
    }
    // (b) 输入框字号 < 16 —— iOS 聚焦缩放 bug
    const inputs = document.querySelectorAll('input[type="text"], input[type="search"], input[type="email"], input[type="url"], input[type="tel"], input[type="password"], input[type="number"], input:not([type]), textarea');
    for (const el of inputs) {
      if (mobileFontIssues.length >= 15) break;
      const cs = getComputedStyle(el);
      if (cs.display === 'none' || cs.visibility === 'hidden' || +cs.opacity === 0) continue;
      const fs = parseFloat(cs.fontSize);
      if (!fs || fs >= 16) continue;
      mobileFontIssues.push({
        kind: 'input-under-16px',
        tag: el.tagName.toLowerCase() + (el.type ? '[type=' + el.type + ']' : ''),
        fontSize: Math.round(fs * 10) / 10,
        text: (el.placeholder || el.value || '').slice(0, 40),
      });
    }
  }

  // 规则 13：正文文字贴视口边缘（仅 mobile shot 启用）
  // 最高频成因是 padding 简写把继承来的左右内边距清零：
  //   .wrap{max-width:1180px;margin:0 auto;padding:0 28px}   ← 通用容器，左右 28px
  //   .hero-inner{padding:88px 0 96px}                        ← 只想加上下，简写把左右一起清零
  // 元素同时挂两个 class 时后写的简写胜出。宽屏下 margin:0 auto 的居中边距掩盖了它
  // （1440 时 (1440-1180)/2 = 130px，看起来完美），视口一旦 ≤ max-width 居中边距归零，
  // padding 又是 0，文字直接贴边 —— 所以只在 mobile shot 能抓到，desktop 永远正常。
  // 与规则 11 不重叠：规则 11 查「元素比视口宽」的溢出，这里的容器宽度恰好等于视口、完全不溢出。
  const edgeHuggingText = [];
  if (isMobile) {
    const t0 = Date.now(), BUDGET = 1200;      // 硬预算：文本节点极多的页面宁可少报也不能拖慢自检
    const csCache = new Map();
    const CS = el => { let v = csCache.get(el); if (!v) { v = getComputedStyle(el); csCache.set(el, v); } return v; };
    // 阶段一：快扫，只量文字矩形不读祖先（读祖先 computed style 是 O(n·depth)，会拖到分钟级）
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const rng = document.createRange();
    const cand = [];
    let node, scanned = 0;
    while ((node = walker.nextNode())) {
      if ((++scanned & 255) === 0 && Date.now() - t0 > BUDGET * 0.6) break;
      const raw = node.textContent;
      if (!raw || raw.trim().length < 2) continue;
      const p = node.parentElement; if (!p) continue;
      rng.selectNodeContents(node);
      const rects = rng.getClientRects();
      for (let i = 0; i < rects.length; i++) {
        const r = rects[i];
        if (r.width < 8 || r.height < 6) continue;
        // 阈值 1px（亚像素容差）。padding 塌陷造成的贴边 left 精确等于 0；
        // 实测 left=4px 的那例是 text-align:center 的长文本两侧各余 4px，属正常，放宽到 4 会误报。
        if (r.left <= 1) { cand.push({ el: p, left: r.left, right: r.right, txt: raw.trim().slice(0, 30) }); break; }
      }
      if (cand.length >= 40) break;
    }
    // 阶段二：只对候选查祖先链，排掉「刻意移出视口」的
    // 移动端收起的抽屉/侧边栏、无障碍 skip link（left:-9999px）、绝对定位 badge 都长这样
    const exemptReason = (el) => {
      let a = el, d = 0;
      while (a && a !== document.documentElement && d++ < 20) {
        const cs = CS(a);
        if (cs.display === 'none' || cs.visibility === 'hidden' || +cs.opacity === 0) return 'invisible';
        if (cs.position === 'fixed' || cs.position === 'absolute' || cs.position === 'sticky') return cs.position;
        const tr = cs.transform;
        if (tr && tr !== 'none') {
          const m = tr.match(/matrix\(([^)]+)\)/);
          if (m && Number(m[1].split(',')[4]) < -1) return 'translated-x';
        }
        if (parseFloat(cs.left) < -40) return 'left-off-screen';
        a = a.parentElement;
      }
      return null;
    };
    const seenEdge = new Set();
    for (const c of cand) {
      if (edgeHuggingText.length >= 8 || Date.now() - t0 > BUDGET) break;
      if (exemptReason(c.el)) continue;
      const cs = CS(c.el), pa = c.el.parentElement, pcs = pa ? CS(pa) : null;
      const sel = c.el.tagName.toLowerCase() + (c.el.className ? '.' + String(c.el.className).trim().split(/\s+/)[0] : '');
      if (seenEdge.has(sel)) continue;
      seenEdge.add(sel);
      edgeHuggingText.push({
        tag: sel,
        text: c.txt,
        left: Math.round(c.left),
        viewportWidth: vw,
        paddingLeft: cs.paddingLeft,
        parentTag: pa ? pa.tagName.toLowerCase() + (pa.className ? '.' + String(pa.className).trim().split(/\s+/)[0] : '') : null,
        parentPaddingLeft: pcs ? pcs.paddingLeft : null,
        parentMarginLeft: pcs ? pcs.marginLeft : null,
        parentMaxWidth: pcs ? pcs.maxWidth : null,
      });
    }
  }

  return {
    structure: {
      title: document.title,
      firstH1: (document.querySelector('h1')||{}).textContent?.trim().slice(0, 80) || '',
      viewport: { w: vw, h: vh },
      fullpage: { w: fw, h: fh },
      counts: {
        section: document.querySelectorAll('section').length,
        h1: document.querySelectorAll('h1').length,
        h2: document.querySelectorAll('h2').length,
        img: document.querySelectorAll('img').length,
        canvas: document.querySelectorAll('canvas').length,
        svg: document.querySelectorAll('svg').length,
        links: document.querySelectorAll('a').length,
        buttons: document.querySelectorAll('button').length,
      },
    },
    horizontalOverflow: overflow,
    fontFailures: fontFailures,
    localImages: localImages,
    stretchedImages: stretchedImages,
    overlappingText: overlappingText,
    clippedText: clippedText,
    pseudoOverflow: pseudoOverflow,
    deadButtons: deadButtons,
    misalignedBlocks: misalignedBlocks,
    unevenColumns: unevenColumns,
    timelineAlignment: timelineAlignment,
    textCandidates: textCandidates,
    docSize: docSize,
    chartContainers: chartContainers,
    unsafeHrefRefs: unsafeHrefRefs,
    invisibleAnimations: invisibleAnimations,
    slopFonts: slopFonts,
    emojiUsage: emojiUsage,
    viewportMeta: viewportMeta,
    touchTargetTooSmall: touchTargetTooSmall,
    fixedWidthElements: fixedWidthElements,
    edgeHuggingText: edgeHuggingText,
    mobileFontIssues: mobileFontIssues,
    isMobileShot: isMobile,
  };
}
"""


def to_url(src: str) -> str:
    if src.startswith(("http://", "https://", "file://")):
        return src
    p = Path(src).resolve()
    if not p.exists():
        raise ValueError(f"文件不存在: {p}")
    return p.as_uri()


def slug(src: str) -> str:
    if src.startswith(("http://", "https://")):
        host = urlparse(src).hostname or "page"
        return host.replace(".", "_")
    return Path(src).stem


def parse_size(s: str):
    w, h = s.lower().split("x")
    return int(w), int(h)


def _postprocess(out_path: Path, max_width: int, jpeg_quality: int, fmt: str,
                 slice_over_kb: int, slice_over_height: int, slice_height: int) -> dict:
    """截图后处理：JPEG 转码 + 可选降宽；单张仍超阈值时按 slice_height 切片。

    - 缺 Pillow 时优雅降级：只做 JPEG 转码或返回原 PNG，slice 跳过。
    - 返回 {"path": 主图, "slices": [子图路径...], "bytes": 主图字节数}。
    """
    def _size_kb(p): return p.stat().st_size // 1024

    # 用户显式要 PNG 且不需降宽：直接返回原图
    if fmt == "png" and max_width <= 0:
        return {"path": out_path, "slices": [], "bytes": out_path.stat().st_size}

    try:
        from PIL import Image  # type: ignore
    except Exception:
        return {"path": out_path, "slices": [], "bytes": out_path.stat().st_size}

    # 主图转码 + 降宽
    # Pillow 9.1+ 用 Image.Resampling.LANCZOS；11.0 移除旧常量。做前瞻兜底。
    _LANCZOS = getattr(getattr(Image, "Resampling", Image), "LANCZOS", None) or Image.LANCZOS
    with Image.open(out_path) as im:
        w, h = im.size
        if max_width and w > max_width:
            new_h = round(h * max_width / w)
            im = im.resize((max_width, new_h), _LANCZOS)
        if fmt == "jpg":
            # 有 alpha 的模式（含调色板 P）先规一化到 RGBA，再往白底 paste
            # 直接 paste P 模式会把索引值当 RGB 用，颜色乱
            if im.mode in ("RGBA", "LA", "P"):
                im = im.convert("RGBA")
                bg = Image.new("RGB", im.size, (255, 255, 255))
                bg.paste(im, mask=im.split()[-1])
                im = bg
            main_path = out_path.with_suffix(".jpg")
            im.save(main_path, "JPEG", quality=jpeg_quality, optimize=True, progressive=True)
        else:
            main_path = out_path
            im.save(main_path, "PNG", optimize=True)
    if main_path != out_path and out_path.exists():
        out_path.unlink()

    # 主图切片：字节超阈值 或 高度超阈值 任一命中就切
    slices = []
    with Image.open(main_path) as _probe:
        main_h = _probe.size[1]
    over_bytes = slice_over_kb > 0 and _size_kb(main_path) > slice_over_kb
    over_height = slice_over_height > 0 and main_h > slice_over_height
    if over_bytes or over_height:
        with Image.open(main_path) as im:
            w, h = im.size
            n = (h + slice_height - 1) // slice_height
            stem = main_path.stem
            for i in range(n):
                top = i * slice_height
                bot = min(top + slice_height, h)
                crop = im.crop((0, top, w, bot))
                sp = main_path.with_name(f"{stem}_p{i+1}of{n}{main_path.suffix}")
                if main_path.suffix.lower() in (".jpg", ".jpeg"):
                    crop.save(sp, "JPEG", quality=jpeg_quality, optimize=True, progressive=True)
                else:
                    crop.save(sp, "PNG", optimize=True)
                slices.append(sp)

    return {"path": main_path, "slices": slices, "bytes": main_path.stat().st_size}


def _wcag_lum(c):
    def ch(v):
        v /= 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(c[0]) + 0.7152 * ch(c[1]) + 0.0722 * ch(c[2])


def _wcag_ratio(a, b):
    l1, l2 = _wcag_lum(a), _wcag_lum(b)
    return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)


def _dominant_bg(img, box):
    """取矩形内的主背景色：**量化到 32 级后取最大色簇，再在簇内按像素数加权平均**。

    不能直接取原始众数：渐变背景下每个像素颜色都略有不同，没有任何单一色值占主导，
    反而是文字抗锯齿的某个中间色偶然聚成最大簇——实测一个 1440×58 的深蓝渐变段落，
    原始众数取到 #e9edf7（仅占 0.8% 像素）、算出 1.17 的假靠色，而实际是白字压
    #23459c 深蓝、对比度 8.74 完全可读。量化把相近色并成一簇后判对。
    纯色背景不受影响：簇内只有一个色值，加权平均就是它本身。

    返回 `(颜色, 最大簇的像素占比)`。占比是必要的可信度信号：众数只有在「背景占主导」
    时才代表背景。实测一段压在咖啡馆照片上的深褐正文（520×97、三行 18px），照片颜色
    高度分散、每簇不到 3%，反倒是集中的文字笔画成了最大簇（占 6%），采出的"背景色"
    正好等于文字色、算出 1.00 的假靠色；而真正同色的正文（#898989 压 #888888）
    最大簇占 100%。
    """
    x, y, w, h = box
    try:
        colors = img.crop((x, y, x + w, y + h)).getcolors(maxcolors=1 << 20)
    except Exception:
        return None
    if not colors:
        return None
    buckets = {}
    for n, c in colors:
        if not isinstance(c, tuple) or len(c) < 3:
            continue
        k = (c[0] >> 3, c[1] >> 3, c[2] >> 3)
        b = buckets.get(k)
        if b is None:
            buckets[k] = [n, c[0] * n, c[1] * n, c[2] * n]
        else:
            b[0] += n; b[1] += c[0] * n; b[2] += c[1] * n; b[3] += c[2] * n
    if not buckets:
        return None
    total = sum(b[0] for b in buckets.values()) or 1
    best = max(buckets.values(), key=lambda b: b[0])
    return ([best[1] / best[0], best[2] / best[0], best[3] / best[0]], best[0] / total)


def _group_by_band(items, band):
    """按 y 贪心分组：落在同一个 band 高度窗口内的候选共用一张 clip 图，控制截图次数。"""
    groups, cur, cur_top = [], [], None
    for c in sorted(items, key=lambda x: x.get("y", 0)):
        y = c.get("y", 0)
        if cur_top is None or y + c.get("h", 0) - cur_top > band:
            if cur:
                groups.append((cur_top, cur))
            cur, cur_top = [c], y
        else:
            cur.append(c)
    if cur:
        groups.append((cur_top, cur))
    return groups


def sample_text_contrast(page, cands, doc_size, threshold=1.6, limit=6, max_shots=16):
    """采样正文段落的**实际渲染背景色**，算 WCAG 对比度。

    为什么背景色必须从像素拿、不能用 DOM 推：渐变在页面不同位置颜色天差地别
    （同一页实测从 #f4ede0 米白到 #6d7275 深灰），按「渐变色标平均色」算会把
    「白字压深灰底、完全可读」误判成靠色；伪元素色块（徽章圆底）和绝对定位的
    覆盖层（<div class="hero-bg">）更不在祖先链上，向上遍历只会拿到底层浅色。

    为什么不复用主截图：`full_page=True` 在超过 Chrome 16384px 纹理上限的页面上
    **内容与坐标错位**——实测 138 个真实产物里 6 个超限、其中 5 个底部内容不对
    （21447px 那页的图底部显示的是中段图表而非 footer）。所以这里按候选元素分组、
    用 `clip` 单独取图；clip 会先滚动到目标区域，实测在超长页上准确。

    取元素矩形内的**众数颜色**作为背景——文字笔画只占少数像素，背景占多数。
    """
    if not cands or page is None:
        return []
    try:
        from PIL import Image           # 没装 Pillow 就静默跳过这条规则，不影响其它 lint
    except Exception:
        return []
    dw = (doc_size or {}).get("w") or 0
    if dw <= 0:
        return []

    try:
        vp_h = int((page.viewport_size or {}).get("height") or 900)
    except Exception:
        vp_h = 900
    band = max(400, vp_h)

    seen, out, dropped, shot_failed = {}, [], 0, 0
    _sample_err = [None]

    def _judge(c, bg):
        fg = [float(v) for v in c["fg"]]
        a = float(c.get("fgAlpha", 1)) * float(c.get("opacity", 1))
        if a < 0.999:                   # 半透明文字的实际渲染色 = 前景以 a 混到背景上
            fg = [fg[i] * a + bg[i] * (1 - a) for i in range(3)]
        cr = _wcag_ratio(fg, bg)
        # 不设下限。曾经把 cr < 1.06 当「描边空心字之类，靠别的机制可见」跳过，那是错的：
        # 候选收集阶段已经排除了 -webkit-text-stroke / text-shadow / background-clip:text，
        # 能走到这里的近同色文字只可能是**真的读不出来的正文**（实测 #898989 压 #888888
        # 的普通 <p> 就因此被静默）。这恰好是最严重的形态——通常是文字色变量被误用成了
        # 跟背景相近的值。
        if cr >= threshold:
            return
        key = (tuple(int(round(v)) for v in fg), tuple(int(v) for v in bg))
        if key in seen:
            seen[key]["count"] += 1
            return
        rec = {
            "text": c.get("text", ""),
            "color": "#%02x%02x%02x" % tuple(int(round(v)) for v in fg),
            "background": "#%02x%02x%02x" % tuple(int(v) for v in bg),
            "contrastRatio": round(cr, 2),
            "fontSizePx": c.get("fontSizePx"),
            "count": 1,
        }
        seen[key] = rec
        out.append(rec)

    # 分流：DOM 能推出纯色背景的直接判（无歧义、零开销），只有渐变 / 位图 /
    # 伪元素色块 / 覆盖层底下的文字才需要截图采样——那部分才是 DOM 猜不准的。
    need_shot = []
    for c in cands:
        if c.get("solidBg"):
            _judge(c, [float(v) for v in c["solidBg"]])
        else:
            need_shot.append(c)

    if need_shot:
        for gi, (top, items) in enumerate(_group_by_band(need_shot, band)):
            if gi >= max_shots:
                dropped += len(items)
                continue
            bottom = max(c.get("y", 0) + c.get("h", 0) for c in items)
            h = max(2, min(band, bottom - top + 4))
            try:
                # clip 的坐标语义取决于 full_page：**必须** full_page=True，此时 clip 才是
                # 文档坐标；不带则是视口坐标，而这里传的 y 来自 rc.top + scrollY，
                # 去掉 full_page 会稳定抛 "Clipped area is either empty or outside the
                # resulting image"（实测 800x600 视口取文档 y=2200 即复现）。
                raw = page.screenshot(full_page=True, type="png",
                                      clip={"x": 0, "y": max(0, top - 2), "width": dw, "height": h})
                img = Image.open(io.BytesIO(raw)).convert("RGB")
            except Exception as e:
                # 不能纯静默：采样失败会让渐变 / 图片背景上的靠色整片查不出来，
                # 而报告里看不出任何异常。计数并留下首个错误，交给调用方报出去。
                shot_failed += 1
                if _sample_err[0] is None:
                    _sample_err[0] = str(e)[:160]
                continue
            for c in items:
                x = int(c.get("x", 0))
                y = int(c.get("y", 0)) - max(0, top - 2)
                w, hh = max(2, int(c.get("w", 0))), max(2, int(c.get("h", 0)))
                if x < 0 or y < 0 or x >= img.size[0] or y >= img.size[1]:
                    continue
                w, hh = min(w, img.size[0] - x), min(hh, img.size[1] - y)
                if w < 2 or hh < 2:
                    continue
                got = _dominant_bg(img, (x, y, w, hh))
                if got is None:
                    continue
                bg, share = got
                # 最大簇跟前景几乎同色时，它可能根本不是背景、而是文字笔画本身——
                # 只有在这个簇确实占主导时才采信。照片 / 复杂图案背景下颜色高度分散，
                # 集中的文字色反而成为最大簇（实测占 6%），采信它就是假靠色；
                # 真正的同色正文里背景占绝大多数（实测 100%）。占比不足就放弃这个元素，
                # 宁可漏报也不误报。
                if _wcag_ratio([float(v) for v in c["fg"]], bg) < 1.1 and share < 0.30:
                    continue
                _judge(c, bg)

    out.sort(key=lambda r: r["contrastRatio"])
    if shot_failed:
        diag = f"{shot_failed} 组候选的背景采样截图失败（首个错误：{_sample_err[0]}），这些段落未被检测"
        if out:
            out[0].setdefault("_note", diag)
        else:
            return [{"_samplingFailed": shot_failed, "_note": diag}]
    if dropped and out:
        out[limit - 1 if len(out) >= limit else len(out) - 1]["_note"] = (
            f"页面过长，另有 {dropped} 个渐变/图片背景上的段落未采样")
    return out[:limit]


def one_shot(page, viewport, url, out_path, console_bucket, resource_bucket,
             max_width, jpeg_quality, fmt, slice_over_kb, slice_over_height, slice_height, include,
             eval_code=None):
    w, h = viewport
    page.set_viewport_size({"width": w, "height": h})
    try:
        page.emulate_media(reduced_motion="reduce")
    except TypeError:
        pass  # playwright < 1.25 不支持 reduced_motion
    try:
        page.goto(url, wait_until="networkidle", timeout=30_000)
    except Exception:
        # networkidle 达不到时退回 domcontentloaded，别死等
        page.goto(url, wait_until="domcontentloaded", timeout=30_000)
    # 逐段滚一遍再回顶：跳跃式滚动（0 → 底 → 0）只会让首尾屏进入视口，
    # 页面中段元素的 IntersectionObserver 从「不相交」直接到「不相交」，永远不触发，
    # 于是那些元素在截图和 lint 时还停在揭示前的 transform 上——量出来的位置是假的。
    page.evaluate(
        "async () => {"
        "  const step = Math.max(300, Math.floor(window.innerHeight * 0.8));"
        "  const H = document.documentElement.scrollHeight;"
        "  for (let y = 0; y < H; y += step) {"
        "    window.scrollTo(0, y);"
        "    await new Promise(r => setTimeout(r, 30));"
        "  }"
        "  window.scrollTo(0, H);"
        "  await new Promise(r => setTimeout(r, 60));"
        "  window.scrollTo(0, 0);"
        "}"
    )
    page.wait_for_timeout(400)
    prepped = page.evaluate(PREP_SCRIPT)
    page.wait_for_timeout(200)
    # 渲染稳态探针：等 fonts / 图片 / 布局都稳；超时上限 3s，超了就照截，不阻塞交付
    try:
        page.wait_for_function(READY_SCRIPT, timeout=3000, polling=120)
    except Exception:
        pass

    report = {"revealed": prepped}

    # 可选：注入一段用户 JS 后再截图。用于状态验证（换数据集重渲染、切 hash、点按钮）
    # 代码被包在 async 函数体里，允许 `await` 与 `return`。返回值 JSON 化后进 evalResult
    # 稳态缓存在注入后重置，让 READY_SCRIPT 重新判定一次 fonts/imgs/layout 稳定
    if eval_code:
        eval_info = {"executed": True}
        try:
            wrapped = "async () => { " + eval_code + " \n}"
            value = page.evaluate(wrapped)
            eval_info["result"] = value
        except Exception as e:
            eval_info["executed"] = False
            eval_info["error"] = str(e)[:400]
        # 注入后可能触发 DOM 变化 / 新图片加载 / 字体切换 —— 清稳态缓存重新等一次
        try:
            page.evaluate("() => { window.__shot_ready_state = null; }")
            page.wait_for_function(READY_SCRIPT, timeout=3000, polling=120)
        except Exception:
            pass
        report["eval"] = eval_info

    # 截图（screenshots 开时才做；未开时也仍需渲染，用于 lint/structure）
    if "screenshots" in include:
        page.screenshot(path=str(out_path), full_page=True)
        post = _postprocess(out_path, max_width, jpeg_quality, fmt, slice_over_kb, slice_over_height, slice_height)
        report["screenshot"] = str(post["path"])
        report["screenshotBytes"] = post["bytes"]
        # chromium canvas 上限约 30000px，超过就会被截断
        page_h = page.evaluate("() => document.documentElement.scrollHeight")
        if page_h and page_h > 30000:
            report["truncated"] = True
            report["truncatedHint"] = f"页面高度 {page_h}px 超过 chromium 单张截图上限，实际截取被截断。"
        else:
            report["truncated"] = False
        if post["slices"]:
            report["slices"] = [str(s) for s in post["slices"]]
            report["sliceHint"] = (
                f"主图过阈值（字节>{slice_over_kb}KB 或 高度>{slice_over_height}px），"
                f"已按 {slice_height}px 切片。若主图 Read 失败，改读 slices 里各分片。"
            )

    # DOM 报告：lint / structure 至少一个开启时才 evaluate
    if "lint" in include or "structure" in include:
        dom = page.evaluate(REPORT_SCRIPT)
        _apply_dom_report(report, dom, console_bucket, resource_bucket, include)
        # 靠色要在**渲染结果**上采样背景色（clip 截图），只有 playwright 分支持有 page
        # 对象能截图；CDP 分支拿不到，所以这条规则不放进共用的 _apply_dom_report。
        if "lint" in include:
            contrast = sample_text_contrast(
                page,
                dom.get("textCandidates") or [],
                dom.get("docSize") or {},
            )
            if contrast:
                report["textContrastIssues"] = contrast
                report["textContrastHint"] = (
                    "含义：正文段落（`<p>`）的文字颜色与背景色对比度过低，读起来吃力或几乎读不出来。"
                    "contrastRatio 是 WCAG 对比度（1.0 = 完全同色），count 是同一套配色在页面里出现的次数，"
                    "color / background 是实际渲染色（已合成 rgba 透明度与祖先 opacity）。"
                    "**本规则只查 `<p>`、只报低于 1.6 的**：人工盲测 28 个真实产物的结论——"
                    "低对比度的标签、徽章、序号、按钮（span / div / a / button）全部被判「不影响使用」，"
                    "它们靠位置和形状就能识别；只有需要通读的正文段落读不清才是真问题。"
                    "所以触发了基本就是真的，不要当成可选建议。"
                    " | 修法：把正文色与背景拉开亮度差——正文正常应在 4.5:1 以上，最低 3:1。"
                    "常见根因是**同一套文字色被复用到了两种背景上**（浅色区和深色区共用一个 --text 变量），"
                    "在其中一种上就糊了；按背景分层定义文字色（如 --text-on-light / --text-on-dark）可以根治。"
                    "只调透明度（`opacity` / `rgba` 的 alpha）通常不够，要动色值本身的明度。"
                    " | 检测局限（不是豁免，是**查不到**）：背景为渐变、图片、伪元素色块或绝对定位覆盖层时，"
                    "拿不到确定的背景色，这些元素一律跳过不报——**渐变背景上的靠色本规则发现不了，要靠截图人工核对**。"
                    " | 豁免：(1) 故意做的水印、暗纹、装饰性段落，截图上确认是设计意图；"
                    "(2) 正文本身是次要信息且用户明确要求低调处理。"
                )
    console_bucket.clear()
    resource_bucket.clear()
    return report


def _apply_dom_report(report, dom, console_bucket, resource_bucket, include):
    """把 REPORT_SCRIPT 的 dom 结果 + console/network buckets 装配进 report。

    抽出这个函数是为了让 playwright 和 chrome CLI (CDP) 两条分支共用同一份装配逻辑——
    在 CDP 里通过 addScriptToEvaluateOnNewDocument 也能跑 INIT_SCRIPT + REPORT_SCRIPT,
    console/network 可以订阅 Runtime.consoleAPICalled / Network.responseReceived 拿到。
    """
    if "structure" in include:
        report["structure"] = dom.get("structure")
    # chartContainers 无论 lint/structure 开哪个都存下来，供跨视口对比
    report["_chartContainers"] = dom.get("chartContainers") or []
    if "lint" in include:
        report["consoleErrors"] = [m for m in console_bucket if m.get("type") == "error"]
        report["consoleWarnings"] = [m for m in console_bucket if m.get("type") == "warning"]
        report["horizontalOverflow"] = dom.get("horizontalOverflow") or []
        report["resourceErrors"] = list(resource_bucket)
        if dom.get("fontFailures"):
            # 字体加载失败合并进 resourceErrors
            for f in dom["fontFailures"]:
                report["resourceErrors"].append({
                    "url": f"font:{f.get('family','')}",
                    "resourceType": "font",
                    "status": None,
                    "reason": "font_load_error",
                })
        local_imgs = dom.get("localImages") or []
        # 只在云电脑上报。本地电脑按 SKILL.md 就该用 assets/ 相对路径引用，
        # 报出来等于指挥模型去做规则明确禁止的事，而且原 hint 给的修法正是云电脑那条。
        # 判据与 SKILL.md 的运行环境判定保持一致：Windows / Mac → 本地电脑，其余 → 云电脑。
        if local_imgs and platform.system() not in ("Darwin", "Windows"):
            report["localImageWarnings"] = local_imgs
            report["localImageHint"] = (
                "含义：页面里存在 file:// 本地图片引用。云电脑交付的 HTML 不能包含文件系统引用。"
                " | 修法：跑 scripts/embed.py 把图以 Base64 内嵌，交付它产出的 <原文件名>_embed.html"
                "（准确路径看该脚本 JSON 报告的 out 字段）。"
                " | 豁免：本地电脑（Computer OS 为 Windows / Mac）不报此项——那里用 assets/"
                " 相对路径引用是规定做法。本规则只匹配 file://，http(s)/data URI 都不会报。"
            )
        stretched = dom.get("stretchedImages") or []
        if stretched:
            report["stretchedImages"] = stretched
            report["stretchedImagesHint"] = (
                "含义：图片渲染盒子的宽高比与图片固有宽高比不符，且 object-fit 是默认的 fill——"
                "图像内容被硬拉伸/压扁。ratioDeviation = 渲染比例 ÷ 固有比例，1.0 为正常，"
                "0.4 表示横向被压到四成宽。**海报、人物、二维码上尤其致命**：二维码形变后扫不出来，"
                "属于功能损坏而非美观问题；而截图上拉伸的设计稿很容易被误读成「刻意的竖版构图」，肉眼复核会漏。"
                " | reason=html-attr-height-not-overridden：`<img width=W height=H>` 这两个 HTML 属性是"
                "presentational hint（等价 `width:Wpx; height:Hpx`），优先级低于任何 CSS。"
                "CSS 里的 `width:100%` 只覆盖 width，**height 仍是 Hpx**；"
                "`aspect-ratio: auto W/H` 只在有一边为 auto 时才反推另一边，两边都确定时不产生约束。"
                "修法二选一，不要都做：(a) 删掉 HTML 的 `width`/`height` 属性，浏览器会自动按固有比例推导；"
                "(b) 在 CSS 里补 `height:auto`。"
                " | reason=box-ratio-mismatch：CSS 把 width 和 height 都写死了但比例算错，"
                "或父级 flex/grid 的 `align-items:stretch` 把图拉高。"
                "修法：只定一边尺寸（另一边留 auto），或改用 `object-fit:cover` 让内容裁切而不形变。"
                " | 豁免：(1) object-fit 为 cover/contain/none/scale-down 的图**本规则完全不检查**——"
                "那些属性下盒子比例变了内容也不形变，是正常做法，无需处理；"
                "(2) `transform:scale(x,y)` 的刻意形变不会被报（本规则用 computed width/height，不含 transform）；"
                "(3) 渲染尺寸 < 20×20 的装饰小图、未加载完成的图不报。"
            )
        overlapping = dom.get("overlappingText") or []
        if overlapping:
            report["overlappingText"] = overlapping
            report["overlappingTextHint"] = (
                "含义：两个含文字的元素 bounding rect 有交集。典型 case：绝对定位徽章/浮层压到内容文字上、卡片尺寸没对齐。"
                "coverRatio 是交集面积占较小元素面积的比例，越大越可疑。"
                " | 修法：调整定位、给徽章预留空间、或缩小重叠元素之一。"
                " | 豁免：(1) 故意的视觉层叠（如卡片右上角小 badge 落在卡片 padding 空隙里没盖文字），可对着截图确认后忽略；"
                "(2) coverRatio < 0.1 且截图看不出问题的，多半是亚像素抖动。"
            )
        clipped = dom.get("clippedText") or []
        if clipped:
            report["clippedText"] = clipped
            report["clippedTextHint"] = (
                "含义：overflow:hidden|clip 的容器把内部文本裁掉了。clippedX/Y 是被吃掉多少 px。"
                "已自动排除 text-overflow:ellipsis 单行截断和 -webkit-line-clamp 多行截断（这两个是设计意图）。"
                " | 修法：把容器 height 改成 min-height、或允许内容溢出、或缩短文案。"
                " | 豁免：(1) 5-20px 小值可能是行高/边距计算的边界抖动、动画过程中的瞬时状态；"
                "(2) 故意的 marquee/scroll 容器（虽然 overflow:hidden 但依赖 JS 滚动）。"
            )
        pseudo_of = dom.get("pseudoOverflow") or []
        if pseudo_of:
            report["pseudoOverflow"] = pseudo_of
            report["pseudoOverflowHint"] = (
                "含义：::before / ::after 伪元素的 content 文字被自身固定 width 装不下（视觉上表现为字溢出小方块/圆点、"
                "或字被居中后飘到色块两侧脱离背景）。三重触发：content 非空 + 显式 width（非 auto/百分比）+ measureText > contentWidth × 1.1。"
                "典型 case：`content:attr(data-i)` 的序号徽章、`.tl-item::before` 的日期徽标，data 值从 1 位变成 2/3 位就撑破。"
                "已过滤：display:none、ellipsis 截断、图标字体（FontAwesome/Material/iconfont）、尺寸 < 4×4。"
                " | 修法：把 `width: Npx` 改成 `min-width: Npx; padding: 0 Xpx;`，配合 `display: inline-flex` 让盒子随内容自适应；"
                "或者收紧数据保证 content 位数固定。"
                " | 豁免：(1) 故意的装饰性溢出（大号引号从盒子里探出来做视觉效果）——对着截图确认后忽略；"
                "(2) 用 web font 但 fallback 字体量出来偏胖导致虚报——检查 font-family 是否加载完成；"
                "(3) overflowPx < 3 且 contentWidth ≥ 20px 的低幅度告警，通常是 measureText 精度问题。"
            )
        dead = dom.get("deadButtons") or []
        if dead:
            report["deadButtons"] = dead
            report["deadButtonsHint"] = (
                "含义：视觉上可点、但点了不发生任何事的元素。覆盖 6 种模式，reason 字段指明是哪种："
                " | button-no-onclick：<button> 既无 onclick 也没被 addEventListener('click') 绑过。"
                " | onclick-noop：onclick 属性是占位/无副作用字符串（`return false` / `void(0)` / 空串 / 分号 / 纯注释等），"
                "extra 字段 onclickAttr 展示原始值。这类写法在生产代码里几乎没有正当用途，视同没写。"
                " | a-no-href / a-href-empty / a-href-hash-no-handler：<a> 无 href / href=\"\" / href=\"#\" 且无 handler。"
                " | a-href-javascript-noop-no-handler：<a href=\"javascript:void(0)\" / \"javascript:;\">，作者显式关掉 native 导航，"
                "但 JS 侧也没人接手。收紧路径：祖先有 click listener 时，还要验证 listener 源码是否引用了本元素的 class/id/data-* 才放行；"
                "listener 源码不可读（native/bound/被 minify）时保守放行，避免误伤。extra 字段 hrefAttr 展示原始 href。"
                " | a-broken-anchor：<a href=\"#foo\"> 但页面里没有 id=\"foo\" 也没有 name=\"foo\" 的元素。"
                "已排除 SPA hash 路由（href 含 / 或 ? 的形式，如 #/dashboard）。"
                " | cursor-pointer-no-handler：<div>/<span> 等非交互标签加了 cursor:pointer 却没绑任何 click。"
                " | input-no-handler：<input type=button|submit|reset|image> 无 onclick 也无 listener。form 里的 submit/reset 已豁免。"
                " | label-for-not-found：<label for=\"xxx\"> 但页面里没有 id=\"xxx\"。用户点 label 期望 focus 到 input，实际什么都不发生。"
                "extra 字段 forAttr 展示 for 值。"
                " | 已排除：form submit/reset、popover 触发器、role=button/link/tab/menuitem/option/switch/checkbox/radio、"
                "<label> 包裹、body/html 上继承 cursor:pointer；cursor-pointer-no-handler 只报尺寸 ≥ 24×16 且有可见文字的元素。"
                " | 修法：给 <button>/<input> 加 onclick 或 addEventListener；给 <a> 补真实 href 或改成 <button>；"
                "把 <div class=\"nav-item\">…</div> 之类假按钮换成真 <button> 或 <a>，或给它加 role=button+tabindex+键盘 handler；"
                "onclick=\"return false\" 之类占位符要么删掉（配合真 handler），要么替换为 toast 提示「演示中」这类可感知反馈；"
                "断链锚点核对目标 id 拼写；label 断链核对 for 与 input id 是否一致。"
                " | 豁免：(1) 带 note=ancestor-has-data-attr 的项可能是**祖先事件委托**目标（document/window 上的全局委托本规则查不到），"
                "对着代码核对，如果确实有 document.addEventListener('click', e => e.target.closest(...)) 之类的委托捕获就忽略；"
                "(2) 纯装饰按钮（无 hover/focus 反馈的 mock 页面）——但这本身也算 slop，建议改成非 <button>；"
                "(3) cursor-pointer-no-handler：如果元素只是 hover 变鼠标做微交互提示（如 tooltip trigger）而非真按钮，去掉 cursor:pointer 更合适；"
                "(4) a-href-javascript-noop-no-handler：如果确实有全局委托捕获（如 window.addEventListener 或 minify 后的框架 handler），"
                "本规则的 listener 源码启发式可能读不到明文标识 → 结合 note 字段和实际代码核对；"
                "(5) a-broken-anchor：如果目标 id 是运行时由 JS 动态注入的（比如懒加载章节），核对确认后可忽略。"
            )
        misaligned = dom.get("misalignedBlocks") or []
        if misaligned:
            report["misalignedBlocks"] = misaligned
            report["misalignedBlocksHint"] = (
                "含义：section/main/article 直接子级里，个别元素撑到父容器全宽、其他兄弟明显更窄。"
                "widthDeltaVsGrid=比栅格宽多少 px、gridWidth=正常栅格宽度、containerWidth=父容器宽度。"
                "最常见根因：HTML 标签闭合错位（<p> 忘了 </p> 等）导致元素跳出 .wrap/.container 层级，"
                "浏览器容错解析、不报 console 错但布局层级已被打乱。"
                " | 修法：从 containerTag 定位到出问题的 section，逐行检查该 section 内前面的 HTML 标签闭合。"
                " | 豁免：(1) **full-bleed / breakout 布局**——故意做全宽 hero、全宽 gradient divider、"
                "文章里跳出正文栏的大图/引用块（杂志排版）。看截图确认是设计意图后忽略；"
                "(2) sticky/absolute 顶栏错放在 section 直接子级下（罕见）。"
            )
        uneven = dom.get("unevenColumns") or []
        if uneven:
            report["unevenColumns"] = uneven
            report["unevenColumnsHint"] = (
                "含义：同一 grid / row-flex 行内两列高度差过大，短列下方出现大片空白。"
                "heightDeltaPx=高度差 px、heightRatio=差 ÷ 长列高度、gapArea=短列宽 × 差（近似空白面积）、"
                "lockerTag=在长列里定位到的锁高元素标签（img/figure/div 等）。"
                "本规则设计上宁漏不错：需同时命中 heightRatio ≥ 0.30、heightDeltaPx ≥ 160、gapArea ≥ 40000，"
                "且必须能在**长列**里定位到锁高的根因（reason 字段）才报，无法归因的一律静默。"
                " | reason=tall-column-image-aspect-ratio：**长列**里有 <img>（或 picture/video）带 `aspect-ratio`（含继承）、"
                "且该图占长列高度 ≥60%。图片被 `aspect-ratio:3/4` 之类锁死高度（= 列宽 × 4/3），"
                "另一列内容较短、容器 `align-items:start`（或短列 align-self 非 stretch）就无法拉齐 → 短列下方空。"
                "修法（推荐前两条）：(a) 让短列跟随长列拉伸——`.short-col{align-self:stretch}` 或容器去掉 `align-items:start`（回默认 stretch），"
                "但注意 stretch 拉的是**盒子**，短列里的内容仍需自己往下铺（比如加 `justify-content:space-between` 或让某块 `margin-top:auto`），"
                "否则盒子拉高了内容还在顶部、白仍在；(b) 让图变矮——`aspect-ratio` 换成更矮的比例（4/5、1/1）或改成 `height:100%` 跟随短列；"
                "(c) 图列改成 sticky 图钉住 + 文字列滚动；(d) 让短列内容也变长（更适合内容自然长的情况）。"
                " | reason=tall-column-aspect-ratio：同上但锁高元素是 figure/div，非 <img>。"
                "多半是有人手写了 `.foo{aspect-ratio:3/4}` 的装饰盒子。修法同上。"
                " | reason=tall-column-fixed-height：长列自身或主要子级 inline style 里写了具体 px 高度。"
                "修法：改成 min-height 或去掉，让内容自然撑开。"
                " | 豁免：(1) 故意的短列 + 长图并排设计（如插画配一小段说明，视觉意图就是不齐），对着截图确认后忽略；"
                "(2) sticky 侧栏本身就短、需要长列滚动而侧栏钉住——本规则未特判 sticky，看截图确认；"
                "(3) 容器宽度 < 640、高度 < 300、或在 header/nav/footer/aside 内的容器本规则不检查；"
                "(4) `align-items:stretch` 且锁高源头不是 img/aspect-ratio 时本规则已豁免（那种情况布局引擎本会拉齐）。"
            )
        tl_align = dom.get("timelineAlignment") or {}
        tl_issues = tl_align.get("issues") or []
        dead_dots = tl_align.get("deadDotStyles") or []
        # 确定性缺陷：圆点声明了 width/height 但 display:inline 让它们静默失效。
        # 与下面的对齐检测不同，这条不需要判断设计意图——inline 吞掉尺寸声明是 CSS 规范的硬事实。
        if dead_dots:
            report["timelineDeadDotStyle"] = dead_dots
            report["timelineDeadDotStyleHint"] = (
                "含义：时间轴圆点声明了 `width`/`height`，但它的 computed `display` 是 `inline`——"
                "**非替换 inline 元素会忽略 `width`/`height` 和垂直 `margin`**（CSS 规范如此，不是浏览器 bug）。"
                "`<span>` 默认就是 inline，所以 `.dot{width:12px;height:12px;border-radius:50%}` 挂在 span 上时，"
                "尺寸声明一行都不生效：盒子宽度由内容撑（常常只有几 px）、高度由 line-height 决定，"
                "`border-radius:50%` 作用在这个畸形盒子上就画出**竖向细长椭圆**；`margin:auto` 同样不居中，圆点会偏出轴线。"
                "看 renderedWidth/renderedHeight 与 aspect 字段：aspect 远离 1.0 就是被 line-height 拉长的。"
                " | 修法：给圆点加 `display:block`（配 `margin:0 auto` 居中）或 `display:inline-block`。"
                "改完 width/height/margin 立刻生效，椭圆变正圆、偏移归零。"
                " | 本规则只在**作者确实声明了 width 或 height** 时才报——没声明尺寸的 inline 装饰元素不报，"
                "所以触发了必定是真错：没有任何设计意图会故意写一个不生效的尺寸声明。"
            )
        # 只在「量到了系统性偏移」时才报。量不到（横向时间轴、表格式、canvas/echarts 渲染）一律静默：
        # 那种情况下给不出可执行的修法，而 SKILL.md 的口径是"报出来基本都是真的"，
        # 报一句"请人工核对"只会诱导模型去改本来正确的代码。
        if tl_issues:
            report["timelineAlignmentIssues"] = tl_issues
            report["timelineAlignmentHint"] = (
                "含义：时间轴的轴线中心与节点圆点中心不重合。orientation=vertical 比的是中心 x、"
                "horizontal 比的是中心 y；offsetPx 是圆点相对轴线的偏移（正=偏右/偏下），"
                "affectedDots 是呈现同一偏移的节点数。**1px 起就可能被看出来，2px 必然可辨**，这是时间轴最高频的 badcase，"
                "实测同批产物里做对的偏移为 0.00px、做错的在 2px 以上（也见过 15px / 20px 的）。"
                "本规则只在「至少 2 个节点呈现同一偏移」时才报——孤立离群值不报，所以触发了基本就是真的。"
                " | reason=pseudo-content-box：圆点用 ::before 画且带 border。**`*{box-sizing:border-box}` 不匹配伪元素**，"
                "伪元素仍是 content-box，实际外径 = width + 2*border，比按 border-box 心算的大一圈，"
                "偏移量恒等于 dotBorderWidth。修法二选一：(a) 在该 ::before 规则里**显式补 `box-sizing:border-box`**；"
                "(b) 改用真元素（<span>/<div>）画圆点，它才吃得到 `*` 的重置。"
                " | reason=origin-mismatch：轴线挂在 axisOrigin 的 ::before 上、圆点挂在 dotOrigin 里，"
                "两者是不同的定位包含块，坐标原点差一个 axisOriginPadding，偏移量恒等于它。"
                "修法：把轴线和圆点锚到**同一个定位祖先**上，别一个挂外层容器、一个挂内层 item。"
                " | reason=arithmetic：手算 left/top 时算错了（常见于双侧交替时间轴——"
                "中央竖线 left:50%，奇偶两列各写一套 left，其中一列没对上，两列偏移量还不一样）。"
                " | 最稳的写法（推荐直接改成这个，而不是去修算式）：item 用 grid 三列"
                "（时间 / 轴 / 内容），圆点是真元素放中列、用 `justify-self:center` 让布局引擎负责居中，"
                "轴线的 left 用 `calc()` 从同一组列宽变量推出，例如 "
                "`.timeline{--date:88px;--axis:30px;--gap:20px}` + "
                "`.timeline::before{left:calc(var(--date) + var(--gap) + var(--axis)/2)}`。"
                "这样圆点一个 left 都不用手算，两者引用同一个真值来源，结构上不可能歪。"
                "横向时间轴同理，把三列换成三行、用 `align-self:center`。"
                " | 顺带核对（本规则不查，但同属时间轴高频问题）：文字与轴线/图标是否重叠；"
                "每个节点是否承载了时间 + 事件名 + 一句话说明，而不是只丢一个标签。"
                " | 豁免：(1) 故意做的错位 / 手绘风设计，且截图上成立；"
                "(2) 圆点本身带外发光或多层 box-shadow、视觉中心与盒模型中心本就不重合。"
            )
        unsafe_href = dom.get("unsafeHrefRefs") or []
        if unsafe_href:
            report["unsafeHrefRefsWarning"] = unsafe_href
            report["unsafeHrefRefsHint"] = (
                "warning · 含义：SVG 内 <use> 或 <textPath> 用 href=\"#id\" 引用同页 fragment。"
                "Chrome 在 file:// 协议下会把这类引用视为 \"Unsafe attempt to load URL\" 并同步中断当前 script，"
                "表现是页面后段 JS 不跑（图表空、卡片空、动效不出）。"
                " | 修法：改成 xlink:href=\"#id\"，并在根 <svg> 上声明 xmlns:xlink=\"http://www.w3.org/1999/xlink\"；"
                "或同时保留两者（href + xlink:href）以兼容新旧写法。"
                " | 豁免：(1) 用户明确只走 http/https 部署、不会以 file:// 打开，可忽略；"
                "(2) 引用的是外链 URL（非 fragment）——本规则已自动过滤，不会报到；"
                "(3) 已在同一元素上写了 xlink:href——本规则已自动过滤。"
            )
        invis_anim = dom.get("invisibleAnimations") or []
        if invis_anim:
            report["invisibleAnimationsWarning"] = invis_anim
            report["invisibleAnimationsHint"] = (
                "warning · 含义：元素初态是 opacity:0 / visibility:hidden / clip-path inset 全遮，"
                "且**没有 CSS transition/animation 兜底**——需要 JS 挂类（如 .in / .chart-in）才能揭出。"
                "如果 IO 未触发、JS 报错、user gesture 未发生，用户永远看不到这些内容。"
                "reason=opacity:0 / visibility:hidden / clip-path-inset。"
                " | 修法：(a) 检查 IntersectionObserver / ScrollTrigger / GSAP 挂载是否正确；"
                "(b) 给元素补 CSS transition 兜底，即使 JS 挂了也能自然过渡到可见态；"
                "(c) 用 @media (prefers-reduced-motion) 分支保证 reduced-motion 用户直接看到静态终态。"
                " | 豁免：(1) 折叠/展开面板、模态框、抽屉——初态本就该隐藏，用户主动触发才显示；"
                "(2) 依赖 hover/click 才展开的 tooltip/menu；"
                "(3) 只在特定视口尺寸/断点下显示的元素；"
                "(4) 类名匹配但语义是 \"揭示后可见\" 且 JS 稳定挂载可自验的——对着截图确认元素已现在最终态即可。"
            )
        slop_fonts = dom.get("slopFonts") or []
        if slop_fonts:
            report["slopFontsWarning"] = slop_fonts
            report["slopFontsHint"] = (
                "warning · 含义：页面使用了 skill 明确禁的 slop 高发字体（Inter / Roboto / Arial / Fraunces / Playfair）。"
                "elementCount 是命中该字体的元素数（不含 fallback），sampleText 是首个样例文字。"
                " | 修法：换成主题相关的字体族（衬线/无衬线/等宽视调性而定），走自托管镜像 miaoda.feishu.cn/fonts/css2。"
                " | 豁免：(1) **用户品牌指定使用**——例如客户 CI 明确要求 Inter/Roboto，写在 brief 里可忽略；"
                "(2) **系统字体 fallback 命中**——虽然本规则只取 fontFamily 首选族，但如果这个族本身写的是 \"Arial\"、可能只是保守 fallback；"
                "如果同一元素明显还挂了自定义字体但 fallback 落到 Arial（例如自定义字体 404 了），修的其实是字体加载而非字体选型；"
                "(3) 极简项目本就要 \"grotesque + 中性感\"，且用户未指定——罕见但存在，看截图和 design plan 确认后可豁免。"
            )
        emoji_use = dom.get("emojiUsage") or []
        if emoji_use:
            report["emojiUsageWarning"] = emoji_use
            report["emojiUsageHint"] = (
                "warning · 含义：页面正文里检出 emoji 字符（U+1F300–U+1FAFF 或 U+2600–U+27BF 平面）。"
                "SKILL.md 视觉设计段明确禁用 emoji——不作图标、不作装饰、不放进数据。"
                " | 修法：换成内联 SVG 图标（<svg viewBox=\"0 0 24 24\">）建立风格连贯的图标语言。"
                " | 豁免：(1) **用户品牌资产明确包含 emoji**（罕见，但如即时通讯、社交媒体主题的产物合理）；"
                "(2) 主题本身就是关于 emoji 的（emoji 历史 / 表情包研究 / Unicode 演进）；"
                "(3) 引用某条真实文本原文（如推文截图的文字版），emoji 是内容而非装饰——保留原文可接受，但仍应权衡；"
                "(4) 装饰性 dingbat（如 U+2713 勾选符 ✓、U+2192 箭头 →、U+2605 星 ★）落入 U+2600–U+27BF 平面被误报的，如确认是符号非 emoji 可忽略。"
            )
        vp = dom.get("viewportMeta") or {}
        # 任意 shot 都要查 viewport meta（不是移动才查——桌面截图也能看出 meta 缺失）
        if vp and (not vp.get("present") or not vp.get("hasDeviceWidth")):
            report["viewportMetaWarning"] = vp
            report["viewportMetaHint"] = (
                "warning · 含义：<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"> 缺失或不含 width=device-width。"
                "iOS Safari / Android Chrome 在真机上会以 980px 假 viewport 渲染再等比缩小，页面上所有元素字如蚂蚁、按钮点不准。"
                "本次 shot.py 因为在受控 viewport 里跑截图，看起来正常，但真机用户会遭殃。"
                " | 修法：<head> 里加 `<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">`。"
                " | 豁免：(1) 产物明确只交付桌面场景（大屏 kiosk / 内嵌大屏投屏），且不会有移动访问——罕见但存在；"
                "(2) 已设 `user-scalable=no` 或 `maximum-scale=1` 但**这本身是 anti-pattern**：违反无障碍，不推荐豁免，反而应移除；"
                "(3) 页面是纯打印用途，无网页渲染需求。"
            )
        elif vp and vp.get("present") and vp.get("disablesZoom"):
            # meta 存在但 user-scalable=no / maximum-scale=1，独立报一条更弱的 warning
            report["viewportMetaWarning"] = vp
            report["viewportMetaHint"] = (
                "warning · 含义：viewport meta 存在但设置了 user-scalable=no 或 maximum-scale=1，禁用了用户缩放。"
                "这是 anti-pattern：低视力用户依赖捏合放大读页面，禁用即等于把这批用户拒之门外。"
                " | 修法：移除 user-scalable=no / maximum-scale=1，改成 `content=\"width=device-width, initial-scale=1\"`。"
                " | 豁免：几乎没有正当理由——map 交互 / 3D 交互也不用禁 zoom，那些场景内嵌自己的手势处理即可，页面缩放不冲突。"
            )
        tts = dom.get("touchTargetTooSmall") or []
        if tts:
            report["touchTargetTooSmallWarning"] = tts
            report["touchTargetTooSmallHint"] = (
                "warning · 含义（仅 mobile shot 触发）：按钮 / 链接 / 交互元素的命中区 < 44×44px（iOS HIG 下限）。"
                "手指宽约 7–10mm ≈ 44px，小于此手指点不准，且按下会误触相邻元素。已自动过滤纯正文里的 inline 超链接（<a> inline + 高度 < 26px）。"
                " | 修法：给按钮/链接加 `min-width: 44px; min-height: 44px;` 或增大 padding；图标按钮特别注意，容易只给 16-20px。"
                " | 豁免：(1) 密集工具栏 / 编辑器 UI（图标按钮 32px 是行业惯例），但需给周围留足 gap 保证不误触；"
                "(2) 装饰性小 icon（不响应 click，只有 hover tooltip）——本规则应该已过滤，若仍报出可忽略；"
                "(3) 主要面向桌面 + 键鼠操作的产物（管理后台 / 编辑器），但如果页面同时对手机用户开放就不能豁免。"
            )
        fixed_w = dom.get("fixedWidthElements") or []
        if fixed_w:
            report["fixedWidthElementsWarning"] = fixed_w
            report["fixedWidthElementsHint"] = (
                "warning · 含义（仅 mobile shot 触发）：元素 computed width > viewport 宽度，且没有 % 相对宽度、父级也不是 overflow 容器。"
                "典型是硬编码 `width: 1200px` 之类固定宽度未做响应式，在 390px viewport 下必然横向溢出。"
                "inlineWidth 字段展示 inline style 里的 width 值（无则为 null）。"
                " | 修法：改成相对宽度（`width: 100%`、`max-width`）、grid / flex 布局、或加移动断点 `@media (max-width: 640px) { ... }` 覆盖。"
                " | 豁免：(1) **故意的横向 scroller**（swiper / carousel / marquee / 横向 timeline）——父元素带 overflow-x:auto 时本规则已自动过滤；"
                "若你的 scroller 靠 JS 拖拽而非 overflow，需在父元素显式设 overflow-x 让规则识别；"
                "(2) SVG / Canvas 图表在容器里 clip 显示，元素本身尺寸大于视口但用户只看到裁切部分——但更好的做法是让 SVG viewBox 自适应。"
            )
        edge_hug = dom.get("edgeHuggingText") or []
        if edge_hug:
            report["edgeHuggingTextWarning"] = edge_hug
            report["edgeHuggingTextHint"] = (
                "warning · 含义（仅 mobile shot 触发）：正文/标题文字的渲染左边缘贴到视口边（left ≤ 1px），"
                "左内边距完全塌陷。**桌面截图永远看不出这个问题**——它只在视口宽度 ≤ 容器 max-width 时出现。"
                " | 最高频成因是 `padding` 简写把继承来的左右内边距清零："
                "`.wrap{max-width:1180px;margin:0 auto;padding:0 28px}` 定义了左右 28px，"
                "而 `.hero-inner{padding:88px 0 96px}` 只想加上下内边距，简写却把左右一起重设为 0；"
                "元素同时挂着这两个 class（`class=\"wrap hero-inner\"`）时后写的简写胜出。"
                "宽屏下 `margin:0 auto` 的居中边距掩盖了它——1440px 视口时 (1440−1180)/2 = 130px，看起来完全正常；"
                "视口一旦 ≤ max-width，居中边距归零，padding 又是 0，文字就直接贴屏幕边缘。"
                "**`margin:0 auto` 不是 padding 的替代品**，它只在 viewport > max-width 时存在。"
                " | 看字段判断：`parentPaddingLeft` 和 `parentMarginLeft` 同时为 `0px`、`parentMaxWidth` 有具体值，就是这个成因。"
                " | 修法：把 `padding: A 0 B` 换成 `padding-block: A B`（逻辑属性，只动上下，不碰左右），"
                "或显式写全 `padding: A 28px B`。不要改成 `margin: 0 auto` 就完事。"
                " | 豁免：(1) 祖先为 `position:absolute/fixed/sticky`、负向 `translateX`、`left < -40px` 的元素"
                "（移动端收起的抽屉、无障碍 skip link、绝对定位 badge）**本规则已自动过滤**，无需处理；"
                "(2) 刻意的满版设计——整块背景图上的装饰性大字、全宽色带里的标题，视觉上贴边成立；"
                "(3) `text-align:center` 的长文本在窄屏两侧各余几像素属正常，本规则阈值 1px 已排除这类。"
            )
        m_font = dom.get("mobileFontIssues") or []
        if m_font:
            report["mobileFontIssuesWarning"] = m_font
            report["mobileFontIssuesHint"] = (
                "warning · 含义（仅 mobile shot 触发）：两类问题合并——"
                "(a) kind=small-body-text：正文字号 < 14px，手机上难读；"
                "(b) kind=input-under-16px：<input> / <textarea> font-size < 16px，iOS Safari 聚焦时会自动缩放页面（那种一点输入框页面跳一下的贼恶心 UX）。"
                " | 修法：正文 ≥ 14px（16px 更佳）；表单元素 ≥ 16px。可以在移动断点里针对性调大："
                "`@media (max-width: 640px) { body { font-size: 16px; } input, textarea { font-size: 16px; } }`。"
                " | 豁免：(1) 图例 / caption / footnote 类辅助文字，12–13px 可接受，但应控制在页面 5% 以内；"
                "(2) 数据密集型表格数字（如财务表 12px 是行业惯例）——需要该单元格开 `tnum` 等宽数字避免飘忽；"
                "(3) input 已设 `font-size: 16px` 但仍报出——可能是 inline style / 父级 rem 计算异常，检查实际 computed 值。"
            )


def _find_chromium_fallback():
    """在常见位置寻找可用的 chromium 可执行文件，返回路径或 None。

    背景：playwright python 包 hard-code 了对应版本的 chromium 目录
    （如 chromium_headless_shell-1234），环境里若只有 1169 或
    /usr/local/bin/chromium 就会 launch 失败。这里做兜底扫描。
    """
    import glob
    candidates = []
    # playwright cache 里其他版本的 headless chrome
    for base in (
        "/opt/vm/preinstall/ms-playwright",
        os.path.expanduser("~/.cache/ms-playwright"),
        os.path.expanduser("~/Library/Caches/ms-playwright"),
        os.path.expanduser("~/AppData/Local/ms-playwright"),
    ):
        # headless shell 覆盖 linux64 / linux-arm64 / mac / mac-arm64 / win64
        for p in glob.glob(f"{base}/chromium_headless_shell-*/chrome-headless-shell-*/chrome-headless-shell"):
            candidates.append(p)
        for p in glob.glob(f"{base}/chromium_headless_shell-*/chrome-headless-shell-*/chrome-headless-shell.exe"):
            candidates.append(p)
        # 完整 chromium：linux / linux64 / linux-arm64
        for p in glob.glob(f"{base}/chromium-*/chrome-linux*/chrome"):
            candidates.append(p)
        for p in glob.glob(f"{base}/chromium-*/chrome-linux*/headless_shell"):
            candidates.append(p)
        # windows
        for p in glob.glob(f"{base}/chromium-*/chrome-win*/chrome.exe"):
            candidates.append(p)
        # macOS：intel & apple silicon
        for p in glob.glob(f"{base}/chromium-*/chrome-mac*/Chromium.app/Contents/MacOS/Chromium"):
            candidates.append(p)
    # 系统安装
    for p in _system_browser_candidates():
        candidates.append(p)
    for c in candidates:
        if os.path.exists(c) and os.access(c, os.X_OK):
            return c
    return None


def _system_browser_candidates():
    """跨平台常见系统浏览器路径。返回按优先级排序的列表。"""
    sysname = platform.system()
    paths = []
    if sysname == "Darwin":
        paths += [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
        ]
    elif sysname == "Linux":
        paths += [
            "/usr/local/bin/chromium",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/opt/google/chrome/chrome",
            "/snap/bin/chromium",
            "/usr/bin/microsoft-edge",
            "/usr/bin/microsoft-edge-stable",
        ]
    elif sysname == "Windows":
        env_program_files = [os.environ.get("PROGRAMFILES", r"C:\Program Files"),
                             os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"),
                             os.environ.get("LOCALAPPDATA", "")]
        for pf in env_program_files:
            if not pf: continue
            paths += [
                os.path.join(pf, r"Google\Chrome\Application\chrome.exe"),
                os.path.join(pf, r"Microsoft\Edge\Application\msedge.exe"),
                os.path.join(pf, r"Chromium\Application\chrome.exe"),
            ]
    # 兜底：PATH 里查
    for name in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable",
                 "chrome", "microsoft-edge", "msedge"):
        w = shutil.which(name)
        if w: paths.append(w)
    return paths


def _launch_chromium(p, explicit_exec):
    """先按默认路径 launch（playwright 自带 chromium）；失败时才扫描 fallback；再不行 raise。

    这样能确保：正常环境走 playwright 官方版本，只有在 VM 里 chromium 缺失时
    才回退到系统 chromium / 其他版本目录。explicit_exec 由 --exec-path 显式给出时优先。
    """
    if explicit_exec:
        try:
            return p.chromium.launch(executable_path=explicit_exec), explicit_exec
        except Exception as e:
            raise RuntimeError(f"显式 --exec-path 启动失败：{explicit_exec}\n{e}")
    try:
        return p.chromium.launch(), "(playwright default)"
    except Exception as first_err:
        fallback = _find_chromium_fallback()
        if fallback:
            try:
                return p.chromium.launch(executable_path=fallback), fallback
            except Exception as second_err:
                raise RuntimeError(
                    f"chromium 启动失败，已尝试默认路径与 fallback ({fallback})：\n"
                    f"default: {first_err}\nfallback: {second_err}"
                )
        raise RuntimeError(
            f"chromium 启动失败，且未找到可用的 fallback 可执行文件。\n"
            f"原始错误：{first_err}\n"
            "在 doubao VM 里可尝试 `PLAYWRIGHT_BROWSERS_PATH=$HOME/.cache/ms-playwright playwright install chromium` "
            "先把 chromium 装到用户目录，再重跑本脚本。"
        )


def _trim_bottom_whitespace(img_path: Path, bg_tolerance: int = 20, min_keep_h: int = 200):
    """裁掉截图里大段纯背景色空白：底部整段 + 中间任何 > 200px 的连续空白段。

    chrome CLI 模式用固定 --window-size=w,24000 截图，页面里 min-height:100vh 会被
    撑成 24000px，导致大量空白。本函数：
      1. 用图像四角像素的中位数作为背景色（避开顶部导航等强色）
      2. 逐行扫描全图，判定每一行是不是"整行都是背景色"
      3. 底部连续背景色行整体裁掉
      4. 中间任何 > 200px 的连续空白段折叠成 40px（保留视觉节奏）

    安全阀：Pillow 缺失时跳过；裁完高度 < min_keep_h 时不动。
    """
    try:
        from PIL import Image  # type: ignore
    except Exception:
        return
    with Image.open(img_path) as im:
        im = im.convert("RGB")
        w, h = im.size
        px = im.load()

        # 背景色基准：用四角 + 底部一行采样，中位数
        sample = []
        step_x = max(1, w // 40)
        for x in range(0, w, step_x):
            sample.append(px[x, h - 1])
        # 四角
        for (x, y) in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
            sample.append(px[x, y])
        sample.sort()
        bg = sample[len(sample) // 2]

        def is_bg_row(y):
            # 在这一行采 40 个 x 位置，全部落在 bg 容差内视为纯背景行
            for x in range(0, w, step_x):
                r = px[x, y]
                if (abs(r[0] - bg[0]) > bg_tolerance or
                    abs(r[1] - bg[1]) > bg_tolerance or
                    abs(r[2] - bg[2]) > bg_tolerance):
                    return False
            return True

        # 一次遍历每一行：True/False
        is_bg = [is_bg_row(y) for y in range(h)]

        # 底部连续 bg → 一次性裁掉，保留 40px 缓冲
        last_content = h - 1
        while last_content >= 0 and is_bg[last_content]:
            last_content -= 1
        if last_content < 0:
            return  # 整张都是背景，不动
        bottom_cut = min(h, last_content + 40)

        # 中间空白段：连续 bg 段 > 200px 折叠成 40px
        # 从上到下扫，边裁边记录 keep 区间
        keeps = []  # [(src_y0, src_y1, dst_h)]
        y = 0
        while y < bottom_cut:
            if is_bg[y]:
                # 找连续空白段
                start = y
                while y < bottom_cut and is_bg[y]:
                    y += 1
                seg_len = y - start
                if seg_len > 200:
                    keeps.append(("bg", start, y, 40))  # 折叠成 40px
                else:
                    keeps.append(("bg", start, y, seg_len))  # 保留原状
            else:
                start = y
                while y < bottom_cut and not is_bg[y]:
                    y += 1
                keeps.append(("content", start, y, y - start))

        # 计算新画布高度
        new_h = sum(k[3] for k in keeps)
        if new_h < min_keep_h or new_h >= h - 20:
            return  # 没啥可省，别动

        new_im = Image.new("RGB", (w, new_h), bg)
        dst_y = 0
        for kind, s0, s1, dst_h in keeps:
            if kind == "content" or dst_h == (s1 - s0):
                # 内容段 / 保留原状的短空白段：直接搬
                new_im.paste(im.crop((0, s0, w, s1)), (0, dst_y))
            # 折叠段：不搬像素，直接留 dst_h 的背景色（Image.new 已经填了 bg）
            dst_y += dst_h

        fmt = "PNG" if img_path.suffix.lower() == ".png" else "JPEG"
        new_im.save(img_path, fmt, quality=80, optimize=True, progressive=True) if fmt == "JPEG" else new_im.save(img_path, fmt, optimize=True)


# ---------- chrome CLI 兜底：playwright 不可用时 ----------
def _chrome_cli_shoot(exec_path: str, url: str, viewport, out_path: Path,
                     max_wait_sec: int = 30,
                     want_report: bool = False,
                     console_bucket=None, resource_bucket=None):
    """CLI 模式截图：优先 CDP full-page（真正的完整长图），失败退到 --screenshot 首屏。

    CDP 路径：起 chrome 带 --remote-debugging-port，Python 直连 devtools
    websocket 发 Page.captureScreenshot(captureBeyondViewport=true)，
    等价于 puppeteer/playwright 底层做法，可以拿到完整长页截图。

    want_report=True 时同时通过 Runtime.evaluate 跑 INIT_SCRIPT+REPORT_SCRIPT，
    返回 dom 报告；退到 --screenshot 兜底路径时无法拿 DOM，返回 None。
    """
    w, h = viewport
    # ---- 首选：CDP 全页截图 ----
    cdp_err = None
    try:
        dom = _cdp_capture(exec_path, url, viewport, out_path, max_wait_sec,
                           want_report=want_report,
                           console_bucket=console_bucket,
                           resource_bucket=resource_bucket)
        # 后处理 trim 底部（CDP 一般贴合内容，很少有大空白，但保底）
        _trim_bottom_whitespace(out_path)
        return dom
    except Exception as e:
        cdp_err = e  # 保留下来；--screenshot 退路也挂时一起报出去

    # ---- 退路：--screenshot 只截视口一屏 ----
    args = [
        exec_path,
        "--headless=new",
        # 与 _cdp_capture 一致：headless chrome 在受限环境（macOS chrome-headless-shell、
        # 容器、VM）下 sandbox 会挂，必须显式关掉。
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--hide-scrollbars",
        "--force-device-scale-factor=1",
        f"--window-size={w},{h}",
        f"--screenshot={out_path}",
        url,
    ]
    def _with_cdp(msg: str) -> str:
        # 把 CDP 分支的错拼在后面，便于一次看清两条路都为什么挂
        return f"{msg}\nCDP 分支先前错误：{cdp_err}" if cdp_err else msg
    try:
        subprocess.run(args, check=True, timeout=max_wait_sec,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    except FileNotFoundError:
        raise RuntimeError(_with_cdp(f"chrome CLI 可执行文件不存在：{exec_path}"))
    except subprocess.TimeoutExpired:
        raise RuntimeError(_with_cdp(f"chrome CLI 超时 ({max_wait_sec}s)：{exec_path}"))
    except subprocess.CalledProcessError as e:
        tail = (e.stderr or b"").decode("utf-8", "replace")[-800:]
        raise RuntimeError(_with_cdp(
            f"chrome CLI 失败 (exit={e.returncode})：{exec_path}\nstderr tail:\n{tail}"
        ))
    if not out_path.exists() or out_path.stat().st_size == 0:
        raise RuntimeError(_with_cdp(f"chrome CLI 没有生成有效截图：{out_path}"))
    _trim_bottom_whitespace(out_path)
    return None  # --screenshot 退路拿不到 DOM


# ---------- 最小 CDP (Chrome DevTools Protocol) 客户端 ----------
def _cdp_capture(exec_path: str, url: str, viewport, out_path: Path, wait_sec: int,
                 want_report: bool = False,
                 console_bucket=None, resource_bucket=None):
    """启 chrome remote-debugging → 直连 websocket → Page.captureScreenshot 全页。

    不依赖任何第三方库；用标准库 socket 实现最小 websocket 帧收发（CDP 消息都是
    JSON 文本，短则几十字节长则几 MB 的 base64 图像）。

    want_report=True 时开 Runtime/Log/Network domain 收集 console+network 事件，
    并在稳态后跑 REPORT_SCRIPT 拿回 dom 报告；否则只出截图。
    """
    w, h = viewport
    port = _pick_free_port()
    user_data_dir = tempfile.mkdtemp(prefix="shot_cdp_")
    proc = subprocess.Popen(
        [
            exec_path,
            "--headless=new",
            # macOS 上 playwright 分发的 chrome-headless-shell 不带 helper app，
            # 缺 --no-sandbox 会 "sandbox initialization failed" 并让 GPU 进程 FATAL；
            # 加上对系统 Chrome/Edge 也安全（短生命周期 headless 本地会话）。
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--hide-scrollbars",
            "--force-device-scale-factor=1",
            f"--window-size={w},{h}",
            f"--remote-debugging-port={port}",
            f"--user-data-dir={user_data_dir}",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    try:
        # 等 devtools endpoint 就绪
        ws_url, target_id = _cdp_wait_target(port, timeout=8)
        with _WSClient(ws_url) as ws:
            # Page.enable → 可选注入 → Page.navigate → Page.loadEventFired → Page.captureScreenshot
            ws.call("Page.enable")
            # 用于把网络请求映射为 URL：Network.requestWillBeSent 早于 responseReceived / loadingFailed，
            # 用来存 requestId → url。放在 _cdp_capture 局部，随 with 结束回收。
            req_url_map = {}
            req_type_map = {}
            if want_report:
                # 收 console.log/warn/error、runtime error、log entry、network 请求
                ws.call("Runtime.enable")
                ws.call("Log.enable")
                ws.call("Network.enable")
                # 在每个新文档 load 之前注入 INIT_SCRIPT（patch addEventListener 标 __shot_hasClickListener）
                ws.call("Page.addScriptToEvaluateOnNewDocument", {"source": INIT_SCRIPT})
            ws.call("Page.navigate", {"url": url})
            # 等 load 事件；若网络卡就 wait_sec 后不再等
            deadline = time.time() + wait_sec
            got_load = False
            while time.time() < deadline:
                ev = ws.recv_event(timeout=deadline - time.time())
                if not ev:
                    continue
                if want_report:
                    _cdp_dispatch_event(ev, console_bucket, resource_bucket, req_url_map, req_type_map)
                if ev.get("method") == "Page.loadEventFired":
                    got_load = True
                    break
            # 再等 1s 让 fonts / lazy 图片跑
            time.sleep(1.0)
            # 触发 lazy 图片：滚到底再回顶
            ws.call("Runtime.evaluate", {"expression": "window.scrollTo(0, document.body.scrollHeight)"})
            time.sleep(0.4)
            ws.call("Runtime.evaluate", {"expression": "window.scrollTo(0, 0)"})
            time.sleep(0.2)
            # 强制显现 scroll-reveal（CDP 也能注入 JS！这是相比 --screenshot 的大提升）
            ws.call("Runtime.evaluate", {"expression": f"({PREP_SCRIPT.strip()})()"})
            time.sleep(0.3)
            # 渲染稳态：轮询 READY_SCRIPT 直到 true 或超 3s；超时不抛，照截
            ready_deadline = time.time() + 3.0
            while time.time() < ready_deadline:
                r = ws.call("Runtime.evaluate", {
                    "expression": f"({READY_SCRIPT.strip()})()",
                    "returnByValue": True,
                }, timeout=5)
                if r.get("result", {}).get("result", {}).get("value") is True:
                    break
                time.sleep(0.12)
            # 消化稳态期间累积的事件
            if want_report:
                _cdp_flush_pending_events(ws, console_bucket, resource_bucket, req_url_map, req_type_map)
            # 收 DOM 报告（在截图前跑，这样 REPORT_SCRIPT 看到的和截图时刻一致）
            dom_report = None
            if want_report:
                rep = ws.call("Runtime.evaluate", {
                    "expression": f"({REPORT_SCRIPT.strip()})()",
                    "returnByValue": True,
                }, timeout=20)
                val = rep.get("result", {}).get("result", {}).get("value")
                if isinstance(val, dict):
                    dom_report = val
            # 全页截图
            resp = ws.call("Page.captureScreenshot", {
                "format": "png",
                "captureBeyondViewport": True,
                "fromSurface": True,
            }, timeout=25)
            b64 = resp.get("result", {}).get("data", "")
            if not b64:
                raise RuntimeError("Page.captureScreenshot 返回空 data")
            out_path.write_bytes(base64.b64decode(b64))
            # 再 flush 一次事件（截图期间可能仍有异步日志）
            if want_report:
                _cdp_flush_pending_events(ws, console_bucket, resource_bucket, req_url_map, req_type_map)
            return dom_report
    except Exception as e:
        # 把 chrome 自己的 stderr 尾部拼进异常，方便定位 sandbox / GPU 崩溃这类根因
        tail = _drain_stderr_tail(proc, limit=800)
        if tail:
            raise RuntimeError(f"{e}\nchrome stderr tail:\n{tail}")
        raise
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            try: proc.kill()
            except Exception: pass
        try: shutil.rmtree(user_data_dir, ignore_errors=True)
        except Exception: pass


def _cdp_dispatch_event(ev, console_bucket, resource_bucket, req_url_map, req_type_map):
    """把单个 CDP event 落到 console/network buckets 里。

    console_bucket / resource_bucket 结构与 playwright 分支保持一致——每条 dict 带
    type/text/location（console）或 url/resourceType/status/reason（network）。
    """
    method = ev.get("method")
    params = ev.get("params") or {}
    if method == "Runtime.consoleAPICalled":
        level = params.get("type") or ""
        # console.log/info/debug/warn/error/... —— 只留 error/warning 与 playwright 一致
        if level == "error":
            typ = "error"
        elif level == "warning":
            typ = "warning"
        else:
            return
        parts = []
        for a in (params.get("args") or []):
            v = a.get("value")
            if v is None:
                v = a.get("description") or ""
            parts.append(str(v))
        text = " ".join(parts)[:300]
        url_loc = ""
        st = params.get("stackTrace") or {}
        frames = st.get("callFrames") or []
        if frames:
            url_loc = frames[0].get("url", "")
        if console_bucket is not None:
            console_bucket.append({"type": typ, "text": text, "location": url_loc})
    elif method == "Runtime.exceptionThrown":
        # 未捕获异常 —— playwright 侧走 pageerror，这里合并进 error
        det = params.get("exceptionDetails") or {}
        text = det.get("text") or ""
        exc = det.get("exception") or {}
        desc = exc.get("description") or exc.get("value") or ""
        merged = (text + " " + str(desc)).strip()[:300]
        if console_bucket is not None:
            console_bucket.append({"type": "error", "text": merged, "location": det.get("url", "")})
    elif method == "Log.entryAdded":
        entry = params.get("entry") or {}
        level = entry.get("level") or ""
        if level not in ("error", "warning"):
            return
        text = (entry.get("text") or "")[:300]
        if console_bucket is not None:
            console_bucket.append({"type": level, "text": text, "location": entry.get("url", "")})
    elif method == "Network.requestWillBeSent":
        req_id = params.get("requestId")
        req = params.get("request") or {}
        if req_id:
            req_url_map[req_id] = req.get("url", "")
            req_type_map[req_id] = params.get("type") or "other"
    elif method == "Network.responseReceived":
        resp = params.get("response") or {}
        status = resp.get("status")
        if status and status >= 400:
            reason = "http_4xx" if status < 500 else "http_5xx"
            req_id = params.get("requestId")
            if resource_bucket is not None:
                resource_bucket.append({
                    "url": (resp.get("url") or req_url_map.get(req_id, ""))[:200],
                    "resourceType": params.get("type") or req_type_map.get(req_id, "other"),
                    "status": status,
                    "reason": reason,
                })
    elif method == "Network.loadingFailed":
        req_id = params.get("requestId")
        if resource_bucket is not None:
            resource_bucket.append({
                "url": req_url_map.get(req_id, "")[:200],
                "resourceType": params.get("type") or req_type_map.get(req_id, "other"),
                "status": None,
                "reason": "network_error",
            })


def _cdp_flush_pending_events(ws, console_bucket, resource_bucket, req_url_map, req_type_map):
    """把 WS 客户端里累积的 events pool 抽干到 buckets。

    call() 里读到的非匹配 event 会存进 ws._events；这里一次性 drain。
    再顺便非阻塞地拉一小段（<= 50ms）时间窗口的 event 兜底。
    """
    if not hasattr(ws, "_events"):
        return
    while ws._events:
        _cdp_dispatch_event(ws._events.pop(0), console_bucket, resource_bucket, req_url_map, req_type_map)
    # 非阻塞地再拉一小段，不阻塞主流程
    ev = ws.recv_event(timeout=0.05)
    while ev:
        _cdp_dispatch_event(ev, console_bucket, resource_bucket, req_url_map, req_type_map)
        ev = ws.recv_event(timeout=0.02)


def _pick_free_port():
    """随机拿一个空闲 TCP 端口，避免 hardcode 冲突。"""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _drain_stderr_tail(proc, limit: int = 800) -> str:
    """异常路径用：非阻塞地把 chrome 的 stderr 抽干，返回末尾 limit 字符。

    chrome 崩掉后进程已经死了，read() 不会阻塞；但如果还活着（比如 CDP 端点未起来
    的超时场景），先 kill 掉再读，避免僵在这。任何异常都吞掉——已经在错误处理路径里，
    再抛就把根因盖住了。
    """
    try:
        if proc.poll() is None:
            try: proc.kill()
            except Exception: pass
        data = proc.stderr.read() if proc.stderr else b""
    except Exception:
        return ""
    if not data:
        return ""
    try:
        text = data.decode("utf-8", "replace")
    except Exception:
        return ""
    return text[-limit:]


def _cdp_wait_target(port, timeout=8):
    """轮询 http://127.0.0.1:port/json 拿到 target 页 websocket URL。"""
    t0 = time.time()
    last_err = None
    while time.time() - t0 < timeout:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=1) as r:
                data = json.loads(r.read().decode("utf-8"))
            # 找 type=page 的 target
            for t in data:
                if t.get("type") == "page" and t.get("webSocketDebuggerUrl"):
                    return t["webSocketDebuggerUrl"], t.get("id", "")
            last_err = "无 page target"
        except Exception as e:
            last_err = str(e)
        time.sleep(0.2)
    raise RuntimeError(f"等待 devtools 端点超时 ({timeout}s)：{last_err}")


class _WSClient:
    """极简 websocket 客户端。只支持文本帧、单帧、无掩码扩展；够用来跟 chrome 说话。"""

    def __init__(self, url):
        self.url = url
        self._msg_id = 0
        self._events = []  # 缓存 event（不带 id 的消息）
        self._responses = {}  # id → result

    def __enter__(self):
        u = urlparse(self.url)
        host, port = u.hostname, u.port or 80
        path = u.path or "/"
        self.sock = socket.create_connection((host, port), timeout=10)
        # WebSocket 握手
        key = base64.b64encode(os.urandom(16)).decode()
        req = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(req.encode())
        # 读握手响应直到 \r\n\r\n
        resp = b""
        while b"\r\n\r\n" not in resp:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise RuntimeError("websocket 握手时连接断开")
            resp += chunk
        if b"101" not in resp.split(b"\r\n", 1)[0]:
            raise RuntimeError(f"websocket 握手失败：{resp[:200]!r}")
        # 握手响应之后可能已有数据；把剩余存起来
        header_end = resp.index(b"\r\n\r\n") + 4
        self._buf = resp[header_end:]
        return self

    def __exit__(self, *a):
        try:
            self.sock.close()
        except Exception:
            pass

    def _send_frame(self, payload: bytes, opcode=0x1):
        # opcode 0x1 = 文本；FIN=1
        header = bytearray([0x80 | opcode])
        mask_bit = 0x80  # 客户端必须 mask
        n = len(payload)
        if n < 126:
            header.append(mask_bit | n)
        elif n < 65536:
            header.append(mask_bit | 126)
            header += struct.pack(">H", n)
        else:
            header.append(mask_bit | 127)
            header += struct.pack(">Q", n)
        mask = os.urandom(4)
        header += mask
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        self.sock.sendall(bytes(header) + masked)

    def _recv_exact(self, n, timeout=None):
        if timeout is not None:
            self.sock.settimeout(max(0.001, timeout))
        while len(self._buf) < n:
            chunk = self.sock.recv(max(4096, n - len(self._buf)))
            if not chunk:
                raise RuntimeError("websocket 读时连接断开")
            self._buf += chunk
        out, self._buf = self._buf[:n], self._buf[n:]
        return out

    def _recv_frame(self, timeout=None):
        # 读一帧，返回 payload（bytes）。假设是文本、单帧、无 mask（服务端不 mask）。
        deadline = None if timeout is None else time.time() + timeout
        def rem():
            return None if deadline is None else max(0.001, deadline - time.time())
        # 帧头 2 字节
        h = self._recv_exact(2, rem())
        fin = h[0] & 0x80
        opcode = h[0] & 0x0F
        payload_len = h[1] & 0x7F
        if payload_len == 126:
            payload_len = struct.unpack(">H", self._recv_exact(2, rem()))[0]
        elif payload_len == 127:
            payload_len = struct.unpack(">Q", self._recv_exact(8, rem()))[0]
        payload = self._recv_exact(payload_len, rem()) if payload_len else b""
        if opcode == 0x9:  # ping → 回 pong
            self._send_frame(payload, opcode=0xA)
            return self._recv_frame(rem())
        if opcode == 0x8:  # close
            raise RuntimeError("websocket 收到 close 帧")
        return payload

    def call(self, method, params=None, timeout=25):
        self._msg_id += 1
        req_id = self._msg_id
        msg = {"id": req_id, "method": method, "params": params or {}}
        self._send_frame(json.dumps(msg).encode("utf-8"))
        # 循环读，直到拿到匹配 id 的响应；期间 event 存起来
        deadline = time.time() + timeout
        while time.time() < deadline:
            data = self._recv_frame(deadline - time.time())
            try:
                parsed = json.loads(data.decode("utf-8"))
            except Exception:
                continue
            if parsed.get("id") == req_id:
                if "error" in parsed:
                    raise RuntimeError(f"CDP {method} 报错：{parsed['error']}")
                return parsed
            if "method" in parsed:
                self._events.append(parsed)
        raise RuntimeError(f"CDP {method} 响应超时")

    def recv_event(self, timeout=1.0):
        # 先返回缓存里的 event
        if self._events:
            return self._events.pop(0)
        try:
            data = self._recv_frame(timeout)
        except socket.timeout:
            return None
        except Exception:
            return None
        try:
            parsed = json.loads(data.decode("utf-8"))
        except Exception:
            return None
        if "id" in parsed:
            self._responses[parsed["id"]] = parsed
            return None
        return parsed


def _degraded_report(out_path: Path, viewport):
    """[deprecated] 保留占位；新代码用 _run_chrome_cli 内的 do_one 直接组装。"""
    return {}


def _run_playwright(url, args, name, outdir, result, include):
    """playwright 分支：完整功能。抛异常时由 main() 决定要不要回退。"""
    console_bucket = []
    resource_bucket = []
    with sync_playwright() as p:
        browser, used_exec = _launch_chromium(p, args.exec_path)
        result["engine"] = "playwright"
        result["chromiumExec"] = used_exec
        try:
            ctx = browser.new_context(device_scale_factor=args.scale)
            ctx.add_init_script(INIT_SCRIPT)
            page = ctx.new_page()

            def on_console(msg):
                if msg.type in ("error", "warning"):
                    console_bucket.append({
                        "type": msg.type,
                        "text": (msg.text or "")[:300],
                        "location": (msg.location or {}).get("url", ""),
                    })

            def on_response(resp):
                try:
                    status = resp.status
                    if status >= 400:
                        reason = "http_4xx" if status < 500 else "http_5xx"
                        resource_bucket.append({
                            "url": (resp.url or "")[:200],
                            "resourceType": (resp.request.resource_type if resp.request else "other"),
                            "status": status,
                            "reason": reason,
                        })
                except Exception:
                    pass

            def on_requestfailed(req):
                try:
                    resource_bucket.append({
                        "url": (req.url or "")[:200],
                        "resourceType": req.resource_type or "other",
                        "status": None,
                        "reason": "network_error",
                    })
                except Exception:
                    pass

            page.on("console", on_console)
            page.on("pageerror", lambda e: console_bucket.append({"type": "error", "text": str(e)[:300], "location": ""}))
            page.on("response", on_response)
            page.on("requestfailed", on_requestfailed)

            if args.only in ("desktop", "both"):
                p_out = outdir / f"{name}_desktop.png"
                result["shots"]["desktop"] = one_shot(
                    page, parse_size(args.desktop), url, p_out,
                    console_bucket, resource_bucket,
                    args.max_width, args.jpeg_quality, args.format,
                    args.slice_over_kb, args.slice_over_height, args.slice_height, include,
                    eval_code=args._eval_code)
            if args.only in ("mobile", "both"):
                p_out = outdir / f"{name}_mobile.png"
                result["shots"]["mobile"] = one_shot(
                    page, parse_size(args.mobile), url, p_out,
                    console_bucket, resource_bucket,
                    args.max_width, args.jpeg_quality, args.format,
                    args.slice_over_kb, args.slice_over_height, args.slice_height, include,
                    eval_code=args._eval_code)
        finally:
            browser.close()


def _run_chrome_cli(url, args, name, outdir, result, include):
    """chrome CLI 分支：playwright 不可用时用系统 chrome 保底出图。

    首选路径通过 CDP 注入 INIT_SCRIPT + REPORT_SCRIPT 获取 dom 报告，等价于
    playwright 分支的 lint / structure 能力；只有当 CDP 挂到 --screenshot 兜底路径时
    才降级并标记 reportDegraded=true。
    """
    exec_path = args.exec_path or _find_chromium_fallback()
    if not exec_path:
        raise RuntimeError(
            "没有可用的浏览器：playwright 未装，也没在系统里找到 chrome/edge/chromium。\n"
            "推荐装 playwright：`pip install playwright && playwright install chromium`。\n"
            "或安装任一系统浏览器：Chrome / Edge / Chromium。"
        )
    result["engine"] = "chrome_cli"
    result["chromiumExec"] = exec_path
    if getattr(args, "_eval_code", None):
        result["evalIgnored"] = "chrome_cli 降级模式不支持 --eval 注入，本次已忽略；如需注入 JS，请装 playwright。"

    want_report = ("lint" in include) or ("structure" in include)

    def do_one(viewport, key):
        w, h = viewport
        rep = {}
        console_bucket, resource_bucket = [], []
        dom = None
        if "screenshots" in include or want_report:
            raw_out = outdir / f"{name}_{key}.png"
            dom = _chrome_cli_shoot(
                exec_path, url, viewport, raw_out,
                want_report=want_report,
                console_bucket=console_bucket,
                resource_bucket=resource_bucket,
            )
            if "screenshots" in include:
                post = _postprocess(raw_out, args.max_width, args.jpeg_quality, args.format,
                                    args.slice_over_kb, args.slice_over_height, args.slice_height)
                rep["screenshot"] = str(post["path"])
                rep["screenshotBytes"] = post["bytes"]
                rep["truncated"] = False  # chrome CLI 用固定 canvas，超出会截断——但没法检测
                if post["slices"]:
                    rep["slices"] = [str(s) for s in post["slices"]]
                    rep["sliceHint"] = (
                        f"主图过阈值（字节>{args.slice_over_kb}KB 或 高度>{args.slice_over_height}px），"
                        f"已按 {args.slice_height}px 切片。若主图 Read 失败，改读 slices 里各分片。"
                    )
            elif raw_out.exists():
                # 用户只要 lint/structure 时，把中间产物删掉，别留脏东西
                try: raw_out.unlink()
                except Exception: pass

        # lint / structure：CDP 分支拿到 dom 时走完整装配；只在 --screenshot 兜底
        # 拿不到 dom 时才降级
        if want_report:
            if dom is not None:
                _apply_dom_report(rep, dom, console_bucket, resource_bucket, include)
                rep["reportSource"] = "cdp"
            else:
                if "lint" in include:
                    rep["consoleErrors"] = None
                    rep["consoleWarnings"] = None
                    rep["resourceErrors"] = None
                    rep["horizontalOverflow"] = None
                if "structure" in include:
                    rep["structure"] = None
                rep["reportDegraded"] = True
                rep["reportHint"] = (
                    "chrome CLI 走 --screenshot 兜底路径（CDP 挂了）：拿不到 DOM，"
                    "lint 与 structure 字段为 null。如需完整报告，请装 playwright："
                    "`pip install playwright && playwright install chromium`。"
                )
        return rep

    if args.only in ("desktop", "both"):
        result["shots"]["desktop"] = do_one(parse_size(args.desktop), "desktop")
    if args.only in ("mobile", "both"):
        result["shots"]["mobile"] = do_one(parse_size(args.mobile), "mobile")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", help="本地 HTML 路径或 URL")
    ap.add_argument("--outdir", help="截图输出目录，默认 <src 所在目录>/_shots")
    ap.add_argument("--desktop", default="1440x900")
    ap.add_argument("--mobile", default="390x844")
    ap.add_argument("--only", choices=["desktop", "mobile", "both"], default="both")
    ap.add_argument("--scale", type=float, default=1.0, help="device scale factor（清晰度倍率）")
    ap.add_argument("--exec-path", help="显式指定 chromium 可执行文件路径（覆盖 fallback 扫描）")
    ap.add_argument("--format", choices=["jpg", "png"], default="jpg",
                    help="截图格式，默认 jpg（体积小、模型读图不易崩）；无损需求用 png")
    ap.add_argument("--jpeg-quality", type=int, default=80, help="JPEG 质量 (1-100)，默认 80")
    ap.add_argument("--max-width", type=int, default=1000,
                    help="降到此宽度（保留纵横比），默认 1000；0 表示不降。Pillow 缺失时自动跳过")
    ap.add_argument("--slice-over-kb", type=int, default=800,
                    help="主图字节超过此值（KB）时额外切片输出，默认 800；0 关闭该判定")
    ap.add_argument("--slice-over-height", type=int, default=4000,
                    help="主图像素高度超过此值（px）时额外切片输出，默认 4000；0 关闭该判定。字节或高度任一超阈值即触发。")
    ap.add_argument("--slice-height", type=int, default=3200,
                    help="切片时每片的像素高度，默认 3200")
    ap.add_argument("--include", default="screenshots,lint,structure",
                    help="逗号分隔要输出的模块：screenshots / lint / structure。默认全开")
    ap.add_argument("--eval", dest="eval_code", default=None,
                    help="页面稳态后注入执行的 JS 代码。会被包在 `async () => { … }` 里，可用 await / return；"
                         "返回值 JSON 化后进 shots.<view>.eval.result。用于状态验证（换数据集重渲染、"
                         "切 hash 视图、点按钮等），不用于任意 REPL 探测。仅 playwright 引擎支持。")
    ap.add_argument("--eval-file", dest="eval_file", default=None,
                    help="从文件读取 --eval 代码；与 --eval 二选一。")
    args = ap.parse_args()

    # --eval / --eval-file 二选一：读取要注入的 JS 代码
    args._eval_code = None
    if args.eval_code and args.eval_file:
        _fail_json(2, "--eval 与 --eval-file 二选一，不能同时指定")
    if args.eval_file:
        try:
            args._eval_code = Path(args.eval_file).read_text(encoding="utf-8")
        except Exception as e:
            _fail_json(2, f"读取 --eval-file 失败：{args.eval_file}\n{e}")
    elif args.eval_code:
        args._eval_code = args.eval_code

    # 解析 include
    include = set()
    for tok in (args.include or "").split(","):
        tok = tok.strip()
        if tok in ("screenshots", "lint", "structure"):
            include.add(tok)
    if not include:
        _fail_json(2, f"--include 里没有有效项：{args.include}（支持 screenshots / lint / structure）")

    # 解析 src → url
    try:
        url = to_url(args.src)
    except Exception as e:
        _fail_json(2, f"无法解析 src：{args.src}\n{e}")

    if args.outdir:
        outdir = Path(args.outdir).resolve()
    else:
        base = Path(args.src).resolve() if not args.src.startswith(("http", "file://")) else Path.cwd()
        outdir = base.parent / "_shots"
    outdir.mkdir(parents=True, exist_ok=True)
    name = slug(args.src)

    t0 = time.time()
    result = {
        "src": args.src,
        "url": url,
        "outdir": str(outdir),
        "include": sorted(include),
        "shots": {},
    }

    try:
        # 优先 playwright；失败或未装则回退 chrome CLI
        if HAVE_PLAYWRIGHT:
            try:
                _run_playwright(url, args, name, outdir, result, include)
            except Exception as pw_err:
                # playwright 分支跑失败：退到 chrome CLI 再试
                result["playwrightError"] = str(pw_err)[:400]
                try:
                    _run_chrome_cli(url, args, name, outdir, result, include)
                    result["engineDegraded"] = True
                except Exception as cli_err:
                    result["error"] = {
                        "code": "no_browser",
                        "message": (f"playwright 与 chrome CLI 都无法完成截图：\n"
                                    f"playwright: {pw_err}\nchrome CLI: {cli_err}")[:1000],
                    }
                    result["elapsedSec"] = round(time.time() - t0, 2)
                    print(json.dumps(result, ensure_ascii=False, indent=2))
                    return 3
        else:
            try:
                _run_chrome_cli(url, args, name, outdir, result, include)
                result["engineDegraded"] = True
                result["engineDegradedReason"] = "playwright 未装"
            except Exception as cli_err:
                result["error"] = {"code": "no_browser", "message": str(cli_err)[:1000]}
                result["elapsedSec"] = round(time.time() - t0, 2)
                print(json.dumps(result, ensure_ascii=False, indent=2))
                return 3
    except Exception as e:
        # 兜底：任何未预期异常也走 JSON 通道，别裸抛 traceback
        result["error"] = {"code": "unexpected", "message": str(e)[:1000]}
        result["elapsedSec"] = round(time.time() - t0, 2)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 3

    # 跨视口对比：图表容器在桌面正常、移动端被挤压 → 响应式失效
    # 判据：桌面 width >= 300 且移动 width < 200 且移动 height >= 100（排除装饰型 mini）
    # 前提：same-run 同时截了 desktop / mobile，且各自有 chartContainers
    _emit_responsive_issues(result)
    # 清掉临时字段（DOM 报告里挂的 _chartContainers 只是给 python 侧对比用，
    # 保留在输出里对读报告的人没意义，反而占地方）
    for sh in result.get("shots", {}).values():
        if isinstance(sh, dict):
            sh.pop("_chartContainers", None)

    result["elapsedSec"] = round(time.time() - t0, 2)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _emit_responsive_issues(result: dict):
    """跨视口对比图表容器尺寸：桌面正常但移动端被压扁 → 响应式失效。

    只在同一 run 同时截了 desktop 和 mobile 时才有效。按 id 优先匹配，
    id 缺失时退回 idx（DOM 顺序）。判据（三条 AND）：
      - 桌面宽度 >= 300px（图表在桌面已达可用尺寸）
      - 移动宽度 < mobileViewport * 0.65（明显没占到视口宽——正常单栏
        降级后图表容器约等于 viewport 内宽，扣两侧 padding 也在 0.75 以上）
      - 移动高度 >= 80px（排除塌陷 / fallback 文字）
    这样 cPlayers/cCost 这类"桌面宽、移动单栏 288px"的正常降级不会被报，
    只有 cm1/cm2 这种"双栏 inline-block 没堆叠、被压到 <260px"才命中。
    """
    shots = result.get("shots") or {}
    dt_shot = shots.get("desktop") or {}
    mo_shot = shots.get("mobile") or {}
    dt = dt_shot.get("_chartContainers")
    mo = mo_shot.get("_chartContainers")
    if not dt or not mo:
        return

    # 拿到移动端视口宽——从 structure 里读，缺省用 390（脚本默认 --mobile）
    mobile_vw = ((mo_shot.get("structure") or {}).get("viewport") or {}).get("w") or 390
    threshold = mobile_vw * 0.65

    def key(c):
        return ("id:" + c["id"]) if c.get("id") else ("idx:" + str(c["idx"]))
    mo_by_key = {key(c): c for c in mo}

    issues = []
    for d in dt:
        m = mo_by_key.get(key(d))
        if not m:
            continue
        dw, dh = d["width"], d["height"]
        mw, mh = m["width"], m["height"]
        if dw < 300:
            continue
        if mh < 80:
            continue
        if mw >= threshold:
            continue  # 移动端已经拿到视口大部分宽度 → 正常降级
        issues.append({
            "id": d.get("id") or "",
            "tag": d.get("tag"),
            "cls": d.get("cls"),
            "desktop": {"w": dw, "h": dh},
            "mobile": {"w": mw, "h": mh},
            "mobileViewport": mobile_vw,
            "widthVsViewport": round(mw / mobile_vw, 2),
        })

    if not issues:
        return

    result["responsiveChartIssues"] = issues
    result["responsiveChartIssuesHint"] = (
        "含义：图表容器在桌面正常（>=300px），移动端却没占到视口宽度的 65%——"
        "说明它没跟着媒体查询堆叠成单栏。widthVsViewport 是移动端图表宽度 / 移动视口宽度。"
        "典型根因：容器用了 width:X% + display:inline-block 双栏、或固定 px 宽，"
        "@media(max-width:...) 里漏写单栏堆叠。echarts 被压到这种宽度，grid.left/right "
        "已吃掉全部绘图区，肉眼看是「空的 / 一根线 / 坐标轴叠一起」。"
        " | 修法：在移动断点里给父容器补 grid-template-columns:1fr 或 display:block，"
        "让子图表单栏堆叠、拿到视口全宽。"
        " | 豁免：(1) 故意做的 side-by-side sparkline / dual-panel 迷你图——对照移动截图确认视觉没坏后忽略；"
        "(2) 移动端图表放在侧栏 / drawer 内本来就窄。"
    )



def _fail_json(code: int, message: str):
    """参数/输入错误：打 JSON 后按指定 exit code 退出，不裸抛。"""
    payload = {"error": {"code": "invalid_argument", "message": message}}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.exit(code)


if __name__ == "__main__":
    sys.exit(main())
