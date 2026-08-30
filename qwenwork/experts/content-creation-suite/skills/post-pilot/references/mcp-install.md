# mcp-autocli 安装流程

## 前置条件
- **Python 3.10+** 已在 PATH（`python --version` 能看到）
- **pip** 可用
- **Microsoft Edge** —— autocli 用专用 Edge 跑登录平台浏览器自动化
  - **Mac**：检测不到会**自动装**：Homebrew cask 优先（`_find_brew` 同时检查
    `/opt/homebrew/bin/brew` 和 `/usr/local/bin/brew`，绕开 spawn PATH 丢失）→
    brew 没装就走 fwlink pkg + `osascript with administrator privileges`，**直接在
    用户屏幕上弹 macOS 系统密码框**，用户敲一次密码即可。装失败 setup 退非零，本
    skill 会重试或求助
  - **Windows**：Edge 一般预装；检测不到只 `[WARN]`，登录平台需用户手动装
  - **Linux**：同 Windows，只 `[WARN]`，需要手动装
- 当前 bundle 内置 **Windows x86_64 + Mac arm64 + Mac Intel** 三平台 autocli 二进制，
  装机零下载；**Linux** 用户安装时 setup 从 GitHub Releases 拉对应平台二进制

## 执行流程

### Step 1: 探测当前状态 + 版本对比
检查 Python 版本 + 已装 mcp-autocli 的版本（**必须解析版本号，不能只看是否装了**）。

```python
execute_shell(
  command="python --version && pip show mcp-autocli 2>&1 | grep -E '^(Name|Version):' || echo 'NOT_INSTALLED'",
  snippet="探测 Python 和 mcp-autocli 版本"
)
```

同时解析 assets 里 wheel 文件名拿到 bundled 版本：`mcp_autocli-X.Y.Z-py3-none-any.whl`
里的 `X.Y.Z`。例如 `mcp_autocli-1.0.6-py3-none-any.whl` → bundled = `1.0.6`。

**决策表**（基于 installed_version vs bundled_version 比较）：

| Python | installed_version | 走法 |
|---|---|---|
| < 3.10 / 不在 | — | 提示用户先装 Python 3.10+，本 skill 终止 |
| 3.10+ | NOT_INSTALLED | **全流程**：Step 2 → Step 3 → Step 4 → Step 5 |
| 3.10+ | < bundled（如 0.6.0 vs 1.0.0） | **必须升级**：Step 2 → Step 3 → Step 4 → Step 5；**严禁**短路 |
| 3.10+ | == bundled | Step 2 跳过 wheel 安装，但**仍要**跑 Step 3（setup 幂等，二进制和扩展已装就跳，Edge 缺失才装）→ Step 4 → Step 5 |
| 3.10+ | > bundled（用户本机比 skill bundle 还新） | 同上 == bundled 处理 |

⚠️ **不要**因为 mcp-autocli 已装就跳到 Step 4！老版本缺工具、缺二进制覆盖、缺依赖自动安装等，**必须按决策表走完整流程**。

### Step 2: 定位并安装 wheel（关键：必须装到沙箱 Python 的 global site-packages）
本 skill 的 `assets/` 目录带了打包好的 wheel（mcp_autocli-1.0.6，约 9 MB，含三平台 autocli 二进制 + chrome 扩展 + 20+ 个 user adapter + 16 个 MCP 工具源码）。
先用 list_files 找到 wheel 的绝对路径（不要硬编码 skill 安装目录，每个 host 不同）。
**模式必须锚定到 skill 自己的 `assets/`**，不要用 `**/` 全局通配：

```python
list_files(
  pattern="assets/mcp_autocli-*.whl",
  snippet="定位 wheel 文件"
)
```

⛔ **严禁使用 `pattern="**/mcp_autocli-*.whl"` 全局通配**：Wukong workspace 的
`artifacts/` 缓存目录可能留有历史版本 wheel（如旧用户上传过 0.2.0 / 0.1.x），
全局通配会同时匹配到 skill 自带 `assets/` 下的新版本和缓存里的旧版本，pip 装到
旧的就会触发"版本不匹配 / unknown tool: check_login"等下游故障。**只有 skill 自带
`assets/` 下的 wheel 才是 single source of truth**。

⚠️ 防御性兜底：若 `assets/mcp_autocli-*.whl` 匹中多于 1 个版本（理论上 skill 自带
应只有 1 份；多份说明 skill 被异常增量塞过），按文件名里的语义版本号取**最大**那个，
并在汇报里加一行"检测到 assets/ 下存在多个 wheel 版本，已选用 X.Y.Z；请通知 skill
作者清理冗余"。若一个都匹不中 → skill 安装不完整，直接终止并提示用户重新跑
`skill_manage create`。

⚠️ **三条硬规矩**（违反任意一条都会导致 `add_server` 报
`connection closed: initialize response`，因为 spawn 出来的进程找不到 mcp_autocli 模块）：

1. 捕获当前正在执行的 Python 的**完全绝对路径**（沙箱 Python），后续所有命令都用它。
   **Mac/Linux 与 Windows 走两套不同的捕获逻辑（见 Step 2a），不要互相套用**
2. 装包时**必须加 `--no-user`**，强制装到沙箱 Python 的 global site-packages，
   不要装到 user-base —— user-base 的位置 Python 启动时不会自动加进 sys.path
3. 先 uninstall 一次，清掉可能已有的 user-base 残留版本

#### Step 2a: 捕获 Python 路径（按系统分支，不要互相套用！）

先判断当前系统：

```python
execute_shell(
  command="python -c \"import platform; print(platform.system())\"",
  snippet="探测当前系统"
)
```

输出 `Darwin` / `Linux` → 走 **Mac/Linux 分支**；输出 `Windows` → 走 **Windows 分支**。

##### ▸ Mac/Linux 分支（Tilde Compaction 防御）

Mac/Linux 终端可能把 `/Users/<you>/...` 显示成 `~/...`，但 `sys.executable` 返回的字符串本身是绝对路径。用 `ord(p[0])` 实证首字符是 `/`(47) 而非 `~`(126) 即可确认。

捕获 Python 路径：

```python
execute_shell(
  command="python -c \"import os,sys; p=os.path.realpath(sys.executable); print(p); print('first_char_ord:', ord(p[0]))\"",
  snippet="捕获 Python 路径 + ord 实证首字符"
)
```

- 预期输出：绝对路径 + `first_char_ord: 47`
- `first_char_ord: 47` → 直接拿第一行字符串往下用，**不做任何 `expanduser` / `replace('~', ...)` 等处理**
- **不要** `| tee /tmp/_pp` 写文件验证（沙箱禁写 `/tmp`，会报 `blocked_operation`）

##### ▸ Windows 分支

Windows 上 `sys.executable` 直接返回带盘符的绝对路径，无需任何额外校验。

```python
execute_shell(
  command="python -c \"import sys; print(sys.executable)\"",
  snippet="捕获 Python 路径"
)
```

直接拿输出的路径字符串用，**不要**加 `realpath` / `assert` / `ord` 等 Mac 防御。

#### Step 2b: 清旧版 + 装到沙箱 global site-packages（通用）

清掉旧版本（不存在也没关系，pip 会 skip）：

```python
execute_shell(
  command="<python_path> -m pip uninstall -y mcp-autocli",
  snippet="清掉旧版本"
)
```

装到沙箱 global site-packages：

```python
execute_shell(
  command="<python_path> -m pip install --no-user --upgrade <wheel_absolute_path>",
  snippet="安装 mcp-autocli wheel"
)
```

校验（这步必须通过，不通过 add_server 一定会挂）—— 看返回的路径必须包含
`...Lib\\site-packages\\mcp_autocli`（Windows）或 `lib/python3.X/site-packages/mcp_autocli`
（Mac），不能含 `python-user-base` 或 `Roaming\\Python`：

```python
execute_shell(
  command="<python_path> -c \"import mcp_autocli; print(mcp_autocli.__file__)\"",
  snippet="验证 mcp_autocli 装在 global"
)
```

### Step 3: setup 子命令（autocli 二进制 + 扩展 + user adapter + yt-dlp/ffmpeg + Edge）
继续用同一个 Python 跑 setup 子命令：

```python
execute_shell(
  command="<python_path> -m mcp_autocli.server setup",
  snippet="装 autocli 二进制+扩展+user adapter+yt-dlp/ffmpeg，Mac 上同时自动装 Edge"
)
```

正常输出**五段**：
- `[1/5] Install autocli binary` → `[OK]`
- `[2/5] Install chrome extension` → `[OK]`
- `[3/5] Install user adapter overrides` → `[OK]` 部署修复版 yaml 到 `~/.autocli/adapters/`
- `[4/5] Ensure yt-dlp + ffmpeg in PATH` → `[OK]` B 站下载和 ASR 的必需依赖
- `[5/5] Prepare profile + check Edge` → `[OK]` 创建 Edge profile + 检测/安装 Edge

**Mac 上 Edge 不存在时**：`[5/5]` 会弹 macOS 密码框（osascript），**立刻告诉用户去桌面找弹框输密码**（可能被挡住，Cmd+Tab 切到桌面）。给 setup 留 15 分钟 timeout。

**setup 退码判断**：
- 退码 = 0 且看到五个 `[OK]` → 进 Step 4
- 退码 ≠ 0 或看到 `[FAIL] pkg installer failed` / `[FAIL] Edge download failed` →
  Edge 装失败（可能是用户取消了密码框，或者下载断了）。**重试一次**：

  ```python
  execute_shell(
    command="<python_path> -m mcp_autocli.server setup",
    snippet="重试 setup（含 Edge 自动装）"
  )
  ```

  重试还失败 → 用 ask_human 告诉用户："Edge 自动装失败两次。请手动跑
  `brew install --cask microsoft-edge`，或去 https://www.microsoft.com/edge/download
  下载 .pkg 双击装。装好后回复'已装好'。" 用户回复后再跑一次 setup 验证。
- 退码 ≠ 0 但 `[FAIL]` 是 binary download（Linux）→ 重试 `setup --force`
- 用户明确不想装 Edge（已知会用不了登录平台）→ 加 `--no-install-edge`：
  `<python_path> -m mcp_autocli.server setup --no-install-edge`

### Step 4: 注册到 Wukong（全自动，无需用户介入）
Wukong 不用静态配置文件，所有 MCP 管理走 `mcp_runtime` 工具。先看 `mcp-autocli` 是否已注册：

```python
mcp_runtime(action="list_servers", snippet="列出 MCP 服务")
```

**没有** → 调 `add_server` 注册（即时建联，无需 reload）。

#### ⚠️ Windows 专属：路径正斜杠化

Windows 上 `<python_path>` 是 `C:\Users\...\.real\...` 反斜杠格式，Wukong 底层
spawn（Node.js `child_process.spawn`）对这种路径解析有坑，会报
`program not found`。**add_server 前必须把反斜杠换成正斜杠**：

```python
# Windows 专属：add_server 前做路径转换
python_path = python_path.replace("\\", "/")
# C:\Users\you\.real\... → C:/Users/you/.real/...
```

正斜杠路径 `C:/Users/...` 对 Node.js spawn 完全兼容。Mac/Linux 不需要这步
（本来就是 `/` 开头）。

#### add_server 注册

⚠️ `command` 必须是 Step 2a 捕获到的 `<python_path>`（Windows 已做正斜杠化），
**不要**用 `mcp-autocli` 这个 console script：

```python
mcp_runtime(
  action="add_server",
  name="mcp-autocli",
  type="stdio",
  command="<python_path>",
  args=["-m", "mcp_autocli.server"],
  snippet="注册 mcp-autocli 到 Wukong"
)
```

#### ⚠️ Windows 专属：add_server 失败自动 remove+add 重试一次

Windows 上 Wukong 偶尔在 stdio handshake 阶段超时，误报 `program not found`。**先 remove + 重新 add**，99% 一次就过：

```python
mcp_runtime(action="remove_server", name="mcp-autocli", snippet="清掉失败的注册")
mcp_runtime(
  action="add_server",
  name="mcp-autocli",
  type="stdio",
  command="<python_path>",
  args=["-m", "mcp_autocli.server"],
  snippet="重新注册（绕开 Windows handshake race）"
)
```

再失败才走 toggle 链路 + ask_human。**Mac/Linux 跳过此步**。

#### 已注册但断开的情况

**已有但断开**（status 非 connected） → toggle 重连，不行就 remove + add：

```python
mcp_runtime(action="toggle_server", name="mcp-autocli", enabled=False, snippet="禁用旧连接")
mcp_runtime(action="toggle_server", name="mcp-autocli", enabled=True, snippet="重新启用")
```

### Step 5: 验证（MCP 连通 + Edge 可启动）

**5a — MCP 服务连通 + 工具列表**：

再次 `list_servers` 确认 `mcp-autocli` 状态为 `connected`，然后验证工具数量。

工具数量验证 = 15（1.0.0 起 server 必须暴露 15 个 Tool；数量不符说明
装上的是老版本残留，回 Step 2 重装）：

```python
execute_shell(
  command="<python_path> -c \"import mcp_autocli; from mcp_autocli.server import server; from mcp.types import Tool; count=len([v for v in vars(__import__('mcp_autocli.server', fromlist=['server'])).values() if isinstance(v, Tool)]); print(mcp_autocli.__version__, count)\"",
  snippet="冒烟验证：工具数 = 16"
)
```

预期：`1.0.6 16`。数量不符 → 回 Step 2 重装 wheel。

**5b — Edge 可启动**（仅 Mac/Windows，登录平台都依赖这个）：

直接用 Python 验证 Edge 二进制存在：

```python
execute_shell(
  command="<python_path> -c \"from mcp_autocli.lib import paths; e=paths.edge_executable(); print('EDGE_OK' if e else 'EDGE_MISSING', e or '')\"",
  snippet="验证 Edge 已安装并可启动"
)
```

- 输出 `EDGE_OK /Applications/Microsoft Edge.app/...`（Mac）或类似 Windows 路径
  → 安装成功
- 输出 `EDGE_MISSING` → Step 3 的 Edge 安装其实没真装上（极少；可能 osascript 静默退出）。
  回到 Step 3 的 setup 重试逻辑

### Step 6: 收尾汇报
告诉用户：

- mcp-autocli MCP 服务已注册并连通
- Edge 已就位
- yt-dlp + ffmpeg 已就位
- user adapter 已部署到 `~/.autocli/adapters/`
- 1.0.6 暴露 **16 个工具**（6 个家族）：采集 5 + 会话 1 + 媒体处理 5 + 账号 2 + 发布 1 + 通用操作 1 + 清理 1。publish 工具使用说明见 `references/publish.md`
- 后续怎么用：
  - **登录平台前置**：先调 `launch_login` → ask_human 确认已登录 → 再调 publish。若跳过 launch_login，publish 会兜底自动起 Edge 登录页，agent 需把 `metadata.edge_launch_instruction` 转述给用户
  - **严禁** agent 自己跑 `pgrep chrome` 排查浏览器 — autocli 用 **Edge**，search 内部已做进程检测
- MCP 安装完成，继续执行 post-pilot 主流程

## 输出规范
- 每步用一句话报当前进度（"装 wheel...完成"、"setup [3/3] 装 Edge..."）
- 出错时把退码 + 关键日志行贴出来，再给具体修复指令
- Step 5 验证结果用清单：`✅ MCP 连通 / ✅ 工具数 = 15 / ✅ Edge 可启动`
- 不要在本 skill 流程里执行真实搜索任务（那是 mcp-autocli 服务的活，不是 installer 的活）

## 异常处理

### 通用

| 现象 | 处理 |
|---|---|
| wheel 路径含 `artifacts/` / `Downloads/` 等非 `assets/` 目录 | 历史缓存残留，**忽略**，只用 `assets/mcp_autocli-*.whl`。assets 下没有 → skill 安装不完整，重新 `skill_manage create` |
| `assets/` 下匹中多个 wheel 版本 | 取语义版本最大的，汇报提示 skill 作者清理 |
| `pip install` 失败 | 看错误信息给用户具体建议 |
| `setup` 退码 ≠ 0 含 `[FAIL] Edge` | Mac Edge 装失败。重试一次；再失败求助用户手动装 Edge |
| `setup` 含 `[FAIL]`（非 Edge） | 看 FAIL 哪一步；binary download 失败重试 `setup --force` |
| `add_server` 返回 `connection closed: initialize response` | mcp_autocli 没装到 global site-packages。`--no-user` 重装 |
| `import mcp_autocli` 路径含 `python-user-base` 或 `Roaming\Python` | 先 `pip uninstall -y mcp-autocli`，再 `pip install --no-user --upgrade <wheel>`。若卸不掉，用 Python `shutil.rmtree` 手动清 |
| 登录平台返回 `autocli_error` + `Chrome is not running` | 磁盘上 autocli 是旧 Chrome-based fork。重跑 `setup --force` 覆盖 |
| `launch_login` 报 `Edge not installed` | 重跑 `setup`，setup 会自动装 Edge |
| 下游调 `check_login` 报 `unknown tool` | 0.3.0+ 已移除该工具，下游需改用 `launch_login` + ask_human |

### Mac/Linux 专属

| 现象 | 处理 |
|---|---|
| Python 路径看着像 `~/.real/...` | 看 `first_char_ord: 47` 确认是绝对路径，直接用，**不做任何 replace/expanduser** |
| 命令带 `tee /tmp/...` 报 `blocked_operation` | 沙箱禁写 `/tmp`，去掉 tee，直接 print |
| `add_server` 报 `program not found` | 回 Step 2a 看 `first_char_ord`；若 47 仍报 → 不是路径问题，查 daemon 崩溃 |
| setup 卡在 Edge 安装几分钟 | 正常，下载 ~200 MB。提示用户去屏幕找密码弹框 |
| Step 5b `EDGE_MISSING` 但 Step 3 没报 FAIL | Spotlight 索引竞态，等 5 秒重跑 Step 5b |

### Windows 专属

| 现象 | 处理 |
|---|---|
| `add_server` 报 `program not found` 但手跑能起 | handshake race，`remove_server` + `add_server` 重试一次 |
| Windows 上套了 Mac 的 `realpath`/`assert`/`ord` 检查 | 删掉，Windows 只需一行 `print(sys.executable)` |
| `list_servers` 显示 active 但 `call_tool` 报 `not connected` | `toggle_server` 关再开，强制重连 |

## 资产清单
- `assets/mcp_autocli-1.0.6-py3-none-any.whl` —— 完整 wheel（约 9 MB），含:
  - **三平台 autocli 二进制**：Windows x86_64 + Mac arm64 + Mac Intel
  - **chrome 扩展**（v1.5.7）：`focused: true` + 10min idle timeout + 6 平台发布页 keep-open
  - **20+ 个 user adapter**：覆盖 douyin/xhs/bilibili/twitter/instagram/weibo/weixin/taobao 的 download/subtitle/publish/search/cart 等场景，setup [3/5] 自动部署到 `~/.autocli/adapters/`
  - **16 个 MCP 工具**：采集 5 + 会话 1 + 媒体处理 5 + 账号 2 + 发布 1 + 通用操作 1 + 清理 1（publish 详见 `references/publish.md`）
  - **依赖自动安装**：yt-dlp + ffmpeg
  - **Mac Edge 自动装**：osascript 弹框免 sudo
  - **setup 强制覆盖**：bytes 比对，干掉磁盘上不匹配的旧 autocli 二进制
