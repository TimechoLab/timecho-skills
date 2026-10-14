# MyBatis Integration with IoTDB

MyBatis and MyBatis-Plus work on top of the IoTDB JDBC driver. Use the **table model**
(`sql_dialect=table`) for MyBatis: its tables map naturally to mapper result types, and the official
MyBatis-Plus Generator only supports the table model. Plain SQL mappers also work with the tree model.

## Dependencies

```xml
<dependency>
    <groupId>org.mybatis.spring.boot</groupId>
    <artifactId>mybatis-spring-boot-starter</artifactId>
    <version>${mybatis-spring-boot.version}</version>
</dependency>
<dependency>
    <groupId>org.apache.iotdb</groupId>
    <artifactId>iotdb-jdbc</artifactId>
    <!-- keep equal to the server version -->
    <version>${iotdb.version}</version>
</dependency>
```

## Data Source

```yaml
spring:
  datasource:
    driver-class-name: org.apache.iotdb.jdbc.IoTDBDriver
    url: jdbc:iotdb://127.0.0.1:6667/factory?sql_dialect=table
    username: root
    password: ${IOTDB_PASSWORD}
    hikari:
      maximum-pool-size: 10
      connection-test-query: SHOW VERSION

mybatis:
  mapper-locations: classpath:mapper/*.xml
  configuration:
    map-underscore-to-camel-case: true
```

Table used below:

```sql
CREATE TABLE IF NOT EXISTS sensors (
  region STRING TAG,
  device_id STRING TAG,
  model STRING ATTRIBUTE,
  temperature FLOAT FIELD,
  humidity DOUBLE FIELD
)
```

## Model

```java
public class SensorReading {
    private Long time;
    private String region;
    private String deviceId;
    private Float temperature;
    private Double humidity;
    // getters and setters
}
```

## Mapper Interface (Annotations)

```java
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface SensorMapper {

    @Insert("INSERT INTO sensors (time, region, device_id, temperature, humidity) "
        + "VALUES (#{time}, #{region}, #{deviceId}, #{temperature}, #{humidity})")
    int insert(SensorReading reading);

    @Select("SELECT time, region, device_id, temperature, humidity FROM sensors "
        + "WHERE device_id = #{deviceId} AND time >= #{from} AND time < #{to} "
        + "ORDER BY time LIMIT #{limit}")
    List<SensorReading> findByDevice(@Param("deviceId") String deviceId,
                                     @Param("from") long from,
                                     @Param("to") long to,
                                     @Param("limit") int limit);

    @Select("SELECT device_id, avg(temperature) AS temperature FROM sensors "
        + "WHERE region = #{region} AND time >= #{from} GROUP BY device_id")
    List<SensorReading> averageByDevice(@Param("region") String region, @Param("from") long from);
}
```

## Batch Insert (XML Mapper)

`resources/mapper/SensorMapper.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN" "http://mybatis.org/dtd/mybatis-3-mapper.dtd">
<mapper namespace="com.example.iotdb.SensorMapper">

    <!-- one multi-row INSERT per call; keep batches to a few thousand rows -->
    <insert id="insertBatch">
        INSERT INTO sensors (time, region, device_id, temperature, humidity) VALUES
        <foreach collection="list" item="r" separator=",">
            (#{r.time}, #{r.region}, #{r.deviceId}, #{r.temperature}, #{r.humidity})
        </foreach>
    </insert>

</mapper>
```

```java
int insertBatch(@Param("list") List<SensorReading> readings);
```

## Tree Model with MyBatis

Tree-model SQL works in mappers when the data source URL has no `sql_dialect=table`:

```java
@Insert("INSERT INTO root.factory.line1.device7(timestamp, temperature) VALUES (#{time}, #{temperature})")
int insertTree(@Param("time") long time, @Param("temperature") float temperature);
```

Paths are identifiers, not values: they cannot be `#{}` parameters. If a path must be dynamic, use `${}` only
with a whitelisted value. Tree result columns are full paths (`root.factory.line1.device7.temperature`), so map
them with `@Results` / `resultMap` or column aliases.

## MyBatis-Plus Generator (Table Model)

The official guide (IoTDB docs, *Ecosystem Integration → MyBatisPlus Generator*) generates entities, mappers,
services and controllers from table-model tables with `mybatis-plus-generator` 3.5.10:

```java
import com.baomidou.mybatisplus.generator.FastAutoGenerator;
import com.baomidou.mybatisplus.generator.config.DataSourceConfig;
import org.apache.iotdb.jdbc.IoTDBDataSource;

IoTDBDataSource dataSource = new IoTDBDataSource();
dataSource.setUrl("jdbc:iotdb://127.0.0.1:6667/factory?sql_dialect=table");
dataSource.setUser("root");
dataSource.setPassword("root");
FastAutoGenerator.create(new DataSourceConfig.Builder(dataSource)
        .driverClassName("org.apache.iotdb.jdbc.IoTDBDriver"))
    // globalConfig / packageConfig / dataSourceConfig (type mapping) / strategyConfig
    // as in the official guide
    .execute();
```

Review generated code before use: `updateById`-style methods cannot work on FIELD columns (see below).

## IoTDB Semantics to Respect

- **No transactions**: `@Transactional` and `rollback()` have no effect on IoTDB.
- **UPDATE** only changes ATTRIBUTE columns; FIELD values are changed by writing the same device and time again.
- **DELETE** removes rows by time range and/or TAG values (`DELETE FROM sensors WHERE time < ... AND device_id = ...`).
- No user-creatable secondary indexes; always filter by TAG columns and time.
- For large ingestion volumes use the native `ITableSessionPool` Tablet API instead of SQL inserts.
