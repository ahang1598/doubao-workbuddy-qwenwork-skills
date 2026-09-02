# Invoice Processing Scripts

本目录为 `invoice-processing` skill 的脚本集合，核心是由 **`run_pipeline.py` 单脚本编排器统一调用**（一次跑完光栅化 → OCR → 金额换算 → 项目匹配 → 远程匹配 → COS 上传 → 组装 `UiReq`）；各子脚本是其内部实现，正常流程 Agent 直接调 `run_pipeline.py` 即可，无需逐脚本调用。

## 脚本清单

| 脚本 | 用途 | 对应 md 说明 |
|-----|------|-----------|
| **`run_pipeline.py`** | **主编排器**：一个 `--input-file manifest.json` 跑完全流程（光栅化→OCR→匹配→上传→组装UiReq），并落盘 `ui_req.json` 供呼起 UI | (见脚本顶部 docstring + SKILL.md「🚀 主编排器」章节) |
| `amount_conversion.py` | 大写金额 → 数值 + 大小写交叉验证 + 输出"分"(`value_cents`) | (见脚本 docstring) |
| `project_matcher.py` | 项目名三级匹配(exact / normalized / substring) → **去重后的 project_id** | (见脚本 docstring) |
| `title_normalizer.py` | 抬头归一化 + **m:n 独占顺序分配** + **提交后剔除已提交项（prune）** | (见 SKILL.md Step 5.4 / Step 6 / 命名步骤「提交票据到远程」) |
| `pdf_to_images.py` | PDF 逐页转 PNG（**支持批量 + 多进程并发**）| (见 SKILL.md Step 2) |
| `local_ocr_batch.py` | **全本地** OCR（脚本内并发，**按需安装**），被 `run_pipeline.py` 统一调用 | (见 SKILL.md「OCR（全本地，run_pipeline.py 内置）」) |
| `cos_batch_upload.py` |票据 PDF **并发上传 COS** + CDN 域名替换 | (见脚本 docstring) |
| `excel_report.py` | 历史独立报表工具；**主流程不再调用** | (见脚本 docstring) |
| `checkpoint.py` | 断点续传进度 | (见 SKILL.md Checkpoint 章节) |

## 统一调用约定

**CLI 格式**：
```bash
python <script>.py --input '<JSON字符串>'
python <script>.py --input-file <path/to/input.json>          # 入参较大时
python project_matcher.py --projects-file <path/to/projects.json> --input '<JSON>'
python title_normalizer.py --candidates-file <path/to/candidates.json> --input-file <path>
```

> ⚠️ **大批量必须走 `--input-file`**：2000 张票据的 JSON 会超出 Windows 8191 字符命令行上限。
> ⚠️ **项目列表必须走文件**：`get_project_list` 实测可返回 1710 条。写临时 JSON 属于"传参手段"，不属于违规。
> ⚠️ **候选池必须走文件**：`list_pending_tickets` 回包可能上千行，直接进 agent 上下文会 token 爆表。

**stdout**：JSON 格式结果
**stderr**：错误信息 / 日志
**exit code**：0 = 成功，非 0 = 失败

## 各脚本要点

### `project_matcher.py` —— 项目名 → project_id

**上游接口为 `get_project_list`**（MCP 工具，返回机构全部项目，与 `application_number` 无关；它**不是**待开票申请候选池）。⚠️ 注意 `page_size`：每页上限 2000，total > 2000 需分页迭代 `page_index`。

**出参新增去重字段**（这是本轮改造的核心）：

| 字段 | 说明 |
|-----|------|
| `distinct_project_ids` | 去重后的项目 ID 集合（保持首次出现顺序）|
| `distinct_count` | ★ **判据就是这个数**，不是命中的项目名条数 |
| `project_id` | 已按规则收敛好，**可直接填进 `filters.project_id`** |

`project_id` 三分支：

| `distinct_count` | `project_id` |
|------------------|--------------|
| `0` | `""` |
| **`1`** | 该 ID |
| `> 1` | `""` |

> ✅ **多个项目名命中同一个 ID 时，去重后是 1 个，应当填入该 ID** —— 不要因为"名字多"就传空。
> ⛔ `> 1` 时严禁任选一个：传错的 `project_id` 在精确匹配下会让本该命中的申请单**直接落空**，比不传更糟。
> ℹ️ `project_id` 对后端是 **nice to have**（有则加严、无则不过滤），传空是安全降级。
> ℹ️ 出参字段名叫 `project_no`，它**就是** `filters.project_id` 要的值 —— 两侧命名不同、语义相同。

**substring 级是需求方明确要求的能力**：OCR 提取的项目名常夹带前后缀（`捐赠项目：乡村教育扶贫计划（2026年度）`），只做精确匹配会丢掉绝大多数项目信号。但归一化后长度 `< 3` 时**跳过** substring（防短串命中海量项目），这个保护必须保留。

### `title_normalizer.py` —— 三个 mode

| mode | 时机 | 作用 |
|------|------|------|
| `normalize` | Step 5.4（送匹配之前）| 输出归一化抬头，供构造 `filters` |
| `allocate` | Step 6（拿到回包之后）| 反向映射 + m:n 独占分配 + 组装 `UiReq` + 一致性断言 |
| `prune` | 「提交票据到远程」步骤 | 剔除已提交项 + 重新组装剩余 `UiReq` |

**归一化只做三类格式层等价变换**：空白折叠 / 全半角统一(NFKC) / 繁转简。

> ⛔ **严禁**截短、去除"深圳市"等前缀、同义替换、去标点。抬头是绑定申请单的凭据，任何实质性变换都可能绑错单。

**m:n 分配规则**：组内 m 张票对 n 个候选行 → 一对一分配 `min(m, n)`；`m > n` 时多出的 `m-n` 张标 `match_status=2`，reason 是**独立文案**「已经有别的票据匹配上了」（不是「匹配不到」）。

**`prune` 的剔除语义**：提交在 UI 内直接完成，UI 回传「已提交成功的 pdf 链接列表」，`prune` 按 `invoice_url` 剔除这些项并写回，供 Agent 据 removed_count / remaining_count 告知"已提交 X 条、剩余 Y 条"（UI 侧已自行刷新展示剩余，不重新呼起 UI）。

**剔除必须由本脚本读盘完成**，不得在 agent 上下文里搬运全量数据。

### `pdf_to_images.py` —— 批量与并发参数

| 入参形态 | 用法 |
|---------|------|
| `pdf_path` + `output_dir` | 单文件（向后兼容）|
| **`items: [{pdf_path, output_dir}]`** | 批量（推荐）|
| **`pdf_paths: [...]` + `output_root`** | 批量，自动分子目录 |

| 参数 | 默认 | 说明 |
|-----|-----|-----|
| `dpi` | `200` | 票据 OCR 推荐 200-300 |
| `workers` | **`8`** | 多进程并发数（设计 D13 的 `P_r=8`）；`1` = 串行；上限 16 |

**批量是省 turn 的关键**：2000 张一张一次调用要 2000 个 turn，一次批量调用只要 1-2 个。

出参新增 `elapsed_ms` / `avg_ms_per_file`，**供耗时预估校准使用**。部分失败不中断其余文件。

> ℹ️ 沙箱不允许多进程时会自动**退回串行**并在 `install_log` 说明，不因并发失败而整体失败。

### `local_ocr_batch.py` —— ⛔ 按需安装，严禁无条件提示

> 本脚本由 `run_pipeline.py` 在**进入 OCR 阶段后**统一调用，所有张数都走本地引擎（不再区分精细/批量）。

| 时机 | 行为 |
|-----|-----|
| 引擎已可用 | **静默使用**，不提示 |
| 引擎缺失 | **此时才**提示并安装 |

> ⛔ **严禁**在会话开始、环境自检（Step -1）阶段调用本脚本做"顺手探测一下环境"的动作 —— 那等于无条件提示安装。本脚本**故意没有** probe-only 模式，从结构上排除这种误用。
>
> ⛔ `requirements.txt` 里**不写** `rapidocr` / `onnxruntime`。进入 OCR 阶段前不应提前下载。
>
> v2.8.2 起，缺失依赖由脚本加进程锁后安装到 `~/.workbuddy/runtimes/invoice-expert/` 的版本化隔离目录；不会覆盖 WB 共享 Python，也不允许 agent 手工拆包安装或并行预装。成功初始化后后续任务直接复用。
>
> v2.8.3 起，PDF 渲染同样使用隔离运行时，`pypdfium2 + Pillow` 一次性检查和安装。Agent 不需要、也不得单独补装 `Pillow`。

| 参数 | 默认 | 说明 |
|-----|-----|-----|
| `workers` | **`4`** | OCR 进程数；实际进程数不超过待处理票据数 |
| `threads_per_worker` | **`2`** | 每个 ONNX Runtime 实例的推理线程数 |
| `lang` | `ch` | 当前启用 PP-OCRv6 small 中文票据模型 |

默认模型为 RapidOCR 3.9.2 + ONNX Runtime + PP-OCRv6 small，正向电子票据关闭方向分类。出参记录 `effective_workers` / `threads_per_worker` / `effective_total_inference_threads` / `model` / `runtime`。

**出参字段**（`title` / `amount_upper` / `amount_lower` / `project_name_raw` / `remarks` / `other_info` / `confidence` / `raw_ocr_text`），下游脚本无需分支判断识别来源。

> ℹ️ 落盘 JSON 里的 `confidence` 是**OCR 识别置信度**（本地引擎固定 `medium`），与已废除的 `match_confidence` **无关**，MUST NOT 用它推导 `match_status`。

安装失败时返回 `error` + `attempted_remediation` + `fallback_hint`，SOP 应据此提高分辨率重试或分多批处理，**严禁静默使用低质结果继续流程**。

### `cos_batch_upload.py` —— 并发上传

> ⚠️ **纯 `requests` 实现**（与 alert-expert 的 `upload_cos.py` 同源），**不依赖 `cos-python-sdk-v5`**。COS 签名由脚本本地用 HMAC-SHA1（hex 摘要）计算，与后端一致。

| 参数 | 默认 | 说明 |
|-----|-----|-----|
| `workers` | **`16`** | 多线程并发（设计 D13 的 `P_u=16`），上限 32 |
| `batch_size` | **`200`** | 自动分批大小；每批上传前校验凭证，过期则重取 `get_org_cos_credential` |
| `credential` | 可选 | 临时凭证；缺省时脚本从 `~/.workbuddy/mcp.json` **自取** `get_org_cos_credential(private=0)` |

- **多文件分批上传**：`files` 一次可传入数百个，脚本按 `batch_size` 切片并自动分批（支持凭证跨周期重取），不会再因凭证过期中断
- 临时密钥由脚本**内部静默自取** `get_org_cos_credential(private=0)`（缺省即自取，⛔ agent 不传 `credential`）；**必须走 `--input-file`**（路径不进命令行历史）
- 对象 key = `{pre_path}/{uuid去横线}.pdf`，不得用用户原始文件名
- CDN 域名替换：`jgpt3-test*` → `test-orgcdn.gongyi.qq.com`；`jgpt3-formal*` → `orgcdn.gongyi.qq.com`；其它前缀保守回退COS 原始域名
- **部分失败不中断**其余上传，失败项单独回报；上传失败的票据**不得**以空 `invoice_url` 进入 `UiReq`
- 出参**不回显任何凭证字段**

>⚠️ **上传时机在呼起UI 之前**（`MatchItem.invoice_url` 是 UI 入参），且**两个列表的全部票据都要上传** —— 未匹配的票用户更需要看原件才知道怎么改。重匹配循环中**复用**已有 URL，严禁同一 PDF 重复上传。

### `excel_report.py` —— 历史可选工具（不在主流程）

> v2.7.0 起，`run_pipeline.py` 不再调用该脚本，安装和处理票据都不会等待 Excel 生成。仅在明确需要离线表格时单独调用。

固定表头（**顺序不得改、不得增删列**）：

```
是否上传 | 票据抬头 | 开票金额（元）| 项目名称 | 匹配状态 | 说明 / 原因 | 申请编号
```

- **排序：未匹配（`match_status=2`）全部排在已匹配之前**，组内按上传顺序
- 输出到**工作区根目录固定文件名** `票据匹配结果.xlsx`，每轮重匹配**覆盖**
- ⛔ 不带时间戳/轮次号后缀；⛔ 不放 `_tmp/`（临时目录会被清理，用户也找不到）
- 生成时机**早于 COS 上传**（上传失败时用户仍有完整对照表）
- 生成后**必须**在对话中告知用户路径，不得静默生成
- ⛔ 表格内容**不得**逐行打进 agent 上下文

> ⚠️ **「开票金额（元）」是全链路唯一用「元」的地方**，其余全是 `uint32` 分。
> 分→元**必须整数运算**（`f"{c//100}.{c%100:02d}"`），**严禁浮点除法**：`33000/ 100` 可能得到 `329.99999999999994`，票据金额出这种误差是事故。
>
> ℹ️ 这**不违反**「严禁自己做元→分换算」铁律 —— 那条禁的是**匹配入参方向**（元→分，必须用 `value_cents`）。这里是**反方向**、属**展示层**、且同样由脚本完成，不是 LLM 心算。

### `checkpoint.py` —— 断点续传

三个 action（提交已改由 UI 内完成，`guard` 不再被引用）：`init` / `mark` / `next`。

阶段**单调递进**，`mark` 只前进不倒退：

```
none → ocr_done → matched → uploaded
```

- 键是 PDF 的 **`md5`**（不是文件路径）—— 用户换目录重传同一份文件仍应识别为"已处理过"
- 进度文件用**原子替换**写入，防写一半被中断

> ⚠️ 重复 OCR / 重复上传会浪费时间。提交完成与否由 UI 回传的「已提交成功 pdf 列表」判定，agent 据此用 `prune` 剔除已提交项。
>
> ⚠️ 官方文档**未说明** `maxTurns` 耗尽后的行为，因此 **MUST NOT 依赖「轮次用完平台会自动提示用户继续」**。续跑能力**完全**由进度文件保证 —— 软着陆返回、被平台截断、用户关客户端，三种中断的续跑路径完全一致。

## 环境依赖

见 `requirements.txt`。

**安装**：
```bash
pip install -r requirements.txt
```

> ⛔ `requirements.txt` **不含** `rapidocr` / `onnxruntime`，它们由 `local_ocr_batch.py` **按需安装**（见上）。

## 单元测试 / 实测

```bash
# 全量单测（49 个用例，无需 pytest 也能跑）
python tests/test_invoice_scripts.py
python -m pytest tests/test_invoice_scripts.py -v      # 有 pytest 时等效

# 光栅化并发 vs 串行实测（自动合成最小合法 PDF，不需要真实票据）
python tests/bench_rasterize.py 20 200        # 20 份, dpi=200
python tests/bench_rasterize.py 100 200
```

> ⚠️ 若本机 `python` 是 Windows Store 存根（`python -c "print(1)"` 无输出），换用真实解释器路径，例如
> `%USERPROFILE%\.workbuddy\binaries\python\versions\<ver>\python.exe`。

## 🔴 两起stdout 实测事故（2026-08-10，改脚本前必读）

本目录所有脚本的对外契约是「**stdout 只有一行 UTF-8 编码的 JSON**」。实测中踩到两个都会让调用方
`json.loads(stdout)` 直接崩、且报错信息完全指不到根因的坑：

| # | 现象 | 根因 | 修复 |
|---|-----|------|-----|
| ① | `JSONDecodeError: Expecting value: line 1 column 1` | `import fitz`会往 **stdout** 打`warning: The 'fitz' API is deprecated...`，混在 JSON 前面 | 各脚本的 `_run_quiet()`（处理期间 stdout 重定向到 stderr）；**并发子进程有独立 stdout fd，父进程的重定向管不到**，所以 `_render_one` / `_init_worker` / `_ocr_images` 内部各自再 `redirect_stdout(sys.stderr)` 一次 |
| ② | `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xbb` | Windows 中文环境下 stdout 是**管道**时默认用 locale 编码（GBK），`ensure_ascii=False` 的中文 JSON 被写成 GBK 字节（实测 `b'\xbb\xf9\xbd\xf0'` = 「基金」） | 每个 `main()` 开头 `sys.stdout.reconfigure(encoding="utf-8")`（stderr 同样处理） |

**症状特征**：脚本自己跑得好好的、退出码 0、文件也生成了，但 agent 说"返回值解析失败"。

**回归守门**：`tests/test_invoice_scripts.py::test_stdout_is_pure_utf8_json` 按**字节**读取 9 条命令的 stdout，
先断言 UTF-8 可解码、再断言 JSON 可解析。⛔ 新增脚本 MUST 加进该用例的 `cases` 列表。

> ⛔ 该用例**不得**用 `subprocess.run(text=True)`：解码失败会表现为 reader thread 崩溃 + `stdout=None`，
> 把真正的断言掩盖成一个莫名其妙的 `TypeError`。

## 开发状态

| 脚本 | 状态 | 实测 |
|-----|-----|-----|
| `amount_conversion.py` | ✅ 已实现（2026-08-08）| 7 个场景全部通过（整元/角分/零/亿/纯角分/交叉一致/交叉冲突）；stdout 纯净性通过 |
| `project_matcher.py` | ✅ 已实现（2026-08-08），✅ 已改造去重输出（2026-08-10）| ✅ 已实测：唯一命中 / 带前后缀子串命中 / **多名同 ID 去重为 1** / 多 ID 传空 / 短串跳过 / 无信号 / `--projects-file` |
| `pdf_to_images.py` | ✅ 已实现（2026-08-08），✅ 已加批量+并发（2026-08-10）| ✅ 已实测：20 份 **1.77x**、100 份 **4.17x**（详见下表）|
| `title_normalizer.py` | ✅ 已实现（2026-08-10）| ✅ 已实测：归一化 8 例 + m:n 分配 4 例 + 五种 reason + prune 剔除已提交 |
| `excel_report.py` | ✅ 历史可选工具，主流程未启用 | ✅ 已实测：表头顺序 / 未匹配排前 / 分→元边界（含 0..20000 全量对比 `Decimal`）/ 连续 3 次覆盖只留1 个文件 |
| `cos_batch_upload.py` | ✅ 已实现（2026-08-10）| ⛔ **待实测**：需真实 COS 临时凭证 |
| `local_ocr_batch.py` | ✅ v2.8.0 切换 PP-OCRv6 small（2026-08-15）| ✅ 3 张真实票据性能实测；正式字段准确率仍需用含完整交款人/金额的扩展样本验证 |
| `checkpoint.py` | ✅ 已实现（2026-08-10）| ✅ 已实测：三阶段递进 / 阶段不倒退 / 续跑分桶 |

### 光栅化并发实测（2026-08-10）

| 样本量 | 串行(workers=1) | 并发(workers=8) | 加速比 | 并发均值 |
|-------|----------------|----------------|-------|---------|
| 20 份 | 1222 ms | 689 ms | **1.77x** | 34 ms/份 |
| 100 份 | 6002 ms | 1440 ms | **4.17x** | 14 ms/份 |

- 后端为 `fitz`（本机已装 PyMuPDF；`pypdfium2` 优先级更高但未安装，故未被选中）
- **样本量越大加速比越高**：Windows 上 `ProcessPoolExecutor` 每个子进程都要重新 `import`，
  20 份时启动开销占比很大，100 份时被摊薄。⛔ 因此**不要**用小样本的加速比去推算大批量耗时。
- ⚠️ 用的是**合成 PDF**（A4 单页 + 一行文本），渲染负载低于真实票据（真实票据含二维码/公章位图）。
  绝对耗时（14~34 ms/份）**必须**用真实样本再校准一次；加速比可直接参考。
