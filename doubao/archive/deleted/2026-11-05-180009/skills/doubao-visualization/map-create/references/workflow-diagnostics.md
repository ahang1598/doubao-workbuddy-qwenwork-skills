# 离线预检与维护诊断

普通生成和正式交付只调用 create-map；本页的预检只用于输入修复诊断，其他分阶段命令只用于维护。

```bash
node "$SKILL_DIR/scripts/preflight-map.mjs" --spec canonical-map-spec.json --plan presentation-plan.json --report build/preflight-report.json
```

预检独立汇总两份 schema 和 AMap 坐标准备诊断。满足输入前置条件后执行完整离线编译以检查引用、分析绑定和组件配置；编译未完成时后续依赖检查没有通过证据，报告保留首个阻断阶段的诊断，不声称全部语义均已检查。不能把 WGS84 仅改名为 GCJ-02。

预检不写工作流历史或 Graph/HTML，不消耗或重置修复预算，deliveryEligible 永远为 false。预检通过不能解锁耗尽的发布预算，更不能代替静态验收和 startup 启动检查；上限后需要维护者审查诊断，不提供普通模型自行重置的参数。

workflow-report.repairBudget 分别累计 input=20、acceptance=10、resource=10 次失败，成功阶段不占失败次数。pending 恢复只累计活动耗时；限流拒绝不再增加计数。同输入同源两次失败阻断再次执行；修改输入不会清空阶段预算。旧失败报告按原 attempt 保守迁入对应阶段，不按升级清零。

维护者可独立调用 check-html 的 smoke/affected/full、write-trace 和 emit-doubao-renderer 定位各层；不能用这些命令替代普通任务的完整发布门禁。最终交付原文由工作流在 HTML 发布成功后保存，失败或 local 状态不能使用旧 delivery 文件。
