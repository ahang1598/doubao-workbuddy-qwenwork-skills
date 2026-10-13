package com.dingtalk.plugin.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;
import java.util.Map;

/**
 * 数据记录响应
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RecordsResponse {

    /**
     * 下一页令牌
     */
    private String nextToken;

    /**
     * 是否还有更多数据
     */
    private Boolean hasMore;

    /**
     * 记录列表
     */
    private List<Record> records;

    /**
     * 总数（可选）
     */
    private Integer total;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Record {
        /**
         * 记录ID
         */
        private String id;

        /**
         * 字段数据
         */
        private Map<String, Object> fields;
    }
}
