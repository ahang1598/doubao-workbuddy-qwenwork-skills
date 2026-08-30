---
name: asset-vault
version: 0.3.0
description: |-
  video-director 资产沉淀子模块——从工作流执行过程和产物中沉淀可复用资产。
  由 video-director 在项目交付后内联调用，或用户主动触发。
  核心能力：深度分析产物、提取可复用知识、归类写入汇总层。
---

# 资产沉淀模块

本模块是 video-director 的**资产管理员**，负责：
1. 项目交付后，读取产物进行深度分析，提取可复用知识并写入汇总层
2. 用户主动投喂时，归类写入对应位置
3. 管理和维护汇总层资产，确保知识持续积累和迭代

---

## 资产库数据结构

资产库位于 `{workspace}/asset-vault/`，与技能代码分离：

```
{workspace}/asset-vault/
├── projects/                             # 原始产物（video-director 写入）
│   └── {YYYYMMDD}_{客户名}_{项目简称}/
│       ├── metadata.json
│       ├── step_01_brief.md              # Step 1: 卖点分析 + Brief 报告
│       ├── step_02_creative.md           # Step 2: 创意研判 + 创意方案报告
│       ├── step_03_script.md             # Step 3: 脚本
│       ├── final_script.md              # Step 4: 最终交付脚本
│       └── uploads/                      # 用户上传素材
├── patterns/                             # 汇总资产（本模块产出）
│   ├── script-structures/
│   │   ├── _summary.md
│   │   └── {类型名}.md
│   ├── hooks/
│   │   ├── _summary.md
│   │   └── {Hook类型}.md
│   ├── selling-points/
│   │   ├── _summary.md
│   │   └── {卖点类型}.md
│   ├── creative-techniques/
│   │   ├── _summary.md
│   │   └── {技巧名}.md
│   ├── platform-rules/
│   │   └── {平台名}.md
│   └── methodologies/
│       ├── brief_analysis.md
│       ├── video_analysis.md
│       ├── selling_point_extraction.md
│       └── script_generation.md
├── industry/
│   └── {行业名}/
│       ├── _summary.md
│       ├── audience.md
│       ├── keywords.md
│       ├── competitors.md
│       └── what_works.md
├── benchmarks/
├── inbox/                                # 待分类素材暂存
├── _index/
│   ├── catalog.md
│   ├── by_industry.json
│   ├── by_platform.json
│   └── by_type.json
└── _log/
    ├── operations.md
    ├── writes.jsonl
    ├── knowledge_notes.jsonl
    ├── active_project.json
    └── user_preferences.json
```

---

## 工作流 1：资产汇总（项目交付后执行）

> video-director 交付项目后触发本工作流。优先通过子智能体后台执行（按 video-director §0 平台适配表），降级为内联执行。
> 所有信息从文件系统读取。完整的触发条件（即时/兜底/累积/手动）和中断项目处理策略详见 `references/trigger_strategy.md`。

### Phase 0：确定处理范围

1. 识别目标项目目录：从 `_log/writes.jsonl` 中最近的未分析条目推断目标项目，或从 `_log/active_project.json` 获取
2. 读取 `_log/writes.jsonl` 中 `"analyzed": false` 且属于目标项目目录的条目 → 确定本项目增量文件列表
3. 检查 `inbox/` 是否有未处理素材
4. 检查 `_log/knowledge_notes.jsonl` 是否有 `analyzed=false` 的条目
5. 汇总处理范围：目标项目产物 + inbox 素材 + 散落知识

> 不同任务通过 `projects/{YYYYMMDD}_{客户名}_{项目简称}/` 目录隔离；固定文件名只在单个项目目录内复用，不会把多个任务产物堆在同一路径下。

### Phase 1：确认原始层完整性

1. 读取目标项目目录，检查固定产物文件集合：`metadata.json`、`step_01_brief.md`、`step_02_creative.md`、`step_03_script.md`、`final_script.md`、`uploads/`
2. 缺失文件 → 标注缺失，不阻塞后续分析
3. 确认 `metadata.json` 中 status 已为 `"delivered"` 或 `"interrupted"`；此阶段只做完整性确认，不提前改为 `"completed"`

### Phase 2：自学习分析

1. 读取 `asset-vault/references/analysis_guide.md` 获取分析引导
2. 逐文件阅读目标项目目录下的固定产物文件和 `uploads/` 素材；多个项目之间不得跨目录混读
3. 按三层递进逻辑提取知识：
   - **What**（发生了什么）→ 提取事实
   - **Why**（为什么有效/无效）→ 提炼规律
   - **So What**（对未来的指导）→ 生成可执行建议
4. 同时分析 inbox/ 素材和 knowledge_notes 中的散落知识
5. 核心原则：开放式挖掘，不局限于固定维度

### Phase 3：归类写入汇总层

1. 读取 `asset-vault/references/templates.md` 获取文件模板
2. 读取 `asset-vault/references/naming_convention.md` 获取命名规范
3. **按 video-director 步骤维度归类**：
   - 辅助 Brief 拆解 → 更新方法论/行业知识
   - 辅助视频分析 → 更新方法论/行业 what_works
   - 辅助卖点拆解 → 更新方法论/卖点规律
   - 辅助脚本生成 → 更新脚本结构/Hook/平台规律
   - 和步骤无关的知识 → 独立创建新目录或文件
4. 写入规则：
   - 已有相关文件 → 合并（追加案例、更新结论）
   - 无相关文件 → 按模板新建
   - 方法论文件 → 迭代更新（非追加案例）
5. **写入前必须 `ls` 目标目录**，确认是否已有同主题文件，避免重复创建（如"产品测评型.md"与"产品评测型.md"并存）
6. 归类判断顺序：先看 `_summary.md` → 再扫目录标题 → 做出判断

### Phase 4：更新增量状态与索引

1. 更新 `_log/writes.jsonl` 中已处理条目的 `"analyzed": true`
2. 更新 `_log/knowledge_notes.jsonl` 中已处理条目的 `"analyzed": true`
3. 清理 `inbox/` 中已归类的素材
4. 运行 `asset-vault/scripts/update_index.py --vault-path {workspace}/asset-vault`（自动更新 `_index/catalog.md` + JSON 索引）
5. 更新 Phase 3 中新建/修改过的子目录的 `_summary.md`（确保下次读取时能发现所有已有文件，防止重复创建）
6. 更新目标项目 `metadata.json`：status = `"completed"`，表示交付产物已完成资产沉淀

### Phase 5：回执

向用户简要报告沉淀结果：
- 新建/更新了哪些资产文件
- 处理了多少 inbox 素材和散落知识
- 当前资产库规模
- 如有不确定的归类，标注"待确认"

### Phase 6：补做中断项目（如有）

> 用户中途中断任务或沉淀未执行时，项目会停留在未沉淀状态。本 Phase 负责兜底续做，确保不丢失。

1. 运行 `asset-vault/scripts/scan_interrupted.py --vault-path {workspace}/asset-vault`，获取 status = `"interrupted"` 的项目列表
2. 对每个中断项目（含超 24h 未更新的 `in_progress` 项目）：
   - 对已有产物执行 Phase 2-5（轻量分析，不要求所有文件齐全）
   - **有什么分析什么**，不因缺失文件而跳过整个项目
3. 完成后更新该项目 `metadata.json` 的 status（沉淀完成 → `"completed"`）

---

## 工作流 2：用户主动投喂

**触发词**："帮我存一下"、"存到资产库"、"记录下这个经验"、发送文件/链接等

**步骤：**

1. 分析用户提供的内容，判断与 video-director 哪个步骤相关
2. 读取 `asset-vault/references/templates.md` 获取模板
3. 判断归类（合并已有 or 新建）→ 写入对应位置
4. 运行 `asset-vault/scripts/update_index.py`
5. 回执

---

## 工作流 3：整理（Lint）

**触发**：用户主动要求，或积累 10+ 项目后建议执行。

1. 运行 `asset-vault/scripts/check_consistency.py --vault-path {workspace}/asset-vault`
2. 报告包含：孤立资产、索引不一致、陈旧内容、矛盾结论、缺失汇总
3. 用户确认后逐条处理

---

## 核心规则

### 合并原则

- 只追加，谨慎修改
- 结论谨慎更新（明确证明旧结论需修正时才改）
- 矛盾标注在"分歧"段，不擅删旧结论
- 更新时修改 frontmatter 的 `updated` 和 `source_count`

### 冷启动规则（前 5 个项目）

> 通过读取 `_index/catalog.md` 中的项目总数判断当前是否处于冷启动期。

- 每次沉淀后列出所有新建/更新的文件请用户 review
- 用户负反馈时立即修改
- 第 5 个项目后建议跑一次整理（工作流 3）
- 冷启动期主动问："归类准确吗？有没有漏掉的知识？"

### 摩擦处理

| 情况 | 处理 |
|------|------|
| 不确定归类 | 先新建，标注"待确认"，积累 2-3 条后再合并 |
| 新旧结论矛盾 | 标注分歧，不擅删 |
| 用户说"不用存" | 跳过 |
| 用户说"删掉" | 确认是删除还是归档 |
| 资产库为空 | 跳过读取，正常执行，完成后正常沉淀 |
| 用户中断任务 | metadata status = `"interrupted"`，在 `interruption` 字段记录 `interrupted_at`/`reason`，下次由 Phase 6 补做 |
| Brief 缺维度 | 直接跳过，不追问 |

---

## 开工前自检

> 执行资产操作前必须完成。

1. ✅ 读完本文件（WORKFLOW.md）
2. ✅ 读 `_index/catalog.md` 了解当前资产概况（不存在则视为冷启动）
3. ✅ 读 `_log/operations.md` 最近 5 条操作记录
4. ✅ 运行 `asset-vault/scripts/check_consistency.py --vault-path {workspace}/asset-vault`，发现不一致先补齐再继续

---

## 增量追踪机制

### writes.jsonl 格式

```jsonl
{"ts": "2026-05-20T10:23:00", "action": "create", "path": "projects/项目A/brief.md", "source": "video-director", "project": "项目A", "analyzed": false}
```

### knowledge_notes.jsonl 格式

```jsonl
{"ts": "2026-05-20T14:30:00", "content": "受众偏好轻松幽默风格", "context": "讨论脚本调性时", "project": "项目A", "analyzed": false}
```

### active_project.json 格式

```json
{"current_project": "projects/20260520_客户名_项目", "started_at": "2026-05-20T14:00:00"}
```

video-director 维护此文件：项目开始时设置、交付/中断时清除（设为 null）。
