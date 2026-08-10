# Creative Design Handoff

Use this when the user wants ecommerce image assets, main images, selling-point images, comparison images, detail images, social covers, static ad creatives, thumbnails, or product-scene images.

## Handoff Package

| Field | Required content |
|---|---|
| Platform / country / language | Amazon UK, Google Shopping US, TikTok Shop VN, Shopee MY |
| Image type | main image, scene image, selling-point image, comparison, size chart, cover, static ad |
| Product facts | exact product, color, material, package, accessories, variants, dimensions |
| Reference assets | product photo, logo, brand guide, prior listing images, competitor inspiration |
| Composition | background, angle, scene, product size in frame, text hierarchy, callout placement |
| Copy | localized headline, bullets, CTA, units, claim evidence |
| Specs | ratio, size, file type, text/no-text constraints, safe area |
| Preserve | product shape, color, label, package, included items |
| No-go | wrong accessories, invented certifications, fake reviews, unauthorized logo/IP, misleading render |
| Acceptance criteria | accurate product, platform compliant, mobile legible, localized, no unsupported claim |

## Product-Fact Gate

Before writing final image prompts, verify or mark missing:

| Field | Why it matters |
|---|---|
| Product reference image | prevents invented bottle, package, accessory, color, material, or scale |
| Exact image type | main image, selling-point image, detail image, comparison image, static ad, or cover have different rules |
| Platform/site | TikTok Shop VN, Amazon UK, Google Shopping US, etc. changes text, background, and policy limits |
| Product claims | text overlays must match evidence; do not add efficacy, certification, review, or safety claims |
| Dimensions/capacity/variants | size charts, bundles, and capacity callouts must be exact |
| Language and local copy | final image text must be localized and mobile-readable |

If the product reference, ingredients/specs, or capacity are missing, output a reusable brief and a missing-assets checklist. Do not default to a specific product such as serum, essential oil, or gadget unless the user explicitly provided it or you label it as an assumption.

## Image Type Logic

| Type | Purpose | Notes |
|---|---|---|
| Main image | product identity and platform eligibility | often stricter; avoid extra text/background if platform forbids it |
| Scene image | use case and lifestyle | must not imply unprovided accessories or fake scale |
| Selling-point image | communicate benefits | claims must be evidence-backed and readable |
| Comparison image | show differences | compare features or old/new workflow; avoid unsupported competitor attacks |
| Size chart/detail | reduce uncertainty | use verified dimensions only |
| Social cover/ad static | stop scroll and match campaign | keep mobile safe zones and platform tone |

## Prompt Discipline

- Preserve product fidelity before style.
- Include exact text only when verified and localized.
- Do not make the product look more premium, larger, safer, certified, or more capable than evidence supports.
- If platform image rules are uncertain, output the brief and mark verification needed.

## Tool-Ready Design Package

For each image, include a compact package that can be passed to a creative design tool:

| Field | Required content |
|---|---|
| `image_id` | `VN_TTS_Main_01`, `VN_TTS_Benefit_02`, etc. |
| `image_type` | main image, selling-point image, scene image, comparison, size/detail, cover |
| `platform_country_language` | e.g. `TikTok Shop VN / Vietnamese` |
| `goal` | click, explain benefit, reduce uncertainty, prove texture, show usage |
| `ratio_size` | e.g. `1:1 1080x1080`, `3:4 1500x2000` |
| `composition` | product placement, background, scene, text hierarchy |
| `exact_copy` | final localized text; leave blank if text is not verified |
| `assets_required` | product photo, logo, packaging, ingredient/spec proof, prior listing image |
| `preserve` | bottle/package shape, label, color, included items, visible material |
| `generate` | background, layout, icons, callouts, scene props that do not change product truth |
| `avoid` | fake before/after, invented certification, fake reviews, wrong accessories, copied competitor design |
| `acceptance_criteria` | product accurate, local language correct, mobile readable, platform compliant, no unsupported claim |

## Marketplace Image Judgment

When the user asks for marketplace images because listing or ads underperform, connect each image to the buyer problem it is meant to solve:

- Low CTR: main image clarity, product-in-frame size, first visual signal, price/value callout only if allowed, mobile readability.
- Low CVR: size/detail image, use-step image, comparison against old workflow, proof assets, trust badges only if verified.
- Local-market mismatch: language, currency, units, climate/scene, cultural cues, local buyer expectation.

Do not imply that image changes alone will fix traffic if price, shipping, reviews, listing readiness, or ad targeting are the real blocker.
