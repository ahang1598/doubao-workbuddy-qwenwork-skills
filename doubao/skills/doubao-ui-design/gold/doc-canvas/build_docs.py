#!/usr/bin/env python3
"""生成两份飞书 doc 的窄栏排版画布（html5-block）。

【这份文档是给客户看的，不是工程记录】
读者是甲方的设计负责人 / 市场负责人。他要的是：
看懂你要做什么、凭什么这么做、对他有什么用，然后想约你聊下一步。

所以正文里**没有**：拒绝清单、验收清单、已知边界、状态枚举、
px / hex / 选择器 / 断言 / 门。那些是我们的家务事，留在包里。
数值应该被**看到**（四宫格里的色块与示例字），不该被**读到**（句子里）。

七节结构：
  1 我们怎么理解这件事   用客户自己的话复述，不加术语
  2 我们看到的机会       一条洞察 + 支撑它的观察
  3 设计主张             一句能被复述给老板听的话
  4 视觉语言             感受先行；数值放四宫格
  5 他会怎么走完这一趟   按用户动线，每屏一句"他在这里想干什么"
  6 为什么这对你有效     接回商业目标
  7 下一步               正向推进项，不是"我们还没做完"

参照物在包里：gold/doc-canvas 与 gold/doc-cycle 三份画布共享七节结构、各有各的人格。

物理约束（都是真事故换来的）：
  · 必须是完整 HTML 文档，否则飞书按片段渲染
  · 样式与注释里不得出现结构标签字面量
  · 单块 <= 512KB，图一律 base64 内嵌
  · 布局用 min() / auto-fit，不用断点——飞书块宽在 560~1145px 之间浮动
"""
import base64
import pathlib
import sys

BASE = pathlib.Path(__file__).parent
IMG = BASE / "img"
OUT = BASE


def b64(name: str) -> str:
    return "data:image/jpeg;base64," + base64.b64encode((IMG / name).read_bytes()).decode()


# ── 人格：不是"换个强调色"，是整套换掉 ─────────────────────────
# 自检门会量三份 gold 的色板两两 Jaccard，>0.34 即判"gold 变成模板"。
# 只换 accent 是过不了的——中性色、纸色、分隔线、字体、圆角都得跟着主题走。
PERSONA = {
  # PULSE：白纸编辑体。锋利、有态度、面向年轻消费。
  "pulse": dict(BG="#FFFFFF", INK="#14161A", SUB="#5A6070", LINE="#E3E1DA",
                SOFT="#F6F4EF", ACC="#FF3B14", ACC2="#FFE0D6", ACCINK="#D42E0D",
                FONT='-apple-system,BlinkMacSystemFont,"PingFang SC","Hiragino Sans GB","Microsoft YaHei",system-ui,sans-serif',
                MONO='ui-monospace,SFMono-Regular,"SF Mono",Menlo,monospace',
                RADIUS="3px", RULE="2px solid var(--ink)", HAIR="1px solid var(--line)"),
  # QQ：档案纸。微黄纸底 + 深靛墨 + 双线分隔，像一份翻出来的旧卷宗。
  # 与 PULSE 共享的只有"七节结构"，颜色/纸/线/字全部另起。
  "qq": dict(BG="#F6F2E8", INK="#1B2A4A", SUB="#5B6478", LINE="#D8D0BC",
             SOFT="#EDE7D8", ACC="#12B7F5", ACC2="#CFF0FF", ACCINK="#0E5F80",
             FONT='"Songti SC","Noto Serif CJK SC",-apple-system,"PingFang SC","Microsoft YaHei",serif',
             MONO='"SF Mono",ui-monospace,Menlo,monospace',
             RADIUS="0", RULE="3px double var(--ink)", HAIR="1px solid var(--line)"),
}

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
.cv{
  --ink:%(INK)s; --sub:%(SUB)s; --line:%(LINE)s; --bg:%(BG)s; --soft:%(SOFT)s;
  --acc:%(ACC)s; --acc2:%(ACC2)s; --accink:%(ACCINK)s; --r:%(RADIUS)s;
  /* --accink 是强调色**当文字用**时的那一支。
     QQ 的品牌蓝在纸底上实测 1.87:1，INSIGHT 那行标签整条读不出来。
     强调色做色块可以饱和，做文字必须压深——这是两个不同的角色。 */
  --mono:%(MONO)s;
  width:100%%; max-width:900px; margin:0 auto;
  /* 阅读边距：文字不能贴着块边。飞书块宽 560–1145 浮动，所以用 clamp 跟着走。
     顶部那条色带要满幅，所以它用负 margin 顶出去（见 .topbar）。 */
  --gut:clamp(24px,4.6vw,56px); background:var(--bg); color:var(--ink);
  font-family:%(FONT)s;
  font-size:15px; line-height:1.82; letter-spacing:.005em;
  -webkit-font-smoothing:antialiased; padding:0 var(--gut) 48px;
}
.cv img{display:block;max-width:100%%;height:auto}
.cv b{font-weight:600}
.topbar{height:5px;background:var(--acc);margin:0 calc(var(--gut) * -1) 26px}
.runhead{display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap;
  font:600 11px/1.6 var(--mono);letter-spacing:.22em;color:var(--sub);
  padding-bottom:12px;border-bottom:1px solid var(--line)}
.runhead span:last-child{color:var(--accink)}

.sec{padding-top:58px}
.sec-top{border-top:%(RULE)s;padding-top:20px;
  display:grid;grid-template-columns:auto 1fr;gap:18px;align-items:baseline}
.sn{font:800 30px/1 var(--mono);color:var(--accink);letter-spacing:-.02em}
.sec-top h2{font-size:26px;font-weight:800;line-height:1.25;letter-spacing:-.01em}

.lede{font-size:17px;line-height:2;color:var(--ink);margin-top:24px;max-width:42em}
.lede em{font-style:normal;background:linear-gradient(transparent 62%%,var(--acc2) 62%%);
  padding:0 2px;font-weight:600}
.body{font-size:15.5px;line-height:1.95;margin-top:20px;max-width:42em;color:var(--ink);opacity:.88}

/* 洞察：一段被抬起来的判断 */
.insight{margin-top:28px;padding:26px 28px;background:var(--soft);
  border-left:3px solid var(--acc)}
.insight .k{font:600 11px/1.7 var(--mono);letter-spacing:.2em;color:var(--accink);
  display:block;margin-bottom:10px}
.insight p{font-size:19px;line-height:1.72;font-weight:600;letter-spacing:-.005em}

/* 设计主张：整篇最大的一句话 */
.claim{margin-top:32px;padding:38px 0 32px;border-top:1px solid var(--line);
  border-bottom:1px solid var(--line);text-align:center}
.claim q{quotes:none;display:block;font-size:clamp(30px,4.4vw,44px);font-weight:800;
  line-height:1.26;letter-spacing:-.02em}
.claim q em{font-style:normal;color:var(--accink)}
.claim .why{margin-top:20px;font-size:14.5px;color:var(--sub);line-height:1.9;
  max-width:34em;margin-inline:auto}

/* 通栏版面证据 */
.plate{margin-top:30px}
.plate img{width:100%%;border:1px solid var(--line);border-radius:var(--r)}
.plate .cap{font-size:13.5px;color:var(--sub);margin-top:12px;line-height:1.85;max-width:42em}
.plate .cap b{color:var(--ink)}

/* 双图 */
.duo{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%%,240px),1fr));
  gap:22px 24px;margin-top:28px;align-items:start}
.duo figure{margin:0}
.duo img{border:1px solid var(--line);border-radius:var(--r)}
.duo figcaption{font-size:13px;color:var(--sub);margin-top:10px;line-height:1.8}
.duo figcaption b{display:block;color:var(--ink);font-size:14px;margin-bottom:4px}

/* 左标签右正文 */
.dl{margin-top:26px}
.dl .r{display:grid;grid-template-columns:minmax(86px,104px) 1fr;gap:14px 20px;
  padding:18px 0;border-top:1px solid var(--line);align-items:baseline}
.dl .r:last-child{border-bottom:1px solid var(--line)}
.dl dt{font:600 11px/1.7 var(--mono);letter-spacing:.14em;color:var(--accink)}
.dl dd{font-size:15px;line-height:1.92}

/* ── 列数必须整除项数，否则会出现"孤儿行"（3+1 / 5+1），整版立刻显乱 ──
   auto-fit 的列数随宽度浮动，控制不住；飞书块宽又在 560–1145 之间跳。
   所以这里显式给列数：由**项数**决定，不由宽度决定。
   用法：<div class="screens" style="--cols:3">（6 项 → 3×2，任何宽度都是整行） */
.quad,.screens,.gain{display:grid;grid-template-columns:repeat(var(--cols,2),minmax(0,1fr))}

/* 四宫格：数值要被看到，不要被读到。4 项 → 2 列 */
.quad{--cols:2;gap:0 38px;margin-top:30px;border-top:1px solid var(--line)}
.quad>div{padding:24px 22px 24px 0;border-bottom:1px solid var(--line)}
.quad h4{font:600 11px/1.7 var(--mono);letter-spacing:.18em;color:var(--sub);margin-bottom:15px}
.sw{display:flex;align-items:center;gap:12px;padding:7px 0}
.sw i{width:26px;height:26px;border-radius:50%%;flex:none;box-shadow:inset 0 0 0 1px rgba(0,0,0,.12)}
.sw span{font-size:14px}
.sw small{margin-left:auto;font-size:12px;color:var(--sub)}
.ts{display:flex;align-items:baseline;justify-content:space-between;gap:12px;padding:6px 0}
.ts b{white-space:nowrap}
.ts b{font-weight:600}
.ts small{font-size:12px;color:var(--sub)}
.rd{display:flex;align-items:center;gap:12px;padding:7px 0;font-size:14px}
.rd i{width:52px;height:26px;background:var(--soft);border:1px solid var(--line);flex:none}
.note{font-size:13px;color:var(--sub);margin-top:12px;line-height:1.85}

/* 关键屏网格：列数由项数决定，写在标签上 */
.screens{gap:22px 14px;margin-top:26px}
.screens figure{margin:0}
.screens img{width:100%%;border-radius:var(--r);border:1px solid var(--line);background:var(--soft)}
.screens figcaption{margin-top:9px;font-size:12.5px;line-height:1.7;color:var(--sub)}
.screens figcaption b{display:block;color:var(--ink);font-size:13px;margin-bottom:2px}
.flowtag{font:600 10.5px/1 var(--mono);letter-spacing:.16em;color:var(--accink);
  display:block;margin-bottom:5px}

/* 效益：3 项 → 3 列 */
.gain{--cols:3;gap:0 clamp(18px,3vw,34px);margin-top:28px;border-top:1px solid var(--line)}
.gain>div{padding:26px 20px 26px 0;border-bottom:1px solid var(--line)}
.gain h4{font-size:17px;font-weight:700;margin-bottom:10px;letter-spacing:-.01em}
.gain p{font-size:14.5px;line-height:1.92;color:var(--ink);opacity:.88}

/* 下一步 */
.next{margin-top:26px}
.next div{display:grid;grid-template-columns:auto 1fr;gap:16px;align-items:baseline;
  padding:17px 0;border-top:1px solid var(--line);font-size:15px;line-height:1.88}
.next div:last-child{border-bottom:1px solid var(--line)}
.next b{font:600 11px/1.7 var(--mono);letter-spacing:.14em;color:var(--accink)}

.foot{margin-top:48px;padding-top:16px;border-top:1px solid var(--line);
  font:400 11px/1.8 var(--mono);letter-spacing:.1em;color:var(--sub);
  display:flex;justify-content:space-between;gap:14px;flex-wrap:wrap}
"""


def page(title, who, body):
    return ("<!DOCTYPE html>\n<html lang=\"zh-CN\">\n<head>\n<meta charset=\"UTF-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n"
            f"<title>{title}</title>\n<style>\n{CSS % PERSONA[who]}\n</style>\n"
            "</head>\n<body>\n<div class=\"cv\">\n" + body + "\n</div>\n</body>\n</html>\n")


def head(project, part):
    return (f'<div class="topbar"></div>\n<div class="runhead">'
            f'<span>{project}</span><span>{part}</span></div>')


def sec(n, h):
    return (f'<section class="sec"><div class="sec-top"><div class="sn">{n}</div>'
            f'<h2>{h}</h2></div>')


# ══════════════════════════════════════════════════════ PULSE · 上篇
def pulse_a():
    b = [head("PULSE 脉冲运动 · 品牌官网", "设计方案 / 上篇")]

    b.append(sec("01", "我们怎么理解这件事"))
    b.append('''<p class="lede">你要一个 00 后运动品牌的官网，能在站内直接买，
      气质对标 lululemon，但要更年轻。<br>
      我们把它翻译成一句话：<em>这个官网要让一个 22 岁的人愿意截图发出去，然后顺手买一件。</em></p>''')
    b.append('''<p class="body">这两件事必须同时成立，而且有先后——
      它得先像个牌子，才谈得上成交。所以这一版的重心不在功能，在气质。
      购买链路我们会做得干净利落，但那不是这份方案要说服你的地方。</p>''')
    b.append('</section>')

    b.append(sec("02", "我们看到的机会"))
    b.append('''<div class="insight"><span class="k">INSIGHT</span>
      <p>技术面料已经不是壁垒了，态度才是。<br>
      有人把它做成了体面，还没有人把它做成有声音。</p></div>''')
    b.append('''<p class="body">lululemon 花了二十年，把运动服带进了写字楼。
      那套视觉语言是安静的、克制的、体面的——它服务的是一群需要"看起来专业"的人。</p>''')
    b.append('''<p class="body">但 00 后的运动不发生在写字楼。发生在深夜的球场、地铁口、
      23:40 还亮着的便利店。同样的四向弹力面料，可以装进两种完全不同的气质里，
      卖给两代人。<b>中间那个位置现在是空的。</b></p>''')
    b.append(f'''<div class="duo">
      <figure><img src="{b64('web-look.jpg')}" alt="现场强色光影像">
        <figcaption><b>他们的运动长这样</b>不是晨跑和普拉提，是霓虹、球场、滑板，
          和随手一拍。</figcaption></figure>
      <figure><img src="{b64('web-band.jpg')}" alt="品牌主张段">
        <figcaption><b>所以品牌也该长这样</b>敢直接说出自己不是谁，
          比反复说自己是谁更有效。</figcaption></figure>
    </div>''')
    b.append('</section>')

    b.append(sec("03", "设计主张"))
    b.append('''<div class="claim">
      <q>先动起来<br><em>再谈风格</em></q>
      <p class="why">先给态度，再给货。首屏不介绍产品，只回答一件事：这是谁的牌子。
        这句话既是官网的开场白，也可以直接搬去门店橱窗、包装和短片。</p></div>''')
    b.append('</section>')

    b.append(sec("04", "视觉语言"))
    b.append('''<p class="body">四组决定，构成这个品牌看起来的样子。
      我们尽量用感受来说明，具体数值排在下面，看一眼就够。</p>''')
    b.append('''<dl class="dl">
      <div class="r"><dt>颜色</dt><dd>底子是<b>骨色</b>——一种带温度的米，不是纯白。
        纯白会把照片衬得廉价，骨色会把它衬得像印刷品。<br>
        全站只有一个彩色：<b>信号橙红</b>。它不做装饰，只做路标——
        出现在哪里，就意味着"该往这儿走"。</dd></div>
      <div class="r"><dt>字</dt><dd>中文用<b>重量</b>说话，拉丁文用<b>宽度</b>说话。
        标题压得很窄很重，正文放松下来。两者之间的落差本身就是态度，
        不需要再加装饰线和图标。</dd></div>
      <div class="r"><dt>影像</dt><dd>只允许两种照片：<b>影棚白底的全身</b>用来卖货，
        <b>现场强色光</b>用来立人设。中间态一律不用——
        混着放会让整个网站看起来像图库拼盘，这是最容易掉价的地方。</dd></div>
      <div class="r"><dt>形状</dt><dd>版面和图片都是直角，<b>只有能点的东西是圆的</b>。
        这条规则顺带省掉了一整套"这里能不能点"的说明。</dd></div>
    </dl>''')
    b.append('''<div class="quad">
      <div><h4>色板</h4>
        <div class="sw"><i style="background:#EFECE3"></i><span>骨色</span><small>画布</small></div>
        <div class="sw"><i style="background:#14140F"></i><span>墨色</span><small>文字与深场</small></div>
        <div class="sw"><i style="background:#FF3B14"></i><span>信号橙红</span><small>唯一路标</small></div>
        <div class="sw"><i style="background:#C9F24D"></i><span>荧光青柠</span><small>限量标签</small></div>
      </div>
      <div><h4>字阶</h4>
        <div class="ts"><b style="font-size:12px">Aa 标签</b><small>最小</small></div>
        <div class="ts"><b style="font-size:15px">Aa 正文</b><small>阅读</small></div>
        <div class="ts"><b style="font-size:26px">Aa 小节</b><small>分段</small></div>
        <div class="ts"><b style="font-size:44px">Aa 大标题</b><small>首屏更大</small></div>
      </div>
      <div><h4>形状</h4>
        <div class="rd"><i style="border-radius:0"></i><span>版面与图片</span></div>
        <div class="rd"><i style="border-radius:6px"></i><span>尺码按钮</span></div>
        <div class="rd"><i style="border-radius:999px"></i><span>胶囊按钮</span></div>
        <p class="note">只有可点的东西才是圆的。</p>
      </div>
      <div><h4>疏密</h4>
        <div class="ts"><b>商品之间</b><small>只留一线</small></div>
        <div class="ts"><b>版块之间</b><small>大留白</small></div>
        <div class="ts"><b>商品照片</b><small>统一竖构图</small></div>
        <p class="note">八张同场拍摄的照片挨得足够近，会连成一张接触印相，
          而不是散成八张卡片。</p>
      </div>
    </div>''')
    b.append('</section>')
    b.append('<div class="foot"><span>PULSE · 上篇</span><span>2026</span></div>')
    return page("PULSE 脉冲 · 品牌官网设计方案（上篇）", "pulse", "\n".join(b))


# ══════════════════════════════════════════════════════ PULSE · 下篇
def pulse_b():
    b = [head("PULSE 脉冲运动 · 品牌官网", "设计方案 / 下篇")]

    b.append(sec("05", "他会怎么走完这一趟"))
    b.append('''<p class="body">从打开首页到下单，一共六个版面。
      每一段我们都先想清楚"他在这里想干什么"，再决定放什么。</p>''')
    b.append(f'''<div class="plate"><img src="{b64('web-hero.jpg')}" alt="首屏">
      <div class="cap"><b>他刚点进来，还不确定这是谁。</b>
        所以整块画面让给一张照片，标题压在人身上，只留一个按钮。
        这一屏不解释面料、不列参数，只让他判断"这是不是我的牌子"。</div></div>''')
    b.append(f'''<div class="plate"><img src="{b64('web-shop.jpg')}" alt="商品网格">
      <div class="cap"><b>他认了，开始想看看有什么。</b>
        八件单品用同一场影棚照片连成一片，缝隙只留一线。
        鼠标停下来才浮出尺码——先让他看造型，别一上来就让他做选择题。</div></div>''')
    b.append(f'''<div class="duo">
      <figure><img src="{b64('web-tech.jpg')}" alt="面料">
        <figcaption><b>他动心了，开始找理由。</b>三块面料、三个能验证的说法：
          多重、多快导汗、夜里多远能被看见。给他一个可以转述给别人的理由。</figcaption></figure>
      <figure><img src="{b64('web-join.jpg')}" alt="会员">
        <figcaption><b>他买完了，我们希望他再来。</b>整块信号橙红收尾，
          全站唯一一次大面积用色，压在最后一个转化点上。</figcaption></figure>
    </div>''')
    b.append('''<p class="body">购买本身做得很直接：<b>选码 → 加袋 → 改数量 → 结账</b>，
      全程不跳页、不强制注册。满额免运费的提示出现在他改数量的那一刻，
      而不是等到结账页才告诉他。</p>''')
    b.append('</section>')

    b.append(sec("06", "为什么这对你有效"))
    b.append('''<div class="gain">
      <div><h4>成交路径更短</h4><p>从"认了这个牌子"到"加进购物袋"只隔一屏。
        我们把说服放在首屏，把决策放在第二屏，中间不插入任何需要阅读的内容。</p></div>
      <div><h4>资产可以复用</h4><p>首屏那句话和那个橙色不只属于网站。
        它们可以直接搬到门店橱窗、包装、短片和联名物料上——一次设计，多处使用。</p></div>
      <div><h4>复购有抓手</h4><p>城市训练队是一个不花预算的复购引擎：
        每周三固定夜跑，跑完在便利店门口拍合照。
        它同时解决了内容素材和到店理由。</p></div>
    </div>''')
    b.append(f'''<div class="plate"><img src="{b64('web-look.jpg')}" alt="系列大片">
      <div class="cap">同一批影像可以横跨官网、社媒和门店，不需要为每个渠道重拍。</div></div>''')
    b.append('</section>')

    b.append(sec("07", "下一步"))
    b.append('''<div class="next">
      <div><b>01</b><span>换上品牌自有大片——现在这版用的是同调性的参考影像，
        正式拍摄时我们提供分镜与造型清单。</span></div>
      <div><b>02</b><span>接入支付与库存，把这套购买链路连到你的后台。</span></div>
      <div><b>03</b><span>把首屏那句话延展成一支 15 秒短片，用于投放与门店循环。</span></div>
      <div><b>04</b><span>排定城市训练队的首季日程与内容节奏。</span></div>
    </div>''')
    b.append('''<p class="body">整站现在就可以打开走一遍，
      也可以先只落地首屏做一次内部验证。</p>''')
    b.append('</section>')
    b.append('<div class="foot"><span>PULSE · 下篇</span><span>2026</span></div>')
    return page("PULSE 脉冲 · 品牌官网设计方案（下篇）", "pulse", "\n".join(b))


SCREENS = [
    ("开场", "屏 1 · 开机", "扫描线扫过、日志逐行打印、拨号进度条走满"),
    ("陪伴", "屏 2 · 在线天数", "整年的日历铺成底纹，亮着的是他在线的日子"),
    ("陪伴", "屏 3 · 消息总数", "巨大的数字，下面是他今年被撤回最多的三句话"),
    ("私密", "屏 4 · 深夜时刻", "把时段分布装进一台旧电脑的窗口里"),
    ("私密", "屏 5 · 年度挚友", "整屏只有一个人的头像和一个数字"),
    ("社交", "屏 6 · 群聊江湖", "四十八个方块，亮着的是他说过话的群"),
    ("社交", "屏 7 · 空间", "三个数字并排，下面是老式的访客名单"),
    ("社交", "屏 8 · 关键词", "从聊天里掉出来的词，字越大说得越多"),
    ("身份", "屏 9 · 年度形象", "一块属性面板，给他一个可以炫耀的称号"),
    ("分享", "屏 10 · 结束页", "把前面九屏压成一张卡片，两个动作：存图、发给朋友"),
]


# ══════════════════════════════════════════════════════ QQ · 上篇
def qq_a():
    b = [head("QQ 2026 年度盘点报告", "设计方案 / 上篇")]

    b.append(sec("01", "我们怎么理解这件事"))
    b.append('''<p class="lede">十屏年度盘点，中间八屏讲数据，最后一屏要能让人愿意发出去。
      你还给了一个前提：今年可以换个风格，走复古。<br>
      我们把它翻译成一句话：<em>这一版的目标不是把数据讲清楚，是让人愿意把它转出去。</em></p>''')
    b.append('''<p class="body">数据讲清楚是及格线。真正决定它成不成的，
      是他看完最后一屏时会不会想截图。所以我们把大部分精力放在
      "怎么让每一屏都值得被看见"，而不是"怎么把每个数字标注清楚"。</p>''')
    b.append('</section>')

    b.append(sec("02", "我们看到的机会"))
    b.append('''<div class="insight"><span class="k">INSIGHT</span>
      <p>往期的问题不是不好看，<br>是每年都好看成同一个样子。</p></div>''')
    b.append('''<p class="body">我们看了往期四版，也看了同期几家平台的年度报告。
      它们几乎共用一套语言：柔和的水彩插画、轻盈的细体字、一个居中的大数字。
      单看都好看，放在一起就分不出谁是谁。</p>''')
    b.append('''<p class="body">而 QQ 手里有一样别家拿不到的东西：<b>它自己的历史。</b>
      像素企鹅、蓝色标题栏的对话框、显像管的扫描线、月亮和星星的等级图标——
      这些不是怀旧素材，是<b>只有 QQ 能用的品牌资产</b>。
      别人复制不了，因为别人没有过那段时间。</p>''')
    b.append('</section>')

    b.append(sec("03", "设计主张"))
    b.append('''<div class="claim">
      <q>把这一年<br>装进一台<em>旧机器</em></q>
      <p class="why">整份报告是一台 2003 年的电脑在回放他这一年。
        开机、读盘、逐屏显示——连等待都是内容的一部分。</p></div>''')
    b.append('</section>')

    b.append(sec("04", "视觉语言"))
    b.append('''<p class="body">"复古"如果只是加一层噪点滤镜，等于没换。
      我们把它落到四件能被一眼指认的东西上。</p>''')
    b.append('''<dl class="dl">
      <div class="r"><dt>像素企鹅</dt><dd>用点阵重新画的企鹅，
        放多大都不糊，换颜色不用重画。它贯穿全程，是这台机器的主人。</dd></div>
      <div class="r"><dt>旧对话框</dt><dd>蓝色渐变的标题栏、右上角三个小方块、
        外凸的边框。放数据图表和好友名单的地方，都装在这样一个窗口里。</dd></div>
      <div class="r"><dt>显像管质感</dt><dd>每隔几像素一条暗线，四角压暗。
        它铺在全部十屏上，是把十种颜色统一起来的那一层。</dd></div>
      <div class="r"><dt>月亮与星星</dt><dd>QQ 的等级图标。只有老用户看得懂，
        而这正是它的价值——它是一句对老用户说的暗号。</dd></div>
    </dl>''')
    b.append('''<div class="quad">
      <div><h4>色板</h4>
        <div class="sw"><i style="background:#071A3A"></i><span>夜靛</span><small>底色起点</small></div>
        <div class="sw"><i style="background:#12B7F5"></i><span>QQ 蓝</span><small>品牌锚</small></div>
        <div class="sw"><i style="background:#FFC93C"></i><span>像素黄</span><small>结束页</small></div>
        <div class="sw"><i style="background:#FF4D4D"></i><span>企鹅红</span><small>围巾与红钻</small></div>
      </div>
      <div><h4>十屏十色</h4>
        <div class="sw"><i style="background:linear-gradient(90deg,#0E2E63,#57D6FF)"></i><span>封面 · 夜</span></div>
        <div class="sw"><i style="background:linear-gradient(90deg,#2A1C63,#9B7BFF)"></i><span>深夜 · 紫</span></div>
        <div class="sw"><i style="background:linear-gradient(90deg,#5A1740,#FF6FA5)"></i><span>挚友 · 玫</span></div>
        <div class="sw"><i style="background:linear-gradient(90deg,#123064,#FFC93C)"></i><span>分享 · 金</span></div>
        <p class="note">每屏换一次颜色，但底纹和扫描线始终是同一层——换色不换人格。</p>
      </div>
      <div><h4>字</h4>
        <div class="ts"><b style="font-size:12px">Aa 眉标</b><small>最小</small></div>
        <div class="ts"><b style="font-size:15px">Aa 一句话</b><small>正文</small></div>
        <div class="ts"><b style="font-size:28px">Aa 屏标题</b><small>一屏一句</small></div>
        <div class="ts"><b style="font-size:46px">Aa 数字</b><small>还会更大</small></div>
      </div>
      <div><h4>节奏</h4>
        <div class="ts"><b>一屏</b><small>一件事</small></div>
        <div class="ts"><b>翻页</b><small>滑动 / 点按钮 / 点画面</small></div>
        <div class="ts"><b>动效</b><small>进屏才播</small></div>
        <p class="note">数字从零滚上来，进度条从零长出来——
          他看到的是"正在算给他看"，而不是一张已经算好的表。</p>
      </div>
    </div>''')
    b.append('</section>')
    b.append('<div class="foot"><span>QQ 2026 · 上篇</span><span>2026</span></div>')
    return page("QQ 2026 年度盘点 · 设计方案（上篇）", "qq", "\n".join(b))


# ══════════════════════════════════════════════════════ QQ · 下篇
def qq_b():
    b = [head("QQ 2026 年度盘点报告", "设计方案 / 下篇")]

    b.append(sec("05", "他会怎么走完这十屏"))
    b.append('''<p class="body">一条完整的情绪曲线：先给体量，再往私密走，
      然后扩展到社交关系，最后落到一个他愿意说出口的身份。</p>''')
    cards = []
    for i, (flow, title, desc) in enumerate(SCREENS, 1):
        cards.append(
            f'<figure><img src="{b64(f"qq-p{i:02d}.jpg")}" alt="{title}">'
            f'<figcaption><span class="flowtag">{flow}</span><b>{title}</b>{desc}</figcaption></figure>')
    b.append('<div class="screens" style="--cols:5">' + "".join(cards) + '</div>')
    b.append('''<dl class="dl">
      <div class="r"><dt>开场</dt><dd>第一屏不直接给标题，先放一段开机。
        <b>把等待做成内容</b>——这两秒建立的是"这是一台旧机器"的前提，
        后面九屏才成立。</dd></div>
      <div class="r"><dt>中段</dt><dd>从"今年在线多久"走到"最晚聊到几点"，
        再走到"最常聊的是谁"。<b>越往后越私密</b>，
        因为越私密的东西越值得被记住。</dd></div>
      <div class="r"><dt>收尾</dt><dd>最后一屏不给数据摘要，给一个<b>称号</b>。
        人不会转发自己的统计表，但会转发自己的身份标签。</dd></div>
    </dl>''')
    b.append('</section>')

    b.append(sec("06", "为什么这对你有效"))
    b.append('''<div class="gain">
      <div><h4>更愿意转发</h4><p>结束页给的是"深夜话痨侠"这样一个称号，
        而不是一张数据卡。它下面还有一句"全站只有 3.6% 的人拿到"——
        稀缺性是转发的第二推力。</p></div>
      <div><h4>唤醒老用户</h4><p>月亮星星、旧对话框、像素企鹅，
        只有用过那个年代 QQ 的人看得懂。对他们，这不是一份报告，
        是一次"你还记得吗"。</p></div>
      <div><h4>别家抄不走</h4><p>插画风格可以被复制，历史不能。
        这套视觉语言天然只属于 QQ，用得越多，品牌资产越厚。</p></div>
    </div>''')
    b.append('</section>')

    b.append(sec("07", "下一步"))
    b.append('''<div class="next">
      <div><b>01</b><span>接入真实数据，我们同步调整文案里所有的具体说法。</span></div>
      <div><b>02</b><span>把结束页的卡片做成可保存的长图，配合分享链路一起上线。</span></div>
      <div><b>03</b><span>为像素企鹅做一套表情与动作，用于后续活动复用。</span></div>
      <div><b>04</b><span>如果反响好，这套语言可以延伸到会员页和节日活动。</span></div>
    </div>''')
    b.append('<p class="body">十屏现在就可以在手机上试玩，随时可以约一次现场走查。</p>')
    b.append('</section>')
    b.append('<div class="foot"><span>QQ 2026 · 下篇</span><span>2026</span></div>')
    return page("QQ 2026 年度盘点 · 设计方案（下篇）", "qq", "\n".join(b))


BUILDERS = {
    "pulse-canvas-a.html": pulse_a, "pulse-canvas-b.html": pulse_b,
    "qq-canvas-a.html": qq_a, "qq-canvas-b.html": qq_b,
}

if __name__ == "__main__":
    bad = 0
    for name, fn in BUILDERS.items():
        out = fn()
        (OUT / name).write_text(out, encoding="utf-8")
        kb = len(out.encode()) // 1024
        bad += kb >= 460
        print(f"  {'OK ' if kb < 460 else 'BIG'} {name:22} {kb:4d} KB")
    sys.exit(1 if bad else 0)
