# Xiaohongshu workflow router

Use Xiaohongshu's own pages as the evidence source when the user asks for Xiaohongshu notes, creators, comments, topics, or in-platform research. Do not use general search snippets as a substitute for opening the relevant note or account page.

Read only the matching workflow:

- Product reviews, gift ideas, inspiration, note collection, or content benchmarking: [collect.md](collect.md)
- Travel routes, transport, accommodation areas, booking, food, or photo-location research: [travel.md](travel.md)
- Like, favorite, follow, comment, or reply: [interact.md](interact.md)
- Drafting or publishing a note: [publish.md](publish.md)

Across all workflows:

- Record direct note links, author, visible publication time, retrieval date, and relevant visible evidence.
- Do not invent engagement counts, prices, claims, authorship, or links. Mark unavailable fields explicitly.
- Prefer a canonical note/share link exposed by the page. If only a search or creator page is accessible, label it as a fallback entry point rather than a direct note link.
- For login, reauthentication, QR/SMS/OTP/CAPTCHA, identity verification, or another human-only checkpoint, immediately follow the mandatory login handoff rule in `SKILL.md`: call `interaction.request_action` with `type="browserControl"`. A text-only request is not sufficient.
- Use `interaction.request_action` with `type="fileUpload"` when the user must choose or upload local media.
