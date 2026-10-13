# 规整对齐

状态：已实现。

参考：图 1 的交替图文、图 2 / 3 的双栏比较、图 5 的规格与四格图片。归并为同一网格；内容顺序和列数是参数，不按行业复制实现。

<a id="layout.evidence-grid"></a>

## 规整对齐原子

风格标签：通用。

| 参数 | 默认值 | 调整与作用 |
|---|---|---|
| `--vl-grid-columns` | `2` | 整数 1–4；宽度不足时切为 1 |
| `--vl-grid-gap` | `16px` | 0–40px；图 5 拼接四格可设为 0 |
| `--vl-grid-align` | `stretch` | start / center / stretch |
| `--vl-grid-ratio` | `1fr 1fr` | 仅 .vl-grid--ratio；如 1.2fr 1fr |

```css
.vl-grid { display:grid; grid-template-columns:repeat(var(--vl-grid-columns,2),minmax(0,1fr)); gap:var(--vl-grid-gap,16px); align-items:var(--vl-grid-align,stretch); }
.vl-grid > * { min-width:0; overflow-wrap:anywhere; }
:where(.vl-grid img) { display:block; width:100%; height:auto; }
.vl-grid--ratio { grid-template-columns:var(--vl-grid-ratio,1fr 1fr); }
```

```html
<section class="vl-grid"><article>第一项</article><article>第二项</article></section>
```

双栏比较：columns=2；三项成分：columns=3；四格：columns=2、四个子项。图文交替保持同一结构，只交换相邻行的图文 DOM 顺序；长文本优先保持语义阅读顺序。规格列表可将同一网格用于每条 dl 行，另加底边线。

图片规则仅提供低优先级自适应默认值，局部图窗与主场的明确宽高、取景必须优先；嵌套使用时检查实际尺寸，不能由网格后加载将定高图窗改回图片自然比例。

等宽网格与比例网格二选一。窄画布的比例网格需同时把 ratio 改为 `1fr`。参考图 3–7 的三条长页并排属于作品展示排版，不据此把实际详情页设成三列。

实现值为视觉近似和可调起点，不是原设计源文件的精确数值。CSS 为生成阶段实现源；正式交付按现有协议展开为行内样式。

<a id="layout.card-rail"></a>

## 横向卡片列

风格标签：通用。

参考蓝色生活活动的侧向露出卡片、女性电影的横向海报。双栏瀑布图文仍使用已有网格，不把所有图片组都改成横向滚动。

| 参数 | 默认值 | 作用与调整 |
|---|---|---|
| `--vl-rail-card-width` | `78%` | 单卡宽度；小于 100% 时露出下一张 |
| `--vl-rail-gap` | `16px` | 卡片间距 |
| `--vl-rail-inset` | `16px` | 两侧与上下安全距离 |

```css
.vl-rail { display:grid; grid-auto-flow:column; grid-auto-columns:var(--vl-rail-card-width,78%); gap:var(--vl-rail-gap,16px); padding:var(--vl-rail-inset,16px); overflow-x:auto; scroll-snap-type:x proximity; }
.vl-rail > * { min-width:0; margin:0; scroll-snap-align:start; overflow-wrap:anywhere; }
:where(.vl-rail img) { display:block; width:100%; height:auto; }
```

```html
<section class="vl-rail" aria-label="作品集"><article>第一张</article><article>第二张</article><article>第三张</article></section>
```

静态导出只能呈现当前可见区域；必须完整展示的信息应使用网格或多章节。没有脚本也可滚动浏览，此布局不包含自动轮播、翻页按钮或数据加载。


<a id="layout.annotated-figure"></a>

## 带引导线的图像标注

风格标签：通用。

适用于两组参考的主体周围标签。图片占独立中央列，左右标注按行对齐；标签引导线是 CSS 直线，不伪装为真实分子连接。复杂曲线路径由任务 SVG 或图像承担。

| 参数 | 默认值 | 作用 |
|---|---|---|
| `--vl-annotation-columns` | `1fr 1.4fr 1fr` | 左标注／图片／右标注宽度 |
| `--vl-annotation-gap` | `24px` | 行列间距 |
| `--vl-annotation-line` | `40px` | 水平引导线长度，不应超过预留槽位 |
| `--vl-annotation-size` | `28px` | 标注字号 |
| `--vl-annotation-rows` | `3` | 图片跨越的行数，与实际标注行数一致 |

```css
.vl-annotated { display:grid; grid-template-columns:var(--vl-annotation-columns,1fr 1.4fr 1fr); gap:var(--vl-annotation-gap,24px); align-items:center; }
.vl-annotated__image { grid-column:2; grid-row:1 / span var(--vl-annotation-rows,3); display:block; width:100%; height:auto; align-self:center; }
.vl-annotation { min-width:0; display:flex; align-items:center; gap:8px; font-size:var(--vl-annotation-size,28px); line-height:1.4; color:var(--vl-ink); }
.vl-annotation__text { min-width:0; overflow-wrap:anywhere; }
.vl-annotation__line { flex:0 0 var(--vl-annotation-line,40px); height:1px; background:var(--vl-edge-color,currentColor); }
```

```html
<div class="vl-annotated" style="--vl-annotation-rows:2">
 <img class="vl-annotated__image" src="机理图素材" alt="由已核验资料决定的机理图">
 <div class="vl-annotation" style="grid-column:1;grid-row:1"><span class="vl-annotation__text">成分名称</span><span class="vl-annotation__line" aria-hidden="true"></span></div>
 <div class="vl-annotation" style="grid-column:3;grid-row:2"><span class="vl-annotation__line" aria-hidden="true"></span><span class="vl-annotation__text">作用说明</span></div>
</div>
```

此结构用于预留标注区的图片，行位置须按最终资产校准。精确指向内部点时在 HTML 实现 中记录端点坐标，用独立路径连接，不声称上述短线已经命中内部结构。窄版不容纳三列时改为图上、说明在下的普通单列，不挤压长文字；图内已有说明时不再重复叠字。

<a id="layout.date-event-row"></a>

## 日期机构说明行与时间线

风格标签：通用。

各事件共享日期、机构、说明三列；可选时间线使用日期列右边框和同轴节点，行高由最长内容决定，线随行连续伸长。

参数基准：示例宽680px；原子颜色用于机制演示，由整页组合覆盖，不绑定某种风格。

| 参数 | 默认值、单位与范围 |
|---|---|
| `--cv-date-col` | {"default": "104px", "unit": "px", "range": "80–140"} |
| `--cv-org-col` | {"default": "155px", "unit": "px", "range": "120–200"} |
| `--cv-row-gap` | {"default": "22px", "unit": "px", "range": "12–32"} |
| `data-timeline` | {"default": "true", "unit": "enum", "range": ["true", "false"]} |

```css
.cv-events,.cv-events *{box-sizing:border-box}.cv-events{--cv-date-col:104px;--cv-org-col:155px;--cv-row-gap:22px;width:min(100%,680px);padding:28px;background:#fff;color:#25372f;font:14px/1.6 Arial,'PingFang SC',sans-serif}.cv-events h2{font-size:22px;margin:0 0 24px}.cv-events .cv-event{display:grid;grid-template-columns:var(--cv-date-col) var(--cv-org-col) minmax(0,1fr);min-width:0}.cv-events .cv-event-date{position:relative;padding:0 16px var(--cv-row-gap) 0;overflow-wrap:anywhere;font-size:12px}.cv-events .cv-event-org,.cv-events .cv-event-desc{margin:0;padding:0 0 var(--cv-row-gap) 22px;min-width:0;overflow-wrap:anywhere}.cv-events .cv-event-org{font-size:14px}.cv-events[data-timeline=true] .cv-event-date{border-right:1px solid #738d7e}.cv-events[data-timeline=true] .cv-event-date:after{content:'';position:absolute;right:-4px;top:.5em;width:7px;height:7px;background:#315b45;border-radius:50%}.cv-events .cv-event:last-child>*{padding-bottom:0}@media(max-width:540px){.cv-events{--cv-date-col:85px}.cv-events .cv-event{grid-template-columns:var(--cv-date-col) minmax(0,1fr)}.cv-events .cv-event-date{grid-column:1;grid-row:1/3}.cv-events .cv-event-org{grid-column:2;padding-bottom:6px}.cv-events .cv-event-desc{grid-column:2}}
```

```html
<section class="cv-events" data-timeline="true" aria-label="工作经历"><h2>工作经历</h2><article class="cv-event"><div class="cv-event-date"><time datetime="2021">2021</time>–<time datetime="2025">2025</time></div><h3 class="cv-event-org">North Studio<br>Senior Designer</h3><p class="cv-event-desc">Led the design system and aligned product teams around accessible interaction patterns.</p></article><article class="cv-event"><div class="cv-event-date"><time datetime="2018">2018</time>–<time datetime="2021">2021</time></div><h3 class="cv-event-org">International Service Innovation Laboratory<br>Designer</h3><p class="cv-event-desc">Designed research prototypes and editorial tools for distributed teams.</p></article></section>
```

适配与边界：
- 时间线是行边框，不使用固定总高；节点相对日期首行定位。
- 机构长名自然增高，不省略说明。窄屏机构与说明合为右列，DOM阅读顺序仍为日期、机构、说明。
- 日期列右侧16px及正文左侧22px分别保护文字与节点；时间线不是数值图表。

示例中的头像轮廓仅验证几何占位，不是可交付人物素材；正式注入人像需另验主体裁切。SVG复用时须按实例重命名ID及引用。

<a id="layout.editorial-rules"></a>

## 同轴编辑式分隔线

风格标签：通用。

页边框、整宽页眉底线、各章节底线与共享两列网格的单元边框共同生成规则线；所有线都是布局边界，不额外绝对定位。

参数基准：示例宽680px；原子颜色用于机制演示，由整页组合覆盖，不绑定某种风格。

| 参数 | 默认值、单位与范围 |
|---|---|
| `--cv-label-col` | {"default": "156px", "unit": "px", "range": "120–210"} |
| `--cv-rule-width` | {"default": "1px", "unit": "px", "range": "1–2"} |
| `--cv-rule-color` | {"default": "#25382e", "unit": "color", "range": "可辨识线色"} |
| `--cv-cell-pad` | {"default": "22px", "unit": "px", "range": "16–32"} |

```css
.cv-editorial,.cv-editorial *{box-sizing:border-box}.cv-editorial{--cv-label-col:156px;--cv-rule-width:1px;--cv-rule-color:#25382e;--cv-cell-pad:22px;width:min(100%,680px);border:var(--cv-rule-width) solid var(--cv-rule-color);background:#faf9f4;color:#25382e;font:14px/1.65 Arial,'PingFang SC',sans-serif}.cv-editorial .cv-editorial-head{padding:var(--cv-cell-pad);border-bottom:var(--cv-rule-width) solid var(--cv-rule-color)}.cv-editorial h1{font-size:36px;line-height:1.15;margin:0 0 10px}.cv-editorial .cv-editorial-row{display:grid;grid-template-columns:var(--cv-label-col) minmax(0,1fr);border-bottom:var(--cv-rule-width) solid var(--cv-rule-color)}.cv-editorial .cv-editorial-row:last-child{border-bottom:0}.cv-editorial .cv-editorial-label{margin:0;padding:var(--cv-cell-pad);border-right:var(--cv-rule-width) solid var(--cv-rule-color);font-size:17px;overflow-wrap:anywhere}.cv-editorial .cv-editorial-body{min-width:0;padding:var(--cv-cell-pad)}.cv-editorial p{margin:0 0 10px;overflow-wrap:anywhere}.cv-editorial p:last-child{margin-bottom:0}@media(max-width:440px){.cv-editorial{--cv-label-col:100px;--cv-cell-pad:14px}}
```

```html
<article class="cv-editorial"><header class="cv-editorial-head"><h1>个人履历</h1><p>Alex Chen / Product &amp; Editorial Designer</p></header><section class="cv-editorial-row"><h2 class="cv-editorial-label">个人简介</h2><div class="cv-editorial-body"><p>I build visual languages for products, publications and public services.</p></div></section><section class="cv-editorial-row"><h2 class="cv-editorial-label">工作经历</h2><div class="cv-editorial-body"><p><strong>North Studio · 2021–2025</strong><br>Senior Designer</p><p>Created a scalable design system and supported cross-functional delivery.</p></div></section><section class="cv-editorial-row"><h2 class="cv-editorial-label">教育背景</h2><div class="cv-editorial-body"><p>Example University<br>BA in Visual Communication · 2017–2021</p></div></section></article>
```

适配与边界：
- 所有章节必须复用同一个--cv-label-col；改变列宽时分隔线自动同轴。
- 单元内距是文字安全区，外边框就是版心边界；不添加浮动卡片破坏连续规则线。
- 长标题可断行并推高章节；打印跨页边框处理取决于浏览器，应检查分页预览。

示例中的头像轮廓仅验证几何占位，不是可交付人物素材；正式注入人像需另验主体裁切。SVG复用时须按实例重命名ID及引用。

<a id="layout.labeled-meter"></a>

## 对齐标签量尺：平条、框条与圆点

风格标签：通用。

每行使用同一标签/轨道/数值三列网格，标签按行自然增长，轨道始终与标签和数值垂直居中。无框模式直接填充轨道，有框模式在边框内留出内衬，圆点模式以等效归一化坐标定位标记并补偿半径以防越界。数值仅用于布局演示，每个量尺提供明确aria-label及同步的数值语义。

参数基准：示例宽680px；原子颜色用于机制演示，由整页组合覆盖，不绑定某种风格。

| 参数 | 默认值、单位与范围 |
|---|---|
| `--cv-demo-width` | {"default": "680px", "unit": "px", "range": "示例固定680px；窄屏最大100%"} |
| `--cv-label-width` | {"default": "148px", "unit": "px", "range": "100–220px，实际不超过行宽34%"} |
| `--cv-row-gap` | {"default": "22px", "unit": "px", "range": "12–36px"} |
| `--cv-column-gap` | {"default": "16px", "unit": "px", "range": "8–24px"} |
| `--cv-track-height` | {"default": "10px", "unit": "px", "range": "6–16px"} |
| `--cv-frame-pad` | {"default": "3px", "unit": "px", "range": "2–6px"} |
| `--cv-dot-size` | {"default": "14px", "unit": "px", "range": "10–20px"} |
| `--cv-accent` | {"default": "#244c50", "unit": "color", "range": "合法CSS颜色"} |
| `--cv-track-color` | {"default": "#d9dfdc", "unit": "color", "range": "合法CSS颜色，须能区分轨道和填充"} |
| `--cv-value` | {"default": 60, "unit": "百分比数值，无单位", "range": "0–100；各轨道独立设置"} |
| `data-cv-mode` | {"default": "plain", "unit": "enum", "range": ["plain", "framed", "dot"]} |

```css
.cv-meter-demo{--cv-demo-width:680px;--cv-label-width:148px;--cv-row-gap:22px;--cv-column-gap:16px;--cv-track-height:10px;--cv-frame-pad:3px;--cv-dot-size:14px;--cv-accent:#244c50;--cv-track-color:#d9dfdc;box-sizing:border-box;width:var(--cv-demo-width);max-width:100%;padding:28px;background:#fff;color:#202a29;font-family:Arial,'PingFang SC',sans-serif;isolation:isolate}.cv-meter-demo *{box-sizing:border-box}.cv-meter-demo .cv-meter-heading{margin:0 0 8px;font-size:22px;line-height:1.4;overflow-wrap:anywhere}.cv-meter-demo .cv-meter-note{margin:0 0 26px;color:#505e5b;font-size:13px;line-height:1.6;overflow-wrap:anywhere}.cv-meter-demo .cv-meter-list{display:grid;gap:var(--cv-row-gap);margin:0;padding:0;list-style:none}.cv-meter-demo .cv-meter-row{display:grid;grid-template-columns:minmax(0,min(var(--cv-label-width),34%)) minmax(var(--cv-dot-size),1fr) 4ch;column-gap:var(--cv-column-gap);align-items:center}.cv-meter-demo .cv-meter-label{min-width:0;font-size:14px;line-height:1.5;overflow-wrap:anywhere}.cv-meter-demo .cv-meter-value{font-size:13px;line-height:1.5;text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}.cv-meter-demo .cv-meter-track{--cv-value:60;--cv-normalized:clamp(0,var(--cv-value),100);position:relative;min-width:var(--cv-dot-size);height:var(--cv-track-height);background:var(--cv-track-color)}.cv-meter-demo .cv-meter-fill{display:block;width:calc(var(--cv-normalized)*1%);height:100%;background:var(--cv-accent)}.cv-meter-demo .cv-meter-row[data-cv-mode='framed'] .cv-meter-track{height:calc(var(--cv-track-height) + var(--cv-frame-pad)*2 + 2px);padding:var(--cv-frame-pad);border:1px solid var(--cv-accent);background:transparent}.cv-meter-demo .cv-meter-row[data-cv-mode='dot'] .cv-meter-track{height:max(var(--cv-track-height),var(--cv-dot-size));background:transparent}.cv-meter-demo .cv-meter-row[data-cv-mode='dot'] .cv-meter-track::before{content:'';position:absolute;left:calc(var(--cv-dot-size)/2);right:calc(var(--cv-dot-size)/2);top:50%;height:2px;transform:translateY(-50%);background:var(--cv-track-color)}.cv-meter-demo .cv-meter-dot{position:absolute;top:50%;left:calc(var(--cv-normalized)*1%);width:var(--cv-dot-size);height:var(--cv-dot-size);transform:translate(calc(var(--cv-normalized)*-1%),-50%);border-radius:50%;background:var(--cv-accent)}@media(forced-colors:active){.cv-meter-demo .cv-meter-track{background:Canvas;border:1px solid CanvasText}.cv-meter-demo .cv-meter-fill,.cv-meter-demo .cv-meter-dot{background:Highlight;forced-color-adjust:none}.cv-meter-demo .cv-meter-row[data-cv-mode='framed'] .cv-meter-track{border-color:CanvasText}.cv-meter-demo .cv-meter-row[data-cv-mode='dot'] .cv-meter-track{border:0}.cv-meter-demo .cv-meter-row[data-cv-mode='dot'] .cv-meter-track::before{background:CanvasText;forced-color-adjust:none}}
```

```html
<section class="cv-meter-demo" aria-label="标签量尺布局演示"><h2 class="cv-meter-heading">标签量尺 · 展示样式</h2><p class="cv-meter-note">以下数值仅演示布局，不代表真实能力、评价或测量结果。</p><ul class="cv-meter-list"><li class="cv-meter-row" data-cv-mode="plain"><span class="cv-meter-label" lang="en">Editorial design</span><div class="cv-meter-track" style="--cv-value:60" role="meter" aria-label="Editorial design，无框条布局示例，非真实能力" aria-valuemin="0" aria-valuemax="100" aria-valuenow="60" aria-valuetext="60%，仅为演示数值"><span class="cv-meter-fill" aria-hidden="true"></span></div><span class="cv-meter-value" aria-hidden="true">60%</span></li><li class="cv-meter-row" data-cv-mode="framed"><span class="cv-meter-label" lang="en">Research and content strategy</span><div class="cv-meter-track" style="--cv-value:45" role="meter" aria-label="Research and content strategy，有框条布局示例，非真实能力" aria-valuemin="0" aria-valuemax="100" aria-valuenow="45" aria-valuetext="45%，仅为演示数值"><span class="cv-meter-fill" aria-hidden="true"></span></div><span class="cv-meter-value" aria-hidden="true">45%</span></li><li class="cv-meter-row" data-cv-mode="dot"><span class="cv-meter-label" lang="en">Digital prototyping</span><div class="cv-meter-track" style="--cv-value:72" role="meter" aria-label="Digital prototyping，圆点位置布局示例，非真实能力" aria-valuemin="0" aria-valuemax="100" aria-valuenow="72" aria-valuetext="72%，仅为演示数值"><span class="cv-meter-dot" aria-hidden="true"></span></div><span class="cv-meter-value" aria-hidden="true">72%</span></li></ul></section>
```

适配与边界：
- 通用局部机制，不限制产物类型；默认不宣称真实能力。若用于实际数据，须提供来源、单位和量程，不能仅以视觉长度暗示可信评价。
- CSS仅约束视觉值；更新时必须同时同步--cv-value、可见百分比、aria-valuenow和aria-valuetext。当前量程为0–100，不能直接套用其他单位。
- 三类安全区：示例外缘28px；标签与轨道由列间距隔开；有框条内衬和圆点半径补偿保护轨道边缘。长标签增长行高、不覆盖轨道，数值列保持对齐。
- 所有行须共享网格参数。极窄容器应降低标签宽度、列间距和外边距；轨道至少应宽于圆点，推荐不小于80px。
- 背景保持平面而非卡片；示例无图片。放到照片背景上时应为整个量尺区域提供不透明底色，保持标签可读与轨道对比。
- 圆点是非交互数据标记，不是滑块；如需用户输入，应改用原生range控件并实现键盘操作。

示例中的头像轮廓仅验证几何占位，不是可交付人物素材；正式注入人像需另验主体裁切。SVG复用时须按实例重命名ID及引用。

<a id="layout.stacked-label-track"></a>

## 上标签、下细轨的纵向列表

风格标签：通用。粒度：局部模块；不绑定整页色彩与字体。



```json
{"dependencies": []}
```

| 参数 | 默认 | 调整范围 | 作用 |
|---|---|---|---|
| `--cvx-value` | 0 | 0–100的无单位数字；越界时钳制；逐项设置 | 作为轨道填充比例的唯一数值来源，不生成数值列或能力事实。 |
| `--cvx-label-track-gap` | 0.4rem | 0.2rem–1rem | 控制上方完整宽度标签与下一行细轨的距离。 |
| `--cvx-track-row-gap` | 1rem | 0.5rem–2rem | 控制相邻标签轨道组的间距。 |
| `--cvx-track-thickness` | 2px | 1px–3px | 保持参考中的细轨形态，不改为粗进度条。 |
| `--cvx-track-ink` | currentColor | 合法CSS颜色 | 配置局部填充颜色。 |
| `--cvx-track-rest` | color-mix(in srgb,currentColor 25%,transparent) | 合法CSS颜色 | 配置完整底轨颜色；默认跟随宿主前景色。 |
| `--cvx-heading-gap` | 0.75rem | 0.25rem–2rem | 控制栏目标题与说明之间的间距。 |

- 每项严格为单列两行：标签占完整宽度，下一行是完整底轨与填充；禁止改为标签、轨道、百分比三列。
- 默认是装饰性展示轨，--cvx-value控制0–100填充。需要表达真实能力时由用户提供事实及可读标签，不把示例长度自动推断为评分。
- 每条轨道都有data-display-only和明确的aria-label；不使用progressbar或meter角色，不把虚构演示值描述为能力事实。
- 长标签必须换行并自然撑高，不能截断、单行省略或与细轨重叠。
- 没有overflow:hidden、伪元素、固定正文高度或整页字体颜色默认值；font-synthesis:none。
- 所用软件名称只是虚构样稿栏目，不代表任何真实人物的工具熟练程度。

```css
.cvx-stacked-label-track,.cvx-stacked-label-track *{box-sizing:border-box;min-width:0;max-width:100%}
.cvx-stacked-label-track{font-synthesis:none;overflow-wrap:anywhere}
.cvx-stacked-label-track h2{margin:0 0 var(--cvx-heading-gap,.75rem)}
.cvx-track-note{margin:0 0 var(--cvx-track-row-gap,1rem)}
.cvx-track-list{display:grid;grid-template-columns:minmax(0,1fr);gap:var(--cvx-track-row-gap,1rem);margin:0;padding:0;list-style:none}
.cvx-track-item{display:grid;grid-template-columns:minmax(0,1fr);row-gap:var(--cvx-label-track-gap,.4rem)}
.cvx-track-label{display:block;white-space:normal}
.cvx-thin-track{block-size:var(--cvx-track-thickness,2px);background:var(--cvx-track-rest,color-mix(in srgb,currentColor 25%,transparent))}
.cvx-thin-track-fill{display:block;inline-size:clamp(0%,calc(var(--cvx-value,0)*1%),100%);block-size:100%;background:var(--cvx-track-ink,currentColor)}
```

```html
<section class="cvx-stacked-label-track" data-css-atom="layout.stacked-label-track" aria-label="标签与细轨的展示用布局" style="--cvx-track-ink:#304fa2;--cvx-track-rest:#9d9d9d;max-width:25rem">
  <h2>Tools &amp; practice areas</h2>
  <p class="cvx-track-note">虚构设计师 Mira Vale 的工具栏目排版样稿。以下轨道宽度仅为CSS布局测试值，不表示熟练度、能力、完成度或测评结果。</p>
  <ul class="cvx-track-list" role="list">
    <li class="cvx-track-item" style="--cvx-value:58">
      <span class="cvx-track-label">Adobe Photoshop · Editorial image assembly</span>
      <div class="cvx-thin-track" data-display-only="true" role="img" aria-label="Photoshop栏目展示轨道：宽度仅为CSS布局演示，不代表能力或测评结果。"><span class="cvx-thin-track-fill" aria-hidden="true"></span></div>
    </li>
    <li class="cvx-track-item" style="--cvx-value:72">
      <span class="cvx-track-label">Adobe Illustrator · Maps and visual explanations</span>
      <div class="cvx-thin-track" data-display-only="true" role="img" aria-label="Illustrator栏目展示轨道：宽度仅为CSS布局演示，不代表能力或测评结果。"><span class="cvx-thin-track-fill" aria-hidden="true"></span></div>
    </li>
    <li class="cvx-track-item" style="--cvx-value:44">
      <span class="cvx-track-label">Adobe After Effects · Short exhibition titles</span>
      <div class="cvx-thin-track" data-display-only="true" role="img" aria-label="After Effects栏目展示轨道：宽度仅为CSS布局演示，不代表能力或测评结果。"><span class="cvx-thin-track-fill" aria-hidden="true"></span></div>
    </li>
    <li class="cvx-track-item" style="--cvx-value:31">
      <span class="cvx-track-label">Figma · Collaborative publication planning and accessible component documentation</span>
      <div class="cvx-thin-track" data-display-only="true" role="img" aria-label="Figma栏目展示轨道：宽度仅为CSS布局演示，不代表能力或测评结果。"><span class="cvx-thin-track-fill" aria-hidden="true"></span></div>
    </li>
  </ul>
</section>
```

<a id="layout.grouped-record-row"></a>

## 左侧成组标签、右侧项目说明的履历行

风格标签：通用。粒度：局部模块；不绑定整页色彩与字体。

依赖：[胶囊与徽章](../shapes/capsules-and-badges.md#shape.badge)。

```json
{"dependencies": ["shape.badge"]}
```

| 参数 | 默认 | 调整范围 | 作用 |
|---|---|---|---|
| `--cvx-record-left` | 2fr | 1fr–4fr；在整个记录组上统一设置 | 确定左侧职位及标签组的共享列权重。 |
| `--cvx-record-right` | 3fr | 1fr–6fr；在整个记录组上统一设置 | 确定右侧项目说明的共享列权重。 |
| `--cvx-record-column-gap` | 1.25rem | 0.5rem–3rem | 控制两列之间的距离。 |
| `--cvx-record-row-gap` | 1.5rem | 0.75rem–3rem | 控制完整履历行之间的间距。 |
| `--cvx-record-inner-gap` | 0.6rem | 0.25rem–1.25rem | 控制职位与标签组，以及窄屏堆叠后的上下间距。 |
| `--cvx-record-tag-gap` | 0.5rem | 0.25rem–1rem | 控制机构胶囊与日期描边标签的横向及换行间距。 |
| `--cvx-record-badge-fill` | transparent | 合法CSS颜色 | 仅配置机构胶囊填色，不新增配色原子。 |
| `--cvx-record-badge-ink` | inherit | 合法CSS颜色或inherit | 配置机构胶囊文字颜色，其余正文继续继承宿主。 |
| `--cvx-record-heading-gap` | 1rem | 0.5rem–2rem | 控制栏目标题、演示说明与记录列表之间的间距。 |
| `--cvx-record-bullet-gap` | 0.25rem | 0rem–0.75rem | 控制右列项目条目间距。 |

- 必须先加载真实依赖shape.badge提供的.vl-badge；机构与日期均使用该类。本原子不重新定义胶囊圆角、内边距或轮廓路径。
- 日期仅增加透明背景和1px描边的局部修饰，胶囊几何继续由.vl-badge负责；依赖缺失时不能声称外观完整。
- 左列职位在上，机构与日期在其下方通过flex并排；空间不足时允许标签整体换行及标签内部文本换行。
- 右列必须保留真实ul和li，不使用绝对定位或装饰文本替代项目说明。
- 所有履历行使用相同列权重和列间距；禁止逐行覆盖列比。每行高度由左右两列中较长内容自然决定。
- 局部列表宽度不超过30rem时，通过命名空间容器查询统一切换为单列；该断点不依赖整页视口宽度。
- 需要支持容器查询的浏览器；正式验证须加载真实shape.badge，检查其样式没有重新引入固定宽高、nowrap或正文裁切。
- 字体及正文颜色继承宿主，font-synthesis:none；所有正文可编辑且具备长机构名换行保护。
- 内容加长后局部记录自然增高，整页尺寸遵循品类Spec；简历容量不足时停止导出，待用户决定内容取舍或增加A4页，禁止缩字、整行截图或overflow:hidden。
- 日期胶囊采用display:block，避免父胶囊的inline-grid把两个time和连接号拆为三行；普通短年份区间应保持同行。

```css
.cvx-grouped-record-row,.cvx-grouped-record-row *{box-sizing:border-box;min-width:0;max-width:100%}
.cvx-grouped-record-row{font-synthesis:none;overflow-wrap:anywhere}
.cvx-grouped-record-row h2{margin:0 0 var(--cvx-record-heading-gap,1rem)}
.cvx-record-note{margin:0 0 var(--cvx-record-heading-gap,1rem)}
.cvx-record-list{display:grid;gap:var(--cvx-record-row-gap,1.5rem);container-name:cvx-record-list;container-type:inline-size}
.cvx-record{display:grid;grid-template-columns:minmax(0,var(--cvx-record-left,2fr)) minmax(0,var(--cvx-record-right,3fr));column-gap:var(--cvx-record-column-gap,1.25rem);row-gap:var(--cvx-record-inner-gap,.6rem);align-items:start}
.cvx-record-title{margin:0 0 var(--cvx-record-inner-gap,.6rem);font-size:inherit}
.cvx-record-meta{display:flex;flex-wrap:wrap;align-items:flex-start;gap:var(--cvx-record-tag-gap,.5rem)}
.cvx-record-meta>.vl-badge{flex:0 1 auto;white-space:normal;overflow-wrap:anywhere;text-align:start}
.cvx-record-organisation{background:var(--cvx-record-badge-fill,transparent);color:var(--cvx-record-badge-ink,inherit)}
.cvx-record-date{background:transparent;border:1px solid currentColor}
.cvx-record-projects{margin:0;padding-inline-start:1.2em}
.cvx-record-projects li+li{margin-block-start:var(--cvx-record-bullet-gap,.25rem)}
@container cvx-record-list (max-width:30rem){.cvx-record{grid-template-columns:minmax(0,1fr)}}
.cvx-record-meta>.cvx-record-date{display:block;flex:0 0 auto;max-width:100%}

```

```html
<section class="cvx-grouped-record-row" data-css-atom="layout.grouped-record-row" aria-label="Expériences professionnelles fictives" style="--cvx-record-badge-fill:#a6cce3;--cvx-record-left:2fr;--cvx-record-right:3fr;max-width:52rem">
  <h2>Expériences</h2>
  <p class="cvx-record-note">Exemple de CV fictif : Léa Marin. Les organisations, missions et dates ci-dessous sont inventées.</p>
  <div class="cvx-record-list">
    <article class="cvx-record" aria-label="Cheffe de projet digital chez Atelier Rivage">
      <div class="cvx-record-summary">
        <h3 class="cvx-record-title">Cheffe de projet digital</h3>
        <div class="cvx-record-meta">
          <span class="vl-badge cvx-record-organisation">Atelier Rivage</span>
          <span class="vl-badge cvx-record-date"><time datetime="2024">2024</time>–<time datetime="2025">2025</time></span>
        </div>
      </div>
      <ul class="cvx-record-projects">
        <li>Piloter la refonte du site d’un festival local avec une équipe éditoriale et deux partenaires techniques.</li>
        <li>Coordonner les étapes de validation, les contenus et le calendrier de publication.</li>
        <li>Documenter les décisions d’accessibilité et préparer la transmission à l’équipe de maintenance.</li>
      </ul>
    </article>
    <article class="cvx-record" aria-label="Responsable marketing digital et contenus multilingues">
      <div class="cvx-record-summary">
        <h3 class="cvx-record-title">Responsable marketing digital et contenus multilingues</h3>
        <div class="cvx-record-meta">
          <span class="vl-badge cvx-record-organisation">Collectif des initiatives culturelles et de la médiation numérique de Belle-Rive</span>
          <span class="vl-badge cvx-record-date"><time datetime="2022-03">mars 2022</time> – <time datetime="2023-12">décembre 2023</time></span>
        </div>
      </div>
      <ul class="cvx-record-projects">
        <li>Créer un calendrier de contenus pour les ateliers, les rencontres publiques et les ressources pédagogiques.</li>
        <li>Préparer des briefs de traduction et vérifier la cohérence des pages françaises et anglaises.</li>
        <li>Réunir les retours des équipes locales dans un bilan mensuel lisible, accompagné de propositions d’amélioration.</li>
      </ul>
    </article>
    <article class="cvx-record" aria-label="Chargée de communication chez Studio Aube Commune">
      <div class="cvx-record-summary">
        <h3 class="cvx-record-title">Chargée de communication</h3>
        <div class="cvx-record-meta">
          <span class="vl-badge cvx-record-organisation">Studio Aube Commune</span>
          <span class="vl-badge cvx-record-date"><time datetime="2020">2020</time>–<time datetime="2021">2021</time></span>
        </div>
      </div>
      <ul class="cvx-record-projects">
        <li>Préparer les dossiers de présentation et les supports de communication des expositions.</li>
        <li>Organiser les échanges avec les associations partenaires et tenir à jour les informations pratiques.</li>
      </ul>
    </article>
  </div>
</section>
```
