# 财报研析团 · 工作目录约定与数据契约（v1.0）

> 所有成员（含主理人）执行任务前必读。本文档定义工作目录、产物路径、单位契约、数据版本化与 PDF 渲染链路。

## 一、工作目录约定

### 1.1 路径定义

- `$PLUGIN_ROOT`：专家包根目录（即 `bank-retail-analyst/` 所在目录，安装时由系统注入，勿硬编码个人路径）
- `$PWD`：本次任务的运行目录（由主理人创建 `~/RetailAnalysis` 或用户指定工作区）
- `$SKILL_ROOT`：`$PLUGIN_ROOT/skills/<skill-name>`

### 1.2 目录结构（任务运行期间）

```
$PWD/
├── data/
│   ├── reports/            # P1 下载的年报 PDF
│   ├── extracted_text/     # 本地解析产物 {银行}_2025年度.md
│   ├── standard/           # P2a 输出 {银行}.json
│   ├── text/               # P2b 输出 {银行}.json
│   ├── partial/            # 中间产物（standard_* / text_* / insight_* / sg_*）
│   └── benchmark_database.json  # P3 重建的对标库
├── work/
│   └── YYYY-MM-DD_{基准行}/  # 每次任务独立目录（见 §二 数据版本化）
├── output/
│   └── {基准行}/             # 最终报告（3 份 PDF + MD）
└── report_assets/          # VIS 资产（LOGO/palette，见 §三）
```

### 1.3 写法规范

- 所有 JSON 产物 `ensure_ascii=False, indent=2`（便于 diff 与复核）
- 脚本/产物命名带日期后缀（`_runtime_xxx_YYYYMMDD.py`），任务结束由主理人清理
- 报告内所有关键数字必须可溯源（standard/text 指标名 + 行号，或 MD 行号）

## 二、数据版本化（防残留铁律）

> **背景教训**：2026-08-06 曾因复用 8 月 4 日"链路验证用模拟值"数据导致整条流水线输出错误，本次修复时全量重建。

1. **每次任务独立 work 目录**：`work/YYYY-MM-DD_{基准行}/`，禁止覆盖历史任务数据
2. **重建数据库前置校验**：`benchmark_database.json` 等核心产物，加载前必须检查：
   - `_schema_version` / `schema_version` 字段存在且为正确版本（standard: v1.x；benchmark: benchmark-v1.0；sg: sg-v1.1）
   - 含 `模拟` / `mock` / `链路验证` 标注 → 判定为残留数据，**必须重建**，禁止复用
3. **覆盖率门控**：standard 有值指标 ≥ 30、text 有值指标 ≥ 8、sg partial = 12 个文件，不达标视为未完成
4. **产物新产出门（mtime）**：产物文件 mtime 必须晚于本次提取执行开始时刻（成员开始时记录 `start_ts=$(date +%s)`，结束时用 `stat -f %m` 对比；mtime 早于 start_ts = 本次未真正写入 = 未完成）。复用旧文件/历史残留一律视为未完成，禁止当作本次产物回报
5. 产物文件存在 ≠ 完成：必须同时通过 **mtime 新产出门 + schema/覆盖率校验**
6. **`extract_partial` 信号**：提取类成员在任一硬门不满足时（bucket 缺失/覆盖率不达标/未落盘/mtime 旧）必须显式回传 `extract_partial` + 缺失 bucket 清单与覆盖率数字，由主理人 resume 走 MD 全文兜底；**禁止 silent return**（既不发 ready 也不发 partial）

## 三、PDF 渲染链路（统一走 build_report）

> **背景教训**：2026-08-06 曾用 playwright 直接渲染 HTML，导致封面独立页 + 目录分页丢失、LOGO 破图；poppler 缺失导致适配器终验失败。

1. **禁 playwright 直渲模板**：skill 模板必须走 `pdf_report_builder_runtime/scripts/html_to_pdf.py` 的 `build_report()`（内部处理封面独立页 + 正文分页 + 合并）
2. **VIS 资产预置**：`report_assets/by_bank/{短名}/logo/logo_base64.txt` 必须存在（缺失时用 PIL 按 banks.yaml 官方色生成文字 LOGO：`{银行}红` + 英文简称），`vis/palette.json` 同步生成
3. **目录 toc_items**：benchmark 模板需要 ctx 提供 `toc_items`（[序号, 标题, 页码] 列表），否则目录页空白
4. **poppler 缺失降级**：`pdf_validator` 依赖 `pdftoppm`，本机缺失时：
   - skill5 适配器：`--html-only` 出 HTML/MD，再用 `build_report` 渲染 PDF（跳过视觉校验）
   - 禁 brew 安装（本机不可用）
5. 渲染完成必须验证：PDF 页数 ≥ 10、封面 LOGO 可见、目录页非空（截图抽查）

## 四、单位契约（成员输出前归一）

| 类型 | 标准单位 | 存储 | 显示 | 换算规则 |
|------|---------|------|------|---------|
| 金额（表格） | 百万元 | standard JSON | 亿元（÷100） | 原表"亿元"需 ×100 并存 notes |
| 金额（文字） | 亿元 | text JSON | 亿元 | 原表百万元 ÷100 并存 calibration_note |
| 客户数 | 万户 | 万户 | 万户 | 原"亿户" ×10000；原"户" ÷10000；threshold：>1000 视为亿户/户 |
| 比率/利率 | % | % | % | 直接输出百分数数值（0.88 = 0.88%） |
| AUM | 亿元 | 亿元 | 亿元 | 原"万亿" ×10000 |

**已知口径差异（报告中注明，不强行对齐）**：
- 兴业/浦发不披露零售分部损益表 → 零售营收/利润/减值显示"-"
- 平安私行门槛 600 万 < 招商 1000 万 → 私行口径不可直接对比
- 财富管理中收各行披露口径有差异

## 五、关键指标名映射（防字段错位）

| 数据库字段 | standard/text 实际指标名 |
|-----------|------------------------|
| 零售分部信用减值损失 | `零售分部信用减值损失`（带"分部"，非"零售信用减值损失"） |
| 零售AUM | text `零售AUM` 或 `零售AUM规模`（招商用"零售AUM"） |
| 私行AUM | text `私行AUM` / `私行客户AUM` |
| 零售客户数 | text `个人客户数` |
| 私行客户数 | text `私人银行客户数` |
| 全行业务费用 | standard `全行业务费用`（RANK_FIELDS 必须含此项） |

> 映射表在 benchmark-analyst 重建数据库时使用；提取阶段指标名以 skill 的 metrics-yaml 为准。

## 六、质量门控清单（主理人 P5 交付前逐项核对）

- [ ] 三份 PDF 存在且页数 ≥ 10（同业财报分析 ≥ 12 / 战略洞察 ≥ 12 / 治理分析 ≥ 18）
- [ ] `data/benchmark_database.json` schema=benchmark-v1.0、`by_bank` 覆盖全部参与银行
- [ ] 排名表参排字段每家都有值（真实未披露除外，WARN 注明）
- [ ] insight_result.json：5 条洞察、20/20 PASS、组织架构字段非空
- [ ] strategy_governance_result.json：phase1-4 齐全、≥1 摇摆点、3 类建议
- [ ] 报告含"信息来源"章节 + 口径说明
- [ ] 无模拟数据残留、无无来源结论
