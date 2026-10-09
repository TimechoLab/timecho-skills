---
name: timechodb-benchmark
description: >
  Integrate iot-benchmark: auto-scale test size by machine resources (write points/s,
  latency percentiles, mixed query load), parse results into structured metrics.
description_zh: iot-benchmark 性能测试：按资源缩放压测规模，吞吐/延迟/资源结构化报告
version: 1.0.0
agent_created: true
---

# TimechoDB 性能测试 (Benchmark)

集成 iot-benchmark 工具进行吞吐与延迟基准测试。

## 触发场景

- "帮我跑一下性能测试"
- "我的环境能支撑多少写入"

## 工作流

### Step 1 — 资源探测

```bash
nproc          # CPU 核数
free -h        # 内存
df -h          # 磁盘
```

### Step 2 — 生成测试配置

根据资源动态计算压测规模：

| CPU | 推荐设备数 | 推荐测点数 | 线程数 |
|-----|-----------|-----------|--------|
| 4C | 1000 | 10 | 4 |
| 8C | 5000 | 10 | 8 |
| 16C | 10000 | 20 | 16 |
| 32C | 50000 | 20 | 32 |

```properties
# benchmark.properties
HOST=127.0.0.1
PORT=6667
DB_NAME=test
DEVICE_NUM=10000
SENSOR_NUM=20
BATCH_SIZE=100
LOOP=1000
```

### Step 3 — 执行

```bash
cd iot-benchmark
./benchmark.sh
```

### Step 4 — 结果解析

```markdown
## 性能测试报告

| 指标 | 值 |
|------|-----|
| 写入吞吐 | 250,000 points/s |
| 写入延迟 P50 | 2.1ms |
| 写入延迟 P99 | 15.3ms |
| 查询延迟 P50 | 8.5ms |
| CPU 利用率 | 62% |
| 磁盘 IO | 120 MB/s |
