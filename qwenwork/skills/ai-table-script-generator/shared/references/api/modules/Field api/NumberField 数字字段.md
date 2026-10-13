# NumberField 数字字段

`NumberField`，继承自基础 [Field](../Field%20模块.md) 类，专门用于处理数字字段数据。支持整数、小数，并提供多种数字格式化选项，如百分比、货币等。

## 字段特有方法

### getValueAsync

获取指定记录在该文本字段的值。

```typescript
getValueAsync: (recordId: string) => Promise<number | null>
```

**参数**

*   `recordId` : `string` - 记录ID
    

**返回值**

*   `Promise<string | null>`\- 数字值，如果记录不存在或值为空则返回null
    

**示例**

```typescript
// 获取数字字段值
const priceField = sheet.getField<NumberField>('价格');
if (priceField) {
  const price = await priceField.getValueAsync('rec123456');
  console.log(`价格: ${price !== null ? price : '无'}`);
}
```
```typescript
// 获取数字字段值
const priceField = sheet.getField<NumberField>('价格');
if (Base.isFieldOfType(priceField, 'number')) {
  const price = await priceField.getValueAsync('rec123456');
  Output.log(`价格: ${price !== null ? price : '无'}`);
}
```

### setValueAsync

设置指定记录在该数字字段的值。

```typescript
setValueAsync: (recordId: string, num: number) => Promise<boolean>
```

**参数**

*   `recordId`: `string` - 记录ID
    
*   `num`: `string` - 要设置的数字值
    

**返回值**

*   `Promise<boolean>`\- 设置是否成功
    

**示例**

```typescript
// 设置数字字段值
const priceField = sheet.getField<NumberField>('价格');
if (priceField) {
  const success = await priceField.setValueAsync('rec123456', 199.99);
  if (success) {
    console.log('价格更新成功');
  } else {
    console.log('价格更新失败');
  }
}
```
```typescript
// 设置数字字段值
const priceField = sheet.getField<NumberField>('价格');
if (Base.isFieldOfType(priceField, 'number')) {
  const success = await priceField.setValueAsync('rec123456', 199.99);
  if (success) {
    Output.log('价格更新成功');
  } else {
    Output.log('价格更新失败');
  }
}
```

### getFormatter

获取数字字段的格式。

```typescript
getFormatter(): NumericalFormatter

```

**返回值**

*   [`NumericalFormatter`](../../interface/API%20类型定义.md) - 数字格式类型
    

**示例**

```typescript
// 获取数字格式
const priceField = sheet.getField<NumberField>('价格');
if (priceField) {
  const formatter = priceField.getFormatter();
}

```
```typescript
// 获取数字格式
const priceField = sheet.getField('价格');
if (Base.isFieldOfType(priceField, 'number')) {
  const formatter = priceField.getFormatter();
}

```

### setFormatter

设置数字字段的格式

```typescript
setFormatter: (formatter: NumericalFormatter) => string
```

**参数**

*   `formatter`: [`NumericalFormatter`](../../interface/API%20类型定义.md)\- 数字格式
    

**返回值**

*   `string` - 字段ID
    

**示例**

```typescript
// 设置数字格式为货币类型
const priceField = sheet.getField<NumberField>('价格');
if (priceField) {
  priceField.setFormatter('CNY_FLOAT');
  console.log('已将价格字段设置为人民币格式');
}

// 设置数字格式为百分比
const rateField = sheet.getField<NumberField>('完成率');
if (rateField) {
  rateField.setFormatter('PERCENT_FLOAT');
  console.log('已将完成率字段设置为百分比格式');
}

```
```typescript
// 设置数字格式为货币类型
const priceField = sheet.getField('价格');
if (Base.isFieldOfType(priceField, 'number')) {
  priceField.setFormatter('CNY_FLOAT');
  Output.log('已将价格字段设置为人民币格式');
}

// 设置数字格式为百分比
const rateField = sheet.getField('完成率');
if (Base.isFieldOfType(rateField, 'number')) {
  rateField.setFormatter('PERCENT_FLOAT');
  Output.log('已将完成率字段设置为百分比格式');
}

```