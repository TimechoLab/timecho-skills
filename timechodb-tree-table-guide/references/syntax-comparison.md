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
WHERE time >= <start_epoch_ms> AND time < <end_epoch_ms>;
```

The full timeseries path ends at the measurement, while ordinary query `FROM`
binds the device/path pattern.

## Table model

```sql
CREATE DATABASE <database>;

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

The Table model creates the `time` column implicitly; do not declare it in
`CREATE TABLE`. It remains available in `INSERT`, `SELECT`, and time predicates.
Select the intended Table database using the target runtime's supported context
or SQL mechanism before execution. Do not assume qualification is portable.

## Do not translate mechanically

- Tree path nodes do not automatically become Table TAG columns.
- Tree tags and attributes do not automatically become Table TAG and ATTRIBUTE
  columns.
- Tree grouping, alignment, pagination, and fill syntax are not portable Table
  syntax.
- Table joins, windows, CTEs, and set operations are not portable Tree syntax.
- Cross-model view or migration DDL is version-specific and must be verified
  before generation.
