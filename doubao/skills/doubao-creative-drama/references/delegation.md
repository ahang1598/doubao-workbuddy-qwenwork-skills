# 执行委派 Ref

本文件是执行主体、委派边界和交接包的唯一权威。主 Agent 负责导演链路、确认和交付，但必须先读取并遵循本 Skill 与对应 Reference；subagent 只做主 Agent 已锁定执行包中的工具执行任务。

## 本 Ref 关键要求

- 规划、剧本、资产体系、分镜、视频参数确认、继续下一批生成确认、进入拼接确认、Prompt 与请求快照定稿、画布写入、回读、用户交付和最终确认必须由主 Agent 按 Skill 完成；主 Agent 不得按自己的偏好或临时判断覆盖 Skill 策略。
- 凡实际调用视频生成/编辑工具（`text_to_video`、`image_to_video`、`media_to_video`、`video_edit`），必须异步委派给 subagent 执行；主 Agent 不能直接调用这些视频工具。异步只表示相对主对话不阻塞，不改变同一集、同一批次 SEG 的串行依赖。异步委派或结果回传能力不可用时暂停受影响步骤，不得回退为主 Agent 直调。
- 凡成片阶段会产出或修改媒体文件的拼接、裁剪、混音、mux、字幕烧录等媒体变更工具调用，必须委派给 subagent 执行；主 Agent 保留剪辑策略、字幕策略、基础可交付检查、交付和确认责任，不设置最终内容质检硬门。
- 图片生成、修图和关键帧可由主 Agent 执行；若委派，也只能让 subagent 按锁定 Prompt 与白名单路径执行图片工具，不得让 subagent 做创作决策。
- subagent 不能改上游、换模型、改 Prompt、扩写分镜、再次委派、调用澄清/确认工具、写 Canvas/Workspace、调用交付工具或面向用户发问。
- 完整模式资产、关键帧和视频片段阶段的每个图片或视频产物生成后，主 Agent 必须按 `SKILL.md` 与 `cli/README.md` 完成用户交付；非 Mobile 必须完成 `present_files`、Canvas 写入和 CLI get 回读，且一产物一交付一上画布。视频执行 subagent 返回时必须包含工具原始可渲染资源字段、URL 或短链、保存路径和“生成成功、待主 Agent 正式交付”状态。轻量模式字幕关闭时交付原始生成视频；字幕开启时原始无字幕视频只作为内部烧录源。成片阶段的裁剪片、拼接中间件、字幕测试样片和内部母版只保存登记；主 Agent 只交付并写画布字幕策略对应的唯一最终视频版本。

## 执行边界

| 阶段 | 主执行责任 | 委派规则 | 边界 |
|---|---|---|---|
| planning | main_agent | 禁止 | 方向、参数、模式、风险和项目级执行确认由主 Agent 决定 |
| script | main_agent | 禁止 | 项目级与分集剧情不得拆给不同 Agent 创作 |
| assets | main_agent | 图片工具可选委派 | 主 Agent 只建立当前集实际需要且项目内无 approved 可复用版本的人物、场景、道具、音色、风格和状态资产；图片委派只执行锁定 Prompt 与指定输出 |
| storyboard | main_agent | 禁止 | 镜头语言、片段切分和连续性必须保持全局一致 |
| keyframes | main_agent | 图片工具可选委派且最多一个 subagent | 主 Agent 先完成 KF 清单、职责和 Prompt；subagent 只生成指定图片并保存到白名单路径 |
| video | main_agent_director + subagent_executor | 必须委派实际视频工具调用 | 主 Agent 完成生成参数展示、`interaction.ask`、请求快照和最终 Prompt；subagent 只串行调用确认覆盖范围内的视频工具并返回可渲染结果 |
| final | main_agent_director + subagent_executor | 必须委派媒体变更工具调用 | 主 Agent 按 Skill 决定片段顺序、剪切点、声音/字幕策略和基础交付检查；subagent 只执行拼接、裁剪、混音、mux、字幕烧录等锁定媒体操作 |

完整制作必须由主 Agent 按 `current_episode` 逐集闭环，不得把不同集并行推进到不同 subagent。`assigned_episodes` 在生产执行包中只能包含当前集；它不授权 subagent 进入其他阶段，也不授权在当前集成片确认前处理下一集。

## 强制委派与前置条件

遇到以下执行动作时必须委派：

1. 实际提交 `text_to_video`、`image_to_video`、`media_to_video` 或 `video_edit`。
2. 实际执行成片拼接、裁剪、混音、mux、字幕烧录或其他会产出/修改最终媒体文件的 mediakit 等价工具。
3. 主 Agent 明确决定把图片生成、修图或关键帧工具调用外包给 subagent。

强制委派前必须同时满足：

1. 上游阶段和本次所需参数已经由主 Agent 确认或锁定。
2. 视频执行已按 `interaction-ask-video-clarification-ref.md` 完成本次标准视频生成确认；完整模式的成片执行还必须由主 Agent 按 `control-contracts.md` 取得进入成片拼接确认，轻量模式不要求拼接确认。
3. 主 Agent 已保存本次最终 Prompt、请求快照、输入媒体清单、模型、时长、比例、字幕策略和输出白名单。
4. 每个 subagent 能读取完整项目上下文和自己范围内的全部上游文件。
5. 交接包逐文件列明允许新增或覆盖的输出；未列出的文件一律不得写入。

任一前置条件不满足时，必须回到对应上游由主 Agent 补齐或重新确认；不得由主 Agent 绕过委派直接调用视频工具或媒体变更工具。

所有用户可见图片与视频媒体均按 `current_episode` 和集内稳定顺序串行委派。视频必须按 `episode_segment_index` 串行：前一个 SEG 返回、保存、登记、交付、非 Mobile 上画布并抽取下一段所需 FRM 后，才能下发下一个 SEG；不得因判断“没有跨集依赖”而并行。observed SEAM 只能在相邻两段都生成并交付后记录。后续集首段还必须先验收上一集真实尾帧、场景锚点帧、必要角色状态帧和必要道具状态帧，并把对应 `EPSEAMxxx` 更新为 `verified`。

## 交接包

每个 subagent 必须收到一个结构化交接包，至少包含：

```json
{
  "subagent_id": "",
  "scope_stage": "image_execution|keyframes|video_execution|final_media_execution",
  "assigned_episodes": ["ep_1"],
  "skill_name": "doubao-creative-drama",
  "reference_paths": [],
  "upstream_artifacts": [],
  "upstream_revisions": [
    {"path": "01_剧本/剧本_全剧完整剧本.md", "revision": 1}
  ],
  "prepared_request_snapshot_files": [],
  "prepared_prompt_files": [],
  "allowed_output_paths": [],
  "produced_outputs": [],
  "hard_constraints": [],
  "acceptance_criteria": [],
  "allow_redelegation": false,
  "allow_upstream_edits": false,
  "allow_user_delivery": false,
  "allow_canvas_or_workspace_write": false,
  "allow_confirmation_tools": false
}
```

### 通用必备内容

- `skill_name` 必须写当前已加载 Skill 名称 `doubao-creative-drama`；Reference 不写机器绑定路径，由宿主按当前 Skill 包解析。
- `reference_paths` 使用 Skill 内相对路径。图片或关键帧执行至少包含 `references/control-contracts.md`、`references/assets.md`、`references/keyframes.md`、`references/manifests.md`；视频执行至少包含 `references/control-contracts.md`、`references/video-batch-confirmation.md`、`references/interaction-ask-video-clarification-ref.md`、`references/video.md`、`references/storyboard.md`、`references/keyframes.md`、`references/assets.md`、`references/manifests.md`；成片媒体执行至少包含 `references/control-contracts.md`、`references/delivery.md`、`references/manifests.md`。
- `upstream_artifacts` 使用项目内相对路径或宿主可访问的云端资源引用，必须包含本次执行真正依赖的全局剧本包、项目数据卡、共享资产注册表、分集创作说明、分集完整剧本、分镜、已确认 KF、已确认 SEG 或剪辑策略。
- `upstream_revisions` 记录关键上游资源的路径和当前 revision；每次下发前都必须重新核对当前锁定 revision。
- 视频执行必须包含本次确认覆盖的全部预填单次请求快照文件和全部最终 Prompt 文件。subagent 不得自行创建、改写、扩写或压缩请求快照与 Prompt。
- 成片媒体执行必须包含采用片段清单、片段顺序、有效切出/切入点、声音桥、字幕开关、输出版本和允许调用的 mediakit 等价能力；subagent 不得决定剪辑策略或字幕文本，不得做最终内容质检判断。
- `allowed_output_paths` 必须在委派前逐项列出 subagent 可新增或覆盖的项目内相对路径或宿主资源引用，不得只给目录。`produced_outputs` 在收回时填写实际写入文件或资源，必须是 `allowed_output_paths` 的子集。
- `hard_constraints` 必须完整复制主 Skill 的执行约束，至少逐项包含：`只允许执行当前单一执行包`、`不得再次委派`、`不得修改已确认上游`、`不得切换模型`、`不得调用澄清或确认工具`、`不得写 Canvas/Workspace`、`不得直接向用户交付`、`不得重写 Prompt 或请求快照`、`必须读取完整上游文件`、`完成后返回真实输出路径、工具原始可渲染资源和工具结果`。
- `acceptance_criteria` 必须列出当前执行包产物、基础可打开/可播放要求和客观阻断项；不得把审美、口型、连续性、接缝或剧情判断写成阻断交付的最终质检门。
- 五个 `allow_*` 字段必须全部为 `false`。

任一执行者报告输入缺失、版本不一致、schema 不符或约束冲突时，当前批次停止并由主 Agent 修复交接包。不得同时启动多个媒体生成执行者。

## 主 Agent 收口

subagent 返回后，主 Agent 必须：

1. 对照交接包逐项检查实际输出路径、数量、版本和状态；任何未列入 `allowed_output_paths` 的新增或修改文件都视为越权。
2. 检查 subagent 未修改任何上游、Prompt、请求快照、确认记录、Workspace/Canvas 或用户交付记录。
3. 检查串行结果持续使用同一已确认项目事实、资产版本、模型参数、字幕策略和输出命名。
4. 亲自完成可打开、可播放、必要媒体探测和阶段 lint；FRM/SEAM 或内容问题只作为内部记录，不阻断已生成视频或成片交付，也不授权自动重生。
5. 按 `SKILL.md` 的交付路由立即向用户展示产物；非 Mobile 必须由主 Agent 使用当前最终交付版本完成 `present_files`、Canvas 写入和 CLI get 回读。未发生媒体处理时，当前最终交付版本就是 subagent 返回的原始可渲染资源。
6. 继续生成或调整视频时，主 Agent 直接按 `interaction-ask-video-clarification-ref.md` 重新展示完整参数并调用标准视频生成确认；进入成片拼接时按 `control-contracts.md` 调用阶段迁移确认。两者不得互相替代。
