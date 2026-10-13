---
name: doubao-coding-analyze-codebase
description: "通过只读调查建立可核验的代码库心智模型，回答入口与调用链、数据流、状态变化、运行时装配、外部副作用和模块责任。用于仓库导览、流程追踪、影响分析、实现定位和架构理解。不用于根因诊断、代码审查、未来方案设计或性能优化。组合任务只闭合“现状如何”的部分。"
---

# 代码库分析：效果主张隔离版

默认只读。答案必须自包含；不修改仓库，不把调查过程、伪代码或未来测试当作当前事实。

## SCOPE → ROUTE → EFFECT → BREAK → SHIP

### 1. SCOPE：锁定身份和证据等级

先记录 `revision/worktree | 用户点名对象的 literal path:symbol:line | 已读/未读范围`。点名对象不可读或不存在时交付 `PARTIAL/BLOCKED`，不得用相似对象代答。

每个 current-fact 先登记：`stage | locator | observed branch/callee | claim scope | confirmed/inferred/unknown`。源码、配置和可复核运行 artifact 只证明其直接表达的内容；issue、fixture、README、注释、目录名、未提交 diff 和相邻实现只能作为候选。完整规则见[主张账本](references/claim-ledger.md)。

### 2. ROUTE：追到可观察边界

流程题必须闭合 `trigger → runtime selection/wiring → transform/state → boundary → observable result`。继续读取真实 callee，直到成功效果、失败返回或明确的仓外边界；枚举 pass-through、conditional、no-op、partial-success、error-swallowed 分支。结构题和存在性题不强套流程，但要写搜索边界。按需读取[证据图与状态机](references/evidence-graph.md)和[仓库边界与追踪](references/repository-tracing.md)。

### 3. EFFECT：强制隔离跨组件效果主张

草稿里一旦准备使用“当前已启用、自动、保证、最终一致、重试、重放、补偿、回滚、不影响、客户端会修复”等效果词，先停止正文，为该主张填写并在最终答案显示一张紧凑的**责任闭合卡**：

`对象/范围 | 触发者 | 当前装配/选择/开关 | 实际执行者 | 成功副作用与观察点 | 失败是否返回且被检查 | 重试/重放来源 | 不能覆盖的对象 | status`

每格都要有 literal locator 或版本化外部契约。任一格缺证据，整条效果主张只能写成 `conditional`、`inferred` 或 `unknown`，禁止换同义词绕过。只对跨函数、跨模块、跨进程或带效果量词的结论使用此卡；普通局部事实不增加表格负担。细则见[责任闭合](references/responsibility-closure.md)。

效果不可继承：

- “实现存在”不等于当前 DI/路由/开关选中，更不等于生产激活。
- 局部事务只证明事务包含的持久化边界；不能继承到缓存、消息、RPC 或下游副作用。
- 修复某类状态的机制不能继承为对广播、通知、外部消费或用户可见结果的补偿。
- 调用成功、投递成功和最终消费成功是三个独立边界；接口名、调用点和未来测试都不能补齐中间证据。

### 4. BREAK：先找能推翻主张的分支

对每条强效果或全称主张，主动寻找最小反例：提前返回、未检查错误、feature flag、运行时分派、批次部分完成、重复输入、空输入、外部边界、无消费者或无重新触发点。只要仍有一个相关分支未读，就不得写“全部、总会、唯一、自动、不影响”。

答案必须区分：

`current repo behavior | selected conditional capability | adjacent-but-not-selected | externally guaranteed | unknown`

不得用篇幅、架构常识或“通常如此”填补未知。

### 5. SHIP：只签发可回链结论

最终正文按以下最短结构交付：

1. 身份/范围与紧凑证据矩阵；
2. 直接答案，每条带 `confirmed/inferred/unknown`；
3. 最短主链及关键旁路；
4. 仅对触发 EFFECT 的结论显示责任闭合卡；
5. 会改变答案的未知和最小验证动作。

签发前读取[最终审计](references/final-audit.md)。每个 current-fact 必须回链到证据矩阵；每个强效果必须回链到完整责任闭合卡。映射缺失就降级或删除，不以更多章节掩盖证据空洞。
