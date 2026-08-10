# `content` 与 `errorMsg` 路由表

每次调用统一工具后完整读取本表。先合并 `content` 中所有文本为 `visibleText`；匹配时忽略首尾空白和不影响语义的标点差异，但不得仅凭近义猜测新增路由。

本表中的大写标签只是 Skill 内部路由名，不代表模型读取到了隐藏的 `statusCode` 或 `errorType`。

## 判定优先级

1. `errorMsg` 非空，或命中错误锚点：错误路由优先。
2. `errorMsg` 为空且只命中一个成功锚点：成功路由。
3. 同时命中互斥成功路由、成功与错误冲突、完全未命中：响应无法识别，重查一次后停止。

## 成功锚点

| 内部路由 | 必须出现的稳定片段 | 补充校验 |
|---|---|---|
| `PLATFORM_NOT_SUPPORTED` | `该平台暂不支持` | content 仅输出文本提示，告知用户当前平台不支持、需切换至 PC 端后重试；不附带按钮、二维码或 quickReplies，requiredUserAction 为 NONE |
| `DOUYIN_BIND_REQUIRED` | `当前账号尚未绑定抖音账号` | content 可包含"去绑定抖音账号"按钮指引，按 stage-reminders 固定文案告知用户 |
| `STUDENT_AUTH_REQUIRED` | `抖音账号已绑定` 且 `尚未完成学生认证` | content 文本中必须包含形如 `https://aka.doubaocdn.com/...` 的二维码图片链接；该链接由模型以 markdown 图片形式渲染展示 |
| `STUDENT_AUTH_PENDING` | `学生认证结果仍在处理中` | 不展示旧二维码或旧二维码链接，等待后重查 |
| `BENEFIT_GRANT_PENDING` | `学生优惠权益正在发放中` | 不宣称到账 |
| `STUDENT_NOT_ELIGIBLE` | `已完成学生身份核验` 且 `不符合本次优惠活动` | 终态 |
| `BENEFIT_GRANTED` | `学生身份已验证` 且 `学生优惠权益已成功下发` | 终态 |
| `BENEFIT_ALREADY_GRANTED` | (`已经领取过学生优惠权益` 或 `已领取学生优惠权益`) **且** `无需重复申请` | 终态；运算符优先级显式固定为 (A∨B)∧C |
| `BENEFIT_RECEIVED_BY_OTHER_ACCOUNT` | `学生身份已在其他账号领取过` | 终态；不得要求用户重新认证或重新绑定 |
| `ACTIVITY_EXPIRED` | `本次学生优惠活动已结束` | 终态；不推测新活动时间 |
| `ACTIVITY_NOT_STARTED` | `本次学生优惠活动尚未开始` | 终态；不推测开始时间 |

## 已知错误锚点

| 内部错误路由 | `content` 或 `errorMsg` 稳定片段 | 重试 | 降级秒数 | 固定文案类别 |
|---|---|---:|---:|---|
| `RUNTIME_CONTEXT_MISSING` | `运行时身份上下文不完整` 或 `运行时身份上下文缺少必要字段` | 否 | — | 运行时身份缺失 |
| `DOUYIN_BIND_QUERY_FAILED` | `抖音账号绑定状态` 与 `查询失败`，或 `当前绑定状态未知` | 是 | 5 | 查询失败；失败阶段填"抖音账号绑定状态查询" |
| `STUDENT_AUTH_QUERY_FAILED` | `学生认证状态` 与 `查询失败`，或 `当前认证状态未知` | 是 | 5 | 查询失败；失败阶段填"学生认证状态查询" |
| `STUDENT_AUTH_QR_CREATE_FAILED` | `未能生成可用的认证二维码`，或 `认证二维码暂时生成失败` | 是 | 3 | 学生认证二维码生成失败 |
| `BENEFIT_GRANT_FAILED` | `未能确认学生优惠权益发放成功`，或 `权益下发服务暂时不可用`，或 `未确认权益发放成功` | 是 | 5 | 查询失败；失败阶段填"学生优惠权益下发" |
| `DEFAULT` | `学生优惠申请状态暂时无法确认`，或未匹配上述任何锚点的非空 errorMsg | 是 | 1 | 响应不完整 |

`content` 中明确出现"等待/稍候 N 秒"时优先使用可见数字；否则使用表中降级秒数。所有可重试错误合计最多自动重试一次。

## 二维码链接

`STUDENT_AUTH_REQUIRED` 路由时，`content` 文本中会给出认证二维码图片链接（形如 `` `https://aka.doubaocdn.com/s/xxxx` `` 或类似 CDN URL）。模型须：

1. 从文本中提取该 URL（在反引号或正文中）；
2. 在回复末尾以 markdown 图片格式展示：`![学生认证二维码](<URL>)`；
3. 不缓存、不复用、不猜测上一轮返回的旧链接；
4. 其他路由即使文本中出现图片链接也不要展示二维码，视为响应冲突重查一次。
