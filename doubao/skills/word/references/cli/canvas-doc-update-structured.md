# 本地 Word：结构化读取与领域更新

> 使用前须完整读取本页；未见末行「全文完」时，调整 offset 继续读取至该标记。

本页覆盖批注、Field 更新、表格几何和浮动对象。它们都遵循同一闭环：**Fetch 结构化状态 → 选择唯一 identity / physical occurrence → 原样复制 guard 或 `update_context_base` → 补充最小 action 参数 → Update → 重新 Fetch 验证**。不得从正文 XML、可见文本、页码或 selection 猜 identity。

命令行使用公共契约及本页列出的参数；CLI 返回未知参数或有版本漂移证据时再查看当前 `--help`，不将内部 `command_params` 字段臆造为 CLI flag。

## 批注：`comments` → `comment`

Fetch `comments` 可按 target ID 过滤并分页；默认 50、最大 100。结果返回批注树、锚点、`state_fingerprint`，按需返回目标的 `target_fingerprint`。作者、时间和持久 ID 只读。

| action | 关键输入 | guard |
|---|---|---|
| `create_root` | `content`、非空 `anchors` | 每个 target 的 `expected_target_fingerprint` |
| `update_comment` | `comment_id`、`content` | `expected_state_fingerprint` |
| `add_reply` | `comment_id`、`content` | `expected_state_fingerprint` |
| `update_reply` | `comment_id`、`reply_id`、`content` | `expected_state_fingerprint` |
| `resolve` / `reopen` / `delete_comment` | `comment_id` | `expected_state_fingerprint` |
| `delete_reply` | `comment_id`、`reply_id` | `expected_state_fingerprint` |

`create_root` 最小 option：

```json
{"action":"create_root","content":"...","anchors":[{"kind":"text_range","start":0,"end":5,"block_id":"...","expected_target_fingerprint":"sha256:..."}]}
```

锚点闭集：同一 textual record 内非空的 UTF-16 `text_range`、已有对象的 `object`、图片上 `[0,1]` 归一化矩形 `image_area`。`text_range` 使用段落等文本记录及其 fingerprint；table/td 等结构容器不是文本目标，表格区域用其内部按文档顺序排列的一个或多个 `text_range`。根批注正文必须用 `update_comment`；`update_reply` 的 `reply_id` 必须属于该根批注。不得伪造作者、时间或 ID。写后回读批注树，并核对正文 marks、对象锚点和解决态。

## Field：`fields` → `field_update`

Fetch `fields` 支持 `field_ids/types/updatable_only/include_cached_result/cursor/limit`；默认 100、最大 500。每项返回 `story_id`、`field_id`、类型、可选缓存结果、`updatable` 和稳定 blocker。

更新只提交同次 Fetch 返回的 `story_id + field_id`，并使用同次 revision。它只重新求值已有且明确可安全更新的 Field，不修改 instruction，也不创建 Field。成功但结果不变会返回 `changed=false`，这是成功 no-op。

PAGE、NUMPAGES、SECTION、SECTIONPAGES、PAGEREF、STYLEREF、TOC-owned PAGEREF、页眉页脚 Field、交互 Field、INDEX、结构父域和不完整/锁定/多实例 Field 当前不可更新；以 `updatable` 与 blocker 为准，不尝试用 XML 改写结果绕过。

## 表格几何：`table_geometry`

Fetch `table_geometry` 必须提供共享 table record ID，返回 `occurrences[]`。每个 occurrence 包含只读 `location`、px 几何、单位及 `update_context_base`；exact `instance` 和双 fingerprint 只在该 base 中返回，不从候选外层取值：

```json
{"update_context_base":{"block_id":"...","table_option":{"instance":{},"expected_topology_fingerprint":"...","expected_geometry_fingerprint":"..."}}}
```

从一个候选原样复制 `update_context_base`，只向 `table_option` 加入 action 和对应字段：

| action | 动作字段 |
|---|---|
| `distribute_columns` | `scope=table`，或 A1 `range` |
| `distribute_rows` | `scope=table`，或 1-based `row_start_index/row_end_index` |
| `resize_column_boundary` | 1-based `boundary_index`、`anchor_row_index`、有符号 `delta_twips` |
| `resize_row_boundary` | 1-based `boundary_index`、有符号 `delta_twips` |
| `resize` | 最终 `width_twips/height_twips` |
| `reorder_rows` / `reorder_columns` | 1-based 闭区间与基于移动前序列的 insertion boundary |

读取几何是 px，写入尺寸/位移是 twips，响应会给出 `twips_per_px=15`；不要混用。Header/Footer、TextBox 或多实例表格必须选择精确 occurrence，绝不取首项。边界拖动、均分、行列重排和整表物理缩放使用本命令；普通插删行列、合并拆分和单元格属性更新仍使用 [`table`](canvas-doc-update-table.md)。列宽声明、行高及其规则、表格对齐和 preferred width 使用完整 XML。

## 浮动对象：`object_context` → `object`

Fetch `object_context` 的 operation 闭集为 `stacking/reanchor/copy/transform`。对象 identity 使用 `{kind:image|shape,block_id,instance?}`，TextBox 使用 Shape 的 `<shape>` ID；stacking/copy/transform 可传 1..16 个对象，reanchor 传单个对象和目标段落。返回 exact occurrence 候选、只读 `location`、能力/动作和 `update_context_base`；稳定 identity、instance 与 fingerprint 只从 base 取。候选超过 100 或无法形成唯一合法组合时明确失败。

选择正确 physical placement 后，原样复制该候选的 `update_context_base`，再按 operation 补充最小字段：

| operation | object action | 补充字段 |
|---|---|---|
| `stacking` | `bring-forward` / `send-backward` / `bring-to-front` / `send-to-back` | 从 `available_actions` 选择 action |
| `reanchor` | `reanchor` | Fetch 时提供同 story、同 placement 的目标段落；候选基底已固定 action |
| `copy` | `copy` | 候选基底已固定 action；复制 1..16 个同 placement 对象 |
| `transform` | `move` | `dx_pt/dy_pt` |
| `transform` | `resize` | primary 最终 `width_pt/height_pt` |
| `transform` | `rotate` | `delta_deg` |
| `transform` | `flip` | `axis=horizontal|vertical` |

`location.physical_page_index` 只是 0-based 提示，不参与身份校验。Header/Footer 必须使用 base 中的完整 placement 和 pagination revision；copy/transform 还须原样回填 base 中的 story-state fingerprint，reanchor 仅使用 exact occurrence 与 placement fingerprint，不能额外传 story-state 字段。不允许当前 story、首 occurrence 或当前 selection 回退。当前不支持 inline、水印、group member、跨 story/placement、跨文档资源迁移或任意数值 z-order。

写后重新 Fetch 相同 operation：核对对象 identity、锚点、层级或几何。`copy` 从 `created_objects` 获取新 identity；不要从 `new_blocks` 猜测。涉及视觉位置、尺寸或层级时按工作流补充 PDF/页面视觉证据。

===== 全文完 =====
