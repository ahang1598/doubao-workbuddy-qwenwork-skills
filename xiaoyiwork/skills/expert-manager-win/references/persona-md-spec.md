# persona 正文规范

persona 目录下的 `*.md` 是专家的 **identity 正文**，会被 agent-core
`_build_persona_prompt_sections` 全部读取、按相对路径排序拼接，作为 `identity`prompt section（priority 10）注入系统提示词。

> jiuwenswarm 的 persona.md **没有 frontmatter**（与某些体系的 agent-md 不同）。
> persona 是纯正文，整段作为人设指令注入。工具/skills 由 manifest 声明，不在 persona 里。

## 加载行为（权威：extension_loader.py:_build_persona_prompt_sections）

1. 取 `persona.dir`（包内相对目录）
2. `rglob("*.md")` 收集所有 markdown 文件
3. 按相对路径字典序排序
4. `"\n\n".join(...)` 拼接全部内容
5. 包成 `PromptSectionSpec(name="identity", content={cn, en}, priority=10)`

> 多个 .md 会被合并进**同一个** identity section；不要靠分文件做"多段身份"，它们会按文件名排序后平铺拼接。

---

## 一、单专家 persona

- 位置：`<expert_id>/agents/<expert_id>.md`（`persona.dir` 固定为 `"agents"`）
- 内容：角色人设、核心能力、工作流程、输出规范、注意事项
- 模板：`templates/agent-persona.md`

### 正文结构：普通 Agent

```markdown
# {角色名} · {花名}

{开篇两三句：这个角色是谁，为用户解决什么问题}

## 核心能力
1. **{能力 1}**：{一句话说明}
2. **{能力 2}**：{一句话说明}
3. **{能力 3}**：{一句话说明}

## 工作流程
1. {第一步}
2. {第二步}
3. {第三步}

## 输出规范
- {对产出形态与格式的要求}
- {……}

## 注意事项
- {边界、禁忌与兜底行为}
```

---

## 二、专家团 persona

### leader persona（主理人身份）

- 位置：`agents/leader/persona/leader-persona.md`
- 内容：主理人身份 + 团队成员表 + SOP 阶段 + 协作机制
- **额外**：leader 同级还必须有 `AGENT.md`（团队级铁律，注入
  `agent_group_leader_rules` section, priority 15）
- 两者关系：**persona = "我是谁、负责什么编排"；AGENT.md = "团队怎么协作"**

### leader 正文模板

```markdown
# {团队名} 主理人 · {花名}

{开篇：这支团队由我统筹，交付什么、怎么协作}

## 团队阵容

### {小组名}
| 成员 id | 花名 | 分工 |
|---|---|---|
| {member-id} | {name} | {一句话职责} |

## 标准作业流程（SOP）

### 阶段 1：{名称}
{投入哪些成员；输入与输出说明}

### 阶段 2：{名称}
{同上}

### 阶段 N：终稿
{汇总各成员产出，形成最终交付}

## 协作机制
1. 每阶段由我点名成员进场、派发独立任务
2. 成员交卷后由我汇总，再流向下一阶段
3. 成员之间的信息一律经我中转
4. 专业结论听成员的，我只做编排与汇编
```

> 协作的"硬铁律 + 红线"写进 `AGENT.md`（见 `team-spec.md`），persona 里不重复。

### member persona（成员身份 + 职责）

- 位置：`agents/<member>/persona/<member>.md`
- 内容：成员身份 + 核心能力 + 输出规范 + 回传机制
- **禁止** `AGENT.md`（校验硬规则：非 leader 成员含 AGENT.md 直接报错）

### member 正文模板

```markdown
# {角色名} · {花名}

{开篇：我是谁，在团队里负责哪一段}

## 核心能力
1. **{能力 1}**：{一句话}
2. **{能力 2}**：{一句话}

## 工作流程
1. {步骤}
2. {步骤}

## 输出规范
- {要求}

## 回传约定
分析收尾后，把结构化结论交回主理人，由主理人续转下一阶段。
```

### 成员必备结构

每位成员的 persona 须覆盖六件事：

1. **身份句**：开门见山说清"你是谁"
2. **能力清单**：3-5 条具体本事，不写空话
3. **打法**：内嵌的分析套路，按步骤展开
4. **取数方式**：用哪些命令或工具拿到数据
5. **产出格式**：给定表格或分段模板
6. **交回要求**：结论以何种形式、在什么节点交回主理人

---

## 三、主理人额外要求

### 成员能力清单

主理人 persona 里给每位成员登记三样：
- **成员 id**（= `agents/` 下目录名，调度凭据）
- **看家能力**（3-5 条具体点）
- **典型场景**（哪类问题该点它）

### 预设 Workflow

为高频综合问题预设 Workflow，每个写明三件事：
- **命中问法**：什么样的提问触发它
- **阶段编排**：谁先谁后、谁并行
- **输入输出**：每阶段输入什么、输出什么

数量以真实高频场景为准，宁精勿多。

### 单 agent 直调路由表

| 问法形态 | 走法 |
|---------|---------|
| 单点问题 | 直派对应成员 |
| 复合问题 | 进预设 Workflow |

---

## 四、能独立成 agent 的标准

判据只有一条：**用户会不会绕过团队直接点名问它？**
- 会 → 单独成成员
- 不会 → 并入其他成员

每个成员守住一个完整的"能力域"：域内能力合并收编，域外协作交给主理人编排。

---

## 五、书写要点

1. **正文即提示词**：persona 内容会被原样塞进系统提示词，按"写给 LLM 的人设指令"
   组织，不要写 README 式说明（如"这个文件用来…"）
2. **id 一致**：persona 中提到的角色 id 须与 manifest `agentCard.id` / 成员目录名一致
3. **不要声明 tools**：persona 无 frontmatter，不支持 `tools` 字段（工具由 manifest `tools` 声明）
4. **大段参考资料**：放 `skills/<name>/references/`，不要塞进 persona 正文
5. **调度形态而非实现**：persona 里的协作描述应写"期望的调度形态"（建团→调度→中转→汇编），
   不写"我来 spawn 某成员"的实现细节——实际多角色调度由 swarm runtime 接管（见 `team-spec.md`）
