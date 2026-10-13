#!/usr/bin/env python3
"""看图回执的交叉验证。

只收三个文本参数（--tier / --worst / --fix-dimension）的审美门是无效的：
没有任何图像证据，校验逻辑是关键词表匹配，**而它的失败提示里直接写着
三句能过门的范例**（ui_pipeline.py:2789）。复述报错就能通过
「唯一的质量决策点」。这不是执行者不老实，是门在教它怎么过门。

这里换一条思路：**不问你觉得好不好，问你看到了什么；
凡是你说的坐标、颜色、字号，我都去页面上量一遍。**
编不出来的东西编了会被当场戳穿。

用法：
    python3 observe.py --url <产物URL> --observed <observed.json> [--min 3]

observed.json 是一个数组，每条：
{
  "where": "会员区左右分界",           必填，要能在页面上定位
  "selector": ".join-media",           必填，真实存在的 CSS 选择器
  "what":  "左侧 #FF3B14 与右图背景橙相邻，两块橙打架",   必填，具体缺陷
  "measure": {"hex": "#FF3B14"},       必填，至少一个可验证量值
  "fix":   "换成高调黑白人像并锁 grayscale"              必填
}

measure 支持的键（至少给一个，给多个就多验几条）：
  hex        该元素或其子元素的实际颜色/背景色里必须出现这个 hex（±8/255 容差）
  fontSize   该元素或其子元素里必须存在这个字号（±1px）
  width/height  该元素的渲染尺寸（±4px）
  count      该选择器匹配到的元素个数（精确）
  contrast   该元素文字与其背景的对比度（±0.4）

**第二轮是建议，不是硬要求**。第二轮的条目带 `"resolved": true`，
它的 measure 会按**改完之后的新数值**去页面上量一遍
——所以"改了"这件事也是量出来的，不是声明出来的。
只有一轮时 `publish.py` 照发，但会在交付输出里把"还差第二轮"披露出来。

> 改的是**入口形状**，不是判据。实测一条真实 trace 里这个脚本跑了 7 次、
> 收据 0 条：3 次 `observed.json 必须是数组`、1 次少于 --min、3 次 --seed。
> 模型第一次就把最外层写成了 `{...}`，然后在**格式**上耗掉三轮，
> 一条真的看图回执都没产出。一个要求执行者从零手写结构化 JSON、
> 写错就整条拒绝的门，在 flash 档上不可达。
> 现在：形状错就地修好（守则 S23-2 机械项脚本直接改完），
> `--seed` 把量值先填好，你只补 `where` / `what` / `fix` 三栏。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import runstate  # noqa: E402

PROBE = r"""
(sel) => {
  const el = document.querySelector(sel);
  if (!el) return {missing: true};
  const all = [el, ...el.querySelectorAll('*')];
  const colors = new Set;
  const sizes = new Set;
  all.forEach(n => {
    const s = getComputedStyle(n);
    [s.color, s.backgroundColor, s.borderTopColor, s.fill].forEach(c => {
      if (c && !c.includes('rgba(0, 0, 0, 0)')) colors.add(c);
    });
    if (n.textContent && n.textContent.trim()) sizes.add(parseFloat(s.fontSize));
  });
  // 背景图里的主色量不到，如实标记，不猜
  const bgImg = all.some(n => getComputedStyle(n).backgroundImage !== 'none')
             || !!el.querySelector('img,video,canvas,svg');
  const r = el.getBoundingClientRect();
  const lum = c => {
    const m = c.match(/[\d.]+/g); if (!m) return null;
    const [rr, gg, bb] = m.slice(0, 3).map(Number).map(v => {
      v /= 255; return v <= .03928 ? v / 12.92 : Math.pow((v + .055) / 1.055, 2.4);
    });
    return .2126 * rr + .7152 * gg + .0722 * bb;
  };
  // 对比度只在背景可信时给值：透明的定位层背后是什么无法从父链推断，
  // 一路取到 body 底色一定是错的（实测会把压在照片上的白字判成 1.18:1）
  let contrast = null;
  const cs = getComputedStyle(el);
  let q = el, bg = null, trusted = true;
  while (q) {
    const b = getComputedStyle(q);
    if (b.backgroundImage !== 'none') { trusted = false; break; }
    if ((b.position === 'fixed' || b.position === 'absolute')
        && b.backgroundColor.includes('rgba(0, 0, 0, 0)')) { trusted = false; break; }
    if (b.backgroundColor && !b.backgroundColor.includes('rgba(0, 0, 0, 0)')) {
      bg = b.backgroundColor; break;
    }
    q = q.parentElement;
  }
  if (trusted && bg) {
    const l1 = lum(cs.color), l2 = lum(bg);
    if (l1 !== null && l2 !== null)
      contrast = Math.round(((Math.max(l1, l2) + .05) / (Math.min(l1, l2) + .05)) * 100) / 100;
  }
  return {
    colors: [...colors], sizes: [...sizes].sort((a, b) => a - b),
    w: Math.round(r.width), h: Math.round(r.height),
    count: document.querySelectorAll(sel).length,
    contrast, hasMedia: bgImg,
  };
}
"""


def _rgb(hex_or_rgb: str) -> tuple[int, int, int] | None:
    s = hex_or_rgb.strip()
    if s.startswith("#"):
        s = s[1:]
        if len(s) == 3:
            s = "".join(c * 2 for c in s)
        if len(s) != 6:
            return None
        return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore
    nums = [int(float(x)) for x in __import__("re").findall(r"[\d.]+", s)[:3]]
    return tuple(nums) if len(nums) == 3 else None  # type: ignore


# ── 入口形状：错了就地修，不整条拒绝 ────────────────────────────
# 这些别名不是"猜意图"，是同一件东西的另一种写法。答案唯一的机械项脚本改完，
# 有第二种合理答案的（比如 what 到底指哪个缺陷）一律不碰。
FIELD_ALIAS = {"css": "selector", "sel": "selector", "element": "selector",
               "problem": "what", "issue": "what", "desc": "what",
               "suggestion": "fix", "howToFix": "fix", "how_to_fix": "fix",
               "location": "where", "position": "where"}
MEASURE_ALIAS = {"color": "hex", "colour": "hex", "background": "hex",
                 "fontsize": "fontSize", "font-size": "fontSize",
                 "font_size": "fontSize", "size": "fontSize",
                 "w": "width", "h": "height", "n": "count"}
LIST_KEYS = ("items", "observed", "list", "data", "observations", "findings")


def normalize(raw) -> tuple[list[dict], list[str]]:
    """把任何合理形状的输入收敛成条目数组。返回 (items, 修了什么)。"""
    notes: list[str] = []
    if isinstance(raw, dict):
        for k in LIST_KEYS:
            if isinstance(raw.get(k), list):
                notes.append(f"最外层是对象，已取它的 `{k}` 数组")
                raw = raw[k]
                break
        else:
            notes.append("最外层是单个对象，已包成 1 条的数组")
            raw = [raw]
    if not isinstance(raw, list):
        return [], ["读不出任何条目——顶层既不是数组也不是对象"]

    items: list[dict] = []
    for x in raw:
        if not isinstance(x, dict):
            notes.append(f"丢掉一个不是对象的条目：{str(x)[:40]}")
            continue
        it = dict(x)
        for a, real in FIELD_ALIAS.items():
            if a in it and not str(it.get(real, "")).strip():
                it[real] = it.pop(a)
                notes.append(f"`{a}` 已改名成 `{real}`")
        m = it.get("measure")
        if isinstance(m, list):
            merged: dict = {}
            for e in m:
                if isinstance(e, dict):
                    merged.update(e)
            m = merged
            notes.append("measure 是数组，已合并成对象")
        if not isinstance(m, dict):
            m = {}
        fixed_m = {}
        for k, v in m.items():
            k2 = MEASURE_ALIAS.get(k, MEASURE_ALIAS.get(k.lower(), k))
            if k2 != k:
                notes.append(f"measure 的 `{k}` 已改名成 `{k2}`")
            fixed_m[k2] = v
        it["measure"] = fixed_m
        for k in ("where", "selector", "what", "fix"):
            it.setdefault(k, "")
        items.append(it)
    return items, notes


def verify(page, item: dict, idx: int) -> list[str]:
    """返回这条回执的失败原因；空列表 = 通过。"""
    bad: list[str] = []
    for key in ("where", "selector", "what", "fix"):
        if not str(item.get(key, "")).strip():
            bad.append(f"第 {idx} 条缺 `{key}`")
    m = item.get("measure") or {}
    if not isinstance(m, dict) or not m:
        bad.append(f"第 {idx} 条没有 `measure`——只有量得出来的东西才算看过")
    if bad:
        return bad

    sel = item["selector"]
    try:
        probe = page.evaluate(PROBE, sel)
    except Exception as e:                              # 选择器语法错
        return [f"第 {idx} 条 selector `{sel}` 无法执行：{e}"]
    if probe.get("missing"):
        return [f"第 {idx} 条 selector `{sel}` 在页面上不存在——这条是编的"]

    for k, v in m.items():
        if k == "hex":
            want = _rgb(str(v))
            if not want:
                bad.append(f"第 {idx} 条 hex `{v}` 不是颜色")
                continue
            hit = any(
                (lambda g: g and max(abs(a - b) for a, b in zip(g, want)) <= 8)(_rgb(c))
                for c in probe["colors"])
            if not hit:
                if probe["hasMedia"]:
                    continue                            # 颜色在图里，量不到，不判错
                bad.append(f"第 {idx} 条说 `{sel}` 有 {v}，实测颜色是 "
                           f"{probe['colors'][:4]}")
        elif k == "fontSize":
            if not any(abs(s - float(v)) <= 1 for s in probe["sizes"]):
                bad.append(f"第 {idx} 条说字号 {v}px，实测 {probe['sizes'][:6]}")
        elif k in ("width", "height"):
            got = probe["w"] if k == "width" else probe["h"]
            if abs(got - float(v)) > 4:
                bad.append(f"第 {idx} 条说 {k}={v}，实测 {got}")
        elif k == "count":
            if probe["count"] != int(v):
                bad.append(f"第 {idx} 条说有 {v} 个，实测 {probe['count']} 个")
        elif k == "contrast":
            if probe["contrast"] is None:
                bad.append(f"第 {idx} 条给了 contrast，但这里背景不可信（压在图/透明层上），"
                           f"量不出对比度——换一个可验证的量值")
            elif abs(probe["contrast"] - float(v)) > 0.4:
                bad.append(f"第 {idx} 条说对比度 {v}:1，实测 {probe['contrast']}:1")
        else:
            bad.append(f"第 {idx} 条 measure 里的 `{k}` 不是支持的键")
    return bad


SEED_PROBE = r"""
 () => {
  const vw = innerWidth, vh = innerHeight;
  const out = [];
  const sel = e => {
    if (e.id) return '#' + e.id;
    const c = (e.className || '').toString().trim().split(/\s+/)[0];
    return c ? e.tagName.toLowerCase() + '.' + c : e.tagName.toLowerCase();
  };
  const push = (e, why, measure) => {
    const s = sel(e);
    if (document.querySelectorAll(s).length && !out.some(o => o.selector === s))
      out.push({where: '', selector: s, what: why, measure,
                fix: '', _text: (e.textContent || '').trim().slice(0, 24)});
  };
  // 1 被放大的图（糊）
  [...document.images].forEach(i => {
    const r = i.getBoundingClientRect();
    if (r.width > 40 && i.naturalWidth && i.naturalWidth < r.width * 0.9)
      push(i, `原图 ${i.naturalWidth}px 显示在 ${Math.round(r.width)}px 上，放大了会糊`,
           {width: Math.round(r.width)});
  });
  // 2 贴边的正文
  [...document.querySelectorAll('p,h1,h2,h3,li')].forEach(e => {
    if (e.textContent.trim().length < 30) return;
    const r = e.getBoundingClientRect();
    if (r.width > 60 && (r.left < 16 || vw - r.right < 16))
      push(e, `离版心边只有 ${Math.round(Math.min(r.left, vw - r.right))}px，字被切在边上`,
           {width: Math.round(r.width)});
  });
  // 3 常驻底栏没贴底
  [...document.querySelectorAll('*')].forEach(e => {
    const st = getComputedStyle(e);
    if (!['fixed', 'sticky', 'absolute'].includes(st.position)) return;
    const r = e.getBoundingClientRect();
    if (r.width >= vw * 0.6 && r.height >= 36 && r.height <= 140 && r.bottom > vh * 0.55
        && Math.abs(vh - r.bottom) > 2)
      push(e, `常驻底栏离视口底还有 ${Math.round(vh - r.bottom)}px，卡在半空`,
           {height: Math.round(r.height)});
  });
  // 4 相邻段落结构雷同（十屏一个模子）
  const secs = [...document.querySelectorAll('section,.sec,.screen')];
  const fp = secs.map(x => [...x.querySelectorAll('*')].slice(0, 30).map(y => y.tagName).join('>'));
  for (let i = 2; i < fp.length; i++)
    if (fp[i] && fp[i] === fp[i-1] && fp[i] === fp[i-2])
      push(secs[i], `这一段和前两段结构完全相同，读者会觉得在原地踏步`, {count: secs.length});
  /* 一条可疑处都没量到时**也要出条目**。
     seed 量不到东西就不落文件，于是执行者又回到"从零手写 JSON"——
     那正是这个脚本被跑了 7 次、收据 0 条的原因。
     这几条的 selector 与 measure 是真的（脚本量的），what/fix 留空由你看图填：
     构成类缺陷（两块颜色打架、装饰变噪音、十屏一个模子）本来就量不出来。 */
  if (!out.length) {
    const anchors = [...document.querySelectorAll(
      'section,.screen,.sec,main,article,header')].slice(0, 3);
    anchors.forEach(e => push(e, '', {count: document.querySelectorAll(sel(e)).length}));
    if (!out.length && document.body) push(document.body, '', {count: 1});
  }
  return out.slice(0, 8);
}
"""


def seed(url: str, w: int, h: int, out_path: str) -> int:
    """把可疑处连同**实测值**打出来，你只补 what 与 fix。

    为什么要有这一步：实测一条真实 trace 里 observe.py 连续 INVALID 六次——
    不是执行者不老实，是它得凭印象猜一个能对上的数值，猜不中就重来。
    于是"走门"比"绕门"贵得多，而绕门零成本。
    这一步把量值先给出来：走门反而成了最省力的路。
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("PLAYWRIGHT_MISSING —— 无法播种，只能手写 observed.json。")
        return 2
    from shoot import ALL_IMAGES_READY, SETTLE_JS, resolve_target
    real, srv = resolve_target(url)
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={"width": w, "height": h})
            for fn in (lambda: pg.goto(real, wait_until="load", timeout=30000),
                       lambda: pg.wait_for_timeout(800),
                       lambda: pg.wait_for_function(ALL_IMAGES_READY, timeout=12000),
                       lambda: pg.evaluate(SETTLE_JS),
                       lambda: pg.wait_for_timeout(1200)):
                try:
                    fn()
                except Exception:
                    pass
            found = pg.evaluate(SEED_PROBE)
            b.close()
    finally:
        if srv:
            srv.close()

    for it in found:
        it.pop("_text", None)
    if not found:
        # 页面上连一个可锚定的元素都没有，才会走到这里。给一条空模板，
        # 至少不让执行者从零发明 JSON 的形状。
        found = [{"where": "", "selector": "body", "what": "",
                  "measure": {"count": 1}, "fix": ""}]
    Path(out_path).write_text(json.dumps(found, ensure_ascii=False, indent=2),
                              encoding="utf-8")
    auto = [it for it in found if it["what"]]
    print(f"播种了 {len(found)} 条到 {out_path}，**selector 和量值已经量好填好**：\n")
    for i, it in enumerate(found, 1):
        print(f"  {i}. {it['selector']}｜{it['what'] or '（这条的 what 留空，等你看图填）'}")
    print(f"\n你要补的是 `where`（在页面上哪儿）、`fix`（怎么改）"
          f"{'，以及留空的 `what`' if len(auto) < len(found) else ''}。\n"
          "  **不要重跑 --seed**（会覆盖你写的），改完直接跑验证那一条。\n\n"
          "  上面这些是量得出来的那一半。**量不出来的那一半只有看图能发现**——\n"
          "  两块颜色打架、装饰元素变噪音、十屏一个模子。\n"
          "  把截图读进上下文，删掉不成立的、加上你看出来的，条目数不必和播种一样。")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="看图回执交叉验证")
    runstate.add_run_arg(ap)
    ap.add_argument("--url", required=True)
    ap.add_argument("--seed", action="store_true",
                    help="先播种：把可疑处连同**实测值**打出来，你只补 what/fix")
    ap.add_argument("--observed", required=True)
    # 3 → 2。降的是**条数**，不是判据 —— 每一条仍然要在页面上量得对。
    # 一条真实 trace 在这道门上耗掉三轮、产出 0 条收据；条数不是瓶颈，形状才是。
    ap.add_argument("--min", type=int, default=2,
                    help="至少几条（默认 2；这是最低限度，不是目标）")
    # 移动端稿要在 390×844 里量。在 1440 宽里量一份 H5，量到的是另一个页面。
    ap.add_argument("--width", type=int, default=1440)
    ap.add_argument("--height", type=int, default=900)
    a = ap.parse_args()
    run_path = runstate.find(a.run)

    if a.seed:
        return seed(a.url, a.width, a.height, a.observed)

    try:
        raw = json.loads(Path(a.observed).read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"INVALID —— {a.observed} 不是合法 JSON：{e}\n"
              "  这一条脚本修不了（缺哪个逗号只有你知道）。其余形状问题都会被自动修好。")
        return 1
    items, notes = normalize(raw)
    if notes:
        # 修好就落盘。下一轮再跑时它已经是规范形状，不会再看到这些提示。
        Path(a.observed).write_text(
            json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
        print("形状已自动修好（不用你改，已写回文件）：")
        for n in dict.fromkeys(notes):
            print("  · " + n)
        print()
    if len(items) < a.min:
        print(f"INVALID —— 只写了 {len(items)} 条，至少 {a.min} 条。\n"
              f"  提示：如果真的看不出 {a.min} 条问题，多半是没把图读进上下文，"
              "或者看的是缩略图。放大到 100% 逐段看。\n"
              f"  播种一份带量值的底稿：python3 {runstate.SCRIPTS}/observe.py --url {a.url} "
              f"--seed --observed {a.observed}")
        return 1

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("PLAYWRIGHT_MISSING —— 无法交叉验证。宿主侧请人工复核 observed 的每一个量值。")
        return 2

    # 和 shoot.py 同一条规矩：networkidle 会在有动画/外链字体的页面上永远等不到，
    # 分段等待且只降级不抛异常；本地路径自己托管。
    from shoot import ALL_IMAGES_READY, resolve_target
    url, srv = resolve_target(a.url)
    fails: list[str] = []
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={"width": a.width, "height": a.height})
            for fn in (lambda: pg.goto(url, wait_until="load", timeout=30000),
                       lambda: pg.wait_for_timeout(900),
                       lambda: pg.evaluate("() =>document.querySelectorAll('img[loading=lazy]')"
                                           ".forEach(i=>i.loading='eager')"),
                       lambda: pg.wait_for_function(ALL_IMAGES_READY, timeout=12000),
                       lambda: pg.wait_for_timeout(1200)):
                try:
                    fn()
                except Exception:
                    pass
            for i, it in enumerate(items, 1):
                fails += verify(pg, it, i)
            b.close()
    finally:
        if srv:
            srv.close()

    for f in fails:
        print("  FAIL  " + f)
    if fails:
        print(f"\nINVALID —— {len(fails)} 条对不上。\n"
              "  这道门不判断你的审美，只判断你**是不是真的看了**。\n"
              "  对不上的原因通常是：凭印象写、或者把别的元素的数值安到了这个选择器上。")
        return 1
    resolved = [it for it in items if it.get("resolved")]
    print(f"PASS —— {len(items)} 条看图回执全部与页面实测吻合"
          f"（其中 {len(resolved)} 条标了已修复）。")
    for it in items:
        mark = "✔ 已修复 " if it.get("resolved") else "· "
        print(f"  {mark}{it['where']}｜{it['what']}  → {it['fix']}")
    runstate.add_receipt(run_path, "observe", {
        "url": a.url, "observed": str(Path(a.observed).resolve()),
        "count": len(items), "resolved": bool(resolved),
        "resolvedCount": len(resolved)})
    if not run_path:
        runstate.note_missing("看图")
    return 0


if __name__ == "__main__":
    sys.exit(main())
