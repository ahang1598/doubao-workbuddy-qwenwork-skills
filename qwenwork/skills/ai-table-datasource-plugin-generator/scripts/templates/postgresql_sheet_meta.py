#!/usr/bin/env python3
"""
PostgreSQL SheetMetaService 模板。
- 连接参数通过 Spring @Value 从 backend/.env 注入
- tableName 通过 @Value("${datasource.tableName}") 从 backend/.env 注入
- DatabaseMetaData.getColumns: schema="public", tableNamePattern=tableName（原始大小写，精确匹配）
- detectPrimaryKey 同样传入原始 tableName，不做任何大小写转换
"""


def get_postgresql_sheet_meta_service() -> str:
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
 * PostgreSQL 表结构服务。
 * 数据库连接参数和 tableName 均从 backend/.env 文件读取（通过 Spring @Value 注入）。
 *
 * 注意：PostgreSQL 默认将未加引号的标识符折叠为小写。
 * DatabaseMetaData.getColumns / getPrimaryKeys 传入的 tableNamePattern 必须与
 * 数据库中存储的表名大小写完全一致（即创建表时使用的原始名称）。
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

    public SheetMetaResponse getSheetMeta(SheetMetaRequest request) {
        log.info("[getSheetMeta] tableName={}, host={}, database={}", tableName, host, database);

        String url = String.format("jdbc:postgresql://%s:%s/%s", host, port, database);

        List<SheetMetaResponse.Field> fields = new ArrayList<>();

        try (Connection conn = DriverManager.getConnection(url, username, password)) {
            log.debug("PostgreSQL 连接成功");
            DatabaseMetaData meta = conn.getMetaData();

            // 传入原始 tableName（不做大小写转换），PostgreSQL JDBC 会精确匹配
            String primaryKeyColumn = detectPrimaryKey(conn, tableName);

            // catalog=null, schema="public", tableNamePattern=tableName（原始大小写）
            try (ResultSet columns = meta.getColumns(null, "public", tableName, null)) {
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
            log.error("[getSheetMeta] PostgreSQL 查询失败, database={}, tableName={}", database, tableName, e);
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
                type = "number";
                property.put("formatter", "INT");
                break;
            case Types.DECIMAL:
            case Types.DOUBLE:
            case Types.FLOAT:
            case Types.NUMERIC:
            case Types.REAL:
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
     * 检测表主键列名。
     * schema 固定为 "public"，tableName 保持原始大小写。
     */
    private String detectPrimaryKey(Connection conn, String tableName) throws SQLException {
        try (ResultSet primaryKeys = conn.getMetaData().getPrimaryKeys(null, "public", tableName)) {
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
