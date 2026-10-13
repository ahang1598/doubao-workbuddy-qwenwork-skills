package com.dingtalk.plugin.service;

import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONObject;
import com.dingtalk.plugin.datasource.DataSourceConfig;
import com.dingtalk.plugin.datasource.DataSourceRegistry;
import com.dingtalk.plugin.datasource.FieldValueBuilder;
import com.dingtalk.plugin.model.RecordsRequest;
import com.dingtalk.plugin.model.RecordsResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

/**
 * 数据记录服务：根据前端传入的配置参数返回数据记录。
 *
 * <p>开发指南：
 * <ol>
 *   <li>本示例使用硬编码的 demo 数据，实际开发时替换为真实的数据源调用</li>
 *   <li>支持分页：通过 nextToken（offset）和 maxResults 控制</li>
 *   <li>records 中每条记录的 fields Map 的 key 必须与 SheetMeta 中的字段 id 一致</li>
 * </ol>
 */
@Slf4j
@Service
public class RecordService {

    public RecordsResponse getRecords(RecordsRequest request) {
        log.info("[getRecords] requestId={}, nextToken={}, maxResults={}, params={}",
                request.getRequestId(), request.getNextToken(),
                request.getMaxResults(), request.getParams());

        JSONObject params = parseParams(request.getParams());
        String dataType = params.getString("dataType");

        // 如果前端未传 dataType，使用默认数据源
        if (dataType == null || dataType.trim().isEmpty()) {
            dataType = "demo";
        }

        // 校验数据源是否已注册
        DataSourceConfig config = DataSourceRegistry.get(dataType);
        if (config == null) {
            throw new IllegalArgumentException("不支持的数据类型: " + dataType);
        }

        // 分页参数
        int pageSize = request.getMaxResults() != null ? request.getMaxResults() : 200;
        int offset = parseOffset(request.getNextToken());

        // 开发指南：在这里替换为真实的数据源调用
        // 例如：调用第三方 API、查询数据库等
        return getDemoRecords(offset, pageSize, getRequestedFieldIds(request));
    }

    // -------------------------------------------------------------------------
    // 示例数据生成（开发时替换为真实数据源调用）
    // -------------------------------------------------------------------------

    /**
     * 生成示例数据，展示各种字段类型的值格式。
     *
     * <p>开发指南：替换此方法为你的真实数据获取逻辑，注意：
     * <ul>
     *   <li>text 类型：字符串值</li>
     *   <li>number 类型：数字值（int/long/double 或数字字符串）</li>
     *   <li>date 类型：毫秒时间戳（Long）</li>
     *   <li>singleSelect 类型：字符串值（必须是 choices 中定义的选项之一）</li>
     *   <li>link 类型：{@code {"text": "显示文本", "link": "URL"}} 结构</li>
     *   <li>checkbox 类型：Boolean 值</li>
     * </ul>
     */
    private RecordsResponse getDemoRecords(int offset, int pageSize, Set<String> requestedFieldIds) {
        // 示例：总共 5 条数据
        List<Map<String, Object>> allData = buildDemoData();
        int total = allData.size();

        // 分页截取
        int end = Math.min(offset + pageSize, total);
        List<RecordsResponse.Record> records = new ArrayList<>();

        for (int i = offset; i < end; i++) {
            Map<String, Object> data = allData.get(i);
            Map<String, Object> fields = new HashMap<>(data);
            if (requestedFieldIds != null) {
                fields.keySet().retainAll(requestedFieldIds);
            }
            records.add(RecordsResponse.Record.builder()
                    .id(String.valueOf(data.get("id")))
                    .fields(fields)
                    .build());
        }

        boolean hasMore = end < total;
        String nextToken = hasMore ? String.valueOf(end) : null;

        log.info("[getRecords] demo 返回: records={}, hasMore={}, total={}",
                records.size(), hasMore, total);

        return RecordsResponse.builder()
                .records(records)
                .hasMore(hasMore)
                .nextToken(nextToken)
                .total(total)
                .build();
    }

    /**
     * 构建示例数据列表。
     * 开发指南：此方法仅用于演示，实际开发时删除并替换为真实数据获取逻辑。
     */
    private List<Map<String, Object>> buildDemoData() {
        List<Map<String, Object>> data = new ArrayList<>();
        long now = System.currentTimeMillis();

        data.add(buildRecord("DEMO-001", "示例任务一", "进行中", 10, 99.50,
                now - 86400000L * 3, now, "这是第一条示例数据", "https://example.com/1"));
        data.add(buildRecord("DEMO-002", "示例任务二", "已完成", 25, 188.00,
                now - 86400000L * 7, now - 86400000L, "这是第二条示例数据", "https://example.com/2"));
        data.add(buildRecord("DEMO-003", "示例任务三", "待处理", 0, 0.00,
                now - 86400000L * 1, now, "这是第三条示例数据", "https://example.com/3"));
        data.add(buildRecord("DEMO-004", "示例任务四", "已取消", 5, 45.80,
                now - 86400000L * 14, now - 86400000L * 2, "这是第四条示例数据", null));
        data.add(buildRecord("DEMO-005", "示例任务五", "进行中", 100, 1234.56,
                now - 86400000L * 30, now, "这是第五条示例数据", "https://example.com/5"));

        return data;
    }

    private Map<String, Object> buildRecord(String id, String name, String status,
                                            int count, double amount,
                                            long createdAt, long updatedAt,
                                            String description, String link) {
        Map<String, Object> record = new HashMap<>();
        record.put("id", id);
        record.put("name", name);
        record.put("status", status);
        record.put("count", count);
        record.put("amount", amount);
        record.put("created_at", createdAt);
        record.put("updated_at", updatedAt);
        record.put("description", description);
        record.put("link", FieldValueBuilder.linkValue(link));
        return record;
    }

    // -------------------------------------------------------------------------
    // 工具方法
    // -------------------------------------------------------------------------

    private JSONObject parseParams(String params) {
        if (params == null || params.trim().isEmpty()) {
            return new JSONObject();
        }
        try {
            JSONObject jsonObject = JSON.parseObject(params);
            return jsonObject != null ? jsonObject : new JSONObject();
        } catch (Exception e) {
            throw new IllegalArgumentException("params 格式错误: " + e.getMessage());
        }
    }

    private int parseOffset(String nextToken) {
        if (nextToken == null || nextToken.trim().isEmpty()) {
            return 0;
        }
        try {
            return Integer.parseInt(nextToken.trim());
        } catch (NumberFormatException e) {
            log.warn("[getRecords] nextToken 格式非法，重置为 0: {}", nextToken);
            return 0;
        }
    }

    /**
     * 获取平台本次请求的字段集合。返回 null 表示平台未指定字段，需要返回全部字段。
     */
    private Set<String> getRequestedFieldIds(RecordsRequest request) {
        if (request.getContext() == null
                || request.getContext().getFields() == null
                || request.getContext().getFields().isEmpty()) {
            return null;
        }

        return request.getContext().getFields().stream()
                .map(RecordsRequest.SyncField::getId)
                .filter(id -> id != null && !id.trim().isEmpty())
                .collect(Collectors.toSet());
    }
}
