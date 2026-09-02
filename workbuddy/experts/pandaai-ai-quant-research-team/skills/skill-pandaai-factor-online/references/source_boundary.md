# Source Boundary / 资料与数据边界

## Allowed sources / 可用来源

- Public PandaAI documentation and community articles / PandaAI 公开文档与社区文章
- Data served to the account by the platform itself through `pandaai-cli` / 平台通过 `pandaai-cli` 向账号提供的数据
- Public filings, papers, and vendor documentation / 公开财报、论文、厂商文档
- Exports and notes the user provides themselves / 用户自行提供的导出与笔记

## Not allowed / 不可使用

- Paywalled or member-only content the user has no rights to / 用户无权使用的付费或会员专属内容
- Another participant's factor definitions or results / 其他参赛者的因子定义与结果
- Any attempt to reach platform data outside the documented CLI and account entitlement / 任何绕开文档化 CLI 与账号权限去取数的做法

## Credentials / 凭据

The phone number, password, token, and uid are the user's. Login is
`python scripts/bootstrap.py --login`, or the interactive prompt. If a tool
declines to run a command containing a password, hand the command to the user rather than working
around the refusal. Never print, log, commit, or paste `~/.pandaai/config.yaml`, the token, or the
uid into a transcript or issue.

手机号、密码、token 和 uid 都属于用户。登录用 `python scripts/bootstrap.py --login`
或交互式输入。工具拒绝执行带密码的命令时，把命令交给用户执行，不要绕过这个拒绝。
不要打印、记录、提交 `~/.pandaai/config.yaml`、token、uid，也不要把它们贴进对话或 issue。

## Redistribution / 转载边界

The field and operator references in this repository are indexes compiled from PandaAI's public
documentation, kept for offline lookup and annotated where the original text is easy to misread.
Each file cites its source article. They are not a substitute for the official documentation, which
remains authoritative when the two disagree.

本仓库的字段与算子参考是根据 PandaAI 公开文档整理的索引，用于离线查阅，并在原文容易读错处加了批注。
每个文件都标注了来源文章。它们不能替代官方文档；两者不一致时以官方为准。

## Research boundary / 研究边界

Backtest results are descriptions of a historical sample, not predictions. This repository organizes
research method only: it does not verify any return claim, does not evaluate any product, and does
not constitute investment advice.

回测结果是对历史样本的描述，不是预测。本仓库只做研究方法层面的整理：不验证任何收益声明、
不评价任何产品、不构成投资建议。
