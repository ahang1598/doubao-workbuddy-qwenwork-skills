---
name: apple-keynote-product-video
description: Generate, adapt, or improve premium product-commercial video prompts with modern minimalist keynote aesthetics, product strategy, timed shot design, camera movement, material choreography, typography, lighting, sound design, continuity, and negative constraints. Use when the user asks for 苹果发布会级, 发布会质感, 极简产品广告, 科技感产品片, 3D 产品宣传片, 产品概念片, 电商产品视频, or wants to adapt an existing shot-by-shot commercial prompt to another product.
---

# Apple Keynote Product Video

Create a copy-ready video-generation prompt that feels restrained, engineered, tactile, and premium. Interpret “苹果发布会级” as a quality bar and visual-language reference. Do not copy Apple products, trademarks, exact campaigns, proprietary assets, or imply Apple authorship or endorsement.

## Guide the customer first

When the Skill is invoked without enough product information, begin with a short intake message instead of generating a generic prompt.

Ask the customer to provide these three minimum inputs:

1. 商品名与品牌名
2. 产品图：prefer one clean front or three-quarter product image; recommend front, side, detail, and packaging images when available
3. 核心卖点：ask for the single benefit the video should make memorable

Then offer these optional inputs:

- 视频时长：6–8 秒、10–15 秒或 20–30 秒
- 画面比例与平台：16:9、9:16 or 1:1; Douyin, Xiaohongshu, Tmall, JD, website, launch event
- 产品材质、颜色、结构和需要重点展示的细节
- 目标人群与使用场景
- 需要出现的品牌文案、价格、活动信息或 official slogan
- 参考视频、参考画面或 desired visual direction
- 是否需要人物、旁白、音乐、字幕或 only sound effects
- Target video model, if already chosen

Use this customer-facing template in the customer’s language:

> 请把以下信息发给我，我就能开始制作：
>
> **必须提供**
> 1. 商品名 / 品牌名
> 2. 产品图（建议正面或 45° 清晰图；有侧面、细节和包装图更好）
> 3. 最想突出的一个核心卖点
>
> **可选提供**
> - 视频时长与比例
> - 发布平台
> - 产品材质、颜色和重点细节
> - 目标人群与使用场景
> - 必须出现的文案或活动信息
> - 参考视频或喜欢的视觉风格
> - 是否需要人物、配乐、旁白或字幕
>
> 如果暂时没有完整信息，也可以只发“商品名＋产品图＋核心卖点”，其余由我按发布会级产品广告标准补齐。

Do not repeat questions whose answers are already present in the conversation or visible in attached images. If the customer supplies the three minimum inputs, proceed without another approval round and infer optional items conservatively. If the product image is missing but the product is visually distinctive, explain briefly that a reference image will materially improve shape, color, logo, and detail consistency; still proceed when the customer asks to use defaults.

If the customer provides only a product name, ask for the image and primary selling point. If the customer provides an existing prompt and asks only for adaptation, treat that prompt as sufficient structure and ask only for missing product-specific facts that would otherwise require invention.

## Define the product story

Extract:

- Product and brand
- Recognizable silhouette, materials, colors, and signature details
- One primary benefit and up to two supporting benefits
- One visually demonstrable function
- Audience and usage context
- Duration, aspect ratio, platform, and target video model if provided
- Required copy, language, logo, packshot, reference image, or source prompt

Translate abstract selling points into visible evidence:

- “耐用” → controlled impact, surface resilience, firm mechanical action
- “保温/保冷” → condensation, ice, vapor contrast, stable liquid state
- “轻盈” → effortless lift, suspended balance, soft shadow response
- “精准” → aligned components, measured movement, exact locking point
- “柔和” → diffused light, slow material deformation, quiet contact
- “高效” → one decisive action followed by an immediate clean result

Choose one hero idea. Do not demonstrate every feature in one short film.

After the minimum inputs are available, do not pause for missing non-critical details. Infer conservative defaults and keep unsupported claims generic. Never invent certifications, performance figures, health claims, awards, official slogans, or unprovided product features.

Default to:

- 15 seconds, 6 shots, 16:9, 24 fps
- 9:16 when the user clearly targets Douyin, Reels, or Shorts
- One hero product in a white, cool-gray, or deep-black studio
- Slow controlled motion plus one decisive functional action
- Sparse neutral sans-serif typography
- No people, dialogue, voiceover, or background music unless requested

## Choose duration and rhythm

Allocate time before writing shots:

- 6–8 seconds: 3–4 shots, one reveal, one action, one packshot
- 10–15 seconds: 5–7 shots, form reveal, detail, action, benefit, packshot
- 20–30 seconds: 7–10 shots, allow one use context and two supporting details

Use this default arc:

`悬浮定场 → 轮廓揭示 → 材质微距 → 功能动作 → 利益点确认 → 品牌收尾`

For a supplied source prompt, preserve its shot count, ordering, cadence, and sound rhythm unless the product requires a different physical action. Replace product-specific mechanics rather than merely changing nouns.

## Design every shot

For each shot, include only details the generator can render:

1. Time range or approximate duration
2. Framing and camera movement
3. Product position, orientation, and exact action
4. Lighting, surface, and background behavior
5. Transition or continuity cue
6. Synchronized sound
7. On-screen text when needed

Prefer precise language:

- Camera: slow dolly-in, controlled 20-degree orbit, top-down rotation, macro lateral track, locked-off packshot
- Lens: macro detail, shallow depth of field, compressed telephoto profile, clean orthographic-like top view
- Light: narrow rim light, moving specular highlight, soft volumetric beam, controlled reflection, gradient shadow
- Physics: droplets condense, lid rotates and locks, button compresses and rebounds, fabric flexes, liquid settles

Avoid vague phrases such as “高级感拉满,” “电影级震撼,” or “充满科技感” without visible instructions.

## Preserve identity and continuity

Treat the product as one immutable hero asset across the film:

- Keep logo spelling, label placement, proportions, color, material, handle, lid, buttons, openings, and accessories unchanged.
- State which side faces the camera at the beginning of each shot.
- Carry motion direction across cuts; if the product exits frame right, continue the next motion from the left only when intentionally matched.
- Use the final pose of one shot as the initial pose of the next when the model supports continuous clips.
- If a reference image is supplied, instruct the model to preserve its exact silhouette, colorway, surface finish, and branding.
- Do not let text, hands, liquids, or effects obscure signature product details.

For multi-clip generation, make each clip independently renderable while repeating the minimum identity anchors needed for consistency.

## Direct product motion

Use motion that expresses the benefit:

- Reveal: emerge from shadow, rotate into edge light, slide through a narrow light plane
- Assembly: align, insert, rotate, lock, click
- Performance: repel, seal, pour, cool, compress, rebound, clean
- Resolution: stop motion decisively, let reflections settle, hold the packshot

Keep motion smooth, mechanically legible, and physically plausible. Use one action per shot. Do not make the product melt, morph, duplicate, deform, or float without controlled support logic unless the concept explicitly requires surrealism.

## Design sound as motion feedback

Attach sound cues to visible events:

- Space: environmental airflow, quiet room tone, soft air cut
- Material: brushed-metal glide, glass touch, rubber friction, fabric sweep
- Mechanism: click, snap, lock, rebound, pressure release
- Product use: subtle pour, ice contact, mist, clean wipe
- Typography: restrained electronic tick or two light clicks
- Closing: one short recognizable sonic mark

Keep effects dry, close, and restrained. Use “咔哒” or “啵” only when material physics justify it. Do not add music unless requested. Never describe an unheard sound without a corresponding visible cause.

## Write restrained copy

Use no more than three copy beats:

1. Product or brand name
2. Demonstrated benefit
3. Closing brand proposition

Keep lines short:

- Benefit: 2–5 English words or 4–10 Chinese characters
- Closing line: 3–7 English words or 6–14 Chinese characters

Connect copy to what the viewer just saw. Preserve supplied slogans exactly. Otherwise treat proposed wording as creative copy, not an official slogan. Prefer plain confidence over inflated claims.

## Handle generated text safely

Video models often distort typography. Choose one of these approaches:

- If exact branding matters, generate clean footage without embedded text and specify text as a post-production overlay.
- If the user explicitly wants in-model text, quote each line exactly and require stable spelling, but warn only when useful that post-production compositing is more reliable.
- Keep the product logo visible only when a reliable reference image is supplied; otherwise describe a clean logo-safe area rather than inventing a mark.

## Add negative constraints

End the prompt with a compact negative block tailored to the product. Include relevant constraints such as:

`避免：产品变形、比例漂移、Logo 拼写错误、标签跳动、部件增减、材质塑料感、液体穿模、手柄错位、随机粒子、过度眩光、杂乱背景、镜头抖动、快速乱切、无关文字、人物或手部入镜。`

Do not dump a generic keyword list. Remove constraints that do not apply.

## Output modes

Infer the needed mode:

- Prompt only: return one complete copy-ready generation prompt.
- Rewrite: return the fully rewritten prompt, not an edit list.
- Shot plan: add timestamps and shot numbers.
- Production pack: provide a master prompt, per-shot prompts, negative prompt, copy list, and sound list.
- Variants: create clearly differentiated concepts such as white-studio precision, dark-studio engineering, or lifestyle minimalism; do not make cosmetic word swaps.

Unless the user asks for analysis, use chronological short paragraphs and interleave:

`时间/画面/镜头 → 音效 → 屏幕文字`

Append one compact parameter line when useful:

`建议参数：15 秒｜16:9｜4K｜24fps｜写实产品广告｜稳定运镜｜真实材质｜无人物｜文字后期叠加`

If a specific video model is named, adapt terminology to that model’s known prompt style without claiming unsupported controls.

## Quality gate

Revise before responding until all are true:

- The first two seconds establish a recognizable product silhouette or action hook.
- One primary selling point drives the entire film.
- The total shot timing matches the requested duration.
- Each shot contains one legible action and a motivated camera move.
- Product identity remains consistent across shots.
- Transitions preserve spatial and motion continuity.
- Every sound has a visible cause.
- Copy is sparse, readable, and tied to demonstrated evidence.
- Claims are supported or safely generic.
- Negative constraints target likely generation failures.
- The last frame works as a clean, holdable brand packshot.
