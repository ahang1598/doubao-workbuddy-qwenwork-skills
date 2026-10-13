# AttachmentField 附件字段

## 基本信息

AttachmentField 类型用于存储和管理各种文件附件，如图片、文档、音频、视频等。它提供了上传、获取和管理附件的功能，支持多种文件格式。

## 数据类型

### [IOpenFile](../../interface/API%20类型定义.md)

表示要上传的文件（如果传入 base64，建议文件大小在 10MB 以下）。

### [AttachmentValue](../../interface/API%20类型定义.md)

表示**单个**已上传的附件。一个附件字段的单元格值是 `AttachmentValue[]`。

## 字段特有方法

### getValueAsync

获取指定记录在该附件字段中的所有附件。

```typescript
getValueAsync: (recordId: string) => Promise<AttachmentValue[] | null>

```

**参数**

*   `recordId`: `string` - 记录ID
    

**返回值**

*   [`AttachmentValue`](../../interface/API%20类型定义.md) - 附件对象数组，每个附件包含url、filename、type、size等属性，如果记录不存在或无附件则返回null
    

**示例**

```typescript
// 获取附件字段值
const filesField = sheet.getField<AttachmentField>('附件');
if (filesField) {
  const attachments = await filesField.getValueAsync('rec123456');
  if (attachments && attachments.length > 0) {
    console.log(`共有 ${attachments.length} 个附件`);
    attachments.forEach(file => {
      console.log(`- ${file.filename} (${file.size} 字节, 类型: ${file.type})`);
    });
  } else {
    console.log('没有附件');
  }
}

```
```typescript
// 获取附件字段值
const filesField = sheet.getField('附件');
if (Base.isFieldOfType(filesField, 'attachment')) {
  const attachments = await filesField.getValueAsync('rec123456');
  if (attachments && attachments.length > 0) {
    Output.log(`共有 ${attachments.length} 个附件`);
    attachments.forEach(file => {
      Output.log(`- ${file.filename} (${file.size} 字节, 类型: ${file.type})`);
    });
  } else {
    Output.log('没有附件');
  }
}

```

### setValueAsync

上传并设置指定记录在该附件字段的值。

```typescript
setValueAsync: (
  recordId: string,
  attachment: IOpenFile | IOpenFile[] | AttachmentValue | AttachmentValue[]
) => Promise<boolean>

```

**参数**

*   `recordId`: `string` - 记录ID
    
*   `attachment`: [`IOpenFile | IOpenFile[]`](../../interface/API%20类型定义.md) | [`AttachmentValue | AttachmentValue[]`](../../interface/API%20类型定义.md)\- 单个文件对象或文件对象数组
    

**返回值**

*   `Promise<boolean>`\- 操作是否成功
    

**注意**

在边栏插件中，当需要在一个单元格内追加附件时，可以参考如下代码，上传附件的接口可以参考[《其他接口》](https://alidocs.dingtalk.com/i/nodes/1zknDm0WRz0NZeXQugKKDANoWBQEx5rG?utm_scene=team_space&iframeQuery=anchorId%3Duu_mdd3b880n5e7dhcb2yl)

```typescript
// service.tsx
// 在service层实现附件追加
function appendAttachments(sheetId: string, fieldId: string, recordId: string, appendFiles: AttachmentValue) {
  const sheet = DingdocsScript.base.getSheet(sheetId);
  const attachmentField = sheet.getField<AttachmentField>(fieldId);
  const files = await attachmentField.getValueAsync(recordId);

  // 调用 setValueAsync 时，要求数组中的所有文件变量的类型保持一致
  // 由于 getValueAsync 的返回结果是 AttachmentValue，所以此处appendFiles类型要需要是AttachmentValue类型
  await attachmentField.setValueAsync(recordId, [
    ...files,
    ...appendFiles,
  ])
}
DingdocsScript.registerScript('appendAttachments', appendAttachments);


// ui.tsx
// 在ui层调用host方法上传文件，方法名是 batchUploadFiles（不存在 uploadFiles）
const files: AttachmentValue[] = await Dingdocs.base.batchUploadFiles([File]);
await Dingdocs.script.run('appendAttachments', files);
```

### getAttachmentUrls

获取指定记录在该附件字段中所有附件的URL列表。

```typescript
getAttachmentUrls: (recordId: string) => Promise<string[]>
```

**参数**

*   `recordId`: `string` - 记录ID
    

**返回值**

*   `Promise<string[]>`\- 附件URL数组
    

**示例**

```typescript
// 获取附件的URL列表
const filesField = sheet.getField<AttachmentField>('附件');
if (filesField) {
  const urls = await filesField.getAttachmentUrls('rec123456');
  console.log('附件URL列表:');
  urls.forEach((url, index) => {
    console.log(`${index + 1}. ${url}`);
  });
  
  // 在网页中显示图片附件
  if (urls.length > 0) {
    const imgContainer = document.getElementById('imageContainer');
    if (imgContainer) {
      urls.forEach(url => {
        const img = document.createElement('img');
        img.src = url;
        img.style.maxWidth = '200px';
        img.style.margin = '5px';
        imgContainer.appendChild(img);
      });
    }
  }
}

```
```typescript
// 获取附件的URL列表
const filesField = sheet.getField('附件');
if (Base.isFieldOfType(filesField, 'attachment')) {
  const urls = await filesField.getAttachmentUrls('rec123456');
  Output.log('附件URL列表:');
  urls.forEach((url, index) => {
    Output.log(`${index + 1}. ${url}`);
  });
}

```

### getAttachmentDetails

获取指定记录在该附件字段中所有附件的详细信息（下载 URL、类型、文件名）。

```typescript
getAttachmentDetails: (recordId: string) => Promise<Array<{ filename: string; type: string; url: string }>>

```

**参数**

*   `recordId`: `string` - 记录ID
    

**返回值**

*   `Promise<Array<{ filename: string; type: string; url: string }>>`\- 附件详细信息列表