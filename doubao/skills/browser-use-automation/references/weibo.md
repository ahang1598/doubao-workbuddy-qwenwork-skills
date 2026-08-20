# Weibo workflow

Use this workflow for Weibo in-site search, public-post evidence collection, timelines, account interactions, drafting, and publishing.

## Choose a mode

- **Research:** search posts, topics, accounts, and public reactions; produce an evidence-backed summary or timeline.
- **Interaction:** like, favorite, follow, comment, or reply to an exact target.
- **Publishing:** prepare a draft, fill the composer, and publish only after required user handoff.

## Research constraints

- When the user asks specifically for Weibo search, trends, public opinion, topics, or super-topics, use traceable Weibo pages as the evidence base: `weibo.com`, `m.weibo.cn`, `s.weibo.com`, or `weibo.cn`.
- Do not use search-engine snippets or repost sites as evidence. If the user requests cross-platform research, keep non-Weibo sources in a separately labeled section.
- Record direct links, author/account, visible verification indicator, visible post time, retrieval date, and a short page-grounded summary. Do not invent engagement counts or verification status.
- Prefer first-party statements, official or institutional accounts, direct participants, and original posts. Filter obvious spam, lottery bait, unattributed reposts, and duplicate low-information posts.
- For evolving events, build a time-ordered evidence table. Present conflicting claims together, mark unresolved gaps, and use cautious language.
- If login, reauthentication, CAPTCHA, SMS/OTP, QR verification, or another human-only checkpoint blocks the in-platform evidence, immediately follow the mandatory login handoff rule in `SKILL.md`: call `interaction.request_action` with `type="browserControl"`. A text-only request is not sufficient. Do not replace missing Weibo evidence with outside claims without clearly changing the requested scope.

A useful report normally includes scope and retrieval date, key findings with links, a timeline or viewpoint table when relevant, conflicts or gaps, and a compact evidence list. Match the user's requested format; do not impose fixed document or code-block counts.

## Like, favorite, follow, comment, or reply

1. Resolve the exact post, account, or comment from a direct link or from title/author/content context. If several targets match, do not guess.
2. Read [action-verification.md](action-verification.md) and inspect the current state so an already-active toggle is not reversed.
3. Prepare exact comment or reply text and show it to the user when required by the host policy.
4. When authorization or personal user control is required, call `interaction.request_action` with `type="browserControl"` and identify the target and action.
5. Re-observe and verify the resulting state. Report an ambiguous outcome as unverified.

## Draft and publish

1. Ground factual claims in the collected evidence and retain direct links in the working notes.
2. Draft content for the requested purpose and tone. Separate unverified claims and avoid overstating uncertain developments.
3. Fill the composer only when the exact account, text, attachments, mentions, topic tags, and visibility are known.
4. If the user must select an attachment, call `interaction.request_action` with `type="fileUpload"`.
5. Before the final publish control, call `interaction.request_action` with `type="browserControl"`, explaining the account, post summary, visibility, and that the user should review and publish or return control.
6. After control returns, verify whether the post was published and capture its direct link if available. Never claim publication from a filled composer alone.
