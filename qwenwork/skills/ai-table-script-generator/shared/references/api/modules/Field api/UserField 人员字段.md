# UserField 人员字段

`UserField` 继承自基础 [`Field`](../Field%20模块.md)类，专门用于处理人员类型数据。

在读写人员字段前，请先了解钉钉用户unionId和userId概念：

:::
**UserId**

UserId是员工在其所属组织中的唯一标识，仅在所属组织内是唯一标识符。同一个用户在不同组织中可以拥有不同的UserId。

[https://open.dingtalk.com/document/development/query-the-list-of-department-userids: https://open.dingtalk.com/document/development/query-the-list-of-department-userids](https://open.dingtalk.com/document/development/query-the-list-of-department-userids)
:::
:::
**Unionid**

UnionId是员工在当前开发者企业范围内的唯一标识，由系统生成。

对于开发边栏插件的用户而言，uniondId为插件所属企业范围内的唯一标识，同一个员工在不同的组织的企业内/三方插件下，unionid是不相同的。在同一个开发者企业账号下，unionid是唯一且不变的。

对于开发脚本插件的用户而言，unionId始终返回文档所属企业下的唯一标识。

[https://open.dingtalk.com/document/development/query-a-user-by-the-union-id: https://open.dingtalk.com/document/development/query-a-user-by-the-union-id](https://open.dingtalk.com/document/development/query-a-user-by-the-union-id)
:::

## 字段特有方法

### getValueAsync

获取指定记录在该人员字段中选择的人员。

```typescript
getValueAsync: (recordId: string) => Promise<UserCellValue[] | null>

```

**参数**

*   `recordId`: `string` - 记录ID
    

**返回值**

*   [`Promise<UserCellValue[] | null>`](../../interface/API%20类型定义.md)\- 选中的人员，返回用户名和用户unionId
    

**示例**

```typescript
// 获取记录的人员值
const userField = sheet.getField<UserField>('人员');
if (userField) {
  const users = await userField.getValueAsync('rec123456');
  console.log('查询到用户：', users.map((user) => (`用户名：${user.name}|用户unionId: ${user.unionId}`)).join('\n'));
}
```
```typescript
const userField = sheet.getField('人员');
if (Base.isFieldOfType(userField, 'user')) {
  const users = await userField.getValueAsync('rec123456');
  Output.log('查询到用户：\n', users.map((user) => (`用户名：${user.name}|用户unionId: ${user.unionId}`)).join('\n'));
}
```

### setValueAsync

设置指定记录在该人员字段中的人员值。

```typescript
setValueAsync: (recordId: string, value: UserCellValue[]) => Promise<boolean>
```

**参数**

*   `recordId`: `string` - 记录ID
    
*   `value`: [`UserCellValue[]`](../../interface/API%20类型定义.md) - 人员值，支持传入用户的userId或unionId
    

**返回值**

*   `Promise<boolean>`\- 操作是否成功
    

**示例**

```typescript
// 设置记录的选项值
const userField = sheet.getField<UserField>('人员');
if (userField) {
  const success = await userField.setValueAsync('rec123456', [{
    userId: 'user123',
  }, {
    unionId: 'xxxxx',
  }]);
  if (success) {
    console.log('向记录中更新了两名人员');
  } else {
    console.log('记录更新失败');
  }
}

```
```typescript
// 设置记录的选项值
const userField = sheet.getField('人员');
if (Base.isFieldOfType(userField, 'user')) {
  const success = await userField.setValueAsync('rec123456', [{
    userId: 'user123',
  }, {
    unionId: 'xxxxx',
  }]);
  if (success) {
    Output.log('向记录中更新了两名人员');
  } else {
    Output.log('记录更新失败');
  }
}

```