#!/usr/bin/env python3
"""真实照片检索 —— 素材三条路里的第三条。

为什么要有它：没有采集通路时，生产代码里 `unsplash|pexels` **0 命中**，
完全没有"找一张真照片"的能力。于是「00 后运动品牌官网」那一轮，
12 张生成图上传后拿到了 CDN 地址却没写进页面，成品是从零脑补的——
症状是：网页里一张真实照片都没有。

三条素材路，按适用场景选（不是三选一，通常混用）：

  ① image_gen / image_edit  —— 品牌主视觉、产品英雄图、插画、App 关键屏。
     方法与门 A 八项自检见 `reference/image-direction.md`，必读。
  ② text_to_video / image_to_video —— 只在 query 明确要动态影像、
     或内容职责依赖时间媒体时用。5–8 秒，必须留 poster 降级。
  ③ 本脚本 —— 需要**真实世界的照片**时：人像、服饰上身、场景、材质。
     生图画真人上身容易出手指与面部瑕疵，真实摄影更稳且更便宜。

已知失败条件（都写进实现了）：
  · Unsplash 有机器人验证；Pexels 搜索页直接 curl 返回 403
  · 但 images.pexels.com 这个 CDN **不挡 curl**
  · 所以流程是：浏览器打开搜索页 → 从 DOM 抠 photo id → curl 规范 URL 批量下

用法：
  # 1) 在浏览器里打开搜索页，把抠到的 id 存成一行一个或逗号分隔
  python3 fetch_photos.py ids --help
  # 2) 批量下载 + 出联络表
  python3 fetch_photos.py get --ids ids.txt --out research/pool --width 640 --sheet
  # 3) 定稿：把选中的 id 按角色下成大图
  python3 fetch_photos.py pick --map picks.json --out site/assets
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import re
import subprocess
import sys
from pathlib import Path

CDN = ("https://images.pexels.com/photos/{id}/pexels-photo-{id}.jpeg"
       "?auto=compress&cs=tinysrgb&w={w}")

BROWSER_SNIPPET = """在浏览器里打开 Pexels 搜索页，然后跑这段 JS 抠 id：

  https://www.pexels.com/search/<关键词>/

  const s=new Set;
  document.querySelectorAll('img').forEach(i=>{
    const m=(i.src||'').match(/^https:\\/\\/images\\.pexels\\.com\\/photos\\/(\\d+)\\//);
    if(m) s.add(m[1]);
  });
  JSON.stringify([...s]);

搜 3–4 组关键词，凑 80–120 个候选再选。候选太少必然选不出统一的一组。
"""


def _dl(pid: str, out: Path, w: int) -> tuple[str, bool]:
    dst = out / f"{pid}.jpg"
    r = subprocess.run(["curl", "-s", "--max-time", "30", "-o", str(dst),
                        CDN.format(id=pid, w=w)], capture_output=True)
    ok = r.returncode == 0 and dst.exists() and dst.stat().st_size > 4000
    if not ok and dst.exists():
        dst.unlink()
    return pid, ok


def read_ids(src: str) -> list[str]:
    raw = Path(src).read_text(encoding="utf-8") if Path(src).is_file() else src
    return sorted(set(re.findall(r"\d{4,9}", raw)))


def cmd_get(a) -> int:
    ids = read_ids(a.ids)
    if not ids:
        print("没有解析到 id。\n\n" + BROWSER_SNIPPET)
        return 1
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    ok = 0
    with cf.ThreadPoolExecutor(max_workers=10) as ex:
        for _pid, good in ex.map(lambda p: _dl(p, out, a.width), ids):
            ok += good
    print(f"下载 {ok}/{len(ids)} 张 → {out}")
    if a.sheet:
        sheet = out.parent / (out.name + "-contact.png")
        rc = subprocess.run([sys.executable, str(Path(__file__).with_name("shoot.py")),
                             "sheet", str(out), str(sheet), "9"], capture_output=True, text=True)
        print(rc.stdout.strip() or rc.stderr.strip())
        print("\n把联络表读进上下文，逐张看，然后按下面的规则选片：")
        print(SELECTION_RULES)
    return 0 if ok else 1


SELECTION_RULES = """
── 选片规则（这不是审美建议，是可执行的取舍）──────────────────
1. **本稿只允许 2 种摄影类型**，写进 art-direction.photoTypes。
   例：`影棚白底全身`（商品）＋ `现场强色光`（大片）。中间态一律不用。
   混着放的结果是整站看起来像图库拼盘 —— 这是"技术上都对但就是廉价"的头号来源。
2. **同一类型内要同一场拍摄**。商品网格的 8 张如果底色深浅不一，
   网格就散了。宁可少 2 件商品，也不要混两场光。
3. **同一块面积里只允许一个强调色**。实测教训：会员区放了一张琥珀橙背景的照片，
   和信号橙红并排 —— 两块橙打架，改 hue-rotate 和叠色都救不回来，最后换成高调黑白。
4. **避开可见的竞品 Logo**。设计稿里出现别家的勾，评审会一直盯着它。
5. 选完写下每张的**角色**（hero / product-01 / lookbook-02 / member…），
   角色决定尺寸：hero 1800、通栏 1400–1600、商品 1000、缩略 640。
"""


def cmd_pick(a) -> int:
    """picks.json: {"hero": ["7793228", 1800], "p1": ["6516169", 1000], …}"""
    m = json.loads(Path(a.map).read_text(encoding="utf-8"))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    ok = 0
    bad: list[str] = []
    for role, v in m.items():
        pid, w = (v if isinstance(v, list) else (v, 1200))
        dst = out / f"{role}.jpg"
        r = subprocess.run(["curl", "-s", "--max-time", "40", "-o", str(dst),
                            CDN.format(id=pid, w=w)], capture_output=True)
        good = r.returncode == 0 and dst.exists() and dst.stat().st_size > 4000
        size = dst.stat().st_size if dst.exists() else 0
        # 失败的下载会留下一个几字节的文件，而**没有任何东西发现它**。
        # 已知失败条件：app/assets/ 里躺着三个 2 字节的 .jpg，
        # 页面引用它们就是裂图，引用别处的临时地址就是交付端碎图。
        # 删掉比留着强 —— 留着会被当成"素材已就位"。
        if not good and dst.exists():
            dst.unlink()
            bad.append(f"{role}(id={pid})")
        ok += good
        print(f"  {'OK ' if good else 'ERR'} {role:14} id={pid} w={w}  "
              f"{size // 1024 if good else 0}KB"
              + ("" if good else f"　← 只下到 {size}B，已删掉"))
    print(f"\n{ok}/{len(m)} 张就位 → {out}")
    if bad:
        print(f"**{len(bad)} 个角色没有素材**：{', '.join(bad)}\n"
              f"  这些角色在页面里不要引用 —— 空文件已经删了，"
              f"引用不存在的路径就是裂图。\n"
              f"  换 id 重下，或者改走 image_gen。")
    print("提醒：摄影素材是 Pexels 免费授权，正式上线要换品牌自有大片 —— "
          "把这条写进文档的「已知边界」，不要让评审以为这是终稿素材。")
    return 0 if ok == len(m) else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="真实照片检索")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("ids", help="打印在浏览器里抠 id 的方法")
    p = sub.add_parser("get", help="批量下候选 + 出联络表")
    p.add_argument("--ids", required=True, help="文件路径或直接粘一串 id")
    p.add_argument("--out", required=True)
    p.add_argument("--width", type=int, default=640)
    p.add_argument("--sheet", action="store_true")
    p = sub.add_parser("pick", help="按角色下定稿大图")
    p.add_argument("--map", required=True)
    p.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.cmd == "ids":
        print(BROWSER_SNIPPET + SELECTION_RULES)
        return 0
    return cmd_get(a) if a.cmd == "get" else cmd_pick(a)


if __name__ == "__main__":
    sys.exit(main())
