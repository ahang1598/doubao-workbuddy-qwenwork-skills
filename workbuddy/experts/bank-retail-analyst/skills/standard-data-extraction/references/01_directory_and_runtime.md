# Skill 1 · 附录 01：目录约定、打包结构与运行时临时脚本规约

> **触发阅读条件**：首次使用本 Skill、调整路径/release.py 相关逻辑、需要写/清理临时脚本时。

## 1. 目录约定（所有 Skill 共享）

本 Skill 系列（Skill 1~5 + cninfo-bank-reports）**不再把配置/数据/输出放在仓库里**，统一落到用户主目录：

```
~/RetailAnalysis/              # 默认 Home；可通过环境变量 RETAIL_ANALYSIS_HOME 覆盖
├── config/                    # 全局共享配置（降级兜底）
│   ├── banks.yaml
│   ├── metrics.yaml
│   ├── calibration_rules.yaml
│   ├── warning_rules.yaml
│   ├── sources.yaml
│   └── output_format.md
├── data/                      # 运行时数据
│   ├── reports/               # 财报 PDF（cninfo-bank-reports 产出）
│   ├── extracted_text/        # 文档解析产物（按银行分目录）
│   ├── partial/               # 单次 (bank × period) 抽取落盘
│   ├── standard/              # Skill 1 主输出：<bank>.json
│   ├── text/                  # Skill 2 主输出：<bank>.json
│   ├── benchmark_database.json   # Skill 3 历史数据库
│   └── insight_result.json       # Skill 4 输出
├── output/                    # 最终报告
├── logs/                      # 各 Skill 运行日志
└── work/                      # 临时工作目录（coarse.json / bundles / extraction）
```

## 2. 本 Skill 打包结构

pack/publish 前由 `scripts/release.py` 从 `shared/config-sources/` 生成，运行时优先于全局 config/：

```
skills/skill1-standard-data-extraction/
├── config/                    # Skill 1 本地配置副本（由 shared/config-sources 生成，优先读取）
│   ├── banks.yaml             # 银行列表
│   ├── metrics.yaml           # 指标字典
│   └── calibration_rules.yaml # 口径映射规则
├── .env                       # 腾讯云密钥（不迁入 Home）
└── scripts/
    ├── paths.py               # 共享路径模块副本（由 release.py 自动同步，勿手改）
    ├── coarse_filter.py
    ├── extract_standard_metrics.py
    ├── fine_extractor.py
    ├── merge_partials.py
    └── tencent_doc_parser.py
```

**zip 打包自包含**：本 Skill 作为独立产物（zip）分发时，`scripts/paths.py` 必须随包进入 zip。`release.py` 在 pack/publish 前会自动把仓库根 `scripts/paths.py` 同步到本 Skill 的 `scripts/paths.py`。**开发期仅需修改仓库根那一份**；如需手动触发同步，执行 `python scripts/release.py --sync-paths`。

**配置查找顺序**：CLI `--metrics-yaml` → `$RETAIL_ANALYSIS_CONFIG_DIR/skill1/metrics.yaml` → Skill 自带 `config/metrics.yaml`。配置缺失立即失败，不读取 `~/RetailAnalysis/config/`。prepare 会把配置来源、绝对路径和 SHA-256 写入 `manifest.json`，merge 必须使用同一指纹。

**DocParse 完整性要求**：`extract_standard_metrics.py prepare` 阶段会自动检查 MD 是否包含"经营分部信息"等附注章节。若缺失会在 manifest.json 中写入 `md_completeness_warnings` 并打印告警。建议重跑 DocParse 确保附注章节完整。

**跨 bundle 交叉引用**：`fine_extractor.py build_bundles` 完成后会自动检查分部报告 bundle 中是否有利润表 candidate。若缺失，会从风控指标/收费指标 bundle 中提取利润表 candidate 补充到分部报告 bundle，以支持"全行信用减值损失"等利润表字段的兜底提取（所有银行通用，不再仅限某一家银行）。

## 3. `data/extracted_text/` 命名与分组规范

> **重要**：DocParse 产物必须按银行分组，且银行命名必须与 `standard/`、`text/`、`partial/` 保持一致，统一使用 `banks.yaml` 中定义的 `short_name`（中文简称）。

- DocParse zip：`~/RetailAnalysis/data/extracted_text/<bank_key>/<bank_key>_<period>_docparse.zip`
- DocParse 解压目录：`~/RetailAnalysis/data/extracted_text/<bank_key>/<bank_key>_<period>/`
- 目录中的主 Markdown：建议命名为 `<bank_key>_<period>_md_full.md`
- OCR 页文件：建议命名为 `<bank_key>_<period>_ocr_page{N}.json`
- 例：`~/RetailAnalysis/data/extracted_text/某某/某某_2025年度_docparse.zip`
- 例：`~/RetailAnalysis/data/extracted_text/某某/某某_2025年度/`

**禁止**继续把以下内容平铺在 `~/RetailAnalysis/data/extracted_text/` 根目录：
- `*_md_full.md`
- `*_ocr_page*.json`
- `images/`
- `citic_2025_annual/`、`cmb_2024_annual/` 这类 legacy 英文目录

已有历史散乱目录可用仓库根脚本整理：

```bash
python scripts/organize_extracted_text.py --apply
```

## 4. 运行时临时脚本命名与清理约束（全 Skill 统一）

> **本约束适用于所有 Skill（Skill 1~5 + cninfo-bank-reports），用于版本化管理"一次性辅助脚本"，防止仓库被运行时产物污染。**

### 4.1 何为"运行时临时脚本"

凡符合以下任一特征者，均视为运行时临时脚本：

- Agent/SubAgent 为完成单次任务而临时撰写的 Python/Shell 脚本（如：某银行某年份单次补提、某指标一次性回填、某个 PDF 一次性切分）
- 多版本迭代的调试脚本（如 `foo_v1.py` / `foo_v2.py` / `foo_fix.py`）
- 仅为生成某张图/某个 PDF 被"即兴写出来"的脚本
- 解决单次数据异常的"补丁脚本"

反之，**以下脚本不是临时脚本**（属于正式工具，必须沉淀到 `skills/<skill>/scripts/` 并纳入版本管理）：

- 被 SKILL.md 流程明确引用的主编排/提取/合并脚本（如 `prepare_text_extraction.py`、`extract_standard_metrics.py`、`merge_partials.py`、`paths.py`）
- 可被多次、多银行、多年份复用的批处理脚本（如 `batch_docparse.py`、`batch_prepare_text.py`）
- `scripts/release.py` 等工程化工具

### 4.2 强制命名规范

所有运行时临时脚本**必须**使用统一前缀：

```
_runtime_generate_<用途>_<时间戳或可读标识>.py
_runtime_generate_<用途>_<可读标识>.sh
```

**示例**：

- ✅ `_runtime_generate_revenue_trend_pdf_20260428.py`
- ✅ `_runtime_generate_patch_bankA_2024.py`
- ❌ `analyze_org_changes.py`（无前缀，违规）
- ❌ `fix_bankA.py`（无前缀，违规）

### 4.3 落盘位置

| 位置 | 是否允许 | 说明 |
|------|---------|------|
| `~/RetailAnalysis/work/_runtime_generate_*.py` | ✅ 推荐 | 临时工作目录，随时可清理 |
| `~/RetailAnalysis/data/partial/_runtime_generate_*.py` | ✅ 允许 | 与单次提取产物共存 |
| `~/RetailAnalysis/scripts/_runtime_generate_*.py` | ⚠️ 不推荐 | 用户主目录脚本区，仅在需要跨会话调试时使用 |
| `skills/**/scripts/_runtime_generate_*.py` | ❌ 严禁 | 会进入 zip 发布包、镜像目录，污染产物 |
| `scripts/_runtime_generate_*.py`（仓库根） | ❌ 严禁 | 同上 |

### 4.4 生命周期（执行闭环）

```
① 生成脚本 → 使用 _runtime_generate_ 前缀 + 落盘到 work/ 或 partial/
         ↓
② 执行脚本 → 产出数据/报告到 data/ 或 output/
         ↓
③ 完成验收 → 用户确认结果或主 Agent 汇总后
         ↓
④ 主动删除 → 调用 delete_file 或 os.remove() 删除该 _runtime_generate_ 脚本
         ↓
⑤ 沉淀判断 → 如该逻辑被反复构造、稳定可复用，主动向用户提出是否固化为正式脚本
```

### 4.5 兜底机制

- **`.gitignore` 已配置**：`_runtime_generate_*` / `**/_runtime_generate_*` 全局忽略，防止误提交
- **清理工具**：`python scripts/cleanup_runtime_scripts.py [--dry-run]`
- **Release 前置检查**：`scripts/release.py` 在打包 zip 前会检查是否存在 `_runtime_generate_*`，存在即报错终止
