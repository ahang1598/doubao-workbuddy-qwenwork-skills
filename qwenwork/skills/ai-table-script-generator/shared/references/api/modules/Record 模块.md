# Record 模块

表示数据表中的单条记录，提供了访问和操作记录数据的方法。

## 基本信息方法

### isValid

检查记录对象是否有效。

```typescript
isValid: () => boolean

```

**返回值**

*   `boolean` - 如果记录存在且有效返回true，否则返回false
    

**示例**

```typescript
// 检查记录是否有效
const record = await sheet.getRecordAsync('rec123456');
if (record && record.isValid()) {
  console.log('记录有效，可以进行操作');
} else {
  console.log('记录无效或已被删除');
}

```
```typescript
// 检查记录是否有效
const record = await sheet.getRecordAsync('rec123456');
if (record && record.isValid()) {
  Output.log('记录有效，可以进行操作');
} else {
  Output.log('记录无效或已被删除');
}

```

### getSheetId

获取记录所属数据表的ID。

```typescript
getSheetId: () => string

```

**返回值**

*   `string` - 数据表ID
    

**示例**

```typescript
const sheetId = record.getSheetId();
console.log(`记录所属数据表ID: ${sheetId}`);

```
```typescript
const sheetId = record.getSheetId();
Output.log(`记录所属数据表ID: ${sheetId}`);

```

### getId

获取记录ID。

```typescript
getId: () => string

```

**返回值**

*   `string` - 记录ID
    

**示例**

```typescript
const recordId = record.getId();

```

## 字段值获取方法

### getCellValue

获取记录中指定字段的值。

```typescript
getCellValue: (fieldIdOrName: string) => CellValue | null

```

**参数**

*   `fieldIdOrName` - 字段ID或字段名称
    

**返回值**

*   [`CellValue | null`](../interface/API%20类型定义.md)\- 字段值，根据字段类型返回不同的数据结构，如果字段不存在或无权限访问则返回null
    

**示例**

```typescript
// 通过字段名称获取值
const title = record.getCellValue('标题');
console.log(`任务标题: ${title}`);

// 处理不同类型的字段值
const dueDate = record.getCellValue('截止日期');
if (dueDate) {
  console.log(`截止日期: ${new Date(dueDate).toLocaleDateString()}`);
}

```

### getCellValues

获取记录中所有字段的值。

```typescript
getCellValues: (options?: IGetCellValuesOptions) => Record<string, CellValue>;

interface IGetCellValuesOptions {
  returnFieldsById?: boolean;
}
```

**参数**

*   `options`: [`IGetCellValuesOptions`](../interface/API%20类型定义.md) - 是否使用字段ID作为返回对象的键，默认为false（使用字段名称）
    

**返回值**

*   [`Record<string /** 字段ID */, CellValue /** 字段值 */>`](../interface/API%20类型定义.md)\- 字段名称/ID到字段值的映射
    

**示例**

```typescript
// 获取所有字段值（使用字段名称作为键）
const allValues = record.getCellValues();
console.log('记录所有字段值:');
Object.entries(allValues).forEach(([fieldName, value]) => {
  console.log(`- ${fieldName}: ${JSON.stringify(value)}`);
});

// 获取所有字段值（使用字段ID作为键）
const allValuesById = record.getCellValues({ returnFieldsById: true });
console.log('记录所有字段值(按ID):');
Object.entries(allValuesById).forEach(([fieldId, value]) => {
  console.log(`- ${fieldId}: ${JSON.stringify(value)}`);
});

```
```typescript
// 获取所有字段值（使用字段名称作为键）
const allValues = record.getCellValues();
Output.log('记录所有字段值:');
Object.entries(allValues).forEach(([fieldName, value]) => {
  Output.log(`- ${fieldName}: ${JSON.stringify(value)}`);
});

// 获取所有字段值（使用字段ID作为键）
const allValuesById = record.getCellValues({ returnFieldsById: true });
Output.log('记录所有字段值(按ID):');
Object.entries(allValuesById).forEach(([fieldId, value]) => {
  Output.log(`- ${fieldId}: ${JSON.stringify(value)}`);
});

```

## 记录元数据方法

### getCreatedBy

获取记录的创建者信息。

```typescript
getCreatedBy: () => UserCellValue | null

```

**返回值**

*   [`UserCellValue | null`](../interface/API%20类型定义.md) - 创建者用户信息，如果信息不可用则返回null
    

### getLastModifiedBy

获取记录的最后修改者信息。

```typescript
getLastModifiedBy: () => UserCellValue | null

```

**返回值**

*   [`UserCellValue | null`](../interface/API%20类型定义.md) - 最后修改者用户信息，如果信息不可用则返回null
    

### getCreatedTime

获取记录的创建时间。

```typescript
getCreatedTime: () => number

```

**返回值**

*   `number` - 创建时间的时间戳（毫秒）
    

**示例**

```typescript
// 获取记录创建时间
const createdTime = record.getCreatedTime();
const createdDate = new Date(createdTime);

```

### getLastModifiedTime

获取记录的最后修改时间。

```typescript
getLastModifiedTime: () => number

```

**返回值**

*   `number` - 最后修改时间的时间戳（毫秒）
    

**示例**

```typescript
// 获取记录最后修改时间
const updatedTime = record.getLastModifiedTime();
const updatedDate = new Date(updatedTime);
console.log(`记录最后修改于: ${updatedDate.toLocaleString()}`);

// 计算记录最后修改以来的时间
const now = Date.now();
const daysSinceUpdate = Math.floor((now - updatedTime) / (24 * 60 * 60 * 1000));
console.log(`上次更新已过去 ${daysSinceUpdate} 天`);

```
```typescript
// 获取记录最后修改时间
const updatedTime = record.getLastModifiedTime();
const updatedDate = new Date(updatedTime);
Output.log(`记录最后修改于: ${updatedDate.toLocaleString()}`);

// 计算记录最后修改以来的时间
const now = Date.now();
const daysSinceUpdate = Math.floor((now - updatedTime) / (24 * 60 * 60 * 1000));
Output.log(`上次更新已过去 ${daysSinceUpdate} 天`);

```