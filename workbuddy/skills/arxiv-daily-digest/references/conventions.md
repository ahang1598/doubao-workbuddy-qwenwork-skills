# arXiv Daily Digest — 环境约定与已知坑（references）

## 网络路径（实测通用约定）

- 直连 `arxiv.org` 的 TLS 在部分沙箱环境会被 reset；脚本先试直连、失败自动走
  `https://proxy.cors.sh/`（返回未改动的原始 arXiv HTML/PDF，保留 list-comments 里的
  venue 字段，这点对排序至关重要）。
- 所有 curl 必须清空代理环境变量（`http_proxy`/`https_proxy`/`HTTP_PROXY`/`HTTPS_PROXY`/`all_proxy`/`ALL_PROXY` 置空），
  否则可能走不通公网的本地代理。
- Cloudflare 部署阶段：若部署脚本需要，用 `env -u HTTP_PROXY -u HTTPS_PROXY` 禁用本地代理
  （由 deploy_verify.sh 的 `DEPLOY_PROXY_STRIP` 控制，默认开启）。

## Python 运行时（关键）

- **必须用装有 pypdf + PyMuPDF 的虚拟环境 python 运行 enrich_authors.py / augment_authors.py /
  PyMuPDF 脚本**（例如本机隔离运行时里的 venv）。系统 `python3` 若缺包会 import 失败并
  **静默返回空文本**（表现为 `PDF empty`），极具迷惑性。
- pypdf 对部分 arXiv PDF 报 `EOF marker not found` 并提取空文本；此时改用 PyMuPDF：
  `import fitz; fitz.open(path)[0].get_text()`。**先试 fitz 再判定"论文未提供"**。
- **回归测试**：`scripts/test_augment_authors.py` 用 fitz 造合成 PDF、强制 pypdf 抛错，断言 `_pdf_text` 仍经 fitz 兜底返回文本。每次改 `_pdf_text` 后跑一次：`python scripts/test_augment_authors.py`，防止再次静默删掉兜底。

### Windows / 无 venv 环境（2026-11-20 实测）

- 该机器上 **PyMuPDF 装不上**：pymupdf wheel 约 63MB，从 PyPI 下载会 `IncompleteRead` 断流
  （清华镜像则直接 `No matching distribution found`）。**pypdf 是小包，可以装成功**（实测 7.1.1），
  所以 `enrich_authors.py` 在装了 pypdf 后可用，但 `extract_dates.py`（硬依赖 `fitz`）仍不可用。
  系统内也没有 `pdftotext` / `mutool` / `qpdf` 可替代。
- 此时 `enrich_authors.py` 会**长时间无输出并挂死**（它对 arXiv 的 e-print / LaTeX 回退没有超时，
  而 `proxy.cors.sh` 在该网络下返回 000），单篇也会卡住；`extract_dates.py` 因缺 `fitz` 直接不可用。
  **不要反复重试**，改用下面的直连路线。
- 备用方案（已实测可用）：先 `pip install pypdf`（小包能成功），`enrich_authors.py` 就能跑；
  仍缺单位时再走直连 + 纯 Python 提取器。
- 直连 `arxiv.org` 在该网络下**可用**（`/html/<id>v1`、`/pdf/<id>` 均 200），无需走 `proxy.cors.sh`。
- 替代方案：`curl` 直接下载 `/pdf/<id>`，再用**纯 Python 提取器**（zlib 解 FlateDecode 流 + 走 Tj/TJ 操作符，
  用 TJ 里的大负 kern 判空格）解析首页作者块；实现见工作区 `rsi_1120/pdftext.py`，可直接复用。
  注意：pikepdf/压缩 xref（对象流）生成的 PDF 没有 `/Type /Page` 明文对象，此时只能按「文本内容是否含
  标题片段 / 首作者姓氏」在所有内容流里挑页，否则会误取附录页。
- `/tmp` 在 Windows 下 Git-Bash 与 Windows Python 解析到不同目录（前者 `%LOCALAPPDATA%\Temp`，
  后者 `C:\tmp`），脚本间传 PDF 路径时注意统一。
- arXiv HTML 的作者单位为空（`Affiliation: [`）并不代表论文没写单位：HTML 渲染常丢失，
  必须回 PDF 首页取；反之少数论文（LaTeX `\affiliation` 未渲染）确实两处皆空，此时如实标注「原文未标注单位」，
  不得推断。

## 作者/单位提取流水线（Stage 2）

1. `enrich_authors.py <ids...>`：从 arXiv HTML (experimental) 渲染页提取；HTML 渲染普遍不提供单位，
   其 LaTeX/e-print 回退长期失效（arxiv.org/e-print 直连 TLS reset、经 cors.sh 返回 400）——不要指望它补单位。
2. `augment_authors.py <ids...>`：下载 arXiv PDF 首页（经 cors.sh）补单位/邮箱/通讯标记。PDF 存放于 `/tmp/aug_<id>.pdf`。
3. 仍缺失/错标 → 写一次性 patch 脚本直接改 `authors_meta.json`（历史先例 patch_authors_09xx.py）。

### 解析与标记易错点（多批次实测）

- RA-L/ICLR 风格 `*†‡` 常是**单位脚注标记**而非共一/通讯（如某篇 *=Pisa、†=ETH、‡=NVIDIA），
  augment 会误标 `equal`/`corr`，须对照 thanks 脚注原文修正。BMVC/ECCV(LNCS) 中两位作者带同一 `⋆` 才通常是共一。
- 作者块可能不在 PDF 首页而在中间页（如 StarVLA 在 p12，含 †=项目负责人、)=通讯 图例）——首页找不到时全文搜索。
- 机构行可能被污染（垃圾后缀、出版社水印、taxonomy 词句），须人工核对。
- `authors_meta.json` schema（report_style.render_authors 消费）：
  `authors[]` 含 `name / first / equal / corr / affs[int]`；`affiliations` 为 `{"1": "机构"}` **字符串键**字典；`emails[]`。
- **v1 提交日期**：从 PDF 首页 arXiv 侧边戳 `arXiv:<id>v1 [cat] D Mon YYYY` 提取（extract_dates.py）；
  个别 LNCS 模板论文首页无戳 → 从 `https://arxiv.org/abs/<id>` 的 `[Submitted on ...]` 行读取。

## 排序与筛选约定

- 质量代理排序后必须**人工剔除离题关键词命中再取前 10**（历史离题先例：越狱攻击/attacker、
  VLM unlearning、LLM 对齐/RL 综述、医学影像（胸片/放射/EHR/超声）、agentic 文档抽取、
  音视频 LLM 失效分析、多模态搜索智能体、低资源语言、电商、PCB/电路、推荐系统、
  文化梗图理解、文档多跳推理、流式主动学习、RCA 共识、LLM 交互 agent 等）。
- 混合排序无领域配额；批次构成（如 CV 6 / 具身 3 / 3D 1）是自然结果，写入报告 note 说明。
- **窄主题的批次不足**：单日批次对细分主题可能只有个位数命中（实例：2026-11-20 的 509 篇新投稿里
  RSI 主题仅 7 篇）。此时不要凑数，改用 arXiv API 拉近 3~7 天窗口：
  `http://export.arxiv.org/api/query?search_query=all:%22<phrase>%22&sortBy=submittedDate&sortOrder=descending`
  （多条短语查询去重后再人工筛），并在报告 note 里写清「先扫批次、再补窗口」的口径。
- 边界判定参考：文本-视频检索、视频理解/字幕、音频描述等 vision-language 方法论属 CV 在册；
  纯 NLP/推荐/安全对齐/医疗影像剔除。

## 报告生成与样式（Stage 3）

- 样式为**默认浅色模板**，非机器锁定的固定模版：默认样式见 `assets/default_style.css`
  （`report_style.py` 内也内联同一份作为 `DEFAULT_STYLE`）。改版时复制 `default_style.css`
  改色/字体后通过 `build_report.py --style <file.css>` 传入即可，**不要**改 `report_style.py`
  内置常量，也**不要**在 build 脚本里内联 `<style>`。
- 是否发布到 Cloudflare Pages 由用户决定：`build_report.py` 仅在传入 `--url` 时才写入
  `publish/index.html` 并把 URL 塞进页脚；不传 `--url` 时只产出本地 `outputs/arxiv_email_<批次日期>.html`。
- `report_style.render_card` 支持可选 `card["date"]`：meta 行渲染「提交日期：…」纯文本。
- 默认样式下，build 脚本内置样式断言（单一 style 块、hero 渐变、浅色背景、卡片数、页脚 URL）；
  自定义 `--style` 时仅做结构性断言（卡片数、单一 style 块），不检查具体颜色/渐变。
- 产物：`outputs/arxiv_email_<批次日期>.html`；`publish/` 只含 `index.html`（仅发布时生成，先清空再写入）。

## 发布（Stage 4，可选）

- **仅当用户明确要求发布时才执行**。固定 URL、项目名、Basic Auth 用户名/口令、Cloudflare API Token
  **全部由用户/调用方提供**，通过 `deploy_verify.sh` 的参数与环境变量注入，**技能内不写死任何地址或凭据**。
- 调用方式：
  ```bash
  DEPLOY_SCRIPT=<用户的CF部署脚本> CF_PAGES_TOKEN=<Token> \
  BASIC_USER=<用户名> BASIC_PASS=<口令> \
  bash <skill>/scripts/deploy_verify.sh <workspace> <固定URL> <项目名>
  ```
  deploy_verify.sh 会把 Basic Auth 写入临时文件（避免口令进 shell 历史），并通过
  `CF_AUTH_FILE` 环境变量传给部署脚本；`CF_PAGES_TOKEN` 同理经环境变量传递。
- 校验：带凭据 200 且卡片数正确；无凭据 401 属正常。若部署脚本默认用户名非用户指定值，
  临时 auth 文件会正确覆盖它。

## 自动化执行纪律

- 每次执行完毕，逐项核对全部步骤并在最终回复给出「✅ 步骤自检清单」（①步骤名 ②✅/⚠️ ③失败原因与补救）。
- 关键步骤失败不得静默结束；执行 automation 时禁止 AskUserQuestion，按合理默认继续并声明。
