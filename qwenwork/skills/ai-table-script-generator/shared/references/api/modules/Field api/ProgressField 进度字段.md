# ProgressField 进度字段

:::
此字段正在灰度放量阶段
:::

`ProgressField`，继承自基础 [Field](../Field%20模块.md) 类，专门用于处理进度字段数据。用于表示任务或项目的完成进度，通常以百分比形式展示，支持设置进度范围。

## 字段特有方法

### getValueAsync

获取指定行记录该进度字段的值。

```typescript
getValueAsync: (recordId: string) => Promise<number | null>

```

**参数**

*   `recordId` : `string` - 记录ID
    

**返回值**

*   `Promise<number | null>` - 进度值，当字段值为空时返回null
    

**示例**

```typescript
// 获取进度字段值
const progressField = sheet.getField<ProgressField>('完成进度');
if (progressField) {
  const progress = await progressField.getValueAsync('rec123456');
  console.log(`完成进度: ${progress !== null ? progress : 0}%`);
}

```
```javascript
// 获取进度字段值
const progressField = sheet.getField('完成进度');
if (Base.isFieldOfType(progressField, 'progress')) {
  const progress = await progressField.getValueAsync('rec123456');
  Output.log(`完成进度: ${progress !== null ? progress : 0}%`);
}

```

### setValueAsync

设置指定行记录该进度字段的值。

```typescript
setValueAsync: (recordId: string, val: number) => Promise<boolean>

```

**参数**

*   `recordId`: `string` - 记录ID
    
*   `val`: `number` - 要设置的进度值
    

**返回值**

*   `Promise<boolean>` - 设置是否成功
    

**示例**

```typescript
// 设置进度字段值
const progressField = sheet.getField<ProgressField>('完成进度');
if (progressField) {
  const success = await progressField.setValueAsync('rec123456', 75);
  if (success) {
    console.log('进度更新成功');
  } else {
    console.log('进度更新失败');
  }
}

```
```javascript
// 设置进度字段值
const progressField = sheet.getField('完成进度');
if (Base.isFieldOfType(progressField, 'progress')) {
  const success = await progressField.setValueAsync('rec123456', 75);
  if (success) {
    Output.log('进度更新成功');
  } else {
    Output.log('进度更新失败');
  }
}

```

### getMin

获取进度字段的最小值。

```typescript
getMin: () => number

```

**返回值**

*   `number` - 最小值
    

**示例**

```typescript
// 获取进度字段最小值
const progressField = sheet.getField<ProgressField>('完成进度');
if (progressField) {
  const minProgress = progressField.getMin();
  console.log(`进度最小值: ${minProgress}`);
}

```
```javascript
// 获取进度字段最小值
const progressField = sheet.getField('完成进度');
if (Base.isFieldOfType(progressField, 'progress')) {
  const minProgress = progressField.getMin();
  Output.log(`进度最小值: ${minProgress}`);
}

```

### setMin

设置进度字段的最小值。

```typescript
setMin: (val: number) => string

```

**参数**

*   `val`: `number` - 最小值
    

**返回**

*   `string` - 字段ID
    

**示例**

```typescript
// 设置进度字段最小值
const progressField = sheet.getField<ProgressField>('完成进度');
if (progressField) {
  progressField.setMin(0);
  console.log('已设置进度最小值为0');
}

```
```javascript
// 设置进度字段最小值
const progressField = sheet.getField('完成进度');
if (Base.isFieldOfType(progressField, 'progress')) {
  progressField.setMin(0);
  Output.log('已设置进度最小值为0');
}

```

### getMax

获取进度字段的最大值。

```typescript
getMax: () => number

```

**返回值**

*   `number` - 最大值
    

**示例**

```typescript
// 获取进度字段最大值
const progressField = sheet.getField<ProgressField>('完成进度');
if (progressField) {
  const maxProgress = progressField.getMax();
  console.log(`进度最大值: ${maxProgress}`);
}

```
```javascript
// 获取进度字段最大值
const progressField = sheet.getField('完成进度');
if (Base.isFieldOfType(progressField, 'progress')) {
  const maxProgress = progressField.getMax();
  Output.log(`进度最大值: ${maxProgress}`);
}

```

### setMax

设置进度字段的最大值。

```typescript
setMax: (val: number) => string

```

**参数**

*   `val`: `number` - 最大值
    

**返回**

*   `string` - 字段ID
    

**示例**

```typescript
// 设置进度字段最大值
const progressField = sheet.getField<ProgressField>('完成进度');
if (progressField) {
  progressField.setMax(100);
  console.log('已设置进度最大值为100');
}

```
```javascript
// 设置进度字段最大值
const progressField = sheet.getField('完成进度');
if (Base.isFieldOfType(progressField, 'progress')) {
  progressField.setMax(100);
  Output.log('已设置进度最大值为100');
}

```

### getFormatter

获取进度字段的格式。

```typescript
getFormatter: () => ProgressFormatter

```

**返回值**

*   [`ProgressFormatter`](../../interface/API%20类型定义.md) - 字段格式
    

**示例**

```typescript
// 获取进度字段格式
const progressField = sheet.getField<ProgressField>('完成进度');
if (progressField) {
  const formatter = progressField.getFormatter();
  console.log(`进度字段格式: ${formatter}`);
}

```
```javascript
// 获取进度字段格式
const progressField = sheet.getField('完成进度');
if (Base.isFieldOfType(progressField, 'progress')) {
  const formatter = progressField.getFormatter();
  Output.log(`进度字段格式: ${formatter}`);
}

```

### setFormatter

设置进度字段的格式。

```typescript
setFormatter: (val: ProgressFormatter) => string

```

**参数**

*   `val`:  [`ProgressFormatter`](../../interface/API%20类型定义.md)\- 进度字段格式
    

**返回值**

*   `string` - 字段ID
    

**示例**

```typescript
// 设置进度字段格式
const progressField = sheet.getField<ProgressField>('完成进度');
if (progressField) {
  const fieldId = progressField.setFormatter('percent'); // 假设'percent'是有效的格式类型
  console.log('进度字段格式已更新，字段ID:', fieldId);
}

```
```javascript
// 设置进度字段格式
const progressField = sheet.getField('完成进度');
if (Base.isFieldOfType(progressField, 'progress')) {
  const fieldId = progressField.setFormatter('percent'); // 假设'percent'是有效的格式类型
  Output.log('进度字段格式已更新，字段ID:', fieldId);
}

```