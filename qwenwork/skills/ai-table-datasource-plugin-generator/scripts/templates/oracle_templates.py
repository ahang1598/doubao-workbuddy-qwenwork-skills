#!/usr/bin/env python3
"""
Oracle SheetMetaService 和 RecordService 模板。
- 连接参数通过 Spring @Value 从 backend/.env 注入
- tableName 通过 @Value("${datasource.tableName}") 从 backend/.env 注入
- Oracle 默认将标识符存储为大写，SQL 中表名用双引号包裹保留原始大小写
- 分页使用 OFFSET ... ROWS FETCH NEXT ... ROWS ONLY（Oracle 12c+）
- DatabaseMetaData.getColumns: schema=username.toUpperCase()（Oracle 的 schema 即用户名）
"""


def get_oracle_sheet_meta_service() -> str:
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
 * Oracle 表结构服务。
 * 数据库连接参数和 tableName 均从 backend/.env 文件读取（通过 Spring @Value 注入）。
 *
 * 注意：Oracle 默认将未加引号的标识符存储为大写。
 * DatabaseMetaData.getColumns 的 schema 参数需传入大写的用户名（Oracle schema = 用户名）。
 * 若表名是混合大小写（用双引号创建的），tableName 需与创建时完全一致。
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

        // Oracle JDBC URL 格式：jdbc:oracle:thin:@host:port:SID 或 jdbc:oracle:thin:@//host:port/ServiceName
        String url = String.format("jdbc:oracle:thin:@//%s:%s/%s", host, port, database);

        List<SheetMetaResponse.Field> fields = new ArrayList<>();

        try (Connection conn = DriverManager.getConnection(url, username, password)) {
            log.debug("Oracle 连接成功");
            DatabaseMetaData meta = conn.getMetaData();

            // Oracle schema = 用户名（大写），tableName 通常也是大写（除非用双引号创建）
            String schema = username.toUpperCase();
            String primaryKeyColumn = detectPrimaryKey(conn, schema, tableName);

            try (ResultSet columns = meta.getColumns(null, schema, tableName, null)) {
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
            log.error("[getSheetMeta] Oracle 查询失败, database={}, tableName={}", database, tableName, e);
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
            case Types.NUMERIC:
                type = "number";
                property.put("formatter", "INT");
                break;
            case Types.DECIMAL:
            case Types.DOUBLE:
            case Types.FLOAT:
            case Types.REAL:
                type = "number";
                property.put("formatter", "FLOAT_2");
                break;
            case Types.DATE:
            case Types.TIMESTAMP:
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
     * 检测表主键列名。schema 传入大写用户名（Oracle schema = 用户名）。
     */
    private String detectPrimaryKey(Connection conn, String schema, String tableName) throws SQLException {
        try (ResultSet primaryKeys = conn.getMetaData().getPrimaryKeys(null, schema, tableName)) {
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


def get_oracle_record_service() -> str:
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
 * Oracle 记录服务。
 * 数据库连接参数从 backend/.env 文件读取（通过 Spring @Value 注入）。
 * tableName 由前端配置页面通过 saveConfigAndGoNext 传入，从 request.params 中解析。
 * 分页使用 OFFSET ... ROWS FETCH NEXT ... ROWS ONLY（Oracle 12c+）。
 *
 * 注意：Oracle 默认将标识符存储为大写。若表名是混合大小写（用双引号创建），
 * SQL 中需用双引号包裹表名（如 "MyTable"）。本模板统一用双引号包裹以兼容两种情况。
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

    public RecordsResponse getRecords(RecordsRequest request) {
        int requestedPageSize = request.getMaxResults() != null ? request.getMaxResults() : 300;
        int pageSize = Math.max(1, Math.min(requestedPageSize, 1000));
        int offset = parseOffset(request.getNextToken());

        log.info("[getRecords] tableName={}, pageSize={}, offset={}", tableName, pageSize, offset);

        String url = String.format("jdbc:oracle:thin:@//%s:%s/%s", host, port, database);

        List<RecordsResponse.Record> records = new ArrayList<>();
        boolean hasMore = false;
        String nextToken = null;

        try (Connection conn = DriverManager.getConnection(url, username, password)) {
            log.debug("Oracle 连接成功");

            String schema = username.toUpperCase();
            String primaryKeyColumn = detectPrimaryKey(conn, schema, tableName);

            // 表名用双引号包裹，Oracle 12c+ 分页语法。无主键时使用 ROWID 保持稳定顺序。
            String escapedTableName = tableName.replace("\\"", "\\"\\"");
            String orderBy = primaryKeyColumn == null
                    ? " ORDER BY ROWID"
                    : " ORDER BY \\"" + primaryKeyColumn.replace("\\"", "\\"\\"") + "\\"";
            String sql = String.format(
                    "SELECT * FROM \\"%s\\"%s OFFSET %d ROWS FETCH NEXT %d ROWS ONLY",
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
                            // BOOLEAN 映射为 singleSelect，必须返回字符串 "true"/"false"
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
            log.error("[getRecords] Oracle 查询失败, database={}, tableName={}", database, tableName, e);
            throw new RuntimeException("获取记录失败: " + e.getMessage(), e);
        }

        log.info("[getRecords] 完成, tableName={}, 返回记录数={}, hasMore={}", tableName, records.size(), hasMore);
        return RecordsResponse.builder()
                .records(records)
                .hasMore(hasMore)
                .nextToken(nextToken)
                .build();
    }

    private String detectPrimaryKey(Connection conn, String schema, String tableName) throws SQLException {
        try (ResultSet primaryKeys = conn.getMetaData().getPrimaryKeys(null, schema, tableName)) {
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
