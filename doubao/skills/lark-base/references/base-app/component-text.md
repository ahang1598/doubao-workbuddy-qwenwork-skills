---
name: app-component-text
description: App 富文本的默认尺寸、双行标题、局部样式和增量保留。
---

# 富文本 text

无数据源，data_config.text为Markdown，create可省略得到空文本。承担标题时首行**必须**用Markdown井号语法形成标题层级：页面标题`# `、区块标题`## `（井号后一个空格），下一行非空普通正文，不另造分节；仅标题、无正文也必须带`#`。大字号、加粗或text_styles只改视觉、不形成标题层级，不能用来代替井号；用户原样、仅正文或其它格式明确优先时不加。组件名称不代替正文，换行用`\n`，不用`<br/>`。

## 尺寸与页面标题

默认容器宽×内容高，推荐W12～48、H3～5。最终流式整行时显式height=auto，即使短正文；exact/用户明确合法高度或模式优先。同其它类型同行时共同固定高须能完整展示。**T型顶部始终auto**，exact.h只是预留，不覆盖该专属要求。页面级说明置业务内容前；区块/页尾按所在区，不套页面标题。

页面级通栏标题显式用 `width=fixed、height=auto`，根布局设 `x=0,y=0,w=48,h=3`。fixed 保留的是画布标准宽度，随画布换算渲染尺寸，不锁死屏幕像素；fill 会重新分配剩余宽度，不表示独占整行。用户明确指定其它合法宽度或宽度模式时保留其要求；已有局部修改不改未点名标题，区块文本不套通栏默认。

auto 不表示预留高度或重叠可以忽略。后续根组件初始从 `y≥3` 开始，实际标题变高后仍须核对下方组件避让；原生回读 `1494×78` 不可原样回写，否则高度78会再次放大。若标题宽度收缩、高度异常或邻居侵入标题行，连同受影响邻居修复并重读 position 与 size_mode，不以刚写完的满宽坐标代替模式验收。单位与校验见 [布局输入与回读单位](app-block-config.md#布局输入与回读单位)。

页面标题最多显示1行，副文案默认1行、最多2行；按真实宽度精简自拟文案，用户原文不擅自删改，超行则报告裁切/换行缺口。现有auto高度不等于满足行数限制，需实际渲染证据；不编max_lines或截断参数。

承担页面标题时首行H1、26px、粗体，不显式指定首行色，沿用主题默认。H1层级来自首行`# `井号语法，26px粗体只是配套视觉，二者不能互相替代。副文案16px普通，future/technology用#FFFFFFB3，其余灰色如#646A73；行距1.3、透明背景、边框0。新建示例：

```json
{"text":"# 经营概览\n查看本月经营数据与待办事项。","text_styles":[{"target":"经营概览","style":{"font_size":26,"bold":true}},{"target":"查看本月经营数据与待办事项。","style":{"font_size":16,"font_color":"#646A73"}}]}
```

通栏标题配套 `--display-config '{"line_spacing":1.3,"background_color":"transparent","border_width":0}'` 和 `--layout-config '{"position":{"x":0,"y":0,"w":48,"h":3},"size_mode":{"width":"fixed","height":"auto"}}'`。主题变化同步副文案颜色，用户样式优先。

## 局部样式与更新

text_styles为`[{target,occurrence?,style}]`：target是Markdown渲染后非空单行可见文本，重复须从1起occurrence或"all"；不能近似匹配。style支持font_size整数10～72、font_color/background_color HEX、bold/italic/underline/strikethrough布尔。颜色#RGB/#RRGGBB/#RRGGBBAA。

```json
{"text_styles":[{"target":"目标","occurrence":2,"style":{"font_size":24,"font_color":"#f00","underline":true}}]}
```

正文整体替换，text=""显式清空，省略保留。追加或重建前取得完整内容、结构与样式；回读text可能已是解析后的可见文本，不能直接当无损Markdown拼回，否则会丢标题/链接等结构。无法还原保留项时报告缺口。只改样式不重写正文；既有标题有显式颜色时，仅省略font_color会保留旧色，不宣称已恢复主题默认色。

## 回读与标题证据

block-get读取data.block.data_config.text；Markdown标题标记在解析后可能被消费，回读首行没有`#`不能据此判定标题缺失。写前仍必须按上文提交标题语法；写入内容只证明请求意图，不能代替真实标题层级证据。若当前公开回读暴露明确的富文本标题结构则据实核对；未暴露时将标题层级记为`unverified`，不编造字段或借字号推断。

实际text_runs来自富文本快照，start/end为可见文本UTF-16下标，end不包含，包含text/style。text_runs只读、不回写，只证明字号/粗体/颜色等视觉样式，不证明标题层级，不拿请求text_styles代替实际样式证据。text没有get-data。定位/样式失败保持失败，不新建重叠文本遮盖；链接/图片/表格等Markdown不作为通用样式承诺。
