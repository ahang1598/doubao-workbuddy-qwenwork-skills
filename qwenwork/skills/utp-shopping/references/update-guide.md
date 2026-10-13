# 更新指导

当 AI 收到 `[系统通知] utp CLI 新版本...` 的工具返回追加文本时，按本指引处理。

---

## 更新流程概览

```
MCP 启动 → 后台检测新版本 → 静默下载到 ~/.utp/.pending-binary（不替换当前二进制）
                                                    ↓
                                    下次工具调用时注入 [系统通知] 提示
                                                    ↓
                                          询问用户是否升级
                                         ↙              ↘
                                    用户确认升级         用户拒绝升级
                                        ↓                  ↓
                              utp update apply        utp update dismiss
                              qw_action disable        （清理已下载的二进制）
                              qw_action enable
                                        ↓
                                  新版本生效
```

---

## 两种提示状态

### 1. 正在下载中（`updatePrepared=false`）

提示文本包含"正在后台下载中"。此时**无需用户做任何操作**，下载完成后会再次提示。

**AI 行为**：在回复中自然提及"utp 有新版本正在后台下载，稍后会再提醒"，然后继续处理用户当前请求。

### 2. 已下载完成（`updatePrepared=true`）

提示文本包含"已在后台预下载完成"。此时需要**询问用户是否现在升级**。

**AI 行为**：
- 自然地询问："utp 有新版本已下载好，是否现在升级？"
- 等待用户回复后再行动，不要自作主张

---

## 用户确认升级

按以下步骤依次执行：

### 步骤 1：应用待下载的二进制

```bash
utp update apply
```

此命令将 `~/.utp/.pending-binary` 替换到当前 `utp.exe` 路径（使用 Windows rename trick：当前 .exe → .old，新二进制 → 原路径）。

### 步骤 2：禁用连接器

执行 qw_action：

```
qwenwork.settings.connector.custom.utp-connector · disable
```

（QoderWork 系列用 `qoderwork.settings.connector.custom.utp-connector · disable`）

此操作会终止当前 MCP server 进程。

### 步骤 3：启用连接器

执行 qw_action：

```
qwenwork.settings.connector.custom.utp-connector · enable
```

此操作会以新二进制启动 MCP server，新版本生效。

### 步骤 4：告知用户

完成上述步骤后，告知用户"utp 已升级到最新版本"。

---

## 用户拒绝升级

如果用户说"不升级"/"暂时不用"/"先不用了"等，执行：

```bash
utp update dismiss
```

此命令会：
1. 屏蔽当前版本的更新提示（不再弹出 `[系统通知]`）
2. 清理已下载的待应用二进制文件（`~/.utp/.pending-binary`）
3. 当前运行的二进制不受影响

**用户不会被迫升级**——拒绝后磁盘上的二进制仍是旧版本，下次重启也不会变成新版本。

当有更新的新版本发布时，提示会自动恢复。

---

## 手动更新（不依赖通知）

用户也可主动触发完整更新（下载 + 替换 + 提示重启）：

```bash
utp update
```

或指定版本：

```bash
utp update --to 0.6.8
```

或预览（不实际更新）：

```bash
utp update --dry-run
```

手动 `utp update` 会直接下载并替换二进制，不经过"待应用"中间状态。

---

## 注意事项

- **不要在用户没有确认时自作主张执行升级**——始终先询问
- **拒绝升级后不会被迫升级**——二进制不会被替换，下次启动仍是旧版本
- **24 小时检查间隔**——MCP server 每 24 小时检查一次新版本（可通过 `--no-update-check` 禁用）
- **跨会话复用**——如 MCP server 重启时已有相同版本的待应用二进制，会直接复用，不重复下载
