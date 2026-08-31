---
name: tencent-docs-operations
description: Use when the user invokes $tencent-docs-operations, mentions Tencent Docs Operations, or requests supported Tencent Docs Operations operations.
---

# Tencent Docs Operations

## Overview

Use this skill for requests that match the verified Tencent Docs Operations capability boundary. Select a live callable operation from the catalog and report provider evidence without inventing unsupported facts.

## Core Rules

- Use the bound `tencent-docs-operations` MCP only when its live callable tools are available in the current runtime.
- Select the narrowest live callable operation that directly answers the user’s request.
- Follow the live callable interface when it differs from this guide; do not invent operation names, identifiers, records, statuses, or results.
- Treat provider output as evidence and label model interpretation separately.
- Do not use shell commands, direct HTTP calls, or hand-written protocol messages to recreate or probe the connector.
- Keep credentials, private data, and authorization material out of prompts, logs, and final answers.
- Require explicit confirmation before writes, deletes, sends, purchases, permission changes, or other external side effects.

## Tools

- `doc.accept_all_revisions`: Accepts all revisions in a Word document.
- `smartsheet.add_fields`: Adds multiple smart-sheet fields in one operation.
- `smartsheet.add_records`: Adds multiple records to a smart sheet in one operation.
- `sheet.add_sheet`: Adds a worksheet with a specified name and position.
- `smartsheet.add_table`: Adds a worksheet to a smart-sheet document with initial settings.
- `smartsheet.add_view`: Creates a smart-sheet view with a name, filters, and displayed fields.
- `doc.ai_format_pure_text`: Converts plain text into a formatted Tencent document.
- `manage.async_import`: Starts asynchronous document import after upload and returns a task ID.
- `check_skill_update`: Checks whether the current Skill has an available update.
- `sheet.clear_link`: Clears link for the worksheet.
- `sheet.clear_range_all`: Clears range all for the worksheet.
- `sheet.clear_range_cells`: Clears range cells for the worksheet.
- `sheet.clear_range_style`: Clears range style for the worksheet.
- `smartsheet.commit_changeset`: Commits changeset for the smart sheet.
- `doc.compare_documents`: Compares two Word documents for content and formatting differences.
- `ocr.toexcel`: Recognizes content in one to nine images and creates an online spreadsheet.
- `ocr.toword`: Recognizes content in one to nine images and creates an online document.
- `manage.copy_file`: Copies file for the Tencent document or file.
- `doc.copy_format`: Copies format for the Word document.
- `manage.create_file`: Creates Tencent online documents, sheets, smart documents, forms, slides, diagrams, folders, or links.
- `create_flowchart_by_mermaid`: Creates an online flowchart from Mermaid text.
- `create_mind_by_markdown`: Creates an online mind map from nested Markdown headings and lists.
- `create_slide`: Uses built-in AI to create or edit slide content and layout.
- `create_smartcanvas_by_mdx`: Creates a richly formatted smart document using MDX or Markdown.
- `create_space`: Creates space for the provider resource.
- `create_space_node`: Creates a folder, document, or link node in a space tree.
- `doc.create_with_markdown`: Creates with markdown for the Word document.
- `sheet.delete_dimension`: Deletes dimension for the worksheet.
- `smartsheet.delete_fields`: Deletes fields for the smart sheet.
- `manage.delete_file`: Deletes file for the Tencent document or file.
- `smartsheet.delete_records`: Deletes records for the smart sheet.
- `sheet.delete_sheet`: Deletes worksheet for the worksheet.
- `delete_space_node`: Deletes space node for the provider resource.
- `smartsheet.delete_table`: Deletes table for the smart sheet.
- `smartsheet.delete_view`: Deletes view for the smart sheet.
- `smartcanvas.edit`: Inserts, updates, or deletes smart-document blocks at an optional anchor.
- `manage.export_file`: Starts a document export task and returns its task ID.
- `ocr.extract`: Recognizes text in one image using basic, accurate, or efficient OCR.
- `smartsheet.fetch`: Fetches a smart-sheet worksheet snapshot for a subsequent changeset operation.
- `doc.find_and_replace`: Finds and replace for the Word document.
- `sheet.get_cell_data`: Retrieves cell data for the worksheet.
- `smartsheet.get_client_var`: Retrieves client var for the smart sheet.
- `doc.get_comments`: Retrieves comments for the Word document.
- `get_content`: Reads document body text for DOC, slides, or sheets.
- `manage.export_progress`: Checks an export task and returns a temporary download link when complete.
- `manage.query_file_info`: Queries file info for the Tencent document or file.
- `manage.query_folder_meta`: Queries folder meta for the Tencent document or file.
- `doc.get_images`: Retrieves images for the Word document.
- `manage.import_progress`: Checks an import task and returns the file ID and URL when complete.
- `doc.get_last_operable_pos`: Retrieves last operable pos for the Word document.
- `sheet.get_merged_cells`: Retrieves merged cells for the worksheet.
- `doc.get_outline`: Retrieves outline for the Word document.
- `doc.get_paragraph_property`: Retrieves paragraph property for the Word document.
- `manage.get_privilege`: Retrieves privilege for the Tencent document or file.
- `sheet.get_sheet_info`: Retrieves worksheet info for the worksheet.
- `doc.get_table_info`: Retrieves table info for the Word document.
- `doc.get_text_property`: Retrieves text property for the Word document.
- `smartcanvas.get_top_level_pages`: Retrieves top level pages for the smart document.
- `get_user_info`: Retrieves user info for the provider resource.
- `doc.insert_attachment`: Inserts attachment for the Word document.
- `doc.insert_border`: Inserts border for the Word document.
- `doc.insert_code_block`: Inserts code block for the Word document.
- `doc.insert_cols`: Inserts columns for the Word document.
- `doc.insert_comment`: Inserts comment for the Word document.
- `sheet.insert_dimension`: Inserts dimension for the worksheet.
- `doc.insert_footer`: Inserts footer for the Word document.
- `doc.insert_footnote`: Inserts footnote for the Word document.
- `doc.insert_header`: Inserts header for the Word document.
- `doc.insert_html_content`: Inserts HTML content for the Word document.
- `sheet.insert_image`: Inserts image for the worksheet.
- `doc.insert_image`: Inserts image for the Word document.
- `doc.insert_normal_link`: Inserts normal link for the Word document.
- `doc.insert_markdown`: Inserts markdown for the Word document.
- `doc.insert_numbering`: Inserts numbering for the Word document.
- `doc.insert_page_break`: Inserts page break for the Word document.
- `doc.insert_paragraph`: Inserts paragraph for the Word document.
- `doc.insert_rows`: Inserts rows for the Word document.
- `doc.insert_table`: Inserts table for the Word document.
- `doc.insert_task`: Inserts task for the Word document.
- `doc.insert_text`: Inserts text for the Word document.
- `doc.insert_paragraph_with_text`: Inserts paragraph with text for the Word document.
- `smartsheet.list_fields`: Lists fields for the smart sheet.
- `manage.folder_list`: Runs list for the Tencent document or file.
- `doc.list_recent_ai_edits`: Lists recent AI edits for the Word document.
- `manage.recent_online_file`: Runs online file for the Tencent document or file.
- `smartsheet.list_records`: Lists records for the smart sheet.
- `smartsheet.list_tables`: Lists tables for the smart sheet.
- `smartsheet.list_views`: Lists views for the smart sheet.
- `sheet.merge_cell`: Runs cell for the worksheet.
- `doc.modify_paragraph`: Runs paragraph for the Word document.
- `manage.move_file`: Moves file for the Tencent document or file.
- `manage.move_file_to_space`: Moves file to space for the Tencent document or file.
- `sheet.operation_sheet`: Runs fine-grained worksheet operations for values, formulas, formatting, and structure.
- `manage.pre_import`: Prepares import for the Tencent document or file.
- `doc.pre_insert_attachment`: Prepares insert attachment for the Word document.
- `query_space_list`: Queries space list for the provider resource.
- `query_space_node`: Queries space node for the provider resource.
- `smartcanvas.read`: Reads the smart document operation.
- `sheet.remove_filter`: Removes filter for the worksheet.
- `manage.rename_file_title`: Renames file title for the Tencent document or file.
- `sheet.rename_sheet`: Renames worksheet for the worksheet.
- `doc.replace_bookmarks`: Replaces bookmarks for the Word document.
- `doc.replace_image`: Replaces image for the Word document.
- `doc.replace_text`: Replaces text for the Word document.
- `report_unsupported_feature`: Reports a requested feature that is unavailable in the current tool list.
- `doc.resolve_document_structure`: Runs document structure for the Word document.
- `scrape_progress`: Scrapes progress for the provider resource.
- `scrape_url`: Clips a web URL into a Tencent document and returns a task ID.
- `smartcanvas.find`: Finds the smart document operation.
- `manage.search_file`: Searches file for the Tencent document or file.
- `doc.find`: Finds the Word document operation.
- `sheet.set_cell_style`: Sets cell style for the worksheet.
- `sheet.set_cell_value`: Sets cell value for the worksheet.
- `sheet.set_dimension_size`: Sets dimension size for the worksheet.
- `sheet.set_filter`: Sets filter for the worksheet.
- `sheet.set_freeze`: Sets freeze for the worksheet.
- `sheet.set_link`: Sets link for the worksheet.
- `doc.set_page_number`: Sets page number for the Word document.
- `manage.set_privilege`: Sets privilege for the Tencent document or file.
- `sheet.set_range_value`: Sets range value for the worksheet.
- `doc.set_table_layout`: Sets table layout for the Word document.
- `doc.set_table_properties`: Sets table properties for the Word document.
- `smartsheet.show_ui`: Shows UI for the smart sheet.
- `slide_add_anim`: Adds animation for the presentation.
- `slide_add_chart`: Adds chart for the presentation.
- `slide_add_comment`: Adds comment for the presentation.
- `slide_add_datetime`: Adds datetime for the presentation.
- `slide_add_footer`: Adds footer for the presentation.
- `slide_add_image`: Adds image for the presentation.
- `slide_add_line_shape`: Adds line shape for the presentation.
- `slide_add_line_shapes`: Adds line shapes for the presentation.
- `slide_add_notes`: Adds notes for the presentation.
- `slide_add_page_number`: Adds page number for the presentation.
- `slide_add_section`: Adds section for the presentation.
- `slide_add_shape`: Adds shape for the presentation.
- `slide_add_shapes`: Adds shapes for the presentation.
- `slide_add_slide`: Adds slide for the presentation.
- `slide_add_slides`: Adds slides for the presentation.
- `slide_add_table`: Adds table for the presentation.
- `slide_add_text`: Adds text for the presentation.
- `slide_add_texts`: Adds texts for the presentation.
- `slide_append_text`: Runs text for the presentation.
- `slide_change_chart_type`: Runs chart type for the presentation.
- `slide_delete_table_cols`: Deletes table columns for the presentation.
- `slide_delete_table_rows`: Deletes table rows for the presentation.
- `slide_delete_text`: Deletes text for the presentation.
- `slide_duplicate_slide`: Runs slide for the presentation.
- `slide_find_replace_text`: Finds replace text for the presentation.
- `slide_find_text`: Finds text for the presentation.
- `slide_get_chart_info`: Retrieves chart info for the presentation.
- `slide_get_comments`: Retrieves comments for the presentation.
- `slide_get_group_info`: Retrieves group info for the presentation.
- `slide_get_info`: Retrieves info for the presentation.
- `slide_get_master_info`: Retrieves master info for the presentation.
- `slide_get_page_info`: Retrieves page info for the presentation.
- `slide_get_sections`: Retrieves sections for the presentation.
- `slide_get_shape_info`: Retrieves shape info for the presentation.
- `slide_get_text`: Retrieves text for the presentation.
- `slide_get_themes`: Retrieves themes for the presentation.
- `slide_group_shapes`: Runs shapes for the presentation.
- `slide_insert_table_cols`: Inserts table columns for the presentation.
- `slide_insert_table_rows`: Inserts table rows for the presentation.
- `slide_insert_text`: Inserts text for the presentation.
- `slide_list_anim_types`: Lists animation types for the presentation.
- `slide_list_builtin_themes`: Lists built-in themes for the presentation.
- `slide_list_recent_ai_edits`: Lists recent AI edits for the presentation.
- `slide_merge_table_cells`: Runs table cells for the presentation.
- `slide_modify_comment`: Runs comment for the presentation.
- `slide_move_anim`: Moves animation for the presentation.
- `slide_move_section`: Moves section for the presentation.
- `slide_move_slide`: Moves slide for the presentation.
- `slide_progress`: Checks AI slide-generation progress and returns the file link when complete.
- `slide_remove_anim`: Removes animation for the presentation.
- `slide_remove_comment`: Removes comment for the presentation.
- `slide_remove_section_with_slides`: Removes section with slides for the presentation.
- `slide_remove_sections`: Removes sections for the presentation.
- `slide_remove_shapes`: Removes shapes for the presentation.
- `slide_remove_slide`: Removes slide for the presentation.
- `slide_rename_section`: Renames section for the presentation.
- `slide_reorder_shape`: Runs shape for the presentation.
- `slide_reorder_shapes_in_group`: Runs shapes in group for the presentation.
- `slide_reply_comment`: Runs comment for the presentation.
- `slide_set_anim_properties`: Sets animation properties for the presentation.
- `slide_set_anim_trigger`: Sets animation trigger for the presentation.
- `slide_set_cell_text`: Sets cell text for the presentation.
- `slide_set_default_font`: Sets default font for the presentation.
- `slide_set_notes_text`: Sets notes text for the presentation.
- `slide_set_page_properties`: Sets page properties for the presentation.
- `slide_set_shape_properties`: Sets shape properties for the presentation.
- `slide_set_slide_size`: Sets slide size for the presentation.
- `slide_set_text_property`: Sets text property for the presentation.
- `slide_set_theme`: Sets theme for the presentation.
- `slide_undo_ai_edit`: Undoes AI edit for the presentation.
- `slide_ungroup_shapes`: Runs shapes for the presentation.
- `slide_unmerge_table_cells`: Runs table cells for the presentation.
- `slide_update_chart_data`: Updates chart data for the presentation.
- `slide_update_chart_style`: Updates chart style for the presentation.
- `doc.undo_ai_edit`: Undoes AI edit for the Word document.
- `sheet.unmerge_cell`: Runs cell for the worksheet.
- `sheet.unset_freeze`: Runs freeze for the worksheet.
- `smartsheet.update_fields`: Updates fields for the smart sheet.
- `slide_update_group_shape_properties`: Updates group shape properties for the presentation.
- `smartsheet.update_records`: Updates records for the smart sheet.
- `doc.update_text_property`: Updates text property for the Word document.
- `upload_image`: Uploads image data to Tencent Docs and returns a temporary image ID.

## Workflow

1. Identify the requested entity, identifier, scope, operation, and output format.
2. Classify the request as lookup, search, analysis, creation, update, export, deletion, sending, purchase, permission change, or another provider operation.
3. Resolve ambiguous identifiers with a live lookup when available; never guess IDs, paths, records, or accounts.
4. Pass only supported user-provided or provider-returned values and preserve returned identifiers, pagination, timestamps, and status.
5. Chain operations only when a returned identifier or status is required by the next step.
6. Inspect outer tool errors and provider status before reading result fields; do not treat empty or partial output as complete success.

## Query Guidance

- Ask only for missing inputs required to choose or safely execute the operation.
- Preserve the user’s requested scope and keep unrelated entities, dates, accounts, and operations separate.
- State filters, result limits, sort order, output format, and data time when available.
- Normalize names or identifiers only when the mapping is unambiguous, and state the normalization.

## Failure Handling

- If no live callable tool is available, report that the connector is unavailable instead of silently substituting another source.
- For authorization, quota, timeout, invalid-argument, permission, provider, or missing-tool errors, report the failed operation without exposing secrets.
- Retry at most once after a safe correction such as narrowing scope, supplying a known identifier, or reducing result size.
- Do not convert an empty, partial, or errored response into a successful factual answer.

## Result Contract

- Separate returned provider facts from model interpretation and derived calculations.
- Preserve identifiers, URLs, paths, dates, timestamps, units, filters, page scope, totals, status, and provider caveats when returned.
- Do not describe one page, sample, or preview as complete unless the provider confirms completeness.
- Report queued, pending, failed, canceled, or partially completed states exactly as returned.
