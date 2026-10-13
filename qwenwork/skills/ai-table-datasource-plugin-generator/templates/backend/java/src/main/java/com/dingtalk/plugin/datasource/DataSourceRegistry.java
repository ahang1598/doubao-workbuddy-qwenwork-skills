package com.dingtalk.plugin.datasource;

import java.util.Collection;
import java.util.HashMap;
import java.util.Map;

/**
 * 数据源注册表：统一管理所有数据源配置。
 *
 * <p>开发指南：创建新的 DataSourceConfig 实现类后，在 static 块中调用 register() 注册即可。
 *
 * <p>用法示例：
 * <pre>
 *   DataSourceConfig config = DataSourceRegistry.get("demo");
 *   List&lt;FieldDefinition&gt; fields = config.getFields();
 * </pre>
 */
public class DataSourceRegistry {

    private static final Map<String, DataSourceConfig> REGISTRY = new HashMap<>();

    static {
        // 注册所有数据源配置
        // 开发指南：在这里注册你的自定义数据源
        register(DemoDataSourceConfig.INSTANCE);
    }

    /**
     * 注册数据源配置
     */
    public static void register(DataSourceConfig config) {
        REGISTRY.put(config.getDataSourceId(), config);
    }

    /**
     * 根据数据源 ID 获取配置
     *
     * @param dataSourceId 数据源 ID，如 "demo"
     * @return 数据源配置，若不存在返回 null
     */
    public static DataSourceConfig get(String dataSourceId) {
        return REGISTRY.get(dataSourceId);
    }

    /**
     * 检查数据源是否已注册
     */
    public static boolean contains(String dataSourceId) {
        return REGISTRY.containsKey(dataSourceId);
    }

    /**
     * 获取所有已注册的数据源 ID
     */
    public static Collection<String> getDataSourceIds() {
        return REGISTRY.keySet();
    }

    /**
     * 获取所有已注册的数据源配置
     */
    public static Collection<DataSourceConfig> getAllConfigs() {
        return REGISTRY.values();
    }
}
