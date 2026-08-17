---
name: qw-pages
description: Publish static or dynamic HTML, websites, and web applications through QW Pages. Use when the user asks to publish, deploy, or make a webpage live. Combine with qw-pages-supabase only when the webpage needs persistent database storage.
---

# QW Pages

Use the QW Pages publishing workflow for explicitly requested web publishing.

## Local development contract

This local skill prepares an artifact for the desktop controlled publisher. Do not ask the user for access tokens or copy tokens into shell commands.

## Tool boundary

QW Pages does not provide lazy MCP tools named `page`, `publish`, `artifact`, or `deploy`. Do not call `qwenwork_mcp_tool_list` to search for those tools and do not invent them from this skill.

MuleRun's reference implementation invokes its bundled `scripts/publish.py`. In QwenWork, the desktop controlled publisher owns the equivalent Page lookup, Artifact allocation, `resource_key` Barn path, dynamic `runtime.zip`, Seal, Publish, and deployment polling. After the artifact is ready, call the built-in `qwenwork_pages_publish` tool exactly once with its absolute path. Do not execute Page/Barn HTTP calls or token issuance yourself.

1. Classify the output as static or dynamic.
2. For a static page, publish the directory that contains the root `index.html`.
3. For a dynamic page, require a self-contained Node.js 22-compatible directory, `package.json`, a relative `.js`, `.mjs`, or `.cjs` entrypoint, and a server that reads both `process.env.PORT` and `process.env.HOST`. Use port `8081` unless the app requires another non-`9000` port. Do not include secrets or symbolic links. Prefer Node.js built-ins. If production dependencies are required, prepare them inside the publish directory before invoking the controlled publisher; it packages existing `node_modules` but does not run package installation scripts on the host.
4. For a dynamic page with persistent data, call `qwenwork_pages_provision_database` exactly once, passing a concise, meaningful `name`, then apply each idempotent migration with `qwenwork_pages_apply_migration`. The desktop pins the session to that Page; do not provision again after migration or publishing.
5. Call `qwenwork_pages_publish` exactly once after the artifact is ready. Pass `file_path` and a concise, meaningful user-visible `name` in the user's task language: for example, a Chinese request for a kindergarten check-in page must pass `name: "幼儿园签到"`, not an English filename or technical ID. Additionally pass `category: "dynamic"`, `entrypoint`, and `port` for a dynamic page. Pass `with_database: true` after database provisioning. Do not pass a shell command when an entrypoint is available. Publish again only after the user requests a real source update; the desktop will create the next version on the same domain.
6. Return the final public URL only after the deployment reports success.

## Canvas / Design workspace

When the request comes from the Canvas design workspace, treat the active Canvas project root supplied in the message as the artifact root. The Canvas header Publish button only submits this explicit publish intent; it never bypasses this controlled workflow.

- Before declaring the design task complete, create or update a Canvas-renderable frame. Writing files and publishing them does not populate the right-side Canvas or Preview by itself.
- For a standalone HTML page, call `mcp__qw_desk_canvas__add_frame` with `kind: "snapshot"`, a `file://` URL for the generated HTML file, its matching `previewUrl`, a `code.files` entry for the HTML entry file, and `activate: true`. Then call `mcp__qw_desk_canvas__set_active_frame` when needed.
- For a React/Vite Canvas project, use `mcp__qw_desk_canvas__start_frame_dev_server` to create the live frame instead of publishing the source project as a dynamic Page runtime.
- A dynamic QW Pages Node.js runtime must not be started directly in Canvas. Create a safe static companion preview, such as `canvas-preview.html`, that represents the page UI, bind that file as a snapshot frame, and publish the Node.js runtime separately. The published public URL is a deployment result, not the source of Canvas frame state.
- Call `mcp__qw_desk_canvas__complete_design_execution` only after the frame is active and the Canvas side has a renderable preview.
- A standalone HTML frame is static when its publish root contains `index.html` and is not a Vite/React/Vue or Node server source project. A build-only `package.json` alone does not make it dynamic; publish static output as `static`.
- Canvas React/Vite source is not a dynamic Pages runtime merely because it has `index.html` and `package.json`. For an explicitly requested dynamic page, create or adapt a self-contained Node.js server project that follows the dynamic contract above, then publish that project directory with `category: "dynamic"`.
- If the design needs database-backed interaction, use `qw-pages-supabase` before publishing. Do not put Supabase credentials into Canvas browser code; the server runtime reads injected environment variables.

## Desktop verification boundary

Treat the structured `qwenwork_pages_publish` result as completion of the normal publishing workflow. Do not start the generated application, run `Bash`, use `curl`, poll the public URL, or write test records merely to verify a routine desktop publish. Those actions can execute untrusted artifact code, trigger user confirmation, leave test data, and duplicate the controlled publisher's deployment polling.

Inspect source files with normal file tools before publishing. Run local processes or public endpoint probes only when the user explicitly asks for runtime diagnosis. In that diagnostic case, explain that a command confirmation may appear and keep the probes bounded. Do not use the public `/healthz` response as proof that a dynamic application is healthy because the Page Gateway reserves that path.

If a database-backed page reports a missing relation or a deployment placeholder, do not provision another Page, repeatedly publish new domains, rename `/api` routes, or convert application errors to HTTP 200. First confirm that the provision, migration, and publish calls belong to the same session. The controlled desktop publisher owns that binding; report a binding error instead of guessing around it.

Do not publish a dynamic page with persistent data without also following `qw-pages-supabase`.
