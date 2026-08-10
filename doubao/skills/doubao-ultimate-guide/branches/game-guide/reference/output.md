# 游戏攻略最终产物输出规则
本文件负责把已完成路由、目标锁定、当前环境、可用性、当前规则、历史边界、检索验真、视觉素材验证和质量检查的内容，生成正式可交付产物。所有正式游戏攻略最终只允许以飞书文档或HTML交付；禁止仅用普通聊天文本、Markdown、提纲、摘要或链接集合代替。

## 目录
- 输出格式
- 内容来源边界
- 当前环境、可用性与历史展示
- 正文结构与步骤写法
- 图片输出规则
- HTML规范与组件
- 飞书文档要求
- 来源、条件、排查与剧透
- 交付前检查
- 硬失败与完成条件

## 一、输出格式
最终格式只允许：
1. 飞书文档；
2. HTML。

选择规则：
- 用户明确要求飞书文档 → 输出飞书文档；
- 用户明确要求HTML → 输出HTML；
- 用户未指定 → 必须先实际尝试创建飞书文档，并默认交付飞书文档；
- 用户同时要求两种 → 可同时生成；
- HTML 备用只允许在严格飞书失败条件成立时使用；不得因为HTML更好看、更省事、图片插入麻烦、飞书排版不熟、缺少父文件夹 token、或未尝试飞书而直接生成HTML。

最终产物必须能脱离聊天上下文独立阅读和执行，禁止只包含摘要、目录、结论、几个关键点、来源链接、“见聊天记录”或未展开步骤。

### 飞书优先与HTML备用硬规则
用户未指定HTML时，飞书是强默认而不是可选偏好。必须先按当前 `lark-cli` 文档读取飞书创建规则，并实际运行飞书创建或更新命令。

允许改用HTML备用的严格条件仅包括：
- 本机没有可用 `lark-cli`，且无法调用飞书文档创建能力；
- 飞书认证或权限明确失败，例如未登录、token失效、权限不足；
- `lark-cli docs +create/+update` 返回明确错误，且重试或修正命令参数后仍无法创建；
- 当前运行环境明确禁止写入飞书；
- 用户明确要求不要使用飞书或明确要求HTML。

以下情况不得作为HTML备用理由：
- HTML排版更容易或更好看；
- 飞书图片上传、图文分栏或Docx XML较麻烦；
- 没有父文件夹 token，因可使用默认位置或个人空间；
- 没有先读取 `lark-doc` / `lark-doc-create` / `lark-doc-xml`；
- 没有尝试 `lark-cli docs +create`；
- 飞书文档已创建但局部图片暂时缺口，此时应继续补图、从真实视频截取关键帧或要求用户提供截图；不能直接改HTML，也不能无图交付正式飞书攻略。

若触发HTML备用，最终回复必须简述：
- 已尝试的飞书命令类型，例如 `docs +create` 或 `docs +update`；
- 失败原因摘要；
- HTML是备用产物，不是默认格式。

## 二、内容来源边界
最终产物只能使用：
- 与 `target_identity_lock` 完全一致的对象信息；
- 已验证为同一对象的 `verified_aliases`；
- `retrieval.md` 验证后的 `accepted_claims`；
- 已写明适用条件的 `conditional_claims`；
- 当前具体方法中 `current_rule_evidence.status=confirmed` 的默认步骤；
- `current_rule_evidence.status=supported` 的条件化方案；
- 当前 `unavailable` 时已验真的历史开放时期和历史方法，并明确当前不可执行；
- `insufficient` 或疑似过期资料只能作为线索、缺口或风险边界说明，不得进入当前步骤；
- `media.md` 验证通过的真实视觉素材；
- 用户明确提供且未被证据否定的当前游戏状态。

禁止使用：
- 相近对象、同家族、其他形态、其他进化阶段或其他服务器版本的信息冒充当前目标；
- 未证实同一对象的社区混称、相关外观/皮肤、进化阶段、资质/词条、强化状态、技能槽、活动变体、相关系统或地图状态冒充当前目标；
- `rejected_claims`、未验真核心结论、只有通用机制证据的目标事实；
- 与当前环境不兼容的历史信息；
- 当前失效/下架/结束的历史攻略包装成现行方法；
- 当前可用性无法确认时用旧机制补位；
- `temporal_compatibility` 未达 `verified_current` 的历史规则；
- 无法解释的大量失败反馈方案；
- 未验证或AI生成的游戏图片。

输出层不得为了页面完整、文案流畅、视觉美观、显得专业、填满Hero/Meta/摘要/提示框而新增事实。标题、Hero、快速结论、状态提示、小标题、图片说明和结尾总结全部遵守同一事实标准。禁止过程性自我背书，如“多渠道验真”“权威攻略”“100%有效”“全网最全”。

若检索发现多个相近对象、形态、外观、进化阶段、资质/词条、状态、同家族对象或相关系统，最终产物只围绕 `canonical_target + requested_action` 展开。相关项最多用于简短消歧、前置说明或“不应混用”提示；不得为相关项分别生成完整攻略，除非用户明确要求比较或它是已验证的必要前置。

## 三、当前环境、可用性与历史展示
最终产物必须继承 `retrieval.md` 的：
- `current_game_context` 与 `verified_at`；
- `current_context_lock`；
- `availability_gate`；
- `current_rule_snapshot`；
- `current_rule_evidence`；
- `temporal_compatibility`；
- 必要的 `target_lifecycle`。

展示规则：
- 正式产物正文的第一信息块必须先展示本次核验时间/当前时间（含日期、具体时间、时区）和当前有效环境；在此之前不得输出当前状态、获取途径、推荐结论或操作步骤。
- 若缺少时间块、时间块晚于状态/结论/步骤，或只写“当前版本/当前环境”而不写核验时点，必须返工后再继续输出正文。
- 版本、Patch、赛季、资料片、活动、服务器、平台、模式会影响答案时，在正文前部写明适用环境；不要机械堆无关字段。
- 活动、卡池、轮换、限时获取等必须以本次核验状态为准，必要时展示日期或有效期。
- 赛季制、版本制、池子制或活动制游戏必须分层展示：当前环境结论、跨环境已验证通用机制、历史环境信息。历史环境的“常驻/池内/可刷”必须写出适用范围，不得简写成当前常驻。
- `available`：说明当前可用；只有当前方法已确认后才给无条件步骤。
- `limited`：先写开放条件，再给对应方法。
- `unavailable`：明确当前不可获得/触发/进入/完成；可靠时补充历史时期和历史方法，并标注当前不可执行。
- `uncertain`：明确状态未能可靠确认，不得用旧方法包装成攻略。
- 当前没有可执行途径时，正文先写“当前没有/当前不可执行”，再写“历史方式（对应环境，当前不可执行）”和“当前仅存已确认途径”；若没有已确认剩余途径，写“暂无可靠当前途径”，不要生成操作步骤。
- 当前不可用、当前方法未确认，或方法组件为 `removed/expired/changed/uncertain` 时，进入“历史信息非执行化展示”：历史方法只能用摘要、对照表或时间线说明，不能使用步骤卡、编号流程、操作流程、效率技巧、推荐路线、FAQ操作建议或祈使句。
- 疑似过期或未能可靠确认当前仍有效的攻略，标题和模块必须标为“疑似过期，未确认当前仍有效”或“未找到可靠当前攻略”；可说明线索和缺口，但不能写成“当前攻略、刷取指南、推荐路线、照做步骤”。

当前规则输出 Gate：

```text
availability_gate = available / limited
+ current_rule_snapshot 已建立
+ current_rule_evidence.status = confirmed
= 可输出当前默认步骤
```

`supported` 只能作为写明条件的方案；`insufficient/speculative` 不能生成 Step-by-Step 确定攻略。历史方法进入当前攻略还必须满足 `temporal_compatibility=verified_current`。当前规则和历史规则必须分层展示，不得把历史步骤放进当前步骤序列。

活动、入口、道具、商店、掉落池、刷新池、保底机制、NPC、任务阶段、地图状态等方法组件必须来自当前环境且 `current_status=active`，才能出现在当前步骤中。抽取、刷新、掉落、盒子、池子、兑换、轮换还必须确认目标在当前池内或当前可用。历史组件标题必须带环境标签，例如“历史方式（旧赛季/旧版本，当前不可执行）”。

历史方法非执行化展示推荐结构：

```text
当前状态：当前环境无法通过该方式获得。
历史方式：
| 所属环境 | 当时方法 | 当前状态 | 说明 |
| 旧环境 | 当时通过某活动/入口/保底获得 | 当前不可执行 | 已结束/已替换/已移除 |
当前可做：只列已确认仍存在的途径；没有则写“暂无可靠当前途径”。
```

资料不足展示推荐结构：

```text
当前核验结论：未找到可靠当前攻略。
已确认：只写已经被当前证据支持的对象、环境或开放状态。
不能确认：列出缺少当前实机/官方/社区复现的核心步骤。
下一步核验：建议用户提供截图、任务日志、版本/服务器，或继续等待当前玩家复现。
```

禁止把历史方法标题或模块写成“抓捕攻略、刷取指南、定向获取、操作流程、推荐刷法、效率提升、常见误区”。禁止在历史方法中使用“前往、清理、处理、等待触发、持续刷、推荐、首选”等会让用户误以为当前可执行的表达。

## 四、正文结构与步骤写法
正文结构由 `primary_task` 决定，不强制统一模板；但必须采用“先总述，再分步骤/分论点展开”的组织方式。正式产物正文第一信息块展示核验时间/当前环境后，必须先给一个总述模块，再进入详细步骤、路线、机制、Build、表格或排查。总述不是用来替代正文的摘要，而是先给读者整篇攻略的主判断和执行框架，后文必须逐项展开。

```text
我现在应该做什么
→ 从哪里开始
→ 按什么顺序执行
→ 哪些地方最容易失败
→ 如何判断已经成功
```

常用模块：
- 当前情况 / 适用环境；
- 总述模块；
- 快速结论；
- 开始前准备；
- 核心路线或具体步骤；
- Boss/战斗处理；
- Build/角色调整；
- 关键前置；
- 失败排查；
- 替代方案；
- 历史信息；
- 完成确认。

### 总述模块
总述模块用于让玩家先看懂整篇攻略的主结论和执行逻辑，类似论文先给总论，再展开分论点。它必须出现在详细步骤之前，不能藏在文末、表格后或步骤中间；也不能只写“下面会详细说明”这类空泛导语。

总述模块应根据任务复杂度包含 3-6 个短项：
- 核心结论：当前能不能做、主方案是什么、不要做什么旧方法；
- 适用条件：版本、平台、服务器、活动、难度、任务阶段、用户前置或资源边界；
- 执行主线：用一句话概括“先做 A → 再做 B → 最后确认 C”；
- 第一动作：玩家打开游戏后先点哪里、去哪、检查什么或准备什么；
- 关键风险：最容易失败、过期、误路由、缺前置、资源浪费或图片识别错误的点；
- 完成标志：任务日志、图鉴、奖励、入口、地图、Boss、UI 或资源状态出现什么变化。

总述只压缩已验证事实，不新增未验证结论；总述中的每个关键判断必须能在后续详细步骤、条件说明或历史边界中找到展开。简单问题可用一个 callout 或 3 条短句完成总述；复杂攻略应使用 callout、grid 或小表格把“结论/先做什么/风险/完成标志”放在开头。总述之后必须继续给出可执行的详细步骤、分论点、表格或排查，不能用总述代替完整攻略。

当当前不可用、疑似过期或未找到可靠当前攻略时，总述模块必须先写清状态，例如“当前不可执行”“仅历史资料”“未找到可靠当前攻略”，再说明已确认内容和缺口；不得在总述中写成当前可照做的攻略。

不要为了模板完整输出无关栏目。标题优先使用玩家能执行的语言，如“从传送点到洞口”“Boss二阶段处理”“任务不触发的排查顺序”，避免泛化“第一部分/机制分析”。建议 H1 为攻略主题，H2 为阶段/模块，H3 为必要子步骤。

需要操作时优先编号。每步尽量包含：起点、动作、方向或对象、识别标志、成功后的下一状态。禁止连续使用“然后过去”“注意一下”“正常打”“按情况调整”“走到那里”等空泛表达。

任务结构重点：

| 任务 | 正文重点 |
|---|---|
| `walkthrough` | 当前阶段、连续流程、检查点、阶段切换、完成标志 |
| `quest` | 任务阶段、前置、NPC/触发条件、下一步、卡点排查 |
| `navigation` | 起点、路线、层级、入口、中途地标、终点确认 |
| `combat-and-boss` | 前摇、时机、站位、躲法、输出窗口、失败原因 |
| `build` | 当前环境、核心组件、替代件、资源成本、适用边界 |
| `character-and-team` | 角色定位、队伍协同、培养顺序、用户已有条件 |
| `puzzle` | 机关状态、观察角度、交互顺序、重置/失败处理 |
| `collection-and-achievement` | 目标唯一性、前置、路线、遗漏点、完成确认 |
| `beginner` | 当前阶段优先级、资源误用风险、短期目标 |
| `resource-and-efficiency` | 成本收益、机会成本、限时性、不可逆风险 |

## 五、图片输出规则
最终攻略中的游戏画面类图片必须来自 `media.md` 验证通过的真实素材。允许真实实机截图、真实游戏内地图/UI、真实实机视频帧、官方明确属于实机的截图。禁止AI生成图、宣传CG、概念图、立绘、同人图、手绘伪地图、非实机渲染、MOD/私服画面、版本/平台/场景不匹配图片。

图片必须服务具体动作或判断，并放在对应步骤、路线节点、对象识别、机制说明或失败排查旁边，而不是堆在文末。可以在真实截图上加箭头、编号、框选、路线和简短标注，但底图事实不能改变。

图片说明只能描述已确认的对象、位置、机制和操作，不得新增未验证事实。正文写“见图”时图片必须存在且编号对应。

尺寸选择：
- `compact`：角色面板、装备UI、道具、局部机关、单一对象；
- 默认：现场截图、入口、NPC位置、单步操作画面；
- `wide`：地图、长路线、大型Boss场地、整体空间关系。

若无法保证图片真实或可访问，宁可减少图片，改用更详细文字说明。

## 六、HTML规范
HTML必须是完整、可独立打开的单文件页面，至少包含 `<!DOCTYPE html>`、`<html lang="zh-CN">`、`<head>`、UTF-8、viewport、页面标题、内嵌CSS、`<body>` 和完整攻略正文。默认不依赖额外CSS或JS。

默认页面结构：

```text
Hero标题区
→ 第一信息块：本次核验时间 / 当前有效环境
→ 总述模块：核心结论 / 适用条件 / 执行主线 / 第一动作 / 风险 / 完成标志
→ 开始前确认
→ Step 01 / 02 / 03
→ 常见失败排查
→ 历史信息（仅必要时）
→ 完成确认
```

视觉目标：
- 像完整攻略页面，不像套CSS的Markdown；
- 用户几秒内能找到当前结论、适用环境和第一步；
- 真实游戏图片与步骤视觉绑定；
- 手机端清晰；
- 不用动画制造高级感。

配色与布局：
- 背景必须偏浅，优先使用低饱和浅灰、灰白、微暖中性色或从游戏场景中提取的极浅色；禁止使用大面积深色、纯黑、深紫、深蓝、强渐变或压暗背景；
- 正文深灰，次要文字中灰；
- 主强调色必须与游戏主题、目标对象或真实素材视觉相关，例如目标精灵主色、地图环境色、阵营/UI色；必须来自已验证真实游戏截图、官方实机图、游戏内UI或目标对象图，不能凭空选择；
- 只用1个中低饱和主强调色，可加1个低饱和辅助色；不得整页一味紫蓝渐变、咖啡棕橙、深蓝暗色或与游戏对象无关的网红配色；
- 状态色仅用于成功、注意、风险、信息，采用浅背景+深文字；
- 选择配色前必须先在视觉素材检索中记录 `theme_color_basis`：取色依据、来源图、对应目标/场景、是否与当前版本一致。若无法找到可靠视觉依据，使用中性浅色主题并说明原因。
- 正文最大宽度约900-1000px；
- 卡片圆角、边框、阴影统一且克制；
- 避免高饱和大背景、蓝紫/彩虹渐变、霓虹、玻璃拟态、重阴影、大量装饰图标和影响阅读的动画。

普通攻略默认不需要JavaScript。只有多平台/职业/阶段切换、Build筛选、可折叠大量可选信息等确实提升体验时才使用；核心步骤不能依赖JS才能看到。

## 七、HTML组件
优先复用固定组件，而不是每次重设样式。

Hero：

```html
<header class="guide-hero">
  <div class="eyebrow">任务攻略 · 已确认环境</div>
  <h1>具体攻略标题</h1>
  <p class="guide-summary">1-2句话说明目标和最重要处理方向。</p>
  <div class="meta-list">
    <span class="meta-chip">本次核验时间：YYYY-MM-DD HH:mm 时区</span>
    <span class="meta-chip">当前有效环境：版本/赛季/服务器/平台中会影响答案的字段</span>
    <span class="meta-chip">最小必要剧透</span>
  </div>
</header>
```

快速结论：

```html
<section class="quick-answer">
  <div class="quick-answer-label">总述</div>
  <p>先概括核心结论、适用条件、执行主线、第一动作、关键风险和完成标志；只压缩已确认事实，不确定时直接写不确定。</p>
</section>
```

步骤卡：

```html
<article class="step-card">
  <div class="step-index">01</div>
  <div class="step-body">
    <h2>确认入口状态</h2>
    <p>到达目标区域后先检查北侧石门是否开启。</p>
    <div class="step-action"><strong>你现在要做：</strong>检查任务日志。</div>
  </div>
</article>
```

提示框只用四类：

```html
<div class="callout callout-success"><strong>当前可用</strong> 当前环境仍存在有效渠道。</div>
<div class="callout callout-warning"><strong>注意前置</strong> 未完成任务A时入口不会出现。</div>
<div class="callout callout-danger"><strong>旧方法已失效</strong> 该历史活动当前不可使用。</div>
<div class="callout callout-info"><strong>成功标志</strong> 任务日志更新后即可继续。</div>
```

图片：

```html
<figure class="guide-figure is-wide">
  <img src="VERIFIED_REAL_GAME_SCREENSHOT" alt="真实游戏截图：目标入口位置" loading="lazy">
  <figcaption><span class="figure-label">入口位置</span> 火把左后方就是实际入口。</figcaption>
</figure>
```

表格：

```html
<div class="table-wrap">
  <table>...</table>
</div>
```

图片引用必须真实可访问；不得使用臆造文件名、搜索结果页地址或不存在的本地路径。

## 八、HTML基础骨架
可用以下最小骨架扩展，不得保留占位内容：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>游戏名｜具体攻略标题</title>
  <style>
    :root {
      --bg:#f7f8f6; --surface:#fff; --soft:#f4f7f4; --text:#202832; --muted:#697481;
      --border:#e2e8e1; --primary:#5d7b68; --primary-soft:#edf4ef;
      --success:#39715a; --success-soft:#eef7f2; --warning:#8b652f; --warning-soft:#fbf5ea;
      --danger:#9b4b45; --danger-soft:#fbefee; --info:#526b84; --info-soft:#eef3f7;
    }
    *{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--text);font:16px/1.7 -apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif}
    main{max-width:980px;margin:auto;padding:32px 18px 56px}.guide-hero,.quick-answer,.step-card,.callout,.guide-figure{background:var(--surface);border:1px solid var(--border);border-radius:16px}
    .guide-hero{padding:30px}.eyebrow,.meta-chip,.quick-answer-label,.figure-label{color:var(--primary);font-weight:700}.meta-list{display:flex;flex-wrap:wrap;gap:8px}.meta-chip{background:var(--primary-soft);padding:4px 10px;border-radius:999px}
    .quick-answer{margin:18px 0;padding:18px 20px}.step-card{display:grid;grid-template-columns:56px 1fr;gap:14px;margin:16px 0;padding:20px}.step-index{color:var(--primary);font-size:24px;font-weight:800}.step-action{background:var(--soft);border-left:4px solid var(--primary);padding:10px 12px}
    .callout{margin:14px 0;padding:13px 15px}.callout-success{background:var(--success-soft);color:var(--success)}.callout-warning{background:var(--warning-soft);color:var(--warning)}.callout-danger{background:var(--danger-soft);color:var(--danger)}.callout-info{background:var(--info-soft);color:var(--info)}
    .guide-figure{margin:18px 0;padding:10px}.guide-figure img{display:block;max-width:100%;height:auto;border-radius:12px}.guide-figure.is-compact{max-width:680px}.guide-figure figcaption{margin-top:8px;color:var(--muted)}.table-wrap{overflow-x:auto}
    @media (max-width:640px){main{padding:20px 12px}.step-card{grid-template-columns:1fr}.guide-hero{padding:22px}}
  </style>
</head>
<body>
  <main>
    <!-- 完整攻略正文 -->
  </main>
</body>
</html>
```

## 九、飞书文档要求
飞书文档必须是可阅读、可继续编辑的正式攻略：
- 标题与 `target_identity_lock` 一致；
- 开头总述、状态标签和快速结论只使用已验真内容；
- 正文第一信息块先展示本次核验时间/当前时间（含日期、具体时间、时区）和当前有效环境；
- 第一信息块后必须先出现总述模块，再进入详细步骤、路线、Build、机制、表格或排查；
- 当前环境、可用性、当前规则和历史边界清楚；
- `confirmed` 方法才作为默认步骤，`supported` 必须条件化；
- 当前不可用时明确不可用，并把历史信息与当前攻略分开；
- 标题层级清楚，步骤编号稳定；
- 图片实际插入并靠近对应步骤；
- 表格不过度拥挤；
- 不出现聊天记录引用、占位符、图片链接代替实际图片、大量Markdown残留、只有目录没有正文、巨大代码块。

### 飞书文档视觉与版式要求
飞书文档不能只是普通聊天文本、Markdown正文或HTML页面的平铺搬运。默认要做成“游戏攻略文档”的阅读体验，主动使用飞书适合编辑和扫描的块级组件。使用 `lark-cli docs +create/+update --api-version v2` 创建或编辑飞书文档时，默认使用 Docx XML；写入前必须按当前 CLI 提示读取 `lark-doc` 相关内置文档，至少包括 `lark-cli skills read lark-doc references/lark-doc-create.md`、`references/lark-doc-xml.md`、`references/style/lark-doc-style.md` 和 `references/style/lark-doc-create-workflow.md`。

- **封面信息区**：标题下方先放紧凑的信息块，包含核验时间、当前环境、目标对象、当前可用性、适用平台/服务器和剧透级别；该信息块必须位于任何结论和步骤之前。
- **视觉主题一致**：飞书不能只有普通段落和零散提示框。根据游戏主题、目标对象或真实截图中的主视觉选择 1 个主语义色，并映射到飞书支持的基础色（green/blue/yellow/red/purple/gray/orange）；不确定时用中性 gray + 任务状态色，不硬套深色或艳色。
- **状态高亮块**：用醒目的 `<callout>` 承载“当前可用、限时、已失效、条件适用、风险、成功标志”。不要把这些关键信息埋在长段落里。高亮块必须有 emoji，且同一文档中至少使用 3 种不同语义样式；复杂攻略应使用 4-6 种语义样式，避免全文只有同一种黄色提示框。
- **分栏布局**：能提升扫描效率时使用 `<grid>` + `<column width-ratio="...">`。推荐用法：
  - 左列：当前结论 / 先做什么；
  - 右列：前置条件 / 失败排查；
  - 三列：目标、入口、完成标志。
- **图文分栏卡**：飞书攻略必须优先使用“左图右字”或“左字右图”的 `<grid>` 展示关键步骤。常用比例为图片列 `0.42`、文字列 `0.58`；地图或长路线可用图片列 `0.55`、说明列 `0.45`。左列放经过 `media.md` 验证的 `<img>`，右列放步骤标题、动作、识别标志、成功状态和风险提示。
- **步骤卡片**：步骤不要只用普通编号列表。每个关键步骤应有固定结构：步骤编号、短标题、执行动作、识别标志、下一状态。飞书中可用高亮块、引用块、分割线和小表格模拟步骤卡。
- **表格化决策**：版本差异、当前/历史方法、错误排查、材料成本、路线对照、Build替代件优先使用表格；表格列数控制在 3-5 列，避免横向过宽。
- **次级信息区**：历史方法、长来源说明、可选优化、进阶技巧、低概率排查应放进次级章节、分割线后的表格/高亮块，或在 lark-cli 当前版本明确支持时使用折叠块；核心当前步骤不能藏进次级信息区。
- **真实图片就近放置**：飞书文档必须实际插入至少 1 张经过 `media.md` 验证且对执行有帮助的真实游戏图片，不能只给图片链接、占位符或“未找到图片”的说明。图片放在对应步骤之后或通过图文分栏放在步骤旁边，图注说明它解决哪个动作判断；找不到可靠图片时必须继续检索、改用真实视频关键帧、要求用户提供截图，或停止交付，不得用立绘/封面/搜索图凑数。
- **代码块只用于结构化信息**：允许使用代码块呈现“游戏状态快照、路线脚本、机制时间轴、掉落/保底规则快照、XML风格高亮块”，但不能把正文大段塞进代码块。

飞书美观度最低标准：
- 开头 20% 内容内必须出现：第一信息块、总述模块、至少一个 `<grid>` 分栏或图文分栏；
- 每个 H1/H2 章节尽量有一个非纯文本块（callout、grid、table、pre、img 中至少一种），避免连续长段落；
- 关键图片优先进入图文分栏，右侧文字写动作和判断，不把图片堆到文末；
- 表格表头使用浅灰或主题浅色背景，列数控制在 3-5 列；
- 章节之间用 `<hr/>` 或紧凑小标题形成节奏，但不要用装饰性空块撑版面。

### lark-cli 分栏与高亮块语法
飞书 Docx XML 中，分栏必须使用 `<grid>` 容器，列使用 `<column>`，各列 `width-ratio` 总和必须为 `1`。不要写 HTML/CSS 的 `display:grid`、`div class="column"` 或 Markdown 表格来冒充飞书分栏。

创建或更新飞书时，优先把正文组织为 Docx XML 文件后通过 `--content @file.xml` 传入，避免超长命令行和转义错误；`@file` 只能使用当前工作目录下的相对路径，不要传 `@/tmp/xxx.xml` 这类绝对路径；只有用户明确要求导入 Markdown 时才切换 `--doc-format markdown`。

图片可直接用 Docx XML 的 `<img href="https://...">` 插入网络图，或先用 `lark-cli docs +media-insert --doc <doc_id> --file <local-image>` 上传本地图片，再在需要的位置用返回的图片 token 或 `block_move_after` 调整位置。使用 `docs +media-insert` 时优先传 `doc_id`，不要把 wiki URL 当成 doc 参数；它默认插入文档末尾，若图片属于某个步骤，必须再移动到对应步骤附近，或改用 `docs +update --command block_insert_after --content '<img href="..."/>'` 精确插入。

两栏示例：

```xml
<grid>
  <column width-ratio="0.5">
    <callout emoji="✅" background-color="light-green" border-color="green" text-color="green">
      <h3>当前结论</h3>
      <p>当前环境仍存在可执行路径。</p>
    </callout>
  </column>
  <column width-ratio="0.5">
    <callout emoji="📌" background-color="light-blue" border-color="blue" text-color="blue">
      <h3>先做什么</h3>
      <p>先确认前置，再进入刷取步骤。</p>
    </callout>
  </column>
</grid>
```

三栏示例：

```xml
<grid>
  <column width-ratio="0.34"><p><b>🎯 目标：</b>锁定要抓的对象</p></column>
  <column width-ratio="0.33"><p><b>🧭 入口：</b>确认当前可用入口</p></column>
  <column width-ratio="0.33"><p><b>🏁 完成：</b>图鉴或奖励状态更新</p></column>
</grid>
```

左图右字步骤卡示例：

```xml
<grid>
  <column width-ratio="0.42">
    <img href="VERIFIED_REAL_GAME_IMAGE_URL" width="360" caption="图：地图入口或目标精灵实机画面" name="step-image.png"/>
  </column>
  <column width-ratio="0.58">
    <callout emoji="📌" background-color="light-blue" border-color="blue" text-color="blue">
      <h3>Step 02｜前往目标点</h3>
      <p><b>动作：</b>从传送点出发，沿已验证路线前往目标区域。</p>
      <p><b>识别标志：</b>到达后能看到图中地标或目标 UI。</p>
      <p><b>成功状态：</b>任务/图鉴/地图状态出现对应变化。</p>
    </callout>
  </column>
</grid>
```

飞书攻略图文模块最低要求：
- 路线、地图、入口、NPC、收集品、隐藏地点类问题：至少 1 个“地图定位图”或“入口/地标实机图”，复杂路线应同时有地图图和现场图；
- 精灵、怪物、道具、装备、技能类问题：至少 1 个目标识别图或真实 UI 图，帮助用户确认“是不是这个对象”；
- Boss、机制、解谜、站位类问题：至少 1 个关键帧、场地图、机关图或 UI 图，帮助判断触发时机或操作位置；
- 若无法找到可靠真实图，必须继续检索、扩大到玩家社区/视频平台、截取真实视频关键帧或要求用户提供截图；除用户明确要求纯文字或 `visual_need=none` 外，飞书文档不得用文字说明替代配图交付。

高亮块使用 `<callout>`，可配置 `emoji`、`background-color`、`border-color`、`text-color`。常用颜色优先使用：`light-green` / `light-blue` / `light-yellow` / `light-red` / `light-purple` / `light-gray`，边框和字色使用基础色：`green` / `blue` / `yellow` / `red` / `purple` / `gray`。

攻略高亮块语义建议：

| 用途 | emoji | background-color | border-color | text-color |
|---|---|---|---|---|
| 当前可用 / 已确认 | ✅ | `light-green` | `green` | `green` |
| 总述 / 核心判断 | 🧭 | `light-blue` | `blue` | `blue` |
| 先做这个 / 关键步骤 | 📌 | `light-blue` | `blue` | `blue` |
| 限时 / 前置 / 注意 | ❗ | `light-yellow` | `yellow` | `yellow` |
| 旧方法失效 / 不要照做 | ❌ | `light-red` | `red` | `red` |
| 目标 / 稀有收集 | ⭐ | `light-purple` | `purple` | `purple` |
| 完成标志 / 终点确认 | 🏁 | `light-green` | `green` | `green` |
| 玩家提示 / 小技巧 | 💡 | `light-gray` | `gray` | `gray` |

每份飞书攻略至少应包含：
- 1 个“总述 / 核心判断”模块；
- 1 个“当前状态”高亮块；
- 1 个“你现在先做什么”高亮块；
- 1 个“风险 / 旧方法 / 前置”高亮块；
- 复杂攻略再增加“完成标志、资源准备、失败排查、历史方式”高亮块。

高亮块选择规则：
- 不同语义必须换 emoji 和颜色，例如“当前可用”用绿色，“先做这个”用蓝色，“旧方法失效”用红色；
- 同一语义在同一文档中保持一致，例如所有“旧方法失效”都用同一红色样式；
- emoji 只用于帮助玩家扫描状态，不用于把未验证内容包装成确定结论；
- callout 内部保持短句、列表或小标题，不塞入长篇正文。

禁止：
- 全文只使用同一种黄色提示框；
- 所有 callout 都用同一个 emoji；
- 用 emoji 装饰未验证结论；
- 因追求视觉多样而新增未验真的概率、保底、入口或活动信息。

### 游戏感 XML 风格高亮块
当飞书文档需要增强攻略的“游戏 UI 感”时，可以使用 `xml` 代码块作为小型信息面板。它们应短、准、可扫描，像游戏任务面板或系统日志，而不是程序代码。所有内容仍必须来自已验证事实。

推荐样式：

```xml
<攻略状态>
  <核验时间>2026-07-20 16:01 CST</核验时间>
  <当前环境>洛克王国：世界 S3「铅字幻梦」</当前环境>
  <目标>异色小独角兽 / 白金独角兽家族</目标>
  <当前结论 status="可刷">使用精灵果实 + 眠枭庇护所定向循环</当前结论>
</攻略状态>
```

```xml
<任务步骤 id="02" title="解锁果实">
  <起点>目标精灵图鉴课题页</起点>
  <动作>完成给精灵果实的捕捉课题</动作>
  <成功标志>背包获得对应家族精灵果实</成功标志>
  <风险>不要用旧赛季大量出没活动替代当前步骤</风险>
</任务步骤>
```

使用规则：
- 每份飞书攻略最多使用 2-4 个 XML 风格块；优先放在开头状态、关键步骤、机制快照或历史边界处。
- XML 风格块不能替代正文步骤；代码块之后必须有玩家能直接照做的自然语言说明。
- 不要编造看似系统字段的事实，例如不存在的掉率、保底计数、活动ID、NPC编号或道具ID。
- 代码块语言标记优先用 `xml`；如果平台不支持语法高亮，则仍保留清晰缩进。

### 飞书文档推荐结构
默认飞书攻略按以下结构组装，并根据任务复杂度增删：

```text
标题
→ 第一信息块：核验时间 / 当前环境 / 目标对象 / 当前可用性
→ XML风格攻略状态块
→ 总述模块：核心结论 / 适用条件 / 执行主线 / 第一动作 / 风险 / 完成标志
→ 三栏：目标｜先做什么｜完成标志
→ 图文分栏：左图｜右侧总述或第一步
→ 当前步骤卡 01 / 02 / 03（关键步骤优先做成图文分栏）
→ 真实图片或截图标注（靠近步骤，或在步骤卡左列）
→ 表格：失败排查 / 历史方式 / 条件分支
→ 次级信息区：来源边界 / 历史信息 / 进阶优化
→ 完成确认
```

飞书版与HTML版允许视觉语言不同：飞书版应更像可编辑攻略手册，HTML版应更像可打开的网页。两者不能改变事实结论、当前步骤、历史边界或图片真实性。

若同时输出飞书和HTML，核心事实、步骤顺序、当前环境、可用性、当前规则、条件方案、历史边界和图片素材必须一致；允许排版不同，不能改变结论。

## 十、来源、条件、排查与剧透
最终攻略不是研究报告，不展示完整后台检索过程。必要时简洁标注版本、活动时间、卡池、机制变化、当前开放状态、高风险数值或条件性攻略来源边界。禁止把搜索结果堆进正文或用“我查了这些平台”代替攻略。

`conditional_claims` 必须把条件放在醒目位置，例如：
- 仅适用于对应历史环境，当前不再使用该机制；
- 仅在当前活动开放期间可用；
- 如果已完成任务A，NPC会在北门；未完成时先做任务A。

失败排查按最可能原因排序，不列大量低概率项：

```text
如果目标没有出现：
1. 检查是否完成前置A。
2. 调整到指定时间/阶段。
3. 重新传送或刷新区域。
4. 确认当前环境和任务阶段。
```

默认最小必要剧透：只展示完成当前目标需要的内容；图片不提前暴露重大剧情；完整攻略请求可以提供完整解法。

## 十一、交付前检查
生成产物后必须确认：

```text
artifact_type:
content_complete:
target_identity_consistent:
accepted_claims_only:
unsupported_summary_claims_absent:
self_time_displayed_first_before_status:
summary_module_present_after_time_block:
summary_before_detailed_steps:
summary_consistent_with_details:
self_endorsement_absent:
html_structure_valid:
    images_embedded:
    artifact_contains_real_image_block:
    images_verified:
    image_text_alignment:
    images_placed_near_key_steps:
    current_context_consistent:
availability_displayed_when_needed:
current_rule_snapshot_present_when_needed:
current_rule_evidence_status_valid:
temporal_compatibility_respected:
historical_information_labeled:
links_working:
layout_readable:
mobile_readable:
final_delivery_ready:
```

重点检查：格式正确；HTML是完整文件；飞书或HTML产物本体中实际存在至少 1 个真实图片块（飞书为实际图片块/上传图片，HTML为真实可访问 `<img>`）；正文完整；正文第一信息块先展示核验时间/当前时间和当前环境；第一信息块后先有总述模块，且总述先于详细步骤；标题/Hero/总述/快速结论/图片说明目标一致；无输出层新增事实；无过程性自我背书；图片真实、可访问且与步骤对应，并放在对应关键信息旁边；当前环境和 `verified_at` 一致；当前默认步骤均为 `confirmed`；历史信息未包装成当前方法。

## 十二、硬失败条件
出现任一情况不得交付：
- 标题、Hero、正文或图片说明目标漂移；
- 未验真事实进入 Hero、总述、快速结论、Meta、小标题或图片说明；
- 正文第一信息块后没有先给总述模块，或直接进入详细步骤、路线、Build、排查、表格。
- 总述模块晚于详细步骤，或总述与后续详细步骤、条件边界、历史边界矛盾。
- 总述模块只是口号、链接集合或过程性自我背书，没有交代核心结论、适用条件、执行主线、第一动作、关键风险或完成标志中的关键项。
- 只有通用机制证据却写成目标对象事实；
- 相关对象、形态、外观、进化、资质、词条、状态、技能槽或系统证据被写成当前目标事实；
- 未验证同一对象的别名或社区混称进入标题、Hero、快速结论或默认步骤；
- 时效敏感内容未基于本次当前环境和状态；
- 正文第一信息块未先展示本次核验时间/当前时间（含日期、具体时间、时区）和当前有效环境，或在时间块前先给当前状态、获取途径、推荐结论、步骤；
- 历史可获取被写成当前可获取；
- 问当前具体方法但无 `current_rule_snapshot`；
- 默认方法证据不是 `confirmed`；
- `supported` 未条件化，或 `insufficient/speculative` 写成步骤；
- 历史规则未达 `temporal_compatibility=verified_current` 却写成现行规则；
- 旧环境活动、入口、道具、商店、掉落池、刷新池、保底、NPC、任务阶段或地图状态被写成当前步骤；
- 历史环境的常驻、池内、可刷、盒子/卡池/掉落名单、保底或刷新规则被写成当前事实；
- 只证明当前机制存在，却没有证明目标当前在池或当前可用，就写成当前可获得；
- 当前没有可执行途径或当前方法未确认时，仍生成 Step-by-Step 操作流程；
- 疑似过期或 `insufficient` 资料被写成当前确定攻略；
- 历史方法以步骤卡、编号操作流程、推荐技巧、效率建议或FAQ操作建议呈现；
- 当前不可用时，页面标题、副标题、Hero或模块标题仍写成“抓捕攻略、刷取指南、定向获取、当前刷法”等当前执行口吻；
- 当前 `unavailable` 却生成现行步骤；
- 当前状态不明却用旧机制补位；
- 为了页面完整新增身份、稀有度、外观、机制、保底、获取规则或评价；
- 出现过程性自我背书；
- 只输出聊天文本、Markdown、摘要、提纲或链接；
- 用户未指定时没有默认创建飞书文档，也未在失败时说明原因并提供HTML备用；
- 用户未指定HTML时，没有先实际尝试飞书创建/更新命令就直接生成HTML；
- 把“HTML更好看、飞书排版麻烦、图片插入麻烦、缺少父文件夹token、未读取lark-doc文档”作为HTML备用理由；
- HTML备用未说明飞书命令类型和明确失败原因；
- HTML不是完整可打开文件；
- HTML使用大面积深色背景、深色渐变或与游戏/目标对象无关的配色；
- HTML主题色没有来自真实游戏截图、官方实机图、游戏内UI或目标对象图的取色依据，且未说明使用中性浅色降级；
- 使用AI图、CG、立绘、概念图、伪地图、MOD/私服或错误版本图片；
- 正文引用不存在图片，图片地址失效，或图片与步骤不对应；
- 图片集中堆在文末，未放在对应关键信息、路线节点、机制说明或对象识别旁边；
- 最终产物本体不包含任何真实图片块；
- 飞书文档没有实际插入至少 1 张经过验证且对执行有帮助的真实游戏图片；
- 飞书文档只有图片链接、占位符、搜索结果页、文件名或“未找到图片”说明，没有实际图片块；
- 飞书文档在 `visual_need=required/recommended` 时用文字降级替代配图交付；
- `rejected_claims` 进入产物；
- 条件性攻略未写明条件。

## 十三、最终完成条件
交付前必须同时满足：
- 已选择正确格式；用户未指定时已创建飞书文档，或已记录严格飞书失败证据并说明HTML为备用；
- 产物包含完整攻略且可独立使用；
- 正文按“第一信息块 → 总述模块 → 详细步骤/分论点”的顺序组织；
- 产物本体实际包含至少 1 张经过验证且对执行有帮助的真实游戏图片；
- 主任务结构完整，关键步骤可执行；
- `target_identity_lock` 全篇一致；
- `verified_aliases`、`related_but_distinct` 和 `excluded_entities` 的边界未被混用；
- 标题、Hero、总述、快速结论、Meta、正文和图片说明只使用已验真事实；
- 当前环境、可用性、当前规则、历史边界与 `retrieval.md` 一致；
- 正文第一信息块已先展示本次核验时间/当前时间和当前有效环境；
- 当前步骤中的方法组件均属于当前环境且状态为 active；
- 默认当前步骤均满足 `current_rule_evidence.status=confirmed`；
- `conditional` 条件清晰，`rejected` 和未执行化的 `insufficient` 不出现于当前步骤；
- 所有图片通过 `media.md` 验真且真实可访问；
- 关键图片位于对应步骤或关键信息旁边；
- 已通过 `quality-check.md`；
- 最终回复只简要交付产物，不重新复制完整攻略正文。
