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

  // 规则 3：僵尸按钮 / 无效链接
  // 目标：抓那种"看起来能点、按下去什么都不发生"的元素。
  // 局限：addEventListener 绑的 handler 无法通过 DOM API 查询到（浏览器故意封的），
  //   委托模式（document.addEventListener('click', delegateHandler)）注定漏抓。
  // 所以只抓高特异性模式：<button> 无 onclick 且非 form submit/aria pattern/popover 触发器；
  //   <a> 无有效 href。元素祖先带 [data-*] 时标 note 提示"可能是委托目标"。
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
    const push = (el, reason) => {
      if (deadButtons.length >= 20) return;
      const r = el.getBoundingClientRect();
      const txt = (el.textContent || '').trim();
      const rec = {
        tag: el.tagName.toLowerCase(),
        text: txt.slice(0, 60),
        reason: reason,
        rect: [Math.round(r.left + window.scrollX), Math.round(r.top + window.scrollY), Math.round(r.width), Math.round(r.height)],
      };
      if (hasDataAttr(el)) {
        rec.note = 'ancestor-has-data-attr: 可能被 addEventListener 委托捕获，请核对';
      }
      deadButtons.push(rec);
    };

    // 3a：<button>
    for (const btn of document.querySelectorAll('button')) {
      if (deadButtons.length >= 20) break;
      if (btn.onclick != null) continue;
      // 被 addEventListener('click', ...) 绑过（自身或祖先）—— 由 INIT_SCRIPT 打的标
      if (btn.__shot_hasClickListener) continue;
      let anc = btn.parentElement, hasAncListener = false;
      while (anc && anc !== document.body) {
        if (anc.__shot_hasClickListener) { hasAncListener = true; break; }
        anc = anc.parentElement;
      }
      if (hasAncListener) continue;
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
      push(btn, 'button-no-onclick');
    }

    // 3b：<a>
    for (const a of document.querySelectorAll('a')) {
      if (deadButtons.length >= 20) break;
      if (a.onclick != null) continue;
      if (a.__shot_hasClickListener) continue;
      let anc = a.parentElement, hasAncListener = false;
      while (anc && anc !== document.body) {
        if (anc.__shot_hasClickListener) { hasAncListener = true; break; }
        anc = anc.parentElement;
      }
      if (hasAncListener) continue;
      const href = a.getAttribute('href');
      if (!isVisible(a)) continue;
      if ((a.textContent || '').trim().length === 0) continue;
      if (href === null) {
        push(a, 'a-no-href');
      } else if (href.trim() === '') {
        push(a, 'a-href-empty');
      } else if (href.trim() === '#') {
        // href="#" 常见于占位；如果没 onclick 且没绑事件，多半是僵尸
        push(a, 'a-href-hash-no-handler');
      }
      // href="#some-id"（真锚点）、http/https/mailto/tel 等一律不报
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
    overlappingText: overlappingText,
    clippedText: clippedText,
    deadButtons: deadButtons,
    misalignedBlocks: misalignedBlocks,
    chartContainers: chartContainers,
    unsafeHrefRefs: unsafeHrefRefs,
    invisibleAnimations: invisibleAnimations,
    slopFonts: slopFonts,
    emojiUsage: emojiUsage,
    viewportMeta: viewportMeta,
    touchTargetTooSmall: touchTargetTooSmall,
    fixedWidthElements: fixedWidthElements,
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
    page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(400)
    page.evaluate("() => window.scrollTo(0, 0)")
    page.wait_for_timeout(200)
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
        if "structure" in include:
            report["structure"] = dom["structure"]
        # chartContainers 无论 lint/structure 开哪个都存下来，供跨视口对比
        report["_chartContainers"] = dom.get("chartContainers") or []
        if "lint" in include:
            report["consoleErrors"] = [m for m in console_bucket if m["type"] == "error"]
            report["consoleWarnings"] = [m for m in console_bucket if m["type"] == "warning"]
            report["horizontalOverflow"] = dom["horizontalOverflow"]
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
            dead = dom.get("deadButtons") or []
            if dead:
                report["deadButtons"] = dead
                report["deadButtonsHint"] = (
                    "含义：<button> 既无 onclick 也没被 addEventListener('click') 绑过，或 <a> 无有效 href。"
                    "reason=button-no-onclick / a-no-href / a-href-empty / a-href-hash-no-handler。"
                    "已排除 form submit/reset、popover 触发器、role=tab/menuitem/option/switch/checkbox/radio、<label> 包裹。"
                    " | 修法：给 <button> 加 onclick 或 addEventListener；给 <a> 补 href 或改成 <button>。"
                    " | 豁免：(1) 带 note=ancestor-has-data-attr 的项可能是**祖先事件委托**目标（document/window 上的全局委托本规则查不到），"
                    "对着代码核对，如果确实有 document.addEventListener('click', e => e.target.closest(...)) 之类的委托捕获就忽略；"
                    "(2) 纯装饰按钮（无 hover/focus 反馈的 mock 页面）——但这本身也算 slop，建议改成非 <button>。"
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
    console_bucket.clear()
    resource_bucket.clear()
    return report


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
                     max_wait_sec: int = 30):
    """CLI 模式截图：优先 CDP full-page（真正的完整长图），失败退到 --screenshot 首屏。

    CDP 路径：起 chrome 带 --remote-debugging-port，Python 直连 devtools
    websocket 发 Page.captureScreenshot(captureBeyondViewport=true)，
    等价于 puppeteer/playwright 底层做法，可以拿到完整长页截图。
    """
    w, h = viewport
    # ---- 首选：CDP 全页截图 ----
    cdp_err = None
    try:
        _cdp_capture(exec_path, url, viewport, out_path, max_wait_sec)
        # 后处理 trim 底部（CDP 一般贴合内容，很少有大空白，但保底）
        _trim_bottom_whitespace(out_path)
        return
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


# ---------- 最小 CDP (Chrome DevTools Protocol) 客户端 ----------
def _cdp_capture(exec_path: str, url: str, viewport, out_path: Path, wait_sec: int):
    """启 chrome remote-debugging → 直连 websocket → Page.captureScreenshot 全页。

    不依赖任何第三方库；用标准库 socket 实现最小 websocket 帧收发（CDP 消息都是
    JSON 文本，短则几十字节长则几 MB 的 base64 图像）。
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
            # Page.enable → Page.navigate → Page.loadEventFired → Page.captureScreenshot
            ws.call("Page.enable")
            ws.call("Page.navigate", {"url": url})
            # 等 load 事件；若网络卡就 wait_sec 后不再等
            deadline = time.time() + wait_sec
            got_load = False
            while time.time() < deadline:
                ev = ws.recv_event(timeout=deadline - time.time())
                if ev and ev.get("method") == "Page.loadEventFired":
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

    没有 DOM 报告能力；scroll-reveal 元素若被 opacity:0 隐藏也无法强制显现。
    lint / structure 在此模式下无法生成，字段返回 null 并标记 reportDegraded=true。
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

    def do_one(viewport, key):
        w, h = viewport
        rep = {}
        if "screenshots" in include:
            raw_out = outdir / f"{name}_{key}.png"
            _chrome_cli_shoot(exec_path, url, viewport, raw_out)
            post = _postprocess(raw_out, args.max_width, args.jpeg_quality, args.format,
                                args.slice_over_kb, args.slice_over_height, args.slice_height)
            rep["screenshot"] = str(post["path"])
            rep["screenshotBytes"] = post["bytes"]
            rep["truncated"] = False  # chrome CLI 用固定 24000 canvas，超出会截断——但没法检测
            if post["slices"]:
                rep["slices"] = [str(s) for s in post["slices"]]
                rep["sliceHint"] = (
                    f"主图过阈值（字节>{args.slice_over_kb}KB 或 高度>{args.slice_over_height}px），"
                    f"已按 {args.slice_height}px 切片。若主图 Read 失败，改读 slices 里各分片。"
                )
        # lint / structure：chrome CLI 模式无 DOM 访问，返回 null 标记
        if "lint" in include:
            rep["consoleErrors"] = None
            rep["consoleWarnings"] = None
            rep["resourceErrors"] = None
            rep["horizontalOverflow"] = None
        if "structure" in include:
            rep["structure"] = None
        if "lint" in include or "structure" in include:
            rep["reportDegraded"] = True
            rep["reportHint"] = (
                "当前 chrome CLI 降级模式：截图走 CDP 全页（若成功）或首屏回退；"
                "lint 与 structure 字段为 null（无 DOM 结构报告）。"
                "如需完整报告，请装 playwright：`pip install playwright && playwright install chromium`。"
            )
        elif "screenshots" in include:
            rep["reportDegraded"] = True
            rep["reportHint"] = "当前 chrome CLI 降级模式：截图走 CDP 全页（若成功）或首屏回退。"
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
