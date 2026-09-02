---
name: criminal-document-delivery-check
version: 1.0.0
name_en: criminal-document-delivery-check
description: 读取实际刑事文书制品，校验案件路径、可打开性、模板回执、最小可交付性、文种机关匹配、确定值冲突和家属敏感披露。触发：刑事文书正式交付前校验、草稿缺口检查、家属稿脱敏检查。不触发：文书说服力评估、法律研究、文书起草或通用 Word 排版。
---

# 刑事文书交付校验

## 核心职责

执行可复现的实际制品交付检查。直接打开 DOCX、HTML、Markdown 或文本，核对案件路径和渲染回执；运行期保持宽容，缺推荐字段、占位、日期签名和一般格式问题不升级为硬阻断。

## 适用范围

- 输出场景：`agency_submission`、`family_communication`、`lawyer_working`。
- 文书阶段：侦查、审查批捕、审查起诉、一审、二审与特殊程序。
- 支持草稿和正式提交两种模式。

## 输入契约

最小输入：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `doc_type` | 是 | 文种代码；缺失返回 `NEEDS_INPUT` |
| `output_scene` | 是 | 三类输出场景之一 |
| `matter_id` | 正式稿建议 | 当前案件标识，进入结果回执 |
| `matter_root` | 有实际制品时是 | 当前案件根目录，用于路径归属检查 |
| `document_path` | 正式稿是 | 实际 DOCX、HTML、Markdown 或文本的绝对路径 |
| `document` | 草稿兼容 | 仅文本草稿检查使用；没有实际制品时永不标记 `submission_ready` |
| `case_stage` | 否 | 能从文种、机关或程序材料推导时不要求 |
| `submission_mode` | 否 | `draft` 或 `formal`，默认 `draft` |
| `handling_authority` | 否 | 仅用于确定性机关错配检查 |
| `conflicts` | 否 | 已识别的主体、案号或金额确定值冲突 |
| `render_receipt` | 正式稿是 | 专项 Skill 返回的 `rendered=true`、`template_id` 等生成证据 |
| `previous_finding_codes` | 否 | 上一次阻断代码，用于第二次熔断 |

## 硬阻断

仅检查：

1. 实际制品不存在、跨案件路径、为空、损坏或无法读取；
2. 正式稿只有标题没有实质正文；
3. 文种与机关存在确定性错配；
4. 家属稿高置信度包含供述内容、卷宗摘录或同案犯供述；
5. 主体、案号或金额有两个无法判断真伪的确定值。

其他问题作为警告或补充输入：

- `case_stage` 可推导但未显式提供；
- 草稿占位、缺签名、日期、案号或执业证号；
- 附件、页码、来源索引不完整；
- 格式偏差或一般法条待核验。

不判断说服力、固定章节数、固定字数、模板哈希或所有字段是否填满。

## 状态和纠正

- `PASS`：交付；
- `PASS_WITH_WARNINGS`：交付，`retry_allowed=false`；
- `NEEDS_INPUT`：保留草稿并一次列缺口，`retry_allowed=false`；
- `BLOCKED`：首次允许一次定点修正；
- 同一阻断代码第二次出现：`fused=true`、`retry_allowed=false`，不得继续循环。

`deliverable_as` 区分机关提交稿、家属沟通稿、律师工作稿和草稿。机关正式稿只有同时满足 `status=PASS`、实际制品已读取、专项 Skill 渲染回执有效且 `template_id` 存在时，才返回 `submission_ready=true`。缺实际制品或回执只降为草稿并警告，不自动重试。

## 执行

调用：

```bash
python3 check_delivery.py input.json
```

脚本输出 JSON。也可安全 import 并调用 `check_document(payload)`。

## 输出模板

校验结果的人读摘要参考 [document-template.md](document-template.md)；确定性机关映射参考 [authority-map.md](./authority-map.md)。内部 JSON 不作为用户正式文书。

## 约束限制

1. 只校验，不修改文书，不新增法律结论。
2. 不因警告自动恢复上游子 Agent。
3. 不把平台不消费的 Agent manifest 字段描述为运行硬门禁。
4. 真实 RicheeAI Trace 和 Outcome 未验证前，本版本仅为候选。
