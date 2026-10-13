# UI 模块

UI 模块提供了与用户界面交互的能力，支持显示消息提示、获取和设置选区等功能。

获取方式：

```typescript
const ui = DingdocsScript.base.ui;
```
```typescript
const ui = Base.ui
```

> **注意**：UI 模块在脚本插件和边栏插件中均可使用。脚本插件通过 `DingdocsScript.base.ui` 或 `Base.ui` 获取，边栏插件在 Service Page (service.ts) 中同样使用 `DingdocsScript.base.ui`。

## toast

显示一个消息提示，用于向用户反馈操作结果或重要信息。

```typescript
toast: (toastOptions: ToastOptions) => Promise<{ success: boolean }>;
```

**参数**
- `toastOptions`: `ToastOptions` - 消息提示配置

**返回值**
- `Promise<{ success: boolean }>` - 消息提示结果，返回操作是否成功

**示例**

### 基础用法

显示一个成功提示：
```typescript
await ui.toast({
  type: ToastType.SUCCESS,
  message: '操作成功！',
});
```

显示一个错误提示：
```typescript
await ui.toast({
  type: ToastType.ERROR,
  message: '操作失败，请重试',
});
```

### 自定义持续时间

显示一个持续 5 秒的警告提示：
```typescript
await ui.toast({
  type: ToastType.WARNING,
  message: '请注意数据安全',
  keepAlive: 'long',
});
```

显示一个常驻的提示消息：
```typescript
await ui.toast({
  type: ToastType.INFO,
  message: '重要通知：系统将在今晚维护',
  keepAlive: 'always',
});
```

### 可关闭的消息

显示一个可手动关闭的消息，并在关闭时执行回调：
```typescript
await ui.toast({
  type: ToastType.INFO,
  message: '数据正在处理中...',
  closeable: true,
  onClose: () => {
    // 用户关闭了消息的回调
  },
});
```

**注意事项**
1. 当 `keepAlive` 设置为 `'always'` 时，`closeable` 会自动设置为 `true`，确保用户可以手动关闭常驻消息
2. 不同的消息类型会以不同的背景色显示：
    - `SUCCESS`: 绿色背景
    - `ERROR`: 红色背景
    - `WARNING`: 黄色背景
    - `INFO`: 蓝色背景

## getSelection

获取当前多维表激活区域信息，返回用户当前选中的单元格、行或列的位置信息。

```typescript
getSelection: () => Promise<Position>;
```

**返回值**
- `Position` - 当前多维表激活区域信息

**示例**

### 基础用法

获取当前选中的单元格位置：
```typescript
const position = await ui.getSelection();
// 输出示例：{ sheetId: 'sheet123', viewId: 'view456', fieldId: 'field789', recordId: 'record001' }
```

### 判断选中类型

根据返回的位置信息判断用户选中的是单元格、整行还是整列：
```typescript
const position = await ui.getSelection();

if (position.fieldId && position.recordId) {
  // 选中了单元格
} else if (position.recordId && !position.fieldId) {
  // 选中了整行
} else if (position.fieldId && !position.recordId) {
  // 选中了整列
} else {
  // 没有选中任何单元格
}
```

**注意事项**
1. 选中整行时，`fieldId` 为 `undefined`
2. 选中整列时，`recordId` 为 `undefined`

## setSelection

设置当前多维表激活区域信息，可以通过代码控制用户的选中状态。

```typescript
setSelection: (position: Position) => Promise<boolean>;
```

**参数**
- `position`: `Position` - 要设置的位置信息

**返回值**
- `Promise<boolean>` - 设置是否成功

**示例**

### 选中指定单元格
```typescript
const success = await ui.setSelection({
  sheetId: 'sheet123',
  viewId: 'view456',
  fieldId: 'field789',
  recordId: 'record001',
});

if (success) {
  await ui.toast({
    type: ToastType.SUCCESS,
    message: '已定位到目标单元格',
  });
}
```

### 选中整行
```typescript
await ui.setSelection({
  sheetId: 'sheet123',
  viewId: 'view456',
  recordId: 'record001',
  // 不设置 fieldId 表示选中整行
});
```

### 选中整列
```typescript
await ui.setSelection({
  sheetId: 'sheet123',
  viewId: 'view456',
  fieldId: 'field789',
  // 不设置 recordId 表示选中整列
});
```

**注意事项**
1. `sheetId` 和 `viewId` 是必需的，必须指向当前打开的表格和视图
2. 如果指定的位置不存在或无效，方法将返回 `false`

## highlightSelection

高亮指定表格区域，用于临时标记和提示用户关注特定区域。高亮信息不会存入文档，刷新后会消失。

```typescript
highlightSelection: (highlightOptions: HighlightOptions) => Promise<boolean>;
```

**参数**
- `highlightOptions`: `HighlightOptions` - 高亮配置

**返回值**
- `Promise<boolean>` - 是否成功

**示例**

### 高亮单个单元格
```typescript
await ui.highlightSelection({
  type: HighlightType.WARNING,
  message: '此单元格数据异常',
  positions: [
    {
      sheetId: 'sheet123',
      viewId: 'view456',
      fieldId: 'field789',
      recordId: 'record001',
    },
  ],
});
```

### 高亮多个单元格
```typescript
await ui.highlightSelection({
  type: HighlightType.INFO,
  message: '这些单元格需要填写',
  positions: [
    {
      sheetId: 'sheet123',
      viewId: 'view456',
      fieldId: 'field789',
      recordId: 'record001',
    },
    {
      sheetId: 'sheet123',
      viewId: 'view456',
      fieldId: 'field789',
      recordId: 'record002',
    },
    {
      sheetId: 'sheet123',
      viewId: 'view456',
      fieldId: 'field789',
      recordId: 'record003',
    },
  ],
});
```

### 高亮整行
```typescript
await ui.highlightSelection({
  type: HighlightType.ERROR,
  message: '此行数据有误',
  positions: [
    {
      sheetId: 'sheet123',
      viewId: 'view456',
      recordId: 'record001',
      // 不设置 fieldId 表示高亮整行
    },
  ],
});
```

**注意事项**
1. 高亮是临时的，刷新页面或退出单元格编辑态后会消失
2. 高亮信息不会保存到文档中
3. 可以同时高亮多个位置
4. 不同的高亮类型会显示不同的颜色

## clearHighlightSelection

清除当前所有的高亮区域。

```typescript
clearHighlightSelection: () => Promise<boolean>;
```

**返回值**
- `Promise<boolean>` - 是否成功

**示例**

### 基础用法
```typescript
// 先高亮一些区域
await ui.highlightSelection({
  type: HighlightType.INFO,
  message: '需要处理的数据',
  positions: [
    {
      sheetId: 'sheet123',
      viewId: 'view456',
      fieldId: 'field789',
      recordId: 'record001',
    },
  ],
});

// 处理完成后清除高亮
await ui.clearHighlightSelection();

await ui.toast({
  type: ToastType.SUCCESS,
  message: '处理完成',
});
```

## showRecordDetail

展示记录详情，可以在侧边栏或弹窗中显示指定记录的详细信息。

```typescript
showRecordDetail: (info: RecordDetailInfo, config?: RecordDetailConfig) => Promise<boolean>;

interface RecordDetailConfig {
  /** 记录详情的展示形式, 默认为侧边栏形式 */
  type?: RecordDetailType;
}

enum RecordDetailType {
  /** 弹窗模式 */
  MODAL = 'modal',
  /** 侧边栏形式（默认） */
  SIDE_PANEL = 'sidePanel',
}
```

**参数**
- `info`: `RecordDetailInfo` - 记录的基本信息
- `config`: `RecordDetailConfig` - 记录详情配置（可选）

**返回值**
- `Promise<boolean>` - 是否成功

**示例**

### 在侧边栏显示记录详情
```typescript
await ui.showRecordDetail({
  sheetId: 'sheet123',
  viewId: 'view456',
  recordId: 'record001',
});
```

### 在弹窗中显示记录详情
```typescript
await ui.showRecordDetail(
  {
    sheetId: 'sheet123',
    viewId: 'view456',
    recordId: 'record001',
  },
  {
    type: RecordDetailType.MODAL,
  }
);
```

### 配合选区使用
```typescript
// 获取当前选中的记录
const position = await ui.getSelection();

if (position.recordId) {
  // 显示选中记录的详情
  await ui.showRecordDetail({
    sheetId: position.sheetId!,
    viewId: position.viewId!,
    recordId: position.recordId,
  });
} else {
  await ui.toast({
    type: ToastType.WARNING,
    message: '请先选中一条记录',
  });
}
```

**注意事项**
1. `sheetId`、`viewId` 和 `recordId` 都是必需的
2. 如果不指定 `config.type`，默认以侧边栏形式展示
3. 侧边栏对应的枚举值是 `RecordDetailType.SIDE_PANEL`（`'sidePanel'`），**不是 `SIDEBAR` / `'sidebar'`**

## getSelectedRecordIds

获取当前用户有效选中的记录 ID 列表。

```typescript
getSelectedRecordIds: () => Promise<IHostApiGetSelectedRecordIdsResult>;
```

**返回值**
- 当前有效选中的记录 ID 列表

**示例**

```typescript
const result = await ui.getSelectedRecordIds();
// 选中多行时可以拿到完整的 recordId 列表，比 getSelection() 只能拿到起始单元格更合适
```

> ⚠️ `getSelection()` 只返回选区起始单元格的 `fieldId` / `recordId`；需要“用户选中了哪几行”时应该用 `getSelectedRecordIds()`。
