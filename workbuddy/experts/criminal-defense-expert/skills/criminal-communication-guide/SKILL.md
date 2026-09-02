---
name: criminal-communication-guide
version: 1.0.0
name_en: criminal-communication-guide
description: 生成律师与公安、检察院、法院沟通前的准备提纲、问题清单和沟通记录。触发：办案人员沟通策略、会前准备、沟通记录、潜在关注点。不触发：家属进展函调用 criminal-family-guide；正式法律意见调用对应文书 Skill。
---

<!-- Copyright © 深圳市法大大网络科技有限公司 版权所有 | Author: 法大大法律AI产品线 -->

## 确定性渲染与回执

1. 执行前核对 manifest 版本、`render_html.py`、`validate_html.py` 和 `html-template.html`；失败即 `BLOCKED`。
2. 只填充既有 `CONTENT_SLOT` 和 `MERMAID_SLOT`，调用 `render_html.py` 将真实 HTML 写入当前 `matter_id` 目录，不修改模板硬块。
3. 调用 `validate_html.py` 解析实际文件，检查案件路径、HTML 结构、可见正文、未填占位和内部控制标记。
4. 返回 `skill_id`、版本、入口、`doc_type`、`template_id`、绝对路径和渲染状态；沟通准备稿和记录不得表述为机关正式法律意见。
5. 正式交付或对外发送前由责任子 Agent 按任务场景另行复核，本 Skill 不反向调用 verification。

## 律师工作稿模板

- 沟通准备：[communication-preparation.md](communication-preparation.md)
- 沟通记录：[communication-record.md](communication-record.md)

两类成果均为 `lawyer_working`，不得包装成正式机关提交文书。

# 刑事辩护沟通指引（办案人员）

> **核心定位**：三件套——沟通红线清单（什么绝对不能说）+ 潜台词解读词典（对方话里的弦外之音）+ 力度校准指南（何时说什么力度的话）
>
> **蓝本依据**：《刑事诉讼法》第34/38/39/48/56/67/81/88/95/97/173/177/187/191/198条；《律师法》第37/38条
>
> **输出格式**：纯 HTML（唯一格式），三层信息架构（L1仪表盘→L2详情→L3工具），Mermaid v11 CDN 图表引擎，I-Practical/C-现代轻量视觉方案

---

## 模块一：法律合规声明

1. **管辖范围**：中国大陆（不含港澳台）刑事辩护场景
2. **输出性质**：所有输出为**沟通策略参考**，不替代律师独立判断
3. **法条检索契约**：`requires_legal_retrieval: true`。核心法条须经外部检索确认现行有效性
4. **无罪推定**：所有表述必须体现"未经法院判决不得确定有罪"，禁止"罪犯/确定有罪"等表述
5. **保密义务**：沟通建议须遵守《刑事诉讼法》第48条及《律师法》第38条保密义务，不得建议律师泄露执业中知悉的委托人信息
6. **红线硬约束**：本技能生成的每条话术建议均须通过红线校验，触犯红线自动替换为安全替代
7. **免责声明**：沟通策略供参考，不保证沟通效果，不替代律师当庭应变和独立判断

---

## 模块二：快速开始

### 最简用法

```
我要和办案民警沟通取保候审的事，张某涉嫌诈骗罪，拘留10天了。
```

### 指定场景

```
审查起诉阶段，我需要约见检察官提交不予起诉意见。
李某涉嫌职务侵占罪，已阅卷，认为证据不足。
```

### 完整信息

```
一审阶段，法官要在庭前会议上讨论非法证据排除。
王某涉嫌受贿罪，我方申请排除第3-5份讯问笔录（涉嫌疲劳审讯）。
需要准备：与法官沟通的力度策略、庭前会议发言红线、对方可能的态度预判。
```

> 详细规则见 [interaction-guide.md](./interaction-guide.md)

---

## 模块三：核心参数

### 关键输入

> 详细规格见 [interaction-guide.md](./interaction-guide.md)

| 类型 | 参数 | 必填 | 说明 |
|------|------|------|------|
| 必填 | `communication_target` | 是 | 沟通对象（公安/检察院/法院） |
| 必填 | `case_stage` | 是 | 诉讼阶段（侦查/审查起诉/一审/二审/执行/申诉再审） |
| 推荐 | `communication_goal` | 否 | 沟通目标（信息获取/程序推进/意见说服/权利维护/危机应对） |
| 推荐 | `alleged_crime` | 否 | 涉嫌罪名 |
| 选填 | `key_dates` | 否 | 关键时间节点（拘留日期/批捕日期等） |
| 选填 | `known_situation` | 否 | 已知案件情况 |
| 选填 | `special_scenario` | 否 | 是否命中特殊场景 |

### 关键输出

> 详细规格见 [html-format-spec.md](./html-format-spec.md)

**三层信息架构**：L1 仪表盘（30秒速览）→ L2 详情（深入了解）→ L3 工具（通话中实时查询）

| # | 输出块 | 层 | 可视化 | 说明 |
|---|--------|-----|--------|------|
| D1 | 通信策略总图 | L1 | Mermaid `flowchart TD` | 一图看懂沟通全貌 |
| D2 | 沟通风险热力图 | L1 | CSS Grid 6×3 | 一眼看到雷区分布 |
| D3 | 今日行动卡片 | L1 | 3 色优先级卡 | 今天必须做的 3 件事 |
| D4 | 准备进度环 | L1 | CSS conic-gradient | 4 类准备完成度 |
| O1 | 沟通前准备清单 | L2 | 折叠卡片墙 | 材料+法条+预判+预案 |
| O2 | 沟通红线清单 | L2 | Mermaid `flowchart LR` + 表格 | 红线决策树+安全替代 |
| O5 | 黄金时间窗口 | L2 | Mermaid `gantt` | 3 轨道甘特图 |
| O3 | 潜台词解读词典 | L3 | Mermaid `flowchart TD` + 表格 | 决策树+置信度表格 |
| O4 | 力度校准指南 | L3 | CSS 光谱条 | 渐变色条+▲推荐位置 |
| C1 | 特殊场景应对 | L3 | Mermaid `flowchart TD` ×2 | 场景流程图+步骤话术 |
| O7 | 沟通记录模板 | L3 | 表单式 | 可打印填写 |

---

## 模块四：工作流概览

> 详细流程见 [interaction-guide.md](./interaction-guide.md)

```
Phase 1: 场景识别与信息采集 [L1]
  → 识别沟通对象/诉讼阶段/沟通目标 → 路由到场景策略
  → 门控 IG-A：场景确认（首次必交互）
Phase 2: 沟通策略生成 [L2]
  → 加载红线+潜台词+力度 → 生成O1-O4
Phase 3: 时间窗口与特殊场景适配 [L2]
  → 计算黄金时间窗口(O5) → 检测特殊场景(C1)
Phase 4: 风险审查与安全校验 [L2]
  → 红线交叉校验 → 力度风险评估 → 安全校验通过
Phase 5: HTML 输出组装 [L1]
  → 加载 html-template.html → 填充 6个MERMAID_SLOT → Mermaid语法自检[🔴阻断]
  → 填充 22个CONTENT_SLOT（含热力图/进度环/光谱条/行动卡片/降级文本）→ 验证无遗漏
Phase 6: 交互跟进（可选）[L1]
  → 根据反馈调整策略
```

### 降级机制

SOFT_DEGRADED：信息不足时输出 C+D+G 最小骨架：
- **[C]** 待补充事实清单（缺失的沟通对象/阶段/案件信息）
- **[D]** 治理与禁区声明（输出局限+保密边界）
- **[G]** 可执行下一步（补充信息后重新生成）

### 协作关系

| 技能 | 关系 | 说明 |
|------|------|------|
| criminal-bail-application | 弱上游 | 取保申请书是沟通弹药 |
| criminal-arrest-review | 弱上游 | 不批捕意见书是核心弹药 |
| criminal-custody-review | 弱上游 | 羁押审查申请是弹药 |
| criminal-meeting-guide | 平行信息源 | 会见是信息来源 |
| criminal-case-strategy | 弱上游 | 全案策略决定沟通重点 |

### 文档索引

| 文件 | 职责 |
|------|------|
| [interaction-guide.md](./interaction-guide.md) | 输入与交互规格 |
| [html-format-spec.md](./html-format-spec.md) | 输出格式规格 |
| 法律依据 | 按需调用法规检索 Skill 核验 |
| [interaction-guide.md](./interaction-guide.md) | 工作流详述 |
| [html-template.html](html-template.html) | HTML 输出模板 v2.2.0（三层架构+6个MERMAID_SLOT+Mermaid CDN+折叠侧栏+保密水印） |
| [html-format-spec.md](./html-format-spec.md) | HTML 排版规范 v2.2.0（三层架构+Mermaid规则+CSS组件+占位符清单） |
| [interaction-guide.md](./interaction-guide.md) | 交互门控策略 |
| [redline-catalog.md](./redline-catalog.md) | 沟通红线清单 |
| [subtext-dictionary.md](./subtext-dictionary.md) | 潜台词解读词典 |
| [preparation-checklist.md](preparation-checklist.md) | 沟通前准备清单模板 |
| [communication-record.md](communication-record.md) | 沟通记录模板 |
| [scenario-routing.md](scenario-routing.md) | 场景路由表 |
| [example-001.md](example-001.md) | 标准示例：侦查阶段取保沟通 |
| [example-002.md](example-002.md) | 标准示例：审查起诉检察官约见 |
| [SKILL.md](./SKILL.md) | 使用说明 |

<!-- Copyright © 深圳市法大大网络科技有限公司 版权所有 | Author: 法大大法律AI产品线 -->
