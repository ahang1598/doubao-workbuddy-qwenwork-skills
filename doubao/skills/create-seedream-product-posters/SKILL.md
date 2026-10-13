---
name: create-seedream-product-posters
description: Turn one casual product photo into a planned, polished Chinese or English commercial poster with Seedream 5.0 Pro. Use when the user asks to 策划商品海报、商品图生海报、电商主图、促销长图、新品发布图、英文海报、English product poster、campaign poster, or when a phone snapshot needs theme planning, localized copy hierarchy, composition, Seedream prompting, generation, and visual QA.
---

# Create Seedream Product Posters

Transform one casual product photo into a campaign concept and a finished vertical Chinese or English poster. Treat the product as truth, select a style from the distilled reference system, and generate with Seedream 5.0 Pro without silently substituting another model.

## Read the required references

Read these files before planning or generating:

1. Read [reference-grammar.md](references/reference-grammar.md) to extract the reference composition, density, rhythm, and richness.
2. Read [style-atlas.md](references/style-atlas.md) to choose the visual family.
3. Read [layout-system.md](references/layout-system.md) to construct the grid and copy hierarchy.
4. Read [prompting-and-api.md](references/prompting-and-api.md) before writing the Seedream prompt or invoking the API.
5. Read [qa-rubric.md](references/qa-rubric.md) before accepting a result.

When the category or campaign structure is ambiguous, read [universal-router.md](references/universal-router.md) first, then [reference-corpus.md](references/reference-corpus.md). Route by product signals and buying mechanism rather than visual color alone.

## Operating contract

- Accept one product snapshot as the minimum input.
- Infer a reasonable commercial direction when the user gives no campaign brief. Ask only when a missing fact would make the claim, price, or brand legally risky.
- Plan the theme before generating. Show a compact concept card unless the user explicitly requests direct generation.
- When references are supplied, imitate their design grammar—not their brand assets: extract macro bands, hierarchy, density, rhythm, scene depth, and module language before selecting a style.
- Use `doubao-seedream-5-0-pro-260628` by default. Allow `SEEDREAM_MODEL` or `--model` to override it because model IDs evolve.
- If Seedream is unavailable and the user explicitly permits Image2 or another available image model, use that model and disclose the actual model in the delivery. Never call a fallback result “Seedream”.
- Use the input photo as the image reference. Never recreate the product from text alone when a reference exists.
- Preserve the product’s silhouette, proportions, material, base color, label placement, logo, closure, visible accessories, and package count.
- Never invent certifications, endorsements, discounts, prices, ingredients, performance numbers, warranties, or brand claims.
- Never add a third-party logo or imitate a living artist. Translate references into generic visual attributes.
- Generate in `9:16` at `2K` by default for mobile posters. Change the ratio only when the user specifies another channel.
- Set one output language for the complete overlay copy: `zh-CN` or `en`. Use exact localized copy in double quotation marks and keep embedded text concise. Preserve physical product-label text in its source language.
- Treat every visible text region as exact copy, including eyebrow, badge, optional CTA, closing slogan, and footer. If a region should be blank, explicitly say it contains no text.
- Inspect every result. Do not deliver a poster that fails a hard rejection condition in the QA rubric.
- For a batch, assign a different visual system to each product unless the user explicitly requests one campaign system. Do not reuse the same dark portal, three-card rail, circular platform, metallic headline, or CTA frame across every item.
- Make the scene lively through purposeful foreground, midground, background, light, material, and information layers. “Rich” means layered and directed, not random stickers or extra claims.
- Treat `top-centered headline + centered product + three equal bottom cards` as a banned generic triptych. A scenic backdrop and three icon cards do not constitute a campaign idea.
- Derive at least two recognizable visual devices from the specific product’s form, material, use, or desire. A different background color does not count.
- Every factual support line and benefit needs provenance: directly visible or explicitly user-supplied. A plausible category claim is still an unsupported claim.

## Workflow

### 1. Audit the product photo

Identify and record:

- product category and likely usage scene;
- dominant and accent colors;
- geometry, camera angle, and material;
- exact visible brand and label text;
- features that must not change;
- photo defects to repair: clutter, perspective, glare, blur, crushed shadows, or color cast;
- sensitive unknowns: price, specification, ingredient, promotion, or trademark status.

Create a **product truth lock** of 4–8 visible facts. Use only visible evidence or user-provided facts.

Also create a **negative-geometry lock** for details the model must not fill in or reinterpret: openings, recesses, transparent gaps, flat lids, screen edges, ports, holes, empty spaces between parts, and the exact number of controls or lenses. These details are frequent hallucination sites.

For transparent drinks, also lock cup silhouette, lid type, liquid color and fill level, label position, ingredient visibility, ice/slice plausibility, and the distinction between the 3D hero product and flat package printing.

For mascot/IP products, assign explicit roles: one main 3D character, package-printed character allowed, optional one flat sticker/doodle, and no additional 3D duplicates.

If the product occupies less than roughly 15% of the frame, is heavily occluded, or is too blurry to identify, request a closer photo before paid generation.

Classify input quality:

- `A clean packshot`: preserve angle unless a better view is visibly supported.
- `B usable casual photo`: repair background, crop, glare, and perspective while preserving the product.
- `C weak snapshot`: use conservative frontal/three-quarter presentation and avoid inventing hidden structure.
- `D unusable`: request another image when identity or structure cannot be reliably recovered.

Never let a weak snapshot lower the poster’s art direction. Upgrade scene, light, scale, and information design around the product while keeping uncertain product details conservative.

For `C weak snapshot` inputs, separate **repairable capture defects** from **immutable product facts**:

- freely replace clutter, glare, noise, color cast, weak lighting, and accidental crop;
- cautiously normalize tilt and perspective only when the visible silhouette supports it;
- never invent the hidden back, sole, dispenser, label side, closure interior, or unseen accessories;
- build richness in the scene, interaction, typography, and depth—not by redesigning the product.

Apply category-specific weak-input locks when relevant:

- **transparent reflective bottle:** lock outer wall, inner liquid boundary, fill level, label plane, cap/dropper, glass base, and empty transparent gaps; add a calm halo and edge light so transparency stays legible;
- **footwear:** lock the exact product count, upper, tongue/opening, lace path, midsole, outsole, toe and heel profile; keep motion in the environment and never generate an unsupported second shoe, foot, logo, air unit, or sole technology;
- **soft tube/pouch:** lock top crimp, flexible shoulder, wrinkle pattern, label plane, cap diameter and closure type; preserve soft deformation and never harden it into a bottle, jar, pump, or box.
- **vacuum bottle or thermos:** lock cap height, shoulder transition, body taper, metal grain, seam, base and any printed mark. Use either one dominant temperature metaphor or a clearly separated hot/cold diptych; never wrap steam and ice around the same undivided surface. Do not reveal insulation layers or claim hours, steel grade, leakproofing, one-touch opening, capacity, or burn protection unless supplied.
- **dress or apparel:** lock exact garment count, neckline, strap path, back structure, waist, seams, hem, print repeat and fabric translucency. A floating dress needs a plausible hanger, mannequin, support, or intentional invisible-form studio treatment. Do not invent a model, second colorway, “slimming,” “breathable,” or “multiway” behavior.
- **portable speaker:** lock grille weave, body proportions, end caps, buttons, ports, strap hardware, feet and visible logo. Build acoustic energy from wavefronts, vibration, reflected light, or environmental response tied to the speaker geometry; never use disconnected floating music-note clip art. Do not claim IP rating, play time, TWS, power, drivers, or surround sound unless supplied.

### 2. Extract the target design grammar

If reference posters exist, analyze them with [reference-grammar.md](references/reference-grammar.md). Record:

- six vertical bands and their approximate height shares;
- first, second, and third attention anchors;
- product scale and overlap behavior;
- module count and density level;
- container language, type personality, and accent effects;
- foreground, interaction, environment, and information layers;
- one recognizable pattern to keep and two elements to change so the result is original.

If no reference is supplied, use the same grammar sheet against the chosen style-atlas family.

### 3. Build the one-line strategy

Complete this sentence:

> For `[audience/use moment]`, present `[product]` as `[single value]` through `[visual metaphor or scene]`, prompting `[action]`.

Choose one primary objective:

- launch or premium perception;
- feature explanation;
- seasonal refreshment;
- daily-use conversion;
- price promotion;
- culture or emotion;
- social sharing or IP excitement.

Do not combine more than two primary objectives.

Before choosing aesthetics, record `form / material / use / desire`, select one buying mechanism, and set density `D1 / D2 / D3` with [universal-router.md](references/universal-router.md). The buying mechanism determines the proof; the density determines module count; only then should the style family determine visual expression.

Then define an **anti-template contract**:

- two category-specific visual devices derived from product truth;
- one interaction or material proof;
- one purposeful foreground depth device;
- one deliberate bottom closure;
- one template signature that this concept explicitly avoids.

Also declare `headline_axis`, `product_axis`, and `bottom_system`. The combination `top-centered / centered / three-equal-cards` is not generation-ready.

Also set:

- `output_language=zh-CN` for Chinese posters or `output_language=en` for English posters;
- target market or channel when supplied;
- one language for all poster-overlay copy. Do not produce an accidental half-Chinese, half-English hierarchy. Brand names and physical package labels may remain in their original language.

### 4. Choose one visual family

Select one family from the style atlas. Mix at most one secondary family and state the split, such as `科技旗舰 80% + 促销会场 20%`.

Match style to product truth:

- reflective metal, electronics, cars → tech flagship;
- cosmetics, beauty devices, gifts → soft premium or oriental quiet luxury;
- makeup with a visible finish or authorized model → portrait-product dual proof;
- cold drinks, soda, fruit products → refreshing beverage;
- coffee, snacks, food, home goods → daily lifestyle;
- packaged food or breakfast sets → pack-result-routine triangle;
- shoes or sports gear → sport energy;
- collectibles and youth products → playful IP;
- multi-SKU discounts → promotion arena;
- multi-SKU discounts with prices → SKU hierarchy pyramid plus mandatory exact-copy pricing;
- personality-led content → social story collage.

### 5. Write the copy deck

Use this default hierarchy.

For Chinese:

1. brand or campaign eyebrow: 2–8 Chinese characters;
2. hero headline: 4–10 Chinese characters;
3. supporting line: 8–18 Chinese characters;
4. three benefits: each 4–8 characters, optionally one 8–14 character explanation;
5. one badge: 2–6 characters;
6. for conversion-led posters only, one CTA: 4–8 characters;
7. for publicity, brand-image, launch-atmosphere, exhibition, or announcement posters, no CTA; use one non-interactive closing slogan, brand line, or verified event line instead;
8. up to three trust items: each 4–6 characters.

For English:

1. eyebrow: 1–6 words;
2. hero headline: 1–8 words, preferably 2–6;
3. supporting line: 4–16 words;
4. three benefits: each 1–6 words;
5. badge: 1–4 words;
6. conversion CTA only: 1–4 words;
7. publicity closing slogan: 2–10 words;
8. trust items: each 1–5 words.

Write idiomatic English rather than translating Chinese word for word. Prefer active, concrete phrases. Use Title Case or all caps only for short display text; use sentence case for support and benefit copy. Avoid splitting articles, prepositions, phrasal verbs, or brand/model names across lines. Use no more than two English type personalities: condensed/geometric sans for tech and promotion, high-contrast serif plus neutral sans for premium/lifestyle, or chunky display plus bold sans for playful campaigns.

Use fewer layers for premium styles and more layers only for promotion or playful-IP styles.

For each support line and benefit, record `claim_provenance` as `visible`, `user-supplied`, or `omitted`. Visible means the claim can be verified from the supplied photograph itself; it does not mean the claim is merely typical for the category. Use neutral descriptive copy or omit the line when provenance is missing.

First classify the poster as `publicity` or `conversion`. Publicity posters do not need a CTA: set `requires_cta=false`, keep `copy_manifest.cta` empty, and close the bottom with a non-clickable slogan or brand line. Do not add buttons, arrows, search bars, “learn more,” “buy now,” or other action instructions merely to fill space. Conversion posters set `requires_cta=true` and use a concrete action matching the buying mechanism, such as `立即了解`, `查看详情`, `立即选购`, `马上出发`, `即刻来一杯`, or a user-supplied campaign CTA.

Never use the generic CTA `即刻探索` or its lazy English equivalent `Explore Now`, even in a conversion poster. Avoid repeating one CTA across unrelated posters.

If the user did not supply verified price or campaign terms, omit them. Never fabricate a placeholder price inside a final generation.

### 6. Produce a concept card

Return this compact structure before the first generation:

```text
主题：
一句话策略：
视觉母版：
商品真值锁：
输出语言与市场：zh-CN / en；目标市场或渠道
海报类型：宣传型 / 转化型；requires_cta=true/false
核心文案：眉题 / 主标题 / 副标题 / 3卖点 / 徽章 / CTA或宣传收口
声明来源：副标题与每条卖点分别标注 visible / user-supplied / omitted
场景与道具：
产品专属装置：至少2项；互动或材质证据；前景纵深装置
版式：六段高度占比、文字区、商品区、促销区、底栏位置
版式签名：headline_axis / product_axis / bottom_system；明确禁止复用的模板
信息密度：模块数 / 强中弱层级 / 视觉锚点顺序
丰富度：前景 / 商品 / 互动 / 环境 / 信息五层
色彩与光影：
生成规格：
```

When the user asks for multiple concepts, produce three genuinely different directions: premium, conversion, and social. Do not make three color variants of one layout.

For multiple products, show a **batch style matrix** before generating:

```text
商品 / 主题 / 明暗基调 / 版式轴 / 字体性格 / 场景材质 / 信息密度 / 禁止复用元素
```

Require every pair of posters to differ in at least four of these six dimensions:

1. high-key versus low-key;
2. palette;
3. vertical, asymmetric, diagonal, or collage layout axis;
4. serif, geometric, condensed, editorial, or display type personality;
5. scene and material system;
6. information density and motif language.

Read [execution-patterns.md](references/execution-patterns.md) for proven combinations and anti-template lessons.

Do not generate until the concept card passes this preflight:

- one clear promise;
- one dominant headline;
- product occupies at least 45% of width or 32% of height unless the scene is intentionally narrative;
- 7–10 modules for standard commercial posters, 11–15 only for promotion/IP/social;
- at least three of the five richness layers;
- at least two category-specific devices and one interaction/material proof;
- one foreground depth device and one deliberate bottom closure;
- every factual support line and benefit has visible or user-supplied provenance;
- layout is not the banned generic triptych;
- calm contrast surfaces behind all important copy;
- bottom 12–18% reserved for conversion/trust when conversion is the objective.

For final or paid generation, make this gate deterministic:

1. Run `python3 scripts/preflight_check.py --write-template /absolute/path/concept.json`.
2. Replace every template value with the audited product facts and planned poster values.
3. Run `python3 scripts/preflight_check.py /absolute/path/concept.json`.
4. Do not generate until the command prints `PASS`.

The checker rejects missing truth locks, invalid density/module combinations, incomplete bands, fewer than three anchors or richness layers, undersized products, missing claim provenance, fewer than two product-specific devices, an incomplete anti-template contract, the generic top-headline/center-product/bottom-triptych signature, unsupported numeric claims, a missing headline, a missing CTA when conversion requires one, a CTA mistakenly added to a publicity poster, absent bottom closure, and unusable input quality.

### 7. Compose the Seedream prompt

Write one cohesive natural-language prompt in this order:

1. task and output type;
2. reference-image role and product truth lock;
3. negative-geometry lock;
4. audience, theme, and scene;
5. the two category-specific devices, interaction/material proof, foreground depth device, and the template signature to avoid;
6. normalized composition, layout signature, and safe areas;
7. complete exact-copy manifest and claim provenance for every factual text region;
   declare `output_language` and forbid all unlisted copy in either language;
8. palette, lighting, material, lens, and finish;
9. explicit invariants, category-specific exclusions, and failure exclusions.

Use the prompt formulas in [prompting-and-api.md](references/prompting-and-api.md). Prefer precise language over long adjective stacks.

### 8. Generate with Seedream 5.0 Pro

Prefer an available callable Seedream 5.0 integration. Otherwise run:

```bash
python3 scripts/seedream_generate.py \
  --image "/absolute/path/product.png" \
  --prompt-file "/absolute/path/poster-prompt.txt" \
  --output "/absolute/path/poster.png" \
  --size "2K"
```

Set `ARK_API_KEY` in the environment. Never ask the user to paste a key into chat, print it, or store it in the skill.

Use `--dry-run` to validate the local image, model, and payload shape without sending a request.

For paid generations, create one first-pass image, inspect it, then decide whether another paid call is justified. Do not generate a large batch by default.

### 9. Inspect and revise

Apply [qa-rubric.md](references/qa-rubric.md). Compare the output directly against the input product image.

Revise by changing only the failed dimension:

- wrong product → strengthen the truth lock and say all other product details must remain unchanged;
- weak hierarchy → reduce copy and specify larger headline/product scale;
- clutter → remove secondary props and badges;
- illegible text → shorten copy or switch to two-pass typesetting;
- generic style → add one concrete scene metaphor, material system, and lighting direction;
- generic triptych → change the composition axis, product overlap, evidence mechanism, module shapes, and bottom closure together; do not merely restyle the three cards;
- poor conversion → enlarge product, CTA, and offer zone while simplifying decoration.
- publicity poster looks like a shopping UI → remove CTA buttons, arrows, search bars, and action instructions; extend the scene or stage into that area and close with a non-interactive slogan.
- batch looks templated → keep product truth locks, then replace the scene system, type personality, composition axis, and module shape rather than merely changing color.
- scene feels empty → add one purposeful foreground frame, one midground interaction layer, and one background depth cue; never solve emptiness with unsupported copy.
- scene is pretty but not ownable → replace generic lifestyle props with two devices derived from the product’s silhouette, material, use, or category physics.
- visual effects feel cheap or contradictory → remove disconnected icons/notes/speed streaks and rebuild one physically coherent effect tied to the product.

Do not keep polishing a failed base image. Regenerate when a hard rejection condition occurs.

Target 90/100 or higher. A score below 90 is a revision candidate even when no single artifact is catastrophic.

Make the delivery gate deterministic:

1. Run `python3 scripts/qa_gate.py --write-template /absolute/path/qa.json`.
2. Record direct evidence from source comparison, full-size inspection, thumbnail inspection, copy checking, claim-provenance checking, anti-template checking, product-specific-device checking, and safe-zone checking.
3. Enter every rubric subscore; list every hard rejection rather than hiding it in a low score.
4. Run `python3 scripts/qa_gate.py /absolute/path/qa.json`.
5. For a batch, pass every QA JSON in one command so the script verifies that each pair differs in at least four of six style dimensions.
6. Deliver only when the command prints `PASS`.

The gate rejects any hard failure, missing inspection evidence, category subtotal below its minimum, total below 90, incomplete scoring, or repetitive batch pair.

### 10. Deliver

Provide:

- the finished poster;
- the selected theme and one-line strategy;
- the final Seedream prompt;
- the QA total and five category subtotals;
- a short note listing any text or product detail that still needs human verification.

If generation cannot run because credentials or a Seedream tool are unavailable, still deliver the complete concept card and ready-to-run prompt, then state the exact missing prerequisite.

## Exact-copy mode

Use two-pass production when price, legal text, model numbers, or dense copy must be exact:

1. Generate the key visual with the product, background, lighting, layout space, and no text except product-label text that belongs to the physical product. Request calm blank surfaces for every overlay region.
2. Run `python3 scripts/typeset_overlay.py --write-template /absolute/path/typeset.json`.
3. Define every overlay region with exact text, normalized box, role, font family, size range, maximum line count, color, alignment, optional shadow, and optional rounded background.
4. Measure overlay boxes against the generated key visual. Treat planned percentages as intent, not as final coordinates: image generation may shift blank cards or the hero by several percent.
5. Run `python3 scripts/typeset_overlay.py /absolute/path/typeset.json`.
6. Reinspect text-to-product overlap, hierarchy, contrast, line breaks, conditional CTA safety, and bottom closure.

Prefer this mode for marketplace promotions, product specifications, and campaign terms. Native Seedream text is suitable for short expressive headlines but must still be inspected.

Keep product-label text and poster-overlay text separate. Do not cover or re-typeset a label that is physically printed on the product. The overlay tool validates absolute paths, installed CJK or Latin fonts, normalized bounds, horizontal safe margins, CTA bottom safety, legal-copy placement, maximum line counts, font-size ranges, and supported roles. It wraps English at word boundaries and Chinese at character boundaries. It uses deterministic local rendering, so the supplied strings are not rewritten by a model.

Prefer ordinary punctuation and tested characters in CTA, slogan, and badge copy. Do not assume decorative arrows, emoji, or icon glyphs exist in the selected font; render a proof first or draw the symbol as a separate graphic. Never add an arrow beside a publicity slogan, because it changes a brand close into a false CTA.

## Resource map

- [universal-router.md](references/universal-router.md): product-signal, buying-mechanism, density, scale, and six-band routing for unfamiliar categories.
- [style-atlas.md](references/style-atlas.md): ten reusable visual families and selection matrix.
- [reference-grammar.md](references/reference-grammar.md): distilled anatomy, density, rhythm, and richness from the supplied poster references.
- [layout-system.md](references/layout-system.md): normalized 9:16 grids, hierarchy, density, and composition formulas.
- [prompting-and-api.md](references/prompting-and-api.md): Seedream 5.0 Pro prompt patterns, API behavior, and retry guidance.
- [qa-rubric.md](references/qa-rubric.md): scorecard and hard rejection conditions.
- [execution-patterns.md](references/execution-patterns.md): field-tested style routing, richness rules, and batch anti-template checks.
- [benchmark-regression.md](references/benchmark-regression.md): sixteen-case regression suite and failure lessons for future changes.
- [reference-corpus.md](references/reference-corpus.md): 22 supplied references indexed by buying mechanism, layout, density, and reusable pattern.
- `scripts/seedream_generate.py`: local-image-to-poster API client with validation, retries, and download.
- `scripts/preflight_check.py`: deterministic JSON preflight for product truth, mechanism, density, bands, anchors, copy, claims, scale, and closure.
- `scripts/qa_gate.py`: deterministic 90-point output gate with hard rejections, evidence flags, category minima, and batch style-distance checks.
- `scripts/typeset_overlay.py`: exact Chinese/English overlay rendering with language-aware wrapping, Latin/CJK font aliases, auto-fit, line-count limits, safe-zone checks, role-aware layout, and optional cards/shadows.
