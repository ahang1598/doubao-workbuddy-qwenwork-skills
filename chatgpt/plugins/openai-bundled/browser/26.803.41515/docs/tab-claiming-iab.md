# User Tab Claiming

- A prompt link shaped like `plugin://browser@openai-bundled?mention=tab-v1&browserId=...&tabId=...&title=...&url=...` without `source=extension` is an explicit user mention of an open in-app browser tab. Decode its query parameters before choosing a browser or tab.
- Resolve each tab mention from `agent.browsers`; never assume an `iab`, `browser`, or other binding from an earlier turn still exists. If `agent.browsers` is unavailable, first run the idempotent Bootstrap block from this skill.
- Call `agent.browsers.list()`, select the `iab` browser whose `metadata.codexSessionId` exactly equals `browserId`, and store `await agent.browsers.get(match.id)` as a local `mentionedBrowser` handle.
- IAB `openTabs()` ids are claim handles, not the `tabId` embedded by the composer. Call `mentionedBrowser.user.openTabs()` and find the exact returned object whose `providerTabId`, `title`, and `url` equal the decoded `tabId`, `title`, and `url`. Pass that exact object to `mentionedBrowser.user.claimTab(tab)`.
- The title and URL are an accepted snapshot used to fail closed when the mentioned tab has changed. If the exact tab no longer exists or has changed, report that it is unavailable; do not silently claim or open a different tab.
- To take over an already-open in-app browser tab, call `browser.user.openTabs()`, choose the matching returned tab by its visible title and URL, then pass that exact object to `browser.user.claimTab(tab)`.
- Claiming makes that existing tab part of the current Browser Use run and returns a normal controllable `Tab`. Reuse the returned tab for navigation, Playwright, screenshots, CUA, and content reads.
- Do not pass `openTabs()` ids to `browser.tabs.get(...)`. `browser.tabs.get(...)` only resolves tabs that the current Browser Use run is already controlling.
- Prefer claiming the existing in-app browser tab when the page you need is already open, instead of opening a duplicate tab to the same URL.
