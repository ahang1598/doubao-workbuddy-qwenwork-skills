package com.dingtalk.plugin.datasource;

import java.util.HashMap;
import java.util.Map;

/**
 * 字段值构建器：提供各类字段值的标准化构建方法。
 *
 * <p>用于将原始数据转换为 AI 表格 records 所需的字段值结构。
 */
public final class FieldValueBuilder {

    private FieldValueBuilder() {
        // 工具类禁止实例化
    }

    /**
     * 将 URL 字符串包装为链接字段值结构。
     *
     * @param url 原始 URL 字符串
     * @return {@code {"text": url, "link": url}}，若 url 为空则返回 null
     */
    public static Map<String, String> linkValue(String url) {
        if (url == null || url.isEmpty()) return null;
        Map<String, String> linkMap = new HashMap<>();
        linkMap.put("text", url);
        linkMap.put("link", url);
        return linkMap;
    }

    /**
     * 将带显示文本的 URL 包装为链接字段值结构。
     *
     * @param text 显示文本
     * @param url  链接地址
     * @return {@code {"text": text, "link": url}}
     */
    public static Map<String, String> linkValue(String text, String url) {
        if (url == null || url.isEmpty()) return null;
        Map<String, String> linkMap = new HashMap<>();
        linkMap.put("text", text != null ? text : url);
        linkMap.put("link", url);
        return linkMap;
    }

    /**
     * 将 "1"/"0" 标志位转换为 Boolean。
     *
     * @param flag 原始标志位字符串（"1" 或 "0"）
     * @return 1→true，其余→false，null→null
     */
    public static Boolean booleanFromFlag(String flag) {
        if (flag == null) return null;
        return "1".equals(flag);
    }
}
