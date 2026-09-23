# UGC creator prompt rules

The rules for the creator/persona image in this workflow. The character is generated as a clean
person image (no products), and every downstream board and clip references it by URL plus a
positional mention ("第一张图片" / "第二张图片") in the prompt.

There is no enhancer service here: you read these rules, write ONE prompt string yourself, and
submit it as `prompt`. **The model comes from `canvas_image_model_list` — never hardcode one.**
Higgsfield's `soul_2` does not exist on WorkRally; pick a portrait-capable model whose
`resolution_options` reach 2K (enum `5`):

```jsonc
canvas_generate_image({
  model: "<canvas_image_model_list 返回的 model_id>",
  prompt: "<the string you wrote>",
  count: 1,
  aspect_ratio: "3:4",
  resolution: 5              // 2K; fall back to that model's highest resolution_options value
})
```

Poll the returned `task_ids` with `canvas_get_task` every 3s, then keep `character_url` =
`output_assets[0].url`. That identity is reused by every board and clip and is never regenerated
mid-run — and you cannot re-inspect the generated image later, so the traits you wrote (age band,
hair, build, wardrobe anchors) ARE the continuity contract. Record them.

Wherever this file says `soul_2`, `gpt_image_2`, `seedream_*` or Seedance, read it as "the model
chosen from `canvas_image_model_list` / `canvas_video_provider_config` for that step".

---

## CRITICAL: No Products in the Character Image

**When generating a character/creator for a UGC video:**

- Prompt describes ONLY the person: appearance, face, expression, clothing, pose, style.
- NEVER include products, objects, props, items, or anything the person holds or interacts with.
- Location/background is OK (bedroom, bathroom, kitchen, outdoor) — but NO objects in hands.
- The product enters the video LATER as a `medias` reference plus its `@ImageN` declaration in the board and clip prompts.

**Bad:** `"a young woman holding a skincare bottle in a bathroom, smiling"` — model bakes the bottle into the image, downstream compositing fails.
**Good:** `"a young woman, mid-20s, natural beauty, friendly smile, casual style, modern bathroom background"` — clean person, product added at video step.

This rule is non-negotiable. Apply it to every character generation in this pipeline.

---

## Beauty Floor (mandatory in every prompt)

The persona must always read as conventionally attractive — model-tier face, symmetrical features, well-proportioned figure. This holds across every tier (drugstore through luxury). Tier changes the wardrobe, the room, and the aesthetic register — it does NOT lower the beauty bar.

Every prompt MUST contain these phrases (or close paraphrases woven in naturally):

- `with high model facial features`
- `symmetrical features`
- `well-proportioned figure`
- `natural skin texture`

These four anchors lock the editorial-grade face structure, prevent plastic/AI look, and ensure the person looks like a real attractive creator regardless of tier.

---

## Variety Defaults (mandatory — pick BEFORE writing the prompt)

When the user does NOT specify these traits, the agent MUST pick one option from each pool BEFORE building the prompt. **Do not default to the same combination every time** — rotate. The "same model" problem (every UGC creator looks like the previous one) is what this rule fixes.

### Variety Roll Protocol (mandatory before generation)

To defeat LLM-bias toward "familiar" pool options, the agent MUST run ONE Bash call before composing the prompt:

```bash
python3 -c "import secrets; print(' '.join(str(secrets.randbelow(100)) for _ in range(8)))"
```

This returns 8 integers in `[0, 99]` (space-separated). Map them in order to the Variety Defaults table below via `roll % pool_size`:

| Roll | Axis | Pool size | Pick index |
|---|---|---|---|
| roll_1 | Age band | 4 | `roll_1 % 4` |
| roll_2 | Hair color | 14 | `roll_2 % 14` |
| roll_3 | Hair length & style | 14 | `roll_3 % 14` |
| roll_4 | Build / vibe | 5 | `roll_4 % 5` |
| roll_5 | Distinctive feature | 9 | `roll_5 % 9` |
| roll_6 | Makeup register | 9 | `roll_6 % 9` |
| roll_7 | Ethnicity / face read | 8 | `roll_7 % 8` |
| roll_8 | Outfit aesthetic register | 10 | `roll_8 % 10` |

Notes:

- `secrets.randbelow` uses OS-level kernel entropy (cryptographic-grade) — every value 0..99 has equal probability per call. It cannot drift or overfit.
- **Skip the roll for any axis the user already specified** — user input wins (see User Override Rule below).
- The `Outfit specifics within tier` axis still relies on the existing Category × Tier Wardrobe Matrix for FORMALITY (luxury / premium / drugstore). The new `Outfit aesthetic register` roll (roll_8) selects the wardrobe VOCABULARY / aesthetic genre on top of the matrix's tier-formality. Both apply together — see the calibration paragraph just below the Wardrobe Matrix.
- If the rolled combo matches the previous character in the session (per the anti-clone rule below), re-roll only the conflicting axes.

| Trait | Pool — rotate through |
|---|---|
| Age band | early 20s · mid 20s · late 20s · early 30s |
| Hair color | warm honey blonde · cool ash blonde · chestnut · espresso · soft brown · jet black · deep auburn · copper · platinum · honey balayage · money-piece highlights · vivid green · vivid pink · pastel lavender |
| Hair length & style | shoulder-length wavy · long sleek straight · long with soft waves · medium with curtain bangs · sleek bob (chin-length) · pixie cut · wolf cut · claw-clip slicked back · messy low bun · half-up half-down · boxer braids · high ponytail · dreadlocks (locs) · shaved buzz cut |
| Build / vibe | athletic toned · soft natural · average proportional · petite · tall everyday |
| Distinctive feature | clean (no distinctive feature) · natural freckles across cheekbones · delicate nose stud · small lip ring · eyebrow piercing · septum ring · dimples · gap teeth · subtle beauty mole on cheek |
| Makeup register | bare-skin no-makeup · casual natural · glowy with mascara only · soft brown smoky eye · playful winged liner · bold colored eyeliner accent · inner-corner glitter highlight · graphic blush draped across cheekbones · glossy lip with neutral face |
| Ethnicity / face read | rotate naturally — fair European · warm Mediterranean · East Asian · South Asian · Latina · mixed · Middle Eastern · Slavic. Pick by face features rather than naming an ethnicity word in the prompt. |
| Outfit aesthetic register | streetwear-oversized · preppy / equestrian · Y2K-coded · quiet-luxury · coastal-minimal · sporty-jersey · editorial-blazer-cool · boho-soft · leather-grit · clean-minimalist |
| Outfit specifics within tier | rotate through the matrix-listed options for the tier — don't always pick the first one. The Outfit aesthetic register above selects the wardrobe VOCABULARY; the tier matrix selects the FORMALITY level. Both apply together. |

The agent should never produce two consecutive characters with identical age + hair + build. If the previous character in this session was "early 20s warm blonde slender", the next one must differ in at least two of those traits.

User-specified traits ALWAYS win — these pools only apply where the user left a gap.

---

## Style

- Always natural, lifestyle, UGC-feel — NOT editorial, studio, or fashion.
- Hair color and makeup roll from the Variety Defaults pools above — both pools span natural-to-bold stylish options on purpose. User-specified hair or makeup ALWAYS wins over the pool roll.
- Approachable, authentic — NOT cold, stylized, or heavily art-directed.
- **Default light tone: neutral cool daylight ONLY. NEVER golden hour, NEVER warm sunset, NEVER orange/amber cast, NEVER late-afternoon warm wash. Even outdoor scenes use neutral midday or overcast diffusion.**

---

## User Override Rule (priority over everything below)

If the user specifies ANY concrete detail — setting, location, clothing, appearance, mood, time of day, props in the room, hair color, ethnicity — that detail wins over every default in this file. Defaults exist ONLY to fill gaps the user left empty. Never replace a user-specified detail with a default.

---

## Product Tier Detection (visual analysis only)

When no setting is given by the user, determine the product tier from the product image — brand identity + packaging visual cues only. **Never look up price.** This drives the location and wardrobe choice in the matrix below.

| Tier | Signals (any combination) |
|---|---|
| **luxury** | Known luxury houses (Chanel, Dior, Givenchy, Tom Ford, La Mer, YSL, Hermès, Cartier, Armani, Versace, Gucci, Louis Vuitton, etc.). Heavy glass packaging with embossed/debossed logos. Monochrome / black / gold / silver / cream typography. Minimalist refined design. Serif or custom display logotypes. |
| **premium** | Modern clean packaging, well-known mid-high brands (Drunk Elephant, Glossier, Sephora-tier, Aēsop-style, niche apothecary). Considered typography, restrained palette. Quality plastic or matte glass. |
| **drugstore / mass-market** | Bright colorful plastic packaging, mass-market brands (CeraVe, Nivea, L'Oréal, Garnier, Pantene, Maybelline, etc.). Vibrant typography, bold claims, supermarket aisle energy. |

**If unclear → default to premium**, not drugstore. Better to over-elevate than to misread a serious brand.

For non-cosmetics categories (food, supplements, tech, cars, etc.) tier still applies in the same way — luxury vehicle vs. econobox, artisan supplement vs. bulk protein tub, premium audiophile gear vs. basic accessory.

---

## Location × Tier × Wardrobe Matrix

**Priority order:**

1. **User specified a location** → use exactly that.
2. **No location given → match (category, tier) below.**
3. **No product context at all** → cozy home, bedroom or living room, casual everyday outfit.

| Category | Tier | Default location | Wardrobe |
|---|---|---|---|
| Cosmetics / makeup / fragrance | luxury | Stylish modern bedroom or vanity nook with designer furniture, soft architectural detail (paneled walls, statement mirror, refined textures) | Silk or satin robe in dark / brand-adjacent / neutral premium tones, tightly tied at the waist with closed modest neckline and lapels overlapping fully, OR designer pajama set, OR "already dressed for going out — applying the final touch" with curated outfit |
| Cosmetics / makeup / fragrance | premium | Bright clean modern bathroom or bedroom, considered details | Premium cotton robe tightly tied at the waist with closed modest neckline, casual chic top, or lounge-luxe set in neutrals |
| Cosmetics / makeup / fragrance | drugstore | Everyday bright bathroom or bedroom, lived-in feel | Cozy oversized cotton robe tightly tied at the waist with closed neckline / soft hoodie / casual fitted top |
| Skincare / haircare / body care / shower gel | luxury | Spa-like bathroom — marble, brass fixtures, rainfall shower, plants, refined materials | Silk robe or premium-feel bathrobe in muted tones, tightly tied at the waist with closed modest neckline and lapels overlapping fully |
| Skincare / haircare / body care / shower gel | premium | Bright modern bathroom — clean tile, matte fixtures, vanity lighting | Cream / oatmeal cotton robe tightly tied at the waist with closed modest neckline, casual lounge wear |
| Skincare / haircare / body care / shower gel | drugstore | Standard bright bathroom, friendly and lived-in | Cozy oversized robe tightly tied at the waist with closed neckline, casual t-shirt |
| Food / beverages / kitchen products | any | Modern kitchen — appropriate finish to tier (luxury: marble + brass; premium: white cabinetry + stainless; mass-market: bright friendly kitchen) | Casual chic — fitted blouse + jeans, knit top, or athleisure if health-coded |
| Protein / supplements / sports nutrition | any | Either home gym (clean dumbbells, mat, mirror, plants) OR bright kitchen (post-workout context) — pick the one that fits the product more (powder/shaker → kitchen; bars/recovery → kitchen or living room; gear-adjacent → gym) | Athleisure / athletic fitted top, joggers or leggings, fresh-from-workout vibe |
| Clothing / accessories / jewelry / watches | luxury | Stylish bedroom or dressing room — wardrobe rack, statement mirror, refined finishes | Curated outfit — "she's already styled, this is the finishing piece" — silk camisole + tailored trousers, or refined knit + slip skirt |
| Clothing / accessories / jewelry / watches | premium | Bedroom / living room with elevated styling — designer chair, plants, considered art | Casual chic — relaxed fitted top, high-waisted trousers, layered minimal jewelry |
| Clothing / accessories / jewelry / watches | drugstore / everyday | Bedroom / living room with everyday cozy feel | Casual relaxed outfit, comfortable layers |
| Fitness / sports / training equipment (dumbbells, kettlebells, weights, resistance bands, yoga mats, foam rollers, jump ropes, training apparel) | any | Home gym, living room mat area, or yoga corner with mat + plants + natural light | Athletic wear matching the discipline (compression top + leggings, sports bra + shorts, running fit, yoga set) |
| Cars / vehicles | any | Outdoor next to the car — driveway, sunlit street, parking pad, or garage with the door open. Walk-around angle, natural daylight | Stylish casual outerwear — light jacket, well-fitted denim or trousers, sneakers or boots; tier elevates the wardrobe (luxury: tailored coat, designer shades; everyday: clean casual) |
| Outdoor gear / sunglasses / summer wear / sunscreen | any | Outdoor café terrace, park, or sunlit street with people in soft background | Outfit appropriate to season + tier — linen shirt, sundress, lightweight set |
| Tech / electronics / audio | any | Home desk, living room, or studio nook (tier elevates the desk: luxury → wood + leather + minimal premium accessories; mass-market → bright clean desk) | Smart casual — fitted knit, button-down, or relaxed athleisure |
| Home / decor / candles | any | Living room or bedroom with the relevant ambiance — tier elevates materials (luxury: linen sofa, art, sculptural pieces; everyday: cozy throws, plants) | Lounge-elevated — soft knit, relaxed trousers, or cozy set |
| **Everything else** | any | Cozy home — bedroom or living room | Casual everyday outfit |

**Outdoor / street** is used only when the product clearly belongs in that context (cars, summer wear, outdoor lifestyle, café products). Otherwise indoor by default.

---

## Outfit aesthetic register × Tier (mandatory layering)

The `Outfit aesthetic register` rolled in Variety Defaults (roll_8) selects the wardrobe VOCABULARY / style genre. The Location × Tier × Wardrobe Matrix above selects the FORMALITY level (luxury / premium / drugstore). Both apply together — the register tells you WHAT KIND of look, the tier tells you HOW REFINED the materials are.

Vocabulary anchors per register:

- `streetwear-oversized` — oversized graphic tee or hoodie + baggy / wide-leg trousers or denim + chunky sneakers + layered chain necklaces
- `preppy / equestrian` — blazer + silk neck-tie or cream silk blouse + leather accents (gloves / belt) + structured bag
- `Y2K-coded` — mini skirt or slip dress + butterfly hair clips + chunky choker + small bag
- `quiet-luxury` — cashmere or merino knit + tailored trousers + delicate gold jewelry + minimal leather accessories
- `coastal-minimal` — linen shirt + cream wide-leg trousers + simple gold hoops + woven / leather sandals
- `sporty-jersey` — oversized sports jersey or polo + baggy trousers or shorts + bandana or hair clip + sneakers
- `editorial-blazer-cool` — pinstripe or tailored blazer over tank / camisole + chunky chain choker + statement sunglasses
- `boho-soft` — slip dress or silk camisole + open cardigan + layered pendants + soft sandals
- `leather-grit` — leather jacket layer over knit or tee + dark denim or trousers + statement cap + boots
- `clean-minimalist` — fitted white shirt or knit + denim or trousers + delicate jewelry (this is the most stock register; the other 9 should be picked more often)

The TIER calibrates materials and brand register: `luxury` reads as silk / cashmere / designer / fine gold; `premium` reads as quality cotton / branded / considered finishing; `drugstore` reads as everyday cotton / thrift-tier / plastic clips / basic chains. The REGISTER calibrates the SHAPE and aesthetic genre. Both apply together — a `Y2K-coded` luxury character wears a silk slip with a chunky gold chain; a `Y2K-coded` drugstore character wears a cotton tank with plastic butterfly clips.

The modesty triplet from **Universal Outfit Modesty** below STILL applies on top of register × tier — necklines, lapels, sash-ties, garment-specific coverage stays mandatory regardless of register.

If the rolled register feels physically wrong for the product (e.g. `sporty-jersey` for a high-end fragrance bottle), the agent MAY re-roll roll_8 once — but most register × tier combinations work because the tier calibrates the register's vocabulary.

---

## Universal Outfit Modesty (mandatory — applies to every matrix entry above)

Every wardrobe entry in the matrix above MUST be wrapped with explicit modesty language in the final prompt — even when the matrix says only "fitted blouse" or "casual chic top". Portrait models otherwise default to plunging V-cuts and exposed cleavage, which then trips the content filters at the board step and the video step. This rule is non-negotiable and applies regardless of tier or category.

### Universal triplet (append to every outfit description)

```
top fully closed at the front, fabric meeting at the collarbone, classic high-coverage fit
```

### Per-garment specifics (layer on top of the universal triplet)

| Garment type | Required modesty language |
|---|---|
| Button-down / shirt | `fully buttoned to at least the second-from-top button` |
| Knit / sweater / fitted top | `modest crew or scoop neckline, no V-cut` |
| Blouse | `modest closed neckline, no plunging V, no deep décolletage` |
| Robe / kimono / silk wrap | `tightly tied at the waist with sash visible, both lapels overlapping fully across the chest` (already in matrix, keep) |
| T-shirt | `fitted but with a modest crew neckline` |
| Tank top / camisole / spaghetti strap | **FORBIDDEN as standalone.** Only allowed when explicitly layered under a button-down / cardigan / blazer that itself follows the modesty rules above |
| Athletic top / compression top | `high crew or modest scoop neckline, fully covering chest` |

### Bottom

Bottom-half wardrobe (jeans, trousers, leggings, skirts) is already implicitly covered by the matrix entries — no extra rule needed beyond the existing `tucked into high-waisted ...` phrasing where applicable.

### Example: applying universal modesty to a matrix entry

Matrix says: `casual chic top + jeans`

Final prompt outfit description:
> `a fitted long-sleeve blouse with a modest closed neckline, no plunging V, no deep décolletage, fully covering chest and torso, tucked into high-waisted dark denim jeans`

Matrix says: `fitted neutral knit + denim`

Final prompt outfit description:
> `a fitted neutral knit top with a modest crew neckline, no V-cut, fully covering chest and torso, paired with well-cut straight-leg denim`

The modesty triplet appears in EVERY character prompt regardless of how short the matrix entry is.

---

## Lighting

- Always specify direction and quality — not just "natural light" but "soft natural daylight streaming in from the left window" or "cool diffused daylight from the right."
- **Default: neutral cool daylight ONLY — bright, clean, no warmth.** Use phrasing like "cool neutral daylight", "soft diffused white light", "clean midday light", "overcast diffusion".
- **HARD BAN: golden hour, warm sunset, orange/amber/honey cast, late afternoon warm wash, sunlit warm tones, "magic hour" — even outdoors.** These tones make the persona look like a stock-photo ad, not a real creator. Sunset is allowed ONLY when the user explicitly requests it AND the story specifically requires it.
- For outdoor scenes (cars, café terrace, park), use neutral midday or overcast — describe explicitly: "soft overcast daylight", "cool neutral midday sun, no warm cast".
- NEVER harsh studio strobes. NEVER pure white seamless background (unless the user asks).
- Light should interact with the space — mention how it hits surfaces in the room.

---

## Location Detail — always be specific

A named location alone ("kitchen", "bedroom") produces a plain wall. Always add architectural detail, materials, and color palette of the space:

- **What's in the background** — type of furniture, cabinetry, shelving, plants, textures
- **Materials** — marble, wood, tile, fabric, stainless steel, brass, linen, etc.
- **Color palette of the space** — dominant colors that set the mood (whites + beiges, warm wood tones, soft pastels, charcoal + brass, etc.)
- **Wardrobe-palette agreement (mandatory)** — the wardrobe colour MUST contain at least one tone from the room's stated palette. If the palette is "deep charcoals + warm off-whites + brass" — wardrobe is in charcoal / off-white / cream / brass-tinted tones. NEVER pair a wardrobe in conflicting colours (e.g. crisp white shirt + dark navy trousers in a charcoal/brass room) — this creates a palette conflict and visibly degrades the rendered atmosphere.
- **Depth of field** — describe naturally as `"subject in clear focus with the background naturally falling out as in any phone photo"`. Do NOT use `"minimal depth of field, soft subtle separation"` — that's editorial DSLR language, NOT phone aesthetic.

---

## Camera & Atmosphere — iPhone UGC is the DEFINING feature

The output MUST read as a real creator's phone photo — NOT a portrait shoot, NOT a fashion editorial, NOT a studio session. This is the most important rule in this file. Skip it and the whole UGC pipeline fails downstream.

### Mandatory iPhone phrasing — include in every prompt

- `Self-portrait selfie shot on iPhone front-facing camera held by the subject at arm's length — head and shoulders fill the frame`
- `Selfie geometry: subject's own arm extended toward the lens, hand or wrist may faintly appear at the edge of frame holding the phone`
- `Slightly off-center, slightly imperfect framing — not posed, not studio-centered`
- `Spontaneous angle with a slight casual tilt, intuitive composition — not symmetric, not centered`
- `Captured mid-moment, NOT a formal pose for the camera`
- `Subject minimally aware of the lens — relaxed, natural, like she just turned the camera on`
- `Phone-sensor grain and realistic skin pores and texture preserved — no retouch, no smooth-skin filter, no professional gloss`
- `Subject in clear focus with the background falling out naturally as in any phone photo`
- `Authentic UGC creator phone selfie, taken by herself with her own front camera at arm's length, NOT editorial fashion photography, NOT studio portrait, NOT magazine retouch`

### HARD BAN — never appear in the prompt

These phrases produce editorial / studio look — the OPPOSITE of UGC:

- `centered composition at eye-level` — too studio-posed
- `straight-on` — too composed, formal-portrait language
- `mid-length portrait`, `editorial portrait`, `fashion portrait` — genre language that flips the whole render to editorial
- `minimal depth of field, soft subtle separation` — too professional-DSLR
- `editorial mood`, `editorial atmosphere`, `crisp editorial` — opposite of UGC
- `aspirational lifestyle atmosphere` — too glossy advertising
- `flattering and even illumination` — too studio
- `glowing skin`, `flawless skin`, `radiant complexion` — too retouched
- `poised`, `refined expression`, `dignified pose`, `elegant stance`, `graceful posture` — posed-photography language
- `warm smile at the camera`, `looking at the camera with a smile`, `direct eye contact with the camera and a confident smile` — aware-of-camera mimic; replace with mid-action expressions (see below)
- Any "pose" verb: `poses`, `is posing`, `striking a pose`, `stands gracefully`
- Anything implying tripod, studio strobe, ring light, beauty dish, professional camera body

### Approved mid-action expressions (use one of these — never `warm smile`)

Pick ONE expression descriptor per prompt that reads as a captured moment, not a posed shot:

- `mid-thought, slight half-smile, eyes glancing slightly off-lens`
- `caught mid-laugh, soft natural laugh, head slightly tilted`
- `casually glancing toward the lens with a relaxed, neutral expression`
- `looking up from her phone with a relaxed, unguarded face`
- `mid-action expression — in the middle of saying something, not posing`
- `natural unguarded face, soft neutral expression, not smiling at the camera`
- `wide-eyed mid-gasp, lips parted, brows lifted — caught at the start of a reaction`
- `mid-laugh with mouth open, head thrown slightly back, shoulders shifted`
- `playful mock-shock — round eyes, slight grin breaking under the surprise`
- `mid-react squint — one eye scrunching, half-grin pulling sideways`
- `eyebrows lifted mid-thought, lips pressed in a "wait, no" line, head tilted slightly`

### Replacements (use these instead)

| Editorial language to AVOID | iPhone UGC replacement |
|---|---|
| `centered composition at eye-level` | `casual handheld iPhone framing — slightly off-center, slightly imperfect, not posed` |
| `minimal depth of field, soft subtle separation` | `subject in clear focus with the background naturally falling out as in any phone photo` |
| `aspirational lifestyle atmosphere` | `real creator phone snapshot vibe, like a moment caught on her phone` |
| `glowing skin` / `flawless` | `realistic skin texture, visible pores, natural` |
| `Captured in UGC style with a smartphone camera` (afterthought) | the full closing block below, prominently placed |

### Closing block — append verbatim at the end of every prompt

```
Self-portrait selfie shot on iPhone front-facing camera held by the subject at arm's length — head and shoulders fill the frame, casual handheld framing, slight natural tilt, slightly off-center, slightly imperfect, not posed. Phone-sensor grain and realistic skin texture preserved, no retouch, no smooth-skin filter. Authentic UGC creator phone selfie, NOT editorial portrait, NOT fashion magazine.
```

---

## No Prompt Rewriting

Build the prompt following these rules and send it **as-is**. `canvas_generate_image` has no prompt-enhancement toggle. Never restate, summarise, or "improve" the prompt yourself between building it and submitting it. Write it in Chinese — WorkRally's models are Chinese-first — while keeping the block order and the camera / light / material vocabulary of the templates below.

---

## Safety Rules (applied BEFORE submitting the prompt)

**1. Age enforcement — minimum 20 years old.**
If the user requests a child, minor, teenager, or uses terms like "girl", "boy", "kid", "teen" — silently age the subject up. Change the description to ensure the person is explicitly at least 20 years old (e.g., "young woman, 20 years old"). Keep the rest of the scene intact. Do not mention this adjustment to the user.

**2. Anatomy & clothing.**
If the prompt contains detailed descriptions of bare skin, specific body parts, or intimate anatomy — do NOT discard the prompt. Instead, adapt it by naturally weaving in clothing that covers sensitive areas:

- Female subjects: clothing that covers chest and lower body (pelvic area)
- Male subjects: clothing that covers lower body (pelvic area)
- Added clothing MUST match the aesthetic, setting, and style of the original prompt seamlessly

**3. Wardrobe modesty — robes / kimonos / silk wraparound pieces.**
When the wardrobe includes a robe, kimono, silk piece, or any wraparound garment, describe it with explicit modesty constraints to prevent downstream image-generation filters (GPT Image 2.0, etc.) from flagging the storyboard as suggestive:

- **Tightly tied at the waist** with the sash visible — NEVER "loose", NEVER "untied"
- **Closed modest neckline** — no plunging V-cut, no exposed chest, no deep décolletage
- **Both lapels overlapping fully** across the chest

Use phrasing like `"robe tightly tied at the waist with closed modest neckline, both lapels overlapping fully"` rather than just `"silk robe"` or `"cozy robe"`. This applies whenever the matrix wardrobe entry mentions a robe, regardless of tier.

**CRITICAL — Seedance 2.0 nsfw exception (ugc-review-video pipeline):** Seedance itself can return `status: nsfw` even when the character is not wearing a robe. A regular fitted knit top combined with certain board poses (extended-arm selfie, product-extension toward lens, cap-opening action) is enough to trigger the filter. If a Seedance job returns `status: nsfw`:
1. **Do NOT retry the same character + board.** The filter is not random — identical inputs fail again.
2. **Regenerate the character** with the most unambiguously conservative outfit (see Outfit Language rule below).
3. **Regenerate the storyboard board** with the new character image.
4. **Add the explicit outfit description** to the Seedance prompt's quality suffix — reinforces coverage to the video model.

The trigger is a combination of outfit ambiguity + pose angles, not outfit alone. A structured, fully-opaque button-down is more filter-safe than a fitted knit or draped top. When in doubt, default characters to button-down + trousers for ugc-review-video.

### Default wardrobe path — pick from matrix, ROTATE

For every first-pass generation: select the wardrobe from the matrix entry matching the product category × tier ([Location × Tier × Wardrobe Matrix](#location--tier--wardrobe-matrix) above). Each matrix row lists multiple options separated by `OR` / `,` (silk robe / pajama set / curated outfit; knit + denim / blouse + jeans / athleisure; compression top + leggings / running fit / yoga set; hoodie / fitted t-shirt; tailored coat / linen shirt / sundress; etc.). **ROTATE through them — never default to button-down for everyone.** Apply the [Universal triplet](#universal-triplet-append-to-every-outfit-description) once. **DO NOT add a camisole base layer to default outfits** — it kills variety and makes every character look identical.

### Positive structural language (general principle for the whole file)

Across every outfit description, prefer positive phrasing — `fully buttoned to the collar`, `crew neckline at the collarbone`, `tightly tied at the waist with sash visible` — over negations like `no V-neck`, `zero neckline exposure`, `completely covering chest`. Diffusion text encoders prime on negation trigger words (`chest`, `torso`, `neckline`, `exposure`) and often render the very thing being negated.

### NSFW retry fallback — ONLY after a filter has actually rejected the generation

When the board step or the video step has been rejected by the content filter and you are regenerating (not on the first attempt), switch to this safety-locked fallback. Pick the colour from the room's palette (Wardrobe-palette agreement still applies):

```
[palette-aligned colour] button-down shirt fully buttoned to the collar, layered over a fitted [palette-aligned colour] camisole base, tucked into high-waisted [palette-aligned colour] trousers
```

Examples per palette:
- charcoal/off-white/brass room → `cream button-down ... layered over cream camisole base ... charcoal trousers`
- warm beige/wood/cream kitchen → `oatmeal button-down ... layered over oatmeal camisole base ... taupe trousers`
- spa-bathroom whites + sage → `off-white button-down ... layered over off-white camisole base ... soft sage trousers`

Use this fallback ONLY after an actual filter failure — never as the first attempt. On retry, also repeat the positive outfit description in the storyboard board prompt — this reinforces it at the board model's filter step.

---

## Prompt Structure

**Gender is determined by the user's request.** Default: woman. If the user says "man", "guy", "male", "dude", "him" — use man / he / his throughout. Never mix genders in a single prompt.

```
A [age band from Variety pool] [man/woman], [expression — pick one from the Approved mid-action expressions list], [hair color + length from Variety pool, build vibe], with high model facial features, symmetrical features, well-proportioned figure, natural skin texture, standing in a [specific location with architectural details].
[Light direction and quality — MUST be cool/neutral daylight, NEVER golden hour, NEVER warm sunset, NEVER orange/amber cast] falls across her face — neutral, clean, no warm cast, **no retouched glow. Skin texture is real, with visible pores and natural unevenness.**
[He/She] wears [outfit matching category × tier from the matrix — pick a non-default option from the matrix's list].
The background features [specific details: materials, colors, furniture].
Color palette dominated by [space colors — keep neutrals; avoid amber/orange dominance].
Casual handheld iPhone selfie taken by [her/him] at arm's length — head and shoulders fill the frame, slight natural tilt, slightly off-center, intuitive composition, captured mid-moment. Subject in clear focus with the background naturally falling out as in any phone photo.
Shot on iPhone front-facing camera. Phone-sensor grain and realistic skin texture preserved, no retouch, no smooth-skin filter. Authentic UGC creator phone selfie, NOT editorial portrait, NOT fashion magazine.
```

---

## Real Examples (target this quality level)

### Kitchen — food / beverage / kitchen product (premium)

```
A spontaneous iPhone snap of a young woman in her early 20s, mid-thought with a slight half-smile, eyes glancing slightly off-lens, with high model facial features, symmetrical features, well-proportioned figure, natural skin texture, standing in a modern, bright kitchen. Soft natural window light streams in from the left across her face — clean, neutral, no warm cast, no retouched glow. Skin texture is real, with visible pores and natural unevenness. She wears a casual chic outfit — a fitted long-sleeve blouse made from matte, opaque cotton with a modest closed neckline, no plunging V, no deep décolletage, fully covering chest and torso, tucked into high-waisted dark denim jeans. The kitchen background is defined by pristine white cabinetry, stainless steel hardware, and subtle recessed lighting, providing a clean and contemporary interior aesthetic. Casual handheld iPhone selfie taken by her at arm's length — head and shoulders fill the frame, slight natural tilt, slightly off-center, intuitive composition, captured mid-moment. Subject in clear focus with the background naturally falling out as in any phone photo. The color palette is bright, dominated by whites, beiges, and subtle tan accents. Self-portrait selfie shot on iPhone front-facing camera held by her at arm's length. Phone-sensor grain and realistic skin texture preserved, no retouch, no smooth-skin filter. Authentic UGC creator phone selfie, NOT editorial portrait, NOT fashion magazine.
```

### Bathroom — skincare / haircare / body care (premium)

```
A spontaneous iPhone snap of a young woman in her mid-20s, casually glancing toward the lens with a relaxed, neutral expression, with high model facial features, symmetrical features, well-proportioned figure, natural skin texture, standing in a bright modern bathroom. Soft diffused daylight from the left falls across her face — neutral cool, no warm cast, no retouched glow. Skin texture is real, with visible pores and natural unevenness. She wears a cozy oversized cream-colored robe tightly tied at the waist with a closed modest neckline and lapels overlapping fully, casual and relaxed. The bathroom background features clean white subway tiles, matte black fixtures, a large mirror with warm vanity lighting, and a small plant on the counter. The color palette is soft and airy, dominated by whites, warm creams, and subtle sage accents. Casual handheld iPhone selfie taken by her at arm's length — head and shoulders fill the frame, slight natural tilt, slightly off-center, intuitive composition, captured mid-moment. Subject in clear focus with the background naturally falling out as in any phone photo. Self-portrait selfie shot on iPhone front-facing camera held by her at arm's length. Phone-sensor grain and realistic skin texture preserved, no retouch, no smooth-skin filter. Authentic UGC creator phone selfie, NOT editorial portrait, NOT fashion magazine.
```

### Bedroom — clothing / accessories / lifestyle (everyday)

```
A spontaneous iPhone snap of a young woman in her early 20s, caught mid-laugh with a soft natural laugh and head slightly tilted, with high model facial features, symmetrical features, well-proportioned figure, natural skin texture, sitting on the edge of a cozy bed. Soft natural daylight streams in from a window on the right, casting gentle neutral light across her face and the room — no warm cast, no retouched glow. Skin texture is real, with visible pores and natural unevenness. She wears a casual everyday outfit — a relaxed fitted long-sleeve top with a modest crew neckline, no V-cut, fully covering chest and torso, paired with high-waisted trousers. The bedroom background features soft neutral bedding in warm beige tones, a wooden nightstand with a small plant, and subtly textured walls. The color palette is warm and inviting, dominated by creams, taupes, and muted warm tones. Casual handheld iPhone selfie taken by her at arm's length — head and shoulders fill the frame, slight natural tilt, slightly off-center, intuitive composition, captured mid-moment. Subject in clear focus with the background naturally falling out as in any phone photo. Self-portrait selfie shot on iPhone front-facing camera held by her at arm's length. Phone-sensor grain and realistic skin texture preserved, no retouch, no smooth-skin filter. Authentic UGC creator phone selfie, NOT editorial portrait, NOT fashion magazine.
```

### Stylish bedroom — luxury cosmetics / fragrance / makeup

```
A spontaneous iPhone snap of a young woman in her mid-20s with a natural unguarded face, soft neutral expression, not smiling at the camera, with high model facial features, symmetrical features, well-proportioned figure, natural skin texture, standing in a stylish modern bedroom with paneled walls and a designer mirror. Soft cool daylight diffuses in from a tall window on the left, falling gently across her face and the room — neutral cool, no warm cast, no retouched glow. Skin texture is real, with visible pores and natural unevenness. She wears a charcoal silk robe with a subtle satin sheen, tightly tied at the waist with a closed modest neckline and lapels overlapping fully, hinting that she is mid-routine before going out. The bedroom background features a sculptural wooden nightstand, a single trailing plant, refined off-white linens, and a slim brass floor lamp. The color palette is muted and elevated, dominated by deep charcoals, warm off-whites, and soft brass accents. Casual handheld iPhone selfie taken by her at arm's length — head and shoulders fill the frame, slight natural tilt, slightly off-center, intuitive composition, captured mid-moment. Subject in clear focus with the background naturally falling out as in any phone photo. Self-portrait selfie shot on iPhone front-facing camera held by her at arm's length. Phone-sensor grain and realistic skin texture preserved, no retouch, no smooth-skin filter. Authentic UGC creator phone selfie, NOT editorial portrait, NOT fashion magazine.
```

### Outdoor next to the car — automotive

```
A spontaneous iPhone snap of a young woman in her mid-20s, looking up from her phone with a relaxed, unguarded face, with high model facial features, symmetrical features, well-proportioned figure, natural skin texture, standing on a sunlit driveway next to a parked car. Soft neutral daylight from the upper right falls evenly across her face and the surrounding pavement, with a faint shadow cast on the ground beside her — neutral, clean, no warm cast, no retouched glow. Skin texture is real, with visible pores and natural unevenness. She wears a clean casual outfit — a fitted neutral knit top with a modest crew neckline, no V-cut, fully covering chest and torso, well-cut straight-leg denim, and minimal white sneakers, with a light tailored jacket layered over the shoulders. The background features a quiet residential street, a hedge with soft green foliage, and the front quarter of the car visible behind her. The color palette is bright and natural, dominated by warm asphalt grays, soft greens, and sky blue. Casual handheld iPhone selfie taken by her at arm's length — head and shoulders fill the frame, slight natural tilt, slightly off-center, intuitive composition, captured mid-moment. Subject in clear focus with the background naturally falling out as in any phone photo. Self-portrait selfie shot on iPhone front-facing camera held by her at arm's length. Phone-sensor grain and realistic skin texture preserved, no retouch, no smooth-skin filter. Authentic UGC creator phone selfie, NOT editorial portrait, NOT fashion magazine.
```

### Home gym — protein / supplement / fitness

```
A spontaneous iPhone snap of a young woman in her early 20s, mid-action — in the middle of saying something, not posing, with high model facial features, symmetrical features, well-proportioned figure, natural skin texture, standing in a bright home gym corner. Soft natural daylight streams in from a tall window on the right, falling cleanly across her face and the matte rubber flooring — neutral, clean, no warm cast, no retouched glow. Skin texture is real, with visible pores and natural unevenness. She wears a fitted athletic set — a sage compression top with a high crew neckline, fully covering chest, paired with high-waisted leggings — with a slight post-workout flush and a few loose strands of hair framing her face. The background features a stack of clean dumbbells on a wooden rack, a rolled yoga mat, a tall potted plant, and a wall-mounted mirror reflecting soft light. The color palette is fresh and grounded, dominated by warm whites, muted sage greens, and natural wood tones. Casual handheld iPhone selfie taken by her at arm's length — head and shoulders fill the frame, slight natural tilt, slightly off-center, intuitive composition, captured mid-moment. Subject in clear focus with the background naturally falling out as in any phone photo. Self-portrait selfie shot on iPhone front-facing camera held by her at arm's length. Phone-sensor grain and realistic skin texture preserved, no retouch, no smooth-skin filter. Authentic UGC creator phone selfie, NOT editorial portrait, NOT fashion magazine.
```

---

## Submission recap

`canvas_generate_image` with the model picked from `canvas_image_model_list`, `aspect_ratio: "3:4"`,
`resolution: 5` — the prompt string exactly as built above, no JSON wrapper. Poll `canvas_get_task`
to `state: 4` and carry `output_assets[0].url` forward as the character reference. There is no
element registration in this pipeline: that URL IS the reusable reference for every board and clip.
