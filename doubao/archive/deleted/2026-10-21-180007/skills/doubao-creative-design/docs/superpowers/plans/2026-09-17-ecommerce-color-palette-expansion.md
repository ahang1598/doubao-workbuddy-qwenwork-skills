# Ecommerce Color Palette Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand ecommerce detail-page color candidates with existing CSS palettes and selected social-long-image color relationships while preventing unsupported cream/warm-light defaults.

**Architecture:** Keep `EC01–EC08` as the semantic decision layer and link each EC system to a small set of existing `palette.*` implementation candidates. Keep one compact warm-light-neutral sentence in the existing color rules, and import only cross-category color relationships from Social Visual without copying its platform-specific proportions or fixed colors.

**Tech Stack:** Markdown rule files, CSS palette catalog, Python reference checker, one-off Python contract test.

---

### Task 1: Establish the color-strategy contract

**Files:**
- Create temporarily: `/private/tmp/test_ecommerce_color_contract.py`
- Inspect: `references/style/coding/systems/ecommerce-visual-system.md`

- [x] **Step 1: Write the failing contract test**

```python
from pathlib import Path

path = Path("references/style/coding/systems/ecommerce-visual-system.md")
text = path.read_text(encoding="utf-8")

required_phrases = [
    "奶油白、米白等暖浅中性色，仅在用户、确认参考或品牌／商品本身有明确依据时才作为大面积底色，不因品类或“柔和、高级”等气质词自动选用。",
    "从 EC 配色职责落实到 CSS 色板",
    "社媒配色关系的迁移边界",
]

required_palettes = [
    "palette.clinical-cyan",
    "palette.science-blue-orange",
    "palette.cream-pink",
    "palette.osmanthus-cream",
    "palette.burgundy-cream",
    "palette.charcoal-rose",
    "palette.industrial-silver-lime",
    "palette.cobalt-acid",
    "palette.warm-paper",
    "palette.pastry-gold",
    "palette.antique-ochre",
    "palette.oxide-blue-paper",
    "palette.bamboo-olive",
    "palette.moss-letter",
    "palette.botanical-green-gold",
    "palette.silver-cyan-mono",
    "palette.aqua-lime",
    "palette.primary-pop",
    "palette.sky-lime",
    "palette.coral-paper-ink",
    "palette.neon-cyan",
]

required_social_relations = ["C03", "C05", "C07", "C09", "C11", "C12", "C13", "C14"]

missing = [item for item in required_phrases + required_palettes + required_social_relations if item not in text]
assert not missing, f"missing ecommerce color contract entries: {missing}"
```

- [x] **Step 2: Run the test and verify the existing Visual fails**

Run:

```bash
python3 /private/tmp/test_ecommerce_color_contract.py
```

Expected: assertion failure listing the missing compact warm-neutral rule, CSS mapping section, palette IDs, and Social color relations.

### Task 2: Add the minimal strategy-layer rules

**Files:**
- Modify: [ecommerce-visual-system.md](../../../references/style/coding/systems/ecommerce-visual-system.md#决定配色)

- [x] **Step 1: Add one compact warm-light-neutral rule immediately after `## 决定配色`**

The added rule must:

- Limit only large backgrounds.
- Allow them when user, confirmed-reference, brand, or product evidence exists.
- State that category names and “soft/premium” mood words are not sufficient by themselves.

- [x] **Step 2: Add `EC → CSS palette` mapping after the existing EC table**

Use the exact palette IDs listed in Task 1. Keep EC as the decision layer; require `describe` before adoption and implementation reads only after Brief freeze. Keep EC02 and warm-light applications of EC04 consistent with the compact rule.

- [x] **Step 3: Add the Social color migration boundary after the CSS mapping**

Transfer only these relationships:

- C03 → EC03: black/white neutral axis plus one fluorescent color.
- C05 → EC01/EC06: cool white/silver-blue plus one evidence color.
- C07 → EC06/EC08: corporate high contrast with paired foreground colors.
- C09: derive color from real photography season and lighting.
- C11 → EC04/EC08: limited print plates.
- C12/C14 → EC08: pigment/commercial pop contrast.
- C13: continuous diffuse color fields with stable text regions.

State that C01/C02/C04/C06/C08/C10 warm-paper or cream branches do not become ecommerce defaults merely because they were migrated.

- [x] **Step 4: Run the contract test and verify it passes**

Run:

```bash
python3 /private/tmp/test_ecommerce_color_contract.py
```

Expected: exit code 0 with no output.

### Task 3: Verify references and candidate availability

**Files:**
- Verify: `references/style/coding/systems/ecommerce-visual-system.md`

- [x] **Step 1: Run the full Markdown reference checker**

Run:

```bash
python3 scripts/maintenance/check-references.py .
```

Expected: JSON with `"status": "pass"` and an empty `errors` list.

- [x] **Step 2: Verify every mapped palette can be described**

Run three `describe` commands with no more than eight IDs each, covering all 21 IDs from Task 1.

Expected: each command exits 0 and returns every requested palette ID.

- [x] **Step 3: Confirm the diff is limited to the approved files**

Because this directory is not a Git repository, inspect the exact changed sections directly and confirm that production behavior changed only in `ecommerce-visual-system.md`; the design and plan documents are non-runtime records.

- [x] **Step 4: Record edge-case verification**

Check these scenarios against the final wording:

1. Generic beauty request without brand/reference cream evidence does not unlock EC02.
2. Explicit cream brand/reference direction unlocks EC02 normally.
3. Beige product packaging stays faithful without automatically expanding beige to the full page.
4. Food/retro can use warm paper when the product/reference/style provides evidence, but not solely because the deliverable is food ecommerce.
5. Dark palettes remain optional and cannot substitute for product/material hierarchy.

No commit step is included because `/Users/bytedance/Documents/code-design/9:17/doubao-creative-design` is not a Git working tree.
