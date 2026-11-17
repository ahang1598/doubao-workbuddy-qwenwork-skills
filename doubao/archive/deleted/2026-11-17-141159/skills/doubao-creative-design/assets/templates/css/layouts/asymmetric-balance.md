# 错落平衡

状态：已实现。

参考：图 2 的左右接力标题。用同一栏内对齐建立错位，文字保持真实占位。

<a id="layout.staggered-title"></a>

## 错落平衡原子

风格标签：通用。

| 参数 | 默认值 | 调整与作用 |
|---|---|---|
| `--vl-stagger-gap` | `4px` | 标题行之间距离 |
| `--vl-stagger-inset` | `12%` | 第二行左侧安全留白；建议 0–24% |

```css
.vl-stagger { display:grid; gap:var(--vl-stagger-gap,4px); }
.vl-stagger > * { margin:0; min-width:0; overflow-wrap:anywhere; }
.vl-stagger > :nth-child(even) { margin-inline-start:var(--vl-stagger-inset,12%); text-align:right; }
```

```html
<h2 class="vl-stagger"><span>首句左侧起笔</span><span>次句右侧收束</span></h2>
```

字号、行高和强调色复用现有文字与配色参数。短句错位是此分支成立的条件；正文或很长的标题不强行拆行，不通过固定高度或负位移制造重叠。

实现值为视觉近似和可调起点，不是原设计源文件的精确数值。CSS 为生成阶段实现源；正式交付按现有协议展开为行内样式。

<a id="layout.cross-column-axis"></a>

## 跨栏标题与单侧信息轴

风格标签：通用。

粒度：整页布局；参考科技与私享邀请。复用主场的图像定位思想，但新增跨栏标题、单侧信息轴、跨栏页脚和独立视觉净空的明确关系；不是两张并列卡片。

参数：axis-width=54%（建议45%–62%）；axis-inset=48px；axis-gap=32px；axis-height=1080px为样本最小高；axis-pause=32px控制标题后的视觉停顿，均按画幅调整。左右宽度先服从文字和真实主体边界；visual-inset控制素材区域，不保证素材内部自动避字。

正文与日期在rail内自然增高；固定画布超量应调整内容分配或重算高度，不隐藏溢出、不默认缩字。没有右侧主体的任务只复用其他布局。长标题可跨栏，但不得覆盖实际高光／主体；替换素材后重新检查。

```css
.vl-invite-axis { position:relative; isolation:isolate; display:grid; grid-template-columns:minmax(0,var(--vl-axis-width,54%)) minmax(0,1fr); grid-template-rows:auto 1fr auto; gap:var(--vl-axis-gap,32px); padding:var(--vl-axis-inset,48px); box-sizing:border-box; min-height:var(--vl-axis-height,1080px); }
.vl-invite-axis__header,.vl-invite-axis__footer { grid-column:1/-1; position:relative; z-index:2; min-width:0; }
.vl-invite-axis__rail { grid-column:1; position:relative; z-index:2; min-width:0; display:flex; flex-direction:column; justify-content:space-between; gap:var(--vl-axis-info-gap,36px); padding-top:var(--vl-axis-pause,32px); }
.vl-invite-axis__visual { position:absolute; inset:var(--vl-visual-inset,22% 0 12% 42%); z-index:0; pointer-events:none; }
.vl-invite-axis__visual img { width:100%; height:100%; object-fit:contain; object-position:right center; display:block; }
```

```html
<section class="vl-invite-axis">
  <div class="vl-invite-axis__visual"><!-- 单侧主体素材；全幅背景另绑定section；净空不能靠降低整图opacity取得 --></div>
  <header class="vl-invite-axis__header"><h1>邀请函</h1><p>INVITATION</p></header>
  <div class="vl-invite-axis__rail"><div>活动名称</div><div>时间与地点</div></div>
  <footer class="vl-invite-axis__footer">报名与联系入口</footer>
</section>
```

<a id="layout.offset-rhythm"></a>

## 疏密交替的偏置内容组

风格标签：通用。

粒度：内容组布局。整组标题和正文在同一12列网格中自然占位，区别于仅错行标题和居中阅读栏。默认起列1、占7列；右组起列6，中组起列3；起列+跨度不得超过13。列距12px、外距42px、组内距10px、段前28px，quiet段前72px；值按画幅调整，均非负。长内容改wide满12列或增高，不缩字、不隐藏；窄画幅在规划时选wide，不默认媒体查询改变构图。原子不创建或裁切背景，背景归共同祖先，渐变默认无。组内可含独立图像，不能为每组复制共底。

已有 [居中阅读栏](airy-and-spacious.md#layout.reading-column) 与 [错行标题](#layout.staggered-title) 用于不同关系，本实现无运行依赖。

```css
.orx-flow{box-sizing:border-box;display:grid;grid-template-columns:repeat(12,minmax(0,1fr));column-gap:var(--orx-column-gap,12px);row-gap:0;padding:var(--orx-pad,42px)}.orx-group{grid-column:var(--orx-start,1)/span var(--orx-span,7);display:grid;align-content:start;gap:var(--orx-inner,10px);min-width:0;margin:0;margin-block-start:var(--orx-pause,28px);overflow-wrap:anywhere}.orx-group>*{margin:0;min-width:0}.orx-group--right{--orx-start:6}.orx-group--middle{--orx-start:3}.orx-group--quiet{--orx-pause:72px}.orx-group--wide{--orx-start:1;--orx-span:12}.orx-demo{width:600px;max-width:100%;margin:0 auto;background:#fff;color:#252b26;font-family:'PingFang SC',Arial,sans-serif}.orx-demo h2{font:400 26px/1.45 'Songti SC',serif}.orx-demo p{font-size:15px;line-height:1.9}.orx-demo small{font:12px/1.6 Arial,'PingFang SC',sans-serif;letter-spacing:1px}
```

```html
<article class="orx-demo"><div class="orx-flow"><section class="orx-group"><small>一 · 观物</small><h2>让一枝清影，留在日常</h2><p>窗边的光慢慢移动，叶片在墙上留下细小的轮廓。空间不必填满，器物也可以安静地被看见。</p></section><section class="orx-group orx-group--right orx-group--quiet"><small>二 · 取材</small><h2>顺着材料的纹理</h2><p>观察纤维的方向，再决定弧度与转折。保留自然形成的细节，让触感成为阅读的一部分。</p></section><section class="orx-group orx-group--quiet"><small>三 · 成形</small><h2>把细节交给时间</h2><p>从粗略轮廓到边缘收束，每一次调整都回应材料本身。轻与重之间，留出可以呼吸的距离。</p></section><section class="orx-group orx-group--right"><small>四 · 相伴</small><h2>在使用中继续生长</h2><p>不急于给出全部答案，让日常的光线、摆放与触摸，慢慢补足物件的故事。</p></section></div></article>
```

示例字体和底色属于演示，不是布局必需；组合另绑定素材、配色、字形和局部渐变。已验证600/420px及四倍正文的几何关系；不代表参考图素材、质感或完整组合效果验证通过。正式输出按目标协议展开样式。

<a id="layout.identity-sidebar"></a>

## 非对称身份侧栏

风格标签：通用。

用可调侧栏宽度和剩余主栏建立非均分网格；命名区域支持左右交换，底色、照片区域和正文独立控制。

适用产物：简历／个人履历／作品集介绍页；粒度：局部模块。此原子不代替整页组合。

参数基准：示例宽680px；原子颜色用于机制演示，由整页组合覆盖，不绑定某种风格。

| 参数 | 默认值、单位与范围 |
|---|---|
| `--cv-width` | {"default": "680px", "unit": "px", "range": "示例680；可缩小"} |
| `--cv-side` | {"default": "210px", "unit": "px", "range": "170–250"} |
| `--cv-gap` | {"default": "26px", "unit": "px", "range": "16–40"} |
| `--cv-side-bg` | {"default": "#e5ecea", "unit": "color", "range": "与侧栏文字对比度至少4.5:1"} |
| `--cv-photo-height` | {"default": "180px", "unit": "px", "range": "120–240"} |
| `data-side` | {"default": "left", "unit": "enum", "range": ["left", "right"]} |

```css
.cv-identity,.cv-identity *{box-sizing:border-box}.cv-identity{--cv-width:680px;--cv-side:210px;--cv-gap:26px;--cv-side-bg:#e5ecea;--cv-photo-height:180px;width:min(100%,var(--cv-width));display:grid;grid-template-columns:var(--cv-side) minmax(0,1fr);grid-template-areas:'side main';background:#fff;color:#172b29;font:14px/1.6 Arial,'PingFang SC',sans-serif}.cv-identity[data-side=right]{grid-template-columns:minmax(0,1fr) var(--cv-side);grid-template-areas:'main side'}.cv-identity .cv-identity-side{grid-area:side;background:var(--cv-side-bg);padding:24px;min-width:0}.cv-identity .cv-identity-main{grid-area:main;padding:28px var(--cv-gap);min-width:0}.cv-identity .cv-identity-photo{height:var(--cv-photo-height);margin:0 0 24px;background:#c8d4d1;overflow:hidden;display:grid;place-items:center}.cv-identity .cv-identity-photo img{width:100%;height:100%;object-fit:cover}.cv-identity .cv-identity-photo svg{height:100%;width:100%}.cv-identity h1{font-size:32px;line-height:1.15;margin:0 0 12px}.cv-identity h2{font-size:17px;margin:24px 0 8px}.cv-identity p{margin:0 0 12px;overflow-wrap:anywhere}.cv-identity .cv-identity-role{letter-spacing:.12em;font-size:12px}@media(max-width:520px){.cv-identity,.cv-identity[data-side=right]{grid-template-columns:minmax(0,1fr);grid-template-areas:'side' 'main'}}
```

```html
<article class="cv-identity" data-side="left" aria-label="个人履历"><aside class="cv-identity-side"><figure class="cv-identity-photo" aria-label="人物照片占位"><svg viewBox="0 0 160 180" role="img" aria-label="Portrait placeholder"><circle cx="80" cy="62" r="30" fill="#809b95"/><path d="M20 180v-20a60 60 0 0 1 120 0v20" fill="#809b95"/></svg></figure><h2>联系方式</h2><p>Alex Chen<br>alex@example.com<br>Shanghai, China</p></aside><main class="cv-identity-main"><p class="cv-identity-role">PRODUCT DESIGNER</p><h1>个人履历</h1><p>Alex Chen creates accessible digital services and clear visual systems.</p><h2>工作经历</h2><p><strong>North Studio · Senior Designer</strong><br>2021–2025<br>Led research and interface design across a multilingual product platform.</p><h2>教育背景</h2><p>BA in Visual Communication<br>Example University, 2017–2021</p></main></article>
```

适配与边界：
- 侧栏与主栏不是均分布局；极长联系方式允许断行。
- 照片裁切安全区由实际照片object-position另设，避免裁掉脸部；正文不覆盖照片。
- 侧栏背景不承担正文卡片层；内容高度自然增长。左右互换不改变DOM阅读顺序。

示例中的头像轮廓仅验证几何占位，不是可交付人物素材；正式注入人像需另验主体裁切。SVG复用时须按实例重命名ID及引用。

<a id="layout.vertical-section-rail"></a>

## 竖排栏目导轨

风格标签：通用。

每个section按标题、内容的DOM顺序组成一行；窄标题轨道使用竖排中文，内容边框形成与该单元同高的连续导线。

适用产物：简历／个人履历／作品集介绍页；粒度：局部模块。此原子不代替整页组合。

参数基准：示例宽680px；原子颜色用于机制演示，由整页组合覆盖，不绑定某种风格。

| 参数 | 默认值、单位与范围 |
|---|---|
| `--cv-rail` | {"default": "56px", "unit": "px", "range": "40–80"} |
| `--cv-gap` | {"default": "22px", "unit": "px", "range": "12–32"} |
| `--cv-rule` | {"default": "#82948e", "unit": "color", "range": "可辨识线色"} |

```css
.cv-vrail,.cv-vrail *{box-sizing:border-box}.cv-vrail{--cv-rail:56px;--cv-gap:22px;--cv-rule:#82948e;width:min(100%,680px);padding:28px;background:#fff;color:#24332e;font:14px/1.65 Arial,'PingFang SC',sans-serif}.cv-vrail .cv-vrail-section{display:grid;grid-template-columns:var(--cv-rail) minmax(0,1fr);align-items:stretch}.cv-vrail .cv-vrail-title{writing-mode:vertical-rl;text-orientation:upright;letter-spacing:.18em;font-size:18px;line-height:1.4;margin:0;justify-self:start;padding:4px 0 24px}.cv-vrail .cv-vrail-content{border-left:1px solid var(--cv-rule);padding:0 0 28px var(--cv-gap);min-width:0}.cv-vrail .cv-vrail-content h3{font-size:17px;margin:0 0 8px}.cv-vrail .cv-vrail-content p{margin:0 0 12px;overflow-wrap:anywhere}.cv-vrail .cv-vrail-section:last-child .cv-vrail-content{padding-bottom:0}
.cv-vrail .cv-vrail-title[data-direction="rotate"]{text-orientation:mixed;transform:rotate(180deg)}
```

```html
<article class="cv-vrail" aria-label="个人履历"><section class="cv-vrail-section"><h2 class="cv-vrail-title">个人简介</h2><div class="cv-vrail-content"><h3>Alex Chen / Product Designer</h3><p>Designer focused on thoughtful interfaces, accessible services and editorial systems.</p></div></section><section class="cv-vrail-section"><h2 class="cv-vrail-title" data-direction="rotate">Experience</h2><div class="cv-vrail-content"><h3>North Studio</h3><p>Senior Designer · 2021–2025</p><p>Built a shared design language and worked with engineering teams to improve complex onboarding journeys.</p></div></section><section class="cv-vrail-section"><h2 class="cv-vrail-title">教育背景</h2><div class="cv-vrail-content"><p>Example University<br>BA in Visual Communication · 2017–2021</p></div></section></article>
```

适配与边界：
- 竖排适用于较短中文栏目名；长标题扩大该行高度，不固定裁切。
- 标题安全区为轨道宽度，正文安全区为导线右侧内距；不得把整段英文正文竖排。
- 导线由内容边框生成，不以跨页绝对定位线替代；打印可在section上按需添加break-inside:avoid。
- 英文整词侧转时在标题设置data-direction="rotate"；中文竖排默认upright。两种方向均需实测标题跨度。

示例中的头像轮廓仅验证几何占位，不是可交付人物素材；正式注入人像需另验主体裁切。SVG复用时须按实例重命名ID及引用。

<a id="layout.scattered-letter-rail"></a>

## 散字侧轨与自然流正文

风格标签：通用。粒度：局部模块；不绑定整页色彩与字体。



```json
{"dependencies": []}
```

| 参数 | 默认 | 调整范围 | 作用 |
|---|---|---|---|
| `--cvx-rail-width` | 6rem | 3rem–10rem；实际不超过局部容器宽度的30% | 调整装饰侧轨宽度，同时为正文保留独立列。 |
| `--cvx-rail-gap` | 1.25rem | 0rem–3rem；实际不超过局部容器宽度的5% | 控制侧轨与正文的间距。 |
| `--cvx-letter-size` | 6rem | 3rem–12rem | 改变真实字形字号，不使用缩放或拉伸变换。 |
| `--cvx-rail-step` | 4.5rem | 2rem–10rem | 控制相邻装饰字的基础纵向间距。 |
| `--cvx-letter-index` | 0 | 非负整数；逐字设置 | 确定字在轨道中的基础纵向序位。 |
| `--cvx-letter-x` | 0% | -60%–80%；逐字设置 | 调整每个字相对于侧轨的横向坐标。 |
| `--cvx-letter-y` | 0rem | -3rem–3rem；逐字设置 | 在基础序位上增加独立纵向偏移。 |
| `--cvx-letter-angle` | 0deg | -45deg–45deg；逐字设置 | 独立旋转字形，不改变字形宽高比例。 |
| `--cvx-rail-ink` | currentColor | 合法CSS颜色 | 仅设置装饰字颜色；正文颜色和字体由宿主继承。 |
| `--cvx-content-gap` | 1.25rem | 0.5rem–3rem | 控制正文各组之间的自然流间距。 |
| `--cvx-paragraph-gap` | 0.5rem | 0.25rem–1.5rem | 控制正文组内标题与段落间距。 |

- 所有字均为真实span，共享一个局部overflow:hidden装饰轨；只有装饰字采用绝对定位，正文全部处于自然流。
- 侧轨高度由正文撑开，不反过来限制正文；正文较短时允许裁切末端装饰字，不保证完整展示装饰单词。
- 装饰轨使用aria-hidden，正文姓名必须另以可编辑文本提供。
- 不使用伪元素、截图或字形拉伸；font-synthesis:none。示例仅为装饰字显式选择Arial，原子不绑定整页字体。
- 正文使用min-width:0、max-width:100%和overflow-wrap:anywhere；不得对正文添加固定高度或溢出裁切。
- 正式导出应解析并内联样式；局部内容可以增高，但整页遵循品类固定尺寸；简历超容量时停止导出并确认内容取舍，不能扩高或自行分页，不得缩小正文来通过验证。

```css
.cvx-scattered-letter-rail,.cvx-scattered-letter-rail *{box-sizing:border-box;min-width:0;max-width:100%}
.cvx-scattered-letter-rail{display:grid;grid-template-columns:minmax(0,min(var(--cvx-rail-width,6rem),30%)) minmax(0,1fr);column-gap:min(var(--cvx-rail-gap,1.25rem),5%);font-synthesis:none;overflow-wrap:anywhere}
.cvx-scattered-rail{position:relative;overflow:hidden;align-self:stretch;color:var(--cvx-rail-ink,currentColor);pointer-events:none;user-select:none}
.cvx-scattered-letter{position:absolute;display:block;max-width:none;left:var(--cvx-letter-x,0%);top:calc(var(--cvx-letter-index,0)*var(--cvx-rail-step,4.5rem) + var(--cvx-letter-y,0rem));font-size:var(--cvx-letter-size,6rem);font-weight:700;line-height:.9;transform:rotate(var(--cvx-letter-angle,0deg));transform-origin:center}
.cvx-scattered-content{display:grid;align-content:start;gap:var(--cvx-content-gap,1.25rem)}
.cvx-scattered-content h2,.cvx-scattered-content h3,.cvx-scattered-content p{margin:0}
.cvx-scattered-content header,.cvx-scattered-content section{display:grid;gap:var(--cvx-paragraph-gap,.5rem)}
.cvx-scattered-content address{font-style:normal}
.cvx-scattered-content a{color:inherit}
.cvx-scattered-content ul{margin:0;padding-inline-start:1.25em}
.cvx-scattered-content li+li{margin-block-start:.4em}
```

```html
<section class="cvx-scattered-letter-rail" data-css-atom="layout.scattered-letter-rail" aria-label="虚构设计师履历：散字侧轨示例" style="--cvx-rail-ink:#304fa2;--cvx-rail-width:6rem;--cvx-letter-size:6.5rem;--cvx-rail-step:4.6rem;max-width:44rem">
  <div class="cvx-scattered-rail" aria-hidden="true" style="font-family:Arial, sans-serif">
    <span class="cvx-scattered-letter" style="--cvx-letter-index:0;--cvx-letter-x:-18%;--cvx-letter-y:-.6rem;--cvx-letter-angle:-18deg">D</span>
    <span class="cvx-scattered-letter" style="--cvx-letter-index:1;--cvx-letter-x:28%;--cvx-letter-y:.2rem;--cvx-letter-angle:24deg">E</span>
    <span class="cvx-scattered-letter" style="--cvx-letter-index:2;--cvx-letter-x:-12%;--cvx-letter-y:.1rem;--cvx-letter-angle:13deg">S</span>
    <span class="cvx-scattered-letter" style="--cvx-letter-index:3;--cvx-letter-x:42%;--cvx-letter-y:-.2rem;--cvx-letter-angle:-12deg">I</span>
    <span class="cvx-scattered-letter" style="--cvx-letter-index:4;--cvx-letter-x:-24%;--cvx-letter-y:.3rem;--cvx-letter-angle:-26deg">G</span>
    <span class="cvx-scattered-letter" style="--cvx-letter-index:5;--cvx-letter-x:18%;--cvx-letter-y:0rem;--cvx-letter-angle:11deg">N</span>
  </div>
  <div class="cvx-scattered-content">
    <header>
      <h2>Hello! I’m Mira Vale</h2>
      <p>Editorial designer &amp; illustrator</p>
      <p>Fictional résumé sample. I develop readable publications and visual stories for community organisations.</p>
      <address><a href="mailto:mira.vale.editorial-and-accessibility@example.com">mira.vale.editorial-and-accessibility@example.com</a><br>Northbridge · Available for collaborative projects</address>
    </header>
    <section aria-label="Education">
      <h3>Education</h3>
      <p><strong>BA in Visual Communication</strong><br>Northbridge School of Art · 2018–2021</p>
      <p>Developed a final-year publication exploring public gardens through field notes, interviews and original illustrations.</p>
    </section>
    <section aria-label="Selected experience">
      <h3>Selected experience</h3>
      <p><strong>Editorial designer · Paper Orchard Studio</strong><br>2022–2025</p>
      <ul>
        <li>Designed a seasonal journal with reusable article layouts, editable captions and a consistent typographic hierarchy.</li>
        <li>Prepared accessible digital editions and coordinated revisions with writers, illustrators and production partners.</li>
        <li>Created a multilingual event guide for the fictional Northbridge Community Arts and Environmental Learning Partnership.</li>
      </ul>
    </section>
    <section aria-label="Working approach">
      <h3>Working approach</h3>
      <p>I begin with the content structure, test long headings and contact details, and leave room for translation rather than compressing the text.</p>
    </section>
  </div>
</section>
```
