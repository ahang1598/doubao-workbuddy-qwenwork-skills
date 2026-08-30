# Picset 公共交接协议

## 用途

主路由和业务子 Skill 共享同一份会话事实，用于跨轮次恢复（如生成超时后用户下次对话继续查询）。不得复制、改名或并行维护第二份商品信息、草稿或结果编号。

当前只有一个业务能力（电商套图），本协议主要用于保存跨轮次恢复所需的最小状态。

## HandoffContext

```yaml
HandoffContext:
  active_intent: commerce_image_suite    # 当前业务能力
  product:                               # 商品基本信息，用于恢复草稿
    name:
    selling_points: []
    target_audience:
    scenarios: []
  platform:                              # 平台配置
    name:
    market:
    language:
  output:                                # 输出配置
    main_count: 0
    detail_count: 0
  results:                               # 已生成结果
    - id: M1 | D1                        # 稳定编号
      status: generated | failed
      image_url:
      local_path:
  execution:                             # 进行中的任务，用于恢复轮询
    - task_id:
      image_type: main | detail | aplus
      stable_ids: []
      status: submitted | processing | partial_success | success | failed
  confirmations:                         # 确认状态
    draft_status: drafting | awaiting_confirmation | confirmed
    generation_status: not_ready | awaiting_confirmation | confirmed
    estimated_credits:
```

缺失字段保持为空或空列表，不用推测填满。

## 稳定编号

- 主图使用 `M1...Mn`；详情图使用 `D1...Dn`
- 局部返工、失败重试和跨轮次恢复都保留原编号
- 删除后保留空缺，不重排后续编号；新增图片使用同组下一个从未使用的编号
- 服务返回批内 `index` 时，使用保存的 `stable_ids[index]` 恢复编号

## 子 Skill 返回

业务子 Skill 执行完成后返回以下结构：

```yaml
HandoffReturn:
  handled_intent: commerce_image_suite
  context_updates: {}          # 本次动作更新的上下文字段
  result_updates: []           # 新增或更新的结果项
  pending_actions: []          # 待执行动作（如继续轮询、等待用户确认）
  user_message:                # 面向用户的最终回复内容
```

执行阶段不创建新草稿，只返回本次动作的更新和待办。
