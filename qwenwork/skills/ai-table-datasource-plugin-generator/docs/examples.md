# 使用示例

本文档提供完整的使用示例，帮助你快速上手。

## 示例 1：创建 MySQL 数据源插件

### 场景描述
创建一个连接 MySQL 数据库的数据源插件，同步用户表数据到 AI 表格。

### 实现步骤

#### 1. 初始化项目

```bash
# 使用 Aone Copilot
创建一个 MySQL 数据源插件，名称为：用户数据源

# 或直接运行脚本
python3 scripts/init_plugin.py --name "user-datasource" --type mysql
```

#### 2. 配置数据库连接

编辑 `backend/src/main/resources/application.yml`：

```yaml
plugin:
  secret-key: my-secret-key-123456
```

#### 4. 启动服务

```bash
# 配置开发环境
python3 scripts/setup_dev.py --name "user-datasource" --project-dir user-datasource-plugin --install

# 启动后端
./scripts/start-backend.sh

# 启动前端（新终端）
./scripts/start-frontend.sh

# 配置内网穿透（新终端）
cloudflared tunnel --url http://localhost:8080
```

#### 5. 在 AI 表格中测试

1. 打开钉钉 AI 表格
2. 进入数据连接中心
3. 选择自定义数据源
4. 填写配置：
   - 主机：localhost
   - 端口：3306
   - 数据库：mydb
   - 用户名：root
   - 密码：password
   - 表名：users

## 示例 2：创建 PostgreSQL 数据源插件

### 场景描述
创建一个连接 PostgreSQL 数据库的数据源插件。

### 实现步骤

#### 1. 初始化项目

```bash
python3 scripts/init_plugin.py --name "postgresql-datasource" --type postgresql
```

#### 2. 自定义字段映射

如果需要自定义字段类型映射，编辑 `backend/src/main/java/com/dingtalk/plugin/service/SheetMetaService.java`：

```java
// 添加自定义类型映射
case Types.ARRAY:
    field.setType("text");
    field.setProperty("{\"formatter\":\"JSON\"}");
    break;
```

## 示例 3：创建自定义 API 数据源插件

### 场景描述
创建一个从第三方 API 获取数据的插件。

### 实现步骤

#### 1. 初始化项目

```bash
python3 scripts/init_plugin.py --name "api-datasource" --type custom
```

#### 2. 实现自定义逻辑

编辑 `backend/src/main/java/com/dingtalk/plugin/service/SheetMetaService.java`：

```java
@Service
public class SheetMetaService {

    @Autowired
    private RestTemplate restTemplate;

    public SheetMeta getSheetMeta(Map<String, Object> config) {
        String apiUrl = (String) config.get("apiUrl");
        String apiKey = (String) config.get("apiKey");
        
        // 调用第三方 API
        HttpHeaders headers = new HttpHeaders();
        headers.set("Authorization", "Bearer " + apiKey);
        HttpEntity<String> entity = new HttpEntity<>(headers);
        
        ResponseEntity<ApiResponse> response = restTemplate.exchange(
            apiUrl + "/schema",
            HttpMethod.GET,
            entity,
            ApiResponse.class
        );
        
        // 转换为 SheetMeta
        return convertToSheetMeta(response.getBody());
    }
    
    private SheetMeta convertToSheetMeta(ApiResponse apiResponse) {
        SheetMeta sheetMeta = new SheetMeta();
        sheetMeta.setName(apiResponse.getTableName());
        
        List<Field> fields = new ArrayList<>();
        for (ApiField apiField : apiResponse.getFields()) {
            Field field = new Field();
            field.setName(apiField.getName());
            field.setType(mapFieldType(apiField.getType()));
            fields.add(field);
        }
        
        sheetMeta.setFields(fields);
        return sheetMeta;
    }
    
    private String mapFieldType(String apiType) {
        switch (apiType) {
            case "string": return "text";
            case "number": return "number";
            case "date": return "date";
            default: return "text";
        }
    }
}
```

## 示例 4：添加数据过滤功能

### 场景描述
在记录接口中添加数据过滤功能。

### 实现步骤

编辑 `backend/src/main/java/com/dingtalk/plugin/service/RecordService.java`：

```java
@Service
public class RecordService {

    public List<Record> getRecords(Map<String, Object> config) {
        // 获取过滤条件
        Map<String, Object> filters = (Map<String, Object>) config.get("filters");
        
        // 构建 SQL
        StringBuilder sql = new StringBuilder("SELECT * FROM " + tableName);
        List<Object> params = new ArrayList<>();
        
        if (filters != null && !filters.isEmpty()) {
            sql.append(" WHERE ");
            List<String> conditions = new ArrayList<>();
            
            for (Map.Entry<String, Object> entry : filters.entrySet()) {
                conditions.add(entry.getKey() + " = ?");
                params.add(entry.getValue());
            }
            
            sql.append(String.join(" AND ", conditions));
        }
        
        // 添加分页
        sql.append(" LIMIT ? OFFSET ?");
        params.add(pageSize);
        params.add((pageNum - 1) * pageSize);
        
        // 执行查询
        return executeQuery(sql.toString(), params);
    }
}
```

## 示例 5：添加数据缓存

### 场景描述
为频繁查询的表结构添加缓存。

### 实现步骤

#### 1. 添加依赖

编辑 `backend/pom.xml`：

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-cache</artifactId>
</dependency>
<dependency>
    <groupId>com.github.ben-manes.caffeine</groupId>
    <artifactId>caffeine</artifactId>
</dependency>
```

#### 2. 配置缓存

编辑 `backend/src/main/resources/application.yml`：

```yaml
spring:
  cache:
    type: caffeine
    caffeine:
      spec: maximumSize=500,expireAfterWrite=10m
```

#### 3. 启用缓存

在 Application 类添加注解：

```java
@SpringBootApplication
@EnableCaching
public class Application {
    // ...
}
```

#### 4. 使用缓存

在 Service 方法添加缓存注解：

```java
@Cacheable(value = "sheetMeta", key = "#config['tableName']")
public SheetMeta getSheetMeta(Map<String, Object> config) {
    // ...
}
```

## 示例 6：实现数据同步进度回调

### 场景描述
在数据同步过程中向 AI 表格报告进度。

### 实现步骤

```java
@Service
public class RecordService {

    public List<Record> getRecords(Map<String, Object> config) {
        String callbackUrl = (String) config.get("callbackUrl");
        int totalRecords = getTotalRecords(config);
        
        List<Record> records = new ArrayList<>();
        int batchSize = 100;
        
        for (int i = 0; i < totalRecords; i += batchSize) {
            // 获取一批数据
            List<Record> batch = fetchBatch(config, i, batchSize);
            records.addAll(batch);
            
            // 报告进度
            if (callbackUrl != null) {
                reportProgress(callbackUrl, i + batch.size(), totalRecords);
            }
        }
        
        return records;
    }
    
    private void reportProgress(String callbackUrl, int current, int total) {
        Map<String, Object> progress = new HashMap<>();
        progress.put("current", current);
        progress.put("total", total);
        progress.put("percentage", (current * 100.0) / total);
        
        restTemplate.postForObject(callbackUrl, progress, Void.class);
    }
}
```

## 示例 7：错误处理和重试

### 场景描述
添加完善的错误处理和自动重试机制。

### 实现步骤

```java
@Service
public class SheetMetaService {

    private static final int MAX_RETRIES = 3;
    private static final long RETRY_DELAY = 1000; // 1秒

    public SheetMeta getSheetMeta(Map<String, Object> config) {
        int retries = 0;
        Exception lastException = null;
        
        while (retries < MAX_RETRIES) {
            try {
                return fetchSheetMeta(config);
            } catch (SQLException e) {
                lastException = e;
                retries++;
                
                if (retries < MAX_RETRIES) {
                    try {
                        Thread.sleep(RETRY_DELAY * retries);
                    } catch (InterruptedException ie) {
                        Thread.currentThread().interrupt();
                        throw new RuntimeException("重试被中断", ie);
                    }
                }
            }
        }
        
        throw new RuntimeException(
            String.format("获取表结构失败，已重试 %d 次", MAX_RETRIES),
            lastException
        );
    }
    
    private SheetMeta fetchSheetMeta(Map<String, Object> config) throws SQLException {
        // 实际的获取逻辑
        // ...
    }
}
```

## 更多示例

查看项目中的 `templates/` 目录获取更多完整示例：
- frontend 前端页面实现
- backend 后端服务实现
    - MySQL 数据源完整实现
    - PostgreSQL 数据源完整实现

## 获取帮助

如有问题，请参考：
- 快速开始指南 `docs/quickstart.md`
- 调试指南 `docs/debug-guide.md`
- 部署指南 `docs/deploy.md`
