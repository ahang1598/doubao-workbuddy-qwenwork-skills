package com.dingtalk.plugin.datasource;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * 数据源配置接口：定义单个数据源的元信息。
 *
 * <p>每个实现类对应一种数据源，包含：
 * <ul>
 *   <li>数据源 ID</li>
 *   <li>表格显示名称</li>
 *   <li>字段定义列表</li>
 * </ul>
 *
 * <p>开发指南：创建新的数据源时，实现此接口并在 {@link DataSourceRegistry} 中注册即可。
 */
public interface DataSourceConfig {

    /**
     * 数据源 ID，对应前端传入的 dataType 参数。
     * 例如 "demo"、"mysql_users" 等。
     */
    String getDataSourceId();

    /**
     * 表格显示名称，将作为 AI 表格中的 sheet 名称。
     * 例如 "示例数据"、"用户列表"。
     */
    String getTableName();

    /**
     * 获取字段定义列表。
     *
     * @return 字段定义，顺序即为表格展示顺序
     */
    List<FieldDefinition> getFields();

    /**
     * 构建 API 请求的 body 参数（可选，用于调用第三方 API 的场景）。
     *
     * @param offset 分页偏移量
     * @param length 每页数量
     * @return 请求 body 的 Map 表示
     */
    default Map<String, Object> buildRequestBody(int offset, int length) {
        Map<String, Object> body = new HashMap<>();
        body.put("offset", offset);
        body.put("length", length);
        return body;
    }
}
