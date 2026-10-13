package com.dingtalk.plugin.util;

import lombok.extern.slf4j.Slf4j;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Base64;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

/**
 * 签名工具类：实现 AI 表格数据源协议的签名验证。
 *
 * <p>签名算法：HMAC-SHA256(secretKey, body + timestamp)，结果 Base64 编码。
 */
@Slf4j
public class SignatureUtil {

    private static final String HMAC_SHA256_ALGORITHM = "HmacSHA256";

    /**
     * HMAC-SHA256 签名并 Base64 编码
     *
     * @param secretKey 签名密钥
     * @param content   待签名内容
     * @return Base64 编码的签名字符串
     */
    public static String hmacSha256Base64(String secretKey, String content) {
        try {
            Mac mac = Mac.getInstance(HMAC_SHA256_ALGORITHM);
            SecretKeySpec secretKeySpec = new SecretKeySpec(
                    secretKey.getBytes(StandardCharsets.UTF_8),
                    HMAC_SHA256_ALGORITHM
            );
            mac.init(secretKeySpec);
            byte[] hash = mac.doFinal(content.getBytes(StandardCharsets.UTF_8));
            return Base64.getEncoder().encodeToString(hash);
        } catch (Exception e) {
            log.error("签名计算失败", e);
            throw new RuntimeException("签名计算失败", e);
        }
    }

    /**
     * 验证签名
     *
     * @param secretKey 签名密钥
     * @param content   待验证内容（body + timestamp）
     * @param signature 请求中携带的签名
     * @return 签名是否匹配
     */
    public static boolean verifySignature(String secretKey, String content, String signature) {
        String expectedSignature = hmacSha256Base64(secretKey, content);
        return MessageDigest.isEqual(
                expectedSignature.getBytes(StandardCharsets.UTF_8),
                signature.getBytes(StandardCharsets.UTF_8)
        );
    }
}
