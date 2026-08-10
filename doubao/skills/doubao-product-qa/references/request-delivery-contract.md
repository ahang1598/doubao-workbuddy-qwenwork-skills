# 请求与交付契约

本文件定义 `request_contract → phase_receipts → delivery_manifest → qa_deliver 回执` 的闭环。它解决三类高频错误：用户要求文件但只收到聊天文本、交付清单为空仍通过、载体文件存在但内容/格式不可用。

## 1. request_contract

正式任务初始化时一次性登记：

```json
{
  "request_contract": {
    "request_summary": "输出 Markdown，报告在前，用例和 Bug 单在后",
    "request_hash": "sha256:...",
    "task_mode": "execution_review",
    "scope": {
      "included_source_ids": ["SRC-001", "SRC-002"],
      "excluded_source_ids": [],
      "included_rounds": ["round-1"],
      "excluded_rounds": ["round-2"]
    },
    "evidence_policy": {
      "allow_new_execution": false,
      "allow_precheck_bug_promotion": false,
      "required_bug_evidence_level": "L2_observation"
    },
    "delivery": {
      "artifact_required": true,
      "format": "markdown",
      "carrier": "local",
      "filenames": ["外链分享灰度测试收口报告.md"],
      "required_sections": ["测试报告", "详细用例", "Bug 单"],
      "section_order": ["测试报告", "详细用例", "Bug 单"],
      "must_surface_to_user": true
    }
  }
}
```

规则：

- 用户指定格式、文件名、章节或顺序时逐字登记；未指定时才推断默认。
- 未指定载体时，方案/报告/Bug/收口默认 `lark_doc`（豆包文档），用例/追踪/矩阵默认 `lark_sheets`（豆包表格），汇报演示默认 `lark_ppt`（豆包 PPT）；叙述内容与二维明细并存时登记为 `multi`。
- `markdown` 不是默认格式，只有用户明确要求 Markdown、md 或 `.md` 文件时才登记。
- 混合格式使用 `format=multi`，并在 `delivery.artifacts` 中逐项登记 `format/carrier/filename`；例如方案 `docx` 与用例 `xlsx` 是两个独立交付物。
- `inline_markdown` 表示聊天内容；`markdown` 表示真实 `.md` 文件，两者不可互换。
- `included_rounds` 非空时，只能把该轮材料标为 `read`；排除轮次不能进入需求、用例、证据或结论。
- `allow_new_execution=false` 时，只能复核已有证据，不能擅自启动浏览器、接口写入或性能测试。
- 请求改变后更新 contract 和 canonical revision，旧阶段回执自动失效。

## 2. 阶段回执

`qa_flow.py complete` 只在门禁不为 `OPEN` 时写入：

```json
{
  "stage": "execution",
  "revision": 2,
  "state": "CLOSED",
  "checked_at": "2026-07-25T00:00:00Z",
  "source_fingerprint": "sha256:..."
}
```

回执同时绑定 revision 与 canonical 指纹。规范化改写不算内容变更，`complete` 会把仍然有效的前序回执重新盖章，不会因此要求你回去重跑上一阶段。`release` 不能通过 `complete` 单独关闭，只能由 `qa_deliver.py` 在真实产物回读后关闭。

## 3. Markdown 合并交付

当 `format=markdown` 且 `artifact_required=true`：

1. 正文由模型按体裁卡撰写；renderer 生成配套的二维附表；
2. 合并文件默认顺序为测试报告、详细用例、Bug 单；
3. publish 回读 UTF-8 文本，检查非空、`.md` 扩展名、必需章节和顺序；
4. 校验通过后登记文件绝对路径、sha256、source revision 和回读回执；
5. 最终回复原样返回 `qa_deliver.py` 回执中的定位，并按它给出的那一条调用上屏（只调一次）。

禁止：

- 只在聊天里写 Markdown；
- 先承诺文件名但不创建文件；
- 创建空文件、错误扩展名或缺章节文件；
- 手工修改派生 Markdown 而不更新 canonical。

## 4. 豆包在线载体、Office 与飞书交接

豆包文档/表格/PPT 在运行时对应飞书在线对象。QA Skill 负责内容、字段映射、revision 与请求契约；载体能力负责真实文件/对象：

| format | 生成与回读能力 | publish 最低检查 |
|---|---|---|
| `docx` | documents | OOXML 结构、标题层级、表格、长文本、revision |
| `xlsx` | spreadsheets | OOXML 结构、Sheet、行列数、类型、换行/样式、状态枚举、公式 |
| `pptx` | presentations | OOXML 结构、页数、溢出、图表数字、链接 |
| `pdf` | pdf | PDF 结构、页数、渲染、截断 |
| `lark_*` | 对应 lark Skill，字段映射见 [lark-delivery.md](lark-delivery.md) | 真实 URL、结构/行数/状态/链接、revision |

Office 任务必须特别回读：

- 业务状态与技术结果是否分列，例如 `AUTO_APPROVED` 与 `SUCCESS`；
- 数字列是否混入无意义常量、文本是否被截断、需要换行的单元格是否换行；
- 用户要求的多个文件是否全部存在，且文件名与契约逐项一致。

publish 的 `--readback-receipt` 应写实际检查结果，不写“已确认”“应该没问题”等空话。多个文件按 `filenames` 顺序逐项传入 locator 与回读回执。

## 5. 交付门

`qa_deliver.py` 会检查：

- 契约中的每个文件名都能在盘上找到，非空、扩展名与内部结构正确；
- 用户约定的章节是否齐全；
- 在线载体（豆包文档/表格）已真实创建并回读；
- 同一产物在本 revision 内是否已经交付过（内容 sha256 未变则复用，不重复创建）。

**只有一个条件会导致 `DELIVERY_LOCK=OPEN`：盘上没有任何产物可以发。**
其余问题——章节缺失、在线载体创建失败降级为本地文件、门的 REPORT 项——
一律放行并写进「本轮披露」，由最终回复原样转述。

这条边界是刻意的。把"产物不够好"也做成阻断，执行者手握真实产物却被判未完成，
就会去发明自己的交付方式（实测：旧版 lock=OPEN 后模型连调 5 次宿主工具，产出重复卡片）。
"够不够好"由披露承担，不由阻断承担。
