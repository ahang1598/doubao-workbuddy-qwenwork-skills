# 02 · store — 门店清单维护

> 门店与店长信息的 CRUD。**配置时操作**，新增 / 调整频次 << 派发频次。

---

## 速查表

| 想做什么 | 直接看 |
| :--- | :--- |
| 新增门店（含查通讯录） | [#新增](#新增) |
| 批量新增门店（JSON / 文件导入） | [#批量新增](#批量新增) |
| 直接在 AI 表格中管理门店（自助） | [#直接在-AI-表格中管理门店](#直接在-AI-表格中管理门店) |
| 调店长 / 改标签 / 暂停门店 | [#修改含调整店长--改标签--暂停](#修改含调整店长--改标签--暂停) |
| 永久删除门店（高危） | [#删除高危](#删除高危) |
| 查门店列表 / 详情 | [`store list / store get`](#store-list--store-get) |

---

## 命令参数（先查 -h，再读决策点）

> 完整参数清单以 `uv run python scripts/cli.py store --help` / `uv run python scripts/cli.py store <subcmd> --help` 为准。
> 本节只列出 Agent 在「决策时」必须知道的关键点。

### store add

- **`--store-id` 一旦创建禁止改**——主键约束，推荐 `S001` `S002` …
- **`--manager`**：店长的 **userId**（user 类型），先用 `dws contact user search` 查到联系人，从 `result[0].userId` 中提取
- **业务约束**：大区 / 区域 / 示范店等**分类属性统一走 `--tags`**，不要为这些分类单独新增字段（避免 schema 漂移）

### store batch-add

- 支持 **`--json`**（JSON 数组字符串）或 **`--file`**（JSON 文件路径）两种方式
- 每条记录至少包含 `store_name` 和 `manager`（userId），`store_id` 可选（不传则自动生成）
- 单次批量不超过 30 条

### store update

- **`--store-id` 是定位主键**，其余字段与 `store add` 同名，传哪个改哪个
- **`--manager`**：传入新店长的 userId 即可

### store delete（高危）

- **`--yes` 是二次确认开关**，不传则 CLI 拒绝执行
- **执行前必须**先向用户复述「将永久删除门店 X，确认请回复"确认"」并拿到肯定回复，详见 `../shared/hard-constraints.md#H3`

### store list / store get

- **`store list --tags`**：标签过滤是**任意命中**（OR）语义，不是全部命中
- **输出**：`store list` 返回 `[{store_id, store_name, ...}, ...]`；`store get` 返回单条门店详情

---

## 维护门店清单

**触发信号**：用户说"添加门店 / 录入门店 / 把张三调到 xxx 店 / 把某店停掉"。

### 新增

#### 步骤 1：先通过通讯录查询店长信息

```bash
dws contact user search --query '张三' --format json
```

从返回的 `result[0]` 中提取 `userId`，作为 `--manager` 参数传入。

> 若需获取当前登录用户自己的信息（如 userId、corpId）：
> ```bash
> dws contact user get-self --format json
> ```
> 返回示例：`{"result":[{"orgEmployeeModel":{"corpId":"dingXXXX...","userId":"000001","orgUserName":"张三",...}}],"success":true}`

#### 步骤 2：新增门店

```bash
cd <SKILL_DIR> && uv run python scripts/cli.py store add \
  --store-id S001 \
  --store-name "北京朝阳店" \
  --manager <从 contact user search 返回的 userId> \
  --tags 华北,旗舰店 \
  --status active
```

### 批量新增

**触发信号**：用户说"批量添加门店 / 一次加多家门店 / 导入门店列表"。

支持两种方式：

#### 方式 1：直接传 JSON 数组

```bash
cd <SKILL_DIR> && uv run python scripts/cli.py store batch-add \
  --json '[{"store_id":"A001","store_name":"A 门店","manager":"10000","tags":"华东大区"},{"store_id":"A002","store_name":"B 门店","manager":"u_lisi","tags":"华西大区"},{"store_id":"A003","store_name":"C 门店","manager":"u_wangwu","tags":"华西大区"}]'
```

#### 方式 2：从 JSON 文件导入

```bash
cd <SKILL_DIR> && uv run python scripts/cli.py store batch-add --file /path/to/stores.json
```

文件内容为 JSON 数组，每条记录至少包含 `store_name` 和 `manager`（userId），`store_id` 可选（不传则自动生成）。

**Agent 决策**：

- 用户需要添加 **1～3 家**门店 → 走 [#新增](#新增) 逐条 `store add`
- 用户需要添加 **4 家以上**或明确要批量 → 走 `store batch-add`
- 单次批量不超过 30 条

### 直接在 AI 表格中管理门店

**触发信号**：用户说"我想自己在表格里管理门店 / 给我门店表格地址 / 我要批量录入门店 / 门店比较多想直接在表格里加"。

当门店数量较多或用户希望自助管理时，可以直接提供门店清单表的 AI 表格链接，用户在表格中自行增删改查：

```bash
cd <SKILL_DIR> && uv run python scripts/cli.py store url
```

**Agent 决策**：

- 用户**只需添加少量门店**（1～3 家）→ 优先走 [#新增](#新增) 的 Agent 交互流程，逐条通讯录查询 + `store add`
- 用户**门店数量较多**或**明确希望自己管理**→ 使用 `store url` 输出表格链接，引导用户直接在 AI 表格中操作
- 用户**没有明确偏好**→ 主动告知两种方式：①通过 Agent 逐条添加 ②直接在 AI 表格中管理，让用户选择

**给用户的注意事项**（`store url` 输出中已包含，Agent 可补充说明）：

- `store_id` 是主键，一旦填写禁止修改，推荐 `S001` `S002` … 格式
- 必填字段：`store_id`、`store_name`、`manager`（user 类型，在表格中直接选择钉钉用户即可）
- `status` 仅允许 `active` / `inactive`
- `tags` 为多选字段，可自由添加标签用于分组筛选

### 修改（含调整店长 / 改标签 / 暂停）

```bash
# 调店长（传入新店长的 userId 即可）
cd <SKILL_DIR> && uv run python scripts/cli.py store update --store-id S001 --manager <新店长userId>

# 改标签
cd <SKILL_DIR> && uv run python scripts/cli.py store update --store-id S001 --tags 华南,示范店

# 暂停（不删历史）
cd <SKILL_DIR> && uv run python scripts/cli.py store update --store-id S001 --status inactive
```

### 删除（高危）

1. 先向用户复述：「将永久删除门店 S001，确认请回复"确认"」
2. 用户确认后：
   ```bash
   cd <SKILL_DIR> && uv run python scripts/cli.py store delete --store-id S001 --yes
   ```

---

## 相关参考

- 字段定义（`store_id` 主键约束 / `tags` 多选 / `status` 枚举）：`../shared/data-model.md#门店清单`
- 高危确认规则（`store delete --yes`）：`../shared/hard-constraints.md#H5`
