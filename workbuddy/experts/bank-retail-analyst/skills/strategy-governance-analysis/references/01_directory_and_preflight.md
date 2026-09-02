# Skill 5 · 附录 01：目录、首次使用、前置核查、增量执行

> **触发阅读条件**：首次使用、排查路径/preflight 问题、增量升级判断、大文件写入规约。

## 1. 共享 PDF Runtime（已随包内置）

本 Skill 生成 PDF 所需的共享 PDF Runtime 已随包内置在 `_vendor/pdf_report_builder_runtime/`，**发布包无需执行任何初始化命令**。

> 仅仓库开发态需从共享源码重新注入：执行 `python3 scripts/release.py --sync-paths`（发布包中不含此脚本）。

## 2. 目录约定

```
~/RetailAnalysis/              # 默认 Home；可通过 RETAIL_ANALYSIS_HOME 覆盖
├── config/                    # 全局共享配置（降级兜底）
├── data/
│   ├── extracted_text/        # 财报解析产物（董事长致辞/行长报告/组织架构章节检索入口）
│   ├── standard/              # Skill 1 主输出：<bank>.json（资源投向口径）
│   ├── text/                  # Skill 2 主输出：<bank>.json（AUM/客户/财富等投向口径）
│   ├── benchmark_database.json # Skill 3 历史库（长序列财务投向）
│   ├── insight_result.json    # Skill 4 主输出（参考上下文）
│   ├── partial/               # 本 Skill 中间产物（sg_*.json）
│   └── strategy_governance_result.json  # 本 Skill 主输出
├── output/
│   ├── <bank_short>/                      # 按基准行隔离
│   │   ├── strategy_governance_result.json
│   │   ├── strategy_governance_report.md
│   │   ├── strategy_governance_report.html
│   │   └── 战略与治理分析报告.pdf
├── report_assets/             # PDF 生成所需视觉资产（与 skill3/skill4 共享）
└── logs/
```

**本 Skill 本地配置**（pack/publish 前由 shared/config-sources 生成）：

```
skills/skill5-strategy-governance/
├── config/
│   ├── banks.yaml             # 对标银行列表（聚焦"基准行+4家"）
│   ├── cycles.yaml            # 2004 至今五大周期划分
│   ├── leaders_template.yaml  # 历任董事长/行长画像模板
│   ├── key_nodes.yaml         # 关键反事实节点
│   ├── governance_scoring.yaml # 战略韧性评分规则
│   ├── narrative_keywords.yaml # 叙事分析关键词词表
│   └── output_format.md
├── scripts/
│   └── paths.py
└── assets/
```

## 3. 前置核查脚本（Step 0 必跑）

> **必跑说明**：执行本 Skill 任何阶段前，Agent 必须动态生成并执行以下 Bash 脚本做前置体检。输出三段式：① 数据文件就绪度 ② `leaders_template.yaml` 填充度 ③ VIS 资产就绪度。**任一项 `BLOCK` 必须停下来提示用户补齐**。

```bash
#!/usr/bin/env bash
# skill5_preflight.sh —— Step 0 前置核查
set -uo pipefail
ROOT="${RETAIL_ANALYSIS_HOME:-$HOME/RetailAnalysis}"
SKILL_DIR="$(dirname "$(realpath "$0")")"
BANKS=("A银行" "B银行" "C银行" "D银行" "E银行")

echo "=== [1/3] 数据文件就绪度 ==="
for b in "${BANKS[@]}"; do
  [ -f "$ROOT/data/standard/$b.json" ] && echo "OK  standard/$b.json" || echo "WARN standard/$b.json missing (可降级)"
  [ -f "$ROOT/data/text/$b.json"     ] && echo "OK  text/$b.json"     || echo "WARN text/$b.json missing (可降级)"
done
[ -f "$ROOT/data/benchmark_database.json" ] && echo "OK  benchmark_database.json" || { echo "BLOCK benchmark_database.json missing —— 请先跑 skill3"; exit 2; }

echo "=== [2/3] leaders_template.yaml 填充度 ==="
LEADERS="$ROOT/config/leaders_template.yaml"
[ -f "$LEADERS" ] || LEADERS="$SKILL_DIR/config/leaders_template.yaml"
if [ -f "$LEADERS" ]; then
  pending=$(grep -c "<待填>\\|name: \"\"\\|name: $" "$LEADERS" || true)
  total=$(grep -c "^\s*- role:" "$LEADERS" || true)
  filled=$((total - pending))
  ratio=$((filled * 100 / (total > 0 ? total : 1)))
  echo "filled=$filled/$total  ratio=${ratio}%"
  if [ "$ratio" -lt 60 ]; then
    echo "BLOCK leaders 填充度 < 60% —— 请先依据各行年报董事会成员简历补齐再执行"
    exit 2
  fi
else
  echo "BLOCK leaders_template.yaml 不存在"
  exit 2
fi

echo "=== [3/3] VIS 资产就绪度（PDF 交付物可选） ==="
VIS="$ROOT/report_assets"
[ -d "$VIS/logo" ]         && echo "OK  report_assets/logo/"         || echo "WARN vis/logo missing (PDF 降级为纯文档版)"
[ -f "$VIS/vis/palette.json" ] && echo "OK  palette.json"           || echo "WARN palette.json missing"
echo "=== 前置核查完成 ==="
```

**运行输出分级**：
- `OK`：直接放行
- `WARN`：允许继续但必须在最终报告「07 数据窗口与降级说明」章节逐条记录
- `BLOCK`：立即停下，提示用户补齐后重跑

## 4. 降级规则

1. **文本章节缺失**：如某年"董事长致辞"章节未被 Skill 1/2 的 DocParse 抓到，先显式提示用户，并仅对已有年份做叙事分析；**不做插值填充**。
2. **领导画像缺失**：`leaders_template.yaml` 为"需人工一次性维护"的元数据表，首次执行时若发现为空，Agent 应先引导用户根据年报封面与"董事长、行长简历"章节填写任期起止+背景类型。
3. **2004~2014 段数据缺失**：仅 Skill 1/2 口径下的 2015 起数据可用，则输出时明确把"周期一（经济过热）""周期二（四万亿）"降级为"基于年报回溯的文字性判断，无同期数据支撑"。

## 5. 执行工程最佳实践

### 规则 1：大文件禁止单次写入，必须分段 append

**禁用方式**：
- ❌ 单次 `write_to_file` 写入 >8KB 的 md/html
- ❌ `execute_command` 内嵌 heredoc Python 长脚本（命令行 >8000 字节触发系统限制）
- ❌ `replace_in_file` 一次替换 >5KB 的 old_str/new_str

**推荐方式**：
1. **单文件分段写入**：把报告按 8 个章节拆分，每章一次 `write_to_file`
2. **append 策略**：调用一个小脚本 `scripts/append_section.py --file <path> --marker "<!--SEC:XX-->" --content-file <tmp.md>`，逐节追加
3. **Python 脚本落盘**：如需通过 Python 写入，先 `write_to_file` 把脚本写到 `~/RetailAnalysis/data/partial/_runtime_write_section_XX.py`（≤ 400 行），再 `python3 <path>` 执行

### 规则 2：产物分级（MCD vs 完整产物集）

| 分级 | 必须包含 | 允许延后 |
|:--|:--|:--|
| **MCD** | `strategy_governance_result.json`（含摇摆点 + 建议）+ `strategy_governance_report.md`（8 节齐备）| PDF、partial/sg_*.json 中间产物、雷达图 SVG |
| **完整产物集** | MCD + `战略与治理分析报告.pdf` + `partial/sg_*.json`（12 个中间产物）+ HTML | — |

**建议执行顺序**：先保证 MCD 落盘 → 再补齐 PDF → 最后回填 partial 中间产物。

### 规则 3：中间产物必须落盘（partial/sg_*.json）

四阶段每一步的产物必须**立即写 `~/RetailAnalysis/data/partial/sg_<key>.json`**，不要仅存在 Agent 对话上下文里。

**强制清单**（缺一补录即视为违规）：

```
sg_cycle_timeline.json          # 第一阶段 1.1
sg_leader_profiles.json         # 第一阶段 1.2
sg_org_heatmap.json             # 第一阶段 1.3
sg_narrative_matrix.json        # 第二阶段 2.1
sg_consistency_matrix.json      # 第二阶段 2.2
sg_continuity_score.json        # 第二阶段 2.3
sg_scenario_context.json        # 第三阶段 3.1
sg_decision_logic.json          # 第三阶段 3.2
sg_counterfactual.json          # 第三阶段 3.3
sg_board_activity.json          # 第四阶段 4.1
sg_shareholder_impact.json      # 第四阶段 4.2
sg_resilience_score.json        # 第四阶段 4.3
```

## 6. 增量执行与幂等性

> **场景**：Agent 再次执行本 Skill 时，`~/RetailAnalysis/output/<bank_short>/` 下常已存在上一版 md/PDF/JSON。必须按以下流程判断"复用 / 增量升级 / 全量重建"，禁止默认推倒重来。

### 决策矩阵

```
┌─ 存在 strategy_governance_result.json？
│   └─ 否 → 【全量生成】走完整 5-member team + 四阶段流程
│   └─ 是：
│       ├─ 读取 result.json.meta.schema_version
│       ├─ 对比当前 SKILL.md 声明的 schema_version（当前 sg-v1.1）
│       ├─ 版本一致 + 数据源时间戳未变 → 【复用】直接用旧产物
│       ├─ 版本升级（minor）→ 【增量升级】仅重跑变化的阶段
│       └─ 版本升级（major）或数据源有新年份数据 → 【全量重建】
```

### schema_version 约定

- 当前 `schema_version: "sg-v1.1"`
- 升级规则：
  - **patch**：仅修辞性修改 → 复用旧产物，无须重跑
  - **minor**（如 `v1.1 → v1.2`）：新增/调整字段 → 增量回填缺失字段
  - **major**（如 `v1 → v2`）：四阶段分析逻辑变化 → 全量重建

### 增量检测脚本（Step 0.5）

```bash
RESULT="$ROOT/data/strategy_governance_result.json"
if [ -f "$RESULT" ]; then
  OLD_VER=$(python3 -c "import json;print(json.load(open('$RESULT'))['meta'].get('schema_version','unknown'))")
  OLD_TS=$(python3 -c "import json;print(json.load(open('$RESULT'))['meta'].get('generated_at','1970-01-01'))")
  BENCH_TS=$(stat -f "%Sm" -t "%Y-%m-%d" "$ROOT/data/benchmark_database.json")
  echo "旧产物 version=$OLD_VER  generated_at=$OLD_TS  benchmark_latest=$BENCH_TS"
fi
```

### 旧产物结构不符的处理

若旧版 `strategy_governance_report.md` 缺失某个 01~08 节：
- **不得**原地拼接修补（容易丢格式）
- **应当**：按 MCD 流程重生成 md，保留旧 JSON 中可复用的 `phase1/phase2/phase4` 数据，仅重跑缺失阶段

## 7. 执行形态：动态生成脚本

参考 skill1 约定：本 Skill **不预置**分析脚本，Agent 根据 SKILL.md 规则临时撰写一次性 Python 脚本。

- **强制命名前缀**：`_runtime_generate_sg_<用途>_<时间戳>.py`
- 落盘位置：`~/RetailAnalysis/work/` 或 `~/RetailAnalysis/data/partial/`
- 唯一持久化脚本是 `scripts/paths.py`
- **严禁**将 `_runtime_generate_*` 提交到 `scripts/`
- 任务完成后**立即调用 `delete_file` 删除**
- 兜底：`.gitignore` + `scripts/cleanup_runtime_scripts.py`
