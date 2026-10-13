# LastModifiedTimeField 最后更新时间字段

`LastModifiedTimeField`，继承自基础 [Field](../Field%20模块.md) 类，专门用于处理最后修改时间字段数据。系统自动记录数据行的最后修改时间，以毫秒级Unix时间戳形式存储。

:::
最后更新时间字段是系统自动生成的行记录最后更新时间，是一个只读字段，不能手动设置值。
:::

## 字段特有方法

### getValueAsync

获取指定行记录该最后修改时间字段的值。

```typescript
getValueAsync: (recordId: string) => Promise<DateCellValue | null>

```

**参数**

*   `recordId` : `string` - 记录ID
    

**返回值**

*   [`Promise<DateCellValue | null>`](../../interface/API%20类型定义.md) - 最后修改时间的时间戳（毫秒），当字段值为空时返回null
    

**示例**

```typescript
// 获取最后修改时间字段值
const lastModifiedTimeField = sheet.getField<LastModifiedTimeField>('最后修改时间');
if (lastModifiedTimeField) {
  const timestamp = await lastModifiedTimeField.getValueAsync('rec123456');
  if (timestamp !== null) {
    const date = new Date(timestamp);
    console.log(`最后修改时间: ${date.toLocaleString()}`);
  } else {
    console.log('未设置最后修改时间');
  }
}

```
```typescript
// 获取最后修改时间字段值
const lastModifiedTimeField = sheet.getField('最后修改时间');
if (Base.isFieldOfType(lastModifiedTimeField, 'lastModifiedTime')) {
  const timestamp = await lastModifiedTimeField.getValueAsync('rec123456');
  if (timestamp !== null) {
    const date = new Date(timestamp);
    Output.log(`最后修改时间: ${date.toLocaleString()}`);
  } else {
    Output.log('未设置最后修改时间');
  }
}

```

### getDateFormat

获取最后修改时间字段的格式。

```typescript
getDateFormat: () => DateFormatter

```

**返回值**

*   [`DateFormatter`](../../interface/API%20类型定义.md) - 日期格式
    

**示例**

```typescript
// 获取最后修改时间字段格式
const lastModifiedTimeField = sheet.getField<LastModifiedTimeField>('最后修改时间');
if (lastModifiedTimeField) {
  const formatter = lastModifiedTimeField.getDateFormat();
  console.log(`最后修改时间格式: ${formatter}`);
}

```
```typescript
// 获取最后修改时间字段格式
const lastModifiedTimeField = sheet.getField('最后修改时间');
if (Base.isFieldOfType(lastModifiedTimeField, 'lastModifiedTime')) {
  const formatter = lastModifiedTimeField.getDateFormat();
  Output.log(`最后修改时间格式: ${formatter}`);
}

```

### setDateFormat

设置最后修改时间字段的格式化器。

```typescript
setDateFormat: (format: DateFormatter) => string

```

**参数**

*   `format`: [`DateFormatter`](../../interface/API%20类型定义.md) - 日期格式
    

**返回值**

*   `string` - 字段ID
    

**示例**

```typescript
// 设置最后修改时间字段格式
const lastModifiedTimeField = sheet.getField<LastModifiedTimeField>('最后修改时间');
if (lastModifiedTimeField) {
  lastModifiedTimeField.setDateFormat('YYYY-MM-DD HH:mm:ss');
  console.log('最后修改时间格式已更新');
}

```
```typescript
// 设置最后修改时间字段格式
const lastModifiedTimeField = sheet.getField('最后修改时间');
if (Base.isFieldOfType(lastModifiedTimeField, 'lastModifiedTime')) {
  lastModifiedTimeField.setDateFormat('YYYY-MM-DD HH:mm:ss');
  Output.log('最后修改时间格式已更新');
}

```