# BarcodeField 条码字段

`BarcodeField`，继承自基础 [Field](../Field%20模块.md) 类，专门用于处理条码字段数据。用于存储和管理条码信息，常用于商品管理、库存跟踪等场景。

## 字段特有方法

### getValueAsync

获取指定行记录该条码字段的值。

```typescript
getValueAsync: (recordId: string) => Promise<string | null>

```

**参数**

*   `recordId` : `string` - 记录ID
    

**返回值**

*   `Promise<string | null>` - 条码值，当字段值为空时返回null
    

**示例**

```typescript
// 获取条码字段值
const barcodeField = sheet.getField<BarcodeField>('商品条码');
if (barcodeField) {
  const barcode = await barcodeField.getValueAsync('rec123456');
  console.log(`商品条码: ${barcode || '未填写'}`);
}

```
```typescript
// 获取条码字段值
const barcodeField = sheet.getField('商品条码');
if (Base.isFieldOfType(barcodeField, 'barcode')) {
  const barcode = await barcodeField.getValueAsync('rec123456');
  Output.log(`商品条码: ${barcode || '未填写'}`);
}

```

### setValueAsync

设置指定行记录该条码字段的值。

```typescript
setValueAsync: (recordId: string, text: string) => Promise<boolean>

```

**参数**

*   `recordId`: `string` - 记录ID
    
*   `text`: `string` - 条码值
    

**返回值**

*   `Promise<boolean>` - 设置是否成功
    

**示例**

```typescript
// 设置条码字段值
const barcodeField = sheet.getField<BarcodeField>('商品条码');
if (barcodeField) {
  const success = await barcodeField.setValueAsync('rec123456', '6901234567890');
  if (success) {
    console.log('条码更新成功');
  } else {
    console.log('条码更新失败');
  }
}

```
```typescript
// 设置条码字段值
const barcodeField = sheet.getField('商品条码');
if (Base.isFieldOfType(barcodeField, 'barcode')) {
  const success = await barcodeField.setValueAsync('rec123456', '6901234567890');
  if (success) {
    Output.log('条码更新成功');
  } else {
    Output.log('条码更新失败');
  }
}

```