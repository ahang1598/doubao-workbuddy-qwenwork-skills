package com.dingtalk.plugin.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * 表结构响应
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SheetMetaResponse {

    /**
     * 表名称
     */
    private String sheetName;

    /**
     * 字段列表
     */
    private List<Field> fields;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Field {
        /**
         * 字段ID
         */
        private String id;

        /**
         * 字段名称
         */
        private String name;

        /**
         * 字段类型
         */
        private String type;

        /**
         * 是否主键
         */
        private Boolean isPrimary;

        /**
         * 字段属性
         */
        private Object property;

        /**
         * 字段描述
         */
        private String description;
    }
}
