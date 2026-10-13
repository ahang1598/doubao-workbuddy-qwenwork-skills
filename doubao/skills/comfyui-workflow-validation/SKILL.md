---
name: comfyui-workflow-validation
description: Use when the user asks for ComfyUI workflow JSON generation/import, ComfyUI报错, 节点找不到, 模型不匹配, 导入失败, CLIP/Flux/MiniMax H3/海螺H3/GGUF model-node adaptation, 本地模型清单, 官方模板复用, dependency installation, or download-link validation.
---

# ComfyUI Workflow Validation

Use this skill to ground ComfyUI workflow generation and troubleshooting in the user's real environment before producing JSON, install steps, or model advice.

## 1. Gate the user intent before touching files

- If the user says only “翻一下”, “解释这张图”, or asks what a screenshot means, answer that scope first; do not edit workflow files or enter a repair loop until they explicitly ask for 排错、导入、修复 or 生成 `workflow JSON`.
- Separate the task into one of these modes: explain screenshot/log, generate new workflow, fix import error, adapt model nodes, install custom nodes, validate links, or assess hardware feasibility.
- For edit requests, preserve versions: if evidence or the user has versioned files, create the next file such as `最大编号+1` instead of overwriting an older `.json` workflow.

## 2. Collect authoritative local inputs

- Before naming exact nodes or model files, read or request the concrete artifacts: screenshot, full console log, existing workflow `.json`, ComfyUI version, `custom_nodes` list, node names, `models` tree, GPU/OS, and dependency URLs.
- Treat ComfyUI local enumerations as authoritative: model choices come from directories such as `models/checkpoints`, `models/clip`, `models/vae`, `models/loras`, `models/unet` or `models/diffusion_models`, not from generic web examples.
- For uploaded files, prefer the provided local path before the URL; when duplicate image names or attachments appear, distinguish them by attachment link/metadata rather than reading one overwritten path twice.

## 3. Inspect installed nodes and schemas before designing

- Resolve missing node classes from the exact failing `class_type` or UI node `type`; then check installed packages under `custom_nodes` and, when available, `NODE_CLASS_MAPPINGS` or ComfyUI-Manager extension-node-map before guessing a repository.
- Check each target node’s `INPUT_TYPES`, widget drop-down values, input socket type, output socket type, and widget order before writing `widgets_values`; never invent enum values such as resize modes from memory.
- If a workflow uses Qwen/LLaVA-style GGUF, classify paired files as LLM `.gguf` plus `mmproj` and route them to llama-TE/LLaVA-style nodes; do not describe them as regular Flux `CLIP` unless the local schema confirms that loader.

## 4. Prefer official templates and known-good local examples

- Start from an official template, node README, model release example, or the user’s already-importing workflow; change only the model names, prompts, dimensions, frame count, and required adapters needed for this user.
- For MiniMax H3/海螺H3 video workflows, explicitly verify the template includes the negative prompt path, video/frame save path, and any `ffmpeg` dependency; if `ffmpeg` is unavailable, deliver a save-frames variant rather than a broken video node chain.
- For Flux-style pipelines, confirm the `UNet`/diffusion model, `CLIP`, `VAE`, LoRA, latent resolution, sampler, scheduler, and any `ModelSampling` node belong to the same documented workflow family before advising a replacement download.

## 5. Validate external dependencies before install advice

- For every dependency URL, verify the GitHub repository, branch, release asset, model filename, and HTTP status before writing install commands; distinguish “已安装可选” from “需要安装”.
- Install custom nodes only into `custom_nodes` and model files only into their matching `models/...` directory; list required and optional files separately, including large CLIP/UNet/VAE/mmproj/LoRA weights.
- Do not propose editing model weight keys, ComfyUI source, or custom converters first; only consider that path after official nodes, official formats, and official conversion instructions fail, and then require a backup plus a low-cost sample.

## 6. Localize the root cause, not symptom patches

- Read the first concrete error chain and map it to one root cause category: missing node, changed node `type`/`class_type`, invalid widget enum, input/output slot mismatch, wrong model directory, incompatible `CLIP`/UNet/VAE/latent channel, missing Python package, or missing `ffmpeg`.
- Before changing links, export or sketch the link table with `from node`, `from slot`, `to node`, `to slot`, and socket type; do not delete or reconnect links whose role is not understood.
- Change one cause class at a time and retain a rollback point; avoid repeated run-and-patch cycles where each failure only changes the latest visible symptom.

## 7. Generate or edit JSON in the correct ComfyUI format

- Distinguish UI workflow JSON from API prompt JSON: UI imports require a root with `nodes`, `links`, node `id`, node `type`, `pos`, and often `widgets_values`; API prompt JSON uses top-level node IDs with `class_type` and `inputs`.
- For UI `links`, verify every link references existing source/target node IDs and the expected slot indices; for API `inputs`, verify references point to existing node IDs and output indexes.
- Before delivery, run a structural check such as `python3 scripts/check_workflow_json.py <workflow.json>` and then manually check semantic items the script cannot know: node schema, required inputs, model filenames, save node, preview node, negative prompt, frame/video output path, and local directory placement.

## 8. Use minimum viable runtime validation

- When runtime testing is possible, first run a tiny sample: low resolution, few `steps`, short frame count/duration, or a single-frame/intermediate-preview path; only scale up after the minimal chain imports and produces an output.
- For image-to-video or video generation, check more than the first frame: inspect a later frame or short clip segment before declaring the I2V/H3 chain successful.
- If using queue/history/server validation, report the exact stage: queued, executing node, completed output, or `exec_errors`; do not merely say “还在跑” without the visible status.

## 9. Package the handoff

- In the final response, list the changed node names/IDs, changed parameters, exact model filenames, destination directories such as `models/checkpoints` or `models/clip`, required `custom_nodes`, and any download URLs that were verified.
- Include import and test steps: where to place the `.json`, how to load it in ComfyUI, what small sample settings to run first, what success signal to expect, and what exact log/screenshot/workflow file to send back if it fails.
- Label uncertainty explicitly: “local installed option”, “official template requirement”, “web-documented but not installed”, or “needs user confirmation”.

## Boundaries

- Never fabricate node structures, `class_type`, `type`, `widgets_values`, model filenames, or directory names before reading user evidence or a local/official source.
- Do not treat web search results as the user’s installed choices; a common ecosystem model is not available until it appears in `models/...` or the user agrees to install it.
- Do not deliver unvalidated workflow JSON; at minimum check JSON parseability, `nodes`/`links` or `class_type`/`inputs` format, unique IDs, link references, required node inputs, key connection types, and model paths.
- Do not add extra complex plugins, unverified-license models, or high-cost GPU settings without explaining why they are needed and checking that they fit the user’s hardware.
- Keep internal reasoning private; show conclusions, evidence, operations, risks, and validation results.

## Example

User: “这个 MiniMax H3 工作流导入后节点找不到，帮我修。”

Response flow:
1. Read the attached `.json` and console error; extract missing UI node `type` or API `class_type`.
2. Check `custom_nodes`, `NODE_CLASS_MAPPINGS`, and ComfyUI-Manager mapping for that exact node.
3. Verify required H3 model files in `models/diffusion_models`, `models/clip`, `models/vae`, or plugin-specific folders.
4. Rebuild from the official MiniMax H3 template or the user’s last importing workflow, replacing only local filenames.
5. Run `python3 scripts/check_workflow_json.py fixed.json`, inspect critical links and save-video dependencies, then hand off install paths and the low-cost test run.
