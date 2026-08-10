# Tab Cleanup

- Before ending a turn after in-app browser work with multiple tabs, call `browser.tabs.finalize({ keep })` when it is supported by the backend.
- Treat `browser.tabs.finalize({ keep })` as the final browser action of the turn. Do not call browser tools after finalizing. If more browser work is needed, do it before finalizing, then finalize once with the final tab disposition.
- Omit tabs by default. A tab is worth keeping only when the user needs that live page after the turn; otherwise leave it out of `keep`.
- Omit research, search, source, intermediate, duplicate, blank, error, and login/navigation tabs after you have extracted what you need.
- Keep a tab with `status: "deliverable"` when the tab itself is a user-facing output or requested open page. Deliverable tabs are left open after the current Browser Use run releases them.
- Keep a tab with `status: "handoff"` only when the task is still in progress and the user or a later turn should continue from that live page.
