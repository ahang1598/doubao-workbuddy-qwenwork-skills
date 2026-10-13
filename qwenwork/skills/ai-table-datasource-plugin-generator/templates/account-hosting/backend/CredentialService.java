package com.dingtalk.plugin.service;

import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.TypeReference;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import javax.crypto.Cipher;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Arrays;
import java.util.Base64;
import java.util.Map;

/**
 * 凭证 Token 解密服务
 *
 * 使用场景：
 *   前端调用 account.getCredentialToken(accountId) 换取 credentialToken，
 *   将其传给插件服务端（如 POST /api/tables），由本服务解密后得到明文凭证 Map。
 *
 * 使用示例：
 *   {@code
 *   @PostMapping("/api/tables")
 *   public Map<String, Object> getTables(@RequestBody Map<String, String> body) throws Exception {
 *       Map<String, String> credentials = credentialService.decrypt(body.get("credentialToken"));
 *       String apiKey = credentials.get("apiKey"); // key 与前端 account.create 时的 credentials 一致
 *       // ... 调用三方 API
 *   }
 *   }
 *
 * 前提配置：
 *   在开放平台的酷应用配置页中填写 encryptionKey，并在 application.yml 中配置：
 *     plugin.encryption-key: your-encryption-key
 *   未配置时 token 为明文 Base64url 编码，直接解码即可（适合开发测试阶段）。
 */
@Slf4j
@Service
public class CredentialService {

    /**
     * 在开放平台配置的加密密钥（对应酷应用配置页的 encryptionKey 字段）
     * 未配置时为空字符串，此时 token 为明文 Base64url 编码
     */
    @Value("${plugin.encryption-key:}")
    private String encryptionKey;

    /**
     * 解密 credentialToken，返回明文凭证 Map
     *
     * @param credentialToken 前端通过 getCredentialToken 获取到的 token（有效期 5 分钟）
     * @return 明文凭证 Map，key 与前端 account.create 时传入的 credentials 字段一致
     * @throws SecurityException        token 已过期
     * @throws IllegalArgumentException token 版本不支持或格式错误
     * @throws Exception                解密失败（encryptionKey 不匹配等）
     */
    public Map<String, String> decrypt(String credentialToken) throws Exception {
        if (encryptionKey == null || encryptionKey.isEmpty()) {
            // 未配置 encryptionKey：token 为 Base64url 编码的明文凭证 JSON
            byte[] raw = Base64.getUrlDecoder().decode(credentialToken);
            return JSON.parseObject(new String(raw, StandardCharsets.UTF_8),
                    new TypeReference<Map<String, String>>() {});
        }

        // 配置了 encryptionKey：token 为 AES-256-GCM 加密结构的 Base64url 编码
        byte[] raw = Base64.getUrlDecoder().decode(credentialToken);
        ByteBuffer buf = ByteBuffer.wrap(raw);

        byte version = buf.get();
        if (version != 0x01) {
            throw new IllegalArgumentException("不支持的 credentialToken 版本: " + version);
        }

        long expireAt = buf.getLong();
        if (System.currentTimeMillis() > expireAt) {
            throw new SecurityException("credentialToken 已过期，请重新获取");
        }

        byte[] iv = new byte[12];
        buf.get(iv);

        byte[] cipherWithTag = new byte[buf.remaining()];
        buf.get(cipherWithTag);

        // 派生 AES 密钥：SHA-256(encryptionKey) 取前 32 字节
        byte[] aesKey = Arrays.copyOf(
                MessageDigest.getInstance("SHA-256")
                        .digest(encryptionKey.getBytes(StandardCharsets.UTF_8)),
                32);

        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.DECRYPT_MODE,
                new SecretKeySpec(aesKey, "AES"),
                new GCMParameterSpec(128, iv));
        // AAD：expireAt 的 big-endian 8 字节，必须与加密时一致
        cipher.updateAAD(ByteBuffer.allocate(8).putLong(expireAt).array());

        byte[] plaintext = cipher.doFinal(cipherWithTag);
        return JSON.parseObject(new String(plaintext, StandardCharsets.UTF_8),
                new TypeReference<Map<String, String>>() {});
    }
}
