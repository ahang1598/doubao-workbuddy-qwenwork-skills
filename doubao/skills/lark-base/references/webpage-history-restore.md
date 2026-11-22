# 网页历史还原

用户明确要求把当前编辑版本恢复到某个历史版本时，先定位目标页面，再用 `+webpage-history-list` 确认目标版本仍在 `artifactMap` 中，随后执行 `+webpage-history-restore`。`--rev` 使用接口中的原始版本号，版本 0 有效。

## 定位目标页面

- 本轮明确指定页优先，否则用引用页（含卡片标题）。产品消息即使只有“还原到版本 N”，也应从附带的页面名称和链接定位目标。已有可信 `base_token` 和页面 `block_id` 直接沿用；完整链接交给 `+url-resolve`，保留 `table` 等参数，不先截成 Base 根链接。返回 `block_type=webpage` 时使用其 `base_token` 和 `block_id`，不因参数名为 `table` 改走数据表、记录历史或整库还原；其他类型按 [Base 定位流程](../scenes/base.md#定位已有-base)处理，不混用表或仪表盘 ID。
- 缺页面 ID 时，用 `+webpage-list` 完整分页，按标题匹配或发现页面；唯一确定后继续，无法唯一确定或信息冲突才询问，不新建页面。
- 只查目标页历史；缺版本就报告，不遍历其他页或搜索任务记忆反推、替换目标。

## 选择版本并还原

前端展示版本号 = 原始 rev + 1，Git 标签为 `v<rev>`。用户按前端要求“还原至版本 N”时，目标是 `rev=N-1`；例如“还原至版本 1”对应 Git 标签 `v0`，应执行 `--rev 0`，并确认 `artifactMap["0"]` 仍保留。接口中的 `curRev`、`publishedRev` 和 `artifactMap` 键均按原始 rev 理解；用户显式指定 rev 或 Git 标签时直接使用原值，不重复减 1。

```bash
lark-cli base +webpage-history-list --base-token <base_token> --block-id <block_id>
lark-cli base +webpage-history-restore --base-token <base_token> --block-id <block_id> --rev <revision> --dir ./page
```

例如，用户要求还原至前端版本 1：

```bash
lark-cli base +webpage-history-restore --base-token <base_token> --block-id <block_id> --rev 0 --dir ./page
```

命令核对本地保存的编辑基线；不一致时先 pull 并合并。未提交改动或合并冲突会阻止还原，保留现场，处理完成后再重试。目标必须有可恢复的 Git 标签；不能拿当前散文件代替缺失的历史源码。

源码和依赖先在候选目录准备。当前版本未提供按历史版本绑定的模板元数据，沿用该工作区固定的模板和锁文件，并在进度中说明；不能据此声称历史模板与依赖已精确追溯。

还原写入与 push、pull 共用页面锁，拿锁失败即返回失败。远端成功后，CLI 才把目标源码交付到原目录，并保留还原前 HEAD 的分支引用及全部版本标签。成功结果在 `data.operation` 中：`operation_type=restore`、`state=succeeded`。还原不新增版本，不修改发布版本；还原后的下一次 push 按最大版本号递增，并继续追加到最大版本标签的提交。

网络失败或结果未确认时，重试同一页面、目录和 rev 的原命令，CLI 会沿原 op 恢复；也可用 `+webpage-operation-get` 按 operation_id 查询。不要删除 `.webpage/restore.json`、替换候选材料、另开 push 或篡改基线。已经写入 TOS 的失败会保留页面占用，直到原操作恢复并确认最终登记。

只有远端成功且本地交付完成，命令才输出成功。若远端已成功，但本地在上传期间有新修改，命令保留新修改并说明状态；不能覆盖现场或把它描述为远端失败。
