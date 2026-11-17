---
keyword: object
---

**功能**：已有浮动 image/shape 的移动、缩放、旋转、翻转、层叠、重锚和复制

# 本地 Word：浮动对象读取与操作

先 Fetch `object_context` 选择正确 physical occurrence，原样复制其 `update_context_base`，只补 operation 对应的最小参数；不得从正文 XML、可见文本、页码或 selection 猜 identity。参数遵循 `local-update` 和本页规则；未知参数或版本漂移时查看当前 `--help`，不将内部 `command_params` 字段臆造为 CLI flag。

---

## 浮动对象：`object_context` → `object`

Fetch `object_context` 的 operation 闭集为 `stacking/reanchor/copy/transform`。对象 identity 使用 `{kind:image|shape,block_id,instance?}`，TextBox 使用 Shape 的 `<shape>` ID；stacking/copy/transform 可传 1..16 个对象，reanchor 传单个对象和目标段落。返回 exact occurrence 候选、只读 `location`、能力/动作和 `update_context_base`；稳定 identity、instance 与 fingerprint 只从 base 取得。候选超过 100 或无法形成唯一合法组合时明确失败。

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

`location.physical_page_index` 只是 0-based 提示，不参与身份校验。Header/Footer 必须使用 base 中的完整 placement 和 pagination revision；copy/transform 还须原样回填 base 中的 story-state fingerprint，reanchor 仅使用 exact occurrence 与 placement fingerprint，不能额外传 story-state 字段。operation 专属 guard 不可混传。不允许当前 story、首 occurrence 或当前 selection 回退。当前不支持 inline、水印、group member、跨 story/placement、跨文档资源迁移或任意数值 z-order。

`copy` 的回执在 `created_objects` 返回新对象身份。