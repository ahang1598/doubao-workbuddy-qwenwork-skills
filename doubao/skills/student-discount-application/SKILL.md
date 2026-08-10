---
name: student-discount-application
description: 仅当用户明确提出豆包专业版学生优惠办理类诉求，方可加载本 Skill 并调用student_discount_run_application_step依次执行全流程；若用户仅咨询学生优惠资讯、咨询其他优惠、诉求模糊无法判定、未提出办理申请，一律禁止加载 Skill 与调用该工具，严格区分目标权益，杜绝一切误触发。
---

# 学生优惠申请

仅调用 `student_discount_run_application_step` 查询并幂等推进当前登录用户的申请。模型运行时只能读取工具返回的 `content` 和 `errorMsg`；其他字段（包括 `structuredContent`、`isError`、`statusCode`、`errorType` 等）不可见，不用于校验或路由。

每次工具返回后先完整读取[内容路由表](references/content-routing.md)；需要理解模型可见返回面时读取[工具契约](references/tool-contract.md)；[工具 Schema](references/tool-schema.json)仅供工具实现和排障参考，不用于运行时路由；生成用户回复时读取[阶段提醒文案](references/stage-reminders.md)，严格以模型可见的 `content` 和 `errorMsg` 填充固定文案；命中 `STUDENT_AUTH_REQUIRED` 路由时，同时读取[学生认证交互](references/student-auth-workflow.md)和[学信网当前有效学籍核验](references/chsi-enrollment-verification.md)。

## 随附参考文件定位

学信网子流程文件固定路径为 `references/chsi-enrollment-verification.md`，位于 `references/` 目录下。直接读取该路径；不将该文件作为独立 Skill。

## 强制边界

1. 只调用 `student_discount_run_application_step` 作为学生优惠业务工具。仅在命中 `STUDENT_AUTH_REQUIRED` 且当前办理历史尚未执行过学信网流程时，额外执行一次内嵌的[学信网当前有效学籍核验](references/chsi-enrollment-verification.md)。
2. 始终以空对象 `{}` 调用，不传 UID、认证结果、流程状态、租户、会话或鉴权信息。
3. 不向用户询问 UID。UID 和幂等键由运行时注入。
4. 不读取、等待或假设 `structuredContent`、`isError`、`statusCode`、`errorType`、`errorStage`、`retryable`、`retryAfterSec`、`suggestedFix`、权益对象、quickReplies、deep link 或二维码失效时间可见。
5. 只按 `content` 中的稳定锚点生成内部路由标签；`errorMsg` 非空时优先进入错误分支。不要用自由语义推断补造一个未命中的业务状态。
6. 不推测或重建客户端绑定交互 deep link、二维码 URL 以外的图片地址、Base64 图片、权益正式名称或有效期。
7. 不收集、输入或复述账号、密码、短信验证码、身份证号、人脸信息等认证数据。
8. 未命中 `BENEFIT_GRANTED` 或 `BENEFIT_ALREADY_GRANTED` 前，不宣称权益领取成功。
9. 学信网流程每个用户发起的办理周期最多执行一次；无论结果如何都必须在 `finally` 中再次以 `{}` 调用统一工具，并先展示一次学信网结果，再展示新工具结果对应的阶段文案。

## 执行流程

1. 确认用户意图是开始申请、继续办理或查询申请状态。
2. 以 `{}` 调用 `student_discount_run_application_step`。
3. 读取 `errorMsg`；将 `content` 中所有非空文本合并为 `visibleText`。
4. 按[内容路由表](references/content-routing.md)分类：
   - `errorMsg` 非空，或 `visibleText` 命中错误锚点：进入错误路由；
   - `errorMsg` 为空且 `visibleText` 只命中一个成功锚点：进入对应成功路由；
   - 未命中、同时命中多个互斥路由，或 `STUDENT_AUTH_REQUIRED` 但文本中缺少二维码 URL：以 `{}` 重查一次；仍无法识别则停止。
5. 按[阶段提醒文案](references/stage-reminders.md)输出当前路由的固定文案。不要把工具的模型提示文本或 `errorMsg` 原样转发给用户。
6. 命中 `STUDENT_AUTH_REQUIRED` 时，按"学信网子流程"决定先执行学信网还是从文本中提取二维码链接并展示。
7. 用户完成外部绑定或认证操作后，再以 `{}` 调用工具确认最新状态。

## 模型可见响应校验

响应校验只检查以下三项：

- `content` 可读，且至少包含一段非空文本；
- `errorMsg` 可读；成功时为空，错误时通常非空；
- `STUDENT_AUTH_REQUIRED` 路由在需要展示二维码时，`content` 文本中必须包含形如 `https://aka.doubaocdn.com/...` 的二维码图片链接（通常以反引号包裹）。

不依赖客户端绑定控件、结构化状态、错误码、权益对象、quickReplies 或二维码失效时间判断响应完整性。

若 `errorMsg` 非空，即使文本同时出现成功措辞也按错误处理，不宣称成功。若 `errorMsg` 为空但文本命中明确错误锚点，也按错误处理。重查一次后仍缺少文本、仍路由冲突或二维码链接缺失时，使用阶段提醒文案中的"响应不完整"并停止。

## 成功状态路由

下表中的标签是 Skill 根据文本锚点生成的内部标签，不是从隐藏字段读取的值。

| 内部路由 | `content` 稳定语义 | 编排动作 |
|---|---|---|
| `PLATFORM_NOT_SUPPORTED` | 该平台暂不支持 | 告知用户当前平台不支持、需切换至 PC 端，本次流程结束 |
| `DOUYIN_BIND_REQUIRED` | 当前账号尚未绑定抖音账号 | 提醒完成绑定，等待用户返回 |
| `STUDENT_AUTH_REQUIRED` | 抖音账号已绑定，但尚未完成学生认证 | 首次先执行学信网子流程；之后从文本提取二维码链接并以 markdown 图片展示 |
| `STUDENT_AUTH_PENDING` | 学生认证结果仍在处理中 | 不展示旧二维码链接，等待后最多重查一次 |
| `BENEFIT_GRANT_PENDING` | 学生优惠权益正在发放中 | 不要求重新认证，等待后最多重查一次 |
| `STUDENT_NOT_ELIGIBLE` | 已完成学生身份核验但不符合活动条件 | 如实告知并结束 |
| `BENEFIT_GRANTED` | 学生身份已验证且权益已成功下发 | 告知领取成功并结束 |
| `BENEFIT_ALREADY_GRANTED` | 当前账号已经领取过学生优惠权益且无需重复申请 | 告知已领取并结束 |
| `BENEFIT_RECEIVED_BY_OTHER_ACCOUNT` | 学生身份已在其他账号领取过 | 如实告知，不要求重新认证或重新绑定，结束 |
| `ACTIVITY_EXPIRED` | 本次学生优惠活动已结束 | 告知活动已结束，不推测新活动时间，结束 |
| `ACTIVITY_NOT_STARTED` | 本次学生优惠活动尚未开始 | 告知活动未开始，不推测开始时间，结束 |

### 等待秒数与重试额度

- 先从 `visibleText` 中读取明确出现的"等待/稍候 N 秒"。仅 `STUDENT_AUTH_PENDING` 或 `BENEFIT_GRANT_PENDING` 未显示数字时，使用 5 秒作为 Skill 本地重查间隔，并在固定文案中填写"约 5 秒"；这不是服务端建议时间。
- 常规自动重查额度：同一轮因业务等待、响应无法识别或工具错误自动重查合计最多 **1 次**。
- 学信网子流程独立额度：学信网流程结束后的 `finally` 强制续调 **1 次**，以及该续调结果因路由冲突/响应不完整再重查 **1 次**，这 2 次与常规额度相互独立，不计入常规 1 次限额。学信网后若仍需重查，才开始消耗常规额度。

### 权益信息固定文案与降级

- `BENEFIT_GRANTED`：固定庆祝文案 + 2.5 倍额度说明 + 38 元专业版付费引导链接（详见 stage-reminders.md）；
- `BENEFIT_ALREADY_GRANTED`：文案中的占位符按以下规则替换：
  - `{benefitName}`：`content` 中明确出现的权益名称；若只有泛称，使用"学生优惠权益"，不要声称这是正式权益名；
  - `{validFrom}` / `{validUntil}`：仅当 `content` 明确同时出现生效和失效时间时才保留；两端时间有任意一端不可见时，省略固定文案中整句"有效期：… 至 …"。不要猜测日期。

注：占位符命名与工具 schema 字段名保持一致，但替换只基于 `content` 可见文本，不依赖隐藏的 structuredContent。

## 学信网子流程（摘要，权威实现见 student-auth-workflow.md）

仅当内部路由为 `STUDENT_AUTH_REQUIRED` 且当前办理历史没有启动过学信网核验时执行一次。以下是高层骨架；**用户交互细节、首次/非首次判定、输出顺序、finally 强制续调、错误分支下的学信网结果展示顺序，全部以 [学生认证交互](references/student-auth-workflow.md) 为权威实现规范**。

骨架：

1. 直接读取[学信网当前有效学籍核验](references/chsi-enrollment-verification.md)。
2. 启动前标记本次办理已执行过学信网流程，不展示或缓存本次旧二维码链接。
3. 完整执行一次核验并将结果归一为 `NO_RESULT` / `VALID_RESULT` / `INVALID_RESULT`。
4. 不把学信网结果、学生 ID、验证码、报告编号或流程状态写入统一工具参数。
5. 无论子流程成功/失败/取消/中断/无结果，都在 `finally` 中以 `{}` 再调统一工具。
6. 对新响应重新执行 `content + errorMsg` 路由；**无论新路由进入成功还是错误分支，都必须先展示一次学信网结果文案，再展示新阶段或错误固定文案**（学信网结果不允许因后续工具错误被省略）。
7. 不因学信网结果为 `false` 或 `unknown` 直接得出活动资格结论；同一办理周期内决不重复执行学信网核验。

```text
if route == STUDENT_AUTH_REQUIRED:
  if 当前办理历史中没有执行过学信网流程:
    标记为已执行；不展示当前旧二维码链接
    try:   chsiOutcome = 执行一次学信网当前有效学籍核验并归一结果
    finally:  nextResult = student_discount_run_application_step({})
    nextRoute = 按 nextResult.content 和 nextResult.errorMsg 重新分类
    # 强制输出顺序：学信网结果 → 新阶段/错误文案 → （若仍需二维码）新二维码链接
    先展示 chsiOutcome；再展示 nextRoute 的固定阶段文案或错误文案
    if nextRoute == STUDENT_AUTH_REQUIRED:
      从 nextResult.content 文本中提取二维码URL
      最后以 markdown 图片格式展示：![学生认证二维码](<URL>)
  else:
    从当前 content 文本中提取二维码URL
    展示固定阶段文案 + markdown图片；等待用户完成认证
```

## 交互素材

- `DOUYIN_BIND_REQUIRED`：绑定交互由客户端处理。若 `content` 明确给出按钮文案（如"去绑定抖音账号"），可在固定文案中引用该按钮名称；不要猜测或编造其他按钮名、链接或 deep link。
- `STUDENT_AUTH_REQUIRED`：从 `content` 文本中提取二维码图片 URL（工具通常以反引号包裹 CDN 链接），在阶段文案后以 markdown 图片格式 `![学生认证二维码](<URL>)` 展示；不缓存或复用旧链接，不把链接直接展示给用户，不读取 quickReplies 中的 action schema。
- 无可见失效时间时不要自行判断二维码是否过期；用户反馈失效或链接不可用时，重新调用工具获取最新内容。

## 错误与重试

1. 先按[内容路由表](references/content-routing.md)匹配错误。不要依赖不可见的错误码、错误类型或重试字段。
2. `errorMsg` 只用于确认工具执行失败和辅助匹配，不原样展示给用户。
3. 只有匹配到明确允许重试的错误路由时，按 `content` 中可见秒数等待后以 `{}` 自动重试一次；没有可见秒数时使用路由表中的固定降级秒数。
4. UID 上下文缺失：停止且不重试，不向用户索要 UID 或其他内部身份标识。
5. 抖音绑定状态查询失败：不要展示绑定入口，不猜测绑定状态。
6. 学生认证查询失败：不要表述为用户认证失败，不要求重新认证或重复扫码。
7. 二维码生成失败：不要展示旧二维码链接，不猜测或编造图片地址。
8. 权益发放失败：学生认证已经完成，但权益未确认到账；不要要求重新认证，也不要宣称领取成功。
9. 未匹配到已知错误锚点的非空 `errorMsg`：走 DEFAULT 路由，使用"响应不完整"固定文案，1 秒自动重试一次；重试仍失败则停止。
10. 不展示堆栈、内部主机名、凭据、UID、trace ID、上游原始报文或完整 PII。
11. **兜底降级**：自动重试一次后仍失败（含二维码生成失败、查询失败、响应不完整），或用户明确表达挫败/无法继续（如"失败了""不行""搞不定""还是不行""扫码没用"），按[阶段提醒文案](references/stage-reminders.md)中的"兜底降级：手动认证入口"给出固定链接，结束本轮流程。正常流程中不主动推送该链接。

## 结束条件

只在以下情况结束：

- `BENEFIT_GRANTED`；
- `BENEFIT_ALREADY_GRANTED`；
- `BENEFIT_RECEIVED_BY_OTHER_ACCOUNT`；
- `STUDENT_NOT_ELIGIBLE`；
- `ACTIVITY_EXPIRED`；
- `ACTIVITY_NOT_STARTED`；
- UID 上下文缺失（不可重试）；
- 自动重试一次后仍失败或响应无法识别。

学生认证完成本身不是申请完成；必须继续确认权益状态。
