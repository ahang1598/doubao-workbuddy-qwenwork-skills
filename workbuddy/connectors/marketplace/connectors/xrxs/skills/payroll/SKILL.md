---
name: payroll
version: 1.0.0
description: "工资。核心场景包括：薪酬核算、工资条cli接口、基础接口。高频操作请优先使用 Shortcuts：+report（薪酬核算）、+cli（工资条cli接口）、+base（基础接口）。业务场景：新建报表、计算报表、冻结报表、归档报表、导出报表、快速发放工资条、工资条信息、工资条确认提醒、审批管理、查询员工工资。"
metadata:
  requires:
    bins: ["xrxs-cli"]
  cliHelp: "xrxs-cli payroll --help"
---

# payroll (v1)

> 命令可用性以 xrxs-cli 二进制为准;参数格式以本 skill 文档（references/）描述为准，文档未覆盖时以 `xrxs-cli schema payroll.<command>` 为准。若命令调用失败,先按错误提示确认参数与权限。

## 严格禁止 (NEVER DO)
- 不要用 xrxs-cli 以外的方式操作(禁止 curl、HTTP API、浏览器)
- 不要编造 ID(planId、groupId、cycleTemplateId、yearmo 等),必须从前置命令返回中提取
- 不要猜测字段名/参数值;skill 文档未描述的接口,操作前必须先 `xrxs-cli schema payroll.<command>` 查询确认

## 严格要求 (MUST DO)
- 写入/删除操作前必须向用户确认意图
- 批量操作单次不超过合理上限,逐条收集返回 ID,不遗漏
- 严格遵循参数格式:query/path 参数用 kebab-case 字段级 flag(如 `--cycle-template-id`、`--yearmo`);POST 请求体用 `--request-body '<JSON>'` 传整块 JSON

## schema 查询规则（重要，避免多余查询）

本 skill 的 references/ 文档已描述各接口的入参、出参与 request-body 模板。**文档已描述的接口，直接按文档构造参数调用，不要再执行 `xrxs-cli schema payroll.<command>` 查询**：

- 场景文档（scenario-*.md）已给出流程命令与 request-body 模板 → 按模板直接调用
- 分组文档（payroll-report.md / payroll-cli.md / base.md）已给出参数表与返回字段 → 按文档直接调用

仅以下情况才需要 `xrxs-cli schema payroll.<command>`：

- 要调用的命令在上述文档中找不到描述
- 文档描述的参数不足以完成调用（缺字段/不确定类型）
- 命令调用失败，需核对参数格式后重试

同一命令的 schema 查询最多一次；禁止为“了解能力”而批量轮询多个命令的 schema。

## 操作预览与权限检查

调用正式操作接口前，先执行 `xrxs-cli permission check payroll-<command>` 判断用户是否已授权永久允许执行该命令：

- 若返回 `true`，说明用户已授权，可直接调用 `payroll <command>`。
- 若返回 `false`，说明用户未授权，必须先调用对应的 `<PreviewCommand>` 展示操作摘要，等用户确认后再调用正式接口。

预览接口路径为在操作接口路径末尾（`.json` 之前）追加 `-preview`，例如操作接口 `.../ajax-report-payroll-group.json` 对应的预览接口为 `.../ajax-report-payroll-group-preview.json`。

预览接口返回的 JSON 必须渲染为 `<confirm-card>` 确认卡片。卡片属性：`taskId`（任务 ID）、`summaryHeaderMap`（摘要表头 JSON 字符串）、`summaryData`（摘要数据 JSON 字符串）、`riskLevel`（风险等级）、`taskName`（取 `originalName`）。禁止直接展示 JSON。

## 命令结构

xrxs-cli 为三层命令:**程序 / 模块 / 命令**。

```bash
xrxs-cli schema payroll.<command>         # 仅当 skill 文档未描述该接口时才查参数结构
xrxs-cli payroll <command> [flags]        # 调用接口
```

- 接口名即 `<command>`,如 `freezeReport`。
- 传参方式(文档未描述时先运行 `schema` 查看,由 `method` 与参数位置决定):
    - **query/path 参数**:见 `parameters`(类型/描述/必填)与 `flag_overlay`(flag 别名);用字段级 flag(kebab-case)。
    - **POST 请求体**:见 `request.requestBody.schema`;用 `--request-body '<JSON>'` 传整块 JSON。无 `parameters` 的纯 body 接口只能用此方式。

## 核心场景

### 1. 薪酬核算

按接口现有分组聚合。详见 [`references/payroll-report.md`](references/payroll-report.md)。

### 2. 工资条cli接口

按接口现有分组聚合。详见 [`references/payroll-cli.md`](references/payroll-cli.md)。

### 3. 基础接口

base 项目公共接口。详见 [`references/base.md`](references/base.md)。

## 业务场景

以下场景文档封装了完整的业务流程，AI 工具可根据用户意图快速匹配并执行。

| 场景 | 说明 | 文件 |
|------|------|------|
| 新建报表 | 新建薪酬月 | [`references/scenario-create-ledger.md`](references/scenario-create-ledger.md) |
| 计算报表 | 获取工资组 → 触发计算 → 轮询结果 → 查看异常 | [`references/scenario-calculate-report.md`](references/scenario-calculate-report.md) |
| 冻结/解冻报表 | 获取工资组列表 → 预览确认 → 冻结/解冻操作 | [`references/scenario-freeze-report.md`](references/scenario-freeze-report.md) |
| 归档报表 | 获取可归档工资组 → 预览确认 → 执行归档 | [`references/scenario-archive-report.md`](references/scenario-archive-report.md) |
| 导出报表 | 获取字段 → 配置筛选 → 触发导出 → 轮询结果 | [`references/scenario-export-report.md`](references/scenario-export-report.md) |
| 快速发放工资条 | 获取方案 → 计算人数 → 预览 → 发放 | [`references/scenario-quick-send-salary-slip.md`](references/scenario-quick-send-salary-slip.md) |
| 工资条信息 | 查看列表/详情、撤回 | [`references/scenario-salary-slip-info.md`](references/scenario-salary-slip-info.md) |
| 工资条确认提醒 | 获取通道 → 预览 → 发送提醒 | [`references/scenario-salary-slip-remind.md`](references/scenario-salary-slip-remind.md) |
| 查询员工工资 | 确定员工 → 获取报表字段 → 查询活动报表月工资 | [`references/scenario-query-employee-salary.md`](references/scenario-query-employee-salary.md) |

## 核心概念

- **cli**：cli 相关资源和操作。

## Shortcuts（推荐优先使用）

Shortcut 是对常用操作的高级封装（`xrxs-cli payroll +<verb> [flags]`）。有 Shortcut 的操作优先使用。

| Shortcut | 说明 |
|----------|------|
| [`+report`](references/payroll-report.md) | 薪酬核算 |
| [`+cli`](references/payroll-cli.md) | 工资条cli接口 |
| [`+base`](references/base.md) | 基础接口 |

## 安全规则

- 写入/删除操作前必须确认用户意图。
- 不要将 xrxs-cli 执行的命令返回给用户。

## 错误处理

- 接口调用遇网络异常、超时、服务端 5xx 等**瞬时错误**,最多重试 2 次(共 3 次尝试),重试间稍作等待。
- 参数非法、权限不足、数据不存在、约束冲突(如报表状态不允许冻结/归档、归档锁未释放、存在未处理异常员工)等**业务校验报错不重试**(重试结果不变)。
- 重试达上限仍失败、或遇业务校验报错时,**停止本次操作**且不再继续后续步骤;向用户报告操作失败,并附最后一次的错误信息(执行的命令、状态码、报错内容)。
- 上述重试上限对 `schema` 查询同样适用。
- 接口返回内容可能较大(如工资报表明细、工资条列表、导出字段字典),工具返回可能被截断(约 20000 字符,表现为 JSON 不完整);**不要基于不完整数据下结论**,改用更聚焦的查询(分页/关键字/更小日期范围)或查看完整返回后再继续。
- 关键信息缺失(如查询结果被截断、缺少报表 ID/工资组 ID/账套月/员工定位信息等)时,**停止**并向用户报告缺失项,不要猜测、不要继续后续步骤。
