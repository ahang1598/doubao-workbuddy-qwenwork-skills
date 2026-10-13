# 第三方依赖、镜像与素材来源

处理依赖安装、构建、发布审核或素材来源问题时读取本文件。

## 模板授权边界

- `assets/electron-template/package.json` 当前标记 `license: UNLICENSED`，表示模板自身不是对外开源包。
- 生成给用户的桌宠工程可作为用户项目继续修改、运行和打包；不要把模板自身描述成 MIT/Apache 等开源授权，除非发布 owner 明确变更。
- 发布审核需要区分“模板自身授权”和“第三方依赖授权”。不要用第三方依赖的 MIT/Apache 许可覆盖模板自身授权。

## 直接依赖

以 `assets/electron-template/package-lock.json` 为准；`package.json` 中的范围版本不等于最终锁定版本。

| 依赖 | 锁定版本 | 许可证 | 用途 |
| --- | --- | --- | --- |
| `electron` | 37.10.3 | MIT | 桌面运行时下载器与类型入口 |
| `@electron-forge/cli` | 7.11.2 | MIT | 开发、打包与 make 命令 |
| `@electron-forge/maker-dmg` | 7.11.2 | MIT | macOS DMG |
| `@electron-forge/maker-squirrel` | 7.11.2 | MIT | Windows Squirrel 安装包 |
| `@electron-forge/maker-zip` | 7.11.2 | MIT | ZIP 可移植包 |
| `@electron-forge/plugin-auto-unpack-natives` | 7.11.2 | MIT | native 模块解包 |
| `@electron-forge/plugin-fuses` | 7.11.2 | MIT | Electron fuse 配置 |
| `@electron-forge/plugin-webpack` | 7.11.2 | MIT | Webpack 集成 |
| `@electron/fuses` | 1.8.0 | MIT | Electron fuse 常量 |
| `@playwright/test` | 1.61.1 | Apache-2.0 | E2E 与 soak |
| `@types/node` | 22.20.1 | MIT | Node 类型 |
| `css-loader` | 7.1.4 | MIT | CSS 打包 |
| `mini-css-extract-plugin` | 2.10.2 | MIT | CSS 提取 |
| `sharp` | 0.34.5 | Apache-2.0 | PNG 抠图、归一化和 QA |
| `ts-loader` | 9.6.2 | MIT | TypeScript Webpack loader |
| `tsx` | 4.23.1 | MIT | 测试脚本运行 |
| `typescript` | 5.9.3 | Apache-2.0 | 类型检查 |
| `webpack` | 5.108.4 | MIT | 主进程/renderer 打包 |

## 语义抠图后端

- macOS 14+ 默认编译并调用系统 Apple Vision `VNGenerateForegroundInstanceMaskRequest`；模板只携带 Swift 源码，不分发 Apple 模型或额外二进制依赖。
- Windows 缺少 [`rembg`](https://github.com/danielgatis/rembg) CLI 时，模板可在系统临时目录创建隔离环境并安装固定版本，处理结束后清理；不会修改用户全局 Python 环境。部署者仍须单独审核 rembg、ONNX Runtime 及所选模型权重的许可证和体积。
- `subjectKind: illustration` 使用 `isnet-anime`，`photo` 使用 `birefnet-general`。如果组织未批准模型权重，不得把自动下载包装成模板内置能力。

## 传递依赖注意点

- lockfile 当前主要许可证分布是 MIT、ISC、Apache-2.0、BSD-2-Clause、BSD-3-Clause。
- Sharp 的平台包会引入 `@img/sharp-libvips-*`，许可证为 `LGPL-3.0-or-later` 或组合许可证。发布材料中必须单独列出 libvips 相关条目。
- 当前 lockfile 存在 `@electron/node-gyp` 的 `git+ssh://git@github.com/electron/node-gyp.git#...` 来源。ActionHub 或 CI 沙箱通常没有 SSH 凭据；发布候选应优先替换为 npm/HTTPS 可重复来源，或附上沙箱 `npm ci` 通过证据。
- 机械扫描命中 npm funding URL、维护者邮箱或依赖名中的 `sudo` 时，不要直接定为安全失败；需要人工复核是否来自 lockfile 元数据。

## Electron 运行时来源

- 官方来源优先；组织批准镜像可用，但必须明确域名、版本和完整性校验策略。
- 模板构建脚本当前把预校验缓存映射到 `https://npmmirror.com/mirrors/electron/`。只有在 owner 能确认该镜像被组织批准时，才能在审核材料中称为“组织批准镜像”。
- 不允许为了下载成功关闭 TLS：不得设置 `strict-ssl=false`、`NODE_TLS_REJECT_UNAUTHORIZED=0`，也不得使用 `curl -k`。
- 使用 `PET_ELECTRON_ZIP_DIR` 时，必须按文件名匹配官方 SHA-256 后再注入缓存；不要只因为存在 `path.txt` 或 zip 文件就判定 Electron 运行时完整。

## 用户素材来源

- 用户上传照片、角色图、IP 形象或动作素材时，只能在用户有权使用的前提下制作桌宠。
- 文生图创建 `core-ip` 时，不要主动要求模型仿制受保护角色、商标形象、真人名人或未授权 IP。
- 如果用户要求“像某个受保护角色”，应改为抽象风格和非受保护特征，例如配色气质、姿态、情绪，不复制具体造型标识。
- 生成的联系表和 QA 报告只记录素材文件名、状态、尺寸和触发关系；不要记录用户素材的敏感来源说明。
