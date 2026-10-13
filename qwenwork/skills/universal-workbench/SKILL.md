---
name: universal-workbench
description: 通用多人工作台生成器（任意业务类型）。先引导用户描述设计思路，再生成带角色权限管控、真实数据库读写、管理后台数据查看、在线发布分享的动态工作台网页。用户要求"做一个工作台/管理后台/协作系统/带数据库的多角色网页/内部工具"时使用。最小流水线场景优先用 min-db-workbench；本 skill 面向任意类型（PMO/日历/库存/审批/CRM 等）。
version: 1.0.0
install_source: official
install_method: download
skill_id: official_zzLnmE5n
enabled_at: 1791893740494
name_zh: 多人工作台
---

# 通用多人工作台生成器

任意业务类型 → 四大核心能力一次到位：**角色权限管控 + 真实数据库 + 管理后台 + 在线发布**。
铁律：**先引导设计思路，后动手写码**；全程积分最小化（见"积分纪律"）。

## 核心架构（固定，不随业务变）

```
用户描述 → [引导确认] → 设计契约 → 定制骨架 → 单次迁移 → 单次发布
```

四层固定结构：
1. **权限层**：roles（admin/member/自定义）× views（功能模块）矩阵。admin 全量；member = 默认可见视图 + 可授权视图（users.permissions JSON 列）。服务端 403 强制，前端只按 `/api/me` 的 `allowed_views` 渲染导航（前端隐藏≠权限，必须在服务端拦）。
2. **数据层**：Supabase（QW Pages 运行时注入 `SUPABASE_URL`/`SUPABASE_ANON_KEY`），PostgREST 访问，每业务实体一张表 + users + seed_meta。
3. **后台层**：管理后台 = 用户管理（角色/状态/授权/禁删）+ 数据浏览器（泛型表查看器，按表白名单逐表渲染）。
4. **发布层**：QW Pages 动态页，provision（一次）→ migration（一次）→ publish（一次）。

## 第 1 步：引导设计思路（先匹配预置，后问后做）

用户只说"做个工作台"时，**禁止直接开写**。

**先跑预置方案匹配**：读 `reference/presets.md`——内置四大预置（P1 班级共写·老师/家长/学生，P2 团队项目管理·替代早会，P3 达人合作·合作方互相隔离，P4 甲方审稿·评论留痕），每条含成套设计契约（角色矩阵/实体映射/视图/权限要点/种子建议）。用户描述命中画像关键词（教育作业→P1，团队任务站会→P2，达人投放合作方→P3，甲方改稿乙方→P4）时：直接出示该预置的一句话 pitch + 设计契约，AskUserQuestion 只确认 1 项（真实录入 or 演示数据），即开工——预置命中比通用四问更省积分。部分命中时以最接近预置为骨架、只问差异点。

**未命中预置**才走通用引导，一次 AskUserQuestion（≤4 问）覆盖：

1. **业务场景与核心实体**：这个工作台给谁用、管什么事？（选项给 3 个典型场景 + Other 让用户自由描述——实体名词从答案里提取，如"客户/跟进记录/合同"）
2. **角色设计**：默认 admin + member 两档；是否需要多角色（如"审批人/执行者/只读访客/外部合作方"）？
3. **功能模块清单**：从答案提取候选视图让用户勾选（multiSelect），典型如：列表/看板/日历/统计/审批流/数据后台
4. **数据要求**：真实录入用（空表+种子管理员）还是演示用（灌虚构假数据）？

引导话术：可借预置的 pitch 句式（"XX 的人终于不用 YY 了——搭一个 ZZ"）帮用户描述自己的场景，例句见 presets.md。

追问纪律：**最多一轮补充追问**，且仅限关键歧义（如实体关系不明）。其余一律"声明假设直接做"，交付时列出假设清单。用户答完即产出**设计契约**（见第 2 步），除非契约与用户原话冲突，否则不再确认。

## 第 2 步：设计契约（映射表，纯文本不落文件）

在回复里用 5-10 行给出，让用户看得见但不打断：

```
实体映射：客户→clients 客户表(名称/负责人/阶段/金额)，跟进→followups...
视图映射：客户列表→clients 视图(member 可见)，数据后台→admin only
角色矩阵：admin=全部+用户管理；member=客户列表+跟进记录（默认），统计(可授权)
种子数据：3 演示账号 + 12 条虚构客户记录（若演示用）
```

## 第 3 步：定制骨架（改配置，不重写）

复制 `reference/` 到工作目录，改动集中在三处：

1. **server-skeleton.js 顶部 CONFIG**：
   - `TABLES` 白名单：每表 `{ name, view, columns[], order }`（columns 同时是写入白名单，前端多余字段自动丢弃）
   - `VIEW_API_PREFIX`：视图 → API 前缀映射（权限门卫核心）
   - `DEFAULT_MEMBER_VIEWS` / `GRANTABLE_VIEWS`：member 默认可见与可授权范围
   - 列类型只允许 text/number/bool/date，避免迁移复杂度
2. **migration-template.sql**：按 TABLES 白名单生成建表 + RLS 全放行策略 + 种子数据。种子数据**必须写 Node 生成脚本**（`gen_seed.js`，参考已在多次实战验证的模式：数组 → SQL 字符串拼接），禁止手写长 SQL——防语法错误返工
3. **前端 public/index.html**（单文件，无 CDN 依赖）：登录页 + 侧栏（按 allowed_views 渲染）+ 每视图一个 section + 泛型列表渲染器（读 TABLES 配置）+ 用户管理 + 数据浏览器（`/api/admin/tables` 拉全表白名单逐表展示）

品牌与文案：`:root` 改 3 个品牌变量 + 全局搜索替换标题文案即可。

## 第 4 步：发布（严格走规程，每步只调一次）

1. 先 `Skill` 加载 **qw-pages** + **qw-pages-supabase**，按其规程执行
2. `qwenwork_pages_provision_database` 一次，name 用中文业务名
3. `qwenwork_pages_apply_migration` **一次**：schema + 种子合并成单个 SQL 一起提交（拆两次=双倍调用=双倍积分）
4. `qwenwork_pages_publish` 一次：`category:"dynamic"` + `entrypoint:"server.js"` + `port:8081` + `with_database:true`
5. 发布前清理：npm 产物里删除 `node_modules/.bin`（发布器拒符号链接）；骨架零依赖时直接不带 node_modules

## 积分纪律（每次执行对照自查）

- 引导只问一轮（≤4 问），追问 ≤1 轮，其余声明假设
- 不做本地起服务/浏览器截图验证；只跑 `node --check`（源码级验证足够）
- migration 单次合并提交；发布单次；**迭代需求攒批改**——用户提小改先记录，凑成一批改完一次重发（每次 publish 都是一次完整积分）
- 种子数据用脚本生成；前端单文件；不引入框架/CDN
- 不重复读取大文件；定制点集中在 CONFIG，避免全文重写

## 验证清单（发布前 60 秒过完）

- [ ] `node --check server.js` 通过
- [ ] TABLES 白名单列 = migration 列 = 前端表单字段（三方一致，最大翻车点）
- [ ] member 访问未授权视图 API 得 403（读代码确认服务端有拦，不是前端藏）
- [ ] 未登录 GET 业务 API 得 401；`/` 重定向 `/login`
- [ ] migration 幂等（`if not exists` + `on conflict` 种子）
- [ ] 种子密码 scrypt 加密，交付时提醒改密

## 常见坑（实战验证过）

- 前端直接读 `d.data` 还是裸字段——**先读骨架模板的 api() 封装再定制**，响应格式不匹配=整页空白（看似"没部署"）
- 发布后立即 curl 得旧版本——部署有秒级传播延迟，等 10s 再验，不要误判失败重发
- `usage`/`order` 等是 SQL 保留字，列名加后缀（`usage_notes`/`sort_order`）
- 前端要显示的表没进 TABLES 白名单 → 后台浏览器不显示
- 用户中途说"再加个模块" → 改 CONFIG + migration 补表 + 攒批重发，不动骨架

## 交付话术（引导用户自己叠加需求）

交付时固定带一句引导："这个工作台可以继续叠能力，比如 XX/XX/XX（按业务举 2-3 例），你随时说，我批量改一次就能更新上线。" —— 把迭代主动权交给用户，同时暗示攒批改。

## 升级路径（用户问到再展开）

多角色→roles 表化；数据隔离→owner 列服务端过滤；文件上传→files 表 base64（≤5MB）；统计图表→前端读业务表 JS 聚合；导出→CSV 服务端拼串。复杂流水线场景直接切 min-db-workbench skill。
