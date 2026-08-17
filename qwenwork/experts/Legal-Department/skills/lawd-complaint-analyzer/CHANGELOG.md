# Changelog

## v2.1.0 (2026-08-11) — 三批真机测试整改（M3/M7/M1）

1. **M7 方案A：消除门禁语义与示例矛盾**——门禁语义第 1 条改为"禁止成批罗列未核验法条；inline 引用必须逐条标注（待核验）并尽快核验"；example.md 与 defense-checklist-template.md 顶部加"内置法条为定位提示，实际输出须标注"说明
2. **M7b：output-template.md 补输出位**——5.1 表加"类型化评估要点"列；5.1 与 5.2 间插入"5.1.5 四关筛查结果"子表（对齐 evidence-vulnerability.md §三/§四框架）
3. **M3：A.5 质量自检硬门禁化**——8 项检查必须逐项显式输出 ✅/❌，仅口头声明视为未执行，未输出不得进入门禁
4. **M1：AH-1 补扫描件段落编号规则**——扫描件无段落编号时按逻辑段划分编号（当事人信息/诉讼请求/事实与理由各节），禁用物理页码替代

## v2.0.0 (2026-08-10) — 第二批单元 9 合并改造

- 合并 `lawd-civlit-dispute-focus`（律师争议焦点分析）为**模式B**，本技能原能力成为**模式A 起诉状风险分析**；对外一个入口，内部按用户意图分流
- SKILL.md 重构为固定六段结构：能力总述 / 触发与分流 / 模式工作流 / 数据源 / 门禁脚本 / 交付物；两模式工作流原文整合，未删减专业方法论
- `name` 保持 `lawd-complaint-analyzer` 不变（QwenWork 要求 name = 目录名）；`name_zh` 由「起诉状分析器」改为「起诉状分析与攻防策略」；description 单行重写，覆盖两模式触发词与 NOT for 边界
- 落地原 dispute-focus description 中"起诉状诉请风险评估优先用专门能力"的逻辑为内部路由规则；保留「仅需类案检索 → `lawd-case-retrieval`」外部边界
- references 归并 dispute-focus 9 个文件：3 个知识库（typical-disputes-by-case-type / legal-elements-checklist / evidence-checklist-by-focus）与 docx-format-standard 按原名迁入并双模式共享；4 个模式B 专属文件加 `dispute-focus-` 前缀；简易版样例迁入 `references/examples/`
- 新增要件清单唯一性规则，避免 `case-dimensions-<案由>.md` 与 `legal-elements-checklist.md` 两套要件编号在同一交付中打架
- 新增门禁脚本 `scripts/validate_analysis_report.py`（争点编号连续无重复 / 要件↔争点映射完整 / 模式A 逐项回应数≥诉请数 / 法条引用带法律名+条号），交付前必须运行、未通过禁止交付；`tests/` 下附 4 份自测样例
- 数据源不改调用方式：类案与法规检索继续调用兄弟技能 `lawd-case-retrieval` / `lawd-regulation-retrieval`（其自身连接器改造由并行任务负责）；`dws doc create` 仍为 docx 不可用时的降级路径
- 被吸收目录 `lawd-civlit-dispute-focus` 保持原样，暂不删除（验收后由产品决定去留）

## v1.0.0 (2026-08-03)

- 自《悟空-千问办公法律规划skills》规划表（0611版，P0）的 skill zip 附件移植入库（起诉状深度解析）
- 移植时清理 .DS_Store / __pycache__ 等垃圾文件
- 已知问题备案：与库内相关技能存在触发语义重叠，按产品决定暂不调整（详见《规划表vs库内技能差距映射表-20260803.md》）
