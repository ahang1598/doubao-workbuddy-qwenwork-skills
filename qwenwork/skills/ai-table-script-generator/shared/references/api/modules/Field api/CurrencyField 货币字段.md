# CurrencyField 货币字段

## 基本信息

CurrencyField 类型专门处理货币值，支持不同货币类型（如人民币、美元、欧元等）和不同精度的小数位数。它提供了专门的货币格式化和显示功能，使货币数据在表格中更直观。

## 字段特有方法

### getValueAsync

获取指定记录在该货币字段的值。

```typescript
getValueAsync: (recordId: string) => Promise<number | null>
```

**参数**

*   `recordId`: `string` - 记录ID
    

**返回值**

*   `Promise<number | null>`\- 货币值（数值），如果记录不存在或值为空则返回null
    

**示例**

```typescript
// 获取货币字段值
const priceField = sheet.getField<CurrencyField>('价格');
if (priceField) {
  const price = await priceField.getValueAsync('rec123456');
  if (price !== null) {
    console.log(`价格: ${price}`);
  } else {
    console.log('未设置价格');
  }
}

```
```typescript
// 获取货币字段值
const priceField = sheet.getField('价格');
if (Base.isFieldOfType(priceField, 'currency')) {
  const price = await priceField.getValueAsync('rec123456');
  if (price !== null) {
    Output.log(`价格: ${price}`);
  } else {
    Output.log('未设置价格');
  }
}

```

### setValueAsync

设置指定记录在该货币字段的值。

```typescript
setValueAsync: (recordId: string, num: number | string) => Promise<boolean>

```

**参数**

*   `recordId`: `string` - 记录ID
    
*   `num`: `number | string` - 要设置的货币值，可以是数字或可转换为数字的字符串
    

**返回值**

*   `Promise<boolean>` - 操作是否成功
    

**示例**

```typescript
// 设置货币字段值
const priceField = sheet.getField<CurrencyField>('价格');
if (priceField) {
  // 使用数字设置价格
  const success1 = await priceField.setValueAsync('rec123456', 299.99);
  
  // 使用字符串设置价格
  const success2 = await priceField.setValueAsync('rec234567', '599.50');
  
  console.log('价格设置成功');
}

```
```typescript
// 设置货币字段值
const priceField = sheet.getField('价格');
if (Base.isFieldOfType(priceField, 'currency')) {
  // 使用数字设置价格
  const success1 = await priceField.setValueAsync('rec123456', 299.99);
  
  // 使用字符串设置价格
  const success2 = await priceField.setValueAsync('rec234567', '599.50');
  
  Output.log('价格设置成功');
}

```

### getDecimalDigits

获取货币字段的小数位数。

```typescript
getDecimalDigits: () => number

```

**返回值**

*   `number` - 小数位数，范围为0-4
    

**示例**

```typescript
// 获取货币字段的小数位数
const priceField = sheet.getField<CurrencyField>('价格');
if (priceField) {
  const decimalDigits = priceField.getDecimalDigits();
  console.log(`价格字段的小数位数: ${decimalDigits}`);
}

```
```typescript
// 获取货币字段的小数位数
const priceField = sheet.getField('价格');
if (Base.isFieldOfType(priceField, 'currency')) {
  const decimalDigits = priceField.getDecimalDigits();
  console.log(`价格字段的小数位数: ${decimalDigits}`);
}

```

### setDecimalDigits

设置货币字段的小数位数。

```typescript
setDecimalDigits: (decimalDigits: number) => string

```

**参数**

*   `decimalDigits`: `number` - 小数位数，必须是0-4之间的整数
    

**返回值**

*   `string` - 字段ID
    

**示例**

```typescript
// 设置货币字段的小数位数
const priceField = sheet.getField<CurrencyField>('价格');
if (priceField) {
  // 设置为2位小数
  priceField.setDecimalDigits(2);
  console.log('价格字段已设置为显示2位小数');
}

```
```typescript
// 设置货币字段的小数位数
const priceField = sheet.getField('价格');
if (Base.isFieldOfType(priceField, 'currency')) {
  // 设置为2位小数
  priceField.setDecimalDigits(2);
  Output.log('价格字段已设置为显示2位小数');
}

```

### getCurrencyType

获取货币字段的货币类型。

```typescript
getCurrencyType: () => CurrencyType

```

**返回值**

*   [`CurrencyType`](../../interface/API%20类型定义.md) - 货币类型，如'CNY'（人民币）、'USD'（美元）等
    

**示例**

```typescript
// 获取货币字段的货币类型
const priceField = sheet.getField<CurrencyField>('价格');
if (priceField) {
  const currencyType = priceField.getCurrencyType();
  console.log(`价格字段的货币类型: ${currencyType}`);
}

```
```typescript
// 获取货币字段的货币类型
const priceField = sheet.getField('价格');
if (Base.isFieldOfType(priceField, 'currency')) {
  const currencyType = priceField.getCurrencyType();
  Output.log(`价格字段的货币类型: ${currencyType}`);
}

```

### setCurrencyType

设置货币字段的货币类型。

```typescript
setCurrencyType: (currencyType: CurrencyType) => string

```

**参数**

*   `currencyType`: [`CurrencyType`](../../interface/API%20类型定义.md) - 货币类型，必须是系统支持的货币类型之一
    

**返回值**

*   `string` - 字段ID
    

**示例**

```typescript
// 设置货币字段的货币类型
const priceField = sheet.getField<CurrencyField>('价格');
if (priceField) {
  // 设置为人民币
  priceField.setCurrencyType('CNY');
  console.log('价格字段已设置为人民币');
}

```
```typescript
// 设置货币字段的货币类型
const priceField = sheet.getField('价格');
if (Base.isFieldOfType(priceField, 'currency')) {
  // 设置为人民币
  priceField.setCurrencyType('CNY');
  Output.log('价格字段已设置为人民币');
}

```