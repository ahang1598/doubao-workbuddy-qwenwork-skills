# WorkBuddy PandaAI CLI 登录与大赛执行契约

本契约只适用于 WorkBuddy 版本。PandaData Connector 负责真实金融数据；PandaAI CLI
负责因子大赛账户登录、因子创建、平台回测和结果下载，两者不能互相替代。

## 主流程状态

1. 标准版或审计版进入 PandaAI 阶段时，先运行：

   ```text
   python scripts/bootstrap.py --status
   ```

2. 只接受以下状态：

   - `READY`：CLI、版本、命令契约、认证、余额和因子列表均已验证，可进入参数确认。
   - `CLI_MISSING`：停止，由用户在平台允许的终端中安装 `pandaai-cli >= 0.1.6`。
   - `CLI_VERSION_UNSUPPORTED` / `CLI_CONTRACT_UNSUPPORTED`：停止并升级 CLI。
   - `LOGIN_REQUIRED`：先询问用户是否已准备在可见终端中输入登录信息。
   - `LOGIN_REQUIRES_INTERACTIVE_TERMINAL`：WorkBuddy 当前执行通道没有 TTY，停止并要求
     用户在可见终端运行同一登录入口。
   - `READY_AFTER_LOGIN`：交互登录后认证验证通过，可继续。

3. 只有用户明确确认已准备好后，才在用户可见、支持 TTY 的终端运行：

   ```text
   python scripts/bootstrap.py --login
   ```

4. 登录程序只调用无命令行凭证参数的交互式 `python scripts/bootstrap.py --login`。手机号和密码由 CLI
   直接读取，专家、主 Agent、任务包和命令守卫都不得接收这些值。

5. 登录成功后立即重新运行 `--status`，只记录脱敏后的 CLI 版本、认证状态、可用算力、
   约可运行次数和因子总数。禁止记录账户 ID、用户 ID、手机号、Token、原始配置内容、
   原始 `balance` 或 `factor_list` 响应。

## 配置持久化

- 登录入口仅在配置不存在时创建不含秘密的 `~/.pandaai/config.yaml` 基础配置：
  `gateway_url` 与 `country_code`。
- CLI 登录后自行把认证状态写入该文件。WorkBuddy 必须提供持久化用户目录，否则每个会话
  都会丢失登录状态并应返回 `BLOCKED_CLI_LOGIN_CAPABILITY`。
- 不得把该配置复制到专家包、项目目录、证据目录、日志、任务包或最终报告。

## 不可录制登录

交互登录不得通过 `workflow_guard.py exec`、管道、重定向、后台进程或任何捕获 stdin 的
执行器运行。登录完成后再由命令守卫执行脱敏的 `bootstrap.py --status`，以此作为审计证据。

## 大赛收费闸门

登录完成不等于授权消费算力。任何 `factor_create` / `factor_run` 或批量实验前，仍必须：

1. 确认调仓周期 1–10 日。
2. 确认不超过三年的回测窗口和独立样本外窗口。
3. 展示候选列表、总候选数、预计单次约 2 算力和批次预算。
4. 获得用户对本批次的明确批准。
5. 通过命令守卫运行收费命令，保留因子 ID、run ID、候选文件哈希和脱敏结果。

没有 `READY`/`READY_AFTER_LOGIN` 状态或没有收费批准时，禁止创建或运行因子。
