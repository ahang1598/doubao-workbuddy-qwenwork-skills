# 文件清单索引

本文件列出 `1688-product-manage` 技能目录下所有关键文件及其用途，方便快速定位。

## 目录总览

```
1688-product-manage/
├── SKILL.md                          # 技能主文件：导航、规则、触发词、索引
├── cli.py                            # 统一 CLI 入口（所有命令均通过此脚本执行）
├── requirements.txt                  # Python 依赖（requests、Pillow）
├── references/                       # 参考文档目录
│   ├── apis/                        # API 接口定义文档（跨能力复用）
│   │   ├── ai_publish_by_imageurl.md                # AI 发品识图识别接口
│   │   ├── ai_publish_save_tair.md                  # 保存选品数据接口（Tair）
│   │   ├── cbu_offer_query_tool.md                  # 商品基础信息查询
│   │   ├── cbu_image_analyse_tool.md                # 图片解析（提交+轮询）
│   │   ├── cbu_image_generation_and_editing_tool.md # 图片生成（图生图）
│   │   ├── cbu_skill_change_main_image.md           # 修改商品主图
│   │   ├── cbu_skill_change_subject.md              # 修改商品标题
│   │   ├── image_bank_change_url_for_offer.md       # 图片 URL 转换
│   │   ├── image_bank_upload_picture.md             # 图片银行上传图片
│   │   ├── prompt_editor_html.md                    # Prompt 编辑器 HTML 模板
│   │   └── publish_select_same_html.md              # 批量发品同款勾选 HTML 模板
│   ├── capabilities/                 # 各能力详细实现文档
│   │   ├── configure.md              # AK 认证配置详细流程
│   │   ├── product_publish.md        # AI 智能发品完整指引
│   │   ├── ai_title_modify.md        # AI 标题优化详细步骤
│   │   ├── ai_image_improve.md       # AI 主图优化详细步骤
│   │   ├── intent_matching.md        # 意图泛化兜底机制（模糊匹配/Guardrails/日志规范）
│   │   ├── product_cancel_offer.md   # 商品下架操作指南
│   │   └── product_repost_offer.md   # 商品上架操作指南
│   └── file-index.md                 # 本文件：完整文件清单
├── scripts/                          # 核心源码目录
│   ├── cli.py                        # CLI 路由与参数解析
│   ├── _auth.py                      # AK 签名认证（HMAC-SHA256）
│   ├── _http.py                      # HTTP 客户端（自动签名 + userId 注入）
│   ├── _const.py                     # 全局常量（BASE_URL、超时配置）
│   ├── _output.py                    # 统一输出格式化
│   ├── _tracker.py                   # 埋点上报
│   ├── _errors.py                    # 错误码定义
│   ├── authorize.py                  # OAuth 浏览器授权流程
│   ├── callback_server.py            # 本地回调服务器
│   ├── token_manager.py              # AK 令牌管理
│   ├── encrypted_store.py            # 加密存储
│   ├── secure_store.py               # 安全存储
│   ├── env_writer.py                 # 环境变量写入
│   ├── pkce.py                       # PKCE 安全校验
│   ├── ak_crypto.py                  # AK 加密工具
│   ├── scope_manager.py              # 权限范围管理
│   └── capabilities/                 # 各能力实现
│       ├── configure/                # AK 配置能力
│       │   ├── cmd.py                # CLI 命令入口
│       │   └── service.py            # 业务逻辑
│       ├── get_ak/                   # AK 浏览器自动获取
│       │   └── cmd.py                # CLI 命令入口（调用 authorize.py）
│       ├── product_publish/          # AI 智能发品能力
│       │   ├── cmd.py                # CLI 命令入口
│       │   └── service.py            # 业务逻辑
│       ├── ai_title_modify/          # AI 标题优化能力
│       │   ├── cmd.py                # CLI 命令入口
│       │   └── service.py            # 业务逻辑
│       ├── ai_image_improve/         # AI 主图优化能力
│       │   ├── cmd.py                # CLI 命令入口
│       │   └── service.py            # 业务逻辑
│       ├── product_cancel_offer/     # 商品下架能力
│       │   ├── cmd.py                # CLI 命令入口
│       │   └── service.py            # 业务逻辑
│       └── product_repost_offer/     # 商品上架能力
│           ├── cmd.py                # CLI 命令入口
│           └── service.py            # 业务逻辑
└── workspace/.1688-AK/               # AK 存储目录（运行时自动生成）
```

## 按用途分类

### 入口与路由

| 文件 | 用途 |
|------|------|
| `cli.py`（根目录） | 统一 CLI 入口，负责命令路由和参数解析 |

### 认证与授权

| 文件 | 用途 |
|------|------|
| `scripts/_auth.py` | AK 签名认证，生成 x-csk-sign |
| `scripts/authorize.py` | OAuth 浏览器授权流程 |
| `scripts/callback_server.py` | 本地回调服务器（监听 10000~10009） |
| `scripts/token_manager.py` | AK 令牌生命周期管理 |
| `scripts/encrypted_store.py` | 加密存储 AK 数据 |
| `scripts/secure_store.py` | 安全存储抽象层 |
| `scripts/pkce.py` | PKCE 安全校验 |
| `scripts/ak_crypto.py` | AK 加解密工具 |

### HTTP 与通信

| 文件 | 用途 |
|------|------|
| `scripts/_http.py` | HTTP 客户端：自动签名、userId 注入、错误处理 |
| `scripts/_const.py` | 全局常量：BASE_URL、超时配置等 |

### API 接口文档

| 文件 | 用途 |
|------|------|
| `apis/cbu_offer_query_tool.md` | 商品基础信息查询接口定义 |
| `apis/cbu_image_analyse_tool.md` | 图片内容解析接口定义（提交+轮询） |
| `apis/cbu_image_generation_and_editing_tool.md` | 图片生成（图生图）接口定义 |
| `apis/image_bank_change_url_for_offer.md` | 图片 URL 转换（图片银行）接口定义 |
| `apis/image_bank_upload_picture.md` | 图片银行上传接口定义（本地图片上传至图片银行） |
| `apis/cbu_skill_change_main_image.md` | 修改商品主图接口定义 |
| `apis/cbu_skill_change_subject.md` | 修改商品标题接口定义 |
| `apis/ai_publish_by_imageurl.md` | AI 发品识图识别接口定义（图片URL → 候选商品） |
| `apis/ai_publish_save_tair.md` | 保存选品数据接口定义（候选缓存至 Tair） |
| `apis/prompt_editor_html.md` | Prompt 编辑器 HTML 模板与交互协议 |
| `apis/publish_select_same_html.md` | 批量发品同款勾选 HTML 模板与交互协议 |

### 能力与业务

| 目录 | 能力 | 文件 |
|------|------|------|
| `scripts/capabilities/configure/` | AK 认证配置 | `cmd.py`, `service.py` |
| `scripts/capabilities/get_ak/` | AK 浏览器自动获取 | `cmd.py` |
| `scripts/capabilities/product_publish/` | AI 智能发品 | `cmd.py`, `service.py` |
| `scripts/capabilities/ai_title_modify/` | AI 标题优化 | `cmd.py`, `service.py` |
| `scripts/capabilities/ai_image_improve/` | AI 主图优化 | `cmd.py`, `service.py` |
| `scripts/capabilities/product_cancel_offer/` | 商品下架 | `cmd.py`, `service.py` |
| `scripts/capabilities/product_repost_offer/` | 商品上架 | `cmd.py`, `service.py` |

### 能力文档（references/capabilities/）

| 文件 | 用途 |
|------|------|
| `capabilities/configure.md` | AK 认证配置详细流程 |
| `capabilities/product_publish.md` | AI 智能发品完整指引（含批量发品） |
| `capabilities/ai_title_modify.md` | AI 标题优化详细步骤 |
| `capabilities/ai_image_improve.md` | AI 主图优化详细步骤（含 Prompt 编辑器） |
| `capabilities/intent_matching.md` | 意图泛化兜底机制（模糊匹配 / Guardrails / 日志规范） |
| `capabilities/product_cancel_offer.md` | 商品下架操作指南 |
| `capabilities/product_repost_offer.md` | 商品上架操作指南 |

### 状态与数据

| 文件/目录 | 用途 |
|-----------|------|
| `workspace/.1688-AK/` | AK 数据持久化存储目录 |
| `.publish_state.json` | 发品流程状态缓存（自动生成） |
| `.title_state.json` | 标题优化状态缓存（自动生成） |
| `.image_state.json` | 主图优化状态缓存（自动生成） |
| `.batch_publish_state.json` | 批量发品识图状态缓存（自动生成） |

## 阅读路径建议

1. **首次接触本技能**：先阅读 `SKILL.md` 了解整体架构和规则
2. **准备执行某项能力**：根据 `SKILL.md` 中的索引阅读 `references/capabilities/` 下对应文档
3. **需要了解文件用途**：查阅本文件（`references/file-index.md`）
4. **调试或二次开发**：查看 `scripts/` 下对应能力的 `cmd.py` 和 `service.py`
