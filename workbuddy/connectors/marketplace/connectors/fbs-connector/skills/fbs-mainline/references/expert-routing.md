# 2026.9.10 当前 13 项专家稳定身份映射

本表保存当前已实现的稳定包身份与明确服务合同映射，不保存专家版本。部署后以服务当前 registry 和 whoami 回读核对；空值不得由模型猜补，表中静态登记不证明宿主已加载或自然使用。

| 专家产品 | `productId` / `packageName` | `serviceProductId` | 已确认入口/字段 | 当前连接器状态 |
| --- | --- | --- | --- | --- |
| AIGC 合规红队 | `fbsir-aigc-compliance-red-team` | 未确认 | 有值时透传 `entryId`、`entrySurface`、`intentFamily`、`assetType` | `registered_no_route`；待当前 schema/registry |
| 备课易 | `fbsir-beike-yi` | 未确认 | 无服务入口字段被本次研究确认 | `registered_no_route`；保持本地首值 |
| 独董会 | `fbsir-eight-seat-board` | `fbsir-eight-seat-board`（26.8.20 已声明） | `expertEntryId=board-convener`、`channelTrack=official_experts` | 待 current registry/宿主回读，不由本地 eventId 晋级 |
| 行业场景研究员 | `fbsir-industry-scene-researcher` | `workbuddy_industry_scene_researcher` | `entryId=genius-industry-scene-researcher`、`intentFamily=genius_partner`；其他字段只在实际入口确认且 schema 接受时发送 | 当前稳定合同采用已命名ID；历史空值记录不回填，调用仍核对服务路由 |
| 实习生 | `fbsir-internship` | 未确认 | 本地交付日志不是服务遥测 | `registered_no_route`；不补发历史事件 |
| 妈妈对话 | `fbsir-mom-dialogue-expert` | 未确认 | 家庭作品和媒体字段不进入归因参数 | `registered_no_route`；保持本地优先 |
| 超级独董 | `fbsir-super-independent-board` | 未确认 | 未确认更多字段时只透传稳定包身份 | `registered_no_route` 或服务实际返回为准 |
| 超级伙伴 | `fbsir-super-partner` | `workbuddy_super_partner_expert` | 当前单专家ID；历史 `workbuddy_super_partner_group` 保持独立，不自动映射为当前专家 | 当前合同已区分单专家与历史专家团；返回不一致仍停止归因写 |
| 产业园招商 | `industrial-park-investment-attraction-expert` | 未确认 | 本地研究摘要不是企业意向；CRM 交接需独立授权 | `registered_no_route` |
| 留学研学 | `liuxue-yanxue-expert` | `workbuddy_liuxue_yanxue_expert`（26.8.20 已声明） | `expertEntryId=liuxue-yanxue-expert`、`channelTrack=study_abroad_study_tour`、`entryId=liuxue-yanxue-dual-track`、`entryPromptCode=wb_qp_liuxue_yanxue_dual_track_48h`、`entrySurface=workbuddy_expert_center`、`scenePackId=liuxue_yanxue_dual_track` | 首批联调；字段仍服从当前 `tools/list` |
| 长文档专家 | `long-manuscript-expert` | `workbuddy_long_manuscript_expert`（26.8.20 已声明） | `expertEntryId=long-manuscript-expert`、`channelTrack=long_manuscript_expert` | 首批 provider binding 联调；保留已有项目 |
| 秘宝媒体归档 | `mibao-media-archivist` | 未确认 | 只在另行授权增强时传最小引用；不传媒体路径或原件 | `registered_no_route`；本地媒体内核优先 |
| 贴图头条 | `tietu-toutiao` | 未确认 | 作品计划/候选/集合摘要属于本地工作流；企微 webhook 独立 | `registered_no_route`；投递不算 FBS 消费 |

## 使用规则

- `productId` 与 `packageName` 均使用表中稳定包 ID；只在工具 schema 支持且宿主确认当前专家时传入。
- 不把 `my_expert` 等通用入口名当成具体产品身份。
- 服务端返回的规范化身份是当前调用结果；若其与输入不同，按未知/降级处理并停止依赖归因的写操作。
- 映射只服务于内部工具参数。用户可见回复使用中文产品名，不展示这些机器字段。
- `registered_no_route` 是服务的登记/路由状态。静态登记、已选业务路由与宿主真实执行分别验证；服务未返回可用下一步时不自动调用增强。
- 本次 13 项研究范围不改写服务端历史 registry 或旧回执；不在表内的历史专家身份仍由对应版本服务合同验证。
