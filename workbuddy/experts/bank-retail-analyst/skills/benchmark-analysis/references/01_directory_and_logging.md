# Skill 3 · 附录 01：目录、首次使用、F/G 回填、日志规约

> **触发阅读条件**：首次使用、调整路径、F/G 回填排错、日志不合规排查时。

## 1. 共享 PDF Runtime（已随包内置）

本 Skill 生成 PDF 所需的共享 PDF Runtime 已随包内置在 `_vendor/pdf_report_builder_runtime/`，**发布包无需执行任何初始化命令**。

> 仅仓库开发态需从共享源码重新注入：执行 `python3 scripts/release.py --sync-paths`（发布包中不含此脚本）。

## 2. 目录约定

```
~/RetailAnalysis/              # 默认 Home；可通过 RETAIL_ANALYSIS_HOME 覆盖
├── config/                    # 全局共享配置（降级兜底）
├── data/
│   ├── extracted_text/        # 财报解析产物
│   ├── standard/              # Skill 1 主输出：<bank>.json（本 Skill 输入）
│   ├── text/                  # Skill 2 主输出：<bank>.json（本 Skill 输入，正式合并）
│   ├── partial/               # 本 Skill 中间产物
│   └── benchmark_database.json # 本 Skill 历史数据库（含 standard + text）
├── output/
│   ├── <bank_short>/                    # 按基准行隔离（2026-04-29 新增·强制）
│   │   ├── benchmark_analysis.md
│   │   ├── benchmark_analysis_result.json
│   │   ├── benchmark_analysis_report.html
│   │   ├── 同业财报数据分析.pdf
│   │   └── pdf_check/
│   └── (同上：某甲 / 某乙 / 某丙 / ...)
├── report_assets/             # PDF 生成所需视觉资产
│   ├── by_bank/<bank_short>/   # 按行隔离（logo / vis / brand.yaml）
│   └── legacy/                 # 历史共享资产（向后兼容）
└── logs/
```

**本 Skill 打包配置**（pack/publish 前由 `scripts/release.py` 从 `shared/config-sources/` 生成）：

```
skills/skill3-benchmark-analysis/
├── config/
│   ├── banks.yaml
│   ├── metrics.yaml
│   ├── calibration_rules.yaml
│   ├── warning_rules.yaml
│   └── output_format.md
└── assets/
```

## 3. Text 数据合并 + F/G 类回填规则

**Text 数据合并**：Skill 3 现已正式合并 Skill 2 的文字类数据（AUM、客户数、财富管理收入、信用卡交易量等），写入 `benchmark_database.json` 的 `text:` 前缀字段。

**⚠️ F/G 类效益指标回填规则**：Skill 2 新增的 F 类（分部效益）和 G 类（量价）指标，在 `benchmark_database.json` 中除了写入 `text:` 前缀字段外，**还必须回填到对应的 standard 字段名**（当该 standard 字段为空时）。回填映射表：

| text 字段名 | 回填到 standard 字段名 | 单位换算 | 触发条件 |
|---|---|---|---|
| `text:零售分部营业净收入(文字)` | `零售分部营业净收入` | 亿元 → 百万元（×100） | standard 字段为空 |
| `text:零售分部税前利润(文字)` | `零售分部税前利润` | 亿元 → 百万元（×100） | standard 字段为空 |
| `text:零售非息净收入(文字)` | `零售分部非息净收入` | 亿元 → 百万元（×100） | standard 字段为空 |
| `text:零售信用减值损失(文字)` | `零售分部信用减值损失` | 亿元 → 百万元（×100） | standard 字段为空 |
| `text:个人存款余额(文字)` | `个人存款-合计-时点余额` | 亿元 → 百万元（×100） | standard 字段为空 |
| `text:个人存款成本率(文字)` | `个人存款成本率` | 无需换算（已为 %） | standard 字段为空 |
| `text:零售贷款收益率(文字)` | `个贷贷款收益率` | 无需换算（已为 %） | standard 字段为空 |
| `text:零售贷款不良率(文字)` | `个人贷款-合计-不良贷款率` | 无需换算（已为 %） | standard 字段为空 |

回填时必须在备注中标注"**来自文字段(Skill 2)，非分部报告表格**"。回填**不得覆盖**已有 standard 值。

## 4. 失败/执行日志规约（2026-04-30 强制）

> **目的**：让每一次 Skill 执行（尤其是失败或降级的）都在 `~/RetailAnalysis/logs/skill3/` 留下可追溯的详细记录。**2026-04-30 故障复盘**：之前 logs/ 目录为空，招商报告出现 4 家银行数据空缺时无从追溯。

### 必须记录的内容

每次运行（无论成功或失败）**必须**生成一个日志文件：

```
~/RetailAnalysis/logs/skill3/<session_id>.log
```

其中 `<session_id>` 建议格式：`YYYYMMDD-HHMMSS-<base_bank>-<kind>`，例：`20260430-125800-某甲-benchmark.log`

### 必记事件（缺一即视为日志不合规）

| 事件 | 样例字段 |
|---|---|
| 启动信息 | 时间戳、skill 名、base_bank、kind、环境变量 |
| 每家银行在当期 metrics 总数 / 有值数 / 样本 3 条 | 用于定位"数据解析契约"相关故障 |
| 每次 text→standard 回填 | 字段名、原值、换算后值 |
| 派生指标产出数量 | 按维度统计 |
| 排名参排家数 < 3 的警告 | 指标名、参排家、缺失家 |
| 任何降级（口径降级、数据缺失、模板 fallback） | 触发条件、降级后结果 |
| **任何 exception**（含 traceback） | ⚠️ 必须 `logger.exception()`，不允许 `except: pass` |
| 产物路径与最终 status | success / failed / degraded |

### 落地实现

```python
import logging, sys, datetime, pathlib
sys.path.insert(0, str(pathlib.Path(os.environ.get('RETAIL_ANALYSIS_HOME', Path.home() / 'RetailAnalysis')) / 'scripts'))
from paths import get_skill_log_path

session_id = f"{datetime.datetime.now():%Y%m%d-%H%M%S}-{base_bank}-benchmark"
log_path = get_skill_log_path("skill3", session_id)
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(log_path, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("skill3")
log.info(f"skill=skill3 base_bank={base_bank} log={log_path}")
```

失败时：

```python
try:
    build_report(...)
except Exception:
    log.exception("build_report 失败")
    raise
```

### 禁止事项

- ❌ `logs/skill3/` 目录为空（每次运行至少要有一个 `.log` 文件）
- ❌ 只用 `print()` 不走 `logging`
- ❌ 吞掉异常而不 `log.exception()`
- ❌ 日志写到别的位置（必须落 `~/RetailAnalysis/logs/skill3/`）
- ❌ 失败后删除日志文件（只有成功且无警告的运行可以在 30 天后由清理脚本清除；失败日志永久保留）

## 5. 执行形态：动态生成脚本，用完即走

> ⚠️ 本 Skill 不再预置 `skill3_benchmark_analysis.py` 等固化脚本，已全部移除。

**Agent 根据用户诉求、本 SKILL.md 的规则、现有 `~/RetailAnalysis` 数据状态，临时撰写一次性 Python 脚本并即时执行**。

约束：
1. **统一命名前缀**：`_runtime_generate_<用途>_<时间戳>.py`
2. 落盘推荐：`~/RetailAnalysis/work/_runtime_generate_...` 或 `~/RetailAnalysis/data/partial/_runtime_generate_...`
3. **唯一持久化脚本是 `scripts/paths.py`**
4. **禁止**将 `_runtime_generate_*` 提交到 `scripts/`
5. **完成后主动删除**：用户验收后立即 `delete_file`
6. 如该逻辑被反复构造、逻辑稳定，应**主动向用户提出**是否固化

**为什么这样做**：
- 同业对标分析的核心价值在于**对当下财报的动态理解**，而非对历史脚本的复刻
- 财报口径、VIS 素材、数据库结构每季可能微调，固化脚本会很快与规则漂移
