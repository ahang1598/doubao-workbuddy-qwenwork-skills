---
name: baidu-netdisk
description: Use when the user invokes $baidu-netdisk, mentions Baidu Netdisk or the Baidu Netdisk MCP, or asks to browse, search, inspect, organize, upload, copy, move, rename, share, or check storage information for files in their Baidu Netdisk account.
---

# Baidu Netdisk

## Overview

Use this skill for requests that should be answered through the Baidu Netdisk MCP. The verified scope covers account and quota lookup, directory and media listing, filename and semantic search, file metadata, folder creation, file copy, move, rename, upload, and share-link creation. Treat file contents, paths, metadata, and share links as private unless the user states otherwise.

## Core Rules

- Use the bound `baidu-netdisk` MCP only when its live callable tools are available in the current runtime.
- Select the narrowest live callable operation that directly answers the request; follow the live interface when it differs from this guide.
- Do not invent account facts, file names, paths, file IDs, metadata, search matches, quota values, or share links from memory.
- Keep secrets, private file content, private URLs, and authorization material out of prompts, logs, and final answers. Never ask the user to paste OAuth tokens, authorization codes, cookies, or credentials into chat.
- Let the MCP client handle its configured HTTP and OAuth flow. Do not expose authorization material in tool arguments or attempt to refresh, exchange, inspect, or persist tokens.
- Do not use shell commands, direct HTTP calls, or hand-written JSON-RPC to recreate, probe, or simulate the MCP server.
- Treat provider output as evidence. Label model interpretation, file-selection reasoning, and recommendations separately.
- Require explicit confirmation immediately before any external write or publication, including folder creation, upload, copy, move, rename, and share-link creation.
- Before confirming a write, summarize the exact source, destination, resulting name, conflict behavior when known, and whether the original remains in place.
- Never claim that a file was downloaded, deleted, edited in place, or made private; no verified tool in this catalog performs those operations.

## Tools

- `file_copy`: Copy a specified file within Baidu Netdisk.
- `file_doc_list`: List documents in a specified Baidu Netdisk directory.
- `file_image_list`: List images in a specified Baidu Netdisk directory.
- `file_keyword_search`: Search a specified directory for file names containing a keyword.
- `file_list`: List files and folders of any supported type in a specified directory.
- `file_meta`: Retrieve detailed metadata for a file by its file ID.
- `file_move`: Move a specified file within Baidu Netdisk.
- `file_rename`: Rename a specified file in Baidu Netdisk.
- `file_semantics_search`: Search Baidu Netdisk files with a natural-language description.
- `file_sharelink_set`: Create a share link for a file.
- `file_upload_by_content`: Upload text content as a file to Baidu Netdisk.
- `file_upload_by_url`: Upload a file to Baidu Netdisk from a file URL.
- `file_video_list`: List videos in a specified Baidu Netdisk directory.
- `get_quota`: Retrieve the account's Baidu Netdisk storage usage.
- `make_dir`: Create a folder in Baidu Netdisk.
- `user_info`: Retrieve basic information for the authorized Baidu Netdisk user.
- Select the narrowest live callable tool that directly answers the request. Follow the live callable interface for current inputs, outputs, and errors.

## Workflow

1. Identify the target account context, directory, file, file ID, search scope, destination, requested output, and any relevant naming or conflict preference.
2. Classify the request as account lookup, quota lookup, listing, keyword search, semantic search, metadata retrieval, folder creation, upload, copy, move, rename, or share-link creation.
3. Prefer a type-specific list tool for documents, images, or videos; use `file_list` when the user wants mixed content or does not specify a type.
4. Prefer `file_keyword_search` for a known literal filename fragment. Prefer `file_semantics_search` for a natural-language description, uncertain filename, content characteristic, or multi-constraint query.
5. Resolve ambiguous files with search or listing, then use `file_meta` when details are needed. Never guess a file ID or path.
6. For a write, show the resolved source and intended result, obtain explicit confirmation, then invoke exactly the confirmed operation. Reconfirm if the target, destination, name, or conflict behavior changes.
7. Chain operations only when a returned file ID, path, status, or structured result is required by the next operation. Do not turn a search request into an organizational write without a separate confirmation.
8. Inspect the outer MCP error and provider status before reading result fields. Do not treat an empty, partial, or queued response as completed success without reporting its scope and status.
9. After a write, report the provider-returned path, file ID, link, or task status when available. Use a narrow read operation to verify the result only when needed and safe.

## Query Guidance

- Ask only for missing inputs required to choose or safely execute the operation, such as a directory, filename, destination, intended content, URL, or selection among multiple matches.
- Treat a path as account-relative provider data, not as a local filesystem path. Preserve exact path spelling and directory boundaries returned by the provider.
- Keep separate files, directories, searches, and writes distinct unless the user clearly requests a batch operation and the live tool supports it.
- For ambiguous matches, present a compact disambiguation using returned names, paths, file IDs, types, sizes, or timestamps rather than choosing silently.
- For uploads by content, confirm the intended content, filename, and destination without echoing sensitive content unnecessarily.
- For uploads by URL, reject credential-bearing or secret-bearing URLs from chat, and confirm the source URL domain, destination, and resulting filename before upload.
- For copy, move, and rename, surface any known collision or overwrite behavior before confirmation. Do not infer a default conflict policy when the live interface or provider response does not state one.
- For share links, confirm the exact files and any live-interface sharing options immediately before creation. Return passwords or access details only to the requesting user and avoid repeating them unnecessarily.
- State search scope, filters, page or result limits, sort order, and data time when available.

## Failure Handling

- If no live Baidu Netdisk callable tool is present, stop MCP execution and report that the connector is unavailable in the current runtime.
- If OAuth authorization is required, expired, denied, or missing, ask the user to complete the MCP client's authorization flow. Never request or handle the token in chat.
- For quota, timeout, invalid-argument, permission, provider, or missing-tool errors, report the failed operation without exposing secrets or private content.
- Retry at most once only after a safe correction such as narrowing a directory, supplying a provider-returned identifier, reducing result scope, or removing an unsupported optional field.
- For empty search or list results, report the exact directory, query, type filter, and page scope. Offer a broader search, semantic search, or parent-directory listing without silently changing scope.
- For ambiguous or stale paths, repeat a narrow lookup and ask the user to choose if multiple candidates remain.
- If a write returns an asynchronous, partial, or indeterminate status, report that status and do not claim completion. Avoid repeating the write unless the provider proves the first attempt failed safely.
- If the user specifically requests Baidu Netdisk, do not silently substitute another storage provider. State the connector failure first and offer a clearly labeled fallback only if the user wants it.

## Result Contract

- Separate returned Baidu Netdisk facts from model interpretation and file-selection reasoning.
- Preserve provider-returned file IDs, names, paths, URLs, timestamps, sizes, filters, page scope, totals, status, and caveats when relevant.
- For lists and searches, report the searched directory and query and state whether the result is complete, paginated, partial, or unknown.
- For write operations, state exactly what changed and what did not change. Report the provider status without upgrading queued or partial work to success.
- For share-link creation, identify the shared file and the provider-returned validity or access details when available, while minimizing exposure of access credentials.
- Do not describe a sample, preview, first page, or semantic match set as a complete account inventory unless the provider confirms completeness.
