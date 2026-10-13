# 03 · template — 巡店模版维护

> 模板的 CRUD + 派发消息文案起草。**配置时操作**，新建 / 改文案频次 << 派发频次。

---

## 速查表

| 想做什么 | 直接看 |
| :--- | :--- |
| 创建一个新的巡店模板 | [#创建巡店模版](#创建巡店模版) |
| 起草 / 重写派发&提醒消息文案 | [template-message-drafting.md](./template-message-drafting.md) |
| 启用 / 禁用模板 | [`template enable / disable`](#template-enable--disable) |
| 改派发范围 / 改自定义字段 | [`template update`](#template-update) |
| 列出所有模板 / 查单条详情 | [`template list / get`](#template-list--template-get) |

---

## 命令参数（先查 -h，再读决策点）

> 完整参数清单以 `uv run python scripts/cli.py template --help` / `uv run python scripts/cli.py template <subcmd> --help` 为准。
> 本节只列出 Agent 在「决策时」必须知道的关键点。

### template create

- **派发范围三选一**：
  - `--target-store-ids S001,S002` 指定门店 ID
  - `--target-store-filter '{"tags_any_of":["华北"]}'` 按标签筛选
  - **两个都不传** → 默认所有 `active` 门店
  - **两者互斥**，不能同时传
- **`--custom-fields` JSON 格式**：见 `../shared/data-model.md#custom_fields-json-格式`
- **`--message-title` / `--dispatch-message`**：派发消息字段，**提醒消息复用同一份**（无独立提醒字段）；占位符见 `../shared/placeholders.md`
- **`--remind-time`**：cron 表达式，**CLI 不消费**（仅作元数据存储），周期触发由用户的 Agent 宿主环境配置（见 H6）
- **`--description` 不参与消息渲染**：仅管理后台展示用

### template update

- **`--template-id` 是定位主键**，其余字段与 `template create` 同名，传哪个改哪个（覆盖式更新）
- **`--custom-fields` 变更自动同步表单视图**：当通过 `template update --custom-fields` 修改自定义字段的 `hidden` 属性后，已有活跃任务实例表的表单视图 `visibleFieldIds` 会自动同步更新（隐藏字段从表单中移除，取消隐藏的字段重新显示）。同步失败不阻断 `template update` 主流程，仅输出警告日志

### template enable / disable

- **`enable`**：参与后续派发 / 汇总
- **`disable`**：`dispatch init` 会拒绝引用该模板（用于停用而不删除）

### template list / template get

- **多模板未指定 ID 时**（H8 触发场景）：必须先 `template list --status enabled` 让用户挑选
- **输出**：`template list` 返回 `[{template_id, name, status, ...}, ...]`；`template get` 返回单条详情，含 `custom_fields` 解析后结构

---

## 创建巡店模版

**触发信号**：用户说"创建一个巡店任务 / 加一个每日巡检模版"。

### 步骤

1. **澄清时间策略**（直接对话询问，不要用 `ask_question` 工具）：
   - 是否需要再次提醒（`remind_time`）—— 可选
   > 注：模板里的 cron 字段仅作元数据存储，CLI 不读取也不消费它。
2. **交互定义自定义字段**（**必须用自然语言对话，禁止用 `ask_question` / `ask_human` 表单工具**）：

   > [!CAUTION]
   > **检查项名称必须由用户自己提供，Agent 绝对禁止根据品牌/行业特征自行编造检查项。**
   > 如果用户只说了"创建 XX 巡店任务"但没有列出具体检查项，**必须先用自然语言对话询问用户**：
   > 「请告诉我这次巡店需要检查哪些项目？例如：鲜食柜陈列、收银台整洁度、客流情况……您可以直接列出所有检查项名称，我来帮您配置。」
   > **绝对不要**自己编造检查项然后反问用户"是否确认"——用户根本没机会提供正确的字段。
   > 详见 [`hard-constraints.md#H10`](../shared/hard-constraints.md#H10)

   - 每个字段需要：字段名称 / 字段类型（单行文本 / 单选 / 数字 / 附件等）
   - 单选 / 多选类型还需要提供选项列表
   - 部分字段类型需要额外 `config`（如 `currency` 需 `currencyType`、`rating` 需 `min/max`、`user` 需 `multiple` 等）
   - **巡检拍照类检查项推荐使用 `attachment` 类型**：当用户的检查项需要上传照片（如"鲜食柜陈列""饮料柜""收银台"等），应使用 `attachment` 类型而非 `singleSelect`，这样可以配合 AI 审核自动判定合规情况
   - **AI 审核字段**：对于 `attachment` 类型的巡检拍照字段，可通过 `"ai_review": true` 启用 AI 自动审核。系统会自动创建对应的「AI审核_xxx」字段，AI 根据预设标准自动判定照片是否合规（通过 / 不通过 / 待人工确认）。还可通过 `"ai_standards"` 注入检查项专属的审核标准
   - **⚠️ 用户列出检查项后的确认规则（H10）**：Agent **禁止**根据字段名称语义自行推断字段类型。巡检场景中，默认偏向 `attachment`（拍照 + AI 审核），只有用户明确表示"不需要拍照"时才用 `singleSelect`。**只确认一次原则**：如果用户已明确提供了字段名称和类型（如"每项需要拍照并AI审核"），应直接执行 `template preview` 生成完整预览作为唯一确认环节，**不要在 preview 之前多加一轮确认**。只有用户没说清字段类型时才需要先展示配置表格确认。未收到用户确认前绝对禁止执行 `template create`。详见 [`hard-constraints.md#H10`](../shared/hard-constraints.md#H10)
   - 示例：`[{"name": "鲜食柜照片", "type": "attachment", "ai_review": true, "ai_standards": ["核心单品≥5个", "无欠品", "陈列整齐"]}, {"name": "客流情况", "type": "singleSelect", "options": ["正常", "偏少", "偏多"]}, {"name": "备注", "type": "richText"}]`
   - **⚠️ 用户填写字段必须在 custom_fields 中定义**：骨架字段只包含系统级元数据（巡店任务编号 / task_id / store_id 等），**不包含任何业务语义的用户填写字段**。以下常见字段**必须**作为自定义字段显式定义，否则表单中不会出现：
     - 「督导员」/「巡检负责人」 → `{"name": "督导员", "type": "user"}`
     - 「整改意见」 → `{"name": "整改意见", "type": "richText"}`（注意：`特殊情况备注` 已作为骨架字段自动创建，无需在 custom_fields 中重复定义）
     - 「门店评分」 → `{"name": "门店评分", "type": "rating", "config": {"min": 1, "max": 5, "icon": "star"}}`
     - 详见 [`data-model.md#自定义字段`](../shared/data-model.md#自定义字段)
   - **当用户询问"可以设置哪些自定义字段"时**：先列出 `../shared/data-model.md#custom_fields-json-格式` 中的常用 & 扩展字段类型清单；如用户需要某个字段类型的详细 config 参数，执行 `dws aitable table create -h` 查询；AI 字段参数执行 `dws aitable field create -h` 查询
3. **确认目标门店范围**：
   - 指定门店 ID → `--target-store-ids S001,S002`
   - 按标签筛选 → `--target-store-filter '{"tags_any_of":["华北"]}'`
   - 都不填 → 默认所有 `active` 门店
4. **执行创建**：

```bash
cd <SKILL_DIR> && uv run python scripts/cli.py template create \
  --name "每日巡检" \
  --description "每日巡检模板：覆盖陈列、客流、安全 3 项基础检查" \
  --dispatch-message "【{任务名称}】{店长姓名}你好，请完成今天的{门店名称}巡检，任务表：{任务表名}\n\n[👉 立即填写]({表单链接})" \
  --custom-fields '[{"name":"鲜食柜照片","type":"attachment","ai_review":true,"ai_standards":["核心单品≥5个","无欠品","陈列整齐"]},{"name":"饮料柜照片","type":"attachment","ai_review":true,"ai_standards":["商品摆放整齐","价签对应"]},{"name":"客流情况","type":"singleSelect","options":["正常","偏少","偏多"]},{"name":"备注","type":"richText"}]' \
  --target-store-ids S001,S002
```

> [!NOTE]
> 如果用户没指定 `--dispatch-message`，**Agent 应该主动起草并立即写入**，
> 完整处方见 [template-message-drafting.md](./template-message-drafting.md)。

---

## 起草派发/提醒消息文案

> 完整的「Agent 起草 + 一稿即写入」处方（触发信号 / 总原则 / 步骤 / 输出样板 / 风格规范）
> 已独立到 [template-message-drafting.md](./template-message-drafting.md)，请直接阅读该文件。

简要规则（避免漂移，详细规则一律以 `template-message-drafting.md` 为准）：

- **默认一稿即写入**，不主动追问"是否调整"
- 起草后**立刻**调用 `template update --message-title ... --dispatch-message-file ...` 写入
- 二次更新只发生在用户主动说出具体修改点时
- 提醒消息无需单独维护（messenger 自动复用，详见 `../shared/placeholders.md#提醒消息自动复用派发模板`）

---

## 相关参考

- 起草消息文案完整处方：[template-message-drafting.md](./template-message-drafting.md)
- 字段定义（含 `custom_fields` JSON 格式）：`../shared/data-model.md#巡店模版`
- 占位符 / 提醒复用机制：`../shared/placeholders.md#提醒消息自动复用派发模板`
