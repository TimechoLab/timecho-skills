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
  Requires iot-benchmark and a reachable TimechoDB/IoTDB server. Testing V2.0.0-V2.0.5
  servers additionally requires ENABLE_IOTDB_RPC_COMPRESSION=false. Confirm DB_SWITCH and
  IoTDB_DIALECT_MODE against the target server version before running.
---

# TimechoDB 性能测试 (Benchmark)

集成 iot-benchmark 完成写入与查询的吞吐/延迟基准测试。

## 触发场景

- "帮我跑一下性能测试"
- "我的环境能支撑多少写入"
- "压测一下读写混合负载"

## 前置确认

压测规模由**被测服务端**的资源决定，与运行压测客户端的机器无关（两者常常不是同一台）。
在动手之前，以下三件事必须先确认：

1. **删库风险**。iot-benchmark 的 `IS_DELETE_DATA` 默认为 `true`，开跑前会先清理目标库：

   - 树模型：执行 `drop database root.<DB_NAME>.**`；
   - 表模型（`IoTDB-200-*` + `IoTDB_DIALECT_MODE=table`）：对 `SHOW DATABASES` 的结果做
     `contains(DB_NAME)` 的**子串匹配**删除。`DB_NAME=test` 时，`latest`、`test_prod`
     这类业务库也会被一起 drop，且不可恢复。

   → 先 `SHOW DATABASES` 核对；`DB_NAME` 用不易被子串命中的专用名字；模板里显式写
   `IS_DELETE_DATA=false`。要改成 `true` 时，必须向用户确认目标库可以被删除。

2. **服务端规格**：CPU、内存、数据盘剩余空间。
3. **服务端版本**：决定 `DB_SWITCH` 的版本段、`IoTDB_DIALECT_MODE`，以及 RPC 压缩是否可用。

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
是否缩减 `DEVICE_NUMBER` / `LOOP`，否则会把盘写满并让节点进入 ReadOnly。

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
# 不要用 test 这类容易被 contains() 命中的名字
DB_NAME=bench_<专用名>
DEVICE_NUMBER=10000
SENSOR_NUMBER=20
BATCH_SIZE_PER_WRITE=100
SCHEMA_CLIENT_NUMBER=16
DATA_CLIENT_NUMBER=16
LOOP=1000
# 启动前是否清理数据：默认 true 会先删库（表模型下为子串匹配），确认可删再改回 true
IS_DELETE_DATA=false
# 最长运行时间（ms），0 表示不限制；给长时间压测兜底，避免挂死
TEST_MAX_TIME=0
# 比例顺序为 写入:Q1:Q2:...:Q12，第一位是写入；混合读写负载调整此项
OPERATION_PROPORTION=1:0:0:0:0:0:0:0:0:0:0:0:0
```

约束（来自 `config.properties` 注释与 README）：

- `DEVICE_NUMBER / CLIENT_NUMBER` 必须是 `DEVICE_NUM_PER_WRITE` 的整数倍；
- 表模型下 `DEVICE_NUMBER / IoTDB_TABLE_NUMBER` 也必须是 `DEVICE_NUM_PER_WRITE` 的整数倍；
- `DB_SWITCH` 的版本段必须与服务端匹配（如 `IoTDB-200-*` 对应 2.0，`IoTDB-130-*` 对应 1.3）；
- `OPERATION_PROPORTION` 有 13 位（写入 + Q1..Q12），某一项为 0 表示不跑该类操作；
- `ENABLE_IOTDB_RPC_COMPRESSION` 默认为 `true`，要求服务端 **2.0.6 及以上**。
  测 2.0.0–2.0.5 时必须显式设为 `false`，否则会大量报错、`failOperation` 飙高，
  容易被误当成性能结果上报。

### Step 3 — 构建与执行

源码根目录没有可直接运行的脚本，需要先构建，再到打包产物目录运行：

```bash
# 1) 构建（源码根目录）
mvn package

# 2) 进入打包产物目录（路径以实际产物为准）
cd iotdb-2.0/target/iot-benchmark-iotdb-2.0/iot-benchmark-iotdb-2.0/

# 配置必须写在当前目录的 conf/config.properties；
# 写进源码里的 configuration/conf 不会被读取，程序会静默按默认值运行。

# 3) 后台运行并重定向输出。前台运行会超出 agent 命令超时，
#    16 个 client 每 5s 各打一行进度也会淹没上下文。
nohup ./benchmark.sh > benchmark_run.log 2>&1 &
```

压测结束后只解析 `benchmark_run.log` 中的结果表，不要把原始进度日志读进上下文。

### Step 4 — 结果解析

数据只从日志里两张输出表取，不要凭记忆或模板里的数字作答：

- `Result Matrix`：`okOperation`、`okPoint`、`failOperation`、`failPoint`、`throughput(point/s)`
- `Latency (ms) Matrix`：`AVG`、`MIN`、`P50`(MEDIAN)、`P90`、`P99`、`MAX`、`SLOWEST_THREAD`

报告按实测填充（`<>` 处替换为实测值）：

```markdown
## 性能测试报告

| 指标 | 值 |
|------|-----|
| 写入吞吐 | <throughput(point/s)> |
| 成功点数 | <okPoint> |
| 失败操作 / 失败点数 | <failOperation> / <failPoint> |
| 写入延迟 AVG / P99 | <AVG> / <P99> ms |
| 查询延迟 AVG / P99 | <AVG> / <P99> ms |
```

两点注意：

- 失败数必须一并报告。失败率高时，吞吐数字没有意义；报错时应先排查配置（如 RPC 压缩版本、
  `DB_SWITCH` 版本段），而不是把它当成性能结论。
- iot-benchmark 默认测试模式**不输出** CPU 利用率和磁盘 IO。需要时在服务端用 `sar`、
  `iostat` 或监控系统单独采集；采集不到就从报告中去掉这两项，不要编造。
