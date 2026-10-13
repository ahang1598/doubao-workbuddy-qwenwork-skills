# RichTextField 富文本字段

`RichTextField`，继承自基础 [Field](../Field%20模块.md) 类，专门用于处理富文本字段数据。支持文本格式化、链接、列表等富文本内容。

## 字段特有方法

### getValueAsync

获取指定行记录该富文本字段的值。

```typescript
getValueAsync: (recordId: string) => Promise<RichTextValue | null>

```

**参数**

*   `recordId` : `string` - 记录ID
    

**返回值**

*   [`Promise<RichTextValue | null>`](../../interface/API%20类型定义.md) - 富文本值，包含markdown格式的富文本，当字段值为空时返回null
    

**示例**

```typescript
// 获取富文本字段值
const richTextField = sheet.getField<RichTextField>('详细描述');
if (richTextField) {
  const richText = await richTextField.getValueAsync('rec123456');
  console.log(`详细描述: ${richText ? richText : '未填写'}`);
}

```
```typescript
// 获取富文本字段值
const richTextField = sheet.getField('详细描述');
if (Base.isFieldOfType(richTextField, 'richText')) {
  const richText = await richTextField.getValueAsync('rec123456');
  Output.log(`详细描述: ${richText ? richText : '未填写'}`);
}

```