---
name: timechodb-tier-storage
description: >
  Multi-tier storage: hot (SSD) → warm → cold (object storage/HDD) auto-tiering,
  access frequency rules, query scheduling logic and parameter tuning.
description_zh: 多级存储：SSD→温→冷对象存储自动分层策略、访问频率判定、查询调度
version: 1.0.0
agent_created: true
---

# TimechoDB 多级存储 (Tiered Storage)

## 触发场景

- "怎么配置冷热数据分层"
- "我想把老数据放到对象存储上"

## 配置

### 目录规划

```
/data/ssd/    → 热数据 (近 7 天)
/data/hdd/    → 温数据 (7-30 天)
s3://bucket/  → 冷数据 (30 天+)
```

### 参数设置

```properties
# iotdb-system.properties
dn_data_dirs=/data/ssd,/data/hdd
dn_multi_dir_strategy=MaxDiskUsableSpaceFirstStrategy
dn_default_space_usage_thresholds=0.85,0.90
```

### 对象存储

```properties
object_storage_type=AWS_S3
object_storage_bucket=iotdb_archive
object_storage_endpoint=https://s3.example.com
object_storage_access_key=<key>
object_storage_access_secret=<secret>
remote_tsfile_cache_dirs=/data/cache
remote_tsfile_cache_max_disk_usage_in_mb=51200
```

## 分层策略

```
写入 → 热层(SSD) → TTL 到期/空间不足 → 温层(HDD)
                                   → 冷层(S3)
查询 → 热层直接读 → 温层本地读 → 冷层先缓存再读
```

## 查询行为

- 查询自动路由到数据所在层
- 冷数据查询比热数据慢（需从对象存储拉取）
- 客户端无感知，SQL 不变

## 调优

| 参数 | 建议 | 说明 |
|------|------|------|
| remote_tsfile_cache_max | 100GB | 冷数据本地缓存上限 |
| space_usage_thresholds | 0.75 | 更早触发分层迁移 |
