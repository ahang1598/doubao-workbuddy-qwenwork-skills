---
name: ai-quant-team-runtime
description: Use when WorkBuddy launches the portable AI quant research team; load and enforce its state machine, evidence contracts, member routing, approval gate, and completion receipt.
license: GPL-3.0-only
metadata:
  package_version: 0.4.2
---

# Portable team runtime

Read `references/AGENTS.md` first and treat it as the only business-policy source. Read the matching member declaration under `references/members/` when invoked as a member.

`references/team.json` uses canonical QuantSkills repository IDs. WorkBuddy Agent frontmatter binds the corresponding internal Skill declaration names recorded in `references/workbuddy-skill-bindings.json`; treat those names as the same routed Skill, not as replacements.

The WorkBuddy adapter adds only these host mappings:

- `TeamCreate` creates the team once, owned by `pd-ai-quant-research-team`.
- `AgentTool` invokes one declared member in an isolated context.
- The real AgentTool call ID is the `invocation_id`; never invent one.
- The `pandadata` Connector supplies all formal financial market data.
- Local command execution runs `scripts/workflow_guard.py` and the bound Skill scripts.

Before starting, verify that the selected mode satisfies `references/host-capability-contract.json`. If WorkBuddy does not expose isolated member calls, a real call ID, persistent files, local process execution, PandaData, approval resume, or `pandaai-cli >=0.1.6` where required, return `BLOCKED_HOST_CAPABILITY`. When the CLI is installed but not authenticated, follow `references/pandaai-cli-login-contract.md`; login additionally requires a user-visible TTY and a persistent user home. Do not fall back to one-Agent role play.

## 最高优先级：PandaData MCP 真实数据硬闸门

本节高于成员角色、业务 Skill 及其历史数据源说明。凡任务涉及行情、财务、资金、因子、
筛选、排名、回测、基准或其他现实金融数据，都必须执行以下流程：

1. 开始时设置 `DATA_GATE=CLOSED`，先真实调用一次 `auth_status`。
2. 认证可用后，按 `references/pandadata-interface-contracts.md` 的固定路由直接调用
   `call_pandadata`；已登记接口不得先用 `search_methods` 或 `get_method_doc` 检索。
3. 最低路由的必需接口均取得真实响应后才能设置 `DATA_GATE=OPEN`。闸门关闭时禁止分析、
   排名、数字结论、回测结论及“无数据”，也不得用模型记忆或用户未提供的数据补数。
4. 只有 Connector 明确报告已登记方法的参数契约失效时，才对该方法调用一次
   `get_method_doc` 并最多重试一次；只有方法未登记或明确不存在时，才调用一次
   `search_methods`。0 行不得触发动态检索。
5. 0 行必须执行交易日/代码校验、放宽日期窗口、移除非必填过滤及备用参数重试。
   第二次仍为空才可报告无数据，并保留两次真实回执。
6. 最终答案必须附带“接口｜实际参数｜状态｜行数｜数据日期范围｜关键字段”调用回执。
   缺少回执或闸门未打开即视为未完成，必须继续调用工具或如实返回阻塞错误。

禁止调用本地 PandaData Python SDK、HTTP 地址或下载脚本；禁止索取或保存 PandaData
账号、密码、Token、MCP 地址和请求头。WorkBuddy Connector 的认证与凭证由平台管理。

## PandaAI CLI 登录与因子大赛闸门

标准版和审计版进入 PandaAI 实验阶段时必须先运行绑定 Skill 中的
`python scripts/bootstrap.py --status`。`READY` 才能继续；`LOGIN_REQUIRED` 时先让用户
确认已准备在可见终端输入登录信息，再以 TTY 运行 `python scripts/bootstrap.py --login`。
登录不能通过命令守卫、输出重定向或后台进程执行，也不得把登录信息放入聊天、参数、任务包
或日志。登录后再通过命令守卫运行一次脱敏的 `--status`，只有 `READY_AFTER_LOGIN` 才可
继续。完整状态机和收费批准要求见 `references/pandaai-cli-login-contract.md`。
