# RecruitmentBrief 输入契约

## 目录

1. 顶层结构
2. 字段定义
3. 输出分支最小输入
4. 事实状态
5. 校验与缺失处理

## 1. 顶层结构

使用 UTF-8 JSON。复制 `assets/recruitment-brief.template.json` 后填写，不删除未知字段的语义；
未知值使用空字符串、空数组、`null` 或事实占位符，不能猜测。

```json
{
  "schema_version": "1.0",
  "packet_status": "draft",
  "club": {},
  "campaign": {},
  "message": {},
  "selection": {},
  "staffing": {},
  "outputs": [],
  "output_options": {},
  "facts": [],
  "notes": []
}
```

`packet_status` 只允许：

- `draft`：允许假设和占位符；
- `review`：关键事实已齐，等待负责人确认；
- `publish_ready`：没有关键占位符、假设、冲突或无证据强主张。

## 2. 字段定义

### `club`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `name` | string | 社团正式名称；所有任务必需 |
| `school`、`campus` | string | 只有需要校内定位或官方核验时必填 |
| `type` | string | 学术、文艺、体育、公益、实践等，仅作内容定位 |
| `mission` | string | 社团存在目的，不写空泛口号 |
| `activities` | string[] | 有事实支持的典型活动 |
| `newcomer_development` | string[] | 真实存在的培训、实践或成长机制 |

### `campaign`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `goal` | string | 本次招新目标和成功条件 |
| `audiences` | string[] | 2-4 类目标新人，不能按敏感属性排除 |
| `target_count` | integer/null | 计划人数；未知时保留 `null` |
| `departments` | object[] | `id`、`name`、`openings`、`description`、`requirements` |
| `timeline` | object[] | `id`、`label`、`start`、`end`、`location`、`owner` |
| `channels` | string[] | 公众号、校内群、线下摊位等 |
| `cta` | object | `action`、`deadline`、`link_or_placeholder`、`contact` |

日期时间优先使用带时区的 ISO 8601；只显示日期时使用 `YYYY-MM-DD`。面向用户的正文可以转为
自然中文，但所有物料必须来自同一个结构化值。

### `message`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `core_values` | string[] | 最多 3 个有事实支持的新人价值 |
| `evidence` | string[] | 活动、作品、培养机制或可观察成果 |
| `tone` | string[] | 例如真诚、清晰、活泼但不过度夸张 |
| `slogan` | string | 主口号；未定可留空 |
| `forbidden_claims` | string[] | 明确不能出现的词句或主张 |

### `selection`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `format` | string | `open_enrollment`、`interview`、`audition`、`portfolio`、`written_test`、`mixed` |
| `competencies` | object[] | `id`、`name`、`definition`、`weight`；权重建议合计为 1 |
| `duration_minutes` | integer/null | 单人或单组时长 |
| `interviewer_count` | integer/null | 面试官人数 |
| `score_scale` | integer | 推荐 5 |

### `staffing`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `defaults.max_shifts_per_person` | integer | 默认最大班次数 |
| `defaults.max_consecutive_shifts` | integer | 默认最大连续班次数 |
| `members` | object[] | 成员身份、技能、可用班次和个人上限 |
| `shifts` | object[] | 班次日期时间、岗位、最低人数和技能要求 |

成员对象：

```json
{
  "id": "m01",
  "display_name": "成员甲",
  "skills": ["摄影"],
  "available_shift_ids": ["s01"],
  "preferred_shift_ids": ["s01"],
  "max_shifts": 2,
  "max_consecutive_shifts": 1
}
```

班次对象：

```json
{
  "id": "s01",
  "label": "首日早班",
  "date": "2026-09-05",
  "start": "09:00",
  "end": "11:00",
  "location": "[待确认：摊位位置]",
  "roles": [
    {
      "name": "讲解",
      "min_count": 2,
      "required_skills": [],
      "preferred_skills": ["宣讲"]
    }
  ]
}
```

### `outputs` 与 `output_options`

`outputs` 只允许：`recruitment_flow`、`poster_copy`、`wechat_article`、`speech`、
`interview_kit`、`group_notices`、`booth_script`、`shift_roster`。

模板必须保持 `outputs: []`。仅把用户明确选择的分支加入数组；不得因模板存在章节而默认加入
八项，也不得在用户只要海报、推文或流程时加入 `interview_kit`。`selection.format` 未知时保留
`[待确认：选拔形式]`；仅当用户明确要求选拔材料时填写 `interview`、`audition`、
`portfolio`、`written_test`、`mixed` 或 `open_enrollment`。

`output_options` 保存用户指定的长度或版本，例如：

```json
{
  "speech_minutes": 5,
  "wechat_target_chars": 1600,
  "poster_versions": 3,
  "notice_scenarios": ["welcome", "interview_reminder", "deadline"]
}
```

## 3. 输出分支最小输入

| 输出 | 除 `club.name` 和 `outputs` 外的最小输入 |
| --- | --- |
| `recruitment_flow` | `campaign.goal`、`campaign.audiences`、至少一个时间节点 |
| `poster_copy` | `campaign.audiences`、`message.core_values`、`campaign.cta.action` |
| `wechat_article` | `campaign.audiences`、`message.core_values`、`campaign.cta.action` |
| `speech` | `campaign.audiences`、`message.core_values`、`campaign.cta.action` |
| `interview_kit` | `selection.format`、至少一个 `selection.competencies` |
| `group_notices` | 至少一个时间节点或 `notice_scenarios` |
| `booth_script` | `campaign.audiences`、`message.core_values`、`campaign.cta.action` |
| `shift_roster` | 至少一个成员、一个班次和一个岗位 |

缺少最小输入时不要生成看似完整的正式稿。可以补问一个主问题，或保留明确占位符并输出 `draft`。

## 4. 事实状态

`facts[]` 每项使用：

```json
{
  "field": "campaign.cta.deadline",
  "value": "2026-09-12T22:00:00+08:00",
  "status": "confirmed_by_user",
  "critical": true,
  "source": "用户在本轮确认"
}
```

允许状态：`confirmed_by_user`、`verified_public`、`assumption`、`placeholder`、`conflict`。
`verified_public` 的 `source` 应包含来源标题、URL 和访问日期。`publish_ready` 中不得存在
`assumption`、`placeholder`、`conflict`；关键事实必须出现在 `facts[]`。

`review` 和 `publish_ready` 至少记录 `club.name`。包含公开宣传物料时，还要记录
`campaign.cta.action`；已填写截止时间或入口时，分别记录 `campaign.cta.deadline` 和
`campaign.cta.link_or_placeholder`。事实记录的值必须与 Brief 对应字段完全一致。

## 5. 校验与缺失处理

运行：

```bash
python3 scripts/validate_brief.py --input recruitment-brief.json
python3 scripts/validate_brief.py --input recruitment-brief.json --strict
```

第一条允许 `draft` 警告；`--strict` 把未确认关键事实和输出分支缺口视为错误，用于定稿前检查。
脚本只校验结构、状态和分支必填项，不联网、不猜同义词、不生成文案。
