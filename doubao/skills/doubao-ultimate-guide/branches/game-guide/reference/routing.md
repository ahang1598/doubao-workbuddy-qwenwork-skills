# 路由与需求拆解规则
本文件负责游戏识别、需求原子化、任务路由、游戏类型路由、信息缺口处理和 reference 精确调用。只决定“用户要解决什么、需要读取哪些规则”，不负责具体攻略内容。
## 一、执行顺序
必须按以下顺序处理：
1. 初步解析用户输入，提取 `game_hint`、`final_goal`、`atomic_needs[]`、`player_context` 和 `input_evidence`。
2. 识别并确认 `game` 与必要的 `version_context`。
3. 完善需求原子并整理 `dependencies`。
4. 判断 `missing_information.blocking` 与 `missing_information.non_blocking`。
5. 确定 `primary_task` 与必要的 `secondary_tasks[]`。
6. 确定 `primary_game_type`、`mechanic_focus` 与必要的 `secondary_game_types[]`。
7. 生成精确的 `required_references[]` 和 `optional_references[]`。

内部路由结果至少包含：

```text
game:
version_context:
input_evidence:

final_goal:
atomic_needs:
dependencies:

player_context:
missing_information:
  blocking:
  non_blocking:

primary_task:
secondary_tasks:

primary_game_type:
mechanic_focus:
secondary_game_types:

required_references:
optional_references:
```
该结构仅用于内部处理，不要求原样展示给用户。
## 二、初步需求解析
在确认游戏前，先理解用户要解决什么。不得因为游戏名不明确而跳过需求拆解。
### `game_hint`
记录用户明确给出的游戏名、简称、截图线索、角色/BOSS/地点/道具/术语等识别线索。
若同一术语可能指向本体、形态/皮肤/外观、进化阶段、强化状态、资质/词条、技能、活动变体、同家族对象或玩家社区混称，先记录为身份歧义，不在路由阶段自行合并，交由 `retrieval.md` 的 `target_identity_lock` 锁定。
### `final_goal`
用户最终希望达成的核心结果。单个处理单元只能有1个 `final_goal`。若用户提出多个互不依赖的并列目标，则分别建立独立处理单元。
### `atomic_needs[]`
只有满足以下任一条件时才拆成独立需求原子：
- 需要独立检索；
- 需要调用不同任务规则；
- 需要独立执行步骤；
- 会改变玩家决策；
- 需要独立视觉辅助；
- 是完成最终目标不可缺少的前置。

不得将同一连续流程机械过度拆分。
### `input_evidence`
记录判断用户当前状态和需求的直接依据，包括：
- 用户明确文字描述；
- 用户上传的截图或其他游戏画面；
- 当前对话中已确认的信息。

证据优先级：用户当前明确描述/截图 > 已确认对话上下文 > 联网资料 > 推断。联网资料用于核验游戏事实，不得覆盖用户自己的实际游戏状态。
## 三、游戏识别
优先使用用户明确给出的游戏名称；未明确时，根据 `game_hint` 结合联网检索确认。

处理原则：
- 能唯一确认：直接确定。
- 存在简称、同名或作品代数歧义：结合上下文、截图和联网结果消歧。
- 联网可以确认：直接确认，不追问。
- 仍存在多个高可能结果，且不同结果会导致完全不同攻略：只问1个最小必要澄清问题。
- 不得在低置信度下硬猜游戏、作品代数、平台或版本。

`version_context` 只记录会影响答案的版本、赛季、DLC、资料片、平台、服务器、模式或难度；不影响答案时不机械补全。多轮对话优先沿用已确认信息，用户提供新信息时更新，不重复询问。
## 四、需求原子完善与依赖关系
补充用户未明确提出但完成 `final_goal` 必须解决的隐含必要需求，例如任务前置、解锁条件、获取路线或关键机制。不得为了内容完整补充与目标无关的知识。

将需求原子按真实执行关系标记为：
- `prerequisite`：完成目标前必须满足；
- `core_blocker`：用户当前真正卡住的问题；
- `follow_up`：解决核心卡点后必须继续完成；
- `supporting`：提高成功率或理解度，但不是必需。

默认按 `prerequisite → core_blocker → follow_up → final_goal` 组织；`supporting` 插入真正需要的位置。若用户提问顺序与实际执行顺序不同，以真实依赖顺序为准。
## 五、玩家上下文
从 `input_evidence` 和已确认上下文中提取：
- `stage`：章节、区域、任务阶段、等级、世界进度；
- `character_or_class`：角色、职业、英雄；
- `equipment_or_build`：装备、武器、技能、天赋、Build；
- `team_or_deck`：队伍、阵容、卡组；
- `resources`：货币、材料、体力、抽卡资源、时间；
- `skill_level`：新手、普通、进阶或明确操作水平；
- `constraints`：无氪、单人、低配、不使用某角色等硬限制；
- `preferences`：稳过、最快、低操作、低成本、全收集等偏好；
- `spoiler_level`：默认 `minimal`，用户明确要求后调整。

只记录已知信息；无法确认的内容保持未知，不自行补造。
## 六、信息缺口处理
将缺失信息分为：
### `missing_information.blocking`
缺失后会直接导致主任务判断、游戏识别或核心攻略方案明显错误，且无法通过联网或条件分支覆盖。
### `missing_information.non_blocking`
不影响核心答案，或可通过联网、条件分支、通用安全方案覆盖。

处理顺序：
1. 联网可确认 → 直接检索；
2. 不影响核心答案 → 保持未知并继续；
3. 可用2–3个真正有差异的条件分支覆盖 → 直接给分支；
4. 可先提供通用可靠方案 → 先处理，并标明不同条件下的调整；
5. 仅存在 `blocking` 且无法通过以上方式解决时 → 只问1个最小必要澄清问题。

禁止为了补齐字段机械追问；禁止重复询问已提供或已确认的信息。
## 七、任务路由
根据 `final_goal` 和 `core_blocker` 选择 `primary_task`，必须且只能有1个。

主任务判定优先级：
1. 用户明确卡在某个具体步骤时，优先以 `core_blocker` 决定主任务。
2. 用户要求完整从当前状态到目标的整体攻略时，以 `final_goal` 对应的整体处理方式决定主任务。
3. 两者仍冲突时，选择最能决定主体输出结构的任务作为主任务，其余作为辅助任务。

任务映射：
- `walkthrough`：章节、区域、关卡或整体流程推进；
- `quest`：主线、支线、NPC或隐藏任务的触发、继续或完成；
- `navigation`：地点、入口、NPC、道具位置或具体路线；
- `combat-and-boss`：击败敌人/BOSS、处理战斗机制或提高战斗成功率；
- `build`：装备、武器、属性、技能、天赋、卡组或构筑体系；
- `character-and-team`：角色/职业培养、配队、阵容或协同；
- `puzzle`：机关、密码、环境谜题或逻辑谜题；
- `collection-and-achievement`：收集、成就、奖杯、全收集或易遗漏内容；
- `beginner`：入门、开局、前期发展、系统理解或新手避坑；
- `resource-and-efficiency`：资源投入、抽取、升级优先级、时间或效率规划。

`secondary_tasks[]` 仅在其他需求原子需要独立规则才能完成最终目标时加入，通常不超过2个。不要因为正文中顺带涉及路线、装备或战斗就全部加载。
## 八、游戏类型路由
按“当前问题依赖的核心玩法机制”确定 `primary_game_type`，不得按游戏本身全部类型标签分类。

类型映射：
- `rpg-open-world`：任务状态、角色成长、开放探索、装备Build、NPC或分支是核心；
- `action-adventure`：即时操作、关卡推进、动作时机、环境互动是核心；
- `strategy-simulation`：局面判断、经营、资源配置、发展路线和决策权衡是核心；
- `card-roguelike`：随机资源、卡组/流派构筑、局内动态选择和协同是核心；
- `competitive`：PvP对局、地图战术、英雄/武器Meta、操作和实时决策是核心；
- `mmo`：职业、装备成长、多人副本、团队职责、资料片或赛季环境是核心；
- `gacha-live-service`：有限资源、抽取、养成、账号价值和持续版本规划是核心；
- `puzzle-survival-sandbox`：解谜、生存阶段、采集制作、建造、开放目标或创造玩法是核心。

同时确定 `mechanic_focus`，用于标记当前问题在大类中的具体机制焦点，例如：
- `competitive`: `fps` / `tps` / `moba`;
- `puzzle-survival-sandbox`: `puzzle` / `survival` / `sandbox`;
- `rpg-open-world`: `rpg` / `arpg` / `open-world`;
- 其他类型按当前问题填写最能缩小规则范围的机制关键词。

只有第二种玩法机制会实质改变攻略策略时，才加入 `secondary_game_types[]`，通常不超过1个。
## 九、Reference 精确调用
路由结束后必须直接生成文件清单，不再让后续步骤重新判断该读什么。
### `required_references[]`
必须包含：
- `reference/retrieval.md`
- `reference/media.md`
- 对应 `primary_task` 的具体文件
- 对应 `primary_game_type` 的具体文件
### `optional_references[]`
仅在确实需要时包含：
- `secondary_tasks[]` 对应文件；
- `secondary_game_types[]` 对应文件；
- `reference/examples.md`。

主任务文件映射：
- `walkthrough` → `reference/tasks/walkthrough.md`
- `quest` → `reference/tasks/quest.md`
- `navigation` → `reference/tasks/navigation.md`
- `combat-and-boss` → `reference/tasks/combat-and-boss.md`
- `build` → `reference/tasks/build.md`
- `character-and-team` → `reference/tasks/character-and-team.md`
- `puzzle` → `reference/tasks/puzzle.md`
- `collection-and-achievement` → `reference/tasks/collection-and-achievement.md`
- `beginner` → `reference/tasks/beginner.md`
- `resource-and-efficiency` → `reference/tasks/resource-and-efficiency.md`

游戏类型文件映射：
- `rpg-open-world` → `reference/game-types/rpg-open-world.md`
- `action-adventure` → `reference/game-types/action-adventure.md`
- `strategy-simulation` → `reference/game-types/strategy-simulation.md`
- `card-roguelike` → `reference/game-types/card-roguelike.md`
- `competitive` → `reference/game-types/competitive.md`
- `mmo` → `reference/game-types/mmo.md`
- `gacha-live-service` → `reference/game-types/gacha-live-service.md`
- `puzzle-survival-sandbox` → `reference/game-types/puzzle-survival-sandbox.md`

禁止一次性加载全部任务文件或全部游戏类型文件。
## 十、复杂请求
复合请求先确定唯一 `final_goal` 和真正的 `core_blocker`，再用 `dependencies` 串联其他需求。只选择1个主任务和1个主游戏类型，只加载完成目标确实需要的辅助文件。

若用户提出多个完全独立的最终目标，则分别建立独立路由单元，并按用户原始优先级或明确顺序处理，不强行合并成一条流程。
## 十一、路由完成条件
进入检索和攻略生成前，至少必须明确：
- `game`
- `final_goal`
- `primary_task`
- `primary_game_type`
- `required_references[]`

尽可能同时明确：
- `core_blocker`
- `dependencies`
- `player_context`
- `version_context`
- `mechanic_focus`

缺失的非阻塞信息不得阻塞任务。路由完成后按 `required_references[]` 读取文件，按需读取 `optional_references[]`；最终输出前再读取 `reference/quality-check.md`。
