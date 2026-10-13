# Field-Tested Execution Patterns

Use these notes when planning a batch or when a first result feels generic.

## Non-negotiable sequence

1. Audit the input and write a 4–8 fact product truth lock.
2. Design the theme and style before generating.
3. For a batch, allocate visibly different style systems before writing prompts.
4. Generate one image per product and inspect it against the source.
5. Revise only the failed dimension; regenerate on a hard product or text failure.
6. Deliver the actual model name, final prompt, and verification notes.

## Lessons from real poster runs

### Earbuds: blue-silver flagship launch

The “metallic headline + feature cards + hero halo + architectural portal + foreground stage” system creates strong launch-event impact for one premium electronics hero. It becomes repetitive when copied to every product.

Regression lesson: the spherical case’s shallow lid recess was initially hallucinated as an extra earbud-shaped bump. A targeted negative-geometry lock fixed it without changing the composition. For unfamiliar electronics, explicitly lock every cavity, seam, port, empty gap, and control count.

### White handheld fan: high-key summer lifestyle

Use pearl white, ice blue, glass, acrylic waves, fabric airflow, droplets, daylight, and an asymmetric editorial layout. This preserved the white fan while making the picture lively without a dark stage.

### Green vivo phone: new-Chinese jade optical gallery

Use ink black, jade, celadon, bronze, a lens-like moon gate, translucent mountains, lacquer stone, vertical serif copy, and museum lighting. This made the circular camera island the visual metaphor and avoided generic cyber-blue styling.

### Orange smart band: urban sports magazine

Use black, warm white, fluorescent orange, a diagonal grid, oversized condensed type, track marks, halftone, torn paper, speed arrows, and a narrow city strip. Keep the watch body single and sharp; allow only strap or background motion echoes.

Regression lesson: the structured editorial system produced high density without confusion because every visual element belonged to one of three containers—headline, running scene, or CTA—and the orange accent repeated across screen, strap, pulse line, badge, and action bar.

## Text discipline lesson

Native generation may invent plausible eyebrow or footer copy even when the main headline is correct. Specify every visible text region in a copy manifest. Use `none` for intentionally blank regions and forbid all text outside the manifest.

## Food, beauty, and multi-SKU regression lessons

- Packaged food reached commercial richness through one pack-result-routine triangle: open box, hero sachet, serving result, and one portability action. Brand color repeated across the H1, package, chips, badge, and CTA.
- Ornate beauty worked best with fewer modules and stronger material proof: macro embossed compact, silk, magnolia, moon-window depth, thin ornamental icons, one seal, and one restrained CTA.
- Six appliances remained readable when organized as anchor/support/accessory tiers. Empty adjacent price-card shapes preserved future exact-copy space without inventing numbers.
- Product-label text belongs to the product truth lock. Poster-overlay copy belongs to the copy manifest. Never move tiny package text into decorative headline or badge regions.

## Lemon tea and IP regression lesson

A high-density red comic beverage poster passed when it used exactly three super-containers: torn-paper headline, giant transparent drink/mascot world, and CTA/footer dock. Product clarity came from locking the cup wall, golden liquid, ice, lemon slices, condensation, wordmark, and splash direction. Character clarity came from assigning one main 3D mascot, one package-printed mascot, and one optional flat headline doodle.

## Weak-snapshot stress-test lessons

- A weak-light transparent serum bottle became premium without product redesign when the prompt separated glass wall, amber liquid, label plane, thick base, dropper, and transparent gaps. A backlit glass disc, edge light, botanical shadow, and foreground refraction supplied richness while keeping the label calm.
- A cluttered single-shoe snapshot survived a strong sports transformation when the exact count, mesh upper, lace path, opening, sculpted midsole, outsole and toe profile were locked. Motion belonged to the runner, wet street, speed marks and diagonal paper system—not to the shoe geometry.
- A glare-heavy soft cosmetic tube stayed truthful when the sealed crimp, flexible wrinkles, minimal label and cylindrical cap were named explicitly. Silk, magnolia, curved mirror depth and pearl light upgraded the scene without turning the tube into rigid packaging.
- For weak inputs, repair capture defects aggressively but reconstruct hidden product structure conservatively. The background may change completely; unsupported product surfaces may not.

## Two-pass exact-copy fan lesson

A real white handheld-fan input passed the full chain at 96/100: concept preflight, text-free key visual, deterministic Chinese overlay, source comparison, and QA gate.

- The generated blank CTA container landed roughly four percentage points lower than planned. Always measure the actual key visual before assigning overlay boxes.
- A decorative arrow glyph rendered as a missing-character box in the selected Chinese font. Keep CTA copy to verified characters or render icons as separate graphics.
- The text-free prompt succeeded because it forbade letters, numbers, pseudo-text, glyphs, and placeholder copy while asking for blank cards explicitly.
- High-key richness came from architecture, airflow fabric, sea depth, glass foreground and reflection—not from extra claims.

## Richness rule

Make the picture lively with directed layers:

- one foreground framing device;
- one large hero product;
- one product-linked interaction effect;
- one environment with depth;
- one disciplined information system.

Every decoration must reinforce theme, motion, material, or conversion. Remove decorations that merely fill gaps.

## Doubao four-category failure audit

Four superficially polished outputs—vacuum bottle, floral dress, running shoes, and portable speaker—exposed one reusable failure: the scene changed, but the poster system did not. All four used a top-centered headline, centered isolated product, and three equal benefit cards at the bottom. This is now a banned generic triptych.

### Vacuum bottle

- Failure: office-and-mountain scenery was generic; steam and ice wrapped the same undivided bottle; steel grade, temperature hours, leakproofing and closure claims were not visibly proven.
- Better route: choose one dominant thermal story or a deliberate two-zone hot/cold diptych; echo the cap/body profile in a thermal arc, condensation boundary, brushed-steel landscape, or temperature-gradient shadow.
- Required restraint: no cross-section, insulation layer, steel grade, capacity, hours, anti-scald or one-touch claim unless supplied.

### Floral dress

- Failure: a beautiful tropical garden still looked like a catalog cutout; the dress floated without plausible support; the three pills added generic copy rather than textile proof.
- Better route: asymmetric fashion editorial with believable hanger/mannequin/invisible-form support, one material macro, directional drape or hem motion, and a season/collection close.
- Required restraint: preserve print repeat, straps, neckline, waist, seams and hem; do not invent a model, colorway, fabric, slimming, breathability, or multiway construction.

### Running shoe

- Failure: a static pair plus generic green speed lines did not prove performance; source count, logo and technology risk increased; numeric weight and cushioning claims were unverified.
- Better route: one exact hero shoe when one is supplied, diagonal crop, outsole-derived lane graphics, environmental motion, impact shadow or terrain interaction. The shoe remains sharp and structurally unchanged.
- Required restraint: no extra shoe, foot, logo, brand technology, weight, rebound, durability or grip claim unless supplied.

### Portable speaker

- Failure: the campfire became the main spectacle while the speaker sat low; disconnected glowing music notes looked decorative and cheap; waterproofing, play time and TWS claims were unverified.
- Better route: make the speaker the anchor; derive acoustic wavefronts from grille/body geometry, let light or nearby surfaces react to sound, and use fire/tent only as secondary context.
- Required restraint: no floating note clip art and no IP rating, battery hours, TWS, surround, wattage or driver claim unless supplied.

### Shared correction

Every new concept must answer five questions before generation:

1. Which two devices are unique to this product?
2. What visible interaction or material proof replaces generic benefit cards?
3. Which foreground element creates depth?
4. How does the bottom close without defaulting to three equal cards or a false CTA?
5. Which factual line is visible, user-supplied, or omitted?

## Batch anti-template check

Before generating, fill this table:

| Product | Theme | Brightness | Axis | Type | Scene/material | Density/motifs | Forbidden reuse |
|---|---|---|---|---|---|---|---|

Reject the plan if two posters share four or more of the following unchanged: brightness, palette, layout axis, type personality, scene/material, information modules, foreground motifs, platform shape.

## Product-reference contract

When using multiple references, state roles explicitly:

- “Reference 1 is style-only.”
- “Reference 2 is the authoritative product reference.”

List visible geometry, controls, materials, labels, count, and orientation. Explicitly forbid category substitution, extra products, extra lenses/buttons, and invented branding.

## Fast fallback rule

Seedream 5.0 Pro remains the default. If it is unavailable and the user authorizes Image2 or another generator, proceed with the same concept, truth lock, prompt, and QA workflow, then disclose the actual model in the delivery.
