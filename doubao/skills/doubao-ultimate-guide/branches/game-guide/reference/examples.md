# 游戏攻略路由、验真与输出示例
本文件只在路由、当前环境、验真、视觉素材或输出格式存在歧义时按需读取。示例用于说明判断方式，不替代 `routing.md`、`retrieval.md`、`media.md`、`output.md`、`quality-check.md` 和具体任务/游戏类型规则，也不提供可脱离验证复用的游戏事实。

## 目录
- 使用边界
- 任务与游戏类型路由
- 当前环境与可用性
- 攻略验真与反证
- 视觉素材
- 输出格式
- 完整复杂请求
- 常见误路由

## 一、使用边界
按需读取本文件的情况：
- `primary_task`、`primary_game_type` 或 `atomic_needs` 难以判断；
- 同一请求含多个任务，或游戏有多个类型标签；
- 不确定辅助任务/辅助游戏类型是否真的需要加载；
- 不确定当前有效环境、当前可用性、历史规则是否延续；
- 不确定当前仍可获取是否等于历史方法仍有效；
- 不确定 `current_rule_evidence` 是否足以输出当前步骤；
- 不确定多个攻略来源是否独立，或高赞攻略能否采用；
- 社区正负反馈冲突；
- 不确定图片是否真实且有用；
- 不确定最终应输出飞书文档还是HTML。

示例判断始终围绕：用户真正目标、核心玩法机制、当前有效环境、目标当前可用性、当前具体规则证据、验真结论、视觉素材用途和最终产物可独立使用性。

## 二、任务与游戏类型路由
| 用户请求 | `primary_task` | `primary_game_type` | 关键判断 |
|---|---|---|---|
| “我在附近传送点，怎么过去拿这个神瞳？” | `navigation` | `rpg-open-world` | 目标是从当前起点到真实入口/目标；不能只给坐标或终点图，需起点、路线、层级、入口、取得确认 |
| “支线让我找NPC，到地方没人，是Bug吗？” | `quest` | `rpg-open-world` | 核心是任务为何不推进，不是单纯NPC位置；需阶段、前置、世界状态、时间/天气/分支 |
| “Boss二阶段大范围攻击秒我，用近战怎么躲？” | `combat-and-boss` | `action-adventure` | 需写“看到什么→何时停手→往哪躲→何时输出”，不能只说及时闪避 |
| “卡牌肉鸽已拿两张毒牌，又出毒核心和强通用卡，选哪个？” | `build` | `card-roguelike` | 根据当前局内 commit signal、稳定性、生存和后续Boss判断；不是静态单卡Tier |
| “MOBA上单，对面三个AD，还照推荐出装吗？” | `build` | `competitive` | 根据当前英雄、赛季/平衡、伤害结构、经济和局势调整装备顺序 |
| “MMO团本三阶段我是治疗该看什么？” | `combat-and-boss` | `mmo` | 优先治疗职责视角，确认资料片、小版本、难度，不默认展开全职业时间轴 |
| “160抽，已有一队，下版本想抽另一个角色，当前卡池值不值得？” | `resource-and-efficiency` | `gacha-live-service` | 核心是有限抽卡资源决策，不是角色培养；需当前卡池、未来规划、账号条件和机会成本 |
| “生存游戏第二天食物不够，还要不要先找矿？” | `beginner` | `puzzle-survival-sandbox` | 当前生存循环优先，不直接给长期科技路线 |
| “模拟经营生产线堵了，要不要加机器？” | `resource-and-efficiency` | `strategy-simulation` | 先定位瓶颈、物流、输入输出和消耗，不因原料多就加产线 |
| “沙盒自动化机器怎么摆？” | `build` 或 `walkthrough` | `puzzle-survival-sandbox` | 若目标是结构方案用 `build`，若是从无到有建造流程用 `walkthrough` |

同一个游戏不固定绑定一个类型。例如开放世界游戏中：找入口可为 `navigation + rpg-open-world`；Boss操作可为 `combat-and-boss + action-adventure`；抽卡取舍可为 `resource-and-efficiency + gacha-live-service`。按当前问题依赖的机制判断。

复合请求先确定唯一 `final_goal` 和 `core_blocker`。例：“任务找不到入口，进去以后Boss也打不过”通常拆为入口路线和Boss处理，但主任务取决于当前卡点；若入口是先决条件，先处理 `navigation`，Boss作为后续需求。

## 三、当前环境与可用性
### 对象关系混淆
用户问“某目标怎么获得”时，检索发现多个相关项：

```text
A: 用户原词对应的目标
B: 相近名称或社区混称
C: 进化后形态 / 外观皮肤 / 颜色变体
D: 资质、词条、技能槽、强化状态或相关系统
E: 同家族对象、活动变体或历史版本对象
```

正确处理：
- `canonical_target` 只锁定用户真正目标；
- 只有已证明与目标同一对象的名称进入 `verified_aliases`；
- B/C/D/E 默认进入 `related_but_distinct` 或 `excluded_entities`；
- 证据若只证明 C/D/E，不能支持 A 的获取、触发、解锁、保底、掉落、入口、Build 或当前可用性；
- 最终产物只围绕 `canonical_target + requested_action`，相关项只作简短消歧或必要前置。

错误写法：

```text
目标A名称相近于C
+ C有完整进化/解锁攻略
→ 输出C作为A的当前获取攻略
```

正确写法：

```text
目标A:
  等待直接证据确认获取方式

相关项C:
  related_but_distinct
  不进入A的默认攻略
```

### 当前获取方式
用户问“这个宠物怎么抓/角色现在怎么拿/活动还能换吗”时，不能直接套历史攻略。正确顺序：

```text
确认当前有效环境
→ 记录 verified_at
→ 判断目标当前是否可用 availability_gate
→ available / limited: 建立 current_rule_snapshot 并验证 current_rule_evidence
→ unavailable: 停止当前步骤，说明历史时期和历史方法
→ uncertain: 继续检索，禁止旧攻略补位
```

`availability_gate.status=available` 只证明当前有渠道，不证明历史方法仍有效。只有 `current_rule_evidence.status=confirmed` 才能生成当前默认步骤；`supported` 必须条件化；`insufficient/speculative` 不输出确定步骤。

### 方法组件属于旧环境
用户问“某目标现在怎么获得”，当前环境是新赛季/新版本，但候选攻略来自旧环境：

```text
current_context_lock:
  新赛季

candidate_method:
  旧赛季活动道具
  旧赛季入口
  旧赛季刷新池
  旧赛季保底机制

method_components:
  current_status:
    expired / removed / changed
```

正确处理：
- 当前正文先写“当前新赛季没有该旧方法，不能通过该方式获得”；
- 历史方式标题写“历史方式（旧赛季，当前不可执行）”；
- 只列当前证据确认仍存在的剩余途径；没有就写“暂无可靠当前途径”；
- 不生成“去旧入口→刷旧道具→触发旧保底”的当前步骤。

错误展示：

```text
旧赛季刷取指南
1. 前往旧入口
2. 清理旧活动道具
3. 等待旧保底触发
```

正确展示：

```text
历史方式（旧赛季，当前不可执行）
| 当时方法 | 当前状态 | 说明 |
| 旧入口 + 旧活动道具 + 旧保底 | 已失效 | 仅说明过去规则，不提供当前操作步骤 |
```

### 环境维度示例
| 场景 | 相关环境 | 注意 |
|---|---|---|
| 赛季制竞技出装 | 当前赛季、当前Patch/平衡 | 使用赛季是因为玩法受赛季影响，不代表所有游戏都查赛季 |
| MMO团本机制 | 资料片、小版本、难度、服务器差异 | 旧资料片同名副本攻略不能直接采用 |
| 活动驱动手游兑换 | 当前活动状态、本次核验时间、兑换入口 | 同版本内活动结束也不能继续输出兑换步骤 |
| 单机Boss入口 | 游戏版本、DLC、平台 | 不机械搜索赛季或卡池，只确认真正影响入口的条件 |

### 历史规则三种结论
| 情况 | 记录 | 输出 |
|---|---|---|
| 历史地图/入口经当前实机确认未变 | `temporal_compatibility=verified_current` | 可作为当前攻略 |
| 只有旧赛季完整攻略，无当前复现 | `availability_gate=uncertain` 或 `current_rule_evidence=insufficient` | 不生成当前步骤，只说明旧赛季信息或继续核验 |
| 当前仍可获取但方法变了 | 历史方法 `historical_only`，当前方法 `confirmed` | 当前正文只写新方法；历史方法单独标历史 |

错误推理示例：

```text
当前帖子说“这个宠物现在还有”
→ 只能支持 current_availability
→ 不能证明旧入口、旧保底、旧获取步骤仍有效
```

证据只能支持它实际证明的 claim。

## 四、攻略验真与反证
### 高赞不等于正确
高赞视频、收藏笔记、聚合站同文案只表示值得检查。若发现它们来自同一原视频、同一Wiki、同一截图或共享同一错误，只算一个来源链。若当前环境玩家反馈“已失效”，候选应进入 `rejected` 或重新核验。

### 独立来源判断
| 表象 | 实际判断 |
|---|---|
| 5个网站都写同一路线 | 若文案/截图/错误相同，可能只有1个来源 |
| 多个短视频推荐同打法 | 若是同一视频切片或搬运，不算多源 |
| 当前帖子提到目标存在 | 不等于当前具体规则已确认 |
| 官方未写隐藏机制 | 若多个独立实机稳定复现且无强反例，可接受为实战证据 |

### 负面反馈分类
| 情况 | 判断 | 写法 |
|---|---|---|
| “NPC晚上不刷”但失败者未完成任务A，成功者都完成 | `conditional` | 写清“完成任务A并进入对应阶段后，晚上去北门” |
| 当前多平台玩家都无法复现，官方Patch说明机制改了 | `rejected` | 不再使用旧数值/路线/卡位 |
| 理论DPS最高但普通玩家大量断循环 | 条件方案 | 主推稳定方案，高操作方案写明适用条件 |

反证搜索示例：

```text
路线：游戏名 + 地点名 + 找不到 / 入口改了 / 失效 / 当前环境
Boss：游戏名 + Boss名 + 卡位失效 / 打法不行 / 修复 / 当前环境
Build：角色名 + Build + 实战 / 不好用 / 高端局 / 低段位 / 当前环境
```

## 五、视觉素材
| 情况 | 判断 |
|---|---|
| 真实截图但看不到洞口、地标、方向 | 真实但无用，`rejected` |
| 高清Boss宣传图解释技能前摇 | 非实机，`rejected` |
| 真实截图但地图状态是旧版本 | 与当前环境不兼容，`rejected` |
| 当前实机地图截图加路线、编号、入口标注 | 底图真实且未改事实，`accepted` |
| 使用地图重制MOD的入口图，用户玩原版 | MOD画面不适用，`rejected` |

真实不等于有用；有用也必须真实。图片要帮助用户判断“从哪里进、站哪里、看哪个机关、Boss什么动作时反应、菜单点哪里”。

## 六、输出格式
| 用户要求 | 输出判断 |
|---|---|
| 未指定格式，只说“写完整攻略” | 必须先实际尝试创建飞书文档并默认交付飞书；只有严格飞书失败并记录证据时才生成HTML备用 |
| 明确要飞书文档 | 必须实际创建飞书；不能创建时说明，并可提供HTML备用 |
| 明确要HTML攻略页 | 生成完整HTML文件，不是HTML片段 |

飞书 Docx XML 版式片段示例，事实内容必须替换为本次已验真的 `accepted_claims` 或条件化 `conditional_claims`：

```xml
<title>游戏名-目标对象当前获取攻略</title>
<callout emoji="📝" background-color="light-gray" border-color="gray" text-color="gray">
  <p><b>核验时间：</b>2026-07-20 16:30 CST</p>
  <p><b>当前环境：</b>写入已确认的版本、服务器、活动或卡池环境</p>
</callout>

<grid>
  <column width-ratio="0.5">
    <callout emoji="✅" background-color="light-green" border-color="green" text-color="green">
      <h3>当前状态</h3>
      <p>只写已确认的当前可用性结论。</p>
    </callout>
  </column>
  <column width-ratio="0.5">
    <callout emoji="📌" background-color="light-blue" border-color="blue" text-color="blue">
      <h3>先做这个</h3>
      <p>写玩家打开游戏后的第一步动作。</p>
    </callout>
  </column>
</grid>

<pre lang="xml" caption="攻略状态快照">
<code>&lt;攻略状态&gt;
  &lt;目标&gt;目标对象&lt;/目标&gt;
  &lt;当前结论 status="已确认"&gt;当前有效方法&lt;/当前结论&gt;
  &lt;风险&gt;不要把旧活动步骤当成当前步骤&lt;/风险&gt;
&lt;/攻略状态&gt;</code>
</pre>

<callout emoji="❗" background-color="light-yellow" border-color="yellow" text-color="yellow">
  <p><b>注意前置：</b>写清进入步骤前必须满足的条件。</p>
</callout>
<callout emoji="❌" background-color="light-red" border-color="red" text-color="red">
  <p><b>旧方法不要照做：</b>只在已验证失效时写入，并与当前步骤分开。</p>
</callout>

<grid>
  <column width-ratio="0.42">
    <img href="VERIFIED_REAL_GAME_IMAGE_URL" width="360" caption="图：地图入口、目标精灵或关键 UI 的实机画面" name="guide-step.png"/>
  </column>
  <column width-ratio="0.58">
    <callout emoji="📌" background-color="light-blue" border-color="blue" text-color="blue">
      <h3>Step 01｜看图执行</h3>
      <p><b>动作：</b>写玩家现在要点哪里、去哪里或抓什么。</p>
      <p><b>看哪里：</b>写图中用于识别的地标、外观、图标或 UI。</p>
      <p><b>成功标志：</b>写完成后任务、图鉴、背包或地图会出现什么变化。</p>
    </callout>
  </column>
</grid>
```

输出反例：
- `<img src="some-image.jpg">` 但文件不存在 → 修正路径、实际保存图片或删除图片；
- 正文写“见图3”但没有图3 → 修正编号或正文；
- 产物只有摘要/提纲/链接 → 不合格；
- Hero、快速结论或图片说明补写未验证稀有度、外观、机制 → 不合格。

## 七、完整复杂请求示例
用户：
> 我在做这个任务，现在找不到入口，进去以后Boss也打不过，帮我做个完整攻略。

处理：

```text
final_goal:
完成该任务

atomic_needs:
1. 锁定任务、当前阶段和目标入口
2. 从用户当前状态到入口
3. 进入后处理Boss关键机制
4. 给出完成确认

dependencies:
入口路线是Boss处理前置

primary_task:
navigation 或 quest（取决于当前卡点是否是任务状态还是入口路线）

secondary_tasks:
combat-and-boss

primary_game_type:
按该问题依赖机制判断，如 rpg-open-world / action-adventure
```

检索：
- 锁定任务和目标对象，排除同名任务/旧版本/不同DLC；
- 确认当前有效环境和任务阶段；
- 验证入口、前置、路线、Boss机制是否当前可用；
- 拆分 claims：入口位置、前置、路线、Boss前摇、安全站位、完成标志；
- 多来源验证并查“入口找不到/改版/Boss打法不行/卡位失效”等反证；
- 图片只用当前环境真实地图、入口截图、Boss关键动作帧。

输出：
- 默认飞书文档，除非用户指定HTML；
- 结构为“适用环境→快速结论→入口路线→Boss处理→失败排查→完成确认”；
- 当前规则未确认时不生成伪确定步骤；
- 历史入口或旧打法只能标历史，不能混入当前流程。

## 八、常见误路由
- “角色该不该抽”通常是 `resource-and-efficiency`，不是 `character-and-team`，除非用户问培养或配队。
- “某个东西在哪”不一定是 `navigation`；若本质是任务状态导致对象不出现，应为 `quest`。
- “打不过”不一定主任务是战斗；若失败根因是Build、等级、前置或队伍错误，主任务应随核心阻塞变化。
- “新手怎么玩”不是全游戏百科；应围绕当前阶段、资源误用风险和短期目标。
- 游戏有多个类型标签时，不要全部加载；只选当前问题真正依赖的机制。
- 同一句请求有多个目标时，不强行合并；若目标互不依赖，按独立处理单元分别路由。

## 九、时效性总边界
无论示例如何简写，涉及当前获取、抓取、兑换、解锁、触发、进入、完成、活动、卡池、Build、Meta、Boss机制、地图入口和效率数值时，都以 `retrieval.md` 的当前环境、可用性、当前规则证据、历史兼容和负面反证 Gate 为准。示例不能降低正式规则强度。
