# Product Poster QA Rubric

Inspect the generated image at full size and as a small mobile thumbnail. Compare it directly with the input product photo.

## Hard rejection conditions

Reject and regenerate if any condition is true:

- product silhouette, package structure, label position, logo, count, or dominant color materially changed;
- a recess, opening, transparent gap, port, flat lid, or screen edge became a new object, bump, button, lens, or decoration;
- product is duplicated without being requested;
- a multi-SKU poster changes the requested SKU count, substitutes a category, or attaches a price/tag ambiguously to the wrong product;
- a third-party logo, certification, price, specification, or endorsement was invented;
- hero headline, CTA when used, or closing slogan contains gibberish, a wrong character, or an unintended extra word;
- English copy uses broken words, accidental mixed-language overlay copy, inconsistent capitalization, or unnatural literal translation;
- a hand, lid, cable, wheel, handle, or transparent material is visibly malformed;
- a transparent drink has an impossible fill level, liquid outside the cup wall, hidden label, melted cup edge, or implausible fruit/ice scale;
- a mascot campaign contains an unrequested second 3D character, inconsistent character design, or a main mascot that blocks the sellable product;
- important text or the product label is cropped or covered;
- CTA falls into the bottom safe area when a CTA is required;
- a publicity poster contains an unnecessary button, arrow, search bar, purchase instruction, or pseudo-interactive control;
- the poster claims something not visible or user-supplied;
- overall concept does not match the selected style family or campaign objective.
- multiple posters in one batch reuse the same template with only a color or product swap;
- a single standard poster uses the banned generic triptych: top-centered headline, centered product, and three equal bottom cards with no stronger product-specific proof;
- the concept relies on an attractive generic lifestyle backdrop but has fewer than two visual devices derived from the product’s form, material, use, or desire;
- decorative effects contradict product physics or are disconnected clip art, such as undivided steam-plus-ice, floating musical notes, or generic speed lines that do not originate from product interaction;
- apparel floats without plausible support or changes the exact neckline, straps, print repeat, seams, waist, or hem;
- a footwear or speaker poster invents a product count, brand technology, numeric specification, performance label, acoustic mode, IP rating, or battery claim;
- the poster feels empty because it lacks a purposeful interaction layer and depth cue;
- the bottom 20% has no intentional conversion, trust, or slogan closure;
- at thumbnail size the headline, product silhouette, or intended closing anchor disappears;

## 100-point scorecard

### A. Product fidelity — 30

- silhouette and proportions: 8
- color and material: 6
- packaging, closure, and accessories: 6
- logo/label placement and legibility: 6
- count and orientation: 4

Minimum acceptable: 25/30.

### B. Message and conversion — 25

- one clear buying promise: 6
- headline readable in two seconds: 5
- product immediately identifiable: 5
- benefits support the promise: 4
- conversion poster: CTA and offer path are clear; publicity poster: non-interactive brand/theme closure is clear: 5

Minimum acceptable: 20/25.

### C. Layout and typography — 20

- hierarchy and reading order: 6
- spacing and safe zones: 4
- product-to-copy balance: 4
- short text rendered accurately: 4
- consistent type/card/icon system: 2

Minimum acceptable: 16/20.

Award full `short text rendered accurately` points only after checking every overlay string against the copy manifest. For prices, legal text, specifications, model numbers, or dense copy, prefer deterministic `typeset_overlay.py`; native generated text must be inspected character by character.

For English, also inspect word boundaries, capitalization, apostrophes, hyphens, brand/model spelling, and whether line breaks preserve natural phrases. Physical package labels may remain in their original language; accidental mixed-language overlay copy may not.

### D. Art direction — 15

- palette supports product and theme: 4
- lighting/material quality: 4
- scene and props are purposeful: 3
- visual family is recognizable but not copied from one brand: 2
- thumbnail impact: 2

For batches, also verify that every pair differs in at least four style-distance dimensions: brightness, palette, layout axis, type personality, scene/material, and density/motifs.

Minimum acceptable: 11/15.

### E. Trust and finish — 10

- no fabricated claims or brand confusion: 4
- no obvious generation artifacts: 3
- no unintended text: 2
- output resolution/format correct: 1

Minimum acceptable: 8/10.

## Acceptance threshold

Accept only when:

- the saved concept JSON passes `scripts/preflight_check.py`;
- the saved QA JSON passes `scripts/qa_gate.py`;
- no hard rejection condition is present;
- total score is at least 90/100;
- every category meets its minimum.

For batches, run all QA JSON files in one `qa_gate.py` command. Every pair must differ in at least four of the six declared style dimensions. A separate single-image pass is not sufficient evidence for batch diversity.

The user’s target is 90+, so 85–89 is “promising but revise,” not final. For dense promotion layouts, never trade product fidelity or copy accuracy for visual intensity.

## Revision diagnosis

| Symptom | Likely cause | Revision |
|---|---|---|
| Product looks generic | Truth lock too vague | List 4–8 visible invariants first in prompt |
| Product gains a bump/object | Negative geometry was not locked | Name every recess, opening, gap, port, and exact control count |
| Product is too small | Too many scene instructions | Set explicit width/height share and remove props |
| Headline loses attention | Competing badges/cards | Keep one H1 and demote all other modules |
| Poster feels cheap | Too many glows, borders, gradients | Use one material system and one accent effect |
| Poster feels empty | No supporting proof | Add one benefit row or purposeful prop triangle |
| Text is wrong | Too much native copy | Shorten or use exact-copy two-pass mode |
| Extra tiny copy appears | Eyebrow/footer unspecified | Supply a complete copy manifest and explicitly forbid all other text |
| Background fights the label | Similar contrast/texture | Add calm halo, tonal separation, or shallow depth |
| Style is generic | Only adjective-based prompt | Add one specific scene metaphor and lighting direction |
| Conversion is weak | No next action/offer zone | Add a clear CTA and verified offer mechanism |
| Publicity looks transactional | Button, arrow, or action copy was added by habit | Remove UI-like controls and use a non-interactive slogan or brand line |
| Dense poster is chaotic | Modules lack containers | Group into headline, hero, and conversion containers |
| Multi-SKU feels flat | All products have equal scale | Rebuild as anchor/support/accessory pyramid |
| Price cards are ambiguous | Cards float between products | Place each card within one product-width; use empty cards until exact-copy pass |
| Batch feels repetitive | Same template reused | Re-route styles and replace scene, axis, type, module shapes, and depth language |
| Single poster feels templated | Top headline + centered product + three equal bottom cards | Replace at least the axis, evidence mechanism, module shapes, product overlap, and bottom close |
| Poster is not lively | Only product and backdrop exist | Add purposeful foreground, interaction, and environmental depth layers |
| Pretty but generic | Lifestyle background is doing all the work | Add two devices derived from product form/material/use and one visible proof |
| Effects feel cheap | Disconnected notes, speed lines, glows, or stickers | Tie one coherent effect to grille, sole, cap, fabric, liquid, airflow, or another true geometry |
| Claims feel plausible but unverified | Category convention was treated as evidence | Mark every support/benefit visible, user-supplied, or omitted; delete unsupported lines |
| Drink becomes a splash sculpture | Transparent structure was not locked | Restate cup wall, fill line, label, ice, slice, and splash-behind-product rules |
| IP scene feels chaotic | Mascot roles are undefined | Keep one 3D hero, package print, and at most one flat sticker |
