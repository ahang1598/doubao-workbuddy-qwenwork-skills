---
name: app-component-image
description: App 图片的默认头图尺寸、展示设置和素材能力边界。
---

# 图片 image

默认容器宽×8，推荐W12～48、H6～8；头图用布局宽铺整行，不默认宽高fill，不height auto。用户合法尺寸优先。

create可省略data_config得到空容器，可选carousel/switching/filling/opacity/description_style。reset_settings=true与其它展示设置互斥，省略保留。当前没有上传/替换图片资源公开字段，轮播开关不会自动补素材。

不支持app-block-get-data，block-get核对实际已有素材与保存设置。用户要求真实头图/轮播且没有资源时报告能力缺口，空容器不算交付，不编URL或把SDK资源方法当CLI能力。
