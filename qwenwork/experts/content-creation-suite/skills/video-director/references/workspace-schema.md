# _workspace 数据交换规范

本文件定义专家团模式下 Agent 间文件交换的目录结构和数据格式。

---

## 目录结构

```
asset-vault/projects/{项目}/
├── _workspace/
│   ├── _state.json
│   ├── _dispatch/
│   │   ├── to_market_strategist.md
│   │   ├── to_creative_director_A.md
│   │   ├── to_creative_director_B.md
│   │   ├── to_creative_director_C.md
│   │   ├── to_scriptwriter.md
│   │   └── to_reviewer.md
│   ├── market_analysis.md
│   ├── creative_A.md
│   ├── creative_B.md
│   ├── creative_C.md
│   ├── draft_script.md
│   └── review_report.md
├── metadata.json
├── step_01_brief.md
├── step_02_creative.md
├── step_03_script.md
├── final_script.md
└── uploads/
```

## 通用文件格式

每个交换文件采用 YAML frontmatter + Markdown body：

```markdown
---
type: market_analysis | creative_proposal | draft_script | review_report | task_dispatch
agent: market_strategist | creative_director_A/B/C | scriptwriter | reviewer | producer
phase: 1 | 2 | 3 | 4
status: draft | final | revision_requested
created_at: "ISO8601"
depends_on: []
schema_version: "1.0"
---

（Markdown 主体）
```

## _state.json

制片人维护的流程状态文件：

```json
{
  "current_phase": 1,
  "phase_status": "dispatching | awaiting_agents | collecting | presenting | awaiting_checkpoint",
  "agents_dispatched": [],
  "agents_completed": [],
  "agents_failed": [],
  "revision_round": 0,
  "max_revision_rounds": 2,
  "checkpoints_passed": [],
  "selected_lenses": [],
  "selected_proposal": null,
  "last_updated": "ISO8601"
}
```

## 产出文件 Schema

### market_analysis.md

**来源**：市场策略师 → 制片人

frontmatter 必填字段：
- `type: market_analysis`
- `agent: market_strategist`
- `phase: 1`
- `status: final`
- `selling_points_count`: int
- `audience_segments_count`: int
- `recommended_platforms`: string[]

body 必含章节：
- **产品核心信息**（表格：产品名/品类/行业/核心差异化）
- **卖点列表**（每个卖点含：类型/论据/匹配度/目标受众段/平台适配/参考来源）
- **受众画像**（每段含：年龄/场景/痛点/决策因素/活跃平台）
- **平台建议**（每平台含：适配理由/形式/时长/策略）

### creative_{A|B|C}.md

**来源**：创意总监 → 制片人

frontmatter 必填字段：
- `type: creative_proposal`
- `agent: creative_director_{A|B|C}`
- `phase: 2`
- `status: final`
- `lens`: string
- `kpi_focus`: string
- `narrative_type`: string
- `platform`: string
- `duration_seconds`: int

body 必含章节：
- **创意主题**（一句话）
- **叙事结构**（表格：段落/内容/时长/情绪）
- **核心卖点运用**（主打 + 辅助卖点及体现方式）
- **钩子设计**（视觉/文案/完播机制）
- **情绪曲线**
- **平台适配**（画幅/节奏/互动设计）
- **风险提示**
- **创意推理**

### draft_script.md

**来源**：编剧 → 制片人

frontmatter 必填字段：
- `type: draft_script`
- `agent: scriptwriter`
- `phase: 3`
- `status: draft | revision_{N}`
- `based_on`: string（来源方案文件名）
- `total_shots`: int
- `total_duration_seconds`: int
- `revision_round`: int

body 必含章节：
- **全局设定**（12字段表格：编号/标题/视频形式/时长/画幅/场景/人物/核心卖点/目标平台/目标受众/情绪基调/参考风格）
- **分镜脚本**（表格：#/景别/时长/画面描述/台词旁白/字幕/音乐音效/运镜）
- **关键帧设计**（开场钩子/产品特写/结尾CTA）
- **拍摄注意事项**（光线/收音/表演指导/AI生成提示）

### review_report.md

**来源**：品控 → 制片人

frontmatter 必填字段：
- `type: review_report`
- `agent: reviewer`
- `phase: 3`
- `status: final`
- `reviewed_file`: string
- `verdict`: "pass" | "has_blockers" | "suggestions_only"
- `blocker_count`: int
- `suggestion_count`: int

body 必含章节：
- **审核结论**（一句话判定）
- **阻断项**（每项含：位置/问题描述/违反规则/建议修改方向）
- **建议项**（每项含：位置/当前内容/建议修改/理由）
- **检查清单**（表格：合规用语/平台规则/品牌一致性/叙事逻辑/卖点完整度/可执行性/平台适配，每项 ✅/⚠️/❌ + 备注）

## 任务派发文件 Schema

所有 `_dispatch/to_*.md` 文件结构：

### 通用 frontmatter

```yaml
type: task_dispatch
target_agent: "{角色}"
phase: "{阶段}"
created_at: "ISO8601"
schema_version: "1.0"
```

### body 结构

1. **任务**：一句话说明任务目标
2. **输入文件**：列出需要读取的文件路径
3. **可用参考资产**：AssetVault 中可读取的参考文件（不存在则跳过）
4. **隔离规则**（如有）：不可读取的文件
5. **输出要求**：指定输出 schema 和目标路径

### 创意总监特有字段

创意总监的派发文件额外包含：

```yaml
lens: "{透镜名}"
kpi_focus: "{KPI}"
```

body 中额外包含：
- **约束**：叙事结构约束 + 开头约束 + KPI导向

### 编剧修订模式

当 `revision_round > 0` 时，派发文件额外包含：
- **修订指令**：品控阻断项列表 + 每项的修改方向
