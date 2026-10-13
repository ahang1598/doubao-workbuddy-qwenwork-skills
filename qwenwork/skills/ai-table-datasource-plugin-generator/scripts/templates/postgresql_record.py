#!/usr/bin/env python3
"""
PostgreSQL RecordService 模板。
- 连接参数通过 Spring @Value 从 backend/.env 注入
- tableName 通过 @Value("${datasource.tableName}") 从 backend/.env 注入
- SQL 中表名用双引号包裹，防止 PostgreSQL 将其折叠为小写
- 分页通过 nextToken（offset 字符串）实现
"""


def get_postgresql_record_service() -> str:
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
 * PostgreSQL 记录服务。
 * 数据库连接参数和 tableName 均从 backend/.env 文件读取（通过 Spring @Value 注入）。
 * 分页通过 nextToken 传递当前 offset，首次请求传 null 或空字符串。
 *
 * 注意：SQL 中表名用双引号包裹（如 "ChatMessage"），防止 PostgreSQL 将其折叠为小写。
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

        String url = String.format("jdbc:postgresql://%s:%s/%s", host, port, database);

        List<RecordsResponse.Record> records = new ArrayList<>();
        boolean hasMore = false;
        String nextToken = null;

        try (Connection conn = DriverManager.getConnection(url, username, password)) {
            log.debug("PostgreSQL 连接成功");

            // 自动检测主键列，用于生成稳定的行 ID
            String primaryKeyColumn = detectPrimaryKey(conn, tableName);

            // 表名用双引号包裹，保留原始大小写（PostgreSQL 默认将无引号标识符折叠为小写）
            String escapedTableName = tableName.replace("\\"", "\\"\\"");
            String orderBy = primaryKeyColumn == null
                    ? ""
                    : " ORDER BY \\"" + primaryKeyColumn.replace("\\"", "\\"\\"") + "\\"";
            if (primaryKeyColumn == null) {
                log.warn("表 {} 没有主键；OFFSET 分页无法保证数据变更期间的稳定顺序", tableName);
            }
            String sql = String.format("SELECT * FROM \\"%s\\"%s LIMIT %d OFFSET %d",
                    escapedTableName, orderBy, pageSize + 1, offset);
            log.debug("执行 SQL: {}", sql);

            try (Statement stmt = conn.createStatement();
                 ResultSet rs = stmt.executeQuery(sql)) {

                ResultSetMetaData metaData = rs.getMetaData();
                int columnCount = metaData.getColumnCount();
                int rowCount = 0;

                while (rs.next()) {
                    rowCount++;
                    // 多查一条用于判断是否还有更多数据
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
            log.error("[getRecords] PostgreSQL 查询失败, database={}, tableName={}", database, tableName, e);
            throw new RuntimeException("获取记录失败: " + e.getMessage(), e);
        }

        log.info("[getRecords] 完成, tableName={}, 返回记录数={}, hasMore={}", tableName, records.size(), hasMore);
        return RecordsResponse.builder()
                .records(records)
                .hasMore(hasMore)
                .nextToken(nextToken)
                .build();
    }

    /**
     * 检测表主键列名。schema 固定为 "public"，tableName 保持原始大小写。
     */
    private String detectPrimaryKey(Connection conn, String tableName) throws SQLException {
        try (ResultSet primaryKeys = conn.getMetaData().getPrimaryKeys(null, "public", tableName)) {
            if (primaryKeys.next()) {
                return primaryKeys.getString("COLUMN_NAME");
            }
        }
        return null;
    }

    /**
     * 生成行 ID：有主键用主键值，无主键则对所有字段值排序后取 MD5。
     */
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
