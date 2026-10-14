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
  Tier migration and the OBJECT_STORAGE cold tier are TimechoDB enterprise capabilities.
  Apache IoTDB parses tiered dn_data_dirs and tier_ttl_in_ms but never migrates data between
  tiers, and treats an uppercase OBJECT_STORAGE entry as an ordinary local directory.
  Confirm parameters against the target TimechoDB version's documentation.
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
- 冷层必须写成 `OBJECT_STORAGE`，且必须是 `dn_data_dirs` 的**最后一层**、前面至少还有一层本地目录。
  否则 DataNode 只记一条 ERROR 日志，然后把这一层换成本地默认目录 `data/datanode/data`，
  本该进对象存储的数据会落到本地盘上；
- 修改后需重启生效。

## 迁移时机

```properties
# 每层一个值，; 分隔，-1 表示不限；修改后需重启生效
tier_ttl_in_ms=604800000;2592000000;-1
# 每层一个值，个数要和层数一致：该层已用比例达到阈值时开始往下一层迁移（默认 0.85）
dn_default_space_usage_thresholds=0.85;0.85;0.85
```

数据迁移只由这两个参数触发：`tier_ttl_in_ms` 控制按时间的分层迁移，
空间阈值控制按容量触发的迁移。没有基于访问频率的判定。

空间阈值的语义以代码和配置模板注释为准：它是**每层的最大已用比例**，某层已用比例达到阈值
（即剩余比例 ≤ 1 − 阈值）时开始往下一层迁移。官方文档有的地方写成了「最小剩余空间比例」，
与代码相反，不要按那种理解填值。

只读与写满要分情况看：

- 空间阈值只用于调度迁移（以及下面 `dn_tier_full_policy=DELETE` 时的删除），**不会**把节点置为
  ReadOnly。官方文档里「最后一层级的使用率达到或超过阈值时，系统标记为 READ_ONLY」与代码不符；
- 节点进入 ReadOnly 由本地磁盘剩余比例阈值 `disk_space_warning_threshold`（默认 `0.05`）触发：
  数据盘剩余比例低于它时，DataNode 被置为 ReadOnly；
- 包含远端存储的层（`OBJECT_STORAGE`）总空间按 `Long.MAX_VALUE` 计，使用率不可能达到阈值，
  所以 `OBJECT_STORAGE` 这一层的阈值不起作用，不要把它当成「保护对象存储层」的开关来调；
- 最后一层用满之后怎么处理由 `dn_tier_full_policy` 控制，只有两个取值（区分大小写）：
  - `NULL`（默认）：不做任何处理；
  - `DELETE`：最后一层已用比例达到它的空间阈值时，从最旧的数据开始**永久删除**（即 SpaceTL）。
    这是多级存储里唯一会删数据的配置，必须向用户说明后果并得到明确同意才能设置。

```properties
disk_space_warning_threshold=0.05
dn_tier_full_policy=NULL
```

## 与 TTL 的区别（重要）

| 参数 | 作用 |
|------|------|
| `tier_ttl_in_ms` | 多级存储的分层迁移时间，只搬数据，不删数据 |
| `SET TTL` / `CREATE TABLE ... WITH (TTL=...)` | 库级/表级 TTL，**到期直接删除数据** |

两者是完全不同的东西。不要用 `SET TTL` 去触发迁移，否则会造成数据丢失。
多级存储里会删数据的只有 `dn_tier_full_policy=DELETE`（见上）。

## 对象存储

```properties
object_storage_type=AWS_S3
# 桶要预先创建；S3 桶名只能用小写字母、数字、- 和 .，不能有下划线
object_storage_bucket=iotdb-archive
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
- `OBJECT_STORAGE` 必须放在 `dn_data_dirs` 的最后一层（见「目录规划」），否则冷数据不会进对象存储。

## 查询行为

- 查询自动路由到数据所在层；冷数据需要先从对象存储拉取（经本地缓存），比热数据慢；
- 客户端无感知，SQL 不变。

## 调优

| 参数 | 建议 | 说明 |
|------|------|------|
| `remote_tsfile_cache_max_disk_usage_in_mb` | 按本地缓存盘容量设置 | 冷数据本地缓存上限（MB） |
| `dn_default_space_usage_thresholds` | 每层一个值，`;` 分隔 | 每层最大已用比例，达到即向下一层迁移（默认 0.85） |
