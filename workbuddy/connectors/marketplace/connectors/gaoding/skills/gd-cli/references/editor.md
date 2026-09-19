# AI+ Editor

## 使用边界

使用 `gd-cli editor` 读取和操作浏览器中当前一个 AI+ Editor 作品。当前版本只支持一个 Editor Session、当前 Page 的直属 Shape 和 Connector，以及单操作者串行操作。

支持的 Shape：

- `rectangle`
- `rounded-rectangle`
- `triangle-up`
- `ellipse`
- `diamond`

Connector 必须从一个 Shape 绑定到另一个 Shape，`lineType` 只支持 `straight` 和 `elbowed`。当前不支持 Group、图片、视频、独立文本、嵌套元素、自由 Connector、半绑定 Connector、Connector label、端点坐标、选择修改或页面管理。

当前 Page 只要包含不支持的直属元素，`snapshot`、`apply` 和 `screenshot` 都会返回 `UNSUPPORTED_PAGE_CONTENT`。此时停止操作，让用户换用空白或专用 Page；保留原作品内容。

## 标准流程

按以下闭环执行，完成标准是保存后得到 `workId` 和公开作品 URL：

1. 建立 Session。target 省略时在线上新建 Board；纯数字按线上作品 ID 打开；完整 HTTP/HTTPS URL 按该 URL 的环境打开：

   ```bash
   gd-cli editor connect
   gd-cli editor connect 37428738696269847
   gd-cli editor connect "http://my.gaoding.art:3000/?mode=create&type=board"
   ```

   三种形式只选与目标匹配的一种。`connect` 只有在页面已连接，且浏览器 AI+ 登录、作品加载、Board 类型、编辑/保存权限和内容检查全部通过后才成功。连接失败时停止作图。

2. 读取当前 Page：

   ```bash
   gd-cli editor snapshot
   ```

3. 根据 Snapshot 生成完整、有序的 Action JSON 数组，通过文件或 stdin 应用：

   ```bash
   gd-cli editor apply --input actions.json
   # 或
   gd-cli editor apply --input -
   ```

4. 每次 Apply 后都重新读取结构。只要涉及布局、文字或 Connector，再获取截图并打开实际 PNG 复查：

   ```bash
   gd-cli editor snapshot
   gd-cli editor screenshot --json
   ```

   `screenshot --json` 返回 `{ "path": "<绝对 PNG 路径>" }`。使用本地图片查看能力检查图片；文件存在或 Action 已提交都不代表渲染正确。

5. 结构和视觉复查均通过后显式保存：

   ```bash
   gd-cli editor save --json
   ```

   成功 stdout 形如：

   ```json
   {
     "workId": "37428738696269847",
     "url": "https://www.gaoding.art/editor/canvas?mode=user&type=board&id=37428738696269847"
   }
   ```

   只有该命令成功才可以声明作品已保存。新 Board 在第一次显式保存时创建作品 ID；把返回的公开 `url` 交给用户，并保留其中的环境参数。

   保存会等待 AI+ Editor 的真实持久化完成，可能明显慢于其他 Editor 命令；Bridge 为 Save 保留最长 5 分 30 秒。保持命令运行直到返回，不因短暂无输出而中断或并发发起其他 Editor 命令。

6. 保存成功后断开 Session：

   ```bash
   gd-cli editor disconnect
   ```

`connect` 会替换旧 Session 并打开作品页面。连接前置检查失败会清理本次 Session，但保留浏览器页面；用户在页面中完成登录或处理访问权限后，再重新执行 `connect`。GD CLI 的 AK/SK 登录不能替代浏览器 AI+ 登录，账号密码应由用户在浏览器登录界面输入。

如果 AI+ 在同一个 SPA 页面再次加载或切换作品，当前 Session 会主动断开以避免误写；此时重新执行 `gd-cli editor connect [target]`。

## 复查作品

复查依据必须是 Apply 后的最新 Snapshot 和实际截图。Snapshot 用于确认元素、字段和连接关系；截图用于判断路径、文字和布局。

逐项检查，全部通过才算完成：

- 每个 Connector 的 `fromId`、`toId` 都指向预期 Shape，方向符合语义；
- 每条可见路径从 `fromId` Shape 边界开始、在 `toId` Shape 边界结束，不穿过任一端点 Shape 的填充或文字；
- 同轴相邻 Connector 也逐条检查，不能把端点穿线解释成连续线效果；
- Connector 不穿过无关 Shape，没有明显绕行、不自然折返或错误连接；
- Shape 中的文字完整可读，没有截断、溢出或意外换行；
- Shape、文字和 Connector 没有非预期重叠，必要间距真实存在；
- 整体阅读方向清楚，构图平衡，关系容易沿 Connector 追踪。

发现可执行问题时，先读取最新 Snapshot，再提交修正。Update 必须包含完整元素，不能提交 patch。若 `fromId`、`toId` 正确，但截图中的 Connector 仍穿过端点 Shape，原样提交该 Connector 的完整 Update 以触发原生路径重算；业务关系正确时不为绕开渲染问题改动关系。

修正后再次执行 `snapshot`；涉及视觉变化时再次执行 `screenshot --json` 并打开图片。存在问题就继续修正；没有可执行问题时结束复查并保存。

## Snapshot 契约

```ts
type FocusedPageSnapshot = {
  elements: Array<FocusedShape | FocusedConnector>;
  selectedIds: string[];
};

type FocusedShape = {
  _type: "shape";
  id: string;
  shapeType:
    | "rectangle"
    | "rounded-rectangle"
    | "triangle-up"
    | "ellipse"
    | "diamond";
  x: number;
  y: number;
  w: number;
  h: number;
  text?: string;
  fill: string;
  stroke: string | null;
};

type FocusedConnector = {
  _type: "connector";
  id: string;
  fromId: string;
  toId: string;
  lineType: "straight" | "elbowed";
  color: string;
};
```

`x`、`y` 是 Shape 左上角的 Page 坐标，`w`、`h` 是尺寸。`selectedIds` 只读。

只使用简短、有语义的 `id`，例如 `start`、`review`、`start-to-review`。Bridge 会把这些 ID 映射到 Editor 内部标识。Connector 用 `fromId`、`toId` 表达有方向的 Shape 关系。

## Action 契约

```ts
type FocusedEditorAction =
  | { _type: "create"; element: FocusedShape | FocusedConnector }
  | { _type: "update"; element: FocusedShape | FocusedConnector }
  | { _type: "delete"; id: string };
```

- 输入必须是 JSON 数组，Action 按数组顺序执行。
- Create 的 `id` 必须唯一；Connector 可以引用本数组中更早创建的 Shape。
- Update 必须提交完整元素，不能提交 patch，也不能改变 `id` 或 `_type`。
- Delete 的 `id` 必须存在；删除 Shape 会同时删除绑定到它的 Connector。
- 对象不接受额外字段。所有数值必须有限，`w`、`h` 必须大于 0。
- `fill`、`stroke` 和 `color` 使用 `#RRGGBB` 或 `#RRGGBBAA`；只有 Shape 的 `stroke` 可以为 `null`。
- 整批 Action 会先预检，再在一个可回滚事务中应用。任何一项无效时整批不写入；修正输入后再提交。

## 完整示例

以下数组创建从左到右的 `Start -> Review? -> Done` 流程图：

```json
[
  {
    "_type": "create",
    "element": {
      "_type": "shape",
      "id": "start",
      "shapeType": "rounded-rectangle",
      "x": 80,
      "y": 160,
      "w": 180,
      "h": 80,
      "text": "Start",
      "fill": "#ffffff",
      "stroke": "#222222"
    }
  },
  {
    "_type": "create",
    "element": {
      "_type": "shape",
      "id": "review",
      "shapeType": "diamond",
      "x": 360,
      "y": 140,
      "w": 140,
      "h": 120,
      "text": "Review?",
      "fill": "#f2f6ff",
      "stroke": "#222222"
    }
  },
  {
    "_type": "create",
    "element": {
      "_type": "shape",
      "id": "done",
      "shapeType": "rounded-rectangle",
      "x": 600,
      "y": 160,
      "w": 180,
      "h": 80,
      "text": "Done",
      "fill": "#e8f7ed",
      "stroke": "#222222"
    }
  },
  {
    "_type": "create",
    "element": {
      "_type": "connector",
      "id": "start-to-review",
      "fromId": "start",
      "toId": "review",
      "lineType": "straight",
      "color": "#222222"
    }
  },
  {
    "_type": "create",
    "element": {
      "_type": "connector",
      "id": "review-to-done",
      "fromId": "review",
      "toId": "done",
      "lineType": "straight",
      "color": "#222222"
    }
  }
]
```

修改现有元素时，以最新 Snapshot 中的完整对象为基础，只改变目标字段后提交完整 Update。

## 失败处理

- `LOGIN_REQUIRED`：停止作图，让用户在已打开的 AI+ 页面登录，然后重新执行 `connect`；浏览器登录不能用 `gd-cli auth` 代替。
- `EDITOR_NOT_READY`：停止并检查页面是否完成加载；重新执行 `connect`，成功前不调用写操作。
- `WORK_NOT_EDITABLE`：停止；当前用户没有该作品的编辑或保存能力。
- `EDITOR_SESSION_NOT_FOUND`：重新执行 `gd-cli editor connect [target]`，然后读取 Snapshot。
- `EDITOR_NOT_CONNECTED`：页面连接已丢失；重新连接目标作品，不轮询旧 Session。
- `UNSUPPORTED_PAGE_CONTENT`：停止，让用户改用空白或专用 Page。
- `INVALID_ACTIONS`：根据本契约和最新 Snapshot 修正 Action，不原样重试。
- `APPLY_FAILED`：运行时异常已触发批次回滚；重新读取 Snapshot，确认作品处于 Apply 前状态后再决定下一步。
- `EDITOR_ROLLBACK_FAILED`：无法确认恢复到 Apply 前状态。停止所有 `apply` 和 `save`，只读取 Snapshot 或截图并报告。
- `SAVE_FAILED`：保留当前 Session，处理明确失败原因后可再次执行 `save --json`；成功前不报告已保存。
- `EDITOR_BUSY`：等待当前命令结束后再发下一条，保持串行。
- `EDITOR_RPC_TIMEOUT`：页面是否执行完成未知，Bridge 会关闭。普通 Editor RPC 默认等待 1 分钟，Save 最长等待 5 分 30 秒。读取类操作可重新连接同一作品后重试；`apply` 或 `save` 属于不确定写入，先重新连接同一作品并检查真实状态，再决定后续动作。无法检查原作品时停止并报告，不自动重试该写入。
- `PROTOCOL_VERSION_MISMATCH`：停止并升级 GD CLI，或使用协议匹配的 AI+ Editor。

任何写操作在超时、取消或连接中断后都可能已经提交。恢复时先观察真实状态，避免重复创建、重复 Apply 或重复 Save。
