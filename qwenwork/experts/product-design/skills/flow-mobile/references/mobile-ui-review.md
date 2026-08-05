# Mobile UI Review — P1 / P2 / P3 规则

> 供 Phase D.3（质量检查）和 Review Mode 使用。
> 按 P1 → P2 → P3 顺序扫描，P1 必须修复后再进 P2。

---

## P1 — 必须修复（影响可用性）

### P1-1 SafeArea 缺失

**描述**：顶部或底部未使用 SafeArea，内容被状态栏 / Home Indicator 遮挡。

**H5 修复**：

```tsx
import { SafeArea } from 'antd-mobile'

// 顶部
<SafeArea position="top" />
// 底部操作区
<SafeArea position="bottom" />
```

**RN 修复**：

```tsx
import { SafeAreaView } from 'react-native-safe-area-context'

<SafeAreaView style={{ flex: 1 }}>
  {/* 页面内容 */}
</SafeAreaView>
```

---

### P1-2 触摸目标 < 44px

**描述**：按钮、图标、Tab item 的可点击区域小于 44×44px，触控失灵。

**H5 修复**：

```tsx
// Button 默认满足，图标点击区需包裹：
<div style={{ minWidth: 44, minHeight: 44, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
  <AppOutline />
</div>
```

**RN 修复**：

```tsx
<Pressable className="min-h-11 min-w-11 items-center justify-center">
  <Icon as={AppIcon} />
</Pressable>
```

---

### P1-3 颜色硬编码（非 CSS 变量 / Tailwind token）

**描述**：组件直接使用十六进制颜色，主题切换失效。

**H5 修复**：

```tsx
// ❌ 错误
color: '#1677ff'

// ✅ 正确
color: 'var(--adm-color-primary)'
```

**RN 修复**：

```tsx
// ❌ 错误
style={{ color: '#1677ff' }}

// ✅ 正确（Tailwind token 或 useToken）
className="text-primary-500"
```

---

### P1-4 H5 容器缺 `width: '100%'`

**描述**：flex item 只设 `maxWidth`，未设 `width: '100%'`，导致 Tab 页宽度随内容收缩，不同 Tab 宽度不一致。

**H5 修复**：

```tsx
// ✅ 正确
const mobileStyle = { width: '100%', maxWidth: 430, margin: '0 auto', minHeight: '100vh' }

// ❌ 错误
const mobileStyle = { maxWidth: 430, margin: '0 auto' }
```

---

### P1-5 antd-mobile 图标使用错误名称

**描述**：使用了 antd PC 端图标名（如 `HomeOutline`），antd-mobile-icons 无此导出，TS 编译报错。

**修复**：参照 B1 图标对照表，改用正确名称：

```text
AppOutline       ← 首页（❌ HomeOutline）
ShopbagOutline   ← 购物车（❌ ShoppingCartOutline）
SearchOutline    ← 搜索
UserOutline      ← 个人中心
AddOutline       ← 新增
```

验证：`node -e "console.log(Object.keys(require('antd-mobile-icons')))"`

---

### P1-6 主 CTA 在拇指盲区（屏幕顶部 1/3）

**描述**：核心操作按钮（提交、确认、购买）放置在屏幕顶部 1/3 区域，单手持机时拇指无法自然触达，造成操作障碍。拇指舒适区在屏幕底部 1/3。

**判断方式**：检查每个屏幕的主 CTA（`Button color="primary"` / `onPress` 的主要入口），如果 `position` 或布局使其出现在页面顶部，标记违反。

**H5 修复**：

```tsx
// ❌ 错误：主操作在顶部
<div style={{ position: 'fixed', top: 16, right: 16 }}>
  <Button color="primary">立即购买</Button>
</div>

// ✅ 正确：固定在底部拇指区
<div style={{ position: 'fixed', bottom: 0, left: 0, right: 0, padding: '12px 16px' }}>
  <SafeArea position="bottom" />
  <Button color="primary" block>立即购买</Button>
</div>
```

**RN 修复**：

```tsx
// ✅ 正确：VStack 底部区域，或 position: 'absolute' bottom
<Box position="absolute" bottom={0} left={0} right={0} p="$4">
  <Button onPress={handleSubmit}><ButtonText>立即购买</ButtonText></Button>
</Box>
```

---

## P2 — 建议修复（影响体验）

### P2-1 长列表未用虚拟化组件

**描述**：使用 `ScrollView + map` 渲染长列表，性能差，滚动卡顿。

**H5 修复**：使用 `InfiniteScroll` 分页加载，或限制初始渲染条数。

**RN 修复**：

```tsx
// ❌ 错误
<ScrollView>{items.map(...)}</ScrollView>

// ✅ 正确
<FlatList data={items} renderItem={...} keyExtractor={...} />
```

---

### P2-2 空状态无 CTA

**描述**：空状态只显示「暂无数据」，用户无路可走。

**H5 修复**：

```tsx
<div style={{ textAlign: 'center' }}>
  <Empty description="暂无数据" />
  <Button color="primary" onClick={() => navigate('/explore')}>去逛逛</Button>
</div>
```

**RN 修复**：在 Empty 占位下方并排 Button，引导用户继续操作。

---

### P2-3 表单无 loading / disabled 状态

**描述**：提交按钮未在请求中禁用，用户可多次点击，产生重复提交。

**H5 修复**：

```tsx
const [loading, setLoading] = useState(false)
<Button loading={loading} disabled={loading} onClick={handleSubmit}>提交</Button>
```

**RN 修复**：

```tsx
<Button isDisabled={loading} onPress={handleSubmit}>
  {loading ? <Spinner /> : <ButtonText>提交</ButtonText>}
</Button>
```

---

### P2-4 TabBar 当前 Tab 无高亮

**描述**：TabBar 未绑定当前路由，所有 Tab 视觉一致，用户无方向感。

**H5 修复**：

```tsx
const location = useLocation()
<TabBar activeKey={location.pathname} onChange={(key) => navigate(key)}>
  <TabBar.Item key="/home" icon={<AppOutline />} title="首页" />
</TabBar>
```

**RN 修复**：Expo Router `(tabs)` layout 自动高亮当前 Tab，确保 `tabBarActiveTintColor` 已配置。

---

### P2-5 字体层级混乱（字号 > 4 种 / 标签比数值更大）

**描述**：一屏中出现 5 种以上字号，或数据标签（"销售额"）字号大于对应数值（"¥591"），破坏视觉层级，用户扫描困难。

**判断方式**：统计屏幕中 `fontSize` / Tailwind 字号类的种类数；检查卡片/统计类组件中标签与数值的字号对比关系。

**H5 修复**：

```tsx
// ❌ 错误：标签比数值大
<div style={{ fontSize: 18 }}>销售额</div>
<div style={{ fontSize: 14 }}>¥591</div>

// ✅ 正确：数值突出，标签辅助
<div style={{ fontSize: 28, fontWeight: 600 }}>¥591</div>
<div style={{ fontSize: 12, opacity: 0.6 }}>销售额</div>
```

**规范**：全屏字号限制在 12 / 14 / 16 / 20 / 28 中取 ≤4 种；font-weight 限 regular(400) + semibold(600)。

---

### P2-6 间距随意硬编码（非 4pt 倍数）

**描述**：padding / margin / gap 使用 `7px`、`11px`、`15px` 等非 4pt 倍数值，导致不同屏幕间视觉节奏混乱。

**判断方式**：检查 `style` 对象中所有 `padding`、`margin`、`gap` 数值，是否均为 4 的倍数（4、8、12、16、24、32、48）。

**H5 修复**：

```tsx
// ❌ 错误
<div style={{ padding: '11px 15px', gap: 7 }}>

// ✅ 正确（8pt grid）
<div style={{ padding: '12px 16px', gap: 8 }}>
```

**倍增规则**：组内相邻元素间距 8px，跨组间距应为 2× → 16px，跨区块间距再 2× → 32px。

---

### P2-7 搜索页为空白态（无历史 / 热门 / 推荐）

**描述**：搜索框聚焦或搜索结果为空时，页面只显示空白或"无结果"，浪费曝光机会，用户无处可去。

**H5 修复**：

```tsx
// 搜索框聚焦时展示默认内容
{!searchValue && (
  <>
    <List header="最近搜索">
      {recentSearches.map(term => (
        <List.Item key={term} onClick={() => setSearchValue(term)}>{term}</List.Item>
      ))}
    </List>
    <List header="热门推荐">
      {hotItems.map(item => <List.Item key={item.id}>{item.name}</List.Item>)}
    </List>
  </>
)}
```

**RN 修复**：同理，在 `SearchBar` 无输入时渲染 `FlatList` 展示历史/热门，替代空白区域。

---

### P2-8 错误状态不可操作（无恢复路径 / 仅红色提示）

**描述**：接口报错或表单校验失败后，只显示红色 Toast 或文案，用户不知道下一步该做什么，容易放弃。

**判断方式**：检查所有 `catch` 块和 `onError` 回调，是否只有 `Toast.show` 而无后续引导；检查表单错误文案是否具体说明原因。

**H5 修复**：

```tsx
// ❌ 错误：仅提示
Toast.show({ content: '请求失败', icon: 'fail' })

// ✅ 正确：提示 + 操作路径
Dialog.confirm({
  content: '网络不稳定，请检查连接后重试',
  confirmText: '重试',
  onConfirm: () => handleSubmit(),
})

// 表单校验错误文案应具体
// ❌ "格式错误"
// ✅ "手机号需为 11 位数字，当前输入了 10 位"
```

**RN 修复**：同理，用 `AlertDialog` 替代单纯 `Toast`，提供重试 / 联系客服 / 返回等操作。

---

### P2-9 同类交互不一致（手势 / 位置 / 文案随屏幕变化）

**描述**：同一 App 内，相同语义的操作在不同屏使用了不同控件、位置或文案（如一处用"确认"另一处用"提交"，一处左滑删除另一处长按删除），增加用户认知负担。

**判断方式**：核对跨屏幕中以下是否统一：① 删除操作手势；② 返回/取消的位置（左上 or 底部按钮）；③ 确认类按钮文案；④ Loading 展示方式。

**H5 / RN 修复原则**：

```text
- 删除：统一用 SwipeAction（H5）/ 左滑（RN），不混用长按菜单
- 返回：统一用 NavBar onBack（H5）/ Stack.goBack（RN），不在底部另加返回按钮
- 确认文案：统一"确认" / "提交" / "完成"三选一，全 flow 保持一致
- Loading：统一用 Button loading 属性（H5）/ Button isDisabled + Spinner（RN）
```

---

## P3 — 建议清单（体验增强）

> 以下各项在 Phase D.3 输出时标注 ✅ 已满足 / ⬜ 未满足。

- [ ] **P3-1** 需要订阅 / 内购的 flow 有「恢复购买」入口
- [ ] **P3-2** Paywall 有关闭按钮（右上角 ×，不强制付费）
- [ ] **P3-3** 权限请求前有自定义说明页（位置 / 相机 / 通知，解释用途）
- [ ] **P3-4** 涉及资金操作有二次确认（Dialog / 生物识别）
- [ ] **P3-5** 图片加载有骨架屏或占位图（非空白区域）
- [ ] **P3-6** 网络错误有重试按钮（非仅 Toast 提示）
- [ ] **P3-7** 核心任务完成有「Peak」情感反馈（Result 页 / 动画 / 鼓励文案，不只是 Toast）
- [ ] **P3-8** Flow 终态有「End」设计（完成摘要 / 进度确认 / 回归引导，不能操作完直接落崖）
- [ ] **P3-9** 按用户阶段分级体验（新用户有引导步骤，回访用户有快捷入口）
- [ ] **P3-10** 符合场景行业视觉规范（金融→蓝色/保守；健康→暖色/友好；娱乐→活泼/高饱和）

---

### P2-10 数字 / 价格未使用等宽字体（tabular-nums 缺失）

**描述**：金额、统计数字使用比例字体，不同数字宽度不一致，数据更新时字符会跳动，影响可读性和专业感。

**判断方式**：检查渲染价格、计数、进度百分比的文本元素，是否有 `fontVariantNumeric: 'tabular-nums'`（H5）或 `fontVariant: ['tabular-nums']`（RN）。

**H5 修复**：

```tsx
// ❌ 错误：比例字体，数字位宽不一致
<span style={{ fontWeight: 600 }}>¥1,234.56</span>

// ✅ 正确
<span style={{ fontVariantNumeric: 'tabular-nums', fontWeight: 600 }}>¥1,234.56</span>
```

**RN 修复**：

```tsx
// ✅ 正确
<Text style={{ fontVariant: ['tabular-nums'], fontWeight: '600' }}>¥1,234.56</Text>
// 或 NativeWind（需 Tailwind 支持 font-variant-numeric）
<Text className="font-semibold tabular-nums">¥1,234.56</Text>
```

---

### P2-11 阴影使用纯黑（应为品牌色调阴影）

**描述**：卡片、浮层使用 `rgba(0,0,0,x)` 纯黑阴影，在有色背景上显得生硬、廉价；品牌色调阴影视觉更柔和、更有层次感。

**判断方式**：检查所有 `boxShadow` / `shadowColor` 属性，是否使用纯黑（`#000` / `rgba(0,0,0,...)`）。

**H5 修复**：

```tsx
// ❌ 错误：纯黑阴影
boxShadow: '0 2px 8px rgba(0,0,0,0.15)'

// ✅ 正确：带主色调的柔和阴影（蓝色系示例）
boxShadow: '0 2px 12px rgba(22,119,255,0.10)'
// 若背景为白色卡片，也可用中性浅灰调：
boxShadow: '0 2px 8px rgba(0,0,0,0.06)'  // 极低透明度可接受
```

**RN 修复**：

```tsx
// ❌ 错误
shadowColor: '#000'

// ✅ 正确：使用品牌色或极低透明度灰
shadowColor: '#1677ff',
shadowOffset: { width: 0, height: 2 },
shadowOpacity: 0.10,
shadowRadius: 6,
elevation: 3,
```
