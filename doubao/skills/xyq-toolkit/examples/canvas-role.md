# 场景：在已有画布创建角色节点

用户请求：“在这个小云雀画布里新增一个叫小雨的角色节点。”用户已提供真实画布资产 ID，目标是新增资料节点，不是生成人物图片。

先读 [Canvas 模块](../commands/canvas.md)，运行 `ensure-cli.js --canvas` 并完成授权。将 `CANVAS_ENTRY` 替换为返回的 Node 入口路径，将 `CANVAS_ASSET_ID` 替换为用户画布资产 ID。

```bash
node "CANVAS_ENTRY" canvas command list
node "CANVAS_ENTRY" canvas command describe create_biz_node --node-kind role
node "CANVAS_ENTRY" canvas command describe get_snapshot
node "CANVAS_ENTRY" canvas command run get_snapshot --canvas-id CANVAS_ASSET_ID --input '{}'
```

确认目标画布与既有节点，按当前 role schema 核对 `initialData.nodeName` 后执行：

```bash
node "CANVAS_ENTRY" canvas command run create_biz_node --canvas-id CANVAS_ASSET_ID --input '{"nodeKind":"role","initialData":{"nodeName":"小雨"}}'
```

由业务工厂分配节点及配套资产，不自行编 ID。检查实际执行结果，再回读：

```bash
node "CANVAS_ENTRY" canvas command run get_snapshot --canvas-id CANVAS_ASSET_ID --input '{}'
```

确认新增角色及名称，只报告“已新增角色节点”，附画布链接（已有时）和查询到的 ID。不调用独立生图命令，也不把新节点认定为已生成图片。失败或响应不确定时按 [画布编辑流程](../workflows/canvas-edit.md) 回读后恢复，避免创建重复节点。
