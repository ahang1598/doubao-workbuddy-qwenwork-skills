# CreatedTimeField 创建时间字段

`CreatedTimeField`，继承自基础 [Field](../Field%20模块.md) 类，专门用于处理创建时间字段数据。系统自动记录数据行的创建时间，以毫秒级Unix时间戳形式存储。

:::
创建时间字段是系统自动生成的行记录创建时间，是一个只读字段，不能手动设置值。
:::

## 字段特有方法

### getValueAsync

获取指定行记录该创建时间字段的值。

```typescript
getValueAsync: (recordId: string) => Promise<DateCellValue | null>

```

**参数**

*   `recordId` : `string` - 记录ID
    

**返回值**

*   [`Promise<DateCellValue | null>`](../../interface/API%20类型定义.md) - 创建时间的时间戳（毫秒），当字段值为空时返回null
    

**示例**

```typescript
// 获取创建时间字段值
const createdTimeField = sheet.getField<CreatedTimeField>('创建时间');
if (createdTimeField) {
  const timestamp = await createdTimeField.getValueAsync('rec123456');
  if (timestamp !== null) {
    const date = new Date(timestamp);
    console.log(`创建时间: ${date.toLocaleString()}`);
  } else {
    console.log('未设置创建时间');
  }
}

```
```typescript
// 获取创建时间字段值
const createdTimeField = sheet.getField('创建时间');
if (Base.isFieldOfType(createdTimeField, 'createdTime')) {
  const timestamp = await createdTimeField.getValueAsync('rec123456');
  if (timestamp !== null) {
    const date = new Date(timestamp);
    Output.log(`创建时间: ${date.toLocaleString()}`);
  } else {
    Output.log('未设置创建时间');
  }
}

```

### getDateFormat

获取创建时间字段的格式。

```typescript
getDateFormat: () => DateFormatter

```

**返回值**

*   [`DateFormatter`](../../interface/API%20类型定义.md) - 日期格式
    

**示例**

```typescript
// 获取创建时间字段格式
const createdTimeField = sheet.getField<CreatedTimeField>('创建时间');
if (createdTimeField) {
  const formatter = createdTimeField.getDateFormat();
  console.log(`创建时间格式: ${formatter}`);
}

```
```typescript
// 获取创建时间字段格式
const createdTimeField = sheet.getField('创建时间');
if (Base.isFieldOfType(createdTimeField, 'createdTime')) {
  const formatter = createdTimeField.getDateFormat();
  Output.log(`创建时间格式: ${formatter}`);
}

```

### setDateFormat

设置创建时间字段的格式。

```typescript
setDateFormat: (format: DateFormatter) => string

```

**参数**

*   `format`: [`DateFormatter`](../../interface/API%20类型定义.md) - 日期格式
    

**返回值**

*   `string` - 字段ID
    

**示例**

```typescript
// 设置创建时间字段格式
const createdTimeField = sheet.getField<CreatedTimeField>('创建时间');
if (createdTimeField) {
  createdTimeField.setDateFormat('YYYY-MM-DD HH:mm:ss');
  console.log('创建时间格式已更新');
}

```
```typescript
// 设置创建时间字段格式
const createdTimeField = sheet.getField('创建时间');
if (Base.isFieldOfType(createdTimeField, 'createdTime')) {
  createdTimeField.setDateFormat('YYYY-MM-DD HH:mm:ss');
  Output.log('创建时间格式已更新');
}

```