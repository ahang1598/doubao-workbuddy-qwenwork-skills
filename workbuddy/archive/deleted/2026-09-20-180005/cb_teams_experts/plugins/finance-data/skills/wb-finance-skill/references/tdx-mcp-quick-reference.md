# 通达信 MCP 调用速查

> 10 个工具，覆盖 A 股 / 港股 / 美股的行情、财务、选股、资讯、宏观五大领域。
> setcode 编码：1=沪市，0=深市，2=北交所；港股 / 美股走扩展行情。
> ✅ 以下所有示例均已于 2026-06-14 实际调用验证通过。

---

## 0. 代码检索（调用前先查代码）

```
tdx_lookup_stock query="贵州茅台"                    # A股（默认 range="GP"）
tdx_lookup_stock query="腾讯控股" range="HK-GP"      # 港股
tdx_lookup_stock query="苹果" range="MG-GP"          # 美股
tdx_lookup_stock query="上证指数" range="ZS"         # 指数
tdx_lookup_stock query="华夏上证50ETF" range="JJ"    # 基金/ETF
```

---

## 1. 实时行情

```
tdx_quotes code="600519" setcode="1"                  # 沪市（茅台）
tdx_quotes code="000001" setcode="0" hasCalcInfo="1"  # 深市，含计算指标
tdx_quotes code="399001" setcode="0"                   # 指数（深证成指）
```

---

## 2. K 线数据

```
tdx_kline code="600519" setcode="1" period="4" wantNum="20"        # 日线
tdx_kline code="000001" setcode="0" period="0" wantNum="48"        # 5分钟线
tdx_kline code="399006" setcode="0" period="5"                      # 周线
# 港股/美股必须加 target="1"：
tdx_kline code="00700" setcode="6" period="4" wantNum="20" target="1"  # 港股日线
```

> period: 0=5分钟, 1=15分钟, 2=30分钟, 3=60分钟, 4=日线, 5=周线, 6=月线, 7=1分钟, 8=1分钟K, 9=日K, 10=季线, 11=年线
> ⚠️ 港股 K 线 `target="1"` 可正常返回列名结构，但实际数据行可能为空或截断，建议交叉验证数据完整性。

---

## 3. 指标查询（自然语言，需明确实体）

```
tdx_indicator_select message="贵州茅台的市盈率和市净率"
tdx_indicator_select message="宁德时代主营构成"
tdx_indicator_select message="上证指数和创业板指估值水平" rang="ZS"
```

> ⚠️ **查基金指标的两步流程**（验证发现 `indicator_select` 无法直接用自然语言查基金）：
> 1. 先查代码：`tdx_lookup_stock query="华夏上证50ETF" range="JJ"` → 拿到基金代码（如 `510500`）
> 2. 再查指标：`tdx_indicator_select message="510500的净值和规模"`
> 直接写 `message="华夏上证50ETF的净值"` 会返回空或无关结果，因为 `indicator_select` 只认代码不认基金名称。

---

## 4. 条件选股（自然语言描述）

```
tdx_screener message="涨停"
tdx_screener message="MACD金叉且放量上涨"
tdx_screener message="主力净流入" pageNo="2" pageSize="20"
tdx_screener message="北向资金连续流入"
```

> 某些条件当天可能返回 0 条（如"3连板"在无相关股票时），属正常。

---

## 5. 深度财务数据（tdx_api_data，自动推导 mode）

### 三大报表
```
tdx_api_data entry="TdxShareCW.ph_agf10_cw_lyb" fixedTag="00101" code="000001"   # 利润表-报告期
tdx_api_data entry="TdxShareCW.ph_agf10_cw_lyb" fixedTag="00102" code="000001"   # 利润表-单季度
tdx_api_data entry="TdxShareCW.ph_agf10_cw_zcfzb" code="000001"                   # 资产负债表
tdx_api_data entry="TdxShareCW.ph_agf10_cw_xjllb" fixedTag="00101" code="000001" # 现金流量表-报告期
```

### 交易与资金
```
tdx_api_data entry="TdxSharePCCW.tdxf10_gg_jyds" code="000001" fixedTag="dzjy"   # 大宗交易
tdx_api_data entry="TdxSharePCCW.tdxf10_gg_jyds" code="000001" fixedTag="rzrq"   # 融资融券
tdx_api_data entry="TdxSharePCCW.tdxf10_gg_jyds" code="000001" fixedTag="jglhb"  # 龙虎榜（个股，仅当日上榜有数据）
```

> ⚠️ 龙虎榜个股查询仅在该股上榜时有数据，否则返回数据库错误。查全市场龙虎榜请用下方路由：
> `tdx_api_data entry="TdxSharePCCW.tdxsj_lhbd_lhbzl" branch="0" date="20260612" period="1"` （date 传具体交易日，传 0 返回最近交易日）

### 股东与机构
```
tdx_api_data entry="TdxSharePCCW.tdxf10_gg_gdyj" code="000001" fixedTag="jgcg"   # 机构持股汇总
tdx_api_data entry="TdxSharePCCW.tdxf10_gg_gdyj" code="000001" fixedTag="ltgd"   # 十大流通股东
tdx_api_data entry="TdxSharePCCW.tdxf10_gg_gdyj" code="000001" fixedTag="gdrs"   # 股东人数
```

### 股本与分红
```
tdx_api_data entry="TdxSharePCCW.tdxf10_gg_fhrz" code="000001" fixedTag="fh"      # 分红表
tdx_api_data entry="TdxSharePCCW.tdxf10_gg_gbjg" code="000001" fixedTag="xslt"   # 限售解禁
tdx_api_data entry="TdxSharePCCW.tdxf10_gg_gbjg" code="000001" fixedTag="gbbd"   # 股本变动
```

### 港股报表
```
tdx_api_data entry="TdxSharePCCW.skef10_hk_cwfx" fixedTag="1" code="00700"  # 港股利润表
tdx_api_data entry="TdxSharePCCW.skef10_hk_cwfx" fixedTag="2" code="00700"  # 港股资产负债表
tdx_api_data entry="TdxSharePCCW.skef10_hk_cwfx" fixedTag="3" code="00700"  # 港股现金流量表
```

### 公司信息
```
tdx_api_data entry="TdxSharePCCW.tdxf10_gg_zxts" fixedTag="gsgy" code="000001"  # 公司概要（含行业、主题、标签、财务亮点）
tdx_api_data entry="TdxSharePCCW.tdxf10_gg_gsgk" fixedTag="0" code="000001"      # 公司基本信息（含主营业务、高管、注册信息）
```

> ⚠️ 主营构成（`entry="TdxShareCW.ph_agf10_jyfx" fixedTag="00202"`）当前上游接口返回数据库错误，建议改用 `tdx_indicator_select message="主营构成"` 替代。

---

## 6. 资讯类（自然语言或结构化参数）

```
wenda_news_query query="贵州茅台最近的新闻"
wenda_news_query name="中芯国际" bdate="20260301" edate="20260614" keywords="扩产,先进制程"

wenda_notice_query query="宁德时代最近的公告"
wenda_notice_query name="贵州茅台" bdate="20260101" edate="20260614" keywords="分红,董事会"

wenda_report_query query="比亚迪最近的券商研报"
wenda_report_query name="中际旭创" bdate="20260301" edate="20260614" keywords="评级,目标价"
```

> 结构化参数（name/bdate/edate/keywords）和自然语言 query 两种方式均验证通过。
> 日期格式 YYYYMMDD，多个关键词用逗号分隔。

---

## 7. 宏观数据（管道格式）

```
wenda_macro_query query="中国|20210101|20251231||年度GDP总量"
wenda_macro_query query="美国|20240101|20251231||美国CPI同比"
wenda_macro_query query="人口|20150101|20251231||人口"
```

> ⚠️ 宏观工具只接受标准管道格式 `query`，不支持 name/bdate 等拆分参数。
> 管道格式：`主体|开始日期|结束日期|关键词|补充说明`

---

## 8. 实战经验与调参技巧

### fixedTag 含义对照

> `fixedTag` 决定 `tdx_api_data` 的子路由，不同 entry 下含义不同。

| entry | fixedTag 值 | 含义 |
|-------|------------|------|
| `ph_agf10_cw_lyb`（利润表） | `00101` | 报告期（累计） |
| | `00102` | 单季度 |
| `ph_agf10_cw_xjllb`（现金流量表） | `00101` | 报告期 |
| `ph_agf10_jyfx`（主营构成） | `00201` | 按产品 |
| | `00202` | 按地区 |
| `tdxf10_gg_jyds`（交易数据） | `dzjy` | 大宗交易 |
| | `rzrq` | 融资融券 |
| | `jglhb` | 龙虎榜（个股） |
| `tdxf10_gg_gdyj`（股东机构） | `jgcg` | 机构持股汇总 |
| | `ltgd` | 十大流通股东 |
| | `gdrs` | 股东人数 |
| `tdxf10_gg_gbjg`（股本结构） | `xslt` | 限售解禁 |
| | `gbbd` | 股本变动 |
| `tdxf10_gg_fhrz`（分红融资） | `fh` | 分红表 |
| `skef10_hk_cwfx`（港股报表） | `1` | 利润表 |
| | `2` | 资产负债表 |
| | `3` | 现金流量表 |

### tdx_api_data 的 mode 自动推导

`tdx_api_data` 内部会根据传入参数自动推导 mode（preset 结构化 / raw 原始）：

- **preset 模式（默认）**：传入 `entry` + `fixedTag` + `code`，工具自动识别路由、拼接参数、解析返回格式 → 输出结构化表格
- **raw 模式（手动降级）**：当 preset 推导失败或想直接传原始参数时，显式设 `mode="raw"`，用 `params` 数组传参：
  ```
  tdx_api_data entry="TdxShareCW.ph_agf10_jyfx" mode="raw" params=["00202","000333",""]
  ```
- **排查技巧**：如果 preset 模式报错，先切 raw 模式交叉验证——如果 raw 也失败，说明是上游接口问题而非参数格式问题（测 jyfx 时就是用这个方法确认的）

### 各工具返回数据量级参考

> 调用前可预期的大致数据量，便于判断是否返回正常。

| 调用 | 典型返回量级 |
|------|-------------|
| 利润表/资产负债表/现金流量表 | 20~24 期（约 5~6 年） |
| 十大流通股东 | 每期 10 人 × 18 期 ≈ 180 条明细 |
| 股东人数 | 约 30 行（按报告期） |
| 股本变动 | 约 20 条历史记录 |
| 港股三大报表 | 86~89 期（可追溯到 2001 年） |
| 龙虎榜全市场（单日） | 约 80~100 只个股 |
| wenda 资讯（news/notice/report） | 默认 5 条/页 |
| 宏观数据 | 取决于日期范围，通常 10~50 条 |

### wenda 系列工具：query vs 结构化参数

两种写法均可用，适用场景不同：

| 方式 | 示例 | 适用场景 |
|------|------|----------|
| 自然语言 query | `wenda_news_query query="贵州茅台最近的新闻"` | 快速查、不确定具体关键词时 |
| 结构化参数 | `wenda_news_query name="中芯国际" bdate="20260301" edate="20260614" keywords="扩产,先进制程"` | 精确筛选、指定日期范围、多关键词组合 |

- `wenda_macro_query` **只接受管道格式** `query="主体|开始日期|结束日期|关键词|补充说明"`，不支持 name/bdate 拆分参数
- 其他三个 wenda 工具（news/notice/report）两种方式都支持

### 错误排查方法论

遇到调用失败时，按以下顺序排查：

1. **参数格式**：setcode 对不对？港股/美股有没有加 `target="1"`？日期格式是不是 `YYYYMMDD`？
2. **标的选择**：查银行主营构成？查非交易日龙虎榜？换一个典型标的试试（推荐用 `000001` 平安银行或 `600519` 茅台做测试）
3. **raw 降级**：切 `mode="raw"` 用 params 数组重试，排除 preset 推导问题
4. **多标的交叉**：同一路由换 2~3 个不同标的，如果全失败 → 上游接口问题；如果部分成功 → 数据覆盖问题
5. **交易日/报告期**：非交易日查询交易类数据（龙虎榜、大宗交易）可能返回空，属正常

### 新手避坑清单

- ❌ 查港股忘了加 `target="1"` → 返回异常或空
- ❌ 用基金名称直接查 `indicator_select` → 返回无关 A 股结果
- ❌ 龙虎榜个股查未上榜的股票 → 报数据库错误（不是返回空）
- ❌ 龙虎榜全市场 `date="0"` 在周末查 → 返回空（不是报错）
- ❌ `wenda_macro_query` 用 name/bdate 拆分参数 → 不被接受
- ❌ `jyfx` 主营构成路由当前上游挂了 → 换 `indicator_select`

---

## 已知限制

| 场景 | 说明 | 替代方案 |
|------|------|----------|
| 龙虎榜（个股） | `jyds fixedTag="jglhb"` 仅在该股当日上榜时有数据；**未上榜时报数据库执行错误**（非空结果，是直接报错），因为上游 SQL 查不到该股当日龙虎榜记录 | 查全市场：`tdx_api_data entry="TdxSharePCCW.tdxsj_lhbd_lhbzl" branch="0" date="20260612" period="1"` |
| 龙虎榜（全市场） | `date="0"` 理论上返回最近交易日，但**非交易日（周末/节假日）返回空结果**（不报错，返回 0 条）；`date="1"` 返回日期解析错误 | 传具体交易日如 `date="20260612"` |
| 主营构成 | `tdx_api_data entry="TdxShareCW.ph_agf10_jyfx"` **上游数据库持续报错**：多标的（000001/600519/000858/000333）在 `fixedTag="00202"` 和 `"00201"` 下均返回 "数据库执行失败"；raw mode 交叉验证同样失败，确认是上游接口问题而非参数问题 | 改用 `tdx_indicator_select message="XXX主营构成"` |
| 北向资金 | `tdx_api_data fixedTag="bszj"` **上游数据源不稳定**：部分日期可返回数据，部分日期返回空或超时错误，行为不可预测 | 暂无稳定替代；可尝试 `tdx_screener message="北向资金连续流入"` 筛选个股 |
| 估值历史 | `tdx_api_data entry="TdxShareCW.ph_agf10_gzfx"` **可能返回空结果**：部分个股查询正常，部分返回空 AttachInfo（列名在但无数据行），取决于上游数据源是否覆盖该股 | 改用 `tdx_indicator_select message="XXX的PE和PB历史"` |
| 基金指标 | `tdx_indicator_select` **只认代码不认基金名称**：直接写 `message="华夏上证50ETF的净值"` 会返回空或无关 A 股结果 | 先 `tdx_lookup_stock query="基金名" range="JJ"` 拿到代码，再用代码查 |
| 港股 K 线 | `tdx_kline target="1"` **返回列名结构正常但数据行可能为空或截断**：ListHead 完整（日期/开/高/低/收/量/额），但 AttachInfo 可能不含实际数据行 | 建议交叉验证，必要时用 westock-data 补充 |
