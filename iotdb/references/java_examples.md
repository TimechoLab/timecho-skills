# Java Examples for IoTDB Connection

Application code uses a pool: `SessionPool` for the tree model and `ITableSessionPool` for the table model.
Create each pool once, share it across threads, and close it when the application stops.

## Maven Dependency

```xml
<dependency>
    <groupId>org.apache.iotdb</groupId>
    <artifactId>iotdb-session</artifactId>
    <!-- keep equal to the server version -->
    <version>${iotdb.version}</version>
</dependency>
```

Version notes:

- The table model (`ITableSessionPool`, `TableSessionPoolBuilder`) requires V2.0+.
- `ColumnCategory` is `org.apache.tsfile.enums.ColumnCategory` from V2.0.3; V2.0.2 uses
  `org.apache.tsfile.write.record.Tablet.ColumnCategory`.
- The examples use the V2.0 `Tablet` API (`getRowSize()`, `addTimestamp()`, `addValue()`).

## Pool Holder

```java
import org.apache.iotdb.isession.pool.ITableSessionPool;
import org.apache.iotdb.session.pool.SessionPool;
import org.apache.iotdb.session.pool.TableSessionPoolBuilder;

import java.util.Arrays;
import java.util.List;

public final class IoTDBPools {

    private static final List<String> NODE_URLS = Arrays.asList("127.0.0.1:6667");
    private static final String USER = System.getenv().getOrDefault("IOTDB_USER", "root");
    private static final String PASSWORD = System.getenv().getOrDefault("IOTDB_PASSWORD", "root");

    /** Tree model pool. */
    public static final SessionPool TREE = new SessionPool.Builder()
        .nodeUrls(NODE_URLS)
        .user(USER)
        .password(PASSWORD)
        .maxSize(10)
        .waitToGetSessionTimeoutInMs(30_000)
        .build();

    /** Table model pool; borrowed sessions start in database "factory". */
    public static final ITableSessionPool TABLE = new TableSessionPoolBuilder()
        .nodeUrls(NODE_URLS)
        .user(USER)
        .password(PASSWORD)
        .database("factory")
        .maxSize(10)
        .waitToGetSessionTimeoutInMs(30_000)
        .build();

    static {
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            TREE.close();
            TABLE.close();
        }));
    }

    private IoTDBPools() {}
}
```

Pools connect lazily, so building them does not fail when the server is down; the first operation does.

## Tree Model

### Schema

```java
import org.apache.iotdb.isession.pool.SessionDataSetWrapper;
import org.apache.iotdb.rpc.IoTDBConnectionException;
import org.apache.iotdb.rpc.StatementExecutionException;
import org.apache.iotdb.session.pool.SessionPool;

import org.apache.tsfile.enums.TSDataType;
import org.apache.tsfile.file.metadata.enums.CompressionType;
import org.apache.tsfile.file.metadata.enums.TSEncoding;

import java.util.Arrays;

public class TreeSchema {

    /** CREATE DATABASE has no IF NOT EXISTS in the tree model, so check first. */
    static void ensureDatabase(SessionPool pool, String database)
            throws IoTDBConnectionException, StatementExecutionException {
        try (SessionDataSetWrapper wrapper = pool.executeQueryStatement("SHOW DATABASES " + database)) {
            if (wrapper.hasNext()) {
                return;
            }
        }
        pool.createDatabase(database);
    }

    static void createSchema(SessionPool pool) throws IoTDBConnectionException, StatementExecutionException {
        ensureDatabase(pool, "root.factory");

        // Non-aligned timeseries with explicit encoding/compression
        String path = "root.factory.line1.device7.temperature";
        if (!pool.checkTimeseriesExists(path)) {
            pool.createTimeseries(path, TSDataType.FLOAT, TSEncoding.GORILLA, CompressionType.LZ4);
        }

        // Aligned timeseries: measurements always written together
        if (!pool.checkTimeseriesExists("root.factory.line1.device8.temperature")) {
            pool.createAlignedTimeseries(
                "root.factory.line1.device8",
                Arrays.asList("temperature", "humidity"),
                Arrays.asList(TSDataType.FLOAT, TSDataType.FLOAT),
                Arrays.asList(TSEncoding.GORILLA, TSEncoding.GORILLA),
                Arrays.asList(CompressionType.LZ4, CompressionType.LZ4),
                null);
        }
    }
}
```

Explicit creation is optional: with `enable_auto_create_schema=true` (default) the first write creates the
timeseries with default encodings.

### Batch Write with Tablet

```java
import org.apache.iotdb.rpc.IoTDBConnectionException;
import org.apache.iotdb.rpc.StatementExecutionException;
import org.apache.iotdb.session.pool.SessionPool;

import org.apache.tsfile.enums.TSDataType;
import org.apache.tsfile.write.record.Tablet;
import org.apache.tsfile.write.schema.IMeasurementSchema;
import org.apache.tsfile.write.schema.MeasurementSchema;

import java.util.Arrays;
import java.util.List;

public class TreeWriter {

    static void writeDevice(SessionPool pool, String deviceId, long startTime, int rows, boolean aligned)
            throws IoTDBConnectionException, StatementExecutionException {
        List<IMeasurementSchema> schemas = Arrays.asList(
            new MeasurementSchema("temperature", TSDataType.FLOAT),
            new MeasurementSchema("humidity", TSDataType.FLOAT));
        Tablet tablet = new Tablet(deviceId, schemas, 1000);

        for (int i = 0; i < rows; i++) {
            int row = tablet.getRowSize();
            tablet.addTimestamp(row, startTime + i * 1000L);
            tablet.addValue("temperature", row, 20.0f + (i % 100) / 10.0f);
            tablet.addValue("humidity", row, 55.0f + (i % 50) / 10.0f);
            if (tablet.getRowSize() == tablet.getMaxRowNumber()) {
                flush(pool, tablet, aligned);
            }
        }
        if (tablet.getRowSize() != 0) {
            flush(pool, tablet, aligned);
        }
    }

    private static void flush(SessionPool pool, Tablet tablet, boolean aligned)
            throws IoTDBConnectionException, StatementExecutionException {
        if (aligned) {
            pool.insertAlignedTablet(tablet);
        } else {
            pool.insertTablet(tablet);
        }
        tablet.reset();
    }
}
```

### Query with Iterator

```java
import org.apache.iotdb.isession.SessionDataSet;
import org.apache.iotdb.isession.pool.SessionDataSetWrapper;
import org.apache.iotdb.rpc.IoTDBConnectionException;
import org.apache.iotdb.rpc.StatementExecutionException;
import org.apache.iotdb.session.pool.SessionPool;

public class TreeReader {

    static void readRange(SessionPool pool, String deviceId, long from, long to)
            throws IoTDBConnectionException, StatementExecutionException {
        String sql = String.format(
            "SELECT temperature, humidity FROM %s WHERE time >= %d AND time < %d", deviceId, from, to);
        // Closing the wrapper returns the session to the pool; never leave it open.
        try (SessionDataSetWrapper wrapper = pool.executeQueryStatement(sql)) {
            SessionDataSet.DataIterator it = wrapper.iterator();
            while (it.next()) {
                long time = it.getLong("Time");
                // Value columns are full paths; check isNull() before reading primitives.
                String temperatureColumn = deviceId + ".temperature";
                if (!it.isNull(temperatureColumn)) {
                    float temperature = it.getFloat(temperatureColumn);
                    System.out.printf("%d %.2f%n", time, temperature);
                }
            }
        }
    }

    static void hourlyAverage(SessionPool pool, String deviceId)
            throws IoTDBConnectionException, StatementExecutionException {
        String sql = "SELECT avg(temperature) FROM " + deviceId
            + " GROUP BY ([2023-11-14T00:00:00, 2023-11-15T00:00:00), 1h)";
        try (SessionDataSetWrapper wrapper = pool.executeQueryStatement(sql)) {
            SessionDataSet.DataIterator it = wrapper.iterator();
            while (it.next()) {
                System.out.println(it.getLong("Time") + " " + it.getString(2));
            }
        }
    }
}
```

`DataIterator` column indexes are 1-based, like JDBC; index 1 is the time column.

## Table Model

### Schema

```java
import org.apache.iotdb.isession.ITableSession;
import org.apache.iotdb.isession.pool.ITableSessionPool;
import org.apache.iotdb.rpc.IoTDBConnectionException;
import org.apache.iotdb.rpc.StatementExecutionException;

public class TableSchema {

    /** Run with a pool whose builder does not set database(...), or before the database exists. */
    static void createSchema(ITableSessionPool pool) throws IoTDBConnectionException, StatementExecutionException {
        try (ITableSession session = pool.getSession()) {
            session.executeNonQueryStatement("CREATE DATABASE IF NOT EXISTS factory");
            session.executeNonQueryStatement(
                "CREATE TABLE IF NOT EXISTS factory.sensors ("
                    + "region STRING TAG, "
                    + "plant_id STRING TAG, "
                    + "device_id STRING TAG, "
                    + "model STRING ATTRIBUTE, "
                    + "temperature FLOAT FIELD, "
                    + "humidity DOUBLE FIELD"
                    + ") WITH (TTL=31536000000)");
        }
    }
}
```

TAG columns identify the device and may be high-cardinality (`device_id`); ATTRIBUTE columns hold device
metadata; FIELD columns hold measurements. The `time` column is added automatically.

### Batch Write with Tablet

```java
import org.apache.iotdb.isession.ITableSession;
import org.apache.iotdb.isession.pool.ITableSessionPool;
import org.apache.iotdb.rpc.IoTDBConnectionException;
import org.apache.iotdb.rpc.StatementExecutionException;

import org.apache.tsfile.enums.ColumnCategory;
import org.apache.tsfile.enums.TSDataType;
import org.apache.tsfile.write.record.Tablet;

import java.util.Arrays;
import java.util.List;

public class TableWriter {

    private static final List<String> COLUMNS =
        Arrays.asList("region", "plant_id", "device_id", "model", "temperature", "humidity");
    private static final List<TSDataType> TYPES = Arrays.asList(
        TSDataType.STRING, TSDataType.STRING, TSDataType.STRING, TSDataType.STRING,
        TSDataType.FLOAT, TSDataType.DOUBLE);
    private static final List<ColumnCategory> CATEGORIES = Arrays.asList(
        ColumnCategory.TAG, ColumnCategory.TAG, ColumnCategory.TAG, ColumnCategory.ATTRIBUTE,
        ColumnCategory.FIELD, ColumnCategory.FIELD);

    static void write(ITableSessionPool pool, String deviceId, long startTime, int rows)
            throws IoTDBConnectionException, StatementExecutionException {
        try (ITableSession session = pool.getSession()) {
            Tablet tablet = new Tablet("sensors", COLUMNS, TYPES, CATEGORIES, 1000);
            for (int i = 0; i < rows; i++) {
                int row = tablet.getRowSize();
                tablet.addTimestamp(row, startTime + i * 1000L);
                tablet.addValue("region", row, "north");
                tablet.addValue("plant_id", row, "p1");
                tablet.addValue("device_id", row, deviceId);
                tablet.addValue("model", row, "A");
                tablet.addValue("temperature", row, 20.0f + (i % 100) / 10.0f);
                tablet.addValue("humidity", row, 55.0 + (i % 50) / 10.0);
                if (tablet.getRowSize() == tablet.getMaxRowNumber()) {
                    session.insert(tablet);
                    tablet.reset();
                }
            }
            if (tablet.getRowSize() != 0) {
                session.insert(tablet);
                tablet.reset();
            }
        }
    }
}
```

### Query with Iterator

```java
import org.apache.iotdb.isession.ITableSession;
import org.apache.iotdb.isession.SessionDataSet;
import org.apache.iotdb.isession.pool.ITableSessionPool;
import org.apache.iotdb.rpc.IoTDBConnectionException;
import org.apache.iotdb.rpc.StatementExecutionException;

public class TableReader {

    static void hourlyAverage(ITableSessionPool pool, String region)
            throws IoTDBConnectionException, StatementExecutionException {
        String sql = "SELECT date_bin(1h, time) AS hour_time, device_id, avg(temperature) AS avg_temp "
            + "FROM sensors "
            + "WHERE region = '" + region + "' AND time >= now() - 1d "
            + "GROUP BY date_bin(1h, time), device_id "
            + "ORDER BY hour_time";
        try (ITableSession session = pool.getSession();
             SessionDataSet dataSet = session.executeQueryStatement(sql)) {
            SessionDataSet.DataIterator it = dataSet.iterator();
            while (it.next()) {
                System.out.printf("%d %s %s%n",
                    it.getLong("hour_time"), it.getString("device_id"), it.getString("avg_temp"));
            }
        }
    }
}
```

Validate or whitelist any user input concatenated into SQL (TAG values, table names).

## Concurrent Use

```java
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

public class ConcurrentWrite {

    public static void main(String[] args) throws Exception {
        ExecutorService executor = Executors.newFixedThreadPool(8);
        List<Future<?>> futures = new ArrayList<>();
        long start = System.currentTimeMillis();
        for (int d = 0; d < 100; d++) {
            String deviceId = "root.factory.line1.device" + d;
            // All threads share one pool; each call borrows and returns a session internally.
            futures.add(executor.submit(() -> {
                TreeWriter.writeDevice(IoTDBPools.TREE, deviceId, start, 10_000, true);
                return null;
            }));
        }
        for (Future<?> f : futures) {
            f.get();
        }
        executor.shutdown();
    }
}
```

Size `maxSize` to the number of threads that use the pool at the same time; extra threads wait up to
`waitToGetSessionTimeoutInMs` for a free session.

## Error Handling

- `IoTDBConnectionException`: network or connection failure. `SessionPool` already retries and reconnects
  (`maxRetryCount`, `retryIntervalInMs` on the builder); after that, fail the operation or retry later.
- `StatementExecutionException`: the server rejected the statement (syntax, schema, permission, read-only node).
  `getStatusCode()` returns the `TSStatusCode` value; do not retry these blindly.

```java
import org.apache.iotdb.rpc.IoTDBConnectionException;
import org.apache.iotdb.rpc.StatementExecutionException;
import org.apache.iotdb.rpc.TSStatusCode;

try {
    IoTDBPools.TREE.createDatabase("root.factory");
} catch (StatementExecutionException e) {
    if (e.getStatusCode() != TSStatusCode.DATABASE_ALREADY_EXISTS.getStatusCode()) {
        throw e;
    }
} catch (IoTDBConnectionException e) {
    // server unreachable after the pool's own retries
    throw e;
}
```

## Best Practices

1. One pool per model per application; never build a pool per request.
2. Close every `SessionDataSetWrapper` / `SessionDataSet` and every borrowed `ITableSession`
   (`try`-with-resources). Leaked result sets exhaust the pool.
3. Batch writes with `Tablet` (hundreds to thousands of rows); one Tablet per device (tree) or per table (table).
4. Bound every query by time, and in the table model by TAG values.
5. Neither model has user-creatable secondary indexes.
