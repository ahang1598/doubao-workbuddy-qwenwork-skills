# LookupField 关联引用字段

LookupField 继承自基础 [Field](../Field%20模块.md)类，可以快捷地提供跨表的数据引用，并可以对数据按照你的需要进行后续的计算。

:::
关联引用字段通过字段配置**自动计算**引用结果，不能手动写入单元格值。
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

*   [`Promise<FormulaValue | null>`](../../interface/API%20类型定义.md) -  查找到的关联字段值，可能是单个值或数组，如果没有关联数据则返回null
    

**示例**

```typescript
// 获取记录的查找字段值
const lookupField = sheet.getField<LookupField>('客户名称');
if (lookupField) {
  const customerName = await lookupField.getValueAsync('rec_order_456');
  if (customerName !== null) {
    console.log(`关联的客户名称: ${customerName}`);
    
    // 如果查找字段返回多个值（多对多关联）
    if (Array.isArray(customerName)) {
      console.log(`找到${customerName.length}个关联客户`);
      customerName.forEach((name, index) => {
        console.log(`客户${index + 1}: ${name}`);
      });
    }
  } else {
    console.log('未找到关联的客户信息');
  }
}
```
```typescript
// 获取记录的查找字段值
const lookupField = sheet.getField('客户名称');
if (Base.isFieldOfType(lookupField, 'lookup')) {
  const customerName = await lookupField.getValueAsync('rec_order_456');
  if (customerName !== null) {
    Output.log(`关联的客户名称: ${customerName}`);
    
    // 如果查找字段返回多个值（多对多关联）
    if (Array.isArray(customerName)) {
      Output.log(`找到${customerName.length}个关联客户`);
      customerName.forEach((name, index) => {
        Output.log(`客户${index + 1}: ${name}`);
      });
    }
  } else {
    Output.log('未找到关联的客户信息');
  }
}
```