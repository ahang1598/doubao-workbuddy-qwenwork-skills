# 本地字体资源与执行契约

本文用于 Canvas／本地字体文件的来源、许可、下载、注册与字形核验。先按 [字体推荐入口](font-recommendation-list.md) 选型；HTML 浏览器字体直接执行 [Web 字体契约](web-font-contract.md)，不进入本地下载流程。pure-image 只借用视觉建议。字体资源处理保持已选产物格式。

## 1. 职责分层

| 文件 | 唯一职责 |
|---|---|
| `references/rendering/font-recommendation-list.md` | 视觉选型统一入口；精选候选、查询诊断与真实文案试排，不负责资源准入 |
| `assets/fonts/font-curated-pool.json` | 推荐候选、主题排序、语种角色、组合映射与平台注册查询镜像 |
| `scripts/runtime/select_fonts.py` | 查询同一 JSON；不下载、不安装、不判定实际字形覆盖 |
| `references/items/fonts.md` | 供明确引用本表的 Canvas Item 字体字段核对精确 family、已注册 normal/italic 字重；不约束 HTML DOM，当前环境仍需验证 |
| `assets/fonts/catalogs/*.json` | 字体名称、语种、来源、许可和预期本地路径的元数据目录 |
| `assets/fonts/font-cdn-manifest.json` | 允许 Canvas／本地通道下载并核对大小、MD5 的已验证 CDN 对象 |
| `assets/fonts/web-font-manifest.json` | 与目标前端对齐、允许 HTML 浏览器直接加载的 Web family／face 白名单 |
| `scripts/runtime/resolve_font.py` | 按目标通道解析精确字体、真实 face、资源状态与对应契约；不改变既定产物格式 |
| `assets/fonts/packages/` | 运行时本地字体缓存；不存在不代表目录损坏 |

不得在本文件重复全部字体名称。目录 JSON 是名称与元数据索引，但目录中的 `local_paths` 只表示预期落盘位置，不证明文件已经存在。

## 2. 当前资源状态

三个目录文件提供：

| 目录 | 语种范围 | 记录数 |
|---|---|---:|
| `assets/fonts/catalogs/chinese.json` | 中文及 CJK | 187 |
| `assets/fonts/catalogs/latin.json` | 拉丁字母 | 874 |
| `assets/fonts/catalogs/multilingual.json` | 日、韩、泰、阿拉伯、越南等 | 500 |

这些记录可用于检索，资源状态分为以下类别；正式字体排版须通过本次目标环境的许可、实际加载、真实 face 和字形覆盖核验。只有实际 Item 字段引用平台字体表时，才额外以该表检查注册资格；HTML DOM 不受该白名单限制，但仍须通过 HTML 协议的目标环境验证：

- `ready`：本次目标渲染环境已实际加载正确 family/face，许可、真实字重和文案覆盖均通过；仅本地文件存在不足以标记 ready；
- `cdn_available`：字体位于已验证 CDN manifest，可按明确操作下载；
- `not_installed`：只有目录元数据，没有可验证本地文件或 CDN 条目；
- `blocked_by_license`：资源存在，但许可不足以支持当前用途。

运行时状态以当前渲染环境实测为准，不读取 catalog 中的历史状态自报。查询器只返回 `local_present`、`cdn_listed_not_rechecked`、`not_installed` 或 `unresolved`；不会生成 `ready`。`listed_not_runtime_verified` 仅表示匹配平台表，不能等同字体实际加载。未安装、待解析或许可阻断的候选可保留检索记录，不能当成正式可用字体。

## 3. CDN 规则

真实 CDN 根地址：

```text
https://lf-flow-web-cdn.doubao.com/obj/flow-doubao/doubao/infinite-canvas/fonts/v1
```

`*` 只表示对象路径占位，不是可请求 URL，也不能从字体名称任意拼接。Canvas／本地通道只有 `assets/fonts/font-cdn-manifest.json` 中 `verified=true` 的完整 URL 可以自动下载；HTML 直接注入只接受 `assets/fonts/web-font-manifest.json` 中 `verified=true` 的完整 URL。Canvas 下载清单中的 URL 必须是 Web 字体清单 URL 的子集，避免同一字体对象在两种消费路径中漂移；该关系由字体回归测试核对。

当前已验证：

- 思源黑体简体 VF；
- 抖音美好体；
- 优设得意黑。

新增 CDN 字体时必须记录：

- catalog ID；
- 预期本地路径；
- 完整 CDN URL；
- 文件大小；
- MD5；
- Content-Type；
- 实际验证日期。

仅替换 CDN 域名而保留旧 `assets/fonts/packages/...` 对象路径是无效的；已实测该旧路径返回 404。

## 4. 强制选择顺序

1. 从 [字体推荐入口](font-recommendation-list.md) 保留用户／参考约束，以真实文案判断候选；查询结果不证明资源可用。
2. 按真实文案选择适用语种，字形覆盖在目标环境渲染后核验；失败按[回退规则](#7-回退规则)处理。
3. 先保持字形与阅读任务适配，再检查适用的平台约束、许可和资源；只有未锁定精确字体时，拒绝项才可传 `--exclude` 继续查找，不以资源方便压过用户或参考约束。
4. 使用精确 catalog ID 核对资源及目标环境的 family、真实 face/字重。实际 Item 字段引用字体表时，读取 `references/items/fonts.md` 或当前平台的实际清单；本地安装不能绕过其注册门禁。HTML DOM 按 HTML 协议核验，不因未列该表而拒绝，也不以本地安装替代目标端加载证据。未经证实的别名、CN/SC/VF 或轻量变体不可合并成同一个可用实例。
5. 返回 `cdn_available` 时，使用下载 manifest 中已验证的 URL，核对大小、MD5 与 Content-Type。
6. 许可与资源通过后写入实现源，在目标环境核验实际 family/face、字重、字形覆盖和排版；按第 6 节记录结果，可编辑文字保持原生。

## 5. 字体许可

- 目录记录不等于完成许可核验。
- 默认只自动下载明确标记为开源且许可证属于 OFL、Apache 或 Ubuntu Font License 的条目。
- 非标许可、链接失效、条款不清或禁止再分发时，按现有授权范围确认用途；查询器不下载资源，也没有 `--allow-license-risk` 下载开关。不得调用不存在的参数或把推荐当成许可。
- 系统字体可记录 `origin: system`，但不得复制进 Skill 或交付包。
- 字体子集化、修改字体、收费字体服务和公开再分发需要额外许可判断。

## 6. 协议无关字体契约

本地流程仅在当前 workflow 要求时提供 `font-contract.json`，记录目标环境已核验的字体事实与角色；不据此切换产物格式。以下示例供该流程交换数据，HTML 记录按 [Web 字体契约](web-font-contract.md) 维护。

```json
{
  "families": {
    "Resolved Family Name": {
      "source": "target_environment",
      "availability": "verified",
      "origin": "local",
      "paths": ["/absolute/path/to/font.otf"],
      "weights": [400, 700],
      "fallback_stack": ["PingFang SC", "Microsoft YaHei", "sans-serif"],
      "coverage_status": "complete"
    },
    "PingFang SC": {
      "source": "target_environment",
      "availability": "verified",
      "origin": "system",
      "paths": [],
      "weights": [400, 600],
      "fallback_stack": ["Microsoft YaHei", "sans-serif"],
      "coverage_status": "complete"
    }
  },
  "roles": {
    "hero": {"family": "Resolved Family Name", "weight": 700},
    "body": {"family": "PingFang SC", "weight": 400}
  }
}
```

- family key 必须与当前渲染环境识别到的真实字体家族名完全一致；
- `source` 固定为 `target_environment`，只有目标渲染环境已实测可用才记录 `availability: verified`；未验证候选不能写成已就绪契约；
- `origin: local` 记录本地资源来源，只能使用已实测存在的真实绝对路径；本地安装不代表目标端可用；
- `origin: system` 记录系统来源，仍须在目标渲染环境按精确 family name 验证；
- CDN URL 和本地下载记录不能冒充目标端已就绪；资源核验后还须验证目标渲染环境的真实字体；
- `roles` 只绑定文字职责、字体家族和真实字重，不绑定对象类型或实现协议；
- 其他格式仅在已选 workflow 确实要求契约时，由该 workflow 完成上述交换字段的映射；字体文档不提供切换格式的理由。

## 本地字体资源核验

按需使用 [资源解析器](../../scripts/runtime/resolve_font.py) 核验已获取的字体。WOFF／WOFF2 解码依赖 [素材工具依赖](../../scripts/runtime/requirements-assets.txt) 中的 FontTools 与 Brotli；缺少依赖或二进制损坏时必须报告未支持／未就绪，不能据后缀声称字形覆盖通过。

注册目录保留包内相对层级；不同子目录的同名字体互不覆盖。写入前检查全部目标，同内容可重复登记，不同内容的既有文件拒绝覆盖。目录内越界链接拒绝登记；失败撤回本次新增字体。已编码下载路径保持原有转义语义，不把 `%20` 再编码为 `%2520`。

上述检查只证明本地资源和字形覆盖，不能替代目标环境可用性验证，也不要求生成独立契约；记录方式遵循第 6 节，字体推荐与生产流程不变。

## 7. 回退规则

- 用户指定的字体加载失败时，先尝试恢复；仍失败则使用可加载的回退字体，检查排版，并在交付时说明目标字体未生效及实际使用的字体。
- 模型自选的字体不可用时，可自行更换为合适、可加载的字体，检查实际字体与排版后交付。标题保留语种、角色、关键形态与气质；正文保留语种和阅读职责。
- 许可核验失败或用户另外锁定的关键字形无法满足时，先确认授权／替代方案。
- 多语种必须按真实文案逐项检查，不通过中文或英文结果推断其他语种；
- 交付前核验实际字体、完整字形与排版；可编辑文字保持原生，pure-image 图内文字按原路线检查。

## 8. 维护

新增或修改字体时：

1. 更新对应 catalog 元数据；
2. 若 CDN 已真实部署，向 manifest 添加经过 HEAD、文件头、大小和 MD5 验证的明确条目；
3. 在精选 JSON 更新主题、语种、角色与排序；已有候选保留其来源，未解析名称显式待核验，不根据名字编造字体事实；
4. 平台清单有真实变更时同步 `fonts.md` 与 JSON 查询镜像，保留精确 family 和各 style 的字重集合；
5. 运行 `scripts/test/test_font_union.py`、CSS 查询和引用检查，核对组合 ID、旧候选保留、语言过滤、排除回退与平台表一致性；
6. 真实下载、字体加载、缺字与目标尺寸的视觉适配在生产环境单独验证，静态测试不代替渲染。


本地解析器的 `package_status=local_present` 仅表示本地资源存在；`invalid` 表示字体解析或结构核验失败，`blocked_by_license` 表示许可阻断。`contract_ready=true` 只代表本地许可、family 和字形覆盖检查通过，不证明目标环境加载成功，也不表示必须创建 `font-contract.json`；`target_environment_status=not_checked` 时仍须完成上述环境门禁。登记包内全部字体与预期路径合并核验，下载遇到不同内容的已有文件或晚到冲突会保留原文件并报错。
