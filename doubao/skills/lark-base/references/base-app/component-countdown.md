---
name: app-component-countdown
description: App 倒计时的默认尺寸、固定毫秒目标和字段聚合。
---

# 倒计时 countdown

默认16×8，推荐W8～24、H8～12，不默认fill/auto；用户合法尺寸/模板优先。仅真实业务时间目标使用，不为右栏填充编日期。

```json
{"mode":"fixed","target_time":1798761600000,"title":"距离发布"}
```

```json
{"mode":"field","base_token":"<base_token>","table_name":"任务","field_name":"截止时间","aggregate":"MIN","title":"最近截止"}
```

示例固定时间须换真实毫秒目标。fixed为正整数毫秒，不传表/view/filter；field须真实日期类型，MIN最早、MAX最晚，view_name/filter互斥。不把秒值或日期字符串当毫秒，只改标题不重置目标，切模式核对旧模式字段清除。顶层Patch、对象/数组整体替换、null不清空。独立回读模式、目标及数据证据。
