# Official Source Map

Use this map before diagnosing product pages, item setup, images, prices, inventory, or platform policy issues.

## Source Priority

| Priority | Source type | Use for | Caveat |
|---:|---|---|---|
| 1 | Seller Center / Merchant Center / Seller University / Policy Center | Listing requirements, product suppression, unpublished reasons, listing quality tools, offer status, price/inventory state | Often permissioned; without screenshots or exports, give verification path only |
| 1 | Official help, Marketplace Learn, public platform guides | PDP rules, image requirements, item setup fields, listing quality criteria, category/attribute standards | Check country/site and update date |
| 2 | Official API / developer docs | Product, category, price, inventory, offer, status, and error fields | API access does not imply user authorization |
| 2 | Public product detail pages and marketplace search/category pages | Visible product fields, competitor display, image, price, review, variants, fulfillment badges | Public pages do not prove backend status or sales |
| 3 | Third-party tools and competitor behavior | Benchmarking and supplementary diagnosis | Never use as policy authority |

## Platform Resource Map

| Platform | Official resources to check | Diagnose with these fields |
|---|---|---|
| Amazon | Seller Central Manage Inventory, Add Products, Listing Quality Dashboard, Featured Offer / pricing health, Inventory Performance Dashboard, Product Detail Page Rules, Seller University, Sell on Amazon listing guides, Amazon Ads PDP improvement guide | product identity, title, images, bullets, description, A+ eligibility, search terms, category, browse node, variations, price, quantity, fulfillment channel, Featured Offer status, suppression notice, IPI/inventory health |
| Walmart Marketplace | Seller Center item setup, Walmart Item Spec, Marketplace Learn content standards, image guidelines and requirements, listing quality guidance | item spec version, category, required attributes, main/additional images, product name, key attributes, price, inventory, variant, unpublished reason |
| TikTok Shop | Seller Center, Product Listing Policy, Product Detail Pages & Listing Quality Guidelines, List & Manage Products, Prohibited / Restricted Product Policies, shop health tools | title, description, brand, images, videos, category, variations, product disclosures/warnings, stock, price, listing quality tier, policy warning |
| Shopify / Independent | Shopify product/admin help, product media and variant docs, inventory/pricing settings, theme PDP, Google Merchant Center diagnostics, Search Console | product title, media, variants, inventory, price, availability, landing page, schema/feed fields, diagnostics |
| AliExpress / Alibaba | Seller Center, product publishing docs, open platform/API docs, public product pages | category, attributes, title, images, SKU, price, stock, logistics template, policy warning |
| Ozon | Seller Help, Seller analytics, product card requirements, category/attribute docs, public product pages | title, category, attributes, images, price, stock, warehouse/FBS/RFBS, product card score, moderation status |
| Shopee / Lazada | Seller Centre, Business Advisor, product listing help, category/attribute requirements, API docs | product name, category, attributes, images, price, stock, promotions, logistics, product status |

## Finding Official Resources When Missing

If the target platform is not covered or the policy may have changed:

1. Search the platform's official seller help or policy center with the exact issue terms: `product listing requirements`, `image requirements`, `item setup`, `product detail page`, `listing quality`, `suppressed listing`, `price`, `inventory`, `variant`, `category attributes`.
2. Prefer pages under official seller domains, for example Seller Center, Seller University, Marketplace Learn, Seller Help, developer docs, or official academy/university pages.
3. Record source URL, title, country/site, update date if visible, and which fields/rules were extracted.
4. If only third-party pages are available, mark the policy as unresolved and give the official path to verify.

## Seed Official References

- Amazon product listings guide: https://sell.amazon.com/blog/amazon-product-listings
- Amazon Ads PDP improvement guide: https://advertising.amazon.com/en-us/library/guides/improve-your-products-for-advertising
- Walmart Item Spec: https://marketplace.walmart.com/item-spec/
- Walmart product image guidelines: https://marketplacelearn.walmart.com/guides/Item%20setup/Item%20content%2C%20imagery%2C%20and%20media/Product-detail-page%3A-Image-guidelines-%26-requirements?locale=en-US
- TikTok Shop List & Manage Products: https://seller.tiktok.com/list-manage-product
- TikTok Shop Product Listing Policy: https://seller-us.tiktok.com/university/essay?from=policy&identity=1&knowledge_id=3196690250417921&role=1
