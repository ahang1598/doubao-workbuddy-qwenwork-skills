# 解析任务执行与结果处理

## 云端解析流程

使用 [DTS-AI 认证 · 服务配置](dts-ai-authentication.md#服务配置) 中定义的地域与 API 版本：

`AuthorizeFileUpload` → OSS `PostObject` → `CreateDocParserJob` → `DescribeDocParserJobStatus` → `DescribeDocParserJobResult`

使用 `Bucket`、规范化后的 `Endpoint` 和 `ObjectKey` 构造上传对象 URL，并将其作为 `OssFileUrl` 传给 `CreateDocParserJob`；同时传入本地文件的基本名称、小写扩展名和 `OutputFormat=markdown`。不得以 `FileUrl` 替代 `OssFileUrl`；`FileUrl` 仅用于已可通过 HTTP 或 HTTPS 访问的文件。

`SecurityToken` 只能通过 OSS 表单字段 `x-oss-security-token` 发送。接受 OSS PostObject 状态 `200`、`201` 或 `204`。不得打印或持久化 API Key、临时 AccessKey、Security Token、Policy 或签名。

## 成功判定

仅当 HTTP 状态码为 `200`、`Success=true` 且 `HttpStatusCode=200` 时，才可判定请求成功。继续执行前还必须满足：

| 操作 | 必需结果 |
| --- | --- |
| `AuthorizeFileUpload` 响应 | `AccessKeyId`、`SecurityToken`、`Bucket`、`EncodedPolicy`、`Endpoint`、`ObjectKey`、`Signature` |
| 创建任务 | 非空 `JobId` |
| 查询状态 | 非空 `Status` |
| 查询结果 | 非空字符串 `Result` |

`Status` 只接受以下区分大小写的官方值：

| `Status` | 处理方式 |
| --- | --- |
| `init`、`pending`、`running` | 继续有界轮询 |
| `success` | 停止轮询并获取结果 |
| `failed` | 报告 `FailureMessage` 并停止 |
| `cancelled` | 报告任务已取消并停止 |

进度和错误报告必须保留服务端返回的原始 `Status`。遇到其他值（包括大小写不同的拼写）时必须报告原值并停止，不得将其映射为已知状态。

## 恢复记录

每当任务创建成功或结果保存成功时，均向当前用户主目录下的 `.aliyun-dts/doc-parse/jobs.jsonl` 追加一条不含密钥的记录。记录必须严格包含当前 v1 格式定义的字段：`schema_version=1`、时间、事件、JobId、输入名称、可用时的输入内容 SHA-256，以及输出路径。忽略格式错误或不符合该格式的记录。恢复记录写入失败不影响解析任务本身的结果。

上传前必须先计算输入内容 SHA-256 并检查恢复记录。如果相同内容已有已保存的解析结果，不得再次上传：省略 `--output` 时直接复用记录中的结果；用户指定新的输出路径时，将已有 Markdown 原子复制到该路径。指定路径已存在时停止，不得自动改名或覆盖。仅当用户明确要求重新解析时，才可使用 `--force`。

省略 `--output` 时，默认输出名为 `<input-name>.md`，其中 `<input-name>` 包含源扩展名，例如 `report.pdf.md`。如果该路径已被不同内容占用，使用 `<input-name>-<sha256-prefix>.md`，其中 `sha256-prefix` 为当前输入内容 SHA-256 的前 8 位。该名称必须稳定，不得使用 `(1)`、`-2` 等依赖执行顺序的编号。哈希兜底路径也已存在时停止并要求用户指定其他输出路径。用户显式指定 `--output` 时必须严格使用该路径，不得自动改名。

`jobs` 命令输出的每条本地记录包含 `state` 字段，取值与必需操作如下：

| `state` | 含义 | 必需操作 |
| --- | --- | --- |
| `saved` | 已保存解析结果至记录中的输出路径 | 直接复用该输出 |
| `pending` | 任务已创建，但本地未记录保存结果 | 使用 `resume <JobId>` 恢复 |

## 轮询与恢复

默认轮询间隔为 5 秒（取值必须大于 0），本地超时为 300 秒（取值必须大于 0）。长时间运行的命令约每 30 秒输出一次心跳。`parse` 与 `resume` 可用 `--poll-interval` 与 `--poll-timeout` 覆盖默认值。

| 退出码 | 含义 | 必需操作 |
| --- | --- | --- |
| `2` | 本地验证或环境失败 | 修正本地输入或配置 |
| `3` | API 或传输失败 | 报告返回的代码、消息和 RequestId |
| `4` | 本地超时，任务可恢复 | 使用输出的恢复命令或 JobId |
| `130` | 被中断 | 恢复同一任务；不得重新上传 |

退出码为 `4`、`130`，或结果保存失败时，保留 JobId 并使用 `resume`。获取结果时如返回错误或空结果，必须保持现有输出不变。

## 结果完整性

将解码后的 `Result` 字符串以 UTF-8 写入，不得增加、删除、重排或补写内容。仅在获得完整结果后执行原子写入。发现版式问题时，建议另行说明。
