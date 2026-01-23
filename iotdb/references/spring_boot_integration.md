# Spring Boot Integration with IoTDB

## Overview

This guide provides comprehensive Spring Boot integration examples for IoTDB, based on the official Apache IoTDB Spring Boot Starter from the iotdb-extras repository. The starter provides auto-configuration and SessionPool management for production applications.

## Table of Contents

- [Dependencies and Configuration](#dependencies-and-configuration)
- [Spring Boot Starter Setup](#spring-boot-starter-setup)
- [SessionPool Auto-Configuration](#sessionpool-auto-configuration)
- [Service Layer Implementation](#service-layer-implementation)
- [Controller Examples](#controller-examples)
- [Configuration Properties](#configuration-properties)
- [Testing Integration](#testing-integration)
- [Error Handling](#error-handling)
- [Performance Considerations](#performance-considerations)

## Dependencies and Configuration

### Maven Dependencies

```xml
<dependencies>
    <!-- Spring Boot Starter Web -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>

    <!-- IoTDB Spring Boot Starter (Official) -->
    <dependency>
        <groupId>org.apache.iotdb</groupId>
        <artifactId>iotdb-spring-boot-starter</artifactId>
        <version>2.0.6</version>
    </dependency>

    <!-- IoTDB Session Client -->
    <dependency>
        <groupId>org.apache.iotdb</groupId>
        <artifactId>iotdb-session</artifactId>
        <version>2.0.6</version>
    </dependency>

    <!-- Optional: For validation -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-validation</artifactId>
    </dependency>
</dependencies>
```

### Gradle Dependencies

```gradle
dependencies {
    implementation 'org.springframework.boot:spring-boot-starter-web'
    implementation 'org.apache.iotdb:iotdb-spring-boot-starter:2.0.6'
    implementation 'org.apache.iotdb:iotdb-session:2.0.6'
    implementation 'org.springframework.boot:spring-boot-starter-validation'
}
```

## Spring Boot Starter Setup

### Application Properties Configuration

```yaml
# application.yml
spring:
  iotdb:
    # Basic connection settings
    host: 127.0.0.1
    port: 6667
    username: root
    password: root

    # SessionPool configuration (RECOMMENDED for production)
    session-pool:
      enabled: true
      max-size: 20              # Maximum connections in pool
      min-size: 5               # Minimum connections to maintain
      max-wait-time-ms: 30000   # Connection timeout

    # Connection settings
    connection:
      timeout-ms: 20000         # Connection timeout
      fetch-size: 10000         # Default fetch size for queries

    # Optional: Enable metrics
    metrics:
      enabled: true

    # Optional: SSL configuration
    ssl:
      enabled: false
      trust-store-path: /path/to/truststore
      trust-store-password: password
```

### Properties File Configuration

```properties
# application.properties
spring.iotdb.host=127.0.0.1
spring.iotdb.port=6667
spring.iotdb.username=root
spring.iotdb.password=root

# SessionPool settings
spring.iotdb.session-pool.enabled=true
spring.iotdb.session-pool.max-size=20
spring.iotdb.session-pool.min-size=5
spring.iotdb.session-pool.max-wait-time-ms=30000

# Connection settings
spring.iotdb.connection.timeout-ms=20000
spring.iotdb.connection.fetch-size=10000
```

## SessionPool Auto-Configuration

The Spring Boot starter automatically configures a SessionPool bean:

### Auto-Configuration Class (Reference)

```java
@Configuration
@EnableConfigurationProperties(IoTDBProperties.class)
@ConditionalOnClass(SessionPool.class)
public class IoTDBAutoConfiguration {

    @Bean
    @ConditionalOnMissingBean
    public SessionPool sessionPool(IoTDBProperties properties) {
        return new SessionPool.Builder()
            .host(properties.getHost())
            .port(properties.getPort())
            .user(properties.getUsername())
            .password(properties.getPassword())
            .maxSize(properties.getSessionPool().getMaxSize())
            .build();
    }
}
```

### Configuration Properties Class

```java
@ConfigurationProperties(prefix = "spring.iotdb")
@Data
public class IoTDBProperties {
    private String host = "127.0.0.1";
    private int port = 6667;
    private String username = "root";
    private String password = "root";

    private SessionPoolProperties sessionPool = new SessionPoolProperties();
    private ConnectionProperties connection = new ConnectionProperties();

    @Data
    public static class SessionPoolProperties {
        private boolean enabled = true;
        private int maxSize = 10;
        private int minSize = 3;
        private long maxWaitTimeMs = 30000;
    }

    @Data
    public static class ConnectionProperties {
        private long timeoutMs = 20000;
        private int fetchSize = 10000;
    }
}
```

## Service Layer Implementation

### IoTDB Service with Iterator Patterns

```java
@Service
@Slf4j
public class IoTDBService {

    @Autowired
    private SessionPool sessionPool;

    /**
     * Initialize database and timeseries
     */
    @PostConstruct
    public void initializeSchema() {
        try {
            // Create database
            sessionPool.createDatabase("root.springboot");

            // Create timeseries for sensors
            sessionPool.createTimeseries(
                "root.springboot.sensors.temperature",
                TSDataType.FLOAT,
                TSEncoding.RLE,
                CompressionType.SNAPPY
            );

            sessionPool.createTimeseries(
                "root.springboot.sensors.humidity",
                TSDataType.FLOAT,
                TSEncoding.RLE,
                CompressionType.SNAPPY
            );

            log.info("IoTDB schema initialized successfully");

        } catch (Exception e) {
            log.error("Failed to initialize IoTDB schema", e);
        }
    }

    /**
     * Insert sensor reading
     */
    public void insertSensorReading(SensorReading reading) {
        try {
            sessionPool.insertRecord(
                "root.springboot.sensors",
                reading.getTimestamp(),
                Arrays.asList("temperature", "humidity"),
                Arrays.asList(TSDataType.FLOAT, TSDataType.FLOAT),
                Arrays.asList(reading.getTemperature(), reading.getHumidity())
            );

            log.debug("Inserted sensor reading: {}", reading);

        } catch (Exception e) {
            log.error("Failed to insert sensor reading", e);
            throw new IoTDBOperationException("Insert failed", e);
        }
    }

    /**
     * Bulk insert using tablet (high performance)
     */
    public void insertSensorReadings(List<SensorReading> readings) {
        if (readings.isEmpty()) return;

        try {
            List<String> measurements = Arrays.asList("temperature", "humidity");
            List<TSDataType> dataTypes = Arrays.asList(TSDataType.FLOAT, TSDataType.FLOAT);

            Tablet tablet = new Tablet("root.springboot.sensors", measurements, dataTypes, readings.size());

            for (int i = 0; i < readings.size(); i++) {
                SensorReading reading = readings.get(i);
                tablet.addTimestamp(i, reading.getTimestamp());
                tablet.addValue("temperature", i, reading.getTemperature());
                tablet.addValue("humidity", i, reading.getHumidity());
            }

            sessionPool.insertTablet(tablet);
            log.info("Bulk inserted {} sensor readings", readings.size());

        } catch (Exception e) {
            log.error("Failed to bulk insert sensor readings", e);
            throw new IoTDBOperationException("Bulk insert failed", e);
        }
    }

    /**
     * Query recent sensor readings with iterator (memory efficient)
     */
    public List<SensorReading> getRecentReadings(int limit) {
        List<SensorReading> readings = new ArrayList<>();

        String sql = "SELECT timestamp, temperature, humidity FROM root.springboot.sensors " +
                    "ORDER BY timestamp DESC LIMIT " + limit;

        try (SessionDataSet dataSet = sessionPool.executeQueryStatement(sql)) {
            // ⭐ CRITICAL: Always use iterator for memory efficiency
            DataIterator iterator = dataSet.iterator();

            while (iterator.next()) {
                long timestamp = iterator.getLong(1);
                float temperature = iterator.getFloat(2);
                float humidity = iterator.getFloat(3);

                readings.add(new SensorReading(timestamp, temperature, humidity));
            }

            log.debug("Retrieved {} recent readings", readings.size());
            return readings;

        } catch (Exception e) {
            log.error("Failed to query recent readings", e);
            throw new IoTDBOperationException("Query failed", e);
        }
    }

    /**
     * Query readings by time range with iterator
     */
    public List<SensorReading> getReadingsByTimeRange(long startTime, long endTime) {
        List<SensorReading> readings = new ArrayList<>();

        String sql = "SELECT timestamp, temperature, humidity FROM root.springboot.sensors " +
                    "WHERE timestamp >= " + startTime + " AND timestamp <= " + endTime +
                    " ORDER BY timestamp";

        try (SessionDataSet dataSet = sessionPool.executeQueryStatement(sql)) {
            DataIterator iterator = dataSet.iterator();

            while (iterator.next()) {
                long timestamp = iterator.getLong(1);
                float temperature = iterator.getFloat(2);
                float humidity = iterator.getFloat(3);

                readings.add(new SensorReading(timestamp, temperature, humidity));
            }

            return readings;

        } catch (Exception e) {
            log.error("Failed to query readings by time range", e);
            throw new IoTDBOperationException("Time range query failed", e);
        }
    }

    /**
     * Get aggregated statistics
     */
    public SensorStatistics getStatistics() {
        String sql = "SELECT AVG(temperature), MAX(temperature), MIN(temperature), " +
                    "AVG(humidity), COUNT(*) FROM root.springboot.sensors";

        try (SessionDataSet dataSet = sessionPool.executeQueryStatement(sql)) {
            DataIterator iterator = dataSet.iterator();

            if (iterator.next()) {
                double avgTemperature = iterator.getDouble(1);
                float maxTemperature = iterator.getFloat(2);
                float minTemperature = iterator.getFloat(3);
                double avgHumidity = iterator.getDouble(4);
                long count = iterator.getLong(5);

                return new SensorStatistics(avgTemperature, maxTemperature, minTemperature, avgHumidity, count);
            }

            return new SensorStatistics();

        } catch (Exception e) {
            log.error("Failed to get statistics", e);
            throw new IoTDBOperationException("Statistics query failed", e);
        }
    }
}
```

### Data Transfer Objects

```java
@Data
@AllArgsConstructor
@NoArgsConstructor
public class SensorReading {
    private long timestamp;
    private float temperature;
    private float humidity;

    public SensorReading(float temperature, float humidity) {
        this.timestamp = System.currentTimeMillis();
        this.temperature = temperature;
        this.humidity = humidity;
    }
}

@Data
@AllArgsConstructor
@NoArgsConstructor
public class SensorStatistics {
    private double avgTemperature;
    private float maxTemperature;
    private float minTemperature;
    private double avgHumidity;
    private long totalCount;
}
```

## Controller Examples

### REST Controller with Validation

```java
@RestController
@RequestMapping("/api/sensors")
@Slf4j
@Validated
public class SensorController {

    @Autowired
    private IoTDBService iotdbService;

    /**
     * Add single sensor reading
     */
    @PostMapping("/readings")
    public ResponseEntity<String> addReading(@Valid @RequestBody SensorReading reading) {
        try {
            iotdbService.insertSensorReading(reading);
            return ResponseEntity.ok("Reading added successfully");
        } catch (IoTDBOperationException e) {
            log.error("Failed to add reading", e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body("Failed to add reading: " + e.getMessage());
        }
    }

    /**
     * Bulk add sensor readings
     */
    @PostMapping("/readings/bulk")
    public ResponseEntity<String> addReadings(@Valid @RequestBody List<SensorReading> readings) {
        try {
            iotdbService.insertSensorReadings(readings);
            return ResponseEntity.ok(readings.size() + " readings added successfully");
        } catch (IoTDBOperationException e) {
            log.error("Failed to add bulk readings", e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body("Failed to add bulk readings: " + e.getMessage());
        }
    }

    /**
     * Get recent readings
     */
    @GetMapping("/readings/recent")
    public ResponseEntity<List<SensorReading>> getRecentReadings(
            @RequestParam(defaultValue = "100") @Min(1) @Max(1000) int limit) {
        try {
            List<SensorReading> readings = iotdbService.getRecentReadings(limit);
            return ResponseEntity.ok(readings);
        } catch (IoTDBOperationException e) {
            log.error("Failed to get recent readings", e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).build();
        }
    }

    /**
     * Get readings by time range
     */
    @GetMapping("/readings/range")
    public ResponseEntity<List<SensorReading>> getReadingsByTimeRange(
            @RequestParam long startTime,
            @RequestParam long endTime) {

        if (startTime >= endTime) {
            return ResponseEntity.badRequest().build();
        }

        try {
            List<SensorReading> readings = iotdbService.getReadingsByTimeRange(startTime, endTime);
            return ResponseEntity.ok(readings);
        } catch (IoTDBOperationException e) {
            log.error("Failed to get readings by time range", e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).build();
        }
    }

    /**
     * Get sensor statistics
     */
    @GetMapping("/statistics")
    public ResponseEntity<SensorStatistics> getStatistics() {
        try {
            SensorStatistics stats = iotdbService.getStatistics();
            return ResponseEntity.ok(stats);
        } catch (IoTDBOperationException e) {
            log.error("Failed to get statistics", e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).build();
        }
    }
}
```

## Configuration Properties

### Complete Configuration Reference

```java
@ConfigurationProperties(prefix = "spring.iotdb")
@Data
public class IoTDBProperties {

    /**
     * IoTDB server host
     */
    private String host = "127.0.0.1";

    /**
     * IoTDB server port
     */
    private int port = 6667;

    /**
     * Username for authentication
     */
    private String username = "root";

    /**
     * Password for authentication
     */
    private String password = "root";

    /**
     * SessionPool configuration
     */
    private SessionPoolProperties sessionPool = new SessionPoolProperties();

    /**
     * Connection properties
     */
    private ConnectionProperties connection = new ConnectionProperties();

    /**
     * SSL configuration
     */
    private SslProperties ssl = new SslProperties();

    /**
     * Metrics configuration
     */
    private MetricsProperties metrics = new MetricsProperties();

    @Data
    public static class SessionPoolProperties {
        /**
         * Enable SessionPool (recommended for production)
         */
        private boolean enabled = true;

        /**
         * Maximum number of sessions in pool
         */
        private int maxSize = 10;

        /**
         * Minimum number of sessions to maintain
         */
        private int minSize = 3;

        /**
         * Maximum wait time for getting session from pool (ms)
         */
        private long maxWaitTimeMs = 30000;

        /**
         * Session timeout (ms)
         */
        private long sessionTimeoutMs = 60000;
    }

    @Data
    public static class ConnectionProperties {
        /**
         * Connection timeout (ms)
         */
        private long timeoutMs = 20000;

        /**
         * Default fetch size for queries
         */
        private int fetchSize = 10000;

        /**
         * Enable connection compression
         */
        private boolean compressionEnabled = false;

        /**
         * Connection retry attempts
         */
        private int retryAttempts = 3;
    }

    @Data
    public static class SslProperties {
        /**
         * Enable SSL connection
         */
        private boolean enabled = false;

        /**
         * Path to trust store
         */
        private String trustStorePath;

        /**
         * Trust store password
         */
        private String trustStorePassword;
    }

    @Data
    public static class MetricsProperties {
        /**
         * Enable connection metrics
         */
        private boolean enabled = false;

        /**
         * Metrics collection interval (ms)
         */
        private long intervalMs = 30000;
    }
}
```

## Testing Integration

### Integration Test Example

```java
@SpringBootTest
@TestPropertySource(properties = {
    "spring.iotdb.host=127.0.0.1",
    "spring.iotdb.port=6667",
    "spring.iotdb.session-pool.max-size=5"
})
class IoTDBIntegrationTest {

    @Autowired
    private IoTDBService iotdbService;

    @Autowired
    private SessionPool sessionPool;

    @Test
    void testSessionPoolAutoConfiguration() {
        assertThat(sessionPool).isNotNull();
    }

    @Test
    void testInsertAndQuerySensorReading() {
        // Given
        SensorReading reading = new SensorReading(25.5f, 60.0f);

        // When
        iotdbService.insertSensorReading(reading);
        List<SensorReading> readings = iotdbService.getRecentReadings(1);

        // Then
        assertThat(readings).hasSize(1);
        assertThat(readings.get(0).getTemperature()).isEqualTo(25.5f);
        assertThat(readings.get(0).getHumidity()).isEqualTo(60.0f);
    }

    @Test
    void testBulkInsertAndStatistics() {
        // Given
        List<SensorReading> readings = IntStream.range(0, 100)
            .mapToObj(i -> new SensorReading(20.0f + i * 0.1f, 50.0f + i * 0.2f))
            .collect(Collectors.toList());

        // When
        iotdbService.insertSensorReadings(readings);
        SensorStatistics stats = iotdbService.getStatistics();

        // Then
        assertThat(stats.getTotalCount()).isGreaterThanOrEqualTo(100);
        assertThat(stats.getAvgTemperature()).isGreaterThan(20.0);
    }
}
```

### Test Configuration

```java
@TestConfiguration
public class IoTDBTestConfig {

    @Bean
    @Primary
    public SessionPool testSessionPool() {
        return new SessionPool.Builder()
            .host("127.0.0.1")
            .port(6667)
            .user("root")
            .password("root")
            .maxSize(3)  // Smaller pool for tests
            .build();
    }
}
```

## Error Handling

### Custom Exception Classes

```java
@ResponseStatus(HttpStatus.INTERNAL_SERVER_ERROR)
public class IoTDBOperationException extends RuntimeException {
    public IoTDBOperationException(String message) {
        super(message);
    }

    public IoTDBOperationException(String message, Throwable cause) {
        super(message, cause);
    }
}

@ControllerAdvice
public class IoTDBExceptionHandler {

    @ExceptionHandler(IoTDBOperationException.class)
    public ResponseEntity<ErrorResponse> handleIoTDBOperation(IoTDBOperationException e) {
        ErrorResponse error = new ErrorResponse("IOTDB_OPERATION_ERROR", e.getMessage());
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(error);
    }

    @ExceptionHandler(ValidationException.class)
    public ResponseEntity<ErrorResponse> handleValidation(ValidationException e) {
        ErrorResponse error = new ErrorResponse("VALIDATION_ERROR", e.getMessage());
        return ResponseEntity.badRequest().body(error);
    }
}

@Data
@AllArgsConstructor
public class ErrorResponse {
    private String code;
    private String message;
}
```

## Performance Considerations

### Connection Pool Monitoring

```java
@Component
@Slf4j
public class SessionPoolMonitor {

    @Autowired
    private SessionPool sessionPool;

    @Scheduled(fixedRate = 30000) // Every 30 seconds
    public void logPoolStatus() {
        // Note: Actual SessionPool doesn't expose these metrics directly
        // This is a conceptual example
        log.info("SessionPool status - Active connections: estimated based on usage patterns");
    }

    @EventListener
    public void handleApplicationReady(ApplicationReadyEvent event) {
        log.info("IoTDB SessionPool initialized and ready");
    }
}
```

### Best Practices Summary

1. **Always use SessionPool** - Configured automatically by the Spring Boot starter
2. **Iterator-based reading** - Implement in all query methods for memory efficiency
3. **Bulk operations** - Use tablets for high-throughput insertions
4. **Connection monitoring** - Implement health checks and monitoring
5. **Error handling** - Use proper exception handling and retry mechanisms
6. **Resource management** - Let Spring manage SessionPool lifecycle
7. **Configuration** - Use external configuration for different environments

This Spring Boot integration provides a production-ready foundation for IoTDB applications with proper resource management, error handling, and performance optimization.