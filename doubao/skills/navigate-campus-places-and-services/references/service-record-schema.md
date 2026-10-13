# 办事记录与证据状态

## ServiceRecord

```json
{
  "mode": "service_guide",
  "institution": {"name": "", "campus": "", "official_domain": ""},
  "service_name": "",
  "audience": [],
  "channel": "online|offline|both|unknown",
  "online_entry": "",
  "responsible_unit": "",
  "materials": [],
  "steps": [],
  "time": {"office_hours": "", "deadline": "", "processing_time": ""},
  "fees": "",
  "location": {"campus": "", "building": "", "floor_room": "", "entrance_landmark": ""},
  "contact": "",
  "status": "verified|verified_with_caveat|partial|unresolved",
  "sources": [],
  "unresolved": []
}
```

## 字段规则

- `service_name`：使用官方事项名；没有官方名称时使用中性、可复述的归一化名称。
- `audience`：记录本科生、研究生、留学生、教职工或其他适用范围；未说明时不要推测。
- `channel`：区分线上、线下和两者，不因存在网页就推定可以在线办结。
- `materials`：逐项记录原文要求；区分原件、复印件、电子文件、照片和表格。
- `steps`：只合并重复表述，不创造前置审批、缴费或领取步骤。
- `time`：严格区分办公时间、截止日期和办理周期。
- `location`：允许只确认到校区或楼宇；不要把地图 POI 当作窗口事实。
- `contact`：只使用来源公开的官方咨询方式，不收集无关个人联系方式。
- `sources`：每个来源至少包含 `type`、`title`、`publisher`、`url_or_document`、`published_or_updated_at`、
  `accessed_at` 和 `supports`。

来源对象的最小形状如下。日期字段必须是 `YYYY-MM-DD` 表示的真实日历日期（例如 `2026-02-29`、
`2026-99-99` 均无效）。`published_or_updated_at` 可以填写官方页面显示的发布日期、更新时间或
`unknown`（仅在页面明确没有日期时），但字段本身不能省略；`publisher` 必须是发布主体名称，不能用
`unknown` 代替。`accessed_at` 记录本次查询日期，`supports` 至少列出一个被该来源直接支持的字段，并且每个
字段必须在当前记录中真实存在且非空；嵌套字段使用点号，例如 `location.building`。

`map_spatial` 的 `supports` 只允许 `address`、`coordinates`、`entrance`、`entrance_landmark`、`distance`
和 `route`。它不能支持 `responsible_unit`、`materials`、`steps`、`channel`、`time`、`fees`、`contact`、
建筑用途、活动安排或考试安排。`service_guide` 至少需要一个非 `map_spatial` 来源；仅有地图来源的办事记录无效。

```json
{
  "type": "school_official",
  "title": "事项办理指南",
  "publisher": "某大学教务处",
  "url_or_document": "https://example.edu/guide",
  "published_or_updated_at": "2026-08-01",
  "accessed_at": "2026-08-12",
  "supports": ["responsible_unit", "steps"]
}
```

## 状态规则

- `verified`：材料、步骤、责任部门和地点等核心字段由当前适用来源支持。
- `verified_with_caveat`：核心信息可信，但存在身份、校区、日期或公开范围限制。
- `partial`：仅确认到部分材料、步骤、部门或地点层级。
- `unresolved`：不足以指导用户办理；提供官方入口或责任部门，不生成猜测步骤。

`verified` 与 `verified_with_caveat` 的 `unresolved` 必须为空；`partial` 与 `unresolved` 必须至少列出一个未确认
项。已填写的责任部门与步骤只有被 `sources[].supports` 明确支持，才允许使用前两种状态。

## 默认交付顺序

1. 一句话办理结论。
2. 适用范围和前置条件。
3. 材料。
4. 步骤。
5. 时间、费用和办理周期。
6. 线下地点及与当前事项相关的功能。
7. 来源、查询日期和未确认项。

只在用户要求路线且已经完成地点确认后添加路线。
