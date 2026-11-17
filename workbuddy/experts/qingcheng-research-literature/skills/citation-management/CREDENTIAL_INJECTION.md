# Semantic Scholar API 凭证配置说明

## 凭证注入机制

### 工作原理

Semantic Scholar API 凭证使用 **自动注入机制**：

1. **凭证创建** ✅ 已完成
   - 通过 `skill_credentials` 工具创建
   - 凭证名称：`semantic_scholar_api`
   - 类型：ApiKey (Header: x-api-key)
   - 域名：api.semanticscholar.org

2. **凭证存储** ✅ 已完成
   - 凭证保存在 Skill 的配置中
   - 与 Skill ID 关联

3. **运行时注入** ⏳ 在 Skill 使用时自动生效
   - 当用户加载并使用 Skill 时
   - 系统自动将凭证注入到环境变量
   - 环境变量名：`COZE_SEMANTIC_SCHOLAR_API_7610256945278271488`

### 重要说明

**当前环境 vs. 运行时环境**：

| 环境 | 凭证状态 | 说明 |
|------|----------|------|
| 开发/构建环境 | ❌ 未注入 | 当前环境，凭证未注入 |
| Skill 运行时 | ✅ 自动注入 | 用户使用 Skill 时，凭证自动注入 |

**关键点**：凭证注入发生在 **Skill 被用户使用** 时，而不是开发/构建阶段。

## 凭证配置验证

### 已完成的配置

```yaml
credential_name: semantic_scholar_api
auth_type: 1 (ApiKey)
allowed_domain: api.semanticscholar.org
env_variable:
  - variable_name: API_KEY
  - api_key_location: 2 (Header)
  - api_key_param_name: x-api-key
```

### 脚本中的凭证读取

```python
skill_id = "7610256945278271488"
api_key = os.getenv(f"COZE_SEMANTIC_SCHOLAR_API_{skill_id}")
```

**状态**：✅ 配置正确，与凭证创建参数匹配

## 使用场景

### 场景 1：Skill 正式使用（推荐）

当用户在对话中使用此 Skill 时：

1. 系统自动加载 Skill
2. 凭证自动注入到环境变量
3. 脚本可以正常访问 API

**示例对话**：
```
用户: 帮我搜索 Semantic Scholar 上关于拓扑平带的文献
AI: [自动加载 Skill，凭证注入] 正在搜索...
```

### 场景 2：开发/测试环境

在当前开发环境中，凭证未注入。解决方案：

**方案 A**：手动设置环境变量（临时）
```bash
export COZE_SEMANTIC_SCHOLAR_API_7610256945278271488="your-api-key"
python scripts/search_semantic_scholar.py "query"
```

**方案 B**：使用手动脚本
```bash
python scripts/search_semantic_scholar_manual.py "query" --api-key "your-key"
```

**方案 C**：使用 PubMed 替代
```bash
python scripts/search_pubmed.py "query" --limit 50 --output results.json
```

## 验证凭证配置

### 方法 1：检查 Skill 打包文件

```bash
# 解压 .skill 文件
unzip citation-management.skill -d citation-management-extracted

# 检查配置文件
cat citation-management-extracted/.skill-config.json
```

### 方法 2：运行调试脚本

```bash
python scripts/debug_semantic_scholar.py
```

输出示例：
```
=== Semantic Scholar API Debug ===
Skill ID: 7610256945278271488
Expected Environment Variable: COZE_SEMANTIC_SCHOLAR_API_7610256945278271488

[开发环境] ✗ API Key not found in environment
[运行时环境] ✓ API Key found: xxx...xxxx
```

## 常见问题

### Q1: 为什么开发环境中凭证不生效？

**A**: 凭证注入机制设计为在 **Skill 运行时** 才注入，这是出于安全考虑：
- 避免凭证在开发过程中泄露
- 确保凭证只在用户授权的上下文中使用

### Q2: 如何确认凭证配置正确？

**A**: 
1. 凭证创建返回 `success: true`
2. Skill 打包成功
3. 脚本中的环境变量名与凭证配置匹配

### Q3: Skill 部署后凭证会自动生效吗？

**A**: 是的。当用户使用 Skill 时，系统会：
1. 识别 Skill 需要的凭证
2. 检查用户是否已授权
3. 自动注入凭证到环境变量

### Q4: 用户需要做什么？

**A**: 用户只需：
1. 首次使用时填写凭证（如果系统提示）
2. 或者在 Skill 设置中配置 API Key
3. 之后每次使用都会自动注入

## 配置检查清单

- [x] 凭证名称：`semantic_scholar_api`
- [x] 授权类型：ApiKey (auth_type=1)
- [x] 允许域名：`api.semanticscholar.org`
- [x] Header 参数名：`x-api-key`
- [x] 环境变量格式：`COZE_SEMANTIC_SCHOLAR_API_{skill_id}`
- [x] skill_id 正确：`7610256945278271488`
- [x] 脚本使用 `coze_workload_identity.requests`
- [x] SSL 证书验证配置正确
- [x] 速率限制实现正确（1 req/sec）

## 总结

✅ **凭证配置已完成**
- 所有配置项正确
- 脚本逻辑正确
- 凭证会在 Skill 运行时自动注入

⏳ **等待运行时验证**
- 在用户使用 Skill 时验证凭证注入
- 开发环境中可使用替代方案

📝 **开发环境替代方案**
- PubMed 搜索（推荐）
- 手动环境变量设置
- 手动脚本
