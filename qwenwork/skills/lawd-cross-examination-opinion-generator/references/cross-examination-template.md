# 质证意见书模板与数据契约

## 一、正式文书结构

1. 标题：质证意见；
2. 致送法院、案号、案由；
3. 提交人和代理人信息；
4. 材料范围或分析局限；
5. 质证意见速览表；
6. 逐项质证意见；
7. 程序性申请；
8. 质证总结论；
9. 可选反证建议；
10. 落款和日期。

速览表、逐项正文和总结论必须由同一 `evidence_items` 列表生成，不分别手写。

## 二、结构化 JSON 契约

生成脚本接收 UTF-8 JSON。最小结构如下：

```json
{
  "title": "质证意见",
  "court_name": "某某人民法院",
  "case_no": "（2026）某01民初1号",
  "case_type": "买卖合同纠纷",
  "submitter": {
    "role": "被告",
    "name": "乙有限公司",
    "agent": "代理人姓名",
    "contact": "联系方式"
  },
  "opposing_party": "原告甲有限公司",
  "scope_note": "本意见针对原告证据1至证据2。",
  "evidence_items": [
    {
      "id": "原告证据1",
      "name": "产品买卖合同",
      "submitter": "原告甲有限公司",
      "purpose": "证明双方存在买卖合同关系",
      "locator": "P1-P5",
      "evidence_type": "书证",
      "recognized_parts": "对该合同文本由双方签署无异议。",
      "dimensions": {
        "authenticity": {
          "status": "无异议",
          "reason": "现有材料未显示影响真实性的具体问题。"
        },
        "legality": {
          "status": "无异议",
          "reason": "现有材料未显示形式或来源方面的具体问题。"
        },
        "relevance": {
          "status": "无异议",
          "reason": "合同内容与本案买卖关系直接相关。"
        },
        "probative_force": {
          "status": "有异议",
          "reason": "合同只能证明约定内容，不能单独证明双方已经实际履行。"
        }
      },
      "conclusion": "对合同真实性及其证明合同关系的目的无异议，但不能据此单独证明实际履行情况。",
      "procedural_requests": [],
      "counter_evidence_suggestions": []
    }
  ],
  "procedural_applications": [],
  "overall_conclusion": "请求人民法院结合全案证据审查各项证据能否实现其证明目的。",
  "submission_date": "2026年8月4日"
}
```

## 三、字段规则

### 顶层字段

| 字段 | 必填 | 说明 |
|---|---:|---|
| `title` | 否 | 缺省为“质证意见” |
| `court_name` | 是 | 不知道时明确写“未提供”，不得编造 |
| `case_no` | 是 | 不知道时明确写“未提供” |
| `case_type` | 否 | 案由 |
| `submitter` | 是 | 至少含 `role` 和 `name` |
| `opposing_party` | 否 | 对方主体 |
| `scope_note` | 否 | 材料范围及局限 |
| `evidence_items` | 是 | 非空数组，编号唯一 |
| `procedural_applications` | 否 | 全案程序申请，字符串数组 |
| `overall_conclusion` | 是 | 全案请求，不得与单项结论冲突 |
| `submission_date` | 是 | 来自用户指示或实际生成日期 |

### 单项证据字段

| 字段 | 必填 | 说明 |
|---|---:|---|
| `id` | 是 | 稳定且唯一的编号 |
| `name` | 是 | 材料中的证据名称 |
| `submitter` | 是 | 实际提交主体 |
| `purpose` | 是 | 对方证明目的；不明确时写“待核验” |
| `locator` | 是 | 页码或其他可复核定位；不明确时写“未提供” |
| `evidence_type` | 否 | 证据类型 |
| `recognized_parts` | 否 | 无认可部分时可为空字符串 |
| `dimensions` | 是 | 四个固定键，不得缺项 |
| `conclusion` | 是 | 精确说明认可与不认可范围 |
| `procedural_requests` | 否 | 对该证据的程序申请，字符串数组 |
| `counter_evidence_suggestions` | 否 | 反证建议，字符串数组；不得虚构现有反证 |

四维固定键：

- `authenticity`：真实性；
- `legality`：合法性；
- `relevance`：关联性；
- `probative_force`：证明力。

每个维度包含 `status` 和 `reason`。`status` 只允许：`无异议`、`有异议`、`待核验`、`不适用`。

## 四、内容规则

- 不使用 `[案号]`、`XXX`、`TODO`、连续下划线等占位符；
- 对未知正式信息使用“未提供”，对待判断事项使用“待核验”；
- `conclusion` 不得只写“完全认可”或“完全不认可”，应说明认可范围和证明目的；
- `overall_conclusion` 不得加入单项分析中没有依据的新结论；
- 程序申请应包含对应证据编号、申请事项和理由；
- 反证建议仅写“建议收集/核验”，不得写成已经存在的己方证据。

## 五、排版约定

生成脚本使用 A4 纵向页面：

- 标题：黑体、二号、居中；
- 一级标题：黑体、小三；
- 正文：宋体、小四、1.5 倍行距；
- 表格：可为适配页面使用较小字号；
- 落款：右对齐；
- 表格和正文不使用颜色表达法律结论，保证黑白打印可读。
