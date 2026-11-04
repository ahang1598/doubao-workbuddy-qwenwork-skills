# 调用者身份字段

当前实现以 [正式遥测](formal-telemetry.md) 与 [Lite 遥测](../lite/references/telemetry.md) 为准。身份字段为可选 doubao_user_id、doubao_email、doubao_username（内部邮箱前缀）。宿主显式 UID/email 优先，其次只在内存解析宿主 Token 的 uid/email；格式不合法分别省略。

不读取 ByteCloud 身份，不调用用户信息接口，不输出或持久化 Token，不上报姓名、工号、部门或身份来源，不生成匿名标识。身份字段用于使用归因，不是权限验证。本次文档整理仅对齐已有实现，未增加字段或采集范围。
