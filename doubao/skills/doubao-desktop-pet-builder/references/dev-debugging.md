# 源码开发与调试

## 平台路线

- macOS：默认执行源码开发链路，不先 package。运行 `npm run test:dev-smoke` 后运行 `npm run dev`。
- Windows：先完成相同的源码检查与冒烟，再默认执行 `npm run package:win`，验证 ready-to-run EXE 及其完整目录。
- 非 Windows 主机只记录 Windows EXE 路线，不交叉构建或宣称已验证。

## 开发链路

1. 先运行 `npm run doctor` 查看 Node、Electron、模板哈希、端口和素材报告，再运行 `npm run preflight`、`npm run check` 和单元/QA 检查。
2. 运行 `npm run test:dev-smoke`，使用临时 userData 和临时调试端口验证交互、设置、提醒、窗口与拖拽 IPC；结束后删除测试数据并关闭调试实例。
3. 运行 `npm run dev`。该命令只允许调用 Forge start，不允许 package、make、签名或创建 release。
4. 等待 `.build/runtime-ready.json`。只有 pet、dashboard、reminder 三个 renderer 都完成 bootstrap，IPC 与素材检查通过且桌宠可见时，输出 `DEV_PREVIEW_READY`。
5. 保持普通开发实例运行供用户试玩。不要保留远程调试端口。

## CSP 与 Webpack

renderer HTML 保持严格 CSP：

```html
script-src 'self'
```

Webpack renderer 固定使用：

```js
devtool: 'source-map'
```

禁止 `eval`、`eval-source-map`、`cheap-module-eval-source-map` 等配置。出现 `Refused to evaluate`、`unsafe-eval` 或 CSP `EvalError` 时，修复 Webpack；不要向 CSP 添加 `unsafe-eval`。

## 成功证据

以下任一项都不能单独证明成功：

- `tsc --noEmit` 通过；
- 本地 HTTP 返回 200；
- Forge 输出 `Launched Electron app`；
- Electron 主进程存在；
- 三个 BrowserWindow 数量正确；
- 静态 HTML 可见。

必须同时证明：

- 三个 renderer 分别报告 ready；
- renderer 控制台没有 CSP、未捕获异常或 preload 错误；
- `window.petAPI` 可用；
- 宠物素材 `naturalWidth > 0` 且素材数匹配；
- 桌宠窗口可见；
- 隔离冒烟测试完成互动、设置恢复、提醒创建/删除、窗口显示/隐藏和拖拽 IPC。

## 数据与进程隔离

- 冒烟测试设置独立的临时 `userData`，不得增加用户真实亲密度或留下测试提醒。
- 普通开发实例和调试实例共用活动锁，不并行启动。
- 启动器自动选择 Webpack、web-multi-logger 和 smoke 调试端口，并将实际值写入 `.build/dev-status.json`。只有需要固定端口时才设置 `PET_DEV_PORT`、`PET_LOGGER_PORT` 或 `PET_SMOKE_PORT`；显式端口被占用时直接报错。
- 调试完成后关闭 CDP 端口和测试实例，再启动无调试端口的普通开发版。
- Ctrl+C 时终止 Forge 与 Electron 子进程树并释放活动锁。

## 常见失败

- `Electron failed to install correctly`：不要直接重跑 `npm install`。运行 `npm run preflight`，检查 Electron 版本、`dist/version`、平台可执行文件、macOS Framework 与 `path.txt`；受控恢复完成前不得启动 Forge。
- Electron 下载出现证书错误：保留原始 URL 与证书错误，检查系统时间、代理和企业根证书；使用证书有效且可按官方 SHA-256 验证的源。禁止关闭 npm strict SSL、全局 TLS 校验或使用 `curl -k`。
- `node_modules/electron` 存在但运行时残缺：这是半安装，不是缓存命中。由 `preflight` 从已校验 ZIP 解压到暂存目录并原子替换，不反复删除整个依赖树。
- 安装长时间无结论：Electron 平台 ZIP 通常超过 100MB。观察唯一安装/构建进程与日志，在配置总超时内等待，不并行重试。
- Sharp 加载失败：核对平台架构、锁文件版本和安装脚本许可；只允许重新执行受控的完整锁文件安装，不单独安装或临时编译替代库。
- 界面显示但按钮无效：先查 renderer 控制台与 CSP；不要先改 IPC。
- 类型检查通过但功能无效：执行 runtime ready 与 dev smoke。
- 只有宠物窗口正常：检查 dashboard/reminder bootstrap ready。
- 测试后数据变化：测试错误地使用了真实 userData，修复隔离后恢复测试数据。
- 重复窗口：终止受控实例并核对活动锁，不并行重启。默认端口被其他程序占用时启动器自动后移；显式配置端口冲突时更换该环境变量，不直接修改受保护的 `forge.config.js`。
- 模板哈希不匹配：先确认工程契约版本。v3 且关键文件未漂移时运行当前 Skill 的 `scripts/migrate_project.py`；已有漂移时保留差异并人工迁移，不手工刷新 `.doubao-pet-builder.json`。
