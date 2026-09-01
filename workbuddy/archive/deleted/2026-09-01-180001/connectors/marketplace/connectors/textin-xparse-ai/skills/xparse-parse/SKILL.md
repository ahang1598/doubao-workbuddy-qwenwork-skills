---
name: xparse-parse
description: "Parse, read, search, navigate, summarize, and extract tables or structured evidence from PDFs, images, Office files, HTML, OFD, and other supported local documents or document URLs through xparse-cli. Use this Skill for both full-document conversion and targeted section/page/fact extraction instead of raw PDF readers or custom OCR scripts."
---

# xparse-parse

Use the installed `xparse-cli` as the only parsing, authentication, quota, and
document-navigation execution kernel. Do not reproduce its HTTP, OAuth, quota,
PDF splitting, or result-merging logic in the Skill.

## WorkBuddy profile and task context

Inside the TextIn xParse WorkBuddy Connector, prefix every invocation with:

```bash
xparse-cli --profile workbuddy <command> ...
```

The Connector declares a Node.js runtime and installs the pinned CLI with the
standard global npm prefix, so WorkBuddy supplies `xparse-cli` on PATH. On
Windows Connector lifecycle commands use `xparse-cli.cmd`; document-task shell
commands may use the command form supported by the active shell. Outside
WorkBuddy, use `xparse-cli <command> ...`.

For every new WorkBuddy user request, create one private `0600` JSON file before
the first xParse command:

```json
{
  "schema_version": "xparse_task_context.v1",
  "user_intent": "the user's original request, in its original language",
  "tool_call_reason": "the document information needed to complete this task"
}
```

- Preserve the user's wording and keep the operational reason brief.
- Never include hidden reasoning, credentials, document content, or the final answer.
- Pass `--task-context <FILE>` only on the first xParse invocation for that request.
- Delete the temporary file after that invocation. Later commands inherit the task.
- Do not pass inline JSON through shell arguments, `echo`, or a heredoc.

## Free, free-package, and paid routing

Use `--api auto` by default. The CLI queries the service quota before parsing and
uses the current server response as the authority instead of relying on a Skill
snapshot.

| Mode | CLI behavior | Use it when |
|------|--------------|-------------|
| `--api auto` | Uses the daily free API allowance first. When quota reports an AppKey-authenticated free package with sufficient `free_remain_count`, it can use that package through the existing authenticated route. | Default for supported PDF and image work. |
| `--api free` | Forces the free endpoint and does not use the authenticated free-package route. | The user explicitly requires the free endpoint only. |
| `--api paid` | Forces the paid endpoint and follows the service's existing package/balance billing behavior. | The user explicitly approves paid use, or approves it after learning that the format requires the paid API. |

Authentication is identity, not permission to spend. Never choose `--api paid`
only because OAuth or AppKey credentials exist.

Run `xparse-cli quota --output json` when the user asks about quota, when a routing failure
needs explanation, or before proposing a paid retry. Read all returned facts:

- daily free pages remaining and reset time;
- whether the request is authenticated;
- authenticated free-package total, historical used count, and current
  `free_remain_count` when present (routing uses only `free_remain_count`);
- maximum pages and file size per request.

Do not cache or calculate an allowance in the Skill. `parse --api auto` performs
its own quota preflight, and the parse response remains authoritative if quota
changes between inspection and execution. The Skill must not promise stronger
billing guarantees than the existing server provides.

WorkBuddy Device OAuth and AppKey are different identities. If quota returns
`authenticated=false` or omits `free_package`, do not infer package access from
an OAuth login indicator. Treat only fields in the current quota response as
available.

The free endpoint supports PDF and images. Office, HTML, OFD, and other formats
may require `--api paid`; explain this and obtain the user's approval before
switching modes. If all reported free sources are insufficient, stop and explain
the current quota rather than silently retrying as paid.

## Choose the workflow

### Full document or conversion

Use one parse command:

```bash
xparse-cli parse <INPUT> --api auto
```

For PDFs, always pass an existing output directory so long Markdown is not
truncated in terminal output:

```bash
xparse-cli parse report.pdf --api auto --output <DIR>
```

Read the saved result before requesting more detail. Add `--view json` only when
the task needs structured elements, coordinates, tables, pages, or title hierarchy.

### Targeted reading, search, or extraction

For a local document, use:

```text
get_doc_info -> parse the complete document -> navigate -> extract
```

1. Run `get_doc_info <FILE>` and retain its exact `doc_id`.
2. Run `parse <FILE> --api auto` without `--page-range`. A successful complete
   local parse writes the navigation cache automatically.
3. Use `get_outline`, `search_text`, or `read_pages` to locate relevant content.
4. Batch the required `read_content` calls after navigation is complete.

There is no separate cache-preparation command. A successful complete local
`parse` is the only preparation step.

Page-range parses intentionally do not replace the complete-document navigation
cache. URL parses have no stable local `doc_id`, so use their direct parse output
instead of local navigation commands.

Read [navigation.md](references/navigation.md) before performing targeted
navigation or extraction.

## Efficiency and fallback rules

- Plan all navigation before reading sections; target no more than eight
  `read_content` calls per task and issue independent reads together.
- Prefer `search_text` for names, dates, amounts, and percentages. Read a full
  section only when its surrounding prose or table structure is needed.
- If an outline is truncated, drill down with `--parent-id`; do not guess IDs.
- Run parse requests serially unless the user explicitly requests a batch.
- Retry a transient service failure once at most. Never silently skip a failure.
- For local documents, try this Skill before Python, PyMuPDF, pdfplumber, qpdf,
  OCR tools, image conversion, or custom scripts.
- If a document is encrypted or required input is missing, ask the user instead
  of trying alternate tools.
- Only fall back after xparse-cli clearly cannot complete the task, and explain why.

## Quick reference

| Goal | Command |
|------|---------|
| Parse with automatic free routing | `xparse-cli parse <FILE> --api auto` |
| Force free endpoint only | `xparse-cli parse <FILE> --api free` |
| Explicit paid parse | `xparse-cli parse <FILE> --api paid --auth-method oauth` |
| Save Markdown | `xparse-cli parse <FILE> --api auto --output <DIR>` |
| Save JSON | `xparse-cli parse <FILE> --api auto --view json --output <DIR>` |
| Parse selected pages only | `xparse-cli parse <FILE> --api auto --page-range 1-5` |
| Encrypted document | `xparse-cli parse <FILE> --api auto --password <PWD>` |
| Character details | `xparse-cli parse <FILE> --api auto --view json --output <DIR> --include-char-details` |
| Show current quota | `xparse-cli quota --output json` |
| Start local navigation | `xparse-cli get_doc_info <FILE>` |
| Show cached outline | `xparse-cli get_outline <DOC_ID>` |
| Search cached text | `xparse-cli search_text <DOC_ID> <PATTERN>` |

`--output` accepts an existing directory, not an output filename. The CLI writes
`<basename>.md` or `<basename>.json` inside it.

## Authentication boundary

- In WorkBuddy, rely on Connector Device OAuth and the isolated `workbuddy`
  profile. If disconnected, ask the user to reconnect the Connector; never ask
  for or echo a Secret, Token, or device code.
- Standalone CLI supports AppKey, Device OAuth, and browser PKCE as documented in
  [authentication.md](references/authentication.md).
- Never print credential files or use `--verbose` while handling authentication.
- An explicitly selected authentication method must fail as that method; do not
  silently retry with another credential type.

## Setup and command discovery

Check installation with `xparse-cli version`. The package requires Node.js 18
or newer and can be installed with:

```bash
npm i -g xparse-cli
```

For users in China, use the npmmirror registry:

```bash
npm i -g xparse-cli --registry=https://registry.npmmirror.com
```

The WorkBuddy Connector installs its pinned CLI version automatically. Do not
replace the Connector-managed version from within a document task.

Use this Skill and its references as the command index. When live discovery is
necessary, read complete `xparse-cli --help`, then the complete help for the exact
command. Do not truncate help output with `head`, `tail`, or a fixed `sed` range.

Stop on unsupported or corrupt files, invalid credentials, exhausted quota,
missing paid approval, or repeated service failure.

## References

- [navigation.md](references/navigation.md): targeted outline, search, page, and content workflow.
- [authentication.md](references/authentication.md): WorkBuddy and standalone authentication.
- [cli-guidance.md](references/cli-guidance.md): modes, output, parameters, and limits.
- [api-reference.md](references/api-reference.md): response fields and service error codes.
- [error-handling.md](references/error-handling.md): retry, stop, and paid-approval decisions.
- [textin-key-setup.md](references/textin-key-setup.md): standalone legacy AppKey setup.
