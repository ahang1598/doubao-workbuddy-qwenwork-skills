# 子流程三：调用云服务 & 监控 & 交付

> 每次新的 `exec` 使用 PPT 路径前，按 `SKILL.md` 的会话恢复步骤提供该 PPT
> 作业的确切 `PPT_JOB_ID`；缺少 ID 时停止，不得恢复不明确的会话。

> **模型须知**：进入此子流程前必须先完整阅读本文件，再执行任何操作。
> 前置条件：大纲文件已在子流程二中保存至 `$PPT_SESSION_DIR/outline_pre.md`，图片已在子流程二·一中生成替换至 `$PPT_SESSION_DIR/outline.md`。

---

## 步骤一：调用 PPT 生成脚本

**目标**：将用户原始指令、替换图片后的大纲文件路径和图片 URL 列表作为参数，在后台启动 PPT 生成任务（脚本内部自动完成上传）。

> **重要**：将 exec 工具的 `yieldMs` 设置为 `1200000`（20 分钟），`timeout` 设置为 `1200`（20 分钟）再执行此步骤。

```bash
echo "$PPT_SESSION_ID"
echo "$PPT_SESSION_DIR"
PPT_SESSION_ID="$PPT_SESSION_ID"
$PYTHON_CMD "$XIAOYI_PPT_DIR/scripts/generate_ppt.py" \
  "<用户的完整原始指令>" \
  --outline-file "$PPT_SESSION_DIR/outline.md" \
  --image-urls-file "$PPT_SESSION_DIR/image_urls.json" \
  > /dev/null 2>&1 &

PPT_PID=$!
echo "PPT 生成任务已启动"
echo "PID：$PPT_PID"
echo "日志：$PPT_SESSION_DIR/generate.log"
```

**关于命令末尾的 `> /dev/null 2>&1 &`**：
- `> /dev/null` 丢弃 stdout，`2>&1` 把 stderr 也合并到 stdout（一并丢弃），`&` 让任务进入后台并把 PID 写入 `$!`
- **不通过 exec 的 stdout 监控脚本进度**：Python 脚本内部已将结构化进度写入 `$PPT_SESSION_DIR/generate.log`，监控逻辑统一从该日志文件读取
- 这样做避免后台进程被未读取的 stdout 缓冲区阻塞、防止脚本内部输出污染对话上下文

**关于 `<用户的完整原始指令>`**：
- 忠实还原用户的所有需求，包括：主题、页数限制、目标受众、风格偏好、重点内容等
- 不要截断或缩减，完整传递给云端服务

**完成汇报**：
```
✅ PPT 生成任务已启动，开始监控进度...
```

---

## 步骤二：监控进度

**目标**：每 15 秒读取一次日志文件，向用户持续汇报进展。

> **监控原则**：仅使用 `generate.log`，不使用 `kill -0`、`process poll` 等进程探测。
> 必须调用 `monitor_generation.py`；它只认 `generate_ppt.py` 写入的最终标记：
> `[DONE]` 表示生成文件已保存，`[ERROR]` 表示生成失败。严禁以“大纲生成完成”、
> “图片校核完成”或“PPT 全部生成完成”等进度文本终止监控。

### 2.1 监控循环（每 15 秒执行一次，最多 80 次）

监控必须逐轮执行：**每次只运行一次检查命令，读取本轮输出并向用户汇报后，再等待
15 秒进入下一轮**。不得把循环、`sleep` 或 80 次轮询放进同一个前台 shell 命令；客户端只会在
命令结束后返回 stdout，那样会吞掉过程进度。

```bash
$PYTHON_CMD "$XIAOYI_PPT_DIR/scripts/monitor_generation.py" \
  "$PPT_SESSION_DIR/generate.log" \
  --check-once
```

每轮读取输出中的 `MONITOR_RESULT`：

| 输出标记 | 处理 |
| --- | --- |
| `pending` | 汇报本轮新的 `[进度]`、`[生成文件]` 或 `[文件已保存]` 信息；单独执行 `sleep 15` 后进入下一轮 |
| `done` 与 `PPT_OUTPUT_PATH=...` | 进入步骤三交付 |
| `failed` | 报告失败并附日志路径 |

模型在本流程内维护轮询次数。第 80 轮仍为 `pending` 时，报告超时并附日志路径。不要把
`pending` 当作命令失败，也不要以任意中间进度文本结束监控。

### 2.2 日志解读与汇报

根据日志内容，向用户汇报当前阶段：

| 日志包含 | 向用户汇报 |
|---------|-----------|
| `[进度]` | 显示进度信息内容 |
| `[调用工具]` | 「正在调用工具」 |
| `[进行中]` | 「正在执行中」 |
| `[生成文件]` | 「文件已生成：{filename}」 |
| `[文件已保存]` | 「文件已下载到本地：{path}」 |
| `[DONE]` | 「PPT 生成完成，停止监控，进入步骤三...」 |

### 2.3 终止条件判断

| 状态                    | 处理方式                                                                                                                                                           |
|-----------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 未出现终态标记且未超时            | 继续等待 15 秒，再次检查                                                                                                                                                 |
| 日志含 `[DONE]`  | **停止监控，进入步骤三**                                                                                                                                                 |
| 日志含 `[ERROR]` | 计入失败次数，根据失败次数重试与降级                                                                                                                                             |
| 轮询次数达到 80 次（约 20 分钟）| 计入失败次数，根据失败次数重试与降级                                                                                                                                             |
| 根据失败次数重试与降级          | 第 1 次失败，自动重试：重新执行步骤一（调用 PPT 生成脚本），向用户汇报「生成遇到问题，正在重试…」；第 2 次失败**自动降级到简易模式**：向用户汇报「深度排版服务暂时不可用，正在切换到简易生成模式…」，然后跳转 `step1_search_confirm.md`中的附录 A：简易生成流程（自动降级路径） |
---

## 步骤三：交付结果

**目标**：分析用户意图，将生成的PPT文件重命名后发送给用户。

### 3.1 使用监控器已验证的生成文件路径

**严格前置条件**：仅当紧前一轮 `--check-once` 的输出同时包含
`MONITOR_RESULT=done` 和 `PPT_OUTPUT_PATH=...` 时，才可进入本步骤。
“PPT 全部生成完成”、`n/n 页完成` 等云端中间进度不满足条件；此时继续监控，禁止调用
`--resolve-output`。这样可避免结果清单尚未写入时显示工具执行错误。

```bash
# 将紧前一轮监控输出中 PPT_OUTPUT_PATH= 后的完整绝对路径原样填入：
SOURCE_PPT_PATH="<PPT_OUTPUT_PATH>"
test -f "$SOURCE_PPT_PATH"
```

`--check-once` 已在输出该路径前读取并校验 `generation_result.json` 和本地 PPTX。
因此正常交付流程**不得再次调用** `--resolve-output`，也不得使用 `ls`、`find`、`grep`
或按文件名猜测路径。

### 3.2 分析用户意图生成文件名

综合分析以下信息推断合适的文件名：
- 用户 query 中的主题关键词
- 用户上传文件的名称（如有）
- 用户明确表达的目的或场景

```bash
# 根据用户意图推断文件名，例如：
# "帮我做一个项目汇报PPT" -> "项目汇报.pptx"
# "制作产品发布会演示文稿" -> "产品发布会.pptx"
# "季度工作总结" -> "季度工作总结.pptx"

SUGGESTED_NAME="<根据用户意图分析得出的文件名，可包含 .pptx 后缀>"
```

### 3.3 AIGC 水印标记
打包出最终 PPTX 后，**必须调用水印脚本**为文件添加 AIGC 标识：

```bash
$PYTHON_CMD "$XIAOYI_PPT_DIR/scripts/ppt_aigc_mark.py" "$SOURCE_PPT_PATH"
```

### 3.4 发送 PPT 给用户

先将最终文件复制到当前任务工作空间。脚本会清理非法文件名，并在目标文件已存在时自动添加序号，避免覆盖：

```bash
FINAL_PPT_PATH="$($PYTHON_CMD "$XIAOYI_PPT_DIR/scripts/deliver_ppt.py" \
  "$SOURCE_PPT_PATH" "$PPT_DELIVERY_DIR" "$SUGGESTED_NAME")"
test -f "$FINAL_PPT_PATH"
```

必须使用脚本输出的绝对路径调用文件发送工具：

```text
send_file_to_user(abs_file_path_list=["<FINAL_PPT_PATH 的绝对路径>"])
```

工具调用成功后再向用户提供完成通知：

```
✅ PPT 生成完成！

【内容简述】<简要说明 PPT 的主题、章节结构和主要内容>
```
