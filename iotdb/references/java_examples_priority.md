# Java Examples for IoTDB Connection - SessionPool Priority

## Overview

This guide provides comprehensive Java examples for IoTDB connection with **SessionPool as the primary recommendation**. All examples emphasize iterator-based data reading for optimal memory efficiency.

## Connection Priority Order

1. **🚀 SessionPool** - RECOMMENDED for all production applications
2. **🔧 JDBC** - For framework integration (Spring, MyBatis, etc.)
3. **📚 Session** - Only for testing or simple single-threaded applications

## SessionPool Examples (RECOMMENDED)

### Basic SessionPool Setup

```java
import org.apache.iotdb.session.pool.SessionPool;
import org.apache.iotdb.session.SessionDataSet;
import org.apache.iotdb.tsfile.read.common.DataIterator;
import org.apache.iotdb.tsfile.file.metadata.enums.TSDataType;
import org.apache.iotdb.tsfile.file.metadata.enums.TSEncoding;
import org.apache.iotdb.tsfile.file.metadata.enums.CompressionType;

public class IoTDBSessionPoolExample {
    private SessionPool sessionPool;

    public void initializeSessionPool() {
        // RECOMMENDED: SessionPool for production applications
        sessionPool = new SessionPool.Builder()
            .host("127.0.0.1")
            .port(6667)
            .user("root")
            .password("root")
            .maxSize(10)          // Connection pool size
            .build();

        System.out.println("SessionPool initialized successfully");
    }

    public void setupDatabase() throws Exception {
        // Create database
        sessionPool.createDatabase("root.production");

        // Create multiple timeseries
        sessionPool.createTimeseries(
            "root.production.factory1.temperature",
            TSDataType.FLOAT,
            TSEncoding.RLE,
            CompressionType.SNAPPY
        );

        sessionPool.createTimeseries(
            "root.production.factory1.humidity",
            TSDataType.FLOAT,
            TSEncoding.RLE,
            CompressionType.SNAPPY
        );

        sessionPool.createTimeseries(
            "root.production.factory1.pressure",
            TSDataType.FLOAT,
            TSEncoding.RLE,
            CompressionType.SNAPPY
        );

        System.out.println("Database and timeseries created");
    }

    public void closeSessionPool() {
        if (sessionPool != null) {
            sessionPool.close();
            System.out.println("SessionPool closed");
        }
    }
}
```

### Iterator-Based Data Reading (CRITICAL)

```java
public class IoTDBIteratorExamples {

    // ⭐ ALWAYS use iterator pattern for reading data
    public void queryWithIterator(SessionPool sessionPool) throws Exception {
        String sql = "SELECT temperature, humidity, pressure FROM root.production.factory1";

        try (SessionDataSet dataSet = sessionPool.executeQueryStatement(sql)) {
            // Iterator pattern - memory efficient
            DataIterator iterator = dataSet.iterator();

            System.out.println("Reading data with iterator:");
            System.out.println("Timestamp\t\tTemperature\tHumidity\tPressure");
            System.out.println("-".repeat(60));

            while (iterator.next()) {
                long timestamp = iterator.getLong(1);      // Time column
                float temperature = iterator.getFloat(2);   // Temperature
                float humidity = iterator.getFloat(3);      // Humidity
                float pressure = iterator.getFloat(4);      // Pressure

                System.out.printf("%d\t%.2f\t\t%.2f\t\t%.2f%n",
                    timestamp, temperature, humidity, pressure);
            }
        } // Auto-close dataSet
    }

    // Time range query with iterator
    public void timeRangeQuery(SessionPool sessionPool) throws Exception {
        long endTime = System.currentTimeMillis();
        long startTime = endTime - 3600000; // Last hour

        String sql = "SELECT * FROM root.production.factory1 WHERE time >= " + startTime +
                    " AND time <= " + endTime + " ORDER BY time";

        try (SessionDataSet dataSet = sessionPool.executeQueryStatement(sql)) {
            DataIterator iterator = dataSet.iterator();

            int count = 0;
            while (iterator.next() && count < 100) { // Limit for demo
                System.out.println("Time: " + iterator.getLong(1) +
                                 ", Temp: " + iterator.getFloat(2));
                count++;
            }

            System.out.println("Processed " + count + " records");
        }
    }

    // Aggregation query with iterator
    public void aggregationQuery(SessionPool sessionPool) throws Exception {
        String sql = "SELECT AVG(temperature), MAX(temperature), MIN(temperature), COUNT(*) " +
                    "FROM root.production.factory1";

        try (SessionDataSet dataSet = sessionPool.executeQueryStatement(sql)) {
            DataIterator iterator = dataSet.iterator();

            if (iterator.next()) {
                double avgTemp = iterator.getDouble(1);
                float maxTemp = iterator.getFloat(2);
                float minTemp = iterator.getFloat(3);
                long count = iterator.getLong(4);

                System.out.printf("Avg: %.2f, Max: %.2f, Min: %.2f, Count: %d%n",
                    avgTemp, maxTemp, minTemp, count);
            }
        }
    }

    // Large dataset processing with iterator (memory efficient)
    public void processLargeDataset(SessionPool sessionPool) throws Exception {
        String sql = "SELECT * FROM root.production.**";

        try (SessionDataSet dataSet = sessionPool.executeQueryStatement(sql)) {
            DataIterator iterator = dataSet.iterator();

            int batchSize = 1000;
            int processed = 0;
            long startTime = System.currentTimeMillis();

            while (iterator.next()) {
                // Process each record without storing in memory
                processRecord(iterator);
                processed++;

                // Progress reporting
                if (processed % batchSize == 0) {
                    long elapsed = System.currentTimeMillis() - startTime;
                    System.out.println("Processed " + processed + " records in " + elapsed + " ms");
                }
            }

            System.out.println("Total processed: " + processed + " records");
        }
    }

    private void processRecord(DataIterator iterator) throws Exception {
        // Example processing - can be any business logic
        long timestamp = iterator.getLong(1);
        // Process other columns as needed...

        // This is just an example - replace with actual processing logic
        if (timestamp > 0) {
            // Do something with the record
        }
    }
}
```

### Bulk Data Insertion with SessionPool

```java
import org.apache.iotdb.session.util.tablet.Tablet;
import java.util.*;

public class IoTDBBulkInsertionExamples {

    // Single record insertion
    public void insertSingleRecord(SessionPool sessionPool) throws Exception {
        long timestamp = System.currentTimeMillis();

        sessionPool.insertRecord(
            "root.production.factory1",
            timestamp,
            Arrays.asList("temperature", "humidity", "pressure"),
            Arrays.asList(TSDataType.FLOAT, TSDataType.FLOAT, TSDataType.FLOAT),
            Arrays.asList(25.5f, 60.2f, 1013.25f)
        );

        System.out.println("Single record inserted");
    }

    // RECOMMENDED: Tablet-based bulk insertion for high performance
    public void bulkInsertWithTablet(SessionPool sessionPool) throws Exception {
        // Define tablet structure
        List<String> measurements = Arrays.asList("temperature", "humidity", "pressure");
        List<TSDataType> dataTypes = Arrays.asList(TSDataType.FLOAT, TSDataType.FLOAT, TSDataType.FLOAT);

        int batchSize = 1000;
        Tablet tablet = new Tablet("root.production.factory1", measurements, dataTypes, batchSize);

        long baseTime = System.currentTimeMillis();

        // Fill tablet with data
        for (int i = 0; i < batchSize; i++) {
            long timestamp = baseTime + i * 1000; // Every second

            tablet.addTimestamp(i, timestamp);
            tablet.addValue(measurements.get(0), i, 20.0f + (float)Math.random() * 10); // Temperature
            tablet.addValue(measurements.get(1), i, 50.0f + (float)Math.random() * 30); // Humidity
            tablet.addValue(measurements.get(2), i, 1000.0f + (float)Math.random() * 50); // Pressure
        }

        // Insert tablet (high performance)
        sessionPool.insertTablet(tablet);
        System.out.println("Inserted " + batchSize + " records using tablet");
    }

    // Multiple records insertion
    public void insertMultipleRecords(SessionPool sessionPool) throws Exception {
        List<String> deviceIds = Arrays.asList(
            "root.production.factory1",
            "root.production.factory2"
        );

        List<Long> timestamps = new ArrayList<>();
        List<List<String>> measurementsList = new ArrayList<>();
        List<List<TSDataType>> typesList = new ArrayList<>();
        List<List<Object>> valuesList = new ArrayList<>();

        long baseTime = System.currentTimeMillis();

        for (int i = 0; i < 10; i++) {
            timestamps.add(baseTime + i * 60000); // Every minute

            measurementsList.add(Arrays.asList("temperature", "humidity"));
            typesList.add(Arrays.asList(TSDataType.FLOAT, TSDataType.FLOAT));
            valuesList.add(Arrays.asList(
                20.0f + (float)Math.random() * 10,
                50.0f + (float)Math.random() * 30
            ));
        }

        sessionPool.insertRecords(
            deviceIds,
            timestamps,
            measurementsList,
            typesList,
            valuesList
        );

        System.out.println("Inserted multiple records across devices");
    }

    // High-throughput insertion example
    public void highThroughputInsertion(SessionPool sessionPool) throws Exception {
        List<String> measurements = Arrays.asList("value1", "value2", "value3", "value4");
        List<TSDataType> dataTypes = Arrays.asList(
            TSDataType.FLOAT, TSDataType.FLOAT, TSDataType.FLOAT, TSDataType.FLOAT
        );

        int batchSize = 10000;
        int totalBatches = 10;
        long startTime = System.currentTimeMillis();

        for (int batch = 0; batch < totalBatches; batch++) {
            Tablet tablet = new Tablet("root.production.highvolume", measurements, dataTypes, batchSize);

            long batchStartTime = System.currentTimeMillis() + batch * batchSize * 1000;

            // Fill tablet
            for (int i = 0; i < batchSize; i++) {
                tablet.addTimestamp(i, batchStartTime + i * 1000);
                tablet.addValue("value1", i, (float)Math.random() * 100);
                tablet.addValue("value2", i, (float)Math.random() * 100);
                tablet.addValue("value3", i, (float)Math.random() * 100);
                tablet.addValue("value4", i, (float)Math.random() * 100);
            }

            // Insert tablet
            sessionPool.insertTablet(tablet);
            System.out.println("Completed batch " + (batch + 1) + "/" + totalBatches);
        }

        long endTime = System.currentTimeMillis();
        long totalRecords = (long) batchSize * totalBatches;
        double duration = (endTime - startTime) / 1000.0;

        System.out.println("Inserted " + totalRecords + " records in " + duration + " seconds");
        System.out.println("Throughput: " + (totalRecords / duration) + " records/second");
    }
}
```

### Complete Application Example

```java
public class IoTDBProductionApplication {
    private SessionPool sessionPool;

    public static void main(String[] args) {
        IoTDBProductionApplication app = new IoTDBProductionApplication();
        app.run();
    }

    public void run() {
        try {
            // Initialize
            initializeConnection();
            setupSchema();

            // Insert data
            insertSampleData();

            // Query data
            queryRecentData();
            queryAggregatedData();

            // Cleanup
            cleanup();

        } catch (Exception e) {
            System.err.println("Application error: " + e.getMessage());
            e.printStackTrace();
        }
    }

    private void initializeConnection() {
        System.out.println("Initializing SessionPool...");

        sessionPool = new SessionPool.Builder()
            .host("127.0.0.1")
            .port(6667)
            .user("root")
            .password("root")
            .maxSize(20)         // Larger pool for production
            .build();

        System.out.println("SessionPool initialized successfully");
    }

    private void setupSchema() throws Exception {
        System.out.println("Setting up database schema...");

        // Create database
        sessionPool.createDatabase("root.production");

        // Create timeseries for multiple devices
        String[] devices = {"factory1", "factory2", "factory3"};
        String[] sensors = {"temperature", "humidity", "pressure", "vibration"};

        for (String device : devices) {
            for (String sensor : sensors) {
                String timeseriesPath = "root.production." + device + "." + sensor;
                sessionPool.createTimeseries(
                    timeseriesPath,
                    TSDataType.FLOAT,
                    TSEncoding.RLE,
                    CompressionType.SNAPPY
                );
            }
        }

        System.out.println("Schema setup completed");
    }

    private void insertSampleData() throws Exception {
        System.out.println("Inserting sample data...");

        String[] devices = {"factory1", "factory2", "factory3"};
        List<String> measurements = Arrays.asList("temperature", "humidity", "pressure", "vibration");
        List<TSDataType> dataTypes = Arrays.asList(
            TSDataType.FLOAT, TSDataType.FLOAT, TSDataType.FLOAT, TSDataType.FLOAT
        );

        int recordsPerDevice = 1000;
        long baseTime = System.currentTimeMillis() - 3600000; // Start 1 hour ago

        for (String device : devices) {
            Tablet tablet = new Tablet("root.production." + device, measurements, dataTypes, recordsPerDevice);

            for (int i = 0; i < recordsPerDevice; i++) {
                long timestamp = baseTime + i * 60000; // Every minute

                tablet.addTimestamp(i, timestamp);
                tablet.addValue("temperature", i, 20.0f + (float)Math.random() * 15);
                tablet.addValue("humidity", i, 40.0f + (float)Math.random() * 40);
                tablet.addValue("pressure", i, 1000.0f + (float)Math.random() * 50);
                tablet.addValue("vibration", i, (float)Math.random() * 10);
            }

            sessionPool.insertTablet(tablet);
        }

        System.out.println("Sample data insertion completed");
    }

    private void queryRecentData() throws Exception {
        System.out.println("\\nQuerying recent data...");

        long currentTime = System.currentTimeMillis();
        long oneHourAgo = currentTime - 3600000;

        String sql = "SELECT * FROM root.production.factory1 " +
                    "WHERE time >= " + oneHourAgo +
                    " ORDER BY time DESC LIMIT 10";

        try (SessionDataSet dataSet = sessionPool.executeQueryStatement(sql)) {
            DataIterator iterator = dataSet.iterator();

            System.out.println("Recent readings from Factory 1:");
            System.out.println("Time\t\t\tTemp\tHumid\tPress\tVibr");
            System.out.println("-".repeat(60));

            while (iterator.next()) {
                System.out.printf("%d\t%.1f\t%.1f\t%.1f\t%.1f%n",
                    iterator.getLong(1),     // timestamp
                    iterator.getFloat(2),    // temperature
                    iterator.getFloat(3),    // humidity
                    iterator.getFloat(4),    // pressure
                    iterator.getFloat(5));   // vibration
            }
        }
    }

    private void queryAggregatedData() throws Exception {
        System.out.println("\\nQuerying aggregated data...");

        String sql = "SELECT AVG(temperature), MAX(temperature), MIN(temperature), " +
                    "AVG(humidity), COUNT(*) " +
                    "FROM root.production.**";

        try (SessionDataSet dataSet = sessionPool.executeQueryStatement(sql)) {
            DataIterator iterator = dataSet.iterator();

            if (iterator.next()) {
                System.out.println("Aggregated Statistics:");
                System.out.printf("Avg Temperature: %.2f°C%n", iterator.getDouble(1));
                System.out.printf("Max Temperature: %.2f°C%n", iterator.getFloat(2));
                System.out.printf("Min Temperature: %.2f°C%n", iterator.getFloat(3));
                System.out.printf("Avg Humidity: %.2f%%%n", iterator.getDouble(4));
                System.out.printf("Total Records: %d%n", iterator.getLong(5));
            }
        }
    }

    private void cleanup() {
        if (sessionPool != null) {
            sessionPool.close();
            System.out.println("\\nResources cleaned up successfully");
        }
    }
}
```

## Performance Monitoring and Error Handling

```java
public class IoTDBPerformanceMonitoring {

    public void monitorQueryPerformance(SessionPool sessionPool) throws Exception {
        String[] queries = {
            "SELECT * FROM root.production.factory1 LIMIT 1000",
            "SELECT AVG(temperature) FROM root.production.** GROUP BY time(1h)",
            "SELECT * FROM root.production.** WHERE temperature > 25.0 LIMIT 500"
        };

        for (String sql : queries) {
            long startTime = System.currentTimeMillis();
            int recordCount = 0;

            try (SessionDataSet dataSet = sessionPool.executeQueryStatement(sql)) {
                DataIterator iterator = dataSet.iterator();

                while (iterator.next()) {
                    recordCount++;
                }

                long endTime = System.currentTimeMillis();
                double duration = (endTime - startTime) / 1000.0;

                System.out.printf("Query: %s%n", sql);
                System.out.printf("Records: %d, Duration: %.2fs, Rate: %.2f records/s%n%n",
                    recordCount, duration, recordCount / duration);

            } catch (Exception e) {
                System.err.println("Query failed: " + sql);
                System.err.println("Error: " + e.getMessage());
            }
        }
    }

    public void robustQueryWithRetry(SessionPool sessionPool, String sql, int maxRetries) {
        for (int attempt = 1; attempt <= maxRetries; attempt++) {
            try (SessionDataSet dataSet = sessionPool.executeQueryStatement(sql)) {
                DataIterator iterator = dataSet.iterator();

                while (iterator.next()) {
                    // Process data
                }

                System.out.println("Query succeeded on attempt " + attempt);
                return;

            } catch (Exception e) {
                System.err.println("Attempt " + attempt + " failed: " + e.getMessage());

                if (attempt < maxRetries) {
                    try {
                        Thread.sleep(1000 * attempt); // Exponential backoff
                    } catch (InterruptedException ie) {
                        Thread.currentThread().interrupt();
                        break;
                    }
                } else {
                    System.err.println("All attempts failed for query: " + sql);
                }
            }
        }
    }
}
```

## Key Takeaways for Java Development

1. **🚀 Always use SessionPool** - Never use single Session for production applications
2. **⭐ Iterator pattern is mandatory** - Use `DataIterator.next()` for all data reading
3. **📦 Use tablets for bulk insertion** - Much better performance than individual records
4. **🔄 Implement proper resource management** - Always use try-with-resources
5. **📊 Monitor performance** - Track query execution times and throughput
6. **🛡️ Handle errors gracefully** - Implement retry mechanisms with exponential backoff

This approach ensures optimal performance, memory efficiency, and production-ready robustness for IoTDB Java applications.