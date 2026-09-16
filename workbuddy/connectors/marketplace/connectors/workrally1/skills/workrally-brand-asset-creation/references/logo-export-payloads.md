# Exact Brandkit logo-export payloads

Use with `logo-export --input`:

```json
{
  "name": "northline-symbol",
  "logo_svg": "https://replace-with-the-user-supplied-official-logo.svg",
  "delivery": "user",
  "replacements": [],
  "include_monochrome": false
}
```

For an explicitly requested one-color export, add `"single_color": "#101820"`.

For explicitly requested black/white production variants, set `"include_monochrome": true` and add `"primary_color": "#00AEEF"`.

Returned SVG and PNG paths are local files; hand them over as paths. Push one into the WorkRally
asset library with `upload_file` (+ `asset_create`) only when the user asks for it there, or when a
later generation step needs it as an `input_images` URL. Never label a rasterized `.png` as SVG.

This route requires a real SVG source, so it only applies to a **user-supplied official SVG logo**.
WorkRally has no vector image model, so a logo generated in this skill has no SVG to export — see
`logo.md`.
