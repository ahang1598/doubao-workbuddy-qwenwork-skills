---
name: criminal-material-intake-gate
name_en: criminal-material-intake-gate
description: 为当前刑事案件建立独立目录，登记全部原始附件，核对案件内路径和逐文件逐页读取或OCR覆盖。触发：收到刑事案件附件、恢复材料处理、刑事文书起草前材料门禁。不触发：实体证据分析、法律研究、文书起草或交付校验。
---

# 刑事案件材料完整性门禁

## 核心职责

本 Skill 只执行确定性的案件目录、原始材料登记、路径归属和页覆盖检查。它不判断犯罪事实，不生成证据分析或法律文书，不依赖模型编写业务 JSON。

## 输入契约

- `workspace_root`：允许创建案件目录的工作区根目录；
- `matter_id`：必需，只允许字母、数字、点、下划线和短横线；
- `resourcePaths`：本轮全部原始附件的明确路径；
- 页覆盖检查另需 `page_count`、`read_pages`、`ocr_pages`、`failed_pages` 和 `retry_count`。

缺少或非法 `matter_id`、路径跨出当前案件、原始材料不存在或重复时返回 `BLOCKED`。非关键材料字段缺失不由本门禁判断。

## 执行顺序

1. 运行 `create-case-workspace`，建立 `<matter_id>` 独立目录及固定子目录。
2. 将全部原始 `resourcePaths` 传给 `register-sources`；不得扫描共享根目录。
3. 根据脚本回执更新 [材料处理进度模板](./templates/material-processing-progress.md)。
4. 对 PDF 逐页记录直接读取或 OCR 覆盖；OCR 成功不等于内容正确。
5. 每份文件运行 `evaluate-page-coverage`。首次缺页只返回局部页，允许一次局部重试；第二次仍缺页返回 `BLOCKED`。
6. 下游使用任何路径前运行 `validate-case-path`，确保路径属于当前案件。

## 固定目录

```text
<matter_id>/
├── 00-原始材料/
├── 01-处理中/
│   ├── material/
│   ├── research/
│   ├── drafting/
│   ├── trial/
│   └── verification/
├── 02-中间成果/
└── 03-最终交付/
```

## 状态和恢复

- `PASS`：目录或材料登记通过，或全部页面已覆盖；
- `NEEDS_LOCAL_RETRY`：首次页覆盖不完整，只重试 `retry_pages`；
- `BLOCKED`：路径越界、材料无效、重复哈希，或局部重试后仍不完整。

用户补交材料后从进度表的断点继续；哈希未变化且已完成的文件不得重复读取或 OCR。

## 输出契约

脚本输出 JSON 回执，包含实际 `case_root`、案件内路径、SHA-256、来源数量、页覆盖状态和局部重试页。材料 Agent 另维护人可读 `材料处理进度.md`，该文件不列入最终交付物。

## 约束限制

1. 不读取未在本轮授权路径或当前案件目录内的材料。
2. 不把 OCR sidecar、摘要或旧制品登记为原始附件。
3. 不以工具成功、文件存在或 OCR 非空替代材料内容正确性判断。
4. 不创建证据目录、辩护策略或刑事文书。

