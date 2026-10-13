# 视频阶段 Ref：生成、抽帧与连续性

完整模式在项目级故事包、`current_episode` 详细剧本、资产、分镜和关键帧均已确认后读取本文件；轻量模式在规划页取得视频生成授权、内部完整分镜已经由已确认预览扩充完成时读取。本文件统一负责当前集视频输入、五段式 Prompt 编译、视频工具委派执行和可交付登记；完整模式另执行生成后的 FRM/接缝内部记录，成片拼接、混音和字幕交给 `delivery.md`。当前集达到目标前不得启动下一集工作。

## 第一部分：视频生成与 Prompt 编译

## 权威引用

- 镜头数量、运镜阈值、时间轴和 planned seam：`storyboard.md`。
- 每集唯一导演总控卡及表演、声音、色彩、风格合同：`storyboard.md`。
- 人物、场景、道具、音色和风格的 approved 版本：`assets.md`；KF 的 approved 版本：`keyframes.md`。
- 批次路径、文件命名和 manifest schema：`manifests.md`。
- 生成后 FRM、接缝窗口和内部连续性记录：本文件“第二部分：生成后抽帧与连续性”。
- 失败重试和返回层级：`troubleshooting.md`；成片、字幕与 SRT：`delivery.md`。

## 当前工具链

### 关键帧术语统一

本文件中任何遗留的 `start KF`、`story KF` 或 `tail KF` 表述均不再作为执行要求。关键帧只指 `keyframes.md` 定义的集级剧情高光 KF：并非每个 SEG 都有，不承担首帧或尾帧职责。首段起点由分镜初始状态定义；非首段先读取 planned `SEAM`，`continuous` 必须由上一段真实 `tail FRM` 承接，`elliptical` 则按明确的新时空或新认知起点开始。当前 SEG 命中分镜已规划高光时才传入对应 KF。

当前可执行能力：

| 能力 | 当前用途 | 禁止误用 |
|---|---|---|
| `image_gen` | 无参考图时从纯中文描述生成新资产 | 不登记虚假参考图 |
| `image_edit` | 有参考图时生成或修订资产、KF 或承接候选图 | 不把编辑图冒充原始 FRM |
| `text_to_video` | 当前片段没有任何媒体输入时根据 Prompt 生成视频 | 有必须继承的图片、视频或音频时不得使用；非首段仅限 `elliptical` 且无必要媒体锚点 |
| `image_to_video` | 只有图片输入时生成视频 | 不得携带视频或音频输入 |
| `media_to_video` | 存在视频或音频输入时生成视频，可同时携带图片 | 至少需要真实视频或音频输入 |
| `video_edit` | 根据编辑指令修改已有视频 | 输出比例和时长必须与输入视频一致 |
| `Seed Audio 1.0` | 生成角色与旁白稳定音色 | 音频输入不可用时提供固定文本锚点；支持后必须传入已批准 VOICE |
| mediakit | mediakit 负责抽帧、拼接、ASR、字幕擦除和固定预设字幕烧录 | 不使用 FFmpeg、本地脚本或手工转码冒充正式媒体链路；不改变剧情和镜头职责，不默认替换合格原生人声 |

工具路由只看本次实际输入：零媒体用 `text_to_video`；只有图片用 `image_to_video`；存在视频或音频用 `media_to_video`；修改已有视频用 `video_edit`。`continuous` 非首段因必须传入上一段真实 tail FRM，不属于零媒体路由；`elliptical` 非首段若确实没有任何必要媒体输入，可以使用 `text_to_video`。调用前读取所选工具实际 schema，并在批次中记录工具、字段和输入，不得为偏好某个工具伪造或丢弃媒体。

## 执行顺序

视频批次的用户可见确认内容必须按 `video-batch-confirmation.md` 编译；`interaction-ask-video-clarification-ref.md` 只负责随后 `interaction.ask` 的调用结构与确认有效性。
本文件中任何把“合并参数确认表、数量、逐段时长或本批次五列分镜表”归为本文件或 `interaction-ask-video-clarification-ref.md` 定义内容的旧句均废止；这些展示内容只以 `video-batch-confirmation.md` 为准。
“视频片段批次生成确认”是本文件对“两张批次展示表 + 确认文件中的视频生成确认”的组合简称，不是确认文件中的章节名。

1. 完整模式从 `project_data_card.json`、每集唯一导演总控卡、十五列详细分镜、视频片段执行表、片段衔接卡、连续性账本和已批准 `keyframe_manifest_ep_N.json` 编译 `SEGxxx` Prompt。轻量模式只从已确认规划、内部十五列详细分镜和真实可用的用户素材编译唯一视频 Prompt，不得伪造其他上游文件、资产或 KF 引用。
2. 盘点本次实际媒体输入，按工具路由选择 `text_to_video`、`image_to_video`、`media_to_video` 或 `video_edit`。
3. 为每个 SEG 独立编译一份完整五段式最终提交文本并保存为 `提示词_SEGxxx_vNN_ep_N.md`；同一长视频及同一剧集的各 SEG 必须继承剧情和因果、人物身份、声音系统及 `SEAM.required_invariants`。`continuous` 片段还继承上一段真实尾帧及连续状态；`elliptical` 片段只继承不变量和明确保留项，不复制已被允许改变的旧时空状态。结构化台词和镜头计划只有逐项进入该文件才算真正传给模型。
4. 每份五段式 Prompt 完成后执行一次集中客观预检：五段顺序完整、每个分镜恰好出现一次、时间连续覆盖、输入标记与真实顺序一致、台词逐字一致、动作桥与切点字段齐全、尾态和禁区明确。发现问题最多集中修订一次，再做一次最终客观校验；除合规、授权、真实性、工具能力、缺失输入或客观校验失败等硬阻塞外，校验后直接进入确认与生成。
5. 完整模式先按 `video-batch-confirmation.md` 展示两张表；轻量模式首次生成直接使用规划页已展示的完整参数与预览，返修或重生再使用单视频批次展示。两种模式都只按 `interaction-ask-video-clarification-ref.md` 调用标准视频生成确认，未取得当前 `generate` 时不得派发视频执行。
6. 主 Agent 为本次确认覆盖范围建立锁定执行包，写明最终 Prompt、请求快照、输入媒体、工具 schema、输出白名单和禁止行为，并按 `delegation.md` 委派 subagent 串行执行实际视频工具调用。
7. subagent 只调用执行包指定的视频能力，保存可渲染结果到白名单路径，并返回真实输出路径、工具原始可渲染资源字段、URL 或短链及工具结果，同时标记“生成成功、待主 Agent 正式交付”；不得重写 Prompt、改变输入、追加片段、写画布、交付用户或再次确认。subagent 成功只表示生成完成，不表示用户已收到或 Canvas 已写入。
8. 主 Agent 收回后保存并登记 SEG，更新 `video_manifest_ep_N.json`，确认文件存在且具备可渲染/可播放资源，并按字幕策略清理模型意外生成的字幕、随机文字、水印或平台 UI；不得因为其他内容、审美、口型、身份、连续性或接缝疑似问题延迟交付。用户要求的正式字幕不在片段阶段补齐，只在最终音轨锁定后的成片阶段生成。
9. 完整模式每个 SEG 保存、登记并具备可渲染资源后，主 Agent 立即按 `SKILL.md` 的交付前置路由展示；非 Mobile 完成 `present_files`、Canvas 写入和 CLI get 回读后才能继续下一段。轻量模式没有独立 SEG 交付门：字幕关闭时原始生成结果就是唯一最终视频并立即交付；字幕开启时原始无字幕结果只作为内部烧录源，不展示或上画布，完成字幕烧录后只交付字幕版。
10. 完整模式每个 SEG 交付后只进入一次本文件第二部分，完成必要 FRM 抽取、内部片段记录、接缝窗口记录和 `continuity_ep_N.json` 更新；发现的问题只记录为后续用户主动修改时的返修线索，不阻断已交付视频，也不授权自动重生或编辑。轻量模式只有一个最终视频，不执行分段接缝与连续性文件流程。
11. 下一片段按工具实际 schema 选择：
   - 没有任何媒体输入时使用 `text_to_video`；只有图片输入时使用 `image_to_video`；存在视频或音频输入时使用 `media_to_video`。`continuous` 非首段必须真实传入上一段 tail FRM，因此不得走 `text_to_video`；`elliptical` 非首段按当前新起点的真实需要选择输入。完整模式再传角色身份图、场景图、必要道具/状态图及本段已规划高光 KF，并逐项记录顺序和职责。
   - 先把图片职责分为 `required` 与 `optional`。只有 optional 图片可在超过工具上限时按“角色身份 > 上一段真实尾帧 > 核心道具/状态 > 场景 > 本段已规划高光 KF > 风格”排序裁剪；required 图片数量本身已超上限时禁止调用，必须返回分镜拆 SEG、减少同段主体或重新确认可用工具方案，不能删除必需职责。
12. 完整模式本轮片段均已逐段交付并上画布后，若仍有未生成片段，为下一批重新展示两张表并按视频确认 Ref 取得新的 `generate`；全部片段完成后，`target_stage=final` 按 `control-contracts.md` 调用进入成片拼接确认，`target_stage=video` 则普通确认后结束。轻量模式按字幕策略完成并交付唯一最终视频后，直接进入成片普通确认。

## 批次合同

每个待生成片段必须具备：

- 完整模式必须具备当前 `episode_id`、`project_data_card.json` revision、`episode_manifest_ep_N.json`、`storyboard_ep_N.json`、`source_manifest.json` 中与本集相关的输入记录、`asset_usage_ep_N.json` 与 `keyframe_manifest_ep_N.json`。轻量模式只要求内部十五列详细分镜、当前确认记录和真实存在的用户素材。
- 完整模式当前片段命中的 `highlight_bindings`：逐字继承亮点对应的视觉兑现、表演兑现、声音兑现、余震镜头和编译说明；不得用通用“震撼、电影感、情绪拉满”替代。轻量模式直接从十五列分镜对应镜头提取可见触发、变化、反馈和结果。
- `ep_2` 及以后各集的首个 SEG 必须读取 `00_制作控制/episode_seams.json` 中对应 `EPSEAMxxx`。`continuous` 跨集接缝必须绑定上一集真实尾帧及 SHA-256 并处于 `verified`；`elliptical` 跨集接缝不强制把尾帧作为视觉输入，但必须记录上一集结果、保留的不变量、允许变化、新起点和切换策略。只有整个项目的 `ep_1` 首段使用 `START`。
- 稳定片段 ID `SEGxxx`、绝对时间范围和完整镜头 ID。
- 已确认的十五列详细分镜，其中包含镜头职责、连续性和抽帧承接要求。
- 完整模式必须具备已确认的 `导演总控卡_ep_N.md`、片段执行表和连续性账本，并使当前镜头可追溯到对应表演、声音、色彩、切镜与连续性合同；轻量模式不创建这些文件，直接使用十五列分镜中的对应列。
- 完整模式必须使用已确认的角色、需要建立 SCN 的主要场景、已升级为 PROP 的关键/复现道具、风格和当前 SEG 已规划的高光 KF；所有出场角色必须解析到数据卡身份与当前状态，主要场景和复现道具必须解析到 approved SCN/PROP 版本。一次性物件只写入 Prompt，不要求建立 PROP。轻量模式只引用真实存在的用户素材，不要求补造独立资产或 KF。
- 已确认的视频模型、片段时长和画幅参数。
- 根据本次 `input_image_ids/input_video_ids/input_audio_ids` 选择的 `tool_mode`，且输入组合满足对应工具合同。
- 当前片段已通过 `storyboard.md` 的状态变化、长镜例外、镜头密度和运镜门禁。
- 所有计划人声已完成朗读估时并标注类型。出镜对白要求对应角色真实开口；旁白、画外音和内心独白要求画面人物不开口。字幕默认关闭，只有用户明确要求字幕时才在成片阶段处理；视频模型阶段始终禁止直接生成字幕；不能传音色媒体不等于允许静音。

同一批次只能包含当前集接下来连续的 `1-2` 个 SEG，禁止超过 `2`。同一批次内必须串行执行：前一个 SEG 返回、保存、登记、交付并非 Mobile 上画布回读成功后，才能派发下一个 SEG。

任一项缺失、版本未确认或能力与工具 schema 不符时停止生成，返回对应阶段修复。

## 批次确认展示

合并参数确认表、数量、逐 SEG 时长、五列分镜表、展示顺序与记录要求全部读取 `video-batch-confirmation.md`。本文件不复制其 schema 或模板；任何历史重复版本均无效。

## 模型、时长与画幅

模型、片段时长、画幅、批次上限和例外理由必须直接继承已确认规划与 `storyboard.md`，并在调用前用所选视频工具的实际 schema 复核。本阶段不得重选模型、重算镜头数量或为适配调用擅自改时长。用户未指定视频模型时，所有新视频生成批次固定使用 `seedance 2.0 fast`，每个 SEG 不得超过 `15` 秒。

片段边界必须落在已确认镜头切换点；画幅只进入工具参数，不写进 Prompt。只有参数确认明确记录用户选择 `seedance 2.5（会员模型并且消耗最多的额度）` 时，才能建立 `seedance 2.5` 批次并把单段上限放宽到 `30` 秒。模型能力与已确认计划不兼容时停止调用并返回规划或分镜，不静默换模型、压缩剧情或突破时长上限。

## 入站连续性

场景与画面一致性由五层控制：

1. **项目数据卡**：SCN 锁定空间拓扑、固定陈设和基础光位，状态时间线记录合理变化。
2. **共享场景参考**：每个主要 SCN 使用同一批准布局图，不在各集重新生成。
3. **生成前 KF**：完整模式每集只使用分镜阶段规划并经确认的 `3-4` 张剧情高光 KF；并非每个 SEG 都有 KF，KF 不承担 `start|tail` 首尾帧职责。
4. **生成后 FRM**：上一段生成后提取首帧、场景锚点帧和尾帧，以实际视频作为事实来源，并记录与 KF 的偏差。
5. **下一段承接**：从实际 `tail FRM` 继续角色位置、姿势、朝向、动作相位、道具状态、构图、镜头角度和光位。

### 长视频逐段连续继承算法

对同一长视频、同一集的 `SEG002` 及以后每段执行；跨集首段同时读取 verified `EPSEAM`。目标是把“上一段真实发生了什么”转换成“下一段 0 秒从哪里继续”，而不是复制一句“保持一致”。

1. **读取五类来源**：读取项目数据卡与 approved 资产的稳定身份；上一段已保存视频；上一段 `start|scene|tail FRM` 及观察记录；当前 `SEAM` 的 `seam_mode|required_invariants|permitted_deltas|transition_anchor`；下一段分镜的首态、动作、台词、状态变化和 `reference_input_plan`。`continuous` 缺真实尾帧时停止编译；`elliptical` 不把尾帧设为必需输入，但接缝合同、新起点或必要状态资产缺失时仍返回上游补齐。
2. **建立继承表**：逐项列出剧情因果与已发生动作、角色身份、服装/妆发/伤痕、屏幕位置/朝向/视线/姿势、产品与包装、道具归属/开合/接触、场景拓扑/固定陈设、主光方向/色温、摄影机轴线/运动、声音主体/音色/环境声/BGM，以及未决钩子。每项同时写“上游锁定值、上一段真实尾值、下一段计划值、允许变化、采用值”。
3. **按优先级比较**：身份、授权、用户锁定项和 `required_invariants` 不能被真实生成偏差改写；上一段真实尾帧决定下一段可见起点；`permitted_deltas` 只允许计划内变化；下一段计划负责从真实起点推进到新状态。若真实尾值与计划值只存在可剪切的小偏差，采用真实尾值作为 0 秒基准并在动作过程中回到计划；若偏差改变身份、因果、道具归属、轴线或未允许状态，不伪写一致，记录冲突并返回分镜调整承接。不得自动重生上一段。
4. **选择真实输入**：`continuous` 把上一段 tail FRM 作为 `previous_tail_as_start_frame`；`elliptical` 不强制传 tail FRM，按新起点选择角色身份/状态、SCN、PROP/状态、本段高光 KF 和必要风格图。按工具实际上传顺序重排 `reference_inputs[].order` 和 `<图片N>`；任何本段已声明 required 的输入无法传入时停止，不得用文字假装已继承。
5. **写入五段 Prompt**：第一段写每个输入职责和 0 秒真实基准；第二段写稳定身份、当前状态、场景、光线和声音事实；第三段第一时间窗先写上一段尾态，再写“从该相位继续”的动作路径、反馈和新结果；第四段写当前 SEAM 的入点、段内切点和本段尾态；第五段复写整段不可漂移项与禁区。每一项继承事实只能有一个权威来源，不在不同段落写互相冲突的值。
6. **写回执行记录**：在批次快照和 `video_manifest` 中保存采用的上一段版本、tail FRM、数据卡 revision、状态资产、`reference_inputs` 顺序和继承摘要；生成后再把本段真实 `start|scene|tail FRM` 写入 `continuity_ep_N.json`，供下一段重复同一算法。
7. **检查闭环**：生成前逐项核对继承表中的每个采用值是否进入真实输入或五段 Prompt；生成后比较本段 start FRM 与上一段 tail FRM，并记录 `accepted|rework`。`rework` 只作为用户主动修改时的定位，不阻断即时交付，也不授权自动调用视频工具。
8. **失败回退**：缺真实证据返回抽帧/登记；计划首态与真实尾态不兼容返回分镜改 SEAM；资产版本冲突返回资产阶段；剧情因果冲突返回剧本。不得用“自然衔接”、模糊景别、黑场、强光、声音桥或后期转场掩盖未解决的不变量冲突。

尾帧参考规则：

- `continuous` 非首段必须把上一段真实尾帧和分镜声明为必需的角色、场景、道具/状态图片放入视频工具的真实图片请求字段；`elliptical` 非首段只传新起点所需图片。本段命中已规划高光 KF 时再传对应 KF。缺任一分镜已声明必需的图片时停止调用。
- 使用 `image_edit` 处理尾帧时，原始尾帧和编辑候选分开保存；只有视频工具真正接收该图片时才算“首帧参考输入”。
- 单靠文字承接不能保证像素级一致，批次确认和内部记录必须明确该风险。

## 图片输入合同

| 场景或问题 | 当前路径 | 处理 |
|---|---|---|
| 无任何媒体输入 | `text_to_video` | 只传 Prompt 和生成参数；不得登记图片、视频或音频 ID；非首段仅限 `elliptical` 且无必要媒体锚点 |
| 只有图片输入 | `image_to_video` | 传本段 KF、角色身份图及必要 SCN/PROP/STYLE；`continuous` 非首段补 tail FRM |
| 存在视频或音频输入 | `media_to_video` | 至少传一个真实视频或音频资源；可同时传图片 |
| 修改已有视频 | `video_edit` | 传一个待编辑视频和明确编辑指令；保持原比例与时长 |

路由结果写入批次 JSON：

```json
{
  "episode_id": "ep_1",
  "tool_mode": "image_to_video",
  "model": "seedance 2.0 fast",
  "project_data_card_revision": 1,
  "task_type": "r2v",
  "segments": [{
    "segment_id": "SEG001",
    "episode_segment_index": 1,
    "duration_s": 12,
    "duration_exception_reason": "",
    "planned_shot_count": 10,
    "shot_density_exception_reason": "",
    "camera_variety_exception_reason": "",
    "observable_state_changes": ["发现门锁异常", "抬头确认门后有人"],
    "compiled_prompt_file": "episodes/ep_1/04_视频片段/提示词_SEG001_v01_ep_1.md",
    "shot_plan": [
      {"shot_id": "E01S01-SHOT001", "shot_size": "中景", "camera_position": "角色右侧眼平", "motion_family": "tracking", "motion_path": "与角色平行向门口侧跟", "direction": "画面左向右", "speed": "中速", "focus_start": "角色手中钥匙", "focus_end": "门锁", "stop_point": "钥匙接触门锁时停在近景", "subject_action": "林远走向房门并把钥匙插入锁孔", "state_change": "从谨慎接近变为确认门锁异常", "cut_trigger": "金属接触声"}
    ],
    "incoming_seam": {"seam_id": "START", "previous_segment_id": "", "previous_tail_frame_id": "", "previous_tail_state": {}, "current_start_state": {}, "cut_type": "not_applicable", "seam_mode": "not_applicable", "outgoing_window_frames": 0, "incoming_window_frames": 0, "action_phase": "初始状态", "screen_position_and_direction": "", "camera_angle_and_motion": "", "prop_contact": "", "axis_and_light": "", "sound_bridge": "", "transition_anchor": "起始片段，无前序转场", "required_invariants": [], "permitted_deltas": [], "proof_requirement": "首帧检查", "fallback": ""},
    "incoming_episode_seam": null,
    "speech_mode": "native_required",
    "speech_lines": [{"speaker": "林远", "voice_id": "VOICE001", "voice_anchor": "28岁男性 声音低沉偏冷 平静克制 语速缓慢 字句间有停顿", "type": "on_screen_dialogue", "source_text": "你终于来了。", "display_text": "你终于来了。", "spoken_text": "你终于来了", "delivery_intent": "压低声音确认身份"}, {"speaker": "林远", "voice_id": "VOICE001", "voice_anchor": "28岁男性 声音低沉偏冷 平静克制 语速缓慢 字句间有停顿", "type": "inner_monologue", "source_text": "这扇门不该开着。", "display_text": "这扇门不该开着。", "spoken_text": "这扇门不该开着", "delivery_intent": "警觉"}],
    "subtitle_enabled": false,
    "video_generation_subtitles": false,
    "subtitle_render_stage": "disabled"
  }],
  "reference_basis": [
    {"asset_id": "CHR001", "role": "identity_reference", "passed_to_tool": true},
    {"asset_id": "SCN001", "role": "scene_layout", "passed_to_tool": true},
    {"asset_id": "PROP001", "role": "prop_structure", "passed_to_tool": true},
    {"keyframe_id": "KF001", "role": "segment_highlight_reference", "passed_to_tool": true},
    {"frame_id": "FRM003", "role": "previous_tail_as_start_frame", "passed_to_tool": true}
  ],
  "reference_frame_mode": "actual_image_input",
  "reference_frame_path": "",
  "reference_inputs": [
    {
      "order": 1,
      "source_type": "frame|keyframe|asset",
      "source_id": "FRM003",
      "file": "",
      "role": "previous_tail_as_start_frame|previous_scene_anchor_reference|previous_character_state_reference|previous_prop_state_reference|segment_highlight_reference|identity_reference|character_state_reference|scene_layout|prop_structure|prop_state_reference|style_reference"
    }
  ],
  "audio_input_supported": false,
  "audio_inputs": [],
  "video_inputs": [],
  "voice_inputs": [],
  "ordered_keyframe_control_supported": false,
  "native_audio_supported": true,
  "generation_route": {
    "decision": "new_segment|regenerate_segment|return_upstream",
    "reason": "",
    "continuity_method": "",
    "fallback": ""
  }
}
```

上例的 `shot_plan` 只展示单条字段结构；实际批次中数组长度必须严格等于 `planned_shot_count`，并逐镜填写，不得复制同一推拉模板凑数。

上例是“只有图片输入”的 `image_to_video`。其他模式沿用相同的 SEG、镜头、声音和质量目标结构，但输入字段按工具路由变化：

- `text_to_video`：三类媒体映射均为空。
- `media_to_video`：`video_inputs` 或 `audio_inputs` 至少一个非空，可同时填写 `reference_inputs`。
- `video_edit`：`video_inputs` 仅包含一个待编辑源视频。

批次文件的位置、命名、集号一致性和 manifest 引用只读取 `manifests.md`。

`incoming_episode_seam` 只在 `ep_2` 及以后各集的 `episode_segment_index: 1` 上必填，结构与 `episode_seams.json` 对应记录一致；它不替代集内 `incoming_seam`。后续集首段的集内 `incoming_seam` 仍写 `START/not_applicable`，跨集状态由 `incoming_episode_seam` 单独承载。

当前 SEG 存在批准图片资产时，全部出场角色身份图和分镜声明为必需的场景、道具/状态图必须进入 `reference_basis` 并由视频工具真实接收；当前 SEG 命中已规划高光 KF 时再加入该 KF。不得把多张静态图无差别同时输入，避免模型退化为定格或幻灯片。`continuous` 非首段还必须加入上一段实际 `tail FRM`；`elliptical` 不强制加入。

视频阶段继承图片是强制输入，不是 Prompt 文本引用：人物资产、人物状态、头部锚点、场景资产、场景状态、道具/道具状态、STYLE、关键帧、视频输入图、返修图和上一段 FRM，只要被当前 SEG 的出场角色、当前状态、所在场景、关键道具、已规划高光、返修目标、视频承接或风格合同命中，就必须作为真实图片输入传入 `image_to_video` 或 `media_to_video`。`reference_basis` 与 `reference_inputs` 必须逐项登记实际文件、职责和 `passed_to_tool: true`；只在 Prompt 中写资产 ID、只登记 source_id、只在执行包描述引用但工具请求未带图片，均视为未传入并阻断调用。图片输入超出工具上限时，必须先拆分 SEG、减少同段主体或返回可用工具方案；不得删除已命中的人物身份/状态图、头部锚点、SCN/场景状态、必需 PROP/状态图、KF、返修图或承接 FRM 后继续生成。

使用图片输入时，`reference_inputs` 按真实调用顺序逐张登记。每项必须有连续 `order`、稳定 `source_id`、项目内真实文件和唯一 `role`；至少覆盖分镜声明的必需参考、全部出场角色的 `identity_reference`、命中的 `character_state_reference`/`face_anchor_reference`、当前主要场景的 `scene_layout`/`scene_state_reference`、必需道具的 `prop_structure`/`prop_state_reference`，`continuous` 非首段再增加 `previous_tail_as_start_frame`。本段命中已规划高光 KF 时使用 `segment_highlight_reference`；返修或重生基于已生成/已返修的视频输入图时使用 `repair_reference` 或 `video_input_reference`。图片总数不得超过工具上限。

## 生成质量目标

每个 `SEGxxx` 在提交生成前写入：

```json
{
  "quality_target": {
    "hook": "",
    "evidence_or_clue": "",
    "credible_action": "",
    "visual_payoff": "",
    "closing_beat": ""
  }
}
```

- `hook`：开头用于吸引注意的异常、问题、冲突或承接悬念。
- `evidence_or_clue`：本段必须被看见的证明、线索或关系证据。
- `credible_action`：符合人物动机、空间和物理规律的关键行动。
- `visual_payoff`：本段实际兑现的揭示、反差、动作结果或情绪回报。
- `closing_beat`：明确尾态以及下一段可继承的动作、视线、物件、场景或声音。

五项必须是可观察内容并绑定镜头。调用数量、总生成时长、重试上限及可核实的费用/额度信息进入批次确认；没有可靠价格时明确写“无法准确估价”，不得猜测。

会员模型必须在参数确认时紧跟模型名告知用户：`seedance 2.5（会员模型并且消耗最多的额度）`、`seedream 5.0 pro（会员模型并且消耗最多的额度）`。缺少该提示或用户未确认时，不得调用对应模型。

## 片段内镜头与运镜执行

把分镜按 `SEGxxx` 分组后逐镜编译，禁止摘要式合并。每个时间段按以下顺序写：

```text
承接事实 -> 景别与机位 -> 主运镜 -> 场景/光线/前中后景 -> 主体位置和朝向 -> 动作起点、过程、接触、反馈和结果 -> 信息或关系变化 -> 为什么此时切 -> 承接锚点 -> 后镜开始状态 -> `{}` 中对应类型的原生人声 -> 尾态
```

- 每个镜头独占一个首尾相接的时间区间，总和等于片段时长。
- 每个切点必须写清为什么此时切、用什么承接前一镜、切后增加什么新信息；承接锚点从动作、方向、主体位置、视线、形状、光色、声音、文字、遮挡或产品状态中选择。
- 跨镜动作必须完整覆盖“前镜状态 -> 动作发起 -> 运动路径 -> 合理切点或镜内调度 -> 后镜续接 -> 接触/反馈 -> 结果”，禁止手、人物、产品或道具无路径瞬移。
- 相邻镜头的主运镜、景别、角度或焦点职责至少一项发生叙事性变化。
- 真正一镜到底只能有一个镜头，必须从头到尾同一次连续拍摄，禁止硬切、隐藏切、遮挡伪切、匹配剪辑和时间跳跃；通过连续摄影机路线、主体行动和空间变化形成至少三个可观察节点。
- 场景和角色描述使用稳定名称，不使用“同上”“还是那里”“那个人”等模糊指代。
- 每镜先写景别和机位，再写一个主运镜家族及可执行参数：摄影机路径、方向、速度、焦点起点、焦点终点、停止点和切镜触发。只写“平推、慢推、拉远、电影感运镜”视为未编译。
- 运镜家族只用于内部检查，最终 Prompt 必须改写为纯中文自然导演语言。例如内部 `tracking` 编译为“摄影机在角色右侧保持一米距离，与角色平行向门口中速侧跟”。

## 镜头密度与片段内切镜

镜头密度、运镜家族阈值、例外字段和切镜规则只以 `storyboard.md` 为准。Prompt 阶段不得重新规划镜头数量或修改阈值，只执行已确认 `shot_plan`：

- 保持镜头顺序、绝对时间、主运镜、路径、方向、速度、焦点起落、停止点、动作桥、切镜原因、承接锚点和新增信息完整；每个已确认镜头在 manifest 映射中恰好编译一次。
- 不因生成方便合并计划镜头、截断台词或把多个镜头退化成统一慢推。
- 生成后是否兑现计划镜头和运镜，由 `video.md` 的实际片段内部记录观察；该观察不阻断交付。

## Prompt 强制五段式

五段式是一份视频生成 Prompt 的五层信息合同，不是五个镜头，也不是五个时间段。每个 `text_to_video`、`image_to_video` 或 `media_to_video` 的 Prompt 都必须包含以下五段，顺序固定，不能调整、合并、拆分或省略；实际提交文本由五个空行分隔的自然段组成，不写“第一段”等说明性标题；`video_edit` 改用后文编辑合同。

最终实际提交给模型的完整文本必须原样保存到当前 SEG 的 `compiled_prompt_file`。Prompt 必须从已校验的完整分镜编译，不能临时重新发明镜头、台词或素材关系。分镜中的每个镜头必须在第三段恰好编译一次，不能遗漏、重复或被摘要合并；内部 SHOT ID 只用于 manifest 覆盖校验，不强制写入提交给模型的自然语言文本。

1. **输入资产定位与 0 秒基准**：说明 `<图片1>`、`<视频1>`、`<音频1>` 分别承担什么职责；明确哪张图是真实首帧、参考图或上一 SEG 的真实尾帧。没有真实输入时不得虚构素材编号。`continuous` 后续片段明确上一段真实尾帧是本段 0 秒视觉基准；`elliptical` 后续片段明确转场锚点及允许变化。
2. **参考主体绑定与生成目标**：锁定人物、产品、包装、Logo、场景和已确认的视觉风格；完整模式从唯一导演总控卡继承，轻量模式从已确认规划和十五列分镜继承。写明必须保持的身份、服装、妆发、状态、空间、光线、材质和声音事实；排除无关人物、错误字幕、水印、竞品元素及参考图中不采用的内容，并写清本段生成目标。
3. **逐时间段动作、声音与脚本**：连续覆盖完整时长，按真实镜头和动作阶段展开，不按五段平均切时间。每个时间段写承接的上一状态、主体位置与动作起点、完整动作路径和反馈、景别/机位/角度及一个主运镜、新增信息、台词/BGM/拟音/画面文字，以及切出时的动作或状态。跨镜动作按“前镜状态 -> 动作发起 -> 运动路径 -> 合理切点或镜内调度 -> 后镜续接 -> 接触/反馈 -> 结果”形成动作桥。可听文本写成 `说话人：{原文}`，例如 `旁白：{门已经开了}`；字幕源使用 `【】` 且不得进入视频生成画面；标题、品牌字、时间地点等画面文字使用 `“”`。
4. **转场与尾态收束**：逐切点写“前镜结束状态 -> 为什么此时切 -> 使用什么承接锚点 -> 后镜开始状态”，并写明切后增加的新信息。锚点可来自动作、方向、主体位置、视线、形状、光色、声音、文字、遮挡或产品状态；不得只写“自然转场”“快速切换”。非最终 SEG 留下可被下一段使用的角色、产品、道具、场景、动作和声音状态；最终 SEG 完成动作、声音和人物/产品/品牌落点。
5. **全片一致性与禁区**：复写全片必须保持的人物身份、产品与包装、服装妆发、道具、场景、光线、材质、音色和视觉风格；禁止随机字幕、乱码、水印、额外主体、产品变形、身份漂移、手部异常、闪烁和无来源特效。抽帧是生成后的检查动作，不写成模型要执行的画面内容。

五段职责属于导演编写规则。完整模式由主 Agent 对照已确认分镜和唯一导演总控卡人工复核；轻量模式只对照内部十五列分镜复核。`drama_lint.py` 只检查可客观验证的 Prompt 文件、分镜覆盖、真实媒体标记、台词原文、路径与哈希，不以标题同义词判断创意质量。

画幅是工具参数，不在 Prompt 末尾写比例。没有音频输入时，Prompt 不写 `<音频N>`，只逐字复用 `voice_anchor`；使用已批准 VOICE 时必须路由到 `media_to_video`，并按真实顺序使用 `<音频N>`。

## 人声与文字合同

- 完整模式每个声音主体在 `project_data_card.json.voices[]` 中只有一个当前 `VOICE ID` 和 `voice_anchor`，每条 `speech_lines.voice_anchor` 必须逐字复制数据卡中的该值。轻量模式不创建项目数据卡，所需声音描述直接继承已确认规划和十五列分镜。声音描述至少包含年龄/性别表达、音高与质感、语言/口音、语速、停顿节奏、基准情绪和句尾习惯。
- `audio_input_supported: false` 表示本次没有音频媒体输入，不表示视频应静音。此时每句台词前必须逐字写入 `speech_lines.voice_anchor`，并按其他实际媒体选择 `text_to_video` 或 `image_to_video`。
- 使用已批准 Seed Audio 时必须路由到 `media_to_video`；`audio_inputs` 保存真实资源与文件，`voice_inputs` 映射 `voice_id/resource_id`。已传 VOICE 是音色权威，文字锚点不得与其冲突。
- 有任何人声的片段必须先确认 `native_audio_supported: true`；不支持时停止并返回参数确认，由用户决定是否改模型或接受无声/后配方案，禁止自主换模型。
- 设置 `speech_mode: native_required`，`speech_lines` 的 `type` 只能是 `on_screen_dialogue`、`narration`、`voiceover`、`inner_monologue`；每句同时保存 `voice_id`、`voice_anchor`、原始 `source_text`、带标点 `display_text` 和无标点 `spoken_text`，用 `delivery_intent`、`pause_plan`、`emotion`、`emphasis_words` 表达表演增量。
- 四类人声均由视频模型原生生成并使用 `{完整文本}`；出镜对白驱动指定角色口型，其余三类明确“画面人物不开口”。
- `speech_lines` 中每条 `spoken_text` 必须逐字以 `{spoken_text}` 出现在 `compiled_prompt_file`。只有结构化字段中存在、但实际 Prompt 没有对应花括号台词，按“台词未提交给模型”阻断。
- 出镜对白必须在同一镜头写“角色名真实开口说出{完整文本}”；旁白、画外音和内心独白必须写声音主体、类型、`{完整文本}` 以及“画面人物不开口”。`【】` 是字幕源标识，禁止代替 `{}` 进入实际视频 Prompt。
- 字幕与人声独立：默认最终 `subtitle_enabled: false`，同时视频调用固定 `video_generation_subtitles: false`；只有用户明确要求字幕时，才在成片阶段按 `subtitle_render_stage: final_mediakit_burn` 处理。必须保留全部计划人声，视频画面中禁止模型直接生成逐句字幕。
- 生成后逐句试听；静音、漏句、串角色、类型错误、截断、画外音触发人物张嘴或出镜口型明显错误只记录为内部返修风险和后续用户主动修改时的建议，不自动重生或编辑已返回的可渲染视频。
- Seed Audio 资产始终生成并保持稳定；不传音频时由固定文字锚点保底，传入音频时必须使用 `media_to_video` 并以该资产为准。

## 动态执行硬门

关键帧只定义若干静态状态，不会自动产生动作。实际 Prompt 必须描述状态之间如何变化：

- 每个 SEG 至少填写两个 `observable_state_changes`，例如“发现门锁异常”“对手后退失去主动权”；每项都必须逐字进入 `compiled_prompt_file`。
- 每个镜头除摄影机运动外，还必须填写 `subject_action` 和 `state_change`。只写构图、站姿、表情或“保持一致”，没有动作过程与结果，视为静态镜头。
- `subject_action` 至少包含动作主体、动作过程和可见结果；`state_change` 必须改变位置、姿势、道具状态、人物关系、信息、焦点或情绪中的至少一项。
- 固定机位不等于静止画面。使用固定机位时，人物动作、道具变化、前后景活动、焦点变化或关系变化仍须持续发生。
- 禁止用“人物静止”“保持画面不变”“全程定格”“仅轻微呼吸”填充剧情片段；确属剧情停顿时必须有明确时长和叙事理由，且不能覆盖整个 SEG。
- 多张关键帧不能替代动作描述。Prompt 必须逐镜写出“起点 → 过程 → 反馈 → 结果”，并明确从一张状态过渡到下一状态的动作路径。

## 表演、声音与色彩编译硬门

第三段不是只写动作的镜头清单。完整模式的每个镜头从唯一 `导演总控卡_ep_N.md` 和十五列分镜提取；轻量模式只从十五列分镜提取。按当前模式已有来源写入：

- **表演**：发生原因、表面策略、内在压力、每拍基准态、一个主要可见脸部动作、目光与一个主要肢体动作、呼吸/停顿节奏、说话前后状态、听者反应及双方尾态和禁止的夸张表演。关键表演镜头按已确认表演谱保留时间段变化，并保证下一拍基准态承接上一拍尾态；AU 只有在同时写出可见自然动作时作为辅助校准。无演员镜头明确写“无表演主体”。
- **声音**：基础环境声保持空间连续，叙事性环境声绑定线索或动作，情绪性环境声只在主观化节点使用；BGM 写清进入、增强、抽离和退出；静默写清被移除的声层和恢复触发；跨镜/跨 SEG 声音桥写清前后范围。
- **色彩**：写当前主辅色、色温/对比、主体分离和光源依据，以及人物认知、关系或危险变化触发的色调偏移；继承色彩脚本规定的跨镜关系。不得把“冷蓝=疏离、暖橙=回忆”当成不看剧情的固定字典。

任何一项在本镜无变化时仍写基准状态，不得空缺或用“同上”。同一表演指令不得同时要求互斥反应，例如“强忍不哭”与“泪流满面”；同一声音频段不得让对白、强拟音和 BGM 同时争夺主体。

声音设计在每个时间轴台词前使用固定格式，`{}` 内使用无标点 `spoken_text`，而语气意图继承带标点的 `display_text`：

```text
声音设计：
- 林晓（VOICE001；25岁年轻女性 声音清亮 普通话标准 略带紧张感 语速偏快）：{什么规矩啊姐}
- 陈默（VOICE002；28岁男性 声音低沉偏冷 平静无情绪起伏 语速缓慢 字句间有停顿）：{欢迎回家}
- 旁白（VOICE003；中性偏男性低沉播音腔 语速平稳 略带悬疑感 句尾微降）：{她打开了门}
```

### 文字符号

| 通道 | 强制符号 | 示例 |
|---|---|---|
| 出镜对白、旁白、画外音、内心独白 | `说话人：{原文}` | `旁白：{门已经开了}`，画面人物不开口 |
| BGM | `()` | (低频弦乐缓慢进入) |
| 环境声、拟音 | `<>` | 门锁转动<金属咔哒声> |
| 逐句字幕源文本 | `【】` | 仅用户明确要求字幕时，从已确认 `speech_lines` 派生为【门已经开了】供成片 SRT；可在第五段声明其为后期字幕源，但必须明确视频模型不渲染 |
| 标题、章节、时间地点等画面文字 | 中文双引号 `“”` | 黑屏中央出现“十年前” |

同一内容默认只进入一个声音或画面文字通道。默认无字幕；只有用户明确要求字幕时，才在成片阶段生成无标点 SRT，且它不属于视频模型画面文字；`{}` 中的人声照常生成。只有用户明确要求气泡对话等剧情内文字时，才允许同一句同时作为人声和画面文字。

## 可选叙事过渡

可按剧情选择短黑屏、暗场、环境空镜、物件特写、声音先行或声音延续，承载时间跳跃、章节转换、记忆和内心活动；不是每段必用。黑屏/暗场必须写时长、叙事职责和进入/离开方式，不能替代应拍剧情。时间、地点或章节提示使用 `“画面文字”`，旁白或内心独白使用 `{人声文本}`；默认不生成逐句字幕，只有用户明确要求字幕时才留到成片阶段生成无标点 SRT。

## 不同场景类型的五段式侧重点

所有类型仍使用同一五段式，只调整第三段逐镜时间轴的重点：

| 场景类型 | Prompt 重点 | 注意事项 |
|---|---|---|
| 对话戏 | 建立轴线、视线匹配、说话动作、倾听反应和策略变化 | 不执行“每句台词一镜”；只有说话权、策略或反应发生变化时切镜 |
| 动作戏 | 起势、位移、接触/落空、受力反应和结果，保持屏幕方向 | 复杂动作拆成可验证拍点，不能让一个镜头承担过多并行动作 |
| 情感戏 | 眼神、手部、距离、停顿、呼吸和光线变化 | 微表情不是唯一信息载体；用动作、空间和声音共同表达 |
| 悬疑戏 | 遮挡、POV、失焦/对焦、线索可见性和信息克制 | 公平线索先出现，不用镜头效果直接替代谜底铺垫 |
| 爽点/反转戏 | 压力累积、证据出现、对手反应、权力关系变化和结果停留 | 慢动作、特写或定格只在强化结果时使用，不机械套用 |
| 空镜/转场 | 场景固定锚点、天气、光位、环境变化和声音桥意图 | 有图片锚点用 `image_to_video`，无媒体输入可用 `text_to_video`；无角色不等于无叙事职责 |

## video_edit 编辑合同

只有已经存在待修改视频，且目标是局部视觉或声音编辑而不是重新生成剧情时使用 `video_edit`：

- `video_inputs` 只包含一个真实源视频，并记录资源编号和文件路径。
- 编辑指令写明时间范围、目标对象、需要修改和必须保持不变的内容。
- 输出建立新 `_vNN`，不得覆盖源视频；编辑后重新运行本文件第二部分的片段内部记录和受影响接缝记录。
- 需要增加/删除镜头、改变时长、改变比例、修正剧情因果或重做复杂动作时，不使用 `video_edit`，返回分镜或重新生成 SEG。

## 视频生成失败处理

失败类型、`V/A/F/S/N` 编号、重试预算和返回层级统一读取 `troubleshooting.md`。本阶段只负责保存旧 Prompt、修改变量、预期改善和实际结果；每轮只改变与证据直接相关的变量。

## 生成后交付记录

本阶段唯一执行入口是上文“执行顺序”第 4-9 步。本节只说明交接结果，不再次触发阻断式质检：交给用户确认前，当前 SEG 必须已经保存、登记、具备可渲染资源，并已由主 Agent 完成即时交付；非 Mobile 还必须已写入 Canvas 并回读成功。FRM、接缝和连续性记录可在交付后静默补齐，用于下一段承接或用户主动修改时定位。

## 存储与无歧义命名

路径、命名、视频清单字段和 manifest schema 只读取 `manifests.md`。本阶段必须同时保存实际提交的 `提示词_SEGxxx_vNN_ep_N.md` 及其哈希，并把实际模型、时长、输入资源、输出文件、版本和任务结果写入对应记录，不维护第二套命名规则。

## 输入模态复核

调用前依据 `reference_inputs/video_inputs/audio_inputs` 中的真实文件选择工具路由；输入变化后重新选择工具。

全部片段完成并已逐段交付后，先把每个已生成、已保存、可渲染且已完成即时交付的 SEG 登记为 `status: candidate`，再将视频阶段及目标分集状态写为 `awaiting_confirmation`，然后运行：

```bash
python3 <skill-dir>/scripts/drama_lint.py --project-root "<项目目录>" --stage video
```

`--stage video` 是发起视频阶段确认前的结构检查，允许已完成上述客观条件的 SEG 保持 `candidate`；它不要求在用户确认前提前写成 `accepted`。结构问题只修复记录、路径、状态或缺失文件这类客观缺口；模型意外生成的字幕、随机文字、水印或平台 UI 按既定字幕策略执行非视频生成类清理并验证。其他内容、审美、口型、身份、连续性或接缝问题只做内部记录，不阻断已生成视频交付，不主动说明，也不触发重生。若某段从未预览、返修后未展示，或用户要求回看，再由主 Agent 按交付路由单独补展示对应片段。不得展示批次文件、工具名、路由、Prompt、内部字段、资源 ID、任务 ID、抽帧清单、内部路径或质检统计。

展示完成后按 `control-contracts.md` 调用进入成片拼接确认；普通聊天不能替代。用户选择 `proceed_assembly` 后，把采用的 `candidate` SEG 原子更新为 `accepted`，并同步写入该集 video 确认记录和 `delivery_manifest.assembly_confirmation`。该确认不授权新视频生成或编辑；后续重生、返修或继续生成仍须重新展示完整参数，并按 `interaction-ask-video-clarification-ref.md` 取得新的 `generate`。若目标止于 video，则使用普通阶段确认后结束，不创建拼接确认。

---

## 第二部分：生成后抽帧与连续性

本部分只适用于完整模式的分段视频。轻量模式只有一个最终视频，不创建 FRM、接缝窗口或 `continuity_ep_1.json`，生成结果直接按字幕策略进入最终交付；第一部分步骤 10 的抽帧与连续性流程对轻量模式不适用。

当一个 `SEGxxx` 已由 `text_to_video`、`image_to_video`、`media_to_video` 或 `video_edit` 生成、保存并交付后读取本文件。本文件是 FRM 和 observed SEAM 内部记录的唯一权威，负责从实际视频提取首帧、场景锚点帧和尾帧，为场景连续性、下一片段承接和用户主动修改时定位提供证据。KF 是生成前目标，FRM 是生成后事实；本部分不是阻断交付的最终质检门。

`KF 关键帧目标`负责生成前计划，`FRM` 只记录生成后的实际画面。

### 权威引用

本文件第二部分只适用于完整模式的分段视频。轻量模式不创建 FRM、接缝窗口或 `continuity_ep_1.json`；生成后的唯一视频直接按字幕策略进入最终交付。

- planned seam、镜头计划和资产需求：`storyboard.md`。
- 视频请求、真实输入和 Prompt：`video.md`。
- FRM、双侧帧窗口、实际片段内部记录和 observed seam 由本文件唯一规定。
- 路径、命名和 `continuity_ep_N.json` schema：`manifests.md`。
- 重试预算与缺陷编号：`troubleshooting.md`；成片消费 verified cut：`delivery.md`。

### 抽帧目标

每个已生成片段至少保存：

1. **首帧检查图**：验证片段是否从分镜要求的首状态开始。
2. **场景锚点帧**：从场景结构、固定陈设、角色位置和主光最清楚的稳定时刻提取；每次明显换场或空间关系变化至少一张。
3. **尾帧**：从最后一个稳定、可解码且无转场污染的画面提取，用于记录本段最终角色、道具、场景、构图、光位和动作状态。
4. **接缝窗口**：对每个相邻片段额外抽取上一段末 `12` 帧和下一段首 `12` 帧，生成逐帧序列或接触表，用于寻找真实剪切点。单张 tail/start 只说明状态，不能证明两段连续。

尾帧不等于视频文件最后一个编码帧。片尾若有黑帧、转场、运动模糊或压缩异常，应向前选择最近的稳定帧，并记录实际时间码。

### 工具顺序

1. 优先调用已加载的 `byted-mediakit-video / extract-frames`，并以工具实际 schema 为准。首尾帧使用 `snapshot_type=SpecifiedFrames` 和 `specified_frames=0,-1`；任意时间点使用 `snapshot_type=SpecifiedTime` 和 `specified_time`。
2. `extract-frames` 是异步能力：保存提交返回的真实 `task_id`，用 `byted-mediakit-shared / query-task` 查询到 `completed`，再及时下载 24 小时有效的 `result.snapshots[].image_url`。`running|queued` 时使用同一 `task_id` 继续查询。
3. mediakit 没有对应能力或接缝窗口需要当前合同不支持的逐帧精确控制时，停止依赖步骤并记录能力缺口；不得使用 FFmpeg、本地脚本或手工命令冒充正式抽帧、探测或接缝窗口。
4. 抽取后必须实际查看。帧模糊、黑屏、遮挡严重或处于转场中时，调整时间码重新抽取。
5. 不使用 `image_edit` 美化原始抽帧后冒充视频真实状态。确需制作“下一段首帧候选”时必须另存为编辑版本，并与原始尾帧同时保留。

接缝窗口按实际帧率抽取，不把 `12` 帧误写成固定秒数。实际使用时先用 mediakit 探测取得帧率和精确时间基；输出帧数不足或能力不支持时阻断并返回成片/接缝处理，不得降级到本地命令。

### 场景一致性记录

场景一致性由“共享 SCN 布局参考 + 数据卡状态 + 分镜文字合同 + 实际视频抽帧 + 下一段承接 Prompt + 成片复看”共同维持。

每张场景锚点帧记录：

- 场景 ID/名称、所属 `SEGxxx`、时间码和文件路径。
- 空间拓扑：入口、出口、墙面、窗户、家具及固定物相对位置。
- 摄影机：高度、方向、景别、焦段感、轴线侧和主体屏幕位置。
- 光线：主光来源、方向、色温、曝光、阴影方向和环境色。
- 角色：身份版本、位置、朝向、视线、姿态和动作相位。
- 道具：`PROPxxx` 状态版本、持有者、可见面、方向和接触点。
- 下一片段必须继承项与允许变化项。

下一片段 Prompt 必须从该记录复制具体事实，不得只写“保持上一段一致”。

### 尾帧承接

下一片段生成前按 `video.md` 根据真实输入选择视频工具：

- `continuous` 接缝在工具支持图片输入时，把上一片段已保存 tail FRM、全部出场角色身份图和分镜声明为必需的场景、道具/状态图作为实际图片输入；`elliptical` 接缝从新起点所需资产开始，不强制传上一段 tail FRM。本段命中已规划高光 KF 时再传对应 KF，并记录资源 ID、文件路径、顺序和职责。
- Prompt 中使用对应 `<图片N>` 标签，明确每张图采用什么、不采用什么；`continuous` 声明 0 秒承接上一段结尾，`elliptical` 声明通过已确认转场锚点进入新状态、只变化 `permitted_deltas`，两者都逐项保留 `required_invariants`。
- 若需要只推进一拍，可用 `image_edit` 基于原始尾帧制作“下一段首帧候选”，但必须保留原始尾帧并记录编辑范围。
- 若 `continuous` 接缝所选工具不支持所需图片输入，停止并说明能力缺口；返回分镜调整分段或由用户重新选择可接收图片的工具方案，不得静默改成文字降级。`elliptical` 接缝按实际输入正常路由。

### 接缝窗口内部记录

每个 `SEAMxxx` 在两个片段都生成并已交付后记录；它不要求用户逐 SEG 确认，也不阻断已生成视频展示。记录结果只用于下一段承接、成片 best available cut 和用户主动修改时定位，不授权自动重生或编辑：

1. 并排查看上一片段末 `12` 帧和下一片段首 `12` 帧，并以 `0.25x` 慢放跨接缝。
2. 标记候选切出帧和切入帧，不默认采用文件最后一帧与第一帧。
3. 先核验 `required_invariants`，再逐项确认变化是否只发生在 `permitted_deltas` 中：角色屏幕位置/朝向/视线、动作相位、运动方向与速度、摄影机运动、道具接触、轴线、光位和环境声不能一律假定为必须连续。
4. `continuous`：连续动作只允许同相位或略微推进，禁止动作完成后回到起势、手部脱离后重新接触、人物跨屏瞬移；未列为不变量的维度也不得无理由变化。
5. `elliptical`：允许计划中的时间、空间、构图、光线、人物/道具状态或声音变化，但必须由 `transition_anchor` 可见地连接，且不得改变未列入 `permitted_deltas` 的事实。按主转场核验：动作匹配检查相位、方向和速度；遮挡切检查遮挡物方向、面积和解除时机；相似构图检查形状、主体位置、视觉重心或色块关系；甩镜检查同向运动、模糊强度和入画落点；视线/物件匹配检查目标或接触关系。
6. 声音桥只能服务已批准的切法，不能掩盖未允许的身份、动作相位或光位错误。

将结果写入：

```text
episodes/ep_N/04_视频片段/质检/质检_接缝_SEAMxxx_SEGxxx_SEGyyy_vNN_ep_N.md
```

至少记录：`SEAM ID`、`上一片段`、`下一片段`、`主转场`、`衔接模式`、`转场锚点`、`不变量`、`允许变化`、`尾部窗口`、`头部窗口`、`候选切点`、`最终切点`、`动作相位`、`屏幕位置与运动方向`、`摄影机运动`、`道具接触`、`轴线与光位`、`声音桥`、`结论`、`修复动作`。

### 命名与存储

抽帧属于视频阶段派生证据，不进入共享或分集资产目录。目录、文件名和 `continuity_ep_N.json` schema 只读取 `manifests.md`；本文件只规定帧的选择、观察、比较和内部记录。`FRMxxx` 保持全项目唯一，时间码来自源视频，重抽时建立新版本。

### 抽帧连续性清单

`episodes/ep_N/04_视频片段/continuity_ep_N.json` 是抽帧和集内 SEAM 的机器权威，结构读取 `manifests.md`。`episodes/ep_N/04_视频片段/抽帧/抽帧_连续性清单_ep_N.md` 至少包含：

| 帧 ID | 来源片段 | 职责 | 对应 KF | 时间码 | 文件路径 | 场景结构 | 角色状态 | 道具状态 | 光位 | 动作相位 | KF 偏差 | 下一段用途 | 实际传图 | 版本 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FRM003 | SEG001 | tail | KF002 | 00:00:11.800 |  |  |  |  |  |  | accepted/rework | SEG002 承接 | yes/no | v01 |

每个 `start FRM` 对照分镜起始状态；`continuous` 非首段同时对照上一段真实 tail FRM，`elliptical` 非首段对照接缝声明的新起点和保留不变量。`scene/tail FRM` 在当前时间点存在已规划高光 KF 时可绑定该 KF，否则对照分镜状态和数据卡。偏差不等于失败；角色身份、道具因果、场景方向、动作相位或接缝职责变化时，只记录为用户主动修改时的返修定位，不阻断当前视频交付。

### 相邻片段首尾并排记录

生成并交付 `SEG002` 及之后每个片段后，`continuous` 接缝把上一段实际 `tail FRM` 与本段实际 `start FRM` 并排查看；`elliptical` 接缝检查上一段结果、新起点、保留不变量和允许变化。两者都与衔接卡、分镜起始状态和项目数据卡核对；本段起始时间点恰好对应已规划高光 KF 时再一并参考该 KF：

| 检查维度 | 通过标准 |
|---|---|
| 人物身份与状态 | `required_invariants` 中的身份一致；状态变化仅可发生在 `permitted_deltas`，且数据卡有有效原因 |
| 人物位置与姿势 | `continuous` 时位置、身体朝向、视线和动作相位连续；`elliptical` 时按锚点与允许变化核验，无计划外跳变 |
| 镜头与轴线 | 景别、机位高度、观察方向、轴线侧和摄影机运动符合预定切法与不变量 |
| 场景与光线 | 仅要求规定不变量连续；允许的 SCN、时间天气、主光方向和色温变化必须符合转场锚点 |
| 道具 | 未列为允许变化的归属、可见面、开合/破损状态和手部接触连续 |
| 声音 | 对白尾音、环境声、拟音或 BGM 的桥接点符合衔接卡；声音变化必须在允许项中 |

逐项结果写入 `continuity_ep_N.json.seams[].comparison`。任一身份、位置、姿势、镜头角度、场景布局或关键道具项为 `rework` 时，只记录责任范围和建议；当前片段仍按 best available cut 进入用户可见交付链路，只有用户主动要求修改并重新确认后，才可重生成当前片段或返回对应上游修订。

### 片段与接缝内部记录

- **单片段内部记录**：每个 SEG 生成并交付后抽取 `start / scene（中间代表帧）/ tail`，记录角色面部与 CHR、当前状态与数据卡、道具与 PROP、场景与 SCN、KF 偏差、声音主体与固定 `voice_anchor`。发现问题只写入内部返修线索，不阻断交付。
- **全片衔接内部记录**：本集所有 SEG 生成并交付后，覆盖全部 `N-1` 个边界，逐一并排比较前段 tail FRM 与后段 start FRM。不得抽样跳过接缝；发现问题只记录责任片段，用户主动要求修改前不调用视频工具。
- 最终成片只按 `delivery.md` 做基础可交付检查并立即交付。

逐 `SEGxxx` 的内部记录至少覆盖：

| 维度 | 记录内容 | 记录触发 |
|---|---|---|
| 剧情完整性 | 片段职责、冲突、线索、回报或收束是否实际出现 | 核心职责缺失 |
| 角色可信度 | 动作符合动机，表情和反应自然，身份稳定 | 身份或关键反应错误 |
| 连贯性 | 内部镜头和相邻片段的场景、位置、动作、道具、光位可剪 | 无法找到有效接点 |
| 情绪传达 | 目标情绪由表演谱中的可见脸部/目光/肢体/声音变化、空间、镜头和节奏共同兑现 | 情绪反向、关键反应缺失或只有抽象情绪词 |
| 视觉质量 | 清晰度、构图、色彩、光影和人体/生物结构 | 影响叙事或身份识别 |
| 镜头执行 | 计划镜头、切点和运镜实际可辨 | 关键镜头遗漏或错误 |
| 声音执行 | 原生人声完整，主体、类型、文本、声线和口型职责正确 | 静音、漏句、错人或职责错误 |

每个生成版本保存结构化结论：

```json
{
  "segment_id": "SEG001",
  "version": "v01",
  "status": "candidate|accepted|rejected|blocked",
  "defect_codes": [],
  "checks": {
    "narrative_fidelity": "",
    "identity_and_asset_match": "",
    "anatomy_and_proportion": "",
    "physics_and_action": "",
    "continuity_and_editability": "",
    "dialog_voice_lipsync": "",
    "shot_execution_and_camera_variety": "",
    "actual_camera_family_counts": {},
    "seam_window_review": "",
    "text_and_artifacts": ""
  },
  "first_audience_rejecting_defect": "",
  "repair_scope": "",
  "next_action": "deliver|record_for_user_requested_revision|not_applicable",
  "target_stage": "planning|script|assets|storyboard|keyframes|video|final|not_applicable"
}
```

内部记录文件还要记录画面可播放、计划/实际运镜家族统计、抽帧 ID、KF/FRM 偏差、原生人声时间范围、口型观察、字幕状态和 `defect_codes`。不使用简单总分掩盖问题；但任何重试、返修或重新调用视频工具都必须等待用户主动要求并重新按确认 ref 完成确认。

`实际传图` 只有在视频工具请求中确实存在对应图片输入时才能写 `yes`；纯文字继承必须写 `no`。

### 检查

- 抽帧来自当前采用的视频版本，时间码可追溯。
- 首帧、场景锚点帧和尾帧都已实际查看，不是黑帧、模糊帧或转场污染帧。
- 场景拓扑、固定陈设、光位、角色位置和道具状态已写成可执行事实。
- 下一片段 Prompt 明确继承哪些事实、从哪一个动作相位继续。
- `image_to_video` 的 `reference_inputs` 与 Prompt `<图片N>` 顺序一致，且全部是真实文件。
- 原始抽帧与任何 `image_edit` 编辑候选分开命名、分开保存。
- 每个相邻 SEG 均有接缝窗口内部记录；最终切点来自真实帧窗口或 best available cut，不是默认文件边界。
