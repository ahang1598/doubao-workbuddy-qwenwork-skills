# Changelog

## v1.1.0 (2026-08-12)

去除 DeLi-Lagal 虚空依赖，改为能力语义 + 三段式探测：

- SKILL.md：移除对不存在的 DeLi-Lagal MCP（law-search / case-search）的硬编码依赖，全文改为「法规检索能力 + 案例检索能力」的能力语义表述；Phase 2 权威检索重写为三段式探测流程（qwenwork_mcp_tool_list 探测 → qwenwork_mcp_tool_get 验 schema → qwenwork_mcp_tool_call 调用，多家连接器失败切换），对齐 律师法规检索；frontmatter 新增 recommended_connectors 与 graceful_degradation: strict；探测不到连接器时停止执行并提示用户到千问办公 设置 → 连接器启用
- references/mcp-tool-usage.md 重写为「数据连接器探测与字段映射指南」：保留法规检索连接器常见字段映射（lawName→title、lawOrder→item、lawSourceContent→content、timeliness→status、similarity→score）及 score 置信度标注、status 默认值覆盖、张冠李戴交叉验证规则；新增案例检索侧语义字段映射（caseNo / trialCourt / trialDate / verdict 等），案例检索能力对接北大法宝、元典等连接器，以实际探测到的工具返回为准
- references/output-template.md、references/example.md：去除 DeLi-Lagal 字样，改为"权威检索服务/法规、案例数据库"
- 新增 scripts/extract_citations.py：从中文法律文本提取法条引用（《法规名》第X条，支持中文数字条号）与案号，输出 JSON，仅依赖 python3 标准库

## v1.0.1 (2026-08-11)

0811 QwenWork 真机测试整改（第二批 N5-N6，依据执行自评报告 81 分扣分项）：

- N5：references/mcp-tool-usage.md 新增「五、实际环境适配」——DeLi-Lagal 设计字段与实际法规检索服务（fy-law-search-service flfg_parallel/iterative_search_tool）的字段映射表；score≠similarity 的展示与低分置信度标注规则；数据源未返回字段（如施行日期）严禁模型知识填充；status 默认值主动覆盖；item/content 组合干扰规避
- N6：SKILL.md 重试策略新增「张冠李戴交叉验证」例外规则（第 2 次重试命中不同条号时允许追加 1 次目标条号检索，不计入重试上限）；step 1.6 确认要求明确模式 A/B 均须暂停等待用户确认（消除原措辞歧义）

## v1.0.0 (2026-08-03)

- 自《悟空-千问办公法律规划skills》规划表（0611版，P0）的 skill zip 附件移植入库（法条案例一键验真）
- 移植时清理 .DS_Store / __pycache__ 等垃圾文件
- 已知问题备案：与库内相关技能存在触发语义重叠，按产品决定暂不调整（详见《规划表vs库内技能差距映射表-20260803.md》）
