# 底图与覆盖物主题

底图仅允许 `themes/amap-styles.json` 的项目自定义浅色与深色样式。不得输出任意 Style URL、官方样式或未知 key。

## 主题来源

优先级：用户明确指定 > 宿主提供 > 浏览器系统主题 > 默认浅色。
模型不得根据海洋、夜景、科技等题材自行决定明暗，也不得把自己的偏好标记为用户要求。

- 用户明确指定时，填写 `stylePreference: { tone: "dark", selectedBy: "user" }`（或 light）。指定底图样式同样记录 user；strict 样式与明暗矛盾时报错。
- 未明确指定时，不填写 tone 与 preferredStyleIds；编译为 auto。已有 model/policy 明暗偏好不覆盖自动跟随。
- 宿主可在启动前设置 `window.mapCreateHostTheme` 为 light/dark；启动后调用 `window.mapCreateSetHostTheme(tone)`，null 表示恢复系统跟随。只接受直接宿主 API，不监听任意跨域消息。
- 未接到宿主主题时使用 `prefers-color-scheme`；这不等同于已经读取豆包应用主题，不能作此承诺。

## 编译与运行边界

编译器为 auto 生成成对的、经对比度校验的主题展示数据：底图、标准 shell、覆盖物样式、Token 与侧栏样式。Runtime 仅切换已编译数据，不生成任意配色；明暗切换保留相机、当前方案、筛选、面板状态与选中对象，不重新全览。用户指定的区域、路线颜色保持原样。

组件 Catalog `shellThemes` 是 UI 颜色唯一来源。浅色为白色侧栏/浮层、近黑主文字、灰色次文字；深色为深色表面、白色主文字、灰色次文字。不得从底图色相派生侧栏与说明文字颜色。路线/分组色只用于色条、标识和小面积选中反馈。`shellPreference` 不再改变这些标准颜色；旧 harmony:basemap 声明不再产生色相派生效果。

显式 Overlay Palette 不适用于当前明暗时，使用对应明暗的兼容 Palette 并记录诊断；业务显式色值不被改写。非法候选底图仍失败，不因 auto 而忽略非法输入。

## 验收

检查用户覆盖、宿主覆盖、系统切换、无信号默认浅色，以及地图和 UI 同步变化。对比度诊断不代表瓦片已加载，也不代表审美验收通过。底图避让由组件高德适配层使用最终点组件占位请求，不能通过关闭所有文字替代，更不能承诺所有底图文字都可避让。

维护者可运行 `tools/calibrate-amap-styles.mjs --out build/style-evidence` 做北京、杭州和跨城截图校准；检查实际截图后更新 profile，不把假设色值写成测量结果。
