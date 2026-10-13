# 维度 → 数据源 / 工具映射

执行第三步「数据收集」时**必须先阅读本文件**。按已选 provider 在对应 server 的工具列表中，用「工具描述关键词」匹配工具；**禁止**跨 provider 混用。

## QoderWork 适配说明（务必先读）

本技能运行在 **QoderWork** 时，数据源接入方式与旧版不同：

1. **企查查（QCC）是 QoderWork 原生连接器**，显示名 `Qichacha`，server 名统一为 **`qcc-company`**（单一连接器，OAuth 授权）。下表中出现的 `qcc-risk`/`qcc-operation`/`qcc-executive`/`qcc-ipr`/`qcc-history` 等是**旧版的多 server 拆分命名**，在 QoderWork 中**不要假设它们作为独立 server 存在**。QoderWork 下应把这些行的「描述关键词」合并，在**同一个 `qcc-company` 连接器**暴露的工具列表里按关键词匹配。
2. **按关键词匹配，不要硬编码工具名**：连接器授权（needs-auth）前工具不会枚举；授权（connected）后再用 `qw_mcp_list`/`qw_mcp_get` 查看真实工具名，并按下表「描述关键词」选择对应工具。
3. **天眼查（TYC）在 QoderWork 无原生连接器**，仅当用户自行接入 TYC 自定义 MCP（server 名 `tyc-mcp`）时下表 TYC 列才适用；否则忽略 TYC 行，统一走企查查。
4. `qcc-history`（历史维度）在旧版需企业认证。QoderWork 下若 `qcc-company` 未暴露历史/变更类工具，则跳过历史维度并标注 `历史数据未启用`。

---

## 通用规则

1. **先搜后查**：用入口工具拿到企业标识，再按维度并行调用（维度间无依赖，尽量并行）
2. **匹配顺序**：server 限定 → 工具 description 含下表关键词 → 确认返回字段覆盖「应查能力」
3. **失败处理**：单维度失败 → 输出中该段标 `该维度数据获取失败`，继续其他维度
4. **字段缺失**：接口成功但字段为空 → 填 `数据缺失`，**不得**省略表格行或整段

---

## 入口：搜索企业

| Provider | Server | 优先工具名（若有） | 描述关键词 | 提取标识 |
|----------|--------|-------------------|------------|----------|
| TYC | `tyc-mcp` | `search_companies` | search、搜索、关键词、企业搜索 | `gid` / `cgid` / `companyId` |
| QCC | `qcc-company` | `get_company_by_query` | 模糊搜索、企业查询、by query | 企查查主体标识 |

多条候选时展示列表让用户确认目标企业。

---

## 核心维度（综合尽调必选）

### 企业基础与画像

| 项目 | 内容 |
|------|------|
| 应查能力 | 工商登记、简介、规模、标签、联系方式、年报、曾用名、集团 |
| TYC server | `tyc-mcp` |
| TYC 描述关键词 | registration、工商、登记、basic、info、profile、企业信息 |
| QCC server | `qcc-company` |
| QCC 描述关键词 | registration、工商、basic、company info、企业基本信息 |

### 股权与投资

| 项目 | 内容 |
|------|------|
| 应查能力 | 股东、实控人、UBO、对外投资、控制企业、变更记录、分支机构 |
| TYC server | `tyc-mcp` |
| TYC 描述关键词 | shareholder、股东、equity、投资、控股、实控、穿透、branch |
| QCC server | `qcc-company` |
| QCC 描述关键词 | shareholder、股权、投资、控股、实控、变更、分支机构 |

### 司法风险

| 项目 | 内容 |
|------|------|
| 应查能力 | 判决文书、立案、开庭、被执行、失信、限消、终本、拍卖、冻结、出质、破产、清算 |
| TYC server | `tyc-mcp` |
| TYC 描述关键词 | risk、司法、诉讼、裁判、立案、被执行、失信、限高、终本、拍卖 |
| QCC server | `qcc-risk` |
| QCC 描述关键词 | judicial、诉讼、裁判、立案、被执行、失信、限消、破产 |

### 经营风险

| 项目 | 内容 |
|------|------|
| 应查能力 | 行政处罚、环保、经营异常、严重违法、动产/土地抵押、信用评价 |
| TYC server | `tyc-mcp` |
| TYC 描述关键词 | 经营异常、行政处罚、违法、抵押、环保、信用 |
| QCC server | `qcc-risk` + `qcc-operation` |
| QCC 描述关键词 | 行政处罚、经营异常、严重违法、抵押、信用 evaluation |

### 人员与高管

| 项目 | 内容 |
|------|------|
| 应查能力 | 主要人员、人员画像、合作伙伴、人员风险（失信/限消/被执行）、任职 |
| TYC server | `tyc-mcp` |
| TYC 描述关键词 | personnel、人员、高管、董事、监事、任职 |
| QCC server | `qcc-executive` |
| QCC 描述关键词 | executive、主要人员、高管、任职、人员风险 |

### 业务与市场

| 项目 | 内容 |
|------|------|
| 应查能力 | 招投标、融资、新闻舆情、荣誉资质、行政许可、供应商与客户 |
| TYC server | `tyc-mcp` |
| TYC 描述关键词 | 招投标、bid、融资、舆情、资质、许可、客户、供应商 |
| QCC server | `qcc-operation` |
| QCC 描述关键词 | 招投标、经营、融资、舆情、资质、许可、客户 |

---

## 按需维度（用户要求或企业类型匹配时）

| 维度 | 适用场景 | TYC | QCC |
|------|---------|-----|-----|
| 知识产权 | 科技/品牌企业或 IP 纠纷 | `tyc-mcp`：专利、商标、软著 | `qcc-ipr`：专利、商标、软著、APP、小程序、社交媒体 |
| 财务与上市 | 上市公司或要求财务分析 | `tyc-mcp`：financial、上市 | `qcc-company`：financial_data、listing_info |
| 历史数据 | 深度尽调、回溯变更 | `tyc-mcp`：历史、变更 history | `qcc-history`（需认证，不可用则跳过并标注） |
| 投资机构 | 目标为投资机构 | `tyc-mcp`：投资 institution | `qcc-operation`：investment_institution、private_fund |
| 建筑资质 | 建筑行业 | `tyc-mcp`：资质 qualification | `qcc-operation`：qualifications、credit_evaluation |

---

## 辅助能力（非独立维度）

| 用途 | TYC 关键词 | QCC 关键词 |
|------|-----------|-----------|
| 风险概览 / 空壳检测 | 风险概览、空壳、shell | risk overview、空壳 |
| 关系图谱 / 关联路径 | 图谱、关联、关系 graph | 关联、关系、图谱 |
| 多条件筛选（行业/地区/榜单） | 筛选、搜索、榜单 | 筛选、搜索、榜单 |

---

## Provider 维护说明

- 工具**正式名称**可能随上游 MCP 版本变化；维护时优先更新「描述关键词」列，勿在 SKILL.md 主文件重复整张表
- 新增维度时在本文件增行，并在 [report-template.md](report-template.md) 同步章节（若综合报告需展示）
