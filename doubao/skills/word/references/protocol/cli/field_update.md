---
keyword: field_update
---

**功能**：Field 读取与结果刷新

# 本地 Word：Field 读取与结果刷新

先 Fetch `fields`，使用同次返回的 `story_id`、`field_id` 和 revision 刷新结果；不得从正文 XML、可见文本、页码或 selection 猜 identity。参数遵循 `local-update` 和本页规则；未知参数或版本漂移时查看当前 `--help`，不将内部 `command_params` 字段臆造为 CLI flag。

---

## Field：`fields` → `field_update`

Fetch `fields` 支持 `field_ids/types/updatable_only/include_cached_result/cursor/limit`；默认 100、最大 500。每项返回 `story_id`、`field_id`、类型、可选缓存结果、`updatable` 和稳定 blocker。

更新只提交同次 Fetch 返回的 `story_id + field_id`，并使用同次 revision。它只重新求值已有且明确可安全更新的 Field，不修改 instruction，也不创建 Field。成功但结果不变会返回 `changed=false`，这是成功 no-op。

PAGE、NUMPAGES、SECTION、SECTIONPAGES、PAGEREF、STYLEREF、TOC-owned PAGEREF、页眉页脚 Field、交互 Field、INDEX、结构父域和不完整/锁定/多实例 Field 当前不可更新；以 `updatable` 与 blocker 为准，不尝试用 XML 改写结果绕过。