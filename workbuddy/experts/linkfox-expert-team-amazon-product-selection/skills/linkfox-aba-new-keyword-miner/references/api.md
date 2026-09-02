# ABA 新词挖掘专家 (ABA New Keyword Mining Expert) API

## 调用规范

- **请求地址**：`${LINKFOX_TOOL_GATEWAY}/aba/intelligentQuery`
- **请求方式**：POST，Content-Type: application/json
- **认证方式**：Header `Authorization: <api_key>`，api_key 从环境变量 `LINKFOX_AGENT_API_KEY` 或 `LINKFOXAGENT_API_KEY` 读取

## 请求参数

POST Body（JSON）：

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| analysisDescription | string | 是 | | 自然语言查询描述，会被后端转换为结构化 SQL |
| region | string | 否 | `US` | 站点代码。可选值：US、DE、BR、CA、AU、JP、AE、ES、FR、IT、SA、TR、MX、SE、NL |
| exportCsv | boolean | 否 | `true` | 本 skill 专属参数，是否自动导出 CSV（脚本拦截，不传给后端） |
| translate | boolean | 否 | `true` | 本 skill 专属参数，是否 AI 批量翻译为中文（脚本拦截，不传给后端；翻译调 linkfox-aigc-textgen） |

### analysisDescription 编写要点

1. 开头指明站点（如"筛选美国站"）
2. 用精确数字范围（写 `searchFrequencyRank <= 200000` 而非"排名比较靠前"）
3. 明确时间范围（写"2025年10月至2025年11月"而非"去年秋天"）
4. 对比基线写清时间点（"在…期间"vs"在…之前"）
5. 指定去重逻辑（"按 searchTerm 去重"）
6. 分页时加"按 searchTerm 字母升序排列，跳过前 N 个，返回第 N+1 到 N+100 个"
7. 需要搜索频率排名时加"返回 searchTerm 及其 searchFrequencyRank"

## 响应结构

| 字段 | 类型 | 说明 |
|------|------|------|
| success | boolean | 是否查询成功 |
| errcode | integer | 200 表示成功 |
| errmsg | string | 错误消息 |
| total | integer | 结果总数 |
| costTime | integer | 耗时（ms） |
| costToken | integer | 消耗 token |
| tables | array | 结果数据数组 |
| tables[].data | array | 数据行，每行含 `searchTerm` 或 `searchterm` 字段 |
| tables[].columns | array | 列定义 |
| tables[].name | string | Sheet 名称 |
| tables[].analysisStatement | string | 后端生成的 SQL |
| tables[].userExplanation | string | 后端对查询的自然语言解释 |
| downloadNote | string | 下载提示 |

### CSV 导出

当 `exportCsv` 为 `true`（默认）且查询成功（`errcode == 200`）时，脚本自动从 `tables[0].data` 中提取搜索词及排名，经 AI 批量翻译后导出为 CSV 文件：

- **编码**：UTF-8 BOM（Excel 直接打开不乱码）
- **列**：`序号` / `搜索词` / `中文翻译` / `搜索频率排名` / `标记` / `备注`
- **翻译**：当 `translate` 为 `true`（默认）时，调用 linkfox-aigc-textgen (GEM_3_FLASH) 批量翻译；翻译失败时对应位置留空
- **路径**：与 JSON 同目录，文件名 `.json` 替换为 `.csv`

## 错误码

| errcode | 含义 | 处理建议 |
|---------|------|----------|
| 200 | 成功 | 正常解析 `tables` / `data` |
| 401 | 认证失败 | 检查 `LINKFOX_AGENT_API_KEY` 环境变量 |
| 402 | 积分不足 | 前往 https://os.linkfox.com/ 补充积分 |
| 其他非200 | 业务异常 | 参考 `errmsg` 字段 |

## 计费

按动态规则计费：
- 初始 SQL 生成积分
- 各成功任务执行重试积分
- `round(CSV文件大小MB * 0.075)`

同一会话同参数组合 24h 本地缓存，不重复计费。

## 数据限制

- ABA 数据为周维度（非日维度）
- 约 3 年历史数据
- 单次查询最多返回 10,000 条记录
- `searchFrequencyRank` 值越小代表搜索热度越高（Rank 1 = 最热门）

## 支持站点

US、DE、BR、CA、AU、JP、AE、ES、FR、IT、SA、TR、MX、SE、NL

## 反馈 API

- **POST** `https://skill-api.linkfox.com/api/v1/public/feedback`
- Content-Type: application/json

```json
{
  "skillName": "linkfox-aba-new-keyword-miner",
  "sentiment": "POSITIVE|NEUTRAL|NEGATIVE",
  "category": "BUG|COMPLAINT|SUGGESTION|OTHER",
  "content": "描述"
}
```
