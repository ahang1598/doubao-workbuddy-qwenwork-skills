# 客户销售增长专家团

一个可直接使用的 Team 型 WorkBuddy 专家包，覆盖客户评分、赛道推荐、客户场景分析、客户匹配、筛选条件、招聘分析、电销话术、陌拜话术和客户攻坚打法。

## 类型

Team 型（1 名主理人 + 9 名专业 Agent）

## 成员

- **顾衡｜销售增长总监**：需求识别、团队调度、上下文中转和最终汇编。
- **沈量｜客户推荐分析师**：四维评分、云需求、产品匹配、交叉售卖。
- **林策｜销售打法策略师**：决策链、破冰/POC/促成、竞品应对。
- **周域｜云赛道推荐分析师**：赛道、头部企业、腾讯云方案、标杆案例。
- **程景｜客户业务场景分析师**：客户场景、产品适配、价值和案例。
- **苏言｜B2B销售电销话术专家**：电话开场、价值切入、异议处理、约访。
- **陆行｜B2B销售陌拜话术专家**：面访开场、价值展示、产品沟通、下一步。
- **唐配｜客户语义匹配分析师**：通过公众号客户信息表 MCP 匹配客户。
- **许准｜客户筛选条件分析师**：通过公众号客户信息表 MCP 核验 JSON 筛选条件。
- **何析｜招聘结构分析师**：岗位归类、人数占比、核心招聘方向。

## 协作路由

```text
评分 + 攻坚：客户推荐分析师 → 销售打法策略师
赛道 + 场景：赛道推荐分析师 ∥ 客户业务场景分析师
找客名单：客户语义匹配分析师 → query_wx_cust_db MCP
找客条件：客户筛选条件分析师 → query_wx_cust_db MCP
触达素材：电销话术专家 / 陌拜话术专家
招聘结构：招聘结构分析师（纯计算，不调用外部工具）
```

## 依赖与 MCP 约束

安装/召唤专家团时，WorkBuddy 会引导连接以下必需依赖；未连接时，对应能力不可用：

- **乐享知识库连接器**（WorkBuddy 官方）：通过 `plugin.json` 的 `workbuddy.dependencies` 声明引用（`{"type": "mcp", "name": "lexiang"}`），由系统统一激活和授权，包内不自带乐享配置。6 名知识库类成员在 frontmatter 声明 `skills: ["lexiang-knowledge-base"]`，启动时预加载官方乐享 Skill 以获得正确的调用规范；可调用 `search_kb_embedding_search`，必要时使用 `search_kb_search`、`entry_describe_ai_parse_content` 或 `block_fetch_page`。
- **公众号客户信息表 MCP**（包内 `.mcp.json`）：由插件标准机制自动加载，`plugin.json` 中无需额外声明。供客户匹配和筛选条件 Agent 调用 `query_wx_cust_db`；用户需自行填写访问令牌，专家包不包含任何真实令牌。
- 客户匹配和筛选条件 Agent 禁止运行 Terminal、Python、CLI，禁止读取 Token、`.env`、配置或 wrapper 文件。
- 客户表查询每次只传一个业务字段；匹配任务 `page_size=5`、总调用不超过 12 次、翻页不超过 4 次。

## 使用示例

- 请先对这个客户做四维推荐评分，再制定从破冰到成交的销售打法。
- 请分析这个赛道的头部企业、腾讯云方案和标杆案例。
- 请根据客户名称和赛道生成一套电销或陌拜话术。
- 请找和这段需求匹配的客户，并按匹配度排序。
- 请把“找湖南省做智能质检的客户”转换成已核验的 JSON 筛选条件。
- 请分析这份岗位招聘 JSON 的岗位结构和核心招聘方向。

## 头像

`avatars/` 中已包含团队、主理人和全部成员头像，均已统一为 512×512 PNG，单张不超过 500KB。

## 目录结构

```text
customer-sales-intelligence-team/
├── .codebuddy-plugin/plugin.json   # 专家团配置
├── agents/                          # 主理人 + 9 名成员定义
├── avatars/                         # 团队、主理人和成员头像
├── settings.json                    # 指定主理人
└── README.md
```

## 校验与打包

在专家包所在目录执行（`$EXPERT_DIR` 为本专家包路径，`$OUTPUT_DIR` 为产物目录）：

```bash
python3 "$SKILL_DIR/scripts/validate_expert.py" "$EXPERT_DIR"
python3 "$SKILL_DIR/scripts/register_expert.py" "$EXPERT_DIR" --session-id "$SESSION_ID"
python3 "$SKILL_DIR/scripts/package_expert.py" "$EXPERT_DIR" "$OUTPUT_DIR"
```

也可直接按规范打包提交：`zip -r customer-sales-intelligence-team.zip customer-sales-intelligence-team/`
