---
name: doubao-desktop-pet-builder
description: 创建、生成、修复桌面宠物。适用于“把一张图片/照片/角色图变成桌面宠物”“基于文字描述生成桌宠”“修复已有桌宠”等请求；支持单图、完整动作素材、文字描述和已有宠物工程。普通网页/H5、小程序、仅做 IP/吉祥物/头像/动作图集且不需要桌面应用时不要触发。
---

# 豆包桌宠构建器

先判断模式，再执行对应流程。不要用网页应用替代桌面应用，不调用 `doubao-app-builder`。GUI 工具仅可辅助取证，不作为通过门禁；验收必须依赖自动握手、renderer ready、素材 `naturalWidth`、窗口可见性和用户/真人体验。

## 选择模式与引用

1. 从图片、素材或文字制作桌宠：读取 [creation-workflow.md](references/creation-workflow.md)、[experience-design.md](references/experience-design.md)、[asset-pipeline.md](references/asset-pipeline.md)。
2. 修复、补功能或稳定已有桌宠：读取 [repair-and-packaging.md](references/repair-and-packaging.md)。默认复制独立修复副本，排除 `node_modules`、`.webpack`、`out`、`release`；只有用户明确要求才原地修改。
3. 只打包已有工程：读取 [repair-and-packaging.md](references/repair-and-packaging.md) 与 [build-execution.md](references/build-execution.md)。

只需要 IP/吉祥物/头像/动作图集、不需要 Electron 桌面应用时不要接管；用户同时需要桌宠与定制角色素材时，由本 Skill 统筹桌宠工程，并只在素材阶段调用生图/修图工具。

所有模式都必须读取 [failure-gates-and-qa.md](references/failure-gates-and-qa.md) 与 [user-communication.md](references/user-communication.md)。涉及代码、配置或调试时还读取 [spec-and-template.md](references/spec-and-template.md) 与 [dev-debugging.md](references/dev-debugging.md)。编写或审查 `pet-spec.json` 时同时读取 [pet-spec.schema.json](references/pet-spec.schema.json)，再运行校验脚本。
涉及依赖安装、构建发布、镜像、License 或用户素材来源时读取 [licenses-and-sources.md](references/licenses-and-sources.md)。
涉及提醒、关系数据、文件口袋、日志或全局打字响应时读取 [data-and-privacy.md](references/data-and-privacy.md)。

## 平台默认路线

- 在 macOS 上优先源码开发模式：完成检查后运行 `npm run test:dev-smoke`，再运行 `npm run dev` 供用户试玩；用户未明确要求时不执行 package、make、签名或生成 `.app`。
- 在 Windows 上优先可直接运行的 EXE：完成源码检查与冒烟后运行 `npm run package:win`，交付 `release/<应用>-win32-x64-ready-to-run/<应用>.exe` 及其完整目录；只有用户明确只要开发预览时才停在 `npm run dev`。
- 不跨平台猜测构建结果。当前主机不是 Windows 时，只记录 Windows EXE 路线，不尝试生成或宣称已验证 EXE。

## 创建模式固定顺序

1. 确认输入类型、视觉保真方向、角色身份和目标平台。默认 Windows x64；Mac 只在真实 Mac 上构建当前架构。
2. 根据真实角色设计 2–4 个首版互动。猫可考虑摸头、喂小鱼干、逗猫；狗应改为挠下巴、喂骨头、接球等。不要把猫的文案和道具机械套给其他角色。
3. 生成并校验 `pet-spec` schema v5，再运行 `generate_asset_plan.py`。`character.coreAsset` 必须是独立身份母版，不得指向任一运行时动画帧。参照照片默认设置 `character.style: balanced-cartoon`，生成轻度卡通桌宠贴纸；只有用户明确要求照片级写实才设置 `style: preserve`。`subjectKind` 只按抠图输入选择：照片/真实宠物用 `photo`，卡通角色用 `illustration`，不得用它推导生成画风。
4. 创建唯一 `core-ip` 并让用户确认。优先用图片模型生成或编辑出真实透明 PNG；Alpha 校验失败时，macOS 14+ 只使用 Apple Vision，Windows 只使用模板受控的临时 `rembg`。平台后端失败立即停止，不切换后端、不重复安装。未修改的源帧复用哈希绑定的语义抠图缓存。
5. 只从确认的 `core-ip` 衍生动作。每个状态必须作为同一动作序列一次生成，禁止把各帧当成互不相关的独立生图任务。先完成 `idle` 试产，再按状态继续；固定镜头、身体尺度和脚底基线，不生成文字、边框、地面或投影。
6. 每完成一个状态运行 `npm run inspect:assets -- --state <状态>`。处理器负责语义分割、Alpha/触边校验、统一 512×512 画布和脚底锚点。语义结果不再重复执行背景颜色簇检测；`SUBJECT_TOUCHES_BORDER` 表示源图内容已被裁断，必须重出，禁止用 padding 假装修复；`SOLID_BLOCK` 表示语义抠图失败，必须重出。
7. 用 `scripts/scaffold_project.py` 创建工程，禁止手写或重新创建简化版 Electron 基础工程；缺少依赖时只运行一次锁文件安装 `npm ci`，随后运行 `npm run preflight` 验证并按校验和恢复 Electron 运行时。除模板受控的 Windows `rembg` 临时环境外，禁止反复重装、关闭 TLS 校验、临时安装单个图像库或另写替代抠图脚本；再固定运行 `npm run process:assets`、`npm run check`、`npm test`。默认 `check` 已包含素材、体验和 UI 门禁，不得从默认检查中移除。
8. 运行 `npm run test:dev-smoke`，再按平台默认路线继续。预览就绪前必须确认全部运行帧真实解码成功，并用真实鼠标事件验证左键、右键和拖拽，不得用 IPC 直接调用代替。`DEV_PREVIEW_READY` 只表示运行时就绪；取得桌宠截图或用户明确确认可见后，才可称为“预览成功”。明确源码预览不是最终安装包。
9. 根据体验提出 2–4 个与角色匹配的增补建议，由用户选择后局部迭代；不要默认把全部功能一次塞满。
10. 用户确认体验后运行 `npm run test:e2e` 与至少 5 分钟的 `npm run test:soak`；发布候选使用 `npm run test:soak:release` 做 60 分钟稳定性门禁，再按 [build-execution.md](references/build-execution.md) 构建目标产物并完成真人清单。自动化启动使用后台测试模式，不抢用户焦点。

## 核心门禁

- 资产存在不等于功能完成。`qa:experience` 必须证明每个状态可达、每个互动有入口、每个启用功能有反馈。
- 新生成首版的待机至少 4 帧，眨眼与可见反馈至少 5 帧，首版互动每项 5–6 帧；3 帧只允许用于用户明确接受的极短微动作，不得作为默认方案。
- 面板和提醒窗必须无系统标题栏、无宿主底色框、无系统滚动条，采用角色色板、圆角卡片、清楚层级和角色化文案；原生表单控件必须重置外观。右键菜单与托盘菜单使用克制且语义匹配的 emoji。
- 托盘图标必须从确认的 `core-ip` 生成透明 PNG，并在运行时验证 `nativeImage.isEmpty() === false`；禁止用未经验证的 SVG data URL 或交付空白图标。
- 默认桌宠应以约 130–170px 的可见主体起步，并提供迷你/小/标准/大四档；最小档不得仍接近 200px。
- 先预览再扩展，先 `dev` 再 `package/make`。用户未确认基础体验时不要进入安装包构建。
- macOS 的 `npm run dev` 必须使用 Forge 源码开发服务器，不得先 package 再启动；不得创建 `out`、`release` 或 `.app`。Windows 的优先 EXE 路线只在真实 Windows 主机执行。
- 构建只能启动一个受控任务，保存完整日志和状态；不得按 1–3 分钟猜测超时、反复停止重来，或把 `.webpack` 存在当成冲突证据。
- Webpack 编译完成、Electron 进程存在或 runtime ready 都不等于成功。只有全部素材真实加载、窗口截图可见且真实鼠标交互通过，才能宣称桌宠启动成功。
- 严格 CSP 与 Webpack 必须兼容。renderer 固定使用非 eval 的 `source-map`；禁止通过加入 `unsafe-eval` 掩盖开发配置错误。
- 依赖准备是内部确定性步骤。除模板受控的 Windows `rembg` 临时环境外，不要临时 `pip install`、`npm install` 或边做边换抠图方案。
- Electron npm 包存在或 `npm ci` 返回 0 不代表平台运行时完整；必须通过 `preflight` 的版本、真实可执行文件/Framework 和 `path.txt` 检查。证书失败时不得设置 `strict-ssl=false`、`NODE_TLS_REJECT_UNAUTHORIZED=0` 或使用 `curl -k`。
- Electron template contract v5 将 `package.json`、锁文件、素材处理器和全部 QA 入口纳入 `.doubao-pet-builder.json` 哈希保护。禁止删除检查项、直接调用 Forge 绕过启动器或手工刷新哈希。
- Squirrel 失败时保留日志并报告，不得擅自改 Forge 配置、手工压 ZIP、伪造清单或把替代产物冒充原目标。

## 输出边界

- macOS 开发预览：`npm run dev`，直接从源码运行，只用于当前机器试玩，不生成 `.app`，不能称为最终版或交付包。
- Windows 首次可执行交付默认运行 `npm run package:win`，直接指出 `release/<应用>-win32-x64-ready-to-run/<应用>.exe`；该 EXE 依赖同目录文件，不能单独拎走。安装版 `Setup.exe` 或传输用 ZIP 仅在用户明确选择后再做，ZIP 不能作为唯一的“可执行程序”答复。
- Mac 在真实 Mac 上先生成并验证 `.app`；用户明确需要分发格式时再生成未签名 `.dmg` 或 ZIP。
- 明确提示未签名应用可能触发系统安全警告。
- 不承诺代码签名、公证、应用商店、Universal 包、自动更新、云同步、账号、语音或联网 AI 对话。
- 全局打字响应必须获得明确授权；只产生活动脉冲，不读取或保存键值，失败时自动降级。

## ActionHub Tool 边界

- Shell 长任务使用 `ShellExec` 启动，使用 `ShellWait`/`ShellView` 读取状态和日志；不得因为短时间无输出反复重启同一构建。
- 需要生成或编辑素材时优先调用 online 生产 `image_gen`/`image_edit`；不要选用 unpublish 测试同名 Tool。
- 文件读写只作用于当前工程、独立修复副本、生成素材和明确交付目录；不要扫描或复制用户无关目录。
- GUI 取证工具只用于辅助观察窗口、截图或人工排查，不替代 `DEV_PREVIEW_READY`、renderer ready、IPC、素材加载和真人试玩。

## 确定性工具

- `python scripts/validate_pet_spec.py <pet-spec.json>`：校验配置、功能触发和动态帧门禁。
- `python scripts/generate_asset_plan.py <pet-spec.json> --output <asset-plan.json>`：按状态生成逐帧提示词、触发入口、动作阶段和禁止元素清单。
- `python scripts/scaffold_project.py --spec <pet-spec.json> --assets <素材目录> --output <新目录>`：创建独立工程，默认拒绝覆盖。
- v2 的母版语义和素材处理链不兼容旧 contract；修复旧工程时创建独立 v2 副本并重新脚手架，不手工刷新旧工程哈希。
- `python scripts/audit_project.py <工程目录> --json <报告路径>`：只读审计安全、功能覆盖、路径和打包配置。
- `python scripts/package_skill.py --output <发布包.zip>`：从干净 staging 目录生成发布 ZIP，校验模板契约，并从解压后的 ZIP 实际完成一次回归脚手架。
- `python scripts/generate_regression_fixture.py`：仅维护 Skill 自带的 40 张合成回归素材；生成结果禁止作为用户角色素材交付。

脚本失败时解决原因，不得绕过检查、硬改报告或用重新生图代替确定性修复。
