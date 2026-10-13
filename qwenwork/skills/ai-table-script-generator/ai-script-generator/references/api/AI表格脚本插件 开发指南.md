# AI表格脚本插件 开发指南

# 简介

脚本插件是AI表格提供的一种开放能力，开发者可以通过编写JS脚本的方式构建自定义脚本插件，并分享给表格协作者共同使用。

脚本插件可以与表格数据进行交互，实现复杂的业务逻辑。和[AI表格边栏插件](https://alidocs.dingtalk.com/i/nodes/R4GpnMqJzOP0oLp6sXPBmZxx8Ke0xjE3)相比，开发者开发脚本时无需进行页面开发和部署，在AI表格的右侧边栏中即可实现脚本编辑、运行和发布，使用内置API构建简易插件交互面板。

![script.gif](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/oJGq75kP0pY1AlAK/img/5fc9e494-8ba1-4b5b-b9c3-c47893fdb90f.gif)

# 开发与发布

## 调试脚本

### 打开脚本编辑器

点击`插件`展示插件面板，在右下角选择`脚本插件`，进入脚本插件列表。

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/oJGq75kP0pY1AlAK/img/3c20a16e-e29b-43da-891f-b160be1f0c38.png)

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/oJGq75kP0pY1AlAK/img/a083f020-2d91-4898-baaf-d6439fa1693d.png)

点击`添加脚本插件`创建新脚本。

### 编辑脚本内容

在脚本编辑区可编辑脚本内容。

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/oJGq75kP0pY1AlAK/img/7d730f95-7552-4bed-b5c5-c254adaca6c8.png)

可通过点击编辑区上方的工具栏`全屏`展开编辑。

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/oJGq75kP0pY1AlAK/img/43805b8a-639b-4040-8448-f7ab27673dff.png)

### 运行脚本

点击`运行插件`进行功能调试。

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/oJGq75kP0pY1AlAK/img/accd8101-5bd9-441d-a1f3-5463eec49910.png)![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/oJGq75kP0pY1AlAK/img/b0ca0706-dac9-4aa8-9f09-69f6a95da220.png)

## 发布脚本插件

点击插件资料下方的`发布到此表格`按钮，脚本作者可将此插件发布到插件首页，其他打开此表格的编辑者也可以看到并使用插件。

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/oJGq75kP0pY1AlAK/img/484586b4-6eaa-4b1c-8da0-fb5b3607928d.png?x-oss-process=image/crop,x_0,y_0,w_716,h_554/ignore-error,1)

配置插件资料，点击`发布`，返回插件首页即可查看脚本插件。

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/oJGq75kP0pY1AlAK/img/d3bbc13b-7792-43cc-9199-443b2890265d.png)

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/oJGq75kP0pY1AlAK/img/025a8ef3-4bb8-48b9-95c7-4e4a12219346.png)

## 基于已有插件进行业务扩展

在`插件中心`\-`脚本插件`中提供了一些官方脚本。

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/oJGq75kP0pY1AlAK/img/7bc3d27b-e850-467c-b05b-d59020eda93b.png)

点击使用后，可在插件已用列表中点击`创建副本`，副本插件将作为个人创建的脚本插件并支持二次编辑。

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/oJGq75kP0pY1AlAK/img/d38b0711-74b9-451e-b125-990e99552006.png)

# 内置API

## 基本语法

脚本插件使用JavaScript语法进行编写，开发者在代码编辑器中编辑的代码片段可视作在一个异步函数的局部作用域中执行。因此当调用异步API时，可以在编辑区的最外层使用`await`表达式。例如：

```javascript
// 无需定义async方法，可直接使用await
const userInput = await Input.textAsync('请输入一段文本');
Output.info('用户输入的文本为': userInput);
```

## AI表格数据模型

脚本插件中提供了一个全局变量`Base`代表AI表格的数据模型。当需要通过脚本执行AI表格的增删改查操作时，可以通过调用Base对象上的各种 API进行操作。

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/oJGq75kP0pY1AlAK/img/b20af145-0d26-42cd-bea4-7c9821f17843.png)

### 常用对象

AI表格的数据对象有以下几类：

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/vBPlN5m0zy8wkOdG/img/d16de762-8859-4314-9378-6ff83bafca59.png)

| **变量** | **含义** | **描述** |
| --- | --- | --- |
| [Base](../../../shared/references/api/modules/Base%20模块.md) | AI表格 | 可包含多个数据表，为整个AI表格的顶级对象。在脚本插件中，直接通过访问Base变量获取。 |
| [Sheet](../../../shared/references/api/modules/Sheet%20模块.md) | 数据表 | 包含多个视图、字段、记录。可通过Base API获取到具体某个Sheet对象。 |
| [View](../../../shared/references/api/modules/View%20模块.md) | 视图 | 可通过Sheet API 获取到某个数据表的具体某个View对象。 |
| [Field](../../../shared/references/api/modules/Field%20模块.md) | 字段 | 可通过Sheet API 获取到某个数据表的具体某个Field对象。 每种字段类型定义在 [各种 Field API](../../../shared/references/api/modules/Field%20api/) |
| [Record](../../../shared/references/api/modules/Record%20模块.md) | 记录 | 可通过Sheet API 获取到某个数据表的具体某个Record对象。 |

## Input API

脚本插件中提供了一个全局变量`Input`支持在运行页面中创建交互式UI，等待用户输入后执行后续步骤。每个交互式输入法都是异步的，因此调用此API时需要使用`await`表达式。

Input模块的API具体使用说明参见：[《Input模块》](../../../shared/references/api/modules/Input模块.md)

## Output API

脚本插件中提供了一个全局变量`Output`支持在运行页面中展示丰富的数据信息。

Output模块的API具体使用说明参见：[《Output模块》](../../../shared/references/api/modules/Output模块.md)

# 常见问题

*   **脚本中是否可以调用外部接口数据？**
    

:::
可以的，脚本插件中支持调用`fetch` API进行数据读写，前提需要开发者确保外部接口支持跨域访问。

```javascript
async function fetchImageAsOpenFile(url) {
  const res = await fetch(url);
  const ab = await res.arrayBuffer();
  return {
    name: 'image',
    type: res.headers.get('content-type') || 'image/',
    size: ab.byteLength,
    content: abToBase64(ab)
  };
}
function abToBase64(ab) {
  const bytes = new Uint8Array(ab);
  let binary = '';
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunk));
  }
  return btoa(binary);
}
```
:::