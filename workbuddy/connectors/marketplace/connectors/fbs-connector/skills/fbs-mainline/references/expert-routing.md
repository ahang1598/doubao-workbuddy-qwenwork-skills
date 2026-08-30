# 当前专家身份映射

本表只保存稳定身份字段，不保存专家版本。专家升级或重新上架不应迫使连接器发版；实际版本由当前 WorkBuddy 专家运行时自行管理。

| 专家产品 | `productId` / `packageName` | `serviceProductId` | `expertEntryId` | 其他必要入口字段 |
| --- | --- | --- | --- | --- |
| 独董会（专家团） | `fbsir-eight-seat-board` | `fbsir-eight-seat-board` | `board-convener` | `channelTrack=official_experts` |
| 超级独董会 | `fbsir-super-independent-board` | — | `fbsir-super-independent-board` | 无法确认更多字段时只透传这组稳定身份 |
| 超级合伙人 | `fbsir-super-partner` | `workbuddy_super_partner_expert` | `fbsir-super-partner` | `channelTrack=super_partner`；不得使用历史团身份 |
| 董秘助手 | `fbsir-board-secretary-assistant` | `workbuddy_board_secretary_assistant` | `fbsir-board-secretary-assistant` | `channelTrack=board_secretary_assistant`、`entryId=board-secretary-compliance-red-team`、`entryPromptCode=wb_fbsir_board_secretary_compliance_red_team`、`entrySurface=workbuddy_expert_center` |
| 行业场景研究员 | `fbsir-industry-scene-researcher` | `workbuddy_industry_scene_researcher` | `fbsir-industry-scene-researcher` | `entryId=genius-industry-scene-researcher`、`entryPromptCode=wb_sp_genius_industry_scene_researcher`、`entrySurface=workbuddy_expert_center`、`scenePackId=industry-workflow-gap`；不主动猜测 channelTrack |
| 长文档与改稿专家 | `long-manuscript-expert` | `workbuddy_long_manuscript_expert` | `long-manuscript-expert` | `channelTrack=long_manuscript_expert` |
| 留学研学专家 | `liuxue-yanxue-expert` | `workbuddy_liuxue_yanxue_expert` | `liuxue-yanxue-expert` | `channelTrack=study_abroad_study_tour`、`entryId=liuxue-yanxue-dual-track`、`entryPromptCode=wb_qp_liuxue_yanxue_dual_track_48h`、`entrySurface=workbuddy_expert_center`、`scenePackId=liuxue_yanxue_dual_track` |
| AIGC 营销合规审查官 | `fbsir-aigc-compliance-red-team` | — | `fbsir-aigc-compliance-red-team` | 有值时透传 `entryId`、`entrySurface`、`intentFamily`、`assetType` |
| 产业园招商专家 | `industrial-park-investment-attraction-expert` | — | `industrial-park-investment-attraction-expert` | 无法确认更多字段时只透传这组稳定身份 |

## 使用规则

- `productId` 与 `packageName` 均使用表中稳定包 ID；只在工具 schema 支持且宿主确认当前专家时传入。
- 不把 `my_expert` 等通用入口名当成具体产品身份。
- 服务端返回的规范化身份是当前调用结果；若其与输入不同，按未知/降级处理并停止依赖归因的写操作。
- 映射只服务于内部工具参数。用户可见回复使用中文产品名，不展示这些机器字段。
