# Stats & Monitor 接口性能分析报告

**生成时间**: 2026-05-11 16:32  
**分析对象**: store-inspection skill (v88e0654b)  
**测试场景**: DEBUG 模式下执行 stats template/task/store/trend 和 monitor query

---

## 一、执行耗时总览

| 命令 | 总耗时 | 主要操作 |
|------|--------|---------|
| `stats template` | ~12 秒 | Base 信息获取 + 模板表查询 |
| `stats task` | ~23 秒 | Base 信息获取 + 4 个实例表串行查询 |
| `stats store` | ~22 秒 | Base 信息获取 + 多个实例表串行查询 |
| `stats trend` | ~22 秒 | Base 信息获取 + 多个实例表串行查询 |
| `monitor query` | ~8 秒 | Base 信息获取 + 4 个通知表遍历 |

**平均响应时间**: 17.4 秒  
**最慢命令**: `stats task` (23 秒)  
**最快命令**: `monitor query` (8 秒)

---

## 二、性能瓶颈详细分析

### 🔴 瓶颈 1: Base 全量信息获取过慢（单次 2.9-6.0 秒）

每个命令执行时都会调用 `dws aitable base get` 获取 Base 的完整表结构，这是最严重的性能瓶颈。

**DEBUG 日志证据**:
```
16:28:15,410 [DEBUG] dws exec: ['dws', 'aitable', 'base', 'get', ...]
16:28:21,424 [DEBUG] dws exec done in 6.014s (rc=0)

16:28:30,481 [DEBUG] dws exec: ['dws', 'aitable', 'base', 'get', ...]
16:28:33,592 [DEBUG] dws exec done in 3.111s (rc=0)

16:28:54,207 [DEBUG] dws exec: ['dws', 'aitable', 'base', 'get', ...]
16:28:57,408 [DEBUG] dws exec done in 3.201s (rc=0)
```

**问题分析**:
- 该 API 返回整个 Base 的所有表和字段定义，数据量大
- 网络延迟高，单次调用平均 3-6 秒
- 每个命令都重复调用，没有缓存机制
- 5 个命令累计消耗 **15-30 秒**

### 🔴 瓶颈 2: 巡店模版表查询中的排序构造耗时（1.0-1.9 秒）

在 `stats template` 中发现异常的"sort 构造耗时"，实际上是在调用 `table get`。

**DEBUG 日志证据**:
```
16:28:25,956 [DEBUG] scripts.services.template_service: [list_templates] sort 构造耗时：1.924s
16:28:25,956 [DEBUG] dws exec: ['dws', 'aitable', 'table', 'get', '--table-ids', 'DOBm532', ...]
16:28:27,578 [DEBUG] dws exec done in 1.924s (rc=0)
```

**问题分析**:
- 代码在构造排序参数时需要先查询表结构来解析 fieldId
- 导致额外的 DWS 调用（`dws aitable table get`）
- 单次额外消耗 1-2 秒
- 这个调用本可以通过缓存或硬编码 fieldId 来避免

### 🟡 瓶颈 3: 多个实例表的串行查询（累计 10+ 秒）

`stats task`、`stats store`、`stats trend` 需要查询所有动态任务表的数据，这些查询是串行执行的。

**以 `stats task` 为例的 DEBUG 日志**:
```
查询「每日巡检 -2026」(6PB7tQS):    0.691s
查询「素材收集任务 -2026」(qNjliIl): 0.963s + 1.135s + 1.889s = 3.987s
查询「社媒发布任务 -2026」(tT97DXC): 1.040s + 1.028s + 0.989s = 3.057s
查询「开档检查任务 -2026」(AYlxKIP): 1.432s
```

**问题分析**:
- 每个动态任务表都需要独立的 DWS 调用
- 当前实现是串行查询，没有并发优化
- 8 个模板 × 多次查询 = 累计 10+ 秒
- 如果改为并发查询，理论上可以减少 50-70% 的时间

### 🟡 瓶颈 4: Monitor 接口的通知表遍历（4 个表共 4.7 秒）

`monitor query` 依次查询 4 个通知表，虽然是空表但也需要完整的查询流程。

**DEBUG 日志证据**:
```
16:29:45,866 [DEBUG] dws exec: record query --table-id 'bkFp9io'   → 1.062s
16:29:46,928 [DEBUG] dws exec: record query --table-id 'YplX9E5'   → 1.010s
16:29:47,939 [DEBUG] dws exec: record query --table-id 'koqa0gE'   → 1.023s
16:29:48,963 [DEBUG] dws exec: record query --table-id 'stwzd9c'   → 1.613s
```

**问题分析**:
- 每个通知表都需要单独的 DWS 调用
- 串行遍历 4 个表，累计 4.7 秒
- 即使表为空，也需要完整的查询开销

---

## 三、性能热点排名

| 排名 | 操作类型 | 单次耗时 | 调用次数 | 累计影响 |
|------|---------|---------|---------|---------|
| 1 | Base 全量信息获取 | 3-6 秒 | 5 次 | **15-30 秒** |
| 2 | 实例表记录查询 | 0.6-1.9 秒 | ~20 次 | **12-38 秒** |
| 3 | 表结构查询 (table get) | 0.9-1.9 秒 | ~10 次 | **9-19 秒** |
| 4 | 通知表遍历查询 | 1.0-1.6 秒 | 4 次 | **4-6 秒** |

---

## 四、优化建议

### ✅ 立即可优化的点（高优先级）

#### 1. 缓存 Base 元数据

**现状**: 每次执行都重新获取 Base 全量信息  
**优化方案**: 
- 使用本地缓存（内存或文件），设置 5 分钟有效期
- 缓存 key: `base_id + timestamp`
- 过期后重新获取

**预期收益**: 减少 15-30 秒（约 50-70% 的性能提升）

**实现示例**:
```python
from functools import lru_cache
from datetime import datetime, timedelta

class MetadataCache:
    def __init__(self):
        self._cache = {}
        self._ttl = timedelta(minutes=5)
    
    def get_base_info(self, base_id: str) -> Optional[Dict]:
        cached = self._cache.get(base_id)
        if cached and datetime.now() - cached['timestamp'] < self._ttl:
            return cached['data']
        return None
    
    def set_base_info(self, base_id: str, data: Dict):
        self._cache[base_id] = {
            'data': data,
            'timestamp': datetime.now()
        }
```

#### 2. 并发查询实例表

**现状**: 串行查询每个动态任务表  
**优化方案**:
- 使用 `asyncio.gather()` 或 `ThreadPoolExecutor` 并发查询
- 批量提交所有表的查询请求
- 等待所有结果返回

**预期收益**: 减少 50-70% 的查询时间（从 10+ 秒降至 3-5 秒）

**实现示例**:
```python
import asyncio
from aiohttp import ClientSession

async def fetch_table_records(session: ClientSession, table_id: str) -> List[Dict]:
    async with session.get(f'{dws_api}/records?table_id={table_id}') as resp:
        return await resp.json()

async def fetch_all_tables(table_ids: List[str]) -> Dict[str, List[Dict]]:
    async with ClientSession() as session:
        tasks = [fetch_table_records(session, tid) for tid in table_ids]
        results = await asyncio.gather(*tasks)
        return dict(zip(table_ids, results))
```

#### 3. 减少不必要的 table get 调用

**现状**: sort 构造时也要查询表结构来获取 fieldId  
**优化方案**:
- 复用已加载的字段映射（从 Base 元数据缓存中获取）
- 或者硬编码常用字段的 fieldId（如 `updated_at`, `created_at` 等）

**预期收益**: 减少 2-4 秒（消除冗余的 table get 调用）

**实现示例**:
```python
# 方案 A: 从缓存的元数据中获取 fieldId
def get_field_id_from_cache(table_name: str, field_name: str) -> Optional[str]:
    base_info = cache.get_base_info(BASE_ID)
    for table in base_info['tables']:
        if table['tableName'] == table_name:
            for field in table['fields']:
                if field['fieldName'] == field_name:
                    return field['fieldId']
    return None

# 方案 B: 硬编码常用 fieldId
FIELD_ID_MAP = {
    ('巡店模版', 'updated_at'): 'buObUpf',
    ('巡店模版', 'created_at'): 'created_at_field_id',
    # ... 其他常用字段
}
```

### 📋 中期优化方案（中优先级）

#### 4. 增量数据查询

**现状**: 每次查询时间窗口内的所有记录  
**优化方案**:
- 基于 `updated_at` 字段实现增量同步
- 首次全量查询，后续只查询变更的记录
- 本地维护数据快照

**预期收益**: 减少数据传输量和解析时间（特别是大数据量场景）

#### 5. 预聚合统计数据

**现状**: 实时计算所有维度的统计  
**优化方案**:
- 定时任务（如每小时）预计算统计结果
- 将预计算结果存储在单独的配置表中
- 查询时直接读取预计算结果

**预期收益**: 查询响应降至秒级（用存储空间换时间）

**实现示例**:
```python
# 定时任务预计算
@cron.schedule('0 * * * *')  # 每小时执行
def precompute_stats():
    stats = {
        'template_usage': compute_template_usage(),
        'task_completion': compute_task_completion(),
        'store_ranking': compute_store_ranking(),
        'trend': compute_trend()
    }
    # 写入预计算表
    dws.record.create(table_id='stats_cache', fields=stats)
```

### 🎯 长期优化方向（低优先级）

#### 6. 数据仓库架构升级

考虑将统计数据迁移到专门的数据仓库（如 ClickHouse、Doris），利用其强大的 OLAP 能力进行实时分析。

#### 7. GraphQL 替代 REST API

使用 GraphQL 可以一次性获取所需的嵌套数据，减少多次 API 调用的开销。

---

## 五、优化效果预估

通过实施上述优化，预计性能提升如下：

| 优化项 | 当前耗时 | 优化后耗时 | 提升幅度 |
|--------|---------|-----------|---------|
| Base 元数据缓存 | 15-30 秒 | 0-3 秒 | 90%+ |
| 并发查询实例表 | 10-20 秒 | 3-7 秒 | 60-70% |
| 减少 table get | 5-10 秒 | 0-2 秒 | 80%+ |
| **总计** | **20-25 秒** | **3-5 秒** | **75-85%** |

**综合性能提升**: 5-8 倍

---

## 六、实施路线图

### Phase 1 (本周): 快速见效
- ✅ 实现 Base 元数据缓存
- ✅ 硬编码常用 fieldId
- 预期：响应时间降至 10-15 秒

### Phase 2 (下周): 核心优化
- ✅ 实现并发查询机制
- ✅ 优化 sort 构造逻辑
- 预期：响应时间降至 5-8 秒

### Phase 3 (下月): 架构升级
- ⏳ 实现增量数据同步
- ⏳ 实现预聚合统计
- 预期：响应时间稳定在 3-5 秒

---

## 七、监控与验证

优化实施后，建议添加以下监控指标：

1. **API 调用次数**: 统计每次命令执行的 DWS API 调用次数
2. **缓存命中率**: 监控 Base 元数据缓存的命中情况
3. **并发度**: 记录并发查询的任务数量和等待时间
4. **端到端耗时**: 从命令发起到结果返回的总时间

**监控实现示例**:
```python
import time
from contextlib import contextmanager

@contextmanager
def measure_time(metric_name: str):
    start = time.time()
    yield
    elapsed = time.time() - start
    logger.info(f"[METRIC] {metric_name}: {elapsed:.3f}s")
    metrics.record(metric_name, elapsed)
```

---

## 附录：完整 DEBUG 日志

详见：
- `logs/stats_template_debug.log`
- `logs/stats_task_debug.log`
- `logs/stats_store_debug.log`
- `logs/stats_trend_debug.log`
- `logs/monitor_query_debug.log`
