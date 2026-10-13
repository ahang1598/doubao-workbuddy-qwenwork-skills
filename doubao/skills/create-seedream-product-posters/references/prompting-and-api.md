# Seedream 5.0 Pro Prompting and API

This reference summarizes the official image-generation behavior needed by this skill. Model IDs and limits can change; prefer the configured model when the environment overrides the default.

## Contents

1. Model choice
2. Prompt construction
3. Product-preservation pattern
4. Integrated-poster template
5. Exact-copy template
6. Revision prompts
7. API and local client
8. Failure handling

## 1. Model choice

Default:

```text
doubao-seedream-5-0-pro-260628
```

Use Seedream 5.0 Pro for a single finished poster because it supports:

- text-to-image;
- single- or multi-reference image generation;
- interactive editing;
- `1K` and `2K` output;
- PNG or JPEG output.

Pro accepts up to 10 reference images and generates one image per request. It does not use the sequential group-generation fields supported by Lite.

If Seedream is not callable and the user explicitly authorizes an available Image2/image-generation tool:

- use the product image as the authoritative reference;
- label any style image as style-only;
- generate one distinct asset per call;
- preserve the same truth lock, exact-copy, and QA rules;
- state the actual model/tool in the final delivery;
- never imply that a fallback output came from Seedream.

The default endpoint is:

```text
POST https://ark.cn-beijing.volces.com/api/v3/images/generations
```

## 2. Prompt construction

Use concise, coherent natural language. Official guidance favors:

```text
subject + action + environment + style/color/light/composition
```

For commercial posters, expand it to:

```text
task + reference role + product truth lock + campaign idea + scene +
two product-specific devices + interaction/material proof + anti-template statement +
six-band layout + layout signature + density budget + three anchors +
exact text with claim provenance + art direction + invariants
```

Put exact visible text in double quotation marks.

Before prompting, make a complete copy manifest:

```text
output_language="zh-CN" or "en"
eyebrow="..."
headline="..."
support="..."
benefits=["...","...","..."]
badge="..."
requires_cta=true or false
CTA="..." or CTA=none
closing_slogan="..." or closing_slogan=none
footer="..." or footer=none
claim_provenance.support="visible" / "user-supplied" / "omitted"
claim_provenance.benefits=["visible","user-supplied","omitted"]
```

The prompt must say that no text outside this manifest may appear. Leaving eyebrow or footer unspecified invites plausible but unauthorized microcopy.

For English posters:

- state “all poster-overlay copy is English” and “no Chinese overlay copy”;
- keep source package labels and registered wordmarks unchanged even when they use another language;
- use idiomatic market-facing English, not literal Chinese syntax;
- define capitalization for every region: Title Case, ALL CAPS, or sentence case;
- keep a headline to 1–8 words, support to 4–16 words, each benefit to 1–6 words, CTA to 1–4 words, and publicity slogan to 2–10 words;
- request word-boundary line breaks and prohibit orphaned articles/prepositions;
- select a Latin type personality rather than requesting a Chinese Song-style or calligraphic font.

Classify intent before writing the manifest:

- conversion poster: `requires_cta=true`; route the CTA to the requested action or buying mechanism;
- publicity, brand-image, launch-atmosphere, exhibition, or announcement poster: `requires_cta=false`; use no button, arrow, search bar, purchase instruction, or pseudo-interactive control. Close with a non-interactive slogan or brand line instead.

Do not use the generic CTA `即刻探索`. Vary CTA wording across unrelated conversion posters.

Treat source-package text separately from poster-overlay copy:

- preserve visible product labels and branding as product truth;
- do not count them as overlay-manifest violations;
- forbid the model from moving package text into the background, headline, badges, or CTA;
- if source-package text is too small to read, preserve its appearance without “correcting” or expanding it.

Describe the use case explicitly: “竖版9:16电商商品海报” is more controllable than “好看的图”.

State the commercial completeness target explicitly:

```text
画面不是极简产品渲染，而是一张完成度高的商业海报：具备明确主标题、
商品英雄区、卖点证明、互动效果、环境纵深，以及与海报类型匹配的底部收口。
转化型使用CTA；宣传型不使用CTA，以品牌口号或主题落款收口。
```

Do not write a comma-separated pile of aesthetic buzzwords. Explain spatial relationships and importance.

Before writing the final prompt, name:

- two visual devices derived from the specific product’s form, material, use, or desire;
- one interaction or material proof;
- one foreground depth device;
- one bottom closure device;
- one template signature to avoid.

Do not generate the generic triptych `top-centered headline + centered product + three equal bottom cards`. A pleasant lifestyle background does not excuse a transferable layout.

For a batch, write prompts independently. Do not copy one prompt and replace only the product, palette, and headline. Change the scene metaphor, composition axis, type system, module shapes, foreground language, and depth cues.

## 3. Product-preservation pattern

Start image-to-image prompts with a strong reference contract:

```text
以输入图片中的商品作为唯一核心商品。严格保留商品的
[轮廓、比例、材质、主色、包装结构、瓶盖/接口、标签位置、可见品牌文字]，
不要重绘、替换或发明品牌与包装信息。只升级拍摄环境、背景、光影与海报排版。
商品外观的其余部分保持不变。
```

List only facts visible in the input. If the logo is small or partly hidden, say “保持原样，不补写看不清的文字”.

Add a negative-geometry sentence for risky shapes:

```text
保持[凹槽/开口/透明间隙/端口/屏幕边缘]为空，不把它填成凸起、按钮、镜头、
装饰件或额外商品；可见控制件严格为[数量]个。
```

Use one hero product unless the campaign clearly requires a set. Explicitly forbid duplicates:

```text
画面中只出现一个完整商品主体，不复制、不拼接、不增加变体包装。
```

Add one category clause when relevant:

```text
保温杯：严格保留瓶盖、肩部、瓶身锥度、金属拉丝、接缝和底部。热或冷选择一个主隐喻；
若同时表达冷热，必须做清晰的左右/上下双区，不让蒸汽与冰块无方向地缠绕同一表面。
```

```text
连衣裙：严格保留吊带路径、领口、腰线、缝线、印花重复、裙摆和透明度。
必须有可信的衣架/人台/隐形人台支撑，或明确的悬挂结构；不增加模特、配色或第二件衣服。
```

```text
跑鞋：商品数量与输入完全一致；严格保留鞋面、鞋带路径、鞋舌、鞋口、中底、外底、
鞋头和后跟。运动只发生在环境、影子和版式中，不生成额外鞋、脚、logo或技术结构。
```

```text
便携音箱：严格保留网罩纹理、机身比例、端盖、按键、接口、挂绳五金、脚垫和可见logo。
声场用从网罩/机身发出的波面、振动光或环境响应表现；禁止漂浮音符和卡通五线谱。
```

## 4. Integrated-poster template

Adapt the brackets and remove unused layers:

```text
设计一张竖版9:16的中文商业商品海报，用于[渠道/活动]。

以输入图片中的[商品类别]作为唯一核心商品。严格保留它的[商品真值锁]；
不改变商品结构、比例、材质、主色、标签和可见品牌信息，只优化拍摄质感、
场景、光影和版式。

主题是“[主题]”。面向[受众/使用时刻]，传达[单一价值]。
场景为[具体场景与视觉隐喻]，使用[不超过三类道具]，道具只用于衬托商品。
产品专属视觉装置为[装置1]与[装置2]，分别来自商品的[形态/材质]和[使用/互动]；
可见证明为[互动或材质证据]，前景用[纵深装置]形成空间层次。
明确避开[模板签名]，不得套用顶部居中大字、中央商品、底部三等分卡片。

版式签名为headline_axis=[...]、product_axis=[...]、bottom_system=[...]。六段布局：
- 顶部[百分比]放置[品牌/眉题]；
- [百分比]放置主标题“[4–10字]”，它是最大文字；
- [百分比]放置副标题“[8–18字]”；
- [百分比]放置一个主证明模块和最多两个次级说明：“[卖点1]”“[卖点2]”“[卖点3]”；
- 中下部由商品占据[宽度/高度比例]，轮廓完整，标签无遮挡；
- 若为转化型，底部放置徽章“[短徽章]”和主按钮“[CTA]”，保留安全边距；
- 若为宣传型，底部不得出现按钮、箭头或行动指令，只放非交互口号“[宣传收口]”。

信息密度为[6–8 / 8–11 / 11–15]个语义模块。三个注意力锚点依次是
[主标题]、[商品]、[CTA/价格/宣传收口]。视觉节奏为小品牌、超大标题、中等证明、
超大商品、中等行动或口号、紧凑收口。使用[前景/互动/环境/信息]层制造纵深，
但商品轮廓和文字底面保持干净。

整体采用[视觉母版]：主色[主色]，辅色[辅色]，点缀色[点缀色]；
[光线方向与软硬]，[材质和背景]，[镜头/景深]。
商业广告摄影质感，层级清晰，文字与商品都易读，留白受控。

必须避免：商品变形、标签错位、额外logo、重复商品、乱码、错别字、
文字压住商品、无关装饰、廉价发光、物理矛盾效果、漂浮音符、通用速度线、
过度拥挤，以及任何无来源的功能/性能描述。副标题与卖点的来源为[逐条填写visible或
user-supplied]；没有来源的项目必须删除。除明确指定的文字外不生成其他文字。
```

For an English poster, replace the opening and copy instructions with:

```text
Design a polished vertical 9:16 English-language commercial product poster for [channel/campaign].
All poster-overlay copy must be English and must exactly match the manifest below.
Preserve physical product labels and registered wordmarks in their original language.
Use word-boundary line breaks. Do not add Chinese copy, filler text, lorem ipsum, or unlisted microcopy.

Exact copy:
eyebrow="[...]"
headline="[...]" ([Title Case / ALL CAPS / sentence case])
support="[...]"
benefits=["[...]","[...]","[...]"]
badge="[...]"
requires_cta=[true/false]
CTA="[...]" or none
closing_slogan="[...]" or none
footer="[...]" or none
```

## 5. Exact-copy template

Use when deterministic typesetting will follow:

```text
生成一张竖版9:16商品广告主视觉，不生成价格、规格、长段文字或随机字符。
严格保留输入商品的所有可见设计。为后续排版预留以下干净区域：
顶部或侧边[位置]留出主标题区；[位置]留出一个主证明模块和最多两个次级说明区；
底部[位置]留出CTA与服务说明区；若为宣传型则留出口号与品牌收口区，禁止按钮和箭头。预留区使用[纯净渐变/雾面玻璃/浅色纸张]
并保持足够对比度。只生成商品、场景、光影、装饰框和空白卡片。
版式不得同时使用顶部居中标题、中央商品和底部三等分卡片。
```

Do not ask the model to generate lorem ipsum, fake Chinese glyphs, or fake Latin microcopy.

## 6. Revision prompts

Change only one failed dimension per revision.

### Restore product fidelity

```text
保持画面构图与背景不变。把商品恢复为输入参考图中的准确外观：
[truth lock]。不要改动标签、颜色、比例或包装结构，画面中仍只有一个商品。
```

### Improve hierarchy

```text
保持商品和场景不变。简化排版：主标题放大为当前的1.35倍；
副标题与卖点缩小，删除无关小字；CTA移到下方安全区并增强对比。
```

For publicity posters, replace the final sentence with:

```text
副标题与卖点缩小，删除无关小字；移除所有按钮、箭头和行动指令，
底部仅保留非交互品牌口号，并把场景或舞台自然延伸到原按钮区域。
```

### Reduce clutter

```text
保持商品、主标题和CTA不变。移除[具体道具/贴纸]，把背景简化为[场景]，
增加商品轮廓四周的留白。
```

### Correct text

```text
保持商品、背景、颜色和布局不变。只把[位置]的文字改为“[精确文字]”，
不要改动其他任何区域。
```

## 7. API and local client

The request body uses:

```json
{
  "model": "doubao-seedream-5-0-pro-260628",
  "prompt": "...",
  "image": "data:image/png;base64,...",
  "size": "2K",
  "output_format": "png",
  "response_format": "url",
  "watermark": false
}
```

`image` accepts an accessible URL or a Base64 data URI. The official single-input limits include:

- formats: JPEG, PNG, WebP, BMP, TIFF, GIF, HEIC, HEIF;
- maximum size: 30 MB;
- pixel dimensions greater than 14 px;
- total pixels no more than 36 million;
- aspect ratio between 1:16 and 16:1.

For Pro, prefer the logical size `2K` and state `9:16` in the prompt. Common 2K mapping for 9:16 is `1584x2816`.

Returned URLs expire after 24 hours. Download them immediately. The bundled script does this.

Run:

```bash
export ARK_API_KEY="..."
python3 scripts/seedream_generate.py \
  --image "/absolute/product.png" \
  --prompt-file "/absolute/poster-prompt.txt" \
  --output "/absolute/poster.png"
```

Override the endpoint or model with:

```bash
export SEEDREAM_BASE_URL="https://ark.cn-beijing.volces.com/api/v3"
export SEEDREAM_MODEL="doubao-seedream-5-0-pro-260628"
```

Never commit an API key, place it in the prompt, or echo it.

## 8. Failure handling

- `401/403`: stop and request valid environment configuration; do not retry.
- `429`: retry with exponential backoff.
- `5xx`: retry up to the script limit.
- empty `data`: report the returned error object.
- URL download failure: preserve the response metadata and retry download only.
- content moderation failure: revise the concept; do not bypass safety controls.
- wrong logo/product: strengthen the reference contract or use exact-copy/compositing mode.
- illegible small copy: shorten it or move to deterministic typesetting.

Primary official references:

- Volcano Engine image-generation API: `https://www.volcengine.com/docs/82379/1541523`
- Volcano Engine Seedream prompt guide: `https://www.volcengine.com/docs/82379/1829186`
- ByteDance Seedream 5.0 model overview: `https://seed.bytedance.com/en/blog/deeper-thinking-more-accurate-generation-introducing-seedream-5-0-lite`
