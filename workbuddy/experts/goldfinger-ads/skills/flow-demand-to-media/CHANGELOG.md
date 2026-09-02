# CHANGELOG · 全链路 · flow-demand-to-media

> 本文件是**历史归档**，不进模型上下文（SKILL.md 只保留生效规则）。
> 阅读须知：历史条目里的做法**可能已被后续版本作废**——判断现行行为一律以 SKILL.md 正文为准，本文件仅用于追溯"某个规则是什么时候、因为什么改的"。
> 归档时间：2026-08-26（当前版本 v3.19.0）

---

> **v3.19.0 改动**（2026-08-26）：需求单阶段**只产出文本确认、零 MCP 调用**——ad-demand-helper-pro v2.32.0 删除"灌入需求确认页"（产出 1.5），立项单回归对话栏完整文字并成为下游唯一取数源；灌入合并为**唯一一次**（flow-media-manager v1.27.0 在阶段2 一次灌全 48 字段 = 需求单 + 策略）；连接器自检推迟到灌入前，需求单阶段不提连接器/不提授权。

> **v3.18.4 改动**（相对 v3.18.3，配套专家包 5.0.0，2026-08-25 全链路实测复盘）：⭐ 阶段2 去 HTML 化 + 灌入校验升级同步
> 1. 🚨 **阶段2 主路径不再产出本地确认单 HTML**（用户实测反馈：拉起金手指页面后又产出本地版策略单 HTML，冗余）——flow-media-manager v1.26.0 直接拼 strategy 全量 48 字段灌入配置页，**页面本身就是确认单**；HTML 仅 MCP 不可用/degraded 时兜底
> 2. **两次灌入统一加 session 存活二次校验**（open_config → curl 字段校验 → sleep 2 → curl 存活复查）——服务端重启会清内存 session（2026-08-25 实测 3 分钟内 404），复查非 200 重灌并如实告知
> 3. **打开方式统一 present_files 右栏拉起 + 兜底链接前置**——旧"Bash open 短链"描述作废（与 flow-media-manager v1.25.4 唯一制对齐）；右栏对深链偶发空白，兜底 markdown 链接与 present_files 同条回复给出
> 4. 全链路最终产出改为 **1 份 HTML（可行性评估）+ 1 份对话栏文字 + 2 次金手指灌入**；正文速查/流程图里"11 题三批"旧稿残留同步勘误为 13 题 4 批
> 5. 配套 plugin 5.0.0 / ad-demand-helper-pro v2.31.4 / flow-media-manager v1.26.0


> **v3.18.2 改动**（相对 v3.18.1）：⭐ 专家更名（2026-08-25，用户定稿）
> 1. **职业名「金手指 · 腾讯广告媒介经理」→「金手指·媒介经理」**：display_name / description / 正文身份贯穿话术 / footNote 口径全部同步；产物 banner brand-tag、模板、打包说明同步
> 2. 历史 changelog 标题与条目按惯例保留旧名不回改；配套 plugin v3.64.0 / ad-demand-helper-pro v2.31.2 / flow-media-manager v1.25.8


> **v3.18.1 改动**（相对 v3.18.0）：可行性总分透传口径同步 100 分制（配套 ad-demand-helper-pro v2.31.1：总分 X/100，基调 80-100 标准 / 50-79 保守 / <50 先补齐再投）

> **v3.18.0 改动**（相对 v3.17.2）：⭐ 新增「灵感直达路由」（灵感模版「可行性分析」配套，2026-08-24）
> 1. **灵感模版仅 1 个（可行性分析）**；全流程是专家常规能力（现有三步制），不做灵感模版。场景定义只存在于灵感模版层，不进触发词、不进场景表、不外显
> 2. **可行性直达路由**：用户首条消息**同时满足**「明确要可行性评估/能不能投」+「已给出产品名与至少 2 项投放要素（预算/目标/载体/行业）」→ 调 `ad-demand-helper-pro` 时传 `DIRECT_MODE=feasibility`，走其直达模式（v2.31.0：跳过 3 步收集、补问≤1 轮、直接出《投放可行性评估》HTML）
> 3. **直达终点约束**：可行性 HTML 交付后**停在阶段 1**，不启动 flow-media-manager、不灌金手指；结尾白话引导「想接着做完整投放方案，直接继续说」→ 用户接话则汇入**常规全流程**从中途进入（已收集字段不重问）
> 4. 配套 `ad-demand-helper-pro` v2.31.0 / plugin v3.61.0

> **v3.17.2 改动**（相对 v3.17.1）：灌入打开方式终稿同步（配套 flow-media-manager v1.25.2 / ad-demand-helper-pro v2.26.2，2026-08-24 全链路实测跑通）
> 1. **打开方式改为 session 短链**：取 `sessionId` → `curl /api/mcp/session/{id}` 字段清单机检 → `open ?session= 短链`（32 位 hex 零复制风险）。**`#s=` 内联长链在 AI 调用链弃用**（复制稳定损坏，两次实测 gzip 报废）
> 2. deepLink 禁令分环境修订：FAT 单实例放行（先 curl 验证）；生产多副本仍禁
> 3. 完整校验脚本模板统一维护在 flow-media-manager《灌入金手指》章节

> **v3.17.1 改动**（相对 v3.17.0）：灌入链接打开方式修正（配套 flow-media-manager v1.25.1 / ad-demand-helper-pro v2.26.1）
> 1. **recommendedLink 从"一次定型双轨"中剥离**：一律走 Bash open + 校验闸门（python 解码校验通过才 open），**不走 present_files 传 URL**——预览面板 iframe 对 `#s=` 深链不可靠（实测空白），且长 URL 复制转手丢/错一个字符 gzip 整体报废（2026-08-24 mock 演练实锤，与"URL 过长"无关，上限 32000 字符）
> 2. HTML 文件产物的双轨机制不变
> 3. 详见 flow-media-manager《灌入金手指》章节（两边共用同一套校验模板）

> **v3.17.0 改动**（相对 v3.16.0）：⭐ 全链路 4 步变 3 步——灌入前移（配套字段规范「两次灌入调用时序」章节）
> 1. **两次灌入定案**（金手指新连接器部署后 dry-run 实测通过，2026-08-23 定案、2026-08-24 按新连接器更新）：
>    - **提需灌入**（1/3 内）：立项单文字产出后，ad-demand-helper-pro 立即调 `open_config` 灌 `{offerName, demand}` 拉起「需求确认页」，用户在页面核对（对话栏文字保留——评估输入锚点+审计）
>    - **确认单灌入**（3/3 内）：flow-media-manager v1.25.0 产出确认单后立即全量灌入（48 字段）拉起「策略配置页」，原 4/4 独立阶段废除
> 2. **用户确认环节移到页面上**（用户决策）：两次灌入都不做"没问题我就灌"前置对话确认，页面可核对预填、直接改字段；大改回对话，改完重灌（新链接，30 分钟过期机制）
> 3. **两次灌入是两个独立页面**（用户决策）：不做会话续灌，对金手指 MCP 无新增接口要求
> 4. **金手指连接器**（2026-08-25 升级 MCP v1.0.5 / server 1.0.48，流程零改动）：连接器 key 为 **`jinshouzhi`**（2026-08-26 起鉴权改 token 模式，需在连接器面板配置 GOLD_FINGER_TOKEN；14 工具、参数向后兼容；旧 `ad-goldfinger` 是残留通道）；深链域名已修（五步主台）；#4（http scheme）与 #3（生产库缺表）均已修复——**recommendedLink/deepLink 已直接返回 https**，落库读写与数据调整工具（list_projects / get_project_data / adjust_project / validate_apikey / upsert_demand_brief / get_project_context）恢复可用。灌入细则见两个子 skill 各自灌入章节（session 短链 + curl 校验 + present_files 右栏不变）
> 5. 老链路 fallback：MCP 不可用 → 退回文字/HTML 产出 + 用户确认后灌入的老节奏
> 6. 配套 `ad-demand-helper-pro` v2.26.0 / `flow-media-manager` v1.25.0

> **v3.16.0 改动**（相对 v3.15.0）：⭐ 专家更名
> 1. **专家职业名改为「金手指 · 腾讯广告媒介经理」**（原"媒介投放专家"/profession"金手指 · 广告投放专家"）：display_name、description、身份贯穿话术同步；历史 changelog 标题保留旧名不回改
> 2. 配套 flow-media-manager v1.24.4 / ad-demand-helper-pro 同步更名注记；专家包 plugin.json profession 待重打包时同步
> 3. 编排逻辑不变（全链路 4 步：提需→评估→执行单→金手指开启投放）

> **v3.15.0 改动**（相对 v3.14.0）：⭐ 场景收缩为 2 个，投放者测评下线（plugin v3.31.0）
> 1. **专家从 4 个模式收缩为 2 个场景**：①媒介专家（全链路，本 skill）②通用咨询（内部判断类直接答 + 规则类调 `tencent-ads-delivery-guide` 查）
> 2. 🚨 **投放者测评下线**：`ad-quiz-bidder-profile` skill 已从包内删除；触发词（测测我/投放者测评）→ 告知"测评功能暂时下线了"并引导到通用咨询或全链路，**不出题、不生成结果卡片**
> 3. 本 skill 编排逻辑不变（全链路 4 步：提需→评估→执行单→金手指开启投放）
> 4. 配套 agents md 路由表重写 / plugin.json skills 数组删 ad-quiz / quickPrompts 删测评

> **v3.14.0 改动**（相对 v3.13.0）：⭐ 专家新增第三场景「通识与规则查询」（plugin v3.28.0）
> 1. **专家从 3 个模式变 4 个**：A 全链路 / B 纯咨询（要判断）/ **D 通识规则查询（新增，调 `tencent-ads-delivery-guide`）** / C 测评
> 2. **B 与 D 的边界**：问"多少/要不要/值不值" → B 凭经验判断；问"怎么弄/要什么/在哪/为什么被拒" → D **必须查知识库**（资质/审核/归因等官方随时改，凭记忆答会误导）
> 3. **全链路中途问规则类问题**：调 skill 查准了答 → **答完立刻指引回流**并说清回到第几步（不能查完就忘了在走全链路）
> 4. 本 skill 的编排逻辑不变，仅补充跑题分支的处理规则
> 5. 配套 `ad-demand-helper-pro` v2.17.0 / agents md / plugin v3.28.0（skills 数组已加 `tencent-ads-delivery-guide`）

> **v3.13.0 改动**（相对 v3.12.0）：⭐ 4/4 改走纯结构化字段，取消需求单静默 HTML（plugin v3.27.0）
> 1. 🚨 **回退 v3.12 的"需求单静默 HTML"**：需求单**只有对话栏文字一个形态**，不产出任何文件
> 2. **4/4 改为纯结构化灌入**：`open_config` 的 `strategy` 里给 `demand.groups`（需求字段）+ 23 个策略结构化字段，**不传 HTML**
> 3. **原因**：HTML 通道需页面用 DOM 选择器反解析，改模板样式就可能失败；配置页前端本有结构化分支，字段直给零风险（已抓前端 JS 核实 + 实测 `degraded:false`）
> 4. **传递物回归**：需求字段靠对话上下文，可行性评估/执行确认单靠文件路径（HTML 只作用户可读产物，不再参与灌入）
> 5. 配套 `ad-demand-helper-pro` v2.16.0 / `flow-media-manager` v1.16.0 / plugin v3.27.0

> **v3.12.0 改动**（相对 v3.11.0）：需求单双形态 + 4/4 灌两份 HTML（⚠️ **已被 v3.13.0 取代**——改走纯结构化字段）

> **v3.11.0 改动**（相对 v3.10.0）：4/4 串联金手指 MCP
> 1. 全链路第 4 步（开启投放）落地为真实动作：用户确认执行单 → 调金手指 `open_config`（strategy + rawHtml）→ 打开 `recommendedLink` 配置页。详细执行规则在 flow-media-manager v1.11.0《4/4 开启投放》
> 2. plugin.json 声明 dependencies.connectors: ["jinshouzhi"]（规范 6.5——用户召唤专家时 WorkBuddy 会引导连接金手指）
> 3. 配套 plugin v3.19.0

> **v3.10.0 改动**（相对 v3.9.1）：恢复可行性评估丰富度
> 1. 上游 ad-demand-helper-pro v2.9.0 恢复**五维 0-10 分制 + 总分/50 + 策略基调**——本 skill 透传总分给 flow-media-manager 定策略基调的链路恢复完整（40-50 标准 / 25-39 保守 / <25 先补齐再投）
> 2. 可行性评估 HTML 恢复 7 段结构（含主要风险清单、同赛道参考、避坑清单）
> 3. 配套 `ad-demand-helper-pro` v2.9.0 / plugin v3.13.0

> **v3.9.0 改动**（相对 v3.8.0）：白话命名 + 4 步进度条对齐
> 1. **白话命名同步**：全部统一为"投放需求清单 / 《投放可行性评估》 / 投放执行确认单"
> 2. **4 步进度条对齐**：环节① = 1/4+2/4；环节② = 3/4+4/4
> 3. 配套 `ad-demand-helper-pro` v2.8.0 / `flow-media-manager` v1.7.0 / plugin v3.11.0

> **v3.8.0 改动**（相对 v3.7.0）：修实测 bug
> 1. 🚨 上游 ad-demand-helper-pro **删除了 `demand-charter-template.md` 模板**——实测发现模板存在会诱导模型把立项单写成 HTML 文件（违背 v3.5.0 起的"对话栏文字"规则）。模板已删，配套升 v2.7.0
> 2. 配套 `ad-demand-helper-pro` v2.7.0 / `flow-media-manager` v1.6.0 / plugin v3.10.0

> **v3.7.0 改动**（相对 v3.6.0）：呈现方式按《WorkBuddy 专家开发规范》修正
> 1. ⭐ **从"只走 present_files"改为一次定型双轨**：规范 4.2 明确专家环境系统分配的工具集里没有 present_files（只有 Read/Write/Grep/Glob/Bash/WebSearch/WebFetch 等）。v3.6.0 在正式专家环境会让所有 HTML 退化成贴路径
> 2. **规则**：本会话第 1 份 HTML 产出时（由 ad-demand-helper-pro 完成）试调一次 `present_files`——成功则本会话全走它；失败则本会话全走 Bash `open`。一次定型后不再重试
> 3. **产物目录迁移**：从 `~/投放需求/`、`~/投放策略/` 统一挪到工作区 `投放产出/[YYYY-MM-DD]/`
> 4. 话术按实际轨道：present_files 成功说"在右边栏打开了"，Bash open 说"在浏览器里打开了"
> 5. 配套 `ad-demand-helper-pro` v2.6.0 / `flow-media-manager` v1.5.0

> **v3.6.0 改动**（相对 v3.5.0）：HTML 呈现方式收敛为单一路径（⚠️ 第 1/2 点已由 v3.7.0 修正——专家环境无 present_files，必须保留 Bash open 轨道）
> **v3.5.0 改动**（相对 v3.4.0）：立项单改对话栏文字输出
> 1. ⭐ **需求立项单不再是 HTML 文件**：改为在对话栏直接输出文字给用户确认（不写文件、不推卡片、不用 md 语法）。理由：立项单只用于快速确认，开文件太重
> 2. **产出数量变化**：阶段 1 从"2 份 HTML"变成"1 份对话栏文字 + 1 份 HTML"；`present_files` 只传可行性评估 1 个路径
> 3. **传递物变化**：立项单不再有文件路径，flow-media-manager 从**对话上下文**取 `demand_*` 值；可行性评估仍靠文件路径传递
> 4. 全链路最终产出 = **2 份 HTML**（可行性评估 + 策略纪要）+ 1 份对话栏文字（立项单）
> 5. 配套 `ad-demand-helper-pro` v2.4.0 / `flow-media-manager` v1.3.0


> **v3.4.0 改动**（相对 v3.3.0）：修 4 个用户实测 bug
> 1. 🚨 **选择题必须串行**：ad-demand-helper-pro 里"3 次 AskUserQuestion 在同一条消息完成"是**错误表述**，会导致后两批被界面判「已跳过」、8 道题答案全丢。现明确：一条消息只能有 1 个 AskUserQuestion，答完一批再发下一批
> 2. **每个选项必须带 `description`**：原来只给了 label，用户点选时看不到备注说明（虽然立项单里有）。现三张题表都按 `label — description` 给全
> 3. **可行性评估统一走 present_files/Bash open**：ad-demand-helper-pro 一直停留在 v2.1.2 的 `show_widget` 方案，与本 skill v3.2.0+ 冲突，且专家 subagent 环境无 `show_widget` 工具 → 用户看不到任何卡片。现两份 HTML 一次 present_files 传 2 个路径
> 4. **删除「可视化分析」段**：可行性评估不再加 Chart.js 雷达图 / 气泡矩阵——用户明确反馈"没有必要"，图表占版面且增加渲染失败风险
> 5. 配套 `ad-demand-helper-pro` v2.3.0


> **v3.3.0 改动**（相对 v3.2.2）：交接点话术/推送方案收尾 + part1→part2 串联 + 跑题引导
> 1. 交接点 1/2 话术统一为"浏览器里打开了"（自动打开预览后的极简说法）
> 2. 清理残留：文件路径规范里 IDE 兜底从"markdown 伪卡片"改为 Bash `open` 浏览器打开，删除"双轨逻辑"旧表述
> 3. part1→part2 串联：可行性评估**总分 → 策略基调**（40-50 标准 / 25-39 保守 / <25 先补齐再投，规则见 flow-media-manager「策略基调判定」）；C11 历史经验答案落盘为 `demand_history`（ad-demand-helper-pro v2.5.4 起），媒介策略按此定路径（基建/诊断）。**版位不作为 part1→part2 强约束**——v3.3.0 早期版本里的"版位强约束"概念已撤销，详见 v3.3.0 changelog 勘误
> 4. 跑题引导：提需进行中用户问流程外问题的处理规则见 ad-demand-helper-pro《跑题处理（意愿收紧）》，本 skill 除跑题引导外不干预子 skill 对话逻辑
> 5. 与 `ad-demand-helper-pro` v2.5.4 / `flow-media-manager` v1.3.2 / agent md 的《HTML 产出》章节保持一致
>

> **v3.3.0 changelog 勘误**：本版本早期 changelog 第 3 点中"版位强约束→决定标准投放 vs 智投 AIM+"的说法**已撤销**——按用户判断版位不约束，flow-media-manager v1.3.2 起投放方式判定不再依赖版位强约束，默认走智投 AIM+。版本号未重发，与 ad-demand-helper-pro v2.5.4 / flow-media-manager v1.3.2 配套。


> **v3.2.2 改动**（相对 v3.2.1）：简化方案，跟 ad-demand-helper-pro 对齐
> 1. 砍掉所有"Plan A/B 双方案 + markdown 伪卡片 + 啰嗦话术"——用户不要文字卡，要自动开浏览器预览
> 2. 改为 2 个极简方案：A 主对话有 `present_files` → 调 present_files（卡片+右侧栏）；B IDE subagent → Bash `open` 在默认浏览器打开
> 3. 极简话术，不再堆路径/emoji/编号


> **v3.2.1 改动**（相对 v3.2.0）：承认 IDE expert subagent 工具集限制，改为自适应
> 1. v3.2.0 强制要求 `present_files`——但 IDE expert subagent 工具集里**没有 `present_files`**（trace 验证：`AskUserQuestion / Bash / Read / Skill / ToolSearch / Write`，无 present_files/show_widget/workbuddy_cloudstudio_deploy）
> 2. 改为"工具能力自适应"：主对话用 `present_files`（卡片+右侧栏），IDE expert 用 markdown 伪卡片
> 3. agent 不要硬调不存在的工具——会浪费 `ToolSearch` 调用


> **v3.2.0 改动**（相对 v3.1.1）：统一三份产出走 `Write + present_files` 卡片
> 1. **可行性评估从 `show_widget` / CloudStudio 双轨改为独立 HTML 文件**——跟立项单、策略纪要保持一致（v3.4.0 起明确不加 Chart.js 图表）
> 2. 删除所有"如 present_files 不可用则贴路径"的兜底——`present_files` 是唯一推送方式，期望它把卡片自动打开到右侧栏预览
> 3. 不再调 `show_widget` / `workbuddy_cloudstudio_deploy` / `read_me(modules: ["mockup"])` 等工具


> **v3.1.1 改动**（相对 v3.1.0）：恢复 CloudStudio fallback 作为专家环境降级
> 1. **双轨呈现逻辑**：主对话环境 → `show_widget` 渲染；专家 agent 环境 → CloudStudio 部署链接
> 2. 专家环境 show_widget 不可用（trace 验证：专家 agent 工具集只有 AskUserQuestion/Edit/Grep/Read/TaskCreate/TaskUpdate/Write/mcp_tools）
> 3. CloudStudio 部署路径保留完整 7 段 HTML（含 Chart.js 雷达图 + 气泡矩阵）


> **v3.1 改动**（相对 v3.0）：
> 1. 可行性评估的**对话内呈现方式**从「对话内嵌 HTML 组件（Chart.js + CloudStudio fallback）」**改为 `show_widget` 渲染**（主对话路径）
> 2. **不再走 CloudStudio 部署链接**（v3.1.1 已恢复为专家环境 fallback）
> 3. 立项单产出方式不变（HTML 文件 + present_files 推卡片）
> 4. 可行性评估不再写 HTML 文件，下游 flow-media-manager 通过对话上下文取评估数据


> **v3.0 改动要点**（相对 v2.0）：
> 1. 提需环节调 `ad-demand-helper-pro` v2.3（业务视角问题 + 每题带"不懂帮我判断"）
> 2. 提需产出从 1 份变 2 份：**需求立项单** + **投放可行性评估清单**
> 3. 媒介策略环节读立项单+可行性评估，策略针对性更强
