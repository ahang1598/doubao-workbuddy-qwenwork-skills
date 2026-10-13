# 第 0 阶段：项目规划 Reference

当用户提出完整短剧、剧情短视频、微电影、连续故事或长篇剧本制作需求时，先读取本文件。本文件是规划字段、参数确认表和规划状态提交的唯一权威。规划阶段位于剧本之前，是六个生产阶段的前置条件；它负责把目标、受众、卖点、策略、风格、规模、风险和验收方法变成结构化合同，不提前写完整剧情、逐镜分镜、资产 Prompt 或视频 Prompt。

## 本 Ref 关键要求

- 先锁定用户明确要求的主体、动作、场景、风格、时长、比例、镜头方式、台词和禁止项；创意扩充只能发生在未锁定空间，并服务整部作品。
- 规划只锁目标、受众、题材策略、风格、规模、模型、风险和验收方法，不提前写完整剧本、资产 Prompt 或视频 Prompt。
- 参数确认表必须在当前对话中直接展示并等待用户确认；模型、时长、画幅和交付范围确认前不得进入剧本。
- 多集短剧默认按集分别交付成片；只有用户明确要求合集，或形态为单条短片、微电影、单部长视频时，才规划单个完整视频。
- 涉及真实人物、品牌、平台规则、热点或“最新”信息时先检索并记录日期。
- 所有未确认事实写为待验证假设，不能伪装成用户要求或可靠事实。

## 目标

在投入剧本、资产和生成额度前回答：

- 为谁制作，准备投放到哪里。
- 观众为什么会继续看，最终获得什么情绪回报。
- 这部作品与同类内容的差异是什么。
- 是否需要通过检索补足题材语境、同类结构、平台表达、行业事实或开源视频流程经验。
- 采用什么呈现形态、题材、冲突和叙事机制。
- 使用什么可执行视觉锚点，哪些风格机制明确排除。
- 情绪如何起伏和兑现，但不套固定秒数、固定气爽比例或固定反转频率。
- 交付什么内容形态、多少集、每集及总时长、什么画幅，分别使用什么生图模型、视频模型和视频生成确认轮次；完整模式必须包含每集 `3-4` 张剧情高光关键帧阶段；输出语言、视频语言和字幕语言静默写入内部合同，不作为参数确认项；字幕默认关闭及交付方式必须作为参数确认项告知用户，用户明确要求字幕时才在最终音轨锁定后的成片阶段生成并烧录字幕。
- 多集项目是逐集成片交付还是用户明确要求的合集交付；未说明时默认逐集交付。完整模式必须明确写入“先锁全局故事圣经、全部分集推进总纲和最终结局，再按集执行详细剧本 -> 资产 -> 分镜 -> 关键帧 -> 视频 -> 成片确认”的生产顺序。
- 哪些事实、授权、平台政策和敏感内容仍需核实。
- 后续六个生产阶段分别如何验收。

## 边界

- 规划阶段不写完整剧情梗概、人物小传、分场剧本或完整台词；这些属于 `scriptwriter.md`。
- 参数确认表固定使用下文规定的逐行字段语义和顺序，不使用 Markdown 表格；字段显示名必须按 `language_contract.output_language` 本地化。其后必须按内容形态选择下文唯一适用的五列“分镜预览表/剧情节奏预览表”，预览表可以使用 Markdown 表格。不得改字段语义、顺序、增删列或混入内部工具、路由、schema、状态和代码字段。
- 不生成角色、场景、道具、音色、图片或视频。
- 不把 `题材受众库.md` 的画像、市场倾向和平台偏好伪装成实时事实。
- 不强制选择电影大师；风格锚点也可以是项目语言的光线、色彩、构图、材质和节奏机制。
- 不用固定 `3 秒`、`15 秒`、`3:1`、固定集数、固定付费点或固定镜头数量代替剧情判断；这不影响默认视频模型单 SEG 不超过 `15` 秒的技术上限。
- 创作调研不是抄故事、找爆款套壳或为虚构内容伪造事实；只吸收可迁移的机制，并保留未采用内容的边界。

## 输入与 Reference 路由

规划阶段始终读取：

- 用户原始指令及后续修改。
- `control-contracts.md`。
- 当前工具 schema 中可核实的生图模型、视频模型、时长、画幅、数量和模态能力。
- `剧作方法与类型库.md`，用于故事引擎、关系与信息方法、类型规律、观众契约、冲突发动机与结局义务。
- `题材亮点与传播库.md`，用于呈现类别变体、故事发动机、项目记忆点、钩子、反转、传播句和节拍候选。
- `题材受众库.md`，用于受众心理假设、平台观看场景、题材适配和待验证边界。
- `电影大师风格库.md`，用于建立可拍视觉锚点、风格排除项和后续分镜可继承的光线/色彩/构图/节奏机制。

额外问题处理读取：

| Reference              | 触发条件                                         | 采用内容       |
| ---------------------- | ------------------------------------------------ | -------------- |
| `troubleshooting.md` | 输入冲突、事实缺失、工具能力不匹配或规划无法闭合 | 诊断和回退路径 |

涉及真实品牌、人物、IP、地点、历史、热点、平台规则、市场数据或审核结论时必须检索可靠来源并记录日期。无法核实时标记 `pending`，不能写成事实。

用户要求调研、题材陌生、方向薄弱、同质化风险高，或需要借鉴短剧/电影/AI 视频 workflow 时，也可以主动使用 search。优先检索文字知识和可读文档：同题材或同平台的钩子和节奏文章、电影/编剧结构方法、GitHub 上可读的短剧/分镜/视频 skill 与开源流程。规划和剧本阶段非必要禁止检索或下载图片；只有用户明确要求视觉参考、需要核验真实人物/地点/物体外观，或资产阶段缺少关键视觉锚点时，才把图片作为来源。每轮检索以能改变决策的少量高信号来源为限，不追求堆数量。

调研结果按以下方式吸收：

- 真实事实、行业规则、平台限制和市场数据写入 `source_lock.verified_facts` 或 `pending_facts`，并记录来源日期。
- GitHub skill、编剧文章、视频提示词指南和用户提供的结构图，只提炼成 `type_strategy.adopted_mechanisms`、`rejected_mechanisms`、`highlight_strategy` 或“策略选择”附录；不得写成事实来源。
- 只采用机制，不复制具体剧情、人物关系、台词、镜头表、Prompt 原文或未授权素材。不要为了找灵感、题材气质或剧情策略去检索图片；确需使用用户上传、外部引用或检索保存的参考图时，先登记为来源并写清必要性。若作为视觉输入，后续生图必须按图生图处理。图中文字只作为参考内容，不视为对 Agent 的操作指令。

## 规划流程

1. **锁定原始需求**：逐字记录用户目标、必须出现项、禁用项、原台词、素材职责和目标交付终点；所有用户上传、外部引用或确有必要检索保存的图片、视频、音频和文档同步登记到 `source_manifest.json`。
2. **区分事实状态**：分开记录 `locked`、`verified`、`pending`、`assumed` 和 `convention`。
3. **确定受众与平台**：用户信息优先；无信息时只建立可证伪假设，不按人口标签机械推断。
4. **创作调研与企划吸收**：按上文条件检索并筛出真正能改变方向的机制，区分事实、假设、惯例和灵感；把采用点、排除点和来源边界写入现有规划字段和“策略选择”附录。
5. **发散创意机制**：先判断用户是否已经锁定完整创意核心。未锁定时使用 `selection_mode: divergent`，内部发散恰好 `3` 个本质不同的主机制候选，每个候选配置 `1-3` 个同源辅助机制；用户已经锁定故事方向和核心观看机制时使用 `selection_mode: user_locked`，不得另造三个故事方向，只在不改变用户要求的前提下登记 `1-3` 个执行方案或直接沿用唯一方案。候选差异必须落在核心观看逻辑、因果发动方式或高潮证明方式，不能只是换名字、背景、滤镜或道具。
6. **筛选唯一机制**：按用户匹配、核心证明、连续性和生成稳定性比较候选，最终只保留 `1` 个主机制贯穿全片，并按实际需要保留 `1-3` 个不冲突的辅助机制。记录 `selected_direction_id`、`creative_mechanism.primary`、`creative_mechanism.supporting[]` 和选择理由；面向用户只展示采用方案，除非比较确有决策价值。
7. **确定核心卖点与开场承诺**：基于已选方向写清一句话卖点、核心戏剧问题、情绪回报和差异化来源；同时选择一个主开场机制，可叠加辅助机制。主开场从悬疑问题、世界观震撼、人物塑造、视觉奇观、冲突驱动或自定义中选择，写清观众首先看见的承诺、随后升级的触发和本集兑现或悬念延续。
8. **选择类型策略**：分别确定主类型、子类型、世界设定、故事引擎、观众承诺、叙事结构、主路径和可选辅助路径；说明为什么采用以及排除什么。类型组合必须写清各自承担的功能，不能只堆标签。
9. **建立亮点策略**：从 `题材亮点与传播库.md` 选择或自定义一条主故事发动机，写出项目签名、亮点支柱、跨集分布与明确排除的俗套。亮点必须同时说明题材职责和呈现类别表达。
10. **建立导演与视觉合同**：规划阶段只形成一张导演总控卡的项目级输入，把视觉风格并入同一决策中心，至少包含媒介形态、构图骨架、光线方向、色彩关系、材质、镜头质感、字体/版式和明确剥离项；禁止另建“强风格系统卡”，也禁止只写“电影感”“高级感”。
11. **推导节奏波形**：不套固定时段模板。先列出不可移动的内容节点；判断每个节点的信息密度、动作强度和阅读时间；确定唯一主重拍；决定节点之间使用切镜还是镜内连续；先保证动作和核心证明，再分配剩余时长；最后用 `1-5` 强度序列检查是否过平或全程过强。可选波形包括“快起 -> 稳证 -> 快收”“逐级加速 -> 高光 -> 短停”“快慢交替 -> 汇聚”“连续推进 -> 节点变速”“结果前置 -> 倒推线索 -> 原因揭示”“稳态建立 -> 突然打断 -> 连续应对 -> 新稳定”“单点触发 -> 层层扩散 -> 整体响应 -> 回收”“两线交替 -> 节奏对齐 -> 汇合”“问题脉冲 -> 回答脉冲 -> 证据停留”“克制积累 -> 局部释放 -> 完整爆发 -> 余韵”“建立规则 -> 两次变奏 -> 打破规则 -> 新规则收束”“起点 -> 偏离 -> 回归 -> 无缝 Loop”。按项目因果选择或自定义，不把候选波形变成新模板。
12. **规划规模与工具**：内部记录生图与视频的实际执行方式；面向用户只确认生图模型和视频模型名称，不展示工具名、路由或宿主能力。同步确认内容形态、集数、单集和总时长、画幅、片段上限、资产复杂度、最终交付形式和字幕交付方式；输出语言、视频语言和字幕语言静默写入内部合同，不在参数确认表中展示或询问。多集短剧默认逐集交付；只有用户明确要求合集时才规划合集版。用户未指定视频模型时固定使用 `seedance 2.0 fast`，所有 SEG 不超过 `15` 秒，不得自主切换；只有用户明确指定 `seedance 2.5` 时才能使用并按其能力规划最长 `30` 秒。
13. **预判风险**：登记事实、授权、平台、敏感内容、长篇漂移和技术可拍性风险及缓解措施。集数超过 `10` 时，必须把剧情、人设、伏笔和资产漂移风险写入参数确认表，并说明先锁项目级故事圣经、全部分集推进总纲、人物弧、伏笔账本与结局，随后逐集生成详细剧本和完整制作；该提示属于参数确认表的一部分。
14. **设计验收**：为规划、剧本、资产、分镜、关键帧、视频和成片分别写可验证检查项。
15. **编译强制参数确认表**：规划完成后先按下方固定结构生成待展示正文，但此时不得向用户发送；所有值必须预先填写，不向用户留空或要求用户填表，也不得增加“工具能力”“路由”“状态”“内部检查”等内容。
16. **建立项目与分集索引**：所有模式按 `manifests.md` 创建 `project_manifest.json`、`source_manifest.json` 及全部 `episode_manifest_ep_N.json`；每个 `episode_manifest_ep_N.json` 必须使用顶层 `stage_manifests` 登记各阶段路径，不得使用旧名 `manifests`。完整模式另创建 `episode_seams.json`，并预登记 `project_data_card_path`、`project_script_manifest_path`、共享 `asset_registry_path` 和分集阶段路径；轻量模式将不适用的数据卡、剧本、资产与接缝索引留空，只登记内部完整分镜、视频执行与最终交付所需路径。单条短片、微电影和单部长视频也创建 `ep_1`。
17. **落盘与内部检查**：将 `制作状态.json.phases.planning` 写为 `awaiting_confirmation`，运行 `drama_lint.py --stage planning`；默认不向用户输出“正在校验”、错误数、警告数或 `release_ready`。
18. **正式确认**：内部检查通过后，参数确认表仍是规划完成后的第一项对用户动作；在当前对话中仅输出一次参数确认表正文，不得改用文件附件、文件链接或 Markdown 落盘代替。在用户明确确认前禁止写任何剧本正文、分镜、资产 Prompt 或视频 Prompt。用户明确确认全部参数后将规划阶段写为 `confirmed`，才可进入剧本阶段。用户只选择方向但未确认其余参数时，更新完整确认列表并再次等待确认。

参数确认表是规划完成后的第一项对用户动作，但“完成”以步骤 17 的落盘和内部检查通过为准；步骤 15 只在内部编译正文，不构成展示或交付。

状态提交规则：`制作状态.json` 是唯一状态源。完整模式 `video|final` 目标按 `control-contracts.md` 调用项目执行确认，完整模式其他目标使用普通规划确认；轻量模式在完整参数与五列预览展示后，直接按 `interaction-ask-video-clarification-ref.md` 调用标准视频生成确认，只有 `generate` 才同时完成规划确认并授权当前唯一视频。确认后，完整模式进入项目级 `script`；轻量模式将 `script|assets|storyboard|keyframes|video` 写为 `merged` 并进入 `ep_1.final`。非 Mobile 下，只有流程将进入 `assets|storyboard|keyframes|video|final` 并实际生成图片或视频时，才把 Workspace 初始化或复用作为确认成功后的第一项执行动作；纯规划或纯剧本目标不初始化。

## 创意机制选择算法

在规划流程第 5-6 步执行。目标不是凑出三个题材简介，而是教模型判断“观众因为什么持续看、剧情靠什么持续发动、高潮靠什么被证明”。

1. **判断是否允许发散**：先逐项读取 `source_lock.user_requirements|must_include|must_avoid`、用户原台词、已确认素材职责和目标交付终点。若用户已经锁定主角、核心目标、主要阻力、关键反转或高潮兑现中的大部分，并明确要求按该方向制作，写 `selection_mode: user_locked`；否则写 `divergent`。拿不准时只把未锁定部分视为可创作空间，不得以“方案比较”为由改写已锁定内容。
2. **提取机制问题**：用一句问句写出本片的核心观看逻辑，例如“主角能否在身份暴露前拿回证据”。再分别填写因果发动方式和高潮证明方式：前者说明什么选择会引出下一轮阻力，后者说明观众最终通过什么可见行动、证据或关系结果确认答案。只写题材、背景或情绪不算机制。
3. **生成候选**：`divergent` 时恰好生成 `3` 个主机制，每个都使用同一批用户锁定事实，但至少改变“核心观看逻辑、因果发动方式、高潮证明方式”中的一项，并为主机制配置 `1-3` 个同源辅助机制。`user_locked` 时保留用户机制，只比较 `1-3` 个不改变核心答案的执行路径；若只有一种合理路径，直接登记唯一方案，不虚构差异。
4. **执行反换皮测试**：把候选的姓名、年代、地点、道具、滤镜和媒介标签全部暂时抹去，再比较其“主角采取什么策略 -> 对手/规则如何反馈 -> 局势如何变化 -> 高潮如何证明”。抹去外壳后仍是同一条因果链的候选属于伪差异，合并后重做；只改变台词措辞、职业、场景、视觉风格或证据道具也属于伪差异。
5. **执行可持续测试**：逐个候选推演至少一轮“目标 -> 阻力 -> 策略 -> 反馈 -> 新局势”。多集项目再推演建立、变奏、升级、回收四个阶段。无法自然产生下一轮选择与代价、只能依赖巧合、反派无理由犯错或临时新增设定的候选淘汰。
6. **按顺序筛选**：先淘汰违反用户锁定项和禁用项的候选，再淘汰无法完成核心证明的候选，再比较人物/资产/场景跨段连续性，最后比较在已确认模型和时长内的生成稳定性。不得用生成方便覆盖用户匹配或高潮证明；只有前一层都成立时才比较后一层。
7. **锁定与记录**：把唯一主机制写入 `creative_mechanism.primary`，只保留与它同向且不会争夺高潮解释权的 `1-3` 个辅助机制；`selection_evidence` 分别记录用户匹配、核心证明、连续性、生成稳定性和淘汰理由。`selected_direction_id` 必须指向采用候选，面向用户默认只展示采用方案。
8. **检查与回退**：若三个候选无法通过反换皮测试，回到第 2 步重写机制问题；若所有候选都违反用户锁定项，停止发散并改为 `user_locked`；若采用候选无法在时长内完成“发动 -> 升级 -> 证明”，先缩小事件范围或调整规模，再重新筛选，不得直接删掉高潮证明。

## 交付物

本阶段落盘产物为 `drama_plan.json`、项目/来源/分集入口、空的跨集接缝登记、共享资产入口、制作状态、用户确认记录和操作日志。参数确认表只在当前对话中直接输出，不生成独立 Markdown 文件；其已确认参数由 `drama_plan.json` 承载，确认事实由 `用户确认记录.jsonl` 承载。

## drama_plan.json

`drama_plan.json` 同时承担创作规划和执行规划，是后续阶段的唯一项目级中间层。不要复制整套空模板；按下列结构写实值，字段含义和取值规则见“字段要求”：

```text
schema_version, project_id, revision
objective: delivery_type, workflow_mode, target_stage, project_goal, success_definition, non_goals
source_lock: user_requirements, must_include, must_avoid, verified_facts, pending_facts, assumptions
language_contract: instruction_language, output_language, video_language, subtitle_language, preserve_source_dialogue, explicit_overrides
audience_plan: user_defined, target_audience, core_pain_or_desire, platform, locale, evidence_status, verified_sources, viewing_focus, emotional_payoff, platform_viewing_context, expression_boundaries, execution_sources
direction_candidates[], selected_direction_id, selection_reason
creative_mechanism: selection_mode, candidates[], primary, supporting[], selection_evidence
creative_proposition: one_sentence_value, core_dramatic_question, emotional_reward, differentiation, proof_or_payoff
opening_strategy: opening_id, primary_type, supporting_types, opening_window, first_observable_promise, escalation_trigger, payoff_or_rollover, bans
type_strategy: format, subject_route, subject_subroute, format_strategy, intersection_strategy, genre, subgenre, setting, core_conflict, story_engine, audience_promise, tone, narrative_structure, main_path, supporting_path, adopted_mechanisms, rejected_mechanisms
highlight_strategy: primary_story_engine_id, secondary_story_engine_id, secondary_engine_role, project_signature, highlight_pillars[], distribution_policy, rejected_cliches
style_contract: anchor_type, anchor, lighting, color, composition, material, camera_tendency, sound_tendency, excluded_mechanisms
emotion_design: curve_type, stages[], character_curves[]
rhythm_design: immutable_nodes[], node_loads[], primary_downbeat, transition_choices[], duration_allocation, intensity_sequence[], selected_wave
scale_plan: format_mode, episode_count, episode_durations_s, episode_duration_displays, total_duration_s, total_duration_display, duration_display_mode, aspect_ratio, segment_duration_policy, video_confirmation_policy
model_plan: image, video
delivery_settings: dialogue_language, asr_language_code, output_fps, intro_outro_policy, bgm_policy, subtitle_enabled, subtitle_policy, video_generation_subtitles, audio_policy, final_deliverables
asset_forecast: estimated_character_count, estimated_scene_count, estimated_characters, estimated_scenes, estimated_story_props, global_style_moodboards, estimated_keyframes, voice_roles, known_state_versions, reference_budget_risks
risk_plan, verification_plan, handoff
```

### 字段要求

- `objective` 明确做什么和不做什么，防止后续扩张范围。`workflow_mode` 默认为 `full`；只有用户要的是一条独立极短视频、不要求逐阶段审查，且总时长不超过当前已确认视频模型的轻量上限时，才能写 `lightweight`：默认或 `seedance 2.0` 系列模型为 `15` 秒以内；用户明确指定并确认 `seedance 2.5` 时为 `30` 秒以内。多个互不相关的视频必须拆为多个独立轻量任务，分别规划和确认。轻量流程为规划参数与最多 `8` 行预览 -> 视频生成确认 -> 内部十五列完整分镜 -> 单条成片；`script|assets|storyboard|keyframes|video` 均写 `merged`。轻量模式只生成与完整模式同列定义、同填写标准的十五列详细分镜来指导 Prompt，不创建导演总控卡、SEG 执行表、连续性账本、参考输入计划、关键帧计划、分镜 JSON、最小数据卡或其他创作配套文件；视频 manifest、Prompt、请求快照和工具记录仍按实际生成与追溯需要保存。内部完整分镜只能扩充确认预览，不能改写。轻量模式只交付字幕策略对应的唯一最终视频；字幕开启时原始无字幕视频及其他中间媒体仅内部保存。`target_stage` 必须对应用户实际要求的最终交付阶段。
- `source_lock` 保存用户原始要求和事实状态，不能把假设写进 `verified_facts`。
- `creative_mechanism.selection_mode` 只能为 `divergent|user_locked`。`divergent` 时 `candidates` 必须恰好包含三个不同主机制候选；`user_locked` 时保留用户锁定的唯一主机制，并允许登记 `1-3` 个不改写故事核心的执行候选。每个候选带 `1-3` 个同源辅助机制；`primary` 只能选一个，`supporting` 只能保留与主机制同向且互不冲突的 `1-3` 项。筛选证据覆盖用户匹配、核心证明、连续性和生成稳定性。
- `language_contract` 锁定本项目语言：`instruction_language` 为当前用户指令主语言，`output_language` 控制用户可见回复和文件正文，`video_language` 控制视频人声、视频 Prompt 自然语言和音色描述，`subtitle_language` 控制字幕文本；三者按用户指令主语言或显式语言要求静默写入，不在参数确认表中展示或询问。用户显式指定不同语言或保留原文台词时，只写入 `explicit_overrides`。参数确认表仍必须显示“字幕”项，告知默认不加字幕、片段交付前检查并擦除字幕残留、最终直接拼接无字幕成片；用户明确要求字幕或修改字幕策略时，在同一“字幕”项中展示对应设置。
- `audience_plan` 的平台、地域和受众结论必须标记来源状态；`viewing_focus` 锁定观众首先关注和持续追踪的信息，`emotional_payoff` 锁定应兑现的情绪回报，`platform_viewing_context` 锁定观看场景与可读性约束，`expression_boundaries` 锁定已确认的表达禁区。这四项都是后续 `storyboard.audience_execution` 的直接来源，不得留到分镜阶段重新推导受众。`execution_sources` 固定登记四项路径：`audience_plan.viewing_focus`、`audience_plan.emotional_payoff`、`audience_plan.platform_viewing_context`、`audience_plan.expression_boundaries`。
- `creative_proposition` 必须能指导钩子、高潮和结尾，不能只写“好看”“高级”。一句话故事核心必须同时包含主角、外在欲望、最大阻力、时间压力、失败代价和反讽/刺激点；如果只能写成“成长故事”“复杂爱情”“职场背叛”等抽象主题，先压尖为一个可拍局面，再进入剧本阶段。
- `opening_strategy.opening_id` 固定为项目级 `OPEN001`；`primary_type` 只能选一个，`supporting_types` 只能增强主机制，不能堆叠互相无关的卖点。`opening_window` 按实际时长和剧情写首个叙事节拍范围，不采用固定“前几秒”公式；`first_observable_promise` 必须是画面、动作、声音或冲突中可被看见或听见的事实，`payoff_or_rollover` 必须回到后续具体场次或段落。第 1 集必须直接继承该合同；后续集可变体，但必须在剧本合同中明确变体理由和它如何延续项目承诺。
- `type_strategy` 只保存实际采用和排除的机制，不复制整个策略库。`format` 从动画/卡通短剧、漫剧、AI 真人/数字人短剧、口播解说短剧、微电影/短片中选择或写明用户自定义形态；`subject_route` 从 `剧作方法与类型库.md` 第二部分的十一种题材路由中选择。
- `subject_subroute` 在年代古风、校园职场、战争军事、玄幻奇幻、励志成长、公益教育等合并词下必须进一步填写主子路由；另一子路由只能作为辅助职责。`format_strategy` 的四项分别锁定叙述载体、场景颗粒、台词/旁白和表演/动作策略；`intersection_strategy` 的四项分别锁定该类别×该题材的钩子、冲突、高潮兑现及制作补偿，禁止只重复两个标签。
- `genre/subgenre/setting` 必须正交，`story_engine` 必须能持续制造选择与代价，`audience_promise` 必须在结局兑现。
- `highlight_strategy.primary_story_engine_id` 可引用题材库 ID，也可使用 `CUSTOM-` 前缀登记自定义发动机。`project_signature` 必须说明本项目不可替换的讲法；`highlight_pillars` 每项都要有铺垫、兑现、题材职责、形态表达和独特性检验。
- 极短单片可以只守住一个主要亮点；总时长超过 60 秒或多集项目至少规划两个不同维度的亮点支柱。`distribution_policy` 写清建立、变奏、升级和回收，`rejected_cliches` 明确本项目不采用的廉价捷径。
- `style_contract` 必须是可观察机制，并作为唯一导演总控卡的视觉子系统继承到角色、场景、道具、关键帧和视频；不得另建第二张风格决策卡。至少填写媒介形态、构图骨架、光线方向、色彩关系、材质、镜头质感、字体/版式和明确剥离项。用户明确要求混合风格时，写清主风格、例外元素和可观察边界。`camera_tendency` 只是倾向，逐镜运镜仍由分镜阶段决定。
- `emotion_design.stages` 动态增减，不能按固定秒数或固定集数填充。`rhythm_design` 必须保存六步推导结果和 `1-5` 强度序列，不得直接套固定的 `0-3 / 3-7 / 7-11.5 / 11.5-14 / 14-15` 时段。`character_curves` 只覆盖承担主要情绪转折的角色；每次变化必须写出事件触发、前后状态、可见证据和关系后果，不能把 BGM、滤镜或抽象情绪词当成角色变化本身。
- `scale_plan.format_mode` 区分单条短片、多集短剧、微电影和长视频。单条短片通常为 `15-60 秒`；多集短剧常规单集为 `1-3 分钟（60-180 秒）`，极短集机制或用户明确要求时支持 `15-60 秒`；微电影通常为 `5-10 分钟（300-600 秒）`。这些范围只用于推导，最终必须结合用户指令、剧本事件量、对白预算和自然切点写入准确秒数。
- `episode_duration_displays` 与 `episode_durations_s` 逐项对应，`total_duration_display` 与 `total_duration_s` 对应。单条/单部作品对用户只显示总时长；多集项目必须显示集数、每集时长和总时长，两个逐集数组数量等于集数且总和等于 `total_duration_s`。单集时长使用自然时长格式；总时长使用下文规定的“精确秒数/分钟换算”格式。
- `model_plan.image` 和 `model_plan.video` 必须分开记录模型、用途和 schema 核实状态。用户未指定生图模型时写 `seedream 5.0 flash`、`selection_source: default`、`user_requested_model: ""`；用户明确指定其他生图模型时写 `selection_source: user_explicit` 和准确的 `user_requested_model`。用户未指定视频模型时写 `seedance 2.0 fast`、`selection_source: default`、`user_requested_model: ""`；用户明确指定其他视频模型时写 `selection_source: user_explicit` 和准确的 `user_requested_model`。具体视频工具不在规划阶段预设，进入视频执行时再按真实图片、视频和音频输入选择。只有任务明确包含“编辑已有视频”时才登记编辑用途和来源；未使用该能力时不得创建空配置占位。默认模型也必须按当前宿主实际 schema 核实；不可用或无法核实时写 `pending` 并停在参数确认表，不得猜测或静默换模型。
- 禁止代理因质量、时长、额度、重试或工具偏好自主切换视频模型。默认 `seedance 2.0 fast` 的每个 SEG 不得超过 `15` 秒；视频阶段 `media_to_video` 上传视频参考总时长不得超过 `14` 秒、音频合计不得超过 `15` 秒，且每次最多传 `3` 个视频参考和 `3` 个音频参考、单个视频/音频参考不得低于 `2` 秒。只有用户明确指定并确认 `seedance 2.5` 后，才允许使用该模型及最长 `30` 秒片段，此时上传视频参考总时长不得超过 `28` 秒、音频合计不得超过 `30` 秒。
- 当前视频模型不可用时停在参数确认表并说明“当前模型暂不可用，需要重新选择模型”，不得自动用 `seedance 2.5` 或其他模型替代；只有用户明确选择新模型并重新确认完整参数后才能继续。
- 参数确认表中出现 `seedance 2.5` 时，必须写成 `seedance 2.5（会员模型并且消耗最多的额度）`；出现 `seedream 5.0 pro` 时，必须写成 `seedream 5.0 pro（会员模型并且消耗最多的额度）`。任何会员模型都必须在调用前明确告知用户。
- 完整模式的规划确认只建立项目级基线和执行授权，不授权生成视频。进入视频阶段后，任何生成、重生、返修或继续下一段都必须按 `video-batch-confirmation.md` 展示当前批次两张表并取得 `generate`；每批连续 `1-2` 个 SEG。确认后串行生成，每个片段返回后立即交付，非 Mobile 写入 Canvas 并回读成功后才继续下一个；片段全部交付后再做拼接确认。轻量模式首次生成例外地直接复用规划参数列表和最多 `8` 行预览作为唯一视频生成确认依据，不再展示批次两张表或进行第二次确认；轻量视频返修或重生仍按单视频批次重新展示并确认。
- `delivery_settings` 锁定最终输出帧率、片头片尾、BGM、字幕开关、视频阶段禁用模型直出字幕、音频职责和最终交付形式。`dialogue_language` 必须与 `language_contract.video_language` 填写同一显示值；`asr_language_code` 单独保存宿主 ASR 或字幕对齐可用的语言码。`output_fps` 记录当前生成与交付链路支持的值；`intro_outro_policy`、`bgm_policy` 不适用时也要明确写“无”。每集最终只交付一个视频版本：默认写 `subtitle_enabled: false`、`subtitle_policy: disabled`、`final_deliverables: ["clean_master"]`；用户明确要求字幕时才写 `subtitle_enabled: true`，并写 `final_deliverables: ["subtitle_master"]`。逐段预览仍交付清理后的无字幕片段；最终音轨锁定后按 `delivery.md` 生成字幕、烧录字幕版并完成验收，无字幕母版只作为内部制作文件。
- `asset_forecast` 只做成本和复杂度预判，不生成资产，也不定义稳定 ID。`estimated_characters` 与 `estimated_scenes` 必须覆盖预计出现的全部角色和场景数量，每项只写名称与一句大致描述；`estimated_story_props` 只预估会多次出现、跨场景出现、跨片段承接、状态会复现，或用户明确要求单独生成道具设定图的关键/复现/功能性道具；一次性证据物、一次性手持物、一次性特写物和普通环境装饰不列入道具资产预估。外貌、空间布局、状态版本、身份锚点和稳定编号统一在剧本阶段的 `project_data_card.json` 定义。必须估算主要场景共享布局参考与一张全局 moodboard。关键帧只按集级高光时刻估算：完整模式每集必须 `3-4` 张，不估算生成式首帧或尾帧。
- `risk_plan` 每个高风险项必须有缓解措施、待确认项或明确接受理由。
- `verification_plan` 的每一项必须可观察、可读回或可播放验证。

## 对话参数确认表：开始写剧本前的强制条件

这不是可选摘要，而是剧本阶段的输入条件。它必须直接出现在当前对话中，不创建或附加 Markdown 文件。面向用户的消息只输出固定开场语义、已填写参数列表、分镜预览表/剧情节奏预览表和确认请求。禁止附加内部工具名、接口名、路由、schema、字段名、状态、任务 ID、内部路径、校验过程或宿主能力说明。

### 固定开头语义

按交付形态选择一句语义，不添加技术性前言；正式输出必须改写为 `language_contract.output_language`：

```text
[single short / micro film / long video opening semantic:
state that the plan is for 1 work; include total duration, aspect ratio, content form, genre strategy, visual style, and core conflict or emotional goal.]

[multi-episode drama opening semantic:
state episode count, per-episode duration or duration range, total duration, aspect ratio, drama type, genre strategy, visual style, and core conflict or emotional goal.]
```

### 强制参数列表

```text
[localized title for creation and generation parameter confirmation]
- **[content form]:** [single short / multi-episode drama / micro film / long video, localized]
- **[story summary]:** [protagonist, goal, obstacle, core change, ending direction]
- **[genre and style]:** [selected genre type and executable visual mechanism]
- **[image model]:** [one user-facing model name; include required membership/cost note when applicable]
- **[video model]:** [one user-facing model name; include segment duration limit and required membership/cost note when applicable]
- **[episode count]:** [integer; use 1 for a single work]
- **[duration per episode]:** [multi-episode only; use the standard duration display format]
- **[total duration]:** [use the standard duration display format]
- **[aspect ratio]:** [9:16 / 16:9 / other valid value]
- **[sound delivery]:** [intro/outro and BGM; write none when not used]
- **[subtitles]:** [default disabled; inspect every segment before delivery, erase unexpected subtitles before delivery, and deliver the final video without subtitles; when explicitly requested, keep segment previews subtitle-free and generate, align, and burn subtitles only after the final audio track is locked]
```

轻量模式首次生成时，上述列表还必须继续逐行展示以下视频执行参数，确保同一条消息完整满足 `interaction-ask-video-clarification-ref.md`，不得另建第二张参数表：

```text
- **[task type]:** [video generation task, localized]
- **[delivery format]:** [actual video file format and delivery method]
- **[video quantity]:** [fixed to 1]
- **[resolution]:** [actual output resolution together with the confirmed aspect ratio]
- **[visual and continuity]:** [locked visual direction, character/product identity, and continuity constraints]
- **[reference materials]:** [all actual image/video/audio inputs, or explicitly none]
- **[tool limits and cost]:** [model duration/input limits and high-consumption notice]
```

- 每一项均由系统根据用户指令和规划结果直接填写，方括号只表示本规范中的字段语义说明，不得出现在正式确认中；正式字段显示名必须使用 `language_contract.output_language`。
- 输出语言、视频语言和字幕语言不作为参数确认项：语言按当前用户指令主语言或显式语言要求静默写入 `language_contract`。字幕必须作为参数确认项展示：默认写明“不加字幕，片段交付前检查并擦除字幕残留，最终直接拼接无字幕成片”；用户明确要求字幕或修改字幕策略时，在“字幕”项中写明对应设置。不得恢复为输出语言、视频语言、字幕语言三条字段。
- 当集数超过 `10` 时，必须在参数列表后、分镜预览表/剧情节奏预览表前加入长篇风险提示，说明剧情、人设、伏笔和资产可能漂移，以及将先锁全局故事圣经、全部分集推进总纲、人物弧、伏笔账本和最终结局，再逐集生成详细剧本并完整制作；该提示属于参数确认表的一部分。
- 内部可以按输入情况分别记录执行方式，但用户可见的“生图模型”和“视频模型”各只显示一个模型名及必要的会员/片段时长提示。
- 会员模型提示必须紧跟模型名，不能只在说明文字、脚注或内部 JSON 中记录；用户明确确认整份参数后才能调用。
- 参数确认表全文不得出现“轻量模式”“完整模式”“流程模式”、`workflow_mode`、“交付范围”“目标响度”“LUFS”、内部工具名、`schema`、`manifest`、`source_manifest`、`stage_manifests`、`selection_source`、`user_requested_model`、`tool_mode`、`task_id`、检查机制或“当前宿主未暴露”等内部表达。轻量模式新增字段仍使用自然用户语言，不暴露模式名。
- 单条短片、微电影和长视频不显示“每集时长”，但仍显示“集数：1”和总时长。
- 单集时长使用自然时长格式：`60` 秒以内写秒数，例如 `48秒`、`60秒`；超过 `60` 秒的整分钟写 `X分钟`；超过 `60` 秒的非整分钟写 `X分Y秒`，例如 `1分15秒`、`2分45秒`。总时长不超过 `60` 秒时只写秒数；超过 `60` 秒时必须同时写精确秒数和分钟换算，固定使用“`120秒/2分钟`”“`165秒/2分45秒`”这类格式，便于同时核对生成预算和观看时长。

### 分镜预览表 / 剧情节奏预览

必须紧跟参数列表，并根据内容形态二选一。下列表头只定义列语义和顺序；正式表头必须按 `language_contract.output_language` 本地化：

#### 多集短剧

| 集数                             | 标题               | 核心剧情与动作                                 | 台词/声音              | 钩子与亮点                 |
| -------------------------------- | ------------------ | ---------------------------------------------- | ---------------------- | -------------------------- |
| 第1集；合并时写第1-3集等连续范围 | 本集或连续集段标题 | 主体、关键行动、冲突变化、结果及与下一集的关系 | 对应声音短摘要或“无” | 本段钩子、反转、回报或悬念 |

- `8` 集以内必须每集一行；超过 `8` 集时必须将相邻集浓缩合并为恰好 `8` 行。
- 合并只允许连续集数范围，必须从第 `1` 集连续覆盖到最后一集，不得跳集、重叠、倒序或省略中间集。
- 合并后的每行仍需写清这一连续集段的起点、发展、结果及如何承接下一行，不能只罗列互不关联的事件。

#### 单集、短片、微电影或长视频

| 时间         | 核心剧情与动作                                 | 台词/声音              | 运镜衔接                     | 钩子与亮点                 |
| ------------ | ---------------------------------------------- | ---------------------- | ---------------------------- | -------------------------- |
| 连续时间范围 | 主体、关键行动、冲突变化、结果及与下一段的关系 | 对应声音短摘要或“无” | 只概括主要观察方式和前后衔接 | 本段钩子、反转、回报或收束 |

- 表格最多 `8` 行；剧情节点超过 `8` 个时合并相邻时间段，不得删除故事起点、关键发展、高潮或结尾。
- 时间必须从 `00:00` 连续覆盖到已确认总时长，不得有空档、重叠、倒序或遗漏结尾。
- 合并后的每行仍需保持故事因果和动作承接，从头到尾形成完整走向。
- 该五列表必须是整个剧本或故事的简洁预览版：从开端连续覆盖到最终结局，每行足以概括对应范围的主体、关键动作与结果、声音、主要观察方式/运镜和实际可用或计划使用的素材方向。轻量模式的“台词/声音”必须完整列出全部实际台词、旁白和画外音，没有则明确“无”；完整模式规划预览仍可使用声音短摘要。
- 两种表都只概括故事走向，不写逐秒动作、镜头编号、详细景别/机位、完整运镜参数、详细光线材质、微表情或完整台词。
- 此表是分镜预览表/剧情节奏预览表，不是最终分镜；正式分镜必须在剧本与资产分别确认后生成。

### 确认收尾语义

收尾只固定语义，不固定句子。完整模式视频目标按 `control-contracts.md` 调用项目执行确认；轻量模式直接按 `interaction-ask-video-clarification-ref.md` 调用标准视频生成确认，只有 `generate` 才确认方案并授权当前唯一视频，不再等待第二次确认。其他目标使用普通聊天确认。

首次确认前，用户修改任何一项时仍合并未修改项并重新输出完整开头、参数列表和分镜预览表/剧情节奏预览表，保证存在一个明确的全量基线。规划已有有效全量确认后，局部修改可以只展示变更参数、修改前后、修改日志、受影响集数或阶段及更新后的相关预览行；核心方向、因果链、人物弧、结局、模型、时长、画幅、集数、授权或目标交付终点变化，或实际推翻原方案时属于重大修改，仍须全量确认。完整模式视频目标必须取得 `proceed_project`；轻量模式必须取得 `generate`；其他目标必须收到普通聊天中的明确肯定后才能推进。

## 规划检查

- 用户要求、原台词、必须出现项和禁用项完整记录。
- 所有事实、假设和未知项状态明确。
- 受众和平台结论有用户来源、检索来源或 `assumed` 标记。
- 创意未锁定时已发散恰好 `3` 个主机制候选；用户已锁定创意时没有另造故事方向，只比较必要的执行方案。最终已按用户匹配、核心证明、连续性和生成稳定性选出唯一主机制及 `1-3` 个不冲突的辅助机制，对用户只展示采用方案。
- 参数确认表以固定开头语义开始，并按 `language_contract.output_language` 写作；所有内容均已根据用户指令填写；不含待用户填写的空值、占位符或问题清单。
- `language_contract` 已填写；输出语言、视频语言和字幕语言按当前用户指令主语言或显式语言要求静默写入，并且不出现在参数确认表中。参数确认表必须显示“字幕”项，默认告知不加字幕、片段交付前检查并擦除字幕残留、最终直接拼接无字幕成片；用户明确要求字幕或修改字幕策略时显示对应设置。
- 完整模式参数列表只显示通用规划字段；轻量模式首次生成必须在同一列表中追加任务类型、交付格式、视频数量、分辨率、视觉与连续性、参考素材、工具限制与消耗。正式字段显示名按 `language_contract.output_language` 本地化；参数区不得使用 Markdown 表格。
- 单片使用总时长；多集同时显示集数、逐集时长和总时长，且时长计算一致；所有用户可见单集时长和总时长均按 `60` 秒以内写秒数、超过 `60` 秒写分钟或分秒的规则展示。
- 多集项目附带“集数、标题、核心剧情与动作、台词/声音、钩子与亮点”五个列语义的预览；单集、短片、微电影或长视频附带“时间、核心剧情与动作、台词/声音、运镜衔接、钩子与亮点”五个列语义的预览；正式表头按 `language_contract.output_language` 本地化。
- 预览最多 `8` 行。多集不超过 8 集时每集一行，超过 8 集时合并相邻集并连续覆盖全部集数；单部作品合并相邻时间段并从 0 秒连续覆盖到总时长。
- 参数确认表未出现内部工具、路由、schema、字段、任务 ID、内部路径、检查结果或宿主能力说明。
- 核心卖点、戏剧问题、情绪回报和差异化能够互相支持。
- 类型策略不依赖换皮、巧合或临时设定。
- 风格合同可以直接被分镜和资产读取，没有抽象形容词冒充机制。
- 情绪设计存在压力、策略变化、回报和后果，不是固定比例模板。
- 内容形态、集数、逐集/总时长、比例、生图模型、视频模型、片段和视频生成确认轮次互相兼容。
- 风险项有处理方式，没有靠改名、影射或模糊措辞规避核验。
- 后续六阶段验收项具体、可执行。
- 对话中展示的参数与 `drama_plan.json` 一致；所有模式已建立 `project_manifest.json`、`source_manifest.json` 和全部 `episode_manifest_ep_N.json`，完整模式另已建立 `episode_seams.json` 与共享资产登记。

## 变更与失效

用户修改目标受众、平台、核心卖点、类型、风格、情绪、集数、时长、画幅、模型、授权或禁用项时：

1. `drama_plan.json.revision` 递增。
2. `制作状态.json.phases.planning` 回到 `awaiting_confirmation`。
3. 使用 `scripts/drama_rollback.py --to-stage planning` 或手动等效事务标记受影响的剧本及下游阶段为 `invalidated`。
4. 重新运行规划检查并交付确认。

规划失效时递增 `drama_plan.json.revision` 与 `制作状态.json.revision`，将 `制作状态.json.phases.planning` 写回 `awaiting_confirmation`、`current_stage` 写回 `planning`，并把受影响下游阶段写为 `invalidated`。可用 `scripts/drama_rollback.py` 自动完成状态回退，再根据实际修改更新规划文件。再次确认只提交唯一状态源。

规划确认后，`scriptwriter.md` 必须逐项继承 `handoff.script_must_inherit`、`source_lock`、`creative_proposition`、`opening_strategy`、`type_strategy`、`highlight_strategy`、`style_contract`、`emotion_design`、`scale_plan` 和 `risk_plan`；不得重新选择另一套受众、类型、亮点主轴或风格。
