# workflow-detail.md

## 一、管线总览

```
用户自然语言输入
      │
      ▼
Phase 1: 输入验证与解析      [L1]
      │ 中间表示（OffenseRecord + CustodyTimeline + SentencingFactors）
      ▼
Phase 2: 法条匹配与引用      [L2]
      │ + [SCRIPT CALL] sentencing_data_retriever.py  ── 地区量刑细则检索
      │ ArticleMap（条文编号→原文摘要→适用条件）+ RegionalSentencingData
      ▼
Phase 3: 宣告刑期计算          [L2]
      │ + 应用 RegionalSentencingData（量刑幅度细化 + 数额档位调整）
      │ 各罪宣告刑（主刑年/月/日 + 附加刑）
      ▼
Phase 4: 羁押折抵计算          [L3]
      │ + [SCRIPT CALL] date_calculator.py  ── 日期精确计算 + 交叉验证
      │ 折抵明细表（折抵天数 + 剩余刑期）
      ▼
Phase 5: 数罪并罚处理          [L3]  [条件：exists_multiple_offenses]
      │ 最终宣告刑
      ▼
Phase 6: 报告组装与质检        [L2]
      │ + [SCRIPT CALL] sentence_validator.py  ── L1 数值范围批量校验
      │ 完整 Markdown 计算报告
      ▼
    输出
```

---

## 二、各 Phase 详细实现

### Phase 1: 输入验证与解析 [L1]

**目标**：将用户自然语言输入转化为结构化中间表示。

**输入**：用户原始输入（自然语言或结构化片段）。

**核心动作**：
1. 提取罪名信息 → `offense_records[]`（每条含罪名名称+法条编号+建议宣告刑）
2. 识别量刑情节 → `sentencing_factors[]`（每条含情节类型+从轻/减轻幅度）
3. 解析羁押日期 → `custody_timeline{}`（拘留日+逮捕日+是否连续+各段起止）
4. 检测是否数罪 → `offense_count > 1 → is_multiple = true`
5. 判断输入完整度 → `completeness_score`（0-100）

**输出**：`StructuredInput { offense_records, sentencing_factors, custody_timeline, is_multiple, completeness_score }`

**门控**：
- 至少1个罪名可识别 → 通过
- 否则 → 追问或拒接（见降级）

**降级触发与动作**：
| 条件 | 动作 |
|------|------|
| 罪名无法识别 | DEGRADED-L3：拒接，"请提供涉嫌罪名（至少一个）" |
| 羁押日期仅知月份 | DEGRADED-L2：追问→仍无→输出概算+标注"±30天偏差" |
| 数罪信息不完整 | 假定单罪 + 标注 |
| 量刑幅度模糊 | 输出区间 + confidence: low |

---

### Phase 2: 法条匹配与引用 [L2]

**目标**：根据罪名类型和羁押信息，匹配适用的刑法条文。

**输入**：`offense_records` + `custody_timeline`

**核心动作**：
1. 确定主刑类型（管制/拘役/有期徒刑/无期徒刑）→ 匹配折抵比例
   - 管制：《刑法》第41条 → 1:2（羁押1日折抵刑期2日）
   - 拘役：《刑法》第44条 → 1:1
   - 有期徒刑：《刑法》第47条 → 1:1
2. 如为数罪，判断并罚适用情形：
   - 判决宣告前发现 → 第69条
   - 判决宣告后发现漏罪 → 第70条
   - 刑罚执行期间又犯新罪 → 第71条
3. 附加规则：
   - 缓刑：《刑法》第73条（考验期）
   - 减刑后最低执行年限：《刑法》第78条第2款
4. **📌 v2.0.0**: 如用户提供 `jurisdiction`，执行地区量刑细则检索：
   - **[SCRIPT CALL] `sentencing_data_retriever.py` — 联网检索代理**：
     - 输入：罪名 + jurisdiction
     - 行为：构造搜索关键词 → agent 执行联网搜索 → 解析搜索结果 → 提取结构化量刑参数
     - 输出：`RegionalSentencingData { baseline_adjustments, range_refinements, threshold_refinements, special_rules }`
     - 降级：无 jurisdiction → 仅使用 P0 全国标准；联网检索无结果 → P0 + confidence: low

**输出**：`ArticleMap { article_id: { text_summary, applicable_condition, offset_ratio } }` + `RegionalSentencingData`（条件触发）

**门控**：
- 法条编号正确（可联网核验）→ 通过
- 法条编号不确定 → 降级

**降级**：DEGRADED-L1：标注"法条编号请律师核实"+ 继续计算

---

### Phase 3: 宣告刑期计算 [L2]

**目标**：基于法定刑区间和量刑情节，计算宣告刑。

**输入**：`offense_records` + `sentencing_factors` + `ArticleMap` + `RegionalSentencingData`（如有）

**核心动作**：
1. 确定法定刑区间（如盗窃罪数额巨大：3-10年有期徒刑）
2. **📌 v2.0.0**: 应用量刑来源优先级（P2 > P1 > P0）：
   - 优先使用用户明确提供的幅度（P2）
   - 用户未提供 → 使用地区细则中的幅度（P1，如有）
   - 均无 → 使用全国统一参考幅度（P0）
3. 应用量刑情节（自首/立功/从犯/未遂/认罪认罚等从轻减轻幅度）
   - 从轻：在法定刑幅度内从轻
   - 减轻：在法定刑以下处罚
4. 计算宣告刑（基准刑 × (1 − 累计从轻减轻幅度)）
5. 数罪 → 各罪分别计算宣告刑

**输出**：`declared_sentence { main_penalty: {years, months, days}, supplementary_penalty: {...}, source_annotations: [...] }`

**门控**：
- 宣告刑在法定刑区间内（含减轻后下限）→ 通过
- 偏离区间 → 警告

**降级**：DEGRADED-L2：量刑幅度模糊 → 输出区间（min-max）+ confidence: low

---

### Phase 4: 羁押折抵计算 [L3] 🔴

**目标**：计算羁押折抵天数及剩余刑期。**这是最核心的 Phase，1天误差 = 实际的人身自由1天。**

**输入**：`declared_sentence` + `custody_timeline` + `ArticleMap.offset_ratio`

**核心动作**：
1. **📌 v2.2.0**: **[SCRIPT CALL] `date_calculator.py` — 日期精确计算**：
   - 脚本执行：`total_custody_days(segments)` 精确计算羁押总天数
   - **返回双值**：`total_days_inclusive`（含首尾，O3事实描述用）+ `total_days_math`（数学差，折抵计算用）
   - 脚本输出：各段天数（含首尾+数学差）+ 按羁押类型分组 + 闰年标记 + 羁押中断检测
   - LLM 同步推导羁押天数（推理+法条引用）
2. **📌 v2.2.0**: 交叉验证使用**数学差天数**：
   - `cross_validate(llm_days, script_days)` — 建议llm_days和script_days均使用数学差
   - 一致 → confidence: high
   - 偏差 1-2天 → 警告 + 以脚本计算值为准
   - 偏差 ≥3天 → 阻断 + 以脚本计算值为准 + 请核实输入日期
3. LLM 推导羁押天数完毕后，按折抵比例和羁押类型折算
   - **📌 v2.2.0**: 使用 `calculate_offset_days(custody_result, penalty_type)` 自动处理混合类型
   - 羁押+有期徒刑（1:1）：羁押N天 = 折抵N天
   - 羁押+拘役（1:1）：同上
   - 羁押+管制（1:2）：羁押N天 = 折抵2N天
   - 指定居所监视居住+有期徒刑/拘役（2:1）：监视居住N天 = 折抵N/2天
   - 指定居所监视居住+管制（1:1）：监视居住N天 = 折抵N天
4. **📌 v2.2.0**: 月→天换算使用逐月推算：
   - **[SCRIPT CALL] `date_calculator.py::months_to_days`**
   - 脚本执行：`months_to_days(start_date, months)` 按刑诉法解释第202条逐月推算
   - 废弃"30天/月概算"（29个月误差13天）
5. 计算折抵后剩余刑期
   - 剩余天数 = 宣告刑天数（逐月推算）− 折抵天数（数学差）
   - 剩余 ≤ 0 → "羁押已超宣告刑期，应立即释放"
6. **[SCRIPT CALL] `date_calculator.py::calculate_release_date`**:
   - 脚本执行：`calculate_release_date(judgment_date, remaining_days)`
   - 刑期起止日精确推算（跨年/闰年自动处理）
7. **📌 v2.2.0**: 折抵回溯验证：
   - 刑期起算日 = 判决日 − 折抵天数（数学差）
   - 验证：起算日应与首次羁押日重合（连续羁押场景）
   - 不重合 → 标注异常，提示律师核验

**输出**：`offset_detail { segments[], total_days_inclusive, total_days_math, llm_days, script_days, cross_validation, offset_days, remaining_days, start_date, release_date, custody_type_breakdown }`

**门控**：
- LLM 推导天数与脚本计算天数偏差 ≤2天（versus v1.0.0 无脚本交叉验证）→ 通过
- 折抵天数 ≤ 宣告刑天数（不能折出负数）→ 通过
- 折抵回溯验证通过（起算日=首次羁押日）→ 通过
- 否则 → 阻断

**降级**：
| 条件 | 动作 |
|------|------|
| 脚本不可用 | 退回纯 LLM 推理 + confidence: medium |
| 羁押日期不连续 | 分段计算 + 标注各段折抵 |
| 日期仅知月份 | 按月估算 + "±30天偏差" |
| 羁押日期完全缺失 | 切换"纯宣告刑模式" |

---

### Phase 5: 数罪并罚处理 [L3] 🔴 [条件触发]

**目标**：适用数罪并罚规则，计算最终宣告刑。

**触发条件**：`is_multiple == true`

**输入**：各罪 `declared_sentence` + `ArticleMap`（第69/70/71条）

**核心动作**：
1. 判罚并罚情形：
   - 第69条：判决宣告前一人犯数罪 → 总和以下、最高以上
   - 第70条：判决宣告后发现漏罪 → "先并后减"
   - 第71条：刑罚执行期间又犯新罪 → "先减后并"
2. 计算并罚上限：
   - 总和 < 35年 → 最高 ≤ 20年（有期徒刑总和不满35年，最高不能超过20年）
   - 总和 ≥ 35年 → 最高 ≤ 25年
   - 管制 ≤ 3年，拘役 ≤ 1年
3. 推导最终宣告刑

**输出**：`final_sentence { punishment_type, derivation, upper_limit, lower_limit }`

**门控**：
- 最终刑期符合并罚规则 → 通过
- 否则 → DEGRADED-L3 阻断

**降级**：DEGRADED-L3：并罚情形不确定 → 不输出确定值，输出3种情形对照

---

### Phase 6: 报告组装与质检 [L2]

**目标**：组装完整计算报告 + 执行质量检查。

**输入**：Phase 3-5 全部中间输出

**核心动作**：
1. 按 O1→O6 顺序组装输出块
2. 根据条件触发追加 C1/C2/C3
3. **📌 v2.2.0**: **[SCRIPT CALL] `sentence_validator.py` — L1 数值范围批量校验**：
   - 脚本执行：`run_all_validations(calculation_data)`
   - 校验项：
     - ✅ 折抵比例是否匹配主刑类型（1:1 vs 1:2 vs 2:1监视居住）
     - ✅ 数罪并罚上限 ≤ 法定上限（20年/25年）
     - ✅ 剩余刑期 ≥ 0
     - ✅ LLM 推导天数 vs 脚本计算天数交叉验证
     - ✅ 输入字段非空（penalty_type / declared_sentence_months）
     - ✅ **v2.2.0 新增**：月天数换算方法校验（必须"逐月推算"，禁止"30天概算"）
     - ✅ **v2.2.0 新增**：异种主刑并罚处理校验（有期徒刑吸收拘役）
     - ✅ **v2.2.0 新增**：量刑情节竞合校验（累计从轻≤60%、重复评价检查）
   - 注意：法条一致性（法条编号/引文准确性）属于 L2 语义校验，由 LLM 在 Phase 5 和本 Phase 质检中负责，不在脚本校验范围内
4. 执行 LLM 质量检查：
   - 阻断检查项（block）：表格存在/法条依据/日期格式/推导过程/律师必检清单
   - 警告检查项（warning）：法条引用格式/禁止装饰/量刑来源标注完整性
5. 追加"律师必检清单"（O6）
6. 追加免责声明块

**输出**：完整 Markdown 计算报告

**门控**：
- 5项 block 检查全部通过 AND sentence_validator 全部通过 → 输出
- 否则 → 返回修正

**L3 输出校验断言**：
```
□ O3 羁押折抵明细使用 Markdown 表格呈现 → is_pass / is_fail
□ 每步计算标注法条依据 → is_pass / is_fail
□ 日期格式统一为 YYYY-MM-DD → is_pass / is_fail
□ 折抵天数展示推导过程（含LLM:Script交叉验证结果） → is_pass / is_fail
□ 报告末尾包含"律师必检清单" → is_pass / is_fail
□ sentence_validator.py ALL PASS → is_pass / is_fail
```

---

## 三、降级路径总览

| Phase | 降级触发 | 档次 | 动作 |
|-------|---------|------|------|
| 1 | 罪名无法识别 | L3 | 拒接 |
| 1 | 羁押日期仅知月份 | L2 | 概算±30天 |
| 1 | 审理地区缺失 | L1 | 仅用 P0 全国标准 + 标注 |
| 1 | 指定居所监视居住类型不明确 | L2 | 追问"是否为指定居所监视居住"→仍不明确→按一般监视居住不计折抵 |
| 2 | 法条编号不确定 | L1 | 警告继续 |
| 2 | 地区细则联网检索无结果 | L2 | 退回 P0 + confidence: low |
| 3 | 量刑幅度模糊 | L2 | 区间min-max |
| 3 | 量刑情节竞合风险 | L1 | 标注"请核实是否存在重复评价"+ 继续计算 |
| 4 | LLM-Script 天数偏差 ≥3天 | L3 | 阻断 + 以脚本值为准 |
| 4 | 脚本不可用 | L2 | 退回纯 LLM 推理 + confidence: medium |
| 4 | 羁押中断 | L2 | 分段计算+标注 |
| 4 | 折抵回溯验证不通过 | L3 | 阻断 + 标注异常 |
| 5 | 并罚情形不确定 | L3 | 3种情形对照 |
| 5 | 异种主刑并罚 | L1 | 按第69条第2款处理+标注 |
| 6 | 质检不通过 | L2 | 返回修正 |
| 6 | sentence_validator 阻断 | L2 | 返回修正 |

---

## 四、SOFT_DEGRADED 骨架

当 Phase 1 判定信息不完整时，启用 C+D+G 降级输出：

```
[C] 待补充事实：
  - 羁押日期精确到日：缺失 → 影响O3/O4/O5，±30天偏差
  - 审理地区：缺失 → 未检索地区量刑细则，仅使用P0全国标准
  - 地区细则检索结果：无结果 → 退回P0全国标准 + confidence: low
  - 数罪信息完整性：缺失 → 无法执行并罚，按单罪计算
  - 量刑情节幅度：模糊 → 输出区间值
  - 指定居所监视居住类型：不明确 → 按一般监视居住不计折抵
  - 判决日类型：取保后判实刑 → 请提供实际收监日

[D] 治理声明：
  本计算基于有限信息，为辅助参考。
  量刑细则可能因地区而异，建议核实本地细则。
  月→天换算已按刑诉法解释第202条逐月推算（非30天概算）。
  折抵计算使用数学差（end-start），含首尾天数仅用于事实描述。
  最终以法院判决书/执行通知书/释放证明书为准。

[G] 下一步：
  1. 补充精确羁押日期 → 可重新计算精确释放日
  2. 补充审理地区 → 可检索该地量刑细则细化宣告刑
  3. 补充数罪信息 → 可执行数罪并罚计算
  4. 补充指定居所监视居住期间 → 可计算2:1折抵（刑诉法第76条）
  5. 核实量刑情节是否构成重复评价 → 调整累计从轻幅度
  6. 对比不同量刑情景 → 多次调用本技能
```
