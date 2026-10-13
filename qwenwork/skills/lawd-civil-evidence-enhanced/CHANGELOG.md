# Changelog

## v2.1.0 (2026-08-11) — 三批真机测试整改（M1/M4/M6）

1. **扫描件 PDF 处理流程**（材料深度分析原则）：pymupdf 检测文字层→无文字页渲染 200dpi PNG 视觉读取→>20页分批子代理并行→全部读完才能进分析；无法全读须标注实际覆盖率，禁止静默按已读当全部
2. **关键数字复核扩为 4 项交叉验证清单**：诉称 vs 凭证加总/退费扣减/跨证据一致性/差异必须标注；隐含信息挖掘补"收据客户名与当事人不一致须查明关系"
3. **门禁脚本修复**：①三性列检测改严格匹配（find_three_char_column：列名=关键词+常见后缀，或含"三性"字样），"真实性保障"等描述性列名不再误判为三性表 ②证据编号正则支持复合编号（"被证1-2"不再与"被证1"冲突）；冒烟验证两处修复+标准三性表仍命中

## v2.0.0 (2026-08-10) — 单元 10「综合证据策略」三合一合并

- `name_zh` 由「民事诉讼证据专项分析」改为「**综合证据策略**」；`name` 与目录名保持 `lawd-civil-evidence-enhanced` 不变（QwenWork 要求 name = 目录名，且库内已有互引指向它）
- 原 SKILL.md 仅 112 行，撑不起三合一：**以 `lawd-civlit-evidence` 工作流为骨架重构**，按六段结构重写（能力总述 / 触发与分流 / 模式工作流 / 数据源 / 门禁脚本 / 交付物）
- 合并为一个入口、三种模式：
  - 模式A 综合证据分析（承 `lawd-civlit-evidence`，十二阶段完整工作流，内容最厚）
  - 模式B 质证意见（承本技能原侧重的逐份质证）
  - 模式C 证据链构建与举证要点映射（承 `lawd-evidence-chain-builder`，五层证明链条 + 缺口分级 + 论证节点预检）
- 触发路由按**用户意图**（产出物形态 / 处理对象 / 范围）细分而非按关键词硬切，消解三者触发词重叠；模糊表述默认走模式A 并告知可切换
- 原 `lawd-civlit-evidence` description 中"仅需简单证据目录或逐份质证意见时优先用更专门能力"的外跳逻辑，落地为内部模式路由（证据目录 → C；逐份质证 → B）
- references 归并至 9 项：`lawd-civlit-evidence/references/` 的 3 个文件（output-format-template.md / docx-format-standard.md / cross-examination-depth-guide.md）经 md5 比对与本目录同名文件**逐字节完全一致**，判定为同一份模板的副本，只保留一份；`lawd-evidence-chain-builder` 的 2 个文件加前缀迁入为 `chain-builder-output-template.md`、`chain-builder-example.md`
- 修复旧 SKILL.md 中 4 处失效引用（constraint-principles.md / evidence-chain-methodology.md / evidence-supplementation.md / cross-examination-guide.md 在 references/ 下并不存在），改为写入正文或指向实际存在的文件
- 新增交付门禁 `scripts/validate_evidence_report.py`：证据三性表格结构完整、证据链缺口标注完整、证据编号连续无重复、模式C 无悬空主张；交付前必须运行，未通过禁止交付
- 数据源口径不变：检索能力仍通过兄弟技能 `lawd-case-retrieval` / `lawd-regulation-retrieval` 获得，本技能不直接调用外部数据连接器；`dws doc create` 作为 docx 降级保留
- 被吸收的 `lawd-civlit-evidence`、`lawd-evidence-chain-builder` 两个目录**原样保留**，待验收后由产品决定去留
- 库内其他技能引用「证据链构建」能力时，应改指**本技能模式C「证据链构建与举证要点映射」**

## v1.0.0 (2026-08-03)

- 自《悟空-千问办公法律规划skills》规划表（0611版，P0）的 skill zip 附件移植入库（庭前准备 - 证据）
- 移植时清理 .DS_Store / __pycache__ 等垃圾文件
- 已知问题备案：与库内相关技能存在触发语义重叠，按产品决定暂不调整（详见《规划表vs库内技能差距映射表-20260803.md》）
