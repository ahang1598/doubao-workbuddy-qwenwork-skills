# AI 表格读取规范

## 目标

只读、完整、可重复地取得生成报告所需的 Base 目录、表结构、字段配置、记录和行级分享链接。所有 ID 必须来自 URL 或查询结果，不能编造。

## 运行时边界

本 skill 自带 `scripts/fetch_dingtalk_aitable.py`，不要求安装 `dingtalk-aitable` 或其他数据读取 skill。脚本内部已经固化认证检查、字段读取、全量分页、字段分片合并和记录链接抓取流程。

实时读取仍需要钉钉官方 DWS CLI 及当前用户自己的有效登录态；skill 不携带也不代管凭据。没有 DWS 的用户可以提供 CSV/JSON 导出文件，报告能力不受影响，只是无法自动生成钉钉行级跳转链接。

通用用法：

```bash
python3 scripts/fetch_dingtalk_aitable.py \
  --url '<AI表格URL>' \
  --output-dir <snapshot-dir>
```

也可以显式传 ID：

```bash
python3 scripts/fetch_dingtalk_aitable.py \
  --base-id <baseId> --table-id <tableId> --view-id <viewId> \
  --output-dir <snapshot-dir>
```

在千问办公中必须把内置脚本作为首选执行入口。先定位已加载 skill 的真实根目录，再运行 `<skill-root>/scripts/fetch_dingtalk_aitable.py`；不得因为当前工作目录不同而改成手工猜 DWS 参数。只有脚本不存在、无法执行或需要排查单个接口时，才进入下面的人工命令路径。

## 登录身份

本 skill 只调用当前运行环境 PATH 中的官方 `dws`，不携带、不识别也不修改任何产品或个人专属账号路由。宿主 Agent、项目规则或用户负责在调用 skill 前选择正确的 DWS 登录环境。

读取前执行 `dws auth status --format json`，把 `user_name`、`corp_name` 和 `user_id` 写入快照清单。身份与目标数据不符时停止，不自动重新登录或切换共享 profile。

## 读取顺序

1. 从用户 URL 解析可见的 Base、table、view 参数。
2. URL 没有完整 ID 时，按名称搜索 Base，并在多候选时让用户选择。
3. 使用 `+base-get` 获取 Base 目录及全部数据表，并验证目标 `tableId` 确实属于该 Base。
4. 对报告涉及的每张表读取字段详情。
5. 读取全量记录并保存原始 JSON；大表必须分页，不把第一页当全量。
6. 公式、关联、引用字段需要显式指定字段 ID，避免默认响应遗漏。
7. 需要打开钉钉原始记录时，批量获取真实分享链接。

推荐 shortcut：

```bash
dws aitable +base-get
dws aitable +list-tables
dws aitable +field-get
dws aitable +record-query
dws aitable +record-share-links
```

所有命令必须加 `--format json`。参数不确定时先执行：

```bash
dws schema --cli-path "aitable +record-query" --compact --format json
```

不要凭旧记忆拼 flag。

## 千问办公正确命令路径

内置脚本不可用时，只执行以下固定顺序：

```bash
# 1. 身份与组织
dws auth status --format json

# 2. Base 目录；不要先调用可能走另一权限链路的 table get
dws aitable +base-get \
  --base-id <baseId> --format json

# 3. 字段；只使用真实 tableId
dws aitable +field-get \
  --base-id <baseId> --table-id <tableId> --format json

# 4. 全量记录；每页上限固定为 100，CLI 自动翻页
dws aitable record query \
  --base-id <baseId> --table-id <tableId> \
  --limit 100 --all --page-limit 0 --format json

# 5. 取得真实 recordId 后再批量获取原始记录链接
dws aitable +record-share-links \
  --base <baseId> --table <tableId> \
  --record-ids <逗号分隔的真实recordId> \
  --view-id <viewId> --format json
```

禁止以下用法：

- `--max-page-size`：该 flag 不存在；
- `--limit 200`：单页范围只能是 1–100；
- `contains`：文本包含操作符是 `contain`；
- `table get --table-id`：需要精确查表时使用当前 Help 接受的 `--table-ids`，但报告抓取主路径优先 `+base-get`；
- 从视图 `columns` 直接当作字段目录：其中可能包含系统列或非字段节点，必须以 `field get` 返回的真实 `fieldId` 为准。

需要手工分页时，首次不传 `--cursor`，后续把响应中的 `nextCursor` 原样传给下一次查询。不得把第一页当作全量。

## 错误分类与对外表述

| 类别 | 判定 | 处理 | 对外表述 |
|---|---|---|---|
| `command_validation` | unknown flag、limit 超限、过滤操作符错误、必填参数缺失 | 读取 leaf Schema/Help，修正后最多重试一次 | “调用参数已修正”，不得说钉钉服务异常 |
| `authentication` | 登录态或 token 明确失效 | 停止，请用户完成登录 | “当前登录态无效” |
| `permission` | Base 目录、字段、记录和导出均一致返回无权限 | 停止，报告目标与当前身份 | “当前身份无读取权限” |
| `interface_identity_mismatch` | Base/视图/导出成功，但某个字段、记录或 table 接口返回 `ORG_DOC_TOKEN_MISMATCH` | 保留成功证据，尝试官方导出并记录 trace ID | “接口身份路由不一致”，不得说用户无权限 |
| `transient_service` | 返回明确 `retryable=true` 的 `SYSTEM_ERROR`、超时或限流 | 最多重试两次，约 2 秒、5 秒 | “结构化接口暂时异常” |
| `degraded_export` | 结构化读取失败，但官方导出成功 | 继续画像和内容蓝图；下钻降级需用户确认 | “数据已取得，但缺少真实 recordId/原始记录链接” |
| `failed` | 结构化读取和官方导出都失败 | 停止 | 才能称为“数据获取失败” |

同一次任务的错误报告必须列出：实际命令、错误类别、服务端 `trace_id`、是否可重试、已成功取得的内容，以及失败影响范围。禁止把不同性质的错误合并成一句“DWS 获取失败”。

## 数据快照

建议输出：

```text
snapshot/
├── manifest.json
├── fields-<tableId>.json
├── records-<tableId>.json
├── record-links-<tableId>.json
└── retrieval.json
```

`manifest.json` 至少包含：

- Base 名称与 ID；
- table/view 的名称和 ID；
- 每张表记录数；
- 抓取时间；
- 账号和组织；
- 是否完成全量分页；
- 是否取得记录分享链接。

## 表关系判断

优先使用字段配置中的关联和引用信息建立关系图。其次使用稳定业务键：工号、订单号、项目编号、客户 ID 等。禁止默认按姓名、公司简称或展示文本 JOIN。

如果两个表存在多个候选关联键，输出候选键的唯一率、空值率和匹配率，由用户确认后再计算跨表指标。

## 敏感信息

记录快照可能含人员履历、评价、手机号、邮箱或附件。遵守以下规则：

- 默认保存在任务受控目录；
- 不提交到 Git；
- 不放进公开 HTML；
- 外发版只保留必要聚合和脱敏记录；
- 不在聊天中粘贴全量敏感数据；
- 用户要求删除快照时，先确认精确路径再执行可恢复删除。

## 有限重试与降级顺序

1. 首选内置抓取脚本，由脚本按 `+base-get → +field-get → record query → record-share-links` 读取字段、全量记录、真实 `recordId` 和真实分享链接。
2. 只有系统错误、超时、限流等明确 `retryable=true` 的错误才重试；最多两次，间隔约 2 秒和 5 秒。禁止无限重试或长时间等待。错误文本中出现 `retryable=false` 时不得仅凭“retryable”这个单词误判为可重试。
3. 字段过多或关联字段遗漏时，使用显式字段 ID 和不超过 100 个字段的分片重读一次。
4. 结构化接口仍不可用时，调用官方 `dws aitable export data` 导出 Excel，或接受用户提供的 CSV/JSON/XLSX。
5. 导出成功代表数据已取得，可以继续汇总分析；但不代表保留了真实记录能力。记录 `data_access_status: retrieved_via_export`、`record_id_fidelity: missing`、`record_link_coverage: 0`，先生成内容蓝图并让用户确认是否接受本地下钻。

认证、对象不存在和明确参数错误不按服务重试。权限错误只有在所有读取路径一致失败时才能确认为权限问题；若 Base/视图/导出中任一路径成功，则按 `interface_identity_mismatch` 处理。

## 真实 ID 与能力清单

`manifest.json` 必须记录：

- `retrieval_status` 和 `source_format`；
- `record_id_fidelity`：只允许 `real` 或 `missing`；
- `record_id_coverage`；
- `record_link_coverage`；
- `original_record_drilldown`；
- `degradation_requires_user_approval`。

禁止把本地行号、Excel 序号或 `row001` 一类模拟值写成 `recordId`。本地稳定键只能命名为 `local_row_key`。

完整原始记录下钻要求真实 ID 与真实链接覆盖率均为 100%。分享链接取不到时可以生成本地详情，但必须明确降级并取得用户整体内容确认，不能把 Base 首页链接冒充单条记录。

## 其他失败处理

- 登录态不可用：报告当前返回的账号和组织，不把钥匙串沙箱错误直接当成 token 失效。
- Base 搜索多候选：列出名称和 ID，请用户选，不默认第一个。
- 记录量与分页总数不一致：停止生成指标，先补齐分页。
- 关联/公式字段缺失：用显式字段 ID 重读，不本地猜值。

---

## 文档溯源

### 生成提示词

```text
要打包成一个skill，而不是相互调用
好，开始执行吧
```

### 依赖文档

| 文档 | 用途 |
|---|---|
| `dingtalk-aitable/SKILL.md` | DWS AI 表格读取顺序、ID 与字段类型约束 |

### 生成信息

- **生成时间**：2026-08-14
- **生成工具**：Codex（GPT-5）
- **数据处理**：将只读盘点、分页、关联和记录分享链接能力整理为报告数据入口规范。
