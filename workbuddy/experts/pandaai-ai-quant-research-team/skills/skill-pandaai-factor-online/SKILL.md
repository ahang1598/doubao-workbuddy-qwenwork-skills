---
name: pandaai-factor-online
description: "Set up pandaai-cli, log in to PandaAI, and mine, backtest, and iterate quantitative factors on the platform. Use when an agent needs to onboard a user to the PandaAI factor competition, install or log in to pandaai-cli, look up available fields and operators, write or debug factor formulas, run and batch factor analyses, or interpret IC / group-return / turnover results on portable agent platforms such as Claude Code, Cursor, OpenClaw, or Codex-style skill systems."
license: GPL-3.0-only
quantSkills:
  organization: https://github.com/quantskills
  repository: quantskills/skill-pandaai-factor-online
  repository_url: https://github.com/quantskills/skill-pandaai-factor-online
  project_type: skill
  collection: factor-analysis
  license: GPL-3.0-only
  category: factor
  tags: [pandaai, factor-mining, pandaai-cli, a-shares, backtest, onboarding]
  platforms: [claude-code, codex, cursor, openclaw]
  language: zh-en
  status: stable
  validation_level: runnable
  maintainer_type: community
  requires: []
  summary_zh: PandaAI 因子大赛上手与在线挖掘：环境体检、登录、字段算子速查、可续跑批量回测，以及按交易成本折算的复盘流程。
  summary_en: "Onboarding and online factor mining for PandaAI: environment preflight, login, field and operator lookup, resumable batch backtests, and a cost-adjusted research loop."
---

## WorkBuddy PandaAI CLI 登录强制覆盖

本节优先于本 Skill 后续所有安装与登录示例。先运行 `python scripts/bootstrap.py --status`；
未登录时先暂停并取得用户准备确认，再在用户可见 TTY 中运行
`python scripts/bootstrap.py --login`。登录信息由 CLI 直接交互读取，禁止在聊天、任务包、
命令参数、日志或证据文件中接收、拼接或保存。交互登录不得通过命令守卫、管道、重定向
或后台进程运行；登录后只记录脱敏的状态、算力、约可运行次数和因子总数。

## WorkBuddy PandaAI CLI 登录强制覆盖

本节优先于本 Skill 后续所有安装与登录示例。先运行 `python scripts/bootstrap.py --status`；
未登录时先暂停并取得用户准备确认，再在用户可见 TTY 中运行
`python scripts/bootstrap.py --login`。登录信息由 CLI 直接交互读取，禁止在聊天、任务包、
命令参数、日志或证据文件中接收、拼接或保存。交互登录不得通过命令守卫、管道、重定向
或后台进程运行；登录后只记录脱敏的状态、算力、约可运行次数和因子总数。

<!-- qsh-form：quantskillhub 运行页的定制表单声明 -->
```json qsh-form
{
  "version": 1,
  "task": {
    "placeholder": "例如：帮我挖一批 5 日调仓、低换手的反转类因子，并按扣除成本后的多头超额排序",
    "required": true
  },
  "fields": [
    {
      "key": "stage",
      "type": "select",
      "label": "阶段",
      "options": [
        { "value": "onboarding", "label": "上手：环境体检与登录" },
        { "value": "probe", "label": "试探：短区间广撒网" },
        { "value": "full", "label": "全区间：只跑幸存者" },
        { "value": "falsify", "label": "证伪：变体与分年拆解" },
        { "value": "oos", "label": "样本外：预留区间重建" },
        { "value": "review", "label": "复盘：相关性与换手成本" },
        { "value": "competition", "label": "进阶：比赛规则代理评估" }
      ]
    },
    { "key": "start_date", "type": "date", "label": "回测开始日期" },
    { "key": "end_date", "type": "date", "label": "回测结束日期（先按服务端实际上限）" },
    { "key": "cycle", "type": "number", "label": "调仓周期（1-10 个交易日）" },
    { "key": "group_number", "type": "number", "label": "收益分组数（2-10，默认推荐 10）" },
    { "key": "round_trip", "type": "number", "label": "单边交易成本（小数，如 0.003）" }
  ],
  "prompt_template": "任务：{{task}}\n阶段：{{stage}}\n回测区间：{{start_date}} 至 {{end_date}}（先按服务端实际上限）\n调仓周期：{{cycle}} 日\n分组数：{{group_number}}（默认推荐 10）\n单边成本：{{round_trip}}\n附件：{{#attachments}}\n\n先检查 CLI 版本，再用短区间探测服务端回测上限；按 SKILL.md 流程执行，并按用户选择的目标排序候选。"
}
```

# PandaAI Factor Online

Everything needed to go from a bare machine to a running factor analysis on PandaAI, then to iterate
without wasting compute credits.

中文版见 [SKILL.zh-CN.md](SKILL.zh-CN.md)。

## Core Workflow

When a user invokes this skill for the first time in a session, follow this sequence before any
mining work. Do not skip ahead to writing formulas, and do not spend a single run until step 3.

**0. Check CLI freshness first.** Read the installed `pandaai-cli` version before account checks,
and compare it with the user's CLI documentation, official release information, or the currently
available package version. If a newer version exists, report the version and likely flag, result-shape,
or billing changes and get consent before upgrading. After an upgrade, rerun preflight and the offline
self-test; never mix an unverified new CLI with the old compatibility assumptions. For a `uv` tool
install, use `uv tool upgrade pandaai-cli`; for `pipx`, use `pipx upgrade pandaai-cli`. Neither is
silent: report the outcome, then confirm `balance` still succeeds.

**0.1. Check Skill freshness once per session.** `scripts/bootstrap.py` compares this Git checkout
with `origin/main` and only reports whether the published Skill is ahead; it never pulls code. If an
update is available, ask for approval, then use `git pull --ff-only origin main` and run
`python3 scripts/selftest.py` before starting a new batch. Do not update a running or resumable batch
in place. If the Skill was installed without Git or GitHub is unreachable, report that the check is
unknown and continue with the local version.

**1. Preflight.** It costs no compute credits — it only queries `balance` and `factor_list` — and
the sole thing it writes is `~/.pandaai/config.yaml` when that file is missing, which the CLI cannot
create for itself. Run it rather than paraphrasing what it would do:

```bash
python3 scripts/bootstrap.py
```

It checks the Skill checkout freshness, Python environment, CLI install, the config file, login state, compute balance,
the number of factors on the account, and the bundled field and operator references, printing the
exact next command whenever a step is unsatisfied. Every script here runs on Windows, macOS, and
Linux; on Windows the interpreter is `python`, not `python3`.

Every path in this document is relative to the directory holding this file — typically
`~/.claude/skills/pandaai-factor-online`, `~/.cursor/skills/...`, or wherever the archive was
unpacked. An agent is rarely started there, so resolve these paths against that directory rather
than the current working directory. The files you produce go the other way: keep `candidates.txt`
and its state file in the user's own working directory, not inside the skill, where reinstalling
would overwrite them.

**2. Resolve whatever it flags, then stop and wait.**

| Preflight says | Do this |
|---|---|
| `python ... needs Python 3.10 or newer` | `uv python install 3.12` if uv is present; otherwise <https://www.python.org/downloads/>, `brew install python`, or `winget install Python.Python.3.12` |
| `pandaai-cli not found on PATH` | Show `uv tool install pandaai-cli` and wait for the user to run it |
| `not logged in` | Climb the login ladder below |
| `balance query failed` | The token expired; climb the ladder from its last rung |

**Login ladder.** Ask which rungs the user has already done rather than assuming, and walk the ones
they have not:

1. **No PandaAI account yet.** Register with a phone number at <https://www.pandaaiquant.com/login>.
2. **Registered but not entered the competition.** Enter at
   <https://www.pandaaiquant.com/factorhub/fourthFactorCompetition/>. Keep this separate from
   registering: credits are granted on entry, so someone who skips it logs in fine and then cannot
   run a single factor. A zero balance in step 3 almost always means this rung was missed.
3. **No password.** Signing up with an SMS code does not create one. Set it at
   <https://www.pandaaiquant.com/personalcenter?id=1>.
4. **Log in.** Recommend `python scripts/bootstrap.py --login` on its own, which prompts for both values and keeps the
   password out of shell history; the flag form is `python scripts/bootstrap.py --login`, with
   that number an example to replace rather than a real one. Give a
   concrete example rather than `<phone>` placeholders, which users type literally, angle brackets
   and all. Ask the user to run it in their own terminal. Never invent or guess a phone number or
   password. Never accept credentials in chat; use the WorkBuddy interactive login wrapper.
   your tooling refuses commands containing a password, say so plainly and hand the command over
   rather than working around it.

Re-run preflight after the user reports back. Only continue when every line reads `ok`.

**Authentication troubleshooting in sandboxed agents.** If the user's own terminal accepts `login`
and `balance` but the agent reports `LOGIN_REQUIRED`, first verify the resolved CLI and config paths.
A sandbox, container, or remote executor may not share the host terminal's live credential view or
network context. A read-only check outside the sandbox / in the host environment is one diagnostic
direction only; the exact procedure depends on the AI tool. Never copy the token into the repository,
candidate files, prompts, or chat.

**3. Report the account, in the user's terms.** Convert the balance into experiments —
the currently observed per-run charge, so state how many runs are affordable — and mention how many factors are
already on the account.

**4. Fix the three parameters before writing any formula.** Ask the user, and do not guess:

- **Rebalance cycle** (1–10 days). If the competition locks it at submission, it must be decided now
  and every candidate evaluated at that cycle.
- **Backtest window**, subject to the limit reported by the current server capability probe. Use five
  years by default for competition A-first research; probe again after any CLI or server change before
  budgeting. Ten years depends on account/server capability. For research OOS, ask whether the user
  wants a non-overlapping reserved window rather than imposing one.
- **Batch budget**, how many runs this session may spend.

**5. Propose a probe batch** of 10–15 candidates spanning *different* hypotheses, and show the list
for approval before creating anything. Run it on a short window first to catch formula errors
cheaply.

**6. Escalate survivors** to the full window, then run the research loop — attribute, falsify,
cost-check, decide — after *every* batch rather than once at the end.

**7. Validate survivors out of sample** on the earlier window reserved in step 4, and report results
against the multiple-testing threshold for the number of candidates tested.

The rest of this document covers each stage in detail. Steps 1 and 2 are onboarding and only need
doing once per machine.

## Output Contract

Produce, and keep in the persistent working directory settled at cold start rather than a
temporary path:

- `candidates.txt` — one line per candidate, `name ~ formula ~ direction`, including the ones you
  expect to fail, since the count is the multiple-testing denominator
- `candidates.txt.state.json` — written by `batch.py`: factor id, run id, and metrics per candidate,
  so an interrupted batch resumes without re-spending credits. Each entry is fingerprinted with the
  formula, direction, window and cycle that produced it, so an edited candidate stops the batch
  instead of resuming as though nothing had changed
- A ranked table with, per candidate: Rank_IC, p-value, monotonicity, long-side excess return,
  turnover, the implied annual cost, and the net figure the ranking is based on
- A retrospective entry per surviving candidate: mechanism in one sentence, highest correlation
  against the existing set, the falsification test run and its result, and a decision of
  escalate / orthogonalize / abandon
- A short report stating how many candidates were tested in total and the resulting p threshold

Never report a factor on its long-short headline alone, and never present an in-sample winner
without saying whether it has been validated out of sample.

## Step 1: Python environment

`pandaai-cli` needs Python 3.10 or newer. Install it as an isolated tool so it stays on `PATH`
regardless of which virtualenv is active:

```bash
uv tool install pandaai-cli        # or: pipx install pandaai-cli
```

If the user prefers a project virtualenv, `uv venv && uv pip install pandaai-cli` works too, but
then every later command must run with that environment activated. Mixing the two is the usual cause
of "command not found" after a successful install: `pip install` can place the script in a user bin
directory that is not on `PATH`.

`bootstrap.py` prints both the interpreter running the script and the one behind the `pandaai-cli`
executable, so confirm they are the environment the project should be using before going further.

## Step 2: Log in

```bash
python scripts/bootstrap.py --login
```

Omitting both flags prompts for them instead, which keeps the password out of shell history. The
account is the one registered on the PandaAI website; the token is written to
`~/.pandaai/config.yaml` and every later command reuses it.

**No password, or forgot it?** Set one at <https://www.pandaaiquant.com/personalcenter?id=1>. Accounts
created by SMS code alone have no password until this is done.

**If the AI tool refuses to handle the password**, do not fight it. Ask the user to run the full
command themselves in a terminal — PowerShell on Windows — and then continue. The token lands in the
config file, so the agent can do everything else without ever seeing the credentials.

**Login fails on a clean machine with `CONFIG_ERROR: 配置文件不存在`.** In pandaai-cli 0.1.x, `cli.py`
loads the config before dispatching any subcommand, and the loader exits when the file is missing —
so `login`, the command that creates it, never gets to run. `bootstrap.py` seeds the file; to do it
by hand:

```yaml
# ~/.pandaai/config.yaml
gateway_url: https://www.pandaaiquant.com/pandaApi
country_code: '86'
```

## Step 3: Check the account before mining

```bash
pandaai-cli --json balance                          # compute credits
pandaai-cli --json factor_list --limit 1 --no-detail  # `total` is the factor count
```

Creating a factor is free. A successful CLI 0.1.3 Python run on 2026-08-05 deducted 2 credits, but
the server settles billing: divide by the preflight's observed charge for planning, then confirm
`billing.deducted` after the first run. The
balance also settles a minute or two behind, so a reading taken the instant a run returns
undercounts it. The factor count matters
because names collide and old experiments pile up; give each batch a distinct name prefix so it can
be cleaned up later. Do not reach for `factor_delete --pattern` to do that: it deletes nothing and
misreports why — HTTP 422 on 0.1.1, `LOGIN_REQUIRED` on 0.1.3 in a session that is plainly logged
in. Deleting by id works. `references/cli.md` carries a one-line replacement that collects unique
ids and passes them positionally. Never delete anything the user did not create in this session without asking first.

## Step 4: Know what you can use

Consult these before writing any formula, since a wrong name costs a run to discover:

- [references/fields.md](references/fields.md) — the 348 formula-mode base fields, plus an index to
  the backtest factor catalog: 949 entries across fourteen tables covering the three financial
  statements, valuation and derived metrics, technical indicator definitions, Barra risk factors,
  and daily and intraday calculated factors
- [references/operators.md](references/operators.md) — the official operator manual in full:
  signatures, semantics, and a worked example per function, in eleven categories

Availability in formula mode can differ from the data API, so validate an unfamiliar field on a
short window first.

Two authoring modes. **Formula mode** (`--formula`) may span several lines with intermediate
variables; the platform takes the last line as the factor value, and field names are
case-insensitive. **Python mode** (`--code` or `--file`) subclasses `Factor` and implements
`calculate(self, factors)`, returning a Series named `value` indexed by `[symbol, date]`, with the
same operators available:

```python
class ComplexFactor(Factor):
    def calculate(self, factors):
        close, volume = factors['close'], factors['volume']
        momentum = RANK((close / DELAY(close, 20)) - 1)
        vol_signal = IF(STDDEV(close / DELAY(close, 1) - 1, 20) > 0.02, 1, -1)
        return momentum * vol_signal
```

Formula mode is faster to iterate and enough for most candidates; Python mode is easier to maintain
once a factor needs several intermediate steps. See [references/python_factors.md](references/python_factors.md)
for the return contract, official examples, and CLI file mode.

What the CLI can actually do:

| Capability | Command |
|---|---|
| Define a factor from a formula or Python code | `factor_create` |
| Inspect or change a definition | `factor_info`, `factor_update` |
| Run the analysis and get results | `factor_run` |
| Re-query a finished run | `factor_result` |
| Download raw per-stock factor values as CSV | `factor_result <run_id> --download PATH` |
| List factors with one-line performance summaries | `factor_list` |
| Check credits | `balance` |
| Clean up by id or name prefix | `factor_delete` |

A completed run returns IC statistics (IC_mean, Rank_IC, IC_IR, t-statistic, p-value, monotonicity),
per-decile annualized and excess returns with turnover and win rates, the current top-ranked names,
and ten chart series. Full flag reference and known CLI bugs: [references/cli.md](references/cli.md).

**Cache before analysis.** A `factor_result` response also contains large chart series. For multiple
completed runs, use `scripts/collect_results.py` to fetch them sequentially into a local cache and
write a compact `summary.json`; do not stream full JSON responses into the conversation. The command
resumes from cached run IDs and only contacts the server again with `--refresh`.

## Platform constraints

| Constraint | Value |
|---|---|
| Backtest window | Probe the current server before budgeting; use five years by default for A-first research, and treat ten years as capability-dependent |
| Groups | 2–10 supported; use 10 by default for decile reporting, and set it explicitly |
| Universe | CLI 0.1.6 is hard-coded to `沪深全A`, the competition's full-A environment; users cannot override it |
| Rebalance cycle | 1–10 days, set at creation |
| Compute | Fixed cpu=4 / mem=8 / gpu=4 |

If the competition locks the rebalance cycle once you submit, choose it **before** mining and
evaluate every candidate at that cycle. A factor that looks strong at 1-day rebalancing can be
unusable at 5.

**Keep workflow identities straight.** `factor_create` creates one factor/workflow object and
returns a `factor_id`; `factor_run` creates only a run record for that object. Re-running it does not
make a second factor, while `factor_update` changes the object's definition. For in-sample and
out-of-sample validation, create two separately named objects from the same definition with
non-overlapping dates. Reserve the final dashboard/submission object for the exact dates, cycle,
group count, and direction you intend to use; probe and OOS objects are research records.

**Choose groups deliberately.** `group-number` changes quantile bucket width and therefore group
returns, monotonicity, turnover, and the concentration of the held extreme. It does **not** normally
change IC, which is computed from factor values and forward returns before grouping. Use 10 by default
for decile-comparable research and the competition-style report; use 5 as a robustness sensitivity
check; use 2–4 only when a coarse long/short split is the explicit objective. Never compare group-return
levels across different group counts as if they were the same portfolio, and keep the chosen value fixed
across probe, full-window, falsification, OOS, and the final dashboard workflow.

**Competition alignment is separate from IC.** The published competition rule builds its long leg
from the highest 10% of the full universe. Set `--group-number 10` when participating so the
direction-selected extreme group is the same top/bottom decile used in the rule. This aligns group
return and turnover diagnostics; it is not an IC optimization and does not reproduce the official
score by itself.

**Competition goal means A-first mining.** When the user explicitly wants a competition pool, settle
the pool's rebalance cycle, stock-pool setting, and decile reporting before creating the first formal
candidate. The formal screening window is the five years ending on the intended submission date; a
short probe only validates syntax and fields, never replaces A. For each five-year result,
`scripts/collect_results.py --cycle <pool cycle>` samples the CLI RankIC chart at the shared rebalance
dates. RankIC is averaged across valid rebalance periods; ICIR and directional win rate use the matching
Pearson IC sequence directly, without monthly RankIC substitution. Keep all candidates and failures in the research
registry, then screen the direction-selected long side with cost and risk as a C history proxy. B is
unavailable until genuine post-effective records exist. Label every local result a proxy; do not submit
a pool or claim an official score automatically. Details: [`references/competition_rules.md`](references/competition_rules.md).

**Present two choices, not a promise.** `A-first` is the default: maximize the five-year A proxy
without accepting a clearly negative, cost-adjusted long side. A user may explicitly choose
`B-regime`: accept weaker A in exchange for factors that worked in a documented historical regime
similar to today. Both are pre-submission research filters; they feed one formal pool, and only new
post-effective observations become B.

**Competition metric reminders.** IC is Pearson and RankIC is Spearman. IC win rate is directional
`IC > 0.02` or `IC < -0.02`, not merely `IC > 0`; all four statistics use shared rebalance
periods, with RankIC averaged across valid periods and ICIR computed directly from the full IC
sequence without annualization. C separately compounds portfolio and benchmark daily returns and
annualizes each with `252 / N`; SR uses after-cost portfolio daily returns and `sqrt(252)`. C turnover
is the sum of `sum(abs(w_new - w_old))/2` over monthly rebalance dates and can exceed 100%; monthly
NAV resets to 1 for calculation while real holdings carry across months. After pool submission,
add/delete changes are restricted to days 1--3 and the platform's 19:00 cutoff; additions enter on
the next shared rebalance and the first IC arrives at the following shared rebalance. Formula/code
edits reset post-effective history, and a name-only edit does not. The latest 0811 guidance states a
50-factor pool cap for Skill and manual submissions; verify any separate daily cap from the platform.

**Snapshot and leaderboard reminders.** A factor's five-year A window is fixed when it enters the
pool; it does not roll monthly while the version is unchanged. Monthly official settlement uses the
month-end official snapshot; a revised snapshot replaces the official one, and preview is display-only.
Do not count the same month twice. Missing months are omitted rather than filled with zero. Quarterly
quality uses the arithmetic means of valid month-end Na and Nb; quarterly excess return averages each
valid month's separately annualized AnnualRex; quarterly robustness uses quarterly mean SR minus twice
the MaxDD of the worst month. The annual leaderboard sums monthly final points and never recomputes
A/B/C from an annual raw ledger.

**Combination selection is a separate layer.** With six or more candidates, first screen them on the
same five-year A window, cost-adjusted long side, and cross-sectional redundancy, then enumerate
five-factor combinations as pending pool candidates. The current CLI has no pool backtest or daily
pool ledger, so never add or average single-factor C values to claim the best official combination;
obtain the platform pool ledger before ranking combinations by C.

## Writing formulas

The most expensive trap, because it fails silently:

```
MA(CLOSE, 20)        # rolling 20-day mean   ← usually what you want
TS_MEAN(CLOSE, 20)   # identical
MEAN(CLOSE, OPEN)    # mean across two series, NOT a rolling window
```

`MEAN(CLOSE, 20)` parses, runs, and returns a plausible-looking factor that measures price level
instead. Read [references/pitfalls.md](references/pitfalls.md) before writing anything with a
lookback window — it also covers look-ahead operators, cross-sectional versus time-series functions,
the direction flag, and why nearly everything correlates with market cap.

**Validate cheaply.** Before a long-window run, create the same definition over a ~3-month window and run it
once. Syntax and field errors surface at the same credit cost but a fraction of the wall-clock time:
what a short window buys is the wait, not the credits.

## Running

```bash
pandaai-cli --json factor_create --formula "BIAS(CLOSE,20)" --name "20d bias" \
  --start-date 20230101 --end-date 20251231 --adjustment-cycle 5 --factor-direction 0
pandaai-cli --json factor_run <factor_id>
```

Use the batch script even for one candidate whenever the result must remain a reusable research
artifact. It creates, runs, tabulates, and
checkpoints after each step so an interruption never re-spends credits. Each successful run also
retains the full CLI response and produces a readable report plus a filterable table:

```bash
python3 scripts/batch.py candidates.txt --start 20230101 --end 20251231 --cycle 5 --prefix "probe-"
```

Each line of the input file is `name ~ formula ~ direction`:

```
20d bias ~ BIAS(CLOSE,20) ~ 0
60d high distance ~ CLOSE/TS_MAX(HIGH,60) ~ 0
```

Duplicate names, look-ahead operators and `MEAN(X, N)` are rejected while parsing, before anything
reaches the platform. Three flags guard the credits:

| Flag | Effect |
|---|---|
| `--max-runs N` | Stops after N runs whatever remains in the file; re-run to continue |
| `--retry-failed` | Failures are terminal by default, since a retry costs the same as the first run |
| `--hypotheses N` | The study-wide candidate count for the multiple-testing threshold |

Every finished batch writes three durable assets beside the candidate file:

- `candidates.results/<run_id>.json` — complete raw `factor_run` response for later local review;
- `candidates.report.md` — research report ranked by cost-adjusted long-side excess return;
- `candidates.report.csv` — filterable table with IC, direction-selected return, turnover, annual cost,
  net excess, direction-selected Sharpe, maximum drawdown, and monthly win rate.

`--report-only` rebuilds the Markdown and CSV from saved state without invoking the CLI or spending
credits. Sharpe, drawdown, and monthly win rate in these reports are **single-factor held-side
diagnostics**, not official C inputs from a standardized, equal-weighted competition pool.

Re-running the same file with a different window is how out-of-sample validation is set up, so the
batch refuses to start when saved results no longer match the candidates. Copy the candidates into a
second file for the earlier window rather than editing the first.

## Reading results

The platform headlines a long-short annualized return, which assumes a short leg A-share
participants cannot build. Judge candidates on the long side instead:

1. **Long-decile excess return.** Groups are ordered by ascending factor value, so 分组10 is the
   long side when `--factor-direction 1` and 分组1 when it is `0`. Reading the wrong end inverts
   every conclusion.
2. **Monotonicity** across the ten groups — a factor that only fires in the extreme group is fragile.
3. **p-value** of the IC_mean t-statistic — the `IC_p` column; Rank_IC has no p-value of its own —
   subject to the multiple-testing caveat below.
4. **Turnover**, converted into a cost rather than quoted as a rate:

```
annual cost ≈ turnover × round_trip_cost × (252 / rebalance_days)
```

The reported `turnoverRate` is the share of the decile replaced each rebalance, so with ten groups it
saturates near 90%. Use **0.3% as the default one-way cost** — roughly commission plus stamp duty
plus slippage for A-share retail execution — rather than asking the user to supply one; raise it if
they trade small caps or size, and say which figure you used. At a 5-day cycle and 0.3%, 60%
turnover costs about 9 points a year. `batch.py` applies this and ranks by the net figure.

## Research loop

Run this after **every** batch, not once at the end.

**Attribute.** Name the economic mechanism of each winner in one sentence; if you cannot, treat it as
noise. Then check what it duplicates — download factor values and compute cross-sectional Spearman
correlation against the existing set (`scripts/analyze.py corr`). A "new" factor correlating 0.85
with one you already hold is not new.

**Falsify.** State what would disprove the finding, then test that: exclude the smallest 20% by
market cap, split by calendar year, vary the lookback by ±50%, change the rebalance cycle. Record
falsified ideas so they stop coming back.

**Cost-check.** Apply the turnover haircut and re-rank. Some leaders do not survive it. Measuring
turnover locally takes the direction too — `scripts/analyze.py turnover --direction 0` prices the
bottom decile, which is the side a direction-0 factor actually holds.

**Decide.** Escalate, orthogonalize, or abandon — one of the three, written down. Without an explicit
abandon step, dead directions get re-explored a week later.

**Separate public names from research notes.** The CLI currently exposes `--name` but has no reliable
description field. Use an opaque submission name such as `F-A17`, and keep a local registry next to
the candidate state with the factor id, exact formula/Python file hash, direction, cycle, group count,
dates, mechanism, and validation status. Do not put economic ideas, field names, or weights in the
public name. The registry is the AI-readable explanation and audit trail; the dashboard name is only
an identifier.

Worksheet and falsification menu: [references/playbook.md](references/playbook.md).

## Statistical hygiene

- **Multiple testing.** Testing N factors on one dataset makes small p-values inevitable. At ~100
  candidates a nominal p < 0.05 means nothing; use p < 0.05/N as a rough filter. `batch.py` prints
  the threshold, but N defaults to the current file — pass `--hypotheses` with the running total
  once a study spans several files, or the threshold resets with every batch.
- **Optional walk-forward.** Do not force a reserved holdout when the user's objective is to use the
  latest five years to choose a submission. Offer a walk-forward or regime-matched historical check
  as an optional B proxy; it is not the official post-effective B.
- **Keep the failures.** They are the denominator of the correction.
- **Prefer few uncorrelated axes.** Five factors at 0.9 mutual correlation is one factor with extra
  steps.

## Scripts

Execute these; they are not reference reading. Standard library only.

| Script | Purpose |
|---|---|
| `scripts/bootstrap.py` | Preflight: Skill freshness, environment, config, login state, balance, factor count |
| `scripts/batch.py` | Batch create / run / tabulate, resumable, ranked net of cost |
| `scripts/analyze.py` | Local Spearman correlation and turnover from downloaded CSVs |
| `scripts/competition_proxy.py` | Offline A/B/C competition proxy from saved result snapshots; never calls the CLI |
| `scripts/selftest.py` | Offline self-test; run it after editing any script above |

## References

| File | Contents |
|---|---|
| [references/cli.md](references/cli.md) | Commands, flags, result JSON shape, and known CLI bugs |
| [references/fields.md](references/fields.md) | 348 formula-mode fields, indexing the 949-entry backtest catalog in `references/fields-*.md` |
| [references/operators.md](references/operators.md) | The official operator manual in full |
| [references/python_factors.md](references/python_factors.md) | Python factor return contract, examples, and CLI file mode |
| [references/pitfalls.md](references/pitfalls.md) | Traps that produce valid-but-wrong factors |
| [references/playbook.md](references/playbook.md) | Credit budget, retrospective worksheet, falsification menu |
| [references/competition_rules.md](references/competition_rules.md) | Official A/B/C scoring summary and the boundary of local proxies |
| [references/competition_proxy.md](references/competition_proxy.md) | Snapshot format and offline competition-proxy usage |
| [references/source_boundary.md](references/source_boundary.md) | Data, credential, and research boundaries |

## Safety

- Read [references/source_boundary.md](references/source_boundary.md) before a live run.
- Prefer the interactive prompt over passing `interactive-login-field`; if the tool balks, hand the command to the
  user rather than working around the refusal. Never commit or print the config file, token, or uid.
- Every run costs credits: check `balance`, probe on short windows, batch the rest.
- Community-maintained and unaffiliated with PandaAI. `pandaai-cli` is a third-party package whose
  behaviour changes, so verify against the platform. Nothing here is investment advice.
