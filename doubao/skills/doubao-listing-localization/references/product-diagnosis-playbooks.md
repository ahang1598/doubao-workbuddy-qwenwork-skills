# Diagnosis Playbooks

## Root Cause Map

| Symptom | Common root causes | Evidence to request | First actions |
|---|---|---|---|
| Low clicks | Main image weak, title unclear, price uncompetitive, poor rating, no trust signals, wrong category | PDP, search result screenshot, competitor PDPs, CTR | Compare main image/title/price/rating against official requirements and competitors |
| Low conversion | Weak product detail, missing attributes, price/shipping friction, insufficient reviews, poor variants, fulfillment delay | CVR, PDP, reviews, shipping promise, return policy | Fix PDP completeness, price/offer, fulfillment promise, trust gaps |
| Price displays differently | Coupon, promotion, VAT/tax, marketplace fee display, variant price, automatic pricing, external competitive price, Featured Offer logic | Offer tab, Manage Pricing, coupon/promo settings, PDP screenshots | Trace price from Offer -> Promo -> PDP -> checkout |
| Product unpublished/suppressed | Missing required attribute, image violation, restricted category, policy claim, brand/IP issue, safety complaint | Suppression notice, Account Health, item setup errors | Map notice to official requirement, then propose field fix |
| Image rejected or poor performance | Main image not compliant, text/watermark, stock photo, low resolution, wrong variant, duplicate angle | Image files, PDP, platform image policy | Create image compliance checklist and replacement brief |
| Variant/size issue | Incorrect variation theme, missing size chart, inconsistent SKU, wrong images per variant, shared copy anchored to one child | SKU table, variation setup, selected-child and landing-state evidence, PDP | Extract parent/child field matrix; separate visible selected child from verified default; keep child facts out of shared fields |
| Multi-model compatibility issue | Similar names hide differences in model year, item code, sole/fitment/connector standard, certification, or package contents | Exact SKU/model/year table, manufacturer specifications, test/certification scope | Compare each model independently; block merged compatibility or safety claims until all included models are verified |
| Inventory/fulfillment issue | Stockout, stranded inventory, delayed check-in, WFS/FBA capacity, wrong fulfillment channel | Inventory dashboard, fulfillment settings, IPI/WFS status | Diagnose stock/fulfillment path, hand off logistics if needed |
| Store/platform difference | Account type, local site rules, fulfillment model, taxes, currency, category eligibility | Store type, site, marketplace rules | Compare platform/site requirements and operational constraints |

## Diagnosis Priority

| Priority | Meaning | Example |
|---|---|---|
| P0 | Policy, suppression, safety, IP, or backend block prevents sale | Product unpublished due to restricted category |
| P1 | High-impact conversion or offer issue | Wrong price display, out of stock, no Featured Offer |
| P2 | Content quality and click-through issue | Weak main image, missing bullets, poor attributes |
| P3 | Optimization and testing opportunity | Add more lifestyle images, A/B title, adjust promo |

## Data Request Checklist

Ask for only what matters:

- Platform and country/site.
- Product link, item ID, ASIN, SKU, or screenshot.
- The exact symptom and when it started.
- Seller Center notice/error text if any.
- Current product fields or upload template.
- Price, promotion, inventory, and fulfillment screenshots when relevant.
- Competitor links for comparison.
- CTR/CVR/sessions/orders only when conversion diagnosis is requested.

## Verification Loop

1. Identify official rule or backend field.
2. Extract current visible/backend state.
3. Compare against rule and competitors.
4. Rank root causes.
5. Recommend a minimal fix.
6. Define metric and timeframe to recheck.
7. Re-read all final copy, tables, files, and summary for claim-scope and recommendation consistency.
