# DateField 日期字段

DateField 继承自基础 [Field](../Field%20模块.md) 类，专门用于处理日期和时间类型数据。以毫秒级Unix时间戳形式存储。它支持不同的日期格式化选项，适合用于存储截止日期、创建时间、开始/结束时间等场景。

## 字段特有方法

### getValueAsync

获取指定记录在该日期字段的值。

```typescript
getValueAsync: (recordId: string) => Promise<DateCellValue | null>

```

**参数**

*   `recordId`: `string` - 记录ID
    

**返回值**

*   [`Promise<DateCellValue | null>`](../../interface/API%20类型定义.md) - 日期时间戳（毫秒），如果记录不存在或值为空则返回null
    

**示例**

```typescript
// 获取日期字段值
const dueDateField = sheet.getField<DateField>('截止日期');
if (dueDateField) {
  const timestamp = await dueDateField.getValueAsync('rec123456');
  if (timestamp !== null) {
    const date = new Date(timestamp);
    console.log(`截止日期: ${date.toLocaleDateString()}`);
  } else {
    console.log('未设置截止日期');
  }
}

```
```typescript
// 获取日期字段值
const dueDateField = sheet.getField('截止日期');
if (Base.isFieldOfType(dueDateField, 'date')) {
  const timestamp = await dueDateField.getValueAsync('rec123456');
  if (timestamp !== null) {
    const date = new Date(timestamp);
    Output.log(`截止日期: ${date.toLocaleDateString()}`);
  } else {
    Output.log('未设置截止日期');
  }
}

```

### setValueAsync

设置指定记录在该日期字段的值。

```typescript
setValueAsync: (recordId: string, timestamp: DateCellValue) => Promise<boolean>
```

**参数**

*   `recordId`: `string` - 记录ID
    
*   `timestamp`: [`DateCellValue`](../../interface/API%20类型定义.md) - 日期时间戳（毫秒）
    

**返回值**

*   `Promise<boolean>`\- 操作是否成功
    

**示例**

```typescript
// 设置日期字段值
const dueDateField = sheet.getField<DateField>('截止日期');
if (dueDateField) {
  // 设置为明天的日期
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  
  const success = await dueDateField.setValueAsync('rec123456', tomorrow.getTime());
  if (success) {
    console.log('截止日期已更新');
  }
}

```
```typescript
// 设置日期字段值
const dueDateField = sheet.getField('截止日期');
if (Base.isFieldOfType(dueDateField, 'date')) {
  // 设置为明天的日期
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  
  const success = await dueDateField.setValueAsync('rec123456', tomorrow.getTime());
  if (success) {
    Output.log('截止日期已更新');
  }
}

```

### getDateFormat

获取日期字段的格式。

```typescript
getDateFormat: () => DateFormatter

```

**返回值**

*   [`DateFormatter`](../../interface/API%20类型定义.md) - 日期格式化器对象
    

**示例**

```typescript
// 获取日期格式
const createdTimeField = sheet.getField<DateField>('创建时间');
if (createdTimeField) {
  const formatter = createdTimeField.getDateFormat();
  console.log(`日期格式: ${formatter}`);
}

```
```typescript
// 获取日期格式
const createdTimeField = sheet.getField('创建时间');
if (Base.isFieldOfType(createdTimeField, 'date')) {
  const formatter = createdTimeField.getDateFormat();
  Output.log(`日期格式: ${formatter}`);
}

```

### setDateFormat

设置日期字段的格式化器。

```typescript
setDateFormat: (formatter: DateFormatter) => string

```

**参数**

*   `formatter`: [`DateFormatter`](../../interface/API%20类型定义.md) - 日期格式化器对象
    

**返回值**

*   `string` - 字段ID
    

**示例**

```typescript
// 设置日期格式
const dueDateField = sheet.getField<DateField>('截止日期');
if (dueDateField) {
  dueDateField.setDateFormat('YYYY/MM/DD HH:mm');
  console.log('日期格式已更新');
}

```
```typescript
// 设置日期格式
const dueDateField = sheet.getField('截止日期');
if (Base.isFieldOfType(dueDateField, 'date')) {
  dueDateField.setDateFormat('YYYY/MM/DD HH:mm');
  Output.log('日期格式已更新');
}

```