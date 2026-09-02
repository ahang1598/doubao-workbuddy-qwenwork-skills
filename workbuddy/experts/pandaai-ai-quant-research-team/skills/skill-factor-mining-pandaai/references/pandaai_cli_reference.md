# PandaAI CLI 完整命令参考

> 来源: https://pypi.org/project/pandaai-cli/
> 版本: 0.1.2（2026-08-04 通过已安装包元数据与命令帮助核对）
> pandaai-cli 为独立的 MIT 许可第三方项目；命令、计费和平台行为可能变化。

## 安装

```bash
pip install pandaai-cli
```

Python >= 3.10

## 快速开始

```bash
# 交互式登录（token 自动保存到用户配置目录）
PandaAI experimenter WorkBuddy interactive login entry

# 创建因子分析
pandaai-cli factor_create --formula "close/ref(close,5)-1"
# → ✅ 因子分析已创建: 6a461b10...

# 执行并拿结果
pandaai-cli factor_run 6a461b10... --download

# 查看列表
pandaai-cli factor_list
```

## 命令一览

```
pandaai-cli <command> [options]

命令:
  login                                   登录并保存 token
  factor_create                           创建因子分析（不执行），返回 factor_id
  factor_info <factor_id>                 查看因子详情（代码/公式 + 所有参数）
  factor_update <factor_id> [options]     修改因子参数
  factor_run <factor_id>                  执行已有因子分析（启动 + 轮询 + 结果）
  factor_list                             列出所有因子分析
  balance                                 查询算力余额
  factor_result <run_id>                  查询运行结果（14 个因子分析接口）
  factor_delete <factor_id> [factor_id...] 删除因子分析
```

## 详细参数

### login — 登录

```bash
PandaAI experimenter WorkBuddy interactive login entry
```

| 参数 | 说明 |
|------|------|
| `interactive-login-field` | 手机号（不建议在命令行传入；不传则交互式输入） |
| `interactive-login-field` | 密码（不要在命令行传入；不传则隐藏输入） |

> 安全边界：不要把手机号、密码、token 或配置文件内容放入提示词、日志、示例或仓库。

登录成功后 token 自动保存到 `~/.pandaai/config.yaml`，后续命令无需再登录。token 过期时自动提示重新登录。

### factor_create — 创建因子分析

```bash
pandaai-cli factor_create (--code CODE | --formula FORMULA | --file FILE)
  [--name NAME] [--start-date YYYYMMDD] [--end-date YYYYMMDD]
  [--adjustment-cycle N] [--factor-direction D]
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--code CODE` | - | Python 因子代码（需继承 Factor 基类） |
| `--formula FORMULA` | - | 因子公式字符串 |
| `--file FILE` | - | 从文件读取代码/公式 |
| `--name NAME` | 新建因子分析 | 因子分析名称 |
| `--start-date` | 昨天-60天 | 因子构建开始日期，格式 YYYYMMDD |
| `--end-date` | 昨天 | 因子构建结束日期，格式 YYYYMMDD |
| `--adjustment-cycle` | 1 | 调仓周期（1-10） |
| `--factor-direction` | 1 | 因子方向：0=负向，1=正向 |

> 分组数量固定为 10，股票池固定为沪深全A，不可修改。

**返回值（JSON）：**
```json
{"success": true, "factor_id": "6a46..."}
```

**示例：**
```bash
pandaai-cli factor_create --formula "close/ref(close,5)-1"
pandaai-cli factor_create --code "$(cat factor.py)" --name "动量因子"
pandaai-cli factor_create --file ./factor.py --start-date 20240101 --end-date 20240630
pandaai-cli factor_create --formula "close/ref(close,5)-1" \
  --adjustment-cycle 3 --factor-direction 0
```

### factor_info — 查看因子详情

```bash
pandaai-cli factor_info <factor_id>
```

展示内容：名称、ID、类型（Python 代码/因子公式）、创建时间、调仓周期、分组数量、因子方向、股票池、日期范围、代码/公式内容。

### factor_update — 修改因子参数

```bash
pandaai-cli factor_update <factor_id> [options]
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--name` | - | 新名称 |
| `--code` / `--formula` / `--file` | - | 新代码/公式（三选一） |
| `--start-date` | - | 开始日期 YYYYMMDD |
| `--end-date` | - | 结束日期 YYYYMMDD |
| `--adjustment-cycle` | - | 调仓周期 1-10 |
| `--factor-direction` | - | 因子方向 0=负向 1=正向 |

**约束：**
- 调仓周期必须在 1-10 之间
- 分组数量固定为 10，不可修改
- 股票池固定为沪深全A，不可修改

### factor_run — 执行因子分析

```bash
pandaai-cli factor_run <factor_id>
  [--download [PATH]] [--poll-interval SEC] [--timeout SEC]
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `factor_id` | 必填 | 要执行的因子分析 ID |
| `--download [PATH]` | 不下载 | 下载结果 CSV，默认 ~/Downloads/ |
| `--poll-interval` | 2 | 状态轮询间隔（秒） |
| `--timeout` | 600 | 超时时间（秒） |

> 算力服务器固定使用 cpu=4, memory=8, gpu=4，无需手动选择。

**返回值（JSON）- 成功：**
```json
{
  "success": true,
  "status": "SUCCESS",
  "factor_id": "6a46...",
  "factor_run_id": "6a46...",
  "duration_seconds": 6.5,
  "output": [{"node_title": "因子分析", "node_output": {"task_id": "..."}}],
  "billing": {"balance": 9451.51, "deducted": 2.0, "status": "ok"},
  "results": {
    "nodes": {...},
    "factor_analysis": {
      "query_factor_analysis_data": [...],
      "query_group_return_analysis": [...],
      ...
    }
  }
}
```

**返回值（JSON）- 失败：**
```json
{
  "success": false,
  "status": "FAILED",
  "error": {"type": "WORKFLOW_FAILED", "message": "...", "node_errors": [...]},
  "billing": {"balance": 9449.51, "deducted": 2.0, "status": "ok"}
}
```

### factor_list — 列出因子分析

```bash
pandaai-cli factor_list [--limit N] [--offset N] [--no-detail]
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--limit` | 100 | 每页条数（最大 100） |
| `--offset` | 0 | 结果偏移量 |
| `--no-detail` | false | 跳过获取分析摘要（更快） |

分析摘要包含：
- **核心绩效**：因子收益、夏普比率、年化收益、最大回撤
- **IC 系列**：IC_mean、Rank_IC、IC_std、IC_IR、IR、P(IC<-0.02)、P(IC>0.02)、t统计量、p-value、单调性

**返回值（JSON）：**
```json
{
  "success": true,
  "total": 180,
  "count": 100,
  "limit": 100,
  "offset": 0,
  "factors": [
    {"_id": "6a46...", "name": "动量因子", "create_at": 1782...,
     "last_run_id": "6a46...", "_last_run_time": "...",
     "_analysis_summary": "因子收益 20.90%  夏普比率 8.02  ..."}
  ]
}
```

### balance — 查询算力余额

```bash
pandaai-cli balance
```

**返回值（JSON）：**
```json
{"success": true, "balance": {"computingPower": 9435.51, ...}}
```

### factor_result — 查询运行结果

```bash
pandaai-cli factor_result <run_id> [--download [PATH]]
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `run_id` | 必填 | 运行 ID |
| `--download [PATH]` | 不下载 | 下载结果 CSV |

调用全部 14 个因子分析接口，展示：
- **核心绩效**：因子收益、夏普比率、年化收益、最大回撤
- **因子分析指标**：IC_mean, Rank_IC, IC_std, IC_IR, IR, P(IC<-0.02), P(IC>0.02), t统计量, p-value, 单调性
- **分组收益**：10 分组 + 多空组合的 年化收益/超额收益/夏普比率/最大回撤/月胜率
- **Top 因子**：最新日期因子值最高的 10 只股票
- **图表数据**：IC 序列、IC 衰减、IC 密度分布等 10 个图表（完整 JSON，含全量数据点）

### factor_delete — 删除因子分析

```bash
pandaai-cli factor_delete <factor_id> [factor_id...]
pandaai-cli factor_delete --pattern "quota-test" [--yes]
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `factor_id` | 至少一个 | 因子分析 ID（支持多个） |
| `--pattern` | - | 按名称前缀批量匹配 |
| `--yes` | false | 跳过删除确认 |

## 通用参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--config PATH` | ~/.pandaai/config.yaml | 配置文件路径 |
| `--json` | false | 仅输出 JSON（不输出 INFO 日志） |
