# 调用云服务 & 监控 & 交付

> **模型须知:** 进入此子流程前必须先完整阅读本文件,再执行任何操作。
>
> 前置条件(均在父 skill `{baseDir}/SKILL.md` 中已完成设置):
> - **CONFIRMED_QUERY**:已确认需要深度研究的查询文本(在 agent 对话上下文中保持)。
> - **`{baseDir}/scripts/.python_cmd`**:可读,内容是标准库启动器的基座路径；业务解释器由启动器每次实时解析。
> - **DR_JOB_ID**:步骤 2 输出并保存在 agent 上下文中的本次研究 UUID。每条命令都必须填入同一个准确 ID。

> `python_env.py run` 只在本用户的依赖就绪后启动业务脚本，并保留参数、会话 ID 和子进程退出码。若中途返回 `PREFLIGHT_PENDING`，先返回父流程做有限等待；不得重复提交已经存在的任务。

> **传输形态说明:** 本 skill 已迁移为命名管道通信。本流程对 agent 的操作协议**没有任何变化**——提交、轮询、下载的调用方式与出口检查完全一致。底层网络调用已改为经主进程 `SkillApiProxy` 转发(`config.skill_post` 统一处理),报告下载预签名 URL 保留直连。云端文档生成或下载失败时，脚本用已完成的云端正文及参考资料离线生成 DOCX 兜底，不重新发起研究。`task_id` 等字段同样**不暴露给用户**。

---

## 本流程的工作机制(必读)

### 关键环境事实

1. **exec 的 yieldMs 上限是 120 秒。** 即使设 `yieldMs: 2400000`,exec 也最多等 120 秒就会返回 `command still running (session ..., pid ...)`。
2. **process 工具可用**,但本流程**不直接使用 process**(理由见下文)。
3. **没有 automatic completion wake**,任务结束 OpenClaw 不会主动通知 agent。
4. **没有 loop detection**,agent 可以安全循环调用 exec。

### 工作流程

深度研究是 10-20 分钟的长任务（有时会长达40分钟甚至更久）,且 exec 最多只能等 120 秒。因此**必须**用"后台运行 + agent 主动轮询"的模式:

```
1. exec 启动 wait 脚本(30 秒内返回 sessionId 提示,任务进入后台继续跑)
   ↓
2. wait 脚本在后台持续运行,周期性把当前状态写到 status.json
   ↓
3. agent 主动循环:每次调一个 check_status.py 看 status.json,
   还在跑就再调一次 sleep(也会被后台化但没关系)
   ↓
4. status.json 显示终态 → 跳出循环,读 result.json 拿最终结果
```

### 核心数据流

**所有任务状态都保存在 `%TEMP%/xiaoyi_dr/<DR_JOB_ID>/` 下,不依赖 stdout 流或 process poll:**

| 文件 | 写入方 | 读取方 | 用途 |
|------|--------|--------|------|
| `session.json` | session_state 脚本 | 所有子脚本 | 会话目录和交付目录 |
| `task.json` | submit 脚本 | wait 脚本 | task_id、query 和会话关联 |
| `status.json` | wait 脚本(周期写) | check_status 脚本 | agent 查进度的主要来源 |
| `start_time.txt` | wait 脚本(首次启动写) | check_status 脚本 | 计算总耗时,判断超时 |
| `result.json` | wait 脚本(终态写) | agent | 最终产物路径 |
| `generate.log` | 两个脚本 | agent(异常时) | 排查日志 |

**为什么不用 process poll:** process poll 返回的是 stdout 文本流,需要解析。我们让脚本直接写结构化 JSON 文件,通过 `cat` 读,简单可靠。

---

## 1. 提交研究任务

**调用 exec 工具:**

```
tool: exec
command: PYTHON_CMD=$(cat "{baseDir}/scripts/.python_cmd") && DR_JOB_ID="<步骤2输出的准确会话ID>" && "$PYTHON_CMD" "{baseDir}/scripts/python_env.py" run submit_research.py --session-id "$DR_JOB_ID" "<把 CONFIRMED_QUERY 的实际文本填这里,需用引号包裹>"
```

> **关于 CONFIRMED_QUERY 的传递:** 它在你(agent)的对话上下文里,你需要把它的实际文本内容**直接拼接到命令行**。例如查询是"AI Agent 评测基准对比",命令实际是:
>
> ```
> ... submit_research.py --session-id "$DR_JOB_ID" "AI Agent 评测基准对比"
> ```

### 出口检查

submit 通常 5-10 秒内完成。从 exec 返回中查找 `=== RESULT_FOR_AGENT ===` 标记,读取下一行 JSON,按 `exit_code` 分支:

| `exit_code` | 处理方式 |
|----|----------|
| 0 | `phase` 应为 `submitted`。告知用户提交成功,**进入第 2 步**(不要把 task_id 给用户) |
| 2 | 提交失败。把 `message` 和 `diagnosis` 翻译成人话告知用户,**停止流程**,询问下一步计划 |

### 异常:submit 被后台化

如果 30 秒内 submit 还没完成,exec 会返回 `command still running` 而**没有** `RESULT_FOR_AGENT` 标记。这种情况下:

1. **只检查本次会话目录中的 task.json 是否存在**:

   ```
   tool: exec
   command: PYTHON_CMD=$(cat "{baseDir}/scripts/.python_cmd") && DR_JOB_ID="<步骤2输出的准确会话ID>" && SESSION_EXPORTS=$("$PYTHON_CMD" "{baseDir}/scripts/python_env.py" run session_state.py load --session-id "$DR_JOB_ID") && eval "$SESSION_EXPORTS" && test -f "$DR_SESSION_DIR/task.json" && echo "TASK_ID_FOUND" || echo "TASK_ID_NOT_YET"
   ```

2. 如果 `TASK_ID_FOUND`,说明本会话 submit 已完成,**进入第 2 步**。
3. 如果 `TASK_ID_NOT_YET`,再等 10 秒重复检查,**最多 3 次**;仍无果则告知用户系统响应异常并停止。不得因为其他会话存在 task.json 而继续。

### 成功后告知用户

"已提交深度研究任务,预计 10-20 分钟完成。我会安静等待,期间会定期检查进度,完成后直接呈现报告。"

---

## 2. 启动后台 wait 脚本

### ⚠️ 硬性红线(违反会导致任务卡死,务必逐条遵守)

wait 脚本是**常驻轮询进程**,云端研究要 10-40 分钟才完成,wait 脚本必须**在后台持续运行**直到云端结束并下载报告。因此调用这条 exec **绝对禁止传任何超时/后台参数**:

- ❌ **禁止传 `timeout`**(无论 60/120/其他)。一旦传了 timeout,执行器到点就强杀 wait 脚本 → 后台失去轮询进程 → 云端完成后无人下载报告,**任务永久卡在 polling,永远等不到结果**。
- ❌ **禁止传 `yieldMs`**。
- ❌ **禁止传 `background` / `run_in_background`**。
- ❌ **禁止在 command 末尾追加 `&` 或 `nohup ... &`**。
- ✅ 只传 `tool: exec` 一个字段 + `command`。其余全部省略,靠执行器默认的 `command still running` 机制把 wait 脚本放后台常驻。

**调用方式(照抄,一个参数都别多加):**

```
tool: exec
command: PYTHON_CMD=$(cat "{baseDir}/scripts/.python_cmd") && DR_JOB_ID="<步骤2输出的准确会话ID>" && "$PYTHON_CMD" "{baseDir}/scripts/python_env.py" run wait_for_completion_and_download.py --session-id "$DR_JOB_ID"
```

**自我检查(提交前必须逐项核对 tool 的 JSON):**
- 确认 `timeout` 键**不存在**(不是等于某个数,是根本没有这个键)。
- 确认 `yieldMs` / `background` / `run_in_background` 键**不存在**。
- 若工具栏或执行器默认给命令附加了超时,也要主动说明"此命令必须长驻后台,超时上限请留足够或禁止前台超时"。

### 预期返回

exec 大约 10-30 秒后返回。**有三种可能的返回内容**:

| 返回内容 | 含义 | 处理 |
|----------|------|------|
| 包含 `=== RESULT_FOR_AGENT ===` 且 `phase: daemonized` | wait 已成功转入后台轮询 | 进入第 3 步轮询 |
| 包含 `command still running (session ..., pid ...)` | wait 脚本已在后台启动(**预期情况**) | 进入第 3 步轮询 |
| 包含 `=== RESULT_FOR_AGENT ===` 且 `phase: preflight_failed` | 启动期检查失败 | 把 `message`/`diagnosis` 翻译告诉用户,停止流程 |
| 其他 exec 报错 | 系统异常 | 告知用户并停止 |

> **如果这条命令返回"失败"或"timeout",说明 wait 脚本被前台超时杀掉了,后台没有轮询进程——这是异常!** 不要当成正常继续。应按缺失等待进程处理:检查 status.json/start_time.txt 是否保留,然后**重新执行本步骤启动 wait 脚本(不带任何参数)**,最多 2 次;若仍被杀,才按第 5 步异常处理告知用户。

> **必须持续保留 DR_JOB_ID。** `status.json` 是会话目录内的状态文件，`check_status.py` 只有拿到准确 ID 才能查询本任务。

---

## 3. 主动轮询循环

> **这是流程的核心。请严格按以下规则循环,直到终态。**

### 单次循环的两个动作

**动作 A — 检查状态:**

```
tool: exec
command: PYTHON_CMD=$(cat "{baseDir}/scripts/.python_cmd") && DR_JOB_ID="<步骤2输出的准确会话ID>" && "$PYTHON_CMD" "{baseDir}/scripts/python_env.py" run check_status.py --session-id "$DR_JOB_ID"
```

check_status 是秒级返回的短任务,从 stdout 读 `=== RESULT_FOR_AGENT ===` 下一行 JSON。

**动作 B — 根据 JSON 的 `exit_code` 决定下一步:**

| `exit_code` | 含义 | 下一步动作 |
|----|------|----------|
| 0 | 任务终态 | **退出循环,进入第 4 步出口检查** |
| 1 | 任务运行中 | **检查 total_elapsed_s 字段,然后调 sleep**(见下) |
| 2 | 拿不到 status.json | **进入第 5 步异常处理** |

### 关于 total_elapsed_s 超时判断

`exit_code: 1` 时,JSON 中会有 `total_elapsed_s` 字段(自最初提交以来的总秒数)。**用它做超时判断,不要用循环计数**:

- `total_elapsed_s < 3000`(50 分钟内)→ 正常,继续等待
- `total_elapsed_s >= 3000` → 视为云端异常长时间未结束,**进入第 5 步异常处理(超时分支)**

### sleep 的标准调用

每次看到 `exit_code: 1` 且未超时后,**调一次 sleep 来等待**:

```
tool: exec
command: sleep 120
yieldMs: 120000
```

> 明确传 `yieldMs: 120000`(本环境上限),让 sleep 尽量跑满 120 秒。即使提前返回,直接进入下一轮 check 即可。

### 沉默约束

- ❌ **轮询期间不要给用户发任何消息**(不要"还在等"、"快好了"、"我看看进度")
- ❌ **不要调用 `process poll/log`、`web_search` 等任何其他工具**
- ❌ **不要尝试自己 cat status.json,统一通过 check_status.py**(它处理了所有边界情况)
- ✅ **唯一允许的循环动作:check_status → sleep → check_status → sleep → ...**

**为什么必须沉默:** 第 1 步结束时已告知用户"我会安静等待"。如果你中途说话,用户会被反复打扰。轮询期间你的工作就是机械循环,什么都不输出给用户,直到看到终态。

**自我反思提示:** 如果在循环中冒出"是不是该汇报进度"、"用户会不会觉得我卡住了"、"看看 generate.log 怎么样了"等念头,**这是被过度泛化的客服习惯,在 agent 工作流里有害无益**。坚持循环,只在终态时输出。

---

## 4. 出口检查:任务终结后的处理

当 `check_status.py` 返回 `exit_code: 0` 时,JSON 里的 `phase` 字段告诉你具体终态:

| `phase` | 含义 | 处理方式 |
|---------|------|----------|
| `completed` | 研究完成,报告已下载并复制到任务工作空间 | 读 `result.json` 拿 `local_path`,用绝对路径调用 `send_file_to_user` |
| `completed_fallback` | 云端文件获取失败，已生成本地 DOCX | 读 `result.json` 拿 `local_path`，用绝对路径调用 `send_file_to_user`；告知用户为本地生成版本，排版可能不同 |
| `download_failed` | 云端文件获取与本地 DOCX 兜底均失败 | 读 `result.json` 的错误信息，说明失败并保留 `paper_url`；不得把链接说成已成功交付的报告 |
| `cloud_failed` | 云端研究失败 | 把 `message`/`diagnosis` 翻译成人话告知用户,询问下一步 |
| `doc_gen_failed` | 文档生成失败 | 同上 |
| `polling_timeout` | wait 脚本内 1 小时云端未给终态 | 告知用户云端任务超时,询问是否重新提交 |
| `network_unstable` | wait 脚本连续轮询失败 | 告知用户网络异常,询问是否稍后重试 |
| `unknown_status` | 云端返回了未知状态码 | 告知用户系统异常 |
| `result_mismatch` | 云端返回任务标识与本会话不一致 | 停止交付错误报告，告知用户系统任务关联异常 |
| `terminated` | wait 脚本被信号杀掉 | **进入第 5 步异常处理**(不是真终态) |

### 读 result.json 的标准方法

```
tool: exec
command: PYTHON_CMD=$(cat "{baseDir}/scripts/.python_cmd") && DR_JOB_ID="<步骤2输出的准确会话ID>" && SESSION_EXPORTS=$("$PYTHON_CMD" "{baseDir}/scripts/python_env.py" run session_state.py load --session-id "$DR_JOB_ID") && eval "$SESSION_EXPORTS" && cat "$DR_SESSION_DIR/result.json"
```

`completed` 或 `completed_fallback` 时必须确认 `local_path` 文件存在，并调用：

```text
send_file_to_user(abs_file_path_list=["<local_path 的绝对路径>"])
```

工具成功后再通知用户。不得只在文本中展示本地路径。`completed_fallback` 应说明“云端文件下载或生成未成功，已用本次研究结果生成本地 DOCX”；图片保留说明和原链接，样式可能不同。不得声称云端存储问题已修复，也不得另行重做研究。

⚠️ **不要把 `task_id` 暴露给用户。** result.json 和 check_status 输出中含有 task_id 字段,这是给 agent 内部用的,**不要转述给用户**。

---

## 5. 异常处理

### 情况 A:check_status 返回 `phase: no_status_file` 或 `status_corrupted`

意味着 wait 脚本可能崩了。处理:

1. **读 generate.log 看具体原因**:

   ```
   tool: exec
   command: PYTHON_CMD=$(cat "{baseDir}/scripts/.python_cmd") && DR_JOB_ID="<步骤2输出的准确会话ID>" && SESSION_EXPORTS=$("$PYTHON_CMD" "{baseDir}/scripts/python_env.py" run session_state.py load --session-id "$DR_JOB_ID") && eval "$SESSION_EXPORTS" && tail -30 "$DR_SESSION_DIR/generate.log" 2>/dev/null
   ```

2. **判断如何重启:**
   - 日志显示明确的、可重试的本地失败(网络断、配置错恢复了)→ **重启 wait 脚本(回到第 2 步),最多 2 次**
   - 日志显示云端明确失败 → 直接按 `cloud_failed` 处理,告知用户
   - 日志为空或不存在 → 说明 wait 脚本根本没起来,**重启 1 次**;仍异常告知用户系统不稳定

> **重启不需要告知用户**(不要"我在重启",仍然沉默)。重启后回到第 3 步主动轮询。

### 情况 B:`phase: terminated`

wait 脚本被信号杀掉。云端任务可能还在跑,直接重启:

1. **使用同一个 DR_JOB_ID 重启 wait 脚本(回到第 2 步),最多 2 次。** 重启时 `start_time.txt` 会保留,total_elapsed_s 计算不会重置。
2. 重启后回到第 3 步轮询循环。
3. 2 次重启仍异常,告知用户系统不稳定,询问是否重新发起任务。

### 情况 C:总耗时超过 50 分钟(`total_elapsed_s >= 3000`)

云端任务异常长时间未结束。处理:

1. 读 generate.log 看最后几行,用人话总结当前阶段(比如"云端一直返回 researching 状态,已超过 50 分钟未变");
2. 告知用户:"研究任务运行时间异常长,可能云端出现异常。是否重新发起一次?"

### 通用约束

⚠️ **任何情况下都不要把 `task_id` 暴露给用户** —— 用户没有手动查询云端任务的渠道,给用户 task_id 反而制造无法行动的困惑。

⚠️ **不要直接贴 generate.log 给用户** —— 日志是技术格式,用人话总结即可。

---

## 附录:常见 phase 速查表

| Phase | 来源 | 终态? | 含义 |
|-------|------|-------|------|
| `starting` | wait | 否 | 脚本启动中 |
| `polling` | wait | 否 | 正在轮询云端 |
| `downloading` | wait | 否 | 云端完成,本地下载中 |
| `submitted` | submit | 是 | 提交成功 |
| `completed` | wait | 是 | 全流程成功 |
| `generating_local_report` | wait | 否 | 正在用云端研究结果生成本地 DOCX |
| `completed_fallback` | wait | 是 | 本地 DOCX 兜底已交付到工作空间 |
| `download_failed` | wait | 是 | 下载与本地兜底均失败，保留原链接 |
| `cloud_failed` | wait | 是 | 云端任务失败 |
| `doc_gen_failed` | wait | 是 | 文档生成失败 |
| `polling_timeout` | wait | 是 | 1 小时云端未给终态 |
| `network_unstable` | wait | 是 | 连续网络失败 |
| `result_mismatch` | wait | 是 | 云端任务标识与本会话不一致，禁止交付 |
| `terminated` | wait | 是(异常) | 被信号杀掉,需重启 |
| `preflight_failed` | wait/submit | 是 | 启动期检查失败 |
| `no_status_file` | check_status | 是(异常) | wait 脚本未启动或被杀 |
| `no_session` | check_status | 是(异常) | 会话目录文件丢失 |
| `status_corrupted` | check_status | 是(异常) | status.json 损坏 |
| `http_timeout` / `http_error` / `http_request_failed` | submit | 是 | 提交时网络/云端问题 |
| `task_id_missing` | submit | 是 | 云端响应没有 task_id |
| `invalid_input` | submit | 是 | CONFIRMED_QUERY 为空 |
