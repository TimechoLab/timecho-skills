---
name: timechodb-benchmark
description: >
  Run and size iot-benchmark load tests against TimechoDB/IoTDB and summarize throughput
  and latency. Use when the user asks to benchmark or stress-test TimechoDB/IoTDB, asks
  how much write or mixed read/write load an environment can sustain, or wants a
  structured performance report.
metadata:
  version: "1.0.0"
  description_zh: >-
    iot-benchmark 性能测试：按服务端资源缩放压测规模，输出吞吐/延迟结构化报告
compatibility: >
  Requires iot-benchmark (building it needs JDK 17) and a reachable TimechoDB/IoTDB server.
  Testing V2.0.0-V2.0.5 servers additionally requires ENABLE_IOTDB_RPC_COMPRESSION=false.
  Confirm DB_SWITCH and IoTDB_DIALECT_MODE against the target server version before running.
---

# TimechoDB 性能测试 (Benchmark)

集成 iot-benchmark 完成写入与查询的吞吐/延迟基准测试。

## 触发场景

- "帮我跑一下性能测试"
- "我的环境能支撑多少写入"
- "压测一下读写混合负载"

## 前置确认

压测规模按**被测服务端**的资源来定（服务端与压测客户端常常不是同一台）。但客户端也要够用：
数据在客户端生成、编码和压缩，客户端的 CPU、内存或网络不足时，测到的是客户端瓶颈。

在动手之前，以下四件事必须先确认：

1. **是否允许压测**。压测会给目标集群带来真实的写入压力，并留下压测数据
   （`IS_DELETE_DATA=false` 时会一直保留）。必须先征得用户同意，不要在未经确认的生产集群上跑。
2. **删库风险**。iot-benchmark 的 `IS_DELETE_DATA` 默认为 `true`，开跑前会先清理，
   清理范围取决于 `DB_SWITCH`：

   - 树模型（`IoTDB_DIALECT_MODE=tree`）的 `*-SESSION_BY_*`：执行 `drop database root.<DB_NAME>.**`；
   - `*-JDBC`：执行 `delete storage group root.<DB_NAME>.*`；
   - `*-REST`：执行 `delete database root.**`，**删除全部树模型库，与 `DB_NAME` 无关**；
   - 表模型（`IoTDB-200-*` + `IoTDB_DIALECT_MODE=table`）：对 `SHOW DATABASES` 的结果做
     `contains(DB_NAME)` 的**子串匹配**删除。`DB_NAME=test` 时，`latest`、`test_prod`
     这类业务库也会被一起 drop，且不可恢复。

   → 模板里显式写 `IS_DELETE_DATA=false`；`DB_NAME` 用不易被子串命中的专用名字。核对表模型库时
   要在 table 方言下执行 `SHOW DATABASES`，默认的 tree 方言看不到表模型库。要改成 `true` 时，
   必须把上面对应的实际删除范围告诉用户并得到确认；`*-REST` 下不要改成 `true`。

3. **服务端规格**：CPU、内存、数据盘剩余空间。
4. **服务端版本**：决定 `DB_SWITCH` 的版本段、`IoTDB_DIALECT_MODE`，以及 RPC 压缩是否可用。

服务端资源在服务端采集（拿不到时向用户索取，不要用客户端的 `nproc` / `free -h` 代替）：

```bash
nproc              # CPU 核数
free -h            # 内存
df -h <data_dir>   # 数据盘剩余空间
```

## 工作流

### Step 1 — 确定压测规模

先按服务端 CPU 与内存给出起始规模（下表为起始建议值，需按实测调整）：

| 服务端规格 | DEVICE_NUMBER | SENSOR_NUMBER | DATA_CLIENT_NUMBER | SCHEMA_CLIENT_NUMBER |
|-----------|--------------|--------------|-------------------|---------------------|
| 4C 8G | 1,000 | 10 | 4 | 4 |
| 8C 16G | 5,000 | 10 | 8 | 8 |
| 16C 32G | 10,000 | 20 | 16 | 16 |
| 32C 64G | 50,000 | 20 | 24 | 24 |

再用磁盘容量校验写入总量：

```
写入总点数 ≈ DEVICE_NUMBER × SENSOR_NUMBER × BATCH_SIZE_PER_WRITE × LOOP × 写入比例
```

每个 LOOP 会把**全部 `DEVICE_NUMBER` 台设备**各写一个 batch，所以公式里乘的是
`DEVICE_NUMBER`，不是 `DEVICE_NUM_PER_WRITE`。漏掉设备数会低估多个数量级：
按示例配置（10000 设备、20 测点、BATCH 100、LOOP 1000、纯写）实际约有
`10000 × 20 × 100 × 1000 = 2×10^10` 点。

估算值只用于判断量级（实际落盘大小取决于压缩率），必须与服务端数据盘剩余空间对比后再决定
是否缩减 `DEVICE_NUMBER` / `LOOP`。注意不是写满才出问题：磁盘剩余比例低于
`disk_space_warning_threshold`（默认 `0.05`）时节点就会进入 ReadOnly，估算时要留出这部分余量，
WAL 所在的盘也要一起看。

### Step 2 — 生成配置

iot-benchmark 只读取**运行目录**下的 `conf/config.properties`，且键名在源码中写死。
**键名写错不会报错，会静默按默认规模运行**（`DEVICE_NUMBER=6000`、`SENSOR_NUMBER=200`、
`IS_DELETE_DATA=true`），因此不要自造键名（如 `DEVICE_NUM` / `SENSOR_NUM` / `BATCH_SIZE`）。

```properties
# conf/config.properties（运行目录下）
DB_SWITCH=IoTDB-200-SESSION_BY_TABLET
IoTDB_DIALECT_MODE=tree
HOST=127.0.0.1
PORT=6667
USERNAME=root
PASSWORD=<password>
# 不要用 test 这类容易被 contains() 命中的名字；每轮压测换一个新名字（见下）
DB_NAME=bench_<专用名>
DEVICE_NUMBER=10000
SENSOR_NUMBER=20
BATCH_SIZE_PER_WRITE=100
SCHEMA_CLIENT_NUMBER=16
DATA_CLIENT_NUMBER=16
LOOP=1000
# 启动前是否清理数据：默认 true 会先删库，范围见「前置确认」，确认可删才能改成 true
IS_DELETE_DATA=false
# 最长运行时间（ms），0 表示不限制；按预期时长设置，给长时间压测兜底
TEST_MAX_TIME=7200000
# 比例顺序为 写入:Q1:Q2:...:Q12，第一位是写入；混合读写负载调整此项
OPERATION_PROPORTION=1:0:0:0:0:0:0:0:0:0:0:0:0
```

`IS_DELETE_DATA=false` 时，用同一个 `DB_NAME` 重跑会把数据写到相同的时间戳上
（写入时间戳由 `START_TIME` 确定性生成），变成乱序覆盖写入，几轮结果之间没法比。
每轮压测换一个新的 `DB_NAME`。

约束（来自 `config.properties` 注释与 README）：

- `DEVICE_NUMBER / CLIENT_NUMBER` 必须是 `DEVICE_NUM_PER_WRITE` 的整数倍；
- 表模型下 `DEVICE_NUMBER / IoTDB_TABLE_NUMBER` 也必须是 `DEVICE_NUM_PER_WRITE` 的整数倍；
- `DB_SWITCH` 的版本段必须与服务端匹配（如 `IoTDB-200-*` 对应 2.0，`IoTDB-130-*` 对应 1.3）；
- `OPERATION_PROPORTION` 有 13 位（写入 + Q1..Q12），某一项为 0 表示不跑该类操作；
- `ENABLE_IOTDB_RPC_COMPRESSION` 默认为 `true`，要求服务端 **2.0.6 及以上**。
  测 2.0.0–2.0.5 时必须显式设为 `false`，否则会大量报错、`failOperation` 飙高，
  容易被误当成性能结果上报。

### Step 3 — 构建与执行

源码根目录没有可直接运行的脚本，需要先构建，再到打包产物目录运行。模块按 `DB_SWITCH` 选：
`IoTDB-200-*` 用 `iotdb-2.0`，`IoTDB-130-*` 用 `iotdb-1.3`。`IoTDB-130-*` 的适配类只在
`iotdb-1.3` 的包里，用 `iotdb-2.0` 的包运行会报类找不到。

```bash
# 1) 构建（源码根目录，需要 JDK 17）：只构建目标模块，跳过测试
mvn clean package -pl iotdb-2.0 -am -Dmaven.test.skip=true

# 2) 进入打包产物目录（以 iotdb-2.0 为例，路径以实际产物为准）
cd iotdb-2.0/target/iot-benchmark-iotdb-2.0/iot-benchmark-iotdb-2.0/

# 配置必须写在当前目录的 conf/config.properties；
# 写进源码里的 configuration/conf 不会被读取，程序会静默按默认值运行。

# 3) 后台运行并重定向输出，记下 PID。前台运行会超出 agent 命令超时，
#    16 个 client 每 5s 各打一行进度也会淹没上下文。
nohup ./benchmark.sh > benchmark_run.log 2>&1 &
echo $! > benchmark.pid
```

判断结束：进程已退出，且日志里出现 `All dataClients finished. The final test result is:`。
不要把原始进度日志读进上下文，只解析这一行之后的结果表。

### Step 4 — 结果解析

数据只从**最终**输出的两张表取，不要凭记忆或模板里的数字作答。运行时间超过
`RESULT_PRINT_INTERVAL`（默认 3600s）时，中途还会打印同名的中间结果（前缀为
`The test is in progress. The current test result is:`），不要取这些：

- `Result Matrix`：`okOperation`、`okPoint`、`failOperation`、`failPoint`、`throughput(point/s)`
- `Latency (ms) Matrix`：完整列为 `AVG`、`MIN`、`P10`、`P25`、`MEDIAN`、`P75`、`P90`、`P95`、
  `P99`、`P999`、`MAX`、`SLOWEST_THREAD`

两张表都是每种操作一行：写入是 `INGESTION`，每种查询各占一行，没有执行的操作整行为 0。

报告按实测填充（`<>` 处替换为实测值）：

```markdown
## 性能测试报告

| 指标 | 值 |
|------|-----|
| 写入吞吐 | <INGESTION 行的 throughput(point/s)> |
| 成功点数 | <okPoint> |
| 失败操作 / 失败点数 | <failOperation> / <failPoint> |
| 写入延迟 AVG / P99 | <INGESTION 行的 AVG> / <P99> ms |
| 查询延迟 AVG / P99 | <按实际执行的查询类型逐行列出；纯写入时删掉这一行> |
```

两点注意：

- 失败数必须一并报告。失败率高时，吞吐数字没有意义；报错时应先排查配置（如 RPC 压缩版本、
  `DB_SWITCH` 版本段），而不是把它当成性能结论。
- iot-benchmark 默认测试模式**不输出** CPU 利用率和磁盘 IO。需要时在服务端用 `sar`、
  `iostat` 或监控系统单独采集；采集不到就不要写进报告，不要编造。
