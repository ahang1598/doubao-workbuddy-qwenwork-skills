# 工程接口

plan.json 和 frames.json 内的路径相对各自文件解析；任务工程位于 Skill 外的工作目录。计划字段见 [规划](planning.md#4-写计划)。

## plan.json

远程原片在理解与初步规划阶段可使用云端探测结果。运行本地工程脚本前，先检查宿主提供的素材路径或素材清单，复用同一原片的可用本地文件，将 `video` 设为该路径；仅无可用本地副本时才下载，不因输入同时包含 URL 而重复下载。脚本继续使用 FFprobe 读取本地原片；云端信息与本地信息存在差异时，先核对素材及画幅、时间基准，再校准计划和工程。

规划数据保存在 `plan.json` 和 `frames.json` 中；不另写执行配置。以下为 20 秒、1920×1080 中文产品测评片段的结构示例，时长、观察与坐标需按实际输入填写：

```json
{
  "schemaVersion":2,
  "video":"../video.mp4",
  "subtitles":"transcript.srt",
  "style":{
    "fontFamily":"PingFang SC","minFontSize":44,
    "groups":{"emphasis":{"purpose":"强调轻便卖点"}},
    "referenceReason":"暖色产品测评","palette":"米白与暖黄",
    "motion":"20秒产品测评；目标3–7次/分钟、1–2条、覆盖20%–45%；实际1条、3次/分钟、覆盖25%；标题轻快进入，稳定阅读，操作演示留白。","layoutLanguage":"利用主体旁留白"
  },
  "nodes":[{"id":"intro","startMs":2000,"endMs":7000,"priority":"key","summary":"产品登场","evidence":"字幕3–5"}],
  "effects":[{
    "id":"headline","nodeId":"intro","mode":"custom","group":"emphasis",
    "startMs":2000,"durationMs":5000,
    "reason":"用“轻装出发”短标题强调轻便卖点",
    "visualObservation":"示例：产品在右侧，刺绣细节位于右上方，左下留白，无原字幕",
    "views":["s1"],"layoutRect":[100,700,650,180],"motionBounds":[80,680,690,220],
    "protectedRegions":[{"frameId":"s1:1","kind":"product-detail","rect":[1100,300,200,160]}],
    "hold":[400,4200]
  }]
}
```

源图索引格式见 [帧索引交接](input-understanding.md#4-帧索引交接)。执行数据以 plan.json 为准；测量试调参数最终回填同一计划。

| 字段 | 要求 / 可省略的默认值 |
| --- | --- |
| schemaVersion | 2 |
| video | 本地视频路径；优先复用宿主提供的同一素材，仅无可用本地副本时下载 |
| subtitles | 可选工作字幕；无语音可省略 |
| frames | 默认 `frames.json`，相对计划文件 |
| fps | 默认30，1–60整数；durationMs 对齐整数帧 |
| nodes、style、effects | 候选节点、全片风格、动效列表；规划要求见 planning.md |
| effects[].id | 小写字母开头，后接小写字母/数字/连字符，最多64字符，唯一 |
| startMs、durationMs | startMs 是在原片中的开始时间，durationMs 是持续时长，单位均为毫秒；时长1000–600000，结束不越过原片 |
| layer | 默认0，整数，越大越靠上；同层按开始时间、id 排序 |
| group / style.groups | 单条引用表现组；组内简记用途，样式与动作在共用代码中实现 |
| mode | 默认 `custom`，自行编写动效 |
| project | 默认 `effects/<id>`，任务目录内唯一工程目录，不放在 Skill 内 |
| canvasMode | 默认 `auto`，按完整 motionBounds 局部渲染；`full` 强制整帧，适合依赖 viewport 或无法可靠确定范围的动效 |
| canvasPadding | 默认32像素，0–1024；在完整运动范围外额外留白，不替代阴影/过冲范围规划 |
| source | 仅 custom 可选，指向完整本地工程；未提供时生成骨架 |
| style.referenceReason、style.palette、style.motion、style.layoutLanguage | 非空字符串；配色与动作写简短描述，不填对象 |
| style.fontFamily、style.accentColor | 分别为本机字体名和强调色；强调色默认 #F6C453，使用 #RRGGBB 格式 |

文字、时间、画幅、fps 或布局变化后同步任务 HTML/CSS/GSAP；prepare 保留已有工程内容并补齐缺失的 GSAP 资源与 package.json；新工程准备完整后才写入目标目录。定点修改对应工程，流程见 [动效编写](motion-authoring.md)。

## 实现时回填的执行字段

`layoutRect` 依据稳定阅读状态测量填写；`motionBounds` 由代码的全程运动和装饰范围确定；`hold` 依据时间线填写。最终范围须通过保护区校验。

| 单条字段 | 要求 |
| --- | --- |
| id、nodeId、mode、startMs、durationMs | 关联节点；超出节点时段写 timingReason |
| reason、visualObservation | 简记表达目的与选型理由、实际看图观察 |
| views | 已看图 id 或格子引用，如 `["s1"]` 或 `["s1:2"]`；至少一帧 |
| layoutRect | 稳定展示外接矩形，含引线和装饰 |
| motionBounds | 全程活动范围，包含 layoutRect、进退场及过冲峰值、旋转和阴影余量；用于防遮挡及 render 局部副本范围计算，原工程不据此裁剪 |
| protectedRegions | `[{frameId:"s1:1",kind:"face",rect:[x,y,w,h]}]`；引用已看格子；空数组时在观察中说明 |
| safeMargin | 默认20，>=0；用于活动范围与保护区的间距检查；同期动效另检查活动范围不重叠 |
| hold | `[稳定阅读起点,阅读时长]`，相对动效起点的毫秒；时长>=500 且 <=durationMs−200，两者之和<=durationMs |

所有矩形用 `[x,y,width,height]`，单位为原片像素；`hold` 从文字全部显示且数字计数完成后的稳定阅读时刻开始；无计数动画时只需文字显示完整。


## HyperFrames HTML 契约

- `index.html` 为完整 HTML，根直接位于 body，不包 template。
- 根属性：`data-composition-id` 等于 effect id，`data-start="0"`、`data-duration`（秒）、`data-width`、`data-height`、`data-fps`；CSS 尺寸同步。
- 至少一个有稳定 id 的 `.clip`，声明 start、duration、track-index。
- 使用本地 `vendor/gsap.min.js`；同步注册暂停时间线到 `window.__timelines[effectId]`。
- 用 `shellHTML(e,c,body,css,timeline)` 生成原片尺寸透明工程，定位层和内容坐标见 [坐标与定位](motion-authoring.md#坐标与定位)。
- html/body/root 透明，不加音频；资源放工程内，不用网络资源或符号链接。
- 局部渲染仅改临时副本，回退条件见 [渲染与合成](verification.md#2-渲染与合成)。
- 移除 `AUTHOR_CUSTOM_EFFECT` 后再渲染。

## 动画编写

根据计划中的表达内容与全片风格，自行设计并编写；HTML 结构遵循上方契约。

### 布局与时间线

- 字号、排版与选位按 [大小与视觉分量](motion-authoring.md#大小与视觉分量) 和 [排版与测量](motion-authoring.md#排版与测量) 执行。
- 进场 → 展开 → 稳定阅读 → 退场；阅读期不持续晃动，数字计数或逐项揭示等动画完成后，再开始计算稳定阅读时间。
- 静态倾斜放外层，GSAP 位移/缩放放内层；不要同时用 CSS 和 GSAP 改写同一变换。
- 活动范围包含旋转四角、运动峰值、引线、装饰及阴影；范围调整按 [编写与测量流程](motion-authoring.md#编写与测量流程) 汇总到计划，并与最终工程保持一致。

### 确定性与透明度

- 使用可直接 seek 的暂停 GSAP 时间线；不依赖计时器、Date.now、未固定随机数或播放历史。
- 优先 x/y/scale/rotation/opacity；用 fromTo 明确起止，后续同属性 fromTo 注意 immediateRender。
- 数字可 tween innerText 并 snap 到整数，不只依靠 onUpdate 生成关键内容。
- 最后一个输出采样帧前完成退场。
- 用户文字转义 HTML。长文案换行、重排或拆分，不裁字、不无限缩小。
- 声明本地 font-face；内容本身须在计划范围内。

完成后按 [执行与交付](verification.md) 渲染合成。

## 过程文件

- `.measure-service/`：常驻测量服务的连接和进程信息，服务正常停止时移除；不要分发其中的连接凭据。
- `measurements/`：每次测量的独立结果，含工程摘要与提交布局；主 Agent 汇总时仅采用与当前工程和计划一致的结果。
- `diagnostics.json`：仅运行可选 preview 时生成的问题定位结果，渲染不依赖此文件。
- `artifacts.json`：render 生成的素材清单，须 `complete:true`；每条的 `width/height` 为素材尺寸，`x/y` 为原片中的叠加位置，`canvasMode/canvasVersion` 标识画布方式与缓存版本。compose 校验尺寸、坐标、摘要、时序与源片；旧清单缺少 x/y 时只接受原片尺寸并叠加在 (0,0)。禁止手改摘要绕过校验。
- `export-state.json`：合成完成记录，随工作目录保留。

## 最终成片压缩

保持原片分辨率、帧率和支持的像素格式，完整导出复制音轨。以相对原片无明显可见画质下降为优先，体积尽量接近原片；不把原片平均码率设为重编码目标或峰值上限。

合成脚本自动探测帧率同步参数：支持时使用 `-fps_mode cfr`，旧版使用 `-vsync 1`；无需手动改命令。

统一输出 H.264 MP4。默认 CRF 20、slow 预设，可用 `compose --crf <值> --preset slow|slower|veryslow` 调整。

有明确体积要求或原片码率很低时，先用含运动、暗部细节和动效的代表片段选择参数；优先保留画质，允许合理增大体积。
