# Google Slides Routing

Read this file for every request whose target is a native Google Slides deck.

## Existing Native Google Slides Decks

Use the Google Drive plugin's Google Slides skill for edits to an existing native Google Slides deck. Do not round-trip it through a local PPTX unless the user asks.

## Net-New Native Google Slides Decks

Create and verify a local `.pptx` with the Presentations skill first. Produce the native Google Slides deliverable with the Google Drive plugin's presentation import action, `mcp__codex_apps__google_drive_import_presentation`, using `upload_mode: "native_google_slides"`.

Do not use Computer Use, Browser Use, blank-Google-Slides creation plus Google Slides write APIs, or another direct-to-Slides construction path unless the user explicitly asks for that alternate workflow.

If the Google Drive plugin is unavailable, ask the user to install `google-drive@openai-curated`. If the plugin is available but presentation import is missing, ask the user to reinstall or refresh it before continuing.

After successful native import, return the Google Slides link as the primary deliverable. Treat the local PPTX as a build artifact unless the user asks to receive it.
