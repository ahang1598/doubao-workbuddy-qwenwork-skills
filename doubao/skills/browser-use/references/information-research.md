# Browser research and recommendation quality

Use this reference when the browser task collects current information, compares multiple candidates, or produces a recommendation.

## Ground every claim

- Record the direct page URL, title or item name, visible publication/update time when present, and retrieval date.
- Never invent unavailable prices, metrics, timestamps, authorship, account verification, reviews, or links. Mark missing fields as unavailable or unverified.
- Prefer first-party or authoritative pages for factual claims. For site-specific research, obey the site's reference about whether evidence must remain in-platform.
- Keep conflicting claims side by side and explain the evidence gap. Do not silently choose the convenient version.

## Search in bounded rounds

1. Start with the user's core terms and constraints.
2. Inspect several plausible results; do not select the first result only because its title matches.
3. Refine with one or two natural qualifiers such as audience, scenario, budget, location, model, or date.
4. Stop after a few low-yield rounds, report the coverage and limitations, and ask for a narrower direction only when necessary.

The candidate count is a quality heuristic, not a rigid quota. Prefer a smaller verified set over a larger shallow or fabricated set.

## Make recommendations explainable

- State the criteria before ranking: relevance, source reliability, fit with constraints, evidence depth, freshness, total cost, or another task-specific factor.
- Include diverse candidates when the problem admits meaningful alternatives.
- Default to one primary recommendation plus a small number of alternatives, with short tradeoffs.
- Label time-sensitive details with the observed date. Avoid fixed year assumptions.

## Recover without hiding gaps

- For non-authentication failures such as duplicated, stale, partly loaded, or missing content, try a nearby in-scope entry point or a fresh observation.
- If a blocking login/sign-up modal, visible authentication controls, login-required target functionality, reauthentication, QR/SMS/OTP/CAPTCHA, or identity verification appears, immediately follow the mandatory login handoff rule in `SKILL.md`, even when the observation does not contain `blocked=auth`. The next tool call must be `interaction.request_action` with `type="browserControl"`; do not first dismiss the prompt, change the query, switch sources, or attempt a fallback.
- In multi-source work, handle authentication independently at each site. If the user skips or declines handoff for one site, stop only that site's branch; do not infer that handoff should also be skipped for another site unless the user explicitly says the decision applies more broadly.
- Clearly distinguish completed, partially completed, blocked, and unverified work in the final result.
