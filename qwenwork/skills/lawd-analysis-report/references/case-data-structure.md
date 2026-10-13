# 案例检索返回数据结构（归一化契约）

> 不同「案例检索」连接器返回结构各异，本文档描述归一化后的统一契约字段。运行时先将连接器实际返回归一化为下述结构，再供报告撰写与门禁核对使用；原始返回可整体保留备查。

## 顶层响应结构

```json
{
  "Body": {
    "data": {
      "caseResult": [/* 案例对象数组 */],
      "currentPage": 1,
      "pageSize": 20,
      "query": "检索的问题",
      "queryKeywords": ["关键词1", "关键词2"],
      "totalCount": 100
    },
    "requestId": "xxx",
    "code": null,
    "httpStatusCode": 200,
    "message": null,
    "success": true
  }
}
```

## 案例对象结构（caseResult 数组元素）

```json
{
  "caseDomain": { /* 见下方字段列表 */ },
  "similarity": "0.85"
}
```

## caseDomain 关键字段

### 报告撰写阶段重点使用的字段

| 字段 | 类型 | 说明 | 报告用途 |
|------|------|------|---------|
| `caseNo` | string | 案号 | 引用案例时必须标注 |
| `caseTitle` | string | 文书名称 | 案例标题 |
| `caseCause` | string | 案由 | 法律关系定性参考 |
| `trialDate` | string | 审理日期 | 时效性判断 |
| `trialCourt` | object | 审理法院信息 | 管辖参考 |
| `disputeFocus` | string | 争议焦点 | **核心**：支撑争议点分析 |
| `verdict` | string | 裁判结果段落 | **核心**：支撑倾向性结论 |
| `legalBasis` | string | 法律依据 | **核心**：法条锁定参考 |
| `judgReason` | string | 裁判理由 | 裁判规则提取 |
| `referLevel` | string | 参考类型 | 案例权威性判断 |

### 列表阶段可用字段（jq 裁剪后保留）

| 字段 | 类型 | 说明 |
|------|------|------|
| `caseId` | string | 案件 ID |
| `caseType` | string | 案件类型 |
| `openCaseCause` | string | 立案案由 |
| `closeCaseCause` | string | 结案案由 |
| `documentType` | string | 文书类型 |
| `trialLevel` | string | 审判层级 |
| `trialProgram` | string | 审判程序 |
| `litigants` | string | 当事人 |
| `litigationParticipant` | string | 诉讼参与人 |
| `keyfacts` | string | 核心事实 |
| `appliedLaws` | string | 应用法条 JSON |
| `caseSummary` | string | 案件概述 |
| `basicCase` | string | 基本案情 |

### 详情阶段字段（裁剪后不可见，需从临时文件提取）

| 字段 | 类型 | 说明 |
|------|------|------|
| `courtFindOut` | string | 本院查明 |
| `courtThink` | string | 本院认为 |
| `sourceContent` | string | 文书正文 |
| `trialProcess` | string | 审理经过 |
| `preTrialProcess` | string | 前审情况 |

## trialCourt 对象

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | string | 法院名称 |
| `commonLevel` | string | 法院层级 |
| `province` | string | 省份 |
| `city` | string | 城市 |

## 调用与裁剪

- 检索通过「案例检索」连接器（`qwenwork_mcp_tool_call`）执行，探测/匹配/调用/降级完整流程见 [case-search-pipeline.md](case-search-pipeline.md)。
- 将连接器返回归一化为上述契约后，删除体量较大的重字段（`courtFindOut` / `sourceContent` / `trialProcess` / `preTrialProcess`）以节省 token，保留报告撰写所需字段。
- 归一化结果可落盘为 JSON（如 `/tmp/lawding_analysis_cases.json`），供交付门禁 `scripts/validate_analysis_report.py` 核对报告引用的案号是否可溯源。
