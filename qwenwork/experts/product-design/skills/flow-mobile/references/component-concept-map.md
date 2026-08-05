# Component Concept Map — Mobile

> **文件用途**：将 Scenario 文件中的抽象 UI 概念名称，映射到 H5 和 React Native 两条路径的具体组件名与子组件链。
> SKILL.md Phase B.1.5 输出「UI 元素→组件映射声明表」时，以本文件为权威查找来源，不得凭记忆猜测组件名。

---

## 使用方法

1. 在 Scenario 文件的 IA Template / Canonical Flows 中找到抽象 UI 描述（如「底部弹层」「下拉刷新」）
2. 查本表对应行，获得当前 Q_tech 路径的具体组件名
3. 填入 B.1.5 声明表的「使用的组件」列，并标注「备注」列中的约束

---

## 一、导航与布局

| UI 概念 | H5（antd-mobile） | React Native（Gluestack + Expo Router） |
|---|---|---|
| 顶部导航栏 | `NavBar`（`back` prop 控制返回键）| Expo Router `<Stack.Screen options={{ title, headerLeft }}>` |
| 底部 Tab 导航 | `TabBar` + `TabBar.Item`（`key` 必须匹配路由 path）| Expo Router `<Tabs>` + `<Tabs.Screen>` |
| Stack 页面跳转 | `useNavigate()` push / replace | `router.push()` / `router.replace()` |
| 安全区处理 | `<SafeArea position="top/bottom" />` | 根 layout 用 `SafeAreaView`；各 Screen 用 `useSafeAreaInsets()` |
| 全屏页面（模态）| 路由 push（新页面）或 `Modal fullscreen` | Expo Router `Stack` push（视觉全屏）|

---

## 二、覆盖层与弹层

| UI 概念 | H5（antd-mobile） | React Native（Gluestack + Expo Router） |
|---|---|---|
| 底部弹层（Bottom Sheet）| `Popup position="bottom"` | `@gorhom/bottom-sheet` `BottomSheetModal`（需额外安装）|
| 半屏弹层 | `Popup` + `style={{ height: '50vh' }}` | `BottomSheet snapPoints={['50%']}` |
| 系统确认弹窗（≤2 操作）| `Dialog.confirm({ title, content, onConfirm })` | `AlertDialog` + `AlertDialogHeader` + `AlertDialogFooter` |
| 多操作菜单（≥3 操作）| `ActionSheet.show({ actions })` | `Actionsheet` + `ActionsheetItem` |
| 非阻断消息提示 | `Toast.show({ content, icon: 'success' })` | `useToast()` + `toast.show({ title, action: 'success' })` |
| 全屏加载遮罩 | `Toast.show({ icon: 'loading' })` 或 `<Mask><SpinLoading /></Mask>` | `<Box className="absolute inset-0 items-center justify-center"><Spinner /></Box>` |
| 居中弹窗（轻内容）| `CenterPopup` | `Modal` + `animationType="fade"` |

---

## 三、列表与滚动

| UI 概念 | H5（antd-mobile） | React Native（Gluestack + Expo Router） |
|---|---|---|
| 标准列表行（可点击）| `List.Item`（支持左图标、右箭头）| `Pressable` + `HStack`（手动布局）|
| 下拉刷新 | `PullToRefresh` 包裹内容区 | `FlatList` + `RefreshControl`（`onRefresh` + `refreshing`）|
| 无限滚动加载 | `InfiniteScroll`（`loadMore` 传异步函数）| `FlatList` `onEndReached` + `onEndReachedThreshold={0.2}` |
| 左右滑动操作 | `SwipeAction`（`rightActions` 删除）| `react-native-swipeable`（第三方，需额外安装）|
| 商品 / 图片网格 | `Grid columns={2}` | `FlatList numColumns={2}` + `columnWrapperStyle` |
| 横向滑动轮播 | `Swiper`（`indicator` 分页点）| `react-native-pager-view` 或 horizontal `FlatList` + 手动分页点 |
| 分组列表 | `List` + 多个 `List.Header` | `SectionList`（`sections` 传分组数据）|
| 空状态 | `Empty`（不接受 children，CTA 用外层 div）| `FlatList ListEmptyComponent` 或自定义 `VStack` + `Button` |

---

## 四、表单与输入

| UI 概念 | H5（antd-mobile） | React Native（Gluestack + Expo Router） |
|---|---|---|
| 表单容器 | `Form` + `Form.Item`（`name` + `rules`）| `FormControl` + `FormControlLabel` + `FormControlError` |
| 单行文本输入 | `Input`（`clearable` / `type="number"`）| `Input` + `InputField`（`keyboardType` 控制键盘类型）|
| 多行文本输入 | `TextArea`（`rows` / `maxLength`）| `Textarea`（`numberOfLines`）|
| 搜索框 | `SearchBar`（`onSearch` / `onClear`）| `Input` + `InputField` + `SearchOutline`（lucide）图标 |
| 级联 / 单列选择 | `Picker`（`columns` + `onConfirm`）| 无原生等价物；用 `ActionSheet` 列表行模拟 |
| 日期时间选择 | `DatePicker`（`precision="day"/"minute"`）| `@react-native-community/datetimepicker`（第三方）|
| 数量增减 | `Stepper`（`min` / `max` / `step`）| 自定义 `HStack` + `Pressable` 按钮 + `Text`（Gluestack 无 Stepper）|
| 开关 | `Switch` | RN 内置 `Switch`（非 Gluestack，`value` + `onValueChange`）|
| 单选组 | `Radio.Group` + `Radio` | `Pressable` 列表行 + 选中态图标（Gluestack 无 RadioGroup）|
| 多选列表 | `CheckList`（`multiple`）| `Pressable` 列表行 + `Checkbox` + `CheckboxIndicator` |
| 已知选项选择器 | `Selector`（chip 样式多选）| 自定义 `Pressable` Chip 行（Gluestack 无 Selector）|
| 星级评分 | `Rate`（`readOnly` 展示态）| `lucide-react-native` Star 图标 + `Pressable` |

---

## 五、数据展示

| UI 概念 | H5（antd-mobile） | React Native（Gluestack + Expo Router） |
|---|---|---|
| 网络图片 | `Image`（`lazy` + `fallback`）| `expo-image` `Image`（`contentFit="cover"`，内置缓存）|
| 全屏图片查看 | `ImageViewer.show({ images })` | `react-native-image-viewing`（第三方）|
| 用户头像 | `Avatar`（`src` + `fallback`）| `Avatar` + `AvatarImage` + `AvatarFallbackText` |
| 角标 / 未读数 | `<Badge content={N}>{children}</Badge>` | `Badge` + `BadgeText`（`action="success/error/warning"`）|
| 状态标签 / Chip | `Tag`（`color` + `fill="outline"`）| `Badge` 或自定义 `Box` rounded + `Text` |
| 线形进度条 | `ProgressBar`（`percent` 0-100）| `Progress`（`value` 0-100）|
| 圆形进度 | `ProgressCircle`（`percent` + children 中间文字）| 自定义 SVG 圆环（Gluestack 无 ProgressCircle）|
| 步骤条 | `Steps`（`current` 控制当前步骤）| 自定义 `HStack` + 连接线（Gluestack 无 Steps，DS Coverage 标注 Missing）|
| 局部加载指示 | `SpinLoading`（`color="primary"`）| `Spinner`（`size="large/small"`）|
| 流式输出动画 | `DotLoading` | 自定义 3 点 animated dots（Gluestack 无等价物）|
| 折叠展开 | `Collapse` + `Collapse.Panel`（`accordion`）| `Pressable` header + `Animated.View` 高度动画 |
| 文字截断展开 | `Ellipsis`（`rows` + `expandText`）| `Text numberOfLines={N}` + `Pressable` 展开 |
| 操作结果页 | `Result`（`status="success/error/waiting"`）| 自定义 `VStack` centered（Gluestack 无 Result，DS Coverage 标注 Missing）|
| 分割线 | `Divider`（水平）| `Divider`（`orientation="horizontal/vertical"`）|

---

## 六、Gluestack UI 缺失组件速查

以下组件在 H5（antd-mobile）有，但 Gluestack UI v2 **没有**原生等价物，生成 RN 代码时须自行实现并在 DS Coverage Notes 标注 `Missing`：

| 缺失组件 | 替代方案 |
|---|---|
| `Steps`（步骤条）| `HStack` + 圆圈数字 + 连接线（自实现）|
| `Stepper`（数量增减）| `HStack` + `-` / `+` `Pressable` + `Text` 数字 |
| `Result`（结果页）| `VStack` centered + 图标 + `Text` + `Button` |
| `Rate`（星级评分）| `lucide-react-native` `Star` + `Pressable` 列表 |
| `DotLoading`（流式动画）| `Animated` 3 点透明度循环动画 |
| `Selector`（chip 多选）| `ScrollView horizontal` + `Pressable` chip 行 |
| `ProgressCircle`（圆形进度）| `react-native-svg` 圆弧（第三方）|
| `Picker`（级联选择）| `ActionSheet` 列表行 或 `@react-native-picker/picker`（第三方）|
