# GroupField 群组字段

`GroupField` 继承自基础 [`Field`](../Field%20模块.md)类，专门用于处理群组类型数据。

在读写群组字段前，请先了解钉钉群会话openConversationId概念：

:::
**openConversationId**

openConversationId用于唯一识别**群聊会话**，通过创建群接口返回值获取。

[https://open.dingtalk.com/document/development/im-session-overview: https://open.dingtalk.com/document/development/im-session-overview](https://open.dingtalk.com/document/development/im-session-overview)
:::

## 字段特有方法

### getValueAsync

获取指定记录在该群组字段中选择的群会话。

```typescript
getValueAsync: (recordId: string) => Promise<GroupCellValue[] | null>

```

**参数**

*   `recordId`: `string` - 记录ID
    

**返回值**

*   [`Promise<GroupCellValue[] | null>`](../../interface/API%20类型定义.md)\- 选中的群会话数组，返回群聊名称和openConversationId
    

**示例**

```typescript
// 获取记录的群组值
const groupField = sheet.getField<GroupField>('群组');
if (groupField) {
  const groups = await groupField.getValueAsync('rec123456');
  console.log('查询到群会话：', groups.map((group) => (`群名：${group.name}|群ID: ${group.openConversationId}`)).join('\n'));
}
```
```typescript
// 获取记录的群组值
const groupField = sheet.getField('群组');
if (Base.isFieldOfType(groupField, 'group')) {
  const users = await groupField.getValueAsync('rec123456');
  Output.log('查询到群会话：', groups.map((group) => (`群名：${group.name}|群ID: ${group.openConversationId}`)).join('\n'));
}
```

### setValueAsync

设置指定记录在该群组字段中的群会话值。

```typescript
setValueAsync: (recordId: string, value: GroupCellValue[]) => Promise<boolean>

```

**参数**

*   `recordId`: `string` - 记录ID
    
*   `value`: [`GroupCellValue[]`](../../interface/API%20类型定义.md) - 群会话值，支持传入openConversationId
    

**返回值**

*   `Promise<boolean>`\- 操作是否成功
    

**示例**

```typescript
// 设置记录的选项值
const groupField = sheet.getField<GroupField>('群组');
if (groupField) {
  const success = await groupField.setValueAsync('rec123456', [{
    openConversationId: 'cidxxxxx123',
  }, {
    openConversationId: 'cidxxxxx456',
  }]);
  if (success) {
    console.log('向记录中更新了两个群会话');
  } else {
    console.log('记录更新失败');
  }
}

```
```typescript
// 设置记录的选项值
const groupField = sheet.getField('群组');
if (Base.isFieldOfType(groupField, 'group')) {
  const success = await groupField.setValueAsync('rec123456', [{
    openConversationId: 'cidxxxxx123',
  }, {
    openConversationId: 'cidxxxxx456',
  }]);
  if (success) {
    Output.log('向记录中更新了两个群会话');
  } else {
    Output.log('记录更新失败');
  }
}

```