# 正式版直播流程

仅在入口已选择正式版，或续办原正式任务时读取。固定线上 OpenAPI，使用随包独立运行时；不安装外部 CLI、不读取其他产品认证缓存。

1. 新建按 [项目与场景选择](product-boundary.md#项目与场景选择) 处理。inspect-entry 返回的完整 projects 直接复用，不重查；登录后尚无列表才查询一次。场景仍需核验本项目真实规则。
2. 按 [任务创建](task-create.md) 校验来源、dry-run，并创建一次。业务参数以对应脚本 Schema 为准；写入结果未知先只读核对。安装损坏停止，认证及业务失败按 [认证恢复](auth-recovery.md)，已有或未知任务不新建 Lite。
3. 创建时使用 dashboard_mode=remote，保存 environment/profile/account_id/project_name/task_id/scenario 及监控台地址，立即按 [直播任务打开远端操作台](doubao-delivery.md#直播任务打开远端操作台) 交付。
4. 当前 Agent 持续执行 [任务结束监听](task-completion-watch.md)，直接接续其 review_preparation，不重复 prepare。风险播报默认关闭，用户明确要求才启用 [Chat 风险播报](chat-delivery.md)，关闭播报不取消结束监听。
5. 终态后按 [报告交付](doubao-delivery.md#直播与视频质检远端报告) 先交付质检报告，再按 [内容复盘](ecommerce-review.md) 分析与 finalize，核验并交付复盘。缺 ASR、失败、超时与中断如实记录，不能把准备完成当复盘完成。

单次查询分别读 [任务详情](task-get.md)、[任务列表](task-list.md) 或 [报告](report-get.md)，不自动开启监听。结束请求读 [结束任务](task-end.md)。续办身份按 [原账号与任务绑定](auth-recovery.md#原账号与任务绑定)；不将登录成功当业务成功。
