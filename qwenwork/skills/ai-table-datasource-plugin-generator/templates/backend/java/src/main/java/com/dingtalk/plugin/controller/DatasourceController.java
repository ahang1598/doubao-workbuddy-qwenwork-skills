package com.dingtalk.plugin.controller;

import com.dingtalk.plugin.model.ApiResponse;
import com.dingtalk.plugin.model.RecordsRequest;
import com.dingtalk.plugin.model.RecordsResponse;
import com.dingtalk.plugin.model.SheetMetaRequest;
import com.dingtalk.plugin.model.SheetMetaResponse;
import com.dingtalk.plugin.service.RecordService;
import com.dingtalk.plugin.service.SheetMetaService;
import com.dingtalk.plugin.util.SignatureUtil;
import com.alibaba.fastjson.JSON;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import javax.servlet.http.HttpServletRequest;
import java.util.Collections;
import java.util.Map;

/**
 * 数据源控制器：提供 AI 表格数据源协议的两个核心接口。
 *
 * <ul>
 *   <li>POST /api/sheet_meta — 返回数据表结构（字段定义）</li>
 *   <li>POST /api/records — 返回数据记录（支持分页）</li>
 * </ul>
 *
 * <p>AI 表格服务端会在请求 Header 中携带签名信息，本控制器负责验证签名。
 */
@Slf4j
@RestController
@RequestMapping("/api")
public class DatasourceController {

    private static final String HEADER_TIMESTAMP = "Ding-Docs-Timestamp";
    private static final String HEADER_SIGNATURE = "Ding-Docs-Signature";
    private static final long MAX_TIMESTAMP_SKEW_MS = 5 * 60 * 1000L;

    @Autowired
    private SheetMetaService sheetMetaService;

    @Autowired
    private RecordService recordService;

    @Value("${plugin.secret-key}")
    private String secretKey;

    @Value("${plugin.enable-signature-verification:true}")
    private boolean enableSignatureVerification;

    @GetMapping("/health")
    public Map<String, String> health() {
        return Collections.singletonMap("status", "ok");
    }

    @PostMapping("/sheet_meta")
    public ApiResponse<SheetMetaResponse> getSheetMeta(
            @RequestBody SheetMetaRequest request,
            HttpServletRequest httpRequest) {

        log.info("[sheet_meta] requestId={}", request.getRequestId());

        if (!verifySignature(httpRequest, request)) {
            return ApiResponse.error(10004, "身份校验失败");
        }

        try {
            return ApiResponse.success(sheetMetaService.getSheetMeta(request));
        } catch (Exception e) {
            log.error("[sheet_meta] 失败, requestId={}", request.getRequestId(), e);
            return ApiResponse.error(10005, "三方系统异常，请检查服务日志");
        }
    }

    @PostMapping("/records")
    public ApiResponse<RecordsResponse> getRecords(
            @RequestBody RecordsRequest request,
            HttpServletRequest httpRequest) {

        log.info("[records] requestId={}, nextToken={}, maxResults={}, params={}",
                request.getRequestId(), request.getNextToken(),
                request.getMaxResults(), request.getParams());

        if (!verifySignature(httpRequest, request)) {
            log.warn("[records] 签名校验失败, requestId={}", request.getRequestId());
            return ApiResponse.error(10004, "身份校验失败");
        }

        try {
            RecordsResponse result = recordService.getRecords(request);
            log.info("[records] 成功, requestId={}, records={}, hasMore={}, total={}",
                    request.getRequestId(),
                    result.getRecords() != null ? result.getRecords().size() : 0,
                    result.getHasMore(), result.getTotal());
            return ApiResponse.success(result);
        } catch (Exception e) {
            log.error("[records] 失败, requestId={}, params={}", request.getRequestId(), request.getParams(), e);
            return ApiResponse.error(10005, "三方系统异常，请检查服务日志");
        }
    }

    /**
     * 签名验证：HMAC-SHA256(body + timestamp)
     * 详见数据源开发文档中的签名算法说明
     */
    private boolean verifySignature(HttpServletRequest httpRequest, Object requestBody) {
        if (!enableSignatureVerification) {
            log.warn("签名验证已关闭，生产环境请设置 plugin.enable-signature-verification=true");
            return true;
        }

        String timestamp = httpRequest.getHeader(HEADER_TIMESTAMP);
        String signature = httpRequest.getHeader(HEADER_SIGNATURE);

        if (timestamp == null || signature == null) {
            log.warn("请求缺少签名 Header");
            return false;
        }

        if (!isTimestampFresh(timestamp)) {
            log.warn("请求时间戳无效或已过期");
            return false;
        }

        try {
            // 必须使用 fastjson 序列化，与 AI 表格服务端约定的签名算法保持一致
            String body = JSON.toJSONString(requestBody);
            return SignatureUtil.verifySignature(secretKey, body + timestamp, signature);
        } catch (Exception e) {
            log.error("签名验证异常", e);
            return false;
        }
    }

    private boolean isTimestampFresh(String timestamp) {
        try {
            long value = Long.parseLong(timestamp);
            // Accept the common seconds and milliseconds representations.
            long timestampMs = value < 1_000_000_000_000L ? value * 1000L : value;
            return Math.abs(System.currentTimeMillis() - timestampMs) <= MAX_TIMESTAMP_SKEW_MS;
        } catch (NumberFormatException e) {
            return false;
        }
    }
}
