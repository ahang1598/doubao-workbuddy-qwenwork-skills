---
name: cninfo-bank-reports
description: 从巨潮资讯网（cninfo.com.cn）下载上市银行的年度报告、半年度报告和季度报告。默认采用 Team 并行模式，每家银行由一个独立 team member 负责下载，显著提升多银行批量下载速度。触发关键词：下载银行报告、年度报告、半年报、季度报告、一季报、三季报、巨潮资讯、银行年报、定期报告、批量下载。
category: finance
version: "20260731"
author: 腾讯云商业银行团队
permissions:
  - network   # 访问巨潮资讯网（cninfo.com.cn）下载公开定期报告 PDF
  - file      # 将下载的 PDF 写入 ~/RetailAnalysis/data/reports/
---

## ✅ 能力边界

**能做：**
- 从巨潮资讯网（cninfo.com.cn）批量下载**上市银行**的年报/半年报/一季报/三季报（PDF，均为公开披露信息）
- 按银行名称或股票代码指定下载目标，支持指定年份范围与报告类型
- Team 并行下载多家银行，自动落盘到共享目录 `~/RetailAnalysis/data/reports/`

**不能做（超出范围）：**
- 不下载非上市银行、非银机构或巨潮未收录主体的报告
- 不解析/提取 PDF 内容（属于 standard-data-extraction / text-data-extraction 的职责）
- 不做任何数据分析（属于 benchmark-analysis 等下游 Skill）
- 不访问任何需要登录/付费的数据源，仅抓取公开披露文件

# 巨潮资讯银行报告下载技能

## 📁 目录约定（所有 Skill 共享）

> **重要**：下载的 PDF 默认保存到 `~/RetailAnalysis/data/reports/`（可通过环境变量 `RETAIL_ANALYSIS_HOME` 覆盖）。后续 Skill 1（标准数据提取）、Skill 2（文字数据提取）默认都从这个目录读取 PDF。
>
> ```
> ~/RetailAnalysis/data/reports/
> ├── 某某银行/
> │   ├── 某某_2024年度_年度报告.pdf
> │   └── ...
> ├── 某甲银行/
> └── ...
> ```
>
> **本 Skill 打包配置**（pack/publish 前由 `scripts/release.py` 从 `shared/config-sources/` 生成，运行时优先于全局 config/）：
>
> ```
> skills/cninfo-bank-reports/
> ├── config/                    # 由 shared/config-sources 生成的本地副本
> │   ├── banks.yaml             # 银行列表（下载目标）
> │   └── sources.yaml           # 数据源配置（巨潮资讯网等）
> └── scripts/
> ```
>
> 详细目录约定见各 Skill 的 `SKILL.md` 开头。

从巨潮资讯网批量下载上市银行的**年度报告**、**半年度报告**和**季度报告**（PDF格式）。

**默认采用 Team 并行模式**：多家银行同时下载，每家银行由独立 team member 负责。

## 功能概述

- 支持指定**任意上市银行**（通过银行名称或股票代码）
- 支持指定**年份时间范围**（如 2020–2025）
- 支持**四种报告类型**：年报、半年报、一季报、三季报
- **Team 并行下载**：多家银行各分配一个 team member 同时执行，互不阻塞
- 自动搜索银行的股票代码和 orgId
- 自动跳过已下载的文件，支持断点续传
- 下载完成后汇总所有成员的结果

## 工具要求

- Python 3（标准库即可，无需 pip 安装）
- 网络连接（需访问 cninfo.com.cn）

---

## 使用流程

### 模式选择

| 场景 | 推荐模式 | 说明 |
|------|---------|------|
| 下载 **1 家**银行 | 单任务模式 | 直接顺序执行 Step 1-3 |
| 下载 **2 家及以上**银行 | **Team 并行模式**（默认） | 创建 team，每家银行一个 member 并行下载 |

---

### Team 并行模式（默认，≥2 家银行）

#### Step 0：解析参数

从用户请求中提取：
- **银行列表**：哪些银行需要下载
- **年份范围**：start_year ~ end_year
- **报告类型**：`all` / `annual` / `semi` / `quarterly`
- **保存目录**：默认 `~/RetailAnalysis/data/reports`（遵循全局目录约定）

如果用户说"下载7家股份制银行的年报"，银行列表为：A银行、B银行、C银行、D银行、E银行、F银行、G银行。

#### Step 1：创建 Team

使用 `team_create` 工具创建下载团队：

```
team_create(team_name="cninfo-download")
```

#### Step 2：为每家银行 Spawn 一个 Team Member

使用 `task` 工具为每家银行创建一个独立的 team member，**所有 member 在同一批 tool call 中发出**以实现并行：

```
task(
  subagent_name="code-explorer",  
  name="dl-B",
  team_name="cninfo-download",
  mode="bypassPermissions",
  description="下载B银行报告",
  prompt="""
你负责下载B银行的财报。请按以下步骤执行：

1. 运行搜索脚本获取银行信息：
   python3 {skill_dir}/scripts/search_bank.py --name "B银行" --json

2. 从输出中提取 stock_code、org_id、plate

3. 运行下载脚本：
   python3 {skill_dir}/scripts/download_reports.py \
     --stock-code {stock_code} \
     --org-id {org_id} \
     --start-year {start_year} \
     --end-year {end_year} \
     --save-dir {save_dir} \
     --report-type {report_type} \
     --plate {plate} \
     --bank-name B银行

4. 下载完成后，向 main 发送结果消息，包含成功/失败/跳过的数量和文件列表。
"""
)
```

**并发度限制：最多 4 个 member 同时运行。** 超过 4 家银行时分批执行：先 spawn 一批（≤ 4 个）→ 等待全部完成（通过 `send_message` 汇报）→ 再 spawn 下一批，以此类推。

示例：7 家银行 → 第一批 spawn 4 个 → 等待完成 → 第二批 spawn 剩余 3 个。

当银行数量 ≤ 4 时，在同一个 tool call batch 中同时发出所有 task：

```
# 同一批次同时发出（≤ 4 个时）：
task(name="dl-A", team_name="cninfo-download", ...)
task(name="dl-B", team_name="cninfo-download", ...)
task(name="dl-C", team_name="cninfo-download", ...)
task(name="dl-D", team_name="cninfo-download", ...)
```

#### Step 3：等待结果并汇总

各 member 完成后会通过 `send_message` 向 main 报告结果。Main agent 收集所有结果后：

1. 汇总成功/失败/跳过数量
2. 列出所有下载的文件路径和大小
3. 列出所有失败项及原因
4. 删除 team：`team_delete()`

#### Step 4：展示最终结果

向用户展示汇总表：

```
下载完成汇总（7家银行）：
━━━━━━━━━━━━━━━━━━━━━━━━━━━
银行     成功  失败  跳过
A银行      5    0    2
B银行      5    0    2
C银行      5    1    1
...
━━━━━━━━━━━━━━━━━━━━━━━━━━━
合计      33    2   10
```

---

### 单任务模式（1 家银行）

当只需下载 1 家银行时，直接顺序执行，不需要创建 team。

#### Step 1：搜索银行信息

```bash
python3 <skill_dir>/scripts/search_bank.py --name "<银行名称>" --json
```

#### Step 2：下载报告

```bash
python3 <skill_dir>/scripts/download_reports.py \
  --stock-code "<股票代码>" \
  --org-id "<orgId>" \
  --start-year <起始年份> \
  --end-year <结束年份> \
  --save-dir "<保存目录>" \
  --report-type <all|annual|semi|quarterly> \
  --plate <sse|szse|hk> \
  --bank-name "<银行名称>"
```

#### Step 3：展示结果

---

## Team Member Prompt 模板

每个 member 收到的 prompt 应包含以下完整信息（由 main agent 填充变量）：

```
你负责从巨潮资讯网下载【{bank_name}】的财报。

参数：
- 年份范围：{start_year} ~ {end_year}
- 报告类型：{report_type}
- 保存目录：{save_dir}

执行步骤：

1. 搜索银行信息：
   python3 {skill_dir}/scripts/search_bank.py --name "{bank_name}" --json
   
   从 JSON_OUTPUT 中提取 stock_code、org_id、plate。

2. 下载报告：
   python3 {skill_dir}/scripts/download_reports.py \
     --stock-code <stock_code> \
     --org-id <org_id> \
     --start-year {start_year} \
     --end-year {end_year} \
     --save-dir {save_dir} \
     --report-type {report_type} \
     --plate <plate> \
     --bank-name {bank_name}

3. 完成后，用 send_message 向 main 报告：
   - 银行名称
   - 成功下载数量和文件列表
   - 失败数量和原因
   - 跳过数量（已存在的文件）
```

---

## 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--stock-code` | 股票代码，如 `601818` | 必填 |
| `--org-id` | 巨潮机构ID，如 `9900006246` | 必填 |
| `--start-year` | 起始年份（含） | 必填 |
| `--end-year` | 结束年份（含） | 必填 |
| `--save-dir` | PDF保存目录 | `~/RetailAnalysis/data/reports`（推荐） |
| `--report-type` | `all`全部 / `annual`仅年报 / `semi`仅半年报 / `quarterly`仅季报 | `all` |
| `--plate` | `sse`上交所 / `szse`深交所 / `hk`港交所 | `sse` |
| `--bank-name` | 银行名称（用于文件命名前缀） | 空 |

## 报告类型说明

| 类型 | `--report-type` | 匹配规则 |
|------|----------------|---------|
| 年度报告 | `annual` | 标题含"年度报告"或"年报"，不含"半年" |
| 半年度报告 | `semi` | 标题含"半年度报告"或"半年报"或"中期报告" |
| 季度报告 | `quarterly` | 标题含"第一季度"/"一季报"或"第三季度"/"三季报" |
| 全部 | `all` | 同时下载年报+半年报+季报 |

**季度报告说明：** 一季报通常4月底前发布，三季报通常10月底前发布。不存在独立的"二季报"和"四季报"。

## 排除规则

下载时自动排除：报告摘要、英文版、更新/补充/修订/修正/更正说明。同年份同类型存在多份时取最新一份。

## 注意事项

1. **Team 并行安全**：各 member 下载不同银行的文件到同一目录，文件名以银行名为前缀，不会冲突
2. **巨潮限速**：脚本每次请求间隔 1 秒。多 member 并行时各自独立限速，总体吞吐量线性提升
3. **断点续传**：已存在且大小正常的 PDF 自动跳过
4. **并发度限制**：同一 team 内同一时间运行的 member 不得超过 4 个，超过时分批 spawn（见 Step 2）
5. **失败容错**：单个 member 失败不影响其他 member，最终汇总时标注失败项

## 🧹 运行时临时脚本命名与清理约束

> **详细规范见 `skills/skill1-standard-data-extraction/SKILL.md` → "运行时临时脚本命名与清理约束（全 Skill 统一）"小节。**

1. Agent 为本 Skill 临时撰写的补抓/修复脚本（如"某银行某年份重新下载"的一次性脚本）**必须**命名为 `_runtime_generate_<用途>_<时间戳>.py`
2. 落盘至 `~/RetailAnalysis/work/`，**严禁**提交到 `skills/cninfo-bank-reports/scripts/`
3. 正式脚本 `download_reports.py`、`search_bank.py`、`paths.py` 不在此列，属于版本化工具
4. 任务完成后立即删除临时脚本；兜底有 `.gitignore` 和 `scripts/cleanup_runtime_scripts.py`


## 常见银行信息参考

| 银行名称 | 股票代码 | orgId | 市场 |
|---------|---------|-------|------|
| 中信银行 | 601998 | 9900002721 | sse |
| 招商银行 | 600036 | gssh0600036 | sse |
| 平安银行 | 000001 | gssz0000001 | szse |
| 兴业银行 | 601166 | 9900002081 | sse |
| 浦发银行 | 600000 | gssh0600000 | sse |
| 民生银行 | 600016 | gssh0600016 | sse |
| 光大银行 | 601818 | 9900006246 | sse |
| 工商银行 | 601398 | jjxt0000019 | sse |
| 建设银行 | 601939 | 9900003682 | sse |
| 农业银行 | 601288 | jjxt0000020 | sse |
| 中国银行 | 601988 | jjxt0000028 | sse |
| 交通银行 | 601328 | 9900002841 | sse |
| 华夏银行 | 600015 | gssh0600015 | sse |
| 邮储银行 | 601658 | 9900005091 | sse |
| 北京银行 | 601169 | 9900003642 | sse |
| 江苏银行 | 600919 | 9900006248 | sse |

---

## 金融免责声明

> ⚠️ 本工具下载的财报文件均来自上市银行公开披露信息。工具本身及产出数据仅供研究参考，不构成任何投资建议，亦不构成对任何个股的推荐。投资有风险，决策需谨慎。
