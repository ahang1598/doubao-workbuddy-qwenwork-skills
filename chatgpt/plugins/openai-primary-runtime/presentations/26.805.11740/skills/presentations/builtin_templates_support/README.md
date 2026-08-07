# Built-In Template Support

Built-in templates separate reusable authoring guidance from large,
blob-managed static assets.

## Shipped template

- `assets/builtin_templates/<template-id>/` contains only static template assets:
  exact slide modules, previews, registries, content, and design tokens.
- `builtin_templates_support/<template-id>/` contains the checked-in,
  template-specific `ARTIFACT.md`, prompt, and manifest.
- `builtin_templates_support/prompts/` and
  `builtin_templates_support/scripts/` contain guidance and helpers shared by
  every built-in template.

`ARTIFACT.md` is intentionally template-specific. It describes the visual
system, layout vocabulary, typography, and adaptation rules of one built-in
template and should not be reused verbatim for a different source deck.

## Adding a template

1. Add a template-specific folder containing `ARTIFACT.md`, `presentation.md`,
   and `manifest.json`.
2. Produce a source-free static asset ZIP whose top-level directory matches
   the manifest's `assetArchive.root`.
3. Add the ZIP as a bundled-runtime extra file and point
   `inventoryManifestPath` at the checked-in manifest.
4. Keep reusable execution logic in `builtin_templates_support/scripts/`; do
   not copy the same runner into each asset archive.
5. Update the Presentations skill's built-in-template selection guidance.
