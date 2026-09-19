# 更新

执行：

```bash
gd-cli update
```

该命令检查 `@gaoding/cli` 的 npm `latest`，更新受支持的 npm 或 pnpm 全局安装，并确保随包 `gd-cli` Agent Skill 已同步；CLI 已是最新版本时仍会同步 Agent Skill。npm 更新只通过 `--allow-scripts=@gaoding/cli` 为本包启用安装脚本，pnpm 更新只通过 `--allow-build=@gaoding/cli` 为本包启用 build lifecycle。

正常使用 CLI 时，版本可用性最多每小时检查一次；存在新版本时，同一本地自然日最多在 stderr 提醒一次。看到提示后执行 `gd-cli update`。自动检查不会更新 CLI，也不会检查或修复 Agent Skill；`CI=true` 时跳过。

如果 `gd-cli update` 提示当前安装由 WorkBuddy 连接器管理，请在 WorkBuddy 中更新「稿定」连接器。不要尝试绕过该安装渠道单独升级 CLI 或同步 Agent Skill；连接器会一起管理并验收匹配版本的 CLI 与 Skill。

命令不接收参数或 `--json`。不支持自动更新的安装来源会给出明确的 npm、pnpm 全局安装命令。若 CLI 已更新但 Agent Skill 验收失败，保留已更新版本，按 stderr 的下一步修复后重新执行 `gd-cli update`。
