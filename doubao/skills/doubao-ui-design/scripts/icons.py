#!/usr/bin/env python3
"""图标取用器 —— 把包里那 4.3MB 图标库送到手上。

**存在的理由是到达率。** 只在 `assetPlan` 里写一行
「icon-set  svg  inline  图标必须用 SVG —— 生图出不了透明底」。
它说了**不能用什么**，没说**去哪儿拿**。结果：

    assets/phosphor/catalog.json      调用 0 次
    图标全部手搓 <path> 或者用 emoji 顶

而 `craft/anti-patterns.md` 的第一条正是「不许用 emoji 冒充主视觉」。
**规则没有变成产能，模型手上没有图，就只能拿 emoji 顶** —— 这个坑
典型失败是拿 ☀️💧🚻🪑 当图标，而只写一条禁令并不能阻止它。

S14：**一条可复制的命令比十条禁止措辞有效。** 同一段 trace 里，
`plan.py` 打印的 `shoot.py screens` 和 `pack_img` 两条命令，模型**真的直接跑了**。

用法：
    python3 <SKILL>/scripts/icons.py find 搜索 消息 发布 我的
    python3 <SKILL>/scripts/icons.py find heart bookmark --weight fill
    python3 <SKILL>/scripts/icons.py list 导航            # 只看有哪些候选，不出码

输出就是可以直接内联进 HTML 的 <svg>（MIT 协议，fill=currentColor，
viewBox 0 0 256 256）—— 不用下载、不用外链、不占素材预算。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "assets" / "phosphor"
CATALOG = PKG / "catalog.json"
ZIP = PKG / "phosphor-svgs-flat.zip"
WEIGHTS = ["regular", "bold", "fill", "light", "thin", "duotone"]

# 中文 → Phosphor 名字。只收**产品界面真的会用到**的那些词。
# 收不全是正常的：收不到就退回英文子串匹配，再收不到就打印最接近的几个候选，
# 让你自己挑 —— 空结果必须给下一步的确定性输入（S13）。
ZH = {
    "首页": ["house", "house-simple"], "主页": ["house"],
    "搜索": ["magnifying-glass"], "查找": ["magnifying-glass"],
    "消息": ["chat-circle", "chat-teardrop", "envelope"],
    "聊天": ["chat-circle-dots", "chats"], "评论": ["chat-text", "chats-circle"],
    "通知": ["bell", "bell-ringing"], "提醒": ["bell-simple"],
    "我的": ["user", "user-circle"], "个人": ["user-circle"],
    "用户": ["user", "users"], "头像": ["user-circle"], "队伍": ["users-three"],
    "发布": ["plus", "plus-circle", "pencil-simple-line"],
    "新建": ["plus-circle"], "添加": ["plus"], "编辑": ["pencil-simple"],
    "删除": ["trash", "trash-simple"], "关闭": ["x", "x-circle"],
    "返回": ["arrow-left", "caret-left"], "前进": ["arrow-right", "caret-right"],
    "更多": ["dots-three", "dots-three-outline"], "菜单": ["list", "list-dashes"],
    "设置": ["gear", "gear-six", "sliders-horizontal"], "筛选": ["funnel", "sliders"],
    "排序": ["sort-ascending", "arrows-down-up"],
    "点赞": ["thumbs-up", "heart"], "喜欢": ["heart", "heart-straight"],
    "收藏": ["bookmark-simple", "star"], "星标": ["star", "star-four"],
    "分享": ["share-network", "share-fat", "export"], "转发": ["arrow-bend-up-right"],
    "下载": ["download-simple"], "上传": ["upload-simple"],
    "购物车": ["shopping-cart-simple", "shopping-bag-open"],
    "订单": ["receipt", "clipboard-text"], "支付": ["credit-card", "wallet"],
    "钱包": ["wallet"], "优惠券": ["ticket", "tag"], "价格": ["tag", "currency-cny"],
    "商品": ["package", "storefront"], "店铺": ["storefront"],
    "地址": ["map-pin", "map-pin-line"], "定位": ["navigation-arrow", "crosshair"],
    "地图": ["map-trifold"], "路线": ["path", "signpost"],
    "时间": ["clock"], "日历": ["calendar-blank", "calendar-dots"],
    "日程": ["calendar-check"], "闹钟": ["alarm"],
    "相机": ["camera"], "照片": ["image", "images"], "图片": ["image-square"],
    "视频": ["video-camera", "play-circle"], "播放": ["play", "play-circle"],
    "暂停": ["pause", "pause-circle"], "音乐": ["music-notes", "music-note"],
    "话筒": ["microphone"], "语音": ["microphone", "waveform"],
    "文件": ["file", "file-text"], "文档": ["file-doc", "article"],
    "文件夹": ["folder", "folder-simple"], "附件": ["paperclip"],
    "链接": ["link", "link-simple"], "二维码": ["qr-code"],
    "统计": ["chart-bar", "chart-line-up"], "数据": ["chart-pie-slice", "database"],
    "趋势": ["trend-up", "chart-line-up"], "报表": ["chart-bar-horizontal"],
    "锁": ["lock", "lock-simple"], "安全": ["shield-check"],
    "帮助": ["question", "info"], "信息": ["info"], "警告": ["warning", "warning-circle"],
    "成功": ["check-circle", "check"], "失败": ["x-circle"], "加载": ["spinner", "circle-notch"],
    "刷新": ["arrows-clockwise", "arrow-clockwise"],
    "眼睛": ["eye", "eye-slash"], "隐藏": ["eye-slash"],
    "火": ["fire", "fire-simple"], "热门": ["fire", "trend-up"],
    "标签": ["tag", "hash"], "话题": ["hash"], "圈子": ["users-three", "circles-three"],
    "学校": ["graduation-cap", "student"], "课程": ["book-open", "chalkboard-teacher"],
    "书": ["book", "book-bookmark"], "笔记": ["notebook", "note-pencil"],
    "运动": ["person-simple-run", "barbell"], "健身": ["barbell"],
    "骑行": ["bicycle", "person-simple-bike"], "跑步": ["person-simple-run"],
    "天气": ["cloud-sun", "sun"], "太阳": ["sun"], "月亮": ["moon"],
    "咖啡": ["coffee"], "餐": ["fork-knife", "bowl-food"], "食物": ["bowl-food"],
    "外卖": ["moped", "bag"], "配送": ["truck"],
    "电量": ["battery-high"], "信号": ["cell-signal-high"], "网络": ["wifi-high"],
    "机器人": ["robot"], "闪电": ["lightning"], "礼物": ["gift"],
    "旗帜": ["flag"], "皇冠": ["crown-simple"], "奖杯": ["trophy"], "勋章": ["medal"],
}


def load() -> tuple[list[str], zipfile.ZipFile]:
    if not CATALOG.is_file() or not ZIP.is_file():
        print(f"图标库不在盘上（要 {CATALOG} 与 {ZIP}）。", file=sys.stderr)
        sys.exit(1)
    names = json.loads(CATALOG.read_text(encoding="utf-8"))["icons"]
    return names, zipfile.ZipFile(ZIP)


def score(name: str, term: str) -> int:
    """越小越好。精确 > 前缀 > 子串 > 词根。"""
    if name == term:
        return 0
    if name.startswith(term + "-"):
        return 1
    if term in name.split("-"):
        return 2
    if term in name:
        return 3
    return 99


def candidates(names: list[str], term: str, k: int = 4) -> list[str]:
    t = term.strip().lower()
    picks: list[str] = []
    for want in ZH.get(term.strip(), []):
        if want in names and want not in picks:
            picks.append(want)
    if not picks and re.fullmatch(r"[a-z0-9\-]+", t):
        ranked = sorted(((score(n, t), len(n), n) for n in names),
                        key=lambda x: (x[0], x[1]))
        picks = [n for s, _l, n in ranked if s < 99][:k]
    return picks[:k]


def svg_of(z: zipfile.ZipFile, name: str, weight: str) -> str | None:
    suffix = "" if weight == "regular" else f"-{weight}"
    path = f"SVGs Flat/{weight}/{name}{suffix}.svg"
    try:
        return z.read(path).decode("utf-8")
    except KeyError:
        return None


def inline(svg: str, name: str, size: int) -> str:
    """加上尺寸与 aria，其余原样 —— fill=currentColor 意味着它跟着文字颜色走，
    换主题不用改图标。**不要自己改 path**。"""
    return re.sub(r"<svg ",
                  f'<svg class="ic ic-{name}" width="{size}" height="{size}" '
                  f'aria-hidden="true" focusable="false" ', svg, count=1)


def main() -> int:
    ap = argparse.ArgumentParser(description="从包内 Phosphor 库取图标（MIT）")
    ap.add_argument("cmd", choices=["find", "list"])
    ap.add_argument("terms", nargs="+", help="中文或英文关键词")
    ap.add_argument("--weight", default="regular", choices=WEIGHTS,
                    help="一稿只用一种字重 —— 混用是最常见的图标不统一成因")
    ap.add_argument("--size", type=int, default=24)
    a = ap.parse_args()

    names, z = load()
    print(f"Phosphor {len(names)} 个图标 · 字重 {a.weight} · MIT · "
          f"fill=currentColor · viewBox 0 0 256 256")
    print(f"**一稿只用一种字重**（现在是 {a.weight}）—— 混用是图标不统一的头号成因。\n")
    miss = []
    for term in a.terms:
        cs = candidates(names, term)
        if not cs:
            miss.append(term)
            continue
        print(f"── {term} → {'、'.join(cs)}"
              + (f"（挑了第一个：{cs[0]}）" if len(cs) > 1 else ""))
        if a.cmd == "list":
            continue
        svg = svg_of(z, cs[0], a.weight)
        if svg is None:
            print(f"   （{cs[0]} 在 {a.weight} 字重里没有，换 --weight regular）")
            continue
        print(inline(svg, cs[0], a.size) + "\n")
    if miss:
        print(f"\n没命中：{'、'.join(miss)}")
        print("  两条路：① 换个更常见的说法（'我的' 而不是 '个人中心页签'）\n"
              "         ② 直接给英文名，1512 个名字在 assets/phosphor/catalog.json 里\n"
              "  **别退回手搓 <path>，更别用 emoji**"
              "（craft/anti-patterns.md 第一条就是这个）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
