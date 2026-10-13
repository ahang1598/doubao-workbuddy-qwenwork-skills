# FilterUpField 查找引用字段

FilterUpField 继承自基础 [Field](../Field%20模块.md)类，使用该字段，无需输入公式以及和其他表进行关联，即可根据指定条件快速查找并引用数据，轻松满足筛选和统计数据的需求。

:::
查找引用字段通过字段配置**自动计算**引用结果，不能手动写入单元格值。
:::

## 字段特有方法

### getValueAsync

获取指定记录在该字段中的值。

```typescript
getValueAsync: (recordId: string) => Promise<FormulaValue | null>

```

**参数**

*   `recordId`: `string` - 记录ID
    

**返回值**

*   [`Promise<FormulaValue | null>`](../../interface/API%20类型定义.md) -  可能是单个值或数组，如果没有关联数据则返回null
    

**示例**

```typescript
// 获取记录的查找引用汇总结果
const filterUpField = sheet.getField<FilterUpField>('本月销售额');
if (filterUpField) {
  const monthlySales = await filterUpField.getValueAsync('rec_789');
  if (monthlySales !== null) {
    console.log(`本月销售额: ${monthlySales}`);
    
    // 如果汇总结果是数组（如多个汇总函数的结果）
    if (Array.isArray(monthlySales)) {
      console.log(`汇总结果包含${monthlySales.length}个值`);
      monthlySales.forEach((value, index) => {
        console.log(`汇总值${index + 1}: ${value}`);
      });
    }
  } else {
    console.log('筛选汇总计算失败或无匹配数据');
  }
}

```
```typescript
// 获取记录的查找引用汇总结果
const filterUpField = sheet.getField('本月销售额');
if (Base.isFieldOfType(filterUpField, 'filterUp')) {
  const monthlySales = await filterUpField.getValueAsync('rec_789');
  if (monthlySales !== null) {
    Output.log(`本月销售额: ${monthlySales}`);
    
    // 如果汇总结果是数组（如多个汇总函数的结果）
    if (Array.isArray(monthlySales)) {
      Output.log(`汇总结果包含${monthlySales.length}个值`);
      monthlySales.forEach((value, index) => {
        Output.log(`汇总值${index + 1}: ${value}`);
      });
    }
  } else {
    Output.log('筛选汇总计算失败或无匹配数据');
  }
}

```