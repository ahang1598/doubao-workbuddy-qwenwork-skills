# 项目、分集与素材 Manifest Ref

当项目初始化、接收用户素材、进入任一生产阶段、恢复中断任务或交付分集时读取本文件。本文件是目录、命名、JSON 字段、枚举、基数和引用关系的唯一权威；创作正文仍以 Markdown 为准，不在 JSON 中复制整篇正文。

## 权威引用

- 规划字段及确认事务：`planning.md`。
- 剧本、分镜、资产、视频和成片的内容规则：对应阶段 Reference。
- 本文件只定义目录、命名、JSON schema、引用关系、状态和基数；不重新定义生成算法、创作阈值或人工审美标准。
- 本文件定义的 schema、基数和引用关系，以及对应阶段权威 Reference 定义的准出条件，是产物合同。

## 设计原则

- 完整模式单集只写一份 `episodes/ep_1/01_剧本/剧本_完整剧本_ep_1.md`，兼作项目故事与本集执行正文；多集先写根目录 `01_剧本/剧本_全局设定与分集总纲.md`，覆盖全剧走向、全部分集、人物、伏笔与最终结局，随后逐集写当前集完整正文。必要设定并入正文，机器资料从正文派生。轻量剧本目标保存唯一正文，其他目标不额外复制独立剧本。单集同一正文一次展示确认，按同一实际回复记录两个作用域；多集按不同内容实际确认。
- 项目级 JSON 管理跨集事实、来源、项目数据卡、共享资产、跨集接缝与索引；分集 JSON 管理本集状态、引用和阶段产物。
- 项目级故事包确认后把 `current_episode` 设为 `ep_1`，从该集详细剧本开始逐集生产。共享资产可以在首次实际需要的分集创建并进入 `asset_registry.json`；后续集先从共享登记和已完成分集资产中复用 approved 版本，只把新增或状态变化项写入本集资产。
- 跨集稳定的角色基准图、主要场景参考图、核心道具和音色 只保存于 `shared/`，不复制到每集目录。
- 完整模式中，`00_制作控制/project_data_card.json` 是角色、场景、道具和音色“不可变身份 + 可变状态时间线”的单一事实源。下游只填写片段增量，不得手工复述另一套基础设定；轻量模式不创建该文件。
- 当集服装、伤痕、年龄、伪装和道具状态先记入数据卡；需要新增的状态媒体保存在对应 `episodes/ep_N/03_资产/`，已有视觉依据足够时登记复用。
- 为后续连续续段准备真实尾帧时使用 `FRMxxx`，记录实际来源和输入承接；不为生成后检查例行抽取首帧或中间帧。具体提取范围只按 `video.md`。
- Markdown 面向用户和人工审阅；JSON 只引用 Markdown 路径与哈希，不复制完整剧本、分镜说明或质检长文。
- 文件中的 `episode_id` 固定使用 `ep_1`、`ep_2`……；文件名最后一个业务后缀也使用 `_ep_N`，版本号放在它之前，例如 `角色_CHR001_林远_战损_v02_ep_2.png`。
- 稳定 ID 在项目内唯一。集号表示使用范围，不重新编号同一个角色、场景、道具、音色、风格、镜头、片段或帧。
- 路径全部相对项目根目录保存；每项记录包含 schema 版本和 revision。已确认版本不得原地覆盖。

## 轻量最小记录

先按 `planning.md` 的轻量分支组织内容。规划 JSON 不要求完整模式的受众、类型、亮点、视觉和六步节奏合同；除实际目标、模式、revision、用户锁定项、时长及适用参数/依赖外，在既有字段保存实际跨镜/跨场共用的创作决定，字段归属只按 `planning.md`。必要信息在原位置充分展开：共用人物/状态/调度/视听约束归规划，完整事件、人声、揭示顺序及局部变化归目标正文或十五列主表，不另建创作基准文件，不因轻量只写摘要。下面目录是可用位置，不是每次必须建齐的文件清单。

## 同一信息的承载与提取

| 信息 | 唯一维护处 | 其他文件如何使用 |
|---|---|---|
| 项目身份、实际规模与时长、模型与采用方向 | `drama_plan.json` | 项目总索引仅保存定位所需身份、规模摘要与阶段指针；摘要由规划提取，不另作决定 |
| 项目/集/阶段的文件位置 | `project_manifest.json` | 剧本索引的 `detailed_script`、`script_contract` 随当前阶段指针提取；不再独立维护第二套路由 |
| 剧情、台词与叙事顺序 | 当前采用的唯一剧本正文；轻量分镜/视频目标为唯一主表 | 剧本索引、分集合同只提取实际执行所需字段；亮点、关系、场景和人声不在 JSON 中重新创作 |
| 完整模式人物/场景/道具/声音身份与状态 | 项目数据卡；媒体版本及批准来源为资产登记 | 主表引用稳定 ID 与有效版本并写本镜变化，不复述另一套基础身份 |
| 逐镜画面、人声分配与声画时序 | 唯一十五列主表；完整模式导演总控卡仅维护共用表达策略 | 分镜 JSON 引用镜号及段间依赖，实际请求按主表展开，不另写逐镜内容副本 |

重复出现的稳定 ID 是引用；因索引或工具执行需要保留的时长摘要、人声字段和实际请求是派生值或提交快照，不是可分别编辑的创作稿。分集合同的人声从正文提取，主表保留采用原句并分配镜头，Prompt 仅作已规定的格式转写，不重新措辞；既有文本若已按用户授权修改，先更新该内容的权威源，再同步本次受影响的派生项及引用 revision/哈希，实际历史请求和真实确认原文保留。提取与同步在正常写入时完成，不增加文件、确认或检查步骤。

剧本目标正文使用 `episodes/ep_1/01_剧本/剧本_完整剧本_ep_1.md`；分镜和视频目标用十五列主表；资产目标保存实际采用设计与媒体到资产目录并由来源登记引用。没有视频调用不建视频/成片 manifest、Prompt 或确认记录占位。项目/分集索引可以预登记将用的路径，但不创建目标之后的产物。状态和同次确认作用域只按 `control-contracts.md`，不再维护一份不同的轻量推进算法。

轻量纯分镜的计划段序、镜号范围、首尾与转场、声音桥及参考依赖留在同一主表的分段说明；这属于详细分镜内容，不要求增加列、独立文件或视频执行记录。后续实际制作视频时再提取到视频 manifest；主表负责采用的镜头与衔接内容，视频记录负责实际调用分组、输入绑定与结果，不在两处另编不同的剧情。

## 统一目录

```text
<工作区>/artifacts/<项目名>/
├── 00_制作控制/
│   ├── drama_plan.json
│   ├── project_manifest.json
│   ├── project_data_card.json       # 仅完整模式
│   ├── source_manifest.json
│   ├── 制作状态.json
│   ├── 用户确认记录.jsonl
│   ├── episode_seams.json           # 仅完整模式且实际存在跨集承接
│   ├── 合规证明/                  # 仅在宿主要求审计证明时创建
│   │   ├── 合规证明_planning.json
│   │   ├── 合规证明_script.json
│   │   ├── 合规证明_assets.json
│   │   ├── 合规证明_storyboard.json
│   │   ├── 合规证明_video.json
│   │   └── 合规证明_final.json
│   ├── 输入素材/                    # 需要持久化的用户上传或外部下载文件
│   ├── 操作日志.jsonl
│   ├── 批次/
│   │   └── batch-NNN_ep_N.json
├── 01_剧本/                         # 仅完整模式
│   ├── project_script_manifest.json
│   └── 剧本_全局设定与分集总纲.md    # 仅多集；单集直接引用 ep_1 完整正文
├── shared/
│   └── 03_资产/
│       ├── 角色/
│       │   ├── 角色_CHRxxx_[名称]_[基准状态]_vNN.[ext]
│       ├── 场景/
│       │   ├── 场景_SCNxxx_[名称]_布局参考_vNN.[ext]
│       ├── 道具/
│       │   ├── 道具_PROPxxx_[名称]_[状态]_[multiview|main|detail]_vNN.[ext]
│       ├── 音色/
│       │   ├── 音色_VOICExxx_[主体]_提示词_vNN.md
│       │   ├── 音色_VOICExxx_[主体]_vNN.[ext]
│       ├── 提示词/                  # 图片实际提交文本，按资产与版本保存
│       └── asset_registry.json
└── episodes/
    ├── ep_1/
    │   ├── 01_剧本/
    │   │   ├── script_contract_ep_1.json
    │   │   └── 剧本_完整剧本_ep_1.md
    │   ├── 02_分镜/
    │   │   ├── storyboard_ep_1.json           # 仅完整模式
    │   │   ├── 导演总控卡_ep_1.md             # 仅完整模式
    │   │   ├── 分镜_完整分镜表_ep_1.md
    │   ├── 03_资产/
    │   │   ├── 角色状态/
    │   │   │   └── 角色_CHRxxx_[名称]_[状态]_vNN_ep_1.[ext]
    │   │   ├── 道具状态/
    │   │   │   └── 道具_PROPxxx_[名称]_[状态]_[multiview|main|detail]_vNN_ep_1.[ext]
    │   │   └── asset_usage_ep_1.json
    │   ├── 04_视频片段/
    │   │   ├── video_manifest_ep_1.json
    │   │   ├── 片段_SEGxxx_E01S01_vNN_ep_1.[ext]
    │   │   ├── 抽帧/
    │   │   │   ├── 抽帧_FRMxxx_SEGxxx_tail_[HH-MM-SS-ms]_vNN_ep_1.[ext]
    │   └── 05_成片/
    │       ├── delivery_manifest_ep_1.json  # 仅完整模式；轻量写 video_manifest.delivery
    │       ├── 字幕_ASR原始_vNN_ep_1.json
    │       ├── 字幕_时间轴_vNN_ep_1.srt
    │       ├── 字幕_烧录参数_vNN_ep_1.json
    │       ├── [项目名]_成片_[比例]_无字幕_vNN_ep_1.[ext]
    │       └── [项目名]_成片_[比例]_字幕烧录_vNN_ep_1.[ext]
    └── ep_2/
        └── ...
```

默认不创建阶段/视频/接缝/成片质检报告、独立连续性账本或重复媒体清单。十五列主表是唯一逐 SHOT 内容源，阅读稿由它整理；导演卡只写全局/场面策略，完整模式的 `storyboard_ep_N.json` 统一保存 SEG 分组、边界、首尾状态、参考职责与计划连续性，按需派生阅读表，不另维护 SEG Markdown。资产需求清单等视图仅在需要展示/查询时派生，不变成另一事实源。

两种模式只在实际视频调用前运行一次 `--stage video --segment SEGxxx` 集中客观查漏，不把各阶段诊断命令作为正常准出门。后续调用需要时才抽取真实尾帧并记录，无默认 start/scene/tail 全套及接缝审查文件。

### project_manifest.json

只做项目总索引，不复制 `drama_plan.json` 的创意与模型字段：

```json
{
  "schema_version": "1.0",
  "project_id": "",
  "revision": 1,
  "format_mode": "single_short|multi_episode|micro_film|long_form_video",
  "episode_count": 1,
  "episode_ids": ["ep_1"],
  "plan_path": "00_制作控制/drama_plan.json",
  "state_path": "00_制作控制/制作状态.json",
  "source_manifest_path": "00_制作控制/source_manifest.json",
  "project_data_card_path": "00_制作控制/project_data_card.json",
  "shared_asset_registry_path": "shared/03_资产/asset_registry.json",
  "episode_seams_path": "",
  "project_script_manifest_path": "01_剧本/project_script_manifest.json",
  "episodes": {
    "ep_1": {
      "episode_id": "ep_1",
      "duration_s": 120,
      "stage_manifests": {
        "script": "episodes/ep_1/01_剧本/script_contract_ep_1.json",
        "assets": "episodes/ep_1/03_资产/asset_usage_ep_1.json",
        "storyboard": "episodes/ep_1/02_分镜/storyboard_ep_1.json",
        "video": "episodes/ep_1/04_视频片段/video_manifest_ep_1.json",
        "delivery": "episodes/ep_1/05_成片/delivery_manifest_ep_1.json"
      }
    }
  }
}
```

`episode_ids`、`episodes` 的键与规划集数一致；每集的身份、时长和阶段指针直接保存在这里，不再创建独立单集入口。来源、状态、用户确认和真实操作记录各有职责，继续分别保存，不合成一份混杂的大文件。
完整全剧规模尚在建议阶段时，索引随采用建议建立，真实确认仍以状态与确认记录为准；不把建议当成已批准。仅处理已有连续剧的局部范围且全剧集数未知时，沿用可用项目记录、补当前集的实际条目，并将缺口记入现有规划依赖；不填 `episode_count=1` 冒充全剧，也不补造未知的未来集。局部文字交付不套全剧可执行索引要求；要求全剧总纲或实际生成确实依赖规模字段时，按规划在已有方案确认中确定所需规模，再补齐可执行索引，不把局部记录冒充完整全剧索引或绕过生成前必要条件。
本示例为单集，跨集路径为空；多集连续作品才填写真实接缝路径。身份和时长摘要从规划提取，不能在本索引另改一套规模。
完整模式从剧本阶段开始维护 `project_script_manifest_path` 指向的项目级剧本索引和 `project_data_card_path` 指向的项目数据卡，已有有效内容直接继承，不重新创建副本；仅实际存在跨集承接时创建接缝文件并填写 `episode_seams_path`，单集该路径留空，不创建空文件。轻量模式不建立完整模式独立剧本/资产/跨集索引，将 `project_script_manifest_path`、`project_data_card_path`、`shared_asset_registry_path` 和 `episode_seams_path` 留空，不得为满足路径字段伪造这些文件。

### 制作状态.json

这是项目级与逐集阶段状态的唯一数据源。`drama_plan.json` 和项目索引 不再重复保存状态；旧项目已有的镜像字段允许保留，但不参与阶段判断，新项目不要创建：

```json
{
  "project_id": "",
  "revision": 1,
  "current_stage": "planning",
  "current_episode": null,
  "phases": {
    "planning": "in_progress",
    "script": "pending",
    "assets": "pending",
    "storyboard": "pending",
    "video": "pending",
    "final": "pending"
  },
  "episodes": {
    "ep_1": {
      "stage_status": {
        "script": "pending",
        "assets": "pending",
        "storyboard": "pending",
        "video": "pending",
        "final": "pending"
      }
    }
  },
  "artifacts": [],
  "open_issues": [],
  "last_successful_operation": ""
}
```

状态枚举保持 `pending|in_progress|awaiting_confirmation|confirmed|completed|merged|invalidated|blocked`。`completed` 表示实际目标已完成并交付，不表示用户批准：视频/成片使用它；纯创作目标交付后也使用它，但不能据此进入超出目标的生产。轻量纯创作交付时规划准备可记 completed，不伪造规划确认。`confirmed` 仍必须有真实认可。`merged` 用于轻量目标之前已包含的阶段，也用于完整模式仅复用已批准资产、没有新增采用决定的 assets 阶段；目标本身不记 merged。

完整模式项目级故事用 `current_episode: null`，之后按集推进；单集同一正文一次真实认可可覆盖项目级与本集。轻量按 `control-contracts.md` 进入实际交付终点；目标之后保持 pending，非视频目标不登记 generate。纯创作交付不要求补一条确认回复。视频/成片工具完成、保存并正式交付即可记 `completed`；异步任务受理、纯文字宣称、失败或缺真实结果不得冒充完成。

### 用户确认记录.jsonl

每次收到用户对当前阶段的明确确认后追加一行，禁止代理预写、补写或把无回复视为确认：

```jsonl
{"stage":"planning","episode_id":"","revision":1,"decision":"confirmed","confirmation_mode":"full","changed_artifacts":[],"impact_scope":[],"confirmation_purpose":"project_execution","interaction_ask_call_id":"实际确认调用 ID","interaction_ask_result":"proceed_project","user_message":"用户通过确认工具确认项目方案的原文","confirmed_at":"2026-09-08T12:00:00+08:00"}
{"stage":"script","episode_id":"ep_1","revision":2,"decision":"confirmed","confirmation_mode":"full","changed_artifacts":[],"impact_scope":[],"confirmation_purpose":"","interaction_ask_call_id":"","interaction_ask_result":"","user_message":"用户确认第 1 集详细剧本的原文","confirmed_at":"2026-09-08T12:05:00+08:00"}
{"stage":"assets","episode_id":"ep_1","revision":2,"decision":"confirmed","confirmation_mode":"full|incremental","base_revision":1,"changed_artifacts":[],"impact_scope":[],"confirmation_purpose":"","interaction_ask_call_id":"","interaction_ask_result":"","user_message":"用户本轮明确回复原文","confirmed_at":"2026-09-08T12:10:00+08:00"}
```

- `planning` 始终是项目级确认。`script` 有两种作用域：项目级故事包确认的 `episode_id` 留空；分集详细剧本确认必须填写当前 `episode_id`。`assets|storyboard|video|final` 始终填写当前 `episode_id`。同名阶段在不同作用域或不同集的确认记录不能互相替代。
- `interaction_ask_result` 是内部归一化授权记录，不是宿主工具原始返回字段。`proceed_project`、`generate`、`proceed_assembly` 分别记录明确的项目制作、视频生成和拼接同意；其他流程文件“取得这些值”的表述均指取得对应的用户授权后登记记录，不要求宿主返回同名值。必须保存本次真实调用关联、用户原文、时间和授权范围，不能用内部枚举、示例数据或历史记录代替本次授权。
- 完整模式且 `target_stage=video|final` 时，planning 写 `project_execution/proceed_project`。轻量 `video|final` 目标执行视频生成确认，取得明确同意后 planning 写 `video_generation/generate`；同一次调用还登记为当前明确批次的 `generation_confirmations`。其他目标实际发生的普通创作确认不填视频交互字段；轻量纯创作交付无需补确认；同一真实回复覆盖明确展示的规划和目标正文时按实际作用域引用，不虚构额外调用。视频确认策略只读取 `interaction-ask-video-clarification-ref.md`，本文件仅维护内部记录。
- 视频/成片生成后直接交付并记录 `completed`，不新增视频接受、进入常规拼接或成片验收确认。`assembly_confirmation` 默认空对象；只有实际重大制作方案变更取得授权时记录真实变更，不伪造 `proceed_assembly`。
- `user_message` 保存触发继续的用户原文；空值、系统生成文字或仅有内部检查结果无效。
- `confirmed_at` 必须是带时区的 ISO-8601 时间。
- 首次确认或重大修改使用 `confirmation_mode: full`；此时 `base_revision` 可省略，`changed_artifacts` 与 `impact_scope` 可为空。已有真实全量确认基础上的局部微调可使用 `incremental`，必须记录上一全量确认 revision、实际变化文件和影响范围；禁止第一次确认就写 `incremental`。
- 用户提出修改时不写 `confirmed`；完成修改、重新展示并再次收到明确确认后才追加新记录。
- 阶段状态写为 `confirmed` 时必须存在同阶段有效确认记录。

### 合规证明_阶段名.json

只有宿主或用户明确要求额外审计证明时，才在 `00_制作控制/合规证明/` 保存对应证明；它不是常规阶段准出硬门。完整委派规则读取 `delegation.md`，建议结构为：

```json
{
  "stage": "planning|script|assets|storyboard|video|final",
  "executor": "main_agent|main_agent_director",
  "delegated": false,
  "skill_read": ["SKILL.md"],
  "upstream_artifacts": [
    {
      "path": "项目根目录内相对路径",
      "sha256": "64位小写十六进制",
      "revision": 1
    }
  ],
  "tool_calls": [
    {
      "operation_id": "与操作日志一致的唯一 ID",
      "tool": "实际工具名",
      "status": "completed",
      "evidence_path": "/absolute/path/to/evidence",
      "evidence_sha256": "64位小写十六进制",
      "observed_metadata": {"width": 1080, "height": 1920}
    }
  ],
  "delegations": [],
  "forbidden_tools_used": [],
  "declaration": "本阶段严格遵循skill要求，未使用禁止的替代工具；本阶段委派情况与 delegation.md 一致"
}
```

`planning|script|storyboard` 的 `delegated` 必须为 `false` 且 `delegations` 为空。`assets` 只有在图片工具执行被外包时才记录委派；`video` 只要发生实际视频生成/编辑工具调用，`delegated` 必须为 `true` 并记录 `video_execution` 交接包；`final` 只要发生拼接、裁剪、混音、mux、字幕烧录等媒体变更工具调用，`delegated` 必须为 `true` 并记录 `final_media_execution` 交接包。每个交接包使用 Skill 内或项目内相对路径，保存逐文件输出白名单、实际输出、硬约束、执行完成条件和禁止再委派声明；
`declaration` 必须以 `本阶段严格遵循skill要求，未使用禁止的替代工具` 开头，后面允许追加本阶段真实说明。
规划、剧本和分镜属于纯文件创作阶段，没有外部生成调用时 `tool_calls` 直接写空数组，不得虚构 `file_creation`。`upstream_artifacts` 只记录当前模式和实际操作依赖的来源、版本与已有哈希，不要求轻量补全上一阶段整包。资产、视频和成片属于生成或媒体处理阶段，必须保存实际调用；每项引用 `操作日志.jsonl` 中同名、同阶段且状态为 `succeeded` 的 `operation_id`，工具名必须一致，证据文件必须列在该操作的 `outputs` 中、实际存在且 SHA-256 匹配。`observed_metadata` 只记录工具真实返回的元数据；无返回则留空，不为填写证明额外探测媒体。

### 操作日志.jsonl

每次外部生成、媒体处理或重要阶段状态变更追加一行；普通 Markdown/JSON 写入不需要伪装成工具调用。尚未发生操作时允许文件为空：

```json
{"operation_id":"","idempotency_key":"","input_revision":1,"stage":"","target_ids":[],"tool":"","params_summary":{},"attempt":1,"status":"started|succeeded|partial|failed","outputs":[],"output_metadata":{},"recovery_action":"","timestamp":"2026-09-08T12:00:00+08:00","prev_hash":"上一条 record_hash；首条为 64 个 0","record_hash":"当前对象移除 record_hash 后按键排序紧凑 JSON 的 SHA-256"}
```

操作日志按时间顺序追加，不修改历史行。恢复任务时先读取 `制作状态.json`、`last_successful_operation`、操作日志和实际文件。外部调用部分成功时保留成功输出，只补失败项，不重复执行已成功调用。

### project_script_manifest.json

完整模式必须创建；轻量模式不创建本索引；仅剧本目标保存唯一 Markdown 正文。以下是多集示例，`source_markdown` 与 `global_story_and_episode_outline` 引用同一份全局总纲，含完整故事走向和结局。单集时两者均指向 `episodes/ep_1/01_剧本/剧本_完整剧本_ep_1.md`，不另写项目正文。

本索引承担故事推进定位；项目、集数、时长和阶段路径均从规划/项目总索引提取。`global_story_and_episode_outline` 是同一 `source_markdown` 的用途别名，直接沿用同一路径，不分别填写；各集推进、人物弧与伏笔字段从唯一正文提取，不另写另一版梗概。正文人声只在分集合同提取，不在本索引增加台词副本。

```json
{
  "schema_version": "1.0",
  "project_id": "",
  "revision": 1,
  "global_story_and_episode_outline": "01_剧本/剧本_全局设定与分集总纲.md",
  "source_markdown": "01_剧本/剧本_全局设定与分集总纲.md",
  "source_sha256": "",
  "episode_count": 2,
  "total_duration_s": 240,
  "episodes": [
    {
      "episode_id": "ep_1",
      "duration_s": 120,
      "opening_state": "",
      "main_conflict": "",
      "major_turns": [],
      "climax_or_payoff": "",
      "ending_state": "",
      "next_hook": "",
      "detailed_script": "",
      "script_contract": ""
    },
    {
      "episode_id": "ep_2",
      "duration_s": 120,
      "opening_state": "",
      "main_conflict": "",
      "major_turns": [],
      "climax_or_payoff": "",
      "ending_state": "",
      "next_hook": "",
      "detailed_script": "",
      "script_contract": ""
    }
  ],
  "character_arcs": [],
  "plot_threads": [],
  "final_resolution": ""
}
```

- 项目级检查只要求当前规模所需的唯一故事正文、项目索引与数据卡。多集的未来集 `detailed_script` 与 `script_contract` 允许为空，当前集完成后才填写。单集项目阶段已完成完整正文，可以填写 `detailed_script`，但本集合同可随唯一正文提取，单集同一实际回复可同时覆盖项目级与本集确认；文件存在本身不代表用户认可。
- 多集时 `global_story_and_episode_outline` 与 `source_markdown` 均为 `01_剧本/剧本_全局设定与分集总纲.md`，正文包含“全局故事圣经”“分集推进总纲”两章；单集均为 `episodes/ep_1/01_剧本/剧本_完整剧本_ep_1.md`，包含必要“故事与设定”和完整分场，不强制伪造单集总纲表。
- 不创建独立项目设定卡、事实与假设文档、全剧详纲副本或每集梗概、人物状态、关系矩阵、场景清单文件。来源与原始要求沿用 `drama_plan.source_lock` 和 `source_manifest.json`，必要创作设定放入正文；关系与状态的执行字段留在既有分集合同和数据卡。
- `source_sha256` 绑定本项目当前真实故事正文。单集项目与分集合同引用同一文件、同一内容哈希，不为两种作用域复制正文。
- `episodes` 数量、顺序和时长必须与 `drama_plan.json` 一致，并覆盖每个 `ep_N` 的开场状态、冲突、主要变化、高潮/兑现、结尾状态及下一钩子。
- `character_arcs`、`plot_threads` 和 `final_resolution` 保证人物弧、伏笔与结局跨集闭合。
- 单集在项目级完成唯一正文，进入本集后复用；多集的每集详细完整剧本在该集开始制作时保存到 `episodes/ep_N/01_剧本/`，它必须细化项目级完整故事，不得改变其中的核心因果、结局或集间承接。需要改变时先更新项目级故事包并使受影响分集失效。

### source_manifest.json

用户上传和外部引用的图片、视频、音频、文档必须登记；没有素材时写空 `sources`，不得省略文件：

```json
{
  "schema_version": "1.0",
  "project_id": "",
  "revision": 1,
  "sources": [
    {
      "source_id": "SRC001",
      "media_type": "image|video|audio|document",
      "source_uri": "",
      "stored_path": "",
      "sha256": "",
      "source_origin": "user_upload|external_reference|generated"
    }
  ]
}
```

- 每个用户提供的 URL、附件 ID 或输入实例都必须先作为独立来源登记，即使系统提示给出相同 `local path`、相同 `image.png` 或相同 basename。`source_uri` 保存原始 URL 或可追溯附件标识；`stored_path` 使用 `SRCxxx` 唯一命名，禁止多个不同 URL 写入同一路径或互相覆盖。只有逐 URL 读取、保存并计算 `sha256` 之后，才允许把内容哈希完全相同的文件标记为重复内容；重复内容仍保留各自 `source_id` 与原始 URL 记录，不能删除来源。
- 本地文件必须记录实际 `stored_path` 和 `sha256`；纯 URL 保存规范化 `source_uri`。需要作为视觉参考、文字来源或后续工具输入的 URL 必须下载或转存到项目内并记录 `stored_path`，不能只保留 URL 文本。
- `stored_path` 必须是项目根目录内的相对路径；
- 需要复制或下载到项目内的输入统一保存为 `00_制作控制/输入素材/来源_SRCxxx_[原始名称]_vNN.[ext]`；仅服务单集时追加 `_ep_N`。
- 用途、采用范围和授权说明可按项目需要补充，但不作为自动检查字段。

### project_data_card.json

本文件只用于完整模式，在项目级故事正文确定后立即从正文与已确认事实提取。它是“一次定义、全局引用”的机器权威。身份字段不可被分集覆盖；服装、发型、妆容、伤痕、场景布置、灯光和道具完整性等变化只能通过带时间范围与原因的状态记录生效：

```json
{
  "schema_version": "1.0",
  "project_id": "",
  "revision": 1,
  "global_settings": {
    "project_name": "",
    "visual_contract": "已确认媒介、必要光色与材质",
    "ratio": "9:16",
    "episode_count": 2,
    "episode_durations_s": [120, 120],
    "subtitle_style": {}
  },
  "shared_baseline": {
    "registry_revision": 1,
    "status": "planned|approved|not_created",
    "approved_asset_ids": []
  },
  "characters": [
    {
      "character_id": "CHR001",
      "identity_locked": {
        "representation_type": "live_action_human",
        "age_or_life_stage": "",
        "face_features": {},
        "skin_fur_feather_scale": "",
        "identity_marks": [],
        "height_and_body": "",
        "voice_id": "VOICE001"
      },
      "state_timeline": [
        {
          "state_id": "STATE001",
          "effective_from": "ep_1:E01S01",
          "effective_to": "",
          "reason": "初始状态",
          "changed_fields": ["initial_state"],
          "affected_shot_ids": [],
          "affected_segment_ids": [],
          "asset_version_ids": [],
          "clothing": {},
          "hairstyle": {},
          "makeup": {},
          "injury_or_surface_state": {}
        }
      ],
      "asset_refs": {
        "turnaround": "CHR001",
        "face_anchor": "CHR001",
        "state_assets": []
      }
    }
  ],
  "scenes": [
    {
      "scene_id": "SCN001",
      "layout_locked": {
        "space_boundary": "长方形办公室",
        "doors_windows": "入口在前墙左侧 百叶窗在左墙",
        "fixed_furniture": "办公桌居中 文件柜靠入口右侧",
        "main_routes": "入口至办公桌之间保留直线通道"
      },
      "consistency_anchors": [
        "门口右侧的绿色铁皮文件柜",
        "后墙中央停在 10:17 的圆形挂钟",
        "左侧百叶窗缺失第三片叶片",
        "桌面右角的红色旋转电话",
        "从门口延伸到办公桌的黑白方砖"
      ],
      "base_lighting_locked": {
        "source": "阴天上午的窗外自然光",
        "direction": "从画面左侧射入",
        "temperature": "偏冷中性色温"
      },
      "state_timeline": [
        {
          "state_id": "STATE001",
          "effective_from": "ep_1:E01S01",
          "effective_to": "",
          "reason": "剧情初始发生在阴天上午",
          "changed_fields": ["initial_state"],
          "observable_state": "阴天上午 冷光从左侧进入 固定陈设保持基准布局",
          "affected_shot_ids": [],
          "affected_segment_ids": [],
          "asset_version_ids": []
        }
      ],
      "asset_ref": "SCN001"
    }
  ],
  "props": [
    {
      "prop_id": "PROP001",
      "scale_class": "handheld",
      "scale_reference": "成人单手可握 约 9 厘米长",
      "appearance_locked": {
        "shape": "长方形旧皮盒",
        "material": "深棕色磨损皮革",
        "identity_marks": ["右下角三道斜向划痕"]
      },
      "narrative_functions": [
        {"episode_id": "ep_1", "scene_id": "E01S01", "function": "制造父亲遗物的悬念"},
        {"episode_id": "ep_2", "scene_id": "E02S03", "function": "通过调包改变证据归属"}
      ],
      "state_timeline": [
        {
          "state_id": "STATE001",
          "effective_from": "ep_1:E01S01",
          "effective_to": "ep_2:E02S02",
          "reason": "初始状态",
          "changed_fields": ["initial_state"],
          "observable_state": "闭合 完整 内有文件 女主持有",
          "affected_shot_ids": [],
          "affected_segment_ids": [],
          "asset_version_ids": []
        }
      ],
      "asset_ref": "PROP001"
    }
  ],
  "voices": [
    {
      "voice_id": "VOICE001",
      "owner_id": "CHR001",
      "voice_locked": {
        "age_and_gender_expression": "",
        "pitch_and_timbre": "",
        "accent_and_language": "",
        "pace": "",
        "rhythm_and_pauses": "",
        "baseline_emotion": "",
        "sentence_ending": "",
        "forbidden_drift": []
      },
      "voice_anchor": "25岁年轻女性 声音清亮 普通话标准",
      "asset_ref": "VOICE001"
    }
  ]
}
```

完整模式在剧本阶段首次创建数据卡时写 `shared_baseline.status: planned`，资产阶段完成后更新为 `approved` 并填入真实批准资产 ID。轻量模式不创建本文件；用户已有素材和文字约束直接由已确认规划、来源登记与内部十五列分镜承接。

这些内容由 mainagent 按已确认剧本编写。
- 面部/头面结构、肤色或物种表面、身份标志、身高体型和 `voice_id` 属于身份锁定项，除非项目级剧本明确发生永久性身份变化，否则不得修改。
- 完整模式中，`shared_baseline.status` 在当前实际需要的 CHR/SCN/PROP/VOICE 已生成或完成合格复用登记、具备真实采用依据前不得写 `approved`；不要求补齐无需求的类别。仅剪用原片画面与演员原声时，沿真实来源、时间码和采用范围核验复用，不要求重生原作设定图或演员音色；新增画面与人声仍按 `assets.md` 准备对应资产。分镜只能在该状态为 `approved` 且资产已有有效采用依据后开始：新增决定取得确认，同范围已批准复用沿用原依据并按控制合同记 merged。轻量模式不适用本数据卡及批准门。
- 服装、发型、妆容、伤痕和湿污等持续性外观可变，但每次变化必须有 `state_id/effective_from/effective_to/reason/changed_fields`，且 `changed_fields` 不得为空；同一 SEG 内变化须来自已确认剧情，并通过可见过程或明确省略交代原因和结果。即时表情、视线、姿态和语气按表演推进，不因此新建资产状态；是否需要补图按 `assets.md` 的可见性与复用规则判断。
- 已进入分镜或生成阶段的状态变化还要填写 `affected_shot_ids`、`affected_segment_ids` 和 `asset_version_ids`；基础初始状态可以使用空数组。
- 场景 `layout_locked` 固定户型、门窗朝向、固定家具与主要通道；`consistency_anchors` 必须选择 `3-5` 个包含对象、外观和固定位置的唯一可见锚点；`base_lighting_locked` 只锁定剧本实际使用的基础光照，`state_timeline` 只记录有剧情原因的布置或灯光变化。
- 道具 `appearance_locked` 固定颜色、形状、材质和标志性磨损；`scale_class/scale_reference` 锁定尺度，`narrative_functions` 逐场记录剧情功能，位置、归属、开合、内容物、破损和完整性变化进入带原因与可观察结果的 `state_timeline`。
- 下游 Prompt 必须记录采用的数据卡 revision、角色/场景/道具 ID 与当前 `state_id`，不得复制后再自行改写基础设定。

分类资产说明、风格说明和汇总 Markdown 默认不创建；按 `assets.md` 在媒体旁展示必要说明，用户明确要求独立文件时从数据卡与登记派生。目录列举的是产物位置，不要求预建空分类、空状态图或未来集资产。身份/状态事实仍由数据卡维护，资产登记只维护媒体版本、来源与使用范围。

### asset_registry.json

共享资产的唯一权威登记：

```json
{
  "schema_version": "1.0",
  "project_id": "",
  "revision": 1,
  "assets": [
    {
      "asset_id": "CHR001|SCN001|PROP001|VOICE001",
      "category": "character|scene|prop|voice|style",
      "name": "",
      "version": "v01",
      "status": "draft|reviewed|approved|rejected|superseded",
      "files": [],
      "source_ids": [],
      "reference_asset_ids": [],
      "project_visual_mode": "",
      "locked_features": [],
      "variable_states": [],
      "used_by_episodes": ["ep_1"],
      "used_by_shots": [],
      "generation": {
        "tool": "",
        "model": "",
        "task_id": "",
        "prompt_path": ""
      },
      "last_reviewed": ""
    }
  ]
}
```

同一 `asset_id + version` 只允许一条权威记录。分集不得复制共享文件，只能通过 `asset_usage_ep_N.json` 引用。
视图选择、状态是否补图和设计与采用由 `assets.md` 决定，不以文件数或三视图/四宫格版式作为独立 schema 门槛。`files` 保存实际可用媒体，不能把未生成的细节、视角或状态写成 approved。共享角色的基准可以就是当前集首次需要的造型，不要求先做一套未入戏的“日常版”。
图片资产的 `generation.tool` 只按当前目标实际采用的视觉输入填写：`generation.reference_inputs|input_files|input_images`、`reference_asset_ids` 和 `style_anchor_reference_ids` 均为空时才可使用 `image_gen`；其中任一项登记了真实图片时使用 `image_edit`。`source_ids` 只表示来源追溯，不单独决定工具路由；文本、脚本、知识来源或只含文字的截图不得因存在 `source_id` 被误判为视觉参考图。

图片风格登记字段对共享条目与分集 `episode_assets` 通用，属于既有生成追溯信息，不另建风格资产：

| 字段 | 类型与适用条件 |
|---|---|
| `project_visual_mode` | approved 图片条目必填字符串：`live_action`、`photoreal`、`2d_comic`、`anime`、`ink_animation`、`illustration`、`stylized_3d`、`mixed_with_explicit_scope`；继承项目已选模式，真人实拍/照片级用前两项，平涂卡通/漫画用 `2d_comic`，动漫用 `anime`，水墨动画用 `ink_animation`，水彩/绘本等插画用 `illustration`，风格化三维用 `stylized_3d`；混合仅限已明确范围。机器值不替代具体画风描述，不新增呈现类别 |
| `available_visual_reference_ids` | 字符串数组，保存本目标可用候选；实际选入请求的图片另记 `generation.reference_inputs`，候选不全传时按 `assets.md` 说明职责覆盖或排除原因 |
| `style_anchor_reference_ids` | 确实采用图片画风时填写非空字符串数组，指向真实来源/版本；没有图片锚点时可省略，不能只填 ID 而未实际传图 |
| `style_prompt_terms`、`style_adopt`、`style_exclude` | 使用图片画风锚点时各为非空字符串数组，分别写可观察画风词、采用维度、剥离维度；实际 Prompt 同步落实 |

上述字段统一放资产条目层；读取兼容既有记录放在 `generation` 内的写法，不要求重复维护两份。分集条目沿用本表，音色条目不填图片模式。已有媒体直接复用时保留来源的风格登记，不虚构新的 `generation`。

### episode_seams.json

只登记跨集边界；集内计划边界在分镜/视频索引维护，必要尾帧按实际输入登记：

```json
{
  "schema_version": "1.0",
  "project_id": "",
  "revision": 1,
  "seams": [
    {
      "seam_id": "EPSEAM001",
      "from_episode": "ep_1",
      "to_episode": "ep_2",
      "from_segment": "",
      "to_segment": "",
      "actual_tail_frame": "",
      "actual_tail_sha256": "",
      "visual_state": {},
      "audio_state": {},
      "unresolved_hooks": [],
      "cut_strategy": "",
      "seam_mode": "continuous|elliptical",
      "required_invariants": ["identity", "screen_direction"],
      "permitted_deltas": [],
      "status": "planned|bound|blocked"
    }
  ]
}
```

仅完整模式有实际跨集承接时创建；单集不创建，项目索引中的 `episode_seams_path` 留空。`continuous` 连续叙事状态，`permitted_deltas` 为空但允许已规划换机位；`elliptical` 明确跳跃维度与新起点。设计时写 `planned`，实际来源存在并用于后续输入时记 `bound`；这不是画面/声音核验通过。连续承接所需真实尾帧路径与哈希在准备下一调用时填写，不伪造；省略转场不硬传尾帧。轻量不用此跨集文件，普通多段接缝直接写视频 manifest。

### 项目索引中的单集入口

两种模式均使用 `project_manifest.json.episodes[ep_N]`，每项保存 `episode_id`、实际时长及 `stage_manifests`。完整模式字段与上面的项目示例一致；轻量 `script` 仅在剧本目标时指向唯一正文，`storyboard` 指向十五列主表，`video` 指向视频执行记录；资产设计/媒体由来源登记引用，不建完整模式的 asset_usage。轻量 `delivery` 也指向视频执行记录，其最终制作与交付信息在该文件的 `delivery` 对象内；没有实际视频不创建这些执行文件。

不再使用 `continuity` 文件指针，实际尾帧写入视频执行记录 `frames[]`。未涉及的阶段指针可省略，不预建未来产物。旧项目入口文件只按需读取，其中独有信息迁入对应项目条目后使用，不要求为继续制作补写新旧两份入口。

### script_contract_ep_N.json

当前集完整正文完成后提取机器执行合同，不复制剧情梗概；关系变化、角色状态、场景引用与人声直接来自同一正文，不依赖独立矩阵或场景清单文件：

```json
{
  "schema_version": "1.0",
  "episode_id": "ep_1",
  "revision": 1,
  "project_data_card_revision": 1,
  "source_markdown": "episodes/ep_1/01_剧本/剧本_完整剧本_ep_1.md",
  "source_sha256": "",
  "duration_s": 120,
  "story_engine": {
    "dramatic_question": "",
    "protagonist_desire": "",
    "opposition": "",
    "stakes": "",
    "irreversible_choice": "",
    "episode_payoff": ""
  },
  "opening_contract": {
    "plan_opening_id": "OPEN001",
    "inheritance_mode": "direct|episode_variation",
    "variation_reason": "",
    "primary_type": "mystery_question|world_spectacle|character_portrait|visual_spectacle|conflict_driven|custom",
    "supporting_types": [],
    "scene_id": "E01S01",
    "opening_window": "",
    "first_observable_promise": "",
    "escalation_trigger": "",
    "payoff_or_rollover": ""
  },
  "relationship_tension": [
    {
      "relationship_id": "REL001",
      "characters": ["CHR001", "CHR002"],
      "initial": {"power_gap": "", "information_gap": "", "emotional_gap": ""},
      "change_nodes": [{"scene_id": "E01S01", "cause": "", "after": {"power_gap": "", "information_gap": "", "emotional_gap": ""}, "blocking_implication": ""}]
    }
  ],
  "reveal_ledger": [
    {"reveal_id": "REV001", "fact": "", "plant_scene": "E01S01", "development_scene": "E01S02", "reveal_scene": "E01S03", "consequence": ""}
  ],
  "shareable_line": {
    "mode": "dialogue|visual|sound|exception",
    "line_id": "LINE001",
    "text_or_motif": "",
    "placement": "climax|reversal|ending",
    "dramatic_support": ""
  },
  "highlight_ledger": [
    {
      "highlight_id": "HL001",
      "role": "primary|supporting",
      "episode_id": "ep_1",
      "scene_id": "E01S03",
      "dimension": "关系攻防|信息重释|专业能力|标志性场面|视觉母题|声音母题|表演瞬间|情绪余震|结构形式|传播台词|custom",
      "setup_evidence": "",
      "payoff_action": "",
      "state_change": "",
      "subject_function": "",
      "format_expression": "",
      "aftereffect": ""
    }
  ],
  "scenes": [
    {
      "scene_id": "E01S01",
      "location_id": "SCN001",
      "characters": ["CHR001"],
      "character_states": ["CHR001:STATE001"],
      "prop_states": ["PROP001:STATE001"],
      "data_card_deltas": [],
      "goal": "",
      "obstacle": "",
      "strategy_shift": "",
      "state_change": "",
      "entry_goal": "",
      "tactic": "",
      "countermove": "",
      "turn": "",
      "exit_value": "",
      "speech_lines": [
        {
          "line_id": "LINE001",
          "speaker": "CHR001",
          "voice_id": "VOICE001",
          "voice_anchor": "25岁年轻女性 声音清亮 普通话标准",
          "type": "on_screen_dialogue|narration|voiceover|inner_monologue",
          "source_text": "",
          "display_text": "",
          "spoken_text": "",
          "delivery_intent": "",
          "pause_plan": "",
          "emotion": "",
          "emphasis_words": []
        }
      ]
    }
  ]
}
```

剧本索引记录正文引用、场次编号、音色资产引用及主要亮点 ID；剧情质量、关系、表演与表达仍由创作者和用户判断。`role=primary` 的亮点必须在分镜 `highlight_bindings` 中逐项兑现。

### storyboard_ep_N.json

本 JSON 只用于完整模式，保存从唯一十五列主表提取的镜号、时间、分组、资产及合同引用，以及唯一的 SEG 边界与计划接缝记录，不重写逐镜剧情与表演。轻量模式只生成 `分镜_完整分镜表_ep_1.md`，不创建本 JSON：

```json
{
  "schema_version": "1.0",
  "episode_id": "ep_1",
  "revision": 1,
  "project_data_card_revision": 1,
  "source_markdown": "episodes/ep_1/02_分镜/分镜_完整分镜表_ep_1.md",
  "director_control_card": "episodes/ep_1/02_分镜/导演总控卡_ep_1.md",
  "source_sha256": "",
  "duration_s": 120,
  "audience_execution": {
    "source_plan_revision": 1,
    "viewing_focus": {
      "source_field": "audience_plan.viewing_focus",
      "contract": "继承已确认受众的首要观看焦点",
      "scene_or_shot_ids": [
        "E01S01-SHOT001"
      ]
    },
    "emotional_payoff": {
      "source_field": "audience_plan.emotional_payoff",
      "contract": "本集承担的情绪回报",
      "scene_or_shot_ids": [
        "E01S03-SHOT004"
      ]
    },
    "platform_viewing_context": {
      "source_field": "audience_plan.platform_viewing_context",
      "contract": "已确认平台观看场景下的可读性执行",
      "scene_or_shot_ids": [
        "E01S01"
      ]
    },
    "expression_boundaries": {
      "source_field": "audience_plan.expression_boundaries",
      "contract": "继承已确认表达禁区及规避方式",
      "scene_or_shot_ids": [
        "E01S02-SHOT003"
      ]
    }
  },
  "highlight_bindings": [
    {
      "highlight_id": "HL001",
      "segment_id": "SEG003",
      "causal_chain": {
        "trigger": {
          "description": "",
          "shot_ids": [
            "E01S03-SHOT002"
          ]
        },
        "change": {
          "description": "",
          "shot_ids": [
            "E01S03-SHOT003"
          ]
        },
        "feedback": {
          "description": "",
          "shot_ids": [
            "E01S03-SHOT004"
          ]
        },
        "result": {
          "description": "",
          "shot_ids": [
            "E01S04-SHOT001"
          ]
        }
      },
      "payoff_shot_ids": [
        "E01S03-SHOT003"
      ],
      "reaction_shot_ids": [
        "E01S03-SHOT004"
      ],
      "visual_execution": "",
      "performance_execution": "",
      "audio_execution": "",
      "aftereffect_shot_ids": [
        "E01S04-SHOT001"
      ],
      "deferred_aftereffect_ref": null,
      "compile_notes": ""
    }
  ],
  "inherited_aftereffect_bindings": [],
  "shots": [],
  "segments": [
    {
      "segment_id": "SEG001",
      "shot_mode": "edited|true_one_take",
      "density_profile": "high_density_short|dialogue_emotional|suspense_build|micro_film|custom",
      "density_rationale": "",
      "indivisible_action_units": [
        {
          "action_unit_id": "ACTU001",
          "state_before": "",
          "action_and_path": "",
          "feedback": "",
          "state_after": "",
          "shot_ids": [
            "E01S01-SHOT001"
          ]
        }
      ],
      "opening_event_chain": [],
      "tail_mode": "continuous_motion|cuttable_completion|stable_hold|loop_continuation",
      "tail_hold_reason": "",
      "tail_selection_reason": "",
      "one_take_route": null,
      "shot_ids": [
        "E01S01-SHOT001"
      ],
      "pacing_profile": "brisk",
      "pacing_exception": null,
      "time_range": "00:00-00:15",
      "duration_s": 15,
      "purpose": "本段承担的行动、反馈与变化",
      "planned_start_state": "本段开始的人物、道具与空间状态",
      "planned_end_state": "本段结束的变化与下一段起点",
      "reference_input_plan": [],
      "generation_risks": []
    }
  ],
  "seams": [
    {
      "seam_id": "SEAM001",
      "from_segment": "SEG001",
      "to_segment": "SEG002",
      "seam_mode": "continuous",
      "transition_anchor": "本边界唯一主锚点",
      "outgoing_prompt_cue": "出段动作相位、方向、速度与落点",
      "incoming_prompt_pickup": "入段接住锚点并立即发展",
      "required_invariants": [],
      "permitted_deltas": [],
      "proof_requirement": "本边界所需真实尾帧与必要参考职责，调用前绑定"
    }
  ]
}
```

分镜索引记录正文引用、镜头编号、片段对镜头的完整覆盖、相邻片段引用、主要亮点绑定和受众执行落点。`shot_mode` 只能为 `edited|true_one_take`；`true_one_take` 必须且只能引用一个 SHOT，并由导演总控卡证明没有硬切、隐藏切、遮挡伪切、匹配剪辑或时间跳跃，`one_take_route` 记录连续摄影机路线、实际行动与观察重点迁移、最终落点，节点数量不设配额。`density_profile` 用于区分高密度平台短片、对白/情感、悬疑蓄力、微电影/生活流和自定义节奏；`density_rationale` 记录主导内容负载和排除理由，`indivisible_action_units` 记录动作单元到 SHOT 的映射。所有内容分类统一执行 `pacing.md` 的默认紧凑节奏、有效覆盖、对白容量与用户明确例外；`opening_event_chain` 记录开头的异常/目标、行动和反馈，不能用内容分类豁免推进要求。`tail_mode` 必须按片段职责选择，`tail_selection_reason` 记录选择依据；中间 SEG 默认 `continuous_motion|cuttable_completion`，使用 `stable_hold` 时填写 `tail_hold_reason`，最终 SEG 通常以 `cuttable_completion` 在结果可读、必要反应成立时结束，不预留固定稳定尾帧；`stable_hold` 只用于剧情确需的停顿并说明具体作用和时长，Loop 使用 `loop_continuation`。`highlight_bindings[].causal_chain` 按触发、变化、反馈、结果记录可观察事实和镜头；变化/兑现映射到 `payoff_shot_ids`，反馈映射到 `reaction_shot_ids`，结果映射到本集 `aftereffect_shot_ids` 或跨集引用。同一 SHOT 可复用于兑现、反馈和后果，只要对应证据与因果清楚；这些数组不要求三个独立镜头或额外高潮后停留，采用条件及并行方式遵循 `storyboard.md`。`highlight_bindings` 必须覆盖 `script_contract.highlight_ledger` 中全部 `role=primary` 项；`segment_id` 是亮点兑现所在 SEG，`payoff_shot_ids` 必须属于该 SEG，`reaction_shot_ids` 可落在本集后续 SEG且不得早于兑现镜头。余震在本集发生时填写真实 `aftereffect_shot_ids`，这些镜头不得早于兑现/反应镜头；计划在后续集回收时留空该数组，并把 `deferred_aftereffect_ref` 写成 `{"episode_id":"ep_2","outline_ref":"01_剧本/剧本_全局设定与分集总纲.md","promise":"第2集揭晓文书转手后的代价","highlight_id":"","binding_id":"HL001-aftereffect"}`。未来目标集详细合同、HL 和 SHOT 在当前阶段不要求存在；先锁定总纲的具体承诺，目标集实际开始后再用真实镜号绑定，不能提前造未来详细剧本。目标集对应绑定用相同 `binding_id` 写入 `inherited_aftereffect_bindings[]`，每项结构为 `{"binding_id":"","source_episode_id":"ep_1","source_highlight_id":"HL001","shot_ids":[]}`，形成反向承接。每项还必须填写视觉、表演、声音和视频编译说明。`audience_execution.source_plan_revision` 必须等于当前已确认 `drama_plan.revision`；四项执行合同必须各自填写固定 `source_field` 并逐字继承当前 `audience_plan` 对应值，再绑定到真实场次或镜头，不得在分镜阶段重新画像或更换受众。上述推导字段由主 Agent 按 `storyboard.md` 形成，实际视频调用前同一次核对；lint 不对其创意质量打分。

### asset_usage_ep_N.json

保存本集资产快照和本集状态与媒体的绑定；字段不意味着每个状态都要新生成文件。图片条目的风格字段沿用上文 `asset_registry.json` 的通用定义：

```json
{
  "schema_version": "1.0",
  "episode_id": "ep_1",
  "revision": 1,
  "project_data_card_revision": 1,
  "shared_assets": [
    {
      "asset_id": "CHR001",
      "version": "v01",
      "registry_path": "shared/03_资产/asset_registry.json",
      "used_by_shots": []
    }
  ],
  "episode_assets": [
    {
      "asset_id": "CHR001",
      "state_id": "STATE002",
      "version": "v02",
      "files": ["episodes/ep_1/03_资产/角色状态/角色_CHR001_林远_战损_v02_ep_1.png"],
      "effective_shots": [],
      "status": "draft|reviewed|approved|rejected|superseded"
    }
  ]
}
```

影响连续性的易主、位置/朝向变化等继续写入数据卡时间线与后续镜头动作。需要 `state_id` 时，本集状态条目可在 `files` 直接引用同一份已批准共享/既有文件，使用对应来源版本并说明生效范围；这种绑定不复制媒体、不增加虚构生成调用。真实外观变化若原文件未覆盖，仍须按 `assets.md` 补图。沿用别集的非共享状态继续用 `reused_episode_assets`，保留原来源、版本及文件。`generation` 仅在确有本条生成操作时登记，复用不编造 Prompt 或工具任务。同范围已批准复用时，在相应采用条目保留批准记录的真实文件/条目引用、原批准范围及本次用途与版本；这些信息随原条目保存，不新增复用确认单或复制批准原文。

表情、视线、短暂姿势和语气属于即时表演，不逐次建立资产状态 ID 或外观状态时间线。不同剧情造型可分别保持 approved；同一造型的错误版被修正替代时才废弃对应旧修订，不能按整个资产的最大版本号淘汰仍需使用的其他剧情状态。共享媒体的权威批准状态以 registry 为准，分集状态绑定不重新批准已废弃来源。具体判断与例子由 `assets.md` 维护。

### video_manifest_ep_N.json

作为本集视频生成结果的权威索引；`00_制作控制/批次/*.json` 继续保存单次请求快照：

```json
{
  "schema_version": "1.0",
  "episode_id": "ep_1",
  "revision": 1,
  "project_data_card_revision": 1,
  "storyboard_manifest": "episodes/ep_1/02_分镜/storyboard_ep_1.json",
  "duration_s": 12,
  "generation_confirmations": [
    {
      "confirmation_id": "VC001",
      "attempt": 1,
      "supersedes_confirmation_ids": [],
      "batch_start_segment_index": 1,
      "batch_end_segment_index": 1,
      "model": "seedance 2.0 fast",
      "aspect_ratio": "9:16",
      "duration_s": 12,
      "planned_video_count": 1,
      "segment_durations": [
        {
          "segment_id": "SEG001",
          "duration_s": 12
        }
      ],
      "displayed_parameter_table": {
        "model": "seedance 2.0 fast",
        "segment_durations": [
          "SEG001：12秒"
        ],
        "total_duration": "12秒",
        "aspect_ratio_and_resolution": "9:16，按当前模型实际分辨率",
        "quantity": 1,
        "task_type": "多媒体生成视频",
        "delivery_format": "MP4 视频片段",
        "visual_and_continuity": "按已确认角色、场景与上一段承接关系生成",
        "audio_and_subtitles": "保留本段完整对白，不生成画面字幕",
        "reference_materials": "当前角色、场景与必要道具/状态图，以及本段发声主体的已批准音色",
        "tool_limits_and_cost": "本批 1 个视频；视频生成为高消耗生成"
      },
      "displayed_storyboard_rows": [
        {
          "segment_id": "SEG001",
          "duration_s": 12,
          "visual_content": "本段从起点到结果的可见剧情内容",
          "subject_action": "主体动作、反馈与尾态",
          "audio": "声音类型与完整台词",
          "camera_and_materials": "主要运镜、承接方式与真实输入素材"
        }
      ],
      "creative_direction": "按已确认分镜生成本段剧情",
      "cost_notice": "视频生成会消耗更多积分或额度",
      "membership_notice": "",
      "final_parameters_text": "我准备为你制作本批悬疑剧情片段，具体安排如下。\n\n- **模型**：seedance 2.0 fast（视频生成为高消耗生成）\n- **时长**：本次目标成片12秒；本批第1段12秒，合计12秒\n- **比例**：9:16\n- **数量**：成片1条；本批生成1段\n- **视频内容**：按已确认分镜生成本段剧情\n- **声音与字幕**：保留本段完整对白，不生成画面字幕\n- **参考素材**：当前角色、场景与必要道具/状态图，以及本段发声主体的已批准音色\n- **限制与消耗**：本批1段；视频生成为高消耗生成\n\n| 片段与时长 | 画面内容 | 主体动作 | 声音与完整台词 | 运镜与素材 |\n|---|---|---|---|---|\n| SEG001｜12秒 | 本段从起点到结果的可见剧情内容 | 主体动作、反馈与尾态 | 声音类型与完整台词 | 主要运镜、承接方式与真实输入素材 |",
      "interaction_ask_call_id": "实际确认调用 ID",
      "interaction_ask_result": "generate",
      "user_message": "用户通过确认工具选择生成的原文",
      "confirmed_at": "2026-09-08T12:00:00+08:00"
    }
  ],
  "segments": [
    {
      "segment_id": "SEG001",
      "episode_segment_index": 1,
      "shot_ids": [
        "E01S01-SHOT001",
        "E01S01-SHOT002",
        "E01S01-SHOT003",
        "E01S01-SHOT004",
        "E01S01-SHOT005",
        "E01S01-SHOT006"
      ],
      "batch_id": "",
      "tool_mode": "media_to_video",
      "model": "seedance 2.0 fast",
      "source_video_file": "",
      "edit_verification": null,
      "duration_s": 12,
      "observable_state_changes": [
        "门内人转动门把暴露位置",
        "手机照片暴露身后的第二人"
      ],
      "request_snapshot_file": "00_制作控制/批次/请求_SEG001_v01_ep_1.json",
      "prompt_sha256": "",
      "reference_inputs": [
        {
          "order": 1,
          "source_type": "asset",
          "source_id": "CHR001_v01",
          "file": "shared/03_资产/角色/角色_CHR001_林远_基准状态_v01.png",
          "role": "identity_reference",
          "adopt": "林远面部、体型与服装身份",
          "exclude": "剥离原图背景、姿态与版式"
        }
      ],
      "required_reference_roles": [
        "identity_reference"
      ],
      "audio_input_supported": true,
      "audio_inputs": [{"resource_id": "示例_VOICE001_已批准音频资源ID", "file": "shared/03_资产/音色/音色_VOICE001_林远_v01.wav"}],
      "video_inputs": [],
      "voice_inputs": [{"voice_id": "VOICE001", "resource_id": "示例_VOICE001_已批准音频资源ID"}],
      "native_audio_supported": true,
      "speech_mode": "native_required",
      "speech_lines": [
        {
          "speaker": "林远",
          "voice_id": "VOICE001",
          "voice_anchor": "28岁男性 声音低沉偏冷 普通话 清晰中音",
          "type": "on_screen_dialogue",
          "source_text": "谁在里面？",
          "display_text": "谁在里面？",
          "spoken_text": "谁在里面",
          "delivery_intent": "短促试探",
          "pause_plan": "不作填时停顿",
          "emotion": "克制警觉",
          "emphasis_words": [
            "谁"
          ],
          "line_id": "LINE001",
          "shot_id": "E01S01-SHOT002",
          "start_s": 2,
          "end_s": 4
        }
      ],
      "generation_confirmation_id": "VC001",
      "tool_call_id": "实际视频工具调用 ID",
      "tool_called_at": "2026-09-08T12:01:00+08:00",
      "output_file": "episodes/ep_1/04_视频片段/片段_SEG001_E01S01_v01_ep_1.mp4",
      "version": "v01",
      "status": "planned|generated|blocked",
      "qc_report": "",
      "incoming_episode_seam": null,
      "shot_mode": "edited",
      "density_profile": "suspense_build",
      "pacing_profile": "brisk",
      "pacing_exception": null
    }
  ]
}
```

完整模式填写 `project_data_card_revision` 和 `storyboard_manifest`。轻量模式不创建这两个上游文件，因此在视频 manifest 中将对应字段留空；它改为通过请求快照记录 `episodes/ep_1/02_分镜/分镜_完整分镜表_ep_1.md` 和实际使用的 Prompt 路径，以维持生成追溯。

生成目标沿用 `video.md` 实际职责，不为每段补钩子或闭环。返回后保存登记并直接交付，不播放/试听、不写质检报告或 observed seam。只有后续调用所需尾帧才提取并记录真实来源，不能用更早帧冒充实际尾态。

`segments[].status`：`planned` 是待执行计划；规划准备期间 Prompt 可暂空，但取得本批生成确认前必须由 mainagent 写好完整正文，依赖后段写好完整 Prompt 模板与接续要求。依赖未就绪时，真实输入及实际提交请求快照可暂空，不能据此延后正文创作或伪造素材。`generated` 是工具真实完成并保存结果；`blocked` 是真实失败或当前应具备的必要输入无法取得；按已声明依赖等待前段结果时仍保留 `planned`，不能把等待写成 `generated`。旧项目 `candidate|accepted|rejected` 可按历史意义读取，不能要求新产物先经接受才能拼接，也不为未审片降级候选。

Prompt 由主 Agent 对照分镜直接撰写并审读，具体五层写法与完整示例只读 `video.md`。单次请求快照保存实际工具参数和唯一完整 Prompt，不另强制生成 Prompt Markdown。快照使用 `request` 保存原样工具参数对象，`prompt_field` 写明其中实际 Prompt 参数键；`request_snapshot_file` 引用该文件，`prompt_sha256` 只绑定取出的 Prompt 原文。执行者读取该字段后原样提交，不将整个快照当模型提示词。旧 `compiled_prompt_file` 仅按实际旧文件复用，不要求复制新快照中的正文。不另建重复创作源或自填预检合格字段。请求快照结构为 `{"request": {实际工具参数}, "prompt_field": "实际 Prompt 参数键"}`；只有 request 中该字段保存完整原文。

前置制作方案选择的真实 `interaction.ask` 调用 ID、用户选择及对应模型、分段、台词取舍，保存在现有规划确认或工具记录中；不新增必填字段，不将 `video_plan_select` 写成生成授权。只有真实 `video_confirm` 的 `generate` 结果才能写入视频生成确认，调用结构和授权规则读取 `interaction-ask-video-clarification-ref.md`。

`generation_confirmations[]` 每项对应一次真实批次确认在本 manifest 中的覆盖范围。先区分展示分支：`confirmation_source: planning_preview` 的轻量首次生成使用规划参数列表、全片五列概览和本批完整人声；完整模式批次及轻量后续批次/返修使用 Markdown 参数列表与一张五列分镜表。共同的真实授权、模型、任务上限与 SEG 范围要求不变，不因展示分支再增加一次确认。具体记录必须满足：

- `confirmation_id` 全局唯一，`attempt` 为从 `1` 递增的正整数。首次确认的 `supersedes_confirmation_ids` 为空；重生或返修覆盖既有 SEG 时，新增确认记录并在该数组中列出所有范围重叠的旧确认 ID，禁止删除历史确认。替代关系只对新旧确认范围的交集生效：例如旧确认覆盖 SEG001-SEG002、新确认只覆盖 SEG001，则旧确认对 SEG002 继续有效。替代确认时间必须晚于被替代确认，每个 SEG 的 `generation_confirmation_id` 必须指向覆盖该 SEG 的最新有效确认。
- `planned_video_count` 只能为 `1|2`，并等于确认范围内 SEG 数、`segment_durations` 项数和 `displayed_parameter_table.quantity`。普通批次另等于 `displayed_storyboard_rows` 行数；轻量首次的该数组为最多八行的全片概览，不要求行数等于本批 SEG 数，也不扩大授权范围。
- `segment_durations` 按 `episode_segment_index` 排序，每项 `segment_id` 与 `duration_s` 必须和同一 `video_manifest` 中对应 SEG 完全一致；`duration_s` 是本批次总时长，必须等于各项之和。
- `displayed_parameter_table` 沿用既有兼容字段名和键结构，保存本次参数及必要执行值，名称不要求把它渲染成表格。所有模式在一句简短开场白后均使用 Markdown 参数列表，先列模型、时长、比例、数量，再列内容和其他必要信息；不拆成逐 SEG 重复参数块。`task_type`、`delivery_format`、`aspect_ratio_and_resolution` 中的分辨率及 `visual_and_continuity` 继续保存实际执行所需值，不作为固定用户参数项展示，也不因隐藏字段而放宽执行约束。`quantity` 始终只保存本批生成/编辑片段数，等于 `planned_video_count`，不改为成片条数；成片条数与本批片段数在列表中分别标明。`segment_durations` 和 `total_duration` 仍分别保存本批逐段时长与本批合计，比例从实际规格中单独展示；所属成片条数与目标时长从已有规划取得。用户实际看到的内容完整记录在 `final_parameters_text`，不新增 JSON 字段、计数或授权状态。
- 普通批次的 `displayed_storyboard_rows` 表示实际展示的一张五列表格；机器结构将第一列拆为 `segment_id + duration_s`，其余四列依次为 `visual_content`、`subject_action`、`audio`、`camera_and_materials`，每个 SEG 恰好一行。轻量首次则保存 `planning.md` 的全片五列概览，使用对应的 `time_range`、`story_and_action`、`audio`、`camera_transition`、`hook`，不强制改成逐 SEG 批次表。内容均从采用主表提取，素材引用真实来源，同批待生成前段的承接按既有依赖规则明示，不伪记为现成输入。
- `final_parameters_text` 保存用户实际看到的完整普通文本，包含简短开场白、按模型/时长/比例/数量开头的 Markdown 参数列表、采用内容及一张分镜表；只有分镜使用表格。普通批次使用本批五列分镜，轻量首次使用规划中的全片五列概览，并在同一消息中展示本批全部人声，不追加另一套批次展示。不列任务类型、交付格式、分辨率、视觉与连续性的固定参数项。展示完整后按原规则实际调用 `interaction.ask`，不因格式精简、数量区分或参数排序增加确认。历史展示原文保持原样，不为新格式改写旧确认。

同批依赖前段真实结果的调用，须由 mainagent 在生成确认前写好完整 Prompt 模板、分镜和接续要求；依赖就绪后只完成真实媒体绑定、必要引用编号及实际请求快照，再按 `delegation.md` 实际委派，不能在这时重新编写剧情或 Prompt 内容。同批授权范围与方案不变时沿用仍有效的批次确认；未来批次仍分别取得授权。确认时保存的表格、原文和数量保持不变；生成后的实际 FRM、路径、哈希及输入顺序写入对应执行记录，不回填覆盖原确认，也不把依赖声明放进实际 `reference_inputs`。等待或输入绑定本身不新增生成任务、不新增确认枚举。

轻量视频目标首次生成使用同一数组登记规划页的标准视频生成确认，并额外写 `confirmation_source: planning_preview`。范围是本次明确列出的首批片段，起于 SEG001，数量仍受统一批次上限约束；规划展示必须包含本批模型、成片与片段数量、适用时长、比例、采用内容与全部人声、声音字幕、参考素材及必要限制与消耗；参数使用 Markdown 列表，只有全片预览使用表格。任务类型、交付格式、分辨率、视觉与连续性不再作为固定用户参数项，所需执行值和约束仍保存在已有记录。该记录的调用 ID、用户原文、时间和 `generate` 结果必须与 planning 确认一致。

多个独立轻量项目同属一次真实生成确认时，先逐条展示各自参数、内容和完整人声，并明确本次共同批次范围；各项目保留独立且唯一的 `confirmation_id`，引用同一真实 `interaction_ask_call_id`、确认结果与时间。每份 manifest 的数量和范围只登记本项目在当前批次的实际片段，`final_parameters_text` 保留含全部当前任务的实际展示原文；不为共同确认虚构多次工具调用。总任务上限按一次真实确认跨项目合计，不能靠拆 manifest 绕过；轻量首次沿用同次规划列表与全片预览，不追加一套批次展示。

`text_to_video` 不得登记媒体输入；`image_to_video` 只登记图片；`media_to_video` 至少登记一类真实图片、音频或视频输入，并按 `video.md` 核对实际 schema；长视频普通续段默认 `video_inputs: []`，只登记实际传入的尾帧、本段必要图片和音频。上一段视频的来源追溯不等于本次工具输入，不为满足路由补传视频。`video_edit` 必须登记真实源视频，在请求中按 `video.md` 锁定原比例、源时长及不足 4 秒输入的已确认例外和授权编辑范围，真实输出只保留工具返回事实。不要求生成后探测 `output_duration_s`、`duration_preserved` 等自填证明；旧 `edit_verification` 仅保留为历史记录。

每集首个 segment 的集内 `incoming_seam` 均写 `START/not_applicable`，仅表示本集没有前一段。`ep_2` 及以后各集的首个 segment 另将 `incoming_episode_seam` 写成 `episode_seams.json` 对应 `EPSEAMxxx` 的完整快照；`ep_1` 首段及非首段的该字段写 `null`。每个视频批次中的同名字段必须与该快照一致；集内 `START` 不能豁免跨集真实事实、参考输入与连续性核验。

### 实际尾帧记录

两种模式均在 `video_manifest_ep_N.json.frames[]` 保存实际帧 ID、源 SEG/版本、真实时间码、文件、哈希及下一调用用途，不再创建独立连续性文件。计划转场仍在分镜执行索引，实际传入顺序仍在本次请求，两者不是帧记录的复制品。

```json
{
  "frames": [
    {"frame_id":"FRM001","segment_id":"SEG001","source_version":"v01","kind":"tail","timestamp_s":15,"file":"episodes/ep_1/04_视频片段/抽帧/尾帧_FRM001_ep_1.png","sha256":"实际文件哈希","used_by_segment":"SEG002"}
  ]
}
```

### delivery_manifest_ep_N.json

完整模式保存最终采用片段、音轨、字幕和交付文件。轻量不创建本文件，将同样的实际字段写入 `video_manifest_ep_1.json.delivery`；单段无后期时直接引用该段真实输出，确有拼接/字幕时记录段序、音轨、字幕来源、参数和任务结果，不复制另一份媒体清单：

```json
{
  "schema_version": "1.0",
  "episode_id": "ep_1",
  "revision": 1,
  "project_data_card_revision": 1,
  "duration_s": 120,
  "duration_display": "2分钟",
  "assembly_confirmation": {},
  "subtitle_enabled": false,
  "clean_master": "episodes/ep_1/05_成片/[项目名]_成片_[比例]_无字幕_v01_ep_1.mp4",
  "subtitle_master": "",
  "asr_source": "",
  "subtitle_source": "",
  "subtitle_burn_params": "",
  "outputs": [
    "episodes/ep_1/05_成片/[项目名]_成片_[比例]_无字幕_v01_ep_1.mp4"
  ],
  "status": "deliverable|blocked"
}
```

轻量省略 `project_data_card_revision`；两种模式常规 `assembly_confirmation` 均为空对象。`segment_ids` 可记录本次采用片段顺序；常规拼接继承既有目标与方案，不新增接受或拼接授权记录。

默认 `outputs` 只能包含一条 `clean_master`；明确要求字幕时内部保留无字幕源，记录真实 ASR 来源、SRT 与烧录参数，`outputs` 只能包含一条 `subtitle_master`。不再要求字幕最终版 JSON、基础检查报告、媒体探测或 ASR 对齐报告；旧字段可留历史空值，不作为门槛。

`deliverable` 表示实际工具完成、结果保存并正式交付，未声称内容质量已审查；`blocked` 表示真实失败、缺输出或无法交付，不冒称完成。不因没有审片改记候选。阶段用 `completed` 收口，不伪造用户确认。

## 状态、失效与一致性

- `制作状态.json` 独占规划与生产阶段状态。`phases.planning` 与 `phases.script` 分别表示项目规划和项目级故事包硬门；`episodes.ep_N.stage_status.script` 表示该集详细剧本。资产及后续项目状态是逐集聚合视图。
- `current_stage: script` 且 `current_episode` 为空时表示项目级故事包；`current_stage: script` 且 `current_episode=ep_N` 时表示该集详细剧本。进入后续制作时，当前集更早创作阶段须为 confirmed，轻量合并阶段及完整模式已批准资产复用可为 merged；纯创作目标交付记 completed 不代表进入后续生产的批准，视频/成片实际交付也用 completed，更晚阶段只能为 `pending|invalidated`；更早集必须至少完成到 `objective.target_stage`，更晚集的详细剧本及后续阶段必须保持 `pending|invalidated`。当前集达到目标后，完整模式下一集从 `script` 开始；轻量只登记独立单集项目。
- 项目索引的单集条目只保存身份、时长和文件指针，不保存 `status` 或 `stage_status`。旧项目中的同名镜像字段允许保留，但推进只读取 `制作状态.json`。
- 每集状态遵循本集阶段拓扑，但不同集允许处于不同阶段：项目仍在规划或项目级故事包阶段时，各分集生产阶段只能为 `pending|invalidated`；进入逐集循环后，仅 `current_episode` 可以处于活动状态，且先活动于 `script`。较早集必须达到目标阶段，较晚集不得提前生成详细剧本或进入资产阶段。
- `project_manifest.json` 是路径索引，`drama_plan.json` 是规划权威，`project_script_manifest.json` 是项目级完整剧本索引，`project_data_card.json` 是跨阶段设定与状态权威，`asset_registry.json` 是共享媒体资产权威，各自不得复制对方的完整字段。
- 单集的完整剧本同时是项目与本集故事权威；多集的全局设定与分集总纲是全剧权威，各集完整剧本是执行细化。修改核心因果、人物弧、结局或分集边界时，受影响的合同与下游阶段按原控制规则失效，不重新生成独立关系矩阵。
- 任一 Markdown 正文修改后更新对应 `source_sha256` 和 revision，并使依赖它的下游 manifest 状态变为 `invalidated`。
- 共享资产版本变化时，只更新 `asset_registry.json` 和受影响分集的 `asset_usage_ep_N.json`，不复制媒体文件。
- 规划阶段可以先登记未来阶段 manifest 的固定路径；进入对应阶段后，该阶段 JSON 中引用的路径必须存在。`episode_id`、文件后缀 `_ep_N`、所属目录 `episodes/ep_N/` 三者必须一致。
- 完整模式连续多集的 `episode_seams.json` 覆盖每对相邻集；同一连续作品的时空省略也登记为 `elliptical`，不能借省略跳过承接。单集作品使用 `ep_1`，不创建该文件且项目指针留空；轻量模式也不创建。

## 不进入 JSON 的内容

- 剧情梗概、人物小传、完整剧本文字。
- 面向用户的参数确认和按内容形态选择的五列剧情节奏预览。
- 人工审美评价、修改建议和完整看片记录。
- 策略库、风格库和方法说明。
- SRT、图片、音频和视频文件本体。

这些内容由对应 Markdown 或媒体文件承载；JSON 只保存路径、哈希、状态、结构化执行字段和引用关系。
