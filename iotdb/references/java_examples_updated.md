# Java Examples for IoTDB Connection

## Recommended Approach: SessionPool with Iterator

**SessionPool is the preferred method** for production Java applications as it provides:
- Connection pooling and resource management
- Better concurrency handling
- Automatic connection lifecycle management

**Iterator-based data reading** is recommended for:
- Memory-efficient data processing
- Streaming large datasets
- Better performance with large result sets

## Complete SessionPool Example (Recommended)

```java
package org.apache.iotdb;

import org.apache.iotdb.isession.SessionDataSet;
import org.apache.iotdb.isession.SessionDataSet.DataIterator;
import org.apache.iotdb.rpc.IoTDBConnectionException;
import org.apache.iotdb.rpc.StatementExecutionException;
import org.apache.iotdb.session.SessionPool;
import org.apache.tsfile.enums.TSDataType;
import org.apache.tsfile.file.metadata.enums.CompressionType;
import org.apache.tsfile.file.metadata.enums.TSEncoding;
import org.apache.tsfile.write.record.Tablet;
import org.apache.tsfile.write.schema.IMeasurementSchema;
import org.apache.tsfile.write.schema.MeasurementSchema;

import java.util.*;

public class IoTDBSessionPoolExample {

    private static final String HOST = "127.0.0.1";
    private static final int PORT = 6667;
    private static final String USERNAME = "root";
    private static final String PASSWORD = "root";

    public static void main(String[] args) {
        // Primary recommendation: SessionPool
        sessionPoolExample();

        // Advanced operations
        advancedSessionPoolOperations();

        // JDBC Example
        jdbcExample();
    }

    public static void sessionPoolExample() {
        SessionPool sessionPool = new SessionPool.Builder()
            .host(HOST)
            .port(PORT)
            .user(USERNAME)
            .password(PASSWORD)
            .maxSize(10)  // Connection pool size
            .build();

        try {
            System.out.println("=== SessionPool Example ===");

            // Create database and timeseries
            sessionPool.createDatabase("root.factory");
            sessionPool.createTimeseries(
                "root.factory.workshop1.temperature",
                TSDataType.FLOAT,
                TSEncoding.RLE,
                CompressionType.SNAPPY
            );

            sessionPool.createTimeseries(
                "root.factory.workshop1.humidity",
                TSDataType.FLOAT,
                TSEncoding.RLE,
                CompressionType.SNAPPY
            );

            System.out.println("Created database and timeseries using SessionPool");

            // Insert single record
            sessionPool.insertRecord(
                "root.factory.workshop1",
                System.currentTimeMillis(),
                Arrays.asList("temperature", "humidity"),
                Arrays.asList(TSDataType.FLOAT, TSDataType.FLOAT),
                Arrays.asList(25.5f, 60.0f)
            );

            // Insert multiple records
            insertMultipleRecords(sessionPool);

            // Query data with iterator (RECOMMENDED)
            queryWithIterator(sessionPool);

        } catch (IoTDBConnectionException | StatementExecutionException e) {
            System.err.println("SessionPool operation failed: " + e.getMessage());
        } finally {
            sessionPool.close();
        }
    }

    private static void insertMultipleRecords(SessionPool sessionPool)
            throws IoTDBConnectionException, StatementExecutionException {

        List<String> deviceIds = Arrays.asList(
            "root.factory.workshop1",
            "root.factory.workshop1",
            "root.factory.workshop1"
        );

        List<Long> timestamps = Arrays.asList(
            System.currentTimeMillis() + 1000,
            System.currentTimeMillis() + 2000,
            System.currentTimeMillis() + 3000
        );

        List<List<String>> measurementsList = Arrays.asList(
            Arrays.asList("temperature", "humidity"),
            Arrays.asList("temperature", "humidity"),
            Arrays.asList("temperature", "humidity")
        );

        List<List<TSDataType>> typesList = Arrays.asList(
            Arrays.asList(TSDataType.FLOAT, TSDataType.FLOAT),
            Arrays.asList(TSDataType.FLOAT, TSDataType.FLOAT),
            Arrays.asList(TSDataType.FLOAT, TSDataType.FLOAT)
        );

        List<List<Object>> valuesList = Arrays.asList(
            Arrays.asList(26.0f, 61.0f),
            Arrays.asList(24.5f, 58.5f),
            Arrays.asList(27.2f, 62.3f)
        );

        sessionPool.insertRecords(deviceIds, timestamps, measurementsList, typesList, valuesList);
        System.out.println("Inserted multiple records using SessionPool");
    }

    private static void queryWithIterator(SessionPool sessionPool)
            throws IoTDBConnectionException, StatementExecutionException {

        // Query with iterator - RECOMMENDED approach
        try (SessionDataSet dataSet = sessionPool.executeQueryStatement(
                "SELECT temperature, humidity FROM root.factory.workshop1")) {

            System.out.println("\nQuery Results (Iterator-based):");
            System.out.println("Column Names: " + dataSet.getColumnNames());

            // Use DataIterator for memory-efficient reading
            DataIterator iterator = dataSet.iterator();
            int count = 0;

            while (iterator.next() && count < 10) { // Limit output for demo
                long timestamp = iterator.getLong(1); // Time column

                // Check for null values before reading
                float temperature = iterator.isNull(2) ? 0.0f : iterator.getFloat(2);
                float humidity = iterator.isNull(3) ? 0.0f : iterator.getFloat(3);

                System.out.printf("Time: %d, Temperature: %.2f, Humidity: %.2f%n",
                    timestamp, temperature, humidity);
                count++;
            }
        }
    }

    public static void advancedSessionPoolOperations() {
        SessionPool sessionPool = new SessionPool.Builder()
            .host(HOST)
            .port(PORT)
            .user(USERNAME)
            .password(PASSWORD)
            .maxSize(15)
            .build();

        try {
            System.out.println("\n=== Advanced SessionPool Operations ===");

            // Tablet insertion for bulk data
            tabletInsertionWithPool(sessionPool);

            // Advanced queries with iterators
            advancedQueriesWithIterator(sessionPool);

            // Aggregation queries
            aggregationQueriesWithIterator(sessionPool);

        } catch (Exception e) {
            System.err.println("Advanced operations failed: " + e.getMessage());
        } finally {
            sessionPool.close();
        }
    }

    private static void tabletInsertionWithPool(SessionPool sessionPool)
            throws IoTDBConnectionException, StatementExecutionException {

        // Create schema for tablet
        List<IMeasurementSchema> schemaList = new ArrayList<>();
        schemaList.add(new MeasurementSchema("temperature", TSDataType.FLOAT));
        schemaList.add(new MeasurementSchema("humidity", TSDataType.FLOAT));
        schemaList.add(new MeasurementSchema("pressure", TSDataType.FLOAT));

        Tablet tablet = new Tablet("root.factory.workshop2", schemaList, 1000);

        // Generate bulk data
        long baseTime = System.currentTimeMillis();
        Random random = new Random();

        for (int i = 0; i < 1000; i++) {
            int rowIndex = tablet.getRowSize();
            tablet.addTimestamp(rowIndex, baseTime + i * 1000);
            tablet.addValue("temperature", rowIndex, 20.0f + random.nextFloat() * 10);
            tablet.addValue("humidity", rowIndex, 40.0f + random.nextFloat() * 30);
            tablet.addValue("pressure", rowIndex, 1000.0f + random.nextFloat() * 100);

            // Insert when tablet is full
            if (tablet.getRowSize() == tablet.getMaxRowNumber()) {
                sessionPool.insertTablet(tablet);
                tablet.reset();
            }
        }

        // Insert remaining data
        if (tablet.getRowSize() != 0) {
            sessionPool.insertTablet(tablet);
        }

        System.out.println("Bulk insert completed using SessionPool: 1000 records");
    }

    private static void advancedQueriesWithIterator(SessionPool sessionPool)
            throws IoTDBConnectionException, StatementExecutionException {

        // Time range query with conditions
        String sql = "SELECT temperature, humidity, pressure FROM root.factory.workshop2 " +
                    "WHERE temperature > 25.0 ORDER BY timestamp DESC LIMIT 50";

        try (SessionDataSet dataSet = sessionPool.executeQueryStatement(sql)) {
            System.out.println("\nAdvanced Query Results (Iterator):");

            DataIterator iterator = dataSet.iterator();
            int count = 0;

            while (iterator.next() && count < 10) {
                long timestamp = iterator.getLong(1);

                // Safe null checking for each column
                String tempStr = iterator.isNull(2) ? "NULL" : String.format("%.2f", iterator.getFloat(2));
                String humidStr = iterator.isNull(3) ? "NULL" : String.format("%.2f", iterator.getFloat(3));
                String pressureStr = iterator.isNull(4) ? "NULL" : String.format("%.2f", iterator.getFloat(4));

                System.out.printf("Time: %d, Temp: %s, Humidity: %s, Pressure: %s%n",
                    timestamp, tempStr, humidStr, pressureStr);
                count++;
            }
        }
    }

    private static void aggregationQueriesWithIterator(SessionPool sessionPool)
            throws IoTDBConnectionException, StatementExecutionException {

        String[] queries = {
            "SELECT COUNT(*) FROM root.factory.workshop2",
            "SELECT AVG(temperature), MAX(temperature), MIN(temperature) FROM root.factory.workshop2",
            "SELECT LAST(temperature), LAST(humidity) FROM root.factory.workshop2"
        };

        for (String sql : queries) {
            System.out.println("\nExecuting: " + sql);

            try (SessionDataSet dataSet = sessionPool.executeQueryStatement(sql)) {
                DataIterator iterator = dataSet.iterator();

                while (iterator.next()) {
                    List<String> columnNames = dataSet.getColumnNames();

                    for (int i = 1; i <= columnNames.size(); i++) {
                        String columnName = columnNames.get(i - 1);
                        String value = iterator.isNull(i) ? "NULL" : iterator.getString(i);
                        System.out.print(columnName + ": " + value + " ");
                    }
                    System.out.println();
                }
            }
        }
    }

    public static void jdbcExample() {
        System.out.println("\n=== JDBC Example ===");

        String jdbcUrl = "jdbc:iotdb://127.0.0.1:6667/";
        String username = "root";
        String password = "root";

        try (java.sql.Connection connection = java.sql.DriverManager.getConnection(
                jdbcUrl, username, password)) {

            // Create database and timeseries
            try (java.sql.Statement stmt = connection.createStatement()) {
                stmt.execute("CREATE DATABASE root.jdbc_example");
                stmt.execute("CREATE TIMESERIES root.jdbc_example.device.temperature " +
                           "WITH DATATYPE=FLOAT, ENCODING=RLE");

                // Insert data
                stmt.execute("INSERT INTO root.jdbc_example.device(timestamp, temperature) " +
                           "VALUES(" + System.currentTimeMillis() + ", 25.5)");

                System.out.println("JDBC operations completed");
            }

            // Query with JDBC ResultSet (iterator-based)
            try (java.sql.Statement stmt = connection.createStatement();
                 java.sql.ResultSet rs = stmt.executeQuery(
                     "SELECT * FROM root.jdbc_example.device")) {

                System.out.println("JDBC Query Results:");
                while (rs.next()) {
                    System.out.println("Time: " + rs.getLong("Time") +
                                     ", Temperature: " + rs.getFloat("root.jdbc_example.device.temperature"));
                }
            }

        } catch (Exception e) {
            System.err.println("JDBC error: " + e.getMessage());
        }
    }
}
```

## Connection Manager with Retry Logic

```java
public class IoTDBConnectionManager {
    private SessionPool sessionPool;
    private final String host;
    private final int port;
    private final String username;
    private final String password;
    private final int poolSize;

    public IoTDBConnectionManager(String host, int port, String username, String password, int poolSize) {
        this.host = host;
        this.port = port;
        this.username = username;
        this.password = password;
        this.poolSize = poolSize;
    }

    public void initializePool() throws IoTDBConnectionException {
        sessionPool = new SessionPool.Builder()
            .host(host)
            .port(port)
            .user(username)
            .password(password)
            .maxSize(poolSize)
            .build();
    }

    public void executeWithRetry(Runnable operation, int maxRetries) {
        int attempts = 0;
        while (attempts < maxRetries) {
            try {
                operation.run();
                return;  // Success
            } catch (Exception e) {
                attempts++;
                if (attempts >= maxRetries) {
                    throw new RuntimeException("Operation failed after " + maxRetries + " attempts", e);
                }

                // Wait before retry
                try {
                    Thread.sleep(1000 * attempts);  // Exponential backoff
                } catch (InterruptedException ie) {
                    Thread.currentThread().interrupt();
                    throw new RuntimeException("Interrupted during retry", ie);
                }
            }
        }
    }

    public SessionPool getSessionPool() {
        return sessionPool;
    }

    public void close() {
        if (sessionPool != null) {
            sessionPool.close();
        }
    }
}
```

## Maven Dependencies

```xml
<dependencies>
    <!-- SessionPool and Session API -->
    <dependency>
        <groupId>org.apache.iotdb</groupId>
        <artifactId>iotdb-session</artifactId>
        <version>2.0.6</version>
    </dependency>

    <!-- Table Model Session -->
    <dependency>
        <groupId>org.apache.iotdb</groupId>
        <artifactId>iotdb-table-session</artifactId>
        <version>2.0.6</version>
    </dependency>

    <!-- JDBC Driver -->
    <dependency>
        <groupId>org.apache.iotdb</groupId>
        <artifactId>iotdb-jdbc</artifactId>
        <version>2.0.6</version>
    </dependency>

    <!-- Optional: Connection Pooling -->
    <dependency>
        <groupId>com.zaxxer</groupId>
        <artifactId>HikariCP</artifactId>
        <version>5.0.1</version>
    </dependency>
</dependencies>
```

## Best Practices Summary

1. **Use SessionPool** instead of individual Session instances for production applications
2. **Always use iterators** when reading query results (`DataIterator.next()`)
3. **Use try-with-resources** for automatic resource cleanup
4. **Implement proper error handling** with retry logic for network operations
5. **Use tablets for bulk data insertion** for better performance
6. **Consider JDBC** for integration with existing Java applications and frameworks