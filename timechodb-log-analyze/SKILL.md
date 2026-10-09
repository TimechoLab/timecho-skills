---
name: timechodb-log-analyze
description: >
  Analyze TimechoDB logs for ERROR/WARN patterns: OOM, GC, WAL flush, Compaction
  anomalies, thread surge, connection pool exhaustion. Generate summary report.
description_zh: TimechoDB 日志分析：OOM/GC/WAL/Compaction/线程/连接池异常提取与根因定位
version: 1.0.0
agent_created: true
---

# TimechoDB 日志分析 (Log Analyzer)

扫描 ConfigNode/DataNode 日志，提取异常模式并关联系统资源。

## 触发场景

- "帮我分析一下日志，最近老是 OOM"
- 贴了一段 ERROR 日志

## 工作流

### Step 1 — 日志收集

```bash
# ConfigNode 日志
grep -E "ERROR|WARN|Exception" logs/log_confignode_all.log | tail -100

# DataNode 日志
grep -E "ERROR|WARN|Exception" logs/log_datanode_all.log | tail -100

# GC 日志（如开启）
tail -100 logs/gc.log
```

### Step 2 — 异常模式匹配

| 正则模式 | 问题类型 | 严重度 |
|----------|----------|--------|
| `OutOfMemoryError` / `GC overhead` | JVM 堆 OOM | **严重** |
| `WAL.*ERROR` / `610` | WAL 写入失败 | **严重** |
| `Disk.*space` / `No space` / `611` | 磁盘满 | **严重** |
| `Compaction.*ERROR` / `608` | 合并失败 | 高 |
| `Connection refused` | 连接拒绝 | 高 |
| `Thrift.*timeout` | RPC 超时 | 中 |
| `slow query` | 慢查询 | 中 |
| `MPP_MEMORY_NOT_ENOUGH` / `709` | 查询内存不足 | 中 |
| `Too many open files` | ulimit 不足 | 中 |
| `IndexOutOfBoundsException.*GrpcLogAppender` | Ratis 已知问题，可忽略 | 低 |

### Step 3 — 关联系统资源

```bash
free -h          # 内存
df -h            # 磁盘
uptime           # CPU 负载
ulimit -n        # 最大文件数
jstack <pid>     # 必要时抓线程堆栈
```

### Step 4 — 输出报告

```markdown
## 日志分析报告

### 严重问题 (3)
- [16:03:21] OOM: Java heap space ×2 → 建议增大 DN 堆内存
- [15:45:00] WAL_ERROR: No space left → 清理 WAL 目录

### 警告 (5)
- GC overhead: 3 次 Full GC > 5s → 建议优化查询
- slow_query: 查询耗时 8234ms → 加索引或 slimit

### 建议
1. 增大 ON_HEAP_MEMORY 到 16G
2. 扩容数据盘 100GB
3. 设置超时阈值 query_timeout_threshold=30000
```
