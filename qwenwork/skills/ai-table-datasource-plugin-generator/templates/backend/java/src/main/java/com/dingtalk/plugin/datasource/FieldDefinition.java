package com.dingtalk.plugin.datasource;

import lombok.Builder;
import lombok.Getter;

/**
 * 字段定义：描述数据源返回的单个字段元信息。
 *
 * <p>用于生成 AI 表格的 sheet_meta 响应以及 records 数据转换。
 */
@Getter
@Builder
public class FieldDefinition {

    /** 字段 ID（对应 records 中 fields Map 的 key） */
    private final String id;

    /** 字段显示名称 */
    private final String name;

    /**
     * 字段类型，可选值：
     * <ul>
     *   <li>text - 文本</li>
     *   <li>number - 数字</li>
     *   <li>singleSelect - 单选</li>
     *   <li>date - 日期（毫秒时间戳）</li>
     *   <li>checkbox - 勾选框</li>
     *   <li>link - 链接</li>
     * </ul>
     */
    private final String type;

    /** 是否主键字段 */
    @Builder.Default
    private final boolean isPrimary = false;

    /** 字段说明 */
    private final String description;

    /**
     * 数字格式化类型，仅当 type=number 时有效：
     * <ul>
     *   <li>INT - 整数</li>
     *   <li>FLOAT_2 - 两位小数浮点数</li>
     * </ul>
     */
    private final String formatter;

    /**
     * 单选选项（仅当 type=singleSelect 时有效）
     */
    private final String[] choices;

    // -------------------------------------------------------------------------
    // 便捷工厂方法
    // -------------------------------------------------------------------------

    /** 创建文本字段 */
    public static FieldDefinition text(String id, String name, String description) {
        return FieldDefinition.builder()
                .id(id).name(name).type("text").description(description)
                .build();
    }

    /** 创建主键文本字段 */
    public static FieldDefinition textPrimary(String id, String name, String description) {
        return FieldDefinition.builder()
                .id(id).name(name).type("text").isPrimary(true).description(description)
                .build();
    }

    /** 创建整数字段 */
    public static FieldDefinition intField(String id, String name, String description) {
        return FieldDefinition.builder()
                .id(id).name(name).type("number").formatter("INT").description(description)
                .build();
    }

    /** 创建浮点数字段 */
    public static FieldDefinition floatField(String id, String name, String description) {
        return FieldDefinition.builder()
                .id(id).name(name).type("number").formatter("FLOAT_2").description(description)
                .build();
    }

    /** 创建单选字段 */
    public static FieldDefinition singleSelect(String id, String name, String description, String... choices) {
        return FieldDefinition.builder()
                .id(id).name(name).type("singleSelect").description(description).choices(choices)
                .build();
    }

    /** 创建日期字段 */
    public static FieldDefinition date(String id, String name, String description) {
        return FieldDefinition.builder()
                .id(id).name(name).type("date").description(description)
                .build();
    }

    /** 创建勾选框字段 */
    public static FieldDefinition checkbox(String id, String name, String description) {
        return FieldDefinition.builder()
                .id(id).name(name).type("checkbox").description(description)
                .build();
    }

    /** 创建链接字段 */
    public static FieldDefinition urlField(String id, String name, String description) {
        return FieldDefinition.builder()
                .id(id).name(name).type("link").description(description)
                .build();
    }
}
