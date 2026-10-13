#!/usr/bin/env python3
"""把一份骨架拷进工作目录 —— 然后它就归你了。

这不是生成器。它不产出成品，也不会在你改坏之后帮你改回来。
它只做一件事：给你一个几何已经对了的起点，省掉那些一定会踩的坑
（安全区、dvh、scroll-snap、飞书块宽不能写断点、单位不能用 em…）。

这里**不放生成器**。一个 3,067 行、含 32KB 字面 CSS 的生成器，
并且明令「执行者不手改 HTML」。结果是所有 query 的产物共享同一套样式表，
两份不同项目的 CSS Jaccard 实测 0.73 —— 长得像同一个网站。
所以这里反过来：骨架越薄越好，改它是本职工作，不是越权。

用法：
    python3 skeleton.py web  <workdir>/site        --title "PULSE"
    python3 skeleton.py h5   <workdir>/h5          --title "QQ 2026"
    python3 skeleton.py doc  <workdir>/doc/canvas-a.html \\
                             --title "…" --project "…" --part "PART 01" --accent "#FF3B14"
"""
from __future__ import annotations

import argparse
import datetime
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import runstate  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SK = {"web": "web.html", "h5": "h5.html", "app": "app.html",
      "console": "console.html", "board": "board.html",
      "screen": "screen.html", "longimg": "longimg.html",
      "doc": "doc-canvas.html", "cover": "doc-cover.html"}

# 封面版式**由内容选**，不是一套模板套所有稿，也不是随机。
# 每篇 doc 都要有一张封面。
COVER_VARIANTS = {
    "interface-archive": "App / 小程序 / H5：主素材是一组关键屏，斜向排开成档案",
    "editorial-object": "主素材是竖图（人像 / 单品 / 竖构图场景）：左文右图两栏",
    "cinematic-field": "主素材是横图（空间 / 场景 / 横构图产品）：满版图 + 底部压字",
}


# ── 文档人格：7 个角色，没有默认值 ─────────────────────────────
# 骨架一旦出厂自带一套完整人格，两份完全不同项目的画布填完空之后
# 13 个视觉角色里 7 个逐字节相同，用户一眼就说「一模一样」。
# 骨架越好用越容易变成模板，所以这里**不给默认值**，只给方向。
PERSONA_KEYS = ["paper", "ink", "muted", "hairline", "soft",
                "font", "rule", "numfont", "radius", "bodysize", "lead"]

# 六维签名 → 人格方向。给的是方向，不是值：值仍然由你定。
DIRECTION = {
    "ground": {"paper": "纸感：微黄纸 / 米白 / 牛皮；线用双线或不用线",
               "dark": "深底浅字：纸取近黑，墨取骨色，发丝线用低透明白",
               "light": "亮场：纸接近白但别停在纯白，靠灰阶拉层次",
               "saturated": "高饱和：纸可以直接上色，墨取近黑，强调色反而收敛"},
    "typeVoice": {"serif-editorial": "衬线（宋体 / Noto Serif）+ 双线分隔 + 零圆角",
                  "rounded-friendly": "圆体（Nunito / 圆黑）+ 大圆角 + 柔和阴影，可以不要分隔线",
                  "condensed-poster": "压缩重体 + 粗墨线 + 直角，编号做大",
                  "sans-cool": "中性无衬线 + 发丝线 + 小圆角，刻度收紧",
                  "display-art": "标题用美术字，正文退到最朴素，编号可以异形"},
}


def parse_persona(raw: str) -> dict[str, str]:
    """`k=v,k=v` → dict，但**逗号不是无条件的分隔符**。

    人格值本身就带逗号，而且是最常用的那两种：
      hairline=rgba(58,53,48,.10)      括号里的逗号
      font=Inter,PingFang SC,system-ui 字体栈的逗号

    按裸逗号切会把 `rgba(58,53,48,.10)` 截成 `rgba(58` ——
    写进画布就是 `--line:rgba(58;`，**整份样式表从这里断掉**，
    后面所有规则一条都不生效（实测：67 条规则只剩 2 条，
    网格全塌成竖排，而每一道门都还是绿的）。

    两条规则：
      · 括号深度 >0 时的逗号属于值，不切
      · 切出来的段里没有 `=` 时，它是上一个值的续接（字体栈）
    """
    out: dict[str, str] = {}
    parts, buf, depth = [], "", 0
    for ch in raw:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth = max(0, depth - 1)
        if ch == "," and depth == 0:
            parts.append(buf)
            buf = ""
            continue
        buf += ch
    parts.append(buf)
    last = None
    for seg in parts:
        if "=" in seg:
            k, v = seg.split("=", 1)
            k = k.strip()
            out[k] = v.strip()
            last = k
        elif seg.strip() and last:
            out[last] += "," + seg.strip()
    return out


def persona_help(style: dict | None) -> str:
    sig = (style or {}).get("signature") or {}
    lines = ["这份骨架**不带人格**——带了的话，两份不同项目的文档 13 个视觉角色里会有 7 个相同。",
             "", "必须给全这 11 个值（--persona k=v,k=v）："]
    lines += ["  paper 纸  ink 墨  muted 灰阶  hairline 发丝线  soft 浅底块",
              "  font 字体栈  rule 章节分隔线  numfont 编号字形  radius 圆角",
              "  bodysize 正文字号  lead 行高"]
    if sig:
        lines += ["", f"本稿签名：ground={sig.get('ground')} typeVoice={sig.get('typeVoice')}",
                  "→ 方向（值仍然由你定）："]
        for dim in ("ground", "typeVoice"):
            hint = DIRECTION.get(dim, {}).get(sig.get(dim))
            if hint:
                lines.append(f"  · {hint}")
    else:
        lines += ["", "（没找到 style.json —— 先跑 style.py，人格要从签名推，不要凭手感）"]
    lines += ["", "例（三份 gold 的做法，可以看不可以抄）：",
              "  PULSE  paper=#FFFFFF,ink=#14161A,font=系统无衬线,rule=2px solid,radius=3px",
              "  QQ     paper=#F6F2E8,ink=#1B2A4A,font=Songti SC,rule=3px double,radius=0",
              "  骑不骑  paper=#FAF8F4,ink=#3A3530,font=Nunito,rule=none,radius=18px",
              "  它们两两之间最多 5 个角色相同。你这份对它们任何一份也不该超过 5。"]
    return "\n".join(lines)


def pick_variant(cls: str, aspect: float | None) -> tuple[str, str]:
    if cls == "mobile":
        return "interface-archive", "移动端稿的主素材是一组关键屏"
    if aspect is not None and aspect < 0.95:
        return "editorial-object", f"主素材长宽比 {aspect}（竖图），满高排更好看"
    return "cinematic-field", "主素材是横图，满版 + 底部压字"

NEXT = {
    "web": """下一步（顺序别换）：
  1 先把 assets/ 填满真实素材：`fetch_photos.py` 找照片，或 image_gen 生图
    （方法与门 A 八项自检见 reference/image-direction.md）
  2 定四组数值写进骨架的 :root —— 参考 craft/aesthetic-baseline.md
  3 按 craft/page-grammar.md 逐段答 job/proof/geometry/move，再决定形状
  4 写完立刻**执行**这一条（它自己起服务器、截图、跑门、写回执，不用你拼）：
      python3 __UI_PY__ review --run __RUN__""",
    "h5": """下一步（顺序别换）：
  1 定屏数与每屏的那一件事；每屏换构图，不要十屏一个骨架
  2 定十屏配色序列，但底纹与质感共用一层
  3 写完立刻**执行**这一条（它自己起服务器、截图、跑门、写回执，不用你拼）：
      python3 __UI_PY__ review --run __RUN__

  这份骨架是**叙事 H5**（年报 / 盘点 / 活动专题）的形状。
  如果你要做的是 App / 小程序界面，用的是另一份：skeleton.py app —— 它没有
  分屏、页码、进度条和三键底栏，因为**不是每个产品都有那些东西**。""",
    "app": """下一步（顺序别换）：
  1 先答一句：用户每天打开它是为了干什么？首屏就答这一句，不要封面页
  2 **挑版式**。骨架里有五个原语，混用是常态，用不到的整段删掉：
       .rail    横滑轨道（分类 chip / 推荐位）
       .grid2   双列瀑布（商品 / 菜谱 / 房源 / 图集）
       .rows    密集列表（排行榜 / 流水 / 消息）—— 一屏十几行几乎无图是**正当**的
       .hero    顶部大图 + 上浮面板（详情页；这种页**没有 tab**，底部是通栏 CTA）
       .canvas  全屏画布 + bottom sheet（地图 / 相机 / 播放器）
     后两种要连带删掉 .tabbar。
  3 至少两个真实状态：tab 切换 / 卡片展开 / 筛选切换 / 进详情，随便哪两个
     —— 门会**真的去点**，数有几个控件改变了界面
  4 写完立刻**执行**这一条（它自己起服务器、截图、跑门、写回执，不用你拼）：
      python3 __UI_PY__ review --run __RUN__

  **底部 tab 是可以删的。** 工具类 App 常常没有 tab，只有一个悬浮主操作；
  地图页的主操作在屏幕中间也是对的。删了不违反任何门 ——
  门查的是「他知不知道自己在哪」和「主操作够不够得着」，不是「有没有 tab 栏」。
  三份结构样本在 tests/archetypes/（详情页 / 地图页 / 排行榜页，三份都是 21/21 全绿）。
  交互工艺见 craft/interaction-contract.md 的产品界面那一列。""",
    "doc": """下一步：
  1 这是**给客户看的汇报**，不是工程记录。七节的顺序已经在骨架里了，
    每一节先问"客户在这一节想知道什么"，再决定写什么
  2 图全部 base64 内嵌（外链和本地路径在飞书里都是裂图）
  3 关键屏图用**真机截图**，不要用示意图
  4 写完**执行**同一条命令（它会出封面图、截画布、跑 doc 门）：
      python3 __UI_PY__ review --run __RUN__
  5 再 `__UI_PY__ ship` 交付 —— 两张卡的参数都由它产出""",
    "cover": """下一步（**两条命令，不要自己发明第三种做法**）：
  1 主图从 assetPlan 里**按角色挑**（opening / declaration / flagship），
    不要抓第一张 —— 封面主角要和方案主角是同一个
  2 配色 / 字体 / 网格密度 / 光晕位置按 style.json 的六维签名定，骨架里都是占位
  3 出图 + 写进文档：`ui.py review`（文档阶段）会出 shots/cover.jpg，
    然后提示你用宿主的 FileBatchUpload 换公网 URL；`publish.py --cover-url`
    会把封面作为 <title> 后第一个块随正文一起创建。

  封面写进 proposal.xml —— 就在 <title> 之后的第一个块：
      <p><img width="3200" height="1800" caption="" name="cover.jpg" href="<公网URL>"/></p>
  <img href> 只吃公网 URL，本地路径会被静默丢弃且不报错（发布报成功、封面没了），
  所以 URL 要先用宿主的 FileBatchUpload 换：给它 shots/cover.jpg，它返回
  https://aka.doubaocdn.com/s/… —— publish.py 会把这一行替你插进去，你不用手写。

  不要写「base64 内嵌的图片块」—— 飞书没有这种块。
  不要用发布后的 +media-insert —— 那条路要模糊匹配锚点，匹配不上会静默追加到文末。""",
}


def main() -> int:
    ap = argparse.ArgumentParser(description="拷一份骨架")
    ap.add_argument("kind", choices=list(SK))
    ap.add_argument("dest")
    ap.add_argument("--title", default="未命名")
    ap.add_argument("--project", default="")
    ap.add_argument("--part", default="")
    ap.add_argument("--accent", default="#FF3B14")
    ap.add_argument("--accent-soft", default="", help="强调色的浅色版（下划线高亮用）")
    ap.add_argument("--accent-ink", default="",
                    help="强调色的**文字版**，要压深；不给就沿用 --accent")
    ap.add_argument("--class", dest="cls", choices=["mobile", "web"], default="web",
                    help="cover 用：决定封面版式")
    ap.add_argument("--hero-aspect", type=float,
                    help="cover 用：主素材宽/高（<0.95 判为竖图）")
    ap.add_argument("--persona", default="",
                    help="doc 用：paper=…,ink=…,font=… 共 11 个角色，无默认值")
    ap.add_argument("--style", default="style.json", help="doc 用：六维签名文件")
    a = ap.parse_args()

    # doc 画布必须先定人格。没有它就不发骨架 —— 这一步不是形式，
    # 是唯一能阻止"所有人的文档长得一样"的地方。
    persona = parse_persona(a.persona)
    if a.kind == "doc":
        missing = [k for k in PERSONA_KEYS if k not in persona]
        if missing:
            st = None
            sp = Path(a.style)
            if sp.is_file():
                try:
                    st = json.loads(sp.read_text(encoding="utf-8"))
                except Exception:
                    st = None
            print(f"缺 {len(missing)} 个人格角色：{' '.join(missing)}\n")
            print(persona_help(st))
            return 1

    src = ROOT / "skeletons" / SK[a.kind]
    dest = Path(a.dest)
    if dest.suffix != ".html":
        # doc 画布是**按合同点名的两个文件**（canvas-a / canvas-b），
        # 传目录会产出一个 doc/index.html —— 没有任何东西要它，
        # 而合同要的两块画布仍然是空的。实测真发生过，成品目录里多了一个孤儿文件。
        if a.kind == "doc":
            print(f"doc 画布要传**文件路径**，不是目录：你给的是 {dest}/\n"
                  f"  合同点名的是两块：doc/canvas-a.html 和 doc/canvas-b.html。\n"
                  f"  传目录会产出一个没人要的 doc/index.html，而那两块还是空的。\n"
                  f"  正常不用手跑这条 —— `{runstate.UI} review --run <run.json>` 会按合同建齐。")
            return 1
        dest.mkdir(parents=True, exist_ok=True)
        dest = dest / "index.html"
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        print(f"{dest} 已存在。骨架只在开头拷一次；后面直接改它，不要重拷覆盖你的稿。")
        return 1

    t = src.read_text(encoding="utf-8")
    run_path = runstate.find(getattr(a, "run", None))
    # NEXT 里不留需要自己解析的占位符：解析不出来，整条指令就会被跳过。
    _ui, _rj = str(ROOT / "scripts" / "ui.py"), str(run_path or "<run.json>")
    next_cmd = (f"python3 {ROOT / 'scripts' / 'ui.py'} review"
                + (f" --run {run_path}" if run_path else " --run <run.json>"))
    for k, v in {"__NEXT_CMD__": next_cmd,
                 "__TITLE__": a.title, "__PROJECT__": a.project or a.title,
                 "__PART__": a.part, "__ACCENT__": a.accent,
                 "__ACCENT_SOFT__": a.accent_soft or a.accent + "26",
                 "__ACCENT_INK__": a.accent_ink or a.accent,
                 "__PAPER__": persona.get("paper", ""),
                 "__INK__": persona.get("ink", ""),
                 "__MUTED__": persona.get("muted", ""),
                 "__HAIRLINE__": persona.get("hairline", ""),
                 "__SOFT__": persona.get("soft", ""),
                 "__FONT_STACK__": persona.get("font", ""),
                 "__RULE__": persona.get("rule", ""),
                 "__NUM_FONT__": persona.get("numfont", ""),
                 "__RADIUS__": persona.get("radius", ""),
                 "__BODY_SIZE__": persona.get("bodysize", ""),
                 "__BODY_LEAD__": persona.get("lead", ""),
                 "__DATE__": datetime.date.today().isoformat(),
                 "__TIME__": datetime.datetime.now().strftime("%H:%M")}.items():
        t = t.replace(k, v)

    variant = None
    if a.kind == "cover":
        variant, why = pick_variant(a.cls, a.hero_aspect)
        t = t.replace('class="cover cinematic-field"', f'class="cover {variant}"')
    dest.write_text(t, encoding="utf-8")

    if a.kind == "web":
        (dest.parent / "assets").mkdir(exist_ok=True)

    print(f"已拷到 {dest}（{len(t.splitlines())} 行）")
    if variant:
        print(f"封面版式：{variant} —— {why}\n"
              f"  三种都在骨架里，换版式只要改根节点的第二个 class：\n"
              + "\n".join(f"    {k:20}{v}" for k, v in COVER_VARIANTS.items())
              + "\n  版式可以同，**视觉必须不同** —— 配色字体由 style.json 定。")
    print("\n这份文件现在归你。里面所有 TODO 和占位值都要换掉 —— "
          "留着不换会被 placeholder 门拦下。")
    if a.kind in ("doc", "cover"):
        # 这一段是**耗时**账，不是审美账。
        # 实测（校园论坛那一轮）：canvas-a 14,006 字节整份 Write 花了 160s、
        # canvas-b 12,778 字节花了 **417s**、cover 2,807 字节花了 414s，合计约 16 分钟。
        # 而重写出来的类选择器与骨架 **100% / 79% 重合** ——
        # 那十几分钟买的是一份它本来就有的 CSS。
        print("\n**改它，不要重写它。**\n"
              "  这份骨架里的 CSS 就是它保证「装得下、不溢出、可读」的全部内容，\n"
              "  而且飞书块宽会浮动，那些 clamp()/min() 是踩出来的，不要凭手感重写。\n"
              "  **只用 Edit 改 <body> 里的文案与图位；不要整份 Write 覆盖。**\n"
              "  实测：一份画布被整份重写花了 7 分钟，而重写出来的类名和骨架 100% 相同 ——\n"
              "  那 7 分钟买的是一份你已经有的 CSS。")
    print("\n动手写之前，这四份读完了吗（各约 1.5 秒）：\n"
          "  craft/award-mechanisms.md    得奖级的六条机制 —— 你这一稿的对手是它们\n"
          "  craft/scale-atlas.md         12 份获奖稿的数值区间（字阶 / 圆角 / 饱和度）\n"
          "  craft/composition-motion.md  构图四条关系 + 滚动驱动 vs 入场揭示\n"
          "  craft/aesthetic-baseline.md  四组数值的判据\n"
          "  骨架只保证装得下、不溢出、可读。**好不好看在这四份里。**\n\n"
          "  一条实测：常见产物的圆角中位是 50px（全是胶囊），"
          "而获奖库中位 3px、12 份里 4 份纯直角。\n"
          "  大圆角是「默认好看」的安全牌 —— 它让任何东西都不难看，也让任何东西都不特别。\n")
    # NEXT 由编排器统一给（守则 S24）。工艺照印，只闭掉"下一步"这一段。
    if not runstate.orchestrated():
        print(NEXT[a.kind].replace("__UI_PY__", _ui).replace("__RUN__", _rj))
    return 0


if __name__ == "__main__":
    sys.exit(main())
