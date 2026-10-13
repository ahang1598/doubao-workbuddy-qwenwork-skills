package com.dingtalk.plugin.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import lombok.Data;

import java.util.Map;

/**
 * 表结构请求
 */
@Data
public class SheetMetaRequest {

    /**
     * 请求ID
     */
    private String requestId;

    /**
     * 配置参数（JSON字符串）
     */
    private String params;

    /**
     * 上下文信息
     */
    private Context context;

    @Data
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Context {
        /**
         * 用户ID
         */
        private String unionId;

        /**
         * 企业ID
         */
        private String corpId;

        private String locale;

        private String docKey;

        private String sheetId;

        /**
         * 三方账号代管凭证。未绑定账号时为空。
         */
        private Map<String, String> credentials;
    }
}
