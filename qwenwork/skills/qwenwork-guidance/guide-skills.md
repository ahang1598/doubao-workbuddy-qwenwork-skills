# Skills Management Guide

This guide covers managing skills through the QwenWork Connector: listing installed skills, searching the marketplace, installing, enabling/disabling, and removing skills.

## Keys

| Key | Actions | Description |
|-----|---------|-------------|
| `qwenwork.settings.skills` | query, open | All skills list (user + builtin) |
| `qwenwork.settings.skills.market` | query, execute | Skill marketplace (search, install) |
| `qwenwork.settings.skills.{folderName}` | query, enable, disable, remove | Single skill operations |

---

## UI-only Flows: Local Upload And Share

Local upload and share are intentionally UI-only. Upload depends on the local file picker, and share depends on clipboard review. Agent must not proxy these flows or claim `upload` / `share` actions; use `action: "open"` on `qwenwork.settings.skills` so the user can complete the flow in the Skills page.

---

## List All Skills

Returns user-installed skills and builtin skills with summary counts.

```
mcp__qw-builtin__qw_query({ key: "qwenwork.settings.skills" })
```

**Response structure:**

```json
{
  "success": true,
  "data": {
    "userSkills": [
      {
        "name": "my-skill",
        "folderName": "my-skill",
        "description": "...",
        "disabled": false,
        "source": "user",
        "version": "1.0.0",
        "installSource": "market",
        "category": "productivity"
      }
    ],
    "builtinSkills": [
      {
        "name": "pdf",
        "folderName": "pdf",
        "description": "...",
        "enabled": true,
        "disabled": false,
        "version": "1.0.0",
        "installedVersion": "1.0.0"
      }
    ],
    "summary": {
      "userCount": 3,
      "builtinCount": 7,
      "builtinEnabledCount": 5
    }
  }
}
```

- `userSkills`: User-installed skills (excluding builtin copies).
- `builtinSkills`: Built-in skills. `enabled` indicates if installed to user directory. `disabled` indicates if explicitly disabled.

---

## Search Skill Marketplace

Search for skills available for installation.

```
mcp__qw-builtin__qw_query({
  key: "qwenwork.settings.skills.market",
  params: {
    keyword: "image",
    category: "productivity",
    page: 1,
    pageSize: 20
  }
})
```

**Parameters (all optional):**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `keyword` | string | - | Search keyword |
| `category` | string or string[] | - | Filter by category (single or multiple) |
| `page` | number | 1 | Page number |
| `pageSize` | number | 20 | Results per page (max 100) |

**Response includes:** `skills[]` (id, name, nameCn, description, descriptionCn, version, installed, category, installCount), `totalSize`, `currentPage`, `pageSize`, `hasMore`.

---

## Install Skill from Marketplace

```
mcp__qw-builtin__qw_action({
  key: "qwenwork.settings.skills.market",
  action: "execute",
  params: {
    operation: "install",
    folderName: "skill-id-from-market"
  }
})
```

**Required params:**

| Param | Type | Description |
|-------|------|-------------|
| `operation` | string | Must be `"install"` |
| `folderName` | string | The skill ID from marketplace search results |

**Response:** `{ success, message, data: { folderName, version, fromCache } }`

---

## Get Skill Detail

```
mcp__qw-builtin__qw_query({ key: "qwenwork.settings.skills.my-skill" })
```

Returns: name, folderName, description, descriptionZh, version, disabled, source ("user" or "builtin"), category, installSource.

Checks user directory first, then falls back to builtin directory.

---

## Enable a Skill

```
mcp__qw-builtin__qw_action({
  key: "qwenwork.settings.skills.my-skill",
  action: "enable"
})
```

**Behavior depends on skill state:**

| State | What happens |
|-------|-------------|
| User skill with `disabled: true` | Removes the disabled flag from SKILL.md frontmatter |
| User skill already enabled | No-op, returns success |
| Builtin skill not in user dir | Copies builtin skill to user directory to activate it |
| Skill not found anywhere | Returns error |

---

## Disable a Skill

```
mcp__qw-builtin__qw_action({
  key: "qwenwork.settings.skills.my-skill",
  action: "disable"
})
```

Sets `disabled: true` in the skill's SKILL.md frontmatter. Only works for skills in the user directory.

---

## Remove a Skill

```
mcp__qw-builtin__qw_action({
  key: "qwenwork.settings.skills.my-skill",
  action: "remove"
})
```

Permanently deletes the skill directory from the user skills folder. Only works for skills in the user directory.

---

## Workflow: Search and Install a Skill

1. **Search** the marketplace for relevant skills:
   ```
   query({ key: "qwenwork.settings.skills.market", params: { keyword: "pdf" } })
   ```

2. **Review** the results and identify the desired skill by its `id` (folderName).

3. **Install** the skill:
   ```
   action({ key: "qwenwork.settings.skills.market", action: "execute", params: { operation: "install", folderName: "pdf-generator" } })
   ```

4. **Verify** installation:
   ```
   query({ key: "qwenwork.settings.skills.pdf-generator" })
   ```

## Workflow: Enable a Builtin Skill

1. **List** all skills to find builtin skills that are not yet enabled:
   ```
   query({ key: "qwenwork.settings.skills" })
   ```

2. Look for builtin skills where `enabled: false`.

3. **Enable** the desired skill:
   ```
   action({ key: "qwenwork.settings.skills.pdf", action: "enable" })
   ```

---

## Notes

- `folderName` is the unique identifier for skills. It must be a valid directory name (alphanumeric, hyphens, underscores).
- Builtin skills live in the app's resources directory. Enabling a builtin skill copies it to the user directory.
- Removing a builtin skill that was enabled simply removes the user copy; the builtin original remains and can be re-enabled.
- Marketplace results are sorted by install count (descending) by default.
