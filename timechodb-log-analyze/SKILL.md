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
再 `grep ERROR` 会把它们全部滤掉。按模式找时要把整条事件（首行 + 堆栈）一起取出来，或直接 `tail`：

```bash
# DataNode：按级别分好的日志（ERROR 与 WARN 各一个文件；ConfigNode 换 log_confignode_*）
tail -n 200 logs/log_datanode_error.log
tail -n 200 logs/log_datanode_warn.log

# 按模式找：每条事件以时间戳行开头，时间戳、线程和业务消息在首行，异常消息和堆栈在后续行。
# grep -A 会丢掉首行，下面把含指定文本的整条事件打印出来；tail 防止输出过多
awk -v pat="No space left" '/^[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] /{if (e ~ pat) printf "%s", e; e=""} {e = e $0 "\n"} END{if (e ~ pat) printf "%s", e}' logs/log_datanode_error.log | tail -n 300

# 慢查询单独落一个文件：SLOW_SQL logger 配了 additivity=false，不会出现在 log_datanode_all.log 里；
# 阈值 slow_query_threshold，默认 10000ms（V1.3.0–V1.3.2 实际默认 30000ms）
tail -n 100 logs/log_datanode_slow_sql.log

# 历史日志按天滚动压缩：解压后用同样的 awk，同样不要按级别过滤
zcat < logs/log-datanode-error-20261001.log.gz | awk -v pat="No space left" '/^[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] /{if (e ~ pat) printf "%s", e; e=""} {e = e $0 "\n"} END{if (e ~ pat) printf "%s", e}' | tail -n 300

# GC 日志（如已开启）
tail -n 100 logs/gc.log
```

**OOM 的证据多半不在日志里**：`conf/datanode-env.sh` 从 V1.3.1 起默认带
`-XX:+CrashOnOutOfMemoryError`，堆内、GC overhead、Metaspace 这几类 OOM 会让 HotSpot
直接 abort（退出码 134），写日志的代码不会执行。证据在崩溃日志 `hs_err_pid<pid>.log` 里：

- 它写在 JVM 的**工作目录**下，不一定是 IoTDB 安装目录：用官方守护脚本（systemd）启动时工作目录是 `/`；
  启动参数里有 `-XX:ErrorFile` 时以它为准；工作目录不可写时会落到 `/tmp`。
- 只看文件头那一行 `OutOfMemory encountered: <类型>`。**不要对全文 grep `OutOfMemoryError` 或
  `Metaspace`**：每个 hs_err 的启动参数里都有 `-XX:+CrashOnOutOfMemoryError`，堆摘要里都有
  `Metaspace`，任何崩溃都会被误判成 OOM。

```bash
ls -lt <IOTDB_HOME>/hs_err_pid*.log /hs_err_pid*.log /tmp/hs_err_pid*.log 2>/dev/null
grep -m1 "OutOfMemory encountered" <hs_err 文件>   # 例：#  fatal error: OutOfMemory encountered: Java heap space
```

没有这一行，就不是 `CrashOnOutOfMemoryError` 触发的崩溃，按文件头的错误信息另行排查。

同时确认进程是否重启过（看进程启动时间，或 ConfigNode 侧的节点状态变化）。
`Direct buffer memory`（堆外）与线程创建失败这两类**不会**触发 abort，仍会进日志。

### Step 2 — 异常模式匹配

| 匹配文本 | 问题类型 | 严重度 | 处理方向 |
|----------|----------|--------|----------|
| `OutOfMemory encountered: Java heap space` / `OutOfMemory encountered: GC overhead limit exceeded`（hs_err 文件头，不在日志里） | 堆内 OOM | **严重** | 调 `conf/datanode-env.sh` 的 `ON_HEAP_MEMORY`；进程已退出，先确认重启情况 |
| `OutOfMemory encountered: Metaspace`（同上） | 类元数据空间不足 | 高 | 检查类加载与元数据相关配置 |
| `direct buffer memory`（JDK 15+ 实际文案为 `Cannot reserve N bytes of direct buffer memory`，匹配时注意大小写） | 堆外内存不足 | **严重** | 调 `OFF_HEAP_MEMORY`（`-XX:MaxDirectMemorySize`）；此时加大堆内存会进一步挤占堆外 |
| `native thread`（JDK 8：`unable to create new native thread`；JDK 11+：`unable to create native thread: possibly out of memory or process/resource limits reached`） | 线程数到上限 | **严重** | 用 Step 3 的非 attach 方式排查，**不要 `jstack`** |
| `Fail to sync wal` / `Fail to fsync wal` / `Fail to roll wal`（都以 `change system mode to error` 结尾） | WAL 写入失败 | **严重** | 见 Step 4：释放/扩容 WAL 磁盘 + `FLUSH`，处理完必须确认节点状态 |
| `DISK_SPACE_INSUFFICIENT` / `No space left` / `code:611` | 磁盘满 | **严重** | 扩容或迁移数据盘；禁止手工删除数据目录 |
| `task meets error`（同一行带 `[Compaction]`；V1.3.0–V1.3.2 为 `[Compaction] Meet errors`） | 合并失败 | 高 | 检查磁盘余量与 compaction 配置 |
| `Status code: 719`（`QUERY_EXECUTION_MEMORY_NOT_ENOUGH`；2.0.5 起按 INFO 记录，只在 `log_datanode_all.log` 里） | 查询内存不足 | 中 | 限制并发查询或调整查询内存 |
| `TTransportException: java.net.SocketTimeoutException: Read timed out` | RPC 超时 | 中 | 检查网络与对端负载 |
| `Connection refused` | 连接拒绝 | 高 | 检查目标实例状态与端口 |
| `Too many open files` | 文件句柄不足 | 中 | 检查进程实际 `open files` 限制（Step 3） |
| `GrpcLogAppender`（类名在首行，`IndexOutOfBoundsException` 在下一行，不能用单行正则跨行匹配） | Ratis 已知问题（见官方 FAQ） | 低 | — |

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

⚠️ 日志里出现过线程创建失败（`native thread`）时，**不要用 `jstack <pid>`**；其他情况下也要先确认线程数
离上限还有余量（`processes` 限制对 root 不生效，容器里还要看 cgroup 的 `pids.max`）。IoTDB 的启动参数里没有
`-XX:+StartAttachListener`，首次 attach 时目标 JVM 需要新建 Attach Listener 线程；
线程数已满时建不出来，HotSpot 会走 `vm_exit_on_osthread_failure` → `vm_abort`，DataNode 直接退出，
排障变成宕机。（`kill -3` 也替代不了：后台启动时 stdout 已被重定向到 `/dev/null`。）

### Step 4 — 输出报告

```markdown
## 日志分析报告

### 严重问题
- OOM（hs_err_pid*.log 文件头：OutOfMemory encountered: Java heap space）
  → 按服务端物理内存调整 conf/datanode-env.sh 的 ON_HEAP_MEMORY（给出计算依据，不要写死数值）
- [15:45:00] Fail to sync wal node-1's buffer, change system mode to error.（Caused by: No space left on device）
  → 确认 dn_wal_dirs 指向的磁盘，释放或扩容该磁盘，然后执行 FLUSH 让系统自行回收 WAL；再确认节点已回到 Running

### 警告
- 慢查询：耗时 12345ms（超过阈值 slow_query_threshold，默认 10000ms）
  → 缩小查询时间范围、减少扫描的序列数/设备数

### 建议
1. ON_HEAP_MEMORY / OFF_HEAP_MEMORY 按物理内存与堆内外比例给出
2. 数据盘剩余空间低于阈值时扩容
```

**处理完必须确认节点状态。** WAL 写失败会经 `handleUnrecoverableError` 把节点置为 ReadOnly，
且不一定自动恢复：只有因磁盘空间不足（`DiskFull`）进入的只读，会在空间恢复后自动解除；
WAL 在独立磁盘上、或属于非空间类 I/O 错误时，只读不带原因，不会自动恢复。
所以报告里要加一步：用 `SHOW DATANODES` / `SHOW CLUSTER DETAILS` 确认节点已回到 `Running`；
仍是 `ReadOnly` 时，确认磁盘与 WAL 恢复正常后连到该节点执行 `SET SYSTEM TO RUNNING ON LOCAL`
（不加 `ON LOCAL` 默认作用于整个集群），仍不能恢复再考虑重启。

报告中不要出现下列建议：

- **不要建议手工删除 IoTDB 任何数据目录下的文件**。默认的 `dn_data_dirs`、`dn_wal_dirs`、
  `dn_consensus_dir`、`dn_system_dir` 都在 `data/datanode` 下（同一个文件系统），
  删旧 TsFile、`.resource`、`.mods` 或 consensus 目录会造成丢数据或 Region 损坏。
  需要释放空间时扩容或迁移数据盘。
  WAL 目录尤其如此：WAL 里是尚未 flush 成 TsFile 的数据，手工删除等于丢数据。
- **不要建议用 `DELETE` 腾空间**。节点只读时 `DELETE` 会被直接拒绝；节点可写时，删除范围只覆盖
  TsFile 的一部分，也只是追加 WAL 和 `.mods`，反而多占空间。
- **不要建议「加索引」**。树模型没有用户可创建的二级索引（`slimit` 也只适用于树模型），
  该建议无法执行；慢查询应缩小时间范围、减少扫描的序列数/设备数。
- **不要建议调小 `query_timeout_threshold`**。它是查询超时上限（默认 60000ms），
  调小只会让更多查询超时失败，不会让查询变快。
- 堆内存取值不要写死（如「调到 16G」），要按机器内存与 ON/OFF heap 分配比例给出。
