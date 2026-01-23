# IoTDB Data Models: Tree vs Table Model Syntax Guide

## Overview

IoTDB supports two data models: Tree Model (traditional timeseries) and Table Model (relational-style). Understanding the syntax differences is crucial for effective IoTDB usage.

## Tree Model (Timeseries Model)

### Path Structure and Syntax

**Basic Path Format:**
```
root.{database}.{device}.{sensor}
```

**Examples:**
```
root.factory.workshop01.temperature
root.vehicle.car001.speed
root.smart_home.living_room.humidity
root.industrial.machine_A.pressure
```

### Database Operations

**Create Database:**
```sql
CREATE DATABASE root.factory
CREATE DATABASE root.vehicle
```

**Show Databases:**
```sql
SHOW DATABASES
```

**Use Database:**
```sql
-- Not required in tree model, paths are absolute
```

### Timeseries Operations

**Create Timeseries:**
```sql
-- Basic creation
CREATE TIMESERIES root.factory.workshop01.temperature WITH DATATYPE=FLOAT, ENCODING=RLE

-- With compression
CREATE TIMESERIES root.factory.workshop01.humidity
WITH DATATYPE=DOUBLE, ENCODING=GORILLA, COMPRESSION=SNAPPY

-- With tags and attributes
CREATE TIMESERIES root.factory.workshop01.pressure
WITH DATATYPE=FLOAT, ENCODING=RLE, COMPRESSION=SNAPPY
TAGS(location='workshop', type='sensor')
ATTRIBUTES(manufacturer='SensorCorp', model='P100')
```

**Show Timeseries:**
```sql
SHOW TIMESERIES
SHOW TIMESERIES root.factory.*
SHOW TIMESERIES root.factory.** WHERE DATATYPE=FLOAT
```

**Data Types:**
- `BOOLEAN` - true/false values
- `INT32` - 32-bit signed integers
- `INT64` - 64-bit signed integers
- `FLOAT` - 32-bit floating point
- `DOUBLE` - 64-bit floating point
- `TEXT` - String values
- `TIMESTAMP` - Timestamp values

**Encoding Types:**
- `PLAIN` - No encoding
- `RLE` - Run Length Encoding (good for integers)
- `GORILLA` - Gorilla encoding (good for floating point)
- `DICTIONARY` - Dictionary encoding (good for text)
- `TS_2DIFF` - Two-level difference encoding

### Data Insertion

**Insert Single Record:**
```sql
INSERT INTO root.factory.workshop01(timestamp, temperature, humidity)
VALUES(1635724800000, 25.5, 60.0)

-- With NOW() function
INSERT INTO root.factory.workshop01(timestamp, temperature, humidity)
VALUES(NOW(), 26.1, 58.5)
```

**Insert Multiple Records:**
```sql
INSERT INTO root.factory.workshop01(timestamp, temperature, humidity) VALUES
(1635724800000, 25.5, 60.0),
(1635724860000, 25.8, 59.2),
(1635724920000, 26.1, 58.5)
```

### Data Querying

**Basic Queries:**
```sql
-- Select all data
SELECT * FROM root.factory.workshop01

-- Select specific measurements
SELECT temperature, humidity FROM root.factory.workshop01

-- With time range
SELECT * FROM root.factory.workshop01
WHERE time >= '2021-11-01T00:00:00' AND time < '2021-11-02T00:00:00'

-- With value conditions
SELECT * FROM root.factory.workshop01
WHERE temperature > 25.0 AND humidity < 60.0
```

**Aggregation Functions:**
```sql
-- Basic aggregations
SELECT count(*), avg(temperature), max(temperature), min(temperature)
FROM root.factory.workshop01

-- With time grouping
SELECT count(*), avg(temperature)
FROM root.factory.workshop01
GROUP BY ([2021-11-01T00:00:00, 2021-11-02T00:00:00), 1h)

-- Fill missing values
SELECT avg(temperature)
FROM root.factory.workshop01
GROUP BY ([2021-11-01T00:00:00, 2021-11-02T00:00:00), 1h)
FILL(previous)
```

**Wildcard Queries:**
```sql
-- Single level wildcard
SELECT * FROM root.factory.*

-- Multi-level wildcard
SELECT * FROM root.factory.**

-- Pattern matching
SELECT * FROM root.factory.workshop* WHERE temperature > 25.0
```

## Table Model (Relational Model)

### Database and Table Structure

**Database Operations:**
```sql
-- Create database
CREATE DATABASE factory

-- Use database
USE factory

-- Show databases
SHOW DATABASES
```

### Table Schema Design

**Column Categories:**
- `TAG` - Index columns, low cardinality, used for filtering
- `ATTRIBUTE` - Metadata columns, rarely change
- `FIELD` - Data columns, actual measurements
- `TIME` - Timestamp column (implicit)

**Create Table:**
```sql
-- Basic table creation
CREATE TABLE sensors (
    region_id STRING TAG,
    device_id STRING TAG,
    device_type STRING ATTRIBUTE,
    manufacturer STRING ATTRIBUTE,
    temperature FLOAT FIELD,
    humidity DOUBLE FIELD,
    pressure FLOAT FIELD
) WITH (TTL=7200000)  -- TTL in milliseconds

-- Table with more options
CREATE TABLE weather_data (
    station_id STRING TAG,
    city STRING TAG,
    country STRING ATTRIBUTE,
    elevation INT32 ATTRIBUTE,
    temperature FLOAT FIELD,
    humidity FLOAT FIELD,
    wind_speed FLOAT FIELD,
    rainfall DOUBLE FIELD
) WITH (
    TTL=2592000000,  -- 30 days TTL
    partition_interval='1d'  -- Daily partitioning
)
```

**Show Tables:**
```sql
SHOW TABLES
DESCRIBE sensors
SHOW CREATE TABLE sensors
```

### Data Operations

**Insert Data:**
```sql
-- Insert single row
INSERT INTO sensors (time, region_id, device_id, device_type, temperature, humidity)
VALUES (NOW(), 'region_1', 'device_001', 'temperature_sensor', 25.5, 60.0)

-- Insert multiple rows
INSERT INTO sensors (time, region_id, device_id, device_type, temperature, humidity, pressure)
VALUES
(1635724800000, 'region_1', 'device_001', 'multi_sensor', 25.5, 60.0, 1013.25),
(1635724860000, 'region_1', 'device_001', 'multi_sensor', 25.8, 59.2, 1013.15),
(1635724920000, 'region_1', 'device_001', 'multi_sensor', 26.1, 58.5, 1013.05)
```

### Query Syntax

**Basic Queries:**
```sql
-- Select all data
SELECT * FROM sensors

-- Select specific columns
SELECT time, region_id, temperature, humidity FROM sensors

-- Filter by tags (most efficient)
SELECT * FROM sensors WHERE region_id = 'region_1'

-- Filter by multiple conditions
SELECT * FROM sensors
WHERE region_id = 'region_1' AND device_type = 'temperature_sensor'

-- Time range queries
SELECT * FROM sensors
WHERE time >= '2021-11-01T00:00:00' AND time < '2021-11-02T00:00:00'
```

**Advanced Queries:**
```sql
-- Aggregation queries
SELECT region_id, avg(temperature), max(humidity)
FROM sensors
WHERE time > NOW() - 1h
GROUP BY region_id

-- Time window aggregation
SELECT region_id,
       date_bin(INTERVAL '1' HOUR, time) as hour_window,
       avg(temperature) as avg_temp,
       count(*) as sample_count
FROM sensors
WHERE time > NOW() - 1d
GROUP BY region_id, hour_window
ORDER BY hour_window

-- Join-like operations (using tags)
SELECT s1.region_id, s1.temperature, s2.humidity
FROM sensors s1, sensors s2
WHERE s1.region_id = s2.region_id
AND s1.device_id = s2.device_id
AND s1.time = s2.time
```

## Data Model Comparison

| Aspect | Tree Model | Table Model |
|--------|------------|-------------|
| **Structure** | Hierarchical paths | Relational tables |
| **Query Style** | Path-based with wildcards | SQL-based with WHERE clauses |
| **Indexing** | Path-based indexes | TAG columns are indexed |
| **Scalability** | Excellent for timeseries | Better for complex queries |
| **Learning Curve** | IoT-specific syntax | Familiar SQL syntax |
| **Use Cases** | Traditional IoT monitoring | Analytics and reporting |

## Schema Design Best Practices

### Tree Model Best Practices

1. **Path Design:**
   ```sql
   -- Good: Logical hierarchy
   root.factory.building1.floor2.room201.temperature

   -- Better: Shorter, still logical
   root.factory.b1f2r201.temperature

   -- Avoid: Too deep nesting
   root.company.site.building.floor.room.zone.sensor.temperature
   ```

2. **Measurement Naming:**
   ```sql
   -- Good: Clear, consistent naming
   root.factory.workshop01.temperature
   root.factory.workshop01.humidity
   root.factory.workshop01.pressure

   -- Avoid: Inconsistent naming
   root.factory.workshop01.temp
   root.factory.workshop01.humid_level
   root.factory.workshop01.air_pressure_reading
   ```

### Table Model Best Practices

1. **Column Category Selection:**
   ```sql
   CREATE TABLE sensors (
       -- TAGs: Low cardinality, used for filtering
       region STRING TAG,          -- Good: Few regions
       building STRING TAG,        -- Good: Limited buildings

       -- ATTRIBUTEs: Metadata, rarely changes
       sensor_model STRING ATTRIBUTE,
       installation_date DATE ATTRIBUTE,

       -- FIELDs: Actual measurements
       temperature FLOAT FIELD,
       humidity FLOAT FIELD,

       -- Avoid: High cardinality TAGs
       -- sensor_serial STRING TAG  -- Bad: Too many unique values
   )
   ```

2. **Efficient Filtering:**
   ```sql
   -- Efficient: Filter by TAGs first
   SELECT * FROM sensors
   WHERE region = 'north' AND building = 'A'
   AND time > NOW() - 1h

   -- Less efficient: Filter by FIELDs without TAG filters
   SELECT * FROM sensors
   WHERE temperature > 25.0  -- Should combine with TAG filters
   ```

## Migration Between Models

### Tree to Table Model

```sql
-- Original tree model data
-- root.factory.workshop01.temperature
-- root.factory.workshop01.humidity

-- Equivalent table model
CREATE TABLE factory_sensors (
    workshop STRING TAG,
    sensor_type STRING TAG,
    value DOUBLE FIELD
) WITH (TTL=2592000000)

-- Or normalized approach
CREATE TABLE workshop_data (
    workshop_id STRING TAG,
    temperature FLOAT FIELD,
    humidity FLOAT FIELD
) WITH (TTL=2592000000)
```

### Table to Tree Model

```sql
-- Original table model
-- sensors(region_id, device_id, temperature, humidity)

-- Equivalent tree model paths
-- root.{region_id}.{device_id}.temperature
-- root.{region_id}.{device_id}.humidity

CREATE TIMESERIES root.region1.device001.temperature WITH DATATYPE=FLOAT, ENCODING=RLE
CREATE TIMESERIES root.region1.device001.humidity WITH DATATYPE=FLOAT, ENCODING=RLE
```

## Performance Considerations

### Tree Model Performance

1. **Path Indexing:** Shorter paths perform better
2. **Wildcard Queries:** Use specific patterns when possible
3. **Batch Operations:** Use tablets for bulk insertions

### Table Model Performance

1. **TAG Optimization:** Design TAGs for common query patterns
2. **Time Range:** Always include time range filters
3. **Partitioning:** Use appropriate partition intervals

## Common Syntax Patterns

### Tree Model Query Patterns

```sql
-- Device-centric queries
SELECT * FROM root.factory.device001.*

-- Measurement-centric queries
SELECT temperature FROM root.factory.**

-- Time-series analysis
SELECT avg(temperature) FROM root.factory.**
GROUP BY ([NOW()-1d, NOW()), 1h)
```

### Table Model Query Patterns

```sql
-- Tag-based filtering (most efficient)
SELECT * FROM sensors WHERE region = 'north'

-- Time-based analysis
SELECT date_bin(INTERVAL '1' HOUR, time) as hour,
       avg(temperature)
FROM sensors
WHERE time > NOW() - 1d
GROUP BY hour

-- Cross-device analysis
SELECT region, device_type, avg(temperature)
FROM sensors
WHERE time > NOW() - 1h
GROUP BY region, device_type
```