# 大请求 / 大响应暂存段落模板

按本模板把"Handling Large I/O"段落嵌入目标 SKILL.md 的对应步骤末尾。**按步骤就近嵌入**，不要在 SKILL.md 末尾整体只提一次。

把 `<...>` 占位符替换为本步骤的实际取值。

> **双向暂存**：response_io.py 同时治"请求过大"和"响应过大"两端——
> - **响应端**：`run` 把主脚本 stdout 全量落盘，只回轻量预览，下游用 `read` 投影字段。
> - **请求端**：参数包过大（几百个 ASIN / 长文本 / **直接拿上游落盘文件当入参**）时，用 `run --params-file <路径>` 从文件读参数，避免把大 JSON 塞进命令行 argv + agent 上下文。

---

## response_io.py 的调用契约

`response_io.py` 只有两个子命令：`run` 与 `read`。

`run` 的工作方式：

- **必须有一个"主脚本"**（main script）作为 argv[1] 之外的执行目标，脚本路径由 `--script` 参数显式给出。
- **主脚本约定**：接受 1 个 JSON 字符串作为 `argv[1]`（参数包），把响应原样以 JSON 形式打印到 `stdout`，错误信息打印到 `stderr`。
- **参数包来源二选一**：行内位置参数（小请求直接写 JSON 字符串）**或** `--params-file <路径>`（大请求从文件读，内容不进 agent 上下文）。两者互斥，缺一报错；`--params-file` 内容会先校验是合法 JSON。无论哪种来源，最终都按主脚本约定作为 argv[1] 传入——**主脚本无需改动**。
- response_io.py 会替主脚本捕获 stdout 全文落盘，仅向调用方返回轻量预览（schema + 首条样例 + 文件路径），并在 `--timeout`（默认 300 秒）内强制结束。
- 主脚本失败或超时时，预览中会出现 `_error` 块（含 `exit_code`、`timed_out`、`stderr_snippet`），调用方必须**先看 `_error` 再读 `file`**——失败情况下文件可能为空或不完整。

LinkFox 官方 skill 的主脚本本身就遵循这个约定，可以直接用。第三方工具或不返回 JSON 的命令需要在目标 skill 的 `scripts/` 内补一个 **thin wrapper**：解析 JSON 入参 → 调用真实工具 → 把结果转为 JSON 后 `print` 到 stdout。

### 大请求暂存（--params-file）

何时用：本步骤的请求参数满足以下任一 → 用 `--params-file` 而非行内 JSON：

- 参数含大数组（几百个 ASIN / 关键词 / id）；
- 参数含长文本（整段 prompt、描述、评论拼接）；
- **参数直接来自上游步骤的落盘文件**（典型：S3 落盘 Top20，S4 把这批 ASIN 当入参）——此时不要 `read` 出来再拼字符串，直接把裁剪后的 JSON 写一个参数文件喂给本步。

写法：先把参数 JSON 落到 `<output_dir>/<S(N)>_params.json`（可由上游 `read --format json` 直接投影生成），再：

```bash
python scripts/response_io.py run \
    --script <主脚本路径> \
    --out-dir <output_dir> \
    --label S<N>_<verb> \
    --params-file <output_dir>/S<N>_params.json
```

这样大请求只在磁盘上流转，agent 上下文里只出现一个文件路径。

---

## 段落模板

```markdown
<!-- LF_LARGE_RESPONSE_BLOCK -->
#### 大响应处理（步骤 S<N>）

此步骤返回数据量大（<理由：字段多 / 含数组 / 分页 / 长文本 / 跨步复用>），必须落盘后再读取，避免溢出 agent 上下文。

**1. 执行 + 落盘**

```bash
python scripts/response_io.py run \
    --script <主脚本路径，例如 scripts/<step_N>_<verb>.py 或 LinkFox 官方 skill 自带主脚本路径> \
    --out-dir <output_dir> \
    --label S<N>_<verb> \
    [--timeout 300] \
    '<JSON 参数包，例如 {"asin":"B0XXX","country":"US"}>'
```

主脚本的协议：从 `argv[1]` 接到 JSON 字符串解析参数；把响应以 JSON 写入 stdout；错误写 stderr；非零 exit code 表示失败。

response_io.py 把 stdout 全部落盘到 `<output_dir>/<skill>__<timestamp>__<label>.json`，并向调用方返回**轻量预览**（含 `file` 字段、`shape`、`sample`，必要时含 `_error` 块）。

⚠️ **失败检查**：返回的预览中如果出现 `_error`（exit_code 非 0 / timed_out=true），先读 `_error.stderr_snippet` 排错，落盘文件**可能为空或部分**——不要用空文件做下游决策。

**2. 按需读取字段**

```bash
python scripts/response_io.py read <文件路径> \
    --fields "<field_a>,<field_b>,<field_c>" \
    --format <json|jsonl|csv|table> \
    [--limit N] [--offset M]
```

或用 JMESPath 做复杂投影（需要 `pip install jmespath`）：

```bash
python scripts/response_io.py read <文件路径> \
    --path "<JMESPath 表达式>" \
    --format json
```

**适用本步骤的判定**：<勾选触发的特征：字段数 ≥ 10 / 含数组 / 含分页 / 含长文本 / 跨步骤复用>

⚠️ 预览只是 schema + 截断样例，**不是完整数据**。任何字段级判断必须通过 `read` 从落盘文件读取。
<!-- /LF_LARGE_RESPONSE_BLOCK -->
```

---

## 模板填写指引

| 占位符 | 写法 |
|--------|------|
| `<N>` | 步骤编号，例如 `S2` |
| `<理由：...>` | 选 1–3 条特征写明，例如 `分页 + 长文本（评论）` |
| `<主脚本路径>` | LinkFox 官方 skill 提供的主脚本绝对/相对路径；或本目标 skill 在 `scripts/` 下补的 thin wrapper |
| `<JSON 参数包>` | 主脚本约定的 JSON 字符串。Windows shell 中需用单引号包裹或用文件转入；含双引号时注意转义 |
| `<output_dir>` | 报告输出目录或临时目录，遵循 skill 的入参 |
| `<verb>` | 动词缩写，与脚本命名风格一致，例如 `fetch`、`scan` |
| `<field_a>,<field_b>,...` | 该步骤实际下游消费的字段名 |
| `<JMESPath 表达式>` | 仅在字段裁剪做不到时使用 |

## 第三方工具的 thin wrapper

如果一个步骤要调用 LinkFox 之外的工具（CLI、HTTP API、自有库），写一个 wrapper 放到目标 skill 的 `scripts/<step_N>_<verb>.py`，结构如下：

```python
#!/usr/bin/env python3
"""Thin wrapper for response_io.py: parses JSON argv[1], calls the real tool,
prints JSON to stdout."""

import json
import sys

def main() -> int:
    if len(sys.argv) < 2:
        print(json.dumps({"error": "missing JSON params in argv[1]"}))
        return 2
    params = json.loads(sys.argv[1])

    # ...  调用第三方工具，组装结果
    result = {"data": [...], "meta": {...}}

    print(json.dumps(result, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

理由：response_io.py 只负责"取 stdout、落盘、给预览"。把"调真实工具 + 形态归一"交给 wrapper，response_io.py 才能保持业务无关。

## 注意

- 始终使用**目标 skill 自身的** `scripts/response_io.py`——不是本生成器的、不是某个外部公共脚本。
- 主脚本的 stdout 必须是**整体一个 JSON 值**（或最坏情况下的纯文本——会被当作 raw_text 落盘但失去字段投影能力）。不要混合日志与数据：日志走 stderr。
- 不要为不大的响应也加这块——参考主 SKILL.md 步骤 3 生成产物中的"大数据落盘审视"判定特征。
- 报告生成阶段从落盘文件读取，**不要把原始大响应塞进报告**。
- `--label` 会被清洗到安全字符集（字母数字、下划线、连字符），过长会截断到 64 字符。
- 默认 `--timeout 300` 秒；步骤需要更长时间（如大批量分页），显式调高。
- **请求端同理**：请求参数大就用 `--params-file`，不要把大 JSON 拼进命令行/上下文；行内位置参数与 `--params-file` 互斥。
