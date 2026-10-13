📋 详细执行日志
【Phase 1】创建 Campaign
  ├─ 请求: POST /campaign/create/
  ├─ 参数: objective_type={objective_type}, budget_mode={budget_mode}, budget={budget}
  ├─ 响应: code={code}, campaign_id={campaign_id}
  └─ 耗时: {time_ms}ms
【Phase 2】创建 Ad Group
  ├─ 请求: POST /adgroup/create/
  ├─ 参数: optimization_goal={optimization_goal}, billing_event={billing_event}, bid_type={bid_type}
  ├─ 响应: code={code}, adgroup_id={adgroup_id}
  └─ 耗时: {time_ms}ms
【Phase 3】上传素材
  ├─ 视频上传: {video_filename} → video_id={video_id}
  ├─ 封面上传: {image_filename} → image_id={image_id}
  └─ 耗时: {time_ms}s
【Phase 4】创建 Ad
  ├─ 请求: POST /ad/create/
  ├─ 参数: ad_format={ad_format}, ad_text={ad_text}
  ├─ 响应: code={code}, ad_id={ad_id}
  └─ 耗时: {time_ms}ms
【汇总】
  ├─ 总耗时: {total_time_ms}ms
  ├─ 成功步骤: {success_count}/{total_count}
  └─ request_id: {request_id}
