# MyBatis Integration with IoTDB

## Overview

This guide provides comprehensive MyBatis integration examples for IoTDB, based on the official Apache IoTDB MyBatis Generator from the iotdb-extras repository. MyBatis provides powerful SQL mapping capabilities for JDBC-based IoTDB applications.

## Table of Contents

- [Dependencies and Setup](#dependencies-and-setup)
- [MyBatis Generator Configuration](#mybatis-generator-configuration)
- [Mapper Interface Examples](#mapper-interface-examples)
- [XML Mapper Files](#xml-mapper-files)
- [Spring Boot Integration](#spring-boot-integration)
- [Connection Pool Configuration](#connection-pool-configuration)
- [Service Layer Implementation](#service-layer-implementation)
- [Transaction Management](#transaction-management)
- [Performance Optimization](#performance-optimization)

## Dependencies and Setup

### Maven Dependencies

```xml
<dependencies>
    <!-- Spring Boot Starter -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>

    <!-- MyBatis Spring Boot Starter -->
    <dependency>
        <groupId>org.mybatis.spring.boot</groupId>
        <artifactId>mybatis-spring-boot-starter</artifactId>
        <version>3.0.3</version>
    </dependency>

    <!-- IoTDB JDBC Driver -->
    <dependency>
        <groupId>org.apache.iotdb</groupId>
        <artifactId>iotdb-jdbc</artifactId>
        <version>2.0.6</version>
    </dependency>

    <!-- HikariCP (Connection Pool) -->
    <dependency>
        <groupId>com.zaxxer</groupId>
        <artifactId>HikariCP</artifactId>
    </dependency>

    <!-- MyBatis Generator (for development) -->
    <dependency>
        <groupId>org.mybatis.generator</groupId>
        <artifactId>mybatis-generator-core</artifactId>
        <version>1.4.2</version>
        <scope>provided</scope>
    </dependency>
</dependencies>

<build>
    <plugins>
        <!-- MyBatis Generator Plugin -->
        <plugin>
            <groupId>org.mybatis.generator</groupId>
            <artifactId>mybatis-generator-maven-plugin</artifactId>
            <version>1.4.2</version>
            <configuration>
                <configurationFile>src/main/resources/mybatis-generator-config.xml</configurationFile>
                <overwrite>true</overwrite>
            </configuration>
            <dependencies>
                <dependency>
                    <groupId>org.apache.iotdb</groupId>
                    <artifactId>iotdb-jdbc</artifactId>
                    <version>2.0.6</version>
                </dependency>
            </dependencies>
        </plugin>
    </plugins>
</build>
```

### Gradle Dependencies

```gradle
dependencies {
    implementation 'org.springframework.boot:spring-boot-starter-web'
    implementation 'org.mybatis.spring.boot:mybatis-spring-boot-starter:3.0.3'
    implementation 'org.apache.iotdb:iotdb-jdbc:2.0.6'
    implementation 'com.zaxxer:HikariCP'

    // MyBatis Generator (for development)
    compileOnly 'org.mybatis.generator:mybatis-generator-core:1.4.2'
}
```

## MyBatis Generator Configuration

### Generator Configuration File

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE generatorConfiguration
    PUBLIC "-//mybatis.org//DTD MyBatis Generator Configuration 1.0//EN"
    "http://mybatis.org/dtd/mybatis-generator-config_1_0.dtd">

<generatorConfiguration>
    <context id="IoTDBTables" targetRuntime="MyBatis3">

        <!-- IoTDB-specific plugin for timeseries handling -->
        <plugin type="org.apache.iotdb.mybatis.plugins.IoTDBTimeseriesPlugin"/>

        <!-- Connection to IoTDB -->
        <jdbcConnection driverClass="org.apache.iotdb.jdbc.IoTDBDriver"
                        connectionURL="jdbc:iotdb://127.0.0.1:6667/"
                        userId="root"
                        password="root">
            <property name="fetchSize" value="10000"/>
        </jdbcConnection>

        <!-- Java type resolver for IoTDB data types -->
        <javaTypeResolver>
            <property name="forceBigDecimals" value="false"/>
            <property name="useJSR310Types" value="true"/>
        </javaTypeResolver>

        <!-- Model generation -->
        <javaModelGenerator targetPackage="com.example.iotdb.model"
                           targetProject="src/main/java">
            <property name="enableSubPackages" value="true"/>
            <property name="trimStrings" value="true"/>
        </javaModelGenerator>

        <!-- SQL Map files generation -->
        <sqlMapGenerator targetPackage="mapper"
                        targetProject="src/main/resources">
            <property name="enableSubPackages" value="true"/>
        </sqlMapGenerator>

        <!-- Mapper interface generation -->
        <javaClientGenerator type="XMLMAPPER"
                           targetPackage="com.example.iotdb.mapper"
                           targetProject="src/main/java">
            <property name="enableSubPackages" value="true"/>
        </javaClientGenerator>

        <!-- Table configuration for timeseries data -->
        <!-- Note: IoTDB doesn't have traditional tables, these are logical mappings -->
        <table schema="root.factory" tableName="sensors"
               enableCountByExample="false"
               enableUpdateByExample="false"
               enableDeleteByExample="false"
               enableSelectByExample="true">

            <!-- Custom SQL for IoTDB timeseries queries -->
            <property name="useActualColumnNames" value="true"/>
            <property name="timeseriesPath" value="root.factory.sensors"/>
        </table>

    </context>
</generatorConfiguration>
```

### MyBatis Configuration

```yaml
# application.yml
spring:
  datasource:
    driver-class-name: org.apache.iotdb.jdbc.IoTDBDriver
    url: jdbc:iotdb://127.0.0.1:6667/
    username: root
    password: root

    # HikariCP configuration for IoTDB
    hikari:
      maximum-pool-size: 20
      minimum-idle: 5
      connection-timeout: 30000
      idle-timeout: 600000
      max-lifetime: 1800000
      pool-name: IoTDBHikariPool

      # IoTDB-specific connection properties
      data-source-properties:
        fetchSize: 10000
        socketTimeout: 60000

mybatis:
  # Mapper XML files location
  mapper-locations: classpath:mapper/*.xml

  # Type aliases package
  type-aliases-package: com.example.iotdb.model

  # MyBatis configuration
  configuration:
    # Enable camelCase mapping
    map-underscore-to-camel-case: true

    # Cache settings
    cache-enabled: true
    lazy-loading-enabled: false

    # Log SQL statements (development only)
    log-impl: org.apache.ibatis.logging.stdout.StdOutImpl

# Logging configuration
logging:
  level:
    com.example.iotdb.mapper: DEBUG
    org.apache.iotdb: INFO
```

## Mapper Interface Examples

### Sensor Data Mapper Interface

```java
@Mapper
public interface SensorDataMapper {

    /**
     * Insert single sensor reading
     */
    @Insert("INSERT INTO root.factory.sensors(timestamp, temperature, humidity, pressure) " +
            "VALUES(#{timestamp}, #{temperature}, #{humidity}, #{pressure})")
    int insertSensorReading(SensorReading reading);

    /**
     * Insert multiple sensor readings (batch)
     */
    @Insert({
        "<script>",
        "INSERT INTO root.factory.sensors(timestamp, temperature, humidity, pressure) VALUES ",
        "<foreach collection='readings' item='reading' separator=','>",
        "(#{reading.timestamp}, #{reading.temperature}, #{reading.humidity}, #{reading.pressure})",
        "</foreach>",
        "</script>"
    })
    int insertBatchSensorReadings(@Param("readings") List<SensorReading> readings);

    /**
     * Query recent sensor readings with iterator-friendly ResultSet handling
     */
    @Select("SELECT timestamp, temperature, humidity, pressure " +
            "FROM root.factory.sensors " +
            "ORDER BY timestamp DESC " +
            "LIMIT #{limit}")
    @Options(fetchSize = 1000) // Configure fetch size for memory efficiency
    List<SensorReading> selectRecentReadings(@Param("limit") int limit);

    /**
     * Query sensor readings by time range
     */
    @Select("SELECT timestamp, temperature, humidity, pressure " +
            "FROM root.factory.sensors " +
            "WHERE timestamp >= #{startTime} AND timestamp <= #{endTime} " +
            "ORDER BY timestamp")
    @Options(fetchSize = 5000)
    List<SensorReading> selectReadingsByTimeRange(
        @Param("startTime") long startTime,
        @Param("endTime") long endTime
    );

    /**
     * Query with custom conditions
     */
    List<SensorReading> selectReadingsWithConditions(SensorQueryParams params);

    /**
     * Get aggregated statistics
     */
    @Select("SELECT AVG(temperature) as avgTemperature, " +
            "MAX(temperature) as maxTemperature, " +
            "MIN(temperature) as minTemperature, " +
            "AVG(humidity) as avgHumidity, " +
            "COUNT(*) as totalCount " +
            "FROM root.factory.sensors " +
            "WHERE timestamp >= #{startTime}")
    SensorStatistics getStatistics(@Param("startTime") long startTime);

    /**
     * Create timeseries (DDL operation)
     */
    @Update("CREATE TIMESERIES root.factory.sensors.#{measurement} " +
            "WITH DATATYPE=#{dataType}, ENCODING=#{encoding}, COMPRESSION=#{compression}")
    int createTimeseries(
        @Param("measurement") String measurement,
        @Param("dataType") String dataType,
        @Param("encoding") String encoding,
        @Param("compression") String compression
    );

    /**
     * Check if timeseries exists
     */
    @Select("SHOW TIMESERIES root.factory.sensors.#{measurement}")
    List<Map<String, Object>> checkTimeseriesExists(@Param("measurement") String measurement);
}
```

### Device Management Mapper

```java
@Mapper
public interface DeviceMapper {

    /**
     * Get all devices under a path
     */
    @Select("SHOW DEVICES root.factory.**")
    List<String> getAllDevices();

    /**
     * Get device count
     */
    @Select("COUNT DEVICES root.factory.**")
    long getDeviceCount();

    /**
     * Get latest data for each device
     */
    @Select("SELECT last(*) FROM root.factory.**")
    @Options(fetchSize = 1000)
    List<Map<String, Object>> getLatestDataForAllDevices();

    /**
     * Insert device metadata (using table model if available)
     */
    @Insert("INSERT INTO device_metadata(device_id, location, type, status) " +
            "VALUES(#{deviceId}, #{location}, #{type}, #{status})")
    int insertDeviceMetadata(DeviceMetadata metadata);

    /**
     * Query device metadata
     */
    @Select("SELECT * FROM device_metadata WHERE device_id = #{deviceId}")
    DeviceMetadata getDeviceMetadata(@Param("deviceId") String deviceId);
}
```

## XML Mapper Files

### Sensor Data XML Mapper

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN"
    "http://mybatis.org/dtd/mybatis-3-mapper.dtd">

<mapper namespace="com.example.iotdb.mapper.SensorDataMapper">

    <!-- Result map for sensor readings -->
    <resultMap id="SensorReadingResultMap" type="com.example.iotdb.model.SensorReading">
        <result column="timestamp" property="timestamp" jdbcType="BIGINT"/>
        <result column="temperature" property="temperature" jdbcType="FLOAT"/>
        <result column="humidity" property="humidity" jdbcType="FLOAT"/>
        <result column="pressure" property="pressure" jdbcType="FLOAT"/>
    </resultMap>

    <!-- Complex query with conditions -->
    <select id="selectReadingsWithConditions"
            parameterType="com.example.iotdb.model.SensorQueryParams"
            resultMap="SensorReadingResultMap"
            fetchSize="5000">
        SELECT timestamp, temperature, humidity, pressure
        FROM root.factory.sensors
        <where>
            <if test="startTime != null">
                AND timestamp >= #{startTime}
            </if>
            <if test="endTime != null">
                AND timestamp &lt;= #{endTime}
            </if>
            <if test="minTemperature != null">
                AND temperature >= #{minTemperature}
            </if>
            <if test="maxTemperature != null">
                AND temperature &lt;= #{maxTemperature}
            </if>
            <if test="minHumidity != null">
                AND humidity >= #{minHumidity}
            </if>
            <if test="maxHumidity != null">
                AND humidity &lt;= #{maxHumidity}
            </if>
        </where>
        ORDER BY timestamp
        <if test="limit != null">
            LIMIT #{limit}
        </if>
    </select>

    <!-- Streaming query for large datasets (cursor-based) -->
    <select id="selectReadingsStream"
            parameterType="map"
            resultMap="SensorReadingResultMap"
            fetchSize="1000"
            resultSetType="FORWARD_ONLY">
        SELECT timestamp, temperature, humidity, pressure
        FROM root.factory.sensors
        WHERE timestamp >= #{startTime}
        AND timestamp &lt;= #{endTime}
        ORDER BY timestamp
    </select>

    <!-- Aggregated query by time window -->
    <select id="getAggregatedDataByWindow"
            parameterType="map"
            resultType="map">
        SELECT
            date_bin(INTERVAL '#{intervalMinutes}' MINUTE, timestamp) as window_start,
            AVG(temperature) as avg_temperature,
            MAX(temperature) as max_temperature,
            MIN(temperature) as min_temperature,
            AVG(humidity) as avg_humidity,
            COUNT(*) as sample_count
        FROM root.factory.sensors
        WHERE timestamp >= #{startTime} AND timestamp &lt;= #{endTime}
        GROUP BY date_bin(INTERVAL '#{intervalMinutes}' MINUTE, timestamp)
        ORDER BY window_start
    </select>

    <!-- Batch insert using MyBatis batch processing -->
    <insert id="insertBatchReadingsOptimized"
            parameterType="list"
            useGeneratedKeys="false">
        <foreach collection="list" item="reading" separator=";">
            INSERT INTO root.factory.sensors(timestamp, temperature, humidity, pressure)
            VALUES(#{reading.timestamp}, #{reading.temperature}, #{reading.humidity}, #{reading.pressure})
        </foreach>
    </insert>

</mapper>
```

### Device Management XML Mapper

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN"
    "http://mybatis.org/dtd/mybatis-3-mapper.dtd">

<mapper namespace="com.example.iotdb.mapper.DeviceMapper">

    <resultMap id="DeviceMetadataResultMap" type="com.example.iotdb.model.DeviceMetadata">
        <result column="device_id" property="deviceId" jdbcType="VARCHAR"/>
        <result column="location" property="location" jdbcType="VARCHAR"/>
        <result column="type" property="type" jdbcType="VARCHAR"/>
        <result column="status" property="status" jdbcType="VARCHAR"/>
        <result column="created_time" property="createdTime" jdbcType="TIMESTAMP"/>
    </resultMap>

    <!-- Dynamic device queries -->
    <select id="queryDevicesByPattern"
            parameterType="map"
            resultType="string">
        SHOW DEVICES
        <if test="pattern != null">
            ${pattern}
        </if>
        <if test="pattern == null">
            root.**
        </if>
    </select>

    <!-- Device statistics -->
    <select id="getDeviceStatistics"
            parameterType="map"
            resultType="map">
        SELECT
            COUNT(DISTINCT device_id) as device_count,
            COUNT(*) as measurement_count,
            MIN(timestamp) as earliest_data,
            MAX(timestamp) as latest_data
        FROM (
            SELECT * FROM root.factory.**
            <if test="startTime != null">
                WHERE timestamp >= #{startTime}
            </if>
        ) device_data
    </select>

</mapper>
```

## Spring Boot Integration

### Configuration Class

```java
@Configuration
@EnableTransactionManagement
@MapperScan(basePackages = "com.example.iotdb.mapper")
public class MyBatisIoTDBConfig {

    @Bean
    @Primary
    @ConfigurationProperties("spring.datasource")
    public DataSource iotdbDataSource() {
        return DataSourceBuilder.create()
            .driverClassName("org.apache.iotdb.jdbc.IoTDBDriver")
            .build();
    }

    @Bean
    public SqlSessionFactory sqlSessionFactory(DataSource dataSource) throws Exception {
        SqlSessionFactoryBean factory = new SqlSessionFactoryBean();
        factory.setDataSource(dataSource);

        // MyBatis configuration
        org.apache.ibatis.session.Configuration configuration = new org.apache.ibatis.session.Configuration();
        configuration.setMapUnderscoreToCamelCase(true);
        configuration.setCacheEnabled(true);
        configuration.setLazyLoadingEnabled(false);

        // Set default fetch size for IoTDB
        configuration.setDefaultFetchSize(5000);

        factory.setConfiguration(configuration);

        // Set mapper locations
        factory.setMapperLocations(new PathMatchingResourcePatternResolver()
            .getResources("classpath:mapper/*.xml"));

        return factory.getObject();
    }

    @Bean
    public SqlSessionTemplate sqlSessionTemplate(SqlSessionFactory sqlSessionFactory) {
        return new SqlSessionTemplate(sqlSessionFactory, ExecutorType.BATCH);
    }

    @Bean
    public DataSourceTransactionManager transactionManager(DataSource dataSource) {
        return new DataSourceTransactionManager(dataSource);
    }
}
```

### Data Models

```java
@Data
@AllArgsConstructor
@NoArgsConstructor
public class SensorReading {
    private Long timestamp;
    private Float temperature;
    private Float humidity;
    private Float pressure;

    public SensorReading(Float temperature, Float humidity, Float pressure) {
        this.timestamp = System.currentTimeMillis();
        this.temperature = temperature;
        this.humidity = humidity;
        this.pressure = pressure;
    }
}

@Data
@AllArgsConstructor
@NoArgsConstructor
public class SensorQueryParams {
    private Long startTime;
    private Long endTime;
    private Float minTemperature;
    private Float maxTemperature;
    private Float minHumidity;
    private Float maxHumidity;
    private Integer limit;
}

@Data
@AllArgsConstructor
@NoArgsConstructor
public class SensorStatistics {
    private Double avgTemperature;
    private Float maxTemperature;
    private Float minTemperature;
    private Double avgHumidity;
    private Long totalCount;
}

@Data
@AllArgsConstructor
@NoArgsConstructor
public class DeviceMetadata {
    private String deviceId;
    private String location;
    private String type;
    private String status;
    private Date createdTime;
}
```

## Service Layer Implementation

### MyBatis-based IoTDB Service

```java
@Service
@Transactional
@Slf4j
public class MyBatisIoTDBService {

    @Autowired
    private SensorDataMapper sensorDataMapper;

    @Autowired
    private DeviceMapper deviceMapper;

    @Autowired
    private SqlSessionTemplate sqlSessionTemplate;

    /**
     * Initialize schema using MyBatis
     */
    @PostConstruct
    public void initializeSchema() {
        try {
            // Create timeseries using mapper
            createTimeseriesIfNotExists("temperature", "FLOAT", "RLE", "SNAPPY");
            createTimeseriesIfNotExists("humidity", "FLOAT", "RLE", "SNAPPY");
            createTimeseriesIfNotExists("pressure", "FLOAT", "RLE", "SNAPPY");

            log.info("IoTDB schema initialized via MyBatis");

        } catch (Exception e) {
            log.error("Failed to initialize schema", e);
        }
    }

    private void createTimeseriesIfNotExists(String measurement, String dataType,
                                           String encoding, String compression) {
        try {
            List<Map<String, Object>> existing = sensorDataMapper.checkTimeseriesExists(measurement);
            if (existing.isEmpty()) {
                sensorDataMapper.createTimeseries(measurement, dataType, encoding, compression);
                log.info("Created timeseries: {}", measurement);
            }
        } catch (Exception e) {
            log.warn("Timeseries {} may already exist: {}", measurement, e.getMessage());
        }
    }

    /**
     * Insert single sensor reading
     */
    public void insertSensorReading(SensorReading reading) {
        try {
            int result = sensorDataMapper.insertSensorReading(reading);
            if (result != 1) {
                throw new RuntimeException("Failed to insert sensor reading");
            }
            log.debug("Inserted sensor reading: {}", reading);

        } catch (Exception e) {
            log.error("Failed to insert sensor reading", e);
            throw new IoTDBOperationException("Insert failed", e);
        }
    }

    /**
     * Batch insert with MyBatis batch processing
     */
    public void insertSensorReadingsBatch(List<SensorReading> readings) {
        if (readings.isEmpty()) return;

        try {
            // Use MyBatis batch session for optimal performance
            try (SqlSession batchSession = sqlSessionTemplate.getSqlSessionFactory()
                    .openSession(ExecutorType.BATCH, false)) {

                SensorDataMapper batchMapper = batchSession.getMapper(SensorDataMapper.class);

                for (SensorReading reading : readings) {
                    batchMapper.insertSensorReading(reading);
                }

                batchSession.flushStatements();
                batchSession.commit();

                log.info("Batch inserted {} sensor readings", readings.size());
            }

        } catch (Exception e) {
            log.error("Failed to batch insert sensor readings", e);
            throw new IoTDBOperationException("Batch insert failed", e);
        }
    }

    /**
     * Query readings with memory-efficient processing
     */
    @Transactional(readOnly = true)
    public List<SensorReading> getRecentReadings(int limit) {
        try {
            List<SensorReading> readings = sensorDataMapper.selectRecentReadings(limit);
            log.debug("Retrieved {} recent readings", readings.size());
            return readings;

        } catch (Exception e) {
            log.error("Failed to query recent readings", e);
            throw new IoTDBOperationException("Query failed", e);
        }
    }

    /**
     * Query with custom conditions
     */
    @Transactional(readOnly = true)
    public List<SensorReading> queryReadingsWithConditions(SensorQueryParams params) {
        try {
            List<SensorReading> readings = sensorDataMapper.selectReadingsWithConditions(params);
            log.debug("Retrieved {} readings with conditions", readings.size());
            return readings;

        } catch (Exception e) {
            log.error("Failed to query readings with conditions", e);
            throw new IoTDBOperationException("Conditional query failed", e);
        }
    }

    /**
     * Stream processing for large datasets
     */
    @Transactional(readOnly = true)
    public void processLargeDataset(long startTime, long endTime,
                                   Consumer<SensorReading> processor) {
        try {
            // Use MyBatis cursor for streaming
            try (SqlSession session = sqlSessionTemplate.getSqlSessionFactory().openSession()) {
                SensorDataMapper mapper = session.getMapper(SensorDataMapper.class);

                Map<String, Object> params = new HashMap<>();
                params.put("startTime", startTime);
                params.put("endTime", endTime);

                // Stream processing with cursor
                try (Cursor<SensorReading> cursor = session.selectCursor(
                        "com.example.iotdb.mapper.SensorDataMapper.selectReadingsStream", params)) {

                    cursor.forEach(processor);
                }
            }

            log.info("Processed large dataset from {} to {}", startTime, endTime);

        } catch (Exception e) {
            log.error("Failed to process large dataset", e);
            throw new IoTDBOperationException("Stream processing failed", e);
        }
    }

    /**
     * Get statistics using MyBatis
     */
    @Transactional(readOnly = true)
    public SensorStatistics getStatistics(long sinceTime) {
        try {
            SensorStatistics stats = sensorDataMapper.getStatistics(sinceTime);
            return stats != null ? stats : new SensorStatistics();

        } catch (Exception e) {
            log.error("Failed to get statistics", e);
            throw new IoTDBOperationException("Statistics query failed", e);
        }
    }
}
```

## Transaction Management

### Transaction Configuration

```java
@Configuration
@EnableTransactionManagement
public class TransactionConfig {

    @Bean
    public PlatformTransactionManager transactionManager(DataSource dataSource) {
        DataSourceTransactionManager manager = new DataSourceTransactionManager(dataSource);
        manager.setDefaultTimeout(60); // 60 seconds default timeout
        return manager;
    }

    @Bean
    public TransactionTemplate transactionTemplate(PlatformTransactionManager transactionManager) {
        TransactionTemplate template = new TransactionTemplate(transactionManager);
        template.setIsolationLevel(TransactionDefinition.ISOLATION_READ_COMMITTED);
        template.setPropagationBehavior(TransactionDefinition.PROPAGATION_REQUIRED);
        return template;
    }
}
```

### Transactional Service Methods

```java
@Service
public class TransactionalIoTDBService {

    @Autowired
    private MyBatisIoTDBService iotdbService;

    @Autowired
    private TransactionTemplate transactionTemplate;

    /**
     * Transactional batch operation
     */
    @Transactional
    public void performBatchOperations(List<SensorReading> readings) {
        // All operations in single transaction
        iotdbService.insertSensorReadingsBatch(readings);

        // Update related metadata
        updateDeviceLastSeen(readings);
    }

    /**
     * Programmatic transaction management
     */
    public void performComplexOperation(List<SensorReading> readings) {
        transactionTemplate.execute(status -> {
            try {
                iotdbService.insertSensorReadingsBatch(readings);
                updateStatistics();
                return null;
            } catch (Exception e) {
                status.setRollbackOnly();
                throw new RuntimeException("Complex operation failed", e);
            }
        });
    }

    private void updateDeviceLastSeen(List<SensorReading> readings) {
        // Implementation for updating device metadata
    }

    private void updateStatistics() {
        // Implementation for updating statistics
    }
}
```

## Performance Optimization

### Connection Pool Optimization

```yaml
spring:
  datasource:
    hikari:
      # Pool sizing
      maximum-pool-size: 25
      minimum-idle: 5

      # Connection lifecycle
      connection-timeout: 20000
      idle-timeout: 300000
      max-lifetime: 1200000

      # Validation
      connection-test-query: "SELECT 1"
      validation-timeout: 3000

      # IoTDB-specific optimizations
      data-source-properties:
        # Large fetch size for IoTDB
        fetchSize: 10000
        # Socket timeout for long queries
        socketTimeout: 300000
        # Enable compression if supported
        useCompression: false

mybatis:
  configuration:
    # Default fetch size
    default-fetch-size: 5000

    # Enable second-level cache
    cache-enabled: true

    # Lazy loading for large objects
    lazy-loading-enabled: true
    aggressive-lazy-loading: false

    # Executor type for batch operations
    default-executor-type: REUSE
```

### Performance Monitoring

```java
@Component
@Slf4j
public class MyBatisPerformanceMonitor {

    @EventListener
    public void handleQueryExecution(SqlSessionFactoryBeanCreatedEvent event) {
        // Configure performance monitoring
        log.info("MyBatis SqlSessionFactory created for IoTDB");
    }

    /**
     * Monitor connection pool performance
     */
    @Scheduled(fixedRate = 60000) // Every minute
    public void monitorConnectionPool(@Autowired DataSource dataSource) {
        if (dataSource instanceof HikariDataSource) {
            HikariDataSource hikariDS = (HikariDataSource) dataSource;
            HikariPoolMXBean poolBean = hikariDS.getHikariPoolMXBean();

            log.info("Connection Pool Stats - Active: {}, Idle: {}, Total: {}, Waiting: {}",
                poolBean.getActiveConnections(),
                poolBean.getIdleConnections(),
                poolBean.getTotalConnections(),
                poolBean.getThreadsAwaitingConnection());
        }
    }
}
```

### Best Practices Summary

1. **Use JDBC with connection pooling** - HikariCP provides excellent performance
2. **Leverage MyBatis streaming** - Use cursors for large result sets
3. **Batch operations** - Use MyBatis batch sessions for bulk inserts
4. **Appropriate fetch sizes** - Configure large fetch sizes for IoTDB
5. **Transaction management** - Use declarative transactions where appropriate
6. **Connection monitoring** - Monitor pool performance and query execution
7. **Iterator patterns** - Even with MyBatis, be mindful of memory usage with large datasets

This MyBatis integration provides a robust, SQL-mapping approach to IoTDB development with proper performance optimization and transaction management.