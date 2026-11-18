---
keyword: move
---

**功能**：在同一文档内移动完整段落、标题、列表项或整表，调整内容顺序

**依赖关键词**：`local-update`

# 完整块移动

参数遵循 `local-update` 和本页规则。CLI 返回未知命令或参数，或有版本漂移证据时，查看当前 `--help`。支持 `move` 时优先使用，不以插入、删除代替。

## 调用与参数

`--revision-id` 必填，使用 Fetch 返回的 `data.document.revision_id` 或上一笔成功回执的 `new_revision_id`；有效范围为 `0–2147483647`，超出时报告版本不兼容，不截断、不传 `-1`。

`--move-option` 仅含 `source`、`destination`。直接传入 JSON，ID 和版本替换为本次 Fetch 值：

```bash
lark-cli docs +local-update --doc "<token>" \
  --command move --revision-id 123 \
  --move-option '{"source":{"block_ids":["<source_B>","<source_D>"]},"destination":{"kind":"block_edge","block_id":"<target_E>","position":"after"}}'
```

| 字段 | 规则 |
|---|---|
| `source` | 仅含 `block_ids`：1–1000 个非空白、唯一的字符串 ID；原样使用，不拆分逗号或修剪 ID |
| `destination.kind=block_edge` | 仅含 `kind`、`block_id`、`position=before\|after`；落在合法正文块前后 |
| `destination.kind=container_edge` | 仅含 `kind`、`container_id`、`position=start\|end`；落在正文或正文单元格首尾 |

正文根容器 ID 从 `layout` 读取，单元格 ID 从完整表格读取；容器 ID 不是文档 token。

`--move-option` 支持内联 JSON、`@relative-file` 或 stdin `-`；路径、单 stdin 和请求大小沿用公共契约。不混用 `--block-id`、`--content`、`--pattern` 或其他领域 option。JSON 不加 `action`、revision 或 `command_params` 包裹层，不二次编码；各层只使用表中字段，不重复成员或混用两种目标结构。

## 移动范围与限制

- 支持完整段落、标题、列表项及其子列表、整表和目录容器。源可非连续，可跨页、节、正文与单元格或不同单元格；不能重复或相互包含，目标不能是源自身或位于源子树内。
- 标题不自动带走章节正文，对象不自动带走相邻题注，除非它们已包含在所选子树中。选齐用户要求移动的完整块，不为通过校验而自动扩大范围。
- 多个源保持原文档的相对顺序，不按 `block_ids` 数组顺序排列。例如 A、B、C、D、E 中，将 B、D 移到 E 后得到 A、C、E、B、D；输入 D、B 也得到相同结果。
- 内嵌对象随宿主段落、浮动对象随锚点段落，保留格式、资源、尺寸、环绕和相对定位。跨节后采用目的节布局，分节符与节配置留在原处；改变浮动对象几何位置用 `object`。
- 整表或任何含表子树不能进入单元格。列表层级保持，不自动合并列表；移入列表父项时，源只能为比父项深一级的列表项。搬空单元格时由宿主维护必需尾段，不自行删除补出的合法空段。
- 跨块书签、批注和 Field 范围必须闭合，相关承载块全部选中且顺序不变，落点也不能切开既有范围。不丢弃关联或拆分段落来通过校验；锁定内容拒绝移动。

不支持局部文字、段内落点、多目标原子重排、跨文档移动或复制、单独移动行列或单元格、分节符、几何调整，以及页眉页脚、脚注尾注、TextBox 内部移动。

### 关联限制

普通 SEQ 和可安全求值的简单 REF 可在同一事务维护；需要刷新域结果时，必须在同一事务内安全维护。

- 正文存在 PAGE、NUMPAGES、SECTION、SECTIONPAGES、PAGEREF、STYLEREF、NOTEREF、LISTNUM 或带 `\s` 的 SEQ 时，实际移动默认整批拒绝，即使这些域不在源内。
- 使用受支持参数和开关的既有悬空 PAGEREF / NOTEREF 仅在以下条件均满足时原样保留：目标书签在移动前后均无定义或残留边界；域指令、边界、嵌套关系和完整载体文本保持不变；载体不受本次移动影响。有效引用、残缺书签、新增悬空或移动引用域自身仍会整批拒绝。
- 仅有 `style_id` 而无直接 `numId` 的列表、需维护的编号 REF（`\n/\r/\w`）、锁定或嵌套域、跨块结果、无法安全维护的格式或关联，以及正文级书签无法安全跨单元格转换时也拒绝。

一次请求全部成功或零写入，不同目标需串行调用，跨调用不保证原子性。合法原位移动为成功 no-op，不推进版本或新增修订；B 已紧邻 C 时，将 B 移到 C 前可为 no-op，将 B 移到 B 前仍非法。no-op 也须通过参数、关联与权限校验。

## 修订行为

move 跟随 `document_mode`，不自动切换模式或接受/拒绝旧修订；`track_revisions`、`show_revisions` 不决定是否生成修订。本人或他人的已有待审内容按完整块剪切粘贴规则处理，不要求先清除。旧修订可保留、裁剪或吸收，普通编辑模式也须维护其语义；实际变化以 `revision_changes` 为准。

修订模式下，标准移动表现为源 DELETE、目标 ADD，目标使用独立 ID；两端独立审阅，不生成 moveFrom/moveTo，也不联动补偿。对无旧修订的标准移动：

| 源 DELETE | 目标 ADD | 最终保留 |
|---|---|---|
| 接受 | 接受 | 仅目标一份 |
| 拒绝 | 拒绝 | 仅源一份 |
| 拒绝 | 接受 | 两处各一份 |
| 接受 | 拒绝 | 两处都移除 |

只有用户要求审阅时，才按 `revisions` 协议接受或拒绝；提交前查询当前待审 ID 与最新 `state_fingerprint`。不能把 ID 映射当成修订配对，或把 `removed_revision_ids` 当作仍可审阅的 ID；其他卡也可能包含更早修改，不作为本次独有撤销单元。

## 回执与后续操作

成功信封及 warnings 遵循 `local-update`；move 成功须为 `data.result=success`，`data.command_result` 字段如下：

| 字段 | 含义与后续处理 |
|---|---|
| `changed` | `true` 为实际移动，`false` 为成功 no-op；不能把 no-op 当失败重试 |
| `moved_block_ids` | 原文档顺序的源根 ID；no-op 为 `[]` |
| `block_id_map` | 普通编辑或 no-op 为 `{}`；修订模式实际移动时为源 ID → 新目标 ID，可含后代，不表示修订配对 |
| `new_revision_id` | 实际提交后的文档版本；下一笔写入的 `--revision-id` 可使用上一笔成功回执返回的 `new_revision_id`；no-op 返回当前版本，不自行加一 |
| `revision_changes.status=complete` | `created_revision_ids`、`updated_revision_ids`、`removed_revision_ids` 分别列出新增、更新和移除的待审修订 ID，可全为空；不固定生成两张卡 |
| `revision_changes.status=not_applicable` | 本次不涉及修订维护，不代表文档没有修订 |
| `revision_changes.status=unavailable` | 编辑已成功，`reason` 说明关联回执不可用；补读修订和内容，不能重试 move |

`updated_blocks_count` 是实际变化块数（含关联维护），不一定等于源数量；no-op 为 0。`data.document.new_blocks=[]`，修订目标 ID 从 `block_id_map` 取得，不从该数组推导。

## 异常处理

按数值 code 和结构化 detail/reason 判断原因，不匹配动态 message 全文：

| 错误 | 处理 |
|---|---|
| `4000002`（常见 `WORD_AI_MOVE_INVALID`） | 修正参数、结构或关联范围；不自动扩选 |
| `4000003`、`4000911`、`4000031/BLOCK_MOVE_STALE`、`4000028/EXEC_REVISION_CONFLICT` | 重新 Fetch 源、目标和版本；`4000028/4000031` 的其他原因须排查，不循环重试 |
| `4030004` | 权限或保护拒绝，停止写入 |
| `5000002`（列表绑定或 Field 结果不支持） | 当前能力不足；不删关联、不降级为删除重建 |
| `4130000`、`4000010/4000011/4000021/4000027` | 变化块数或文档结构限额；调整合法范围，拆分后不再保证整体原子 |
| `4000920` | 文档就绪后重新 Fetch，不在未就绪状态下重复写入 |

超时、断连或回执不完整时，按 [recovery](../../workflows/canvas-doc-recovery.md) 跟进原请求；请求结束后仍不能确定结果时，读取源、目标和受影响关联确认实际状态，不盲重试或用反向 move 补偿。
