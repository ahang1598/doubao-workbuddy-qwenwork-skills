# 交互文案

在发送输入引导、图片识别失败、兑换前确认或最终结果反馈前完整读取本文件。结构化工具字段决定事实；本文件只决定表达。

## 目录

- [输入引导](#输入引导)
- [兑换前确认](#兑换前确认)
- [PREPARE 未成功文案](#prepare-未成功文案)
- [PREPARE 工具异常文案](#prepare-工具异常文案)
- [REDEEM 成功文案](#redeem-成功文案)
- [REDEEM 其他结果文案](#redeem-其他结果文案)

## 输入引导

用户尚未提供兑换码或二维码图片时：

> 你好，我来帮你完成豆包订阅礼品卡兑换。请直接发送兑换码，或上传一张清晰的二维码图片。

用户只在消息文本中提供图片或二维码 URL、没有实际上传图片附件时：

> 为了安全处理二维码，请直接上传二维码图片，不要只发送图片链接；你也可以直接发送兑换码。

图片模糊、不是礼品卡二维码，或运行时无法取得可传给工具的图片链接时：

> 不好意思，暂时无法从这张图片中识别礼品卡二维码，请重新上传一张清晰、完整的二维码图片，或直接发送兑换码。

平台或工具明确返回客户端版本不支持兑换时：

> 当前豆包版本过低，请升级到最新版本后再尝试兑换。

## 兑换前确认

仅当 PREPARE 明确可兑换且 `packageLabel` 已生成时使用。

这是执行 REDEEM 前不可省略的知情确认。必须完整展示与当前 PREPARE 结果匹配的引用块，其中包含实际套餐、生效方式、目标账号和礼品卡兑换规则链接；发送后结束当前回复，等待用户在下一条消息中明确确认。用户在 PREPARE 前或提交兑换码、二维码图片时说过“直接兑换”“不用问”“自动兑换”或“确认兑换”，均不能替代本次询问，也不得删减规则链接。

`isPaidUser=false`：

> 当前兑换码为「<packageLabel>」，兑换视为同意【[豆包专业版礼品卡兑换规则](https://lf9-cdn-tos.draftstatic.com/obj/ies-hotsoon-draft/grace_legal/gift-card-rules.html)】，兑换后权益立即生效。
> 是否立刻为当前账号「<username>」兑换，确认的话回复我「确认兑换」就可以。

`isPaidUser=true`：

> 当前兑换码为「<packageLabel>」，兑换视为同意【[豆包专业版礼品卡兑换规则](https://lf9-cdn-tos.draftstatic.com/obj/ies-hotsoon-draft/grace_legal/gift-card-rules.html)】，兑换后权益立即生效，将与你现有的套餐额度叠加，按到期顺序消耗。
> 是否立刻为当前账号「<username>」兑换，确认的话回复我「确认兑换」就可以，如果不想和已有订阅叠加生效，你也可以晚些等已有订阅过期再进行兑换。

用实际 `packageLabel` 替换占位符。仅当运行时提供可信账号展示名时才替换 `<username>`；否则将“当前账号「<username>」”整体改为“当前登录账号”，不得编造用户名。

## PREPARE 未成功文案

`valid=false` 时优先使用 `unavailableReason`。在不改变事实的前提下，可统一为以下语气：

- 当前兑换码无效，请确认输入是否有误。
- 最近尝试次数较多，请稍后再试。
- 该礼品卡已经兑换。
- 该礼品卡已过期。

不要根据旧接口数字 `result` 自行映射。

## PREPARE 工具异常文案

按工具返回契约决定后续动作，优先保留工具提供的安全、可行动信息。通用说明为：“礼品卡信息暂时无法查询，请稍后再试。”不得宣称兑换码有效或无效，不向用户展示内部错误类型或错误码。

## REDEEM 成功文案

`redemptionData.status="SUCCEEDED"` 时，先根据当前运行环境选择 `quotaManagementUrl`：

- 运行环境明确表明当前是 Mobile 端时，使用以下端内跳转链接：

  ```text
  sslocal://lynxview?url=https%3A%2F%2Flf-doubao-sourcecdn-tos.bytegecko.com%2Fobj%2Fbyte-gurd-source%2F11517%2Fgecko%2Fresource%2Fflow_lynx_doubao_member_template%2Ftemplate%2Fquota-management%2Ftemplate.js%3Fgecko_channel%3Dflow_lynx_doubao_member_template%26gecko_bundle%3Dtemplate%2Fquota-management%2Ftemplate.js&loader_name=forest&enable_code_cache=1&should_full_screen=1&use_anniex=1&hide_nav_bar=1&enable_lynx_generic_fetcher=1&enable_prefetch=1&need_login_strict_mode=1&need_intercept_in_minor_mode=1&bdhm_bid=flow_lynx_monorepo&bdhm_pid=subs_quota_management&enter_method={ORIGIN}
  ```

- 运行环境明确表明当前是 Web 或 PC 端时，使用以下 HTTPS 链接：

  ```text
  https://www.doubao.com/member/quota-management?enter_method={ORIGIN}&need_login_strict_mode=1&need_intercept_in_minor_mode=1
  ```

- 无法从运行环境可靠确定端类型时，兜底使用上述 HTTPS 链接。不要仅根据用户措辞、二维码来源或链接形式猜测端类型。

用 PREPARE 阶段保存的 `packageLabel` 和选定的 `quotaManagementUrl` 替换占位符，并严格按照下面引用块的内容结构返回，不得改写、缩写或增删句子，也不得将占位符原样输出：

> 恭喜你已完成「<packageLabel>」兑换，具体订阅/额度信息可以查看【[订阅与额度管理](<quotaManagementUrl>)】，去畅快使用豆包的 AI 能力吧～

如果 `packageLabel` 未在 PREPARE 阶段成功生成，则返回结构不完整，不得猜测套餐名或周期，也不得套用上述成功文案；应说明兑换成功但套餐信息暂时无法确认。

## REDEEM 其他结果文案

明确的业务未成功状态优先使用 `redemptionData.suggestedMessage`。在不改变事实的前提下，可统一为：

- 当前兑换码不可用。
- 今日已达到兑换上限，请明日再试。
- 最近尝试次数较多，请稍后再试。
- 本次兑换需要人工审核，请稍后查看或联系客服。
- 兑换失败，请稍后再试。
- 该礼品卡已经兑换，无需重复兑换。

明确仍在处理中时：

> 兑换正在处理中，请稍后查看订阅状态。

结果未知或结果结构不完整时，统一说明：“礼品卡兑换结果暂时无法确认，请不要重复提交兑换。请稍后查看会员状态，或按工具建议处理。”不要展示内部错误类型、错误码、token、内部异常、调用链或完整响应 JSON。
