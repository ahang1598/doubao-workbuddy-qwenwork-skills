# 构建执行与交付

## 先体验，后封装

macOS 开发阶段运行 `npm run test:dev-smoke` 后运行 `npm run dev`；它直接从源码启动，不执行 package，必须通过三个 renderer 的握手后输出 `DEV_PREVIEW_READY`。Windows 完成相同检查后默认优先生成 ready-to-run EXE；当前主机不是 Windows 时只记录该路线，不尝试交叉构建。

用户明确要求其他交付格式时再选择：

- `npm run package:win`：生成本机可直接运行的应用目录，适合先验收；其中 EXE 依赖同目录文件。
- `npm run make:win`：生成 Windows Squirrel `Setup.exe`。
- `npm run portable:win`：生成 Windows 便携 ZIP。
- `npm run make:mac`：在真实 Mac 生成 DMG。
- `npm run portable:mac`：在真实 Mac 生成 ZIP/App。

Windows 默认先做 `package:win`，把可直接双击的 EXE 及其所在目录交给用户继续验收；这是 Windows 的优先路线。只有用户明确需要安装器或传输压缩包时，再做 `make:win` 或 `portable:win`。ZIP 只是传输容器，不能替代对可执行文件路径的说明。

## 唯一受控构建

模板构建脚本必须：

1. `npm run dev`、`npm run test:dev-smoke` 与所有构建共用 `.build/activity.lock`；已有活跃开发、冒烟或构建进程时拒绝并行启动。锁内 PID 已不存在时自动记录并回收过期锁，不把清理责任推给普通用户。
2. Windows 将 `TEMP`、`TMP` 和 Forge `outDir` 指向纯英文的外部隔离目录（优先 `%LOCALAPPDATA%/DoubaoPetBuilder/<project-key>`）；规避跨盘临时文件问题，也避开 Squirrel/rcedit 对中文项目路径的兼容缺陷。Mac 使用项目外临时目录。
3. 在开始前只清理项目内的生成目录；解析并验证绝对路径，不碰源码和素材。
4. 把 stdout/stderr 同时写入 `.build/build.log`，完成后复制到 `release/build.log`。
5. 每 15 秒刷新 `.build/status.json`，记录唯一 PID、模式、当前阶段、开始时间、更新时间和最终结果。
6. `package` 只做一次；Maker 使用 Forge 的 `--skip-package` 复用结果。
7. 总超时采用 `pet-spec.json` 的 `build.timeoutMinutes`，默认 20 分钟；超时后记录并失败，不自动重启。
8. 命令退出后才依据退出码和完整日志判断，不能凭 `.webpack`、`out` 或 `release` 是否存在猜测。
9. Node 25+ 主机必须自动选择受支持的 Node 24 或更早版本执行 Forge；缓存的 Electron ZIP 必须先与官方 `checksums.json` 做 SHA-256 核对。
10. Mac 收集 `.app` 时保留相对符号链接、拒绝绝对符号链接，执行 ad-hoc 签名并用 `codesign --verify --deep --strict` 复核。

## Electron 依赖准备协议

依赖、镜像、许可证和用户素材来源审核同时读取 [licenses-and-sources.md](licenses-and-sources.md)。

Electron npm 包只是下载器和类型定义，平台运行时通常还有 100MB 以上。依赖阶段固定执行：

1. `package.json` 精确锁定 Electron 版本，并只允许锁文件中已知的 Electron、Sharp、esbuild 等必要安装脚本；不得广泛批准未知脚本。
2. 新脚手架只运行一次 `npm ci`。退出码为 0 只表示 npm 阶段结束，不等于 Electron 平台运行时可启动。
3. 紧接着运行 `npm run preflight`。必须同时核对 Electron 包版本、`dist/version`、真实可执行文件；macOS 还要核对 `Electron Framework.framework`。不要只看 `path.txt`。
4. 运行时缺失或半解压时，由模板从带官方 `checksums.json` 的缓存/下载结果恢复到暂存目录，验证探针后原子替换 `dist`，最后写入无换行的正确 `path.txt`。不要先反复删除整个 `node_modules`。
5. 构建优先复用本机 Electron ZIP；使用前必须匹配文件名对应的 SHA-256。可用 `PET_ELECTRON_ZIP_DIR` 指向预先下载的可信缓存目录，但不得把未校验 ZIP 直接解压进工程。
6. TLS/证书失败时停止当前下载并保留日志，检查系统时间、代理、企业根证书和下载源。优先使用证书有效的官方源或组织批准镜像；禁止 `strict-ssl=false`、`NODE_TLS_REJECT_UNAUTHORIZED=0`、`curl -k`。
7. Sharp 缺少预编译运行时时仍回到锁文件安装与平台诊断，不执行临时 `npm install sharp`，也不切换到另一套图片库。

常见判断：

| 现象 | 结论与动作 |
|---|---|
| `Electron failed to install correctly` | 运行 `preflight` 查看真实运行时探针；不要因 npm 包目录存在而判定完成 |
| `path.txt` 存在但应用不能启动 | 检查 `dist/version`、可执行文件和 macOS Framework；由受控恢复替换半安装目录 |
| 证书链错误 | 修复代理/证书或改用可信源；不关闭 TLS |
| 下载很久但进程仍有输出 | Electron 包体积大，按构建总超时与完整日志等待，不按几分钟猜测卡死 |
| Sharp 加载失败 | 检查锁定版本、平台架构和安装脚本许可；不临时换库 |

## 禁止反复换路

- `.webpack` 存在是正常状态，不是冲突证据。只有日志明确出现 `dest already exists` 且没有活跃进程时，才由受控脚本清理后重试一次。
- Squirrel 失败时保留已成功的 package 目录，但不得擅自改成 Forge ZIP、系统压缩或手工伪造 manifest 后宣称原目标完成。
- 如果用户同意改成交付便携版，运行固定 `portable:win` 命令并生成新的独立报告；不要现场修改 `forge.config.js`。
- 不要在构建过程中同时运行 `npm run dev`、`test:e2e` 或第二个 make。

## 成功标准

- `package:win`：`release/<应用>-win32-x64-ready-to-run/` 存在，EXE 能在该目录内启动；明确说明不能只复制 EXE。
- `make:win`：`release/` 中存在本轮新生成的 `Setup.exe` 和 manifest。
- `portable:win`：`release/` 中存在本轮新生成的 ZIP 和 manifest，解压后 EXE 能启动。
- Mac 同理核对 DMG 或 ZIP/App。
- manifest 由脚本从实际文件生成，记录版本、平台、架构、字节数、SHA-256、构建模式和日志路径。
- E2E 与 Soak 使用临时 userData 和后台测试窗口，不抢占用户正在操作的桌面；常规 Soak 至少 5 分钟，发布候选使用 60 分钟。

未完成启动和真人清单时，只能写“构建产物已生成，真人验收待确认”。开发预览、ready-to-run EXE、Setup.exe 和 ZIP 必须分别命名，不得统称“最终版”。
