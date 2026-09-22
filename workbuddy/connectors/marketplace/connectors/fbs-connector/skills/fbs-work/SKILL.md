---
name: fbs-connector-work
description: "说明福帮手事项与人工帮助的接续方式；当前默认资源仅提供指引，不自动保存或提交资料。"
description_zh: "仅说明事项与帮助接续条件；工具未开放时不查询、保存或提交资料。"
description_en: "Explain case and assistance prerequisites; unavailable tools do not query, save or submit user materials."
version: "2026.9.20"
author: "FBSir"
---

# 事项与帮助接续

本页事项CRUD/帮助工具仍为support_readiness=guidance_only，未在本轮OAuth Gateway暴露；管理系统本人网页已有的事项流程与此不同。画像已支持获准的本人既有CASE事实，但不因此开放member_case_*或member_request_*。先遵守[公共路由](../fbs-connector/SKILL.md)，缺工具仅给已核实的本人门户入口。

以下工具只有后续单独审定并在本轮真实开放时才适用：member_case_list/get、member_case_create、member_case_link；当前不尝试它们。已存在事项可按[画像协议](../fbs-profile/references/profile-purpose-and-provenance.md)复用同意范围内事实，不改变事项本身或关联服务。不得把聊天、打开文件或沉默当保存许可。

用户希望人工协助时，`member_request_entry` 只提供填写入口；`member_request_list/get` 只查本人已提交需求与公开回复。用户在网页选择资料范围及联系许可；不代提交、不自动联系工作人员。

服务目录目前只有网页/API。拟议 `member_service_catalog_list/get` 未通过能力门不能调用；提供已核实入口，不把目录当订单。成果引用不表示正文已上传或支持跨设备下载。
