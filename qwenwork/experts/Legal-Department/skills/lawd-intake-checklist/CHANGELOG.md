# 变更日志

## v1.4 - 2026-08-11

0811 QwenWork 真机测试整改（第二批 N1-N4，依据执行自评报告 70 分扣分项）：

| 编号 | 修改内容 | 修改原因 |
|------|----------|----------|
| N1 | 新增合同纠纷 4 个子类模板（建设工程/买卖/租赁/服务），建设工程场景问题 6→16 条、材料 5→13 项；置信度校准（精确匹配=high，包含/子类匹配=medium）；通用材料"发货单/收货单"改为场景中性表述 | 真机测试中"建设工程设计合同纠纷"仅得通用 6 问/5 材料且含不适用项，confidence 误标 high |
| N2 | 实现 Step 1.4 场景细化（brief_description 参与子类识别）、Step 2.4 问题逻辑关系（depends_on）、Step 3.4 材料关联关系（related_to） | SKILL.md 声明但脚本未实现的三项核心功能 |
| N3 | 模块结构声明改为实际单文件实现；功能表、工作流程措辞与实现对齐 | 原声明 3 文件结构与"已完全实现"同实际不符 |
| N4 | 输出新增 upgrade_alert（低置信度/多类型交叉/特殊领域/子类未命中四类触发）与 legal_basis 字段 | 脚本无升级提示机制与法律依据输出 |

冒烟测试：4 个内置用例全过，建设工程设计合同场景输出 16 问/13 材料、confidence=medium、depends_on/related_to 正确解析为 Q/M id。

## v1.3 - 2026-08-03

- 自 LS-DEV 分支（commit 50dcb20）移植至 QwenWork-Legal-Skill 目录
- frontmatter 规范化：name 改为 hyphen-case（lawd-intake-checklist），移除 name_en/version 非标字段，description 单行化并补充 TRIGGER/NOT for 触发结构
- 删除库内不存在技能的互引（case-brief-cite、consult-routing、lead-eval-civil、fact-gap-civil）

## v1.2 - 2026-03-16

### 优化摘要

使用 legal-skill-optimizer4.0 对 `intake_checklist` 技能进行优化，实现完整的脚本化生成器，支持8大法律问题类型的自动识别和清单生成。

### 主要修改

| 序号 | 修改内容 | 修改原因 |
|------|----------|----------|
| 1 | 新增 `intake_checklist_generator.py` | 实现脚本化生成器 |
| 2 | 内置8大类型问题模板 | 提供针对性清单 |
| 3 | 内置各类型材料模板 | 完善清单内容 |
| 4 | 实现问题类型自动识别 | 提升用户体验 |
| 5 | 新增置信度计算功能 | 提供质量参考 |
| 6 | 新增输入校验规则 | 增强健壮性 |
| 7 | 补充上下游协作关系 | 明确工作流程 |
| 8 | 补充法律依据引用 | 增强专业性 |

### 脚本化实现详情

#### 核心功能

| 功能 | 说明 | 状态 |
|------|------|------|
| 问题类型识别 | 支持8大法律问题类型自动识别 | ✅ 已实现 |
| 问题清单生成 | 按类型生成定制化问题清单 | ✅ 已实现 |
| 材料清单生成 | 按类型生成定制化材料清单 | ✅ 已实现 |
| 详细程度控制 | 标准/详细两档输出控制 | ✅ 已实现 |
| 置信度计算 | 自动计算匹配置信度 | ✅ 已实现 |
| 结构化输出 | 标准化JSON格式输出 | ✅ 已实现 |

#### 支持的问题类型

| 类型 | 代码 | 问题数 | 材料数 |
|------|------|--------|--------|
| 民事纠纷 | civil_dispute | 5+ | 3+ |
| 劳动争议 | labor_dispute | 8+ | 6+ |
| 婚姻家事 | family_law | 8+ | 6+ |
| 合同纠纷 | contract_dispute | 6+ | 5+ |
| 交通事故 | traffic_accident | 6+ | 6+ |
| 房产纠纷 | real_estate | 5+ | 4+ |
| 知识产权 | ip_dispute | 5+ | 4+ |
| 公司股权 | corporate | 5+ | 4+ |

### 四维分诊结果

| 维度 | 结果 | 说明 |
|------|------|------|
| intent | clear | 核心目标清晰明确 |
| legal_risk | low | 不涉及实体法律判断 |
| dependency | referenced | 引用下游技能 |
| script_signals | strong | 存在强脚本化信号（D4结构化提取） |

### 法律安全标记

substantive_legal_change: false
requires_human_review: false

---

## v1.1 - 2026-03-08

### 初始版本

- 基本的问题类型分类
- 基础的问题和材料模板
- 简单的输出结构

---

*本变更日志由 Legal Skill Optimizer Core v4.0.0-core 自动生成*
