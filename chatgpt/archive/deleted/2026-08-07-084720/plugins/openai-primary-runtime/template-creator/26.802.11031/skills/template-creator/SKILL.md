---
name: template-creator
description: Create or update a reusable personal Codex artifact-template skill. Use when the user invokes $template-creator or asks in natural language to create a reusable template from a reference document, presentation, spreadsheet, ImageGen or Product Design image, email, or Slack message, or explicitly asks to edit or update a passed artifact-template skill. Do not use for one-off creation from an existing template.
---

# Template Creator

Create or update a reference-backed template. Keep the source file inside the skill so later use can reproduce its structure, voice, and visual system precisely.

## Routing

- Manage only personal skills under `${CODEX_HOME:-~/.codex}/skills`.
- Create a new template by default. Use a numbered skill name instead of overwriting an existing template.
- Update only when the user explicitly asks to edit or update exactly one passed artifact-template skill. Treat that passed skill as the exact target; never choose a similarly named template.
- Do not modify an installed or bundled plugin cache. If the passed template is plugin-backed, explain that this skill can update only a personal template.
- Do not create, modify, upload, or publish a plugin. If the request also asks to share the template with a workspace, explain that this skill only manages personal templates.
- A gallery-backed template exists only after `create-template-skill.mjs` succeeds. Never hand-author, rename, or copy a normal skill and report it as an artifact template.

## Create workflow

1. Require exactly one supported reference unless the user explicitly requests a batch. For a batch, complete this workflow separately for every reference:
   - Document: `.docx`
   - Presentation: `.pptx`
   - Spreadsheet: `.xlsx`
   - ImageGen or Product Design image: `.png`
   - Email or Slack message: `.txt`
   - When email or Slack content is pasted rather than attached, materialize the exact content as a temporary UTF-8 `reference.txt` without rewriting it.
2. Infer a concise display name and intended-use description from the reference and request. Infer document, presentation, spreadsheet, and image from the file extension. For an image, set its gallery kind to `imagegen` when the request originates from `$imagegen`, or `product-design` when it originates from `@Product Design`; ask which gallery should use the template when neither or both make the intended target clear. For `.txt`, determine whether the user requested `email` or `slack`; ask if the intended type is ambiguous.
3. Create `preview.png` before packaging:
   - DOCX: use Documents to render the reference and copy its first page PNG.
   - PPTX: use Presentations to render the reference and copy its first slide PNG.
   - XLSX: use Spreadsheets to render the used range of the first visible non-empty sheet.
   - PNG: copy the reference PNG unchanged.
   - Email or Slack: render a legible representative portion of the exact reference text on a neutral canvas. Do not paraphrase, decorate, or invent content.
4. Visually inspect the PNG. Stop if it is blank, clipped, corrupted, or not representative of the reference.
5. Do not create an intermediary request file or use a file-editing tool for script inputs. Set `SKILL_DIR` to the directory containing this `SKILL.md`, load the workspace dependency runtime, and pass the values directly. Before substituting real values into the command, shell-escape each value as one argument for the active shell. Never interpolate a raw path, display name, description, or skill name.

```bash
"$NODE_BIN" "$SKILL_DIR/scripts/create-template-skill.mjs" \
  --reference-path "/absolute/path/reference.docx" \
  --preview-path "/absolute/path/preview.png" \
  --display-name "Standup" \
  --description "Run a structured daily standup with updates, blockers, and owners."
```

Use the Node path returned by the dependency loader for `NODE_BIN`. Do not use a system Node installation.

Pass `--kind "image"` and `--gallery-kind "imagegen"` or `--gallery-kind "product-design"` for image templates. Pass `--kind "email"` or `--kind "slack"` for text templates. The script can infer the three Office kinds and image from their extensions, but Template Creator must pass the image gallery kind explicitly so ImageGen and Product Design templates remain separate. `.txt` always requires `--kind "email"` or `--kind "slack"`.

```bash
"$NODE_BIN" "$SKILL_DIR/scripts/create-template-skill.mjs" \
  --kind "image" \
  --gallery-kind "product-design" \
  --reference-path "/absolute/path/reference.png" \
  --preview-path "/absolute/path/preview.png" \
  --display-name "Launch Visual" \
  --description "Create launch visuals with this product-design direction."
```

```bash
"$NODE_BIN" "$SKILL_DIR/scripts/create-template-skill.mjs" \
  --kind "email" \
  --reference-path "/absolute/path/reference.txt" \
  --preview-path "/absolute/path/preview.png" \
  --display-name "Launch Email" \
  --description "Draft launch emails with this structure, voice, and call to action."
```

6. Read the JSON result. Verify that `skillName` begins with `artifact-template-` and that the generated directory contains `SKILL.md`, `artifact-template.json`, `agents/openai.yaml`, the retained canonical `assets/reference.<ext>`, and `assets/preview.png`. If any check fails, do not claim the template was created or emit an artifact-template card.

## Update workflow

1. Resolve the exact passed artifact-template skill and read its `SKILL.md`, `artifact-template.json`, `agents/openai.yaml`, retained reference, and preview. Stop if it is not a direct child of the personal skills directory or if more than one target was passed.
2. Preserve the skill folder name and every file or behavior the user did not ask to change.
3. Apply the requested edit:
   - For reference content or visual changes, use the matching artifact, image, or text workflow to edit a temporary copy of the retained reference, render a new preview from it, and visually inspect the result.
   - For display-name or intended-use changes, preserve the current reference and preview unless the request also changes them.
   - For instruction-only or other skill-owned text changes, edit only the requested files directly and keep the manifest and agent metadata consistent.
4. When the reference, preview, display name, or description changes, pass the existing kind and values for every unchanged field directly to the script. For an image template, also pass its existing `galleryKind` as `--gallery-kind`. Do not create or edit a request file:

```bash
"$NODE_BIN" "$SKILL_DIR/scripts/create-template-skill.mjs" \
  --mode "update" \
  --skill-name "artifact-template-standup" \
  --kind "document" \
  --reference-path "/absolute/path/updated-reference.docx" \
  --preview-path "/absolute/path/updated-preview.png" \
  --display-name "Standup" \
  --description "Run a structured daily standup with updates, blockers, and owners."
```

5. The script validates the existing template kind, preserves additional skill-owned files, and replaces the package atomically without changing its skill name.
6. Verify every requested change in the target directory and confirm there are no staging or backup directories left behind.

## Response

After verification, replace the placeholders with the script result and respond with the applicable paragraphs followed by the card directive:

Here’s your {displayName} template.

### How to find templates

Find it in the **Template Gallery** when @{kind} is added to the prompt.

### How to use a template

Tag ${skillName} and describe what you want to build.

### Sharing

Personal Templates are private by default. To share one, you can ask Codex to:

- Package the Template into a new Plugin or Add the Template to an existing Plugin
- Share plugin with team or entire workspace

Whoever you share this template with can then install the plugin to use any of the templates inside!

::artifact-template{skill_name="{skillName}" skill_directory="{skillPath}" display_name="{displayName}" artifact_kind="{kind}"}

Formatting rules:

- Include the **How to find templates** section for document, presentation, spreadsheet, and image templates. Omit its heading and sentence for email and Slack templates because their source plugins do not open the Template Gallery.
- Keep the paragraph wording and punctuation unchanged apart from replacing `{displayName}`, `{skillPath}`, `{skillName}`, and `{kind}`.
- In the how to find template section, substitute @{kind} with the matching gallery-enabled mention: `@Documents`, `@Presentations`, `@Spreadsheets`, `$imagegen`, or `@Product Design`. For image templates, use the generated template's exact `galleryKind`; never treat ImageGen and Product Design as interchangeable. Preserve the literal `@` or `$` so Codex renders an unquoted mention.
- Do not tell users to add `@Gmail`, `@Outlook Email`, or `@Slack` to open the Template Gallery. Email and Slack templates are used by tagging their saved template skill directly.
- In the usage sentence, preserve the literal `$` before the exact returned `skillName` so Codex renders an unquoted skill mention.
- Put the directive on its own line, using the exact returned `skillName`, `skillPath`, `displayName`, and lowercase `kind` values.
- Escape directive attribute values when needed so the directive remains valid.
- For a batch, repeat the applicable response block for each created or updated skill.

## Constraints

- Do not search for or fetch remote templates.
- Do not create or edit `request.json` or any other intermediary request file. Pass script inputs through command-line flags so Template creation never surfaces a code-file edit card.
- Do not delete or sanitize the retained reference; the user chose reference retention for fidelity.
- Do not send an email or post a Slack message merely because a template was created or invoked.
- Do not create or mutate workspace plugins or marketplaces.
- Do not add Artifact.md package generation here. The artifact plugins own template distillation and creation.
- Do not modify global skill metadata or protocol files.
