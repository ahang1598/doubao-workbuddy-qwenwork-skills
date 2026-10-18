# MCP Apps

The `mcpapps` backend controls existing MCP Apps opened in a side-panel tab in the current task.
Apps shown only inline in the conversation do not appear in its tab list. If needed, ask the user to expand the app.

Use `browser.tabs.list()` to find the app, then `browser.tabs.get(id)` to select it.
This backend cannot create or navigate tabs. Closing the app invalidates its tab handle.
If a handle becomes unavailable, list the tabs again before selecting the app.

Use the documented Playwright locators to inspect the app, click controls, and fill fields.
Clicks use synthetic events. Native pointer and keyboard operations are unavailable.
Locator actions use the shared browser action checks and wait for elements to become ready.
Locator timeouts are supported. Forced clicks, modifiers, and non-left clicks are unsupported.

Use `tab.playwright.frameLocator()` to locate controls inside an embedded website.
Chain `frameLocator()` calls for nested frames. Website access may require approval before entering each frame.
Navigation or replacement of an approved document invalidates access to it.
Screenshots of apps containing embedded frames and clicks inside transformed frames are unsupported.
