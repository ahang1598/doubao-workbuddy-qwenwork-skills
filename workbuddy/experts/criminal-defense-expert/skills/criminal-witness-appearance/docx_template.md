# DOCX 模板：证人出庭作证申请书

> criminal-witness-appearance | F-Strict 模板 | v3.2.0
>
> 本模板定义证人出庭作证申请书的 DOCX 渲染骨架，供 python-docx 引用。
> L3 类型规格卡：`base/rule/format-docx/types/application/T-witness-appearance.md`

---

## 1. 组件序列

| 顺序 | 组件ID | 组件名称 | 内容 | 格式 |
|------|--------|---------|------|------|
| 1 | C-court-header | 标题 | "关于{defendant_name}涉嫌{alleged_crime}一案证人出庭申请书" | 方正小标宋简体 22pt 居中 加粗 |
| 2 | C-court-greeting | 致送机关 | "{court_name}：" | 仿宋_GB2312 16pt 顶格 |
| 3 | C-party-info | 申请人信息 | "申请人：{lawyer_name}，{law_firm}律师，执业证号{license_no}，系{defendant_name}涉嫌{alleged_crime}一案中{defendant_name}的辩护人。" | 仿宋_GB2312 16pt 两端对齐 |
| 4 | C-claim-list | 申请事项 | "申请事项：准许证人{witness_name}出庭作证。" | 仿宋_GB2312 16pt 两端对齐 首行缩进2字符 |
| 5 | C-fact-reason | 事实与理由（三重论证） | ARG-1+ARG-2+ARG-3 三段 | 仿宋_GB2312 16pt 两端对齐 首行缩进2字符 |
| 6 | C-conclusion | 结论段 | "综上，……恳请贵院依法通知其出庭作证。" | 仿宋_GB2312 16pt 两端对齐 首行缩进2字符 |
| 7 | C-zhici-block | 此致 | "此致" + 换行 + "{court_name}" | "此致"首行缩进2字符；法院名顶格 |
| 8 | C-signature-block | 落款 | "申请人：{signature}" + 换行 + "{law_firm}" | 仿宋_GB2312 16pt 右对齐 |
| 9 | C-date-block | 日期 | "{date}" | 仿宋_GB2312 16pt 右对齐 |

---

## 2. 事实与理由段（C-fact-reason）三重论证模板

### 2.1 ARG-1 证明必要性

```
一、证人{witness_name}的证言对证明{defendant_name}的{dispute_fact}具有关键作用，
对定罪量刑有重大影响。{evidence_reference}
{contradiction_analysis}
{reverse_argument}
[注：刑诉法第{article_192}条]
```

**占位符说明**：
- `{dispute_fact}`：具体争议事实（如"主观故意""正当防卫"）
- `{evidence_reference}`：证据引用（卷宗页码/证言编号）
- `{contradiction_analysis}`：证言与其他证据的矛盾分析
- `{reverse_argument}`：反面论证——为什么仅凭书面证言不够

### 2.2 ARG-2 证明目的

```
二、证人{witness_name}出庭所要证明的具体事实为{testified_fact}，
该事实对本案{defense_direction}具有直接支撑作用。
[注：刑诉法第{article_192}条]
```

**占位符说明**：
- `{testified_fact}`：待证事实（具体、明确、与辩护策略呼应）
- `{defense_direction}`：辩护方向（如"正当防卫辩护""无罪辩护"）

### 2.3 ARG-3 出庭可行性

```
三、证人{witness_name}具备出庭条件，不属于刑诉法第193条规定的正当理由
不能出庭的情形。{feasibility_details}
{protection_measures_if_any}
[注：刑诉法第193条{+刑诉法解释第91条_if_video}]
```

**占位符说明**：
- `{feasibility_details}`：可行性细节（健康/居住地/意愿）
- `{protection_measures_if_any}`：保护措施申请（如需）
- `{+刑诉法解释第91条_if_video}`：视频作证时附加引用

---

## 3. 证人类型变体路由

| witness_type | ARG-1 法条 | ARG-2 重点 | ARG-3 补充 |
|--------------|-----------|-----------|-----------|
| 证人 | 第192条第1款 | 亲身感知的具体事实 | 身体健康+居住地+意愿 |
| 鉴定人 | 第192条第3款 | 鉴定意见的异议点 | 鉴定人出庭义务（拒不出庭→鉴定意见排除） |
| 侦查人员 | 第192条第2款 | 取证合法性争议 | 执行职务目击犯罪情况 |
| 有专门知识的人 | 第197条第2-3款 | 鉴定意见的专业疑问 | 专家资质+费用承担说明 |

---

## 4. 保护措施附加段（如需）

当证人存在安全顾虑时，在ARG-3后附加：

### 4.1 第64条特定犯罪类型（涉黑/毒品/恐怖活动/危害国家安全）

```
关于证人保护措施：本案系{crime_type}案件，属于刑诉法第64条规定的特定犯罪类型。
证人{witness_name}因作证面临人身安全危险，根据刑诉法第64条，恳请贵院对证人
采取以下保护措施：
（一）不公开真实姓名、住址和工作单位等个人信息；
（二）采取不暴露外貌和真实声音的出庭方式；
（三）禁止被告人及其关联人员接触证人及其近亲属；
（四）对人身和住宅采取专门性保护措施。
```

### 4.2 普通刑事案件

```
关于证人保护措施：证人{witness_name}因出庭作证存在安全顾虑，恳请贵院
采取以下保护措施：
（一）对证人{witness_name}的个人信息不予公开；
（二）采取不暴露外貌和真实声音的出庭方式。
```

---

## 5. 页面布局参数

| 参数 | 标准值 | DXA 值 |
|------|--------|--------|
| 纸张 | A4 | 11906 × 16838 |
| 上/下/左/右边距 | 3.7/3.5/2.8/2.6cm | 2100/1984/1588/1474 |
| 行距 | 固定值 28 磅 | 560 DXA |
| 首行缩进 | 2 字符 | 640 DXA |

> 详细排版规范见 `references/docx-format-spec.md`

---

*本模板遵循 L3 类型规格卡 `base/rule/format-docx/types/application/T-witness-appearance.md` 的组件清单*
