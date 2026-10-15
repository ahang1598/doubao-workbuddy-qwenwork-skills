# 威胁模式种子库

本文件是精选的威胁模式种子，按 STRIDE 六类组织。在威胁识别阶段，这些模式作为"参考而非上限"，帮助分析者快速定位常见威胁，但不应局限于这些模式——应根据具体设计的技术栈和业务场景扩展。

## 类别指导语（CATEGORY_GUIDE）

在识别每类威胁时，参考以下指导语确保方向正确：

- **Spoofing**：Impersonation of users/services/components; weak/missing authentication; stolen credentials; cert/JWT/session-token forgery.
- **Tampering**：Unauthorized modification of data in transit or at rest; missing integrity checks; insecure deserialization; MITM alteration.
- **Repudiation**：Actions that can be denied; missing/tamperable audit logs; shared accounts; unsigned critical operations.
- **Information Disclosure**：Leakage of sensitive data via logs/errors/responses/transit; missing encryption; overbroad data exposure.
- **Denial of Service**：Resource/algorithmic exhaustion; missing rate limits/throttling/backpressure; storage or connection starvation.
- **Elevation of Privilege**：Gaining unauthorized privileges; IDOR/missing authz checks; JWT alg confusion; privesc via misconfig.

## Spoofing（仿冒）

1. **入口点弱认证或缺失认证**：服务间调用无 mTLS/API Key，公网接口无认证机制
2. **凭证/会话令牌窃取**：通过日志泄露、Referer 泄露、不安全存储（本地明文、URL 参数）获取凭证
3. **JWT/Token 伪造与重放**：算法混淆（alg=none）、缺失签名校验、Token 无过期时间、可重放
4. **上下游组件冒充**：无双向 TLS 或服务身份验证，攻击者可伪造上游/下游服务
5. **账户接管**：密码重置逻辑缺陷、OTP 暴力破解、特权账户无 MFA、会话固定攻击

## Tampering（篡改）

1. **不安全反序列化**：对不可信输入使用 pickle、yaml.load、Java ObjectInputStream、对象映射器自动绑定
2. **缺失完整性校验**：数据流或存储状态无 MAC/签名，配置/功能开关可被篡改
3. **注入攻击**：SQL 注入、命令注入、Prompt 注入、LDAP 注入、XPath 注入，允许攻击者修改查询或控制流程
4. **中间人篡改**：非 TLS 通道或 TLS 证书校验被禁用/弱化（跳过校验、信任所有证书）
5. **未签名产物**：固件/容器镜像/部署包无签名，构建流水线可变，依赖包未锁定版本

## Repudiation（抵赖）

1. **关键操作无审计日志**：认证、支付、配置变更、数据导出、权限变更等操作未写入不可篡改审计日志
2. **审计日志可篡改**：审计日志可被同一主体修改/删除，或缺少用户标识+时间戳+操作详情
3. **共享账户**：使用共享服务账户或通用账户，无法追溯具体操作人
4. **跨系统事务无追踪**：跨系统调用无签名/可追溯请求链，出现问题时各方可互相推诿

## Information Disclosure（信息泄露）

1. **敏感信息写入日志/错误/指标**：密钥、Token、PII、密码写入应用日志、错误信息、监控指标或 URL 查询参数
2. **传输层不安全**：数据通过明文传输，或 TLS 版本过旧/密码套件弱化/证书校验被禁用
3. **静态数据未加密**：数据库/对象存储/磁盘中的敏感数据未加密，或密钥与数据同存/存入代码仓库/配置文件
4. **过宽的数据暴露**：API 响应包含过多字段、GraphQL 查询无字段限制、批量赋值（Mass Assignment）泄露不应暴露的字段
5. **错误信息泄露内部细节**：错误响应暴露堆栈跟踪、内部主机名、IP 地址、软件版本、数据库类型等内部信息

## Denial of Service（拒绝服务）

1. **无限制的资源消耗**：无请求大小/Body/超时限制，用户输入触发 O(n²) 算法或正则表达式灾难性回溯（ReDoS）
2. **缺失限流/节流/背压**：公网或多租户端点无速率限制、无并发控制、无背压机制，可被流量洪泛打垮
3. **连接/线程池耗尽**：连接池/线程池配置过小或无超时，无界队列持续增长，缓存击穿/雪崩导致后端过载
4. **存储耗尽**：未清理的日志、上传文件、备份数据持续增长，无存储配额，导致磁盘满服务不可用
5. **LLM/Agent 调用无上限**：不可信输入可触发昂贵的 LLM/Agent 调用，无 Token/迭代/工具调用次数上限，导致成本失控或服务不可用

## Elevation of Privilege（权限提升）

1. **IDOR/缺失对象级授权**：用户 A 可通过修改资源 ID 访问用户 B 的资源（Insecure Direct Object Reference），仅做了角色级鉴权而未做对象级/租户级鉴权
2. **权限检查缺失或仅客户端**：角色/权限检查仅在前端实现，后端无校验；管理路径无访问控制；功能级权限缺失
3. **JWT 声明篡改/Scope 膨胀**：JWT 中 role/scope/tenant_id 等声明可被篡改，跨租户 confused deputy 攻击，Token 签名校验不严格
4. **错误配置的 IAM/服务账户**：IAM 策略过宽（通配符权限）、服务账户权限过大、SSRF 可访问内部元数据服务（169.254.169.254 获取临时凭证）
5. **不安全默认值**：默认管理员账户（admin/admin）、调试端点暴露、actuator/env 端点未保护、开发环境配置未在生产关闭

## 使用说明

1. 这些模式是**种子**，不是穷举列表。分析时应根据具体系统的技术栈、业务场景和架构特点扩展
2. 每条威胁必须**关联到具体的 DFD 元素**，不能脱离架构泛泛而谈
3. 优先关注与设计文档中**实际存在的技术和组件**相关的威胁模式
4. 对每条匹配的模式，需要**具体化**为该系统特有的攻击场景，而非直接复制模式描述
5. 威胁的**置信度**取决于设计文档中是否有明确证据支持；无证据的威胁应标注为 needs_confirmation

## 按需筛选规则

在威胁识别阶段，不需要加载全部 30 条种子。应根据当前 DFD 元素的适用 STRIDE 类别，仅加载对应类别的种子。例如：

- 对 `external_entity` 类型元素：仅加载 Spoofing（5 条）和 Repudiation（4 条）= 9 条
- 对 `process` 类型元素：加载全部六类 = 29 条
- 对 `data_store` 类型元素：仅加载 Tampering（5 条）、Repudiation（4 条）、Information Disclosure（5 条）= 14 条
- 对 `data_flow` 类型元素：仅加载 Tampering（5 条）、Information Disclosure（5 条）、Denial of Service（5 条）= 15 条
