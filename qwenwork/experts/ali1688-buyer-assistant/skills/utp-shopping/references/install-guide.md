# 安装指导

**仅在执行购物操作时发现工具不可用才需要安装**，平常正常使用不必触发：

- CLI 方式：PATH 中的 `utp` 不存在，或执行报 `command not found`
- MCP 方式：环境中找不到 `utp` MCP Server，或 MCP 工具调用失败

安装完成后回到原本的购物流程继续执行，不要因为安装打断用户。

---

## CLI 安装（npm 全局安装，主路径）

CLI 通过 npm 全局安装：

```bash
npm i -g @ut-protocol/utp
```

Windows 下也可直接：
```batch
npm i -g @ut-protocol/utp
```

安装后，`utp` 位于 npm 全局 bin 目录（通常为 `npm config get prefix`/bin/utp；Windows 下为 `npm config get prefix`\utp.cmd）。

本 skill **自带跨平台安装脚本**，一行搞定上述安装 + `utp install`：

**macOS / Linux**：
```bash
bash <skill-dir>/scripts/install.sh --host <当前 Host>
```

**Windows（原生，推荐）**：
```batch
<skill-dir>\scripts\install-win.bat
```

**Windows（Git Bash 备选）**：
```bash
bash "<skill-dir>/scripts/install-win.sh"
```
注意：Git Bash 中路径请使用正斜杠 `/`，不要组合 `cd` 与 `&&`。

### 🔴 `--host` 必须显式传（硬规则）

Agent 跑安装脚本时**必须按自己所在的 Host 显式传 `--host`**，不要裸跑脚本：开发机上通常同时装了 QoderWork / Claude Code / Cursor 等多个 Host，不传参数时脚本只会装到探测顺序里的第一个（`qoderwork` 优先），结果是「脚本报安装成功，但当前 Host 里依然没有 utp 工具」。

| 当前 Host | 传参 |
|-----------|------|
| 千问 Work 中国版 | `--host qwenworkcn` |
| 千问 Work | `--host qwenwork` |
| QoderWork 中国版 | `--host qoderworkcn` |
| QoderWork | `--host qoderwork` |
| Claude Code | `--host claude-code` |
| Claude Desktop | `--host claude-desktop` |
| Cursor | `--host cursor` |

拿不准当前是哪个 Host 时，用 `--all` 对所有探测到的 Host 都装一遍，**不要**省略参数裸跑。

- 脚本幂等，重复运行会升级为最新版本。
- 脚本会把 `--host` 映射成 `utp install --target <target>` 显式传入（不依赖 CLI 自动探测，CLI 自动探测同样是 `~/.qoderwork` 优先）。
- 若全局 `utp` 命令被其它 npm 包占用（npm 报 `EEXIST`），脚本会自动带 `--force` 覆盖重装，无需人工处理。
- **加 `--reset`** 可清除 `~/.utp/` 本地数据和各 Host 的 skill 目录/MCP 配置，然后全新安装。

**手动安装 CLI**：若只想装 CLI 本身，执行上面的 `npm i -g` 命令即可。

---

## MCP Server 配置

MCP 方式依赖 `utp` CLI（MCP Server 由 CLI 启动），请先完成上面的 CLI 安装。

MCP 是面向用户的**唯一主路径**。Server 未接入时，Agent 应**主动帮用户完成接入**——可直接读写当前 Host 的 MCP 配置文件，无需让用户手动操作。配置的**位置和格式因 Host 而异**（Claude Code、Cursor、Claude Desktop 等各不相同），由 Agent 按所在 Host 判断格式，把下面这台 server 写进去：

| 项 | 值 |
|----|----|
| Server 名称 | `utp`（Host 可加前缀，以环境中可用的为准） |
| 启动命令 | `utp`（npm 全局安装后在 PATH 中；安装脚本会自动写入解析后的绝对路径） |
| 启动参数 | `mcp serve`（可选追加 `--session-id <id>`） |
| 传输方式 | stdio |
| 环境变量 | 无 |

> 安装脚本会自动解析 npm 全局 bin 的绝对路径并写入 MCP 配置，无需手动填写。若手动配置，确保路径指向 npm 全局安装的 `utp` 可执行文件。

配置样例（以 JSON 类 Host 为例，实际键名/结构按所在 Host 调整）：

```json
{
  "mcpServers": {
    "utp": {
      "command": "utp",
      "args": ["mcp", "serve"]
    }
  }
}
```

Agent 应**主动**用当前 Host 的标准 MCP 接入手段（配置文件、接入命令、扩展面板等）完成接入。**写完配置后必须引导用户重新加载 MCP server**——改配置只是落盘，server 不会自动启动，绝大多数 Host 需用户手动重载/重启才会加载新 server（Claude Code：`/mcp` 重连或重启会话；Cursor：设置里 reload/toggle 该 server；其它 Host 按其方式）。按所在 Host 给出对应重载方式，用户重载后即走 MCP。

**仅当**确实无法接入（Host 不支持 MCP、无权限改配置、或反复接入失败）才回退 CLI 兜底，并把上表接入信息清楚告知用户以便其手动配置——不要主动向用户提议走 CLI。

---

## 安装阶梯（工具不可用时，失败即自动进下一步）

**不要停下来问"之前装过吗"，直接推进；不在同一轮反复试同一步：**

1. **运行安装脚本**（见上方，**必须带 `--host <当前 Host>`**），完成后不重启，先试第 2 步
   - **专家套件（插件）环境可跳过此步**：套件自带二进制和 `.mcp.json`，无需再跑安装脚本，直接进第 2 步启用连接器
2. **启用 MCP 连接器**（配置已就绪，不需重启 Host）：
   - 千问 Work / QwenWork：调 Host 控制面 `qw_action`，key `qwenwork.settings.connector.custom.utp-connector`，action `enable`（**不要**沿用 `qoderwork.*` 前缀）
   - QoderWork / QoderWork CN：Host 操作 `qoderwork.settings.connector.custom.utp-connector · enable`
   - **专家套件（插件）**：插件 `.mcp.json` 中的连接器名为 `utp-shopping-connector`（非 `utp-connector`）。插件连接器默认未启用，**启用位置在专家套件详情页**（左侧导航「专家套件」→ 点击套件卡片 → 详情页「数据连接」区域的开关），不在连接器设置页面。`qw_action` enable 对插件级连接器无效（返回 ok:false）
3. **兜底**：仅前两步都无效时才建议重启 Host

## 🔴 安装完成后必须停下（硬规则）

**安装/启用成功后，禁止在同一轮回复里继续调用任何购物工具**（discover/search 等）。第一件事只能是回到用户需求：

- 需求不够明确（品类模糊或只给了裸品类词）→ 汇报安装完成，随即进入需求澄清
- 没带具体诉求（只是装好了/说"试试看"）→ 汇报完成并给样例引导语
- 需求已足够具体 → 汇报完成并问"现在就帮你搜『…』吗？"，**等用户确认后才调搜索**

仅限「本轮刚执行过安装/启用」的衔接场景；工具本就可用时直接购物无需确认。

---

## 渠道门禁

渠道门禁已移除。所有 host 均无需额外配置即可访问。
