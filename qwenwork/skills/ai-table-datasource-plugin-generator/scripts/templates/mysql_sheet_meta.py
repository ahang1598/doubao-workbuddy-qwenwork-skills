#!/usr/bin/env python3
"""
MySQL SheetMetaService 模板。
- 连接参数通过 Spring @Value 从 backend/.env 注入
- tableName 通过 @Value("${datasource.tableName}") 从 backend/.env 注入
- DatabaseMetaData.getColumns 使用 catalog=database 保证大小写正确
"""


def get_mysql_sheet_meta_service() -> str:
    return """package com.dingtalk.plugin.service;

import com.alibaba.fastjson.JSON;
import com.dingtalk.plugin.model.SheetMetaRequest;
import com.dingtalk.plugin.model.SheetMetaResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.sql.*;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * MySQL 表结构服务。
 * 数据库连接参数和 tableName 均从 backend/.env 文件读取（通过 Spring @Value 注入）。
 */
@Slf4j
@Service
public class SheetMetaService {

    @Value("${datasource.host}")
    private String host;

    @Value("${datasource.port}")
    private String port;

    @Value("${datasource.database}")
    private String database;

    @Value("${datasource.username}")
    private String username;

    @Value("${datasource.password}")
    private String password;

    @Value("${datasource.tableName}")
    private String tableName;

    @Value("${datasource.sslMode:PREFERRED}")
    private String sslMode;

    public SheetMetaResponse getSheetMeta(SheetMetaRequest request) {
        log.info("[getSheetMeta] tableName={}, host={}, database={}", tableName, host, database);

        String url = String.format(
                "jdbc:mysql://%s:%s/%s?sslMode=%s&serverTimezone=UTC&allowPublicKeyRetrieval=false",
                host, port, database, sslMode);

        List<SheetMetaResponse.Field> fields = new ArrayList<>();

        try (Connection conn = DriverManager.getConnection(url, username, password)) {
            log.debug("MySQL 连接成功");
            DatabaseMetaData meta = conn.getMetaData();

            // catalog 传入 database 名，保证 MySQL 在大小写不敏感模式下也能匹配正确的表
            String primaryKeyColumn = detectPrimaryKey(conn, database, tableName);

            // catalog=database, schema=null, tableNamePattern=tableName（精确匹配）
            try (ResultSet columns = meta.getColumns(database, null, tableName, null)) {
                while (columns.next()) {
                    String columnName = columns.getString("COLUMN_NAME");
                    int dataType = columns.getInt("DATA_TYPE");
                    boolean isPrimary = columnName.equals(primaryKeyColumn);

                    SheetMetaResponse.Field field = buildField(columnName, dataType, isPrimary);
                    log.debug("映射字段: {} -> type={}, isPrimary={}", columnName, field.getType(), isPrimary);
                    fields.add(field);
                }
            }
        } catch (SQLException e) {
            log.error("[getSheetMeta] MySQL 查询失败, database={}, tableName={}", database, tableName, e);
            throw new RuntimeException("获取表结构失败: " + e.getMessage(), e);
        }

        log.info("[getSheetMeta] 完成, tableName={}, 字段数={}", tableName, fields.size());
        return SheetMetaResponse.builder()
                .sheetName(tableName != null ? tableName : "unknown")
                .fields(fields)
                .build();
    }

    private SheetMetaResponse.Field buildField(String columnName, int dataType, boolean isPrimary) {
        String type;
        Map<String, Object> property = new HashMap<>();

        switch (dataType) {
            case Types.INTEGER:
            case Types.BIGINT:
            case Types.SMALLINT:
            case Types.TINYINT:
                type = "number";
                property.put("formatter", "INT");
                break;
            case Types.DECIMAL:
            case Types.DOUBLE:
            case Types.FLOAT:
            case Types.NUMERIC:
                type = "number";
                property.put("formatter", "FLOAT_2");
                break;
            case Types.DATE:
                type = "date";
                property.put("formatter", "YYYY-MM-DD");
                break;
            case Types.TIMESTAMP:
            case Types.TIME:
                type = "date";
                property.put("formatter", "YYYY-MM-DD HH:mm");
                break;
            case Types.BOOLEAN:
            case Types.BIT:
                type = "singleSelect";
                property.put("choices", buildBoolChoices());
                break;
            default:
                type = "text";
                break;
        }

        return SheetMetaResponse.Field.builder()
                .id(columnName)
                .name(columnName)
                .type(type)
                .isPrimary(isPrimary)
                .property(property.isEmpty() ? null : property)
                .build();
    }

    private List<Map<String, String>> buildBoolChoices() {
        Map<String, String> trueChoice = new HashMap<>();
        trueChoice.put("name", "true");
        Map<String, String> falseChoice = new HashMap<>();
        falseChoice.put("name", "false");
        List<Map<String, String>> choices = new ArrayList<>();
        choices.add(trueChoice);
        choices.add(falseChoice);
        return choices;
    }

    /**
     * 检测表主键列名。catalog 传入 database 名以精确匹配。
     */
    private String detectPrimaryKey(Connection conn, String catalog, String tableName) throws SQLException {
        try (ResultSet primaryKeys = conn.getMetaData().getPrimaryKeys(catalog, null, tableName)) {
            if (primaryKeys.next()) {
                return primaryKeys.getString("COLUMN_NAME");
            }
        }
        return null;
    }

    private String parseParam(String params, String key) {
        if (params == null || params.isEmpty()) {
            return null;
        }
        try {
            return JSON.parseObject(params).getString(key);
        } catch (Exception e) {
            log.warn("解析 params 失败: {}", e.getMessage());
            return null;
        }
    }
}
"""
