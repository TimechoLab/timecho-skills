# JDBC Examples for IoTDB Connection

## Overview

IoTDB provides JDBC driver support for standard SQL database connectivity. This allows integration with existing Java applications, BI tools, and frameworks that use JDBC.

## JDBC Driver Setup

### Maven Dependency

```xml
<dependency>
    <groupId>org.apache.iotdb</groupId>
    <artifactId>iotdb-jdbc</artifactId>
    <version>2.0.6</version>
</dependency>
```

### Driver Registration

```java
// Automatic registration (modern JDBC)
// No explicit registration needed

// Manual registration (if needed)
Class.forName("org.apache.iotdb.jdbc.IoTDBDriver");
```

## Basic JDBC Connection

### Connection URL Format

```
jdbc:iotdb://host:port/[database]
```

### Simple Connection Example

```java
import java.sql.*;

public class IoTDBJDBCBasic {
    private static final String JDBC_URL = "jdbc:iotdb://127.0.0.1:6667/";
    private static final String USERNAME = "root";
    private static final String PASSWORD = "root";

    public static void main(String[] args) {
        try (Connection connection = DriverManager.getConnection(JDBC_URL, USERNAME, PASSWORD)) {
            System.out.println("Connected to IoTDB via JDBC");

            // Basic operations
            basicOperations(connection);

        } catch (SQLException e) {
            System.err.println("JDBC Connection failed: " + e.getMessage());
        }
    }

    private static void basicOperations(Connection connection) throws SQLException {
        try (Statement stmt = connection.createStatement()) {
            // Create database
            stmt.execute("CREATE DATABASE root.jdbc_example");

            // Create timeseries
            stmt.execute(
                "CREATE TIMESERIES root.jdbc_example.device1.temperature " +
                "WITH DATATYPE=FLOAT, ENCODING=RLE"
            );

            stmt.execute(
                "CREATE TIMESERIES root.jdbc_example.device1.humidity " +
                "WITH DATATYPE=FLOAT, ENCODING=RLE"
            );

            // Insert data
            stmt.execute(
                "INSERT INTO root.jdbc_example.device1(timestamp, temperature, humidity) " +
                "VALUES(" + System.currentTimeMillis() + ", 25.5, 60.0)"
            );

            System.out.println("Data inserted successfully");
        }
    }
}
```

## Data Insertion with JDBC

### Prepared Statements (Recommended)

```java
public class IoTDBJDBCInsertion {

    public static void insertDataWithPreparedStatement(Connection connection) throws SQLException {
        String sql = "INSERT INTO root.jdbc_example.device1(timestamp, temperature, humidity) VALUES(?, ?, ?)";

        try (PreparedStatement pstmt = connection.prepareStatement(sql)) {
            // Insert multiple records
            long baseTime = System.currentTimeMillis();

            for (int i = 0; i < 100; i++) {
                pstmt.setLong(1, baseTime + i * 1000);
                pstmt.setFloat(2, 20.0f + (float) Math.random() * 10);
                pstmt.setFloat(3, 50.0f + (float) Math.random() * 30);
                pstmt.executeUpdate();
            }

            System.out.println("Inserted 100 records using prepared statements");
        }
    }

    public static void batchInsertion(Connection connection) throws SQLException {
        String sql = "INSERT INTO root.jdbc_example.device2(timestamp, temperature, humidity) VALUES(?, ?, ?)";

        try (PreparedStatement pstmt = connection.prepareStatement(sql)) {
            connection.setAutoCommit(false); // Enable batch mode

            long baseTime = System.currentTimeMillis();

            for (int i = 0; i < 1000; i++) {
                pstmt.setLong(1, baseTime + i * 1000);
                pstmt.setFloat(2, 20.0f + (float) Math.random() * 10);
                pstmt.setFloat(3, 50.0f + (float) Math.random() * 30);
                pstmt.addBatch();

                // Execute batch every 100 records
                if (i % 100 == 0) {
                    pstmt.executeBatch();
                }
            }

            // Execute remaining batch
            pstmt.executeBatch();
            connection.commit();
            connection.setAutoCommit(true);

            System.out.println("Batch insertion completed: 1000 records");
        }
    }
}
```

## Data Querying with JDBC

### Iterator-Based Result Processing

```java
public class IoTDBJDBCQuerying {

    public static void queryWithIterator(Connection connection) throws SQLException {
        String sql = "SELECT timestamp, temperature, humidity FROM root.jdbc_example.device1 " +
                    "WHERE timestamp >= ? ORDER BY timestamp";

        try (PreparedStatement pstmt = connection.prepareStatement(sql)) {
            // Query last hour of data
            pstmt.setLong(1, System.currentTimeMillis() - 3600000);

            try (ResultSet rs = pstmt.executeQuery()) {
                System.out.println("Query Results (Iterator-based):");
                System.out.println("Time\t\t\tTemperature\tHumidity");
                System.out.println("-".repeat(50));

                // Use iterator pattern for memory efficiency
                while (rs.next()) {
                    long timestamp = rs.getLong("timestamp");
                    float temperature = rs.getFloat("temperature");
                    float humidity = rs.getFloat("humidity");

                    System.out.printf("%d\t%.2f\t\t%.2f%n",
                        timestamp, temperature, humidity);
                }
            }
        }
    }

    public static void aggregationQueries(Connection connection) throws SQLException {
        String[] queries = {
            "SELECT AVG(temperature), MAX(temperature), MIN(temperature) FROM root.jdbc_example.device1",
            "SELECT COUNT(*) FROM root.jdbc_example.device1",
            "SELECT temperature, humidity FROM root.jdbc_example.device1 ORDER BY timestamp DESC LIMIT 10"
        };

        for (String sql : queries) {
            System.out.println("\nExecuting: " + sql);
            try (Statement stmt = connection.createStatement();
                 ResultSet rs = stmt.executeQuery(sql)) {

                ResultSetMetaData metaData = rs.getMetaData();
                int columnCount = metaData.getColumnCount();

                // Print column headers
                for (int i = 1; i <= columnCount; i++) {
                    System.out.print(metaData.getColumnName(i) + "\t");
                }
                System.out.println();

                // Print results using iterator
                while (rs.next()) {
                    for (int i = 1; i <= columnCount; i++) {
                        System.out.print(rs.getString(i) + "\t");
                    }
                    System.out.println();
                }
            }
        }
    }

    public static void timeRangeQueries(Connection connection) throws SQLException {
        // Query with time range and conditions
        String sql = """
            SELECT timestamp, temperature, humidity
            FROM root.jdbc_example.device1
            WHERE timestamp >= ? AND timestamp <= ? AND temperature > ?
            ORDER BY timestamp
            """;

        try (PreparedStatement pstmt = connection.prepareStatement(sql)) {
            long endTime = System.currentTimeMillis();
            long startTime = endTime - 3600000; // Last hour

            pstmt.setLong(1, startTime);
            pstmt.setLong(2, endTime);
            pstmt.setFloat(3, 22.0f); // Temperature > 22.0

            try (ResultSet rs = pstmt.executeQuery()) {
                System.out.println("Time Range Query Results:");

                int count = 0;
                while (rs.next() && count < 20) { // Limit output
                    System.out.printf("Time: %d, Temp: %.2f, Humidity: %.2f%n",
                        rs.getLong(1), rs.getFloat(2), rs.getFloat(3));
                    count++;
                }
            }
        }
    }
}
```

## Connection Pool with JDBC

### Using HikariCP

```xml
<!-- Add HikariCP dependency -->
<dependency>
    <groupId>com.zaxxer</groupId>
    <artifactId>HikariCP</artifactId>
    <version>5.0.1</version>
</dependency>
```

```java
import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.HikariDataSource;

public class IoTDBConnectionPool {
    private HikariDataSource dataSource;

    public void setupConnectionPool() {
        HikariConfig config = new HikariConfig();
        config.setJdbcUrl("jdbc:iotdb://127.0.0.1:6667/");
        config.setUsername("root");
        config.setPassword("root");
        config.setDriverClassName("org.apache.iotdb.jdbc.IoTDBDriver");

        // Pool configuration
        config.setMaximumPoolSize(20);
        config.setMinimumIdle(5);
        config.setConnectionTimeout(30000);
        config.setIdleTimeout(600000);
        config.setMaxLifetime(1800000);

        // IoTDB specific settings
        config.addDataSourceProperty("fetchSize", "10000");

        dataSource = new HikariDataSource(config);
    }

    public Connection getConnection() throws SQLException {
        return dataSource.getConnection();
    }

    public void performPooledOperations() {
        try (Connection conn = getConnection()) {
            // Use connection from pool
            queryWithIterator(conn);
        } catch (SQLException e) {
            System.err.println("Pooled operation failed: " + e.getMessage());
        }
    }

    private void queryWithIterator(Connection conn) throws SQLException {
        String sql = "SELECT * FROM root.jdbc_example.device1 LIMIT 100";
        try (Statement stmt = conn.createStatement();
             ResultSet rs = stmt.executeQuery(sql)) {

            while (rs.next()) {
                System.out.println("Timestamp: " + rs.getLong(1) +
                                 ", Values: " + rs.getString(2));
            }
        }
    }

    public void closePool() {
        if (dataSource != null && !dataSource.isClosed()) {
            dataSource.close();
        }
    }
}
```

## Spring JDBC Integration

### Configuration

```java
@Configuration
@EnableTransactionManagement
public class IoTDBConfig {

    @Bean
    @Primary
    public DataSource iotdbDataSource() {
        HikariConfig config = new HikariConfig();
        config.setJdbcUrl("jdbc:iotdb://127.0.0.1:6667/");
        config.setUsername("root");
        config.setPassword("root");
        config.setMaximumPoolSize(10);
        return new HikariDataSource(config);
    }

    @Bean
    public JdbcTemplate jdbcTemplate(DataSource dataSource) {
        return new JdbcTemplate(dataSource);
    }
}
```

### Service Layer

```java
@Service
public class IoTDBService {

    @Autowired
    private JdbcTemplate jdbcTemplate;

    public void insertSensorData(String device, long timestamp, float temperature, float humidity) {
        String sql = "INSERT INTO " + device + "(timestamp, temperature, humidity) VALUES(?, ?, ?)";
        jdbcTemplate.update(sql, timestamp, temperature, humidity);
    }

    public List<SensorReading> getRecentReadings(String device, int limit) {
        String sql = "SELECT timestamp, temperature, humidity FROM " + device +
                    " ORDER BY timestamp DESC LIMIT ?";

        return jdbcTemplate.query(sql, new Object[]{limit}, (rs, rowNum) -> {
            SensorReading reading = new SensorReading();
            reading.setTimestamp(rs.getLong("timestamp"));
            reading.setTemperature(rs.getFloat("temperature"));
            reading.setHumidity(rs.getFloat("humidity"));
            return reading;
        });
    }

    public List<Map<String, Object>> executeCustomQuery(String sql) {
        return jdbcTemplate.queryForList(sql);
    }

    // Iterator-based processing for large result sets
    public void processLargeDataset(String device, Consumer<SensorReading> processor) {
        String sql = "SELECT timestamp, temperature, humidity FROM " + device + " ORDER BY timestamp";

        jdbcTemplate.query(sql, rs -> {
            SensorReading reading = new SensorReading();
            reading.setTimestamp(rs.getLong("timestamp"));
            reading.setTemperature(rs.getFloat("temperature"));
            reading.setHumidity(rs.getFloat("humidity"));
            processor.accept(reading);
        });
    }
}

// Data class
public class SensorReading {
    private long timestamp;
    private float temperature;
    private float humidity;

    // getters and setters
    public long getTimestamp() { return timestamp; }
    public void setTimestamp(long timestamp) { this.timestamp = timestamp; }
    public float getTemperature() { return temperature; }
    public void setTemperature(float temperature) { this.temperature = temperature; }
    public float getHumidity() { return humidity; }
    public void setHumidity(float humidity) { this.humidity = humidity; }
}
```

## Error Handling and Best Practices

### Robust Error Handling

```java
public class IoTDBJDBCErrorHandling {

    public static void robustQueryExecution(Connection connection) {
        String sql = "SELECT * FROM root.jdbc_example.device1 WHERE timestamp >= ?";

        try (PreparedStatement pstmt = connection.prepareStatement(sql)) {
            pstmt.setLong(1, System.currentTimeMillis() - 3600000);

            try (ResultSet rs = pstmt.executeQuery()) {
                processResultSetSafely(rs);
            }

        } catch (SQLException e) {
            handleSQLException(e);
        }
    }

    private static void processResultSetSafely(ResultSet rs) throws SQLException {
        ResultSetMetaData metaData = rs.getMetaData();
        int columnCount = metaData.getColumnCount();

        while (rs.next()) {
            try {
                for (int i = 1; i <= columnCount; i++) {
                    String columnName = metaData.getColumnName(i);
                    Object value = rs.getObject(i);

                    if (!rs.wasNull()) {
                        System.out.println(columnName + ": " + value);
                    }
                }
            } catch (SQLException e) {
                System.err.println("Error processing row: " + e.getMessage());
                // Continue processing other rows
            }
        }
    }

    private static void handleSQLException(SQLException e) {
        System.err.println("SQL Error occurred:");
        System.err.println("Error Code: " + e.getErrorCode());
        System.err.println("SQL State: " + e.getSQLState());
        System.err.println("Message: " + e.getMessage());

        // Log the full stack trace for debugging
        e.printStackTrace();
    }

    public static void connectionRetry() {
        String jdbcUrl = "jdbc:iotdb://127.0.0.1:6667/";
        String username = "root";
        String password = "root";

        int maxRetries = 3;
        int retryDelay = 1000; // 1 second

        for (int attempt = 1; attempt <= maxRetries; attempt++) {
            try (Connection conn = DriverManager.getConnection(jdbcUrl, username, password)) {
                System.out.println("Connected successfully on attempt " + attempt);
                // Perform operations
                return;

            } catch (SQLException e) {
                System.err.println("Connection attempt " + attempt + " failed: " + e.getMessage());

                if (attempt < maxRetries) {
                    try {
                        Thread.sleep(retryDelay * attempt); // Exponential backoff
                    } catch (InterruptedException ie) {
                        Thread.currentThread().interrupt();
                        break;
                    }
                } else {
                    System.err.println("All connection attempts failed");
                }
            }
        }
    }
}
```

## Performance Optimization

### Batch Operations

```java
public class IoTDBJDBCPerformance {

    public static void optimizedBatchInsertion(Connection connection) throws SQLException {
        String sql = "INSERT INTO root.performance.device1(timestamp, value1, value2, value3) VALUES(?, ?, ?, ?)";

        connection.setAutoCommit(false);

        try (PreparedStatement pstmt = connection.prepareStatement(sql)) {
            long startTime = System.currentTimeMillis();
            int batchSize = 1000;
            int totalRecords = 100000;

            for (int i = 0; i < totalRecords; i++) {
                pstmt.setLong(1, System.currentTimeMillis() + i);
                pstmt.setFloat(2, (float) Math.random() * 100);
                pstmt.setFloat(3, (float) Math.random() * 100);
                pstmt.setFloat(4, (float) Math.random() * 100);
                pstmt.addBatch();

                if (i % batchSize == 0 || i == totalRecords - 1) {
                    pstmt.executeBatch();
                    connection.commit();
                    System.out.println("Processed " + (i + 1) + " records");
                }
            }

            long endTime = System.currentTimeMillis();
            double duration = (endTime - startTime) / 1000.0;
            System.out.println("Inserted " + totalRecords + " records in " + duration + " seconds");
            System.out.println("Throughput: " + (totalRecords / duration) + " records/second");

        } finally {
            connection.setAutoCommit(true);
        }
    }

    public static void optimizedQuerying(Connection connection) throws SQLException {
        String sql = "SELECT timestamp, value1, value2, value3 FROM root.performance.device1 " +
                    "WHERE timestamp >= ? ORDER BY timestamp";

        try (PreparedStatement pstmt = connection.prepareStatement(sql)) {
            // Set fetch size for better performance
            pstmt.setFetchSize(10000);

            pstmt.setLong(1, System.currentTimeMillis() - 3600000);

            long startTime = System.currentTimeMillis();
            int recordCount = 0;

            try (ResultSet rs = pstmt.executeQuery()) {
                while (rs.next()) {
                    // Process each record
                    recordCount++;

                    // Optional: limit processing for demo
                    if (recordCount % 10000 == 0) {
                        System.out.println("Processed " + recordCount + " records");
                    }
                }
            }

            long endTime = System.currentTimeMillis();
            double duration = (endTime - startTime) / 1000.0;
            System.out.println("Queried " + recordCount + " records in " + duration + " seconds");
        }
    }
}
```

## Integration Examples

### MyBatis Integration

```xml
<!-- MyBatis configuration -->
<configuration>
    <environments default="development">
        <environment id="development">
            <transactionManager type="JDBC"/>
            <dataSource type="POOLED">
                <property name="driver" value="org.apache.iotdb.jdbc.IoTDBDriver"/>
                <property name="url" value="jdbc:iotdb://127.0.0.1:6667/"/>
                <property name="username" value="root"/>
                <property name="password" value="root"/>
            </dataSource>
        </environment>
    </environments>
</configuration>
```

### JPA Integration (Limited Support)

```java
// Note: IoTDB has limited JPA support due to its time-series nature
// Use JDBC for full functionality

@Entity
@Table(name = "root.jpa_example.sensor_data")
public class SensorData {
    @Id
    private Long timestamp;
    private Float temperature;
    private Float humidity;

    // getters and setters
}
```

## Complete Example Application

```java
public class IoTDBJDBCApplication {
    private static final String JDBC_URL = "jdbc:iotdb://127.0.0.1:6667/";
    private static final String USERNAME = "root";
    private static final String PASSWORD = "root";

    public static void main(String[] args) {
        IoTDBJDBCApplication app = new IoTDBJDBCApplication();
        app.run();
    }

    public void run() {
        try (Connection connection = DriverManager.getConnection(JDBC_URL, USERNAME, PASSWORD)) {
            // Setup
            setupDatabase(connection);

            // Insert test data
            insertTestData(connection);

            // Query and display results
            queryAndDisplay(connection);

        } catch (SQLException e) {
            System.err.println("Application error: " + e.getMessage());
        }
    }

    private void setupDatabase(Connection connection) throws SQLException {
        try (Statement stmt = connection.createStatement()) {
            stmt.execute("CREATE DATABASE root.application");
            stmt.execute("CREATE TIMESERIES root.application.sensor1.temperature WITH DATATYPE=FLOAT, ENCODING=RLE");
            stmt.execute("CREATE TIMESERIES root.application.sensor1.humidity WITH DATATYPE=FLOAT, ENCODING=RLE");
            System.out.println("Database setup completed");
        }
    }

    private void insertTestData(Connection connection) throws SQLException {
        String sql = "INSERT INTO root.application.sensor1(timestamp, temperature, humidity) VALUES(?, ?, ?)";

        try (PreparedStatement pstmt = connection.prepareStatement(sql)) {
            long baseTime = System.currentTimeMillis();

            for (int i = 0; i < 100; i++) {
                pstmt.setLong(1, baseTime + i * 60000); // Every minute
                pstmt.setFloat(2, 20.0f + (float) Math.random() * 10);
                pstmt.setFloat(3, 50.0f + (float) Math.random() * 30);
                pstmt.executeUpdate();
            }

            System.out.println("Inserted 100 test records");
        }
    }

    private void queryAndDisplay(Connection connection) throws SQLException {
        String sql = "SELECT timestamp, temperature, humidity FROM root.application.sensor1 ORDER BY timestamp DESC LIMIT 10";

        try (Statement stmt = connection.createStatement();
             ResultSet rs = stmt.executeQuery(sql)) {

            System.out.println("\nLatest 10 readings:");
            System.out.println("Timestamp\t\t\tTemperature\tHumidity");
            System.out.println("-".repeat(60));

            while (rs.next()) {
                System.out.printf("%d\t%.2f\t\t%.2f%n",
                    rs.getLong("timestamp"),
                    rs.getFloat("temperature"),
                    rs.getFloat("humidity"));
            }
        }
    }
}
```