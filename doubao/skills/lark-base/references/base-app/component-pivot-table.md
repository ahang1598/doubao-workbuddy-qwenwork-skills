---
name: app-component-pivot-table
description: App 透视表的密度高度、内部列宽填充和行列指标。
---

# 透视表 pivotTable

默认容器宽×20，默认尺寸范围W24～48、H≥16；显式宽fill，根组合决定高fill，不height auto。无用户尺寸覆盖时固定高用20，不因叶子行少缩到12；首页模板调整时仍保持默认最小高16。用户明确合法尺寸优先。内部auto_fill_width与外框fill分别验收。

base_token/table_name/rows/columns/values为主结构，values至少1项，可选view_name或filter、维度/指标排序及auto_fill_width。行列是维度，values是指标；记录数用合适字段+COUNT，不用标准count_all/COUNTA。指标值排序与字段名排序分开，不套标准图专有格式方法。

先确定最终维度集合，明确“只按X”或完整行列不得补维度。只给主维度、预计≤8叶子行且有同一问题的真实分类时可补恰好1层；无合适分类时保留原维度及默认高度，不用编号/备注等高基数字段填空间。叶子数由真实记录不同组合或真实枚举上界证明，无证据未知。

新建默认显式auto_fill_width=true，用户手动列宽例外。更新最终行列指标传完整数组，省略保留；view_name/filter显式一项替换旧另一项。独立回读最终维度、values、排序、范围、叶子证据、外框高与内部列宽，实际结果另核对。
