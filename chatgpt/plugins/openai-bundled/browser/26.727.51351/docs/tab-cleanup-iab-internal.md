# Tab Cleanup

- Agent-created tabs are temporary by default and close when the turn ends. Claimed user tabs are released back to the user by default.
- Call `tab.markDeliverable()` on a tab that should remain open as a user-facing output. The app releases the tab from browser control when the turn ends.
- Call `tab.markHandoff()` only when work should continue in a later turn. Handoff tabs remain under browser control so a later turn can resume them.
- Marks apply only to the current turn. Mark a handoff tab again in a later turn if it still needs to remain controlled.
- If the user asks to close all visible browser tabs in the in-app browser, do not rely on `browser.user.openTabs()` alone. Close current-session tabs from `browser.tabs.list()`, and claim and close released or user tabs from `browser.user.openTabs()`.
