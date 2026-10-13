# ISV接入AI表格开放API

## 背景：

AI表格读权限属于高敏感度权限，无法简单直接开放给ISV。

由于AI表格数据属于组织，而 isv 有了开放 api 接口调用权限后，AI表格数据会流入第三方服务。

为了解决该场景的合规性，AI表格在咨询法务和安全同事后，引入了【组织授权和个人授权】机制共同进行管理。

## 原理：

一句话解释：借助 【AI 表格边栏插件】的授权机制，在【组织授权+个人授权】的基础上，允许 ISV 以授权用户的身份访问 AI 表格的数据。

用户视角授权示例：

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ybEnB5jRBPNNYlP1/img/93777da4-803c-4398-bda7-f0e14fe349b6.png)

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ybEnB5jRBPNNYlP1/img/2c721151-22a5-4ce4-a42f-5d54464ad923.png)

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ybEnB5jRBPNNYlP1/img/4dce42ba-44a3-43b4-90c7-4b62c8efc9b5.png)

1.  首先需要组织管理员授权开通此【边栏插件】，该边栏插件即可显示在组织内的边栏插件市场中心中
    
2.  待组织内某个用户通过点击该【边栏插件】授权完成后，该【三方应用】即有权限调用 AI 表格开放 API 进行数据读写
    

## ISV 接入方式：

1.  注册三方应用
    
    ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ybEnB5jRBPNNYlP1/img/80589ebd-76e4-433c-a272-71db9ad9c82a.png)
    
2.  创建 AI 表格 酷应用
    
    ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ybEnB5jRBPNNYlP1/img/ccc2ceca-550c-49ab-952f-40ee4f2a45f5.png)
    
    [《AI 表格插件 - 企业内插件发布指南》](./AI 表格插件 - 企业内插件发布指南.md)
    
    :::
    在边栏插件中，AI 表格提供了几个 JSAPI 帮助开发者获得 accessToken，此处展示示例代码：
    
    获取当前边栏插件是在哪个组织下打开，获取对应的 corpId。（边栏插件打开时，会在 url 末尾拼上当前的 corpId）
    
    ```typescript
    const getSearchParams = () => {
      const search =
        window.location.search || window.location.hash.split("?")[1] || "";
      const params = new URLSearchParams(search);
      return params;
    };
    
    const getCorpId = () => {
      const search =
        window.location.search || window.location.hash.split("?")[1] || "";
      const params = new URLSearchParams(search);
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
    
3.  联系 $\color{#0089FF}{@张浩(子澄)}$ ，上架酷应用，并开通【 ISV 调用 AI 表格开放 API】 的白名单