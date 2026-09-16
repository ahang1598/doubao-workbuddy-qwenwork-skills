# Brandkit state routing

Brandkit approval state lives in `.brandkit/state.json` inside the working directory you run the
bundled script from. Drafts never enter it. The script writes atomically and preserves independent
logo, palette, typography, visual-axis, and downstream-element revisions.

Run every operation in the **local shell** (Cursor / Codex / CodeBuddy). There is no remote sandbox
and no `sandbox_exec` tool in this environment.

```bash
python3 <skill dir>/scripts/brandkit.py state --action ACTION [--input INPUT.json]
```

Create payload files with a quoted heredoc (`cat > brandkit/input.json <<'JSON' … JSON`); never
interpolate JSON or user text into the shell command arguments.

Before the first state write, load [exact state payloads](state-payloads.md) and copy only the
matching complete object shape. Replace values, not keys or nesting.

## Working directory protocol (local filesystem)

The local filesystem is durable, so no upload/restore round trip is needed. What matters is that
every call in one brand job uses the **same** working directory.

1. At the start of a brand job, pick one stable working directory and keep using it for the whole
   conversation. Prefer a directory the user named; otherwise create `./brandkit-work/<brand-slug>/`
   under the current project and tell the user where it is.
2. `mkdir -p .brandkit brandkit` inside it. `cd` into it before every script call. When
   `.brandkit/state.json` does not exist, the script initializes it.
3. Never adopt a `.brandkit/state.json` belonging to a different brand. When the user switches
   brands, use a new working directory.
4. Create each input with a quoted heredoc, run the state action, and redirect its potentially
   large JSON result to `brandkit/state-action.json`. Continue only on exit 0. Print a narrow
   `state --action get_status` response when needed, not the full ledger.
5. Do not announce a slot as locked / selected / approved / saved until its script call exits 0.

Local files are the deliverable source. Push a file into the WorkRally asset library only when the
user needs it there or a generation step needs an HTTPS URL: `upload_file` → (optional)
`asset_create`. Never store a stale short link in state when the local path is what you will reuse —
WorkRally short links expire after about 5 hours.

Do not retry a paid generation after a state-write failure. Recover from the on-disk state and the
explicit selection already in this conversation; if the selected asset or approval evidence is
missing, stop and explain the recovery failure. Never invent approvals. Initialize a new empty
ledger only when the user explicitly resets the brand decisions.

## Call moments

### Start of any Brandkit turn

```bash
python3 <skill dir>/scripts/brandkit.py state --action get_status
```

### Lock user-supplied official assets

Immediately after asset analysis, write one input object with the matching top-level slot, then call
only its action:

```text
lock_authoritative_logo       {"source_summary": "...", "logo": {...}}
lock_authoritative_palette    {"source_summary": "...", "palette": {...}}
lock_authoritative_typography {"source_summary": "...", "typography": {...}}
```

These actions preserve official assets the user already owns. They do not approve generated work,
and an authoritative slot cannot be replaced by a later generated choice.

### Persist visual axes

```json
{
  "visual_axes": {
    "restrained_expressive": 50,
    "geometric_organic": 50,
    "familiar_experimental": 50
  }
}
```

Call `set_visual_axes`; later read with `state --action get_visual_axes`.

### Read only the required slot

- `state --action get_logo` before logo placement, export, or logo-dependent revisions.
- `state --action get_palette` for color-dependent work.
- `state --action get_typography` for type-dependent work.
- `state --action get_essential_kit` only when logo, palette, and typography are all genuinely
  required.

Never use `state --action get_essential_kit` as a universal gate for partial outputs.

### Browse approved downstream elements

Call `state --action list_brandbook_elements`, then use `state --action get_brandbook_element` with:

```json
{ "key": "exact-element-key" }
```

### Approve generated elements independently

After an explicit user selection, write the exact selected object under its slot and call:

```text
approve_logo       {"approval_summary": "...", "logo": {...}}
approve_palette    {"approval_summary": "...", "palette": {...}}
approve_typography {"approval_summary": "...", "typography": {...}}
```

The script assigns the next revision. Do not put generated-but-unapproved work into state.

### Approve a downstream element

Only after explicit approval:

```json
{
  "approval_summary": "User approved the primary mockup.",
  "required_slots": ["logo", "palette"],
  "brandbook_element": {
    "key": "mockup-primary",
    "kind": "mockup",
    "name": "Primary packaging mockup",
    "asset": { "id": "...", "url": "..." }
  }
}
```

Call `approve_brandbook_element`. Declare exactly the foundation slots the output used.

## Recovery

If the working directory was deleted and no copy of `.brandkit/state.json` exists, stop and report
the recovery failure. A narrow `state --action get_status` response is not a restorable snapshot.
Never reconstruct state from the account-wide asset library.

## Never

- Never load the entire state file directly when a narrow read action is enough.
- Never put drafts into an authoritative lock.
- Never delay locking a user-declared official asset.
- Never store generated-but-unapproved assets.
- Never require or request approval for an unrelated missing slot.
- Never ask for combined approval after independent selections.
- Never use this state outside Brandkit.
- Never store a WorkRally short link as the durable record of an approved asset; keep the local path
  or a confirmed CDN URL.
