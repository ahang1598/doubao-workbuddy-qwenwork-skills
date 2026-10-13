#!/usr/bin/env python3
"""query → 六维风格签名，并强制与最近几次不同。

这条是给"无数人用"最关键的一条。

实测的病：低分参照样本 的 doc 画布把 gold 的**结构学去了，工艺没学去**——
章节头、四宫格、拒绝清单一模一样，关键屏区退化成 5 行完全相同的
「左手机 + 右三段清单」，图标全用 emoji。
**gold 成了模板。**

根因不是执行者偷懒，是包里**没有一条 query → 风格的确定性通道**。
把风格锁死成 13 套 design_kits 是错的，但只删不补同样不行，
于是只能凭"最近见过什么"来选，必然收敛。作为官方 skill 给无数人用，
这个方向必须掐死：**gold 的身份是「机制的证据」，不是「可以照抄的版式」。**

这个脚本产出的是**签名**，不是样式表——一行 CSS 都不产。
配色、字号、圆角、构图仍然是你写的；它只回答"这一稿该往哪个方向长"。

用法：
    python3 style.py --query "<当前请求原文>" [--set ground=dark] [--out style.json]
    python3 style.py --diverge a/index.html b/index.html    # 两稿的 CSS 差异度
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import runstate  # noqa: E402

# 历史文件必须是**用户级**的，不能是 workdir 级的。
#
# 不要写成 HISTORY = ".style-history.json"（相对 cwd），
# 而每个任务一个新 workdir、style.py 一个任务只跑一次 ——
# **history 永远是空的**。空 history 时下面 choose 的 min 排序键
# 对所有候选都是 (0, -99)，于是退化成"取字典里的第一个键"：
# ground=dark  typeVoice=sans-cool  imageWorld=photo
# layoutLogic=grid  colorStrategy=mono-neutral  motionVoice=still
# 三条真实 trace 的 ground **3/3 是 dark**，colorStrategy 3/3 是 mono-neutral。
# 一个为了防止"所有人的产出长得一样"而写的脚本，实际效果是让所有人的产出长得一样。
# 「校园主题用了黑色」不是审美失误，是这个包对任何没命中关键词的 query 的固定答案。
HISTORY = str(Path.home() / ".cache" / "ui-design-v2" / "style-history.json")

# 六个维度。每个选项后面是**判别它的语义线索**，不是随机权重。
# 没有线索命中时**留空**，把这一维交回给你 —— 见 choose。
DIMS: dict[str, dict[str, list[str]]] = {
    "ground": {                       # 底色是承诺，不是背景
        "dark": ["夜", "暗", "科技", "游戏", "影音", "酷", "赛博", "潮", "硬核", "音乐"],
        "light": ["清爽", "简洁", "医疗", "健康", "办公", "效率", "教育", "干净",
                  "校园", "学生", "大学", "课堂", "亲子", "母婴", "阅读", "笔记",
                  "学习", "考研", "自习"],
        "saturated": ["活动", "促销", "节日", "年轻", "冲击", "营销", "潮玩", "运动",
                      "骑行", "跑步", "户外", "健身", "球",
                      "社交", "论坛", "动态", "话题", "社区", "校园", "青春",
                      "ugc", "打卡", "表白"],
        "paper": ["文化", "书", "杂志", "手作", "茶", "复古", "档案", "报", "展",
                  "手账", "日记", "图书馆", "文具"],
    },
    "typeVoice": {
        "sans-cool": ["科技", "效率", "工具", "saas", "后台", "数据", "金融"],
        "serif-editorial": ["文化", "杂志", "奢", "品牌", "故事", "书", "展", "酒"],
        "condensed-poster": ["运动", "潮", "音乐", "球", "赛", "冲击", "街",
                             "骑行", "跑步", "户外", "装备"],
        "rounded-friendly": ["儿童", "宠物", "社区", "亲子", "生活", "萌", "陪伴",
                             "校园", "学生", "论坛", "动态", "话题", "ugc", "青春"],
        "display-art": ["活动", "年度", "盘点", "campaign", "h5", "美术字", "国潮"],
    },
    "imageWorld": {
        "photo": ["实拍", "人物", "服饰", "食", "旅行", "房", "场景", "餐", "咖啡",
                  "骑行", "户外", "路线", "地图", "天气", "城市",
                  "校园", "学生", "社区", "邻里", "晒单"],
        "render3d": ["数码", "硬件", "汽车", "材质", "产品", "工业", "3d"],
        "illustration": ["儿童", "教育", "故事", "插画", "宠物", "萌", "科普"],
        "graphic-abstract": ["数据", "金融", "saas", "分析", "抽象", "后台", "报表"],
        "none": ["纯文字", "文档", "条款", "说明"],
    },
    "layoutLogic": {
        "grid": ["商品", "列表", "目录", "商城", "作品集", "档案"],
        "axial": ["宣言", "品牌", "单品", "主张", "发布"],
        "collage": ["杂志", "潮", "青年", "文化", "拼", "街",
                    "论坛", "信息流", "动态", "广场", "瀑布流"],
        "full-bleed-stack": ["沉浸", "大片", "旅行", "影音", "空间", "展"],
        "long-scroll": ["年度", "盘点", "故事", "叙事", "历程", "报告",
                        "路线", "行程", "流程", "一天"],
    },
    "colorStrategy": {
        "mono-neutral": ["克制", "高级", "奢", "极简", "黑白", "性冷淡"],
        "duotone-clash": ["潮", "运动", "冲击", "年轻", "街", "对撞"],
        "tri-role": ["工具", "后台", "saas", "系统", "效率", "多状态"],
        "full-color": ["儿童", "节日", "活动", "缤纷", "游乐", "美食",
                       "社交", "校园", "青春", "ugc"],
    },
    "motionVoice": {
        "still": ["文档", "严肃", "医疗", "政务", "条款"],
        "slow-push": ["品牌", "奢", "空间", "建筑", "静"],
        "parallax": ["官网", "landing", "产品", "故事"],
        "type-in": ["宣言", "主张", "文案", "标题"],
        "scene-advance": ["h5", "年度", "盘点", "活动", "翻页", "一屏"],
    },
}

WHY = {
    "ground": "底色（暗场 / 亮场 / 高饱和色场 / 纸感）",
    "typeVoice": "字的性格（无衬线冷静 / 衬线编辑 / 压缩体海报 / 圆体友好 / 美术字）",
    "imageWorld": "影像世界（实拍 / 3D 渲染 / 插画 / 图形抽象 / 无影像）",
    "layoutLogic": "版面逻辑（网格 / 中轴 / 拼贴 / 满版叠压 / 长滚动叙事）",
    "colorStrategy": "配色分工（单色+中性 / 双色对冲 / 三色分工 / 全彩）",
    "motionVoice": "动的语气（静 / 缓推 / 位移视差 / 逐字入场 / 场景推进）",
}

MIN_DIFF = 3       # 与最近 N 次至少 3 维不同
RECENT = 5


def score(query: str) -> dict[str, dict[str, int]]:
    q = query.lower()
    return {d: {opt: sum(1 for k in keys if k.lower() in q)
                for opt, keys in opts.items()}
            for d, opts in DIMS.items()}


def load_history(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))[-RECENT:]
    except Exception:
        return []


def diff_count(a: dict, b: dict) -> int:
    """只比**两边都定了值**的维度。留空的维度还没做决定，算不上"相同"。"""
    return sum(1 for d in DIMS
               if a.get(d) and b.get(d) and a.get(d) != b.get(d))


def choose(sc: dict, history: list[dict], forced: dict) -> tuple[dict, dict]:
    """有语义信号就按信号取；**没有信号就留空，不兜底。**

    不要写成"取最近几稿用得最少的那个"。那种兜底在真实链路里
    等于"永远取字典第一个键"（history 见 HISTORY 的注释）。
    兜底值最恶劣的地方不是它不准，是**它会被当成结论用掉**：
    模型读到 `ground dark`，就照着 dark 写了一整稿，
    而这个 dark 里没有任何关于"这一稿该是什么样"的信息。

    留空则强制一次判断。「校园社交 App 该是亮场还是暗场」——模型判得出来。
    信号不足留空不兜底，这条在隔壁包（doubao-visual-creative ）已经验证过。

    平手也留空：ground 里「校园」同时出现在 light 与 saturated，这是**故意的**。
    """
    sig, conf = {}, {}
    for d, opts in sc.items():
        if d in forced:
            sig[d], conf[d] = forced[d], "你指定的"
            continue
        best = max(opts.values())
        top = [o for o, v in opts.items() if v == best]
        if best > 0 and len(top) == 1:
            sig[d] = top[0]
            conf[d] = f"语义命中 {best} 个线索"
        elif best > 0:
            sig[d] = None
            conf[d] = ("平手：" + " / ".join(sorted(top))
                       + f" 各命中 {best} 个线索 —— 由你按内容定")
        else:
            sig[d] = None
            conf[d] = "query 没给这一维的信号 —— 由你按内容定"
    # 拉开与历史的差异：只在**已经有值**的维度之间比，且只提示不强改。
    # 不要把"没有语义信号"的维度依次换掉：那是拿一个假值去修另一个假值。
    return sig, conf


def css_tokens(path: Path) -> set[str]:
    t = path.read_text(encoding="utf-8", errors="ignore")
    css = " ".join(re.findall(r"<style[^>]*>(.*?)</style>", t, re.S | re.I)) or t
    css = re.sub(r"/\*.*?\*/", " ", css, flags=re.S)
    # 只看**视觉层**声明。几何/机箱（display、position、overflow…）本来就该复用，
    # 拿它们算差异度会把"机箱可复用"判成抄袭。
    return set(re.findall(
        r"(?:color|background[\w-]*|font-[\w-]+|border-radius|box-shadow|"
        r"letter-spacing|line-height|text-transform|filter|opacity)\s*:\s*[^;{}]+", css))


def main() -> int:
    ap = argparse.ArgumentParser(description="六维风格签名")
    runstate.add_run_arg(ap)
    ap.add_argument("--query")
    ap.add_argument("--set", action="append", default=[],
                    help="覆盖某一维，如 --set ground=dark（你比脚本更懂这一稿）")
    ap.add_argument("--history", default=HISTORY)
    ap.add_argument("--out", default="style.json")
    ap.add_argument("--diverge", nargs=2, metavar=("A", "B"),
                    help="量两稿视觉层 CSS 的 Jaccard 差异度")
    a = ap.parse_args()

    if a.diverge:
        x, y = (css_tokens(Path(p)) for p in a.diverge)
        j = len(x & y) / len(x | y) if (x | y) else 1.0
        print(f"视觉层 CSS Jaccard = {round(j, 3)}（{len(x & y)} 交 / {len(x | y)} 并）")
        ok = j <= 0.55
        print("PASS —— 两稿不是同一套模板。" if ok else
              "FAIL —— 两稿视觉层重合 >0.55，这是「所有人的产出长得一样」的样子。\n"
              "  机箱（分屏、安全区、取景框）可以相同，**人格不可以**：\n"
              "  底色、字的性格、影像世界、版面逻辑要按各自的签名重新长一遍。")
        return 0 if ok else 1

    if not a.query:
        ap.error("要么给 --query，要么给 --diverge")

    forced = dict(s.split("=", 1) for s in a.set if "=" in s)
    for d, v in forced.items():
        if d not in DIMS or v not in DIMS[d]:
            print(f"--set {d}={v} 不合法。{d} 可选：{list(DIMS.get(d, {}))}")
            return 1

    hist_path = Path(a.history)
    hist_path.parent.mkdir(parents=True, exist_ok=True)
    history = load_history(hist_path)
    sig, conf = choose(score(a.query), history, forced)

    open_dims = [d for d in DIMS if not sig.get(d)]
    diffs = [diff_count(sig, h["signature"]) for h in history]
    style = {"query": a.query, "signature": sig, "why": conf,
             "open": open_dims,
             "divergence": {"vsRecent": diffs, "min": min(diffs) if diffs else None,
                            "require": MIN_DIFF}}
    Path(a.out).write_text(json.dumps(style, ensure_ascii=False, indent=2),
                           encoding="utf-8")
    history.append({"query": a.query, "signature": sig})
    hist_path.write_text(json.dumps(history[-20:], ensure_ascii=False, indent=2),
                         encoding="utf-8")

    run_path = runstate.find(a.run)
    if run_path:
        data = runstate.load(run_path) or runstate.blank(a.query)
        data["style"] = style
        runstate.save(run_path, data)

    print(f"风格签名 → {a.out}\n")
    for d in DIMS:
        v = sig.get(d) or "（待你定）"
        print(f"  {d:15} {v:18} {WHY[d]}\n  {'':15} └ {conf[d]}")
    if open_dims:
        print(f"\n有 {len(open_dims)} 维留空了。**留空不是脚本没算出来，是它拒绝替你猜。**")
        print("  这里**不兜底**成「取最近几稿用得最少的那个」，因为历史文件在真实链路里")
        print("  永远是空的，于是它退化成「取第一个键」：三条真实 trace 的 ground 全是 dark。")
        print("  「校园社交 App 用黑底」就是这么来的 —— 不是审美失误，是默认值。\n")
        for d in open_dims:
            print(f"  {d}　{WHY[d]}")
            for opt, keys in DIMS[d].items():
                print(f"    {opt:18} 线索：{'、'.join(keys[:10])}")
            print(f"    → 定了就写回去：python3 {runstate.SCRIPTS}/style.py "
                  f"--query \"…\" --set {d}=<值>\n")
    if diffs:
        print(f"与最近 {len(diffs)} 稿**都定了值的维度**里的差异：{diffs} 维"
              f"（要求 >= {MIN_DIFF}）")
        if min(diffs) < MIN_DIFF:
            print("  差异不够，但有语义信号的维度不会被强行换掉 ——\n"
                  "  风格要服从内容。这里请你自己用 --set 换掉一到两维。")
    print("\n这只是方向。**配色、字号、圆角、构图仍然是你写的。**\n"
          "gold/ 是机制的证据，不是可以照抄的版式：\n"
          "  允许学 —— 为什么用 2px 墨线做章节分隔、为什么商品缝隙压到 4px。\n"
          "  禁止抄 —— 四宫格的具体排法、章节编号的具体样式、关键屏网格的具体结构。\n"
          "  **产物和 gold 在版式上一眼能认出是同一套模板，就是抄了。**")
    return 0


if __name__ == "__main__":
    sys.exit(main())
