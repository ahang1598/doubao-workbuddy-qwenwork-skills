package com.dingtalk.plugin.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import lombok.Data;

import java.util.List;
import java.util.Map;

/**
 * 数据记录请求
 */
@Data
public class RecordsRequest {

    /**
     * 请求ID
     */
    private String requestId;

    /**
     * 最大返回记录数
     */
    private Integer maxResults;

    /**
     * 分页令牌
     */
    private String nextToken;

    /**
     * 配置参数（JSON字符串）
     */
    private String params;

    /**
     * 上下文信息
     */
    private Context context;

    /**
     * records 接口上下文。平台可能持续增加字段，因此必须忽略未知字段。
     */
    @Data
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Context {
        private String unionId;
        private String corpId;
        private Map<String, String> credentials;
        private String locale;
        private String docKey;
        private String sheetId;
        private String syncInstanceId;
        private String taskId;

        /**
         * 本次同步需要返回的字段。非空时应只查询并返回这些字段。
         */
        private List<SyncField> fields;

        private Integer maxImportRowCount;
    }

    @Data
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class SyncField {
        private String id;
        private String type;
    }
}
