# 国内路线规划

仅用于国内实际出行。旅游行程及多地点顺序串联使用 `map_mark`；指定偏好、时间、车辆条件，或比较交通方式及候选路线使用 `route_plan_v2`。海外路线、历史人物事件轨迹、指定线路、道路路网及区域边界，依据公开可信资料获取。

## 1. 多地点行程：map_mark

`map_data` 传 JSON 对象：

| 字段 | 说明 |
| --- | --- |
| `title` | 地图标题 |
| `text` | 完整行程上下文，包含行政区、地点消歧及住宿、游览等说明 |
| `scene` | 普通旅游、Citywalk、景区游览等用 `travel_plan`；以自驾或全程包车为主的路线用 `travel_route` |
| `plans` | 行程分组，每组包含 `name` 和有序 `points` |
| `plans[].description` | 可选，每组的简要攻略，展示在对应分组及详情中 |
| `points[].name` | 每个点对应一个明确地点，使用精简地点本名，必要时保留城市或分店限定；不混写备选地点或活动说明 |
| `points[].via` | 从上一个参与连线的地点到当前地点的交通方式 |
| `points[].level` | 普通地点省略；仅展示、不连线时填 `recommend` |

`travel_route` 下，行程为环线或出发地与返回地一致时，首日第一个点与最后一天最后一个点使用相同地点名称。

`via` 支持 `walking`、`driving`、`transit`、`rail`、`flight`、`cycling`、`ferry`；无明确要求时省略。

```json
{"map_data":{"title":"杭州游览路线","text":"地点均位于浙江省杭州市西湖区。","scene":"travel_plan","plans":[{"name":"游览路线","points":[{"name":"灵隐寺"},{"name":"上天竺法喜讲寺","via":"walking"}]}]}}
```

按出行顺序填写地点。服务解析地点并规划相邻地点之间的路线，无需提前补查全部坐标。上述参数写入任务文件的 `parameters`，由下方脚本发起请求，无需先单独调用 MCP。

## 2. 交通路线：route_plan_v2

`origin`、`destination` 为起终点，`waypoints` 为有序途经点数组；每个地点只选一种表示：

| `type` | 填写规则 |
| --- | --- |
| `place` | `value.text` 填名称或地址，带必要的城市、分店或出入口信息 |
| `id` | `value.text` 填工具支持的真实 POI ID |
| `coordinate` | `value.longitude`、`value.latitude` 填可靠坐标，遵循工具坐标系 |
| `current_location` | 仅在具备有效定位信息时使用 |

已有可靠地点数据直接复用，不编造 ID、坐标，不使用 `0,0` 占位。途经点最多 **15 个**；超出按顺序拆分，共用相邻请求的衔接地点，不遗漏必经点。

`modes` 支持 `driving`、`walking`、`cycling`、`transit`。公交、地铁及火车、高铁、飞机、大巴、轮渡使用 `transit`。未指定方式时省略；需要多方式比较时传入相应方式，不因跨城市就强制公共交通。

- `departure_time` / `arrival_time`：最多一个，使用明确的未来时间，格式 `YYYY-MM-DD HH:mm:ss`；“现在”“马上”通常省略。
- `vehicle_context`：按需填车型和用户提供的车牌；车型按工具定义选择。
- `search_by_route_query`：沿途搜索关键词数组。
- `preference`：只填用户要求且适用于当前方式的偏好；冲突要求需澄清。

| 偏好 | 枚举 |
| --- | --- |
| 最短距离 / 最快 | `minimize_distance` / `minimize_time` |
| 避高速 / 优先高速 | `avoid_highway` / `perfer_highway` |
| 避拥堵 / 避收费 / 少红绿灯 | `avoid_congestion` / `avoid_tolls` / `minimize_traffic_lights` |
| 少换乘 / 少步行 | `minimize_transfers` / `minimize_walking` |
| 不坐地铁 / 优先地铁 | `avoid_subway` / `prefer_subway` |
| 跨城最早出发 / 低价 | `intercity_departure_asc` / `intercity_price_asc` |
| 跨城铁路 / 飞机 / 大巴优先 | `intercity_vehicle_railway` / `intercity_vehicle_plane` / `intercity_vehicle_coach` |

`intercity_*` 仅用于跨城公共交通；`perfer_highway` 沿用接口拼写。参数以当前工具定义为准，无需求的字段省略。

核对返回的地点、方式和约束。有歧义时明确采用的候选，无法判断时请求确认；仅有地点候选而无路线时不编造路线。普通查询选择推荐方案；比较时保留各方案，分别导入，不拼接候选轨迹。耗时、费用、车次和航班以实际返回为准，缺失不补造。

## 3. 一份任务输入，自动生成 MapSpec

选定工具、组织方式和 View 后，只写 `map-task.json`，运行一次脚本。**不用先调用 MCP，不用写 Spec 骨架、映射文件或后处理脚本，也无需阅读脚本源码。**

| 字段 | 含义 |
| --- | --- |
| `id`、`title` | 任务标识和标题，id 可省略 |
| `summary` | 可选，填写在任务 JSON 根层，用于总览简介；每日攻略填写 `plans[].description` |
| `tool` | `map_mark` 或 `route_plan_v2` |
| `parameters` | 上述对应工具的参数对象 |
| `organization` | `route` 单条路线；`itinerary` 顺序行程；`days` 明确分日；`alternatives` 候选比较；`distribution` 同屏分布 |
| `views` | 必填：`single` 同屏展示全部组；`per-group` 总览加每组独立查看 |
| `reason` | 已采纳的组织和 View 决策依据；不为通过校验虚构依据 |
| `selection` | 仅交通路线：`recommended` 取首个推荐实体；`all` 保留全部候选，须配 `alternatives` |
| `presentation` | 可选，展示偏好对象或完整 Plan 文件路径；整体简介用根层 `summary`，不放入此字段 |

完整输入见 [行程示例](../examples/map-task-itinerary.json) 、[自驾示例](../examples/map-task-road-trip.json) 和 [交通方案示例](../examples/map-task-transport.json)。只改需求相关字段，不默认分天、分方案或多个 View。交通路线的 organization 使用 `route` 或 `alternatives`；多交通方式比较用 `selection: all`。

```bash
node "$SKILL_DIR/scripts/create-map.mjs" --request map-task.json --out build/map.html --publish --telemetry-task telemetry-task.json
```

脚本生成 Spec 和基础 Plan，保持输入分组及地点顺序；`days` 按分组顺序组织日期。`organization: "distribution"` 只采纳地点，不将服务附带路径作为路线，不生成游览顺序或编号。需要路线与独立地点共存时，用 Spec 显式声明关系。完整坐标保存在文件，不读回模型上下文。

`presentation` 使用现有 [Presentation Plan](presentation-plan.md) 字段，仅填写需要覆盖的偏好，无需补协议身份或空配置。例如 `"presentation": {"stylePreference": {"tone": "dark"}}`。未指定时使用基础展示；提供完整 Plan 时按原样校验。对象合并规则：

- 根字段覆盖默认值，数组整体替换；`views` 按 ID 合并。
- `organization` 保留缺省字段；总览模式不变时 `overview` 按字段合并；`viewPurposes` 按 View ID 及字段合并。不能覆盖任务已声明的 dimension/evidenceRefs 或协议身份。
- 改为集合入口需提供有效节点与入口；行程代表位置由程序从真实成员中派生并记录依据；指标、筛选等必须有真实数据依据，不能靠默认值猜测。

相对文件路径按任务 JSON 所在目录解析。工具参数与展示偏好分开缓存，仅修改展示偏好不重新请求路线。非工具任务直接编写 Spec/Plan，按 SKILL 的 `--spec --plan` 命令执行，无需包装任务 JSON。

交通查询的分段顺序不是游览编号：起终点使用端点标记；有名称和坐标的换乘点保留，缺少坐标时保留分段说明，不从折线猜测车站。公开标题和简介使用可读内容，不展示内部 reason 或整段服务响应。

同一 map_mark path 保持为一条路线，分段方式和指标保存在 properties.segments；轨迹标为 supplied，可能含接线或降级段，不宣称全是真实道路。map_mark 距离为米、时间为分钟；route_plan 距离为米、时间为秒、费用为元，缺失或默认零费用不解释成免费。

## 4. 等待与失败

单次轮询最多 10 秒。超时后重跑**同一命令、同一目录**，脚本使用 task-state.json 继续查询，不重复提交。提交超时则状态不确定，先确认原任务，不能自动重发；并发占用目录时先等待现有进程结束。修改输入后，在原目录重跑同一命令。

响应、状态和结果缓存在工作目录；已完成任务重跑直接复用，不拉取长坐标到模型上下文。地点歧义、缺失轨迹或不支持的结构会明确报错，不输出不完整 Spec；当前 map_mark 自动转换支持平铺 plans 的点线结果，child_plan/区域数据需走相应数据流程。

参数错误或地点歧义仅修正受影响请求；暂时失败最多重试两次。无可用路线时查询公开可信资料；仍缺失且允许示意时按通用 MapSpec 流程使用直线，并标注“路线示意，非实际通行路径”。要求真实路线时说明缺失部分，不虚构轨迹、耗时或费用。
