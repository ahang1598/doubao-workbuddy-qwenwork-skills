# `student_discount_run_application_step` 模型可见契约

## 职责

工具从运行时读取当前用户 UID，每次重新查询权益、抖音绑定和学生认证状态；必要时生成绑定交互或学生认证二维码，并在条件满足时幂等下发权益。Skill 始终以空对象调用：

```json
{}
```

不要传 UID 或任何业务字段。一般优惠咨询不调用工具。

## 当前模型可见返回面

当前模型运行时只能读取：

- `content`：包含模型提示文本；需要学生认证时文本中会给出认证二维码图片链接（CDN URL，通常以反引号包裹）；
- `errorMsg`：工具执行错误信息，成功时为空或无错误内容。

适配层仅向模型暴露 `content` 和 `errorMsg`，其他字段不进入模型上下文。

以下字段模型不可读取，Skill 不得依赖：

- `structuredContent` 及其中全部业务字段；
- `isError`；
- `errorCode`、`errorType`、`errorStage`、`retryable`、`retryAfterSec`、`suggestedFix`；
- `statusCode`、`requiredUserAction`、`nextCheckAfterSec`、权益对象和二维码失效时间。

[工具 Schema](tool-schema.json)只描述工具提供方的完整定义，不能作为当前模型运行时的可见输入。

## 判定顺序

1. 合并 `content` 中所有非空文本为 `visibleText`。
2. `errorMsg` 非空时优先判定为工具错误。
3. 无论 `errorMsg` 是否为空，文本命中[内容路由表](content-routing.md)中的明确错误锚点时都进入错误路由。
4. 仅当 `errorMsg` 为空且文本只命中一个成功锚点时进入成功路由。
5. 未命中、命中多个互斥路由或 `STUDENT_AUTH_REQUIRED` 缺少二维码 URL 时，用 `{}` 重查一次；仍异常则停止。

业务上的待绑定、待认证、处理中、不符合条件、已领取和已发放都是成功业务状态。工具依赖失败、环境缺失和未识别状态属于错误。

## 可见数据边界

- 等待秒数：只读取 `content` 明确出现的数字；两个业务 pending 状态未显示数字时使用 Skill 本地 5 秒降级值。
- 二维码：从 `content` 文本中提取 CDN 图片链接（形如 `` `https://aka.doubaocdn.com/s/xxxx` ``），以 markdown 图片格式 `![学生认证二维码](<URL>)` 展示；不缓存旧链接，不猜测 Base64 或其他图片地址，不读取 quickReplies 中的 deep link。
- 权益：只使用 `content` 明确出现的名称；没有正式名称时仅称“学生优惠权益”。不可见的有效期一律省略。
- `errorMsg`：不原样展示给用户，仅用于错误判定和锚点匹配。

## 重试边界

- 同一轮业务等待、无法识别响应和工具错误自动重查合计最多一次。
- 只有内容路由表明确标记为可重试的错误才自动重试。
- UID 上下文缺失及无法匹配的非空 `errorMsg` 不自动重试。
- 学信网子流程结束后的强制续调不是自动重试，不计入一次额度；学信网后响应冲突可独立再重查一次（详见 SKILL.md「等待秒数与重试额度」段）。

---

## 附录：errorCode → 可见锚点排障映射表（仅供排障，Skill 不读取）

> Skill 运行时**不读取 hidden 的 errorCode**，仅按 `content + errorMsg` 的稳定锚点路由；本表用于工具侧排障时，把观察到的 errorCode 快速对齐到「Skill 实际会命中哪条路由」。若出现 errorCode 对应的文本锚点与 Skill 路由不一致，先改工具侧的 content/errorMsg 文案锚点，不要改 Skill。

| errorCode | 名称/含义（schema 定义） | errorStage | 模型可见的锚点对齐 | Skill 预期路由 |
|---:|---|---|---|---|
| 0 | 成功获得业务状态 | null | content 出现 10 种成功状态之一，errorMsg 为空；isError=false | DOUYIN_BIND_REQUIRED / STUDENT_AUTH_REQUIRED / STUDENT_AUTH_PENDING / BENEFIT_GRANT_PENDING / STUDENT_NOT_ELIGIBLE / BENEFIT_GRANTED / BENEFIT_ALREADY_GRANTED / BENEFIT_RECEIVED_BY_OTHER_ACCOUNT / ACTIVITY_EXPIRED / ACTIVITY_NOT_STARTED |
| 40001 | 运行时身份上下文缺失 RUNTIME_CONTEXT_MISSING | REQUEST_CONTEXT | errorMsg 或 content 含「运行时身份上下文」+「不完整/缺少必要字段」 | RUNTIME_CONTEXT_MISSING（不重试；不索要 UID/TenantID/BizID） |
| 51001 | 绑定状态查询失败 DOUYIN_BIND_QUERY_FAILED | DOUYIN_BINDING | errorMsg 或 content 命中「绑定状态」+「查询失败」/「当前绑定状态未知」 | DOUYIN_BIND_QUERY_FAILED（5 秒重试一次） |
| 51002 | 学生认证查询失败 STUDENT_AUTH_QUERY_FAILED | STUDENT_AUTH | errorMsg 或 content 命中「认证状态」+「查询失败」/「当前认证状态未知」 | STUDENT_AUTH_QUERY_FAILED（5 秒重试一次；不展示旧二维码） |
| 51003 | 二维码生成失败 STUDENT_AUTH_QR_CREATE_FAILED | STUDENT_AUTH | errorMsg 或 content 命中「未能生成可用的认证二维码」/「认证二维码暂时生成失败」 | STUDENT_AUTH_QR_CREATE_FAILED（3 秒重试一次；不展示旧二维码） |
| 51004 | 权益下发失败 BENEFIT_GRANT_FAILED | BENEFIT_GRANT | errorMsg 或 content 命中「未能确认权益发放成功」/「权益下发服务暂时不可用」/「未确认权益发放成功」 | BENEFIT_GRANT_FAILED（5 秒重试一次；不要求重新认证） |

排障检查点：
1. 若某 errorCode 下 content/errorMsg 文案改动，**必须同步更新 content-routing.md 对应锚点或本表**，否则会出现「工具认为返回了某业务码但 Skill 路由到 DEFAULT/未知错误」的错位。
2. 未在本表中列出的非空 errorMsg（适配层异常、网络层错误等）统一走 DEFAULT 路由：1 秒重试一次，仍失败则用"响应不完整"固定文案停止。
