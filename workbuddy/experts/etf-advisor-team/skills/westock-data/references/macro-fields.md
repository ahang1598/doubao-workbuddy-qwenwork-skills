# 宏观经济指标字段说明

本文档列出 `westock-data macro` 命令的指标清单与返回 schema。

> 数据来源：腾讯自选股宏观经济数据接口

## 子命令总览

```bash
westock-data macro list [--region cn|us|hk|jp|eu|global]    # 列出指标
westock-data macro indicator <短名[,短名...]> [...]          # 查主题型指标
westock-data macro indicator --region <r> [--date D]         # 一键拉某 region 全套
westock-data macro expect list                               # 列 36 个地区
westock-data macro expect --area <iso3> [--year Y | --start --end]  # 海外预期日历
```

每个 entry 在注册表里声明 `region` + `mode`：
- `mode=date` → 用 `--date`（默认今天），底层 `query_list_data_by_date(实际日期)`
- `mode=year` → 用 `--year`/`--start --end`，底层 `query_list_data_by_date(YYYY-01-01)`

## 指标清单（短名表）

### 中国 (cn) — 按年指标

| 短名 | 完整代码 | 名称 | 分类 |
| --- | --- | --- | --- |
| `cn_gdp` | `macro_gdp` | GDP数量指标 | GDP |
| `cn_cpi_ppi` | `macro_cpi_ppi` | GDP价格指标(CPI/PPI) | GDP |
| `cn_pmi` | `macro_pmi` | GDP供给指标(PMI) | GDP |
| `cn_profit` | `macro_profit` | GDP供给指标(工业企业利润) | GDP |
| `cn_valueadded` | `macro_valueadded` | GDP供给指标(工业增加值) | GDP |
| `cn_consumption` | `macro_consumption` | GDP需求指标(消费) | GDP |
| `cn_investment` | `macro_investment` | GDP需求指标(投资) | GDP |
| `cn_export` | `macro_export` | GDP需求指标(进出口) | GDP |
| `cn_export_value` | `macro_export_value` | GDP需求指标(出口交货值) | GDP |
| `cn_prosperity` | `macro_prosperity` | GDP供给指标(企业景气指数) | GDP |
| `cn_fiscal` | `macro_fiscal` | GDP财政指标 | GDP |
| `cn_power_consumption` | `macro_power_consumption` | GDP供给指标(用电量) | GDP |
| `cn_disposable_income` | `macro_disposable_income` | GDP需求指标(可支配收入) | GDP |
| `cn_capacity_utilization` | `macro_capacity_utilization` | GDP供给指标(产能利用率) | GDP |
| `cn_product_output` | `macro_product_output` | GDP供给指标(宏观产量) | GDP |
| `cn_financing` | `macro_financing` | 货币需求指标(社融) | 货币 |
| `cn_fundquantity` | `macro_fundquantity` | 货币供给指标(数量) | 货币 |
| `cn_fundcost` | `macro_fundcost` | 货币供给指标(利率) | 货币 |
| `cn_yield_curve` | `macro_yield_curve` | 货币供给指标(国债收益率曲线) | 货币 |
| `cn_mlf` | `macro_mlf` | 货币供给指标(公开市场操作/MLF) | 货币 |
| `cn_forecast` | `macro_forecast` | 宏观预测 | 综合 |
| `cn_calendar_hist` | `macro_calendar_hist` | 宏观日历历史 | 综合 |

### 中国 (cn) — 按日期指标

| 短名 | 完整代码 | 名称 | 分类 |
| --- | --- | --- | --- |
| `cn_core` | `macro_core_indicators_cur_p1/p2` | 最新核心宏观指标（聚合短名，一键拉 p1+p2） | 综合 |
| `cn_core_p1` | `macro_core_indicators_cur_p1` | 最新核心宏观指标(1) | 综合 |
| `cn_core_p2` | `macro_core_indicators_cur_p2` | 最新核心宏观指标(2) | 综合 |
| `cn_employment` | `macro_employment` | 就业情况 | 综合 |
| `cn_calendar_future` | `macro_calendar_future` | 宏观日历未来 | 综合 |
| `cn_premium_curve` | `macro_premium_curve` | 溢价率曲线(红利/股债) | 估值 |
| `cn_premium_value` | `macro_premium_value` | 溢价率水平(含10年分位) | 估值 |
| `cn_term_spread` | `macro_term_spread` | 期限利差与曲线形态 | 估值 |
| `cn_lpr` | `macro_lpr` | 贷款市场报价利率(LPR) | 中国专项 |
| `cn_caixin_pmi` | `macro_caixin_pmi` | 财新PMI | 中国专项 |
| `cn_installed_capacity` | `macro_installed_capacity` | 发电装机容量 | 中国专项 |

### 美股 / 港股 / 日本 / 欧元区 — 按日期主题指标

| 短名 | 完整代码 | 名称 |
| --- | --- | --- |
| `us_employment` / `us_eco_growth` / `us_inflation` / `us_confidence` / `us_monetary` / `us_fiscal` / `us_energy` / `us_realestate` | `macro_us_*` | 美股宏观（就业/增长/通胀/景气/货币/财政/能源/地产） |
| `hk_eco_growth` / `hk_export_reserve` / `hk_monetary` / `hk_others` | `macro_hk_*` | 港股宏观 |
| `jp_eco_growth` / `jp_inflation` / `jp_employment` / `jp_confidence` / `jp_monetary` / `jp_export_reserve` | `macro_jp_*` | 日本宏观 |
| `eu_eco_growth` / `eu_inflation` / `eu_monetary` / `eu_confidence` / `eu_export_reserve` / `eu_employment` | `macro_eu_*` | 欧元区宏观 |

> 这些主题指标返回**事件日历型数据**：每条记录对应一次具体的指标发布（如"美国 5 月 ISM 制造业 PMI"）。统一 schema：`IndicatorName / OccurDate / OccurTime / ActualValue / ForecastValue / FormerValue`。

### 海外预期日历 (global) — 按年（按地区 iso3）

通过 `macro expect --area <iso3>` 查询。短名形如 `expect_<iso3>`，共 36 个地区：

| iso3 | 国家/地区 | iso3 | 国家/地区 | iso3 | 国家/地区 |
| --- | --- | --- | --- | --- | --- |
| `chn` | 中国 | `usa` | 美国 | `jpn` | 日本 |
| `hk` | 中国香港 | `twn` | 中国台湾 | `kor` | 韩国 |
| `sgp` | 新加坡 | `aus` | 澳大利亚 | `nzl` | 新西兰 |
| `ind` | 印度 | `idn` | 印度尼西亚 | `mys` | 马来西亚 |
| `tha` | 泰国 | `phl` | 菲律宾 | `vnm` | 越南 |
| `eu` | 欧洲联盟 | `euz` | 欧元区 | `efta` | 欧英EFTA |
| `uk` | 英国 | `fra` | 法国 | `deu` | 德国 |
| `ita` | 意大利 | `esp` | 西班牙 | `grc` | 希腊 |
| `che` | 瑞士 | `swe` | 瑞典 | `nor` | 挪威 |
| `rus` | 俄罗斯 | `ukr` | 乌克兰 | `tur` | 土耳其 |
| `can` | 加拿大 | `mex` | 墨西哥 | `bra` | 巴西 |
| `chl` | 智利 | `zaf` | 南非 | `glo` | 全球 |

> 海外预期 schema：`IndicatorName / OccurDate / OccurTime / ActualValue / ForecastValue / FormerValue / Importance`（`Importance` 为重要程度 1~3）。

---

## 统一字段说明（主题型 + 海外预期共用）

| 字段 | 说明 |
| --- | --- |
| `IndicatorName` | 指标名（中文，如"美国 5 月非农就业"） |
| `OccurDate` | 数据发生/发布日期（YYYYMMDD） |
| `OccurTime` | 发布时间（HH:MM） |
| `ActualValue` | 实际值（已发布） |
| `ForecastValue` | 市场预测值 |
| `FormerValue` | 前值 |
| `Importance` | 重要程度（仅海外预期，1=低 / 2=中 / 3=高） |

> 各指标的具体返回字段（如 GDP 子项、CPI 分项等）可通过 `westock-data macro indicator <短名> --raw` 查看实际返回的完整字段列表，字段名通常为英文大写下划线格式（如 `NOMINAL_GDP_CUM`），含义可从字段名和上下文推断。
