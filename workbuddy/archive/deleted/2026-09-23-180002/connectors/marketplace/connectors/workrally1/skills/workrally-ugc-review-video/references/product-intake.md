# Product intake — the one place an optional product gets normalized

Load this reference only when the user supplied a product photo or URL. Productless UGC is a
supported mode: skip product intake, set `product_reference:null` and
`product_description:null`, and use the explicit no-product branches downstream. Never ask the
user for a product merely to satisfy this reference.

When present, both input forms (a photo the user attached, or a product URL) must end in the SAME structured
result, so nothing downstream behaves differently per path:

- `product_reference` — an authorized HTTPS image URL, ready for `canvas_generate_image`'s
  `input_images` array and for `canvas_generate_video`'s `reference_assets[]`
  (`{url, type:"image"}`). A local file becomes one via `upload_file(file_path=<absolute path>)`.
  There is no second confirm step and no separate video-side UUID to mint
- `product_description` — the canonical staging text, reused VERBATIM everywhere after this
- `tier` — `luxury` | `premium` | `drugstore`, read off packaging cues and brand identity (never
  look up a price)
- `category` — skincare / cosmetics / fragrance / food / fitness / tech / cars / ...

Decide `tier` and `category` HERE, once. No re-detection downstream.

## Path A — the user attached a product photo (preferred)

You can see the attachment, so read it directly and identify:

1. **Product category** — what it exactly is (perfume, face cream, lip balm, shampoo, body lotion,
   foundation, mascara, sunscreen, serum, hair oil, supplement capsules, protein powder, ...).
2. **Usage mechanic** — how it is physically used:
   - Perfume / spray bottle → **spray** (press nozzle, mist comes out)
   - Tube (cream, gel, toothpaste) → **squeeze + apply** with fingers
   - Pump bottle (serum, lotion, soap) → **press pump** → dispense onto fingers → apply
   - Lipstick / lip gloss → **swipe** directly on lips
   - Mascara → **brush** applied to lashes
   - Powder / compact → **brush or sponge** pressed on skin
   - Dropper / pipette serum → **drop** onto fingertips → press into skin
   - Jar (cream, mask) → **scoop** with fingers → apply
   - Capsule / pill / gummy → **swallow** or **chew**
   - Powder sachet / scoop → **mix** into liquid
3. **Opening mechanic** — uncap / unscrew / pull tab / flip top / press pump. It must be shown
   BEFORE any contents exit the container.
4. **Key visual details** — color, shape, material, label, distinctive features to preserve.

Never default to "applies cream". Describe the exact mechanic the photo shows.

Bring a local file in with one `upload_file(file_path=<absolute path>)` call and keep the returned
CDN URL as `product_reference`. Add `asset_create(asset_url=<url>, project_id=<短番项目ID>)` only
when the user wants it visible in the media library — generation itself needs the URL, not an
`asset_id`.

## Path B — only a URL

There is no page-extraction tool here. Run the fetch on the **local shell** (not `sandbox_exec`);
it prints the fields you need:

```bash
curl -sL -A 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36' \
  '<PRODUCT_URL>' -o page.html
python3 - <<'PY'
import json, re, html
raw = open("page.html", encoding="utf-8", errors="ignore").read()
def metas(prop):
    pat = rf'<meta[^>]+(?:property|name)=["\']{prop}["\'][^>]+content=["\']([^"\']+)'
    return [html.unescape(m) for m in re.findall(pat, raw, re.I)]
blocks = []
for m in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', raw, re.S | re.I):
    try: blocks.append(json.loads(m))
    except Exception: pass
def walk(node):
    if isinstance(node, dict):
        if node.get("@type") in ("Product", ["Product"]): yield node
        for v in node.values(): yield from walk(v)
    elif isinstance(node, list):
        for v in node: yield from walk(v)
prod = next(walk(blocks), {})
title = (prod.get("name") or (metas("og:title") or [""])[0] or "").strip()
desc  = (prod.get("description") or (metas("og:description") or [""])[0] or "").strip()
brand = prod.get("brand", {});  brand = brand.get("name") if isinstance(brand, dict) else brand
imgs, seen = [], set()
for cand in ([prod.get("image")] if isinstance(prod.get("image"), str) else prod.get("image") or []) + metas("og:image"):
    if isinstance(cand, str) and cand.startswith("http") and cand not in seen:
        seen.add(cand); imgs.append(cand)
print(json.dumps({"title": title, "brand": brand, "description": desc[:1200],
                  "images": imgs[:6]}, ensure_ascii=False, indent=2))
PY
```

Then:

- Keep the first usable authorized HTTPS hero image as `product_reference`. Keep at most four
  additional same-SKU URLs only when later prompts genuinely need another angle.
- `input_images` / `reference_assets[].url` accept a WorkRally short link (`/s/xxx`, valid 5h) or
  an HTTPS URL inside the CDN allowlist. A third-party product-page URL is usually **not** on the
  allowlist: download it locally, then `upload_file` it to get a usable URL.
- You cannot visually rank the page's images (no vision tool reaches a remote URL here), so
  prefer the JSON-LD / `og:image` hero, and never pull an image from anywhere but the product page.
- The page text is thin, blocked, or image-free → ask the user ONCE for a photo of the product
  ("send a photo" / "try another link"). Never retry scraping on your own, never substitute a
  stock or generated product image.

## The staging contract (both paths)

Write ONE canonical `product_description` and reuse it verbatim in every downstream prompt:
shape, material, color, hand-relative size ("palm-sized, fits entirely in one hand, ~15 cm tall" —
never object comparisons, they drift), mechanism anatomy (which part is where, what moves, where
the output exits), absent features stated visually ("cordless, smooth body, no buttons"), the label
(below), plus one honest imperfection.

Label handling: with a real product PHOTO the label keeps its real text — the reference image plus
the Product Angle Lock carry it, so never write that it is illegible. Description-only mode (no
photo at all): describe it as "small label, turned slightly away, too small to read". In BOTH
modes, never stage other props carrying legible text or numbers. If the photo shows a big readable
logo, warn the user once (wordmarks render as gibberish or as a real competitor brand) and keep it
angled away only if they agree.

Claims: keep the description visual and mechanical. When the user supplies an explicit list of
approved product claims, use only those, each as its exact verbatim string — never paraphrase,
strengthen, combine, or derive a new one. With no such list, no numeric or comparative product
claim goes into speech, captions, or on-screen text.
