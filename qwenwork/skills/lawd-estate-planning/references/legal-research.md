# 法律法规、案例与普法链接检索（阶段 3）

## 1. 研究目标

为本次起草建立可复核的检索证据：不把模型记忆或搜索摘要当法律依据。内置规则包提供可重复的核心检查；实时检索负责确认当前效力、发现更新、补足规则未覆盖问题并寻找相关案例。二者必须同时具备，互不替代。

## 2. 检索通道（按优先级）

### 条文：pkulaw MCP 优先

1. `mcp__pkulaw__mcp-law-search-service.search_article`：`text` 传争点关键词，`timeliness` 传 `现行有效`，`size` ≤ 20；用于发现条文和关联规范。
2. `mcp__pkulaw__mcp-law-search-service.get_article`：`title` 传法规全称（如"中华人民共和国民法典"）、`number` 传中文条号（如"第一千一百三十四条"）；用于逐条取出规则包引用的条文原文。
3. 效力终核：对民法典继承编及继承编解释（一），用 `WebSearch`/`WebFetch` 打开国家法律法规数据库（flk.npc.gov.cn）或最高人民法院官网（court.gov.cn）页面核对"现行有效"，记录 `retrieved_at`。官网与 MCP 冲突时以官网为准并记入 `limitations`。

### 案例：pkulaw 案例检索

`mcp__pkulaw__mcp-case-search-service.search_case`：`text` 传与本案同构的事实描述（如"打印遗嘱 见证人 利害关系 无效"），`case_type` 传 `民事案件`，`decision_date_start` 默认近 5 年，必要时限定 `courthouse_province`。命中后记录案号/法院/裁判要旨，并写明与本案的事实差异（不只写有利结论）。

### 普法链接

`WebSearch` 优先选择立法机关、法院、司法行政机关、公证机构等可识别发布主体的文章/视频；每条必须用 `WebFetch` 实际打开，核对标题、发布者、发布日期与相关性，`verified_access = true` 才可交付。

## 3. 检索问题表

从已确认事实和诉求生成，每项含：问题 ID 与事实前提、法律问题和目标法域、关键词/同义词/案由、时间范围（案例默认近 5 年）、需要的法源层级和案例类型、与遗嘱条款或 AI 须知的关联。律师版保留完整检索式；普通用户版只呈现核心依据和用途。

## 4. 每条证据的最低字段

法律依据：`id`、`title`、`issuing_body`、`document_number`、`effective_status`、`publication_date`、`effective_date`、`source_url`、`retrieved_at`、`relevance`、`limitations`。

案例：`id`、`title`、`case_number_or_library_id`、`court_or_publisher`、`decision_or_publication_date`、`source_kind`、`source_url`、`retrieved_at`、`relevance`、`differences`。

普法链接：`id`、`title`、`publisher`、`content_type`、`published_at`、`url`、`retrieved_at`、`verified_access`、`relevance`。

## 4.5 财产表述清晰性核验与联网核验（阶段 3 必做，对用户静默执行）

所有财产表述都必须符合清晰、明确、可特定的原则；本步骤只执行、不在采集卡片中向用户展示。

- **不动产**：对每一处坐落地址，用 `WebSearch`（地图、行政区划、不动产登记公开信息等可核验来源）核验能否对应真实存在的地点（行政区划/道路/小区/楼栋层级匹配即可，不要求精确到户）。通过的记录来源与时间；无法确认（地址不规范、查无此地、多个同名歧义）的标记 `address_unverified`。
- **其他财产**：逐项检查表述是否足以特定该财产（存款是否有银行与账户类别、股权是否有公司与比例、数字资产是否有平台与账号、车辆是否有车牌或品牌型号等）。表述要素缺失但可经联网检索补足的（如公司存续状态、平台账号继承规则），检索补足并记录来源；
- **不清晰且无法补足**：标记 `description_unclear`，必须明确提示用户补足——列入汇总核对的待补清单与执行指引待办，说明缺什么、怎么补（例如"请补充存款所在银行及账户尾号"）；
- 核验只验证表述清晰性与地点真实性，不替代权属核验，不得据此推断权属或份额。

## 5. 核验门禁

`legal_research.status` 置为 `verified` 前必须确认：

- 规则包引用的每条条文都已通过 `get_article` 或官网原文取出，非凭记忆转述；
- 至少一项法律依据具有明确效力状态和检索时间；
- 至少一项近年相关案例。穷尽扩展（关键词、案由、时间、地区）后确无命中的，`status` 不得置为 `verified`：记录完整检索范围、转入人工判断，并把“未检索到相关案例”简明列入执行指引；
- 每项个案结论可追溯到事实前提和证据对象；
- 来源冲突已列入 `limitations` 或 `issues`；
- 普法链接均 `verified_access = true`；
- 全部财产表述已完成清晰性核验：不动产已联网核验或标记 `address_unverified`，不清晰且无法补足的已标记 `description_unclear` 并提示用户补足。
- 普法文章或视频不生成独立文件；交付时从 `conversation_education_links` 直接在对话中列出名称、主要内容和链接。

## 6. 失败与降级

- pkulaw MCP 调用失败：改用官网检索并在 `limitations` 记录"未获数据库原文"；
- 官网不可达、需登录或验证码：`status = "blocked"`，记录时间、目标来源和失败原因，不伪造依据；
- 未找到相关案例：扩大关键词、案由、时间或地区后仍无结果 → 记录检索范围、转人工说明；
- 只有二手内容：可作线索保存，不计入 `verified` 的最低数量；
- 发现规则包法源已修改：停用旧规则结论，标记规则包需升级并转专业复核。
