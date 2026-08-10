---
name: computer-use
description: Control Windows apps from ChatGPT
---

# Computer Use

Use this skill to automate the UI of Microsoft Windows apps. It uses SendInput, UI Automation, and Windows.Graphics.Capture screenshots that work even when windows are occluded.

If this plugin is available, read this entire `SKILL.md` once before Windows automation work, before saying Computer Use is unavailable, and before falling back to other Windows automation.

Start with the directions in the Initialize section below. Use `await sky.documentation("<name>")` when you need information about the specific topic they cover:

- `guidance`: core runtime behavior, target-window workflow, screenshot handling, and recovery guidance. You MUST read this before controlling Windows apps.
- `api`: full `sky` API reference. Read this when you need method signatures or object shapes.
- `confirmations`: you MUST read this before deciding whether a Windows UI action needs confirmation

## Initialize

The Computer Use entry point is `<plugin root>/scripts/computer-use-client.mjs`. Import it by absolute path. It loads the bundled `cua_node` `@oai/sky` runtime internally; do not import `@oai/sky` directly, spawn `codex-computer-use.exe`, or build a custom helper protocol client. App approvals and user interruption handling only work through this wrapper.

Run this once per fresh `node_repl` JavaScript session:

```js
if (!globalThis.sky) {
  const { setupComputerUseRuntime } = await import("<plugin root>/scripts/computer-use-client.mjs");
  await setupComputerUseRuntime({ globals: globalThis });
}
```
