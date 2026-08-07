---
name: "excel-live-control"
description: "Control an open or active Microsoft Excel workbook through the ChatGPT add-in or connected session. Use when the user tags the Microsoft Excel app in Codex or follows up on an established live Excel task. Do not use for standalone spreadsheet files or Google Sheets."
---

# Excel Live Control

Inspect, edit, analyze, format, and verify the workbook in the selected live Microsoft Excel session. Use connected-document tools for workbook reads and writes; use Computer Use only for application setup, target confirmation, and focus management.

On initial entry, complete the setup gates in order before session discovery. On follow-ups, reuse only the verified target and rediscover after workbook or add-in lifecycle changes.

Resolve every referenced file relative to this skill folder. Do not load the sibling artifact skill or its artifact-tool instructions while this live route is active.

## Hard Routing Rules

Use this skill only when explicitly tagged or when the request clearly targets the Microsoft Excel desktop application, an open, active, or connected workbook in Excel Desktop, a selected range in Excel Desktop, the ChatGPT add-in for Excel, or a follow-up edit on the live-control path. For generic requests such as "create a spreadsheet," "create a workbook," or "create an Excel file" without explicit targeting of the Microsoft Excel desktop application or ChatGPT add-in, use the local workbook-authoring `Spreadsheets` skill instead. Stay on the live-control path unless the user explicitly switches targets; keep follow-up edits on the same path.

Routing selects the execution and delivery surface only; it does not override requested workbook content or a supplied reference/template.

Setup is part of the task. Use Computer Use only for setup checks and focus management, then use connected-document tools for workbook reads and writes. If a setup gate or required live capability is unavailable, stop and use the applicable exact guidance below. Do not silently switch to artifact authoring, open an unrelated workbook, or edit workbook cells through Computer Use.

Keep user-facing language to "Microsoft Excel", "ChatGPT add-in for Excel", "open workbook", "connected Excel session", or "live Excel control"; avoid internal connector/backend names.

## Setup State Machine

Complete these gates in order. A later gate cannot prove that an earlier gate passed.

Checklist: Excel app open -> intended workbook active and unambiguous -> ChatGPT add-in installed -> pane open -> signed in -> connected-document tools available -> target workbook registered.

### 1. Open Microsoft Excel And Establish The Target Workbook

Use Computer Use to inspect the Microsoft Excel application.

- If Microsoft Excel is installed but closed, open it.
- If Microsoft Excel is unavailable, use the exact **Excel unavailable** guidance below.
- If Excel shows its start screen or has no workbook open, open the workbook named by the user. If the user did not name an existing workbook, create a blank workbook.
- Wait until the workbook title, worksheet grid, and ribbon are visible. The Excel start screen is not a workbook.
- If several workbook windows are open, identify the intended workbook by title. Do not assume that the frontmost workbook is the target.
- If the request depends on the current selection, verify the selected sheet and range. If the selection is missing or ambiguous, ask the user to select it or provide an exact sheet and range.

### 2. Determine Whether The ChatGPT Add-in Is Installed

Inspect the Home ribbon only after a workbook grid is active.

- A visible `ChatGPT` button on the ribbon is positive evidence that the add-in is installed.
- If the button is absent, open **Home > Add-ins** and look for **ChatGPT** published by **OpenAI, LLC**. Do not infer that the add-in is missing only because its task pane is closed.
- If ChatGPT is not present in the ribbon or the installed add-ins list, treat the add-in as not installed.

For a missing add-in, give the user these exact choices:

1. Open the official Microsoft Marketplace listing: https://marketplace.microsoft.com/en-us/product/office/WA200010215
2. Or, in Excel, go to **Home > Add-ins**, search for **ChatGPT**, verify that the publisher is **OpenAI, LLC**, and choose **Add** or **Get it now**.
3. Return to the target workbook and open **ChatGPT** from the ribbon.

Installing an add-in is a user-controlled software-install action. Ask the user to complete the final install step, then resume inspection. If the Microsoft Marketplace or Office add-in store is blocked by organization policy, ask the user to contact their Microsoft 365 administrator. The official OpenAI setup and admin-deployment guidance is at https://help.openai.com/en/articles/20001063-chatgpt-for-excel/.

### 3. Open The ChatGPT Add-in Pane

If the add-in is installed but its pane is not visible, click **ChatGPT** on the Home ribbon. Allow a few seconds for the task pane to load, then inspect the pane again.

- A ribbon button without a visible task pane means installed but not open.
- A task pane titled **ChatGPT** means the add-in is open, but it does not by itself prove that the user is signed in.
- If Excel shows an add-in load or restart error, retry opening the pane once. If the same error returns, stop and tell the user what Excel displayed. For a recurring Windows SSO add-in error, direct the user to OpenAI Support as described in the official setup guidance.

### 4. Verify ChatGPT Sign-in

Inspect the contents of the open task pane.

- A normal chat surface such as **New chat** with the composer text **Ask anything, @ for context** is positive evidence that the add-in is signed in.
- A **Sign in**, **Log in**, **Get started**, account-choice, or workspace-access screen means sign-in is incomplete.
- Do not infer sign-in from the ribbon button, the pane title, or a previously signed-in browser session.

If sign-in is incomplete, ask the user to take over and finish sign-in with the ChatGPT account and workspace they intend to use. The user must handle credentials, account choice, SSO, and MFA. If the workspace says the add-in is disabled, the user needs a ChatGPT workspace administrator to enable **ChatGPT for Excel and Sheets** in workspace permissions. Resume only after the normal chat composer is visible.

### 5. Verify Connected-Document Tool Availability

After Excel, the target workbook, the open add-in pane, and sign-in are all verified, check whether `list_document_sessions` is available in the current Codex thread.

- If the tool is unavailable, do not report that the workbook failed to register. The current Codex thread did not load the connected-document tool surface.
- Tell the user to confirm that the Spreadsheets plugin is installed or reinstalled, then start a new Codex thread and retry the Microsoft Excel request. A thread does not necessarily acquire newly installed plugin tools after it has started.

### 6. Verify Workbook Registration

Call `list_document_sessions(surface="excel")` only after the previous gates pass.

- If exactly one session matches the target workbook, select it.
- If several sessions match and the target is unclear, ask the user which workbook to use.
- If sessions exist only for other workbooks, do not send commands to them. Activate the intended workbook, open its ChatGPT pane, keep the pane visible, and retry discovery.
- If no Excel session exists, keep the target workbook active, select a cell in it, keep the signed-in ChatGPT pane open, wait briefly, and retry once.
- If no session appears, close and reopen the ChatGPT pane once, wait for the normal composer, and retry once.
- If the workbook still does not register, tell the user that Excel and the add-in are ready but Codex cannot see a connected session. Ask the user to reopen the target workbook or restart Excel, then reopen ChatGPT and sign in if prompted. Do not loop indefinitely.

Workbook registration is tied to the current workbook and add-in lifecycle. Rediscover sessions after the workbook is renamed or saved under a new name, after the add-in reloads, after Excel recovers or restarts, or when a previously working command reports a missing or stale session. Never reuse an `executor_session_id` merely because its workbook title looks similar.

### Exact User Guidance For Incomplete Gates

Use the smallest applicable message and wait for the user when their action is required:

- **Excel unavailable:** "I cannot find the Microsoft Excel desktop app. Install or make Microsoft Excel available, open it, and tell me to continue. I will not switch this request to another spreadsheet workflow unless you ask me to."
- **Target workbook unclear:** "Microsoft Excel has more than one workbook open, and I cannot safely identify the target. Tell me the workbook title to use, or bring that workbook to the front and tell me to continue."
- **Add-in missing:** "Microsoft Excel and the workbook are open, but ChatGPT for Excel is not installed. Install the OpenAI add-in from https://marketplace.microsoft.com/en-us/product/office/WA200010215, or use Home > Add-ins in Excel and search for ChatGPT by OpenAI, LLC. Open ChatGPT from the ribbon when installation finishes, then tell me to continue."
- **Installation blocked:** "Your organization is blocking the Microsoft Marketplace or the ChatGPT add-in. Ask your Microsoft 365 administrator to deploy ChatGPT for Excel using the admin guidance at https://help.openai.com/en/articles/20001063-chatgpt-for-excel/. After the add-in appears in Excel, open it and tell me to continue."
- **Pane closed:** "ChatGPT for Excel is installed, but its task pane is closed. Open ChatGPT from the Home ribbon and keep the pane visible, then tell me to continue."
- **Signed out:** "The ChatGPT pane is open, but sign-in is not complete. Please finish sign-in, account/workspace selection, and any MFA in the pane. When you see New chat and the Ask anything composer, tell me to continue."
- **Tools unavailable:** "Excel and ChatGPT for Excel are ready, but this Codex thread does not have the connected Excel tools. Reinstall or enable the Spreadsheets plugin if needed, then start a new Codex thread and retry this request."
- **Wrong workbook registered:** "Codex can see an Excel workbook, but it is not the workbook you asked me to use. Activate the target workbook, open its ChatGPT pane, and tell me to retry. I will not send commands to the other workbook."
- **Workbook not registered:** "Excel and the signed-in ChatGPT pane are ready, but Codex cannot see this workbook yet. Keep the target workbook active, reopen the ChatGPT pane, and tell me to retry. If it still does not connect, reopen the workbook or restart Excel and open ChatGPT again."

## Live Commands

Before live commands, fetch the selected session's tool schemas with `get_document_tool_schemas`, then call `execute_document_command` with the exact `executor_session_id`, schema-valid args, and a caller-stable `idempotency_key`. Treat advertised schemas as the live-control contract.

Default to direct live workbook tools when the selected session advertises them: `read_ranges`, `search_workbook`, `list_items`, `write_range`, `clear_range`, `update_sheet`, `update_workbook`, `copy_range_to`, `read_range_image`, `read_sheets_metadata`, `resize_range`, `update_sheet_view`, `format_range`, `chart`, `table`, and `pivot_table`. The session may also advertise `run_officejs`; use it only under the Office.js gate below.

### Live Workbook Quality Checklist

For generated workbooks, source-to-workbook conversions, analytical trackers, and substantial workbook edits, apply the shared workbook quality rules and live completion rules in this skill before final response.

Minimum live verification:
- Inspect key values and formulas after writes; resolve formula errors, blank outputs, broken references, and obvious mismatches with the requested logic.
- Follow `features/charts.md` for chart source and object verification. For tables and PivotTables, verify source ranges before creation and confirm the expected native objects with `list_items` when available.
- Use `read_range_image` for charts, dashboards, dense presentation tables, or substantial layout changes; fix blank charts, clipped headers or numbers, unreadable formatting, and obvious layout overflow.
- For long multi-sheet builds, verify and format each user-facing sheet before moving far ahead; do not defer all content checks and layout repair until the end.
- For dashboards, reports, scorecards, and trackers, apply the dashboard/report quality floor from `style_guidelines.md` and chart decision rules from `features/charts.md` when those files are required.
- Do not treat successful setup, a completed command, or a saved workbook as task completion until the workbook content has passed the relevant checks.

When the user expects a file from a live Excel session, save through the selected session only when an advertised command supports save or export behavior. If no such command is available, report that limitation and leave host-global save or recovery unchanged.

If the selected session does not advertise a tool needed for the request, follow the workbook-registration rediscovery rules once if the workbook or add-in changed. Otherwise report the missing live capability and wait for the user to repair setup or explicitly switch targets.

## Office.js Gate

Before calling `run_officejs` for any reason, read `officejs.md` completely in the current turn and follow its decision boundary and instructions, even when the schema is already available. The hard routing rules above continue to govern setup, Computer Use, and fallback behavior.

## Out Of Scope

Do not use live Excel control for Google Drive, Google Sheets, or other cloud spreadsheet connector requests.

Do not claim live control can install desktop apps, change OS or Excel settings, enable macros, use COM/win32com, run native print/PDF/export/page-setup workflows, bypass workbook protections, or perform commands not advertised by the selected session.

Treat spreadsheet-processing code questions as software implementation or debugging unless the user also asks to control a connected Excel session.

## Bundled Guidance

- `style_guidelines.md`: required when generating or substantially formatting a workbook.
- `features/charts.md`: read when creating or editing charts, or when a visual summary would clarify KPIs, comparisons, trends, breakdowns, rankings, or progress.
- `officejs.md`: read completely before using `run_officejs`; do not read it for direct-tool-only work.

Load only the relevant files in this skill folder. Do not follow references from the sibling artifact skill.

## Domain Requirements
You must read these domain rules when the request clearly relates to the domain, but do not load domain guidance for unrelated tasks unless asked:
- Finance and investment banking: `domain_guidance/financial_models.md`
- Corporate finance and FP&A: `domain_guidance/corporate_finance_fpa.md`
- Healthcare: `domain_guidance/healthcare.md`
- Marketing and advertising: `domain_guidance/marketing_advertising.md`
- Scientific research: `domain_guidance/scientific_research.md`

Instruction precedence for workbook content, layout, and formatting is: user request > reference/template > domain and formatting defaults.

## Making edits on a spreadsheet or using an uploaded reference or template.
- Before modifying: ALWAYS study and match the existing format, style and conventions when making edits by rendering and viewing the image. Read related values and formulas.
- For visual fix requests, start with the smallest plausible local change. Do not apply sheet-wide autofit, wrapping, or restyling unless requested.
- Ensure existing formulas, layouts, structures, and patterns are consistent. For example, if asked to add another column or row to a table and there is conditional formatting applied to the whole table, it should extend to the new column or rows as well.
- Keep edits targeted unless a broader change is clearly necessary. Exceptions are when there's dependencies, e.g. a dynamic chart that is based on the range of values in a table and a new row is added, the chart should also update.
- Extend conditional formatting if needed to keep style consistent for an area or table.
- Never overwrite formatting for spreadsheets with established formats, unless requested or to extend an added range.

## Importing or extracting data from screenshots or reference images
- When a reference image or screenshot is provided, use appropriate data formats (e.g. number/date formats) based on the workbook topic, audience and purpose instead of trying to recreate the rendered format with just text. Preserve numeric/date usability even when the screenshot shows locale-specific punctuation or currency symbols.
- Use formulas when appropriate and correct: For screenshot recreation, do not bulk-write numeric tables as all static values until you have separated any clearly formula-derived ranges; test adjacent numeric rows/columns for exact repeated relationships such as sums, differences, products, ratios, or constant multiples, then keep inputs hardcoded and write derived ranges as formulas.
- Match visible styling, but do not infer intentional formatting from ambiguous image artifacts such as zoom, antialiasing, or compression. Infer font weight only from relative contrast or clear semantics; if all visible text has the same apparent weight, use normal weight.

## Handling queries and questions
- The user may ask questions about the sheet instead of requesting an edit or a change. Simply answer those questions about the spreadsheet based on the context available rather than making an edit the user didn't intend for. Use the selected workflow's read tools to inspect relevant values, formulas, tables, and objects.
- For a read-only question, do not modify or export the workbook.
- Locate the requested output by its row and column labels and period, inspect its displayed value and formula, and trace formula precedents to labeled assumptions or raw inputs instead of stopping at an intermediate total.
- Explain calculations with the workbook's displayed values and preserve units and period conversions. For broad questions about assumptions or drivers, rank the inputs that actually drive the requested output rather than inferring from nearby labels.

## Error Recovery
On first tool or API error:
1. Read error text.
2. Consult the selected workflow's targeted help or schema discovery only if needed.
3. Retry with minimal patch (not full rewrite).
4. Continue from existing workbook state.

Do not loop indefinitely on similar failures.

## Formula Rules
- Place assumptions and raw data in dedicated cells or clearly delineated input ranges, following the reference workbook's organization when one is provided.
- Keep lookup, mapping, scoring, and quality-control rules in visible cells or tables and reference them from formulas instead of hardcoding the logic.
- Derived values must be formulas (not hardcoded) and legible.
- Keep calculations formula driven, and prefer consistent formula patterns across a range where possible for readability. For example, formulas should be consistent across all projection periods.
- Use absolute/relative references correctly for fill/copy behavior.
- Use references instead of hardcoded or magic numbers inside formulas e.g. Use `=A5*(1+$A$6)` instead of =A5*1.05
- Formulas should be simple, legible and **easily auditable**. Use helper cells for intermediate values rather than performing complex calculations in a single cell. Users should be able to trace the model from inputs to outputs easily.
- No harcoded numbers inside calculation areas unless explicitly allowed. Always ensure color formatting conventions are properly applied.
- For any complex formulas or important assumptions, add comments to cells to explain.
- Always reference cells on other Excel sheets using the format ='Sheet Name'!A1, wrapping the sheet name in single quotes every time since quotes are required for any spaces or special characters.

### Ensure formulas are correct
- Checklist: No formula errors, all cell references are correct, no off-by-one errors in ranges, edge cases (zero values, negative numbers) are handled, no unintended circular references.
- For source-backed analyses and summaries, spot-check representative outputs and reconcile key totals with source definitions.

## Data Formatting Rules
- Store numbers, percentages, currency, and dates as typed spreadsheet values, not preformatted strings. Use text only for true identifiers such as ZIP codes, account IDs, SKUs, or labels.
- Use Excel-invariant number/date format codes, not locale-specific display strings. Examples include `#,##0`, `#,##0.0`, `0.0%`, `0.00%`, `"$"#,##0`, `"$"#,##0.00`, `yyyy-mm-dd`, `mmm yyyy` but choose the format that best fits the data.
- Percentages: When not specified or no reference is provided, use 1 decimal for most internal/analytical cells, 0 decimals for user-facing/dashboard outputs, and 2 decimals where small differences in rates matter.
- Do not swap `.` and `,` in format codes to mimic locale separators; separators are controlled by spreadsheet/render locale. Use `0.0%`, not `0,0%`, and `#,##0`, not `#.##0`.
- Choose the appropriate format for readability. Match precision to meaning: counts use `#,##0`; rates usually use `0.0%` or `0.00%`; currency uses whole units unless cents matter.

## Quality Guidelines
- Build correct, readable workbooks for the intended audience with clear structure, consistent formatting, reliable formulas, and useful outputs. Keep them as simple as practical.
- After autofit and wrapping, cap oversized column widths and row heights.
- Make workbooks easy for another person to update, trace, and audit without the original author.

## Completion

- Complete a live edit only after the connected workbook contains the requested changes, key values and formulas have been inspected, and native objects have been confirmed when relevant.
- Use `read_range_image` or the advertised equivalent for charts, dashboards, dense presentation tables, or substantial layout changes. Fix material clipping, overlap, blank charts, unreadable formatting, and visible formula errors before finishing.
- Do not require a local `.xlsx` export unless the user explicitly requests one and the selected session advertises a supported save or export command.
- For question-only requests, answer from the connected workbook context without editing unless the user asks for a change.
- If setup or a required live capability is blocked, use the smallest applicable user guidance from this skill and wait. Do not silently switch to artifact authoring.

## Source, Comment, And Attachment Rules

- Keep source notes compact: record the source name, section or table label, URL when available, and enough context to audit the number.
- For financial models, cite model-input sources in cell comments; for researched row-wise tables, include source URLs in a dedicated source column.
- If the authenticated profile provides a display name, use it as the threaded-comment author unless the user requests another name. Default to `User`.
- Use bundled extraction libraries only for supporting analysis. Keep auditable and user-editable calculations in workbook formulas, then write results through the connected Excel session.
