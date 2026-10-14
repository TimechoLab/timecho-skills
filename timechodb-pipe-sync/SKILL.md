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
  rate limiting, the SHOW PIPES backlog columns and iotdb-system.properties require V1.3.3+.
  Dual-active sync and the air-gap sink are TimechoDB enterprise features; double-living
  requires V2.0.2+. V1.x and V2.x cannot sync to each other through Pipe.
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
- 双活场景使用 `source.mode.double-living`（V2.0.2+，它会忽略 `sql_dialect`，树表数据都捕获），见「双活镜像」；
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

需要指定接收端用户时，在 sink 里加上 `'sink.username'` / `'sink.password'`（以目标版本的参数表为准）。

子句顺序固定为 `WITH SOURCE` → `WITH PROCESSOR` → `WITH SINK`，顺序写错会直接报语法错误。
在 V1.3.1+ 上，CREATE 之后 pipe 会自动启动，`START PIPE` 可省略。

源端插件名是 `iotdb-source`（没有 `iotdb-thrift-source`）。
`source.mode` 取值为 `live`（默认）/ `query` / `snapshot` / `subscribe`。其中 `query` 与 `snapshot`
只传一次历史数据，传完 pipe 会自动终止并被删除，也不会被自动拆分；要「先全量后增量」就保持默认。

**V2.0.8 / V1.3.6 起，全量 pipe 会被自动拆分**：配置项 `pipe_auto_split_full_enabled` 默认为 `true`，
history 与 realtime 都开启时（即上面的默认写法），`station_to_center` 会被拆成
`station_to_center_history` 和 `station_to_center_realtime` 两条，**原名 pipe 不存在**。
之后按原名执行 `DROP PIPE` / `STOP PIPE` / `START PIPE` 都会报 pipe 不存在（错误码因版本而异）。
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

双活是 **TimechoDB 企业版**功能（官方文档：「目前双活能力为企业版功能」）。Apache IoTDB 的发布版
做不了双活：2.0.2–2.0.10 里 realtime 转发是写死开启的，加了 double-living 也挡不住回环；
1.3.5 起又会直接拒绝 `'forwarding-pipe-requests'='false'`。

双活最容易配错的两处：**转发**与**方言**。两端都按默认值转发时，数据会在 A 与 B 之间无限循环；
两端方言不一致时，只会镜像其中一个模型，两端静默分叉。

**V2.0.2 及以上**：两端都开启 `source.mode.double-living`（参数表中记作 `mode.double-living`）。
开启后会**忽略连接所用的 `sql_dialect`，树表模型数据都会被捕获**，且不转发由另一条 pipe 同步而来的数据，
正好同时解决上面两个问题：

```sql
-- A 端
CREATE PIPE ab
WITH SOURCE ('source.mode.double-living'='true')
WITH SINK ('sink'='iotdb-thrift-sink', 'node-urls'='<B_ip>:6667');

-- B 端对称创建 ba（SINK 指向 A），同样带 source.mode.double-living=true
```

`source.mode.double-living=true` 与 `forwarding-pipe-requests=true` 不能同时设置，校验会直接报错。

**V1.3.x**：没有 `double-living`，而且 1.3 不会对不认识的参数报错，照上面的写法建出来的 pipe
仍然转发，两端会无限回环。按 V1.3.x 文档，两端都关闭转发：

```sql
-- A 端（B 端对称创建，SINK 指向 A）
CREATE PIPE ab
WITH SOURCE ('inclusion'='all', 'forwarding-pipe-requests'='false')
WITH SINK ('sink'='iotdb-thrift-sink', 'node-urls'='<B_ip>:6667');
```

这种写法在 2.x 上不等价于 double-living：捕获范围仍由创建 pipe 的会话方言决定，树表混用时只会镜像一个模型。

两条额外要求：

- 开启元数据同步时，接收端需要设置 `enable_auto_create_schema=false`；
- 双活两端不要同时做元数据操作；同步期间避免执行任何删除操作，防止两端状态不一致。

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
- 接收端要开启 Thrift SSL：在 `iotdb-system.properties`（V1.3.3+；之前在 `iotdb-datanode.properties`）
  中设置 `enable_thrift_ssl=true` 以及 `key_store_path` / `key_store_pwd`，重启后生效。
- ⚠️ `enable_thrift_ssl=true` 会让**整个 `dn_rpc_port`（默认 6667）只接受 SSL**：普通服务与 SSL
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

跨网闸用 `iotdb-air-gap-sink`（不是 `opc-ua-sink`，后者是通过 OPC UA 协议对外提供数据）。
它是 TimechoDB 企业版插件，Apache IoTDB V1.3.3 及之后的发布版不内置：

```sql
CREATE PIPE a2b
WITH SINK (
  'sink'='iotdb-air-gap-sink',
  'node-urls'='<网闸映射的接收端IP>:9780'
);
```

接收端需要在 `iotdb-system.properties`（V1.3.3+；之前在 `iotdb-common.properties`）中设置
`pipe_air_gap_receiver_enabled=true`，端口由 `pipe_air_gap_receiver_port` 指定（默认 9780），重启后生效。

**接收端的目标用户必须在创建 pipe 之前就已存在**，事后再补建用户，之前的数据也无法同步。
支持的网闸型号以官方文档列表为准。

## 监控

```sql
SHOW PIPES;
```

结果里包含 `RemainingEventCount`、`EstimatedRemainingSeconds`（V1.3.3+，统计有延迟）和 `ExceptionMessage`。
`SHOW PIPES` 只列出当前方言下的 pipe；`information_schema.pipes` 只在表模型方言
（`sql_dialect=table`）下存在，在树模型连接里执行会失败。

## 排查

| 症状 | 排查 |
|------|------|
| 积压持续增长 | 看 `SHOW PIPES` 的 `RemainingEventCount`；检查网络带宽与接收端写入能力 |
| Pipe 频繁停止 | 看 `SHOW PIPES` 的 `ExceptionMessage`；检查发送端 WAL 与接收端端口可达性 |
| 按原名操作报 pipe 不存在 | 全量 pipe 可能已被拆分为 `<PipeId>_history` / `<PipeId>_realtime`（V2.0.8 / V1.3.6 起），或当前会话方言与创建时不同；先 `SHOW PIPES` 确认真实名字 |
| 显示 RUNNING 但数据没同步 | 确认数据模型与创建 pipe 时的 `sql_dialect` 是否一致 |
| 同步数据不一致 | STOP/START 只暂停与恢复，**进度会保留，不会重做全量**；需要重做全量时先 `DROP PIPE` 再重新 `CREATE`，注意重传后的覆盖语义，且同步期间不要执行删除操作 |
| SSL 握手失败 | 检查 trust-store 路径与密码，以及接收端是否开启 `enable_thrift_ssl` |
