# RatingField 评分字段

`RatingField`，继承自基础 [Field](../Field%20模块.md) 类，专门用于处理评分字段数据。支持设置评分范围和评分图标，常用于评价、打分等场景。

## 字段特有方法

### getValueAsync

获取指定行记录该评分字段的值。

```typescript
getValueAsync: (recordId: string) => Promise<number | null>

```

**参数**

*   `recordId` : `string` - 记录ID
    

**返回值**

*   `Promise<number | null>` - 评分值，当字段值为空时返回null
    

**示例**

```typescript
// 获取评分字段值
const ratingField = sheet.getField<RatingField>('满意度评分');
if (ratingField) {
  const rating = await ratingField.getValueAsync('rec123456');
  console.log(`满意度评分: ${rating !== null ? rating : '未评分'}`);
}

```
```typescript
// 获取评分字段值
const ratingField = sheet.getField('满意度评分');
if (Base.isFieldOfType(ratingField, 'rating')) {
  const rating = await ratingField.getValueAsync('rec123456');
  Output.log(`满意度评分: ${rating !== null ? rating : '未评分'}`);
}

```

### setValueAsync

设置指定行记录该评分字段的值。

```typescript
setValueAsync: (recordId: string, val: number) => Promise<boolean>

```

**参数**

*   `recordId`: `string` - 记录ID
    
*   `val`: `number` - 评分值，必须为最小值到最大值之间的整数
    

**返回值**

*   `Promise<boolean>` - 设置是否成功
    

**示例**

```typescript
// 设置评分字段值
const ratingField = sheet.getField<RatingField>('满意度评分');
if (ratingField) {
  const success = await ratingField.setValueAsync('rec123456', 4);
  if (success) {
    console.log('评分更新成功');
  } else {
    console.log('评分更新失败');
  }
}

```
```typescript
// 设置评分字段值
const ratingField = sheet.getField('满意度评分');
if (Base.isFieldOfType(ratingField, 'rating')) {
  const success = await ratingField.setValueAsync('rec123456', 4);
  if (success) {
    Output.log('评分更新成功');
  } else {
    Output.log('评分更新失败');
  }
}

```

### getMin

获取评分字段的最小值。

```typescript
getMin: () => number

```

**返回值**

*   `number` - 最小值
    

**示例**

```typescript
// 获取评分字段最小值
const ratingField = sheet.getField<RatingField>('满意度评分');
if (ratingField) {
  const minRating = ratingField.getMin();
  console.log(`评分最小值: ${minRating}`);
}

```
```typescript
// 获取评分字段最小值
const ratingField = sheet.getField('满意度评分');
if (Base.isFieldOfType(ratingField, 'rating')) {
  const minRating = ratingField.getMin();
  Output.log(`评分最小值: ${minRating}`);
}

```

### getMax

获取评分字段的最大值。

```typescript
getMax: () => number

```

**返回值**

*   `number` - 最大值
    

**示例**

```typescript
// 获取评分字段最大值
const ratingField = sheet.getField<RatingField>('满意度评分');
if (ratingField) {
  const maxRating = ratingField.getMax();
  console.log(`评分最大值: ${maxRating}`);
}

```
```typescript
// 获取评分字段最大值
const ratingField = sheet.getField('满意度评分');
if (Base.isFieldOfType(ratingField, 'rating')) {
  const maxRating = ratingField.getMax();
  Output.log(`评分最大值: ${maxRating}`);
}

```

### setMin

设置评分字段的最小值。支持设置为0或1。

```typescript
setMin: (val: number) => string

```

**参数**

*   `val`: `number` - 最小值
    

**返回值**

*   `string` - 字段ID
    

**示例**

```typescript
// 设置评分字段最小值
const ratingField = sheet.getField<RatingField>('满意度评分');
if (ratingField) {
  ratingField.setMin(0);
  console.log('已设置评分最小值为0');
}

```
```typescript
// 设置评分字段最小值
const ratingField = sheet.getField('满意度评分');
if (Base.isFieldOfType(ratingField, 'rating')) {
  ratingField.setMin(0);
  Output.log('已设置评分最小值为0');
}

```

### setMax

设置评分字段的最大值。支持设置为2～10之间的整数。

```typescript
setMax: (val: number) => string

```

**参数**

*   `val`: `number` - 最大值
    

**返回**

*   `string` - 字段ID
    

**示例**

```typescript
// 设置评分字段最大值
const ratingField = sheet.getField<RatingField>('满意度评分');
if (ratingField) {
  ratingField.setMax(5);
  console.log('已设置评分最大值为5');
}

```
```typescript
// 设置评分字段最大值
const ratingField = sheet.getField('满意度评分');
if (Base.isFieldOfType(ratingField, 'rating')) {
  ratingField.setMax(5);
  Output.log('已设置评分最大值为5');
}

```

### getIcon

获取评分字段的图标类型。

```typescript
getIcon: () => RatingIconType

```

**返回值**

*   [`RatingIconType`](../../interface/API%20类型定义.md) - 图标类型
    

**示例**

```typescript
// 获取评分字段图标类型
const ratingField = sheet.getField<RatingField>('满意度评分');
if (ratingField) {
  const iconType = ratingField.getIcon();
  console.log(`评分图标类型: ${iconType}`);
}

```
```typescript
// 获取评分字段图标类型
const ratingField = sheet.getField('满意度评分');
if (Base.isFieldOfType(ratingField, 'rating')) {
  const iconType = ratingField.getIcon();
  Output.log(`评分图标类型: ${iconType}`);
}

```

### setIcon

设置评分字段的图标类型。

```typescript
setIcon: (icon: RatingIconType) => string

```

**参数**

*   `icon`: [`RatingIconType`](../../interface/API%20类型定义.md) - 图标类型
    

**返回值**

*   `string` - 字段ID
    

**示例**

```typescript
// 设置评分字段图标类型
const ratingField = sheet.getField<RatingField>('满意度评分');
if (ratingField) {
  const fieldId = ratingField.setIcon('star');
  console.log(`已设置评分图标为星形，字段ID: ${fieldId}`);
}

```
```typescript
// 设置评分字段图标类型
const ratingField = sheet.getField('满意度评分');
if (Base.isFieldOfType(ratingField, 'rating')) {
  const fieldId = ratingField.setIcon('star');
  Output.log(`已设置评分图标为星形，字段ID: ${fieldId}`);
}

```