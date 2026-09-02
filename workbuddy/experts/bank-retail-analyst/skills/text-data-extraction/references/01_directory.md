# Skill 2 · 附录 01：目录约定与文件命名规范

> **触发阅读条件**：首次使用、排查路径问题、调整命名规范时。

## 1. 目录约定（所有 Skill 共享）

本 Skill 系列不再把配置/数据/输出放在仓库里，统一落到用户主目录：

```
~/RetailAnalysis/              # 默认 Home；可通过 RETAIL_ANALYSIS_HOME 覆盖
├── config/                    # 全局共享配置（降级兜底）
├── data/
│   ├── reports/               # 财报 PDF
│   ├── extracted_text/        # 文档解析产物
│   ├── partial/               # 单次 (bank × period) 抽取
│   ├── standard/              # Skill 1 主输出
│   └── text/                  # Skill 2 主输出
├── output/                    # 最终报告
├── logs/                      # 各 Skill 运行日志
└── work/                      # 临时工作目录
```

## 2. 本 Skill 打包结构

pack/publish 前由 `scripts/release.py` 从 `shared/config-sources/` 生成，运行时优先于全局 config/：

```
skills/skill2-text-data-extraction/
├── config/                    # Skill 2 本地配置副本（由 shared/config-sources 生成）
│   ├── banks.yaml             # 银行列表
│   └── metrics.yaml           # 指标字典（text_metrics 部分为主）
└── scripts/
    ├── paths.py               # 共享路径模块副本
    ├── prepare_text_extraction.py   # 编排脚本：prepare / merge
    ├── text_extractor_prompt.md     # SubAgent 子代理契约
    ├── merge_partials.py            # 按银行聚合 partial JSON
    └── legacy/                # 旧脚本归档（不再使用）
```

**配置查找顺序**：CLI `--metrics-yaml` → `$RETAIL_ANALYSIS_CONFIG_DIR/skill2/metrics.yaml` → Skill 自带 `config/metrics.yaml`。配置缺失立即失败，不读取 `~/RetailAnalysis/config/`；prepare 会把配置来源、绝对路径和 SHA-256 写入 `manifest.json`。

## 3. 文件命名规范（所有 Skill 统一）

> **重要**：`text/` 和 `partial/` 的命名必须与 `standard/` 保持一致，使用 `banks.yaml` 中定义的 `short_name`（中文简称）。

**命名规则**：
- `partial/` 文件：`{kind}_{bank_key}_{period}.json`
  - 例：`text_A银行_2021年度.json`、`text_B银行_2022年度.json`
- `text/` 聚合文件：`{bank_key}.json`
  - 例：`A银行.json`、`B银行.json`
- 其中 `{bank_key}` 是 `banks.yaml` 中的 `short_name`（如 `A银行`、`B银行`、`C银行`）
- `{period}` 如 `2021年度`、`2022年度`、`2025H1`、`2025Q3`，**不允许下划线**

**与 `standard/` 的一致性**：
- `standard/` 使用：`A银行.json`、`B银行.json`（✅ 已统一）
- `partial/standard_*.json` 使用：`standard_A银行_2021年度.json`（✅ 已统一）
- `text/` 使用：`B银行.json`、`C银行.json`（✅ 已迁移）
- `partial/text_*.json` 使用：`text_B银行_2021年度.json`（✅ 已迁移）

## 4. `data/extracted_text/` 输入目录规范

> **重要**：本 Skill 读取的 DocParse 产物也必须遵守同一套银行简称规则。

**命名规则**：
- zip：`~/RetailAnalysis/data/extracted_text/<bank_key>/<bank_key>_<period>_docparse.zip`
- 解压目录：`~/RetailAnalysis/data/extracted_text/<bank_key>/<bank_key>_<period>/`
- 主 Markdown：`<bank_key>_<period>_md_full.md`
- OCR 页文件：`<bank_key>_<period>_ocr_page{N}.json`
- 其中 `<bank_key>` 必须是 `banks.yaml` 中的 `short_name`

**示例**：
- `~/RetailAnalysis/data/extracted_text/A银行/A银行_2025年度_docparse.zip`
- `~/RetailAnalysis/data/extracted_text/A银行/A银行_2025年度/`
- `~/RetailAnalysis/data/extracted_text/B银行/B银行_2022年度/B银行_2022年度_md_full.md`

已有历史散乱目录可用仓库根脚本整理：

```bash
python scripts/organize_extracted_text.py --apply
```

## 5. 运行时临时脚本命名与清理约束

> **详细规范见 `skills/skill1-standard-data-extraction/references/01_directory_and_runtime.md` → 第 4 节。**

本 Skill 强制要点：
1. Agent/SubAgent 为单次任务临时撰写的 Python/Shell 脚本，**必须**命名为 `_runtime_generate_<用途>_<时间戳>.py`
2. 落盘位置优先：`~/RetailAnalysis/work/` 或 `~/RetailAnalysis/data/partial/`，**严禁**放入 `scripts/`
3. 任务完成（数据写入 `~/RetailAnalysis/data/text/<bank>.json` 并经用户验收）后，**立即删除**该临时脚本
4. 本 Skill 已沉淀的**正式脚本**不在此列：`prepare_text_extraction.py`、`merge_partials.py`、`batch_docparse.py`、`batch_prepare_text.py`、`paths.py`
5. 兜底：`_runtime_generate_*` 已写入 `.gitignore`；`scripts/cleanup_runtime_scripts.py` 可批量清理
