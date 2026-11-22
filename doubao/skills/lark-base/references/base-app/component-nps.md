---
name: app-component-nps
description: App NPS的默认尺寸、Rating样本和分类范围。
---

# NPS nps

默认16×10，推荐W8～24、H8～12，不默认fill/auto；用户合法尺寸/模板优先。必须真实Rating评分字段，不用其他数字或平均/求和冒充。

data_config.base_token/table_name/rating_field_name必填，可选view_name或filter、四段category_range、title/background_color。view_name/filter互斥，显式提交一项替换旧另一项，省略保留；数组整体替换，不传标准series/count_all。回读真实评分、样本范围、分类边界、模式并对照实际结果，不仅看标题。
