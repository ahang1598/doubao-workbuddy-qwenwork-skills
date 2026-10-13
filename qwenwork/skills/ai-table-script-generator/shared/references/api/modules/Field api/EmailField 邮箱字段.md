# EmailField 邮箱字段

`EmailField`，继承自基础 [Field](../Field%20模块.md) 类，专门用于处理邮箱字段数据。用于存储和验证邮箱地址信息。

## 字段特有方法

### getValueAsync

获取指定行记录该邮箱字段的值。

```typescript
getValueAsync: (recordId: string) => Promise<string | null>

```

**参数**

*   `recordId` : `string` - 记录ID
    

**返回值**

*   `Promise<string | null>` - 邮箱地址值，当字段值为空时返回null
    

**示例**

```typescript
// 获取邮箱字段值
const emailField = sheet.getField<EmailField>('联系邮箱');
if (emailField) {
  const email = await emailField.getValueAsync('rec123456');
  console.log(`联系邮箱: ${email || '未填写'}`);
}

```
```typescript
// 获取邮箱字段值
const emailField = sheet.getField('联系邮箱');
if (Base.isFieldOfType(emailField, 'email')) {
  const email = await emailField.getValueAsync('rec123456');
  Output.log(`联系邮箱: ${email || '未填写'}`);
}

```

### setValueAsync

设置指定行记录该邮箱字段的值。

```typescript
setValueAsync: (recordId: string, text: string) => Promise<boolean>

```

**参数**

*   `recordId`: `string` - 记录ID
    
*   `text`: `string` - 邮箱地址值
    

**返回值**

*   `Promise<boolean>` - 设置是否成功
    

**重要提示**

调用该API时，请确保邮箱地址为合法邮箱，否则更新数据将失败。

**示例**

```typescript
// 设置邮箱字段值
const emailField = sheet.getField<EmailField>('联系邮箱');
if (emailField) {
  const success = await emailField.setValueAsync('rec123456', 'example@company.com');
  if (success) {
    console.log('邮箱更新成功');
  } else {
    console.log('邮箱更新失败');
  }
}

```
```typescript
// 设置邮箱字段值
const emailField = sheet.getField('联系邮箱');
if (Base.isFieldOfType(emailField, 'email')) {
  const success = await emailField.setValueAsync('rec123456', 'example@company.com');
  if (success) {
    console.log('邮箱更新成功');
  } else {
    console.log('邮箱更新失败');
  }
}

```