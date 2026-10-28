---
name: environment-packages
version: 1.0.0
description: Routing guide for the built-in qwenwork_environment_package_fetch tool, which downloads a runtime dependency (node, python, uv, ffmpeg, or a custom name your organization published) from the enterprise environment package mirror with size and SHA-256 verification. Load ONLY when a task needs such a runtime AND installing it from public sources (pip / npm / apt / curl) has failed or is known to be impossible because the organization has no public internet egress. If the tool is not available in this session, the current edition does not support the mirror - fall back to the normal install path silently and do not mention this skill. Never load for ordinary coding, document, research or web tasks, and never load just because a dependency name was mentioned.
description_zh: 内置工具 qwenwork_environment_package_fetch 的路由指南：该工具从企业环境依赖镜像库下载运行时依赖（node、python、uv、ffmpeg 或组织自行上传的自定义依赖），并对大小与 SHA-256 做校验。仅在「任务确实需要这类运行时」且「公网安装（pip / npm / apt / curl）已经失败，或因组织无公网出口而不可能成功」时才加载。若当前会话看不到该工具，说明当前形态不支持镜像库——静默回退常规安装方式，不要提及本技能。普通编码、文档、调研、联网任务一律不加载，也不要只因为对话里出现了依赖名就加载。
---

# Environment Package Mirror

Enterprises with no public internet egress cannot install runtimes from `pip`, `npm`, `apt` or
`curl`. The host application can fetch them from the organization's own mirror instead, using
your current enterprise identity:

- **`qwenwork_environment_package_fetch`** — query the mirror, download the archive, verify its
  size and SHA-256, and publish it under the product data directory.

The tool returns a **verified archive path only**. It never extracts, installs, configures or
runs anything — that part is yours.

## When to use it

Use it only when both are true:

1. The task genuinely needs `node`, `python`, `uv`, `ffmpeg` or another dependency your
   organization published to the mirror.
2. Installing it from public sources already failed, or cannot work because there is no public
   egress (typical in private / on-premises enterprise deployments).

Do not use it as a general package manager, do not use it for Python *libraries* (`pypdf`,
`pandas`, ... are not mirror dependencies unless the organization published them), and do not
use it when a working runtime is already on `PATH`.

## Arguments

| Argument | Required | Meaning |
| --- | --- | --- |
| `dependency` | yes | Dependency name, e.g. `node`, `python`, `uv`, `ffmpeg`. `nodejs` / `node.js` are normalized to `node`; every other name must match exactly what the administrator uploaded. |
| `version` | no | Exact version string, e.g. `20.19.0`. Omit it to take the organization's current mirror. Ranges (`^20`, `>=20`) are not supported and a `v` prefix is not stripped. |
| `file_name` | no | Original archive file name, to distinguish builds, libc or distribution variants. |
| `checksum_sha256` | no | A SHA-256 you already trust from upstream. It is verified **in addition to** the mirror's own checksum, never replaced by it. |
| `target` | no | Where the dependency will actually run: `host` or `sandbox`. Defaults to `sandbox` when the session runs in VM mode, otherwise `host`. |

There is no destination-path argument. Artifacts always land in the product data directory;
copy them elsewhere yourself if you need a writable location.

## Choosing `target`

Pick the environment where the dependency will **actually execute**, not where you are reading
this:

- Your shell commands run through `mcp__workspace__bash` inside a Linux VM → use `sandbox`
  (the tool then queries `platform=linux` with the machine's real architecture).
- The dependency is consumed by host-side file tools or a host process → use `host`.

Choosing the wrong target yields an archive that cannot execute in the environment you intended.
When unsure, check whether the session uses the VM sandbox and prefer `sandbox` in that case.

## Using the returned paths

The result's first line is JSON; the lines after it are instructions.

- `path` — host absolute path. Use it with `Read`, `Write`, `Edit`, `Grep`, `Glob`.
- `sandbox_path` — present only in VM mode. It is valid **only** inside
  `mcp__workspace__bash` and is **read-only**. Never pass a `/sessions/...` path to
  `Read` / `Write` / `Edit` / `Grep` / `Glob`; those run on the host, where it does not exist.
- `cached: true` — the artifact was already on disk and passed size + SHA-256 verification, so
  nothing was downloaded this time.
- To extract or install into a writable location from the sandbox, copy the archive into your
  workspace first, then work on the copy.

Download success is **not** installation success. After extracting or installing, verify the
executable really runs (for example `<bin> --version`) before you build further steps on it.

## Handling results

| Result | What it means | What you must do |
| --- | --- | --- |
| `status: "ok"` | Verified archive ready at `path` | Extract / install yourself, then verify the executable. |
| `status: "no_match"` | The mirror has no package for these constraints | Tell the user exactly that, then fall back to the normal public install path under the same version constraint; do **not** silently pick another mirror version. If the target environment might be wrong, retry once with the other `target` value. |
| `code: "invalid_request"` | Your arguments are wrong (with `field` / `reason`) | Fix the argument. Retrying unchanged will fail again. |
| `code: "forbidden"` | Your identity may not use the mirror | Report the restriction. Do not work around it by switching sources. |
| `code: "unauthorized"` | Session invalid or expired | Ask the user to sign in again. |
| `code: "verify_failed"` | The artifact failed integrity checks and was discarded | Report it. Never use the file and never try to bypass the check. |
| `code: "unavailable"` / `"query_failed"` / `"download_failed"` / `"link_expired"` | Transient mirror or network problem | You may retry once later. `query_failed` is **not** the same as `no_match`. |
| `code: "unsupported_target"` | This platform or target is not covered by the mirror | Report it; do not force another platform value. |
| `code: "identity_switched"` | Account / organization changed mid-download, result discarded | Retry under the current identity only if still needed. |
| `code: "skipped_not_premium"` | This edition has no mirror access | Fall back to the normal install path. |

## Hard rules

1. When the mirror returns `no_match`, say so plainly before falling back to public sources -
   the fallback must never hide that the mirror lacked the package.
2. Never treat a failed or unverified artifact as usable, and never re-run the tool in a tight
   loop after `verify_failed` or `invalid_request`.
3. Never print, log or echo a signed download address. The tool deliberately does not return one;
   do not try to obtain it another way.
4. Constraints stay in effect: if you passed `version`, `file_name` or `checksum_sha256`, the
   mirror only returns an artifact satisfying all of them, and a retry keeps them unless the
   user changes the requirement.
5. If the tool is not visible in this session, the current edition does not support the mirror.
   Fall back to the normal install path silently and do not tell the user about this skill.
