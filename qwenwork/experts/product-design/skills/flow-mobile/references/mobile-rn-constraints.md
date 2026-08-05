# RN 路径约束（Expo + NativeWind v4 + Gluestack UI v2）

> 本文件由 SKILL.md Phase B（RN 路径）和 Phase C 引用。

---

## 技术约束

- 使用 Gluestack UI v2 本地组件（`@/components/ui/[component]`）+ NativeWind 类名，不引入其他 UI 库
- 颜色通过 Tailwind 色板访问，不硬编码
- 间距使用 Tailwind 间距系统（`p-4`, `gap-3` 等），不任意硬编码
- 图标使用 `lucide-react-native` 或 `@expo/vector-icons`，不引入其他图标库
- 触摸目标最小 44pt（Pressable / Button 使用 `className="min-h-11 min-w-11"`）
- 路由使用 Expo Router（`expo-router`）

---

## 每屏注释头格式

```tsx
/* ================================================
   FLOW: [Flow Name]
   SCREEN [N] of [Total]: [Screen Name]
   PLATFORM: React Native (Expo + NativeWind + Gluestack UI v2)
   ------------------------------------------------
   ENTRY:  [上一屏哪个操作跳转到这里]
   EXIT:   [本屏主 CTA → 下一屏名称 / 终态]
   BRANCH: [可选，分支跳转规则]
   ================================================ */
```

---

## 常用组件引用（Gluestack UI v2 本地组件路径）

```tsx
import { Button, ButtonText } from "@/components/ui/button"
import { Text } from "@/components/ui/text"
import { Box } from "@/components/ui/box"
import { VStack } from "@/components/ui/vstack"
import { HStack } from "@/components/ui/hstack"
import { Input, InputField } from "@/components/ui/input"
import { Badge, BadgeText } from "@/components/ui/badge"
import { Spinner } from "@/components/ui/spinner"
import { Pressable } from "@/components/ui/pressable"
import { SafeAreaView, FlatList, RefreshControl, Modal } from 'react-native'
import { useRouter } from 'expo-router'
```

> **注意**：如未通过 `npx gluestack-ui add [component]` 安装该组件，则 `components/ui/[component]/` 目录不存在，import 会报错。
> 每次新增组件类型前先运行：`npx gluestack-ui add [component-name]`

---

## 视觉质量规范

```tsx
// 1. 文字层级用 NativeWind opacity 类
<Text className="text-base text-gray-900">标题</Text>
<Text className="text-sm text-gray-900 opacity-80">正文</Text>
<Text className="text-xs text-gray-900 opacity-60">辅助说明</Text>

// 2. 价格 / 统计数字加 tabular-nums
<Text style={{ fontVariant: ['tabular-nums'], fontWeight: '600' }}>¥1,234.56</Text>

// 3. 阴影带颜色调（iOS shadowColor / Android elevation）
style={{
  shadowColor: '#1677ff',
  shadowOffset: { width: 0, height: 2 },
  shadowOpacity: 0.10,
  shadowRadius: 6,
  elevation: 3,
}}

// 4. 已知选项用 Pressable 列表行，不用 TextInput
// ❌ 错误
<Input><InputField placeholder="请输入职位" /></Input>
// ✅ 正确
{roles.map(r => (
  <Pressable key={r.value} onPress={() => setRole(r.value)}
             className="flex-row items-center justify-between p-4 border-b border-gray-100">
    <Text>{r.label}</Text>
    {role === r.value && <CheckIcon />}
  </Pressable>
))}
```

---

## Gluestack 缺失组件速查

以下 UI 模式 Gluestack UI v2 无内置组件，需自定义实现并在 DS Coverage Notes 中标注 Missing：

| UI 元素 | 替代方案 |
|---|---|
| 步骤条 / Stepper | 自定义 HStack + 条件渲染 |
| 底部弹层 | `@gorhom/bottom-sheet` BottomSheet |
| 滑动删除 | `react-native-gesture-handler` |
| 图表 | `victory-native` 或 `react-native-svg` |

---

## C.2-RN 验证流程（Phase C 完成后执行）

> A.4 若已做过 SetupCheck 验证，此处只需确认路由集成正确。

```text
执行顺序：
1. 清理 SetupCheck —— 删除 app/setup-check.tsx，恢复 app/index.tsx 为正式入口
2. npx expo start —— 确认 Metro bundler 正常启动，无 module resolution 报错
3. 用 Expo Go 扫码，检查以下三项：
   - TabBar 底部导航正常渲染（各 Tab 可切换）
   - 至少一个 flow 的 Screen 1 正常显示（非白屏）
   - SafeAreaView 正常处理刘海屏（内容不被遮挡）

常见报错排查：
  "Unable to resolve module" → 检查 import 路径大小写，RN 对路径大小写敏感
  NativeWind className 无效 → 检查 babel.config.js 是否包含 "nativewind/babel"
  白屏无报错 → 检查 app/_layout.tsx GluestackUIProvider 是否包裹 <Slot />
  Metro 启动报错 → 执行 npx expo start --clear 清除缓存后重试
  "Module not found @/components/ui/[x]" → 运行 npx gluestack-ui add [x]
```
