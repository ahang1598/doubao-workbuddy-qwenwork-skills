# CHANGELOG

## v2.1.0 - 2026-08-11 — 三批真机测试整改（M1/M3/M5/M11）

1. **M11② 客户沟通弹性规则**（SKILL.md §3.0.2）：材料齐全时简化为确认 3 个关键假设（核心经济目标/调解意愿/成本承受力），未确认须标注"基于材料推断"，不得静默跳过
2. **M1+M4 材料深度分析**（SKILL.md §3.0.4）：关键数字复核清单化（诉称vs凭证加总/退费扣减/跨证据一致性/差异标注）；补扫描件 PDF 处理流程（pymupdf 渲染→分批→子代理并行→覆盖率标注）
3. **M5/M11① 降级执行章节**（mode-a-full-preparation.md §3.1.1 后）：目标技能不可用禁止静默跳过——重试→直接撰写+标注降级→报告保留标注；检索降级 MCP 直连并标注
4. **M3 大纲确认强化**（§3.1.8）：必须显式展示各部分核心结论要点（不得只给章节名），未展示直接生成 Word 视为流程违规
5. **M3 六项自检硬门禁化**（§3.1.11 第12条）：逐项 ✅/❌ 显式输出，口头声明视为未执行
6. **M11③ 模式A 执行检查清单**（文件末尾新增）：10 项硬执行节点逐项核对，任一未完成不得交付

## v2.0.0 - 2026-08-10 — 第二批单元 7「律师庭前准备」二合一合并 + 编排重接线

- 合并 `lawd-civlit-courtroom-questioning`（律师庭审发问策略）为**模式B**，原编排器能力成为**模式A 完整庭前准备报告**；对外一个入口，内部按用户意图分流
- SKILL.md 重写为固定六段结构：能力总述 / 触发与分流 / 模式工作流 / 数据源 / 门禁脚本 / 交付物（另附异常处理、参考文件说明、合并与接线说明）
- `name` 保持 `lawd-civlit-preparation` 不变（QwenWork 要求 name = 目录名，库内多处互引指向它）；`name_zh` 由「律师庭前准备综合」改为「**律师庭前准备**」；description 单行重写，覆盖两模式触发词与 NOT for 边界
- **编排重接线**（原 4 个外部子技能中 3 个已变更身份）：
  - 证据分析：改为调用 `lawd-civil-evidence-enhanced` 并显式指定**模式A（综合证据分析）**（原 `lawd-civlit-evidence` 已被合并）
  - 争议焦点分析：改为调用 `lawd-complaint-analyzer` 并显式指定**模式B（争议焦点分析）**、透传 `report_profile`（原 `lawd-civlit-dispute-focus` 已被合并）
  - 庭审发问策略：由跨技能调用改为**本单元内部模式B**，不再外跳
  - 模拟裁判：仍为外部技能 `lawd-civlit-judge-simulation`，保持原样
- 集中检索约定重写：本单元集中做一次检索（`lawd-case-retrieval` / `lawd-regulation-retrieval`），产出统一检索结果包并随每次子能力调用显式传入、要求跳过重复检索；内部模式B 复用同一结果包；追加检索只能由本单元发起
- 检索降级按 A 档（报告用于开庭）：未取得检索结果时不得罗列法条、不得虚构案例、不得用 WebSearch 兜底，相关章节就地标注「未取得检索支撑」
- 门禁脚本 `scripts/check_sub_outputs.py` 同步适配新接线：子产物 id 由旧技能名改为功能名（evidence-analysis / dispute-focus / questioning / judge-simulation），新增 source 字段标注产出来源，keywords 加入推荐文件名（`sub-*.md`）与新技能名并保留旧技能名作为历史别名；门禁语义不变（full 4 份齐全才放行，single 只校验 1 份）
- references 归并 courtroom-questioning 3 个文件：`docx-format-standard.md` 与主目录同名文件 MD5 完全一致，未重复迁入；`output-format-template.md` 加前缀迁入为 `questioning-output-format-template.md`；`questioning-knowledge-base.md` 按原名迁入
- 被吸收目录 `lawd-civlit-courtroom-questioning` 保持原样暂不删除（待验收后决定去留）

## v1.0.0 - 2026-08-03

- 合规整改：纳入 QwenWork-Legal-Skill 统一治理，补建 CHANGELOG 版本记录
- 此前历史变更详见 git 提交记录
