# Platform Listing Rules

Use this file to choose output fields and platform-specific checks.

## Amazon

Typical fields:

- Title
- Bullet points
- Product description
- Backend search terms
- A+ Content modules
- Image brief / listing image sequence

Default Amazon structure:

| Field | Recommended handling |
|---|---|
| Title | Brand or product identity + core product term + key differentiating attributes. Keep readable and avoid repetition. Verify current category/store title requirements when exact limits matter. |
| Bullets | 3-5 or platform-allowed bullets depending on category; each should cover one buyer-relevant point such as use, dimensions, contents, material, country of origin, compatibility, or care. |
| Description | Short narrative that explains product benefits, use cases, and specs without repeating bullets verbatim. |
| Backend search terms | Cover relevant long-tail terms and synonyms not already overused in visible fields. Avoid commas, repeated terms, competitor brands, and subjective claims. |
| A+ Content | Use feature modules, scenario modules, comparison tables, brand story, and image-led explanations when Brand Registry allows it. |
| Images | Main image should be clean and accurate; detail/lifestyle images should map to specific selling points. |

Amazon checks:

- Avoid price, promotion, availability, contact details, external URLs, review requests, and all-caps promotional language in detail page content.
- Do not invent Brand Analytics/Search Query Performance or ABA values.
- If user asks for PPC match type or bids, hand off to ads/growth after preparing the SEO keyword map.
- Build a parent/child field map before rewriting a variation family. Do not assume that a size named in the current title is the default child or that title, bullets, images, dimensions, and weight share the same maintenance level.
- Keep child- or sample-specific dimensions, weight, package contents, test results, and compatibility out of parent-shared copy. Use child-specific fields when verified; otherwise use neutral family wording or name all included variants.
- Backend search terms must not repeat visible terms unnecessarily, include unauthorized brands, or introduce unsupported audiences, body locations, compatibility, or use cases.
- When an exact backend limit matters, verify the current category/site rule and calculate the final string's encoded byte length. Report both the result and method; do not report an estimated character count as a byte check.

## Etsy

Typical fields:

- Title
- Tags
- Attributes
- Description
- Images / alt text

Etsy structure:

| Field | Recommended handling |
|---|---|
| Title | Natural buyer-facing title with the most important traits early. Avoid repetition and subjective empty words. |
| Tags | Use up to 13 relevant tags; each tag should be an accurate buyer-minded phrase. |
| Attributes | Use all relevant category-specific attributes because they help buyers find and understand items. |
| Description | First sentence should clearly state what is being sold; include details buyers need before purchase. |
| Images | Multiple high-quality images showing variations, use, scale, and details. |

Etsy checks:

- New listings may need time for search data to stabilize; avoid frequent title/tag churn without performance evidence.
- Tags should be diverse and accurate, not the same phrase repeated with tiny variations.

## Google Shopping / Merchant Center

Typical fields:

- id
- title
- description
- link
- image_link
- price
- availability
- brand
- gtin / mpn
- item_group_id
- product_detail

Rules:

- Match feed title and description to landing page content.
- Put differentiating attributes early in the title.
- Include GTIN when available; if a product has a GTIN but it is omitted, performance may be limited.
- Main image must show the real product and avoid promotional overlays, watermarks, borders, or mismatched variants.
- Google Shopping campaign design belongs to ads/growth; this skill handles feed content quality.

## TEMU / AliExpress / Alibaba

Typical fields:

- Localized title
- Product attributes
- Selling points
- Variant labels
- Image text and detail page copy
- Category and platform-specific required fields

Rules:

- Extract supplier-title facts first, then rewrite as buyer-facing marketplace copy.
- Emphasize accurate attributes, variant clarity, pack quantity, material, size, and usage.
- Avoid unsupported "cross-border hot sale" style claims in final buyer-facing text.
- For low-price marketplace listings, image clarity, variant naming, and attribute completeness are often as important as title SEO.

## Shopify / Independent Site

Typical fields:

- Product title
- Product description
- SEO title
- Meta description
- URL handle
- Product schema fields
- Collection/category copy

Rules:

- Balance marketplace-style keywords with brand tone.
- Make SEO title/meta description match the product page.
- Include structured facts for schema and Google Merchant Center when relevant.
- If the user asks for content marketing pages or blog strategy, hand off outside listing SEO.
