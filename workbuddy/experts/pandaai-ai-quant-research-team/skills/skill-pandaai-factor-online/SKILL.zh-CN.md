---
name: pandaai-factor-online-zh
description: 搭建 pandaai-cli、登录 PandaAI，并在平台上挖掘、回测、迭代量化因子。当用户参加 PandaAI 因子大赛、安装或登录 pandaai-cli、询问有哪些字段与算子可用、编写与调试因子公式、运行因子分析、解读 IC / 分组收益 / 换手率结果时使用。
license: GPL-3.0-only
---

# PandaAI 因子在线挖掘

从一台干净的机器到跑出第一个因子分析，再到不浪费算力地持续迭代，需要的全部内容。
比赛参赛者可另阅 [references/competition_rules.md](references/competition_rules.md) 了解官方积分与组合口径；它只作参考，不改变用户自己的研究目标或排序标准。

English version: [SKILL.md](SKILL.md)

## 核心流程 Core Workflow

用户在一次会话里第一次调用本技能时，先按下面的顺序走完再开始挖掘。不要跳过去写公式，
第 3 步之前不要花任何算力。

**0. 先检查 CLI 新鲜度。** 在体检和任何账号操作前，读取本机 `pandaai-cli` 版本，并与用户提供的 CLI 文档、
官方发布信息或当前可安装版本比较。发现新版本时先报告版本差异和潜在的参数、返回结构或计费变化，征得用户同意后再升级；
升级后重新跑体检和离线自检，不要在未确认兼容性时用新旧 CLI 混跑。通过 `uv` 安装时用
`uv tool upgrade pandaai-cli`，通过 `pipx` 安装时用 `pipx upgrade pandaai-cli`；都不能静默执行，
要汇报结果并确认 `balance` 仍然成功。

**0.1. 每个会话只检查一次 Skill 新鲜度。** `scripts/bootstrap.py` 会把本地 Git 仓库与 `origin/main` 比较，
只报告 GitHub 是否有新提交，不会自动拉取。如果发现更新，先征得用户同意，再执行
`git pull --ff-only origin main`，并在开始新批次前运行 `python3 scripts/selftest.py`。不要在正在运行或可续跑的批次中途更新。
如果 Skill 不是 Git 仓库，或 GitHub 暂时无法访问，报告“无法确认版本”并继续使用本地版本。

**1. 体检。** 它不花算力——只调用 `balance` 和 `factor_list`；唯一会写的东西是 `~/.pandaai/config.yaml`，
且仅在该文件缺失时创建，因为 CLI 自己创建不了它。直接运行，不要用自己的话复述它的功能：

```bash
python3 scripts/bootstrap.py
```

它会依次检查 Skill 是否落后、Python 环境、CLI 安装、配置文件、登录状态、算力余额、账号已有的因子数量，
以及随技能附带的字段与算子参考，并在任何一步不满足时打印出确切的下一条命令。
这里的脚本在 Windows、macOS、Linux 上都能跑；Windows 上解释器是 `python`，不是 `python3`。

本文里的所有路径都相对于**存放本文件的那个目录**——通常是
`~/.claude/skills/pandaai-factor-online`、`~/.cursor/skills/...`，或者压缩包解压到的位置。
Agent 很少正好从那里启动，所以请以该目录为基准解析这些路径，而不是当前工作目录。
产出的文件则相反：`candidates.txt` 和它的断点文件要放在用户自己的工作目录里，
不要放进技能目录，那里重装一次就被覆盖了。

**2. 按它的提示解决问题，然后停下来等用户。**

| 体检报什么 | 怎么做 |
|---|---|
| `python ... needs Python 3.10 or newer` | 本机有 uv 就 `uv python install 3.12`；否则 <https://www.python.org/downloads/>、`brew install python` 或 `winget install Python.Python.3.12` |
| `pandaai-cli not found on PATH` | 给出 `uv tool install pandaai-cli`，等用户执行 |
| `not logged in` | 顺着下面的登录阶梯往上走 |
| `balance query failed` | token 过期，从阶梯的最后一级重来 |

**登录阶梯。** 不要替用户假设，问清楚他已经做了哪几级，然后带他走没做的：

1. **还没有 PandaAI 账号。** 到 <https://www.pandaaiquant.com/login> 用手机号注册。
2. **注册了但没报名大赛。** 到 <https://www.pandaaiquant.com/factorhub/fourthFactorCompetition/> 报名。
   这一级必须和注册分开说：算力是随报名发放的，跳过它的人照样能登录，然后一个因子都跑不了。
   第 3 步看到余额为 0，基本就是漏了这一级。
3. **没有密码。** 用短信验证码注册的账号不会自动生成密码，
   到 <https://www.pandaaiquant.com/personalcenter?id=1> 设一个。
4. **登录。** 优先推荐直接 `python scripts/bootstrap.py --login`，它会交互式地问手机号和密码，密码不落进 shell 历史；
   参数写法是 `python scripts/bootstrap.py --login`（号码是示例，替换成用户自己的）。
   给具体示例，不要写 `<手机号>` 这种尖括号占位符，
   会有人连尖括号一起敲进去。请用户自己在终端里运行。绝不编造或猜测手机号和密码。
   如果用户主动把凭据交给你、并且你的工具允许，可以替他执行；如果你的工具拒绝执行带密码的命令，
   直截了当说明，把命令交给用户，不要绕过这个拒绝。

用户回来后重新跑一次体检，每一行都是 `ok` 才继续。

**沙盒中的认证排查。** 如果用户终端的 `login` 和 `balance` 都成功，而 Agent 返回
`LOGIN_REQUIRED`，先核对实际 CLI 路径和生效的配置文件路径。沙盒、容器或远程执行器可能无法共享
宿主终端的实时凭据视图或网络上下文。可以把“在沙盒外/宿主环境重复一次只读认证检查”作为排查方向，
但具体操作取决于所用 AI 工具，不能把它当成固定解决方案。严禁把 token 复制到仓库、候选文件、提示词或聊天中。

**3. 用用户能理解的说法汇报账号状态。** 用当前实测单次扣费把余额换算成实验次数；
直接说还能跑多少次——并说明账号上已有多少个因子。

**4. 写任何公式之前，先定死这三个参数。** 问用户，不要替他决定：

- **调仓周期**（1–10 日）。如果比赛在提交时锁定，现在就必须定下来，之后所有候选都在这个周期下评估。
- **回测区间**，比赛 A-first 默认使用提交日前近 5 年；每次 CLI 或服务端升级后都重新探测可用上限。10 年是否可用取决于
  账号与服务端能力。不要强制用户预留样本外；B-regime/走步验证是可选研究路径。
- **本次预算**，这一轮允许花多少次运行。

**5. 提出一批 10–15 个候选的试探清单**，覆盖**不同**假设而不是同一想法的变体，
先把清单给用户过目再创建。先在短区间跑，便宜地暴露公式错误。

**6. 幸存者上全区间**，然后做复盘——归因、证伪、成本校验、决策——**每一批**都做，不要留到最后。

**7. 幸存者做样本外验证**，用第 4 步预留的更早区间，并对照本轮候选数量对应的多重检验阈值汇报结果。

后面各节是每个阶段的展开。第 1、2 步属于上手流程，每台机器只需做一次。

## 产出约定 Output Contract

产出下面这些，放在冷启动时定好的持久工作目录里，而不是临时路径：

- `candidates.txt`：每行一个候选，`名称 ~ 定义 ~ 方向`；定义可以是公式或 Python 文件（按模式选择），**包括你预期会失败的那些**，
  因为这个数量是多重检验的分母
- `candidates.txt.state.json`：`batch.py` 写的断点文件，含每个候选的 factor id、run id 与指标，
  中断后续跑不会重复花算力。每条记录都带一个指纹，绑定当时的模式、定义、方向、区间与调仓周期，
  所以改过的候选会让批次停下来，而不是当作没变过继续复用
- 一张排序表，每个候选给出：Rank_IC、p 值、单调性、多头组超额收益、换手率、折算出的年化成本，
  以及作为排序依据的净值
- 每个幸存候选一条复盘记录：一句话机制、与已有因子集的最高相关性、做了哪项证伪测试及其结果、
  以及「加码 / 正交化 / 放弃」的决策
- 一段简短汇报，说明本轮总共测了多少个候选，以及由此得到的 p 阈值

不要只用多空数字汇报因子，也不要在没说明是否做过样本外验证的情况下把样本内赢家端出来。

## 第 1 步：Python 环境

`pandaai-cli` 需要 Python 3.10 或更高。装成隔离的工具，这样无论当前激活的是哪个虚拟环境，
它都留在 `PATH` 上：

```bash
uv tool install pandaai-cli        # 或 pipx install pandaai-cli
```

如果更习惯项目虚拟环境，`uv venv && uv pip install pandaai-cli` 也可以，但之后每条命令都必须在
激活该环境的前提下运行。两种方式混用，正是「装成功了却提示 command not found」的常见原因：
`pip install` 可能把脚本放进一个不在 `PATH` 上的用户 bin 目录。

`bootstrap.py` 会同时打印运行脚本的解释器和 `pandaai-cli` 背后的解释器，继续往下之前先确认
它们就是这个项目该用的环境。

## 第 2 步：登录

```bash
python scripts/bootstrap.py --login
```

两个参数都不给则改为交互式输入，可以避免密码进入 shell 历史。账号就是在 PandaAI 官网注册的那个；
token 会写入 `~/.pandaai/config.yaml`，之后所有命令复用它。

**没有密码，或者忘了密码？** 到 <https://www.pandaaiquant.com/personalcenter?id=1> 设置。
只用短信验证码注册的账号，在设置之前是没有密码的。

**如果 AI 工具拒绝处理密码**，不要硬绕。请用户自己在终端里运行完整命令（Windows 上是 PowerShell），
然后继续即可。token 会落到配置文件里，所以 Agent 不需要接触凭据也能完成后续全部工作。

**新机器上登录报 `CONFIG_ERROR: 配置文件不存在`。** pandaai-cli 0.1.x 的 `cli.py` 在分发任何子命令
之前先加载配置，而加载器在文件缺失时直接退出——于是 `login` 这个负责创建文件的命令永远轮不到执行。
`bootstrap.py` 会把文件写好；手工处理则是：

```yaml
# ~/.pandaai/config.yaml
gateway_url: https://www.pandaaiquant.com/pandaApi
country_code: '86'
```

## 第 3 步：挖掘之前先看账号状态

```bash
pandaai-cli --json balance                            # 算力余额
pandaai-cli --json factor_list --limit 1 --no-detail  # 返回体里的 total 就是因子数量
```

创建因子不扣算力。2026-08-05 在 CLI 0.1.3 上实测每次运行扣 2 算力，但计费由服务端结算；
用余额除以体检报告的当前实测单次扣费规划批次，并在首个运行后核对 `billing.deducted`。另外扣费结算晚一两分钟，
运行刚返回就去读余额会读少。
因子数量要看，是因为名称会撞车、旧实验会堆积；给每一批起一个独立的名称前缀，方便日后清理。
但**不要用 `factor_delete --pattern` 去清理**：它一个都删不掉，而且报错理由是假的——
0.1.1 上报 HTTP 422，0.1.3 上报 `LOGIN_REQUIRED`，而同一会话里其他命令鉴权都正常。
按 id 删除是好用的。`references/cli.md` 里有一条可直接粘贴的替代命令，它会取唯一 id 后按位置参数传入。另外，不是本次会话创建的东西，未经用户同意不要删。

## 第 4 步：搞清楚有什么可用

写任何公式之前先查下面两份，因为名字写错要花一次运行才能发现：

- [references/fields.md](references/fields.md)：348 个公式模式基础字段，并索引到完整的回测因子目录——
  十四张表共 949 条，覆盖财报三张表、估值与各类衍生指标、技术指标定义、Barra 风险因子，
  以及日频与日内计算因子
- [references/operators.md](references/operators.md)：官方算子手册全文，十一个类别，
  每个函数含签名、说明、用法与示例

公式模式下的可用性可能与数据接口不同，用到陌生字段时先在短区间验证一次。

两种写法。**公式方式**（`--formula`）支持多行与中间变量，系统取最后一行作为因子值，字段名大小写均可。
**Python 方式**（`--code` 或 `--file`）继承 `Factor` 并实现 `calculate(self, factors)`，
返回值是列名为 `value`、以 `[symbol, date]` 为多级索引的 Series，同一套算子照样可用：

```python
class ComplexFactor(Factor):
    def calculate(self, factors):
        close, volume = factors['close'], factors['volume']
        momentum = RANK((close / DELAY(close, 20)) - 1)
        vol_signal = IF(STDDEV(close / DELAY(close, 1) - 1, 20) > 0.02, 1, -1)
        return momentum * vol_signal
```

公式方式迭代更快，多数候选够用；因子需要好几步中间计算时，Python 方式更好维护。Python 的返回契约、官方示例和 CLI 文件模式见 [references/python_factors.md](references/python_factors.md)。

CLI 实际能做的事：

| 能力 | 命令 |
|---|---|
| 用公式或 Python 代码定义因子 | `factor_create` |
| 查看或修改定义 | `factor_info`、`factor_update` |
| 运行分析并取回结果 | `factor_run` |
| 重新查询已完成的运行 | `factor_result` |
| 下载每只股票的原始因子值 CSV | `factor_result <run_id> --download PATH` |
| 列出因子并附一行绩效摘要 | `factor_list` |
| 查算力 | `balance` |
| 按 id 或名称前缀清理 | `factor_delete` |

一次完成的运行会返回 IC 统计（IC_mean、Rank_IC、IC_IR、t 统计量、p-value、单调性）、
每个分组的年化与超额收益及换手率与胜率、当前因子值最高的股票，以及十组图表序列。
完整参数与已知 CLI bug 见 [references/cli.md](references/cli.md)。

**批量读取要先落盘再分析。** 多个 `factor_result` 会携带很大的图表序列；不要并行把完整
JSON 打到对话里。用 `python3 scripts/collect_results.py run_ids.txt --out-dir result-cache`
逐个缓存原始响应并生成紧凑的 `summary.json`，后续分析直接读缓存。脚本可续跑，只有显式
传入 `--refresh` 才会再次请求服务器。

## 平台约束

| 约束 | 取值 |
|---|---|
| 回测区间 | 使用前探测当前服务端上限；比赛 A-first 默认近 5 年，10 年按账号与服务端能力决定 |
| 分组数 | CLI 支持 2–10 组；本技能报告与方向端解析推荐保持 10 组 |
| 股票池 | CLI 0.1.6 固定为 `沪深全A`（比赛规则中的中证全指环境），不可由用户改写 |
| 调仓周期 | 1–10 天，创建时设定 |
| 算力规格 | 固定 cpu=4 / mem=8 / gpu=4 |

如果比赛在提交后锁定调仓周期，那就在**开始挖掘之前**定好，并且所有候选都在这个周期下评估。
1 日调仓下很漂亮的因子，5 日调仓下可能完全不能用。

**分清工作流身份。** `factor_create` 创建一个因子/工作流对象并返回 `factor_id`；`factor_run` 只为该对象创建运行记录，
重复运行不会产生第二个因子；`factor_update` 改日期则会改掉该对象的工作流定义。样本内和样本外验证应从同一份定义分别创建
两个日期不重叠、名称带区间的对象。最终出现在因子看板或准备提交的对象，必须使用准确的日期、调仓周期、分组数和方向；
试探对象与样本外对象只是研究记录，不能混作最终看板结果。

**分组数要单独做选择。** `group-number` 会改变分位数组的宽度，因此会改变分组收益、单调性、换手率和实际持有极端组的集中度；
它通常**不会改变 IC**，因为 IC 是在分组之前用因子值与未来收益计算的。默认用 10 组，保持十分位结果可比；用 5 组做稳健性敏感性检查；
只有明确要做粗粒度多空切分时才用 2–4 组。不同分组数得到的分组收益不能直接横向比较；从试探、全区间、证伪、样本外到最终看板，分组数必须保持一致并显式传给 CLI。

**比赛目标时从基础挖掘就进入 A 优先模式。** 用户明确要按比赛规则准备因子池时，在创建第一个正式候选前就先
确定池的调仓周期、股票池和 10 组报告口径；候选的正式筛选窗口固定为提交日前近 5 年。短窗口只用于检查语法和
字段，不能拿来排序或替代 A。每个 5 年运行通过 `scripts/collect_results.py --cycle <池调仓日>` 从 CLI 的
IC 和 RankIC 图表抽取统一调仓日；RankIC 对有效调仓周期直接取均值，ICIR 和方向性胜率使用匹配的 Pearson IC 序列，
不以月度 RankIC 替代。候选与失败都保留在研究登记表。随后用实际多头端的收益、
换手成本和风险做 C 的历史代理。B 只在正式生效后才有真实记录，提交前必须明确标记为不可得。所有本地结果都标为
“代理”，不要自动提交因子池或宣称得到官方积分。规则与输入边界见
[`references/competition_rules.md`](references/competition_rules.md) 和
[`references/competition_proxy.md`](references/competition_proxy.md)。

**给用户的两条选择建议。** 默认走 `A-first`：把近 5 年 A 代理尽量做高，同时不接受扣成本后明显为负的多头端。
用户也可以明确选择 `B-regime`：承认可能牺牲 A，专门选择在与当前环境相似的历史阶段表现更好的因子，并记录
环境定义、样本长度和失效条件。两条路径都是提交前的研究筛选；最终只进入同一个正式因子池，未来新增记录才是 B。

**比赛口径提醒。** IC 是 Pearson，RankIC 是 Spearman；四项统计均按统一调仓周期生成，RankIC 对有效周期直接取均值，
ICIR 使用完整 IC 序列计算且不年化。A/B 的 IC 胜率不是 `IC>0`，而是按方向统计 `IC>0.02` 或 `IC<-0.02` 的周期占比。
C 分别复合组合和基准日收益后按 `252/N` 年化，SR 使用扣成本后的组合日收益并乘 `sqrt(252)`；换手是当月各调仓日
`sum(abs(w_new-w_old))/2` 之和，可超过 100%。每个自然月净值计算从 1 开始，但实际持仓跨月延续。
因子池提交后，删改仅限每月 1--3 日并受每日 19:00 截止；新增因子下一个统一调仓日生效，再下一个统一调仓日产生首条 IC。
公式/代码修改会清空样本外累计，单纯改名不会。0811 最新口径确认因子池总数不超过 50 只，Skill 和人工提交都适用；
如平台另有每日新增限制，以后台提示为准。

**快照与榜单提醒。** 因子版本不变时，入池时确定的五年 A 历史窗口不按月滚动。月末正式结算使用 official 快照；
同月 revised 替换 official，preview 只用于展示，同一个月不能重复计入。缺月不补 0。季度质量榜对有效月末 Na、Nb
分别取算术平均；季度超额榜先逐月按有效交易日计算 AnnualRex，再对有效月份取算术平均；季度稳健榜使用季度平均
SR 减去最大月回撤的两倍。年度榜直接累加各月最终积分，不把全年原始日账本重新计算一遍 A/B/C。

**五因子组合是下一层，而不是单因子 C 相加。** 当用户有 6 个以上候选时，先统一跑 5 年 A、成本筛选并检查
因子相关性，再枚举所有 5 因子组合形成待验证组合。当前 CLI 没有池级组合回测或日频账本，不能在本地诚实地选出
“官方 C 最高”的组合；必须拿到平台池级账本后才能按 C 排序。详细边界见
[`references/competition_rules.md`](references/competition_rules.md)。

## 编写公式

最贵的一个陷阱，因为它是静默失败的：

```
MA(CLOSE, 20)        # 20 日滚动均值   ← 通常你想要的是这个
TS_MEAN(CLOSE, 20)   # 等价写法
MEAN(CLOSE, OPEN)    # 两个序列求均值，不是滚动窗口
```

`MEAN(CLOSE, 20)` 能解析、能运行，返回一个看起来合理、实际测的是价格水平的因子。
凡是要写回看窗口，先读 [references/pitfalls.md](references/pitfalls.md)；那里还讲了未来函数、
截面算子与时序算子的区别、方向参数，以及为什么几乎一切都和市值相关。

**先用便宜的方式验证。** 跑满长区间之前，先用同一条定义建一个约 3 个月区间的因子跑一次。
语法和字段错误暴露出来花的算力一样，但等待时间少得多：短窗口买到的是时间，不是算力。

## 运行

```bash
pandaai-cli --json factor_create --formula "BIAS(CLOSE,20)" --name "20日乖离" \
  --start-date 20230101 --end-date 20251231 --adjustment-cycle 5 --factor-direction 0
pandaai-cli --json factor_run <factor_id>
```

需要保留研究资产时，即使只有一个候选也用批量脚本。它负责创建、运行、汇总，并在每一步之后落盘，中断后不会重复花算力。每个成功运行还会保留完整的 CLI 原始响应，并生成可读报告和表格：

```bash
python3 scripts/batch.py candidates.txt --start 20230101 --end 20251231 --cycle 5 --prefix "probe-"
```

输入文件每行格式为 `名称 ~ 公式 ~ 方向`：

```
20日乖离 ~ BIAS(CLOSE,20) ~ 0
距60日高点 ~ CLOSE/TS_MAX(HIGH,60) ~ 0
```

重名候选、未来函数和 `MEAN(X, N)` 在解析阶段就会被拒绝，不会送到平台上去花算力。另有三个参数看住预算：

| 参数 | 作用 |
|---|---|
| `--max-runs N` | 跑满 N 次就停，文件里剩下的留到下次；再执行一遍从断点继续 |
| `--retry-failed` | 失败默认是终态，因为重试一次和第一次一样扣算力 |
| `--hypotheses N` | 整个研究累计测过的候选数，用于多重检验阈值 |

每次批次结束，在候选文件同一目录得到三类资产：

- `candidates.results/<run_id>.json`：完整原始 `factor_run` 返回，供以后新增指标时本地复核；
- `candidates.report.md`：按扣成本多头超额排序的研究报告；
- `candidates.report.csv`：可筛选的表格，含 IC、方向端超额收益、换手、年化成本、净超额、方向端夏普、最大回撤和月度胜率。

`--report-only` 只用已保存 state 重建 Markdown 和 CSV，不会调用 CLI 或花算力。报告里的夏普、回撤和月度胜率是**单因子方向端诊断**；它们不能替代比赛池标准化、等权合成后的官方 C。

样本外验证正是「同一批候选换一个更早的区间」，所以当保存的结果与当前候选对不上时，批次会拒绝启动。
请把候选复制到第二个文件里跑更早的区间，不要在原文件上改。

默认先用公式：它便于审阅、字段与算子参考也更直接。用户明确需要路径依赖状态、复杂表格处理或其他公式难以清楚表达的逻辑时，Agent 应自动改走 Python 路径，并说明切换原因。Python 候选单独建立文件，避免和公式定义混淆：

```text
# python-candidates.txt，每行仍是 名称 ~ Python文件 ~ 方向
复杂状态因子 ~ factors/complex_state.py ~ 1
```

```bash
python3 scripts/batch.py python-candidates.txt --mode python \
  --start 20230101 --end 20251231 --cycle 5 --prefix "py-"
```

脚本会在创建前检查 Python 语法、唯一的 `Factor` 子类和 `calculate(self, factors)`；文件内容、模式、方向、区间和周期都会写入指纹。随后先按用户批准的短窗口运行 CLI 验证，再决定是否扩大范围。Python 静态检查不能证明没有未来函数，仍需做短区间试探和证伪。

## 解读结果

平台把多空年化放在最显眼处，而这假设了 A 股参与者建不起来的空头腿。除非用户另有明确目标，默认优先呈现可交易长端的结果；用户也可以自行指定排序指标、成本假设和风险约束。

1. **多头分组的超额收益。** 平台按全市场因子值排序，前10%组成等权组合，并在创建时确定的调仓周期同步调仓。
   分组按因子值升序排列，所以 `--factor-direction 1` 时多头侧是分组10，为 `0` 时是分组1。看错一端，全部结论都会反过来。
2. **十组单调性**：只在极端组起作用的因子很脆弱。
3. **IC_mean 的 t 统计量对应的 p 值**，即表里的 `IC_p` 列；Rank_IC 没有自己的 p 值。
   注意下面的多重检验问题。
4. **换手率**，要折算成成本，而不是当成一个比率引用：

```
年化成本 ≈ 换手率 × 单边成本 × 2 × (252 / 调仓天数)
```

`turnoverRate` 是分析工具返回的方向端单次/周期换手观察值；比赛 C 使用当月各调仓日单边换手率之和，不能直接把单次值
代入官方 C。`batch.py` 默认按单边 0.3%、买卖两边合计 0.6% 折算用于历史筛选；用户可以按资金规模、标的和执行条件修改
成本假设。普通因子挖掘不受 A/B/C 硬目标约束，比赛模式才按比赛口径筛选。

**公开名称与研究说明分开。** 当前 CLI 可靠暴露的是 `--name`，没有稳定可用的描述字段。提交或看板使用不暴露思路的名称，
例如 `F-A17`；在候选状态文件旁维护本地登记表，记录因子 ID、公式或 Python 文件哈希、方向、调仓周期、分组数、日期、经济机制和验证状态。
名称里不要放字段名、算子、窗口或权重。登记表才是 AI 的解释材料和审计记录，看板名称只是标识符。

## 研究复盘流程

**每一批**跑完都做一遍，不要留到最后。

**归因。** 用一句话说清每个赢家的经济机制；说不清就当噪声。然后查它重复了什么——下载因子值，
与已有因子集做截面 Spearman 相关（`scripts/analyze.py corr`）。与已持有因子相关 0.85 的「新」因子不是新的。

**证伪。** 先说清什么能推翻这个结论，然后就去测：剔除市值最小的 20%、按自然年拆开、
回看窗口变动 ±50%、换调仓周期。被证伪的想法记下来，别让它们再回来。

**成本校验。** 套用换手率折算后重新排序。有些榜首撑不过这一步。本地算换手也要带上方向：
`scripts/analyze.py turnover --direction 0` 量的是最低分位，那才是方向为 0 的因子真正持有的一端。

**决策。** 加码、正交化、放弃，三选一，并且写下来。没有显式的「放弃」动作，
死掉的方向一周后会被重新探索一遍。

复盘表与证伪菜单见 [references/playbook.md](references/playbook.md)。

## 统计纪律

- **多重检验。** 在同一份数据上测 N 个因子，小 p 值必然出现。候选到 100 个左右时，
  名义上的 p < 0.05 毫无意义；用 p < 0.05/N 做粗筛。`batch.py` 会打印这个阈值，但 N 默认只算当前文件——
  研究跨了多个文件时，用 `--hypotheses` 传入累计数，否则阈值每批都重置一次。
- **留出样本。** 受服务端实际上限限制，样本外意味着在挖掘前预留一段不重叠区间，把幸存者重建为新的因子对象，
  确认符号和幅度都站得住。
- **保留失败记录。** 它们是校正的分母。
- **少数不相关的轴优先。** 相互相关 0.9 的五个因子，本质上是一个因子加了四道手续。

## 脚本

这些是拿来执行的，不是拿来读的。只依赖标准库。

| 脚本 | 用途 |
|---|---|
| `scripts/bootstrap.py` | 体检：Skill 新鲜度、环境、配置、登录状态、算力、因子数量 |
| `scripts/batch.py` | 批量创建 / 运行 / 汇总，可续跑，按扣除成本后的净值排序 |
| `scripts/analyze.py` | 用下载的 CSV 本地算 Spearman 相关与换手率 |
| `scripts/competition_proxy.py` | 从保存的结果快照离线计算 A/B/C 比赛规则代理；绝不调用 CLI |
| `scripts/selftest.py` | 脚本离线自检，改动任一脚本之后跑一遍 |

## 参考文件

| 文件 | 内容 |
|---|---|
| [references/cli.md](references/cli.md) | 命令、参数、返回结构与已知 CLI bug |
| [references/fields.md](references/fields.md) | 348 个公式模式字段，并索引 `references/fields-*.md` 的 949 条回测因子目录 |
| [references/operators.md](references/operators.md) | 官方算子手册全文 |
| [references/python_factors.md](references/python_factors.md) | Python 因子返回契约、官方示例与 CLI 文件模式 |
| [references/pitfalls.md](references/pitfalls.md) | 会产出「能跑但跑错」因子的陷阱 |
| [references/playbook.md](references/playbook.md) | 算力预算、复盘表、证伪菜单 |
| [references/competition_rules.md](references/competition_rules.md) | 第四届比赛收益率、IC 与积分评分口径 |
| [references/competition_proxy.md](references/competition_proxy.md) | 比赛规则代理的快照格式与离线用法 |
| [references/source_boundary.md](references/source_boundary.md) | 数据、凭据与研究边界 |

## 安全边界

- 实盘取数前先读 [references/source_boundary.md](references/source_boundary.md)。
- 优先用交互式输入而不是 `interactive-login-field`；工具拒绝处理时，把命令交给用户执行，不要绕过这个拒绝。
  不要提交或打印配置文件、token、uid。
- 每次运行都扣算力：先查 `balance`，先用短区间试探，其余批量跑。
- 社区维护，与 PandaAI 官方无关。`pandaai-cli` 是第三方包且行为会变，请自行在平台上核对。
  本文不构成投资建议。
