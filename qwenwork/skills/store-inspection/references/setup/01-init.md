# 01 · init — 系统初始化

> AI表格 绑定 / 校验 / 重置。**配置时操作**，每个 AI表格 通常只跑 1～2 次。

---

## 速查表

| 想做什么 | 直接看 |
| :--- | :--- |
| 第一次使用，从 0 开始 | [#首次使用](#首次使用) |
| 新建一个全新 AI表格 | [`init create`](#init-create) |
| 在自己已有 AI表格 中筛选绑定 | [`init query`](#init-query) |
| 已知 BASE_ID 或 URL，直接绑定 | [`init url`](#init-url) |
| 检查当前是否已正确初始化 | [`init validate`](#init-validate) |
| 解除当前 AI表格 绑定（⚠️ 仅限用户主动要求时调用） | [`init unbind`](#init-unbind) |

---

## 命令参数（先查 -h，再读决策点）

> 完整参数清单以 `uv run python scripts/cli.py init --help` / `uv run python scripts/cli.py init <subcmd> --help` 为准。
> 本节只列出 Agent 在「决策时」必须知道的关键点。

### init create

- **何时使用**：用户什么都没有，请帮新建一个全新 AI表格
- **副作用**：自动创建 `门店清单` / `巡店模版` / `任务记录` 3 张固定表（受 H2 保护）
- **输出**：`{base_id, base_url, table_ids: {...}}`，校验通过后持久化到 `config.json`

### init query

- **何时使用**：用户说「我有 AI表格 但不记得在哪」
- **后续动作**：列出候选 → 让用户挑选 → 用 `init url` 绑定
- **输出**：候选列表 `[{base_id, name, owner, ...}, ...]`

### init url

- **何时使用**：用户已知 BASE_ID 或粘贴了 AI 表格 URL
- **关键参数**：`--auto-repair` **强烈推荐总是带**——校验失败时自动补齐缺失的固定表 / 字段
- **输出**：`{base_id, validation: {...}}`

### init validate

- **何时使用**：每个业务命令前置检查（步骤 1）
- **输出**：`{is_passed: bool, missing_tables: [...], missing_fields: {...}, type_mismatch: [...]}`
- **Agent 决策**：
  - `is_passed: true` → 进入业务命令
  - 报「未初始化 / base_id 缺失」→ 引导走 `init create / query / url`，不要绕过
  - 报「字段缺失 / 类型不匹配」→ 引导跑 `init url <BASE_ID> --auto-repair` 自动补齐

### init unbind

- **何时使用**：用户**主动明确要求**解除当前 AI表格 绑定时（如需要切换到其他表格、重新创建新表格）
- **副作用**：清除本地 `config.json`，解除与当前 AI表格 的绑定关系；**不会删除 AI表格 数据**
- **关键参数**：`--confirm` 是必传的确认开关；未传时命令拒绝执行并提示重读本文档
- **二次确认**：执行前**必须**先向用户复述「我即将解除当前 AI表格 绑定，确认请回复"确认"」并拿到肯定回复，详见 `../shared/hard-constraints.md#H3`
- **Agent 决策**：**仅当用户主动说出「解除绑定 / 解绑 / 换一个表格 / 重置」等明确意图时才可调用**，禁止在其他流程中自动调用
- **典型场景**：用户希望新建全新 AI表格，但本地已有绑定 → 先 `init unbind --confirm`，再 `init create --name "xxx"`

---

## 首次使用

**触发信号**：用户首次对话；`init validate` 报告未初始化；用户说"刚拿到这个 skill 怎么用"。

### 步骤

1. **判断用户的 AI表格 准备情况**，用 `ask_question` 工具提一个单选问题：
   - A. 我什么都没有，请帮我新建（推荐）
   - B. 我已经有 AI 表格，给你链接 / BASE_ID
   - C. 我有 AI表格，但不记得在哪，帮我搜一下
2. **执行初始化**：
   - A → `cd <SKILL_DIR> && uv run python scripts/cli.py init create --name "巡检任务中心"`
   - B → `cd <SKILL_DIR> && uv run python scripts/cli.py init url <用户给的 URL 或 BASE_ID>`，若校验报缺字段，加 `--auto-repair` 重跑
   - C → `cd <SKILL_DIR> && uv run python scripts/cli.py init query --keyword <关键词>`，列出候选 → 让用户挑 → 用模式 B 绑定
3. **必须展示 AI 表格链接**：`init create` 输出中包含 `base_url`，Agent **必须**将此链接展示给用户（可点击），让用户能直接打开查看自己的 AI 表格。话术示例：「您的 AI 表格已创建：[点击打开]({base_url})」。**绝不能跳过此步骤**——用户需要通过此链接进入 AI 表格进行后续的表单发布等操作。
4. **必告知用户**：⚠️ 这 3 张固定表名禁改：`门店清单` / `巡店模版` / `任务记录`
5. **建议下一步**：进入 [02-store.md#维护门店清单](./02-store.md#维护门店清单)。

---

## 相关参考

- 3 张固定表结构与字段：`../shared/data-model.md#门店清单`
- 高危确认（`init unbind`）：`../shared/hard-constraints.md#H3`
- 配置文件位置：`../shared/glossary.md#数据--配置位置`
