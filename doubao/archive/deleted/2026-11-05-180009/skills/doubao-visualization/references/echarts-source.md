# 来源说明

- Fornax SP：用户指定的 `agent.doubao_base.pro_online_prov5_visualize_echarts` 开发态 prompt。
- 抽取对象：系统消息中标题为 `# ECharts 图表展示规则` 的完整章节。
- 抽取结果：移动端/手机与 PC 分支中的 ECharts 章节内容一致；本 Skill 仅保留与 ECharts 关联的规则，不包含原 SP 的身份、安全、记忆、日期位置等非 ECharts 通用系统提示。
- 参考 Skill：用户指定的 MCP/ActionHub `doubao-visualization` Skill，用于参照目录拆分、触发边界、references 渐进加载和安全边界写法。
- 敏感信息处理：来源平台 URL、空间 ID、prompt ID 和 skill ID 不写入发布包正文；如需追溯，请查看交付工作目录下的只读抓取记录。
