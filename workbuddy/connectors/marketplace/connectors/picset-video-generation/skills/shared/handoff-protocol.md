# 交接协议

主 Skill 与子 Skill 之间只通过 `VideoHandoffContext` 交接视频创作状态。主 Skill 负责创建、读取、合并和透传上下文；子 Skill 只更新自己负责的字段，并返回可继续执行的下一步。

```yaml
VideoHandoffContext:
  active_flow: generate | replica | model
  project:
    project_id:
  product:
    name:
    description:
    verified_facts: []
    uncertain_facts: []
    confirmed_selling_points: []
  requirements:
    country:
    language:
    video_count:
    video_type:
    duration_sec:
    aspect_ratio:
    use_fixed_model:
    replica_requirements: []
  assets:
    - id:
      asset_type: image | video
      asset_role: product_image | target_video | model_image | scene_image
      source: uploaded | generated
      local_path:
      registered_ref:
      confirmed: false
  drafts:
    outline:
      status: 草稿、待选择、待确认、已确认或已失效
      directions: []
      selected_direction_id:
    service_script:
      mode: generate | replica
      visible_script_or_plan:
      duration_sec:
      aspect_ratio:
      status: 无、待确认、已确认或已失效
    credit_confirmation:
      estimated_credits:
      status: 未就绪、待确认、已确认或已失效
    model:
      person_requirements: []
      person_summary:
      estimated_credits: 0
      status: 无、待确认或已确认
  service_state:
    script_id:
    replica_script_id:
    model_task_id:
    model_prompt_id:
    generation_request_ids: []
    generation_task_ids: []
  results:
    - id:
      role: model_image | video
      status: 生成中、成功或失败
      artifact_ref:
```

`project_id` 只在内部保存和透传，用于项目归属、素材登记和生成历史关联，不得展示给用户。脚本或方案生成工具未传 `project_id` 时，由服务端自动创建或恢复真实 `project_id` 并返回，收到后必须保存到 `VideoHandoffContext.project.project_id`；未返回时保存 `script_id` 或 `replica_script_id`。预估或生成前必须具备后端返回的有效 `project_id` 或可让后端恢复项目归属的脚本任务 ID。没有后端返回的 `project_id` 时，使用 `script_id` 或 `replica_script_id` 让后端恢复项目归属。不得传空字符串作为 `project_id`，不得臆造项目归属、不得用脚本任务 ID 冒充 `project_id`、不得用历史项目标识试探。不得对用户解释字段、配置、错误或要求用户提供、修正、查找 `project_id`。

## 用户回复规则

普通用户回复不得展示英文工具名、字段名、内部状态名、接口错误码或原始错误字段；工具名和字段名只可在内部执行或开发文档中使用。不得向用户说明底层上传实现细节、临时凭据、存储路径、内部素材引用或参数字段。向普通用户说明进度时，改用中文动作表达，例如：生成脚本、预估积分、可以上传、我会继续处理素材、素材已准备好、开始生成视频、查询生成进度。

不要说“我先确认某个内部方法在脚本阶段如何引用这张图”这类实现说明；应改说“我先根据这张图整理视频脚本，再给你确认”。

不要解释底层上传、存储、登记和参数传递细节；应改说“可以上传，我会继续处理素材”或“素材已准备好，现在继续生成”。

不得向用户说明内部执行动作、工具准备过程、服务端错误码或自动恢复细节。不说不会扣积分，只说正在预估积分；不说服务端项目错误或重试细节，只说我会继续处理；不说具体素材处理动作，只说素材已准备好。

预估失败时，只说暂时无法完成积分预估；状态说明只使用自然中文，不展示原始字段或状态值。

## 内部交接规则

用户消息不得包含内部任务 ID、`project_id`、`script_id`、`replica_script_id`、`model_task_id`、`model_prompt_id`、`generation_request_ids` 或 `generation_task_ids`；内部任务 ID 不得展示、提供、发送或告知用户。

上下文不保存 STS、OAuth、SK、最终 prompt、最终视频 prompt、最终模特 prompt、原始接口参数、调试信息或完整敏感 URL。需要给用户确认时，只展示可读脚本、复刻方案、预计积分、时长、比例、数量、素材摘要和生成结果。

`asset_role=target_video` 表示用户提供的复刻参考视频；`asset_role=model_image` 表示已生成或已上传并确认的模特图。`asset_role=scene_image` 仅保留为未来扩展，本期不执行或宣称场景图生成。
