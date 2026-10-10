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
  Requires iot-benchmark and a reachable TimechoDB/IoTDB server. Confirm DB_SWITCH and
  IoTDB_DIALECT_MODE against the target server version before running.
---

# TimechoDB 性能测试 (Benchmark)

集成 iot-benchmark 完成写入与查询的吞吐/延迟基准测试。

## 触发场景

- "帮我跑一下性能测试"
- "我的环境能支撑多少写入"
- "压测一下读写混合负载"

## 前置确认

压测规模由**被测服务端**的资源决定，与运行压测客户端的机器无关（两者常常不是同一台）。先确认：

- 服务端规格：CPU、内存、数据盘剩余空间；
- 服务端版本：决定 `DB_SWITCH` 的版本段与 `IoTDB_DIALECT_MODE`；
- 是否允许在该环境产生压测数据（会真实写入并占用磁盘）。

拿不到服务端规格时向用户索取，**不要用客户端的 `nproc` / `free -h` 代替服务端规格**。

资源在服务端采集：

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

再用磁盘容量校验写入量。按 iot-benchmark `conf/config.properties` 注释：

```
每次写入操作的点数 = DEVICE_NUM_PER_WRITE × SENSOR_NUMBER × BATCH_SIZE_PER_WRITE
写入总点数 ≈ 每次写入点数 × LOOP × 写入比例
```

该估算用于判断量级（实际落盘大小取决于压缩率），必须与服务端数据盘剩余空间对比后
再决定是否缩减 `DEVICE_NUMBER` / `LOOP`，避免把盘写满。

### Step 2 — 生成配置

iot-benchmark 只读取 `conf/config.properties`，且键名在源码中写死。**键名写错不会报错，会静默按默认规模运行**，因此不要自造键名（如 `DEVICE_NUM` / `SENSOR_NUM` / `BATCH_SIZE`）。

```properties
# conf/config.properties
DB_SWITCH=IoTDB-200-SESSION_BY_TABLET
IoTDB_DIALECT_MODE=tree
HOST=127.0.0.1
PORT=6667
USERNAME=root
PASSWORD=<password>
DB_NAME=test
DEVICE_NUMBER=10000
SENSOR_NUMBER=20
BATCH_SIZE_PER_WRITE=100
SCHEMA_CLIENT_NUMBER=16
DATA_CLIENT_NUMBER=16
LOOP=1000
# 比例顺序为 写入:Q1:Q2:...:Q12，第一位是写入；混合读写负载调整此项
OPERATION_PROPORTION=1:0:0:0:0:0:0:0:0:0:0:0:0
```

约束（同样来自 `config.properties` 注释）：

- `DEVICE_NUMBER / CLIENT_NUMBER` 必须是 `DEVICE_NUM_PER_WRITE` 的整数倍；
- 表模型下 `DEVICE_NUMBER / IoTDB_TABLE_NUMBER` 也必须是 `DEVICE_NUM_PER_WRITE` 的整数倍；
- `DB_SWITCH` 的版本段必须与服务端匹配（如 `IoTDB-200-*` 对应 2.0，`IoTDB-130-*` 对应 1.3）；
- `OPERATION_PROPORTION` 有 13 位（写入 + Q1..Q12），某一项为 0 表示不跑该类操作。

### Step 3 — 执行

```bash
cd iot-benchmark
./benchmark.sh
```

### Step 4 — 结果解析

数据只从 iot-benchmark 控制台输出的两张表中取，不要凭记忆或模板里的数字作答：

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

- 失败数必须一并报告。失败率高时，吞吐数字没有意义。
- iot-benchmark 默认测试模式**不输出** CPU 利用率和磁盘 IO。需要时在服务端用 `sar`、
  `iostat` 或监控系统单独采集；采集不到就从报告中去掉这两项，不要编造。
