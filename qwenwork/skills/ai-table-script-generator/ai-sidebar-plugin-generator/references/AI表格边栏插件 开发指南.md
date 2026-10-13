# AI表格边栏插件 开发指南

# 简介

边栏插件是AI表格提供的一种开放能力，开发者可以通过构建自定义插件来扩展AI表格的功能。

插件运行在AI表格的右侧边栏中，可以与表格数据进行交互，实现复杂的业务逻辑。

# 架构概述

边栏插件采用双页面架构：

*   **脚本服务页面（Script Service）**：运行在 Web Worker 中，负责与AI表格数据模型交互
    
*   **UI交互页面（Sidebar UI）**：运行在边栏 iframe 中，负责用户界面展示和交互
    

# AI表格数据模型

### 核心对象层次结构

```plaintext
Base (AI表格)
├── Sheet (数据表)
│   ├── View (视图)
│   ├── Field (字段)
│   └── Record (记录)

```

### 对象说明

| 对象 | 描述 | 获取方式 |
| --- | --- | --- |
| **Base** | AI表格顶级对象，包含多个数据表 | `DingdocsScript.base` |
| **Sheet** | 数据表对象，包含字段、记录、视图 | `base.getActiveSheet()` / `base.getSheet(id)` |
| **View** | 视图对象，表示数据表的不同展示方式 | `sheet.getViews()` |
| **Field** | 字段对象，定义数据表的列结构 | `sheet.getFields()` |
| **Record** | 记录对象，表示数据表中的一行数据 | `sheet.getRecordsAsync()` / `sheet.getRecordAsync(id)` |

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/vBPlN5m0zy8wkOdG/img/d16de762-8859-4314-9378-6ff83bafca59.png)

# 快速开始

### 环境准备

#### 1. 安装依赖

```bash
# 使用npm
npm install dingtalk-docs-cool-app@latest

# 使用yarn
yarn add dingtalk-docs-cool-app@latest

# 使用pnpm
pnpm install dingtalk-docs-cool-app@latest
```

#### 2. 项目模板

推荐使用官方模板快速开始：

[https://github.com/dingdocs-notable/addon-demo: https://github.com/dingdocs-notable/addon-demo](https://github.com/dingdocs-notable/addon-demo)

```bash
git clone https://github.com/dingdocs-notable/addon-demo.git
cd addon-demo
npm install
npm start
```

### 开发服务页面

1.  在src/scripts下新建`service.ts`，并配置以下内容
    
    ```typescript
    
    // 1.定义如何读写文档对象模型
    function getActiveSheetName() {
      const sheet = DingdocsScript.base.getActiveSheet();
      return sheet?.getName();
    }
    
    // 2.注册指令「getActiveSheetName」
    DingdocsScript.registerScript('getActiveSheetName', getActiveSheetName);
    ```
    
    此部分代码注册了一个文档脚本服务指令getActiveSheetName，通过这个指令可以获取到当前打开的数据表表名。
    
    将此文件单独打包到路径`{PUBLIC_URL}/static/js/script.code.js`。
    
2.  在src/entries下新建`script.tsx`，并配置以下内容
    
    ```typescript
    import React, { useEffect } from 'react';
    import ReactDOM from 'react-dom/client';
    
    import { initScript } from 'dingtalk-docs-cool-app';
    
    function App() {
      useEffect(() => {
        // 初始化文档模型服务
        initScript({
          scriptUrl: new URL(`${process.env.PUBLIC_URL}/static/js/script.code.js`, window.location.href),
          onError: (e) => {
            console.log(e);
          }
        });
      }, []);
      return null;
    }
    
    const root = ReactDOM.createRoot(document.getElementById('script')!);
    root.render(
      <React.StrictMode>
        <App/>
      </React.StrictMode>
    );
    ```
    
    此部分代码用于初始化文档脚本服务，获取开发者定义的所有脚本服务指令。
    
3.  在src/entries下新建`ui.tsx`，并配置以下内容
    
    ```typescript
    import React, { useEffect, useState } from 'react';
    import ReactDOM from 'react-dom/client';
    import { initView } from 'dingtalk-docs-cool-app';
    
    function App() {
      const [currentSheetName, setCurrentSheetName] = useState<string>('');
      useEffect(() => {
        initView({
          onReady: () => {
            console.log('init ui completed!');
          },
          onError: (e) => {
            console.log(e);
          },
        });
      }, []);
    
      const getCurrentSheetName = async () => {
        const name = await Dingdocs.script.run('getActiveSheetName');
        setCurrentSheetName(name);
      };
    
      return (
        <div>
          <h1>调试边栏插件</h1>
          <p>当前打开的数据表名称为{currentSheetName}</p>
          <button onClick={getCurrentSheetName}>点击刷新</button>
        </div>
      )
    }
    
    const root = ReactDOM.createRoot(document.getElementById('ui')!);
    root.render(
      <React.StrictMode>
        <App/>
      </React.StrictMode>
    );
    ```
    
    此部分代码用于初始化边栏交互页面，页面中包含一个按钮，点击按钮时，会向文档模型服务发送指令getActiveSheetName，获取当前打开的数据表表名。
    
4.  将script.tsx和ui.tsx分别打包为两个静态页面，分别作为插件的脚本服务地址和交互页面地址。
    

## 插件调试

跟随上方的示例，搭建一个边栏插件后

*   新建或打开任意AI表格，点击 `插件` 展开插件面板
    
*   打开`插件市场` 点击 `自定义插件`，点击 `+新增插件`，在输入框内填入两个 html 的运行地址（一般情况下，服务地址是`http://localhost:3000/sidebar.html`，scriptServiceUrl 的地址是`http://localhost:3000/script.html`，具体以插件根目录的 README.md 为准）后点击 `确定` 添加并运行插件
    

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/oJGq75kv4DDQ2lAK/img/d08495f1-85f7-4fdd-b861-402ec6fd11dd.png)

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/oJGq75kv4DDQ2lAK/img/f64a6846-f346-49e7-8b1a-ede5e6c4bf9c.png)

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/vBPlN5m0zy8wkOdG/img/ec8ef01a-f1c7-435f-93d3-3f25f2d20a2f.png)

## 插件上架

请联系 $\color{#0089FF}{@huanan(桦楠)}$  $\color{#0089FF}{@欧阳莫微(弗隐)}$ 

## 附录（JSAPI 开放文档）

[《读写AI 表格模型》](../../shared/references/api/读写AI 表格模型.md)