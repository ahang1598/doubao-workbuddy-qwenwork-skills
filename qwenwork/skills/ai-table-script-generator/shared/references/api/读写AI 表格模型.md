# 读写AI 表格模型

:::
当前API参考文档适用于AI 表格插件开发用户，针对**边栏插件**开发者和**脚本插件**开发者，我们提供了一套共用的AI表格对象模型。
:::

当需要对文档执行某个具体的操作时，应当首先获取到AI 表格的对象模型，然后调用对象上的具体方法。

**边栏插件**

调用DingdocsScript.base可访问AI 表格模型的顶级对象Base，代表当前打开的AI 表格。调用JSAPI读写AI 表格数据时，通常从Base开始。

**脚本插件**

脚本编辑器中提供了一个全局变量Base用于访问AI 表格模型的顶级对象Base。

### 常用对象

AI表格的数据对象有以下几类：

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/vBPlN5m0zy8wkOdG/img/d16de762-8859-4314-9378-6ff83bafca59.png)

| **变量** | **含义** | **描述** |
| --- | --- | --- |
| [Base](./modules/Base%20模块.md) | AI表格 | 可包含多个数据表，为整个AI表格的顶级对象。在脚本插件中，直接通过访问Base变量获取。 |
| [Sheet](./modules/Sheet%20模块.md) | 数据表 | 包含多个视图、字段、记录。可通过Base API获取到具体某个Sheet对象。 |
| [View](./modules/View%20模块.md) | 视图 | 可通过Sheet API 获取到某个数据表的具体某个View对象。 |
| [Field](./modules/Field%20模块.md) | 字段 | 可通过Sheet API 获取到某个数据表的具体某个Field对象。 |
| [Record](./modules/Record%20模块.md) | 记录 | 可通过Sheet API 获取到某个数据表的具体某个Record对象。 |