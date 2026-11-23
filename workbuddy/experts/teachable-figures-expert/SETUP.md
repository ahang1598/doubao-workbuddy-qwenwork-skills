# Optional local verification (NOT required to use the expert)

Upstream uses Node ≥20 + Playwright only for **dev** visual checks of example HTML.

```bash
cd skills/teachable-figures
# optional: npm install && npx playwright install  # only if you want to re-run upstream tests
```

Do **not** ship `node_modules/` or Playwright browsers in the market zip.
The expert runs as a WorkBuddy skill: produce self-contained offline HTML teaching figures; no external LLM API key.
