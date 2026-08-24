# Legacy `.ppt` normalization

Legacy `.ppt` files are binary OLE containers, not OOXML packages. Normalize
the file once before using PPTX inspection, editing, rendering, or QA tools.
Do not unzip it, scan binary records, infer fonts from byte ranges, or enter a
manual OLE reverse-engineering loop.

## Choose the target from the task

| Task needs | Target | Command | Guarantees and limits |
|---|---|---|---|
| Visible text, page appearance, OCR, summary, or a read-only report | PDF | `python scripts/prepare_legacy_ppt.py source.ppt --to pdf --output work/source.pdf` | Cloud-first with one validated local fallback. Preserves visible output, but not editable chart, action, animation, or original font semantics. |
| Editing, template reuse, original font names, hyperlinks/actions, native charts, animations, or OOXML inspection | PPTX | `python scripts/prepare_legacy_ppt.py source.ppt --to pptx --output work/source.pptx` | Discovers an advertised cloud target first, then a registered host bridge, then LibreOffice. Every result must pass PPTX package validation. |

The choice is semantic, not an optimization guess. If the requested answer
depends on native PowerPoint structure, a PDF is not an acceptable substitute.

## Routing rules

1. Run the deterministic normalization command before content exploration.
2. For PDF, `auto` mode prefers `document.convert` and permits at most one
   fallback to LibreOffice.
3. For editable PPTX, read the live `document.convert` Catalog. Try cloud only
   when its `target_format` enum and output extensions advertise `.pptx`.
4. If cloud is unavailable or fails safely, try the host-injected converter at
   `QWENWORK_PPTX_CONVERTER_PATH`, then LibreOffice. The host converter uses
   the fixed `--input PATH --output PATH --target pptx` contract. Never set
   this environment variable from user-provided text.
5. Each registered candidate runs at most once. Do not bounce between cloud,
   bridge, and LibreOffice or retry the same failed command with cosmetic
   argument changes.
6. `LEGACY_PPT_FAST_PATHS_EXHAUSTED` hands control back to the Agent. Perform
   one bounded discovery pass over capabilities already exposed by the cloud
   Catalog, Desktop/VM bridge, and preinstalled host tools. A different trusted
   converter may be used when it has an explicit local file input/output
   contract and its output passes `_valid_pptx` or `validate_pptx.py`.
7. Do not download packages, start a container, invoke arbitrary shell/Office
   automation, or reverse-engineer OLE as part of discovery. If no additional
   trusted capability exists, request a `.pptx` source or report the precise
   semantic limitation.
8. After conversion, continue with the normal PPTX or PDF workflow. Never
   inspect both normalized forms unless the user task independently needs both.
9. Keep the original `.ppt` unchanged and write the normalized file to the
   task workspace.
10. Any converter may normalize unsupported legacy features. Immediately verify
   any task-critical font, action, chart, or animation semantics in the
   converted PPTX. If the requested structure is absent, report it as
   unsupported instead of reconstructing it from raw bytes.

## Terminal outcomes

- `LEGACY_PPT_CLOUD_TARGET_UNAVAILABLE`: execution was explicitly forced to
  cloud, but the live Catalog does not advertise PPTX output.
- `LEGACY_PPT_FAST_PATHS_EXHAUSTED`: known fast paths are unavailable or failed
  safely. Continue with the single bounded capability-discovery pass above.
- `LOCAL_CONVERSION_OUTPUT_INVALID` or `CLOUD_CONVERSION_OUTPUT_INVALID`: stop
  using that output. Do not feed a partial file into later tools.

The deterministic script accepts only the typed cloud operation, one
host-injected absolute executable, and LibreOffice. Broader problem-solving
remains with the Agent under the bounded discovery rules rather than being
encoded as arbitrary executable probing in the script.
