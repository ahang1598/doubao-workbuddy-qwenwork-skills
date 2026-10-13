# AI Table API Quick Reference

## Quick Lookup

### Global Objects

脚本沙箱里只有以下全局变量可用（内置模块仅 `console`）：

- `Base` - AI表格顶级对象
- `Input` - 用户输入交互
- `Output` - 输出显示
- `fetch` - 网络请求
- 枚举：`PermissionScope` / `PermissionType` / `FilterConjunction` / `FilterOperator` / `FilterDuration` / `FillColorType` / `ToastType` / `HighlightType` / `RecordDetailType`

> ⚠️ 没有 `window` / `document` / `localStorage`，不要生成依赖 DOM 的代码。
> ⚠️ `Input` / `Output` **只在脚本插件里存在**；边栏插件的 Script Service 里没有这两个对象。

### Sheet Operations
```typescript
Base.getActiveSheet()              // 获取当前激活的数据表
Base.getSheet(idOrName)            // 根据ID或名称获取数据表
Base.getSheets()                   // 获取所有数据表
```

### Field Operations
```typescript
sheet.getField(idOrName)           // 获取字段（脚本插件不支持泛型！不要写 getField<T>()）
sheet.getFields()                  // 获取所有字段
sheet.getFieldsByType(type)        // 获取指定类型的字段
sheet.insertField(name, type, property)  // 插入字段（位置参数，不是对象！）
Base.isFieldOfType(field, type)    // 检查/收窄字段类型
```

### Record Operations
```typescript
sheet.getRecordsAsync(options)     // 获取记录
sheet.insertRecordsAsync(records)  // 插入记录
sheet.updateRecordsAsync(records)  // 更新记录
sheet.deleteRecordsAsync(ids)      // 删除记录
```

### Field Type-Specific Methods

#### Text Field
```typescript
await textField.getValueAsync(recordId)  // Promise<string | null>
await textField.setValueAsync(recordId, text: string)  // Promise<boolean>
```

#### Number Field
```typescript
await numberField.getValueAsync(recordId)  // Promise<number | null>
await numberField.setValueAsync(recordId, num: number)  // Promise<boolean>
// 声明类型是 number；运行时也接受可转数字的字符串，但编辑器会报类型错误，推荐传 number
numberField.getFormatter()  // NumericalFormatter（注意：没有 getFormat()）
```

#### Date Field
```typescript
await dateField.getValueAsync(recordId)  // Promise<number | null> (毫秒级 timestamp)
await dateField.setValueAsync(recordId, timestamp: number)  // Promise<boolean>
// 声明类型是毫秒级 timestamp；运行时也接受 dayjs 可解析的日期字符串，但编辑器会报类型错误
dateField.getDateFormat()  // DateFormatter
```

#### Single Select Field
```typescript
await singleSelectField.getValueAsync(recordId)  // Promise<{id, name} | null>
await singleSelectField.setValueAsync(recordId, optionId: string)  // Promise<boolean>
// 运行时先按选项 id 匹配，匹配不上再按选项名匹配，所以也可以传选项名
// ⚠️ 传 { id } / { name } 对象形式【只有边栏插件(ADDON)支持】，脚本插件传对象会抛错
singleSelectField.getOptions()  // Array<{id, name, color}>
singleSelectField.addOption(name)  // string（只接收 name，不支持设色）
```

#### Multiple Select Field
```typescript
// 字段类型字面量是 'multipleSelect'（不是 'multiSelect'）
await multiSelectField.getValueAsync(recordId)  // Promise<Array<{id, name}> | null>
await multiSelectField.setValueAsync(recordId, optionIds: string | string[])  // Promise<boolean>
multiSelectField.getOptions()  // Array<{id, name, color}>
multiSelectField.addOption(name)  // string
```

#### Attachment Field
```typescript
await attachmentField.getValueAsync(recordId)  // Promise<AttachmentValue[] | null>
await attachmentField.setValueAsync(recordId, file: IOpenFile | IOpenFile[] | AttachmentValue | AttachmentValue[])  // Promise<boolean>
await attachmentField.getAttachmentUrls(recordId)  // Promise<string[]>
await attachmentField.getAttachmentDetails(recordId)  // Promise<Array<{filename, type, url}>>
```

#### URL Field
```typescript
await urlField.getValueAsync(recordId)  // Promise<{link, text?} | null>
await urlField.setValueAsync(recordId, url: string | {link, text?})  // Promise<boolean>
```

#### User Field
```typescript
await userField.getValueAsync(recordId)  // Promise<Array<{unionId, userId, name?}> | null>
await userField.setValueAsync(recordId, users: Array<{userId?, unionId?}>)  // Promise<boolean>
```

#### Link Fields (Uni/Bidirectional)
```typescript
await linkField.getValueAsync(recordId)  // Promise<{linkedRecordIds: string[]} | null>
await linkField.setValueAsync(recordId, value: {linkedRecordIds: string[]})  // Promise<boolean>
```

#### Rating Field
```typescript
await ratingField.getValueAsync(recordId)  // Promise<number | null>
await ratingField.setValueAsync(recordId, value: number)  // Promise<boolean>
ratingField.getMin()  // number
ratingField.getMax()  // number
```

#### Progress Field
```typescript
await progressField.getValueAsync(recordId)  // Promise<number | null>
await progressField.setValueAsync(recordId, value: number)  // Promise<boolean>
progressField.getMin()  // number
progressField.getMax()  // number
progressField.getFormatter()  // ProgressFormatter
```

#### Currency Field
```typescript
await currencyField.getValueAsync(recordId)  // Promise<number | null>
await currencyField.setValueAsync(recordId, value: number | string)  // Promise<boolean>
currencyField.getDecimalDigits()  // number
currencyField.getCurrencyType()  // CurrencyType
```

### Input Methods
```typescript
await Input.textAsync(label: string, config?: InputConfig<string>)  // Promise<string>
await Input.selectAsync(label: string, options: Array<string | {text, value}>, config?)  // Promise<string | V | undefined>
await Input.formAsync(title: string, items: FormItem[], config?)  // Promise<Record<string, FormItemResult | undefined>>
```

### Output Methods
```typescript
// 全部是可变参数 (...message: unknown[]) => void
Output.log(...message)        // 普通日志
Output.info(...message)       // 提示信息（蓝色）
Output.warn(...message)       // 警告信息（黄色）
Output.error(...message)      // 错误信息（红色）
Output.success(...message)    // 成功信息（绿色）
Output.markdown(message: string)  // Markdown格式
Output.table(data: unknown)   // 表格展示
Output.clear()                // 清空运行面板
```

## Type Definitions

### IOpenFile
```typescript
interface IOpenFile {
  name: string;
  type: string;
  size: number;
  content: string | ArrayBuffer;  // base64 字符串或 ArrayBuffer
}
```

### AttachmentValue
```typescript
// 描述的是【单个附件】；单元格值是 AttachmentValue[]
type AttachmentValue = {
  type: string;
  filename: string;
  url: string;
  thumbUrl?: string;
  size?: number;
  resourceId?: string;
  isLink?: boolean;
};
```

### GetRecordsOptions
```typescript
interface GetRecordsOptions {
  recordIds?: string[];
  fieldIds?: string[];
  fieldIdOrNames?: string[];
  pageSize?: number;  // 脚本/边栏插件默认 500，取值范围 1~500
  cursor?: string;
  filter?: Filter;    // 见下方 Filter
  viewId?: string;
}
```

### Filter（getRecordsAsync 专用，与 GridView 筛选不通用）
```typescript
interface Filter {
  combination?: 'and' | 'or';  // 默认 'and'
  conditions: Array<{
    field: string;   // 字段ID或字段名
    operator: 'equal' | 'notEqual' | 'greater' | 'greaterEqual' | 'less' | 'lessEqual'
      | 'contain' | 'notContain' | 'empty' | 'notEmpty';
    value?: unknown[];  // 注意是数组
  }>;
}
// ❌ 错误：{ conjunction: 'and', conditions: [{ fieldName, operator: 'is', value: 'x' }] }
// ✅ 正确：{ combination: 'and', conditions: [{ field: '状态', operator: 'equal', value: ['x'] }] }
```

### GetRecordsResult
```typescript
interface GetRecordsResult {
  hasMore: boolean;
  cursor?: string;
  records: Record[];
  total?: number;
}
```

### RecordToInsert
```typescript
interface RecordToInsert {
  fields: Record<string, CellValue>;
}
```

### RecordToUpdate
```typescript
interface RecordToUpdate {
  id: string;
  fields: Record<string, CellValue>;
}
```

## Common Patterns

### Batch Processing Pattern
```typescript
const batchSize = 500;  // updateRecordsAsync 单次上限 500
while (updates.length > 0) {
  const batch = updates.slice(0, batchSize);
  await sheet.updateRecordsAsync(batch);
  updates.splice(0, batchSize);
}
```

### Pagination Pattern
```typescript
const allRecords = [];
let hasMore = true;
let cursor = "";

while (hasMore) {
  const result = await sheet.getRecordsAsync({
    pageSize: 500,
    cursor: cursor,
  });
  allRecords.push(...result.records);
  hasMore = result.hasMore;
  cursor = result.cursor;
}
```

### Type-Safe Field Access
```typescript
const field = sheet.getField('fieldName');
if (Base.isFieldOfType(field, 'singleSelect')) {
  const options = field.getOptions();
  // Type-safe operations
}
```

### Error Handling Pattern
```typescript
try {
  // Operations
  Output.log('操作成功');
} catch (error) {
  if (error instanceof Error) {
    Output.error(`执行过程中发生错误: ${error.message}`);
  } else {
    Output.error(`执行过程中发生未知错误`);
  }
}
```

## Limitations

以下是**脚本插件 / 边栏插件**（appType = SCRIPT / ADDON）的真实上限：

| 操作 | 单次上限 | 超限错误 |
|---|---|---|
| `insertRecordsAsync` | **1000** | `You may insert at most 1000 records at a time.` |
| `updateRecordsAsync` | **500** | `You may update at most 500 records at a time.` |
| `deleteRecordsAsync` | **500** | `You may delete at most 500 records at a time.` |
| `getRecordsAsync` 的 `pageSize` | **500**（不传时默认 500） | `PageSize should be between 1 and 500.` |

> ⚠️ 常见错误：把 REST OpenAPI 通道的上限（insert 500 / update 100 / delete 100 / pageSize 100）当成插件上限。插件里用 50 做 batchSize 会白白多跑10 倍请求。

## Important Notes

1. **Never invent APIs**: Only use methods documented in references/api/
2. **Always check field types**: Use `Base.isFieldOfType()` before type-specific operations
3. **Match value types**: Ensure values match expected field type formats
4. **Use batch processing**: Process records in batches to avoid limits
5. **Handle errors gracefully**: Always wrap operations in try-catch blocks
6. **Provide user feedback**: Use Output methods to inform users of progress