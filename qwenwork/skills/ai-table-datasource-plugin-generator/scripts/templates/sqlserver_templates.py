#!/usr/bin/env python3
"""
SQL Server SheetMetaService 和 RecordService 模板。
- 连接参数通过 Spring @Value 从 backend/.env 注入
- tableName 通过 @Value("${datasource.tableName}") 从 backend/.env 注入
- SQL 中表名用方括号包裹（[tableName]），防止大小写问题和保留字冲突
- 分页使用 OFFSET ... FETCH NEXT ... ROWS ONLY（SQL Server 2012+）
"""


def get_sqlserver_sheet_meta_service() -> str:
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
 * SQL Server 表结构服务。
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

    @Value("${datasource.trustServerCertificate:false}")
    private boolean trustServerCertificate;

    public SheetMetaResponse getSheetMeta(SheetMetaRequest request) {
        log.info("[getSheetMeta] tableName={}, host={}, database={}", tableName, host, database);

        String url = String.format(
                "jdbc:sqlserver://%s:%s;databaseName=%s;encrypt=true;trustServerCertificate=%s",
                host, port, database, trustServerCertificate);

        List<SheetMetaResponse.Field> fields = new ArrayList<>();

        try (Connection conn = DriverManager.getConnection(url, username, password)) {
            log.debug("SQL Server 连接成功");
            DatabaseMetaData meta = conn.getMetaData();

            // SQL Server: catalog=database, schema="dbo"（默认 schema）
            String primaryKeyColumn = detectPrimaryKey(conn, database, tableName);

            try (ResultSet columns = meta.getColumns(database, "dbo", tableName, null)) {
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
            log.error("[getSheetMeta] SQL Server 查询失败, database={}, tableName={}", database, tableName, e);
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
     * 检测表主键列名。catalog=database, schema="dbo"。
     */
    private String detectPrimaryKey(Connection conn, String catalog, String tableName) throws SQLException {
        try (ResultSet primaryKeys = conn.getMetaData().getPrimaryKeys(catalog, "dbo", tableName)) {
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


def get_sqlserver_record_service() -> str:
    return """package com.dingtalk.plugin.service;

import com.alibaba.fastjson.JSON;
import com.dingtalk.plugin.model.RecordsRequest;
import com.dingtalk.plugin.model.RecordsResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.security.MessageDigest;
import java.sql.*;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * SQL Server 记录服务。
 * 数据库连接参数从 backend/.env 文件读取（通过 Spring @Value 注入）。
 * tableName 由前端配置页面通过 saveConfigAndGoNext 传入，从 request.params 中解析。
 * 分页使用 OFFSET ... FETCH NEXT ... ROWS ONLY（需要 ORDER BY，SQL Server 2012+）。
 * SQL 中表名用方括号包裹（[tableName]），防止大小写问题和保留字冲突。
 */
@Slf4j
@Service
public class RecordService {

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

    @Value("${datasource.trustServerCertificate:false}")
    private boolean trustServerCertificate;

    public RecordsResponse getRecords(RecordsRequest request) {
        int requestedPageSize = request.getMaxResults() != null ? request.getMaxResults() : 300;
        int pageSize = Math.max(1, Math.min(requestedPageSize, 1000));
        int offset = parseOffset(request.getNextToken());

        log.info("[getRecords] tableName={}, pageSize={}, offset={}", tableName, pageSize, offset);

        String url = String.format(
                "jdbc:sqlserver://%s:%s;databaseName=%s;encrypt=true;trustServerCertificate=%s",
                host, port, database, trustServerCertificate);

        List<RecordsResponse.Record> records = new ArrayList<>();
        boolean hasMore = false;
        String nextToken = null;

        try (Connection conn = DriverManager.getConnection(url, username, password)) {
            log.debug("SQL Server 连接成功");

            String primaryKeyColumn = detectPrimaryKey(conn, database, tableName);

            // 表名用方括号包裹，SQL Server 分页需要 ORDER BY
            // 若无主键则按 (SELECT NULL) 排序（保证语法合法，但顺序不稳定）
            String escapedTableName = tableName.replace("]", "]]" );
            String orderBy = primaryKeyColumn != null
                    ? "[" + primaryKeyColumn.replace("]", "]]" ) + "]"
                    : "(SELECT NULL)";
            if (primaryKeyColumn == null) {
                log.warn("表 {} 没有主键；OFFSET 分页无法保证数据变更期间的稳定顺序", tableName);
            }
            String sql = String.format(
                    "SELECT * FROM [%s] ORDER BY %s OFFSET %d ROWS FETCH NEXT %d ROWS ONLY",
                    escapedTableName, orderBy, offset, pageSize + 1);
            log.debug("执行 SQL: {}", sql);

            try (Statement stmt = conn.createStatement();
                 ResultSet rs = stmt.executeQuery(sql)) {

                ResultSetMetaData metaData = rs.getMetaData();
                int columnCount = metaData.getColumnCount();
                int rowCount = 0;

                while (rs.next()) {
                    rowCount++;
                    if (rowCount > pageSize) {
                        hasMore = true;
                        nextToken = String.valueOf(offset + pageSize);
                        break;
                    }

                    Map<String, Object> fields = new HashMap<>();
                    for (int i = 1; i <= columnCount; i++) {
                        String columnName = metaData.getColumnName(i);
                        Object value = rs.getObject(i);
                        if (value instanceof Boolean) {
                            // BIT 映射为 singleSelect，必须返回字符串 "true"/"false"
                            value = String.valueOf(value);
                        } else if (value instanceof Timestamp) {
                            value = ((Timestamp) value).getTime();
                        } else if (value instanceof java.sql.Date) {
                            value = ((java.sql.Date) value).getTime();
                        }
                        fields.put(columnName, value);
                    }

                    String recordId = generateRecordId(fields, primaryKeyColumn);
                    filterRequestedFields(request, fields);
                    records.add(RecordsResponse.Record.builder()
                            .id(recordId)
                            .fields(fields)
                            .build());
                }
            }
        } catch (SQLException e) {
            log.error("[getRecords] SQL Server 查询失败, database={}, tableName={}", database, tableName, e);
            throw new RuntimeException("获取记录失败: " + e.getMessage(), e);
        }

        log.info("[getRecords] 完成, tableName={}, 返回记录数={}, hasMore={}", tableName, records.size(), hasMore);
        return RecordsResponse.builder()
                .records(records)
                .hasMore(hasMore)
                .nextToken(nextToken)
                .build();
    }

    private String detectPrimaryKey(Connection conn, String catalog, String tableName) throws SQLException {
        try (ResultSet primaryKeys = conn.getMetaData().getPrimaryKeys(catalog, "dbo", tableName)) {
            if (primaryKeys.next()) {
                return primaryKeys.getString("COLUMN_NAME");
            }
        }
        return null;
    }

    private String generateRecordId(Map<String, Object> fields, String primaryKeyColumn) {
        if (primaryKeyColumn != null && fields.containsKey(primaryKeyColumn)) {
            return String.valueOf(fields.get(primaryKeyColumn));
        }
        String allValues = fields.entrySet().stream()
                .sorted(Map.Entry.comparingByKey())
                .map(e -> e.getKey() + "=" + e.getValue())
                .collect(Collectors.joining("_"));
        return generateMd5(allValues);
    }

    private String generateMd5(String input) {
        try {
            MessageDigest md = MessageDigest.getInstance("MD5");
            byte[] digest = md.digest(input.getBytes("UTF-8"));
            StringBuilder sb = new StringBuilder();
            for (byte b : digest) {
                sb.append(String.format("%02x", b));
            }
            return sb.toString();
        } catch (Exception e) {
            throw new RuntimeException("生成行 ID 失败", e);
        }
    }

    private int parseOffset(String nextToken) {
        if (nextToken == null || nextToken.isEmpty()) {
            return 0;
        }
        try {
            return Math.max(0, Integer.parseInt(nextToken));
        } catch (NumberFormatException e) {
            return 0;
        }
    }

    private void filterRequestedFields(RecordsRequest request, Map<String, Object> fields) {
        if (request.getContext() == null
                || request.getContext().getFields() == null
                || request.getContext().getFields().isEmpty()) {
            return;
        }
        List<String> requestedFieldIds = request.getContext().getFields().stream()
                .map(RecordsRequest.SyncField::getId)
                .filter(id -> id != null && !id.trim().isEmpty())
                .collect(Collectors.toList());
        fields.keySet().retainAll(requestedFieldIds);
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
