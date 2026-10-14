# IoTDB Data Models: Tree vs Table Model Syntax Guide

## Overview

IoTDB supports two data models:

- **Tree model**: timeseries addressed by hierarchical paths.
- **Table model** (V2.0+): relational-style tables with `TAG`, `ATTRIBUTE`, `FIELD` and `TIME` columns.

The SQL dialect is chosen per connection (`sql_dialect=tree|table`, CLI `-sql_dialect table`). Tree and table
schemas are separate; a statement only sees the model of its connection. For choosing a model and mapping
an existing tree schema to tables, use the `timechodb-tree-table-guide` skill.

## Tree Model (Timeseries Model)

### Path Structure

```
root.<database>.<device path>.<measurement>
```

The database is a path prefix (for example `root.factory`); the device path may have several levels; the
last node is the measurement.

```
root.factory.line1.device7.temperature
root.vehicle.car001.speed
```

### Database Operations

```sql
CREATE DATABASE root.factory
SHOW DATABASES
SHOW DATABASES root.factory
DELETE DATABASE root.factory
```

The tree model has no `USE`; every statement uses full paths. `CREATE DATABASE` has no `IF NOT EXISTS`;
check with `SHOW DATABASES <path>` first if the statement must be idempotent.

### Timeseries Operations

Timeseries are created automatically on first write while `enable_auto_create_schema=true` (default).
Create them explicitly to control data type, encoding and compression:

```sql
CREATE TIMESERIES root.factory.line1.device7.temperature WITH DATATYPE=FLOAT, ENCODING=GORILLA, COMPRESSION=LZ4

-- Aligned timeseries: measurements of one device written together share one time column
CREATE ALIGNED TIMESERIES root.factory.line1.device8(temperature FLOAT, humidity FLOAT)

-- Timeseries tags and attributes (metadata attached to one timeseries)
CREATE TIMESERIES root.factory.line1.device7.pressure WITH DATATYPE=FLOAT
TAGS(unit='kPa') ATTRIBUTES(vendor='SensorCorp')

SHOW TIMESERIES root.factory.**
SHOW DEVICES root.factory.**
COUNT TIMESERIES root.factory.**
```

**Data types:** `BOOLEAN`, `INT32`, `INT64`, `FLOAT`, `DOUBLE`, `TEXT`, `STRING`, `BLOB`, `TIMESTAMP`, `DATE`.
Prefer `STRING` for short strings (it keeps statistics that speed up value filters); `TEXT` is for long text.

**Common encodings:** `PLAIN`, `RLE`, `TS_2DIFF`, `GORILLA`, `DICTIONARY`; leave encoding unspecified to use
the server default for the data type.

### Data Insertion

```sql
INSERT INTO root.factory.line1.device7(timestamp, temperature, humidity)
VALUES (1700000000000, 25.5, 60.0)

INSERT INTO root.factory.line1.device7(timestamp, temperature, humidity) VALUES
(1700000000000, 25.5, 60.0),
(1700000001000, 25.8, 59.2)
```

Writing the same timestamp again overwrites the previous value. Use client `Tablet` APIs for bulk writes.

### Data Querying

```sql
-- One device
SELECT temperature, humidity FROM root.factory.line1.device7
WHERE time >= 2023-11-14T00:00:00 AND time < 2023-11-15T00:00:00

-- Relative time
SELECT temperature FROM root.factory.line1.device7 WHERE time >= now() - 1h

-- All devices under a prefix: * matches one level, ** matches any number of levels
SELECT temperature FROM root.factory.*.*
SELECT temperature FROM root.factory.**

-- Aggregation per time window
SELECT avg(temperature), max(temperature)
FROM root.factory.line1.device7
GROUP BY ([2023-11-14T00:00:00, 2023-11-15T00:00:00), 1h)

-- Fill empty windows with the previous value
SELECT avg(temperature)
FROM root.factory.line1.device7
GROUP BY ([2023-11-14T00:00:00, 2023-11-15T00:00:00), 1h)
FILL(PREVIOUS)

-- Latest value of each timeseries
SELECT last temperature FROM root.factory.**

-- One row per device instead of one column per timeseries
SELECT temperature FROM root.factory.** ALIGN BY DEVICE
```

In query results the time column is `Time` and value columns are full paths
(for example `root.factory.line1.device7.temperature`), unless `ALIGN BY DEVICE` is used.

## Table Model (Relational Model, V2.0+)

### Database Operations

```sql
CREATE DATABASE IF NOT EXISTS factory
USE factory
SHOW DATABASES
DROP DATABASE factory
```

### Column Categories

| Category | Meaning |
|----------|---------|
| `TAG` | Device identifier. All TAG columns together identify one device (like a composite primary key); a table may have zero or more. High cardinality is expected (for example `device_id`). TAG values of a device do not change, and TAG columns cannot be dropped. |
| `ATTRIBUTE` | Device-level metadata (for example `model`, `firmware`). One value per device, not per row; it can be updated with `UPDATE`. |
| `FIELD` | Measurements; one value per row. |
| `TIME` | Timestamp column. If `CREATE TABLE` declares no TIME column, a column named `time` is added automatically. It can be declared explicitly as `time TIMESTAMP TIME`; a custom name is allowed since Apache IoTDB V2.0.8 / TimechoDB V2.0.8.2. |

### Create Table

Create one table per device type:

```sql
CREATE TABLE IF NOT EXISTS sensors (
    region STRING TAG,
    plant_id STRING TAG,
    device_id STRING TAG,
    model STRING ATTRIBUTE,
    install_date DATE ATTRIBUTE,
    temperature FLOAT FIELD,
    humidity DOUBLE FIELD,
    status BOOLEAN FIELD
) WITH (TTL=31536000000)   -- data older than one year (ms) is no longer visible

SHOW TABLES
DESC sensors
SHOW CREATE TABLE sensors
ALTER TABLE sensors ADD COLUMN IF NOT EXISTS pressure FLOAT FIELD
ALTER TABLE sensors SET PROPERTIES TTL=2592000000
```

`TTL` is the only table property.

### Data Operations

```sql
-- Insert rows; TAG values select the device, ATTRIBUTE values set the device metadata
INSERT INTO sensors (time, region, plant_id, device_id, model, temperature, humidity)
VALUES (1700000000000, 'north', 'p1', 'd7', 'A', 25.5, 60.0),
       (1700000001000, 'north', 'p1', 'd7', 'A', 25.8, 59.2)

-- Only ATTRIBUTE columns can be updated; the WHERE clause may only use TAG and ATTRIBUTE columns
UPDATE sensors SET model = 'B' WHERE device_id = 'd7'

-- Delete by time range and/or TAG values
DELETE FROM sensors WHERE time < 1690000000000 AND device_id = 'd7'
```

Writing the same device and timestamp again overwrites the FIELD values of that row.

### Query Syntax

```sql
-- Filter by TAG values and time first
SELECT time, device_id, temperature FROM sensors
WHERE region = 'north' AND plant_id = 'p1' AND time >= now() - 1h

-- Aggregation per device
SELECT device_id, avg(temperature), max(humidity)
FROM sensors
WHERE time >= now() - 1d
GROUP BY device_id

-- Time windows
SELECT date_bin(1h, time) AS hour_time, device_id, avg(temperature) AS avg_temp
FROM sensors
WHERE time >= now() - 1d
GROUP BY date_bin(1h, time), device_id
ORDER BY hour_time

-- Latest row per device
SELECT device_id, last(time), last_by(temperature, time)
FROM sensors
GROUP BY device_id
```

Result columns use the table's column names (`time`, `device_id`, ...).

## Data Model Comparison

| Aspect | Tree Model | Table Model |
|--------|------------|-------------|
| **Structure** | Hierarchical paths | One table per device type |
| **Device identity** | Device path | Values of the TAG columns |
| **Query style** | Path patterns with `*` / `**` | SQL with `WHERE` on TAG columns and time |
| **Indexes** | No user-creatable secondary indexes | No user-creatable secondary indexes |
| **Metadata** | Timeseries tags/attributes (per timeseries) | ATTRIBUTE columns (per device) |
| **Client APIs** | `SessionPool`, JDBC, REST v2 | `TableSessionPool`, JDBC (`sql_dialect=table`), table REST |

## Schema Design Best Practices

### Tree Model

1. Put the database at a stable, coarse level (`root.factory`), not at device level.
2. Keep the path a real hierarchy that queries follow (`root.factory.<line>.<device>.<measurement>`);
   avoid encoding changing values (status, version) into path nodes.
3. Use consistent measurement names across devices of the same type so that `**` queries line up.
4. Use aligned timeseries for measurements always written together.

### Table Model

1. One table per device type; devices of the same type share the FIELD columns.
2. TAG columns: the attributes that identify a device (`region`, `plant_id`, `device_id`). A high-cardinality
   TAG such as `device_id` is normal; do not avoid it.
3. ATTRIBUTE columns: descriptive device metadata that may change (`model`, `firmware`).
4. FIELD columns: measured values. Never model measurements as rows of a generic
   `(sensor_type TAG, value FIELD)` table; give each measurement its own FIELD column.
5. Filter by TAG columns and time in every query.

```sql
-- Good
CREATE TABLE turbine (
    farm STRING TAG,
    turbine_id STRING TAG,
    model STRING ATTRIBUTE,
    wind_speed FLOAT FIELD,
    power DOUBLE FIELD
)

-- Avoid: measurements stored as key/value rows, and a changing value used as TAG
CREATE TABLE turbine_kv (
    turbine_id STRING TAG,
    status STRING TAG,        -- changes over time; makes the same turbine look like many devices
    metric_name STRING TAG,   -- measurement name as data
    value DOUBLE FIELD
)
```

## Migration Between Models

A tree schema does not translate mechanically into tables. Decide explicitly:

- which path levels identify a device (they become TAG columns);
- which path level is the device type (it becomes the table);
- which leaves are measurements (they become FIELD columns);
- what happens to timeseries tags/attributes (they do not become TAG/ATTRIBUTE columns automatically).

```text
Tree:  root.factory.beijing.line1.device7.temperature

  root.factory   -> database (confirm this boundary first)
  beijing        -> region      TAG
  line1          -> line        TAG
  device7        -> device_id   TAG
  temperature    -> temperature FIELD of table <device type>
```

This is a design mapping, not executable DDL. Cross-model views and migration tools are version-specific;
verify them against the target version before generating DDL. The `timechodb-tree-table-guide` skill has a
mapping checklist.
