# Conservative Tree and Table Syntax Shapes

Confirm the connected version and use the matching SQL dialect before adapting
these shapes.

## Tree model

```sql
CREATE DATABASE root.<database>;

CREATE TIMESERIES root.<database>.<device>.<measurement>
  WITH DATATYPE=<type>;

SELECT <measurement>
FROM root.<database>.<device>
WHERE time >= <start_timestamp> AND time < <end_timestamp>;
```

The full timeseries path ends at the measurement, while ordinary query `FROM`
binds the device/path pattern. Integer time literals are interpreted in the
cluster's `timestamp_precision` (`ms`, `us` or `ns`, fixed at first start); do
not assume milliseconds.

## Table model

```sql
CREATE DATABASE <database>;
USE <database>;

CREATE TABLE <table> (
  device_id STRING TAG,
  model STRING ATTRIBUTE,
  temperature FLOAT FIELD
);

SELECT device_id, AVG(temperature)
FROM <table>
WHERE time >= <start_timestamp> AND time < <end_timestamp>
GROUP BY device_id;
```

The Table model adds a `time` column automatically when `CREATE TABLE` omits a
TIME column; declaring it explicitly (`time TIMESTAMP TIME`) is also valid, and
since Apache IoTDB V2.0.8 / TimechoDB V2.0.8.2 the TIME column may use a custom
name. Use the table's actual TIME column name in `INSERT`, `SELECT`, and time
predicates.
Select the database with `USE <database>` (or the client's database setting)
before `CREATE TABLE` or queries.

## Do not translate mechanically

- Tree path nodes do not automatically become Table TAG columns.
- Tree tags and attributes do not automatically become Table TAG and ATTRIBUTE
  columns.
- Tree grouping, alignment, pagination, and fill syntax are not portable Table
  syntax.
- Table joins, windows, CTEs, and set operations are not portable Tree syntax.
- Cross-model view or migration DDL is version-specific and must be verified
  before generation.
