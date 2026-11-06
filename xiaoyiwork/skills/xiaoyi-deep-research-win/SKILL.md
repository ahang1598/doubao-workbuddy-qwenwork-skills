---
name: xiaoyi-deep-research-win
description: >
  用户出现以下任一情况时,立即读入本skill:

  (1)消息中出现"深度研究" 和 "deep research"这两个关键词

  (2)提出以下类型的问题(即使你觉得自己能回答,也要读入skill):
  - 技术选型、方案对比(如"X和Y怎么选")
  - 行业调研、市场格局(如"某赛道有哪些玩家")
  - 投资、财务、政策分析判断(如"某板块值不值得配置")
  - 学术研究现状、文献综述(如"某方向研究进展如何")
  - 竞品调研、产品对标(如"X和竞品比怎么样")
  - 事件影响分析、趋势判断(如"某事件会带来什么影响")
  - 战略决策支持(如"我们应该怎么布局X")
  - 复杂问题诊断(技术架构、医疗、法律案情等)
  - 陌生领域系统了解(如"X最近很火,到底怎么回事")
  - 意图表达(如"帮我彻底搞清楚X"、"帮我梳理一下X")

  (3)用户在最近3轮以上对话中围绕同一专业话题持续深挖

  **场景(2)即使你觉得能答也要读入**,这类问题往往依赖最新数据、多源观点或系统性知识结构,单次回答通常无法覆盖。

  **不读入:** 简单事实查询、日常问答、概念定义、编码/翻译/总结任务、闲聊、需用户私有信息的查询。
metadata:
  openclaw:
    requires:
      bins:
        - python3
---

# 技能说明

本技能负责识别深度研究需求、澄清研究问题、调用深度研究云服务以及获取最后的研究报告。

---

# 🔐 桌面形态鉴权与网络调用方式(必读)

本 skill 已从"云沙箱直连开放 API"迁移到**命名管道通信**:

- **桌面形态(默认)**:所有云端接口(`submit`/`check`/`doc_gen`)经主进程 `SkillApiProxy` 经命名管道(`\\.\pipe\claw-skill`)转发。**业务鉴权由主进程注入,skill 侧零业务凭证**,只需环境变量 `CLAW_SKILL_TOKEN`(主进程注入,子进程继承)。
- **报告下载 / 预签名 URL**:URL 本身即一次性凭证，保留直连，不经管道代理。云端研究完成后先保存正文和参考资料；云端 DOCX 生成或下载失败时，使用该研究结果在本地生成 DOCX 兜底，不重新提交研究，也不新增依赖。`completed_fallback` 必须交付本地 DOCX，并说明为本地生成版本。图片保留说明与原链接，排版不保证与云端一致。
- **旧沙箱形态(兼容)**:若旧集群仍在用,可配 `SERVICE_URL=http(s)://...` + `.xiaoyienv`,脚本回退到 `requests` 直连。
- 脚本通过 `config.skill_post(path, payload, headers)` 统一转发,无需关心底层是管道还是直连。

---

# ⚠️ 关于跨 exec 调用的会话隔离(在执行任何步骤前必读)

OpenClaw 的每次 `exec` 调用会启动**新的子 shell**,**不能假设 `export` 的环境变量会跨调用继承**。

因此,每次研究任务都必须先创建独立 UUID,状态保存到系统临时目录下的独立目录:

```text
%TEMP%/xiaoyi_dr/<DR_SESSION_ID>/
├── session.json
├── task.json
├── status.json
├── start_time.txt
├── report_source.json  # 完成的云端正文和参考资料，用于本地 DOCX 兜底
├── result.json
└── generate.log
```

步骤 2 输出的 `DR_SESSION_ID` 是本次研究唯一的 `DR_JOB_ID`。将它保存在 agent
对话上下文中；后续提交、启动后台等待、查询状态和异常恢复都必须显式传入这个准确
ID。**禁止使用“最近一次会话”、默认会话或全局 current-session 文件。**

`{baseDir}/scripts/.python_cmd` 只缓存运行标准库启动器的 Skill 基座 Python，不代表业务依赖已就绪。每个新 `exec` 都通过 `python_env.py run` 重新识别本用户的共享 venv 或 `py-site`，避免沿用 Agent 首次启动时的旧解释器。任务身份始终通过 `--session-id "$DR_JOB_ID"` 传递。

---

# 核心工作流程

完整流程按顺序分为四步。前两步是**环境准备**,中间一步是**需求判断与澄清**,最后一步是**任务执行与交付**。

## 步骤 1:环境初始化(始终最先执行)

> 即使本次会话之前已触发过本 skill,也要重新执行此步骤。状态文件可能因系统清理被删除,且每次 exec 是新 shell,无法继承先前状态。

**执行以下 bash:**

```bash
set -e

# 1) 定位运行标准库助手的引导 Python。优先使用桌面注入值；
# 该值可能早于依赖安装，业务解释器由助手另外解析和验证。
PYTHON_CMD=""
if [ -n "${CLAW_PYTHON_EXE:-}" ] && "$CLAW_PYTHON_EXE" -c "import sys; exit(0 if sys.version_info >= (3,8) else 1)" 2>/dev/null; then
  PYTHON_CMD="$CLAW_PYTHON_EXE"
fi

# 引导值不可用时，系统 Python 也只能运行标准库助手；桌面业务不会回退到它。
# PYTHON_CMD 必须是单一命令或解释器路径，不能带参数。
if [ -z "$PYTHON_CMD" ]; then
  for cmd in python3 python python3.13 python3.12 python3.11 python3.10 python3.9 python3.8; do
    if command -v "$cmd" &>/dev/null && "$cmd" -c "import sys; exit(0 if sys.version_info >= (3,8) else 1)" 2>/dev/null; then
      PYTHON_CMD="$cmd"
      break
    fi
  done
fi
if [ -z "$PYTHON_CMD" ] && command -v py >/dev/null 2>&1 && py -3 -c "import sys; exit(0 if sys.version_info >= (3,8) else 1)" 2>/dev/null; then
  PYTHON_CMD=$(py -3 -c 'import sys; print(sys.executable)')
fi

if [ -z "$PYTHON_CMD" ]; then
  echo "PREFLIGHT_FAILED: python_not_found"
  exit 1
fi

echo "已找到 Python: $PYTHON_CMD ($($PYTHON_CMD --version))"

# 2) 启动器只依赖标准库；它实时检查共享 Skill 环境，最多等待后台安装 45 秒。
# 不安装依赖，不修改框架 Python；缓存的只是后续启动器所需的基座路径。
"$PYTHON_CMD" "{baseDir}/scripts/python_env.py" prepare --wait-seconds 45
```

**出口检查:**

- `PREFLIGHT_OK`：共享 Skill 环境已实际导入 `requests`、`urllib3`，进入步骤 2。
- `PREFLIGHT_PENDING`：后台依赖正在准备，不能当作研究失败，也不能继续提交。向用户说明“正在准备首次使用环境”，再单独执行一次本准备命令；每轮最多等待 45 秒，总共最多 4 轮。每轮都是独立 exec，避免长命令被执行器超时杀掉。
- 4 轮仍未就绪：停止并说明后台依赖暂未准备完成，可稍后重试或在技能页重试依赖安装。禁止自行安装依赖、改用系统 Python 执行业务，或重复提交云端研究。
- `PREFLIGHT_FAILED`：按具体错误停止；找不到引导 Python 时说明安装包的 Python 尚不可用。

首次 Agent 可能早于依赖安装而启动，因此 `CLAW_PYTHON_EXE` 可能仍指向基座。不要通过该路径手动导入第三方包来判断自动安装是否失败；以启动器的检查结果为准。独立运行且未处于桌面环境时，才使用当前解释器的依赖。

**路径与变量约定:**

| 名称          | 实际位置                 |
| ----------- | -------------------- |
| `{baseDir}` | 本 skill 根目录(由运行环境注入) |

## 步骤 2:会话初始化

```bash
set -e

# 1) 读取上一步持久化的 PYTHON_CMD
if [ ! -f "{baseDir}/scripts/.python_cmd" ]; then
  echo "SESSION_INIT_FAILED: python_cmd_missing"
  exit 1
fi
PYTHON_CMD=$(cat "{baseDir}/scripts/.python_cmd")

# 2) 创建隔离会话。session_state.py 用 Python 的真实 cwd 记录最终交付目录。
SESSION_EXPORTS=$("$PYTHON_CMD" "{baseDir}/scripts/python_env.py" run session_state.py init) || exit $?
eval "$SESSION_EXPORTS"
DR_JOB_ID="$DR_SESSION_ID"

echo "SESSION_INIT_OK"
echo "会话 ID: $DR_JOB_ID"
echo "会话目录: $DR_SESSION_DIR"
echo "最终交付目录: $DR_DELIVERY_DIR"
```

**出口检查:** stdout 出现 `SESSION_INIT_OK` 后，必须把输出的会话 ID 原样保存在 agent
上下文，作为本任务的 `DR_JOB_ID`。若 ID 丢失，停止并重新初始化；禁止猜测或复用其他
研究任务的 ID。

**路径与变量约定:**

| 名称          | 实际位置                                                       |
| ----------- | ---------------------------------------------------------- |
| `{baseDir}` | 本 skill 根目录(由运行环境注入)                                       |
| 会话目录        | 系统临时目录下的 `xiaoyi_dr/<DR_JOB_ID>/`                     |
| 最终报告目录      | 当前任务工作空间；下载完成后从会话临时目录安全复制到这里                         |

## 步骤 3:需求判断与澄清

**执行以下命令读取详细指引:**

```bash
cat "{baseDir}/step_judge_clarification.md"
```

> 不要凭对文件名的猜测自行实现需求判断逻辑。该文件包含触发判断规则和澄清话术,必须读入后再执行。

**完成标准:** 判断是否需要调用深度研究。

- **需要** → 与用户澄清后,在 agent 自己的对话上下文中确定 `CONFIRMED_QUERY`(最终的研究查询文本),进入步骤 4。
- **不需要** → 退出本 skill 流程,回到普通对话模式正常回答用户的问题。

> `CONFIRMED_QUERY` 是一段查询文本,**保存在 agent 上下文里即可,不需要写文件或环境变量**。步骤 4 会把它作为命令行参数直接传给提交脚本。

## 步骤 4:调用云服务 & 监控 & 交付

**执行以下命令读取详细指引:**

```bash
cat "{baseDir}/step_generate_monitor.md"
```

> 该文件包含 exec 调用必需参数(`yieldMs` / `timeout`)、出口检查协议、自动重连机制、等待期间的沉默约束等关键内容。**不读入直接执行会导致脚本被提前杀掉、状态丢失或用户被频繁打扰**。

**前置条件:** 已完成步骤 1、2、3，步骤 3 确认调用深度研究，且 agent 上下文中保留本任务准确的 `DR_JOB_ID`。

---

# 方法与脚本清单

本 skill 通过以下脚本与云服务交互:

| 脚本                                            | 用途                | 调用的云服务                    |
| --------------------------------------------- | ----------------- | ------------------------- |
| `scripts/submit_research.py`                  | 提交研究任务,获取 task_id | 云服务(提交服务)                 |
| `scripts/wait_for_completion_and_download.py` | 等待研究完成,自动生成并下载报告  | 云服务(查询服务) + 文档生成服务 + 报告存储 |
| `scripts/local_report_docx.py`              | 云端文档获取失败后离线生成 DOCX；仅标准库 | 本地文件系统 |
| `scripts/python_env.py`                     | 解析/等待当前用户的 Skill Python | 本地检查；不安装依赖 |
| `scripts/session_state.py`                    | 创建/恢复 UUID 隔离会话     | 本地文件系统                       |
| `scripts/claw_doc_gen.py`                     | 文档生成工具(内部调用)      | 云服务(文档生成服务)               |
| `scripts/deliver_report.py`                   | 将最终报告安全复制到任务工作空间 | 本地文件系统                       |

### 脚本依赖文件

| 文件                                      | 用途                       | 生命周期                  |
| --------------------------------------- | ------------------------ | --------------------- |
| `scripts/req_template.json`             | 提交研究任务的请求模板              | 静态,跟随 skill 发布         |
| `scripts/.python_cmd`                   | 标准库启动器使用的 Skill 基座路径 | 运行时引导缓存，不代表依赖环境      |
| `<会话目录>/session.json`                 | 会话 ID、会话目录和最终交付目录        | 每个研究任务独立              |
| `<会话目录>/task.json`                    | task_id、原始 query 和摘要        | 每个研究任务独立              |
| `<会话目录>/status.json` / `result.json` | 轮询状态和最终结果                 | 每个研究任务独立              |
| `scripts/claw_doc_gen.py`               | 文档生成工具                   | 静态,跟随 skill 发布         |

不同聊天或同一聊天中的多个研究任务可以并行执行。每个任务必须使用自己的 `DR_JOB_ID`，不得交叉复用。
