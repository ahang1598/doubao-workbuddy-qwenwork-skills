---
name: arxiv-daily-digest
name_for_model: arxiv-daily-digest
version: 1.0.0
display_name: "arXiv 每日精选"
display_name_en: "arXiv Daily Digest"
description_zh: "从 arXiv 抓取每日新公示论文，按用户主题筛选并质量排序，提取作者排名、单位与联系方式，生成中文 HTML 精选报告（发布到 Cloudflare Pages 为可选项）"
description_en: "Fetch daily arXiv announcements, filter and rank by a user-supplied topic, extract author / affiliation / contact details, and generate a Chinese HTML digest report (Cloudflare Pages publishing is optional)"
description: arXiv 每日精选自动化流水线（可复用技能，不含任何本机/个人隐私信息）。从 arXiv 指定类别抓取最近一天公示的新提交，按用户给定的 topic 关键词筛选，质量代理混合排序取前 N，提取作者排名（一作/共一/通讯）、单位与联系方式，生成中文 HTML 报告。报告样式为可覆盖的默认浅色模板；是否发布到 Cloudflare Pages 由用户决定（可选）。当用户要求“抓取 arXiv 最新论文”、“arxiv 每日精选/日报”、“按某主题生成论文精选报告”或执行 arxiv 主题搜索自动化任务时使用此技能。topic、抓取类别、样式、发布 URL、Basic Auth 与 Cloudflare 凭据均由用户/调用方提供。
agent_created: true
---

# arXiv Daily Digest（arXiv 每日精选流水线）

## Overview

本技能封装一条经过多批次实战验证的四阶段流水线，把 arXiv 最近一天的公示批次转化为一份
带作者/单位/联系方式的中文精选报告。报告样式是**可覆盖的默认浅色模板**（用户可用
`--style` 指定自己的 CSS），是否发布到 Cloudflare Pages 由用户决定（**可选**，不发布时
只生成本地 HTML）。执行前先读 `references/conventions.md`——其中记录了网络路径、运行时、
解析坑位等**非显而易见的关键约定**。

**本技能不携带任何本机路径、用户名或个人隐私数据。** 所有主题范围、样式、发布地址与凭据
均在调用时由用户提供，通过命令行参数或环境变量注入。

## 必填参数（由用户提供，禁止写死）

| 参数 | 说明 | 示例 |
|---|---|---|
| **topic** | 报告主题标签（用于标题、Hero 与页脚说明） | `Embodied AI / Computer Vision / 3D Reconstruction` |
| **cats** | 抓取的 arXiv 类别（逗号分隔） | `cs.CV,cs.RO,cs.GR,cs.AI,cs.LG,cs.MM` |
| **keywords**（可选） | 自定义主题关键词（逗号分隔）；提供后取代内置主题词典 | `robot,manipulation,grasp,embodied` |

## 可选参数（仅在需要发布到 Cloudflare Pages 时提供）

| 参数 | 说明 | 示例 |
|---|---|---|
| **publish url** | Cloudflare Pages 固定访问地址 | `https://your-project.pages.dev` |
| **project name** | Cloudflare Pages 项目名（`--project-name`） | `your-project` |
| **Basic Auth** | 发布站点的访问用户名 / 口令 | 用户自定 |
| **CF 凭据** | Cloudflare API Token（及可选 Account ID） | 用户自定 |
| **deploy script** | 一个支持 `--project-name`、注入 Basic Auth worker、读取 `CF_PAGES_TOKEN`/`CF_AUTH_FILE` 环境变量的 Cloudflare Pages 部署脚本路径 | 用户自定 |
| **style** | 自定义样式表 `.css` 路径；省略则用技能自带的默认浅色模板 | `/path/to/my_style.css` |

## 前置条件

- 工作区（workspace）内已有或能引用以下模块（本技能 `scripts/` 内自带副本）：
  `report_style.py`（默认样式渲染器）、`enrich_authors.py`、`augment_authors.py`。
- Python：解析/排序用任意 python3；**作者提取与 PyMuPDF 相关步骤必须用装有
  pypdf + PyMuPDF 的虚拟环境 python**（直连系统 `python3` 会因缺包静默返回空文本，
  详见 conventions.md 的“静默空文本坑”）。
- 仅在发布时才需要 Cloudflare 凭据，通过环境变量提供：`CF_PAGES_TOKEN`（Cloudflare API Token）、
  `BASIC_USER` / `BASIC_PASS`（站点 Basic Auth）。**不读取任何固定路径的凭据文件。**
- 默认样式见 `assets/default_style.css`；如需改版，复制该文件改色/字体后通过 `--style` 传入，
  **不要**改 `report_style.py` 的内置常量。

## Stage 1 — 抓取、解析与排序（参数化 topic）

```bash
cd <workspace>
python3 <skill>/scripts/run_pipeline.py --tag <MMDD> \
    --cats "cs.CV,cs.RO,cs.GR,cs.AI,cs.LG,cs.MM" \
    --topic "Embodied AI / CV / 3D" \
    --keywords "robot,manipulation,grasp"   # 可选；省略则用内置 embodied/cv/3d 主题
```

产出 `arxiv_parsed_<tag>.json`、`ranked_<tag>.json`、`digest_config_<tag>.json`。
要点：

- 各类别 `/list/<cat>/new`，剔除 Replacement 区，保留 New + Cross-list；直连失败自动走 proxy.cors.sh。
- 输出会打印公示日期分布——**确认批次是“最近一天”**；若日期混杂，停下核实。
- 排序为质量代理混合评分（venue 层级×2.2、基准/数据集贡献、量化实证、规模、主题中心度、跨主题加权），
  **无领域配额**，所有在册论文同池竞争。主题过滤阈值：内置主题默认 ≥3 命中，自定义关键词默认 ≥1 命中（可 `--threshold` 覆盖）。

## Stage 2 — 人工甄别与作者提取

1. 通读 ranked 前 30–55 的标题/摘要/comment，**剔除离题条目**（历史离题先例清单见 conventions.md）。
2. 依剔除后顺序取前 N（默认 10），记录每篇的 venue、themes。
3. 作者提取级联：
   ```bash
   VENV=<装有 pypdf+PyMuPDF 的 python>   # 见前置条件
   $VENV <workspace>/enrich_authors.py <id1> ... <idN> --out authors_meta.json
   $VENV <workspace>/augment_authors.py <缺失单位的id...> --meta authors_meta.json
   ```
4. 仍缺失/错标 → 用 PyMuPDF 抽首页文本人工核对，写一次性 patch 脚本直接改 `authors_meta.json`。
   注意标记误判坑（`*†‡` 可能是单位脚注非共一/通讯），见 conventions.md。
5. v1 提交日期：
   ```bash
   $VENV <skill>/scripts/extract_dates.py <id...> --out submit_dates_<tag>.json
   ```
   个别论文 PDF 无戳 → 从 `arxiv.org/abs/<id>` 的 `[Submitted on ...]` 行补齐，不得留空。

## Stage 3 — 生成报告（样式可选，默认浅色模板）

复制 `<skill>/scripts/build_report.py` 为工作区 `build_<tag>.py`，填写 `SELECTIONS`
（每篇中文 `topic` / `innovations` / `content`），再运行：

```bash
# 仅生成本地报告（不发布）：
python3 build_<tag>.py --tag <MMDD> --date <批次公示日期>

# 自定义样式：
python3 build_<tag>.py --tag <MMDD> --style /path/to/my_style.css

# 需要发布时附带 URL（写入页脚 + 生成 publish/index.html）：
python3 build_<tag>.py --tag <MMDD> --url <用户提供的固定URL> --date <批次公示日期>
```

- 报告标题 / Hero / 页脚说明由 `digest_config_<tag>.json` 的 topic 驱动，**不写死主题标签**。
- 样式：默认采用技能内置浅色模板；传 `--style <file.css>` 则完全使用用户样式表（此时
  脚本只做结构性断言，不检查具体颜色/渐变）。`report_style.render(cards, ctx)` 统一渲染，
  **禁止内联自定义 CSS**（自定义样式请走 `--style` 文件，而非在 build 脚本里写 `<style>`）。
- 产物：`outputs/arxiv_email_<批次日期>.html`；**仅当传入 `--url` 时**才清空并写入
  `publish/index.html`（供 Cloudflare Pages 部署使用）。不传 `--url` 则完全无网络动作。

## Stage 4 — 发布与验证（可选）

只有用户明确要求发布时才执行。需要发布时：

```bash
DEPLOY_SCRIPT=<用户的CF部署脚本路径> \
CF_PAGES_TOKEN=<用户Token> \
BASIC_USER=<用户名> BASIC_PASS=<口令> \
bash <skill>/scripts/deploy_verify.sh <workspace> <固定URL> <项目名>
```

脚本自动部署（原地覆盖同项目）并验证：带凭据 200 且卡片数正确、无凭据 401。
固定 URL 即用户提供的地址（可在 Cloudflare Dashboard - Workers & Pages 管理）。

若用户**不**发布，直接跳到收尾即可——Stage 1–3 已产出本地 HTML 报告。

## 收尾（强制）

1. 最终回复给出「✅ 步骤自检清单」：逐条列出①步骤名②✅/⚠️③失败原因与补救。
2. 若已发布，在回复中给出用户提供的固定 URL 并注明可在 Cloudflare Dashboard 管理；不发送邮件。
   若未发布，说明报告仅生成为本地 HTML（给出路径）。
3. 把执行摘要（批次、入选 ID、修正点、遗留问题）写入 automation 的 memory.md 与工作区每日日志；
   新发现的环境坑沉淀进本技能 `references/conventions.md`。

## Resources

- `scripts/run_pipeline.py` — Stage 1 全流程（fetch → parse → rank），`--tag`/`--cats`/`--topic`/`--keywords` 参数化。
- `scripts/build_report.py` — Stage 3 **模板**：复制后填写 SELECTIONS；`--url` 可选（发布时注入），`--style` 可选（自定义样式），**无任何写死 URL/个人数据**。
- `scripts/extract_dates.py` — 从 PDF arXiv 戳提取 v1 提交日期（PyMuPDF）。
- `scripts/deploy_verify.sh` — Stage 4 部署 + Basic Auth 验证（**仅发布时调用**），URL/项目/凭据全部来自参数与环境变量。
- `scripts/report_style.py` — 默认样式渲染器（`render()` 支持 `ctx["css"]` 覆盖）。
- `assets/default_style.css` — 自带默认浅色模板样式表；改版请复制后用 `--style` 传入。
- `scripts/enrich_authors.py` / `scripts/augment_authors.py` — 作者提取器（工作区副本，实际运行优先用工作区版本，保持最新）。
- `references/conventions.md` — **必读**：网络路径、venv 运行时、PDF 解析坑、标记误判、离题先例、样式/发布约定。
