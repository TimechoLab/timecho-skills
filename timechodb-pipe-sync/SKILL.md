---
name: timechodb-pipe-sync
description: >
  Data sync (Pipe) configuration: station-to-center, full/incremental/cascade,
  air-gap penetration, encrypted compression, dual-active mirror, sync lag monitoring.
description_zh: Pipe 数据同步：场站→中心汇聚、全量/增量/级联、双活镜像、延迟监控
version: 1.0.0
agent_created: true
---

# TimechoDB Pipe 数据同步 (Pipe Sync)

## 触发场景

- "场站数据怎么同步到中心"
- "Pipe 同步延迟很高"

## Pipe 配置

### 全量 + 增量同步

```sql
-- 发送端
CREATE PIPE station_to_center
WITH SINK (
  'sink'='iotdb-thrift-sink',
  'sink.ip'='<center_ip>',
  'sink.port'='6667'
)
WITH SOURCE (
  'source'='iotdb-thrift-source',
  'source.mode'='hybrid'  -- 先全量后增量
);

START PIPE station_to_center;
```

### 级联同步

```
Station → Edge → Center
   Pipe1     Pipe2
```

### 加密 SSL

```sql
CREATE PIPE secure_pipe
WITH SINK (
  'sink'='iotdb-thrift-ssl-sink',
  'sink.ip'='<ip>',
  'sink.port'='6667',
  'sink.ssl.enable'='true'
);
```

### 网闸穿透

```bash
-- 使用跨网闸插件（需单独配置 opc-ua-sink 等）
-- 参考手册跨网闸同步章节
```

## 监控

```sql
-- 查看所有 Pipe 状态
SHOW PIPES;

-- 查看 Pipe 积压
SELECT * FROM information_schema.pipes;
```

## 延迟排查

| 症状 | 排查 |
|------|------|
| 积压持续增长 | 检查网络带宽，接收端写入能力 |
| Pipe 频繁停止 | 检查发送端 WAL，接收端端口可达 |
| 同步数据不一致 | START/STOP PIPE 重置全量同步 |
| SSL 握手失败 | 检查证书路径和密码配置 |
