---
name: doubao-document-delivery
description: Doubao Book Writer 的豆包飞书文档交付方法论。仅在本地 Markdown 已完成并通过写作检查后交付；交付由 make deliver 用 lark-cli 一次性完成——合章、创建飞书文档、读回校验。用户明确只要 Markdown 时不创建飞书文档。
---

# Document Delivery（交付方法论）

交付只把已经通过写作检查的 Markdown 真源镜像到飞书云文档。不得在交付时改写观点、补充新内容，或把云文档反向当成正文真源。

交付动作全部由 `make deliver WORKDIR=<书稿目录>` 完成：长稿先合章生成 `deliverables/final.md`（短稿直接复制 `manuscript.md`），再用 `lark-cli docs` 创建飞书文档，读回后由 `check_lark.mjs` 校验一致性。你不手动维护交付状态，也不手写交付回执——状态即 `.doubao-book-writer/reports/lark_check.json` 与 `doc-result.json` 等真实文件。

用户输入的 PDF、Word、TXT、图片和链接均属于只读素材来源，不是交付的写回目标。默认创建飞书云文档，不覆盖用户上传的原文件；用户明确要求仅 Markdown、导出文件或其他格式时，才按其要求改变交付方式。

## 交付前提

`make deliver` 依赖链会先跑 `write` 与 `prepare` 检查，拦在最早未满足处，因此交付能启动即意味着：

1. 需求清单与布局已通过 `make prepare`。
2. 正文形态、字数、占位符清洁已通过 `make write`（长稿含台账真值）。
3. 终稿 Markdown 非空、可合章。

任一上游检查未过时，依赖链会阻塞在对应阶段并打印修复提示；不要为了交付去绕过上游检查，也不得创建一个内容不完整的云文档充数。

用户明确要求"仅 Markdown"或"不要飞书文档"时，全程加 `SKIP_LARK=1`：`make deliver` 只生成终稿并由 `make status` 判定 PASS，不创建飞书文档。

## make deliver 做什么

交付内部按以下顺序执行，全部由 make 编排，无需你逐条手动运行：

1. **合章/ 生成终稿**：短稿把 `manuscript.md` 复制为 `deliverables/final.md`；长稿用 `merge_chapters.mjs` 把 `manuscript/*.md` 按章序合并为 `deliverables/final.md`。
2. **创建飞书文档**：以 Markdown 格式一次性写入云文档。

   ```bash
   lark-cli docs +create --api-version v2 --doc-format markdown --content @deliverables/final.md --format json
   ```

   命令返回文档 URL 供读回和最终回复使用。
3. **读回校验**：拉回云文档内容与本地终稿比对。

   ```bash
   lark-cli docs +fetch --api-version v2 --doc "<文档URL>" --doc-format markdown --format json
   ```

4. **一致性检查**：`check_lark.mjs` 比对本地终稿与读回文本，写 `reports/lark_check.json`。

`lark-cli docs` 操作显式使用 `--api-version v2`。飞书文档应保持内容结构清晰，不使用装饰性 callout、折叠块、大量 emoji 或无信息价值的复杂布局。

## 读回校验口径

读回校验只做内容一致性，不含任何交付操作证明仪式。`check_lark.mjs` 确认：

- 本地终稿 Markdown 非空；
- 飞书读回内容非空；
- 本地每个 Markdown 标题都能在读回文本中找到；
- 本地与读回内容都不含 TODO、TBD、`{{...}}`、`[待补...]` 等占位符或半成品标记；
- 可见正文的 4-gram 覆盖率达到阈值（默认 0.85）。

任一项不满足即 `status: fail`，交付判为未通过。修复方向是修飞书镜像内容后重跑 `make deliver`，或回上游修正终稿——**正确的 Markdown 不因云文档错误而被覆盖。**

## 交付结论

交付是否完成由 `make status` 给出三态，你只如实转述，不自行宣布完成：

- **PASS**：写作检查通过且飞书读回校验通过（或 `SKIP_LARK=1` 显式跳过飞书且终稿已生成），附文档链接。
- **BLOCKED**：飞书读回校验未过或上游卡住，说明卡点与下一步。
- **DRAFT_ONLY**：写作已过但尚未完成交付，标注未验收草稿，禁止说"已完成"。

最终回复只包含简洁结果、终稿 Markdown 路径和飞书链接或真实阻塞原因；不向用户暴露命令、状态 JSON 或内部机制。

## 失败处理

- 飞书创建/更新失败：保留本地终稿，记录真实错误，不伪造链接。飞书文档创建失败时 `make deliver` 会打印 `doc-result.json` 供排查 lark-cli 登录与权限。
- 读回校验失败：修复飞书文档内容后重跑 `make deliver`，不跳过校验直接标记完成。
- 认证或权限失败：检查 lark-cli 登录状态与文档创建权限；用户身份按最小缺失授权，不自行绕过。
- 飞书失败时保留 Markdown，不回滚正确的本地成果。

## 与其他阶段的衔接

- 上游 `make write`：提供通过形态与字数检查的正文；交付前依赖链自动复查。
- 版式与中文排版细节见 [`references/delivery-layout-policy.md`](./references/delivery-layout-policy.md)。
