---
name: timechodb-tier-storage
description: >
  Configure TimechoDB tiered storage: hot/warm/cold tiers, moving aged data to object
  storage, and tuning tier TTL and space thresholds. Use when the user asks to set up
  cold/hot data separation, archive old data to S3-compatible object storage, or reduce
  local disk usage.
metadata:
  version: "1.0.0"
  description_zh: >-
    多级存储：热/温/冷分层、冷数据转对象存储、分层 TTL 与空间阈值配置
compatibility: >
  Tiered storage is a TimechoDB enterprise capability. Confirm tier syntax and threshold
  semantics against the target version's documentation before applying.
---

# TimechoDB 多级存储 (Tiered Storage)

## 触发场景

- "怎么配置冷热数据分层"
- "我想把老数据放到对象存储上"
- "本地盘不够了，想按时间把数据挪走"

## 目录规划

```properties
dn_data_dirs=/data/ssd;/data/hdd;OBJECT_STORAGE
```

分隔符规则（`IoTDBDescriptor.parseDataDirs`）：

- **层与层之间用 `;` 分隔，同一层内的多个目录用 `,` 分隔**；
- `/data/ssd,/data/hdd` 是**同一层**里的两个目录，`dn_multi_dir_strategy` 只决定同层内往哪个目录写，
  不会形成冷热分层；
- 冷层必须写成 `OBJECT_STORAGE`，且必须放在 `dn_data_dirs` 的**最后一层**，
  否则下面整组 `object_storage_*` 配置都不会生效；
- 修改后需重启生效。

## 迁移时机

```properties
# 每层一个值，; 分隔，-1 表示不限；修改后需重启生效
tier_ttl_in_ms=604800000;2592000000;-1
# 值的个数要和层数一致
dn_default_space_usage_thresholds=<tier1>;<tier2>;<tier3>
```

数据迁移只由这两个参数触发：`tier_ttl_in_ms` 控制按时间的分层迁移，
空间阈值控制按容量触发的迁移。没有基于访问频率的判定。

⚠️ 空间阈值的语义（“每层最大使用率” 还是 “剩余空间阈值”）官方文档的参数表与示例表
表述不一致，两种理解下数值的调整方向正好相反。**必须按目标版本的文档确认后再改**，
不要凭经验填值。另外，最后一层达到阈值后系统会进入 `READ_ONLY`。

## 与 TTL 的区别（重要）

| 参数 | 作用 |
|------|------|
| `tier_ttl_in_ms` | 多级存储的分层迁移时间，只搬数据，不删数据 |
| `SET TTL` / `CREATE TABLE ... WITH (TTL=...)` | 库级/表级 TTL，**到期直接删除数据** |

两者是完全不同的东西。不要用 `SET TTL` 去触发迁移，否则会造成数据丢失。

## 对象存储

```properties
object_storage_type=AWS_S3
object_storage_bucket=iotdb_archive
object_storage_region=<region>
object_storage_endpoint=https://s3.example.com
object_storage_access_key=<key>
object_storage_access_secret=<secret>
# MinIO 等 S3 兼容存储按需开启
enable_path_style_access=true
remote_tsfile_cache_dirs=/data/cache
remote_tsfile_cache_max_disk_usage_in_mb=51200
```

- `object_storage_region` 是必填项（使用远程存储时）；
- 整组配置仅在 `dn_data_dirs` 最后一层为 `OBJECT_STORAGE` 时生效。

## 查询行为

- 查询自动路由到数据所在层；冷数据需要先从对象存储拉取（经本地缓存），比热数据慢；
- 客户端无感知，SQL 不变。

## 调优

| 参数 | 建议 | 说明 |
|------|------|------|
| `remote_tsfile_cache_max_disk_usage_in_mb` | 按本地缓存盘容量设置 | 冷数据本地缓存上限（MB） |
| `dn_default_space_usage_thresholds` | 每层一个值，`;` 分隔 | 迁移触发阈值，语义以目标版本文档为准 |
