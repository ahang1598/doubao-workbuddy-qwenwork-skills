# 豆包在线载体 / 飞书交付映射

豆包文档、豆包表格和豆包 PPT 在当前运行时分别对应飞书在线文档、表格和 PPT。本文件定义用户选择豆包/飞书在线载体，或未指定载体时，QA 内容如何映射。实际创建、编辑、回读和权限处理交给 `lark-doc`、`sheet`、`lark-base`、`lark-ppt`，不在本 Skill 重写其内部命令。

## 目录

1. 载体选择
2. 文档结构
3. 表格与 Base 结构
4. PPT 结构
5. 单一事实源与同步
6. 回读检查
7. 降级与失败

## 1. 载体选择

用户明确指定永远优先。未指定时：

| 任务 | 默认组合 | 不要做 |
|---|---|---|
| 完整提测方案（方案/报告 + 用例） | 豆包文档 + 豆包表格 | 不额外创建 PPT |
| 只要方案、报告、复核、Bug 或收口 | 豆包文档 | 不生成本地 Markdown |
| 只要用例/追踪/矩阵 | 豆包表格 | 不制造长报告 |
| 执行协作、多角色回填 | 多维表格/Base | 不用文档表格模拟状态库 |
| 多 Bug 持续跟踪 | Base + 豆包文档摘要 | 不在两处手改状态 |
| 汇报演示或 go/no-go 会议材料 | 豆包 PPT | PPT 不承载全部明细；需要明细时链接文档/表格 |
| 一次性轻量回答且未要求文件 | 聊天直接回答 | 不为形式创建在线对象 |

飞书表格适合二维清单和公式；Base 适合状态流、多人协作、关联需求/用例/Bug 与多视图。二者选一作为结构化主载体，不并行维护重复行。

Markdown 不是默认兜底。只有用户明确说“Markdown”“md”或指定 `.md` 文件时才创建；在线载体创建实际失败后，才可在披露原因的前提下交付本地替代文件。

## 2. 文档结构

测试计划/报告的不可省章节：

1. 标题、版本和 `source_revision`
2. 一句话结论
3. 范围与非范围
4. 需求冲突与待确认
5. 高风险机制
6. 覆盖与执行摘要
7. Bug/阻塞/未验证项
8. 发布判断及依据
9. 后续动作、责任人与时间
10. 关联表格/Base/PPT

无执行数据时将“执行摘要”明确写成“尚未执行”；发布判断固定为“无法判断”。不要用空表或“暂无 Bug”暗示已验证。

Bug 文档必须把实际结果与期望结果分成独立小节；影响、严重程度与优先级分别陈述。

## 3. 表格与 Base 结构

### 需求追踪表

| 字段 | 类型/说明 |
|---|---|
| requirement_id | 稳定文本 ID |
| requirement | 原子需求 |
| source | 文档/章节/页面/接口 |
| risk_priority | P0–P3 |
| actor/trigger/rule | P0/P1 行为拆解 |
| observable_result | 可观察验收结果 |
| impact_scope | 关联模块、角色、数据或上下游 |
| conflict_id | 可空 |
| risk_mechanism_ids | 多值 |
| test_case_ids | 多值 |
| coverage_status | 已覆盖/部分覆盖/未覆盖/阻塞/不适用 |
| owner | 责任角色 |
| notes | 原因或下一动作 |

### 测试用例表

| 字段 | 类型/说明 |
|---|---|
| case_id | 稳定文本 ID；禁止自动编号替代 |
| module/title | 模块与标题 |
| priority/type | P0–P3 与测试类型 |
| preconditions | 前置条件 |
| test_data | 固定值/构造式/fixture |
| steps | 有序步骤 |
| expected_result | 可观察 oracle |
| requirement_ids | 关联需求 |
| risk_mechanism_ids | 关联机制 |
| execution_mode | automated/manual/hybrid |
| current_status | 从最新 execution 派生 |
| evidence_links | 证据 |
| assignee | 计划执行角色 |
| source_revision | canonical revision |

### 执行表

| 字段 | 类型/说明 |
|---|---|
| execution_id | `EXE-*` |
| case_id | 关联用例 |
| attempt | 第几次运行 |
| status | 通过/失败/待确认/阻塞/不适用 |
| validation_scope | precheck/exploratory/formal |
| actual_result | 真实观察 |
| evidence_ids | 多值 |
| started_at/finished_at | 含时区 |
| operator | 人或 runner |
| execution_level | full_automation/partial_validation/exploratory/blocked |
| retest_of | 可空 |

### Bug 表

| 字段 | 类型/说明 |
|---|---|
| bug_id/title | 稳定 ID 与标题 |
| severity | S1–S4 |
| priority | P0–P3 |
| status | 待复现/打开/修复中/待回归/关闭/拒绝 |
| case_id/execution_id | 关联证据链 |
| evidence_links | 附件或链接 |
| impact | 用户与业务影响 |
| classification | 问题分类 |
| trigger_hypothesis | 触发条件假设 |
| change_correlation | 近期变更关联 |
| blast_radius | 其他入口波及范围 |
| confidence | high/medium/low/unknown |
| owner/due_at | 责任与时限 |
| source_revision | canonical revision |

### 验收清单表

| 字段 | 类型/说明 |
|---|---|
| acceptance_id | `AC-*` 稳定 ID |
| title/type | 决策级检查项与类别 |
| case_ids | 关联的一条或多条用例 |
| blocking | 是否阻断发布 |
| current_status | 从关联用例最新 execution 派生 |
| notes | 不适用原因、阻塞说明或决策备注 |
| source_revision | canonical revision |

验收结果列使用公式或受控派生，不开放人工自由编辑；摘要区的各状态计数之和必须等于验收项总数。

Base 推荐关系：

```text
需求 ↔ 风险机制 ↔ 用例 ↔ 执行 ↔ 证据
                  ↘ 验收清单      ↘ Bug
```

状态只能从 canonical 或关系数据派生；不要同时在人肉维护的“状态文本”和公式列中各存一份真相。

## 4. PPT 结构

只有用户明确要汇报或存在评审会议时创建。默认 6–10 页，内容密度优先，不套 15 页惯例：

1. 封面：版本、范围、评审时间
2. 决策页：go/conditional/no-go/undetermined 与一句话依据
3. 业务链路与本轮范围
4. P0/P1 风险机制及覆盖
5. 执行结果与证据
6. 阻断 Bug/阻塞/未验证项
7. 放行条件、责任人与时限
8. 监控和回滚
9. 附录链接：文档、表格/Base

零证据时 PPT 不设置红色“No-Go”产品结论；应展示“Evidence pending / 无法判断”和获取证据的最小路径。

## 5. 单一事实源与同步

`qa-run.json` 保存：

```json
{
  "delivery_manifest": {
    "source_revision": 3,
    "outputs": [
      {
        "carrier": "lark_doc",
        "format": "lark_doc",
        "filename": "版本 QA 收口报告",
        "purpose": "test_report",
        "locator": "<真实 URL 或 token>",
        "status": "validated",
        "source_revision": 3,
        "validated": true,
        "readback_receipt": "标题、章节、数字、链接与 revision 回读通过"
      }
    ]
  }
}
```

规则：

- `locator` 只抄实际工具返回，不编造 URL/token；
- `filename` 必须匹配 `request_contract.delivery.filenames`；
- `validated` 必须附真实 `readback_receipt`，不能只凭“创建成功”；
- 外部载体不反向覆盖 canonical；
- 人工回填先导入 canonical，再刷新投影；
- 多轮修改更新原对象；
- 每个对象记录 `source_revision`；
- revision 不一致时外部状态标 `stale`。

## 6. 回读检查

### 文档

- 标题与章节完整；
- 表格没有退化成纯文本；
- 长内容未截断；
- 结论、数字、Bug 状态与 canonical 一致；
- 链接可定位到真实对象。

### 表格/Base

- 表头、字段类型和必填列存在；
- 行/记录数与有效对象数一致；
- 输入清单中的 Sheet/压缩包成员核对数与材料实际结构一致；
- ID 没被自动格式化、截断或重复；
- 多值关系没有被逗号文本破坏；
- 状态枚举与严重程度/优先级口径一致；
- 验收状态由关联执行派生，状态计数之和等于总数；
- 筛选、排序、公式或视图没有隐藏关键阻塞项。

### PPT

- 页面无文字溢出或截断；
- 图表数字能从表格复算；
- 决策页与报告一致；
- 未验证项没有被视觉弱化；
- 详细内容有可点击的文档/表格链接。

## 7. 降级与失败

对应飞书 Skill 不可用、无权限或创建失败时：

1. 保留已完成的 QA 内容；
2. 交付本地 Markdown/CSV/JSON/PPTX 中最接近的格式；
3. 在 `delivery_manifest` 记录 `failed/local_fallback` 与原因；
4. 明确哪些飞书对象没有创建；
5. 不编造链接，不把聊天中的表格声称为已落到飞书；
6. 权限恢复后更新原任务，不从内容建模阶段重做。

降级文件仍必须通过 `scripts/qa_flow.py publish` 登记、回读和返回 locator；没有发布回执不能对外声称完成。
