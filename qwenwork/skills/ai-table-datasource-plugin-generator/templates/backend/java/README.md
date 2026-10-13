# 数据源插件后端

AI 表格数据源插件的后端服务，基于 Java 17 + Spring Boot 2.7 构建。

## 快速开始

### 1. 安装依赖

```bash
mvn clean install -DskipTests
```

### 2. 配置

编辑 `src/main/resources/application.yml`，配置插件密钥：

```yaml
plugin:
  secret-key: your-secret-key-here        # 与 AI 表格平台约定的签名密钥
  enable-signature-verification: false    # 开发调试时设为 false
```

如需连接外部数据源（如数据库、第三方 API），可在 `backend/` 目录下创建 `.env` 文件：

```properties
# 示例：数据库连接配置
DB_HOST=localhost
DB_PORT=3306
DB_NAME=your_database
DB_USER=root
DB_PASSWORD=your_password
```

### 3. 启动

```bash
mvn spring-boot:run
```

服务默认运行在 `http://localhost:8080`。

## 核心接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/sheet_meta` | POST | 返回数据表结构（字段定义） |
| `/api/records` | POST | 返回数据记录（支持分页） |

## 项目结构

```
src/main/java/com/dingtalk/plugin/
├── ApiApplication.java          # Spring Boot 启动类
├── controller/
│   └── DatasourceController.java  # 数据源 API 控制器
├── datasource/
│   ├── DataSourceConfig.java      # 数据源配置接口
│   ├── DataSourceRegistry.java    # 数据源注册表
│   ├── DemoDataSourceConfig.java  # 示例数据源配置
│   ├── FieldDefinition.java       # 字段定义
│   └── FieldValueBuilder.java     # 字段值构建器
├── filter/
│   └── RequestLoggingFilter.java  # 请求日志过滤器
├── model/
│   ├── ApiResponse.java           # 通用响应格式
│   ├── RecordsRequest.java        # 记录请求模型
│   ├── RecordsResponse.java       # 记录响应模型
│   ├── SheetMetaRequest.java      # 表结构请求模型
│   └── SheetMetaResponse.java     # 表结构响应模型
├── service/
│   ├── RecordService.java         # 数据记录服务
│   └── SheetMetaService.java      # 表结构服务
└── util/
    └── SignatureUtil.java         # 签名工具类
```

## 开发指南

### 添加新数据源

1. 在 `datasource/` 下创建新的 Config 类，实现 `DataSourceConfig` 接口
2. 在 `DataSourceRegistry` 的 static 块中注册
3. 在 `RecordService` 中添加对应的数据获取逻辑

### 签名验证

- 开发调试时在 `application.yml` 中设置 `plugin.enable-signature-verification: false`
- 生产环境必须开启签名验证，密钥通过环境变量 `PLUGIN_SECRET_KEY` 注入

## 技术栈

- Java 17
- Spring Boot 2.7.18
- Maven
- FastJSON（签名算法依赖）
- OkHttp（第三方 API 调用）
- Lombok
