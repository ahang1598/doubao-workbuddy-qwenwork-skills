---
name: ai-table-script-generator
displayName: AI 表格插件开发
name_en: ai-table-script-generator
description: |
  钉钉 AI 表格（多维表）插件开发专家，根据需求直接产出可运行的插件代码。 当用户提到“写 AI 表格脚本”“创建表格自动化脚本”“生成多维表代码”“做个边栏插件” “搭个表格插件界面”，或提到字段批量操作、记录增删改查、数据校验、按钮字段触发、 表格事件监听、选区联动等场景时使用。支持两种形态：脚本插件（TypeScript 自动化） 与边栏插件（React 双页架构）。
description_en: |
  Expert for building DingTalk AI Table (Notable) plugins. Use it when the user wants to write an AI Table automation script, generate multi-dimensional table code, or build a sidebar plugin UI: batch field operations, record CRUD, data validation, button-field triggers, table event listening and selection-driven interactions. Produces runnable production code for two plugin types: script plugins (TypeScript automation) and sidebar plugins (React dual-page architecture).
argument-hint: 要实现的表格能力描述（如“把重复邮箱标记出来”），可附带目标数据表/字段名
version: 1.0.0
category_code: product_development
install_source: official
install_method: download
skill_id: official_jRZfN4UJ
enabled_at: 1791893813687
name_zh: AI表格插件开发
---

# AI 表格插件开发（AI Table Plugin Generator）

Comprehensive development assistant for AI Table (钉钉AI表格) plugins. Supports two types of plugins:

1. **Script Plugins**: TypeScript automation scripts for data operations
2. **Sidebar Plugins**: React-based UI plugins with dual-page architecture

## 前置依赖

**本技能不依赖任何连接器（Connector）**，也不需要 MCP 工具或外部鉴权。它基于内置的 AI 表格 JSAPI 知识库（`shared/references/api/`）直接产出代码，因此：

- 无需执行连接器就绪性检查（无 Step 0）
- 不读写用户真实数据，只生成代码与配置文件，因此不需要写入类确认门
- **降级路径**：若 `references/` 未覆盖所需 API，**不得自行编造**，应向用户说明“当前知识库未覆盖该能力”，并给出最接近的可用替代方案

## 适用场景

适用：

- 为钉钉 AI 表格写**脚本插件**：批量改写字段值、去重/校验、汇总统计、按钮字段触发的自动化
- 为钉钉 AI 表格写**边栏插件**：带表单/列表/图表的侧边栏界面、选区联动、事件监听
- 查某个 AI 表格 JSAPI 的准确签名、字段值结构或批量上限
- 为已完成的脚本生成上架用的 `manifest.json`

不适用（应改用其他能力）：

- 只是想**查一条表格数据**或修改真实数据 —— 本技能只产出代码，不操作用户表格
- 非 AI 表格的钉钉形态（在线电子表格、文档插件）
- 与 AI 表格 无关的通用 React/TypeScript 问题

## 执行步骤

### Step 1 — 判定插件形态（必做，不要跳过）

先确认用户要的是哪种插件，再写任何代码：

- “跑一次把数据改完”、“点按钮触发”、“不需要界面” → **脚本插件**
- “需要一直开着的面板”、“要表单/图表”、“要跟随选中行变化” → **边栏插件**
- 描述不明确时直接问：是要一次性自动化脚本，还是常驻的侧边栏界面？

### Step 2 — 查阅对应指南与 API 知识库

**脚本插件**，读：

- `ai-script-generator/GUIDE.md` - Complete script generation guide
- `ai-script-generator/references/` - Script-specific examples

**边栏插件**，读：

- `ai-sidebar-plugin-generator/GUIDE.md` - Complete sidebar plugin guide
- `ai-sidebar-plugin-generator/references/` - UI development guides

**两者共用的 API 定义**：

- `shared/references/api/modules/` - Base, Sheet, Field, Record, View, Input, Output, UI
- `shared/references/api/interface/` - Type definitions

### Step 3 — 生成代码

按对应指南里的详细流程执行：

- Script: `ai-script-generator/GUIDE.md` → Phase 3
- Sidebar: `ai-sidebar-plugin-generator/GUIDE.md` → Phase 3-5

### Step 4 — 交付前自检

逐条比对对应指南的 Validation Checklist，重点确认：无自造 API、字段类型已用 `Base.isFieldOfType` 收窄、批量操作在上限内、所有异步调用有 try-catch。

## 输出格式

每次交付按以下顺序输出，不要只丢一堆代码：

1. **方案一句话**：选了哪种插件形态、为什么
2. **代码**：
   - 脚本插件 → 单个 TypeScript 文件（必选）+ `manifest.json`（仅在用户确认要上架时生成）
   - 边栏插件 → `service.ts` + `ui.tsx` + `script.tsx`，每个文件独立代码块并注明文件名
3. **关键 API 说明**：用到的 JSAPI 及其文档位置，便于用户核对
4. **限制与注意事项**：批量上限、权限要求、已知边界情况
5. **下一步**：如何在 AI 表格里调试运行

## Core Principles

1. **API Compliance**: Strictly follow AI Table API definitions in `shared/references/api/` directory
2. **No Fabrication**: Never invent APIs or methods - only use documented interfaces
3. **Production Ready**: Include proper error handling, user feedback, and TypeScript type safety
4. **Determine Plugin Type First**: Always clarify which type of plugin the user needs before generating code

## Plugin Type Selection

### When to Use Script Plugin

Use **Script Plugin** (`ai-script-generator/`) when user:
- Asks to "create a script", "generate AI table code", "write automation script"
- Needs data manipulation: CRUD operations, batch processing, data validation
- Wants button-triggered automation
- Requires simple input/output without complex UI

**Output**: Single TypeScript file + optional manifest.json

### When to Use Sidebar Plugin

Use **Sidebar Plugin** (`ai-sidebar-plugin-generator/`) when user:
- Asks to "create a sidebar plugin", "generate AI Table UI", "build plugin interface"
- Needs complex UI: forms, tables, charts, real-time displays
- Wants event-driven interactions: selection changes, record modifications
- Requires persistent sidebar interface

**Output**: service.ts + ui.tsx + script.tsx

## Workflow（详细展开，对应上方《执行步骤》）

### Phase 1: Determine Plugin Type

Ask clarifying questions:
- "Do you need a simple automation script or a sidebar UI plugin?"
- "Will this require a visual interface or just data processing?"
- "Should this run once or provide an ongoing interactive experience?"

### Phase 2: Consult Appropriate Documentation

**For Script Plugins**, read:
- `ai-script-generator/GUIDE.md` - Complete script generation guide
- `ai-script-generator/references/` - Script-specific examples

**For Sidebar Plugins**, read:
- `ai-sidebar-plugin-generator/GUIDE.md` - Complete sidebar plugin guide
- `ai-sidebar-plugin-generator/references/` - UI development guides

**For Both (Shared API)**, consult:
- `shared/references/api/modules/` - Base, Sheet, Field, Record, View modules
- `shared/references/api/interface/` - Type definitions

### Phase 3: Generate Code

Follow the specific workflow in the appropriate sub-skill:
- Script: `ai-script-generator/GUIDE.md` → Phase 3
- Sidebar: `ai-sidebar-plugin-generator/GUIDE.md` → Phase 3-5

## Directory Structure

```
ai-table-script-generator/
├── SKILL.md                          # 本文件 —— 包内唯一的 SKILL.md，技能入口
├── assets/
│   └── icon.svg                      # 技能图标（SVG 矢量图，免 200×200 尺寸校验）
├── ai-script-generator/              # Script plugin generation
│   ├── GUIDE.md                      # Detailed script workflow
│   └── references/                   # Script examples & API
├── ai-sidebar-plugin-generator/      # Sidebar plugin generation
│   ├── GUIDE.md                      # Detailed sidebar workflow
│   └── references/                   # UI development guides
└── shared/                           # Shared API documentation
    ├── GUIDE.md                      # Shared module overview
    └── references/api/               # Complete API reference
        ├── modules/                  # Base, Sheet, Field, Record, View, Input, Output, UI
        └── interface/                # Type definitions
```

## Quick Reference

### Script Plugin Template
```typescript
async function main() {
  try {
    const formResult = await Input.formAsync('配置', [/* form items */]);
    // Data processing logic
    Output.log('完成');
  } catch (error) {
    Output.error(`错误: ${error.message}`);
  }
}
await main();
```

### Sidebar Plugin Template

> **Important**: The addon-demo template generates `ui.html` and `script.html` (NOT `sidebar.html`). Plugin addresses: `http://localhost:3000/ui.html` (UI) + `http://localhost:3000/script.html` (Script Service).

**service.ts**:
```typescript
import { BaseApi } from 'dingtalk-docs-cool-app';

async function getData() {
  const sheet = DingdocsScript.base.getActiveSheet();
  if (!sheet) return null;
  // In service.ts (TypeScript) getField IS generic. In a *script plugin* it is not — use Base.isFieldOfType there.
  const field = sheet.getField<BaseApi.TextField>('字段名');
  const value = await field?.getValueAsync('recordId');
  return { name: sheet.getName(), value };
}
DingdocsScript.registerScript('getData', getData);
```

**script.tsx** (mounted on `root_script`, NOT `script`):
```typescript
import { initScript } from 'dingtalk-docs-cool-app';
// public/script.html has <div id="root_script">
const root = ReactDOM.createRoot(document.getElementById('root_script')!);
```

**ui.tsx** (event listeners MUST be gated on `ready` state):
```typescript
import { initView } from 'dingtalk-docs-cool-app';

function App() {
  const [ready, setReady] = useState(false);
  useEffect(() => {
    initView({
      onReady: () => { setReady(true); loadData(); },
    });
  }, []);
  // Gate events on ready to avoid white screen crash
  useEffect(() => {
    if (!ready) return;
    const off = Dingdocs.base.event.onSelectionChanged(handler);
    return () => off();
  }, [ready]);
}
```

## API Modules Overview

| Module | Purpose | Key Methods |
|--------|---------|-------------|
| Base | Entry point | `getActiveSheet()`, `getSheets()`, `isFieldOfType()`, `getCurrentUser()`, `getCorpId()`, `ui` |
| Sheet | Table operations | `getFields()`, `getRecordsAsync()`, `updateRecordsAsync()`, `insertField(name, type)` |
| Field | Field operations | `getName()`, `getType()`, `getValueAsync()`, `setValueAsync()`, `getFormatter()` |
| Record | Record access | `getId()`, `getCellValue()`, `getCellValues()` |
| View | View management | `getActiveView()`, `asGridView()` |
| Input | User input (Script only) | `textAsync()`, `selectAsync()`, `formAsync()` |
| Output | Logging (Script only) | `log()`, `info()`, `success()`, `error()`, `table()`, `clear()` |
| UI | Page interaction | `ui.toast()`, `ui.getSelection()`, `ui.getSelectedRecordIds()`, `ui.showRecordDetail()` |

## Important Notes

0. **本包只有一份 `SKILL.md`（即本文件）**；子目录里的 `GUIDE.md` 是被本文件按需读取的长指南，不是独立技能，不要重命名为 `SKILL.md`。
1. **Always read the specific sub-guide `GUIDE.md`** before generating code
2. **Use shared API references** for accurate method signatures
3. **Never hardcode** sheet names, field names, or credentials
4. **Batch limits (script / sidebar plugin)**: `insertRecordsAsync` ≤ 1000, `updateRecordsAsync` ≤ 500, `deleteRecordsAsync` ≤ 500, `getRecordsAsync` `pageSize` ≤ 500 (default 500). The 500/100/100/100 numbers are REST OpenAPI limits — do not apply them to plugins.
5. **Error handling** is mandatory for all async operations
6. **Script sandbox globals** are only `Base` / `Input` / `Output` / `fetch` / `console` / enum objects (`PermissionScope`, `PermissionType`, `ToastType`, `HighlightType`, `RecordDetailType`, `FilterConjunction`, `FilterOperator`, `FilterDuration`, `FillColorType`). There is **no** `window` / `document` / `localStorage`.
7. **`sheet.getField<T>()` generics only work in a sidebar plugin's `service.ts`**; in script plugins use `Base.isFieldOfType(field, type)`.
8. **`insertField` takes positional args** — `insertField(name, type, property?)`, never `insertField({ name, type })`. There is no `FieldType` enum; field types are string literals (`'text'`, `'multipleSelect'`, `'lastModifiedTime'`, …).
