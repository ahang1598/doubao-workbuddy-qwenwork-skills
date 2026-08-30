---
name: yunke-cli
description: "通过 omni-cli 操作云客 CRM：组织架构查询、员工/客户/通话数据统计、AI 智能分析。登录由 WorkBuddy 连接器经 OAuth 自动完成，使用前需确保 omni-cli 已安装且已登录。"
metadata:
  requires:
    bins: ["omni-cli"]
---

# yunke-cli（云客 CRM）

通过 omni-cli 的 yunke-crm 插件操作云客 CRM。凭证（`~/.omnicli/yunke-crm.json`）由 WorkBuddy 连接器经 OAuth 登录流程自动写入，无需手动登录。

> **前置条件**：连接器已安装 omni-cli 并完成 OAuth 登录（`yunke-crm.auth.login-web`）。首次使用前，用户须先在云枢完成「AI 助手登录」生成 agentapp 凭证，否则登录会返回 `access_denied`。

所有命令输出统一为 JSON 信封：`{ "status": "ok" | "error", "data": ..., "error": "..." }`。日期统一用 `YYYY-MM-DD`，时间戳为毫秒。

## 命令分类

| 类别 | 命令前缀 | 用途 |
|---|---|---|
| 组织架构 | `yunke-crm.org.*` | 部门树、员工搜索 |
| 用户信息 | `yunke-crm.user.*` | 当前登录用户详情 |
| 报表统计 | `yunke-crm.report.*` | 员工/客户/设备统计 |
| 通话 | `yunke-crm.call.*` | 通话记录、ASR 转写 |
| AI 分析 | `yunke-crm.ai.*` | SOP、情绪、意向、痛点等智能分析 |
| 定位 | `yunke-crm.location.*` | 部门/员工定位轨迹 |
| 其他 | `yunke-crm.misc.*` | 飞单预警、短信、管控日志 |

## 常用示例

### 组织架构

查询部门树（顶层部门）：

```bash
omni-cli yunke-crm.org.department-tree
```

按姓名搜索员工：

```bash
omni-cli yunke-crm.org.search --keyword "张伟"
```

### 报表统计

查询部门员工统计（`department_id` 留空取默认部门）：

```bash
omni-cli yunke-crm.report.employee-statistics --department_id "d001" --start_date "2026-07-01" --end_date "2026-07-31"
```

设备统计：

```bash
omni-cli yunke-crm.report.device-statistics
```

### 通话与 ASR

查询通话记录列表（后端每页最多 10 条，需翻页汇总）：

```bash
omni-cli yunke-crm.call.log-list --start_date "2026-07-01" --end_date "2026-07-31" --page 1
```

获取某通通话的 ASR 语音转写：

```bash
omni-cli yunke-crm.call.asr-result --call_id "call_xxx"
```

### AI 智能分析

员工 SOP 分析：

```bash
omni-cli yunke-crm.ai.sop-analysis --department_id "d001" --start_date "2026-07-01" --end_date "2026-07-31"
```

客户情绪分析 / 意向分析：

```bash
omni-cli yunke-crm.ai.customer-emotion --start_date "2026-07-01" --end_date "2026-07-31"
omni-cli yunke-crm.ai.customer-intention --start_date "2026-07-01" --end_date "2026-07-31"
```

### 定位

部门定位（建议先用 `org.search` 缩小部门范围）：

```bash
omni-cli yunke-crm.location.by-department --department_id "d001"
```

## 调用规范

- **先看 schema**：不确定参数时运行 `omni-cli yunke-crm.<cmd> --help` 查看参数定义。
- **显式传时间范围**：多数查询支持 `start_date`/`end_date`，建议显式传入较短范围，不要依赖默认。
- **翻页**：列表类命令返回分页信息，`pageCount > 当前页` 时继续翻页取全再汇总。
- **企业上下文**：所有命令以已登录用户所属企业为范围，无需手动传 `company_code`。

---

# yunke-cli (Yunke CRM) — English

Operate Yunke CRM via the omni-cli `yunke-crm` plugin. Credentials (`~/.omnicli/yunke-crm.json`) are written automatically by the WorkBuddy connector through the OAuth login flow — no manual login required.

> **Prerequisite**: The connector has installed omni-cli and completed OAuth login (`yunke-crm.auth.login-web`). Before first use, the user must complete "AI Assistant login" in Yunshu to generate the agentapp credential, otherwise login returns `access_denied`.

All commands output a JSON envelope: `{ "status": "ok" | "error", "data": ..., "error": "..." }`. Dates use `YYYY-MM-DD`; timestamps are milliseconds.

## Common Examples

Search employees:

```bash
omni-cli yunke-crm.org.search --keyword "Zhang Wei"
```

Employee statistics for a department:

```bash
omni-cli yunke-crm.report.employee-statistics --department_id "d001" --start_date "2026-07-01" --end_date "2026-07-31"
```

Call records:

```bash
omni-cli yunke-crm.call.log-list --start_date "2026-07-01" --end_date "2026-07-31" --page 1
```

Customer emotion analysis:

```bash
omni-cli yunke-crm.ai.customer-emotion --start_date "2026-07-01" --end_date "2026-07-31"
```

## Conventions

- Run `omni-cli yunke-crm.<cmd> --help` to inspect parameters when unsure.
- Pass explicit, narrow date ranges rather than relying on defaults.
- Paginate list commands until all pages are fetched, then aggregate.
- Commands are scoped to the logged-in user's company; no need to pass `company_code`.
