# Temporary Sites dual-write rule

Until the bundled-to-remote Sites migration is declared complete, `plugins/sites` and `chatgpt/oai-maintained-plugins/plugins/sites-codex` are maintained as mirrors in this monorepo.

- The bundled `openai/openai/plugins/sites` payload remains the canonical authoring source during this transition.
- Any shared skill, MCP, script, starter, asset, test, or version change must update both directories in the same PR.
- Do not merge a shared payload change in only one directory. If a difference is intentionally product-specific, document and allowlist it explicitly.
- Keep mirrored files byte-identical except for the plugin manifest name: `sites` locally and `sites-codex` remotely.
- Run the Sites parity check before handing off the PR.
- Mirroring source does not authorize creating or publishing a remote-plugin release. Production publication requires separate rollout approval.
