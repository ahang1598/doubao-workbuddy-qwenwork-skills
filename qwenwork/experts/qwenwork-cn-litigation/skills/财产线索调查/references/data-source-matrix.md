# 数据源与能力映射矩阵

> 本矩阵中的能力名（BIZ.*）为平台无关抽象，实际工具名由运行时 `qw_mcp_list` 探测解析（企查查/天眼查/启信宝等同类），映射见 qoder.md「外部能力后端」。
>
> 优先级：工商信息后端 > 全网搜索 > WebFetch直访公开站点

## A. 工商信息后端（首选，按保全通道聚合）

### A1. 通道一 · 直接锁定
| 资产项 | 能力 |
|---|---|
| 银行账户（公开可查的零星账户） | `BIZ.company_detail`（招投标公告/政府公告中的付款信息） |
| 对外投资股权 | `BIZ.investment` |
| 股权冻结情况 | `BIZ.risk`（股权冻结） |
| 知识产权出质质 | `BIZ.ipr`（知识产权质押） |
| 股权质押 | `BIZ.risk`（股权质押） |
| 动产抵押 | `BIZ.risk`（动产抵押） |
| 土地抵押 | `BIZ.risk`（土地抵押） |
| 司法拍卖 | `BIZ.risk`（司法拍卖） |

### A2. 通道二 · 调查追踪
| 资产项 | 能力 |
|---|---|
| 曾用名 | `BIZ.company_detail` |
| 注册地址（含历史变更） | `BIZ.company_detail` |
| 变更记录 | `BIZ.company_detail` |
| 土地 | `BIZ.company_detail`（土地出让/转让） |
| 在建工程（许可证） | `BIZ.company_detail`（行政许可） |
| 专利（已授权/未授权） | `BIZ.ipr`（专利） |
| 商标 | `BIZ.ipr`（商标） |
| 著作权/软件著作权 | `BIZ.ipr`（著作权） |
| 域名 | `BIZ.ipr`（互联网服务） |
| 资质证书 | `BIZ.company_detail`（资质证书） |
| 行政许可 | `BIZ.company_detail`（行政许可） |

### A3. 通道三 · 债权拦截
| 资产项 | 能力 |
|---|---|
| 招投标项目 | `BIZ.company_detail`（招投标） |
| 诉讼案件（立案/裁判） | `BIZ.risk`（立案信息/裁判文书） |
| 被执行情况 | `BIZ.risk`（被执行人） |

### A4. 通道四 · 关联穿透
| 资产项 | 能力 |
|---|---|
| 股东信息 | `BIZ.shareholder` |
| 实际控制人 | `BIZ.investment`（实控人/受益所有人） |
| 分支机构 | `BIZ.company_detail` |
| 高管控制企业 | `BIZ.investment`（高管控制企业） |
| 高管对外任职 | `BIZ.investment`（高管/关联方） |
| 高管被执行/失信 | `BIZ.investment`（高管被执行/失信） |
| 历史关联方 | `BIZ.investment`（历史接口） |

### A5. 诉讼竞合态势
| 数据 | 能力 |
|---|---|
| 被执行人 | `BIZ.risk`（被执行人） |
| 失信被执行人 | `BIZ.risk`（失信被执行人） |
| 限制消费 | `BIZ.risk`（限制消费） |
| 终本案件 | `BIZ.risk`（终本案件） |
| 经营异常 | `BIZ.risk`（经营异常） |
| 行政处罚 | `BIZ.risk`（行政处罚） |
| 破产重整 | `BIZ.risk`（破产重整） |
| 担保信息 | `BIZ.risk`（担保信息） |

## B. 全网搜索（次选）

工商信息后端未覆盖的信息通过全网搜索补充检索。

## C. 公开站点直访

| 站点 | URL | 用途 |
|---|---|---|
| 国家企业信用信息公示系统 | gsxt.gov.cn | 基本信息、年报 |
| 中国执行信息公开网 | zxgk.court.gov.cn | 被执行人/失信/限消 |
| 信用中国 | creditchina.gov.cn | 行政处罚、信用记录 |
| 国家知识产权局 | cnipa.gov.cn | 专利 |
| 中国商标网 | sbj.cnipa.gov.cn | 商标 |
| 中国土地市场网 | landchina.com | 土地出让/转让 |
| 裁判文书网 | wenshu.court.gov.cn | 裁判文书全文 |

## D. 降级策略

当工商信息后端不可用时：
1. 全网搜索检索同类信息
2. WebFetch直访上述公开站点
3. 标注"⚠ 未经工商信息后端交叉验证"
