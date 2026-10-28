# Taobao and Tmall workflow

Use this workflow for product search, comparison, store reliability checks, and cart actions on Taobao or Tmall.

## Establish the decision criteria

Infer or obtain the product, required features, variant, quantity, budget, delivery destination if relevant, and preferences such as official store, return policy, warranty, or delivery speed. Do not block on optional preferences; state reasonable assumptions.

## Research and compare

1. Search within Taobao or Tmall using short product and constraint phrases.
2. Inspect multiple relevant product pages from distinct sellers when available.
3. Record only visible facts: exact title, selected variant, current displayed price and conditions, store name, official/flagship indicators, sales or review signals, shipping, returns, warranty, direct link, and retrieval date.
4. Treat coupons, member prices, cross-store discounts, and pre-sale deposits as conditional. Do not present them as the unconditional final price.
5. Prefer reliability and constraint fit over the lowest headline price. Flag mismatched variants, suspiciously low prices, unclear sellers, or weak after-sales terms.
6. Return one primary choice and a small number of alternatives with concise tradeoffs.

If login, reauthentication, CAPTCHA, SMS/OTP, QR verification, region confirmation, or another human-only checkpoint blocks research, immediately follow the mandatory login handoff rule in `SKILL.md`: call `interaction.request_action` with `type="browserControl"`. A text-only request is not sufficient. Re-observe with fresh refs after control returns.

## Add to cart

1. Open the exact chosen product and verify the title, seller, price condition, variant, quantity, shipping destination, and stock.
2. Use fresh refs to select variant and quantity. Re-observe the selected state.
3. Before the first account-changing cart action, follow [action-verification.md](action-verification.md). If authorization or user control is required, call `interaction.request_action` with `type="browserControl"` and name the exact product, variant, quantity, and action.
4. After the action, verify the cart contains the intended item and that no unintended item or quantity changed.

Adding to cart is not authorization to check out, place an order, or pay. Never automate payment credentials. For checkout, order placement, or payment, hand control to the user with `interaction.request_action` and stop until control is returned.

## Deliver the result

Include:

- recommended item and why it best matches the constraints;
- alternatives and their tradeoffs;
- visible price conditions, variant, seller, and direct links;
- cart action status, if requested;
- unknown, conditional, blocked, or unverified fields.
