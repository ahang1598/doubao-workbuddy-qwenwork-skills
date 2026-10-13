# TelephoneField 电话字段

`PhoneField`，继承自基础 [Field](../Field%20模块.md) 类，专门用于处理电话字段数据。用于存储和管理电话号码信息。

## 字段特有方法

### getValueAsync

获取指定行记录该电话字段的值。

```typescript
getValueAsync: (recordId: string) => Promise<string | null>

```

**参数**

*   `recordId` : `string` - 记录ID
    

**返回值**

*   `Promise<string | null>` - 电话号码值，当字段值为空时返回null
    

**示例**

```typescript
// 获取电话字段值
const phoneField = sheet.getField<PhoneField>('联系电话');
if (phoneField) {
  const phone = await phoneField.getValueAsync('rec123456');
  console.log(`联系电话: ${phone ? phone : '未填写'}`);
}

```
```typescript
// 获取电话字段值
const phoneField = sheet.getField('联系电话');
if (Base.isFieldOfType(phoneField, 'telephone')) {
  const phone = await phoneField.getValueAsync('rec123456');
  Output.log(`联系电话: ${phone ? phone : '未填写'}`);
}

```

### setValueAsync

设置指定行记录该电话字段的值。

```typescript
setValueAsync: (recordId: string, val: string) => Promise<boolean>

```

**参数**

*   `recordId`: `string` - 记录ID
    
*   `val`: `string` - 电话号码值
    

**返回值**

*   `Promise<boolean>` - 设置是否成功
    

**重要提示**

调用该API时，请确保电话号码为合法号码，否则更新数据将失败。

**示例**

```typescript
// 设置电话字段值
const phoneField = sheet.getField<PhoneField>('联系电话');
if (phoneField) {
  const success = await phoneField.setValueAsync('rec123456', '13800138000');
  if (success) {
    console.log('电话号码更新成功');
  } else {
    console.log('电话号码更新失败');
  }
}

```
```typescript
// 设置电话字段值
const phoneField = sheet.getField('联系电话');
if (Base.isFieldOfType(phoneField, 'telephone')) {
  const success = await phoneField.setValueAsync('rec123456', '13800138000');
  if (success) {
    Output.log('电话号码更新成功');
  } else {
    Output.log('电话号码更新失败');
  }
}

```