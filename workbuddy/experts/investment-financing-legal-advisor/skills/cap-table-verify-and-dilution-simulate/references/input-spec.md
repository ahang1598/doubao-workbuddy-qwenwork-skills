# 输入规格

## 输入模式

### Mode A：文件上传

用户提供历轮SPA文档（PDF/图片/文本）+ 工商登记信息截图或PDF。
技能从文档中提取结构化数据。

### Mode B：结构化输入

用户直接提供JSON/YAML格式的历轮数据+工商登记数据。

### Mode C：自然语言描述

用户口述历轮融资历程+工商登记概况。技能追问补全关键字段（追问≤1次，一次性列全部缺口）。

## 输入参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| round_agreements | file[] / object[] | 是 | 历轮SPA/增资协议/股权转让协议 |
| company_registration | object | 是 | 工商登记信息（注册资本/股东/持股比例/实缴出资） |
| founder_info | list | 是 | 创始人信息（姓名/角色/代持情况） |
| simulation_params | object | 否 | 假设融资参数（投前估值/投资额/新发比例） |
| anti_dilution_type | enum | 否 | weighted_average / full_ratchet |
| option_pool | object | 否 | 期权池信息（池比例/已授予/未授予/是否需Top-up） |
| convertible_bonds | object[] | 否 | 可转债信息（本金/利率/转换价/到期日） |
| nominee_arrangements | object[] | 否 | 代持安排（显名股东/隐名股东/代持比例） |
| platform_info | object | 否 | 持股平台信息（平台名称/类型/GP/LP/份额分配表） |
| liquidation_preference | object | 否 | 优先清算权条款（各轮优先级/倍数/参与权/上限） |

## round_agreements 结构

每轮协议须含以下字段：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| round_name | string | 是 | 轮次名称（设立/A轮/B轮/...） |
| round_type | enum | 是 | establishment / capital_increase / transfer / option_pool / convertible_conversion / shareholding_reform |
| date | string | 是 | 协议签署日期（YYYY-MM-DD） |
| investment_amount | number | 增资轮必填 | 投资额（万元） |
| pre_money_valuation | number | 增资轮必填 | 投前估值（万元） |
| new_shares | number | 增资轮必填 | 新发股数（万股） |
| price_per_share | number | 增资轮必填 | 每股价格（元） |
| transfer_shares | number | 转让轮必填 | 转让股数（万股） |
| transferor | string | 转让轮必填 | 转让方 |
| transferee | string | 转让轮必填 | 受让方 |
| investors | list | 增资轮必填 | 投资人列表（姓名/机构/投资额/持股类型） |
| special_terms | object | 否 | 特殊条款（反稀释/优先清算/参与权/转换权） |

## company_registration 结构

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| registered_capital | number | 是 | 注册资本（万元） |
| shareholders | list | 是 | 股东列表（姓名/持股比例/认缴出资/实缴出资） |
| registration_date | string | 否 | 最新工商登记日期 |
| notes | string | 否 | 工商登记备注（如代持标注/特殊说明） |

## 数据完整性校验

| 缺失项 | 影响程度 | 处理方式 |
|--------|----------|----------|
| 某轮协议未提供 | 高 | 追问+标注"缺少X轮数据" |
| 实缴数据缺失 | 中 | 按认缴计算+标注"按认缴口径" |
| 工商登记未提供 | 高 | 追问+标注"待核实工商登记" |
| 协议日期缺失 | 中 | 追问+按用户提供的顺序排列 |
| 每股价格缺失 | 中 | 可由投资额/新发股数推算+标注"推算值" |
