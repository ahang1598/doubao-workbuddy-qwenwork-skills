package com.dingtalk.plugin.datasource;

import java.util.Arrays;
import java.util.List;

/**
 * 示例数据源配置：展示各种字段类型的用法。
 *
 * <p>开发指南：参照此类创建你自己的数据源配置类，然后在 {@link DataSourceRegistry} 中注册。
 *
 * <p>本示例定义了一个包含常见字段类型的"示例数据"表，包括：
 * 文本（主键）、数字（整数/浮点）、单选、日期、链接等。
 */
public class DemoDataSourceConfig implements DataSourceConfig {

    public static final DemoDataSourceConfig INSTANCE = new DemoDataSourceConfig();

    @Override
    public String getDataSourceId() {
        return "demo";
    }

    @Override
    public String getTableName() {
        return "示例数据";
    }

    @Override
    public List<FieldDefinition> getFields() {
        return Arrays.asList(
                FieldDefinition.textPrimary("id", "ID", "记录唯一标识"),
                FieldDefinition.text("name", "名称", "记录名称"),
                FieldDefinition.singleSelect("status", "状态", "当前状态",
                        "待处理", "进行中", "已完成", "已取消"),
                FieldDefinition.intField("count", "数量", "统计数量"),
                FieldDefinition.floatField("amount", "金额", "金额（元）"),
                FieldDefinition.date("created_at", "创建时间", "记录创建时间"),
                FieldDefinition.date("updated_at", "更新时间", "最近更新时间"),
                FieldDefinition.text("description", "描述", "详细描述信息"),
                FieldDefinition.urlField("link", "链接", "相关链接")
        );
    }
}
