---
name: timechodb-log-analyze
description: >
  Analyze TimechoDB/IoTDB DataNode and ConfigNode logs for ERROR and WARN patterns:
  JVM OOM variants, WAL and disk failures, compaction errors, slow queries, and
  thread/file-descriptor limits. Use when the user reports a TimechoDB/IoTDB fault,
  pastes error or exception logs, or asks what an error code or log spike means.
metadata:
  version: "1.0.0"
  description_zh: >-
    TimechoDB 日志分析：OOM/WAL/磁盘/Compaction/慢查询/线程与句柄异常提取与根因定位
compatibility: >
  Logger names, log file names and TSStatusCode values must be confirmed against the
  target TimechoDB/IoTDB version's logback configuration before relying on them.
---

# TimechoDB 日志分析 (Log Analyzer)

扫描 DataNode / ConfigNode 日志，提取异常模式并关联系统资源。

## 触发场景

- "帮我分析一下日志，最近老是 OOM"
- 贴了一段 ERROR 日志或错误码

## 工作流

### Step 1 — 日志收集

按级别分好的日志优先，不要直接在大而全的日志里捞：

```bash
# 按级别分好的日志（DataNode；ConfigNode 同理换 log_confignode_*）
grep -E "ERROR" logs/log_datanode_error.log | tail -100
grep -E "WARN"  logs/log_datanode_warn.log  | tail -100

# 慢查询单独落一个文件：SLOW_SQL logger 配了 additivity=false，
# 这些内容不会出现在 log_datanode_all.log 里
tail -100 logs/log_datanode_slow_sql.log     # 阈值 slow_query_threshold，默认 10000ms

# 历史日志按天滚动压缩，需要 zgrep
zgrep -E "ERROR" logs/log-datanode-error-20261001.log.gz

# 异常要带堆栈上下文，否则只能看到第一行
grep -A 30 "OutOfMemoryError" logs/log_datanode_error.log

# GC 日志（如已开启）
tail -100 logs/gc.log
```

### Step 2 — 异常模式匹配

| 正则模式 | 问题类型 | 严重度 | 处理方向 |
|----------|----------|--------|----------|
| `Java heap space` / `GC overhead limit exceeded` | 堆内 OOM | **严重** | 调 `conf/datanode-env.sh` 的 `ON_HEAP_MEMORY` |
| `Direct buffer memory` | 堆外内存不足 | **严重** | 调 `OFF_HEAP_MEMORY`（`-XX:MaxDirectMemorySize`）；此时加大堆内存会进一步挤占堆外 |
| `Metaspace` | 类元数据空间不足 | 高 | 检查类加载与元数据相关配置 |
| `unable to create new native thread` | 线程数到上限 | **严重** | 检查进程实际 `processes` 限制（Step 3）与线程池配置 |
| `WAL_ERROR` / `code:610` | WAL 写入失败 | **严重** | 见 Step 4：释放/扩容 WAL 磁盘 + `FLUSH`，禁止手工删除 WAL |
| `DISK_SPACE_INSUFFICIENT` / `No space left` / `code:611` | 磁盘满 | **严重** | 扩容或清理数据盘 |
| `COMPACTION_ERROR` / `code:608` | 合并失败 | 高 | 检查磁盘余量与 compaction 配置 |
| `MPP_MEMORY_NOT_ENOUGH` / `code:709` | 查询内存不足 | 中 | 限制并发查询或调整查询内存 |
| `Connection refused` | 连接拒绝 | 高 | 检查目标实例状态与端口 |
| `Thrift.*timeout` | RPC 超时 | 中 | 检查网络与对端负载 |
| `Too many open files` | 文件句柄不足 | 中 | 检查进程实际 `open files` 限制（Step 3） |
| `IndexOutOfBoundsException.*GrpcLogAppender` | Ratis 已知问题，可忽略 | 低 | — |

匹配注意：**不要用裸状态码做正则**。DataNode 日志的 pattern 是 `%d [%t] %-5p ...`，
时间戳毫秒位本身就是 3 位数字（例如 `2026-10-09 16:03:21,610`），裸写 `610` 会命中大量无关行；
线程号、ID 同理。优先匹配枚举名（`WAL_ERROR` 等），或带上下文匹配（`code:610`）。

对应关系：608 `COMPACTION_ERROR`、610 `WAL_ERROR`、611 `DISK_SPACE_INSUFFICIENT`、
709 `MPP_MEMORY_NOT_ENOUGH`。

### Step 3 — 关联系统资源

```bash
free -h
df -h
uptime
cat /proc/<pid>/limits | grep -E "open files|processes"   # 进程实际生效的限制
jstack <pid>                                              # 必要时抓线程堆栈
```

`ulimit -n` 显示的是当前 shell 的限制，不一定等于 IoTDB 进程实际生效的值
（取决于启动方式，如 systemd 的 `LimitNOFILE`），要读 `/proc/<pid>/limits`。

### Step 4 — 输出报告

```markdown
## 日志分析报告

### 严重问题
- [16:03:21] OutOfMemoryError: Java heap space ×2
  → 按服务端物理内存调整 conf/datanode-env.sh 的 ON_HEAP_MEMORY（给出计算依据，不要写死数值）
- [15:45:00] WAL_ERROR: No space left
  → 确认 dn_wal_dirs 指向的磁盘，释放或扩容该磁盘，然后执行 FLUSH 让系统自行回收 WAL

### 警告
- 慢查询：耗时 8234ms（阈值 slow_query_threshold，默认 10000ms）
  → 缩小查询时间范围、减少扫描的序列数/设备数

### 建议
1. ON_HEAP_MEMORY / OFF_HEAP_MEMORY 按物理内存与堆内外比例给出
2. 数据盘剩余空间低于阈值时扩容
```

报告中不要出现下列建议：

- **不要建议清理 WAL 目录**。WAL 里是尚未 flush 成 TsFile 的数据，手工删除等于丢数据。
  正确处理是释放/扩容 WAL 所在磁盘，再 `FLUSH` 等系统回收。
- **不要建议「加索引」**。树模型没有用户可创建的二级索引（`slimit` 也只适用于树模型），
  该建议无法执行；慢查询应缩小时间范围、减少扫描的序列数/设备数。
- **不要建议调小 `query_timeout_threshold`**。它是查询超时上限（默认 60000ms），
  调小只会让更多查询超时失败，不会让查询变快。
- 堆内存取值不要写死（如「调到 16G」），要按机器内存与 ON/OFF heap 分配比例给出。
