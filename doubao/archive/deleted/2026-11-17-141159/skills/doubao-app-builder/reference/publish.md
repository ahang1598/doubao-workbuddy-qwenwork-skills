# 发布到妙搭平台

把本地产物发布成一个线上可访问的应用。**产物托管形态**：代码留在本地，产物上传平台，由平台负责分发与路由。

## 何时读本文

**默认不发布。** 开发完成的正常交付按链路走：**webapp** 启动本地服务、把 localhost 地址交给用户（见 [`webapp-develop.md`](webapp-develop.md)「交付与发布」）；**html** 直接把产物文件交给用户（见 [`html-develop.md`](html-develop.md)）。到此为止。

**只有用户明确要求发布 / 托管 / 拿线上可访问链接时**才读本文并执行发布——「帮我发布上线」「部署一下」「给我个能分享的链接」这类。

**用户开口让你发，你就直接发。** 这句话本身即授权，不用再问一遍要不要发（**唯一例外见第八节：`app_id` 不是本会话写入的，要先确认再发**——那是防止覆盖别人线上应用，优先级高于本条），**更不要把用户推回去让他自己点按钮**。

🔴 **说「重新发布」「再发一次」就真的再发一次**，哪怕这一轮你没改过任何代码。**你看不见用户在编辑器里的手动改动**——他可能自己调了文案、换了图、改了配置，然后让你把最新的产物发上去。**以「对话里没有变化」为由跳过发布是错的**：发布读的是磁盘上的当前文件，不是你记忆里的那一版。迭代重发的成本很低——webapp 工程零参数 `+deploy` 就行，html 产物把首发那条命令加上 `--app-id` 再跑一次——宁可多发一次。

发布有两条路，都可用：用户可以自己在预览界面点发布按钮，你也可以用下面的命令直接发。**这两条路只是入口不同，不是谁替代谁**——用户没提发布就都不做，用户让你发就你来发，用户说他自己发就别抢。

**两条链路的发布出口都是本文，但走的不是同一条路**：html 产物（单文件 / 静态目录）用 `+deploy --file-path` / `--dir` **一条命令直发**，不用准备任何配置文件；webapp 工程（有构建）仍走 `spark.json` 那一套。先按第一节认准自己是哪种，别把 webapp 的准备工作套到 html 上。

🔴 **`app_builder_agent` 链路的产物不走本文**（`arch_type=jspage` / `fullstack`）：那些产物在它的沙箱里，你没有代码也没有发布权限，本文的命令对它们全部无效。用户问发布时：**`jspage` 已经自动发布了，告诉用户不用发**；**`fullstack` 要用户自己去开发页面点发布按钮**。你在那条链路上不执行任何发布动作。

全栈应用目前发不了，见第十节。**改可用范围 / 访问权限、导出应用代码不在本文**，见 [`app-manage.md`](app-manage.md)。

> 运行时命令事实以 `lark-cli apps <命令> --help` 为准，本文写的是流程与协议，命令签名以 CLI 自述为准。

---

## 一、先判断：你的产物走哪条路

🔴 **先认产物是什么，再去看有没有 `spark.json`。** html 产物本来就没有这个文件，**别照着下表最后一行判成「发不了」**——它说的是 webapp 工程。

| 产物 | 怎么发 |
|---|---|
| **html 产物**（单文件 `index.html` / 静态目录，无构建） | ✅ **什么都不用准备**——看 2.1，一条命令的事 |
| **webapp 工程**，`spark.json` 的 `stack` 是 `react-standard-webapp`（官方脚手架初始化的） | ✅ **直接发**，跳到第六节；**但工程里有本地资源文件时先过第四节**（见下方例外） |
| **webapp 工程**，有 `spark.json` 但 `stack` 是 `custom-*` | ⚠️ 先过一遍第三节的清单，缺什么补什么 |
| **webapp 工程**，没有 `spark.json` | ❌ 先按第二、三节改造，写出合规的 `spark.json` |

官方模板能直接发，是因为它的 `vite.config.ts` 和构建脚本已经把协议要求的东西都实现好了（base path 注入、CDN 前缀、routes.json 生成）。**其他工程要自己补上这些**——平台不会替你猜。

⚠️ **一条例外，官方模板也躲不掉**：工程里只要有靠 dev server 加载的本地资源文件（用户给的 csv / xlsx / json、pdf、本地字体等），**无论用不用官方模板都要过第四节**。模板替你处理的是构建配置，不会替你检查「你把文件放对地方了没有、路径写对了没有」。

---

## 二、发布方式：html 直发 vs webapp 工程

两种产物的准备工作完全不同：html 产物走 2.1，一条命令发完；webapp 工程走 2.2 起的 `spark.json` 那套。

### 2.1 html 产物：一条命令发完

单文件或静态目录，**不用准备任何配置文件、不用起服务、不构建**，也不会在本地落下任何东西：

```bash
# 资源引用都是静态写死的 → 指到入口 html，依赖自动跟着走
lark-cli apps +deploy --file-path ./index.html

# 有扫不出来的资源引用 → 必须发整个目录
lark-cli apps +deploy --dir ./site                          # 目录根有 index.html，它就是入口
lark-cli apps +deploy --dir ./site --entry-file home.html   # 目录根没有 index.html 时指定
```

🔴 **选命令前先判断一件事：页面里有没有「扫不出来的资源」。**

`--file-path` 靠**静态扫描**收集依赖：`<link>`、`<script src>`、`<img src|srcset>`、CSS 的 `url()` 与 `@import`、JS 的 `import` / `fetch()` / `new Worker` / `new URL(…, import.meta.url)` 都在范围内，写死的路径它都能找到。

但**运行时才拼出来的路径它一律扫不到**——`'./img/' + name + '.png'`、从数据里读出来的文件名、模板字符串拼的地址。这些资源不会进包，页面上线后那一块就是碎图或空白，**而且本地打开一切正常，你不去线上点根本发现不了**。

🔴 **只要页面里有这类拼接引用，就必须用 `--dir` 整目录发。** 别赌扫描能覆盖到。

🔴 **入口必须是确定的**：用 `--file-path` 时它指的就是入口；用 `--dir` 时，目录根有 `index.html` 它就是入口，没有就**必须**带 `--entry-file`。**不要在没确认目录根有什么的情况下裸跑 `--dir`**——入口给不出来会直接报 `no entry file`。

`--file-path` 的额外好处是**只打包被引用到的文件**，`_backup/`、`scratchpad.md` 这类草稿压根进不了包；`--dir` 是整目录原样上传（跳过 `.git` 子树，不跟随符号链接），所以下面清理那条对它特别重要。

`--entry-file` 只收 `--dir` 的直接子文件名（不含 `/`、须 `.html`），发布产物里会被改名为 `index.html`——只改产物，不动磁盘上的原文件。入口在子目录里时把 `--dir` 直接指到那一层，不要在 `--entry-file` 里写路径。⚠️ **目录根已经有 `index.html` 时不要再带 `--entry-file`**，两个入口会报 `entry conflict`。

🔴 **路径一律相对当前目录，绝对路径会被拒**——产物不在 cwd 下就先 `cd` 过去。

🔴 **页面里引资源用相对路径**（`./img/x.png`、`assets/app.css`），**别用 `/` 开头的裸根路径**。应用挂在 `/app/<app_id>/` 下，`/img/x.png` 会打到域名根、必然 404，本地打开时却一切正常，最容易骗过自己。

🔴 **复发布必须带上一次返回的 `--app-id`。** 不带的话，幂等标识是入口文件的**绝对路径**：用户改个文件名、挪个目录，或者你换了 cwd，都会**悄悄新建一个应用**而不是更新原来那个。这条链路不回写任何本地文件，**首次拿到的 app_id 当场记下来**，丢了就找不回来了。

**要自定义应用名就先建再发**：`lark-cli apps +create --name "<应用名>" --app-type html`，拿到 app_id 再 `+deploy --app-id`。直接发的话应用名取入口文件名去扩展名（`report.html` → `report`，入口是 `index.html` 时取父目录名），用户在应用列表里认不出来。

🔴 **用 `--dir` 时先删掉目录里的非交付文件**：`_backup/`（版本备份）、`scratchpad.md`（大纲草稿）、`.DS_Store`。「不属于交付产物」指的是不交给用户看，**不等于不会被打包**——整目录上传，`_backup/index-v1.html` 会变成一条真实线上路由，草稿也跟着公网可达。拿不准就先 `--dry-run` 看一眼实际待发文件清单，它不发任何写请求。（走 `--file-path` 没这个问题，没被引用的文件不会进包。）

发用户提供的 HTML 成品同样走这条，不用为它准备任何声明文件。发完直接跳 6.1 的「输出契约」看怎么轮询取地址——**6.0 那道 dev server 前置门是 webapp 的，与你无关**。下面 2.2 起也都是 webapp 工程用的。

### 2.2 webapp 工程

`+deploy` 靠 `spark.json` 知道「产物在哪、要不要构建」，**没有这个文件就发不了**。标准 JSON（不是 JSONC、不是 TOML），放在项目根：

```json
{
  "stack": "custom-webapp",
  "dev":   { "command": ["npm", "run", "dev"], "port": 31207 },
  "build": { "command": ["npm", "run", "build"], "output": "dist" }
}
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `stack` | ✅ | 自定义工程一律填 `custom-webapp` |
| `dev.port` | ✅ | 本地 dev 端口，**填你这次实际起服务用的那个**（示例里的数字只是占位，别照抄）。`+deploy` 要靠 `GET localhost:<port>/spark.json` 验证身份（见 §6.0），**不写发不了**（除非 `--no-verify`） |
| `dev.command` | ⬜ | 本地启动命令，缺省回退 `npm run dev` |
| `build.command` | ⬜ | 构建命令 argv 数组。**不写 = buildless**，跳过构建直接打包产物目录 |
| `build.output` | ⬜ | **同源产物目录**，缺省 `dist/output`；纯静态项目常填 `"."` |
| `build.output_cdn` | ⬜ | CDN 产物目录，不写就是全同源（够用，别为了写而写） |
| `app.id` | 首发前 ✅ | **`+create` 拿到后由你手写进来**（见 6.1 第②步），没有它发布过不去 |
| `app.online_url` | ❌ | 状态区，发布成功后由 CLI 回写——见第七节，不要手工编辑 |

三个 `build` 字段互相正交：`command` 的有无只决定跳不跳构建，**不改变目录字段的含义**。

⚠️ **「我这个是纯静态目录」不是用这份声明的理由**——你自己产出的静态目录一律回 2.1 一条命令直发。下面这份最小声明只给**用户已有的、要靠 dev server 跑起来的手工工程**：

```json
{ "stack": "custom-webapp", "dev": { "command": ["npx","serve","-l","24680"], "port": 24680 }, "build": { "output": "." } }
```

`dev.port` 省不掉——发布时要靠它验证本地自描述端点。这里的 24680 同样是占位，换成你实际起服务的端口，两处保持一致。

---

## 三、webapp 工程：改造到符合协议

用官方脚手架初始化的工程这些都已经做好了，**跳过本节**。手工搭的、或用户已有的工程要自己补上——平台不会替你猜。

### 3.1 构建期要消费两个环境变量

发布时平台在执行 `build.command` 前注入：

| 变量 | 含义 | 工程侧义务 |
|---|---|---|
| `MIAODA_CLIENT_BASE_PATH` | 应用根路径（形如 `/app/app_xxx`） | 客户端路由 base **必须**设为该值，**不许**自己拼接推导；缺省回退 `/` |
| `MIAODA_RESOURCE_CDN_PREFIX` | CDN 前缀 | 声明了 `build.output_cdn` 时静态资源必须带此前缀；缺省回退 base path |

**两个都必须有回退**——本地不带环境变量时 `dev` 和 `build` 也要能跑通。除这两个之外不要假设任何其他 `MIAODA_*` 变量存在（平台不注入 `MIAODA_APP_ID`）。

### 3.2 产物目录要满足的约束

`build.output` 指向的目录：

- **至少一个 `.html`**，SPA 入口必须叫 `index.html`
- **要有 `routes.json`**（见 3.3）
- 其余静态文件（favicon、数据 JSON、图片）随意放，按相对路径直出，页面可同源 fetch
- `routes.json` 是保留文件名，不要拿它当业务文件

`build.output_cdn` 指向的目录会推 CDN、**公网匿名可达**，只放内容寻址（带 hash 文件名）的 JS / CSS / 字体 / 图片，**不许放任何含敏感信息的文件**。

### 3.3 `routes.json`

声明应用全部页面路由，位置 `<build.output>/routes.json`。它是**运行态安全扫描的输入**（平台按路由遍历页面），**漏报即漏扫**。

```json
[
  { "path": "/", "file": "index.html", "name": "首页" },
  { "path": "/orders/:id" }
]
```

- 顶层必须是数组，`path` 以 `/` 开头且**不带** base 前缀、必须去重
- `file` / `name` 可选；SPA 各路由通常都是 `index.html`，多页应用应当填对应文件
- 无路由的纯静态站可以是空数组 `[]`

生成责任：

- **声明了 `build.command`** → 由你的构建过程产出，必须跟实际路由一致
- **buildless** → CLI 打包时扫描 `.html` 文件树自动生成（`foo/index.html → /foo`）；工程自带 `routes.json` 时 CLI 不覆盖

路由要用字面量声明，**动态拼接出来的路由扫不到**。

### 3.4 最高频的翻车点：裸根路径

```html
<!-- ❌ 本地能跑，上线 404 -->
<script src="/assets/main.js"></script>
```

构建期静态引用（HTML 的 `<script src>` / `<link href>`、CSS 的 `url()`）**不许出现裸根路径**——资源在 CDN 目录就带 `MIAODA_RESOURCE_CDN_PREFIX`，在同源目录就指向应用根路径。

🔴 **运行时引用同样不许**（代码里的字符串，如 `fetch('/data.json')`、`<img src="/logo.png">`）。浏览器解析以 `/` 开头的 URL 时相对的是**域名根**，不是应用根——应用挂在 `/app/app_xxx/` 下时，`fetch('/data.json')` 打到 `https://host/data.json`，必然 404。一律用 base 前缀拼。

另外三条禁令：不许在代码或产物里硬编码 base（base 只能来自环境变量）；不许在 `/__runtime__/*` 保留路径下定义业务路由或文件；不许依赖平台注入的浏览器全局（`window.appId` / `window._userInfo` 等属平台内部实现，随时会变）。

### 3.5 改造完的自检清单

发布前逐条过：

- [ ] 零环境变量下执行 `build.command` 退出码为 0，`<build.output>/index.html` 存在（buildless 则目录里直接有 `index.html`）
- [ ] 注入 `MIAODA_CLIENT_BASE_PATH=/app/app_test` 和 `MIAODA_RESOURCE_CDN_PREFIX=https://cdn.example.com/x/` 再构建，HTML 里的 JS/CSS 引用带上了 CDN 前缀（声明了 `output_cdn` 时），bundle 内路由 base 是 `/app/app_test`
- [ ] HTML 里没有裸根路径静态引用
- [ ] 产物里没有未替换的模板占位符字面量
- [ ] **dev 下能读到的本地资源文件，构建后确实出现在 `build.output` 目录里**，且代码里的取用路径带 base 前缀（见第四节）

## 四、本地资源文件：开发态与发布后必须一致

**这一节是 webapp 工程的，用官方脚手架的也不例外**——模板替你处理的是构建配置，不替你检查文件放没放对、路径写没写对。（html 直发没有构建这一步，资源随包上传，不用过本节。）

如果工程里有**靠 dev server 加载的本地资源**（用户给的 csv / xlsx / json、pdf 文档、本地字体等），发布前必须逐个确认它们线上也能读到。**dev server 能吐出来不代表产物里有这个文件。**

逐条核：

1. **在产物里**：手跑一次 `npm run build`，去 `build.output` 目录里**实际确认这些文件存在**——不是假设构建工具会拷贝，是打开目录看。构建工具只会拷它认的那个静态目录，放错地方的文件会被静默丢掉。

   ℹ️ 开发阶段那条「不用专门跑构建」在这里不适用：**有本地资源文件时，这是唯一需要你手跑一次 build 的场景**，因为 `+deploy` 内部的构建不给你看产物的窗口，而文件有没有被拷进去只能打开目录才知道。没有本地资源文件的工程照旧不跑。
2. **路径能命中**：代码里的取用路径用了 base 前缀，不是裸绝对路径。线上应用挂在 `/app/<appId>/` 下，裸 `/data/x.csv` 必然 404。
3. **没进 CDN 目录**：`build.output_cdn` 公网匿名可达，用户的业务数据放这里等于公开。除非确定可公开，一律放同源的 `build.output`。
4. **失败有兜底**：读不到 / 解析失败要有可见的错误态，不能白屏、也不能静默显示空列表——线上出问题时用户得知道是数据没读到。

以上四条都是**发布前**在代码里自查的，发布后不再重复（见第七节）。

---

## 五、静态资源：默认不用管，只有产物目录外的才手工传

**html 直发已经把这件事办了**：`--file-path` 自动爬取页面引用的本地依赖，`--dir` 整目录原样打包——两种模式下本地图片、字体、css、js 都会随包上线，**不需要先上传再替换链接**。

**扫不出来的资源也不用手工传**——那种情况按 2.1 的规则改用 `--dir` 整目录发就解决了，目录里的文件原样上传，不存在扫不扫得到的问题。

**资源不在产物目录里就先复制进来**，用相对路径引——这是本链路的资源规则（见 [`html-develop.md`](html-develop.md)），不是绕去上传的理由。

只有文件大到不适合随包（单个几十 MB 以上），或者用户明确要走文件存储时，才用手工上传：

- `lark-cli apps +file-upload --app-id <app_id> --file <相对路径>`（要先有 app_id），把代码里的引用换成返回的 `download_url`。**不要用 `+file-sign` 返回的 `signed_url`**——签名链接有有效期。
- **资源链接按 `app_id` 隔离**：不要跨应用复用 `download_url`，换应用发布时同一个文件要重传。

---

## 六、发布

### 6.0 🔴 前置门：dev server 必须在跑，且能吐出 `/spark.json`

⚠️ **本节只对 webapp 工程有效。** html 直发（`--file-path` / `--dir`）没有这道门，不用起任何服务——看完 2.1 直接跳 6.1 的输出契约。

`+deploy` 会去验证 **`GET localhost:<dev.port>/spark.json`**——这个端点不可达，发布直接失败。所以**发布前先确认本地 dev server 还开着**（正常交付流程里它本来就该在跑，见「交付与发布」的第一步）。

- **用官方模板不用做任何事**：模板已经内置了这个 `/spark.json` 自描述端点，起了 dev server 就有。
- **手工搭的工程要自己实现**：让 dev server 在 `/spark.json` 路径上伺服项目根的那份 `spark.json` 实时内容（不是拷贝一份静态副本——你把 `app.id` 写进去后要能立刻读到新值）。
- `spark.json` 的 `dev.port` **必填**，它就是这个端点的端口。端口以 dev server 终端实际输出的为准，被占用时会顺延。**正常流程里起服务那一步就该把它改成实际端口了**（见 [`webapp-develop.md`](webapp-develop.md)「交付与发布」）；走到这里才发现两边不一致，说明那步漏了。

**验证逻辑**：端点要可达，且它返回的 `app.id` 与本次部署目标一致。所以 `+create` 之后**必须先把 app_id 写进 `spark.json`**（见 6.1 第②步）再发——漏了这步，端点吐不出 `app.id`，这道门就过不去。写完**不用重启 dev server**，端点伺服的是实时文件，迭代重发时身份比对自然通过。

🔴 **自查这个端点一律用 `localhost`，不要用 `127.0.0.1`**——vite dev server 默认只监听 IPv6（`::1`），IPv4 的 `127.0.0.1` 访问不通，会让你误判成「服务没起」而白排查一轮。

⚠️ **端点验证失败时不要顺手加 `--no-verify` 重试。** 先判断是哪种情况：

| 报错 | 说明 | 怎么办 |
|---|---|---|
| `the local self-description endpoint is unavailable` | dev server 没起，或端口不对 | 先把 dev server 起起来；确实是无头 / CI 环境才用 `--no-verify` |
| `dev server ... declares app X, but this deploy targets app Y` | **发错目录**，或那个端口上跑着别的项目 | 这是强信号，**停下告知用户**，绝不要用 `--no-verify` 绕过 |

### 6.1 建应用、发布、查状态

**html 产物**用 2.1 的 `--file-path` / `--dir` 直发，命令不在这里重复。下面是 **webapp 工程**的：

```bash
# ① 建应用拿 app_id（webapp 工程的 --app-type 是 frontend，不是 html）
lark-cli apps +create --name "<应用名>" --app-type frontend --description "<一句话>"

# ② 🔴 把拿到的 app_id 手写进 spark.json —— 这一步不能跳，漏了发布过不去
#    { "stack": …, "dev": …, "build": …, "app": { "id": "app_xxx" } }

# ③ 发布（必须在含 spark.json 的项目根执行）
lark-cli apps +deploy --app-id <app_id>    # 首次
lark-cli apps +deploy                      # 迭代重发，零参数，读 spark.json 里的 app.id
```

🔴 **第②步是硬前提，不是可选的润色。** `+deploy` 的前置门要拿 dev server 端点返回的 `app.id` 跟本次部署目标比对，`spark.json` 里没有 `app.id` 就比不上、直接失败。写完**不用重启 dev server**——端点伺服的是文件实时内容。

- **在哪执行就发哪个目录**：`cd` 到含 `spark.json` 的产物目录再跑 `+deploy`，目录内全部文件随包上传。**不要在工作区根目录、用户主目录、仓库根目录执行**——那会把整棵树打进去。
- 应用名从项目主题生成，**不要让用户手动提供 app_id**。
- 返回的 `app_id` 以 `app_` 开头；`cli_` 开头的是飞书应用 ID，**绝不能**传给 `apps +*` 命令。
- **agent 来源标识**：豆包沙箱由环境自动注入 `LARKSUITE_CLI_AGENT_NAME=doubao_moa`，不用管。在其他环境手工执行时必须带上它，否则应用建出来了、`+deploy` 会因为拿不到上传凭据而失败（报 `pre_release kvs missing artifact_url`，这时要重新 `+create` 一个应用，改不了旧的）。
- `+deploy` 内部流程：取上传凭据与构建变量 → 执行 `build.command`（buildless 跳过）→ 校验产物 → 归一化打包 → 上传 → 触发发布。

**输出契约**（两条路都适用；`online_url` 是唯一可信的线上地址来源，拿到当场记下）：

- 命令**受理后立即返回、不原地等待**。同步完成 → 直接返回 `data.online_url`
- 发布中 → 返回 `data.release_id`，用 `lark-cli apps +release-get --app-id <app_id> --release-id <release_id>` 轮询（间隔 ≥ 3s），`status=finished` 后读 `online_url`
- 🔴 **只有本轮轮询到 `finished` 才算发成了。** `is_published=true` 只代表这个应用历史上发布过，不代表你这次的代码已经上线——不要拿它或 `+list` 的结果当「已上线」的凭据。
- **流水线失败 = 发布失败**：exit 非 0，报错里带各 step 的 `error_logs` 摘要；产物已上传，修完重新 `+deploy`

**执行注意**：`+deploy` 含构建，可能跑几十秒。在有前台超时的环境里被转入后台**不是失败**——等命令真正结束、读到 JSON 结果再行动，**结果没读到前不要重复执行**。

---

## 七、发布之后：拿到地址、交给用户

🔴 **发布完成后不做任何检查**——不打开线上地址、不截图、不预览、不抓取页面验证功能。**发布命令返回成功就是成功**，把地址交给用户，这一轮到此结束。前面那些自查都是发布前在代码里做的，发布后不重复。

🔴 **html 直发不回写任何本地文件**——`app_id` 和 `online_url` 只存在于命令返回值里，**当场记下来**，复发布和交付都要用。下面这段回写只对 webapp 工程。

**字段分工**：`stack` / `dev` / `build` 是**声明区**（你写）；`app` 段是**状态区**，记录这个工程发到了哪个应用。

### `+deploy` 之后：CLI 会回写，你负责确认并交出地址

`app.id` 是你在发布前手写进去的（见 6.1 第②步）；**发布成功后 CLI 再回写 `app.online_url`**：

```json
{
  "stack": "react-standard-webapp", "dev": { }, "build": { },
  "app": {
    "id": "app_17d096r2xqp",
    "online_url": "https://bytedance.feishuapp.cn/app/app_17d096r2xqp"
  }
}
```

⚠️ 字段名是 **`app.online_url`**（不是 `app.url`）。`app.id` 供迭代重发时零参数 `+deploy` 找到目标应用。

你要做的两件事：

1. **确认回写生效**（webapp 工程；html 直发跳过这条）：读一遍 `spark.json`，`app.online_url` 有值。万一没写上（异常情况），用命令返回的 `data.online_url` 补进去——**以返回值为准，不要自己拼**。
2. **把这个 URL 交给用户**：用 `present_files` 交付这个链接（细则见下方「交付形式」）。

### 🔴 发布成功后，MUST 把线上地址交给用户

**两条链路都一样，没有例外**：首次发布要发，迭代重发也要发；用户问了要发，没问也要发。发布成功却没把地址交出去，等于没发布。

#### 地址只能来自命令返回值，**严禁自己拼**

发布地址取命令返回的 `data.online_url`（发布中的情况，轮询到 `status=finished` 后再取 `online_url`）。**拿到就立刻记下来**，后面交付要用。

🔴 **严禁按 `app_id` 拼 URL**。域名不是固定的——同一个账号下既有 `bytedance.feishuapp.cn/app/<app_id>`，也有 `bytedance.aiforce.cloud/app/<app_id>`，还可能有别的。**拼出来的链接看着像真的，点开是错的**，这是本链路最容易骗过自己的一个错。

- ❌ `https://bytedance.feishuapp.cn/app/${app_id}` —— 凭 app_id 套模板拼出来的
- ❌ 从别的应用的链接改个 app_id 得到的
- ✅ 命令返回的 `online_url` 原样使用，一个字符都不改

**隔了很多轮、返回值已经不在手边时**：webapp 工程先读 `spark.json` 的 `app.online_url`（CLI 发布时已回写）；**html 直发没有这个文件**，直接用 `lark-cli apps +list` 查对应 `app_id` 那条记录的 `online_url`。

都拿不到就**如实告诉用户没取到线上地址**，让他到平台查看。**不要因为拿不到就去拼一个** —— 给错链接比说「没拿到」糟得多。

#### 🔴 交付形式：用 `present_files` 交付链接

发布成功后，**这一轮唯一要做的交付动作**是通过 `present_files` 工具把链接发送出来：`source` 填命令返回的 `online_url`、`name` 给短标题。

正文只用一两句讲清这是什么、做了哪些范围、有什么未实现项，**不要再重复贴一遍链接**——卡片本身就能点开。这一轮也不要再交付产物文件（`index.html`、工程目录之类），产物已经在线上跑着，传文件是把输入当结果交，还会多推一张卡片。

⚠️ **迭代重发后同样要重新交付一次**，哪怕线上地址跟上一轮一模一样——不能让用户回头去翻上一张卡片。

#### 可见范围是另一套东西

`+deploy` 只把产物推上去，**谁能打开这个应用它完全不碰**。发布后的 `online_url` 默认不是公开链接——匿名打开会跳飞书登录页。

🔴 **发布完的下一个问题多半就是权限**（「别人打不开」「怎么设成公开」）。那一刻**先读 [`app-manage.md`](app-manage.md) 再回答**，别凭印象说「CLI 改不了，你去平台设置」——改得了。那边统一走 `drive` 域 + `meta_token`；放开到什么程度**由用户选，别替他定**。

---

## 八、安全与确认

- **敏感文件扫描命中时不要自动加 `--allow-sensitive` 重试。** 按文件名扫的是这一类：`.env` / `.env.*`、`.npmrc`、`.netrc`、`id_rsa` 等私钥、`*.pem` / `*.p12` / `*.pfx` / `*.keystore`、`credentials`、`service-account.json`（大小写不敏感）。默认动作是**把这些文件移出发布范围**——删掉，或者把 `--dir` 收窄到只含站点那一层。`--allow-sensitive` 会跳过整道扫描，而产物是公网可分享链接，**误放行等于把凭证发上公网**；只有确认这就是要公开的页面内容才用，用之前先问用户。`--dry-run` 命中同样非零退出，别拿它绕。
- **`app_id` 不是本会话拿到的**（来自历史文件、别人的仓库，或用户直接贴给你的）时，发布前把目标 app_id 告知用户确认——**发布会覆盖那个应用的线上内容**。两条路都适用。
- webapp 工程另外注意：`--app-id` 与 `spark.json` 记录不一致会被拒绝（防误发错目标），确要切换先更新 `spark.json`。
- 命令失败时转述 `error.hint`，不要把 JSON envelope 原样甩给用户。

---

## 九、常见失败

涉及 `spark.json`、dev server、构建产物、`routes.json` 的那几条只会在 **webapp 工程**上出现；建应用与发布流水线相关的（`pre_release kvs`、`no publish target`、`release failed`）两条路都会遇到。

| 报错 | 处理 |
|---|---|
| `the local self-description endpoint is unavailable` | dev server 没起或端口不对——先起服务；确认是无头 / CI 才用 `--no-verify` |
| `dev server ... declares app X, but this deploy targets app Y` | 发错目录，或那个端口上是别的项目的 dev server。停下告知用户，别用 `--no-verify` 绕 |
| `missing the required dev.port field` | `spark.json` 里补 `{"dev":{"port": <实际端口>}}`，托管后平台要靠这个端点自描述 |
| `pre_release kvs missing artifact_url` | 建应用时缺 `LARKSUITE_CLI_AGENT_NAME=doubao_moa`，补上后重新 `+create`（改不了旧应用，只能重建） |
| `current directory is not a Miaoda app project` | 不在项目根，`cd` 到含 `spark.json` 的目录 |
| `no publish target` | 先 `+create`，把 app_id 写进 `spark.json`，再带 `--app-id` 发一次 |
| `artifact directory ... does not exist` | 有 `build.command`：先构建；buildless：确认 `build.output` 目录真的存在 |
| `routes.json is missing` | 声明了 `build.command` 的项目要由构建产出它（buildless 会自动生成，不会报这个） |
| `release ... failed`（带 `error_logs`） | 转述失败的 step 与关键错误，修完重新 `+deploy` |
| `no entry file` / `entry conflict` | html `--dir` 的入口没定好，见 2.1 的入口判定表 |
| 路径被拒 | `--file-path` / `--dir` 只收相对当前目录的路径，先 `cd` 到产物所在目录 |

**表里没有的报错照报错信息处理**：命令的 `error.hint` 优先转述，看得懂的自己修、修不了的把原文转述给用户，**不要凭猜测改产物**。体积、大小这类超限被拒时同理——把超限的是哪个文件、差多少如实告诉用户，删还是换由他定，别自己想办法压。

---

## 十、全栈应用目前发不了

本链路只覆盖**纯前端**产物托管。全栈（要真实服务端运行时）目前**没有初始化模板、也无法通过本链路发布**。

用户明确要服务端时：如实告知这条限制，可以引导用户自己用 Express 等在本地起服务端开发，但**产出没法发布到妙搭平台**——不要让用户做完一整个全栈应用才发现发不上去。

全栈的初始化模板与发布能力在排期中。
