# Spring Boot Integration with IoTDB

The official `iotdb-spring-boot-starter` (Apache IoTDB, `iotdb-extras` repository) auto-configures two pool
beans from the same `iotdb.session.*` properties:

| Bean type | Model | Builder used |
|-----------|-------|--------------|
| `ITableSessionPool` | Table model | `TableSessionPoolBuilder` |
| `ISessionPool` | Tree model | `SessionPool.Builder` |

Both beans are closed by Spring on shutdown (`destroyMethod = "close"`); do not close them yourself.
Each bean is created only if the application has not defined a bean of that type.

## Requirements

- IoTDB server and `iotdb-spring-boot-starter` **V2.0.3+**.
- Java 17 (the starter is compiled for Java 17).

## Dependency

```xml
<dependency>
    <groupId>org.apache.iotdb</groupId>
    <artifactId>iotdb-spring-boot-starter</artifactId>
    <version>2.0.3</version>
</dependency>
```

Gradle:

```groovy
implementation 'org.apache.iotdb:iotdb-spring-boot-starter:2.0.3'
```

## Configuration

`application.properties` (keys as in the official documentation):

```properties
# One or more nodes, separated by semicolons
iotdb.session.node_urls=127.0.0.1:6667
iotdb.session.username=root
iotdb.session.password=${IOTDB_PASSWORD}
# Default database of sessions borrowed from the table pool
iotdb.session.database=factory
iotdb.session.sql-dialect=table
# Maximum sessions per pool (default 5)
iotdb.session.max-size=10
```

Other properties of `IoTDBSessionProperties` (prefix `iotdb.session`), with defaults:

| Property | Default |
|----------|---------|
| `fetch_size` | client default |
| `query_timeout_in_ms` | `60000` |
| `enable_auto_fetch` | `true` |
| `max_retry_count` | `60` |
| `wait_to_get_session_timeout_in_ms` | `60000` |
| `enable_compression` | `false` |
| `retry_interval_in_ms` | client default |
| `use_ssl` / `trust_store` / `trust_store_pwd` | `false` / unset / unset |
| `connection_timeout_in_ms` | client default |
| `zone_id` | system default |
| `enable_redirection` | `false` |

## Table Model Service

```java
import org.apache.iotdb.isession.ITableSession;
import org.apache.iotdb.isession.SessionDataSet;
import org.apache.iotdb.isession.pool.ITableSessionPool;
import org.apache.iotdb.rpc.IoTDBConnectionException;
import org.apache.iotdb.rpc.StatementExecutionException;

import org.apache.tsfile.enums.ColumnCategory;
import org.apache.tsfile.enums.TSDataType;
import org.apache.tsfile.write.record.Tablet;

import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

@Service
public class SensorTableService {

    private final ITableSessionPool tableSessionPool;

    public SensorTableService(ITableSessionPool tableSessionPool) {
        this.tableSessionPool = tableSessionPool;
    }

    public void write(String deviceId, long time, float temperature)
            throws IoTDBConnectionException, StatementExecutionException {
        Tablet tablet = new Tablet(
            "sensors",
            Arrays.asList("device_id", "temperature"),
            Arrays.asList(TSDataType.STRING, TSDataType.FLOAT),
            Arrays.asList(ColumnCategory.TAG, ColumnCategory.FIELD),
            1);
        tablet.addTimestamp(0, time);
        tablet.addValue("device_id", 0, deviceId);
        tablet.addValue("temperature", 0, temperature);
        // close() returns the session to the pool
        try (ITableSession session = tableSessionPool.getSession()) {
            session.insert(tablet);
        }
    }

    public List<Float> recentTemperatures(String deviceId)
            throws IoTDBConnectionException, StatementExecutionException {
        List<Float> result = new ArrayList<>();
        try (ITableSession session = tableSessionPool.getSession();
             SessionDataSet dataSet = session.executeQueryStatement(
                 "SELECT temperature FROM sensors WHERE device_id = '" + deviceId
                     + "' AND time >= now() - 1h")) {
            SessionDataSet.DataIterator it = dataSet.iterator();
            while (it.next()) {
                result.add(it.getFloat("temperature"));
            }
        }
        return result;
    }
}
```

The table pool's default database comes from `iotdb.session.database`; the table above is `factory.sensors`.
Validate `deviceId` before concatenating it into SQL.

## Tree Model Service

```java
import org.apache.iotdb.isession.SessionDataSet;
import org.apache.iotdb.isession.pool.ISessionPool;
import org.apache.iotdb.isession.pool.SessionDataSetWrapper;
import org.apache.iotdb.rpc.IoTDBConnectionException;
import org.apache.iotdb.rpc.StatementExecutionException;

import org.apache.tsfile.enums.TSDataType;

import org.springframework.stereotype.Service;

import java.util.Collections;

@Service
public class SensorTreeService {

    private final ISessionPool sessionPool;

    public SensorTreeService(ISessionPool sessionPool) {
        this.sessionPool = sessionPool;
    }

    public void write(String deviceId, long time, float temperature)
            throws IoTDBConnectionException, StatementExecutionException {
        sessionPool.insertRecord(
            deviceId, time,
            Collections.singletonList("temperature"),
            Collections.singletonList(TSDataType.FLOAT),
            Collections.<Object>singletonList(temperature));
    }

    public Float latestTemperature(String deviceId)
            throws IoTDBConnectionException, StatementExecutionException {
        // closing the wrapper returns the session to the pool
        try (SessionDataSetWrapper wrapper =
                 sessionPool.executeQueryStatement("SELECT last temperature FROM " + deviceId)) {
            SessionDataSet.DataIterator it = wrapper.iterator();
            // LAST query result columns: Time, Timeseries, Value, DataType
            return it.next() ? Float.valueOf(it.getString("Value")) : null;
        }
    }
}
```

For many rows, build a `Tablet` and call `sessionPool.insertTablet(tablet)` instead of `insertRecord`
(see [Java Examples](java_examples.md)).

## Custom Pool Beans

Define your own bean to override a starter bean, for example to set builder options that have no property:

```java
import org.apache.iotdb.isession.pool.ITableSessionPool;
import org.apache.iotdb.session.pool.TableSessionPoolBuilder;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.Collections;

@Configuration
public class IoTDBConfig {

    @Bean(destroyMethod = "close")
    public ITableSessionPool tableSessionPool() {
        return new TableSessionPoolBuilder()
            .nodeUrls(Collections.singletonList("127.0.0.1:6667"))
            .user("root")
            .password(System.getenv("IOTDB_PASSWORD"))
            .database("factory")
            .maxSize(20)
            .build();
    }
}
```

## Testing

Integration tests need a running IoTDB server (for example a Testcontainers `GenericContainer` with the
`apache/iotdb` image, port 6667). Point `iotdb.session.node_urls` at it with `@DynamicPropertySource`, and use
a dedicated database that the test drops afterwards.

## Notes

- IoTDB has no transactions; `@Transactional` does not make IoTDB writes atomic or reversible.
- Always close borrowed `ITableSession`s and result sets; an unclosed one keeps its session out of the pool.
- Size `iotdb.session.max-size` to the number of request threads that use IoTDB at the same time.
