# Mobile Component Map

> **文件用途**：定义 SparkFlow Mobile Skill 中可使用的组件清单，说明各组件的适用场景和使用规范。
> 覆盖两条路径：**H5（Ant Design Mobile v5）** 和 **React Native（Expo + NativeWind + Gluestack UI v2）**。
> SKILL.md 在 Q_tech 选择后读取本文件，确保组件选用有规范依据。

---

## 一、组件使用原则

1. **库组件优先**。H5 路径优先用 antd-mobile；RN 路径优先用 Gluestack UI + NativeWind，仅在库无等价物时自行实现。
2. **语义优先**。按交互语义选组件，而非视觉相似。确认框用 Dialog（H5）/ Alert（RN），多操作菜单用 ActionSheet，表单用 Form，不混用。
3. **安全区必须处理**。H5 顶部用 `NavBar`，底部用 `<SafeArea position="bottom" />`；RN 用 `SafeAreaView` 包裹根视图。
4. **触控区域 44px/pt 最小**。所有可点击元素保证最小触控区域。
5. **主题色通过 token 访问**。H5 用 `var(--adm-color-primary)`；RN 用 Gluestack token 或 Tailwind 色板，不硬编码颜色。

---

## 二、H5 路径 — Ant Design Mobile v5

### 安装

```bash
npm create vite@latest [project-name] -- --template react-ts
cd [project-name] && npm install --legacy-peer-deps
npm install antd-mobile antd-mobile-icons tslib react-router-dom --legacy-peer-deps
```

> **注**：`--legacy-peer-deps` 仅在从 `npm create vite@latest` 新建项目时必须，因为 Vite 模板默认生成 React 19，而 antd-mobile v5 尚未声明 React 19 peer dep 支持。已有 React 17/18 项目直接按官方指南 `npm install --save antd-mobile` 即可。

### 2.1 布局与导航

| 组件 | 用途 | 使用规范 |
|---|---|---|
| `NavBar` | 顶部导航栏（返回键 + 标题 + 右侧操作）| `back` prop 为 null 时不显示返回；`right` 放图标按钮 |
| `TabBar` | 底部 Tab 导航（4-5 项）| 配合 `react-router-dom` 路由切换；`Badge` 显示未读数 |
| `SafeArea` | 安全区处理（刘海屏/底部手势条）| `position="top"` 或 `"bottom"`，必须在顶层使用 |
| `SideBar` | 左侧分类栏（商品目录场景）| 竖向分类列表，配合右侧内容区 |
| `Tabs` | 页内 Tab 切换（Feed / 关注切换）| `defaultActiveKey` 控制初始选中 |

### 2.2 列表与数据展示

| 组件 | 用途 | 使用规范 |
|---|---|---|
| `List` | 标准列表容器 | `List.Item` 支持左侧图标、右侧内容、箭头 |
| `SwipeAction` | 列表行左右滑动操作 | `rightActions`（删除）/ `leftActions`（收藏）|
| `PullToRefresh` | 下拉刷新 | 包裹在 `ScrollView` 或页面最外层 |
| `InfiniteScroll` | 无限滚动加载 | `loadMore` prop 传异步函数 |
| `Grid` | 商品 / 图片网格 | `columns={2}` 适合商品列表 |
| `Card` | 内容卡片（Feed / 商品）| 可嵌套 `Image`、`Tag`、`Button` |
| `Badge` | 角标（未读数 / 状态标记）| `<Badge content={N}>{children}</Badge>` 包裹子元素显示角标 |
| `Tag` | 标签（分类 Chip / 状态 Badge）| `color` 控制颜色，`fill="outline"` 边框样式 |
| `Image` | 图片（支持懒加载 + placeholder）| `lazy` 开启懒加载；`fallback` 设置错误态 |
| `ImageViewer` | 全屏图片查看器 | `ImageViewer.show({ images })` 命令式调用 |
| `Swiper` | 横向滑动轮播（图片 Carousel）| `indicator` 显示分页点；`loop` 循环播放 |
| `FloatingBubble` | 浮动气泡按钮（主操作 FAB）| `axis="xy"` 可拖动 |
| `FloatingPanel` | 可拖拽底部面板（地图场景）| `anchors` 设置多个停靠高度 |

### 2.3 表单与输入

| 组件 | 用途 | 使用规范 |
|---|---|---|
| `Form` | 表单容器（自动处理布局和校验）| `Form.Item` + `name` + `rules` |
| `Input` | 单行文本输入 | `clearable` 一键清除；`type="number"` 数字键盘 |
| `TextArea` | 多行文本输入（帖子内容、备注）| `rows` 控制初始行数；`maxLength` 限制字数 |
| `SearchBar` | 搜索框 | `placeholder` + `onSearch` + `onClear` |
| `Picker` | 级联选择（城市 / 日期 / 分类）| `columns` 传数据；`onConfirm` 回调 |
| `DatePicker` | 日期时间选择 | `precision="day"/"minute"` 控制精度 |
| `Slider` | 范围选择（价格筛选）| `range` 开启双滑块 |
| `Stepper` | 数量增减（购物车）| `min` / `max` / `step` |
| `Switch` | 开关（通知 / 功能开关）| 即时生效，无需提交按钮 |
| `CheckList` | 复选列表（筛选多选）| `multiple` 开启多选 |
| `Radio.Group` | 单选组（排序 / 支付方式）| `defaultValue` 设默认值 |
| `Rate` | 星级评分 | `readOnly` 展示态 |

### 2.4 覆盖层与反馈

| 组件 | 用途 | 使用规范 |
|---|---|---|
| `Popup` | 底部 / 顶部弹出面板（Sheet）| `position="bottom"` 标准 Bottom Sheet |
| `CenterPopup` | 居中弹窗（轻量内容展示）| 不用于表单，改用 `Dialog` |
| `Dialog` | 系统级确认弹窗（≤2 个操作）| `Dialog.confirm({ title, content, onConfirm })` |
| `ActionSheet` | 多操作选择菜单（≥3 个操作）| `ActionSheet.show({ actions })` 命令式 |
| `Toast` | 非阻断式操作反馈 | `Toast.show({ content, icon: 'success' })` |
| `Modal` | 全屏模态页（Onboarding / 内容详情）| `fullscreen` prop |
| `Loading` | 全屏加载遮罩 | antd-mobile v5 无 `Loading.show()` 命令式 API；正确方式：`Toast.show({ content: '加载中', icon: 'loading' })` 或 `<Mask visible={loading}><SpinLoading color="white" /></Mask>` |
| `SpinLoading` | 局部 Loading 指示器 | `color="primary"` |
| `DotLoading` | 流式输出的省略号加载动画 | AI 消息等待场景 |
| `ProgressBar` | 线形进度条（课程 / 上传）| `percent` 0-100 |
| `ProgressCircle` | 圆形进度（训练完成度）| `percent` + `children` 中间文字 |

### 2.5 操作与控制

| 组件 | 用途 | 使用规范 |
|---|---|---|
| `Button` | 所有可点击操作 | `color="primary"` 主要；`color="default"` 次要；`fill="none"` 幽灵；`color="danger"` 危险 |
| `Empty` | 空状态（搜索无结果 / 列表为空）| `image` 自定义图片；必须包含 CTA 按钮 |
| `ErrorBlock` | 错误状态（网络错误 / 404）| `status="default"/"busy"/"disconnected"` |
| `Steps` | 步骤条（Checkout Wizard / Onboarding）| `current` 控制当前步骤 |
| `Collapse` | 折叠展开（FAQ / 商品描述）| `accordion` 手风琴模式 |
| `Ellipsis` | 文字截断展开（多行内容）| `rows` 控制行数；`expandText` 展开按钮文字 |
| `Avatar` | 用户头像 | `src` + `fallback` 备用文字头像 |
| `Result` | 操作结果页（成功 / 失败）| `status="success"/"error"/"waiting"` |
| `PageIndicator` | 分页点（Swiper / Onboarding）| `total` + `current` |

---

## 三、RN 路径 — Expo + NativeWind + Gluestack UI v2

### 安装

```bash
npx create-expo-app [project-name] --template blank-typescript
cd [project-name]
npx expo install nativewind@^4 tailwindcss react-native-safe-area-context react-native-reanimated
npx gluestack-ui@latest init
npx gluestack-ui add button text box vstack hstack input badge spinner pressable
npx expo install expo-router
npm install lucide-react-native
```

> **Gluestack UI v2 说明**：v2 使用本地组件文件模式，`npx gluestack-ui add` 会在 `components/ui/[component]/index.tsx` 下生成组件。
> import 路径为 `@/components/ui/[component]`，**不再使用 `@gluestack-ui/themed`**。
> 如需新增未列出的组件，运行 `npx gluestack-ui add [component-name]`。

### 3.1 布局与导航

| 组件 | 用途 | 使用规范 |
|---|---|---|
| `Box` | 基础容器（替代 View）| NativeWind 类名控制样式 |
| `VStack` / `HStack` | 垂直 / 水平布局容器 | `space` prop 或 `gap-*` 类名 |
| `SafeAreaView`（RN 内置）| 安全区包裹 | 必须在每屏根组件使用 |
| `ScrollView`（RN 内置）| 页面滚动容器 | 内容不定高时使用 |
| `FlatList`（RN 内置）| 高性能长列表 | `keyExtractor` + `renderItem`；空状态用 `ListEmptyComponent` |
| `SectionList`（RN 内置）| 分组列表（外卖菜单 / 设置页）| `sections` 传分组数据 |
| Expo Router `Tabs` | 底部 Tab 导航 | `_layout.tsx` 中配置 `tabBarIcon` |
| Expo Router `Stack` | 页面堆叠导航 | `push` 前进；`back` / `dismiss` 返回 |

### 3.2 数据展示

| 组件 | 用途 | 使用规范 |
|---|---|---|
| `Text` | 文本展示 | NativeWind 类名控制字体大小/粗细/颜色 |
| `Image`（expo-image）| 网络图片（高性能缓存）| `contentFit="cover"` 适配容器 |
| `Badge` / `BadgeText` | 角标 / 状态标签 | `action="success"/"error"/"warning"` |
| `Avatar` / `AvatarImage` | 用户头像 | `AvatarFallbackText` 备用文字 |
| `Progress` | 进度条 | `value` 0-100 |
| `Spinner` | 加载指示器 | `size="large"/"small"` |
| `Divider` | 分割线 | 水平 / 垂直方向 |

### 3.3 表单与输入

| 组件 | 用途 | 使用规范 |
|---|---|---|
| `FormControl` | 表单字段容器（含 Label + Error）| 包裹 Input、Select 等 |
| `Input` / `InputField` | 单行文本输入 | `keyboardType` 控制键盘类型 |
| `Textarea` | 多行文本输入 | `numberOfLines` 控制行数 |
| `Button` / `ButtonText` | 操作按钮 | `variant="solid"/"outline"/"link"` |
| `Pressable` | 可点击容器（自定义样式按钮）| `onPress` + 子组件 |
| `Switch`（RN 内置）| 开关 | `value` + `onValueChange` |
| `Slider`（@miblanchard/react-native-slider）| 范围选择 | `minimumValue` / `maximumValue` |
| `Modal`（RN 内置）| 全屏 / 透明背景弹层 | `animationType="slide"/"fade"` |
| Bottom Sheet（@gorhom/bottom-sheet）| 底部弹层（规格选择 / 筛选）| `snapPoints` 控制高度 |

### 3.4 覆盖层与反馈

| 组件 | 用途 | 使用规范 |
|---|---|---|
| `AlertDialog` | 系统级确认弹窗 | `AlertDialogHeader` + `AlertDialogBody` + `AlertDialogFooter` |
| `Toast` / `useToast` | 非阻断式消息提示 | `toast.show({ title, description, action: "success" })` |
| `Actionsheet` | 多操作选择菜单 | `ActionsheetItem` 列出各操作 |
| `Popover` | 锚点式气泡提示 | `PopoverTrigger` + `PopoverContent` |

### 3.5 图标

```tsx
// 使用 lucide-react-native（推荐）
import { ShoppingCart, Heart, Search, ArrowLeft } from 'lucide-react-native'

// 或 @expo/vector-icons
import { Ionicons, MaterialIcons } from '@expo/vector-icons'
```

---

## 四、容器模式对照表（iOS → Mobile）

> 帮助从 iOS scenario 文件理解容器模式在两个路径中的对应实现：

| iOS 容器 | H5（antd-mobile）| React Native（Gluestack / RN）|
|---|---|---|
| `.sheet()` 底部弹层 | `Popup position="bottom"` | `@gorhom/bottom-sheet` |
| `.sheet(.medium)` 半屏弹层 | `Popup` + `style={{ height: '50vh' }}` | `BottomSheet snapPoints={['50%']}` |
| `.fullScreenCover()` 全屏 | `Modal fullscreen` 或路由跳转 | `Stack` push（全屏页面）|
| `.alert()` 确认弹窗 | `Dialog.confirm()` | `AlertDialog` |
| `.confirmationDialog()` 多操作 | `ActionSheet.show()` | `Actionsheet` |
| `TabView` 主导航 | `TabBar` + `react-router-dom` | Expo Router `Tabs` |
| `NavigationStack` | `useNavigate` / Link | Expo Router `Stack` |
| `LazyVStack` 长列表 | `List` + `InfiniteScroll` | `FlatList` |
| `LazyVGrid` 商品网格 | `Grid columns={2}` | `FlatList numColumns={2}` |
| `.refreshable()` 下拉刷新 | `PullToRefresh` | `FlatList` + `RefreshControl` |
| `.swipeActions()` 滑动操作 | `SwipeAction` | `react-native-swipeable` 或自实现 |
| `ContentUnavailableView` 空状态 | `Empty` | 自定义 Empty 组件（含 CTA）|
| `ProgressView` 加载 | `SpinLoading` / `DotLoading` | `Spinner` |
| `TabView(.page)` 图片轮播 | `Swiper` | `FlatList` horizontal + `PagerView` |

---

## 五、场景 × 核心组件矩阵

| 移动场景 | H5 必用组件 | RN 必用组件 |
|---|---|---|
| 消费者社交 | `List`, `PullToRefresh`, `Image`, `ActionSheet`, `Popup` | `FlatList`, `RefreshControl`, `expo-image`, `Actionsheet` |
| 健康 & 运动 | `ProgressCircle`, `Steps`, `Card`, `Result` | `Progress`, `FlatList`, `Pressable` |
| AI 助手 | `List`, `Input`, `DotLoading`, `FloatingBubble` | `FlatList`, `Input`, `Spinner`, `KeyboardAvoidingView` |
| 消费者金融 | `List`, `Dialog`, `Steps`, `Result`, `Toast` | `FlatList`, `AlertDialog`, `Toast` |
| 电商本地生活 | `Grid`, `Swiper`, `Popup`, `SwipeAction`, `Stepper`, `Toast` | `FlatList`, `BottomSheet`, `PagerView`, `Stepper` |
| 娱乐流媒体 | `Grid`, `Popup`, `Modal`, `ProgressBar` | `FlatList`, `Modal`, `BottomSheet` |
| 出行旅游 | `DatePicker`, `Picker`, `Steps`, `Card` | `DateTimePicker`, `FlatList`, `Modal` |
| 教育科技 | `Steps`, `ProgressBar`, `CheckList`, `Result` | `Progress`, `FlatList`, `AlertDialog` |
| 求职平台 | `SearchBar`, `List`, `Tag`, `Popup`, `Steps` | `FlatList`, `BottomSheet`, `Badge` |
| 新闻阅读 | `List`, `PullToRefresh`, `InfiniteScroll`, `Popup` | `FlatList`, `RefreshControl`, `Modal` |
| 设计编辑 | `Grid`, `ActionSheet`, `Modal`, `FloatingBubble` | `FlatList`, `Modal`, `Actionsheet`, `Pressable` |

---

## 六、H5 路径已知陷阱（antd-mobile v5 实测）

> 以下问题在 elle-shop 项目生成时实际踩坑，已验证。

| 组件 / 场景 | 陷阱 | 正确做法 |
|---|---|---|
| `Empty` | 不接受 `children` prop，TypeScript 直接报错 | CTA 按钮移到 `<Empty />` 外，用包装 div 并排放置 |
| `InfiniteScroll` | 内部依赖 `tslib`，生产构建（Rolldown）报 resolve 错误；开发模式不报 | 安装时额外执行 `npm install tslib`，已内置到 Phase A 安装命令 |
| `antd-mobile-icons` 图标名 | 与 PC 端 Ant Design Icons 命名不同，按语义猜名必错（如 `HomeOutline`、`ShoppingCartOutline` 均不存在） | 生成代码前用 `node -e "console.log(Object.keys(require('antd-mobile-icons')))"` 核查实际导出名；常用速查见下表 |
| Flex 容器内的移动端外壳 | App 根容器只设 `maxWidth` 不设 `width: 100%`，在 `display: flex` 父级中会收缩到内容宽度，导致各页宽度不一致 | 必须同时设置 `width: '100%'` + `maxWidth`，让容器撑满 flex 父级后再封顶 |
| `Badge.wrap` | antd-mobile v5 Badge 无 `.wrap()` 静态方法 | 改用 `<Badge content={N}>{children}</Badge>` 直接包裹子元素 |
| `Loading.show()` / `Loading.hide()` | antd-mobile v5 无此命令式 API，`Loading` 是声明式组件 | 命令式加载用 `Toast.show({ content: '加载中', icon: 'loading' })`；全屏遮罩用 `<Mask visible={loading}><SpinLoading color="white" /></Mask>` |

### 常用图标速查（antd-mobile-icons 实际导出名）

| 语义 | 实际导出名 |
| --- | --- |
| 首页 | `AppOutline` |
| 购物车 / 购物袋 | `ShopbagOutline` |
| 搜索 | `SearchOutline` |
| 收藏（空心） | `HeartOutline` |
| 收藏（实心） | `HeartFill` |
| 用户 | `UserOutline` |
| 筛选 | `FilterOutline` |
| 返回 | `LeftOutline` |
| 更多 | `MoreOutline` |

---

## 七、RN 路径已知陷阱（Expo + Gluestack UI 实测）

| 组件 / 场景 | 陷阱 | 正确做法 |
|---|---|---|
| `KeyboardAvoidingView` | 含 `Input`/`Textarea` 的屏幕未包裹，键盘弹出时遮挡输入框 | 用 `KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'}` 包裹整个 Screen |
| `FlatList` vs `ScrollView` | `ScrollView + map` 渲染长列表，内存不释放、滚动卡顿 | 超过 10 条数据必须用 `FlatList`；短固定列表（≤10 条）可用 `ScrollView` |
| Shadow 跨平台 | 仅设 `shadowColor/shadowOffset`，iOS 有效 Android 无效 | 必须同时设 `elevation`（Android）和 `shadow*` 系列（iOS） |
| NativeWind `className` 无效 | `babel.config.js` 未添加 `"nativewind/babel"` preset，className 被忽略 | 参照 SKILL.md Phase A.2 配置文件模板；安装后用 A.4 SetupCheck 验证 |
| `<Text>` 包裹字符串 | JSX 中字符串裸露在 View 里，RN 运行时报错（不同于 DOM） | 所有文字内容必须在 `<Text>` 内，不得裸露字符串 |
| `SafeAreaView` 重复嵌套 | 每个 Screen 都有 `SafeAreaView`，产生双重 padding | `SafeAreaView` 只在根 layout（`app/_layout.tsx`）使用，各 Screen 内改用 `useSafeAreaInsets()` |
| Tab 切换数据不刷新 | Tab 切换时 `useEffect` 不重新触发，数据停留在上次状态 | 用 `useFocusEffect(useCallback(() => { fetchData() }, []))` 替代 `useEffect` |
| Expo Router `push` 路径 | `router.push('/some-path')` 字符串无类型检查，拼写错误运行时才发现 | 使用对象形式 `router.push({ pathname: '/some-path', params: {} })` 获得类型提示 |
| Gluestack `Steps` 组件 | Gluestack UI v2 无 Steps 组件，凭记忆 import 会报错 | 用自定义 `HStack` + 连接线实现步骤条；在 DS Coverage Notes 中标注为 Missing |
| `expo-image` vs `Image` | RN 内置 `Image` 无缓存优化，网络图片闪烁 | 统一使用 `expo-image` 的 `Image`，`contentFit="cover"` 适配容器 |

---

## 八、禁止行为

**H5 路径**：
- 不硬编码颜色值（用 `var(--adm-color-*)` 或 Tailwind 色板）
- 不跳过 NavBar + SafeArea（会导致刘海屏内容被遮挡）
- 不用 `window.alert()` / `window.confirm()`（用 antd-mobile 的 `Dialog`）
- 不省略空状态 CTA（Empty 必须含操作按钮）
- 不在移动端用 hover 状态（touch 设备无 hover）

**RN 路径**：
- 不用 `StyleSheet.create` 替代 NativeWind（保持统一风格）
- 不用 `ScrollView + map` 渲染长列表（用 `FlatList`，避免性能问题）
- 不忽略键盘遮挡（含 `Input` / `Textarea` 的屏幕必须用 `KeyboardAvoidingView`）
- 不省略 `SafeAreaView`（会导致内容与系统 UI 重叠）
- 不硬编码颜色（用 Gluestack token 或 Tailwind 色板）
- 不省略 Loading 状态（异步操作必须有 `Spinner` 或 `SpinLoading`）
- 不省略 Empty State（`FlatList` 的 `ListEmptyComponent` 必须设置）
