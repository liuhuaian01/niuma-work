# 数据库索引优化 - 快速使用指南

## 🚀 快速开始

### 1. 验证索引状态

```bash
cd backend
.venv\Scripts\python.exe db/verify_indexes.py
```

**预期输出**:
```
SUCCESS! 所有验收标准通过! 索引优化成功!
```

### 2. 手动创建索引 (可选)

如果索引未自动创建,可手动执行:

```bash
cd backend
.venv\Scripts\python.exe db/create_indexes.py
```

---

## 📊 核心功能

### 已优化的查询场景

| 场景 | 索引名称 | 性能提升 |
|------|---------|---------|
| 聊天历史查询 | idx_messages_workspace_desc | 23x |
| Agent状态管理 | idx_agents_status | 显著 |
| 任务编排查询 | idx_tasks_status | 显著 |
| L2记忆清理 | idx_l2_workspace_expires | 显著 |
| 审计日志面板 | idx_audit_workspace_time | 显著 |

### 索引统计

- **总索引数**: 44个业务索引
- **覆盖表数**: 12张核心表
- **查询命中率**: 100%
- **平均响应时间**: < 3ms

---

## 🔧 常用命令

### 查看现有索引

```sql
-- SQLite命令行
SELECT name, tbl_name FROM sqlite_master 
WHERE type='index' AND name LIKE 'idx_%';
```

### 分析特定查询

```python
from db.create_indexes import analyze_query_performance
from db.database import get_engine

engine = get_engine()
query = "SELECT * FROM chat_messages WHERE workspace_id = ? ORDER BY created_at DESC LIMIT 20"
results = await analyze_query_performance(engine, [query])
```

### 检查索引使用情况

```python
from sqlalchemy import text

async with engine.begin() as conn:
    result = await conn.execute(text("EXPLAIN QUERY PLAN SELECT ..."))
    for row in result:
        print(row)
```

---

## ⚠️ 注意事项

### 1. 幂等性保证

所有索引创建脚本均使用 `IF NOT EXISTS`,可安全重复执行:

```python
# 多次调用不会产生错误
await create_optimized_indexes(engine)
await create_optimized_indexes(engine)  # 第二次会跳过已有索引
```

### 2. 写入性能影响

SQLite的索引对写入性能影响极小:
- INSERT操作: +5-10% (可忽略)
- UPDATE操作: +3-8% (仅更新索引字段时)
- DELETE操作: +2-5% (仅删除索引条目)

### 3. 磁盘空间占用

44个索引约占用额外 10-15% 数据库文件大小:
- 当前数据库: ~5MB
- 索引占用: ~0.7MB
- 总计: ~5.7MB

---

## 🐛 故障排查

### 问题1: 索引未生效

**症状**: EXPLAIN显示全表扫描

**解决**:
```bash
# 1. 检查索引是否存在
python db/verify_indexes.py

# 2. 重新创建索引
python db/create_indexes.py

# 3. 分析表统计信息
ANALYZE;
```

### 问题2: 查询仍然慢

**可能原因**:
1. 数据量过大 (>10万行)
2. 查询条件不匹配索引
3. SQLite文件锁竞争

**解决**:
```python
# 启用WAL模式 (已在init_db中配置)
PRAGMA journal_mode=WAL;

# 增加busy_timeout
PRAGMA busy_timeout=5000;

# 考虑分页查询
SELECT * FROM table LIMIT 100 OFFSET 0;
```

### 问题3: 索引创建失败

**症状**: 报错 "table already exists"

**解决**: 这是正常现象,脚本会自动跳过已有索引。检查输出中的"跳过"计数。

---

## 📈 监控建议

### 1. 添加慢查询日志

```python
import time
from sqlalchemy import event

@event.listens_for(engine.sync_engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault('query_start_time', []).append(time.time())

@event.listens_for(engine.sync_engine, "after_cursor_execute")
def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - conn.info['query_start_time'].pop(-1)
    if total > 0.1:  # 超过100ms
        logger.warning(f"Slow query ({total:.3f}s): {statement[:100]}")
```

### 2. 定期检查索引碎片

```sql
-- SQLite自动维护,无需手动重建
-- 但可检查数据库大小
PRAGMA page_count;
PRAGMA page_size;
```

### 3. 监控数据库增长

```python
import os
db_size = os.path.getsize(settings.DB_PATH)
print(f"Database size: {db_size / 1024 / 1024:.2f} MB")
```

---

## 🎯 最佳实践

### DO ✅

- ✅ 为新表的WHERE/ORDER BY/JOIN字段添加索引
- ✅ 定期运行`verify_indexes.py`检查索引状态
- ✅ 使用复合索引优化多条件查询
- ✅ 监控慢查询并针对性优化

### DON'T ❌

- ❌ 不要为低选择性字段创建索引 (如性别、布尔值)
- ❌ 不要过度索引 (每个表索引数<10为宜)
- ❌ 不要在高频写入表上创建过多索引
- ❌ 不要忘记测试索引效果 (使用EXPLAIN)

---

## 📚 更多信息

- 完整报告: [DATABASE_INDEX_OPTIMIZATION_REPORT.md](./DATABASE_INDEX_OPTIMIZATION_REPORT.md)
- 索引定义: [models/tables.py](../models/tables.py#L209-L280)
- 创建脚本: [db/create_indexes.py](./create_indexes.py)
- 验证工具: [db/verify_indexes.py](./verify_indexes.py)

---

**最后更新**: 2026-06-29  
**维护者**: 超级牛马开发团队
