# AI 表格插件 - 企业内插件发布指南

## 什么是企业内插件

AI表格插件是一个提供给用户更加便捷、灵活的数据处理与开放能力。企业成员可以自定义开发插件，供企业内的其他成员使用。

## 应用场景

*   数据分析
    

根据企业业务场景对AI表格数据进行自定义数据分析及内容更新，提升工作效率。

*   接入企业内部业务系统数据
    

在AI表格中将企业内业务系统数据导入到AI表格中，或将AI表格内容批量导出到业务系统，实现高效数据互通。

## 如何发布企业内插件

### 前提条件

需要进行以下两个动作：

1.  开发插件及调试
    
    如需要开发企业内边栏插件，可参考以下开发指南：

    [《AI表格边栏插件 开发指南》](./AI表格边栏插件 开发指南.md)
    
    :::
    ⚠️发布给企业其他人使用的边栏插件需要先进行JSAPI鉴权，才能正常读写文档内容。详见下方[插件鉴权](#插件鉴权)。
    :::
    
2.  完成[创建酷应用](https://open.dingtalk.com/document/orgapp/create-coolapp?spm=ding_open_doc.document.0.0.626873808t7GbN)流程。
    

### 操作步骤

1.  进入创建酷应用界面，选择扩展到AI 表格。
    
    ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/8oLl952aX9DVJlap/img/469105f7-0d62-4d42-af09-093732f8c387.png)
    
2.  填写AI 表格插件基本信息，填写基本的插件名称、作者、图标，用于在插件中心展示。
    
    ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/8oLl952aX9DVJlap/img/16b174e0-ac51-4cd6-bc7d-2f6665aa7887.png)
    
3.  完善插件配置，选择插件类型为侧栏插件
    
    | 插件配置项 | 说明 |
    | --- | --- |
    | 插件分类 | 插件分类决定当前插件在插件市场中展示的位置<br>配置分类为首页精选推荐将展示在插件首页精选推荐<br>![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/8oLl952aX9DVJlap/img/c78615f0-c62e-4642-b59a-9bb385b0ccc5.png)<br>配置其他分类标签将展示在插件中心对应插件分类列表中<br>![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/8oLl952aX9DVJlap/img/88c7cda9-11ad-4349-817a-9ef1fda85fa7.png)<br>当未配置分类标签时，默认在插件中心的「其它」<br>![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/8oLl952aX9DVJlap/img/f3942d25-9ddc-4226-8a36-b1a50542f6ad.png)<br>此外通过企业自建应用创建的插件也可在「插件中心」-「企业专用」分类下找到<br>![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/8oLl952aX9DVJlap/img/43c67892-8ec0-45c9-96f1-a9545020d213.png) |
    | 用户界面地址 | 运行在边栏 iframe 中，负责用户界面展示和交互 |
    | 数据处理地址 | 运行在 Web Worker 中，负责与AI表格数据模型交互 |
    
4.  完善插件介绍信息（选填），用于在插件中心中展示。
    
    ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/8oLl952aX9DVJlap/img/7b8df4ed-c352-45a9-a4a7-3b92fdb4f7be.png)
    
5.  **点击「保存」，然后点击「发布」**即可将最新的插件上架到企业文档中。
    
    ### 插件可见性
    
    刚发布的企业内插件仅插件作者可以看见，开发者可以通过「开发者后台」-「包含AI 表格插件的钉钉企业内部应用」-「应用发布」进行插件的可见性更新。
    
    ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/8oLl952aX9DVJlap/img/1ef2e898-3e5f-443c-b12f-527277294c8b.png)
    
    ## 插件鉴权
    
    当发布企业内插件或第三方企业插件时，需要使用 `Dingdocs.base.host.configPermission` 进行额外鉴权，以允许插件读写AI表格数据。
    
    鉴权参数和钉钉应用JSAPI鉴权参数保持一致，可参考以下文档：
    
    [https://open.dingtalk.com/document/dingstart/develop-webapp-frontend: https://open.dingtalk.com/document/dingstart/develop-webapp-frontend](https://open.dingtalk.com/document/dingstart/develop-webapp-frontend)
    
    在[官方推荐模版](https://github.com/dingdocs-notable/addon-demo)中可直接执行`npm/yarn start:server`启动本地服务端，并在调用initView初始化逻辑后补充调用插件鉴权API。
    
    ```javascript
    initView({
      onReady: async () => {
        // 初始化插件鉴权(公开发布企业内插件/三方企业插件场景下需要进行以下鉴权)
        await Dingdocs.base.host.configPermission(agentId, corpId, timeStamp, nonceStr, signature, jsApiList);
      },
    });
    ```
    
    :::
    在边栏插件中，AI 表格提供了几个 JSAPI 帮助开发者获得 accessToken，此处展示示例代码：
    
    获取当前边栏插件是在哪个组织下打开，获取对应的 corpId。
    
    用户界面地址配置：`https://example.com/ui.html?corpId=$CORPID$`，边栏插件打开时，会在 url 末尾拼上当前的 corpId
    
    ```typescript
    const getSearchParams = () => {
      const search =
        window.location.search || window.location.hash.split("?")[1] || "";
      const params = new URLSearchParams(search);
      return params;
    };
    
    const getCorpId = () => {
      const params = getSearchParams();
      const corpId = params.get("corpId") || "";
      return corpId;
    };
    ```
    
    获取当前用户免登码 AuthCode
    
    ```typescript
    const getAuthCode = async () => {
      const corpId = getCorpId();
      const authCode = await Dingdocs.base.host.getAuthCode(corpId);
      return authCode;
    };
    ```
    
    其他可参考开放平台接口，获得对应的信息：
    
    [服务商获取第三方应用授权企业的access\_token](https://open.dingtalk.com/document/isvapp/obtains-the-enterprise-authorized-credential)
    
    [通过免登码获取用户信息](https://open.dingtalk.com/document/orgapp/obtain-the-userid-of-a-user-by-using-the-log-free)
    :::
    
    ## FAQ
    
    **Q：**报错获取文档信息失败: PermissionError:  Do not have permission to access this document.
    
    ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/YdgOk2bGJWb9gq4B/img/1c6898a3-cadf-41ba-af5e-43d4b3d6c2a7.png)
    
    **A：**未执行插件鉴权，无法读取AI表格内容。请先执行`Dingdocs.base.host.configPermission`。
    
    **Q：**我想发布一个三方插件，使用插件的组织corpId是非固定的，应该如何获取当前打开插件的组织corpId?
    
    **A：**在配置**用户界面地址**时，可以补充传参`https://www.example.com/ui.html?corpId=$CORPID$`，实际在插件打开时，参数corpId中可以动态获取到当前使用插件的组织corpId。
    
    **Q**：`Dingdocs.base.host.getAuthCode`无法获取免登码。
    
    **A**：您需要检查以下问题：
    
    1.  针对企业内插件，确保您钉钉应用所属组织和AI表格所属组织一致。
        
    2.  检查酷应用所在钉钉应用是否配置了免登授权码跳转域名，如果没有，请配置插件用户界面地址到**重定向URL**和**端内免登地址**中
        
        ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/pLdn55XvkoRAWno8/img/b19969fa-9abd-422d-b74f-bcd7090d21be.png)
        
    3.  检查酷应用所在的钉钉应用是否进行了应用发布
        
        ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/pLdn55XvkoRAWno8/img/6fb7a592-e4fb-4e31-a978-ab00222a6ff4.png)
        
    4.  检查当前钉钉应用扩展的应用能力，如果仅添加了「酷应用」能力，需要额外添加「网页应用」或「小程序」。（可以不用进行具体配置）
        

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/pLdn55XvkoRAWno8/img/e2507c4a-cb48-4ed7-828d-44ff4875e2ef.png)

### 问题反馈

有任何插件发布、开发等相关问题可联系 $\color{#0089FF}{@欧阳莫微(弗隐)}$ 咨询