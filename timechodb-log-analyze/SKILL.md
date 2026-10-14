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
  Logger names, log file names and status codes must be confirmed against the
  target TimechoDB/IoTDB version's logback configuration before relying on them.
  OOM handling differs for V1.3.1+ (CrashOnOutOfMemoryError is enabled by default).
---

# TimechoDB 日志分析 (Log Analyzer)

扫描 DataNode / ConfigNode 日志，提取异常模式并关联系统资源。

## 触发场景

- "帮我分析一下日志，最近老是 OOM"
- 贴了一段 ERROR 日志或错误码

## 工作流

### Step 1 — 日志收集

**按级别分好的文件不要再按级别过滤**：`log_datanode_error.log` 已由 logback 的 `LevelFilter`
保证只含 ERROR 事件，而异常类名、消息和 `Caused by` 都在后续行里，这些行不含 `ERROR` 字样，
再 `grep ERROR` 会把它们全部滤掉。按模式用 `grep -A`，或直接 `tail`：

```bash
# DataNode：按级别分好的日志（ERROR 与 WARN 各一个文件；ConfigNode 换 log_confignode_*）
tail -n 200 logs/log_datanode_error.log
tail -n 200 logs/log_datanode_warn.log

# 按模式找时用 grep -A 把堆栈上下文一起带出来
grep -A 30 "No space left" logs/log_datanode_error.log

# 慢查询单独落一个文件：SLOW_SQL logger 配了 additivity=false，
# 不会出现在 log_datanode_all.log 里；阈值 slow_query_threshold，默认 10000ms
tail -n 100 logs/log_datanode_slow_sql.log

# 历史日志按天滚动压缩，同样按模式找、不要按级别过滤
zgrep -A 30 "No space left" logs/log-datanode-error-20261001.log.gz

# GC 日志（如已开启）
tail -n 100 logs/gc.log
```

**OOM 的证据多半不在日志里**：`conf/datanode-env.sh` 从 V1.3.1 起默认带
`-XX:+CrashOnOutOfMemoryError`，堆内、GC overhead、Metaspace 这几类 OOM 会让 HotSpot
直接 abort（退出码 134），写日志的代码不会执行。因此：

```bash
# 进程工作目录下的崩溃日志，OOM 的真实证据
ls -lt hs_err_pid*.log
grep -E "OutOfMemoryError|Java heap space|Metaspace" hs_err_pid*.log
```

同时确认进程是否重启过（看进程启动时间，或 ConfigNode 侧的节点状态变化）。
`Direct buffer memory`（堆外）与线程创建失败这两类**不会**触发 abort，仍会进日志。

### Step 2 — 异常模式匹配

| 匹配文本 | 问题类型 | 严重度 | 处理方向 |
|----------|----------|--------|----------|
| `Java heap space` / `GC overhead limit exceeded`（在 `hs_err_pid*.log`，不在日志里） | 堆内 OOM | **严重** | 调 `conf/datanode-env.sh` 的 `ON_HEAP_MEMORY`；进程已退出，先确认重启情况 |
| `Metaspace`（同上，在 `hs_err_pid*.log`） | 类元数据空间不足 | 高 | 检查类加载与元数据相关配置 |
| `direct buffer memory`（JDK 15+ 实际文案为 `Cannot reserve N bytes of direct buffer memory`，匹配时注意大小写） | 堆外内存不足 | **严重** | 调 `OFF_HEAP_MEMORY`（`-XX:MaxDirectMemorySize`）；此时加大堆内存会进一步挤占堆外 |
| `native thread`（JDK 8：`unable to create new native thread`；JDK 11+：`unable to create native thread: possibly out of memory or process/resource limits reached`） | 线程数到上限 | **严重** | 用 Step 3 的非 attach 方式排查，不要先 `jstack` |
| `Fail to sync wal` / `No space left` / `WAL_ERROR` | WAL 写入失败 | **严重** | 见 Step 4：释放/扩容 WAL 磁盘 + `FLUSH`，处理完必须确认节点状态 |
| `DISK_SPACE_INSUFFICIENT` / `No space left` / `code:611` | 磁盘满 | **严重** | 扩容或迁移数据盘；禁止手工删除数据目录 |
| `[Compaction] ... task meets error` | 合并失败 | 高 | 检查磁盘余量与 compaction 配置 |
| `QUERY_EXECUTION_MEMORY_NOT_ENOUGH`（719；1.3 为 301） | 查询内存不足 | 中 | 限制并发查询或调整查询内存 |
| `TTransportException: java.net.SocketTimeoutException: Read timed out` | RPC 超时 | 中 | 检查网络与对端负载 |
| `Connection refused` | 连接拒绝 | 高 | 检查目标实例状态与端口 |
| `Too many open files` | 文件句柄不足 | 中 | 检查进程实际 `open files` 限制（Step 3） |
| `IndexOutOfBoundsException.*GrpcLogAppender` | Ratis 已知问题，可忽略 | 低 | — |

两点匹配注意：

- 上表是**真实日志文本**，不是猜测的状态码。不少状态码根本不会写进日志（如 compaction 失败
  不带状态码，709 不会被记录），按状态码匹配会得到空结果并被误判为「没有问题」。
- 也不要用裸数字做正则：DataNode 日志的时间戳毫秒位本身就是 3 位数字
  （例如 `2026-10-09 16:03:21,610`），裸写 `610` 会命中大量无关行。

### Step 3 — 关联系统资源

```bash
free -h
df -h
uptime
cat /proc/<pid>/limits | grep -E "open files|processes"   # 进程实际生效的限制
```

`ulimit -n` 显示的是当前 shell 的限制，不一定等于 IoTDB 进程实际生效的值
（取决于启动方式，如 systemd 的 `LimitNOFILE`），要读 `/proc/<pid>/limits`。

线程问题用**不需要 attach** 的方式：

```bash
grep Threads /proc/<pid>/status                                  # 线程总数
cat /proc/<pid>/task/*/comm | sort | uniq -c | sort -rn | head   # 线程构成
```

⚠️ 只有确认线程数**没有**达到上限时，才可以用 `jstack <pid>`。IoTDB 的启动参数里没有
`-XX:+StartAttachListener`，首次 attach 时目标 JVM 需要新建 Attach Listener 线程；
线程数已满时建不出来，HotSpot 会走 `vm_exit_on_osthread_failure` → `vm_abort`，DataNode 直接退出，
排障变成宕机。（`kill -3` 也替代不了：后台启动时 stdout 已被重定向到 `/dev/null`。）

### Step 4 — 输出报告

```markdown
## 日志分析报告

### 严重问题
- OOM（hs_err_pid*.log：Java heap space）
  → 按服务端物理内存调整 conf/datanode-env.sh 的 ON_HEAP_MEMORY（给出计算依据，不要写死数值）
- [15:45:00] Fail to sync wal: No space left
  → 确认 dn_wal_dirs 指向的磁盘，释放或扩容该磁盘，然后执行 FLUSH 让系统自行回收 WAL

### 警告
- 慢查询：耗时 8234ms（阈值 slow_query_threshold，默认 10000ms）
  → 缩小查询时间范围、减少扫描的序列数/设备数

### 建议
1. ON_HEAP_MEMORY / OFF_HEAP_MEMORY 按物理内存与堆内外比例给出
2. 数据盘剩余空间低于阈值时扩容
```

**处理完必须确认节点状态。** WAL 写失败会经 `handleUnrecoverableError` 把节点置为 ReadOnly，
且不一定自动恢复：只有 DISK_FULL 会自动恢复；WAL 在独立磁盘上、或属于非空间类 I/O 错误时，
只读原因为空，同样不会自动恢复；只读原因被锁定为 `UnrecoverableError` 时，
`SET SYSTEM TO RUNNING` 之后下一次 sync 又会把节点打回只读，只能重启。
所以报告里要加一步：用 `SHOW DATANODES` / `SHOW CLUSTER DETAILS` 确认节点已回到 `Running`；
仍是 `ReadOnly` 时，按版本给出 `SET SYSTEM TO RUNNING` 或重启步骤。

报告中不要出现下列建议：

- **不要建议手工删除 IoTDB 任何数据目录下的文件**。默认的 `dn_data_dirs`、`dn_wal_dirs`、
  `dn_consensus_dir`、`dn_system_dir` 都在 `data/datanode` 下（同一个文件系统），
  删旧 TsFile、`.resource`、`.mods` 或 consensus 目录会造成丢数据或 Region 损坏。
  需要释放空间时走 TTL、`DELETE`、扩容或迁移数据盘。
  WAL 目录尤其如此：WAL 里是尚未 flush 成 TsFile 的数据，手工删除等于丢数据。
- **不要建议「加索引」**。树模型没有用户可创建的二级索引（`slimit` 也只适用于树模型），
  该建议无法执行；慢查询应缩小时间范围、减少扫描的序列数/设备数。
- **不要建议调小 `query_timeout_threshold`**。它是查询超时上限（默认 60000ms），
  调小只会让更多查询超时失败，不会让查询变快。
- 堆内存取值不要写死（如「调到 16G」），要按机器内存与 ON/OFF heap 分配比例给出。
