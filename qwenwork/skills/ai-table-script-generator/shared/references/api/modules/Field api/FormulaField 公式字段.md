# FormulaField 公式字段

FormulaField 继承自基础 [Field](../Field%20模块.md)类，专门用于处理公式计算类型数据。

:::
公式字段通过预定义的公式表达式**自动计算**并显示结果，不能手动写入单元格值。
:::

## 字段特有方法

### getValueAsync

获取指定记录在该公式字段中的计算结果值。

```typescript
getValueAsync: (recordId: string) => Promise<FormulaValue | null>

```

**参数**

*   `recordId`: `string` - 记录ID
    

**返回值**

*   [`Promise<FormulaValue | null>`](../../interface/API%20类型定义.md) - 公式计算结果，可能是单个值或数组，如果计算失败或记录不存在则返回null
    

**示例**

```typescript
// 获取记录的公式计算结果
const formulaField = sheet.getField<FormulaField>('总金额');
if (formulaField) {
  const result = await formulaField.getValueAsync('rec_order_123');
  if (result !== null) {
    console.log(`订单总金额: ${result}`);
    
    // 如果公式返回数组结果
    if (Array.isArray(result)) {
      console.log(`计算结果包含${result.length}个值`);
      result.forEach((value, index) => {
        console.log(`结果${index + 1}: ${value}`);
      });
    }
  } else {
    console.log('公式计算失败或记录不存在');
  }
}
```
```typescript
// 获取记录的公式计算结果
const formulaField = sheet.getField('总金额');
if (Base.isFieldOfType(formulaField, 'formula')) {
  const result = await formulaField.getValueAsync('rec_order_123');
  if (result !== null) {
    Output.log(`订单总金额: ${result}`);
    
    // 如果公式返回数组结果
    if (Array.isArray(result)) {
      Output.log(`计算结果包含${result.length}个值`);
      result.forEach((value, index) => {
        Output.log(`结果${index + 1}: ${value}`);
      });
    }
  } else {
    Output.log('公式计算失败或记录不存在');
  }
}
```

### setFormula

设置公式表达式，详情参考[公式字段基础介绍](https://wolai.dingtalk.com/k1gwYpHxHkj2QVBWSoKrTX)

```typescript
setFormula: (formula: string) => string;

```

**参数**

*   `formula`: `string` - 公式表达时
    

**返回值**

*   `string` - 字段 ID
    

**示例**

```typescript
// 获取记录的公式计算结果
const formulaField = sheet.getField<FormulaField>('总金额');
if (formulaField) {
  formulaField.setFormula("[单价]*[数量]");
  formulaField.setFormula("[单价]*20");
}
```
```typescript
// 获取记录的公式计算结果
const formulaField = sheet.getField('总金额');
if (Base.isFieldOfType(formulaField, 'formula')) {
  formulaField.setFormula("[单价]*[数量]");
  formulaField.setFormula("[单价]*20");
}
```