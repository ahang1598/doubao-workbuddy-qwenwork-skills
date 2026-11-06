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
- **报告下载 / 预签名 URL**:URL 本身即一次性凭证,**保留直连**,不经代理。
- **旧沙箱形态(兼容)**:若旧集群仍在用,可配 `SERVICE_URL=http(s)://...` + `.xiaoyienv`,脚本回退到 `requests` 直连。
- 脚本通过 `config.skill_post(path, payload, headers)` 统一转发,无需关心底层是管道还是直连。

---

# ⚠️ 关于跨 exec 调用的状态传递(在执行任何步骤前必读)

OpenClaw 的每次 `exec` 调用会启动**新的子 shell**,**不能假设 `export` 的环境变量会跨调用继承**。

因此,本 skill 把跨步骤共享的状态写入**固定路径的文件**:

| 状态           | 载体文件                                     | 写入步骤 | 读取方              |
| ------------ | ---------------------------------------- | ---- | ---------------- |
| Python 解释器路径 | `{baseDir}/scripts/.python_cmd`          | 步骤 1 | 步骤 4 中所有 bash 调用 |
| 当前会话目录       | `{baseDir}/scripts/.current_session_dir` | 步骤 2 | 步骤 4 中的子脚本       |

**这两个文件由本父 skill 写入,子流程脚本只读不写。** 后续所有 bash 调用引用 Python 或会话目录时,**先 `cat` 对应文件**,不要假设当前 shell 里有 `$PYTHON_CMD` 或 `$DR_SESSION_DIR`。

> 文档中出现的 `$DR_SESSION_DIR`、`$PYTHON_CMD` 等记号**仅作为路径占位符**便于描述,**不是实际可用的环境变量**。

---

# 核心工作流程

完整流程按顺序分为四步。前两步是**环境准备**,中间一步是**需求判断与澄清**,最后一步是**任务执行与交付**。

## 步骤 1:环境初始化(始终最先执行)

> 即使本次会话之前已触发过本 skill,也要重新执行此步骤。状态文件可能因系统清理被删除,且每次 exec 是新 shell,无法继承先前状态。

**执行以下 bash:**

```bash
set -e

# 1) 定位 Python
# Windows 上用 py launcher(Git Bash 里 python/python3 可能是 WindowsApps 存根)。
# 注意:PYTHON_CMD 必须是单一命令名(不能带参数,如 "py -3"),
# 因为后续以 "$PYTHON_CMD" 拼接脚本路径调用。
if command -v py >/dev/null 2>&1 && py -3 -c "import sys; exit(0 if sys.version_info >= (3,8) else 1)" 2>/dev/null; then
  PYTHON_CMD="py"
fi
if [ -z "$PYTHON_CMD" ]; then
  for cmd in python3 python python3.13 python3.12 python3.11 python3.10 python3.9 python3.8; do
    if command -v "$cmd" &>/dev/null && "$cmd" -c "import sys; exit(0 if sys.version_info >= (3,8) else 1)" 2>/dev/null; then
      PYTHON_CMD="$cmd"
      break
    fi
  done
fi

if [ -z "$PYTHON_CMD" ]; then
  echo "PREFLIGHT_FAILED: python_not_found"
  exit 1
fi

echo "已找到 Python: $PYTHON_CMD ($($PYTHON_CMD --version))"

# 2) 装依赖(已存在则跳过)
if ! "$PYTHON_CMD" -c "import requests" 2>/dev/null; then
  if ! "$PYTHON_CMD" -m pip install -q --break-system-packages requests; then
    echo "PREFLIGHT_FAILED: dependency_install_failed"
    exit 1
  fi
fi
echo "依赖已就绪。"

# 3) 持久化 PYTHON_CMD 到固定路径
echo "$PYTHON_CMD" > "{baseDir}/scripts/.python_cmd"
echo "PREFLIGHT_OK"
```

**出口检查:**

- stdout 出现 `PREFLIGHT_OK` → 进入步骤 2。
- stdout 出现 `PREFLIGHT_FAILED: <reason>` → 翻译成人话告知用户并**停止流程**:
  - `python_not_found` → "深度研究功能需要 Python 3.8+,当前环境未找到符合要求的解释器。"
  - `dependency_install_failed` → "依赖安装失败,请检查网络或手动安装 requests 后重试。"

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

# 2) 生成会话 ID 和目录
# 会话目录放在系统临时目录的 xiaoyi_dr 子目录下,跨平台:
#   Unix/macOS  -> /tmp
#   Windows(Git Bash) -> $TMP/$TEMP(映射到用户临时目录)
DR_SESSION_ID=$(uuidgen 2>/dev/null || "$PYTHON_CMD" -c 'import uuid; print(uuid.uuid4())')
DR_SESSION_DIR="$(mktemp -d -t xiaoyi_dr.XXXXXX 2>/dev/null || echo "$TMPDIR/xiaoyi_dr/$DR_SESSION_ID" || echo "/tmp/xiaoyi_dr/$DR_SESSION_ID")"
mkdir -p "$DR_SESSION_DIR"

# 3) 持久化会话目录路径
echo "$DR_SESSION_DIR" > "{baseDir}/scripts/.current_session_dir"

echo "SESSION_INIT_OK"
echo "会话 ID: $DR_SESSION_ID"
echo "会话目录: $DR_SESSION_DIR"
```

**出口检查:** stdout 出现 `SESSION_INIT_OK` 即可进入步骤 3。否则告知用户初始化失败并停止。

**路径与变量约定:**

| 名称          | 实际位置                                                       |
| ----------- | ---------------------------------------------------------- |
| `{baseDir}` | 本 skill 根目录(由运行环境注入)                                       |
| 会话目录        | 系统临时目录下的 `xiaoyi_dr/` 子目录(Windows 为 `%TEMP%` 下,非固定 `/tmp`) |

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

**前置条件:** 已完成步骤 1、2、3,且步骤 3 确认调用深度研究。

---

# 方法与脚本清单

本 skill 通过以下脚本与云服务交互:

| 脚本                                            | 用途                | 调用的云服务                    |
| --------------------------------------------- | ----------------- | ------------------------- |
| `scripts/submit_research.py`                  | 提交研究任务,获取 task_id | 云服务(提交服务)                 |
| `scripts/wait_for_completion_and_download.py` | 等待研究完成,自动生成并下载报告  | 云服务(查询服务) + 文档生成服务 + 报告存储 |
| `scripts/claw_doc_gen.py`                     | 文档生成工具(内部调用)      | 云服务(文档生成服务)               |

### 脚本依赖文件

| 文件                             | 用途                 | 生命周期                                    |
| ------------------------------ | ------------------ | --------------------------------------- |
| `scripts/req_template.json`    | 提交研究任务的请求模板        | 静态,跟随 skill 发布                          |
| `scripts/task_id.json`         | 存储已提交任务的 task_id   | 运行时,每次调用`scripts/submit_research.py`时覆盖 |
| `scripts/.python_cmd`          | 当前可用的 Python 解释器路径 | 运行时,步骤 1 写入                             |
| `scripts/.current_session_dir` | 当前会话目录绝对路径         | 运行时,步骤 2 写入                             |
| `scripts/claw_doc_gen.py`      | 文档生成工具             | 静态,跟随 skill 发布                          |

> ⚠️ **关于并发会话的已知限制:** `task_id.json`、`.python_cmd`、`.current_session_dir` 都是固定路径文件,**同一时刻只能有一个深度研究会话在跑**。如果用户在前一个研究未完成时发起新研究,新会话会覆盖旧会话的状态。当前版本暂不支持并发,遇到这种请求时建议告知用户等前一个完成。