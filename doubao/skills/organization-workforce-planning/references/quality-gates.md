# Quality Gates

## Hard Gate

- Route：组织单元/能力/HC/成本联合任务才进入本 Skill。
- Evidence：HC、成本、组织状态和审批 Claim 可追溯；冲突未被静默覆盖。
- Capability：每个结论槽位独立 allowed/missing/blocked。
- Calculation：期末 HC 等于 baseline 加 delta；成本含单位、期间、币种和公式；unknown 未补默认值。
- Scenario：至少一个情景才能 ready；validator 从 `role_deltas` 独立重算 HC、经常性成本、一次性成本和流量桥，不信任已写入汇总值。
- Reconciliation：研发统计口径、正式/外包、共享/专岗和专业-周分别守恒；不可替代对象的闲余不得跨对象抵扣缺口。
- Cost degradation：成本字段缺失只阻断对应成本槽，HC 继续计算；不得为了运行工具填写 0、虚构币种或期间。
- Permission：无自动裁员、调线、批预算或招聘执行。
- Artifact：六态一致，full/compact 关键状态、计数与哈希一致。
- Finalizer：空 claims、空替换、无来源对象或会破坏主工件完整性的更新均失败关闭；未触达核心槽保持原值，完成后重新验证。
- Completeness：`full_package` 必为 full；degraded 仍含能力—工作量—岗位依赖骨架、情景支持选项、HC 流量桥、条件迁移门和最大反方。
- Unknown：能力地图、工作量、结构基线、HC 流量拆分缺失时，unknowns 与 compact core_slots 均非空且逐项写明影响。
- HC bridge：净增量不能冒充招聘；缺招聘/离职/调入/调出任一分项时桥保持不完整。
- Hash：full 与 compact 指向完整 plan pack；full SHA256 和 compact payload SHA256 均可独立复算。

## 失败条件

套用固定 span/层级/团队规模、占用率、面积效率、缓冲比例或岗位配比；把净增量写成招聘人数；缺结构基线仍发明汇报线；以缺输入为由删除结构选项、迁移门或最大反方；无法守恒仍排名；跨专业抵扣资源缺口；把未批准外部上限当可用产能；相关性写成因果；个体风险或绩效推断；Finalizer 新增或清空阈值、对象、数字和核心槽；承诺工件不存在。

## 隐私与 Token

默认聚合，移除姓名、联系方式、证件、健康和受保护属性。小样本阈值必须由用户或组织政策提供；低于阈值的指标置空并注明抑制原因，不能自设固定人数阈值。先保留结论、Hard Gate、情景桥、反方、unknown、局限和工件索引，再压缩结构图和扩展说明。

## 用户可见正文

- 评测关键词只扫描最终用户正文；full/compact 的字段、哈希与 schema 走结构校验，不能与正文关键词混扫。
- 正文不得出现 Skill 文件、脚本路径、工具报错、解压/读取过程或多个相互冲突的中间版本。
- 简单算术题允许不调用引擎；复杂题必须在正文给完整主表，外部文档不能替代核心交付。
