# Source Map

Use this file before making claims about keywords, platform rules, ranking, or listing requirements.

## Source Priority

| Priority | Source type | Use for | Caveat |
|---:|---|---|---|
| 1 | User-provided product files, links, screenshots, exports | Product facts, current listing, target SKU constraints | Treat as first-party input but still mark fields that are not visible or verified |
| 1 | Platform Seller Center / Brand Analytics / Search Query Performance | Search terms, impressions, clicks, cart adds, purchases, query-to-ASIN data | Permissioned data; if not provided, explain exact export path instead of inventing numbers |
| 1 | Official platform help, policy, Seller University, ads docs | Field limits, prohibited content, image/detail page rules, listing quality guidance | Rules change; verify current page for high-stakes claims |
| 2 | Official marketplace search/category/product detail pages | Competitor titles, bullets, images, price, rating, reviews, variants, A+ modules | Public pages do not prove true sales volume |
| 2 | Retailer, brand, manufacturer, and official product pages | Product specs, compatibility, materials, claims, usage instructions | Prefer official brand/manufacturer pages over reseller summaries |
| 3 | Third-party keyword tools and SEO tools | Keyword ideas, relative trend hints, SERP/marketplace search suggestions | Mark as non-official; do not present as platform truth |
| 3 | Competitor listing text and reviews | Buyer language, pain points, differentiators, objection handling | Do not copy wording or use competitor brands in final copy without risk warning |

## Platform Paths

| Platform | Official / primary paths | Fields to extract |
|---|---|---|
| Amazon | Seller Central, Brand Analytics, Search Query Performance, Search Catalog Performance, Amazon Ads search term report, Seller University, Product Detail Page Rules, public PDP/search pages | title, bullets, description, backend terms, ASIN, category, browse node, images, A+ modules, rating, reviews, query, impressions, clicks, cart adds, purchases |
| TEMU | Seller Center / partner center exports, public product pages, platform category/search pages, user-provided screenshots | title, category, attributes, selling points, image text, price, variants, localized language, compliance prompts |
| AliExpress / Alibaba | Seller tools, public product pages, category pages, supplier/product detail pages | title, attributes, material, size, MOQ, variants, images, buyer-facing claims |
| Etsy | Etsy Help, Shop Manager stats, listing pages, tags, attributes, public search pages | title, tags, attributes, description, images, shop stats, buyer keywords |
| Shopify / independent site | Store product pages, Google Search Console, site analytics, feed data, landing pages | product title, SEO title, meta description, schema fields, page copy, variant data |
| Google Shopping | Google Merchant Center, Content API, product data specification, diagnostics, landing page | id, title, description, link, image_link, price, availability, brand, gtin, mpn, item_group_id, product_detail |

## Source Rules

- If the user asks for "热搜词", "搜索量", "排名", "best seller", "top", or "销量", first state whether live or permissioned data is needed.
- If no live or permissioned data is available, output a verification table with recommended sources and extraction fields.
- Use public competitor listings for wording patterns and field extraction, not for exact sales or search volume.
- Keep facts, assumptions, and recommendations separate.
- For official rules, prefer the official help/policy page and include the verification date when answering high-risk cases.

## Official References

- Amazon listing creation and optimization: https://sell.amazon.com/blog/amazon-product-listings
- Amazon SEO guidance: https://sell.amazon.com/blog/amazon-seo
- Amazon Ads detail page improvement guide: https://advertising.amazon.com/en-us/library/guides/improve-your-products-for-advertising
- Google Merchant Center product data specification: https://support.google.com/merchants/answer/14779112
- Google Merchant Center product data optimization: https://support.google.com/merchants/answer/7380908
- Etsy SEO for shop and listing pages: https://help.etsy.com/hc/en-us/articles/115015663987-Search-Engine-Optimization-SEO-for-Shop-and-Listing-Pages
- Etsy tags: https://help.etsy.com/hc/en-us/articles/360000336307-How-to-Use-Tags-to-Get-Found-in-Search
- Etsy attributes: https://help.etsy.com/hc/en-us/articles/115014502508-How-to-Use-Attributes-When-Listing-an-Item
