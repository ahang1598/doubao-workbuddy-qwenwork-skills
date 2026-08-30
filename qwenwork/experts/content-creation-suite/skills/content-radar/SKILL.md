---
name: content-radar
description: |
  内容雷达：帮**知识博主 / 内容创作者**快速找到"有信息差 + 有受众"的选题，
  输出带评分的推荐报告。所有平台采集走 `mcp-autocli` MCP 服务。
  TRIGGER when: 用户说"内容雷达 / 找选题 / 选题发现 / 找点写什么 / 博主选题"
  等**面向内容创作**的选题诉求（详细触发词见正文「触发与边界」）。
  DO NOT TRIGGER when: 用户要订阅资讯 / 监控舆情（路由到 discovery）；
  提供具体 URL 要拆解爆款（路由到 content-breakdown）；要求发布/编辑已有博文；
  闲聊或通用百科问答。
version: 2.0.0
user-invocable: true
display_name: 内容雷达
metadata:
  routing_priority: high
  conflicts_with:
    - discovery
  preempts:
    - discovery
  depends_on_mcp:
    - mcp-autocli
  depends_on_skills:
    - post-pilot
---

# 内容雷达 Content Radar

**核心公式：好选题 = 信息差（供给侧） + 受众需求（需求侧）**

- **供给侧**：新信息 / 新实践 / 新玩法（用高互动内容作为证据）
- **需求侧**：真实互动 / 提问 / 负面吐槽（数字越大需求越强）

---

## 依赖前置

本技能依赖已注册并 connected 的 `mcp-autocli` MCP 服务（≥ {{VERSION_FROM_POST_PILOT_ASSETS}}，版本号从 post-pilot 的 assets/mcp_autocli-*.whl 文件名中提取）。

版本获取方式：通过 `useSkill post-pilot` 调用获取当前支持的 mcp-autocli 版本号（从 assets 文件名解析）。

- **未安装或版本不足时** → Step 0.0 会自动调用 `useSkill post-pilot` 完成安装
  （wheel + setup + Wukong 注册），全程无需用户介入。
- ⛔ **本技能不内嵌任何 pip install / setup 步骤** —— 装 MCP 是 post-pilot 的活，
  混在一起会破坏职责边界。

---

## 触发与边界

### 强触发词（最高优先级，命中即用本技能，不要走 discovery）

"内容雷达"、"选题发现"、"帮我找选题"、"找选题"、"发现选题"、"找点选题"、
"扫一下最近的热点"、"最近有什么值得做的选题"、"有啥可写的"、"博主选题"、
"知识博主选题"、"自媒体选题"、"内容选题"，支持指定话题（如"内容雷达 MCP"、
"帮我找 AI 工具方向的选题"）。

### 与 discovery 技能的边界（必须遵守）

- 用户说"帮我找选题 / 选题发现 / 内容雷达 / 找点选题写"等**面向内容创作的选题诉求**
  → **必须用本技能**（content-radar），禁止走 discovery（资讯/舆情订阅）。
- discovery 处理的是"订阅 XX 行业资讯 / 监控 XX 品牌舆情 / 查最新新闻"。
- 本技能处理的是"我是博主 / 创作者，想找下一篇可以写什么"。

### 不触发场景

- 用户要求发布/编辑/排版已有博文 → 不触发
- 用户提供具体 URL 要求拆解/分析爆款 → 路由到 `content-breakdown`
- 闲聊、通用百科问答 → 不触发
- 用户想"订阅资讯 / 监控舆情" → 路由到 `discovery`

---

## 流程硬约束（违反即评测失败）

- 必须先按 Step 0.0 用 `mcp_runtime list_servers` + 版本号检测验证 `mcp-autocli` 已 connected 且 ≥ VERSION_FROM_POST_PILOT，
  未满足时自动 `useSkill post-pilot` 完成安装，**禁止**自己跑 pip / setup。
- 必须按 Step 0.1 反问"你这次想找什么方向的选题？"，**禁止自行假设话题**直接采集。
- 必须按 Step 0.2 询问网络环境（能否访问海外），**禁止跳过**——决定平台过滤范围。
- 必须按 Step 0.3 用 ask_human（form + multi_select）让用户**多选**采集平台，禁止跳过。
  仅国内网络时**只展示国内平台**。
- 必须按 Step 0.4 调 `launch_login` 打开 Edge 登录窗口 + `ask_human` 让用户多选确认
  已登录平台，**禁止跳过**；**禁止**自己调任何"登录探测"工具（已不存在）。
- 必须按 Step 1 用 `mcp-autocli` 的 `search` 工具采集所有平台数据。
- 兜底：某平台 search 失败时允许 `web_search` 兜底（标 🟡）；
  RSS 用 `read_url` 抓 XML（标 🟡）。

---

## 前置条件

| 项目 | 要求 |
|---|---|
| MCP 服务 | `mcp-autocli` 已注册到 Wukong 且 status = `connected` |
| mcp-autocli 版本 | wheel ≥ `VERSION_FROM_POST_PILOT`（从 post-pilot 获取版本，含 15 工具 + publish click_draft_btn 等新特性） |
| 登录平台前置 | Edge 浏览器已装，登录态由用户在 `launch_login` 弹出的窗口手动完成 |

未满足任一项 → Step 0.0 会自动 `useSkill post-pilot` 完成安装，装完重检后继续。

---

## 执行流程

### Step 0.0：MCP 安装预检（首步硬约束）

#### 阶段 A：检查 MCP 服务是否注册

```python
mcp_runtime(
  action="list_servers",
  snippet="检查 mcp-autocli 是否已注册"
)
```

判读返回结果中 `mcp-autocli` 这一项：

| 状态 | 处理 |
|---|---|
| 找到且 `status` = `connected`（或 `isActive: true`） | → 阶段 B：版本号检测 |
| 找到但断开 / 未连接 | 尝试一次重连：`mcp_runtime(action="toggle_server", name="mcp-autocli", enabled=false)` → 再 `enabled=true`，仍未连接 → 走安装流程 |
| 未找到 / 重连失败 | → 走安装流程 |

#### 阶段 B：版本号检测

```python
execute_shell(
  command="python -c \"import mcp_autocli; print(mcp_autocli.__version__)\"",
  snippet="检查 mcp-autocli 版本"
)
```

**最低版本要求：从 post-pilot assets 文件名解析的版本号**。比对：

| 状态 | 处理 |
|---|---|
| `installed >= {{VERSION_FROM_POST_PILOT_ASSETS}}`（从 post-pilot assets 文件名解析） | ✅ 进入 Step 0.1 |
| `installed < {{VERSION_FROM_POST_PILOT_ASSETS}}`（从 post-pilot assets 文件名解析） | → 走安装流程 |
| import 失败 | → 走安装流程 |

#### 安装流程（自动，不询问用户）

当阶段 A 或阶段 B 判定需要安装时，**不要终止本技能**，直接触发 post-pilot 完成安装：

```
useSkill post-pilot
```

悟空会路由到 post-pilot skill，post-pilot 的 `references/mcp-install.md` 会执行完整安装：
wheel → setup → Wukong 注册 → 验证。

post-pilot 安装完成后**回到 Step 0.0 重检**，确认 mcp-autocli 已 connected 且版本 ≥ {{VERSION_FROM_POST_PILOT_ASSETS}}（从 post-pilot assets 文件名解析），再进入 Step 0.1。

⛔ **严禁**在本技能里自己跑 `pip install` / `mcp-autocli setup` /
`mcp_runtime add_server` —— 那是 post-pilot 的活，混在一起会破坏职责边界。

**仅当 post-pilot 自身安装也失败时**，输出下方文案并终止：

> 🛑 `mcp-autocli` MCP 服务安装失败（post-pilot 安装流程出错），
> 请检查 Python 环境后重试。

---

### Step 0.1：话题输入（每次必问）

> 你这次想找什么方向的选题？（如：AI 工具、独立开发、出海、前端、设计……）

用户回答后：
1. 根据话题自动生成 `topic`、`keywords`、`keywords_cn`、`scope`、`role`、`style`
2. **覆盖写入**配置文件（无论是否已存在，每次都重新生成）
3. 直接进入 **Step 0.2 网络环境询问**

**配置文件路径**：`{项目根目录}/.content-radar/my-radar.yaml`。
（项目根目录 = SKILL.md 所在目录的上级，即 `content-radar/` 本身。）
参照 `examples/my-radar.yaml.example`。

---

### Step 0.2：网络环境询问（每次必问，决定平台过滤）

> ⛔ **此步骤是强制的**：在话题确认后、平台选择前，**必须主动询问用户当前的网络环境**，
> 禁止跳过。网络环境直接决定 Step 0.3 平台列表展示哪些平台。

使用 `ask_human` 工具询问（**单选**：顶层 `question_type: "single_select"`、内层
`input_type: "single_select"`，questions 数组正好 1 道题）：

```python
ask_human(
  question_type="single_select",
  task_title="网络环境确认",
  questions=[{
    "id": "network",
    "input_type": "single_select",
    "question": "你当前的网络环境能访问海外网站吗？（如 HackerNews / Twitter / Reddit / YouTube 等）",
    "required": True,
    "options": [
      { "label": "可以（有代理/VPN，能访问海外）",      "value": "overseas_ok" },
      { "label": "不行（仅国内网络，访问不了海外）",    "value": "domestic_only", "default": True }
    ]
  }],
  snippet="确认网络环境"
)
```

或在用户消息中已明确表态时直接识别（"仅国内网络"、"能访问海外"、"有代理/VPN"），
无需再次询问。

返回值：`single_select` 模式工具结果**直接是 value 字符串本身**
（`"overseas_ok"` 或 `"domestic_only"`），不是 form 模式的 JSON 包装。

- **`overseas_ok`** → Step 0.3 展示**全部 14 个平台**（含 HN/Lobsters/Dev.to/SO/
  Arxiv/HF/Wikipedia/Twitter/YouTube/Instagram + 4 个国内平台）
- **`domestic_only`** → Step 0.3 **只展示 4 个国内平台**（小红书/B站/抖音/微博），
  **禁止展示**任何标注"需外网"的海外平台

---

### Step 0.3：平台选择（form + multi_select 硬性要求）

> ⛔ **多选硬约束 · 必须 form + multi_select 双层组合**：
> - 顶层 `question_type` **必须** `"form"`。绝对禁止用 `"single_select"` ——
>   会强制降级成单选卡片，用户只能勾一个。
> - 内层 `input_type` **必须** `"multi_select"`，配 `options` + `min_selections: 1` +
>   `max_selections` ≥ options 数。
> - **option 的 `value` 必须是 mcp-autocli 平台英文 key**（如 `xiaohongshu`），
>   `label` 给中文显示名。后续直接把 `answers.platforms` 数组传给 search 的 `platforms`
>   参数。

> ⛔ **平台展示按 Step 0.2 网络环境过滤**：
> - `network = overseas_ok` → 全部 14 个平台
> - `network = domestic_only` → 只展示 4 个国内平台；报告区块 0「本轮说明」
>   必须标注："因仅国内网络，本轮跳过所有海外平台。"

**`overseas_ok` 调用（14 个平台）**：

```python
ask_human(
  question_type="form",
  task_title="选择采集平台",
  questions=[{
    "id": "platforms",
    "input_type": "multi_select",
    "question": "请勾选本轮要采集的平台（可多选）",
    "required": True,
    "min_selections": 1,
    "max_selections": 14,
    "options": [
      { "label": "HackerNews（需外网）",            "value": "hackernews" },
      { "label": "Lobsters（需外网）",              "value": "lobsters" },
      { "label": "Dev.to（需外网）",                "value": "devto" },
      { "label": "StackOverflow（需外网）",         "value": "stackoverflow" },
      { "label": "Arxiv（需外网，AI/论文相关）",    "value": "arxiv" },
      { "label": "HuggingFace（需外网，AI/模型）",  "value": "hf" },
      { "label": "Wikipedia（需外网）",             "value": "wikipedia" },
      { "label": "小红书（需登录）",                "value": "xiaohongshu" },
      { "label": "B站（需登录）",                   "value": "bilibili" },
      { "label": "抖音（需登录）",                  "value": "douyin" },
      { "label": "微博搜索（需登录）",              "value": "weibo" },
      { "label": "Twitter/X（需登录 + 需外网）",    "value": "twitter" },
      { "label": "YouTube（需登录 + 需外网）",      "value": "youtube" },
      { "label": "Instagram（需登录 + 需外网）",    "value": "instagram" }
    ]
  }],
  snippet="勾选采集平台"
)
```

**`domestic_only` 调用（仅 4 个国内平台）**：

```python
ask_human(
  question_type="form",
  task_title="选择采集平台（仅国内网络）",
  questions=[{
    "id": "platforms",
    "input_type": "multi_select",
    "question": "请勾选本轮要采集的平台（可多选）",
    "required": True,
    "min_selections": 1,
    "max_selections": 4,
    "options": [
      { "label": "小红书（需登录）",   "value": "xiaohongshu" },
      { "label": "B站（需登录）",      "value": "bilibili" },
      { "label": "抖音（需登录）",     "value": "douyin" },
      { "label": "微博搜索（需登录）", "value": "weibo" }
    ]
  }],
  snippet="勾选采集平台"
)
```

**返回值解析**：先校验 `user_action == "submit"`，再读 `answers.platforms` 数组。
**未选**的平台跳过；**未 submit** 按未答处理，不要假设 default。

---

### Step 0.4：登录预检（`launch_login` 打开窗口 → `ask_human` 让用户多选确认）

> ⛔ **此步骤是强制的**：用户在 Step 0.3 勾选了任何**需登录平台**（xiaohongshu /
> bilibili / douyin / weibo / twitter / youtube / instagram）时，**必须**完成下面两步。
>
> ⚠️ **为什么是用户确认而非自动探测**：mcp-autocli 0.1.8 起已移除自动登录探测
> 工具 —— 早期版本对小红书 / 抖音 / B 站误判率过高（合法 JSON 中含 `login` 子串
> 的 URL 会被错判为未登录）。登录确认彻底交给用户，更可靠。

#### 步骤 1：打开 Edge 登录窗口

```python
mcp_runtime(
  action="call_tool",
  server_id="mcp-autocli",
  tool_name="launch_login",
  arguments={
    "platforms": ["<Step 0.3 勾选的所有需登平台>"]
  },
  snippet="打开 Edge 登录窗口"
)
```

返回结构关键字段：

```json
{
  "ok": true,
  "edge_pid": 12345,
  "opened_pages": [{"platform": "xiaohongshu", "url": "..."}],
  "user_instruction": "已为你打开 ... 的登录页（AutoCLI 专用 Edge 窗口...）",
  "error": null
}
```

把 `user_instruction` **原样转发给用户**。

⚠️ `launch_login` 是异步：调用立刻返回，**不会阻塞等用户登录**。是否真的已登录
完全靠下面 ask_human 让用户自己说。

#### 步骤 2：ask_human 让用户多选确认

> ⛔ **必须 form + multi_select 组合**（同 Step 0.3 硬约束）。option 的 `value`
> 必须用 mcp-autocli 平台英文 key（xiaohongshu / bilibili / ...），
> `answers.logged_in_platforms` 数组直接转给 Step 1 的 search `platforms` 参数。

```python
ask_human(
  question_type="form",
  task_title="确认登录状态",
  questions=[{
    "id": "logged_in_platforms",
    "input_type": "multi_select",
    "question": "你已经在 Edge 窗口里登录哪几个平台？请勾选（未勾选的本轮跳过采集）",
    "required": True,
    "min_selections": 0,
    "max_selections": <Step 0.3 勾选的需登平台数量>,
    "options": [
      // 对 Step 0.3 勾的每个需登平台生成一条 option，未勾的平台不要出现在这
      { "label": "小红书",    "value": "xiaohongshu" },
      { "label": "B站",       "value": "bilibili" },
      { "label": "抖音",      "value": "douyin" },
      { "label": "微博",      "value": "weibo" },
      { "label": "Twitter",   "value": "twitter" },
      { "label": "YouTube",   "value": "youtube" },
      { "label": "Instagram", "value": "instagram" }
    ]
  }],
  snippet="确认已登录平台"
)
```

#### 处理返回

校验 `user_action == "submit"` 后读 `answers.logged_in_platforms`：

| 情况 | 处理 |
|---|---|
| **勾选**的需登平台 | 加入 Step 1 search 的 `platforms` 参数采集 |
| **未勾选**的需登平台 | 区块 0「本轮说明」标 "用户标记本轮未登录，{平台名} 跳过"；**不调 search** |
| 公共平台（hackernews 等） | 不受影响，照常进入 Step 1 |
| `launch_login` 返回 `error` 含 "Edge not installed" | 转发错误（一般要求装 Edge / 重跑 `mcp-autocli setup`）→ **本技能终止** |
| `launch_login` 返回其它 `error` | 转发错误，但仍允许用户在已有 Edge 里手动登录后回答 ask_human |

⚠️ **采集阶段不再询问登录** —— 所有登录问题在 Step 0.4 一次性解决。
Step 1 如果 search 仍返回 `login_required`，标"登录态失效，本轮跳过"，
**不再二次** launch_login。

---

### Step 1：全平台采集（一次 `search` 调用）

按用户在 Step 0.3 的勾选 + 当前配置的关键词，调用 `mcp-autocli` 的 `search`：

```python
mcp_runtime(
  action="call_tool",
  server_id="mcp-autocli",
  tool_name="search",
  arguments={
    "keyword": "<topic 或 keywords_cn[0]>",
    "platforms": ["<本轮勾选的平台数组>"],
    "limit_per_platform": 20
  },
  snippet="一次调用采集所有勾选平台"
)
```

返回结构：

```json
{
  "items": [
    { "platform": "hackernews", "title": "...", "url": "...", "score": 1024, "comments": 230, "author": "..." },
    { "platform": "xiaohongshu", "title": "...", "url": "...", "likes": "5.2万", "author": "..." }
  ],
  "metadata": {
    "platforms_searched": ["hackernews", "xiaohongshu"],
    "platforms_skipped":  [{ "platform": "twitter", "reason": "login_required" }],
    "elapsed_seconds": 12.3
  }
}
```

#### 中英文关键词策略

| 平台分类 | 关键词来源 |
|---|---|
| 国内平台（xiaohongshu/bilibili/douyin/weibo） | 中文，取 `keywords_cn[0]`（或回退到 `topic`） |
| 海外平台（hackernews/lobsters/devto/stackoverflow/arxiv/hf/wikipedia/twitter/youtube） | 英文，取 `keywords[0]`（或回退到 `topic` 的英文译写） |

如果配置同时给了中英文且勾选了两类平台 → **分两次调 `search`**：
1. 第一次：`platforms = [所有国内平台]`，`keyword = keywords_cn[0]`
2. 第二次：`platforms = [所有海外平台]`，`keyword = keywords[0]`

最后把两次返回的 items 合并即可。如果用户只配了一种语言或只勾了一类平台，单次调用足矣。

#### 热榜补充（仅当勾选了支持 hot 的平台时）

`hot` 工具拉的是平台"现在最火"的内容，不依赖关键词。适合在用户话题比较宽泛、
或希望加一个"当前流量风口"维度时跑一遍。

**支持 hot 工具的平台**：

| 平台 | 调用 |
|---|---|
| bilibili | `hot(platform="bilibili", limit=20)` 或 `variant="ranking"` |
| weibo    | `hot(platform="weibo", limit=20)` |
| twitter  | `hot(platform="twitter", limit=20)` |

```python
mcp_runtime(
  action="call_tool",
  server_id="mcp-autocli",
  tool_name="hot",
  arguments={"platform": "<平台 key>", "limit": 20},
  snippet="拉热榜补充候选"
)
```

**Instagram 没有 hot 工具，用 `platform_action` 的 `explore` 替代**：

```python
mcp_runtime(
  action="call_tool",
  server_id="mcp-autocli",
  tool_name="platform_action",
  arguments={
    "platform": "instagram",
    "action": "explore",
    "options": {"limit": 20}
  },
  snippet="拉 Instagram Explore 补充候选"
)
```

返回与 search 一致的 items 数组。把这些热榜/Explore 条目**合并进 Step 1 的 items 池**，
并在 Step 2a 排序时一视同仁参与互动数据排序。在区块 3「数据来源汇总」单独列一行
标"{{平台}} 热榜/Explore X 条"，便于用户知道这部分来自热榜而非关键词搜索。

未勾选任何支持 hot/explore 的平台时，**跳过本步**。

#### 硬约束

> - 主采集必须用 `mcp-autocli.search`，`platforms` 参数必须包含用户在 Step 0.3 勾选的全部平台。
> - `web_search` 仅作兜底：当某平台出现在 `metadata.platforms_skipped` 且重试失败时使用，**报告中必须标 🟡 二手**。
> - 采集失败 / 平台跳过 → 在区块 0/3 如实标注，**禁止用模型自身知识凑数**。

#### 失败处理

| 现象 | 处理 |
|---|---|
| 整个 `search` 调用超时 / 报错 | 重试 1 次（同 keyword + 同 platforms）→ 仍失败则按"全部平台本轮无数据"记录，跳到 Step 2 用兜底（如果有的话） |
| `metadata.platforms_skipped` 含某平台，`reason = login_required` | Step 0.4 已经处理过；这里直接标"登录态失效，本轮跳过"，**不再**重复 launch_login |
| `metadata.platforms_skipped` 含某平台，`reason = autocli_error` | 重试一次仅传该平台 → 仍失败则降级用 `web_search` 兜底（标 🟡） |
| `items` 数组为空但 metadata 显示已搜 | 标"{{平台}} 本轮无搜索结果"，继续下一阶段 |
| 连续 3 个平台 skipped | 暂停，`ask_human` 询问用户是否继续 |

---

### Step 2：排序、痛点、补充信号

#### 2a. 按互动数据排序 + 平台权重

1. **排序字段**：参见 `references/platform-mapping.md` → 「排序字段表」
2. **数值解析**：互动量字符串按解析规则转数值（K/千→×1k，M/万→×1w，B/亿→×1e8）
3. **应用平台权重**：`最终分数 = 原始排序分数 × 平台权重`（默认 1.0，来自 my-radar.yaml）
4. **取 Top 10**：各平台排序后取前 10 进入后续分析

#### 2b. 需求强度推断（含评论挖掘）

先从 search 返回字段做粗筛：

| 维度 | 来源字段 |
|---|---|
| 受众数量 | `views` / `plays` / `score` |
| 互动密度 | `likes` / `comments` / `reposts` / `reactions` |
| 提问情绪 | 标题中是否含"怎么 / 求 / 怎么办 / how to / vs / 推荐" |
| 负面吐槽 | 标题中是否含"踩坑 / 翻车 / 不要买 / 失败 / 难用" |

然后，对 **Top 10 中属于 post_detail 支持平台的条目**调 `post_detail`
拉评论原文（不支持的平台直接跳过）。

支持 post_detail 的平台：**xiaohongshu / youtube / twitter / zhihu / douban / arxiv**。
其中 zhihu 返回问题 + 高赞回答，douban 返回条目元数据 + 短评，arxiv 返回论文元数据（无评论）。

```python
mcp_runtime(
  action="call_tool",
  server_id="mcp-autocli",
  tool_name="post_detail",
  arguments={
    "platform": "<xiaohongshu | youtube | twitter | zhihu | douban | arxiv>",
    "url": "<Top 条目的 url>",
    "comment_limit": 30
  },
  snippet="拉评论提炼痛点"
)
```

返回 `detail.comments[]`，每条带 `author / text / likes / publish_time`。从评论文本
中提炼：

- **高频提问**：含"怎么 / 求教 / how / why"
- **明显负面**：含"踩雷 / 不推荐 / 翻车 / disappointed / waste"
- **未满足需求**：用户说"希望有 / 要是能 / 求一个 X"

评论文本本身和提炼出的痛点写进区块 2 选题详情的「💡 推荐理由」段落（不需要每条
引用，1-2 句概括即可）。

> ⚠️ post_detail 是逐条调，N 条候选 = N 次 MCP 调用。请把调用上限定在 **Top 10 候选
> 里前 5 条**，避免 wall-clock 爆炸。
> 调用失败（`metadata.skip_reason` 非空）→ 该条退回"仅用 search 字段推断"路径，
> 不影响其它条目。

**YouTube 视频深挖**：对 Top 候选中的 YouTube 视频，可用 `platform_action` 获取更丰富
的元数据和文字稿，辅助判断选题价值：

```python
# 获取视频元数据（比 search 返回更丰富：description、duration、channel 详情等）
mcp_runtime(
  action="call_tool",
  server_id="mcp-autocli",
  tool_name="platform_action",
  arguments={
    "platform": "youtube",
    "action": "video",
    "args": ["<视频 URL>"]
  },
  snippet="拉 YouTube 视频元数据"
)

# 获取视频文字稿（纯文本读取，不下载视频）
mcp_runtime(
  action="call_tool",
  server_id="mcp-autocli",
  tool_name="platform_action",
  arguments={
    "platform": "youtube",
    "action": "transcript",
    "args": ["<视频 URL>"]
  },
  snippet="拉 YouTube 视频文字稿"
)
```

文字稿可用于判断视频实际讲了什么、是否有信息差，写进「💡 推荐理由」。
调用上限同 post_detail：**Top 10 里前 5 条**。

「需求证据」直接引用 search / hot 命中的高互动条目本身（标 🟢 一手）。
某平台 search 失败时，允许用一次 `web_search` 兜底该话题，**所得引用标 🟡 二手**。

#### 2c. RSS 采集（如配置了 `rss_feeds`，可选）

用 agent 内置 `read_url` 工具抓 XML 文本，模型自己解析 `<item>` / `<entry>` 节点：

```python
read_url(
  url="<rss_feeds[i]>",
  snippet="抓取 RSS 源 XML"
)
```

解析每条 RSS item，提取 `title` / `link` / `pubDate`，取前 10 条。
**RSS 条目标 🟡 二手**，仅作补充参考，不参与主排序评分。

如 `read_url` 因登录墙 / 超时失败 → 跳过该 RSS 源并在区块 0「本轮说明」如实标注。

#### 2d. `follow_list`（关注列表）

如果 `my-radar.yaml` 里配了 `follow_list`，按平台分别调对应工具。
**两类**：指定用户列表用 `user_timeline`，自己关注圈整体用 `following_feed`。

| 配置形态 | 适用工具 | 支持平台 |
|---|---|---|
| `follow_list.<platform>: [user_id, ...]` | `user_timeline` 逐 user_id 调一次 | bilibili / xiaohongshu / douyin |
| `follow_list.<platform>: [username, ...]` | `platform_action(instagram, user)` 逐 username 调一次 | instagram |
| `follow_list.<platform>: "self"`（特殊值） | `following_feed`（无 user_id） | bilibili / twitter |

**user_timeline 调用**（bilibili / xiaohongshu / douyin）：

```python
mcp_runtime(
  action="call_tool",
  server_id="mcp-autocli",
  tool_name="user_timeline",
  arguments={
    "platform": "bilibili",   # 或 xiaohongshu / douyin
    "user_id":  "<UID 或 profile_id 或 sec_uid>",
    "limit":    10
  },
  snippet="拉指定 UP 主最新视频"
)
```

**Instagram 关注用户调用**（Instagram 无 user_timeline 工具，用 platform_action 替代）：

```python
mcp_runtime(
  action="call_tool",
  server_id="mcp-autocli",
  tool_name="platform_action",
  arguments={
    "platform": "instagram",
    "action": "user",
    "args": ["<username>"],
    "options": {"limit": 10}
  },
  snippet="拉指定 Instagram 用户最新帖子"
)
```

**following_feed 调用**（bilibili / twitter）：

```python
mcp_runtime(
  action="call_tool",
  server_id="mcp-autocli",
  tool_name="following_feed",
  arguments={
    "platform": "bilibili",   # 或 twitter
    "limit":    20
  },
  snippet="拉自己关注圈时间线"
)
```

返回结构与 search 一致（items 列表 + metadata.skip_reason）。把这些条目**合并进 Step 1
的 items 池**，参与 Step 2a 排序时与 search 命中条目一视同仁。

**未支持的平台**（weibo / youtube 的指定用户场景，以及 xhs/douyin/instagram 的关注圈
场景）配了也跳过，区块 0 加一行："follow_list.{平台} 暂不支持，已跳过。"

关注列表数据标 🟢 一手，作为补充信号进入主排序池。

#### 2e. 账号自审与需求信号（可选，提升选题精准度）

当用户勾选了支持账号工具的平台时，可额外调取自己的账号数据作为选题参考信号。
这些数据**不进入主排序池**，而是作为 Step 3 评分时的辅助维度（"我的受众关心什么"）。

**account_dashboard — 账号概览**（支持平台：xiaohongshu / bilibili / twitter）：

```python
mcp_runtime(
  action="call_tool",
  server_id="mcp-autocli",
  tool_name="account_dashboard",
  arguments={"platform": "xiaohongshu"},  # 或 bilibili / twitter
  snippet="拉账号概览（创作者数据 / 收藏 / 历史）"
)
```

返回内容因平台而异：
- xiaohongshu：creator-profile + 7 日数据统计 + 最近 5 篇笔记摘要
- bilibili：个人信息 + 收藏夹(20) + 浏览历史(20)
- twitter：profile + bookmarks(20)

用途：识别自己近期哪类内容表现好、收藏/书签了什么待写素材。

**account_notifications — 通知收件箱**（支持平台：xiaohongshu / douyin / twitter）：

```python
mcp_runtime(
  action="call_tool",
  server_id="mcp-autocli",
  tool_name="account_notifications",
  arguments={
    "platform": "xiaohongshu",  # 或 douyin / twitter
    "limit": 20
  },
  snippet="拉通知（@提及 / 评论 / 新粉丝）"
)
```

用途：通知中的提问、@提及是高信号需求——有人主动找你要内容，说明需求真实存在。
将高频提问话题提取出来，作为 Step 3 评分的加分项。

**Instagram 收藏/已保存内容**（Instagram 无 account_dashboard，用 platform_action 替代）：

```python
mcp_runtime(
  action="call_tool",
  server_id="mcp-autocli",
  tool_name="platform_action",
  arguments={
    "platform": "instagram",
    "action": "saved",
    "options": {"limit": 20}
  },
  snippet="拉 Instagram 已保存帖子"
)
```

用途：已保存的帖子通常是用户认为有价值但还没来得及消化的素材，可作为选题灵感。

> ⚠️ 账号工具调用上限：每个平台最多调 1 次 dashboard + 1 次 notifications。
> 调用失败（skip_reason 非空）→ 跳过，不影响主流程。

#### 2f. KOL 画像（可选，辅助竞品分析）

对 Top 候选中出现的高频作者，可调 `platform_action` 获取其公开画像，辅助判断
"这个话题的头部玩家是谁、他们怎么做的"。

**Twitter 创作者画像**：

```python
mcp_runtime(
  action="call_tool",
  server_id="mcp-autocli",
  tool_name="platform_action",
  arguments={
    "platform": "twitter",
    "action": "profile",
    "args": ["<username>"]
  },
  snippet="拉 Twitter 用户画像"
)
```

**Instagram 创作者画像**：

```python
mcp_runtime(
  action="call_tool",
  server_id="mcp-autocli",
  tool_name="platform_action",
  arguments={
    "platform": "instagram",
    "action": "profile",
    "args": ["<username>"]
  },
  snippet="拉 Instagram 用户画像"
)
```

返回粉丝数、bio、近期帖子等公开信息。将这些写入区块 2 选题详情的「📚 参考材料」
段落，帮助用户了解同一话题下的头部创作者和他们的内容风格。

> ⚠️ 调用上限：**Top 10 候选里前 3 位高频作者**，每位最多查 1 个平台。
> 不支持的平台直接跳过。

---

### Step 3：交叉比对、评分与输出报告

#### 交叉比对

保留同时满足以下条件的候选：
- **供给侧** 有新信息 / 新实践 / 新玩法
- **需求侧** 有明确受众兴趣 / 互动 / 提问（优先用 Step 2a 排序后的高互动内容作为证据）
- 与 `topic`、`scope`、`platforms` 匹配

#### 评分

使用 `my-radar.yaml` 的 `scoring` 权重（按配置动态读取，不硬编码维度）。
计算细则见 `references/scoring.md`。

#### 输出报告

报告**结构、5 区块、表头、信源标签、入选硬约束、保存路径全部以
`references/output-template.md` 为准**，禁止自由发挥。

报告要点：
- 区块 0「本轮说明」的"采集引擎"字段填 `mcp-autocli MCP（v0.1.7+）`
- 区块 4「已知限制与建议」中"重新登录"的建议用 `launch_login` MCP 流程话术

**保存报告**（直接落盘，无需用户确认）：

将报告内容直接写入 `output/radar_{{topic}}_{{日期}}.md`，告知用户最终路径。

---

## 资源索引

| 路径 | 说明 | 读取时机 |
|---|---|---|
| `references/platform-mapping.md` | mcp-autocli 平台 key ↔ 中文显示名 + 排序字段对照 + 数值解析规则 | Step 0.3 / Step 1 / Step 2 必读 |
| `references/output-template.md`  | 报告 5 区块结构契约（表头 / 信源标签 / 入选硬约束 / 保存路径） | Step 3 必读 |
| `references/scoring.md`          | 评分维度权重定义 + 计算方式 + 平台权重应用 | Step 2c / Step 3 |
| `examples/my-radar.yaml.example` | 配置模板（topic / keywords / platforms / scoring / rss_feeds） | 首次配置 |

---

## 全局规则

- 所有链接必须有效；无法确认有效性的不允许出现在报告中
- Twitter 链接格式：`https://x.com/{用户名}/status/{推文ID}`
- 需求证据和参考材料每条必须 `[可点击标题](完整URL)` 格式
- 参考材料优先原始来源页，不要放聚合页

**数据真实性硬约束**：
- **禁止编造补位**：mcp-autocli `search` 失败 → 严禁用模型自身知识生成候选。空返平台直接标记"该平台本轮无数据"
- **信源标签强制**：每个候选必须标 🟢 / 🟡，未标注的禁止写入最终报告
  - 🟢 一手：来自 `mcp-autocli.search` 命中的条目
  - 🟡 二手：来自 `web_search` 兜底 / RSS 订阅源

---

## 异常处理速查

| 现象 | 处理 |
|---|---|
| Step 0.0 `list_servers` 返回中没有 `mcp-autocli` | 自动 `useSkill post-pilot` 完成安装，重检通过后继续；post-pilot 也失败则终止 |
| `list_servers` 中 `mcp-autocli` 状态非 connected | `toggle_server` off→on 重连一次；仍非 connected → `useSkill post-pilot` 安装 |
| `launch_login` 返回 `error` 含 "Edge not installed" | 转发错误提示（要求装 Edge / 重跑 `mcp-autocli setup`），本技能终止 |
| `launch_login` 返回 `ok=false` 其它原因 | 转发错误；告知用户也可在已开的 Edge 里手动打开登录页，然后照常回答 Step 0.4 的 ask_human |
| Step 0.4 ask_human 用户**未勾任何平台** | 区块 0 标"用户本轮未确认任何登录平台"；如还有公共平台则继续，否则本技能终止 |
| `search` 返回 `autocli_error` | 单平台重试一次；仍失败 → web_search 兜底（🟡）+ 区块 0 标注 |
| `search` `metadata.platforms_skipped` 含某平台，`reason=login_required` | 标"登录态失效，本轮跳过"；不再 launch_login（已在 Step 0.4 处理过） |
| 整轮一个候选都没凑够（Step 3 入选规则要求 5-8 个） | 区块 0 标"本轮数据不足"，区块 1 只列出实际入选的；不要硬凑 |
| `read_url` 抓 RSS 失败 | 跳过该 RSS，区块 0 标注 "<rss_url> 抓取失败" |

---

## 状态

唯一持久文件是 `.content-radar/my-radar.yaml`（每次 Step 0.1 覆盖写入）；
不维护其他会话级状态文件，已完成/待采集平台通过对话上下文跟踪。
