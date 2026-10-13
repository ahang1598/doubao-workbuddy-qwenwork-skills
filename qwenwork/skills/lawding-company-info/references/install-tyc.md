# 天眼查 (TYC) 接入说明（QoderWork 无原生连接器）

**重要：QoderWork 连接器市场目前没有原生的天眼查连接器。** 本技能在 QoderWork 中的**默认与推荐数据源是企查查**（原生 OAuth 连接器，见 [install-qcc.md](install-qcc.md)）。

天眼查在 QoderWork 中**只能作为自定义 MCP 服务**手动接入。仅当用户明确坚持使用天眼查、且愿意自行配置时，才走本文流程；否则一律引导用户使用原生企查查连接器。

## 作为自定义 MCP 接入（可选）

1. 引导用户打开：**QoderWork → 设置 → 连接器 → 自定义 MCP 服务 → 添加**（对应 key `qoderwork.settings.connector.custom`，动作 `add`）。
2. 服务类型选 HTTP（streamable-http），填写：

   ```json
   {
     "type": "streamable-http",
     "url": "https://mcp.tianyancha.com/v1",
     "headers": { "Authorization": "YOUR_API_KEY" }
   }
   ```

3. **API Key**：在天眼查开放平台账户中获取（`https://ai.tianyancha.com/profile/api-key`，注册登录后领取，以官方页面为准）。
4. **Authorization 格式**：天眼查**不带** `Bearer` 前缀，直接填 API Key 字符串（这一点与企查查不同）。
5. 保存后无需重启；工具列表出现由该 MCP 提供的企业搜索 / 工商登记类工具即视为可用。

## 可用性自检

工具列表中出现天眼查自定义 MCP 提供的工具即视为可用。标志性样本（前缀因配置而异）：

- 企业搜索类（描述含 search / 搜索 / 关键词）
- 工商登记类（描述含 registration / 工商 / 企业信息）

## 建议

由于 QoderWork 原生已内置企查查连接器（一键 OAuth、免 Key、免 JSON），在 QoderWork 环境下**优先推荐企查查**。天眼查自定义 MCP 仅作为用户强需求下的兜底选项。
