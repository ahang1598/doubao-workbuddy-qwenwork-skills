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
import re
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from urllib.parse import unquote, urlparse

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
  // 同一趟遍历里额外收一份不限量的 file:// 引用，供 Python 侧的「JS 拼路径」检测用。
  // 不复用 localImages：它有 20 条上限，截断后漏掉的正是要检测的那些。
  const fileAssetRefs = [];
  const localSeen = new Set();
  const pushLocal = (tag, attr, url) => {
    if (!url || url === document.baseURI) return;
    if (typeof url !== 'string' || !url.startsWith('file://')) return;
    if (localSeen.has(url)) return;
    localSeen.add(url);
    if (fileAssetRefs.length < 200) fileAssetRefs.push({ tag: tag, attr: attr, url: url.slice(0, 400) });
    if (localImages.length >= 20) return;
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

  // 图片固有宽高比过于极端：3:4(0.75) 以下的窄竖条、21:9(2.333) 以上的长横条，
  // 放进任何常规容器都排不好——裁掉主体，或者两侧/上下大量留白。跟 stretchedImages
  // 是两件事：那条查「渲染盒子与固有比例不符」（页面把图拉变形了），这条查素材本身
  // 的比例就不适合排版（生图时没约束比例导致），图片没被拉伸也会命中。
  const extremeAspectImages = [];
  for (const im of document.querySelectorAll('img')) {
    if (extremeAspectImages.length >= 8) break;
    const nw = im.naturalWidth, nh = im.naturalHeight;
    if (!nw || !nh) continue;                          // 未加载 / 解码失败，判不了
    // 装饰性细长条（分隔线、渐变边、纹理条、1px 占位）本来就该是极端比例，不是内容图。
    // 用最小边过滤而不是面积：1200x8 的分隔线面积近万，用面积挡不住
    if (Math.min(nw, nh) < 40) continue;
    const ar = nw / nh;
    // 判定线比 SKILL.md 给模型的规范值（3:4 ~ 21:9）各放宽约 4%：规范值是生图时的目标，
    // 判定线要避免边界误报。实测 2048x872=2.349 只超 21:9(2.333) 的 0.67%，那是想做
    // 21:9 banner 的正常素材，而 2.35:1 本身就是电影宽银幕标准比例；21:9 显示器的实际
    // 比例也在 2.33~2.37 之间浮动。真正要抓的是 1:5、9:16、3:1 这类差一个量级的
    if (ar >= 0.72 && ar <= 2.40) continue;
    const rawSrc = im.currentSrc || im.src || '';
    extremeAspectImages.push({
      natural: nw + 'x' + nh,
      aspect: Math.round(ar * 1000) / 1000,
      shape: ar < 0.72 ? 'too-tall' : 'too-wide',
      renderedBox: Math.round(im.getBoundingClientRect().width) + 'x'
                 + Math.round(im.getBoundingClientRect().height),
      objectFit: getComputedStyle(im).objectFit,
      alt: (im.alt || '').slice(0, 40),
      src: rawSrc.startsWith('data:') ? rawSrc.slice(0, 24) + '...' : rawSrc.slice(0, 80),
    });
  }

  // 平铺多图时反复用同一张：模型在需要多张不同图时偷懒复用一个文件。
  // 只看内容图（渲染 ≥ 100×100）—— 图标、logo、头像占位重复使用是正常做法，
  // 用尺寸把它们挡在外面。data URI 也要能判（页面里可能直接内嵌 data:），
  // 用长度 + 尾部 48 字符做指纹，同一张图的 base64 完全一致。
  const duplicateImages = [];
  {
    const bySrc = new Map();
    let contentImgCount = 0;
    for (const im of document.querySelectorAll('img')) {
      const raw = im.currentSrc || im.src || '';
      if (!raw) continue;
      const r = im.getBoundingClientRect();
      if (r.width < 100 || r.height < 100) continue;
      contentImgCount++;
      const key = raw.startsWith('data:') ? 'data:' + raw.length + ':' + raw.slice(-48) : raw;
      if (!bySrc.has(key)) bySrc.set(key, { src: raw, els: [] });
      bySrc.get(key).els.push(im);
    }
    for (const [, v] of bySrc) {
      if (v.els.length < 2 || duplicateImages.length >= 6) continue;
      const boxes = v.els.map(e => e.getBoundingClientRect());
      // 尺寸是否一致：一致说明是平铺的同级卡片（偷懒复用），不一致更像缩略图+主图
      const sameSize = boxes.every(b => Math.abs(b.width - boxes[0].width) < 4
                                     && Math.abs(b.height - boxes[0].height) < 4);
      // alt 差异是比尺寸更强的信号：**不同的 alt 配同一张图 = 两个不同的东西用了同一张图**。
      // 实测 138 产物的 5 个命中里，alt 相同的两个都是同一产品在列表和详情两处展示（正常），
      // alt 不同的三个都是真偷懒（"招牌拿铁"和"焦糖玛奇朵"共用一张图）
      const alts = v.els.map(e => (e.alt || '').trim()).filter(Boolean);
      const distinctAlts = new Set(alts).size;
      duplicateImages.push({
        count: v.els.length,
        contentImageTotal: contentImgCount,
        sameRenderedSize: sameSize,
        distinctAlts: distinctAlts,
        sizes: boxes.slice(0, 6).map(b => Math.round(b.width) + 'x' + Math.round(b.height)),
        alts: v.els.slice(0, 4).map(e => (e.alt || '').slice(0, 20)),
        // src 保留**尾部**：file:// 绝对路径很长，取前 90 字符全是目录前缀，
        // 看不到文件名，模型没法知道是哪张图
        src: v.src.startsWith('data:') ? v.src.slice(0, 24) + '…(data URI)'
           : (v.src.length > 90 ? '…' + v.src.slice(-88) : v.src),
      });
    }
  }

  // favicon：缺失或指向外部文件
  // 实测 17 个模型原始产物（发布前）只有 1 个写了 favicon —— 缺失率 94%，浏览器 tab 上
  // 是一个空白/默认图标。发布平台会在 head 最前面注入自己的默认 favicon，而浏览器对多个
  // icon link 取最后一个，所以模型写在后面的会覆盖它 —— 写了就一定生效，两个场景都值得写。
  // 只能用 data URI：`link href` 不在发布链路的资源收集白名单里（只认 src 和 CSS url()），
  // 指向 assets/ 的图标文件发布后必然 404，同时也破坏单文件自包含。
  const faviconInfo = (() => {
    const links = [...document.querySelectorAll(
      'link[rel~="icon" i], link[rel="shortcut icon" i], link[rel="apple-touch-icon" i]')];
    if (!links.length) return { present: false };
    const external = [];
    const brokenDataUri = [];
    for (const l of links) {
      const href = (l.getAttribute('href') || '').trim();
      if (!href) continue;
      if (!href.startsWith('data:')) { external.push(href.slice(0, 90)); continue; }
      // data URI 里出现裸 `#` 必然是错的：URL 解析在 `#` 处截断，后面的 SVG 内容全丢，
      // 图标静默不显示。最常见的成因就是 `fill='#0F766E'` 没写成 `fill='%230F766E'`。
      // DOM 侧看不出来——link 在、href 是 data: 开头，只有查字符串才发现
      if (href.includes('#')) brokenDataUri.push(href.slice(0, 70));
    }
    return { present: true, count: links.length,
             externalRefs: external.slice(0, 4),
             unencodedHash: brokenDataUri.slice(0, 3) };
  })();

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

  // ============ 表格列被挤到极窄 ============
  // 实测根因（一个 4 列表格，实际列宽 229 / 406 / 407 / **88** px）：
  //   <th style="width:14%">…<th style="width:24%">…<th style="width:30%">…<th>（第四列没写）
  // 前三列声明的百分比加起来只有 68%，第四列漏写。而 `table-layout: auto` 下声明的百分比
  // 只是「最小期望」——内容长的列会突破它，前三列实际吃掉 1042px（92%），漏写的那列只剩 88px。
  // 88px 装不下中文句子，逐字折了 17 行、每行 3.9 字，把整行行高撑到 424px；表格行高统一，
  // 其余列跟着变成大片空白 —— 一屏只看得到两行就是这么来的。
  // 触发条件用「逐字折行」这个现象（确保真出了问题），reason 指出声明层面的根因。
  // 行数必须用 Range.getClientRects() 量，**不能用单元格高度算** —— 那是被同行最高的
  // 单元格撑起来的，量出来所有单元格都是 17 行。
  const squeezedTableColumns = [];
  {
    const t0 = Date.now(), BUDGET = 800;
    // 取某个单元格的宽度声明：inline style 优先，其次翻样式表。computed 值区分不了
    // 「声明过」和「算出来的」，而这里要判的恰恰是有没有声明
    const declaredWidth = (el) => {
      if (el.style && el.style.width) return el.style.width;
      try {
        for (const sheet of document.styleSheets) {
          let rules; try { rules = sheet.cssRules; } catch (e) { continue; }
          for (const rule of rules) {
            if (!rule.selectorText || !rule.style || !rule.style.width) continue;
            try { if (el.matches(rule.selectorText)) return rule.style.width; } catch (e) {}
          }
        }
      } catch (e) {}
      return null;
    };
    for (const table of document.querySelectorAll('table')) {
      if (squeezedTableColumns.length >= 6 || Date.now() - t0 > BUDGET) break;
      const head = table.querySelector('tr');
      if (!head) continue;
      const headCells = [...head.children];
      const colCount = headCells.length;
      const colWidths = headCells.map(c => Math.round(c.getBoundingClientRect().width));
      // 逐列收集宽度声明，**要扫前几行不能只看表头** —— 实测那个 case 的声明分散在两处：
      // thead 是 inline `style="width:14%"`，tbody 是 class 规则 `td.gree-col{width:39%}`，
      // 后者才是决定性的（22%+39%+39%=100%，把宽度占满）。只看表头会得出完全错误的结论
      const decls = new Array(colCount).fill(null);
      // 同一列在 thead / tbody 各有声明时，浏览器按**最大值**确定列宽，这里同口径。
      // 实测那个 case：thead inline 14/24/30，tbody class 22/39/39 —— 取最大得
      // 22+39+39=100%，正好说明「前三列已占满、第四列没份额」；取 thead 那组只有 68%，
      // 会让人误以为补到 100% 就行
      const setDecl = (i, d) => {
        if (!d) return;
        const cur = decls[i];
        if (!cur) { decls[i] = d; return; }
        if (cur.endsWith('%') && d.endsWith('%') && parseFloat(d) > parseFloat(cur)) decls[i] = d;
      };
      for (const row of [...table.querySelectorAll('tr')].slice(0, 3)) {
        [...row.children].forEach((c, i) => {
          if (i < colCount && (c.colSpan || 1) === 1) setDecl(i, declaredWidth(c));
        });
      }
      const declared = decls.filter(Boolean);
      const pctSum = Math.round(decls.reduce(
        (s, v) => s + (v && v.endsWith('%') ? parseFloat(v) || 0 : 0), 0));
      let reason;
      if (declared.length && declared.length < colCount) {
        reason = 'partial-width-declaration';   // 部分列声明了宽度，漏写的列吃剩余空间
      } else if (pctSum > 0 && pctSum < 95) {
        reason = 'width-sum-under-100';         // 全声明了但加起来不到 100%
      } else {
        reason = 'auto-layout-content-driven';  // 没有声明，纯靠内容长度分配
      }
      for (const c of table.querySelectorAll('td, th')) {
        if (squeezedTableColumns.length >= 6 || Date.now() - t0 > BUDGET) break;
        const txt = (c.textContent || '').trim();
        if (txt.length < 12) continue;                    // 短文本折几行都无所谓，先免费过滤
        const box = c.getBoundingClientRect();
        if (box.width > 160) continue;                    // 宽列不可能每行只放 5 个字，省掉 Range
        const cs = getComputedStyle(c);
        if (cs.writingMode && cs.writingMode !== 'horizontal-tb') continue;   // 刻意竖排不报
        let lines = 0;
        try {
          const r = document.createRange();
          r.selectNodeContents(c);
          lines = r.getClientRects().length;
        } catch (e) { continue; }
        if (lines < 4) continue;
        const perLine = txt.length / lines;
        if (perLine > 5) continue;
        // 行高门槛：真正难受的是「一个窄单元格把整行撑高、其余列全变空白」，不是列窄本身。
        // 移动端 390px 里塞 4-5 列时逐字折行是必然的，不加这道门槛命中率 24%（实测），
        // 全是「窄屏放不下多列表格」这个客观事实，进报告就是噪声。200px 在 844 高的移动
        // 视口里占近 1/4 屏，是「明显异常」的界；实测那个真实 case 的行高是 424px
        if (box.height < 200) continue;
        const maxW = colWidths.length ? Math.max(...colWidths) : 0;
        const minW = colWidths.length ? Math.min(...colWidths) : 0;
        squeezedTableColumns.push({
          reason: reason,
          cellWidth: Math.round(box.width),
          rowHeight: Math.round(box.height),
          lines: lines,
          charsPerLine: Math.round(perLine * 10) / 10,
          textLength: txt.length,
          tableLayout: getComputedStyle(table).tableLayout,
          colWidths: colWidths.slice(0, 10),
          declaredWidths: decls.slice(0, 10),
          declaredPctSum: pctSum || null,
          widthRatio: minW > 0 ? Math.round(maxW / minW * 100) / 100 : null,
          text: txt.slice(0, 30),
        });
      }
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
  const timelineBrokenAxis = [];
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
    // —— 连续性判据专用的两个放宽版识别器 ——
    // isDot 要求圆点「被显式定位」（absolute / justify-self:center），那是对齐判据的反误报手段：
    // 对齐要拿圆点跟轴线比坐标，混进一个装饰圆就得出一个假偏移。连续性判据不比坐标、只看
    // 「相邻两点之间有没有线」，防误报靠的是「≥3 个圆点共线 + 这条线上真的存在线段」这个组合，
    // 所以这里不能沿用那条约束——出问题的写法恰恰是圆点作为 flex 子元素（position:static）。
    const isDotLoose = b => {
      if (b.w < 6 || b.w > 32 || Math.abs(b.w - b.h) > 3) return false;
      const r = b.cs.borderTopLeftRadius || '';
      if (r.indexOf('%') < 0 && num(r) < b.w / 2 - 1) return false;
      return true;
    };
    const visibleColor = c => !!c && c !== 'transparent' && !/,\s*0\s*\)$/.test(c);
    const SEG_THICK = 6;
    // 线段**不设长度下限**（axisDir 要求 ≥60px）：断裂 case 的线段本来就短——实测那个
    // badcase 每段只有 40px，用 60px 的下限会把要找的东西正好过滤掉。
    const collectSeg = (b, sel, out) => {
      const bg = b.cs.backgroundColor, bgImg = b.cs.backgroundImage;
      const painted = visibleColor(bg) || (bgImg && bgImg !== 'none');
      // 刻意的虚线轴（repeating-linear-gradient / dashed border）在几何上本来就是断的，
      // 整条轴一律豁免，否则 100% 误报。
      const dashed = !!(bgImg && bgImg !== 'none' && /gradient/i.test(bgImg));
      const left = b.cx === null ? null : b.cx - b.w / 2;
      // 细长比是必须的：没有它，一个 6×6 的圆点自身就满足「宽≤6 且 高≥6」，会被当成它自己的轴线，
      // 于是每个点都「有线」但覆盖率恒为 0——实测 138 个产物的 2 个命中全是这么来的，全是误报。
      const slim = (long, thin) => long >= Math.max(10, thin * 3);
      if (painted && b.w > 0 && b.w <= SEG_THICK && slim(b.h, b.w) && b.cx !== null && b.cy !== null) {
        out.push({ sel, dir: 'v', cx: b.cx, cy: b.cy, w: b.w, h: b.h, dashed });
      }
      if (painted && b.h > 0 && b.h <= SEG_THICK && slim(b.w, b.h) && b.cx !== null && b.cy !== null) {
        out.push({ sel, dir: 'h', cx: b.cx, cy: b.cy, w: b.w, h: b.h, dashed });
      }
      // border 当轴线：元素自身不窄，但左边框就是那条竖线（实测 59 个产物里 5 个这么写）
      const bw = num(b.cs.borderLeftWidth);
      if (bw >= 0.5 && bw <= SEG_THICK && slim(b.h, bw) && left !== null &&
          visibleColor(b.cs.borderLeftColor) && b.cs.borderLeftStyle !== 'none') {
        out.push({ sel: sel + '(border-left)', dir: 'v', cx: left + bw / 2, cy: b.cy,
                   w: bw, h: b.h, dashed: /dashed|dotted/.test(b.cs.borderLeftStyle) });
      }
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
      const segs = [], looseDots = [];      // 连续性判据用
      const pool = [root].concat([].slice.call(root.querySelectorAll('*'), 0, 400));
      for (const el of pool) {
        for (const pseudo of ['', '::before', '::after']) {
          let b = null;
          try { b = boxOf(el, pseudo); } catch (e) { b = null; }
          if (!b) continue;
          const dir = axisDir(b);
          if (dir) axes[dir].push(Object.assign({ sel: label(el, pseudo) }, b));
          else if (isDot(b)) dots.push(Object.assign({ sel: label(el, pseudo) }, b));
          try { collectSeg(b, label(el, pseudo), segs); } catch (e) {}
          if (isDotLoose(b)) looseDots.push(Object.assign({ sel: label(el, pseudo) }, b));
        }
      }
      // ==== 轴线连续性（俗称「蝌蚪」：每个圆点拖一小截短尾巴，点与点之间断开）====
      // 放在 `if (!dots.length)` 之前：这条判据用的是 looseDots，出问题的写法（圆点是 flex 子元素）
      // 恰好过不了 isDot 的「必须显式定位」，dots 会是空的。
      for (const dir of ['v', 'h']) {
        if (timelineBrokenAxis.length >= 4) break;
        const key = dir === 'v' ? 'cx' : 'cy';      // 共线看这个坐标
        const along = dir === 'v' ? 'cy' : 'cx';    // 沿轴排列看这个坐标
        const thick = d => (dir === 'v' ? d.h : d.w);
        const clusters = [];
        for (const d of looseDots) {
          if (d[key] === null || d[along] === null) continue;
          let c = null;
          for (const x of clusters) if (Math.abs(x.pos - d[key]) <= 3) { c = x; break; }
          if (!c) { c = { pos: d[key], items: [] }; clusters.push(c); }
          c.items.push(d);
          c.pos = c.items.reduce((s, x) => s + x[key], 0) / c.items.length;
        }
        for (const c of clusters) {
          if (timelineBrokenAxis.length >= 4) break;
          if (c.items.length < 3) continue;         // 少于 3 个共线圆点，不足以认定是一条轴
          c.items.sort((a, b) => a[along] - b[along]);
          const mine = segs.filter(s => s.dir === dir && Math.abs(s[key] - c.pos) <= 4);
          if (!mine.length) continue;               // 这条轴上一根线都没有 = 刻意的无连线点列表，豁免
          if (mine.some(s => s.dashed)) continue;   // 刻意的虚线轴，豁免
          const iv = mine.map(s => (dir === 'v'
            ? [s.cy - s.h / 2, s.cy + s.h / 2] : [s.cx - s.w / 2, s.cx + s.w / 2]))
            .sort((a, b) => a[0] - b[0]);
          const merged = [];
          for (const x of iv) {
            const last = merged[merged.length - 1];
            if (last && x[0] <= last[1] + 1) last[1] = Math.max(last[1], x[1]);
            else merged.push([x[0], x[1]]);
          }
          const gaps = [];
          for (let i = 0; i + 1 < c.items.length; i++) {
            const a = c.items[i][along] + thick(c.items[i]) / 2;        // 前一个点的尾
            const b = c.items[i + 1][along] - thick(c.items[i + 1]) / 2; // 后一个点的头
            const span = b - a;
            if (span < 12) continue;                 // 两点几乎贴着，中间有没有线看不出来
            let free = span;
            for (const m of merged) {
              const o = Math.min(b, m[1]) - Math.max(a, m[0]);
              if (o > 0) free -= o;
            }
            gaps.push({ at: a, span: span, uncovered: Math.max(0, free), ratio: Math.max(0, free) / span });
          }
          // 阈值 0.3：正确写法（容器一条线贯穿）实测 ratio 恒为 0；那个 badcase 是 0.62。
          // 留 30% 的余量是给两端各收几 px 的写法（`top:8px;bottom:8px`）和亚像素舍入。
          const bad = gaps.filter(g => g.ratio > 0.3);
          if (!bad.length) continue;
          const worst = bad.reduce((x, y) => (y.ratio > x.ratio ? y : x));
          timelineBrokenAxis.push({
            orientation: dir === 'v' ? 'vertical' : 'horizontal',
            dots: c.items.length,
            gapsMeasured: gaps.length,
            gapsBroken: bad.length,
            worstUncoveredRatio: Math.round(worst.ratio * 100) / 100,
            worstGapPx: Math.round(worst.span * 10) / 10,
            worstUncoveredPx: Math.round(worst.uncovered * 10) / 10,
            atPx: Math.round(worst.at),
            dot: c.items[0].sel,
            line: mine[0].sel,
            lineSegments: mine.length,
            longestSegmentPx: Math.round(Math.max.apply(null, mine.map(s => (dir === 'v' ? s.h : s.w))) * 10) / 10,
            root: shortSel(root),
          });
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

  // ECharts 数值字段里塞了转不成数字的字符串 —— 图元静默不渲染，console 干净
  // 实测 case：柱状图某根柱子凭空消失，tooltip 显示该值是 `~490`（模型想标注「约 490」，
  // 把「约」写成了 `~` 放进数值字段）。ECharts 对无法解析的值直接跳过、不抛异常，
  // 所以 consoleErrors 为空、容器尺寸正常、模型自检「6 个画布全部渲染」——全都对，
  // 只是画布里少了一根柱子。chartContainers 只量容器尺寸，查不到画布内部的数据问题。
  const chartBadValues = [];
  {
    // 只查数值型图表。关系图 / 桑基图 / 树图 / 地图的 data 是节点对象，语义完全不同
    const NUMERIC = ['bar', 'line', 'scatter', 'effectScatter', 'pie',
                     'radar', 'funnel', 'gauge', 'boxplot', 'candlestick'];
    try {
      if (typeof echarts !== 'undefined' && echarts.getInstanceByDom) {
        for (const el of document.querySelectorAll('[_echarts_instance_]')) {
          if (chartBadValues.length >= 8) break;
          let inst = null, opt = null;
          try { inst = echarts.getInstanceByDom(el); } catch (e) { continue; }
          if (!inst) continue;
          try { opt = inst.getOption(); } catch (e) { continue; }
          const seriesList = opt && opt.series || [];
          for (let si = 0; si < seriesList.length; si++) {
            const s = seriesList[si];
            if (!s || NUMERIC.indexOf(s.type) < 0) continue;
            const data = s.data || [];
            const scan = Math.min(data.length, 500);          // 大数据量图表设上限
            for (let i = 0; i < scan; i++) {
              if (chartBadValues.length >= 8) break;
              const d = data[i];
              let v = (d && typeof d === 'object' && !Array.isArray(d)) ? d.value : d;
              // null / undefined / '' 是 ECharts 支持的「无数据」，画断点，可能是刻意的，不报
              if (v === null || v === undefined || v === '') continue;
              if (Array.isArray(v)) continue;                 // [x,y] / [o,c,l,h] 形态，先不管
              if (typeof v === 'number') {
                if (isFinite(v)) continue;
                chartBadValues.push({ chartId: el.id || '', seriesIndex: si, seriesType: s.type,
                  dataIndex: i, rawValue: String(v), kind: 'non-finite-number' });
                continue;
              }
              // 字符串能转数字就没事（ECharts 自己会转）；转不出来的会被静默丢弃
              if (typeof v === 'string' && String(v).trim() !== '' && !isNaN(Number(v))) continue;
              chartBadValues.push({
                chartId: el.id || '',
                seriesName: (s.name || '').slice(0, 24),
                seriesIndex: si, seriesType: s.type, dataIndex: i,
                rawValue: String(v).slice(0, 30),
                itemName: (d && typeof d === 'object' && d.name) ? String(d.name).slice(0, 20) : '',
                kind: 'unparsable-string',
              });
            }
          }
        }
      }
    } catch (e) { /* echarts 未加载或被打包重命名时静默跳过，宁可漏报 */ }
  }

  // 规则 4.6：图表文本里写了 HTML 标签，但那个位置由 canvas 绘制、不解析 HTML
  // ECharts 只有 tooltip 的默认 renderMode（'html'，DOM 浮层）解析 HTML。一旦
  // renderMode 改成 'richText'，tooltip 就画进 canvas —— `<b>` / `<br/>` 全部原样
  // 显示成字面文本，且 <br/> 不换行会把提示框撑成横跨整图的一行。richText 这个名字
  // 有误导性：它指 ECharts 自有的 `rich` 富文本语法，恰恰不支持 HTML。
  // label / axisLabel 同理，它们永远是 canvas 绘制，换行只能用 \n。
  const chartHtmlInCanvasText = [];
  {
    const HTML_RE = /<\s*(?:br|b|i|u|span|div|strong|em|p|font)\b[^>]*>/i;
    // formatter 可以是字符串模板，也可以是函数；函数就读源码找 HTML 字面量
    const probe = (fm) => {
      if (typeof fm === 'string') return HTML_RE.test(fm) ? fm : null;
      if (typeof fm === 'function') {
        let src = '';
        try { src = fm.toString(); } catch (e) { return null; }
        const m = src.match(HTML_RE);
        if (!m) return null;
        const i = Math.max(0, m.index - 30);
        return src.slice(i, m.index + 50).replace(/\s+/g, ' ');
      }
      return null;
    };
    const push = (el, reason, where, sample) => {
      if (chartHtmlInCanvasText.length >= 8) return;
      if (chartHtmlInCanvasText.some(r => r.chartId === (el.id || '') && r.where === where)) return;
      chartHtmlInCanvasText.push({
        reason, where, chartId: el.id || '',
        cls: (el.className || '').toString().slice(0, 40),
        sample: String(sample).slice(0, 90),
      });
    };
    try {
      if (typeof echarts !== 'undefined' && echarts.getInstanceByDom) {
        for (const el of document.querySelectorAll('[_echarts_instance_]')) {
          if (chartHtmlInCanvasText.length >= 8) break;
          let inst = null, opt = null;
          try { inst = echarts.getInstanceByDom(el); } catch (e) { continue; }
          if (!inst) continue;
          try { opt = inst.getOption(); } catch (e) { continue; }
          if (!opt) continue;
          // (a) tooltip.renderMode === 'richText' 且 formatter 产出 HTML
          //     getOption() 把 tooltip 规整成数组；series 上也可以各带一个
          const tips = [].concat(opt.tooltip || []);
          for (const s of (opt.series || [])) if (s && s.tooltip) tips.push(s.tooltip);
          for (const tp of tips) {
            if (!tp || tp.renderMode !== 'richText') continue;
            const hit = probe(tp.formatter);
            if (hit) push(el, 'tooltip-richtext', 'tooltip.formatter', hit);
          }
          // (b) label / axisLabel：canvas 绘制，任何 renderMode 下都不解析 HTML
          for (const s of (opt.series || [])) {
            if (!s) continue;
            for (const k of ['label', 'labelLine', 'endLabel']) {
              const hit = s[k] && probe(s[k].formatter);
              if (hit) push(el, 'canvas-label', 'series.' + k + '.formatter', hit);
            }
          }
          for (const axKey of ['xAxis', 'yAxis', 'radiusAxis', 'angleAxis']) {
            for (const ax of [].concat(opt[axKey] || [])) {
              const hit = ax && ax.axisLabel && probe(ax.axisLabel.formatter);
              if (hit) push(el, 'canvas-label', axKey + '.axisLabel.formatter', hit);
            }
          }
        }
      }
    } catch (e) { /* 同上，静默 */ }
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

  // 规则 8.5：假的展开指示符（chevron 当列表符号）
  // `›` `>` `▸` 这类 chevron / caret 在 UI 惯例里是 disclosure indicator——手风琴的展开箭头、
  // 列表项"进入下一级"的指示器。拿它当静态列表符号，用户会以为能点开，属于假 affordance，
  // 与规则 3 的僵尸按钮同族（那条是"看起来能点的容器"，这条是"看起来能展开的符号"）。
  // 字符集只收 chevron / caret，**不含** `→ ➜ ⇒`——流向箭头在正文里表达因果、流程是合理的。
  // 元素自身或祖先真能交互（绑了 click / <summary> / aria-expanded / role=button / href）时
  // 豁免：那种情况下 chevron 正是正确用法，报出来才是错的。
  const fakeDisclosureBullets = [];
  {
    const CHEV = '>＞›‹»«▸▹▶►❯⟩˃';
    const isChev = (s) => s.length === 1 && CHEV.indexOf(s) !== -1;
    const prefixRe = new RegExp('^([' + CHEV + '])\\s+(\\S)');
    const interactive = (el) => {
      if (el.closest('a[href],button,summary,details,[role="button"],[aria-expanded],[onclick],input,select,textarea,label')) return true;
      let p = el;
      while (p && p !== document.body) {
        if (p.__shot_hasClickListener) return true;
        p = p.parentElement;
      }
      return false;
    };
    const seen = new Set();
    const groups = new Map();   // 同一条 CSS 规则会命中整组 li——按来源聚合，只报代表 + 计数
    const add = (el, via, ch) => {
      if (seen.has(el)) return;
      const cs0 = getComputedStyle(el);
      if (cs0.display === 'none' || cs0.visibility === 'hidden' || +cs0.opacity === 0) return;
      const r = el.getBoundingClientRect();
      if (r.width < 4 || r.height < 4) return;
      seen.add(el);
      const cls = (typeof el.className === 'string' ? el.className : '').trim();
      const key = via + '|' + ch + '|' + (cls || el.tagName);
      const g = groups.get(key);
      if (g) { g.count++; if (g.samples.length < 3) g.samples.push((el.textContent || '').trim().slice(0, 40)); return; }
      if (groups.size >= 8) return;
      const rec = {
        tag: el.tagName.toLowerCase(), via: via, char: ch, count: 1,
        samples: [(el.textContent || '').trim().slice(0, 40)],
        rect: [Math.round(r.left + window.scrollX), Math.round(r.top + window.scrollY), Math.round(r.width), Math.round(r.height)],
      };
      if (cls) rec.cls = cls.slice(0, 60);
      // INIT_SCRIPT 的 hook 只标 Element，document 级委托标不到 —— 给核对提示，不静默漏抓
      let p = el, dd = false;
      while (p && p !== document.body && !dd) {
        if (p.attributes) for (const a of p.attributes) if (a.name.startsWith('data-')) { dd = true; break; }
        p = p.parentElement;
      }
      if (dd) rec.note = 'ancestor-has-data-attr: 可能是 document 级委托的可折叠组件，请核对';
      groups.set(key, rec);
      fakeDisclosureBullets.push(rec);
    };

    // 8.5a：列表项的 ::before / ::after content 是 chevron（最主流形态）
    for (const el of document.querySelectorAll('li, [role="listitem"]')) {
      if (interactive(el)) continue;
      for (const pseudo of ['::before', '::after']) {
        let cs; try { cs = getComputedStyle(el, pseudo); } catch (e) { continue; }
        const raw = (cs.content || '').trim();
        if (!raw || raw === 'none' || raw === 'normal') continue;
        const m = raw.match(/^["'](.*)["']$/);
        const v = m ? m[1] : raw;
        if (isChev(v)) { add(el, 'pseudo' + pseudo, v); break; }
      }
    }

    // 8.5b：ul / ol 的 list-style-type 是 chevron 字符串（`list-style-type: '›'`）
    for (const ul of document.querySelectorAll('ul, ol')) {
      let cs; try { cs = getComputedStyle(ul); } catch (e) { continue; }
      const m = (cs.listStyleType || '').trim().match(/^["'](.*)["']$/);
      if (m && isChev(m[1]) && !interactive(ul)) add(ul, 'list-style-type', m[1]);
    }

    // 8.5c：文本里硬写 chevron 前缀。li 直接算；非 li 需有 ≥2 个同构兄弟也这么写才算伪列表
    {
      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null);
      let n, scanned = 0;
      while ((n = walker.nextNode())) {
        if (++scanned > 4000) break;   // 超长文档保护；前 4000 个文本节点足够定位来源
        const t = (n.nodeValue || '').trim();
        const mm = t && prefixRe.exec(t);
        if (!mm) continue;
        // ASCII `>` / 全角 `＞` 后面紧跟数字是数学比较（"> 60%"），不是列表符号
        if ((mm[1] === '>' || mm[1] === '＞') && /[\d.]/.test(mm[2])) continue;
        const host = n.parentElement;
        if (!host || interactive(host)) continue;
        const li = host.closest('li, [role="listitem"]');
        if (li) { add(li, 'text-prefix', mm[1]); continue; }
        const par = host.parentElement;
        if (!par) continue;
        const sibs = [...par.children].filter(c => c.tagName === host.tagName && c.className === host.className);
        if (sibs.length < 2) continue;
        if (sibs.filter(c => prefixRe.test((c.textContent || '').trim())).length >= 2) {
          add(host, 'pseudo-list-text', mm[1]);
        }
      }
    }
  }

  // 规则 8.6：等宽卡片组最后一行只剩 1 个（孤儿卡片）。判据 N % C == 1。
  // 按 rect.top 聚类分行，不依赖 DOM 顺序；只看等宽栅格形态，瀑布流/自然宽度不判。
  // 最后一个已跨满整行的是刻意处理，不报。
  const orphanCards = [];
  {
    const vis = (el) => {
      const cs = getComputedStyle(el);
      if (cs.display === 'none' || cs.visibility === 'hidden' || +cs.opacity === 0) return false;
      const r = el.getBoundingClientRect();
      return r.width >= 40 && r.height >= 20;
    };
    for (const box of document.querySelectorAll('div,ul,ol,section,main')) {
      if (orphanCards.length >= 6) break;
      const d = getComputedStyle(box).display;
      if (d.indexOf('grid') < 0 && d.indexOf('flex') < 0) continue;
      const kids = [...box.children].filter(vis);
      if (kids.length < 3 || kids.length > 40) continue;
      const br = box.getBoundingClientRect();
      if (br.width < 200) continue;
      const rects = kids.map(k => k.getBoundingClientRect());
      // 等宽判定：宽度极差 ≤ 均值 12%，否则不是等宽栅格
      const ws = rects.map(r => r.width);
      const avg = ws.reduce((a, b) => a + b, 0) / ws.length;
      if (avg <= 0 || (Math.max(...ws) - Math.min(...ws)) / avg > 0.12) continue;
      // 按 top 聚类分行（4px 容差）
      const byTop = new Map();
      for (const r of rects) {
        const k = Math.round(r.top / 4) * 4;
        byTop.set(k, (byTop.get(k) || 0) + 1);
      }
      const rows = [...byTop.entries()].sort((a, b) => a[0] - b[0]).map(e => e[1]);
      if (rows.length < 2 || rows[rows.length - 1] !== 1 || rows[0] < 2) continue;
      // 2 列出现孤儿 ⟺ N 为奇数 ⟺ 无解（换 1 列或 3 列都不更好），报了也改不动 —— 静默
      if (rows[0] === 2) continue;
      if (rects[rects.length - 1].width > br.width * 0.7) continue;   // 已跨满整行
      const cls = (typeof box.className === 'string' ? box.className : '').trim();
      const rec = {
        tag: box.tagName.toLowerCase(), count: kids.length, cols: rows[0], rows: rows,
        rect: [Math.round(br.left + window.scrollX), Math.round(br.top + window.scrollY),
               Math.round(br.width), Math.round(br.height)],
      };
      if (cls) rec.cls = cls.slice(0, 60);
      orphanCards.push(rec);
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
    fileAssetRefs: fileAssetRefs,
    stretchedImages: stretchedImages,
    extremeAspectImages: extremeAspectImages,
    duplicateImages: duplicateImages,
    overlappingText: overlappingText,
    clippedText: clippedText,
    pseudoOverflow: pseudoOverflow,
    deadButtons: deadButtons,
    misalignedBlocks: misalignedBlocks,
    unevenColumns: unevenColumns,
    squeezedTableColumns: squeezedTableColumns,
    timelineAlignment: timelineAlignment,
    timelineBrokenAxis: timelineBrokenAxis,
    textCandidates: textCandidates,
    docSize: docSize,
    chartContainers: chartContainers,
    chartBadValues: chartBadValues,
    chartHtmlInCanvasText: chartHtmlInCanvasText,
    unsafeHrefRefs: unsafeHrefRefs,
    invisibleAnimations: invisibleAnimations,
    slopFonts: slopFonts,
    emojiUsage: emojiUsage,
    fakeDisclosureBullets: fakeDisclosureBullets,
    orphanCards: orphanCards,
    viewportMeta: viewportMeta,
    faviconInfo: faviconInfo,
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


def _plan_slices(page_h, scale: float, slice_out_h: int):
    """把文档按「输出像素高度 slice_out_h」切成 CSS 坐标区间，返回 [(y, h), ...]。

    CSS 步长向下取整：宁可多切一片，也不要某片输出超过 slice_out_h——超了就等于没切。
    slice_out_h 传了 0 或负数时不退化成逐像素切（那会对长页发起上万次截图），
    直接落回默认 3200。
    """
    if slice_out_h <= 0:
        slice_out_h = 3200
    step = max(1, int(slice_out_h / scale)) if scale > 0 else max(1, slice_out_h)
    plan, y = [], 0
    while y < page_h:
        plan.append((y, min(step, page_h - y)))
        y += step
    return plan


def _capture_with_clip(shoot, page_w, page_h, out_path: Path, fmt: str, *,
                       dsf: float, max_width: int, slice_over_kb: int,
                       slice_over_height: int, slice_height: int,
                       budget_sec: float = 60.0) -> dict:
    """整页截一张；输出超阈值时再按 clip 分片补截。

    `shoot(clip, dest)` 由各引擎分支注入，负责编码与落盘；这里只决定「切几片、
    每片是文档的哪一段」。clip 用 CSS 像素 + scale，**裁剪、降宽、编码在浏览器里
    一次完成**——不需要 Pillow，也就不存在「缺 Pillow 就退化成一张读不了的原图」。

    `dsf` 是 `--scale`（设备像素倍率）。注意 CDP 的 `clip.scale` 会**覆盖**而不是叠加
    context 的 deviceScaleFactor：实测 DSF=2 + clip.scale=1 输出的仍是 CSS 尺寸。
    所以倍率必须自己算进去，否则 `--scale` 会变成 no-op。语义与改动前对齐——
    先按设备倍率放大，超过 --max-width 再压回上限。

    返回 {"path": 主图, "slices": [...], "bytes": 主图字节数}；分片失败时额外带
    "sliceError"，但主图一定有效。主图本身截不出来（如超过 chrome 位图上限）时，
    退化成「只有分片」——每片都小得多，往往仍能成功。

    `budget_sec` 是**分片阶段的总时间预算**。分片是 N 次独立的 CDP 调用，每次都有自己的
    超时，长页切十几片时累计可以卡住好几分钟；自检卡死对调用方是最难排查的失败模式，
    所以超预算就放弃分片、退回主图，而不是一直等下去。
    """
    dsf = dsf if dsf and dsf > 0 else 1.0
    scale = dsf
    if max_width > 0 and page_w * dsf > max_width:
        scale = max_width / page_w
    main = out_path.with_suffix(".jpg" if fmt == "jpg" else ".png")
    # 上一轮如果跑的是另一种格式，同名异后缀的旧图会留在目录里误导读图
    if main != out_path and out_path.exists():
        try: out_path.unlink()
        except Exception: pass
    # 旧分片同理：这轮切 3 片、上轮切 5 片时，_p4of5 / _p5of5 会残留。
    # 用正则再筛一遍，避免 glob 的 * 吃掉手工放进来的同前缀文件。
    _slice_re = re.compile(re.escape(main.stem) + r"_p\d+of\d+" + re.escape(main.suffix) + r"$")
    for stale in main.parent.glob(f"{main.stem}_p*of*"):
        if _slice_re.match(stale.name):
            try: stale.unlink()
            except Exception: pass

    main_err = None
    # 先删掉同名旧主图：截失败时如果留着上一轮的同名文件，main.exists() 会为真，
    # 报告就把**上一轮的图**当成本轮产物交出去了——这比没有图更坏。
    if main.exists():
        try: main.unlink()
        except Exception: pass
    try:
        shoot({"x": 0, "y": 0, "width": page_w, "height": page_h, "scale": scale}, main)
    except Exception as e:
        # 整页截不出来不代表分片也不行——主图一张要装下整页，分片每张只有一段
        main_err = f"{type(e).__name__}: {e}"[:200]
        # 写到一半失败会留个截断文件，同样会被 main.exists() 当成有效主图
        try: main.unlink()
        except Exception: pass

    res = {"path": main, "slices": [],
           "bytes": main.stat().st_size if main.exists() else 0}
    # 注意与改动前的一处**有意不同**：旧 _postprocess 在 `--format png --max-width 0` 时
    # 直接返回、顺带跳过了切片。那个短路会让「主图过阈值自动切片」这条承诺在 PNG 下失效，
    # 而超限图读不了正是本次要解决的问题，所以这里不跟随——切片只看阈值，不看格式。
    over = (main_err is not None
            or (slice_over_kb > 0 and res["bytes"] // 1024 > slice_over_kb)
            or (slice_over_height > 0 and page_h * scale > slice_over_height))
    if not over:
        return res
    plan = _plan_slices(page_h, scale, slice_height)
    if len(plan) < 2 and main_err is None:
        return res  # 切不出第二片，分片没有意义
    n = len(plan)
    deadline = time.time() + budget_sec if budget_sec and budget_sec > 0 else None
    try:
        for i, (y, h) in enumerate(plan):
            if deadline and time.time() > deadline:
                raise RuntimeError(f"分片累计超过 {budget_sec:g}s 预算（已完成 {i}/{n} 片），放弃分片")
            sp = main.with_name(f"{main.stem}_p{i + 1}of{n}{main.suffix}")
            try:
                shoot({"x": 0, "y": y, "width": page_w, "height": h, "scale": scale}, sp)
            except Exception:
                # 这一片自己可能已经落了个截断文件，一并清掉再往上抛
                try: sp.unlink()
                except Exception: pass
                raise
            res["slices"].append(sp)
    except Exception as e:
        # 分片失败不该拖垮整次自检：清掉半成品，退回「只有整页主图」
        for sp in res["slices"]:
            try: sp.unlink()
            except Exception: pass
        res["slices"] = []
        res["sliceError"] = f"{type(e).__name__}: {e}"[:200]
    if main_err is not None:
        if not res["slices"]:
            # 主图和分片全军覆没：这次真没图。抛出去让上层按旧版行为降级
            # （playwright 分支退到 chrome_cli，chrome_cli 退到 --screenshot），
            # 别返回一个指向不存在文件的 path 让读图方去撞墙。
            raise RuntimeError(f"整页与分片都截不出来：{main_err}"
                               + (f"；分片：{res['sliceError']}" if res.get("sliceError") else ""))
        res["mainError"] = main_err
        # 主图不可信——即使残留文件还在（unlink 失败），它也是截断的或上一轮的。
        # 无条件把 path/bytes 指向首个分片，两者始终对应同一个真实可读的文件。
        res["path"] = res["slices"][0]
        res["bytes"] = res["path"].stat().st_size
    return res


def _page_content_size(send, evaluate, viewport):
    """拿文档的 CSS 内容尺寸，用于 clip 全页截图。返回 (w, h, degraded_reason)。

    首选 `Page.getLayoutMetrics().cssContentSize`——它就是 captureBeyondViewport 用来
    定全页尺寸的那个值，实测与 full_page 截图的真实尺寸逐例相等。
    拿不到就退到 `documentElement.scrollWidth/Height`：语义明确是 CSS 像素，且实测在
    绝对定位溢出文档流时仍等于真值（`body.scrollHeight` 会算少，所以不用它）。
    **不采用同一响应里 deprecated 的 `contentSize`**——它在存在 page scale factor 时
    可能是设备像素，单位取错会让 clip 尺寸整体翻倍或减半，比拿不到更糟。

    **退到视口尺寸是最后手段，那意味着长页只会截到首屏，必须让报告说出来**，
    否则会出现「只有首屏却报 truncated:false」这种最坏情况：静默截少。
    """
    lm = send("Page.getLayoutMetrics") or {}
    box = lm.get("cssContentSize") or {}
    if box.get("width") and box.get("height"):
        return box["width"], box["height"], None
    try:
        sz = evaluate()
        if sz and sz[0] and sz[1]:
            return sz[0], sz[1], None
    except Exception:
        pass
    return viewport[0], viewport[1], (
        "拿不到文档内容尺寸（getLayoutMetrics 无 cssContentSize，"
        "scrollWidth/Height 也取不到），已退回视口尺寸——**长页只截到了首屏**。"
    )


def _cdp_shooter(send, fmt: str, quality: int):
    """造一个 shoot(clip, dest)：走 CDP Page.captureScreenshot 直出。

    `send(method, params) -> result dict`——playwright 的 CDPSession 与本文件内的
    最小 websocket 客户端返回层级不同，由调用方各自包一层，这里只认 result。
    """
    def shoot(clip, dest: Path):
        params = {
            "format": "jpeg" if fmt == "jpg" else "png",
            "clip": clip,
            "captureBeyondViewport": True,
            "fromSurface": True,
        }
        if fmt == "jpg":
            params["quality"] = quality
        data = (send("Page.captureScreenshot", params) or {}).get("data")
        if not data:
            raise RuntimeError("Page.captureScreenshot 返回空 data")
        dest.write_bytes(base64.b64decode(data))
    return shoot


def _apply_capture(rep: dict, cap: dict, slice_over_kb: int,
                   slice_over_height: int, slice_height: int) -> None:
    """把截图结果装进单个视口的报告。两条引擎分支共用，别再各写一份。"""
    rep["screenshot"] = str(cap["path"])
    rep["screenshotBytes"] = cap["bytes"]
    if cap["slices"]:
        rep["slices"] = [str(s) for s in cap["slices"]]
        rep["sliceHint"] = (
            f"主图过阈值（字节>{slice_over_kb}KB 或 高度>{slice_over_height}px），"
            f"已按 {slice_height}px 切片。若主图 Read 失败，改读 slices 里各分片。"
        )
    if cap.get("sliceError"):
        rep["sliceError"] = cap["sliceError"]
        rep["sliceErrorHint"] = (
            "主图过阈值但分片补截失败，只有整张主图可用。主图若 Read 不动，"
            "就只按 lint 字段改代码，别把没看过的截图当成看过了。"
        )
    if cap.get("mainError"):
        rep["screenshotMainError"] = cap["mainError"]
        rep["screenshotMainErrorHint"] = (
            "整页主图没截出来（多半是页面过长超过 chrome 位图上限），"
            "已改为只提供分片。**按 slices 逐张 Read**；slices 也为空时这次没有可用截图，"
            "只能按 lint 字段改代码。"
        )
    if cap.get("sizeDegraded"):
        rep["screenshotSizeDegraded"] = cap["sizeDegraded"]


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
             eval_code=None, scale=1.0):
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
        # 走 CDP 而不是 page.screenshot：clip 里带 scale，裁剪 + 降宽 + 编码一次做完，
        # 省掉「先截一张巨大 PNG 再用 Pillow 后处理」那一轮解码/重编码。
        cdp = page.context.new_cdp_session(page)
        try:
            def _send(method, params=None):
                return cdp.send(method, params or {})
            page_w, page_h, size_degraded = _page_content_size(
                _send,
                lambda: page.evaluate("() => [document.documentElement.scrollWidth,"
                                      " document.documentElement.scrollHeight]"),
                (w, h))
            cap = _capture_with_clip(
                _cdp_shooter(_send, fmt, jpeg_quality), page_w, page_h, out_path, fmt,
                dsf=scale, max_width=max_width, slice_over_kb=slice_over_kb,
                slice_over_height=slice_over_height, slice_height=slice_height)
            if size_degraded:
                cap["sizeDegraded"] = size_degraded
        finally:
            try: cdp.detach()
            except Exception: pass
        _apply_capture(report, cap, slice_over_kb, slice_over_height, slice_height)
        # chromium canvas 上限约 30000px，单张装不下就会被截断。
        # 但分片是一段段截的，每段都远小于上限——只要出了分片，内容其实是全的，
        # 这时再报 truncated 会让读图方以为内容缺失而放弃那些完整分片。
        if page_h and page_h > 30000 and not cap["slices"]:
            report["truncated"] = True
            report["truncatedHint"] = f"页面高度 {page_h}px 超过 chromium 单张截图上限，实际截取被截断。"
        else:
            report["truncated"] = False

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
    # fileAssetRefs 同理：判「路径是否静态写在源码里」要读 HTML 原文，
    # 这个函数拿不到文件路径，先原样带出去，由 main 统一处理
    report["_fileAssetRefs"] = dom.get("fileAssetRefs") or []
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
                " | 修法：对每张图跑 `lark-cli drive +html-image-upload --file <图片路径>`，"
                "把返回里 data.url 的链接换进 <img src>；图片文件本身保留在 assets/ 里不要删。"
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
        extreme_ar = dom.get("extremeAspectImages") or []
        if extreme_ar:
            report["extremeAspectImagesWarning"] = extreme_ar
            report["extremeAspectImagesHint"] = (
                "含义：图片**素材本身**的宽高比过于极端，超出了 3:4 ~ 21:9（竖版到宽条形）"
                "这个能正常排版的区间。shape=too-tall 是窄竖条（如 1:5、9:16），"
                "too-wide 是长横条（如 3:1）。放进常规容器只有两种结果：`cover` 裁掉大部分主体，"
                "或 `contain` 在两侧/上下留出大片空白——**换个端也一样不好看**，不是响应式能救的。"
                " | 与 stretchedImages 的区别：那条查「页面把图拉变形了」，这条查「素材比例本身不适合排版」，"
                "图片没被拉伸也会命中，两条互不重叠。"
                " | 修法：重新生成这张图，在生图 prompt 里指定 3:4 ~ 21:9 之间的比例"
                "（Banner / Hero 用 16:9 或 21:9，章节题图用 3:2，方形插图用 1:1）。"
                "只调 CSS 没有用——固有比例不变，裁切和留白的取舍还在。"
                " | 豁免（本项是 warning，不是必改）："
                "(1) **用户自己提供的素材不要动**——SKILL 规定用户素材第一优先、不得擅自替换，"
                "本规则分不清图是生成的还是用户给的，命中用户素材时忽略即可；"
                "(2) 手机 UI 设计稿、竖版海报、二维码长图等媒介本身就要求极端比例的，"
                "对着截图确认是设计意图后忽略；"
                "(3) **检索来的真实产品图**（球拍、手机、瓶装商品这类本身就竖长的实物）不要重新生成——"
                "SKILL 规定忠实呈现真实产品要用检索，生成图会失真造假。这种情况改容器不改图："
                "给它一个匹配的竖向容器，或用 `contain` + 收窄容器宽度，避免两侧大片留白；"
                "(4) 最小边 < 40px 的分隔线、纹理条、渐变边不报。"
            )
        dup_imgs = dom.get("duplicateImages") or []
        if dup_imgs:
            report["duplicateImagesWarning"] = dup_imgs
            report["duplicateImagesHint"] = (
                "含义：同一张图片文件被用在多处（count 是次数，contentImageTotal 是页面内容图总数）。"
                "需要多张不同图时复用一个文件是高频偷懒，典型是画廊、产品网格、多图平铺——"
                "视觉上一眼就看出重复，可信度直接崩。"
                " | **先看 distinctAlts（这几处 alt 文本的去重数）**，它比尺寸更能说明问题："
                "≥2 表示不同的东西共用了同一张图（实测「招牌拿铁」和「焦糖玛奇朵」共用一张），"
                "那就是要改的；=1 或 0 表示同一个东西在多处展示（列表页 + 详情区），通常正常。"
                "再结合 sameRenderedSize：true 是平铺的同级卡片，false 更像主图 + 缩略图。"
                "**distinctAlts ≥ 2 且 sameRenderedSize=true 时几乎可以确定是偷懒**，直接改。"
                " | 修法：给每个位置配不同的图。生图时把 prompt 写出差异（不同角度、不同场景、不同主体），"
                "别只改一两个词；素材确实凑不够时，减少展示数量，或改用不依赖图片的形式（图标 + 文字卡片），"
                "**不要用重复的图占位**。"
                " | 豁免：(1) 品牌 logo、作者头像、统一的占位符按设计就该一致；"
                "(2) 轮播/对比场景刻意用同一张图做前后对照；"
                "(3) 渲染尺寸 < 100×100 的图标、装饰小图本规则不检查——那些重复使用是正常做法。"
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
        squeezed = dom.get("squeezedTableColumns") or []
        if squeezed:
            report["squeezedTableColumns"] = squeezed
            report["squeezedTableColumnsHint"] = (
                "含义：表格某列被挤到极窄（cellWidth），里面的中文逐字折行——charsPerLine 是每行"
                "平均字数，lines 是实际折行数。**表格行高是统一的**，所以这一个窄单元格把整行撑到 "
                "rowHeight 那么高，其余列跟着变成大片空白：表现就是一屏只看得到一两行、版面全是空档。"
                " | reason=partial-width-declaration（最常见）：**部分列写了 width、有列漏写**。"
                "实测形态是前三列 `style=\"width:14%\"` / `24%` / `30%`，第四列没写——"
                "declaredWidths 里的 null 就是漏写的列。而 `table-layout: auto` 下声明的百分比只是"
                "「最小期望」，内容长的列会突破它，于是漏写的那列只拿到剩余的 88px。"
                "修法：**给所有列都写宽度、加起来正好 100%**，并给表格加 `table-layout: fixed` "
                "让声明被严格执行。文字多的列给大比例，标签列给小比例。"
                " | reason=width-sum-under-100：所有列都声明了但 declaredPctSum 不到 100，"
                "剩余空间的分配由内容决定，同样会挤出一个窄列。修法：把百分比补齐到 100%。"
                " | reason=auto-layout-content-driven：一列都没声明，纯按内容长度分配。"
                "修法：用 `<colgroup><col style=\"width:25%\">` 显式给出各列宽度 + `table-layout: fixed`。"
                " | 移动端修法不同：窄屏放不下多列表格，调列宽比例没用。两种做法——"
                "(a) 用媒体查询把表格改成卡片式（每行变一张卡，字段名和值上下排）；"
                "(b) 外面套 `<div style=\"overflow-x:auto\">` 并给 table 设 `min-width`（如 600px），"
                "让它横向滚动而不是压扁。**做 (b) 时要确认滚动条或渐变提示可见**，"
                "否则用户不知道右边还有内容——右侧列被静默裁掉比压扁更糟。"
                " | 豁免：(1) `writing-mode` 非 horizontal-tb 的刻意竖排不报；"
                "(2) 单元格文本 < 12 字、或列宽 > 160px 的不报；"
                "(3) 折行数 < 4 行、或每行 > 5 字的不报——那是正常折行；"
                "(4) **行高 < 200px 的不报**——移动端窄屏放不下多列表格时列窄是必然的，"
                "只有行高被撑到明显异常（占近 1/4 屏）才算问题。所以本规则报出来的都是"
                "「一行吃掉大半屏」那种，不是普通的窄列。"
            )
        broken_axis = dom.get("timelineBrokenAxis") or []
        if broken_axis:
            report["timelineBrokenAxis"] = broken_axis
            report["timelineBrokenAxisHint"] = (
                "含义：时间轴的轴线在节点之间断开了——每个圆点只拖着一小截短线，下一个圆点前有一段空白，"
                "视觉上是一串「蝌蚪」而不是一条串起所有节点的轴。worstUncoveredRatio 是相邻两点之间"
                "没被线覆盖的比例（0.62 = 六成是空的），worstGapPx / worstUncoveredPx 是该处的间距与空白长度，"
                "atPx 是断裂处的页面 y 坐标。"
                " | 根因几乎都是**轴线被切成一段一段挂在每个节点上，而那一段没能撑到下一个节点**。"
                "最典型的写法：节点行用 grid、轴列里放一个 `.line` 元素靠 `flex:1` 撑高，"
                "父级却写了 `align-items:start`——grid item 不再 stretch，轴列高度塌缩成内容高，"
                "`flex:1` 没有剩余空间可分，只剩 `min-height` 那点兜底值。"
                " | 修法：让轴线的长度不再是被声明的量。"
                "(a) 最简单——轴线画在**整个时间轴容器**上一条贯穿到底（`.timeline{position:relative}` + "
                "`.timeline::before{position:absolute;top:0;bottom:0;left:...;width:2px}`），线不分段就没有接缝可断，"
                "实测 59 个真实时间轴里 56 个是这么写的；"
                "(b) 若坚持每行画一段——让轴列自己就是线（`width:2px;justify-self:center;background:...`，"
                "高度交给 grid 默认的 stretch），并把行间距放进内容列的 `padding-bottom`，不要用 `gap` / `margin` 把行撑开。"
                " | 顺带：`min-height:40px` 这类兜底值是这个 bug 变隐蔽的原因——没有它，线会是 0 高、一眼就看出来；"
                "有了它，断裂伪装成「设计就这样」。"
                " | 豁免（已在规则内自动排除，不会报出来）：(1) 刻意的虚线/点线轴"
                "（`repeating-linear-gradient` 或 `border-style:dashed`）；(2) 整条轴上一根线都没有的"
                "点列表式设计；(3) 共线圆点少于 3 个、或相邻两点间距不足 12px 的。"
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
        bad_vals = dom.get("chartBadValues") or []
        if bad_vals:
            report["chartBadValues"] = bad_vals
            report["chartBadValuesHint"] = (
                "含义：ECharts 的 `series.data` 里有**转不成数字的值**（rawValue 是原始内容）。"
                "ECharts 遇到这种值直接跳过、**不抛异常**——所以柱子/折线点凭空少一个，而 "
                "consoleErrors 是空的、容器尺寸也正常、画布确实渲染了。"
                "光看 console 和「图表有没有出来」发现不了，只有对着截图数图元才看得出。"
                " | 最常见的成因是**想在数值里表达额外信息**：`\"~490\"`（约等于）、`\"1,234\"`"
                "（千分位逗号）、`\"12%\"`（带单位）、`\"约 490\"`、`\"N/A\"`、`\"-\"`。"
                " | 修法：`data` 只放纯数字（`490`），要表达的信息挪到别处——"
                "估算/约等于用 `label: { formatter: '~{c}' }`，单位写进 `yAxis.name` 或 "
                "`tooltip.valueFormatter`，千分位用 `label.formatter` 里的 `toLocaleString()`。"
                "确实没有数据就写 `null`（ECharts 支持，会画成断点），不要写 `\"N/A\"` 这类占位文字。"
                " | kind=non-finite-number 是 `NaN` / `Infinity`，通常来自除零或字符串运算，"
                "要回去查算这个值的代码。"
                " | 豁免：`null` / `undefined` / `''` 本规则不报——那是 ECharts 支持的「无数据」，"
                "可能是刻意的；关系图 / 桑基图 / 树图 / 地图的 data 是节点对象，不在检查范围内。"
            )
        html_in_canvas = dom.get("chartHtmlInCanvasText") or []
        if html_in_canvas:
            report["chartHtmlInCanvasText"] = html_in_canvas
            report["chartHtmlInCanvasTextHint"] = (
                "含义：图表文本里写了 HTML 标签，但那个位置由 **canvas 绘制、不解析 HTML**——"
                "`<b>` / `<br/>` 会原样显示成字面文本给用户看到。"
                "而且 `<br/>` 不换行，一条多行提示会被拉成横跨整张图的一行，右侧内容直接被截掉。"
                "**截图上能看见裸标签，但 consoleErrors 是空的、图表本身渲染正常**，只看有没有报错发现不了。"
                " | reason=tooltip-richtext：`tooltip.renderMode: 'richText'` + formatter 返回 HTML。"
                "ECharts 只有 tooltip 的**默认** renderMode（`'html'`，DOM 浮层）解析 HTML；"
                "改成 `richText` 就画进 canvas 了。`richText` 这个名字有误导性——它指的是 ECharts "
                "自有的 `rich` 富文本语法，恰恰不支持 HTML。"
                "修法（二选一）：① 删掉 `renderMode: 'richText'` 回到默认，HTML 立刻生效——"
                "想让提示框不超出图表范围用 `confine: true` 就够了，不需要动 renderMode；"
                "② 保留 richText，则把 `<br/>` 换成 `\\n`、`<b>x</b>` 换成 ECharts 的 `rich` 样式段"
                "（`{a|x}` + `rich: { a: { fontWeight: 'bold' } }`）。"
                " | reason=canvas-label：`series.label` / `axisLabel` 的 formatter 里有 HTML。"
                "这两个位置**任何配置下都是 canvas 绘制**，没有「切回 HTML」的选项："
                "换行只能用 `\\n`，加粗/换色只能用 `rich`。"
                " | 豁免：tooltip 在默认 renderMode 下写 HTML 是**正确用法**，本规则不报。"
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
        fake_disc = dom.get("fakeDisclosureBullets") or []
        if fake_disc:
            report["fakeDisclosureBulletsWarning"] = fake_disc
            report["fakeDisclosureBulletsHint"] = (
                "warning · 含义：列表项拿 chevron / caret（`›` `>` `▸` `»` `❯` 等）当项目符号，"
                "但这些元素**并不可点击**。chevron 在 UI 惯例里是 disclosure indicator——手风琴的展开箭头、"
                "列表项\"进入下一级\"的指示器，用户看到会尝试去点、点了没反应，"
                "属于和僵尸按钮同族的假 affordance（`via` 字段说明来源：`pseudo::before` / "
                "`list-style-type` / `text-prefix` / `pseudo-list-text`）。"
                " | 修法：要项目符号就用真正表示\"并列\"的记号——`•`（U+2022）、`‣`、`–`，或者 `list-style: disc`；"
                "更干净的做法是干掉符号，只靠缩进和行距分隔，同一页面里同级信息块的呈现方式要一致。"
                "**反过来说：如果这些列表项本来就该能展开，那不是改符号，是补上真实的展开交互**"
                "（`<details>/<summary>` 或挂 click handler + `aria-expanded`）。"
                " | 豁免：(1) 元素或祖先真绑了 click / 是 `<summary>` / 有 `aria-expanded` / 有 `href` 的**不会报**——"
                "那时 chevron 是正确用法；带 `note: ancestor-has-data-attr` 的说明交互可能挂在 document 级委托上、"
                "本规则的 hook 探测不到，核对一下确实能点就忽略；"
                "(2) 面包屑导航、路径指示（`首页 › 产品 › 详情`）里 chevron 是分隔符不是项目符号，误报可忽略；"
                "(3) 内容本身就是在讲这些符号（键盘按键说明、Unicode 科普、终端提示符 `>` 的教程）。"
            )
        orphans = dom.get("orphanCards") or []
        if orphans:
            report["orphanCardsWarning"] = orphans
            report["orphanCardsHint"] = (
                "warning · 含义：等宽卡片组最后一行只剩 1 个（`rows` 是每行个数，如 `[3,1]`），"
                "右侧拖一大片空白、上重下轻。判据是 `N % C == 1`（卡片数对列数取余）。"
                " | 修法：让列数序列**跳过**这一档——4 张走 `4 → 2 → 1`（跳过 3 列）。"
                "卡片数固定就直接给这个栅格改断点即可；数量运行时才定，"
                "用 `.cards:has(> :nth-child(4):last-child)` 配媒体查询切列数，"
                "**通用那条要写成 `:not(:has(...))` 与它互斥**，否则 `:has()` 特异性更高，会压住宽屏那档、"
                "把 4 张永久钉在 2 列。"
                " | 豁免：(1) 2 列档不报——那时孤儿等价于 N 为奇数，无解；"
                "(2) 最后一个已跨满整行的不报；(3) 瀑布流、自然宽度、刻意的非对称布局。"
            )
        fav = dom.get("faviconInfo") or {}
        if fav and (not fav.get("present") or fav.get("externalRefs") or fav.get("unencodedHash")):
            report["faviconWarning"] = fav
            if not fav.get("present"):
                _fav_what = ("没有任何 favicon 声明——浏览器 tab、书签、历史记录里显示的是"
                             "空白默认图标，产物看起来没做完。实测模型原始产物的缺失率 94%。")
            elif fav.get("unencodedHash"):
                _fav_what = ("favicon 的 data URI 里有**未编码的 `#`**（见 unencodedHash），"
                             "URL 解析会在 `#` 处截断，后面的 SVG 内容全部丢失，"
                             "**图标静默不显示**。几乎总是 `fill='#0F766E'` 忘了写成 `fill='%230F766E'`。"
                             "这个错误在 DOM 里看不出来，截图上也只是 tab 图标空着，很容易漏。")
            else:
                _fav_what = "favicon 指向了外部文件（见 externalRefs），不是 data URI。"
            report["faviconHint"] = (
                "warning · 含义：" + _fav_what
                + " | 修法：用**内联 SVG data URI**，一行搞定、零额外文件："
                "`<link rel=\"icon\" type=\"image/svg+xml\" href=\"data:image/svg+xml,"
                "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E"
                "%3Crect width='64' height='64' rx='14' fill='%230F766E'/%3E"
                "%3Ctext x='32' y='44' font-size='36' text-anchor='middle' fill='white'%3EA%3C/text%3E"
                "%3C/svg%3E\">`。图形取产物主题里的一个符号（首字母、核心图标、品牌形状），"
                "配色沿用页面主色，别用无关的通用图标。"
                " | **三个必须注意的编码细节**：外层 href 用双引号、SVG 内部属性用单引号；"
                "`<` `>` 写成 `%3C` `%3E`；**颜色的 `#` 必须写成 `%23`**——不编码会被当成 URL fragment，"
                "图标直接不显示。想做深浅色两版就写两个 link，加 `media=\"(prefers-color-scheme: dark)\"`。"
                " | 为什么只能用 data URI：`link href` **不在发布链路的资源收集白名单里**"
                "（那里只认 `src` 属性和 CSS `url()`），指向 `assets/` 的图标文件发布后必然 404；"
                "而且额外文件破坏单文件自包含，用户拿到一个 html 就该能用。"
                " | 会不会被平台图标覆盖：不会。发布平台把自己的默认 favicon 注入在 `<head>` 最前面，"
                "浏览器对多个 icon link **取最后一个**，模型写在后面的那个生效。"
                " | 豁免：(1) 产物是页面片段（没有完整 `<head>`）时不适用；"
                "(2) externalRefs 指向 CDN 域名（`lf3-static.bytednsdoc.com` 之类）时，"
                "那是**发布平台注入的**默认图标，不是你写的——迭代已发布产物时会看到，忽略即可，"
                "自己另加一个 data URI 的 link 就行（浏览器对多个 icon link 取最后一个）。"
            )
        vp = dom.get("viewportMeta") or {}
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

# playwright 缺席时降级用系统 Chrome（macOS 上即 /Applications/Google Chrome.app），
# 而 CDP 路径每次还新开一个临时 user-data-dir —— 对 Chrome 而言每次截图都是「首次运行」，
# 组件更新、变体下载、默认浏览器检查会逐次重跑。这些对一次性 headless 截图毫无用处，
# 其中触碰 app bundle 的写操作疑似触发 macOS TCC 的 App Management 拦截（弹窗
# 「已阻止"XX"修改 Mac 上的 App」，责任进程记到进程树顶端的宿主 App）。统一关掉；
# playwright 自己启动 chromium 时本身也带这批开关，两条 chrome_cli 路径实测无副作用。
_CHROME_QUIET_FLAGS = [
    "--disable-background-networking",
    "--disable-component-update",
    "--no-first-run",
    "--no-default-browser-check",
]


def _chrome_cli_shoot(exec_path: str, url: str, viewport, out_path: Path,
                     max_wait_sec: int = 30,
                     want_report: bool = False,
                     console_bucket=None, resource_bucket=None, shot_opts=None):
    """CLI 模式截图：优先 CDP full-page（真正的完整长图），失败退到 --screenshot 首屏。

    CDP 路径：起 chrome 带 --remote-debugging-port，Python 直连 devtools
    websocket 发 Page.captureScreenshot(clip)，等价于 puppeteer/playwright 底层做法，
    可以拿到完整长页截图，并按需分片。

    want_report=True 时同时通过 Runtime.evaluate 跑 INIT_SCRIPT+REPORT_SCRIPT，
    返回 dom 报告；退到 --screenshot 兜底路径时无法拿 DOM，返回 None。

    返回 (dom, cap)。cap 为 None 表示这次没要图；`--screenshot` 退路只能截视口一屏、
    没有 clip 能力，所以那条路的 cap 永远是单张无分片。
    """
    w, h = viewport
    # ---- 首选：CDP 全页截图 ----
    cdp_err = None
    try:
        dom, cap = _cdp_capture(exec_path, url, viewport, out_path, max_wait_sec,
                                want_report=want_report,
                                console_bucket=console_bucket,
                                resource_bucket=resource_bucket,
                                shot_opts=shot_opts)
        # clip 已按 cssContentSize 精确取全页，不会再有底部大片空白，无需 trim
        return dom, cap
    except Exception as e:
        cdp_err = e  # 保留下来；--screenshot 退路也挂时一起报出去

    # ---- 退路：--screenshot 只截视口一屏 ----
    # 注意：这里不要加 --user-data-dir。--headless=new 配 --screenshot 时 chrome 本来就用
    # 一次性 profile，截完即退；显式指定 user-data-dir 反而会让它截完图后挂住不退出
    # （实测 45s 超时仍在跑），把整条退路拖死。
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
        *_CHROME_QUIET_FLAGS,
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
    if shot_opts is None:
        # 这次只要 DOM 报告，而这条退路本来就拿不到 DOM——图也不用留
        try: out_path.unlink()
        except Exception: pass
        return None, None
    # --screenshot 截的是固定 window-size，短页面底部会留大片空白，仍需 trim
    _trim_bottom_whitespace(out_path)
    # 这条路没有 clip 能力，也不做 Pillow 后处理就交出去。走到这里意味着 playwright 与
    # CDP 都挂了：没有 lint 报告、只有视口一屏、本来就不是完整页面，再去精确满足
    # --format / --max-width / --slice-* 是给一个已经失败的场景做精度优化。
    # 改动前这条路的后处理同样取决于机器上有没有 Pillow，本就不是稳定契约。
    return None, {"path": out_path, "slices": [], "bytes": out_path.stat().st_size,
                  "clipUnsupported": True}




# ---------- 最小 CDP (Chrome DevTools Protocol) 客户端 ----------
def _cdp_capture(exec_path: str, url: str, viewport, out_path: Path, wait_sec: int,
                 want_report: bool = False,
                 console_bucket=None, resource_bucket=None, shot_opts=None):
    """启 chrome remote-debugging → 直连 websocket → Page.captureScreenshot 全页。

    shot_opts=None 表示这次只要 DOM 报告、不出图，连编码都省掉。
    返回 (dom_report, cap)；cap 为 None 表示没截图。

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
            *_CHROME_QUIET_FLAGS,
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
            # 全页截图：与 playwright 分支共用 _capture_with_clip，切片规则只有一份
            cap = None
            if shot_opts is not None:
                def _send(method, params=None):
                    return ws.call(method, params or {}, timeout=25).get("result", {}) or {}
                def _scroll_size():
                    r = ws.call("Runtime.evaluate", {
                        "expression": "[document.documentElement.scrollWidth,"
                                      " document.documentElement.scrollHeight]",
                        "returnByValue": True}, timeout=10)
                    return r.get("result", {}).get("result", {}).get("value")
                page_w, page_h, size_degraded = _page_content_size(_send, _scroll_size, viewport)
                cap = _capture_with_clip(
                    _cdp_shooter(_send, shot_opts["fmt"], shot_opts["quality"]),
                    page_w, page_h, out_path, shot_opts["fmt"],
                    # chrome CLI 起进程时固定 --force-device-scale-factor=1，
                    # 所以这条路径上 --scale 本来就不生效，传 1 与改动前一致
                    dsf=1.0,
                    max_width=shot_opts["max_width"],
                    slice_over_kb=shot_opts["slice_over_kb"],
                    slice_over_height=shot_opts["slice_over_height"],
                    slice_height=shot_opts["slice_height"])
                if size_degraded:
                    cap["sizeDegraded"] = size_degraded
            # 再 flush 一次事件（截图期间可能仍有异步日志）
            if want_report:
                _cdp_flush_pending_events(ws, console_bucket, resource_bucket, req_url_map, req_type_map)
            return dom_report, cap
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
                    eval_code=args._eval_code, scale=args.scale)
            if args.only in ("mobile", "both"):
                p_out = outdir / f"{name}_mobile.png"
                result["shots"]["mobile"] = one_shot(
                    page, parse_size(args.mobile), url, p_out,
                    console_bucket, resource_bucket,
                    args.max_width, args.jpeg_quality, args.format,
                    args.slice_over_kb, args.slice_over_height, args.slice_height, include,
                    eval_code=args._eval_code, scale=args.scale)
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
            shot_opts = None
            if "screenshots" in include:
                shot_opts = {"fmt": args.format, "quality": args.jpeg_quality,
                             "max_width": args.max_width,
                             "slice_over_kb": args.slice_over_kb,
                             "slice_over_height": args.slice_over_height,
                             "slice_height": args.slice_height}
            dom, cap = _chrome_cli_shoot(
                exec_path, url, viewport, raw_out,
                want_report=want_report,
                console_bucket=console_bucket,
                resource_bucket=resource_bucket,
                shot_opts=shot_opts,
            )
            if cap:
                _apply_capture(rep, cap, args.slice_over_kb,
                               args.slice_over_height, args.slice_height)
                rep["truncated"] = False  # chrome CLI 用固定 canvas，超出会截断——但没法检测
                if cap.get("clipUnsupported"):
                    rep["screenshotHint"] = (
                        "CDP 挂了，走 --screenshot 兜底：只有视口一屏，不是完整长页，"
                        "也未按 --format / --max-width 转码降宽、未分片。"
                        "图读不动时就只按 lint 字段改代码，别把没看过的截图当成看过了。"
                    )

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
    # 图片路径是否写在发布链路收集得到的位置：要比对 HTML 源码原文，
    # 只有这里同时拿得到 args.src 和各视口的运行时结果
    _emit_publish_broken_assets(result, args.src)
    # 清掉临时字段（DOM 报告里挂的 _chartContainers 只是给 python 侧对比用，
    # 保留在输出里对读报告的人没意义，反而占地方）
    for sh in result.get("shots", {}).values():
        if isinstance(sh, dict):
            sh.pop("_chartContainers", None)
            sh.pop("_fileAssetRefs", None)

    result["elapsedSec"] = round(time.time() - t0, 2)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


# ---- 发布链路资源收集：源码位置扫描
# 线上探针实测（一次发布，5 种写法同页对照）：发布链路只收集 **`src` 属性** 与 **CSS `url()`**
# 两处的静态路径，其余位置一概不上传 → 发布后 404 裂图。实测裂的三种：路径写在 JS 字符串
# 常量里、路径由 JS 拼接、路径写在 `data-src` 属性里（后者即便是静态写在 HTML 属性上也照样裂）。
_REGION_RE = re.compile(
    r"<!--.*?-->|<script\b[^>]*>.*?</script\s*>|<style\b[^>]*>.*?</style\s*>",
    re.DOTALL | re.IGNORECASE,
)
# 属性感知：引号内的 ">" 不会提前截断标签
_TAG_RE = re.compile(r"""<([a-zA-Z][a-zA-Z0-9:_-]*)((?:"[^"]*"|'[^']*'|[^>"'])*)>""")
_ATTR_RE = re.compile(
    r"""([a-zA-Z_:][a-zA-Z0-9_:.\-]*)\s*=\s*("([^"]*)"|'([^']*)'|([^\s"'>=`]+))"""
)
_CSS_URL_RE = re.compile(r"""url\(\s*(?:"([^"]*)"|'([^']*)'|([^)"']*))\s*\)""", re.IGNORECASE)
# 任意位置的图片路径字面量。必须带图片扩展名才认——JS 里的字符串也可能是下载名、
# localStorage 键或比较常量，靠扩展名把噪声压到可接受
_IMG_EXT = r"(?:png|jpe?g|gif|webp|avif|svg|bmp|ico)"
_IMG_LITERAL_RE = re.compile(
    r"""(["'`])([^"'`\n\\]{1,300}?\.%s)\1""" % _IMG_EXT, re.IGNORECASE)
_IMG_EXT_RE = re.compile(r"\.%s$" % _IMG_EXT, re.IGNORECASE)
# 发布链路会收集的位置。改这个集合等于改判据——只能按线上实测结果改，不要凭推测加
_SAFE_POSITIONS = frozenset({"src", "css-url"})


def _looks_like_local_img(ref: str) -> bool:
    """带图片扩展名、且是本地相对/绝对路径（排除远程、data URI、模板插值）"""
    r = (ref or "").split("?")[0].split("#")[0].strip()
    if not r or r.startswith(("http://", "https://", "//", "data:", "blob:")):
        return False
    # `${x}/logo.svg`、`{{path}}/a.png` 这类带插值的不是静态路径，解析结果未知。
    # 平台注入的代码里很常见（实测 138 个真实产物 100% 都有一处），不排掉全是噪声
    if "${" in r or "{{" in r:
        return False
    return bool(_IMG_EXT_RE.search(r))


def _scan_source_ref_positions(text: str) -> dict:
    """扫 HTML 源码，返回 {引用字符串: set(位置标签)}。

    位置标签取值：'src' / 'css-url' / 'attr:<名>' / 'script'。注释区域整体跳过——
    注释里的路径不构成引用，既不该算安全也不该算违规。

    只做位置归类，不做合法性判断；判定交给调用方对照 _SAFE_POSITIONS。
    """
    pos = {}

    def note(ref, tag):
        ref = (ref or "").strip()
        if ref:
            pos.setdefault(ref, set()).add(tag)

    def scan_css(chunk):
        for m in _CSS_URL_RE.finditer(chunk):
            note(m.group(1) or m.group(2) or m.group(3), "css-url")

    def scan_tags(seg):
        for m in _TAG_RE.finditer(seg):
            chunk = m.group(2)
            if not chunk:
                continue
            for a in _ATTR_RE.finditer(chunk):
                name = a.group(1).lower()
                val = a.group(3) if a.group(3) is not None else (
                    a.group(4) if a.group(4) is not None else (a.group(5) or ""))
                if name == "style":
                    scan_css(val)
                elif name == "src":
                    note(val, "src")                       # 唯一的安全属性
                elif name in ("srcset", "imagesrcset"):
                    # `a.png 1x, b.png 2x` —— 拆出每个候选，它们各自都不在白名单
                    for part in val.split(","):
                        bits = part.strip().split()
                        if bits and _looks_like_local_img(bits[0]):
                            note(bits[0], "attr:" + name)
                elif _looks_like_local_img(val):
                    note(val, "attr:" + name)              # data-src / poster / href ...

    # 按 comment / script / style 分区，区域外走标签扫描
    cursor = 0
    for m in _REGION_RE.finditer(text):
        start, end, body = m.start(), m.end(), m.group(0)
        if start > cursor:
            scan_tags(text[cursor:start])
        head = body[:7].lower()
        inner_start = body.find(">") + 1
        if head.startswith("<!--"):
            pass                                            # 注释：整块跳过
        elif inner_start > 0:
            scan_tags(body[:inner_start])                    # 开标签自身仍要扫（<script src>）
            if head.startswith("<style"):
                inner_end = body.lower().rfind("</style")
                if inner_end > inner_start:
                    scan_css(body[inner_start:inner_end])
            else:
                inner_end = body.lower().rfind("</script")
                if inner_end > inner_start:
                    for sm in _IMG_LITERAL_RE.finditer(body[inner_start:inner_end]):
                        if _looks_like_local_img(sm.group(2)):
                            note(sm.group(2), "script")
        cursor = end
    if cursor < len(text):
        scan_tags(text[cursor:])
    return pos


def _emit_publish_broken_assets(result: dict, src: str):
    """哪些图片发布后会裂 —— 三层检测合并成一条规则。

    发布链路靠静态扫描 HTML 源码决定上传哪些文件，只认 `src` 属性和 CSS `url()`
    （线上探针实测）。写在别处的路径不会被上传，发布后 404。

    三层各有盲区，并集覆盖：
      L1 源码方向：扫出所有路径字面量，位置不在白名单就报。抓得到「运行时没渲染到」的
         资源（tab 切换、点击后加载），但抓不到路径被拼接的——源码里没有完整字面量。
      L2 运行时方向：DOM 实际加载了的资源，没有对应的安全静态引用就报。抓得到拼接的，
         但只能看见被渲染出来的。
      L3 目录方向：assets/ 下的文件，前两层都没覆盖到。兜住「既是拼接的、又没渲染到」
         这个 L1∩L2 的盲区，但用户自己往目录里放文件会误报——所以只作提醒，不算错。

    误报面：L1/L2 是纯位置判定，没有启发式成分；L3 会误报，单独标 severity。
    """
    if src.startswith(("http://", "https://")):
        return                                       # 远程页面读不到源码，也不走发布链路
    try:
        html_path = Path(src).resolve()
        text = html_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return                                       # 读不到原文就不判，宁可漏报
    base = html_path.parent

    def norm(ref):
        """引用字符串 / file:// URL → 绝对 realpath 字符串；不是产物内资源则返回 None"""
        r = (ref or "").split("?")[0].split("#")[0].strip()
        if not r or r.startswith(("http://", "https://", "//", "data:", "blob:")):
            return None
        if r.startswith("file://"):
            r = r[7:]
        r = unquote(r)
        try:
            p = (Path(r) if os.path.isabs(r) else base / r).resolve()
            # 必须落在 HTML 所在目录之内。发布链路只上传产物目录里的文件，目录外的引用
            # 不是产物资源。`/spark/app/.../runtime/api/...` 这类站点绝对路径尤其要挡掉——
            # 它在 file:// 下被解析到文件系统根，实测真实产物里很常见（服务端 API 路径）
            p.relative_to(base)
            return str(p)
        except Exception:
            return None

    # 账本：绝对路径 -> 该资源的所有已知信息
    ledger = {}

    def entry(key, ref=None):
        e = ledger.setdefault(key, {"positions": set(), "runtime": False, "ref": ref})
        if ref and not e["ref"]:
            e["ref"] = ref
        return e

    # L1：源码里的位置
    for ref, tags in _scan_source_ref_positions(text).items():
        key = norm(ref)
        if key:
            entry(key, ref)["positions"] |= tags

    # L2：运行时实际加载的
    for sh in (result.get("shots") or {}).values():
        if isinstance(sh, dict):
            for r in sh.get("_fileAssetRefs") or []:
                key = norm(r.get("url") or "")
                if key:
                    entry(key)["runtime"] = True

    # L3：assets/ 目录里的图片文件。**仅本地电脑（macOS / Windows）执行**——
    # 这一层的唯一产出是 unreferenced-file（磁盘上有、源码和运行时都没引用），只在
    # 「图片用相对路径引用」的本地模式下成立。云电脑（Linux）图片走 lark-cli drive
    # 上传、HTML 引用的是外链，assets/ 里的原图按 SKILL.md 要求保留、必然「未被引用」，
    # 在那儿扫这一层等于对每个带图产物都误报一次，还会诱导模型删掉不该删的原图。
    # 另外三种 reason（js-literal / js-concat / non-src-attr）不依赖本层，两端照常检测。
    if platform.system() in ("Darwin", "Windows"):
        assets_dir = base / "assets"
        if assets_dir.is_dir():
            try:
                for p in assets_dir.rglob("*"):
                    if p.is_file() and not p.name.startswith(".") and _IMG_EXT_RE.search(p.name):
                        entry(str(p.resolve()))
            except Exception:
                pass

    hits = []
    for key, e in sorted(ledger.items()):
        if e["positions"] & _SAFE_POSITIONS:
            continue                                  # 有一处写在安全位置就够了，会被上传
        # 磁盘上没有、运行时也没加载 → 这个字符串压根不构成资源引用（平台注入的模板、
        # 文案里提到的文件名、被注释掉的旧代码）。报了模型也无从下手；真的缺文件由
        # resourceErrors 负责报「加载失败」，两条规则不重叠
        if not e["runtime"] and not os.path.isfile(key):
            continue
        positions = e["positions"]
        if "script" in positions:
            reason, sev = "js-literal", "error"        # 路径写在 JS 字符串里
        elif positions:
            attrs = sorted(p.split(":", 1)[1] for p in positions if p.startswith("attr:"))
            reason = "non-src-attr:" + ",".join(attrs) if attrs else "unsafe-position"
            sev = "error"
        elif e["runtime"]:
            reason, sev = "js-concat", "error"         # 源码里没有这个字面量，运行时拼出来的
        else:
            reason, sev = "unreferenced-file", "warning"
        try:
            rel = str(Path(key).relative_to(base))
        except Exception:
            rel = Path(key).name
        hits.append({
            "file": rel, "reason": reason, "severity": sev,
            "loadedAtRuntime": e["runtime"], "onDisk": os.path.isfile(key),
        })

    if not hits:
        return
    errors = [h for h in hits if h["severity"] == "error"]
    # error 优先，warning 垫后；总量截断避免刷屏
    hits = (errors + [h for h in hits if h["severity"] == "warning"])[:20]
    result["publishBrokenAssets"] = hits
    result["publishBrokenAssetsHint"] = (
        "含义：发布链路靠静态扫描 HTML 源码决定上传哪些图片文件，**只认 `src` 属性和 "
        "CSS `url()` 两个位置**（线上实测）。写在别处的路径不会被上传，发布后 404 裂图。"
        "本地打开和自检截图都看不出来——文件真实存在，浏览器照样加载。"
        " | severity=error 的逐条改，改法都是同一个：把路径挪到 `<img src=\"assets/x.png\">` "
        "或 CSS `url('assets/x.png')`。"
        "reason=js-literal 路径写在 JS 字符串里（`const g=['assets/x.png']` 这种常量数组也算，"
        "照样裂）；reason=js-concat 路径由 JS 拼接（`'assets/img'+i+'.png'`）；"
        "reason=non-src-attr 路径写在 `data-src`、`srcset`、`poster` 等非 `src` 属性上——"
        "**这类即便静态写在 HTML 属性里也会裂**，懒加载写法要在 `src` 上放真实路径。"
        " | severity=warning（reason=unreferenced-file）是提醒不是错误：`assets/` 里有这个文件，"
        "但源码和运行时都没引用到它。可能是没用上的多余素材（删掉即可），"
        "也可能是路径拼接且当前视口没渲染到的图（那就是会裂的，按 error 处理）。"
        "**这一条只在本地电脑（macOS / Windows）检测**——云电脑图片走 `lark-cli drive "
        "+html-image-upload`，HTML 引用外链、`assets/` 里的原图本就该保留且不被引用，"
        "在那儿报是纯误报，所以直接不报；**别因为这条去删云电脑上的原图**。"
        "自行判断，别的规则不受它影响。"
    )


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
