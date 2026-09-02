---
name: criminal-family-guide
version: 1.0.0
name_en: criminal-family-guide
description: 生成面向家属的刑事案件阶段指引、脱敏会见反馈或阶段工作进展函。触发：给家属说明进展、会见反馈、家属注意事项、阶段告知。不触发：提交公检法的正式文书；律师内部沟通策略调用 criminal-communication-guide。
---

<!-- Copyright © 深圳市法大大网络科技有限公司 版权所有 | Author: 法大大法律AI产品线 -->

## 确定性渲染与回执

1. 执行前核对 manifest 版本、`render_html.py`、`validate_html.py` 和所选 HTML 模板；失败即 `BLOCKED`。
2. 只填充选定模板的内容槽，调用 `render_html.py` 将真实 HTML 写入当前 `matter_id` 目录，不覆盖模板源文件。
3. 调用 `validate_html.py` 解析实际文件，检查案件路径、HTML 结构、可见正文、未填占位和内部控制标记。
4. 返回 `skill_id`、版本、入口、`doc_type`、`template_id`、绝对路径和渲染状态；仍有非关键占位时使用 `PASS_WITH_WARNINGS`。
5. 家属稿继续执行既有脱敏规则；渲染成功不证明敏感披露检查已经通过。

## 家属材料模板

- 脱敏会见反馈：[sanitized-meeting-feedback.md](sanitized-meeting-feedback.md)
- 阶段工作进展：[family-progress-update.md](family-progress-update.md)

原有 pocket/minimal/standard HTML 程序指引继续保留。家属稿不得包含供述、卷宗摘录、同案犯供述或会见策略。

# 刑事家属程序指引

> **版本**: v2.1.0 | **风险等级**: L1 | **类型**: T-content | **严肃度**: I-Practical
>
> **核心定位**：三阶段程序须知（侦查/审查起诉/审判）× 三档深度（速览卡半页/极简1页/标准2-3页）——让家属搞清楚"现在处于哪个阶段、接下来会发生什么、我能做什么不能做什么"
>
> **设计原则**：家属在极端焦虑下阅读，文字越少越好，图表越多越好。能用表格就不用文字，能用图标就不用句子，能折叠就不展开。
>
> **蓝本依据**：《刑事诉讼法》第34/39/44/67/68/74/91/93/95/97/156/157/158/172/208/227/230条；《看守所条例》第28/30/31条；《公安机关办理刑事案件程序规定》
>
> **输出格式**：HTML（可直接浏览器打开→打印→交付家属），I-Practical/律所品牌自动注入

---

## 模块一：法律合规声明

1. **管辖范围**：中国大陆（不含港澳台）刑事程序家属指引
2. **输出性质**：所有输出为**程序性普及指引**，不构成法律意见，不替代律师咨询
3. **法条检索契约**：`requires_legal_retrieval: true`。核心法条须联网核实现行有效性
4. **禁止保证结果**：全文不得出现"一定""保证""肯定能"等承诺性措辞
5. **免责声明不可省略**：每份输出必须包含"仅供参考·不构成法律意见"声明
6. **无罪推定**：所有表述必须体现"未经法院判决不得确定有罪"，禁止使用"罪犯"等有罪推定表述
7. **家属行为红线**：严禁建议或暗示家属实施串供、毁灭证据、干扰证人等违法行为
8. **信息密度约束**：速览卡≤300字/极简≤800字/标准≤1500字；每板块不超字数上限
9. **信息去重**：每个信息点只出现一次，取保详情归O9/禁止行为详情归O5/时间详情归O6

---

## 模块二：快速开始

### 最简用法

```
侦查阶段，标准版，嫌疑人张三，诈骗罪
```

### 速览卡

```
侦查阶段，速览卡
```

### 含家属关切

```
审查起诉阶段，标准版，家属想知道能不能取保
```

> 详细规则见 [family-behavior-rules.md](./family-behavior-rules.md)

---

## 模块三：核心参数

### 关键输入

> 详细规格见 [timeline-data.md](./timeline-data.md)

| 类型 | 参数 | 必填 | 说明 |
|------|------|------|------|
| 必填 | `stage` | 是 | 诉讼阶段（侦查/审查起诉/审判） |
| 必填 | `depth` | 是 | 输出深度（速览卡pocket/极简版minimal/标准版standard） |
| 推荐 | `suspect_name` | 否 | 嫌疑人姓名/称谓 |
| 推荐 | `charge` | 否 | 涉嫌罪名 |
| 选填 | `family_concern` | 否 | 家属特殊关切 |

### 关键输出

> 详细规格见 [html-format-spec.md](./html-format-spec.md)

**三档结构**：

| # | 输出板块 | 速览卡 | 极简版 | 标准版 | 说明 |
|---|---------|--------|--------|--------|------|
| O0 | 速览5图块 | ✅ | ❌ | ❌ | 5个等宽图块横排 |
| O1 | 律所品牌区 | ✅ | ✅ | ✅ | 页眉：Logo + 律所名称 |
| O2 | 当前阶段高亮卡 | ❌ | ✅ | ✅ | 色块标注阶段 + 简要说明 |
| O3 | 律师现在能做什么 | ❌ | ✅表格 | ✅表格 | 工作项表格 |
| O4 | 家属能做什么 | ❌ | ✅表格 | ✅表格 | 行动清单表格（行动🟢） |
| O5 | 家属不能做什么 | ❌ | ✅表格 | ✅表格 | 禁止行为表格（禁止🔴） |
| O6 | 下一步时间节点 | ❌ | ✅流程图 | ✅流程图 | 可视化流程图（关注🟠） |
| O7 | 三阶段时间线总览 | ❌ | ❌ | ✅ | 三阶段色块横排 |
| O8 | 会见规则详解 | ❌ | ❌ | ✅折叠 | 折叠详情，默认关闭（参考⚪） |
| O9 | 取保候审条件 | ❌ | ❌ | ✅对照表 | 条件对照表（关注🟠） |
| O10 | 送物送钱规则 | ❌ | ❌ | ✅折叠 | 折叠详情，默认关闭（参考⚪） |
| O11 | 罪名简介 | ❌ | ❌ | ✅条件折叠 | charge有值时输出（参考⚪） |
| O12 | 常见问题 Q&A | ❌ | ❌ | ✅折叠 | 5个通用+1-2定制，默认关闭（参考⚪） |
| O13 | 律所联系方式 | ✅ | ✅ | ✅ | 页脚：律所名+联系方式留白 |
| O14 | 免责声明 | ✅ | ✅ | ✅ | "仅供参考·不构成法律意见" |

---

## 模块四：工作流概览

> 详细流程见 [family-behavior-rules.md](./family-behavior-rules.md)

```
P0.5 律所配置检查 → P1 输入验证 → P2 阶段+深度路由 → P3 法律知识检索 → P3.5 板块内容规划 → P4 HTML 生成 → P5 质量自检
```

### 降级机制

SOFT_DEGRADED = C + D + G：
- **[C]** 核心（不可降级）：阶段识别 + 家属能做/不能做 + 时间节点
- **[D]** 增强（可降级）：罪名简介 + 定制Q&A + 时间线图
- **[G]** 格式（可降级）：HTML → Markdown

### 协作关系

| 技能 | 关系 | 说明 |
|------|------|------|
| criminal-bail-application | 弱上游 | 取保候审申请的详细流程 |
| criminal-meeting-guide | 弱上游 | 会见提纲和注意事项 |
| criminal-communication-guide | 平行 | 公检法沟通策略 |
| criminal-custody-review | 弱上游 | 羁押必要性审查申请 |

### 文档索引

| 文件 | 职责 | 加载方式 |
|------|------|---------|
| [timeline-data.md](./timeline-data.md) | 输入时间线与阶段数据 | 🔴 必须（P1 每次加载） |
| [html-format-spec.md](./html-format-spec.md) | 输出格式规格 | 🔴 必须（P4 每次加载） |
| 法律依据 | 按需调用法规检索 Skill 核验 | 🔴 必须（P3 每次加载） |
| [family-behavior-rules.md](./family-behavior-rules.md) | 工作流与披露规则 | 🔴 必须（全程加载） |
| [html-format-spec.md](./html-format-spec.md) | HTML 排版规范 | 🟡 条件（P4 时加载） |
| [family-behavior-rules.md](./family-behavior-rules.md) | 家属行为规则清单 | 🟡 条件（O4/O5 时加载） |
| [timeline-data.md](./timeline-data.md) | 三阶段时间线数据 | 🟡 条件（O6/O7 时加载） |
| [html_pocket.html](html_pocket.html) | 速览卡 HTML 模板 | 🟡 条件（depth=pocket 时加载） |
| [html_minimal.html](html_minimal.html) | 极简版 HTML 模板 | 🟡 条件（depth=minimal 时加载） |
| [html_standard.html](html_standard.html) | 标准版 HTML 模板 | 🟡 条件（depth=standard 时加载） |
| [example-001.md](example-001.md) | 标准示例：侦查阶段标准版 | 🟢 参考（不加载，按需查阅） |
| [example-002.md](example-002.md) | 标准示例：速览卡 | 🟢 参考（不加载，按需查阅） |
| [example-003.md](example-003.md) | 标准示例：审查起诉+标准版+家属关切 | 🟢 参考（不加载，按需查阅） |
| [SKILL.md](./SKILL.md) | 使用说明 | 🟢 参考（不加载，按需查阅） |

<!-- Copyright © 深圳市法大大网络科技有限公司 版权所有 | Author: 法大大法律AI产品线 -->
