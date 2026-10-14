---
name: iotdb
description: Connect to Apache IoTDB / TimechoDB from Java, Python, C++, JDBC and REST, using connection pools (SessionPool for the tree model, TableSessionPool for the table model) and iterator-based result reading. Covers tree model (timeseries paths) and table model (TAG/ATTRIBUTE/FIELD tables) read/write syntax. Use when users need to establish IoTDB connections, implement data insertion/querying, configure client sessions, or integrate IoTDB clients into applications.
license: Complete terms in LICENSE
compatibility: >
  Examples target IoTDB/TimechoDB V2.0.x clients and servers; keep the client version equal to
  the server version. The table model requires V2.0+. The C++ SessionPool requires V2.0.11+.
---

# IoTDB Connection Guide

## License

This skill is licensed under the **Apache License 2.0**.

IoTDB itself is an Apache Software Foundation project licensed under Apache 2.0. All code examples and templates in this skill follow the same license for compatibility and consistency with the IoTDB ecosystem.

## Overview

Provides guidance for connecting to Apache IoTDB / TimechoDB from Java, Python, C++, JDBC and REST, for both data models:

- **Tree model**: hierarchical timeseries paths such as `root.factory.line1.device7.temperature`.
- **Table model** (V2.0+): tables whose columns are `TAG`, `ATTRIBUTE`, `FIELD` and a `TIME` column.

For choosing between the models and planning a migration, use the `timechodb-tree-table-guide` skill.

## Connection Decision Tree

**Application code always goes through a pool.** Create one pool per application (a singleton),
share it across threads, and close it on shutdown. Do not create a pool per request, and do not use a
bare `Session` / `TableSession` in application code.

| Client | Tree model | Table model |
|--------|------------|-------------|
| Java | `SessionPool` | `ITableSessionPool` (built by `TableSessionPoolBuilder`) |
| Python | `SessionPool` (+ `PoolConfig`) | `TableSessionPool` (+ `TableSessionPoolConfig`) |
| C++ | `SessionPool` (V2.0.11+) | `SessionPool` with `sqlDialect("table")` (V2.0.11+) |
| JDBC | `jdbc:iotdb://<host>:6667/` | `jdbc:iotdb://<host>:6667/<database>?sql_dialect=table` |
| REST | `/rest/v2/*` | `/rest/table/v1/*` |

- C++ before V2.0.11 has no pool: create one `Session` / `TableSession` per worker thread, open it once and
  reuse it.
- JDBC is for frameworks that require it (MyBatis, Spring `JdbcTemplate`); native pools are faster for bulk writes.
- REST is disabled by default (`enable_rest_service=true` in `iotdb-system.properties`, port `18080`).

### Connection defaults

- RPC port: `6667`.
- User: `root`. Default password: `root` for Apache IoTDB; `TimechoDB@2021` for TimechoDB V2.0.6.1+.
  Never hard-code credentials in production code.

## Data Model Selection

- **Tree model**: path-oriented access, devices addressed by path, wildcard queries (`*`, `**`).
- **Table model**: one table per device type; `TAG` columns identify a device, `ATTRIBUTE` columns hold
  device-level metadata, `FIELD` columns hold measurements; SQL-style filtering, `GROUP BY`, joins.

See [Data Models Guide](references/data_models.md) for syntax of both models.

## Java

```xml
<dependency>
    <groupId>org.apache.iotdb</groupId>
    <artifactId>iotdb-session</artifactId>
    <!-- keep equal to the server version -->
    <version>${iotdb.version}</version>
</dependency>
```

### Tree model: SessionPool

```java
import org.apache.iotdb.isession.SessionDataSet;
import org.apache.iotdb.isession.pool.SessionDataSetWrapper;
import org.apache.iotdb.session.pool.SessionPool;

import org.apache.tsfile.enums.TSDataType;
import org.apache.tsfile.write.record.Tablet;
import org.apache.tsfile.write.schema.IMeasurementSchema;
import org.apache.tsfile.write.schema.MeasurementSchema;

// One pool per application; share it across threads and close it on shutdown.
SessionPool sessionPool = new SessionPool.Builder()
    .nodeUrls(Collections.singletonList("127.0.0.1:6667"))
    .user("root")
    .password("root")
    .maxSize(10)
    .build();

// Write: batch rows of one device into a Tablet.
// Timeseries are created automatically on first write (enable_auto_create_schema=true by default).
List<IMeasurementSchema> schemas = Arrays.asList(
    new MeasurementSchema("temperature", TSDataType.FLOAT),
    new MeasurementSchema("humidity", TSDataType.FLOAT));
Tablet tablet = new Tablet("root.factory.line1.device7", schemas, 1000);
long start = System.currentTimeMillis();
for (int i = 0; i < 5000; i++) {
    int row = tablet.getRowSize();
    tablet.addTimestamp(row, start + i * 1000L);
    tablet.addValue("temperature", row, 20.0f + i % 10);
    tablet.addValue("humidity", row, 60.0f);
    if (tablet.getRowSize() == tablet.getMaxRowNumber()) {
        sessionPool.insertTablet(tablet);
        tablet.reset();
    }
}
if (tablet.getRowSize() != 0) {
    sessionPool.insertTablet(tablet);
    tablet.reset();
}

// Read: SessionPool returns a SessionDataSetWrapper; closing it returns the session to the pool.
try (SessionDataSetWrapper wrapper = sessionPool.executeQueryStatement(
        "SELECT temperature FROM root.factory.line1.device7 WHERE time >= now() - 1h")) {
    SessionDataSet.DataIterator it = wrapper.iterator();
    while (it.next()) {
        long time = it.getLong("Time");
        float temperature = it.getFloat("root.factory.line1.device7.temperature");
    }
}

// On application shutdown
sessionPool.close();
```

### Table model: TableSessionPool

Create the database and table once (CLI, migration script, or a session borrowed from the pool):

```sql
CREATE DATABASE IF NOT EXISTS factory;
USE factory;
CREATE TABLE IF NOT EXISTS sensors (
  region STRING TAG,
  plant_id STRING TAG,
  device_id STRING TAG,
  model STRING ATTRIBUTE,
  temperature FLOAT FIELD,
  humidity DOUBLE FIELD
) WITH (TTL=31536000000);
```

```java
import org.apache.iotdb.isession.ITableSession;
import org.apache.iotdb.isession.SessionDataSet;
import org.apache.iotdb.isession.pool.ITableSessionPool;
import org.apache.iotdb.session.pool.TableSessionPoolBuilder;

import org.apache.tsfile.enums.ColumnCategory;   // V2.0.2: org.apache.tsfile.write.record.Tablet.ColumnCategory
import org.apache.tsfile.enums.TSDataType;
import org.apache.tsfile.write.record.Tablet;

ITableSessionPool tablePool = new TableSessionPoolBuilder()
    .nodeUrls(Collections.singletonList("127.0.0.1:6667"))
    .user("root")
    .password("root")
    .database("factory")   // default database of every borrowed session
    .maxSize(10)
    .build();

// Borrow a session per unit of work; close() returns it to the pool.
try (ITableSession session = tablePool.getSession()) {
    List<String> columns = Arrays.asList("region", "plant_id", "device_id", "model", "temperature", "humidity");
    List<TSDataType> types = Arrays.asList(TSDataType.STRING, TSDataType.STRING, TSDataType.STRING,
        TSDataType.STRING, TSDataType.FLOAT, TSDataType.DOUBLE);
    List<ColumnCategory> categories = Arrays.asList(ColumnCategory.TAG, ColumnCategory.TAG,
        ColumnCategory.TAG, ColumnCategory.ATTRIBUTE, ColumnCategory.FIELD, ColumnCategory.FIELD);

    Tablet tablet = new Tablet("sensors", columns, types, categories, 1000);
    int row = tablet.getRowSize();
    tablet.addTimestamp(row, System.currentTimeMillis());
    tablet.addValue("region", row, "north");
    tablet.addValue("plant_id", row, "p1");
    tablet.addValue("device_id", row, "d7");
    tablet.addValue("model", row, "A");
    tablet.addValue("temperature", row, 25.5f);
    tablet.addValue("humidity", row, 60.0);
    session.insert(tablet);

    try (SessionDataSet dataSet = session.executeQueryStatement(
            "SELECT time, device_id, temperature FROM sensors "
                + "WHERE region = 'north' AND time >= now() - 1h")) {
        SessionDataSet.DataIterator it = dataSet.iterator();
        while (it.next()) {
            long time = it.getLong("time");
            String deviceId = it.getString("device_id");
            float temperature = it.getFloat("temperature");
        }
    }
}

// On application shutdown
tablePool.close();
```

A `USE <db>` executed in a borrowed session only lasts until the session is returned; the next borrower
starts from the pool's `database(...)` again.

More: [Java Examples](references/java_examples.md) (concurrency, aligned timeseries, error handling, retries).

### JDBC and frameworks

```java
// Tree model
Connection tree = DriverManager.getConnection("jdbc:iotdb://127.0.0.1:6667/", "root", "root");
// Table model
Connection table = DriverManager.getConnection(
    "jdbc:iotdb://127.0.0.1:6667/factory?sql_dialect=table", "root", "root");
```

IoTDB has no transactions: `commit()` / `rollback()` are no-ops. See [JDBC Examples](references/jdbc_examples.md),
[Spring Boot Integration](references/spring_boot_integration.md) (official `iotdb-spring-boot-starter`, which
exposes `ISessionPool` and `ITableSessionPool` beans) and [MyBatis Integration](references/mybatis_integration.md).

## Python

```bash
pip install apache-iotdb==<server version>
```

### Tree model: SessionPool

```python
from iotdb.SessionPool import PoolConfig, SessionPool
from iotdb.utils.IoTDBConstants import TSDataType
from iotdb.utils.Tablet import Tablet

pool_config = PoolConfig(
    host="127.0.0.1", port="6667", user_name="root", password="root",
    fetch_size=1024, time_zone="Asia/Shanghai", max_retry=3,
)
session_pool = SessionPool(pool_config, max_pool_size=10, wait_timeout_in_ms=3000)

session = session_pool.get_session()
try:
    # values: one list per row, in the order of the measurements
    tablet = Tablet(
        "root.factory.line1.device7",
        ["temperature", "humidity"],
        [TSDataType.FLOAT, TSDataType.FLOAT],
        [[25.5, 60.0], [26.0, 61.5], [24.8, 58.2]],
        [1700000000000, 1700000001000, 1700000002000],
    )
    session.insert_tablet(tablet)

    with session.execute_query_statement(
        "SELECT temperature FROM root.factory.line1.device7"
    ) as data_set:
        while data_set.has_next():
            print(data_set.next())
finally:
    session_pool.put_back(session)

session_pool.close()  # on application shutdown
```

### Table model: TableSessionPool

```python
from iotdb.table_session_pool import TableSessionPool, TableSessionPoolConfig
from iotdb.utils.IoTDBConstants import TSDataType
from iotdb.utils.Tablet import ColumnType, Tablet

config = TableSessionPoolConfig(
    node_urls=["127.0.0.1:6667"], username="root", password="root",
    database="factory", max_pool_size=10, wait_timeout_in_ms=3000,
)
table_pool = TableSessionPool(config)

session = table_pool.get_session()
try:
    tablet = Tablet(
        "sensors",
        ["region", "plant_id", "device_id", "model", "temperature", "humidity"],
        [TSDataType.STRING] * 4 + [TSDataType.FLOAT, TSDataType.DOUBLE],
        [["north", "p1", "d7", "A", 25.5, 60.0]],
        [1700000000000],
        [ColumnType.TAG] * 3 + [ColumnType.ATTRIBUTE] + [ColumnType.FIELD] * 2,
    )
    session.insert(tablet)

    with session.execute_query_statement(
        "SELECT * FROM sensors WHERE device_id = 'd7'"
    ) as data_set:
        while data_set.has_next():
            print(data_set.next())
finally:
    session.close()  # returns the session to the pool

table_pool.close()  # on application shutdown
```

More: [Python Examples](references/python_examples.md) (threads, pandas, `next_df()` batches).

## C++

V2.0.11+ ships a `SessionPool`; earlier versions only have `Session` / `TableSession`.
See [C++ Examples](references/cpp_examples.md) for both.

## REST

```bash
# Tree model (REST v2)
curl -H "Content-Type: application/json" -H "Authorization: Basic cm9vdDpyb290" \
     -X POST --data '{"sql": "SELECT temperature FROM root.factory.line1.device7 LIMIT 10"}' \
     http://127.0.0.1:18080/rest/v2/query

# Table model
curl -H "Content-Type: application/json" -H "Authorization: Basic cm9vdDpyb290" \
     -X POST --data '{"database": "factory", "sql": "SELECT * FROM sensors LIMIT 10"}' \
     http://127.0.0.1:18080/rest/table/v1/query
```

`cm9vdDpyb290` is `base64("root:root")`. See [REST API Reference](references/rest_api.md).

## SSL/TLS

- Java: `new SessionPool.Builder()...useSSL(true).trustStore("/path/to/truststore").trustStorePwd("<pwd>")`;
  `TableSessionPoolBuilder` has the same three methods.
- Python: `PoolConfig(..., use_ssl=True, ca_certs="/path/to/ca.pem")`; `TableSessionPoolConfig` takes the same.
- JDBC: URL parameters `use_ssl=true&trust_store=<path>&trust_store_pwd=<pwd>`.
- The server must have `enable_thrift_ssl=true`. That switches the whole RPC port to SSL, so every client
  connecting to that node must use SSL.

## Best Practices

1. **Connections**
   - One pool per application, shared by all threads; size `maxSize` to the number of concurrent workers.
   - Always return borrowed sessions (`try`-with-resources in Java, `put_back()` / `close()` in Python)
     and close every result set; an unclosed result set keeps its session out of the pool.
   - Configure `waitToGetSessionTimeoutInMs` (Java) / `wait_timeout_in_ms` (Python) so that pool exhaustion
     fails fast instead of hanging.
2. **Reading**
   - Iterate results row by row (`DataIterator`, `has_next()`/`next()`), or in DataFrame batches with
     `has_next_df()`/`next_df()` (Python V2.0.8+). Use `todf()` only for small results.
   - Always bound queries by time (`WHERE time >= ... AND time < ...`) and, in the table model, by TAG values.
3. **Writing**
   - Use `Tablet` batches (hundreds to thousands of rows) instead of row-by-row inserts.
   - Tree model: use aligned timeseries for measurements that are always written together.
4. **Schema**
   - Neither model has user-creatable secondary indexes; do not suggest "adding an index".
     Tree queries are located by path; table queries by TAG values and time.
   - Table model: TAG columns identify the device (they can be high-cardinality, e.g. `device_id`);
     ATTRIBUTE columns hold device metadata; never store measurements in TAG columns.

## Resources

### References

- [Java Examples](references/java_examples.md) - SessionPool / TableSessionPool, concurrency, error handling
- [Python Examples](references/python_examples.md) - SessionPool / TableSessionPool, threads, pandas
- [C++ Examples](references/cpp_examples.md) - SessionPool (V2.0.11+) and Session / TableSession for older versions
- [JDBC Examples](references/jdbc_examples.md) - Tree and table dialect URLs, batching, HikariCP
- [Spring Boot Integration](references/spring_boot_integration.md) - Official `iotdb-spring-boot-starter`
- [MyBatis Integration](references/mybatis_integration.md) - MyBatis / MyBatis-Plus over IoTDB JDBC
- [REST API Reference](references/rest_api.md) - Tree model REST v2 and table model REST
- [Data Models Guide](references/data_models.md) - Tree and table model syntax

### Scripts

- [Connection Validator](scripts/validate_connection.py) - Check RPC (tree/table) and REST connectivity
- [Connection Smoke Test](scripts/performance_test.py) - Quick client-side write/query timing through a SessionPool;
  for capacity benchmarks use the `timechodb-benchmark` skill (iot-benchmark)

### Assets

- [Connection Templates](assets/connection_templates/) - Java and Python templates built on the pools
