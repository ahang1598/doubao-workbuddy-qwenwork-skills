# RecruitmentPacket 一致性与 QA

## 目录

1. 数据包结构
2. 事实一致性
3. 发布状态
4. 面试与排班检查
5. 人工终检

## 1. 数据包结构

机器校验使用 `assets/recruitment-packet.template.json`。每个物料至少包含：

```json
{
  "status": "draft",
  "content_markdown": "物料正文",
  "facts_used": {
    "club.name": "某大学摄影协会",
    "campaign.cta.deadline": "2026-09-12T22:00:00+08:00"
  },
  "structured": {}
}
```

`facts_used` 只记录物料真正使用的关键事实。相同键在多个物料中必须使用相同规范值，并与
`brief_snapshot.fact_values` 一致。自然中文显示可不同，但不得改变时间、地点、费用或含义。

## 2. 事实一致性

逐项检查：

- `club.name`：正式名称和简称的关系已说明；
- `campaign.audiences`：没有某物料擅自扩大或排除对象；
- `campaign.timeline.*`：报名、面试、通知、首次会议日期一致；
- `campaign.location.*`：校区、楼栋、摊位和线上入口一致；
- `campaign.departments.*`：部门名称、职责、名额和要求一致；
- `campaign.cta.*`：主行动、截止、链接/二维码和联系人一致；
- `selection.*`：流程文案、推文和群公告使用同一选拔形式；
- `fees` 和 `time_commitment`：不省略会改变报名决定的重要限制。

发现冲突时记录字段、物料和两个值，不自动选择其一。

## 3. 发布状态

| 状态 | 允许 | 禁止 |
| --- | --- | --- |
| `draft` | 占位符、假设、待确认项 | 暗示已经定稿或已经发布 |
| `review` | 已确认事实和负责人批注 | 未处理的 `conflict` |
| `publish_ready` | 仅已确认或公开核验事实 | 占位符、假设、冲突、无来源强主张 |

运行：

```bash
python3 scripts/validate_packet.py --input recruitment-packet.json
python3 scripts/validate_packet.py --input recruitment-packet.json --strict
```

脚本检查结构、缺失物料、占位符、事实不一致、禁用词和结构化面试题。它不能判断所有含蓄夸大、
实际校方审批或文案质量，仍需人工终检。

## 4. 面试与排班检查

面试：

- `structured.questions[]` 每题有 `competency_id`、`question`、`follow_ups` 和 `anchors`；
- `competency_id` 存在于 Brief 的胜任力表；
- 问题不包含敏感属性、人格标签或与任务无关的个人信息；
- 低分锚点不把“紧张”“内向”“无经验”本身当作失败。

排班：

- `status` 为 `feasible`、`partial` 或 `infeasible`；
- 每个分配都能追溯到成员可用性、技能和上限；
- `partial` 表示至少有一项已分配但仍有缺岗；`infeasible` 表示完全没有可行分配；
- `partial` 或 `infeasible` 必须列出 `unfilled[]`，正文不能写“已全部安排”，且不得进入
  `review` 或 `publish_ready`；
- 外部日历、任务或表格写入必须发生在人工确认之后。

## 5. 人工终检

1. 逐条朗读标题、宣讲稿和摊位话术，删除不自然的营销套话。
2. 用报名者视角确认能找到：做什么、投入多少、怎么报名、何时截止、如何选拔。
3. 用负责人视角确认流程、话术、题库和排班可以直接执行且没有责任空白。
4. 检查二维码或链接的目标与文字一致；Skill 不能通过猜测验证链接有效性。
5. 检查结果通知尊重隐私，不公开名单、分数或比较性评价。
6. 列出所有 handoff，并清楚区分“已生成内容”和“尚未执行外部动作”。
