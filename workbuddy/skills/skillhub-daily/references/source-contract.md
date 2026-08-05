# SkillHub API 接口契约

## 基础信息

- **API 基地址**：`https://api.skillhub.cn`
- **认证方式**：无需认证
- **前端页面**：`https://skillhub.cn/skills?sort=downloads`

## 核心接口

### 1. 下载榜列表

```
GET /api/skills?page={page}&pageSize={size}&sortBy=downloads&order=desc
```

**参数**：

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| page | int | 1 | 页码 |
| pageSize | int | 50 | 每页条数（最大50） |
| sortBy | string | downloads | 排序字段 |
| order | string | desc | 排序方向 |

**响应**：

```json
{
  "code": 0,
  "data": {
    "skills": [
      {
        "slug": "skill-name",
        "name": "Skill名称",
        "ownerName": "作者",
        "category": "developer-tools",
        "description_zh": "中文描述",
        "description": "英文描述",
        "downloads": 12345,
        "installs": 8900,
        "stars": 456,
        "score": 4.5,
        "version": "1.0.0",
        "homepage": "https://...",
        "labels": { "requires_api_key": false },
        "source": "github"
      }
    ],
    "total": 77000
  }
}
```

### 2. 分类列表

```
GET /api/v1/categories
```

**响应**：

```json
{
  "items": [
    {
      "key": "developer-tools",
      "name": "开发工具",
      "nameEn": "developer-tools",
      "sortOrder": 10,
      "active": true
    }
  ]
}
```

**7大分类**：

| key | 中文名 | 全站Skill数 |
|-----|--------|------------|
| ai-intelligence | AI 智能 | ~3600 |
| developer-tools | 开发工具 | ~6400 |
| productivity | 效率提升 | ~4400 |
| data-analysis | 数据分析 | ~3900 |
| content-creation | 内容创作 | ~3100 |
| security-compliance | 安全合规 | ~2100 |
| communication-collaboration | 通讯协作 | ~1400 |

### 3. 分类筛选

```
GET /api/skills?category={key}&pageSize={size}&sortBy=downloads&order=desc
```

与下载榜列表接口格式相同，增加 `category` 筛选参数。

### 4. Skill详情

```
GET /api/v1/skills/{slug}
```

**注意**：此接口部分 slug 可能返回空的 `skill` 字段，建议优先使用列表接口的 `description_zh` 字段。

## 衍生指标计算

### 收藏率

```python
star_rate = (stars / downloads * 100) if downloads > 0 else 0.0
```

### 安装转化率

```python
install_rate = (installs / downloads * 100) if downloads > 0 else 0.0
```

### 活跃安装率

```python
active_rate = (stars / installs * 100) if installs > 0 else 0.0
```

### 综合潜力分

```python
potential_score = (
    star_rate_normalized * 40 +
    install_rate_normalized * 30 +
    active_rate_normalized * 20 +
    star_bonus * 10
)
```

归一化到 0-100 分。

## 潜力筛选规则

1. **收藏率 Top10**（始终生效，不需历史数据）
2. **被埋没的金子**：收藏率高但排名>20（始终生效）
3. **新进 Top100** / 下载增量+星标增量 / 安装增量 / 排名上升 / 收藏率上升（需历史数据对比）

## 请求规范

- User-Agent: `SkillHub-Daily/5.0`
- Accept: `application/json`
- Referer: `https://skillhub.cn/`
- 请求超时: 20秒
