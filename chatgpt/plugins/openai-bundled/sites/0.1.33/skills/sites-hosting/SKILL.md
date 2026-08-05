---
name: sites-hosting
description: Host websites with Sites. Always use after `sites-building`, and use for website publishing, deployment, hosting management, or projects containing `.openai/hosting.json`.
---

# Sites hosting

Publish the exact validated source with the shortest safe sequence. Treat the
Sites connector descriptions as the source of truth for arguments and archive
requirements.

## Communicate clearly

Assume the user is a nontechnical knowledge worker. Keep source control,
credentials, IDs, commits, branches, archives, versions, packaging, connector
calls, and deployment polling out of user-facing messages. Usually send one
update when publishing begins, then the final URL or a plain-language blocker.
For example: `Your site is ready. I’m publishing it privately now.`

## Rules

- Publish after a successful build unless the user requested local-only work.
- Publishing does not require browser preview or visual QA. Use the preview from
  `sites-building`; do more browser work only when the user asks. A failed
  browser handoff does not block publishing.
- Treat `public/screenshot.jpeg` as an optional deployment thumbnail. Preserve
  an existing file. Create or refresh it only when the user explicitly requests
  a Sites deployment thumbnail; a generic screenshot request does not count.
  Missing or failed capture never blocks validation, version saving, or
  deployment.
- Store only `project_id` plus optional logical `d1` and `r2` bindings in
  `.openai/hosting.json`. Manage runtime values through Sites.

## Fast publish sequence

1. Reuse the successful build from `sites-building` when the source has not
   changed. Rebuild only when needed.
2. Call `create_site` once for a new site. Persist its `project_id` in
   `.openai/hosting.json` and reuse the source write credential returned by that
   call. Reuse these values instead of rediscovering them. Retry only when the
   error explicitly identifies a temporary failure or slug conflict. Treat
   quota, permission, and access errors as terminal; do not change the slug
   speculatively.
3. Commit the exact validated source. Push it with the returned credential as a
   per-command HTTP authorization header. Keep the credential out of remote
   URLs and Git configuration. Use the pushed branch-head SHA as `commit_sha`.
4. Package with this plugin's root-level `scripts/package-site.sh` helper,
   passing the project directory and archive path. It stages `dist/`, hosting
   metadata, and migrations; validates required files; and creates the archive.
5. Save one version with the connector using that `commit_sha` and archive.
6. Prefer private deployment. Use `deploy_private_site_version` when available.
   If only shared or public deployment is available, call `request_user_input` with an approval choice that names the resolved access level, such as `Publish publicly` or `Publish to existing shared access`, plus `Not now`; wait for the response, and call `deploy_site_version` only after approval.
7. Poll `get_deployment_status` directly until deployment succeeds or fails.
   Use discovery calls only when an error requires them.

## Existing sites and advanced capabilities

- Reuse an existing `project_id` and valid source credential when available.
- If a credential is absent or expired, obtain one with
  `create_source_repository_write_credential` and reuse it until expiry.
- If the D1 schema changed, ensure generated migrations are present before
  packaging.
- Require `dist/server/index.js`, static assets when emitted,
  `dist/.openai/hosting.json`, and `dist/.openai/drizzle/**` when migrations
  exist.
- For non-vinext projects, use the established Cloudflare Workers-compatible
  build output and adapt staging only as required by the connector contract.

## Handoff

After `get_deployment_status` reports `status: "succeeded"`, call
`open_in_codex` without `threadId` so it defaults to the calling thread. Use
the exact deployed URL returned in that response:
`target: { type: "browser", url: deployedUrl }`.

Then return the deployed Sites URL and a concise description of what the user
can do. If the deployment is unsuccessful, do not call `open_in_codex` or
mention that the deployed URL could not be opened in the in-app browser;
explain the user-visible reason and next step. Keep source credentials and
temporary archives private. Do not include file paths, commands, build details,
IDs, commits, or version information unless the user asks.
