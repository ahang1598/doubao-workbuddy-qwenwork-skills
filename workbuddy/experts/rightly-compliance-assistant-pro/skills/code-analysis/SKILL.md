---
name: code-analysis
description: |
  代码合规分析能力，通过MCP对接Rightly平台数据，在代码中定位合规问题。
  触发词：代码分析、Rightly堆栈、代码定位、调用链、合规检测、productId
---

# 代码合规分析

## 功能说明

通过 Rightly MCP 接口获取产品的合规检测数据（违规API调用、调用堆栈、敏感行为统计），结合代码仓库分析，定位合规问题并生成修复建议。

## 使用场景

- 用户需要查看产品的合规检测结果
- 用户需要定位违规API的调用位置
- 用户需要分析调用堆栈，区分App代码和SDK调用
- 用户需要批量排查合规风险

## MCP配置

使用专家包 `.mcp.json` 中声明的 `rightly` MCP服务器：
- 调用MCP工具时需传入 `productId` 标识目标产品
- 不在本技能中硬编码服务地址；以当前专家包的内置 MCP 配置为准

## 参考资料

分析过程中可参阅以下文件获取模块映射和解决方案知识：
- violation-mapping技能中的 @references/api-module-mapping.md — API与PandoraEx模块映射
- case-solution技能中的 @references/common-stack-solutions.md — 常见堆栈问题解法
- case-solution技能中的 @references/rightly-guide.md — Rightly指引与分析建议
- rightly-remediation-guides技能中的技术指引 — 非沙箱文件访问日志与 Android 分模块授权问题的代码级分析
