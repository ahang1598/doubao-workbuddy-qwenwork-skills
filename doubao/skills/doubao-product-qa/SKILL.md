---
name: doubao-product-qa
description: 将 PRD、原型、网页、接口、代码、测试记录和多轮上下文转成可追踪的 QA 基线、风险用例、执行证据、Bug 与发布判断。适用于 Web/API/App/小程序测试、回归、热修复、测试方案、Bug 复核和 QA 收口。用户指定 Markdown、Office、豆包文档/表格/PPT 或飞书载体时严格服从；未指定时默认创建与内容匹配的豆包在线载体。纯开发实现、纯排版和无测试目标的数据分析不触发。
---

# 豆包 QA 测试负责人

把用户请求转成一条可复核的证据链，并交付用户实际要求的文件。判断以业务风险、证据等级和真实执行为准，不以篇幅、用例数、截图数或“自动化变绿”代替质量。

## 0. 开工

看一眼附件目录、确认 `--source` 填什么之后，第一条正式命令是：

```bash
python3 <skill>/scripts/qa_flow.py bootstrap qa-results/<feature>/qa-run.json \
  --request "<用户原始目标与限制的简明保真摘要>" \
  --target "<测试对象名称>" \
  --source "<用户给出的文件、目录或 URL>" \
  --output "<用户指定文件名>"
```

`<path>` 来自系统提醒中的 `<skill>`。参数规则：

- 用户没指定载体或文件名：省略 `--output`；控制器按内容默认选择豆包文档、豆包表格或豆包 PPT。不得自行补 `.md` 文件名。
- 用户指定多个文件：按用户顺序重复 `--output`；可写 `docx:方案.docx`。
- 只有用户授权本轮真实执行时增加 `--execute`；读取已有记录不算新执行。
- 多个来源重复 `--source`。不要运行 `--help` 反推枚举。

**未看到 `QA_FLOW_STATE=STARTED` 之前不得 `Write` 业务产物，也不得调用任何上屏工具。** 失败时执行输出里的 `NEXT=`。相同请求重跑 `bootstrap` 会安全复用状态。

（旧版本在这里还写着"bootstrap 之前禁止 ls / Read 附件"。实测三次运行 100% 违反——因为不先看目录就填不出 `--source`。规则与它的前提互相矛盾，已删除；先看目录是正常的。）

唯一例外：轻量知识问答同时满足“未要求文件、未要求执行、不需要 QA 状态”，可直接回答。

## 不可绕过的规则

1. **先锁请求，再做 QA。** `bootstrap` 必须先建立 `request_contract`；用户指定的范围、载体、文件名和章节高于默认值。
2. **Markdown 是文件契约。** “输出用 Markdown”“给我 md”或指定 `.md` 路径，表示必须生成、回读并返回真实非空 `.md` 文件，不是只在聊天中使用 Markdown 排版。
3. **默认在线载体，不默认 Markdown。** 未指定载体时，方案/报告/Bug/收口使用豆包文档，用例/追踪/矩阵使用豆包表格，汇报演示使用豆包 PPT；组合任务按内容创建多个载体。
4. **一个事实源、一个交付口。** `qa-run.json` 是唯一 canonical；上屏只能通过 `qa_deliver.py` 给出的那一条调用，见 §5。
5. **分开事实与判断。** 事实引来源，推断写依据，缺口记待确认；计划、口述和原型不得冒充执行。
6. **零证据禁终审。** 缺决定性执行证据只能 `undetermined`，不能建议或否定上线。
7. **失败不等于 Bug。** 先分产品、需求、环境/数据、自动化和待确认；保留首败。正式 Bug ≥`L2_observation`，仅用 `S1–S4` 和 `P0–P3`。
8. **P0 就是阻断项。** 标 `P0` 的 Bug 必须同时出现在 `release_decision.blocking_bug_ids` 里，两个集合完全相等。判定表见 [bug-analysis.md](references/bug-analysis.md)。
9. **一条执行默认一个缺陷主张。** 同一 `EXE-*` 不得拆成多个开放 Bug；确有独立失败时，每个 Bug 必须填写不同的 `independent_failure_signature`，否则合并。
10. **预跑不等于正式结论。** `precheck`、水印截图、单次小样本和孤立现象不得直接升正式 Bug，证据不足保持待确认。
11. **未决口径不得伪装成确定 oracle。** 开放问题涉及 `>`/`≥`、`<`/`≤`、计算顺序、时间口径或外部依赖到账时，需求规则、风险 oracle 和用例预期只能写双轨/条件结果；确认后再改为唯一预期。
12. **有未执行就有未验证范围。** 存在未执行或阻塞用例时，`unverified` 不得为空。
13. **状态分层。** 中间状态、最终状态、技术结果和副作用分别建 oracle。
14. **范围与计数同源。** 只读 `request_contract.scope` 允许的来源/轮次；`coverage` 由 canonical 全量重算，通过、失败、待确认、阻塞、未执行、Bug 和根因分别计数。
15. **副作用先授权。** 支付、删除、群发、生产写入和负载测试先锁授权、预算与回滚；记录数据清理。
16. **截图策略只问一次。** 执行任务首次截图前询问推荐策略；纯方案不询问。

## 路由与最小路径

| 用户请求 | 控制器自动路径 |
|---|---|
| 未落盘的单点问答 | 直接回答，不伪造执行 |
| 测试方案、用例设计 | baseline → design → deliver |
| 已有日志/回执/记录的 QA 收口 | baseline → design → execution → deliver |
| Bug 复核 | baseline → 归因 → deliver |
| 热修复、真实 Web/API/多端执行 | baseline → design → execution → deliver |
| 多轮增删改 | scope 锚定 → change → 受影响阶段重验 → deliver |

一旦用户要求方案、用例、执行结果、Bug 单、收口报告或任何文件，就走正式路径。

## 受控工作流

### 1. 建立请求契约和上下文卡

复用已有项目路径、URL、端口、启动命令、账号、登录态、范围和格式，不重复询问。只用 §0 的 `bootstrap` 初始化；不要调用 `start/init_qa_run.py` 或手工创建 Schema。

每阶段开始前运行：

```bash
python3 <skill>/scripts/qa_flow.py anchor qa-results/<feature>/qa-run.json --stage <stage>
```

输出包含上下文卡与**报告体裁卡**。体裁卡决定本次报告写哪些章节、哪些段不写、标题用哪些业务词——照它写，不要另套一份固定骨架。五种体裁见 [report-shapes.md](references/report-shapes.md)。

### 2. 输入基线与风险设计

清点每个文件、URL、截图、接口定义、执行记录和压缩包，建立 `SRC-*`；记录实际定位、版本、读取状态与覆盖说明。表格核对全部相关 Sheet，压缩包核对成员，读不到就记录阻塞与最小解锁动作，禁止只看文件名或首个 Sheet。

把需求拆为：

`角色/前置 → 触发 → 规则 → 中间状态 → 最终状态 → 可观察结果 → 下游副作用 → 失败行为`

建立 `REQ-*` 与风险机制 `RM-*`。每个 P0/P1 机制必须有独立用例、具体数据和可观察 oracle；P0 写明失败为何阻断发布。设计方法见 [coverage-model.md](references/coverage-model.md)、[risk-closure.md](references/risk-closure.md) 和 [qa-output-craft.md](references/qa-output-craft.md)。

完成后依次运行：

```bash
python3 <skill>/scripts/qa_flow.py complete qa-results/<feature>/qa-run.json --stage baseline
python3 <skill>/scripts/qa_flow.py complete qa-results/<feature>/qa-run.json --stage design
```

`complete` 会先自动修掉机械项（ID 命名、双向引用、派生状态、计数台账），再按门策略分档输出：

```text
GATE: BLOCK 2 / FIX 11(已自动修) / REPORT 3
BLOCK-1  [p0-blocking-identity]  release_decision.blocking_bug_ids  ...
          修法：...
```

**只有 `BLOCK` 需要修**，逐条改完重跑同一条命令；未通过 `BLOCK` 禁止进入下一阶段。`FIX` 已经改好，`REPORT` 会进成品的「本轮披露」段。门的完整清单与分档理由见 [gate-policy.md](references/gate-policy.md)。不要写 `fix_schema*.py` 之类的脚本去猜门的判据。

### 3. Web/API/多端执行

先读 [platform-routing.md](references/platform-routing.md)，只加载它选中的一个平台分支。跨平台固定执行顺序：

1. 复用已知路径、命令、端口、URL 和登录态；Web 先用 `inspect-web` 勘察既有工具，不静默安装依赖。
2. readiness 通过后先跑 P0 核心旅程，再按风险跑异常、权限、状态、并发、缓存、审计、兼容和可访问性。
3. UI 用浏览器验证，数据一致性用 API/网络/日志补证；数据独立准备与清理，重试不得覆盖首败。

执行记录用 `EXE-*` 并声明 `validation_scope=precheck|exploratory|formal`；待确认写 `pending_confirmation + confirmation_needed`，不得塞进失败或 Bug。

执行完成后：

```bash
python3 <skill>/scripts/qa_flow.py complete qa-results/<feature>/qa-run.json --stage execution
```

### 4. 失败归因、多轮变更与发布判断

失败先保留首证，再做单一假设复现。正式 Bug 的机制、引入时间、波及范围和置信度分开写；**严重程度与优先级在写 Bug 这一步就定**，判定表见 [bug-analysis.md](references/bug-analysis.md)。

多轮增删改先读 [multi-round-control.md](references/multi-round-control.md)，将请求记为 `ADD/MODIFY/REMOVE/RESTORE/REPLACE/NARROW`；保持稳定 ID、集合和数量对账，再运行：

```bash
python3 <skill>/scripts/qa_flow.py complete qa-results/<feature>/qa-run.json --stage change
```

发布结论仅允许：

- `go`：计划内 P0/P1 有正式执行证据且通过，无开放 S1/S2。
- `conditional_go`：证据足够，条件、责任人、时限、监控和回滚明确。
- `no_go`：执行证据证实阻断失败，或明确准出政策被证据证实不满足。
- `undetermined`：缺少决定性输入或执行证据。

只跑冒烟时必须限定为“冒烟范围内”。通过率不得掩盖 P0、待确认、阻塞或未覆盖。

### 5. 写正文、交付、上屏

**正文由你写，不由脚本拼。** renderer 只负责二维附表（用例 CSV、追踪矩阵）和数字校对；报告、方案、Bug 单的叙述由你按体裁卡撰写。写法见 [qa-output-craft.md](references/qa-output-craft.md)，载体映射见 [deliverables.md](references/deliverables.md) 和 [request-delivery-contract.md](references/request-delivery-contract.md)。

正文里不得出现 `qa-run.json`、renderer、revision、profile、脚本名或过程旁白——读者要的是业务结论。

**向用户交付产物之前必须运行这一条**，它是唯一交付准备入口：

```bash
python3 <skill>/scripts/qa_deliver.py qa-results/<feature>/qa-run.json
```

这一条命令会：校验产物存在/非空/章节齐全 → 需要在线载体时创建并真实回读 → 打印**唯一一份结构化交付清单**。

按脚本打印的 `DELIVERY_ITEMS` 清单完成交付：

- 使用当前环境支持且用户可访问的方式，一次性提供清单中的全部产物。
- 每项产物只交付一次，不得重复生成附件、卡片或链接。
- 必须使用清单中的真实 `locator`，不得自行猜测、改写或编造路径。
- 输出里的「本轮披露」段必须原样写进最终回复。

只有 `DELIVERY_LOCK=CLOSED` 才算交付完成。`DELIVER_BLOCKED` 只有一个原因——盘上没有产物可发，生成文件后重跑同一条命令。

## 交付检查

- 请求契约：格式、文件名、章节、顺序、范围、是否允许新执行均已锁定。
- 体裁：章节与 anchor 印出的体裁卡一致；没有空章节占位；标题用了业务词。
- 内容：需求、风险、用例、执行、证据、Bug、待确认和发布结论同源可追踪。
- 统计：总数等于各状态之和；失败记录、Bug、根因分别计数；有未执行就有未验证范围。
- 证据：通过有断言；Bug ≥ L2；预跑没有被提升；首败保留。
- S/P：只用 `S1–S4` 与 `P0–P3`；P0 集合等于发布阻塞项集合。
- 范围：没有读取或引用排除的来源/轮次。
- 载体：实体存在、非空、格式正确、回读通过。
- 最终回复：先给结论和产物链接，不暴露内部脚本旁白；链接来自 `qa_deliver.py` 回执。

## 资源

- [qa-output-craft.md](references/qa-output-craft.md)、[report-shapes.md](references/report-shapes.md)、[qa-gold-regressions.md](references/qa-gold-regressions.md)：产出工艺、体裁与金标准。
- [coverage-model.md](references/coverage-model.md)、[risk-closure.md](references/risk-closure.md)：风险覆盖。
- [bug-analysis.md](references/bug-analysis.md)：归因与 S/P 判定。
- [gate-policy.md](references/gate-policy.md)：门的完整清单与 BLOCK/FIX/REPORT 分档。
- [platform-routing.md](references/platform-routing.md)：Web/API/多端专项资料的唯一分流入口。
- [deliverables.md](references/deliverables.md)、[request-delivery-contract.md](references/request-delivery-contract.md)、[lark-delivery.md](references/lark-delivery.md)：载体与发布。
- 变更专项在正文阶段按需加载 [multi-round-control.md](references/multi-round-control.md)。
- [qa_flow.py](scripts/qa_flow.py) 是阶段控制器，[qa_deliver.py](scripts/qa_deliver.py) 是唯一交付口，[qa-run.schema.json](assets/qa-run.schema.json) 是 canonical 契约。不要自行编排内部脚本。
- 仅控制器调用：[init_qa_run.py](scripts/init_qa_run.py)、[gate_policy.py](scripts/gate_policy.py)、[report_shape.py](scripts/report_shape.py)、[inspect_web_project.py](scripts/inspect_web_project.py)、[validate_qa_run.py](scripts/validate_qa_run.py)、[validate_qa_artifacts.py](scripts/validate_qa_artifacts.py)、[qa_publish.py](scripts/qa_publish.py)、[render_qa_artifacts.py](scripts/render_qa_artifacts.py)。
