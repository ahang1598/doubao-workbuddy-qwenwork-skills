# Phase A — 项目初始化

> 本文件由 SKILL.md Phase A 引用。用户确认 Q_tech 技术路径后，按以下步骤执行项目初始化。

---

## A.1 询问项目名称与状态

用 `AskUserQuestion` 推荐 1 个名称：

```json
{
  "questions": [
    {
      "question": "项目命名为什么？",
      "header": "项目名",
      "options": [
        { "label": "[推荐名称，基于场景自动生成]", "description": "推荐，根据场景类型生成" },
        { "label": "已有项目，跳过初始化", "description": "在现有代码库中添加 flow 文件，直接进入 Phase B" }
      ]
    }
  ]
}
```

---

## A.2 执行安装（根据 Q_tech 路径）

### H5 路径

```bash
npm create vite@latest [name] -- --template react-ts
cd [name] && npm install --legacy-peer-deps
npm install antd-mobile antd-mobile-icons tslib react-router-dom --legacy-peer-deps
```

> **注意**：
> - `--legacy-peer-deps`：绕过 antd-mobile 与 React 19 的 peer dep 冲突，运行时暂无影响
> - `tslib`：antd-mobile `InfiniteScroll` 等组件内部依赖。Vite 8（Rolldown bundler）生产构建必须安装

### RN 路径（Expo + NativeWind v4 + Gluestack UI v2）

```bash
# 第一步：创建项目
npx create-expo-app [name] --template blank-typescript
cd [name]

# 第二步：安装 NativeWind v4 核心依赖
npx expo install nativewind@^4 tailwindcss react-native-safe-area-context react-native-reanimated

# 第三步：初始化 Gluestack UI v2（自动更新 _layout.tsx）
npx gluestack-ui@latest init

# 第四步：添加所需组件（会在 components/ui/ 下生成本地组件文件）
npx gluestack-ui add button text box vstack hstack input badge spinner pressable

# 第五步：安装路由 + 图标
npx expo install expo-router
npm install lucide-react-native
```

> **Gluestack UI v2 说明**：v2 改为本地组件文件模式。`npx gluestack-ui add` 会在 `components/ui/[component]/index.tsx` 下生成组件，
> import 路径统一为 `@/components/ui/[component]`，不再使用 `@gluestack-ui/themed`。

写入以下配置文件（`Write` 工具）：

**`tailwind.config.js`**：
```js
module.exports = {
  content: ["./app/**/*.{js,jsx,ts,tsx}", "./components/**/*.{js,jsx,ts,tsx}"],
  presets: [require("nativewind/preset")],
  theme: { extend: {} },
  plugins: [],
}
```

**`babel.config.js`**（替换原有内容）：
```js
module.exports = function (api) {
  api.cache(true)
  return {
    presets: [
      ["babel-preset-expo", { jsxImportSource: "nativewind" }],
      "nativewind/babel",
    ],
  }
}
```

**`metro.config.js`**：
```js
const { getDefaultConfig } = require("expo/metro-config")
const { withNativeWind } = require("nativewind/metro")
const config = getDefaultConfig(__dirname)
module.exports = withNativeWind(config, { input: "./global.css" })
```

**`global.css`**：
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

在 `app/_layout.tsx` 最顶部添加 `import "../global.css"`（`npx gluestack-ui init` 会自动注入 `GluestackUIProvider`，检查是否已写入，未写入则手动补充）：

```tsx
import "../global.css"
import { GluestackUIProvider } from "@/components/ui/gluestack-ui-provider"
import { Slot } from "expo-router"

export default function RootLayout() {
  return (
    <GluestackUIProvider mode="light">
      <Slot />
    </GluestackUIProvider>
  )
}
```

---

## A.3 生成共享文件

生成以下文件：
- **`src/flows/shared/types.ts`** — 跨 flow 共用类型定义
- **`src/flows/shared/mock-data.ts`** — 跨 flow 共用 mock 数据

**项目目录结构**：

```
src/
├── App.tsx
└── flows/
    ├── shared/
    │   ├── types.ts          ← Phase A 生成
    │   └── mock-data.ts      ← Phase A 生成
    ├── flow-1/               ← Phase B 生成
    ├── flow-2/               ← Phase B 生成
    └── [app-name]/           ← Phase C 生成（App Shell）
```

---

## A.4 RN 路径环境验证（仅 RN 路径 + 新建项目执行）

用 `Write` 工具在 `app/setup-check.tsx` 生成以下验证组件（使用 v2 import）：

```tsx
import { Button, ButtonText } from "@/components/ui/button"
import { Text } from "@/components/ui/text"
import { Box } from "@/components/ui/box"
import { VStack } from "@/components/ui/vstack"
import { SafeAreaView } from "react-native"

export default function SetupCheck() {
  return (
    <SafeAreaView className="flex-1">
      <Box className="flex-1 items-center justify-center bg-white p-8">
        <VStack className="items-center w-full" space="md">
          <Text className="text-2xl font-bold text-gray-900">环境验证</Text>
          <Box className="w-full rounded-xl bg-blue-50 p-4">
            <Text className="text-sm text-blue-700">
              ✅ NativeWind：若此框显示蓝色背景，NativeWind className 正常
            </Text>
          </Box>
          <Button className="w-full">
            <ButtonText>✅ Gluestack UI：若此按钮显示品牌色，组件正常</ButtonText>
          </Button>
          <Text className="text-xs text-gray-400">
            两项均正常后，回到对话发送「继续」
          </Text>
        </VStack>
      </Box>
    </SafeAreaView>
  )
}
```

然后临时修改 `app/index.tsx` 只渲染 `<SetupCheck />`，执行：

```bash
npx expo start
```

---

## Phase A 结束语

**RN 路径**：

```
✅ Phase A 完成：依赖已安装，配置文件已写入。
技术栈：React Native（Expo + NativeWind v4 + Gluestack UI v2）

⚠️ 环境验证：请用 Expo Go 扫描终端中的 QR 码，确认以下两项均正常：
  1. 「NativeWind」框显示蓝色背景（NativeWind className 生效）
  2. 「Gluestack UI」按钮显示品牌色（Gluestack 组件样式正常）

全部正常后发送「继续」，开始生成第一个 flow 文件。
如有异常请截图或描述问题，先修复环境再继续。

⚠️ 退出提醒：如需中途退出，请保留 app/setup-check.tsx 不删除，
下次从 Phase B 继续时，执行完首个 flow 后再删除 setup-check.tsx 并恢复 app/index.tsx。

常见问题：
- className 无效（白色背景）→ 检查 babel.config.js 是否包含 "nativewind/babel" preset
- 按钮样式异常 → 检查 app/_layout.tsx 是否用 GluestackUIProvider 包裹
- 启动报错 → 检查 metro.config.js 是否引入 withNativeWind
```

**H5 路径**：

```
✅ 依赖已安装，共享文件已生成。
接下来将依次生成 [N] 个 flow 文件：[flow 1 名称] → [flow 2 名称] → ...
发送「继续」开始生成第一个 flow。
```
