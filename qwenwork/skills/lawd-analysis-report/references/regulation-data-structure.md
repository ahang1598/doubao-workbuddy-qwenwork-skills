# 法规检索返回数据结构（归一化契约）

> 不同「法规检索」连接器返回结构各异，本文档描述归一化后的统一契约字段。运行时先将连接器实际返回归一化为下述结构，再供报告撰写与门禁核对使用；原始返回可整体保留备查。

## 顶层结构

```json
{
  "data": {
    "currentPage": 1,
    "lawResult": [/* 法规对象数组 */],
    "pageSize": 10,
    "pageTotalCount": 200,
    "query": "检索关键词",
    "queryKeywords": ["关键词1", "关键词2"],
    "totalCount": 200
  },
  "httpStatusCode": 200,
  "requestId": "请求ID",
  "success": true
}
```

## lawResult 数组元素结构

```json
{
  "lawDomain": { /* 法规详细信息 */ },
  "similarity": "0.85"
}
```

## lawDomain 关键字段

### 报告撰写阶段重点使用的字段

| 字段 | 类型 | 说明 | 报告用途 |
|------|------|------|---------|
| `lawName` | string | 法规名称 | **核心**：引用法规时必须标注 |
| `lawOrder` | string | 条款编号（如"第二百六十三条"） | **核心**：精确引用条款 |
| `lawTitle` | string | 条款标题 | 条款定位 |
| `lawSourceContent` | string | 条款原文 | **核心**：报告中引用的法条内容 |
| `timeliness` | string | 时效性（现行有效/已废止/尚未生效） | **核心**：必须标注时效性 |
| `potencyLevel` | string(JSON) | 效力级别（法律/行政法规/司法解释等） | 法律层级判断 |
| `similarity` | string | 匹配相似度 | 相关性排序 |

### 其他可用字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `lawId` | string | 法规唯一 ID |
| `lawItemId` | string | 法规条目 ID |
| `issuingOrgan` | string(JSON) | 发布机关 |
| `issuingNo` | string | 发文字号 |
| `releaseYearMonthDate` | string | 发布日期 |
| `implementYearMonthDate` | string | 施行日期 |
| `abolitionBasis` | string(JSON) | 废止依据 |
| `modifyBasis` | string(JSON) | 修改依据 |
| `thematicClassify` | string | 主题分类 |

## 调用参考

- 检索通过「法规检索」连接器（`qwenwork_mcp_tool_call`）执行，探测/匹配/调用/降级完整流程见 [regulation-search-pipeline.md](regulation-search-pipeline.md)。
- 将连接器返回归一化为上述契约后，归一化结果可落盘为 JSON（如 `/tmp/lawding_analysis_regulations.json`），供交付门禁 `scripts/validate_analysis_report.py` 核对报告引用的法条（法规名+条号）是否可溯源。

## 注意事项

1. **Keywords 格式**：必须使用英文逗号（`,`）分隔，中文逗号会导致空结果
2. **Query 长度**：严格控制在 8-15 字以内
3. **时效性标注**：已废止的法规必须在报告中明确标注"已废止"
4. **优先引用**：现行有效法律优先，禁止引用已废止的《合同法》《担保法》《婚姻法》等旧法
