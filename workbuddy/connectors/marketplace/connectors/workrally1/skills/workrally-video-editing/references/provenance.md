# Reference provenance

This skill is a port of the Higgsfield `video-editing` skill (Codex plugin v1.5.0).

The upstream skill was a wrapper around `higgsedit`, a proprietary Node-based
timeline and motion-graphics CLI (pinned to `/opt/fable/VERSION.json`, native CLI
v0.14.0) that ran inside Higgsfield's `sandbox_exec` cloud sandbox. Its thirteen
reference files documented that CLI's JSX composition API, keyframe and choreography
semantics, GLSL shader contract, project mutation verbs and inspection commands.

**None of that runtime exists in WorkRally**, and the binary is not distributable
with this plugin. The upstream API documentation was therefore not carried over
verbatim — shipping it would instruct the agent to invoke commands that always fail.

What was retained is the upstream's **organisation and editorial discipline**:
separating the generation contract from craft guidance, grouping references by
deliverable, and stating explicitly what each command does and does not prove.

The mechanics were re-authored against the capabilities WorkRally actually has:

| Upstream reference | Disposition here |
|---|---|
| `compose.md` | dropped — higgsedit JSX / GLSL API, no analogue |
| `animation-contract.md` | dropped — higgsedit clock semantics, no analogue |
| `editor-measured.md` | dropped — higgsedit CLI runtime contract |
| `workflows.md` | dropped — `higgsedit do` / `ops` / `sync`; assembly notes folded into `assembly.md` |
| `caption-titling.md` | folded into `caption-systems.md` |
| `assembly.md` | re-authored → local ffmpeg |
| `clip-geometry.md` | re-authored → aspect-ratio and resolution enums + ffmpeg reshaping |
| `caption-systems.md` | re-authored → ASS + ffmpeg `subtitles` burn |
| `title-animation.md` | re-authored → ASS override tags + ffmpeg `overlay` |
| `motion-language.md` | re-authored → Chinese prompt vocabulary for generative edits |
| `shot-blueprints.md` | re-authored → need → mechanism map for this toolchain |
| `failure-modes.md` | re-authored → real error strings from `canvas_generate_video` and ffmpeg |
| `provenance.md` | this file |
| — | `generative-edit.md` added — the three WorkRally edit modes |
| — | `ffmpeg-recipes.md` added — deterministic local operations |

The upstream reference organisation was itself informed by the public Apache-2.0
project [heygen-com/hyperframes](https://github.com/heygen-com/hyperframes),
inspected at commit `8800214`; only general documentation patterns were retained.

Tool and parameter mappings shared across this plugin live in
`../../references/workrally-mcp-mapping.md`.
