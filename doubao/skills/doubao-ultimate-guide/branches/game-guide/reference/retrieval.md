# 游戏攻略检索与验真规则
本文件用于锁定游戏目标、确认当前有效环境、判断当前可用性、验证当前规则、筛选攻略结论并淘汰毒攻略。所有正式游戏攻略必须读取本文件并联网检索；禁止只凭模型记忆生成核心事实。

## 目录
- 核心顺序
- 搜索尝试范围
- 目标对象锁定
- 当前环境与可用性
- 历史资料使用
- 候选攻略与证据矩阵
- 来源生态与验证强度
- 社区共识与负面反证
- 结论状态与停止条件
- 历史/不足资料标识
- 任务验真重点
- 完成条件

## 一、核心顺序
必须按以下顺序执行：

```text
识别游戏
→ 锁定目标对象
→ 排除相近对象/同家族/不同形态/不同阶段/不同服
→ 确认当前有效游戏环境
→ 判断目标当前可用性
→ available / limited: 验证当前具体规则
→ unavailable: 停止生成当前步骤，回溯必要历史
→ uncertain: 继续验证，禁止旧攻略补位
→ 建立候选攻略池
→ 拆分 candidate_claims
→ 检查目标特异性、当前环境、来源独立性和实机/玩家复现
→ 主动查负面证据
→ accepted / conditional / rejected / insufficient
```

检索必须围绕 `routing.md` 已确定的 `game`、`version_context`、`final_goal`、`atomic_needs[]`、`dependencies`、`player_context`、`primary_task`、`primary_game_type` 展开。搜索词可以改写，但验证对象不能漂移。

执行时使用短验真协议：
1. 锁定游戏与目标对象，排除相近对象、同家族、不同形态和不同服。
2. 锁定当前有效环境，并记录本次 `verified_at/time_anchor`。
3. 判断目标当前可用性；问当前方法时建立当前规则快照。
4. 建立候选攻略池，不采用第一篇攻略直接输出。
5. 把候选攻略拆成核心 `candidate_claims`。
6. 检查来源独立性、当前环境、目标特异性、实机/玩家复现，并主动搜索反证。
7. 将每条核心结论标为 `accepted` / `conditional` / `rejected` / `insufficient`，只允许合格结论进入当前步骤。

## 二、搜索尝试范围
搜索尝试要宽，采信要严。不要因为第一个搜索结果像攻略就停止；也不要机械要求每个平台都有结果。优先尝试至少 4 类来源生态，若某些来源不可访问或没有有效结果，继续换同类来源或关键词。

来源池：
- 官方/权威：游戏官网、官方公告、Patch Notes、活动页、官方论坛、官方社区、客服 FAQ、发行商或平台公告。
- 大型攻略站/媒体：游民星空、3DM、游侠网、17173、18183、九游、TapTap、IGN、GameSpot、Polygon、Eurogamer、PowerPyx、Game8、GameWith 等。
- 玩家社区：小黑盒、NGA、贴吧、TapTap 社区、米游社或对应游戏官方社区、Steam 社区、Reddit、Discord/官方论坛、各游戏高活跃玩家论坛。
- 视频/实机：B站、抖音、小红书、YouTube、Twitch/录播、玩家实机视频、直播切片。
- Wiki/数据库：官方 Wiki、Fandom、灰机 Wiki、BG Wiki、专项数据库、物品/地图/成就数据库、维护良好的社区百科。

中文游戏或国内玩家生态强的游戏，优先补搜小黑盒、NGA、贴吧、TapTap、游民星空、3DM、游侠网、B站、抖音、小红书；海外或全球游戏优先补搜官方论坛、Steam 社区、Reddit、YouTube、Fandom/专项 Wiki、IGN/PowerPyx/Game8 等。不同游戏有自己的核心社区，按实际玩家聚集地调整，不用机械搜完整清单。

候选攻略池最低要求：
- 稳定低争议事实：至少 `1 个高可信/数据库来源 + 1 个实际攻略或实机来源`。
- 普通流程、任务、路线、收集、解谜：先发现至少 `3 个候选攻略/实机来源`；最终采信至少 `2 个独立来源` 支持核心步骤。
- Boss、Build、刷取效率、复杂路线、竞技/团本机制、资源投入等高风险实战内容：先发现 `4-6 个候选攻略/实机/社区来源`；最终采信至少 `3 个独立来源`，并覆盖至少 `2 类来源生态`，其中至少包含 `1 个玩家社区或实机复现来源`。
- 当前版本、赛季、活动、卡池、Meta、平衡、MMO职业环境等高时效内容：必须包含 `官方或当前环境来源 + 当前实机/攻略 + 当前社区反馈`。
- 如果访问限制、冷门游戏或资料稀缺导致达不到候选数量，不得硬凑；记录搜索范围和缺口，将相关结论标为 `insufficient`、`historical_only` 或 `uncertain`，并按输出规则说明。

## 三、目标对象锁定
开始攻略结论前先建立：

```text
target_identity_lock:
  game:
  exact_user_term:
  canonical_target:
  target_category:
  requested_action:
  form_or_variant:
  lifecycle_stage:
  acquisition_or_trigger_system:
  verified_aliases:
  related_but_distinct:
  excluded_entities:
  identity_evidence:
  identity_status: locked | ambiguous
```

必须确认：
- 用户说的是哪个具体游戏、作品、服务器、平台或版本分支；
- 目标是角色、宠物、Boss、任务、地点、道具、活动、装备、成就、外观、状态、资质、词条、技能、形态或其他对象；
- 用户真正问的是本体、形态/皮肤/外观、进化阶段、强化状态、资质/词条、技能槽、解锁、触发、进入、完成还是其他目标；
- 是否存在同名、相近名、玩家误称、社区混称、普通/异色/炫彩/限定/觉醒/进化形态、同家族对象、活动变体、职业专精、装备词条或地图状态；
- 相关对象或相关机制与用户目标是什么关系，是否会改变获取、触发、解锁、保底、掉落、Build、入口或步骤。

Gate：
- `identity_status=locked` 后才能生成具体攻略。
- 若歧义会改变攻略方法，先检索消歧；仍无法可靠排除时，只问最小必要澄清。
- `verified_aliases` 只能放已证明与 `canonical_target` 是同一对象的名称；玩家混称、相关形态、进化后对象、外观、资质、词条、状态、同家族对象或相关系统默认放入 `related_but_distinct` 或 `excluded_entities`。
- 禁止把近似对象、相关对象、相关形态、通用机制、同家族规则、资质/词条/状态/技能系统迁移成目标对象事实。

## 四、当前有效游戏环境
先判断该游戏实际用什么维度改变内容，不机械套版本/赛季字段。

可能维度：
- 版本、Patch、赛季、资料片、DLC、活动周期、当前卡池；
- 服务器、平台、模式、难度；
- 正式服/测试服/经典服/怀旧服；
- 其他会改变地图、任务、Boss、Build、掉落、获取方式或入口的条件。

内部记录：

```text
current_game_context:
  game:
  relevant_context_dimensions:
  active_context:
  user_specified_context:
  verified_at:
  time_anchor:

current_context_lock:
  active_context:
  locked: true
```

规则：
- `verified_at/time_anchor` 必须记录本次确认时间，并用来判断当前版本、赛季、活动、卡池、轮换和限时内容是否仍在有效期；不能只展示时间却不用它验真。
- 用户未指定历史环境时，默认回答当前有效环境。
- 当前环境一旦锁定，所有时效敏感内容都必须与它兼容。
- 与当前环境不一致的历史来源默认不能作为当前步骤。
- “常驻、永久、当前可刷、稳定获取、池内目标、当前机制”等词必须带环境范围；历史环境中的常驻只代表该历史环境常驻，不能自动升级为当前常驻。

## 五、当前可用性与当前规则
对“怎么获得/抓/兑换/解锁/触发/进入/完成/参加”等请求，必须先判断目标当前是否存在有效执行路径：

```text
availability_gate:
  status: available | unavailable | limited | uncertain
  current_method_exists:
  availability_conditions:
  evidence:
```

状态含义：
- `available`：当前存在正常有效路径，但不代表旧方法仍有效。
- `limited`：仅在特定时间、活动、服务器、平台、模式、条件或返场状态下可用；先写限制，再验证方法。
- `unavailable`：当前不可获取/触发/进入/完成/参与；停止生成当前步骤，可补充可靠历史时期和历史方法，并标注当前不可执行。
- `uncertain`：当前状态无法确认；继续检索，禁止用旧攻略自动补位。

若 `available / limited` 且用户问当前具体方法，还必须建立：

```text
current_rule_snapshot:
  current_method:
  mechanism_generation:
  target_in_current_pool: yes | no | unknown | not_applicable
  carryover_status: current_specific | cross_context_verified | historical_only | changed | unknown
  method_components:
    - name:
      type: activity | item | entrance | shop | drop | pity | spawn | quest | npc | map | system
      method_environment:
      validity_window:
      current_status: active | removed | expired | changed | uncertain
      evidence:
  requirements:
  limitations:
  verified_at:

current_rule_evidence:
  status: confirmed | supported | insufficient | speculative
  evidence:
```

当前规则 Gate：
- `confirmed`：可写成当前默认攻略。
- `supported`：只能作为明确条件下的 `conditional` 方案。
- `insufficient`：不能生成确定步骤；继续检索或说明未确认。
- `speculative`：爆料、猜测、推断、未经验证转载，禁止作为攻略。
- 历史方法要进入当前攻略，必须同时满足 `temporal_compatibility=verified_current`。

方法组件 Gate：
- 目标当前可用，不等于旧方法组件当前可用。
- 当前环境存在某个系统、盒子、卡池、活动或机制，不等于目标对象在当前池内，也不等于旧目标名单、旧保底、旧掉落或旧触发规则仍有效。
- 活动、入口、道具、商店、掉落池、刷新池、保底机制、NPC、任务阶段、地图状态等会影响步骤的组件，必须记录 `method_environment` 和 `current_status`。
- 对抽取、刷新、掉落、盒子、池子、商店、兑换、活动轮换等内容，必须单独验证 `target_in_current_pool`；没有当前池名单或当前实测证据时，不得写成当前可刷/常驻。
- 只有 `current_status=active` 且证据来自当前环境，组件才能进入当前步骤。
- `removed/expired/changed/uncertain` 的组件只能作为历史、变更或不确定信息，不能写入当前操作流程。
- 若所有当前组件都无法确认，不能为了完整性生成 Step 01/02/03。

## 六、历史资料使用
历史资料默认只能证明其历史时期。只有确认机制仍兼容，才能继承为当前规则。

```text
source_game_context:
context_compatibility: compatible | incompatible | uncertain
temporal_compatibility: verified_current | historical_only | incompatible | uncertain
```

使用规则：
- `compatible` 只说明来源环境兼容；`verified_current` 才说明历史规则已被当前证据重新确认。
- 当前资料不足不等于可自动回退旧攻略。
- 允许历史补充当前攻略的条件：目标当前仍有效、当前资料缺细节、历史机制被当前证据重新确认、且被继承的只是同一机制层级；池名单、常驻状态、掉落目标、保底、入口、活动道具和刷新目标必须逐项达到 `temporal_compatibility=verified_current`。
- 当前不可用时，只回溯判断当前状态和说明历史所需的信息，不机械考古完整生命周期。
- 输出历史信息时必须标注历史环境，禁止把多个历史环境拼成当前方案。

按需记录：

```text
target_lifecycle:
  introduced_context:
  historical_acquisition_methods:
  latest_known_change:
  current_status:
```

## 七、候选攻略与证据矩阵
第一轮先发现候选，不能看到第一篇攻略就采用。搜索组合优先包含：
- 精确游戏名；
- `target_identity_lock` 中的目标名和必要别名；
- 用户要完成的动作；
- 当前有效环境关键词；
- 平台、服务器、模式、难度；
- 攻略、路线、实机、打法、Build、位置、前置、失效、改版等任务关键词。

候选攻略可以来自公开图文攻略、实机视频、Wiki/数据库、玩家社区复盘和评论反馈。可以综合多个公开攻略、实机视频和社区反馈，提炼为新的可执行步骤；不得整段复制原文或照搬他人完整排版。公开攻略中的真实游戏截图、游戏内地图/UI图或实机视频帧可作为候选视觉素材，但必须按 `media.md` 验证真实、适用、可追溯，并放在对应步骤附近。

把整篇攻略拆成可验证的 `candidate_claims`，例如入口位置、前置任务、钥匙用途、Boss前摇、安全点、当前获取规则、Build优先级。每条核心结论检查：

```text
candidate_claim:
  subject:
  action:
  system:
  relation_to_target:
target_match:
target_specific_evidence:
direct_evidence:
current_context_evidence:
evidence_supports:
evidence_scope:
claim_environment:
method_environment:
method_component_status:
validity_window:
mechanism_generation:
target_in_current_pool:
carryover_status:
source_game_context:
context_compatibility:
temporal_compatibility:
applicability_conditions:
negative_evidence:
```

硬规则：
- 通用机制真实，不等于目标对象适用；必须有直接连接目标对象与结论的证据。
- 相关对象、相关形态、进化阶段、外观/皮肤、资质/词条、强化状态、技能槽、同家族对象、活动变体或地图状态的证据，只能支持其自身 claim；不能自动支持用户目标的获取、触发、解锁、保底、掉落、入口、Build 或当前可用性。
- 一条证据只支持“当前存在”时，不能扩展证明当前方法、保底、掉率或其他未被支持的规则。
- 每条获取途径、入口、活动、道具、兑换、掉落、刷新、保底或任务步骤都必须标明所属环境；`method_environment` 与 `current_context_lock` 不一致时，默认只能作历史信息。
- “某环境常驻/池内/可刷”只能证明该环境；若当前环境不同，必须重新验证当前池名单、当前常驻状态和当前机制代际。
- 跨版本/赛季继承必须拆层判断：底层机制可复用，不代表目标名单、概率、保底、入口、活动道具或触发流程可复用。
- 若 `relation_to_target` 不是 `same_target`，该 claim 默认不能进入当前默认攻略；除非用户明确询问关系差异，或该关系是完成目标的已验证必要前置。
- 核心攻略不能依赖单一未经验证来源。
- 热度、点赞、播放、收藏、排名只能作为发现信号，不能作为真实性证据。
- 互相转载、搬运、同一视频切片、同一 Wiki 改写、共享同一错误或截图，原则上算同一来源链。

建议维护：

```text
verified_facts:
target_identity_lock:
current_game_context:
current_context_lock:
availability_gate:
current_rule_snapshot:
current_rule_evidence:
target_lifecycle:
candidate_claims:
source_matrix:
community_consensus:
negative_evidence:
accepted_claims:
conditional_claims:
rejected_claims:
uncertain_points:
player_specific_constraints:
```

## 八、来源生态与验证强度
不同来源解决不同问题：

| 来源 | 适合确认 | 注意 |
|---|---|---|
| 官方 | 版本、活动、卡池、模式规则、系统机制、开放状态 | 通常不够解决隐藏路线、实战打法和效率 |
| Wiki/数据库/维护站 | 固定位置、任务链、道具、NPC、数据、前置 | 必须确认维护状态和环境 |
| 实机视频/高质量作者 | 路线、入口、Boss动作、Build运行、解谜、建造 | 必须确认发布日期和实际游戏环境 |
| 玩家社区 | 当前复现、失败点、机制失效、共识、争议 | 不能替代官方基础事实，但对可重复性关键 |
| 搜索摘要/聚合页/低质转载 | 发现线索 | 不直接作为核心事实 |

最低强度：

| 类型 | 最低要求 |
|---|---|
| 稳定低争议事实 | 1个高可信资料源 + 1个实际攻略或实机来源 |
| 普通流程/任务/路线/收集/解谜 | 先发现至少3个候选攻略/实机来源；最终采信至少2个独立来源支持核心步骤 |
| 实战型攻略 | 先发现4-6个候选攻略/实机/社区来源；最终采信至少3个真正独立来源，覆盖2类来源生态，含1个玩家/社区型来源，并查负面反馈 |
| 高时效内容 | 官方最新信息 + 当前环境实测/实机 + 当前社区反馈 + 目标特异性证据 |
| 高风险决策 | 核验当前规则、用户条件、成本收益、反例和不确定边界 |

若存在足够强的一手直接证据，可降低数量要求，但不得跳过当前环境、当前可用性、目标特异性和反证检查。

来源独立性快速判断：
- 相同截图、相同路线图、相同文案结构、相同错误、搬运同一视频、同一 Wiki 改写、同一作者多平台分发，原则上只算同一来源链。
- 评论区大量复述但没有实机、版本、条件或复现细节，只能作为关注信号。
- 一个来源可以支持它实际证明的 claim，不能从“目标存在”扩展成“旧方法仍有效”。

## 九、社区共识与负面反证
主动搜索与任务相关的反面词：
- 失效、不行、失败、找不到、改版、修复、前置、旧版本、骗人、毒攻略；
- 以及该游戏社区常用同义表达。

负面反馈分类：

| 类型 | 示例 | 处理 |
|---|---|---|
| 可解释 | 版本、平台、难度、任务阶段、角色/职业、缺前置、操作条件不同 | 标为 `conditional`，正文写清条件 |
| 不可解释 | 当前环境多名独立玩家失败、实机与攻略冲突、跨来源无法复现 | 标为 `rejected`，禁止推荐 |

若社区正负冲突，继续查适用条件、当前环境、实机证据和来源独立性。无法解释的大量失败优先阻止输出，而不是用“高赞”压过去。

## 十、结论状态
候选结论最终只能进入四类：

| 状态 | 条件 | 输出方式 |
|---|---|---|
| `accepted` | 目标匹配、证据直接支持、环境兼容、必要时有当前证据、无无法解释的强反证 | 可作为默认攻略 |
| `conditional` | 结论成立但依赖平台、版本、难度、任务阶段、角色、资源、操作或证据强度边界 | 必须写明条件 |
| `rejected` | 对象不匹配、环境不兼容、证据不支持、历史已失效、强反证无法解释、疑似同源误传 | 禁止进入主推荐 |
| `insufficient` | 搜到线索但未达到当前环境、目标特异性、来源独立性、实机复现或反证检查要求 | 不能生成确定步骤；可说明已知线索、缺口和下一步核验 |

## 十一、历史/不足资料标识
遇到过期攻略、资料不足或无法确认当前有效性时，不要空白交付，也不要包装成现行攻略。按以下标识输出：

| 标识 | 使用条件 | 允许输出 |
|---|---|---|
| 当前可执行 | `availability_gate=available/limited` 且当前规则证据 `confirmed` | 可给当前步骤、路线和执行建议 |
| 条件可执行 | 只在特定版本、平台、活动、任务阶段、角色或难度下成立 | 先写条件，再给条件内步骤 |
| 历史攻略，当前不可执行 | 来源只证明旧版本/旧赛季/旧活动，或当前证据确认已失效 | 可写历史时期、当时方法、当前状态；不能写成 Step-by-Step 操作 |
| 疑似过期，未确认当前仍有效 | 来源较旧且缺少当前复现，尚未证明失效 | 只能作为线索；不得进入主方案 |
| 未找到可靠当前攻略 | 已扩大来源仍缺少足够证据 | 说明已确认内容、搜索范围、缺口、用户可补充的信息或下一步核验方式 |

历史信息要“非执行化”：使用摘要、对照表或时间线，不使用“前往、刷取、推荐路线、效率技巧、Step 01/02/03、照做”等当前执行口吻。若仍存在已确认当前途径，历史信息必须放在当前方案之后或次级区。

## 十二、任务验真重点
| 任务 | 重点验证 |
|---|---|
| `walkthrough` | 当前章节/关卡状态、前置、连续流程、阶段切换、检查点 |
| `quest` | 任务名、阶段、NPC/触发状态、前置、分支、时间/天气/剧情状态 |
| `navigation` | 起点、路线、入口、地上/地下层级、中途地标、终点现场 |
| `combat-and-boss` | Boss版本/难度、阶段、前摇、站位、躲法、输出窗口、失败原因 |
| `build` | 当前版本数值、装备/技能/卡组协同、用户资源、替代件、Meta变化 |
| `character-and-team` | 角色定位、队伍协同、养成成本、用户已有角色、当前环境适配 |
| `puzzle` | 机关状态、线索、交互顺序、视角、重置条件 |
| `collection-and-achievement` | 目标唯一性、地图版本、前置、隐藏入口、收集状态、遗漏点 |
| `beginner` | 当前阶段、系统开放顺序、资源误用风险、短期生存/成长目标 |
| `resource-and-efficiency` | 成本、收益、机会成本、限时性、不可逆决策、账号条件 |

## 十三、无法充分验证时
如果无法确认核心事实：
- 明确说明已确认、未确认和风险边界；
- 不生成确定步骤；
- 不用旧攻略或相近对象补位；
- 可给出下一步核验方式或需要用户提供的最小信息。

## 十四、停止型 Gate
任一情况出现时停止生成当前确定攻略，返回检索或澄清：
- `target_identity_lock` 未锁定；
- 当前环境未确认且问题时效敏感；
- 需要可用性判断但 `availability_gate` 未建立；
- 用户问当前具体方法，但 `current_rule_snapshot` 未建立；
- 当前默认方法的 `current_rule_evidence.status` 不是 `confirmed`；
- `supported` 未写条件却准备作为默认方案；
- `insufficient / speculative` 准备进入步骤；
- 当前不可用却准备输出历史方法为当前步骤；
- 旧环境活动/入口/道具/商店/掉落池/刷新池/保底/NPC/任务阶段准备进入当前步骤；
- 历史环境的常驻、池内、盒子/卡池/掉落名单、保底或刷新规则准备写成当前事实；
- 当前环境只有机制存在证据，却没有目标当前池内或当前可用证据；
- 方法组件 `current_status` 为 `removed/expired/changed/uncertain` 却准备进入当前操作流程；
- 只有历史证据，没有 `temporal_compatibility=verified_current`；
- 只有通用机制证据，没有目标特异性证据；
- 相关对象/形态/系统证据正被用于证明当前目标的核心方法；
- `verified_aliases` 未证实同一对象，或 `related_but_distinct` 正被并入默认攻略；
- 核心攻略只来自单一来源或同源转载；
- 重要方案存在无法解释的持续失败反馈；
- `rejected_claims` 准备进入最终产物。

## 十五、检索完成条件
进入输出前至少完成：
- 游戏与目标对象锁定；
- 当前有效环境与必要 `verified_at`；
- 需要时完成 `availability_gate`、`current_rule_snapshot`、`current_rule_evidence`；
- 需要时完成 `method_components` 的环境归属和当前状态检查；
- 需要时完成当前机制代际、有效期、目标当前池内/常驻状态和跨环境继承状态检查；
- 关键 `candidate_claims` 拆解并逐条判定；
- 来源环境和独立性检查；
- 目标特异性、直接证据和当前环境证据检查；
- 别名、相关对象、相关系统和证据作用域检查；
- 玩家社区或实机复现检查；
- 重要负面反馈扫描；
- `accepted_claims`、`conditional_claims`、`rejected_claims` 分离；
- `insufficient`、`historical_only`、过期或疑似过期资料已按标识分离；
- 用户条件和适用边界记录。
