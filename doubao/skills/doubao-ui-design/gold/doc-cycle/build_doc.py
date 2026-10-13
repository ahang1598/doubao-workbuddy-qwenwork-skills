#!/usr/bin/env python3
"""gold #3 · 骑行 App「今天骑不骑」设计方案画布。

【它在三份 gold 里承担的职责：证明文档人格必须随主题变】

同样是七节汇报结构，这一份和 PULSE / QQ 那两份**长得完全不一样**：

|        | PULSE / QQ（编辑体）        | 本份（自然体）                  |
|--------|---------------------------|-------------------------------|
| 底色   | 骨色 / 深场                | 沙色 #FAF8F4，纸感             |
| 墨色   | 近黑 #14140F              | 棕灰 #3A3530，比纯黑暖         |
| 主色   | 信号橙红 / QQ 蓝          | 橄榄绿 #6B8E5A + 陶土橙 #D9634F |
| 字     | 压缩重体 + 等宽小标签      | 圆润无衬线，无等宽             |
| 分隔   | 2px 墨线 + 巨编号         | 卡片 + 柔和多层阴影            |
| 圆角   | 直角为主，只有可点的是圆的 | 12 / 20 / 32，处处圆润         |

**结构可以共享，人格不能共享。** 一个周末骑行的产品如果用 PULSE 那套
硬边编辑体，气质就错了——它讲的是"轻松出门转一圈"，不是"跑给自己看"。

七节顺序与另外两份一致：理解 → 机会 → 主张 → 视觉语言 → 动线 → 有效 → 下一步。
正文不出现 px / hex / 选择器 / 拒绝清单 / 验收边界；数值放四宫格里被看到。
"""
import base64
import pathlib
import sys

BASE = pathlib.Path(__file__).parent
IMG = BASE / "img"


def b64(name: str) -> str:
    return "data:image/jpeg;base64," + base64.b64encode((IMG / name).read_bytes()).decode()


CSS = """
/* 注意：这个文件不对 CSS 做 % 格式化，所以百分号是单个 %。
   （从 build_docs.py 抄 CSS 时容易把 %% 转义带过来 —— 那会让
   `minmax(min(100%,250px),1fr)` 变成非法值，整条 grid 声明被丢弃，
   四宫格静默塌成一列。实测踩过。） */
*{box-sizing:border-box;margin:0;padding:0}
.cv{
  /* --ink-3 是最浅的一级灰。它一度是 #A8A095，在沙底上实测 2.44:1——
     眉标和页脚整行读不出来，而肉眼只觉得"淡了点"。真值门抓到的。
     浅灰的下限就在这里，别再往上调。 */
  --sand:#FAF8F4; --paper:#FFFFFF; --ink:#3A3530; --ink-2:#7A7268; --ink-3:#8A8276;
  --moss:#6B8E5A; --moss-soft:#A8C49A; --clay:#D9634F; --line:rgba(58,53,48,.12);
  --r-card:20px; --r-shell:32px; --r-ctl:12px;
  --sh:0 1px 2px rgba(58,53,48,.05), 0 8px 24px -10px rgba(58,53,48,.16);
  width:100%; max-width:900px; margin:0 auto;
  /* 阅读边距：文字不能贴着块边。飞书块宽 560–1145 浮动，所以用 clamp 跟着走。
     顶部那条色带要满幅，所以它用负 margin 顶出去（见 .topbar）。 */
  --gut:clamp(24px,4.6vw,56px); background:var(--sand); color:var(--ink);
  font-family:"Nunito","PingFang SC","Hiragino Sans GB","Microsoft YaHei",system-ui,sans-serif;
  font-size:15.5px; line-height:1.9; -webkit-font-smoothing:antialiased;
  padding:0 var(--gut) 52px;
}
.cv img{display:block;max-width:100%;height:auto}
.cv b{font-weight:800}

/* 页眉：一条圆头绿线 + 圆润眉标。没有等宽字，没有大字距 */
.topbar{height:6px;border-radius:0 0 6px 6px;background:var(--moss);margin:0 calc(var(--gut) * -1) 24px}
.runhead{display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap;
  font-size:13px;font-weight:800;color:var(--ink-2);padding-bottom:14px}
.runhead span:last-child{color:var(--moss)}

/* 章节头：编号做成绿色圆牌，而不是墨线 + 巨号 */
.sec{padding-top:52px}
.sec-top{display:flex;align-items:center;gap:14px;margin-bottom:6px}
.sn{width:38px;height:38px;flex:none;border-radius:50%;background:var(--moss);color:#fff;
  display:grid;place-items:center;font-size:15px;font-weight:800}
.sec-top h2{font-size:25px;font-weight:800;line-height:1.3;letter-spacing:-.005em}

.lede{font-size:17.5px;line-height:1.95;margin-top:18px;max-width:42em}
.lede em{font-style:normal;color:var(--moss);font-weight:800}
.body{font-size:15.5px;line-height:1.92;margin-top:16px;max-width:42em;color:#4A443E}

/* 洞察：一张浅绿的圆角卡，不是左边一道竖线 */
.insight{margin-top:24px;padding:26px 28px;border-radius:var(--r-shell);
  background:linear-gradient(160deg,#EAF1E4,#F4F7F0);box-shadow:var(--sh)}
.insight .k{display:inline-block;background:var(--moss);color:#fff;border-radius:999px;
  padding:5px 13px;font-size:12px;font-weight:800;margin-bottom:14px}
.insight p{font-size:19.5px;line-height:1.66;font-weight:800;letter-spacing:-.005em}

/* 主张：整块沙色圆角，居中 */
.claim{margin-top:28px;padding:44px 28px;border-radius:var(--r-shell);
  background:var(--ink);color:var(--sand);text-align:center;box-shadow:var(--sh)}
.claim q{quotes:none;display:block;font-size:clamp(28px,4.2vw,40px);font-weight:800;
  line-height:1.34;letter-spacing:-.01em}
.claim q em{font-style:normal;color:var(--moss-soft)}
.claim .why{margin-top:18px;font-size:14.5px;line-height:1.9;color:rgba(250,248,244,.76);
  max-width:32em;margin-inline:auto}

/* 版面证据 */
.plate{margin-top:26px}
.plate img{width:100%;border-radius:var(--r-card);box-shadow:var(--sh)}
.plate .cap{font-size:14px;color:var(--ink-2);margin-top:13px;line-height:1.85;max-width:42em}
.plate .cap b{color:var(--ink)}

/* 左标签右正文：标签做成绿色圆角小牌 */
.dl{margin-top:24px;display:grid;gap:12px}
.dl .r{display:grid;grid-template-columns:minmax(76px,88px) 1fr;gap:16px;align-items:start;
  background:var(--paper);border-radius:var(--r-card);padding:18px 20px;box-shadow:var(--sh)}
.dl dt{background:#EAF1E4;color:var(--moss);border-radius:999px;padding:5px 0;
  text-align:center;font-size:12.5px;font-weight:800}
.dl dd{font-size:15px;line-height:1.9}

/* ── 列数必须整除项数，否则会出现"孤儿行"（3+1 / 5+1），整版立刻显乱 ──
   auto-fit 的列数随宽度浮动，控制不住；飞书块宽又在 560–1145 之间跳。
   所以这里显式给列数：由**项数**决定，不由宽度决定。
   用法：<div class="screens" style="--cols:3">（6 项 → 3×2，任何宽度都是整行） */
.quad,.screens,.gain{display:grid;grid-template-columns:repeat(var(--cols,2),minmax(0,1fr))}

/* 四宫格：卡片式，不是分隔线 */
.quad{--cols:2;gap:14px;margin-top:26px}
.quad>div{background:var(--paper);border-radius:var(--r-card);padding:22px;box-shadow:var(--sh)}
.quad h4{font-size:13px;font-weight:800;color:var(--ink-3);margin-bottom:14px}
.sw{display:flex;align-items:center;gap:12px;padding:6px 0}
.sw i{width:30px;height:30px;border-radius:10px;flex:none;box-shadow:inset 0 0 0 1px rgba(58,53,48,.1)}
.sw span{font-size:14.5px;font-weight:700}
.sw small{margin-left:auto;font-size:12.5px;color:var(--ink-2);font-weight:700}
.ts{display:flex;align-items:baseline;justify-content:space-between;gap:12px;padding:5px 0}
.ts b{white-space:nowrap}   /* 示例字不许折行：'Aa 数字'断成两行会像坏了 */
.ts small{font-size:12.5px;color:var(--ink-2);font-weight:700}
.rd{display:flex;align-items:center;gap:12px;padding:7px 0;font-size:14.5px;font-weight:700}
.rd i{width:50px;height:28px;background:#EAF1E4;flex:none}
.note{font-size:13.5px;color:var(--ink-2);margin-top:12px;line-height:1.85;font-weight:600}

/* 关键屏：6 屏 → 3 列 × 2 行。列数写在标签上，见文件顶部说明 */
.screens{gap:24px 16px;margin-top:26px}
.screens figure{margin:0}
.screens img{width:100%;border-radius:16px;box-shadow:var(--sh)}
.screens figcaption{margin-top:11px;font-size:13px;line-height:1.7;color:var(--ink-2)}
.screens figcaption b{display:block;color:var(--ink);font-size:14px;margin-bottom:3px;font-weight:800}
.step{display:inline-block;background:var(--clay);color:#fff;border-radius:999px;
  padding:3px 10px;font-size:11px;font-weight:800;margin-bottom:7px}

/* 效益：3 项 → 3 列，窄的时候靠 padding 收缩而不是掉列 */
.gain{--cols:3;gap:14px;margin-top:26px}
.gain>div{background:var(--paper);border-radius:var(--r-card);
  padding:clamp(15px,2.3vw,24px);box-shadow:var(--sh)}
.gain h4{font-size:17.5px;font-weight:800;margin-bottom:10px}
.gain p{font-size:14.5px;line-height:1.9;color:#4A443E}

/* 下一步：绿色数字牌 */
.next{margin-top:24px;display:grid;gap:10px}
.next div{display:grid;grid-template-columns:auto 1fr;gap:16px;align-items:center;
  background:var(--paper);border-radius:var(--r-card);padding:18px 20px;
  box-shadow:var(--sh);font-size:15px;line-height:1.85}
.next b{width:30px;height:30px;border-radius:50%;background:#EAF1E4;color:var(--moss);
  display:grid;place-items:center;font-size:13px;font-weight:800}

.foot{margin-top:46px;padding-top:18px;border-top:1px solid var(--line);
  font-size:13px;font-weight:700;color:var(--ink-3);
  display:flex;justify-content:space-between;gap:14px;flex-wrap:wrap}
"""


def page(title, body):
    return ("<!DOCTYPE html>\n<html lang=\"zh-CN\">\n<head>\n<meta charset=\"UTF-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n"
            f"<title>{title}</title>\n<style>\n{CSS}\n</style>\n</head>\n"
            "<body>\n<div class=\"cv\">\n" + body + "\n</div>\n</body>\n</html>\n")


def head(part):
    return ('<div class="topbar"></div>\n<div class="runhead">'
            f'<span>骑不骑 · 周末骑行决策 App</span><span>{part}</span></div>')


def sec(n, h):
    return (f'<section class="sec"><div class="sec-top"><div class="sn">{n}</div>'
            f'<h2>{h}</h2></div>')


SCREENS = [
    ("第 1 步", "今天适合吗", "打开就回答这一件事：今天能不能骑。天气、体感、一句结论。"),
    ("第 2 步", "你有多少时间", "全程只让他做这一个决定。拖一下滑杆，剩下交给我们。"),
    ("第 3 步", "只给两条路线", "不是十条让他挑。他不知道自己想要什么，我们该帮他选。"),
    ("看一眼", "这一路什么样", "距离、时间、爬升、补给。以及最要紧的：几点能回到起点。"),
    ("出发前", "就检查四样", "时间、体力、带水、能不能按时回。只标出需要注意的那一项。"),
    ("走吧", "11:30 见", "一个开始按钮，一个叫上朋友。骑完自动生成路线卡。"),
]


def part_a():
    b = [head("设计方案 / 上篇")]

    b.append(sec("01", "我们怎么理解这件事"))
    b.append('''<p class="lede">这个 App 服务的是<em>周末偶尔骑一次</em>的城市人，
      不是专业骑手。<br>他们要的不是数据，是"能不能去、去了会不会累、能不能按时回来"
      这三个问题的答案。</p>''')
    b.append('''<p class="body">所以整件事的重心不在功能多，在<b>替他做决定</b>。
      一个一年骑十次的人，打开 App 时最怕的是面对一屏参数、十条路线和一堆专业术语。
      我们要让他五分钟内出门。</p>''')
    b.append('</section>')

    b.append(sec("02", "我们看到的机会"))
    b.append('''<div class="insight"><span class="k">INSIGHT</span>
      <p>市面上的骑行 App 都在服务"已经决定要骑的人"。<br>
      没有人服务"还在犹豫的那个人"。</p></div>''')
    b.append('''<p class="body">功率、配速、心率区间、训练负荷——这些是给备赛的人看的。
      而周末骑车的人打开 App 的那一刻，问题还停留在更前面一步：
      <b>我今天到底要不要出门。</b></p>''')
    b.append('''<p class="body">这一步没人管，所以他往往就不去了。
      把这一步做顺，比把训练数据做深，对这群人有用得多。</p>''')
    b.append('</section>')

    b.append(sec("03", "设计主张"))
    b.append('''<div class="claim">
      <q>只问一件事：<br>你今天有<em>多少时间</em></q>
      <p class="why">其余全部由我们判断。时间是他唯一说得清的约束，
        也是唯一真正决定"骑不骑"的变量。</p></div>''')
    b.append('</section>')

    b.append(sec("04", "视觉语言"))
    b.append('''<p class="body">这是一个让人放松出门的产品，不是一个让人较劲的产品。
      所以整套视觉是<b>自然、温和、圆润</b>的——和运动 App 惯用的黑底荧光正好相反。</p>''')
    b.append('''<dl class="dl">
      <div class="r"><dt>颜色</dt><dd>底色是<b>沙色</b>，一种晒过太阳的米白，
        比纯白暖，配得上林荫道的照片。墨色也不用纯黑，用<b>棕灰</b>。<br>
        两个功能色：<b>橄榄绿</b>说"可以走"，<b>陶土橙</b>说"这里要看一眼"。
        绿多橙少，因为大部分时候答案都是"能去"。</dd></div>
      <div class="r"><dt>字</dt><dd>圆润无衬线，不用任何等宽和窄体。
        字要看起来像在说话，不像在报数。</dd></div>
      <div class="r"><dt>影像</dt><dd>只用一种照片：<b>晨光里的林荫绿道</b>。
        每一屏都是满版实景，文字压在上面。不用插画、不用图标堆砌——
        他要去的地方长什么样，就给他看什么样。</dd></div>
      <div class="r"><dt>形状</dt><dd>处处圆角，阴影柔而深。
        卡片像放在桌面上的实物，不像贴在屏幕上的方块。</dd></div>
    </dl>''')
    b.append('''<div class="quad">
      <div><h4>色板</h4>
        <div class="sw"><i style="background:#FAF8F4"></i><span>沙色</span><small>纸</small></div>
        <div class="sw"><i style="background:#3A3530"></i><span>棕灰</span><small>字</small></div>
        <div class="sw"><i style="background:#6B8E5A"></i><span>橄榄绿</span><small>可以走</small></div>
        <div class="sw"><i style="background:#D9634F"></i><span>陶土橙</span><small>看一眼</small></div>
      </div>
      <div><h4>字</h4>
        <div class="ts"><b style="font-size:13px">Aa 说明</b><small>辅助</small></div>
        <div class="ts"><b style="font-size:15px">Aa 正文</b><small>阅读</small></div>
        <div class="ts"><b style="font-size:25px">Aa 屏标题</b><small>一屏一句</small></div>
        <div class="ts"><b style="font-size:44px">Aa 数字</b><small>还会更大</small></div>
      </div>
      <div><h4>圆角</h4>
        <div class="rd"><i style="border-radius:32px"></i><span>大容器</span></div>
        <div class="rd"><i style="border-radius:20px"></i><span>卡片</span></div>
        <div class="rd"><i style="border-radius:12px"></i><span>控件</span></div>
        <p class="note">没有直角。这个产品不需要任何硬边。</p>
      </div>
      <div><h4>照片怎么放</h4>
        <div class="ts"><b>满版</b><small>铺满整屏</small></div>
        <div class="ts"><b>压一层暗场</b><small>保证字读得出</small></div>
        <div class="ts"><b>文字在最上层</b><small>是真字不是图</small></div>
        <p class="note">照片永远铺满，从不做成浮在页面上的小方块——
          那样四周会有一圈生硬的边。</p>
      </div>
    </div>''')
    b.append('</section>')
    b.append('<div class="foot"><span>骑不骑 · 上篇</span><span>2026</span></div>')
    return page("骑不骑 · 周末骑行决策 App 设计方案（上篇）", "\n".join(b))


def part_b():
    b = [head("设计方案 / 下篇")]

    b.append(sec("05", "他会怎么走完这一趟"))
    b.append('''<p class="body">六屏，从"要不要去"走到"走吧"。
      每一屏只承担一个问题，问完就往下走。</p>''')
    cards = []
    for i, (step, title, desc) in enumerate(SCREENS, 1):
        cards.append(f'<figure><img src="{b64(f"s{i:02d}.jpg")}" alt="{title}">'
                     f'<figcaption><span class="step">{step}</span>'
                     f'<b>{title}</b>{desc}</figcaption></figure>')
    b.append('<div class="screens" style="--cols:3">' + "".join(cards) + '</div>')
    b.append('''<dl class="dl">
      <div class="r"><dt>只问一次</dt><dd>全程只有第 2 屏需要他动手。
        其余五屏他只要往下滑。<b>决定越少，出门越快。</b></dd></div>
      <div class="r"><dt>只给两条</dt><dd>第 3 屏刻意只给两个选项。
        给十条等于把选择的负担丢回给他，而他正是因为不想选才打开这个 App。</dd></div>
      <div class="r"><dt>诚实提醒</dt><dd>第 5 屏四项里，只有"带水"是橙色。
        <b>把该注意的标出来，其余的就别提</b>——全绿等于没有信息。</dd></div>
    </dl>''')
    b.append('</section>')

    b.append(sec("06", "为什么这对你有效"))
    b.append('''<div class="gain">
      <div><h4>打开就有用</h4><p>不需要注册、不需要绑定设备、不需要填偏好。
        第一次打开三十秒内就能拿到一条能去的路线——这是低频用户留下来的唯一机会。</p></div>
      <div><h4>低频也能高频</h4><p>决策成本降下来之后，"这周要不要骑"
        从一个需要下决心的问题变成一个顺手的问题。频次是从这里长出来的。</p></div>
      <div><h4>路线卡会自己传播</h4><p>骑完自动生成一张带实景照片的路线卡。
        它天然适合发出去，而每一张都是一条路线的广告。</p></div>
    </div>''')
    b.append('</section>')

    b.append(sec("07", "下一步"))
    b.append('''<div class="next">
      <div><b>1</b><span>接入真实的天气与路况数据，把"今天适合吗"这句结论算准。</span></div>
      <div><b>2</b><span>补齐首批 20 条城市路线的实景照片与补给点。</span></div>
      <div><b>3</b><span>把骑完的路线卡做成可保存长图，接上分享链路。</span></div>
      <div><b>4</b><span>如果这套走得通，同一逻辑可以复制到跑步和徒步。</span></div>
    </div>''')
    b.append('<p class="body">六屏现在就可以在手机上走一遍，随时可以约一次现场体验。</p>')
    b.append('</section>')
    b.append('<div class="foot"><span>骑不骑 · 下篇</span><span>2026</span></div>')
    return page("骑不骑 · 周末骑行决策 App 设计方案（下篇）", "\n".join(b))


if __name__ == "__main__":
    bad = 0
    for name, fn in {"cycle-canvas-a.html": part_a, "cycle-canvas-b.html": part_b}.items():
        out = fn()
        (BASE / name).write_text(out, encoding="utf-8")
        kb = len(out.encode()) // 1024
        bad += kb >= 460
        print(f"  {'OK ' if kb < 460 else 'BIG'} {name:22} {kb:4d} KB")
    sys.exit(1 if bad else 0)
