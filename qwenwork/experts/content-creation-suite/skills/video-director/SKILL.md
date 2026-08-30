---
name: video-director
version: 0.8.0
description: 自动化视频编导工作流：解析产品资料、发散创意方案并生成标准化分镜脚本。当用户提供产品资料并要求"生成视频方案"、"写短视频脚本"或"拆解产品卖点"时触发。不适用于纯娱乐剧情片、无产品植入的内容或纯文案排版需求。
type: project
---

# AI 视频编导 (AI Video Director)

本技能通过分步执行实现视频创作流程的自动化。用户提供原始产品资料（产品说明书、文档、文字描述等），系统经过 **产品解析 → 创意方案 → 视频脚本** 三个阶段，产出可执行的视频脚本设计文档。

---

## 0. 外部依赖

### 资产管理子模块（内置）

团队沉淀数据的存储与检索。通过文件系统直接读写交互：

- **读取**：每步开始前读取资产库中的沉淀数据作为参考
- **写入**：步骤产物写入项目目录 + 追加 `_log/writes.jsonl`
- **沉淀**：项目交付后执行 asset-vault 工作流 1（优先 `spawn_agent` 后台执行，降级为读取 `asset-vault/WORKFLOW.md` 内联执行）

资产库位于 `{workspace}/asset-vault/`，详细结构和工作流参考 `asset-vault/WORKFLOW.md`。

### Agent 技能（可选）

| 技能 | 用途 | 缺失时降级 |
| :--- | :--- | :--- |
| `content-breakdown` | 竞品视频深度拆解 | 跳过，依赖用户手动提供 |
| `smart-web-search` | 爆款趋势搜索 | 跳过，依赖资产库沉淀或内置模板 |

### 子智能体调用

工作流中通过 `dispatch_subagent` 函数派发子智能体，函数定义见 §3.5。

- **数据交换**：通过 `_workspace/` 目录文件系统，格式见 `references/workspace-schema.md`
- **Prompt 模板**：`references/agent-prompts/` 下各角色文件
- **降级**：`spawn_agent` 不可用时，专家团模式回退到标准模式（单 Agent 完成全部工作）；资产沉淀回退到读取 `asset-vault/WORKFLOW.md` 内联执行

### 降级策略

资产库为空或文件不存在时，绝不阻塞流程：

- 资产库未初始化/文件不存在 → 跳过读取，使用 `references/methodologies.md` 内置方法论
- 无匹配的沉淀资产 → 使用对应的 `references/` 内置规则文件兜底

---

## 1. 项目生命周期

### 项目创建（Step 0 确认后）

1. 创建项目目录：`{workspace}/asset-vault/projects/{YYYYMMDD}_{客户名}_{项目简称}/`
2. 写入 `metadata.json`：

```json
{
  "status": "in_progress",
  "client": "",
  "project": "",
  "industry": "",
  "platform": "",
  "date": "YYYY-MM-DD",
  "updated_at": "YYYY-MM-DDTHH:mm:ss",
  "content_goal": "",
  "tags": []
}
```

> `updated_at` 每次写入步骤产物时必须同步更新，供启动检查判断"超 24h 未更新"。

**status 状态机（统一定义，全流程遵循）：**

| status | 含义 | 设置时机 | 后续 |
| :--- | :--- | :--- | :--- |
| `in_progress` | 进行中 | 项目创建 | 交付/中断/放弃时流转 |
| `delivered` | 脚本已交付 | Step 4 交付完成 | 触发沉淀 → `completed` |
| `completed` | 已沉淀 | asset-vault 工作流 1 完成 | 终态 |
| `interrupted` | 中断待补做 | 用户中断但保留进度 | Phase 6 补做后 → `completed` |
| `abandoned` | 彻底放弃 | 用户明确不做了 | 终态，不补做 |

中断时在 metadata 追加 `interruption` 字段：`{"interrupted_at": "step_NN", "reason": "..."}`（供 `scan_interrupted.py` 与 Phase 6 读取）。

metadata.json 的字段类型、命名规范、文件名规范详见 `asset-vault/references/format_validation.md`。

3. 更新 `_log/active_project.json`：`{"current_project": "projects/{项目目录}", "started_at": "..."}`
4. 追加 `_log/writes.jsonl`：`{"ts":"...","action":"create","path":"projects/{项目}/metadata.json","source":"video-director","project":"{项目}","analyzed":false}`

### 步骤产物写入（每步完成后）

1. 将步骤产物写入 `{workspace}/asset-vault/projects/{项目}/step_{NN}_{步骤名}.md`
2. 追加 `_log/writes.jsonl`

### 项目交付（最终步骤完成后）

1. 写入 `final_script.md`
2. 更新 `metadata.json`：status = `"delivered"`
3. 清除 `_log/active_project.json`（设 current_project 为 null）
4. **告知用户"脚本已交付"**
5. **必须执行资产沉淀**（详见 §3 Step 4：优先子智能体后台执行，降级为内联）

### 项目中断/放弃

| 场景 | 操作 |
| :--- | :--- |
| 用户明确说"不做了"（彻底放弃） | 更新 metadata status="abandoned"，清除 active_project，不再补做 |
| 用户明确中断但希望保留进度 | 更新 metadata status="interrupted"，在 `interruption` 字段记录 `interrupted_at`（中断步骤）+ `reason`，清除 active_project，待下次由 asset-vault 工作流 1 Phase 6 补做沉淀 |
| 用户切换话题/短暂暂停 | 不做额外操作，metadata 保持 in_progress（超 24h 未更新会被启动检查识别为待补做） |

---

## 1.5 启动检查

技能激活时执行：

1. 读取 `{workspace}/asset-vault/_log/user_preferences.json`（不存在则标记为首次使用）
2. 检查 `{workspace}/asset-vault/_log/active_project.json` 是否有活跃项目
3. 如有 → 读取对应项目的 `metadata.json`，询问用户是否继续
4. 扫描中断/超时项目：运行 `asset-vault/scripts/scan_interrupted.py` 获取 status=`"interrupted"` 的项目列表，同时扫描 status=`"in_progress"` 且 `updated_at` 超 24h 的项目 → 提示用户，执行 asset-vault 工作流 1 Phase 6 补做沉淀（优先子智能体，降级为内联）
5. 检查 `inbox/` 和 `knowledge_notes.jsonl` 中待处理项数量 → 如超阈值则提示

---

## 1.6 对话中行为

- **用户上传素材**：
  - 有活跃项目 → 保存到 `projects/{项目}/uploads/{日期}_{描述}.{ext}`
  - 无活跃项目 → 保存到 `inbox/{日期}_{序号}_{描述}.{ext}`
  - 追加 `_log/writes.jsonl`

- **散落知识捕获**：用户偏好/经验总结/行业认知 → 追加 `_log/knowledge_notes.jsonl`：
  ```jsonl
  {"ts":"...","content":"受众偏好轻松幽默风格","context":"讨论脚本调性时","project":"项目A","analyzed":false}
  ```

  **捕获信号**：
  - 用户表达偏好（"我喜欢轻松幽默的风格"）→ 记录
  - 用户给出经验总结（"上次悬念开头效果特别好"）→ 记录
  - 用户提供行业认知（"竞品都在做种草类内容"）→ 记录
  - 闲聊、情绪表达、与内容创作无关 → 不记录

- **工作偏好记录**：用户表达模式偏好时 → 更新 `_log/user_preferences.json`：
  ```json
  {"default_mode": "fast", "confirmation_level": "minimal", "updated_at": "..."}
  ```
  - `default_mode`: `"fast"` / `"standard"` / `"expert"`
  - `confirmation_level`: `"minimal"`（快速模式，0 次确认） / `"standard"`（卖点 + 脚本 2 次确认）
  - 记录时机：Step 0 用户首次选模式后写入；用户说"以后都快速出"时更新

---

## 1.7 执行控制

**暂停规则：根据 checkpoint 标记决定，非一律暂停。**

1. **checkpoint 步骤**：输出交付物后 **必须暂停**，等待用户确认或反馈
2. **非 checkpoint 步骤**：输出简要进度（1-2 句）后 **自动继续** 下一步
3. 用户随时可打断：任何步骤中收到用户反馈 → 暂停调整

**用户在 checkpoint 的操作：**

- 确认 / "可以" → 继续下一步
- 具体反馈 → 根据反馈调整当前产出，调整完毕后再次暂停
- "跳过" → 跳过当前步骤，进入下一步

**哪些步骤是 checkpoint：** 由工作模式决定，详见 §2。

---

## 2. 工作模式

### 模式选择

**Step 0 明确询问用户**，而非靠触发词猜测：

> "你希望怎么做？"
> 1. ⚡ 快速出脚本（直接交付，不确认）
> 2. 📋 标准多方案比选（2 次确认）
> 3. 🧠 专家团多视角（3 次确认，需子智能体支持）

**辅助信号**（用户初始消息已明确意图时可跳过询问）：
- 快速模式信号："快速出"、"直接给我"、"赶时间"、"先出一版"
- 标准模式信号："正式方案"、"完整流程"、"多出几个方案"、"给甲方看"
- 专家团信号："多角度"、"专家团"、"要3个以上不同方向"
- 单节点信号：用户明确指定"只拆解卖点"或"直接写脚本"

**有偏好记录时**：展示上次选择，"按上次习惯（快速模式）来？还是换一种？"

### 标准模式概览（5 步，2 次确认）

```
Step 0  任务规划 + 选择模式         → 自动继续
Step 1  分析产品 + 拆解卖点         → [checkpoint] 用户确认卖点
Step 2  创意研判 + 生成创意方案      → 自动继续
Step 3  生成脚本                   → [checkpoint] 用户确认脚本
Step 4  交付 + 沉淀               → 一口气完成
```

### 快速模式概览（2 步，0 次确认）

```
Step 0  快速规划              → 自动继续
Step 1  出脚本 + 交付 + 沉淀   → 一口气完成
```

用户有修改意见 → 新一轮迭代，改完重新交付+沉淀。

### 单节点模式

用户明确指定只执行某个阶段时，跳过其余节点。

| 用户意图 | 执行步骤 | 用户需提供的输入 |
| :--- | :--- | :--- |
| "只拆解卖点" | Step 0 → Step 1 | 原始产品资料 |
| "只出创意方案" | Step 0 → Step 2 | 产品卖点列表、目标人群、宣传平台 |
| "直接写脚本" | Step 0 → Step 3 → Step 4 | 创意方案描述（主题、叙事方向、时长等） |

单节点模式下，Step 0 的规划内容简化为确认输入完整度和执行范围。用户提供的输入映射为对应阶段所需的结构化字段，缺失字段主动追问。

### 专家团模式概览（3 Phase，3 次确认）

制片人（本技能）协调多个专家 Agent 并行工作，提供真正的多元视角创意。

```
Phase 1  需求理解    市场策略师分析           → [checkpoint] 用户确认卖点
Phase 2  创意发散    创意总监 ×3 并行         → [checkpoint] 用户选方案
Phase 3  脚本生产    编剧+品控 → 确认 → 交付+沉淀  → [checkpoint] 用户确认 → 一口气完成
```

**与标准模式的区别：**

| 维度 | 标准模式 | 专家团模式 |
| :--- | :--- | :--- |
| 创意来源 | 单上下文生成多方案 | 3个独立上下文各生成1条 |
| 品控审核 | 无独立审核 | 独立品控 Agent 前置审核 |
| 信息隔离 | 无 | 创意总监互不可见 |
| 方案评分 | 无 | 多维度评分排序 |
| 失败处理 | 不适用 | 重试→fallback→退化为标准模式 |

---

## 3. 标准模式工作流

### Step 0: 任务规划 + 模式选择

**输入：** 用户的原始产品资料（产品说明书、文档、文字描述、聊天记录、语音转录等）。

**执行：**

1. 快速扫描产品资料，评估信息完整度
2. 读取 `_log/user_preferences.json`（如有偏好记录）
3. **明确询问用户选择模式**（见 §2 模式选择），或根据辅助信号自动确定
4. 记录/更新 `_log/user_preferences.json`
5. 输出执行计划（1-2 句）："我将用{模式}为你生成脚本，{确认次数}次确认。"
6. 如有信息缺失项 → 追问后再继续

**用户选完模式后自动继续，不额外暂停。**

---

### Step 1: 分析产品 + 拆解卖点 [checkpoint]

**步骤开始前读取参考（文件不存在则跳过）：**

- `{workspace}/asset-vault/patterns/methodologies/brief_analysis.md`
- `{workspace}/asset-vault/industry/{行业}/audience.md`

无文件时使用 `references/brief-parsing-rules.md` 内置规则。

从原始产品资料中提取 7 个结构化字段，结合沉淀数据，拆解出 **至少 6 个**产品卖点。

详细的字段定义和拆解方法论参考 `references/brief-parsing-rules.md`。

若结构化字段有缺失，先向用户追问补全。

输出卖点列表后 **暂停，等待用户操作：**

- **全选** → 确认全部卖点
- **挑选** → 选中部分卖点，未选中的标记为「备选」
- **补充** → 用户提出新卖点方向，补充后重新确认
- **否决** → 替换不满意的卖点后重新确认

此步骤为 **必须 checkpoint**，禁止跳过。

用户确认后，自动按 `references/templates/brief-report.md` 模板生成《产品卖点解析报告》。

**步骤完成后写入：** `{workspace}/asset-vault/projects/{项目}/step_01_brief.md` + 追加 writes.jsonl

**交付物：** 结构化卖点列表 + 《产品卖点解析报告》。

用户确认卖点后 **自动继续** Step 2。

---

### Step 2: 创意研判 + 生成创意方案

**步骤开始前读取参考（文件不存在则跳过）：**

- `{workspace}/asset-vault/patterns/methodologies/video_analysis.md`
- `{workspace}/asset-vault/industry/{行业}/what_works.md`
- `{workspace}/asset-vault/patterns/hooks/_summary.md`
- `{workspace}/asset-vault/patterns/platform-rules/{平台}.md`

无文件时使用 `references/creative-ideation-rules.md` 内置规则。

加载 Step 1 的《产品卖点解析报告》，通过三个渠道进行创意研判：

1. **沉淀数据** — 上方读取到的行业模式、受众特征、平台基准
2. **竞品调研**（可选）— 用户提供竞品链接时，调用 `content-breakdown` 和 `smart-web-search`
3. **爆款拆解**（可选）— 提取爆款的钩子类型、情绪曲线、转化链路

详细的研判策略参考 `references/creative-ideation-rules.md`。

基于卖点和研判结论，生成 **至少 3 条**差异化创意方案。每条方案含 12 个字段，且必须覆盖至少 3 种叙事类型。

详细的方案字段和叙事类型规则参考 `references/creative-ideation-rules.md`。

自动按 `references/templates/creative-report.md` 模板生成《创意方案报告》。

**步骤完成后写入：** `{workspace}/asset-vault/projects/{项目}/step_02_creative.md` + 追加 writes.jsonl

**交付物：** 完整的《创意方案报告》。

输出方案后 **自动继续** Step 3。用户如需调整方案可在 Step 3 确认脚本时反馈。

---

### Step 3: 生成脚本 [checkpoint]

**步骤开始前读取参考（文件不存在则跳过）：**

- `{workspace}/asset-vault/patterns/methodologies/script_generation.md`
- `{workspace}/asset-vault/patterns/script-structures/_summary.md`
- `{workspace}/asset-vault/patterns/hooks/_summary.md`
- `{workspace}/asset-vault/patterns/platform-rules/{平台}.md`
- `{workspace}/asset-vault/patterns/creative-techniques/_summary.md`

无文件时使用 `references/script-generation-rules.md` 内置规则。

为每条确认的创意方案独立生成视频脚本。根据用户需求选择输出格式：

**口播脚本格式（默认）**：适用于真人口播、直播引流、种草带货。输出场景设定 + 完整口播文稿。

**分镜脚本格式**：适用于多场景叙事、剧情短片、品牌 TVC、产品推广。输出全局设定 + 分镜表 + 关键帧 + 拍摄注意事项。

默认使用口播脚本格式。仅当用户明确要求分镜脚本（如"要分镜表"、"出分镜"、"给拍摄团队用"、"要完整分镜"）时使用分镜格式。

详细的字段定义和示例参考 `references/script-generation-rules.md`。

**步骤完成后写入（暂停前先落盘，防止中断丢失草稿）：** `{workspace}/asset-vault/projects/{项目}/step_03_script.md` + 追加 writes.jsonl

用户在 checkpoint 反馈修改后，覆盖更新 `step_03_script.md` 并再次追加 writes.jsonl。

输出脚本后 **暂停，等待用户操作：**

- **确认** → 进入交付
- **修改单条** → 对特定镜头或台词提出修改意见
- **调整全局** → 修改视频形式、时长等全局参数
- **换方案方向** → 回到创意层面调整（此时重新执行 Step 2-3）

此步骤为 **必须 checkpoint**，禁止跳过。

**⏸ 暂停，等待用户完成确认。**

---

### Step 4: 交付 + 资产沉淀

> **强制规则**：用户确认脚本后，你**必须完成交付并触发沉淀**，不得中途停止。

**交付流程：**

1. 写入 `{workspace}/asset-vault/projects/{项目}/final_script.md` + 追加 writes.jsonl
2. 更新 `metadata.json`：status = "delivered"，补充 script_type/hook_type 等字段
3. 清除 `_log/active_project.json`
4. **告知用户"脚本已交付"**

**资产沉淀（交付后执行，不可跳过）：**

交付完成后，执行资产沉淀（asset-vault 工作流 1，Phase 0-5）：

1. **优先**：后台派发子智能体
   ```
   spawn_agent(
     agent_id        = "general",
     snippet         = "资产沉淀",
     task            = "请读取 asset-vault/WORKFLOW.md，执行工作流 1（资产汇总），目标项目目录：asset-vault/projects/{项目}/。同时处理 inbox/ 中的待分类素材和 _log/knowledge_notes.jsonl 中 analyzed=false 的条目。完成后输出沉淀结果摘要。",
     run_in_background = true
   )
   ```
2. **降级**：`spawn_agent` 不可用时，当前会话读取 `asset-vault/WORKFLOW.md` 内联执行工作流 1
3. 沉淀完成后向用户简要转述（2-3 句）：新建/更新了哪些资产文件，处理了多少条知识

---

## 3.5 专家团模式工作流

专家团模式由制片人（本技能）编排，通过派发子智能体将子任务分配给各专家角色。

### 通用编排规则

| 规则 | 说明 |
| :--- | :--- |
| 串行依赖 | Phase N 完成后才进入 Phase N+1 |
| 重试策略 | 单 Agent 失败最多重试 1 次 |
| Fallback | Agent 失败后制片人自行执行该步骤（退化为标准模式） |
| 审核上限 | 编剧↔品控最多 2 轮循环 |

### dispatch_subagent 函数定义

专家团模式中基于 prompt 模板的子智能体调用通过此函数执行。资产沉淀（Step 4）因不使用 prompt 模板，直接调用 `spawn_agent`，不经此函数。

```
function dispatch_subagent(role, variables, snippet, run_in_background):

  // 1. 构造 task
  task_text = read_file("references/agent-prompts/{role}.md")
  for key, value in variables:
    task_text = task_text.replace("{" + key + "}", value)

  // 2. 调用 spawn_agent
  result = spawn_agent(
    agent_id        = "general",
    snippet         = snippet,
    task            = task_text,
    run_in_background = run_in_background
  )

  // 3. 等待完成（run_in_background=true 时需等待子智能体执行完毕）
  if run_in_background:
    wait_for(result)  // 阻塞直到该子智能体返回

  // 4. 收集并验证结果
  output = read_file(variables.output_path)
  if output 的 frontmatter 缺少必填字段:
    // 重试 1 次：重复步骤 2-3
    result = spawn_agent(同上参数)
    if run_in_background: wait_for(result)
    output = read_file(variables.output_path)
    if 仍然失败:
      return FAILED  // 调用方自行处理降级
  return output
```

> 并行派发时，对每个子智能体分别调用 `dispatch_subagent(run_in_background=true)`。函数内部会各自等待自己的子智能体返回，多个函数并行执行时整体效果为并行等待。

`{项目路径}` = `{workspace}/asset-vault/projects/{YYYYMMDD}_{客户名}_{项目简称}`

### Phase 1: 需求理解

**对应标准模式 Step 1。**

**执行流程：**

1. 读取资产库参考文件，将内容写入 `_workspace/` 供子智能体读取
2. 调用：
   ```
   dispatch_subagent(
     role = "market-strategist",
     variables = {
       output_path:      "{项目路径}/_workspace/market_analysis.md",
       task_description: "分析以下产品资料，拆解至少 6 个卖点",
       input_files:      "- {资产库参考文件路径1}\n- {资产库参考文件路径2}",
       product_brief:    "{用户提供的产品资料原文}"
     },
     snippet = "市场策略师分析产品卖点",
     run_in_background = false
   )
   ```
3. 如返回 FAILED → 制片人自行完成分析（按标准模式 Step 1 执行）
4. 呈现卖点列表给用户

**⏸ Checkpoint: 用户确认卖点。**

用户确认后：
- 将卖点报告写入项目目录的 `step_01_brief.md`（与标准模式同名，便于沉淀统一扫描；`_workspace/market_analysis.md` 仅作子智能体间中间交换） + 追加 writes.jsonl

### Phase 2: 创意发散

**对应标准模式 Step 2。**

**透镜选择逻辑（制片人执行，不需要额外派发）：**

从 market_analysis 中提取行业、平台、产品类型、卖点类型分布，按以下规则选 3 个透镜：

| 产品特征 | 优先透镜 |
| :--- | :--- |
| 功能型/工具类产品 | 痛点解决型 |
| 需要高完播率 | 反转/意外型 |
| 参数敏感受众（科技/数码） | 证言/测评型 |
| 品牌向/生活方式 | 情感共鸣型 |
| 知识/教育类 | 教程/干货型 |
| 需要出圈传播 | 社会议题型 |

选 3 个覆盖不同 KPI 方向的透镜。透镜配置详见 `references/agent-prompts/creative-director.md` 透镜配置表。

**执行流程：**

1. 选择 3 个透镜（从透镜配置表中选取，覆盖不同 KPI 方向）
2. 对 A/B/C 三个创意总监分别调用（全部设 run_in_background=true 并行派发）：
   ```
   // 对每个透镜 X ∈ {A, B, C}，从透镜配置表查出对应值后调用：
   dispatch_subagent(
     role = "creative-director",
     variables = {
       lens:                 "{透镜名}",
       lens_philosophy:      "{透镜哲学}",
       narrative_constraint: "{叙事约束}",
       hook_constraint:      "{开头约束}",
       kpi_focus:            "{KPI}",
       narrative_type:       "{叙事类型}",
       X:                    "A",  // 或 B、C
       platform:             "{目标平台}",
       duration:             "{时长秒数}",
       output_path:          "{项目路径}/_workspace/creative_A.md",
       task_description:     "基于市场分析和确认卖点，生成一条完整的视频创意方案",
       input_files:          "- {项目路径}/_workspace/market_analysis.md"
     },
     snippet = "创意总监A-{透镜名}",
     run_in_background = true
   )
   ```
   全部派发后等待所有结果返回。
3. 失败处理：
   - ≥2 个成功 → 直接评分
   - 1 个成功 → 制片人自行用剩余透镜补足
   - 全失败 → 制片人自行生成 3 个方案（退化为标准模式 Step 2）
4. 评分排序（制片人执行）：
   - 维度：完播潜力 / 互动潜力 / 转化潜力（各 1-5 分）
   - 加权：方案对应 kpi_focus 的维度权重 ×1.5
   - 排序：加权总分降序
5. 呈现：方案内容 + 评分 + 推荐理由

**⏸ Checkpoint: 用户选择方案。**

用户选择后：
- 将创意方案报告写入项目目录的 `step_02_creative.md`（`_workspace/creative_{A|B|C}.md` 仅作中间交换） + 追加 writes.jsonl

### Phase 3: 脚本生产

**对应标准模式 Step 3。**

**执行流程：**

1. 从资产库读取脚本结构参考，写入 `_workspace/`
2. 派发编剧：
   ```
   dispatch_subagent(
     role = "scriptwriter",
     variables = {
       output_path:      "{项目路径}/_workspace/draft_script.md",
       script_format:    "oral",  // 或 "storyboard"（用户要求分镜时）
       task_description: "基于选定创意方案生成完整视频脚本",
       input_files:      "- {项目路径}/_workspace/creative_{选定方案}.md\n- {项目路径}/_workspace/market_analysis.md"
     },
     snippet = "编剧生成脚本",
     run_in_background = false
   )
   ```
3. 如返回 FAILED → 制片人自行写脚本（按标准模式 Step 3）
4. 派发品控：
   ```
   dispatch_subagent(
     role = "reviewer",
     variables = {
       output_path:      "{项目路径}/_workspace/review_report.md",
       reviewed_file:    "draft_script.md",
       task_description: "审核以下脚本的合规性和质量",
       input_files:      "- {项目路径}/_workspace/draft_script.md\n- {项目路径}/_workspace/market_analysis.md"
     },
     snippet = "品控审核脚本",
     run_in_background = false
   )
   ```
5. 如返回 FAILED → 制片人自行做简单合规检查
6. 判断 verdict：
   - `pass` → 直接呈现脚本
   - `suggestions_only` → 呈现脚本 + 建议项标注
   - `has_blockers` → 进入修订循环
7. 呈现脚本前先落盘：将终稿写入项目目录的 `step_03_script.md`（`_workspace/draft_script.md` 仅作中间交换；防止 checkpoint 中断丢失草稿） + 追加 writes.jsonl

**修订循环（最多 2 轮）：**

1. 派发编剧修订：
   ```
   dispatch_subagent(
     role = "scriptwriter",
     variables = {
       output_path:      "{项目路径}/_workspace/draft_script.md",
       script_format:    "{同首次}",
       task_description: "根据品控阻断项修订脚本。阻断项列表：\n{逐条列出阻断项及修改方向}",
       input_files:      "- {项目路径}/_workspace/draft_script.md\n- {项目路径}/_workspace/review_report.md"
     },
     snippet = "编剧修订脚本-第{N}轮",
     run_in_background = false
   )
   ```
2. 派发品控审核修订稿：
   ```
   dispatch_subagent(
     role = "reviewer",
     variables = {
       output_path:      "{项目路径}/_workspace/review_report.md",
       reviewed_file:    "draft_script.md",
       task_description: "审核修订后的脚本",
       input_files:      "- {项目路径}/_workspace/draft_script.md\n- {项目路径}/_workspace/market_analysis.md"
     },
     snippet = "品控审核修订稿-第{N}轮",
     run_in_background = false
   )
   ```
3. 如仍有阻断项且 round < 2：重复步骤 1-2
4. 如超过 2 轮仍有阻断项：
   - 用语级修改 → 制片人直接改
   - 结构级问题 → 标注"品控意见"呈现给用户裁决

**⏸ Checkpoint: 用户确认脚本。**

用户确认后，制片人直接执行交付+沉淀（同标准模式 Step 4，一口气完成，不得中途停止）：
1. 写入 `final_script.md` + 更新 `metadata.json` status="delivered"
2. 清除 `_log/active_project.json`
3. **告知用户"脚本已交付"**
4. **执行资产沉淀**（同标准模式 Step 4：优先子智能体后台执行，降级为内联）

---

## 4. 快速模式工作流

当用户选择快速模式，或初始消息明确表达"快速出脚本"、"直接给我分镜"时启用。

### Step 0: 快速规划

快速扫描产品资料，输出一句话方向："我打算用 XX 卖点切入，走 XX 叙事类型，直接出脚本。"

**不暂停，自动继续。**

### Step 1: 出脚本 + 交付 + 沉淀

**一步完成全部工作，不暂停：**

1. 从原始素材提取关键信息（缺失字段用合理默认值，不追问）
2. 拆解 3-4 个核心卖点，写入 `{workspace}/asset-vault/projects/{项目}/step_01_brief.md` + 追加 writes.jsonl
3. 生成 1 条最匹配的创意方案，写入 `{workspace}/asset-vault/projects/{项目}/step_02_creative.md` + 追加 writes.jsonl
4. 生成脚本（默认口播脚本格式；用户要求分镜时用分镜格式），写入 `{workspace}/asset-vault/projects/{项目}/step_03_script.md` + 追加 writes.jsonl
5. 写入 `{workspace}/asset-vault/projects/{项目}/final_script.md` + 追加 writes.jsonl
6. 更新 `metadata.json`：status = "delivered"
7. 清除 `_log/active_project.json`
8. 告知用户"脚本已交付"
9. **执行资产沉淀**（同标准模式 Step 4：优先子智能体后台执行，降级为内联）

**交付物：** 脚本（即最终产物）。

**用户后续反馈的处理：**

用户有修改意见时，视为新一轮迭代：
1. 根据反馈调整脚本
2. 重新写入 `final_script.md`（覆盖）
3. 重新执行资产沉淀（同标准模式 Step 4）

---

## 5. 适用场景

- 甲方提供了模糊的产品介绍，需要快速出方案
- 知识博主需要根据热点或产品特性批量生产脚本
- 需要将产品资料快速转化为拍摄团队可用的分镜表
- 需要同时支持真人拍摄和 AI 视频生成两种制作方式
- 团队希望积累可复用的内容资产，避免每次从零开始

## 不适用场景

- 纯娱乐向、无明确产品植入的剧情短片
- 需要极高艺术性、非线性叙事的电影级长片脚本
- 仅需简单的社交媒体文案排版
