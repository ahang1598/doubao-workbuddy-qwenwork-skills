# Skill 1 · 附录 04：Team 并行模式与完整执行示例

> **触发阅读条件**：需要处理 ≥ 2 个 `(银行 × 报告期)` 目标、配置 Team、跑完整 pipeline 时。

## 1. Team 并行模式（默认多目标处理方式）

**触发条件**：待提取目标 ≥ 2 个 `(银行 × 报告期)` 组合时，**默认使用此模式**。

**两级并行**：
- **外层并行（跨 bank×period）**：每个 `(bank, period)` 组合作为一个独立 team member
- **内层并行（同一 bank×period 的 7 个 bucket）**：member 按自己的 `fine_tasks.json` 并发 spawn **精筛子代理**（默认并发 3）

**核心思想**：
- `prepare` 阶段（粗筛 + bundle 构造 + `fine_tasks.json`）是纯 Python，快速完成
- `fine` 阶段（LLM 精筛）按 `fine_tasks.json.batches` 分批并发，**每个 bucket 都是独立子代理**
- `merge` 阶段合并 + S2 加总校验，生成 partial JSON
- 主 Agent 负责编排、跨期校验（规则 S1）、跨银行合并

### 1.1 流程

```
Step 0: 解析目标列表 [(bank_i, period_i), ...]
  │
  ├─ Step 1: team_create("skill1-extract")
  ├─ Step 2: 分批 spawn task（每批最多 4 个 member 并发，外层并行）
  │    member 名称规范："s1-{bank简称}-{period简写}"，如 "s1-某某-25ann"
  │    每个 member 独立执行：
  │      a) prepare → $RA/work/<bank>_<period>/{coarse.json, bundles/*.json,
  │         fine_tasks.json, manifest.json}
  │      b) 读 fine_tasks.json，**按 batches 分批、批内并发 spawn 精筛子代理**
  │         （默认并发 3，内层并行；禁止 member 自己顺序处理 bundle）
  │         子代理按 scripts/fine_extractor_prompt.md 输出到
  │         $RA/work/<bank>_<period>/extraction/<bucket>.json
  │      c) merge → $RA/data/partial/standard_<bank>_<period>.json
  │    完成后 send_message 向 main 汇报
  │
  ├─ Step 3: main 等待所有 member 完成
  ├─ Step 4: main 执行跨期校验（规则 S1）
  ├─ Step 5: main 调用 merge_partials.py --kind standard
  │         把 $RA/data/partial/standard_*_*.json 聚合为 $RA/data/standard/<bank>.json
  ├─ Step 6: main shutdown 所有 member + team_delete
  └─ Step 7: 向用户汇报整体结果
```

### 1.2 Member 职责边界

| 归属 | 工作内容 |
|------|---------|
| **Member** | prepare（粗筛+bundle+fine_tasks）→ **读 fine_tasks.json，按 batches 并发 spawn 精筛子代理** → merge（S2 校验）→ 输出 partial JSON |
| **精筛子代理** | 按 `fine_extractor_prompt.md` 契约，针对**单个 bundle**输出单 bucket 的 extraction JSON |
| **Main** | 任务拆分、team 编排、规则 S1 跨期校验、结果合并、对外汇报 |

### 1.3 单任务场景

**1 个目标**：不创建 team，主 Agent 直接：
1. 跑 `prepare`，拿到 `fine_tasks.json`
2. **按 fine_tasks.json.batches 分批、批内并发 spawn 子代理**（默认并发 3）
3. 跑 `merge` 生成 partial
4. 跑 `merge_partials.py` 聚合到 `<bank>.json`

> 即使是单任务，也**必须**走「fine_tasks.json → 子代理并发」路径，不得由主 Agent 顺序读 bundle 自行处理。

## 2. 单目标完整执行示例

以"某某银行 2025 年度"为例，整条流水线（`$RA` 代指 `~/RetailAnalysis`）：

```bash
RA=~/RetailAnalysis

# 1) 腾讯云解析 PDF -> zip
python scripts/tencent_doc_parser.py \
  --file-type PDF \
  --file-path "$RA/data/reports/某某银行/某某_2025年度_年度报告.pdf" \
  --output-zip "$RA/data/extracted_text/某某/某某_2025年度_docparse.zip"

# 2) 粗筛 + 构造精筛 bundle + 生成子代理任务清单
python scripts/extract_standard_metrics.py prepare \
  --bank 某某银行 --period 2025年度 \
  --parse-zip "$RA/data/extracted_text/某某/某某_2025年度_docparse.zip" \
  --work-dir "$RA/work/bankA_2025" \
  --partial-output "$RA/data/partial/standard_某某_2025年度.json" \
  --concurrency 3

# → 产出 $RA/work/bankA_2025/{coarse.json, bundles/*.json, fine_tasks.json, manifest.json}

# 3) 精筛（主 Agent 必须按 fine_tasks.json 的 batches 分批、批内并发 spawn 子代理）
#    - 读 $RA/work/bankA_2025/fine_tasks.json
#    - 对 batches[0] 中的每个 task_id，在一次响应里并发 spawn
#    - 每个子代理使用对应 task 的 spawn_prompt，按 fine_extractor_prompt.md 契约
#      输出到 $RA/work/bankA_2025/extraction/<bucket>.json
#    - 等 batches[0] 全部完成，再处理 batches[1]、batches[2]…

# 4) 合并与校验（写 partial 文件）
python scripts/extract_standard_metrics.py merge \
  --manifest "$RA/work/bankA_2025/manifest.json"

# → 产出 $RA/data/partial/standard_某某_2025年度.json

# 5) 按银行聚合（单期也要做，可重复执行，后续新增期次会自动并入同一文件）
python scripts/merge_partials.py --kind standard --bank 某某

# → 产出 $RA/data/standard/某某.json
```

> **partial 文件命名约定**（必须严格遵守）：`$RA/data/partial/standard_<bank_key>_<period>.json`
> 其中 `<bank_key>` 是简称（如"某某"/"某甲"），`<period>` 如 `2025年度`、`2025H1`、`2025Q3`，**不允许下划线**。

## 3. Step 2 文档解析（腾讯云 lkeap）细节

### 3.1 安装依赖

```bash
pip install -r requirements.txt
```

依赖清单：
- `tencentcloud-sdk-python>=3.0.1334` — 腾讯云官方 SDK（含 lkeap 服务）
- `cos-python-sdk-v5>=1.9.35` — 腾讯云对象存储 SDK
- `requests>=2.31.0` — 下载结果 zip
- `pyyaml>=6.0`

### 3.2 配置 `.env`

在**本 Skill 根目录**放置 `.env`（参考 `.env.example`），路径为
`skills/skill1-standard-data-extraction/.env`，至少包含：

```env
TENCENT_SECRET_ID=你的腾讯云SecretId
TENCENT_SECRET_KEY=你的腾讯云SecretKey
TENCENT_REGION=ap-guangzhou
TENCENT_COS_REGION=ap-guangzhou
TENCENT_COS_BUCKET=你的COS存储桶名
```

> `TENCENT_REGION` 按腾讯云文档仅支持 `ap-beijing` 或 `ap-guangzhou`。
> `TENCENT_COS_BUCKET` 必须是**已创建的**腾讯云 COS 桶。

### 3.3 执行解析脚本

```bash
python scripts/tencent_doc_parser.py \
  --file-type PDF \
  --file-path "~/RetailAnalysis/data/reports/某某银行/某某_2025年度_年度报告.pdf" \
  --output-zip "~/RetailAnalysis/data/extracted_text/某某/某某_2025年度_docparse.zip"
```

内置流程：
1. **上传到 COS**：本地 PDF → `temp_doc_<timestamp>.pdf`（支持最大 100MB PDF）
2. **调用 `ReconstructDocumentSSE`**：SSE 流式接收解析进度，通常 10 秒内完成
3. **下载结果 zip**：流式写入 `--output-zip`，含 Markdown、OCR JSON、图片等完整产物
4. **清理 COS 临时文件**：成功或失败都会自动清理

**常见排查**：
- 启动报 `ModuleNotFoundError: qcloud_cos`：未安装依赖
- 启动报 `缺少必要配置: TENCENT_COS_BUCKET`：`.env` 缺少 COS 配置
- 上传报 `NoSuchBucket`：COS 桶不存在或 region 不匹配
- SSE 长时间无进度输出：检查网络代理，脚本默认不走代理

腾讯云接口文档：
- [文档解析 SSE 接口](https://cloud.tencent.com/document/product/1772/115340)
- [COS Python SDK](https://cloud.tencent.com/document/product/436/12269)

> 规则：文档解析阶段必须优先调用腾讯云文档解析服务，不使用本地 `pdfplumber/PyMuPDF` 作为主路径；本地库仅允许在腾讯云服务不可用时作为临时兜底方案并需显式说明。
