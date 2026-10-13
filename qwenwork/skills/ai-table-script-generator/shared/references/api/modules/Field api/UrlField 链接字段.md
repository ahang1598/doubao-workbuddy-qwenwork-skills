# UrlField 链接字段

UrlField 继承自基础 [Field](../Field%20模块.md) 类，用于存储和管理URL链接，可以包含显示文本和实际链接地址。它适合用于存储网站链接、资源地址等需要跳转的信息。

## 字段特有方法

### getValueAsync

获取指定记录在该URL字段的值。

```typescript
getValueAsync: (recordId: string) => Promise<LinkValue | null>

```

**参数**

*   `recordId`: `string` - 记录ID
    

**返回值**

*   [`Promise<LinkValue | null>`](../../interface/API%20类型定义.md) - URL对象，包含text（显示文本）和link（链接地址）属性，如果记录不存在或值为空则返回null
    

**示例**

```typescript
// 获取URL字段值
const websiteField = sheet.getField<UrlField>('网站');
if (websiteField) {
  const url = await websiteField.getValueAsync('rec123456');
  if (url) {
    console.log(`链接地址: ${url.link}`);
    if (url.text) {
      console.log(`显示文本: ${url.text}`);
    }
  } else {
    console.log('未设置网站链接');
  }
}

```
```typescript
// 获取URL字段值
const websiteField = sheet.getField('网站');
if (Base.isFieldOfType(websiteField, 'url')) {
  const url = await websiteField.getValueAsync('rec123456');
  if (url) {
    Output.log(`链接地址: ${url.link}`);
    if (url.text) {
      Output.log(`显示文本: ${url.text}`);
    }
  } else {
    Output.log('未设置网站链接');
  }
}

```

### setValueAsync

设置指定记录在该URL字段的值。

```typescript
setValueAsync: (recordId: string, url: LinkValue | string) => Promise<boolean>
```

**参数**

*   `recordId`: `string` - 记录ID
    
*   `url`: [`LinkValue | string`](../../interface/API%20类型定义.md) - URL值，可以是字符串（直接作为链接地址）或包含link和可选text属性的对象
    

**返回值**

*   `Promise<boolean>`\- 操作是否成功
    

**示例**

```typescript
// 使用字符串设置URL字段值
const websiteField = sheet.getField<UrlField>('网站');
if (websiteField) {
  // 方式1：直接设置链接地址
  const success1 = await websiteField.setValueAsync('rec123456', 'https://www.example.com');
  
  // 方式2：设置带显示文本的链接
  const success2 = await websiteField.setValueAsync('rec234567', {
    link: 'https://www.example.org',
    text: '示例网站'
  });
}

```
```typescript
// 使用字符串设置URL字段值
const websiteField = sheet.getField('网站');
if (Base.isFieldOfType(websiteField, 'url')) {
  // 方式1：直接设置链接地址
  const success1 = await websiteField.setValueAsync('rec123456', 'https://www.example.com');
  
  // 方式2：设置带显示文本的链接
  const success2 = await websiteField.setValueAsync('rec234567', {
    link: 'https://www.example.org',
    text: '示例网站'
  });
}

```

## 使用示例

```typescript
// 完整的URL字段使用示例
async function manageWebsiteLinks() {
  const sheet = base.getSheet('合作伙伴');
  const websiteField = sheet.getField<UrlField>('官网链接');
  
  if (websiteField && websiteField.getType() === 'url') {
    // 获取所有记录
    const partners = await sheet.getRecordsAsync({ pageSize: 50 });
    
    // 统计有效的网站链接
    let validLinksCount = 0;
    let missingLinksCount = 0;
    
    for (const partner of partners.records) {
      const website = await websiteField.getValueAsync(partner.getId());
      
      if (website && website.link) {
        validLinksCount++;
        console.log(`${partner.getCellValue('公司名称')}: ${website.text || website.link}`);
      } else {
        missingLinksCount++;
        
        // 为没有网站的合作伙伴自动添加一个搜索链接
        const companyName = partner.getCellValue('公司名称');
        if (companyName) {
          const searchUrl = `https://www.google.com/search?q=${encodeURIComponent(companyName)}`;
          await websiteField.setValueAsync(partner.getId(), {
            link: searchUrl,
            text: `搜索 ${companyName}`
          });
          console.log(`为 ${companyName} 添加了搜索链接`);
        }
      }
    }
    
    console.log(`统计结果: ${validLinksCount} 个有效链接, ${missingLinksCount} 个缺失链接`);
    
    // 更新特定记录的链接
    const importantPartnerId = 'rec123456';
    await websiteField.setValueAsync(importantPartnerId, {
      link: 'https://www.important-partner.com',
      text: '重要合作伙伴官网'
    });
  }
}

```