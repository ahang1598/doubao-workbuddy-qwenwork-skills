---
name: computer-use
description: Control Windows apps from ChatGPT
---

# Computer Use

Use this skill to automate the UI of Microsoft Windows apps. It uses SendInput, UI Automation, and Windows.Graphics.Capture screenshots that work even when windows are occluded.

If this plugin is available, read this entire `SKILL.md` once before Windows automation work, before saying Computer Use is unavailable, and before falling back to other Windows automation.

Start with the directions in the Initialize section below. Read these bundled Markdown files relative to this `SKILL.md` when you need information about the specific topic they cover:

- `../../docs/guidance.md`: core runtime behavior, target-window workflow, screenshot handling, and recovery guidance. You MUST read this before controlling Windows apps.
- `../../docs/api.md`: full `sky` API reference. Read this when you need method signatures or object shapes.
- `../../docs/confirmations.md`: you MUST read this before deciding whether a Windows UI action needs confirmation

## Initialize

The bundled `cua_node` `@oai/sky` package is the core entry point for Computer Use. Import it directly by package name from the JavaScript session. Do not spawn `codex-computer-use.exe`, search for the helper executable, or build a custom helper protocol client.

Run this once per fresh `node_repl` JavaScript session:

```js
if (!globalThis.sky) {
  const { sky } = await import("@oai/sky");
  globalThis.sky = sky;
}
```
