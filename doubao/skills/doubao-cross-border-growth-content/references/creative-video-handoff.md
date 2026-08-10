# Creative Video Handoff

Use this when the user wants finished video, edited video, video variants, TTS video, livestream clip, short ad, or Spark/UGC video assets.

## Handoff Package

| Field | Required content |
|---|---|
| Platform / country / language | TikTok Shop MY, Instagram Reels US, Amazon UK, etc. |
| Video goal | organic, Spark Ads, product education, conversion, live clip, creator demo |
| Product facts | verified product name, material, features, size, included items, visual preservation |
| Audience and scene | target buyer, local use case, setting, occasion |
| Structure | hook, shot sequence, voiceover, subtitles, CTA |
| Specs | count, duration, ratio, captions, cover, safe zone, output language |
| Assets | product photos/video, logo, brand colors, reference links, voice/TTS preference |
| Usage rights | creator authorization status, paid media permission, platform, territory, duration, editing/derivative rights, raw footage rights, music rights |
| No-go | unsupported claims, wrong product details, unsafe scenes, copyrighted music/IP, culture risks |
| Acceptance criteria | product accurate, platform-native, first 3 seconds clear, mobile readable, no claim risk |

## Spark / Creator Ads Fields

When the brief is for TikTok Spark Ads, Partnership Ads, whitelisting, UGC paid amplification, or creator video reuse, include these fields before writing variants:

| Field | Required decision |
|---|---|
| Original asset | creator raw video, posted video URL, product photos, product listing, or missing |
| Authorization | Spark/Partnership authorization granted or still needed |
| Territory | exact countries/regions where paid usage is allowed |
| Duration | usage period, renewal requirement, takedown date |
| Edit rights | crop, subtitle, cutdown, hook swap, voiceover, derivative variants allowed/not allowed |
| Music rights | original music usable for ads, must replace with commercial music, or needs confirmation |
| Disclosure | #ad, paid partnership, affiliate code, or platform-required disclosure |
| Tracking | UTM, affiliate link, discount code, creator ID, content ID |

Do not call a video "Spark-ready" unless authorization, territory, duration, edit rights, and music rights are either confirmed or explicitly marked as missing.

Before giving setup instructions, identify the actual authorization route: Spark Pull, Spark Push, account authorization, video-code authorization, or Affiliate Mass Authorization. Record who initiates it, which account/video is authorized, scope, territory, duration, and current status. These routes are not interchangeable; verify the current official country/account flow and check date rather than turning a remembered process into a universal rule.

## Serial vs Parallel

- **Serial:** one hero video, complex narrative, needs approval before variants, or compliance-sensitive product.
- **Parallel:** multiple hooks, multiple creator personas, multiple languages, or same product facts across several short variants.
- **Video + image parallel:** allowed only after product facts, claims, and local language are locked.

## Video Brief Output

For each variant, provide:

1. variant name;
2. target angle;
3. shot list;
4. voiceover/subtitle;
5. on-screen text;
6. CTA;
7. required assets;
8. no-go;
9. acceptance criteria.

## Tool-Ready Output Shape

When handing off to a creative video tool, include a compact field package in addition to prose:

| Field | Example |
|---|---|
| `variant_id` | `SparkAd_V1_PainHook_MY` |
| `platform_country_language` | `TikTok Shop MY / Malay + English subtitles` |
| `goal` | `Spark Ads conversion` |
| `duration_ratio` | `20s, 9:16` |
| `hook` | `Still struggling with [problem]?` |
| `shot_list` | numbered shots with seconds and required product visibility |
| `voiceover` | local spoken copy |
| `subtitles` | local subtitle copy, separate from voiceover if different |
| `on_screen_text` | exact text and safe-zone placement |
| `cta` | platform-appropriate action |
| `assets_required` | product photo, creator raw clip, logo, listing link |
| `preserve` | product shape, packaging, color, visible included items |
| `avoid` | unsupported claims, wrong accessories, copyrighted music, unsafe scenes |
| `rights` | territory, duration, edit rights, music status |
| `acceptance_criteria` | first 3s clear, mobile readable, product accurate, no claim risk |

## Diagnosis Before Video Fixes

If the user asks for video because ads are not working, first identify whether the problem is creative, traffic, PDP/listing, offer, or fulfillment:

- Low CTR: first frame, hook, thumbnail/cover, relevance to search/audience, product clarity, price shown near competitors.
- Low CVR: PDP/listing quality, reviews, shipping/Prime/FBA, price/coupon, trust assets, claims evidence, checkout friction.
- Missing data: request campaign objective, placements, CTR/CVR/CPC/CPA/ROAS, audience/search terms, product link, and dates.

Only propose video variants after stating which hypothesis the variant is meant to test.
