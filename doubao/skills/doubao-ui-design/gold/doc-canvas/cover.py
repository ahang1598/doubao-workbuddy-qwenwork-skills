#!/usr/bin/env python3
"""文档封面：16:9 满版，版式由内容决定。

机制来自老包 `canvas_scaffold.doc_cover_html()`——那是老包唯一做对的东西。
搬过来时换了形态：老包是 Python 里的 f-string 大字符串（又一份字面 CSS），
这里是**可编辑的模板**，三个 variant 只是起点，不是全集。

三种版式怎么选（由内容定，不是随机、不是 hash）：
  interface-archive  App / 小程序 / 多屏产物 —— 主图是竖屏界面，用画框陈列
  editorial-object   主素材是竖图（产品、人物立像）—— 左字右物，像杂志封面
  cinematic-field    主素材是横图（场景、大片）—— 满版压字

边界：版式可复用，**视觉不可复用**。配色/字体/网格密度由本稿的设计语言决定，
两份不同项目的封面版式可以同，颜色和气质必须不同。
"""
from __future__ import annotations

import html
from pathlib import Path

TPL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>{subject} · 封面</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:100%;height:100%;overflow:hidden;background:{canvas}}}
body{{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Hiragino Sans GB",
  "Microsoft YaHei",system-ui,sans-serif;color:{ink}}}
.cover{{position:relative;width:100vw;height:100vh;min-height:540px;overflow:hidden;
  isolation:isolate;background:{canvas};
  /* 12 列网格底纹 + 一处强调色光晕：整份文档的"纸" */
  background-image:
    linear-gradient(90deg,{grid} 1px,transparent 1px),
    radial-gradient(circle at {glowx} {glowy},{glow},transparent 42%);
  background-size:8.3333% 100%,100% 100%;}}
/* 巨号编号水印：先于一切被看到，也最先被忘掉 —— 它只提供"这是一份正经方案"的信号 */
.folio{{position:absolute;right:-2.5vw;bottom:-9vh;z-index:0;
  font-size:clamp(240px,30vw,460px);font-weight:900;line-height:.72;
  letter-spacing:-.08em;color:{folio_ink};user-select:none}}
.meta{{position:absolute;z-index:3;font-size:11px;letter-spacing:.28em;
  font-weight:600;color:{meta_ink};text-transform:uppercase}}
.meta.tl{{top:5.4vh;left:4.6vw}}
.meta.bl{{bottom:5.4vh;left:4.6vw;display:flex;gap:2.2vw;letter-spacing:.2em}}
.meta.br{{bottom:5.4vh;right:4.6vw;letter-spacing:.2em}}
.side{{position:absolute;z-index:3;right:1.9vw;top:50%;transform:translateY(-50%) rotate(180deg);
  writing-mode:vertical-rl;font-size:10.5px;letter-spacing:.42em;color:{meta_ink};font-weight:600}}
.stage{{position:absolute;inset:0;z-index:2;display:grid;align-items:center;
  padding:0 4.6vw;gap:4vw}}
.title{{font-size:clamp(40px,5.6vw,86px);font-weight:800;line-height:1.06;
  letter-spacing:-.022em;max-width:15ch}}
.title em{{font-style:normal;color:{accent}}}
.rule{{width:min(38vw,420px);height:2px;background:{ink};margin:3.4vh 0 2.6vh;opacity:.9}}
.sub{{font-size:clamp(13px,1.15vw,17px);line-height:1.85;color:{sub_ink};max-width:32ch}}
.art{{position:relative;overflow:hidden;background:{art_bg}}}
.art img{{width:100%;height:100%;object-fit:cover;display:block}}

/* ── 版式 A：cinematic-field —— 横图满版，字压在上面 ── */
.v-cinematic .stage{{grid-template-columns:1fr;align-content:end;padding-bottom:11vh}}
.v-cinematic .art{{position:absolute;inset:0;z-index:-1}}
.v-cinematic .art::after{{content:"";position:absolute;inset:0;
  background:linear-gradient(75deg,{scrim} 8%,{scrim_soft} 52%,transparent 88%)}}
.v-cinematic .title,.v-cinematic .sub{{color:{on_art}}}
.v-cinematic .rule{{background:{on_art}}}
.v-cinematic .meta,.v-cinematic .side{{color:{on_art};opacity:.72}}
.v-cinematic .folio{{color:{on_art};opacity:.10}}

/* ── 版式 B：editorial-object —— 左字右物，像杂志封面 ── */
.v-editorial .stage{{grid-template-columns:1.06fr .94fr}}
.v-editorial .art{{height:74vh;align-self:center;border-radius:2px}}

/* ── 版式 C：interface-archive —— 界面陈列，给 App / 多屏产物 ── */
.v-archive .stage{{grid-template-columns:1.02fr .98fr}}
.v-archive .shelf{{position:relative;height:76vh;align-self:center;
  background:{shelf};display:flex;align-items:center;justify-content:center;
  border-radius:2px}}
.v-archive .shelf::before{{content:"";position:absolute;width:66%;aspect-ratio:1;
  border:1px solid {shelf_line};border-radius:50%}}
.v-archive .phone{{position:relative;z-index:2;height:62vh;aspect-ratio:390/844;
  border-radius:14px;overflow:hidden;background:#0B0F1C;
  box-shadow:0 22px 60px rgba(0,0,0,.28),0 0 0 6px {shelf_bezel}}}
.v-archive .phone img{{width:100%;height:100%;object-fit:cover}}
</style>
</head>
<body>
<div class="cover {variant_class}">
  <div class="folio">{folio}</div>
  <div class="meta tl">{kicker}</div>
  <div class="side">{side}</div>
  {art_block}
  <div class="stage">
    <div>
      <h1 class="title">{title_html}</h1>
      <div class="rule"></div>
      <p class="sub">{sub}</p>
    </div>
    {right_block}
  </div>
  <div class="meta bl">{meta_bl}</div>
  <div class="meta br">{meta_br}</div>
</div>
</body>
</html>
"""


def build(variant: str, *, subject: str, title_html: str, sub: str, kicker: str,
          side: str, folio: str, meta_bl: str, meta_br: str, img_src: str,
          palette: dict) -> str:
    """variant: cinematic | editorial | archive"""
    p = dict(palette)
    art_img = (f'<img src="{html.escape(img_src, quote=True)}" '
               f'alt="{html.escape(subject, quote=True)} 主视觉">') if img_src else ""
    if variant == "cinematic":
        art_block, right_block = f'<div class="art">{art_img}</div>', ""
    elif variant == "archive":
        art_block = ""
        right_block = f'<div class="shelf"><div class="phone">{art_img}</div></div>'
    else:
        art_block, right_block = "", f'<div class="art">{art_img}</div>'
    return TPL.format(
        subject=html.escape(subject), title_html=title_html, sub=sub,
        kicker=kicker, side=side, folio=folio, meta_bl=meta_bl, meta_br=meta_br,
        variant_class="v-" + variant, art_block=art_block, right_block=right_block,
        **p)


PALETTE_PULSE = dict(
    canvas="#EFECE3", ink="#14140F", accent="#FF3B14", sub_ink="rgba(20,20,15,.62)",
    meta_ink="rgba(20,20,15,.5)", folio_ink="rgba(20,20,15,.05)",
    grid="rgba(20,20,15,.05)", glow="rgba(255,59,20,.14)", glowx="78%", glowy="16%",
    art_bg="#141410", scrim="rgba(10,10,8,.86)", scrim_soft="rgba(10,10,8,.42)",
    on_art="#F6F3EC", shelf="#E4E0D4", shelf_line="rgba(20,20,15,.16)",
    shelf_bezel="#14140F",
)

PALETTE_QQ = dict(
    canvas="#0A1226", ink="#F3EEE1", accent="#FFC93C", sub_ink="rgba(243,238,225,.6)",
    meta_ink="rgba(243,238,225,.46)", folio_ink="rgba(243,238,225,.055)",
    grid="rgba(243,238,225,.045)", glow="rgba(18,183,245,.2)", glowx="24%", glowy="18%",
    art_bg="#050A16", scrim="rgba(5,8,20,.88)", scrim_soft="rgba(5,8,20,.4)",
    on_art="#F3EEE1", shelf="#101B36", shelf_line="rgba(87,214,255,.2)",
    shelf_bezel="#1B2440",
)

COVERS = {
    "pulse-cover.html": dict(
        variant="cinematic", subject="PULSE 脉冲",
        title_html="先动起来<br><em>再谈风格</em>",
        sub="为 18–26 岁的身体做训练服。<br>一个 00 后会自己转发的运动品牌官网。",
        kicker="DESIGN PROPOSAL / 01",
        side="PULSE · SS26 · 城市训练系列",
        folio="26", meta_bl="品牌官网 · 宽屏 · 可下单", meta_br="脉冲运动 PULSE",
        img_src="../web-pulse/assets/hero.jpg", palette=PALETTE_PULSE),
    "qq-cover.html": dict(
        variant="archive", subject="QQ 2026 年度报告",
        title_html="把这一年<br>装进一台<br><em>旧机器</em>",
        sub="QQ 2026 年度盘点报告。<br>十屏竖版，复古风。",
        kicker="DESIGN PROPOSAL / 01",
        side="QQ · ANNUAL REPORT · 2026",
        folio="26", meta_bl="移动端 H5 · 10 屏 · 可分享", meta_br="腾讯 QQ",
        img_src="../h5-qq2026/cover-shot.jpg", palette=PALETTE_QQ),
}

if __name__ == "__main__":
    here = Path(__file__).parent
    for name, kw in COVERS.items():
        (here / name).write_text(build(**kw), encoding="utf-8")
        print(f"  {name}  variant={kw['variant']}")
