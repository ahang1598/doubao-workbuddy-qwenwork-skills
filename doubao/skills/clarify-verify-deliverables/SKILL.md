---
name: clarify-verify-deliverables
description: Use when the agent is asked to generate, edit, integrate, or deliver files/content from user-provided materials, especially for 需求模糊, 附件读取, 图片编辑, PPT生成, 表格口径, 全部加入, 日期歧义, 交付复核, Logo替换, 配音视频, Excel统计, 文件打包, or 素材确认 tasks.
---

# Clarify and Verify Deliverables

Use this skill for image/PPT/spreadsheet/video/document/file-delivery work where the output depends on user-provided materials, ambiguous requirements, or a final artifact that must be checked before handoff.

## Workflow

1. **Classify the deliverable and lock the source set.**
   - Decide whether the task is image editing, PPT, Excel/table statistics, video/audio, copy/docx, or packaged files before choosing tools.
   - Concrete convention: for image edit tasks with current attachments, use the current message's file or link as the authority; if both a local path and URL are present, read the local path first when the environment says so, then use the current URL for tools that require URL input. Do not reuse an older CDN URL or historical attachment for `图一`/`图二` unless the user confirms it is the same asset.
   - Concrete convention: when a user says `图片2这款水泵替换之前图片1中的水泵`, map `图片1` to the target scene and `图片2` to the replacement product, then edit only the pump region.

2. **Surface blocking ambiguity before generating the final artifact.**
   - Ask or state defaults when ambiguity changes the result: style, page count, target language, date, statistical口径, table层级, whether `全部加入` means every item, which regions must be preserved, or which material corresponds to which output.
   - Concrete convention: `2026-05/2` is a blocking date ambiguity; confirm whether it means `2026-05-02` or `2026-05-22`, or produce clearly labeled alternatives instead of silently choosing one.
   - Concrete convention: for a vague `请做一个PPT`, confirm or infer from the uploaded image whether the target is a summary deck, an English translation, or a redesign; if the user later says `请改为两页` and then `请总结为两页，不是只剩下两页`, treat the requirement as two summary pages, not deleting all but two existing slides.

3. **Confirm material coverage and constraints in measurable terms.**
   - For `全部加入`, count the source items before layout; if capacity is limited, confirm whether to use one-item-per-slide, same-page collage, appendix, or curated selection.
   - Concrete convention: when adding all image cases into a PPT, compute coverage as `included_source_count / total_source_count`; do not claim “全部加进来” if only a selected subset such as 48 images was included.
   - Concrete convention: for batch image processing, validate output count equals successful input count; for resize/format jobs with stated specs, check every file matches the requested format and dimensions such as `JPEG` and `450×450` before zipping.

4. **Use the direct tool path for the current material.**
   - Avoid needless downloads, Bash retries, or format detours when the attachment can be read or passed directly to the relevant tool.
   - Concrete convention: `image_edit`-style URL-only tools should receive uploaded/current attachment URLs in `image_reference_url_list`; local files should be uploaded once to obtain URLs only when direct local input is unsupported.
   - Concrete convention: for PPT template work, use the uploaded `.pptx` only when template identifiers/page details are actually available; `ppt_write`/`ppt_refine` prompts must not invent image links, and image references must come from real uploaded or generated URLs.

5. **Generate in small verified steps.**
   - For high-risk edits, make a sample, preview, or scoped change before batch generation or final packaging.
   - Concrete convention: for wall/space edits like `药食同源`, remove original frames only if requested, preserve structural elements explicitly named by the user such as `窗户` and `柱子`, and add the exact visible phrase `药食同源` when requested.
   - Concrete convention: for Logo/brand replacement, keep the uploaded Logo's shape, letters, color relationship, font proportions, and brand lockup; do not invent an unofficial Logo or change the mark unless the user asks for redesign.

6. **Validate by artifact type before delivery.**
   - Images: re-read/OCR the result for text, spelling, coverage, occlusion, changed regions, preserved regions, Logo shape, and product identity.
   - PPT: verify slide count, page intent, source-image coverage, figure/page mapping, layout overflow, text overlap, and whether the download link points to the latest version.
   - Tables/Excel: compare against the original workbook, list all sheets/row counts/fields before cleaning, lock table hierarchy, detect city-year mismatches and abnormal jumps, and reconcile totals before writing prose.
   - Video/audio: transcribe or inspect captions, confirm every subtitle/voice line is present, detect voice/BGM balance, and ensure original audio is muted when the request says to keep only the new narration.
   - Documents/packages: verify filenames, current-date assumptions, extension compatibility, file opens successfully, directory contents, and link accessibility.
   - Concrete convention: for audio narration with 5 subtitle sentences, use ASR or readable transcript review to confirm all 5 sentences exist before mixing; if BGM is present, inspect voice and BGM loudness instead of relying only on a prompt.
   - Concrete convention: for multi-sheet Excel cleaning, list every `sheet`, row count, and field first, then confirm whether sheets should be vertically merged before producing detail-level and daily-level tables.

7. **Stop on anomalies and repair before handoff.**
   - If you find a missing sentence, spelling error, abnormal data jump, unclear numerator/denominator, invalid link, unreadable attachment, image mismatch, or audio imbalance, do not ship the unchecked version.
   - Concrete convention: for AE or clinical-style statistics, confirm analysis set, denominator, deduplication rule, whether grade can be counted repeatedly, and missing-value handling before reporting percentages or drawing figures.
   - Concrete convention: if output upload/download fails, first verify the file exists and opens, then upload once through a supported attachment or public-link path; do not repeatedly give local `file://` paths or the same failing link.

8. **Deliver with a concise audit trail.**
   - State what materials were used, what assumptions were made, what was validated, what files are included, and any unresolved limitations.
   - Concrete convention: when handing off revised docs/PPT/PDF/scripts, include the latest filename or link, the number of pages/slides/files delivered, and the specific checks passed, such as “14页讲稿完整”, “128个PPT标题已全量核对”, or “输出数量=成功处理数量”.
   - Concrete convention: for sensitive files such as政务/审计 materials, disclose whether the link is an external/public upload before using that path.

## Boundaries

- Do not generate final files when requirements, source material, dates, statistics, or table hierarchy are still materially ambiguous; `2026-05/2` must be resolved to `2026-05-02` or `2026-05-22` before a single dated chart is treated as final.
- Do not substitute history, old URLs, or previous attachments for current materials without user confirmation; `图一`/`图二` references and `image_reference_url_list` must point to the current turn's intended assets.
- Do not claim full coverage when only a subset was used; for `全部加入`, disclose `included_source_count / total_source_count` and any selection rule.
- Do not use summary or aggregate artifacts as the sole authority for calculations; for Excel jobs, first inspect every `sheet`, row count, and field, then reconcile derived outputs.
- Do not change Logo shape, brand rules, required user text, preserved image regions such as `窗户`/`柱子`, or source table hierarchy without confirmation.
- Do not conceal defaults, missing assets, anomalies, failed reads, tool limitations, or format constraints; for batch image resizing, failed `JPEG` or `450×450` checks must be reported before packaging.

## Mini example

User: “把全部案例图片加入这个培训PPT，并给我下载链接。”

Response pattern:
1. Count the source images and read the target PPT/page capacity.
2. Confirm coverage rule if every image cannot fit cleanly: one-per-slide, collage, appendix, or curated subset.
3. Generate or update a small sample section, then batch the rest.
4. Validate `included_source_count / total_source_count`, slide count, title-image mapping, and download link.
5. Deliver the latest link with the coverage count and any layout assumptions.
