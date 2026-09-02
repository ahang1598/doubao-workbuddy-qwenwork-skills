# Skill 2 · 附录 04：Team 并行模式、子代理契约与完整示例

> **触发阅读条件**：需要处理 ≥ 2 个 `(银行 × 报告期)` 目标、配置 Team、查子代理 prompt 格式时。

## 1. 精筛阶段 fine_tasks.json 结构

`prepare` 阶段已经生成一份**机器可读的子代理任务清单**：

```
$RA/work/text_<bank>_<period>/fine_tasks.json
{
  "bank": "某某银行",
  "period": "2025年度",
  "concurrency": 3,
  "prompt_template": "/abs/…/scripts/text_extractor_prompt.md",
  "extraction_dir": "/abs/…/text_extraction",
  "tasks": [
    {
      "task_id": "s2-fine-某某银行-2025年度-AUM",
      "bucket": "AUM",
      "bundle_path": "/abs/…/text_bundles/bundle_AUM.json",
      "output_path": "/abs/…/text_extraction/AUM.json",
      "batch_index": 0,
      "spawn_prompt": "你是 Skill2 文字指标子代理，…"
    },
    …
  ],
  "batches": [
    ["s2-fine-…-AUM", "s2-fine-…-客户数", "s2-fine-…-财富收入"],
    ["s2-fine-…-信用卡", "s2-fine-…-分部效益", "s2-fine-…-量价"],
    ["s2-fine-…-渠道", "s2-fine-…-其他"]
  ]
}
```

## 2. 强制并行规约（主 Agent / Member 必须遵守）

1. **严禁**主 Agent / Member 自己读 bundle 并在主上下文中抽取 —— 这违反架构铁律
2. **严禁**调用任何 LLM API（腾讯云混元 / OpenAI / …） —— 这违反架构铁律
3. **必须**读取 `fine_tasks.json`，**按 `batches` 顺序**处理，**同一 batch 内并发 spawn** 所有 `task_id`
4. **每个 `task_id` 对应一个独立子代理**，使用该 task 的 `spawn_prompt` 作为 prompt；子代理只负责**单一 bucket**的提取
5. **默认并发度 = 3**；如需调整：`prepare --concurrency N`
6. 所有子代理完成后（`extraction_dir` 下 N 个文件齐全），才能进入 merge

## 3. 宿主适配（CodeBuddy / Cursor / WorkBuddy）

| 宿主 | 子代理调用方式 | 并发实现 |
|------|---------------|---------|
| **CodeBuddy** | `task` 工具，`subagent_name="code-explorer"`（或自定义子代理），`prompt=spawn_prompt` | 在**同一个响应内**把同 batch 的所有 `task` 调用放到同一个 tool call 块 |
| **Cursor** | 右侧 Chat → Agent 模式的「Run in background」或「Spawn parallel agents」，prompt 粘贴 `spawn_prompt` | 同 batch 内为每个 task 各开一个后台 Agent |
| **WorkBuddy** | 并行子任务入口（"新建子任务" / "后台任务"），prompt 粘贴 `spawn_prompt` | 同 batch 内一次性派发所有 task |

**统一效果**：无论哪个宿主，都是「读 `fine_tasks.json` → 外层按 batch 串行 / 内层按 task 并发 → 等待本批完成 → 下一批」。

## 4. Team 并行模式（多目标默认方式）

**触发条件**：待提取目标 ≥ 2 个 `(银行 × 报告期)` 组合时。

**两级并行**：
- **外层并行（跨 bank×period）**：每个 `(bank, period)` 组合作为一个独立 team member
- **内层并行（同一 bank×period 的 8 个 bucket）**：member 按自己的 `fine_tasks.json` 并发 spawn **精筛子代理**（默认并发 3）

### 流程

```
Step 0: 解析目标列表 [(bank_i, period_i), ...]
  │
  ├─ Step 1: team_create("skill2-extract")
  ├─ Step 2: 分批 spawn task（每批最多 4 个 member 并发，外层并行）
  │    member 名称规范："s2-{bank简称}-{period简写}"，如 "s2-某行-25ann"
  │    每个 member 独立执行：
  │      a) prepare → $RA/work/text_<bank>_<period>/{coarse.json,
  │         text_bundles/*.json, fine_tasks.json, manifest.json}
  │      b) 读 fine_tasks.json，**按 batches 分批、批内并发 spawn 精筛子代理**
  │         （默认并发 3，内层并行；禁止 member 自己顺序处理 bundle，
  │          严禁调用任何 LLM API）
  │      c) merge → $RA/data/partial/text_<bank>_<period>.json
  │    完成后 send_message 向 main 汇报
  │
  ├─ Step 3: main 等待所有 member 完成
  ├─ Step 4: main 执行规则 T1 反推校验（需跨期）
  ├─ Step 5: main 执行规则 T3 口径变化关联检索
  ├─ Step 6: main 调用 merge_partials.py --kind text
  ├─ Step 7: main shutdown 所有 member + team_delete
  └─ Step 8: 向用户汇报整体结果
```

### 职责边界

| 归属 | 工作内容 |
|------|---------|
| **Member（bank×period）** | prepare（粗筛 + bundle + fine_tasks）→ **读 fine_tasks.json，按 batches 并发 spawn 精筛子代理** → merge（T2 校验）→ 输出 partial JSON |
| **精筛子代理（bucket）** | 按 `text_extractor_prompt.md` 契约，针对**单个 bundle** 输出单 bucket 的 extraction JSON |
| **Main** | 任务拆分、team 编排、规则 T1 跨期校验、规则 T3 口径变化检索、结果合并、对外汇报 |

> **为何 T1/T3 由 main 执行**：T1 需要跨期数据对比，T3 需要检索全量合并后的口径信息，这类"需要全局视野"的校验不适合放在单个 member 中。

### 单任务场景

**1 个目标**：不创建 team，主 Agent 直接：
1. 跑 `prepare`，拿到 `fine_tasks.json`
2. **按 fine_tasks.json.batches 分批、批内并发 spawn 子代理**（默认并发 3）
3. 跑 `merge` 生成 partial
4. 跑 `merge_partials.py` 聚合到 `<bank>.json`

> 即使是单任务，也**必须**走「fine_tasks.json → 子代理并发」路径，不得由主 Agent 顺序读 bundle / 自行调用 LLM。

## 5. 单目标完整执行示例

以"某某银行 2025 年度"为例：

```bash
RA=~/RetailAnalysis

# 1) 粗筛 + bundle + fine_tasks
python scripts/prepare_text_extraction.py prepare \
  --bank 某某银行 --period 2025年度 \
  --source "$RA/data/extracted_text/某某/某某_2025年度_docparse.zip" \
  --work-dir "$RA/work/text_某某_2025年度" \
  --partial-output "$RA/data/partial/text_某某_2025年度.json" \
  --concurrency 3

# → 产出 $RA/work/text_某某_2025年度/{coarse.json, text_bundles/*.json,
#        text_extraction/, fine_tasks.json, manifest.json}

# 2) 精筛（主 Agent 按 fine_tasks.json 的 batches 分批、批内并发 spawn 子代理）
#    - 读 $RA/work/text_某某_2025年度/fine_tasks.json
#    - 对 batches[0] 中的每个 task_id，在一次响应里并发 spawn
#    - 每个子代理使用对应 task 的 spawn_prompt，按 text_extractor_prompt.md 契约
#      输出到 $RA/work/text_某某_2025年度/text_extraction/<bucket>.json
#    - 等 batches[0] 全部完成，再处理 batches[1]、batches[2]…
#    - **主 Agent 自己不得调用任何 LLM API**

# 3) 合并（含 T2 校验）→ partial
python scripts/prepare_text_extraction.py merge \
  --manifest "$RA/work/text_某某_2025年度/manifest.json" \
  --prior-partial "$RA/data/partial/text_某某_2024年度.json"  # 可选

# → 产出 $RA/data/partial/text_某某_2025年度.json

# 4) 按银行聚合
python scripts/merge_partials.py --kind text --bank 某某

# → 产出 $RA/data/text/某某.json
```

## 6. 设计原则：粗筛 + 精筛（与 Skill 1 一致）

| 阶段 | 执行者 | 职责 | 成本/速度 |
|------|--------|------|----------|
| 解析 | 腾讯云 lkeap | PDF → Markdown | 10 秒级、固定成本 |
| **粗筛** | **Python 规则**（`prepare_text_extraction.py prepare`） | 章节定位 + 段落候选 + bundle + fine_tasks | 毫秒级、零 LLM |
| **精筛** | **SubAgent 子代理**（`text_extractor_prompt.md`） | 按 bucket 结构化提取，含回溯信息 | 秒级、按 bucket 并发 |
| 合并 | Python 规则（`prepare_text_extraction.py merge`） | 汇总、T2 停披校验 | 毫秒级 |
| 跨期校验 | 主 Agent（规则 T1 + T3） | 反推一致性 + 口径变化检索 | 秒级 |
| 按银行聚合 | Python（`merge_partials.py`） | partial → by-bank JSON | 毫秒级 |
