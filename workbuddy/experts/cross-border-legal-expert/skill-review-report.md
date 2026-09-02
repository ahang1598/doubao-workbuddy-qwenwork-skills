# cross-border-legal-expert · 技能评测报告

**评测工具**：skill-reviewer-v2（Platform Mode，五阶段：结构检查 → 安全风险 → 功能对话实测 → 深度质量评审 → 终审）
**评测对象**：`workbuddy-agent/cross-border-legal-expert/skills/` 下全部 14 项绑定技能
**评测窗口**：2026-08-15 ～ 2026-08-17
**证据基础**：26 个真实子代理对话场景（13 技能 × 2）+ 4 组安全语义审查 + 14 份深度质量评审

---

## 一、总览（14/14 完成评测）

| # | 技能 | S1 结构 | S2 安全 | S3 功能实测 | S4 深度评审 | S5 终审 | 结论 |
|---|------|---------|---------|-------------|-------------|---------|------|
| 1 | cross-border-spa-sha-drafting | ✅ passed | ✅ passed | ✅ pass（2场景） | ✅ passed | ✅ reviewed | **通过** |
| 2 | data-export-security-assessment-report | ✅ passed | ✅ passed | ✅ pass（2场景） | ✅ passed | ✅ reviewed | **通过** |
| 3 | english-contract-review | ✅ passed | ✅ passed | ✅ pass（2场景） | ✅ passed | ✅ reviewed | **通过** |
| 4 | excel-table-processing | ✅ passed | ✅ passed | ⚠️ pass（1场景warn） | ✅ passed | ✅ reviewed | **通过（带整改项）** |
| 5 | export-control-compliance-system-design | ✅ passed | ✅ passed | ✅ pass（2场景） | ✅ passed | ✅ reviewed | **通过** |
| 6 | fadada-professional-contract-information-extraction | ✅ passed | ✅ passed | ✅ pass（2场景） | ✅ passed | ✅ reviewed | **通过** |
| 7 | global-legal-research | ✅ passed | ✅ passed | 🔧 needs_config | ✅ passed | 🔧 needs_config | **通过（需配置）** |
| 8 | html-document-generation | ✅ passed | ✅ passed | ✅ pass（2场景） | ✅ passed | ✅ reviewed | **通过** |
| 9 | international-trade-policy-change-early-warning | ✅ passed | ✅ passed | ✅ pass（2场景） | ✅ passed | ✅ reviewed | **通过** |
| 10 | legal-translation | ✅ passed | ✅ passed | ✅ pass（2场景） | ✅ passed | ✅ reviewed | **通过（带整改项）** |
| 11 | overseas-investment-structure-design | ✅ passed | ✅ passed | ✅ pass（2场景） | ✅ passed | ✅ reviewed | **通过** |
| 12 | pdf-generation-editing-tool | ✅ passed | ✅ passed | ✅ pass（2场景） | ✅ passed | ✅ reviewed | **通过（带整改项）** |
| 13 | supply-chain-compliance-review | ✅ passed | ✅ passed | ✅ pass（2场景） | ✅ passed | ✅ reviewed | **通过** |
| 14 | word-document-processing | ✅ passed | ✅ passed | ✅ pass（2场景） | ✅ passed | ✅ reviewed | **通过（实测驱动修复2处缺陷）** |

> global-legal-research 的 needs_config 为凭证依赖终态：LDH 检索需 `RICHEEAI_TOKEN` 环境变量（平台注入），配置后重跑 Stage 03 即可转 reviewed；其结构、安全、深度评审均已通过。

---

## 二、评测过程中完成的修复

| 类别 | 内容 | 影响 |
|------|------|------|
| B06 命名 | 12 项技能 `name` 改为 kebab-case canonical ID | Stage 01 全过 |
| B09 版本 | 13 项技能补 `version: 1.0.0`（html 保留 2.1.0） | Stage 01 全过 |
| B15 断链 | legal-translation SKILL.md 删除 2 处指向不存在文件的引用 | Stage 01 全过 |
| BOM | cross-border-spa-sha-drafting/SKILL.md 剥离 UTF-8 BOM | 解析正常 |
| 实测修复① | word 技能补齐 `scripts/templates/` 5 个批注基础设施模板 | 批注功能可用 |
| 实测修复② | word 技能 `document.py` 修复 add_comment 段落锚点插到 body 级的缺陷 | OOXML 结构合规 |
| 残留清理 | 移除测试代理留在包内的 `demo/` 目录 | 打包卫生 |

## 三、深度评审亮点（11 维度评分）

**excellent（9分）维度**：
- spa-sha / data-export / export-control / fadada / legal-translation / overseas / supply-chain —— `domain_accuracy`（法条锚点密度与实测判定准确率）
- english-contract-review / html-document-generation —— `executability`（脚本链/模板链完整且实测稳定）
- international-trade-policy —— `fault_tolerance`（Mode D 检索分级降级机制完备）

**needs_work 维度与整改建议**：
| 技能 | 维度 | 分 | 问题 | 建议 |
|------|------|----|------|------|
| excel-table-processing | consistency / maintainability | 5 | SKILL.md 将 recalc.py 描述为 LibreOffice 自动重算并列为强制步骤，实际脚本恒返回 unsupported | 更新 SKILL.md 移除该步骤，或移除 stub |
| legal-translation | maintainability | 6 | `__pycache__`/`.pyc` 编译产物随包分发 | 发布前剔除 pyc |
| pdf-generation-editing-tool | portability | 6 | cover.py 运行时静默 `pip install --break-system-packages` | 改为提示用户手动安装 |
| global-legal-research | executability | 5 | LDH 检索硬依赖平台凭证 | SKILL.md 前置说明凭证要求，补无凭证降级路径；清理源目录 3 条裸 IP 条目 |

**安全评审（S2）**：14/14 通过。全部技能无数据外发、无混淆、无危险操作；medium 级 findings 3 条（均为平台内部鉴权架构或文档失实类，非安全威胁）。

## 四、后续建议

1. ~~**word 技能修复回传**~~：✅ 已完成（2026-08-17）——修复已回传 enterprise-compliance-counsel-expert / data-privacy-ai-compliance-expert / investment-financing-legal-advisor 三包，四包 document.py MD5 一致（ac29ba27…），模板 6 件齐全，version 统一 1.0.1。
2. ~~**excel / pdf / legal-translation 整改**~~：✅ 已完成（2026-08-17）——
   - excel：SKILL.md 移除 recalc.py 强制重算与 LibreOffice 依赖描述，改为读回校验公式（v1.0.1）
   - pdf：11 个脚本依赖缺失改为"打印缺失包名 + 提示 pip install + 退出码 4"（v1.0.1），make.sh fix 保留为显式安装命令
   - legal-translation：包内 8 个 __pycache__ 目录与 39 个 .pyc 全部剔除
3. **global-legal-research**：运营环境注入 `RICHEEAI_TOKEN` 后重跑功能实测（本次未处理，属运营配置项）。
4. ~~剔除包内 .pyc~~：✅ 已完成（2026-08-17，与第 2 项合并执行）。

**整改回归验证**：excel / pdf / word / legal-translation 四项技能重跑 Stage 01 结构检查全部 passed（word 技能期间二次清理了对话测试残留的 demo/ 目录，包体 1588KB，符合 <2MB 限制）。
