# 文件上传底层说明

本 skill 不直接调业务网关端点，而是复用 `_shared/linkfox_paths.py` 的两个函数。

## get_sts_voucher()

- 调 `POST {LINKFOX_TOOL_GATEWAY}/oss/getStsVoucherByAPI`（缺省 `https://tool-gateway.linkfox.com`），`Authorization` 头取 `LINKFOX_AGENT_API_KEY`。
- 返回临时上传凭证（accessKeyId / accessKeySecret / securityToken / expiration）+ OSS 信息（endpoint / bucketName / dir / region）+ 约束（supportedTypes / maxFileSize / maxFileCount）。
- 最多重试 3 次、指数退避（1s→2s），仅对 408/429/5xx 重试；errcode≠200 直接抛错。

## upload_file(local_path, *, slug=None, ts=None, voucher=None)

- 用 `oss2` 以 STS 凭证上传到 `{dir}/{YYYY/MM}/{uuid}.{ext}`。
- 上传前校验：文件大小 ≤ `maxFileSize`、扩展名 ∈ `supportedTypes`，超限抛 `RuntimeError`。
- 成功后把 URL 登记进会话 `_meta.json` 的 `deliverables`。

返回：

| 字段 | 含义 |
|------|------|
| `url`  | 可公开访问的 HTTPS URL |
| `path` | OSS 对象键（如 `tmp/2026/06/abc123.png`） |
| `name` | 原始文件名 |
| `size` | 文件大小（字节） |
| `ext`  | 扩展名（不含点） |

## 依赖与环境

- `pip install oss2`
- `LINKFOX_AGENT_API_KEY`（必需）；`LINKFOX_TOOL_GATEWAY`（可选，覆盖 tool-gateway 地址）。
