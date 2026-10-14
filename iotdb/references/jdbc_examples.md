# JDBC Examples for IoTDB Connection

Use JDBC when a framework requires it (MyBatis, Spring `JdbcTemplate`, BI tools). For high-throughput writes
from application code, the native pools (`SessionPool` / `ITableSessionPool`, see [Java Examples](java_examples.md))
are faster.

## Dependency

```xml
<dependency>
    <groupId>org.apache.iotdb</groupId>
    <artifactId>iotdb-jdbc</artifactId>
    <!-- keep equal to the server version -->
    <version>${iotdb.version}</version>
</dependency>
```

Driver class: `org.apache.iotdb.jdbc.IoTDBDriver`.

## Connection URLs

| Model | URL |
|-------|-----|
| Tree | `jdbc:iotdb://127.0.0.1:6667/` |
| Table (V2.0+) | `jdbc:iotdb://127.0.0.1:6667/factory?sql_dialect=table` (database optional; otherwise `USE factory`) |

SSL: append `use_ssl=true&trust_store=<path>&trust_store_pwd=<pwd>`.

## Transactions

IoTDB has no transactions. `commit()` and `rollback()` are no-ops and `setAutoCommit(false)` does not group
statements: every statement takes effect when executed, and a failed batch is not rolled back.

## Tree Model

```java
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;

public class TreeJdbcExample {

    public static void main(String[] args) throws SQLException {
        String url = "jdbc:iotdb://127.0.0.1:6667/";
        try (Connection connection = DriverManager.getConnection(url, "root", "root");
             Statement statement = connection.createStatement()) {

            statement.execute("CREATE ALIGNED TIMESERIES root.factory.line1.device7(temperature FLOAT, humidity FLOAT)");

            // Batch inserts: one round trip per executeBatch()
            for (int i = 0; i < 1000; i++) {
                statement.addBatch(String.format(
                    "INSERT INTO root.factory.line1.device7(timestamp, temperature, humidity) VALUES (%d, %.1f, %.1f)",
                    1700000000000L + i * 1000L, 20.0 + i % 10, 60.0));
            }
            statement.executeBatch();
            statement.clearBatch();

            // Query: iterate the ResultSet row by row
            try (ResultSet rs = statement.executeQuery(
                    "SELECT temperature, humidity FROM root.factory.line1.device7 LIMIT 10")) {
                while (rs.next()) {
                    long time = rs.getLong("Time");
                    float temperature = rs.getFloat("root.factory.line1.device7.temperature");
                    System.out.println(time + " " + temperature);
                }
            }
        }

        // Parameterized query (placeholders are substituted on the client)
        try (Connection connection = DriverManager.getConnection(url, "root", "root");
             PreparedStatement ps = connection.prepareStatement(
                 "SELECT temperature FROM root.factory.line1.device7 WHERE time >= ? AND time < ?")) {
            ps.setLong(1, 1700000000000L);
            ps.setLong(2, 1700000600000L);
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    System.out.println(rs.getLong("Time"));
                }
            }
        }
    }
}
```

Tree result columns are `Time` plus one column per full timeseries path.

## Table Model

```java
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;

public class TableJdbcExample {

    public static void main(String[] args) throws SQLException {
        try (Connection connection = DriverManager.getConnection(
                "jdbc:iotdb://127.0.0.1:6667?sql_dialect=table", "root", "root");
             Statement statement = connection.createStatement()) {

            statement.execute("CREATE DATABASE IF NOT EXISTS factory");
            statement.execute("USE factory");
            statement.execute(
                "CREATE TABLE IF NOT EXISTS sensors ("
                    + "region STRING TAG, device_id STRING TAG, model STRING ATTRIBUTE, "
                    + "temperature FLOAT FIELD, humidity DOUBLE FIELD)");

            statement.execute(
                "INSERT INTO sensors (time, region, device_id, model, temperature, humidity) VALUES "
                    + "(1700000000000, 'north', 'd7', 'A', 25.5, 60.0), "
                    + "(1700000001000, 'north', 'd7', 'A', 25.8, 59.2)");

            try (ResultSet rs = statement.executeQuery(
                    "SELECT time, device_id, temperature FROM sensors "
                        + "WHERE region = 'north' AND time >= 1700000000000")) {
                while (rs.next()) {
                    System.out.println(rs.getLong("time") + " " + rs.getString("device_id")
                        + " " + rs.getFloat("temperature"));
                }
            }
        }
    }
}
```

## Connection Pool (HikariCP)

```java
import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.HikariDataSource;

HikariConfig config = new HikariConfig();
config.setDriverClassName("org.apache.iotdb.jdbc.IoTDBDriver");
config.setJdbcUrl("jdbc:iotdb://127.0.0.1:6667/factory?sql_dialect=table");
config.setUsername("root");
config.setPassword(System.getenv("IOTDB_PASSWORD"));
config.setMaximumPoolSize(10);
config.setConnectionTestQuery("SHOW VERSION");
config.setAutoCommit(true);   // IoTDB ignores transactions anyway
HikariDataSource dataSource = new HikariDataSource(config);
```

Create one `DataSource` per application and close it on shutdown.

## Spring JdbcTemplate

```java
import org.springframework.jdbc.core.JdbcTemplate;

JdbcTemplate jdbc = new JdbcTemplate(dataSource);   // table-dialect DataSource from above

jdbc.update(
    "INSERT INTO sensors (time, region, device_id, temperature) VALUES (?, ?, ?, ?)",
    System.currentTimeMillis(), "north", "d7", 25.5f);

List<Float> temperatures = jdbc.query(
    "SELECT temperature FROM sensors WHERE device_id = ? AND time >= ?",
    (rs, rowNum) -> rs.getFloat("temperature"),
    "d7", System.currentTimeMillis() - 3_600_000L);
```

## Best Practices

1. Close `ResultSet`, `Statement` and `Connection` (`try`-with-resources).
2. Bound every query by time; in the table model also filter by TAG columns.
3. Batch inserts (`addBatch` / multi-row `VALUES`) instead of one statement per row; for large volumes switch to
   the native Tablet APIs.
4. Do not rely on `commit()` / `rollback()` for consistency.
