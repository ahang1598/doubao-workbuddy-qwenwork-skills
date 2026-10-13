package com.dingtalk.plugin.service;

import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONObject;
import com.dingtalk.plugin.datasource.DataSourceConfig;
import com.dingtalk.plugin.datasource.DataSourceRegistry;
import com.dingtalk.plugin.datasource.FieldDefinition;
import com.dingtalk.plugin.model.SheetMetaRequest;
import com.dingtalk.plugin.model.SheetMetaResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * 表结构服务：根据前端传入的 dataType 返回对应数据源的字段结构。
 *
 * <p>数据源配置统一通过 {@link DataSourceRegistry} 管理，
 * 每个数据源的字段定义在独立的 Config 类中维护。
 */
@Slf4j
@Service
public class SheetMetaService {

    public SheetMetaResponse getSheetMeta(SheetMetaRequest request) {
        log.info("[getSheetMeta] requestId={}, params={}", request.getRequestId(), request.getParams());

        JSONObject params = parseParams(request.getParams());
        String dataType = params.getString("dataType");

        // 如果前端未传 dataType，使用默认数据源
        if (dataType == null || dataType.trim().isEmpty()) {
            dataType = "demo";
            log.info("[getSheetMeta] dataType 为空，使用默认数据源: {}", dataType);
        }

        // 通过注册表获取数据源配置
        DataSourceConfig config = DataSourceRegistry.get(dataType);
        if (config == null) {
            throw new IllegalArgumentException("不支持的数据类型: " + dataType
                    + "，已注册的数据源: " + DataSourceRegistry.getDataSourceIds());
        }

        return buildSheetMetaFromConfig(config);
    }

    /**
     * 根据 DataSourceConfig 构建 SheetMetaResponse。
     */
    private SheetMetaResponse buildSheetMetaFromConfig(DataSourceConfig config) {
        List<SheetMetaResponse.Field> fields = config.getFields().stream()
                .map(this::convertFieldDefinition)
                .collect(Collectors.toList());

        return SheetMetaResponse.builder()
                .sheetName(config.getTableName())
                .fields(fields)
                .build();
    }

    /**
     * 将 FieldDefinition 转换为 SheetMetaResponse.Field。
     */
    private SheetMetaResponse.Field convertFieldDefinition(FieldDefinition def) {
        SheetMetaResponse.Field.FieldBuilder builder = SheetMetaResponse.Field.builder()
                .id(def.getId())
                .name(def.getName())
                .type(def.getType())
                .isPrimary(def.isPrimary())
                .description(def.getDescription());

        // 构建 property
        Map<String, Object> property = new HashMap<>();

        // 数字类型添加 formatter
        if ("number".equals(def.getType()) && def.getFormatter() != null) {
            property.put("formatter", def.getFormatter());
        }

        // 单选类型添加 choices
        if ("singleSelect".equals(def.getType()) && def.getChoices() != null) {
            List<Map<String, Object>> choices = Arrays.stream(def.getChoices())
                    .map(this::buildChoice)
                    .collect(Collectors.toList());
            property.put("choices", choices);
        }

        if (!property.isEmpty()) {
            builder.property(property);
        }

        return builder.build();
    }

    private JSONObject parseParams(String params) {
        if (params == null || params.trim().isEmpty()) {
            return new JSONObject();
        }
        try {
            JSONObject jsonObject = JSON.parseObject(params);
            return jsonObject != null ? jsonObject : new JSONObject();
        } catch (Exception e) {
            log.warn("解析 params 失败: {}", e.getMessage());
            throw new IllegalArgumentException("params 格式错误: " + e.getMessage());
        }
    }

    private Map<String, Object> buildChoice(String name) {
        Map<String, Object> choice = new HashMap<>();
        choice.put("name", name);
        return choice;
    }
}
