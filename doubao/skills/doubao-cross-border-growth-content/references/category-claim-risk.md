# Category Claim Risk

Read this before generating claims, scripts, captions, image text, or creator instructions for sensitive categories.

| Category / theme | Content opportunity | High-risk claims | Safe handling |
|---|---|---|---|
| Beauty / personal care | routines, texture, how-to, before/after if verified | medicalized effects, permanent results, exaggerated before/after, filter deception | use sensory and routine language; require evidence for efficacy |
| Health / supplements / weight loss | habit support, packaging, lifestyle scenes | disease treatment, weight-loss promises, body shaming, clinical claims | avoid treatment or guaranteed result language; hand off to compliance |
| Food / kitchen | taste, recipe, convenience, use cases | health cures, allergens omitted, nutrition claims, unsafe prep | require ingredients/allergen proof for claims |
| Kids / baby | safety, ease, parent use cases | age safety, certifications, dangerous demos, children in risky scenes | require age/certification/warning evidence |
| Electronics / battery | demo, compatibility, charging, setup | fake specs, battery safety, water resistance, certifications, compatibility guarantees | use supplier specs only; verify certifications |
| Pet products | real use, cleaning, training | animal harm, medical effects, guaranteed behavior change | avoid harmful scenes and medical promises |
| Gifts / holidays / patterns | occasion, recipient, personalization | copyrighted characters, trademarked art, religious/political insensitivity | check IP and culture before generating |
| Eco / sustainability | reusable, material story, packaging | biodegradable, carbon neutral, non-toxic, certified claims | require certification or official evidence |

## Claim Rules

- Product facts must come from user evidence, visible product details, official specs, or verified listing content.
- Treat specific performance and health wording—including fast charging, self-cleaning, instant/seconds-level output, low-calorie, fat-burning, and guaranteed efficacy—as blocked unless the exact claim and supporting proof are on the fact whitelist.
- Do not add certifications, test results, customer review quotes, sales numbers, awards, or before/after outcomes unless provided.
- Use “may help”, “designed for”, “made to”, and concrete use-case language only when supported.
- If a claim changes legal, health, safety, import, certification, or ad-policy risk, hand off to `doubao-ecommerce-compliance-tax-logistics`.
- Claim safety depends on the target country and platform. When the country/site is missing, give the safest cross-market wording and state which country/platform needs verification.
- For before/after content, prefer process records over result promises: same lighting, same angle, same device, no beauty filter, time-stamped sequence, personal-experience wording, and an on-screen disclaimer.
- If a product has special registration, clinical tests, certification, or efficacy data, require the exact document or approved claim language before using stronger claims.

## Before / After Production Checks

Use this for beauty, personal care, fitness, health, cleaning, pet behavior, electronics performance, and any visual transformation claim.

| Check | Requirement |
|---|---|
| Platform / country | TikTok Shop US, Vietnam, EU, Japan, Amazon, Meta, etc.; rules and wording differ |
| Product status | ordinary cosmetic, special cosmetic, medical device, supplement, electronics, or unknown |
| Evidence | clinical/test report, official claim file, product registration, user-provided real record, or none |
| Visual truth | same person/object, same light, same angle, same camera, no filter, no misleading edit |
| Wording | subjective/process language if evidence is weak; no guaranteed, instant, permanent, or medicalized result |
| Disclaimer | visible and long enough to read; e.g. results may vary / personal experience |
| Asset retention | keep original unedited footage/screenshots in case platform review or appeal is needed |

## Country / Platform Sensitivity Pattern

When exact policy verification is not available, use these routing instincts:

| Market / platform | Safer handling |
|---|---|
| TikTok / TikTok Shop | first-person routine, product demo, no exaggerated transformation, clear disclosure for ads |
| Meta / Instagram ads | avoid implying the viewer has a personal flaw; be careful with before/after and body/skin attributes |
| Amazon creative | avoid external CTA, aggressive urgency, unsupported claims, and before/after where marketplace rules restrict it |
| Japan / Korea beauty | whitening/brightening claims may require special cosmetic or quasi-drug registration |
| EU / UK | claims need evidence and should avoid medical, environmental, safety, or guaranteed-performance overreach |
| Southeast Asia | local platform and country rules vary; localize language and keep efficacy conservative unless registration supports it |

## Script And Asset Iteration For Risky Claims

For claim-sensitive scripts or image briefs, output:

- a conservative primary version;
- one longer version if the user asked for a short script but production needs more detail;
- exact banned words and safe replacement words;
- subtitle/safe-zone and disclaimer notes;
- a shooting or asset acceptance checklist;
- A/B test variables that do not increase claim risk, such as hook, scene, texture shot, CTA, subtitle language, or timeline length.

## No-Go Examples

- “Cures acne in 7 days”
- “Guaranteed weight loss”
- “100% safe for all babies”
- “FDA certified” without evidence
- “Official Disney style” without rights
- “Biodegradable” without proof
