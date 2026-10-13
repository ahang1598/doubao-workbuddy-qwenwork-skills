#!/usr/bin/env python3
"""把交付形态从「一张表格」变成「一个状态」。

为什么需要这个脚本，一条实测就够了：两个典型失败任务
（campus-app、airest-site）的**完整**文件清单是

    airest-site/index.html
    airest-site/assets/*.jpg   ×4

没有 doc/、没有画布、没有 proposal.xml、没有发布收据。
而这两份成品页做得相当好——分栏首屏、克制暖灰场、材质微距通栏。

所以真相不是"做不好"，是**doc 那一半根本没被执行**。
原因很直接：SKILL.md 里「交付形态」是一张表格，`publish.py` 是一条可选命令，
跑完 HTML 之后没有任何东西说「你还欠一份 doc」。
**写在文档里的合同，模型会在最后一刻自行删减；只有冻结成状态的才交得出来。**

用法：
    python3 plan.py --query "<当前请求原文>" [--dir .] [--class mobile|web]
    python3 plan.py --validate            # 只校验现有 contract 的 assetPlan
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import runstate  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

# 移动端有**三种**形态。包里长期只做了后两种，而最常见的是第一种。
#
# 实测：query 是「咖啡点单小程序首页改版」，
# 点开网页卡看到的是「03 / FULL VIEW · 完整首页 · 改版后全貌」——
# 一份关于产品的幻灯片，屏中央贴着一张 400px 宽的首页缩略图。
# 那是严重缺陷。而这不是执行者跑偏：合同的 note 里写的就是
# 「封面 + 内容屏 + 结束页」——那是年报 H5 的定义，被套在了所有 App 和小程序上。
# **模型忠实执行了一个错的合同。这一类 bug 不在执行层。**
#
# 产品界面    交的是**真实产品界面原型**：首屏就是产品首页本身，点了真的会变
# 单向叙事    年报 / 盘点 / 品牌活动页：封面 + 内容屏 + 结束页
# 互动生成器  钩子 → 选择 → 专属结果卡 → 分享，主角是"关于你的那个结果"
#
# 实看网易哒哒近几年的 H5，标题几乎全是「测测你的…／生成你的…」——那是第三种。
GENERATOR = re.compile(r"(测测|测一测|生成你的|制作你的|你是哪种|你的专属|专属你|"
                       r"人格|测试|抽签|盲盒|定制一张|生成一张)")
NARRATIVE = re.compile(r"(年度报告|年度盘点|年报|盘点|品牌故事|活动页|营销页|"
                       r"专题页|发布会|campaign|长图)", re.I)
PROTOTYPE = re.compile(r"(改版|重构|首页|界面|页面|列表页|详情页|下单|点单|"
                       r"信息流|动态流|购物车|个人中心|搜索页|工作台|后台|"
                       r"控制台|dashboard)", re.I)
APP_WORDS = re.compile(r"(app|应用|小程序|客户端|ios|android)", re.I)

# `app\b` 是 挖出来的确定性 bug：Python 的 \w 把 CJK 也算词字符，
# 所以 `app\b` 在「社交app首页」「记账app的首页」「健身app界面」里**永不匹配**，
# 三条全部兜底判成 web。连锁反应就是从这里开始的：
# 判错载体 → 模型手改 run.json → 合同不再可信 → 骨架不用了 →
# 闭包挡路 → 从 --help 读到 --no-closure → 三次发布全部绕过闭包。
# **一个正则的 \b，让整条质量链在真实链路上全线关闭。**
MOBILE = re.compile(r"(app|应用|小程序|h5|活动页|营销页|移动端|手机|"
                    r"ios|android|客户端|年度报告|年度盘点)", re.I)
WEB = re.compile(r"(官网|网站|网页|landing|落地页|dashboard|后台|门户|主页|"
                 r"web\b|web端|website|saas|控制台|品牌站|宽屏)", re.I)

# ── 素材角色表 ───────────────────────────────────────────────
# 这不是"生成器"：它产出的是**要采哪些素材**的清单，一行 CSS 都不产。
# 存在的理由是 F4：低分参照样本 是骑行 App，天气/路线/地图/海拔全是画面，
# 产物却零张图片、零张插画，用 ☀️💧🚻🪑 当图标。
# 包里的 anti-patterns.md 早写了「不许用 emoji 冒充主视觉」，
# 但**规则没有变成产能**——模型手上没有图，就只能拿 emoji 顶。
TOPIC_ROLES: list[tuple[re.Pattern, list[tuple[str, str, str, str]]]] = [
    (re.compile(r"(电商|商城|购物|品牌|服饰|鞋|家具|数码|产品|零售)"), [
        ("product-01", "image_gen", "full-bleed", "产品主图，装在满版容器里"),
        ("product-02", "image_gen", "full-bleed", "第二视角，和主图不同机位"),
        ("material-detail", "image_gen", "full-bleed", "材质微距，讲工艺"),
    ]),
    (re.compile(r"(社区|用户|团队|人物|健身|运动|教育|课程|招聘|社交)"), [
        ("scene-01", "fetch_photos", "full-bleed", "真人场景——生图容易出手指瑕疵，用实拍"),
        ("portrait-01", "fetch_photos", "full-bleed", "人像，锁定同一种光线"),
    ]),
    (re.compile(r"(数据|报表|分析|dashboard|年度|盘点|统计|监控)"), [
        ("data-visual", "svg", "layer", "图表用 SVG 画——生图画不了精确数字"),
        ("number-plate", "css", "layer", "巨数字版面用 CSS，字要能选中"),
    ]),
    (re.compile(r"(地图|出行|骑行|旅行|导航|路线|城市|交通)"), [
        ("map-plate", "image_gen", "full-bleed", "地图底图当满版背景，路线压在上面"),
        ("route-visual", "svg", "layer", "路线/海拔曲线用 SVG——生图画不准"),
        ("scene-01", "fetch_photos", "full-bleed", "沿途实景"),
    ]),
    (re.compile(r"(餐|食|咖啡|茶|饮|菜|厨)"), [
        ("dish-01", "fetch_photos", "full-bleed", "食物实拍，生图的食物容易假"),
        ("texture-detail", "image_gen", "full-bleed", "材质/氛围特写"),
    ]),
    (re.compile(r"(家居|工艺|材质|建筑|空间|设计)"), [
        ("material-detail", "image_gen", "full-bleed", "材质微距通栏"),
        ("scene-01", "image_gen", "full-bleed", "使用场景，主体在画面里"),
    ]),
]

BASE_ROLES = [
    ("hero-bg", "image_gen", "full-bleed", "首屏满版氛围，文字压在上面"),
    ("icon-set", "svg", "inline", "图标必须用 SVG——生图出不了透明底"),
    ("texture", "css", "layer", "底纹用 CSS 画，不占素材预算"),
]

# ── M1 · 这一稿的对手（§5.8）──────────────────────────────
# 包里有 14 份 craft、4 份 reference、5 组带源码 gold、一个 4.3MB 图标库。
# 实测到达的只有必读六份；**写成品页那一半，"好东西"到达率是 0**：
# gold/app-home/index.html（本稿唯一对口的产品界面金标准）  0 次
# reference/fingerprints/index.json（SKILL.md 明写的质量锚点）0 次
# assets/phosphor/catalog.json                              0 次
# gold 全部 4 次读取**都发生在第 47 分钟写 doc 时**，而成品页第 7 分钟就定稿了。
#
# SKILL.md 里有整整一节讲 gold，问题不在于没写，在于**没有任何东西在
# 该看它的那一刻指向它**。所以这一段印在 `brief` 的必经输出里，
# 而且给的是「看哪一份、看哪几段、什么机制」，不是「目录在这里」——
# 少量真实微原型 > 大量抽象统计。
#
# 锚点用**类名现算**，不写死行号：往 gold 里插 20 行空白，它仍然指得对。
GOLD_ANCHORS = {
    "产品界面": ("gold/app-home/index.html", "「班次」通勤到站 App 首页 · 能用的产品界面原型", [
        (r"^#flow\{", "滚动容器怎么给底栏和安全区预留位置 —— 你会遇到同一个几何问题"),
        (r"^\.plan\{|^\.dense\{", "信息块的密度与缝隙 —— 为什么它不像卡片墙"),
        (r"tabs\.forEach", "tab 切换的状态机 —— prototype-not-deck 要的「点了真的变」"),
    ]),
    "单向叙事": ("gold/h5-qq2026/index.html", "QQ 年度报告 · 分屏叙事 H5", [
        (r"^\.screen\{", "一屏 = 一个视口高，scroll-snap 怎么落点确定"),
        (r'^\.screen\[data-t="1"\]', "十屏配色序列：底纹质感共用一层，只换三个变量"),
        (r"^\.big\{|^\.kicker\{", "巨字与眉标的刻度 —— 一屏一件事靠它们承担"),
    ]),
    "互动生成器": ("gold/h5-cycle/index.html", "骑不骑 · 选择 → 专属结果卡", [
        (r"^\.screen\{", "一屏 = 一个视口高"),
        (r"^\.card\{", "结果卡是整个 H5 的产品，前面几屏都是为了它"),
        (r"^\.art\{|^\.scrim\{", "满版影像 + 压字用的遮罩层 —— 白字压照片的正确做法"),
    ]),
    "web": ("gold/web-pulse/index.html", "PULSE · 宽屏产品官网", [
        (r"^\.hero\{", "首屏满版影像 + 巨字 —— 首屏影像占比实测 100%"),
        (r"^\.display\{|^\.cn-display\{", "巨字的字号曲线 —— 字阶断崖实测 13.5"),
        (r"^\.rule\{|^\.wrap\{", "章节怎么分隔 —— 一条 1px 墨线胜过一个卡片"),
    ]),
    # ── 补的四份：四种新载体各有自己对口的 gold ──────────
    # 它们还原自真实项目的设计终稿（附评分细则），不是我们凭空编的版式。
    "web-console": ("gold/console-api/index.html",
                    "数据中台 · API 服务监控页 · 亮场工作台", [
        (r"^\.kpis\{|^\.kpi\{", "四个总览指标：一个数配一个环比，"
                                  "**下面每一块都在解释其中一个**"),
        (r"^th,td\{", "表格密度靠行高（44px）不靠塞；斑马纹不如一条 1px 细线"),
        (r"^\.tag\{", "状态色分两个角色：底用浅的、字用深的 —— "
                      "只用一个值必然掉到 3:1 以下"),
        (r"\[data-state\]\{", "**四种状态一个都不能少**：有数据 / 空 / 加载 / 异常"),
    ]),
    "big-screen": ("gold/screen-hotan/index.html",
                   "和田智能测温防疫平台 · 指挥大厅首屏 4001×2251", [
        (r"^\.canvas\{", "画布几何写死 + transform:scale 适配窗口 —— "
                         "**内部一律不做响应式**"),
        (r"^\.grid3\{", "三列骨架：左轨 · 地图 · 右轨。**地图是唯一的视觉主角**"),
        (r"^\.totals\{|^\.total\{", "两个总数抬到地图正上方 —— "
                                     "一眼看到的就该是它们"),
        (r"^\.alarm\{", "预警用红、常态用青，两色不混 —— "
                        "所以红在 4001px 宽的画面里仍然第一眼能找到"),
    ]),
    "spec-board": ("gold/board-flow/index.html",
                   "客资中心 · 深转引导 5 帧横向流程展板", [
        (r"^\.cap\{", "每帧的标签栏：编号徽章 + 竖线 + 中文说明，**逐帧看标签**"),
        (r"^\.frame:not\(:last-child\)::after", "箭头是内容不是装饰："
                                              "落在两帧画面区的垂直中线上"),
        (r"^\.shot\{", "帧内浅色界面 + 帧外深色底 —— 这个反差就是展板的全部视觉语言"),
        (r"^\.dlg\{", "**换底色的容器必须同时换字色** —— 白底弹窗继承深底的浅墨"
                      "就是白字压白底"),
    ]),
    "long-image": ("gold/longimg-summit/index.html",
                   "实验有道 · 增长无限 · 年度宣讲会分享长图 750×N", [
        (r"^\.cover\{", "首段要能**单独当封面** —— 转发时缩略图截的就是它"),
        (r"^\.seg\{|^\.seg\.soft\{", "段与段之间必须换气：深底 / 浅底块 / "
                                     "通栏图 / 一条细线，四种交替"),
        (r"^h2\{|^\.part\s", "字号按 750 画布放大：正文 26–30、段标 46–54"),
        (r"^\.talk\{", "重复结构要给分组（Part 1/2/3），"
                       "否则 8 条连排读的人会在第 3 条放弃"),
    ]),
}
# 形态名（旧）→ 对手卡的键。新载体直接用 surface 当键。
def anchor_key(shape: str | None, surface: str | None) -> str:
    if shape in GOLD_ANCHORS:
        return shape
    if surface in GOLD_ANCHORS:
        return surface
    return "web"


def _excerpt(path: Path, pattern: str, span: int = 6) -> tuple[int, str] | None:
    if not path.is_file():
        return None
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    for i, ln in enumerate(lines):
        if re.search(pattern, ln):
            body = "\n".join(f"      {x[:96]}" for x in lines[i:i + span])
            return i + 1, body
    return None


def opponent_card(root: Path, shape: str | None, cls: str,
                  surface: str | None = None) -> str:
    key = anchor_key(shape, surface)
    rel, what, anchors = GOLD_ANCHORS[key]
    p = root / rel
    L = ["", "这一稿的对手 —— **先看它，再动手**。"
             "它是真做出来、被验收通过的，带完整源码。", "",
         f"  {p}", f"    {what}",
         f"    ▸ 为什么是这一份：你这一稿是「{key}」，包里 {len(GOLD_ANCHORS)} 组 gold "
         f"里只有它对口"]
    hit = 0
    for pat, why in anchors:
        got = _excerpt(p, pat)
        if not got:
            continue
        hit += 1
        n, body = got
        L += [f"    ▸ L{n} 起 —— {why}", body]
    if not hit:
        L.append(f"    ▸（{rel} 不在盘上或结构变了，整份读一遍也就几秒）")
    L += ["",
          "    规矩（gold/README.md 原文）：**学机制，不抄版式。**",
          "      允许学：为什么章节用一条墨线分隔、为什么商品缝隙只留一线。",
          "      禁止抄：四宫格的具体排法、关键屏网格的具体结构。",
          "      **产物和 gold 在版式上一眼能认出是同一套模板，就是抄了。**", ""]
    # 外部锚点：4 个获奖站的真实浏览器实测值（不是估计值）
    try:
        fp = json.loads((root / "reference" / "fingerprints"
                         / "index.json").read_text(encoding="utf-8"))
        L.append("  外部锚点（reference/fingerprints/index.json，"
                 "2026-07-25 真实浏览器实测，不是估计值）：")
        for s in fp.get("sites", [])[:3]:
            m = s.get("measured", {})
            L += [f"    {s['id']:9}{s.get('readAs', '')}",
                  f"    {'':9}字阶 {m.get('typeRatio')} · display {m.get('displayMax')}"
                  f" · 首屏图占比 {m.get('imageAreaPct')}%"
                  f" · 面色 {m.get('surfaceColorCount')} 种"]
    except Exception:
        pass
    L += ["",
          "  ▸ 动手之前写下一条：**这一稿要在哪一维超过它们？**"
          " 指到具体机制，不要写「更好看」。"]
    return "\n".join(L)

# F10（用户实测）：豆包的生图**只能出矩形，没有透明底，也画不了精确中文**。
# 所以凡是 image_gen 的素材，slot 只能是 full-bleed（满版容器 + object-fit:cover）。
# 写成 inline 会被拦——矩形图当浮动元素贴上去必然带一圈白边。
SLOTS = {"full-bleed", "inline", "layer"}


# ── 合同的四个**正交**字段（§5.2）────────────────────────
#
# 只有两个字段（载体 + 形态），而且是 if-elif 链：
# 「给我一张 4001×2251 大屏图，不要网页」会同时命中两条，**结果取决于正则顺序**。
# 拿评测集 31 题实跑，载体判对 16/31。
#
# 四个字段各判各的，两两之间没有一处需要"谁优先"——这就是正交的判据：
#
# provenance   谁说的     explicit / inferred / ambiguous
# operation    做什么     create / revise / restore / amend
# surface      长什么样   7 种载体
# deliverables 交什么     {html, doc} 的集合
#
# 每个判定器都是 query 的**纯函数**，所以打乱调用顺序结果必然相同。
# surface 内部也不用 if-elif：**按权重打分取最大**，平票时按固定优先级裁决。

SURFACE_RULES: dict[str, list[tuple[str, int]]] = {
    "big-screen": [(r"数据大屏|可视化大屏|指挥中心|驾驶舱|监控大屏", 10),
                   (r"\d{4}\s*[×xX*]\s*\d{4}", 6), (r"大屏", 4)],
    "spec-board": [(r"展板|设计板|流程图|交互流程|图层拆解|标注图|规范图", 10),
                   (r"\d+\s*帧", 6), (r"横向.{0,4}(排布|展开|多帧)", 4)],
    "long-image": [(r"长图|竖长图|分享长图|海报长图", 8), (r"750\s*[×xX*]", 5)],
    "web-console": [(r"dashboard|控制台|后台|工作台|管理系统|监控页|saas|b\s*端", 9),
                    (r"数据看板|报表系统|运营平台", 7)],
    "web-site": [(r"官网|网站|网页|landing|落地页|门户|主页|品牌站|作品集|website", 9),
                 (r"web端|宽屏|pc\s*页", 5)],
    "mobile-app": [(r"app|应用|小程序|客户端|ios|android", 8),
                   (r"改版|重构|首页|界面|页面|列表页|详情页|下单|点单|信息流|"
                    r"动态流|购物车|个人中心|搜索页|加载页", 5),
                   (r"移动端|手机", 3)],
    "mobile-h5": [(r"测测|测一测|生成你的|制作你的|你是哪种|你的专属|专属你|抽签|盲盒", 10),
                  (r"年度报告|年度盘点|年报|盘点|品牌故事|活动页|营销页|专题页|"
                   r"发布会|campaign", 9),
                  (r"h5", 5)],
}
# 平票裁决顺序：**信号越专的排越前**。这不是"优先级链"——
# 只有分数完全相同时才用得上它，而且它是固定的、可证伪的。
SURFACE_TIE = ["big-screen", "spec-board", "long-image", "mobile-h5",
               "web-console", "mobile-app", "web-site"]
SURFACES = list(SURFACE_TIE)

# surface → 骨架 / 成品页路径 / 门的 profile / 数量单位
SURFACE_SPEC = {
    "mobile-app": ("app", "app/index.html", "app-screen", "屏",
                   "**真实产品界面原型**：首屏就是用户日常会看到的那一屏，不是关于它的说明"),
    "mobile-h5": ("h5", "h5/index.html", "h5", "屏",
                  "分屏叙事 H5 或互动生成器：一屏一件事，结果卡是产品"),
    "web-site": ("web", "site/index.html", "web", "模块",
                 "宽屏可运行网页 1440×900"),
    "web-console": ("console", "console/index.html", "web-console", "模块",
                    "B 端控制台：表格 + 筛选 + 弹窗 + 空/异常状态，1440 与 1920 两档"),
    "spec-board": ("board", "board/index.html", "spec-board", "帧",
                   "设计展板：横向多帧 + 箭头 + 中文步骤标签，一张给人看的方案图"),
    "big-screen": ("screen", "screen/index.html", "big-screen", "区",
                   "数据大屏：按 query 给的尺寸整屏铺满，不滚动、不触控"),
    "long-image": ("longimg", "longimg/index.html", "long-image", "段",
                   "活动分享长图：750×N 单栏纵向"),
}

EXPLICIT = re.compile(
    r"数据大屏|展板|流程图|长图|dashboard|控制台|后台|官网|网站|landing|"
    r"落地页|小程序|app|h5|年度报告|活动页|作品集|"
    r"\d{3,5}\s*[×xX*]\s*\d{3,5}|\d+\s*(帧|屏|页|张|区|段)|"
    r"不要(网页|代码|html)|只要(图片|图|一张)", re.I)
RESTORE = re.compile(r"还原|复刻|1\s*:\s*1|按(参考图|设计稿|附件)|照着.{0,4}做|临摹")
REVISE = re.compile(r"改版|升级|优化|迭代|重做|把.{0,12}改|在.{0,12}基础上")
IMAGE_ONLY = re.compile(r"不要(网页|代码|html|页面)|只要(图片|图片就行|一张图|图)|"
                        r"(交|给我).{0,4}(一张|图片)", re.I)


def judge_surface(query: str, forced: str | None = None) -> tuple[str, dict]:
    """按权重打分取最大。返回 (surface, 每个 surface 的得分)。"""
    if forced:
        return forced, {forced: 99}
    score = {s: 0 for s in SURFACES}
    for s, pats in SURFACE_RULES.items():
        for pat, w in pats:
            if re.search(pat, query, re.I):
                score[s] += w
    best = max(score.values())
    if best == 0:
        return "web-site", score
    top = [s for s in SURFACE_TIE if score[s] == best]
    return top[0], score


def judge_provenance(query: str, forced: bool) -> str:
    if forced:
        return "explicit"
    _s, score = judge_surface(query)
    hits = [s for s, v in score.items() if v > 0]
    if EXPLICIT.search(query):
        # 两个不同族的载体同时被点名（"大屏图，不要网页"不算——那是交付集合的事）
        fam = {s.split("-")[0] for s in hits}
        return "ambiguous" if len(fam) > 1 and len(hits) > 2 else "explicit"
    return "inferred" if hits else "ambiguous"


def judge_operation(query: str, attachments: list[str], amend: bool) -> str:
    if amend:
        return "amend"
    if RESTORE.search(query):
        return "restore"
    if REVISE.search(query):
        return "revise"
    return "create"


def judge_deliverables(query: str) -> list[str]:
    """交什么。**默认两件必交** —— 评测集 31 题里 25 题是这个。

    只有 query 明确说了"不要网页 / 只要图片"才砍掉 html。
    注意这里的判据是**交付集合**，不是载体：「给我一张 4001×2251 大屏图」
    的载体仍然是 big-screen（照常做 HTML 再截图），只是不交 html 文件。
    """
    if IMAGE_ONLY.search(query):
        return ["image", "doc"] if not re.search(r"不要(文档|doc|方案)", query, re.I) \
            else ["image"]
    return ["html", "doc"]


# ── 需求账本（§5.6）──────────────────────────────────────
# 评测 rubric 里权重最大的一族是「用户点名的东西逐条履约」，而包里此前是**零**。
# 抽取判据必须可证伪，不做语义猜测：引号里的、数字加量词的、井号色值、尺寸。
LEDGER_RULES: list[tuple[str, re.Pattern]] = [
    ("文案", re.compile(r"[「『\"“”']([^「」『』\"“”'\n]{2,20})[」』\"“”']")),
    ("色值", re.compile(r"(#[0-9a-fA-F]{3,8})")),
    ("尺寸", re.compile(r"(\d{3,5}\s*[×xX*]\s*\d{3,5})")),
    ("必须", re.compile(r"(?:必须|需要|要有|保留|包含)([^，。；\n]{2,24})")),
    ("避免", re.compile(r"(?:避免|不使用|不要|禁止|不能有)([^，。；\n]{2,24})")),
]
COUNT_RE = re.compile(r"(恰好|正好|至少|不少于|不低于|共|一共)?\s*"
                      r"(\d+)\s*(个|屏|帧|页|张|档|类|种|区|段|块|条|栏|列)")


# 画布尺寸。大屏 / 展板 / 长图这三种**尺寸由 query 决定**，不是载体默认。
# 这条是被一个真 bug 逼出来的：4001×2251 的大屏用 1920×1080 去截，
# `transform:scale` 不改变布局尺寸 → full_page 按 4001 的布局框去截，
# 而内容被缩到中间一小块 —— 截出来大半张是空的。
# **门在哪个尺寸量、图就要在哪个尺寸截**，这两件事必须同源。
CANVAS_DEFAULT = {"big-screen": (1920, 1080), "spec-board": (1600, 1000),
                  "long-image": (750, 1600), "web-console": (1440, 900),
                  "web-site": (1440, 900), "mobile-app": (390, 844),
                  "mobile-h5": (390, 844)}
SIZE_RE = re.compile(r"(\d{3,5})\s*[×xX*]\s*(\d{3,5})")


def judge_canvas(query: str, surface: str) -> dict:
    w, h = CANVAS_DEFAULT[surface]
    m = SIZE_RE.search(query)
    src = "载体默认"
    if m and surface in ("big-screen", "spec-board", "long-image"):
        w, h = int(m.group(1)), int(m.group(2))
        src = f"原话「{m.group(0)}」"
    return {"w": w, "h": h, "source": src}


def judge_count(query: str, surface: str) -> dict:
    """数量分三档。**判据是"这个数是谁说的"，不是"它看起来重不重要"。**

      exact    用户点名了确切数量：「恰好 5 屏」，或者直接说了本载体自己的单位
               （展板说「11 帧」、移动端说「5 屏」—— 那就是规格，不是建议）
      minimum  「至少 3 个」「不少于 4 种」
      target   **脚本按载体建议的**。只报告，永不阻断 ——
               脚本自己猜的数字不能拿来阻断模型。
    """
    unit = SURFACE_SPEC[surface][3]
    for m in COUNT_RE.finditer(query):
        qual, n, u = m.group(1), int(m.group(2)), m.group(3)
        if u not in ("个", "屏", "帧", "页", "张", "区", "段", "块", "栏", "种", "类"):
            continue
        if n < 2 or n > 60:
            continue
        if qual in ("至少", "不少于", "不低于"):
            mode = "minimum"
        elif qual in ("恰好", "正好", "共", "一共") or u == unit:
            mode = "exact"
        else:
            continue                  # 别的数字（"3 个卖点"）不是交付数量
        return {"unit": u, "n": n, "mode": mode,
                "source": f"原话「{m.group(0).strip()}」"}
    return {"unit": unit, "n": None, "mode": "target", "source": "载体默认"}


def build_ledger(query: str) -> list[dict]:
    out: list[dict] = []
    seen = set()
    for kind, pat in LEDGER_RULES:
        for m in pat.finditer(query):
            v = (m.group(1) if m.lastindex else m.group(0)).strip()
            if len(v) < 2 or (kind, v) in seen:
                continue
            seen.add((kind, v))
            # 「主按钮文案必须是「立即发布」」会被"文案"和"必须"各抓一次。
            # 同一件事列两遍会让账本变噪音，而噪音会训练人忽略整份账本。
            if kind in ("必须", "避免") and any(
                    o["value"] in v for o in out if o["kind"] == "文案"):
                continue
            out.append({"kind": kind, "value": v,
                        # 否定式的挡不住换个说法，只报告不阻断（包里已证实三次）
                        "block": kind in ("文案", "色值", "尺寸")})
    return out[:24]


def classify(query: str, forced: str | None) -> str:
    """旧字段 artifactClass，由 surface 派生。保留是因为 publish / deliver /
    skeleton 都在用它，而它的语义（移动端 vs 宽屏）仍然成立。"""
    if forced:
        return forced
    return "mobile" if judge_surface(query)[0].startswith("mobile") else "web"


def product_shape(query: str, forced: str | None = None) -> str:
    """移动端交的到底是哪一种东西。顺序即优先级。

    生成器 > 叙事 > 产品界面 —— 因为前两者的信号词更专（年报、测测），
    而「首页 / 界面 / 改版」这类词几乎出现在所有 App 需求里。
    什么都没命中时，只要 query 里出现过 app / 小程序 / 客户端，
    默认就是**产品界面**：那是这一类需求的绝大多数。
    这里必须有第三个分支，默认值是叙事 —— 那正是判错形态的成因。
    """
    if forced:
        return forced
    if GENERATOR.search(query):
        return "互动生成器"
    if NARRATIVE.search(query):
        return "单向叙事"
    if PROTOTYPE.search(query):
        return "产品界面"
    return "产品界面" if APP_WORDS.search(query) else "单向叙事"


# 每种形态的三条正向口径。**放在这里而不是只放在 method/ 里**，
# 是因为它必须在合同冻结的那一刻就被打印出来 —— 那是唯一必经的路径。
SHAPE_RULES = {
    "产品界面": (
        "app/index.html", "app-screen",
        "**真实产品界面原型**：首屏就是用户日常会看到的那一屏，不是关于它的说明",
        ["首屏 = 产品首页本身。第一眼看到的就是产品，不是封面、不是标题页",
         "至少 2 个由 JS 切换的真实界面状态（切 tab / 点进详情 / 展开卡片 / "
         "下拉刷新），点了真的变",
         "不出现幻灯片语汇：标题里 0 处「方案 / 设计 / 改版 / 全貌 / 总结 / "
         "封面 / 结束」——那些属于 doc，不属于原型"]),
    "单向叙事": (
        "h5/index.html", "h5",
        "分屏叙事 H5：封面 + 内容屏 + 结束页，一屏一件事",
        ["一屏 = 100dvh，scroll-snap-stop:always，落点确定不停半屏",
         "一屏一件事、一个数据点；巨字 56–116px；进屏才播",
         "底部常驻三键：上一页 / 继续 / 分享，「继续」最强最顺手"]),
    "互动生成器": (
        "h5/index.html", "h5",
        "互动生成器：钩子 → 选择 ×2–4 → 生成中 → 专属结果卡 → 分享",
        ["选完立刻有反馈，不要「下一步」按钮",
         "把等待做成内容 —— 生成中那一屏是内容，不是转圈",
         "**结果卡是整个 H5 的产品**，前面几屏都是为了它；它必须能保存成一张图"]),
}


def asset_plan(query: str) -> list[dict]:
    roles: list[tuple[str, str, str, str]] = list(BASE_ROLES)
    seen = {r[0] for r in roles}
    for pat, extra in TOPIC_ROLES:
        if not pat.search(query):
            continue
        for r in extra:
            if r[0] not in seen:
                roles.append(r)
                seen.add(r[0])
    if len(roles) < 5:                       # 兜底：任何一稿都要有一张场景图
        roles.append(("scene-01", "image_gen", "full-bleed", "一张能定调的场景"))
    return [{"role": r, "how": h, "slot": s, "why": w} for r, h, s, w in roles]


def validate(plan: list[dict]) -> list[str]:
    errs = []
    for a in plan:
        if a["slot"] not in SLOTS:
            errs.append(f"{a['role']}: slot `{a['slot']}` 不是 {SLOTS}")
        if a["how"] == "image_gen" and a["slot"] != "full-bleed":
            errs.append(
                f"{a['role']}: how=image_gen 时 slot 只能是 full-bleed。"
                "生图只能出矩形、没有透明底，当浮动元素贴上去必然带一圈白边。"
                "异形和图标一律走 svg / css。")
    if len(plan) < 4:
        errs.append(f"assetPlan 只有 {len(plan)} 个角色——少于 4 个，"
                    "成品页一定会退化成 emoji 顶替。")
    return errs


def make_title(query: str, given: str | None) -> str:
    """标题不是被截断的 query。

    不要写成 `query[:28] + " · 设计方案"`，交付卡上的名字于是长这样：
    「为大学生群体设计一个校园论坛形式的社交app首页，核心功 · 设计方案」——
    **用户第一眼看到的就是这个。**
    现在：剥掉"为…设计一个/帮我做/我想要"这类祈使前缀，砍在第一个标点处，
    再从剩下的名词短语里取一段。取不到就退回原来的做法（不兜底成一个假标题）。
    """
    if given:
        return given
    q = re.sub(r"^\s*(请|帮我|麻烦|我想|我要|需要|能不能)?\s*"
               r"(给|为|帮)?\s*", "", query.strip())
    q = re.sub(r"^(.{0,12}?)(设计|做|出|制作)(一个|一份|一张|一套)?", "", q)
    head = re.split(r"[，。；、,;\n]", q)[0].strip()
    head = re.sub(r"^(的|了)", "", head)
    if 4 <= len(head) <= 24:
        return head + " · 设计方案"
    return (query.strip()[:20] + "… · 设计方案") if len(query) > 20 \
        else query.strip() + " · 设计方案"


def build(query: str, cls: str, workdir: Path, title: str | None,
          shape: str | None = None, surface: str | None = None,
          attachments: list[str] | None = None, amend: bool = False,
          forced_any: bool = False) -> dict:
    surface = surface or judge_surface(query)[0]
    mobile = surface.startswith("mobile")
    cls = "mobile" if mobile else "web"
    if surface == "mobile-app":
        sh = shape or "产品界面"
    elif surface == "mobile-h5":
        sh = shape or ("互动生成器" if GENERATOR.search(query) else "单向叙事")
    else:
        sh = shape
    kind, path, profile, _unit, note = SURFACE_SPEC[surface]
    if sh in SHAPE_RULES:
        path, profile, note, _rules = SHAPE_RULES[sh]
    return {
        "query": query,
        "artifactClass": cls,
        # ── 四个正交字段。各判各的，打乱调用顺序结果相同。 ──
        "surface": surface,
        "provenance": judge_provenance(query, forced_any),
        "operation": judge_operation(query, attachments or [], amend),
        # `handoff` 是"交什么"的集合。**不叫 deliverables** ——
        # 那个名字下面已经被"两件必交产物的路径表"占着，改名会连累
        # publish / deliver / ui 三个消费方，而它们关心的确实是路径。
        "handoff": judge_deliverables(query),
        "count": judge_count(query, surface),
        "canvas": judge_canvas(query, surface),
        "ledger": build_ledger(query),
        "attachments": [{"path": p, "role": "reference"} for p in (attachments or [])],
        "skeleton": kind,
        "title": make_title(query, title),
        "workdir": str(workdir),
        # 两条都是必交，缺一不算完成。
        "deliverables": {
            "doc": {
                "proposal": "doc/proposal.xml",
                "canvases": ["doc/canvas-a.html", "doc/canvas-b.html"],
                # 封面是**一张图**，不是那个 HTML 文件。
                # 实测：3/3 trace 都建了 cover.html，3/3 文档都没有封面 ——
                # 因为闭包查的是「文件在不在」，而封面要靠发布后的媒体插入才进文档。
                # 所以这里冻的是两个：出图的源（cover）和要插进去的那张图（coverImage）。
                "cover": "doc/cover.html",
                "coverImage": "shots/cover.jpg",
                "required": True,
                "note": "设计思路、设计想法、设计语言、为什么这么设计；"
                        "窄栏排版画布，像一份印出来的专题",
            },
            "product": {
                "path": path,
                "profile": profile,
                "required": True,
                "shape": sh,
                "h5Shape": sh,          # 兼容旧字段名
                "note": note,
            },
        },
        # screenRenderMode 这个字段**故意不存在**。
        # 初稿设计过一个「画面密 → 整屏生图；纯文字 → HTML」的分叉，已经推翻：
        # 分叉本身就是新的失败点（低分参照样本 就是判错了），而且生图画不了能读的中文。
        # 统一走 HTML，画面由素材层承担——生图的产能没浪费，只是换了角色。
        "assetPlan": asset_plan(query),
        # 素材下限按形态分。8 这个数标定自 gold/web-pulse(17) 与 gold/h5-qq2026(14)，
        # 那两份都是**影像驱动**的产物。
        # 实测参考库：真实的产品界面里，排行榜页 / 叫车页 / 交易流水页
        # 靠的是列表、数据和地图，**内容即画面**——
        # 对它们要 8 个满版级素材，只会逼出往列表页里塞装饰图。
        # 所以产品界面下调到 5（且小头像/缩略图现在也计数）。
        # 下限仍然远高于 低分参照样本 的 2（且那 2 个全是 emoji 冒充）。
        "minVisualAssets": 5 if sh == "产品界面" else 8,
        "frozen": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }


# 合同指纹 —— 治「冻结之后被手改」。
# 实测：plan.py 判错载体，模型**手改了 run.json**
# 把 artifactClass 从 web 改成 h5。改完之后合同还在，但它不再是脚本产出的东西，
# 后面所有以"合同为准"的核对就都失去了意义。
# 要改合同不是不行 —— 走 `plan.py --force` 重冻，那样素材计划和形态会一起重算。
HASHED = ("artifactClass", "surface", "operation", "handoff",
          "deliverables", "count", "canvas", "minVisualAssets")


def contract_hash(c: dict) -> str:
    import hashlib
    payload = json.dumps({k: c.get(k) for k in HASHED},
                         ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def main() -> int:
    ap = argparse.ArgumentParser(description="编译交付合同")
    runstate.add_run_arg(ap)
    ap.add_argument("--query")
    ap.add_argument("--dir", default=".", help="工作目录（run.json 落在这里）")
    ap.add_argument("--class", dest="cls", choices=["mobile", "web"])
    ap.add_argument("--shape", choices=list(SHAPE_RULES),
                    help="移动端交的是哪一种（不给就按 query 判）")
    ap.add_argument("--title")
    ap.add_argument("--surface", choices=SURFACES,
                    help="用户点名了产物类型就给它 —— **点名了就照他说的**")
    ap.add_argument("--attach", action="append", default=[],
                    help="用户给的参考图 / 旧版稿 / 附件，可给多次")
    ap.add_argument("--amend", action="store_true",
                    help="就地改这一稿已交付的产物（由 ui.py 判定后传进来）")
    ap.add_argument("--force", action="store_true", help="重新冻结合同（会覆盖）")
    ap.add_argument("--validate", action="store_true", help="只校验现有合同")
    a = ap.parse_args()

    if a.validate:
        run = runstate.load(runstate.find(a.run))
        if not run or not run.get("contract"):
            print("没有已冻结的合同。")
            return 1
        errs = validate(run["contract"].get("assetPlan") or [])
        for e in errs:
            print("  ✗ " + e)
        print("assetPlan 校验通过。" if not errs else f"\n{len(errs)} 条不合规。")
        return 1 if errs else 0

    if not a.query:
        ap.error("要么给 --query，要么给 --validate")

    workdir = Path(a.dir).resolve()
    workdir.mkdir(parents=True, exist_ok=True)
    path = Path(a.run).resolve() if a.run else workdir / runstate.RUN_NAME

    run = runstate.load(path) or runstate.blank(a.query)
    if run.get("contract") and not a.force:
        print(f"合同已冻结于 {run['contract']['frozen']}，不覆盖。\n"
              "  合同冻结之后就不改了——这是它治得了「最后一刻自行删减必交产物」的原因。\n"
              "  确实要改：加 --force。")
        return 1

    cls = classify(a.query, a.cls)
    contract = build(a.query, cls, workdir, a.title, a.shape,
                     surface=a.surface, attachments=a.attach, amend=a.amend,
                     forced_any=bool(a.surface or a.cls or a.shape))
    errs = validate(contract["assetPlan"])
    if errs:
        for e in errs:
            print("  ✗ " + e)
        return 1
    contract["hash"] = contract_hash(contract)

    run["query"] = a.query
    run["contract"] = contract
    runstate.save(path, run)

    d = contract["deliverables"]
    shape = d["product"].get("shape")
    print(f"合同已冻结 → {path}\n")
    # ── 四个正交字段：各判各的，不存在"谁优先" ──
    cnt = contract["count"]
    print("合同四字段（判错了就改，改一个不影响另外三个）：")
    print(f"  谁说的  provenance   {contract['provenance']:<12}"
          + {"explicit": "用户点名了 —— 本包的默认与偏好全部让位",
             "inferred": "按载体词推断的",
             "ambiguous": "信号不足或互相矛盾 —— 会改变画布尺寸/交付件数的，"
                          "**在这里问用户一次**；只影响骨架细节的按最可能的做下去"}
          [contract["provenance"]])
    print(f"  做什么  operation    {contract['operation']:<12}"
          + {"create": "新建", "revise": "按用户给的旧版改，默认全部保留，"
                                       "只改点名的那几处；doc 要有改前改后对比",
             "restore": "按参考图还原 —— **审美偏好让位于还原度**，"
                        "拆成硬约束表逐项对",
             "amend": "就地改这一稿已交付的产物，`--update` 重发同一篇，"
                      "不产生第二个链接"}[contract["operation"]])
    print(f"  长什么样 surface      {contract['surface']:<12}"
          f"{SURFACE_SPEC[contract['surface']][4]}")
    cv = contract["canvas"]
    print(f"  画布    canvas       {cv['w']}×{cv['h']:<7}"
          f"来自 {cv['source']}　← **门在这个尺寸量，图也在这个尺寸截**")
    print(f"  交什么  handoff      {'+'.join(contract['handoff']):<12}"
          f"{'两件必交，缺一不算完成' if 'html' in contract['handoff'] else '按 query 点名的来'}")
    if cnt.get("n"):
        print(f"  数量    count        {cnt['n']} {cnt['unit']:<8}"
              f"〔{cnt['mode']}〕来自 {cnt['source']}"
              + ("　← 硬的，少一个都不算完成" if cnt["mode"] == "exact"
                 else "　← 下限" if cnt["mode"] == "minimum"
                 else "　← 脚本按载体建议的，只提示不阻断"))
    if contract["ledger"]:
        print(f"\n需求账本（用户逐字点名的 {len(contract['ledger'])} 项，"
              f"ship 会逐条对账）：")
        for x in contract["ledger"]:
            print(f"  {'●' if x['block'] else '○'} {x['kind']:<5}{x['value']}"
                  + ("" if x["block"] else "　（只报告，不阻断）"))
        print("  ● 的必须**逐字**出现在产物里 —— 用户写「立即预约」就不能写「马上预约」。")
    print()
    print(f"载体：{cls}（{'移动端' if cls == 'mobile' else '宽屏'}）"
          + (f"　形态：**{shape}**" if shape else ""))
    print("必交 ①  设计方案 Doc：" + ", ".join(d["doc"]["canvases"])
          + f" + {d['doc']['cover']} + {d['doc']['proposal']}")
    print(f"        封面由 `ui.py review`（文档阶段）出图、`ui.py ship` 插进第 1 块，"
          f"插完回读确认，不成换定位再来，最多三级 —— 你不用记这两步。\n"
          f"        （封面**不能**写进 proposal 的 <img href>：飞书只吃公网 URL，"
          f"本地路径被静默丢弃且不报错）")
    print(f"必交 ②  {d['product']['note']}：{d['product']['path']}")
    # 顺序契约：先把成品页做出来，再把它的截图放进 doc。
    # 这条依赖必须在包里被表达出来 ——
    # 典型失败：关键屏都截了（各 10 张 / 6 张），进 doc 的是 **0 张**。
    # 这三步**按载体分叉**。不能无条件打印 `shoot.py screens`，
    # 而 screens 模式写死 390×844 —— 于是一份「响应式产品官网」的关键界面节
    # 变成了三台手机 —— 宽屏稿被做成了移动端的窄屏。
    # 模型当时其实起疑了（trace 原文：「shoot.py 的 screens 模式可能是移动端视口？
    # 让我检查一下代码…**实际上，让我先不管这个**」），但成本超预算就放弃了。
    # **一条错的可复制命令，比十条正确的散文更有效**（S14 反向生效）。
    if cls == "mobile":
        evidence = ("  2  这三步 `ui.py ship` 自己做完：逐个界面状态截图 → 压缩 → "
                    "转 data URI\n"
                    "  3  → 原地写进画布的 <!-- KEY-SCREENS-START --> 标记块\n"
                    "     **你不用截图、不用压缩、不用粘 <figure>** —— "
                    "隔一步的事情不会自己发生")
    else:
        evidence = ("  2  这三步 `ui.py ship` 自己做完：整页长图 → 压缩 → "
                    "转 data URI\n"
                    "  3  → 原地写进画布的 <!-- KEY-SCREENS-START --> 标记块\n"
                    "     宽屏稿的证据是**通栏长图**（.plate），不是手机机身位 —— "
                    "ship 按载体分好了")
    print(f"""
**两件必交有先后**：doc 的「关键界面」那一节放的是**成品页的真机截图**，
所以顺序是 —— 先把 {d['product']['path']} 做完、看过、改好，再回来写 doc。

  1  做成品页 → shoot.py full / screens → observe.py 看图改稿
{evidence}
  4  这时才写 doc/canvas-*.html 的关键界面节

  **那一节不放素材照片。** 实测一份真实产物把咖啡馆场景照放进了「首页改版全貌」，
  另一份把 .screens 容器建好了却一张图都没填 —— 两份的关键屏截图都躺在 shots/ 里。""")
    if shape:
        print(f"\n「{shape}」的三条正向口径（门会逐条量，缺一条就重出）：")
        for i, r in enumerate(SHAPE_RULES[shape][3], 1):
            print(f"  {i}. {r}")
        if shape == "产品界面":
            print("  —— 判错这一条的代价是最大的：典型失败是把一个「小程序首页改版」\n"
                  "     做成了 5 屏宣讲 deck，第 4 屏叫「完整首页 · 改版后全貌」，\n"
                  "     里面贴了一张 400px 的缩略图。那是严重缺陷。\n"
                  f"     形态判错了就换：{runstate.UI} brief --force --shape 单向叙事 --query \"…\"")
    print(f"\n素材计划（{len(contract['assetPlan'])} 个角色，"
          f"成品页最少 {contract['minVisualAssets']} 个真实视觉资产）：")
    for x in contract["assetPlan"]:
        print(f"  · {x['role']:16} {x['how']:13} {x['slot']:11} {x['why']}")
        # M4：这一行只说**不能用什么**，没说**去哪儿拿** ——
        # 结果 4.3MB 的图标库调用 0 次，图标只能手搓或者用 emoji 顶，
        # 而 anti-patterns 的第一条正是「不许用 emoji 冒充主视觉」。
        # 一条可复制的命令比十条禁止措辞有效（S14，本 trace 已验证两次）。
        if x["role"] == "icon-set":
            print(f"      包里有 Phosphor 全套（MIT，1512 个，6 种字重，"
                  f"fill=currentColor，viewBox 0 0 256 256）：\n"
                  f"        python3 {ROOT / 'scripts' / 'icons.py'} find "
                  f"搜索 消息 发布 我的\n"
                  f"      ← 直接打印可内联的 <svg>。"
                  f"**不要手搓 path，也不要用 emoji。**")
    kind = "04-build-h5.md" if cls == "mobile" else "04-build-web.md"
    ranges = ("  字阶断崖 H1÷正文   p10 2.8 / 中位 3.6 / p90 6.9\n"
              "  正文字号          p10 14 / 中位 16 / p90 20\n"
              "  圆角              获奖库中位 3px，12 份里 4 份纯直角\n"
              "                    —— 常见产物的实测中位是 50px（全是胶囊），"
              "这是差得最远的一项\n"
              "  强调色饱和度       中位 0.80，12 份里 10 份 >=0.6")
    if cls == "mobile" and shape != "产品界面":
        ranges += (
            "\n\n  **先回答一个问题再动手：这件事在现实里最像什么？**\n"
            "    实看数英的 H5 项目榜，头部作品几乎都借了一个现实世界的形态——\n"
            "    一台旧机器 / 一个电视新闻台 / 一套非遗版画 / 一座俯视微缩城 / 左右对分的两极。\n"
            "    借到了世界，色板字体图标转场文案口吻就都有了出处，而且天然不会和别人撞；\n"
            "    借不到，产出就只能被描述成「深色 + 渐变 + 大数字」——"
            "那正是每年都像同一张的成因。\n"
            "    见 craft/composition-motion.md 第四节。")
    if cls == "mobile":
        ranges += ("\n  注意：字阶下沿 2.8 对**年报 / 活动 H5** 成立，"
                   "对 **App / 小程序界面稿不成立**\n"
                   "        —— 真实 App 的标题就是 24–32px，"
                   "包内 gold/h5-cycle 实测 1.9 是对的。")
    if shape == "产品界面":
        ranges += ("\n\n  **这一稿的对手不是获奖 H5，是用户手机里那个真的 App。**\n"
                   "    参照 gold/app-home/（真实产品首页原型，带 tab 切换与详情态），\n"
                   "    交互工艺见 craft/interaction-contract.md —— 那九条讲的是\n"
                   "    「控件和内容怎么响应状态」，与题材无关，产品界面同样适用。")
    if cls == "mobile":
        ranges += ("\n\n  交互工艺：craft/interaction-contract.md（九条，按形态给了两种落法）")
    print(f"""
两条都是必交，缺一不算完成——publish.py 会核对。

必读五件套（动手之前读完，约 7 秒；不是"按需"）：
  craft/award-mechanisms.md      什么叫得奖级 —— 未读它之前不要开始定风格
  craft/scale-atlas.md           12 份获奖稿的数值**区间** —— 未读它之前不要定字阶和圆角
  craft/composition-motion.md    构图与动效的**关系** —— 未读它之前不要决定首屏长什么样
  craft/aesthetic-baseline.md    四组数值的判据 —— 未读它之前不要写 :root
  method/{kind:<22} 这个载体怎么做 —— 未读它之前不要拷骨架
  reference/image-direction.md   生图门 A 八项 —— 采素材之前读

  不要写成"三份就够开工，其余按需"，并许诺"脚本会打印给你"。
  那个通路根本不存在。工艺必须有一条会被真的走的路，这就是那条路。

本载体的参考区间（**区间不是目标值**，落在哪一段由签名定）：
{ranges}""")
    print(opponent_card(ROOT, shape, cls, contract["surface"]))
    # NEXT 由编排器统一给（守则 S24：一条命令的输出里只能有一个 NEXT）。
    if not runstate.orchestrated():
        print("\n下一步：动作 1 看参考 → 动作 2 采素材（**先把素材落地，再排版式**）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
