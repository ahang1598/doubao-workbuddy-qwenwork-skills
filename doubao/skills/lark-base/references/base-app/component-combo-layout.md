---
name: app-component-combo-layout
description: App 组合布局容器的内容尺寸、子树编辑和稳定ID边界。
---

# 组合布局 comboLayout

用于相关组件同时可见的视觉分区，无自身数据源；同位置切换使用Tabs。默认容器宽×内部内容高，推荐W16～48、H≥16，不默认宽高fill，内容决定高不等于height=auto。子项按各自尺寸规则和父坐标系，用户合法尺寸优先。

CLI结构为 `--structure-config '{"children":["<已有子组件ID>"]}'`，不是SDK factory或append/replace方法对象。先创建并回读子组件，再提交最终有序children。更新显式children会重排/移入所列项，遗漏的旧子项移回Page根；省略children保留。追加/改序时保留完整正确ID集合，不能把短Patch当SDK增量。精确形状可本地print-schema查看。当前只能同页移动；跨页同 App 仅在递归确认子树不含 View 时授权复制，再按要求删除。任意后代含 View 的容器不支持直接 copy，不承诺整树无损重建；单个 View 的公开配置重建见 [视图](component-view.md#复制单个-view按公开配置新建)。

名称在整页唯一，重名使用稳定ID。保留未点名兄弟与相对顺序，普通改名/排序不删除子树。原Agent的append/replace/remove方法不能直接调用；删除使用有授权的原子命令并另验。容器在页面根布局中只占一个目标，内部不跨根布局编排。

页面级可见按钮放Page根与容器邻接。写后structure核对父子树、稳定ID、顺序与子项rect；同父级重叠分别检查，容器和子项不相互比较。容器内唯一列表不触发根级高fill。
