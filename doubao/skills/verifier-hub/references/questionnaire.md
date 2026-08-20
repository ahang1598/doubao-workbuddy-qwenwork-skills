# questionnaire 评分员模式

只有当前工作区里存在 `questionnaire.md`、`rubric_index.yaml`、`run_verifiers.py`
这些文件时才适用。这些脚本由评分 harness 现场铺进工作区，**不在本 skill 包里**。
工作区里没有它们，就按 SKILL.md 的交付前自检流程用 verifier，不要套用这里的工作流。

## 工作区文件

此时当前 session 工作区（`judge_<id>/`）已经由 harness 准备好：

| 文件 | 用途 |
| ---- | ---- |
| `task.md` | 被评估 Agent 当时拿到的任务描述（只读） |
| `trajectory.jsonl` | 被评估 Agent 的完整工具调用轨迹（只读） |
| `artifacts/*` | 被评估 Agent 实际交付的文件（xlsx/pptx/docx/pdf/html…） |
| `ARTIFACT_INVENTORY.txt` | bootstrap 已经预跑了 `verifier file artifact-list artifacts/`，**先 cat 这个**，不要重复跑 |
| `PREFLIGHT.txt` | bootstrap dry-run `verify_questionnaire.py` 的结果，用来确认环境健康 |
| `questionnaire.md` | 你要填的问卷（唯一可写文件） |
| `rubric_index.yaml` | rubric_id → score_labels 的索引（只读） |
| `verify_questionnaire.py` | 自检脚本：填完后必须跑到看见 `OK`（已 `chmod 555`） |
| `fill_rubric.py` | 写盘助手：单条或批量（`--batch-file`）写 questionnaire.md（已 `chmod 555`） |
| `run_verifiers.py` | 批量 verifier 调度：1 次 Bash 调用并行跑 N 个 verifier（已 `chmod 555`） |

## 推荐工作流（4 步）

优先走批量，减少串行等待和重复调用。

1. `cat ARTIFACT_INVENTORY.txt PREFLIGHT.txt task.md questionnaire.md`
   —— 先读预计算清单和静态信息。
2. `python run_verifiers.py --spec /tmp/spec.yaml --output /tmp/evidence.json`
   —— spec 里每条 rubric 一个 entry（`{id, cmd: [<family>, <subcmd>, <args...>]}`），
   harness 并行调度（默认并发 8）。同一子命令要跑多个文件就开多个 entry。
   `evidence.json.results[*].stdout` 就是 verifier 的原始 JSON 信封。
3. `python fill_rubric.py --batch-file /tmp/decisions.yaml`
   —— decisions.yaml 是一个 list，元素为 `{rubric_id, score, rationale}`，一次写完所有 rubric。
   任一条失败只影响它自己，已写盘的保留。
4. `python verify_questionnaire.py`
   —— 看到 `OK: N/N rubrics valid` 即结束。

## `run_verifiers.py` 的 spec 格式

```yaml
- id: hard_0
  cmd: [rubric, check-file-format, artifacts/report.pptx, --expected-ext, .pptx]
- id: hard_1
  cmd: [pptx, list-slides, artifacts/report.pptx]
# 同一个子命令对多个文件 → 多个 entry（并行跑）
- id: soft_3_a
  cmd: [xlsx, assert-value, artifacts/data.xlsx, --sheet, Sum, --cell, B2, --expected, '1234']
- id: soft_3_b
  cmd: [xlsx, assert-value, artifacts/data2.xlsx, --sheet, Sum, --cell, B2, --expected, '5678']
```

输出信封（写到 `--output` 或 stdout）：

```json
{
  "ok": true,
  "concurrency": 8,
  "elapsed_sec": 3.21,
  "results": [
    {"id": "hard_0", "ok": true, "exit_code": 0,
     "stdout": "{\"ok\": true, \"tool\": \"rubric.check-file-format\", \"evidence\": {...}}",
     "stderr": "", "elapsed_sec": 0.42},
    {"id": "soft_3_b", "ok": false, "exit_code": 1,
     "stdout": "...{\"ok\": false, \"error\": ...}", "stderr": "", "elapsed_sec": 0.38}
  ]
}
```

按 `id` 把 `stdout` 里 verifier 信封的 `evidence.quote`（rubric 家族是
`result.evidence_quote`）拷进 decisions.yaml 的 `rationale` 字段。

注意 `exit_code` 为 1 只说明该条 verifier 的 `ok` 是 false，也就是工具本身没跑成；
校验结论不通过属于 `ok: true` + `result.passed: false`，`exit_code` 仍是 0。

## `fill_rubric.py` 批量与单条

```bash
# 推荐：批量
python fill_rubric.py --batch-file /tmp/decisions.yaml      # 文件
python fill_rubric.py --batch-stdin < /tmp/decisions.yaml   # stdin

# 单条（仅在补打补丁时用）
python fill_rubric.py <rubric_id> <score> "<rationale，不少于 30 字>"
python fill_rubric.py <rubric_id> <score> --rationale-file /tmp/r.txt
```

每条 rubric 一次 Bash 的单条链式写法，只在批量确实不合适时用，
例如某条 rubric 必须先读大量 trajectory 上下文、无法提前批量取证。
