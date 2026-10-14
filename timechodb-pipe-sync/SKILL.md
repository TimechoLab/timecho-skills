---
name: timechodb-pipe-sync
description: >
  Configure TimechoDB/IoTDB Pipe for station-to-center sync, cascading, dual-active
  mirroring, SSL, compressed transfer, air-gap transfer and lag monitoring. Use when
  the user asks to sync data between instances, aggregate field-site data to a center,
  build a dual-active pair, move data across a network gap, or diagnose Pipe backlog
  and stalls.
metadata:
  version: "1.0.0"
  description_zh: >-
    Pipe 数据同步：场站→中心汇聚、全量/增量/级联、双活镜像、SSL/压缩、网闸、延迟监控
compatibility: >
  Examples require V1.3.1+ (V1.3.0 does not accept the unprefixed 'node-urls'). Compression,
  rate limiting and iotdb-system.properties require V1.3.3+. V1.x and V2.x cannot sync to
  each other through Pipe. Confirm plugin names and parameters against the target version.
---

# TimechoDB Pipe 数据同步 (Pipe Sync)

## 触发场景

- "场站数据怎么同步到中心"
- "Pipe 同步延迟很高 / 经常停"
- "两端互相同步怎么做"

## 先确认 SQL 方言

2.x 的 pipe 按 SQL 方言隔离，`capture.tree` / `capture.table` 默认取**创建该 pipe 的会话的
`sql_dialect`**。在默认的 tree 方言下执行本文示例，只会捕获树模型数据：场站若用表模型写入，
pipe 显示 `RUNNING`、`RemainingEventCount=0`，但表模型数据一条也不会同步。

- 先确认数据属于哪个模型，再在对应方言下创建 pipe（`SET SQL_DIALECT=TABLE`，或 CLI 加
  `-sql_dialect table`）；
- 树表数据都有时，分别建两条 pipe；
- 双活场景按官方文档使用 `mode.double-living`；
- `SHOW PIPES` 只列出**当前方言**下创建的 pipe，在 tree 会话里看不到 table 方言建的 pipe。

## 全量 + 增量同步

「先全量后增量」是默认行为（`history.enable` 与 `realtime.enable` 默认均为 `true`），
**不需要写 SOURCE 子句**。目标地址用 `node-urls`：

```sql
CREATE PIPE station_to_center
WITH SINK (
  'sink'='iotdb-thrift-sink',
  'node-urls'='<center_ip>:6667'
);
```

子句顺序固定为 `WITH SOURCE` → `WITH PROCESSOR` → `WITH SINK`，顺序写错会直接报语法错误。
在 V1.3.1+ 上，CREATE 之后 pipe 会自动启动，`START PIPE` 可省略。

源端插件名是 `iotdb-source`（没有 `iotdb-thrift-source`）。
`source.mode` 只有 `live`（默认）/ `query` / `snapshot` / `subscribe`，与「先全量后增量」无关。

**V2.0.8 / V1.3.6 起，全量 pipe 会被自动拆分**：`pipeAutoSplitFullEnabled` 默认为 `true`，
history 与 realtime 都开启时（即上面的默认写法），`station_to_center` 会被拆成
`station_to_center_history` 和 `station_to_center_realtime` 两条，**原名 pipe 不存在**。
之后按原名执行 `DROP PIPE` / `STOP PIPE` / `START PIPE` 都会返回 `PIPE_NOT_EXIST_ERROR`。
操作前先用 `SHOW PIPES` 确认实际名字，再对两条分别操作。

## 级联同步

```
Station → Edge → Center
```

Edge 上的 pipe 需要 `'forwarding-pipe-requests'='true'`，否则 Station 的数据到不了 Center。
该值是默认值，但级联场景建议显式写出（同样受方言隔离影响，Edge 上要按数据所在模型创建）：

```sql
CREATE PIPE edge_to_center
WITH SOURCE ('forwarding-pipe-requests'='true')
WITH SINK ('sink'='iotdb-thrift-sink', 'node-urls'='<center_ip>:6667');
```

## 双活镜像

双活最容易配错的两处：**转发**与**方言**。两端都按默认值转发时，数据会在 A 与 B 之间无限循环；
两端方言不一致时，只会镜像其中一个模型，两端静默分叉。

```sql
-- A 端
CREATE PIPE ab
WITH SOURCE ('inclusion'='all', 'forwarding-pipe-requests'='false')
WITH SINK ('sink'='iotdb-thrift-sink', 'node-urls'='<B_ip>:6667');

-- B 端对称创建 ba（SINK 指向 A），同样带 forwarding-pipe-requests=false
```

两条额外要求：

- 开启元数据同步时，接收端需要设置 `enable_auto_create_schema=false`；
- 两端不要同时做元数据操作或删除操作。

## 加密传输 (SSL)

```sql
CREATE PIPE secure_pipe
WITH SINK (
  'sink'='iotdb-thrift-ssl-sink',
  'node-urls'='<ip>:6667',
  'ssl.trust-store-path'='<trust_store_path>',
  'ssl.trust-store-pwd'='<trust_store_pwd>'
);
```

- 使用 `iotdb-thrift-ssl-sink` 时，`ssl.trust-store-path` 与 `ssl.trust-store-pwd` 是**必填项**，
  缺失会在创建时报错；插件名本身已开启 SSL，不需要额外的 `sink.ssl.enable`。
- 接收端要开启 Thrift SSL：在 `iotdb-system.properties`（V1.3.3+）中设置 `enable_thrift_ssl=true`
  以及 `key_store_path` / `key_store_pwd`，重启后生效。
- ⚠️ `enable_thrift_ssl=true` 会让**整个 `rpc_port`（默认 6667）只接受 SSL**：普通服务与 SSL
  服务在同一个端口上只会启动其中一个，这个开关不是给 pipe 单独开一条 SSL 通道。在「场站→中心」
  场景里直接开启，其他仍用普通 `iotdb-thrift-sink` 的场站、以及中心上所有不带 SSL 的
  CLI / Session / JDBC 业务连接都会连不上，同步和业务写入同时中断。**开启前必须确认所有客户端与
  上游 pipe 都已切到 SSL，并把它作为需要用户明确确认的变更。**
- SSL sink 需要 V1.3.1 及以上版本。

## 压缩与限速（V1.3.3+）

在 sink 中追加：

```sql
'compressor'='snappy,lz4',
'rate-limit-bytes-per-second'='<bytes_per_second>'
```

可选压缩算法：snappy、gzip、lz4、zstd、lzma2。

## 网闸穿透

跨网闸用 `iotdb-air-gap-sink`（不是 `opc-ua-sink`，后者是通过 OPC UA 协议对外提供数据）：

```sql
CREATE PIPE a2b
WITH SINK (
  'sink'='iotdb-air-gap-sink',
  'node-urls'='<网闸映射的接收端IP>:9780'
);
```

接收端需要在 `iotdb-system.properties`（V1.3.3+）中设置 `pipe_air_gap_receiver_enabled=true`，
端口由 `pipe_air_gap_receiver_port` 指定（默认 9780），重启后生效。

**接收端的目标用户必须在创建 pipe 之前就已存在**，事后再补建用户，之前的数据也无法同步。
支持的网闸型号以官方文档列表为准。

## 监控

```sql
SHOW PIPES;
```

结果里包含 `RemainingEventCount`、`EstimatedRemainingSeconds`（统计有延迟）和 `ExceptionMessage`。
`SHOW PIPES` 只列出当前方言下的 pipe；`information_schema.pipes` 只在表模型方言
（`sql_dialect=table`）下存在，在树模型连接里执行会失败。

## 排查

| 症状 | 排查 |
|------|------|
| 积压持续增长 | 看 `SHOW PIPES` 的 `RemainingEventCount`；检查网络带宽与接收端写入能力 |
| Pipe 频繁停止 | 看 `SHOW PIPES` 的 `ExceptionMessage`；检查发送端 WAL 与接收端端口可达性 |
| pipe 报 `PIPE_NOT_EXIST_ERROR` | 全量 pipe 可能已被拆分为 `<PipeId>_history` / `<PipeId>_realtime`（V2.0.8 / V1.3.6 起），先 `SHOW PIPES` 确认真实名字 |
| 显示 RUNNING 但数据没同步 | 确认数据模型与创建 pipe 时的 `sql_dialect` 是否一致 |
| 同步数据不一致 | STOP/START 只暂停与恢复，**进度会保留，不会重做全量**；需要重做全量时先 `DROP PIPE` 再重新 `CREATE`，注意重传后的覆盖语义，且同步期间不要执行删除操作 |
| SSL 握手失败 | 检查 trust-store 路径与密码，以及接收端是否开启 `enable_thrift_ssl` |
