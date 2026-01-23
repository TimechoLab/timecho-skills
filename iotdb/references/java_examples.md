# Java Examples for IoTDB Connection

## Recommended Approach: SessionPool with Iterators

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

        // Alternative: Basic session (use SessionPool instead)
        // basicSessionExample();

        // Advanced operations
        advancedSessionPoolOperations();
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

            // Create database
            session.createDatabase("root.factory");

            // Create timeseries
            session.createTimeseries(
                "root.factory.workshop1.temperature",
                TSDataType.FLOAT,
                TSEncoding.RLE,
                CompressionType.SNAPPY
            );

            session.createTimeseries(
                "root.factory.workshop1.humidity",
                TSDataType.FLOAT,
                TSEncoding.RLE,
                CompressionType.SNAPPY
            );

            // Insert single record
            List<String> measurements = Arrays.asList("temperature", "humidity");
            List<TSDataType> types = Arrays.asList(TSDataType.FLOAT, TSDataType.FLOAT);
            List<Object> values = Arrays.asList(25.5f, 60.0f);

            session.insertRecord(
                "root.factory.workshop1",
                System.currentTimeMillis(),
                measurements,
                types,
                values
            );

            // Insert multiple records
            List<String> deviceIds = Arrays.asList(
                "root.factory.workshop1",
                "root.factory.workshop2"
            );
            List<Long> timestamps = Arrays.asList(
                System.currentTimeMillis(),
                System.currentTimeMillis() + 1000
            );
            List<List<String>> measurementsList = Arrays.asList(
                Arrays.asList("temperature", "humidity"),
                Arrays.asList("temperature", "humidity")
            );
            List<List<TSDataType>> typesList = Arrays.asList(
                Arrays.asList(TSDataType.FLOAT, TSDataType.FLOAT),
                Arrays.asList(TSDataType.FLOAT, TSDataType.FLOAT)
            );
            List<List<Object>> valuesList = Arrays.asList(
                Arrays.asList(26.0f, 61.0f),
                Arrays.asList(24.5f, 58.5f)
            );

            session.insertRecords(deviceIds, timestamps, measurementsList, typesList, valuesList);

            // Query data
            SessionDataSet dataSet = session.executeQueryStatement(
                "SELECT temperature, humidity FROM root.factory.workshop1 WHERE time >= now() - 1h"
            );

            System.out.println("Column Names: " + dataSet.getColumnNames());
            while (dataSet.hasNext()) {
                System.out.println(dataSet.next());
            }
            dataSet.close();

        } catch (IoTDBConnectionException | StatementExecutionException e) {
            e.printStackTrace();
        } finally {
            try {
                session.close();
            } catch (IoTDBConnectionException e) {
                e.printStackTrace();
            }
        }
    }

    public static void tabletInsertExample() {
        Session session = new Session.Builder()
            .host(HOST)
            .port(PORT)
            .username(USERNAME)
            .password(PASSWORD)
            .build();

        try {
            session.open(false);

            // Create tablet for efficient bulk insertion
            List<IMeasurementSchema> schemaList = new ArrayList<>();
            schemaList.add(new MeasurementSchema("temperature", TSDataType.FLOAT));
            schemaList.add(new MeasurementSchema("humidity", TSDataType.FLOAT));
            schemaList.add(new MeasurementSchema("pressure", TSDataType.FLOAT));

            Tablet tablet = new Tablet("root.factory.workshop1", schemaList, 1000);

            long timestamp = System.currentTimeMillis();
            Random random = new Random();

            // Add 100 rows of data
            for (int i = 0; i < 100; i++) {
                int rowIndex = tablet.getRowSize();
                tablet.addTimestamp(rowIndex, timestamp + i * 1000);
                tablet.addValue("temperature", rowIndex, 20.0f + random.nextFloat() * 10);
                tablet.addValue("humidity", rowIndex, 50.0f + random.nextFloat() * 30);
                tablet.addValue("pressure", rowIndex, 1000.0f + random.nextFloat() * 100);

                // Insert when tablet is full or at the end
                if (tablet.getRowSize() == tablet.getMaxRowNumber()) {
                    session.insertTablet(tablet);
                    tablet.reset();
                }
            }

            // Insert remaining data
            if (tablet.getRowSize() != 0) {
                session.insertTablet(tablet);
            }

        } catch (Exception e) {
            e.printStackTrace();
        } finally {
            try {
                session.close();
            } catch (IoTDBConnectionException e) {
                e.printStackTrace();
            }
        }
    }

    public static void sessionPoolExample() {
        SessionPool sessionPool = new SessionPool.Builder()
            .host(HOST)
            .port(PORT)
            .user(USERNAME)
            .password(PASSWORD)
            .maxSize(10)  // Maximum concurrent sessions
            .build();

        try {
            // Use session pool for concurrent operations
            sessionPool.insertRecord(
                "root.factory.workshop1",
                System.currentTimeMillis(),
                Arrays.asList("temperature"),
                Arrays.asList(TSDataType.FLOAT),
                Arrays.asList(25.0f)
            );

            SessionDataSet dataSet = sessionPool.executeQueryStatement(
                "SELECT * FROM root.factory.workshop1 LIMIT 10"
            );

            while (dataSet.hasNext()) {
                System.out.println(dataSet.next());
            }
            dataSet.close();

        } catch (Exception e) {
            e.printStackTrace();
        } finally {
            sessionPool.close();
        }
    }

    public static void advancedOperationsExample() {
        Session session = new Session.Builder()
            .host(HOST)
            .port(PORT)
            .username(USERNAME)
            .password(PASSWORD)
            .build();

        try {
            session.open(false);

            // Create timeseries with tags and attributes
            Map<String, String> tags = new HashMap<>();
            tags.put("location", "workshop1");
            tags.put("type", "sensor");

            Map<String, String> attributes = new HashMap<>();
            attributes.put("manufacturer", "ACME");
            attributes.put("model", "T1000");

            session.createTimeseries(
                "root.factory.workshop1.sensor1",
                TSDataType.FLOAT,
                TSEncoding.RLE,
                CompressionType.SNAPPY,
                null,  // props
                tags,
                attributes,
                "temperature_sensor"  // alias
            );

            // Query with aggregation
            SessionDataSet dataSet = session.executeQueryStatement(
                "SELECT AVG(temperature), MAX(temperature), MIN(temperature) " +
                "FROM root.factory.workshop1 " +
                "WHERE time >= now() - 1d " +
                "GROUP BY ([now() - 1d, now()), 1h)"
            );

            System.out.println("Aggregation Results:");
            while (dataSet.hasNext()) {
                System.out.println(dataSet.next());
            }
            dataSet.close();

            // Delete data
            session.deleteData(
                Arrays.asList("root.factory.workshop1.temperature"),
                System.currentTimeMillis() - 3600000  // Delete data older than 1 hour
            );

        } catch (Exception e) {
            e.printStackTrace();
        } finally {
            try {
                session.close();
            } catch (IoTDBConnectionException e) {
                e.printStackTrace();
            }
        }
    }
}
```

## Complete Java Table Model Example

```java
package org.apache.iotdb;

import org.apache.iotdb.isession.ITableSession;
import org.apache.iotdb.isession.SessionDataSet;
import org.apache.iotdb.rpc.IoTDBConnectionException;
import org.apache.iotdb.rpc.StatementExecutionException;
import org.apache.iotdb.session.TableSessionBuilder;
import org.apache.tsfile.enums.ColumnCategory;
import org.apache.tsfile.enums.TSDataType;
import org.apache.tsfile.write.record.Tablet;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;

public class IoTDBTableModelExample {

    private static final String LOCAL_URL = "127.0.0.1:6667";

    public static void main(String[] args) {
        tableModelBasicExample();
        tableModelAdvancedExample();
    }

    public static void tableModelBasicExample() {
        try (ITableSession session = new TableSessionBuilder()
                .nodeUrls(Collections.singletonList(LOCAL_URL))
                .username("root")
                .password("root")
                .build()) {

            // Create database
            session.executeNonQueryStatement("CREATE DATABASE factory");
            session.executeNonQueryStatement("USE factory");

            // Create table with different column categories
            session.executeNonQueryStatement(
                "CREATE TABLE sensors(" +
                "region_id STRING TAG, " +
                "plant_id STRING TAG, " +
                "device_id STRING TAG, " +
                "device_type STRING ATTRIBUTE, " +
                "manufacturer STRING ATTRIBUTE, " +
                "temperature FLOAT FIELD, " +
                "humidity DOUBLE FIELD, " +
                "pressure FLOAT FIELD" +
                ") WITH (TTL=7200000)"
            );

            // Insert data using tablet
            insertTableData(session);

            // Query data
            queryTableData(session);

        } catch (IoTDBConnectionException | StatementExecutionException e) {
            e.printStackTrace();
        }
    }

    private static void insertTableData(ITableSession session)
            throws IoTDBConnectionException, StatementExecutionException {

        List<String> columnNames = Arrays.asList(
            "region_id", "plant_id", "device_id", "device_type",
            "manufacturer", "temperature", "humidity", "pressure"
        );

        List<TSDataType> dataTypes = Arrays.asList(
            TSDataType.STRING, TSDataType.STRING, TSDataType.STRING,
            TSDataType.STRING, TSDataType.STRING,
            TSDataType.FLOAT, TSDataType.DOUBLE, TSDataType.FLOAT
        );

        List<ColumnCategory> columnCategories = Arrays.asList(
            ColumnCategory.TAG, ColumnCategory.TAG, ColumnCategory.TAG,
            ColumnCategory.ATTRIBUTE, ColumnCategory.ATTRIBUTE,
            ColumnCategory.FIELD, ColumnCategory.FIELD, ColumnCategory.FIELD
        );

        Tablet tablet = new Tablet("sensors", columnNames, dataTypes, columnCategories, 100);

        // Add sample data
        for (int i = 0; i < 50; i++) {
            int rowIndex = tablet.getRowSize();
            tablet.addTimestamp(rowIndex, System.currentTimeMillis() + i * 1000);
            tablet.addValue("region_id", rowIndex, "region_" + (i % 3));
            tablet.addValue("plant_id", rowIndex, "plant_" + (i % 5));
            tablet.addValue("device_id", rowIndex, "device_" + i);
            tablet.addValue("device_type", rowIndex, i % 2 == 0 ? "temperature_sensor" : "humidity_sensor");
            tablet.addValue("manufacturer", rowIndex, i % 3 == 0 ? "ACME" : "TechCorp");
            tablet.addValue("temperature", rowIndex, 20.0f + (float)(Math.random() * 15));
            tablet.addValue("humidity", rowIndex, 40.0 + (Math.random() * 30));
            tablet.addValue("pressure", rowIndex, 1000.0f + (float)(Math.random() * 100));

            if (tablet.getRowSize() == tablet.getMaxRowNumber()) {
                session.insert(tablet);
                tablet.reset();
            }
        }

        if (tablet.getRowSize() != 0) {
            session.insert(tablet);
        }
    }

    private static void queryTableData(ITableSession session)
            throws IoTDBConnectionException, StatementExecutionException {

        // Basic query
        try (SessionDataSet dataSet = session.executeQueryStatement(
                "SELECT * FROM sensors WHERE region_id = 'region_0' LIMIT 10")) {
            System.out.println("Basic Query Results:");
            printDataSet(dataSet);
        }

        // Aggregation query
        try (SessionDataSet dataSet = session.executeQueryStatement(
                "SELECT region_id, AVG(temperature), MAX(humidity) " +
                "FROM sensors " +
                "GROUP BY region_id")) {
            System.out.println("Aggregation Query Results:");
            printDataSet(dataSet);
        }

        // Time range query
        try (SessionDataSet dataSet = session.executeQueryStatement(
                "SELECT device_id, temperature, humidity " +
                "FROM sensors " +
                "WHERE time >= now() - 10m " +
                "ORDER BY time DESC")) {
            System.out.println("Time Range Query Results:");
            printDataSet(dataSet);
        }
    }

    public static void tableModelAdvancedExample() {
        try (ITableSession session = new TableSessionBuilder()
                .nodeUrls(Collections.singletonList(LOCAL_URL))
                .username("root")
                .password("root")
                .database("factory")  // Set default database
                .build()) {

            // Show tables
            try (SessionDataSet dataSet = session.executeQueryStatement("SHOW TABLES")) {
                System.out.println("Available Tables:");
                printDataSet(dataSet);
            }

            // Create another table
            session.executeNonQueryStatement(
                "CREATE TABLE events(" +
                "device_id STRING TAG, " +
                "event_type STRING TAG, " +
                "severity STRING ATTRIBUTE, " +
                "message STRING FIELD, " +
                "value DOUBLE FIELD" +
                ") WITH (TTL=86400000)"
            );

            // Complex query with JOIN (if supported)
            try (SessionDataSet dataSet = session.executeQueryStatement(
                    "SELECT s.device_id, s.temperature, s.humidity " +
                    "FROM sensors s " +
                    "WHERE s.temperature > 30.0 " +
                    "ORDER BY s.temperature DESC " +
                    "LIMIT 5")) {
                System.out.println("High Temperature Devices:");
                printDataSet(dataSet);
            }

        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private static void printDataSet(SessionDataSet dataSet)
            throws StatementExecutionException, IoTDBConnectionException {
        System.out.println("Columns: " + dataSet.getColumnNames());
        int count = 0;
        while (dataSet.hasNext() && count < 5) {  // Limit output
            System.out.println(dataSet.next());
            count++;
        }
        System.out.println();
    }
}
```

## Error Handling and Connection Management

```java
public class IoTDBConnectionManager {

    private Session session;
    private final String host;
    private final int port;
    private final String username;
    private final String password;

    public IoTDBConnectionManager(String host, int port, String username, String password) {
        this.host = host;
        this.port = port;
        this.username = username;
        this.password = password;
    }

    public void connect() throws IoTDBConnectionException {
        session = new Session.Builder()
            .host(host)
            .port(port)
            .username(username)
            .password(password)
            .fetchSize(10000)
            .thriftDefaultBufferSize(1024)
            .thriftMaxFrameSize(67108864)
            .enableCompression(false)
            .zoneId(ZoneId.systemDefault())
            .build();

        session.open(false);
    }

    public void disconnect() {
        if (session != null) {
            try {
                session.close();
            } catch (IoTDBConnectionException e) {
                System.err.println("Error closing session: " + e.getMessage());
            }
        }
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

    public Session getSession() {
        return session;
    }
}
```

## Maven Dependencies

```xml
<dependencies>
    <dependency>
        <groupId>org.apache.iotdb</groupId>
        <artifactId>iotdb-session</artifactId>
        <version>2.0.6</version>
    </dependency>
    <dependency>
        <groupId>org.apache.iotdb</groupId>
        <artifactId>iotdb-table-session</artifactId>
        <version>2.0.6</version>
    </dependency>
</dependencies>
```