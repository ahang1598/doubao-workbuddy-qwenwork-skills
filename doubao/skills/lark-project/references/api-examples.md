# 命令调用示例

---

## 空间域

### project.search

```bash
larkproject_cli_exce project search --project-key 空间名或key --format json
```

## 工作项域

### workitem.meta-types

```bash
larkproject_cli_exce workitem meta-types --project-key 空间key --format json
```

### workitem.meta-fields

查询所有字段：

```bash
larkproject_cli_exce workitem meta-fields --project-key 空间key --work-item-type-key story --format json
```

### workitem.meta-roles

```bash
larkproject_cli_exce workitem meta-roles --project-key 空间key --work-item-type-key story --format json
```

### workitem.query

查询空间中所有未冻结的需求：

```bash
larkproject_cli_exce workitem query --project-key 空间key --search-mql 'SELECT `work_item_id`, `name`, `current_owners`, `status` FROM `空间名`.`story` WHERE `is_archived` = 0' --format json
```

### workitem.get

```bash
larkproject_cli_exce workitem get --project-key 空间key --work-item-id 工作项ID或名称 --format json
```

### workitem.create

```bash
larkproject_cli_exce workitem create --project-key 空间key --work-item-type-key story --format json
```

### workitem.update

更新普通字段：

```bash
larkproject_cli_exce workitem update --project-key 空间key --work-item-id 工作项ID --format json
```

---

## 人员域

### user.search

```bash
larkproject_cli_exce user search --user-keys ["张三", "李四"] --format json
```

### user.me

```bash
larkproject_cli_exce user me --format json
```

---

## 工作台域

### mywork.todo

查询我的待办：

```bash
larkproject_cli_exce mywork todo --action todo --page-num 1 --format json
```

---

## 工时域

### workhour.list-schedule

```bash
larkproject_cli_exce workhour list-schedule --project-key 空间key --user-keys ["张三", "李四"] --start-time 2025-03-01 --end-time 2025-03-31 --format json
```

---

## 视图域

### view.get

```bash
larkproject_cli_exce view get --view-id 视图ID --project-key 空间key --format json
```

---

## 工作流域

### workflow.get-node

```bash
larkproject_cli_exce workflow get-node --work-item-id 工作项ID --node-id-list ["节点ID或_all"] --project-key 空间key --format json
```

### workflow.transition

完成节点（节点流）：

```bash
larkproject_cli_exce workflow transition --work-item-id 工作项ID --node-id 节点ID --action confirm --project-key 空间key --format json
```

### workflow.transition-state

流转状态（状态流）：

```bash
larkproject_cli_exce workflow transition-state --work-item-id 工作项ID --transition-id 流转ID --project-key 空间key --format json
```

### workflow.list-state-transitions

```bash
larkproject_cli_exce workflow list-state-transitions --project-key 空间key --work-item-id 工作项ID --work-item-type-key story --user-key userkey --format json
```

---

## 评论域

### comment.add

```bash
larkproject_cli_exce comment add --work-item-id 工作项ID --comment-content '评论内容' --format json
```

### comment.list

```bash
larkproject_cli_exce comment list --project-key 空间key --work-item-id 工作项ID --format json
```

---

## 关系域

### relation.meta-definitions

```bash
larkproject_cli_exce relation meta-definitions --project-key 空间key --format json
```

### relation.list

```bash
larkproject_cli_exce relation list --project-key 空间key --work-item-id 工作项ID --format json
```

---

## 子任务域

### subtask.update

```bash
larkproject_cli_exce subtask update --node-id 节点ID --work-item-id 工作项ID --action create --format json
```
