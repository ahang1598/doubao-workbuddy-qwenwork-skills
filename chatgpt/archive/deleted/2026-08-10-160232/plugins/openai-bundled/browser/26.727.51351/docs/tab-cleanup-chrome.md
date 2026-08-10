# Tab Cleanup

- Before ending a turn after Chrome browser work, call `browser.tabs.finalize({ keep })`.
- Treat `browser.tabs.finalize({ keep })` as the final Chrome browser action of the turn. Do not call Chrome browser tools after finalizing. If more browser work is needed, do it before finalizing, then finalize once with the final tab disposition.
- Omit tabs by default. A tab is worth keeping only when the user needs that live page after the turn; otherwise leave it out of `keep`.
- Omit research, search, source, intermediate, duplicate, blank, error, and login/navigation tabs after you have extracted what you need. If the user asked a question and the answer can be given in the thread, omit the tab even if it helped you answer.
- Keep a tab with `status: "deliverable"` when the tab itself is a user-facing output or requested open page: for example a created/edited document, spreadsheet, slide deck, dashboard, checkout/cart, submitted form result, or a page the user explicitly asked to keep open or inspect directly. Deliverable tabs are left open after the current browser session releases them.
- Keep a tab with `status: "handoff"` only when the task is still in progress and the user or a later turn should continue from that live page: for example a page waiting for user input, login, approval, payment, CAPTCHA, or an unfinished workflow. Handoff tabs release browser control and stay where they are; agent-created handoff tabs keep their existing ChatGPT visual grouping, and a later browser session can still claim them directly.
- Explicitly agent-created omitted tabs are closed. Claimed user tabs, deliverable tabs, and restored tabs without an explicit agent origin are released from browser-session control and left open.
